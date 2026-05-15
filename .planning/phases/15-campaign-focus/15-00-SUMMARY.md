---
phase: 15-campaign-focus
plan: 00
subsystem: tests
tags: [tdd, red-stubs, scaffolding, CAMP-01, CAMP-02, CAMP-05, CAMP-06]
requirements: [CAMP-06]
dependency_graph:
  requires: [phase-14 _FakeGAdsClient pattern, phase-11 _skip_unless_geo_section pattern]
  provides: [_skip_unless_campaign_filter, _skip_unless_campaign_focus_section, _RecordingFakeGAdsClient, brief_with_campaign_focus.md, google-ads-perf-with-campaign.json]
  affects: [plan 15-01 perf_fetch.py, plan 15-02 render_report.py]
tech_stack:
  added: []
  patterns: [per-function hasattr/signature skip guards, list-recording fake gAds client for multi-query fetches]
key_files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/fixtures/brief_with_campaign_focus.md
    - .claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-perf-with-campaign.json
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_perf_fetch.py
    - .claude/skills/google-ad-research/scripts/tests/test_render_report.py
decisions:
  - "Parametrized fetch-all-four test counts as 1 function but expands to 4 pytest cases — accept divergence between 'test functions' (6) vs 'collected cases' (9) for perf_fetch."
  - "Multi-query fetches (fetch_perf 2 calls, fetch_existing_negatives 2 calls) require list-recording fake — added _RecordingFakeGAdsClient rather than mutating existing _FakeGAdsClient single-slot capture (keeps GREEN Phase 14 tests intact)."
  - "Brief fixture omits-case (Test 2 in CAMP-01 parser block) constructs inline brief text rather than maintaining a separate '_no_campaign_focus' fixture file — single-purpose tests don't justify a second fixture file."
  - "Typo-warning test accepts either 'not found' or 'typo' substring — gives Plan 15-02 phrasing flexibility without re-editing tests."
metrics:
  duration: ~8min
  tasks: 3
  files: 4 (2 created + 2 modified)
  date: 2026-05-15
---

# Phase 15 Plan 00: Wave 1 RED Test Scaffolding Summary

**One-liner:** Laid 15 RED test stubs + 2 fixtures covering CAMP-01 / CAMP-02 / CAMP-05 / CAMP-06; all skip-guarded so the existing 208-test suite stays GREEN until Plans 15-01 / 15-02 land production code.

## What Shipped

**Fixtures (2 files, created):**

- `brief_with_campaign_focus.md` — Full brief carrying both `**Geo focus:**` (Phase 11 carryover) and `**Campaign focus:** Search | Lake Worth Accident Exams | Manual CPC` lines. Used by `test_parse_brief_fields_extracts_campaign_focus_single`.
- `google-ads-perf-with-campaign.json` — Phase 8 perf envelope with 2 campaigns: target ("Search | Lake Worth Accident Exams | Manual CPC") + distractor ("FL PIP - Hybrid - Performance Max"). Used by name-validation tests (typo-warning / happy-path).

**test_perf_fetch.py (6 new test functions, 9 collected cases — all SKIPPED):**

| Test | Asserts | Pattern |
|------|---------|---------|
| `test_campaign_filter_single_value_gaql` | `campaign.name = '<name>'` in query | _FakeGAdsClient single-slot |
| `test_campaign_filter_list_uses_in_clause` | `campaign.name IN ('A', 'B')` | _FakeGAdsClient |
| `test_campaign_filter_escapes_single_quote` | `O''Brien Auto` (doubled quote) | _FakeGAdsClient |
| `test_campaign_filter_absent_no_clause` | No `campaign.name =` / `IN` predicate | _FakeGAdsClient |
| `test_campaign_filter_empty_list_treated_as_absent` | No filter clause | _FakeGAdsClient |
| `test_campaign_filter_applied_to_all_four_fetches[*]` | Filter in EVERY captured query | _RecordingFakeGAdsClient (4 parametrize cases) |

Skip guard: `_skip_unless_campaign_filter()` inspects `perf_fetch.fetch_search_terms` signature for `campaign_filter` kwarg.

**test_render_report.py (9 new test functions, all SKIPPED):**

