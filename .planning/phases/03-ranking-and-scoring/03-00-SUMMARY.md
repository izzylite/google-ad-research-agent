---
phase: 03-ranking-and-scoring
plan: "00"
subsystem: testing
tags: [pytest, tdd, red-tests, fixtures, json, rank_keywords]

# Dependency graph
requires:
  - phase: 02-signal-collection
    provides: keywords.json schema (canonical, lemma_hash, signal_count, source_diversity, sources[])
provides:
  - RED test stubs for rank_keywords.py (16 tests, all skipped until Wave 1)
  - keywords_phase2.json fixture (5 rows, diversity 1-4, all source types)
  - intent_labels.json fixture (5 rows, all 4 intent classes represented)
affects:
  - 03-01 (Wave 1 rank_keywords.py implementation — must pass all 16 tests)
  - 03-02 (SKILL.md Step 11-13 update — test contract pre-established)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - MODULE_MISSING guard pattern (try/except ImportError + pytest.skip) for RED wave stubs

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/tests/test_rank_keywords.py
    - .claude/skills/google-ad-research/scripts/tests/fixtures/keywords_phase2.json
    - .claude/skills/google-ad-research/scripts/tests/fixtures/intent_labels.json
  modified: []

key-decisions:
  - "MODULE_MISSING guard (try/except ImportError + pytest.skip) chosen for RED stubs — matches Phase 2 pattern; keeps collection clean without xfail noise"
  - "ocado website stays navigational/phrase (diversity 1) in fixtures; fabricated ocado login (diversity 3) inline in test_match_type_exact_navigational to cover exact-navigational branch"
  - "intent_labels.json uses two commercial entries (best grocery delivery uk + grocery delivery service) — matches rubric anchor examples and covers diversity-2 commercial case"

patterns-established:
  - "Wave 0 RED pattern: MODULE_MISSING guard at file top, pytest.skip() as first line in each test body"
  - "Inline fabrication for edge-case fixtures: when fixture doesn't cover a branch, create minimal inline dict rather than adding new fixture file"

requirements-completed: []

# Metrics
duration: 6min
completed: 2026-05-08
---

# Phase 3 Plan 00: Ranking and Scoring Wave 0 Summary

**16 RED test stubs for rank_keywords.py with pytest MODULE_MISSING skip pattern and realistic 5-row fixtures covering all 4 intent classes and source_diversity 1-4**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-08T05:11:37Z
- **Completed:** 2026-05-08T05:17:41Z
- **Tasks:** 2/2
- **Files modified:** 3 created

## Accomplishments

- keywords_phase2.json fixture with 5 rows matching merge_signals.py schema exactly (diversity values 1, 2, 3, 4 all represented)
- intent_labels.json fixture with all 4 intent classes (transactional, commercial x2, informational, navigational) and matching lemma_hashes
- test_rank_keywords.py with 16 test functions covering RANK-01 through RANK-04; all 16 collect and skip cleanly (0 errors) before rank_keywords.py exists
- Full suite: 41 passed, 16 skipped — no regressions introduced

## Task Commits

Each task was committed atomically:

1. **Task 1: keywords_phase2.json + intent_labels.json fixtures** - `26a2bde` (chore)
2. **Task 2: test_rank_keywords.py RED stubs** - `f1fc7e8` (test)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/tests/fixtures/keywords_phase2.json` — 5-row keywords fixture matching merge_signals.py output schema; source_diversity 1-4 fully covered
- `.claude/skills/google-ad-research/scripts/tests/fixtures/intent_labels.json` — 5 matching intent labels; all 4 classes (transactional/commercial/informational/navigational) present; lemma_hashes match exactly
- `.claude/skills/google-ad-research/scripts/tests/test_rank_keywords.py` — 16 RED test stubs; MODULE_MISSING guard; covers compute_score, validate_labels, build_ranked, schema, match_type, deterministic output

## Decisions Made

- MODULE_MISSING guard (try/except ImportError + pytest.skip) chosen over xfail — consistent with Phase 2 decision; skip is explicit RED signal, xfail would obscure the GREEN transition.
- Fabricated inline `ocado login` row in `test_match_type_exact_navigational` rather than adding a 6th row to fixtures — the existing `ocado website` is diversity=1 (phrase), so exact-navigational branch requires diversity>=3; inline fabrication avoids fixture bloat.
- Two commercial entries in intent_labels.json intentional — covers both diversity-3 (`best grocery delivery uk`) and diversity-2 (`grocery delivery service`) commercial cases; `test_match_type_phrase_default` asserts both are phrase.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 1 (Plan 03-01) can now implement rank_keywords.py against a locked test contract
- All 16 tests will transition from SKIPPED to RED (ImportError removed) → GREEN as implementation passes each assertion
- Fixtures cover the full scoring matrix; no additional fixture work needed for Wave 1
- No blockers.

---
*Phase: 03-ranking-and-scoring*
*Completed: 2026-05-08*
