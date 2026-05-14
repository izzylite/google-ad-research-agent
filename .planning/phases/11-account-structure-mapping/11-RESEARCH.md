# Phase 11: Account-Structure Mapping - Research

**Researched:** 2026-05-14
**Domain:** Geographic SERP refinement + ad-group similarity matching against existing client account structure
**Confidence:** HIGH

## Summary

Phase 11 is a pure-compute, two-concern phase that piggybacks on already-shipped scaffolding:

1. **Geographic refinement (GEO-01..05):** extend `run_init.py` brief intake with optional `geo_focus`; pipe tokens into `serp_fetch.py` query strings; add a city-level wrong-geo filter to `merge_signals.py` (the state-level filter is already in place — see `_keyword_drifts_geo` / `US_STATE_TOKENS` / `AMBIGUOUS_CITIES` in `merge_signals.py:64-97`); render a "Geographic Focus" callout in `render_report.py`.
2. **Ad-Group Mapping (ADGM-01..06):** new `ad_group_match.py` sidecar reads `raw/google-ads-perf.json` + `raw/google-ads-search-terms.json`, builds an existing-ad-group → token-bag index, computes Jaccard × intent-match similarity per ranked keyword, emits `ad-group-mapping.json`. `export_csv.py` rewrites the Ad Group column from the mapping; `render_report.py` rewrites Next Steps step 3 when coverage > 50%.

All work follows already-proven patterns in this codebase: PEP 723 inline metadata, `uv run`, lib/ shared utilities, stdout-JSON contract, exit-code taxonomy (0 ok / 2 retryable / 3 fatal), test scaffolding before implementation. SKILL.md is at the 500-line cap — Phase 11 details MUST extract to `references/phase11-account-structure-mapping.md` (single-line pointer in SKILL.md, mirroring phases 5/7/8/9/10).

**Primary recommendation:** Wave 0 (tests + us-cities.json data + ad_group_match.py MODULE_INCOMPLETE stub) → Wave 1 (geo plumbing + ad_group_match.py core, parallel) → Wave 2 (export_csv + render_report integrations, parallel) → Wave 3 (SKILL.md pointer + references file + human-verify smoke). Mirrors Phase 10's RED-scaffolded waveline exactly.

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase (Phase 11 has no `/gsd:discuss-phase` artifact). All Phase 11 design constraints come from REQUIREMENTS.md GEO-01..05 + ADGM-01..06, the orchestrator's additional_context block, and project conventions in CLAUDE.md.

### Locked Decisions (from REQUIREMENTS.md + additional_context)

- **`references/us-cities.json` is the canonical wrong-city data file** — operator-editable, ~30KB target, top 5000 US cities. Sourced from US Census place data or simplemaps.com free dataset.
- **`ad-group-mapping.json` is a sidecar at run_dir root** — never mutates `ranked.json` / `ranked-enriched.json` / `clusters.json` (mirrors Phase 8 sidecar pattern).
- **Confidence tiers are config-block constants with frozenset assertion** — `high >= 0.7`, `medium >= 0.4 < 0.7`, `low < 0.4`. Threshold values frozen at module import.
- **Coverage threshold 50%** — value lives in single config block at top of `render_report.py` Next Steps rewrite logic (configurable per ADGM-06 + additional_context point 8).
- **Skip silently when Phase 8 not run** (ADGM-01) — missing `raw/google-ads-perf.json` exits 0 with empty mapping JSON, not exit 3.
- **Geographic Focus callout omitted gracefully when geo_focus empty** (GEO-05) — no empty section header.
- **SKILL.md ≤500 lines** — Phase 11 details extract to `references/phase11-account-structure-mapping.md` (project convention; see Phase 5/7/8/9/10 precedent).
- **All scripts PEP 723 inline metadata, `uv run`-only invocation, secrets via `lib/config.load_env()`, never CLI args.**
- **Run-folder isolation preserved** — no caching, no cross-run state.

### Claude's Discretion

- Tokenization for similarity: simple `re.findall(r"\b[a-z]{2,}\b", text.lower())` vs. stop-word-aware. Recommend stop-word-aware (see Pitfall 3).
- Token bag aggregation key: `ad_group_name` vs `ad_group_id`. **Verified: search_terms.json carries `ad_group_name` ONLY (no id field)** — must group by name. Confirmed by reading `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/raw/google-ads-search-terms.json`.
- Similarity formula exact shape: Jaccard × intent-match-multiplier. Recommend `jaccard * (1.0 if intent_match else 0.5)` (additional_context point 4).
- Whether to use `ad_groups` array from `google-ads-perf.json` as the authoritative ad-group list (with names + status) or derive ad-group list purely from `search_terms.json` distinct `ad_group_name` values. Recommend: use BOTH — `perf.json.ad_groups[].name` as the canonical existing-ad-group list (with status filter — exclude REMOVED), `search_terms.json` as the token-bag source bucketed by `ad_group_name`.
- Intent inference for existing ad groups: deferred to Phase 3 logic or re-classify. Recommend: derive dominant intent of existing ad group from the most-frequent intent class among its bucketed search_terms after running them through the rank_keywords intent rubric — OR simpler heuristic: count keyword-token matches against a small intent-marker lexicon (transactional: buy/order/cheap/near/me; commercial: best/top/review/vs; informational: how/what/why; navigational: brand-name tokens). Recommend the heuristic for v1 — avoids dependency on calling the LLM again for ad-group classification.

### Deferred Ideas (OUT OF SCOPE)

