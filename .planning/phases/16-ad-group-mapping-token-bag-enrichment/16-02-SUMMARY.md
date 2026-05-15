---
phase: 16-ad-group-mapping-token-bag-enrichment
plan: 02
subsystem: ad-group-match
tags: [phase16, calibration-docs, live-e2e, lake-worth, oauth-account, reference-doc, adgm-10, adgm-11-deferred]

requires:
  - phase: 16-ad-group-mapping-token-bag-enrichment
    plan: "01"
    provides: _build_ag_token_bag + keywords-aware index + per-source reason attribution + _THRESHOLDS locked at {0.30, 0.10} (loosening-cap floor) + xfail-with-rationale on Lake Worth coverage floor
  - phase: 11-account-structure-mapping
    provides: references/phase11-account-structure-mapping.md (progressive-disclosure target; existing SKILL.md pointer carries new Phase 16 section without SKILL.md edit)

provides:
  - "`references/phase11-account-structure-mapping.md` extended with `## Phase 16 Token-Bag Enrichment (ADGM-07..11)` section: why-it-exists narrative + bag composition ASCII diagram + per-source reason attribution table + threshold calibration table (Phase 11 0.7/0.4 -> Phase 16 0.30/0.10 with rationale) + backward-compat contract + open-question carry-forward"
  - "Live e2e verification on real Lake Worth OAuth account — observed mapping_coverage_pct = 16.42% (within 0.25pp of the offline golden 16.67%), confirming Phase 16 enrichment wires end-to-end with no regression from the pre-enrichment 0% baseline and that the structural Jaccard ceiling holds against real-account data (not a fixture artifact)"
  - "ADGM-10 (threshold rationale auditable) closed — operator reading one reference file can re-derive the {0.30, 0.10} calibration"
  - "ADGM-11 (>=50% Lake Worth floor) reaffirmed as deferred — structural-fix follow-up plan needed (candidates already named in 16-01 xfail rationale)"

affects: structural-fix follow-up plan (per-source max-jaccard / token-bag subsampling / asymmetric similarity) + next-account calibration cycle once a 2nd OAuth-enabled real account ships

tech-stack:
  added: []
  patterns:
    - "Reference-doc-as-calibration-record: empirical threshold derivations (before/after numbers + observed coverage on real account) live in `references/phase11-account-structure-mapping.md` not in code comments — operator-tunable knob remains auditable without a code diff"
    - "Live-e2e-closeout-as-checkpoint: a phase that lands behind an offline goldenfile (16.67% offline) must verify the goldenfile is not a fixture-artifact by running the skill end-to-end against the real OAuth account; 16.42% vs 16.67% (0.25pp delta) confirms predictive validity"

key-files:
  created:
    - .planning/phases/16-ad-group-mapping-token-bag-enrichment/16-02-SUMMARY.md
  modified:
    - .claude/skills/google-ad-research/references/phase11-account-structure-mapping.md

key-decisions:
  - "Reference-doc edits are the ONLY artifact change for ADGM-10 — SKILL.md untouched (stays at 497/500 lines). Existing Phase 11 progressive-disclosure pointer in SKILL.md carries the new section on-demand; no global rule load needed"
  - "Live e2e 16.42% (vs offline 16.67%) accepted as predictive-validity confirmation despite ADGM-11 floor miss — the live result rules out fixture overfit and confirms the structural ceiling holds on real OAuth data; the gap is real, not a goldenfile artifact"
  - "ADGM-11 deferral carried forward to next planning cycle as a structural-algorithm follow-up plan (per-source max-jaccard / token-bag subsampling / asymmetric similarity), NOT as a re-threshold attempt — 16-01's calibration sweep already exhausted the loosening cap"

patterns-established:
  - "Operator-verifiable live closeout: when an offline calibration lands behind its floor with an option-a deferral, the follow-up closeout plan should still produce a live-e2e checkpoint to confirm (a) no regression vs pre-change baseline and (b) the offline goldenfile predicts real-account behavior — this gives the deferred-fix planner ground-truth intel, not just fixture intel"

requirements-completed: [ADGM-10]

duration: ~25min (Task 1 docs ~10min in prior executor session + Task 2 live e2e operator wall-time ~15min)
completed: 2026-05-15
---

# Phase 16 Plan 02: Calibration Documentation + Live E2E Closeout Summary

**ADGM-10 threshold rationale shipped to `references/phase11-account-structure-mapping.md` (+78 lines, SKILL.md untouched at 497/500); live e2e on real Lake Worth OAuth account confirms 16.42% mapping coverage (vs offline 16.67% golden — within 0.25pp), validating Phase 16 enrichment wires end-to-end and the Jaccard ceiling is structural, not a fixture artifact; ADGM-11 floor remains deferred to a structural-algorithm follow-up plan.**

