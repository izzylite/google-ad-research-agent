---
phase: 09-campaign-economics-and-compliance
plan: 02
subsystem: forecast_budget
tags: [forecast, economics, micros, stdlib, sidecar]
status: complete
completed: 2026-05-14
self_check: PASSED
requires:
  - ranked-enriched.json (Phase 8 + Phase 9 plan 01 — must carry suggested_max_cpc_micros)
  - clusters.json (Phase 4 output)
provides:
  - forecast_budget.py CLI
  - INTENT_CTRS / AVG_CPC_RATIO / BAND_MULTIPLIERS exports
  - compute_cluster_forecast / build_forecast / main_with_args
  - forecast.json sidecar in run_dir
affects:
  - new sidecar artifact at {run_dir}/forecast.json
  - no mutation of ranked-enriched.json or clusters.json
tech_stack:
  added: []
  patterns:
    - module-level config block + frozenset assertion (mirrors BIDS-04 pattern)
    - atomic-ish writeback via .tmp + rename
    - argv[0]-skip heuristic for full-sys.argv or args-only callers
    - methodology block mirroring constants — single source of truth for FRCS-05 disclaimer
key_files:
  created:
    - .claude/skills/google-ad-research/scripts/forecast_budget.py
    - .planning/phases/09-campaign-economics-and-compliance/09-02-SUMMARY.md
  modified: []
decisions:
  - "INTENT_CTRS frozenset assertion at import time (mirrors INTENT_MULTIPLIERS pattern from 09-01) — fails fast on typo / drift, not at runtime"
  - "campaign_totals aggregated by SUM of per-cluster fields, not recomputed from raw rows (Pitfall 5) — keeps cluster-level and campaign-level skip-rules consistent"
  - "daily_clicks_mid kept as raw float in per-cluster output (not rounded to int) so tests can use pytest.approx(6.0, rel=0.01); int rounding only applied to low/high bands where exact integer presentation matters for stdout summary"
  - "main_with_args stub (NotImplementedError) committed in Task 1 — lifts MODULE_MISSING guard immediately; full CLI lands in Task 2 commit, preserving atomic per-task discipline (same pattern used in 09-01)"
  - "Methodology notes string (_METHODOLOGY_NOTES) declared once at module top — methodology.notes in forecast.json reads from it, so editing the disclaimer in one place propagates to every render (FRCS-05 single-source-of-truth contract)"
metrics:
  duration_minutes: 3
  tasks_completed: 2
  files_created: 1
  lines_of_code: 372
  commits:
    - f935ded
    - a253755
---

# Phase 9 Plan 2: Budget Forecast (FRCS-01/02/03/05) Summary

Implemented `forecast_budget.py` — stdlib-only script that consumes `ranked-enriched.json`
(post-bid_suggest, carrying `suggested_max_cpc_micros` per row) and `clusters.json`,
emitting `{run_dir}/forecast.json` with per-cluster + campaign-level click and spend
bands plus a methodology block. Junior PPC managers can now read `campaign_totals.daily_spend_mid_usd`
to set a Day 1 budget. Phase 10's STEP-01 ("set daily budget to <mid forecast>") will
consume this field. Tuning knobs (INTENT_CTRS, AVG_CPC_RATIO, BAND_MULTIPLIERS) live in
a single config block guarded by a frozenset assertion (FRCS-02, FRCS-03). The
methodology block in forecast.json mirrors those constants verbatim — single source of
truth for the FRCS-05 disclaimer. Lifts the MODULE_MISSING guard on the 10 RED stubs
from Wave 0 (plan 09-00).

## What Shipped

| Artifact | Path | Purpose |
|----------|------|---------|
| New script | `.claude/skills/google-ad-research/scripts/forecast_budget.py` | 372 lines, stdlib-only, PEP 723 header |
| New sidecar contract | `{run_dir}/forecast.json` | metadata + methodology + clusters[] + campaign_totals; junior PPC budget guidance |

## Tuning Constants (FRCS-02, FRCS-03)

```python
INTENT_CTRS: dict[str, float] = {
    "transactional": 0.06,
    "commercial":    0.04,
    "informational": 0.02,
    "navigational":  0.08,
}

AVG_CPC_RATIO: float = 0.65          # avg_cpc = suggested_max_cpc × this

BAND_MULTIPLIERS: dict[str, float] = {"low": 0.5, "mid": 1.0, "high": 1.5}
```

