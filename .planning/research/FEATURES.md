# Feature Research

**Domain:** Google Ads keyword research tooling (delivered as an internal Claude Code skill)
**Researched:** 2026-05-08
**Confidence:** HIGH for table stakes / anti-features (broad consensus across 2026 sources); MEDIUM for ranking-without-volume heuristics (less well-trodden, mostly synthesised from intent-classification literature + PPC practitioner posts)

## Context Recap

This skill replaces "operator opens 6 tabs and stitches together a brief" with one Claude Code session that produces a markdown report containing:

1. Ranked keyword table
2. Ad group clusters
3. Competitor ad copy
4. Negative keyword candidates

Single internal operator. No volume/CPC API in v1 — frequency-of-occurrence + LLM-scored commercial intent. Generic engine, vertical presets deferred. WebSearch + Serper.dev + Tavily as the three signal sources.

Key implication for this research: many "table stakes" of *commercial* keyword tools (volume, CPC, KD, SERP volatility) are explicitly out-of-scope. Our table stakes are scoped to **what the operator needs to deliver a campaign-ready brief** — not what Ahrefs ships.

---

## Feature Landscape

### Table Stakes (Must Have or the Report Is Useless)

The operator already has Keyword Planner. If we miss any of these, they will reach for it instead.

#### Intake

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Conversational brief intake with field elicitation | Operator pastes whatever they have; skill draws out the rest. Hard requirement per PROJECT.md (Active scope). | LOW | System prompt pattern: parse paste, identify missing fields from the canonical list, ask 2-3 clarifying questions max per turn. Don't re-ask answered fields. |
| Canonical brief field set | Without these, every downstream signal is mis-targeted. Industry standard across PPC intake templates: industry/vertical, primary product or service, geographic targets, language(s), target audience description, budget signal (size class is enough — exact spend not needed for keyword research), business goal (lead gen / ecom sale / app install / brand). | LOW | Define a fixed schema in the skill. Ten fields max. Each field gets one elicitation question. Validate before research starts. |
| Brief validation / confirmation step | Operator confirms parsed brief before any paid API call fires. Prevents £-burning research on a misread brief. | LOW | Render the parsed brief back as a markdown table, ask "ship it?". |
| Geo + language exclusions captured | Crucial for negative-keyword generation downstream. "We sell in UK only" is a different research run than "global English". | LOW | Two extra fields in the schema. Used downstream for negatives + competitor SERP locale. |

#### Ranked Keyword Table

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Keyword column with the actual phrase | Obvious. | LOW | Normalise casing, strip stopwords inconsistently across sources. |
| Intent label column | Industry has standardised on the four-class model — informational, navigational, commercial, transactional. PPC tools in 2026 (SEMrush Keyword Magic, Ahrefs Intent Score, KeywordInsights) all surface this. Operator expects it. | LOW | LLM call: classify each keyword into {informational, navigational, commercial, transactional}. Prompt with definitions + examples. |
| Match type recommendation column | Operators copy keywords directly into Google Ads; "exact / phrase / broad" recommendation saves the manual decision. 2026 best practice consensus: exact for high-intent core, phrase for controlled expansion, broad rare and only with smart bidding. | LOW | Heuristic: transactional + brand-exact → exact; transactional + multi-word → phrase; commercial/informational → phrase by default; broad only for high-confidence head terms with smart bidding signal in brief. |
| Theme / cluster tag column | Lets the operator sort the table by ad group at a glance, sanity-check clustering before pasting. | LOW | Same tag the clustering step assigns. One column join. |
| Ranking score column with explanation | Operator must trust the ordering. Without volume, "why is this #1?" must be answerable. | MEDIUM | Composite score: frequency-of-occurrence across SERP signals (PAA, related, organic anchors, ad headlines) × LLM-judged commercial intent on a 1-5 scale × brief-fit boost. Show the score AND the components. |
| Source signal column | "Where did this keyword come from?" — PAA / Related / Organic / Ad Block / Competitor LP / WebSearch. Builds operator trust in the system. | LOW | Track source per keyword from the moment it's harvested. |
| Deduplication & normalisation | Same keyword with different casing/punctuation/stopwords appearing twice destroys credibility. | LOW | Lowercase, strip punctuation, collapse whitespace, optional stopword strip for the dedup key. Keep the original for display. |

