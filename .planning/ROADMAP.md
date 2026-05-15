# Roadmap: Google Ad Research Agent

**Created:** 2026-05-08
**Granularity:** standard (5-8 phases)
**Coverage:** 35/35 v1 requirements mapped (100%)

## Core Value

From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session, without the operator leaving the chat.

## Phases

- [x] **Phase 1: Skill Scaffold and Brief Intake** — Project structure, env contract, run folder layout, conversational brief capture; nothing paid runs without a validated brief on disk. (completed 2026-05-08)
- [x] **Phase 2: Signal Collection** — Three-source harvest (Serper, Tavily, WebSearch) with locale plumbing, source attribution, and lemmatized canonicalization before any scoring. (completed 2026-05-08)
- [x] **Phase 3: Ranking and Scoring** — LLM 4-class intent classification + composite ranking (signal_count + source_diversity + intent weight) producing the canonical keyword table schema. (completed 2026-05-08)
- [x] **Phase 4: Clustering** — Intent-homogeneous LLM clusters of 5-15 keywords with descriptive theme + intent names, ad-group-paste-ready. (completed 2026-05-08)
- [x] **Phase 5: Competitor Ad Copy and LP Extraction** — Per-cluster Serper requery for ad block (domain-deduped, affiliate-filtered) plus Tavily LP value-prop extraction for top advertisers. (completed 2026-05-08)
- [x] **Phase 6: Negatives, Report Assembly, and Persistence** — Tiered negatives (Strong / Considered / Investigate), four-section markdown report, JSON twin, run history index, raw API persistence. (completed 2026-05-08)

## Phase Details

### Phase 1: Skill Scaffold and Brief Intake
**Goal:** Operator can launch the skill in Claude Code, fill a conversational brief, and have a sealed run folder with a saved `brief.md` ready for paid API calls.
**Depends on:** Nothing (first phase)
**Requirements:** SCFD-01, SCFD-02, SCFD-03, SCFD-04, SCFD-05, INTK-01, INTK-02, INTK-03, INTK-04
**Success Criteria** (what must be TRUE):
  1. Operator can trigger the skill via Claude Code's skill discovery and is prompted for a brief; no SKILL.md edit needed.
  2. Operator pastes a free-form brief; the skill loops on missing required fields (industry, product, location, language, audience) and refuses to advance until all five are non-empty.
  3. The skill solicits optional fields (budget, geo/language exclusions, brand terms, competitor URLs) only when relevant, never burying mandatory intake in noise.
  4. After intake, a dated run folder `.runs/<ISO-timestamp>-<slug>/` exists on disk containing the verbatim `brief.md` plus an empty `raw/` subfolder, before any paid API call has fired.
  5. `uv run` invocations of helper scripts succeed with PEP 723 metadata; secrets load only from `.env` (never CLI args), and `.env.example` is committed while `.env` is git-ignored.
**Plans:** 6/6 plans complete
- [x] 01-00-PLAN.md — Wave 0: pytest scaffolding (test stubs for lib/ and run_init.py, RED state)
- [x] 01-01-PLAN.md — Wave 1: scripts/lib/ package (config.py, io.py, log.py — env + slug + timestamp + folder primitives)
- [x] 01-02-PLAN.md — Wave 1: root CLAUDE.md + .gitignore/.env.example secrets-contract audit (parallel with 01-01)
- [x] 01-03-PLAN.md — Wave 2: run_init.py with PEP 723 metadata (sealed run folder + verbatim brief.md)
- [ ] 01-04-PLAN.md — Wave 3: SKILL.md (frontmatter + 5-step intake workflow with per-step gates)
- [ ] 01-05-PLAN.md — Wave 4: VALIDATION.md sign-off (automated rows + 4 manual smokes; checkpoint plan)

### Phase 2: Signal Collection
**Goal:** All three signal sources (Serper, Tavily, WebSearch) write locale-correct raw JSON to the run folder, and every emitted keyword carries source attribution and a canonicalized form.
**Depends on:** Phase 1 (run folder + brief.md must exist; locale fields must be in brief)
**Requirements:** SIGL-01, SIGL-02, SIGL-03, SIGL-04, SIGL-05, SIGL-06
**Success Criteria** (what must be TRUE):
  1. `serp_fetch.py` produces `raw/serper.json` containing organic results, People Also Ask, related searches, and the ads block — fields preserved verbatim, locale params (`gl`, `hl`) reflecting the brief.
  2. `tavily_extract.py` produces one JSON per competitor domain in `raw/`, capped at 5 competitors × 5 URLs each, using `extract_depth='basic'` — never `tavily_crawl`.
  3. WebSearch is invoked from the skill prompt (not wrapped in a script), and its digested findings land in `raw/websearch-baseline.json` via the Write tool.
  4. Every keyword that survives harvest carries a `sources` array recording which source(s) surfaced it; single-source and multi-source keywords are distinguishable downstream.
  5. Close variants ("grocery delivery" / "groceries delivery" / "grocery deliveries") merge into a single canonical surface form via lemmatized + token-sorted hashing before scoring sees them.
**Plans:** 6/6 plans complete
- [x] 02-00-PLAN.md — Wave 0: test scaffolding (5 RED test files + 3 fixture JSONs + conftest extension)
- [x] 02-01-PLAN.md — Wave 1: lib/http.py (httpx RetryTransport) + lib/canon.py (inflect + token-sort hash)
- [x] 02-02-PLAN.md — Wave 2: serp_fetch.py (Serper REST, locale plumbing, all signal blocks)
- [x] 02-03-PLAN.md — Wave 2: tavily_extract.py (Tavily SDK extract, caps, failed_results persistence)
- [x] 02-04-PLAN.md — Wave 3: merge_signals.py (sources array, variant merge, 6-source taxonomy → keywords.json)
- [x] 02-05-PLAN.md — Wave 4: SKILL.md update (Steps 6-10: seed gen + WebSearch + script invocations + stop)

