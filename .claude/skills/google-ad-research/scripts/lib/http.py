"""lib/http.py — shared httpx.Client builder with httpx-retries RetryTransport.

Used by serp_fetch.py + competitor_intel.py + pulse_fetch.py for all Serper REST calls.

Retry policy (verified against PITFALLS § Error Handling):
    total=3 retries
    backoff_factor=1.0  (sleep 1s, 2s, 4s with jitter)
    status_forcelist=[429, 500, 502, 503, 504]
    Retry-After header honoured (httpx-retries default)
"""
from __future__ import annotations

import httpx
from httpx_retries import Retry, RetryTransport


def build_client(*, timeout: float = 30.0) -> httpx.Client:
    """Return a configured sync httpx.Client; caller is responsible for context-manager close."""
    retry = Retry(total=3, backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504])
    transport = RetryTransport(retry=retry)
    return httpx.Client(
        transport=transport,
        timeout=timeout,
        follow_redirects=False,  # Serper returns direct JSON; redirects would be suspicious
    )