#### Ad Group Clustering

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Clusters of 5-15 keywords per group | 2026 consensus is STAGs (Single Theme Ad Groups), 5-15 keywords sharing intent. SKAGs deprecated since close-variants expansion. Operator expects ad groups they can paste straight into Google Ads. | MEDIUM | LLM-based semantic clustering with a hard cap on cluster size. Split clusters > 15 by sub-theme. |
| Theme-coherent groupings (not just lexical) | A cluster of {"buy red shoes", "red shoes for sale", "purchase red shoes"} is good. {"red shoes", "shoe red", "redshoes.com"} is bad. Production tools (KeywordInsights, TopicalMap, SEMrush) all use semantic / SERP-overlap clustering, not n-gram. | MEDIUM | LLM clustering pass with theme labels. Optional: validate cluster coherence by asking the LLM to name a single ad headline that would suit all keywords in the group — if it can't, split. |
| Theme name per cluster | Operator names ad groups in Google Ads from these. A cluster called "shoe-red-buy" is more useful than "Cluster 7". | LOW | LLM names cluster after composition. Use kebab-case, ≤4 words. |
| Intent-homogeneous clusters | Mixing transactional + informational in one ad group destroys Quality Score. The cluster step must respect intent boundaries. | LOW | Cluster within intent class as a hard constraint, not soft. |

#### Competitor Ad Copy

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Top headlines pulled from Serper ad block | The whole point of paying for Serper. Headlines are the highest-value competitor signal. | LOW | Serper returns the ads block as structured JSON; pull `title` fields. |
| Descriptions / body copy per ad | Captures USP, offer language, urgency cues. Industry-standard competitor analysis output. | LOW | Serper returns ad descriptions. Parse and store. |
| Display URL / final URL | Shows the landing page. Operator clicks through to assess. Also the de-dup key per advertiser. | LOW | Both fields present in Serper ads payload. |
| Deduplication by advertiser | Same advertiser can run 3-4 rotations. Showing all 4 to the operator is noise. | LOW | Group by display URL host; keep best 1-2 per host. "Best" = longest headline + most extensions, or just first occurrence. |
| Ad copy grouped by ad group / theme | Operator wants to see "for cluster 'red-shoes-buy', here's how the top 5 advertisers pitch it". Generic dump is less useful. | MEDIUM | Run Serper queries per cluster representative keyword, attach ads to cluster. Some clusters share advertisers — that's fine, surface the overlap. |
| Competitor landing page value props (Tavily) | One step beyond just ads: pull the actual hook from the landing page. PROJECT.md explicitly Active scope. Differentiator from Serper-only tools. | MEDIUM | Tavily extract on top 3-5 competitor URLs per cluster. Prompt: extract headline, sub-headline, primary CTA text, top 3 listed benefits, any visible offer (£X off, free trial, etc.). |

#### Negative Keywords

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Categorised negative list (not flat) | 2026 consensus across PPC strategy posts: separate lists by category enable per-campaign / per-ad-group application. Flat lists get dumped at account level and over-block. | LOW | Six categories minimum: Jobs/Careers, Free/DIY/Tutorial, Used/Refurbished/Wholesale, Competitor Brands, Wrong Geo (if exclusions in brief), Wrong Audience (e.g. "for kids" when brief is B2B). |
| "Free / cheap / discount" exclusions for premium brands | If brief signals premium/B2B, "free" / "cheap" / "discount" are obvious negatives. Industry table-stakes negative list. | LOW | Brief field: budget-signal + audience drives whether to add or skip these. |
| Job / career / hiring exclusions | Universal. "[brand] jobs" is the most common cited waste source. Almost every PPC negative list starts here. | LOW | Add unconditionally unless brief explicitly says "we are a recruiter". |
| Information-seeking modifier exclusions | "How to", "what is", "tutorial", "guide", "DIY" — drains transactional campaign budget. Standard in every 2026 PPC negative list. | LOW | Conditional on campaign goal. Lead-gen and ecom: include. Awareness/top-of-funnel: skip. |
| Per-keyword justification | "Why is 'free' negative for me?" — operator needs to defend choices to the manager who'll apply them. | LOW | Each negative gets a one-line `reason` field. Drives operator confidence. |
| Match-type recommendation per negative | Negatives have match types too. Phrase-match negatives are usually right; broad-match negatives over-block. | LOW | Default phrase-match for multi-word, exact-match for single ambiguous word, broad-match never recommended. |