### Phase 3: Ranking and Scoring
**Goal:** Every harvested keyword has a stable 4-class intent label, a match-type recommendation, and a composite score whose primary signal is source_diversity — locked into the canonical table schema.
**Depends on:** Phase 2 (needs canonicalized keywords with source attribution)
**Requirements:** RANK-01, RANK-02, RANK-03, RANK-04
**Success Criteria** (what must be TRUE):
  1. Each keyword carries one of four intent labels (informational / commercial / transactional / navigational) assigned via a categorical rubric with anchor examples and `temperature=0` — re-running the same brief produces ≥90% intent agreement.
  2. The composite score visibly weighs `source_diversity` as primary (a 4-source keyword outranks a single-source keyword regardless of signal_count); ties break on signal_count then intent weight.
  3. Each keyword has a match-type recommendation (broad / phrase / exact) with a conservative default — phrase by default, exact only for high-confidence transactional or brand terms, broad rare and justified.
  4. The keyword table schema renders the canonical columns `keyword | intent | match_type | theme | signal_count | source_diversity | sources | score` and `signal_count` is never labelled "volume".
**Plans:** 3/3 plans complete
- [ ] 03-00-PLAN.md — Wave 0: RED test stubs (test_rank_keywords.py, 16 tests) + keywords_phase2.json + intent_labels.json fixtures
- [ ] 03-01-PLAN.md — Wave 1: rank_keywords.py (compute_score, build_ranked, validate_labels, CLI → ranked.json)
- [ ] 03-02-PLAN.md — Wave 2: SKILL.md Steps 11-13 (4-class rubric + intent-labels.json write + rank_keywords.py invocation)

### Phase 4: Clustering
**Goal:** Keywords arrive grouped into named, intent-homogeneous clusters of 5-15 members that a PPC manager can paste straight into Google Ads ad groups.
**Depends on:** Phase 3 (intent labels must exist before clustering — intent class is a hard split)
**Requirements:** CLST-01, CLST-02, CLST-03
**Success Criteria** (what must be TRUE):
  1. No cluster contains keywords spanning more than one intent label; the clustering step rejects mixed clusters and re-splits them.
  2. Each cluster contains 5-15 keywords (minimum size 3); over-clustered fragments fold into nearest neighbours, and any cluster exceeding 25 splits.
  3. Cluster names follow the `{theme}_{intent}` pattern (e.g., "same-day-delivery_transactional") — no numeric or abstract names like "Cluster 3" or "Theme A".
**Plans:** 3/3 plans complete
- [x] 04-00-PLAN.md — Wave 0: RED test stubs (9 functions, all skipping) + 4 fixture JSONs (clusters_valid, clusters_mixed_intent, clusters_oversize, ranked_phase3)
- [x] 04-01-PLAN.md — Wave 1: validate_clusters.py (9 invariant checks, PEP 723 stdlib-only, CLI exit 0/1/2/3, all 9 tests GREEN)

### Phase 5: Competitor Ad Copy and LP Extraction
**Goal:** For every cluster, the report carries a slice of real competitor ad copy and landing-page value props from advertisers actually competing in that intent space.
**Depends on:** Phase 4 (per-cluster Serper requery requires clusters to exist)
**Requirements:** COMP-01, COMP-02, COMP-03
**Success Criteria** (what must be TRUE):
  1. Every cluster has at least one Serper requery against representative cluster keywords, harvesting paid headlines and descriptions from the ads block.
  2. Ad copy is deduplicated by advertiser display-URL domain; affiliate / aggregator / voucher domains are filtered out (URLs with `?ref=`, `aff_id`, awin/skimlinks/partnerize patterns).
  3. For the top 3-5 surviving advertisers per cluster, Tavily extracts the landing-page headline, primary CTA, and offer language and persists them per advertiser.
**Plans:** 3/3 plans complete
- [ ] 05-00-PLAN.md — Wave 0: RED test stubs (10 functions, all skipping) + 4 fixture JSONs + competitor_intel.py MODULE_MISSING stub
- [ ] 05-01-PLAN.md — Wave 1: competitor_intel.py full implementation (affiliate filter, domain dedupe, per-cluster Serper requery, Tavily LP extraction caps) — COMP-01, COMP-02
- [ ] 05-02-PLAN.md — Wave 2: SKILL.md Steps 18-20 (invoke competitor_intel.py, LLM extracts headline/CTA/offer from raw_content per advertiser) — COMP-03

### Phase 6: Negatives, Report Assembly, and Persistence
**Goal:** A dated run folder contains a four-section markdown report, a JSON twin with stable schema, raw API responses for traceability, and a browsable index of past runs — operator can read it, paste it, and find it later.
**Depends on:** Phase 5 (negatives dedup against final positive pool; report integrates all upstream stages)
**Requirements:** NEGT-01, NEGT-02, NEGT-03, RPRT-01, RPRT-02, RPRT-03, RPRT-04, RPRT-05, PRST-01, PRST-02
**Success Criteria** (what must be TRUE):
  1. Negatives are split into three tiers (Strong / Considered / Investigate); each negative carries a category tag (jobs-careers / free-DIY-tutorial / used-refurb-wholesale / competitor-brand / wrong-geo / wrong-audience) and a per-keyword justification, and none collide with positive keywords.
  2. `report.md` exists in the run folder containing four sections — ranked keyword table, ad group clusters, competitor ad copy, tiered negatives — plus a "How to read this" section explaining `signal_count` is not search volume.
  3. `report.json` exists alongside `report.md` with the same canonical keyword and cluster keys (stable from v1 so future run-diff works); markdown table cells are sanitized (pipes escaped, smart quotes normalized, newlines stripped).
  4. Each run is a sealed dated folder containing `brief.md`, `report.md`, `report.json`, and a `raw/` subfolder with every per-stage API response — no cross-run mutation.
  5. `.runs/INDEX.md` lists every past run (date, brief slug, status) so the operator can browse historical work without `ls`-ing dated folders.
