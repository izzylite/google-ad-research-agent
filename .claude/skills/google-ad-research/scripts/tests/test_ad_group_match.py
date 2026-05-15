"""RED stubs for ad_group_match.py (Phase 11 Wave 0).

The module is shipped today as a MODULE_INCOMPLETE stub (plan 11-00 Task 3):
    - _THRESHOLDS / _STOPWORDS / _DEFAULT_INTENT_MISMATCH_MULTIPLIER locked
    - main_with_args() raises NotImplementedError
    - build_mapping / _jaccard / _tokens / _classify all absent

`test_module_imports` is the only test that should run today (it asserts the
stub imports cleanly and the locked constants are correct). All other tests
SKIP via the MODULE_INCOMPLETE pytestmark until Wave 1 plan 11-02 fills in
build_mapping().
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import ad_group_match  # noqa: F401
    MODULE_INCOMPLETE = not hasattr(ad_group_match, "build_mapping")
    PHASE16_INCOMPLETE = not hasattr(ad_group_match, "_build_ag_token_bag")
    IMPORT_OK = True
except ImportError:
    MODULE_INCOMPLETE = True
    PHASE16_INCOMPLETE = True
    IMPORT_OK = False

FIXTURES = Path(__file__).parent / "fixtures"


def _skip_unless_phase16() -> None:
    """Per-function guard for Phase 16 tests — skips at Wave 0 stub-time."""
    if PHASE16_INCOMPLETE:
        pytest.skip(
            "Phase 16 _build_ag_token_bag not yet implemented (plan 16-01)"
        )


def _skip_unless_build_mapping() -> None:
    """Per-function guard — every Wave-1 test calls this at its start.

    `test_module_imports` deliberately omits the guard so it runs today
    against the Wave-0 stub. All other tests skip until build_mapping ships.
    """
    if MODULE_INCOMPLETE:
        pytest.skip(
            "ad_group_match.build_mapping not yet implemented (Wave 1, plan 11-02)"
        )


# ---------------------------------------------------------------------------
# Stub-time sanity — runs TODAY against the Wave-0 stub.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not IMPORT_OK, reason="ad_group_match stub not yet shipped")
def test_module_imports():
    """Module imports cleanly; locked constants + Wave-1 public surface intact."""
    import ad_group_match as agm
    # Phase 16 recalibrated thresholds — exact values land via empirical calibration
    # in plan 16-01. test_thresholds_recalibrated_below_phase11 sentinel locks the
    # invariant (high < 0.7 AND medium < 0.4). This test just asserts shape + types.
    assert set(agm._THRESHOLDS) == {"high", "medium"}
    assert isinstance(agm._THRESHOLDS["high"], float)
    assert isinstance(agm._THRESHOLDS["medium"], float)
    assert 0.0 < agm._THRESHOLDS["medium"] < agm._THRESHOLDS["high"] < 1.0
    assert "near" in agm._STOPWORDS
    assert "me" in agm._STOPWORDS
    assert "best" in agm._STOPWORDS
    assert "top" in agm._STOPWORDS
    assert agm._DEFAULT_INTENT_MISMATCH_MULTIPLIER == 0.5
    # Wave 1 (plan 11-02) public surface — all helpers exposed.
    assert hasattr(agm, "build_mapping")
    assert hasattr(agm, "_tokens")
    assert hasattr(agm, "_jaccard")
    assert hasattr(agm, "_classify")
    assert hasattr(agm, "_intent_match_multiplier")
    assert hasattr(agm, "_infer_ad_group_intent")
    assert hasattr(agm, "_build_ad_group_index")
    assert callable(agm.main_with_args)


# ---------------------------------------------------------------------------
# ADGM-01 — Phase 8 artifacts absent → graceful skip
# ---------------------------------------------------------------------------

def test_phase8_absent_graceful_skip(tmp_path):
    """Missing raw/google-ads-perf.json → exit 0 + empty mapping with skipped_reason."""
    _skip_unless_build_mapping()
    run_dir = tmp_path / "2026-05-14T120000Z-no-phase8"
    (run_dir / "raw").mkdir(parents=True)
    # Stage a minimal ranked-enriched.json (5 rows) but no perf.json.
    ranked = [{"keyword": f"kw {i}", "intent": "transactional"} for i in range(5)]
    (run_dir / "ranked-enriched.json").write_text(json.dumps(ranked), encoding="utf-8")

    rc = ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    assert rc == 0

    mapping_path = run_dir / "ad-group-mapping.json"
    assert mapping_path.exists()
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert mapping["matches"] == []
    assert mapping["mapping_coverage_pct"] == 0.0
    assert mapping["skipped_reason"] == "phase8_artifacts_absent"
    # unmapped_count = total ranked rows (5).
    assert mapping["unmapped_count"] == 5


# ---------------------------------------------------------------------------
# ADGM-02 — similarity math
# ---------------------------------------------------------------------------

def test_similarity_math_exact_intent():
    """Identical token sets + matching intent → score 1.0 exact."""
    _skip_unless_build_mapping()
    a = frozenset({"lake", "worth", "accident", "doctor"})
    score = ad_group_match._jaccard(a, a) * 1.0
    assert score == 1.0


def test_similarity_math_intent_mismatch():
    """jaccard=0.6 × intent_mismatch_multiplier (0.5) = 0.3."""
    _skip_unless_build_mapping()
    # Build two sets with jaccard exactly 0.6 — 3 shared / 5 union.
    a = frozenset({"lake", "worth", "accident"})
    b = frozenset({"lake", "worth", "accident", "exam", "fast"})
    assert ad_group_match._jaccard(a, b) == pytest.approx(0.6)
    score = ad_group_match._jaccard(a, b) * ad_group_match._DEFAULT_INTENT_MISMATCH_MULTIPLIER
    assert score == pytest.approx(0.3)


def test_stopword_filter_active():
    """`_tokens` strips 'near'/'me' (Pitfall 3) — only meaningful tokens remain."""
    _skip_unless_build_mapping()
    tokens = ad_group_match._tokens("doctor near me lake worth")
    assert tokens == frozenset({"doctor", "lake", "worth"})


# ---------------------------------------------------------------------------
# ADGM-03 — confidence tier classifier + boundary behaviour
# ---------------------------------------------------------------------------

def test_confidence_tier_high():
    _skip_unless_build_mapping()
    assert ad_group_match._classify(0.75) == "high"


def test_confidence_tier_medium_boundary():
    """Boundary: _THRESHOLDS['medium'] exactly → medium; just below → low.

    Phase 16 recalibrated thresholds — test follows _THRESHOLDS values dynamically
    (rather than hardcoding 0.4) so the boundary semantics are preserved across
    calibration deltas. The Phase 11 boundary semantics (== threshold → medium,
    < threshold → low) is the actual invariant under test.
    """
    _skip_unless_build_mapping()
    med = ad_group_match._THRESHOLDS["medium"]
    hi = ad_group_match._THRESHOLDS["high"]
    assert ad_group_match._classify(med) == "medium"
    assert ad_group_match._classify(med - 1e-5) == "low"
    # Sanity: med strictly less than hi so the medium tier is non-degenerate.
    assert med < hi


def test_confidence_tier_high_boundary():
    """Boundary: _THRESHOLDS['high'] exactly → high; just below → medium.

    Phase 16 recalibrated thresholds — test follows _THRESHOLDS values dynamically
    (rather than hardcoding 0.7) so the boundary semantics are preserved across
    calibration deltas. The Phase 11 boundary semantics (== threshold → high,
    < threshold → medium) is the actual invariant under test.
    """
    _skip_unless_build_mapping()
    hi = ad_group_match._THRESHOLDS["high"]
    assert ad_group_match._classify(hi) == "high"
    assert ad_group_match._classify(hi - 1e-5) == "medium"


def test_confidence_tier_low():
    """Score strictly below medium threshold → low."""
    _skip_unless_build_mapping()
    med = ad_group_match._THRESHOLDS["medium"]
    assert ad_group_match._classify(med / 2.0) == "low"


# ---------------------------------------------------------------------------
# ADGM-04 — mapping shape + coverage math
# ---------------------------------------------------------------------------

def test_mapping_shape_keys():
    """ad-group-mapping.json carries the locked schema (incl. row keys)."""
    _skip_unless_build_mapping()
    mapping = json.loads(
        (FIXTURES / "ad-group-mapping-60pct.json").read_text(encoding="utf-8")
    )
    required_top = {"matches", "unmapped_count", "mapping_coverage_pct", "computed_at"}
    assert required_top <= set(mapping.keys())
    assert mapping["matches"], "fixture must have at least one match row"
    required_row = {"keyword", "existing_ad_group", "confidence", "score", "reason"}
    assert required_row <= set(mapping["matches"][0].keys())


def test_coverage_pct_high_plus_medium_only(tmp_path):
    """coverage_pct counts (high + medium) / total_ranked; low excluded (Pitfall 7).

    Crafted against the Phase 11 fixture so the math is deterministic:
    "Accident Exams – Lake Worth" token bag is the union of its 4 search
    terms (Pitfall 3 stopwords applied) =
        {car, accident, doctor, lake, worth, exam, clinic, palm, beach, auto}
    The bag has 10 tokens; inferred intent is `transactional` (clinic/doctor/
    exam markers ≥3). All 10 ranked keywords below use intent=transactional
    so intent_multiplier=1.0 and score == raw_jaccard.

    Six keywords share 7 tokens with the 10-token bag → jaccard 7/10=0.70 → high.
    Two keywords share 5 / 4 tokens                  → jaccard 0.50 / 0.40 → medium.
    Two unrelated keywords share 0 tokens             → jaccard 0.0    → low.
    Expected coverage = (6+2)/10 * 100 = 80.0%.
    """
    _skip_unless_build_mapping()

    # 6 HIGH: 7-token subsets of the AELW bag (raw_jaccard = 7/10 = 0.70 → high)
    hi_keywords = [
        "car accident doctor lake worth exam clinic",
        "car accident doctor lake worth exam palm",
        "car accident doctor lake worth exam beach",
        "car accident doctor lake worth exam auto",
        "car accident doctor lake worth clinic palm",
        "car accident doctor lake worth clinic auto",
    ]
    # 2 MEDIUM: 5- and 4-token subsets (raw_jaccard = 0.50 and 0.40 → medium)
    med_keywords = [
        "car accident doctor lake worth",   # 5/10 = 0.50
        "car accident doctor lake",          # 4/10 = 0.40
    ]
    # 2 LOW: tokens with zero overlap against any ENABLED ad-group bag
    low_keywords = [
        "tomato sandwich recipe",
        "quantum mechanics tutorial",
    ]
    ranked = (
        [{"keyword": k, "intent": "transactional"} for k in hi_keywords]
        + [{"keyword": k, "intent": "transactional"} for k in med_keywords]
        + [{"keyword": k, "intent": "transactional"} for k in low_keywords]
    )

    run_dir = tmp_path / "2026-05-14T120000Z-coverage"
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "ranked-enriched.json").write_text(
        json.dumps(ranked), encoding="utf-8",
    )
    (run_dir / "raw" / "google-ads-perf.json").write_text(
        (FIXTURES / "google-ads-perf-phase11.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (run_dir / "raw" / "google-ads-search-terms.json").write_text(
        (FIXTURES / "google-ads-search-terms-phase11.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    assert rc == 0
    out = json.loads((run_dir / "ad-group-mapping.json").read_text(encoding="utf-8"))
    # 8 of 10 are high/medium → coverage_pct = 80.0 (NOT 100.0). HARD INVARIANT.
    assert out["mapping_coverage_pct"] == pytest.approx(80.0)
    # Per-tier sanity: 8 of 10 land in high+medium, 2 in low.
    # Note: exact high vs medium split is calibration-dependent (Phase 16 recalibrated
    # _THRESHOLDS — a 0.50-score keyword may classify high under lower hi-threshold
    # whereas Phase 11's 0.7 hi-threshold placed it at medium). The COVERAGE invariant
    # (high+medium total = 8/10 = 80%) is what this test ultimately enforces.
    tiers = [m["confidence"] for m in out["matches"]]
    assert tiers.count("high") + tiers.count("medium") == 8
    assert tiers.count("low") == 2
    # Garbage keywords must still classify as low (C5 — zero-overlap sanity).
    low_matches = [m for m in out["matches"] if m["confidence"] == "low"]
    low_kws = {m["keyword"] for m in low_matches}
    assert "tomato sandwich recipe" in low_kws
    assert "quantum mechanics tutorial" in low_kws


# ---------------------------------------------------------------------------
# ADGM bucketing rules — disabled groups, name keying, Unicode dashes
# ---------------------------------------------------------------------------

def test_disabled_ad_groups_skipped(tmp_path):
    """ad_groups[] with status='REMOVED' must NOT surface as a match candidate."""
    _skip_unless_build_mapping()
    run_dir = tmp_path / "2026-05-14T120000Z-disabled"
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "ranked-enriched.json").write_text(
        json.dumps([{"keyword": "old legacy term", "intent": "transactional"}]),
        encoding="utf-8",
    )
    (run_dir / "raw" / "google-ads-perf.json").write_text(
        (FIXTURES / "google-ads-perf-phase11.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (run_dir / "raw" / "google-ads-search-terms.json").write_text(
        (FIXTURES / "google-ads-search-terms-phase11.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    mapping = json.loads(
        (run_dir / "ad-group-mapping.json").read_text(encoding="utf-8")
    )
    for m in mapping["matches"]:
        assert m["existing_ad_group"] != "Old Legacy Ad Group", (
            "REMOVED ad group leaked into matches"
        )


def test_token_bag_keyed_by_ad_group_name(tmp_path):
    """search_terms.json keys on ad_group_name (NOT ad_group_id) — Pitfall 1."""
    _skip_unless_build_mapping()
    run_dir = tmp_path / "2026-05-14T120000Z-keying"
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "ranked-enriched.json").write_text(
        json.dumps([{"keyword": "car accident doctor lake worth",
                     "intent": "transactional"}]),
        encoding="utf-8",
    )
    (run_dir / "raw" / "google-ads-perf.json").write_text(
        (FIXTURES / "google-ads-perf-phase11.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # Re-use Phase 11 search_terms fixture (no ad_group_id field present).
    (run_dir / "raw" / "google-ads-search-terms.json").write_text(
        (FIXTURES / "google-ads-search-terms-phase11.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    assert rc == 0
    mapping = json.loads(
        (run_dir / "ad-group-mapping.json").read_text(encoding="utf-8")
    )
    # Best match should be "Accident Exams – Lake Worth" (token bag bucketed by name).
    assert mapping["matches"], "expected at least one match"
    best = mapping["matches"][0]
    assert best["existing_ad_group"] == "Accident Exams – Lake Worth"


def test_unicode_dashes_preserved(tmp_path):
    """Unicode en-dash (U+2013) in existing_ad_group round-trips byte-for-byte."""
    _skip_unless_build_mapping()
    run_dir = tmp_path / "2026-05-14T120000Z-unicode"
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "ranked-enriched.json").write_text(
        json.dumps([{"keyword": "car accident doctor lake worth",
                     "intent": "transactional"}]),
        encoding="utf-8",
    )
    (run_dir / "raw" / "google-ads-perf.json").write_text(
        (FIXTURES / "google-ads-perf-phase11.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (run_dir / "raw" / "google-ads-search-terms.json").write_text(
        (FIXTURES / "google-ads-search-terms-phase11.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    raw_bytes = (run_dir / "ad-group-mapping.json").read_bytes()
    # U+2013 is the en-dash; UTF-8 encoding = 0xE2 0x80 0x93.
    assert b"\xe2\x80\x93" in raw_bytes, "en-dash byte sequence missing from mapping"
    mapping = json.loads(raw_bytes.decode("utf-8"))
    # The literal en-dash character must be present in the round-tripped name.
    en_dashed = [
        m for m in mapping["matches"]
        if "Accident Exams – Lake Worth" == m["existing_ad_group"]
    ]
    assert en_dashed, "existing_ad_group lost en-dash byte fidelity"


# ---------------------------------------------------------------------------
# ADGM-07..11 — Phase 16 token-bag enrichment
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason=(
        "ADGM-11 deferred to plan 16-02 (operator decision option-a, 2026-05-15). "
        "Structural Jaccard ceiling: Lake Worth's enriched AG token bag has ~34 "
        "tokens (name ∪ kw_criteria ∪ top-10 search-terms) whereas typical ranked "
        "queries carry only 4-6 tokens. Best-case jaccard caps at ~0.15-0.25 — "
        "lowering the medium threshold below the calibration cap floor (0.10) "
        "breaks C5 (garbage keywords like 'tomato sandwich' classify as medium). "
        "At locked thresholds {high: 0.30, medium: 0.10}: observed coverage 16.67% "
        "(11 medium / 66 ranked). Phase 11 80% invariant + zero-overlap garbage "
        "guard both preserved. Closing the gap requires a structural change "
        "(per-source max-jaccard instead of full-union jaccard, OR token bag "
        "subsampling) — scheduled for plan 16-02 follow-up."
    ),
    strict=True,
)
def test_lake_worth_coverage_floor(tmp_path):
    """ADGM-11 — Lake Worth golden run yields mapping_coverage_pct >= 50%.

    XFAIL — option-a deferral to plan 16-02. See marker rationale above.
    """
    _skip_unless_phase16()
    run_dir = tmp_path / "2026-05-15T120000Z-lake-worth-golden"
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "ranked-enriched.json").write_text(
        (FIXTURES / "ranked_lake_worth.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for src, dst in [
        ("google-ads-perf-lake-worth.json", "google-ads-perf.json"),
        ("google-ads-search-terms-lake-worth.json", "google-ads-search-terms.json"),
        ("google-ads-keywords-lake-worth.json", "google-ads-keywords.json"),
    ]:
        (run_dir / "raw" / dst).write_text(
            (FIXTURES / src).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    rc = ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    assert rc == 0
    out = json.loads((run_dir / "ad-group-mapping.json").read_text(encoding="utf-8"))
    golden = json.loads(
        (FIXTURES / "golden_mapping_lake_worth.json").read_text(encoding="utf-8")
    )
    assert out["mapping_coverage_pct"] >= golden["mapping_coverage_pct_floor"], (
        f"Phase 16 coverage {out['mapping_coverage_pct']}% < floor "
        f"{golden['mapping_coverage_pct_floor']}% — token-bag enrichment regression"
    )


def test_backward_compat_keywords_absent(tmp_path):
    """ADGM-08 — keywords.json absent → graceful degrade (<=30% coverage)."""
    _skip_unless_phase16()
    run_dir = tmp_path / "2026-05-15T120000Z-no-keywords-fallback"
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "ranked-enriched.json").write_text(
        (FIXTURES / "ranked_lake_worth.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # Stage perf + search-terms — but NOT keywords.json
    (run_dir / "raw" / "google-ads-perf.json").write_text(
        (FIXTURES / "google-ads-perf-lake-worth.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (run_dir / "raw" / "google-ads-search-terms.json").write_text(
        (FIXTURES / "google-ads-search-terms-lake-worth.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    rc = ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    assert rc == 0
    out = json.loads((run_dir / "ad-group-mapping.json").read_text(encoding="utf-8"))
    # Without kw_criteria, bag = ag_name ∪ search-terms only. Ceiling at 30%.
    assert 0.0 <= out["mapping_coverage_pct"] <= 30.0, (
        f"Backward-compat path should NOT inflate coverage; got "
        f"{out['mapping_coverage_pct']}%"
    )


def test_reason_field_per_source_attribution(tmp_path):
    """ADGM-09 — match.reason carries name=/kw-criterion=/search-term= substrings."""
    _skip_unless_phase16()
    run_dir = tmp_path / "2026-05-15T120000Z-reason-shape"
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "ranked-enriched.json").write_text(
        (FIXTURES / "ranked_lake_worth.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for src, dst in [
        ("google-ads-perf-lake-worth.json", "google-ads-perf.json"),
        ("google-ads-search-terms-lake-worth.json", "google-ads-search-terms.json"),
        ("google-ads-keywords-lake-worth.json", "google-ads-keywords.json"),
    ]:
        (run_dir / "raw" / dst).write_text(
            (FIXTURES / src).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    out = json.loads((run_dir / "ad-group-mapping.json").read_text(encoding="utf-8"))
    high_med = [m for m in out["matches"] if m["confidence"] in ("high", "medium")]
    assert high_med, "expected at least one high/medium match on Lake Worth golden"
    sample = high_med[0]["reason"]
    assert "name=" in sample, f"reason missing per-source attribution: {sample!r}"
    assert "kw-criterion=" in sample, f"reason missing per-source attribution: {sample!r}"
    assert "search-term=" in sample, f"reason missing per-source attribution: {sample!r}"


def test_token_bag_unions_all_three_sources():
    """ADGM-07 — _build_ag_token_bag unions ag_name ∪ kw_criteria ∪ search_terms."""
    _skip_unless_phase16()
    bag = ad_group_match._build_ag_token_bag(
        ag_name="Accident Exams – Lake Worth",
        kw_criteria=[
            {"ad_group_name": "Accident Exams – Lake Worth",
             "ad_group_criterion": {"keyword": {"text": "auto accident doctor"}}}
        ],
        search_terms=[
            {"ad_group_name": "Accident Exams – Lake Worth",
             "search_term": "car crash clinic", "clicks": 10, "impressions": 100}
        ],
    )
    # AG name contributes: accident, exams, lake, worth (stopword filter active)
    # kw_criteria contributes: auto, accident, doctor
    # search_terms contributes: car, crash, clinic
    assert {"accident", "exams", "lake", "worth"} <= bag, "AG name tokens missing"
    assert {"auto", "doctor"} <= bag, "kw_criterion tokens missing"
    assert {"car", "crash", "clinic"} <= bag, "search-term tokens missing"


def test_thresholds_recalibrated_below_phase11():
    """ADGM-10 sentinel — fails loud if Wave 2 reverts the calibration delta.

    Phase 11 ships 0.7/0.4. Phase 16 must tighten — exact values land via
    empirical calibration in plan 16-01. This sentinel just asserts the
    delta was applied (high < 0.7) so silent revert is caught. NO skip guard —
    must run TODAY against the Wave-0 stub and FAIL loudly to confirm TDD wiring.
    """
    assert ad_group_match._THRESHOLDS["high"] < 0.7, (
        f"Phase 16 ADGM-10 calibration not applied; high still at "
        f"{ad_group_match._THRESHOLDS['high']}"
    )
    assert ad_group_match._THRESHOLDS["medium"] < 0.4, (
        f"Phase 16 ADGM-10 calibration not applied; medium still at "
        f"{ad_group_match._THRESHOLDS['medium']}"
    )
