"""RED stub tests for render_report.py — Phase 6 Wave 0.

Requirements covered: RPRT-01, RPRT-02, RPRT-03, RPRT-04 (pipe in table), PRST-01.
All tests skip while render_report.py is absent (MODULE_MISSING guard).

Wave 0: All tests are RED stubs. They turn GREEN in plan 06-03.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module guard — skip all tests while render_report.py does not exist
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import render_report  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="render_report.py not yet implemented")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Local fixtures — tmp_run_dir with all required Phase 6 input files
# ---------------------------------------------------------------------------


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    """Isolated run folder populated from Phase 6 fixtures.

    Creates:
      run/
        brief.md          (from fixtures/brief_sample.md)
        ranked.json       (from fixtures/ranked_full.json)
        clusters.json     (from fixtures/clusters_full.json)
        negatives.json    (from fixtures/negatives_valid.json)
        raw/
          competitor-intel.json  (from fixtures/competitor_intel_full.json)
    """
    run = tmp_path / "2026-05-08T143024Z-grocery-delivery-uk"
    (run / "raw").mkdir(parents=True)

    shutil.copy(FIXTURES_DIR / "brief_sample.md", run / "brief.md")
    shutil.copy(FIXTURES_DIR / "ranked_full.json", run / "ranked.json")
    shutil.copy(FIXTURES_DIR / "clusters_full.json", run / "clusters.json")
    shutil.copy(FIXTURES_DIR / "negatives_valid.json", run / "negatives.json")
    shutil.copy(FIXTURES_DIR / "competitor_intel_full.json", run / "raw" / "competitor-intel.json")

    return run


@pytest.fixture
def ranked_data() -> list[dict]:
    return json.loads((FIXTURES_DIR / "ranked_full.json").read_text(encoding="utf-8"))


@pytest.fixture
def clusters_data() -> dict:
    return json.loads((FIXTURES_DIR / "clusters_full.json").read_text(encoding="utf-8"))


@pytest.fixture
def competitor_intel_data() -> dict:
    return json.loads((FIXTURES_DIR / "competitor_intel_full.json").read_text(encoding="utf-8"))


@pytest.fixture
def negatives_data() -> list[dict]:
    return json.loads((FIXTURES_DIR / "negatives_valid.json").read_text(encoding="utf-8"))


@pytest.fixture
def brief_text() -> str:
    return (FIXTURES_DIR / "brief_sample.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# RPRT-01: Four required sections + "How to read this" present in report.md
# ---------------------------------------------------------------------------


def test_report_md_sections(run_dir, ranked_data, clusters_data,
                             competitor_intel_data, negatives_data, brief_text):
    """RPRT-01/03: render_full_report() output contains all 5 required section headings."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )

    assert "## How to Read This Report" in md
    assert "signal_count" in md          # disclaimer must use exact column name
    assert "## Ranked Keywords" in md
    assert "## Ad Group Clusters" in md
    assert "## Competitor Ad Copy" in md
    assert "## Negative Keywords" in md
    assert "### Strong Negatives" in md
    assert "### Considered Negatives" in md
    assert "### Investigate Negatives" in md


# ---------------------------------------------------------------------------
# RPRT-02: report.json schema with top-level keys + meta.version == "v1"
# ---------------------------------------------------------------------------


def test_report_json_schema(run_dir, ranked_data, clusters_data,
                             competitor_intel_data, negatives_data, brief_text):
    """RPRT-02: build_report_json() produces expected top-level keys and meta.version='v1'."""
    from render_report import build_report_json

    report = build_report_json(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )

    assert set(report.keys()) >= {"meta", "brief", "keywords", "clusters", "competitor_intel", "negatives"}
    assert report["meta"]["version"] == "v1"


# ---------------------------------------------------------------------------
# RPRT-03: "How to read this" disclaimer present with signal_count mention
# ---------------------------------------------------------------------------


