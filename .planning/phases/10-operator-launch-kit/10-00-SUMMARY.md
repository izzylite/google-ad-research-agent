---
phase: 10-operator-launch-kit
plan: 00
subsystem: testing
tags: [pytest, csv, golden-bytes, red-stubs, fixtures, module-missing-guard]

# Dependency graph
requires:
  - phase: 09-campaign-economics-and-compliance
    provides: ranked-enriched.json schema with suggested_max_cpc_micros; forecast.json campaign_totals.daily_spend_mid_usd; compliance-flags.json matched_verticals[].verification_url
provides:
  - test_export_csv.py (14 functions, 23 test cases via parametrize) covering EXPT-01..04
  - test_render_report.py extension (12 new functions) covering STEP-01..04 + CMPL-05 + EXPT-05 (scaffolded)
  - 7 Phase 10 JSON fixtures (negatives mixed/empty, clusters with all-null CPC subset, forecast with mid-spend, compliance with-match/two-verticals/empty)
  - 3 byte-exact golden CSVs (no BOM, CRLF, Editor v2.x headers, deterministic 'Phase 10 Test Brief' Campaign)
  - export_csv.py MODULE_MISSING-style stub exposing POSITIVES/NEGATIVES/AD_GROUPS headers + TIER_TO_LEVEL + MATCH_TYPE_TITLECASE constants
affects: [10-01-bid-and-csv-writer, 10-02-next-steps-render, 10-03-export-section-and-integration]

# Tech tracking
tech-stack:
  added: []  # zero new dependencies — pure stdlib + existing pytest stack
  patterns:
    - "Per-function hasattr-guard skip (vs file-level pytestmark) for incremental extension of GREEN-already test files"
    - "Byte-exact golden fixture comparison for CSV byte contracts (no BOM, CRLF, Editor v2.x exact header bytes)"
    - "MODULE_INCOMPLETE sentinel via hasattr(module, 'helper_name') — stub ships before tests, tests skip until helper exists"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/export_csv.py (stub)
    - .claude/skills/google-ad-research/scripts/tests/test_export_csv.py
    - .claude/skills/google-ad-research/scripts/tests/fixtures/negatives_phase10.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/negatives_empty.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/clusters_phase10.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/forecast_phase10.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/compliance_with_match.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/compliance_two_verticals.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/compliance_empty.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/golden_positives.csv
    - .claude/skills/google-ad-research/scripts/tests/fixtures/golden_negatives.csv
    - .claude/skills/google-ad-research/scripts/tests/fixtures/golden_ad_groups.csv
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_render_report.py (appended ~310 lines, preserved all existing GREEN cases)

key-decisions:
  - "Stub-then-guard pattern (Phase 9 09-01 / 09-03 prior art) — export_csv.py ships in Wave 0 with header constants + a NotImplementedError main(), so test_export_csv.py can import the module cleanly; MODULE_INCOMPLETE trips on absence of write_positives, keeping every test SKIPPED until Wave 1"
  - "Per-function hasattr guard on test_render_report.py extension (vs file-level pytestmark) — necessary because the file already hosts GREEN Phase 6 + Phase 9 tests; new STEP-* and CMPL-05 tests skip individually while legacy keeps running"
  - "Byte-exact golden CSV fixtures encode the EXACT bytes Wave 1's csv.DictWriter must emit (no BOM, CRLF, RFC 4180 quoting) — the strongest Nyquist signal for Editor-importable v2.x format; single-byte drift fails the assert"
  - "Campaign column literal 'Phase 10 Test Brief' is the title-cased 'phase-10-test-brief' fixture slug — locked in fixtures so Wave 1 has zero string-derivation ambiguity"
  - "Informational cluster (grocery_delivery_basics_informational) intentionally seeded with all-null cpc_micros — exercises the BIDS-02 fallback path and the 0.00-not-blank Default Max CPC rule (Pitfall 10) without needing a synthetic test-only cluster"
  - "Combined-verticals fixture (compliance_two_verticals.json) carries TWO matched verticals so the CMPL-05 ONE-combined-step rule can be asserted directly (not by inference)"

patterns-established:
  - "Pattern: byte-exact CSV golden — `assert run_dir.read_bytes() == fixtures/golden_<name>.csv.read_bytes()`. Catches BOM drift, encoding drift, CRLF drift, header-cell drift, and column-order drift in one parametrized test."
  - "Pattern: per-function hasattr-skip in shared test files — `if not hasattr(module, 'helper'): pytest.skip('...not yet implemented (Wave N)')`. Preserves GREEN legacy while adding RED stubs."
  - "Pattern: header constants live in the stub, not the test — POSITIVES_HEADERS etc. ship in export_csv.py Wave 0 so Wave 1 has zero header-string ambiguity and tests reference `export_csv.POSITIVES_HEADERS` (single source of truth)."

