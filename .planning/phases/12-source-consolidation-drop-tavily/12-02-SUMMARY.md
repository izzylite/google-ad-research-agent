---
phase: 12-source-consolidation-drop-tavily
plan: 02
subsystem: refactor

tags: [tavily-removal, serper-only, webfetch-handoff, competitor-intel, merge-signals, source-taxonomy, wfch-03, wfch-04]

# Dependency graph
requires:
  - phase: 12-source-consolidation-drop-tavily
    provides: Wave 0 RED tests locking the Serper-only advertisers shape (WFCH-03) + 5-source VALID_SOURCES taxonomy (WFCH-04); Plan 12-01 dropped tavily-python dep + lib/config REQUIRED_KEYS + .env.example TAVILY_API_KEY
provides:
  - competitor_intel.py with Serper-only advertisers list comprehension; Serper requery for ads block + Serper-organic fallback preserved; zero Tavily references
  - merge_signals.py with 5-source VALID_SOURCES frozenset (serper-organic, serper-paa, serper-related, serper-ads, websearch-baseline); read_tavily reader function deleted; tavily-*.json glob loop deleted; _extract_first_phrase + _PUNCT_STRIP helpers deleted (orphans after read_tavily removal)
  - WFCH-03 flipped GREEN: test_advertisers_shape_post_phase12 + test_competitor_intel_no_tavily_import
  - WFCH-04 flipped GREEN: test_valid_sources_post_phase12 + test_read_tavily_removed
  - Updated Phase 5 tests (test_competitor_intel.py): test_advertisers_serper_only_shape replaces test_tavily_failed_result_persisted; test_advertiser_urls_built_from_top_ads renamed; TavilyClient monkeypatches removed from test_ads_fetched_per_cluster + test_empty_ads_block_ok + test_output_schema_valid
  - Updated Phase 2 tests (test_merge_signals.py): test_five_source_taxonomy replaces test_six_source_taxonomy; _write_tavily helper removed; tavily-extract assertions stripped from 3 other tests
affects:
  - Phase 12 Plan 03 (pulse_fetch / pulse_synth Tavily removal — separate file ownership, runs in parallel)
  - Phase 12 Plan 04 (render_report._load_competitor_landing_pages helper for WFCH-02 JOIN test; SKILL.md + references rewrites for WFCH-01 + PULSE-12)
  - Phase 12 Plan 05 (full-suite GREEN gate — will close out the remaining test_repo_grep_tavily_clean offenders after Plans 12-03 + 12-04 land)
  - Phase 5 Step 19 SKILL.md workflow — Claude WebFetch now owns LP extraction; competitor_intel.py emits advertisers list with URLs for WebFetch to consume

# Tech tracking
tech-stack:
  added: []  # Pure deletion + refactor; no new deps
  patterns:
    - "Wave-1 deletion of a third-party API integration: surgical removal preserves every non-deleted code path (Serper requery + Serper-organic fallback + affiliate filter + dedupe + advertiser cap all intact)"
    - "Test updates co-located with production refactor: Phase 11-shape assertions (raw_content / tavily_fetched_at / extract_status / tavily-extract source) replaced with Wave-0 audit shape in the SAME commit as the production refactor — preserves atomic per-task review"
    - "Orphan helper detection via grep before deletion: _extract_first_phrase + _PUNCT_STRIP only used by read_tavily; verified zero other callers before removing"
    - "Comment scrubbing for substring purity: 'tavily' references in docstrings/comments removed to satisfy strict must-have ('competitor_intel.py 'tavily' substring count == 0'); narrative preserved via 'landing-page extraction is Phase 5 only' framing"

key-files:
  created:
    - .planning/phases/12-source-consolidation-drop-tavily/12-02-SUMMARY.md
  modified:
    - .claude/skills/google-ad-research/scripts/competitor_intel.py
    - .claude/skills/google-ad-research/scripts/merge_signals.py
    - .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py
    - .claude/skills/google-ad-research/scripts/tests/test_merge_signals.py

