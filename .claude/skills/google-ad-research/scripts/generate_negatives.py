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

Writes:
    {run_dir}/negatives.json        (overwritten with valid + deduped rows only)
    {run_dir}/raw/negatives.json    (copy of validated output — for RPRT-05)

Stdout (exactly one JSON line):
    {"valid_count": N, "error_count": N, "collision_count": N, "category_warnings": [...]}

Exit codes:
    0  valid, no collisions, all 6 categories represented
    1  enum errors fixed OR collisions removed OR category missing (operator warned)
    3  negatives.json or ranked.json missing or not valid JSON
"""
from __future__ import annotations

import argparse
import json
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
    missing_categories = check_category_coverage(deduped)

    # -- Write outputs -------------------------------------------------------
    output_json = json.dumps(deduped, indent=2, ensure_ascii=False)

    # Overwrite run_dir/negatives.json with valid+deduped rows
    negatives_path.write_text(output_json, encoding="utf-8", newline="\n")

    # Copy to run_dir/raw/negatives.json (raw/ must already exist — created by run_init.py)
    raw_dir = run_dir / "raw"
    if raw_dir.exists():
        (raw_dir / "negatives.json").write_text(output_json, encoding="utf-8", newline="\n")

    # -- Stdout summary ------------------------------------------------------
    result = {
        "valid_count": len(deduped),
        "error_count": len(errors),
        "collision_count": len(collisions),
        "category_warnings": missing_categories,
    }
    print(json.dumps(result))

    # -- Determine exit code -------------------------------------------------
    # Exit 1 if any enum errors were found, collisions were removed, or categories missing
    if errors or collisions or missing_categories:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
