---
phase: 11-account-structure-mapping
plan: 03
subsystem: export-csv + render-report integrations
tags: [phase-11, wave-2, adgm-05, adgm-06, geo-05, mapping-aware-exports, step-3-rewrite]
dependency-graph:
  requires:
    - phase: 11-00
      provides: "RED stubs (4 in test_export_csv.py for ADGM-05; 5 in test_render_report.py for GEO-05 + ADGM-06) guarded by per-function hasattr / inspect.signature checks; ad-group-mapping fixture trio (50pct/60pct/20pct); brief-with-geo-focus.md / brief-no-geo-focus.md"
    - phase: 11-01
      provides: "_parse_optional_geo_focus(brief_text) + _infer_state_code; references/us-cities.json data file (Wave-2 doesn't read it directly, but the report can surface state_code + geo_focus from brief context)"
    - phase: 11-02
      provides: "{run_dir}/ad-group-mapping.json schema (matches[].keyword + .existing_ad_group + .confidence + .score + .reason; unmapped_count; mapping_coverage_pct; computed_at; skipped_reason)"
  provides:
    - "export_csv: _load_ad_group_mapping + _resolve_ad_group_from_mapping + _existing_ad_group_names_in_mapping public-but-underscored API; mapping= kwarg on _build_positives_rows + _build_ad_groups_rows; mapping-aware stdout JSON (existing_ad_groups_used + new_ad_groups_emitted + mapping_coverage_pct)"
    - "render_report: render_geographic_focus_section + _load_ad_group_mapping_for_render; _COVERAGE_REWRITE_PCT = 50.0 module-level config; render_next_steps_section ad_group_mapping= kwarg; build_report_json geographic_focus (always) + ad_group_mapping_summary (when mapping present)"
    - "Phase 10 byte contract preserved — Unicode dashes round-trip byte-for-byte through positives.csv (Pitfall 2)"
  affects:
    - "Wave 3 plan 11-04 (SKILL.md pointer + references/phase11-account-structure-mapping.md + human-verify smoke) UNBLOCKED — Wave 2 has shipped the operator-visible artifacts the smoke test exercises"
tech-stack:
  added: []
  patterns:
    - "Backward-compat sidecar reader pattern: None on file absence + None on JSONDecodeError → caller falls back to pre-sidecar behavior (mirrors Phase 9 forecast/compliance loaders)"
    - "Strict-greater-than coverage threshold (50.0 → no rewrite; 50.1 → rewrite) — single source of truth via _COVERAGE_REWRITE_PCT constant"
    - "Counter-grouped step-3 text: descending by match count, alphabetical tie-break for stable JSON snapshot diff"
    - "Section composition order locked: Header → HOW_TO_READ → Geographic Focus (GEO-05) → Compliance Warning (CMPL-03) → Pulse / Perf / Sync / Clusters / Forecast / Negatives / Competitor / Ranked / Exports / Next Steps"
key-files:
  created:
    - .planning/phases/11-account-structure-mapping/11-03-SUMMARY.md
  modified:
    - .claude/skills/google-ad-research/scripts/export_csv.py
    - .claude/skills/google-ad-research/scripts/render_report.py
    - .claude/skills/google-ad-research/scripts/tests/test_export_csv.py
