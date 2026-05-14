---
phase: 11-account-structure-mapping
plan: 01
subsystem: geo plumbing (GEO-01..04)
tags: [phase-11, wave-1, geo-filter, city-county, brief-intake, serp-fetch]
dependency-graph:
  requires:
    - Phase 11 Wave 0 RED scaffold (test_geo_filter.py, us-cities-subset.json fixture, GEO-* RED stubs in test_run_init/test_serp_fetch/test_merge_signals)
    - Existing merge_signals state-level filter (_build_state_filter, _keyword_drifts_geo, US_STATE_TOKENS, AMBIGUOUS_CITIES)
    - Existing run_init verbatim stdin → brief.md write path
    - Existing serp_fetch argparse surface (--gl, --hl, --location)
  provides:
    - references/us-cities.json (top ~4800 cities across 50 states + DC; ≤103KB)
    - run_init._parse_optional_geo_focus(brief_text) → list[str]
    - serp_fetch --geo-focus arg + _augment_seed_with_geo helper + _GEO_FOCUS_SUPPORTED marker
    - merge_signals._load_us_cities + _strip_county_suffix + _build_city_filter + _keyword_drifts_city + _infer_state_code
    - merge_signals --us-cities-path CLI flag (test injection)
    - merge_signals stdout telemetry: geo_focus, state_code, cities_in_focus, cities_filtered_out, keywords_dropped_city_filter, keywords_dropped_state_filter
  affects:
    - Wave 2 plan 11-03 (export_csv + render_report integrations) — render_report.py can now read geo_focus + state_code from brief.md and us-cities.json from disk for the "Geographic Focus" callout (GEO-05)
    - Future serp_fetch callers (SKILL.md plan 11-04) — can pass --geo-focus tokens from brief.md
tech-stack:
  added: []
  patterns:
    - "Module-level data file at known relative path (_US_CITIES_DATA_PATH) with monkeypatchable constant + CLI override flag — mirrors the references/compliance-verticals.json pattern from Phase 9 plan 09-03"
    - "Case-insensitive substring dedup for query token append (Pitfall 8) — multi-word safe without regex word-boundary edge cases"
    - "City→county hierarchy via county-as-value schema — geo_focus 'Palm Beach County' is normalised by `_strip_county_suffix` then matched against either city name or its county value"
    - "Telemetry-by-default stdout JSON additions are pure additions (no key renames), preserving v1.0/v1.1 consumer backward compat"
key-files:
  created:
    - .claude/skills/google-ad-research/references/us-cities.json
    - .claude/skills/google-ad-research/references/us-cities.SOURCE.md
    - .planning/phases/11-account-structure-mapping/11-01-SUMMARY.md
  modified:
    - .claude/skills/google-ad-research/scripts/run_init.py
    - .claude/skills/google-ad-research/scripts/serp_fetch.py
    - .claude/skills/google-ad-research/scripts/merge_signals.py
