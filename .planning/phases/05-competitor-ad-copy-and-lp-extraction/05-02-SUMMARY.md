---
phase: 05-competitor-ad-copy-and-lp-extraction
plan: "02"
subsystem: skill
tags: [skill-prompt, competitor-intel, llm-extraction, tavily, serper]

requires:
  - phase: 05-competitor-ad-copy-and-lp-extraction
    provides: competitor_intel.py script with CLI contract and competitor-intel.json schema

provides:
  - SKILL.md Steps 18-20 wiring Phase 5 competitor intel into operator workflow
  - references/phase5-competitor-intel.md extracted rubric for 500-line guard compliance
  - Step 18 documents competitor_intel.py invocation (--run-dir, --gl, --hl) with credit reporting and exit code handling
  - Step 19 provides explicit LLM extraction instructions for headline/cta/offer from raw_content
  - Step 20 is the new Phase 5 stop gate before Phase 6

affects:
  - Phase 6 (report assembly reads competitor_summary built in Step 19)
  - Any operator session starting Phase 5 from SKILL.md

tech-stack:
  added: []
  patterns:
    - Phase section extraction to references/ when SKILL.md approaches 500-line limit
    - Pointer pattern in SKILL.md body — "Load it with the Read tool when entering Phase N"

key-files:
  created:
    - .claude/skills/google-ad-research/references/phase5-competitor-intel.md
  modified:
    - .claude/skills/google-ad-research/SKILL.md

key-decisions:
  - "Phase 5 section body extracted to references/phase5-competitor-intel.md — SKILL.md was 551 lines with full inline content; extraction reduced to 473 lines (within 500-line limit)"
  - "Step 17 forward chain added — 'Phase 5 (competitor intel) begins at Step 18 below.' replaces the hard STOP"
  - "SKILL.md body holds a Read-tool pointer to the references file rather than a bare stub — operator is explicitly told to load the file when entering Phase 5"

requirements-completed: [COMP-03]

duration: 5min
completed: 2026-05-08
---

# Phase 5 Plan 02: SKILL.md Steps 18-20 (Competitor Intel + Value-Prop Extraction) Summary

**SKILL.md updated with Phase 5 operator workflow: Step 17 chains to Step 18 (competitor_intel.py invocation), Step 19 (LLM headline/CTA/offer extraction from raw_content), Step 20 (Phase 5 stop gate); Phase 5 rubric extracted to references/ to maintain the 500-line cap.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-08T07:37:07Z
- **Completed:** 2026-05-08T07:42:00Z
- **Tasks:** 1/1
- **Files modified:** 2

## Accomplishments

- Step 17 stop gate removed; SKILL.md now chains Phase 4 directly into Phase 5
- Step 18 documents `competitor_intel.py` CLI invocation with locale derivation, stdout credit reporting, and exit 0/2/3 handling
- Step 19 provides unambiguous LLM extraction rubric for headline (first H1 or bold phrase, ≤10 words), cta (first imperative/button text), and offer (verbatim price/discount/delivery claim)
- Step 20 is the new explicit STOP gate before Phase 6
- Phase 5 section body extracted to `references/phase5-competitor-intel.md`; SKILL.md reduced from 551 to 473 lines

## Task Commits

1. **Task 1: Update Step 17 and add Phase 5 Steps 18-20 to SKILL.md** - `f1e5970` (feat)

**Plan metadata:** (docs commit follows this summary)

## Files Created/Modified

- `.claude/skills/google-ad-research/SKILL.md` — Step 17 updated; Phase 5 pointer added (473 lines)
- `.claude/skills/google-ad-research/references/phase5-competitor-intel.md` — Steps 18-20 full rubric (extracted for 500-line compliance)

## Decisions Made

- Phase 5 section body extracted to references/ rather than kept inline — SKILL.md was 551 lines with full inline content; the plan explicitly provided for this extraction if the limit was breached.
- SKILL.md pointer tells operator to "Load it with the Read tool when entering Phase 5" — explicit instruction rather than silent pointer ensures the operator knows to load the file before proceeding.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Deviation] Phase 5 section extracted to references/ due to 500-line breach**
- **Found during:** Task 1 (after initial SKILL.md edit)
- **Issue:** SKILL.md reached 551 lines with all Phase 5 steps inline
- **Fix:** Extracted Phase 5 section body to `.claude/skills/google-ad-research/references/phase5-competitor-intel.md`; replaced with a single Read-tool pointer in SKILL.md body. This extraction path was explicitly planned in the task action: "if SKILL.md exceeds 500 lines, extract the Phase 5 section to references/..."
- **Files modified:** `.claude/skills/google-ad-research/SKILL.md`, `.claude/skills/google-ad-research/references/phase5-competitor-intel.md`
- **Verification:** `python -c "assert len(lines) <= 500"` passes at 473 lines
- **Committed in:** f1e5970 (Task 1 commit)

---

**Total deviations:** 1 (planned extraction path — not unexpected; line limit breach was anticipated by plan)
**Impact on plan:** No scope change. Extraction reduces SKILL.md to 473 lines while all required content is in references/phase5-competitor-intel.md.

## Issues Encountered

None — the 500-line extraction was a known contingency already documented in the task action block.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 operator workflow is fully wired: Steps 18-20 documented with all required CLI params, exit code handling, and LLM extraction rubric
- Phase 6 (Negatives, Report Assembly, and Persistence) can begin; its plan will add Steps 21+ to SKILL.md
- COMP-03 requirement is satisfied

---
*Phase: 05-competitor-ad-copy-and-lp-extraction*
*Completed: 2026-05-08*
