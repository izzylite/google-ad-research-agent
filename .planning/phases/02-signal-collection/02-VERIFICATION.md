---
phase: 02-signal-collection
verified: 2026-05-08T13:00:00Z
status: passed
score: 5/5 must-haves verified
gaps: []
human_verification:
  - test: "Run SKILL.md Steps 6-10 end-to-end with real API keys"
    expected: "raw/websearch-baseline.json, raw/serper.json, raw/tavily-*.json, and keywords.json all exist in run folder; Phase 2 summary printed at Step 10"
    why_human: "Requires live SERPER_API_KEY and TAVILY_API_KEY; WebSearch is LLM-invoked from the skill prompt and cannot be mocked in unit tests"
---

# Phase 2: Signal Collection Verification Report

**Phase Goal:** All three signal sources (Serper, Tavily, WebSearch) write locale-correct raw JSON to the run folder, and every emitted keyword carries source attribution and a canonicalized form.
**Verified:** 2026-05-08T13:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `serp_fetch.py` produces `raw/serper.json` with organic, PAA, related, and ads blocks; gl/hl locale params embedded in request and persisted in output | VERIFIED | `serp_fetch.py` normalise_response() uses `.get()` for all four blocks; `--gl` and `--hl` are required CLI args; `locale` dict and `searchParameters` verbatim echo written to `by_seed[]`; 6/6 tests GREEN |
| 2 | `tavily_extract.py` writes one per-domain JSON to `raw/`, capped at 5 competitors × 5 URLs each, using `extract_depth='basic'` — never `crawl` | VERIFIED | `extract_depth="basic"` hardcoded at line 110; cap enforced at `competitors[:args.max_competitors]` and `urls[:args.max_urls_per_competitor]`; only `client.extract()` called — no `crawl`; 4/4 tests GREEN |
| 3 | WebSearch is invoked from the skill prompt (not a script) and its output is written to `raw/websearch-baseline.json` via the Write tool | VERIFIED | SKILL.md Step 7 instructs WebSearch calls with locale-embedded query strings; Step 7 ends with explicit Write-tool instruction to `{run_dir}/raw/websearch-baseline.json` with the full JSON schema |
| 4 | Every keyword that survives harvest carries a non-empty `sources` array recording which source(s) surfaced it; `source_diversity` = distinct source string count | VERIFIED | `build_keywords_json()` in `merge_signals.py` computes `source_diversity = len({s["source"] for s in sources})`; `signal_count = len(sources)`; every row guaranteed non-empty sources by construction; 6/6 tests GREEN including `test_every_keyword_has_sources` and `test_source_diversity_count` |
| 5 | Close variants ("grocery delivery" / "groceries delivery" / "grocery deliveries") merge into one canonical row via lemmatized + token-sorted hashing | VERIFIED | `lib/canon.canonicalise()` singularises via inflect + sorts tokens (non-question) → sha256[:16]; `merge_raw_files()` groups by `lemma_hash`; `canonical = min(variants, key=len)`; `test_close_variants_merge` and `test_grocery_variants_merge` GREEN |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/lib/http.py` | `build_client()` with RetryTransport, retries 429/500/502/503/504 × 3, no retry on 401 | VERIFIED | 27-line factory; `Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])`; 3/3 tests GREEN |
| `scripts/lib/canon.py` | `canonicalise(keyword) -> (canonical_form, lemma_hash)` | VERIFIED | 56 lines; inflect singularisation + token sort for non-questions; question-prefix order preserved; ValueError on empty; 4/4 tests GREEN |
| `scripts/serp_fetch.py` | Serper REST fetch → `raw/serper.json` with all four signal blocks | VERIFIED | 202-line PEP 723 script; exports `main`, `main_with_args`, `fetch_seed`, `normalise_response`; locale required args; 6/6 tests GREEN |
| `scripts/tavily_extract.py` | Tavily SDK extract per competitor → `raw/tavily-<domain>.json` | VERIFIED | 161-line PEP 723 script; exports `main`, `main_with_args`, `parse_competitor_arg`; caps enforced; `extract_depth='basic'`; 4/4 tests GREEN |
| `scripts/merge_signals.py` | raw/*.json → `keywords.json` with sources array, canonical form, source_diversity | VERIFIED | 361-line PEP 723 script; exports `main`, `main_with_args`, `merge_raw_files`, `build_keywords_json`; handles all 6 source types; writes to run_dir root; 6/6 tests GREEN |
| `SKILL.md` Steps 6-10 | Phase 2 workflow with WebSearch, serp_fetch, tavily_extract, merge invocations | VERIFIED | 279 lines (under 500); Steps 6-10 present; WebSearch locale-embedded query instruction present; Write tool instruction for websearch-baseline.json; exact CLI signatures match scripts |
| `tests/fixtures/serper_search_uk.json` | Full Serper UK response with organic/PAA/related/ads | VERIFIED | Present with correct shape |
| `tests/fixtures/serper_empty_ads.json` | Serper response with empty ads array | VERIFIED | Present |
| `tests/fixtures/tavily_extract_2urls.json` | Tavily extract with 1 result + 1 failed_result | VERIFIED | Present with correct shape |
| `tests/README.md` | Test invocation guide | VERIFIED | Present with full `uv run --with` command |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `serp_fetch.py` | `lib/http.py` | `from lib.http import build_client` | WIRED | Line 39 import; line 156 used in `with build_client() as client:` |
| `merge_signals.py` | `lib/canon.py` | `from lib.canon import canonicalise` | WIRED | Line 60 import; line 232 called in `_add()` |
| `merge_signals.py` | `run_dir/keywords.json` | `out_path = run_dir / "keywords.json"` then `.write_text()` | WIRED | Line 336 path construction; line 337 write |
| `merge_signals.py` | `raw/*.json` | `raw_dir.glob("*.json")` and named-path reads | WIRED | serper.json read by name; `tavily-*.json` by glob; websearch-baseline.json by name (optional) |
| `SKILL.md Step 7` | `raw/websearch-baseline.json` | Write tool instruction with explicit path | WIRED | Line 211: `Write to: {run_dir}/raw/websearch-baseline.json` |
| `SKILL.md Step 8` | `serp_fetch.py` | `Bash(uv run ... serp_fetch.py --run-dir ... --seeds ... --gl ... --hl ...)` | WIRED | Line 225 |
| `SKILL.md Step 9` | `merge_signals.py` | `Bash(uv run ... merge_signals.py --run-dir ...)` | WIRED | Line 255 |
| `conftest.py` | `tests/fixtures/*.json` | `serper_fixture` / `serper_empty_ads_fixture` / `tavily_fixture` fixtures | WIRED | Lines 42-56; all three fixtures load from `FIXTURES_DIR` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SIGL-01 | 02-02-PLAN.md | `serp_fetch.py` persists organic + PAA + related + ads to `raw/serper.json` | SATISFIED | `normalise_response()` extracts all four blocks with defensive `.get()`; `test_writes_all_blocks` asserts all blocks non-empty |
| SIGL-02 | 02-03-PLAN.md | `tavily_extract.py` with max-5-competitors, max-5-URLs, `extract_depth='basic'` | SATISFIED | `extract_depth="basic"` hardcoded; cap logic present; `test_caps_enforced` and `test_uses_basic_depth` GREEN |
| SIGL-03 | 02-05-PLAN.md | WebSearch invoked from skill prompt (not a script) | SATISFIED | SKILL.md Step 7 instructs WebSearch calls + Write tool for websearch-baseline.json; no Python wrapper script exists for WebSearch |
| SIGL-04 | 02-02-PLAN.md | Locale params (gl, hl) passed to all sources from brief fields | SATISFIED | `serp_fetch.py` has required `--gl`/`--hl` args included in POST body and persisted in `locale` block; SKILL.md Step 7 embeds locale in WebSearch query strings; SKILL.md Step 8 derives gl/hl from brief fields |
| SIGL-05 | 02-04-PLAN.md | Each keyword retains `sources` array with attribution | SATISFIED | `build_keywords_json()` preserves full attribution dicts; `source_diversity` computed as distinct source string count; `test_every_keyword_has_sources` GREEN |
| SIGL-06 | 02-01-PLAN.md + 02-04-PLAN.md | Keywords lemmatized + canonicalized to merge close variants | SATISFIED | `lib/canon.canonicalise()` singularises + sorts; `merge_raw_files()` groups by `lemma_hash`; `canonical = min(variants, key=len)`; `test_close_variants_merge` and `test_grocery_variants_merge` GREEN |

No orphaned requirements — all 6 SIGL requirements are claimed by plans and verified against code.

---

### Anti-Patterns Found

No anti-patterns detected in production code.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | — |

No TODOs, no placeholder returns, no stub implementations, no console-only handlers found in any of the five implementation files or the two library modules.

---

### Phase 3 Schema Readiness

Phase 3 (RANK-04) requires columns: `keyword | intent | match_type | theme | signal_count | source_diversity | sources | score`.

`keywords.json` as produced by Phase 2 provides:
- `canonical` — maps to `keyword` column
- `signal_count` — present, correctly computed
- `source_diversity` — present, correctly computed as distinct source string count
- `sources` — present, full attribution dicts

Phase 3 adds: `intent`, `match_type`, `theme`, `score`. These are Phase 3 responsibilities and correctly absent from Phase 2 output. The schema is additive-compatible — Phase 3 can augment each row without breaking existing fields.

**Phase 3 is unblocked.** No missing fields required for ranking to consume `keywords.json`.

---

### Human Verification Required

#### 1. End-to-End Live Run

**Test:** Complete SKILL.md Steps 6-10 in a Claude Code session with a real grocery delivery brief, real API keys in `.env`.

**Expected:**
- `raw/websearch-baseline.json` written by the Write tool (verifies SIGL-03 live path)
- `raw/serper.json` exists with `gl` and `hl` matching the brief Location/Language fields
- `raw/tavily-<domain>.json` files for each competitor URL provided
- `keywords.json` at run folder root with `keywords_count > 0`
- Step 10 summary printed to chat

**Why human:** Requires live API keys; WebSearch is LLM-invoked and cannot be mocked in unit tests; locale derivation logic in SKILL.md (e.g., "United Kingdom" → "uk") requires human judgment to confirm correctly applied.

This item does NOT block Phase 3 — `keywords.json` schema is validated by unit tests and Phase 3 can proceed from any valid `keywords.json`.

---

### Gaps Summary

No gaps. All five observable truths are fully implemented and verified:

1. Serper fetch is real (not a stub) — writes locale-correct `by_seed[]` JSON with all four signal blocks.
2. Tavily extract is real — enforces caps, explicit `extract_depth='basic'`, persists `failed_results`.
3. WebSearch is wired through SKILL.md Step 7 as a Write-tool output to `websearch-baseline.json`.
4. Source attribution is real — every keyword row has a non-empty `sources` array with distinct `source` strings; `source_diversity` is computed correctly.
5. Canonicalization is real — `lib/canon.canonicalise()` lemmatizes and sorts; `merge_signals.py` groups by hash; close variants merge to one row.

The full 41-test suite (18 Phase 1 + 23 Phase 2) passes green. SKILL.md is 279 lines (under the 500-line limit). All 6 SIGL requirements are satisfied.

---

_Verified: 2026-05-08T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