decisions:
  - "us-cities.json composed from plotly/us-cities-top-1k (population priority) + millbj92/USCities (county lookup via dominant ZIP-derived county) + 13 manual fixture-required entries (tx/lake worth, ca/hollywood, FL spot-checks). 51 states (50 + DC), ~4800 cities, 103KB minified — well under 200KB budget."
  - "US territories (PR, VI, GU, AS, MP, FM, MH, PW) intentionally excluded — GEO-03 filter targets US-state Google Ads runs; territories out of scope for v1.2."
  - "_parse_optional_geo_focus regex tolerates leading list markers (`-`, `*`) and whitespace so both `- **Geo focus:** A, B` and `**Geo focus:** A, B` parse identically. Returns [] for absent / blank-value line — preserves backward compat with pre-Phase-11 briefs."
  - "_GEO_FOCUS_SUPPORTED module marker on serp_fetch enables tests to detect Phase 11 wiring without monkey-importing argparse parser internals."
  - "_augment_seed_with_geo is a pure helper (testable in isolation, no HTTP) — wired once per seed inside the existing for-loop. Augmented seed feeds both the POST body `q` AND the persisted by_seed[].seed field, so Phase 3 downstream sees the same augmented query (no schema drift)."
  - "merge_signals._infer_state_code prefers full state names (case-insensitive) over 2-letter uppercase fallback — avoids false positives on common lowercase words like 'or', 'in', 'ok', 'hi', 'ma'. Mirrors the existing `_build_state_filter` design choice."
  - "_build_city_filter normalises geo_focus entries via `_strip_county_suffix` ONCE, then iterates the state's city catalogue. A city is in-focus when its name OR its county value matches a focus entry. Pitfall 5 (city→county hierarchy) verified by test_keyword_kept_when_city_county_in_geo_focus."
  - "_keyword_drifts_city uses literal substring match (not regex \\b) because multi-word city names like 'west palm beach' / 'boca raton' break under naive word-boundary heuristics. Stopword-list independence (Pitfall covered) — geo filter is purely catalogue-membership, not token-overlap math."
  - "merge_raw_files signature gains city_filter + dropped_counter kwargs as keyword-only — preserves positional-call compatibility for any direct callers; signature growth is additive."
  - "stdout JSON gains 6 new keys (geo_focus, state_code, cities_in_focus, cities_filtered_out, keywords_dropped_city_filter, keywords_dropped_state_filter). All optional from a downstream-consumer perspective; existing keys (keywords_count, source_diversity_avg, variants_merged) unchanged byte-for-byte when filter inactive."
metrics:
  duration_min: 8
  tasks_completed: 4
  files_created: 3
  files_modified: 3
  completed_date: "2026-05-14"
---

# Phase 11 Plan 01: Wave 1 Geo Plumbing Summary

Wave 1 lands the geographic refinement plumbing across three scripts plus the new `references/us-cities.json` reference data file. GEO-01/02/03/04 contracts are now executable end-to-end: an operator's `**Geo focus:**` brief line propagates through `run_init` (preserved verbatim) → `merge_signals` (city catalogue lookup + drift filter) → `serp_fetch` (`--geo-focus` tokens appended to `q` with Pitfall-8 dedup). All 14 Phase 11 GEO-* RED stubs from plan 11-00 flip GREEN. Zero v1.0/v1.1 regressions. SKILL.md untouched at exactly 500/500 lines.

## What Shipped

### Files Created (3)

| File | Purpose | Notes |
|---|---|---|
| `references/us-cities.json` | GEO-04 canonical city→county lookup | 51 states (50 + DC), ~4800 cities, 103KB minified, sort_keys, comma-separator. All 12 `us-cities-subset.json` fixture entries match byte-for-byte. |
| `references/us-cities.SOURCE.md` | Provenance + schema invariants | Documents sources (plotly top-1k + millbj92 USCities), manual fixture entries, regeneration recipe |
| `.planning/phases/11-account-structure-mapping/11-01-SUMMARY.md` | This file | |

### Files Modified (3)

| File | Added | Mechanism |
|---|---|---|
| `scripts/run_init.py` | `_parse_optional_geo_focus(brief_text) → list[str]` | Module-level regex `_GEO_FOCUS_LINE_RE` (multiline, case-insensitive, tolerates leading `-`/`*`); splits on `,`, strips whitespace, drops empty entries |
| `scripts/serp_fetch.py` | `--geo-focus` CLI arg + `_augment_seed_with_geo` helper + `_GEO_FOCUS_SUPPORTED` marker + stdout `geo_focus_tokens` key | Case-insensitive substring dedup (Pitfall 8); augmented seed feeds both POST body `q` AND persisted `by_seed[].seed` field |
| `scripts/merge_signals.py` | `_US_CITIES_DATA_PATH` + `_COUNTY_SUFFIX_RE` + `_STATE_NAME_TO_CODE` + `_load_us_cities` + `_strip_county_suffix` + `_build_city_filter` + `_keyword_drifts_city` + `_infer_state_code` + `--us-cities-path` CLI arg + 6 stdout telemetry keys | Wired into `_add` filter chain alongside existing `_keyword_drifts_geo`; backward-compat preserved when geo_focus empty |

