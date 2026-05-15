---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Phases
status: unknown
stopped_at: Completed Plan 16-03 — RED tests authored for ADGM-11 per-source max-Jaccard structural fix; 3 RED tests + 20 PASSED; Plan 16-04 has clean GREEN target
last_updated: "2026-05-15T19:24:37.237Z"
progress:
  total_phases: 15
  completed_phases: 12
  total_plans: 65
  completed_plans: 63
---

# State: Google Ad Research Agent

**Last updated:** 2026-05-15

## Project Reference

**Core value:** From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session.

**Current focus:** Milestone v1.5 — Account-Aware Narrowing. Phase 15 (`campaign_focus` brief field filters all Phase 8 GAQL queries to one campaign) + Phase 16 (AG Mapping token-bag enrichment lifts 0% → 50%+ coverage). Triggered by Lake Worth dogfood (2026-05-15) showing contamination from unrelated campaigns + 0% AG mapping coverage. Phases 15 + 16 now in ROADMAP; planning Phase 15 next.

## Current Position

| Field | Value |
|-------|-------|
| Phase | 16 — Ad-Group Mapping Token-Bag Enrichment (ADGM-07..10 complete; ADGM-11 RED-state wired Plan 16-03 → GREEN target Plan 16-04) |
| Plan | 16-00 + 16-01 + 16-02 + 16-03 complete; Plan 16-04 next (structural fix: replace full-union Jaccard with `max(name_j, crit_j, term_j)` in `ad_group_match.build_mapping`) |
| Status | Plan 16-03 RED tests authored: 3 FAILED (Lake Worth floor + lynchpin per-source max + tied-sources score-VALUE 0.333 vs full-union 0.50) + 20 PASSED (C2 80% Phase 11 invariant + C5 garbage-low + ADGM-07..10 reason-field all preserved); xfail decorator removed from test_lake_worth_coverage_floor; Plan 16-04 has clean GREEN target |
| Last activity | 2026-05-15 — Plan 16-03 RED test authoring: 4 new tests + 1 xfail-removal in test_ad_group_match.py (commit 7d76a9e, 267 insertions / 17 deletions); lynchpin `test_per_source_max_jaccard_used_for_scoring` uses constructed in-memory fixture (1 AG name='Accident' + 30 distinct non-overlapping criteria) where full-union 1/31 ≈ 0.032 → low but per-source max name_j=1.0 → high; tied-sources test uses score-VALUE assertion (≈0.333) not score-CLASS to surface the algorithm delta cleanly |

## Previous Milestone

v1.4 — Positives Sync (1 phase, 7 reqs). Shipped 2026-05-15. perf_fetch keyword_view + perf_synth cross_ref_positives + 4-bucket positives-sync.json + render section md+HTML+JSON + export_csv filter + SKILL.md Step 34a LLM re-tag. Live e2e Lake Worth confirmed: 83 ranked → 11 already_active / 8 covered_by_broad / 64 new_to_add. Post-ship UX fix: Existing Ad Groups always rendered in Mapping section (commit 4674b00). 96/96 v1 requirements Complete.

v1.3 — Source Consolidation / Drop Tavily (1 phase, 11 reqs). Shipped 2026-05-15. tavily_extract.py deleted; WebFetch replaces COMP-03 landing-page extraction; Serper /news single-source niche pulse; pyproject deps cleaned; full suite 250/250.

v1.2 — Account-Structure Mapping (1 phase, 11 reqs). Shipped 2026-05-15. Brief `geo_focus`, us-cities filter, ad_group_match.

v1.1 — Operator-Ready Output (2 phases 9-10, 23 requirements). Shipped 2026-05-14. Editor CSV exports, max-CPC bid suggestions, budget forecasts, Next Steps checklist, compliance flags.

