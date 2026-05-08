---
description: Run Google Ads keyword research from a campaign brief — produces ranked keyword tables, ad group clusters, competitor ad copy, and tiered negative keyword lists. Use when the operator says "keyword research", "Google Ads research", "PPC keywords", "ad group clusters", or pastes a campaign brief mentioning industry / product / location / language / audience.
allowed-tools: Bash(uv run *) Read Write WebSearch
---

# Google Ad Research

Turn one campaign brief into campaign-ready Google Ads keyword research:
ranked keyword tables, ad-group clusters, competitor ad copy, and tiered
negative keyword lists. Single-operator skill. Filesystem-only output.
Phase 1 of the workflow handles brief intake and run-folder creation;
Phases 2-6 (signal collection, ranking, clustering, competitor intel,
report assembly) land in subsequent skill updates.

## Mission

The operator pastes a free-form campaign brief (or asks you to research
keywords for a campaign). You loop on the brief until five required fields
are non-empty, ask conditional follow-ups for relevant optional fields,
render the brief as markdown, and call `run_init.py` to seal a dated run
folder. You stop at the end of Phase 1 — do NOT proceed to any signal
collection or paid API call yet.

## Workflow

### Step 1: Capture the brief

Ask the operator to paste a campaign brief. Free-form prose is fine; bullet
points are fine; a short paragraph is fine. Acknowledge whatever they paste.

If the operator just said "research keywords for X" without pasting a brief,
ask them to provide more context (industry, product, location, language,
audience).

**Do not advance to Step 2 yet.**

### Step 2: Extract and validate the five required fields

From whatever the operator pasted (or said), extract these five required fields:

1. **industry** — what sector / vertical (e.g., "online groceries", "B2B SaaS", "DTC fashion")
2. **product** — what specific product/service this campaign promotes (e.g., "same-day grocery delivery", "AI-powered onboarding tool", "sustainable activewear")
3. **location** — country/region targeted (e.g., "UK", "London", "US-California", "EU-DACH")
4. **language** — primary search language (e.g., "en-GB", "en-US", "de-DE")
5. **audience** — who the campaign targets (e.g., "households 25-45 in metro areas", "growth-stage SaaS founders", "Gen Z urban professionals")

For each field, treat these answers as EMPTY (must re-prompt):
- empty string / blank
- "n/a" / "N/A" / "tbd" / "TBD"
- "you decide" / "you choose" / "your call"
- "any" / "anything"
- a question mark or `?`

**Do not advance to Step 3 if ANY of the five required fields is empty (per the rules above).**

If a field is empty, re-prompt with this exact pattern:
> "I still need {missing field name(s)}. {field-specific suggestion}. What should I use?"

Examples of field-specific suggestions:
- industry: "e.g., 'online groceries', 'B2B SaaS', 'DTC fashion'"
- product: "the specific product or service this campaign sells"
- location: "country, region, or city — e.g., 'UK' or 'San Francisco Bay Area'"
- language: "primary search language code, e.g., 'en-GB', 'en-US', 'de-DE'"
- audience: "who you want to reach — e.g., 'busy parents 25-45'"

Loop until all five fields are non-empty. Don't guess. Don't infer.

### Step 3: Solicit optional fields (only when relevant)

For each of these optional fields, ask a follow-up ONLY when the trigger fires.
Do NOT ask all five every time — that buries the operator in noise.

| Optional field | Trigger to ask follow-up |
|----------------|-------------------------|
| **budget** | The brief mentions cost, scale, spend ceiling, daily/monthly budget, or "we have $X to spend" |
| **geo exclusions** | The location targets a region with known sub-market overlap (UK excluding NI; US excluding HI/AK; "Europe" — ask which countries) |
| **language exclusions** | The location is multilingual (Belgium, Switzerland, Canada) and only one language matters |
| **brand terms** | The brief names the brand or competitor brands but does not list every term/variation |
| **competitor URLs** | The brief names competitors by name but does not provide URLs |

When you ask, ask ONE field per turn. After the operator answers, re-evaluate whether other triggers now fire. Skip silently when no trigger fires.

**Do not advance to Step 4 if you opened an optional follow-up loop without resolving it.**

### Step 4: Render the brief and save it

