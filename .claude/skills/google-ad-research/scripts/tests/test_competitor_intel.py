"""Tests for competitor_intel.py — Phase 5 competitor ad copy + LP extraction.

All tests skip when competitor_intel.py raises ImportError (MODULE_MISSING stub).
Tests become GREEN in Wave 1 (Plan 05-01) when competitor_intel.py is implemented.

Requirements covered: COMP-01, COMP-02, COMP-03.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest
import respx
import httpx

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import competitor_intel  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="competitor_intel.py not yet implemented")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# COMP-01: Per-cluster Serper re-query
# ---------------------------------------------------------------------------


def test_ads_fetched_per_cluster(tmp_run_dir, mock_env, monkeypatch):
    """COMP-01: For each cluster, a Serper call is made using the highest-scored keyword."""
    from competitor_intel import main_with_args

    # Copy clusters_phase5.json (3 clusters) into tmp_run_dir
    shutil.copy(FIXTURES_DIR / "clusters_phase5.json", tmp_run_dir / "clusters.json")

    serper_raw = json.loads((FIXTURES_DIR / "serper_ads_raw.json").read_text())

    call_count = 0

    def mock_fetch_seed(client, seed, *, gl, hl, num, api_key):
        nonlocal call_count
        call_count += 1
        return serper_raw

    monkeypatch.setattr("competitor_intel.fetch_seed", mock_fetch_seed)

    exit_code = main_with_args(["--run-dir", str(tmp_run_dir)])

    assert exit_code == 0
    # 3 clusters => 3 Serper calls
    assert call_count == 3

    out = json.loads((tmp_run_dir / "raw" / "competitor-intel.json").read_text())
    assert "clusters" in out
    assert len(out["clusters"]) == 3


def test_empty_ads_block_ok(tmp_run_dir, mock_env, monkeypatch):
    """COMP-01: Empty ads/organic block produces ads=[] advertisers=[] without exit.

    Phase 12: post-Tavily refactor — when both ads and organic are empty after
    fallback, advertisers list is empty (no LP extraction performed in Python;
    WebFetch in Phase 5 Step 19 handles LP content).
    """
    from competitor_intel import main_with_args

    # Single-cluster clusters.json using the informational keyword
    single_cluster = {
        "metadata": {},
        "clusters": [
            {
                "name": "delivery_how_informational",
                "intent": "informational",
                "keywords": [
                    {"keyword": "how does grocery delivery work", "score": 40}
                ],
            }
        ],
        "orphans": [],
    }
    (tmp_run_dir / "clusters.json").write_text(json.dumps(single_cluster), encoding="utf-8")

    # Both ads AND organic empty so the fallback yields no advertisers.
    serper_empty = {
        "searchParameters": {"q": "how does grocery delivery work", "gl": "uk", "hl": "en-GB"},
        "organic": [],
        "ads": [],
        "peopleAlsoAsk": [],
        "relatedSearches": [],
        "credits": 1,
    }

    monkeypatch.setattr("competitor_intel.fetch_seed", lambda *a, **kw: serper_empty)

    exit_code = main_with_args(["--run-dir", str(tmp_run_dir)])

    assert exit_code == 0

    out = json.loads((tmp_run_dir / "raw" / "competitor-intel.json").read_text())
    cluster = out["clusters"]["delivery_how_informational"]
    assert cluster["ads"] == []
    assert cluster["advertisers"] == []


# ---------------------------------------------------------------------------
# COMP-02: Affiliate filtering
# ---------------------------------------------------------------------------


def test_affiliate_url_param_filter():
    """COMP-02: is_affiliate_url() detects ?ref= param as affiliate; clean URL is not affiliate."""
    from competitor_intel import is_affiliate_url

    assert is_affiliate_url("https://quidco.com/grocery?ref=abc123") is True
    assert is_affiliate_url("https://ocado.com/landing/same-day") is False


def test_affiliate_domain_blocklist():
    """COMP-02: is_affiliate_domain() blocks awin1.com; clean domain tesco.com is not blocked."""
    from competitor_intel import is_affiliate_domain

    assert is_affiliate_domain("https://www.awin1.com/cread.php") is True
    assert is_affiliate_domain("https://www.tesco.com/delivery") is False


def test_affiliate_subdomain_blocked():
    """COMP-02: is_affiliate_domain() blocks subdomains of affiliate domains (sub.awin.com)."""
    from competitor_intel import is_affiliate_domain

    assert is_affiliate_domain("https://sub.awin.com/x") is True


# ---------------------------------------------------------------------------
# COMP-02: Domain deduplication and advertiser cap
# ---------------------------------------------------------------------------


def test_dedupe_by_domain():
    """COMP-02: dedupe_by_domain() keeps highest-position ad when domain appears twice."""
    from competitor_intel import dedupe_by_domain

    ads = [
        {"displayUrl": "tesco.com/offer", "link": "https://tesco.com/offer", "position": 4, "title": "Tesco A"},
        {"displayUrl": "tesco.com/delivery", "link": "https://tesco.com/delivery", "position": 1, "title": "Tesco B"},
    ]
    result = dedupe_by_domain(ads)

    assert len(result) == 1
    assert result[0]["position"] == 1


def test_advertiser_cap_enforcement():
    """COMP-02: After dedup, output has at most 5 entries even when 7 clean unique-domain ads exist."""
    from competitor_intel import filter_ads, dedupe_by_domain, MAX_ADVERTISERS

    # 7 unique-domain clean ads
    ads = [
        {"displayUrl": f"domain{i}.com/path", "link": f"https://domain{i}.com/page", "position": i, "title": f"Ad {i}"}
        for i in range(1, 8)
    ]
    clean_ads, _ = filter_ads(ads)
    deduped = dedupe_by_domain(clean_ads)
    top = deduped[:MAX_ADVERTISERS]

    assert len(top) <= 5
    assert len(top) == MAX_ADVERTISERS


# ---------------------------------------------------------------------------
# COMP-03 (post-Phase-12): Advertisers list derived from Serper top_ads;
# LP extraction moved to Claude WebFetch in Phase 5 Step 19 (SKILL.md).
# ---------------------------------------------------------------------------


def test_advertiser_urls_built_from_top_ads():
    """COMP-03 (post-Phase-12): Top 5 deduped ads produce URL list from the link field.

    Originally named test_tavily_urls_built_from_top_ads; renamed and de-Tavilyfied
    in Plan 12-02. The URL list is now consumed by Claude WebFetch in Phase 5
    Step 19, not a Python LP-extract client.
    """
    from competitor_intel import filter_ads, dedupe_by_domain

    serper_raw = json.loads((FIXTURES_DIR / "serper_ads_raw.json").read_text())
    # serper_ads_raw has 6 ads: 2 affiliate (quidco + awin1), 2 tesco (duplicate domain),
    # 1 ocado, 1 sainsburys — after filter: 4 clean, after dedupe: 3 unique domains
    ads = serper_raw["ads"]
    clean_ads, filtered_count = filter_ads(ads)
    deduped = dedupe_by_domain(clean_ads)
    top5 = deduped[:5]

    lp_urls = [a["link"] for a in top5 if a.get("link")]

    # All URLs come from the link field
    for url in lp_urls:
        assert url.startswith("https://")
    # No affiliate URLs in the result
    from competitor_intel import is_affiliate_url, is_affiliate_domain
    for url in lp_urls:
        assert not is_affiliate_url(url)
        assert not is_affiliate_domain(url)


def test_advertisers_serper_only_shape(tmp_run_dir, mock_env, monkeypatch):
    """COMP-03 (post-Phase-12): advertisers entries carry Serper-only fields.

    Replaces the Phase-11 test_tavily_failed_result_persisted (asserted on
    raw_content + extract_status — fields no longer present). Wave-0 contract
    locked in test_advertisers_shape_post_phase12: each advertiser has exactly
    {domain, url, title, description, position}.
    """
    from competitor_intel import main_with_args

    single_cluster = {
        "metadata": {},
        "clusters": [
            {
                "name": "same_day_delivery_transactional",
                "intent": "transactional",
                "keywords": [{"keyword": "order same day grocery delivery", "score": 95}],
            }
        ],
        "orphans": [],
    }
    (tmp_run_dir / "clusters.json").write_text(json.dumps(single_cluster), encoding="utf-8")

    serper_raw = json.loads((FIXTURES_DIR / "serper_ads_raw.json").read_text())
    monkeypatch.setattr("competitor_intel.fetch_seed", lambda *a, **kw: serper_raw)

    exit_code = main_with_args(["--run-dir", str(tmp_run_dir)])
    assert exit_code == 0

    out = json.loads((tmp_run_dir / "raw" / "competitor-intel.json").read_text())
    advertisers = out["clusters"]["same_day_delivery_transactional"]["advertisers"]

    assert advertisers, "at least one advertiser expected from serper_ads_raw fixture"
    expected_keys = {"domain", "url", "title", "description", "position"}
    for entry in advertisers:
        assert set(entry.keys()) == expected_keys, (
            f"advertisers entry has wrong keys; got {set(entry.keys())}, "
            f"expected exactly {expected_keys}"
        )
        # Phase-11 Tavily fields must NOT appear
        assert "raw_content" not in entry
        assert "tavily_fetched_at" not in entry
        assert "extract_status" not in entry


def test_output_schema_valid(tmp_run_dir, mock_env, monkeypatch):
    """COMP-03 integration: output competitor-intel.json has metadata + clusters keys; each cluster has representative_keyword, ads, advertisers."""
    from competitor_intel import main_with_args

    shutil.copy(FIXTURES_DIR / "clusters_phase5.json", tmp_run_dir / "clusters.json")

    serper_raw = json.loads((FIXTURES_DIR / "serper_ads_raw.json").read_text())
    monkeypatch.setattr("competitor_intel.fetch_seed", lambda *a, **kw: serper_raw)

    exit_code = main_with_args(["--run-dir", str(tmp_run_dir)])
    assert exit_code == 0

    out = json.loads((tmp_run_dir / "raw" / "competitor-intel.json").read_text())

    # Top-level keys
    assert "metadata" in out
    assert "clusters" in out
    assert "generated_at" in out["metadata"]

    # Each cluster has required keys
    for cluster_name, cluster_data in out["clusters"].items():
        assert "representative_keyword" in cluster_data, f"{cluster_name} missing representative_keyword"
        assert "ads" in cluster_data, f"{cluster_name} missing ads"
        assert "advertisers" in cluster_data, f"{cluster_name} missing advertisers"


# ---------------------------------------------------------------------------
# Phase 12 WFCH-03: advertisers entries carry Serper fields only;
# no Tavily raw_content / tavily_fetched_at / extract_status.
# ---------------------------------------------------------------------------
def test_advertisers_shape_post_phase12():
    """WFCH-03: competitor_intel.py source contains no Tavily-shape fields.

    RED against Phase 11 (current competitor_intel.py imports tavily and writes
    raw_content + tavily_fetched_at into advertisers entries). Wave 1 plan 12-02
    rewrites the helper to emit only Serper fields:
        {domain, url, title, description, position}
    Tavily fields {raw_content, tavily_fetched_at} are deleted; extract_status
    (if any) moves to raw/competitor-landing-pages.json under WFCH-02.
    """
    if MODULE_MISSING:
        pytest.skip("competitor_intel not yet implemented")
    import inspect as _i
    src = _i.getsource(competitor_intel)
    # Source-level invariants — Tavily fields must NOT appear in source text
    assert "raw_content" not in src, \
        "WFCH-03: competitor_intel.py must not reference raw_content (Tavily-shape field)"
    assert "tavily_fetched_at" not in src, \
        "WFCH-03: competitor_intel.py must not reference tavily_fetched_at"
    assert "tavily" not in src.lower(), \
        "WFCH-03: competitor_intel.py must contain no Tavily references"
    # No Tavily-prefixed symbols in module namespace
    tavily_symbols = [m for m in dir(competitor_intel) if "tavily" in m.lower()]
    assert not tavily_symbols, \
        f"WFCH-03: competitor_intel namespace must contain no tavily-prefixed symbols; got {tavily_symbols}"
