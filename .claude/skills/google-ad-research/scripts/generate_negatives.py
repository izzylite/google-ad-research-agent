# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""generate_negatives.py — validator + deduplicator for LLM-generated negatives.json.

CLI:
    uv run generate_negatives.py --run-dir <abs>

Reads:
    {run_dir}/negatives.json   (LLM-written — required, exit 3 if missing/unparseable)
    {run_dir}/ranked.json      (positive keyword pool — required, exit 3 if missing/unparseable)
    {run_dir}/brief.md         (optional — brand_terms field for brand-safety guard)
    {run_dir}/raw/google-ads-perf.json   (optional — customer_descriptive_name for brand-safety guard)

Writes:
    {run_dir}/negatives.json        (overwritten with valid + deduped rows only)
    {run_dir}/raw/negatives.json    (copy of validated output — for RPRT-05)

Stdout (exactly one JSON line):
    {"valid_count": N, "error_count": N, "collision_count": N,
     "brand_safety_dropped": N, "brand_safety_tokens": [...],
     "category_warnings": [...]}

Exit codes:
    0  valid, no collisions, all 6 categories represented
    1  enum errors fixed OR collisions removed OR category missing (operator warned)
    3  negatives.json or ranked.json missing or not valid JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TIERS: frozenset[str] = frozenset({"Strong", "Considered", "Investigate"})

VALID_CATEGORIES: frozenset[str] = frozenset({
    "jobs-careers",
    "free-DIY-tutorial",
    "used-refurb-wholesale",
    "competitor-brand",
    "wrong-geo",
    "wrong-audience",
})


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def validate_negatives(negatives: list[dict]) -> tuple[list[dict], list[dict]]:
    """Validate tier and category enums for each negative row.

    Args:
        negatives: Raw list of negative keyword dicts.

    Returns:
        (valid_rows, error_rows) where error_rows have an added "error" key.
    """
    valid: list[dict] = []
    errors: list[dict] = []
    for row in negatives:
        if row.get("tier") not in VALID_TIERS:
            errors.append({**row, "error": f"invalid tier: {row.get('tier')!r}"})
        elif row.get("category") not in VALID_CATEGORIES:
            errors.append({**row, "error": f"invalid category: {row.get('category')!r}"})
        else:
            valid.append(row)
    return valid, errors


def dedupe_negatives(
    negatives: list[dict], ranked: list[dict]
) -> tuple[list[dict], list[str]]:
    """Remove negatives whose keyword appears in the positive ranked pool.

    Comparison is case-insensitive and strips surrounding whitespace.

    Args:
        negatives: Validated negative rows.
        ranked: Rows from ranked.json (positive keyword pool).

    Returns:
        (deduped_negatives, collisions) where collisions is a list of original
        keyword strings that were removed due to positive-pool overlap.
    """
    positive_keywords: set[str] = {row["keyword"].lower().strip() for row in ranked}
    deduped: list[dict] = []
    collisions: list[str] = []
    for neg in negatives:
        kw = neg["keyword"].lower().strip()
        if kw in positive_keywords:
            collisions.append(neg["keyword"])
        else:
            deduped.append(neg)
    return deduped, collisions


# ---------------------------------------------------------------------------
# Brand-safety guard (BRND-01)
# ---------------------------------------------------------------------------
#
# Algorithm: phrase-substring matching, not token-bag overlap.
#
# Token-bag overlap (intersect kw_tokens with protected_tokens) produced too
# many false positives — "md now urgent care" got dropped because it shares
# {urgent, care} with the brand "Primary Urgent Care Centers", even though
# MD Now is a real competitor. Industry-vocabulary words like "urgent",
# "care", "centers", "clinic", "doctor" appear in both legitimate competitor
# names AND the client's brand, so set intersection over-matches.
#
# Phrase-substring is conservative: only drops candidates whose normalised
# string contains a brand phrase (or vice versa for short candidates) as a
# CONTIGUOUS substring. This matches the operator's mental model — "primary
# urgent care" is dropped because that exact phrase IS the brand; "md now
# urgent care" is kept because no brand phrase appears as a substring.

# Minimum brand-phrase length — below this, the phrase is too generic to
# safely use as a substring match (would over-match common words).
_MIN_BRAND_PHRASE_CHARS = 4


