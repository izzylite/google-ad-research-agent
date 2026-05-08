# Phase 3: Ranking and Scoring — Research

**Researched:** 2026-05-08
**Domain:** LLM-driven 4-class intent classification + deterministic composite scoring + match-type recommendation, producing `ranked.json` with canonical 8-column schema.
**Confidence:** HIGH (architecture, schema, rubric design, scoring math — all derived from locked project decisions); MEDIUM (intent weight tuning — acknowledged v1 hypothesis awaiting real-run calibration)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RANK-01 | LLM classifies each keyword by 4-class intent (informational / commercial / transactional / navigational) using categorical rubric with anchor examples, temperature=0 | § Intent Classification Architecture; § Categorical Rubric; § Code Examples — Intent prompt structure |
| RANK-02 | Composite ranking uses `signal_count` + `source_diversity` + intent weight; primary ranking signal is `source_diversity` | § Composite Scoring Formula; § Don't Hand-Roll |
| RANK-03 | Match-type recommendation (broad / phrase / exact) per keyword with conservative defaults | § Match-Type Heuristic |
| RANK-04 | Ranked keyword table columns: `keyword`, `intent`, `match_type`, `theme`, `signal_count`, `source_diversity`, `sources`, `score`; `signal_count` never labelled "volume" | § Canonical Output Schema; § Pitfall 2 Mitigation |
</phase_requirements>

---

## Summary

Phase 3 transforms the flat `keywords.json` produced by Phase 2 into `ranked.json` — a scored, intent-labeled, match-type-annotated keyword table ready for Phase 4 clustering. The work splits cleanly into two concerns: (1) **LLM judgment** — intent labeling, done by Claude in the skill prompt using a categorical rubric with anchor examples at temperature=0; (2) **deterministic math** — composite scoring and match-type assignment, done by a Python helper `rank_keywords.py` that takes labeled keywords and writes `ranked.json`. No separate LLM API call is made from Python; Claude reads `keywords.json`, applies the rubric, and writes an intermediate `intent-labels.json`, then the script does the math.

The central risk for this phase is Pitfall 3 (LLM intent scoring drift between runs). The mitigation is not a clever algorithm — it is discipline: categorical labels (not scalars), a rubric with explicit class definitions and anchor examples baked into the skill prompt, temperature=0, and metadata logging (model name + prompt version) written to the run folder each time scoring runs. The rubric must be authored once and locked; changing it is a breaking change because Phase 4 reads intent as a hard clustering split.

The secondary risk is Pitfall 2 (frequency misread as volume). The schema locks the column name as `signal_count` unconditionally and the "How to read this" explanatory snippet is authored here and referenced by Phase 6 report assembly.

**Primary recommendation:** Skill prompt does intent labeling (Claude reads `keywords.json`, labels each row, writes `intent-labels.json`). `rank_keywords.py` does only deterministic scoring math, consuming `intent-labels.json` + `keywords.json` to write `ranked.json`. Theme field is set to `""` (empty string) — Phase 4 fills it.

---

## Standard Stack

### Core (Phase 3 net-new)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib `json`, `pathlib`, `argparse` | — | `rank_keywords.py` I/O, CLI, file writes | No new deps needed; scoring math is arithmetic. [HIGH] |
| `tabulate` | 0.9.0 | Optional: spot-check table rendering during dev | Already present; `tablefmt="github"` for markdown preview. Not used in `rank_keywords.py` output (output is JSON). [HIGH] |
| `pytest` | 8.x | Unit tests for `rank_keywords.py` scoring math | Inherited test infrastructure; conftest at `scripts/tests/conftest.py`. [HIGH] |

### NOT Needed for Phase 3

| Library | Why Rejected |
|---------|--------------|
| Any LLM API client (anthropic SDK, openai, etc.) | Intent classification is done by Claude in the skill prompt, not from Python. No separate API call. |
| `pydantic` | Output rows have 8 fixed fields; dict-with-type-annotations + tests are sufficient. Add in Phase 6 if cross-script contracts grow. |
| `scikit-learn` | Clustering is Phase 4; this is scoring math only. |
| Any NLP library | Lemmatisation was Phase 2 (`lib/canon.py`). Phase 3 consumes already-canonical keywords. |

