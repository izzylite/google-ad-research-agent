# Google Ad Research Agent

A [Claude Code](https://claude.com/claude-code) skill that turns one campaign brief into a campaign-ready Google Ads research package — ranked keyword tables, ad-group clusters, competitor ad copy + landing pages, tiered negative keywords, geo/account structure, bid + budget suggestions, compliance flags, and a Google Ads Editor CSV — in a single interactive Claude Code session.

```
brief in chat  →  ~10 min  →  report.html + report.md + report.json + Editor CSV
```

Built as an **internal team tool** — single-operator, filesystem-only, no multi-tenant. Designed for a PPC team that wants consistent, auditable keyword research without the 4-6 hours of manual cross-tabulation. Not a commercial product.

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
├── ranked-enriched.json              ← ranked.json + Ahrefs MSV/CPC/KD + Phase 9
│                                       suggested_max_cpc_micros (Phase 8+9)
├── account-perf.json                 ← Google Ads MCC performance pull (Phase 8)
├── negatives-sync.json               ← generated vs existing-account negatives (Phase 8)
├── forecast.json                     ← clicks/conv/spend low-mid-high bands (Phase 9)
├── compliance-flags.json             ← vertical policy alerts (Phase 9)
├── ad-group-mapping.json             ← geo eligibility + ad-group structure (Phase 11)
├── report.md                         ← human-readable narrative
├── report.json                       ← stable v1 schema for automation
├── report.html                       ← interactive: sortable, filterable, CSV export
├── export/                           ← Google Ads Editor paste-ready (Phase 10)
│   ├── positives.csv                 ← keywords with Max CPC, match-type
│   ├── negatives.csv                 ← tiered negatives
│   └── ad_groups.csv                 ← ad-group structure
└── raw/                              ← per-stage API dumps (audit trail, git-ignored)
    ├── serper.json
    ├── serper-news.json
    ├── websearch-baseline.json
    ├── competitor-intel.json
    ├── google-ads-perf.json
    ├── google-ads-search-terms.json
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
| 8 | Volume + perf context (optional) | `ranked-enriched.json`, `account-perf.json`, `negatives-sync.json` | `volume_enrich.py`, `perf_fetch.py`, `perf_synth.py` |
| 9 | Bid + forecast + compliance | `ranked-enriched.json` (+suggested_max_cpc_micros), `forecast.json`, `compliance-flags.json` | `bid_suggest.py`, `forecast_budget.py`, `compliance_check.py` |
| 10 | Operator launch kit (Editor CSVs) | `export/{positives,negatives,ad_groups}.csv` | `export_csv.py` |
| 11 | Account-structure mapping | `ad-group-mapping.json` | `ad_group_match.py` |
| 14 | Positives sync (existing-keyword dedup) | `positives-sync.json` | `merge_signals.py`, `perf_synth.py` |
| 15 | Campaign focus (narrow to target campaign) | `account-perf.json` (filtered) | `perf_synth.py` |
| 16 | Token-bag enrichment + per-source max-Jaccard | `ad-group-mapping.json` (enriched matches) | `ad_group_match.py` |

Phases 8-11 + 14-16 **auto-run when prerequisites are present** (Ahrefs + Google Ads creds in `.env`, geo focus in brief). Phases 1-6 are the always-on core. No per-phase prompts — skill announces explicit skip + reason when a phase can't run.

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
  - **[Serper.dev](https://serper.dev/)** — required. Free tier ships with **2,500 credits on signup** (~80-100 internal runs) — covers internal-team usage indefinitely. Paid tier only if you exhaust free credits.
  - **[Ahrefs API](https://ahrefs.com/api)** — required for Phase 8 (real volume/CPC/KD). Phase 9 + Phase 10 (Launch Kit Editor CSVs) chain off Phase 8, so this is effectively required for launch-ready output.
  - **[Google Ads API](https://developers.google.com/google-ads/api)** — required for Phase 8 (account performance pull) and Phase 11 (existing-ad-group preservation). Free quota.

### Setup

```bash
git clone https://github.com/izzylite/google-ad-research-agent.git
cd google-ad-research-agent
cp .env.example .env
```

Edit `.env`:

```
SERPER_API_KEY=...
AHREFS_API_TOKEN=...
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=...
```

All keys are needed for the full pipeline (Phases 1-11). Skill will run core Phases 1-6 with Serper alone but skip Phase 8-10 and Phase 11's existing-ad-group preservation if Ahrefs / Google Ads creds are missing.

That's it. The skill is at `.claude/skills/google-ad-research/` and Claude Code auto-discovers project-scoped skills when you launch a session in this directory.

### Verify

```bash
uv run --project .claude/skills/google-ad-research/scripts \
  --with pytest --with respx --with python-dotenv --with python-slugify \
  --with tabulate --with inflect \
  pytest .claude/skills/google-ad-research/scripts/tests/ -q
```

Expect **283 passed, 0 failed** at v1.5.

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
> Phases 8-11 auto-ran (Account Data, Economics, Launch Kit, Account Mapping)
> — all prereqs in .env. No further prompts.
```

### Phase 8-11 + 14-16: default behavior

All auto-run when prerequisites are present in `.env` + brief. No prompts. Skill announces explicit skip + reason if a phase can't run.

| Phase | Default | Auto-run trigger | What it adds |
|-------|---------|------------------|--------------|
| **8 — Account Data + Volume** | **Auto-run** | `AHREFS_API_KEY` AND Google Ads OAuth creds in `.env` | Ahrefs MSV + CPC + Keyword Difficulty (`ranked-enriched.json`); Google Ads MCC performance baseline (`account-perf.json`); existing-account negatives sync (`negatives-sync.json`). |
| **9 — Economics + Compliance** | **Auto-run** | Phase 8 produced `cpc_micros` | Max CPC per keyword (mutated into `ranked-enriched.json`), budget forecast bands (`forecast.json`), vertical compliance flags (`compliance-flags.json`). Pure compute. |
| **10 — Operator Launch Kit** | **Auto-run** | Phase 9 completed | `{run}/export/` Editor v2.x CSVs: `positives.csv` (with Max CPC), `negatives.csv` (tiered), `ad_groups.csv`. Next-Steps checklist with daily budget + Max CPC pre-filled. |
| **11 — Account-Structure Mapping** | **Auto-run** | Brief has `Geo focus:` field OR Phase 8 produced account data | Geo eligibility filter (state/county/city — drops out-of-area keywords), existing-ad-group preservation (skill won't re-create ad groups your account already has). |
| **14 — Positives Sync** | **Auto-run** | Phase 8 produced account keyword data | Deduplicates suggested keywords against the existing account positives (`positives-sync.json`) — operator only sees genuinely new keywords. |
| **15 — Campaign Focus** | **Auto-run** | Brief has `Campaign focus:` field | Narrows Phase 8 account pull to one target campaign — sharper threshold calibration, less noise from off-target ad groups. |
| **16 — Token-Bag Enrichment** | **Auto-run** | Phase 14 OAuth keywords pulled | Per-source max-Jaccard scoring (AG name ∪ kw_criteria ∪ search-terms tokens) — lifts mapping coverage to 50%+ on short-name-AG accounts (was 0% pre-Phase-16). |

**To get the full pipeline by default**, set all 7 keys in `.env`. Skill announces a skip + reason whenever a phase can't run. No silent skips, no per-phase prompts.

### Credits per run

| Phase | Source | Cost |
|-------|--------|------|
| 2: Signal collection | Serper × ~12 | 12 credits |
| 5: Competitor intel | Serper × N clusters | ~14 credits |
| 5: Landing-page extract | WebFetch (Claude built-in) | $0 |
| 8: Volume enrichment | Ahrefs API | ~73 units |
| 8: Perf context | Google Ads API | free quota |
| **Total Serper per run** | | **~26 credits** |

Serper free tier = **2,500 credits**. At ~26 credits/run that's ~95 runs free — comfortably covers internal-team usage. No paid plan required for normal volume.

---

## Architecture

```
SKILL.md (operator-facing prompt — ≤500 lines)
   │ Bash / Read / Write / WebSearch / WebFetch
   ▼
references/                          ← progressive-disclosure rubrics
├── phase5-competitor-intel.md       ← Serper ads + WebFetch landing pages
├── phase6-negatives-report.md       ← negative categories + report schema
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
│   ├── ROADMAP.md                        ← 14 active phases (Phase 7 removed, Phase 13 backlog), completion status
│   ├── REQUIREMENTS.md                   ← 107 requirements traced to phases
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

1. **Real volume + CPC requires Phase 8 (Ahrefs).** Core Phases 1-6 rank on `source_diversity` × intent × `signal_count` — a popularity proxy designed to work without paid volume data. Phase 8 (opt-in, needs `AHREFS_API_KEY`) adds real Ahrefs MSV, CPC, and Keyword Difficulty per keyword and is the prerequisite for Phase 9 bid suggestions + Phase 10 Editor CSVs. Without Phase 8, paste the final keyword list into Keyword Planner manually for volume + CPC.
2. **Brief quality drives output quality.** A vague brief produces vague keywords. Five required fields (industry, product, location, language, audience) are enforced for a reason.
3. **Serper ads block is unreliable in some verticals.** Healthcare and several others return 0 ads even when Google clearly shows them. The competitor intel script falls back to top organic results — those landing pages contain the same value props paid advertisers would highlight, so the downstream analysis still works.
4. **WebFetch can fail on JS-heavy or bot-blocked sites.** Typical success rate ~80% in production runs. The `competitor-landing-pages.json` schema includes `extract_status` so failures are visible; `report.md` shows fallback text per failed advertiser.
5. **Single-operator design.** No multi-tenant, no auth, no shared state. The skill expects one PPC operator running it for in-house team campaigns. Productizing for end clients is out of scope.

---

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — Claude Code project conventions (skill location, secret discipline, run-folder rules)
- [`.planning/PROJECT.md`](.planning/PROJECT.md) — project context, scope, key decisions
- [`.planning/ROADMAP.md`](.planning/ROADMAP.md) — 14 active phases + completion status
- [`.planning/REQUIREMENTS.md`](.planning/REQUIREMENTS.md) — every requirement (107 v1) traced to a phase
- [`.planning/research/SUMMARY.md`](.planning/research/SUMMARY.md) — domain research synthesis
- [`.planning/research/PITFALLS.md`](.planning/research/PITFALLS.md) — pitfalls + mitigations
- [`.claude/skills/google-ad-research/SKILL.md`](.claude/skills/google-ad-research/SKILL.md) — operator workflow

---

## Milestone history

| Milestone | Scope | Status |
|-----------|-------|--------|
| **v1.0** | Phases 1-6 — core pipeline (Phase 7 Niche Pulse shipped here, removed post-v1.3) | Shipped 2026-05-08 |
| **v1.1** | Phases 8-10 — Account Data + Volume, Economics, Launch Kit | Shipped 2026-05-14 |
| **v1.2** | Phase 11 — Account-Structure Mapping | Shipped 2026-05-15 |
| **v1.3** | Phase 12 — Source Consolidation (drop Tavily) | Shipped 2026-05-15 |
| **v1.4** | Phase 14 — Positives Sync (existing-keyword dedup) | Shipped 2026-05-15 |
| **v1.5** | Phases 15-16 — Campaign Focus + Ad-Group Token-Bag Enrichment | Shipped 2026-05-15 |

**107/107 requirements complete.** Full test suite: 283 passed.

---

## Roadmap (post-v1.5)

| Item | Status |
|------|--------|
| Second-account calibration of Phase 16 `{high: 0.30, medium: 0.08}` thresholds | watch-item |
| Shape-contract smoke test between `perf_fetch.py` output and downstream consumers | watch-item |
| Phase 13 — Landing-Page Extract vendor swap | backlog (defer-until-friction) |
| Composite ranking weight calibration (after 3-5 real runs) | v2 candidate |
| Match-type recommendation conservatism re-tune | v2 candidate |
| FRCS avg-CPC ratio + band spread calibration | v2 candidate |
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

Built using the [GSD (Get Shit Done) methodology](https://github.com/get-shit-done/get-shit-done) for phase-driven greenfield projects with goal-backward verification at every step. 14 active phases, 107 requirements, 283 tests, 6 milestones — all driven from one campaign-brief-to-research-package contract.