v1.0 — Core Pipeline (8 phases, 52 requirements, 108 tests). Shipped 2026-05-08. End-to-end runnable: brief intake → signals → ranking → clustering → competitor intel → negatives/report → niche pulse → account data + Ahrefs enrichment.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 16 (13 shipped + Phase 13 BACKLOG + Phases 15-16 pending) |
| Phases complete | 13 (v1.0 + v1.1 + v1.2 + v1.3 + v1.4 all complete; v1.5 pending) |
| Plans complete | 27 (v1.0) + 6 (v1.1 Phase 9) + 5 (v1.1 Phase 10) + 5 (v1.2 Phase 11) + 6 (v1.3 Phase 12) + 6 (v1.4 Phase 14) = 55 |
| v1.0 requirements complete | 52 / 52 |
| v1.1 requirements complete | 23 / 23 (BIDS 4/4, FRCS 5/5, CMPL 5/5, EXPT 5/5, STEP 4/4) |
| v1.2 requirements complete | 11 / 11 (GEO 5/5, ADGM 6/6) |
| v1.3 requirements complete | 11 / 11 (TVLY 4/4, WFCH 4/4, PULSE 3/3) |
| v1.4 requirements complete | 7 / 7 (POS-01..07) |
| v1.5 requirements complete | 7 / 11 (CAMP 3/6 — CAMP-01 + CAMP-02 + CAMP-05 shipped via Plans 15-01 + 15-02; CAMP-03 SKILL wiring + CAMP-04 graceful degrade + CAMP-06 test coverage all already met but not yet marked; ADGM 4/5 — ADGM-07..10 shipped via Phase 16 Plans 01 + 02; ADGM-11 deferred to structural-algorithm follow-up plan) |
| Phase 15 P00 | ~8min | 3 tasks | 2 created + 2 modified |
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
| Phase 12-source-consolidation-drop-tavily P05 | ~20min | 3 tasks | 10 files |
| Phase 14 P00 | ~18min | 3 tasks | 5 created + 3 modified |
| Phase 14 P01 | 2min | 2 tasks | 1 files |
| Phase 14 P02 | 2min | 2 tasks | 1 files |
| Phase 14 P04 | 3min | 2 tasks | 1 files |
| Phase 14 P03 | ~4min | 2 tasks | 1 files |
| Phase 14 P05 | 12min | 3 tasks | 2 files |
| Phase 15-campaign-focus P01 | 3 min | 2 tasks | 1 files |
| Phase 15-campaign-focus P02 | 2 min | 2 tasks | 1 files |
| Phase 15-campaign-focus P03 | 12 min | 3 tasks | 3 files |
| Phase 16 P00 | 12min | 2 tasks | 7 files |
| Phase 16-ad-group-mapping-token-bag-enrichment P01 | 18min | 4 tasks | 2 files |
| Phase 16-ad-group-mapping-token-bag-enrichment P02 | ~25min | 2 tasks (1 docs + 1 human-verify live e2e) | 1 modified + 1 created |
| Phase 16-ad-group-mapping-token-bag-enrichment P03 | ~3min | 1 tasks | 1 files |

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