**Plans:** 6/6 plans complete
- [x] 06-00-PLAN.md — Wave 0: RED test stubs (14 functions) + 2 fixtures + tabulate>=0.9.0 in pyproject.toml
- [x] 06-01-PLAN.md — Wave 1: generate_negatives.py (enum validator + dedup) — NEGT-01, NEGT-02, NEGT-03
- [x] 06-02-PLAN.md — Wave 1: lib/io.py escape_md_cell() — RPRT-04
- [x] 06-03-PLAN.md — Wave 2: render_report.py (report.md + report.json) — RPRT-01, RPRT-02, RPRT-03, RPRT-05, PRST-01
- [x] 06-04-PLAN.md — Wave 2: update_index.py (.runs/INDEX.md append) — PRST-02
- [x] 06-05-PLAN.md — Wave 3: SKILL.md Steps 21-26 (negatives gen → validate → render → index → final STOP)

### Phase 7: Niche Pulse — REMOVED post-v1.3 (2026-05-15)
**Status:** Removed. Code (`pulse_fetch.py`, `pulse_synth.py`), reference (`phase7-niche-pulse.md`), tests, fixtures, report sections deleted from skill. Single-team internal tool; team lives in the urgent-care/PIP niche daily, so trending-news synthesis produced noise on repeated runs. Manual Google News checks faster than running the sidecar. Requirements PULSE-01..12 marked removed in REQUIREMENTS.md.

---

# Milestone v1.1 — Operator-Ready Output

**Started:** 2026-05-14
**Goal:** Turn the report from a data dump into a campaign launch kit — junior PPC managers can move from `report.md` to a live, compliant Google Ads campaign with starter bids, budget bands, a step-by-step checklist, and Editor-importable CSVs.
**Granularity:** standard (2 phases for 23 requirements)
**Coverage:** 23/23 v1.1 requirements mapped (100%)

## v1.1 Phases

- [x] **Phase 9: Campaign Economics and Compliance** — Enrich existing v1.0 artifacts with starter-bid suggestions, per-cluster budget forecast bands, and regulated-vertical compliance flags. All output enriches `ranked-enriched.json`/`clusters.json` and writes new `forecast.json` + `compliance-flags.json` sidecars.
 (completed 2026-05-14)
- [x] **Phase 10: Operator Launch Kit** — Consume the enriched data from Phase 9 to emit Editor-importable CSVs and a bespoke Next-Steps checklist that walks a junior PPC manager from `report.md` to a live campaign.
 (completed 2026-05-14)

## v1.1 Phase Details

### Phase 9: Campaign Economics and Compliance
**Goal:** The operator can answer the three economic questions a junior PPC manager asks — "What should I bid?", "How much will it cost?", "Is this vertical regulated?" — directly from the report, with values baked into the JSON artifacts so downstream tooling can consume them.
**Depends on:** Phase 8 (needs `ranked-enriched.json` with Ahrefs `cpc_micros`; needs `clusters.json` for per-cluster aggregation; needs `brief.md` for compliance keyword matching).
**Requirements:** BIDS-01, BIDS-02, BIDS-03, BIDS-04, FRCS-01, FRCS-02, FRCS-03, FRCS-04, FRCS-05, CMPL-01, CMPL-02, CMPL-03, CMPL-04, CMPL-05
**Success Criteria** (what must be TRUE):
  1. The operator opens `report.md` and sees a `Suggested Max CPC` (USD with cents) on every keyword row; keywords with no Ahrefs CPC data fall back to cluster-median × intent multiplier and are flagged `no_cpc_data` so the operator knows the value is imputed.
  2. The operator opens the new "Budget Forecast" section in `report.md` and reads per-cluster + campaign-level daily click bands (low/mid/high) and daily spend bands, plus a "How this is calculated" subsection that names the CTR and avg-CPC assumptions so the operator does not over-promise to a client.
  3. When the brief or top keywords match a regulated vertical (medical, legal, finance, gambling, crypto), a "⚠ Compliance Required" warning block renders above the Ranked Keywords table naming the matched vertical, the evidence tokens, and a verification-path URL — invisible on non-regulated runs.
  4. The bid multipliers live in a single config block (one place to tune transactional/commercial/informational/navigational ratios) and the compliance token lists live in `references/compliance-verticals.json` (data, not code) so the operator can extend either without editing Python.
  5. The downstream JSON contract is stable: `ranked-enriched.json` gains a `suggested_max_cpc_micros` field, a new `forecast.json` sidecar carries per-cluster + campaign-level click/spend bands, and a new `compliance-flags.json` sidecar lists matched verticals; `report.json` gains a `compliance[]` array.
**Plans:** 6/6 plans complete
- [x] 09-00-PLAN.md — Wave 0: test scaffolding (3 RED test files + 6 fixtures + compliance-verticals.json reference data)
- [x] 09-01-PLAN.md — Wave 1: bid_suggest.py (BIDS-01, BIDS-02, BIDS-04 — Suggested Max CPC + cluster-median fallback + INTENT_MULTIPLIERS config block)
- [x] 09-02-PLAN.md — Wave 1: forecast_budget.py (FRCS-01, FRCS-02, FRCS-03, FRCS-05 — per-cluster + campaign-level click/spend bands + methodology block)
- [x] 09-03-PLAN.md — Wave 1: compliance_check.py (CMPL-01, CMPL-02 — token scan + compliance-flags.json sidecar)
- [x] 09-04-PLAN.md — Wave 2: render_report.py extension (BIDS-03 column + FRCS-04 section + CMPL-03 warning block + CMPL-04 report.json keys)
- [x] 09-05-PLAN.md — Wave 3: SKILL.md pointer + references/phase9-economics-compliance.md (Steps 36-40 rubric + human-verify smoke)

