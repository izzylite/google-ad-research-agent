# Pitfalls Research

**Domain:** Google Ads keyword research agent (Claude Code skill, no volume/CPC data, multi-source SERP signals)
**Researched:** 2026-05-08
**Confidence:** HIGH

This document maps the failure modes that cause keyword research tools — and especially LLM-driven, no-volume-data tools — to produce reports that look thorough but lead to wasted ad spend, mismatched ad groups, or operator distrust. Pitfalls are scoped to the eight categories defined for this project. Generic PPC advice (e.g., "set conversion tracking") is excluded — those are downstream of this skill's deliverable.

---

## Critical Pitfalls

These cause the report to be wrong in ways that won't be caught until budget is already spent.

---

### Pitfall 1: Garbage-in-garbage-out from a thin brief

**What goes wrong:**
Operator pastes a one-liner ("Run keywords for our new product launch — McGrocer same-day grocery delivery"). The skill produces a 200-keyword report dominated by generic terms ("online grocery", "grocery delivery near me") that ignore the actual differentiator (same-day, location, audience, price tier, brand vs competitor terms). Report looks complete; PPC manager wastes a week before realising the framing was wrong.

**Why it happens:**
- LLMs are good at producing plausible output from sparse input — output looks right even when the brief was insufficient.
- Operators under time pressure skip the clarifying-question phase or answer "whatever you think is fine."
- The skill has no enforced minimum-information bar before it commits to research spend.

**How to avoid:**
- Make the conversational intake **structured under the hood** — track which fields are filled (industry, sub-vertical, USP, geo, language, audience, price band, competitor list, negative themes, conversion goal). Don't move to research until each has a non-empty answer.
- If operator answers "you decide", the skill should make an explicit assumption and **echo it back in the report front-matter** so it's auditable later.
- Persist the final brief verbatim in the run folder as `brief.md`. Reports without a saved brief should be rejected by the skill itself.

**Warning signs:**
- The brief file is shorter than 5 lines.
- More than two fields say "not specified" or "TBD".
- Operator skipped the clarifying-question turn entirely.

**Phase to address:** Phase 1 (brief intake / skill contract). This is the foundation — every other pitfall compounds if the brief is weak.

---

### Pitfall 2: Frequency-of-occurrence misread as search volume

**What goes wrong:**
Without volume data, v1 ranks keywords by how often they appear across WebSearch + Serper PAA + Serper related + Tavily extracts. Operator (or downstream PPC manager) reads "frequency: 7" as "7 monthly searches" or "7× more popular than frequency: 1". Both interpretations are wrong — frequency only measures **how many of our SERP signals echoed the term**, which correlates loosely with topicality and not at all with search volume.

**Why it happens:**
- The column in the markdown table is labelled ambiguously (e.g., "Score" or "Volume Proxy").
- LLMs will happily explain frequency as if it were a volume signal if asked "is this a popular keyword?".
- PPC industry trains people to expect a volume column; readers project that mental model onto whatever number they see.

**How to avoid:**
- Name the column explicitly: **`signal_count`** (count of source-fragments that surfaced this keyword) and **`source_diversity`** (count of distinct sources: WebSearch / Serper-PAA / Serper-related / Tavily-extract — max 4).
- Add a per-report **"How to read this"** section that says verbatim: *"signal_count is NOT search volume. To estimate volume, paste the keyword list into Google Keyword Planner."*
- Rank primarily by `source_diversity`, tie-break by `signal_count`. A keyword echoed by 4 sources once is more reliable than one repeated 7× by a single PAA block.
- Cap any single source's contribution to a keyword at 1 (or weight it logarithmically). One PAA block listing 8 questions about "free grocery coupons" should not let "free" dominate the report.

**Warning signs:**
- A keyword with `signal_count` ≥ 5 has `source_diversity` = 1.
- The top-10 keywords all originate from the same SERP feature.
- Operator asks "is this volume per month?" — that's a red flag the labelling failed.

**Phase to address:** Phase 3 (ranking / scoring). Lock the column names and the explanatory section in the report template before any ranking math is written.

---

### Pitfall 3: LLM intent scoring drift between runs

**What goes wrong:**
Operator runs the same brief twice (Monday vs Friday). The Monday report scores "best grocery delivery service" as `commercial-intent: 0.8`. Friday's run scores it `0.55`. PPC manager spots the discrepancy and loses trust in the whole tool. Worse, they never notice and just see ad groups shift week-over-week with no explanation.

**Why it happens:**
- LLM scoring is non-deterministic by default (temperature, sampling).
- Free-form prompts ("score this keyword's commercial intent 0-1") give different anchors on different days.
- Different keywords scored in different batches drift relative to each other.

**How to avoid:**
- Use a **rubric, not a scalar**: classify into `{informational, navigational, commercial-investigation, transactional, local}` with explicit criteria for each (e.g., "transactional = contains buy/order/price/cheap/near-me/[brand]+[product]"). Categorical labels are far more stable than 0-1 scores across runs.
- Score keywords in **fixed-size batches with anchor examples**: include 3 "known transactional" and 3 "known informational" examples in every classification prompt so the LLM calibrates against consistent reference points.
- Set `temperature=0` (or as low as the API allows) on the scoring call.
- For each run, log the model name, prompt version, and rubric hash to the run folder. When two reports disagree, the operator can diff them.
- Run the scoring step **twice** for a 5-10% sample (cheap) and flag any keyword whose category flipped — that's the drift detector.

**Warning signs:**
- Same keyword gets different intent labels in adjacent runs.
- Intent distribution per run varies wildly (50% transactional one day, 20% the next).
- Operator can't articulate the rubric when asked.

**Phase to address:** Phase 3 (ranking / scoring). Categorical rubric must be locked in v1 — switching to scalar scoring later is a breaking change for downstream consumers.

---

### Pitfall 4: Geo / language drift (US results when targeting UK)