#### Output Mechanics

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Markdown report with all four sections | PROJECT.md requirement. Operator pastes into docs/Slack. | LOW | Single `.md` file per run. |
| Run history folder, dated | PROJECT.md requirement. Operator wants to look up past work. | LOW | `runs/YYYY-MM-DD-{slug}/` containing `brief.md`, `report.md`, `raw/` for API responses. |
| Brief saved alongside report | Reproducibility. "What did we ask for?" must be answerable for any historic run. | LOW | Write the parsed brief next to the report. |

---

### Differentiators (Better Than Copy-Pasting From Keyword Planner)

These are why the operator chooses this skill over manual Keyword Planner work, *given* the table stakes are met.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Three-source signal triangulation (WebSearch + Serper + Tavily, with role separation) | Keyword Planner only sees Google's view. We see organic SERP, paid ads block, competitor landing page copy — three orthogonal signals. WebSearch is free baseline; Serper structures the SERP; Tavily extracts deep content. Each fills a gap the others miss. | MEDIUM | Orchestration: parallel calls per cluster, merge by keyword key, per-source frequency tracking. |
| Frequency-across-sources as the primary ranking signal | Volume APIs cost money and lag. A keyword that shows up in PAA + organic anchors + 2 competitor ad headlines + a competitor LP H1 is *demonstrably* central — without paying DataForSEO for volume. This is the v1 thesis and it's defensible. | MEDIUM | Count distinct sources per keyword. Weight by source quality (ad block > LP > PAA > organic body). Tie-break with LLM intent score. |
| LLM-scored commercial intent (1-5) per keyword | Goes beyond the four-class label — gives a continuous signal that tie-breaks within a class. "buy red shoes" and "compare red shoes" are both commercial; intent-5 vs intent-3 lets them sort correctly. | LOW | One LLM call per keyword (batched). Prompt: definition + examples + scale anchor for each level. |
| Cluster names that read like ad-group names | Most tools dump "Cluster 1, Cluster 2". A cluster called `shoes-red-buy-transactional` saves the operator a renaming pass and signals the intent. | LOW | LLM-generated, kebab-case, intent suffix appended. |
| Competitor LP value-prop extraction (not just ad copy) | Most competitor tools stop at the ad block. Pulling the hook, CTA, and offer from the landing page is more useful for ad-copy ideation. Tavily is the right tool for this. | MEDIUM | Tavily extract on top 3 advertiser URLs per cluster. Structured prompt with fixed fields. |
| Negative-keyword generation with brief-aware filtering | Generic 3,000-keyword negative lists (which exist) are overkill. Surfacing the 30-50 negatives that actually apply to *this* brief is more valuable than a wall of text. | MEDIUM | Brief fields drive which categories activate. Generic per-category seeds + LLM expansion + dedup against the positive keyword list. |
| Per-run reproducibility (brief + raw API responses + report) | Operator can re-derive any past report. Manager can audit the source signal. Useful when a campaign underperforms three months later and someone asks "where did 'cheap red shoes' come from?". | LOW | Already in PROJECT.md as run-history folder; the differentiator is saving raw signal too. |
| Source attribution per keyword | Builds operator trust. "This keyword scored high because it appeared in 3 ad headlines and PAA" is much more useful than a black-box ranking. | LOW | Already in table-stakes; the differentiator is exposing it cleanly. |
| LLM clustering with intent-homogeneity constraint | Lexical / n-gram clustering (cheap) groups "red shoes" with "redshoes.com". Semantic clustering with intent-class as a hard split produces ad-group-ready clusters. | MEDIUM | LLM clustering with explicit constraint: cluster only within same intent class. |
| Markdown table format pasteable to Google Ads Editor (later) | If we use simple pipe tables and consistent column order, future-Phase CSV export becomes trivial. Hedges against the "we need CSV for Google Ads import" request. | LOW | Discipline in v1 column ordering; CSV export is v2 if needed. |

---

### Anti-Features (Deliberately NOT Building)