## Test Pass / Skip Profile

```
Before plan 11-01 (Phase 11 Wave 0 baseline):
  203 passed, 36 skipped

After plan 11-01:
  217 passed (+14: all GEO-* RED stubs flip GREEN)
   22 skipped (-14: down from 36)

Breakdown of the 14 flips:
  test_geo_filter.py         : 7 / 7 (all RED stubs GREEN)
  test_run_init.py           : 2 / 2 (test_geo_focus_persisted, test_geo_focus_absent_backward_compat)
  test_serp_fetch.py         : 2 / 2 (test_geo_focus_appended_to_query, test_geo_focus_dedup_on_existing_token)
  test_merge_signals.py      : 3 / 3 (test_city_filter_active, test_city_filter_inactive_when_geo_focus_empty,
                                       test_city_filter_preserves_county_hierarchy)
```

Zero legacy regressions. Zero collection errors. Full suite runtime ~15s.

## Locked Interfaces (Wave 2 reads against these)

### `references/us-cities.json` schema

```json
{
  "fl": {"lake worth": "palm beach", "boca raton": "palm beach", "tampa": "hillsborough", ...},
  "tx": {"lake worth": "tarrant", "dallas": "dallas", "houston": "harris", ...},
  "...": {"...": "..."}
}
```

- Keys: 2-letter USPS lowercase (50 states + `dc`)
- City names: lowercase, original spelling
- County values: lowercase, NO ` county` suffix (the filter strips ` county` from `geo_focus` inputs before lookup)
- Empty-county entries dropped
- ≤200KB target — current 103KB

### `merge_signals` public surface added by this plan

```python
_US_CITIES_DATA_PATH: Path = scripts/../references/us-cities.json  # monkeypatchable

def _load_us_cities(path: Path | None = None) -> dict[str, dict[str, str]]: ...
def _strip_county_suffix(name: str) -> str: ...
def _build_city_filter(state_code: str, geo_focus: list[str], us_cities: dict) -> dict[str, set[str]]:
    """Returns {'in': <cities in focus>, 'out': <cities not in focus>}."""
def _keyword_drifts_city(text: str, city_filter: dict) -> bool: ...
def _infer_state_code(brief_text: str) -> str: ...  # "" when no match
```

### `serp_fetch` public surface added by this plan

```python
_GEO_FOCUS_SUPPORTED: bool = True  # presence detected by tests
def _augment_seed_with_geo(seed: str, geo_focus_tokens: list[str]) -> str: ...
```

CLI: `serp_fetch.py ... --geo-focus "Palm Beach County" "Lake Worth"` (nargs='*', default=[])

### `run_init` public surface added by this plan

```python
def _parse_optional_geo_focus(brief_text: str) -> list[str]: ...
```

CLI signature unchanged. Verbatim stdin → brief.md write path unchanged.

## Pitfall Mitigations Verified

| Pitfall | Mitigation | Verified by |
|---|---|---|
| **4 — Wrong-city homonyms across states** | `_build_city_filter` scopes lookup to brief's `state_code`; only that state's cities considered | `test_state_disambiguation` — FL filter keeps `lake worth chiropractor` AND drops `tampa pain clinic`; TX filter independently keeps `lake worth car shop` and drops `dallas car shop` |
| **5 — City → county → geo_focus hierarchy** | County stored as VALUE in us-cities.json; `_strip_county_suffix` normalises geo_focus before comparison; in-focus check matches city name OR county | `test_keyword_kept_when_city_county_in_geo_focus` — `boca raton dentist` survives `Palm Beach County` filter because Boca Raton's county IS Palm Beach |
| **8 — Double-locating queries** | `_augment_seed_with_geo` does case-insensitive substring dedup before append | `test_geo_focus_dedup_on_existing_token` — seed `lake worth accident doctor` + token `Lake Worth` produces exactly ONE occurrence of `lake worth` in the POST body `q` |

