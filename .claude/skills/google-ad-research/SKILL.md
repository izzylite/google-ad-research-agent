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

**STOP. Do not advance to any signal collection, do not call Serper or Tavily, do not invoke WebSearch. Phase 1 ends here.**

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