### Phase 10: Operator Launch Kit
**Goal:** A junior PPC manager finishing `report.md` has three CSVs to paste into Google Ads Editor and an ordered, run-specific checklist that names the campaign location, budget, ad groups, compliance verification (if any), and step order — zero hand-copying, zero boilerplate.
**Depends on:** Phase 9 (CSV Max-CPC column comes from `suggested_max_cpc_micros`; Next-Steps "set daily budget to <mid forecast>" reads `forecast.json`; checklist reorders compliance-first when `compliance-flags.json` is non-empty).
**Requirements:** EXPT-01, EXPT-02, EXPT-03, EXPT-04, EXPT-05, STEP-01, STEP-02, STEP-03, STEP-04, CMPL-05
**Success Criteria** (what must be TRUE):
  1. The operator finds three Editor-importable CSVs under `{run_dir}/export/` — `positives.csv`, `negatives.csv`, `ad_groups.csv` — that import cleanly into Google Ads Editor v2.x without column-mapping errors (UTF-8 no BOM, CRLF line endings, exact header match, `csv.DictReader` round-trip passes).
  2. The negatives CSV correctly assigns Strong-tier negatives to campaign level and Considered/Investigate to ad-group level, so a single Editor paste lands them at the correct scope — no manual re-bucketing needed.
  3. `report.md` ends with a "Next Steps" section containing an ordered 8-step ops checklist whose values (location, language, audience, daily-budget mid-forecast number, ad-group names from clusters) are substituted from the brief and Phase 9 forecast — each run reads as bespoke instructions, never as boilerplate.
  4. When `compliance-flags.json` is non-empty, the Next-Steps checklist promotes "Complete <vertical> verification at <URL> before launching" from step 8 to step 1 and renumbers the remaining steps, so the operator cannot accidentally launch ahead of regulated-vertical verification.
  5. The HTML report renders the checklist with copy-able command snippets and localStorage-backed checkboxes so the operator can track per-session progress; `report.json` carries the ordered list as a `next_steps[]` array and the CSV file paths as an `exports[]` array for downstream tooling.
**Plans:** 5/5 plans complete
- [x] 10-00-PLAN.md — Wave 0: test scaffolding (test_export_csv.py + test_render_report.py extension + 11 fixtures including 3 byte-exact golden CSVs + export_csv.py MODULE_MISSING stub) — completed 2026-05-14
- [ ] 10-01-PLAN.md — Wave 1: export_csv.py (EXPT-01..04 — single script writing positives.csv + negatives.csv + ad_groups.csv with UTF-8 no-BOM + CRLF byte contract)
- [ ] 10-02-PLAN.md — Wave 1: render_report.py Next Steps section + report.json next_steps[] + HTML checkbox state (STEP-01..04 + CMPL-05)
- [ ] 10-03-PLAN.md — Wave 2: render_report.py Export Files section + report.json exports[] (EXPT-05) + E2E integration test
- [ ] 10-04-PLAN.md — Wave 3: SKILL.md pointer + references/phase10-operator-launch-kit.md + human-verify Editor import smoke

---

## Milestone v1.2: Account-Structure Mapping

**Started:** 2026-05-14
**Goal:** Skill output respects the client's existing Google Ads account.
**Granularity:** standard (1 phase for 11 requirements)
**Coverage:** 11/11 v1.2 requirements mapped (100%)

### Phase 11: Account-Structure Mapping
**Status:** Complete (shipped 2026-05-15)
**Goal:** Skill output respects the client's existing Google Ads account. Brief narrows research to specific counties/cities via optional `geo_focus` field; out-of-scope city tokens drop from the keyword pool; `ad_group_match.py` maps our ranked keywords to existing account ad groups (Phase 8 perf data), and `export_csv.py` writes existing ad group names when matched, preserving the client's structure.
**Depends on:** Phase 10 (export_csv.py — extends with mapping read), Phase 8 (raw/google-ads-perf.json), Phase 9 (suggested_max_cpc_micros — unchanged), Phase 1-2 (brief intake + serp_fetch — extends with geo_focus).
**Requirements:** GEO-01, GEO-02, GEO-03, GEO-04, GEO-05, ADGM-01, ADGM-02, ADGM-03, ADGM-04, ADGM-05, ADGM-06
**Success Criteria** (what must be TRUE):
  1. The operator passes a brief with optional `geo_focus: ["Palm Beach County", "Lake Worth"]` (or skips the field for backward compat); `serp_fetch.py` includes the geo tokens in query strings to bias SERP locality.
  2. `merge_signals.py` drops keywords containing US-city tokens NOT in `geo_focus` within the same state, scoped via `references/us-cities.json` data file — Lake Worth FL run no longer surfaces "Tampa" or "Jacksonville" results.
  3. `ad_group_match.py` reads `raw/google-ads-perf.json` + `raw/google-ads-search-terms.json` and emits `ad-group-mapping.json` with per-keyword `{existing_ad_group, confidence}` tier (high/medium/low).
  4. When mapping covers >50% of keywords, `export_csv.py` writes existing ad group names in the `Ad Group` column for matched rows; ad_groups.csv lists only NEW ad groups (preserves existing names, no Editor duplicate-name errors).
  5. Report Next Steps section conditionally rewrites step 3 to "Add keywords to existing ad groups: <names>" instead of "Create ad groups: <new names>" when mapping coverage > 50%.
