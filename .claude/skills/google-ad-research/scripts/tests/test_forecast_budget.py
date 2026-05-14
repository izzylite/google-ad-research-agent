"""Tests for forecast_budget.py — RED stubs (Phase 9 Wave 0).

All tests SKIP via MODULE_MISSING guard until forecast_budget.py lands in
Wave 1 (Phase 9 plan 02). Contract under test: FRCS-01..05.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from forecast_budget import (  # noqa: F401
        AVG_CPC_RATIO,
        BAND_MULTIPLIERS,
        INTENT_CTRS,
        build_forecast,
        compute_cluster_forecast,
        main_with_args,
    )
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(
    MODULE_MISSING,
    reason="forecast_budget.py not yet implemented (Wave 1, plan 02)",
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# FRCS-02 — INTENT_CTRS frozen-set + values
# ---------------------------------------------------------------------------

def test_intent_ctrs_frozenset():
    """INTENT_CTRS keys must match the 4-class rubric."""
    assert frozenset(INTENT_CTRS.keys()) == frozenset(
        {"transactional", "commercial", "informational", "navigational"}
    )


# ---------------------------------------------------------------------------
# FRCS-03 — avg-CPC ratio + band multipliers
# ---------------------------------------------------------------------------

def test_avg_cpc_ratio_constant():
    """AVG_CPC_RATIO is the documented 0.65 anchor."""
    assert AVG_CPC_RATIO == 0.65


def test_band_multipliers():
    """Low / mid / high bands are 0.5 / 1.0 / 1.5."""
    assert BAND_MULTIPLIERS == {"low": 0.5, "mid": 1.0, "high": 1.5}


# ---------------------------------------------------------------------------
# FRCS-02 — click estimates derive from intent-CTR
# ---------------------------------------------------------------------------

def test_click_estimates_use_intent_ctrs():
    """daily_clicks_mid for a single keyword = volume × CTR / 30 (FRCS-02)."""
    # Single-keyword cluster: volume=3000, intent=transactional, ctr=0.06
    cluster = {
        "name": "delivery_transactional",
        "intent": "transactional",
        "keywords": [{"keyword": "same-day grocery delivery", "score": 100}],
    }
    ranked_index = {
        "same-day grocery delivery": {
            "keyword": "same-day grocery delivery",
            "intent": "transactional",
            "volume": 3000,
            "suggested_max_cpc_micros": 360_000,
        }
    }
    out = compute_cluster_forecast(cluster, ranked_index)
    # Expected: 3000 × 0.06 / 30 = 6.0 clicks/day (mid)
    assert out["daily_clicks_mid"] == pytest.approx(6.0, rel=0.01)


# ---------------------------------------------------------------------------
# FRCS-03 — band arithmetic: spend_low = spend_mid × 0.5, spend_high × 1.5
# ---------------------------------------------------------------------------

def test_band_arithmetic():
    """Low / high spend mirror mid × 0.5 / × 1.5."""
    cluster = {
        "name": "delivery_transactional",
        "intent": "transactional",
        "keywords": [{"keyword": "same-day grocery delivery", "score": 100}],
    }
    ranked_index = {
        "same-day grocery delivery": {
            "keyword": "same-day grocery delivery",
            "intent": "transactional",
            "volume": 3000,
            "suggested_max_cpc_micros": 400_000,
        }
    }
    out = compute_cluster_forecast(cluster, ranked_index)
    assert out["daily_spend_low_usd"] == pytest.approx(
        out["daily_spend_mid_usd"] * 0.5, rel=0.01
    )
    assert out["daily_spend_high_usd"] == pytest.approx(
        out["daily_spend_mid_usd"] * 1.5, rel=0.01
    )


# ---------------------------------------------------------------------------
# FRCS-01 — forecast.json schema
# ---------------------------------------------------------------------------

def test_forecast_json_schema():
    """forecast.json must contain metadata, methodology, clusters[], campaign_totals."""
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    # Synthesize suggested_max_cpc_micros for the schema test
    for row in ranked:
        row["suggested_max_cpc_micros"] = (
            int(row["cpc_micros"] * 1.0) if row.get("cpc_micros") is not None else None
        )
    clusters = json.loads(
        (FIXTURES / "clusters_phase9.json").read_text(encoding="utf-8")
    )
    forecast = build_forecast(ranked, clusters, run_id="test-run")
    assert "metadata" in forecast
    assert "methodology" in forecast
    assert "clusters" in forecast
    assert "campaign_totals" in forecast
    assert isinstance(forecast["clusters"], list)
    expected_per_cluster = {
        "name",
        "intent",
        "keyword_count",
        "keywords_with_volume",
        "daily_clicks_low",
        "daily_clicks_mid",
        "daily_clicks_high",
        "daily_spend_low_usd",
        "daily_spend_mid_usd",
        "daily_spend_high_usd",
    }
    for cl in forecast["clusters"]:
        assert expected_per_cluster.issubset(set(cl.keys())), (
            f"Missing keys in cluster: {expected_per_cluster - set(cl.keys())}"
        )


# ---------------------------------------------------------------------------
# Skip keywords without volume OR suggested_max_cpc
# ---------------------------------------------------------------------------

def test_skips_keywords_without_volume_or_cpc():
    """Keyword with volume=None OR suggested_max_cpc=None contributes 0."""
    cluster = {
        "name": "delivery_transactional",
        "intent": "transactional",
        "keywords": [
            {"keyword": "with everything", "score": 100},
            {"keyword": "no volume", "score": 90},
            {"keyword": "no cpc", "score": 80},
        ],
    }
    ranked_index = {
        "with everything": {
            "keyword": "with everything",
            "intent": "transactional",
            "volume": 3000,
            "suggested_max_cpc_micros": 400_000,
        },
        "no volume": {
            "keyword": "no volume",
            "intent": "transactional",
            "volume": None,
            "suggested_max_cpc_micros": 400_000,
        },
        "no cpc": {
            "keyword": "no cpc",
            "intent": "transactional",
            "volume": 1000,
            "suggested_max_cpc_micros": None,
        },
    }
    out = compute_cluster_forecast(cluster, ranked_index)
    # Only "with everything" contributes; keywords_with_volume == 1
    assert out["keywords_with_volume"] == 1
    # daily_clicks_mid = 3000 × 0.06 / 30 = 6.0
    assert out["daily_clicks_mid"] == pytest.approx(6.0, rel=0.01)


# ---------------------------------------------------------------------------
# Pitfall 6 — cluster join is lowercased + stripped
# ---------------------------------------------------------------------------

def test_cluster_join_lowercase_strip():
    """'Same-Day Delivery' in cluster matches 'same-day delivery' in ranked."""
    cluster = {
        "name": "delivery_transactional",
        "intent": "transactional",
        "keywords": [{"keyword": "Same-Day Delivery", "score": 100}],
    }
    ranked_index = {
        "same-day delivery": {
            "keyword": "same-day delivery",
            "intent": "transactional",
            "volume": 1000,
            "suggested_max_cpc_micros": 300_000,
        }
    }
    out = compute_cluster_forecast(cluster, ranked_index)
    # Must have matched — keywords_with_volume should be 1
    assert out["keywords_with_volume"] == 1


# ---------------------------------------------------------------------------
# FRCS-05 — methodology block present + mirrors script constants exactly
# ---------------------------------------------------------------------------

def test_methodology_block_present():
    """methodology.intent_ctrs + avg_cpc_ratio mirror the script constants."""
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    for row in ranked:
        row["suggested_max_cpc_micros"] = (
            int(row["cpc_micros"] * 1.0) if row.get("cpc_micros") is not None else None
        )
    clusters = json.loads(
        (FIXTURES / "clusters_phase9.json").read_text(encoding="utf-8")
    )
    forecast = build_forecast(ranked, clusters, run_id="test-run")
    method = forecast["methodology"]
    assert method["intent_ctrs"] == INTENT_CTRS
    assert method["avg_cpc_ratio"] == AVG_CPC_RATIO


# ---------------------------------------------------------------------------
# main_with_args — writes forecast.json
# ---------------------------------------------------------------------------

def test_main_with_args_writes_forecast_json(tmp_run_dir):
    """main_with_args writes {run_dir}/forecast.json which parses as JSON."""
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    for row in ranked:
        row["suggested_max_cpc_micros"] = (
            int(row["cpc_micros"] * 1.0) if row.get("cpc_micros") is not None else None
        )
    clusters = json.loads(
        (FIXTURES / "clusters_phase9.json").read_text(encoding="utf-8")
    )
    (tmp_run_dir / "ranked-enriched.json").write_text(
        json.dumps(ranked), encoding="utf-8"
    )
    (tmp_run_dir / "clusters.json").write_text(json.dumps(clusters), encoding="utf-8")

    rc = main_with_args(["--run-dir", str(tmp_run_dir)])
    assert rc == 0
    out_path = tmp_run_dir / "forecast.json"
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "clusters" in data
    assert "campaign_totals" in data
