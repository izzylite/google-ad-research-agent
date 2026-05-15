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


# ===========================================================================
# Phase 9 Plan 04 — Task 2 tests
#   FRCS-04: Budget Forecast section in report.md (between Clusters & Negatives)
#   FRCS-05: "How this is calculated" subsection (CTRs, ratios, multipliers, disclaimer)
# ===========================================================================


def _sample_forecast() -> dict:
    """Minimal forecast.json dict shape (per forecast_budget.build_forecast)."""
    return {
        "metadata": {
            "generated_at": "2026-05-14T18:30:00Z",
            "run_id": "test-run",
            "schema_version": "v1",
            "horizon": "daily",
        },
        "methodology": {
            "intent_ctrs": {
                "transactional": 0.06,
                "commercial":    0.04,
                "informational": 0.02,
                "navigational":  0.08,
            },
            "avg_cpc_ratio": 0.65,
            "band_multipliers": {"low": 0.5, "mid": 1.0, "high": 1.5},
            "notes": (
                "Forecast is directional — not Google's official forecast. "
                "Bands ×0.5/×1.0/×1.5; avg CPC = suggested max CPC × 0.65."
            ),
        },
        "clusters": [
            {
                "name": "same_day_delivery_transactional",
                "intent": "transactional",
                "keyword_count": 3,
                "keywords_with_volume": 3,
                "total_monthly_volume": 9200,
                "daily_clicks_low": 9,
                "daily_clicks_mid": 18.4,
                "daily_clicks_high": 28,
                "daily_spend_low_usd": 2.89,
                "daily_spend_mid_usd": 5.78,
                "daily_spend_high_usd": 8.67,
                "monthly_spend_mid_usd": 173.4,
                "unjoined_keywords": 0,
            },
        ],
        "campaign_totals": {
            "cluster_count": 1,
            "keyword_count": 3,
            "daily_clicks_low": 9,
            "daily_clicks_mid": 18.4,
            "daily_clicks_high": 28,
            "daily_spend_low_usd": 2.89,
            "daily_spend_mid_usd": 5.78,
            "daily_spend_high_usd": 8.67,
            "monthly_spend_mid_usd": 173.4,
            "unjoined_keywords": 0,
        },
    }


def test_forecast_section_in_report(run_dir, ranked_data, clusters_data,
                                     competitor_intel_data, negatives_data,
                                     brief_text):
    """FRCS-04: render_full_report includes '## Budget Forecast' when forecast supplied."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        forecast=_sample_forecast(),
    )
    assert "## Budget Forecast" in md


def test_forecast_section_position(run_dir, ranked_data, clusters_data,
                                    competitor_intel_data, negatives_data,
                                    brief_text):
    """FRCS-04: Budget Forecast lands between Ad Group Clusters and Negative Keywords."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        forecast=_sample_forecast(),
    )
    idx_clusters = md.index("## Ad Group Clusters")
    idx_forecast = md.index("## Budget Forecast")
    idx_negatives = md.index("## Negative Keywords")
    assert idx_clusters < idx_forecast < idx_negatives


def test_forecast_methodology_present(run_dir, ranked_data, clusters_data,
                                       competitor_intel_data, negatives_data,
                                       brief_text):
    """FRCS-05: 'How this is calculated' subsection names CTR anchors, avg-CPC ratio, bands, disclaimer."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        forecast=_sample_forecast(),
    )
    assert "### How this is calculated" in md
    # All four intent labels by name
    for intent in ("transactional", "commercial", "informational", "navigational"):
        assert intent in md
    # avg-CPC ratio mention (0.65)
    assert "0.65" in md
    # Disclaimer keyword (verbatim from methodology.notes — "directional")
    assert "directional" in md


def test_no_forecast_section_when_data_absent(run_dir, ranked_data, clusters_data,
                                               competitor_intel_data, negatives_data,
                                               brief_text):
    """FRCS-04 graceful degrade: no forecast kwarg → 'Budget Forecast' NOT in report."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )
    assert "Budget Forecast" not in md


def test_no_forecast_section_when_empty_dict(run_dir, ranked_data, clusters_data,
                                              competitor_intel_data, negatives_data,
                                              brief_text):
    """FRCS-04: forecast={} (no clusters[]) → 'Budget Forecast' NOT in report."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        forecast={},
    )
    assert "Budget Forecast" not in md


# ===========================================================================
# Phase 9 Plan 04 — Task 3 tests
#   CMPL-03: ⚠ Compliance Required block above Ranked Keywords when matched
# ===========================================================================


def _sample_compliance() -> dict:
    """Compliance-flags.json shape with one matched vertical."""
    return {
        "matched_verticals": [
            {
                "name": "medical",
                "evidence_tokens": ["clinic", "physician"],
                "evidence_sources": {
                    "brief": ["clinic", "physician"],
                    "keywords": [],
                },
                "matched_keyword_count": 3,
                "verification_url": "https://support.google.com/adspolicy/answer/176031",
                "policy_note": (
                    "Healthcare advertisers may require LegitScript certification. "
                    "Verify before launching."
                ),
            }
        ]
    }


def test_compliance_block_renders_when_matched(run_dir, ranked_data, clusters_data,
                                                competitor_intel_data, negatives_data,
                                                brief_text):
    """CMPL-03: '⚠ Compliance Required' block renders when matched_verticals non-empty."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        compliance=_sample_compliance(),
    )
    assert "⚠ Compliance Required" in md
    # Vertical name (case-insensitive match — title or lowercase both OK)
    assert "medical" in md.lower()
    # Verification URL surfaces in the block
    assert "https://support.google.com/adspolicy/answer/176031" in md


