---
phase: 01-skill-scaffold-and-brief-intake
plan: "00"
subsystem: test-infrastructure
tags: [pytest, tdd, wave-0, test-stubs, red-green]
dependency_graph:
  requires: []
  provides:
    - scripts/tests/__init__.py
    - scripts/tests/conftest.py
    - scripts/tests/test_lib_io.py
    - scripts/tests/test_config.py
    - scripts/tests/test_run_init.py
  affects:
    - "01-01-PLAN.md (Plan A) — test_lib_io.py and test_config.py will go GREEN"
    - "01-02-PLAN.md (Plan B) — test_run_init.py will go GREEN"
tech_stack:
  added:
    - pytest 9.x (provisioned via uv run --with pytest, no pyproject.toml)
    - python-dotenv (provisioned via uv run --with)
    - python-slugify (provisioned via uv run --with)
  patterns:
    - PEP 723 ad-hoc test execution (no project-level pytest config)
    - sys.path.insert for scripts/ importability without package install
    - subprocess test pattern for CLI scripts (sys.executable, no recursive uv run)
key_files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/__init__.py
    - .claude/skills/google-ad-research/scripts/tests/conftest.py
    - .claude/skills/google-ad-research/scripts/tests/test_lib_io.py
    - .claude/skills/google-ad-research/scripts/tests/test_config.py
    - .claude/skills/google-ad-research/scripts/tests/test_run_init.py
  modified: []
decisions:
  - "No pyproject.toml — Wave 0 uses ad-hoc uv run --with pytest; promote to project-level deps in Phase 2"
  - "sys.executable for subprocess tests — avoids recursive uv run overhead (~2s saved per test)"
  - "sys.path.insert in conftest.py — makes scripts/ importable without package install"
metrics:
  duration: "~3 minutes"
  tasks_completed: 3
  tasks_total: 3
  files_created: 5
  files_modified: 0
  completed_date: "2026-05-08"
---

# Phase 1 Plan 00: Wave 0 Pytest Scaffolding Summary

**One-liner:** Five RED test stubs pin the lib/io.py, lib/config.py, and run_init.py interface contracts before any implementation begins.

---

## What Was Built

### Test Files Written

| File | Tests | Covers |
|------|-------|--------|
| `scripts/tests/__init__.py` | — | Python package marker (empty) |
| `scripts/tests/conftest.py` | — | Shared fixtures: `tmp_runs_root`, `sample_brief_text` |
| `scripts/tests/test_lib_io.py` | 8 | `iso_timestamp`, `slugify_brief` (basic/unicode/empty/max_length), `create_run_dir` (layout/collision), `write_brief` (verbatim) |
| `scripts/tests/test_config.py` | 4 | `REQUIRED_KEYS`, `load_env(require=())`, `load_env` missing-required raises, `override=False` semantics |
| `scripts/tests/test_run_init.py` | 6 | Happy path folder creation, verbatim brief write, collision retry, empty brief (exit 2), empty slug-source (exit 2), single-line JSON stdout |

**Total:** 18 tests collected in 0.02s (well above the required 14, sub-second discovery confirmed).

---

## Fixture Conventions

Both fixtures are defined in `conftest.py` and auto-available to all test files in the package:

**`tmp_runs_root(tmp_path: Path) -> Path`**
An isolated `.runs/` root inside pytest's `tmp_path`. Every test that creates run directories gets a fresh, clean root with no cross-test pollution.

**`sample_brief_text() -> str`**
A minimal-but-valid `brief.md` body covering all 5 required intake fields (industry, product, location, language, audience). Used by both unit tests (`test_write_brief_verbatim`) and subprocess tests (`test_creates_run_folder`, `test_brief_written_verbatim`).

---

## Interface Contracts Pinned

These contracts are now locked in place by the tests. Plans A and B must implement to these exact signatures:

### From `scripts/lib/io.py` (Plan A)

```python
def iso_timestamp() -> str:
    """Returns YYYY-MM-DDTHHMMSSZ — UTC, no colons (Windows-safe filename)."""

def slugify_brief(slug_source: str, *, max_length: int = 60) -> str:
    """Raises ValueError on empty or whitespace-only input."""

def create_run_dir(runs_root: Path, *, slug_source: str) -> Path:
    """Creates <ts>-<slug>/raw/.gitkeep. On same-second collision: adds -[0-9a-f]{4} suffix."""

def write_brief(run_dir: Path, brief_text: str) -> Path:
    """Writes brief.md verbatim, LF newlines (no CRLF on Windows)."""
```

### From `scripts/lib/config.py` (Plan A)

```python
REQUIRED_KEYS: tuple[str, ...] = ("SERPER_API_KEY", "TAVILY_API_KEY")

def load_env(*, require: tuple[str, ...] = ()) -> Path:
    """Finds .env via find_dotenv walk. Raises EnvironmentError if require keys missing.
    override=False: OS env wins over .env file values."""
```

### From `scripts/run_init.py` (Plan B)

- CLI: `--slug-source <phrase>` (required), `--runs-root <path>` (optional, default project-root/.runs)
- Reads brief from stdin (UTF-8)
- Stdout: exactly one JSON line `{"run_dir": str, "slug": str, "timestamp": str, "brief_path": str}`
- Exit codes: 0 ok, 2 missing/empty slug-source or empty stdin, 3 io error

---

## Test Run Command

```bash
# Quick run (targeted):
uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/test_run_init.py -x

# Full suite:
uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/ -x

# Collect-only (verify no syntax errors):
uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/ --collect-only
```

---

## RED State Confirmation

Tests are RED today — confirmed by running the full suite:

```
FAILED test_config.py::test_required_keys_defined
  ModuleNotFoundError: No module named 'lib'
```

All 18 tests fail with `ModuleNotFoundError: No module named 'lib'` (for lib/ tests) or `FileNotFoundError` (for run_init.py subprocess tests) — exactly as intended. Plan A will turn test_lib_io.py and test_config.py GREEN. Plan B will turn test_run_init.py GREEN.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check: PASSED

All 5 created files confirmed on disk. All 3 task commits (c281d7e, 98d1e57, 778f1f5) confirmed in git log.
