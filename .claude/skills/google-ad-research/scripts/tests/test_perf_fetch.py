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


# ---------------------------------------------------------------------------
# Phase 15 Wave 0 — --campaign-filter RED stubs (CAMP-02 / CAMP-06)
#
# Each test guards on `campaign_filter` kwarg presence via signature
# inspection so the suite SKIPs cleanly until Wave 2 plan 15-01 lands the
# kwarg + GAQL clause on all 4 fetch functions.
#
# The existing `_FakeGAdsClient` captures only the LAST query passed to
# `search_stream`. `fetch_perf` issues TWO calls (campaigns + ad_groups)
# and `fetch_existing_negatives` issues TWO try/except calls — for the
# parametrized all-four test we use a list-recording fake variant so we
# can assert the filter appears in EVERY captured query.
# ---------------------------------------------------------------------------


def _skip_unless_campaign_filter() -> None:
    """Per-function guard — Wave 2 plan 15-01 lands --campaign-filter kwarg."""
    if PF_MISSING:
        pytest.skip("perf_fetch not importable (google-ads SDK env)")
    import inspect
    sig = inspect.signature(perf_fetch.fetch_search_terms)
    if "campaign_filter" not in sig.parameters:
        pytest.skip(
            "Wave 2 plan 15-01 not yet landed: campaign_filter kwarg missing"
        )


class _RecordingGoogleAdsService:
    """Variant of _FakeGoogleAdsService that records every query in a list.

    Used by fetch_perf / fetch_existing_negatives tests which issue multiple
    GAQL calls per fetch — single-slot `captured["query"]` would only retain
    the last one.
    """
    def __init__(self, queries: list[str], rows: list[_FakeRow]) -> None:
        self._queries = queries
        self._rows = rows

    def search_stream(self, customer_id: str, query: str):
        self._queries.append(query)
        yield _FakeBatch(self._rows)


class _RecordingFakeGAdsClient:
    def __init__(self, rows: list[_FakeRow] | None = None) -> None:
        self.captured: dict = {"queries": []}
        self._rows = rows or []

    def get_service(self, name: str):
        assert name == "GoogleAdsService"
        return _RecordingGoogleAdsService(self.captured["queries"], self._rows)


def test_campaign_filter_single_value_gaql():
    """CAMP-02: single campaign_filter value → `campaign.name = '<name>'` clause."""
    _skip_unless_campaign_filter()
    client = _FakeGAdsClient(rows=[])
    perf_fetch.fetch_search_terms(
        client, "9999999999", days=30,
        campaign_filter=["Search | Lake Worth Accident Exams | Manual CPC"],
    )
    query = client.captured.get("query", "")
    assert "campaign.name = 'Search | Lake Worth Accident Exams | Manual CPC'" in query


def test_campaign_filter_list_uses_in_clause():
    """CAMP-02: list of ≥2 values → `campaign.name IN ('A', 'B')` clause."""
    _skip_unless_campaign_filter()
    client = _FakeGAdsClient(rows=[])
    perf_fetch.fetch_search_terms(
        client, "9999999999", days=30,
        campaign_filter=["A", "B"],
    )
    query = client.captured.get("query", "")
    assert "campaign.name IN ('A', 'B')" in query


def test_campaign_filter_escapes_single_quote():
    """CAMP-02: single quote in campaign name doubled (SQL escape)."""
    _skip_unless_campaign_filter()
    client = _FakeGAdsClient(rows=[])
    perf_fetch.fetch_search_terms(
        client, "9999999999", days=30,
        campaign_filter=["O'Brien Auto"],
    )
    query = client.captured.get("query", "")
    assert "campaign.name = 'O''Brien Auto'" in query


def test_campaign_filter_absent_no_clause():
    """CAMP-04 backward compat: campaign_filter=None → no `campaign.name` clause.

    Note: existing queries SELECT `campaign.name` as a column. The contract
    here is that the WHERE clause does NOT add a `campaign.name = ` or
    `campaign.name IN` filter — i.e. no equality/membership predicate on
    campaign.name is added when filter omitted.
    """
    _skip_unless_campaign_filter()
    client = _FakeGAdsClient(rows=[])
    perf_fetch.fetch_search_terms(client, "9999999999", days=30, campaign_filter=None)
    query = client.captured.get("query", "")
    assert "campaign.name =" not in query
    assert "campaign.name IN" not in query


def test_campaign_filter_empty_list_treated_as_absent():
    """CAMP-04: empty list → graceful degrade, no filter clause added."""
    _skip_unless_campaign_filter()
    client = _FakeGAdsClient(rows=[])
    perf_fetch.fetch_search_terms(client, "9999999999", days=30, campaign_filter=[])
    query = client.captured.get("query", "")
    assert "campaign.name =" not in query
    assert "campaign.name IN" not in query


@pytest.mark.parametrize(
    "fetch_name",
    ["fetch_search_terms", "fetch_perf", "fetch_existing_negatives", "fetch_keyword_view"],
)
def test_campaign_filter_applied_to_all_four_fetches(fetch_name):
    """CAMP-02: every one of the 4 perf_fetch fetch functions threads
    campaign_filter into its outgoing GAQL.

    Uses _RecordingFakeGAdsClient because `fetch_perf` issues 2 queries
    (campaigns + ad_groups) and `fetch_existing_negatives` issues 2
    (campaign-level + ad-group-level negatives) — every captured query
    must carry the filter.
    """
    _skip_unless_campaign_filter()
    client = _RecordingFakeGAdsClient(rows=[])
    fn = getattr(perf_fetch, fetch_name)
    # fetch_existing_negatives signature does not take `days`; pass kwargs
    # carefully per function.
    if fetch_name == "fetch_existing_negatives":
        fn(client, "9999999999", campaign_filter=["X"])
    else:
        fn(client, "9999999999", days=30, campaign_filter=["X"])
    queries = client.captured["queries"]
    assert queries, f"{fetch_name} did not issue any GAQL queries"
    for q in queries:
        assert "campaign.name = 'X'" in q, (
            f"{fetch_name} query missing campaign.name filter: {q!r}"
        )
