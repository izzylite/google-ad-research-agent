---
phase: 12-source-consolidation-drop-tavily
plan: 01
subsystem: integrations

tags: [tavily-deprecation, tvly-01, tvly-02, tvly-03, tvly-04, deletion-only, parallel-wave-1, audit-test-green]

# Dependency graph
requires:
  - phase: 12-source-consolidation-drop-tavily
    plan: 00
    provides: tests/test_audit_tavily_removed.py with 4 RED TVLY-* audit tests + tavily_fixture in conftest + tavily_extract.py + test_tavily_extract.py + tavily-python in pyproject.toml + TAVILY_API_KEY in .env.example/lib/config.py
provides:
  - Removal of scripts/tavily_extract.py (162-line PEP 723 helper deleted from disk)
  - Removal of tests/test_tavily_extract.py (4 tests, 131 lines deleted)
  - Removal of 3 tavily fixture JSONs (tavily_extract_2urls.json, tavily_lp_response.json, tavily_news.json)
  - Removal of tavily_fixture() from tests/conftest.py
  - TAVILY_API_KEY stripped from .env.example
  - REQUIRED_KEYS in lib/config.py reduced to single-element tuple ("SERPER_API_KEY",)
  - tavily-python>=0.7.24 removed from scripts/pyproject.toml dependencies
  - uv.lock regenerated — tavily-python + 5 transitive deps (charset-normalizer, regex, requests, tiktoken, urllib3) removed
  - TVLY-01, TVLY-02, TVLY-03, TVLY-04 audit tests flipped RED → GREEN
affects:
  - Phase 12 Plan 02 (competitor_intel.py refactor — now sees REQUIRED_KEYS=("SERPER_API_KEY",) when calling load_env)
  - Phase 12 Plan 03 (pulse_fetch.py refactor — same lib/config.py contract; tavily-news.json path absent)
  - Phase 12 Plan 05 (full-suite GREEN gate — 4 TVLY-* assertions now lock the post-deletion contract)

# Tech tracking
tech-stack:
  removed:
    - "tavily-python>=0.7.24 (direct dep)"
    - "charset-normalizer (transitive via tavily-python)"
    - "regex (transitive via tavily-python)"
    - "requests (transitive via tavily-python)"
    - "tiktoken (transitive via tavily-python)"
    - "urllib3 (transitive via tavily-python)"
  patterns:
    - "Deletion-only plan pattern — file ownership disjoint from parallel wave plans (12-02 owns competitor_intel.py + merge_signals.py; 12-03 owns pulse_fetch.py + pulse_synth.py); no refactor in this plan"
    - "Two-task atomic split — Task 1 deletes files, Task 2 edits configs; per-task verification against named audit-test subset"
    - "uv lock as a metadata operation (NOT uv sync) — works even when downstream imports still reference removed package, because lock resolution does not import target packages"

key-files:
  deleted:
    - .claude/skills/google-ad-research/scripts/tavily_extract.py
    - .claude/skills/google-ad-research/scripts/tests/test_tavily_extract.py
    - .claude/skills/google-ad-research/scripts/tests/fixtures/tavily_extract_2urls.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/tavily_lp_response.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/tavily_news.json
  modified:
    - .env.example  # removed TAVILY_API_KEY=tvly-... line
    - .claude/skills/google-ad-research/scripts/lib/config.py  # REQUIRED_KEYS dropped TAVILY_API_KEY
    - .claude/skills/google-ad-research/scripts/pyproject.toml  # removed tavily-python>=0.7.24
    - .claude/skills/google-ad-research/scripts/uv.lock  # regenerated cleanly
    - .claude/skills/google-ad-research/scripts/tests/conftest.py  # removed tavily_fixture()
  created:
    - .planning/phases/12-source-consolidation-drop-tavily/12-01-SUMMARY.md

