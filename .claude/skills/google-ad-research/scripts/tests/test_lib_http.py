"""
RED stubs for lib/http.py — httpx-retries RetryTransport wrapper.

Tests go GREEN in Phase 2 Plan A (Wave 1) when lib/http.py is implemented.
"""
import pytest

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from lib.http import build_client  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="lib/http.py not yet implemented")


def test_retry_on_429():
    """build_client() retries on HTTP 429 with exponential backoff."""
    raise NotImplementedError


def test_no_retry_on_401():
    """build_client() does NOT retry on HTTP 401 (auth errors are fatal)."""
    raise NotImplementedError


def test_success_path():
    """build_client() returns a working httpx.Client for a 200 response."""
    raise NotImplementedError
