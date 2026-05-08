---
phase: 04-clustering
plan: "00"
subsystem: clustering-tests
tags: [tdd, red-stubs, fixtures, validate-clusters, wave-0]
dependency_graph:
  requires: []
  provides:
    - "9 RED test stubs for validate_clusters.py (CLST-01, CLST-02, CLST-03)"
    - "4 fixture JSON files for clustering invariant tests"
  affects:
    - ".claude/skills/google-ad-research/scripts/tests/test_validate_clusters.py"
    - ".claude/skills/google-ad-research/scripts/tests/fixtures/"
tech_stack:
  added: []
  patterns:
    - "MODULE_MISSING guard (try/except ImportError + pytest.skip) — Wave 0 RED pattern"
    - "FIXTURES_DIR = Path(__file__).parent / 'fixtures' — shared fixture loading convention"
key_files:
  created:
    - ".claude/skills/google-ad-research/scripts/tests/test_validate_clusters.py"
    - ".claude/skills/google-ad-research/scripts/tests/fixtures/ranked_phase3.json"
    - ".claude/skills/google-ad-research/scripts/tests/fixtures/clusters_valid.json"
    - ".claude/skills/google-ad-research/scripts/tests/fixtures/clusters_mixed_intent.json"
    - ".claude/skills/google-ad-research/scripts/tests/fixtures/clusters_oversize.json"
  modified: []
decisions:
  - "VC_MISSING guard (try/except ImportError + pytest.skip) for Wave 0 RED stubs — consistent with Phase 3 MODULE_MISSING pattern; keeps collection clean and makes RED-to-GREEN transition explicit when validate_clusters.py is implemented in Wave 1"
  - "test_orphans_warn uses hasattr assertion stub — orphan checking surface TBD at implementation time; placeholder keeps test collectible and skippable without binding Wave 1 to a specific API signature"
  - "clusters_oversize.json uses 4 real ranked_phase3 keywords + 22 synthetic fillers — oversize check is exercised in isolation; test_oversize_exit3 builds ranked_index covering all 26 keywords as transactional so only oversize fires"
  - "clusters_valid.json uses 4 transactional keywords (not 5) in first cluster — test_pure_intent_passes validates intent purity not size; target_undersize warning is acceptable here since the fixture's purpose is intent-purity testing"
metrics:
  duration: "~2 min"
  completed_date: "2026-05-08"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
---

# Phase 04 Plan 00: Wave 0 RED Test Stubs + Fixtures for validate_clusters.py Summary

**One-liner:** 9 pytest RED stubs with VC_MISSING skip guards + 4 JSON fixtures (ranked_phase3, clusters_valid, clusters_mixed_intent, clusters_oversize) covering all CLST-01/02/03 invariants.

## What Was Built

Two deliverables for the Wave 0 Nyquist-compliant test scaffold:

**1. `tests/fixtures/` — 4 JSON fixture files**

| File | Purpose | Keywords |
|------|---------|----------|
| `ranked_phase3.json` | 8-row ranked.json shape (4 transactional, 3 commercial, 1 informational) | 8 |
| `clusters_valid.json` | 2 pure-intent clusters (transactional + commercial), 0 orphans | 7 |
| `clusters_mixed_intent.json` | 1 cluster mixing transactional + commercial (mixed_intent trigger) | 4 |
| `clusters_oversize.json` | 1 cluster with 26 keywords (4 real + 22 synthetic fillers, oversize trigger) | 26 |

**2. `tests/test_validate_clusters.py` — 9 RED stub test functions**

| Test | Requirement | Invariant |
|------|-------------|-----------|
| `test_pure_intent_passes` | CLST-01 | Pure-intent cluster → no mixed_intent violation |
| `test_mixed_intent_exit3` | CLST-01 | Mixed transactional+commercial → mixed_intent hard violation |
| `test_target_size_valid` | CLST-02 | 7-keyword cluster → no size violations |
| `test_undersize_warns` | CLST-02 | 2-keyword cluster → undersize warning, no hard violations |
| `test_oversize_exit3` | CLST-02 | 26-keyword cluster → oversize hard violation |
| `test_valid_name` | CLST-02/03 | `same_day_delivery_transactional` → no bad_name |
| `test_bad_name_numeric` | CLST-03 | `cluster_3_informational` → bad_name hard violation |
| `test_duplicate_keyword_exit3` | CLST-03 | Same keyword in 2 clusters → duplicate_keyword hard violation |
| `test_orphans_warn` | CLST-03 | Orphan stub — hasattr check keeps test collectible |

## Verification Results

```
pytest --collect-only: 9 tests collected
pytest -v: 9 skipped in 0.02s, 0 errors, 0 failures
```

All tests skip with reason "validate_clusters not yet implemented" — exactly the Wave 0 expected state.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 8a98b6c | chore(04-00): add 4 fixture JSON files for validate_clusters tests |
| Task 2 | 75bd5cd | test(04-00): add RED test stubs for validate_clusters.py — 9 tests, all skipped |

## Self-Check: PASSED

All 5 created files confirmed on disk. Both task commits (8a98b6c, 75bd5cd) confirmed in git log.
