---
phase: 04-clustering
plan: "01"
subsystem: testing
tags: [python, pytest, clustering, validation, pep723, stdlib]

# Dependency graph
requires:
  - phase: 04-00
    provides: RED test stubs (9 functions, all skipping) and fixture files for validate_clusters tests
provides:
  - validate_clusters.py — importable module with check_clusters(), check_orphans(), check_avg_size() functions
  - CLI entry point: uv run validate_clusters.py --run-dir with --small-run and --clusters-file flags
  - All 9 invariant checks enforced deterministically (mixed_intent, oversize, undersize, target_undersize, bad_name, orphans, duplicate_keyword, unknown_keyword, avg_size_low)
  - Exit codes 0/1/2/3 as specified
affects: [04-02, 04-03, SKILL.md clustering steps 14-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PEP 723 inline metadata (# /// script block) for stdlib-only Python scripts"
    - "MODULE_MISSING guard pattern for TDD RED stubs (try import, skip if missing)"
    - "ranked_index cross-check: always trust ranked.json intent, not cluster's own intent field"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/validate_clusters.py
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_validate_clusters.py

key-decisions:
  - "check_clusters() accepts small_run=False param to suppress target_undersize warnings for narrow verticals"
  - "check_avg_size() implemented as separate helper (not in check_clusters) to evaluate aggregate statistics"
  - "Orphan detection in CLI operates on ranked_index diff vs clustered keywords set — supplements clusters_json orphans field"
  - "test_orphans_warn updated to call check_orphans(data) directly with explicit orphans list"

patterns-established:
  - "Validator cross-checks cluster keyword intents against ranked.json (source of truth), not cluster's declared intent field"
  - "CLI outputs one JSON line to stdout with valid/cluster_count/orphan_count/violations"

requirements-completed: [CLST-01, CLST-02, CLST-03]

# Metrics
duration: 15min
completed: 2026-05-08
---

# Phase 04 Plan 01: validate_clusters Summary

**Deterministic clustering invariant enforcement via validate_clusters.py — stdlib-only, PEP 723, 9 checks, CLI with exit codes 0/1/2/3**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-08T00:00:00Z
- **Completed:** 2026-05-08T00:15:00Z
- **Tasks:** 2 (RED confirmation + GREEN implementation)
- **Files modified:** 2

## Accomplishments
- Implemented `validate_clusters.py` with all 9 clustering invariants enforced deterministically
- All 9 test stubs flipped from SKIP to PASS (0 skips)
- CLI works: exit 0 for valid inputs, exit 1 for warnings, exit 3 for hard violations, exit 2 for infra errors
- Full suite (43 passed, 20 skipped) confirms no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: RED confirmation** — stubs already committed in `82038bf` (Wave 0)
2. **Task 2: GREEN implementation** — `18828aa` (feat: implement validate_clusters with all 9 invariant checks)

_Note: TDD RED stubs were committed in the Wave 0 plan (04-00). This plan confirmed RED (all 9 skip) then implemented GREEN._

## Files Created/Modified
- `.claude/skills/google-ad-research/scripts/validate_clusters.py` — New module with check_clusters(), check_orphans(), check_avg_size(), CLI __main__
- `.claude/skills/google-ad-research/scripts/tests/test_validate_clusters.py` — Updated test_orphans_warn stub body to call check_orphans()

## Decisions Made
- `check_clusters()` accepts optional `small_run=False` parameter to suppress `target_undersize` warnings — aligns with CLI `--small-run` flag and RESEARCH.md Open Question 1
- `check_avg_size()` kept as separate helper so CLI can call it independently of per-cluster checks
- CLI computes orphans from `ranked_index diff clustered_keywords` in addition to `clusters_json["orphans"]` field, ensuring all unassigned keywords surface
- `test_orphans_warn` stub updated to directly instantiate data with orphans field and call `check_orphans(data)` explicitly

## Deviations from Plan

None - plan executed exactly as written. The `test_orphans_warn` stub update was explicitly specified in the plan's implementation section step 4.

## Issues Encountered
- `test_lib_http.py` fails collection due to missing `respx` module — pre-existing issue unrelated to this plan. Logged to deferred-items. Full suite run with `--ignore=tests/test_lib_http.py` passes clean (43 passed, 20 skipped).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `validate_clusters.py` is ready for use in SKILL.md Steps 14-16 (clustering skill prompt + fix loop)
- CLI surface: `uv run validate_clusters.py --run-dir {run_dir}` with optional `--small-run` and `--clusters-file` flags
- Exit code semantics established: 0=valid, 1=warnings only, 2=infra error, 3=hard violations
- Phase 04-02 (cluster_keywords skill prompt) can now use the validator in its fix loop

---
*Phase: 04-clustering*
*Completed: 2026-05-08*
