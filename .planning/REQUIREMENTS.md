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

### Niche Pulse (Phase 7) — REMOVED post-v1.3

**Removed 2026-05-15.** Phase 7 dropped after internal-team review: skill is for a single team in a single vertical (urgent care PIP, FL); operators already live in the niche daily, so news-theme synthesis was noise on repeated runs. PULSE-01..12 all marked ~~deprecated~~ — code, references, tests, and report sections deleted. Operators perform manual Google News checks when actually needed.

- [x] ~~**PULSE-01..09**: Phase 7 Niche Pulse core (Serper /news, theme clustering, regulatory alerts, competitor news, trending negatives).~~ **REMOVED post-v1.3 — internal-team noise.**
- [x] ~~**PULSE-10..12**: Phase 12 Tavily-drop work on pulse pipeline.~~ **REMOVED post-v1.3 alongside Phase 7 deletion.**

## v1.1 Requirements (Operator-Ready Output)

Milestone v1.1 — campaign launch kit additions. Builds on v1.0 artifacts (ranked-enriched.json, clusters.json, negatives.json, report.md).

### Editor CSV Export

- [x] **EXPT-01**: `export_csv.py` writes `{run_dir}/export/positives.csv` with columns `Campaign, Ad Group, Keyword, Match Type, Max CPC, Final URL` in Google Ads Editor import format (UTF-8, comma-delimited, quoted strings)
- [x] **EXPT-02**: `export_csv.py` writes `{run_dir}/export/negatives.csv` with columns `Campaign, Ad Group, Keyword, Match Type, Level` (Level = `campaign` | `ad_group`); Strong tier → campaign level, Considered/Investigate → ad_group level
- [x] **EXPT-03**: `export_csv.py` writes `{run_dir}/export/ad_groups.csv` with columns `Campaign, Ad Group, Status, Default Max CPC` for ad group creation
- [x] **EXPT-04**: Editor-importable verification — CSV passes `csv.DictReader` round-trip and column headers exactly match Google Ads Editor v2.x spec (no BOM, CRLF line endings)
- [x] **EXPT-05**: `render_report.py` adds "Export Files" section linking to each CSV; `report.json` lists export file paths in stable `exports[]` array

### Max-CPC Bid Suggestions

- [x] **BIDS-01**: `bid_suggest.py` (or extension to volume_enrich.py) adds `suggested_max_cpc_micros` column to `ranked-enriched.json` derived from `cpc_micros × intent_multiplier` (transactional 1.2, commercial 0.8, informational 0.4, navigational 1.0)
- [x] **BIDS-02**: Keywords with no Ahrefs `cpc_micros` data fall back to cluster-median CPC × intent_multiplier; if cluster has no CPC data at all, suggested_max_cpc is `null` and flagged `no_cpc_data` in report
- [x] **BIDS-03**: Report ranked-enriched table renders `Suggested Max CPC` column (USD with cents); HTML report shows the multiplier in a tooltip on hover
- [x] **BIDS-04**: Bid multipliers are loaded from a single config block at top of `bid_suggest.py` (no magic numbers scattered across code) so operator can tune in one place

### Budget Forecast

- [x] **FRCS-01**: `forecast_budget.py` reads `clusters.json` + `ranked-enriched.json` and emits `{run_dir}/forecast.json` containing per-cluster `est_daily_clicks_low/mid/high`, `est_daily_spend_low/mid/high`, `est_monthly_spend_band`, and a campaign-level rollup
- [x] **FRCS-02**: Click estimates use intent-class CTR anchors: transactional 6%, commercial 4%, informational 2%, navigational 8% (documented in script header, configurable)
- [x] **FRCS-03**: Spend estimates use suggested_max_cpc × 0.65 (typical avg CPC ratio to max CPC); low band = sum × 0.5, mid = sum × 1.0, high = sum × 1.5 to express forecast uncertainty
- [x] **FRCS-04**: Report renders Budget Forecast section per cluster + campaign totals; report.md table shows low/mid/high daily spend per cluster
- [x] **FRCS-05**: Forecast section includes a "How this is calculated" subsection explaining assumptions are directional, not Google's official forecast tool — prevents operator over-promising to client

### Operator Next-Steps Checklist