The methodology block in `forecast.json` reads from these dicts directly — `dict(INTENT_CTRS)`, `AVG_CPC_RATIO`, `dict(BAND_MULTIPLIERS)`. Editing one block updates both the math and the disclaimer (FRCS-05 single-source contract).

## Function Signatures Committed

```python
def compute_cluster_forecast(
    cluster: dict,
    ranked_index: dict[str, dict],
) -> dict: ...

def build_forecast(
    ranked_enriched: list[dict],
    clusters_data: dict,
    run_id: str,
) -> dict: ...

def main_with_args(argv: list[str]) -> int: ...
```

## Sample Output (smoke test with fixtures + synthesized suggested_max_cpc_micros)

Smoke command:

```bash
# ranked-enriched.json: tests/fixtures/ranked_with_cpc.json with
# suggested_max_cpc_micros = cpc_micros × 1.2 (transactional-style multiplier
# applied uniformly to all 12 rows for the smoke test).
# clusters.json: tests/fixtures/clusters_phase9.json (4 clusters + 1 orphan).
python forecast_budget.py --run-dir <tmp>
```

Stdout summary:

```json
{"clusters_forecast": 4, "keywords_in_forecast": 12, "daily_spend_mid_usd": 7.12, "unjoined_keywords": 0}
```

First cluster (high-intent same-day delivery) sample from on-disk forecast.json:

```json
{
  "name": "same_day_delivery_transactional",
  "intent": "transactional",
  "keyword_count": 3,
  "keywords_with_volume": 3,
  "total_monthly_volume": 9200,
  "daily_clicks_low": 9,
  "daily_clicks_mid": 18.4,
  "daily_clicks_high": 28,
  "daily_spend_low_usd": 2.89,
  "daily_spend_mid_usd": 5.78,
  "daily_spend_high_usd": 8.67,
  "monthly_spend_mid_usd": 173.4
}
```

Sanity check (per-cluster math):

- Sum of volumes: 2400 + 1800 + 5000 = 9200 ✓
- Monthly clicks: 9200 × 0.06 = 552 → daily 552/30 = **18.4** ✓
- avg_cpc_micros (per kw, weighted): (320k×1.2)×0.65 = 249,600 micros = $0.2496 (etc.) — daily spend lands at $5.78 (sane, sub-$10/day for a small fixture). NOT 5.78M (Pitfall 8 cleared).
- Bands: 5.78 × 0.5 = 2.89 ✓ ; 5.78 × 1.5 = 8.67 ✓
- Monthly: 5.78 × 30 = 173.4 ✓

Campaign totals (aggregate of all 4 clusters): `{"cluster_count": 4, "keyword_count": 12, "daily_clicks_mid": 35.5, "daily_spend_mid_usd": 7.12, "monthly_spend_mid_usd": 213.6, "unjoined_keywords": 0}` — verified as SUM of per-cluster values, not a recomputation (Pitfall 5 cleared).

## Test Results — BEFORE / AFTER

| File | Before (plan 09-01 end) | After (this plan) |
|------|--------------------------|-------------------|
| `test_forecast_budget.py` | 10 SKIPPED (MODULE_MISSING) | **10 PASSED** |
| `test_bid_suggest.py` | 13 PASSED | 13 PASSED |
| `test_compliance_check.py` | 10 SKIPPED | 10 SKIPPED (plan 09-03 owns) |
| Full suite | 111 passed, 30 skipped | **121 passed, 20 skipped** |

Phase 1-8 + 09-01 regression: 121 passed (10 ↑ from forecast_budget GREEN). No regressions introduced.

## bid_suggest → forecast_budget Contract Check

`forecast_budget.py` consumes the `suggested_max_cpc_micros` field that `bid_suggest.py` (09-01) writes into every row of `ranked-enriched.json`. The link is verified:

- `ranked_index[kw].get("suggested_max_cpc_micros")` is the sole spend-side input.
- Null-handling: rows where bid_suggest emitted `null + no_cpc_data=true` are skipped in the forecast (`continue` path) — not double-counted, not crashing.
- Micros stay in micros through the entire arithmetic; conversion to USD via `round(total_micros / 1_000_000, 2)` happens exactly once at the cluster-aggregate boundary (Pitfall 8 invariant preserved end-to-end across 09-01 and 09-02).

## Deviations from Plan

**Auto-fix Rule 2 (minor):** Like 09-01, committed a `main_with_args` stub (NotImplementedError) at Task 1's end so the MODULE_MISSING guard lifts immediately for the 9 core-function tests; full CLI lands in Task 2's commit. The plan's `<done>` for Task 1 anticipates this pattern. No scope creep.

