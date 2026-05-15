---
phase: 14-positives-sync
plan: 01
subsystem: perf-fetch

tags: [google-ads, gaql, keyword_view, perf_fetch, oauth, positives-sync, pos-01]

# Dependency graph
requires:
  - phase: 08-account-data
    provides: perf_fetch.fetch_search_terms / fetch_perf / fetch_existing_negatives + lib.gads_client + lib.config + _date_literal helper + main_with_args try-block layout
  - phase: 14-positives-sync
    provides: Wave 0 RED tests + _FakeGAdsClient stub + google-ads-keywords-fixture.json fixture
provides:
  - perf_fetch.fetch_keyword_view(client, customer_id, *, days=30) -> list[dict]
  - raw/google-ads-keywords.json write inside main_with_args
  - keyword_count stdout JSON summary field
  - 2 Wave 0 RED tests flipped SKIP → PASS (test_fetch_keyword_view_gaql_query + test_perf_fetch_writes_google_ads_keywords_json)
affects: [14-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "fetch_keyword_view mirrors fetch_search_terms line-for-line (same client surface, same date literal, same enum .name pattern, same envelope shape) — inherits Phase 8's proven hardness"
    - "GAQL keyword_view query lives unindented inside f-string — operator-readable, status filter inline ('REMOVED' single-quoted to match Google Ads literal syntax)"
    - "No LIMIT on keyword_view query — account-wide kw lists are bounded; mirrors fetch_perf's no-LIMIT campaigns query"
    - "Raw envelope: {fetched_at, horizon_days, customer_id, items} — verbatim shape of google-ads-search-terms.json + Wave 0 fixture"
    - "kws fetch nested inside SAME try-block as 3 existing fetches — single GoogleAdsException + generic Exception handler at function bottom; one auth/network failure mode for the whole script"

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/scripts/perf_fetch.py

key-decisions:
  - "No per-keyword cost_usd derived field in fetch_keyword_view (unlike fetch_search_terms which emits both cost_micros + cost_usd) — keep raw faithful to API; perf_synth.cross_ref_positives does USD math downstream if needed. Plan 14-01 action block explicitly mandated this faithfulness."
  - "fetch_keyword_view inserted AFTER fetch_existing_negatives and BEFORE main_with_args — preserves the existing function declaration ordering and matches plan instruction. Wired in main_with_args AFTER the negatives block (same try-block, separate log line) so the 4th fetch slots in cleanly without restructuring the function."
  - "stdout JSON summary key ordering: keyword_count placed after existing_negatives_count and BEFORE customer_id — matches plan's explicit ordering in interfaces block, preserving downstream parser stability if anyone ever indexed by position."
  - "Wave 0 _FakeGAdsClient fixture machinery (built in 14-00) consumed verbatim — fixture's _FakeRow + SimpleNamespace pattern surfaces ad_group_criterion.keyword.match_type.name and ad_group_criterion.status.name exactly as the production code accesses them. No fixture or stub edits needed in 14-01."

requirements-completed: [POS-01]

# Metrics
duration: ~2min
completed: 2026-05-15
---

# Phase 14 Plan 01: perf_fetch.fetch_keyword_view Summary

**Adds a GAQL `keyword_view` puller to `perf_fetch.py` — writes `raw/google-ads-keywords.json` alongside the existing 3 Google Ads raw files; upstream input for Plan 14-02's `cross_ref_positives`.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-15T12:23:32Z
- **Completed:** 2026-05-15T12:25:02Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `fetch_keyword_view(client, customer_id, *, days=30) -> list[dict]` landed in `perf_fetch.py` mirroring `fetch_search_terms` exactly
- GAQL query verbatim from CONTEXT.md decision block: `FROM keyword_view WHERE segments.date DURING LAST_30_DAYS AND ad_group_criterion.status != 'REMOVED'` — selects all 10 required fields
- `main_with_args` writes `raw/google-ads-keywords.json` with `{fetched_at, horizon_days, customer_id, items}` envelope alongside the existing 3 Google Ads raw writes
- Stdout JSON summary gains `keyword_count` field (5 counts now: search_terms / campaigns / ad_groups / existing_negatives / keyword)
- 2 Wave 0 RED tests in `test_perf_fetch.py` flipped SKIP → PASS:
  - `test_fetch_keyword_view_gaql_query` — asserts FROM/DURING/status-filter substrings
  - `test_perf_fetch_writes_google_ads_keywords_json` — asserts item shape contract (10 locked keys, enum names not enums)
- Full test suite: 244 passed, 12 skipped (was 242 + 14 pre-Plan-14-01; 0 regressions)
- POS-01 satisfied — raw/google-ads-keywords.json now downstream-available for cross_ref_positives (Plan 14-02)

## Task Commits

1. **Task 1: Add fetch_keyword_view function** — `d8ade67` (feat) — function definition only
2. **Task 2: Wire into main_with_args + stdout summary** — `33f36e5` (feat) — raw write + stdout key

**Plan metadata:** pending (this commit)

## Files Created/Modified

### Modified
- `.claude/skills/google-ad-research/scripts/perf_fetch.py` — +54 lines (43 for fetch_keyword_view function, 11 for main_with_args wiring + stdout summary)

## Decisions Made

See `key-decisions:` frontmatter for the full list. Summary:

1. **No cost_usd derived field** in `fetch_keyword_view` items — keep raw faithful to API; perf_synth does USD math downstream if needed.
2. **fetch_keyword_view declared between fetch_existing_negatives and main_with_args** — preserves source ordering; matches plan's `<action>` block placement.
3. **kws block wired inside the existing try** — single GoogleAdsException + generic Exception handler for the whole script; no separate error-handling tree.
4. **keyword_count stdout key ordered after existing_negatives_count, before customer_id** — preserves downstream parser stability against the existing 4-count ordering.

## Deviations from Plan

**None** — plan executed exactly as written.

## Issues Encountered

None. Wave 0 fixtures + _FakeGAdsClient stub + the keyword-view fixture were already in place from Plan 14-00, so Task 1's GAQL substring assertion + Task 2's shape contract assertion both flipped GREEN on first run.

## Self-Check

- File exists: `.claude/skills/google-ad-research/scripts/perf_fetch.py` — confirmed modified (5 hits across `fetch_keyword_view` / `FROM keyword_view` / `google-ads-keywords.json` / `keyword_count`)
- Commits found in `git log`: `d8ade67`, `33f36e5` — both present
- Targeted test: `test_perf_fetch.py::test_fetch_keyword_view_gaql_query PASSED`, `test_perf_fetch_writes_google_ads_keywords_json PASSED`
- Full test suite: 244 passed, 12 skipped (delta +2 PASS, -2 SKIP vs pre-plan baseline)

## Self-Check: PASSED

## Next Phase Readiness

- Plan 14-02 (`perf_synth.cross_ref_positives`) can now consume `raw/google-ads-keywords.json` — envelope shape locked, item key contract enforced by tests
- The remaining 12 Wave 0 SKIPs in the suite are gated on Wave 1 14-02 (cross_ref_positives — 6 tests) and Wave 2 14-03 / 14-04 (render section + CSV filter — 6 tests)
- No follow-up cleanup required; perf_fetch.py is feature-complete for the v1.4 positives-sync pipeline

---
*Phase: 14-positives-sync*
*Completed: 2026-05-15*
