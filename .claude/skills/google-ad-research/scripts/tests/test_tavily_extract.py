"""
RED stubs for tavily_extract.py — Tavily SDK extract → raw/tavily-<domain>.json.

Tests go GREEN in Phase 2 Plan C (Wave 2) when tavily_extract.py is implemented.
"""
import pytest

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import tavily_extract  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="tavily_extract.py not yet implemented")


def test_caps_enforced(tmp_run_dir, mock_env):
    """tavily_extract processes at most 5 competitors × 5 URLs each (hard caps)."""
    raise NotImplementedError


def test_uses_basic_depth(tmp_run_dir, mock_env, tavily_fixture):
    """TavilyClient.extract is called with extract_depth='basic'."""
    raise NotImplementedError


def test_failed_results_persisted(tmp_run_dir, mock_env, tavily_fixture):
    """failed_results from Tavily response are logged and persisted to disk (not silently dropped)."""
    raise NotImplementedError


def test_exit_code_3_on_auth_error(tmp_run_dir, mock_env):
    """tavily_extract exits with code 3 when Tavily raises InvalidAPIKeyError."""
    raise NotImplementedError
