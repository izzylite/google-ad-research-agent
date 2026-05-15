"""Tests for perf_synth.py — synth + negative cross-reference logic."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import perf_synth
    PS_MISSING = False
except ImportError:
    PS_MISSING = True

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture_json(name: str):
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _skip_unless_cross_ref_positives() -> None:
    """Per-function guard — Wave 1 plan 14-02 lands perf_synth.cross_ref_positives."""
    if PS_MISSING:
        pytest.skip("perf_synth not yet implemented")
    if not hasattr(perf_synth, "cross_ref_positives"):
        pytest.skip(
            "Wave 1 14-02 not yet landed: perf_synth.cross_ref_positives missing"
        )


def test_norm_neg_strips_match_type_punctuation():
    if PS_MISSING:
        pytest.skip("perf_synth not yet implemented")
    assert perf_synth._norm_neg('"lawyer"') == "lawyer"
    assert perf_synth._norm_neg('[exact match]') == "exact match"
    assert perf_synth._norm_neg('+modified +broad') == "modified broad"
    assert perf_synth._norm_neg('  LawSuit  ') == "lawsuit"


def test_synth_negatives_sync_flags_overlap():
    if PS_MISSING:
        pytest.skip("perf_synth not yet implemented")
    ours = [
        {"keyword": "lawyer", "tier": "Strong", "category": "wrong-audience", "justification": ""},
        {"keyword": "free", "tier": "Strong", "category": "free-DIY-tutorial", "justification": ""},
        {"keyword": "diy", "tier": "Considered", "category": "free-DIY-tutorial", "justification": ""},
    ]
    existing = [
        {"keyword": "lawyer", "level": "campaign"},
        {"keyword": '"free"', "level": "ad_group"},  # quoted variant
    ]
    sync = perf_synth.synth_negatives_sync(ours, existing)
    assert sync["stats"]["already_covered"] == 2  # lawyer + free
    assert sync["stats"]["new_to_add"] == 1  # diy
    assert sync["stats"]["our_total"] == 3
    assert any(n["keyword"] == "lawyer" for n in sync["already_in_account"])
    assert any(n["keyword"] == "diy" for n in sync["new_candidates"])


def test_synth_negatives_sync_buckets_by_tier():
    if PS_MISSING:
        pytest.skip("perf_synth not yet implemented")
    ours = [
        {"keyword": "alpha", "tier": "Strong", "category": "x", "justification": ""},
        {"keyword": "beta", "tier": "Strong", "category": "x", "justification": ""},
        {"keyword": "gamma", "tier": "Considered", "category": "x", "justification": ""},
        {"keyword": "delta", "tier": "Investigate", "category": "x", "justification": ""},
    ]
    sync = perf_synth.synth_negatives_sync(ours, [])
    assert len(sync["new_by_tier"]["Strong"]) == 2
    assert len(sync["new_by_tier"]["Considered"]) == 1
    assert len(sync["new_by_tier"]["Investigate"]) == 1


def test_synth_account_perf_separates_converted_vs_lossy():
    if PS_MISSING:
        pytest.skip("perf_synth not yet implemented")
    perf = {
        "campaigns": [
            {"name": "X", "cost_usd": 100, "clicks": 10, "conversions": 2,
             "conversions_value": 400, "roas": 4.0, "cpa_usd": 50, "status": "ENABLED"},
            {"name": "Y", "cost_usd": 50, "clicks": 5, "conversions": 0,
             "conversions_value": 0, "roas": None, "cpa_usd": None, "status": "ENABLED"},
        ],
        "ad_groups": [],
        "horizon_days": 30,
        "customer_id": "test",
    }
    terms = {
        "items": [
            {"search_term": "buy widgets", "conversions": 1.0, "clicks": 5,
             "cost_usd": 20, "campaign_name": "X"},
            {"search_term": "blue widgets", "conversions": 0, "clicks": 8,
             "cost_usd": 30, "campaign_name": "Y"},
            {"search_term": "no impressions", "conversions": 0, "clicks": 0,
             "cost_usd": 0, "campaign_name": "Y"},
        ],
    }
    out = perf_synth.synth_account_perf(perf, terms)
    assert len(out["converted_search_terms"]) == 1
    assert out["converted_search_terms"][0]["search_term"] == "buy widgets"
    # Only "blue widgets" is lossy (clicks > 0 but no conv); "no impressions" excluded
    assert len(out["lossy_search_terms"]) == 1
    assert out["lossy_search_terms"][0]["search_term"] == "blue widgets"
    assert out["totals"]["spend_usd"] == 150.0
    assert out["totals"]["conversions"] == 2.0


# ===========================================================================
# Phase 14 Wave 0 — cross_ref_positives RED stubs (POS-07)
#
# Wave 1 plan 14-02 lands `cross_ref_positives(ranked, existing_kws) -> dict`
# on perf_synth. Each test below is guarded by per-function
# `_skip_unless_cross_ref_positives()` so legacy Phase 8 tests above stay GREEN
# while the Wave 0 RED stubs SKIP (not error) on current production code.
# ===========================================================================


def test_cross_ref_positives_already_active():
    """ENABLED account exact match → ranked kw lands in `already_active` bucket."""
    _skip_unless_cross_ref_positives()
    ranked = _load_fixture_json("ranked_phase14.json")
    raw = _load_fixture_json("google-ads-keywords-fixture.json")
    sync = perf_synth.cross_ref_positives(ranked, raw["items"])
    already = sync.get("already_active", [])
    kws = {r["keyword"] for r in already}
    assert "urgent care lake worth" in kws


def test_cross_ref_positives_paused_in_account():
    """PAUSED account match → ranked kw lands in `paused_in_account` bucket."""
    _skip_unless_cross_ref_positives()
    ranked = _load_fixture_json("ranked_phase14.json")
    raw = _load_fixture_json("google-ads-keywords-fixture.json")
    sync = perf_synth.cross_ref_positives(ranked, raw["items"])
    paused = sync.get("paused_in_account", [])
    kws = {r["keyword"] for r in paused}
    assert "auto accident clinic" in kws


def test_cross_ref_positives_covered_by_broad():
    """Ranked exact `pip insurance clinic` vs account BROAD `pip clinic`
    (broader token set covers narrower) → `covered_by_broad` bucket."""
    _skip_unless_cross_ref_positives()
    ranked = _load_fixture_json("ranked_phase14.json")
    raw = _load_fixture_json("google-ads-keywords-fixture.json")
    sync = perf_synth.cross_ref_positives(ranked, raw["items"])
    covered = sync.get("covered_by_broad", [])
    kws = {r["keyword"] for r in covered}
    assert "pip insurance clinic" in kws


def test_cross_ref_positives_new_to_add():
    """Ranked kw with NO account counterpart → `new_to_add` bucket."""
    _skip_unless_cross_ref_positives()
    ranked = _load_fixture_json("ranked_phase14.json")
    raw = _load_fixture_json("google-ads-keywords-fixture.json")
    sync = perf_synth.cross_ref_positives(ranked, raw["items"])
    new_to_add = sync.get("new_to_add", [])
    kws = {r["keyword"] for r in new_to_add}
    assert "accident chiropractor lake worth" in kws
    assert "walk in clinic boca raton" in kws


def test_cross_ref_positives_stats_block():
    """stats dict contains 5 integer counts matching bucket list lengths."""
    _skip_unless_cross_ref_positives()
    ranked = _load_fixture_json("ranked_phase14.json")
    raw = _load_fixture_json("google-ads-keywords-fixture.json")
    sync = perf_synth.cross_ref_positives(ranked, raw["items"])
    stats = sync["stats"]
    for key in ("our_total", "already_active", "paused_in_account",
                "covered_by_broad", "new_to_add"):
        assert key in stats, f"stats missing key: {key}"
        assert isinstance(stats[key], int), f"stats[{key}] must be int"
    assert stats["our_total"] == len(ranked)
    assert stats["already_active"] == len(sync["already_active"])
    assert stats["paused_in_account"] == len(sync["paused_in_account"])
    assert stats["covered_by_broad"] == len(sync["covered_by_broad"])
    assert stats["new_to_add"] == len(sync["new_to_add"])


def test_cross_ref_positives_golden_fixture_byte_match(monkeypatch):
    """Full dict-equality against golden_positives_sync.json (synthesized_at pinned)."""
    _skip_unless_cross_ref_positives()
    monkeypatch.setattr(perf_synth, "_now_iso",
                        lambda: "2026-05-15T00:00:00Z")
    ranked = _load_fixture_json("ranked_phase14.json")
    raw = _load_fixture_json("google-ads-keywords-fixture.json")
    got = perf_synth.cross_ref_positives(ranked, raw["items"])
    expected = _load_fixture_json("golden_positives_sync.json")
    assert got == expected