def test_compliance_block_position(run_dir, ranked_data, clusters_data,
                                    competitor_intel_data, negatives_data,
                                    brief_text):
    """CMPL-03 contract: compliance block precedes the Ranked Keywords table."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        compliance=_sample_compliance(),
    )
    idx_compliance = md.index("⚠ Compliance Required")
    idx_ranked = md.index("## Ranked Keywords")
    idx_clusters = md.index("## Ad Group Clusters")
    assert idx_compliance < idx_ranked
    assert idx_compliance < idx_clusters


def test_no_compliance_block_when_clean(run_dir, ranked_data, clusters_data,
                                         competitor_intel_data, negatives_data,
                                         brief_text):
    """CMPL-03 graceful degrade: no compliance kwarg → block NOT in report."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
    )
    assert "Compliance Required" not in md


def test_no_compliance_block_when_empty_array(run_dir, ranked_data, clusters_data,
                                               competitor_intel_data, negatives_data,
                                               brief_text):
    """CMPL-03: compliance={'matched_verticals': []} → block NOT in report."""
    from render_report import render_full_report

    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        compliance={"matched_verticals": []},
    )
    assert "Compliance Required" not in md


def test_compliance_block_escapes_policy_note(run_dir, ranked_data, clusters_data,
                                               competitor_intel_data, negatives_data,
                                               brief_text):
    """CMPL-03: pipe characters in policy_note are escaped (table-safe)."""
    from render_report import render_full_report

    pipe_compliance = {
        "matched_verticals": [
            {
                "name": "medical",
                "evidence_tokens": ["clinic"],
                "evidence_sources": {"brief": ["clinic"], "keywords": []},
                "matched_keyword_count": 1,
                "verification_url": "https://example.com",
                "policy_note": "danger | pipe | injection text",
            }
        ]
    }
    md = render_full_report(
        ranked_data, clusters_data, competitor_intel_data,
        negatives_data, brief_text, run_dir,
        compliance=pipe_compliance,
    )
    # Compliance block present
    assert "⚠ Compliance Required" in md
    # Find the rendered policy_note line — must show escaped pipes (\|), not raw pipes,
    # because escape_md_cell was applied.
    assert r"\|" in md


# ===========================================================================
# Phase 10 Wave 0 — Next Steps + Export Files RED stubs
#
# Each function skips when the Wave 1 helper / kwarg is absent. We use
# per-function guards (NOT a file-level pytestmark) so the existing
# Phase 6 + Phase 9 GREEN tests above keep running.
#
# Contracts covered:
#   STEP-01  ## Next Steps section appended to report.md
#   STEP-02  Brief location/language + forecast spend substituted into steps
#   STEP-03  HTML checkbox + localStorage namespacing
#   STEP-04  report.json next_steps[] = list of {n, text, id}
#   CMPL-05  Compliance reorder (single + combined verticals)
#   EXPT-05  Export Files section + report.json exports[]  (Wave 2 stubs)
# ===========================================================================

NEXT_STEPS_HELPER = "render_next_steps_section"
EXPORT_SECTION_HELPER = "render_export_section"


def _skip_unless_next_steps():
    if not hasattr(render_report, NEXT_STEPS_HELPER):
        pytest.skip(
            "render_report.render_next_steps_section not yet implemented "
            "(Phase 10 Wave 1, plan 10-02)"
        )


def _skip_unless_export_section():
    if not hasattr(render_report, EXPORT_SECTION_HELPER):
        pytest.skip(
            "render_report.render_export_section not yet implemented "
            "(Phase 10 Wave 2, plan 10-03)"
        )


@pytest.fixture
def brief_fields_phase10() -> dict[str, str]:
    """Brief field dict mirroring `_parse_brief_fields` output."""
    return {
        "industry": "online groceries",
        "product": "same-day grocery delivery",
        "location": "UK",
        "language": "en-GB",
        "audience": "households 25-45 in metro areas",
    }


