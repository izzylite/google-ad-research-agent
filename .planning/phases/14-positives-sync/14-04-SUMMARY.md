---
phase: 14-positives-sync
plan: 04
subsystem: export-csv

tags: [export_csv, positives-sync, pos-04, pos-05, include-existing-flag, status-column, graceful-fallback]

# Dependency graph
requires:
  - phase: 10-operator-ready-output
    provides: export_csv.py byte-exact CSV writers + POSITIVES_HEADERS contract + _build_positives_rows joiner
  - phase: 11-account-structure-mapping
    provides: _load_ad_group_mapping optional-sidecar pattern (mirrored for positives-sync)
  - phase: 14-positives-sync
    provides: Wave 0 RED stubs in test_export_csv (3 Phase 14 tests + _POSITIVES_SYNC_SUPPORTED sentinel hook)
  - phase: 14-positives-sync
    provides: positives-sync.json schema + buckets (Plan 14-02 cross_ref_positives)
provides:
  - export_csv._load_positives_sync helper (optional positives-sync.json reader)
  - export_csv._POSITIVES_SYNC_SUPPORTED = True module sentinel
  - --include-existing CLI flag (action=store_true, default=False)
  - _build_positives_rows positives_sync + include_existing kwargs
  - write_positives include_status kwarg (appends Status column)
  - Default filter: positives.csv contains ONLY new_to_add rows when sync present
  - --include-existing path: all ranked rows + trailing Status column tagging bucket
  - POS-05 graceful fallback: full ranked list when positives-sync.json absent
  - stdout JSON summary gains positives_filter key (new_to_add | include_existing | no_sync_full_list)
  - 3 Wave 0 export_csv Phase 14 RED stubs flipped SKIP → PASS
