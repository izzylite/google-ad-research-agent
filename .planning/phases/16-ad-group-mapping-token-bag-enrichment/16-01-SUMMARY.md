---
phase: 16-ad-group-mapping-token-bag-enrichment
plan: 01
subsystem: ad-group-match
tags: [phase16, token-bag-enrichment, calibration, jaccard, lake-worth-golden, option-a-deferral]

requires:
  - phase: 16-ad-group-mapping-token-bag-enrichment
    plan: "00"
    provides: 5 Lake Worth golden fixtures + 5 RED tests + PHASE16_INCOMPLETE guard
  - phase: 14-positives-sync
    provides: raw/google-ads-keywords.json (kw_criteria per AG) — token-bag input
  - phase: 11-account-structure-mapping
    provides: ad_group_match.py public surface (build_mapping, _build_ad_group_index, _classify, _tokens, _jaccard, _THRESHOLDS)

provides:
  - _build_ag_token_bag(ag_name, kw_criteria, search_terms, top_n_terms=10) helper
  - _build_ad_group_index keywords-aware rewrite (3-source per-AG token bag)
  - build_mapping + main_with_args keywords pass-through (ADGM-08 graceful absence)
  - match.reason per-source attribution: `jaccard=X.XX (name=Y.YY kw-criterion=Z.ZZ search-term=W.WW) intent_match=B`
  - _THRESHOLDS recalibration {0.70/0.40} -> {0.30/0.10} (loosening-cap floor)

affects: 16-02 (gap-closure plan inherits ADGM-11 follow-up — close 16.67% -> >=50% Lake Worth coverage via structural algorithm change)

tech-stack:
  added: []
  patterns:
    - "Calibration protocol with HARD constraints (C1 floor, C2 80% invariant, C3 fallback ceiling, C4 sentinels, C5 garbage-low) + operator-gated checkpoint when constraint set is infeasible"
    - "Per-source partial Jaccards stored in ad-group index for reason-field attribution (zero extra Jaccard recomputation)"
    - "@pytest.mark.xfail(strict=True) with rationale docstring referencing follow-up plan ID — preserves test intent + signals operator-acknowledged deferral without test deletion"

key-files:
  created:
    - .planning/phases/16-ad-group-mapping-token-bag-enrichment/16-01-SUMMARY.md
  modified:
    - .claude/skills/google-ad-research/scripts/ad_group_match.py
    - .claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py

key-decisions:
  - "Operator chose option-a (accept Lake Worth coverage miss, defer ADGM-11 floor to plan 16-02) over option-b (edit Phase 11 test) or option-c (loosen cap below 0.30/0.10 — would break C5 garbage-keyword guard)"
  - "Locked _THRESHOLDS at the calibration_protocol loosening-cap FLOOR {high: 0.30, medium: 0.10} — best Lake Worth coverage achievable while preserving Phase 11 80% invariant + C5 garbage-low classification"
  - "Root cause of Lake Worth miss is STRUCTURAL not threshold-tuning: 34-token enriched AG bag vs typical 4-6-token ranked queries caps observed jaccard at 0.15-0.25; no {high, medium} pair within the loosening cap (high>=0.30, medium>=0.10) can lift coverage to 50% without breaking C5"
  - "test_reason_field_per_source_attribution left GREEN (not xfail'd) — at locked thresholds 11 medium matches exist on Lake Worth providing reason-field samples; test asserts on reason-field format-when-matched, NOT on Lake Worth match count itself"
  - "xfail rationale string explicitly names plan 16-02 + the structural fix candidates (per-source max-jaccard instead of full-union jaccard, OR token-bag subsampling) — gives plan 16-02 planner a clean handoff"

patterns-established:
  - "Calibration deviation handling: when calibration_protocol terminal state B is reached, lock at cap-floor + xfail-with-rationale (not delete the test) + create follow-up plan; preserves traceability and intent"
  - "Per-source attribution in reason field via partial sets stored once in index dict — pattern reusable for any future multi-source similarity scoring"

requirements-completed: [ADGM-07, ADGM-08, ADGM-09, ADGM-10]

duration: ~18min (across two executor sessions including operator checkpoint resolution)
completed: 2026-05-15
---

# Phase 16 Plan 01: Token-Bag Enrichment + Option-A Deferral Summary

**Token-bag enrichment shipped (name ∪ kw_criteria ∪ top-10 search-terms) with per-source reason attribution + recalibrated thresholds at loosening-cap floor; Lake Worth coverage observed at 16.67% — operator chose option-a deferral of ADGM-11 floor (>=50%) to plan 16-02 follow-up.**

## Performance

- **Duration:** ~18 min (Tasks 1-3 first executor ~13min + Task 4 resumption ~5min)
- **Started:** 2026-05-15
- **Completed:** 2026-05-15
- **Tasks:** 4 (Task 4 = operator-gated decision checkpoint)
- **Files created:** 1 (this SUMMARY)
- **Files modified:** 2 (ad_group_match.py + test_ad_group_match.py)

## Accomplishments