- [x] **STEP-01**: `render_report.py` appends a `## Next Steps` section to `report.md` containing an ordered ops checklist: (1) create campaign in <location/language>, (2) set daily budget to <mid forecast>, (3) create ad groups <names from clusters>, (4) paste positives.csv via Editor, (5) paste negatives.csv at campaign level for Strong tier, (6) write 3 RSAs per ad group using competitor headline/CTA/offer examples, (7) set max CPC per keyword from suggested values, (8) review compliance flags before enabling
- [x] **STEP-02**: Checklist substitutes brief values (location, language, audience, budget) and forecast values (mid spend) into the template so each run reads as bespoke instructions, not boilerplate
- [x] **STEP-03**: HTML report renders the checklist with copy-able command snippets and checkboxes that persist via localStorage so operator can track progress within a session
- [x] **STEP-04**: report.json `next_steps[]` array carries the ordered step list for downstream tooling

### Compliance Flags

- [x] **CMPL-01**: `compliance_check.py` scans `ranked-enriched.json` + `brief.md` against regulated-vertical token lists (medical/legal/finance/gambling/crypto) and emits `{run_dir}/compliance-flags.json` with matched verticals, evidence tokens, and verification-path URLs
- [x] **CMPL-02**: Token lists are stored in `references/compliance-verticals.json` (data, not code) so operator can extend without code change; each vertical entry has `tokens[]`, `verification_url`, and `policy_note`
- [x] **CMPL-03**: Report renders a "⚠ Compliance Required" block above the Ranked Keywords table when any vertical matches; HTML uses warning-yellow background; markdown uses block quote with `⚠` prefix
- [x] **CMPL-04**: report.json `compliance[]` array lists matched verticals; build_report_json signature extends with `compliance` kwarg; absent → empty array
- [x] **CMPL-05**: Next-Steps checklist (STEP-01) reorders step 8 to step 1 when compliance flags present — "Complete <vertical> verification at <URL> before launching"; the rest of the checklist remains in order

## v1.2 Requirements (Account-Structure Mapping)

Milestone v1.2 — Phase 11 only. Team feedback driven: research narrows to specific counties/cities + reuses client's existing ad group structure.

### Geographic Refinement

- [x] **GEO-01**: Brief intake accepts optional `geo_focus` field — comma-separated list of counties/cities within the top-level location (e.g., "Palm Beach County, Lake Worth, West Palm Beach"). Skill prompts conditionally when location is at state level + operator hints at locality.
- [x] **GEO-02**: `serp_fetch.py` includes `geo_focus` tokens in query strings to bias SERP locality (e.g., "car accident doctor Palm Beach County" instead of "car accident doctor"); appended to existing seed phrases when geo_focus present.
- [x] **GEO-03**: `merge_signals.py` adds an out-of-scope-city filter — drops keywords containing US-city/county tokens NOT in `geo_focus` (within the same state); scope-aware to avoid false positives (e.g., "Boca Raton" dropped from Lake Worth run, "Tampa" dropped from Palm Beach County run).
- [x] **GEO-04**: `references/us-cities.json` reference data file (operator-editable, ~30KB) lists US cities and counties per state for the GEO-03 filter scan. Sourced from US Census place data; subset to top 5000 cities (covers >95% of likely false-positive tokens).
- [x] **GEO-05**: `render_report.py` adds a "Geographic Focus" callout under the Header section showing top-level location + geo_focus list (e.g., "Florida → Palm Beach County, Lake Worth"). Empty geo_focus → callout omitted gracefully.

### Ad-Group Mapping (existing client structure)

- [x] **ADGM-01**: `ad_group_match.py` reads `raw/google-ads-perf.json` (Phase 8 GADS-02 output) + `raw/google-ads-search-terms.json` (GADS-01) to extract a `{existing_ad_group → [member_keywords]}` index. Skip silently when Phase 8 not run.
- [x] **ADGM-02**: For each ranked-enriched keyword, compute similarity to each existing ad group via token overlap + intent class match; pick highest-scoring match above a configurable threshold (default 0.4).
- [x] **ADGM-03**: Confidence tier per match — `high` (>= 0.7), `medium` (0.4-0.7), `low` (< 0.4 = no match, fallback to new cluster). Threshold values in a single config block, frozenset-asserted.
- [x] **ADGM-04**: Emits `ad-group-mapping.json` sidecar: `{matches: [{keyword, existing_ad_group, confidence, reason}], unmapped_count, mapping_coverage_pct}`.
- [x] **ADGM-05**: `export_csv.py` reads `ad-group-mapping.json` when present; positives.csv `Ad Group` column = existing ad group name for matched keywords, cluster slug for unmapped. ad_groups.csv lists only NEW ad groups (skip existing ones to avoid Editor duplicate-name errors).
- [x] **ADGM-06**: `render_report.py` Next Steps section conditionally rewrites when mapping coverage > 50% — "Add keywords to existing ad groups: <names>" replaces "Create ad groups: <new names>"; existing ad groups listed by name with keyword count.