**What goes wrong:**
Brief says "UK same-day grocery delivery". Skill calls Serper without explicit `gl=uk`/`hl=en-gb`, defaults to US, returns ads from Instacart and Walmart, ranks "produce" highly (US term — UK uses "veg"/"fresh"). Report ships with Americanisms, US competitors, and dollars in ad copy.

**Why it happens:**
- Serper's defaults follow the API key's account region or fall back to US.
- WebSearch tool inside Claude Code may not honour locale params in the same way Serper does.
- LLMs auto-correct UK→US spellings ("colour"→"color", "trousers"→"pants") in their summaries even when the source data was UK.

**How to avoid:**
- Require `country` and `language` as **mandatory brief fields** — skill cannot proceed without them.
- Pass `gl` (country code) and `hl` (language code) explicitly to every Serper call. Verify support: Serper documents support for `gl`, `hl`, plus city-level `location`.
- For Tavily extract, prefer competitor URLs on country-specific TLDs (`.co.uk`) when the brief is UK; pass `country` parameter where available.
- Add a **locale assertion step** in post-processing: scan the final keyword list for telltale wrong-locale tokens (e.g., "$" vs "£", "ZIP" vs "postcode", US state names) and fail the report build if matches exceed a threshold.
- For WebSearch, include the country in the query string itself (e.g., append "UK" or "in London") since locale params are unreliable there.

**Warning signs:**
- Currency symbols mismatch the brief's region.
- Competitor names in the report aren't operating in the brief's geography.
- Spelling drifts (favorite/favourite mixed in same report).

**Phase to address:** Phase 2 (signal collection). Locale plumbing must be wired through every API call and validated in Phase 4 (report assembly).

---

### Pitfall 5: Mixing intent types within a single ad group cluster

**What goes wrong:**
Cluster named "Grocery Delivery" contains: `grocery delivery near me` (transactional), `how does grocery delivery work` (informational), `is grocery delivery worth it` (commercial-investigation). One ad copy can't address all three; Quality Score tanks; CPC inflates.

**Why it happens:**
- Embedding-based or theme-based clustering groups by lexical similarity, not by intent.
- LLM clustering prompts that say "group similar keywords" produce semantic clusters, not intent-coherent ones.
- Operators assume "ad group" means "topic" — actually it should mean "topic ∩ intent".

**How to avoid:**
- **Cluster in two dimensions: theme × intent.** First classify intent (per Pitfall 3), then cluster within each intent bucket. Output ad groups as `{theme}_{intent}` (e.g., "grocery_delivery_transactional", "grocery_delivery_informational").
- Reject any cluster whose member keywords span more than one intent label. Re-cluster or split.
- The cluster name in the report should make the intent explicit so the PPC manager doesn't blend them downstream.
- Add a single-line "ad copy hint" per cluster generated from the intent + theme, so the PPC manager can sanity-check whether one ad covers the cluster.

**Warning signs:**
- A single cluster has keywords with three different verbs (buy / how / is).
- Question-style keywords ("how do I…") in the same cluster as transactional ("…cheap").
- Operator says "this cluster needs splitting" during review more than 1× per report.

**Phase to address:** Phase 4 (clustering). Must come after intent scoring (Phase 3) — order matters.

---

### Pitfall 6: Long-tail noise that nobody actually searches for

**What goes wrong:**
LLM expansion + PAA scraping produces 500 keywords; 300 are grammatically-valid-but-no-volume strings ("same-day organic grocery delivery for vegetarian families in central London under £30"). Report bloats; operator wastes review time; PPC manager pastes them into Google Ads and they become "low search volume" placeholders that never serve.

**Why it happens:**
- PAA and related-searches surface real questions, but LLMs *expand* on them and invent variations that sound real but aren't.
- No volume API in v1 means there's no way to filter zero-volume terms automatically.
- Operators conflate "long tail = good" (a 2014 SEO meme) with "long tail = useful for paid search" (which requires actual volume).

**How to avoid:**
- **Don't generate keywords; only surface them.** Phase 2 should *only* extract verbatim n-grams that appeared in source data (Serper PAA, related searches, Tavily extracts, top organic titles). LLM may rephrase but should not hallucinate variants.
- Cap keyword length: drop keywords with >7 words (Google Ads enforces a 10-word max anyway, but 7 is the practical zero-volume cliff).
- Require each keyword to have `source_diversity ≥ 2` OR appear ≥ 2 times in a single source before it makes the report. Single-mention keywords go to a separate "low-confidence" appendix, not the main table.
- Mark the report's keyword count cap explicitly (e.g., 100 keywords main + up to 50 appendix). Forces signal-over-noise.

**Warning signs:**
- Report has >200 keywords.
- More than 30% of keywords have `source_diversity` = 1.
- Multiple keywords differ only by stop-words ("for vegetarian" vs "for the vegetarian").

**Phase to address:** Phase 2 (signal collection) — extract-don't-generate rule. Phase 3 reinforces with the diversity threshold.

---

### Pitfall 7: Failing to detect close-variant duplicates

**What goes wrong:**
Report contains `grocery delivery`, `groceries delivery`, `grocery delivered`, `grocery deliveries`, `delivery groceries` as separate rows. Each occupies a slot, dilutes frequency counts (because each variant has frequency 1 instead of one canonical form having frequency 5), and Google Ads will treat them as close variants of each other anyway.

**Why it happens:**
- Naive deduplication uses exact-string match.
- Source data is messy — PAA gives "Grocery Delivery", related gives "grocery deliveries", Tavily extracts give "delivered groceries".
- Stemming + lemmatisation isn't applied, or is applied inconsistently.

