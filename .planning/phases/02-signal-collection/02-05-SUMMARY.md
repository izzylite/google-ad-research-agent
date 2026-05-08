---
phase: 02-signal-collection
plan: "05"
subsystem: skill-documentation
tags: [skill, websearch, serper, tavily, merge-signals, keyword-research]

# Dependency graph
requires:
  - phase: 02-signal-collection
    provides: serp_fetch.py, tavily_extract.py, merge_signals.py — the scripts invoked by Phase 2 steps
provides:
  - SKILL.md Phase 2 Steps 6-10: seed gen, WebSearch baseline, serp_fetch, tavily_extract, merge_signals invocation
  - tests/README.md with ad-hoc uv run invocation guide
affects: [phase-3-ranking, future-skill-updates]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SKILL.md conditional gate: 'If Phase 2 is not yet in this SKILL.md, stop here' — enables progressive phase appending"
    - "WebSearch locale embedding: queries carry location/language in query string, not user_location param (Pitfall 4 mitigation)"
    - "Write tool for raw JSON: Claude writes websearch-baseline.json directly (SIGL-03 pattern)"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/README.md
  modified:
    - .claude/skills/google-ad-research/SKILL.md

key-decisions:
  - "WebSearch called from skill prompt (not a Python script) — satisfies SIGL-03 requirement"
  - "extracted_keywords extraction-only rule: verbatim phrases from snippets only, no generated variations (Pitfall 6 mitigation)"
  - "Step 5 STOP replaced with conditional gate to allow Phase 2 continuation without breaking existing Phase 1 behaviour"
  - "Phase 2 ends at Step 10 with explicit STOP — no Phase 3 scope in this skill update"

patterns-established:
  - "Phase gate pattern: each phase boundary uses conditional STOP allowing progressive appending"
  - "Seed quoting pattern: seeds passed as space-separated args to --seeds flag in serp_fetch.py"
  - "Error surfacing pattern: exit code 2 = retryable (ask operator), exit code 3 = fatal (stop)"

requirements-completed: [SIGL-03]

# Metrics
duration: 12min
completed: 2026-05-08
---

# Phase 02 Plan 05: SKILL.md Phase 2 Signal Collection Steps Summary

**SKILL.md extended with Steps 6-10: seed keyword generation, WebSearch baseline via Write tool to websearch-baseline.json, serp_fetch.py + tavily_extract.py via uv run, merge_signals.py merge, and explicit Phase 2 STOP**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-08T12:09:50Z
- **Completed:** 2026-05-08T12:21:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added tests/README.md documenting ad-hoc `uv run --with` invocation for full and single-file test runs
- Appended Phase 2 Steps 6-10 to SKILL.md (279 lines total, under 500-line limit)
- Step 5 STOP replaced with conditional gate enabling progressive phase appending without breaking Phase 1
- SIGL-03 satisfied: WebSearch invoked from skill prompt, output written via Write tool (not a Python script)
- All scripts invoked with exact CLI signatures matching their implementation: `--seeds`, `--gl`, `--hl`, `--competitor`, `--run-dir`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests/README.md** - `c360b41` (chore)
2. **Task 2: Append Phase 2 Steps 6-10 to SKILL.md** - `ee6a041` (feat)

**Plan metadata:** _(final docs commit to follow)_

## Files Created/Modified
- `.claude/skills/google-ad-research/scripts/tests/README.md` — ad-hoc uv run invocation guide for Phase 1+2 tests; full suite and single-file patterns
- `.claude/skills/google-ad-research/SKILL.md` — Phase 2 Steps 6-10 appended; Step 5 STOP made conditional; 279 total lines

## Decisions Made
- WebSearch called from skill prompt (not a Python script) — satisfies SIGL-03, keeps LLM in control of query formulation and locale embedding
- Extracted keywords rule: verbatim phrases from WebSearch snippets only — mitigates Pitfall 6 (LLM keyword hallucination during signal phase)
- Step 5 STOP line replaced with conditional "If Phase 2 is not yet in this SKILL.md, stop here" — allows progressive skill appending without operator confusion
- Phase 2 ends at Step 10 STOP — no Phase 3 scope included per plan

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. (`SERPER_API_KEY` and `TAVILY_API_KEY` in `.env` are prerequisites for running Phase 2, already documented in prior plans.)

## Next Phase Readiness
- SKILL.md Phase 2 is complete and self-contained; operator can execute Steps 6-10 end-to-end with real API keys
- Phase 3 (ranking and scoring) skill steps can be appended using the same conditional gate pattern
- VALIDATION.md rows 2-E-01 and 2-E-02 can now be executed as manual smoke tests against this SKILL.md

---
*Phase: 02-signal-collection*
*Completed: 2026-05-08*
