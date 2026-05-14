"""Tests for volume_enrich.py — merge logic + country detection.

Network is mocked via respx (no real Ahrefs calls).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import respx
    import httpx
    import volume_enrich
    VE_MISSING = False
except ImportError:
    VE_MISSING = True


def test_country_from_locale_detects_uk():
    if VE_MISSING:
        pytest.skip("volume_enrich not yet implemented")
    assert volume_enrich._country_from_locale("Language: en-GB") == "gb"
    assert volume_enrich._country_from_locale("Targeting UK households") == "gb"


def test_country_from_locale_defaults_us():
    if VE_MISSING:
        pytest.skip("volume_enrich not yet implemented")
    assert volume_enrich._country_from_locale("Florida, en-US") == "us"
    assert volume_enrich._country_from_locale("") == "us"


def test_enrich_keywords_merges_ahrefs_response():
    if VE_MISSING:
        pytest.skip("volume_enrich not yet implemented")
    kws = [
        {"keyword": "urgent care", "intent": "transactional", "score": 100},
        {"keyword": "PIP exam", "intent": "transactional", "score": 90},  # mixed case
    ]
    with respx.mock(base_url="https://api.ahrefs.com") as router:
        router.get("/v3/keywords-explorer/overview").mock(
            return_value=httpx.Response(200, json={
                "keywords": [
                    {"keyword": "urgent care", "volume": 1000, "cpc": 250,
                     "difficulty": 30, "parent_topic": "urgent care", "clicks": None},
                    {"keyword": "pip exam", "volume": 50, "cpc": None,
                     "difficulty": None, "parent_topic": None, "clicks": None},
                ]
            })
        )
        enriched, raw, calls = volume_enrich.enrich_keywords(
            kws, country="us", api_key="test-key", batch_size=100,
        )
    assert calls == 1
    by_kw = {k["keyword"]: k for k in enriched}
    assert by_kw["urgent care"]["volume"] == 1000
    assert by_kw["urgent care"]["cpc_micros"] == 250 * 10_000
    assert by_kw["urgent care"]["difficulty"] == 30
    assert by_kw["urgent care"]["parent_topic"] == "urgent care"
    # Case-insensitive merge ("PIP exam" → matched "pip exam" from response)
    assert by_kw["PIP exam"]["volume"] == 50
    # Null fields preserved
    assert by_kw["PIP exam"]["cpc_micros"] is None
    assert by_kw["PIP exam"]["difficulty"] is None


def test_enrich_keywords_handles_keyword_not_in_response():
    """Ahrefs returns no data for some keywords (zero-volume). enriched row
    should still have the 4 enrichment keys (set to None)."""
    if VE_MISSING:
        pytest.skip("volume_enrich not yet implemented")
    kws = [
        {"keyword": "real keyword", "score": 100},
        {"keyword": "zero volume oddity", "score": 90},
    ]
    with respx.mock(base_url="https://api.ahrefs.com") as router:
        router.get("/v3/keywords-explorer/overview").mock(
            return_value=httpx.Response(200, json={
                "keywords": [
                    {"keyword": "real keyword", "volume": 500, "cpc": 100,
                     "difficulty": 20, "parent_topic": "real", "clicks": None},
                    # "zero volume oddity" missing entirely
                ]
            })
        )
        enriched, _, _ = volume_enrich.enrich_keywords(
            kws, country="us", api_key="test-key",
        )
    by_kw = {k["keyword"]: k for k in enriched}
    assert by_kw["zero volume oddity"]["volume"] is None
    assert by_kw["zero volume oddity"]["cpc_micros"] is None
    assert "volume" in by_kw["zero volume oddity"]  # key exists, value None
