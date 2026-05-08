# Google Ad Research Agent

## What This Is

Internal Claude Code skill for a centralized PPC operator. Operator pastes a campaign brief in a Claude Code session; the skill asks clarifying questions, runs keyword research via WebSearch + Serper.dev + Tavily, and produces a markdown report with a ranked keyword table, ad group clusters, competitor ad copy, and negative keyword candidates. The operator distributes results to the rest of the PPC team.

## Core Value

From one campaign brief, deliver campaign-ready keyword research — clusters, competitor intel, and negatives — in a single Claude Code session, without the operator leaving the chat.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Conversational brief intake — skill prompts operator for missing context (industry, product, location, language, audience, budget signal) instead of expecting a filled template
- [ ] Seed keyword expansion via Serper.dev SERP signals (organic results, People Also Ask, related searches)
- [ ] Competitor / landing page mining via Tavily (extract value props, terminology, offers from competitor sites)
- [ ] WebSearch as zero-cost baseline signal alongside Serper/Tavily
- [ ] Ranking by frequency-of-occurrence + LLM-scored commercial intent (no volume/CPC API in v1)
- [ ] Ad group clustering — keywords pre-grouped by theme, ready to paste into Google Ads ad groups
- [ ] Competitor ad copy extraction from Serper ad block (top paid headlines + descriptions per theme)
- [ ] Negative keyword candidate list
- [ ] Markdown report output containing all four sections (table, clusters, ad copy, negatives)
- [ ] Run history folder — each run = dated subfolder containing brief + report, browsable for past work
- [ ] Generic engine usable across verticals (no vertical-specific presets in v1)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Volume / CPC / competition metrics from a paid data API (DataForSEO, Google Ads API) — v1 ranks on frequency + LLM intent; volume enrichment is manual via Keyword Planner. Revisit in v2.
- Vertical presets (ecommerce / SaaS / lead gen / local) — defer to v2 once real usage shows which verticals matter.
- Web dashboard / UI — markdown report is the deliverable; building a UI duplicates Claude Code chat without adding value for a single operator.
- Multi-tenant or auth — single internal operator model, no per-user state needed.
- Auto-push to Google Ads (API or Editor CSV import format) — operator pastes results manually; pushing risks bad data going live.
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
| Markdown report (no CSV, no dashboard) | Operator reads in Claude Code; markdown tables paste cleanly into docs/Slack; CSV deferrable if Google Ads import becomes a need | — Pending |

---
*Last updated: 2026-05-08 after initialization*
