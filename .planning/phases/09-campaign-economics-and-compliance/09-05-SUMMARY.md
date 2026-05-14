---
phase: 09-campaign-economics-and-compliance
plan: 05
subsystem: skill-workflow
tags: [skill-md, reference-rubric, operator-workflow, phase9-wiring, smoke-test]

# Dependency graph
requires:
  - phase: 09-01
    provides: bid_suggest.py CLI (Suggested Max CPC enrichment)
  - phase: 09-02
    provides: forecast_budget.py CLI (forecast.json sidecar + methodology block)
  - phase: 09-03
    provides: compliance_check.py CLI (compliance-flags.json sidecar)
  - phase: 09-04
    provides: render_report.py extension (Suggested CPC column, Budget Forecast section, ⚠ Compliance block, report.json forecast+compliance keys)
provides:
  - SKILL.md Phase 9 pointer (Steps 36-40) following the Phase 5/7/8 reference-load pattern
  - references/phase9-economics-compliance.md (209-line rubric — prerequisites, four uv-run invocations, exit codes, anti-patterns, failure modes, Phase 10 downstream contract)
  - End-to-end smoke verification on `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/` confirming all Phase 9 outputs render correctly
affects: [phase-10-operator-launch-kit]

# Tech tracking
tech-stack:
  added: []  # no new dependencies — pure documentation + smoke
  patterns:
    - "Phase 5/7/8 reference-load pointer pattern extended to Phase 9 (explicit 'Load it with the Read tool when entering Phase 9' instruction)"
    - "SKILL.md ≤500-line cap honored by extracting full step rubric to references/ — pointer-only inside SKILL.md"
    - "Reference file documents the Phase 10 downstream contract upfront so the Phase 10 planner has an upstream specification to read"

key-files:
  created:
    - .claude/skills/google-ad-research/references/phase9-economics-compliance.md
  modified:
    - .claude/skills/google-ad-research/SKILL.md

key-decisions:
  - "Phase 9 pointer placed after Phase 8 pointer with `---` separator — keeps the optional-sidecar pattern (Phases 7, 8) visually distinct from the v1.0 sequential workflow (Phases 1-6)"
  - "Phase 9 pointer paragraph explicitly calls out 'mandatory for Phase 10 (Operator Launch Kit)' — disambiguates 'optional in v1.0' vs 'required for v1.1 launch kit' so operators don't skip and then discover Phase 10 won't run"
  - "Smoke verification reused the existing Phase 8 run-folder `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/` (medical vertical) rather than building a fresh fixture-driven folder — gave a realistic compliance-block trigger and exercised real Ahrefs cpc_micros data"
  - "Cosmetic float-formatting nit on `Daily Clicks` column (raw floats like `0.44000000000000006` rendering in report.md) noted for follow-up but explicitly NOT blocking — render_report.py formatting tweak is a Phase 10 / cleanup-plan candidate, not a Phase 9 regression"

patterns-established:
  - "Pointer-only SKILL.md sections for optional/late-phase workflows (Phases 5, 7, 8, 9) — full rubric lives in references/, SKILL.md stays under the 500-line cap"
  - "Reference files document the downstream contract (what the next phase reads) as a dedicated section — Phase 10 planner reads Phase 9's reference to discover suggested_max_cpc_micros, forecast.campaign_totals.daily_spend_mid_usd, and matched_verticals[].verification_url upfront"

requirements-completed: [BIDS-03, FRCS-04, FRCS-05, CMPL-03]

# Metrics
duration: ~12min
completed: 2026-05-14
---

# Phase 9 Plan 05: SKILL Wiring + End-to-End Smoke Summary

**Phase 9 pointer added to SKILL.md (497 lines, under 500-cap), 209-line `references/phase9-economics-compliance.md` rubric created mirroring the Phase 5/7/8 pattern, and full end-to-end smoke approved on a real run-folder with all 6 visual checks green and 56/56 Phase 9 tests + 0 v1.0 regressions.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-14T18:30:00Z (approx — Task 1 commit dd94a8b)
- **Completed:** 2026-05-14T18:43:14Z
- **Tasks:** 3/3 (1 reference file + 1 SKILL pointer + 1 human-verify checkpoint)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- **Phase 9 reference rubric shipped** at `.claude/skills/google-ad-research/references/phase9-economics-compliance.md` (209 lines). Mirrors `phase8-account-data.md` structure verbatim: When-to-run, Prerequisites, Step 36 (operator confirm), Step 37 (`bid_suggest.py`), Step 38 (`forecast_budget.py`), Step 39 (`compliance_check.py`), Step 40 (re-render report), Anti-patterns (5), Failure modes (5), Downstream contract for Phase 10 (4 explicit join points).
- **SKILL.md Phase 9 pointer wired in** at lines 495-497 (file now 497 lines / 498 with trailing newline — well under the 500-line cap). Pointer follows the Phase 5/7/8 explicit-load pattern ("Load it with the Read tool when entering Phase 9") and explicitly calls out the optional-in-v1.0 / mandatory-for-Phase-10 dual contract.
- **End-to-end smoke approved** against `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/`. All 6 visual + suite checks green:
  - `bid_suggest`: 73 rows enriched (26 direct cpc, 32 cluster-median fallback, 15 null+flagged `no_cpc_data`)
  - `forecast_budget`: 14 clusters forecast, `daily_spend_mid_usd = 66.65`, monthly mid = `$1999.50`
  - `compliance_check`: 2 matched verticals (legal + medical — expected on an urgent-care/car-accident brief)
  - `report.md`: ⚠ Compliance Required block at line 18, Budget Forecast section at line 402, "How this is calculated" subsection at line 425, Suggested CPC column populated in the Ranked Keywords table
  - `report.json`: top-level `forecast` object + `compliance` array both populated
  - Full pytest suite: **56/56 Phase 9 tests GREEN, 0 v1.0 regressions** (149 v1.0 + 56 v1.1 = 205 passed, 10 skipped)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create `references/phase9-economics-compliance.md` (Steps 36-40 rubric)** — `dd94a8b` (feat)