PROJECT.md already lists "Out of Scope" — this section adds the features ecosystem-research surfaced as common-but-wrong-for-us.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Volume / CPC / competition metrics from a paid API | "Real PPC tools have these." | Doubles API surface and cost; DataForSEO ≈ $0.05/req, Google Ads API needs OAuth + MCC. PROJECT.md explicitly defers. Adds plumbing for v1 with no payoff while frequency+intent ranking is unvalidated. | v1: rely on frequency+intent. Operator enriches manually via Keyword Planner if needed. v2: add DataForSEO if real usage shows it's the gap. |
| Auto-push to Google Ads (API or Editor CSV) | "Why paste manually?" | Risks bad data going live; couples skill to Google Ads API auth; one bug pushes wasted budget. PROJECT.md explicitly out-of-scope. | Markdown tables paste cleanly. CSV export is a low-cost addition if it becomes the friction point. |
| SEO content generation (article briefs, on-page recommendations) | Many "AI keyword tools" bundle this. | Different product. The operator's job is paid search; SEO content is a different team's deliverable. Bundling muddies positioning. | Keep scope to PPC. If the operator wants SEO briefs, that's a separate skill. |
| Automated bidding suggestions / CPC recommendations | "Tell me how much to bid." | Requires volume + CPC + Quality Score data we don't have. Without ground truth, recommendations are dangerous — they look authoritative but aren't. | Skill stays in research-and-recommend mode. Bidding is the operator's job, informed by Keyword Planner + Smart Bidding signals. |
| Account integration / direct Google Ads connection | "Pull my existing keywords automatically." | Auth surface, multi-account complexity, MCC permissions. PROJECT.md says single operator, no auth. Inconsistent with the "skill in Claude Code" runtime. | Operator pastes existing keyword list as part of the brief if they want to expand on it. |
| Volume forecasting / seasonal projections | "When should we run this campaign?" | Needs historical volume data we don't have. Forecasts without volume are guesses. | Out of scope. Operator handles seasonality in campaign planning, not keyword research. |
| Live SERP monitoring / scheduled re-runs | "Tell me when a competitor changes ads." | PROJECT.md: operator-triggered only, no cron. Adds a daemon, scheduling, alerting — none of which fits the Claude Code skill runtime. | Operator re-runs the skill when they want fresh signal. Run history makes diff manual but cheap. |
| Multi-language / multi-locale parallel runs | "Research UK + US + DE in one shot." | 3x the cost; operator usually runs one market at a time anyway; geo/language is a brief field, not a fan-out. | One run = one locale. Run twice for two markets. |
| SERP cache layer | "Avoid re-paying Serper for the same query." | PROJECT.md: deferred. Cache invalidation is the hard part (SERP changes daily). Real cost at this volume is low (~$0.01 per run). | Pay per run. Revisit if costs sting. |
| Vertical presets (ecom / SaaS / lead-gen / local) in v1 | "Smart defaults per vertical." | PROJECT.md: deferred to v2. We don't yet know which verticals matter; building 4 presets blind = building 3 wrong ones. | Generic engine v1. Watch real usage; build presets for the 1-2 verticals that dominate. |
| Web dashboard / GUI | "I want to see this in a UI." | PROJECT.md: out of scope. Single operator. The Claude Code session is the UI. Markdown tables render fine in chat and paste fine to Slack/docs. | Markdown report is the deliverable. |
| Chat-with-your-results / Q&A over past reports | "Can I ask the skill 'show me all past reports about shoes'?" | The folder structure + ripgrep already does this for one operator. Building a retrieval layer over markdown files is fun and unnecessary. | Operator opens the folder, greps, asks Claude Code to read files directly. |
| Quality Score prediction | "Will this keyword have a good Quality Score?" | Quality Score is an account-and-history-dependent Google internal signal. Predicting it without account data is impossible; estimating it badly is worse than not at all. | Out of scope. The clustering and intent-homogeneity work *aids* Quality Score by structure, but we don't predict it. |
| Search term mining from existing campaigns | "Pull my Search Terms report and find new keywords." | Different signal source, requires account integration (anti-feature above), and is a v2-onwards feature even if accepted. | Operator runs the skill on a brief, not on an account. Existing search terms are a brief input if relevant. |
| 3,000-keyword "universal" negative list dump | Several 2026 articles publish these. Tempting to include. | Most are irrelevant per-brief; dumping them at account level over-blocks; 90% of them duplicate what brief-aware generation produces. | Brief-aware generation, ~30-50 negatives per run, categorised. |

---

## Feature Dependencies

