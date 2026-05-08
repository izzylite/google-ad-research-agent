---
phase: 05-competitor-ad-copy-and-lp-extraction
verified: 2026-05-08T08:00:00Z
status: passed
score: 3/3 must-haves verified
re_verification: false
human_verification:
  - test: "Live run — run competitor_intel.py against a real run folder with SERPER_API_KEY + TAVILY_API_KEY set"
    expected: "competitor-intel.json written to raw/ with real ad copy (non-empty ads[], advertisers[].raw_content populated)"
    why_human: "Cannot fire live Serper/Tavily API calls programmatically — tests mock both clients; real credential + network path untested"
  - test: "SKILL.md Step 19 LLM extraction quality"
    expected: "For a real competitor-intel.json, the LLM correctly extracts headline (first H1/bold, <=10 words), CTA (first imperative), offer (verbatim price/discount claim) and skips failed entries"
    why_human: "LLM extraction is a prompt-driven runtime step — no script, no automated test covers extraction correctness; depends on actual raw_content quality"
---

# Phase 5: Competitor Ad Copy and LP Extraction — Verification Report

**Phase Goal:** For every cluster, the report carries a slice of real competitor ad copy and LP value props.
**Verified:** 2026-05-08
**Status:** PASSED (with 2 human-verification items)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Every cluster has a Serper requery against its top-scored keyword, harvesting paid ad headlines and descriptions (COMP-01) | VERIFIED | `competitor_intel.py` loops over `clusters["clusters"]`, picks `keywords[0]["keyword"]` per cluster, calls `fetch_seed()` + `normalise_response()` (lines 252-277); `test_ads_fetched_per_cluster` asserts `call_count == 3` for 3-cluster input and verifies `len(out["clusters"]) == 3`; 10/10 tests GREEN |
| 2 | Ad copy is deduplicated by display-URL domain; affiliate/aggregator/voucher domains (URL-param and blocklist) are filtered out (COMP-02) | VERIFIED | `is_affiliate_url()`, `is_affiliate_domain()`, `dedupe_by_domain()`, `filter_ads()` all implemented and importable; AFFILIATE_DOMAINS frozenset of 23 domains; schemeless displayUrl bug fixed; 6 unit tests cover affiliate URL param, domain blocklist, subdomain match, dedup, cap — all GREEN |
| 3 | For top 3-5 advertisers per cluster, Tavily extracts LP raw_content; failed results are persisted (not dropped) with extract_status="failed"; LLM extraction rubric for headline/CTA/offer is documented and wired into SKILL.md (COMP-03) | VERIFIED | `main_with_args` calls `TavilyClient.extract()` on top N ad links, builds `advertisers[]` with `extract_status` field; failed_results written as `raw_content=""`, `extract_status="failed"`; SKILL.md Step 17 chains to Step 18; references/phase5-competitor-intel.md has Steps 18-20 with explicit extraction rubric |

