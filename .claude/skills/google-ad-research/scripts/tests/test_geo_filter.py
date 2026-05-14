"""RED stubs for geographic city/county filter (Phase 11 Wave 0).

All tests SKIP via module-level pytestmark until Wave 1 plan 11-01 adds the
new merge_signals helpers:
    - merge_signals._build_city_filter(state, geo_focus, us_cities)
    - merge_signals._keyword_drifts_city(text, city_filter)

Requirements covered (RED):
    GEO-03  Drop OTHER-city tokens in the brief's state; preserve city→county
            hierarchy; backward-compatible when geo_focus is empty.
    GEO-04  references/us-cities.json schema (state_code → city → county).

The us-cities-subset.json fixture is the local stand-in for the full
top-5000 reference data file (which ships in Wave 1 plan 11-01).
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
    import merge_signals  # noqa: F401
    GEO_FILTER_INCOMPLETE = not hasattr(merge_signals, "_keyword_drifts_city")
except ImportError:
    GEO_FILTER_INCOMPLETE = True

pytestmark = pytest.mark.skipif(
    GEO_FILTER_INCOMPLETE,
    reason="merge_signals city filter — Wave 1 plan 11-01",
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_us_cities() -> dict:
    return json.loads(
        (FIXTURES / "us-cities-subset.json").read_text(encoding="utf-8")
    )


# ---------------------------------------------------------------------------
# GEO-04 — us-cities-subset.json loadable + correct county values
# ---------------------------------------------------------------------------

def test_us_cities_loadable():
    """us-cities-subset.json loads as JSON; FL/TX values match expected counties."""
    us_cities = _load_us_cities()
    assert us_cities["fl"]["lake worth"] == "palm beach"
    assert us_cities["fl"]["boca raton"] == "palm beach"
    assert us_cities["tx"]["lake worth"] == "tarrant"
    # Homonym sanity — CA Hollywood maps to LA County, FL Hollywood to Broward.
    assert us_cities["ca"]["hollywood"] == "los angeles"
    assert us_cities["fl"]["hollywood"] == "broward"


# ---------------------------------------------------------------------------
# GEO-03 — city/county/state filter behaviour
# ---------------------------------------------------------------------------

def test_keyword_kept_when_city_in_geo_focus():
    """Lake Worth (FL) appears in keyword + geo_focus=Palm Beach County → KEEP."""
    us_cities = _load_us_cities()
    city_filter = merge_signals._build_city_filter(
        "fl", ["Palm Beach County"], us_cities,
    )
    assert merge_signals._keyword_drifts_city(
        "lake worth chiropractor", city_filter,
    ) is False


def test_keyword_kept_when_city_county_in_geo_focus():
    """Boca Raton city's county IS Palm Beach (hierarchy) → KEEP (Pitfall 5)."""
    us_cities = _load_us_cities()
    city_filter = merge_signals._build_city_filter(
        "fl", ["Palm Beach County"], us_cities,
    )
    assert merge_signals._keyword_drifts_city(
        "boca raton dentist", city_filter,
    ) is False


def test_keyword_dropped_when_other_state_city():
    """Tampa (Hillsborough) NOT in Palm Beach focus → DROP."""
    us_cities = _load_us_cities()
    city_filter = merge_signals._build_city_filter(
        "fl", ["Palm Beach County"], us_cities,
    )
    assert merge_signals._keyword_drifts_city(
        "tampa pain clinic", city_filter,
    ) is True


def test_keyword_kept_when_no_geo_focus():
    """Backward compat: empty geo_focus disables city filter entirely."""
    us_cities = _load_us_cities()
    city_filter = merge_signals._build_city_filter("fl", [], us_cities)
    # Even a city normally out-of-focus should NOT be dropped when filter inactive.
    assert merge_signals._keyword_drifts_city(
        "tampa pain clinic", city_filter,
    ) is False


def test_state_disambiguation():
    """Lake Worth lives in BOTH FL and TX — disambiguate by brief state (Pitfall 4)."""
    us_cities = _load_us_cities()
    # FL run, Palm Beach focus — Lake Worth FL kept; Tampa dropped.
    fl_filter = merge_signals._build_city_filter(
        "fl", ["Palm Beach County"], us_cities,
    )
    assert merge_signals._keyword_drifts_city(
        "lake worth chiropractor", fl_filter,
    ) is False
    assert merge_signals._keyword_drifts_city(
        "tampa pain clinic", fl_filter,
    ) is True
    # TX run, Tarrant focus — Lake Worth TX kept; Dallas should be dropped.
    tx_filter = merge_signals._build_city_filter(
        "tx", ["Tarrant County"], us_cities,
    )
    assert merge_signals._keyword_drifts_city(
        "lake worth car shop", tx_filter,
    ) is False
    assert merge_signals._keyword_drifts_city(
        "dallas car shop", tx_filter,
    ) is True


def test_stopword_safety():
    """Geographic filter MUST NOT consult the similarity-math stopword list.

    The city/county filter is purely a string-membership check against the
    state's city catalogue. Tokens like 'near' / 'me' that appear in
    `_STOPWORDS` for ad_group_match must not influence the geo filter at all.
    """
    us_cities = _load_us_cities()
    city_filter = merge_signals._build_city_filter(
        "fl", ["Palm Beach County"], us_cities,
    )
    # 'near me lake worth doctor' should NOT be dropped (Lake Worth in focus).
    assert merge_signals._keyword_drifts_city(
        "near me lake worth doctor", city_filter,
    ) is False
