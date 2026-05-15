---
phase: 12-source-consolidation-drop-tavily
plan: 00
subsystem: testing

tags: [pytest, tdd, red-state, audit-test, phase-12, tavily-deprecation, webfetch, serper]

# Dependency graph
requires:
  - phase: 11-account-structure-mapping
    provides: Existing tests/conftest.py with tavily_fixture; tavily_extract.py module; merge_signals.VALID_SOURCES taxonomy with tavily-extract; pulse_fetch.py with Tavily news branch; competitor_intel.py with raw_content/tavily_fetched_at fields
provides:
  - tests/test_audit_tavily_removed.py — 8-method repo-wide audit (TVLY-01..04, WFCH-01, PULSE-12, WFCH-03 import guard, all-surfaces grep)
  - tests/test_pulse_fetch.py — new file locking PULSE-10 single-source contract (no fetch_tavily_news symbol, no tavily-news.json path)
  - tests/test_pulse_synth.py::test_load_news_items_serper_only — single-source signature contract (PULSE-11)
  - tests/test_merge_signals.py::test_valid_sources_post_phase12 — 5-source taxonomy lock (WFCH-04); test_read_tavily_removed
  - tests/test_competitor_intel.py::test_advertisers_shape_post_phase12 — source-level Tavily-field guard (WFCH-03)
  - tests/test_render_report.py::test_competitor_section_joins_webfetch_results — WebFetch JOIN test with skip-guard (WFCH-02)
  - tests/fixtures/phase12-competitor-intel.json — WFCH-03-shaped advertisers fixture (Serper fields only)
  - tests/fixtures/phase12-competitor-landing-pages.json — WFCH-02 schema fixture (headline/cta/offer + extract_status)
affects:
  - Phase 12 Plan 01 (delete tavily_extract.py + .env keys + deps + fixtures)
  - Phase 12 Plan 02 (rewrite competitor_intel.py + merge_signals.py to drop Tavily)
  - Phase 12 Plan 03 (strip Tavily branch from pulse_fetch.py + pulse_synth.py)
  - Phase 12 Plan 04 (add _load_competitor_landing_pages to render_report.py + WebFetch reference rewrite + phase7 docs update)
  - Phase 12 Plan 05 (full-suite green gate + e2e smoke)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Repo-wide audit test pattern — single test file with filesystem.exists + substring scans pins every requirement; one GREEN run proves deletion complete"
    - "All-surfaces grep skipping tests/ directory — production code must be Tavily-free; test files legitimately contain 'tavily' in assertion messages"
    - "Per-function skip-guard via hasattr sentinel (_skip_unless_join_implemented) — preserves legacy GREEN tests in same file while new RED tests stage cleanly"
    - "Append-only test extensions — Phase 12 tests appended at end of test_competitor_intel.py / test_merge_signals.py / test_pulse_synth.py; pre-existing tests untouched"
    - "Source-level assertion via inspect.getsource — strongest RED-state test for symbol/field removal; complements hasattr namespace check"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/test_audit_tavily_removed.py
    - .claude/skills/google-ad-research/scripts/tests/test_pulse_fetch.py
    - .claude/skills/google-ad-research/scripts/tests/fixtures/phase12-competitor-intel.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/phase12-competitor-landing-pages.json
    - .planning/phases/12-source-consolidation-drop-tavily/12-00-SUMMARY.md
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_pulse_synth.py
    - .claude/skills/google-ad-research/scripts/tests/test_merge_signals.py
    - .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py
    - .claude/skills/google-ad-research/scripts/tests/test_render_report.py

key-decisions:
  - "All-surfaces grep test (test_repo_grep_tavily_clean) excludes tests/ directory — Phase 12 test files legitimately contain 'tavily' in assertion messages and test names; production code under scripts/ + references/ + SKILL.md is the real audit target"
  - ".venv / site-packages / __pycache__ / fixtures excluded from all-surfaces grep — third-party tavily-python package will be uninstalled by Plan 01 but venv hygiene is not the test's concern"
  - "WFCH-02 render_report test uses per-function _skip_unless_join_implemented() sentinel, NOT module-level pytestmark — mirrors Phase 10 10-00 / Phase 11 patterns; preserves 41 GREEN legacy tests in same file"
  - "WFCH-03 competitor_intel test uses BOTH inspect.getsource substring scan AND dir() namespace scan — covers source-text-only artifacts (raw_content key in dict literal) and symbol-deletion (TavilyClient import)"
  - "Phase 12 fixtures named with phase12- prefix (phase12-competitor-intel.json, phase12-competitor-landing-pages.json) — distinguishes from Phase 5 competitor_intel_full.json fixture which still carries Tavily-shape entries"

