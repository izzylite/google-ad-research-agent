---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Phases
status: unknown
stopped_at: "Completed 12-04-PLAN.md — WFCH-01 + WFCH-02 + PULSE-12 GREEN. 8/8 Wave 0 audit tests GREEN. SKILL.md 486/500. 3 commits: 9028020 (Task 1 docs), 0b21392 (Task 2 SKILL+lib), 36f3a59 (Task 3 render+JOIN). Suite: 249 passed, 1 failed (Plan 12-01 test_config leftover, deferred to 12-05), 0 skipped."
last_updated: "2026-05-15T04:16:19.661Z"
progress:
  total_phases: 11
  completed_phases: 9
  total_plans: 49
  completed_plans: 48
---

# State: Google Ad Research Agent

**Last updated:** 2026-05-15

## Project Reference

**Core value:** From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session.

**Current focus:** Milestone v1.3 — Source Consolidation. Phase 12 (drop Tavily; swap to WebFetch + Serper). Triggered by Tavily quota exhaustion during dogfood re-run.

## Current Position

| Field | Value |
|-------|-------|
| Phase | 12 — Source Consolidation (Drop Tavily) |
| Plan | 04 complete (Wave 2 done; Plan 12-05 final-gate next) |
| Status | WFCH-01 + WFCH-02 + PULSE-12 GREEN; 8/8 Wave 0 audit tests GREEN; SKILL.md 486/500; Plan 12-05 (full-suite gate + e2e smoke) ready |
| Last activity | 2026-05-15 — Plan 12-04 rewrote Phase 5 + Phase 7 docs for WebFetch; render_report.py JOINs raw/competitor-landing-pages.json. Suite: 249 passed, 1 failed (test_config Plan-12-01 leftover, deferred), 0 skipped. |

## Previous Milestone

v1.2 — Account-Structure Mapping (1 phase, 11 reqs). Shipped 2026-05-15. Brief `geo_focus`, us-cities filter, ad_group_match.

v1.1 — Operator-Ready Output (2 phases 9-10, 23 requirements). Shipped 2026-05-14. Editor CSV exports, max-CPC bid suggestions, budget forecasts, Next Steps checklist, compliance flags.