- Embedding-based similarity (e.g., sentence-transformers) — already excluded by PROJECT.md "v2 fallback only" decision; token overlap is sufficient.
- Multi-account / cross-customer ad-group matching — single client per run.
- Auto-creation of new campaigns in Google Ads — explicit out-of-scope in REQUIREMENTS.md "Out of Scope" table (Editor CSV is the launch path).
- Per-cluster geo-bias (only top-level location + geo_focus tokens land in queries) — GEO-02 scope is single seed-level append, not per-cluster customization.
- Dynamic intent classification of existing ad groups via LLM — costs API budget; deferred until v2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| **GEO-01** | Brief intake accepts optional `geo_focus` list (counties/cities). Skill prompts conditionally when location is state-level. | Extension to `run_init.py` (read field from stdin brief markdown — already parses brief verbatim) + SKILL.md Step 3 trigger for optional follow-up. Brief.md `**Geo focus:**` line read by `merge_signals.py` and downstream. |
| **GEO-02** | `serp_fetch.py` appends `geo_focus` tokens to query strings. | New `--geo-focus` CLI arg or read from brief.md; serps `q` payload field gets tokens appended. SKILL.md Step 8 invocation updated. |
| **GEO-03** | `merge_signals.py` drops keywords containing OTHER-city tokens in same state. | Existing state-level `_keyword_drifts_geo` filter (lines 283-304) extended with city-level check using `us-cities.json` lookup. Hierarchy: city → its county → is county/city in `geo_focus`? |
| **GEO-04** | `references/us-cities.json` reference data file (top 5000 US cities). | New data file. Format recommendation: `{state_code: {city_lower: county_lower}}` keyed for O(1) lookup. Counties also stored as separate state-scoped keys. Source: US Census Gazetteer or simplemaps.com basic free CSV. |
| **GEO-05** | `render_report.py` adds "Geographic Focus" callout. | New helper `render_geographic_focus_section()` returns markdown string or "". Position: after Header block, before Compliance Warning. Reads brief.md for location + geo_focus. |
| **ADGM-01** | `ad_group_match.py` reads `raw/google-ads-perf.json` + `raw/google-ads-search-terms.json`. Skip silently when absent. | New sidecar script. `perf.json.ad_groups[]` (filter status=ENABLED) gives existing-ad-group list; `search_terms.json.items[].ad_group_name` gives token bag per ad group. Exit 0 with empty mapping when files absent. |
| **ADGM-02** | Similarity = token overlap × intent match per ranked keyword. Threshold default 0.4. | Algorithm: `jaccard(kw_tokens, ad_group_token_bag) * intent_multiplier`. Intent multiplier 1.0 same / 0.5 different. Pick highest-scoring match above threshold. |
| **ADGM-03** | Confidence tiers `high >= 0.7`, `medium 0.4-0.7`, `low < 0.4` in single config block, frozenset-asserted. | Module-level `_THRESHOLDS = {"high": 0.7, "medium": 0.4}` with `assert frozenset(_THRESHOLDS) == frozenset({"high", "medium"})`. Pattern from Phase 9 `INTENT_MULTIPLIERS`. |
| **ADGM-04** | Emit `ad-group-mapping.json` sidecar `{matches: [...], unmapped_count, mapping_coverage_pct}`. | Schema: `{"matches": [{"keyword": str, "existing_ad_group": str, "confidence": "high"|"medium"|"low", "score": float, "reason": str}], "unmapped_count": int, "mapping_coverage_pct": float, "computed_at": ISO}`. Written to run_dir root. |
| **ADGM-05** | `export_csv.py` reads `ad-group-mapping.json`; matched rows → existing ad group name; ad_groups.csv lists only NEW. | Extend `_build_positives_rows` to consult mapping; extend `_build_ad_groups_rows` to filter out existing-ad-group names. Backward compat: mapping absent → fall back to cluster name (current behavior). |
| **ADGM-06** | `render_report.py` Next Steps step 3 conditionally rewrites when coverage > 50%. | Extend `render_next_steps_section` to read mapping; substitute step 3 text with "Add keywords to existing ad groups: A (N kw), B (M kw); plus NEW: X, Y" when `coverage_pct > 50`. Step text remains in `_STANDARD_NEXT_STEPS_TEMPLATE`. |