When all required fields are non-empty (and any opened optional follow-ups are resolved), render the brief as markdown using this template VERBATIM (substitute placeholders; omit empty optional fields entirely; preserve the operator's raw paste at the end):

```markdown
# Campaign Brief

**Captured:** {ISO timestamp the operator can read, e.g., 2026-05-08 14:30 UTC}

## Required

- **Industry:** {industry}
- **Product:** {product}
- **Location:** {location}
- **Language:** {language}
- **Audience:** {audience}

## Optional

{Include only the optional fields that were filled. Omit the entire "## Optional" section if no optional fields were filled.}
- **Budget:** {budget}
- **Geo exclusions:** {geo_exclusions}
- **Language exclusions:** {language_exclusions}
- **Brand terms:** {brand_terms}
- **Competitor URLs:** {competitor_urls}

## Raw operator paste

> {verbatim original brief text, indented as a blockquote — preserve line breaks
>  by prefixing each line with "> "}
```

Write this rendered markdown to a temporary file using the Write tool. Pick a path under the OS temp dir, e.g., on Windows `${TEMP}\gar-brief.md`, on macOS/Linux `/tmp/gar-brief.md`.

Then call `run_init.py`, piping the temp file as stdin:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" --slug-source "{product field value}" < "/tmp/gar-brief.md"
```

(Use the actual temp path you wrote to. Quote `${CLAUDE_SKILL_DIR}` because operator paths may contain spaces.)

Parse the script's stdout — it is exactly one JSON line containing:
- `run_dir` — absolute path to the new run folder
- `slug` — derived slug
- `timestamp` — UTC ISO timestamp
- `brief_path` — absolute path to the saved brief.md

**Do not advance if any of the following:**
- The script exits non-zero (codes 2 or 3 — read stderr; surface the error to the operator).
- Stdout is empty.
- Stdout is not parseable JSON.
- `run_dir` does not exist on disk after the call (verify with the Read tool or a quick `ls`).

If any failure happens, do NOT retry silently — explain the failure to the operator and ask how to proceed. Phase 1 has no paid API spend; re-running is free.

### Step 5: Confirm and stop

Tell the operator: "Run folder ready at `{run_dir}`. Brief saved at `{brief_path}`. Phase 1 complete — signal collection (Phase 2) lands in a future skill update."

**If Phase 2 signal collection is not yet in this SKILL.md, stop here.** Otherwise continue to Step 6.

## Anti-patterns (do not do these)

- **Never accept a thin brief.** A one-line "research grocery delivery keywords" is an empty brief — re-prompt for all five required fields.
- **Never guess missing required fields from context.** "Online groceries" does not imply "UK households" — ask.
- **Never write API keys to the run folder.** This skill currently makes zero API calls; Phase 2+ uses `lib/config.load_env()` only. If you ever see `SERPER_API_KEY` or `TAVILY_API_KEY` written to disk, STOP and surface it.
- **Never bypass `run_init.py` by writing brief.md directly.** The script owns the run folder layout (timestamp, slug, raw/ subfolder, collision suffix). Hand-rolling defeats Pitfall 19/20 mitigations.
- **Never embed the brief in `--slug-source`.** Slug-source is one phrase (typically `product`). The full brief goes through stdin.
- **Never let SKILL.md grow past 500 lines.** Extract step rubrics into `.claude/skills/google-ad-research/references/{step-name}.md` and link them — but Phase 1 should not need any references yet.

## Reference: tools you may use in Phase 1

- `Bash(uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" ...)` — the single helper script
- `Write` — to drop the rendered brief markdown into a temp file
- `Read` — to verify the run folder + brief.md exist after `run_init.py` succeeds

`WebSearch` is allowed in the frontmatter for Phase 2 use — do NOT call it in Phase 1.

---

## Phase 2: Signal Collection

> Prerequisites: Phase 1 complete — `run_dir` and `brief.md` exist. `SERPER_API_KEY` and `TAVILY_API_KEY` set in `.env`.

### Step 6: Generate seed keywords

Read `brief.md` from `run_dir`. From the five required fields (industry, product, location, language, audience), generate 5-15 seed phrases:
1. The exact product phrase (e.g., "same-day grocery delivery")
2. 2-3 product + location composites (e.g., "london grocery delivery", "uk same-day grocery delivery")
3. 2-3 product + audience composites (e.g., "grocery delivery for busy parents")
4. 1-2 intent variations (e.g., "best grocery delivery", "cheap grocery delivery uk")
5. 1-2 brand or comparison variations IF Brand terms are in brief (e.g., "tesco vs ocado delivery")

Skip variations that contradict Geo exclusions or Language exclusions in brief.

**Do not advance to Step 7 until you have 5-15 seed phrases written out.**

### Step 7: WebSearch baseline (free signal)

Call WebSearch 3-5 times using the seed phrases. Embed locale explicitly in every query string (e.g., "same day grocery delivery UK", "best grocery delivery London 2026") — do NOT rely on user_location parameter.

Suggested query pattern for a UK grocery campaign:
- "{product} {location}" (e.g., "same day grocery delivery uk")
- "best {product} {location}" (e.g., "best grocery delivery london")
- "how to {product intent} {location}" (e.g., "how to get grocery delivery uk")
- "{brand} vs {competitor} delivery" (only if brand terms present in brief)

After all WebSearch calls complete, write the digested findings as a structured JSON file using the Write tool:

```json
{
  "source": "websearch-baseline",
  "queries": [
    {"q": "<query string>", "locale": "<location/language from brief>"}
  ],
  "results": [
    {"query": "<q>", "title": "<title>", "url": "<url>", "snippet": "<snippet>", "page_age": "<age>"}
  ],
  "extracted_keywords": [
    {"keyword": "<phrase from snippet>", "from_query": "<q>", "snippet_excerpt": "<short excerpt>"}
  ],
  "captured_at": "<ISO timestamp>"
}
```

Write to: `{run_dir}/raw/websearch-baseline.json`

**Rules for extracted_keywords:** Extract verbatim keyword phrases (2-7 words) that appear in result titles and snippets. Do NOT invent variations — only phrases explicitly present in the WebSearch output. This is extraction, not generation (Pitfall 6 mitigation).

**Do not advance to Step 8 until `raw/websearch-baseline.json` exists.**

### Step 8: Run Serper fetch and Tavily extract

Derive locale parameters from brief:
- `gl` = lowercased country code from Location field (e.g., "UK" → "uk", "United Kingdom" → "uk")
- `hl` = language tag from Language field (e.g., "en-GB" stays "en-GB"; "English" → "en")

Run Serper (passing all seeds from Step 6):
```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/serp_fetch.py" \
  --run-dir "{run_dir}" \
  --seeds {seed1} {seed2} ... \
  --gl {gl} \
  --hl {hl}
```

Parse stdout JSON. Surface `organic_count`, `paa_count`, `related_count`, `ads_count`, `credits_used` to operator.

If exit code 2 (retryable): tell operator "Serper returned a transient error — retry? (y/n)". Re-run once if yes. If exit code 3: stop and surface the error; do not proceed.

Run Tavily extract for each competitor domain in brief's Competitor URLs field (up to 5 domains, up to 5 URLs each):
```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/tavily_extract.py" \
  --run-dir "{run_dir}" \
  --competitor "domain1:url1,url2,url3" \
  --competitor "domain2:url1,url2"
```

If no competitor URLs in brief: skip Tavily (no `--competitor` args means Tavily step is skipped; log "no competitor URLs — skipping Tavily extract").

Parse stdout JSON. Surface `competitor_count`, `urls_succeeded`, `urls_failed`, `credits_used`.

If exit code 2 (quota): warn operator "Tavily quota exceeded — continuing with partial data". If exit code 3: stop and surface error.

**Do not advance to Step 9 until both scripts have exited (0 or 2 with partial data accepted).**

### Step 9: Merge signals

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/merge_signals.py" --run-dir "{run_dir}"
```

Parse stdout JSON. Confirm `{run_dir}/keywords.json` exists. Surface `keywords_count`, `source_diversity_avg`, `variants_merged` to operator.

If exit code 3: surface error; do not proceed.

**Do not advance to Step 10 until `keywords.json` exists and keywords_count > 0.**

### Step 10: Confirm Phase 2 complete and stop

Tell the operator:

> "Phase 2 complete. Signal collection summary:
> - Serper: {organic_count} organic, {paa_count} PAA, {related_count} related, {ads_count} ads
> - Tavily: {urls_succeeded} pages extracted across {competitor_count} competitor domains
> - WebSearch: {len(extracted_keywords)} keyword phrases extracted
> - Merged: {keywords_count} canonical keywords ({variants_merged} variants collapsed), avg source diversity {source_diversity_avg:.1f}
>
> Run folder: `{run_dir}`
> Keyword file: `{run_dir}/keywords.json`
>
> Phase 3 (ranking and scoring) is not yet available in this skill."

Phase 3 (ranking and scoring) begins at Step 11 below.

---

## Phase 3: Ranking and Scoring

> Prerequisites: Phase 2 complete — `{run_dir}/keywords.json` exists and `keywords_count > 0`.

### Step 11: Intent labeling (RANK-01)

Read `{run_dir}/keywords.json`. Process keywords in batches of ≤ 30.

**Temperature: 0. Use the categorical rubric — do NOT score 0-1 or use any scale.**

For EVERY batch, include these calibration anchors at the top of your prompt:

> Anchor examples (do not change these labels):
> - "order grocery delivery" → transactional
> - "best grocery delivery uk" → commercial
> - "how does grocery delivery work" → informational
> - "ocado website" → navigational

For each keyword, assign:
- `intent`: EXACTLY one of: `informational` | `commercial` | `transactional` | `navigational`
- `match_type`: EXACTLY one of: `phrase` | `exact` | `broad`

**4-Class Intent Rubric:**

| Class | Definition | Anchor Examples | Borderline Guidance |
|-------|-----------|-----------------|---------------------|
| **transactional** | Intent to complete an action NOW: buy, order, subscribe, book, sign up, get a quote. Contains: buy / order / cheap / price / cost / near me / delivery + brand / [brand] vs [competitor]. | "order grocery delivery", "cheap same-day delivery uk", "grocery delivery near me", "get groceries delivered today" | "grocery delivery service" without action modifier → commercial. "Same-day delivery" alone without action word → commercial (intent is uncertain). |
| **commercial** | Active product research or comparison before purchase: best, top, review, vs, compare, alternative to, worth it, [brand] pricing, is X good. User is evaluating options. | "best grocery delivery uk", "ocado vs tesco delivery", "grocery delivery comparison", "is same-day delivery worth it", "grocery delivery review" | "best grocery delivery" → commercial (not transactional; no buy signal). "Grocery delivery app" → commercial unless "download" present. Comparison and review terms always commercial, not informational. |
| **informational** | Desire to learn or understand a topic without immediate purchase intent. Contains: how, what, why, does, can, which, guide, tips, history, meaning, definition. | "how does grocery delivery work", "what is same-day delivery", "grocery delivery tips for beginners", "why is grocery delivery expensive" | "how to order groceries online" — action in the how-to → transactional. "What is the best grocery delivery" → commercial (comparison framing). When unsure between informational and commercial, prefer commercial if any evaluation language is present. |
| **navigational** | Targets a specific brand, website, or destination. Contains: brand name alone, brand + login / website / app / account. User knows where they want to go. | "mcgrocer login", "ocado website", "tesco groceries app", "sainsburys food delivery", "[brand] sign in" | Brand + generic modifier (e.g., "tesco grocery delivery") — use transactional if action word present, commercial if comparison framing, navigational only if the keyword is purely brand + destination (login, website, app). |

**Match-type rules:**
- `exact`: navigational with `source_diversity ≥ 3`, OR transactional with `source_diversity ≥ 3`
- `phrase`: all other cases (default)
- `broad`: do not assign in v1

After all batches, write `{run_dir}/intent-labels.json` via the Write tool:

```json
[
  {"canonical": "<keyword>", "lemma_hash": "<hash>", "intent": "<class>", "match_type": "<type>"},
  ...
]
```

**Len-check gate:** Verify `len(intent-labels.json) == len(keywords.json)` (match on `lemma_hash`) before advancing. If short, re-run the missing batch only — do NOT re-run all batches.

Then write `{run_dir}/intent-meta.json` via the Write tool:

```json
{"model": "<model name>", "rubric_version": "v1.0", "batches": N, "keywords_labeled": N, "scored_at": "<ISO timestamp>"}
```

**Do not advance to Step 12 until `intent-labels.json` exists and every keyword in `keywords.json` has a matching entry.**

### Step 12: Run rank_keywords.py (RANK-02, RANK-03, RANK-04)

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/rank_keywords.py" --run-dir "{run_dir}"
```

Parse stdout JSON. Surface `ranked_count`, `avg_score`, `intent_distribution` to operator.

Exit code handling:
- **Exit 0:** continue to Step 13.
- **Exit 3:** surface the error message from stderr; do NOT proceed; tell the operator which file is missing or which keyword has no label.

**Do not advance to Step 13 until `{run_dir}/ranked.json` exists.**

### Step 13: Confirm Phase 3 complete and stop

Tell the operator:

> "Phase 3 complete. Ranking summary:
> - {ranked_count} keywords ranked
> - Avg score: {avg_score:.1f}
> - Intent distribution: {intent_distribution}
>
> Ranked keyword file: `{run_dir}/ranked.json`
>
> Phase 4 (clustering) is not yet available in this skill."

**STOP. Do not proceed to any Phase 4+ activity.**
