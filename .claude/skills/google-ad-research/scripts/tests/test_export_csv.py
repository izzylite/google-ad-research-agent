"""Tests for export_csv.py — RED stubs (Phase 10 Wave 0).

All tests SKIP via MODULE_INCOMPLETE guard until export_csv.py grows its
write_positives helper in Wave 1 (plan 10-01). Contracts under test:

    EXPT-01  positives.csv (Campaign, Ad Group, Keyword, Match Type,
                            Max CPC, Final URL)
    EXPT-02  negatives.csv (Strong → campaign-level, Considered/Investigate
                            → ad_group-level)
    EXPT-03  ad_groups.csv (one row per cluster, Status=Enabled,
                            Default Max CPC = USD-formatted cluster median)
    EXPT-04  Byte contract: UTF-8 no BOM, CRLF, round-trip via DictReader.
             Exit codes 0/3 on happy/missing-input paths.

Skip pattern mirrors test_compliance_check.py's MODULE_MISSING guard, but
this module is allowed to *import* (the stub is shipped in plan 10-00
Task 1); the sentinel is the absence of `write_positives`, so the guard
trips while collection stays clean.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import export_csv  # noqa: F401
    # Wave 0 stub lacks write_*; presence of write_positives is the GREEN signal.
    MODULE_INCOMPLETE = not hasattr(export_csv, "write_positives")
except ImportError:
    MODULE_INCOMPLETE = True

pytestmark = pytest.mark.skipif(
    MODULE_INCOMPLETE,
    reason="export_csv.write_positives not yet implemented (Wave 1, plan 10-01)",
)

FIXTURES = Path(__file__).parent / "fixtures"
CAMPAIGN = "Phase 10 Test Brief"  # Title-cased fixture slug (deterministic).


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clusters_phase10() -> dict:
    return json.loads((FIXTURES / "clusters_phase10.json").read_text(encoding="utf-8"))


@pytest.fixture
def negatives_phase10() -> list[dict]:
    return json.loads((FIXTURES / "negatives_phase10.json").read_text(encoding="utf-8"))


@pytest.fixture
def negatives_empty() -> list[dict]:
    return json.loads((FIXTURES / "negatives_empty.json").read_text(encoding="utf-8"))


@pytest.fixture
def ranked_enriched_phase10() -> list[dict]:
    """Minimal ranked-enriched rows joining cleanly to clusters_phase10.

    Mirrors the Phase 9 `ranked-enriched.json` shape: per-keyword `intent`,
    `match_type`, `cpc_micros`, and `suggested_max_cpc_micros`. The
    suggested CPCs here correspond to the values the goldens encode.
    """
    return [
        # same_day_delivery_transactional (mult 1.2)
        {"keyword": "same-day grocery delivery", "intent": "transactional",
         "match_type": "exact", "cpc_micros": 320_000, "suggested_max_cpc_micros": 384_000},
        {"keyword": "order groceries online uk", "intent": "transactional",
         "match_type": "exact", "cpc_micros": 380_000, "suggested_max_cpc_micros": 456_000},
        {"keyword": "grocery delivery near me", "intent": "transactional",
         "match_type": "exact", "cpc_micros": 450_000, "suggested_max_cpc_micros": 540_000},
        # grocery_comparison_commercial (mult 0.8)
        {"keyword": "best grocery delivery uk", "intent": "commercial",
         "match_type": "phrase", "cpc_micros": 210_000, "suggested_max_cpc_micros": 168_000},
        {"keyword": "ocado vs tesco delivery", "intent": "commercial",
         "match_type": "phrase", "cpc_micros": 175_000, "suggested_max_cpc_micros": 140_000},
        {"keyword": "grocery delivery comparison", "intent": "commercial",
         "match_type": "phrase", "cpc_micros": 160_000, "suggested_max_cpc_micros": 128_000},
        # grocery_delivery_basics_informational (all-null CPC, mult 0.4)
        {"keyword": "how does grocery delivery work", "intent": "informational",
         "match_type": "phrase", "cpc_micros": None, "suggested_max_cpc_micros": None,
         "no_cpc_data": True},
        {"keyword": "what is same day grocery delivery", "intent": "informational",
         "match_type": "phrase", "cpc_micros": None, "suggested_max_cpc_micros": None,
         "no_cpc_data": True},
    ]


@pytest.fixture
def staged_run_dir(tmp_path, clusters_phase10, negatives_phase10,
                   ranked_enriched_phase10) -> Path:
    """A run-folder staged with everything export_csv.main() expects.

    Path layout deliberately uses the timestamp-Z-slug shape so
    `_derive_brief_slug` returns "phase-10-test-brief" → title-cased to
    "Phase 10 Test Brief" for the Campaign column.
    """
    run = tmp_path / "2026-05-14T120000Z-phase-10-test-brief"
    (run / "raw").mkdir(parents=True)
    (run / "ranked-enriched.json").write_text(
        json.dumps(ranked_enriched_phase10), encoding="utf-8"
    )
    (run / "clusters.json").write_text(
        json.dumps(clusters_phase10), encoding="utf-8"
    )
    (run / "negatives.json").write_text(
        json.dumps(negatives_phase10), encoding="utf-8"
    )
    (run / "brief.md").write_text(
        "# Campaign Brief\n\n**Industry:** test\n**Product:** phase 10 test brief\n"
        "**Location:** UK\n**Language:** en-GB\n**Audience:** test audience\n",
        encoding="utf-8",
    )
    return run


def _run_main_or_call_writers(run_dir: Path) -> int:
    """Drive export_csv via main() if Wave 1 supplies it; return exit code."""
    return export_csv.main(["--run-dir", str(run_dir)])


# ---------------------------------------------------------------------------
# EXPT-01 — positives.csv
# ---------------------------------------------------------------------------

def test_positives_headers_exact(staged_run_dir):
    """positives.csv fieldnames match POSITIVES_HEADERS exactly (no drift)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "positives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == export_csv.POSITIVES_HEADERS