key-decisions:
  - "Mapped keywords override cluster assignment entirely (not just relabel): if a ranked keyword has high/medium mapping match, it's emitted with the existing-ad-group name even when the LLM clusterer would have orphaned it. Otherwise mapping cannot move keywords into client's existing structure — would only relabel ones we already happened to cluster."
  - "Step-3 rewrite happens BEFORE CMPL-05 compliance prepend so it always targets template index 2 (the original 'Create ad groups: ...' slot). Reversing the order would force the rewrite to chase a moving index after compliance shifts steps down."
  - "Strict `>` coverage threshold via single _COVERAGE_REWRITE_PCT constant: 50.0 exact → no rewrite (boundary preserved); 50.1 → rewrite. Open-Q 4 / Pitfall 7 resolved deterministically via one numeric literal."
  - "_parse_brief_fields geo_focus regex broadened to tolerate leading list markers (- / *) — matches both bare and bulleted brief formats and is forward-compatible with the SKILL.md prompt update in plan 11-04."
  - "build_report_json adds geographic_focus key ALWAYS (empty focus list when brief has no geo line) but ad_group_mapping_summary ONLY when the sidecar exists — geographic_focus is part of every v1.2 report; mapping summary is contextual telemetry."
  - "Counter ordering: descending count, alphabetical tie-break (sorted(..., key=lambda kv: (-kv[1], kv[0]))) — produces byte-stable step-3 text across runs so snapshot tests and committed report.md fixtures don't drift on ties."
requirements-completed: [GEO-05, ADGM-05, ADGM-06]
metrics:
  duration_min: 9
  tasks_completed: 2
  files_created: 1
  files_modified: 3
  completed_date: "2026-05-15"
---

# Phase 11 Plan 03: export_csv + render_report Mapping Integrations Summary

**Wave 2 wires the Phase 11 sidecars (ad-group-mapping.json from plan 11-02 + brief Geo focus parse from plan 11-01) into operator-visible artifacts. Two scripts modified; 9 RED stubs from plan 11-00 flip GREEN; zero regressions on the 230-test full suite (now 239/0); SKILL.md untouched (Wave 3 deliverable).**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-05-15T23:13:00Z (right after 11-02 closeout)
- **Completed:** 2026-05-15T23:22:30Z
- **Tasks:** 2 / 2 committed atomically
- **Suite delta:** 230 passed / 9 skipped → 239 passed / 0 skipped (+9 GREEN flips, -9 skipped, 0 regressions)

## Accomplishments

- **ADGM-05 (mapping-aware positives.csv):** `_resolve_ad_group_from_mapping` substitutes existing ad-group name into the `Ad Group` column when a ranked keyword matches a high/medium confidence entry in `ad-group-mapping.json`. Backward compat: mapping absent → cluster slug (pre-Phase-11 behavior preserved byte-for-byte).
- **ADGM-05 (ad_groups.csv dedup):** `_existing_ad_group_names_in_mapping` returns the set of existing-AG names; `_build_ad_groups_rows` filters cluster rows whose name appears in that set, preventing Editor "Ad group already exists" duplicate-name errors on import.
- **ADGM-05 (Unicode preservation):** "Accident Exams – Lake Worth" (U+2013 en-dash) round-trips byte-for-byte through `positives.csv` (Pitfall 2 verified).
- **GEO-05 (Geographic Focus callout):** `render_geographic_focus_section` emits `## Geographic Focus\n\n**Location:** X → **Focus:** Y` block under the header. `_parse_brief_fields` extended to populate `fields["geo_focus"]` from the optional `**Geo focus:**` brief line (tolerates leading list markers). Empty/absent → `""` (graceful degrade, no orphan heading).
- **ADGM-06 (Next Steps step-3 rewrite):** `render_next_steps_section` accepts `ad_group_mapping=` kwarg. When `mapping_coverage_pct > _COVERAGE_REWRITE_PCT` (strict `>` 50.0), step 3 rewrites from `"Create ad groups: {csv}"` to `"Add keywords to existing ad groups: <name> (<N> kw), <name> (<N> kw)."`. Counter-grouped by `existing_ad_group` over high+medium matches, ordered descending by count with alphabetical tie-break for byte-stable output.
- **Strict boundary verified:** coverage = 50.0 exact → step 3 stays at "Create ad groups: ..." (no rewrite); coverage = 60.0 → rewrite fires.
- **build_report_json:** emits `geographic_focus: {location, focus[]}` always; emits `ad_group_mapping_summary: {coverage_pct, matched_high, matched_medium, unmapped}` only when mapping sidecar exists.

## Task Commits