**Installation:** no new packages. `rank_keywords.py` uses stdlib only.

---

## Architecture Patterns

### Recommended Project Structure (Phase 3 additions)

```
.claude/skills/google-ad-research/scripts/
├── rank_keywords.py          # NEW: deterministic scoring math — keywords.json + intent-labels.json → ranked.json
├── merge_signals.py          # Phase 2 (existing)
├── lib/
│   └── (existing: canon.py, config.py, http.py, io.py, log.py)
└── tests/
    └── test_rank_keywords.py # NEW: unit tests for scoring math

.runs/<ts>-<slug>/
├── keywords.json             # Phase 2 output (input to Phase 3)
├── intent-labels.json        # NEW: Claude's intent+match_type labels (written by skill prompt)
└── ranked.json               # NEW: final scored output (written by rank_keywords.py)

.claude/skills/google-ad-research/
└── SKILL.md                  # Updated: Steps 11-13 (intent labeling + scoring + stop)
```

### Pattern 1: Skill Prompt Does Intent Labeling (RANK-01)

**What:** Claude reads `keywords.json` from `run_dir`, applies the categorical rubric (embedded in SKILL.md), and writes `intent-labels.json` to the run folder via the Write tool.

**When to use:** Always in v1. Claude is already in-context with the brief and the rubric; no separate API call needed; temperature=0 is set for the step.

**Why not a Python script:** The intent labeling step requires LLM judgment — that is Claude's job. A Python script calling an LLM API would duplicate Claude Code's existing in-session context, add API cost, and introduce a separate auth requirement.

**SKILL.md Step 11 structure:**
```markdown
### Step 11: Intent labeling

Read `{run_dir}/keywords.json`. For each keyword row, assign:
- `intent`: one of ["informational", "commercial", "transactional", "navigational"]
  using the rubric below.
- `match_type`: one of ["phrase", "exact", "broad"]
  using the match-type heuristic below.

Temperature: 0. Use the categorical rubric — do NOT score 0-1 or use any scale.
Include anchor examples in every batch prompt (see § Categorical Rubric).

Write results to `{run_dir}/intent-labels.json` using the Write tool:
[
  {"canonical": "<keyword>", "lemma_hash": "<hash>", "intent": "<class>", "match_type": "<type>"},
  ...
]

Do not advance to Step 12 until `intent-labels.json` exists and every keyword
in keywords.json has a matching entry (match on lemma_hash).
```

### Pattern 2: rank_keywords.py Does Deterministic Math (RANK-02, RANK-03, RANK-04)

**What:** Pure Python. Reads `keywords.json` + `intent-labels.json`, joins on `lemma_hash`, computes `score`, writes `ranked.json` sorted descending by score.

**When to use:** After Step 11 (intent labels exist). Invoked from SKILL.md Step 12.

**CLI contract (inherits Phase 1/2 conventions):**
```
stdin:  none
stdout: single JSON line — {"ranked_count": N, "avg_score": float, "intent_distribution": {...}}
stderr: progress logs
exit:   0 ok / 3 fatal (missing input file / join failure)
```

**Script invocation from SKILL.md:**
```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/rank_keywords.py" --run-dir "{run_dir}"
```

### Anti-Patterns to Avoid

- **Scalar 0-1 intent scores:** Pitfall 3. Categorical only. "transactional" not "0.87".
- **Calling an LLM API from rank_keywords.py:** Scoring math is deterministic; LLM call is Claude's job in the skill prompt.
- **Setting theme in Phase 3:** `theme` is Phase 4's output. Phase 3 writes `""`. Phase 4 overwrites it.
- **Labelling the column "volume" anywhere:** Always `signal_count`. No exceptions.
- **Batching all keywords in one unbounded prompt:** Batch in groups of 25-50 with rubric anchors in every batch. Context window discipline.

---

## Categorical Rubric (for SKILL.md and RANK-01)

This rubric is locked. Changing it is a breaking change — Phase 4 treats intent as a hard split.