```
Brief Intake (canonical fields + validation)
  └── drives ──> Search Query Construction (seeds, locale, language)
                  └── feeds ──> WebSearch + Serper + Tavily (parallel)
                                  └── produces ──> Raw Keyword Pool (with source attribution)
                                                    └── feeds ──> Deduplication + Normalisation
                                                                    └── feeds ──> Intent Classification (LLM)
                                                                                    └── feeds ──> Frequency Scoring
                                                                                                    └── feeds ──> Ranked Keyword Table
                                                                                                                    └── feeds ──> Clustering (LLM, intent-homogeneous)
                                                                                                                                    ├── feeds ──> Cluster naming
                                                                                                                                    ├── feeds ──> Match-type recommendation
                                                                                                                                    └── feeds ──> Per-cluster Serper requery (for ad copy)
                                                                                                                                                    └── feeds ──> Ad Copy Section (deduped per advertiser)
                                                                                                                                                                    └── feeds ──> Tavily LP extraction (top advertisers)
                                                                                                                                                                                    └── feeds ──> Value-prop block per cluster

Brief Intake ──also drives──> Negative Category Activation (jobs, free/DIY, used, comp brands, geo, audience)
                                  └── feeds ──> LLM negative expansion
                                                  └── dedup against ──> Positive Keyword Pool
                                                                          └── feeds ──> Negative Keywords Section

Markdown Report Assembly (last step)
  └── consumes ──> Ranked Table + Clusters + Ad Copy + Negatives
                    └── written to ──> runs/YYYY-MM-DD-{slug}/report.md
                                        └── alongside ──> brief.md + raw/

[Volume API enrichment] ──conflicts (out of scope v1)──> [Frequency-based Ranking]
[Account Integration] ──conflicts (out of scope)──> [Brief-driven Search Query Construction]
[SERP Cache] ──conflicts (out of scope)──> [Live signal per run]
```

### Dependency Notes

- **Clustering depends on intent classification:** Intent class is a *hard split* before clustering. We need the label before we can cluster within-class. This means the LLM intent pass runs before the LLM cluster pass — they cannot be merged.
- **Per-cluster ad copy depends on clustering:** We re-query Serper per cluster representative to get ads scoped to that theme, rather than dumping every ad we ever saw. This means ad-copy extraction is *not* free — it's an additional ~N Serper calls where N = cluster count. Watch this for cost.
- **Tavily LP extraction depends on having an advertiser URL list:** Falls out of the Serper ads block. Tavily cost scales with number of unique advertisers we want to deeply mine — cap at top 3-5 per cluster.
- **Negatives depend on the positive pool:** We dedup negatives against positives so we don't accidentally negative-out our own keywords. This means negative generation is a *late* step, not parallel to keyword expansion.
- **Brief validation gates everything:** No paid API call fires until the operator confirms the parsed brief. This is a cost control feature, not just UX.
- **Frequency ranking requires source tracking from the start:** If we don't tag every keyword with its source(s) at harvest time, we cannot reconstruct frequency-of-occurrence later. This is a discipline thing — get it right in the harvest layer.

---

## MVP Definition

### Launch With (v1) — All Table Stakes

The skill is not useful below this line.

- [ ] **Conversational brief intake with canonical field set + validation** — without this, every signal is mis-targeted
- [ ] **Three-source signal harvest (WebSearch + Serper + Tavily) with source attribution per keyword** — the v1 thesis
- [ ] **Dedup + normalisation** — credibility floor
- [ ] **LLM intent classification (4-class)** — gates clustering, sorts the table
- [ ] **Frequency-of-occurrence + LLM intent ranking with explainable score** — the no-volume ranking story
- [ ] **Ranked keyword table with: keyword, intent, match-type rec, theme tag, score, source(s)** — section 1 of the report
- [ ] **LLM clustering, intent-homogeneous, 5-15 keywords/cluster, named clusters** — section 2
- [ ] **Per-cluster competitor ad copy from Serper, deduped by advertiser** — section 3 (basic)
- [ ] **Tavily LP value-prop extraction for top advertisers per cluster** — section 3 (deep)
- [ ] **Categorised negatives (≥6 categories), brief-driven, deduped against positives, with per-keyword justification** — section 4
- [ ] **Markdown report assembly + run history folder with brief + raw API output** — deliverable + audit trail

### Add After Validation (v1.x)

Add when real usage reveals the friction.

- [ ] **CSV export of the keyword table in Google Ads Editor format** — trigger: operator asks for it twice, or Google Ads import becomes the manual step
- [ ] **Cluster diff vs previous run** — trigger: operator runs the skill twice on similar briefs and asks "what's new"
- [ ] **Generic negative seed library** (the standard Jobs/Free/DIY/etc seeds expanded to ~200 entries) — trigger: LLM-generated negatives are missing obvious ones
- [ ] **Match-type recommendation tuning based on operator feedback** — trigger: the rec is wrong often enough that the operator overrides systematically
- [ ] **Multi-cluster representative keyword sampling** (more than one keyword per cluster used as Serper requery seed) — trigger: ad-copy section is too sparse for some clusters
- [ ] **Brief template auto-suggestion based on industry field** (still generic engine, but smarter defaults for the canonical field elicitation) — trigger: operator types the same opening lines on every run

