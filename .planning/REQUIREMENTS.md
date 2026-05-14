# Requirements: Google Ad Research Agent

**Defined:** 2026-05-08
**Core Value:** From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Scaffold

- [x] **SCFD-01**: Skill installed at `.claude/skills/google-ad-research/` with `SKILL.md` and `scripts/` subfolder
- [x] **SCFD-02**: Python helper scripts run via `uv run` with PEP 723 inline dependency metadata
- [x] **SCFD-03**: API keys (Serper, Tavily) loaded from `.env` via python-dotenv; `.env` git-ignored, `.env.example` committed
- [x] **SCFD-04**: `scripts/lib/` package provides shared HTTP client (httpx + retry), config loader, IO helpers, structured logging
- [x] **SCFD-05**: `run_init.py` creates dated run folder `.runs/<ISO-timestamp>-<slug>/` containing `brief.md`, `raw/` subfolder

### Brief Intake

- [x] **INTK-01**: Skill prompts operator for campaign brief in chat; operator pastes free-form context
- [x] **INTK-02**: Skill validates 5 required fields (industry, product, location, language, audience); loops until all non-empty
- [x] **INTK-03**: Skill solicits optional fields (budget signal, geo exclusions, language exclusions, brand terms, competitor URLs) when relevant
- [x] **INTK-04**: Validated brief saved verbatim to `brief.md` in run folder before any paid API call

### Signal Collection

- [x] **SIGL-01**: `serp_fetch.py` calls Serper.dev REST and persists organic + PAA + related + ads block to `raw/serper.json`
- [x] **SIGL-02**: `tavily_extract.py` runs Tavily extract on competitor URL list (max 5 competitors, 5 URLs each, `extract_depth='basic'`); per-domain JSON written
- [x] **SIGL-03**: WebSearch tool invoked from skill prompt for free baseline signal
- [x] **SIGL-04**: Locale parameters (`gl`, `hl`, language hints) passed to all sources from brief fields
- [x] **SIGL-05**: Each keyword retains source attribution (which source(s) surfaced it) for downstream ranking
- [x] **SIGL-06**: Keywords lemmatized + canonicalized to merge close variants before scoring

### Ranking

- [x] **RANK-01**: LLM classifies each keyword by 4-class intent (informational / commercial / transactional / navigational) using categorical rubric with anchor examples, temperature=0
- [x] **RANK-02**: Composite ranking uses `signal_count` (occurrences) + `source_diversity` (distinct sources) + intent weight; primary ranking signal is `source_diversity`
- [x] **RANK-03**: Match-type recommendation (broad / phrase / exact) suggested per keyword with conservative defaults (phrase by default; exact for high-confidence transactional/brand; broad rarely)
- [x] **RANK-04**: Ranked keyword table columns: `keyword`, `intent`, `match_type`, `theme`, `signal_count`, `source_diversity`, `sources`, `score`

### Clustering

- [x] **CLST-01**: Keywords cluster within intent class only — no intent-mixed clusters allowed
- [x] **CLST-02**: LLM produces clusters of 5-15 keywords (min size 3) with descriptive names combining theme + intent
- [x] **CLST-03**: Any cluster spanning more than one intent label is rejected and re-split

### Competitor Intel

- [x] **COMP-01**: Per-cluster Serper requery extracts paid ad headlines + descriptions from ads block
- [x] **COMP-02**: Ad copy deduplicated by advertiser domain; affiliate / aggregator domains filtered
- [x] **COMP-03**: Tavily extracts landing-page value props (headline, primary CTA, offer) for top 3-5 advertisers per cluster

### Negatives

- [x] **NEGT-01**: Negatives generated in three tiers — Strong, Considered, Investigate
- [x] **NEGT-02**: Each negative tagged with category (jobs-careers / free-DIY-tutorial / used-refurb-wholesale / competitor-brand / wrong-geo / wrong-audience) and per-keyword justification
- [x] **NEGT-03**: Negatives deduplicated against the final positive keyword pool

### Report Output

- [x] **RPRT-01**: `render_report.py` writes `report.md` to run folder containing four sections — ranked keyword table, ad group clusters, competitor ad copy, tiered negatives
- [x] **RPRT-02**: `report.json` twin written with stable canonical schema (enables future run-diff in v2)
- [x] **RPRT-03**: Report includes "How to read this" section explaining `signal_count` is not search volume and ranking is signal-source-diversity-driven
- [x] **RPRT-04**: Markdown sanitization on all table cells (escape pipes, quotes, newlines)
- [x] **RPRT-05**: All raw per-stage API responses persisted to `raw/` subfolder for traceability

### Persistence

