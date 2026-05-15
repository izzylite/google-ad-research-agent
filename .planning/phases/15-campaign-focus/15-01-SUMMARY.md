---
phase: 15-campaign-focus
plan: 01
subsystem: api
tags: [google-ads, gaql, campaign-filter, perf_fetch, CAMP-02]

requires:
  - phase: 15-00
    provides: 6 RED tests (9 parametrized cases) covering CAMP-02 / CAMP-06
provides:
  - "_apply_campaign_filter + _escape_gaql_string helpers in perf_fetch.py"
  - "--campaign-filter CLI flag on perf_fetch.py main_with_args"
  - "campaign_filter kwarg on all 4 fetch_* functions (search_terms, perf, existing_negatives, keyword_view)"
  - "All 4 GAQL queries inject AND campaign.name = '...' (single) or IN (...) (list)"
  - "stdout JSON gains campaign_filter key for traceability (null when absent)"
affects: [phase-15-02 render_report.py campaign_focus section, phase-15-03 SKILL.md wiring, phase-16 AG-mapping enrichment]

tech-stack:
  added: []
  patterns:
    - "Module-level GAQL filter-clause builder (_apply_campaign_filter) — mirrors Phase 11 serp_fetch.py _augment_seed_with_geo composition pattern"
    - "Pipe-split heuristic for CLI input — ' | ' (spaced pipe) preserved as single name; bare '|' splits into list"

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/scripts/perf_fetch.py

key-decisions:
  - "Inserted {campaign_clause} as a separate WHERE-line via empty-string-when-absent contract — preserves v1.4 GAQL byte-identical (only whitespace difference) when filter omitted (CAMP-04)"
  - "Pipe-split heuristic: ' | ' = single name; '|' (bare) = list separator. Rationale: Google Ads naming convention 'Search | Lake Worth Accident Exams | Manual CPC' is ONE campaign — operators copy-paste these verbatim"
  - "SQL-escape single quotes by doubling (O'Brien → O''Brien) — standard GAQL string-literal handling; no backslash / newline escaping needed"
  - "campaign_filter persisted in stdout JSON for downstream traceability — downstream scripts (perf_synth, render_report) can read it from raw artifacts later if desired"

patterns-established:
  - "GAQL filter helpers live as module-level functions in the fetch script (not in lib/), keeping the filter logic colocated with the queries it modifies"
  - "Empty-clause contract: helpers return '' so callers can unconditionally inject — preserves bit-for-bit backward compat without conditional f-string branches"

requirements-completed: [CAMP-02]

duration: 3 min
completed: 2026-05-15
---

# Phase 15 Plan 01: perf_fetch --campaign-filter Summary

**Added `--campaign-filter` CLI flag + `campaign_filter` kwarg threaded through all 4 GAQL fetches in `perf_fetch.py`, narrowing search_term_view / campaign / ad_group / campaign_criterion / ad_group_criterion / keyword_view queries to operator-specified campaign(s) via SQL-escaped `AND campaign.name = '<focus>'` (single) or `IN (...)` (list).**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-15T15:12:51Z
- **Completed:** 2026-05-15T15:15:54Z
- **Tasks:** 2 / 2
- **Files modified:** 1 (perf_fetch.py)

## Accomplishments

- `_escape_gaql_string(value)` helper added — doubles inner single quotes for safe GAQL string literals (`O'Brien` → `O''Brien`)
- `_apply_campaign_filter(campaign_filter)` helper added — returns `""` for None/empty (v1.4 compat), `AND campaign.name = '<escaped>'` for single, `AND campaign.name IN ('A', 'B', ...)` for list
- All 4 fetch_* functions accept `campaign_filter: list[str] | None = None` kwarg and inject `{campaign_clause}` into their GAQL bodies (multi-query fetches `fetch_perf` and `fetch_existing_negatives` apply to BOTH queries)
- `main_with_args` adds `--campaign-filter` argparse option with the pipe-split heuristic (`' | '` preserved as single name, bare `|` splits)
- All 4 fetch_* invocations inside main now thread `campaign_filter=campaign_filter`
- stdout JSON gains `campaign_filter` key (null when absent)
- Module docstring CLI synopsis updated to include `[--campaign-filter "<name>"]`

