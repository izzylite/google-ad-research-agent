---
phase: 16-ad-group-mapping-token-bag-enrichment
verified: 2026-05-15T21:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "ADGM-11 ≥50% high+medium coverage floor — real Lake Worth OAuth account now at 50.75% (operator-approved); 23/23 test_ad_group_match.py tests pass; xfail marker removed"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run skill end-to-end on a second real Google Ads OAuth account with short-label AG names"
    expected: "mapping_coverage_pct and reason-field shape consistent with offline golden prediction within ~1pp; no regression on Phase 11 80% C2 invariant"
    why_human: "Requires a second OAuth-enabled Google Ads account; cannot verify programmatically — watch-item only, does not block phase closure"
---

# Phase 16: Ad Group Mapping Token-Bag Enrichment Verification Report

**Phase Goal:** `ad_group_match.py` Jaccard scoring uses an enriched per-AG token bag, lifting high+medium mapping coverage from 0% to 50%+ on real client accounts whose AG names are short labels. When Phase 14 `raw/google-ads-keywords.json` is absent, falls back silently to the current search-terms-only Jaccard plus AG name addition.
**Verified:** 2026-05-15T21:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap-closure cycle (plans 16-03 + 16-04 + 16-05)

## Re-verification Context

The initial verification (2026-05-15T20:00:00Z) returned `gaps_found` with score 3/5. The single blocking gap was ADGM-11: live Lake Worth coverage was 16.42% (offline golden 16.67%), far below the ≥50% floor. Root cause was structural — full-union Jaccard's |A∪B| denominator diluted scores when the AG token bag (~34 tokens) dwarfed the ranked-keyword query (4-6 tokens).

