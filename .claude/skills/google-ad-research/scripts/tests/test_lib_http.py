"""
Tests for lib/http.py — httpx-retries RetryTransport wrapper.

Tests verify:
- build_client() retries on 429 (transient) up to 3 times before succeeding
- build_client() does NOT retry 401 (auth failures are fatal)
- build_client() succeeds immediately on a 200 response
"""
import pytest
import respx
from httpx import Response

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from lib.http import build_client  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="lib/http.py not yet implemented")


@respx.mock
def test_retry_on_429():
    """build_client() retries on HTTP 429 with exponential backoff."""
    # Return 429 twice, then 200 on the third attempt
    route = respx.get("https://example.com/").mock(side_effect=[
        Response(429),
        Response(429),
        Response(200, json={"ok": True}),
    ])

    client = build_client(timeout=5.0)
    response = client.get("https://example.com/")

    assert response.status_code == 200
    assert route.call_count == 3


@respx.mock
def test_no_retry_on_401():
    """build_client() does NOT retry on HTTP 401 (auth errors are fatal)."""
    import httpx as _httpx

    route = respx.get("https://example.com/").mock(return_value=Response(401))

    client = build_client(timeout=5.0)
    with pytest.raises(_httpx.HTTPStatusError):
        client.get("https://example.com/").raise_for_status()

    # 401 is not in status_forcelist — should only be called once
    assert route.call_count == 1


@respx.mock
def test_success_path():
    """build_client() returns a working httpx.Client for a 200 response."""
    respx.get("https://example.com/").mock(return_value=Response(200, json={"hello": "world"}))

    client = build_client(timeout=5.0)
    response = client.get("https://example.com/")

    assert response.status_code == 200
    assert response.json() == {"hello": "world"}
