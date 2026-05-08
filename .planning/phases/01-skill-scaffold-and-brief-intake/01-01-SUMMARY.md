---
phase: 01-skill-scaffold-and-brief-intake
plan: "01"
subsystem: infra
tags: [python-dotenv, python-slugify, logging, pathlib, pytest]

# Dependency graph
requires:
  - phase: 01-skill-scaffold-and-brief-intake/01-00
    provides: Wave 0 RED test stubs for lib/io.py and lib/config.py
provides:
  - lib/__init__.py — package marker making scripts/lib/ importable
  - lib/config.py — load_env() with find_dotenv walk + override=False, REQUIRED_KEYS constant
  - lib/io.py — iso_timestamp, slugify_brief, create_run_dir, write_brief filesystem primitives
  - lib/log.py — configure_logger() idempotent stderr StreamHandler
affects:
  - 01-02 (run_init.py imports from lib.config, lib.io, lib.log)
  - all subsequent phases (2-6) import the same primitives

# Tech tracking
tech-stack:
  added: [python-dotenv, python-slugify]
  patterns:
    - find_dotenv(usecwd=True) + load_dotenv(override=False) for OS-env-wins .env loading
    - iso_timestamp() format %Y-%m-%dT%H%M%SZ (Windows-safe, no colons)
    - secrets.token_hex(2) collision suffix for run-dir uniqueness
    - newline="\n" on write_text() for LF-only output on Windows

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/lib/__init__.py
    - .claude/skills/google-ad-research/scripts/lib/config.py
    - .claude/skills/google-ad-research/scripts/lib/io.py
    - .claude/skills/google-ad-research/scripts/lib/log.py
  modified: []

key-decisions:
  - "Used find_dotenv(usecwd=True) instead of usecwd=False so test isolation via monkeypatch.chdir() works; usecwd=False searches from calling frame which is always inside project tree"
  - "Removed __file__-based fallback walk from config.py — find_dotenv(usecwd=True) suffices for both production (CWD = project root) and test (CWD = tmp_path with local .env)"
  - "lib/http.py intentionally absent — RESEARCH.md Open Questions (1) defers HTTP client to Phase 2; no HTTP calls in Phase 1"

patterns-established:
  - "env contract: find_dotenv(usecwd=True) + load_dotenv(override=False); OS shell exports always win over .env file"
  - "timestamp format: %Y-%m-%dT%H%M%SZ UTC (no colons — Windows path-safe)"
  - "run-dir naming: <ts>-<slug> with 4-hex collision suffix via secrets.token_hex(2)"
  - "LF newlines: always pass newline='\\n' to write_text() on Windows"
  - "configure_logger() idempotency: check log.handlers before adding new ones"

requirements-completed: ["SCFD-04", "SCFD-03"]

# Metrics
duration: 6min
completed: 2026-05-08
---

# Phase 1 Plan 01: lib/ Shared Package Summary

**Four-module scripts/lib/ package: env loading with override=False secrets contract, Windows-safe UTC timestamps, python-slugify filesystem naming, collision-retried run-dir creation, and idempotent stderr logging.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-08T14:35:37Z
- **Completed:** 2026-05-08T14:41:00Z
- **Tasks:** 2 / 2
- **Files modified:** 4 created

## Accomplishments

- `lib/config.py`: `load_env()` + `REQUIRED_KEYS` — Phase 1 callers pass `require=()` (never raises); Phase 2+ callers pass required key names to fail-loud on missing secrets
- `lib/io.py`: `iso_timestamp()` (Windows-safe), `slugify_brief()` (Unicode transliteration via python-slugify), `create_run_dir()` (raw/.gitkeep layout + collision retry), `write_brief()` (LF-only)
- `lib/log.py`: `configure_logger()` — idempotent stderr StreamHandler with `[HH:MM:SS] LEVEL name: msg` format
- Wave 0 RED test flip: 12/12 tests GREEN (`test_config.py` 4/4, `test_lib_io.py` 8/8)

## Task Commits

Each task was committed atomically:

1. **Task 1: lib/config.py + lib/log.py + lib/__init__.py** - `14e641a` (feat)
2. **Task 2: lib/io.py** - `0f30649` (feat)

**Plan metadata:** committed with docs commit below

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/lib/__init__.py` — empty package marker
- `.claude/skills/google-ad-research/scripts/lib/config.py` — `load_env(*, require=())`, `REQUIRED_KEYS`
- `.claude/skills/google-ad-research/scripts/lib/io.py` — `iso_timestamp`, `slugify_brief`, `create_run_dir`, `write_brief`
- `.claude/skills/google-ad-research/scripts/lib/log.py` — `configure_logger(name, level)`

## Exported API Surface

### lib/config.py

```python
REQUIRED_KEYS: tuple[str, ...] = ("SERPER_API_KEY", "TAVILY_API_KEY")

def load_env(*, require: tuple[str, ...] = ()) -> Path:
    # Locates .env via find_dotenv(usecwd=True), loads with override=False.
    # Raises EnvironmentError listing missing keys if any `require` key is unset.
    # Returns Path to .env (or empty Path() if not found and require=()).