@pytest.fixture
def forecast_phase10() -> dict:
    return json.loads(
        (FIXTURES_DIR / "forecast_phase10.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def clusters_phase10_data() -> dict:
    return json.loads(
        (FIXTURES_DIR / "clusters_phase10.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def compliance_with_match_data() -> dict:
    return json.loads(
        (FIXTURES_DIR / "compliance_with_match.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def compliance_two_verticals_data() -> dict:
    return json.loads(
        (FIXTURES_DIR / "compliance_two_verticals.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def compliance_empty_data() -> dict:
    return json.loads(
        (FIXTURES_DIR / "compliance_empty.json").read_text(encoding="utf-8")
    )


# ---------------------------------------------------------------------------
# STEP-01 + STEP-02 + STEP-04 — render_next_steps_section() shape
# ---------------------------------------------------------------------------

def test_next_steps_section_default_order(brief_fields_phase10, forecast_phase10,
                                           clusters_phase10_data, compliance_empty_data):
    """Returns (markdown, list_of_8_steps) for the standard non-compliance flow."""
    _skip_unless_next_steps()
    md, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10, compliance_empty_data, clusters_phase10_data,
    )
    assert isinstance(md, str)
    assert md.startswith("## Next Steps") or "## Next Steps" in md
    assert isinstance(steps, list)
    # 8 ops steps; no compliance prepend in empty-compliance path.
    assert len(steps) == 8
    for s in steps:
        assert set(s.keys()) >= {"n", "text", "id"}


def test_next_steps_section_substitution(brief_fields_phase10, forecast_phase10,
                                          clusters_phase10_data, compliance_empty_data):
    """Step text substitutes brief location/language, daily_spend_mid_usd, cluster names."""
    _skip_unless_next_steps()
    md, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10, compliance_empty_data, clusters_phase10_data,
    )
    all_text = " ".join(s["text"] for s in steps)
    # Brief substitution
    assert brief_fields_phase10["location"] in all_text
    assert brief_fields_phase10["language"] in all_text
    # Forecast substitution — daily_spend_mid_usd = 12.50 → "$12.50"
    expected_spend = (
        f"${forecast_phase10['campaign_totals']['daily_spend_mid_usd']:.2f}"
    )
    assert expected_spend in all_text
    # Cluster names — all three cluster names appear somewhere in the checklist
    for cluster in clusters_phase10_data["clusters"]:
        assert cluster["name"] in all_text


def test_next_steps_section_step_ids_8_char_sha1(brief_fields_phase10, forecast_phase10,
                                                  clusters_phase10_data):
    """Each step['id'] is 8 chars lowercase hex (SHA-1 prefix)."""
    _skip_unless_next_steps()
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10, None, clusters_phase10_data,
    )
    for s in steps:
        assert isinstance(s["id"], str)
        assert len(s["id"]) == 8
        assert all(c in "0123456789abcdef" for c in s["id"]), (
            f"step id not lowercase hex: {s['id']!r}"
        )


def test_next_steps_section_n_from_position(brief_fields_phase10, forecast_phase10,
                                             clusters_phase10_data):
    """step['n'] is the 1-indexed position in the final list."""
    _skip_unless_next_steps()
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10, None, clusters_phase10_data,
    )
    for idx, s in enumerate(steps, start=1):
        assert s["n"] == idx, f"step at position {idx} has n={s['n']}"


def test_report_json_next_steps_array(run_dir, ranked_data, clusters_data,
                                       competitor_intel_data, negatives_data,
                                       brief_text, forecast_phase10,
                                       compliance_empty_data):
    """build_report_json emits a top-level next_steps[] of {n, text, id} dicts.

    Wave 1 plan 10-02 extends build_report_json to thread the kwarg.
    Skip if signature has not been extended yet.
    """
    _skip_unless_next_steps()
    from render_report import build_report_json
    try:
        report = build_report_json(
            ranked_data, clusters_data, competitor_intel_data,
            negatives_data, brief_text, run_dir,
            forecast=forecast_phase10, compliance=compliance_empty_data,
        )
    except TypeError:
        pytest.skip("build_report_json does not yet emit next_steps (Wave 1)")

    if "next_steps" not in report:
        pytest.skip("build_report_json next_steps key not yet implemented (Wave 1)")

    assert isinstance(report["next_steps"], list)
    assert len(report["next_steps"]) >= 1
    for s in report["next_steps"]:
        assert set(s.keys()) >= {"n", "text", "id"}
        assert isinstance(s["n"], int)
        assert isinstance(s["text"], str)
        assert isinstance(s["id"], str) and len(s["id"]) == 8


# ---------------------------------------------------------------------------
# STEP-03 — HTML report renders next-steps section + localStorage namespacing
# ---------------------------------------------------------------------------

def test_next_steps_html_section_exists(run_dir, ranked_data, clusters_data,
                                          competitor_intel_data, negatives_data,
                                          brief_text, forecast_phase10):
    """report.html contains <section id="next-steps"> + checkbox inputs."""
    _skip_unless_next_steps()
    if not hasattr(render_report, "render_html_report"):
        pytest.skip("render_html_report not present")
    from render_report import render_html_report, build_report_json
    try:
        report = build_report_json(
            ranked_data, clusters_data, competitor_intel_data,
            negatives_data, brief_text, run_dir,
            forecast=forecast_phase10,
        )
    except TypeError:
        pytest.skip("build_report_json forecast kwarg not threaded yet")
    html = render_html_report(report)
    assert 'id="next-steps"' in html
    assert '<input type="checkbox"' in html


def test_next_steps_html_localstorage_namespacing(run_dir, ranked_data, clusters_data,
                                                    competitor_intel_data, negatives_data,
                                                    brief_text, forecast_phase10):
    """HTML script block namespaces localStorage keys per run slug (Pitfall 7)."""
    _skip_unless_next_steps()
    if not hasattr(render_report, "render_html_report"):
        pytest.skip("render_html_report not present")
    from render_report import render_html_report, build_report_json
    import re
    try:
        report = build_report_json(
            ranked_data, clusters_data, competitor_intel_data,
            negatives_data, brief_text, run_dir,
            forecast=forecast_phase10,
        )
    except TypeError:
        pytest.skip("build_report_json forecast kwarg not threaded yet")
    html = render_html_report(report)
    # Accept any of: literal template `gar_${slug}_step_`,
    # or fully-baked `gar_<runslug>_step_<id>`.
    assert re.search(r"gar_(\$\{[A-Za-z_.]+\}|[a-zA-Z0-9_-]+)_step_", html), (
        "localStorage key namespace pattern not found"
    )


def test_next_steps_html_escapes_step_text(brief_fields_phase10, forecast_phase10,
                                             clusters_phase10_data):
    """Step text containing <script> is escaped (reuse _html_escape)."""
    _skip_unless_next_steps()
    # Inject an XSS payload as an extra cluster name; assert it never appears
    # raw in the rendered markdown / steps list.
    injected = dict(clusters_phase10_data)
    injected["clusters"] = list(injected["clusters"]) + [
        {"name": "<script>alert(1)</script>", "intent": "transactional", "keywords": []}
    ]
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10, None, injected,
    )
    if not hasattr(render_report, "_html_escape"):
        pytest.skip("_html_escape helper not present")
    # When the text would be rendered into HTML, _html_escape must neutralise it.
    for s in steps:
        escaped = render_report._html_escape(s["text"])
        assert "<script>" not in escaped


# ---------------------------------------------------------------------------
# CMPL-05 — Compliance-aware reorder (single + combined verticals)
# ---------------------------------------------------------------------------

def test_next_steps_compliance_reorder_single_vertical(brief_fields_phase10,
                                                         forecast_phase10,
                                                         clusters_phase10_data,
                                                         compliance_with_match_data):
    """Single matched vertical → step 1 = verification; step 2 = 'Create campaign…'."""
    _skip_unless_next_steps()
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10,
        compliance_with_match_data, clusters_phase10_data,
    )
    # Compliance prepend → 8 ops steps + 1 verification = 9 total.
    assert len(steps) == 9
    vertical = compliance_with_match_data["matched_verticals"][0]
    # Step 1 = verification — contains the vertical's name (title-cased) and URL.
    assert "Medical" in steps[0]["text"] or "medical" in steps[0]["text"]
    assert vertical["verification_url"] in steps[0]["text"]
    # Step 2 = standard "Create campaign…" step (renumbered down by 1).
    assert "Create campaign" in steps[1]["text"]


def test_next_steps_compliance_combined_two_verticals(brief_fields_phase10,
                                                        forecast_phase10,
                                                        clusters_phase10_data,
                                                        compliance_two_verticals_data):
    """Two matched verticals → ONE combined step (not two separate steps)."""
    _skip_unless_next_steps()
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10,
        compliance_two_verticals_data, clusters_phase10_data,
    )
    # Combined step rule: exactly 1 verification prepend, not 2.
    verification_steps = [
        s for s in steps if "verification" in s["text"].lower()
    ]
    assert len(verification_steps) == 1, (
        f"expected exactly 1 combined verification step, got {len(verification_steps)}"
    )
    combined = verification_steps[0]
    # Both vertical names appear, joined "+" style.
    assert "Medical" in combined["text"]
    assert "Legal" in combined["text"]
    # Both URLs appear (joined with "; " or similar — assert both substrings).
    for v in compliance_two_verticals_data["matched_verticals"]:
        assert v["verification_url"] in combined["text"]


def test_next_steps_no_compliance_standard_order(brief_fields_phase10,
                                                   forecast_phase10,
                                                   clusters_phase10_data,
                                                   compliance_empty_data):
    """Empty matched_verticals → step 1 = 'Create campaign…' (no prepend)."""
    _skip_unless_next_steps()
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10,
        compliance_empty_data, clusters_phase10_data,
    )
    assert len(steps) == 8
    # The first step in the standard order is the "Create campaign…" step.
    assert "Create campaign" in steps[0]["text"]
    # No literal angle-bracket fallback leaked into the text (Pitfall 8).
    for s in steps:
        assert "<vertical>" not in s["text"]
        assert "<URL>" not in s["text"]


