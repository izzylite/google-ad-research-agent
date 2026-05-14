---
phase: 11-account-structure-mapping
plan: 00
subsystem: tests + sidecar stub
tags: [phase-11, wave-0, red-scaffold, geo, ad-group-mapping]
dependency-graph:
  requires:
    - Phase 8 perf.json / search_terms.json shape (verified against real run-folder)
    - Phase 10 RED-scaffold pattern (per-function hasattr guards on legacy files)
  provides:
    - test_geo_filter.py: 7 RED stubs for GEO-03/GEO-04 city-county-state filter
    - test_ad_group_match.py: 14 RED stubs for ADGM-01..04 (1 PASS test_module_imports + 13 SKIP)
    - 16 hasattr-guarded RED stubs across 5 existing test files (GEO-01/02 + ADGM-05/06 + GEO-05)
    - 7 fixtures + 1 sidecar stub (ad_group_match.py) with locked _THRESHOLDS + _STOPWORDS
  affects:
    - Wave 1 plans 11-01 (geo plumbing) + 11-02 (ad_group_match core) — both unblocked, no shared mutated files
    - Wave 2 plan 11-03 (export_csv + render_report integrations) — RED stubs ready for flip-GREEN
tech-stack:
  added: []
  patterns:
    - "Sidecar script (PEP 723, stdlib-only, --run-dir CLI, JSON-stdout, 0/2/3 exit codes)"
    - "Locked taxonomy via frozenset assertion at import (ADGM-03)"
    - "Per-function _skip_unless_* helpers preserve legacy GREEN while RED stubs SKIP"
    - "Wave-0 RED scaffold: module imports cleanly + main_with_args raises NotImplementedError"
key-files:
  created:
    - .claude/skills/google-ad-research/scripts/ad_group_match.py
    - .claude/skills/google-ad-research/scripts/tests/test_geo_filter.py
    - .claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py
    - .claude/skills/google-ad-research/scripts/tests/fixtures/us-cities-subset.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-perf-phase11.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-search-terms-phase11.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/ad-group-mapping-50pct.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/ad-group-mapping-60pct.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/ad-group-mapping-20pct.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/brief-with-geo-focus.md
    - .claude/skills/google-ad-research/scripts/tests/fixtures/brief-no-geo-focus.md
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_run_init.py
    - .claude/skills/google-ad-research/scripts/tests/test_serp_fetch.py
    - .claude/skills/google-ad-research/scripts/tests/test_merge_signals.py
    - .claude/skills/google-ad-research/scripts/tests/test_export_csv.py
    - .claude/skills/google-ad-research/scripts/tests/test_render_report.py
decisions:
  - "test_ad_group_match.py uses per-function _skip_unless_build_mapping() guard (NOT module-level pytestmark) so test_module_imports PASSES against the Wave-0 stub while other 13 tests SKIP — mirrors the Phase 10 10-00 per-function pattern for files hosting a mix of stub-PASS and Wave-1-RED tests"
  - "ad-group-mapping-*pct.json fixtures live at 50.0% (boundary, no rewrite per Pitfall 7 / open-question 4 strict `>`), 60.0% (rewrite path), 20.0% (negative path) — encoded coverage_pct exactly so ADGM-06 boundary math is testable without running build_mapping"
  - "us-cities-subset.json stores county as VALUE (lowercase, no `county` suffix); Wave 1 plan 11-01 will strip `county` suffix from geo_focus tokens before lookup. Schema = `{state_code_lower: {city_lower: county_lower}}`"
  - "search_terms fixture omits ad_group_id field entirely (Pitfall 1 verified against real run-folder) — bucketing key is ad_group_name only"
  - "Existing-ad-group names include Unicode en-dash (U+2013) in `Accident Exams – Lake Worth` to exercise Pitfall 2 byte-fidelity through CSV round-trip"
  - "ad_group_match.py main_with_args raises NotImplementedError with explicit `Wave 1` and `plan 11-02` strings so test_module_imports can assert error-message routing"
  - "Wave-1 contract pre-decision: merge_signals.py grows --us-cities-path CLI flag defaulting to references/us-cities.json — tests monkeypatch the module-level constant _US_CITIES_DATA_PATH when present"
  - "Wave-1 contract pre-decision: render_next_steps_section signature gains ad_group_mapping kwarg in Wave 2 plan 11-03 — detected via inspect.signature in tests"
metrics:
  duration_min: 7
  tasks_completed: 3
  files_created: 11
  files_modified: 5
  completed_date: "2026-05-14"
---

# Phase 11 Plan 00: Wave 0 RED Scaffold Summary

