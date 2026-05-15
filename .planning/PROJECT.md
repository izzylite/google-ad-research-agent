# Google Ad Research Agent

## What This Is

Internal Claude Code skill for a centralized PPC operator. Operator pastes a campaign brief in a Claude Code session; the skill asks clarifying questions, runs keyword research via WebSearch + Serper.dev + Tavily, and produces a markdown report with a ranked keyword table, ad group clusters, competitor ad copy, and negative keyword candidates. The operator distributes results to the rest of the PPC team.

## Core Value

From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session, without the operator leaving the chat.

## Current Milestone: v1.5 Account-Aware Narrowing

**Goal:** Narrow skill output from "whole OAuth account" to "operator's actual target campaign + the AGs inside it". Same architectural pattern as v1.2's `geo_focus`. Two issues fixed: Phase 8 GAQL queries pull all 30+ campaigns (cross-refs contaminated by unrelated data); Ad Group Mapping algorithm uses AG name only (Jaccard near zero on real client accounts).

**Target features:**
- Optional `campaign_focus:` brief field — `perf_fetch.py` adds `AND campaign.name = '<focus>'` filter to all 4 GAQL queries (keyword_view, search_term_view, ad_group, campaign_criterion)
- Positives Sync + Negatives Sync + Ad Group Mapping inherit narrowed dataset automatically (no per-script wiring needed)
- Report header renders "Campaign Focus" callout beside Geographic Focus; validates name against `raw/google-ads-perf.json` campaigns list
- Graceful degrade: no `campaign_focus` → account-wide pull (current v1.4 behavior)
- `ad_group_match.py` `_build_ag_token_bag(name, kw_criteria, search_terms)` — Jaccard input enriched with Phase 14 `keyword_view` + Phase 8 `search_term_view`; replaces name-only logic
- Threshold recalibration after enrichment (likely 0.5 high / 0.25 medium); backward compat when Phase 14 raw absent

## Previous Milestone: v1.4 Positives Sync

**Goal (shipped):** Mirror negatives-sync for positives — diff ranked keywords against the client's currently-active Google Ads keywords and surface only net-new in `positives.csv`. Eliminates manual dedup pain on re-runs against the same account.

**Target features (shipped):**
- `perf_fetch.py` pulls `keyword_view` (active + paused account keywords, last 30d) via existing Google Ads OAuth
- `perf_synth.py` produces 4-bucket `positives-sync.json`: `already_active` / `paused_in_account` / `covered_by_broad` / `new_to_add`
- Report `## Positives Sync` section mirrors negatives-sync UX (stats line + enumerated `new_to_add` + count-only `already_active`)
- `positives.csv` filters to `new_to_add` by default; `--include-existing` CLI override for full list
- Graceful skip when `raw/google-ads-keywords.json` absent (no OAuth available)
- SKILL.md Step 34a LLM re-tag step for borderline semantic dupes
- Phase 13 (Landing-Page Extract Vendor Swap) remains backlog under v1.3 — defer-until-friction

## Previous Milestone: v1.3 Source Consolidation

**Goal (shipped):** Dropped Tavily. Landing-page extraction switched to Claude WebFetch. Niche pulse news single-source via Serper /news. Paid API surface reduced from 3 keys → 2 (Serper + Ahrefs + Google Ads).

**Target features (shipped):**
- Tavily removed entirely (script + SDK dep + env key + tests)
- Phase 5 COMP-03 landing-page extraction switches to WebFetch (built-in, free, mirrors WebSearch baseline pattern)
- Phase 7 Niche Pulse removed entirely post-v1.3 (internal-team noise on repeated runs in single vertical)
- Source taxonomy in merge_signals.py drops `tavily-extract`; `webfetch-landing` source added
- `.env.example` + lib/config.py drop TAVILY_API_KEY

## Previous Milestone: v1.2 Account-Structure Mapping

**Goal:** Skill output respects the client's existing Google Ads account — narrows research to specific counties/cities in the brief, and maps our generated keywords TO the client's existing ad group structure instead of inventing new groups.

