---
description: Run Google Ads keyword research from a campaign brief — produces ranked keyword tables, ad group clusters, competitor ad copy, and tiered negative keyword lists. Use when the operator says "keyword research", "Google Ads research", "PPC keywords", "ad group clusters", or pastes a campaign brief mentioning industry / product / location / language / audience.
allowed-tools: Bash(uv run *) Read Write WebSearch WebFetch
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
| **exclusions** | The Product field uses "NOT X" / "excluding X" / "not including X" language OR the Audience implies a specialty exclusion (adult-only vs pediatric, human vs veterinary, MVA vs workers-comp). Comma-separated list of tokens/phrases to drop from research output ENTIRELY (positives and negatives generation alike). Drives `merge_signals.py` substring filter (EXCL-01). Examples: `pediatric, veterinary, dental, mental health, chiropractor, physical therapy, pain management, orthopedic`. See **Step 3b** below — auto-derive from Product / Audience before sealing. |
| **geo_focus** | The location is at state/region level and operator hints at sub-area focus (county or city). Comma-separated list — e.g., "Palm Beach County, Lake Worth". Drives `serp_fetch.py --geo-focus` + `merge_signals.py` city filter (GEO-01..03). **Ambiguity guard:** if the operator's list mixes a county-level token (contains "County", "Parish", "Borough", "Province") AND a city-level token, see **Step 3a** below — you must resolve scope before advancing. |
| **campaign_focus** | The brief targets ONE specific existing Google Ads campaign in the operator's account (rather than account-wide research). Single name OR pipe-separated list (no spaces around pipes for list form). Example: `Search \| Lake Worth Accident Exams \| Manual CPC` (single, spaced pipes = one name) or `Campaign A\|Campaign B` (list). Drives `perf_fetch.py --campaign-filter` — narrows all 4 GAQL queries to the named campaign(s); Positives Sync / Negatives Sync / Ad Group Mapping inherit the narrowed raw data automatically. Omit when researching account-wide (CAMP-04 graceful degrade). |

When you ask, ask ONE field per turn. After the operator answers, re-evaluate whether other triggers now fire. Skip silently when no trigger fires.

**Do not advance to Step 3a / Step 4 if you opened an optional follow-up loop without resolving it.**

### Step 3a: Disambiguate geo_focus scope (GEO-06)

This runs only when **all four** are true:
1. The operator provided a `geo_focus` value in Step 3.
2. The value contains at least one **county-level token** — case-insensitive substring match against `"County"`, `"Parish"`, `"Borough"`, `"Province"` (e.g., `"Palm Beach County"`, `"Orleans Parish"`, `"Staten Island Borough"`).
3. The value ALSO contains at least one **city-level token** — any token without those keywords (e.g., `"Lake Worth"`, `"West Palm Beach"`).
4. The two tokens are not the same area (`"Brooklyn Borough"` + `"Brooklyn"` is one place — skip the prompt).

When triggered, ask the operator EXACTLY this question once, then wait for the answer:

> "Your geographic focus contains both a **county-level** token (`{county_token}`) and a **city-level** token (`{city_token}`). Which scope do you want?
>
> **(a) City-only.** Research only `{city_token}`-area SERPs. Drops other cities within `{county_token}`. Use this when the active campaign is radius-targeted to `{city_token}` and the county appears in the brief only as broader context.
>
> **(b) County-wide.** Research all cities within `{county_token}` including `{city_token}`. Use this when the campaign actually targets multiple cities in the county OR when you're prepping research for future campaign expansion into other county cities.
>
> Reply `a` or `b`."

Treat any answer other than `a` or `b` as a re-prompt (do not infer). Once the operator picks:

- **If `a` (city-only):** rewrite the brief's `geo_focus` to contain ONLY the city token(s); drop the county token entirely. Append a comment line beneath the field for audit: `<!-- GEO-06: disambiguated to city-only on {ISO timestamp} -->`.
- **If `b` (county-wide):** keep the brief's `geo_focus` as-is. Append: `<!-- GEO-06: disambiguated to county-wide on {ISO timestamp} -->`.

**Why this matters.** Without the guard, "Palm Beach County, Lake Worth" silently expands into research covering WPB, Palm Beach Gardens, Wellington, Delray, Royal Palm Beach — surprising the operator when the active campaign is Lake Worth-radius-only. The 2026-05-15 dogfood run for Primary Urgent Care Centers shipped 6 out-of-scope clusters because this guard didn't exist; recovery required a full re-run.