def _normalise_brand_phrase(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation.

    Mirrors the canonicalisation other skill scripts use for keyword
    comparison (render_report._build_cluster_index, merge_signals canon).
    """
    text = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def _read_brand_phrases_from_brief(run_dir: Path) -> list[str]:
    """Return list of normalised brand phrases from brief.md `Brand terms:`.

    Comma-separated. Empty list when brief.md is missing, line is absent,
    or no phrase passes the minimum-length filter.
    """
    brief_path = run_dir / "brief.md"
    if not brief_path.exists():
        return []
    try:
        text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return []
    m = re.search(
        r"^\s*-?\s*\*\*Brand terms:\*\*\s*(.+)$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return []
    phrases: list[str] = []
    for chunk in m.group(1).split(","):
        norm = _normalise_brand_phrase(chunk)
        if norm and len(norm) >= _MIN_BRAND_PHRASE_CHARS:
            phrases.append(norm)
    return phrases


def _read_customer_name_phrase(run_dir: Path) -> str:
    """Return normalised customer_descriptive_name from raw/google-ads-perf.json.

    Defense-in-depth source — when the operator forgets `Brand terms:` in
    the brief, the account's own descriptive name (pulled from Google Ads
    API by perf_fetch.py) still protects the client brand.
    Returns empty string when Phase 8 wasn't run or the name is unavailable.
    """
    perf_path = run_dir / "raw" / "google-ads-perf.json"
    if not perf_path.exists():
        return ""
    try:
        perf = json.loads(perf_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    norm = _normalise_brand_phrase(perf.get("customer_descriptive_name") or "")
    return norm if len(norm) >= _MIN_BRAND_PHRASE_CHARS else ""


def filter_brand_safety(
    negatives: list[dict], protected_phrases: list[str]
) -> tuple[list[dict], list[dict]]:
    """Drop competitor-brand negatives whose normalised keyword contains
    (or is contained in) any protected brand phrase.

    Args:
        negatives: Validated + deduped negative rows.
        protected_phrases: List of normalised brand phrases — union of
            `Brand terms:` from brief and customer_descriptive_name from
            perf data. Empty list = guard disabled (no source available).

    Returns:
        (kept, dropped) where dropped rows carry "brand_safety_reason"
        naming the matched phrase. Non-competitor-brand rows always pass.
    """
    if not protected_phrases:
        return negatives, []
    kept: list[dict] = []
    dropped: list[dict] = []
    for row in negatives:
        if row.get("category") != "competitor-brand":
            kept.append(row)
            continue
        kw_norm = _normalise_brand_phrase(row.get("keyword", ""))
        matched: str | None = None
        for phrase in protected_phrases:
            # Bidirectional substring: brand phrase appears in candidate
            # (e.g. brand "primary urgent care" matches candidate
            # "primary urgent care lake worth"), OR candidate appears in
            # brand phrase (e.g. candidate "primary" matches brand
            # "primary urgent care centers"). Word-boundary aware via the
            # normalisation step (single-space tokens).
            if phrase in kw_norm or (
                len(kw_norm) >= _MIN_BRAND_PHRASE_CHARS and kw_norm in phrase
            ):
                matched = phrase
                break
        if matched:
            dropped.append({
                **row,
                "brand_safety_reason": (
                    f"matches protected brand phrase '{matched}' — would "
                    f"suppress own-brand traffic"
                ),
            })
        else:
            kept.append(row)
    return kept, dropped


def check_category_coverage(valid_rows: list[dict]) -> list[str]:
    """Return list of categories with zero representatives among valid_rows.

    Args:
        valid_rows: Validated (and deduped) negative rows.

    Returns:
        Sorted list of category strings that have no rows. Empty list = full coverage.
    """
    present: set[str] = {row["category"] for row in valid_rows}
    return sorted(VALID_CATEGORIES - present)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse args, validate and dedupe negatives.json, write output. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Validate and deduplicate LLM-generated negatives.json.",
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="Absolute path to the run folder.",
    )
    args = parser.parse_args()
    run_dir: Path = args.run_dir

    # -- Load required inputs ------------------------------------------------
    negatives_path = run_dir / "negatives.json"
    ranked_path = run_dir / "ranked.json"

    if not negatives_path.exists():
        print(f"ERROR: negatives.json not found in {run_dir}", file=sys.stderr)
        return 3

    if not ranked_path.exists():
        print(f"ERROR: ranked.json not found in {run_dir}", file=sys.stderr)
        return 3

    try:
        negatives: list[dict] = json.loads(negatives_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot parse negatives.json: {exc}", file=sys.stderr)
        return 3

    try:
        ranked: list[dict] = json.loads(ranked_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot parse ranked.json: {exc}", file=sys.stderr)
        return 3

    # -- Validate + dedupe ---------------------------------------------------
    valid, errors = validate_negatives(negatives)
    deduped, collisions = dedupe_negatives(valid, ranked)

    # -- Brand-safety guard (BRND-01) ---------------------------------------
    # Phrase-substring match against the union of:
    #   - brand_terms phrases (brief.md `**Brand terms:**`)
    #   - customer_descriptive_name (raw/google-ads-perf.json, Phase 8)
    # Either source alone is enough; both is defense-in-depth.
    # Empty list = guard disabled (no source available; caller should ensure
    # at least `Brand terms:` is set in the brief for real-account runs).
    brand_phrases = _read_brand_phrases_from_brief(run_dir)
    account_phrase = _read_customer_name_phrase(run_dir)
    protected_phrases = list(brand_phrases)
    if account_phrase and account_phrase not in protected_phrases:
        protected_phrases.append(account_phrase)
    safe, brand_dropped = filter_brand_safety(deduped, protected_phrases)

    missing_categories = check_category_coverage(safe)

    # -- Write outputs -------------------------------------------------------
    output_json = json.dumps(safe, indent=2, ensure_ascii=False)

    # Overwrite run_dir/negatives.json with valid+deduped rows
    negatives_path.write_text(output_json, encoding="utf-8", newline="\n")

    # Copy to run_dir/raw/negatives.json (raw/ must already exist — created by run_init.py)
    raw_dir = run_dir / "raw"
    if raw_dir.exists():
        (raw_dir / "negatives.json").write_text(output_json, encoding="utf-8", newline="\n")

    # -- Stdout summary ------------------------------------------------------
    result = {
        "valid_count": len(safe),
        "error_count": len(errors),
        "collision_count": len(collisions),
        "brand_safety_dropped": len(brand_dropped),
        "brand_safety_phrases": protected_phrases,
        "brand_safety_dropped_keywords": [d["keyword"] for d in brand_dropped],
        "category_warnings": missing_categories,
    }
    print(json.dumps(result))

    # -- Determine exit code -------------------------------------------------
    # Exit 1 if any enum errors were found, collisions were removed, brand-safety
    # rows were dropped, or categories missing — each is an operator-visible signal.
    if errors or collisions or brand_dropped or missing_categories:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