affects: [14-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-sidecar pattern reuse: _load_positives_sync mirrors _load_ad_group_mapping line-for-line — file-presence gate + try/except JSONDecodeError|OSError → None. Single canonical shape for sidecar readers in this script."
    - "Filter-mode derivation in main: 3-branch ladder (no_sync_full_list | include_existing | new_to_add) computed once from (positives_sync, args.include_existing) then threaded through both _build_positives_rows AND write_positives. Single source of truth for filter state."
    - "Bucket priority preserved in bucket_by_kw build: new_to_add inserted FIRST so already_active/paused/covered_by_broad don't overwrite a kw that the sync surfaces in multiple buckets. Defensive against future cross_ref_positives changes."
    - "Status column path uses include_status kwarg on write_positives — header list mutation localised to the writer; row-builder emits a payload dict with the Status key only when needed; QUOTE_MINIMAL byte contract preserved unchanged for the 6-column default path."

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/scripts/export_csv.py

key-decisions:
  - "Single atomic commit covering both Task 1 (sentinel + helper + flag) and Task 2 (filter logic). Rationale: Wave 0 tests only flip GREEN when ALL of (sentinel, flag, filter, status column) land — splitting into two commits would leave the intermediate commit in a failing-tests state which violates the per-task commit invariant 'every commit passes its targeted tests'. Per-task hash discipline (Task 1 sentinel, Task 2 filter) is preserved in the commit message bullets."
  - "Defensive 'Status' = 'new_to_add' fallback when --include-existing surfaces a ranked kw not in any sync bucket. Alternative was empty-string or 'unknown' — chose new_to_add because cross_ref_positives is the authoritative tagger and any unbucketed kw indicates our ranked list grew between perf_synth and export_csv (small race window) — treating as new is the safest operator default."
  - "Parallel-wave commit hygiene: explicit git add of export_csv.py only — render_report.py was concurrently modified by Plan 14-03. Avoided absorbing 14-03's working-tree changes (per Phase 12 12-03 precedent: parallel-wave shared-config files need explicit per-path staging)."
  - "bucket_by_kw populated in priority order with first-write-wins semantics — 'if kw_lc not in bucket_by_kw' guard preserves the canonical priority (ENABLED-exact > PAUSED-exact > BROAD-cover > new) defined by cross_ref_positives even if a hypothetical sync surfaces a kw in multiple buckets."
  - "Re-used existing (Ad Group asc, Score desc) sort untouched — Status column is added INSIDE the payload before sorting, not as a sort-key, so the byte-exact contract with golden_positives_new_to_add.csv (which sorts accident_chiropractor_commercial before walk_in_clinic_transactional alphabetically) holds without filter-mode-specific sort logic."

requirements-completed: [POS-04, POS-05]

# Metrics
duration: ~3 min
completed: 2026-05-15
---

# Phase 14 Plan 04: export_csv positives-sync filter + --include-existing flag Summary

**Extends `export_csv.py` to filter `positives.csv` to `new_to_add` rows when `positives-sync.json` is present (default), with `--include-existing` flag as the backward-compat escape hatch (7-column Status path). POS-05 graceful fallback preserves pre-Phase-14 full-ranked-list behaviour when sync absent. 3 Wave 0 RED stubs flipped GREEN; full suite 256 passed.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-15T12:37:46Z
- **Completed:** 2026-05-15T12:40:20Z
- **Tasks:** 2 (committed as a single atomic feat — see Decisions)
- **Files modified:** 1

## Accomplishments

- `_POSITIVES_SYNC_SUPPORTED = True` module sentinel added directly under the existing drift-guard asserts — Wave 0 test skip-guards now flip via `getattr(export_csv, "_POSITIVES_SYNC_SUPPORTED", False)`.
- `_load_positives_sync(run_dir) -> dict | None` helper added — mirrors `_load_ad_group_mapping` line-for-line (file-presence gate + try/except → None).
- `--include-existing` argparse flag (`action="store_true"`, `default=False`) wired into `main`.
- `_build_positives_rows` extended with `positives_sync: dict | None = None` + `include_existing: bool = False` kwargs:
  - Default path (sync present, flag absent): drops every ranked row whose keyword is NOT in `sync['new_to_add']` (case-insensitive).
  - `--include-existing` path: emits all rows + appends `"Status": bucket_name` to the payload dict.
  - Sync absent: pre-Phase-14 behaviour preserved (no filter, no Status column).
- `write_positives` extended with `include_status: bool = False` kwarg — appends `"Status"` to the headers list when True; CSV byte contract (CRLF, UTF-8 no BOM, QUOTE_MINIMAL) unchanged.
- `main` derives `filter_mode` (`no_sync_full_list` | `include_existing` | `new_to_add`) once and threads it through both `_build_positives_rows` and `write_positives`.
- Stdout JSON summary gains `positives_filter` key carrying the filter mode (operator telemetry).
- 3 Wave 0 Phase 14 RED stubs flipped SKIP → PASS on first run:
  - `test_export_csv_default_filters_to_new_to_add` (byte-exact match against `golden_positives_new_to_add.csv`)
  - `test_export_csv_include_existing_flag_emits_all` (Status column appended, all 5 ranked rows surface)
  - `test_export_csv_graceful_fallback_when_sync_absent` (no positives-sync.json → full ranked list)
- Full `test_export_csv.py`: **37/37 PASSED** (0 regressions on Phase 10/11 goldens, ADGM-05 mapping tests, byte-contract tests).
- Full skill test suite: **256 passed** (was 250 passed + 6 skipped pre-Wave-2; +6 PASS / -6 SKIP across parallel 14-03 + 14-04, 0 regressions).
- POS-04 + POS-05 (CSV-side) satisfied.

## Task Commits

1. **Task 1 + Task 2 (bundled atomically): positives-sync filter + --include-existing flag on export_csv** — `65bb6f6` (feat)

_Note: Both tasks landed in a single atomic commit because the 3 Wave 0 RED stubs only flip GREEN when the full chain (sentinel + helper + flag + filter + status column) lands together; an intermediate Task 1-only commit would have left the suite in a state where 2 of the 3 tests still fail, violating per-task commit invariant 'every commit passes its targeted tests'._

**Plan metadata:** pending (this commit).

## Files Created/Modified

### Modified
- `.claude/skills/google-ad-research/scripts/export_csv.py` — +102 / -13 lines:
  - +3 lines: `_POSITIVES_SYNC_SUPPORTED = True` sentinel (after drift-guard asserts)
  - +14 lines: `_load_positives_sync` helper
  - +11 lines: `--include-existing` argparse flag
  - +18 lines: `bucket_by_kw` build + per-row filter / Status payload in `_build_positives_rows`
  - +3 lines: signature kwargs (positives_sync, include_existing)
  - +3 lines: `write_positives` include_status kwarg + dynamic headers
  - +8 lines: `main` filter_mode derivation + positives_sync load + telemetry key
  - +2 lines: `write_positives` include_status flag wired in main

## Decisions Made

See `key-decisions:` frontmatter for the full list. Summary:

1. **Single atomic commit covering both tasks** — Wave 0 tests require the full chain together; per-task hash discipline preserved in commit message bullets.
2. **`Status` defaults to `new_to_add`** when `--include-existing` surfaces a ranked kw not in any bucket — safest operator default (signals a perf_synth/export race-window kw).
3. **Parallel-wave commit hygiene** — explicit `git add` of `export_csv.py` only; `render_report.py` left for 14-03's commit.
4. **`bucket_by_kw` first-write-wins** with `new_to_add` inserted first — preserves cross_ref_positives' canonical bucket priority chain.
5. **Existing `(Ad Group asc, Score desc)` sort untouched** — Status column lives in payload, not in sort-key; byte-exact golden contract holds without filter-mode-specific sort.

## Deviations from Plan

**None** — plan executed exactly as written. The golden `golden_positives_new_to_add.csv` byte-match passed on first run; no golden edits needed (sort order in `_build_positives_rows` produced `accident_chiropractor_commercial` before `walk_in_clinic_transactional` alphabetically, matching the golden's encoded order).

## Issues Encountered

None. Wave 0 fixtures + RED stubs + golden byte-match all wired correctly in Plan 14-00; both Task 1 (sentinel + helper + flag) and Task 2 (filter logic + Status column path) passed targeted tests on first run.

## Self-Check

- File exists: `.claude/skills/google-ad-research/scripts/export_csv.py` — confirmed modified (sentinel + _load_positives_sync + --include-existing + filter logic + write_positives include_status present)
- Commit found in `git log --oneline -3`: `65bb6f6` (feat 14-04 export_csv) — present
- Targeted tests: 37/37 PASSED in `test_export_csv.py` (33 legacy + 3 new Phase 14 + 4 ADGM-05)
- Full skill test suite: **256 passed** — delta +6 PASS, -6 SKIP vs pre-Wave-2 baseline; 0 regressions

## Self-Check: PASSED

## Next Phase Readiness

- Plan 14-04 closes the Wave 3 parallel pair (14-03 render + 14-04 export). All POS-* CSV-side and render-side contracts are now LIVE in production scripts.
- Plan 14-05 (SKILL.md LLM re-tag step + Phase 8 sub-flow doc update, POS-03 + POS-06) is the final Phase 14 plan — gated only on prose work in references/phase8-account-data.md + SKILL.md + (probably) a new references/phase14-positives-sync.md rubric. All Python is now done.
- Remaining 0 SKIPs in suite (was 6 pre-Wave-2). Full suite GREEN.
- v1.4 requirements complete: POS 6/7 — POS-01, POS-02, POS-03 (rendered into report.md by 14-03), POS-04, POS-05, POS-07 complete. POS-06 (LLM re-tag step) pending Plan 14-05.

---
*Phase: 14-positives-sync*
*Completed: 2026-05-15*