key-decisions:
  - "Surgical deletion preserves Serper requery + Serper-organic fallback (RESEARCH.md lines 254-275 + 287-302 intact) — only the post-fallback advertisers building logic changes from Tavily extract loop to a 5-key Serper list comprehension"
  - "Comment scrubbing for substring purity: any 'tavily' reference in docstrings/comments removed to satisfy strict must-have; narrative preserved via 'landing-page extraction is Phase 5 only' framing instead of 'tavily-replaced-with-WebFetch' framing"
  - "_extract_first_phrase + _PUNCT_STRIP deleted alongside read_tavily — both helpers had a single consumer (verified via grep) so they become orphans after read_tavily removal; keeping them would inflate the source-text 'tavily' count via the docstring reference"
  - "Phase 5 test updates land in the SAME commit as the production refactor — test_tavily_failed_result_persisted (asserted on raw_content + extract_status fields no longer in output) replaced with test_advertisers_serper_only_shape asserting exact {domain,url,title,description,position} key set; Wave-0 contract is the source of truth"
  - "uv.lock regeneration deferred to Plan 12-01 (verified clean: grep -c tavily uv.lock == 0); avoids parallel-wave lock-file race"
  - "merge_signals docstring narrative kept 5-source-only (no 'Phase 12: tavily-extract removed' archaeological note) so future contributors don't see 'tavily' substring in production code; deletion archaeology lives in this SUMMARY.md instead"

patterns-established:
  - "Wave-1 refactor with file ownership: 12-02 touches ONLY competitor_intel.py + merge_signals.py + their tests; pulse_fetch.py / pulse_synth.py / render_report.py / SKILL.md / references stay untouched (owned by Plans 12-03 + 12-04)"
  - "Pre-existing RED tests outside the plan's file ownership are documented as out-of-scope (test_audit_tavily_removed.py legacy reds + test_config.py::test_required_keys_defined) — Plan 12-05 final-gate plan closes them out"
  - "Test refactor preserves test names where possible (test_output_schema_valid) and renames otherwise (test_tavily_urls_built_from_top_ads → test_advertiser_urls_built_from_top_ads) — Phase 5 GREEN test invariants preserved; only Tavily-specific shape assertions rewritten"

requirements-completed: [WFCH-03, WFCH-04]

# Metrics
duration: ~25min
completed: 2026-05-15
---

# Phase 12 Plan 02: Strip Tavily from competitor_intel.py + merge_signals.py (WFCH-03 + WFCH-04)

**Tavily branch surgically removed from competitor_intel.py (advertisers now derived from post-dedupe Serper top_ads only) and from merge_signals.py (5-source VALID_SOURCES taxonomy; read_tavily + tavily-*.json glob loop deleted). WFCH-03 + WFCH-04 Wave-0 RED tests flip GREEN; Phase 5/6/11 GREEN suite preserved via co-located test refactor.**

## Performance

- **Duration:** ~25min
- **Started:** 2026-05-15 (continuation of Wave 1)
- **Completed:** 2026-05-15
- **Tasks:** 2 (no checkpoints)
- **Files modified:** 4 (2 production + 2 tests)

## Accomplishments