**Target features:**
- Optional county/city `geo_focus` list in brief; SERP queries + keyword filter narrow to scope
- US cities/counties reference data file for out-of-scope keyword filter
- `ad_group_match.py` maps our ranked keywords to existing account ad groups (Phase 8 perf data)
- Match confidence per keyword (high/medium/low); low-confidence flagged for new ad group
- `export_csv.py` writes existing ad group names when mapping covers keyword; unmapped → new cluster
- Next Steps checklist reorders to "Add to existing ad groups" when mapping coverage >50%

## Previous Milestone: v1.1 Operator-Ready Output

**Goal:** Turn the report from a data dump into a campaign launch kit — junior PPC managers can move from report.md to a live, compliant Google Ads campaign with starter bids, budget bands, and a step-by-step checklist.

**Target features:**
- CSV export in Google Ads Editor import format (positives, negatives, ad groups)
- Per-keyword max-CPC bid suggestions (intent-weighted, derived from Ahrefs CPC)
- Budget forecast per cluster (low/mid/high daily click + spend bands)
- Operator Next-Steps ordered checklist appended to report.md
- Compliance flags for regulated verticals (medical, legal, finance, gambling, crypto)

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Conversational brief intake (5 required fields + optional conditional follow-ups) — v1.0
- ✓ Three-source signal collection (Serper, Tavily, WebSearch) with locale plumbing — v1.0
- ✓ 4-class intent ranking + source-diversity-primary composite score — v1.0
- ✓ Intent-homogeneous LLM clustering (5-15 kw per cluster) — v1.0
- ✓ Per-cluster competitor ad copy + landing-page value-prop extraction — v1.0
- ✓ Tiered negatives (Strong/Considered/Investigate) × 6 categories, dedup vs positive pool — v1.0
- ✓ Four-section markdown + JSON twin + HTML report, sealed run folder, browsable INDEX — v1.0
- ✓ Niche Pulse sidecar — 7-day news harvest with trending themes + regulatory alerts — v1.0 (✗ REMOVED post-v1.3 — internal-team noise)
- ✓ Account Data + Volume Enrichment sidecar — Ahrefs volume/CPC/KD + Google Ads search terms/perf/negatives sync — v1.0
- ✓ Editor CSV export (positives/negatives/ad_groups, Editor v2.x format) — v1.1
- ✓ Max-CPC bid suggestions (intent-weighted from Ahrefs CPC) — v1.1
- ✓ Budget forecast per cluster (low/mid/high bands, methodology disclaimer) — v1.1
- ✓ Operator Next Steps checklist (bespoke substitution + HTML localStorage checkboxes) — v1.1
- ✓ Compliance flags w/ CMPL-05 reorder (regulated-vertical verification at step 1) — v1.1
- ✓ Optional brief `geo_focus` (county/city) — narrows research to specific area, drops out-of-scope city keywords — v1.2
- ✓ us-cities.json reference data file (top 5000 US cities w/ county hierarchy) — v1.2
- ✓ ad_group_match.py — maps ranked keywords to existing account ad groups w/ confidence tiers — v1.2
- ✓ export_csv preserves existing ad group names when mapping coverage > 50% — v1.2
- ✓ Tavily removed entirely (script + SDK dep + TAVILY_API_KEY + tests) — v1.3
- ✓ WebFetch invoked from SKILL.md Phase 5 for top 3-5 advertisers per cluster (landing page extraction) — v1.3
- ✓ competitor_intel.py + merge_signals.py Tavily code paths stripped — v1.3
- ✓ Phase 7 Niche Pulse REMOVED post-v1.3 (pulse_fetch + pulse_synth deleted; references/phase7 deleted; report sections stripped)
- ✓ Source taxonomy: tavily-extract removed; webfetch-landing added — v1.3
- ✓ `perf_fetch.py` pulls `keyword_view` (active + paused account keywords, last 30d) — v1.4
- ✓ `perf_synth.py` 4-bucket `positives-sync.json` (already_active / paused_in_account / covered_by_broad / new_to_add) — v1.4
- ✓ Report `## Positives Sync` section + HTML mirrors negatives-sync UX — v1.4
- ✓ `positives.csv` filters to `new_to_add` by default; `--include-existing` flag for full list — v1.4
- ✓ Graceful skip across synth/render/csv when `raw/google-ads-keywords.json` absent — v1.4
- ✓ SKILL.md Step 34a LLM re-tag step for borderline semantic dupes — v1.4
- ✓ Existing Ad Groups in Account always rendered in Mapping section (post-v1.4 UX fix, commit 4674b00)

