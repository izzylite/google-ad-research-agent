"""Shared pytest fixtures for Phase 1 tests."""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

# Make scripts/ importable so tests can do `from lib.io import ...` and `import run_init`.
# Test file lives at scripts/tests/<name>.py — scripts/ is one level up.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def tmp_runs_root(tmp_path: Path) -> Path:
    """An isolated `.runs/` root inside pytest's tmp_path."""
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    return runs_root


@pytest.fixture
def sample_brief_text() -> str:
    """A minimal-but-valid brief.md body for write_brief() tests."""
    return (
        "# Campaign Brief\n"
        "\n"
        "**Captured:** 2026-05-08\n"
        "\n"
        "## Required\n"
        "\n"
        "- **Industry:** online groceries\n"
        "- **Product:** same-day grocery delivery\n"
        "- **Location:** UK\n"
        "- **Language:** en-GB\n"
        "- **Audience:** households 25-45 in metro areas\n"
        "\n"
        "## Raw operator paste\n"
        "\n"
        "> Run keywords for our same-day grocery delivery launch in the UK.\n"
    )
