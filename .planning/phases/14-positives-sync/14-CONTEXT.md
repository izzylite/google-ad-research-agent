# Phase 14: Positives Sync — Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Source:** Operator conversation + parked scope doc `.planning/proposed/v1.4-positives-sync.md`

<domain>
## Phase Boundary

Phase 14 mirrors the **negatives-sync architecture from Phase 8 (GADS-04)** for positives.

**What ships:**
- New GAQL query against `keyword_view` in `perf_fetch.py` → `raw/google-ads-keywords.json`
- New `cross_ref_positives()` function in `perf_synth.py` → `positives-sync.json` (4 buckets)
- New `render_positives_sync_section()` in `render_report.py` (md + HTML) mirroring negatives-sync UX
- `export_csv.py` filters `positives.csv` to `new_to_add` by default; `--include-existing` override
- Graceful skip when `raw/google-ads-keywords.json` absent (no OAuth)
- SKILL.md adds LLM re-tag step after script-based cross-ref for semantic dupes
- Test coverage: unit tests + byte-exact golden fixture

**What does NOT ship:**
- No new external APIs (reuses existing Google Ads OAuth + free quota)
- No changes to ranking logic — sync is post-rank filter only
- No bid-conflict detection (existing kw at higher CPC than suggested)
- No match-type auto-tightening recommendations
- No Ahrefs paid-kw fallback for accounts without OAuth (separate future phase)
- No auto-pause of kw already running in account — surface, let operator decide

</domain>

<decisions>
## Implementation Decisions

### Data source
- **Google Ads API `keyword_view`** is the authoritative source (NOT Ahrefs paid-kw inference).
- Reason: OAuth already wired in Phase 8; truth not inference; includes status (ENABLED/PAUSED) + match_type + perf metrics.
- Ahrefs paid-kw fallback was considered as a path for accounts without OAuth — deferred to a future phase.

### GAQL query shape (POS-01)
```
SELECT
  ad_group.id, ad_group.name,
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type,
  ad_group_criterion.status,
  metrics.impressions, metrics.clicks, metrics.conversions, metrics.cost_micros
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_criterion.status != 'REMOVED'
```
- Last 30 days segment (matches existing Phase 8 search_term_view + campaign queries).
- Exclude REMOVED status (only ENABLED + PAUSED matter for sync).
- PMax campaigns return no kw-level data — they're silently absent from `keyword_view`; no explicit filter needed.

### Bucket taxonomy (POS-02) — 4 buckets
- `already_active` — match (exact + lemma-hash), status ENABLED
- `paused_in_account` — match, status PAUSED → operator decides reactivate vs leave
- `covered_by_broad` — ranked kw (any match-type) lies within broad-match coverage of an active broad-match kw in account (heuristic: substring or shared head tokens)
- `new_to_add` — no match in account

### LLM re-tag step (POS-06) — REQUIRED, NOT OPTIONAL
- User explicitly promoted POS-06 from "optional polish" to required scope during questioning.
- LLM re-tag fires AFTER `cross_ref_positives` produces `positives-sync.json`.
- LLM reads ranked.json + positives-sync.json + competitor-intel.json (for context) and re-tags borderline cases.
- Catches ~20% of cases plain string-norm misses: token reorder, semantic dupe, match-type drift.
- Writes refined output back to `positives-sync.json` (overwrites script-only buckets).
- SKILL.md gets a new step in Phase 8 sub-flow with anchor examples.

### Match-type semantics (covered_by_broad heuristic)
- Google broad-match expansion is fuzzy — heuristic will have false positives.
- Mitigation 1: LLM re-tag step catches obvious misses.
- Mitigation 2: Surface `covered_by_broad` bucket as "review", not "skip" — operator decides whether to add exact for tighter targeting.

### Stats line shape
Mirror negatives-sync stats: `our_total / already_active / paused_in_account / covered_by_broad / new_to_add` — single bold count per bucket on one line.

### CSV filter behavior (POS-04)
- Default when `positives-sync.json` present: emit only `new_to_add` rows.
- `--include-existing` flag → emit all 4 buckets, with `Status` column added (`new` / `already_active` / `paused` / `broad_covered`).
- When `positives-sync.json` absent: full ranked list (current behavior unchanged).

### Graceful skip (POS-05)
- If `raw/google-ads-keywords.json` doesn't exist (no OAuth env vars OR Phase 8 perf_fetch never ran):
  - `perf_synth.py` skips `cross_ref_positives`; no `positives-sync.json` written
  - `render_report.py` omits "Positives Sync" section (mirrors how negatives-sync section omits when `negatives-sync.json` absent)
  - `export_csv.py` emits full ranked list (default v1.0 behavior)
- No error surfaced. Phase 14 is purely additive.

