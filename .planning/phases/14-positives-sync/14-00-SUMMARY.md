---
phase: 14-positives-sync
plan: 00
subsystem: testing

tags: [pytest, fixtures, red-stubs, positives-sync, google-ads, keyword_view, byte-exact-golden]

# Dependency graph
requires:
  - phase: 08-account-data
    provides: perf_synth.synth_negatives_sync envelope shape (mirrored by cross_ref_positives)
  - phase: 10-operator-launch-kit
    provides: byte-exact golden CSV pattern + per-function hasattr skip-guard pattern
  - phase: 12-source-consolidation-drop-tavily
    provides: per-function _skip_unless_* pattern in shared test files
provides:
  - 4 Phase 14 test fixtures (raw keyword_view envelope, ranked_phase14, golden positives-sync, golden positives_new_to_add.csv)
  - 14 RED-via-SKIP tests across test_perf_synth.py / test_perf_fetch.py (new file) / test_render_report.py / test_export_csv.py
  - 1 PASSING Wave-0 test (render_positives_sync_section omit-when-absent via getattr-default)
  - Locked public-API contracts via hasattr sentinels for Wave 1 (14-01, 14-02) and Wave 2 (14-03, 14-04) plans
  - _FakeGAdsClient stub pattern in test_perf_fetch.py (captures GAQL query + yields synthetic rows; no respx)