- **`_build_ag_token_bag(ag_name, kw_criteria, search_terms, top_n_terms=10)`** shipped per plan contract: returns frozenset = name_tokens ∪ kw_criterion_tokens (status != REMOVED) ∪ top-N-search-term-tokens (filtered zero-impression; sorted clicks desc / impressions desc).
- **`_build_ad_group_index` rewired** to accept optional `keywords: dict | None = None` arg + emit partial token sets (`name_tokens`, `criterion_tokens`, `search_term_tokens`) alongside the full-union `token_bag` — partials power the per-source reason field with zero extra Jaccard recomputation.
- **`build_mapping` + `main_with_args` threaded** keywords end-to-end — `main_with_args` loads `raw/google-ads-keywords.json` when present, falls back to `None` with WARN log if absent or unparseable (ADGM-08 graceful degrade preserved).
- **`match.reason` format extended** to `jaccard=X.XX (name=Y.YY kw-criterion=Z.ZZ search-term=W.WW) intent_match=B` on high+medium matches; low matches retain simpler `jaccard=0.00 intent_match=False` shape (no spurious partials against nothing).
- **`_THRESHOLDS` recalibrated** from Phase 11 `{0.70, 0.40}` to `{0.30, 0.10}` — the calibration_protocol loosening-cap FLOOR. ADGM-10 sentinel (high < 0.7 AND medium < 0.4) passes loud.
- **Phase 11 `test_coverage_pct_high_plus_medium_only` invariant PRESERVED** at 80.0% across the threshold delta — zero Phase 11 test edits.
- **Suite: 18 passed + 1 xfailed** — zero unexpected failures.

## Task Commits

1. **Task 1: Implement `_build_ag_token_bag` + rewire `_build_ad_group_index`** — `23c1c02` (feat)
2. **Task 2: Thread keywords through `build_mapping` + `main_with_args` + extend reason field** — `23c1c02` (feat, same commit as Task 1 in first executor session)
3. **Task 3: Recalibrate `_THRESHOLDS` empirically — terminal state B reached** — `23c1c02` (feat, same commit)
4. **Task 4: Apply operator decision option-a — lock thresholds at floor + xfail Lake Worth coverage** — `fbb7372` (fix)

## Calibration Sweep — Threshold-Pair Search

The constrained search exhausted the loosening cap (high>=0.30, medium>=0.10) before reaching Lake Worth's 50% floor. Documented sweep below for plan 16-02 planning context:

| {high, medium} | Lake Worth coverage | Phase 11 coverage | C5 garbage-low | Outcome |
|----------------|---------------------|-------------------|----------------|---------|
| {0.70, 0.40} (Phase 11 baseline) | 0.0% | 80.0% | OK | C1 fails hard |
| {0.45, 0.20} (CONTEXT hypothesis) | 0.0% | 80.0% | OK | C1 still fails — Lake Worth bag-vs-query jaccard ceiling kicks in |
| {0.30, 0.10} (option-a cap floor) | **16.67%** (11 medium / 66 ranked) | 80.0% | OK | **LOCKED** — C1 fails, all other constraints hold |
| {below cap} | (not tested — would break C5) | — | FAIL | Excluded by calibration_protocol cap |

**Per-source Jaccard ranges observed on Lake Worth (11 medium matches against `Accident Exams – Lake Worth` AG bag, useful intel for plan 16-02):**

- name= contribution: 0.04–0.20 (Lake Worth AG name has 4 stopword-filtered tokens — `accident`, `exams`, `lake`, `worth`)
- kw-criterion= contribution: 0.05–0.15 (47 kw_criteria narrow to ~30 distinct tokens once stopwords applied)
- search-term= contribution: 0.05–0.18 (top-10 search terms by clicks contribute ~15 distinct tokens)
- Full-union jaccard (what `build_mapping` actually scores against): 0.10–0.17 — at locked medium=0.10 these all classify medium; lifting them to >=0.30 (high) is structurally impossible given the bag-vs-query token-count asymmetry.

## Decisions Made