Wave 0 lands the test/fixture/stub scaffolding for Phase 11 (geographic refinement + ad-group mapping against existing client account structure) using the Phase 10 10-00 RED-scaffold pattern. Two new test files (21 RED stubs) plus 16 hasattr-guarded extensions to existing test files. Seven fixtures including us-cities-subset.json (FL/TX/CA with FL Lake Worth/TX Lake Worth homonym for Pitfall 4 disambiguation testing) and three ad-group-mapping coverage fixtures at the 50.0% / 60.0% / 20.0% boundary. ad_group_match.py shipped as a MODULE_INCOMPLETE stub with _THRESHOLDS frozenset-asserted at import and main_with_args() routing operators to Wave 1 plan 11-02. Full suite remains 165 passing legacy tests; 1 new test passes (test_module_imports); 37 new RED stubs SKIP via per-function or module-level guards; SKILL.md untouched at 500/500 lines.

## What Shipped

### Files Created (11)

| File | Purpose | Notes |
|---|---|---|
| `scripts/ad_group_match.py` | Wave-0 stub — MODULE_INCOMPLETE | PEP 723 header, `_THRESHOLDS` frozenset assertion, `_STOPWORDS` (21 entries), `main_with_args` raises NotImplementedError mentioning "Wave 1" + "plan 11-02" |
| `scripts/tests/test_geo_filter.py` | 7 RED stubs for GEO-03/GEO-04 | Module-level `pytestmark` skipif on `hasattr(merge_signals, '_keyword_drifts_city')` |
| `scripts/tests/test_ad_group_match.py` | 14 stubs (1 PASS + 13 SKIP) | Per-function `_skip_unless_build_mapping()` so `test_module_imports` PASSES today |
| `tests/fixtures/us-cities-subset.json` | FL/TX/CA city→county subset | 7 FL cities, 3 TX (incl. Lake Worth homonym), 2 CA (incl. Hollywood homonym) |
| `tests/fixtures/google-ads-perf-phase11.json` | 4 ad_groups (3 ENABLED + 1 REMOVED) | "Accident Exams – Lake Worth" carries U+2013 en-dash literally |
| `tests/fixtures/google-ads-search-terms-phase11.json` | 9 search terms keyed by `ad_group_name` only | No `ad_group_id` field — Pitfall 1 verified |
| `tests/fixtures/ad-group-mapping-50pct.json` | 5/10 high+medium → boundary | `mapping_coverage_pct=50.0` exact — no rewrite per Pitfall 7 |
| `tests/fixtures/ad-group-mapping-60pct.json` | 6/10 high+medium → rewrite | 2+ distinct existing_ad_group names for Counter-grouped step-3 text |
| `tests/fixtures/ad-group-mapping-20pct.json` | 2/10 high+medium → negative path | 8 low-tier rows confirm `> 50.0` strict gate |
| `tests/fixtures/brief-with-geo-focus.md` | Brief with `**Geo focus:**` line | Triggers GEO-01 / GEO-05 paths |
| `tests/fixtures/brief-no-geo-focus.md` | Same brief minus Optional section | Backward-compat baseline |

### Files Modified (5)

| File | Added | Mechanism |
|---|---|---|
| `tests/test_run_init.py` | +2 GEO-01 stubs | `_skip_unless_geo_focus_supported()` per-function helper |
| `tests/test_serp_fetch.py` | +2 GEO-02 stubs | `_skip_unless_geo_focus_arg()` checks `_GEO_FOCUS_SUPPORTED` marker on `serp_fetch` |
| `tests/test_merge_signals.py` | +3 GEO-03 integration stubs | `_skip_unless_city_filter()` + `_stage_geo_run` helper |
| `tests/test_export_csv.py` | +4 ADGM-05 stubs | `_skip_unless_mapping_aware()` checks `_resolve_ad_group_from_mapping` hasattr |
| `tests/test_render_report.py` | +5 GEO-05 + ADGM-06 stubs | `_skip_unless_geo_section()` + `_skip_unless_next_steps_mapping_aware()` (uses `inspect.signature` to detect kwarg) |

## Test Pass / Skip Profile

```
Before this plan (Phase 10 baseline):
  165 passed, 37 skipped

After 11-00:
  166 passed  (+1: test_ad_group_match.test_module_imports)
   73 skipped (+36 new RED stubs all SKIPPING):
              21 from two new test files
              16 from five extended test files (run_init+2, serp+2, merge+3, export+4, render+5)
```

Zero legacy regressions. Zero collection errors. Full suite runtime ~2.0s.

## Locked Interfaces (Wave 1 + Wave 2 read against these)

### `_THRESHOLDS` (ad_group_match.py)
```python
_THRESHOLDS: dict[str, float] = {"high": 0.7, "medium": 0.4}
assert frozenset(_THRESHOLDS) == frozenset({"high", "medium"}), (
    "_THRESHOLDS drift — ADGM-03 taxonomy changed?"
)
_DEFAULT_INTENT_MISMATCH_MULTIPLIER: float = 0.5
_STOPWORDS: frozenset[str] = frozenset({
    "near", "me", "the", "a", "an", "of", "in", "on", "at",
    "to", "for", "and", "or", "with", "by", "from", "is", "are",
    "best", "top",
})
```