</phase_requirements>

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13 (PEP 723) | Runtime | Project convention; all helpers declare `requires-python = ">=3.11"` or `">=3.13"` |
| `argparse` | stdlib | CLI parsing | Already used by every script in `scripts/` |
| `json` | stdlib | JSON read/write + stdout contract | Already used everywhere |
| `re` | stdlib | Tokenization | Already used in `merge_signals.py` for token extraction |
| `pathlib.Path` | stdlib | Path handling | Project convention |
| `lib.log.configure_logger` | local | Structured stderr logging | Already used by all sidecars |
| `lib.io` | local | Markdown sanitization | Already used by `render_report.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `csv` | stdlib | (already imported in `export_csv.py`) | No new use; existing reader is sufficient |
| `pytest` | dev-only | Test framework | Per CLAUDE.md run-tests command; tests use `--with pytest --with python-dotenv --with python-slugify` |

### Alternatives Considered (and rejected)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stdlib-only `ad_group_match.py` | `rapidfuzz` | Token overlap (Jaccard) is exact for this use case; adding a fuzz dependency for one script breaks the "stdlib-only sidecar" pattern proven in Phase 8 `perf_synth.py` and Phase 9 `compliance_check.py`. |
| Hand-rolled `us-cities.json` | `geopy` / `uszipcode` package | 30KB static JSON is < 1% the install footprint of either, fully offline, operator-editable. |
| Jaccard | TF-IDF cosine | TF-IDF needs `sklearn` (PROJECT.md "v2 fallback only"); Jaccard is one line, no deps. Operator-comprehensible. |
| LLM-driven ad-group similarity | n/a | Adds API cost to a phase that should be pure-compute. Heuristic is auditable and fast. |

**Installation:** No new dependencies. Both new scripts (`ad_group_match.py`) are stdlib-only PEP 723 (mirrors `perf_synth.py:1-7` / `export_csv.py:1-4`).

## Architecture Patterns

### Recommended Project Structure

```
.claude/skills/google-ad-research/
├── SKILL.md                                       # +1 pointer line for Phase 11 (stay under 500)
├── references/
│   ├── phase11-account-structure-mapping.md      # NEW — full Phase 11 step rubric
│   └── us-cities.json                            # NEW — ~30KB reference data (GEO-04)
└── scripts/
    ├── run_init.py                               # MODIFY — read geo_focus from brief
    ├── serp_fetch.py                             # MODIFY — append geo_focus tokens to q
    ├── merge_signals.py                          # MODIFY — city-level wrong-geo filter
    ├── ad_group_match.py                         # NEW — ADGM-01..04 sidecar
    ├── export_csv.py                             # MODIFY — read ad-group-mapping.json (ADGM-05)
    ├── render_report.py                          # MODIFY — Geographic Focus callout + Next Steps rewrite
    └── tests/
        ├── fixtures/
        │   ├── us-cities-subset.json             # NEW — small FL/TX/CA fixture
        │   ├── google-ads-perf-phase11.json      # NEW — 3-4 ad groups with names
        │   ├── google-ads-search-terms-phase11.json # NEW — token bags per ad group
        │   ├── ad-group-mapping-high-coverage.json  # NEW — 70% coverage fixture
        │   ├── ad-group-mapping-low-coverage.json   # NEW — 20% coverage fixture
        │   └── brief-with-geo-focus.md           # NEW — brief.md with **Geo focus:** line
        ├── test_geo_filter.py                    # NEW — GEO-03 filter unit tests
        ├── test_ad_group_match.py                # NEW — ADGM-01..04 unit tests
        ├── test_export_csv.py                    # EXTEND — ADGM-05 cases
        ├── test_render_report.py                 # EXTEND — GEO-05 + ADGM-06 cases
        ├── test_serp_fetch.py                    # EXTEND — GEO-02 query string contains tokens
        ├── test_run_init.py                      # EXTEND — GEO-01 brief.md contains Geo focus line
        └── test_merge_signals.py                 # EXTEND — GEO-03 integration
```

### Pattern 1: Sidecar Script (proven by Phase 8 `perf_synth.py` and Phase 9 `compliance_check.py`)

**What:** A self-contained Python script with PEP 723 inline metadata, stdlib-only deps, single `--run-dir` CLI arg, JSON-on-stdout contract, 0/2/3 exit codes.

**When to use:** New `ad_group_match.py` follows this exactly.

**Example:**
```python
# Source: scripts/perf_synth.py:1-7 (paste verbatim style)
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""ad_group_match.py — Map ranked keywords to existing ad groups.

Reads:
    {run_dir}/ranked-enriched.json (or ranked.json fallback)
    {run_dir}/raw/google-ads-perf.json
    {run_dir}/raw/google-ads-search-terms.json

Writes:
    {run_dir}/ad-group-mapping.json — {matches[], unmapped_count, mapping_coverage_pct}

CLI:
    uv run ad_group_match.py --run-dir <abs>

Stdout (one JSON line):
    {"mapping_path": "...", "total_ranked": N, "matched_high": N,
     "matched_medium": N, "unmapped": N, "coverage_pct": float}

Exit codes:
    0  ok (including silent skip — no perf.json present)
    2  retryable (disk PermissionError / OSError)
    3  fatal (--run-dir missing / ranked.json unparseable)
