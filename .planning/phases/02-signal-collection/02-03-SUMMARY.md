---
phase: 02-signal-collection
plan: "03"
subsystem: api
tags: [tavily, python, pep723, extract, competitor-intel, signal-collection]

# Dependency graph
requires:
  - phase: 02-signal-collection/02-01
    provides: lib/config.py (load_env), lib/log.py (configure_logger)
provides:
  - "tavily_extract.py: TavilyClient.extract() per competitor domain → raw/tavily-<domain>.json with caps, failure persistence, source annotation"
affects: [02-04-merge_signals, 02-05-skill-update, phase-5-competitor-intel]

# Tech tracking
tech-stack:
  added: [tavily-python>=0.7.24, python-slugify>=8.0]
  patterns:
    - "parse_competitor_arg('domain:url1,url2') helper splits CLI --competitor arg"
    - "main_with_args(argv) entry point detects and skips script name if argv[0] is non-flag"
    - "Hard caps enforced before iterating: competitors[:max], urls[:max_per]"
    - "extract_depth='basic' always explicit (never omitted) — Pitfall 8 mitigation"
    - "Annotate each result with source='tavily-extract' + competitor_domain for downstream fan-out"
    - "failed_results persisted verbatim alongside results (not silently dropped)"
    - "Exit-code convention: 0 ok / 2 UsageLimitExceededError / 3 auth (InvalidAPIKeyError, MissingAPIKeyError)"

key-files:
  created:
    - ".claude/skills/google-ad-research/scripts/tavily_extract.py"
  modified: []

key-decisions:
  - "argv[0] skip heuristic: main_with_args strips first element if it does not start with '-' — supports both sys.argv and bare args-only lists without requiring callers to slice first"
  - "BadRequestError per-competitor skip (not fatal exit) — one bad URL list should not abort all competitors"
  - "credits_used = ceil(succeeded / 5) using integer ceiling divide (-(-n // 5)) — basic depth = 1 credit per 5 successful URLs"

patterns-established:
  - "Tavily extract pattern: parse → cap → extract(extract_depth='basic') → annotate → persist (results + failed_results)"
  - "Per-domain output file: raw/tavily-{slugify(domain)}.json (python-slugify, consistent with run-folder slug rule)"

requirements-completed: [SIGL-02]

# Metrics
duration: 15min
completed: 2026-05-08
---

# Phase 02 Plan 03: tavily_extract.py Summary

**Tavily SDK extract caller with 5x5 hard caps, failed_results persistence, and source annotation writing per-domain raw/tavily-<domain>.json files**

## Performance

- **Duration:** ~15 min (continuation run — RED stubs pre-existed from commit 063cb53)
- **Started:** 2026-05-08T04:25:00Z (continuation)
- **Completed:** 2026-05-08T04:41:35Z
- **Tasks:** 1 (GREEN: implement tavily_extract.py)
- **Files modified:** 1

## Accomplishments

- Implemented tavily_extract.py with PEP 723 inline metadata (tavily-python>=0.7.24, python-dotenv>=1.0, python-slugify>=8.0)
- All 4 stub tests turned GREEN: test_caps_enforced, test_uses_basic_depth, test_failed_results_persisted, test_exit_code_3_on_auth_error
- Full test suite: 35 passed, 6 skipped (merge_signals stubs — not yet implemented, expected)
- SIGL-02 satisfied: extract_depth='basic' explicit in every client.extract() call, verified by test

## Task Commits

1. **Task: Implement tavily_extract.py (GREEN)** — `2854141` (feat)

**Plan metadata:** (docs commit — this summary)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/tavily_extract.py` — Tavily SDK extract per competitor domain; parse_competitor_arg(); main_with_args(argv); caps enforced; results annotated; failed_results persisted; exit codes 0/2/3

## Decisions Made

- **argv[0] skip heuristic** in main_with_args: tests pass `["tavily_extract.py", "--run-dir", ...]` (full sys.argv style) while serp_fetch-style callers pass args-only. Solution: strip first element if it does not start with `'-'`. Simple, unambiguous, matches test expectations without requiring callers to slice.
- **BadRequestError → skip competitor, not exit**: A bad URL list for one competitor should not abort the whole batch. Log and continue, consistent with partial-success semantics.
- **ceil(succeeded / 5)** for credits_used: Tavily basic depth bills 1 credit per 5 successful URL extracts. Integer ceiling divide `-(-n // 5)` avoids importing math.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] argv[0] script-name skipping in main_with_args**
- **Found during:** Task 1 (first test run)
- **Issue:** Tests call `main_with_args(["tavily_extract.py", "--run-dir", ...])` — argparse treated "tavily_extract.py" as an unrecognized argument, raising SystemExit(2)
- **Fix:** Added leading-element detection: if `argv[0]` does not start with `'-'`, treat it as the script name and parse `argv[1:]` instead
- **Files modified:** `.claude/skills/google-ad-research/scripts/tavily_extract.py`
- **Verification:** All 4 tests pass GREEN after fix
- **Committed in:** `2854141` (part of feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in argv handling)
**Impact on plan:** Necessary fix for test compatibility. No scope creep. Research.md example used `parse_args()` without args (reads sys.argv directly); adapting to `main_with_args(argv)` contract required this argv[0] strip.

## Issues Encountered

- Stream timeout during original 02-03 execution left only RED test stubs (commit 063cb53). This continuation run picked up from the GREEN phase only, no repeated work.

## User Setup Required

None — no new external services. TAVILY_API_KEY was already required by .env contract from Phase 2 planning.

## Next Phase Readiness

- `tavily_extract.py` is complete and tested. CLI contract stable: `--run-dir`, `--competitor domain:url1,url2`, `--max-competitors`, `--max-urls-per-competitor`
- Output shape: `raw/tavily-{slugify(domain)}.json` with `results` (source-annotated) + `failed_results` + `usage`
- Ready for Phase 2 Plan 04 (merge_signals.py) which consumes both serper.json and tavily-*.json
- merge_signals tests are currently SKIPPED (module missing) — Plan 04 will turn them GREEN

---
*Phase: 02-signal-collection*
*Completed: 2026-05-08*
