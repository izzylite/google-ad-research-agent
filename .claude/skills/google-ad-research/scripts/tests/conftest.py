"""Shared pytest fixtures for Phase 1 and Phase 2 tests."""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

# Make scripts/ importable so tests can do `from lib.io import ...` and `import run_init`.
# Test file lives at scripts/tests/<name>.py — scripts/ is one level up.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_runs_root(tmp_path: Path) -> Path:
    """An isolated `.runs/` root inside pytest's tmp_path."""
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    return runs_root


@pytest.fixture
def tmp_run_dir(tmp_path):
    """An isolated run folder with a pre-created raw/ subdirectory."""
    run = tmp_path / "run"
    (run / "raw").mkdir(parents=True)
    return run


@pytest.fixture
def mock_env(monkeypatch):
    """Inject stub API keys so lib/config.load_env() does not raise."""
    monkeypatch.setenv("SERPER_API_KEY", "test-serper-key")


@pytest.fixture
def serper_fixture():
    """Full Serper UK search response (organic/PAA/related/ads)."""
    return json.loads((FIXTURES_DIR / "serper_search_uk.json").read_text())


@pytest.fixture
def serper_empty_ads_fixture():
    """Serper response variant with an empty ads array."""
    return json.loads((FIXTURES_DIR / "serper_empty_ads.json").read_text())


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
