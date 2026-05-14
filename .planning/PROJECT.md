# Google Ad Research Agent

## What This Is

Internal Claude Code skill for a centralized PPC operator. Operator pastes a campaign brief in a Claude Code session; the skill asks clarifying questions, runs keyword research via WebSearch + Serper.dev + Tavily, and produces a markdown report with a ranked keyword table, ad group clusters, competitor ad copy, and negative keyword candidates. The operator distributes results to the rest of the PPC team.

## Core Value

From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session, without the operator leaving the chat.

## Current Milestone: v1.2 Account-Structure Mapping

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
- ✓ Niche Pulse sidecar — 7-day news harvest with trending themes + regulatory alerts — v1.0
- ✓ Account Data + Volume Enrichment sidecar — Ahrefs volume/CPC/KD + Google Ads search terms/perf/negatives sync — v1.0
- ✓ Editor CSV export (positives/negatives/ad_groups, Editor v2.x format) — v1.1
- ✓ Max-CPC bid suggestions (intent-weighted from Ahrefs CPC) — v1.1
- ✓ Budget forecast per cluster (low/mid/high bands, methodology disclaimer) — v1.1
- ✓ Operator Next Steps checklist (bespoke substitution + HTML localStorage checkboxes) — v1.1
- ✓ Compliance flags w/ CMPL-05 reorder (regulated-vertical verification at step 1) — v1.1

### Active

<!-- v1.2 scope. Building toward these. -->

- [ ] Geographic refinement via brief `geo_focus` list (counties/cities under top-level location)
- [ ] US cities/counties reference data file (operator-editable, JSON)
- [ ] SERP query geo-biasing + out-of-scope city filter at merge stage
- [ ] Ad-group mapping script reads existing account perf, maps our keywords to existing ad groups
- [ ] Match confidence per keyword (high/medium/low); unmapped fall back to cluster
- [ ] export_csv + Next Steps integrate mapping: respect existing structure when present

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

---
*Last updated: 2026-05-14 after milestone v1.2 start*
