# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""compliance_check.py — Scan brief.md + top-N ranked keywords against vertical
token lists; emit {run_dir}/compliance-flags.json sidecar.

Implements:
    CMPL-01  Scans brief.md (in full) plus the top-N ranked keywords from
             ranked-enriched.json against operator-editable token lists.
             Emits compliance-flags.json with a `matched_verticals[]` array
             (empty when nothing matched — file is still written).
    CMPL-02  Token lists live in references/compliance-verticals.json — DATA,
             not code. NO vertical-specific tokens (medical/legal/finance/
             gambling/crypto strings) appear in this Python file. Operator
             extends the JSON file; this script reads whatever it finds.

CMPL-05 contract (consumed by Phase 10 STEP-01):
    Every entry in matched_verticals[] carries a non-empty `verification_url`
    string so the Next-Steps checklist can reorder compliance to step 1 and
    link the operator to the correct Google policy page.

UNIT CONTRACT:
    Token matching is case-insensitive AND word-boundary-aware. Pitfall 3:
    "loan" must NOT match "loaner mug" — the \\b regex boundary blocks the
    false positive. "personal loan" (with `loan` as a whole word) DOES match.

This module exposes:
    COMPLIANCE_SCAN_TOP_N   (CMPL-01 default top-N window; operator-tunable)
    load_verticals          (CMPL-02 reference loader)
    find_matches            (word-boundary token scan helper)
    scan                    (top-level scan → compliance-flags.json dict)
    main_with_args          (CLI entrypoint — argv → exit code)

Reads:
    {run_dir}/brief.md
    {run_dir}/ranked-enriched.json
    <skill-root>/references/compliance-verticals.json
        (path overridable via --verticals-path for tests)

Writes:
    {run_dir}/compliance-flags.json

CLI:
    uv run compliance_check.py --run-dir <abs> [--verticals-path <abs>]

Stdout (one JSON line):
    {"matched_verticals_count": N, "verticals": ["medical", ...]}

Exit codes:
    0  ok (file written even when matched_verticals == [])
    2  retryable (transient disk error)
    3  fatal (missing input, malformed JSON, schema violation)
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

# Make sibling lib/ importable (mirror volume_enrich.py / bid_suggest.py /
# forecast_budget.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.log import configure_logger  # noqa: E402


# --- Tuning knobs (CMPL-01 top-N window) ---
# Edit here only; nothing else in this file uses literal top-N values.
# Pitfall 4: 50 covers high-signal keywords without false-positive flooding
# from long-tail rows (the brief.md is ALWAYS scanned in full regardless).
COMPLIANCE_SCAN_TOP_N: int = 50

log = configure_logger(__name__)


# ---------------------------------------------------------------------------
# CMPL-02 — load token lists from references/compliance-verticals.json
# ---------------------------------------------------------------------------

_REQUIRED_VERTICAL_KEYS = frozenset(
    {"name", "tokens", "verification_url", "policy_note"}
)


def load_verticals(reference_path: Path) -> list[dict]:
    """Load + validate the vertical token list (CMPL-02 contract).

    Returns the `verticals` array from references/compliance-verticals.json.
    Each entry MUST carry name + tokens + verification_url + policy_note —
    the verification_url is the CMPL-05 contract Phase 10 will consume.

    Raises FileNotFoundError when the file is missing (main_with_args
    translates to exit 3). Raises ValueError when an entry is malformed.
    """
    if not reference_path.exists():
        raise FileNotFoundError(
            f"compliance-verticals.json not found at {reference_path}"
        )
    data = json.loads(reference_path.read_text(encoding="utf-8"))
    verticals = data.get("verticals")
    if not isinstance(verticals, list) or not verticals:
        raise ValueError(
            f"{reference_path} must contain a non-empty 'verticals' array"
        )
    for entry in verticals:
        if not isinstance(entry, dict):
            raise ValueError(
                f"Each vertical entry must be an object, got {type(entry).__name__}"
            )
        missing = _REQUIRED_VERTICAL_KEYS - set(entry.keys())
        if missing:
            raise ValueError(
                f"Vertical '{entry.get('name', '?')}' missing required keys: "
                f"{sorted(missing)}"
            )
        if not isinstance(entry["tokens"], list) or not entry["tokens"]:
            raise ValueError(
                f"Vertical '{entry['name']}' tokens must be a non-empty list"
            )
    return verticals