def test_positives_rows_per_keyword(staged_run_dir, ranked_enriched_phase10):
    """One row per ranked-enriched keyword that maps to a cluster (8 rows)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "positives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    # Every ranked-enriched keyword in the fixture maps to a cluster.
    assert len(rows) == len(ranked_enriched_phase10)


def test_positives_max_cpc_format(staged_run_dir):
    """Max CPC = micros/1_000_000 with 2-decimal formatting; None → '0.00'."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "positives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_kw = {r["Keyword"]: r for r in rows}
    # 384_000 micros → "0.38"
    assert by_kw["same-day grocery delivery"]["Max CPC"] == "0.38"
    # 456_000 micros → "0.46"
    assert by_kw["order groceries online uk"]["Max CPC"] == "0.46"
    # None → "0.00" (Pitfall 10: Editor rejects empty numeric cells)
    assert by_kw["how does grocery delivery work"]["Max CPC"] == "0.00"


def test_positives_match_type_titlecase(staged_run_dir):
    """Match Type title-cased at write boundary (phrase → Phrase, exact → Exact)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "positives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_kw = {r["Keyword"]: r for r in rows}
    assert by_kw["same-day grocery delivery"]["Match Type"] == "Exact"
    assert by_kw["best grocery delivery uk"]["Match Type"] == "Phrase"


def test_positives_final_url_empty(staged_run_dir):
    """Final URL column is empty for every row (v1.2 brief field TODO)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "positives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert all(r["Final URL"] == "" for r in rows)


def test_positives_campaign_titlecase_brief_slug(staged_run_dir):
    """Campaign column == title-cased brief slug (fixture: 'Phase 10 Test Brief')."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "positives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert all(r["Campaign"] == CAMPAIGN for r in rows)


# ---------------------------------------------------------------------------
# EXPT-02 — negatives.csv (Tier → Level mapping)
# ---------------------------------------------------------------------------

def test_negatives_strong_to_campaign_level(staged_run_dir):
    """Strong tier → Level=campaign, Ad Group="" (Pitfall: NOT 'ALL')."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "negatives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    strong_rows = [r for r in rows if r["Keyword"] in
                   ("grocery delivery jobs", "free grocery delivery")]
    assert len(strong_rows) == 2
    for r in strong_rows:
        assert r["Level"] == "campaign"
        assert r["Ad Group"] == ""


def test_negatives_considered_to_ad_group(staged_run_dir):
    """Considered tier → Level=ad_group, Ad Group=cluster name verbatim."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "negatives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_kw = {r["Keyword"]: r for r in rows}
    assert by_kw["ocado discount code"]["Level"] == "ad_group"
    assert by_kw["ocado discount code"]["Ad Group"] == "grocery_comparison_commercial"


def test_negatives_investigate_to_ad_group(staged_run_dir):
    """Investigate tier → Level=ad_group (same mapping as Considered)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "negatives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_kw = {r["Keyword"]: r for r in rows}
    assert by_kw["grocery delivery northern ireland"]["Level"] == "ad_group"


