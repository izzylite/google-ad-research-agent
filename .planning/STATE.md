# State: Google Ad Research Agent

**Last updated:** 2026-05-08

## Project Reference

**Core value:** From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session.

**Current focus:** Phase 1 — Skill Scaffold and Brief Intake (Plan 01-00 complete; next: Plan 01-01).

## Current Position

| Field | Value |
|-------|-------|
| Phase | 1 — Skill Scaffold and Brief Intake |
| Plan | 01-01 (Plan A: lib/io.py + lib/config.py) |
| Status | Plan 01-00 complete — Wave 0 test scaffolding done |
| Progress | `[░░░░░░░░░░] 0/6 phases complete` |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 1 / 6 |
| Phases complete | 0 / 6 |
| Plans complete | 1 |
| v1 requirements complete | 0 / 35 |

### Execution History

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 00 | ~3 min | 3/3 | 5 created |

## Accumulated Context

### Decisions

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

### Open Questions / Todos

- Composite ranking weight tuning (source_diversity vs signal_count vs intent) — v1 hypothesis; calibrate after first 3-5 real runs.
- Tavily credit consumption per run — estimated $0.09-$0.30; measure from run 1, adjust caps if needed.
- Cluster count vs vertical — narrow verticals may yield fewer than the 5-10 general recommendation; do not force the range.
- Match-type recommendation conservatism — validate after first campaign launch.

### Blockers

None.

## Session Continuity

**Last session:** 2026-05-08 — Completed Plan 01-00 (Wave 0 pytest scaffolding). 5 test files created: __init__.py, conftest.py, test_lib_io.py, test_config.py, test_run_init.py. 18 tests collect in 0.02s, all RED (ModuleNotFoundError until Plan A lands).

**Stopped at:** Completed 01-00-PLAN.md

**Next session:** Execute Plan 01-01 (Plan A — lib/io.py + lib/config.py implementation).

**Files of record:**
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\PROJECT.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\REQUIREMENTS.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\ROADMAP.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\SUMMARY.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\ARCHITECTURE.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\PITFALLS.md`

---
*State initialized: 2026-05-08*