## Performance

- **Duration:** ~25 min (Task 1 docs ~10min + Task 2 live operator e2e ~15min wall-time)
- **Started:** 2026-05-15
- **Completed:** 2026-05-15
- **Tasks:** 2 (Task 2 = human-verify checkpoint on live OAuth account)
- **Files created:** 1 (this SUMMARY)
- **Files modified:** 1 (`references/phase11-account-structure-mapping.md`)

## Accomplishments

- **`references/phase11-account-structure-mapping.md` gains `## Phase 16 Token-Bag Enrichment (ADGM-07..11)` section** carrying: why-Phase-16-exists paragraph (Lake Worth dogfood 0% pre-enrichment), bag composition ASCII diagram (`name ∪ kw.text ∪ top-10 search_terms`), per-source reason-field attribution table, threshold calibration table (Phase 11 `0.7/0.4` → Phase 16 `0.30/0.10`), backward-compat contract for pre-Phase-14 accounts, and open-question carry-forward for next-account calibration.
- **+78 lines added** (well under the 100-line scannability cap in the plan).
- **SKILL.md untouched at 497/500 lines** — existing Phase 11 progressive-disclosure pointer carries the new content on demand. No SKILL.md edit needed for ADGM-10.
- **Live e2e on real Lake Worth OAuth account** completed: run dir `.runs/2026-05-15T180642Z-car-accident-injury-care-services/` — `mapping_coverage_pct = 16.42%` (operator-verified, file inspected).
- **Predictive-validity confirmation:** offline goldenfile predicted 16.67%; live observed 16.42%; 0.25pp delta confirms the Lake Worth goldenfile fixture is NOT overfit — the structural Jaccard ceiling holds against real-account data.
- **Test suite reaffirmed green:** 18 passed + 1 xfailed (per 16-01 lock state).

## Task Commits

1. **Task 1: Extend phase11-account-structure-mapping.md with Phase 16 calibration rationale** — `e7492c7` (docs)
2. **Task 2: Live e2e closeout — operator-verified on real Lake Worth OAuth account** — no code/test artifacts; verification-only (operator approved with 16.42% observed)

**Plan metadata:** _this commit_ (docs: complete plan)

## Live E2E Results

**Run folder:** `.runs/2026-05-15T180642Z-car-accident-injury-care-services/`

**Brief:** car accident / urgent care PIP services, Lake Worth FL (matches plan `<how-to-verify>` step 1 fields)

**Coverage:**

| Metric | Offline golden (16-01) | Live OAuth account | Delta |
|---|---|---|---|
| `mapping_coverage_pct` | 16.67% (11 medium / 66 ranked) | **16.42%** | -0.25pp |

**Match distribution (live):** 0 high / 11 medium / 56 low. Same shape as offline golden (zero high, single-digit-tens medium, remainder low) — confirms the locked `_THRESHOLDS = {0.30, 0.10}` interact with real OAuth data the same way they interact with the goldenfile fixture.

**Reason-field format verified (live sample):**
```
jaccard=0.10 (name=0.33 kw-criterion=0.00 search-term=0.00) intent_match=True
```
Per-source attribution renders correctly. Note: on this particular sample the score is driven entirely by AG-name overlap; `kw-criterion=0.00` and `search-term=0.00` reinforce the structural-ceiling story from 16-01 — full-union Jaccard is bag-vs-query asymmetric.

**Sample match observed:** `keyword="urgent care lake worth"` classified `medium`, score driven by name overlap alone (kw-criterion + search-term contributions zero). This is exactly the failure mode the 16-01 sweep table predicted at the locked floor — meaningful matches happen, but only through one source at a time, capping the full-union Jaccard below 0.30 (the high threshold).

**Test suite state:** `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/ -x` reaffirmed green at 18 passed + 1 xfailed (per 16-01 locked state). No regressions outside Phase 16 scope.

## Phase 16 Requirements Status After This Plan

- **ADGM-07** ✅ Complete (16-01) — token-bag union shipped
- **ADGM-08** ✅ Complete (16-01) — graceful absence of `raw/google-ads-keywords.json` preserved
- **ADGM-09** ✅ Complete (16-01) — per-source reason field renders (verified live above)
- **ADGM-10** ✅ Complete (16-02) — calibration rationale auditable in `references/phase11-account-structure-mapping.md`; operator can re-derive {0.30, 0.10} from one file
- **ADGM-11** ⏸ Deferred to structural-fix follow-up — live e2e reaffirms the 16.42% observed gap vs 50% floor is structural (Jaccard bag-vs-query asymmetry), not a calibration miss. Candidate fixes already named in 16-01 xfail rationale: per-source max-jaccard, token-bag subsampling, or asymmetric similarity (e.g. `|A ∩ B| / |A|`).

