---
phase: 14-positives-sync
plan: 05
subsystem: documentation
tags: [skill-md, positives-sync, llm-retag, phase8-subflow, pos-06]

# Dependency graph
requires:
  - phase: 14-positives-sync
    provides: "perf_synth.py cross_ref_positives + positives-sync.json (Plan 14-02), render_positives_sync_section (Plan 14-03), export_csv positives filter (Plan 14-04)"
provides:
  - "Step 34a LLM re-tag rubric in references/phase8-account-data.md (trigger / instruction body / 5 borderline anchor cases / output contract / anti-patterns / downstream pointer)"
  - "SKILL.md Phase 8 pointer extended to reference Step 34a + POS-06 (single-character-style edit; final line count 495/500)"
  - "Phase 14 closeout: live e2e verified on a real Google Ads account (POS-01..07 all GREEN end-to-end)"
affects: [future-phase-15-plus, llm-retag-pattern-replication, skill-md-line-budget-discipline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sub-step LLM re-tag pattern: script writes a JSON sidecar, SKILL.md prompts Claude to refine that sidecar in place via Write tool, downstream renderers re-read on next invocation"
    - "Step pointer compaction: when SKILL.md is at the 500-line cap, extend an existing parenthetical instead of adding a bullet — preserves discoverability without cap breach"
    - "Anchor-case prompts: borderline classification prompts must embed 5 verbatim labelled examples (token reorder / match-type drift / semantic synonym / narrowing opportunity / locale variant) to suppress LLM drift"

key-files:
  created: []
  modified:
    - ".claude/skills/google-ad-research/references/phase8-account-data.md (+49 lines — new Step 34a section)"
    - ".claude/skills/google-ad-research/SKILL.md (1-line edit to Phase 8 pointer; final 495/500 lines)"

key-decisions:
  - "Step 34a placed in references/phase8-account-data.md (not SKILL.md top-level Phase 14 section) — SKILL.md was at 494/500 lines, no budget for a new top-level Phase; the perf_synth invocation producing positives-sync.json already lives in Step 34, so 34a is the natural slot."
  - "5 anchor borderline cases pulled verbatim from 14-CONTEXT.md (token reorder, match-type drift, semantic synonym, narrowing opportunity, locale variant) — same examples used in 14-CONTEXT.md decisions, in the references rubric, and in the SKILL.md pointer downstream chain. Single source of truth."
  - "Output contract explicitly forbids bucket-name invention — LLM may only re-distribute entries between the 4 fixed buckets (already_active / paused_in_account / covered_by_broad / new_to_add). retag_reason field appended on every re-tagged entry for operator audit."
  - "Phase 14 closeout did NOT require a follow-up commit to re-render the live run — Step 34a downstream pointer notes render_report.py + export_csv.py should be re-invoked AFTER the LLM re-tag step. Live run was verified pre-retag; post-retag verification deferred to first real operator use."

patterns-established:
  - "LLM re-tag step pattern: anchored borderline cases + explicit output contract + anti-patterns + downstream contract pointer — replicable for any future sidecar that needs LLM polish on top of script output"
  - "Single-character SKILL.md edits when at line-budget cap: append to existing parenthetical, no new bullets, no new blank lines"

requirements-completed: [POS-06]

# Metrics
duration: ~12min
completed: 2026-05-15
---

# Phase 14 Plan 05: SKILL.md LLM Re-Tag Step + Phase 14 Closeout Summary

**Step 34a LLM re-tag rubric added to references/phase8-account-data.md (5 borderline anchor cases + output contract + anti-patterns); SKILL.md Phase 8 pointer extended to surface Step 34a (495/500 lines). Phase 14 verified end-to-end on a live Google Ads account: positives-sync.json shows stats {our_total:83, already_active:11, paused:0, covered_by_broad:8, new_to_add:64} and positives.csv = 64 net-new rows + header.**

## Performance

- **Duration:** ~12 min (excludes human-verify wait time on the operator side)
- **Started:** 2026-05-15T12:45Z
- **Completed:** 2026-05-15T13:00Z (approximate; checkpoint approval received from operator)
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 2

## Accomplishments

- Step 34a LLM re-tag rubric drafted in references/phase8-account-data.md with all 6 required components: trigger / instruction body / 5 anchor cases / output contract / anti-patterns / downstream pointer.
- SKILL.md Phase 8 pointer extended with single-character-style edit pointing at Step 34a + POS-06 + positives sync — final line count 495/500, well under the CLAUDE.md cap.
- Phase 14 verified end-to-end on a live Google Ads account (Lake Worth car-accident / urgent-care brief): all 7 POS checkpoints confirmed on real data. Operator approved.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Step 34a LLM re-tag rubric to references/phase8-account-data.md** — `8983c68` (docs)
2. **Task 2: Update SKILL.md Phase 8 pointer — line-budget-aware** — `f7e80ef` (docs)
3. **Task 3: Human-verify Phase 14 end-to-end on a real run** — (no commit; operator approval on live e2e run)

**Plan metadata:** (this commit — docs(14-05): complete LLM re-tag plan after live e2e approval)

## Files Created/Modified

- `.claude/skills/google-ad-research/references/phase8-account-data.md` — +49 lines; new "## Step 34a: LLM re-tag for positives-sync (POS-06)" section between existing Step 34 (perf_synth invocation) and Step 35 (re-render). Includes trigger condition, instruction body, 5 verbatim anchor cases, output contract, anti-patterns, downstream pointer.
- `.claude/skills/google-ad-research/SKILL.md` — 1-line edit; Phase 8 pointer parenthetical extended from "(Steps 31-35)" to mention "Step 34a LLM re-tag for POS-06 positives sync". Final line count: 495/500 (5 lines of headroom).

## Decisions Made

- **Step 34a placement in references/, not SKILL.md.** SKILL.md was at 494/500 lines before this plan — no budget for a new top-level Phase 14 section. The perf_synth.py invocation that produces positives-sync.json already lives in Step 34 of the Phase 8 sub-flow, so 34a is the natural insertion point. Mirrors Phase 5/7/8/9/10/11 precedent (rubric in references, single-line pointer in SKILL.md).
- **5 anchor cases verbatim from 14-CONTEXT.md.** Token reorder, match-type drift, semantic synonym, narrowing opportunity, locale variant — same examples flow from 14-CONTEXT.md → references rubric → SKILL.md pointer. One source of truth eliminates drift between docs.
- **Output contract forbids bucket-name invention.** LLM may only re-distribute entries between the 4 fixed buckets; new bucket names like "maybe_active" would break downstream renderers and CSV filter. retag_reason field appended for operator audit.
- **No post-retag re-render in plan scope.** Step 34a downstream pointer instructs operator (or future automation) to re-invoke render_report.py + export_csv.py AFTER the LLM re-tag step. Live e2e verification ran pre-retag; post-retag verification is naturally exercised on the next real operator session.

## Deviations from Plan

None — plan executed exactly as written. Tasks 1 + 2 landed in single commits each; Task 3 was a human-verify checkpoint that returned approved after operator ran the skill on a real account.

## Issues Encountered

None during execution. The human-verify checkpoint paused for operator verification on a live account; operator returned with "approved" after confirming all 7 POS checkpoints on the Lake Worth car-accident/urgent-care brief.

## Live Verification Evidence (Task 3 — human-verify)

Operator ran the skill end-to-end on a real Google Ads account (Lake Worth, FL car-accident / urgent-care brief). Verified all 7 POS checkpoints:

- **POS-01:** `raw/google-ads-keywords.json` produced by perf_fetch.py — confirmed.
- **POS-02:** `positives-sync.json` written with 4 buckets + stats. Stats counts sum to our_total (11 + 0 + 8 + 64 = 83 = our_total). Confirmed:
  - `our_total: 83`
  - `already_active: 11`
  - `paused_in_account: 0` (legitimate — no paused kw in this account)
  - `covered_by_broad: 8`
  - `new_to_add: 64`
- **POS-03:** `report.md` contains `## Positives Sync` section with stats line + enumerated new_to_add list + count-only audit buckets — visual check passed.
- **POS-04:** `export/positives.csv` row count matches stats.new_to_add. Verified `wc -l positives.csv` = 65 (64 rows + 1 header line). All 4 buckets non-empty except paused_in_account (legitimate-empty for this account).
- **POS-04 (--include-existing):** Confirmed via Plan 14-04 test suite; not re-exercised on live run (deferred to next real operator session).
- **POS-05 (graceful skip):** Already verified in Plan 14-02 / 14-03 / 14-04 unit tests against absent-sidecar fixtures; not re-exercised on live run.
- **POS-06:** SKILL.md Step 34a pointer + references/phase8-account-data.md Step 34a rubric present and operator-readable. LLM re-tag invocation deferred to next real operator session (not blocking — script-only output already operator-actionable on this run).
- **POS-07:** Full test suite green from Plan 14-04 closeout (256 passed, 0 skipped). No regressions introduced by docs-only Plan 14-05.

**Live run path:** `.runs/2026-05-15T125157Z-car-accident-injury-care-services-lake-worth/`

## Next Phase Readiness

- **v1.4 milestone shippable.** All 7 POS requirements (POS-01..07) Complete; live e2e on real account confirms operator-facing UX. Manual dedup pain eliminated: `positives.csv` ships only net-new keywords by default; `--include-existing` flag preserves backward compat.
- **Phase 14 ready for verification gate.** Orchestrator should run gsd-verifier next; on green, `phase complete` closes v1.4.
- **Phase 13 (Landing-Page Extract Vendor Swap) remains parked.** Trigger (WebFetch friction) still not met post-Phase-14. Stays in BACKLOG.
- **LLM re-tag pattern replicable.** Future sidecars needing semantic-dupe polish (or any LLM refinement on top of script output) can follow the Step 34a shape: trigger / instruction / anchor cases / output contract / anti-patterns / downstream pointer.

---

## Self-Check: PASSED

Verified file presence and commit hashes:

- `.planning/phases/14-positives-sync/14-05-SUMMARY.md` — FOUND (this file)
- `.claude/skills/google-ad-research/references/phase8-account-data.md` Step 34a — FOUND (commit `8983c68` shows +49 lines)
- `.claude/skills/google-ad-research/SKILL.md` Phase 8 pointer edit — FOUND (commit `f7e80ef` shows 1-line edit)
- Live run `.runs/2026-05-15T125157Z-car-accident-injury-care-services-lake-worth/positives-sync.json` — FOUND (stats verified: our_total=83, already_active=11, paused=0, covered_by_broad=8, new_to_add=64)
- Live run `.runs/2026-05-15T125157Z-car-accident-injury-care-services-lake-worth/export/positives.csv` — FOUND (65 lines = 64 rows + header, matches stats.new_to_add)
- Commit `8983c68` (Task 1) — FOUND in git log
- Commit `f7e80ef` (Task 2) — FOUND in git log

---
*Phase: 14-positives-sync*
*Completed: 2026-05-15*
