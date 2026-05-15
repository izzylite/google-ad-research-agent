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
    # Phase 16 plan 16-01 option-a — locked at loosening cap floor.
    # Best achievable {high, medium} pair under calibration_protocol constraints:
    # - C2 Phase 11 80% coverage PRESERVED (HARD invariant)
    # - C4 sentinels (high < 0.7 AND medium < 0.4) PASS
    # - C5 garbage keywords ("tomato sandwich") stay classified as "low"
    # - C1 Lake Worth >= 50% UNREACHABLE within cap — observed 16.7% at this floor.
    # Operator chose option-a (accept miss, defer ADGM-11 to plan 16-02 follow-up).
    # Root cause: structural Jaccard ceiling — Lake Worth's enriched 34-token AG bag
    # vs typical 4-6-token ranked queries caps jaccard at ~0.15-0.25; lowering
    # medium below 0.10 breaks C5 (garbage matches). See 16-01-SUMMARY.md.
    "high": 0.30,
    "medium": 0.10,
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


from datetime import datetime, timezone
from typing import Any


def _now_iso_z() -> str:
    """UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` form (ad-group-mapping.json contract)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_ag_token_bag(
    ag_name: str,
    kw_criteria: list[dict] | None,
    search_terms: list[dict] | None,
    top_n_terms: int = 10,
) -> frozenset[str]:
    """Phase 16 (ADGM-07): per-AG token bag = name ∪ kw_criteria ∪ top-N search-terms.

    Sources:
      1. _tokens(ag_name) — always (even if "" → empty)
      2. _tokens(kw.ad_group_criterion.keyword.text) for kw in kw_criteria
         where kw.ad_group_criterion.status != "REMOVED" (ADGM-07)
      3. _tokens(st.search_term) for st in top-N search_terms by clicks desc
         (tiebreak impressions desc; drop impressions==0) (ADGM-07 top-N cap)

    Degrades gracefully (ADGM-08): kw_criteria None/empty → bag = name ∪ search-terms;
    search_terms None/empty → bag = name ∪ kw_criteria; all empty → empty frozenset
    (caller drops empty bags — Pitfall 6 preserved).
    """
    name_tokens = _tokens(ag_name or "")

    crit_tokens: set[str] = set()
    for kw in (kw_criteria or []):
        crit = kw.get("ad_group_criterion") or {}
        status = (crit.get("status") or "").upper()
        if status == "REMOVED":
            continue
        text = ((crit.get("keyword") or {}).get("text")) or ""
        crit_tokens |= _tokens(text)

    # Search terms — filter zero-impression, sort clicks desc / impressions desc, top-N
    filtered = [
        st for st in (search_terms or [])
        if (st.get("impressions") or 0) > 0
    ]
    filtered.sort(
        key=lambda st: ((st.get("clicks") or 0), (st.get("impressions") or 0)),
        reverse=True,
    )
    term_tokens: set[str] = set()
    for st in filtered[:top_n_terms]:
        term_tokens |= _tokens(st.get("search_term") or "")

    return frozenset(name_tokens | crit_tokens | term_tokens)


def _build_ad_group_index(
    perf: dict,
    search_terms: dict,
    keywords: dict | None = None,
) -> dict[str, dict[str, Any]]:
    """Build {ad_group_name: {token_bag, name_tokens, criterion_tokens,
    search_term_tokens, inferred_intent, status}} from Phase 8/14 raws.

    Phase 16 (ADGM-07/08): per-AG bag = name ∪ kw_criteria ∪ top-N search-terms.
    Backward-compat: keywords=None → bag = name ∪ search-terms only (Phase 11 + name).

    - Filters perf.ad_groups[] to status='ENABLED' (REMOVED dropped).
    - Buckets keywords.items[] + search_terms.items[] by ad_group_name (Pitfall 1).
    - Drops ad groups with empty token bags (Pitfall 6).
    - Preserves original ad_group_name string byte-for-byte (Pitfall 2 — Unicode).
    """
    # 1. Enumerate ENABLED ad groups from perf.ad_groups[]
    enabled_names: set[str] = set()
    for ag in (perf or {}).get("ad_groups", []) or []:
        name = ag.get("name")
        status = (ag.get("status") or "").upper()
        if name and status == "ENABLED":
            enabled_names.add(name)

    # 2. Bucket kw_criteria + search_terms by ad_group_name (Pitfall 1 — name, NOT id)
    kw_by_ag: dict[str, list[dict]] = {}
    for item in (keywords or {}).get("items", []) or []:
        ag_name = item.get("ad_group_name")
        if not ag_name or ag_name not in enabled_names:
            continue
        kw_by_ag.setdefault(ag_name, []).append(item)

    st_by_ag: dict[str, list[dict]] = {}
    for item in (search_terms or {}).get("items", []) or []:
        ag_name = item.get("ad_group_name")
        if not ag_name or ag_name not in enabled_names:
            continue
        st_by_ag.setdefault(ag_name, []).append(item)

    # 3. Build the index — per-AG Phase 16 token-bag (drop empty bags Pitfall 6)
    index: dict[str, dict[str, Any]] = {}
    for ag_name in enabled_names:
        kw_for_ag = kw_by_ag.get(ag_name) or []
        st_for_ag = st_by_ag.get(ag_name) or []

        # Compute partial sets for per-source reason-field attribution
        name_tokens = _tokens(ag_name)
        crit_tokens: set[str] = set()
        for kw in kw_for_ag:
            crit = kw.get("ad_group_criterion") or {}
            status = (crit.get("status") or "").upper()
            if status == "REMOVED":
                continue
            text = ((crit.get("keyword") or {}).get("text")) or ""
            crit_tokens |= _tokens(text)

        filtered = [
            st for st in st_for_ag if (st.get("impressions") or 0) > 0
        ]
        filtered.sort(
            key=lambda st: ((st.get("clicks") or 0), (st.get("impressions") or 0)),
            reverse=True,
        )
        term_tokens: set[str] = set()
        for st in filtered[:10]:
            term_tokens |= _tokens(st.get("search_term") or "")

        full_bag = frozenset(name_tokens | crit_tokens | term_tokens)
        if not full_bag:
            continue
        index[ag_name] = {
            "token_bag": full_bag,
            "name_tokens": name_tokens,
            "criterion_tokens": frozenset(crit_tokens),
            "search_term_tokens": frozenset(term_tokens),
            "inferred_intent": _infer_ad_group_intent(full_bag),
            "status": "ENABLED",
        }
    return index


def build_mapping(
    ranked: list[dict],
    perf: dict,
    search_terms: dict,
    keywords: dict | None = None,
) -> dict[str, Any]:
    """Compute the ad-group-mapping.json body. See module docstring for schema.

    Algorithm (ADGM-02 + ADGM-11):
        Phase 16 Plan 16-04 (ADGM-11): per-source max-Jaccard. raw_j =
        max(name_j, crit_j, term_j) replaces the previous full-union
        jaccard(kw, full_bag) to address the bag-vs-query token-count asymmetry
        observed on real Lake Worth data (see 16-04-SUMMARY.md). The
        intent_multiplier still applies multiplicatively to the max:
            score = max(name_j, crit_j, term_j) * intent_multiplier
            intent_multiplier = 1.0 if kw.intent == ag.inferred_intent else 0.5

    Confidence tiers (ADGM-03):
        high   >= _THRESHOLDS["high"]
        medium >= _THRESHOLDS["medium"]
        low    <  _THRESHOLDS["medium"]  →  existing_ad_group=None

    Coverage % (Pitfall 7):
        (high + medium count) / total_ranked * 100  —  low EXCLUDED
    """
    index = _build_ad_group_index(perf, search_terms, keywords)
    matches: list[dict[str, Any]] = []
    unmapped_count = 0
    match_count = 0  # high + medium only (Pitfall 7)

    for kw in ranked or []:
        kw_text = (kw.get("keyword") or "").strip()
        kw_intent = (kw.get("intent") or "").lower()
        kw_tokens = _tokens(kw_text)

        best_score = 0.0
        best_ag_name: str | None = None
        best_jaccard = 0.0
        best_intent_match = False
        best_partials: tuple[float, float, float] = (0.0, 0.0, 0.0)

        for ag_name, ag in index.items():
            # Phase 16 Plan 16-04 (ADGM-11): compute per-source partials ONCE per
            # (kw, ag) — power both scoring AND reason-field rendering. Replaces
            # the previous full-union _jaccard(kw_tokens, ag["token_bag"]) call.
            name_j = _jaccard(kw_tokens, ag["name_tokens"])
            crit_j = _jaccard(kw_tokens, ag["criterion_tokens"])
            term_j = _jaccard(kw_tokens, ag["search_term_tokens"])
            raw_j = max(name_j, crit_j, term_j)
            if raw_j == 0.0:
                continue
            intent_match = kw_intent == ag["inferred_intent"]
            score = raw_j * (
                1.0 if intent_match else _DEFAULT_INTENT_MISMATCH_MULTIPLIER
            )
            if score > best_score:
                best_score = score
                best_ag_name = ag_name
                best_jaccard = raw_j
                best_intent_match = intent_match
                best_partials = (name_j, crit_j, term_j)

        confidence = _classify(best_score)
        if confidence == "low":
            unmapped_count += 1
            resolved_ag = None
            if best_jaccard > 0.0:
                # Borderline-low audit: keep per-source attribution.
                name_j, crit_j, term_j = best_partials
                reason = (
                    f"jaccard={best_jaccard:.2f} "
                    f"(name={name_j:.2f} kw-criterion={crit_j:.2f} search-term={term_j:.2f}) "
                    f"intent_match={best_intent_match}"
                )
            else:
                reason = (
                    f"jaccard={best_jaccard:.2f} intent_match={best_intent_match}"
                )
        else:
            match_count += 1
            resolved_ag = best_ag_name
            # Per-source Jaccards (ADGM-09) — from cached best_partials (Plan 16-04)
            name_j, crit_j, term_j = best_partials
            reason = (
                f"jaccard={best_jaccard:.2f} "
                f"(name={name_j:.2f} kw-criterion={crit_j:.2f} search-term={term_j:.2f}) "
                f"intent_match={best_intent_match}"
            )

        matches.append({
            "keyword": kw_text,
            "existing_ad_group": resolved_ag,
            "confidence": confidence,
            "score": round(best_score, 4),
            "reason": reason,
        })

    total = len(matches)
    coverage_pct = round((match_count / total * 100.0), 2) if total else 0.0

    return {
        "matches": matches,
        "unmapped_count": unmapped_count,
        "mapping_coverage_pct": coverage_pct,
        "computed_at": _now_iso_z(),
        "skipped_reason": None,
    }


import argparse
import json
from pathlib import Path

# stderr logging — reuse the project-wide configure_logger when available
try:
    from lib.log import configure_logger  # type: ignore
except ImportError:  # pragma: no cover — defensive fallback for ad-hoc invocation
    import logging

    def configure_logger(name: str, level: str = "INFO"):
        logging.basicConfig(stream=sys.stderr, level=level)
        return logging.getLogger(name)


def main_with_args(argv: list[str]) -> int:
    """CLI entry. --run-dir required. Phase 8 absent → exit 0 with skipped sidecar."""
    parser = argparse.ArgumentParser(
        description="Map ranked keywords to existing Google Ads ad groups (ADGM-01..04).",
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    log = configure_logger("ad_group_match")
    run_dir: Path = args.run_dir

    if not run_dir.exists():
        print(
            json.dumps({"error": f"--run-dir does not exist: {run_dir}"}),
            file=sys.stderr,
        )
        return 3

    raw_dir = run_dir / "raw"
    perf_path = raw_dir / "google-ads-perf.json"
    terms_path = raw_dir / "google-ads-search-terms.json"
    ranked_path = run_dir / "ranked-enriched.json"
    if not ranked_path.exists():
        ranked_path = run_dir / "ranked.json"

    if not ranked_path.exists():
        print(
            json.dumps({
                "error": f"ranked.json/ranked-enriched.json absent in {run_dir}",
            }),
            file=sys.stderr,
        )
        return 3

    try:
        ranked_raw = json.loads(ranked_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(
            json.dumps({"error": f"ranked.json unparseable: {exc}"}),
            file=sys.stderr,
        )
        return 3

    # ranked.json schema: list[dict] OR {"keywords": [...]}
    if isinstance(ranked_raw, dict):
        ranked = ranked_raw.get("keywords", []) or []
    else:
        ranked = ranked_raw or []

    mapping_path = run_dir / "ad-group-mapping.json"

    # ADGM-01: graceful skip when Phase 8 artifacts are absent (Pitfall 6)
    if not perf_path.exists() or not terms_path.exists():
        log.info("Phase 8 artifacts absent — skipping ad-group mapping")
        mapping = {
            "matches": [],
            "unmapped_count": len(ranked),
            "mapping_coverage_pct": 0.0,
            "computed_at": _now_iso_z(),
            "skipped_reason": "phase8_artifacts_absent",
        }
        try:
            mapping_path.write_text(
                json.dumps(mapping, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except (PermissionError, OSError) as exc:
            print(
                json.dumps({"error": f"write failed: {exc}"}),
                file=sys.stderr,
            )
            return 2
        print(json.dumps({
            "mapping_path": str(mapping_path),
            "skipped": True,
            "coverage_pct": 0.0,
        }))
        return 0

    # Happy path — load Phase 8 raws and compute the mapping
    try:
        perf = json.loads(perf_path.read_text(encoding="utf-8"))
        search_terms = json.loads(terms_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(
            json.dumps({"error": f"Phase 8 raw unparseable: {exc}"}),
            file=sys.stderr,
        )
        return 3

    # Phase 16 (ADGM-08): optional Phase 14 keywords.json — graceful absence
    keywords_path = raw_dir / "google-ads-keywords.json"
    keywords: dict | None = None
    if keywords_path.exists():
        try:
            keywords = json.loads(keywords_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            # Soft-fail: log + continue with keywords=None (graceful degrade)
            log.warning(
                f"google-ads-keywords.json unparseable, falling back to "
                f"name+search-terms only: {exc}"
            )

    mapping = build_mapping(ranked, perf, search_terms, keywords)

    try:
        # ensure_ascii=False so Unicode dashes write byte-for-byte (Pitfall 2)
        mapping_path.write_text(
            json.dumps(mapping, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except (PermissionError, OSError) as exc:
        print(
            json.dumps({"error": f"write failed: {exc}"}),
            file=sys.stderr,
        )
        return 2

    # Stdout summary (one JSON line)
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    for m in mapping["matches"]:
        confidence_counts[m["confidence"]] += 1
    print(json.dumps({
        "mapping_path": str(mapping_path),
        "total_ranked": len(mapping["matches"]),
        "matched_high": confidence_counts["high"],
        "matched_medium": confidence_counts["medium"],
        "unmapped": confidence_counts["low"],
        "coverage_pct": mapping["mapping_coverage_pct"],
    }))
    return 0


def main() -> int:  # pragma: no cover
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