key-decisions:
  - "uv.lock regenerated cleanly during Task 2 (NOT deferred to Plan 02). Plan permitted deferral if lock failed due to lingering tavily imports, but `uv lock` is a metadata-only resolve (does not import target packages) so it succeeded against the current scripts/ state where competitor_intel.py + pulse_fetch.py still imported tavily. 5 transitive deps auto-pruned."
  - "Task 2 commit was absorbed by parallel agent (Plan 12-03) commit f153729 — both plans edited identical files (.env.example, lib/config.py, pyproject.toml, uv.lock) because both needed the same Tavily-key deletions. Parallel-wave note specified file ownership disjoint, but these 4 shared-config files are inherently shared. Net result on disk is identical to plan spec; only commit attribution differs. No data loss."
  - "Per the parallel-wave note, scripts/pulse_fetch.py + scripts/competitor_intel.py edits remained out-of-scope for this plan — verified by inspecting `git diff --cached` before commit: only Task 2 owned files staged."

requirements-completed:
  - TVLY-01  # tavily_extract.py deleted (test_tavily_extract_deleted GREEN)
  - TVLY-02  # TAVILY_API_KEY stripped from .env.example + lib/config.py (test_tavily_env_keys_stripped GREEN)
  - TVLY-03  # tavily-python removed from pyproject.toml + fixtures deleted (test_tavily_deps_and_fixtures_stripped GREEN)
  - TVLY-04  # test_tavily_extract.py + tavily_fixture removed (test_tavily_test_artifacts_stripped GREEN)

# Metrics
duration: ~2min
completed: 2026-05-15
---

# Phase 12 Plan 01: Drop Tavily — Pure Deletion Summary

**5 files deleted, 4 files edited, 4 of 8 Wave 0 audit tests flipped RED → GREEN. Tavily artifacts this plan owns (script + test + env key + dep + fixture function + 3 fixture JSONs) are gone from disk; remaining tavily references (in competitor_intel.py, merge_signals.py, pulse_synth.py, SKILL.md, references/) belong to parallel plans 12-02 / 12-03 and downstream plan 12-04.**

## Performance

- **Duration:** ~2 min (start 2026-05-15T03:53:12Z, end 2026-05-15T03:55:10Z)
- **Tasks:** 2 (both verified GREEN against named audit subset)
- **Files deleted:** 5 (1 script, 1 test, 3 fixtures)
- **Files modified:** 4 (.env.example, lib/config.py, scripts/pyproject.toml, scripts/tests/conftest.py)
- **Files regenerated:** 1 (uv.lock)

## Accomplishments

- **TVLY-01 GREEN** — `scripts/tavily_extract.py` deleted from disk; `test_tavily_extract_deleted` passes.
- **TVLY-02 GREEN** — `TAVILY_API_KEY` stripped from `.env.example` (line removed) AND from `lib/config.py` REQUIRED_KEYS (now `("SERPER_API_KEY",)`); `test_tavily_env_keys_stripped` passes.
- **TVLY-03 GREEN** — `tavily-python>=0.7.24` removed from `scripts/pyproject.toml`; 3 `*tavily*` fixture files deleted; `test_tavily_deps_and_fixtures_stripped` passes.
- **TVLY-04 GREEN** — `tests/test_tavily_extract.py` deleted; `tavily_fixture()` definition removed from `tests/conftest.py`; `test_tavily_test_artifacts_stripped` passes.
- **uv.lock regenerated cleanly** — `uv lock --project .claude/skills/google-ad-research/scripts` resolved 19 packages in 521ms; removed tavily-python plus 5 transitive deps (charset-normalizer, regex, requests, tiktoken, urllib3).
- **Parallel-wave isolation maintained on the deletion-owned files** — `scripts/competitor_intel.py`, `scripts/merge_signals.py`, `scripts/pulse_fetch.py`, `scripts/pulse_synth.py` NOT touched in this plan (those belong to plans 12-02 + 12-03).

## Task Commits

1. **Task 1: Delete tavily_extract.py + test file + 3 fixture JSONs; strip tavily_fixture from conftest.py** — `93c785f` (feat). 6 files changed, 355 deletions. Verification: `test_tavily_extract_deleted` + `test_tavily_test_artifacts_stripped` PASS.
2. **Task 2: Strip TAVILY_API_KEY from .env.example + lib/config.py; remove tavily-python from pyproject.toml; regenerate uv.lock** — absorbed by `f153729` (parallel Plan 12-03 commit). See "Issues Encountered" below. Verification: `test_tavily_env_keys_stripped` + `test_tavily_deps_and_fixtures_stripped` PASS.