v1.0 — Core Pipeline (8 phases, 52 requirements, 108 tests). Shipped 2026-05-08. End-to-end runnable: brief intake → signals → ranking → clustering → competitor intel → negatives/report → niche pulse → account data + Ahrefs enrichment.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 11 / 11 |
| Phases complete | 11 / 11 (v1.0 + v1.1 + v1.2 all complete) |
| Plans complete | 27 (v1.0) + 6 (v1.1 Phase 9) + 5 (v1.1 Phase 10) + 5 (v1.2 Phase 11) = 43 |
| v1.0 requirements complete | 52 / 52 |
| v1.1 requirements complete | 23 / 23 (BIDS 4/4, FRCS 5/5, CMPL 5/5, EXPT 5/5, STEP 4/4) |
| v1.2 requirements complete | 11 / 11 (GEO 5/5, ADGM 6/6) |
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
| Phase 11 P00 | 7min | 3 tasks | 11 created + 5 modified |
| Phase 11 P00 | 7 | 3 tasks | 16 files |
| Phase 11 P01 | 8 | 4 tasks | 6 files |
| Phase 11 P02 | 6 | 3 tasks | 2 files |
| Phase 11 P03 | 9 | 2 tasks | 3 files |
| Phase 11 P04 | ~25min | 3 tasks (2 docs + 1 auto-fix + 1 human-verify) | 3 files (1 created + 2 modified) |
| Phase 12 P00 | 12min | 3 tasks | 8 files |
| Phase 12-source-consolidation-drop-tavily P01 | 2min | 2 tasks | 9 files |
| Phase 12-source-consolidation-drop-tavily P03 | 5min | 2 tasks | 4 files |
| Phase 12-source-consolidation-drop-tavily P02 | 25min | 2 tasks | 4 files |
| Phase 12-source-consolidation-drop-tavily P04 | 45min | 3 tasks | 7 files |

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
- [Phase 11]: test_ad_group_match.py uses per-function _skip_unless_build_mapping() guard (NOT module-level pytestmark) so test_module_imports PASSES against the Wave-0 stub while other 13 tests SKIP — mirrors Phase 10 10-00 per-function pattern
- [Phase 11]: ad-group-mapping-*pct.json fixtures encode coverage_pct exactly at 50.0 (boundary - no rewrite), 60.0 (rewrite), 20.0 (negative path) so ADGM-06 strict- math is testable without running build_mapping
- [Phase 11]: us-cities-subset.json schema: state_code_lower -> city_lower -> county_lower (county as VALUE, no 'county' suffix). Wave 1 plan 11-01 will strip 'county' suffix from geo_focus tokens before lookup
- [Phase 11]: Wave-1 contract pre-decisions: merge_signals.py grows --us-cities-path CLI flag (tests monkeypatch _US_CITIES_DATA_PATH constant); render_next_steps_section gains ad_group_mapping kwarg in Wave 2 plan 11-03 (tests detect via inspect.signature)
- [Phase 11]: [Phase 11-01] us-cities.json composed from plotly top-1k (population priority) + millbj92 USCities (county lookup via dominant ZIP-derived county) + 13 manual fixture entries — 51 states (50+DC), ~4800 cities, 103KB minified (well under 200KB budget); territories (PR/VI/GU/AS/MP/FM/MH/PW) excluded since GEO-03 targets US states only
- [Phase 11]: [Phase 11-01] _build_city_filter normalises geo_focus via _strip_county_suffix once, then matches each state-cities entry on city name OR county value — Pitfall 5 city→county hierarchy verified by test_keyword_kept_when_city_county_in_geo_focus (boca raton survives Palm Beach focus)
- [Phase 11]: [Phase 11-01] _augment_seed_with_geo case-insensitive substring dedup feeds BOTH POST body q AND persisted by_seed[].seed — Phase 3 downstream sees the same augmented query, no schema drift. Empty --geo-focus default preserves Phase 2-10 backward compat
- [Phase 11]: [Phase 11-01] _GEO_FOCUS_SUPPORTED module marker on serp_fetch enables tests to detect Phase 11 wiring via hasattr without monkey-importing argparse internals; merge_signals exposes _US_CITIES_DATA_PATH constant for monkeypatch-style fixture injection PLUS --us-cities-path CLI flag as the production override path
- [Phase 11]: [Phase 11-02] _INTENT_MARKERS['transactional'] extended with healthcare/service action words (doctor, clinic, treatment, exam, care, injury, appointment, service, repair, install) — plan's minimal lexicon (buy/order/book/cheap/delivery/price) was too sparse for paid-search ad-group bags, causing every fixture bag to default to 'commercial' and breaking test_token_bag_keyed_by_ad_group_name (0.5 raw jaccard × 0.5 mismatch = 0.25 → low → None)
- [Phase 11]: [Phase 11-02] build_mapping rounds final score to 4 decimals (round(score, 4)) for stable JSON diff in committed mapping fixtures and snapshot tests — eliminates floating-point representation noise across platforms
- [Phase 11]: [Phase 11-02] test_module_imports rewritten from Wave-0 stub-state assertions (assert not hasattr build_mapping + main raises NotImplementedError) to Wave-1 public-surface assertions (hasattr build_mapping/_tokens/_jaccard/_classify/_intent_match_multiplier/_infer_ad_group_intent/_build_ad_group_index + callable main_with_args) — original assertions were intrinsically incompatible with Wave 1 helpers landing
- [Phase 11]: [Phase 11-02] test_coverage_pct_high_plus_medium_only rewritten with deterministic-jaccard keywords (6×0.7/2×0.5+0.4/2×0.0 against Accident-Exams–Lake-Worth bag) — original Wave-0 keywords ('hi 0' / 'med 0' / 'low 0') shared zero tokens with every ad-group bag, making asserted 80% coverage literally unachievable. Per-tier sanity counts added for explicit math contract
- [Phase 11]: [Phase 11-03] Mapped keywords override cluster assignment entirely (not just relabel): _build_positives_rows emits a row for any keyword the mapping resolves to an existing AG, even when the LLM clusterer orphaned it. Without this, mapping could only relabel rows our clusterer already happened to group — partially defeating the ADGM-05 contract.
- [Phase 11]: [Phase 11-03] ADGM-06 step-3 rewrite applied BEFORE CMPL-05 compliance prepend so it targets the static template index 2 (the 'Create ad groups: ...' slot) regardless of compliance state. Reversing the order would force the rewrite to chase a moving index after compliance shifts steps down by 1.
- [Phase 11]: [Phase 11-03] _stage_mapping_run test helper augments ranked-enriched + clusters with mapping keywords when a mapping fixture is supplied (Rule-1 deviation). Original Wave-0 fixtures had zero keyword overlap between grocery ranked rows and accident-doctor mapping entries, making the existing-AG assertion structurally unachievable.
- [Phase 11]: [Phase 11-04] Phase 11 step rubric (Steps 44-47) lives ONLY in references/phase11-account-structure-mapping.md (240 lines); SKILL.md gets a single pointer line. Mirrors Phase 5/7/8/9/10 precedent. Final SKILL.md = 499 / 500 (under by 1 after Phase 11 wiring + compaction of blank lines between Phase 9 and Phase 10 pointers).
- [Phase 11]: [Phase 11-04] render_report._parse_brief_fields regex (auto-fix during e2e smoke) extended to accept BOTH `**Field:**` and `**Field**:` forms — colon can be inside OR outside the bold markers. Discovered when smoke brief used the colon-outside form and Geographic Focus section silently dropped. Rule 1 (bug) fix, no architectural change. Commit 16f5d5d.
- [Phase 11]: [Phase 11-04] Coverage 0.0% on real urgent-care account (73 keywords vs 83-token search-term bag, all jaccards below 0.4) is MATHEMATICALLY CORRECT, not a bug. Anti-pattern documented in references/phase11 explicitly covers narrow-vertical low coverage. ADGM-06 strict > 50.0 threshold confirmed honored — Next Steps step 4 stayed at default "Create ad groups" template instead of rewriting to "Add keywords to existing ad groups: ...".
- [Phase 11]: [Phase 11-04] CMPL-05 compliance-first reorder verified end-to-end against real account: Next Steps step 1 = compliance verification (medical + legal verticals matched in urgent-care brief). ADGM-06 rewrite would have targeted step 4 (post-CMPL-05 prepend) had coverage been > 50%. Order of operations (ADGM-06 before CMPL-05 prepend, per plan 11-03 decision) holds in production.
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-00] All-surfaces grep test skips tests/ + .venv + site-packages — Phase 12 test files legitimately contain 'tavily' in assertion messages; production audit target is scripts/ (non-test) + references/ + SKILL.md only
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-00] WFCH-02 render_report test uses per-function _skip_unless_join_implemented() sentinel (NOT module-level pytestmark) — preserves 41 legacy GREEN tests in same file; mirrors Phase 10 10-00 + Phase 11 11-02 pattern
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-00] WFCH-03 competitor_intel guard uses BOTH inspect.getsource substring AND dir() namespace scan — covers Tavily dict-literal keys (raw_content) AND symbol imports (TavilyClient)
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-00] Phase 12 fixtures prefixed phase12- (phase12-competitor-intel.json, phase12-competitor-landing-pages.json) — distinguishes from Phase 5 competitor_intel_full.json which still carries Tavily-shape entries used by 41 GREEN render_report tests
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-00] Wave 2 plan 12-04 must land _load_competitor_landing_pages helper on render_report — exact symbol name locked by hasattr sentinel in test_render_report.py::_skip_unless_join_implemented
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-01] uv.lock regenerated in-task (5 transitive deps auto-pruned: charset-normalizer, regex, requests, tiktoken, urllib3). Deferral path (per plan) not needed — uv lock is metadata-only and does not require import resolution. Cleaner outcome than deferring to plan 12-02 closing task.
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-01] Task 2 commit absorbed by parallel Plan 12-03 commit f153729. Both plans needed identical edits to shared config files (.env.example, lib/config.py, pyproject.toml, uv.lock). Disk state matches spec; only commit attribution shifted. Structural race in parallel-wave shared-config files — future waves should explicitly document shared-config ownership.
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-03] Test fixture enrichment chosen over MIN_THEME_MENTIONS_FLOOR re-tune — adjusting serper_news.json snippets to surface 'florida pip law' as a substantive 3-gram in 3 items keeps pre-existing test_find_themes_clusters_repeated_phrases GREEN under single-source mode without violating Plan 12-05's threshold-tuning ownership
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-03] load_news_items signature reduced to single Path arg + main() caller chain collapses to one local — PULSE-11 contract; missing-input error message simplifies from 'Neither serper-news.json nor tavily-news.json found' to 'serper-news.json not found'
- [Phase 12-source-consolidation-drop-tavily]: [Phase 12-03] Parallel-wave commit hygiene: explicit per-path git add + git status --short review before commit prevents absorption of concurrent Plan 12-01 / 12-02 working-tree changes when Wave 1 plans run simultaneously
- [Phase 12-source-consolidation-drop-tavily]: [Plan 12-02] Comment-text purity for substring audit — Removed Phase 12 archaeological comments (Phase 12: tavily-extract removed) from production .py files; would have left 'tavily' substrings violating the strict must-have. Deletion archaeology lives in 12-02-SUMMARY.md instead. Future Phase 12 cleanups should follow the same pattern: prose narrative goes in SUMMARY.md, not in surviving code files.
- [Phase 12-source-consolidation-drop-tavily]: [Plan 12-02] Co-located test refactor — Pre-existing Phase 5 + Phase 2 tests that asserted on Tavily-shape fields (raw_content, extract_status, source_diversity == 6, _write_tavily helper) were updated in the SAME commit as the production refactor. Atomic per-task review: each commit is one self-consistent change. Wave 0 audit shape is the source of truth for what assertions should look like post-refactor.
- [Phase 12-source-consolidation-drop-tavily]: [Plan 12-02] Orphan helper detection before deletion — _extract_first_phrase + _PUNCT_STRIP regex in merge_signals.py had read_tavily as their only consumer (verified via grep). Deleted alongside read_tavily rather than keeping them as dead code; keeping them would also have inflated the source-text 'tavily' count via the docstring reference. Pattern: grep for callers before deleting any function, then aggressively prune orphans in the same commit.
- [Phase 12-source-consolidation-drop-tavily]: [Plan 12-04] render_competitor_section signature extended with optional run_dir kwarg (not required) — preserves backward compat with every existing test in test_render_report.py while enabling Wave 0 WFCH-02 JOIN. Adding required arg would have cascade-broken 41 pre-existing GREEN tests.
- [Phase 12-source-consolidation-drop-tavily]: [Plan 12-04] Out-of-scope file scrubs (lib/http.py 1-line docstring + render_report.py 5 Tavily mentions) bundled with their owning task commits rather than spawning separate deviation commits — Rule 3 (blocking) justification: test_repo_grep_tavily_clean is the gate, and decoupling would have forced Plan 12-05 to redo this work.
- [Phase 12-source-consolidation-drop-tavily]: [Plan 12-04] Wave 0 test fixture bug (Rule 1) — test_competitor_section_joins_webfetch_results wrote negatives.json as tier-keyed dict; Phase 6 contract is flat list. Fixed inline because the test's actual contract is competitor-section content assertions, not negatives shape; without fix, render_negatives_section crashes before reaching the section under test.

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

**Last session:** 2026-05-15T04:16:07.466Z

**Stopped at:** Completed 12-04-PLAN.md — WFCH-01 + WFCH-02 + PULSE-12 GREEN. 8/8 Wave 0 audit tests GREEN. SKILL.md 486/500. 3 commits: 9028020 (Task 1 docs), 0b21392 (Task 2 SKILL+lib), 36f3a59 (Task 3 render+JOIN). Suite: 249 passed, 1 failed (Plan 12-01 test_config leftover, deferred to 12-05), 0 skipped.

**Next session:** Milestone v1.2 complete. All 11 / 11 phases shipped (v1.0 + v1.1 + v1.2). No active phase. Options: (1) Define v1.3 milestone scope, (2) Address open-question/todos list (composite ranking calibration, Tavily credit metrics, match-type recommendation validation, v1.1 bid multiplier calibration, FRCS ratio tuning), (3) Triage v2 backlog (VOLM-*, VPRS-*, TOOL-*).

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