| Task | Commit  | Description                                                                                                                                                                                                                                                                                                                                                                                                  |
| ---- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | `8bca0f3` | feat(phase-11-03): ADGM-05 — export_csv reads ad-group-mapping.json. Three private helpers + `mapping=` kwarg on `_build_positives_rows` / `_build_ad_groups_rows` + main() threading + stdout telemetry. Also patches `_stage_mapping_run` test helper so fixtures overlap with mapping keywords (Rule-1 deviation — see below).                                                                              |
| 2    | `c8514a7` | feat(phase-11-03): GEO-05 + ADGM-06 — `_COVERAGE_REWRITE_PCT` constant, `render_geographic_focus_section`, `_load_ad_group_mapping_for_render`, `_parse_brief_fields` geo_focus extension, `render_next_steps_section` `ad_group_mapping=` kwarg with Counter-grouped step-3 rewrite, `build_report_json` `geographic_focus` + optional `ad_group_mapping_summary`, `main` wires mapping into Next Steps. |

## Files Created/Modified

- **`.claude/skills/google-ad-research/scripts/export_csv.py`** — three new private helpers (`_load_ad_group_mapping`, `_resolve_ad_group_from_mapping`, `_existing_ad_group_names_in_mapping`); `mapping=` kwarg added to both row builders; `main()` loads mapping once and threads through; stdout JSON extended with `existing_ad_groups_used` + `new_ad_groups_emitted` + `mapping_coverage_pct`.
- **`.claude/skills/google-ad-research/scripts/render_report.py`** — `_COVERAGE_REWRITE_PCT: float = 50.0` constant; `render_geographic_focus_section()`; `_load_ad_group_mapping_for_render()`; `_parse_brief_fields()` extended for geo_focus; `render_next_steps_section()` gains `ad_group_mapping=` kwarg + Counter-grouped step-3 rewrite; `render_full_report()` inserts Geographic Focus + threads mapping into Next Steps; `build_report_json()` emits `geographic_focus` always + `ad_group_mapping_summary` when present; `main()` reads mapping once for shared Next Steps computation.
- **`.claude/skills/google-ad-research/scripts/tests/test_export_csv.py`** — `_stage_mapping_run` augments ranked-enriched + clusters with mapping keywords when a mapping fixture is supplied (test-only fix; see Deviations).
- **`.planning/phases/11-account-structure-mapping/11-03-SUMMARY.md`** — this file.

## Locked Interfaces (Wave 3 reads against these)

### `export_csv` mapping API
```python
def _load_ad_group_mapping(run_dir: Path) -> dict | None: ...
def _resolve_ad_group_from_mapping(keyword: str, cluster_slug: str, mapping: dict | None) -> str: ...
def _existing_ad_group_names_in_mapping(mapping: dict | None) -> set[str]: ...
def _build_positives_rows(ranked_enriched, cluster_index, campaign, mapping: dict | None = None) -> list[dict]: ...
def _build_ad_groups_rows(clusters_data, ranked_index, campaign, mapping: dict | None = None) -> list[dict]: ...
```

### `render_report` mapping/geo API
```python
_COVERAGE_REWRITE_PCT: float = 50.0  # ADGM-06 strict > threshold
def render_geographic_focus_section(brief_fields: dict[str, str]) -> str: ...
def _load_ad_group_mapping_for_render(run_dir: Path) -> dict | None: ...
def render_next_steps_section(
    brief_fields, forecast, compliance, clusters_data,
    ad_group_mapping: dict | None = None,
) -> tuple[str, list[dict]]: ...
```

### `report.json` new keys (Wave 2)
```jsonc
{
  "geographic_focus": {"location": "Florida", "focus": ["Palm Beach County", "Lake Worth"]},
  // ad_group_mapping_summary only when sidecar present:
  "ad_group_mapping_summary": {
    "coverage_pct": 60.0,
    "matched_high": 4,
    "matched_medium": 2,
    "unmapped": 4
  }
}
```

## Pitfall Mitigations Verified

