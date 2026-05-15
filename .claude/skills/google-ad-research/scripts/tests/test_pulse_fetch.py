"""PULSE-10: pulse_fetch writes only Serper /news; no Tavily branch.

RED against Phase 11 (pulse_fetch.py still has fetch_tavily_news + writes
raw/tavily-news.json). Wave 1 plan 12-03 strips the Tavily branch.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

# Make scripts/ importable
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import pulse_fetch  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="pulse_fetch.py not yet implemented")


def test_only_serper_news_written() -> None:
    """PULSE-10: Tavily news helpers must be deleted from pulse_fetch namespace."""
    assert not hasattr(pulse_fetch, "fetch_tavily_news"), \
        "PULSE-10: fetch_tavily_news must be deleted"
    assert not hasattr(pulse_fetch, "normalise_tavily_news"), \
        "PULSE-10: normalise_tavily_news must be deleted"


def test_no_tavily_news_path_in_main() -> None:
    """PULSE-10: pulse_fetch.py source must contain no Tavily references."""
    src = inspect.getsource(pulse_fetch)
    assert "tavily" not in src.lower(), \
        "PULSE-10: pulse_fetch.py source must contain no Tavily references"
    assert "tavily-news.json" not in src, \
        "PULSE-10: pulse_fetch.py must not write tavily-news.json"