### 4-Class Intent Rubric

| Class | Definition | Anchor Examples (affirm) | Borderline Guidance |
|-------|-----------|--------------------------|---------------------|
| **transactional** | Keyword signals intent to complete an action NOW: buy, order, subscribe, book, sign up, get a quote. Contains: buy / order / cheap / price / cost / near me / delivery + brand/product / [brand] vs [competitor]. | "order grocery delivery", "cheap same-day delivery uk", "grocery delivery near me", "get groceries delivered today" | "grocery delivery service" without action modifier → commercial. "Same-day delivery" alone without action word → commercial (intent is uncertain). |
| **commercial** | Keyword signals active product research or comparison before purchase: best, top, review, vs, compare, alternative to, worth it, [brand] pricing, is X good. User is evaluating options. | "best grocery delivery uk", "ocado vs tesco delivery", "grocery delivery comparison", "is same-day delivery worth it", "grocery delivery review" | "best grocery delivery" → commercial (not transactional; no buy signal). "Grocery delivery app" → commercial unless "download" present. Comparison and review terms always commercial, not informational. |
| **informational** | Keyword signals desire to learn, understand, or research a topic without immediate purchase intent. Contains: how, what, why, does, can, which, guide, tips, history, meaning, definition. | "how does grocery delivery work", "what is same-day delivery", "grocery delivery tips for beginners", "why is grocery delivery expensive", "how to save money on grocery delivery" | "how to order groceries online" — action in the how-to → transactional (the goal is completing an order). "What is the best grocery delivery" → commercial (comparison framing). When unsure between informational and commercial, prefer commercial if there is any evaluation language. |
| **navigational** | Keyword targets a specific brand, website, or destination. Contains: brand name alone, brand + login / website / app / account. User knows where they want to go. | "mcgrocer login", "ocado website", "tesco groceries app", "sainsburys food delivery", "[brand] sign in" | Brand + generic modifier (e.g., "tesco grocery delivery") — use transactional if action word present, commercial if comparison framing, navigational only if the keyword is purely brand + destination (login, website, app). |

### Batching Instructions (for SKILL.md Step 11)

Process keywords in batches of ≤ 30. Include in EVERY batch prompt:

> "These are anchor examples. Use them as calibration — do not change their labels:
> - 'order grocery delivery' → transactional
> - 'best grocery delivery uk' → commercial
> - 'how does grocery delivery work' → informational
> - 'ocado website' → navigational"

This ensures consistent calibration across batches even if the keyword set spans multiple prompt invocations.

---

## Composite Scoring Formula (RANK-02)

### Formula

```
score = (source_diversity * 100) + intent_weight + signal_count
```

Where `intent_weight`:

| Intent class | Weight |
|-------------|--------|
| transactional | 30 |
| commercial | 20 |
| navigational | 10 |
| informational | 5 |

### Sort Order

Primary: `score` descending.
Tie-break 1: `signal_count` descending.
Tie-break 2: `canonical` ascending (alphabetical, for deterministic output).

### Rationale

- `source_diversity * 100` makes source diversity the dominant signal. A keyword echoed by 4 distinct sources (score contribution 400) always outranks a single-source keyword (100) regardless of signal_count or intent. This directly satisfies RANK-02 ("primary ranking signal is source_diversity").
- `intent_weight` (5-30) gives a secondary preference for purchase-intent keywords within the same diversity tier — useful for PPC budget allocation.
- `signal_count` (unbounded integer, typically 1-20) breaks ties within same diversity + same intent class.
- Alphabetical final tie-break produces deterministic output across runs for identical inputs.

### Score Range Examples

| Keyword | source_diversity | intent | signal_count | score |
|---------|-----------------|--------|-------------|-------|
| order groceries uk | 4 | transactional | 5 | 435 |
| grocery delivery service | 4 | commercial | 8 | 428 |
| best grocery delivery | 3 | commercial | 12 | 332 |
| how does grocery delivery work | 3 | informational | 3 | 308 |
| ocado login | 1 | navigational | 1 | 111 |

### Weight Tuning Note