def test_negatives_empty_input(tmp_path, negatives_empty, clusters_phase10,
                                ranked_enriched_phase10):
    """Empty negatives.json → header-only CSV (no crash, no missing file)."""
    run = tmp_path / "2026-05-14T120000Z-phase-10-test-brief"
    (run / "raw").mkdir(parents=True)
    (run / "ranked-enriched.json").write_text(
        json.dumps(ranked_enriched_phase10), encoding="utf-8")
    (run / "clusters.json").write_text(json.dumps(clusters_phase10), encoding="utf-8")
    (run / "negatives.json").write_text(json.dumps(negatives_empty), encoding="utf-8")
    (run / "brief.md").write_text(
        "**Industry:** test\n**Product:** phase 10 test brief\n"
        "**Location:** UK\n**Language:** en-GB\n**Audience:** test\n",
        encoding="utf-8",
    )

    rc = export_csv.main(["--run-dir", str(run)])
    assert rc == 0
    path = run / "export" / "negatives.csv"
    assert path.exists()
    raw = path.read_bytes()
    # Header line + trailing CRLF; NO data rows.
    decoded = raw.decode("utf-8")
    assert decoded.startswith("Campaign,Ad Group,Keyword,Match Type,Level")
    # Exactly one CRLF-terminated line (the header) → splitlines() returns 1.
    assert decoded.count("\r\n") == 1


def test_negatives_match_type_default_phrase(staged_run_dir):
    """Missing match_type on a negative → default 'Phrase' (RANK-03 fallback)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "negatives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_kw = {r["Keyword"]: r for r in rows}
    # 'grocery delivery northern ireland' has no match_type in the fixture.
    assert by_kw["grocery delivery northern ireland"]["Match Type"] == "Phrase"


# ---------------------------------------------------------------------------
# EXPT-03 — ad_groups.csv
# ---------------------------------------------------------------------------

def test_ad_groups_one_row_per_cluster(staged_run_dir, clusters_phase10):
    """ad_groups.csv has one row per cluster (3 rows for clusters_phase10)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "ad_groups.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(clusters_phase10["clusters"])


def test_ad_groups_status_enabled(staged_run_dir):
    """Every ad_groups.csv row has Status='Enabled'."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "ad_groups.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert all(r["Status"] == "Enabled" for r in rows)


def test_ad_groups_default_max_cpc_from_cluster_median(staged_run_dir):
    """Default Max CPC = USD-formatted cluster-median suggested_max_cpc_micros."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "ad_groups.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_ag = {r["Ad Group"]: r for r in rows}
    # same_day_delivery_transactional siblings: 384_000, 456_000, 540_000 → median 456_000 → 0.46
    assert by_ag["same_day_delivery_transactional"]["Default Max CPC"] == "0.46"
    # grocery_comparison_commercial siblings: 168_000, 140_000, 128_000 → median 140_000 → 0.14
    assert by_ag["grocery_comparison_commercial"]["Default Max CPC"] == "0.14"


def test_ad_groups_zero_cpc_for_all_null_cluster(staged_run_dir):
    """All-null suggested_max_cpc_micros cluster → '0.00' (Pitfall 10)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "ad_groups.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_ag = {r["Ad Group"]: r for r in rows}
    assert by_ag["grocery_delivery_basics_informational"]["Default Max CPC"] == "0.00"


def test_ad_groups_ad_group_name_verbatim_from_cluster(staged_run_dir,
                                                       clusters_phase10):
    """Ad Group column == clusters_phase10.json[i]['name'] verbatim (Pitfall 6)."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / "ad_groups.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    expected = {c["name"] for c in clusters_phase10["clusters"]}
    got = {r["Ad Group"] for r in rows}
    assert got == expected


# ---------------------------------------------------------------------------
# EXPT-04 — byte contract + round-trip + exit codes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["positives.csv", "negatives.csv", "ad_groups.csv"])
def test_all_csvs_no_bom(staged_run_dir, name):
    """No CSV starts with a UTF-8 BOM (Pitfall 1 — Editor rejects ﻿Campaign)."""
    _run_main_or_call_writers(staged_run_dir)
    raw = (staged_run_dir / "export" / name).read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", f"BOM detected in {name}: {raw[:8]!r}"


@pytest.mark.parametrize("name", ["positives.csv", "negatives.csv", "ad_groups.csv"])
def test_all_csvs_crlf_only(staged_run_dir, name):
    """CSVs use CRLF endings; no bare \\n (Pitfall 2 — Windows phantom rows)."""
    _run_main_or_call_writers(staged_run_dir)
    raw = (staged_run_dir / "export" / name).read_bytes()
    assert b"\r\n" in raw, f"no CRLF found in {name}"
    text = raw.decode("utf-8")
    assert "\n" not in text.replace("\r\n", ""), (
        f"bare \\n detected in {name} after stripping CRLF pairs"
    )


