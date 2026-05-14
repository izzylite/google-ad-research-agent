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

import re as _re
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

# --- Token regex (consistent with merge_signals.py:290 — Pitfall 3) ---
_TOKEN_RE = _re.compile(r"\b[a-z]{2,}\b")

# --- Intent-marker lexicon for ad-group intent inference (open-question 3) ---
# Action-oriented service/healthcare markers added to transactional so paid-search
# ad-group bags (which heavily favor service words like "doctor", "clinic",
# "treatment", "exam", "care", "injury") infer to "transactional" instead of
# falling back to the no-marker default. Matches the dominant paid-search bid
# pattern: ad groups bidding on these terms target transactional searchers.
_INTENT_MARKERS: dict[str, frozenset[str]] = {
    "transactional": frozenset({
        "buy", "order", "book", "cheap", "delivery", "price",
        # Service/healthcare action markers (paid-search dominant intent)
        "doctor", "clinic", "treatment", "exam", "care", "injury",
        "appointment", "service", "repair", "install",
    }),
    "commercial":    frozenset({"review", "compare", "vs", "alternative", "rating"}),
    "informational": frozenset({"how", "what", "why", "guide", "tips"}),
}


def _tokens(text: str) -> frozenset[str]:
    """Lowercase, stopword-filtered, 2+letter alpha tokens.

    Same regex as merge_signals.py:290 (consistency). Stopwords applied AFTER
    extraction so "near me" → set() rather than {"near", "me"} → unintentionally
    matching every ad group with location markers (Pitfall 3).
    """
    if not text:
        return frozenset()
    raw = _TOKEN_RE.findall(text.lower())
    return frozenset(t for t in raw if t not in _STOPWORDS)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Set similarity. Empty union → 0.0 (no-data sentinel)."""
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _intent_match_multiplier(intent_a: str, intent_b: str) -> float:
    """1.0 if intent_a == intent_b (case-insensitive) else _DEFAULT_INTENT_MISMATCH_MULTIPLIER."""
    if (intent_a or "").lower() == (intent_b or "").lower():
        return 1.0
    return _DEFAULT_INTENT_MISMATCH_MULTIPLIER


def _classify(score: float) -> str:
    """Score → 'high' | 'medium' | 'low' per _THRESHOLDS (ADGM-03)."""
    if score >= _THRESHOLDS["high"]:
        return "high"
    if score >= _THRESHOLDS["medium"]:
        return "medium"
    return "low"


def _infer_ad_group_intent(token_bag: frozenset[str]) -> str:
    """Tally intent-marker token overlaps; return class with most hits.

    Empty bag → 'commercial' (least committal default).
    Non-empty bag with zero marker hits → 'commercial' (same default).
    Tie among non-zero counts → first-defined wins ('transactional').
    """
    if not token_bag:
        return "commercial"
    counts = {
        intent: len(token_bag & markers)
        for intent, markers in _INTENT_MARKERS.items()
    }
    best = max(counts, key=lambda k: counts[k])
    if counts[best] == 0:
        return "commercial"
    return best


def _build_ad_group_index(perf, search_terms):  # pragma: no cover — Task 2 fills in
    """Wave 1 Task 1 placeholder — Task 2 ships the real implementation."""
    raise NotImplementedError(
        "_build_ad_group_index is implemented in plan 11-02 Task 2 (Wave 1)."
    )


def build_mapping(ranked, perf, search_terms):  # pragma: no cover — Task 2 fills in
    """Wave 1 Task 1 placeholder — Task 2 ships the real implementation.

    Stub exists so per-function `_skip_unless_build_mapping()` guard in tests
    flips from SKIP→ACTIVE, letting Task 1's pure-helper tests execute.
    """
    raise NotImplementedError(
        "build_mapping is implemented in plan 11-02 Task 2 (Wave 1)."
    )


def main_with_args(argv: list[str]) -> int:  # pragma: no cover — Task 3 fills in
    raise NotImplementedError(
        "ad_group_match.py CLI implemented in plan 11-02 Task 3 (Wave 1). "
        "See .planning/phases/11-account-structure-mapping/11-02-PLAN.md"
    )


def main() -> int:  # pragma: no cover
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