**Decision (in scope, no rule trigger):** Kept `daily_clicks_mid` as a raw float in per-cluster output (not int-rounded). Reason: the test `test_click_estimates_use_intent_ctrs` does `assert out["daily_clicks_mid"] == pytest.approx(6.0, rel=0.01)`, which only succeeds against a float-typed value. Low/high band fields use `int(round(...))` so the stdout summary stays clean ("9, 18.4, 28" rather than "9, 18, 28" losing precision on the mid). If a downstream consumer prefers an int mid, render_report.py (plan 09-04) can format it as needed — the underlying number is correct.

## Verification — Success Criteria

- [x] forecast_budget.py implemented (PEP 723 header, stdlib-only — `dependencies = []`)
- [x] All 10 tests in `tests/test_forecast_budget.py` PASS GREEN
- [x] `{run_dir}/forecast.json` written with per-cluster + campaign rollup (smoke confirmed)
- [x] `INTENT_CTRS` + `AVG_CPC_RATIO` + `BAND_MULTIPLIERS` in single config block (FRCS-02, FRCS-03)
- [x] frozenset assertion guards 4-class rubric at import time
- [x] Methodology block present in forecast.json — `methodology.intent_ctrs == INTENT_CTRS`, `methodology.avg_cpc_ratio == 0.65`, `methodology.band_multipliers == BAND_MULTIPLIERS`, methodology.notes references "Not Google's official forecast" (FRCS-05)
- [x] Full suite still passes: 121 passed, 20 skipped — zero v1.0 regressions
- [x] No magic numbers scattered (grep verified: only docstring + INTENT_CTRS + AVG_CPC_RATIO + a comment explaining a test case)
- [x] Cluster join via lower+strip works ("Same-Day Delivery" → "same-day delivery") — `test_cluster_join_lowercase_strip` PASS
- [x] Each task committed individually (`f935ded` core, `a253755` CLI)

## Authentication Gates

None — pure stdlib compute on local JSON. No API calls, no `.env` reads.

## Requirements Coverage

- **FRCS-01** ✓ — `forecast.json` emitted with per-cluster + campaign-level click + spend bands.
- **FRCS-02** ✓ — `INTENT_CTRS` module-level dict with frozenset assertion; click math reads `INTENT_CTRS.get(intent, 0.0)`.
- **FRCS-03** ✓ — `AVG_CPC_RATIO = 0.65` and `BAND_MULTIPLIERS = {"low": 0.5, "mid": 1.0, "high": 1.5}` both in the single config block; applied at cluster aggregate (not per-keyword).
- **FRCS-05** ✓ — `methodology` block mirrors module constants exactly; `_METHODOLOGY_NOTES` declared once at module top; FRCS-05 disclaimer in plan 09-04's report will pull from `forecast.json` methodology (single source of truth).
- **FRCS-04** (Budget Forecast section in report.md/html) — intentionally out of scope; lands in plan 09-04 (render_report extension).

## Notes

- Phase 9 plan 09-03 (compliance_check) remains unblocked and untouched by this plan; its tests are still SKIPPED via MODULE_MISSING. Wave 2 can spawn it in parallel with plan 09-04 (render_report extension) per the wave dependency graph.
- The `_build_ranked_index` helper builds a single lower+strip index from `ranked-enriched.json` in O(n); cluster compute reads from it in O(cluster_size) per cluster — total work is O(n + total_cluster_keywords), no nested loops.
- `unjoined_keywords` surfaces silent join failures (cluster keyword not present in ranked-enriched.json) — operator's smoke signal for cluster/rank drift. In the smoke run this was 0, as expected from sibling fixtures.
- The `Any` import is currently used only in the CLI's `clusters_data: dict[str, Any]` type hint — kept for type clarity; could be removed by switching to bare `dict` if linter pressure ever picks it up.

## Self-Check: PASSED

- forecast_budget.py exists: FOUND ✓ (`.claude/skills/google-ad-research/scripts/forecast_budget.py`)
- commit f935ded exists: FOUND ✓
- commit a253755 exists: FOUND ✓
- 10/10 forecast_budget tests GREEN ✓
- 121 passed in full suite (no v1.0 + no 09-01 regression) ✓
- methodology.intent_ctrs equals INTENT_CTRS in forecast.json (asserted by `test_methodology_block_present`) ✓
