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
    IMPORT_OK = True
except ImportError:
    MODULE_INCOMPLETE = True
    IMPORT_OK = False

FIXTURES = Path(__file__).parent / "fixtures"


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
    assert agm._THRESHOLDS == {"high": 0.7, "medium": 0.4}
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
    """Boundary: 0.4 exactly → medium; 0.39999 → low."""
    _skip_unless_build_mapping()
    assert ad_group_match._classify(0.4) == "medium"
    assert ad_group_match._classify(0.39999) == "low"


def test_confidence_tier_high_boundary():
    """Boundary: 0.7 exactly → high; 0.69999 → medium."""
    _skip_unless_build_mapping()
    assert ad_group_match._classify(0.7) == "high"
    assert ad_group_match._classify(0.69999) == "medium"


def test_confidence_tier_low():
    _skip_unless_build_mapping()
    assert ad_group_match._classify(0.2) == "low"


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
    """coverage_pct counts (high + medium) / total_ranked; low excluded (Pitfall 7)."""
    _skip_unless_build_mapping()
    # Build a synthetic 10-row mapping: 6 high + 2 medium + 2 low.
    matches = (
        [{"keyword": f"hi {i}", "existing_ad_group": "AG", "confidence": "high",
          "score": 0.8, "reason": ""} for i in range(6)]
        + [{"keyword": f"med {i}", "existing_ad_group": "AG", "confidence": "medium",
            "score": 0.5, "reason": ""} for i in range(2)]
        + [{"keyword": f"low {i}", "existing_ad_group": "AG", "confidence": "low",
            "score": 0.2, "reason": ""} for i in range(2)]
    )
    # Stage a run_dir with ranked-enriched.json totalling 10 rows; perf/terms
    # are required by ADGM-01 contract — copy the Phase 11 fixtures.
    run_dir = tmp_path / "2026-05-14T120000Z-coverage"
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "ranked-enriched.json").write_text(
        json.dumps([{"keyword": m["keyword"], "intent": "transactional"}
                    for m in matches]),
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

    rc = ad_group_match.main_with_args(["--run-dir", str(run_dir)])
    assert rc == 0
    out = json.loads((run_dir / "ad-group-mapping.json").read_text(encoding="utf-8"))
    # 8 of 10 are high/medium → coverage_pct = 80.0 (NOT 100.0).
    assert out["mapping_coverage_pct"] == pytest.approx(80.0)


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