## Files Created/Modified/Deleted

**Deleted (5):**
- `.claude/skills/google-ad-research/scripts/tavily_extract.py` (162 lines — PEP 723 stdlib + tavily-python wrapper)
- `.claude/skills/google-ad-research/scripts/tests/test_tavily_extract.py` (131 lines — 4 tests)
- `.claude/skills/google-ad-research/scripts/tests/fixtures/tavily_extract_2urls.json`
- `.claude/skills/google-ad-research/scripts/tests/fixtures/tavily_lp_response.json`
- `.claude/skills/google-ad-research/scripts/tests/fixtures/tavily_news.json`

**Modified (5):**
- `.env.example` — removed line `TAVILY_API_KEY=tvly-...` ; kept `SERPER_API_KEY=...` ; preserved trailing newline + leading comment.
- `.claude/skills/google-ad-research/scripts/lib/config.py` — line 19 diff:
  ```python
  - REQUIRED_KEYS: tuple[str, ...] = ("SERPER_API_KEY", "TAVILY_API_KEY")
  + REQUIRED_KEYS: tuple[str, ...] = ("SERPER_API_KEY",)
  ```
- `.claude/skills/google-ad-research/scripts/pyproject.toml` — `project.dependencies` array diff:
  ```toml
        "httpx>=0.28",
        "httpx-retries>=0.5",
  -     "tavily-python>=0.7.24",
        "python-dotenv>=1.0",
  ```
- `.claude/skills/google-ad-research/scripts/uv.lock` — regenerated; removed tavily-python v0.7.24 + 5 transitive deps (charset-normalizer v3.4.7, regex v2026.4.4, requests v2.33.1, tiktoken v0.12.0, urllib3 v2.7.0).
- `.claude/skills/google-ad-research/scripts/tests/conftest.py` — removed the `@pytest.fixture` decorator + `def tavily_fixture()` function + 2-line body that loaded `tavily_extract_2urls.json`.

**Created (1):**
- `.planning/phases/12-source-consolidation-drop-tavily/12-01-SUMMARY.md`

## Decisions Made

1. **uv.lock regenerated in-task, not deferred.** Plan explicitly permitted deferral if `uv lock` failed due to lingering `import tavily` statements in competitor_intel.py / pulse_fetch.py (refactored by parallel plans 12-02 / 12-03). In practice `uv lock` is a metadata-only operation — it resolves the declared dependency tree, not the import graph — so it succeeded immediately. Five transitive deps auto-pruned. Operator-acceptable per plan; cleaner outcome than the deferral path.

2. **Conftest.py edit preserved trailing fixture(s) + import block intact.** The plan called for removing `tavily_fixture` ONLY. Verified surrounding code (`json` import + `FIXTURES_DIR` constant + `serper_fixture` + `sample_brief_text` + `mock_env`) all still in use by other tests. No collateral deletion.

3. **.env.example located at repo root** (not at `.claude/skills/google-ad-research/.env.example`). Confirmed via `Glob` — only the root file exists. Single edit covered TVLY-02 audit half (audit test reads root path first, falls back to skill path).

## Deviations from Plan

None functional. Plan executed as written.

## Issues Encountered