### Active

<!-- v1.5 scope. Building toward these. -->

- [ ] Brief `campaign_focus:` field parsed by `_parse_brief_fields` (single value or list)
- [ ] `perf_fetch.py --campaign-filter '<name>'` adds `AND campaign.name = '...'` to all 4 GAQL queries
- [ ] SKILL.md Phase 8 step auto-passes `campaign_focus` from brief.md to perf_fetch
- [ ] Graceful degrade: no `campaign_focus` → account-wide pull (current v1.4 behavior)
- [ ] Report header renders Campaign Focus callout when set; validates name against raw perf.json
- [ ] `_build_ag_token_bag(name, kw_criteria, search_terms)` enriches Jaccard input beyond AG name
- [ ] Jaccard scoring uses enriched bag; falls back to name-only when Phase 14 raw absent
- [ ] Match `reason` field surfaces which evidence source contributed
- [ ] Threshold recalibration documented in `references/phase11-account-structure-mapping.md`
- [ ] Test coverage: brief w/ campaign_focus + respx GAQL filter assertion + golden mapping fixture asserting ≥50% coverage

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Vertical presets (ecommerce / SaaS / lead gen / local) — defer to v2 once real usage shows which verticals matter.
- Web dashboard / UI — markdown report is the deliverable; building a UI duplicates Claude Code chat without adding value for a single operator.
- Multi-tenant or auth — single internal operator model, no per-user state needed.
- **Auto-push** to Google Ads via API — CSV export now in-scope (operator imports manually via Editor) but **direct API push** stays excluded; CSV-in-Editor gives operator final sanity check before going live.
- Caching of SERP results — adds plumbing, real cost is low at this volume; revisit if API costs sting.
- Real-time / scheduled runs — operator-triggered only; no cron.

## Context

- **Distribution model:** centralized operator runs the skill on demand, hands the markdown report to PPC managers. Not self-serve for the wider team in v1.
- **Greenfield repo:** empty directory `c:\Users\Izzy\Documents\Projects\google-ad-research-agent`, fresh git init, no prior code.
- **Runtime:** lives entirely inside Claude Code as a skill — skill markdown for prompts + Python helper scripts for API calls and report assembly. No separate server, no deploy target.
- **Three signal sources, three roles:** WebSearch (free baseline), Serper.dev (structured SERP — PAA, related, ads block), Tavily (deep content from competitor pages).
- **No volume data in v1:** explicit decision. Ranking falls back to frequency-of-occurrence across SERP signals + LLM-judged commercial intent. Operator enriches with Keyword Planner manually if needed.

## Constraints