- **WFCH-03 GREEN:** competitor_intel.py contains zero 'tavily' substrings (grep -c -i tavily == 0). advertisers list comprehension produces dicts with exactly `{domain, url, title, description, position}` keys. TavilyClient import + instantiation + extract block + failed_results loop + tavily_credits accounting all deleted. Exit-code docstring scrubbed (exit 2 = retryable Serper HTTP, exit 3 = fatal auth/config; Tavily-specific quota/auth language gone).
- **WFCH-04 GREEN:** merge_signals.VALID_SOURCES is the exact 5-element frozenset (serper-organic, serper-paa, serper-related, serper-ads, websearch-baseline). hasattr(merge_signals, 'read_tavily') is False. _extract_first_phrase + _PUNCT_STRIP regex helpers deleted (orphans after read_tavily removal). tavily-*.json glob loop in merge_raw_files() deleted.
- **Serper requery + Serper-organic fallback preserved:** RESEARCH.md lines 254-275 (Serper ad-block fetch via fetch_seed) and 287-302 (organic fallback when ads block empty) untouched in competitor_intel.py. The refactor is targeted: only the post-fallback advertisers building logic changes.
- **Phase 5 GREEN suite preserved:** All 11 pre-existing test_competitor_intel.py tests + 1 Wave-0 WFCH-03 test = 12 PASSED. TavilyClient monkeypatches removed from 3 tests (test_ads_fetched_per_cluster, test_empty_ads_block_ok, test_output_schema_valid). test_tavily_failed_result_persisted replaced with test_advertisers_serper_only_shape (asserts exact key set + absence of Phase-11 Tavily fields). test_tavily_urls_built_from_top_ads renamed test_advertiser_urls_built_from_top_ads (URL-list assertion unchanged; renamed because Phase 5 WebFetch now consumes the URLs, not Tavily SDK).
- **Phase 2 GREEN suite preserved:** All 11 pre-existing test_merge_signals.py tests + 2 Wave-0 WFCH-04 tests = 11 PASSED. _write_tavily helper deleted (orphan after read_tavily deletion). test_six_source_taxonomy renamed test_five_source_taxonomy (5-element expected set + source_diversity == 5).
- **Full suite delta:** Pre-Plan: 14 failed + 239 passed + 1 skipped. Post-Plan: 4 failed + 245 passed + 1 skipped. Net: -10 failures (WFCH-03/04 audit + 4 unit tests flipped to GREEN; +6 new GREEN from co-located test refactor that no longer asserts Tavily shapes).

## Task Commits

Each task committed atomically:

1. **Task 1: Refactor competitor_intel.py — strip Tavily branch, preserve Serper requery + fallback** — `a20b597` (refactor)
2. **Task 2: Refactor merge_signals.py — drop tavily-extract source + read_tavily + glob loop** — `0a572fc` (refactor)

**Plan metadata commit:** TBD (final docs commit after STATE.md + ROADMAP.md + REQUIREMENTS.md updates)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/competitor_intel.py` — Serper-only competitor intel; PEP 723 deps drop tavily-python; load_env(require=("SERPER_API_KEY",)); advertisers list comprehension with 5 Serper fields; exit-code docstring scrubbed
- `.claude/skills/google-ad-research/scripts/merge_signals.py` — 5-source VALID_SOURCES frozenset; read_tavily + _extract_first_phrase + _PUNCT_STRIP + tavily-*.json glob loop all deleted; docstring + merge_raw_files args docstring updated
- `.claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py` — TavilyClient monkeypatches removed from 3 tests; MagicMock import dropped; test_tavily_failed_result_persisted replaced with test_advertisers_serper_only_shape; test_tavily_urls_built_from_top_ads renamed
- `.claude/skills/google-ad-research/scripts/tests/test_merge_signals.py` — _write_tavily helper removed; test_six_source_taxonomy renamed test_five_source_taxonomy with 5-source set + source_diversity == 5; tavily fixture blocks dropped from 3 other tests

## Exact Line Ranges Deleted

**competitor_intel.py (pre-refactor 404 lines → post-refactor 333 lines, -71 net):**
- Header `dependencies = [...]` block: removed `"tavily-python>=0.7.24"` line (pre-refactor line 6)
- Module docstring exit codes: rewrote `2  retryable (Tavily quota exceeded)` to `2  retryable (Serper HTTP error)` (line 24); rewrote `3  fatal (missing input file, bad API key, missing env var)` framing
- Imports block: deleted `from tavily import TavilyClient` (line 46) + `from tavily import (InvalidAPIKeyError, MissingAPIKeyError, UsageLimitExceededError)` (lines 47-51)
- main_with_args body: changed `load_env(require=("SERPER_API_KEY", "TAVILY_API_KEY"))` → `load_env(require=("SERPER_API_KEY",))` (line 192)
- main_with_args body: deleted `tavily_key = os.environ["TAVILY_API_KEY"]` (line 198) + `tavily_client = TavilyClient(api_key=tavily_key)` (line 232)
- output metadata: dropped `"tavily_credits_used": 0` from initial dict (line 222) and metadata update (line 387)
- counter: dropped `tavily_credits = 0` (line 228) and `tavily_credits += usage.get(...)` (line 343)
- main loop: deleted entire Tavily extract block (lines 317-360 inclusive) including:
  - `lp_urls = [...]` URL collection (line 318)
  - `if lp_urls:` outer guard (line 321)
  - `tavily_response = tavily_client.extract(...)` call (lines 322-328)
  - except branches for InvalidAPIKeyError / MissingAPIKeyError / UsageLimitExceededError / generic Exception (lines 329-339)
  - `tavily_fetched_at` timestamp (line 341)
  - `usage` extraction + credits accounting (lines 342-343)
  - results loop (lines 345-352) and failed_results loop (lines 354-360)
- main loop: replaced deleted Tavily block with 11-line Serper-only `advertisers = [...]` list comprehension over post-dedupe `top_ads`
- serper_client.close() calls inside Tavily except branches: deleted (lines 331, 335)
- stdout JSON: dropped `"tavily_credits_used": tavily_credits` (line 397)

**merge_signals.py (pre-refactor 670 lines → post-refactor 597 lines, -73 net):**
- Module docstring: rewrote 6-source taxonomy block (lines 19-25) to 5-source + WFCH-04 NOTE about webfetch-landing exclusion
- `_PUNCT_STRIP = re.compile(...)` (line 124): deleted (orphan after read_tavily removal)
- VALID_SOURCES (lines 111-118): pruned `"tavily-extract"` element; replaced with 5-element frozenset + 3-line comment documenting WFCH-04 contract
- `_extract_first_phrase(...)` function (lines 316-333 in pre-refactor, ~18 lines): deleted (orphan after read_tavily removal)
- `read_tavily(...)` function (lines 336-360 in pre-refactor, ~25 lines): deleted entirely per WFCH-04
- `merge_raw_files` docstring (lines 441-443): updated args to drop `tavily-*.json` mention; rephrased to "(Landing-page content is a Phase 5 WebFetch sidecar — never feeds the keyword pool.)"
- `merge_raw_files` body: deleted entire `# --- tavily-*.json ---` section + glob loop (lines 510-513): `for tavily_path in sorted(raw_dir.glob("tavily-*.json")): for text, attr in read_tavily(tavily_path): _add(text, attr)`