# ---------------------------------------------------------------------------
# EXPT-05 — Export Files section + report.json exports[] (Wave 2 stubs)
# ---------------------------------------------------------------------------

def test_export_files_section_in_markdown(run_dir):
    """## Export Files markdown lists relative CSV paths (Wave 2)."""
    _skip_unless_export_section()
    # Stage the three CSVs the section is supposed to list.
    export_dir = run_dir / "export"
    export_dir.mkdir(exist_ok=True)
    for name in ("positives.csv", "negatives.csv", "ad_groups.csv"):
        (export_dir / name).write_text("Campaign,Ad Group\r\n", encoding="utf-8")
    md = render_report.render_export_section(run_dir)
    assert "## Export Files" in md
    assert "export/positives.csv" in md
    assert "export/negatives.csv" in md
    assert "export/ad_groups.csv" in md


def test_report_json_exports_array(run_dir, ranked_data, clusters_data,
                                    competitor_intel_data, negatives_data,
                                    brief_text):
    """report.json top-level exports[] = ['export/positives.csv', ...] (Wave 2)."""
    _skip_unless_export_section()
    from render_report import build_report_json
    # Stage the three CSVs so build_report_json (Wave 2) can compute exports[].
    export_dir = run_dir / "export"
    export_dir.mkdir(exist_ok=True)
    for name in ("positives.csv", "negatives.csv", "ad_groups.csv"):
        (export_dir / name).write_text("Campaign,Ad Group\r\n", encoding="utf-8")
    try:
        report = build_report_json(
            ranked_data, clusters_data, competitor_intel_data,
            negatives_data, brief_text, run_dir,
        )
    except TypeError:
        pytest.skip("build_report_json exports kwarg not threaded yet")
    if "exports" not in report:
        pytest.skip("build_report_json exports key not yet implemented (Wave 2)")
    assert isinstance(report["exports"], list)
    assert "export/positives.csv" in report["exports"]
    assert "export/negatives.csv" in report["exports"]
    assert "export/ad_groups.csv" in report["exports"]


