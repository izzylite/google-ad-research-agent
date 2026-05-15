# Phase 16: Ad Group Mapping Token-Bag Enrichment — Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Source:** Operator conversation + parked scope `.planning/proposed/v1.5-account-aware-narrowing.md` (Issue 2) + Lake Worth Phase 15 dogfood evidence

<domain>
## Phase Boundary

Phase 16 enriches the Jaccard input for `ad_group_match.py` so coverage lifts from current 0% (Phase 15 narrowed run) to ≥50% on real client accounts whose AG names are short labels.

**Today's behavior** (post-Phase-15):
- `_build_ad_group_index()` builds AG token bag from **search-term tokens only** (last 30d `search_term_view`)
- Lake Worth run: 3 narrowed AGs × 47 ranked kw → still 0% high+medium coverage because Lake Worth's AGs have sparse 30-day search history
- AG name tokens NOT in the bag; kw_criterion (Phase 14 `raw/google-ads-keywords.json`) NOT in the bag

**What ships:**
- `_build_ag_token_bag(ag_name, kw_criteria, search_terms)` — bag = AG name tokens ∪ kw_criterion tokens ∪ top-10 search-term tokens (by clicks)
- `_build_ad_group_index()` rewired to call `_build_ag_token_bag()` per AG
- Match `reason` field extended to surface contribution per source (`"jaccard=0.42 on kw-criterion bag; name=0.10; intent=transactional match"`)
- Threshold recalibration in `_THRESHOLDS` — measured calibration on Lake Worth + 1 synthetic fixture; expected ~0.5/0.25 from current 0.7/0.4
- Graceful degrade — when Phase 14 `raw/google-ads-keywords.json` absent, bag = AG name ∪ search-terms (current Phase 11 behavior plus AG name addition)
- references/phase11-account-structure-mapping.md updated with calibration rationale + new bag composition
- Test coverage: golden mapping fixture sourced from Lake Worth real-account data asserting ≥50% high+medium coverage; backward-compat fixture asserting old behavior preserved when keywords.json absent

**What does NOT ship:**
- No LLM semantic similarity (cost + non-determinism)
- No performance-aware match weighting (high-ROAS AGs win ties) — deferred
- No PMax handling (PMax has no kw-criterion)
- No new external APIs (reuses existing raw artifacts from Phase 8 + Phase 14)
- No change to `ad-group-mapping.json` top-level schema (matches[] / unmapped_count / mapping_coverage_pct stay) — only `match.reason` content shape extends
- No change to confidence tier names (high / medium / low) — only thresholds may recalibrate

</domain>

<decisions>
## Implementation Decisions

### Token bag composition (ADGM-07)
```
bag(ag) = _tokens(ag.name) ∪ kw_criterion_tokens(ag) ∪ top10_search_term_tokens(ag)
```
- **AG name tokens**: tokenize via existing `_tokens()` (lowercase, stopword filter, punctuation strip)
- **kw_criterion tokens**: from `raw/google-ads-keywords.json` items, filter to `ad_group_name == ag.name` AND `status != REMOVED`, tokenize each kw_text, union
- **Top-10 search-term tokens by clicks**: replace current "all search terms" — top 10 by clicks descending; tiebreak by impressions descending; drop zero-impression terms
- All three union into single frozenset → still passed to existing `_jaccard()` (no algorithm change beyond input)

### Backward compat (ADGM-08)
- `raw/google-ads-keywords.json` absent → kw_criterion tokens = ∅; bag = AG name ∪ search-terms (degrades to Phase 11 + name addition)
- `raw/google-ads-search-terms.json` absent (already handled) → degrades further to AG name ∪ kw_criteria (Phase 11 graceful-skip preserved)
- Both absent → bag = AG name only (last-resort minimum)
- AG with empty bag (all 3 sources contribute nothing) → still excluded from index (existing Pitfall 6 behavior)

### Match reason field (ADGM-09)
Current `match.reason`: `"jaccard=0.04 intent_match=False"`
New `match.reason`: `"jaccard=0.42 (name=0.10 kw-criterion=0.32 search-term=0.20) intent_match=True"`
- Surface partial Jaccards per source so operator can audit which evidence drove the decision
- Compute per-source Jaccards using same `_jaccard()` against partial bags; OR Jaccard runs once on union bag with per-source contribution traced via set intersection cardinality
- Implementation choice deferred to planner — simplest is run `_jaccard()` 3 times (per partial bag) + once on union; cost is trivial at typical sizes (47 kw × 3 AGs × 4 jaccards = 564 ops)

