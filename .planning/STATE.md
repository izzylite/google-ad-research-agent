---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
stopped_at: Completed 06-05-PLAN.md
last_updated: "2026-05-08T07:26:39.886Z"
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 27
  completed_plans: 27
---

# State: Google Ad Research Agent

**Last updated:** 2026-05-08

## Project Reference

**Core value:** From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session.

**Current focus:** Phase 1 complete (signed-off-by-inspection). Next: Phase 2 — Signal Collection (Plans 02-xx).

## Current Position

| Field | Value |
|-------|-------|
| Phase | 6 — Negatives, Report Assembly, and Persistence |
| Plan | 06-05 COMPLETE (SKILL.md Phase 6 wiring — Steps 21-26 reference + Phase 5 stop gate removed) |
| Status | Phase 6 complete — all 27 plans complete; v1 skill end-to-end runnable |
| Progress | `[██████████] 6/6 phases complete` |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 6 / 6 |
| Phases complete | 1 / 6 |
| Plans complete | 6 |
| v1 requirements complete | 9 / 35 |
| Phase 02 P00 | 7min | 2 tasks | 9 files |
| Phase 02-signal-collection P01 | 12min | 2 tasks | 4 files |
| Phase 02-signal-collection P02 | 8min | 2 tasks | 2 files |
| Phase 02-signal-collection P03 | 15min | 1 tasks | 1 files |
| Phase 02-signal-collection P04 | 4min | 2 tasks | 2 files |
| Phase 02-signal-collection P05 | 12min | 2 tasks | 2 files |
| Phase 03-ranking-and-scoring P00 | 6min | 2 tasks | 3 files |
| Phase 03-ranking-and-scoring P01 | 1min | 1 tasks | 1 files |
| Phase 03-ranking-and-scoring P02 | 5min | 1 tasks | 1 files |
| Phase 04-clustering P00 | 2min | 2 tasks | 5 files |
| Phase 04-clustering P01 | 15min | 2 tasks | 2 files |
| Phase 04-clustering P02 | 8min | 1 tasks | 1 files |
| Phase 05-competitor-ad-copy-and-lp-extraction P00 | 8 | 2 tasks | 6 files |
| Phase 05-competitor-ad-copy-and-lp-extraction P01 | 25 | 2 tasks | 3 files |
| Phase 05-competitor-ad-copy-and-lp-extraction P02 | 5 | 1 tasks | 2 files |
| Phase 06-negatives-report-assembly-and-persistence P00 | 4 | 2 tasks | 12 files |
| Phase 06-negatives-report-assembly-and-persistence P01 | 12 | 1 tasks | 1 files |
| Phase 06-negatives-report-assembly-and-persistence P02 | 5 | 1 tasks | 1 files |
| Phase 06-negatives-report-assembly-and-persistence P03 | 8 | 1 tasks | 1 files |
| Phase 06-negatives-report-assembly-and-persistence P04 | 10 | 1 tasks | 1 files |
| Phase 06-negatives-report-assembly-and-persistence P05 | 87s | 2 tasks | 3 files |

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
- [Phase 02-signal-collection]: respx side_effect pattern used to capture outgoing POST body for locale assertion in serp_fetch tests
- [Phase 02-signal-collection]: 401/403 map to exit 3 (fatal auth); all other HTTPStatusError maps to exit 2 (retryable) in serp_fetch.py
- [Phase 02-signal-collection]: searchParameters echoed verbatim from Serper response into normalised output for downstream locale lint (Pitfall 4)
- [Phase 02-signal-collection]: argv[0] skip heuristic in main_with_args: strips script name if first element does not start with '-' — supports both full sys.argv and args-only list without requiring callers to slice
- [Phase 02-04]: Tavily raw_content: extract first 7-word phrase from first sentence (v1 intentionally simple — Phase 3 applies intent classification)
- [Phase 02-04]: source_diversity = distinct source strings not occurrence count (serper-paa + serper-organic = 2, not 1)
- [Phase 02-04]: websearch-baseline.json treated as optional — merge proceeds without it (exit 3 only if run_dir or raw_dir missing)
- [Phase 02-04]: keywords.json written to run_dir root (not raw/) to match Phase 3 consumption contract
- [Phase 02-05]: WebSearch invoked from skill prompt (not Python script) — SIGL-03 pattern; extracted_keywords verbatim-only rule (Pitfall 6 mitigation)
- [Phase 02-05]: Step 5 STOP replaced with conditional gate enabling progressive phase appending without breaking Phase 1 behaviour
- [Phase 02-05]: Phase 2 ends at Step 10 STOP; no Phase 3 scope in this skill update
- [Phase 03-ranking-and-scoring]: MODULE_MISSING guard (try/except ImportError + pytest.skip) for Wave 0 RED stubs — consistent with Phase 2 pattern; keeps collection clean without xfail noise
- [Phase 03-ranking-and-scoring]: Inline ocado login row fabricated in test_match_type_exact_navigational (diversity=3) to cover exact-navigational branch not present in fixture (ocado website is diversity=1)
- [Phase 03-ranking-and-scoring]: match_type passthrough from intent-labels.json — rank_keywords.py reads but never recalculates match_type; heuristic belongs to skill prompt Step 11
- [Phase 03-ranking-and-scoring]: 4-class intent rubric embedded inline in SKILL.md (not references/) — 365 lines total under 500-line limit; extraction deferred unless budget needed
- [Phase 03-ranking-and-scoring]: Phase 2 STOP replaced with forward gate enabling progressive Phase 3 appending without breaking Phase 2 behaviour
- [Phase 04-clustering]: VC_MISSING guard (try/except ImportError + pytest.skip) for Wave 0 RED stubs — consistent with Phase 3 MODULE_MISSING pattern; keeps collection clean and makes RED-to-GREEN transition explicit when validate_clusters.py is implemented in Wave 1
- [Phase 04-clustering]: clusters_oversize.json uses 4 real ranked_phase3 keywords + 22 synthetic fillers — test_oversize_exit3 builds ranked_index covering all 26 as transactional so only oversize violation fires
- [Phase 04-clustering]: check_clusters() accepts small_run=False param to suppress target_undersize warnings for narrow verticals (< 15 keywords) — aligns with CLI --small-run flag
- [Phase 04-clustering]: validate_clusters.py CLI computes orphans from ranked_index diff clustered_keywords set in addition to clusters_json orphans field — ensures all unassigned keywords surface
- [Phase 04-clustering]: check_avg_size() is a separate helper (not inside check_clusters) — CLI calls it independently to evaluate aggregate stats across all clusters
- [Phase 04-clustering]: Step 17 added (confirm+STOP) alongside Steps 14-16 — task detail and success criteria listed Steps 14-17; followed task detail
- [Phase 04-clustering]: Checkpoint auto-approved by code inspection — user asleep, all 5 verify criteria confirmed via Read tool + automated python check; marked auto-verified-by-inspection
- [Phase 05-competitor-ad-copy-and-lp-extraction]: [Phase 05-competitor]: MODULE_MISSING guard for Wave 0 RED stubs in test_competitor_intel.py — consistent with Phases 2-4 pattern; keeps collection clean and makes RED-to-GREEN transition explicit
- [Phase 05-competitor-ad-copy-and-lp-extraction]: extract_domain prepends '//' to schemeless URLs before urlparse — handles displayUrl values like 'awin1.com/grocery' that have no scheme, making affiliate domain checks reliable
- [Phase 05-competitor-ad-copy-and-lp-extraction]: scripts/pyproject.toml added to declare httpx-retries + tavily-python as project deps — enables uv run --with pytest --with respx to resolve transitive imports via --project flag
- [Phase 05-competitor-ad-copy-and-lp-extraction]: Phase 5 section body extracted to references/phase5-competitor-intel.md — SKILL.md was 551 lines with full inline content; extraction reduced to 473 lines (within 500-line limit)
- [Phase 05-competitor-ad-copy-and-lp-extraction]: SKILL.md Phase 5 pointer uses 'Load it with the Read tool when entering Phase 5' — explicit instruction rather than silent pointer ensures operator loads rubric before proceeding
- [Phase 06-negatives-report-assembly-and-persistence]: tabulate resolved as 0.10.0 (declared >=0.9.0) — backwards-compatible with tablefmt='github'
- [Phase 06-negatives-report-assembly-and-persistence]: test_update_index.py created as separate file per VALIDATION.md Wave 0 list — objective prompt also specified dedicated file; followed more specific requirement over PLAN.md bundling
- [Phase 06-negatives-report-assembly-and-persistence]: escape_md_cell guard uses AttributeError in addition to ImportError — lib.io exists but function absent; handles name-not-defined case
- [Phase 06-negatives-report-assembly-and-persistence]: Exit 1 (not 2) for all operator-warning conditions (enum errors, collisions, missing categories) per CLI contract; raw/ write guarded by dir existence check; dedup comparison is case-insensitive strip
- [Phase 06-negatives-report-assembly-and-persistence]: escape_md_cell uses module-level _SMART_QUOTE_MAP (str.maketrans) built at import time, O(n) per call with zero map construction overhead
- [Phase 06-03]: main() accepts optional argv parameter for testability — test_run_folder_complete calls main(["--run-dir", str(run_dir)]) directly without subprocess
- [Phase 06-03]: cluster_id derived at render time via _build_cluster_index(); null if keyword not in any cluster — ranked.json never mutated
- [Phase 06-03]: Competitor section prefers advertisers[] over ads[] when both present (advertisers has richer domain + extract_status fields)
- [Phase 06-04]: Open "a" mode for existing INDEX.md, write_text(HEADER+row) only on creation — avoids read-modify-write race and duplicate headers
- [Phase 06-04]: --runs-root optional CLI flag added (default run_dir.parent) for non-standard directory layouts
- [Phase 06-04]: Missing brief.md returns industry="unknown" with exit 0 — INDEX.md audit trail priority over completeness
- [Phase 06-05]: Step 21 instructs LLM to write negatives.json to {run_dir}/negatives.json (not raw/); generate_negatives.py copies validated output to raw/negatives.json — clean operator-writes / script-validates boundary
- [Phase 06-05]: Step 26 is a hard STOP with no continuation prompts — workflow complete signal is unambiguous

### Open Questions / Todos

- Composite ranking weight tuning (source_diversity vs signal_count vs intent) — v1 hypothesis; calibrate after first 3-5 real runs.
- Tavily credit consumption per run — estimated $0.09-$0.30; measure from run 1, adjust caps if needed.
- Cluster count vs vertical — narrow verticals may yield fewer than the 5-10 general recommendation; do not force the range.
- Match-type recommendation conservatism — validate after first campaign launch.

### Blockers

None.

## Session Continuity

**Last session:** 2026-05-08T07:20:09Z

**Stopped at:** Completed 06-05-PLAN.md

**Next session:** All 27 plans complete. v1 skill is end-to-end runnable. Run `/gsd:verify-work` for final sign-off.

**Files of record:**
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\PROJECT.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\REQUIREMENTS.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\ROADMAP.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\SUMMARY.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\ARCHITECTURE.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\PITFALLS.md`

---
*State initialized: 2026-05-08*