### Test coverage (POS-07)
- `test_perf_fetch.py`: respx mock for `keyword_view` GAQL response; assert correct query string built + raw JSON write
- `test_perf_synth.py`: 4 unit tests, one per bucket; assert tagging correct for fixture pairs
- `tests/fixtures/golden_positives_sync.json` — byte-exact golden fixture (mirror pattern of `golden_positives.csv` in Phase 10)
- `test_export_csv.py`: assert default filter + `--include-existing` both produce correct row counts
- `test_render_report.py`: assert section omits when missing, renders when present

### Claude's Discretion
- Exact regex / heuristic for `covered_by_broad` detection (substring vs token overlap vs Levenshtein) — planner picks; tests must cover both true-positive and false-positive cases
- HTML collapsible vs flat for `paused_in_account` + `covered_by_broad` buckets — match how negatives-sync renders those buckets today
- LLM re-tag prompt structure — anchor examples + JSON output schema, planner drafts; SKILL.md ≤500 lines rule applies
- Wave structure — likely 1 wave (sequential: perf_fetch → perf_synth → render + export); planner decides parallelism

</decisions>

<specifics>
## Specific Ideas

### Files that will change (planner reference)
- **Modify:** `.claude/skills/google-ad-research/scripts/perf_fetch.py` — new GAQL query + writer
- **Modify:** `.claude/skills/google-ad-research/scripts/perf_synth.py` — new `cross_ref_positives()` function
- **Modify:** `.claude/skills/google-ad-research/scripts/render_report.py` — new `render_positives_sync_section()` (md + HTML)
- **Modify:** `.claude/skills/google-ad-research/scripts/export_csv.py` — filter logic + `--include-existing` flag
- **Modify:** `.claude/skills/google-ad-research/SKILL.md` — new LLM re-tag step (≤500 line rule)
- **Modify:** `.claude/skills/google-ad-research/references/phase8-account-data.md` — note new sub-step + downstream contract
- **New:** `.claude/skills/google-ad-research/scripts/tests/fixtures/golden_positives_sync.json`
- **New:** `.claude/skills/google-ad-research/scripts/tests/fixtures/google-ads-keywords-fixture.json`
- **Modify:** `tests/test_perf_fetch.py`, `tests/test_perf_synth.py`, `tests/test_export_csv.py`, `tests/test_render_report.py`

### Architecture mirror points (Phase 8 GADS-04 → Phase 14 POS)
- Phase 8 wrote `negatives-sync.json` with `stats` + `new_by_tier` + `already_in_account` → Phase 14 writes `positives-sync.json` with `stats` + `new_to_add` + 3 other buckets
- Phase 8 `_norm_neg()` lowercase + strip → Phase 14 reuses same `_norm_neg()` for kw text canonicalization (or extracts a shared `_norm_kw()` helper)
- Phase 8 `render_negatives_sync_section()` → copy/adapt for `render_positives_sync_section()`
- Phase 8 raw → synth → render flow → Phase 14 mirrors exactly

### Borderline cases LLM must catch (anchor examples for POS-06)
1. Token reorder: `urgent care lake worth` (ranked) vs `lake worth urgent care` (active) → `already_active`
2. Match-type drift: ranked exact `pip insurance clinic` vs account broad `pip clinic` → `covered_by_broad`
3. Semantic synonym: ranked `open 24 hours` vs account `24 hour clinic` (both transactional) → `already_active`
4. Match-type narrowing opportunity: ranked exact `car accident chiropractor` vs account broad `car accident` → `covered_by_broad` BUT flagged for operator review (exact narrows targeting)
5. Locale variant: ranked Spanish `clinica de accidente` vs account English-only `accident clinic` → stays `new_to_add` (locale gap is legitimate net-new)

</specifics>

<deferred>
## Deferred Ideas

- **Ahrefs paid-kw fallback** for accounts without Google Ads OAuth — separate future phase; v1.4 ships OAuth path only
- **Bid-conflict detection** — flag ranked kw whose `suggested_max_cpc_micros` is lower/higher than current account bid — defer; v1.4 only detects presence, not bid drift
- **Match-type auto-tightening** — auto-suggest "add as exact" when ranked exact lies under account broad — surface via `covered_by_broad` bucket; operator decides; no auto-action
- **Negative-keyword conflict check** on `new_to_add` — Editor warns at import time; redundant to bake into v1.4
- **PMax kw inference** — PMax doesn't expose kw, no API path; out of scope
- **Auto-pause active kw with low conv + low ranked-score** — perf-aware pruning; v1.4 only ADDS, never removes/pauses

</deferred>

---

*Phase: 14-positives-sync*
*Context gathered: 2026-05-15 via conversation + parked scope doc consolidation*