def test_how_to_read_present(run_dir, ranked_data, clusters_data,
                              competitor_intel_data, negatives_data, brief_text):
    """RPRT-03: render_full_report() includes the 'How to Read This Report' boilerplate."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )

    assert "## How to Read This Report" in md
    assert "signal_count" in md


# ---------------------------------------------------------------------------
# RPRT-04: Pipe characters in keyword content are escaped in table rows
# ---------------------------------------------------------------------------


def test_pipe_escaped(run_dir, clusters_data, competitor_intel_data,
                      negatives_data, brief_text):
    """RPRT-04: Keywords containing a literal pipe are escaped as \\| in rendered output."""
    from render_report import render_full_report

    # Inject a keyword with a pipe character into ranked data
    ranked_with_pipe = [
        {
            "keyword": "Free | Same Day Delivery",
            "intent": "transactional",
            "match_type": "exact",
            "theme": "",
            "signal_count": 2,
            "source_diversity": 2,
            "sources": ["serper-organic", "serper-paa"],
            "score": 200,
        }
    ]

    md = render_full_report(
        ranked_with_pipe, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )

    # The escaped pipe must appear in the output
    assert r"\|" in md
    # Raw pipe must not appear inside a table row (lines starting with |)
    table_lines = [line for line in md.splitlines() if line.startswith("|")]
    for line in table_lines:
        # Remove escaped pipes first, then check no raw pipe remains in cell content
        stripped = line.replace(r"\|", "")
        # Only separator characters | at column boundaries are allowed
        # Each cell content (between | delimiters) should not contain a raw |
        cells = stripped.split("|")
        for cell in cells[1:-1]:  # skip leading and trailing empty strings
            assert "|" not in cell, f"Raw pipe found in table cell: {cell!r}"


# ---------------------------------------------------------------------------
# PRST-01: render_report.main() writes report.md + report.json into run_dir
# ---------------------------------------------------------------------------


def test_run_folder_complete(run_dir):
    """PRST-01: After render_report.main() runs, report.md and report.json exist in run_dir."""
    from render_report import main

    # main() reads all inputs from run_dir and writes outputs there
    exit_code = main(["--run-dir", str(run_dir)])

    assert exit_code == 0
    assert (run_dir / "report.md").exists()
    assert (run_dir / "report.json").exists()


# ===========================================================================
# Phase 9 Plan 04 — Task 1 tests
#   BIDS-03: Suggested CPC column in enriched table
#   CMPL-04: report.json compliance[] array + forecast{} object
# ===========================================================================


def _ranked_with_suggested_cpc() -> list[dict]:
    """Minimal enriched-ranked rows carrying suggested_max_cpc_micros."""
    return [
        {
            "keyword": "same day grocery delivery",
            "intent": "transactional",
            "match_type": "exact",
            "theme": "delivery",
            "signal_count": 4,
            "source_diversity": 3,
            "sources": ["serper-organic"],
            "score": 71,
            "volume": 2400,
            "cpc_micros": 320000,
            "difficulty": 28,
            "parent_topic": "grocery delivery",
            "suggested_max_cpc_micros": 300000,
            "no_cpc_data": False,
        },
        {
            "keyword": "orphan keyword no bid",
            "intent": "commercial",
            "match_type": "phrase",
            "theme": "",
            "signal_count": 1,
            "source_diversity": 1,
            "sources": ["serper-organic"],
            "score": 10,
            "volume": 100,
            "cpc_micros": None,
            "difficulty": None,
            "parent_topic": None,
            "suggested_max_cpc_micros": None,
            "no_cpc_data": True,
        },
    ]


def test_enriched_table_has_suggested_cpc_column(run_dir, clusters_data,
                                                  competitor_intel_data,
                                                  negatives_data, brief_text):
    """BIDS-03: Volume-enriched table includes a 'Suggested CPC' header."""
    from render_report import render_full_report

    ranked = _ranked_with_suggested_cpc()
    md = render_full_report(
        ranked, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )
    assert "Suggested CPC" in md


def test_enriched_table_renders_usd_format(run_dir, clusters_data,
                                            competitor_intel_data,
                                            negatives_data, brief_text):
    """BIDS-03: suggested_max_cpc_micros=300000 renders as $0.30 (USD with cents)."""
    from render_report import render_full_report

    ranked = _ranked_with_suggested_cpc()
    md = render_full_report(
        ranked, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )
    assert "$0.30" in md


def test_enriched_table_renders_dash_for_null_suggested_cpc(run_dir, clusters_data,
                                                             competitor_intel_data,
                                                             negatives_data, brief_text):
    """BIDS-03: rows with suggested_max_cpc_micros=null render '—' (em-dash)."""
    from render_report import render_full_report

    ranked = _ranked_with_suggested_cpc()
    md = render_full_report(
        ranked, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )
    # Find the row for 'orphan keyword no bid' — it must contain an em-dash
    # in the Suggested CPC cell. We assert presence of em-dash on that row's line.
    rows = [line for line in md.splitlines()
            if line.startswith("|") and "orphan keyword no bid" in line]
    assert rows, "orphan keyword row not found in table"
    # An em-dash must appear in that row (either CPC or Suggested CPC column)
    assert "—" in rows[0]


def test_report_json_forecast_empty_default(run_dir, ranked_data, clusters_data,
                                             competitor_intel_data, negatives_data,
                                             brief_text):
    """CMPL-04/FRCS: build_report_json defaults forecast={} when kwarg omitted."""
    from render_report import build_report_json

    report = build_report_json(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )
    assert "forecast" in report
    assert report["forecast"] == {}


def test_report_json_forecast_populated(run_dir, ranked_data, clusters_data,
                                         competitor_intel_data, negatives_data,
                                         brief_text):
    """CMPL-04/FRCS: forecast kwarg passes through verbatim to report.json."""
    from render_report import build_report_json

    forecast_obj = {
        "metadata": {"schema_version": "v1"},
        "clusters": [
            {"name": "c1", "daily_spend_mid_usd": 5.78, "monthly_spend_mid_usd": 173.4}
        ],
        "campaign_totals": {"daily_spend_mid_usd": 7.12, "monthly_spend_mid_usd": 213.6},
    }
    report = build_report_json(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        forecast=forecast_obj,
    )
    assert report["forecast"]["campaign_totals"]["daily_spend_mid_usd"] == 7.12


def test_report_json_compliance_empty_when_none(run_dir, ranked_data, clusters_data,
                                                 competitor_intel_data, negatives_data,
                                                 brief_text):
    """CMPL-04: when compliance kwarg omitted → report.json['compliance'] == []."""
    from render_report import build_report_json

    report = build_report_json(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )
    assert "compliance" in report
    assert report["compliance"] == []


def test_report_json_compliance_empty_when_matched_verticals_empty(
    run_dir, ranked_data, clusters_data, competitor_intel_data,
    negatives_data, brief_text,
):
    """CMPL-04: compliance={'matched_verticals': []} → report.json['compliance'] == []."""
    from render_report import build_report_json

    report = build_report_json(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        compliance={"matched_verticals": []},
    )
    assert report["compliance"] == []


def test_report_json_compliance_array(run_dir, ranked_data, clusters_data,
                                       competitor_intel_data, negatives_data,
                                       brief_text):
    """CMPL-04: compliance dict → report.json['compliance'] is the matched_verticals[] array."""
    from render_report import build_report_json

    compliance_obj = {
        "matched_verticals": [
            {
                "name": "medical",
                "verification_url": "https://support.google.com/adspolicy/answer/176031",
                "policy_note": "Healthcare verification required.",
                "evidence_tokens": ["clinic", "physician"],
                "evidence_sources": {"brief": ["clinic"], "keywords": []},
                "matched_keyword_count": 0,
            }
        ]
    }
    report = build_report_json(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        compliance=compliance_obj,
    )
    assert isinstance(report["compliance"], list)
    assert len(report["compliance"]) == 1
    assert report["compliance"][0]["name"] == "medical"
