"""Tests for compliance_check.py — RED stubs (Phase 9 Wave 0).

All tests SKIP via MODULE_MISSING guard until compliance_check.py lands in
Wave 1 (Phase 9 plan 03). Contract under test: CMPL-01..04.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from compliance_check import (  # noqa: F401
        COMPLIANCE_SCAN_TOP_N,
        find_matches,
        load_verticals,
        main_with_args,
        scan,
    )
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(
    MODULE_MISSING,
    reason="compliance_check.py not yet implemented (Wave 1, plan 03)",
)

FIXTURES = Path(__file__).parent / "fixtures"
SKILL_ROOT = Path(__file__).resolve().parents[2]
VERTICALS_PATH = SKILL_ROOT / "references" / "compliance-verticals.json"


# ---------------------------------------------------------------------------
# Word-boundary matching (Pitfall 3 — no false positives)
# ---------------------------------------------------------------------------

def test_word_boundary():
    """'loaner mug' does NOT match the token 'loan' (word-boundary required)."""
    assert find_matches("loaner mug for sale", ["loan"]) == []


def test_word_boundary_positive():
    """'personal loan rates' matches the token 'loan'."""
    assert find_matches("personal loan rates", ["loan"]) == ["loan"]


def test_case_insensitive():
    """'CLINIC HOURS' matches the token 'clinic' case-insensitively."""
    assert find_matches("CLINIC HOURS", ["clinic"]) == ["clinic"]


# ---------------------------------------------------------------------------
# CMPL-02 — load_verticals reads references/compliance-verticals.json
# ---------------------------------------------------------------------------

def test_loads_from_json_reference():
    """load_verticals returns 5 dicts each with name/tokens/verification_url/policy_note."""
    verticals = load_verticals(VERTICALS_PATH)
    assert isinstance(verticals, list)
    assert len(verticals) == 5
    names = {v["name"] for v in verticals}
    assert names == {"medical", "legal", "finance", "gambling", "crypto"}
    required_keys = {"name", "tokens", "verification_url", "policy_note"}
    for v in verticals:
        assert required_keys.issubset(set(v.keys())), (
            f"Vertical {v.get('name')} missing keys: {required_keys - set(v.keys())}"
        )
        assert isinstance(v["tokens"], list) and len(v["tokens"]) >= 1
        assert isinstance(v["verification_url"], str) and v["verification_url"]
        assert isinstance(v["policy_note"], str) and v["policy_note"]


# ---------------------------------------------------------------------------
# CMPL-01 — scan() flags brief + top-N keywords against verticals
# ---------------------------------------------------------------------------

def test_scans_brief_and_keywords():
    """Medical brief → medical vertical flagged; evidence_sources.brief non-empty."""
    brief_text = (FIXTURES / "brief_medical.md").read_text(encoding="utf-8")
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    verticals = load_verticals(VERTICALS_PATH)
    out = scan(brief_text, ranked, verticals, top_n=COMPLIANCE_SCAN_TOP_N)
    matched_names = {m["name"] for m in out["matched_verticals"]}
    assert "medical" in matched_names
    medical = next(m for m in out["matched_verticals"] if m["name"] == "medical")
    assert "evidence_sources" in medical
    assert len(medical["evidence_sources"]["brief"]) >= 1


def test_neutral_brief_no_matches():
    """Neutral kitchenware brief → matched_verticals == [] (no false positives)."""
    brief_text = (FIXTURES / "brief_neutral.md").read_text(encoding="utf-8")
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    verticals = load_verticals(VERTICALS_PATH)
    out = scan(brief_text, ranked, verticals, top_n=COMPLIANCE_SCAN_TOP_N)
    assert out["matched_verticals"] == []


# ---------------------------------------------------------------------------
# CMPL-01 — top-N enforcement
# ---------------------------------------------------------------------------

def test_scans_top_n_only():
    """Token at rank 80 must NOT appear in evidence when COMPLIANCE_SCAN_TOP_N=50."""
    # Synthesize 100 ranked rows; only the row at index 79 contains a regulated token.
    rows = []
    for i in range(100):
        rows.append(
            {
                "keyword": f"grocery delivery option {i}",
                "intent": "commercial",
                "score": 1000 - i,
                "volume": 500,
                "cpc_micros": 100_000,
            }
        )
    rows[79]["keyword"] = "buy cryptocurrency online"
    verticals = load_verticals(VERTICALS_PATH)
    out = scan(brief_text="", ranked_enriched=rows, verticals=verticals, top_n=50)
    # 'crypto' is in the regulated tokens; it should NOT have been picked up
    # because the keyword is at rank 80 (index 79), outside the top 50.
    matched_names = {m["name"] for m in out["matched_verticals"]}
    assert "crypto" not in matched_names


# ---------------------------------------------------------------------------
# verification_url present per matched vertical (CMPL-05 contract for Phase 10)
# ---------------------------------------------------------------------------

def test_verification_url_present_per_vertical():
    """Every matched vertical dict carries non-empty verification_url string."""
    brief_text = (FIXTURES / "brief_medical.md").read_text(encoding="utf-8")
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    verticals = load_verticals(VERTICALS_PATH)
    out = scan(brief_text, ranked, verticals, top_n=COMPLIANCE_SCAN_TOP_N)
    assert len(out["matched_verticals"]) >= 1
    for m in out["matched_verticals"]:
        assert "verification_url" in m
        assert isinstance(m["verification_url"], str)
        assert m["verification_url"].startswith("http")


# ---------------------------------------------------------------------------
# main_with_args — writes compliance-flags.json
# ---------------------------------------------------------------------------

def test_main_with_args_writes_compliance_flags(tmp_run_dir):
    """main writes {run_dir}/compliance-flags.json with metadata + matched_verticals."""
    brief = (FIXTURES / "brief_medical.md").read_text(encoding="utf-8")
    (tmp_run_dir / "brief.md").write_text(brief, encoding="utf-8")
    ranked = json.loads((FIXTURES / "ranked_with_cpc.json").read_text(encoding="utf-8"))
    (tmp_run_dir / "ranked-enriched.json").write_text(
        json.dumps(ranked), encoding="utf-8"
    )

    rc = main_with_args(["--run-dir", str(tmp_run_dir)])
    assert rc == 0
    out_path = tmp_run_dir / "compliance-flags.json"
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "metadata" in data
    assert "matched_verticals" in data
    assert isinstance(data["matched_verticals"], list)


def test_emits_empty_array_on_no_match(tmp_run_dir):
    """Neutral brief: file still written; matched_verticals == []."""
    brief = (FIXTURES / "brief_neutral.md").read_text(encoding="utf-8")
    (tmp_run_dir / "brief.md").write_text(brief, encoding="utf-8")
    # Use ranked rows that contain NO regulated tokens — synthesize cookware rows
    cookware_rows = [
        {
            "keyword": "copper bottom cookware",
            "intent": "commercial",
            "score": 200,
            "volume": 500,
            "cpc_micros": 100_000,
        },
        {
            "keyword": "non-stick frying pan",
            "intent": "transactional",
            "score": 180,
            "volume": 800,
            "cpc_micros": 120_000,
        },
    ]
    (tmp_run_dir / "ranked-enriched.json").write_text(
        json.dumps(cookware_rows), encoding="utf-8"
    )

    rc = main_with_args(["--run-dir", str(tmp_run_dir)])
    assert rc == 0
    out_path = tmp_run_dir / "compliance-flags.json"
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["matched_verticals"] == []