Gap-closure cycle shipped three plans:
- **16-03**: Removed `@pytest.mark.xfail(strict=True)` from `test_lake_worth_coverage_floor`; authored 3 RED tests pinning the per-source max-Jaccard contract (`test_per_source_max_jaccard_used_for_scoring`, `test_max_jaccard_boundary_tied_sources`, `test_max_jaccard_boundary_all_zero_sources`) and 1 C5 invariant guard (`test_max_jaccard_preserves_garbage_low`). Suite state: 3 FAILED + 20 PASSED.
- **16-04**: Replaced full-union `_jaccard(kw_tokens, ag["token_bag"])` with `raw_j = max(name_j, crit_j, term_j)` in `build_mapping`; recalibrated thresholds to option-d `{high: 0.30, medium: 0.08}`; discovered and fixed a preexisting shape-mismatch bug (nested reader vs flat writer at `perf_fetch.py:292-303` boundary, commit `56d4196`). Live Lake Worth post-fix: **50.75%**. All 23 `test_ad_group_match.py` tests GREEN.
- **16-05**: Updated `references/phase11-account-structure-mapping.md` with per-source max-Jaccard algorithm rationale, calibration sweep table, live e2e closeout, and shape-bug discovery. STATE.md ADGM-11 structural-algorithm follow-up bullet removed. REQUIREMENTS.md coverage summary updated 0/11 → 11/11 v1.5. ROADMAP.md Phase 16 entry marked 6/6 Complete.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Real account previously at 0% Phase 11 coverage → ≥50% post-Phase-16 coverage with Phase 14 + Phase 15 data present | VERIFIED | Live Lake Worth OAuth account: `mapping_coverage_pct = 50.75` confirmed in `.runs/2026-05-15T180642Z-car-accident-injury-care-services/ad-group-mapping.json` line 474; `skipped_reason: null` confirms full code path ran; operator-approved. Offline goldenfile: 54.55%. `test_lake_worth_coverage_floor` passes (no xfail; asserts ≥ 50.0). |
| 2 | Backward-compat: account without OAuth → name-only behavior preserved, no errors | VERIFIED | `test_backward_compat_keywords_absent` passes; `main_with_args` guards `keywords_path.exists()` at lines 514-522; `keywords=None` degrades gracefully to `max(name_j, 0.0, term_j)` — empirical without-keywords coverage is 43.94% (≤50.0% ceiling). ADGM-08 contract intact. |
| 3 | Each match entry carries a `reason` field with per-source attribution | VERIFIED | Live sample confirms format: `"jaccard=0.33 (name=0.33 kw-criterion=0.08 search-term=0.00) intent_match=True"`. `test_reason_field_per_source_attribution` passes (asserts `name=`, `kw-criterion=`, `search-term=` all present). `build_mapping` lines 363-384 emit this format for both high+medium and borderline-low matches. |
| 4 | Recalibrated thresholds documented in `references/phase11-account-structure-mapping.md` with empirical rationale | VERIFIED | `_THRESHOLDS = {"high": 0.30, "medium": 0.08}` at `ad_group_match.py` lines 37-58 with inline rationale block. Reference doc `### Plan 16-04: Per-Source Max-Jaccard Structural Fix (ADGM-11)` subsection (lines ~283-346) contains algorithm one-liner, calibration sweep table `{0.30, 0.10}` + `{0.30, 0.08}`, live e2e closeout trajectory, shape-fix paragraph, and ADGM-11 Complete status. `test_thresholds_recalibrated_below_phase11` passes. |
| 5 | Operator can paste keywords and land in right ad groups on short-name-AG accounts | VERIFIED (automated portion) | 50.75% live coverage on Lake Worth short-name-AG account confirmed. 52 of 67 matches show non-zero `kw_criterion` contribution, confirming all three token-bag sources are exercised. `reason` field identifies the winning evidence channel on each match, enabling operator audit. Paste workflow via `export_csv.py` unchanged from Phase 11; Editor CSV export not re-tested in Phase 16 (unmodified). Human confirmation of Editor paste workflow is a watch-item, not a blocker — see Human Verification section. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `ad_group_match.py` | Per-source max-Jaccard in `build_mapping`; `_build_ag_token_bag` present; thresholds `{0.30, 0.08}`; 450+ lines | VERIFIED | 560 lines; `build_mapping` lines 339-345 compute `name_j`, `crit_j`, `term_j` per-AG and take `raw_j = max(...)`; `best_partials` cached at line 357; `_THRESHOLDS = {"high": 0.30, "medium": 0.08}` lines 57-58; `_build_ag_token_bag` at line 158; flat-shape keyword reader at lines 263-270 |
| `tests/test_ad_group_match.py` | 23 tests GREEN; no `xfail` markers; 3 Plan 16-03 RED tests now PASS | VERIFIED | Grep for `xfail` returns zero matches. All 4 Plan 16-03 tests (`test_lake_worth_coverage_floor`, `test_per_source_max_jaccard_used_for_scoring`, `test_max_jaccard_boundary_tied_sources`, `test_max_jaccard_boundary_all_zero_sources`) present without xfail. 16-04 SUMMARY confirms 23/23 GREEN, 180 passed + 103 skipped full suite. |
| `tests/fixtures/golden_mapping_lake_worth.json` | `mapping_coverage_pct_floor: 50.0` | VERIFIED | `mapping_coverage_pct_floor: 50.0` per initial verification; fixture not regenerated post-16-04 (offline goldenfile remains at 54.55%; shape-agnostic — algorithm logic test). |
| `tests/fixtures/google-ads-keywords-lake-worth.json` | Phase 14 keyword_view — fixture re-shaped for self-consistency | VERIFIED | File present (16-04 SUMMARY: re-shaped for self-consistency with goldenfile; live-layer shape contract verified at `perf_fetch ↔ ad_group_match` directly). |
| `references/phase11-account-structure-mapping.md` | Phase 16 section updated with per-source max-Jaccard algorithm + calibration sweep + live closeout + shape-bug; ≤346 lines total | VERIFIED | 346 lines (under 350-line cap); `### Plan 16-04: Per-Source Max-Jaccard Structural Fix (ADGM-11)` subsection confirmed (lines ~283-346); calibration sweep table with {0.30, 0.10} and {0.30, 0.08} rows; `max(name_j, crit_j, term_j)` one-liner; 50.75% live e2e closeout; shape-fix paragraph with commit `56d4196`; ADGM-11 Complete status. |
| `.planning/STATE.md` | ADGM-11 open question removed; closure decision logged | VERIFIED | `stopped_at` reflects Plan 16-05 closeout; `completed_plans: 65`; `completed_phases: 13`; v1.5 requirements `11/11`; ADGM-11 structural-algorithm follow-up bullet removed; forward-looking "Next-account calibration cycle" watch-item retained. |
| `.planning/REQUIREMENTS.md` | ADGM-07..11 all `[x]`; Coverage summary 11/11 v1.5 | VERIFIED | All 5 ADGM-07..11 rows have `[x]` at lines 204-208; Coverage summary updated to `11/11 v1.5 Complete` and `107/107` total per 16-05 SUMMARY. |
| `.planning/ROADMAP.md` | Phase 16 entry 6/6 Complete | VERIFIED | 16-05 SUMMARY confirms: `6/6 plans executed`; Progress table row `6/6 Complete | 2026-05-15`; 16-05 row `[x]`. |
| `.runs/2026-05-15T180642Z-.../ad-group-mapping.json` | `mapping_coverage_pct >= 50.0` | VERIFIED | `"mapping_coverage_pct": 50.75` at line 474; `"skipped_reason": null`; `"unmapped_count": 33`; first match shows per-source reason format `"jaccard=0.33 (name=0.33 kw-criterion=0.08 search-term=0.00) intent_match=True"`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `build_mapping` | per-source max-Jaccard | `raw_j = max(name_j, crit_j, term_j)` at line 345 | WIRED | Computed against `ag["name_tokens"]`, `ag["criterion_tokens"]`, `ag["search_term_tokens"]` stored in index by `_build_ad_group_index` |
| `_build_ad_group_index` | partial token sets | Stores `name_tokens`, `criterion_tokens`, `search_term_tokens` at lines 286-292 | WIRED | Powers both reason-field rendering (via `best_partials` cache at line 357) and scoring |
| `build_mapping` | `best_partials` cache | Assigned `best_partials = (name_j, crit_j, term_j)` at line 357; unpacked at lines 365/379 | WIRED | Causally aligns reason field with winning score — reason now reflects the AG that won, not a post-loop re-lookup |
| `main_with_args` | `google-ads-keywords.json` | `keywords_path.exists()` guard at line 514; passes to `build_mapping` at line 524; absent → `keywords=None` | WIRED | Graceful absence path confirmed by `test_backward_compat_keywords_absent` |
| `ad_group_match.py` keyword reader | `perf_fetch.py:292-303` flat writer | Flat-shape access: `kw.get("keyword")`, `kw.get("status")`, `kw.get("ad_group_name")` | WIRED (shape-fix 56d4196) | Shape-mismatch bug (nested reader vs flat writer) fixed in Plan 16-04 Task 2.5; 52/67 live matches now show non-zero `kw_criterion` contribution confirming the fix is exercised end-to-end |
| `SKILL.md` | `references/phase11-account-structure-mapping.md` | Existing Phase 11 progressive-disclosure pointer at line 495 | WIRED | Pointer predates Phase 16; SKILL.md at 497/500 lines (unchanged) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| ADGM-07 | 16-01 | `_build_ag_token_bag` produces token set = AG name ∪ kw_criterion ∪ top-10 search-term tokens by clicks | SATISFIED | `_build_ag_token_bag` at lines 158-202; flat-shape reader confirmed; `test_token_bag_unions_all_three_sources` passes |
| ADGM-08 | 16-01 | Jaccard scoring falls back to name-only when Phase 14 `raw/google-ads-keywords.json` absent | SATISFIED | `main_with_args` soft-fails absent keywords.json at lines 512-522; `test_backward_compat_keywords_absent` passes (coverage ≤50.0%) |
| ADGM-09 | 16-01 | Match `reason` field surfaces which evidence source contributed | SATISFIED | `build_mapping` lines 363-384 emit `jaccard=X.XX (name=Y.YY kw-criterion=Z.ZZ search-term=W.WW) intent_match=B`; `test_reason_field_per_source_attribution` passes; live sample confirmed |
| ADGM-10 | 16-01, 16-02 | Threshold recalibration with empirical rationale documented | SATISFIED | `_THRESHOLDS = {"high": 0.30, "medium": 0.08}` with inline sweep rationale; reference doc Plan 16-04 section has calibration sweep table + option-d rationale; `test_thresholds_recalibrated_below_phase11` passes |
| ADGM-11 | 16-00, 16-01, 16-03, 16-04 | Golden mapping fixture from Lake Worth asserts ≥50% high+medium coverage | SATISFIED | `test_lake_worth_coverage_floor` passes (no xfail; asserts ≥50.0%); live 50.75%; offline 54.55%; 23/23 `test_ad_group_match.py` GREEN |

