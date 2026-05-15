---
phase: 16-ad-group-mapping-token-bag-enrichment
plan: 03
subsystem: ad-group-match
tags: [phase16, adgm-11, red-tests, tdd-wiring, per-source-max-jaccard, gap-closure]

requires:
  - phase: 16-ad-group-mapping-token-bag-enrichment
    plan: "01"
    provides: _build_ad_group_index partial token sets (name_tokens, criterion_tokens, search_term_tokens) — partials already shipped to power the per-source reason field; Plan 16-04 will reuse them as the inputs to max(name_j, crit_j, term_j)
  - phase: 16-ad-group-mapping-token-bag-enrichment
    plan: "02"
    provides: live e2e reason-field evidence (jaccard=0.10, name=0.33, kw=0.00, st=0.00 — full-union dilution failure mode that motivates per-source max-Jaccard as the structural fix)
  - phase: 11-account-structure-mapping
    provides: google-ads-perf-phase11.json + google-ads-search-terms-phase11.json fixtures (re-used by test_max_jaccard_preserves_garbage_low for C5 invariant guard)

provides:
  - "4 new RED tests + 1 xfail-decorator-removal in test_ad_group_match.py pinning the per-source max-Jaccard structural fix contract for Plan 16-04"
  - "test_per_source_max_jaccard_used_for_scoring — lynchpin RED on a constructed fixture (1 AG name 'Accident' + 30 non-overlapping criteria) where full-union Jaccard mathematically cannot produce the asserted high classification; full-union gives 1/31 ≈ 0.032 (low), per-source max gives name_j=1.0 (high)"
  - "test_max_jaccard_boundary_tied_sources — score-value RED: full-union yields 0.50 but per-source max yields 0.333 (1/3 from tied name + criterion sources)"
  - "test_max_jaccard_boundary_all_zero_sources — degenerate-case regression guard; passes under both algorithms (no overlap → all jaccards 0.0)"
  - "test_max_jaccard_preserves_garbage_low — C5 invariant guard on Phase 11 fixture (tomato sandwich / quantum mechanics stay low → coverage 0.0%)"
  - "test_lake_worth_coverage_floor unguarded — xfail decorator removed; test now FAILS LOUD against full-union (16.67% < 50%) as TDD-wiring proof pre-16-04"

affects: 16-04 (gap-closure plan must flip the 3 RED tests GREEN by replacing the full-union Jaccard call in build_mapping with `max(name_j, crit_j, term_j)`)

tech-stack:
  added: []
  patterns:
    - "Score-VALUE RED tests over score-CLASS RED tests for algorithm-shape changes: test_max_jaccard_boundary_tied_sources asserts score ≈ 0.333 not just 'confidence=high' — score-class assertions would have passed under both algorithms (full-union 0.50 and per-source max 0.333 both classify high), masking the structural change; score-value pinning surfaces the algorithm delta cleanly"
    - "Constructed-fixture RED test as lynchpin: test_per_source_max_jaccard_used_for_scoring uses an in-memory fixture where the math is unambiguous (1/31 vs 1.0) rather than relying on real-account fixtures; full-union is mathematically incapable of producing the asserted result, so the test cannot pass by accident under any threshold drift"
    - "Degenerate-case + invariant guards alongside lynchpin RED: test_max_jaccard_boundary_all_zero_sources + test_max_jaccard_preserves_garbage_low pass under both algorithms — they don't prove the fix is in place, but they catch regressions where the max() rewrite mis-handles empty intersections or accidentally relaxes the C5 garbage guard"

key-files:
  created:
    - .planning/phases/16-ad-group-mapping-token-bag-enrichment/16-03-SUMMARY.md
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py