affects: [14-01, 14-02, 14-03, 14-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "per-function _skip_unless_<fn>_implemented() guard preserves legacy GREEN tests in shared test files"
    - "byte-exact golden fixture (CRLF, UTF-8 no BOM, csv.QUOTE_MINIMAL) for Phase 14 positives.csv filter contract"
    - "_FakeGAdsClient stub: SimpleNamespace-backed fake of the google-ads SDK search_stream layer (no respx)"
    - "getattr(module, fn, default_lambda) pattern lets the omit-when-absent test PASS against Wave 0 while still gating the rendered-section tests behind hasattr sentinel"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-keywords-fixture.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/ranked_phase14.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/golden_positives_sync.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/golden_positives_new_to_add.csv
    - .claude/skills/google-ad-research/scripts/tests/test_perf_fetch.py
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_perf_synth.py
    - .claude/skills/google-ad-research/scripts/tests/test_render_report.py
    - .claude/skills/google-ad-research/scripts/tests/test_export_csv.py

key-decisions:
  - "test_perf_fetch.py CREATED from scratch (Rule 3 deviation: plan assumed file existed). _FakeGAdsClient + _FakeRow + _FakeBatch + _FakeGoogleAdsService stub captures GAQL query and yields rows synthesized from google-ads-keywords-fixture.json. No respx (google-ads SDK uses gRPC, not HTTP)."
  - "Fixture design seeds 5 ranked rows aligned to 4 bucket scenarios (already_active urgent-care, paused auto-accident, covered-by-broad pip-insurance vs broad pip-clinic, 2 new_to_add). Account fixture includes 1 unmatched entry (wellness exam) as sanity for the not-surfaced case."
  - "synthesized_at pinned to 2026-05-15T00:00:00Z in golden + monkeypatched at the fixture level via perf_synth._now_iso. Locks byte-exact dict equality without timezone drift."
  - "test_export_csv.py module-level pytestmark stays (gates on MODULE_INCOMPLETE = not hasattr(write_positives), currently False so 0 tests are gated). New Phase 14 tests stack a SECOND per-function gate via _skip_unless_positives_sync_filter() checking export_csv._POSITIVES_SYNC_SUPPORTED — Wave 2 14-04 must set this flag True when the filter logic lands."
  - "test_render_report.py omit-when-absent test uses getattr-default lambda → PASSES on Wave 0 (1 GREEN signal for the section feature). Other 3 section tests SKIP via hasattr-guarded _skip_unless_positives_sync_section() until Wave 2 14-03 lands the helper."
  - "Byte-exact golden_positives_new_to_add.csv: Campaign='Phase 14 Positives Sync' (derived from staged run-dir name '2026-05-15T000000Z-phase-14-positives-sync'), 2 rows (accident_chiropractor_commercial / walk_in_clinic_transactional). Tests stage cluster names verbatim to land the byte-match."

patterns-established:
  - "Per-function skip-guard layering: when a shared test file already hosts both unconditional GREEN tests and module-level pytestmark gates, new contract tests use a per-function helper to add an additional gate WITHOUT relaxing the module-level gate"
  - "Module-level sentinel for downstream contract detection: export_csv._POSITIVES_SYNC_SUPPORTED = True signals to tests that Wave 2 feature has shipped — single boolean check is more durable than argparse introspection"
  - "Hand-rolled google-ads SDK fake (no respx, no library mocks): SimpleNamespace-based stub + captured-args dict on the client instance — sufficient for query-string assertions + row-shape contract tests without pulling gRPC mocks into the dev surface"

requirements-completed: [POS-07]

# Metrics
duration: ~18min
completed: 2026-05-15
---

# Phase 14 Plan 00: Wave 0 RED Test Scaffolding Summary

**Byte-exact golden fixtures + 14 RED-via-SKIP tests lock the public API surface (cross_ref_positives, fetch_keyword_view, render_positives_sync_section, --include-existing flag) before Wave 1 implementation lands.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-15 (within session)
- **Completed:** 2026-05-15
- **Tasks:** 3
- **Files created:** 5 (4 fixtures + test_perf_fetch.py)
- **Files modified:** 3 (test_perf_synth.py / test_render_report.py / test_export_csv.py)

## Accomplishments

- 4 byte-exact data-contract fixtures (raw envelope + ranked + golden sync + golden CSV) locked
- 14 Wave-0 RED stubs SKIP cleanly on current production code; will flip to GREEN one bucket at a time as Wave 1 + Wave 2 plans land
- Per-function `_skip_unless_*` guards added in 4 shared test files — every legacy GREEN test continues to pass (242 passed, was 241 pre-Phase-14)
- Locked public-API contracts for 4 downstream plans via hasattr / getattr sentinels:
  - `perf_synth.cross_ref_positives` (Wave 1 14-02)
  - `perf_fetch.fetch_keyword_view` (Wave 1 14-01)
  - `render_report.render_positives_sync_section` (Wave 2 14-03)
  - `export_csv._POSITIVES_SYNC_SUPPORTED` + `--include-existing` flag (Wave 2 14-04)

## Task Commits

1. **Task 1: Build fixtures locking the Phase 14 data contract** — `954e4a3` (test)
2. **Task 2: Extend test_perf_synth.py + create test_perf_fetch.py with Phase 14 RED stubs** — `ae0a73f` (test)
3. **Task 3: Extend test_render_report.py + test_export_csv.py with Phase 14 RED stubs** — `71790dd` (test)

**Plan metadata:** pending (this commit)

## Files Created/Modified

### Created
- `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-keywords-fixture.json` — Raw keyword_view envelope (fetched_at + horizon_days + customer_id + 4-item array) seeding all 4 bucket scenarios + 1 unmatched
- `.claude/skills/google-ad-research/scripts/tests/fixtures/ranked_phase14.json` — 5 ranked-enriched rows aligned to the raw fixture for byte-exact cross-ref
- `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_positives_sync.json` — Byte-exact target output of cross_ref_positives (synthesized_at pinned, stats block with 5 int counts, 4 bucket lists each with status tag)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_positives_new_to_add.csv` — Byte-exact filtered positives.csv (UTF-8 no BOM, CRLF, 2 new_to_add rows)
- `.claude/skills/google-ad-research/scripts/tests/test_perf_fetch.py` — New test file with _FakeGAdsClient stub + 2 RED stubs for fetch_keyword_view (GAQL query string + item shape contract)

### Modified
- `.claude/skills/google-ad-research/scripts/tests/test_perf_synth.py` — Added 6 RED stubs (4 bucket assertions + stats block + golden fixture byte-match) guarded by `_skip_unless_cross_ref_positives()`
- `.claude/skills/google-ad-research/scripts/tests/test_render_report.py` — Added 4 tests (1 PASSES via getattr-default, 3 SKIP via `_skip_unless_positives_sync_section()`)
- `.claude/skills/google-ad-research/scripts/tests/test_export_csv.py` — Added 3 RED stubs (default filter byte-match + --include-existing + graceful fallback) guarded by `_skip_unless_positives_sync_filter()`

## Decisions Made

See `key-decisions:` frontmatter block above for the full list. Summary:

1. **Created test_perf_fetch.py from scratch (Rule 3 deviation).** Plan listed the file under `files_modified` but no such file existed in the test directory. Built a minimal `_FakeGAdsClient` / `_FakeRow` / `_FakeBatch` / `_FakeGoogleAdsService` stub from scratch using SimpleNamespace — no respx, no library mocks, no extra deps. Captures the GAQL query string passed to `search_stream` and yields synthetic rows.
2. **Pinned `synthesized_at` to 2026-05-15T00:00:00Z** in golden + monkeypatched perf_synth._now_iso at the test level → deterministic dict equality.
3. **getattr-default lambda for omit-when-absent test** lets one Wave-0 test PASS against current code (graceful-omit contract is the strongest invariant to lock first), while the other 3 section tests SKIP until Wave 2 14-03 lands the helper.
4. **Stacked skip-guards in test_export_csv.py** — module-level `pytestmark.skipif(MODULE_INCOMPLETE)` currently gates 0 tests (write_positives exists), so the new per-function `_skip_unless_positives_sync_filter()` adds a second gate without conflicting with the file-level pattern.

## Deviations from Plan

### Rule 3 — Blocking issue auto-fixed

**1. [Rule 3 - Blocking] Created test_perf_fetch.py from scratch (file did not exist)**
- **Found during:** Task 2 (Extend test_perf_synth.py + test_perf_fetch.py)
- **Issue:** Plan's `files_modified` listed `test_perf_fetch.py` and `<action>` block said "Inspect the existing tests for the mocking pattern (likely a `_FakeGAdsClient` / `_StubSearchStream` helper)". No test_perf_fetch.py exists in `.claude/skills/google-ad-research/scripts/tests/`. No existing fake-GAds-client pattern in the test suite (grep across all tests/ returned 0 matches for FakeGAdsClient / search_stream / GoogleAdsService / StubSearch).
- **Fix:** Built test_perf_fetch.py from scratch with a minimal stub pattern (_FakeGAdsClient + _FakeRow + _FakeBatch + _FakeGoogleAdsService). The stub is self-contained — SimpleNamespace-backed, captures GAQL query on a dict on the client, yields rows synthesized from google-ads-keywords-fixture.json. No respx (google-ads SDK is gRPC). No extra dependencies.
- **Files modified:** .claude/skills/google-ad-research/scripts/tests/test_perf_fetch.py (created)
- **Verification:** `pytest test_perf_fetch.py -v` → 2 SKIPPED (Wave 1 14-01 not yet landed). Module imports cleanly, fake client surface matches perf_fetch.fetch_search_terms's actual usage (`client.get_service("GoogleAdsService").search_stream(customer_id=..., query=...)`).
- **Committed in:** ae0a73f (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking)
**Impact on plan:** The missing test file would have prevented Task 2 from completing per the plan's contract; building it from scratch using a documented stub pattern is strictly better than skipping the perf_fetch RED stubs. The new file is committed and ready for Wave 1 14-01 to flip the SKIPs to GREEN.

## Issues Encountered

- **Python `_` digit separators in JSON.** First draft of `ranked_phase14.json` + `google-ads-keywords-fixture.json` used `4_200_000` (legal Python int literal, illegal JSON). Caught at validation time, stripped underscores via a regex sweep. Files now parse cleanly.

## Self-Check

- Files exist: 4 fixtures + 1 new test file + 3 modified test files → all confirmed via tests/full-suite run
- Commits found in `git log --oneline`: `954e4a3`, `ae0a73f`, `71790dd`
- Full test suite: **242 passed, 14 skipped** (was 241 passed pre-Phase-14; one new omit-when-absent test PASSES, 13 + 1 stacking from new file = 14 SKIP)

## Self-Check: PASSED

## Next Phase Readiness

- Wave 1 plans (14-01 perf_fetch, 14-02 perf_synth) can implement against locked fixtures + RED stubs
- Wave 2 plans (14-03 render_report, 14-04 export_csv) inherit byte-exact golden CSV + section markdown contract
- `_POSITIVES_SYNC_SUPPORTED` sentinel + `_now_iso` monkeypatch hook + `_FakeGAdsClient` stub all in place for downstream tests to flip RED-via-SKIP → GREEN one bucket at a time

---
*Phase: 14-positives-sync*
*Completed: 2026-05-15*
