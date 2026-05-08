---
phase: 02-signal-collection
plan: "00"
subsystem: testing
tags: [pytest, fixtures, respx, httpx, tavily-python, inflect, serper]

requires:
  - phase: 01-skill-scaffold
    provides: conftest.py test infrastructure and lib/ package importable from tests/

provides:
  - 3 fixture JSONs (serper_search_uk, serper_empty_ads, tavily_extract_2urls) with correct shapes
  - 5 RED test stub files covering all Phase 2 production modules
  - Extended conftest.py with tmp_run_dir, mock_env, serper_fixture, serper_empty_ads_fixture, tavily_fixture
affects:
  - 02-signal-collection plans A-D (Wave 1-3 turn these stubs GREEN)

tech-stack:
  added: [respx, httpx, httpx-retries, tavily-python, inflect]
  patterns:
    - "Module-missing guard pattern: try/except ImportError → MODULE_MISSING=True → pytestmark skipif"
    - "Fixture JSONs co-located with tests in scripts/tests/fixtures/"
    - "conftest.py FIXTURES_DIR constant for fixture path resolution"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/fixtures/serper_search_uk.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/serper_empty_ads.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/tavily_extract_2urls.json
    - .claude/skills/google-ad-research/scripts/tests/test_lib_http.py
    - .claude/skills/google-ad-research/scripts/tests/test_lib_canon.py
    - .claude/skills/google-ad-research/scripts/tests/test_serp_fetch.py
    - .claude/skills/google-ad-research/scripts/tests/test_tavily_extract.py
    - .claude/skills/google-ad-research/scripts/tests/test_merge_signals.py
  modified:
    - .claude/skills/google-ad-research/scripts/tests/conftest.py

key-decisions:
  - "Module-missing guard via try/except ImportError + pytestmark skipif chosen over xfail — keeps collection clean (skipped not failed) and makes RED/GREEN transition explicit when module is added"
  - "Fixture JSONs use realistic shapes (not empty dicts) to assert correct key presence in future implementation tests"
  - "serper_empty_ads fixture needed as separate file to drive test_empty_ads_no_error without mocking"

patterns-established:
  - "Phase 2 stub pattern: import guard at top of each test file; all functions raise NotImplementedError until module implemented"
  - "Fixture naming: serper_fixture (full), serper_empty_ads_fixture (variant), tavily_fixture (extract)"
  - "tmp_run_dir fixture pre-creates raw/ subdirectory matching production run-folder layout"

requirements-completed: []

duration: 7min
completed: 2026-05-08
---

# Phase 2 Plan 00: Signal Collection Test Scaffolding Summary

**5 RED pytest stub files + 3 fixture JSONs establishing the Nyquist-compliant test contract for Serper, Tavily, lib/http, lib/canon, and merge_signals modules**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-08T04:16:31Z
- **Completed:** 2026-05-08T04:23:08Z
- **Tasks:** 2/2
- **Files modified:** 9 (3 fixture JSONs, 5 test stubs, 1 conftest.py)

## Accomplishments

- Created `tests/fixtures/` directory with 3 realistic JSON fixtures covering full Serper UK response, empty-ads variant, and Tavily extract with failed_results
- Extended `conftest.py` with 5 new Phase 2 fixtures: `tmp_run_dir`, `mock_env`, `serper_fixture`, `serper_empty_ads_fixture`, `tavily_fixture`
- Wrote 5 RED test stub files (23 test functions total) covering every production module in Phase 2 Waves 1-3
- Phase 1 test suite remains fully GREEN (18 passed); Phase 2 stubs skip cleanly (23 skipped, 0 errors)

## Task Commits

1. **Task 1: Create fixture JSONs** - `e513fcb` (test)
2. **Task 2: Extend conftest + 5 RED stubs** - `8615a84` (test)

**Plan metadata:** (final commit hash pending)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/tests/fixtures/serper_search_uk.json` - Full Serper UK grocery response with organic/PAA/related/ads blocks
- `.claude/skills/google-ad-research/scripts/tests/fixtures/serper_empty_ads.json` - Same shape but ads:[] for empty-ads test
- `.claude/skills/google-ad-research/scripts/tests/fixtures/tavily_extract_2urls.json` - Tavily extract with 1 success + 1 failed_result
- `.claude/skills/google-ad-research/scripts/tests/conftest.py` - Extended with 5 Phase 2 fixtures
- `.claude/skills/google-ad-research/scripts/tests/test_lib_http.py` - 3 stubs: retry/429, no-retry/401, success path
- `.claude/skills/google-ad-research/scripts/tests/test_lib_canon.py` - 4 stubs: variants merge, question order, empty raises, token-sort hash
- `.claude/skills/google-ad-research/scripts/tests/test_serp_fetch.py` - 6 stubs: all-blocks, locale params, locale persist, empty-ads, 429, 401
- `.claude/skills/google-ad-research/scripts/tests/test_tavily_extract.py` - 4 stubs: caps, basic-depth, failed_results, auth-error exit code
- `.claude/skills/google-ad-research/scripts/tests/test_merge_signals.py` - 6 stubs: sources array, variants merge, taxonomy, diversity count, coverage, e2e

## Decisions Made

- Module-missing guard (`try/except ImportError` + `pytestmark = pytest.mark.skipif(MODULE_MISSING, ...)`) chosen over `xfail` — keeps collection clean (skipped not failed) and makes the RED-to-GREEN transition explicit when each module is implemented
- Fixture JSONs use realistic shapes, not empty dicts — the organic/PAA/relatedSearches/ads keys and results/failed_results keys will be asserted by future tests
- `tmp_run_dir` fixture pre-creates the `raw/` subdirectory matching the production run-folder layout from Phase 1

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All 23 Phase 2 test stubs are collected and in RED state
- Wave 1 (Plan 02-A): implement `lib/http.py` (turns test_lib_http.py GREEN) and `lib/canon.py` (turns test_lib_canon.py GREEN)
- Wave 2 (Plans 02-B, 02-C): implement `serp_fetch.py` and `tavily_extract.py`
- Wave 3 (Plan 02-D): implement `merge_signals.py`
- No blockers

---
*Phase: 02-signal-collection*
*Completed: 2026-05-08*
