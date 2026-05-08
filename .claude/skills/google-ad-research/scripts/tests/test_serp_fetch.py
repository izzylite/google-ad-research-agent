"""
Tests for serp_fetch.py — Serper.dev REST → raw/serper.json.

Tests go GREEN in Phase 2 Plan 02 (Wave 2) when serp_fetch.py is implemented.
"""
import json
import sys
from pathlib import Path

import pytest
import httpx

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import serp_fetch  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="serp_fetch.py not yet implemented")


def test_writes_all_blocks(tmp_run_dir, mock_env, serper_fixture):
    """serp_fetch writes organic, peopleAlsoAsk, relatedSearches, and ads to raw/serper.json."""
    import respx

    with respx.mock:
        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json=serper_fixture)
        )
        exit_code = serp_fetch.main_with_args([
            "--run-dir", str(tmp_run_dir),
            "--seeds", "grocery delivery uk",
            "--gl", "uk",
            "--hl", "en-GB",
        ])

    assert exit_code == 0
    serper_path = tmp_run_dir / "raw" / "serper.json"
    assert serper_path.exists(), "raw/serper.json not created"
    data = json.loads(serper_path.read_text())
    assert "by_seed" in data
    seed_entry = data["by_seed"][0]
    assert len(seed_entry["organic"]) > 0, "organic block should be non-empty"
    assert len(seed_entry["peopleAlsoAsk"]) > 0, "peopleAlsoAsk block should be non-empty"
    assert len(seed_entry["relatedSearches"]) > 0, "relatedSearches block should be non-empty"
    assert len(seed_entry["ads"]) > 0, "ads block should be non-empty"


def test_locale_params_passed(tmp_run_dir, mock_env, serper_fixture):
    """gl and hl params from brief are included in the Serper API request body."""
    import respx

    sent_body = {}

    def capture(request):
        sent_body.update(json.loads(request.content))
        return httpx.Response(200, json=serper_fixture)

    with respx.mock:
        respx.post("https://google.serper.dev/search").mock(side_effect=capture)
        serp_fetch.main_with_args([
            "--run-dir", str(tmp_run_dir),
            "--seeds", "grocery delivery uk",
            "--gl", "uk",
            "--hl", "en-GB",
        ])

    assert sent_body.get("gl") == "uk", f"gl missing or wrong in request body: {sent_body}"
    assert sent_body.get("hl") == "en-GB", f"hl missing or wrong in request body: {sent_body}"


def test_locale_persisted(tmp_run_dir, mock_env, serper_fixture):
    """searchParameters.gl and searchParameters.hl appear in the persisted raw/serper.json."""
    import respx

    with respx.mock:
        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json=serper_fixture)
        )
        serp_fetch.main_with_args([
            "--run-dir", str(tmp_run_dir),
            "--seeds", "grocery delivery uk",
            "--gl", "uk",
            "--hl", "en-GB",
        ])

    data = json.loads((tmp_run_dir / "raw" / "serper.json").read_text())
    seed_entry = data["by_seed"][0]
    # locale block
    assert seed_entry["locale"] == {"gl": "uk", "hl": "en-GB"}, (
        f"locale block wrong: {seed_entry.get('locale')}"
    )
    # searchParameters verbatim echo
    sp = seed_entry.get("searchParameters", {})
    assert sp.get("gl") == "uk", f"searchParameters.gl missing: {sp}"


def test_empty_ads_no_error(tmp_run_dir, mock_env, serper_empty_ads_fixture):
    """serp_fetch does not raise when the Serper response has an empty ads array."""
    import respx

    with respx.mock:
        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json=serper_empty_ads_fixture)
        )
        exit_code = serp_fetch.main_with_args([
            "--run-dir", str(tmp_run_dir),
            "--seeds", "grocery delivery uk",
            "--gl", "uk",
            "--hl", "en-GB",
        ])

    assert exit_code == 0, "exit code should be 0 even when ads array is empty"
    data = json.loads((tmp_run_dir / "raw" / "serper.json").read_text())
    seed_entry = data["by_seed"][0]
    assert seed_entry["ads"] == [], "ads should be empty list, not absent"


def test_retries_on_429(tmp_run_dir, mock_env):
    """serp_fetch returns exit code 2 after exhausting retries on HTTP 429."""
    import respx

    # Respond with 429 every time (retries exhausted → HTTPStatusError → exit 2)
    with respx.mock:
        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(429, json={"error": "rate limited"})
        )
        exit_code = serp_fetch.main_with_args([
            "--run-dir", str(tmp_run_dir),
            "--seeds", "grocery delivery uk",
            "--gl", "uk",
            "--hl", "en-GB",
        ])

    assert exit_code == 2, f"expected exit 2 on exhausted 429 retries, got {exit_code}"


def test_exit_code_3_on_401(tmp_run_dir, mock_env):
    """serp_fetch exits with code 3 on HTTP 401 (fatal auth error)."""
    import respx

    with respx.mock:
        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        exit_code = serp_fetch.main_with_args([
            "--run-dir", str(tmp_run_dir),
            "--seeds", "grocery delivery uk",
            "--gl", "uk",
            "--hl", "en-GB",
        ])

    assert exit_code == 3, f"expected exit 3 on 401, got {exit_code}"