**Plans:** 5/5 plans complete
- [x] 11-00-PLAN.md — Wave 0: test scaffolding (test_geo_filter.py + test_ad_group_match.py + 5 extended test files + 7 fixtures + ad_group_match.py MODULE_INCOMPLETE stub)
- [x] 11-01-PLAN.md — Wave 1: geo plumbing (us-cities.json data + run_init geo_focus helper + serp_fetch --geo-focus + merge_signals city filter)
- [x] 11-02-PLAN.md — Wave 1: ad_group_match.py full implementation (build_mapping + Jaccard × intent match + confidence tiers + sidecar + graceful Phase-8-absent skip)
- [x] 11-03-PLAN.md — Wave 2: integrations (export_csv mapping-aware + render_report Geographic Focus + Next Steps step-3 rewrite)
- [x] 11-04-PLAN.md — Wave 3: SKILL.md pointer + references/phase11-account-structure-mapping.md + human-verify e2e smoke

---

## Milestone v1.3: Source Consolidation

### Phase 12: Source Consolidation (Drop Tavily)
**Goal:** Drop Tavily entirely. Replace Phase 5 COMP-03 landing-page extraction with Claude's built-in WebFetch (mirrors WebSearch baseline pattern). Drop redundant Phase 7 Tavily news call (Serper /news covers it). Reduce paid API surface from {Serper, Tavily, Ahrefs, Google Ads} to {Serper, Ahrefs, Google Ads}.
**Depends on:** Phase 5 (competitor_intel.py extension), Phase 7 (pulse_fetch.py extension). All other phases unaffected.
**Requirements:** TVLY-01, TVLY-02, TVLY-03, TVLY-04, WFCH-01, WFCH-02, WFCH-03, WFCH-04, PULSE-10, PULSE-11, PULSE-12
**Success Criteria** (what must be TRUE):
  1. `scripts/tavily_extract.py` deleted; `tavily-python` removed from pyproject.toml; `TAVILY_API_KEY` stripped from `.env.example` + `lib/config.py`; project still runs end-to-end on a brief.
  2. SKILL.md Phase 5 instructs Claude to WebFetch top 3-5 advertiser landing pages per cluster and write `{headline, cta, offer}` to `raw/competitor-landing-pages.json` via Write tool (no helper script).
  3. `competitor_intel.py` keeps Serper requery for ads block + Serper-organic fallback for advertiser identity; Tavily code path deleted.
  4. `pulse_fetch.py` removes `_tavily_news` call; only Serper `/news` survives; `pulse_synth.py` simplified to single-source.
  5. Full test suite passes after removal (target: 252+ tests, with test_tavily_extract.py deleted and Phase 5/7 tests adapted to new contract).
**Status:** Complete (shipped 2026-05-15)
**Plans:** 6/6 plans complete
- [x] 12-00-PLAN.md — Wave 0: RED test scaffolding (test_audit_tavily_removed.py + test_pulse_fetch.py + extensions to test_pulse_synth/test_merge_signals/test_competitor_intel/test_render_report + 2 fixture JSONs)
- [x] 12-01-PLAN.md — Wave 1: pure deletion (TVLY-01..04 — tavily_extract.py + test_tavily_extract.py + tavily fixtures + conftest tavily_fixture + .env.example + lib/config.py + pyproject.toml)
- [x] 12-02-PLAN.md — Wave 1: competitor_intel.py + merge_signals.py refactor (WFCH-03, WFCH-04 — Serper-only advertisers shape + 5-source VALID_SOURCES)
- [x] 12-03-PLAN.md — Wave 1: pulse_fetch.py + pulse_synth.py single-source (PULSE-10, PULSE-11)
- [x] 12-04-PLAN.md — Wave 2: SKILL.md WebFetch + references docs rewrite + render_report.py JOIN (WFCH-01, WFCH-02, PULSE-12)
- [x] 12-05-PLAN.md — Wave 3: full suite + e2e human-verify smoke + REQUIREMENTS.md/STATE.md milestone closeout

### Phase 13: Landing-Page Extract Vendor Swap (BACKLOG — defer-until-friction)
**Goal:** If WebFetch flow in Phase 12 proves disruptive in real-operator runs (per-domain permission prompts, reliability issues, parsing friction), migrate landing-page extract from Claude WebFetch → Serper `/scrape` helper script. Vendor consolidation onto existing Serper account, eliminates Claude prompts, restores helper-script + respx-mockable pattern.
**Trigger:** Operator runs 1-2 real briefs in Phase 12 mode. If WebFetch flow is fine → skip Phase 13 entirely. If friction observed → activate.
**Depends on:** Phase 12 shipped.
**Requirements:** TBD (write `serper_scrape.py` helper; rewrite SKILL.md Step 19 from "Claude WebFetch" → "run `serper_scrape.py`"; preserve `raw/competitor-landing-pages.json` schema + render_report JOIN; add respx tests).
**Success Criteria** (when activated):
  1. `scripts/serper_scrape.py` exists, uses existing `lib/http.py` + `SerperClient` pattern; calls Serper `/scrape` endpoint.
  2. SKILL.md Step 19 invokes helper script (no Claude WebFetch); no per-domain permission prompts.
  3. `raw/competitor-landing-pages.json` schema unchanged; `render_report.py` JOIN unchanged.
  4. respx-mocked tests cover happy path + retry + 4xx fallback.
  5. Full test suite passes; e2e smoke produces equivalent report.md competitor section quality.
**Plans:** TBD — defer until trigger condition met.

---

## Milestone v1.4: Positives Sync

**Started:** 2026-05-15
**Goal:** Mirror negatives-sync UX for positives — diff ranked keywords against the client's currently-active Google Ads keywords and surface only net-new in `positives.csv`. Eliminates the manual dedup pain operators hit on skill re-runs against the same account.
**Granularity:** standard (1 phase for 7 requirements)
**Coverage:** 7/7 v1.4 requirements mapped (100%)

