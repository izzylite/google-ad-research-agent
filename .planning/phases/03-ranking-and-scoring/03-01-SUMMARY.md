---
phase: 03-ranking-and-scoring
plan: "01"
subsystem: ranking
tags: [python, stdlib, scoring, keywords, intent, match_type, ranked_json]

# Dependency graph
requires:
  - phase: 03-00
    provides: test stubs (test_rank_keywords.py, fixtures/keywords_phase2.json, fixtures/intent_labels.json) — RED stubs waiting for implementation
  - phase: 02-signal-collection
    provides: keywords.json schema (canonical, lemma_hash, signal_count, source_diversity, sources[])
provides:
  - rank_keywords.py: deterministic scorer that joins keywords.json + intent-labels.json → ranked.json
  - compute_score(): source_diversity*100 + intent_weight + signal_count formula
  - validate_labels(): rejects invalid intent/match_type values with ValueError
  - build_ranked(): sorts on (-score, -signal_count, keyword asc)
  - CLI --run-dir contract with exit 3 on any fatal
affects: [04-clustering, 06-report-assembly]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PEP 723 inline metadata (# /// script block) — stdlib-only, no deps"
    - "match_type passthrough: rank_keywords.py reads it from intent-labels.json (set by skill prompt), does not recalculate"
    - "Deterministic sort: (-score, -signal_count, keyword asc) — same inputs always produce same ranked.json"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/rank_keywords.py
  modified: []

key-decisions:
  - "match_type comes from intent-labels.json (written by skill prompt Step 11), not recomputed by rank_keywords.py — locked architecture from 03-RESEARCH.md Pattern 1"
  - "validate_labels rejects broad as well as phrase/exact so test coverage is complete — broad is valid in labels, never auto-assigned by script"

patterns-established:
  - "Pattern: rank_keywords.py reads match_type from intent-labels.json passthrough — do not add match_type heuristic logic to rank_keywords.py in future iterations without updating RESEARCH.md"

requirements-completed: [RANK-02, RANK-03, RANK-04]

# Metrics
duration: 1min
completed: 2026-05-08
---

# Phase 03 Plan 01: rank_keywords.py Summary

**Deterministic composite scorer: source_diversity*100 + intent_weight + signal_count formula joining keywords.json + intent-labels.json into ranked.json with 8-column canonical schema**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-05-08T05:15:07Z
- **Completed:** 2026-05-08T05:16:16Z
- **Tasks:** 1
- **Files modified:** 1 created

## Accomplishments

- Implemented `rank_keywords.py` with stdlib-only PEP 723 metadata — zero new dependencies
- All 16 `test_rank_keywords.py` tests turn GREEN (were SKIP/RED before this plan)
- Full test suite passes: 34 passed, 23 skipped (pre-existing network test skips), 0 failures
- CLI smoke test confirms exit 3 with clear error message on missing run directory

## Task Commits

1. **Task 1: Implement rank_keywords.py (RED → GREEN)** - `c5b25ff` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/rank_keywords.py` - Deterministic scorer: compute_score, validate_labels, build_ranked, CLI main; 148 lines

## Decisions Made

- match_type is read from intent-labels.json and passed through unchanged — rank_keywords.py does NOT apply the match_type heuristic from RESEARCH.md. The heuristic in RESEARCH.md is documented for the skill prompt (Step 11) to use when writing intent-labels.json. This is the locked architecture (Pattern 1). rank_keywords.py only validates that match_type is one of {phrase, exact, broad}.
- validate_labels accepts "broad" as a valid match_type (passes validation) even though broad is never auto-assigned. This is correct: if an operator manually sets broad in intent-labels.json, it should pass through without error.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. The code examples in 03-RESEARCH.md provided an exact implementation blueprint. The test fixtures in keywords_phase2.json and intent_labels.json were already written and matched the expected function signatures precisely.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `rank_keywords.py` is ready for Phase 4 (clustering) to consume `ranked.json`
- All RANK-02, RANK-03, RANK-04 requirements satisfied
- Phase 3 complete: both plans (03-00 and 03-01) done
- Next: Phase 4 — keyword clustering (reads ranked.json, fills theme field)

---
*Phase: 03-ranking-and-scoring*
*Completed: 2026-05-08*
