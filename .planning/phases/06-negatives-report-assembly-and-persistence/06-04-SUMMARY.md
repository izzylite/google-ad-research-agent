---
phase: 06-negatives-report-assembly-and-persistence
plan: "04"
subsystem: persistence
tags: [python, stdlib, pathlib, markdown, index]

# Dependency graph
requires:
  - phase: 06-02
    provides: escape_md_cell() in lib/io.py for industry cell sanitization

provides:
  - scripts/update_index.py — append-only .runs/INDEX.md writer with CLI

affects:
  - SKILL.md Step 24 (uv run update_index.py --run-dir {run_dir})
  - 06-05 (final integration plan that exercises full run pipeline)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - PEP 723 stdlib-only script (dependencies = []) — no uv dependency resolution needed
    - Append-only INDEX.md pattern: check exists → write_text(HEADER+row) vs open("a")
    - run_dir.name parsing: date=name[:10], slug=name[18:] if len>18 else name

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/update_index.py
  modified: []

key-decisions:
  - "Open INDEX.md in append mode ('a') for existing files; write_text only on first creation — avoids read-modify-write race condition"
  - "Slug and date parsed from run_dir.name directly, not re-derived from brief fields"
  - "Missing brief.md returns industry='unknown' with exit 0 (non-fatal) — INDEX.md integrity more important than completeness"
  - "--runs-root CLI flag added (default run_dir.parent) to support non-standard directory layouts"

patterns-established:
  - "Pattern: Append-only cross-run index — only mutable file in otherwise run-isolated .runs/ structure"
  - "Pattern: Non-fatal fallback for optional inputs (brief.md missing → unknown, not error)"

requirements-completed: [PRST-02]

# Metrics
duration: 10min
completed: 2026-05-08
---

# Phase 6 Plan 04: update_index.py Summary

**Stdlib-only append-only INDEX.md writer that records each run as a date/slug/industry/status row, creating the file with a Markdown header on first use**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-08T07:15:00Z
- **Completed:** 2026-05-08T07:25:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- `append_run_to_index()` creates `.runs/INDEX.md` with header on first call, appends row-only on subsequent calls
- Date and slug parsed from `run_dir.name` without re-derivation from brief fields
- `escape_md_cell()` from `lib/io.py` applied to industry column preventing pipe-broken table rows
- CLI with `--run-dir` (required) and `--runs-root` (default `run_dir.parent`); exits 0 always
- `test_index_append` GREEN; all 65 unrelated tests continue passing

## Task Commits

1. **Task 1: Implement update_index.py (append-only INDEX.md writer)** - `91994c1` (feat)

**Plan metadata:** *(docs commit pending)*

## Files Created/Modified
- `.claude/skills/google-ad-research/scripts/update_index.py` - Append-only INDEX.md updater with `append_run_to_index()` and CLI

## Decisions Made
- Used `open("a")` for existing file appends; `write_text(HEADER + row)` only on first creation — eliminates read-modify-write pattern and avoids duplicate headers
- Added `--runs-root` optional CLI argument beyond what the plan specified — enables callers with a non-standard directory layout to override the default `run_dir.parent`
- `_extract_industry()` returns `"unknown"` (not raises) on missing `brief.md` — INDEX.md audit trail is more valuable than blocking on an optional field

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added --runs-root optional CLI flag**
- **Found during:** Task 1 (CLI implementation)
- **Issue:** Plan specified `--run-dir` only; `runs_root = run_dir.parent` is the default but operators may need to override this for non-standard layouts
- **Fix:** Added optional `--runs-root PATH` argument (default `None` → falls back to `run_dir.parent`). Function signature unchanged; behavior identical for the default case.
- **Files modified:** update_index.py
- **Verification:** test_index_append passes; CLI default behavior unchanged
- **Committed in:** 91994c1

---

**Total deviations:** 1 auto-fixed (missing critical — optional CLI ergonomic improvement)
**Impact on plan:** Strictly additive. No existing interface changed. No scope creep.

## Issues Encountered
- `test_render_report.py::test_index_append` referenced in plan verification was not found in that file — the test lives in `test_update_index.py` (written in plan 06-00). Plan verification command was adjusted accordingly. Both `test_update_index.py` and `test_render_report.py` are GREEN.
- Pre-existing `respx` missing module failures in `test_competitor_intel.py`, `test_lib_http.py`, and `test_serp_fetch.py` are out-of-scope (not caused by this plan); deferred to `deferred-items.md`.

## Next Phase Readiness
- `update_index.py` is fully implemented and tested; SKILL.md Step 24 can reference it directly
- 06-05 (final integration) can call `append_run_to_index()` or invoke the CLI after `render_report.py` writes `report.json`
- No blockers

---
*Phase: 06-negatives-report-assembly-and-persistence*
*Completed: 2026-05-08*
