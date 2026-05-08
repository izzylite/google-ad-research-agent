---
phase: "06"
plan: "05"
subsystem: skill-wiring
tags: [skill, phase6, negatives, report-assembly, persistence, lazy-load]
dependency_graph:
  requires: ["06-03", "06-04"]
  provides: ["phase6-negatives-report.md", "SKILL.md-phase6-entry"]
  affects: ["SKILL.md", "references/phase5-competitor-intel.md"]
tech_stack:
  added: []
  patterns: ["lazy-load reference pattern", "phase gate pattern"]
key_files:
  created:
    - .claude/skills/google-ad-research/references/phase6-negatives-report.md
  modified:
    - .claude/skills/google-ad-research/SKILL.md
    - .claude/skills/google-ad-research/references/phase5-competitor-intel.md
decisions:
  - "Step 21 instructs LLM to write to {run_dir}/negatives.json (not raw/) — generate_negatives.py copies to raw/ per RPRT-05"
  - "Step 26 is a hard STOP — no continuation prompts after final summary"
  - "Phase 6 entry in SKILL.md follows identical lazy-load pattern as Phase 5 (one paragraph + Read tool instruction)"
metrics:
  duration_seconds: 87
  completed_date: "2026-05-08"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
---

# Phase 06 Plan 05: SKILL.md Phase 6 Wiring — Negatives + Report + Index + Final STOP Summary

Phase 6 wired end-to-end into SKILL.md: lazy-load reference file (Steps 21-26) created, Phase 5 stop gate replaced with Phase 6 entry pointer, SKILL.md stays at 479 lines (well within 500-line budget).

## What Was Built

### Task 1: references/phase6-negatives-report.md

Created the full Phase 6 operator instructions at `.claude/skills/google-ad-research/references/phase6-negatives-report.md` (153 lines, 6 steps):

- **Step 21** — LLM reads ranked.json + brief.md, generates 30-50 negatives as JSON array (3 tiers, 6 categories, justification per row), writes to `{run_dir}/negatives.json` via Write tool. Includes baseline checklist (jobs/free/refurb triggers) and gate condition (≥1 entry per tier).
- **Step 22** — `uv run generate_negatives.py --run-dir {run_dir}` validates + deduplicates. Exit 0: continue. Exit 1: surfaces warnings (enum errors, collisions, missing categories) with proceed/fix operator choice. Exit 3: fatal stop.
- **Step 23** — `uv run render_report.py --run-dir {run_dir}` renders report.md + report.json. Gate: both files must exist.
- **Step 24** — `uv run update_index.py --run-dir {run_dir}` appends row to `.runs/INDEX.md`. Gate: INDEX.md updated.
- **Step 25** — Read tool loads report.md, confirms all 7 required sections present, summarizes findings to operator.
- **Step 26** — Final summary (run path, report paths, keyword count, cluster count, negative tier breakdown) + hard **STOP**.

### Task 2: SKILL.md + phase5-competitor-intel.md

Two edits:

1. **references/phase5-competitor-intel.md (Step 20):** Replaced `"Phase 6 (report assembly) is not yet available in this skill."` + `**STOP. Do not proceed to any Phase 6+ activity.**` with `"Phase 6 (report assembly) begins at Step 21. Load .../phase6-negatives-report.md with the Read tool when entering Phase 6."` — the workflow is now fully continuous.

2. **SKILL.md:** Added Phase 6 section at the bottom following the identical lazy-load pattern used for Phase 5 — a one-paragraph entry with a Read tool instruction pointing to `references/phase6-negatives-report.md`. SKILL.md is now 479 lines (≤500 budget satisfied).

## Verification

```
SKILL lines: 479
SKILL has Phase 6: True
SKILL has ref link: True
Steps 21-26 in ref: True
P5 no longer blocked: True
```

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| f53f5f9 | feat(06-05): add references/phase6-negatives-report.md with Steps 21-26 |
| 8d6a266 | feat(06-05): wire Phase 6 into SKILL.md + fix Phase 5 stop gate |

## Self-Check: PASSED

- `references/phase6-negatives-report.md` exists: FOUND
- `SKILL.md` ≤ 500 lines (479): PASSED
- Phase 5 stop no longer says "not yet available": PASSED
- Steps 21-26 all present in reference: PASSED
- generate_negatives.py CLI referenced in Step 22: PASSED
- render_report.py CLI referenced in Step 23: PASSED
- update_index.py CLI referenced in Step 24: PASSED
- Hard STOP in Step 26: PASSED
- Commit f53f5f9 exists: FOUND
- Commit 8d6a266 exists: FOUND
