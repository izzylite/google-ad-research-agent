# Google Ad Research Agent

A [Claude Code](https://claude.com/claude-code) skill that turns one campaign brief into a complete Google Ads research package — paste a brief, walk away with a launch-ready report and Google Ads Editor CSVs.

```
brief in chat  →  ~10 min  →  ranked keywords + ad groups + competitor intel + negatives + Editor CSVs
```

---

## Why this tool

Manual Google Ads keyword research takes 4–6 hours per campaign:

- Tabbing between Google search, People Also Ask, and Related Searches
- Clicking through competitor sites to copy headlines, CTAs, and offers
- Grouping keywords into ad groups in a spreadsheet
- Brainstorming negative keywords from scratch
- Cross-checking geo eligibility against your state / county target
- Estimating bids + daily budget against client CPA targets
- Flagging vertical compliance (medical, legal, financial, etc.)
- Formatting everything into something a stakeholder can read

This skill compresses all of that into one guided session. Paste a brief, answer a few clarifying questions, walk away with a production-ready package. Same rubric every run — two operators running the same brief get nearly identical output.

---

## Benefits

- **One brief → full package.** Ranked keywords, ad-group clusters, competitor ad copy + landing-page value props, tiered negatives, geo-filtered targeting, suggested Max CPC, daily budget forecast, compliance flags — all in one run.
- **Google Ads Editor paste-ready.** Three CSVs (`positives.csv`, `negatives.csv`, `ad_groups.csv`) drop straight into Editor v2.x — no manual reformatting.
- **Budget-aware.** Set a daily cap in the brief and the report tells you exactly which keywords fit the budget (priority-sorted launch list with cumulative spend). No more "the forecast recommends $338/day on a $82 account."
- **Brand-safe.** When you list your client's brand in `Brand terms:`, the skill will never label any variant of it as a competitor — your own branded traffic can't be accidentally suppressed.
- **Service-line strict.** An `Exclusions:` field deterministically drops off-service keywords (e.g., chiropractor / PT / pain management) before they reach the report — not just LLM-prose guidance.
- **Account-aware.** When connected to your Google Ads account, the skill dedupes against your existing keywords, negatives, and ad groups, so you only see what's genuinely new.
- **Campaign-focused.** Point the skill at one specific campaign in your account and it narrows everything (search terms, keywords, negatives, ad-group mapping) to that scope.
- **Geo-precise.** Lake Worth ≠ Lake Worth Texas. The skill filters out off-target geographies before they pollute the keyword list, and asks you to disambiguate when a brief mixes a county-level token with a city-level one.
- **Compliance scan included.** Flags regulated verticals (medical, legal, etc.) and links to Google Ads policy verification before launch.
- **Interactive HTML report + printable PDF.** Self-contained HTML with sortable tables and CSV export buttons; PDF for stakeholder review.
- **Audit trail.** Every run lives in a sealed dated folder — you can rerun, diff, or hand off any past research.
- **Cheap.** ~26 Serper credits per run. Serper's free tier (2,500 credits on signup) covers ~95 runs.

---

## Installation

### Prerequisites

- [Claude Code](https://docs.claude.com/en/docs/claude-code) (CLI, desktop, or IDE extension)
- [`uv`](https://docs.astral.sh/uv/) ≥ 0.4 (handles all Python dependencies automatically)
- Python ≥ 3.11
- API keys:
  - **[Serper.dev](https://serper.dev/)** — required. Free tier ships with 2,500 credits on signup.
  - **[Ahrefs API](https://ahrefs.com/api)** — optional but recommended. Adds real search volume, CPC, and Keyword Difficulty.
  - **[Google Ads API](https://developers.google.com/google-ads/api)** — optional. Unlocks account-aware dedup + existing-ad-group preservation. Free quota.

### Setup

```bash
git clone https://github.com/izzylite/google-ad-research-agent.git
cd google-ad-research-agent
cp .env.example .env
```

Edit `.env`:

```
SERPER_API_KEY=...
AHREFS_API_KEY=...
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=...
```

The core pipeline runs with `SERPER_API_KEY` alone. Add the Ahrefs + Google Ads keys to unlock volume enrichment, account sync, bid suggestions, and the Editor CSV launch kit.

That's it. Launch Claude Code in this directory — the skill is auto-discovered.

```bash
claude
```

---

## How to use

In Claude Code, paste a brief. The skill activates on keywords like *"keyword research"*, *"Google Ads research"*, *"PPC keywords"*, *"ad group clusters"*, or any prose that mentions industry / product / location / language / audience.

### Example brief

A minimal brief works (just the 5 required fields), but the richer the brief, the tighter the output. This is what a real client-account brief looks like:

```
I'm running a Google Ads campaign for an urgent care clinic in Lake Worth FL,
targeting recent car accident victims with PIP insurance coverage.

Industry: medical / urgent care
Product: urgent care exam + PIP documentation for car accident victims
         (NOT chiropractor, NOT physical therapy, NOT pain management,
          NOT orthopedics — those are refer-out specialties)
Location: Lake Worth FL
Language: en-US
Audience: car accident victims with PIP insurance

Budget: $82/day / $1,600/mo
Brand terms: Primary Urgent Care Centers, Primary Urgent Care, Primary UC, primaryuc.com
Exclusions: chiropract, physical therapy, pain management, orthopedic,
            pediatric, veterinary, dental, mental health, psychiatric, geriatric
Geographic focus: Lake Worth
Campaign focus: Search | Lake Worth Accident Exams | Manual CPC
```

The optional fields each unlock specific guardrails:

- `Budget:` → the report's **What Fits Your Cap** subsection delivers a priority-sorted launch list under your daily cap, instead of a forecast that exceeds budget.
- `Brand terms:` → the negative-generation step is blocked from labelling any variant of your brand as a competitor.
- `Exclusions:` → off-service-line and off-audience keywords (e.g., `pediatric urgent care lake worth`) are dropped from the keyword pool entirely, before clustering. Each exclusion is also auto-added as a Strong negative.
- `Geo focus:` (single city) → only the city's SERPs are researched. If you mix a county and a city, the skill asks you to disambiguate before generating anything.
- `Campaign focus:` → account dedup narrows to one named campaign so the existing-keywords / negatives / ad-groups sync isn't polluted by unrelated campaigns.

### Required fields

The skill enforces five required fields. If any are missing it will ask before doing anything else:

| Field | What it means | Example |
|-------|---------------|---------|
| **Industry** | The sector / vertical | medical / urgent care |
| **Product** | The specific product or service this campaign sells | car accident injury care services |
| **Location** | Country, region, or city | Lake Worth FL |
| **Language** | Search language code | en-US |
| **Audience** | Who you're trying to reach | car accident victims with PIP insurance |

### Optional fields

Use these to sharpen the research. Each one activates a specific guardrail:

| Field | What it does |
|-------|-------------|
| **Budget** | Daily and/or monthly spend cap. Activates the **What Fits Your Cap** launch-list subsection in the report. Example: `$82/day / $1,600/mo` |
| **Brand terms** | Comma-separated brand variants. Protects them from being labelled as competitor negatives. Example: `Acme, Acme Inc, acme.com` |
| **Exclusions** | Comma-separated phrases (or word stems) to drop from research output entirely. Keywords containing any phrase are dropped at intake; each phrase is auto-added as a Strong negative. Use word stems for safer matching (e.g., `chiropract` catches `chiropractor`, `chiropractic`, `chiropractors`). Example: `chiropract, physical therapy, pediatric, veterinary` |
| **Geographic focus** | Single city or comma-separated cities. Drops out-of-area SERP results before ranking. If you mix a county-level token (`Palm Beach County`) with a city-level token (`Lake Worth`), the skill asks you to clarify scope. Example: `Lake Worth` |
| **Campaign focus** | Points the skill at one specific campaign in your Google Ads account. All account-aware features (existing keywords, negatives, ad groups, performance) narrow to that campaign. Example: `Search \| Lake Worth Accident Exams \| Manual CPC` |
| **Competitor URLs** | Specific competitor sites to inspect |
| **Geo exclusions** | Sub-regions to exclude (e.g., `Europe excluding UK`) |
| **Language exclusions** | Languages to skip (for multilingual regions) |

---

## What you get

Every run lands in a dated folder under `.runs/`. Here's what's inside:

### The deliverables (open these)

| File | What it is |
|------|-----------|
| **`report.html`** | Interactive report — sortable tables, CSV export buttons per section, "how to use" guidance inline. Self-contained — opens in any browser. **Best for working with the data.** |
| **`report.pdf`** | Printable / emailable snapshot of the HTML report. Best for stakeholder review. |
| **`report.md`** | Plain markdown version for Notion / GitHub / docs. |
| **`export/positives.csv`** | Keywords with Max CPC, match type, ad group — paste straight into Google Ads Editor. |
| **`export/negatives.csv`** | Tiered negatives (Strong / Considered / Investigate) ready for Editor import. |
| **`export/ad_groups.csv`** | Ad-group structure for Editor. |

### The data (audit + automation)

| File | What it is |
|------|-----------|
| `brief.md` | The brief you pasted, verbatim |
| `keywords.json` | Canonicalised, deduped, source-attributed keyword pool |
| `ranked.json` | Scored + intent-classified (transactional / commercial / informational / navigational) |
| `clusters.json` | Keywords grouped into ad-group-sized clusters |
| `negatives.json` | Tiered + categorised negatives with justifications |
| `competitor-intel.json` | Per-cluster competitor identity + ad copy |
| `competitor-landing-pages.json` | Headline / CTA / offer extracted from top competitor pages |
| `ranked-enriched.json` | Adds real search volume, CPC, KD, and suggested Max CPC (if Ahrefs connected) |
| `account-perf.json` | Your account's recent performance (if Google Ads connected) |
| `negatives-sync.json` | Your generated negatives flagged as new vs already-in-account |
| `positives-sync.json` | Your suggested keywords flagged as new vs already-active / paused / covered |
| `forecast.json` | Daily clicks + spend bands (low / mid / high) per cluster |
| `compliance-flags.json` | Regulated-vertical warnings + Google Ads policy verification links |
| `ad-group-mapping.json` | Maps suggested keywords to your existing ad-group structure |
| `report.json` | Stable JSON of everything in `report.md` — for automation or run-diffing |
| `raw/` | Per-stage API dumps (git-ignored — kept locally for debugging) |

### Index

`.runs/INDEX.md` is a browsable history of every run with one-line summaries — easy to scan when you have dozens of past campaigns.

---

## A typical session

```
You:  I'm running a Google Ads campaign for an urgent care clinic in Lake
      Worth FL, targeting recent car accident victims with PIP insurance...
      Budget $82/day, exclude chiro / PT / pain mgmt, brand is Primary UC.

Skill: [confirms five required fields and any optional fields]
       [auto-derives Exclusions from Product NOT-clauses + Audience;
        asks operator to confirm before sealing the brief]
       [generates seed keywords, pulls SERPs, extracts landing pages,
        classifies intent, clusters, generates negatives, runs account
        sync + bid + forecast + compliance + Editor CSVs]

       Run complete:
       - 59 keywords → 9 clusters (3 transactional, 1 commercial,
         2 navigational, 3 informational)
       - 59 negatives (48 Strong, 5 Considered, 5 Investigate)
       - Compliance flagged: medical + legal — verify before launch
       - Exclusions filter dropped 3 off-service keywords pre-cluster
       - Budget Forecast: 0.49x your $82/day cap
         → Launch list: 32 keywords at $42.46/day cumulative
       - Account sync: 3 already active, 1 paused, 55 new candidates
       - Negatives sync: 27 already in account, 58 new candidates
       - Ad-group mapping coverage: 55.9% → routes to existing AGs
       - Open report.html for interactive view
```

---

## Limitations

- **A vague brief produces vague keywords.** The five required fields are enforced for a reason.
- **Real volume + CPC need an Ahrefs key.** Without it, ranking uses a popularity proxy (source diversity × intent × signal count). For real MSV, either connect Ahrefs or paste the keyword list into Google Keyword Planner manually.
- **Some sites block automated extraction.** Typical landing-page extraction success rate is ~80%. Failed extracts fall back to SERP snippet copy in the report.
- **Single-operator tool.** No multi-tenant, no shared state, no auth. Designed for one PPC operator running campaigns for their team or in-house clients.

---

## License

MIT — see [LICENSE](LICENSE) for details.