# ---------------------------------------------------------------------------
# CMPL-01 — word-boundary token matching (Pitfall 3 mitigation)
# ---------------------------------------------------------------------------

def find_matches(text: str, tokens: list[str]) -> list[str]:
    """Return the sorted, de-duplicated list of tokens that appear in `text`.

    Case-insensitive (re.IGNORECASE) AND word-boundary-aware (\\b ... \\b).
    This combination is what blocks "loaner mug" from matching the `loan`
    token while still matching "personal loan".

    `re.escape` preserves multi-word tokens with spaces ("buy now pay later")
    and tokens with regex specials (rare; included defensively).

    Edge cases:
        find_matches("", ["loan"])    → []  (empty text)
        find_matches("text", [])      → []  (empty tokens)
        find_matches("text", ["", "loan"]) → []  (empty token entries skipped)

    Returned tokens are lower-cased + sorted for stable golden fixtures.
    """
    if not text or not tokens:
        return []
    found: set[str] = set()
    for token in tokens:
        if not isinstance(token, str) or not token.strip():
            continue
        pattern = r"\b" + re.escape(token) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            found.add(token.lower())
    return sorted(found)


# ---------------------------------------------------------------------------
# Top-N selection (Pitfall 4 — bounded keyword scan window)
# ---------------------------------------------------------------------------

def _select_top_keywords(
    ranked: list[dict], top_n: int
) -> list[dict]:
    """Return the top-N rows of `ranked`.

    If rows have a `score` key, sort descending by score (ties keep input
    order — Python's sort is stable). Otherwise preserve input order.
    """
    if not ranked:
        return []
    if any("score" in row for row in ranked):
        ranked_sorted = sorted(
            ranked, key=lambda r: r.get("score", 0), reverse=True
        )
    else:
        ranked_sorted = list(ranked)
    return ranked_sorted[: max(0, top_n)]


# ---------------------------------------------------------------------------
# Per-vertical matched_keyword_count (for compliance-flags.json detail)
# ---------------------------------------------------------------------------

def _count_matched_keywords(
    top_keywords: list[dict], evidence_tokens: list[str]
) -> int:
    """How many of the top-N keywords contain ANY of the evidence_tokens?

    Word-boundary aware so we stay consistent with find_matches. Counts each
    keyword at most once even if multiple tokens hit.
    """
    if not evidence_tokens or not top_keywords:
        return 0
    hits = 0
    for row in top_keywords:
        kw = (row.get("keyword") or "").lower()
        if not kw:
            continue
        if find_matches(kw, evidence_tokens):
            hits += 1
    return hits


# ---------------------------------------------------------------------------
# CMPL-01 — scan() returns the compliance-flags.json dict shape
# ---------------------------------------------------------------------------

