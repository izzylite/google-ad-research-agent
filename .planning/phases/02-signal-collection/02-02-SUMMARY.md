---
phase: 02-signal-collection
plan: "02"
subsystem: api
tags: [serper, httpx, httpx-retries, respx, locale, signal-collection, tdd]

# Dependency graph
requires:
  - phase: 02-01
    provides: lib/http.py build_client() with RetryTransport; lib/canon.py canonicalise()
  - phase: 01-xx
    provides: lib/config.load_env(), lib/log.configure_logger(), lib/io, run_init.py run-folder layout

provides:
  - serp_fetch.py: Serper REST caller with gl/hl locale params persisting all 4 signal blocks to raw/serper.json
  - main_with_args(argv) entry point for subprocess-free test invocation
  - Correct exit codes: 0 (ok), 2 (retryable 429/5xx), 3 (fatal 401/403/config/IO)

affects: [tavily_extract, merge_signals, SKILL.md Phase 2 step wiring]

# Tech tracking
tech-stack:
  added: [httpx>=0.28, httpx-retries>=0.5, respx>=0.22 (test only)]
  patterns:
    - "TDD RED→GREEN: stub module allows import + raises NotImplementedError; real tests written before implementation"
    - "main_with_args(argv) pattern: allows test-time invocation without subprocess"
    - "respx.mock context manager: intercept httpx requests + assert request body shape"
    - "respx side_effect capture: capture outgoing request body for locale assertion"
    - "Defensive .get(key, []) on all Serper response blocks: handles absent ads/PAA/related gracefully"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/serp_fetch.py
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_serp_fetch.py

key-decisions:
  - "respx.mock side_effect pattern used to capture outgoing POST body for locale assertion — cleaner than patching urllib internals"
  - "401 and 403 map to exit 3 (fatal auth); all other HTTPStatusError maps to exit 2 (retryable) — consistent with lib/http.py retry policy that excludes 401"
  - "searchParameters echoed verbatim from Serper response into normalised output — enables downstream locale lint without re-parsing"
  - "Stub module (raises NotImplementedError in functions, not at module level) allows pytest collection + real test execution before implementation"

patterns-established:
  - "Pattern: capture_outgoing_body — respx side_effect function that writes request.content JSON to a dict for assertion"
  - "Pattern: tdd_stub_module — importable stub with function signatures raising NotImplementedError (not module-level raise)"

requirements-completed: [SIGL-01, SIGL-04]

# Metrics
duration: 8min
completed: 2026-05-08
---

# Phase 2 Plan 02: serp_fetch.py Summary

**Serper.dev REST caller with gl/hl locale params, all 4 signal blocks (organic/PAA/related/ads), and correct 0/2/3 exit codes — 6 tests RED to GREEN via TDD**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-08T04:23:00Z
- **Completed:** 2026-05-08T04:31:19Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Implemented `serp_fetch.py` with PEP 723 inline metadata, full CLI contract, and `main_with_args()` entry point
- Locale parameters (`gl`, `hl`) required CLI args, passed in Serper POST body, and echoed verbatim via `searchParameters` in persisted JSON
- Defensive `.get(key, [])` on all 4 signal blocks — empty `ads` produces no error and `ads_count: 0` in stdout
- All 6 test_serp_fetch.py tests GREEN; full test suite 31 passed, 10 skipped (future plans)

## Task Commits

Each task was committed atomically:

1. **Task RED: test_serp_fetch.py real implementations + stub module** - `638e62c` (test)
2. **Task GREEN: serp_fetch.py full implementation** - `db07db0` (feat)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/serp_fetch.py` - Serper REST caller with locale + all 4 signal blocks
- `.claude/skills/google-ad-research/scripts/tests/test_serp_fetch.py` - 6 real test implementations (replaced NotImplementedError stubs)

## Decisions Made

- `respx.mock` `side_effect` pattern used to capture outgoing POST body for locale assertion — cleaner than patching; respx.mock context manager ensures clean teardown
- `401` and `403` map to exit 3 (fatal auth); all other `HTTPStatusError` maps to exit 2 (retryable) — consistent with `lib/http.py` `status_forcelist` which excludes 401
- `searchParameters` echoed verbatim from Serper response into normalised output — downstream locale lint can assert `gl`/`hl` are present without re-querying
- Stub module raises `NotImplementedError` inside function bodies (not at module level) so pytest can collect and run the real test bodies before implementation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- `serp_fetch.py` is fully functional and test-verified; ready for SKILL.md wiring in Phase 2 Wave 3
- Next immediate plan: `tavily_extract.py` (02-03)
- `test_tavily_extract.py` is already in RED stub state waiting for implementation
- Full test suite regression-clean: 31 passed, 10 skipped

---
*Phase: 02-signal-collection*
*Completed: 2026-05-08*