## Decisions Made

- **SKILL.md NOT edited:** Plan's must-have explicitly required SKILL.md ≤500 preserved. Reference-doc edits route through the existing Phase 11 progressive-disclosure pointer in SKILL.md — operator opening the reference doc gets the Phase 16 section on demand. Zero SKILL.md surface change.
- **Accepted 16.42% live result as closeout despite ADGM-11 miss:** Plan 16-01's option-a deferral already acknowledged the floor miss; this plan's live e2e was a predictive-validity check, NOT a re-attempt at hitting 50%. The 0.25pp delta between offline (16.67%) and live (16.42%) confirms the goldenfile predicts real behavior — that's the success condition Plan 16-02 actually needed to verify before handing ADGM-11 off to a structural follow-up.
- **Carried ADGM-11 forward as a structural-algorithm open question (not a re-calibration open question):** The 16-01 sweep already exhausted the loosening cap. The follow-up plan needs to change the algorithm shape, not retry threshold values. Documenting this distinction in STATE.md prevents a future planner from re-running the calibration loop.

## Deviations from Plan

None — plan executed exactly as written.

Task 1 was performed by a prior executor session (commit `e7492c7`, +78 lines vs the plan's 100-line cap). Task 2 was an operator-driven human-verify checkpoint; the operator returned with `approved 16.42%` resume signal carrying the observed coverage and a sample reason-field snippet. This closeout summary records the results — no code or test artifacts produced beyond docs.

## Issues Encountered

None during this plan's execution. The ADGM-11 floor miss observed during Task 2 (16.42% < 50%) is plan-anticipated per 16-01's option-a deferral — it is documented as a deferred follow-up, not a new issue.

## User Setup Required

None — no external service configuration required. Live e2e uses the existing Lake Worth OAuth wiring from Phase 8 + Phase 14; no new env vars or dashboard steps.

## Next Plan Readiness

The structural-algorithm follow-up plan (currently un-numbered; will be authored next planning cycle) inherits:

1. **Confirmed real-account baseline:** 16.42% live coverage on Lake Worth — predictive-validity-verified, not a fixture artifact.
2. **Auditable threshold rationale doc:** `references/phase11-account-structure-mapping.md` Phase 16 section gives the next planner a single-file read for "why the current thresholds exist + what evidence supports them."
3. **Named candidate fixes** (carried from 16-01 xfail rationale + reaffirmed by live e2e observation that meaningful matches happen one-source-at-a-time):
   - **per-source max-jaccard** (replace full-union Jaccard with `max(jaccard_name, jaccard_kw, jaccard_st)` — directly addresses the live-observed `0.33 / 0.00 / 0.00` failure mode where one strong source carries the match but full-union dilutes it)
   - **token-bag subsampling** (cap AG bag at top-K most informative tokens to fix bag-vs-query asymmetry)
   - **asymmetric similarity** (`|A ∩ B| / |A|` where A = query — overlap-relative-to-query, ignoring bag size)
4. **Sweep table from 16-01** documenting the threshold-pair search exhaustion — saves the next planner from re-running calibration loops.
5. **Open question for STATE.md:** next-account calibration target (Lake Worth + 1 more real OAuth account) to lock thresholds after structural fix lands.

No blockers. Phase 16 is complete pending the structural follow-up plan.

## Self-Check: PASSED

- `.claude/skills/google-ad-research/references/phase11-account-structure-mapping.md` — FOUND (modified; `Phase 16 Token-Bag Enrichment` section present)
- `.planning/phases/16-ad-group-mapping-token-bag-enrichment/16-02-SUMMARY.md` — FOUND (this file)
- `.runs/2026-05-15T180642Z-car-accident-injury-care-services/ad-group-mapping.json` — FOUND (`mapping_coverage_pct: 16.42` confirmed via grep)
- Commit `e7492c7` — FOUND in git log (Task 1 reference-doc extension)
- SKILL.md line count: 497/500 — confirmed via `wc -l` (≤500 invariant preserved)
- Live e2e pytest state: 18 passed + 1 xfailed — operator-confirmed (no regression vs 16-01 lock)

---
*Phase: 16-ad-group-mapping-token-bag-enrichment*
*Completed: 2026-05-15*