### Future Consideration (v2+)

Defer until product-market fit is established or PROJECT.md scope is revisited.

- [ ] **Vertical presets (ecom / SaaS / lead-gen / local)** — defer per PROJECT.md; revisit when 1-2 verticals dominate real usage
- [ ] **Volume / CPC enrichment via DataForSEO or Google Ads API** — defer per PROJECT.md; revisit if frequency+intent ranking proves insufficient
- [ ] **SERP cache layer** — defer per PROJECT.md; revisit if cost becomes painful
- [ ] **Search-term-report mining from operator's existing campaigns** — needs account integration which is out-of-scope
- [ ] **Multi-locale fan-out in a single run** — defer; one-run-per-market is fine
- [ ] **Scheduled re-runs / monitoring** — defer per PROJECT.md
- [ ] **Cross-run analytics / "all keywords for shoes ever researched"** — defer; folder + grep + Claude Code chat covers this for one operator

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Brief intake with canonical fields + validation | HIGH | LOW | P1 |
| WebSearch + Serper + Tavily harvest with source attribution | HIGH | MEDIUM | P1 |
| Dedup + normalisation | HIGH | LOW | P1 |
| LLM intent classification (4-class) | HIGH | LOW | P1 |
| Frequency + intent composite ranking with explainable score | HIGH | MEDIUM | P1 |
| Ranked keyword table (markdown) | HIGH | LOW | P1 |
| Match-type recommendation column | MEDIUM | LOW | P1 |
| Theme tag column | MEDIUM | LOW | P1 |
| LLM clustering, intent-homogeneous, named | HIGH | MEDIUM | P1 |
| Per-cluster Serper ad copy section, deduped | HIGH | LOW | P1 |
| Tavily LP value-prop extraction | HIGH | MEDIUM | P1 |
| Categorised negatives with justification | HIGH | MEDIUM | P1 |
| Run history folder with brief + raw + report | MEDIUM | LOW | P1 |
| CSV export | MEDIUM | LOW | P2 |
| Cluster diff between runs | MEDIUM | MEDIUM | P2 |
| Generic negative seed library | LOW | LOW | P2 |
| Vertical presets | MEDIUM | HIGH | P3 |
| Volume / CPC enrichment | HIGH | HIGH | P3 |
| SERP cache | LOW | MEDIUM | P3 |
| Account integration | LOW | HIGH | P3 (anti-feature, listed for completeness) |
| Auto-push to Google Ads | LOW | HIGH | Never (anti-feature) |
| SEO content generation | LOW | MEDIUM | Never (out of scope) |
| Quality Score prediction | LOW | HIGH | Never (anti-feature) |

**Priority key:**
- P1: Must have for v1 launch
- P2: Should have, add when validated friction emerges
- P3: Future consideration, only if PMF established and gap proven
- Never: Anti-feature; deliberately not building

---

## Competitor Feature Analysis

The operator's actual alternatives are: Google Keyword Planner (free, no semantic clustering, no negatives, no competitor copy), SEMrush PPC Keyword Tool (paid, full-featured, but a separate tool outside Claude Code), Ahrefs Keywords Explorer (similar), and the manual "Keyword Planner + competitor SERP scrape + ChatGPT clustering" stack the operator currently runs.

| Feature | Google Keyword Planner | SEMrush / Ahrefs | Our Approach |
|---------|------------------------|------------------|--------------|
| Volume / CPC | Yes — but in ranges in 2026 unless spending | Yes, full numeric | Deliberately skip v1; use frequency-of-occurrence + LLM intent. Operator enriches via Keyword Planner manually if needed. |
| Intent classification | Parent Topic feature, coarse | Yes (Ahrefs Intent Score 0-100, SEMrush 4-class) | LLM 4-class label + 1-5 commercial intensity |
| Match-type recommendation | No | Partial (filters yes, recs no) | Heuristic per-keyword recommendation column |
| Ad group clustering | No (manual) | Yes (KeywordInsights, SEMrush Magic Tool) | LLM semantic clustering with intent-homogeneity constraint, named clusters |
| Cluster size | N/A | 5-20, varies | 5-15 hard cap, split larger clusters by sub-theme |
| Competitor ad copy extraction | No (separate Auction Insights only) | Yes (SEMrush Advertising Research) | Serper ads block per cluster, deduped by advertiser |
| Competitor LP value-prop extraction | No | No (mostly ads only) | **Differentiator** — Tavily extract on top advertisers |
| Negative keyword suggestions | Limited | Some (generic lists) | **Differentiator** — brief-aware categorised negatives with justifications |
| Output format | UI / CSV | UI / CSV / report | Markdown (suits Claude Code chat + paste-to-Slack workflow) |
| Lives inside Claude Code | No | No | **Differentiator** — operator never leaves the chat |
| Cost per run | Free | $100-500/mo subscription | ~$0.01-0.10 per run in API costs (Serper + Tavily) |
| Volume API dependency | Yes | Yes | No (deliberate v1 choice) |
| Reproducibility / run history | None | Project history in UI | Folder per run with brief + raw + report |