| Test | Block | Asserts |
|------|-------|---------|
| `test_parse_brief_fields_extracts_campaign_focus_single` | CAMP-01 | raw string `"Search \| Lake Worth Accident Exams \| Manual CPC"` |
| `test_parse_brief_fields_campaign_focus_absent_returns_empty` | CAMP-01 | empty string default |
| `test_parse_brief_fields_campaign_focus_pipe_list` | CAMP-01 | raw `"A \| B \| C"` preserved |
| `test_campaign_focus_section_rendered_single` | CAMP-05 | `## Campaign Focus` + literal value (raw or escaped pipe) |
| `test_campaign_focus_section_omitted_when_empty` | CAMP-05 | empty string / no heading |
| `test_campaign_focus_section_list_form_bulleted` | CAMP-05 | all 3 names appear |
| `test_campaign_focus_typo_warning` | CAMP-05 | `⚠` + name + "not found"/"typo" |
| `test_campaign_focus_no_warning_when_name_matches` | CAMP-05 | no `⚠` |
| `test_campaign_focus_no_warning_when_perf_path_absent` | CAMP-05 | no `⚠` (graceful) |

Skip guards:
- `_skip_unless_campaign_focus_section()` — `hasattr(render_report, "render_campaign_focus_section")`
- `_skip_unless_brief_parser_has_campaign_focus()` — probes `_parse_brief_fields` for `campaign_focus` key

## Verification Result

```
pytest .claude/skills/google-ad-research/scripts/tests/
→ 208 passed, 66 skipped, 0 failed

pytest -k "campaign_filter or campaign_focus or parse_brief_fields_extracts or parse_brief_fields_campaign"
→ 18 skipped (9 perf_fetch parametrize-expanded + 9 render_report)
```

Pre-existing Phase 11 GEO-05 / Phase 14 POS-07 / Phase 6 RPRT-* tests all still pass — no regression.

## Commits

| Commit | Message |
|--------|---------|
| `ce7e636` | test(15-00): add campaign_focus brief + perf fixtures |
| `0fa29c2` | test(15-00): add --campaign-filter GAQL RED stubs (CAMP-02 / CAMP-06) |
| `f40acd2` | test(15-00): add campaign_focus parser + section + typo warning RED stubs |

## Deviations from Plan

None — plan executed exactly as written. Three minor planner-discretion calls were resolved during execution:

1. **Inline brief text for absent-case test** instead of separate `_no_campaign_focus` fixture file — keeps fixture directory uncluttered for a single-purpose test.
2. **`_RecordingFakeGAdsClient`** added as a sibling class (not a refactor of `_FakeGAdsClient`) so Phase 14 single-slot-capture tests stay byte-identical.
3. **Typo-warning assertion accepts either "not found" or "typo" substring** — gives Plan 15-02 phrasing flexibility without test rewrites.

## Anti-Pattern Reused

`respx` cannot mock google-ads SDK's gRPC layer (Phase 14 lesson — POS-07). `_FakeGAdsClient` + new `_RecordingFakeGAdsClient` captures the GAQL query string passed to `search_stream` and yields synthetic `_FakeRow` batches. Mirrors the lightweight fake-client pattern already proven in Phase 14.

## Wave 2 Wiring

Plan 15-01 lands `campaign_filter: list[str] | None = None` kwarg on all 4 `perf_fetch.fetch_*` functions and `--campaign-filter '<value>'` CLI arg on `main_with_args`. As soon as the kwarg exists, the 6 perf_fetch tests flip GREEN one-by-one as the GAQL clause is wired into each fetch.

Plan 15-02 lands `render_campaign_focus_section(brief_fields, perf_path=None) -> str` on `render_report.py` plus extends `_parse_brief_fields` to emit `campaign_focus` key. As soon as both land, all 9 render_report tests flip GREEN.

## Self-Check: PASSED

- [x] `.claude/skills/google-ad-research/scripts/tests/fixtures/brief_with_campaign_focus.md` exists
- [x] `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-perf-with-campaign.json` exists
- [x] `test_perf_fetch.py` carries 6 new test functions guarded by `_skip_unless_campaign_filter`
- [x] `test_render_report.py` carries 9 new test functions guarded by `_skip_unless_campaign_focus_section` / `_skip_unless_brief_parser_has_campaign_focus`
- [x] Commit `ce7e636` exists
- [x] Commit `0fa29c2` exists
- [x] Commit `f40acd2` exists
- [x] Full pytest suite green (208 passed, 66 skipped, 0 failed)