- [v1.5 roadmap]: Two-phase split (15: Campaign Focus filter, 16: AG token-bag enrichment) chosen over single fat phase — Phase 16 must calibrate against the narrowed dataset Phase 15 produces; running enrichment against full-account data inflates denominators with out-of-scope AGs and gives noisy thresholds. Splitting also keeps success criteria observable in isolation (Phase 15 = "raw artifacts contain only target campaign"; Phase 16 = "≥50% high+medium coverage").
- [v1.5 roadmap]: Phase 15 mirrors Phase 11's `geo_focus` architectural pattern exactly — brief.md field parsed by `_parse_brief_fields`, threaded through `perf_fetch.py --campaign-filter`, rendered as report-header callout. Same proven shape, just at campaign-name level instead of geographic-token level. No new external APIs (reuses existing Google Ads OAuth from Phase 8 + Phase 14 raw).
- [v1.5 roadmap]: Phase 16 backward compat is non-negotiable — when `raw/google-ads-keywords.json` (Phase 14 output) absent, falls back to current name-only Jaccard. Phase 11 behavior preserved for pre-Phase-14 accounts; no regression on installs that have not opted into OAuth.
- [v1.5 roadmap]: Threshold recalibration (likely 0.5 high / 0.25 medium vs current 0.7 / 0.4) deliberately deferred to empirical calibration on ≥2 real accounts; documenting rationale in `references/phase11-account-structure-mapping.md` keeps the tuning knob auditable and operator-tunable without code edits.
- [v1.5 roadmap]: Phase 13 (Landing-Page Extract Vendor Swap) stays parked as defer-until-friction backlog under v1.3 — WebFetch real-run pass on Lake Worth brief means trigger condition not met. Phase 14 → 15 → 16 skips ahead in the numbering; Phase 13 is NOT a prerequisite, the two tracks are orthogonal.
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
- [Phase 14]: [14-05] Live e2e on real Lake Worth car-accident/urgent-care account approved Phase 14 closeout: positives-sync.json stats {our_total:83, already_active:11, paused:0, covered_by_broad:8, new_to_add:64} sums correctly; positives.csv = 64 rows + header matches stats.new_to_add. paused_in_account empty is legitimate (no paused kw in account). LLM re-tag invocation deferred to next real operator session (script-only output already operator-actionable; not blocking).
- [Phase 15-campaign-focus]: [15-01]: Pipe-split heuristic for --campaign-filter — ' | ' (space-pipe-space) preserved as single Google-Ads-naming-convention campaign name; bare '|' (no spaces) splits into list. Single-quoted operator copy-paste of names like 'Search | Lake Worth Accident Exams | Manual CPC' stays one filter value.
- [Phase 15-campaign-focus]: [15-01]: Empty-clause contract — _apply_campaign_filter returns '' when filter is None/empty so callers inject {campaign_clause} unconditionally; preserves v1.4 GAQL byte-identical modulo whitespace (CAMP-04 backward compat).
- [Phase 15-campaign-focus]: [15-02]: render_campaign_focus_section bypasses escape_md_cell — Google Ads campaign names like 'Search | Lake Worth Accident Exams | Manual CPC' use pipes by convention; escaping breaks operator recognition. Name validation against perf.json is case-sensitive (Google Ads API preserves case + enforces uniqueness).
- [Phase 15-campaign-focus]: [15-03]: SKILL.md stays at 497/500 lines by offloading Step 33 --campaign-filter contract to references/phase8-account-data.md — trigger row + template line are the only SKILL.md edits; detailed contract loads on demand via progressive disclosure
- [Phase 15-campaign-focus]: [15-03]: Live e2e on real Lake Worth OAuth account is the closeout gate, not unit tests alone — Plan 15-00/15-01/15-02 unit tests are necessary but not sufficient; only a real Google Ads pull confirms the GAQL clause narrows server-side (verified: 30+ campaigns → 1, 35+ AGs → 3, 47 focused keywords)
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-00]: Used real-run row counts (66 ranked, 1 ENABLED AG) over plan estimates (47, 3) — plan philosophy 'fidelity to real run' wins over planner's pre-flight estimate
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-00]: Keywords fixture re-shaped from flat real-data schema into nested ad_group_criterion.keyword.text form to match plan 16-01 _build_ag_token_bag contract — defers Wave 2 adapter complexity into the fixture
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-00]: Threshold sentinel test ships WITHOUT skip guard — must FAIL at Wave 0 against 0.7/0.4 stub values to prove TDD wiring is connected; flips green when Wave 2 lands recalibration delta
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-01] Operator chose option-a (accept Lake Worth coverage miss, defer ADGM-11 floor to plan 16-02) — Lake Worth coverage gap is STRUCTURAL not threshold-tunable; 34-token enriched AG bag vs 4-6-token queries caps observed jaccard at 0.15-0.25 within loosening cap floor (high>=0.30, medium>=0.10)
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-01] _THRESHOLDS locked at calibration_protocol cap FLOOR {high: 0.30, medium: 0.10} — yields 16.67% Lake Worth coverage (11 medium / 66 ranked) while preserving Phase 11 80% invariant + C5 garbage-keyword guard. xfail-with-rationale strategy on test_lake_worth_coverage_floor (strict=True) preserves test intent + signals operator-acknowledged deferral without test deletion
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-02] ADGM-10 documentation routes through `references/phase11-account-structure-mapping.md` (+78 lines) NOT SKILL.md — preserves SKILL.md ≤500 invariant (still 497/500) via existing Phase 11 progressive-disclosure pointer. Threshold rationale auditable from one file read.
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-02] Live e2e on real Lake Worth OAuth account observed `mapping_coverage_pct = 16.42%` vs offline goldenfile 16.67% (0.25pp delta) — confirms (a) Phase 16 enrichment wires correctly end-to-end with no regression from 0% pre-enrichment baseline, (b) goldenfile is NOT overfit, and (c) the Jaccard ceiling that caps coverage below 50% is STRUCTURAL (bag-vs-query asymmetry holds on real data), not a fixture artifact.
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-02] Live sample reason field on real OAuth data: `jaccard=0.10 (name=0.33 kw-criterion=0.00 search-term=0.00) intent_match=True` — confirms meaningful matches happen one-source-at-a-time (name carries 0.33, kw + st 0.00) while full-union Jaccard dilutes to 0.10. Directly motivates per-source max-jaccard as the leading structural-fix candidate for ADGM-11 follow-up.
- [Phase 16-ad-group-mapping-token-bag-enrichment]: [16-03] 4 RED tests + xfail-removal pin per-source max-Jaccard contract for Plan 16-04; suite runs 3 FAILED (Lake Worth floor + lynchpin per-source max + tied-sources score-VALUE 0.333 vs full-union 0.50) + 20 PASSED (C2 80% invariant + C5 garbage-low preserved). Score-VALUE assertion in tied-sources test (not score-CLASS) is the key TDD pattern: full-union 0.50 also classifies high, so a class-only assertion would have masked the algorithm shift.

