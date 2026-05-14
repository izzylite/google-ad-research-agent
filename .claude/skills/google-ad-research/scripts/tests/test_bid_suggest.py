"""Tests for bid_suggest.py — RED stubs (Phase 9 Wave 0).

All tests SKIP via MODULE_MISSING guard until bid_suggest.py lands in Wave 1
(Phase 9 plan 01). Contract under test: BIDS-01..04.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from bid_suggest import (  # noqa: F401
        INTENT_MULTIPLIERS,
        cluster_median_cpc,
        compute_suggested_cpc,
        enrich_with_bids,
        main_with_args,
    )
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(
    MODULE_MISSING, reason="bid_suggest.py not yet implemented (Wave 1, plan 01)"
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# BIDS-04 — INTENT_MULTIPLIERS frozenset contract
# ---------------------------------------------------------------------------

def test_intent_multipliers_frozenset():
    """INTENT_MULTIPLIERS must cover exactly the 4-class rubric (BIDS-04)."""
    assert frozenset(INTENT_MULTIPLIERS.keys()) == frozenset(
        {"transactional", "commercial", "informational", "navigational"}
    )


# ---------------------------------------------------------------------------
# BIDS-01 — compute_suggested_cpc per-intent multiplier (no USD conversion)
# ---------------------------------------------------------------------------

def test_compute_suggested_cpc_transactional():
    """cpc_micros × 1.2 (transactional); stays in micros — never USD-convert."""
    result, no_cpc_data = compute_suggested_cpc(
        cpc_micros=250_000, intent="transactional", cluster_median_micros=None
    )
    assert result == 300_000
    assert no_cpc_data is False


def test_compute_suggested_cpc_informational():
    """cpc_micros × 0.4 (informational)."""
    result, no_cpc_data = compute_suggested_cpc(
        cpc_micros=200_000, intent="informational", cluster_median_micros=None
    )
    assert result == 80_000
    assert no_cpc_data is False


@pytest.mark.parametrize(
    "intent,multiplier",
    [
        ("transactional", 1.2),
        ("commercial", 0.8),
        ("informational", 0.4),
        ("navigational", 1.0),
    ],
)
def test_all_four_intents_multiplied(intent, multiplier):
    """Every intent class applies its multiplier; mirrors INTENT_MULTIPLIERS."""
    assert INTENT_MULTIPLIERS[intent] == multiplier
    result, no_cpc_data = compute_suggested_cpc(
        cpc_micros=100_000, intent=intent, cluster_median_micros=None
    )
    assert result == int(100_000 * multiplier)
    assert no_cpc_data is False


# ---------------------------------------------------------------------------
# BIDS-02 — cluster-median fallback when cpc_micros is null
# ---------------------------------------------------------------------------

def test_cluster_median_fallback():
    """Null cpc_micros → cluster median × multiplier; flagged no_cpc_data=True."""
    result, no_cpc_data = compute_suggested_cpc(
        cpc_micros=None, intent="commercial", cluster_median_micros=200_000
    )
    # 200_000 × 0.8 = 160_000
    assert result == 160_000
    assert no_cpc_data is True


def test_null_when_cluster_empty_cpc():
    """No cpc on row and no cluster median → (None, True)."""
    result, no_cpc_data = compute_suggested_cpc(
        cpc_micros=None, intent="transactional", cluster_median_micros=None
    )
    assert result is None
    assert no_cpc_data is True


def test_orphan_returns_null():
    """Orphan keyword (cluster_name=None) with no row cpc → (None, True)."""
    # cluster_median_cpc on an unknown cluster name should return None
    keyword_to_cluster = {"foo": "cluster_a_transactional"}
    cluster_to_keywords = {"cluster_a_transactional": ["foo"]}
    median = cluster_median_cpc(keyword_to_cluster, cluster_to_keywords, None)
    assert median is None
    # And compute_suggested_cpc with both nulls returns (None, True)
    result, no_cpc_data = compute_suggested_cpc(
        cpc_micros=None, intent="transactional", cluster_median_micros=None
    )
    assert result is None
    assert no_cpc_data is True


# ---------------------------------------------------------------------------
# enrich_with_bids — operates on ranked-enriched.json shape (additive mutation)
# ---------------------------------------------------------------------------

def _load_clusters_phase9():
    return json.loads((FIXTURES / "clusters_phase9.json").read_text(encoding="utf-8"))


def test_enrich_with_bids_adds_field():
    """Every row gains 'suggested_max_cpc_micros' (BIDS-01)."""
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    clusters = _load_clusters_phase9()
    enriched = enrich_with_bids(ranked, clusters)
    assert len(enriched) == len(ranked)
    for row in enriched:
        assert "suggested_max_cpc_micros" in row


def test_enrich_with_bids_flags_no_cpc_data():
    """Rows with null cpc AND empty cluster pool get no_cpc_data=True (BIDS-02)."""
    ranked = json.loads(
        (FIXTURES / "ranked_partial_cpc.json").read_text(encoding="utf-8")
    )
    clusters = _load_clusters_phase9()
    enriched = enrich_with_bids(ranked, clusters)
    # Find rows where cpc_micros is None AND cluster siblings also have no cpc
    flagged = [r for r in enriched if r.get("no_cpc_data") is True]
    assert len(flagged) >= 1, "expected at least one no_cpc_data flagged row"
    # Every flagged row must have suggested_max_cpc_micros = None
    for row in flagged:
        assert row["suggested_max_cpc_micros"] is None


# ---------------------------------------------------------------------------
# main_with_args — CLI entrypoint writes back ranked-enriched.json additively
# ---------------------------------------------------------------------------

def test_main_with_args_writes_file(tmp_run_dir):
    """main_with_args seeds ranked-enriched.json + clusters.json; assert
    exit code 0 and file mutated additively (existing keys preserved)."""
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    clusters = _load_clusters_phase9()
    (tmp_run_dir / "ranked-enriched.json").write_text(
        json.dumps(ranked), encoding="utf-8"
    )
    (tmp_run_dir / "clusters.json").write_text(json.dumps(clusters), encoding="utf-8")

    rc = main_with_args(["--run-dir", str(tmp_run_dir)])
    assert rc == 0

    out = json.loads(
        (tmp_run_dir / "ranked-enriched.json").read_text(encoding="utf-8")
    )
    assert len(out) == len(ranked)
    # Original keys preserved
    for row, original in zip(out, ranked):
        assert row["keyword"] == original["keyword"]
        assert row["intent"] == original["intent"]
        assert row["score"] == original["score"]
        assert "suggested_max_cpc_micros" in row
