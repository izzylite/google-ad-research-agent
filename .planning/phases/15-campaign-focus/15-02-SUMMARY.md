---
phase: 15-campaign-focus
plan: 02
subsystem: rendering
tags: [render_report, campaign_focus, brief-parser, report-json, CAMP-01, CAMP-05]

requires:
  - phase: 15-00
    provides: 9 RED tests (3 parser + 6 render) skip-guarded on render_campaign_focus_section / campaign_focus key
  - phase: 11
    provides: render_geographic_focus_section architectural template + _parse_brief_fields shape
provides:
  - "_parse_brief_fields emits campaign_focus key (raw string, '' when absent)"
  - "_split_campaign_focus helper (shared pipe-split heuristic: ' | ' = single name, '|' = list)"
  - "render_campaign_focus_section(brief_fields, *, perf_path=None) with name-validation warning"
  - "Main render pipeline inserts Campaign Focus between Geographic Focus and Compliance"
  - "report.json top-level campaign_focus key (list[str])"
affects: [phase-15-03 SKILL.md wiring, phase-16 AG-mapping enrichment]

tech-stack:
  added: []
  patterns:
    - "Shared pipe-split heuristic with perf_fetch — ' | ' preserved as single Google Ads name, bare '|' splits"
    - "Optional perf_path kwarg for name validation — graceful degrade when file absent/unparseable"
    - "Campaign names bypass escape_md_cell (preserves operator-facing pipe naming convention)"

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/scripts/render_report.py

key-decisions:
  - "Pipe-split heuristic mirrors Plan 15-01 perf_fetch (' | ' = single; '|' = list) — operators copy-paste Google Ads names verbatim, auto-split would break common case"
  - "Campaign names NOT escape_md_cell'd — pipes are a labelling convention in Google Ads names; escaping breaks operator recognition (contrasts with GEO-05 which escapes city names)"
  - "Name validation is case-sensitive — Google Ads API preserves case and enforces uniqueness; soft-matching would risk false negatives on real typos"
  - "Validation graceful-degrades on FileNotFoundError / JSONDecodeError / OSError — perf.json being absent is a legitimate v1.4 pre-Phase-14 state, not an error"
  - "Section order: Geographic Focus → Campaign Focus → Compliance Required — narrowed scope context surfaces before any keyword work"

patterns-established:
  - "Brief-field render helpers follow GEO-05 contract: raw string in parser, list-split + render in helper, list in report.json"
  - "Name-validation via optional perf_path kwarg keeps helper testable without filesystem when perf_path=None"

requirements-completed: [CAMP-01, CAMP-05]

duration: 2 min
completed: 2026-05-15
---

# Phase 15 Plan 02: render_report campaign_focus Summary

**Extended `render_report.py` with a `campaign_focus` brief field parser + `render_campaign_focus_section` callout + typo-warning name validation against `raw/google-ads-perf.json` — surfaces the operator's narrowed scope at the top of `report.md` (between Geographic Focus and Compliance) and adds a `campaign_focus` list key to `report.json`, mirroring Phase 11's GEO-05 architecture at the campaign-name level.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-15T15:19:46Z
- **Completed:** 2026-05-15T15:21:53Z
- **Tasks:** 2 / 2
- **Files modified:** 1 (render_report.py)

## Accomplishments

- `_parse_brief_fields` extracts `campaign_focus` via new regex `^[-*\s]*\*\*Campaign\s*focus:\*\*\s*(.+)$` (case-insensitive, multiline); raw string returned, empty when absent — mirrors `geo_focus` contract exactly.
- `_split_campaign_focus(raw)` helper added at module level; applies the shared pipe-split heuristic (spaced-pipe preserved as one name; bare-pipe splits).
- `render_campaign_focus_section(brief_fields, *, perf_path=None)` renders `## Campaign Focus` heading + single (`**Campaign:** <name>`) or bulleted-list form; emits `> ⚠ Campaign name not found in account: '<name>' — check for typo` warning per mismatched name when `perf_path` provided and name not in `perf_data["campaigns"][].name` set.
- Validation graceful-degrades on `FileNotFoundError`, `json.JSONDecodeError`, `OSError` — perf.json absent or unparseable yields no warning (legitimate pre-Phase-14 state).
- Main render pipeline (`build_report_md`) inserts `camp_md` between `geo_md` and `compliance_md`; both are appended only when non-empty (graceful degrade).
- `report.json` builder gains top-level `campaign_focus` key (list[str], empty list when absent), positioned beside `geographic_focus`.
- 9 Plan 15-00 RED tests flip GREEN: 3 parser + 3 section rendering + 3 name-validation.
- Full pytest suite: 226 passed, 48 skipped, 0 failed (up from 217/57 — picked up the 9 unblocked tests).