**How to avoid:**
- Pipeline normalisation: lowercase → strip punctuation → lemmatise (NLTK / spaCy) → sort tokens for non-question keywords → hash. Group keywords by hash; pick the most-search-natural surface form (lowest word count, or matches Google Trends / Serper most-frequent surface form) as canonical.
- Question keywords (those starting with how/what/why/is/can/who/where/when) keep word order because intent depends on it ("how to deliver groceries" ≠ "groceries delivery how").
- Keep the variant list in the row's metadata so operator can see what was merged.
- Apply **before** ranking, so frequency aggregates correctly across variants.

**Warning signs:**
- Two report rows differ by 1 character / one suffix.
- Operator manually deletes duplicates during review.
- Frequency distribution looks suspiciously flat (everything is "1") — sign that duplicates were spread thin.

**Phase to address:** Phase 2 (signal collection / canonicalisation). Run dedup before scoring, before clustering.

---

### Pitfall 8: Tavily cost blowup from deep-crawling competitor sites

**What goes wrong:**
Brief lists 10 competitors. Skill calls Tavily Crawl (mapping + extraction) on each. At ~$0.005-0.01 per page and competitor sites with 500-2000 pages, a single run costs $25-100. Operator runs daily across 5 campaigns — bill is $5k+/month for what was supposed to be a sub-$100 line item.

**Why it happens:**
- Tavily Crawl combines mapping + extraction; a "1 URL" call can spider hundreds of pages.
- Default Tavily settings prefer broad crawl over narrow extract.
- Operator doesn't see the credit count until invoice arrives.

**How to avoid:**
- **Use `tavily_extract` not `tavily_crawl`** on a curated URL list (homepage + /pricing + /products + 1-2 category pages per competitor). Extract is bounded; crawl is not.
- Hard cap: maximum N (e.g., 5) URLs per competitor, maximum 5 competitors per run, with `extract_depth='basic'` not `'advanced'` unless brief explicitly requests it. Per Tavily docs, basic = 1 credit / 5 URLs, advanced = 2× that.
- Estimate cost before each run and surface it in the brief-confirmation turn ("This run will cost approximately X Tavily credits and Y Serper credits — proceed?"). Hard-fail if estimate exceeds an operator-set ceiling.
- Log actual credits consumed per run to a `runs/_meta/cost.csv` so monthly totals are visible without checking the Tavily dashboard.

**Warning signs:**
- A single run consumes >50 Tavily credits.
- Tavily monthly bill exceeds Serper monthly bill (Tavily is more expensive per call by ~5-10×; if it's runaway it's because crawl scope is wrong).
- Run duration exceeds 5 minutes (likely crawling, not extracting).

**Phase to address:** Phase 2 (signal collection). Set the extract-not-crawl rule and cost-ceiling check before any production runs.

---

### Pitfall 9: API key leakage in run-history files

**What goes wrong:**
Run folder contains the raw shell command or Python script invocation that includes `--serper-key=abc123` or an env-dump from debug logging. Operator commits the run folder to git or shares it via Slack. Key ends up in repo history or chat archive.

**Why it happens:**
- Debug-friendly logging dumps the request object including headers.
- Convenience scripts hardcode keys "just for now".
- Run folders accumulate `error.log` files with stack traces that include key fragments.

**How to avoid:**
- Read keys from env vars only. Never accept them as CLI args, never write them to disk.
- Centralise API calls through a single `api_client.py` module; the only place that touches `os.environ['SERPER_API_KEY']`. Everywhere else passes a client instance.
- Pre-write log filter that redacts any 32+ char hex/base64 string before writing to run folders.
- Add `runs/**/*.log` and `*secret*`, `*key*` patterns to `.gitignore`.
- Pre-commit hook (or simple script) that scans `runs/` for high-entropy strings before allowing commit.

**Warning signs:**
- Any file in `runs/` contains a string longer than 24 chars of mixed alphanumeric.
- `git status` shows `runs/` files staged accidentally.
- Operator copies an error from a run folder into Slack — review what's in those errors.

**Phase to address:** Phase 1 (skill scaffold). Establish env-var-only contract before first API call is wired.

---

## Moderate Pitfalls

These degrade quality but won't kill a campaign on their own.

### Pitfall 10: Over-clustering (every keyword is its own ad group)

**What goes wrong:**
Clustering algorithm has a tight similarity threshold; report has 80 keywords spread across 60 clusters. Operator can't realistically write 60 ad copies; defaults to 5-10 manually-merged groups, throwing away the skill's clustering work.

**Why it happens:**
- LLM clustering with a "be precise" prompt over-segments.
- Cosine-similarity thresholds tuned for retrieval (high precision) are too tight for ad grouping (which is closer to topic modelling).
- No floor on cluster size.

**How to avoid:**
- Constrain target cluster count to **5-15** per run (configurable in brief). Force re-merging if more clusters emerge.
- Minimum cluster size of 3 keywords; smaller clusters get folded into the nearest larger cluster or into a "miscellaneous" bucket.
- Use intent-bucketed clustering (see Pitfall 5) which naturally caps the count: there are only ~5 intents, so themes × intents has a known upper bound.

**Warning signs:**
- Average cluster size < 3.
- Cluster count > keyword count / 4.
- Operator merges clusters during review.

**Phase to address:** Phase 4 (clustering).

---

### Pitfall 11: Under-clustering (broad themes that mix everything)

**What goes wrong:**
Clustering produces 3 clusters: "Grocery", "Delivery", "Other". Useless — every keyword has groceries and delivery in it. PPC manager has to redo the work.

**Why it happens:**
- LLM clustering with "group broadly" prompts collapses too aggressively.
- Centroid-based clustering with too few centroids.
- No quality check on cluster diversity.