patterns-established:
  - "Audit test file pattern: 8 deterministic tests, each pinning ONE post-phase invariant, all RED against current codebase. Wave 1 flips one test GREEN per requirement."
  - "Skip-guard helper convention: _skip_unless_<feature>_implemented() functions live alongside the tests they guard; check hasattr on the production module for a sentinel symbol that Wave 1+ lands. Mirrors Phase 10/11 precedent."
  - "Append-only extension to existing test files — pre-existing Phase 11 GREEN tests preserved unchanged; new Phase 12 tests appended below with explicit '# ---- Phase 12 XXXX-NN: short description ----' section banner."

requirements-completed: []  # Wave 0 RED scaffolding has no requirement closures; each requirement closes in Wave 1+ when its test flips GREEN

# Metrics
duration: 12min
completed: 2026-05-15
---

# Phase 12 Plan 00: Wave 0 RED Test Scaffolding Summary

**6 test files (3 new + 3 extended) + 2 fixture JSONs lock the post-Phase-12 Tavily-free contract: 13 of 14 new tests FAIL, 1 SKIPS against current Phase 11 codebase; 239 legacy tests remain GREEN.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-15T02:00:00Z (approximate)
- **Completed:** 2026-05-15T02:12:00Z (approximate)
- **Tasks:** 3
- **Files created:** 4 (1 audit test, 1 pulse_fetch test, 2 fixtures)
- **Files modified:** 4 (test_pulse_synth, test_merge_signals, test_competitor_intel, test_render_report)

## Accomplishments

- **All 8 audit tests RED** against Phase 11 codebase: TVLY-01..04, WFCH-01, PULSE-12, all-surfaces grep, and competitor_intel import guard all fail. Wave 1 flips one test GREEN per requirement deletion.
- **5 unit tests RED** locking the new contracts: pulse_fetch namespace + source scan (PULSE-10); load_news_items signature (PULSE-11); VALID_SOURCES = 5-source set + read_tavily removed (WFCH-04); competitor_intel source-level Tavily-field guard (WFCH-03).
- **1 integration test SKIPS** with explicit Phase 12 sentinel — render_report WebFetch JOIN test (WFCH-02) waits on Wave 2 plan 12-04's `_load_competitor_landing_pages` helper. Per-function guard mirrors Phase 10/11 pattern.
- **Two fixture JSONs committed** to fixtures/: phase12-competitor-intel.json (WFCH-03 advertisers shape) and phase12-competitor-landing-pages.json (WFCH-02 captured-content shape).
- **Zero regressions on 239 pre-existing tests** — every Phase 1-11 test still GREEN.

## Task Commits

Each task committed atomically:

1. **Task 1: tests/test_audit_tavily_removed.py — repo-wide audit** — `9ea9ae8` (test)
2. **Task 2: tests/test_pulse_fetch.py + extend pulse_synth / merge_signals / competitor_intel** — `8121628` (test)
3. **Task 3: tests/test_render_report.py + phase12 fixtures** — `191e997` (test)