## Task Commits

1. **Task 1: Extend `_parse_brief_fields` with `campaign_focus` key (CAMP-01)** — `9e589d2` (feat)
2. **Task 2: Add `render_campaign_focus_section` + pipeline wiring + report.json key (CAMP-05)** — `6bbad29` (feat)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/render_report.py` — Extended `_parse_brief_fields` docstring + new regex; added `_split_campaign_focus` helper; added `render_campaign_focus_section`; wired `camp_md` into `build_report_md` between Geographic Focus and Compliance; added `campaign_focus` key to `report.json` builder.

## Decisions Made

- **Pipe-split heuristic shared with Plan 15-01:** `' | '` (spaced pipe) preserved as one Google-Ads-naming-convention campaign name; bare `|` (no spaces) splits into list. Rationale: operators copy-paste names like `Search | Lake Worth Accident Exams | Manual CPC` verbatim; auto-splitting would break the common case. Bare `A|B|C` is the explicit list opt-in.
- **Campaign names bypass `escape_md_cell`:** Pipes are an intentional labelling convention in Google Ads campaign names. Escaping them to `\|` would break operator recognition. (Contrasts with GEO-05, which routes city names through `escape_md_cell` because city names rarely contain markdown-special chars.)
- **Case-sensitive name validation:** Google Ads API preserves case and enforces uniqueness on `campaign.name`. A soft-match (lowercased compare) would risk false negatives on real typos. Mismatches emit the `⚠` warning quoting the exact operator input verbatim.
- **Section order — Geo → Campaign → Compliance:** Both scope-narrowing callouts surface adjacent to each other at the top of the report, before compliance warnings and any keyword work. This is the operator's narrowed-scope context block.
- **Empty list (not None) for report.json `campaign_focus` when absent:** Mirrors `geographic_focus.focus` shape — downstream JS / sidecar tooling can rely on a stable list type.

## Verification

```
uv run --with pytest --with python-dotenv --with python-slugify --with tabulate \
  pytest .claude/skills/google-ad-research/scripts/tests/test_render_report.py -v \
  -k "campaign_focus or parse_brief_fields_campaign or parse_brief_fields_extracts_campaign"
→ 9 passed, 46 deselected

uv run --with pytest --with python-dotenv --with python-slugify --with tabulate --with respx --with httpx \
  pytest .claude/skills/google-ad-research/scripts/tests/
→ 226 passed, 48 skipped, 0 failed
```

No regression: Phase 11 GEO-05, Phase 14 positives-sync, Phase 6 render, Plan 15-01 perf_fetch `--campaign-filter` tests all still pass.

## Deviations from Plan

None — plan executed exactly as written. Two minor planner-discretion calls resolved during execution:

1. **Extracted `_split_campaign_focus` as a module-level helper** rather than inlining the split twice (`render_campaign_focus_section` + `report.json` builder). Single source of truth for the heuristic; trivial to keep consistent with Plan 15-01's CLI parser if the heuristic is ever revised.
2. **Trailing newline after warnings block** when warnings present — minor cosmetic addition for cleaner section separation in the rendered markdown; not strictly required by any test.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 15-02 unblocks Plan 15-03 (SKILL.md Phase 8 Step 33 auto-pass `--campaign-filter "${campaign_focus}"`). Both Wave 2 plans (15-01 perf_fetch, 15-02 render_report) are now complete; 15-03 wires SKILL.md to call them together.
- Operators can now see Campaign Focus prominently in `report.md` header with typo protection — before they conclude an empty sync section is a clean account vs. a misspelled campaign name (CAMP-05 design intent).
- `report.json.campaign_focus` is stable for downstream sidecar tooling (export_csv, future Phase 16 AG-mapping calibration which needs to know which campaign was narrowed).

## Self-Check: PASSED

- [x] `.planning/phases/15-campaign-focus/15-02-SUMMARY.md` exists
- [x] `.claude/skills/google-ad-research/scripts/render_report.py` exists (modified)
- [x] Commit `9e589d2` exists (Task 1 — parser)
- [x] Commit `6bbad29` exists (Task 2 — section + pipeline + report.json)
- [x] All 9 Plan 15-00 RED campaign_focus tests GREEN
- [x] Full pytest suite green (226 passed, 48 skipped, 0 failed)
- [x] `render_campaign_focus_section` callable, `campaign_focus` key present in `_parse_brief_fields` output

---
*Phase: 15-campaign-focus*
*Completed: 2026-05-15*
