---
phase: 16-ad-group-mapping-token-bag-enrichment
plan: 00
subsystem: testing
tags: [pytest, tdd, fixtures, ad-group-match, jaccard, lake-worth-golden]

requires:
  - phase: 11-account-structure-mapping
    provides: ad_group_match.py public surface (build_mapping, _build_ad_group_index, _classify, _tokens, _jaccard, _THRESHOLDS)
  - phase: 14-positives-sync
    provides: raw/google-ads-keywords.json (kw_criteria per AG) — Phase 16 token-bag input
  - phase: 15-campaign-focus
    provides: Narrowed perf/search-terms/keywords artifacts (single-campaign scope) — Lake Worth real-account fixtures sourced from a Phase-15-narrowed run

provides:
  - 5 golden Lake Worth fixtures under tests/fixtures/ (ranked, perf, search-terms, keywords, golden-mapping floor)
  - 5 RED tests in test_ad_group_match.py — 4 SKIPPED under PHASE16_INCOMPLETE + 1 threshold sentinel FAILING loud (TDD wiring proof)
  - PHASE16_INCOMPLETE module-level guard + _skip_unless_phase16() helper
  - scripts/stage_lake_worth_fixtures.py — reproducible fixture re-baker

affects: 16-01 (token-bag enrichment implementation flips these tests GREEN)

tech-stack:
  added: []
  patterns:
    - "Wave-0 scaffold: PHASE16_INCOMPLETE guard mirrors Phase 11 MODULE_INCOMPLETE pattern"
    - "Coverage-floor (>=) assertion vs byte-equality — allows Wave 2 threshold tuning without re-baking fixtures"
    - "Threshold sentinel test (NO skip guard) fires loud at Wave 0 to confirm TDD wiring is connected"
    - "Reproducible-fixture script committed under scripts/ so fixtures can be re-baked deterministically from real run"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/fixtures/ranked_lake_worth.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-perf-lake-worth.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-search-terms-lake-worth.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-keywords-lake-worth.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/golden_mapping_lake_worth.json
    - scripts/stage_lake_worth_fixtures.py
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py

key-decisions:
  - "Real run had 66 ranked rows + 1 ENABLED AG + 2 PAUSED (plan estimated 47 rows + 3 ENABLED) — used real-data fidelity per plan philosophy; updated golden total_ranked=66 and expected_ad_groups to ENABLED-only"
  - "Keywords fixture re-shaped from flat real-data schema (top-level `keyword`) into nested `ad_group_criterion.keyword.text` form to match Phase 16 plan 16-01 _build_ag_token_bag contract"
  - "Threshold sentinel deliberately omits skip guard — must FAIL at Wave 0 to prove TDD wiring works; expected RED state today"

patterns-established:
  - "Wave-0 fixture + RED test scaffold: 4 SKIPPED + 1 FAILED single-sentinel — Wave 2 flips both to GREEN by shipping the missing symbol AND the calibration delta"
  - "Reproducibility: fixture slimming script lives under scripts/ (not tests/) so re-baking on schema drift is one command"

requirements-completed: [ADGM-11]

duration: ~12min
completed: 2026-05-15
---

# Phase 16 Plan 00: Lake Worth Golden Fixtures + RED Test Scaffold Summary

**5 Lake Worth real-account fixtures staged + 5 RED tests for token-bag enrichment (4 SKIPPED behind PHASE16_INCOMPLETE + 1 threshold sentinel FAILING loud — TDD wiring proven for Wave 2)**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-15T16:00:00Z (approx)
- **Completed:** 2026-05-15T16:12:00Z (approx)
- **Tasks:** 2
- **Files created:** 6 (5 fixtures + 1 slimming script)
- **Files modified:** 1 (test_ad_group_match.py)

## Accomplishments

- Lake Worth real-account fixtures committed under tests/fixtures/ — sourced from the Phase-15-narrowed run at `.runs/2026-05-15T153121Z-car-accident-injury-care-services/`
- Reproducible fixture slimming script (`scripts/stage_lake_worth_fixtures.py`) — hardcoded AG name list + sorted keys, deterministic re-bake
- 5 RED tests appended to test_ad_group_match.py — current state: 4 SKIPPED + 1 FAILED (threshold sentinel), 14 Phase 11 tests still GREEN (zero regression)
- PHASE16_INCOMPLETE module-level guard added alongside MODULE_INCOMPLETE — Wave 2 implementation flips it false automatically when `_build_ag_token_bag` symbol exists

## Task Commits

1. **Task 1: Stage Lake Worth golden fixtures from real run** — `5144f8f` (test)
2. **Task 2: Add 5 RED tests for Phase 16 token-bag enrichment** — `43de949` (test)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/tests/fixtures/ranked_lake_worth.json` — 66-row ranked-enriched copied verbatim from real run
- `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-perf-lake-worth.json` — 1 campaign + 3 AGs (1 ENABLED, 2 PAUSED) with status preserved
- `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-search-terms-lake-worth.json` — 63 items narrowed to the 3 AGs (Phase 16 ag_name keying)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-keywords-lake-worth.json` — 47 narrowed items in nested `ad_group_criterion.keyword.text` shape per 16-01 contract
- `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_mapping_lake_worth.json` — floor=50%, expected_ad_groups=[Accident Exams – Lake Worth], total_ranked=66
- `scripts/stage_lake_worth_fixtures.py` — reproducible fixture re-baker
- `.claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py` — +5 tests + PHASE16_INCOMPLETE guard

## Decisions Made