## v1.3 Requirements (Source Consolidation — Drop Tavily)

Milestone v1.3 — Phase 12 only. Replace Tavily landing-page extraction w/ Claude WebFetch (built-in). Drop redundant Tavily news call in Phase 7 (Serper /news covers it). Reduce paid API surface by one vendor.

### Tavily Removal

- [x] **TVLY-01**: `scripts/tavily_extract.py` deleted; any `lib/` Tavily helper removed
- [x] **TVLY-02**: `TAVILY_API_KEY` removed from `.env.example`, `lib/config.py` validation list, and any project docs/README
- [x] **TVLY-03**: `pyproject.toml` deps drop `tavily-python`; fixture files with `tavily-` prefix renamed or deleted; raw output filenames `tavily-*.json` removed from glob references
- [x] **TVLY-04**: `tests/test_tavily_extract.py` deleted; conftest fixtures pruned; respx mocks for Tavily removed

### WebFetch Replacement for COMP-03

- [x] **WFCH-01**: SKILL.md Phase 5 step (Step 19) rewrites — Claude invokes WebFetch from skill prompt for top 3-5 advertisers per cluster, mirrors WebSearch baseline pattern in Step 7
- [x] **WFCH-02**: Skill writes extracted `{headline, cta, offer}` per advertiser to `raw/competitor-landing-pages.json` via Write tool (replaces `raw/tavily-<domain>.json` files)
- [x] **WFCH-03**: `competitor_intel.py` drops Tavily call path; keeps Serper requery for ads block + Serper-organic fallback for advertiser identity discovery
- [x] **WFCH-04**: Source taxonomy in `merge_signals.py` removes `tavily-extract` from 6-source list; the new `webfetch-landing` source is NOT merged into main keyword pool (landing-page extraction is Phase 5 competitor intel only, not keyword harvest)

### Pulse Tavily Drop — REMOVED post-v1.3

Phase 7 dropped entirely post-v1.3 (see Niche Pulse section above). PULSE-10..12 work is historical record only.

## v1.4 Requirements (Positives Sync)

Milestone v1.4 — Phase 14 only. Mirror negatives-sync UX for positives: diff ranked keywords against the client's currently-active Google Ads keywords, surface only net-new in `positives.csv`. Eliminates manual dedup pain on re-runs against the same account. Uses existing Google Ads OAuth from Phase 8.

### Positives Sync (Phase 14)