**All 5 ADGM-07..11 requirements satisfied. 107/107 v1 requirements Complete.**

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `ad_group_match.py` | 205-293 | `_build_ad_group_index` inlines token-computation logic from `_build_ag_token_bag` rather than delegating to it | Info | No functional impact — both paths produce identical token sets. Structural coupling is intentional: the index function must capture partial sets (`name_tokens`, `criterion_tokens`, `search_term_tokens`) separately for reason-field attribution. `_build_ag_token_bag` is still exposed at module level and tested separately. Cleanup opportunity only. |

No TODO/FIXME/placeholder anti-patterns found in Phase 16 modified files. No empty implementations. No `return null` stubs. No `xfail` markers in `test_ad_group_match.py`. No stub-class red flags.

### Human Verification Required

#### 1. Editor Paste Workflow at Short-Name-AG Accounts (Watch-Item)

**Test:** Take the high/medium matches from `.runs/2026-05-15T180642Z-car-accident-injury-care-services/ad-group-mapping.json` and paste the corresponding keywords from `positives.csv` into Google Ads Editor, landing them in "Accident Exams – Lake Worth."
**Expected:** Keywords route to the correct existing AG; Editor does not emit duplicate-AG errors; operator finds the routing decision auditable from the `reason` field.
**Why human:** End-to-end Editor import workflow; cannot verify without a live Google Ads Editor session.