```

### lib/io.py

```python
def iso_timestamp() -> str:
    # UTC "%Y-%m-%dT%H%M%SZ" — no colons, Windows filesystem-safe.

def slugify_brief(slug_source: str, *, max_length: int = 60) -> str:
    # python-slugify with Unicode transliteration; ValueError on empty/whitespace input.

def create_run_dir(runs_root: Path, *, slug_source: str) -> Path:
    # Creates <ts>-<slug>/raw/.gitkeep; retries up to 5x with -<4hex> on collision.

def write_brief(run_dir: Path, brief_text: str) -> Path:
    # Writes brief.md with encoding="utf-8", newline="\n" (LF only on Windows).
```

### lib/log.py

```python
def configure_logger(name: str = "gar", level: int = logging.INFO) -> logging.Logger:
    # Idempotent: returns existing logger if handlers already attached.
    # Single StreamHandler -> sys.stderr with "[HH:MM:SS] LEVEL name: msg" format.
    # propagate = False.
```

## Env-loading Contract

`find_dotenv(usecwd=True)` walks up from the current working directory to find `.env`. `load_dotenv(override=False)` means OS shell exports always win over file values. `require=()` is the Phase 1 default because `run_init.py` needs no API keys — it only captures the brief. Phase 2+ scripts pass the keys they actually need (`require=("SERPER_API_KEY",)`) to fail loudly if the operator forgot to set them.

## Timestamp Format

`%Y-%m-%dT%H%M%SZ` (UTC, no colons). Windows treats `:` as a drive separator and forbids it in filenames (per Microsoft naming rules). The format is also filesystem-safe on all Unix systems. Example: `2026-05-08T143024Z`.

## Collision-Retry Suffix Scheme

`create_run_dir` tries `<ts>-<slug>` first. On `FileExistsError` (same-second double-call), it appends `-<4hex>` where the 4 hex chars come from `secrets.token_hex(2)` — 65 536 unique suffixes per second, collision-resistant for human-paced operations. Up to 5 retries; raises `OSError` if all fail.

## Intentional Omissions

`lib/http.py` is intentionally absent. RESEARCH.md Open Questions (1) explicitly defers the HTTP client to Phase 2. There are no HTTP calls in Phase 1. Writing an untested stub now risks API mismatch when Serper/Tavily calls are designed in Phase 2.

## Decisions Made

- Used `find_dotenv(usecwd=True)` instead of `usecwd=False`: `usecwd=False` searches from the calling stack frame, which during tests is always inside the project tree — it finds the project `.env` even when `monkeypatch.chdir(tmp_path)` isolates the test. `usecwd=True` searches from CWD, respecting test isolation.
- Removed `__file__`-based fallback walk: unnecessary once `usecwd=True` is in place; the fallback would always find the project `.env` regardless of CWD, breaking the `test_load_env_missing_required_raises` assertion.
- `lib/http.py` deferred to Phase 2 as specified in RESEARCH.md.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] find_dotenv usecwd=True instead of usecwd=False**
- **Found during:** Task 1 (test_config.py verification)
- **Issue:** Plan specified `usecwd=False` + `__file__` fallback. This causes `find_dotenv` to walk up from the calling frame (the test file, inside the project) and always find the project `.env`, even when `monkeypatch.chdir(tmp_path)` isolates the test directory. `test_load_env_missing_required_raises` failed: DID NOT RAISE — keys were loaded from project `.env`.
- **Fix:** Changed to `find_dotenv(usecwd=True)` and removed the `__file__` fallback. Production scripts run from the project root (or subdir); CWD-based search finds the project `.env` correctly. Tests that chdir to OS temp dirs have no `.env` in their parent chain.
- **Files modified:** `.claude/skills/google-ad-research/scripts/lib/config.py`
- **Verification:** `test_load_env_missing_required_raises` now raises `EnvironmentError`; all 4 `test_config.py` tests pass.
- **Committed in:** `14e641a` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix required for test isolation correctness. Production behavior unchanged (CWD-based search finds project `.env` in all normal execution paths). No scope creep.

## Issues Encountered

- `find_dotenv(usecwd=False)` semantics differ from the plan's description: it searches from the calling stack frame, not from `__file__`. In a test context the calling frame is inside the project tree, defeating test isolation. Resolved by switching to `usecwd=True`.

## User Setup Required

None — no external service configuration required for this plan. The `.env` is already populated (per environment context).

## Next Phase Readiness

- `lib/` package fully operational; `run_init.py` (Plan 01-02) can `from lib.config import load_env`, `from lib.io import slugify_brief, iso_timestamp, create_run_dir, write_brief`, `from lib.log import configure_logger` with no import errors.
- SCFD-04 satisfied: lib/ provides config loader, IO helpers, structured logging.
- SCFD-03 partially satisfied: env contract pinned in lib/config.py. Plan C (01-03) audits `.env`/`.env.example`/`.gitignore` to close it fully.
- `test_run_init.py` (Wave 0 stub) remains RED until Plan 01-02 creates `run_init.py`.

---
*Phase: 01-skill-scaffold-and-brief-intake*
*Completed: 2026-05-08*
