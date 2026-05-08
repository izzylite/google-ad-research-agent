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
- [ ] **Phase 5: Competitor Ad Copy and LP Extraction** — Per-cluster Serper requery for ad block (domain-deduped, affiliate-filtered) plus Tavily LP value-prop extraction for top advertisers.
- [ ] **Phase 6: Negatives, Report Assembly, and Persistence** — Tiered negatives (Strong / Considered / Investigate), four-section markdown report, JSON twin, run history index, raw API persistence.

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
**Plans:** 2/3 plans executed
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
**Plans:** TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Skill Scaffold and Brief Intake | 6/6 | Complete    | 2026-05-08 |
| 2. Signal Collection | 6/6 | Complete    | 2026-05-08 |
| 3. Ranking and Scoring | 3/3 | Complete    | 2026-05-08 |
| 4. Clustering | 3/3 | Complete    | 2026-05-08 |
| 5. Competitor Ad Copy and LP Extraction | 2/3 | In Progress|  |
| 6. Negatives, Report Assembly, and Persistence | 0/0 | Not started | - |

## Coverage Map

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1 | SCFD-01, SCFD-02, SCFD-03, SCFD-04, SCFD-05, INTK-01, INTK-02, INTK-03, INTK-04 | 9 |
| 2 | SIGL-01, SIGL-02, SIGL-03, SIGL-04, SIGL-05, SIGL-06 | 6 |
| 3 | RANK-01, RANK-02, RANK-03, RANK-04 | 4 |
| 4 | CLST-01, CLST-02, CLST-03 | 3 |
| 5 | COMP-01, COMP-02, COMP-03 | 3 |
| 6 | NEGT-01, NEGT-02, NEGT-03, RPRT-01, RPRT-02, RPRT-03, RPRT-04, RPRT-05, PRST-01, PRST-02 | 10 |
| **Total** | | **35 / 35** |

No orphans. No duplicates. Every v1 requirement maps to exactly one phase.

## Phase Ordering Rationale

- **Scaffold before signals:** key leakage and state contamination are unrecoverable from day 1; folder/env contract must exist before any API call fires.
- **Signals before scoring:** source attribution and canonicalization must happen at harvest time — retrofitting variants/sources later corrupts frequency counts permanently.
- **Scoring before clustering:** intent class is a hard prerequisite split for clustering (no intent-mixed ad groups).
- **Clustering before ad copy:** per-cluster Serper requery and per-cluster Tavily LP extraction need clusters to exist as their unit of work.
- **Positives before negatives:** negatives must dedup against the final positive pool; running them earlier produces collisions.
- **Report assembly last:** render is the integration test for every upstream stage; markdown sanitization and JSON-twin schema validation depend on all data being final.

---
*Roadmap created: 2026-05-08*
*Phase 1 plans drafted: 2026-05-08*
*Phase 2 plans drafted: 2026-05-08*
*Phase 3 plans drafted: 2026-05-08*
*Phase 5 plans drafted: 2026-05-08*
