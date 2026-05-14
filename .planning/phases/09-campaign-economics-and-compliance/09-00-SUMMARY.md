---
phase: 09-campaign-economics-and-compliance
plan: 00
status: complete
completed: 2026-05-14
self_check: PASSED
---

# Plan 09-00 — Summary

## Objective

Stand up Wave 0 test scaffolding for Phase 9: three RED pytest files w/
MODULE_MISSING guards, six fixtures, and operator-editable
`compliance-verticals.json` reference data. Unblocks Wave 2 parallel
implementations (09-01 bid_suggest, 09-02 forecast_budget, 09-03 compliance_check).

## What Shipped

| Artifact | Path | Purpose |
|---------|------|---------|
| Test stubs (RED) | `tests/test_bid_suggest.py` | 13 stubs: intent multipliers, cluster-median fallback, null+flag, BIDS-04 config invariant |
| Test stubs (RED) | `tests/test_forecast_budget.py` | 10 stubs: CTR anchors, max-CPC × 0.65, low/mid/high band math, schema, methodology |
| Test stubs (RED) | `tests/test_compliance_check.py` | 10 stubs: word-boundary regex, brief+top-N scan, JSON load, neutral baseline, empty array |
| Fixture | `tests/fixtures/ranked_with_cpc.json` | All rows have `cpc_micros` populated |
| Fixture | `tests/fixtures/ranked_no_cpc.json` | All rows have `cpc_micros=null` (forces fallback) |
| Fixture | `tests/fixtures/ranked_partial_cpc.json` | Mix — exercises cluster-median pool |
| Fixture | `tests/fixtures/clusters_phase9.json` | Cluster groupings for median grouping |
| Fixture | `tests/fixtures/brief_medical.md` | Triggers medical vertical match |
| Fixture | `tests/fixtures/brief_neutral.md` | No regulated tokens — baseline |
| Reference data | `references/compliance-verticals.json` | 5 verticals (medical/legal/finance/gambling/crypto) w/ tokens + verification_url + policy_note |

## Verification

- `pytest --collect-only` → 33 tests collected, no import errors ✓
- `pytest` → 33 skipped (MODULE_MISSING guards firing as designed — RED state pre-Wave-2) ✓
- All 10 files exist on disk ✓
- 2 atomic commits: `192f49a` (tests), `7150977` (fixtures + reference) ✓

## Requirements Coverage

All 13 in-scope reqs have at least one stub test:
- BIDS-01..04: bid_suggest tests
- FRCS-01..05: forecast_budget tests
- CMPL-01..04: compliance_check tests

## Self-Check: PASSED

Tests collect cleanly. MODULE_MISSING pattern matches Phases 2-8.
Wave 2 plans (09-01, 09-02, 09-03) can spawn in parallel — independent
inputs, no cross-file conflicts.

## Notes

- Original spawned executor (`aa94e968b05630cac`) hit API socket failure
  after committing both tasks. Orchestrator inspected disk state, confirmed
  all 10 files written + 2 commits landed, and closed plan manually.
- No production code introduced. Wave 2 plans implement scripts; tests
  flip GREEN as MODULE_MISSING guards lift.
