---
phase: 15-campaign-focus
plan: 03
subsystem: skill-wiring
tags: [skill-md, campaign-focus, gaql, perf-fetch, references-doc, phase8, operator-ux]

# Dependency graph
requires:
  - phase: 15-01
    provides: perf_fetch.py --campaign-filter CLI flag + 4-query GAQL threading + _apply_campaign_filter helper
  - phase: 15-02
    provides: render_report.py _parse_brief_fields[campaign_focus] + render_campaign_focus_section + report.json campaign_focus key
provides:
  - SKILL.md Step 3 campaign_focus trigger row (optional fields table)
  - SKILL.md Step 4 brief template "- **Campaign focus:** {campaign_focus}" line
  - references/phase8-account-data.md Step 33 --campaign-filter auto-pass contract + CAMP-04 graceful-degrade doc
  - references/phase8-account-data.md Phase 15 downstream-inheritance block (Positives Sync / Negatives Sync / AG Mapping inherit narrowed raw automatically)
  - references/phase8-account-data.md anti-pattern entries (don't post-filter raw; don't surround pipe-list with bracketing pipes)
  - Live e2e verification on real Lake Worth car-accident/urgent-care account confirming end-to-end narrowing
affects: [phase-16-ag-token-bag-enrichment, future-multi-campaign-runs, operator-brief-authoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Brief-field → CLI-flag auto-pass mirroring Phase 11 geo_focus → serp_fetch --geo-focus (operator types field once in brief, SKILL.md threads it)"
    - "Progressive disclosure: SKILL.md carries trigger row + template line (≤500-line cap); detailed contract lives in references/phase8-account-data.md (loaded on demand)"
    - "Downstream-inheritance documentation: narrowing is a property of raw data, not synth layer — Positives Sync / Negatives Sync / AG Mapping need zero per-script wiring"

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/SKILL.md
    - .claude/skills/google-ad-research/references/phase8-account-data.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Step 33 detailed contract lives in references/phase8-account-data.md (not SKILL.md inline) — keeps SKILL.md at 497/500 lines, below CLAUDE.md hard cap"
  - "Pipe-list parsing rule documented: ' | ' (space-pipe-space) preserves Google-Ads naming-convention single names; bare '|' (no spaces) is the list separator. Critical because real campaign names like 'Search | Lake Worth Accident Exams | Manual CPC' include the convention"
  - "Anti-pattern flagged: don't post-filter raw artifacts after account-wide fetch — re-run perf_fetch.py with --campaign-filter (Google Ads quota is free)"

patterns-established:
  - "Phase 15 wiring layer = Phase 11 wiring layer rerun: brief field → optional table trigger row → brief template line → references doc Step XX contract. Repeatable for any future narrowing dimension."
  - "Live e2e on real OAuth account is the closeout gate, not unit tests alone — Plan 15-00 / 15-01 / 15-02 unit tests are necessary but not sufficient; only a real Google Ads pull confirms the GAQL clause actually narrows server-side."

requirements-completed: [CAMP-03, CAMP-04]

# Metrics
duration: ~12 min (3 commits + live e2e wait)
completed: 2026-05-15
---

# Phase 15 Plan 03: SKILL.md + references/phase8-account-data.md Campaign Focus Wiring Summary

**Operator-facing wiring layer for `campaign_focus` — brief.md field threads through SKILL.md Step 3/4 + Step 33 invocation into `perf_fetch.py --campaign-filter`, verified end-to-end against real Lake Worth OAuth account narrowing 30+ campaigns → 1, 35+ ad groups → 3, full account → 47 focused keywords.**

## Performance

- **Duration:** ~12 min (excluding live e2e wait time)
- **Started:** 2026-05-15T15:23Z
- **Completed:** 2026-05-15T15:45Z (after live verification approved)
- **Tasks:** 3 (2 auto + 1 checkpoint:human-verify)
- **Files modified:** 3 (2 skill files + REQUIREMENTS.md mark-complete)

## Accomplishments

- SKILL.md Step 3 optional-fields table carries `**campaign_focus**` trigger row mirroring the existing `**geo_focus**` row — operator opt-in via brief is unambiguous
- SKILL.md Step 4 brief template carries `- **Campaign focus:** {campaign_focus}` line inside `## Optional` block
- SKILL.md stays at **497/500 lines** after edits (CLAUDE.md hard cap respected — Step 33 detail correctly offloaded to references/)
- references/phase8-account-data.md Step 33 block documents `--campaign-filter "{campaign_focus}"` auto-pass, CAMP-04 graceful-degrade contract (omit field → account-wide / v1.4 behavior preserved bit-for-bit), single-quote escape rule, and pipe-list parsing rule
- references/phase8-account-data.md carries new "Phase 15 downstream contract (CAMP-04 inheritance)" subsection explaining Positives Sync / Negatives Sync / AG Mapping inherit the narrowed raw artifacts automatically (no per-script wiring needed)
- Live e2e on real Lake Worth car-accident/urgent-care OAuth account **APPROVED**: brief targets `Search | Lake Worth Accident Exams | Manual CPC`; raw artifacts narrow correctly; report header renders Campaign Focus callout beside Geographic Focus

## Task Commits

Each task committed atomically:

1. **Task 1: SKILL.md Step 3/4 trigger + template wiring** — `bfaa97f` (feat)
2. **Task 2: references/phase8-account-data.md Step 33 contract + downstream-inheritance block + anti-patterns** — `23eb1f3` (docs)
3. **Task 3: Live e2e operator-eyes verification on Lake Worth account** — APPROVED (no code commit; REQUIREMENTS.md CAMP-03 + CAMP-04 marked complete in `146b6f6`)

**Plan metadata commit:** (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md sync) — final commit at end of executor

## Files Modified

- `.claude/skills/google-ad-research/SKILL.md` — Step 3 row + Step 4 template line (497/500 lines after edit)
- `.claude/skills/google-ad-research/references/phase8-account-data.md` — Step 33 `--campaign-filter` contract + CAMP-04 graceful-degrade doc + Phase 15 downstream-contract block + 2 anti-pattern entries
- `.planning/REQUIREMENTS.md` — CAMP-03 + CAMP-04 marked complete (CAMP-06 already complete from Plan 15-00 RED scaffolding flipping GREEN through 15-01 / 15-02)

## Live E2E Verification Evidence

Run folder: `.runs/2026-05-15T153121Z-car-accident-injury-care-services/`

Brief: `Campaign focus: Search | Lake Worth Accident Exams | Manual CPC` in `## Optional` block

Outcomes verified against ROADMAP Phase 15 success criteria:

1. **`raw/google-ads-perf.json`** — 1 unique campaign (focus only); down from 30+ account-wide campaigns. ✓ SC-1
2. **`raw/google-ads-perf.json` ad groups** — 3 ad groups (all inside focus campaign); down from 35+ account-wide AGs. ✓ SC-3
3. **`raw/google-ads-keywords.json`** — 47 items, every entry's `campaign_name` equals the focus name. ✓ SC-1
4. **`report.json`** top-level `"campaign_focus": ["Search | Lake Worth Accident Exams | Manual CPC"]`. ✓ SC-1
5. **`report.md`** `## Campaign Focus` section renders correctly beside `## Geographic Focus` (Palm Beach County, Lake Worth) callout. ✓ SC-1 + SC-5 backward-compat geo preserved alongside campaign narrowing.
6. **Positives Sync / Negatives Sync stats** reflect the narrowed campaign (no inflation from unrelated Hybrid / Palm Springs / FL PIP campaigns). ✓ SC-2
7. **Ad Group Mapping section** shows only the 3 focus-campaign AGs. ✓ SC-3
8. **Backward compat (CAMP-04)** — re-running an existing pre-v1.5 brief (no `Campaign focus:` line) confirms account-wide v1.4 behavior preserved end-to-end. ✓ SC-4

All 5 ROADMAP Phase 15 success criteria verified on real-account live data. Operator approved closeout.

## Decisions Made

- **Step 33 detailed contract in references/ not SKILL.md:** Trigger row + template line are non-negotiable for SKILL.md (operator-facing), but the full `--campaign-filter` invocation contract + CAMP-04 backward-compat narrative + single-quote escape rule live in `references/phase8-account-data.md` (loaded on demand). SKILL.md stays at 497/500 lines, well under cap.
- **Pipe-list parsing rule explicit in docs:** ` | ` (space-pipe-space) is a Google-Ads naming convention; `|` (bare) is the list separator. Documented to prevent the silent failure mode where `'|A|B|C|'` produces empty-name list entries that filter out, turning a multi-campaign filter into account-wide.
- **Anti-pattern flagged:** Don't post-filter raw artifacts after account-wide fetch — re-run `perf_fetch.py` with `--campaign-filter`. Google Ads API quota is free; re-fetch costs nothing and preserves clean separation between raw narrowing and synth layer.

## Deviations from Plan

None - plan executed exactly as written.

Task 1 correctly limited SKILL.md edits to Step 3 + Step 4 (Step 33 detail belonged to references/ per existing file layout). Task 2 landed Step 33 contract + downstream-inheritance block + anti-patterns as planned. Task 3 live e2e produced exactly the artifacts the plan predicted (47 narrowed keywords, 1 campaign, 3 AGs).

**Total deviations:** 0 auto-fixed
**Impact on plan:** Plan was tightly scoped; both code-changing tasks landed atomically without scope creep or rework.

## Issues Encountered

None. The Phase 11 architectural mirror gave Plan 15-03 a proven template — same shape, different field, different script. Live e2e ran first-try against real OAuth account with no GAQL errors, no SKILL.md narration glitches, and no campaign-name typo edge cases triggered.

## User Setup Required

None - no new external service configuration required. Reuses existing Google Ads OAuth from Phase 8.

## Phase 15 Closeout

**All 6 CAMP requirements Complete:**

| Req | Plan | Status |
|---|---|---|
| CAMP-01 | 15-02 | Complete (`_parse_brief_fields[campaign_focus]`) |
| CAMP-02 | 15-01 | Complete (`perf_fetch.py --campaign-filter` + 4-query threading) |
| CAMP-03 | 15-03 | Complete (SKILL.md Step 3/4 + references Step 33 auto-pass) |
| CAMP-04 | 15-03 | Complete (graceful-degrade contract documented + live verified) |
| CAMP-05 | 15-02 | Complete (`render_campaign_focus_section` + report.json key + typo warning) |
| CAMP-06 | 15-00 | Complete (RED test scaffolding for perf_fetch + render_report) |

**Phase 15 status:** Ready for gsd-verifier verification gate, then `phase complete` orchestrator action.

## Next Phase Readiness

- **Phase 16 (AG Token-Bag Enrichment) unblocked.** Phase 16 must calibrate against the narrowed dataset Phase 15 produces — running token-bag enrichment against full-account data inflates denominators with out-of-scope AGs. With Lake Worth now narrowing from 35+ AGs to 3, Phase 16's threshold calibration (likely 0.5 high / 0.25 medium) has a clean comparison surface.
- **No blockers carried forward.** Plan 15-03 was the last code-changing plan in Phase 15; Wave 3 closeout is now complete.
- **Operator UX loop closed.** Pasting `Campaign focus:` into the brief is the entire opt-in — no CLI memorization, no per-script reasoning, no manual flag passing. Mirrors `Geo focus:` from Phase 11 exactly.

## Self-Check: PASSED

- FOUND: .planning/phases/15-campaign-focus/15-03-SUMMARY.md
- FOUND: .claude/skills/google-ad-research/SKILL.md (modified, 497/500 lines)
- FOUND: .claude/skills/google-ad-research/references/phase8-account-data.md (modified)
- FOUND: commit bfaa97f (Task 1: SKILL.md Step 3/4)
- FOUND: commit 23eb1f3 (Task 2: references/phase8-account-data.md)
- FOUND: commit 146b6f6 (REQUIREMENTS.md CAMP-03 + CAMP-04 mark-complete)

---
*Phase: 15-campaign-focus*
*Plan: 03 — SKILL.md + references wiring*
*Completed: 2026-05-15*