Intent weights (30/20/10/5) are a v1 hypothesis. Calibrate after first 3-5 real runs by checking whether ranked order aligns with the operator's intuition about high-value keywords. The formula is in `rank_keywords.py` (deterministic Python) — adjusting weights is a one-line change, no LLM prompt update needed.

---

## Match-Type Heuristic (RANK-03)

### Decision Rules

```
if intent == "navigational" and source_diversity >= 3:
    match_type = "exact"
elif intent == "transactional" and source_diversity >= 3:
    match_type = "exact"
elif intent == "transactional" and source_diversity < 3:
    match_type = "phrase"
elif intent == "commercial":
    match_type = "phrase"
elif intent == "informational":
    match_type = "phrase"
elif intent == "navigational" and source_diversity < 3:
    match_type = "phrase"
```

Broad match is never assigned automatically. If the operator explicitly requests broad match for a keyword, they can override in Google Ads Editor post-export. v1 does not generate broad recommendations.

### Rationale

- **Exact for navigational + transactional with diversity ≥ 3:** These are high-confidence, high-intent keywords corroborated by multiple signal sources — exact match maximises spend efficiency and prevents budget bleed to unintended variants.
- **Phrase as default for everything else:** Phrase match captures close variants without the uncontrolled expansion of broad. Conservative default aligned with RANK-03 requirement.
- **Broad rare with justification:** Not generated in v1. A future v2 field in `brief.md` ("expand_to_broad: true") could override for discovery campaigns.

---

## Canonical Output Schema (RANK-04)

### ranked.json Row Shape

```json
{
  "keyword":          "order groceries uk",
  "intent":           "transactional",
  "match_type":       "exact",
  "theme":            "",
  "signal_count":     5,
  "source_diversity": 4,
  "sources":          ["serper-paa", "serper-related", "tavily-extract", "websearch-baseline"],
  "score":            435
}
```

### Field Definitions

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `keyword` | string | `keywords.json` → `canonical` | Never renamed; not "term", not "query". |
| `intent` | string | `intent-labels.json` | One of: informational / commercial / transactional / navigational. |
| `match_type` | string | `intent-labels.json` (set during Step 11) OR `rank_keywords.py` (deterministic fallback) | One of: phrase / exact / broad. |
| `theme` | string | `""` (empty) in Phase 3 | Phase 4 clustering fills this with `{theme}_{intent}` pattern. |
| `signal_count` | integer | `keywords.json` → `signal_count` | NEVER labelled "volume". Count of source-fragment occurrences. |
| `source_diversity` | integer | `keywords.json` → `source_diversity` | Count of distinct source strings. Max 6 (6-source taxonomy). |
| `sources` | array of strings | Derived from `keywords.json` → `sources[]` — distinct `source` values only | Compact form for ranked.json; full provenance stays in `keywords.json`. |
| `score` | integer | Computed by `rank_keywords.py` | `source_diversity * 100 + intent_weight + signal_count`. |

### intent-labels.json Shape (intermediate file)

```json
[
  {
    "canonical":   "order groceries uk",
    "lemma_hash":  "a3f2b1c4d5e6f7a8",
    "intent":      "transactional",
    "match_type":  "exact"
  }
]
```

This is the sole bridge between LLM judgment (skill prompt) and deterministic math (script). Join key is `lemma_hash`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Intent classification consistency | Custom scalar scoring, 0-1 confidence, probability outputs | Categorical rubric with anchor examples, temperature=0 | Scalars drift between runs (Pitfall 3). Categories are stable. Industry standard for classification reliability. |
| Composite ranking | Multi-factor sort with ad-hoc weights inline | Explicit formula: `source_diversity * 100 + intent_weight + signal_count` in a named function | Named formula is testable, diffable, tunable. Inline ad-hoc sorts can't be unit-tested or calibrated. |
| Match-type defaults | Operator-described "conservative" with no rules | Decision tree in `rank_keywords.py` with documented rules | Without explicit rules, match-type varies by whoever ran the skill last. Rules make it auditable. |
| "How to read this" text | Generate ad-hoc per report | Canonical snippet authored here, referenced in Phase 6 | Consistency across runs; no LLM paraphrase drift in explanatory copy. |

