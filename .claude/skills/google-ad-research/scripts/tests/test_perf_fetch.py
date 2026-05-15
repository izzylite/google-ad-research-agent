"""Tests for perf_fetch.py — Google Ads keyword_view fetch (Phase 14 POS-07).

Wave 0 RED stubs for `perf_fetch.fetch_keyword_view`. The function is landed
by Wave 1 plan 14-01. Until then, the per-function `_skip_unless_fetch_keyword_view()`
guard SKIPS (does not error) the new tests.

The google-ads SDK has its own gRPC layer that respx cannot mock. We use a
hand-rolled `_FakeGAdsClient` + `_FakeSearchStream` stub that captures the
GAQL query string passed to `search_stream` and yields synthetic rows. This
mirrors the lightweight fake-client pattern used elsewhere in the test suite
(see perf_fetch.py contract: fetch_* functions take a `client` arg whose
only API is `client.get_service("GoogleAdsService").search_stream(...)`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import perf_fetch  # noqa: F401
    PF_MISSING = False
except ImportError:
    PF_MISSING = True

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _skip_unless_fetch_keyword_view() -> None:
    """Per-function guard — Wave 1 plan 14-01 lands perf_fetch.fetch_keyword_view."""
    if PF_MISSING:
        pytest.skip("perf_fetch not importable (google-ads SDK env)")
    if not hasattr(perf_fetch, "fetch_keyword_view"):
        pytest.skip(
            "Wave 1 14-01 not yet landed: perf_fetch.fetch_keyword_view missing"
        )


# ---------------------------------------------------------------------------
# Lightweight google-ads SDK fake — captures query string + yields rows.
# ---------------------------------------------------------------------------

class _FakeRow:
    """Mirrors the dotted attribute access of a real google-ads row."""
    def __init__(self, data: dict) -> None:
        # Each top-level key maps to a SimpleNamespace; enums are wrapped to
        # expose `.name` so `row.segments.match_type.name` works.
        for k, v in data.items():
            if isinstance(v, dict):
                setattr(self, k, SimpleNamespace(**{
                    kk: (SimpleNamespace(name=vv) if isinstance(vv, str) and kk.endswith(("status", "match_type")) else vv)
                    for kk, vv in v.items()
                }))
            else:
                setattr(self, k, v)


class _FakeBatch:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self.results = rows


class _FakeGoogleAdsService:
    def __init__(self, captured: dict, rows: list[_FakeRow]) -> None:
        self._captured = captured
        self._rows = rows

    def search_stream(self, customer_id: str, query: str):
        self._captured["customer_id"] = customer_id
        self._captured["query"] = query
        yield _FakeBatch(self._rows)


class _FakeGAdsClient:
    def __init__(self, rows: list[_FakeRow] | None = None) -> None:
        self.captured: dict = {}
        self._rows = rows or []

    def get_service(self, name: str):
        assert name == "GoogleAdsService"
        return _FakeGoogleAdsService(self.captured, self._rows)


def _keyword_view_rows_from_fixture() -> list[_FakeRow]:
    raw = json.loads(
        (FIXTURES_DIR / "google-ads-keywords-fixture.json").read_text(encoding="utf-8")
    )
    rows: list[_FakeRow] = []
    for item in raw["items"]:
        rows.append(_FakeRow({
            "ad_group": {
                "id": int(item["ad_group_id"]),
                "name": item["ad_group_name"],
            },
            "ad_group_criterion": {
                "keyword": SimpleNamespace(
                    text=item["keyword"],
                    match_type=SimpleNamespace(name=item["match_type"]),
                ),
                "status": SimpleNamespace(name=item["status"]),
            },
            "campaign": {"name": item["campaign_name"]},
            "metrics": {
                "impressions": item["impressions"],
                "clicks": item["clicks"],
                "conversions": item["conversions"],
                "cost_micros": item["cost_micros"],
            },
        }))
    return rows


# ---------------------------------------------------------------------------
# Phase 14 Wave 0 — fetch_keyword_view RED stubs (POS-07)
# ---------------------------------------------------------------------------

def test_fetch_keyword_view_gaql_query():
    """GAQL query string contains the required substrings (POS-01)."""
    _skip_unless_fetch_keyword_view()
    client = _FakeGAdsClient(rows=_keyword_view_rows_from_fixture())
    perf_fetch.fetch_keyword_view(client, "9999999999", days=30)
    query = client.captured.get("query", "")
    assert "FROM keyword_view" in query
    assert "DURING LAST_30_DAYS" in query
    assert "ad_group_criterion.status != 'REMOVED'" in query


def test_perf_fetch_writes_google_ads_keywords_json(tmp_path: Path):
    """End-to-end: fetch_keyword_view items shape matches the raw envelope contract."""
    _skip_unless_fetch_keyword_view()
    client = _FakeGAdsClient(rows=_keyword_view_rows_from_fixture())
    items = perf_fetch.fetch_keyword_view(client, "9999999999", days=30)
    # Shape contract: each item carries the locked Phase 14 keys.
    assert items, "fetch_keyword_view returned no items"
    sample = items[0]
    required_keys = {
        "keyword", "match_type", "status",
        "ad_group_id", "ad_group_name", "campaign_name",
        "impressions", "clicks", "conversions", "cost_micros",
    }
    missing = required_keys - set(sample.keys())
    assert not missing, f"fetch_keyword_view item missing keys: {missing}"
    # match_type / status are upper-case strings (NOT enums)
    assert sample["match_type"] in ("EXACT", "PHRASE", "BROAD")
    assert sample["status"] in ("ENABLED", "PAUSED")