| Pitfall | Mitigation | Verified by |
|---|---|---|
| **2 — Unicode bytes through CSV** | csv.DictWriter encoding='utf-8' (no BOM) preserves U+2013 en-dash byte-for-byte; mapping lookup returns existing_ad_group string unchanged | `test_unicode_dash_preserved_in_csv` — asserts `b"\xe2\x80\x93"` in positives.csv raw bytes |
| **7 — Coverage threshold boundary** | Strict `>` via single `_COVERAGE_REWRITE_PCT = 50.0` constant; `coverage = 50.0 → no rewrite`; `coverage = 50.1 → rewrite` | `test_next_steps_no_rewrite_at_exactly_50pct` (50.0 → "Create ad groups") + `test_next_steps_rewrite_high_coverage` (60.0 → "Add keywords to existing ad groups") |
| **Editor duplicate-name error** | `_existing_ad_group_names_in_mapping` excludes existing names from `ad_groups.csv` | `test_ad_groups_csv_skips_existing` — set-intersection of output ad-group names ∩ mapping existing names == ∅ |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test fixture overlap] `_stage_mapping_run` original fixtures didn't overlap with the mapping**

- **Found during:** Task 1 first test run — `test_existing_ad_group_in_positives` asserts at least one positives.csv row carries `Ad Group == "Accident Exams – Lake Worth"`, but `ranked_enriched_phase10` contains only grocery-delivery keywords while `ad-group-mapping-60pct.json` contains accident-doctor keywords. With no overlap, every `_resolve_ad_group_from_mapping` call returns the cluster slug fallback, and the asserted existing-AG row never materializes.
- **Issue:** The Wave-0 test design assumed an overlap that didn't exist. The plan's `_resolve_ad_group_from_mapping` API is keyword-exact (case-sensitive) — only ranked keywords that literally appear in `mapping.matches[]` get the existing-AG label. With zero overlap, the test's positive assertion is structurally unachievable.
- **Fix:** Extended `_stage_mapping_run` to, when a mapping fixture is provided, append each mapping keyword to `ranked-enriched.json` (as a synthetic transactional row with `score=50`, `suggested_max_cpc_micros=300_000`) and to add a single `phase11_mapping_fallback` cluster that lists those keywords. This gives the joiner a cluster fallback for low-confidence rows (Pitfall 6 — orphans are filtered out of positives.csv) while the mapping resolver overrides the cluster slug for high/medium matches. Backward-compat test (`test_no_mapping_file_backward_compat`) passes `mapping_fixture=None` so this augmentation never fires, and the original `ranked_enriched_phase10` / `clusters_phase10` are preserved unchanged.
- **Files modified:** `.claude/skills/google-ad-research/scripts/tests/test_export_csv.py` (`_stage_mapping_run` helper only)
- **Verification:** All 4 ADGM-05 RED stubs flip GREEN; all 30 Phase 10 GREEN tests REMAIN GREEN; backward-compat test passes (positives.csv Ad Group ∈ cluster_names when mapping absent).
- **Committed in:** `8bca0f3` (Task 1 commit)

**2. [Rule 2 - Missing functional behavior] Mapped keywords needed to override cluster assignment, not just relabel**

- **Found during:** Task 1 design analysis
- **Issue:** The plan's textual behavior says "Substitute the existing ad-group name into positives.csv `Ad Group` column for high/medium matches" — but the existing `_build_positives_rows` skips any ranked keyword that doesn't map to a cluster (`if not ag: continue`). If a mapping match exists for a keyword that the LLM clusterer orphaned, naive substitution would never fire because the row was already skipped. This contradicts the spirit of ADGM-05: mapped keywords belong in the existing client ad group regardless of whether our heuristic clusterer happened to group them.
- **Fix:** Wrote `_build_positives_rows` to call `_resolve_ad_group_from_mapping(kw, cluster_slug or "", mapping)` for every ranked row. When the mapping returns an existing-AG name, that becomes the Ad Group cell and the row is emitted even when `cluster_slug` was empty. When the mapping returns the fallback (because no match exists or confidence is low), the original "skip orphans" rule applies (returns `""` → row filtered out). This preserves the Phase 10 behavior for unmapped keywords while letting mapped keywords ride into positives.csv regardless of our cluster.
- **Files modified:** `.claude/skills/google-ad-research/scripts/export_csv.py` (`_build_positives_rows` body)
- **Verification:** `test_existing_ad_group_in_positives` asserts mapped keywords appear with the existing AG name; `test_no_mapping_file_backward_compat` asserts that when mapping is absent, all output Ad Group cells are still in the cluster slug set (i.e., the previous orphan-skip rule still applies for non-mapped rows).
- **Committed in:** `8bca0f3` (Task 1 commit)