- **Option-a deferral over option-b (Phase 11 test edit) or option-c (loosen cap below 0.30/0.10):** Option-b would silently weaken Phase 11's anchor invariant for a Phase 16 problem — wrong layer, wrong direction. Option-c would lower medium below 0.10 and re-classify `"tomato sandwich"` against the medical AG as medium (breaks C5 — algorithm becomes wrong, not just permissive). Option-a accepts the visible miss and creates a clean handoff for a structural fix in plan 16-02.
- **Locked at cap FLOOR (0.30/0.10), not at the lowest pair that satisfied all non-C1 constraints (could have been 0.45/0.20 since both yielded the same 0% Lake Worth at higher thresholds — but at locked floor we get 16.67% not 0%):** Operator preference is to ship the highest achievable Lake Worth coverage that doesn't break anything else — that's the floor, where 11 of the 66 ranked keywords flip from `low` (unmapped) to `medium`. This is real signal the operator can review even if the floor goal slips.
- **xfail with `strict=True` and detailed rationale, not test deletion:** Preserves the assertion intent and the wired test infrastructure. Plan 16-02 just removes the `@pytest.mark.xfail` marker once the structural fix lifts coverage past 50%. If we ever accidentally hit >=50% with the current algorithm, `strict=True` flips the test to XPASS-fail and forces a re-evaluation — protects against silent over-fitting.
- **`test_reason_field_per_source_attribution` stays GREEN (not xfail'd):** Read the test — it asserts the reason-format-when-matched contract (`"name=" in sample`, `"kw-criterion=" in sample`, `"search-term=" in sample`) using `high_med = [m for m in out["matches"] if m["confidence"] in ("high", "medium")]`. At locked thresholds 11 medium matches exist on Lake Worth — the test gets its samples and passes. Test is NOT directly downstream of the 50% floor; it's downstream of "at least one high+medium match exists", which the locked floor satisfies (11 > 0).

## Deviations from Plan

### Plan-Anticipated Deviation (resolved via checkpoint)

**Task 4 checkpoint:decision triggered as planned.** Plan's `<calibration_protocol>` step 5 explicitly anticipated terminal state B (constraint set infeasible within loosening cap) and routed through operator-gated Task 4. Operator chose option-a per `<resume-signal>` contract. This is plan-anticipated flow control, not an unplanned deviation.

### Auto-fixed Issues

None during this plan. All structural code changes flowed through the plan's `<interfaces>` block and TDD verify gates. The Lake Worth coverage gap is a calibration-data finding (operator-gated), not an auto-fix item.

## Issues Encountered

- **Lake Worth coverage gap is structural, not threshold-tunable.** Discovered during Task 3 sweep: at the planner's starting hypothesis {0.45, 0.20} Lake Worth coverage was 0.0% — every {high, medium} pair within the loosening cap that preserved C2 (Phase 11 80%) also failed C1 (Lake Worth >=50%). Pre-mortem cause: the planner's empirical-calibration intuition assumed token-bag enrichment would lift jaccard distributions toward 0.5+ on real data, but the Lake Worth enriched bag has 34 distinct tokens (post-stopwords) against ranked queries averaging 4-6 tokens — the jaccard denominator (|A ∪ B|) dominates, capping observed scores at ~0.15-0.25. Resolution: option-a deferral + plan 16-02 structural follow-up (candidates: per-source max-jaccard, token-bag subsampling, or asymmetric similarity).

## Phase 16 Status After This Plan

- **ADGM-07** ✅ Complete — verified by `test_token_bag_unions_all_three_sources` PASSED
- **ADGM-08** ✅ Complete — verified by `test_backward_compat_keywords_absent` PASSED (16.67% with keywords vs <=30% without — gracefully degrades)
- **ADGM-09** ✅ Complete — verified by `test_reason_field_per_source_attribution` PASSED
- **ADGM-10** ✅ Complete — verified by `test_thresholds_recalibrated_below_phase11` PASSED ({0.30, 0.10} both below {0.7, 0.4})
- **ADGM-11** ⏸ Deferred to plan 16-02 — observed 16.67% < 50% floor; structural Jaccard ceiling rationale documented; operator-acknowledged miss via option-a

## Next Plan Readiness

Plan 16-02 (gap closure / ADGM-11 follow-up) inherits:

1. A working token-bag enrichment pipeline (no code regression).
2. Locked baseline thresholds {0.30, 0.10} — the structural fix should NOT need to move these.
3. An `@pytest.mark.xfail(strict=True)` test (`test_lake_worth_coverage_floor`) ready to flip GREEN once coverage clears 50% — remove the marker.
4. Sweep table above documenting the threshold-pair search exhaustion.
5. Per-source Jaccard ranges (name 0.04-0.20, kw-criterion 0.05-0.15, search-term 0.05-0.18) giving the planner concrete intel for the structural-fix candidate evaluation.
6. Three named candidate fixes in the xfail rationale: per-source max-jaccard instead of full-union jaccard, token-bag subsampling, asymmetric similarity (e.g. |A ∩ B| / |A|).

No blockers. Plan 16-02 can be authored next.

## Self-Check: PASSED

- `.claude/skills/google-ad-research/scripts/ad_group_match.py` — FOUND (modified, `_THRESHOLDS` locked at {0.30, 0.10}; `_build_ag_token_bag` exposed at module level)
- `.claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py` — FOUND (modified, `test_lake_worth_coverage_floor` carries `@pytest.mark.xfail(strict=True)` with ADGM-11 -> 16-02 rationale)
- `.planning/phases/16-ad-group-mapping-token-bag-enrichment/16-01-SUMMARY.md` — FOUND (this file)
- Commit `23c1c02` — FOUND in git log (Tasks 1-3)
- Commit `fbb7372` — FOUND in git log (Task 4 option-a application)
- pytest output: 18 passed + 1 xfailed — matches plan's done criteria for terminal state B + option-a application
- Phase 11 `test_coverage_pct_high_plus_medium_only` still PASSES — HARD invariant preserved

---
*Phase: 16-ad-group-mapping-token-bag-enrichment*
*Completed: 2026-05-15*