**Parallel-wave commit absorption (Task 2).** While Task 2 was being staged (4 files: `.env.example`, `lib/config.py`, `pyproject.toml`, `uv.lock`), the parallel Plan 12-03 agent committed `f153729` ("feat(12-03): strip Tavily news call from pulse_fetch.py (PULSE-10)"). Their commit included those same 4 shared-config files plus `pulse_fetch.py`. Net effect: my staged changes were absorbed into their commit because both plans needed identical deletions on the shared config files (Plan 12-03's pulse_fetch.py also calls `load_env(require=("SERPER_API_KEY",))` and ships its own PEP 723 block without tavily-python).

**Root cause:** Parallel-wave note declared `12-01 owns: tavily_extract.py, test_tavily_extract.py, conftest.py, pyproject.toml, lib/config.py, .env.example` and `12-03 owns: pulse_fetch.py, pulse_synth.py`. But Plan 12-03's pulse_fetch.py work transitively required Plan 12-01's config-side deletions (otherwise `load_env(require=("SERPER_API_KEY", "TAVILY_API_KEY"))` would still demand the deleted key). Two valid parallel plans drove the same 4 file edits — race condition is structural, not procedural.

**Impact:** Zero data loss. Disk state matches plan spec exactly. Only commit attribution differs:
- Task 1 (`93c785f`): solely this plan's work — clean attribution.
- Task 2 (would have been my second commit): absorbed by parallel `f153729`. The diff in that commit precisely matches what this plan would have committed.

**Mitigation for future parallel waves:** Either (a) sequence config edits before parallel wave begins, or (b) document shared-config files explicitly in the parallel-wave note so first-mover wins is documented. Not blocking — plan 12-01 contract satisfied.

## Audit Test Status (full TVLY subset)

```
test_tavily_extract_deleted              GREEN  (TVLY-01)
test_tavily_env_keys_stripped            GREEN  (TVLY-02)
test_tavily_deps_and_fixtures_stripped   GREEN  (TVLY-03)
test_tavily_test_artifacts_stripped      GREEN  (TVLY-04)
4 passed, 4 deselected in 0.02s
```

Other Wave 0 audit tests (verified still RED — expected, owned by plans 02/03/04):
- `test_competitor_intel_no_tavily_import` — Plan 12-02 closes
- `test_skill_md_uses_webfetch_for_step19` — Plan 12-04 closes (Wave 2)
- `test_phase7_docs_tavily_free` — Plan 12-04 closes
- `test_repo_grep_tavily_clean` — Plan 12-02/03/04 all required for this

## User Setup Required

None. Existing operator `.env` files keep the now-orphaned `TAVILY_API_KEY` value harmlessly — it just stops being read. `.env.example` no longer instructs operators to set it.

## Next Phase Readiness

Plan 12-01 contract met. Per parallel-wave structure:
- Plan 12-02 (competitor_intel.py + merge_signals.py refactor) — in progress as I write this; will close WFCH-03 + WFCH-04 audit tests.
- Plan 12-03 (pulse_fetch.py + pulse_synth.py refactor) — already committed `f153729`; PULSE-10/11 + PULSE-12 audit tests should be flipping.
- Plan 12-04 (render_report._load_competitor_landing_pages + docs cleanup) — Wave 2; lifts the SKIP on `test_competitor_section_joins_webfetch_results`.
- Plan 12-05 (full-suite GREEN + e2e smoke) — Wave 3 milestone close.

No blockers introduced. No follow-ups.

## Self-Check

- FOUND: 93c785f (Task 1 commit)
- FOUND: f153729 (Task 2 absorbed commit — parallel attribution)
- MISSING: .claude/skills/google-ad-research/scripts/tavily_extract.py (DELETED — correct per plan)
- MISSING: .claude/skills/google-ad-research/scripts/tests/test_tavily_extract.py (DELETED — correct per plan)
- MISSING: .claude/skills/google-ad-research/scripts/tests/fixtures/tavily_extract_2urls.json (DELETED — correct)
- MISSING: .claude/skills/google-ad-research/scripts/tests/fixtures/tavily_lp_response.json (DELETED — correct)
- MISSING: .claude/skills/google-ad-research/scripts/tests/fixtures/tavily_news.json (DELETED — correct)
- VERIFIED: .env.example contains no `TAVILY_API_KEY`
- VERIFIED: lib/config.py REQUIRED_KEYS == ("SERPER_API_KEY",)
- VERIFIED: pyproject.toml has no `tavily-python` entry
- VERIFIED: conftest.py has no `def tavily_fixture` regex match
- VERIFIED: 4 TVLY-* audit tests PASS (0.02s)

## Self-Check: PASSED

---
*Phase: 12-source-consolidation-drop-tavily*
*Plan: 01*
*Completed: 2026-05-15*