## Pre-existing Tests That Needed Updates (Tavily-shape assertions)

Per plan's Step 8 contract: "If any existing test referenced `tavily-extract` as an expected source, update or delete (those tests were locked to the Phase 2-11 shape)."

### test_competitor_intel.py (4 tests touched)

1. **test_ads_fetched_per_cluster** — Removed the TavilyClient monkeypatch block (8 lines). Assertion unchanged.
2. **test_empty_ads_block_ok** — Removed TavilyClient monkeypatch + replaced `serper_ads_empty.json` fixture load with an inline empty-organic+empty-ads dict so the Serper-organic fallback also yields no advertisers. Assertion unchanged (still `advertisers == []`).
3. **test_tavily_failed_result_persisted** → **test_advertisers_serper_only_shape** — Renamed and rewritten. Pre-Plan asserted `extract_status == "failed"` + `raw_content == ""` (Tavily-specific fields). Post-Plan asserts each advertiser dict has exactly the 5-key Serper set `{domain, url, title, description, position}` and that the Phase-11 Tavily fields are absent.
4. **test_output_schema_valid** — Removed TavilyClient monkeypatch. Assertion unchanged (top-level + per-cluster keys still validated).
5. **test_tavily_urls_built_from_top_ads** → **test_advertiser_urls_built_from_top_ads** — Renamed. URL-list assertion unchanged (still asserts URLs from link field + no affiliate URLs). Renamed because Phase 5 WebFetch now consumes the URLs, not Tavily SDK.

### test_merge_signals.py (5 tests touched)

1. **_write_tavily helper function** — Deleted (orphan after read_tavily removal).
2. **test_sources_array_per_keyword** — Swapped the `_write_tavily(...)` call for `_write_websearch([...])`. Assertion unchanged.
3. **test_six_source_taxonomy** → **test_five_source_taxonomy** — Renamed and rewritten. Pre-Plan asserted 6 source types including `tavily-extract` + `source_diversity == 6`. Post-Plan asserts the 5-source post-Phase-12 set + `source_diversity == 5`.
4. **test_source_diversity_count** — Swapped the `_write_tavily(...)` call for `_write_websearch([kw])`. Assertion text updated to say `serper-organic + websearch-baseline` instead of `serper-organic + tavily-extract`. `source_diversity == 2` invariant unchanged.
5. **test_end_to_end_with_fixtures** — Deleted the tavily fixture adaptation block (lines 306-319 pre-refactor). Other fixture loads + assertions unchanged.

