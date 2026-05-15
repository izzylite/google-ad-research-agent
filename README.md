# Google Ad Research Agent

A [Claude Code](https://claude.com/claude-code) skill that turns one campaign brief into a campaign-ready Google Ads research package — ranked keyword tables, ad-group clusters, competitor ad copy + landing pages, tiered negative keywords, geo/account structure, bid + budget suggestions, compliance flags, and a Google Ads Editor CSV — in a single interactive Claude Code session.

```
brief in chat  →  ~10 min  →  report.html + report.md + report.json + Editor CSV
```

Built for in-house PPC operators and agency teams that want consistent, auditable keyword research without the 4-6 hours of manual cross-tabulation.

---

## Why this skill exists

Manual Google Ads keyword research is hours of:

- Tabbing between Google search, People Also Ask, and Related Searches
- Clicking through competitor sites to copy headlines, offers, CTAs
- Manually grouping keywords into ad groups in a spreadsheet
- Brainstorming negative keywords from scratch
- Cross-checking geo eligibility against your state/county target
- Estimating bids and daily budget against client CPA targets
- Flagging vertical-specific compliance (healthcare HIPAA, finance UDAP, etc.)
- Formatting everything into something a stakeholder can read

This skill compresses that into one guided session: paste a brief, answer a few clarifying questions, walk away with a production-ready research package. Same rubric every run, same scoring formula, same negative keyword categories, same compliance checks — two operators running the same brief get nearly identical output.

**Single-operator, filesystem-only.** No server. No UI. No multi-tenant. Lives entirely in your Claude Code session and your local `.runs/` folder.

---

## What it produces

Every run lands in a sealed dated folder under `.runs/`:

```
.runs/2026-05-15T102741Z-car-accident-injury-care-lake-worth/
├── brief.md                          ← verbatim operator brief
├── keywords.json                     ← canonicalised, deduped, source-attributed
├── ranked.json                       ← scored + 4-class intent-classified
├── intent-labels.json                ← LLM intent assignments
├── clusters.json                     ← intent-homogeneous ad groups (5-15 kw)
├── negatives.json                    ← tiered + categorised negatives
├── competitor-intel.json             ← per-cluster advertiser identity + ads
├── competitor-landing-pages.json     ← WebFetch-extracted headline/CTA/offer
├── niche-pulse.json                  ← time-sensitive news themes (optional)
├── volume-enrichment.json            ← Ahrefs MSV + difficulty (optional)
├── perf-context.json                 ← Google Ads MCC performance pull (optional)
├── bid-suggestions.json              ← per-keyword max CPC recommendations
├── forecast.json                     ← clicks/conv/spend bands per cluster
├── compliance-flags.json             ← vertical-specific policy alerts
├── ad-group-mapping.json             ← Editor-ready ad group + geo structure
├── report.md                         ← human-readable narrative
├── report.json                       ← stable v1 schema for automation
├── report.html                       ← interactive: sortable, filterable, CSV export
├── positives.csv                     ← Google Ads Editor paste-ready (keywords)
├── negatives.csv                     ← Google Ads Editor paste-ready (negatives)
└── raw/                              ← per-stage API dumps (audit trail, git-ignored)
    ├── serper.json
    ├── serper-news.json
    ├── websearch-baseline.json
    ├── competitor-intel.json
    └── ahrefs-*.json
```

The HTML report is the recommended deliverable — self-contained (no CDN), opens in any browser, has CSV-export buttons per section, and includes per-section "How to use" guidance so the operator knows what action to take with each list.

---

## How it works

The skill splits into two layers that communicate only through files in a sealed run folder.

**Layer 1 — Skill prompt (`SKILL.md` + `references/phaseN-*.md`).** A workflow Claude reads when triggered. Drives brief intake, generates seed keywords, performs LLM judgment work (intent classification, semantic clustering, value-prop extraction from landing pages via WebFetch, negative generation, compliance interpretation).

**Layer 2 — Python helper scripts (`scripts/*.py`).** Deterministic utilities that handle HTTP, JSON parsing, validation, scoring math, geo filtering, bid math, forecasting, and report rendering. Each script is self-provisioning via `uv run` and PEP 723 inline metadata — no shared environment to manage.

### Pipeline

| # | Phase | Output | Key files |
|---|-------|--------|-----------|
| 1 | Brief intake + run scaffold | `brief.md` | `run_init.py` |
| 2 | Signal collection (3 sources) | `keywords.json` | `serp_fetch.py`, `merge_signals.py` |
| 3 | Ranking + 4-class intent | `ranked.json` | `rank_keywords.py` |
| 4 | Clustering | `clusters.json` | `validate_clusters.py` |
| 5 | Competitor ads + landing pages | `competitor-{intel,landing-pages}.json` | `competitor_intel.py` + WebFetch |
| 6 | Negatives + report assembly | `report.{md,json,html}` | `generate_negatives.py`, `render_report.py`, `update_index.py` |
| 7 | Niche pulse (optional sidecar) | `niche-pulse.json` | `pulse_fetch.py`, `pulse_synth.py` |
| 8 | Volume + perf context (optional) | `volume-enrichment.json`, `perf-context.json` | `volume_enrich.py`, `perf_fetch.py`, `perf_synth.py` |
| 9 | Bid + forecast + compliance | `bid-suggestions.json`, `forecast.json`, `compliance-flags.json` | `bid_suggest.py`, `forecast_budget.py`, `compliance_check.py` |
| 10 | Operator launch kit (Editor CSVs) | `positives.csv`, `negatives.csv` | `export_csv.py` |
| 11 | Account-structure mapping | `ad-group-mapping.json` | `ad_group_match.py` |

Phases 7-11 are **sidecars** — operator opts in per-run. Phases 1-6 are the always-on core. Skill prompts you after Phase 6 to pick which sidecars to run.

### Signal sources

| Source | Role | Cost |
|--------|------|------|
| [WebSearch](https://docs.claude.com/en/docs/agents-and-tools/tool-use/web-search-tool) | Free baseline (Claude Code built-in) | $0 |
| [Serper.dev](https://serper.dev/) | Structured Google SERP — organic, PAA, related, ads, news | ~$0.001/query |
| **WebFetch** (Claude built-in) | Landing-page extract — headline / CTA / offer | $0 |
| [Ahrefs API](https://ahrefs.com/api) (Phase 8, optional) | Real MSV + keyword difficulty | metered |
| [Google Ads API](https://developers.google.com/google-ads/api) (Phase 8, optional) | Account-level performance context | $0 |

**Paid surface is intentionally minimal.** Landing-page extraction uses Claude's built-in WebFetch ($0). News harvest uses Serper `/news`. Single paid API in the core pipeline (Serper); Ahrefs + Google Ads opt-in for Phase 8 enrichment.

### Score formula

```
score = source_diversity × 100 + intent_weight + signal_count
```

Multi-source agreement dominates ranking. `signal_count` is **not** search volume — it's the count of source fragments that mentioned the keyword. For real MSV + CPC, opt into Phase 8 (Ahrefs) or paste the final keyword list into [Google Keyword Planner](https://ads.google.com/aw/keywordplanner).

---

## Installation

### Prerequisites

- [Claude Code](https://docs.claude.com/en/docs/claude-code) (CLI, desktop, IDE extension, or web)
- [`uv`](https://docs.astral.sh/uv/) ≥ 0.4 — handles all Python deps via PEP 723
- Python ≥ 3.11
- API keys:
  - **[Serper.dev](https://serper.dev/)** — required. ~$50/mo for 50k queries; ~$0.20 per full run
  - **[Ahrefs API](https://ahrefs.com/api)** — optional (Phase 8 volume enrichment)
  - **[Google Ads API](https://developers.google.com/google-ads/api)** — optional (Phase 8 performance context)

### Setup

```bash
git clone https://github.com/izzylite/google-ad-research-agent.git
cd google-ad-research-agent
cp .env.example .env
```

Edit `.env`:

```
SERPER_API_KEY=...
# Optional Phase 8 enrichment:
# AHREFS_API_TOKEN=...
# GOOGLE_ADS_DEVELOPER_TOKEN=...
# GOOGLE_ADS_CLIENT_ID=...
# GOOGLE_ADS_CLIENT_SECRET=...
# GOOGLE_ADS_REFRESH_TOKEN=...
# GOOGLE_ADS_LOGIN_CUSTOMER_ID=...
```

That's it. The skill is at `.claude/skills/google-ad-research/` and Claude Code auto-discovers project-scoped skills when you launch a session in this directory.

### Verify

```bash
uv run --project .claude/skills/google-ad-research/scripts \
  --with pytest --with respx --with python-dotenv --with python-slugify \
  --with tabulate --with inflect \
  pytest .claude/skills/google-ad-research/scripts/tests/ -q
```

Expect **250 passed, 0 failed, 0 skipped** at v1.3.

---

## Usage

Open Claude Code in this directory and paste a brief. The skill activates on phrases like *"keyword research"*, *"Google Ads research"*, *"PPC keywords"*, *"ad group clusters"*, or any campaign brief that mentions industry / product / location / language / audience.

### Example session

```
> I'm running a Google Ads campaign for an urgent care clinic in Lake Worth FL,
> targeting recent car accident victims. Want keyword research + competitor intel.

[Skill activates]
> I need a language to target. (e.g., 'en-US')

> en-US

[Skill confirms 5 required fields, asks one optional follow-up]
[Generates 12 seed keywords, calls WebSearch + Serper, merges signals,
 classifies intent, clusters into ad groups, runs competitor_intel.py
 for ads block, WebFetches top advertisers per cluster for headline/CTA/offer,
 generates negatives, renders report.{md,json,html}, updates .runs/INDEX.md]

> Run folder: .runs/2026-05-15T102741Z-car-accident-injury-care-services-lake-worth/
> Keywords: 87 (44 commercial, 31 navigational, 12 informational, 0 transactional)
> Clusters: 14 (validator: 5 undersize warnings, accepted)
> Negatives: 31 (Strong 15, Considered 8, Investigate 8)
> Top 3 by score: urgent care lake worth (226), urgent care royal palm beach (123),
>                 auto accident chiropractor lake worth fl (122)
> Serper credits used: 26
> WebFetch: 19 OK / 5 failed (JS/bot-blocked — fallback applied)
> Geo filter: dropped 44 keywords (wrong state) + 2 (wrong PB-county city)
> Open report.html for interactive view.
>
> Phase 7-11 sidecars (Niche Pulse, Account Data, Economics, Launch Kit,
> Account Mapping) optional — say which to run.
```

### Optional sidecars (run after the core)

| Sidecar | What it adds | When to run |
|---------|--------------|-------------|
| **Phase 7 — Niche Pulse** | Trending news themes, regulatory alerts, competitor news, time-sensitive negative candidates | Weekly refresh; before launch in volatile niches (insurance, healthcare, finance) |
| **Phase 8 — Account Data + Volume** | Ahrefs MSV + difficulty per keyword; Google Ads MCC performance baseline (avg CPC, CTR, conv rate) | When client provides Ahrefs / Ads MCC access |
| **Phase 9 — Economics + Compliance** | Max-CPC suggestions (from intent × baseline CPC × bid multipliers), daily budget forecast (low/mid/high), vertical compliance flags (HIPAA, finance UDAP, employment EEO, etc.) | Always before launch |
| **Phase 10 — Operator Launch Kit** | Google Ads Editor-paste CSVs (positives + negatives), Next-Steps checklist with daily budget + max-CPC pre-filled | Always before launch |
| **Phase 11 — Account-Structure Mapping** | Geo eligibility filter (state/county/city), ad-group structure suggestion with bid modifiers | Local-services and geo-targeted campaigns |

### Cost per run

| Phase | API | Typical cost |
|-------|-----|--------------|
| 2: Signal collection | Serper × ~12 | ~$0.012 |
| 5: Competitor intel | Serper × N clusters | ~$0.02 |
| 5: Landing-page extract | WebFetch (Claude built-in) | $0 |
| 7: Niche pulse (optional) | Serper /news × ~10 | ~$0.01 |
| 8: Volume enrichment (optional) | Ahrefs API | metered |
| 8: Perf context (optional) | Google Ads API | $0 |
| **Core total (Phases 1-6)** | | **~$0.03 / run** |
| **+ all sidecars except Ahrefs** | | **~$0.05 / run** |

---

## Architecture

```
SKILL.md (operator-facing prompt — ≤500 lines)
   │ Bash / Read / Write / WebSearch / WebFetch
   ▼
references/                          ← progressive-disclosure rubrics
├── phase5-competitor-intel.md       ← Serper ads + WebFetch landing pages
├── phase6-negatives-report.md       ← negative categories + report schema
├── phase7-niche-pulse.md            ← news theme synthesis
├── phase8-account-data.md           ← Ahrefs + Google Ads pulls
├── phase9-economics-compliance.md   ← bid math + forecast + compliance
├── phase10-operator-launch-kit.md   ← Editor CSV + Next-Steps
├── phase11-account-structure-mapping.md  ← geo + ad-group structure
├── compliance-verticals.json        ← vertical → policy rules
└── us-cities.json                   ← state/county/city eligibility data

scripts/
├── lib/                             ← shared modules
│   ├── config.py     load_env, REQUIRED_KEYS=("SERPER_API_KEY",)
│   ├── io.py         slugify, iso_timestamp, escape_md_cell
│   ├── http.py       httpx + httpx-retries client factory
│   ├── canon.py      inflect singularization + lemma_hash
│   └── log.py        stderr logger
│
├── run_init.py            seal run folder + verbatim brief
├── serp_fetch.py          Serper REST: organic + PAA + related + ads
├── merge_signals.py       dedup, canonicalize, source-attribute (5 sources)
├── rank_keywords.py       composite scoring + match-type heuristic
├── validate_clusters.py   enforce intent-homogeneity + size invariants
├── competitor_intel.py    per-cluster ads → organic fallback (Serper-only)
├── generate_negatives.py  enum validator + dedup vs positives
├── render_report.py       report.md + report.json + report.html (with WebFetch JOIN)
├── update_index.py        append .runs/INDEX.md row
│
├── pulse_fetch.py         Phase 7: Serper /news (single-source post-Phase-12)
├── pulse_synth.py         Phase 7: theme cluster + regulatory tag
│
├── volume_enrich.py       Phase 8: Ahrefs MSV + difficulty
├── perf_fetch.py          Phase 8: Google Ads MCC pull
├── perf_synth.py          Phase 8: MCC baseline metrics
│
├── bid_suggest.py         Phase 9: per-keyword max CPC
├── forecast_budget.py     Phase 9: low/mid/high spend bands
├── compliance_check.py    Phase 9: vertical compliance flags
│
├── export_csv.py          Phase 10: Editor-ready positives/negatives CSV
└── ad_group_match.py      Phase 11: geo eligibility + ad-group structure

.runs/                                ← per-run sealed folders
├── INDEX.md                          ← browsable run history
└── <ISO>-<slug>/
    ├── brief.md
    ├── *.json (12+ output files)
    ├── *.csv (Editor paste)
    ├── report.{md,json,html}
    └── raw/                          ← git-ignored API dumps
```

**Boundary rule:** scripts handle I/O + math + validation. Claude (LLM) handles judgment — seed generation, intent classification, semantic clustering, landing-page value-prop extraction (via WebFetch), negative generation, compliance interpretation. They communicate via files in the run folder. No IPC. No shared mutable state.

---

## Project layout

```
.
├── .claude/skills/google-ad-research/    ← the skill (project-scoped)
│   ├── SKILL.md                          ← operator workflow, ≤500 lines
│   ├── scripts/                          ← 19 helper scripts + lib/
│   └── references/                       ← phase-specific rubrics
├── .planning/                            ← GSD planning artifacts
│   ├── PROJECT.md                        ← project context, scope, key decisions
│   ├── ROADMAP.md                        ← 12 phases, completion status
│   ├── REQUIREMENTS.md                   ← 89 requirements traced to phases
│   ├── STATE.md                          ← current position, decisions, history
│   ├── research/                         ← stack + features + architecture + pitfalls
│   └── phases/                           ← per-phase RESEARCH/PLAN/VERIFICATION
├── .runs/                                ← per-run output (raw/ git-ignored)
├── .env.example                          ← copy to .env
├── CLAUDE.md                             ← Claude Code project conventions
└── README.md                             ← this file
```

---

## Limitations & honest tradeoffs

1. **No real search volume in the core.** Phases 1-6 rank on `source_diversity` × intent × `signal_count` — a popularity proxy, not Google's actual data. Phase 8 (opt-in) adds Ahrefs MSV. Otherwise paste the final keyword list into Keyword Planner for volume + CPC.
2. **Brief quality drives output quality.** A vague brief produces vague keywords. Five required fields (industry, product, location, language, audience) are enforced for a reason.
3. **Serper ads block is unreliable in some verticals.** Healthcare and several others return 0 ads even when Google clearly shows them. The competitor intel script falls back to top organic results — those landing pages contain the same value props paid advertisers would highlight, so the downstream analysis still works.
4. **WebFetch can fail on JS-heavy or bot-blocked sites.** Typical success rate ~80% in production runs. The `competitor-landing-pages.json` schema includes `extract_status` so failures are visible; `report.md` shows fallback text per failed advertiser.
5. **Niche pulse themes have noise.** N-gram clustering surfaces some news-source bylines and reporter names. Stop-token list filters most; the Highlights block at the top of the section is curated to high-priority items only.
6. **Single-operator design.** No multi-tenant, no auth, no shared state. The skill expects one PPC operator running it for in-house or solo agency campaigns. Productizing for end clients is out of scope for v1.

---

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — Claude Code project conventions (skill location, secret discipline, run-folder rules)
- [`.planning/PROJECT.md`](.planning/PROJECT.md) — project context, scope, key decisions
- [`.planning/ROADMAP.md`](.planning/ROADMAP.md) — 12 phases + completion status
- [`.planning/REQUIREMENTS.md`](.planning/REQUIREMENTS.md) — every requirement (89 v1) traced to a phase
- [`.planning/research/SUMMARY.md`](.planning/research/SUMMARY.md) — domain research synthesis
- [`.planning/research/PITFALLS.md`](.planning/research/PITFALLS.md) — pitfalls + mitigations
- [`.claude/skills/google-ad-research/SKILL.md`](.claude/skills/google-ad-research/SKILL.md) — operator workflow

---

## Milestone history

| Milestone | Scope | Status |
|-----------|-------|--------|
| **v1.0** | Phases 1-7 — core pipeline + Niche Pulse | Shipped 2026-05-08 |
| **v1.1** | Phases 8-10 — Account Data + Volume, Economics, Launch Kit | Shipped 2026-05-14 |
| **v1.2** | Phase 11 — Account-Structure Mapping | Shipped 2026-05-15 |
| **v1.3** | Phase 12 — Source Consolidation | Shipped 2026-05-15 |

**89/89 requirements complete.** Full test suite: 250 passed.

---

## Roadmap (post-v1.3)

| Item | Status |
|------|--------|
| Composite ranking weight calibration (after 3-5 real runs) | v1.4 candidate |
| Match-type recommendation conservatism re-tune | v1.4 candidate |
| FRCS avg-CPC ratio + band spread calibration | v1.4 candidate |
| Niche-pulse threshold re-tune (single-source post-Phase-12) | v1.4 candidate |
| SERP cache by query hash to reduce repeat API spend | v2 |
| Run-diff script comparing two runs by `report.json` | v2 |
| Multi-locale fan-out (one brief, multiple country/language reports) | v2 |

---

## Tech stack

- **Runtime:** Python ≥ 3.11 via [`uv`](https://docs.astral.sh/uv/) ≥ 0.4 with PEP 723 inline script metadata
- **HTTP:** [`httpx`](https://www.python-httpx.org/) 0.28 + [`httpx-retries`](https://github.com/will-ockmore/httpx-retries) 0.5
- **APIs:** [Serper.dev](https://serper.dev/) (REST), [Ahrefs API](https://ahrefs.com/api) (optional), [Google Ads API](https://developers.google.com/google-ads/api) (optional)
- **Built-in Claude tools:** WebSearch (free baseline), WebFetch (landing-page extract)
- **Text processing:** [`inflect`](https://github.com/jaraco/inflect) 7.5 (singularization), [`python-slugify`](https://github.com/un33k/python-slugify) 8
- **Reports:** [`tabulate`](https://github.com/astanin/python-tabulate) 0.9 (markdown), self-contained vanilla JS for HTML
- **Secrets:** [`python-dotenv`](https://github.com/theskumar/python-dotenv) 1.0
- **Tests:** `pytest` 9 + `respx` (httpx mocking)
- **Logging:** stdlib `logging` + [`rich`](https://github.com/Textualize/rich) `RichHandler`

---

## License

[Add your license — MIT, Apache 2.0, or proprietary depending on use case.]

---

## Acknowledgments

Built using the [GSD (Get Shit Done) methodology](https://github.com/get-shit-done/get-shit-done) for phase-driven greenfield projects with goal-backward verification at every step. 12 phases, 89 requirements, 250 tests, 4 milestones — all driven from one campaign-brief-to-research-package contract.