def _utc_iso_now() -> str:
    """UTC ISO timestamp like `2026-05-14T18:30:00Z` (matches forecast_budget)."""
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan(
    brief_text: str,
    ranked_enriched: list[dict],
    verticals: list[dict],
    top_n: int = COMPLIANCE_SCAN_TOP_N,
) -> dict:
    """Scan brief.md (full) + top-N keywords against vertical token lists.

    Returns the compliance-flags.json dict (see RESEARCH.md "compliance-flags.json
    shape"):

        {
          "metadata": {generated_at, run_id, schema_version, scanned_top_n_keywords},
          "matched_verticals": [
              {name, evidence_tokens, evidence_sources{brief, keywords},
               matched_keyword_count, verification_url, policy_note},
              ...
          ]
        }

    run_id is set to "" here; main_with_args populates it from args.run_dir.name.

    matched_verticals[] is sorted ascending by `name` so goldens stay stable.
    """
    top_keywords = _select_top_keywords(ranked_enriched or [], top_n)
    keywords_text = "\n".join(
        (row.get("keyword") or "") for row in top_keywords
    )

    matched: list[dict] = []
    # Sorted by name for stable output ordering.
    for vertical in sorted(verticals, key=lambda v: v.get("name", "")):
        tokens = vertical.get("tokens", []) or []
        brief_hits = find_matches(brief_text or "", tokens)
        kw_hits = find_matches(keywords_text, tokens)
        if not brief_hits and not kw_hits:
            continue  # no match — skip this vertical
        evidence_tokens = sorted(set(brief_hits) | set(kw_hits))
        matched.append(
            {
                "name": vertical["name"],
                "evidence_tokens": evidence_tokens,
                "evidence_sources": {
                    "brief": brief_hits,    # already sorted unique by find_matches
                    "keywords": kw_hits,
                },
                "matched_keyword_count": _count_matched_keywords(
                    top_keywords, evidence_tokens
                ),
                "verification_url": vertical["verification_url"],
                "policy_note": vertical["policy_note"],
            }
        )

    return {
        "metadata": {
            "generated_at": _utc_iso_now(),
            "run_id": "",   # main_with_args fills this from args.run_dir.name
            "schema_version": "v1",
            "scanned_top_n_keywords": top_n,
        },
        "matched_verticals": matched,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint — writes {run_dir}/compliance-flags.json
# ---------------------------------------------------------------------------

def _default_verticals_path() -> Path:
    """Resolve references/compliance-verticals.json relative to this script.

    Script lives at:
        .claude/skills/google-ad-research/scripts/compliance_check.py
    Reference at:
        .claude/skills/google-ad-research/references/compliance-verticals.json

    `parent.parent` from this file lands on the skill root.
    """
    return (
        Path(__file__).resolve().parent.parent
        / "references"
        / "compliance-verticals.json"
    )


def main_with_args(argv: list[str]) -> int:
    """CLI: compliance_check --run-dir <path> [--verticals-path <path>].

    Reads brief.md + ranked-enriched.json + references/compliance-verticals.json.
    Writes {run_dir}/compliance-flags.json with the CMPL-01 schema.

    Exit codes:
        0  ok (file written; matched_verticals may be empty)
        2  retryable (transient disk error)
        3  fatal (missing input, malformed JSON, schema violation)
    """
    parser = argparse.ArgumentParser(
        prog="compliance_check",
        description=(
            "Scan brief.md + top-N ranked keywords against vertical token "
            "lists; emit compliance-flags.json sidecar (CMPL-01..02)."
        ),
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument(
        "--verticals-path",
        type=Path,
        default=None,
        help=(
            "Override path to compliance-verticals.json (default: skill-root/"
            "references/compliance-verticals.json)."
        ),
    )

    # argv[0]-skip heuristic — matches serp_fetch.py / volume_enrich.py /
    # bid_suggest.py / forecast_budget.py. Accept either full sys.argv or
    # args-only list.
    args_only = argv[1:] if argv and not argv[0].startswith("-") else argv
    args = parser.parse_args(args_only)

    run_dir: Path = args.run_dir
    if not run_dir.exists():
        log.error("--run-dir does not exist: %s", run_dir)
        return 3

    verticals_path: Path = args.verticals_path or _default_verticals_path()
    brief_path = run_dir / "brief.md"
    ranked_path = run_dir / "ranked-enriched.json"

    for p, label in (
        (brief_path, "brief.md"),
        (ranked_path, "ranked-enriched.json"),
        (verticals_path, "compliance-verticals.json"),
    ):
        if not p.exists():
            log.error("%s not found at %s", label, p)
            return 3

    try:
        brief_text = brief_path.read_text(encoding="utf-8")
        ranked: list[dict] = json.loads(ranked_path.read_text(encoding="utf-8"))
        verticals = load_verticals(verticals_path)
    except FileNotFoundError as exc:
        log.error("Missing input: %s", exc)
        return 3
    except json.JSONDecodeError as exc:
        log.error("Failed to parse input JSON: %s", exc)
        return 3
    except ValueError as exc:
        log.error("Schema violation in compliance-verticals.json: %s", exc)
        return 3
    except OSError as exc:
        log.error("Failed to read input file: %s", exc)
        return 2

    result: dict[str, Any] = scan(brief_text, ranked, verticals)
    result["metadata"]["run_id"] = run_dir.name

    # Atomic-ish write: write to .tmp then rename (matches forecast_budget.py).
    out_path = run_dir / "compliance-flags.json"
    try:
        tmp = out_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(out_path)
    except OSError as exc:
        log.error("Failed to write compliance-flags.json: %s", exc)
        return 2

    summary = {
        "matched_verticals_count": len(result["matched_verticals"]),
        "verticals": [v["name"] for v in result["matched_verticals"]],
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv))
