---
phase: 11-account-structure-mapping
verified: 2026-05-15T00:35:00Z
status: passed
score: 6/6 must-haves verified
re_verification: null
---

# Phase 11: Account-Structure Mapping Verification Report

**Phase Goal:** Skill output respects the client's existing Google Ads account. Brief narrows research to specific counties/cities via optional `geo_focus` field; out-of-scope city tokens drop from keyword pool; `ad_group_match.py` maps ranked keywords to existing account ad groups; `export_csv.py` writes existing ad group names when matched.

**Verified:** 2026-05-15T00:35:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | Operator can supply optional `geo_focus` in brief; `run_init._parse_optional_geo_focus` preserves the line verbatim and is parseable downstream (GEO-01) | VERIFIED | `run_init.py:51 _parse_optional_geo_focus`; smoke brief.md persisted "Palm Beach County, Lake Worth"; report.json `geographic_focus = {location: '10.0 mi radius around Lake Worth, FL', focus: ['Palm Beach County', 'Lake Worth']}` |
| 2 | `serp_fetch.py --geo-focus` appends tokens to seed queries with case-insensitive dedup (GEO-02) | VERIFIED | `serp_fetch.py:55 _augment_seed_with_geo` + wire site at `serp_fetch.py:212`; SKILL.md Step 8 documents the flag |
| 3 | `merge_signals.py` drops out-of-scope city tokens via `_keyword_drifts_city` + county hierarchy via `_build_city_filter` (GEO-03, GEO-04) | VERIFIED | `merge_signals.py:176 _build_city_filter`, `:208 _keyword_drifts_city`, wired at `:480` (drop branch) and `:606-611` (main wiring with `_parse_optional_geo_focus` + state inference). `references/us-cities.json` exists at 103KB (~5,000 cities) |
| 4 | `render_report.py` emits `## Geographic Focus` callout when brief carries geo_focus (GEO-05) | VERIFIED | Smoke report.md line 18 contains `## Geographic Focus` with "10.0 mi radius around Lake Worth, FL → Focus: Palm Beach County, Lake Worth"; `render_report.py:557 render_geographic_focus_section` |
| 5 | `ad_group_match.py` produces `ad-group-mapping.json` sidecar with required schema (ADGM-01..04); graceful Phase-8-absent skip emits `skipped_reason` | VERIFIED | Smoke `ad-group-mapping.json` has keys `{computed_at, mapping_coverage_pct, matches, skipped_reason, unmapped_count}`; 73 matches; `build_mapping` at `ad_group_match.py:183`; locked `_THRESHOLDS = {high: 0.7, medium: 0.4}` with frozenset assertion |
| 6 | `export_csv.py` substitutes existing ad-group names when mapping coverage matched, filters duplicates from ad_groups.csv; `render_report.py` rewrites Next Steps step 3 strictly when coverage > 50% (ADGM-05, ADGM-06) | VERIFIED | `export_csv.py:134 _load_ad_group_mapping`, `:149 _resolve_ad_group_from_mapping`, wired at `:327` and `:475`. `render_report.py:156 _COVERAGE_REWRITE_PCT = 50.0`, gate at `:911 if coverage > _COVERAGE_REWRITE_PCT`. Smoke at 0% coverage correctly retains "Create ad groups: ..." (step 4) — strict `>` boundary holds |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `.claude/skills/google-ad-research/references/us-cities.json` | ~100KB US Census subset, 51 states | VERIFIED | 103,260 bytes; FL/TX/CA + 48 other states |
| `.claude/skills/google-ad-research/scripts/ad_group_match.py` | Full sidecar with build_mapping + CLI | VERIFIED | 13,733 bytes; `build_mapping` at line 183; `_THRESHOLDS` locked at top; `main_with_args` wired |
| `.claude/skills/google-ad-research/references/phase11-account-structure-mapping.md` | ~240 lines, Steps 44-47 rubric | VERIFIED | 240 lines, file exists |
| `.claude/skills/google-ad-research/SKILL.md` | ≤500 lines, Phase 11 pointer + Step 3/4/8 extensions | VERIFIED | 499 lines (under cap); Phase 11 pointer at line 499; geo_focus row at line 80; brief template line at 111; Step 8 note at 234 |
| `run_init.py _parse_optional_geo_focus` | GEO-01 helper | VERIFIED | Line 51, with docstring + examples |
| `serp_fetch.py _augment_seed_with_geo` | GEO-02 helper + --geo-focus arg | VERIFIED | Line 55 + wire site line 212 |
| `merge_signals.py _build_city_filter + _keyword_drifts_city` | GEO-03/04 city filter | VERIFIED | Lines 176, 208; wired into drift pipeline (line 480) + main (line 606-611) |
| `export_csv.py mapping-aware helpers` | ADGM-05 | VERIFIED | `_load_ad_group_mapping`, `_resolve_ad_group_from_mapping` + wire sites at line 327 (positives) and 475 (main) |
| `render_report.py render_geographic_focus_section + _COVERAGE_REWRITE_PCT` | GEO-05 + ADGM-06 | VERIFIED | Lines 156, 557; strict `>` gate at 911; mapping loader at 580; geo-md inserted at 1001 |
| Live smoke run folder `.runs/2026-05-14T232828Z-phase-11-smoke/` | E2E artifacts present | VERIFIED | report.md, report.json, ad-group-mapping.json, export/{positives,negatives,ad_groups}.csv all present |
| 5 plan SUMMARYs (11-00..11-04) | status: complete | VERIFIED | All 5 SUMMARY.md files present in phase directory |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `merge_signals.py` | `references/us-cities.json` | `_load_us_cities` + `--us-cities-path` flag | WIRED | Reference data file shipped; loader honors override path |
| `merge_signals.py` | `brief.md` | `_parse_optional_geo_focus` import + Location field state inference | WIRED | Import at line 64; geo_focus extracted at line 606 |
| `serp_fetch.py` | Serper REST API | POST body `q` field with `_augment_seed_with_geo` per seed | WIRED | Wire site verified at line 212 |
| `ad_group_match.py` | `{run_dir}/raw/google-ads-perf.json` | json.loads + filter ENABLED | WIRED | `_build_ad_group_index` filters by status; tests verify REMOVED skipped |
| `ad_group_match.py` | `{run_dir}/raw/google-ads-search-terms.json` | bucket by `ad_group_name` (Pitfall 1) | WIRED | Token bag keyed by ad_group_name (test verifies) |
| `ad_group_match.py` | `{run_dir}/ranked-enriched.json` | json.loads with ranked.json fallback | WIRED | main_with_args fallback path implemented |
| `export_csv.py` | `{run_dir}/ad-group-mapping.json` | `_load_ad_group_mapping(run_dir)` returns None on absence | WIRED | Tolerant loader (json/OSError → None); fallback to cluster_slug |
| `render_report.py` | `{run_dir}/ad-group-mapping.json` | `_load_ad_group_mapping_for_render` | WIRED | Used at lines 1068, 1806, 1953 (next_steps + report.json composition) |
| `render_report.py` | `run_init._parse_optional_geo_focus` | Imported indirectly via `_parse_brief_fields` populating `geo_focus` key | WIRED | brief_fields.geo_focus drives `render_geographic_focus_section` |
| Live smoke artifacts | Skill output contract | end-to-end pipeline run on .runs/2026-05-14T232828Z-phase-11-smoke/ | WIRED | All scripts exit 0; CSVs emit 73/47/14 rows; report.md has Geographic Focus + Next Steps; report.json has geographic_focus + ad_group_mapping_summary |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| GEO-01 | 11-00, 11-01, 11-04 | Optional `geo_focus` brief field, comma-separated | SATISFIED | `_parse_optional_geo_focus` helper; SKILL.md Step 3+4 wired; report.json `geographic_focus.focus` populated in smoke |
| GEO-02 | 11-00, 11-01 | serp_fetch.py appends geo_focus tokens to seed `q` | SATISFIED | `_augment_seed_with_geo` + `--geo-focus` flag + per-seed wire |
| GEO-03 | 11-00, 11-01 | merge_signals.py drops out-of-scope city tokens scoped to state | SATISFIED | `_build_city_filter` + `_keyword_drifts_city` + drift-pipeline integration at line 480 |
| GEO-04 | 11-00, 11-01 | references/us-cities.json (top ~5000 US cities) | SATISFIED | 103KB file with all 50 states + DC; lookup contract honored by `_load_us_cities` |
| GEO-05 | 11-00, 11-03, 11-04 | render_report.py "Geographic Focus" callout | SATISFIED | Smoke report.md line 18 confirms callout; `render_geographic_focus_section` returns "" when geo_focus empty |
| ADGM-01 | 11-00, 11-02 | ad_group_match reads Phase 8 raws; silent skip when absent | SATISFIED | `main_with_args` emits `skipped_reason: "phase8_artifacts_absent"` with exit 0 when raws missing |
| ADGM-02 | 11-00, 11-02 | Similarity = jaccard × intent_multiplier; threshold ≥ 0.4 | SATISFIED | `_jaccard` × `_intent_match_multiplier`; `_DEFAULT_INTENT_MISMATCH_MULTIPLIER = 0.5` |
| ADGM-03 | 11-00, 11-02 | Confidence tiers from frozenset-locked thresholds | SATISFIED | `_THRESHOLDS = {high: 0.7, medium: 0.4}` with `frozenset(_THRESHOLDS) == frozenset({"high","medium"})` assertion at import |
| ADGM-04 | 11-00, 11-02 | ad-group-mapping.json sidecar with full schema | SATISFIED | Smoke artifact has all 5 keys: matches, unmapped_count, mapping_coverage_pct, computed_at, skipped_reason |
| ADGM-05 | 11-00, 11-03 | export_csv.py substitutes existing names; filters ad_groups.csv | SATISFIED | `_resolve_ad_group_from_mapping` + `_existing_ad_group_names_in_mapping` + `mapping=` kwarg threaded through `_build_positives_rows` and `_build_ad_groups_rows` |
| ADGM-06 | 11-00, 11-03 | render_report.py Next Steps rewrite when coverage > 50% (strict) | SATISFIED | `_COVERAGE_REWRITE_PCT = 50.0` + strict `>` at line 911; smoke at 0% coverage correctly does NOT rewrite (step 4 keeps "Create ad groups: ...") |