**Key insight:** The only non-deterministic step in Phase 3 is intent labeling by the LLM. Everything else — scoring, match-type, schema — must be deterministic Python so that the same `keywords.json` + `intent-labels.json` always produces identical `ranked.json`. This makes the phase testable.

---

## Common Pitfalls

### Pitfall 2 (Frequency misread as volume)

**What goes wrong:** Operator or downstream PPC manager reads `signal_count` as monthly search volume. They allocate budget expecting 7 searches/month and get 700 (or zero).

**Why it happens:** PPC industry trains people to expect a volume column. Any number in a keyword table gets interpreted as volume.

**How to avoid:**
- Column name: `signal_count` — always, everywhere. Never "volume", "frequency", "count", "score", "occurrences".
- The "How to read this" explanatory snippet (authored in Phase 3, rendered in Phase 6 report) must contain verbatim: *"signal_count is NOT search volume. It counts how many source-fragments (Serper results, PAA questions, Tavily excerpts, WebSearch snippets) surfaced this keyword during research. To estimate search volume, paste the keyword list into Google Keyword Planner."*
- `ranked.json` field name is `signal_count`. `keywords.json` field name is `signal_count`. Both locked from Phase 2.

**Warning signs:** Operator asks "is this per month?" — the labelling has failed.

### Pitfall 3 (LLM intent scoring drift between runs)

**What goes wrong:** Re-running the same brief on a different day produces different intent labels for the same keywords, causing ad groups to shift without explanation.

**Why it happens:** Temperature > 0, no rubric anchors, free-form prompts give the LLM different calibration each time.

**How to avoid:**
- Categorical rubric (not scalar) — 4 named classes only.
- Anchor examples in EVERY batch prompt — 4 anchors (one per class), never removed.
- `temperature=0` on every scoring call. Claude Code supports this via the model's lowest temperature.
- Metadata logging: after Step 11 completes, write `{run_dir}/intent-meta.json`:
  ```json
  {"model": "claude-sonnet-4-6", "rubric_version": "v1.0", "batches": 3, "keywords_labeled": 87, "scored_at": "2026-05-08T14:30:00Z"}
  ```
- Drift detector: for a 5-10% sample of keywords, run classification twice in separate prompts and flag any that disagree.

**Warning signs:** Two adjacent runs show different intent for the same canonical keyword; intent distribution varies by more than ±10% between runs.

### Pitfall 5 (Intent must precede clustering — ordering enforcement)

**What goes wrong:** Phase 4 reads `ranked.json` and expects every row to have a non-null `intent`. If Phase 3 is incomplete or produces partial labels, Phase 4 will either error out or silently produce intent-mixed clusters.

**How to avoid:**
- Step 12 in SKILL.md must gate on: all keywords in `keywords.json` have a corresponding entry in `intent-labels.json` (match on `lemma_hash`).
- `rank_keywords.py` should exit 3 if any row in `keywords.json` has no matching `lemma_hash` in `intent-labels.json` — hard fail, not silent skip.
- `ranked.json` rows with `"theme": ""` are expected and valid — Phase 4 fills them. But `"intent": null` or missing `intent` is invalid.

---

## Code Examples

### rank_keywords.py — Scoring Core

