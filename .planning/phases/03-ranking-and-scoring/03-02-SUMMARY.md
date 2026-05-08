---
phase: 03-ranking-and-scoring
plan: "02"
subsystem: skill-prompt
tags: [intent-classification, rubric, rank_keywords, skill-md, phase3]

# Dependency graph
requires:
  - phase: 03-01
    provides: rank_keywords.py CLI (uv run invocation contract, exit codes 0/3, stdout JSON schema)
  - phase: 03-00
    provides: test fixtures (keywords_phase2.json, intent_labels.json) confirming intent-labels.json schema

provides:
  - SKILL.md Steps 11-13: complete Phase 3 operator workflow
  - Step 11: locked 4-class intent rubric with anchor examples + temperature=0 + len-check gate + intent-labels.json + intent-meta.json write instructions
  - Step 12: rank_keywords.py uv run invocation with --run-dir and exit-code 0/3 handling
  - Step 13: Phase 3 summary message + STOP directive

affects:
  - Phase 4 clustering (reads intent from ranked.json; depends on Phase 3 STOP being explicit)
  - Any future SKILL.md operator working from Phase 3 instructions

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Progressive SKILL.md phase appending: Phase 2 STOP replaced with forward gate; Phase 3 appended; no Phase 1/2 content modified"
    - "Categorical rubric inline in SKILL.md: 4-class table with anchor examples, borderline guidance, match-type heuristic rules — no external reference file needed (365 lines, under 500-line limit)"
    - "Len-check gate before script invocation: verify intent-labels count == keywords count before advancing to rank_keywords.py"

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/SKILL.md

key-decisions:
  - "SKILL.md Phase 2 STOP replaced with forward gate ('Phase 3 begins at Step 11 below') — maintains Phase 2 completeness signal while unlocking Phase 3 progression"
  - "4-class intent rubric table embedded inline in SKILL.md (not extracted to references/) — 365 lines total stays well under 500-line limit; extraction deferred unless line budget is needed"
  - "match_type passthrough from intent-labels.json confirmed: Step 11 assigns match_type using heuristic rules; rank_keywords.py reads but never recalculates it (consistent with 03-01 decision)"
  - "intent-meta.json write instruction included in Step 11: model name + rubric_version + batches + keywords_labeled + scored_at — Pitfall 3 drift detection metadata"

patterns-established:
  - "Pattern: anchor-in-every-batch — 4 verbatim anchor examples (one per class) included in every batch prompt header to prevent calibration drift across batches"
  - "Pattern: gate-before-advance — each step ends with an explicit 'Do not advance to Step N+1 until X exists' gate"

requirements-completed: [RANK-01]

# Metrics
duration: 5min
completed: 2026-05-08
---

# Phase 3 Plan 02: SKILL.md Steps 11-13 Summary

**SKILL.md extended with 4-class categorical intent rubric (temperature=0, anchor examples, len-check gate), intent-labels.json write instruction, rank_keywords.py uv run invocation, and Phase 3 STOP — 279 → 365 lines.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-08T05:20:00Z
- **Completed:** 2026-05-08T05:25:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Replaced Phase 2 STOP with a forward gate enabling seamless Phase 3 progression in a single skill session
- Appended Step 11 with the full locked 4-class intent rubric table (informational / commercial / transactional / navigational), verbatim anchor examples for all four classes, borderline guidance, match-type heuristic rules, intent-labels.json write instruction with schema, len-check gate, and intent-meta.json write instruction
- Appended Step 12 with the exact `uv run` invocation for rank_keywords.py and exit-code 0/3 handling
- Appended Step 13 with Phase 3 summary message template and explicit STOP directive
- SKILL.md grows from 279 to 365 lines — 135 lines under the 500-line limit; no extraction to references/ required

## Task Commits

1. **Task 1: Append Steps 11-13 to SKILL.md** - `53ab4e2` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `.claude/skills/google-ad-research/SKILL.md` — Phase 2 STOP → forward gate; Phase 3 Steps 11-13 appended (87 lines added, 1 line replaced)

## Decisions Made

- 4-class rubric embedded inline (not in references/) — 365 lines total is comfortably under 500; inline keeps the rubric immediately readable without a secondary file load.
- Step 11 includes intent-meta.json write instruction (model, rubric_version, batches, keywords_labeled, scored_at) — direct implementation of Pitfall 3 drift-detection metadata requirement from 03-RESEARCH.md.
- match_type assigned in Step 11 by skill prompt (not recalculated in rank_keywords.py) — consistent with the passthrough decision locked in 03-01.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 3 is now fully operational end-to-end: operator can run a complete Phase 3 session using Steps 11-13 in SKILL.md
- Phase 4 clustering is not yet in SKILL.md; Step 13 STOP directive explicitly blocks Phase 4+ activity
- ranked.json (output of rank_keywords.py) will be the input for Phase 4 when that phase is implemented

---
*Phase: 03-ranking-and-scoring*
*Completed: 2026-05-08*
