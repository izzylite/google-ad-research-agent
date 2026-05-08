"""
Tests for tavily_extract.py — Tavily SDK extract → raw/tavily-<domain>.json.

RED state: tests are written and will FAIL until tavily_extract.py is implemented.
GREEN state: achieved when tavily_extract.py is fully implemented (Phase 2 Plan 03).
"""
import json
import sys
from pathlib import Path

import pytest

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import tavily_extract  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="tavily_extract.py not yet implemented")


def test_caps_enforced(tmp_run_dir, mock_env, monkeypatch):
    """tavily_extract processes at most 5 competitors × 5 URLs each (hard caps)."""
    calls = []

    def fake_extract(self, **kwargs):
        calls.append(kwargs)
        return {
            "results": [{"url": kwargs["urls"][0], "raw_content": "content"}],
            "failed_results": [],
            "response_time": 1.0,
            "usage": {"credits_used": 1},
        }

    monkeypatch.setattr("tavily.TavilyClient.extract", fake_extract)

    # Build 7 competitors, each with 8 URLs — caps must trim to 5 × 5
    competitors = []
    for i in range(7):
        domain = f"competitor{i}.com"
        urls = ",".join(f"https://competitor{i}.com/page{j}" for j in range(8))
        competitors.append(f"{domain}:{urls}")

    argv = ["tavily_extract.py", "--run-dir", str(tmp_run_dir)]
    for c in competitors:
        argv += ["--competitor", c]

    exit_code = tavily_extract.main_with_args(argv)
    assert exit_code == 0

    # At most 5 competitors processed
    assert len(calls) <= 5, f"Expected ≤5 extract calls, got {len(calls)}"

    # At most 5 URLs per call
    for call in calls:
        assert len(call["urls"]) <= 5, f"Expected ≤5 URLs per call, got {len(call['urls'])}"

    # Exactly 5 output files written
    raw_dir = tmp_run_dir / "raw"
    tavily_files = list(raw_dir.glob("tavily-*.json"))
    assert len(tavily_files) == 5, f"Expected 5 output files, got {len(tavily_files)}"


def test_uses_basic_depth(tmp_run_dir, mock_env, tavily_fixture, monkeypatch):
    """TavilyClient.extract is called with extract_depth='basic'."""
    captured_kwargs = {}

    def fake_extract(self, **kwargs):
        captured_kwargs.update(kwargs)
        return tavily_fixture

    monkeypatch.setattr("tavily.TavilyClient.extract", fake_extract)

    argv = [
        "tavily_extract.py",
        "--run-dir", str(tmp_run_dir),
        "--competitor", "tesco.com:https://tesco.com/groceries/delivery,https://tesco.com/groceries/same-day",
    ]
    exit_code = tavily_extract.main_with_args(argv)
    assert exit_code == 0

    assert "extract_depth" in captured_kwargs, "extract_depth was not passed to client.extract()"
    assert captured_kwargs["extract_depth"] == "basic", (
        f"extract_depth must be 'basic', got {captured_kwargs['extract_depth']!r}"
    )


def test_failed_results_persisted(tmp_run_dir, mock_env, tavily_fixture, monkeypatch):
    """failed_results from Tavily response are logged and persisted to disk (not silently dropped)."""

    def fake_extract(self, **kwargs):
        return tavily_fixture

    monkeypatch.setattr("tavily.TavilyClient.extract", fake_extract)

    argv = [
        "tavily_extract.py",
        "--run-dir", str(tmp_run_dir),
        "--competitor", "tesco.com:https://tesco.com/groceries/delivery,https://tesco.com/groceries/same-day",
    ]
    exit_code = tavily_extract.main_with_args(argv)
    assert exit_code == 0

    out_path = tmp_run_dir / "raw" / "tavily-tesco-com.json"
    assert out_path.exists(), f"Expected output file at {out_path}"

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "results" in data, "Output JSON missing 'results' key"
    assert "failed_results" in data, "Output JSON missing 'failed_results' key"
    assert len(data["results"]) == 1, f"Expected 1 result, got {len(data['results'])}"
    assert len(data["failed_results"]) == 1, f"Expected 1 failed_result, got {len(data['failed_results'])}"


def test_exit_code_3_on_auth_error(tmp_run_dir, mock_env, monkeypatch):
    """tavily_extract exits with code 3 when Tavily raises InvalidAPIKeyError."""
    from tavily import InvalidAPIKeyError

    def fake_extract(self, **kwargs):
        raise InvalidAPIKeyError("Invalid API key")

    monkeypatch.setattr("tavily.TavilyClient.extract", fake_extract)

    argv = [
        "tavily_extract.py",
        "--run-dir", str(tmp_run_dir),
        "--competitor", "tesco.com:https://tesco.com/groceries/delivery",
    ]
    exit_code = tavily_extract.main_with_args(argv)
    assert exit_code == 3, f"Expected exit code 3 on auth error, got {exit_code}"