- **Used real-run row counts (66 ranked, 1 ENABLED AG) not plan estimates (47 ranked, 3 ENABLED AGs).** The plan was authored before re-counting; Lake Worth's narrowed run actually has 66 ranked rows and only 1 ENABLED AG (the other 2 are PAUSED). Plan philosophy: "fidelity to the real run is the point" — so the golden fixture reflects ground truth, not the planner's estimate.
- **Re-shaped keywords fixture into nested `ad_group_criterion.keyword.text` form.** Real Phase 14 schema is flat (top-level `keyword`), but Phase 16 plan 16-01 `_build_ag_token_bag` contract expects nested. Re-shaping in the fixture means Wave 2 can implement the contract straight from the plan without an extra schema-adapter layer; the slimming script documents the mapping for future re-bakes.
- **Coverage floor (>=) not equality in golden mapping.** Threshold recalibration in Wave 2 may land coverage anywhere in 55-75% depending on tuning — a `>=50%` floor lets that tuning land without re-baking the fixture each iteration.
- **Threshold sentinel test ships WITHOUT skip guard.** All other Phase 16 tests skip until `_build_ag_token_bag` exists, but the threshold sentinel must FAIL today against the Wave-0 0.7/0.4 values to prove the TDD wiring is connected. Wave 2 lands the calibration delta and the sentinel flips green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan/Data Drift] Plan assumed 47 ranked rows + 3 ENABLED AGs; real run has 66 rows + 1 ENABLED**
- **Found during:** Task 1 (Stage Lake Worth golden fixtures)
- **Issue:** Plan frontmatter (`provides: "47-row ranked-enriched.json"`) and `<source_fixtures>` block (`3 ENABLED AGs inside ad_groups[]`) did not match the actual Phase-15-narrowed run on disk. Real run: 66 ranked rows; only `Accident Exams – Lake Worth` is ENABLED (`AG1` + `AG2` are PAUSED). Search-terms only cover the ENABLED AG; keywords cover all 3 AGs.
- **Fix:** Used real-data counts. golden_mapping_lake_worth.json now has `total_ranked: 66` and `expected_ad_groups: ["Accident Exams – Lake Worth"]`. perf fixture retains all 3 AGs with their real statuses (1 ENABLED, 2 PAUSED) so `_build_ad_group_index` filters as it would in production. Notes field in golden fixture documents the ENABLED count for downstream readers.
- **Files modified:** All 5 fixtures + scripts/stage_lake_worth_fixtures.py
- **Verification:** All 5 fixtures parse as valid JSON; pytest run confirms Phase 11 tests still GREEN; plan's `must_haves.truths` (fixtures exist + decode + 5 RED tests fail correctly) all satisfied.
- **Committed in:** 5144f8f (Task 1)

**2. [Rule 1 - Schema Drift] Real Phase 14 keywords.json has flat schema; plan 16-01 contract expects nested**
- **Found during:** Task 1 (Stage Lake Worth golden fixtures)
- **Issue:** Real `raw/google-ads-keywords.json` items use top-level `keyword`, `match_type`, `status` fields. Plan 16-01 `_build_ag_token_bag` signature expects items with `ad_group_criterion.keyword.text` nested shape.
- **Fix:** Slimming script re-shapes each kept item into the nested form. Decision deferred to Wave 2 whether to (a) keep nested shape in the fixture as the public contract OR (b) align the implementation to the flat real-data shape — current decision is (a) so plan 16-01 implementation matches its own spec.
- **Files modified:** scripts/stage_lake_worth_fixtures.py, google-ads-keywords-lake-worth.json
- **Verification:** Fixture parses; 47 items emitted; Wave 2 (plan 16-01) will catch any contract mismatch via the SKIPPED tests flipping GREEN.
- **Committed in:** 5144f8f (Task 1)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — plan/data drift). Both essential for fixture correctness against real account data.
**Impact on plan:** Plan's success criteria still met — 5 fixtures staged, 5 RED tests scaffolded, threshold sentinel fires loud. The data-count deltas (66 vs 47, 1 vs 3 ENABLED) make the golden mapping MORE faithful to ground truth, not less.

## Issues Encountered

- None during execution. The plan/real-run data drift was caught immediately on first inspection of the source artifacts (see Deviations).

## Self-Check: PASSED

- `.claude/skills/google-ad-research/scripts/tests/fixtures/ranked_lake_worth.json` — FOUND (27,856 bytes)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-perf-lake-worth.json` — FOUND (645 bytes)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-search-terms-lake-worth.json` — FOUND (10,661 bytes)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-keywords-lake-worth.json` — FOUND (12,126 bytes)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_mapping_lake_worth.json` — FOUND (639 bytes)
- `scripts/stage_lake_worth_fixtures.py` — FOUND
- Commit `5144f8f` — FOUND in git log
- Commit `43de949` — FOUND in git log
- pytest output: 14 PASSED + 4 SKIPPED + 1 FAILED (threshold sentinel as expected) — matches plan's done criteria

## Next Phase Readiness

- Plan 16-01 (`_build_ag_token_bag` implementation + threshold recalibration) inherits a 4-skip + 1-fail RED set. Wave 2 flips all 5 GREEN by:
  1. Adding `_build_ag_token_bag(ag_name, kw_criteria, search_terms, top_n_terms=10)` returning `frozenset[str]`
  2. Threading `keywords` dict through `_build_ad_group_index` + `build_mapping` + `main_with_args`
  3. Extending `match.reason` format to include `name=X.XX kw-criterion=Y.YY search-term=Z.ZZ` substrings
  4. Lowering `_THRESHOLDS` (likely 0.5 high / 0.25 medium per ROADMAP empirical-calibration target)
- No blockers. Plan 16-01 is unblocked and can be executed next.

---
*Phase: 16-ad-group-mapping-token-bag-enrichment*
*Completed: 2026-05-15*