**Final RED-state suite result:** `14 failed, 239 passed, 1 skipped in 12.59s`

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/tests/test_audit_tavily_removed.py` — 157 lines, 8 audit tests (TVLY-01..04, WFCH-01, PULSE-12, all-surfaces grep, competitor_intel import guard)
- `.claude/skills/google-ad-research/scripts/tests/test_pulse_fetch.py` — 43 lines, 2 tests pinning PULSE-10 (no fetch_tavily_news symbol, no tavily-news.json path)
- `.claude/skills/google-ad-research/scripts/tests/test_pulse_synth.py` — appended test_load_news_items_serper_only (PULSE-11)
- `.claude/skills/google-ad-research/scripts/tests/test_merge_signals.py` — appended test_valid_sources_post_phase12 + test_read_tavily_removed (WFCH-04)
- `.claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py` — appended test_advertisers_shape_post_phase12 (WFCH-03)
- `.claude/skills/google-ad-research/scripts/tests/test_render_report.py` — appended test_competitor_section_joins_webfetch_results + _skip_unless_join_implemented helper (WFCH-02)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/phase12-competitor-intel.json` — 2 advertisers in Serper-only shape (domain/url/title/description/position)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/phase12-competitor-landing-pages.json` — same 2 advertisers with WebFetch shape (headline/cta/offer/extract_status)

## Decisions Made

- **All-surfaces grep skips tests/ + .venv + site-packages + __pycache__ + fixtures** — Phase 12 test files legitimately contain "tavily" in assertion messages (e.g., `assert "tavily-extract" not in VALID_SOURCES`). The audit's real target is production code under scripts/ (production .py) + references/ + SKILL.md. Without this, the audit would FAIL forever even after Wave 1 deletes all Tavily code.
- **Per-function `_skip_unless_join_implemented()` for WFCH-02** rather than module-level `pytestmark` — test_render_report.py already hosts 41 GREEN Phase 6/9/10/11 tests; module-level skip would regress them. Mirrors Phase 10 10-00 / Phase 11 11-02 patterns documented in STATE.md.
- **WFCH-03 uses BOTH inspect.getsource substring scan AND dir() namespace scan** — covers Tavily-shape dict-literal keys (`"raw_content": result.get("raw_content", "")`) which dir() can't catch, AND covers TavilyClient import which substring catches in module bytecode but namespace check makes explicit.
- **Phase 12 fixtures named with `phase12-` prefix** — distinguishes from Phase 5 `competitor_intel_full.json` which still carries Phase-11-shape (Tavily) entries used by 41 GREEN render_report tests.
- **Sentinel function name `_load_competitor_landing_pages`** chosen as the hasattr probe for WFCH-02 — Wave 2 plan 12-04 will land this helper on render_report. Decision recorded so plan-12-04 author knows the exact symbol name.

## Deviations from Plan

None significant — plan executed as written. Minor refinements applied during execution:

1. **All-surfaces grep skip list expanded** beyond plan's `{__pycache__, fixtures}` → added `.venv, venv, site-packages, tests, .runs, .pytest_cache` after initial test run revealed the third-party `tavily-python` package inside `.venv/Lib/site-packages/tavily/` was being picked up as offender. Plan's intent (audit production code only) preserved; implementation tightened. No requirement impact.
2. **test_no_tavily_news_path_in_main** named per plan; checks for `tavily-news.json` literal AND case-insensitive `tavily` substring in pulse_fetch source. Both assertions retained per plan spec.

**Total deviations:** 0 functional, 1 implementation tightening (SKIP_DIRS expanded for venv hygiene).
**Impact on plan:** Zero scope drift. RED-state contract preserved.

## Issues Encountered

- **First audit run flagged 27 offenders** including `.venv/Lib/site-packages/tavily/` — expected for Wave-0 RED, but `.venv` would remain flagged forever (third-party package, not project code). Resolved by adding `.venv / venv / site-packages` to SKIP_DIRS. Also added `tests/` to SKIP_DIRS for the same reason (Phase 12 tests contain "tavily" in their assertion strings by design).
- **test_merge_signals tests skipped on first run** due to `inflect` package not in default `--with` args. Resolved by adding `--with inflect` to the test command. This is a local environment quirk (uv hadn't auto-resolved transitive deps); does not block CI / will resolve automatically once Phase 12 Plan 05 runs the full suite via `--project` with proper dep resolution.

## User Setup Required

None — Wave 0 is pure test scaffolding. No env vars, no API keys, no external services touched.

## Next Phase Readiness

**Wave 0 deliverable contract:** 14 new tests in RED state + 1 in SKIP state. Wave 1 plans (12-01, 12-02, 12-03) each flip a subset of the audit + unit tests to GREEN; Wave 2 plan (12-04) lifts the SKIP on the JOIN test by landing `_load_competitor_landing_pages` on render_report.py. Wave 3 plan (12-05) gates milestone close on full-suite GREEN + `grep -rni tavily .` returning zero matches outside `.planning/`.

**Suite baseline for Wave 1 entry:**
- `14 failed, 239 passed, 1 skipped` (per validation: `pytest .claude/skills/google-ad-research/scripts/tests/`)
- Quick-run command: `pytest tests/test_audit_tavily_removed.py tests/test_pulse_fetch.py -x` should show 10 failed (8 audit + 2 pulse_fetch)
- Skip sentinel: `hasattr(render_report, "_load_competitor_landing_pages") == False` on Phase 11 codebase

**Ready for Plan 12-01:** Delete tavily_extract.py → flips `test_tavily_extract_deleted` GREEN; strip TAVILY_API_KEY from .env.example + lib/config.py → flips `test_tavily_env_keys_stripped` GREEN; remove tavily-python from pyproject.toml → flips `test_tavily_deps_and_fixtures_stripped` GREEN; delete test_tavily_extract.py + tavily_fixture from conftest → flips `test_tavily_test_artifacts_stripped` + `test_tavily_test_artifacts_stripped` GREEN.

No blockers. No open questions.

## Self-Check: PASSED

All 6 test files exist on disk:
- FOUND: .claude/skills/google-ad-research/scripts/tests/test_audit_tavily_removed.py
- FOUND: .claude/skills/google-ad-research/scripts/tests/test_pulse_fetch.py
- FOUND: .claude/skills/google-ad-research/scripts/tests/test_pulse_synth.py (extended)
- FOUND: .claude/skills/google-ad-research/scripts/tests/test_merge_signals.py (extended)
- FOUND: .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py (extended)
- FOUND: .claude/skills/google-ad-research/scripts/tests/test_render_report.py (extended)
- FOUND: .claude/skills/google-ad-research/scripts/tests/fixtures/phase12-competitor-intel.json
- FOUND: .claude/skills/google-ad-research/scripts/tests/fixtures/phase12-competitor-landing-pages.json

All 3 task commits exist:
- FOUND: 9ea9ae8 (Task 1 audit)
- FOUND: 8121628 (Task 2 unit tests)
- FOUND: 191e997 (Task 3 WFCH-02 + fixtures)

RED-state verified: `14 failed, 239 passed, 1 skipped in 12.59s` from full-suite run.

---
*Phase: 12-source-consolidation-drop-tavily*
*Completed: 2026-05-15*