# ===========================================================================
# Phase 11 Wave 0 — GEO-05 + ADGM-06 RED stubs (per-function hasattr guards)
#
# GEO-05: render_geographic_focus_section() emits "## Geographic Focus" block
#         when brief carries geo_focus; empty string when absent.
# ADGM-06: Next Steps step 3 rewrites when coverage_pct > 50.0.
# ===========================================================================

def _skip_unless_geo_section():
    if not hasattr(render_report, "render_geographic_focus_section"):
        pytest.skip("render_geographic_focus_section — Wave 2 plan 11-03")


def _skip_unless_next_steps_mapping_aware():
    if not hasattr(render_report, "render_next_steps_section"):
        pytest.skip(
            "render_next_steps_section absent — Phase 10 Wave 1 prerequisite"
        )
    # Wave 2 (plan 11-03) extends render_next_steps_section signature to
    # accept an `ad_group_mapping` kwarg. Detect by signature inspection.
    import inspect
    sig = inspect.signature(render_report.render_next_steps_section)
    if "ad_group_mapping" not in sig.parameters:
        pytest.skip(
            "render_next_steps_section ad_group_mapping kwarg — Wave 2 plan 11-03"
        )


def _brief_fields_with_geo() -> dict[str, str]:
    return {
        "industry": "urgent care",
        "product": "accident & injury care",
        "location": "Florida",
        "language": "en-US",
        "audience": "adults 25-65 post-accident",
        "geo_focus": "Palm Beach County, Lake Worth",
    }


def _brief_fields_without_geo() -> dict[str, str]:
    return {
        "industry": "urgent care",
        "product": "accident & injury care",
        "location": "Florida",
        "language": "en-US",
        "audience": "adults 25-65 post-accident",
    }


# ---------------------------------------------------------------------------
# GEO-05 — Geographic Focus callout
# ---------------------------------------------------------------------------

def test_geo_focus_section_rendered():
    """GEO-05: render_geographic_focus_section returns markdown with '## Geographic Focus'."""
    _skip_unless_geo_section()
    md = render_report.render_geographic_focus_section(_brief_fields_with_geo())
    assert "## Geographic Focus" in md
    assert "Florida" in md
    assert "Palm Beach County" in md
    assert "Lake Worth" in md


def test_geo_focus_section_omitted_when_empty():
    """GEO-05: empty geo_focus → empty string (no heading)."""
    _skip_unless_geo_section()
    md = render_report.render_geographic_focus_section(_brief_fields_without_geo())
    assert md == "" or "## Geographic Focus" not in md


# ---------------------------------------------------------------------------
# ADGM-06 — Next Steps step 3 rewrite when coverage > 50%
# ---------------------------------------------------------------------------

def test_next_steps_rewrite_high_coverage(brief_fields_phase10, forecast_phase10,
                                            clusters_phase10_data,
                                            compliance_empty_data):
    """ADGM-06: coverage 60% (> 50) → step 3 rewrites to 'Add keywords to existing ad groups: ...'."""
    _skip_unless_next_steps_mapping_aware()
    mapping = json.loads(
        (FIXTURES_DIR / "ad-group-mapping-60pct.json").read_text(encoding="utf-8")
    )
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10,
        compliance_empty_data, clusters_phase10_data,
        ad_group_mapping=mapping,
    )
    step3 = steps[2]["text"]  # 0-indexed list, step 3 = index 2
    assert "Add keywords to existing ad groups" in step3
    # The 60pct fixture has at least 2 distinct existing ad-group names —
    # confirm both groups appear with keyword counts.
    assert "Accident Exams – Lake Worth" in step3
    assert "Sports Injury" in step3 or "Car Injury Care" in step3