- [x] **POS-01**: `perf_fetch.py` adds new GAQL against `keyword_view` (last 30d) pulling `ad_group_criterion.keyword.text`, `ad_group_criterion.keyword.match_type`, `ad_group_criterion.status`, `metrics.impressions/clicks/conversions/cost_micros`; writes `raw/google-ads-keywords.json`. PMax campaigns excluded (no kw-level data).
- [ ] **POS-02**: `perf_synth.py` adds `cross_ref_positives(ranked, existing_kws)` producing `positives-sync.json` with 4 buckets — `already_active` / `paused_in_account` / `covered_by_broad` / `new_to_add` — plus stats block mirroring `negatives-sync.json` structure.
- [ ] **POS-03**: `render_report.py` adds `render_positives_sync_section()` — markdown + HTML — surfacing stats line + enumerated `new_to_add` list (with category/justification per row) + count-only `already_active` + collapsible `paused_in_account` + `covered_by_broad`; mirrors negatives-sync UX.
- [ ] **POS-04**: `export_csv.py` filters `positives.csv` rows to `new_to_add` only by default when `positives-sync.json` present; new `--include-existing` CLI flag opts back into full ranked list.
- [ ] **POS-05**: Phase 14 graceful-skips when `raw/google-ads-keywords.json` absent (no Google Ads OAuth in `.env`) — report omits Positives Sync section, `positives.csv` falls back to full ranked list.
- [ ] **POS-06**: SKILL.md adds optional LLM re-tag step after `cross_ref_positives` — re-classifies borderline cases (semantic dupes like `urgent care lake worth` vs `lake worth urgent care`, match-type drift like ranked exact vs account broad covering same kw) by reading `positives-sync.json` + emitting refined tags.
- [x] **POS-07**: Test coverage: `test_perf_synth.py` adds `cross_ref_positives` unit tests (each bucket exercised); `tests/fixtures/golden_positives_sync.json` byte-exact fixture; `test_perf_fetch.py` mocks `keyword_view` GAQL response via respx.

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
| BIDS-01 | Phase 9 | Complete |
| BIDS-02 | Phase 9 | Complete |
| BIDS-03 | Phase 9 | Complete |
| BIDS-04 | Phase 9 | Complete |
| FRCS-01 | Phase 9 | Complete |
| FRCS-02 | Phase 9 | Complete |
| FRCS-03 | Phase 9 | Complete |
| FRCS-04 | Phase 9 | Complete |
| FRCS-05 | Phase 9 | Complete |
| CMPL-01 | Phase 9 | Complete |
| CMPL-02 | Phase 9 | Complete |
| CMPL-03 | Phase 9 | Complete |
| CMPL-04 | Phase 9 | Complete |
| CMPL-05 | Phase 10 | Complete |
| EXPT-01 | Phase 10 | Complete |
| EXPT-02 | Phase 10 | Complete |
| EXPT-03 | Phase 10 | Complete |
| EXPT-04 | Phase 10 | Complete |
| EXPT-05 | Phase 10 | Complete |
| STEP-01 | Phase 10 | Complete |
| STEP-02 | Phase 10 | Complete |
| STEP-03 | Phase 10 | Complete |
| STEP-04 | Phase 10 | Complete |
| GEO-01 | Phase 11 | Complete |
| GEO-02 | Phase 11 | Complete |
| GEO-03 | Phase 11 | Complete |
| GEO-04 | Phase 11 | Complete |
| GEO-05 | Phase 11 | Complete |
| ADGM-01 | Phase 11 | Complete |
| ADGM-02 | Phase 11 | Complete |
| ADGM-03 | Phase 11 | Complete |
| ADGM-04 | Phase 11 | Complete |
| ADGM-05 | Phase 11 | Complete |
| ADGM-06 | Phase 11 | Complete |
| TVLY-01 | Phase 12 | Complete |
| TVLY-02 | Phase 12 | Complete |
| TVLY-03 | Phase 12 | Complete |
| TVLY-04 | Phase 12 | Complete |
| WFCH-01 | Phase 12 | Complete |
| WFCH-02 | Phase 12 | Complete |
| WFCH-03 | Phase 12 | Complete |
| WFCH-04 | Phase 12 | Complete |
| PULSE-10 | Phase 12 | Complete |
| PULSE-11 | Phase 12 | Complete |
| PULSE-12 | Phase 12 | Complete |
| POS-01 | Phase 14 | Complete |
| POS-02 | Phase 14 | Pending |
| POS-03 | Phase 14 | Pending |
| POS-04 | Phase 14 | Pending |
| POS-05 | Phase 14 | Pending |
| POS-06 | Phase 14 | Pending |
| POS-07 | Phase 14 | Complete (Plan 14-00 scaffolding; flips fully GREEN as Wave 1/2 plans land) |

**Coverage:**
- v1.0 requirements: 52 total (Phases 1-8, all complete)
- v1.1 requirements: 23 total (Phase 9 + 10, all complete)
- v1.2 requirements: 11 total (Phase 11, all complete)
- v1.3 requirements: 11 / 11 Complete (TVLY×4 + WFCH×4 + PULSE×3) — Phase 12
- v1.4 requirements: 0 / 7 Complete (POS×7) — Phase 14 pending
- v1.3 mapped to phases: 11 (Phase 12)
- v1.4 mapped to phases: 7 (Phase 14)
- Unmapped: 0
- Orphaned: 0

**Total: 89 Complete / 7 Pending = 96 v1 requirements** (52 v1.0 + 23 v1.1 + 11 v1.2 + 11 v1.3 + 7 v1.4).

---
*Requirements defined: 2026-05-08*
*Last updated: 2026-05-15 — Milestone v1.4 (Positives Sync) started; 7 new requirements POS-01..07 mapped to Phase 14 (pending). Total v1 surface: 96 requirements (89 Complete + 7 Pending).*