**Position summary:** We're not competing on volume/CPC accuracy — Keyword Planner wins that. We're competing on **time-to-campaign-ready-brief** for one operator working inside Claude Code, with three-source signal triangulation and competitor LP value-prop extraction as the two real differentiators.

---

## Confidence & Open Questions

**HIGH confidence:**
- Table-stakes feature list — broad consensus across 2026 sources, multiple independent practitioner posts, official Google Ads docs, and PPC tooling vendors agree on the four-section deliverable shape, intent classification, STAG clustering at 5-15 keywords, categorised negatives.
- Anti-features list — most are explicit in PROJECT.md; the rest (Quality Score prediction, content gen, search-term mining) are well-supported as scope-creep risks.

**MEDIUM confidence:**
- Exact ranking heuristic (frequency × LLM intent × brief-fit) — the *components* are well-supported individually; the *combination weighting* is not standardised in the literature. We will need to tune in v1 against operator feedback. This is the highest-risk part of v1 from a "does the output rank right" perspective.
- Cluster-sizing target (5-15 keywords) — sources span 3-20; 5-15 is the modal recommendation. Edge cases (very narrow vertical, very broad ecom catalogue) may need different bands.

**LOW confidence / open questions:**
- How many Tavily extractions are economically reasonable per run? Cost is ~$0.005-0.01 per extraction. With 6-10 clusters × 3 advertisers/cluster = 18-30 extractions = $0.09-0.30. Acceptable for an internal skill but worth measuring after the first 5 real runs.
- Should match-type recommendations be conservative (default phrase, exact only when high confidence) or aggressive (default exact for transactional)? 2026 best-practice consensus leans conservative-then-expand. v1 default: conservative.
- Whether the operator wants ad-copy section grouped by cluster or as a standalone "top advertisers" section is unproven — recommend per-cluster grouping based on PPC workflow norms, but worth confirming on first real run.

---

## Sources

