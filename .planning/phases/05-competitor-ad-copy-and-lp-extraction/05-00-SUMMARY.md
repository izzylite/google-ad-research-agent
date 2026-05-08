---
phase: 05-competitor-ad-copy-and-lp-extraction
plan: "00"
subsystem: testing
tags: [pytest, fixtures, json, competitor-intel, serper, tavily, affiliate-filter]

# Dependency graph
requires:
  - phase: 04-clustering
    provides: clusters.json schema — clusters_phase5.json fixture mirrors this shape
provides:
  - 10 RED pytest stubs for competitor_intel.py (COMP-01, COMP-02, COMP-03)
  - 4 fixture JSON files for Phase 5 test suite
  - competitor_intel.py MODULE_MISSING stub (raises ImportError until Plan 05-01)
affects: [05-01-competitor-intel-implementation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - MODULE_MISSING guard: try/except ImportError + pytestmark skipif — consistent with Phases 2-4 RED stub pattern
    - FIXTURES_DIR pattern: Path(__file__).parent / "fixtures" for fixture loading in tests
    - Wave 0 RED stubs: assert False body in all test functions — replaced with real assertions in Wave 1

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py
    - .claude/skills/google-ad-research/scripts/competitor_intel.py
    - .claude/skills/google-ad-research/scripts/tests/fixtures/clusters_phase5.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/serper_ads_raw.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/serper_ads_empty.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/tavily_lp_response.json
  modified: []

key-decisions:
  - "MODULE_MISSING guard (try/except ImportError + pytest.mark.skipif) for Wave 0 RED stubs — consistent with Phases 2-4 pattern; keeps collection clean and makes RED-to-GREEN transition explicit when competitor_intel.py is implemented in Wave 1"
  - "serper_ads_raw.json includes 2 affiliate entries (1 URL-param via quidco.com?ref=, 1 domain blocklist via awin1.com) + 1 domain duplicate (tesco.com at positions 4 and 5) — minimal but complete coverage of COMP-02 filter cases"
  - "tavily_lp_response.json has 3 ok results + 1 failed_result — covers both success and failure paths for COMP-03 extract_status field"

patterns-established:
  - "Wave 0 RED stub pattern: assert False, 'RED — implement in Plan 05-01' as test body — no premature assertions before module exists"
  - "Fixture shape mirrors production output: clusters_phase5.json uses same schema as clusters.json written by validate_clusters.py"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-05-08
---

# Phase 5 Plan 00: Competitor Intel Wave 0 RED Stubs Summary

**10 RED pytest stubs for competitor_intel.py + 4 fixture files covering COMP-01/02/03 affiliate filter, domain dedup, and Tavily LP extraction**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-08T12:18:55Z
- **Completed:** 2026-05-08T12:26:55Z
- **Tasks:** 2
- **Files modified:** 6 created

## Accomplishments

- 4 fixture JSON files created with realistic shapes: 3-cluster input, 6-ad Serper response (2 affiliate + 1 domain dupe + 3 clean), empty ads block, Tavily LP response (3 ok + 1 failed)
- competitor_intel.py MODULE_MISSING stub (raises ImportError) — consistent with Phases 2-4 Wave 0 pattern
- test_competitor_intel.py: 10 RED stubs covering COMP-01, COMP-02, COMP-03 all skipping cleanly via MODULE_MISSING guard
- Full suite result: 43 passed, 33 skipped — prior-phase tests unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Write 4 fixture JSON files** - `718ed73` (test)
2. **Task 2: Write test stubs and competitor_intel.py MODULE_MISSING stub** - `eb2e207` (test)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/tests/fixtures/clusters_phase5.json` - 3-cluster input fixture (transactional/commercial/informational)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/serper_ads_raw.json` - 6-ad block with 2 affiliate entries + 1 domain duplicate + 3 clean ads
- `.claude/skills/google-ad-research/scripts/tests/fixtures/serper_ads_empty.json` - Empty ads block for informational cluster graceful-handling tests
- `.claude/skills/google-ad-research/scripts/tests/fixtures/tavily_lp_response.json` - Tavily extract response with 3 ok results + 1 failed_result
- `.claude/skills/google-ad-research/scripts/competitor_intel.py` - MODULE_MISSING stub (raises ImportError)
- `.claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py` - 10 RED stubs all skipping via MODULE_MISSING guard

## Decisions Made

- MODULE_MISSING guard (try/except ImportError + pytest.mark.skipif) for Wave 0 RED stubs — consistent with Phases 2-4 pattern; keeps collection clean and makes RED-to-GREEN transition explicit when competitor_intel.py is implemented in Wave 1.
- serper_ads_raw.json includes 2 affiliate entries (1 URL-param via quidco.com?ref=abc123, 1 domain blocklist via awin1.com) + 1 domain duplicate (tesco.com at positions 4 and 5) — minimal but complete coverage of COMP-02 filter cases.
- tavily_lp_response.json has 3 ok results + 1 failed_result — covers both success and failure paths for COMP-03 extract_status field.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — pre-existing `respx` module was already required by other tests; running `uv run --with respx` matches the established pattern for the test suite.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 10 RED stubs collected cleanly by pytest
- Fixtures provide all data shapes needed by Wave 1 implementation
- Plan 05-01 (Wave 1 GREEN) can implement competitor_intel.py and turn all 10 stubs GREEN

---
*Phase: 05-competitor-ad-copy-and-lp-extraction*
*Completed: 2026-05-08*
