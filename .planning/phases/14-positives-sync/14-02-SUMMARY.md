---
phase: 14-positives-sync
plan: 02
subsystem: perf-synth

tags: [perf_synth, cross_ref_positives, positives-sync, pos-02, pos-05, pos-07, graceful-skip, golden-fixture]

# Dependency graph
requires:
  - phase: 08-account-data
    provides: synth_negatives_sync envelope shape + _norm_neg semantics + main_with_args negatives-block layout
  - phase: 14-positives-sync
    provides: Wave 0 RED tests + golden_positives_sync.json + google-ads-keywords-fixture.json + ranked_phase14.json
  - phase: 14-positives-sync
    provides: raw/google-ads-keywords.json writer (Plan 14-01 fetch_keyword_view)
provides:
  - perf_synth.cross_ref_positives(ranked, existing_kws) -> dict (4 buckets + stats)
  - perf_synth._norm_kw helper (single source of keyword canonicalization; _norm_neg aliased)
  - main_with_args writes {run_dir}/positives-sync.json when raw/google-ads-keywords.json + ranked-enriched.json (or ranked.json) present
  - POS-05 graceful skip when raw/google-ads-keywords.json absent (no error, no file)
  - 5 new stdout JSON summary keys: positives_sync_path, positives_our_total, positives_already_active, positives_paused, positives_new_to_add
  - 6 Wave 0 cross_ref_positives tests flipped SKIP -> PASS (incl. golden byte-match)