### `ad-group-mapping.json` schema
```json
{
  "matches": [
    {"keyword": "...", "existing_ad_group": "...", "confidence": "high|medium|low",
     "score": 0.78, "reason": "jaccard=... intent_match=..."}
  ],
  "unmapped_count": 4,
  "mapping_coverage_pct": 60.0,
  "computed_at": "2026-05-14T22:00:00Z",
  "skipped_reason": null
}
```
Coverage = `(high + medium) / total_ranked` (NOT including low — Pitfall 7). Strict `> 50.0` triggers Next Steps step-3 rewrite (ADGM-06).

### `us-cities.json` schema (subset fixture today, full reference file in Wave 1 plan 11-01)
```json
{"fl": {"lake worth": "palm beach", "boca raton": "palm beach", "tampa": "hillsborough"},
 "tx": {"lake worth": "tarrant", "dallas": "dallas"}, "ca": {...}}
```
Cities and counties stored lowercase, no "county" suffix. Wave 1 filter will strip "county" from geo_focus tokens before lookup.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test design bug] Module-level pytestmark blocked test_module_imports**

- **Found during:** Task 3 verification — `test_module_imports` skipped despite the stub being importable.
- **Issue:** test_ad_group_match.py originally used module-level `pytestmark = pytest.mark.skipif(MODULE_INCOMPLETE, ...)` plus a per-test `@pytest.mark.skipif(not IMPORT_OK, ...)` decorator. pytestmark applied to ALL tests regardless of position, so test_module_imports SKIPPED even though the plan explicitly requires it to PASS once Task 3 ships the stub.
- **Fix:** Removed `pytestmark`; introduced `_skip_unless_build_mapping()` helper called at the start of every Wave-1-dependent test (13 tests). test_module_imports keeps its `@pytest.mark.skipif(not IMPORT_OK, ...)` guard (which is False because IMPORT_OK is True once the stub ships) and runs unconditionally.
- **Files modified:** `tests/test_ad_group_match.py`
- **Result:** Suite went from `165 passed / 74 skipped` to `166 passed / 73 skipped` — the +1 PASS being test_module_imports asserting `_THRESHOLDS`/`_STOPWORDS` constants and the NotImplementedError message routing.
- **Commit:** `d026b8b`

**2. [Rule 1 - Spurious pytest warning] `@pytest.mark.usefixtures()` with no args**

- **Found during:** Task 1 pytest collect-only run produced `PytestWarning: usefixtures() in tests/test_ad_group_match.py::test_module_imports without arguments has no effect`.
- **Fix:** Removed the no-op decorator (it was a copy-paste artifact from a similar Phase 10 stub).
- **Files modified:** `tests/test_ad_group_match.py` (during Task 1, before commit `8973f52`).

No Rule 2/3/4 deviations. Plan executed essentially as written.

## Authentication Gates

None. Phase 11 plan 11-00 is pure local file/test work.

## Wave 1 Unblocked

Plans 11-01 (geo plumbing — run_init geo_focus parse + serp_fetch query token append + merge_signals city filter + references/us-cities.json data file) and 11-02 (ad_group_match.py core — build_mapping / _jaccard / _tokens / _classify) are now ready to run in parallel. They share no mutated files:

- 11-01 touches: `run_init.py`, `serp_fetch.py`, `merge_signals.py`, `references/us-cities.json` (new data file)
- 11-02 touches: `ad_group_match.py` (extending the Wave-0 stub)

Wave 2 plan 11-03 (export_csv + render_report integrations) gates on both Wave-1 plans completing; its RED stubs already exist in test_export_csv.py and test_render_report.py.

## Self-Check: PASSED

Verified each artifact exists on disk and each task commit is reachable:

- [x] `.claude/skills/google-ad-research/scripts/ad_group_match.py` — FOUND
- [x] `.claude/skills/google-ad-research/scripts/tests/test_geo_filter.py` — FOUND
- [x] `.claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py` — FOUND
- [x] All 7 fixture files under `tests/fixtures/` — FOUND
- [x] 5 modified test files include Phase 11 RED stubs — verified by grep
- [x] Commit `8973f52` (Task 1) — FOUND
- [x] Commit `fddbe3f` (Task 2) — FOUND
- [x] Commit `d026b8b` (Task 3) — FOUND
- [x] Full suite: `166 passed, 73 skipped, 0 errors` (≤2.1s)
- [x] SKILL.md still exactly 500 lines (unchanged this plan)