### Phase 14: Positives Sync
**Goal:** Operator re-running the skill against a client whose Google Ads OAuth is already wired (Phase 8) sees a Positives Sync section in `report.md` + `report.html` with 4 buckets (`already_active` / `paused_in_account` / `covered_by_broad` / `new_to_add`) and an Editor-ready `positives.csv` that defaults to only the net-new keywords — no manual scrub needed before paste. Same skill on an account without OAuth degrades gracefully (sync section omitted, CSV falls back to full ranked list).
**Depends on:** Phase 8 (existing Google Ads OAuth wiring + `perf_fetch.py` foundation), Phase 6 (`render_report.py` section composition), Phase 10 (`export_csv.py` extension surface). No new external APIs — reuses free Google Ads API quota.
**Requirements:** POS-01, POS-02, POS-03, POS-04, POS-05, POS-06, POS-07
**Success Criteria** (what must be TRUE):
  1. Operator re-runs the skill on a client whose Google Ads account is already OAuth-wired (Phase 8); `positives.csv` contains only `new_to_add` rows by default — no manual dedup against the live account needed before Editor paste.
  2. Operator passes `--include-existing` to `export_csv.py` and the full ranked list (all 4 buckets) lands in `positives.csv` — backward-compatible escape hatch for the v1.0 / pre-Phase-8 workflow.
  3. Operator runs the skill on an account without Google Ads OAuth (`raw/google-ads-keywords.json` absent); Phase 14 graceful-skips with no errors — Positives Sync section omitted from the report and `positives.csv` falls back to the full ranked list.
  4. Operator opens `report.md` and `report.html` and sees a `## Positives Sync` section that mirrors the existing negatives-sync UX: stats line (our_total / already_active / paused_in_account / covered_by_broad / new_to_add) above an enumerated `new_to_add` list (with category + justification per row) and collapsible / count-only views for the other 3 buckets.
  5. Borderline semantic-dupe keywords (e.g. `urgent care lake worth` ranked vs `lake worth urgent care` active in account, or ranked-exact `auto accident doctor` covered by account-broad `accident doctor`) get re-tagged from `new_to_add` → `already_active` (or `covered_by_broad`) by the SKILL.md LLM re-tag step after script dedup — script + LLM tandem catches both string-norm hits and the ~20% of cases plain hashing misses.
**Plans:** 6/6 plans complete
- [x] 14-00-PLAN.md — Wave 1: RED test scaffolding (test_perf_synth + test_perf_fetch + test_render_report + test_export_csv extensions + 4 fixtures including golden_positives_sync.json + golden_positives_new_to_add.csv) — POS-07
- [ ] 14-01-PLAN.md — Wave 2: perf_fetch.py fetch_keyword_view + raw/google-ads-keywords.json writer — POS-01
- [ ] 14-02-PLAN.md — Wave 3: perf_synth.py cross_ref_positives + positives-sync.json 4-bucket writer + graceful skip — POS-02, POS-05, POS-07
- [ ] 14-03-PLAN.md — Wave 4: render_report.py render_positives_sync_section (md + HTML + JSON twin) — POS-03, POS-05
- [ ] 14-04-PLAN.md — Wave 4: export_csv.py positives-sync filter + --include-existing flag — POS-04, POS-05
- [ ] 14-05-PLAN.md — Wave 5: SKILL.md Step 34a pointer + references/phase8-account-data.md LLM re-tag rubric + end-to-end human-verify — POS-06

---

## Milestone v1.5: Account-Aware Narrowing

**Started:** 2026-05-15
**Goal:** Narrow skill output from OAuth-account scope to the operator's actual target campaign + the AGs inside it. Mirrors v1.2's `geo_focus` architectural pattern at the campaign + AG-criterion level. Two related contamination issues from Lake Worth dogfood fixed: (1) Phase 8 GAQL pulls all 30+ campaigns when brief targets one → Positives/Negatives Sync + AG Mapping show irrelevant data; (2) AG Mapping Jaccard uses AG name only (~4 tokens) vs ranked kw (long phrases) → 0% coverage. No new external APIs — reuses existing Google Ads OAuth + Phase 14 raw data.
**Granularity:** standard (2 phases for 11 requirements)
**Coverage:** 11/11 v1.5 requirements mapped (100%)

### Phase 15: Campaign Focus
**Goal:** Operator declares an optional `campaign_focus` in brief.md; `perf_fetch.py` adds `AND campaign.name = '<focus>'` to all 4 GAQL queries so every Phase 8 raw artifact, plus the downstream Positives Sync, Negatives Sync, and Ad Group Mapping that consume them, narrows to the single target campaign without per-script wiring. Omitting `campaign_focus` preserves current v1.4 account-wide behavior.
**Depends on:** Phase 14 (extends `perf_fetch.py` 4-query surface including `keyword_view`), Phase 11 (mirrors `geo_focus` brief-parsing + report-callout pattern), Phase 8 (Google Ads OAuth wiring).
**Requirements:** CAMP-01, CAMP-02, CAMP-03, CAMP-04, CAMP-05, CAMP-06
**Success Criteria** (what must be TRUE):
  1. Operator includes `Campaign focus: Search | Lake Worth Accident Exams | Manual CPC` in `brief.md`; `raw/google-ads-keywords.json` + `raw/google-ads-perf.json` + `raw/google-ads-search-terms.json` + `raw/google-ads-negatives.json` contain only that campaign's data — no Palm Springs / FL PIP / Hybrid noise.
  2. Positives Sync stats and Negatives Sync stats accurately reflect the narrowed campaign — no contamination from keywords or negatives running in unrelated campaigns inflating the `already_active` / `already_in_account` buckets.
  3. Ad Group Mapping section shows only the ad groups inside the focused campaign (e.g. the 3 AGs under "Lake Worth Accident Exams") instead of all 35 account-wide ad groups.
  4. Operator omits `campaign_focus` from `brief.md` → skill runs account-wide unchanged (current v1.4 behavior preserved end-to-end; backward compat verified by re-running an existing pre-v1.5 brief).
  5. Operator types a `campaign_focus` value that does not match any campaign name in `raw/google-ads-perf.json` → `render_report.py` emits a warning callout in the report header before downstream sections render against the (empty) narrowed result.