## Task Commits

1. **Task 1: Add helpers + extend fetch_* signatures** — `3a9b7ea` (feat)
2. **Task 2: Add --campaign-filter CLI arg + thread to main** — `b21ab7f` (feat)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/perf_fetch.py` — Added 2 helpers + extended 4 fetch_* signatures with `campaign_filter` kwarg + added `--campaign-filter` CLI arg + threaded through main_with_args + stdout traceability key

## Decisions Made

- **Pipe-split heuristic**: `' | '` (space-pipe-space) preserved as a single campaign name; bare `|` splits into list. Rationale: Google Ads naming convention uses spaced pipes inside one campaign name (e.g. `Search | Lake Worth Accident Exams | Manual CPC`). Operators copy-paste these strings verbatim — auto-splitting would break the common case. The bare-pipe form `A|B|C` is the explicit opt-in for list mode.
- **Empty-clause contract**: helpers return `""` when filter is None/empty so callers can inject `{campaign_clause}` unconditionally — preserves v1.4 GAQL behavior with only a whitespace difference (test asserts substring `campaign.name =` / `campaign.name IN` does NOT appear).
- **No `lib/` extraction**: kept `_apply_campaign_filter` as module-level in `perf_fetch.py`. Single consumer, single test file, no reuse beyond this script.

## Verification

```
uv run --with pytest --with python-dotenv pytest .claude/skills/google-ad-research/scripts/tests/test_perf_fetch.py -v -k "campaign_filter"
→ 9 passed, 2 deselected

uv run --with pytest --with python-dotenv --with python-slugify --with tabulate --with respx --with httpx pytest .claude/skills/google-ad-research/scripts/tests/
→ 217 passed, 57 skipped (was 208/66 before plan; +9 = the 6 campaign_filter test functions, including 4 parametrize cases for the all-four test)

uv run .claude/skills/google-ad-research/scripts/perf_fetch.py --help | grep -i campaign-filter
→ --campaign-filter CAMPAIGN_FILTER ... CAMP-02.
```

## Deviations from Plan

None — plan executed exactly as written.

One incidental tooling note: the full-suite verification command in the plan omits `--with respx --with httpx` (required by `test_competitor_intel.py`'s respx import). This is pre-existing test-runner ergonomics, not a deviation in 15-01's scope. Added both to the verification invocation locally; no code change.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 15-01 unblocks downstream Phase 14 Positives Sync + Phase 11 AG Mapping + Phase 16 token-bag enrichment — they all inherit narrowed `raw/google-ads-*.json` artifacts automatically (CAMP-04: no code changes downstream).
- Plan 15-02 (`render_report.py` `campaign_focus` brief field + `render_campaign_focus_section` + typo warning) is unblocked and runs in parallel (different file).
- Plan 15-03 (SKILL.md Phase 8 Step 33 auto-pass `--campaign-filter "${campaign_focus}"`) waits for both 15-01 + 15-02.

## Self-Check: PASSED

- [x] `.planning/phases/15-campaign-focus/15-01-SUMMARY.md` exists
- [x] `.claude/skills/google-ad-research/scripts/perf_fetch.py` exists (modified)
- [x] Commit `3a9b7ea` exists (Task 1)
- [x] Commit `b21ab7f` exists (Task 2)
- [x] All 6 Plan 15-00 RED tests (9 parametrize cases) GREEN
- [x] Full pytest suite green (217 passed, 57 skipped, 0 failed)
- [x] `perf_fetch.py --help` exposes `--campaign-filter`

---
*Phase: 15-campaign-focus*
*Completed: 2026-05-15*
