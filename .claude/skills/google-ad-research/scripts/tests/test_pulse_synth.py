"""Tests for pulse_synth.py — theme clustering, regulatory, competitor, negatives."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make scripts/ importable
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import pulse_synth  # noqa: E402
    PS_MISSING = False
except ImportError:
    PS_MISSING = True

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _items_from_fixtures():
    s = FIXTURES_DIR / "serper_news.json"
    t = FIXTURES_DIR / "tavily_news.json"
    if PS_MISSING:
        return []
    return pulse_synth.load_news_items(s, t)


def test_load_news_items_combines_sources():
    if PS_MISSING:
        pytest.skip("pulse_synth not yet implemented")
    items = _items_from_fixtures()
    assert len(items) == 5
    sources = {it.get("_source") for it in items}
    assert "serper-news" in sources
    assert "tavily-news" in sources


def test_find_themes_clusters_repeated_phrases():
    if PS_MISSING:
        pytest.skip("pulse_synth not yet implemented")
    items = _items_from_fixtures()
    themes = pulse_synth.find_themes(items)
    # "florida pip" should be a theme — appears in multiple titles
    theme_strs = {t["theme"] for t in themes}
    assert any("pip" in s for s in theme_strs), f"no pip theme found: {theme_strs}"


def test_find_regulatory_alerts_flags_law_keywords():
    if PS_MISSING:
        pytest.skip("pulse_synth not yet implemented")
    items = _items_from_fixtures()
    alerts = pulse_synth.find_regulatory_alerts(items)
    # PIP + law + lawsuit + amendment all in fixtures → multiple alerts
    assert len(alerts) >= 3
    # Each alert has matched_keywords
    for a in alerts:
        assert a["matched_keywords"]


def test_find_competitor_news_matches_brand_name():
    if PS_MISSING:
        pytest.skip("pulse_synth not yet implemented")
    items = _items_from_fixtures()
    matches = pulse_synth.find_competitor_news(items, brands=["MD Now"])
    # The lawsuit headline mentions MD Now
    assert len(matches) == 1
    assert matches[0]["matched_brand"] == "md now"


def test_find_trending_negatives_flags_scam_lawsuit_terms():
    if PS_MISSING:
        pytest.skip("pulse_synth not yet implemented")
    items = _items_from_fixtures()
    negs = pulse_synth.find_trending_negatives(items)
    triggers = {n.get("suggested_negative") for n in negs}
    # Scam + lawsuit both present in fixtures
    assert "scam" in triggers or "lawsuit" in triggers


def test_themes_have_required_fields():
    if PS_MISSING:
        pytest.skip("pulse_synth not yet implemented")
    items = _items_from_fixtures()
    themes = pulse_synth.find_themes(items)
    for t in themes:
        assert "theme" in t
        assert "mention_count" in t
        assert "sources" in t
        assert "headlines" in t
        assert "suggested_keywords" in t
        assert t["mention_count"] >= 2


# ---------------------------------------------------------------------------
# Phase 12 PULSE-11: single-source signature — load_news_items(serper_path)
# ---------------------------------------------------------------------------
def test_load_news_items_serper_only():
    """PULSE-11: load_news_items must accept only serper_path post-Phase-12.

    RED against Phase 11 (current signature is load_news_items(serper_path, tavily_path)).
    Wave 1 plan 12-03 strips the tavily_path arg.
    """
    if PS_MISSING:
        pytest.skip("pulse_synth not yet implemented")
    import inspect as _i
    sig = _i.signature(pulse_synth.load_news_items)
    params = list(sig.parameters)
    assert params == ["serper_path"], (
        f"PULSE-11: load_news_items must accept only serper_path; got {params}"
    )