- [x] **PRST-01**: Each run is an isolated dated folder containing `brief.md`, `report.md`, `report.json`, `raw/`
- [x] **PRST-02**: `.runs/INDEX.md` lists past runs (date, brief slug, status) for operator browsing

### Account Data + Volume Enrichment (Phase 8)

- [x] **AHRF-01**: `volume_enrich.py` calls Ahrefs `/v3/keywords-explorer/overview` for all ranked keywords and adds `volume`, `cpc_micros`, `difficulty`, `parent_topic` columns to a new `ranked-enriched.json`
- [x] **AHRF-02**: Ahrefs requests batch keywords (single call per ≤100) to minimize unit cost; failures surface in stderr but don't abort
- [x] **AHRF-03**: HTML + markdown report show enriched columns when present; fall back to source-diversity ranking when absent
- [x] **GADS-01**: `perf_fetch.py` pulls `search_term_view` (last 30 days) via Google Ads API and persists `raw/google-ads-search-terms.json`
- [x] **GADS-02**: `perf_fetch.py` pulls campaign + ad_group performance (cost, clicks, conversions) and persists `raw/google-ads-perf.json`
- [x] **GADS-03**: `perf_fetch.py` pulls existing negative keywords (`campaign_criterion` + `ad_group_criterion`) and persists `raw/google-ads-negatives.json`
- [x] **GADS-04**: `perf_synth.py` cross-references our `negatives.json` against existing account negatives and flags each as `already_in_account` or `new_candidate`
- [x] **GADS-05**: Report includes new sections: Volume-Enriched Keywords (replaces ranked table when enrichment present), Real Search Terms, Account Performance, Negative Sync

### Niche Pulse (Phase 7 — time-sensitive sidecar)

- [x] **PULSE-01**: `pulse_fetch.py` calls Serper `/news` endpoint per seed keyword with `tbs=qdr:w` (last 7 days) and persists `raw/serper-news.json`
- [x] **PULSE-02**: `pulse_fetch.py` calls Tavily `search` with `topic="news"` and `days=7` per seed keyword and persists `raw/tavily-news.json`
- [x] **PULSE-03**: `pulse_synth.py` reads news raws and produces `niche-pulse.json` containing trending themes, regulatory alerts, competitor news, and trending negatives sections
- [x] **PULSE-04**: Trending themes are clustered by repeated phrase/topic across both news sources with `mention_count`, `first_seen`, and `sources[]` attribution
- [x] **PULSE-05**: Regulatory alerts are tagged via keyword heuristics (law/regulation/PIP/HIPAA/compliance/court/ruling/lawsuit terms)
- [x] **PULSE-06**: `render_report.py` adds a Niche Pulse section to `report.md` and `report.html` showing trending themes, regulatory alerts, competitor news, freshness window
- [x] **PULSE-07**: Niche Pulse data is tagged with `horizon_days` and `captured_at` so consumers know shelf life
- [x] **PULSE-08**: SKILL.md Steps 27-30 wire the niche pulse phase as optional (skill prompts operator: run pulse?)
- [x] **PULSE-09**: Niche pulse keywords/themes are NOT merged into the main `keywords.json` ranking (different lifecycle); they live in their own `niche-pulse.json`

## v1.1 Requirements (Operator-Ready Output)

Milestone v1.1 — campaign launch kit additions. Builds on v1.0 artifacts (ranked-enriched.json, clusters.json, negatives.json, report.md).

### Editor CSV Export

- [ ] **EXPT-01**: `export_csv.py` writes `{run_dir}/export/positives.csv` with columns `Campaign, Ad Group, Keyword, Match Type, Max CPC, Final URL` in Google Ads Editor import format (UTF-8, comma-delimited, quoted strings)
- [ ] **EXPT-02**: `export_csv.py` writes `{run_dir}/export/negatives.csv` with columns `Campaign, Ad Group, Keyword, Match Type, Level` (Level = `campaign` | `ad_group`); Strong tier → campaign level, Considered/Investigate → ad_group level
- [ ] **EXPT-03**: `export_csv.py` writes `{run_dir}/export/ad_groups.csv` with columns `Campaign, Ad Group, Status, Default Max CPC` for ad group creation
- [ ] **EXPT-04**: Editor-importable verification — CSV passes `csv.DictReader` round-trip and column headers exactly match Google Ads Editor v2.x spec (no BOM, CRLF line endings)
- [ ] **EXPT-05**: `render_report.py` adds "Export Files" section linking to each CSV; `report.json` lists export file paths in stable `exports[]` array

### Max-CPC Bid Suggestions

