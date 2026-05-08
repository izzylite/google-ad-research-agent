---
phase: 06-negatives-report-assembly-and-persistence
plan: "00"
subsystem: test-infra
tags: [wave-0, tdd, red-stubs, pytest, fixtures]
dependency_graph:
  requires: []
  provides:
    - test_generate_negatives.py RED stubs (NEGT-01/02/03, RPRT-04)
    - test_render_report.py RED stubs (RPRT-01/02/03/04, PRST-01)
    - test_update_index.py RED stub (PRST-02)
    - test_lib_io.py escape_md_cell stubs (RPRT-04)
    - fixtures/negatives_valid.json
    - fixtures/negatives_with_collision.json
    - fixtures/ranked_full.json
    - fixtures/clusters_full.json
    - fixtures/competitor_intel_full.json
    - fixtures/brief_sample.md
  affects:
    - 06-01 (generate_negatives.py turns RED→GREEN)
    - 06-02 (lib/io.py escape_md_cell turns RED→GREEN)
    - 06-03 (render_report.py turns RED→GREEN)
    - 06-04 (update_index.py turns RED→GREEN)
tech_stack:
  added:
    - tabulate>=0.9.0 (pyproject.toml + uv.lock, resolved as 0.10.0)
  patterns:
    - MODULE_MISSING guard (try/import + pytestmark skipif) consistent with Phases 2-5
    - Separate ESCAPE_MISSING guard for lib.io.escape_md_cell (lib exists, function absent)
    - tmp_run_dir fixture with raw/ subdirectory from conftest.py
key_files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/test_generate_negatives.py
    - .claude/skills/google-ad-research/scripts/tests/test_render_report.py
    - .claude/skills/google-ad-research/scripts/tests/test_update_index.py
    - .claude/skills/google-ad-research/scripts/tests/fixtures/negatives_valid.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/negatives_with_collision.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/ranked_full.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/clusters_full.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/competitor_intel_full.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/brief_sample.md
  modified:
    - .claude/skills/google-ad-research/scripts/pyproject.toml (tabulate added)
    - .claude/skills/google-ad-research/scripts/uv.lock (resolved tabulate 0.10.0)
    - .claude/skills/google-ad-research/scripts/tests/test_lib_io.py (+4 escape_md_cell stubs)
decisions:
  - tabulate resolved as 0.10.0 (declared >=0.9.0) — minor version difference is fine; 0.10.0 is backwards-compatible with tablefmt="github"
  - test_update_index.py created as separate file per VALIDATION.md Wave 0 list — PLAN.md bundled index_append into test_render_report.py but VALIDATION.md and objective prompt both specify a dedicated file; followed the more specific requirement
  - escape_md_cell guard uses AttributeError in addition to ImportError — lib.io exists but function is absent; AttributeError handles the case where import succeeds but name is not defined
  - run_dir fixture in test_render_report.py named "run_dir" (not "tmp_run_dir") to avoid shadowing conftest.py's tmp_run_dir fixture which has a different shape (no input files copied)
  - negatives_with_collision.json uses "grocery delivery near me" as collision keyword — exact match to ranked_phase3.json; case-insensitive compare confirmed
metrics:
  duration: 4 min
  completed: 2026-05-08
  tasks_completed: 2
  files_created: 9
  files_modified: 3
---

# Phase 6 Plan 00: Wave 0 RED Stubs + Fixtures + tabulate dependency Summary

**One-liner:** Wave 0 test scaffold with 14 RED stubs across 3 new test files, 6 fixtures, and tabulate>=0.9.0 added to pyproject.toml — all 14 new tests skip cleanly via MODULE_MISSING guard while production modules are absent.

## What Was Built

### Task 1: tabulate dependency (commit e436697)

Added `"tabulate>=0.9.0"` to `scripts/pyproject.toml` dependencies and ran `uv lock`. Resolved as tabulate 0.10.0. Import verified via `uv run --project scripts/ python -c "import tabulate; print(tabulate.__version__)"`.

### Task 2: RED stub test files + fixtures (commit eaeff76)

**Test files created:**

- `test_generate_negatives.py` — 8 test functions, MODULE_MISSING guard for `generate_negatives`, separate ESCAPE_MISSING guard for `lib.io.escape_md_cell`
- `test_render_report.py` — 5 test functions, MODULE_MISSING guard for `render_report`, local `run_dir` fixture that populates a full tmp run folder from fixtures/
- `test_update_index.py` — 1 test function (test_index_append), MODULE_MISSING guard for `update_index`
- `test_lib_io.py` — extended with 4 escape_md_cell stubs, skip-guarded via `_ESCAPE_MISSING`

**Fixtures created:**

- `negatives_valid.json`: 6 rows, 3 tiers (2 Strong, 2 Considered, 2 Investigate), all 6 categories covered exactly once
- `negatives_with_collision.json`: 4 rows, "grocery delivery near me" collides with ranked_phase3.json
- `ranked_full.json`: 8 rows matching ranked_phase3.json shape (complete with all required fields)
- `clusters_full.json`: 2 clusters + orphans, matching clusters_valid.json shape
- `competitor_intel_full.json`: 2 cluster entries with ads + advertisers
- `brief_sample.md`: minimal valid brief covering all 5 required fields

## Verification Results

```
14 skipped in 0.06s   (test_generate_negatives.py + test_render_report.py + test_update_index.py)
8 passed, 4 skipped   (test_lib_io.py — existing tests pass, escape stubs skip)
```

Zero ERRORs. Zero FAILED. All collections clean.

## Deviations from Plan

### Auto-fixed Issues

None.

### Notes

**PLAN.md vs VALIDATION.md discrepancy resolved:** PLAN.md placed `test_index_append` inside `test_render_report.py` (6 functions), while VALIDATION.md and the objective prompt both list `test_update_index.py` as a separate Wave 0 file. Followed the more specific VALIDATION.md + objective prompt. Total test count: 14 (8+5+1) matching the PLAN.md target.

## Self-Check: PASSED

All 9 created files found on disk. Both commits (e436697, eaeff76) verified in git log.