@pytest.mark.parametrize("name,expected_headers_attr", [
    ("positives.csv", "POSITIVES_HEADERS"),
    ("negatives.csv", "NEGATIVES_HEADERS"),
    ("ad_groups.csv", "AD_GROUPS_HEADERS"),
])
def test_all_csvs_round_trip_dictreader(staged_run_dir, name, expected_headers_attr):
    """csv.DictReader round-trip yields fieldnames matching the module constant."""
    _run_main_or_call_writers(staged_run_dir)
    path = staged_run_dir / "export" / name
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == getattr(export_csv, expected_headers_attr)
        rows = list(reader)
    # Round-trip succeeded — every row has the same keys as fieldnames.
    for r in rows:
        assert set(r.keys()) == set(reader.fieldnames)


@pytest.mark.parametrize("name", ["positives.csv", "negatives.csv", "ad_groups.csv"])
def test_all_csvs_match_golden_bytes(staged_run_dir, name):
    """Byte-exact equality with fixtures/golden_<name>.csv (Nyquist signal)."""
    _run_main_or_call_writers(staged_run_dir)
    got = (staged_run_dir / "export" / name).read_bytes()
    golden = (FIXTURES / f"golden_{name}").read_bytes()
    assert got == golden, f"{name} bytes drift from golden (len={len(got)} vs {len(golden)})"


def test_exit_code_0_on_happy_path(staged_run_dir):
    """main() returns 0 on a valid run_dir with all inputs staged."""
    rc = export_csv.main(["--run-dir", str(staged_run_dir)])
    assert rc == 0


def test_exit_code_3_on_missing_inputs(tmp_path):
    """main() returns 3 when ranked-enriched.json is absent (fatal, not retryable)."""
    run = tmp_path / "2026-05-14T120000Z-empty"
    (run / "raw").mkdir(parents=True)
    rc = export_csv.main(["--run-dir", str(run)])
    assert rc == 3


# ===========================================================================
# Phase 11 Wave 0 — ADGM-05 RED stubs (per-function hasattr guards)
#
# Wave 2 (plan 11-03) extends export_csv to consult `{run_dir}/ad-group-mapping.json`
# at write time. When the mapping is absent → fall back to cluster slug
# (existing behaviour). When present:
#   - positives.csv Ad Group = existing_ad_group name for high/medium matches
#   - ad_groups.csv ROWS only contain NEW cluster slugs (existing names excluded)
# ===========================================================================

def _skip_unless_mapping_aware() -> None:
    """Skip if Wave 2 mapping integration is absent."""
    if MODULE_INCOMPLETE:
        pytest.skip("export_csv stub — Wave 1 not yet shipped")
    if not hasattr(export_csv, "_resolve_ad_group_from_mapping"):
        pytest.skip("export_csv mapping-aware helpers — Wave 2 plan 11-03")


def _stage_mapping_run(tmp_path: Path, mapping_fixture: str | None,
                       clusters_phase10: dict, negatives_phase10: list[dict],
                       ranked_enriched_phase10: list[dict]) -> Path:
    """Stage a phase-10-style run_dir + optional ad-group-mapping.json at root.

    When a mapping fixture is supplied, augment ranked-enriched + clusters with
    the mapping's keywords so the existing-ad-group resolution path can fire.
    The original grocery fixtures alone don't overlap with the mapping's
    accident-doctor keywords; the test contract requires the overlap to exist
    so positives.csv can pick up the mapped Ad Group cell.
    """
    run = tmp_path / "2026-05-14T120000Z-phase-11-mapping"
    (run / "raw").mkdir(parents=True)

    ranked_to_write = list(ranked_enriched_phase10)
    clusters_to_write = json.loads(json.dumps(clusters_phase10))  # deep copy
    if mapping_fixture is not None:
        mapping_data = json.loads(
            (FIXTURES / mapping_fixture).read_text(encoding="utf-8")
        )
        # One synthetic cluster holds all mapping keywords so the positives
        # joiner has a cluster fallback for low-confidence rows (Pitfall 6).
        mapping_cluster_kws = []
        for m in mapping_data.get("matches", []):
            kw = m.get("keyword", "")
            ranked_to_write.append({
                "keyword": kw,
                "intent": "transactional",
                "match_type": "phrase",
                "cpc_micros": 250_000,
                "suggested_max_cpc_micros": 300_000,
                "score": 50,
            })
            mapping_cluster_kws.append({"keyword": kw, "score": 50})
        clusters_to_write["clusters"].append({
            "name": "phase11_mapping_fallback",
            "intent": "transactional",
            "keywords": mapping_cluster_kws,
        })
        (run / "ad-group-mapping.json").write_text(
            json.dumps(mapping_data), encoding="utf-8",
        )

    (run / "ranked-enriched.json").write_text(
        json.dumps(ranked_to_write), encoding="utf-8")
    (run / "clusters.json").write_text(
        json.dumps(clusters_to_write), encoding="utf-8")
    (run / "negatives.json").write_text(
        json.dumps(negatives_phase10), encoding="utf-8")
    (run / "brief.md").write_text(
        "**Industry:** test\n**Product:** phase 11 mapping\n"
        "**Location:** UK\n**Language:** en-GB\n**Audience:** test\n",
        encoding="utf-8",
    )
    return run


