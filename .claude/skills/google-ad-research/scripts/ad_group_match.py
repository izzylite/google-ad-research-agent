# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""ad_group_match.py — Map ranked keywords to existing ad groups.

Reads:
    {run_dir}/ranked-enriched.json (or ranked.json fallback)
    {run_dir}/raw/google-ads-perf.json
    {run_dir}/raw/google-ads-search-terms.json

Writes:
    {run_dir}/ad-group-mapping.json — {matches[], unmapped_count, mapping_coverage_pct}

CLI:
    uv run ad_group_match.py --run-dir <abs>

Stdout (one JSON line on success):
    {"mapping_path": "...", "total_ranked": N, "matched_high": N,
     "matched_medium": N, "unmapped": N, "coverage_pct": float}

Exit codes:
    0  ok (including silent skip — no perf.json present, ADGM-01)
    2  retryable (disk PermissionError / OSError)
    3  fatal (--run-dir missing / ranked.json unparseable)

--- STUB (Wave 0 / Phase 11 plan 11-00) ---
Wave 1 (plan 11-02) ships build_mapping(), _jaccard(), _tokens(), _classify().
MODULE_INCOMPLETE = not hasattr(ad_group_match, "build_mapping")
"""
from __future__ import annotations

import sys

# --- Locked taxonomy (ADGM-03; frozenset assertion fails fast at import) ---
_THRESHOLDS: dict[str, float] = {
    "high": 0.7,
    "medium": 0.4,
}
assert frozenset(_THRESHOLDS) == frozenset({"high", "medium"}), (
    "_THRESHOLDS drift — ADGM-03 taxonomy changed?"
)

# --- Intent-mismatch multiplier (ADGM-02; configurable single source) ---
_DEFAULT_INTENT_MISMATCH_MULTIPLIER: float = 0.5

# --- Stopword filter (Pitfall 3; identical to Wave 1 implementation) ---
_STOPWORDS: frozenset[str] = frozenset({
    "near", "me", "the", "a", "an", "of", "in", "on", "at",
    "to", "for", "and", "or", "with", "by", "from", "is", "are",
    "best", "top",
})


def main_with_args(argv: list[str]) -> int:  # pragma: no cover — Wave 1 fills in
    raise NotImplementedError(
        "ad_group_match.py is a Wave 0 stub. Wave 1 (plan 11-02) ships build_mapping(). "
        "See .planning/phases/11-account-structure-mapping/11-02-PLAN.md"
    )


def main() -> int:  # pragma: no cover
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
