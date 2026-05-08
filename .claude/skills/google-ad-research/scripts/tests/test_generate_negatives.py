"""RED stub tests for generate_negatives.py — Phase 6 Wave 0.

Requirements covered: NEGT-01, NEGT-02, NEGT-03, RPRT-04 (escape_md_cell).
All tests skip while generate_negatives.py is absent (MODULE_MISSING guard).
test_escape_md_cell_pipe uses a separate guard for lib.io.escape_md_cell.

Wave 0: All tests are RED stubs. They turn GREEN in plans 06-01 and 06-02.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module guard — skip all tests while generate_negatives.py does not exist
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import generate_negatives  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="generate_negatives.py not yet implemented")

# ---------------------------------------------------------------------------
# Separate guard for escape_md_cell (lib.io must exist; function added in 06-02)
# ---------------------------------------------------------------------------
try:
    from lib.io import escape_md_cell  # noqa: F401
    ESCAPE_MISSING = False
except (ImportError, AttributeError):
    ESCAPE_MISSING = True

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# NEGT-01 / NEGT-02: validate_negatives — tier + category validation
# ---------------------------------------------------------------------------


def test_validate_negatives_accepts_valid_rows():
    """NEGT-01/02: validate_negatives() returns all 6 fixture rows as valid when schema is correct."""
    from generate_negatives import validate_negatives

    rows = json.loads((FIXTURES_DIR / "negatives_valid.json").read_text(encoding="utf-8"))
    valid, errors = validate_negatives(rows)

    assert len(valid) == 6
    assert len(errors) == 0


def test_validate_negatives_rejects_bad_tier():
    """NEGT-01: Row with tier='Bad' lands in errors, not valid list."""
    from generate_negatives import validate_negatives

    bad_row = {
        "keyword": "grocery jobs",
        "tier": "Bad",
        "category": "jobs-careers",
        "justification": "Invalid tier",
    }
    valid, errors = validate_negatives([bad_row])

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["keyword"] == "grocery jobs"


def test_validate_negatives_rejects_bad_category():
    """NEGT-02: Row with category='made-up' lands in errors, not valid list."""
    from generate_negatives import validate_negatives

    bad_row = {
        "keyword": "some keyword",
        "tier": "Strong",
        "category": "made-up",
        "justification": "Invalid category",
    }
    valid, errors = validate_negatives([bad_row])

    assert len(valid) == 0
    assert len(errors) == 1


def test_three_tiers_present():
    """NEGT-01: negatives_valid.json fixture contains exactly Strong, Considered, Investigate."""
    from generate_negatives import validate_negatives, VALID_TIERS

    rows = json.loads((FIXTURES_DIR / "negatives_valid.json").read_text(encoding="utf-8"))
    valid, _ = validate_negatives(rows)

    tiers_in_output = {row["tier"] for row in valid}
    assert tiers_in_output == VALID_TIERS


def test_category_enum_valid():
    """NEGT-02: All categories in negatives_valid.json are members of VALID_CATEGORIES."""
    from generate_negatives import VALID_CATEGORIES

    rows = json.loads((FIXTURES_DIR / "negatives_valid.json").read_text(encoding="utf-8"))
    for row in rows:
        assert row["category"] in VALID_CATEGORIES, (
            f"Unexpected category {row['category']!r} in fixture"
        )


# ---------------------------------------------------------------------------
# NEGT-03: dedupe_negatives — collision against positive keyword pool
# ---------------------------------------------------------------------------


def test_dedupe_removes_collision():
    """NEGT-03: Keyword present in ranked_phase3.json is removed from deduped list and appears in collisions."""
    from generate_negatives import dedupe_negatives

    negatives = json.loads(
        (FIXTURES_DIR / "negatives_with_collision.json").read_text(encoding="utf-8")
    )
    ranked = json.loads(
        (FIXTURES_DIR / "ranked_phase3.json").read_text(encoding="utf-8")
    )

    deduped, collisions = dedupe_negatives(negatives, ranked)

    # "grocery delivery near me" is in ranked_phase3.json — must be removed
    deduped_keywords = [row["keyword"].lower().strip() for row in deduped]
    assert "grocery delivery near me" not in deduped_keywords
    assert any(c.lower().strip() == "grocery delivery near me" for c in collisions)


def test_dedupe_no_false_positives():
    """NEGT-03: When no negative keyword overlaps positives, deduped list equals input."""
    from generate_negatives import dedupe_negatives

    negatives = [
        {
            "keyword": "grocery delivery jobs",
            "tier": "Strong",
            "category": "jobs-careers",
            "justification": "Recruitment intent",
        },
        {
            "keyword": "free grocery delivery tutorial",
            "tier": "Considered",
            "category": "free-DIY-tutorial",
            "justification": "DIY framing",
        },
    ]
    # ranked pool has no overlap with the above keywords
    ranked = json.loads(
        (FIXTURES_DIR / "ranked_phase3.json").read_text(encoding="utf-8")
    )

    deduped, collisions = dedupe_negatives(negatives, ranked)

    assert len(deduped) == len(negatives)
    assert collisions == []


# ---------------------------------------------------------------------------
# RPRT-04: escape_md_cell — pipe escaping (separate guard; no MODULE_MISSING)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(ESCAPE_MISSING, reason="lib.io.escape_md_cell not yet implemented")
def test_escape_md_cell_pipe():
    """RPRT-04: escape_md_cell escapes pipe characters as \\| for safe GFM table cells."""
    from lib.io import escape_md_cell

    assert escape_md_cell("Free | Same") == r"Free \| Same"