def test_existing_ad_group_in_positives(tmp_path, clusters_phase10,
                                         negatives_phase10, ranked_enriched_phase10):
    """ADGM-05: ad-group-mapping.json present → positives.csv Ad Group = existing name for high matches."""
    _skip_unless_mapping_aware()
    run = _stage_mapping_run(
        tmp_path, "ad-group-mapping-60pct.json",
        clusters_phase10, negatives_phase10, ranked_enriched_phase10,
    )
    rc = export_csv.main(["--run-dir", str(run)])
    assert rc == 0

    path = run / "export" / "positives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    # At least one row's Ad Group should be the existing "Accident Exams – Lake Worth"
    existing_ag_rows = [
        r for r in rows if r["Ad Group"] == "Accident Exams – Lake Worth"
    ]
    assert existing_ag_rows, (
        "no positives.csv row picked up existing ad group name from mapping"
    )


def test_ad_groups_csv_skips_existing(tmp_path, clusters_phase10,
                                       negatives_phase10, ranked_enriched_phase10):
    """ADGM-05: ad_groups.csv excludes existing-ad-group names from mapping (prevents Editor dupes)."""
    _skip_unless_mapping_aware()
    run = _stage_mapping_run(
        tmp_path, "ad-group-mapping-60pct.json",
        clusters_phase10, negatives_phase10, ranked_enriched_phase10,
    )
    export_csv.main(["--run-dir", str(run)])

    path = run / "export" / "ad_groups.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    ag_names = {r["Ad Group"] for r in rows}
    mapping = json.loads(
        (FIXTURES / "ad-group-mapping-60pct.json").read_text(encoding="utf-8")
    )
    existing_names = {
        m["existing_ad_group"] for m in mapping["matches"]
        if m["confidence"] in ("high", "medium")
    }
    overlap = ag_names & existing_names
    assert not overlap, (
        f"ad_groups.csv contains existing ad-group names (Editor dupe risk): {overlap}"
    )


def test_no_mapping_file_backward_compat(tmp_path, clusters_phase10,
                                          negatives_phase10, ranked_enriched_phase10):
    """ADGM-05 backward compat: mapping absent → positives.csv Ad Group = cluster slug."""
    _skip_unless_mapping_aware()
    run = _stage_mapping_run(
        tmp_path, None,  # NO mapping file
        clusters_phase10, negatives_phase10, ranked_enriched_phase10,
    )
    rc = export_csv.main(["--run-dir", str(run)])
    assert rc == 0

    path = run / "export" / "positives.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    cluster_names = {c["name"] for c in clusters_phase10["clusters"]}
    for r in rows:
        assert r["Ad Group"] in cluster_names, (
            f"backward-compat broken: Ad Group {r['Ad Group']!r} not a cluster slug"
        )


def test_unicode_dash_preserved_in_csv(tmp_path, clusters_phase10,
                                        negatives_phase10, ranked_enriched_phase10):
    """ADGM-05 / Pitfall 2: 'Accident Exams – Lake Worth' (U+2013) round-trips through CSV."""
    _skip_unless_mapping_aware()
    run = _stage_mapping_run(
        tmp_path, "ad-group-mapping-60pct.json",
        clusters_phase10, negatives_phase10, ranked_enriched_phase10,
    )
    export_csv.main(["--run-dir", str(run)])

    raw_bytes = (run / "export" / "positives.csv").read_bytes()
    # UTF-8 encoding of U+2013 en-dash = 0xE2 0x80 0x93.
    assert b"\xe2\x80\x93" in raw_bytes, "en-dash bytes lost through CSV write"
