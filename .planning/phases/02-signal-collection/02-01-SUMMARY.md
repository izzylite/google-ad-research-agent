---
phase: 02-signal-collection
plan: "01"
subsystem: http-client, canonicalization
tags: [httpx, httpx-retries, inflect, respx, RetryTransport, lemmatization, token-sort-hash]

# Dependency graph
requires:
  - phase: 02-signal-collection/02-00
    provides: RED test stubs (test_lib_http.py, test_lib_canon.py) and fixture infrastructure
provides:
  - lib/http.py — build_client() factory with httpx-retries RetryTransport (retries 429/500/502/503/504, not 401)
  - lib/canon.py — canonicalise(keyword) -> (canonical_form, lemma_hash) using inflect singularization + token-sort SHA-256[:16]
affects:
  - 02-02-signal-collection (serp_fetch.py imports build_client)
  - 02-03-signal-collection (tavily_extract.py imports build_client)
  - 02-04-signal-collection (merge_signals.py imports canonicalise)

# Tech tracking
tech-stack:
  added:
    - httpx-retries 0.5+ (RetryTransport, Retry — transport-layer backoff for httpx)
    - inflect 7.5+ (singular_noun for English noun-phrase lemmatization, pure-Python, zero downloads)
    - respx 0.22+ (httpx-native mock — used in test_lib_http.py)
  patterns:
    - "RetryTransport factory: build_client() returns a pre-configured httpx.Client; callers own the context-manager lifecycle"
    - "Module-level inflect engine: _INF = inflect.engine() instantiated once at import time, not per call"
    - "Token-sort hash: sorted-lemmas SHA-256[:16] for non-question keywords; preserve-order for question-prefix keywords"
    - "Question-prefix guard: if tokens[0] in _QUESTION_PREFIXES: preserve word order before hashing"

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/lib/http.py
    - .claude/skills/google-ad-research/scripts/lib/canon.py
  modified:
    - .claude/skills/google-ad-research/scripts/tests/test_lib_http.py (RED stubs -> GREEN tests)
    - .claude/skills/google-ad-research/scripts/tests/test_lib_canon.py (RED stubs -> GREEN tests)

key-decisions:
  - "RetryTransport status_forcelist=[429,500,502,503,504] — 401 excluded deliberately (auth failures are fatal, not transient)"
  - "inflect.singular_noun returns False if already singular — use `sing if sing else token` pattern, not truthiness on the string"
  - "canonical_form is the lowercased + punctuation-stripped original (not the sorted lemma form) — merge_signals.py picks shortest surface per hash group for display"
  - "respx.mock decorator (not context-manager) used for test_lib_http.py — cleaner for simple route-per-test pattern"

patterns-established:
  - "RetryTransport factory pattern: build_client() owns retry config; callers get a ready-to-use httpx.Client"
  - "Module-level NLP engine: _INF = inflect.engine() at module scope (not per-call) to avoid re-instantiation overhead"
  - "Question-prefix detection: first-token set lookup determines sort vs preserve-order branch"

requirements-completed: [SIGL-06]

# Metrics
duration: 12min
completed: 2026-05-08
---

# Phase 02 Plan 01: lib/http.py + lib/canon.py Summary

**httpx RetryTransport factory and inflect-based token-sort canonicaliser — both library modules implemented, 7/7 tests flipped RED to GREEN**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-08T05:00:00Z
- **Completed:** 2026-05-08T05:12:00Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 test files rewritten)

## Accomplishments
- `lib/http.py` delivers `build_client()` using `httpx-retries` `RetryTransport` — retries 429/500/502/503/504 up to 3 times with `backoff_factor=1.0`; 401 is intentionally excluded (auth failures are fatal, not transient)
- `lib/canon.py` delivers `canonicalise(keyword) -> (canonical_form, lemma_hash)` — inflect singularization + alphabetical token-sort for non-question keywords, preserve-order for question-prefixed keywords, SHA-256[:16] hash
- Full suite passes: 25 tests passed, 16 skipped (planned Wave 2 stubs); no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: lib/http.py + test_lib_http.py GREEN** - `38da7a9` (feat)
2. **Task 2: lib/canon.py + test_lib_canon.py GREEN** - `676c320` (feat)

## Files Created/Modified
- `.claude/skills/google-ad-research/scripts/lib/http.py` — `build_client()` factory using httpx-retries RetryTransport; pure factory, no logging
- `.claude/skills/google-ad-research/scripts/lib/canon.py` — `canonicalise()` with inflect singularization, question-prefix guard, token-sort SHA-256 hash
- `.claude/skills/google-ad-research/scripts/tests/test_lib_http.py` — RED stubs replaced with 3 respx-mocked tests (retry_on_429, no_retry_on_401, success_path)
- `.claude/skills/google-ad-research/scripts/tests/test_lib_canon.py` — RED stubs replaced with 4 behavioural tests (grocery variants merge, question order preserved, empty raises, token-sort stability)

## Decisions Made
- `status_forcelist` excludes 401 — aligns with plan truths: "auth failures are fatal, not transient"; confirmed by test_no_retry_on_401
- `inflect.singular_noun` returns `False` (not empty string) when already singular — using `sing if sing else token` (not `sing or token`) avoids treating the word "False" as a result
- `canonical_form` returns the lowercased + punctuation-stripped input surface form, not the sorted lemma string — preserves display intent; merge_signals.py picks shortest-per-hash-group as display name
- `respx.mock` decorator pattern used for test isolation; no shared route state between tests

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Both modules are pure libraries; no API keys or env vars needed.

## Next Phase Readiness
- `lib/http.py` is ready for import by `serp_fetch.py` (02-02) and `tavily_extract.py` (02-03)
- `lib/canon.py` is ready for import by `merge_signals.py` (02-04)
- Both modules pass isolation tests; no fixture or conftest dependencies required at import time
- Wave 2 can proceed in parallel: 02-02 and 02-03 are independent of each other

---
*Phase: 02-signal-collection*
*Completed: 2026-05-08*