**Plans:** 4/4 plans complete
- [x] 15-00-PLAN.md — Wave 1: RED test scaffolding (test_perf_fetch + test_render_report + brief_with_campaign_focus.md + google-ads-perf-with-campaign.json fixtures) — CAMP-06
- [ ] 15-01-PLAN.md — Wave 2: perf_fetch.py --campaign-filter CLI + thread through 4 GAQL queries + SQL-quote escape — CAMP-02
- [ ] 15-02-PLAN.md — Wave 2: render_report.py _parse_brief_fields campaign_focus + render_campaign_focus_section + name validation + report.json key — CAMP-01, CAMP-05
- [ ] 15-03-PLAN.md — Wave 3: SKILL.md Step 3/4 wiring + references/phase8-account-data.md Step 33 + end-to-end Lake Worth smoke — CAMP-03, CAMP-04

### Phase 16: Ad Group Mapping Token-Bag Enrichment
**Goal:** `ad_group_match.py` Jaccard scoring uses an enriched per-AG token bag (AG name ∪ active kw_criteria tokens ∪ top-N search-term tokens) instead of the current search-terms-only bag, lifting high+medium mapping coverage from 0% to 50%+ on real client accounts whose AG names are short labels. When Phase 14 `raw/google-ads-keywords.json` is absent, falls back silently to the current search-terms-only Jaccard plus AG name addition (AG name ∪ search-terms — backward compat for pre-Phase-14 accounts, with the AG-name token contribution as the only Phase 16 delta vs Phase 11 in that fallback path).
**Depends on:** Phase 15 (calibrates against the narrowed dataset Phase 15 produces — running token-bag enrichment against the full-account dataset gives noisier threshold calibration), Phase 14 (consumes `raw/google-ads-keywords.json` for AG kw-criteria evidence), Phase 11 (extends existing `ad_group_match.py` algorithm + threshold config).
**Requirements:** ADGM-07, ADGM-08, ADGM-09, ADGM-10, ADGM-11
**Success Criteria** (what must be TRUE):
  1. Operator runs the skill on a real account (Lake Worth-shape: short AG names, deep kw_criteria) that previously showed 0% high+medium coverage in Phase 11; post-Phase-16 mapping shows ≥50% high+medium coverage when Phase 14 + Phase 15 raw data is present.
  2. Operator runs the skill on an account without Phase 14 OAuth (`raw/google-ads-keywords.json` absent) → current name-only Jaccard behavior preserved with no errors; mapping section renders as it did in pre-Phase-14 Phase 11 runs.
  3. Each match entry in `ad-group-mapping.json` carries a `reason` field naming which evidence source(s) contributed (e.g. `"jaccard=0.32 on kw-criterion bag, name overlap 0"`) so operator can audit any auto-routing decision.
  4. Recalibrated thresholds (likely tighter, e.g. 0.5 high / 0.25 medium vs current 0.7 / 0.4) are documented in `references/phase11-account-structure-mapping.md` with empirical rationale from at least 2 real-account calibration runs.
  5. Operator pastes new ranked keywords into Google Ads Editor and lands them in the right existing ad groups (high+medium tier) without re-thinking account structure — the original v1.2 promise of "respect client's existing AG structure" finally lands operationally on short-name-AG accounts.
**Status:** Complete (shipped 2026-05-15 — ADGM-07..10 done via Plans 16-00..02; ADGM-11 >=50% floor deferred to structural-algorithm follow-up plan tracked in STATE.md open questions)
**Plans:** 4/6 plans executed
- [x] 16-00-PLAN.md — Wave 1: Lake Worth golden fixtures + 5 RED tests + PHASE16_INCOMPLETE guard
- [x] 16-01-PLAN.md — Wave 2: `_build_ag_token_bag` + keywords-aware index + per-source reason field + `_THRESHOLDS` recalibrated to {0.30, 0.10} (option-a deferral applied) — ADGM-07, ADGM-08, ADGM-09
- [x] 16-02-PLAN.md — Wave 3: reference-doc Phase 16 section (+78 lines; SKILL.md untouched at 497/500) + live Lake Worth OAuth e2e closeout (16.42% observed vs 16.67% offline — within 0.25pp predictive validity) — ADGM-10


## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Skill Scaffold and Brief Intake | 6/6 | Complete    | 2026-05-08 |
| 2. Signal Collection | 6/6 | Complete    | 2026-05-08 |
| 3. Ranking and Scoring | 3/3 | Complete    | 2026-05-08 |
| 4. Clustering | 3/3 | Complete    | 2026-05-08 |
| 5. Competitor Ad Copy and LP Extraction | 3/3 | Complete    | 2026-05-08 |
| 6. Negatives, Report Assembly, and Persistence | 6/6 | Complete    | 2026-05-08 |
| 7. Niche Pulse | — | Removed post-v1.3 | 2026-05-15 |
| 8. Account Data + Volume Enrichment | 8/8 | Complete    | 2026-05-08 |
| 9. Campaign Economics and Compliance | 6/6 | Complete    | 2026-05-14 |
| 10. Operator Launch Kit | 5/5 | Complete    | 2026-05-14 |
| 11. Account-Structure Mapping | 5/5 | Complete    | 2026-05-14 |
| 12. Source Consolidation (Drop Tavily) | 6/6 | Complete    | 2026-05-15 |
| 13. Landing-Page Extract Vendor Swap | 0/0 | Backlog (defer-until-friction) | — |
| 14. Positives Sync | 6/6 | Complete    | 2026-05-15 |
| 15. Campaign Focus | 4/4 | Complete    | 2026-05-15 |
| 16. Ad Group Mapping Token-Bag Enrichment | 4/6 | In Progress|  |