**Do not advance to Step 4 until the disambiguation question is resolved.**

### Step 3b: Auto-derive Exclusions from Product + Audience (EXCL-01)

This runs when **either** is true:
1. The brief's `Product:` field contains "NOT X" / "excluding X" / "not including X" patterns (e.g., `urgent care + PIP exams (NOT chiropractor, NOT physical therapy, NOT pain management, NOT orthopedics)`).
2. The brief's `Audience:` field implies a specialty exclusion: any of `adult`, `victim(s)`, `patient(s)`, `worker(s)`, `veteran(s)` → pediatric is implicitly out-of-audience; `human` mentioned or implied → veterinary is out-of-audience; medical/healthcare vertical → dental + mental health are out-of-audience unless Product explicitly includes them.

When triggered, **derive an Exclusions list** by combining:
- Every "NOT X" item from Product (split on commas, strip "NOT" / "excluding" / "not including" prefixes)
- Default audience exclusions inferred from Audience semantics (e.g., adult MVA brief → add `pediatric`)
- Default category exclusions inferred from medical vertical (when off-product) → `veterinary`, `dental`, `mental health`, `psychiatric`, `geriatric`

**EXCL-03: Morphological-form expansion.** Substring matching catches stem variants only when the stem matches. `dental` does NOT catch `dentist`. So every derived exclusion gets expanded into its noun + adjective + practitioner-noun + plural forms before being written to the brief. Use this expansion map for the medical vertical (other verticals use their own — extend the dictionary in `references/morphological-forms.json` when you hit a new vertical):

| Exclusion you derive | Auto-expand to |
|---|---|
| `dental` | `dental, dentist, dentists, dentistry` |
| `psychiatric` | `psychiatric, psychiatrist, psychiatrists, psychiatry` |
| `geriatric` | `geriatric, geriatrician, geriatricians, geriatrics, elderly care` |
| `pediatric` | `pediatric, pediatrician, pediatricians, pediatrics, peds, kids urgent care` |
| `chiropract` | `chiropractor, chiropractors, chiropractic` (use stem `chiropract` — substring covers all) |
| `orthopedic` | `orthopedic, orthopaedic, orthopedist, orthopedists, orthopaedics, ortho ` (trailing space to avoid matching "north") |
| `physical therapy` | `physical therapy, physical therapist, physical therapists, physiotherapy, physiotherapist, pt clinic` |
| `pain management` | `pain management, pain clinic, pain doctor, pain specialist` |
| `veterinary` | `veterinary, veterinarian, vet clinic, pet care` |
| `mental health` | `mental health, mental healthcare, behavioral health, behavioral healthcare` |

Rule of thumb: if a specialty has a `-ic`/`-ical` adjective AND a `-ist`/`-ian` practitioner noun, both forms (plus plural) go in. For practitioner brands that may share generic words (`ortho` collides with `north`, `orthorexia`), add a trailing space or use the longer adjective form (`orthopedic ` not `ortho`).

Then ask the operator to confirm or edit the list, ONCE:

> "I'm going to drop any keyword containing these phrases from the research pool entirely (positives AND negatives). The exclusions will also be auto-included as Strong wrong-audience / wrong-product negatives so they're blocked at the campaign level too.
>
> Derived from your Product + Audience: `{exclusions_list}`
>
> Reply with one of:
> - `ok` — use this list as-is
> - `edit: <new comma-separated list>` — replace with your own
> - `add: <phrases>` / `remove: <phrases>` — incremental tweaks
> - `skip` — disable the filter (use only when the LLM's prose-reading of Product is sufficient; not recommended for tight-budget single-campaign briefs)"

Apply the operator's reply, then write the final list to the brief's `**Exclusions:**` field.

**Rules:**
- Phrase length minimum: 3 characters per phrase (sub-3 phrases over-match generic words; filter strips them automatically).
- Substring match is case-insensitive. `chiropract` catches `chiropractor`, `chiropractic`, `chiropractors` — operator can use either the stem or the full word; the stem is safer.
- The list is **additive** to negatives generation (Step 21 must auto-include each phrase as a Strong negative in `wrong-audience` or `used-refurb-wholesale` category as appropriate).
- Skipping the filter (operator replies `skip`) is logged in the rendered brief as `<!-- EXCL-01: filter disabled by operator on {ISO timestamp} -->` for audit.

**Why this matters.** The 2026-05-15 + 2026-05-16 dogfood runs both leaked off-service-line keywords (chiropractor, physical therapy, pain management) and off-audience keywords (pediatric) into positives despite Product/Audience prose explicitly excluding them. The LLM clustering / negative-gen pass reads Product as guidance, not as a contract — a deterministic substring drop at `merge_signals.py` is the contract. Operators were having to scrub `positives.csv` by hand before every Editor import.

**EXCL-04: Acronym-collision auto-detection.** Read `references/acronym-collisions.json` and scan the brief's Industry / Product / Audience fields for any acronym (uppercase or lowercase) that matches a key in the dictionary. For each match:

1. Check the operator's `Budget:` field. If `confidence: high`, always surface. If `confidence: medium`, surface when Budget is unset OR < $300/day. If `confidence: low`, surface only when Budget < $150/day.
2. Show the operator the intended meaning (from the dictionary) AND the collision list, then ask:

   > "Brief mentions `{acronym}`. In your domain that almost certainly means `{intended_meaning}`. Google also indexes `{acronym}` as several other meanings that can pollute search queries on this budget tier. Add the collision phrases to Exclusions?
   >
   > Suggested additions: `{collisions_list}`
   >
   > Reply `ok` / `edit: <list>` / `add: <subset>` / `skip`."

3. Apply the operator's reply — append confirmed collisions to the Exclusions list before sealing the brief. Each becomes a Strong wrong-audience or used-refurb-wholesale negative via EXCL-02.

**Operator-edits-only-the-dictionary contract.** The collision dictionary at `references/acronym-collisions.json` is operator-editable data. When you discover a new acronym collision during dogfood (e.g., a new vertical's "XYZ" gets polluted by "X Y Z" indexing), add an entry to the JSON file — no code change, no SKILL.md change. The skill picks it up on the next run.

**Why EXCL-04 matters.** 2026-05-16 Primary Urgent Care dogfood: operator manually added 10 acronym-collision negatives (`personal independence payment`, `disability benefit`, `universal credit`, `electromagnetic compatibility`, `emc testing`, `emc engineer`, `irs`, `rental`, `tax`, `real estate`) post-launch because PIP and EMC indexes are wider than the brief's intended meaning. Surfacing these at brief intake means the operator confirms once instead of discovering them in search-term reports after spend.

**Do not advance to Step 4 until Exclusions is set (or operator explicitly chose `skip`) AND any matched acronym collisions have been resolved.**

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
- **Exclusions:** {exclusions}
- **Geo focus:** {geo_focus}
- **Campaign focus:** {campaign_focus}

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
- **Never write API keys to the run folder.** This skill currently makes zero API calls; Phase 2+ uses `lib/config.load_env()` only. If you ever see `SERPER_API_KEY` written to disk, STOP and surface it.
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

> Prerequisites: Phase 1 complete — `run_dir` and `brief.md` exist. `SERPER_API_KEY` set in `.env`.

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

### Step 8: Run Serper fetch

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

When brief has `**Geo focus:**`, append `--geo-focus "{token_1}" "{token_2}"` (one quoted arg per token); `serp_fetch.py` appends tokens to each seed query once, case-insensitively skipping already-present tokens (GEO-02; see `references/phase11-account-structure-mapping.md`).

Parse stdout JSON. Surface `organic_count`, `paa_count`, `related_count`, `ads_count`, `credits_used` to operator.

If exit code 2 (retryable): tell operator "Serper returned a transient error — retry? (y/n)". Re-run once if yes. If exit code 3: stop and surface the error; do not proceed.

Landing-page extraction for paid competitors is deferred to Phase 5 (Step 19), where Claude calls WebFetch directly on the advertiser URLs surfaced by `competitor_intel.py`. No separate Phase 2 extraction step.

**Do not advance to Step 9 until `serp_fetch.py` has exited 0 (or 2 with partial data accepted).**

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

Phase 4 (clustering) begins at Step 14 below.

---

## Phase 4: Clustering

> Prerequisites: Phase 3 complete — `{run_dir}/ranked.json` exists.

### Step 14: Partition keywords by intent

Read `{run_dir}/ranked.json`. Partition all keywords into four lists by their `intent` field.

Print a count summary to confirm the split:
> "Intent partition: transactional=N, commercial=N, informational=N, navigational=N"

Store each partition in memory. **Do not proceed to Step 15 until you have printed this summary and all keywords from ranked.json are accounted for (sum of partition counts == total rows in ranked.json).**

### Step 15: Cluster semantically within each partition

For each intent class that has ≥ 1 keyword, perform semantic clustering:

1. Display the keyword list for that intent class (keyword + score, sorted by score descending).
2. Group the keywords into thematic clusters following these rules:
   - **Target size:** 5-15 keywords per cluster. Minimum 3.
   - If a class has < 3 keywords total: create a single `misc_{intent}` cluster containing all of them.
   - **Do NOT split keywords across intent classes.** Every cluster contains keywords of exactly one intent.
   - **Naming:** Each cluster name must be `{theme_slug}_{intent}` — derive the theme slug from the 2-3 most-frequent meaningful words in the group's keywords. Use lowercase snake_case only. No hyphens. No numbers in the slug. No generic prefixes (cluster, theme, topic, group).
     - Valid: `same_day_delivery_transactional`, `grocery_brand_comparison_commercial`
     - Invalid: `cluster_1_transactional`, `Grocery_Transactional`, `grocery_transactional` (single-word theme)
   - **Do NOT re-assign intent.** Do NOT create clusters that span more than one intent class.
   - **Fold fragments:** If after grouping any cluster would have < 3 keywords, merge it into the nearest thematic neighbor within the same intent class.

3. When all intent classes are clustered, write `{run_dir}/clusters.json` using the Write tool:

```json
{
  "metadata": {
    "clustered_at": "<ISO timestamp>",
    "method": "llm-driven",
    "model": "<your model name>",
    "ranked_input": "ranked.json",
    "total_keywords": <N>,
    "total_clusters": <N>
  },
  "clusters": [
    {
      "name": "<theme_slug>_<intent>",
      "intent": "<intent class>",
      "keywords": [
        {"keyword": "<keyword string>", "score": <score integer>}
      ]
    }
  ],
  "orphans": []
}
```

Every keyword from ranked.json must appear in exactly one cluster or in `orphans`. Do not include any ranked.json fields beyond `keyword` and `score` in the clusters array.

**Do not advance to Step 16 until `{run_dir}/clusters.json` exists.**

### Step 16: Validate and fix loop

Run the validator:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/validate_clusters.py" --run-dir "{run_dir}"
```

Parse the stdout JSON and the exit code:

**Exit 0 — valid:** Continue to Step 17.

**Exit 1 — warnings only:** Surface the warnings to the operator:
> "Clustering complete with warnings: {violations list}. Proceed anyway or fix? (proceed/fix)"
If operator says fix: treat as exit 3 for the warned clusters and re-prompt. If proceed: continue to Step 17.

**Exit 3 — hard violations:** Read the `violations` list from stdout. For each violation, identify the offending cluster by name. Re-prompt for ONLY those clusters:
> "Validator found violations in clusters: {names}. Violation details: {violations}. Re-clustering only those groups now."

Re-cluster the offending clusters (keeping all other clusters unchanged), rewrite only those entries in `{run_dir}/clusters.json` (preserve the rest), then re-run the validator.

Maximum 2 fix iterations. If violations persist after 2 iterations:
> "Clustering could not satisfy all invariants after 2 fix attempts. Remaining violations: {violations}. Stopping — operator review required."
Do NOT proceed to Step 17.

**Exit 2 — infrastructure error:** Surface the error to the operator. Do not retry silently.

**Do not advance to Step 17 until validator exits 0 (or operator accepts exit 1 warnings).**

### Step 17: Confirm Phase 4 complete and stop

Tell the operator:

> "Phase 4 complete. Clustering summary:
> - {total_clusters} clusters created across {intent_count} intent classes
> - {total_keywords} keywords assigned
> - Orphans: {orphan_count}
> - Validator: {valid status}
>
> Clusters file: `{run_dir}/clusters.json`"

Phase 5 (competitor intel) begins at Step 18 below.

## Phase 5: Competitor Ad Copy and Landing Page Extraction

> See `.claude/skills/google-ad-research/references/phase5-competitor-intel.md` for full step instructions (Steps 18-20). Load it with the Read tool when entering Phase 5.

## Phase 6: Negatives, Report Assembly, and Persistence

> See `.claude/skills/google-ad-research/references/phase6-negatives-report.md` for full step instructions (Steps 21-26). Load it with the Read tool when entering Phase 6.

## Phase 8: Account Data + Volume Enrichment (auto-run when creds present)

> See `.claude/skills/google-ad-research/references/phase8-account-data.md` for full step instructions (Steps 31-35 + Step 34a LLM re-tag for POS-06 positives sync). Load it with the Read tool when entering Phase 8. **Auto-run when `AHREFS_API_KEY` AND Google Ads OAuth creds are present in `.env`** — do NOT prompt the operator. Enriches the keyword table with Ahrefs volume / CPC / KD / parent_topic, pulls real search terms and campaign performance from the Google Ads account, and cross-references generated negatives against existing account negatives. Costs ~73 Ahrefs units + free Google Ads quota per run. Produces `ranked-enriched.json`, `account-perf.json`, `negatives-sync.json` alongside existing artifacts.
>
> **Skip-and-announce conditions (and only these):**
> - `AHREFS_API_KEY` missing → announce `Phase 8 skipped: AHREFS_API_KEY not set. Add to .env to enable real volume/CPC/KD enrichment. Continuing to Phase 9 is impossible without it.`
> - Google Ads OAuth creds missing (`GOOGLE_ADS_DEVELOPER_TOKEN` / `GOOGLE_ADS_CLIENT_ID` / `GOOGLE_ADS_CLIENT_SECRET` / `GOOGLE_ADS_REFRESH_TOKEN` / `GOOGLE_ADS_LOGIN_CUSTOMER_ID`) → announce `Phase 8 skipped: Google Ads OAuth creds incomplete. Skill is internal-team tool — these are required for the launch kit and account mapping. Configure .env and rerun.`
> - Operator explicitly says "skip Phase 8" (rare; honor it but warn that Phase 9, 10, 11 chain breaks).

---

## Phase 9: Campaign Economics and Compliance (auto-run when Phase 8 ran)

> See `.claude/skills/google-ad-research/references/phase9-economics-compliance.md` for full step instructions (Steps 36-40). Load it with the Read tool when entering Phase 9. **Auto-run when Phase 8 produced `ranked-enriched.json` with `cpc_micros`** — do NOT prompt. Adds Suggested Max CPC per keyword, per-cluster + campaign-level budget forecast bands, and a regulated-vertical compliance scan. Pure-compute phase — no API costs. Produces an additive mutation of `ranked-enriched.json` plus two new sidecars (`forecast.json`, `compliance-flags.json`).
>
> **Skip only if** Phase 8 was skipped or `cpc_micros` is absent from every row — announce `Phase 9 skipped: no Phase 8 CPC data to derive bid suggestions.`

## Phase 10: Operator Launch Kit (auto-run when Phase 9 ran)

> See `.claude/skills/google-ad-research/references/phase10-operator-launch-kit.md` for full step instructions (Steps 41-43). **Auto-run when Phase 9 completed** — do NOT prompt. Turns report into ready-to-import campaign. Emits 3 Editor v2.x CSVs (`positives.csv`, `negatives.csv`, `ad_groups.csv`) under `{run_dir}/export/` + appends bespoke Next Steps checklist. Pure compute, no API costs. Extends `report.md`/`report.json`/`report.html`.
>
> **Skip only if** Phase 9 was skipped — announce `Phase 10 skipped: no Phase 9 economics to populate Editor CSVs.`

## Phase 11: Account-Structure Mapping (auto-run when brief has geo_focus OR Phase 8 ran)

> See `.claude/skills/google-ad-research/references/phase11-account-structure-mapping.md` for full step instructions (Steps 44-47). Load it with the Read tool when entering Phase 11. **Auto-run when EITHER the brief has a `Geo focus:` field OR Phase 8 produced `raw/google-ads-perf.json` + `raw/google-ads-search-terms.json`** — do NOT prompt. Refines research to specific counties/cities (GEO-01..05) and maps ranked keywords to the client's existing ad groups (ADGM-01..06). Pure compute, no API costs. Produces `{run_dir}/ad-group-mapping.json` + rewrites `report.md` Next Steps step 3 when coverage > 50% + filters `export/ad_groups.csv` to skip existing names.
>
> **Skip only if** brief has no `Geo focus:` field AND Phase 8 did not produce account data. Internal-team skill: every brief targets a specific FL geography + pastes into an existing Ads account — geo-filtering + existing-ad-group preservation are primary value, not polish.
