"""
RED stubs for serp_fetch.py — Serper.dev REST → raw/serper.json.

Tests go GREEN in Phase 2 Plan B (Wave 2) when serp_fetch.py is implemented.
"""
import pytest

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import serp_fetch  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="serp_fetch.py not yet implemented")


def test_writes_all_blocks(tmp_run_dir, mock_env, serper_fixture):
    """serp_fetch writes organic, peopleAlsoAsk, relatedSearches, and ads to raw/serper.json."""
    raise NotImplementedError


def test_locale_params_passed(tmp_run_dir, mock_env, serper_fixture):
    """gl and hl params from brief are included in the Serper API request body."""
    raise NotImplementedError


def test_locale_persisted(tmp_run_dir, mock_env, serper_fixture):
    """searchParameters.gl and searchParameters.hl appear in the persisted raw/serper.json."""
    raise NotImplementedError


def test_empty_ads_no_error(tmp_run_dir, mock_env, serper_empty_ads_fixture):
    """serp_fetch does not raise when the Serper response has an empty ads array."""
    raise NotImplementedError


def test_retries_on_429(tmp_run_dir, mock_env):
    """serp_fetch retries the Serper call on HTTP 429 before succeeding."""
    raise NotImplementedError


def test_exit_code_3_on_401(tmp_run_dir, mock_env):
    """serp_fetch exits with code 3 on HTTP 401 (fatal auth error)."""
    raise NotImplementedError