key-decisions:
  - "Lynchpin fixture uses intent='commercial' on the ranked kw (not 'transactional' as the plan suggested) — AG bag contains 'accident' + 30 non-marker tokens so _infer_ad_group_intent returns the default 'commercial' (no transactional/commercial/informational markers fire); matching intents → multiplier=1.0 → score equals raw_j cleanly. Plan's 'transactional' would have applied 0.5 multiplier → score 0.5 → still ≥0.30 high but obscures the math. Picking matching intent keeps the assertion '1.0 ≥ 0.30' arithmetically transparent."
  - "Tied-sources test uses score-VALUE assertion (≈ 0.333) not just score-CLASS (== 'high') — under full-union the same fixture yields 0.50 which is ALSO 'high', so a class-only assertion would pass GREEN today. The 0.333 value is achievable ONLY under per-source max, making the test correctly RED."
  - "All 4 new tests placed AFTER the existing ADGM-07..10 section (line 514 onward) with a comment-block divider citing the live e2e evidence from 16-02 — preserves Plan 16-01's section layout and gives the 16-04 implementer a single contiguous block of new tests to flip GREEN."
  - "Re-used existing _skip_unless_phase16() guard pattern in all 4 new tests — consistent with the 16-01 ADGM-07..11 section convention; ensures the tests skip cleanly if a future caller imports the module pre-Phase-16."

patterns-established:
  - "Score-VALUE pinning for algorithm-shape RED tests (vs threshold-class pinning) — applicable to any future scoring algorithm change where the new algorithm produces a DIFFERENT score on the same input, even if the classification tier coincidentally matches"
  - "Constructed in-memory lynchpin fixture + real-fixture invariant guards — separate concerns: the lynchpin proves the new algorithm wired correctly, the invariant guards prove the old contracts weren't accidentally weakened"

requirements-progressed: [ADGM-11]
requirements-completed: []

duration: ~3min (single TDD RED authoring task, no checkpoints)
completed: 2026-05-15
---

# Phase 16 Plan 03: Per-Source Max-Jaccard RED Tests Summary

**4 RED tests authored + 1 xfail decorator removed in `test_ad_group_match.py`, locking the test contract for Plan 16-04's per-source max-Jaccard structural fix; suite runs 3 FAILED + 20 PASSED (Phase 11 80% C2 invariant preserved unchanged), proving the RED state is correctly wired and Plan 16-04 has a clean target to flip GREEN.**

## Performance

- **Duration:** ~3 min (single-task TDD RED authoring; no checkpoints)
- **Started:** 2026-05-15T19:19:56Z
- **Completed:** 2026-05-15T19:22:21Z
- **Tasks:** 1 (RED test authoring + xfail removal — both in one commit)
- **Files created:** 1 (this SUMMARY)
- **Files modified:** 1 (`test_ad_group_match.py`)

## Accomplishments

- **`@pytest.mark.xfail(strict=True)` decorator removed** from `test_lake_worth_coverage_floor` (was lines 385-400 in Plan 16-01 lock state). Docstring updated to cite Plan 16-04 as the structural fix that will flip it GREEN. The test now FAILS LOUD against current HEAD `ad_group_match.py` — observed 16.67% < 50.0% floor (offline goldenfile) — proving the deferred gap is now exposed in the test suite as a regression-class signal.
- **`test_per_source_max_jaccard_used_for_scoring` added** as the lynchpin RED test. Constructed fixture: 1 ENABLED AG named "Accident" (`name_tokens={accident}`) + 30 distinct non-overlapping criterion tokens (greek letters + fruits, none of which fire any `_INTENT_MARKERS` so AG inferred intent stays "commercial"). Ranked kw "accident" with `intent="commercial"` (matching → multiplier=1.0). Math is unambiguous:
  - Full-union: bag has 31 tokens, kw∩bag={accident}, jaccard = 1/31 ≈ 0.032 → classifies LOW (below medium=0.10)
  - Per-source max: name_j=1.0, crit_j ≈ 0.032, term_j=0 → max=1.0 → classifies HIGH (≥0.30)

  Assertion `confidence == "high" AND score >= 0.30` is mathematically unreachable under full-union — only per-source max can satisfy.