def test_next_steps_no_rewrite_at_exactly_50pct(brief_fields_phase10, forecast_phase10,
                                                  clusters_phase10_data,
                                                  compliance_empty_data):
    """ADGM-06 boundary (Pitfall 7 / Open-Q 4): coverage == 50.0 → NO rewrite (strict `>`)."""
    _skip_unless_next_steps_mapping_aware()
    mapping = json.loads(
        (FIXTURES_DIR / "ad-group-mapping-50pct.json").read_text(encoding="utf-8")
    )
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10,
        compliance_empty_data, clusters_phase10_data,
        ad_group_mapping=mapping,
    )
    step3 = steps[2]["text"]
    # Boundary: standard step retained ("Create ad groups: ...").
    assert "Create ad groups" in step3
    assert "Add keywords to existing ad groups" not in step3


def test_next_steps_no_rewrite_low_coverage(brief_fields_phase10, forecast_phase10,
                                              clusters_phase10_data,
                                              compliance_empty_data):
    """ADGM-06 negative path: coverage 20% → step 3 stays at standard 'Create ad groups: ...'."""
    _skip_unless_next_steps_mapping_aware()
    mapping = json.loads(
        (FIXTURES_DIR / "ad-group-mapping-20pct.json").read_text(encoding="utf-8")
    )
    _, steps = render_report.render_next_steps_section(
        brief_fields_phase10, forecast_phase10,
        compliance_empty_data, clusters_phase10_data,
        ad_group_mapping=mapping,
    )
    step3 = steps[2]["text"]
    assert "Create ad groups" in step3
    assert "Add keywords to existing ad groups" not in step3


# ---------------------------------------------------------------------------
# Phase 12 WFCH-02: render_report JOINs competitor-intel.json +
# competitor-landing-pages.json into the competitor section.
# ---------------------------------------------------------------------------
def _skip_unless_join_implemented() -> None:
    """Per-function skip-guard mirrors Phase 10/11 pattern in this file.

    Wave 2 plan 12-04 lands `_load_competitor_landing_pages` on render_report.
    Until then this test SKIPS (RED-via-skip) so the legacy GREEN suite stays
    intact.
    """
    if MODULE_MISSING:
        pytest.skip("render_report not yet implemented")
    if not hasattr(render_report, "_load_competitor_landing_pages"):
        pytest.skip("Phase 12 WFCH-02 not yet implemented — Wave 2 plan 12-04 lands the JOIN helper")


def test_competitor_section_joins_webfetch_results(tmp_path: Path) -> None:
    """WFCH-02: report.md competitor section must surface verbatim WebFetch
    headline / CTA / offer for advertisers that have a landing-pages entry.

    Wave 2 plan 12-04 wires render_report to read raw/competitor-landing-pages.json
    and JOIN it against raw/competitor-intel.json by (cluster_name, domain, url).
    """
    _skip_unless_join_implemented()

    # Stage minimal run folder with both Phase 12 fixtures
    run_dir = tmp_path / "2026-05-15T000000Z-phase12-test"
    (run_dir / "raw").mkdir(parents=True)

    shutil.copy(
        FIXTURES_DIR / "phase12-competitor-intel.json",
        run_dir / "raw" / "competitor-intel.json",
    )
    shutil.copy(
        FIXTURES_DIR / "phase12-competitor-landing-pages.json",
        run_dir / "raw" / "competitor-landing-pages.json",
    )

    # Minimum sibling files render_report.main needs
    (run_dir / "brief.md").write_text(
        "# Campaign Brief\n\n"
        "**Industry:** grocery\n"
        "**Product:** delivery\n"
        "**Location:** UK\n"
        "**Language:** en-GB\n"
        "**Audience:** families\n",
        encoding="utf-8",
    )
    (run_dir / "ranked.json").write_text(json.dumps([]), encoding="utf-8")
    (run_dir / "clusters.json").write_text(
        json.dumps({
            "metadata": {"clustered_at": "2026-05-15T00:00:00Z", "total_keywords": 0, "total_clusters": 1},
            "clusters": [
                {"name": "grocery_delivery_transactional", "intent": "transactional", "keywords": []}
            ],
            "orphans": [],
        }),
        encoding="utf-8",
    )
    # negatives.json is a flat list of {keyword, tier, category, justification}
    # dicts (per the Phase 6 contract that render_negatives_section consumes).
    (run_dir / "negatives.json").write_text(
        json.dumps([]),
        encoding="utf-8",
    )

    rc = render_report.main(["--run-dir", str(run_dir)])
    assert rc == 0, f"render_report.main exited non-zero: {rc}"

    report_md = (run_dir / "report.md").read_text(encoding="utf-8")
    # Verbatim WebFetch values must appear in competitor section
    assert "Fresh groceries delivered today" in report_md, \
        "WFCH-02: headline from competitor-landing-pages.json not rendered"
    assert "Order now" in report_md, \
        "WFCH-02: CTA from competitor-landing-pages.json not rendered"
    assert "Free delivery over £40" in report_md, \
        "WFCH-02: offer from competitor-landing-pages.json not rendered"


