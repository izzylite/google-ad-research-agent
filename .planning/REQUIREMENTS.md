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

- [ ] **RANK-01**: LLM classifies each keyword by 4-class intent (informational / commercial / transactional / navigational) using categorical rubric with anchor examples, temperature=0
- [x] **RANK-02**: Composite ranking uses `signal_count` (occurrences) + `source_diversity` (distinct sources) + intent weight; primary ranking signal is `source_diversity`
- [x] **RANK-03**: Match-type recommendation (broad / phrase / exact) suggested per keyword with conservative defaults (phrase by default; exact for high-confidence transactional/brand; broad rarely)
- [x] **RANK-04**: Ranked keyword table columns: `keyword`, `intent`, `match_type`, `theme`, `signal_count`, `source_diversity`, `sources`, `score`

### Clustering

- [ ] **CLST-01**: Keywords cluster within intent class only — no intent-mixed clusters allowed
- [ ] **CLST-02**: LLM produces clusters of 5-15 keywords (min size 3) with descriptive names combining theme + intent
- [ ] **CLST-03**: Any cluster spanning more than one intent label is rejected and re-split

### Competitor Intel

- [ ] **COMP-01**: Per-cluster Serper requery extracts paid ad headlines + descriptions from ads block
- [ ] **COMP-02**: Ad copy deduplicated by advertiser domain; affiliate / aggregator domains filtered
- [ ] **COMP-03**: Tavily extracts landing-page value props (headline, primary CTA, offer) for top 3-5 advertisers per cluster

### Negatives

- [ ] **NEGT-01**: Negatives generated in three tiers — Strong, Considered, Investigate
- [ ] **NEGT-02**: Each negative tagged with category (jobs-careers / free-DIY-tutorial / used-refurb-wholesale / competitor-brand / wrong-geo / wrong-audience) and per-keyword justification
- [ ] **NEGT-03**: Negatives deduplicated against the final positive keyword pool

### Report Output

- [ ] **RPRT-01**: `render_report.py` writes `report.md` to run folder containing four sections — ranked keyword table, ad group clusters, competitor ad copy, tiered negatives
- [ ] **RPRT-02**: `report.json` twin written with stable canonical schema (enables future run-diff in v2)
- [ ] **RPRT-03**: Report includes "How to read this" section explaining `signal_count` is not search volume and ranking is signal-source-diversity-driven
- [ ] **RPRT-04**: Markdown sanitization on all table cells (escape pipes, quotes, newlines)
- [ ] **RPRT-05**: All raw per-stage API responses persisted to `raw/` subfolder for traceability

### Persistence

- [ ] **PRST-01**: Each run is an isolated dated folder containing `brief.md`, `report.md`, `report.json`, `raw/`
- [ ] **PRST-02**: `.runs/INDEX.md` lists past runs (date, brief slug, status) for operator browsing

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
| Auto-push to Google Ads (API or Editor CSV format) | v1 hands operator a markdown report; uploading manually prevents bad data going live |
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
| RANK-01 | Phase 3 | Pending |
| RANK-02 | Phase 3 | Complete |
| RANK-03 | Phase 3 | Complete |
| RANK-04 | Phase 3 | Complete |
| CLST-01 | Phase 4 | Pending |
| CLST-02 | Phase 4 | Pending |
| CLST-03 | Phase 4 | Pending |
| COMP-01 | Phase 5 | Pending |
| COMP-02 | Phase 5 | Pending |
| COMP-03 | Phase 5 | Pending |
| NEGT-01 | Phase 6 | Pending |
| NEGT-02 | Phase 6 | Pending |
| NEGT-03 | Phase 6 | Pending |
| RPRT-01 | Phase 6 | Pending |
| RPRT-02 | Phase 6 | Pending |
| RPRT-03 | Phase 6 | Pending |
| RPRT-04 | Phase 6 | Pending |
| RPRT-05 | Phase 6 | Pending |
| PRST-01 | Phase 6 | Pending |
| PRST-02 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-05-08*
*Last updated: 2026-05-08 — traceability mapped to roadmap*