### Threshold recalibration (ADGM-10)
- Larger bags → score compression. Current 0.7/0.4 will rarely fire post-enrichment.
- **Measured calibration**: run on Lake Worth fixture + 1 synthetic fixture; find thresholds that yield 50%+ coverage on Lake Worth while still rejecting clearly-mismatched kw
- Starting hypothesis: **0.45 high / 0.20 medium** (from CONTEXT-doc estimate 0.5/0.25, adjusted slightly down because intent multiplier of 0.5 halves a same-token-overlap score when intents mismatch)
- Final values land via empirical calibration during plan 16-02 (TDD: golden fixture from Lake Worth defines target coverage)
- Updated `_THRESHOLDS` w/ same frozenset assertion; `references/phase11-account-structure-mapping.md` documents rationale + before/after coverage numbers

### Test coverage (ADGM-11)
- **Lake Worth golden fixture**: pulled from `.runs/2026-05-15T153121Z-car-accident-injury-care-services/` (real campaign-narrowed data) — staged into `tests/fixtures/` as `ranked_lake_worth.json` + `perf_lake_worth.json` + `search_terms_lake_worth.json` + `keywords_lake_worth.json`
- Test asserts `mapping_coverage_pct >= 50.0` on Lake Worth golden
- **Backward-compat fixture**: same Lake Worth scenario MINUS `keywords.json` → assert coverage falls to 0-20% (Phase 11 behavior preserved)
- **Per-source attribution test**: assert `match.reason` substring contains `name=`, `kw-criterion=`, `search-term=` when keywords.json present
- **Empty-bag test**: AG with no search terms + no kw-criteria + AG name has only stopwords → AG excluded from index (Pitfall 6 preserved)
- **Threshold sentinel test**: assert `_THRESHOLDS["high"] < 0.7` to lock the calibration delta (sentinel — fails loud if someone reverts)

### Claude's Discretion
- Top-N for search-terms (10 vs 5 vs 15) — planner picks; default 10 per CONTEXT
- Exact reason field format string — planner formats `f"jaccard={s:.2f} (...) intent_match={b}"` consistently
- Calibration approach — empirical (test-driven on golden fixture) or theoretical (compute optimal from token-bag size distribution); planner picks empirical for auditability
- Wave structure — likely 1 RED scaffolding + 1 production (single file `ad_group_match.py`) + 1 docs/calibration; planner decides

</decisions>

<specifics>
## Specific Ideas

### Files that will change (planner reference)
- **Modify:** `.claude/skills/google-ad-research/scripts/ad_group_match.py` — new `_build_ag_token_bag()` helper + rewire `_build_ad_group_index()` + extend `build_mapping()` reason field + update `_THRESHOLDS`
- **Modify:** `.claude/skills/google-ad-research/references/phase11-account-structure-mapping.md` — Pitfall section update + calibration rationale + bag composition diagram
- **New:** `.claude/skills/google-ad-research/scripts/tests/fixtures/ranked_lake_worth.json` + 3 raw fixtures
- **New:** `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_mapping_lake_worth.json` (≥50% coverage)
- **Modify:** `tests/test_ad_group_match.py`

### Architecture (today vs Phase 16)

| Source | Current bag | Phase 16 bag |
|---|---|---|
| AG name tokens | ❌ excluded | ✅ included |
| kw_criterion tokens | ❌ excluded | ✅ included (when keywords.json present) |
| search-term tokens | ✅ all of last 30d | ✅ top-10 by clicks |

### Borderline cases planner must handle
1. AG has 100+ kw_criteria — token bag could be 200+ tokens; Jaccard denominator inflates. Top-N cap on kw_criterion tokens too? Discretion — recommend ALL kw_criterion tokens (they're already operator-curated, smaller signal-to-noise than search terms)
2. Single AG with very generic kw `[* clinic *]` broad match → "clinic" alone, weak signal; rely on Jaccard intersection with ranked kw + intent multiplier filtering
3. AG name is a pure label (e.g. `Ad group 1`, `RSA`) — tokens after stopword filter is empty set, fine, bag still has criterion + search-term contributions
4. Brand new AG with no kw, no search history — empty bag → excluded from index → kw can't route to it (correct; "no signal = no match")
5. Phase 14 `raw/google-ads-keywords.json` exists but has items in OTHER campaigns (when Phase 15 narrowing wasn't used) — filter by ad_group_name match only; campaign-level filtering is Phase 15's job

</specifics>

<deferred>
## Deferred Ideas

- LLM semantic similarity (cost + non-determinism)
- Performance-aware match weighting (high-ROAS AGs win ties)
- PMax campaign handling (no kw-criterion exists)
- Auto-create new ad groups in operator's account — skill stays suggest-only
- Dynamic threshold tuning per-account (adaptive based on bag-size distribution)
- Cross-campaign matching (operator runs without Phase 15 narrowing) — out of scope; rely on Phase 15

</deferred>

---

*Phase: 16-ad-group-mapping-token-bag-enrichment*
*Context gathered: 2026-05-15 via parked-scope-doc consolidation + Phase 15 live-run evidence*