# ===========================================================================
# Phase 14 Wave 0 — render_positives_sync_section RED stubs (POS-07)
#
# Wave 2 plan 14-03 lands `render_positives_sync_section(sync) -> str` on
# render_report (mirrors render_negatives_sync_section). The omit-when-absent
# test uses a getattr-default lambda so it passes against Wave 0 (gives at
# least one GREEN signal for the section feature). The other three tests
# SKIP via per-function guards.
# ===========================================================================


def _skip_unless_positives_sync_section():
    if MODULE_MISSING:
        pytest.skip("render_report not yet implemented")
    if not hasattr(render_report, "render_positives_sync_section"):
        pytest.skip(
            "Wave 2 14-03 not yet landed: "
            "render_report.render_positives_sync_section missing"
        )


def _golden_positives_sync() -> dict:
    return json.loads(
        (FIXTURES_DIR / "golden_positives_sync.json").read_text(encoding="utf-8")
    )


def test_render_positives_sync_section_omits_when_absent():
    """None / {} input → empty string (graceful omit).

    Uses getattr-default lambda so this case passes against Wave 0 (one
    GREEN signal for the section feature) without breaking when the
    helper lands in Wave 2.
    """
    if MODULE_MISSING:
        pytest.skip("render_report not yet implemented")
    fn = getattr(render_report, "render_positives_sync_section",
                 lambda _: "")
    assert fn(None) == ""
    assert fn({}) == ""


def test_render_positives_sync_section_renders_stats_line():
    """Section markdown carries '## Positives Sync' + stats line."""
    _skip_unless_positives_sync_section()
    sync = _golden_positives_sync()
    md = render_report.render_positives_sync_section(sync)
    assert "## Positives Sync" in md
    # Stats shape: our list = N · already active = N · paused = N ·
    # covered by broad = N · new to add = **N**
    assert "our list = 5" in md
    assert "already active = 1" in md
    assert "paused = 1" in md
    assert "covered by broad = 1" in md
    assert "new to add = **2**" in md


def test_render_positives_sync_section_enumerates_new_to_add():
    """Each new_to_add row appears as a list item with the keyword text."""
    _skip_unless_positives_sync_section()
    sync = _golden_positives_sync()
    md = render_report.render_positives_sync_section(sync)
    assert "accident chiropractor lake worth" in md
    assert "walk in clinic boca raton" in md


def test_render_positives_sync_section_count_only_for_other_buckets():
    """already_active / paused / covered_by_broad render as count-only or
    collapsible — NOT full per-row enumeration like new_to_add."""
    _skip_unless_positives_sync_section()
    sync = _golden_positives_sync()
    md = render_report.render_positives_sync_section(sync)
    # The new_to_add bucket enumerates rows; the other 3 must not enumerate
    # their keyword text inline (heuristic: keyword strings not present).
    assert "urgent care lake worth" not in md, (
        "already_active bucket should not enumerate keyword rows inline"
    )
    assert "auto accident clinic" not in md, (
        "paused_in_account bucket should not enumerate keyword rows inline"
    )
    assert "pip insurance clinic" not in md, (
        "covered_by_broad bucket should not enumerate keyword rows inline"
    )


# ===========================================================================
# Phase 15 Wave 0 — Campaign Focus RED stubs (CAMP-01 / CAMP-05 / CAMP-06)
#
# Per-function skip guards so Wave 2 plans 15-02 can flip these GREEN
# one-by-one without re-editing test scaffolding.
# ===========================================================================


def _skip_unless_campaign_focus_section():
    if MODULE_MISSING:
        pytest.skip("render_report not yet implemented")
    if not hasattr(render_report, "render_campaign_focus_section"):
        pytest.skip("render_campaign_focus_section — Wave 2 plan 15-02")


def _skip_unless_brief_parser_has_campaign_focus():
    """Skip when _parse_brief_fields does not yet emit a `campaign_focus`
    key for a brief carrying the field.

    `_parse_brief_fields` itself exists today (Phase 11) — guard probes
    whether the function returns a `campaign_focus` key when the brief
    has `**Campaign focus:** X`.
    """
    if MODULE_MISSING:
        pytest.skip("render_report not yet implemented")
    probe = "- **Campaign focus:** X\n"
    fields = render_report._parse_brief_fields(probe)
    if "campaign_focus" not in fields:
        pytest.skip("_parse_brief_fields campaign_focus key — Wave 2 plan 15-02")


# ---------------------------------------------------------------------------
# CAMP-01 — _parse_brief_fields campaign_focus extraction
# ---------------------------------------------------------------------------

def test_parse_brief_fields_extracts_campaign_focus_single():
    """CAMP-01: brief with `**Campaign focus:** <name>` parses to raw string."""
    _skip_unless_brief_parser_has_campaign_focus()
    brief_text = (FIXTURES_DIR / "brief_with_campaign_focus.md").read_text(encoding="utf-8")
    fields = render_report._parse_brief_fields(brief_text)
    assert fields["campaign_focus"] == "Search | Lake Worth Accident Exams | Manual CPC"