**How to avoid:**
- Reject any cluster containing >25 keywords (split it).
- Reject any cluster whose top-3 TF-IDF tokens are also the top-3 of another cluster (they're not differentiated).
- Require each cluster name to be a 2-4 word phrase that includes a differentiator beyond the brief's core terms. "Grocery" alone is invalid; "Same-Day Grocery Transactional" is valid.

**Warning signs:**
- Cluster names are single words.
- Cluster count < 4 for a >50-keyword report.
- Two clusters share their top tokens.

**Phase to address:** Phase 4 (clustering).

---

### Pitfall 12: Cluster names that don't map to ad copy

**What goes wrong:**
Cluster is named "K-Cluster 3" or "Theme A". PPC manager has to read the keyword list to figure out what the ad should say. Workflow stalls.

**Why it happens:**
- Algorithmic clustering uses index-based labels.
- LLM-generated names sometimes use abstract topic-modelling vocabulary ("Customer Retention Vector") that's accurate but unusable.

**How to avoid:**
- Cluster name = `{differentiator phrase} — {intent}` (e.g., "Same-Day Delivery — Transactional").
- Generate names from the keyword list, not from embeddings. Pick the most-frequent 2-3 word phrase that appears in ≥30% of the cluster's keywords.
- Validate names against an "ad copy fit" check: would a hypothetical ad headline using this name's words be allowed in Google Ads (≤30 chars, no banned terms)?

**Warning signs:**
- Cluster names contain numbers, "k", "theme", "topic_N".
- Cluster names don't appear (or partially appear) in the cluster's keywords.
- PPC manager renames clusters during downstream work.

**Phase to address:** Phase 4 (clustering).

---

### Pitfall 13: Capturing affiliate or competitor-of-competitor ads

**What goes wrong:**
Brief's competitors are Tesco, Sainsbury's, Ocado. Serper ads block returns ads from voucher sites, comparison aggregators, and small affiliates bidding on the brand terms. Operator extracts those as "competitor copy" and the PPC team writes against irrelevant messaging.

**Why it happens:**
- Google Ads serves whoever wins the auction at query time, not just direct competitors.
- Brand-keyword auctions attract affiliates ("get 20% off Tesco delivery!").
- Skill has no allowlist of intended competitors.

**How to avoid:**
- Filter ads block results by **display URL domain match against the brief's competitor list**. Only keep ads from domains the operator declared as competitors (or close subdomains).
- Bucket non-matching ads into a separate "Adjacent advertisers" appendix labelled clearly — useful intel but not "what your competitors say".
- Detect and flag affiliate patterns (URLs with `?ref=`, `aff_id`, common affiliate networks like awin, skimlinks, partnerize).

**Warning signs:**
- "Competitor" ad copy mentions discount codes / cashback.
- Display URL doesn't match any brief-listed competitor.
- Same advertiser appears across unrelated keyword themes.

**Phase to address:** Phase 5 (competitor ad copy extraction).

---

### Pitfall 14: Stale / cached / personalised ad block results

**What goes wrong:**
Serper returns the ads block, but the result reflects a cached SERP from 30 minutes ago, or the auction at the time of scrape didn't include the current top bidder, or it was personalised to Serper's data-centre IP. Report shows "competitor X is top bidder" when they aren't, today, in the operator's region.

**Why it happens:**
- SERP APIs cache results 15-60 minutes for cost reasons. Some return stale ads while organic results are fresh.
- Ads auctions vary by time-of-day, device, intent, geo, prior session.
- Single SERP scrape is a sample of one — not representative.

**How to avoid:**
- For each high-priority cluster, scrape **3-5 representative keywords** and union the ad copy. Don't trust a single keyword's ads block.
- Pass `gl`/`hl` and a `device` parameter (mobile vs desktop) per the brief. Document in the report which device + locale was used.
- Note in the report's competitor section: *"Ads observed on {date} from {locale}/{device}; live auctions vary."*
- Detect freshness: if Serper response includes a cache timestamp or age field, log it. Treat results >30 min old as cached and re-fetch.
- For Google Ads Transparency Center as a future enhancement: that's a more reliable source for "what is X advertiser actually running" — note for v2.

**Warning signs:**
- Same ad text repeats verbatim across 10+ different keywords (likely cached / generic placeholder).
- Operator says "we never see them top of page" about a "top competitor" the report flagged.
- Ads block contains 0 ads — possibly cached from a low-commercial-intent fetch.

**Phase to address:** Phase 5 (competitor ad copy extraction).

---

### Pitfall 15: Over-aggressive negative keywords

**What goes wrong:**
Skill auto-suggests negatives like `cheap`, `free`, `diy`, `tutorial`, `review`. Operator pastes them all in. Campaign blocks valid traffic — "cheap grocery delivery" was actually a high-converting term for the budget audience.

**Why it happens:**
- LLMs over-generalise: "informational keywords are bad for transactional campaigns" → blocks all info-modifiers.
- One-size-fits-all negative templates assume every brand competes on premium positioning.
- No tier separation between "definitely block" vs "consider blocking".

**How to avoid:**
- Tier negatives into three lists in the report:
  1. **Strong negatives** (almost always block): `job`, `jobs`, `salary`, `career`, `wikipedia`, `definition`, `meaning`, the literal word `free` only when the brand isn't free, competitor brand names if the brief says "exclude brand bidding".
  2. **Considered negatives** (block if the brand is premium): `cheap`, `discount`, `coupon`, `voucher` — but explicitly note that for a value-tier brand these are *positive* signals.
  3. **Investigate**: terms that surfaced in research but might be valid traffic (e.g., `review`, `vs`, `alternative`).
- Generate negatives from the **brief's explicit positioning** (premium vs value, B2B vs B2C, paid vs free product), not from a fixed list.
- For each suggested negative, include the source keyword that triggered it so operator can sanity-check.

**Warning signs:**
- Negatives list includes the brand's own positioning words.
- More than 30 negatives suggested per run.
- Operator blanket-pastes negatives without review.

**Phase to address:** Phase 6 (negatives). After ranking + clustering so negatives reflect what was actually surfaced.

---

### Pitfall 16: Missing the obvious negatives

**What goes wrong:**
Skill produces a sophisticated negatives list but misses the no-brainers — `jobs`, `careers`, `wikipedia`, brand-mismatch terms (e.g., a B2B SaaS forgetting to negate the consumer-product interpretation of its name).

**Why it happens:**
- LLM-driven negative generation focuses on "interesting" patterns and forgets the boilerplate.
- The "always negate" list isn't codified in the skill.

**How to avoid:**
- Maintain a **fixed baseline negatives list** in the skill (`jobs`, `salary`, `career`, `internship`, `wikipedia`, `definition`, `meaning`, `pdf`, `download free`, `torrent`, `for sale used` — adjust per brief). These are appended to every report unconditionally.
- For brand-mismatch detection, ask the LLM specifically: "List 5 unrelated meanings or homonyms of the brand name." Negate those.
- Job/recruitment filter: any keyword containing job/career/salary/internship/hiring goes to negatives automatically.

**Warning signs:**
- Operator manually adds `jobs` after every run.
- Brand has a homonym that wasn't negated (e.g., "Apple" without negating fruit).
- Free-seeking modifiers absent from negatives for a paid product.

**Phase to address:** Phase 6 (negatives).

---

### Pitfall 17: Skill prompt drift / instruction overrun

**What goes wrong:**
The skill markdown grows over months — every fixed bug adds a "do X" line, every misbehaviour adds a "never do Y" line. After 6 months it's 3000 lines, the LLM ignores the middle, and behaviour regresses on edge cases that earlier rules covered.

**Why it happens:**
- One-skill-one-job rule is violated as features accrete.
- Negative instructions accumulate without being deduped or restructured.
- Context rot in the model when the skill prompt + run context push past ~300-400k tokens.

**How to avoid:**
- One skill file per phase concern. Splitting into sub-skills or sub-agents (intake / collection / scoring / clustering / report) is better than one mega-skill. Per Anthropic guidance: one skill, one job.
- Keep the top-level skill short (<500 lines). Push detail into referenced helper scripts and `SKILL.md` sub-files loaded only when needed.
- Per-step constraint design: each phase has its own constraints, not a global blob. Convergent steps (scoring) get tight rules; divergent steps (cluster naming) get permissive ones.
- Version the skill (`v0.1.0`, `v0.2.0`) and log the version per run. Regressions become detectable across run-history.
- Periodic prune: review skill markdown quarterly, delete rules that no longer trigger (no warning signs in last 50 runs).

**Warning signs:**
- Skill markdown >1000 lines.
- Same behaviour rule restated 3+ times in different phrasings.
- New rules contradict existing ones.
- Operator notices behaviour that was correct 2 months ago is now broken.

**Phase to address:** Phase 1 (skill scaffold) — set the size budget and structure. Reinforced every phase by adding helper scripts not skill text.

---

### Pitfall 18: Markdown table escaping issues with pipes and quotes

**What goes wrong:**
Competitor ad copy contains a literal `|` or unescaped quotes. Markdown table renders broken. Operator pastes into Slack/Notion and it's garbage.

**Why it happens:**
- Ad copy frequently contains `|` ("Free Delivery | Same Day | Order Now").
- Smart quotes from extracted content collide with markdown.
- Newlines in ad descriptions break table rows.

**How to avoid:**
- Sanitise table cells before write: replace `|` with `\|` (or with `/`), strip newlines, normalise smart quotes to ASCII, truncate cells to 120 chars with ellipsis.
- For long content (full ad descriptions), use a separate sub-section with code-fenced blocks instead of table cells.
- Validate generated markdown: parse it with `markdown` lib post-write; if parse fails, fail the run with a clear error.

**Warning signs:**
- Report has malformed tables when previewed.
- Cells contain `|` literally.
- Pasting into Notion/Slack produces visual breakage.

**Phase to address:** Phase 7 (report assembly).

---

### Pitfall 19: Run folder bloat

**What goes wrong:**
After 6 months, `runs/` has 500 dated subfolders, each 5-50MB of raw API responses. Repo size 20GB; cloning takes 10 minutes; grep is slow.

**Why it happens:**
- Every run dumps raw Serper + Tavily JSON for "debugging".
- No retention policy.
- Run folders are committed to git instead of being .gitignored.

**How to avoid:**
- Run folder structure: `runs/YYYY-MM-DD_slug/{brief.md, report.md, raw/}` where `raw/` is .gitignored or zipped.
- Retention: keep `brief.md` + `report.md` indefinitely (small, valuable), purge `raw/` after 30 days.
- Compress old runs (`tar.gz` per quarter) to reduce file count.
- `.gitignore` entry for `runs/**/raw/` from day 1.
- Optional: separate the run folder from the code repo entirely — `runs/` lives in a parallel directory or a different repo.

**Warning signs:**
- Repo > 100MB.
- Single run folder > 100MB.
- `git status` slow.

**Phase to address:** Phase 1 (skill scaffold). Set folder structure + .gitignore before first run.

---

### Pitfall 20: Inconsistent briefs across operator sessions

**What goes wrong:**
Even with one operator, briefs drift in detail — a Monday brief is exhaustive, Friday's is two lines because operator was rushed. Reports are wildly different quality. Comparison across runs becomes meaningless.

**Why it happens:**
- Conversational intake permits "good enough" answers.
- No template enforcement.

**How to avoid:**
- Enforce a brief schema (10-15 fields). Skill loops on missing fields until all are answered (even if "n/a — generic" with explicit acknowledgement).
- Save the brief as both prose (for the LLM) and structured YAML (for diffing across runs).
- For repeat campaigns, allow `--brief-from runs/2026-04-15_grocery_delivery/brief.yaml` to inherit + override.

**Warning signs:**
- Brief files vary 5× in line count across same-campaign runs.
- Reports for "the same" campaign produce different cluster structures unexpectedly.

**Phase to address:** Phase 1 (brief intake).

---

### Pitfall 21: Operator can't trace why a keyword was included

**What goes wrong:**
PPC manager queries "why is `grocery delivery sunday` in the report?" — operator can't say. The keyword had `frequency: 1` and `source_diversity: 1` but slipped through. Trust erodes.

**Why it happens:**
- Per-keyword provenance not logged.
- Aggregation throws away the source URL/snippet that surfaced each term.

**How to avoid:**
- For every keyword, persist a `sources` array: `[{source: 'serper-paa', url: '...', snippet: '...', timestamp: '...'}]`. At least one entry per source-fragment that contributed.
- Report includes a hidden details block (HTML `<details>` tag inside markdown) per keyword showing top 2 sources.
- Run folder retains source-mapping JSON so any keyword can be traced post-hoc.

**Warning signs:**
- Operator answers "I don't know why it's there".
- Same question asked twice for two different keywords.

**Phase to address:** Phase 2 (signal collection — emit provenance) + Phase 7 (report — surface provenance).

---

### Pitfall 22: Hard to compare two runs of the same campaign over time

**What goes wrong:**
Operator runs campaign X in March and again in May. They want to know what changed (new keywords, dropped keywords, intent shifts). With markdown-only output and no structured side, diffing is manual.

**Why it happens:**
- Output is only markdown.
- Keyword identity isn't stable (canonicalisation changed between runs, or LLM names clusters differently).

**How to avoid:**
- Alongside `report.md`, write `report.json` with stable keys: `{keywords: [{canonical, sources, intent, signal_count, source_diversity, cluster_id}], clusters: [{name, members}]}`. JSON is for diffing; markdown is for reading.
- Provide a `gsd compare runs/A runs/B` script that produces a markdown delta (new / dropped / intent-shifted).
- Stable cluster IDs: derive cluster ID from the canonical-form hash of the cluster's top-3 keywords, not from a counter.

**Warning signs:**
- Operator copies two reports side by side in a doc to compare manually.
- "What changed?" is asked but not answered.

**Phase to address:** Phase 7 (report assembly) — emit JSON twin. Phase 8+ (out of v1 if scope tight, but the JSON twin must ship in v1 even if compare script doesn't).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode locale (e.g., always UK) | Skip locale plumbing in v1 | Re-architect when first non-UK campaign hits; reports silently wrong | Never — locale is single field, plumb it day 1 |
| Single LLM call to "score and cluster all keywords" in one prompt | Less code | Drift, cost, no caching of intermediate, can't reuse intent scores | Never — separate the steps |
| Skip canonicalisation, dedupe by exact match | Faster shipping | Reports bloat with variants; ranking is wrong | Only for first prototype; must fix before any operator other than author uses it |
| Inline API keys in helper scripts during dev | "Just for testing" | Will leak; key rotation pain | Never — env vars from day 1, even in dev |
| Don't emit JSON twin, only markdown | Less code | Can't diff runs, can't compare campaigns over time | Never if multiple runs per campaign expected; otherwise acceptable for one-shot use only |
| No cost ceiling check before run | Faster prototyping | Bill shock from first stuck-in-loop run | Acceptable for first 5 runs while calibrating; then mandatory |
| Skip provenance tracking | Smaller payload, simpler code | Operator can't defend keyword choices; trust issue | Never — provenance is core to the trust contract with PPC team |
| Use `tavily_crawl` instead of `tavily_extract` | "Discovers more" | Cost blowup, slow, unfocused | Only with hard page cap and explicit operator opt-in per run |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Serper.dev | Using default locale (US-biased) | Always pass `gl` and `hl` per brief; verify per call |
| Serper.dev | Treating `searchParameters` echo as confirmation of locale | Inspect actual results — verify TLDs/currency match expectations |
| Serper.dev | Calling without `num` parameter, getting variable result counts | Set `num=20` (or higher) explicitly for predictable signal volume |
| Serper.dev | Assuming ads block always present | Many queries return zero ads; handle empty `ads` array gracefully |
| Serper.dev | Treating PAA as deterministic | PAA varies run-to-run; pull 2-3 times per high-value query and union |
| Tavily | Using `crawl` for what should be `extract` | Curate URL list, use `extract` with `basic` depth |
| Tavily | Not setting `extract_depth`, defaulting to `advanced` | Default to `basic`, opt into `advanced` only when content is JS-heavy |
| Tavily | Ignoring failed extractions silently | Log failures with URL; bills count both successful and attempted |
| WebSearch (Claude Code built-in) | Assuming structured PAA/related fields like Serper | WebSearch returns prose snippets; parse for keywords with regex / LLM, don't expect structured fields |
| WebSearch | No locale targeting | Embed locale terms in the query string itself ("UK same-day grocery delivery") |
| All three | Combining results without source labels | Emit `source: 'serper-paa' \| 'serper-related' \| 'serper-organic' \| 'tavily' \| 'websearch'` per signal, always |
| LLM scoring (Claude API) | Using temperature default | `temperature=0` for scoring; `temperature=0.3` only for cluster naming and ad-copy hints |

---

## Performance Traps

This is a low-volume tool (one operator, < 50 runs/month expected). Performance traps here are about *cost* and *runtime per run*, not concurrency.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential API calls when parallel is safe | Run takes 5+ min | Parallelise Serper queries (different keywords) and Tavily extracts (different URLs) with `asyncio.gather` or `concurrent.futures`; respect Serper's 300 q/s ceiling | Once per-run keyword count > 20 or competitor count > 3 |
| Re-scoring the same keyword across runs with no cache | Cost scales with run frequency | Cache LLM intent scores keyed by `(canonical_keyword, locale, rubric_hash)`; even without SERP cache, intent cache is safe (intent is locale-stable) | Once same operator runs the same brief 2+ times |
| Pulling all PAA / related across all keywords in one Serper batch | Single failure loses everything | Per-keyword Serper calls with retry/backoff; treat each as independent | Once any single Serper call fails (network blip) |
| LLM context window inflation | Slow, expensive per call | Batch scoring in groups of 25-50 keywords with rubric anchors; don't pass the whole keyword list every prompt | Once keyword count per run > 100 |
| Tavily on every run | Bill grows linearly | Default to "Tavily competitors only on first run per campaign; reuse extracts for repeat runs within 30 days" | Once same campaign re-runs > 2× |
| Markdown report rendering with all data inline | Files become huge, slow to open in editors | Cap main table at top-100 keywords; appendix is collapsed `<details>` | Once keyword count > 200 |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| API keys in run folder logs | Key leak via screenshare / git push / Slack | Centralised log filter redacts high-entropy strings; keys read from env only |
| Run folders committed to public repo | Brief leak (proprietary campaign info) | `runs/` in `.gitignore` from day 1; private repo regardless |
| Sharing markdown reports in Slack with embedded competitor URLs | URL might be `?utm` tagged with internal trace IDs | Strip query strings from URLs in reports unless they're in scope |
| Using Tavily's URL-extract on internal/staging URLs by mistake | Sends internal content to Tavily | Validate URLs are publicly resolvable before extract; explicit allowlist of competitor domains |
| Logging full brief text including any operator-pasted PII | Accidental PII storage | Briefs should be campaign-context only; explicit reminder in intake "do not paste customer data"; redact obvious PII patterns (email, phone) before logging |
| Trusting brand-name input as-is in API calls | Prompt-injection from brief text into LLM scoring | Sanitise brief content before injecting into LLM prompts (escape backticks, strip prompt-injection patterns); separate "data" from "instructions" with clear delimiters |
| Storing API keys in `.env` committed to git | Standard credentials leak | `.env` in `.gitignore`; provide `.env.example` only |

---

## UX Pitfalls

These are operator-facing — the operator IS the user in v1.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No cost preview before run | Bill shock | Show estimated Serper + Tavily credit cost in pre-run summary; require explicit "proceed" |
| Report generated without explaining the methodology | Operator can't defend choices to PPC managers | Every report has a "How this was made" section: data sources, scoring rubric, cluster algorithm version, run cost |
| All keywords in one giant table | Hard to scan | Split: top-50 main table, rest in collapsible appendix |
| Cluster names abstract / numeric | Operator can't tell what's in each | Cluster names = differentiator phrase + intent; max 4 words |
| No visible run history index | Operator can't find past work | Generate `runs/INDEX.md` listing all runs with brief one-liner; updated each run |
| Same keyword in multiple clusters silently | Operator confused; PPC manager double-bids | Each keyword belongs to exactly one cluster; multi-cluster candidates flagged for operator review |
| No "what changed?" for repeat runs | Operator manually diffs | Auto-emit `delta.md` when prior run for same campaign exists |

---

## "Looks Done But Isn't" Checklist

Before declaring v1 ready, verify each:

- [ ] **Brief intake:** Often missing locale, language, or positioning fields — verify all 10-15 fields are non-empty in the saved brief, including explicit "n/a" for genuinely unused fields.
- [ ] **Locale plumbing:** Often missing on one of three APIs — verify `gl`/`hl` on every Serper call, `country` on every Tavily call, locale terms in every WebSearch query.
- [ ] **Keyword frequency labelling:** Often labelled "volume" or "score" — verify the column is `signal_count` and the report has the "How to read this" disclaimer.
- [ ] **Provenance:** Often missing — verify every keyword has at least one `source` entry persisted to the run JSON.
- [ ] **Intent rubric stability:** Often forgotten — verify two consecutive runs of the same brief produce ≥90% intent agreement on the same keywords.
- [ ] **Cluster intent purity:** Often missing — verify no cluster contains keywords with more than one intent label.
- [ ] **Negative tiering:** Often missing — verify negatives are split into Strong / Considered / Investigate, not one flat list.
- [ ] **Cost ceiling check:** Often missing — verify the skill estimates and confirms cost before any paid API call.
- [ ] **Markdown sanitisation:** Often missing — verify a competitor with `|` in their ad copy renders the table correctly.
- [ ] **JSON twin:** Often skipped "for v2" — verify `report.json` is emitted alongside `report.md` and contains all keyword-level fields.
- [ ] **Run folder retention:** Often unset — verify `.gitignore` covers `runs/**/raw/` and the README documents retention policy.
- [ ] **API key handling:** Often loose — verify keys are env-only, no script accepts them as args, log filter redacts high-entropy strings.
- [ ] **Skill prompt size:** Often growing — verify top-level skill markdown is < 500 lines.
- [ ] **Locale assertion:** Often missing — verify post-run lint catches currency / spelling mismatches.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Frequency misread as volume (downstream report consumed) | LOW | Add "How to read this" section to existing reports, prepend disclaimer; rename column in JSON twin and regenerate markdown from JSON |
| API key leaked in run folder / git history | HIGH | Rotate keys immediately; `git filter-repo` to scrub history; audit Tavily/Serper usage for unauthorised calls; force-push (coordinate with anyone who has clones) |
| Locale drift in shipped report | MEDIUM | Regenerate run with correct locale; mark old run folder with `LOCALE_DRIFT.md` note; if downstream campaign already built, PPC manager re-targets — keyword set usually still mostly valid |
| Intent scoring drift between runs | MEDIUM | Lock to categorical rubric, re-score affected runs, cache scores; document the cutover version in the report |
| Tavily cost blowup mid-run | LOW (caught early) / MEDIUM (caught on invoice) | Add hard ceiling that aborts; refund unlikely; calibrate by re-running a sample with extract-only |
| Cluster drift across reruns | LOW | Stable cluster IDs from canonical-keyword hash; re-emit prior reports with new IDs; document cutover |
| Skill prompt overrun | MEDIUM | Refactor to sub-skills/sub-agents; archive old skill version; regression-test against a saved corpus of 5 prior briefs |
| Stale ad block results | LOW | Re-fetch with explicit locale + device; union across multiple representative keywords |
| Over-aggressive negatives shipped | LOW | Operator removes from Google Ads; update skill to mark them "Considered" not "Strong"; add brand positioning to brief schema if missing |
| Run folder bloat | LOW | Compress old `raw/` dirs; prune per retention policy; add `.gitignore` retroactively |

---

## Pitfall-to-Phase Mapping

Recommended phase ordering with each pitfall mapped to the phase that prevents it. Pitfalls without a phase number are cross-cutting and should be addressed in the skill's quality gates.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Thin brief / GIGO | Phase 1 (intake) | Brief schema has ≥10 fields, all non-empty in saved file |
| 2. Frequency-as-volume confusion | Phase 3 (ranking) + Phase 7 (report) | Column named `signal_count`; "How to read this" present |
| 3. LLM intent scoring drift | Phase 3 (scoring) | Categorical rubric + temperature=0 + anchor examples logged |
| 4. Geo / language drift | Phase 2 (collection) + Phase 7 (lint) | All API calls pass locale; post-run linter catches mismatches |
| 5. Mixed intent in clusters | Phase 4 (clustering, after Phase 3) | No cluster spans multiple intent labels |
| 6. Long-tail noise | Phase 2 (extract-don't-generate) + Phase 3 (diversity threshold) | Keywords < 200; source_diversity ≥ 2 for main table |
| 7. Close-variant duplicates | Phase 2 (canonicalisation) | Lemmatised hash dedup applied before scoring |
| 8. Tavily cost blowup | Phase 2 (collection) + Phase 1 (cost ceiling) | extract-not-crawl; per-run estimate confirmed by operator |
| 9. API key leakage | Phase 1 (skill scaffold) | env-only contract; .gitignore from day 1; log redaction filter |
| 10. Over-clustering | Phase 4 | Cluster count 5-15; min cluster size 3 |
| 11. Under-clustering | Phase 4 | Max cluster size 25; differentiated top tokens |
| 12. Bad cluster names | Phase 4 (naming) | Names = differentiator + intent, derived from keywords |
| 13. Affiliate / wrong-competitor ad capture | Phase 5 | Domain allowlist filter; affiliate-pattern detector |
| 14. Stale / cached ad results | Phase 5 | Multi-keyword union per cluster; freshness logged |
| 15. Over-aggressive negatives | Phase 6 | Tiered output; brand-positioning-aware generation |
| 16. Missing obvious negatives | Phase 6 | Baseline negatives appended unconditionally |
| 17. Skill prompt drift | Phase 1 (structure) + ongoing | Top-level skill < 500 lines; quarterly review |
| 18. Markdown escape errors | Phase 7 (report) | Sanitiser + parse-validation post-write |
| 19. Run folder bloat | Phase 1 | Folder structure + .gitignore + retention policy documented |
| 20. Inconsistent briefs across sessions | Phase 1 (intake schema) | Structured YAML brief saved; field count check |
| 21. Untraceable keyword inclusion | Phase 2 (provenance) + Phase 7 (surface in report) | Every keyword has ≥1 source entry in report JSON |
| 22. Can't compare runs over time | Phase 7 (JSON twin) + post-v1 compare script | `report.json` emitted; stable canonical keys + cluster IDs |

---

## Sources

- [Google Ads Keyword Match Types Explained: Broad, Phrase, Exact (2026)](https://www.stackmatix.com/blog/google-ads-keyword-match-types-guide) — match-type expansion behaviour
- [Avoid Mixing Informational and Transactional Keywords in Google Ads](https://www.search-south.com/2026/02/18/avoid-mixing-informational-and-transactional-keywords-in-google-ads/) — intent-mixing performance impact
- [Top 10 Google Ads Mistakes to Avoid in 2026 (Search Engine Land)](https://searchengineland.com/google-ads-mistakes-avoid-449288) — keyword research methodology mistakes
- [Google Ads no longer runs on keywords. It runs on intent. (Search Engine Land)](https://searchengineland.com/google-ads-intent-not-keywords-468271) — SKAGs deprecated, intent-clustering
- [Google Ads Common Mistakes to Avoid (2026)](https://www.get-ryze.ai/blog/google-ads-common-mistakes-to-avoid-guide-ai) — broad-match overuse, ad-group fragmentation
- [Serper.dev official site](https://serper.dev/) — rate limits, country/locale params, pricing
- [Serper documentation (via Sim Docs)](https://docs.sim.ai/tools/serper) — `gl`/`hl`/`location` parameters
- [Tavily API Credits & Pricing (official docs)](https://docs.tavily.com/documentation/api-credits) — extract vs crawl cost model
- [Tavily Pricing — Firecrawl analysis](https://www.firecrawl.dev/blog/tavily-pricing) — cost-at-scale failure modes
- [SERP API guide — RapidSeedbox](https://www.rapidseedbox.com/blog/serp-api-guide) — cached vs real-time results, ads block freshness
- [How to Stop Claude Code Skills from Drifting (DEV Community)](https://dev.to/akari_iku/how-to-stop-claude-code-skills-from-drifting-with-per-step-constraint-design-2ogd) — per-step constraint design for skill prompt drift
- [Claude Code best practices (official docs)](https://code.claude.com/docs/en/best-practices) — one-skill-one-job, negative instructions, context window discipline
- [Claude Code Skills: A Practical Guide for 2026 (DEV Community)](https://dev.to/muhammad_moeed/claude-code-skills-a-practical-guide-for-2026-3f6p) — skill structuring, sub-skill composition
- Operator-domain experience: McGrocer PPC operations context (per project brief)

---
*Pitfalls research for: Google Ads keyword research agent (Claude Code skill)*
*Researched: 2026-05-08*
