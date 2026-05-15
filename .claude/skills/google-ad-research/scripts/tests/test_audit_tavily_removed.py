"""Phase 12 audit — every Tavily surface deleted.

Each test pins one post-Phase-12 invariant. All RED against Phase 11; Wave 1
flips them GREEN as each requirement (TVLY-01..04, WFCH-01, PULSE-12) lands.
"""
from __future__ import annotations

import re
from pathlib import Path

# Test file lives at:
#   <repo>/.claude/skills/google-ad-research/scripts/tests/test_audit_tavily_removed.py
# parents[0] = tests/
# parents[1] = scripts/
# parents[2] = google-ad-research/ (SKILL_DIR)
# parents[3] = skills/
# parents[4] = .claude/
# parents[5] = <repo root>
SKILL_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
REPO_ROOT = Path(__file__).resolve().parents[5]


# ---------------------------------------------------------------------------
# TVLY-01: tavily_extract.py deleted
# ---------------------------------------------------------------------------
def test_tavily_extract_deleted() -> None:
    assert not (SCRIPTS_DIR / "tavily_extract.py").exists(), \
        "TVLY-01: tavily_extract.py must be deleted"


# ---------------------------------------------------------------------------
# TVLY-02: TAVILY_API_KEY stripped from .env.example AND lib/config.py
# ---------------------------------------------------------------------------
def test_tavily_env_keys_stripped() -> None:
    env_example_text = ""
    skill_env = SKILL_DIR / ".env.example"
    repo_env = REPO_ROOT / ".env.example"
    if skill_env.exists():
        env_example_text = skill_env.read_text(encoding="utf-8")
    elif repo_env.exists():
        env_example_text = repo_env.read_text(encoding="utf-8")

    config_py = (SCRIPTS_DIR / "lib" / "config.py").read_text(encoding="utf-8")

    assert "TAVILY_API_KEY" not in env_example_text, \
        "TVLY-02: TAVILY_API_KEY must be stripped from .env.example"
    assert "TAVILY_API_KEY" not in config_py, \
        "TVLY-02: TAVILY_API_KEY must be stripped from lib/config.py REQUIRED_KEYS"


# ---------------------------------------------------------------------------
# TVLY-03: tavily-python dep stripped from pyproject.toml; tavily-* fixtures removed
# ---------------------------------------------------------------------------
def test_tavily_deps_and_fixtures_stripped() -> None:
    pyproject = (SCRIPTS_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert "tavily-python" not in pyproject, \
        "TVLY-03: tavily-python must be removed from pyproject.toml deps"

    fixture_dir = SCRIPTS_DIR / "tests" / "fixtures"
    if fixture_dir.exists():
        tavily_fixtures = sorted(p.name for p in fixture_dir.glob("*tavily*"))
        assert not tavily_fixtures, \
            f"TVLY-03: tavily-* fixture files must be deleted; found {tavily_fixtures}"


# ---------------------------------------------------------------------------
# TVLY-04: test_tavily_extract.py + tavily_fixture removed
# ---------------------------------------------------------------------------
def test_tavily_test_artifacts_stripped() -> None:
    assert not (SCRIPTS_DIR / "tests" / "test_tavily_extract.py").exists(), \
        "TVLY-04: test_tavily_extract.py must be deleted"

    conftest = (SCRIPTS_DIR / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert not re.search(r"def\s+tavily_fixture\b", conftest), \
        "TVLY-04: tavily_fixture must be removed from conftest.py"


# ---------------------------------------------------------------------------
# WFCH-01: SKILL Phase 5 reference uses WebFetch, not Tavily
# ---------------------------------------------------------------------------
def test_skill_md_uses_webfetch_for_step19() -> None:
    ref = (REFERENCES_DIR / "phase5-competitor-intel.md").read_text(encoding="utf-8")
    assert "WebFetch" in ref, \
        "WFCH-01: references/phase5-competitor-intel.md must reference WebFetch"
    assert "tavily" not in ref.lower(), \
        "WFCH-01: references/phase5-competitor-intel.md must not reference Tavily"


# ---------------------------------------------------------------------------
# PULSE-12: phase7 docs absent (Phase 7 Niche Pulse dropped post-v1.3)
# ---------------------------------------------------------------------------
def test_phase7_docs_removed() -> None:
    assert not (REFERENCES_DIR / "phase7-niche-pulse.md").exists(), \
        "PULSE-12: phase7-niche-pulse.md must be deleted (Phase 7 removed)"


# ---------------------------------------------------------------------------
# All-surfaces audit: walk scripts/ + references/ + SKILL.md; assert no 'tavily'
# ---------------------------------------------------------------------------
SKIP_DIRS = {
    "__pycache__", "fixtures", ".pytest_cache", ".runs",
    ".venv", "venv", "site-packages",
    # Phase 12 test files intentionally contain 'tavily' in assertion messages
    # (test_no_tavily_news_path_in_main, "tavily-extract" not in VALID_SOURCES, etc).
    # The all-surfaces audit targets PRODUCTION code under scripts/ + references/ +
    # SKILL.md; tests/ is the contract-enforcement layer, not a target.
    "tests",
}
SKIP_FILES = {"uv.lock"}


def _iter_source_files() -> list[Path]:
    """Yield production source files under scripts/ (excluding tests/), references/,
    and SKILL.md. These must be Tavily-free post-Phase-12."""
    roots: list[Path] = [SCRIPTS_DIR, REFERENCES_DIR, SKILL_DIR / "SKILL.md"]
    out: list[Path] = []
    for root in roots:
        if root.is_file():
            out.append(root)
            continue
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.name in SKIP_FILES:
                continue
            if p.suffix in {".py", ".md", ".toml"} or p.name in {"SKILL.md", ".env.example"}:
                out.append(p)
    return out


def test_repo_grep_tavily_clean() -> None:
    offenders: list[str] = []
    for path in _iter_source_files():
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "tavily" in txt.lower():
            offenders.append(str(path.relative_to(SKILL_DIR)))
    assert not offenders, \
        f"All-surfaces audit: 'tavily' substring must be absent. Offenders: {offenders}"


# ---------------------------------------------------------------------------
# WFCH-03 (source-level guard): competitor_intel.py has no tavily imports
# ---------------------------------------------------------------------------
def test_competitor_intel_no_tavily_import() -> None:
    src = (SCRIPTS_DIR / "competitor_intel.py").read_text(encoding="utf-8")
    assert "import tavily" not in src and "from tavily" not in src, \
        "WFCH-03: competitor_intel.py must drop Tavily imports"
