# Google Ad Research Agent

A [Claude Code](https://claude.com/claude-code) skill that turns one campaign brief into campaign-ready Google Ads keyword research — ranked keyword tables, ad-group clusters, competitor ad copy, tiered negative keywords, and a time-sensitive niche pulse — in a single 10-minute interactive session.

```
brief in chat  →  10 min  →  CSV-exportable report.html + report.md + report.json
```

Built for in-house PPC operators and agency teams that want consistent, auditable keyword research without the 4-6 hours of manual cross-tabulation.

---

## Why this exists

Manual Google Ads keyword research means:

- Tabbing between Google search, People Also Ask, and Related Searches
- Clicking through competitor sites to copy their headlines and offers
- Manually grouping keywords into ad groups in a spreadsheet
- Brainstorming negative keywords from scratch
- Formatting everything into something a stakeholder can read

This skill compresses that into a guided session: paste a brief, answer a few clarifying questions, walk away with a production-ready research package. Same rubric every run, same scoring formula, same negative keyword categories — two operators running the same brief get nearly identical output.

---

## What it produces

Every run lands in a sealed dated folder under `.runs/`:

```
.runs/2026-05-08T143024Z-grocery-delivery-uk/
├── brief.md                      ← verbatim operator brief
├── keywords.json                 ← canonicalised, deduped, source-attributed
├── ranked.json                   ← scored + intent-classified
├── intent-labels.json            ← LLM-assigned 4-class intent
├── clusters.json                 ← intent-homogeneous ad groups (5-15 kw each)
├── negatives.json                ← validated tier + category negatives
├── niche-pulse.json              ← time-sensitive news signals (Phase 7)
├── report.md                     ← human-readable narrative
├── report.json                   ← stable v1 schema for downstream automation
├── report.html                   ← interactive: sortable, filterable, CSV export
└── raw/                          ← per-stage API dumps (audit trail)
    ├── serper.json
    ├── tavily-<domain>.json
    ├── websearch-baseline.json
    ├── serper-news.json
    ├── tavily-news.json
    └── competitor-intel.json
```

The HTML report is the recommended deliverable — self-contained (no CDN), opens in any browser, has CSV-export buttons per section, and includes per-section "How to use" guidance so the operator knows what action to take with each list.

---

## How it works

The skill is split into two layers that communicate only through files in a sealed run folder.

**Layer 1 — Skill prompt (`SKILL.md`).** A workflow that Claude reads when triggered. Drives the brief intake dialogue, generates seed keywords, performs LLM-only judgment work (intent classification, semantic clustering, value-prop extraction, negative generation).

**Layer 2 — Python helper scripts (`scripts/*.py`).** Deterministic utilities that handle HTTP calls, JSON parsing, validation, scoring math, and report rendering. Each script is self-provisioning via `uv run` and PEP 723 inline metadata — no shared environment to manage.

**Pipeline (7 phases):**

| # | Phase | Output | Key files |
|---|-------|--------|-----------|
| 1 | Skill scaffold + brief intake | `brief.md` | `run_init.py` |
| 2 | Signal collection (3 sources) | `keywords.json` | `serp_fetch.py`, `tavily_extract.py`, `merge_signals.py` |
| 3 | Ranking + intent | `ranked.json` | `rank_keywords.py` |
| 4 | Clustering | `clusters.json` | `validate_clusters.py` |
| 5 | Competitor ad copy + LP | `competitor-intel.json` | `competitor_intel.py` |
| 6 | Negatives + report assembly | `report.{md,json,html}` | `generate_negatives.py`, `render_report.py`, `update_index.py` |
| 7 | Niche pulse (sidecar) | `niche-pulse.json` | `pulse_fetch.py`, `pulse_synth.py` |

**Three signal sources, three roles:**

- [WebSearch](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool) — free baseline, Claude Code built-in
- [Serper.dev](https://serper.dev/) — structured Google SERP (organic, People Also Ask, related searches, ads block)
- [Tavily](https://tavily.com/) — deep content extraction from competitor landing pages, plus news harvest for niche pulse

**Score formula:** `score = source_diversity × 100 + intent_weight + signal_count`. Multi-source agreement dominates. `signal_count` is **not** search volume — it's the count of source fragments that mentioned the keyword. Paste keywords into [Google Keyword Planner](https://ads.google.com/aw/keywordplanner) for actual volume + CPC.

---

## Installation

### Prerequisites

- [Claude Code](https://docs.claude.com/en/docs/claude-code) (CLI, desktop, IDE extension, or web)
- [`uv`](https://docs.astral.sh/uv/) ≥ 0.4 — handles all Python deps via PEP 723
- Python ≥ 3.11
- API keys:
  - [Serper.dev](https://serper.dev/) — ~$50/mo for 50k queries
  - [Tavily](https://tavily.com/) — free tier covers ~100 runs/mo

### Setup

```bash
git clone https://github.com/izzylite/google-ad-research-agent.git
cd google-ad-research-agent
cp .env.example .env
```

Edit `.env`:

```
TAVILY_API_KEY=tvly-...
SERPER_API_KEY=...
```

That's it. The skill is at `.claude/skills/google-ad-research/` and Claude Code auto-discovers project-scoped skills when you launch a session in this directory.

### Verify

```bash
# Run the test suite
uv run --quiet --with pytest --with python-dotenv --with python-slugify \
  --with respx --with httpx --with httpx-retries --with tavily-python \
  --with inflect --project .claude/skills/google-ad-research/scripts \
  pytest .claude/skills/google-ad-research/scripts/tests/ -q
```

Expect ~90 tests passing, ~10 skipped (network-dependent).

---

## Usage

Open Claude Code in this directory and paste a brief. The skill activates on phrases like "keyword research", "Google Ads research", "PPC keywords", or any campaign brief mentioning industry / product / location / language / audience.

### Example session

```
> I'm running a Google Ads campaign for an urgent care clinic in Lake Worth FL,
> targeting recent car accident victims. Want keyword research and competitor intel.

[Skill activates]
> I still need language. What should I use? (e.g., 'en-US', 'es-US')

> en-US, also target Spanish

[Skill confirms 5 required fields, asks one optional follow-up]
[Generates 12 seed keywords, calls WebSearch + Serper, runs Tavily on competitors,
 merges signals, classifies intent, clusters into ad groups, extracts competitor
 LPs, generates negatives, renders report.md + report.json + report.html,
 updates .runs/INDEX.md]

> Run folder: .runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/
> 101 keywords ranked across 14 clusters
> 47 negative keywords across 3 tiers
> 70 competitor landing pages extracted
> Open report.html for the interactive view.
```

### Niche Pulse (optional)

After the main report, the skill can run a separate news harvest:

```
> Run niche pulse?

[Calls Serper /news + Tavily news search across 10 seeds, last 7 days]
[Synthesizes trending themes, regulatory alerts, competitor news, trending negatives]
[Re-renders report with embedded Niche Pulse section + highlights]

> 30 trending themes, 74 regulatory alerts, 41 trending negative candidates.
> Top highlight: "Florida Lawmakers Did Not Repeal No-Fault Auto Insurance Law"
> — directly affects PIP keyword bidding.
```

Run weekly to refresh time-sensitive signals without re-running the full pipeline.

### Cost per run

| Phase | API | Cost |
|-------|-----|------|
| 2: Signal collection | Serper × 12 + Tavily extract × ~20 | ~$0.05 |
| 5: Competitor intel | Serper × N clusters + Tavily × N×5 | ~$0.10 |
| 7: Niche pulse | Serper × 10 + Tavily news × 10 | ~$0.02 |
| **Total** | | **~$0.20 per full run** |

---

## Architecture

```
SKILL.md (operator-facing prompt)
   │ Bash / Read / Write / WebSearch
   ▼
scripts/
├── lib/                              ← shared modules
│   ├── config.py    load_env, REQUIRED_KEYS
│   ├── io.py        slugify, iso_timestamp, escape_md_cell
│   ├── http.py      httpx + httpx-retries client factory
│   ├── canon.py     inflect singularization, lemma_hash
│   └── log.py       stderr logger
│
├── run_init.py            seal run folder + verbatim brief
├── serp_fetch.py          Serper REST: organic + PAA + related + ads
├── tavily_extract.py      Tavily SDK: per-competitor LP extract
├── merge_signals.py       dedup, canonicalize, source-attribute
├── rank_keywords.py       composite scoring + match-type heuristic
├── validate_clusters.py   enforce intent-homogeneity + size invariants
├── competitor_intel.py    per-cluster ads → organic fallback → Tavily LP
├── generate_negatives.py  enum validator + dedup vs positives
├── render_report.py       report.md + report.json + report.html
├── update_index.py        append .runs/INDEX.md row
├── pulse_fetch.py         Phase 7: Serper /news + Tavily news search
└── pulse_synth.py         Phase 7: theme cluster, regulatory tag,
                                    competitor match, trending negs

references/                    ← progressive-disclosure rubrics
├── phase5-competitor-intel.md
├── phase6-negatives-report.md
└── phase7-niche-pulse.md

.runs/                         ← per-run sealed folders (git-ignored raw/)
└── INDEX.md                   ← browsable run history
```

**Boundary rule:** scripts handle I/O + math + validation. Claude (LLM) handles judgment — seed generation, intent classification, semantic clustering, value-prop extraction, negative generation. They communicate via files in the run folder. No IPC. No shared mutable state.

---

## Project layout

```
.
├── .claude/skills/google-ad-research/    ← the skill (project-scoped)
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
├── .planning/                            ← GSD planning artifacts
│   ├── PROJECT.md
│   ├── ROADMAP.md
│   ├── REQUIREMENTS.md
│   ├── STATE.md
│   ├── research/                         ← stack + features + architecture
│   └── phases/                           ← per-phase RESEARCH/PLAN/VERIFICATION
├── .runs/                                ← per-run output (raw/ git-ignored)
├── .env.example                          ← copy to .env
├── .gitignore
├── CLAUDE.md                             ← Claude Code project conventions
└── README.md                             ← this file
```

---

## Limitations & honest tradeoffs

1. **No real search volume.** The skill ranks on `source_diversity` × intent × `signal_count` — a popularity proxy, not Google's actual data. You still paste the final keyword list into Keyword Planner for volume + CPC.
2. **Brief quality drives output quality.** A vague brief produces vague keywords. Five required fields are enforced for a reason.
3. **Serper ads block is unreliable.** Healthcare and many other niches return 0 ads even when Google clearly shows them. The competitor intel script falls back to top organic results — those landing pages contain the same value props paid advertisers would highlight, so the downstream analysis still works.
4. **Niche pulse themes have noise.** N-gram clustering surfaces some news-source bylines and reporter names. Stop-token list filters most; the Highlights block at the top of the section is curated to high-priority items only.
5. **Single-operator design.** No multi-tenant, no auth, no shared state. The skill expects one PPC operator running it for in-house or solo agency campaigns. Productizing for end clients is out of scope for v1.

---

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — Claude Code project conventions (skill location, secret discipline, run-folder rules)
- [`.planning/PROJECT.md`](.planning/PROJECT.md) — project context, scope, key decisions
- [`.planning/ROADMAP.md`](.planning/ROADMAP.md) — phase breakdown + completion status
- [`.planning/REQUIREMENTS.md`](.planning/REQUIREMENTS.md) — every requirement (44 v1) traced to a phase
- [`.planning/research/SUMMARY.md`](.planning/research/SUMMARY.md) — domain research synthesis
- [`.planning/research/PITFALLS.md`](.planning/research/PITFALLS.md) — 22 pitfalls + mitigations
- [`.claude/skills/google-ad-research/SKILL.md`](.claude/skills/google-ad-research/SKILL.md) — operator workflow

---

## Roadmap (post-v1)

| Item | Status |
|------|--------|
| Optional Google Ads API integration for real volume + CPC | v2 |
| Vertical presets (ecommerce, SaaS, lead-gen, local services) | v2 |
| SERP cache by query hash to reduce repeat API spend | v2 |
| Google Ads Editor CSV export format | v2 |
| Run-diff script comparing two runs by `report.json` | v2 |
| Multi-locale fan-out (one brief, multiple country/language reports) | v2 |

---

## Tech stack

- **Runtime:** Python ≥ 3.11 via [`uv`](https://docs.astral.sh/uv/) ≥ 0.4 with PEP 723 inline script metadata
- **HTTP:** [`httpx`](https://www.python-httpx.org/) 0.28 + [`httpx-retries`](https://github.com/will-ockmore/httpx-retries) 0.5
- **APIs:** [Serper.dev](https://serper.dev/) (REST), [Tavily](https://tavily.com/) (`tavily-python` 0.7.24)
- **Text processing:** [`inflect`](https://github.com/jaraco/inflect) 7.5 (singularization), [`python-slugify`](https://github.com/un33k/python-slugify) 8
- **Reports:** [`tabulate`](https://github.com/astanin/python-tabulate) 0.9 (markdown), self-contained vanilla JS for HTML
- **Secrets:** [`python-dotenv`](https://github.com/theskumar/python-dotenv) 1.0
- **Tests:** `pytest` 8 + `respx` (httpx mocking) + `monkeypatch` (Tavily SDK)
- **Logging:** stdlib `logging` + [`rich`](https://github.com/Textualize/rich) `RichHandler`

---

## License

[Add your license — MIT, Apache 2.0, or proprietary depending on use case.]

---

## Acknowledgments

Built using the [GSD (Get Shit Done) methodology](https://github.com/get-shit-done/get-shit-done) for phase-driven greenfield projects with goal-backward verification at every step.
