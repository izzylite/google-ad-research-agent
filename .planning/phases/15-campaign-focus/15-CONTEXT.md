# Phase 15: Campaign Focus — Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Source:** Operator conversation + parked scope doc `.planning/proposed/v1.5-account-aware-narrowing.md` (Issue 1)

<domain>
## Phase Boundary

Phase 15 mirrors **Phase 11's `geo_focus` architectural pattern** (v1.2 shipped) at the campaign-name level.

**What ships:**
- New optional `campaign_focus:` brief field — parsed by `_parse_brief_fields` alongside existing `geo_focus`
- `perf_fetch.py --campaign-filter '<name>'` CLI flag — auto-populated from brief.md by SKILL.md
- All 4 GAQL queries (`keyword_view`, `search_term_view`, `ad_group`, `campaign_criterion`) gain `AND campaign.name = '<name>'` filter when set
- Report header renders "Campaign Focus" callout beside Geographic Focus
- Name validation against `raw/google-ads-perf.json` campaigns list → warns operator on typo
- Test coverage: respx assertion on GAQL filter clause + render typo warning test

**What does NOT ship:**
- Campaign inference from brief content (operator names campaign explicitly — same opt-in pattern as `geo_focus`)
- Account-wide vs campaign-scoped TOGGLE — `campaign_focus` presence IS the toggle
- New external APIs (reuses existing Google Ads OAuth from Phase 8)
- Changes to Positives Sync / Negatives Sync / Ad Group Mapping LOGIC — they inherit narrowed raw data automatically
- AG token-bag enrichment (that's Phase 16 — separate phase)

</domain>

<decisions>
## Implementation Decisions

### Brief field shape (CAMP-01)
- Field name: `Campaign focus:` (matches `Geographic focus:` convention from Phase 11)
- Value: single campaign name string OR pipe-separated list (`A | B | C`)
- Position: appears after `Geographic focus:` in brief.md when both present
- Parser: `_parse_brief_fields()` in `render_report.py` extends to extract `campaign_focus`
- Output shape: `brief_fields["campaign_focus"]` returns list of campaign-name strings (single value wrapped in 1-element list); empty list when absent — mirrors `geo_focus` exactly

### GAQL filter clause (CAMP-02)
Single value:
```sql
AND campaign.name = 'Search | Lake Worth Accident Exams | Manual CPC'
```
List (≥2 values):
```sql
AND campaign.name IN ('Search | Lake Worth Accident Exams | Manual CPC', 'Lake Worth- Car Accidents - Call Only')
```
- Applied to all 4 perf_fetch queries: `fetch_keyword_view`, `fetch_search_terms`, `fetch_perf`, `fetch_existing_negatives`
- Escape single quotes in campaign names by doubling: `O''Brien Auto` → `'O''Brien Auto'` (standard SQL escaping)
- Empty filter list → no clause added (graceful degrade)

### CLI flag (CAMP-02)
- `perf_fetch.py --campaign-filter '<name>'` — single value
- `perf_fetch.py --campaign-filter 'A|B|C'` — list (pipe-separated, mirrors `--geo-focus` from Phase 11)
- When absent → account-wide (current v1.4 behavior)

### SKILL.md wiring (CAMP-03)
- SKILL.md Phase 8 Step 33 `perf_fetch.py` invocation auto-passes `--campaign-filter "${campaign_focus}"` when brief.md has the field
- New line in Step 33: `[--campaign-filter "<focus>"]` parallel to existing `[--customer-id <id>]`
- Skill announces "Narrowing to campaign: <focus>" before fetch when set

### Graceful degrade (CAMP-04)
- Brief omits `Campaign focus:` → `campaign_focus = []` → no `--campaign-filter` passed → no GAQL clause → account-wide pull (v1.4 behavior preserved bit-for-bit)
- Phase 14 (Positives Sync) + Phase 11 (AG Mapping) inherit narrowed raw data without code changes — they consume `raw/*.json` as-is

### Report header (CAMP-05)
- `render_campaign_focus_section()` new helper in render_report.py — mirrors `render_geographic_focus_section`
- Appears after Geographic Focus callout, before Compliance Required
- Format: `**Campaign:** Search | Lake Worth Accident Exams | Manual CPC` (single) OR bulleted list (≥2)
- Validation: load `raw/google-ads-perf.json` campaigns list; if any focus name absent → render warning callout `⚠ Campaign name not found in account: '<name>' — check for typo`

### Test coverage (CAMP-06)
- `test_perf_fetch.py`: respx mock asserts `campaign.name =` (single) and `campaign.name IN` (list) appear in outgoing GAQL when `--campaign-filter` set; assert absent when flag omitted
- `test_render_report.py`: assert Campaign Focus callout renders when brief has field; assert typo warning fires when name not in perf.json campaigns list
- Golden brief fixture w/ `Campaign focus:` line for byte-exact rendering test

### Claude's Discretion
- Exact regex for `_parse_brief_fields` — planner picks; should handle both `Campaign focus:` and `**Campaign focus:**` (bold variant) per Phase 11 precedent
- Wave structure — likely 1 wave RED scaffolding + 1 wave production (perf_fetch + render parallel since different files) + 1 wave SKILL.md wiring; planner decides
- Whether to extract `_apply_campaign_filter(query, focus)` helper or inline the clause in each fetch function — planner picks based on duplication tolerance

</decisions>

<specifics>
## Specific Ideas

### Files that will change (planner reference)
- **Modify:** `.claude/skills/google-ad-research/scripts/perf_fetch.py` — add `--campaign-filter` arg + thread through 4 fetch functions
- **Modify:** `.claude/skills/google-ad-research/scripts/render_report.py` — extend `_parse_brief_fields` + add `render_campaign_focus_section` + name validation
- **Modify:** `.claude/skills/google-ad-research/SKILL.md` — Phase 8 Step 33 auto-passes `--campaign-filter` (≤500 line rule applies)
- **Modify:** `.claude/skills/google-ad-research/references/phase8-account-data.md` — note campaign_focus in Step 33 + downstream contract
- **New:** `.claude/skills/google-ad-research/scripts/tests/fixtures/brief_with_campaign_focus.md`
- **Modify:** `tests/test_perf_fetch.py` + `tests/test_render_report.py`

### Architecture mirror points (Phase 11 GEO → Phase 15 CAMP)
| Phase 11 (GEO) | Phase 15 (CAMP) |
|---|---|
| `Geographic focus:` brief field | `Campaign focus:` brief field |
| `_parse_brief_fields["geo_focus"]` → list | `_parse_brief_fields["campaign_focus"]` → list |
| `serp_fetch.py --geo-focus` | `perf_fetch.py --campaign-filter` |
| us-cities.json validation | perf.json campaigns list validation |
| `render_geographic_focus_section()` | `render_campaign_focus_section()` |
| Filters SERP / merge_signals | Filters Phase 8 GAQL queries |

### Borderline cases planner must handle
1. Campaign name contains single quotes (e.g., `O'Brien Auto`) → SQL escape to `'O''Brien Auto'`
2. Campaign name contains pipe character → not a list separator when inside a single quoted name; only the `--campaign-filter 'A|B'` CLI form treats unquoted pipes as separators
3. Brief has `Campaign focus:` blank line → treat as absent
4. Operator typos campaign name → render warning + still proceed (don't fail-fast; empty raw is its own signal)
5. Campaign exists but has 0 ad groups in last 30 days (paused entirely) → filtered raw is empty; downstream sections render "no data" gracefully

</specifics>

<deferred>
## Deferred Ideas

- **PMax exception** — PMax campaigns return no kw-level data; campaign_focus filter just makes this more explicit. Out-of-scope for Phase 15 (handled by existing `WHERE ad_group_criterion.status != 'REMOVED'` filter; PMax campaigns silently absent from `keyword_view`).
- **Inference from brief topic** — auto-suggest campaign name from brief.md content. Deferred — operator-explicit pattern matches Phase 11 `geo_focus` precedent.
- **MCC-level rollup** — campaign_focus applies per-customer; MCC parent rollup out of scope.
- **AG Mapping algorithm enrichment** — Phase 16 (separate phase, calibrates against Phase 15's narrowed dataset)
- **Performance-aware match weighting** — separate future concern

</deferred>

---

*Phase: 15-campaign-focus*
*Context gathered: 2026-05-15 via parked-scope-doc consolidation + Phase 11 architectural mirror*