- [ ] **BIDS-01**: `bid_suggest.py` (or extension to volume_enrich.py) adds `suggested_max_cpc_micros` column to `ranked-enriched.json` derived from `cpc_micros × intent_multiplier` (transactional 1.2, commercial 0.8, informational 0.4, navigational 1.0)
- [ ] **BIDS-02**: Keywords with no Ahrefs `cpc_micros` data fall back to cluster-median CPC × intent_multiplier; if cluster has no CPC data at all, suggested_max_cpc is `null` and flagged `no_cpc_data` in report
- [ ] **BIDS-03**: Report ranked-enriched table renders `Suggested Max CPC` column (USD with cents); HTML report shows the multiplier in a tooltip on hover
- [ ] **BIDS-04**: Bid multipliers are loaded from a single config block at top of `bid_suggest.py` (no magic numbers scattered across code) so operator can tune in one place

### Budget Forecast

- [ ] **FRCS-01**: `forecast_budget.py` reads `clusters.json` + `ranked-enriched.json` and emits `{run_dir}/forecast.json` containing per-cluster `est_daily_clicks_low/mid/high`, `est_daily_spend_low/mid/high`, `est_monthly_spend_band`, and a campaign-level rollup
- [ ] **FRCS-02**: Click estimates use intent-class CTR anchors: transactional 6%, commercial 4%, informational 2%, navigational 8% (documented in script header, configurable)
- [ ] **FRCS-03**: Spend estimates use suggested_max_cpc × 0.65 (typical avg CPC ratio to max CPC); low band = sum × 0.5, mid = sum × 1.0, high = sum × 1.5 to express forecast uncertainty
- [ ] **FRCS-04**: Report renders Budget Forecast section per cluster + campaign totals; report.md table shows low/mid/high daily spend per cluster
- [ ] **FRCS-05**: Forecast section includes a "How this is calculated" subsection explaining assumptions are directional, not Google's official forecast tool — prevents operator over-promising to client

### Operator Next-Steps Checklist

- [ ] **STEP-01**: `render_report.py` appends a `## Next Steps` section to `report.md` containing an ordered ops checklist: (1) create campaign in <location/language>, (2) set daily budget to <mid forecast>, (3) create ad groups <names from clusters>, (4) paste positives.csv via Editor, (5) paste negatives.csv at campaign level for Strong tier, (6) write 3 RSAs per ad group using competitor headline/CTA/offer examples, (7) set max CPC per keyword from suggested values, (8) review compliance flags before enabling
- [ ] **STEP-02**: Checklist substitutes brief values (location, language, audience, budget) and forecast values (mid spend) into the template so each run reads as bespoke instructions, not boilerplate
- [ ] **STEP-03**: HTML report renders the checklist with copy-able command snippets and checkboxes that persist via localStorage so operator can track progress within a session
- [ ] **STEP-04**: report.json `next_steps[]` array carries the ordered step list for downstream tooling

### Compliance Flags

- [ ] **CMPL-01**: `compliance_check.py` scans `ranked-enriched.json` + `brief.md` against regulated-vertical token lists (medical/legal/finance/gambling/crypto) and emits `{run_dir}/compliance-flags.json` with matched verticals, evidence tokens, and verification-path URLs
- [ ] **CMPL-02**: Token lists are stored in `references/compliance-verticals.json` (data, not code) so operator can extend without code change; each vertical entry has `tokens[]`, `verification_url`, and `policy_note`
- [ ] **CMPL-03**: Report renders a "⚠ Compliance Required" block above the Ranked Keywords table when any vertical matches; HTML uses warning-yellow background; markdown uses block quote with `⚠` prefix
- [ ] **CMPL-04**: report.json `compliance[]` array lists matched verticals; build_report_json signature extends with `compliance` kwarg; absent → empty array
- [ ] **CMPL-05**: Next-Steps checklist (STEP-01) reorders step 8 to step 1 when compliance flags present — "Complete <vertical> verification at <URL> before launching"; the rest of the checklist remains in order

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Volume Enrichment

- **VOLM-01**: Optional Google Ads API integration for monthly search volume, low/high CPC bid, competition level
- **VOLM-02**: Optional DataForSEO fallback when Google Ads API unavailable

### Vertical Presets

- **VPRS-01**: Ecommerce preset shaping seed expansion + intent rubric for product-focused campaigns
- **VPRS-02**: SaaS preset for B2B software lead-gen
- **VPRS-03**: Local services preset emphasizing geo modifiers
- **VPRS-04**: Lead-gen preset for form-driven funnels

### Tooling

