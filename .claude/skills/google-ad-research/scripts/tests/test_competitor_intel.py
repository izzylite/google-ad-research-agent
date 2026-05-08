"""Tests for competitor_intel.py — Phase 5 competitor ad copy + LP extraction.

All tests skip when competitor_intel.py raises ImportError (MODULE_MISSING stub).
Tests become GREEN in Wave 1 (Plan 05-01) when competitor_intel.py is implemented.

Requirements covered: COMP-01, COMP-02, COMP-03.
"""
import json
import sys
from pathlib import Path

import pytest

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


def test_ads_fetched_per_cluster():
    """COMP-01: For each cluster, a Serper call is made using the highest-scored keyword."""
    assert False, "RED — implement in Plan 05-01"


def test_empty_ads_block_ok():
    """COMP-01: Empty ads block from informational cluster produces ads=[] advertisers=[] without exit."""
    assert False, "RED — implement in Plan 05-01"


# ---------------------------------------------------------------------------
# COMP-02: Affiliate filtering
# ---------------------------------------------------------------------------


def test_affiliate_url_param_filter():
    """COMP-02: is_affiliate_url() detects ?ref= param as affiliate; clean URL is not affiliate."""
    assert False, "RED — implement in Plan 05-01"


def test_affiliate_domain_blocklist():
    """COMP-02: is_affiliate_domain() blocks awin1.com; clean domain tesco.com is not blocked."""
    assert False, "RED — implement in Plan 05-01"


def test_affiliate_subdomain_blocked():
    """COMP-02: is_affiliate_domain() blocks subdomains of affiliate domains (sub.awin.com)."""
    assert False, "RED — implement in Plan 05-01"


# ---------------------------------------------------------------------------
# COMP-02: Domain deduplication and advertiser cap
# ---------------------------------------------------------------------------


def test_dedupe_by_domain():
    """COMP-02: dedupe_by_domain() keeps highest-position ad when domain appears twice."""
    assert False, "RED — implement in Plan 05-01"


def test_advertiser_cap_enforcement():
    """COMP-02: After dedup, output has at most 5 entries even when 7 clean unique-domain ads exist."""
    assert False, "RED — implement in Plan 05-01"


# ---------------------------------------------------------------------------
# COMP-03: Tavily LP extraction
# ---------------------------------------------------------------------------


def test_tavily_urls_built_from_top_ads():
    """COMP-03: Top 4 deduped ads produce a list of 4 URL strings taken from the link field."""
    assert False, "RED — implement in Plan 05-01"


def test_tavily_failed_result_persisted():
    """COMP-03: Failed Tavily results produce advertiser entry with extract_status=failed and raw_content=''."""
    assert False, "RED — implement in Plan 05-01"


def test_output_schema_valid():
    """COMP-03 integration: output competitor-intel.json has metadata + clusters keys; each cluster has representative_keyword, ads, advertisers."""
    assert False, "RED — implement in Plan 05-01"
