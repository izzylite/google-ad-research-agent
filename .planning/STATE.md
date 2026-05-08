---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
stopped_at: Completed 02-01-PLAN.md
last_updated: "2026-05-08T04:27:45.232Z"
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 12
  completed_plans: 8
---

# State: Google Ad Research Agent

**Last updated:** 2026-05-08

## Project Reference

**Core value:** From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session.

**Current focus:** Phase 1 complete (signed-off-by-inspection). Next: Phase 2 — Signal Collection (Plans 02-xx).

## Current Position

| Field | Value |
|-------|-------|
| Phase | 1 — Skill Scaffold and Brief Intake |
| Plan | 01-05 COMPLETE (Validation / Sign-off) |
| Status | Phase 1 signed-off-by-inspection — all 18 tests green, SKILL.md prompt logic verified; fresh CC session smoke TODO before production |
| Progress | `[██░░░░░░░░] 1/6 phases complete` |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 6 / 6 |
| Phases complete | 1 / 6 |
| Plans complete | 6 |
| v1 requirements complete | 9 / 35 |
| Phase 02 P00 | 7min | 2 tasks | 9 files |
| Phase 02-signal-collection P01 | 12min | 2 tasks | 4 files |

### Execution History

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 00 | ~3 min | 3/3 | 5 created |
| 01 | 01 | ~6 min | 2/2 | 4 created |
| 01 | 02 | ~5 min | 2/2 | 1 created |
| 01 | 03 | ~8 min | 2/2 | 1 created |
| 01 | 04 | ~4 min | 1/1 | 1 created |
| 01 | 05 | ~8 min | 2/2 | 1 modified |

## Accumulated Context

### Decisions

- find_dotenv(usecwd=True) not usecwd=False in lib/config.py — usecwd=False searches from calling stack frame (inside project tree during tests), defeating monkeypatch.chdir() isolation; usecwd=True correctly respects test CWD and production CWD.
- lib/http.py intentionally absent from Phase 1 — no HTTP calls in Phase 1; writing untested stub now risks API mismatch when Serper/Tavily are designed in Phase 2.
- Claude Code skill (not standalone app) — operator already lives in Claude Code; second runtime adds no value.
- Three signal sources, three roles: WebSearch (free baseline), Serper.dev (structured SERP — PAA / related / ads), Tavily (deep competitor LP content).
- No volume / CPC API in v1 — rank on `source_diversity` (primary) + `signal_count` (tiebreak) + LLM intent weight; explicit "not search volume" labelling.
- Categorical 4-class intent rubric (informational / commercial / transactional / navigational), `temperature=0`, anchor examples in every prompt — drift prevention.
- LLM-driven clustering in v1 — `sentence-transformers` rejected (~700MB torch deps make skill non-portable); `scikit-learn` TF-IDF/k-means kept as v2 fallback only.
- Conversational brief intake (not structured form) — skill loops on 5 mandatory fields (industry, product, location, language, audience).
- `tavily_extract` not `tavily_crawl`, hard cap 5 competitors × 5 URLs, `extract_depth='basic'` — Tavily cost-blowup mitigation.
- `report.json` ships in v1 alongside `report.md` — stable canonical schema enables future run-diff without breaking changes.
- Generic engine v1 (no vertical presets) — defer to v2 once real usage reveals which verticals matter.
- Run-folder isolation, no caching, no cross-run mutable state — reproducibility over efficiency in v1.
- CLAUDE.md capped at 56 lines — directive not exhaustive; each section is a pointer so future executors stay on-rails without re-debating conventions.
- run_init.py derives slug and timestamp from run_dir.name (not re-calling iso_timestamp()) — guarantees stdout reflects actual on-disk folder name including any collision suffix.
- SKILL.md must quote run_init.py path: `uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py"` — handles spaces in operator paths.
- SKILL.md Phase 1 ends with hard STOP at Step 5 — Phase 2 signal collection will replace Step 5 in future skill update; no Phase 2 stubs added in Phase 1.
- SKILL.md operator trigger phrases front-loaded in description field ('keyword research', 'Google Ads research', 'PPC keywords', 'ad group clusters') — ensures Claude Code auto-discovers skill on brief paste.
- Brief rendered to OS temp file via Write tool before piping to run_init.py — avoids multiline shell quoting issues in Bash tool.
- [Phase 01]: signed-off-by-inspection chosen over signed-off — automated rows green; manual rows verified by SKILL.md prompt inspection only; fresh CC session smoke is still required before production use
- [Phase 02]: Module-missing guard (try/except ImportError + pytestmark skipif) chosen over xfail — keeps collection clean and makes RED-to-GREEN transition explicit when each Phase 2 module is implemented
- [Phase 02]: Fixture JSONs use realistic shapes with correct keys (organic/PAA/relatedSearches/ads; results/failed_results) not empty dicts — future test assertions need real key presence
- [Phase 02]: tmp_run_dir fixture pre-creates raw/ subdirectory to match production Phase 1 run-folder layout — tests can write to raw/ without extra setup
- [Phase 02-signal-collection]: RetryTransport status_forcelist excludes 401 — auth failures are fatal, not transient; confirmed by test_no_retry_on_401
- [Phase 02-signal-collection]: Module-level inflect engine (_INF = inflect.engine()) at import scope, not per call — avoids re-instantiation overhead
- [Phase 02-signal-collection]: canonical_form is lowercased + punctuation-stripped input surface (not sorted lemma form) — merge_signals.py picks shortest surface per hash group as display name

### Open Questions / Todos

- Composite ranking weight tuning (source_diversity vs signal_count vs intent) — v1 hypothesis; calibrate after first 3-5 real runs.
- Tavily credit consumption per run — estimated $0.09-$0.30; measure from run 1, adjust caps if needed.
- Cluster count vs vertical — narrow verticals may yield fewer than the 5-10 general recommendation; do not force the range.
- Match-type recommendation conservatism — validate after first campaign launch.

### Blockers

None.

## Session Continuity

**Last session:** 2026-05-08T04:27:45.230Z

**Stopped at:** Completed 02-01-PLAN.md

**Next session:** Plan Phase 2 — Signal Collection (Serper.dev + Tavily + WebSearch). First task: implement `lib/http.py` per RESEARCH.md Open Questions.

**Files of record:**
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\PROJECT.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\REQUIREMENTS.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\ROADMAP.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\SUMMARY.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\ARCHITECTURE.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\PITFALLS.md`

---
*State initialized: 2026-05-08*