requirements-completed: []  # 10-00 ships RED scaffolding only.
# The plan frontmatter listed [EXPT-01..05, STEP-01..04, CMPL-05] but those
# requirements describe GREEN contracts (export_csv.main writes the CSVs;
# render_report.render_next_steps_section returns the substituted list;
# build_report_json emits next_steps[]). Wave 0 ships none of those — it
# ships *test scaffolding that skips until Wave 1 lands the contracts*.
# REQUIREMENTS.md and the traceability matrix stay Pending until each
# Wave 1+ plan flips its target requirement(s) GREEN.

# Metrics
duration: ~25 min
completed: 2026-05-14
---

# Phase 10 Plan 00: Wave 0 RED Scaffolding Summary

**RED test scaffolding for Operator Launch Kit — 14 new export_csv tests + 12 next-steps/compliance tests, 7 JSON fixtures, 3 byte-exact golden CSVs, and an export_csv.py stub with locked header contracts. Suite goes 159→202 tests, all new ones SKIPPED via hasattr guards; zero collection errors; zero regressions on the 149 legacy GREEN tests.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-14T19:42:24Z
- **Completed:** 2026-05-14T20:07:00Z (approx)
- **Tasks:** 2 / 2
- **Files created:** 12
- **Files modified:** 1 (test_render_report.py)

## Accomplishments

- Phase 10 Wave 1+ planners can now write `<automated>` verify commands that reference files already on disk — every EXPT-* and STEP-* test name exists in the test suite as a SKIPPED stub.
- Byte-exact golden CSVs lock the Editor v2.x format (UTF-8 no BOM, CRLF, exact header strings, RFC 4180 quoting) one wave before Wave 1 writes the actual `csv.DictWriter` calls.
- `export_csv.py` ships its header constants, tier→level map, and match-type title-case map in the stub — Wave 1 inherits these as single-source-of-truth and cannot drift.
- Full suite: 149 passed, 53 skipped (43 new Phase 10 stubs + 10 pre-existing module-missing skips), 0 failed, 0 collection errors.

## Task Commits

Each task was committed atomically:

1. **Task 1: Phase 10 fixtures + export_csv.py MODULE_MISSING stub** — `815988c` (feat)
2. **Task 2: RED test scaffolding — test_export_csv.py + test_render_report.py extension** — `3bdbcc7` (test)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/export_csv.py` — Wave 0 stub: PEP 723 metadata, POSITIVES/NEGATIVES/AD_GROUPS headers, TIER_TO_LEVEL, MATCH_TYPE_TITLECASE, `main()` raising NotImplementedError.
- `.claude/skills/google-ad-research/scripts/tests/test_export_csv.py` — 14 test functions (4 parametrized → 23 test cases) for EXPT-01..04: positives/negatives/ad_groups headers + rows + Max CPC format + Match Type title-case + empty input + Tier→Level + cluster-median CPC + Status=Enabled + byte contract (BOM/CRLF/round-trip/golden bytes) + exit codes 0/3.
- `.claude/skills/google-ad-research/scripts/tests/test_render_report.py` — extended in place (~310 lines appended): STEP-01..04 (Next-Steps section default order / substitution / SHA-1 step IDs / positional n / report.json next_steps[]), STEP-03 HTML (section exists / localStorage namespacing / step text escaping), CMPL-05 (single-vertical reorder / combined-two-verticals / no-compliance standard order), EXPT-05 (Wave 2 stubs: Export Files markdown + report.json exports[]).
- `.claude/skills/google-ad-research/scripts/tests/fixtures/negatives_phase10.json` — 5 negatives spanning Strong / Considered / Investigate tiers, with `match_type` and `cluster` keys for full level + ad-group assertion coverage.
- `.claude/skills/google-ad-research/scripts/tests/fixtures/negatives_empty.json` — `[]`, drives the header-only CSV test (Pitfall 4).
- `.claude/skills/google-ad-research/scripts/tests/fixtures/clusters_phase10.json` — 3 clusters, 8 keywords; informational cluster has all-null suggested CPC (Pitfall 10 fixture).
- `.claude/skills/google-ad-research/scripts/tests/fixtures/forecast_phase10.json` — campaign_totals.daily_spend_mid_usd = 12.50, per-cluster bands, full methodology block.
- `.claude/skills/google-ad-research/scripts/tests/fixtures/compliance_with_match.json` — 1 matched vertical (medical) for CMPL-05 reorder test.
- `.claude/skills/google-ad-research/scripts/tests/fixtures/compliance_two_verticals.json` — 2 matched verticals (medical + legal) for CMPL-05 combined-step rule test.
- `.claude/skills/google-ad-research/scripts/tests/fixtures/compliance_empty.json` — empty matched_verticals[] for standard-order baseline.
- `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_positives.csv` — 806 bytes; 8 data rows + header; Campaign='Phase 10 Test Brief'; CRLF; no BOM.
- `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_negatives.csv` — 450 bytes; 5 data rows + header; Strong-tier rows have empty Ad Group; Considered/Investigate rows carry cluster name verbatim.
- `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_ad_groups.csv` — 244 bytes; 3 rows (one per cluster); Status=Enabled; Default Max CPC = 0.46 / 0.14 / 0.00.

## Decisions Made

See `key-decisions` in frontmatter. The four highest-leverage:

1. **Stub-then-guard** (mirrors Phase 9 09-01 / 09-03 prior art) — `export_csv.py` ships in Wave 0 with locked constants + a `NotImplementedError`-raising `main()`. Tests `try: import export_csv` succeeds; `MODULE_INCOMPLETE = not hasattr(export_csv, 'write_positives')` is the GREEN signal. This is strictly better than absent-module guarding because it lets us version the header contracts and the tier-map in source from day 1.
2. **Per-function hasattr guard for test_render_report.py extension** — file-level `pytestmark` would have skipped the existing 23 Phase 6/9 GREEN tests. Per-function `_skip_unless_next_steps()` + `_skip_unless_export_section()` keep legacy GREEN while new Phase 10 stubs skip individually.
3. **Byte-exact golden CSV comparison** — `assert got_bytes == golden_bytes` is the single most-discriminating Nyquist signal for Editor-importable v2.x format. One assert catches BOM drift + encoding drift + CRLF drift + header-cell drift + column-order drift + cell-value drift in one shot. The three goldens were generated via `csv.DictWriter(lineterminator='\r\n')` so Wave 1 has a known-good byte target.
4. **Deterministic Campaign literal** — fixture run-dir name `2026-05-14T120000Z-phase-10-test-brief` → `_derive_brief_slug` → `"phase-10-test-brief"` → title-cased to `"Phase 10 Test Brief"`. Locked in the goldens so Wave 1's slug-derivation cannot accidentally diverge.

## Deviations from Plan

None - plan executed exactly as written.

The plan listed 14 EXPT-* tests and ~10 STEP-* / CMPL-05 / EXPT-05 tests; final counts:
- `test_export_csv.py`: 14 distinct functions, 23 test-case invocations (4 functions parametrized over 3 CSV names).
- `test_render_report.py` extension: 12 functions covering STEP-01..04 + 3 CMPL-05 cases + 2 EXPT-05 scaffolds.

Both end up at-or-above the plan's "~14" / "~10" targets. No scope creep.

## Issues Encountered

None.

## Next Phase Readiness

- **Wave 1 (plan 10-01 + 10-02) can start in parallel.** EXPT-01..04 tests reference `export_csv.write_positives` / `write_negatives` / `write_ad_groups` / `main` — Wave 1 ships these to flip all 23 EXPT cases from SKIPPED to PASSED. STEP-01..04 + CMPL-05 tests reference `render_report.render_next_steps_section` and a `next_steps` kwarg on `build_report_json` — Wave 1's render_report extension flips those.
- **Wave 2 (plan 10-03) ships render_export_section + exports[] kwarg** — the two EXPT-05 stub tests in `test_render_report.py` are already in place and will flip GREEN.
- **No blockers.** All Wave 0 invariants satisfied: pytest collects cleanly (zero errors), the existing 149 GREEN tests still pass, the 43 new tests skip with informative reasons that name the responsible Wave + plan.

## Self-Check: PASSED

Verified:
- All 12 created files exist on disk (11 new + 1 modified).
- Both commits (`815988c`, `3bdbcc7`) present in `git log`.
- Suite collection produces 202 tests, zero errors.
- All 43 new Phase 10 tests skip with `MODULE_INCOMPLETE` / hasattr reasons.
- The 149 legacy GREEN tests still pass (verified via `pytest ... -q` full-suite run prior to Task 2 commit).
- The 3 golden CSVs encode no BOM (`bytes[:3] != b'\xef\xbb\xbf'`) and contain CRLF (`b'\r\n' in bytes`).
- `import export_csv` succeeds; `export_csv.POSITIVES_HEADERS == ['Campaign', 'Ad Group', 'Keyword', 'Match Type', 'Max CPC', 'Final URL']`; `export_csv.main([])` raises NotImplementedError.

---
*Phase: 10-operator-launch-kit*
*Completed: 2026-05-14*