"""
```

### Pattern 2: Config-block frozen taxonomy (Phase 9 / Phase 10 precedent)

**What:** Module-level dict with `assert frozenset(...) == frozenset({...})` immediately after to fail fast at import if the taxonomy drifts.

**When to use:** `_THRESHOLDS` in `ad_group_match.py`; `_COVERAGE_THRESHOLD` in `render_report.py` next-steps logic.

**Example:**
```python
# Source: scripts/export_csv.py:64-85 (TIER_TO_LEVEL + MATCH_TYPE_TITLECASE pattern)
_THRESHOLDS: dict[str, float] = {
    "high": 0.7,
    "medium": 0.4,
}
assert frozenset(_THRESHOLDS) == frozenset({"high", "medium"}), (
    "_THRESHOLDS drift — ADGM-03 taxonomy changed?"
)
_DEFAULT_INTENT_MISMATCH_MULTIPLIER = 0.5
_DEFAULT_COVERAGE_REWRITE_PCT = 50.0
```

### Pattern 3: Wave 0 RED scaffold (Phase 10 plan 10-00 precedent)

**What:** Wave 0 ships test stubs that import a module-incomplete sentinel; module exists with header constants + `NotImplementedError`-raising `main()`. Tests `try: import x` succeeds; `MODULE_INCOMPLETE = not hasattr(x, "build_mapping")` is the GREEN signal.

**When to use:** `ad_group_match.py` Wave 0 stub with `_THRESHOLDS` locked + `build_mapping()` absent + `main()` raises NotImplementedError. Per-function hasattr guards on extension tests in `test_export_csv.py` / `test_render_report.py`.

**Example:** See STATE.md "[Phase 10]: [10-00] Stub-then-guard pattern" decision.

### Pattern 4: Stdout-JSON contract (every helper in scripts/)

**What:** Every CLI prints exactly one JSON line on stdout (success); stderr carries human-readable progress via `lib.log.configure_logger()`.

**When to use:** `ad_group_match.py` stdout summary mirrors `perf_synth.py:219-226`.

### Pattern 5: Geographic Focus callout = render-only helper (Phase 9 compliance precedent)

**What:** `render_compliance_warning(compliance)` in `render_report.py:502` returns empty string when absent; identical pattern for `render_geographic_focus_section(brief_fields)`.

```python
# Source: scripts/render_report.py:502 (render_compliance_warning shape)
def render_geographic_focus_section(brief_fields: dict[str, str]) -> str:
    """Render '## Geographic Focus' callout. Empty geo_focus → ''."""
    geo_focus = (brief_fields or {}).get("geo_focus") or ""
    location = (brief_fields or {}).get("location") or ""
    if not geo_focus.strip():
        return ""
    return (
        "## Geographic Focus\n\n"
        f"**Location:** {location} → **Focus:** {geo_focus}\n\n"
    )
```

### Anti-Patterns to Avoid

- **Don't grow SKILL.md past 500 lines.** Phase 11 step rubric MUST land in `references/phase11-account-structure-mapping.md`; SKILL.md gets one pointer line per Phase 5/7/8/9/10 precedent.
- **Don't mutate `ranked.json` / `ranked-enriched.json` / `clusters.json`.** Mapping is a sidecar (mirrors Phase 8). `export_csv.py` consumes both at write time.
- **Don't add HTTP / network calls to `ad_group_match.py`.** Pure compute. No `httpx`. No `lib/http.py` import.
- **Don't bake LLM intent re-classification into ad_group_match.py** for v1. Use the heuristic intent-marker lexicon.
- **Don't put the coverage threshold in a magic number.** Configurable constant at top of `render_report.py` (additional_context point 8 — "make configurable in single config block").
- **Don't write the `us-cities.json` from a generator script.** It's reference data, hand-curated subset (top 5000), committed to the repo. Operator can edit. Sourced from US Census Gazetteer or simplemaps free CSV.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| US city/county lookup | Hand-typed Python dict in code | `references/us-cities.json` (data) loaded once | Operator extends without code edits (ADGM-02 "data not code" rule from STATE.md decisions) |
| Set similarity | Custom overlap math | Python set `&` and `\|` for Jaccard | Stdlib correctness; one-liner: `len(a & b) / len(a \| b) if a \| b else 0` |
| Token extraction | Per-script regex variation | `re.findall(r"\b[a-z]{2,}\b", text.lower())` — same regex used in `merge_signals.py:290` | Consistency; minimum 2-letter tokens drops single-char noise |
| CSV writing | Hand-rolled string formatting | `csv.DictWriter` (already used in `export_csv.py`) | RFC 4180 quoting + Editor v2.x byte contract already proven |
| Markdown sanitization | Custom escapes | `lib.io.escape_md_cell` | Already used in `render_report.py` table cells |
| Brief field parsing | Re-parse brief.md ad-hoc | One `_parse_brief_fields(brief_text)` helper in `render_report.py` | Already exists (used for location/language substitution in Next Steps) — extend to read `**Geo focus:**` line |
| Confidence-tier branching | If/elif chains scattered | Single `_classify_confidence(score) -> "high"\|"medium"\|"low"` reading `_THRESHOLDS` | Frozenset-asserted; one place to tune |

**Key insight:** Phase 11 introduces ZERO new dependencies. Every problem has an existing in-codebase solution — the work is wiring, not new infrastructure.

## Common Pitfalls

### Pitfall 1: `search_terms.json` has `ad_group_name`, NOT `ad_group_id`

**What goes wrong:** Bucketing by `ad_group_id` produces empty token bags.

**Why it happens:** The fetched Google Ads search-terms view only carries `ad_group_name` (and `campaign_name`). Verified by reading the sample `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/raw/google-ads-search-terms.json` — line 16-17 shows `"ad_group_name": "Accident Exams – Lake Worth"` with no id.

**How to avoid:** Token bag aggregation key is `ad_group_name`. Cross-reference against `perf.json.ad_groups[].name` (which has both name AND id, but we only need name).

**Warning signs:** Empty token bags; all keywords falling to confidence=low.

### Pitfall 2: Unicode em-dash / en-dash in ad-group names

**What goes wrong:** Existing ad-group names contain en-dashes (U+2013) and em-dashes (U+2014) — e.g., `"Accident Exams – Lake Worth"`, `"P-Max – Accident Exams – LW & PS – Calls"`. CSV writers and string comparisons must preserve these byte-for-byte.

**Why it happens:** Google Ads accounts often use Unicode dashes for visual hierarchy.

**How to avoid:** UTF-8 encoding everywhere (already locked in `export_csv.py:191` — `encoding="utf-8"`). Don't normalize/strip Unicode in token-overlap math — only lowercase + `re.findall` extraction of word characters.

**Warning signs:** Ad-group name shows up garbled in `positives.csv` Ad Group column.

### Pitfall 3: "near me" tokens dominate similarity

**What goes wrong:** Every car-accident-related search term contains "near" and "me". Jaccard against a token bag that has hundreds of "near me" mentions gives every keyword a non-trivial similarity score even when the topic doesn't match.

**Why it happens:** Stop-word noise in geo + commercial-intent queries.

**How to avoid:** Apply a small stop-word filter before tokenization. Recommended set: `{"near", "me", "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "with", "by", "from"}`. Apply identically to both sides of Jaccard.

**Warning signs:** All confidences trending toward 0.4-0.6 band; mapping coverage abnormally high; "near me" matches everything.

### Pitfall 4: Wrong-city false positives — homonym cities across states

**What goes wrong:** Brief targets "Lake Worth, FL"; "Lake Worth" exists in both FL and TX. The state-level filter already in `merge_signals.py:_keyword_drifts_geo` handles state-token drift, but city homonym disambiguation requires the new us-cities.json lookup.

**Why it happens:** ~30% of common US city names recur in multiple states.

**How to avoid:** `us-cities.json` is keyed by state_code first (`{"FL": {...}, "TX": {...}}`). The filter only looks up cities under the brief's detected state. Existing `AMBIGUOUS_CITIES` dict in `merge_signals.py:86-97` already lists these.

**Warning signs:** Tampa results surfacing in a Palm Beach County run; Hollywood (CA) results surfacing in a Hollywood (FL) brief.

### Pitfall 5: City → county → geo_focus hierarchy

**What goes wrong:** Brief sets `geo_focus = ["Palm Beach County"]`. The keyword "boca raton dentist" should NOT be dropped (Boca Raton IS in Palm Beach County) but a naive token-match would drop it because "boca raton" is not literally in `geo_focus`.

**Why it happens:** Counties contain many cities; only checking city-name string membership misses the hierarchy.

**How to avoid:** us-cities.json schema MUST carry county per city: `{"fl": {"boca raton": "palm beach", "lake worth": "palm beach", "tampa": "hillsborough", ...}}`. Filter logic: city found → look up its county → if county OR city is in geo_focus (case-insensitive), KEEP; else DROP.

**Warning signs:** All within-target-county cities being filtered out; `keywords.json` smaller than expected after geo filter active.

### Pitfall 6: Empty perf.json / Phase 8 not run

**What goes wrong:** `ad_group_match.py` exits 3 (fatal) when `raw/google-ads-perf.json` is missing → blocks Phase 6 report rendering downstream.

**Why it happens:** Phase 8 is optional (some operator runs skip account data); Phase 11 must degrade gracefully.

**How to avoid:** Missing perf.json OR search_terms.json → exit 0 with `ad-group-mapping.json` containing `{"matches": [], "unmapped_count": N, "mapping_coverage_pct": 0.0}`. Log a single info-level "Phase 8 artifacts absent — skipping ad-group mapping" to stderr. `export_csv.py` already tolerates absent mapping (falls back to cluster name).

**Warning signs:** Operator hasn't run Phase 8 but Phase 11 crashes; CI fails on Phase 11 alone.

### Pitfall 7: Coverage % uses unmatched / total, not low-tier / total

**What goes wrong:** ADGM-04 specifies `mapping_coverage_pct`. If "coverage" counts low-tier (< 0.4) matches, the metric inflates falsely. If it counts only high+medium, low-tier rows can still be reported as matched in `matches[]` (per additional_context point 8: "low = no match, fallback to cluster").

**Why it happens:** Naming ambiguity — "match" vs. "useful match."

**How to avoid:** Define coverage = `(high + medium matches) / total_ranked`. Low-tier matches are recorded for traceability but DON'T contribute to coverage and DON'T trigger the Next Steps rewrite (ADGM-06). Document in module docstring.

**Warning signs:** Next Steps rewrites when most matches are low-confidence cluster fallbacks; operator complains "this isn't actually mapped."

### Pitfall 8: `geo_focus` token appended to query strings double-locates

**What goes wrong:** Operator's seeds at SKILL.md Step 6 already include location composites ("lake worth car accident doctor"); GEO-02 appends `geo_focus` tokens → "lake worth car accident doctor Palm Beach County" — redundant + may confuse Google's locality heuristic.

**Why it happens:** Phase 2 already builds product+location composites in seeds.

**How to avoid:** GEO-02 token append happens ONCE per query, AND only when not already textually present (cheap `if token.lower() not in q.lower()` guard). Document in serp_fetch.py docstring.

**Warning signs:** Serper organic results returning duplicates / lower-quality matches than Phase 2 baseline.

### Pitfall 9: SKILL.md crosses 500-line cap when adding Phase 11 wiring

**What goes wrong:** SKILL.md is currently 500/500 (exact cap per additional_context). Adding even a 5-line Phase 11 section breaks the cap.

**Why it happens:** Project rule (CLAUDE.md): ≤500 lines, extract to `references/`.

**How to avoid:** Phase 11 SKILL.md change is ONE pointer line (model: line 499-500 Phase 10 pointer). Full step rubric goes in `references/phase11-account-structure-mapping.md`. Verify line count post-edit before commit.

**Warning signs:** `wc -l SKILL.md` > 500 after Wave 3 edit.

### Pitfall 10: us-cities.json size budget

**What goes wrong:** A full US Census place file is 5-10 MB; even subsetting to top 5000 cities at ~50 fields each can exceed 500KB if county/population/lat-lon all retained.

**Why it happens:** Naive copy-paste from Census source.

**How to avoid:** Schema is minimal: `{state_code_lower: {city_name_lower: county_name_lower}}`. ~5000 cities × 30 bytes average = ~150KB at the high end, ~30KB at the low end if state codes are aggressively short and county names share many duplicates. Recommend: top 5000 by population, sourced from simplemaps "Basic" free dataset (US Census-derived) at https://simplemaps.com/data/us-cities.

**Warning signs:** `references/us-cities.json` over 500KB; git diffs slow.

## Code Examples

Verified patterns from in-repo sources.

### Sidecar script entrypoint (Phase 8 pattern, applied to ad_group_match.py)

```python
# Source: scripts/perf_synth.py:162-227 (perf_synth main_with_args)
def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Map ranked keywords to existing ad groups.")
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    run_dir: Path = args.run_dir
    if not run_dir.exists():
        print(json.dumps({"error": f"--run-dir does not exist: {run_dir}"}), file=sys.stderr)
        return 3

    raw_dir = run_dir / "raw"
    perf_path = raw_dir / "google-ads-perf.json"
    terms_path = raw_dir / "google-ads-search-terms.json"
    ranked_path = run_dir / "ranked-enriched.json"
    if not ranked_path.exists():
        ranked_path = run_dir / "ranked.json"

    if not perf_path.exists() or not terms_path.exists():
        # ADGM-01: graceful skip (Pitfall 6)
        mapping = {"matches": [], "unmapped_count": 0, "mapping_coverage_pct": 0.0,
                   "skipped_reason": "phase8_artifacts_absent"}
        (run_dir / "ad-group-mapping.json").write_text(json.dumps(mapping, indent=2))
        print(json.dumps({"mapping_path": str(run_dir / "ad-group-mapping.json"),
                          "skipped": True, "coverage_pct": 0.0}))
        return 0

    # ... build mapping ...
```

### Jaccard with stop-word filter (ADGM-02)

```python
# Source: pattern aligned with merge_signals.py:290 token regex
_STOPWORDS: frozenset[str] = frozenset({
    "near", "me", "the", "a", "an", "of", "in", "on", "at", "to", "for",
    "and", "or", "with", "by", "from", "is", "are", "best", "top",
})
_TOKEN_RE = re.compile(r"\b[a-z]{2,}\b")

def _tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS)

def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0
```

### Confidence tier classifier (ADGM-03)

```python
# Source: export_csv.py:64-85 (TIER_TO_LEVEL + frozenset assertion)
_THRESHOLDS: dict[str, float] = {"high": 0.7, "medium": 0.4}
assert frozenset(_THRESHOLDS) == frozenset({"high", "medium"}), (
    "_THRESHOLDS drift — ADGM-03 taxonomy changed?"
)

def _classify(score: float) -> str:
    if score >= _THRESHOLDS["high"]:
        return "high"
    if score >= _THRESHOLDS["medium"]:
        return "medium"
    return "low"
```

### City → county → geo_focus filter (GEO-03)

```python
# Extends merge_signals.py _keyword_drifts_geo pattern
def _build_city_filter(state_code: str, geo_focus: list[str], us_cities: dict) -> dict:
    """Return {"cities_in_focus": set, "cities_out_of_focus": set} for filter."""
    state_cities = us_cities.get(state_code.lower(), {})
    geo_focus_lower = {g.lower().strip() for g in geo_focus}
    in_focus, out_of_focus = set(), set()
    for city, county in state_cities.items():
        if city in geo_focus_lower or county in geo_focus_lower:
            in_focus.add(city)
        else:
            out_of_focus.add(city)
    return {"in": in_focus, "out": out_of_focus}

def _keyword_drifts_city(text: str, city_filter: dict) -> bool:
    if not city_filter["out"]:
        return False
    lower = text.lower()
    # Multi-word city match
    return any(c in lower for c in city_filter["out"])
```

### us-cities.json schema (GEO-04)

```json
{
  "fl": {
    "lake worth": "palm beach",
    "boca raton": "palm beach",
    "west palm beach": "palm beach",
    "tampa": "hillsborough",
    "miami": "miami-dade",
    "jacksonville": "duval"
  },
  "tx": {
    "lake worth": "tarrant",
    "dallas": "dallas",
    "houston": "harris"
  },
  "ca": {
    "los angeles": "los angeles",
    "hollywood": "los angeles"
  }
}
```

### Coverage-driven Next Steps rewrite (ADGM-06)

```python
# Source: render_report.py:777 (render_next_steps_section signature extension)
_COVERAGE_REWRITE_PCT: float = 50.0  # ADGM-06: > this → rewrite step 3

def _rewrite_step_3_if_high_coverage(
    steps_text: list[str],
    mapping: dict | None,
) -> list[str]:
    if not mapping or mapping.get("mapping_coverage_pct", 0.0) <= _COVERAGE_REWRITE_PCT:
        return steps_text
    # Tally per-existing-ad-group keyword counts
    from collections import Counter
    by_ag = Counter()
    for m in mapping.get("matches", []):
        if m.get("confidence") in ("high", "medium"):
            by_ag[m["existing_ad_group"]] += 1
    add_to = ", ".join(f"{name} ({n} kw)" for name, n in by_ag.most_common())
    # Step 3 in _STANDARD_NEXT_STEPS_TEMPLATE is "Create ad groups: {cluster_names_csv}"
    steps_text[2] = f"Add keywords to existing ad groups: {add_to}"
    return steps_text
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| State-level wrong-geo filter only (`merge_signals.py:_keyword_drifts_geo`) | + City-level filter via `us-cities.json` data lookup | Phase 11 (this phase) | Brief can target counties/cities precisely; out-of-county cities drop from keyword pool |
| All keywords mapped to NEW cluster ad groups | Ranked keywords mapped to EXISTING ad groups when similarity ≥ 0.4 | Phase 11 | Preserves client's account structure; avoids Editor duplicate-name errors |
| `export_csv.py` Ad Group always = cluster slug | Ad Group = existing ad-group name when mapping matches; cluster slug when unmapped | Phase 11 ADGM-05 | Operator pastes positives.csv directly into existing campaign without re-bucketing |
| Next Steps step 3 always "Create ad groups: ..." | Conditional rewrite when coverage > 50% | Phase 11 ADGM-06 | Bespoke per-run instructions; junior operator sees existing structure mentioned by name |

**Deprecated/outdated:** Nothing deprecated. Phase 11 is purely additive.

## Open Questions

1. **us-cities.json sourcing — Census Gazetteer vs simplemaps?**
   - What we know: Both are free, US Census-derived. Census Gazetteer is canonical but the file is wide (50+ fields). simplemaps "Basic" is curated, includes county_name, smaller file.
   - What's unclear: Licensing for redistribution in a public repo. Census Gazetteer is public domain; simplemaps Basic has a permissive license but requires attribution.
   - Recommendation: Pull from US Census Gazetteer "Places" file (https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html) and write a one-time generator script (NOT committed; output JSON IS committed). Header comment in `us-cities.json` references the source URL + Census-derived note. No license concern.

2. **Should `serp_fetch.py` use the `location` parameter for fine geo, or only append tokens to `q`?**
   - What we know: `serp_fetch.py:140-142` already accepts an optional `--location` arg (e.g., 'Lake Worth, Florida, United States'). GEO-02 specifies token append to `q`.
   - What's unclear: Whether to also wire `geo_focus` into the `--location` param for stronger locality bias.
   - Recommendation: GEO-02 scope is `q` only (per REQUIREMENTS.md verbatim). Don't expand scope; leave `--location` operator-controlled. Document in references/phase11 step rubric.

3. **Intent classification for existing ad groups — heuristic or LLM?**
   - What we know: Additional_context point 4 says "intent class match (1.0 if ad_group's dominant intent matches our_keyword's intent, 0.5 otherwise)". Existing ad groups have no intent label.
   - What's unclear: Whether to apply Phase 3 LLM rubric to existing ad groups (cost) or use a lexicon heuristic (free but lower fidelity).
   - Recommendation: Lexicon heuristic for v1 (additional_context confirms heuristic approach). Add as future-work note: re-classify via Phase 3 LLM in v2 if mapping accuracy < 70% in real-world testing.

4. **What if mapping coverage is exactly 50.0%?**
   - What we know: ADGM-06 says "> 50%". Boundary case.
   - Recommendation: Strict `> 50.0` per REQUIREMENTS verbatim. Document boundary in test fixture (one fixture at 50.0% → no rewrite; one at 50.1% → rewrite).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (latest via `uv run --with pytest`) |
| Config file | `scripts/pyproject.toml` (added in Phase 5 per STATE.md decision) |
| Quick run command | `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py -x` |
| Full suite command | `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| **GEO-01** | `run_init.py` writes brief.md containing `**Geo focus:**` line when stdin brief has the field | unit | `pytest tests/test_run_init.py::test_geo_focus_persisted -x` | ❌ Wave 0 (extension to existing file) |
| **GEO-02** | `serp_fetch.py` query payload includes geo_focus tokens appended to seed | unit (respx mock) | `pytest tests/test_serp_fetch.py::test_geo_focus_appended_to_query -x` | ❌ Wave 0 (extension) |
| **GEO-03** | `merge_signals.py` drops "tampa pain clinic" from FL run with `geo_focus=["Palm Beach County"]`; KEEPS "lake worth chiropractor" | unit | `pytest tests/test_geo_filter.py -x` | ❌ Wave 0 (new file) |
| **GEO-03** (integration) | merge_signals + us-cities.json end-to-end | integration | `pytest tests/test_merge_signals.py::test_city_filter_active -x` | ❌ Wave 0 (extension) |
| **GEO-04** | `references/us-cities.json` loads as JSON; FL state contains "tampa" + "lake worth" with correct county values | unit | `pytest tests/test_geo_filter.py::test_us_cities_loadable -x` | ❌ Wave 0 |
| **GEO-05** | `render_report.py` emits `## Geographic Focus` when geo_focus non-empty; omitted when empty | unit | `pytest tests/test_render_report.py::test_geo_focus_section -x` | ❌ Wave 0 (extension) |
| **ADGM-01** | `ad_group_match.py` exits 0 with empty matches when perf.json absent | unit | `pytest tests/test_ad_group_match.py::test_phase8_absent_graceful_skip -x` | ❌ Wave 0 (new file) |
| **ADGM-02** | Jaccard × intent-mismatch math; threshold 0.4 default | unit | `pytest tests/test_ad_group_match.py::test_similarity_math -x` | ❌ Wave 0 |
| **ADGM-03** | Confidence tier classifier: 0.75 → high, 0.5 → medium, 0.2 → low | unit | `pytest tests/test_ad_group_match.py::test_confidence_tiers -x` | ❌ Wave 0 |
| **ADGM-04** | `ad-group-mapping.json` schema: matches[], unmapped_count, mapping_coverage_pct | unit | `pytest tests/test_ad_group_match.py::test_mapping_shape -x` | ❌ Wave 0 |
| **ADGM-05** | `export_csv.py` positives Ad Group = existing name when mapping high/medium; cluster slug when low | unit | `pytest tests/test_export_csv.py::test_existing_ad_group_in_positives -x` | ❌ Wave 0 (extension) |
| **ADGM-05** | `export_csv.py` ad_groups.csv excludes existing-ad-group names | unit | `pytest tests/test_export_csv.py::test_ad_groups_csv_skips_existing -x` | ❌ Wave 0 (extension) |
| **ADGM-06** | Next Steps step 3 rewrites when coverage > 50% (use 51% fixture); does NOT rewrite at 50.0% | unit | `pytest tests/test_render_report.py::test_next_steps_rewrite_high_coverage -x` | ❌ Wave 0 (extension) |
| End-to-end smoke | Reuse `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/` | manual smoke | Wave 3 — operator runs full pipeline | ❌ manual |

### Sampling Rate

- **Per task commit:** `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/test_<changed>.py -x`
- **Per wave merge:** Full suite — `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/ -x`
- **Phase gate:** Full suite green + manual end-to-end smoke on real Phase 8 run-folder before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `scripts/tests/test_ad_group_match.py` — new file; covers ADGM-01..04
- [ ] `scripts/tests/test_geo_filter.py` — new file; covers GEO-03 + GEO-04
- [ ] `scripts/tests/test_run_init.py` — extend with GEO-01 case (brief.md contains `**Geo focus:**`)
- [ ] `scripts/tests/test_serp_fetch.py` — extend with GEO-02 case (query string includes geo_focus tokens; respx captures)
- [ ] `scripts/tests/test_merge_signals.py` — extend with GEO-03 integration case (city filter active given a brief + us-cities.json fixture)
- [ ] `scripts/tests/test_export_csv.py` — extend with ADGM-05 cases (positives Ad Group resolution + ad_groups.csv exclusion of existing)
- [ ] `scripts/tests/test_render_report.py` — extend with GEO-05 + ADGM-06 cases (Geographic Focus section + Next Steps step 3 rewrite)
- [ ] `scripts/tests/fixtures/us-cities-subset.json` — small fixture with FL, TX, CA states for fast tests
- [ ] `scripts/tests/fixtures/google-ads-perf-phase11.json` — 3-4 ad groups (Lake Worth Accident, Car Injury Care, Sports Injury, Generic Urgent Care)
- [ ] `scripts/tests/fixtures/google-ads-search-terms-phase11.json` — token bags per ad group (use real shape: `ad_group_name` not `ad_group_id`)
- [ ] `scripts/tests/fixtures/ad-group-mapping-high-coverage.json` — 70% coverage fixture for ADGM-06 rewrite test
- [ ] `scripts/tests/fixtures/ad-group-mapping-low-coverage.json` — 20% coverage fixture for negative test
- [ ] `scripts/tests/fixtures/brief-with-geo-focus.md` — brief.md with `**Geo focus:**` line
- [ ] `references/us-cities.json` — top 5000 US cities; SHOULD ship in Wave 1 (data plumbing) since Wave 0 fixture is a subset
- [ ] No framework install needed — pytest already used by all phases

## Sources

### Primary (HIGH confidence)

- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\REQUIREMENTS.md` — GEO-01..05 + ADGM-01..06 verbatim, traceability table
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\STATE.md` — accumulated decisions through Phase 10; sidecar / config-block / RED-scaffold patterns
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\.planning\ROADMAP.md` — Phase 11 block with success criteria
- `c:\Users\Izzy\Documents\Projects\google-ad-research-agent\CLAUDE.md` — PEP 723 + uv run + 500-line cap + run-folder isolation
- `.claude/skills/google-ad-research/SKILL.md` — currently 500/500 lines; Phase 5/7/8/9/10 pointer pattern (line 473, 485, 491, 497, 499)
- `.claude/skills/google-ad-research/scripts/merge_signals.py` — existing `_keyword_drifts_geo` / `US_STATE_TOKENS` / `AMBIGUOUS_CITIES` (lines 64-97, 283-304) — GEO-03 extends this
- `.claude/skills/google-ad-research/scripts/serp_fetch.py` — payload shape, `--location` arg precedent (line 140) — GEO-02 extends this
- `.claude/skills/google-ad-research/scripts/export_csv.py` — `_THRESHOLDS` frozenset assertion pattern (lines 64-85), `_build_positives_rows` / `_build_ad_groups_rows` extension points (lines 241, 292) — ADGM-05 extends these
- `.claude/skills/google-ad-research/scripts/render_report.py` — `render_next_steps_section` signature (line 777), `_STANDARD_NEXT_STEPS_TEMPLATE` substitution, `_derive_brief_slug` (line 720) — ADGM-06 + GEO-05 extend these
- `.claude/skills/google-ad-research/scripts/perf_synth.py` — sidecar script pattern (stdlib-only, CLI, exit codes) — `ad_group_match.py` blueprint
- `.claude/skills/google-ad-research/scripts/run_init.py` — brief.md stdin parsing — GEO-01 extends
- `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/raw/google-ads-perf.json` — VERIFIED real perf.json schema: `campaigns[]` + `ad_groups[]` with `ad_group_id, name, status, campaign_name, cost_usd, ...`
- `.runs/.../google-ads-search-terms.json` — VERIFIED real schema: `items[]` with `search_term, ad_group_name` (NO ad_group_id field — Pitfall 1 source)

### Secondary (MEDIUM confidence)

- US Census Bureau Gazetteer Files (https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html) — canonical US places source; public domain; verified via knowledge of US Census data products
- simplemaps US Cities Basic dataset (https://simplemaps.com/data/us-cities) — alternative source; permissive license requiring attribution

### Tertiary (LOW confidence)

- None used. All findings backed by direct file inspection or REQUIREMENTS verbatim.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep already in project; zero new libraries
- Architecture: HIGH — sidecar / config-block / RED-scaffold patterns each have 2-3 in-repo precedents (Phase 8, 9, 10)
- Pitfalls: HIGH — Pitfalls 1, 2, 4, 6 verified by reading real run-folder fixture files; Pitfalls 3, 5, 7, 8, 9, 10 are project-rule and design-discipline derived
- us-cities.json sourcing: MEDIUM — requires operator decision on Census Gazetteer vs simplemaps; recommendation given but final choice belongs to planner

**Research date:** 2026-05-14
**Valid until:** 2026-06-13 (30 days — phase is internal, no fast-moving external dependencies)