```python
# scripts/rank_keywords.py
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""rank_keywords.py — keywords.json + intent-labels.json → ranked.json (pure math).

CLI:
    uv run rank_keywords.py --run-dir <abs>

Stdout (exactly one JSON line):
    {"ranked_count": N, "avg_score": float, "intent_distribution": {"transactional": N, ...}}

Exit codes:
    0  ok
    3  fatal (missing input / join failure / unlabeled keywords)
"""

INTENT_WEIGHTS = {
    "transactional":  30,
    "commercial":     20,
    "navigational":   10,
    "informational":   5,
}

def compute_score(source_diversity: int, intent: str, signal_count: int) -> int:
    weight = INTENT_WEIGHTS.get(intent, 5)
    return source_diversity * 100 + weight + signal_count


def build_ranked(keywords: list[dict], labels: dict[str, dict]) -> list[dict]:
    """Join keywords with intent labels and compute scores.

    Args:
        keywords: rows from keywords.json
        labels: dict keyed by lemma_hash from intent-labels.json

    Returns:
        ranked rows sorted by (score desc, signal_count desc, canonical asc)

    Raises:
        ValueError: if any keyword has no matching intent label
    """
    rows = []
    for kw in keywords:
        lh = kw["lemma_hash"]
        label = labels.get(lh)
        if label is None:
            raise ValueError(f"No intent label for lemma_hash={lh} canonical={kw['canonical']!r}")
        intent = label["intent"]
        match_type = label["match_type"]
        score = compute_score(kw["source_diversity"], intent, kw["signal_count"])
        # Compact sources: distinct source strings only
        distinct_sources = sorted({s["source"] for s in kw["sources"]})
        rows.append({
            "keyword":          kw["canonical"],
            "intent":           intent,
            "match_type":       match_type,
            "theme":            "",
            "signal_count":     kw["signal_count"],
            "source_diversity": kw["source_diversity"],
            "sources":          distinct_sources,
            "score":            score,
        })
    rows.sort(key=lambda r: (-r["score"], -r["signal_count"], r["keyword"]))
    return rows
```

### intent-labels.json Minimal Validator

```python
def validate_labels(labels_list: list[dict]) -> dict[str, dict]:
    """Return dict keyed by lemma_hash; raise ValueError on invalid entries."""
    valid_intents = {"informational", "commercial", "transactional", "navigational"}
    valid_match_types = {"phrase", "exact", "broad"}
    out = {}
    for row in labels_list:
        if row.get("intent") not in valid_intents:
            raise ValueError(f"Invalid intent {row.get('intent')!r} for {row.get('canonical')!r}")
        if row.get("match_type") not in valid_match_types:
            raise ValueError(f"Invalid match_type {row.get('match_type')!r} for {row.get('canonical')!r}")
        out[row["lemma_hash"]] = row
    return out
```

### SKILL.md Step 11 Batch Prompt Template

```markdown
### Step 11: Intent labeling

Read `{run_dir}/keywords.json`. Process keywords in batches of ≤ 30.

For EVERY batch, include these calibration anchors at the top of your prompt:
> Anchor examples (do not change these labels):
> - "order grocery delivery" → transactional
> - "best grocery delivery uk" → commercial
> - "how does grocery delivery work" → informational
> - "ocado website" → navigational

For each keyword, assign:
- `intent`: EXACTLY one of: informational | commercial | transactional | navigational
- `match_type`: EXACTLY one of: phrase | exact | broad

Match-type rules:
- exact: navigational with source_diversity ≥ 3, OR transactional with source_diversity ≥ 3
- phrase: all other cases (default)
- broad: do not assign in v1

After all batches, write `{run_dir}/intent-labels.json` via the Write tool.
Verify: every lemma_hash in keywords.json has a matching entry in intent-labels.json.

Do not advance to Step 12 until intent-labels.json passes this check.
```

### "How to Read This" Canonical Snippet (for Phase 6 use)