## Coverage Map

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1 | SCFD-01, SCFD-02, SCFD-03, SCFD-04, SCFD-05, INTK-01, INTK-02, INTK-03, INTK-04 | 9 |
| 2 | SIGL-01, SIGL-02, SIGL-03, SIGL-04, SIGL-05, SIGL-06 | 6 |
| 3 | RANK-01, RANK-02, RANK-03, RANK-04 | 4 |
| 4 | CLST-01, CLST-02, CLST-03 | 3 |
| 5 | COMP-01, COMP-02, COMP-03 | 3 |
| 6 | NEGT-01, NEGT-02, NEGT-03, RPRT-01, RPRT-02, RPRT-03, RPRT-04, RPRT-05, PRST-01, PRST-02 | 10 |
| 7 | _removed post-v1.3 (PULSE-01..09 dropped)_ | 0 |
| 9 | BIDS-01, BIDS-02, BIDS-03, BIDS-04, FRCS-01, FRCS-02, FRCS-03, FRCS-04, FRCS-05, CMPL-01, CMPL-02, CMPL-03, CMPL-04, CMPL-05 | 14 |
| 10 | EXPT-01, EXPT-02, EXPT-03, EXPT-04, EXPT-05, STEP-01, STEP-02, STEP-03, STEP-04 | 9 |
| 11 | GEO-01, GEO-02, GEO-03, GEO-04, GEO-05, ADGM-01, ADGM-02, ADGM-03, ADGM-04, ADGM-05, ADGM-06 | 11 |
| 12 | TVLY-01..04, WFCH-01..04 (PULSE-10..12 removed with Phase 7) | 8 |
| 14 | POS-01, POS-02, POS-03, POS-04, POS-05, POS-06, POS-07 | 7 |
| 15 | CAMP-01, CAMP-02, CAMP-03, CAMP-04, CAMP-05, CAMP-06 | 6 |
| 16 | ADGM-07, ADGM-08, ADGM-09, ADGM-10, ADGM-11 | 5 |
| **Total** | | **95 / 95** (Phase 7 PULSE-01..09 + Phase 12 PULSE-10..12 removed post-v1.3) |

No orphans. No duplicates. Every v1.0 + v1.1 + v1.2 + v1.3 + v1.4 + v1.5 requirement maps to exactly one phase.

## Phase Ordering Rationale

- **Scaffold before signals:** key leakage and state contamination are unrecoverable from day 1; folder/env contract must exist before any API call fires.
- **Signals before scoring:** source attribution and canonicalization must happen at harvest time — retrofitting variants/sources later corrupts frequency counts permanently.
- **Scoring before clustering:** intent class is a hard prerequisite split for clustering (no intent-mixed ad groups).
- **Clustering before ad copy:** per-cluster Serper requery and per-cluster Tavily LP extraction need clusters to exist as their unit of work.
- **Positives before negatives:** negatives must dedup against the final positive pool; running them earlier produces collisions.
- **Report assembly last (v1.0):** render is the integration test for every upstream stage; markdown sanitization and JSON-twin schema validation depend on all data being final.
- **Economics before launch kit (v1.1):** Phase 10 CSVs need Phase 9's `suggested_max_cpc_micros` for the Max-CPC column; Phase 10 Next-Steps checklist needs Phase 9's mid-forecast spend for the daily-budget step and Phase 9's compliance flags to decide checklist ordering. Splitting data layer from output layer keeps each phase's success criteria observable in isolation.
- **Why not one fat Phase 9?** 23 requirements in one phase produces ~13 plans and a coverage map where success criteria mix data-shape concerns (does `forecast.json` exist?) with output concerns (does CSV import into Editor?). Splitting yields two phases of ~5-7 plans each with crisper success criteria.
- **Positives Sync (v1.4) deferred until after v1.0 ships, not bundled with Phase 8:** the negatives-sync architecture (Phase 8 GADS-04) had to prove out before mirroring it for positives; v1.4 inherits the same OAuth wiring + `perf_synth.py` shape, so the engineering surface is small (~3 scripts touched, no new APIs) and the phase stays single — coverage of POS-01..07 in one delivery boundary keeps success criteria observable end-to-end.
- **Phase 15 before Phase 16 (v1.5):** Phase 16 token-bag enrichment must calibrate against the narrowed dataset Phase 15 produces. Running enrichment against the full-account dataset yields noisier thresholds (denominators inflated by AGs that aren't even in scope), and the operator-visible payoff — 50%+ coverage on the target campaign — is only verifiable end-to-end once Phase 15 has already filtered the comparison surface.

---
*Roadmap created: 2026-05-08*
*Phase 1 plans drafted: 2026-05-08*
*Phase 2 plans drafted: 2026-05-08*
*Phase 3 plans drafted: 2026-05-08*
*Phase 5 plans drafted: 2026-05-08*
*Phase 6 plans drafted: 2026-05-08*
*v1.1 milestone phases (9-10) added: 2026-05-14*
*v1.2 milestone phase 11 shipped: 2026-05-15*
*v1.3 milestone phase 12 shipped: 2026-05-15 — Tavily dropped; WebFetch replaces COMP-03; Serper /news single-source niche pulse. 89/89 requirements Complete.*
*v1.4 milestone phase 14 added: 2026-05-15 — Positives Sync (POS-01..07) pending; 96 total v1 requirements (89 Complete + 7 Pending).*
*v1.5 milestone phases 15 + 16 added: 2026-05-15 — Account-Aware Narrowing (CAMP-01..06 + ADGM-07..11) pending; 107 total v1 requirements (96 Complete + 11 Pending).*