2. **Task 2: Add Phase 9 pointer to SKILL.md (≤500 lines)** — `24dd777` (feat)
3. **Task 3: End-to-end Phase 9 smoke on real run-folder** — checkpoint:human-verify, operator-approved (no new commit; smoke against existing artifacts)

**Plan metadata (this commit):** `docs(09-05): close plan 09-05 (SKILL wiring + smoke approved)`

## Files Created/Modified

- `.claude/skills/google-ad-research/references/phase9-economics-compliance.md` — NEW 209-line rubric covering Steps 36-40, anti-patterns, failure modes, and Phase 10 downstream contract
- `.claude/skills/google-ad-research/SKILL.md` — modified: 491 → 497 lines; Phase 9 pointer appended after Phase 8 with `---` separator

## Decisions Made

- **Pointer style mirrors Phase 5/7/8 verbatim.** Pointer paragraph names: the reference file, the explicit `Read tool` load instruction, the "optional in v1.0 / mandatory for Phase 10" disambiguation, the no-API-cost note, the Phase 8 dependency (`ranked-enriched.json` with `cpc_micros`), and the three produced artifacts (additive mutation of `ranked-enriched.json` + two new sidecars).
- **Reference file structure mirrors `phase8-account-data.md`.** Sections in order: header (3-paragraph intro) → When to run → Prerequisites → Step 36 → Step 37 → Step 38 → Step 39 → Step 40 → Anti-patterns → Failure modes → Downstream contract (read by Phase 10). The downstream-contract section is the key Phase 10 input — it names 4 specific join points (`suggested_max_cpc_micros`, `campaign_totals.daily_spend_mid_usd`, `matched_verticals[].verification_url`, `report.json["forecast"]/["compliance"]`) so the Phase 10 planner reads the upstream API contract before designing.
- **Smoke run-folder selection:** reused `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/` (real Phase 8 output, medical+legal vertical) rather than a fresh fixture-built folder. Real Ahrefs `cpc_micros` data exercises the direct-cpc + cluster-median fallback + no_cpc_data paths simultaneously; medical+legal brief triggers the compliance block naturally.

## Deviations from Plan

None — plan executed exactly as written. Task 1 and Task 2 verification scripts both passed; the human-verify checkpoint at Task 3 was approved on first pass with no fix-up required.

---

**Total deviations:** 0
**Impact on plan:** Clean run. Reference-file pattern is now established across 4 phases (5, 7, 8, 9), reusable for Phase 10's eventual SKILL.md pointer.

## Issues Encountered

**Cosmetic float-formatting nit (non-blocking, deferred):**
- `report.md` Budget Forecast table renders raw Python floats in the `Daily Clicks` column (e.g., `0.44000000000000006` instead of `0.4`).
- Caused by `render_report.py` directly stringifying the float from `forecast.json` per-cluster `daily_clicks_mid` field.
- Confirmed cosmetic only — JSON contract is correct (the float is the precise compute result), `daily_spend_*` USD columns format correctly via `_micros_to_usd`, and HTML report would benefit from the same formatting tweak.
- **Logged for follow-up**, not blocking Phase 9 closeout. Candidate fix locations: `render_report.py` `render_forecast_section` helper (apply `f"{val:.1f}"` to the daily-clicks columns), OR `forecast_budget.py` round-half-up to 1 decimal at write time. The latter would also clean stdout summaries.

## User Setup Required

None — Phase 9 reads no secrets, makes zero API calls, and adds no new `.env` keys.

## Next Phase Readiness

**Phase 9 is now operator-runnable end-to-end via the skill workflow.** An operator can:
1. Trigger the skill in Claude Code → reach Step 35 (Phase 8 done) → see the Phase 9 pointer in SKILL.md.
2. Load `references/phase9-economics-compliance.md` via Read.
3. Run the four `uv run` invocations against any v1.0 + Phase 8 run-folder.
4. See Suggested Max CPC, Budget Forecast, and ⚠ Compliance Required all surface in `report.md` / `report.html` / `report.json`.

**Phase 10 planner has a documented upstream contract** in `phase9-economics-compliance.md` — `suggested_max_cpc_micros` (BIDS-03), `forecast.campaign_totals.daily_spend_mid_usd` (FRCS-04), `matched_verticals[].verification_url` (CMPL-05), `report.json["forecast"]` + `["compliance"]` (CMPL-04). Phase 10 (`/gsd:plan-phase 10`) can now be planned.

**Phase 9 remaining work before close:**
- CMPL-05 (Next-Steps checklist reordering on compliance match) is mapped to Phase 10, not Phase 9 — Phase 10 STEP-01 reads `compliance-flags.json` and reorders the checklist. Tracking row in REQUIREMENTS.md left at "Pending — Phase 10".

---
*Phase: 09-campaign-economics-and-compliance*
*Completed: 2026-05-14*

## Self-Check: PASSED

- FOUND: `.claude/skills/google-ad-research/references/phase9-economics-compliance.md` (209 lines)
- FOUND: `.claude/skills/google-ad-research/SKILL.md` (497 lines, under 500-cap)
- FOUND: `.planning/phases/09-campaign-economics-and-compliance/09-05-SUMMARY.md`
- FOUND: commit `dd94a8b` (Task 1 — reference file)
- FOUND: commit `24dd777` (Task 2 — SKILL.md pointer)
- Task 3 was a human-verify checkpoint (no commit expected) — operator-approved.
