"""lib/ahrefs_client.py — Ahrefs API v3 client wrapper.

Single-purpose: GET /v3/keywords-explorer/overview. Batches up to ~100
keywords per call. Retries on 5xx + 429 with backoff. Returns raw JSON.

Auth: Bearer token via AHREFS_API_KEY env var (loaded from .env upstream).

Pricing note: Ahrefs charges per row returned (not per call). Cost is
predictable per keyword regardless of batch size — batching just reduces
HTTP overhead.
"""
from __future__ import annotations

import os
from typing import Iterable

import httpx
from httpx_retries import Retry, RetryTransport


AHREFS_BASE = "https://api.ahrefs.com"
KEYWORDS_OVERVIEW_PATH = "/v3/keywords-explorer/overview"

# Comma-separated fields requested from /overview.
DEFAULT_SELECT = "keyword,volume,cpc,difficulty,parent_topic,clicks"

# Ahrefs accepts up to 1000 keywords per call (per docs) but 100 is a safer
# default — keeps URL length bounded for GET, lets us retry smaller chunks.
MAX_KEYWORDS_PER_CALL = 100


def build_client(*, timeout: float = 30.0) -> httpx.Client:
    """httpx.Client with retry on 429/5xx + 30s timeout."""
    retry = Retry(
        total=4,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    transport = RetryTransport(retry=retry)
    return httpx.Client(
        base_url=AHREFS_BASE,
        transport=transport,
        timeout=timeout,
    )


def fetch_overview(
    client: httpx.Client,
    keywords: list[str],
    *,
    country: str,
    api_key: str,
    select: str = DEFAULT_SELECT,
) -> dict:
    """Fetch /keywords-explorer/overview for a batch of keywords.

    Returns parsed JSON: {"keywords": [{keyword, volume, cpc, difficulty, ...}]}.

    Raises httpx.HTTPStatusError on persistent 4xx/5xx after retries.

    Args:
        keywords: ≤ MAX_KEYWORDS_PER_CALL strings.
        country: 2-letter country code lowercased (e.g. "us", "uk", "ca").
        api_key: Ahrefs bearer token.
        select: comma-separated field list. Default covers what
            volume_enrich.py needs.
    """
    if len(keywords) > MAX_KEYWORDS_PER_CALL:
        raise ValueError(
            f"keywords batch size {len(keywords)} exceeds "
            f"MAX_KEYWORDS_PER_CALL={MAX_KEYWORDS_PER_CALL}; "
            f"call chunk_keywords() first"
        )

    params = {
        "country": country,
        "keywords": ",".join(keywords),
        "select": select,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    response = client.get(KEYWORDS_OVERVIEW_PATH, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def chunk_keywords(
    keywords: Iterable[str],
    *,
    size: int = MAX_KEYWORDS_PER_CALL,
) -> list[list[str]]:
    """Split keywords into chunks of at most `size`."""
    kws = list(keywords)
    return [kws[i : i + size] for i in range(0, len(kws), size)]


def get_api_key() -> str:
    """Read AHREFS_API_KEY from env. Raises EnvironmentError if missing."""
    key = os.environ.get("AHREFS_API_KEY")
    if not key:
        raise EnvironmentError(
            "AHREFS_API_KEY not set. Add to .env at project root."
        )
    return key
