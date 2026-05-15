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
- **Account-aware.** When connected to your Google Ads account, the skill dedupes against your existing keywords + ad groups, so you only see what's genuinely new.
- **Campaign-focused.** Point the skill at one specific campaign in your account and it narrows everything (search terms, keywords, negatives) to that scope.
- **Geo-precise.** Lake Worth ≠ Lake Worth Texas. The skill filters out off-target geographies before they pollute the keyword list.
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

```
I'm running a Google Ads campaign for an urgent care clinic in Lake Worth FL,
targeting recent car accident victims with PIP insurance coverage.

Industry: medical / urgent care
Product: car accident injury care services
Location: Lake Worth FL
Language: en-US
Audience: car accident victims with PIP insurance

Geographic focus: Palm Beach County, Lake Worth
Campaign focus: Search | Lake Worth Accident Exams | Manual CPC
```

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

Use these to sharpen the research. They activate extra phases:

| Field | What it does |
|-------|-------------|
| **Geographic focus** | Narrows keyword discovery to specific counties or cities — drops out-of-area results before ranking. Example: `Palm Beach County, Lake Worth` |
| **Campaign focus** | Points the skill at one specific campaign in your Google Ads account. All account-aware features (existing keywords, negatives, ad groups, performance) narrow to that campaign. Example: `Search \| Lake Worth Accident Exams \| Manual CPC` |
| **Budget** | Daily / monthly spend target |
| **Brand terms** | Brand keywords to include |
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

Skill: [confirms five required fields and any optional fields]
       [generates seed keywords, pulls SERPs, extracts landing pages,
        classifies intent, clusters, generates negatives, runs account
        sync + bid + forecast + compliance + Editor CSVs]

       Run complete:
       - 86 keywords → 12 clusters (4 transactional, 2 commercial,
         3 navigational, 3 informational)
       - 48 negatives (33 Strong, 12 Considered, 3 Investigate)
       - Compliance flagged: medical + legal — verify before launch
       - Daily spend forecast: ~$338/day (mid)
       - Account sync: 1 already active, 4 paused, 81 new candidates
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
