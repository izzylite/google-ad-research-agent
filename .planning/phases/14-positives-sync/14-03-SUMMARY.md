---
phase: 14-positives-sync
plan: 03
subsystem: render-report

tags: [render_report, render_positives_sync_section, positives-sync, pos-03, pos-05, graceful-omit, html-section, json-key]

# Dependency graph
requires:
  - phase: 14-positives-sync
    provides: positives-sync.json envelope shape (4 buckets + 5-count stats) — Plan 14-02 cross_ref_positives writer
  - phase: 14-positives-sync
    provides: Wave 0 RED stubs in test_render_report.py + golden_positives_sync.json fixture (Plan 14-00)
provides:
  - render_report.render_positives_sync_section(sync) -> str (markdown helper, mirrors render_negatives_sync_section)
  - render_report.USAGE_POS_SYNC explainer constant
  - build_report `positives_sync` kwarg + adjacent-to-negatives-sync markdown wiring
  - render_html_report `<section id="positives-sync">` block + renderPositivesSync() JS function (collapsible audit buckets)
  - build_report_json `positives_sync` kwarg + `positives_sync` key in output dict (empty {} when absent)
  - main {run_dir}/positives-sync.json sidecar loader (graceful None on absent / JSONDecodeError — POS-05)
  - 3 Wave 0 render_positives_sync_section RED stubs flipped SKIP -> PASS (omit-when-absent already PASSED via getattr-default)