- **`test_max_jaccard_boundary_tied_sources` added** to pin the algorithm shape via score-VALUE assertion. AG name="cardiology clinic" + 1 kw_criterion "heart specialist"; ranked kw "cardiology heart". Both name_j and crit_j equal 1/3 ≈ 0.333 under per-source max, while full-union scores 2/4 = 0.50. The test asserts `score == pytest.approx(0.333, abs=0.01)` — a score-CLASS-only assertion (e.g., `confidence == "high"`) would have passed GREEN today (full-union 0.50 is also "high"), masking the structural delta. The 0.333 value can only emerge under per-source max.
- **`test_max_jaccard_boundary_all_zero_sources` added** as a degenerate-case regression guard. Kw with zero token overlap; passes under both full-union and per-source max (all 3 partial jaccards = 0.0 → max=0.0 → low). Doesn't prove the fix; proves the rewrite didn't accidentally mis-handle empty intersections.
- **`test_max_jaccard_preserves_garbage_low` added** as a C5 invariant guard on the Phase 11 fixture. Two garbage keywords ("tomato sandwich recipe", "quantum mechanics tutorial") share zero tokens with any ENABLED AG bag; coverage stays at 0.0% under both algorithms. Catches any accidental over-permissive regression introduced by the max() rewrite.

## Task Commits

1. **Task 1: Add per-source max-Jaccard RED tests + remove xfail decorator** — `7d76a9e` (test) — 267 insertions, 17 deletions in `test_ad_group_match.py`

## Test Suite State After This Plan

```
$ uv run --with pytest --with python-dotenv --with python-slugify \
    pytest .claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py -v

PASSED  test_module_imports
PASSED  test_phase8_absent_graceful_skip
PASSED  test_similarity_math_exact_intent
PASSED  test_similarity_math_intent_mismatch
PASSED  test_stopword_filter_active
PASSED  test_confidence_tier_high
PASSED  test_confidence_tier_medium_boundary
PASSED  test_confidence_tier_high_boundary
PASSED  test_confidence_tier_low
PASSED  test_mapping_shape_keys
PASSED  test_coverage_pct_high_plus_medium_only        ← C2 invariant (80% Phase 11) — preserved
PASSED  test_disabled_ad_groups_skipped
PASSED  test_token_bag_keyed_by_ad_group_name
PASSED  test_unicode_dashes_preserved
FAILED  test_lake_worth_coverage_floor                 ← ADGM-11 exposed (ex-xfail; 16.67% < 50%)
PASSED  test_backward_compat_keywords_absent
PASSED  test_reason_field_per_source_attribution
PASSED  test_token_bag_unions_all_three_sources
PASSED  test_thresholds_recalibrated_below_phase11
FAILED  test_per_source_max_jaccard_used_for_scoring   ← RED lynchpin (full-union 0.032 → low, expected high)
PASSED  test_max_jaccard_boundary_all_zero_sources     ← degenerate (passes either way)
FAILED  test_max_jaccard_boundary_tied_sources         ← RED score-VALUE (full-union 0.50 ≠ expected 0.333)
PASSED  test_max_jaccard_preserves_garbage_low         ← C5 invariant (passes either way)

== 3 failed, 20 passed in 0.49s ==
```

**RED proof (representative failure output from `test_max_jaccard_boundary_tied_sources`):**

```
E   AssertionError: Expected score ≈ 0.333 under per-source max-Jaccard (1/3 from
    tied name/criterion sources); got 0.5. Full-union Jaccard yields 0.50 here, NOT
    0.333 — RED under current algorithm. reason='jaccard=0.50 (name=0.33
    kw-criterion=0.33 search-term=0.00) intent_match=True'
E   assert 0.5 == 0.333 ± 0.01
```

Note the reason-field output: `name=0.33 kw-criterion=0.33` — the per-source partial jaccards are already correct (Plan 16-01 stored them in the index). Plan 16-04 just needs to feed those values into a `max()` call instead of recomputing via full-union — confirming the 16-01 SUMMARY's claim that the structural fix is a small surgical delta.

## Pre-/Post-Plan-16-04 Expectation