```markdown
## How to read this report

**signal_count** is NOT search volume. It counts how many source-fragments
(Serper results, PAA questions, Tavily excerpts, WebSearch snippets) surfaced
this keyword during research. A signal_count of 7 means the keyword appeared
across 7 source-fragment hits — not "7 monthly searches."

**source_diversity** counts the number of distinct signal sources that
surfaced the keyword (max 6: serper-organic, serper-paa, serper-related,
serper-ads, tavily-extract, websearch-baseline). Keywords with source_diversity ≥ 3
are corroborated by multiple independent sources and are ranked above
single-source keywords regardless of signal_count.

To estimate actual search volume, paste the keyword list into
[Google Keyword Planner](https://ads.google.com/aw/keywordplanner).
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SKAG (Single Keyword Ad Groups) | Intent-clustered ad groups (STAG pattern) | ~2021-2022 (Google match-type consolidation) | Phase 4 clustering follows STAG; Phase 3 scoring is prerequisite |
| Keyword volume as ranking signal | Source diversity + intent weight (no volume API) | v1 decision, 2026 | Explicit "not volume" labeling is non-negotiable |
| Scalar LLM intent scoring (0-1) | Categorical 4-class rubric, temperature=0 | Best practice established ~2023-2024 | Phase 3 rubric design follows categorical-only approach |
| Broad match as default | Phrase match as default (exact for high-confidence signals) | Google Ads 2021+ match-type consolidation made broad very expansive | Conservative phrase default protects budget; matches RANK-03 |

**Deprecated/outdated:**
- **Broad match as discovery strategy in new campaigns:** Google's 2021 broad match consolidation made broad significantly more expansive; phrase is the safe default in v1.
- **Scalar confidence scores for intent:** Replaced by categorical rubrics across the PPC toolchain for LLM-driven classification (more stable across runs).

---

## Open Questions

1. **Intent weight tuning (transactional=30, commercial=20, navigational=10, informational=5)**
   - What we know: These weights make transactional keywords rise above commercial within the same diversity tier; consistent with PPC value hierarchy.
   - What's unclear: Whether these specific values match the McGrocer use case (grocery delivery may have fewer navigational keywords than assumed).
   - Recommendation: Ship v1 with these weights; review after first 3-5 real runs; adjust in `rank_keywords.py` (one-line change per weight).

2. **Partial intent-labels.json recovery**
   - What we know: `rank_keywords.py` exits 3 if any keyword is unlabeled.
   - What's unclear: What happens if the skill prompt fails mid-batch (e.g., context overflow on very large keyword sets)?
   - Recommendation: Step 11 in SKILL.md should check `len(intent-labels.json) == len(keywords.json)` before invoking `rank_keywords.py`. If short, re-run the missing batch only (not all batches). Document this in SKILL.md anti-patterns.

---

## Validation Architecture

`nyquist_validation: true` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `scripts/tests/conftest.py` (existing) |
| Quick run command | `uv run pytest scripts/tests/test_rank_keywords.py -x -q` |
| Full suite command | `uv run pytest scripts/tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RANK-01 | Intent labeling is done by skill prompt at temperature=0 with categorical rubric | manual | Inspect SKILL.md Step 11 for rubric + anchor examples + temp=0 directive | ❌ Wave 0 (SKILL.md update; manual verification only) |
| RANK-01 | `intent-labels.json` has valid intent values (no nulls, no scalars, only 4 valid classes) | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_validate_labels_rejects_invalid_intent -x` | ❌ Wave 0 |
| RANK-01 | `intent-labels.json` rejects unknown match_type values | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_validate_labels_rejects_invalid_match_type -x` | ❌ Wave 0 |
| RANK-02 | Score formula: source_diversity × 100 + intent_weight + signal_count | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_compute_score_formula -x` | ❌ Wave 0 |
| RANK-02 | Higher source_diversity always outranks lower regardless of signal_count | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_source_diversity_dominates_signal_count -x` | ❌ Wave 0 |
| RANK-02 | Within same diversity tier, transactional outranks commercial, commercial outranks informational | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_intent_weight_ordering -x` | ❌ Wave 0 |
| RANK-02 | Tie-break on signal_count descending, then alphabetical | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_sort_tiebreak -x` | ❌ Wave 0 |
| RANK-02 | `rank_keywords.py` exits 3 if any keyword has no matching intent label | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_missing_label_exits_3 -x` | ❌ Wave 0 |
| RANK-03 | exact assigned to transactional with source_diversity ≥ 3 | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_match_type_exact_transactional -x` | ❌ Wave 0 |
| RANK-03 | exact assigned to navigational with source_diversity ≥ 3 | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_match_type_exact_navigational -x` | ❌ Wave 0 |
| RANK-03 | phrase default for commercial and informational | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_match_type_phrase_default -x` | ❌ Wave 0 |
| RANK-03 | broad never assigned by rank_keywords.py deterministic path | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_no_broad_in_output -x` | ❌ Wave 0 |
| RANK-04 | ranked.json rows contain exactly 8 columns (keyword, intent, match_type, theme, signal_count, source_diversity, sources, score) | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_output_schema_columns -x` | ❌ Wave 0 |
| RANK-04 | `signal_count` field name is never "volume" anywhere in ranked.json | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_no_volume_field_name -x` | ❌ Wave 0 |
| RANK-04 | `theme` field is `""` for all rows in Phase 3 output | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_theme_empty_string -x` | ❌ Wave 0 |
| RANK-04 | `sources` field is list of distinct strings (not the full provenance objects) | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_sources_compact_form -x` | ❌ Wave 0 |
| RANK-01 | Re-running same keywords.json + intent-labels.json produces identical ranked.json | unit | `uv run pytest scripts/tests/test_rank_keywords.py::test_deterministic_output -x` | ❌ Wave 0 |
| RANK-01 (drift) | Same brief run twice produces ≥90% intent agreement | manual | Manual: run two skill sessions on same brief; compare intent-labels.json files | Manual-only (requires real LLM execution) |

### Sampling Rate

- **Per task commit:** `uv run pytest scripts/tests/test_rank_keywords.py -x -q`
- **Per wave merge:** `uv run pytest scripts/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `scripts/tests/test_rank_keywords.py` — covers all RANK-* unit rows above
- [ ] `scripts/tests/fixtures/sample_keywords.json` — realistic keywords.json fixture (3-5 rows, mix of source_diversity values 1-4)
- [ ] `scripts/tests/fixtures/sample_intent_labels.json` — matching intent-labels.json fixture for the sample keywords
- [ ] `scripts/rank_keywords.py` — the script itself (Wave 1 implementation target)