affects: [14-04, 14-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mirror-and-adapt: render_positives_sync_section line-for-line parallels render_negatives_sync_section — same graceful-empty-string guard, same escape_md_cell sanitisation, same load-then-thread main pattern. Future maintainers can read either function as a template for the other."
    - "Bucket display split: new_to_add enumerated (action-this-week), audit buckets count-only with 'see positives-sync.json' pointer — keeps report.md scannable without losing the audit trail (full data lives in the JSON sidecar)."
    - "HTML collapsibles asymmetric: new_to_add `<details open>`, audit buckets collapsed — surfaces the action item by default, hides audit clutter until clicked. Mirrors how renderNegativesSync handles tiers (Strong open, others collapsed)."
    - "POS-05 graceful omit: file-presence check in main + empty-string return from render helper means absent sidecar is normal flow, never an error path. Mirrors negatives-sync / account-perf / forecast / compliance sidecar pattern."

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/scripts/render_report.py

key-decisions:
  - "USAGE_POS_SYNC explainer placed adjacent to USAGE_NEG_SYNC at module top (not inside the function) — matches USAGE_NEG_SYNC / USAGE_KEYWORDS pattern; keeps copy editable without touching logic"
  - "render_positives_sync_section returns '' when stats key absent OR sync empty — caller wraps in `if positives_sync:` so the markdown path appends nothing when stats missing; tighter than negatives-sync (which returns a partial section with zero counts). Rationale: positives sync envelope without stats is a malformed sidecar, not a normal case."
  - "Audit buckets render as count-only level-3 headings + 'See positives-sync.json for the full list' pointer (NOT collapsible details in markdown). Matches the test contract (`urgent care lake worth not in md`) and keeps the report under operator scroll budget. HTML path uses collapsible <details> instead — different medium, different affordance."
  - "Justification field falls back through r.get('justification') -> r.get('theme') -> '' chain — golden fixture has neither populated on new_to_add rows, so output renders as `- \\`kw\\` · _intent_` without trailing em-dash; conditional check on `if just` keeps the markdown clean."
  - "HTML <section> placed immediately AFTER <section id='negatives-sync'> to keep the DOM order matching markdown order; renderPositivesSync() call wedged between renderNegativesSync and renderNegatives in the bootstrap line for visual / execution parallelism."
  - "build_report + build_report_json + main all accept positives_sync as positional-after-keyword (after negatives_sync, before forecast) — keeps the argument ordering grouped: account_perf -> negatives_sync -> positives_sync -> forecast -> compliance. Lexically adjacent kwargs make future audit-grade reviews easier."

requirements-completed: [POS-03, POS-05]

# Metrics
duration: ~4min
completed: 2026-05-15
---

# Phase 14 Plan 03: render_positives_sync_section Summary

**Wires Phase 14's positives-sync data into the operator-facing report. Adds `render_positives_sync_section` to `render_report.py` (mirrors `render_negatives_sync_section`), a parallel HTML `<section id="positives-sync">` block with collapsible audit buckets, a `positives_sync` key in `report.json`, and a `{run_dir}/positives-sync.json` loader in `main`. POS-03 satisfied across md + HTML + JSON outputs; POS-05 graceful omit preserves the no-OAuth path.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-15T12:38:42Z
- **Completed:** 2026-05-15T12:42:24Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `USAGE_POS_SYNC` module-level constant added adjacent to `USAGE_NEG_SYNC` — single source of operator-facing copy for the section
- `render_positives_sync_section(sync) -> str` mirrors `render_negatives_sync_section`:
  - Graceful empty-string omit when `sync` is None / empty / missing `stats` key (POS-05)
  - Stats line: `our list = N · already active = N · paused = N · covered by broad = N · new to add = **N**`
  - `new_to_add` rows enumerated as `` - `keyword` · _intent_ — justification ``
  - `already_active` / `paused_in_account` / `covered_by_broad` render as count-only level-3 headings + "See positives-sync.json for the full list" pointer
  - All keyword text routed through `escape_md_cell` for pipe / smart-quote safety
- `build_report` markdown path: `positives_sync: dict | None = None` kwarg added; section appended immediately after the existing `render_negatives_sync_section` call so Positives Sync sits adjacent to Negative Keyword Sync visually
- `render_html_report` HTML path: `<section id="positives-sync">` block emitted with fallback paragraph when sidecar absent; `renderPositivesSync()` JS function added — stats div + `<details open>` for new_to_add + collapsed `<details>` for each audit bucket; hooked into the bootstrap call list between `renderNegativesSync` and `renderNegatives`
- `build_report_json`: `positives_sync: dict | None = None` kwarg added; `"positives_sync": positives_sync or {}` key threaded into output dict adjacent to existing `"negatives_sync"` key
- `main`: parallel `positives-sync.json` loader added directly after the negatives-sync block; graceful `None` on absent file or `json.JSONDecodeError`; threaded `positives_sync=positives_sync` into both `render_full_report` and `build_report_json` calls
- 3 Wave 0 RED stubs flipped SKIP -> PASS (`test_render_positives_sync_section_renders_stats_line`, `test_render_positives_sync_section_enumerates_new_to_add`, `test_render_positives_sync_section_count_only_for_other_buckets`); the 4th (`test_render_positives_sync_section_omits_when_absent`) was already PASSED in Wave 0 via the `getattr` default lambda
- Full test suite: **256 passed, 0 skipped** (was 250 passed, 6 skipped) — +6 PASS, -6 SKIP vs pre-plan baseline; 0 regressions

## Test Suite Reconciliation

- **Pre-plan baseline:** 250 passed, 6 skipped (per 14-02-SUMMARY)
- **Post-plan actual:** 256 passed, 0 skipped
- **Delta:** All 6 remaining SKIPs cleared. 3 of those (`test_render_positives_sync_section_*`) were the direct target of this plan and are confirmed flipped. The other 3 (Plan 14-04 export-filter SKIPs) cleared as a side-effect — investigation: re-running `pytest -v | grep -i skip` after this plan returned zero actual `SKIPPED` lines (only test names containing "skip" matched, all PASSED). Probable explanation: the Wave 0 `_skip_unless_positives_sync_filter` guard checks `export_csv._POSITIVES_SYNC_SUPPORTED` sentinel; the sentinel may have been set earlier than tracked, OR the export-csv tests' assertions pass against the existing v1.0 fallback path even before Plan 14-04 lands the filter logic. Plan 14-04 should re-verify whether those tests still cover the intended contract, and tighten the assertions if they have become tautologies.

## Task Commits

1. **Task 1: Implement render_positives_sync_section + USAGE_POS_SYNC** — `7d0b0f7` (feat)
2. **Task 2: Wire positives_sync through build_report + HTML + JSON + main** — `b5b35a9` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified

### Modified
- `.claude/skills/google-ad-research/scripts/render_report.py` — +129 lines (70 for section helper + USAGE constant in Task 1; 59 for build_report / HTML / build_report_json / main wiring in Task 2)

## Decisions Made

See `key-decisions:` frontmatter for the full list. Summary:

1. **USAGE_POS_SYNC at module top** — matches USAGE_NEG_SYNC pattern; copy lives separately from logic.
2. **Tighter empty-stats guard** — return `""` when `stats` key absent (not partial-section with zeros). Malformed sidecar = silent omit, not a half-rendered section.
3. **Audit buckets count-only in markdown, collapsible in HTML** — different affordances per medium; markdown stays scannable, HTML offers drill-down.
4. **Justification fallback chain** — `justification` -> `theme` -> `''` with `if just` guard avoids trailing em-dash when both empty.
5. **HTML section + JS hook adjacent to negatives-sync** — DOM order matches markdown order; visual + execution parallelism.
6. **Argument grouping in build_report*** — `account_perf -> negatives_sync -> positives_sync -> forecast -> compliance` keeps lexically related kwargs together for audit reviews.

## Deviations from Plan

**None** — plan executed exactly as written. All 4 Wave 0 section tests passed on first run after Task 1; full suite stayed clean after Task 2. Smoke tests (present + absent) confirmed graceful behaviour matches POS-05 contract.

The plan's optional "_HTML JS hook only if Wave 0 test exercises it_" caveat was resolved in favour of shipping the full `renderPositivesSync()` consumer in Task 2 — the HTML `<section>` was already being added for parity, and the JS hook is small / self-contained / no test gate, so deferring it would have left a permanent fallback paragraph as the only HTML signal.

## Issues Encountered

None. Wave 0 fixtures + RED stubs + golden positives-sync envelope all wired correctly. Both Task 1 (helper) and Task 2 (wiring) passed targeted + full-suite tests on first run.

One smoke-test trip-up worth noting: bash `python -c "..."` initially failed to read `report.json` because the temp dir path was POSIX-translated under MSYS; rerunning via `uv run python` with `sys.argv[1]` arg passing fixed it. No production code involved.

## Smoke Verification

- **Happy path** (positives-sync.json present, golden fixture):
  - `report.md` carries `## Positives Sync` (1 occurrence) + correct stats line: `our list = 5 · already active = 1 · paused = 1 · covered by broad = 1 · new to add = **2**`
  - `report.html` carries 3 `positives-sync` substrings (section id + JS meta hook + content hook)
  - `report.json` has `positives_sync.stats.our_total == 5` + 2 rows in `new_to_add`
- **Absent path** (positives-sync.json removed):
  - `report.md` `## Positives Sync` count = 0 (graceful omit per POS-05)
  - All other section headings present and correct (Geographic Focus, Ad Group Clusters, Negative Keywords, etc.)
  - Exit code 0, no error surfaced

## Self-Check

- File modified: `.claude/skills/google-ad-research/scripts/render_report.py` — `render_positives_sync_section` defined; `USAGE_POS_SYNC` defined; `build_report` + `build_report_json` accept `positives_sync` kwarg; main reads `positives-sync.json` and threads through to both calls; HTML section + JS function added
- Commits found via `git log --oneline -5`: `7d0b0f7` (Task 1) + `b5b35a9` (Task 2) — both present
- Targeted tests: 4/4 PASSED in `test_render_report.py::test_render_positives_sync_section_*`
- Full suite: **256 passed, 0 skipped** — delta +6 PASS, -6 SKIP vs pre-plan baseline; 0 regressions
- Smoke: happy path renders section with golden data; absent path omits gracefully across md + json + html

## Self-Check: PASSED

## Next Phase Readiness

- **Plan 14-04 (`export_csv` filter + `--include-existing`)** is now unblocked: `positives-sync.json` schema is the source of truth across the entire render path; CSV filter logic can read the same sidecar without coordination. Plan 14-04 runs in parallel with this plan (different file) — atomic per-task commits ensure no merge conflicts.
- **Plan 14-05 (SKILL.md LLM re-tag step + closeout)** can now reference the rendered report sections in its anchor examples (operator-facing copy is locked).
- 3 export-filter SKIPs unexpectedly flipped to PASS during this plan's full-suite run — Plan 14-04 should re-verify whether those tests still cover the intended contract or have become tautologies. If tautological, Plan 14-04 strengthens the assertions; if substantive, the filter logic is already partially exercised by upstream stubs.

---
*Phase: 14-positives-sync*
*Completed: 2026-05-15*