| Test | Pre-16-04 (current HEAD) | Post-16-04 |
|------|--------------------------|------------|
| `test_lake_worth_coverage_floor` | **FAILED** (16.67% < 50.0%) | **PASSED** (per-source max lifts coverage past floor) |
| `test_per_source_max_jaccard_used_for_scoring` | **FAILED** (full-union 1/31 ≈ 0.032 → low) | **PASSED** (name_j=1.0 → high; score ≥ 0.30) |
| `test_max_jaccard_boundary_tied_sources` | **FAILED** (full-union 0.50 ≠ 0.333) | **PASSED** (per-source max 0.333 ≈ 0.333) |
| `test_max_jaccard_boundary_all_zero_sources` | PASSED (degenerate; 0.0 under both) | PASSED (unchanged) |
| `test_max_jaccard_preserves_garbage_low` | PASSED (C5; zero overlap under both) | PASSED (C5 must remain — Plan 16-04 cannot break this) |
| `test_coverage_pct_high_plus_medium_only` (C2 invariant) | PASSED (80%) | PASSED (must remain — Plan 16-04 cannot break this) |
| All other existing tests (18 total) | PASSED | PASSED (Plan 16-04 cannot break any) |

**Plan 16-04 success contract:** Replace the full-union Jaccard call at `ad_group_match.py` line 312 with `max(name_j, crit_j, term_j)` where the three per-source jaccards are computed against the partial sets already stored in `index[ag_name]` (`name_tokens`, `criterion_tokens`, `search_term_tokens` — all shipped in Plan 16-01). All 3 RED tests must flip GREEN; all 20 currently-passing tests (including C2 80% invariant + C5 garbage-low + ADGM-07..10 reason-field) must stay GREEN.

## Decisions Made

- **Lynchpin fixture uses matching intent (commercial) rather than the plan's suggested transactional intent.** AG bag contains "accident" + 30 non-marker tokens, so `_infer_ad_group_intent` defaults to "commercial" (no transactional/commercial/informational markers fire). Matching intents → multiplier=1.0 → score equals raw_j cleanly. The plan's "transactional" would have applied 0.5 multiplier → score 0.5 → still ≥0.30 high but obscures the math (now the test passes because 0.5 × 1.0 = 0.5 NOT because 1.0 → high, conflating two contracts). Picking matching intent keeps the assertion `1.0 ≥ 0.30` arithmetically transparent.
- **Score-VALUE assertion in tied-sources test (not score-CLASS).** Under full-union, the tied-sources fixture yields 0.50 which IS classified "high" — a class-only assertion would have passed GREEN today, masking the structural delta. The plan-prescribed `score == pytest.approx(0.333, abs=0.01)` is achievable ONLY under per-source max, making the test correctly RED. This is the key TDD principle for algorithm-shape changes: pin the value the new algorithm produces, not the tier classification.
- **Lynchpin uses 30 distinct non-overlapping criterion tokens (greek + fruits) to drive full-union toward sub-medium classification.** Plan's draft included a smaller fixture that would have yielded full-union 1/5 = 0.20 (still medium — half-RED). The 30-token version pushes full-union to 1/31 ≈ 0.032 < 0.10 medium threshold → fully low under current algorithm, fully high under per-source max — a clean tier-shift across both thresholds. This guards against any future calibration drift on the medium threshold.

## Deviations from Plan

### Auto-fixed Issues

None during this plan. The single task was a TDD RED authoring task with no executable code beyond pytest fixtures; no auto-fixes were triggered.

### Plan-Construction Refinements (applied during execution)

The plan's draft for `test_per_source_max_jaccard_used_for_scoring` initially had two construction variants (lines 180-196 of 16-03-PLAN.md). The plan author flagged the first variant ("Lake Worth Accident" name) as wrong because the resulting full-union jaccard (3/5 = 0.60) would have ALREADY classified high, defeating the RED purpose. They explicitly switched to the "AG name='Accident' + 30 distinct criteria" variant. I executed the second (correct) variant per the plan's redesign. The plan also suggested using `string.ascii_lowercase[:30]` or similar; I used 24 greek letters + 6 fruits (alpha..omega + apple, banana, cherry, elderberry, fig, grape) to guarantee `_TOKEN_RE = r"\b[a-z]{2,}\b"` matches all 30 tokens cleanly without any 1-char edge cases that ascii_lowercase would have produced.