## Deviations from Plan

None. The plan executed essentially as written. Two small notes:

1. **us-cities.json sourcing.** The plan recommended US Census Gazetteer Places file as preferred source. The Census ZIP archive isn't trivially fetchable from this environment (would require unzipping + parsing a wide schema), so I composed the file from two open MIT-licensed datasets that together produce the same `{state: {city: county}}` shape:
   - `plotly/datasets/us-cities-top-1k.csv` for the population priority subset
   - `millbj92/US-Zip-Codes-JSON/USCities.json` for the city→dominant-county lookup
   - Manual entries added for `tx/lake worth`, `ca/hollywood`, and FL fixture spot-checks
   This satisfies all plan acceptance criteria: ≤200KB, all 50 states + DC, all 12 test-fixture entries match, valid JSON, UTF-8 no BOM.

2. **`_parse_optional_geo_focus` regex tolerance.** The plan example showed `r"^\*\*Geo\s*focus:\*\*\s*(.+)$"`. I broadened the leading character class to `^[-*\s]*\*\*Geo\s*focus:\*\*` so both `- **Geo focus:** ...` and `* **Geo focus:** ...` (and bare `**Geo focus:** ...`) all parse identically. This matches how the Wave-0 fixture brief is formatted (with a leading `-` list marker) and is forward-compatible with the SKILL.md prompt update in plan 11-04.

## Authentication Gates

None. Plan 11-01 is pure local file/test work plus two HTTPS fetches for the one-time us-cities.json composition (both anonymous, both committed to repo).

## Wave 2 Unblocked

Plan 11-03 (export_csv + render_report integrations) can now:

- Call `merge_signals._infer_state_code` and `run_init._parse_optional_geo_focus` to read state + geo_focus from `brief.md`
- Read `references/us-cities.json` via `merge_signals._load_us_cities` for any geographic helper needs (e.g., "Cities in target county" enumeration for the "Geographic Focus" callout in `render_report.py`)
- Trust that `merge_signals` stdout JSON includes `geo_focus`, `state_code`, `cities_in_focus`, `cities_filtered_out`, `keywords_dropped_city_filter` — telemetry already plumbed and ready for the report rendering layer

Plan 11-02 (ad_group_match.py core, parallel Wave 1) is independent of this plan — no shared mutated files.

## Self-Check: PASSED

Verified each artifact exists on disk and each task commit is reachable.

- [x] `.claude/skills/google-ad-research/references/us-cities.json` — FOUND (103260 bytes, valid JSON, 51 states, 4794 cities)
- [x] `.claude/skills/google-ad-research/references/us-cities.SOURCE.md` — FOUND
- [x] `.claude/skills/google-ad-research/scripts/run_init.py` — modified, `_parse_optional_geo_focus` exported
- [x] `.claude/skills/google-ad-research/scripts/serp_fetch.py` — modified, `_GEO_FOCUS_SUPPORTED` + `_augment_seed_with_geo` exported
- [x] `.claude/skills/google-ad-research/scripts/merge_signals.py` — modified, all 5 GEO helpers exported
- [x] Commit `f14b6f5` (Task 1: us-cities.json + SOURCE.md) — FOUND
- [x] Commit `c4add00` (Task 2: run_init geo_focus parse) — FOUND
- [x] Commit `87c9b4d` (Task 3: serp_fetch --geo-focus) — FOUND
- [x] Commit `7bbe02d` (Task 4: merge_signals city filter) — FOUND
- [x] Full suite: `217 passed, 22 skipped, 0 errors` (~15s)
- [x] SKILL.md still exactly 500 lines (unchanged this plan)