#### 2. Second-Account Calibration (Watch-Item)

**Test:** Run the full skill end-to-end against a second real Google Ads OAuth account with short-label AG names.
**Expected:** `mapping_coverage_pct` and reason-field shape consistent with offline prediction; `{0.30, 0.08}` thresholds generalise beyond a single-account calibration.
**Why human:** Requires a second OAuth-enabled Google Ads account. Documented as a forward-looking watch-item in STATE.md Open Questions — not a blocker for phase closure.

### Gaps Summary

No blocking gaps remain. Phase 16 is fully closed.

The ADGM-11 gap from the initial verification was resolved by the 16-03 / 16-04 / 16-05 gap-closure cycle:

1. **Algorithm fix (16-04):** `raw_j = max(name_j, crit_j, term_j)` replaced full-union `_jaccard(kw_tokens, ag["token_bag"])` in `build_mapping`. The full-union denominator diluted scores below useful thresholds on accounts whose AG token bags are structurally larger than ranked-keyword queries. Per-source max preserves the strongest evidence channel (name Jaccard in Lake Worth's case).

2. **Shape-bug fix (16-04 Task 2.5):** A preexisting bug (nested reader vs flat writer at the `perf_fetch.py:292-303 ↔ ad_group_match.py` boundary) silently zeroed `kw_criterion` contribution on every live run from Phase 16-01 through pre-fix. Fix: 4 field accesses changed to flat shape (`kw["keyword"]`, `kw["status"]`, `kw["ad_group_name"]`). Post-fix: 52 of 67 live matches show non-zero `kw_criterion` contribution.

3. **Threshold recalibration (16-04 option-d):** `medium` lowered from 0.10 to 0.08. Under per-source max-Jaccard, garbage keywords score exactly 0.0 (no shared tokens → all three partials 0.0 → max=0.0), so the 0.10 floor was structurally obsolete. 0.08 admits legitimate borderline name-only matches without re-opening the C5 garbage-classification risk.

4. **Test wiring (16-03 + 16-04):** xfail removed from `test_lake_worth_coverage_floor`; 3 RED tests flipped GREEN; 4 new tests (lynchpin + boundary + C5 invariant guard) now pass. Phase 11 80% C2 invariant preserved.

5. **Docs closeout (16-05):** Reference doc, STATE.md, REQUIREMENTS.md, and ROADMAP.md all updated to reflect Phase 16 Complete.

---

_Verified: 2026-05-15T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes (initial: gaps_found 3/5; re-verified: passed 5/5)_