### Anti-Patterns Found

None blocking. All known pitfalls from RESEARCH/VALIDATION are mitigated:
- Pitfall 1 (ad_group_name not ad_group_id) — test_token_bag_keyed_by_ad_group_name covers
- Pitfall 2 (Unicode dash preservation) — test_unicode_dashes_preserved + ensure_ascii=False on JSON write
- Pitfall 3 (stopwords for similarity only, not geo filter) — `_STOPWORDS` applied in `_tokens`; geo filter uses literal substring
- Pitfall 4 (homonym cities — Lake Worth FL vs TX) — state_code scopes us_cities lookup
- Pitfall 5 (county hierarchy) — `_strip_county_suffix` + county-value check
- Pitfall 6 (Phase 8 absent) — graceful skip with `skipped_reason`
- Pitfall 7 (coverage excludes low tier; strict > 50.0 threshold) — verified in render_report.py:911 + ad_group_match.py coverage math
- Pitfall 8 (case-insensitive dedup in `_augment_seed_with_geo`) — implemented
- Pitfall 9 (SKILL.md 500-line cap) — at 499 lines; trims documented in 11-04-SUMMARY

### Human Verification Required

None — operator has already approved the Wave 3 checkpoint per the live smoke run produced at `.runs/2026-05-14T232828Z-phase-11-smoke/`. All operator-visible artifacts (report.md, report.json, positives.csv, ad_groups.csv, ad-group-mapping.json) round-trip cleanly with expected schemas.

### Gaps Summary

No gaps. Phase 11 goal fully achieved:
- Geographic refinement plumbing (GEO-01..05) is operator-accessible via SKILL.md Steps 3/4/8 and the references file.
- Ad-group mapping (ADGM-01..06) ships `ad_group_match.py` end-to-end with locked thresholds and graceful Phase-8-absent skip.
- Export + render integrations (ADGM-05, ADGM-06) are mapping-aware with backward-compat fallback when mapping absent.
- Live smoke confirms all scripts exit 0 against `.runs/2026-05-14T232828Z-phase-11-smoke/` with the expected operator-visible artifacts.
- The 0% coverage observed in the smoke is correct behavior (strict `> 50.0` gate) — the rewrite branch is exercised by the unit test `test_next_steps_rewrite_high_coverage` against `ad-group-mapping-60pct.json`, and the boundary case (50.0 exactly → no rewrite) is covered by `test_next_steps_no_rewrite_at_exactly_50pct`.

REQUIREMENTS.md already marks all 11 requirements (GEO-01..05 + ADGM-01..06) Complete; Phase 11 verification confirms that traceability is grounded in real artifacts and live evidence.

---

_Verified: 2026-05-15T00:35:00Z_
_Verifier: Claude (gsd-verifier)_