- **TOOL-01**: SERP result cache by query hash to reduce repeat API spend
- **TOOL-02**: CSV export in Google Ads Editor import format
- **TOOL-03**: Run-diff script comparing two runs by `report.json`
- **TOOL-04**: Multi-locale fan-out (one brief, multiple country/language report sets)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Cost gate / pre-run spend confirmation | Operator chose to skip — trust operator, faster iteration |
| Web dashboard / UI | Markdown report sufficient; UI duplicates Claude Code chat |
| Multi-tenant / auth | Single internal operator model |
| ~~Auto-push to Google Ads (API or Editor CSV format)~~ | **Updated v1.1**: Editor CSV export moved in-scope (EXPT-01..05). Direct API push remains excluded — operator's manual Editor import preserves bad-data gate. |
| Real-time / scheduled / cron runs | Operator-triggered only |
| Strict 10-field brief schema | Operator chose looser 5-required + optional model |
| `sentence-transformers` / embedding-based clustering | ~700MB torch transitive deps make skill non-portable; LLM-driven clustering chosen |
| `scikit-learn` TF-IDF/k-means clustering | v2 fallback only if LLM clustering proves inconsistent |
| SEO content generation | Out of remit — agent is for paid search keywords |
| Quality Score prediction | Requires Google Ads account integration; v2+ |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCFD-01 | Phase 1 | Complete |
| SCFD-02 | Phase 1 | Complete |
| SCFD-03 | Phase 1 | Complete |
| SCFD-04 | Phase 1 | Complete |
| SCFD-05 | Phase 1 | Complete |
| INTK-01 | Phase 1 | Complete |
| INTK-02 | Phase 1 | Complete |
| INTK-03 | Phase 1 | Complete |
| INTK-04 | Phase 1 | Complete |
| SIGL-01 | Phase 2 | Complete |
| SIGL-02 | Phase 2 | Complete |
| SIGL-03 | Phase 2 | Complete |
| SIGL-04 | Phase 2 | Complete |
| SIGL-05 | Phase 2 | Complete |
| SIGL-06 | Phase 2 | Complete |
| RANK-01 | Phase 3 | Complete |
| RANK-02 | Phase 3 | Complete |
| RANK-03 | Phase 3 | Complete |
| RANK-04 | Phase 3 | Complete |
| CLST-01 | Phase 4 | Complete |
| CLST-02 | Phase 4 | Complete |
| CLST-03 | Phase 4 | Pending |
| COMP-01 | Phase 5 | Complete |
| COMP-02 | Phase 5 | Complete |
| COMP-03 | Phase 5 | Complete |
| NEGT-01 | Phase 6 | Complete |
| NEGT-02 | Phase 6 | Complete |
| NEGT-03 | Phase 6 | Complete |
| RPRT-01 | Phase 6 | Complete |
| RPRT-02 | Phase 6 | Complete |
| RPRT-03 | Phase 6 | Complete |
| RPRT-04 | Phase 6 | Complete |
| RPRT-05 | Phase 6 | Complete |
| PRST-01 | Phase 6 | Complete |
| PRST-02 | Phase 6 | Complete |
| BIDS-01 | Phase 9 | Pending |
| BIDS-02 | Phase 9 | Pending |
| BIDS-03 | Phase 9 | Pending |
| BIDS-04 | Phase 9 | Pending |
| FRCS-01 | Phase 9 | Pending |
| FRCS-02 | Phase 9 | Pending |
| FRCS-03 | Phase 9 | Pending |
| FRCS-04 | Phase 9 | Pending |
| FRCS-05 | Phase 9 | Pending |
| CMPL-01 | Phase 9 | Pending |
| CMPL-02 | Phase 9 | Pending |
| CMPL-03 | Phase 9 | Pending |
| CMPL-04 | Phase 9 | Pending |
| CMPL-05 | Phase 9 | Pending |
| EXPT-01 | Phase 10 | Pending |
| EXPT-02 | Phase 10 | Pending |
| EXPT-03 | Phase 10 | Pending |
| EXPT-04 | Phase 10 | Pending |
| EXPT-05 | Phase 10 | Pending |
| STEP-01 | Phase 10 | Pending |
| STEP-02 | Phase 10 | Pending |
| STEP-03 | Phase 10 | Pending |
| STEP-04 | Phase 10 | Pending |

**Coverage:**
- v1.0 requirements: 52 total (35 originally mapped + 9 PULSE + 8 AHRF/GADS added during v1.0)
- v1.0 mapped to phases: 52 (Phases 1-8)
- v1.1 requirements: 23 total (BIDS-01..04, FRCS-01..05, CMPL-01..05, EXPT-01..05, STEP-01..04)
- v1.1 mapped to phases: 23 (Phase 9: 14 reqs, Phase 10: 9 reqs)
- Unmapped: 0 v1.0 / 0 v1.1
- Orphaned: 0 — every requirement maps to exactly one phase

---
*Requirements defined: 2026-05-08*
*Last updated: 2026-05-14 — v1.1 traceability rows added (Phases 9-10)*