- **Tech stack:** Python helper scripts + Claude Code skill markdown. Python chosen for ecosystem (requests, JSON/CSV/markdown handling, LLM tooling).
- **APIs:** WebSearch (built-in, free), Serper.dev (paid, ~$0.001/query), Tavily (paid, ~$0.005-0.01/query). Two paid keys required.
- **Runtime:** Claude Code only — no standalone CLI, no web app, no server. Skill must work entirely within a Claude Code session.
- **Data freshness:** all signals fetched live per run; no cache means Serper/Tavily costs scale linearly with run frequency.
- **Operator skill level:** technical enough to use Claude Code, manage API keys via env vars, and read markdown reports. Not building for non-technical end users.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Claude Code skill, not standalone app | Operator already lives in Claude Code; avoids second runtime to maintain | — Pending |
| WebSearch + Serper.dev + Tavily (no DataForSEO/Google Ads API) | Volume data deferred — frequency + intent ranking adequate for v1, keeps API count low | — Pending |
| Conversational brief intake, not structured form | Skill UX matches Claude Code chat pattern; operator can paste rough brief and let skill draw out missing fields | — Pending |
| Generic engine v1, vertical presets v2 | Ship simpler core; let real usage reveal which verticals justify presets | — Pending |
| Python helper scripts | Standard for LLM/data work, easy CSV/markdown generation, both Tavily and Serper have Python SDKs | — Pending |
| Run history folder, no caching | Dated folders cover "what did we research last week"; caching adds plumbing without v1 payoff | — Pending |
| Markdown report (no CSV, no dashboard) — v1.0 | Operator reads in Claude Code; markdown tables paste cleanly into docs/Slack; CSV deferrable if Google Ads import becomes a need | ⚠️ Revisit — Editor CSV moved in-scope for v1.1 (operator productivity gain outweighs original concern, manual Editor step preserves bad-data gate) |
| Add Editor CSV export in v1.1 | Junior managers spend 30+ min/run hand-copying keywords; Editor CSV is a one-import paste; manual Editor review keeps the "no bad data live" guardrail | — Pending |
| Intent-weighted bid multipliers (1.2x / 0.8x / 0.4x) | Junior asks "what bid?" — defensible starting point from Ahrefs CPC anchored by buyer-stage; transactional aggressive, informational conservative | — Pending |
| Compliance flag heuristics, not full policy engine | Detect 5 high-friction verticals (medical/legal/finance/gambling/crypto) by keyword token match; deeper Google Ads policy automation deferred — pointer to verification path is enough for junior | — Pending |

| Geo narrowing via brief `geo_focus` list — v1.2 | Team feedback: research returned Lake Worth FL keywords from across Florida; need county/city precision. Brief field + US-cities reference data scan keeps it simple. | — Pending |
| Ad-group mapping respects client structure — v1.2 | Junior PPC manager paste-experience: current export creates new ad groups (theme_intent slugs) instead of reusing client's existing ad groups. Mapping script reads Phase 8 perf data + writes existing names to CSV. | — Pending |

| Drop Tavily v1.3 | Tavily plan quota exhausted mid-Lake Worth re-run; Serper /webpage covers landing-page extract OR Claude WebFetch covers it free. Reducing paid API surface = fewer quota concerns + one fewer key to manage. WebFetch chosen over Serper /webpage — free (no API credits), mirrors WebSearch baseline pattern, fits single-operator Claude Code workflow. | ✓ Good — shipped v1.3, empirical pass on Lake Worth run |
| Positives Sync v1.4 (Phase 14) | Re-running skill against the same client produces duplicate keyword imports — operator manually scrubs `positives.csv` before Editor paste. Negatives already dedup via Phase 8 `negatives-sync.json`; positives are asymmetric. Use existing Google Ads OAuth + `keyword_view` GAQL (free quota). LLM re-tag for semantic dupes catches the 20% of cases plain string norm misses. | ✓ Good — shipped v1.4, live e2e on Lake Worth (64 new / 11 active / 8 covered_by_broad) |
| Account-Aware Narrowing v1.5 (Phases 15-16) | Lake Worth dogfood revealed two related contamination issues: (1) Phase 8 GAQL pulls all 30+ campaigns when brief targets ONE → Positives/Negatives Sync + AG Mapping show irrelevant data; (2) AG Mapping Jaccard uses AG name only (~4 tokens) vs ranked kw (long phrases) → 0% coverage. Both fixed by extending Phase 11's `geo_focus` pattern to campaign + AG-criterion narrowing. No new APIs — reuses existing OAuth + raw data. | — Pending |
| Use Google Ads API over Ahrefs paid-kw for positives sync source | Authoritative truth (exact text, match_type, status, perf) vs Ahrefs inference (~60-80% accuracy, no match_type). OAuth already wired in Phase 8. Ahrefs paid-kw considered as fallback for accounts without OAuth — deferred. | — Pending |

---
*Last updated: 2026-05-15 after milestone v1.5 start*
