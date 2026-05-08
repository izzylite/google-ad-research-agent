"""RED stub tests for update_index.py — Phase 6 Wave 0.

Requirements covered: PRST-02 (.runs/INDEX.md append).
All tests skip while update_index.py is absent (MODULE_MISSING guard).

Wave 0: All tests are RED stubs. They turn GREEN in plan 06-04.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module guard — skip all tests while update_index.py does not exist
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import update_index  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="update_index.py not yet implemented")


# ---------------------------------------------------------------------------
# PRST-02: append_run_to_index writes date + slug + no duplicate header
# ---------------------------------------------------------------------------


def test_index_append(tmp_path: Path) -> None:
    """PRST-02: append_run_to_index() adds a row with date and slug to INDEX.md.

    Calling it a second time must NOT duplicate the header — header appears exactly once.
    """
    from update_index import append_run_to_index

    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    run_dir = runs_root / "2026-05-08T143024Z-grocery-delivery-uk"
    run_dir.mkdir()

    industry = "online groceries"

    # First call — creates INDEX.md with header + first row
    append_run_to_index(runs_root, run_dir, industry, status="complete")

    index_path = runs_root / "INDEX.md"
    assert index_path.exists()

    content = index_path.read_text(encoding="utf-8")
    assert "2026-05-08" in content
    assert "grocery-delivery-uk" in content

    # Second call — appends a second row; header must NOT be duplicated
    run_dir_2 = runs_root / "2026-05-09T100000Z-grocery-delivery-uk-v2"
    run_dir_2.mkdir()
    append_run_to_index(runs_root, run_dir_2, industry, status="complete")

    content_2 = index_path.read_text(encoding="utf-8")
    # Header line "# Run History" must appear exactly once
    assert content_2.count("# Run History") == 1
    # Both dates present
    assert "2026-05-08" in content_2
    assert "2026-05-09" in content_2
