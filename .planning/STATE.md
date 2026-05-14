---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: account-structure-mapping
status: defining_requirements
stopped_at: Milestone v1.2 started — Phase 11 (geo refinement + ad-group mapping) ahead
last_updated: "2026-05-14T22:00:00.000Z"
progress:
  total_phases: 11
  completed_phases: 10
  total_plans: 0
  completed_plans: 0
---

# State: Google Ad Research Agent

**Last updated:** 2026-05-14

## Project Reference

**Core value:** From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session.

**Current focus:** Milestone v1.2 — Account-Structure Mapping. Phase 11 (geo county/city refinement + ad-group mapping to existing client structure). Defining requirements.

## Current Position

| Field | Value |
|-------|-------|
| Phase | 11 — Account-Structure Mapping (not yet planned) |
| Plan | — |
| Status | Defining requirements |
| Last activity | 2026-05-14 — Milestone v1.2 started after team feedback (Palm Beach County focus + reuse existing ad groups) |

## Previous Milestone

v1.1 — Operator-Ready Output (2 phases 9-10, 23 requirements). Shipped 2026-05-14. Editor CSV exports, max-CPC bid suggestions, budget forecasts, Next Steps checklist, compliance flags.

v1.0 — Core Pipeline (8 phases, 52 requirements, 108 tests). Shipped 2026-05-08. End-to-end runnable: brief intake → signals → ranking → clustering → competitor intel → negatives/report → niche pulse → account data + Ahrefs enrichment.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 10 / 10 |
| Phases complete | 8 / 10 (Phase 9 plans 6/6 done; Phase 10 plan 00/?? scaffolding shipped) |
| Plans complete | 27 (v1.0) + 6 (v1.1 Phase 9) + 1 (v1.1 Phase 10 Wave 0) |
| v1.0 requirements complete | 52 / 52 |
| v1.1 requirements complete | 13 / 23 (BIDS 4/4, FRCS 5/5, CMPL 4/5 — CMPL-05 mapped to Phase 10; EXPT-* / STEP-* RED-scaffolded in 10-00, GREEN in Wave 1+) |
| Phase 10 P00 | ~25min | 2 tasks | 12 files created + 1 modified |
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
| Phase 09 P01 | 6min | 2 tasks | 1 files |
| Phase 09 P02 | 3min | 2 tasks | 1 files |
| Phase 09 P03 | 4min | 2 tasks | 1 files |
| Phase 09 P04 | 9min | 3 tasks | 2 files |
| Phase 09 P05 | 12min | 3 tasks | 2 files |

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
- [v1.1 roadmap]: Two-phase split (9: data layer, 10: output layer) chosen over single fat phase — Phase 10 CSVs and Next-Steps checklist consume Phase 9's `suggested_max_cpc_micros`, mid-forecast spend, and compliance flags; splitting makes success criteria observable in isolation and yields ~5-7 plans per phase rather than ~13.
- [v1.1 roadmap]: Phase 9 success criteria 4 enforces "data not code" for tuning knobs — bid multipliers in single config block, compliance verticals in `references/compliance-verticals.json` — so operator-side tuning needs zero Python edits.
- [v1.1 roadmap]: 23 v1.1 requirements mapped (not 22 as initial brief suggested) — recount: BIDS=4 + FRCS=5 + CMPL=5 + EXPT=5 + STEP=4 = 23. Discrepancy noted; all 23 mapped to phases.
- [Phase 09]: [Phase 09-01] bid_suggest.py: stub main_with_args(NotImplementedError) committed alongside core to lift MODULE_MISSING guard immediately — full CLI lands in Task 2 commit, preserving atomic per-task commit discipline
- [Phase 09]: [Phase 09-01] INTENT_MULTIPLIERS frozenset assertion at module import time guards typo / drift — fails fast (not at runtime); pattern available for forecast_budget.py INTENT_CTRS in plan 09-02
- [Phase 09]: [Phase 09-02] forecast_budget.py: INTENT_CTRS / AVG_CPC_RATIO / BAND_MULTIPLIERS in single module-level config block with frozenset assertion — mirrors INTENT_MULTIPLIERS pattern from 09-01; methodology block in forecast.json reads from these dicts so disclaimer edits live in one place (FRCS-05)
- [Phase 09]: [Phase 09-02] campaign_totals aggregated by SUM of per-cluster fields, not recomputed from raw rows (Pitfall 5) — keeps cluster-level and campaign-level skip-rules consistent; unjoined_keywords surfaced as silent-failure smoke signal
- [Phase 09]: [Phase 09-02] daily_clicks_mid kept as float (not int-rounded) so tests can use pytest.approx; only low/high bands int-rounded for clean stdout summary. Render layer (09-04) can format as needed
- [Phase 09]: [09-03] compliance_check: two-commit Task 1 (stub main_with_args) + Task 2 (full CLI) split — mirrors 09-01 bid_suggest pattern; lifts MODULE_MISSING guard immediately while preserving atomic per-task commits
- [Phase 09]: [09-03] compliance_check: matched_keyword_count reuses find_matches recursively (rather than re-tokenizing) — single source of truth for the word-boundary algorithm; per-keyword cost negligible at default top_n=50
- [Phase 09]: [09-03] compliance_check: ValueError from load_verticals on missing key maps to exit 3 (fatal, not retryable) — operator-edited references/compliance-verticals.json typos should fail fast, not silently emit empty matched_verticals[]
- [Phase 09]: [09-04] _micros_to_usd helper centralises Pitfall 8 conversion — both cpc_micros and suggested_max_cpc_micros now route through one place; replaces the inline cpc/10_000/100 formula that risked unit drift
- [Phase 09]: [09-04] HTML JS extensions (renderForecast / renderCompliance) intentionally deferred — markdown contract is the v1.1 ship path; report.json carries forecast + compliance so Phase 10 reads JSON, not HTML. Avoids regressing v1.0 HTML invariants without operator pain signal
- [Phase 09]: [09-04] Task 2/3 bundled RED+GREEN in single feat commit (vs Task 1 split RED-then-GREEN) — keeps per-task atomic commit discipline (one task = one commit) once the failing-first invariant has been demonstrated in Task 1
- [Phase 09]: [09-04] Compliance block uses markdown blockquote prefix (> ## ⚠ ...) rather than plain heading — natural visual containment in any GFM viewer without inline HTML; matches the warning-panel affordance from CMPL-03 design
- [Phase 09]: [09-04] render_forecast_section + render_compliance_warning both return empty string on absent data — graceful degrade built into the helper, not the caller; mirrors render_niche_pulse_section's contract
- [Phase 09]: [09-05] SKILL.md Phase 9 pointer follows Phase 5/7/8 reference-load pattern verbatim — "Load it with the Read tool when entering Phase 9" — keeps SKILL.md under the 500-line cap (497 lines after edit) while documenting the optional-in-v1.0 / mandatory-for-Phase-10 dual contract inline
- [Phase 09]: [09-05] references/phase9-economics-compliance.md (209 lines) mirrors phase8-account-data.md structure — When-to-run, Prerequisites, Step 36-40, Anti-patterns, Failure modes, Downstream contract — the explicit Phase 10 downstream-contract section is the upstream API spec for the Phase 10 planner (suggested_max_cpc_micros, campaign_totals.daily_spend_mid_usd, matched_verticals[].verification_url)
- [Phase 09]: [09-05] End-to-end smoke reused real Phase 8 run-folder (.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth) — exercises all three bid-suggest paths (direct cpc / cluster-median fallback / no_cpc_data flagged) and triggers compliance block naturally (medical + legal verticals matched). All 6 visual + suite checks green; 56/56 Phase 9 tests GREEN; 0 v1.0 regressions
- [Phase 09]: [09-05] Daily Clicks column in report.md renders raw Python floats (e.g., 0.44000000000000006) — cosmetic only, JSON contract correct, USD columns format correctly via _micros_to_usd. Deferred to Phase 10 / cleanup plan; not blocking Phase 9 closeout
- [Phase 10]: [10-00] Stub-then-guard pattern (mirrors Phase 9 09-01 / 09-03) — export_csv.py ships in Wave 0 with locked header constants (POSITIVES_HEADERS / NEGATIVES_HEADERS / AD_GROUPS_HEADERS), TIER_TO_LEVEL map, MATCH_TYPE_TITLECASE map, and a NotImplementedError-raising main(). Tests `try: import export_csv` succeeds; `MODULE_INCOMPLETE = not hasattr(export_csv, "write_positives")` is the GREEN signal. Strictly better than absent-module guarding because Wave 1 inherits header strings as single source of truth.
- [Phase 10]: [10-00] Per-function hasattr skip-guard on test_render_report.py extension (vs file-level pytestmark) — necessary because the file already hosts 23 GREEN Phase 6+9 tests. `_skip_unless_next_steps()` / `_skip_unless_export_section()` helpers wrap each new test so legacy GREEN keeps running while new Phase 10 RED stubs skip individually.
- [Phase 10]: [10-00] Byte-exact golden CSV fixtures (golden_positives.csv / golden_negatives.csv / golden_ad_groups.csv) — generated via `csv.DictWriter(lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)`, encoding='utf-8' (no BOM). Single `assert got == golden` catches BOM drift + CRLF drift + header-cell drift + column-order drift + cell-value drift in one shot. Strongest Nyquist signal for Editor-importable v2.x format.
- [Phase 10]: [10-00] Deterministic Campaign literal 'Phase 10 Test Brief' — derived from fixture run-dir name `2026-05-14T120000Z-phase-10-test-brief` → `_derive_brief_slug` → title-cased. Locked in goldens so Wave 1's slug-derivation cannot drift; tests read constant via module attribute, not by recomputing.
- [Phase 10]: [10-00] Informational cluster (grocery_delivery_basics_informational) in clusters_phase10.json intentionally seeded with all-null cpc_micros — exercises the BIDS-02 fallback path AND the 0.00-not-blank Default Max CPC rule (Pitfall 10) without needing a synthetic test-only cluster.
- [Phase 10]: [10-00] compliance_two_verticals fixture has 2 matched verticals (medical + legal) so CMPL-05 ONE-combined-step rule can be asserted directly via `len(verification_steps) == 1` rather than inferred.

### Open Questions / Todos

- Composite ranking weight tuning (source_diversity vs signal_count vs intent) — v1 hypothesis; calibrate after first 3-5 real runs.
- Tavily credit consumption per run — estimated $0.09-$0.30; measure from run 1, adjust caps if needed.
- Cluster count vs vertical — narrow verticals may yield fewer than the 5-10 general recommendation; do not force the range.
- Match-type recommendation conservatism — validate after first campaign launch.
- [v1.1] Bid multiplier calibration (transactional 1.2 / commercial 0.8 / informational 0.4 / navigational 1.0) — defensible starting point per PROJECT.md decision; revisit after first 3 v1.1 runs against client CPA targets.
- [v1.1] FRCS avg-CPC-to-max-CPC ratio of 0.65 and band spread (×0.5 / ×1.0 / ×1.5) — directional anchor, not Google forecast; measure delta against real campaign data after first 2-3 launches.
- [v1.1] Compliance vertical token lists — start with 5 (medical/legal/finance/gambling/crypto); operator can extend via `references/compliance-verticals.json`. Track which verticals get extended for v2 preset signal.

### Blockers

None.

## Session Continuity

**Last session:** 2026-05-14T20:10:00Z

**Stopped at:** Completed 10-00-PLAN.md (Wave 0 RED scaffolding for Operator Launch Kit). Tasks 1+2 committed (815988c + 3bdbcc7). 202 tests collected (up from 159); 149 GREEN legacy, 43 Phase 10 RED stubs SKIPPED via MODULE_INCOMPLETE / hasattr guards, 0 collection errors, 0 regressions. Wave 1 (plans 10-01 + 10-02) ready to start in parallel.

**Next session:** Execute 10-01 (`export_csv.py` write_positives / write_negatives / write_ad_groups + CLI — flips 23 EXPT cases GREEN) and 10-02 (`render_report.render_next_steps_section` + `build_report_json` `next_steps` kwarg — flips STEP-01..04 + CMPL-05 GREEN) in parallel. They share no mutated files.

**Files of record:**
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\PROJECT.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\REQUIREMENTS.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\ROADMAP.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\SUMMARY.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\ARCHITECTURE.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\PITFALLS.md`

---
*State initialized: 2026-05-08*
*v1.1 milestone started: 2026-05-14*