**Score:** 3/3 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.claude/skills/google-ad-research/scripts/competitor_intel.py` | Full orchestrator: Serper requery + affiliate filter + dedupe + Tavily LP extract | VERIFIED | 378 lines, PEP 723 header present, all 5 exported helpers (`main_with_args`, `is_affiliate_url`, `is_affiliate_domain`, `dedupe_by_domain`, `filter_ads`) implemented and importable |
| `.claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py` | 10 GREEN tests covering COMP-01, COMP-02, COMP-03 | VERIFIED | 270 lines, MODULE_MISSING guard present, all 10 tests collected and passing |
| `.claude/skills/google-ad-research/scripts/tests/fixtures/clusters_phase5.json` | 3-cluster input (transactional/commercial/informational) | VERIFIED | Valid JSON, `clusters` array length = 3 |
| `.claude/skills/google-ad-research/scripts/tests/fixtures/serper_ads_raw.json` | 6-ad Serper response: 2 affiliate, 1 domain dupe, 3 clean | VERIFIED | Valid JSON, `ads` array length = 6 |
| `.claude/skills/google-ad-research/scripts/tests/fixtures/serper_ads_empty.json` | Serper response with ads: [] | VERIFIED | Valid JSON, `ads` array length = 0 |
| `.claude/skills/google-ad-research/scripts/tests/fixtures/tavily_lp_response.json` | Tavily extract: 3 ok results + 1 failed_result | VERIFIED | Valid JSON, `results` length = 3, `failed_results` length = 1 |
| `.claude/skills/google-ad-research/SKILL.md` | Steps 18-19 for Phase 5; Step 17 chains into Phase 5; under 500 lines | VERIFIED | 473 lines; Step 17 text = "Phase 5 (competitor intel) begins at Step 18 below."; pointer to references/phase5-competitor-intel.md with Read-tool instruction |
| `.claude/skills/google-ad-research/references/phase5-competitor-intel.md` | Steps 18-20 with competitor_intel.py invocation, LLM extraction rubric, Phase 5 stop gate | VERIFIED | Steps 18, 19, 20 present; `competitor_intel.py` CLI documented; `raw_content`, `headline`, `cta`, `offer` extraction rubric present; Phase 6 stop gate present |
| `.claude/skills/google-ad-research/scripts/pyproject.toml` | Project manifest declaring httpx-retries + tavily-python so tests resolve imports | VERIFIED | Created in Plan 05-01; required for `uv run --project .../scripts --with pytest` to resolve transitive deps |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `competitor_intel.py` | `serp_fetch.fetch_seed` + `normalise_response` | `from serp_fetch import fetch_seed, normalise_response` at line 54 | WIRED | Import confirmed in source; `sys.path.insert(0, str(Path(__file__).resolve().parent))` at line 38 enables sibling import |
| `competitor_intel.py` | `TavilyClient.extract()` | `tavily_client.extract(urls=lp_urls, ...)` at line 299 | WIRED | TavilyClient imported at line 46; extract called in main loop with `include_usage=True` |
| `competitor_intel.py` | `lib/http.build_client()` | `serper_client = build_client(timeout=30.0)` at line 231 | WIRED | `from lib.http import build_client` at line 42 |
| `competitor_intel.py` | `raw/competitor-intel.json` | `out_path.write_text(json.dumps(output, indent=2), ...)` at line 365 | WIRED | Output path constructed as `raw_dir / "competitor-intel.json"` at line 215 |
| `SKILL.md Step 17` | `Phase 5 / Step 18` | Text: "Phase 5 (competitor intel) begins at Step 18 below." | WIRED | Old STOP gate removed; forward chain confirmed |
| `SKILL.md Phase 5 pointer` | `references/phase5-competitor-intel.md` | `> See .../references/phase5-competitor-intel.md ... Load it with the Read tool` | WIRED | Pointer and Read-tool instruction present at line 473 of SKILL.md |
| `references Step 18` | `scripts/competitor_intel.py` | `uv run "${CLAUDE_SKILL_DIR}/scripts/competitor_intel.py" --run-dir ...` | WIRED | Confirmed in phase5-competitor-intel.md line 13 |
| `references Step 19` | `raw/competitor-intel.json` | `Read competitor-intel.json["clusters"][*].advertisers[*].raw_content` | WIRED | Step 19 reads the file using the Read tool; extraction loop over `extract_status == "ok"` entries confirmed |
| `test_competitor_intel.py` | `competitor_intel.py` | MODULE_MISSING guard: `try: import competitor_intel; MODULE_MISSING = False` | WIRED | Guard at lines 18-23; `pytestmark = pytest.mark.skipif(MODULE_MISSING, ...)` at line 25 |
| `test_competitor_intel.py` | `fixtures/*.json` | `FIXTURES_DIR = Path(__file__).parent / "fixtures"` | WIRED | FIXTURES_DIR used in 5 test functions to load fixture JSON |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|---------|
| COMP-01 | 05-01 | Per-cluster Serper requery extracts paid ad headlines + descriptions from ads block | SATISFIED | `main_with_args` loops over clusters, calls `fetch_seed()` per cluster; `test_ads_fetched_per_cluster` verifies 3 Serper calls for 3 clusters; REQUIREMENTS.md checkbox [x] |
| COMP-02 | 05-01 | Ad copy deduplicated by advertiser domain; affiliate/aggregator domains filtered | SATISFIED | `is_affiliate_url`, `is_affiliate_domain`, `dedupe_by_domain`, `filter_ads` all implemented; 5 unit tests cover all filter and dedup cases GREEN; REQUIREMENTS.md checkbox [x] |
| COMP-03 | 05-02 | Tavily extracts landing-page value props (headline, primary CTA, offer) for top 3-5 advertisers per cluster | SATISFIED | `competitor_intel.py` extracts LP raw_content via Tavily; SKILL.md Step 19 (in references file) provides explicit LLM extraction rubric for headline/CTA/offer; REQUIREMENTS.md checkbox [x] |

No orphaned requirements. REQUIREMENTS.md maps all 3 COMP-* requirements to Phase 5, all marked complete.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned `competitor_intel.py` (378 lines) and `test_competitor_intel.py` (270 lines). Zero TODO/FIXME/HACK/PLACEHOLDER comments. No empty return stubs. No console.log-only handlers. No MODULE_MISSING stub remaining (raises ImportError replaced with full implementation).

---

### Full Test Suite Result

```
66 passed, 10 skipped in 9.37s
```

Phase 5 tests: **10/10 PASSED**. Prior-phase tests unaffected. The 10 skipped entries are Wave 0 stubs in other test files (pre-existing).

---

### Phase 6 Readiness — File Contract

The task prompt notes Phase 6 reads: `competitor-intel.json`, `competitor-intel-extracted.json`, `ranked.json`, `clusters.json`.

| File | Written by | Status |
|------|-----------|--------|
| `raw/competitor-intel.json` | `competitor_intel.py` (Phase 5) | PRODUCED — schema verified: `metadata.generated_at`, `clusters[*].representative_keyword`, `clusters[*].ads[]`, `clusters[*].advertisers[].raw_content`, `clusters[*].advertisers[].extract_status` |
| `clusters.json` | Phase 4 `validate_clusters.py` | PRE-EXISTS — Phase 4 complete |
| `ranked.json` | Phase 3 `rank_keywords.py` | PRE-EXISTS — Phase 3 complete |
| `competitor-intel-extracted.json` | Not defined in Phase 5 | NOTE — this file name does not appear anywhere in Phase 5 plans, REQUIREMENTS.md, or RESEARCH.md. The `headline/cta/offer` extraction in Step 19 is LLM-driven at runtime and held in memory; Phase 6 will either read `competitor-intel.json` directly (advertiser raw_content) or define a Write-tool step to persist the extracted data. This is a Phase 6 planning concern, not a Phase 5 gap. |

---

### Human Verification Required

#### 1. Live API run

**Test:** With `SERPER_API_KEY` and `TAVILY_API_KEY` set in `.env`, copy a real `clusters.json` into a test run folder and execute `uv run .claude/skills/google-ad-research/scripts/competitor_intel.py --run-dir <path> --gl uk --hl en-GB`.
**Expected:** `raw/competitor-intel.json` written; stdout JSON shows `clusters_processed >= 1`, `serper_credits_used >= 1`; at least one cluster has non-empty `ads[]` and at least one advertiser with `extract_status="ok"` and non-empty `raw_content`.
**Why human:** All tests mock `fetch_seed` and `TavilyClient.extract`; the live HTTP path (SSL, auth, Serper ads block shape in production, Tavily extract for real LP URLs) has not been exercised.

#### 2. Step 19 LLM extraction quality

**Test:** With a real `competitor-intel.json` (produced by live run), advance to SKILL.md Step 19. Verify the LLM correctly extracts `headline` (first H1 or bold phrase, truncated to 10 words), `cta` (first imperative/button text), `offer` (verbatim price/discount claim), and produces `null` for fields not found.
**Expected:** `competitor_summary` list shows plausible values; no hallucinated headlines; failed advertisers correctly skipped.
**Why human:** LLM extraction correctness depends on real `raw_content` quality from Tavily; cannot verify programmatically without live API data and a running LLM session.

---

### Gaps Summary

No gaps. All 3 requirements satisfied, all artifacts exist and are substantive, all key links wired, 10/10 tests GREEN, full suite clean. The `competitor-intel-extracted.json` file mentioned in the task prompt is not a Phase 5 deliverable per the RESEARCH.md, REQUIREMENTS.md, and plan frontmatter — it is a Phase 6 concern.

---

_Verified: 2026-05-08_
_Verifier: Claude (gsd-verifier)_