The plan's prescribed `intent="transactional"` on the lynchpin's ranked kw was changed to `intent="commercial"` per the "Decisions Made" entry above — keeps the math transparent. Score reaches 1.0 (≥ 0.30) under either intent choice, so the assertion still holds either way; commercial is just arithmetically cleaner.

## Issues Encountered

None. The plan's `<verification>` section predicted exactly 3 FAILED tests (Lake Worth floor + per-source max lynchpin + tied-sources score-value); execution observed exactly 3 FAILED tests. No surprises in the RED proof.

The plan also noted that if `test_max_jaccard_boundary_tied_sources` happened to coincidentally score 0.50 under full-union (which it does), and that 0.50 happens to ALSO be ≥ 0.30 (so confidence=="high" passes), the test could potentially pass on the class assertion alone — this is why I followed the plan's explicit prescription to assert on score VALUE (`pytest.approx(0.333, abs=0.01)`), not just classification. The score-value assertion is what makes the test correctly RED.

## Phase 16 Status After This Plan

- **ADGM-07** ✅ Complete (16-01) — token-bag union shipped
- **ADGM-08** ✅ Complete (16-01) — graceful absence of `raw/google-ads-keywords.json` preserved
- **ADGM-09** ✅ Complete (16-01) — per-source reason field renders
- **ADGM-10** ✅ Complete (16-02) — calibration rationale auditable
- **ADGM-11** ⏳ RED-state wired (16-03) → GREEN target for Plan 16-04. 3 RED tests + 1 unguarded floor test + Phase 11 C2 invariant + C5 garbage guard all pinned. The structural fix (`max(name_j, crit_j, term_j)` in `build_mapping`) has a clean, unambiguous test contract.

## Next Plan Readiness

Plan 16-04 (the structural fix that flips these RED tests GREEN) inherits:

1. **A clean RED test contract.** 3 tests must flip from FAILED to PASSED; 20 tests must stay PASSED. Zero ambiguity on success criteria.
2. **A surgical implementation target.** The full-union Jaccard call at `ad_group_match.py` line 312 (`raw_j = _jaccard(kw_tokens, ag["token_bag"])`) is the single point of change. The partial sets (`name_tokens`, `criterion_tokens`, `search_term_tokens`) are already in `index[ag_name]` (shipped Plan 16-01) — no helper functions or new data flow needed.
3. **Live e2e closeout pattern already established.** Plan 16-02's pattern of (a) ship offline change, (b) run live e2e on real Lake Worth OAuth account, (c) compare predicted vs observed coverage — applicable as-is to Plan 16-04. The 16.42% live baseline is the floor 16-04 must lift past 50%.
4. **Reason-field format unchanged.** The `jaccard=X.XX (name=Y.YY kw-criterion=Z.ZZ search-term=W.WW)` format already correctly attributes per-source contributions; under per-source max the `jaccard=X.XX` value will simply equal the max of the three component values (one of them IS the score), making the format causally aligned with the score (was previously decorative — partials didn't sum to or relate to the full-union jaccard).
5. **C2 + C5 sentinels in place.** Plan 16-04 cannot accidentally weaken either invariant without the suite catching it.

No blockers. Plan 16-04 can be authored next.

## Self-Check: PASSED

- `.claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py` — FOUND (modified; 4 new tests + 1 xfail removal; 267 insertions / 17 deletions)
- `.planning/phases/16-ad-group-mapping-token-bag-enrichment/16-03-SUMMARY.md` — FOUND (this file)
- Commit `7d76a9e` — FOUND in git log (Task 1 commit)
- `@pytest.mark.xfail` count in test_ad_group_match.py — 0 (decorator removed)
- 4 new test function definitions verified via grep — all present
- pytest result: 3 failed + 20 passed — matches plan's verification section prediction exactly
- C2 invariant `test_coverage_pct_high_plus_medium_only` — PASSED (HARD invariant preserved)
- ADGM-07..10 tests (`test_token_bag_unions_all_three_sources`, `test_backward_compat_keywords_absent`, `test_reason_field_per_source_attribution`, `test_thresholds_recalibrated_below_phase11`) — all PASSED unchanged

---
*Phase: 16-ad-group-mapping-token-bag-enrichment*
*Completed: 2026-05-15*
