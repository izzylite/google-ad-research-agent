---
phase: 06-negatives-report-assembly-and-persistence
plan: "01"
subsystem: validation
tags: [python, negatives, validator, deduplicator, pep723, stdlib]

# Dependency graph
requires:
  - phase: 05-competitor-intel
    provides: ranked.json positive keyword pool shape for dedup input
  - phase: 06-00
    provides: Wave 0 RED stub tests (test_generate_negatives.py) and fixtures
provides:
  - generate_negatives.py with validate_negatives(), dedupe_negatives(), VALID_TIERS, VALID_CATEGORIES
  - CLI --run-dir interface: reads negatives.json + ranked.json, writes validated output + raw/ copy
  - Exit code contract: 0 clean, 1 warnings, 3 IO/parse error
affects:
  - 06-02 (render_report.py imports dedupe logic; escape_md_cell test unlocks)
  - 06-03 (update_index.py; full phase gate needs generate_negatives GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PEP 723 stdlib-only script (dependencies = []) pattern for validators"
    - "validate-then-dedupe pipeline: validate_negatives() then dedupe_negatives() then check_category_coverage()"
    - "Exit code 1 = operator warning (not fatal); exit 3 = fatal IO/parse; exit 0 = clean"
    - "raw/ copy written only if raw/ dir exists (created by run_init.py, not this script)"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/generate_negatives.py
  modified: []

key-decisions:
  - "Exit 1 (not 2) for warnings: enum errors fixed + collisions removed + missing categories all use exit 1 per CLI contract; exit 2 reserved for future use; VALID_TIERS/VALID_CATEGORIES defined as frozenset at module level for importability by tests"
  - "raw/ write is guarded: only writes if raw/ dir exists (run_init.py responsibility); avoids crashing on bare test environments"
  - "Dedup comparison is case-insensitive strip: neg.keyword.lower().strip() vs ranked pool to catch casing differences from LLM output"

patterns-established:
  - "Pattern: module-level VALID_TIERS / VALID_CATEGORIES frozensets; imported directly by tests without instantiation"
  - "Pattern: (valid_rows, error_rows) tuple return from validate_negatives; (deduped, collisions) from dedupe_negatives — consistent with existing scripts"

requirements-completed:
  - NEGT-01
  - NEGT-02
  - NEGT-03

# Metrics
duration: 12min
completed: 2026-05-08
---

# Phase 6 Plan 01: generate_negatives.py Validator + Deduplicator Summary

**Stdlib-only validator/deduplicator for LLM-generated negatives.json: enum checks (3 tiers, 6 categories), positive-pool dedup against ranked.json, and CLI with exit 0/1/3 contract**

## Performance

- **Duration:** 12 min
- **Started:** 2026-05-08T00:00:00Z
- **Completed:** 2026-05-08T00:12:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Implemented `generate_negatives.py` with `VALID_TIERS`, `VALID_CATEGORIES`, `validate_negatives()`, `dedupe_negatives()`, and `check_category_coverage()` — all exported at module level for test import
- CLI `--run-dir` reads `negatives.json` + `ranked.json`, validates enum correctness, dedupes against positive pool, writes validated output to run_dir root and raw/ copy
- 7/8 `test_generate_negatives.py` tests GREEN; 1 skipped (`test_escape_md_cell_pipe` correctly deferred to plan 06-02)

## Task Commits

1. **Task 1: Implement generate_negatives.py (validator + deduplicator + CLI)** - `4631693` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/generate_negatives.py` - Validator + deduplicator; VALID_TIERS, VALID_CATEGORIES, validate_negatives(), dedupe_negatives(), check_category_coverage(), main() CLI

## Decisions Made

- Exit 1 used for all operator-warning conditions (enum errors fixed, collisions removed, categories missing) per CLI contract from 06-RESEARCH.md; exit 3 reserved for fatal IO/JSON parse failures
- `raw/` write is guarded by `raw_dir.exists()` check — avoids crashing when called outside of a full run environment (e.g., test fixtures without raw/ dir)
- Dedup comparison lowercases and strips both sides to handle LLM casing inconsistencies

## Deviations from Plan

None - plan executed exactly as written. The test file is named `test_generate_negatives.py` (not `test_negatives.py` as referenced in the plan's `<verify>` block) — this is a naming discrepancy in the plan itself; the actual test file on disk was used.

## Issues Encountered

- Plan's `<verify>` block references `test_negatives.py` but the Wave 0 file on disk is `test_generate_negatives.py`. Used the correct on-disk filename. No functional impact.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `generate_negatives.py` is complete and all 7 applicable tests GREEN
- Plan 06-02 (`render_report.py` + `escape_md_cell`) can proceed; `test_escape_md_cell_pipe` will turn GREEN once `lib/io.py` is updated
- No blockers

---
*Phase: 06-negatives-report-assembly-and-persistence*
*Completed: 2026-05-08*