## Decisions Made

See `key-decisions` in frontmatter. Highlights:

- **Comment-text purity:** Removed "Phase 12: tavily-extract removed" archaeological comments from production .py files. They would have left "tavily" substrings in the source and failed both the strict must-have (`'tavily' substring count == 0`) and the all-surfaces audit. Deletion archaeology lives in this SUMMARY.md instead.
- **Co-located test refactor:** Test updates landed in the SAME commit as the production refactor (Task 1 commit = competitor_intel.py + test_competitor_intel.py; Task 2 commit = merge_signals.py + test_merge_signals.py). Atomic per-task review: each commit is reviewable as one self-consistent change.
- **uv.lock deferred:** Plan 12-01 already regenerated uv.lock (`grep -c tavily uv.lock == 0` confirmed before commit). Skipped Step 8 to avoid parallel-wave race condition.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing tests in test_competitor_intel.py referenced removed TavilyClient + Tavily-shape advertisers fields**

- **Found during:** Task 1 verification (test_competitor_intel.py full run)
- **Issue:** 3 Phase 5 GREEN tests (test_ads_fetched_per_cluster, test_empty_ads_block_ok, test_output_schema_valid) monkeypatched `competitor_intel.TavilyClient` which no longer exists; 1 test (test_tavily_failed_result_persisted) asserted on `raw_content` + `extract_status` fields that are gone; 1 test (test_tavily_urls_built_from_top_ads) had Tavily-flavoured name but the assertion was actually still valid.
- **Fix:** Removed TavilyClient monkeypatches (test still mocks fetch_seed for Serper). Rewrote test_tavily_failed_result_persisted as test_advertisers_serper_only_shape asserting the exact Serper-only key set. Renamed test_tavily_urls_built_from_top_ads → test_advertiser_urls_built_from_top_ads. Removed unused MagicMock import.
- **Files modified:** .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py
- **Verification:** pytest test_competitor_intel.py → 11 PASSED (all pre-existing Phase 5 invariants preserved); test_advertisers_shape_post_phase12 (Wave 0 RED) flipped to GREEN.
- **Committed in:** a20b597 (Task 1 commit — co-located with production refactor)

**2. [Rule 1 - Bug] Pre-existing tests in test_merge_signals.py wrote tavily fixtures + asserted tavily-extract source**

- **Found during:** Task 2 design (predicted RED before running)
- **Issue:** _write_tavily helper would still write tavily-*.json into raw/, but merge_signals no longer reads them (glob loop deleted). Tests asserting tavily-extract source in keyword rows would fail because no tavily reader fires. test_six_source_taxonomy hard-coded `expected_taxonomy = {... "tavily-extract" ...}` + `source_diversity == 6`.
- **Fix:** Deleted _write_tavily helper (orphan). Renamed test_six_source_taxonomy → test_five_source_taxonomy and rewrote expectations to the 5-source set + source_diversity == 5. Swapped _write_tavily calls in 2 other tests for _write_websearch. Deleted tavily fixture adaptation block in test_end_to_end_with_fixtures.
- **Files modified:** .claude/skills/google-ad-research/scripts/tests/test_merge_signals.py
- **Verification:** pytest test_merge_signals.py → 11 PASSED; test_valid_sources_post_phase12 + test_read_tavily_removed (both Wave 0 RED) flipped GREEN.
- **Committed in:** 0a572fc (Task 2 commit — co-located with production refactor)

**3. [Rule 1 - Bug] Production-code comments contained 'tavily' substrings, violating must-have**