PPC keyword research tools and 2026 landscape:
- [9 Best Google Ads Keyword Research Tools Guide 2026 — keywordme.io](https://www.keywordme.io/blog/google-ads-keyword-research-tools)
- [AI-Powered Keyword Research for Google Ads 2026 (15 Tools)](https://www.get-ryze.ai/blog/ai-powered-keyword-research-google-ads)
- [Google Keyword Planner — Google Ads Help](https://support.google.com/google-ads/answer/7337243?hl=en)
- [Keyword Research in 2026: The Complete B2B Guide — Whitehat](https://whitehat-seo.co.uk/blog/secrets-of-keyword-research)

Match types & intent in 2026:
- [About keyword matching options — Google Ads Help](https://support.google.com/google-ads/answer/7478529?hl=en)
- [Google Ads Keyword Match Types Explained 2026 — Stackmatix](https://www.stackmatix.com/blog/google-ads-keyword-match-types-guide)
- [Keyword match types in Google Ads 2026 — Store Growers](https://www.storegrowers.com/keyword-match-types/)
- [Google Ads Match Types 2026: Control Spend & Scale](https://infrontmarketing.ca/blog/google-ads/google-ads-match-types-in-2026-how-to-control-spend-without-killing-scale/)
- [Search Intent Classification Methods 2026 — TopicalMap](https://topicalmap.ai/blog/auto/search-intent-classification-methods-2026)

Ad group structure (STAG vs SKAG, cluster sizes):
- [STAG vs SKAG Campaigns: What Is Best for 2026? — sitecentre](https://www.sitecentre.com.au/blog/stag-vs-skag-campaigns)
- [Single Keyword Ad Groups: Still Relevant in 2026? — Store Growers](https://www.storegrowers.com/single-keyword-ad-groups/)
- [Google Ads Account Structure in 2026 — Groas](https://groas.ai/post/google-ads-account-structure-in-2026-the-framework-that-actually-works)
- [How To Cluster Keywords By Theme For Ad Groups — keywordme.io](https://www.keywordme.io/blog/how-to-cluster-keywords-by-theme-for-ad-groups)
- [What Are STAGs (Single Theme Ad Groups)? — Adzooma](https://adzooma.com/blog/what-are-stags-single-theme-ad-groups/)
- [How Many Keywords Should Be in One Google Ads Ad Group? — Jyll](https://learn.jyll.ca/blog/how-many-keywords-should-be-in-one-google-ads-ad-group)

Competitor ad copy & SERP extraction:
- [How to Scrape Competitors' Google Ads Data — ScraperAPI](https://www.scraperapi.com/blog/how-to-scrape-competitors-google-ads-data-to-better-your-own/)
- [How to Analyze Competitors' Google Ads: 5 Methods — Oxylabs](https://oxylabs.io/blog/google-ads-competitor-analysis)
- [Google Ads Competitor Analysis 2026 Guide — Media Spearhead](https://mediaspearhead.com/blog/competitor-analysis-in-google-ads/)
- [Competitor Landing Page Analysis Template — Kaya](https://www.usekaya.com/blog/analyze-competitor-landing-pages)
- [How to Spy on Your Google Ads Competition (2026) — Traffic Think Tank](https://trafficthinktank.com/check-competitors-google-ads/)

SERP APIs (Serper / SerpApi / Tavily):
- [Serper — The World's Fastest and Cheapest Google Search API](https://serper.dev/)
- [SerpApi vs Serper vs ValueSERP vs SearchApi 2026](https://serpapi.com/blog/compare-serpapi-with-the-alternatives-serper-and-searchapi/)
- [Best SERP APIs in 2026 — Scrapfly Blog](https://scrapfly.io/blog/posts/google-serp-api-and-alternatives)
- [Tavily 101: AI-powered Search for Developers](https://www.tavily.com/blog/tavily-101-ai-powered-search-for-developers)
- [Tavily's /search vs /extract APIs and when to use each — Sofia Guzowski](https://medium.com/@sofia_51582/tavilys-search-vs-extract-apis-and-when-to-use-each-67cc70edd610)

Negative keywords:
- [The real strategy behind negative keywords in 2026 — Search Engine Land](https://searchengineland.com/negative-keywords-strategy-476563)
- [Negative Keywords in Google Ads (2026) — Karooya](https://www.karooya.com/blog/negative-keywords-in-google-ads-2026-are-you-using-them-to-filter-traffic-or-control-it/)
- [Ultimate list of negative keywords for CMOs 2026 — cometogether.media](https://www.cometogether.media/single-post/list-of-negative-keywords)
- [3,000+ negative keywords for PPC 2026 — Launchcodex](https://launchcodex.com/blog/industry-news-shifts/negative-keyword-list-ppc/)
- [5 Negative Keyword Lists Every PPC Campaign Should Have — Zinnius](https://zinnius.com/ppc-negative-keyword-lists/)

Conversational intake & brief design:
- [Conversational AI Development Best Practices 2026](https://www.ai-agentsplus.com/blog/conversational-ai-development-best-practices)
- [PPC Strategy Template — Bowler Hat (PDF)](https://www.bowlerhat.co.uk/wp-content/uploads/2017/05/PPC-Strategy-Template.pdf)
- [How to Perfectly Manage a PPC Campaign Template — HubSpot](https://blog.hubspot.com/blog/tabid/6307/bid/33882/how-even-you-can-master-ppc-campaign-management-template.aspx)

Naming conventions / cluster naming:
- [Google Ads Naming Conventions: The Complete Guide — JD Consulting](https://jdconsulting.io/blog/why-your-google-ads-naming-conventions-are-holding-you-back)
- [Marketing Campaign Naming Conventions 2026 — Improvado](https://improvado.io/blog/marketing-campaign-naming-conventions)
- [Ad Group Themes — Google Ads API](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-ad-group-themes)

PAA / Related Searches as expansion sources:
- [People Also Ask: The obvious opportunity most SEOs are missing — Search Engine Land](https://searchengineland.com/guide/people-also-ask)
- [How to Use People Also Ask Data for Keyword Research — Wellows](https://wellows.com/blog/how-to-use-people-also-ask-data/)

---
*Feature research for: Google Ads keyword research skill (Claude Code, internal operator)*
*Researched: 2026-05-08*
