"""Tests for perf_synth.py — synth + negative cross-reference logic."""
from __future__ import annotations

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