- **Found during:** Task 2 verification after initial pass
- **Issue:** First-pass merge_signals.py docstring/comments retained "Phase 12: tavily-extract removed" archaeological wording. Strict must-have ("`'tavily' substring count == 0`") would fail; all-surfaces audit would continue flagging the file as offender.
- **Fix:** Rewrote 3 docstring/comment lines to omit "tavily" entirely while preserving narrative ("5 sources"; "Landing-page content is a Phase 5 WebFetch sidecar"). Deletion archaeology preserved in this SUMMARY.md.
- **Files modified:** .claude/skills/google-ad-research/scripts/merge_signals.py
- **Verification:** `grep -c -i tavily merge_signals.py` → 0; `grep -c -i tavily competitor_intel.py` → 0.
- **Committed in:** 0a572fc (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs / breaking changes from the production refactor). Zero scope drift.
**Impact on plan:** Necessary corollaries of the production refactor. All within the plan's `files_modified` list (the test files are extensions of the production files per Wave 0 contract). No architectural changes.

## Issues Encountered

- **Pre-existing reds outside plan scope remain.** Post-Plan full-suite result: `4 failed, 245 passed, 1 skipped`. Remaining failures (all outside Plan 12-02 file ownership):
  - `test_audit_tavily_removed::test_skill_md_uses_webfetch_for_step19` — Plan 12-04 territory (SKILL.md + references rewrite)
  - `test_audit_tavily_removed::test_phase7_docs_tavily_free` — Plan 12-04 territory
  - `test_audit_tavily_removed::test_repo_grep_tavily_clean` — remaining offenders are `render_report.py` + `lib/http.py` + 2 references files + `SKILL.md` (Plans 12-03 + 12-04 territory)
  - `test_config::test_required_keys_defined` — pre-existing test asserts `"TAVILY_API_KEY" in REQUIRED_KEYS`; Plan 12-01 updated lib/config.py to drop TAVILY_API_KEY from REQUIRED_KEYS but did not update test_config.py. Plan 12-01 territory or a Plan 12-05 final-gate cleanup.
- **No new reds introduced by Plan 12-02.** All 4 remaining failures predate Plan 12-02 OR were predicted out-of-scope per file ownership.

## User Setup Required

None — pure code refactor. No new env vars, no API keys, no dashboard config.

## Next Phase Readiness

**Plan 12-02 deliverable:** competitor_intel.py + merge_signals.py are Tavily-free, the Serper requery + fallback flow is intact, Phase 2 + Phase 5 GREEN test invariants are preserved, and WFCH-03 + WFCH-04 are GREEN.

**Wave 1 status (after parallel plans):**
- Plan 12-01 (delete tavily_extract.py + .env keys + deps + fixtures): already committed (commits visible in `git log` ahead of this plan). lib/config.py REQUIRED_KEYS = `('SERPER_API_KEY',)`. uv.lock clean.
- Plan 12-02 (this plan): COMPLETE.
- Plan 12-03 (pulse_fetch / pulse_synth Tavily removal): already committed (`f153729 feat(12-03): strip Tavily news call from pulse_fetch.py (PULSE-10)` in git log).

**Wave 2 ready:** Plan 12-04 (SKILL.md + references + render_report._load_competitor_landing_pages helper for WFCH-02 JOIN test). The advertisers list emitted by competitor_intel.py now matches the WFCH-02 contract that 12-04's helper will join against.

**No blockers.** No open questions.

## Self-Check: PASSED

All files exist on disk:
- FOUND: .claude/skills/google-ad-research/scripts/competitor_intel.py
- FOUND: .claude/skills/google-ad-research/scripts/merge_signals.py
- FOUND: .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py
- FOUND: .claude/skills/google-ad-research/scripts/tests/test_merge_signals.py
- FOUND: .planning/phases/12-source-consolidation-drop-tavily/12-02-SUMMARY.md

All task commits exist:
- FOUND: a20b597 (Task 1 — competitor_intel.py refactor)
- FOUND: 0a572fc (Task 2 — merge_signals.py refactor)

Verification commands:
- `grep -c -i tavily competitor_intel.py` → 0
- `grep -c -i tavily merge_signals.py` → 0
- WFCH-03 + WFCH-04 4-test subset → 4 PASSED
- Full test_competitor_intel.py → 12 PASSED
- Full test_merge_signals.py → 11 PASSED
- Full suite → 4 failed (out-of-scope, Plans 12-01/03/04/05 territory), 245 passed, 1 skipped

---
*Phase: 12-source-consolidation-drop-tavily*
*Completed: 2026-05-15*