affects: [14-03, 14-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single normalisation rule shared across negatives + positives sync via _norm_kw + _norm_neg alias — both sync directions canonicalize keyword text identically"
    - "4-bucket priority chain (ENABLED exact > PAUSED exact > ENABLED BROAD token-superset > new) — each ranked kw lands in exactly one bucket; explicit early-continue rather than nested if/else"
    - "covered_by_broad token-set heuristic with min-2-token guard — frozenset.issubset comparison; avoids single-token false positives like 'insurance' generating mass false-coverage tags"
    - "Symmetric main_with_args block placement: positives-sync block sits after negatives-sync block, mirrors load-then-write pattern, shares the same exit-3 IO error handling"
    - "POS-05 graceful skip: file-presence check gates the whole block; absent input is normal flow, not an error"

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/scripts/perf_synth.py

key-decisions:
  - "_norm_neg = _norm_kw alias chosen over copy-paste — single source of canonicalization avoids future drift between negatives and positives sync; existing 4 negatives tests stay GREEN unchanged"
  - "Bucket priority encoded via early-continue chain (not nested conditionals) — ENABLED-exact wins over PAUSED-exact wins over BROAD-cover wins over new. Order matches golden_positives_sync.json which was authored against this exact ordering in Wave 0."
  - "covered_by_broad min-token guard set at >= 2 tokens (per plan's locked Claude-Discretion area). Single-token broad-match account kws (e.g. 'clinic') would otherwise tag every ranked kw containing that token as covered — catastrophic false-positive rate."
  - "ranked-enriched.json preferred over ranked.json (Phase 9+ enriched layer carries suggested_max_cpc_micros + cpc_micros; downstream Plan 14-04 CSV filter wants those fields preserved in positives-sync.json buckets)."
  - "Empty-keyword ranked rows tagged new_to_add (defensive fall-through) rather than dropped — keeps our_total stat equal to len(ranked) which the stats-block test asserts."

requirements-completed: [POS-02, POS-05]

# Metrics
duration: ~2min
completed: 2026-05-15
---

# Phase 14 Plan 02: cross_ref_positives Summary

**Adds `cross_ref_positives` to `perf_synth.py` — the structural heart of Phase 14. Cross-references ranked keywords against `raw/google-ads-keywords.json` and writes `positives-sync.json` with 4 buckets (`already_active`, `paused_in_account`, `covered_by_broad`, `new_to_add`) + a 5-count stats block. POS-05 graceful skip preserves no-OAuth path.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-15T12:32:44Z
- **Completed:** 2026-05-15T12:34:36Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `_norm_kw` extracted as single source of keyword canonicalization; `_norm_neg = _norm_kw` alias keeps existing negatives-sync code + tests untouched
- `cross_ref_positives(ranked, existing_kws) -> dict` lands with 4-bucket envelope + 5-count stats block matching `golden_positives_sync.json` byte-for-byte
- Bucket priority chain: ENABLED-exact > PAUSED-exact > ENABLED-BROAD token-superset (>= 2 tokens) > new_to_add; each ranked kw lands in exactly one bucket
- `main_with_args` extended with symmetric positives-sync block after the existing negatives-sync block; reads `raw/google-ads-keywords.json` + `ranked-enriched.json` (fallback `ranked.json`), writes `{run_dir}/positives-sync.json`
- POS-05 graceful skip: when `raw/google-ads-keywords.json` is absent, no error surfaces and no `positives-sync.json` is written — verified by manual smoke
- Stdout JSON summary gains 5 keys: `positives_sync_path`, `positives_our_total`, `positives_already_active`, `positives_paused`, `positives_new_to_add`
- 6 Wave 0 RED tests in `test_perf_synth.py` flipped SKIP -> PASS:
  - `test_cross_ref_positives_already_active`
  - `test_cross_ref_positives_paused_in_account`
  - `test_cross_ref_positives_covered_by_broad`
  - `test_cross_ref_positives_new_to_add`
  - `test_cross_ref_positives_stats_block`
  - `test_cross_ref_positives_golden_fixture_byte_match`
- Full test suite: **250 passed, 6 skipped** (was 244 passed, 12 skipped pre-plan; +6 PASS / -6 SKIP, 0 regressions)
- POS-02 + POS-05 satisfied — `positives-sync.json` is now downstream-available for Plan 14-03 (render) and Plan 14-04 (export filter)

## Task Commits

1. **Task 1: Implement cross_ref_positives + _norm_kw helper** — `306d522` (feat)
2. **Task 2: Wire main_with_args + POS-05 graceful skip + stdout summary keys** — `6e73321` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified

### Modified
- `.claude/skills/google-ad-research/scripts/perf_synth.py` — +122 lines (88 for `_norm_kw` extraction + `cross_ref_positives` function; 34 for main_with_args wiring + stdout summary expansion)

## Decisions Made

See `key-decisions:` frontmatter for the full list. Summary:

1. **`_norm_neg = _norm_kw` alias** — single source of canonicalization; zero behaviour change for existing negatives-sync flow.
2. **Bucket priority via early-continue chain** — matches the golden fixture's authored order (ENABLED-exact > PAUSED-exact > BROAD-cover > new).
3. **`covered_by_broad` min-2-token guard** — locked by plan (Claude's Discretion); avoids catastrophic single-token broad-match false positives.
4. **`ranked-enriched.json` preferred over `ranked.json`** — Phase 9 enrichment fields (`suggested_max_cpc_micros`, `cpc_micros`) need to be preserved through to downstream CSV export.
5. **Empty-keyword defensive fall-through to `new_to_add`** — keeps `stats.our_total == len(ranked)` invariant intact.

## Deviations from Plan

**None** — plan executed exactly as written. Bucket priority order in the implementation matched the golden fixture's encoded order on first run; no golden edit needed.

## Issues Encountered

None. Wave 0 fixtures + RED stubs + golden byte-match all wired correctly in Plan 14-00; both Task 1 (function) and Task 2 (wiring + graceful skip) passed targeted tests on first run.

## Self-Check

- File exists: `.claude/skills/google-ad-research/scripts/perf_synth.py` — confirmed modified (cross_ref_positives + _norm_kw + main_with_args positives-block present)
- Commits found in `git log --oneline -5`: `306d522` (Task 1), `6e73321` (Task 2) — both present
- Targeted tests: 10/10 PASSED in `test_perf_synth.py` (4 legacy + 6 new)
- Full test suite: **250 passed, 6 skipped** — delta +6 PASS, -6 SKIP vs pre-plan baseline; 0 regressions
- Smoke: happy path writes `positives-sync.json` with correct stats; graceful-skip path exits 0 with no file when `google-ads-keywords.json` absent

## Self-Check: PASSED

## Next Phase Readiness

- Plan 14-03 (`render_report.render_positives_sync_section`) can now consume `positives-sync.json` — 4-bucket envelope + stats locked; 3 RED stubs in `test_render_report.py` await Wave 2.
- Plan 14-04 (`export_csv` filter + `--include-existing` flag) can now read `positives-sync.json` to filter `positives.csv` to `new_to_add` by default — `_POSITIVES_SYNC_SUPPORTED` sentinel hook + 3 RED stubs in `test_export_csv.py` await Wave 2.
- Remaining 6 SKIPs in suite are all gated on Wave 2 plans 14-03 (3 section tests) + 14-04 (3 filter tests).

---
*Phase: 14-positives-sync*
*Completed: 2026-05-15*