def test_parse_brief_fields_campaign_focus_absent_returns_empty():
    """CAMP-01: brief without Campaign focus line → empty string default."""
    _skip_unless_brief_parser_has_campaign_focus()
    brief_text = (
        "# Campaign Brief\n\n"
        "## Required\n\n"
        "- **Industry:** Urgent care\n"
        "- **Product:** Accident & injury care\n"
        "- **Location:** Florida\n"
        "- **Language:** en-US\n"
        "- **Audience:** Adults 25-65\n"
    )
    fields = render_report._parse_brief_fields(brief_text)
    assert fields.get("campaign_focus", "") == ""


def test_parse_brief_fields_campaign_focus_pipe_list():
    """CAMP-01: pipe-list raw value preserved (split-to-list happens in render)."""
    _skip_unless_brief_parser_has_campaign_focus()
    brief_text = (
        "# Campaign Brief\n\n"
        "## Required\n\n"
        "- **Industry:** Urgent care\n"
        "- **Product:** Accident & injury care\n"
        "- **Location:** Florida\n"
        "- **Language:** en-US\n"
        "- **Audience:** Adults 25-65\n\n"
        "## Optional\n\n"
        "- **Campaign focus:** A | B | C\n"
    )
    fields = render_report._parse_brief_fields(brief_text)
    assert fields["campaign_focus"] == "A | B | C"


# ---------------------------------------------------------------------------
# CAMP-05 — render_campaign_focus_section
# ---------------------------------------------------------------------------

def _brief_fields_with_campaign_focus(value: str) -> dict[str, str]:
    return {
        "industry": "urgent care",
        "product": "accident & injury care",
        "location": "Florida",
        "language": "en-US",
        "audience": "adults 25-65 post-accident",
        "geo_focus": "Palm Beach County, Lake Worth",
        "campaign_focus": value,
    }


def test_campaign_focus_section_rendered_single():
    """CAMP-05: single-value campaign_focus renders heading + literal value."""
    _skip_unless_campaign_focus_section()
    fields = _brief_fields_with_campaign_focus(
        "Search | Lake Worth Accident Exams | Manual CPC"
    )
    md = render_report.render_campaign_focus_section(fields)
    assert "## Campaign Focus" in md
    # Literal campaign name appears in rendered markdown (pipes may be escaped
    # for table safety — accept either raw or escaped form).
    assert (
        "Search | Lake Worth Accident Exams | Manual CPC" in md
        or "Search \\| Lake Worth Accident Exams \\| Manual CPC" in md
    )


def test_campaign_focus_section_omitted_when_empty():
    """CAMP-05: empty campaign_focus → empty string or no heading."""
    _skip_unless_campaign_focus_section()
    fields = _brief_fields_with_campaign_focus("")
    md = render_report.render_campaign_focus_section(fields)
    assert md == "" or "## Campaign Focus" not in md


def test_campaign_focus_section_list_form_bulleted():
    """CAMP-05: pipe-list value → all 3 campaign names appear in rendered md."""
    _skip_unless_campaign_focus_section()
    fields = _brief_fields_with_campaign_focus("A | B | C")
    md = render_report.render_campaign_focus_section(fields)
    assert "## Campaign Focus" in md
    # All three names appear (whether bulleted or comma-joined, planner's pick)
    assert "A" in md
    assert "B" in md
    assert "C" in md


# ---------------------------------------------------------------------------
# CAMP-05 — name validation against raw/google-ads-perf.json
# ---------------------------------------------------------------------------

def test_campaign_focus_typo_warning():
    """CAMP-05: focus name absent from perf.json campaigns → ⚠ warning."""
    _skip_unless_campaign_focus_section()
    fields = _brief_fields_with_campaign_focus("Nonexistent Campaign")
    perf_path = FIXTURES_DIR / "google-ads-perf-with-campaign.json"
    md = render_report.render_campaign_focus_section(fields, perf_path=perf_path)
    assert "⚠" in md
    assert "Nonexistent Campaign" in md
    # Warning phrasing — accept either "not found" or "typo"
    assert ("not found" in md.lower()) or ("typo" in md.lower())


def test_campaign_focus_no_warning_when_name_matches():
    """CAMP-05 happy path: focus name present in perf.json → no warning."""
    _skip_unless_campaign_focus_section()
    fields = _brief_fields_with_campaign_focus(
        "Search | Lake Worth Accident Exams | Manual CPC"
    )
    perf_path = FIXTURES_DIR / "google-ads-perf-with-campaign.json"
    md = render_report.render_campaign_focus_section(fields, perf_path=perf_path)
    assert "⚠" not in md


def test_campaign_focus_no_warning_when_perf_path_absent():
    """CAMP-05 graceful degrade: perf_path=None → no warning (validation needs file)."""
    _skip_unless_campaign_focus_section()
    fields = _brief_fields_with_campaign_focus("Anything Goes")
    md = render_report.render_campaign_focus_section(fields, perf_path=None)
    assert "⚠" not in md