### Open Questions / Todos

- Composite ranking weight tuning (source_diversity vs signal_count vs intent) — v1 hypothesis; calibrate after first 3-5 real runs.
- Cluster count vs vertical — narrow verticals may yield fewer than the 5-10 general recommendation; do not force the range.
- Match-type recommendation conservatism — validate after first campaign launch.
- [v1.1] Bid multiplier calibration (transactional 1.2 / commercial 0.8 / informational 0.4 / navigational 1.0) — defensible starting point per PROJECT.md decision; revisit after first 3 v1.1 runs against client CPA targets.
- [v1.1] FRCS avg-CPC-to-max-CPC ratio of 0.65 and band spread (×0.5 / ×1.0 / ×1.5) — directional anchor, not Google forecast; measure delta against real campaign data after first 2-3 launches.
- [v1.1] Compliance vertical token lists — start with 5 (medical/legal/finance/gambling/crypto); operator can extend via `references/compliance-verticals.json`. Track which verticals get extended for v2 preset signal.
- [v1.4] `covered_by_broad` heuristic false-positive rate — Google's broad-match expansion is fuzzy; measure how often the LLM re-tag flips script's `covered_by_broad` calls in the first 2-3 v1.4 runs.
- [v1.4] PMax / Search-Themes auto-added keywords — `keyword_view` surfaces them; will appear in `already_active`. Operator confusion risk if origin not surfaced — add origin field to HTML if friction observed.
- [v1.5] Multi-campaign `campaign_focus` (list form) ergonomics — rare but real (operator running Lake Worth across 2 campaigns). Single-value default keeps common case clean; list form via pipe-separated or YAML list — finalize syntax in Phase 15 plan.
- [v1.5] Threshold recalibration empirical target — Phase 16 16-02 locked `{0.30, 0.10}` based on Lake Worth (one account). After the next OAuth-enabled real account ships AND the structural-fix follow-up for ADGM-11 lands, re-run calibration; reference doc `references/phase11-account-structure-mapping.md` carries the audit trail (ADGM-10 satisfied).
- [v1.5] Search-term-bag top-N cutoff — currently planned at top-10 by clicks with zero-impression filter; revisit if real-account mapping shows noise from lossy / off-topic search terms pulling matches wrong direction.
- [v1.5] **ADGM-11 structural-algorithm follow-up plan (carried from Phase 16 closeout):** Live Lake Worth OAuth e2e observed 16.42% coverage (offline goldenfile 16.67% — within 0.25pp), confirming the gap to the 50% floor is STRUCTURAL not threshold-tunable. Candidate algorithm changes (named in 16-01 xfail rationale, reaffirmed by 16-02 live sample reason field `name=0.33 kw=0.00 st=0.00 -> full-union=0.10`): (1) per-source max-jaccard replacing full-union Jaccard — leading candidate, directly addresses the live-observed dilution failure mode; (2) token-bag subsampling — cap AG bag at top-K most informative tokens; (3) asymmetric similarity `|A ∩ B| / |A|` where A = query. Next planning cycle should author a structural-fix plan; sweep table in 16-01-SUMMARY documents the threshold-pair exhaustion that rules out re-calibration as a fix.

### Blockers

None.

## Session Continuity

**Last session:** 2026-05-15T19:24:37.233Z

**Stopped at:** Completed Plan 16-03 — RED tests authored for ADGM-11 per-source max-Jaccard structural fix; 3 RED tests + 20 PASSED; Plan 16-04 has clean GREEN target

**Next session:** Author a structural-algorithm follow-up plan for ADGM-11 (>=50% mapping coverage floor). Leading candidate per 16-02 live sample reason-field evidence: per-source max-jaccard replacing full-union Jaccard in `ad_group_match.py::_classify`. Plan should also pin a 2nd real OAuth account for the next-account calibration cycle once the structural fix lands.

**Files of record:**
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\PROJECT.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\REQUIREMENTS.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\ROADMAP.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\proposed\v1.5-account-aware-narrowing.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\SUMMARY.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\ARCHITECTURE.md`
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\research\PITFALLS.md`

---
*State initialized: 2026-05-08*
*v1.1 milestone started: 2026-05-14*
*v1.4 milestone started: 2026-05-15*
*v1.5 milestone started: 2026-05-15*
*v1.5 ROADMAP entries added: 2026-05-15 — Phases 15 + 16 (CAMP-01..06 + ADGM-07..11) detailed; 95/95 v1 requirements mapped.*