*(No new conftest.py needed — existing `scripts/tests/conftest.py` from Phase 2 covers shared fixtures.)*

---

## Sources

### Primary (HIGH confidence)

- `STATE.md` § Decisions — Locked decisions: categorical 4-class intent rubric, temperature=0, anchor examples, source_diversity primary signal, no volume/CPC API in v1, LLM-driven classification.
- `REQUIREMENTS.md` — RANK-01 through RANK-04 definitions, Phase 3 success criteria.
- `ROADMAP.md` — Phase 3 goal, dependencies, success criteria.
- `merge_signals.py` — Confirmed keywords.json schema: canonical, lemma_hash, signal_count, source_diversity, sources[]. Phase 3 consumes this directly.
- `PITFALLS.md` Pitfall 2, 3, 5 — Intent labeling stability (categorical + temp=0 + anchors), column naming (`signal_count` not volume), intent-before-clustering ordering.
- `SUMMARY.md` — Architecture approach: scripts for deterministic I/O, skill prompt for LLM judgment. Confirmed Phase 3 addresses Pitfalls 2, 3, 5.
- `STACK.md` — stdlib-only rank script confirmed; no new deps needed; uv PEP 723 pattern for all scripts.

### Secondary (MEDIUM confidence)

- `PITFALLS.md` — Performance traps § "LLM context window inflation": batch scoring in groups of 25-50 with rubric anchors; confirmed batching recommendation for Step 11.
- ROADMAP.md Phase 4 dependency — "intent labels must exist before clustering — intent class is hard split"; confirms theme = "" until Phase 4.

### Tertiary (LOW confidence / needs validation)

- Intent weight values (30/20/10/5): synthesized from intent-classification literature and PPC value hierarchy. No industry standard. v1 hypothesis; calibrate after first real runs.
- Drift rate at temperature=0 with categorical rubric: expected ≥ 90% agreement per Pitfall 3 guidance; unverified until real runs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only; confirmed by project stack decisions
- Architecture (skill-does-labeling / script-does-math split): HIGH — follows project's locked orchestrator/script boundary
- Categorical rubric: HIGH — derived directly from locked decisions (STATE.md) and Pitfall 3 mitigations
- Scoring formula: MEDIUM-HIGH — formula is deterministic; weight values are v1 hypothesis
- Pitfall mitigations: HIGH — Pitfalls 2, 3, 5 mitigations are concrete and derived from project research

**Research date:** 2026-05-08
**Valid until:** Stable — no external APIs involved in Phase 3; valid until requirements change. Weight tuning is v1 hypothesis; review after first 5 real runs.