No Rule 3 or Rule 4 deviations. The plan's locked interfaces (helper names, signatures, schemas) were honored exactly as documented.

## Authentication Gates

None. Plan 11-03 is pure local file/test work — no API calls, no secrets.

## Issues Encountered

- One transient `wc -l SKILL.md` invariant check needed an explicit re-run after editing render_report.py to confirm Wave 2 didn't accidentally pull SKILL.md into scope. SKILL.md unchanged at exactly 500/500 lines (Wave 3 owns the SKILL.md update in plan 11-04).
- The plan example signature for `render_next_steps_section` showed `(brief_fields, clusters, forecast, compliance, ad_group_mapping)` but the existing function (shipped in Phase 10 plan 10-02) uses `(brief_fields, forecast, compliance, clusters_data)`. Honored the existing positional order — appending `ad_group_mapping` as a keyword-only-style trailing kwarg with default None — to preserve the Phase 10 contract. Tests that detect the kwarg via `inspect.signature` see the new parameter and unblock.

## Self-Check

Verified each artifact exists on disk and each task commit is reachable:

- [x] `.claude/skills/google-ad-research/scripts/export_csv.py` — exists, helpers exported, mapping kwarg threaded through `main()`
- [x] `.claude/skills/google-ad-research/scripts/render_report.py` — exists, `_COVERAGE_REWRITE_PCT = 50.0`, `render_geographic_focus_section` exported, `render_next_steps_section` accepts `ad_group_mapping=`
- [x] `.claude/skills/google-ad-research/scripts/tests/test_export_csv.py` — `_stage_mapping_run` augmented
- [x] Commit `8bca0f3` (Task 1: ADGM-05) — reachable
- [x] Commit `c8514a7` (Task 2: GEO-05 + ADGM-06) — reachable
- [x] Full suite (all deps loaded): 239 passed / 0 skipped / 0 errors — zero regressions from 11-02 baseline (was 230/9)
- [x] All 9 Phase 11 Wave 2 RED stubs flip GREEN (4 test_export_csv + 5 test_render_report)
- [x] SKILL.md unchanged at exactly 500/500 lines (Wave 3 owns the SKILL.md edit)
- [x] REPL sanity checks for both modules return `OK`

## Self-Check: PASSED

## Next Phase Readiness

- **Wave 3 plan 11-04 (SKILL.md pointer + references/phase11-account-structure-mapping.md + human-verify e2e smoke) UNBLOCKED.** The Wave 2 surface is in place: SKILL.md can now point operators at:
  - `--geo-focus` brief field (parsed by run_init, propagated through serp_fetch + merge_signals filters from plan 11-01)
  - `ad_group_match.py` sidecar (writes `ad-group-mapping.json` per plan 11-02)
  - `export_csv.py` mapping-aware Ad Group / ad_groups.csv dedup (this plan)
  - `render_report.py` Geographic Focus callout + Next Steps step-3 rewrite (this plan)
- **No blockers.** All ADGM-05 / GEO-05 / ADGM-06 RED stubs flipped GREEN; pitfalls 2 / 7 mitigated and test-verified; Unicode-dash round-trip + 50.0 strict boundary both exercised.

---
*Phase: 11-account-structure-mapping*
*Plan: 03*
*Completed: 2026-05-15*
