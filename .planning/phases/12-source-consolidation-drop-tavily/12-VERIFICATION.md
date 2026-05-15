---
phase: 12-source-consolidation-drop-tavily
verified: 2026-05-15T10:30:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 12: Source Consolidation (Drop Tavily) Verification Report

**Phase Goal:** Drop Tavily entirely. Replace Phase 5 COMP-03 landing-page extraction with Claude's built-in WebFetch. Drop redundant Phase 7 Tavily news call (Serper /news covers it). Reduce paid API surface from {Serper, Tavily, Ahrefs, Google Ads} to {Serper, Ahrefs, Google Ads}.

**Verified:** 2026-05-15T10:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `scripts/tavily_extract.py` does not exist | VERIFIED | `ls` returns "No such file or directory" |
| 2 | `tests/test_tavily_extract.py` does not exist | VERIFIED | `ls` returns "No such file or directory" |
| 3 | TAVILY_API_KEY absent from `.env.example` and `lib/config.py` | VERIFIED | `grep TAVILY_API_KEY` returns empty on both files; `REQUIRED_KEYS = ("SERPER_API_KEY",)` confirmed at lib/config.py:19 |
| 4 | `tavily-python` absent from `scripts/pyproject.toml` | VERIFIED | `grep tavily-python pyproject.toml` returns empty |
| 5 | No `tavily_fixture` in conftest.py; no `*tavily*` fixture files | VERIFIED | `grep tavily_fixture conftest.py` returns empty; fixture dir has zero `*tavily*` files |
| 6 | `competitor_intel.py` advertisers shape is Serper-only `{domain, url, title, description, position}` | VERIFIED | Lines 313-322 of competitor_intel.py show list comprehension over `top_ads` with exactly those five keys; no `raw_content`, `tavily_fetched_at`, or `extract_status` |
| 7 | `merge_signals.VALID_SOURCES` is the 5-source frozenset (no tavily-extract, no webfetch-landing) | VERIFIED | merge_signals.py:117-123 shows exactly `{serper-organic, serper-paa, serper-related, serper-ads, websearch-baseline}` |
| 8 | `pulse_synth.load_news_items` accepts single positional arg `serper_path` | VERIFIED | pulse_synth.py:165 shows `def load_news_items(serper_path: Path) -> list[dict]`; sole caller at line 444 passes single arg |
| 9 | `references/phase5-competitor-intel.md` references WebFetch and not Tavily | VERIFIED | `grep -in tavily` returns empty; "WebFetch" appears multiple times (Step 19 heading + body at lines 32, 39, 77, 78, 91) |
| 10 | `references/phase7-niche-pulse.md` contains zero Tavily references | VERIFIED | `grep -in tavily` returns empty |
| 11 | `render_report.py` exposes `_load_competitor_landing_pages` and `_join_advertisers_with_landing_pages` JOIN helpers | VERIFIED | render_report.py:229-316 defines both helpers and calls them in the competitor section render loop |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/tavily_extract.py` | DELETED | VERIFIED | File absent on disk |
| `scripts/tests/test_tavily_extract.py` | DELETED | VERIFIED | File absent on disk |
| `scripts/lib/config.py` | `REQUIRED_KEYS = ("SERPER_API_KEY",)` | VERIFIED | Line 19 confirmed |
| `scripts/pyproject.toml` | No `tavily-python` dep | VERIFIED | grep returns empty |
| `.env.example` | No `TAVILY_API_KEY` line | VERIFIED | grep returns empty |
| `scripts/competitor_intel.py` | Serper-only advertisers shape | VERIFIED | Lines 313-322 confirmed |
| `scripts/merge_signals.py` | 5-source VALID_SOURCES; no `read_tavily` | VERIFIED | Lines 117-123 confirmed; `read_tavily` symbol absent |
| `scripts/pulse_fetch.py` | No `fetch_tavily_news`, no `normalise_tavily_news`, no `tavily-news.json` write | VERIFIED | Production grep returns zero matches in pulse_fetch.py |
| `scripts/pulse_synth.py` | `load_news_items(serper_path: Path)` single-arg | VERIFIED | Line 165 confirmed |
| `scripts/render_report.py` | `_load_competitor_landing_pages` + `_join_advertisers_with_landing_pages` helpers | VERIFIED | Lines 229 and 253 confirmed |
| `SKILL.md` | `allowed-tools` includes `WebFetch`; ≤500 lines | VERIFIED | Line 3: `allowed-tools: Bash(uv run *) Read Write WebSearch WebFetch`; wc -l = 486 |
| `references/phase5-competitor-intel.md` | Step 19 uses WebFetch pattern | VERIFIED | Step 19 heading and body contain WebFetch; zero Tavily mentions |
| `references/phase7-niche-pulse.md` | Zero Tavily mentions | VERIFIED | grep returns empty |
| `.planning/REQUIREMENTS.md` | All 11 v1.3 requirements `[x]`; PULSE-02 deprecated | VERIFIED | All TVLY-01..04, WFCH-01..04, PULSE-10..12 marked `[x]`; PULSE-02 has strikethrough + DEPRECATED pointer |
| `.planning/ROADMAP.md` | Phase 13 backlog row exists | VERIFIED | Phase 13 section present: "Landing-Page Extract Vendor Swap (BACKLOG — defer-until-friction)" |
| `.planning/STATE.md` | Milestone v1.3 closed | VERIFIED | frontmatter: `milestone: v1.3`, `status: awaiting_next_milestone` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test_audit_tavily_removed.py` | `scripts/` tree + `SKILL.md` + `references/` | pathlib glob + substring scan | VERIFIED | All 8 audit tests pass in full suite run |
| `competitor_intel.py:main` | `raw/competitor-intel.json` | `json.dump` over Serper-only advertisers | VERIFIED | List comprehension at lines 313-322 uses `top_ads` (Serper); no Tavily branch |
| `merge_signals.py:VALID_SOURCES` | downstream keyword pool | 5-element frozenset membership check | VERIFIED | frozenset confirmed; `tavily-extract` absent; `webfetch-landing` absent |
| `pulse_synth.py:load_news_items` | `raw/serper-news.json` | single Path argument | VERIFIED | Signature and caller both confirmed |
| `render_report.py:_render_competitor_section` | `raw/competitor-landing-pages.json` | JOIN on `(cluster_name, advertiser.domain)` | VERIFIED | `_load_competitor_landing_pages` called at line 298; `_join_advertisers_with_landing_pages` at line 307 |
| `SKILL.md:frontmatter` | Claude Code permission system | `allowed-tools` field | VERIFIED | Line 3 includes `WebFetch` |
| `references/phase5-competitor-intel.md:Step 19` | `raw/competitor-landing-pages.json` | Write tool invocation in skill prompt | VERIFIED | Step 19 instructs WebFetch + Write tool output to `competitor-landing-pages.json` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TVLY-01 | 12-01 | `tavily_extract.py` deleted | SATISFIED | File absent; test_tavily_extract_deleted passes |
| TVLY-02 | 12-01 | `TAVILY_API_KEY` removed from `.env.example` + `lib/config.py` | SATISFIED | Both files confirmed clean; `REQUIRED_KEYS=("SERPER_API_KEY",)` |
| TVLY-03 | 12-01 | `tavily-python` removed from `pyproject.toml`; fixture files deleted | SATISFIED | pyproject.toml clean; zero `*tavily*` fixture files |
| TVLY-04 | 12-01 | `test_tavily_extract.py` deleted; conftest `tavily_fixture` removed | SATISFIED | Both absent |
| WFCH-01 | 12-04 | SKILL.md Phase 5 Step 19 rewritten for WebFetch | SATISFIED | references/phase5-competitor-intel.md Step 19 uses WebFetch; zero Tavily mentions |
| WFCH-02 | 12-04 | Skill writes `{headline, cta, offer}` to `raw/competitor-landing-pages.json` | SATISFIED | render_report.py JOIN helpers exist; test_competitor_section_joins_webfetch_results passes |
| WFCH-03 | 12-02 | `competitor_intel.py` drops Tavily; Serper-only advertisers shape | SATISFIED | Zero tavily substrings in competitor_intel.py; shape confirmed at lines 313-322 |
| WFCH-04 | 12-02 | `merge_signals.py` removes `tavily-extract` from VALID_SOURCES | SATISFIED | 5-source frozenset confirmed; `read_tavily` symbol absent |
| PULSE-10 | 12-03 | `pulse_fetch.py` removes Tavily news call | SATISFIED | Zero tavily mentions in pulse_fetch.py; `fetch_tavily_news` symbol absent |
| PULSE-11 | 12-03 | `pulse_synth.load_news_items` drops Tavily branch; single-arg signature | SATISFIED | `def load_news_items(serper_path: Path)` confirmed |
| PULSE-12 | 12-04 | SKILL.md Steps 27-30 (Phase 7) drop Tavily; PULSE-02 deprecated | SATISFIED | references/phase7-niche-pulse.md clean; REQUIREMENTS.md PULSE-02 has strikethrough + deprecation note |

**All 11 v1.3 requirement IDs SATISFIED.**

---

### Test Suite Verification

**Full suite command (with `--with inflect` required for merge_signals.py PEP 723 transitive):**

```
uv run --project .claude/skills/google-ad-research/scripts \
  --with pytest --with respx --with python-dotenv --with python-slugify \
  --with tabulate --with inflect \
  pytest .claude/skills/google-ad-research/scripts/tests/
```

**Result:** 250 passed, 0 failed, 0 skipped

Note: Running without `--with inflect` produces `228 passed, 22 skipped` — the 22 skips are `merge_signals.py` + `lib/canon` import-guard skips due to missing `inflect` in the sandbox. This is a uv invocation issue, not a code issue. The SUMMARY documents this and the correct invocation. All 250 tests are substantive.

---

### Operator-Grep Gate

**Command:** `grep -rni tavily .claude/skills/google-ad-research/ | grep -v -E "(__pycache__|\.pytest_cache|tests/)"`

**Result:** Zero matches in production code (scripts/, lib/, references/, SKILL.md, .env.example).

Test files retain `tavily` strings intentionally as absence-assertion messages and Wave-0 Phase 12 archaeology. The audit test `test_repo_grep_tavily_clean` already encodes this via `SKIP_DIRS = {"tests", "fixtures", "__pycache__", ".venv", ...}` and only walks `SCRIPTS_DIR + REFERENCES_DIR + SKILL_DIR/"SKILL.md"` roots. This is correct and intentional design — obfuscating absence-assertions would destroy their value.

---

### Anti-Patterns Found

None found in production code. Scan of competitor_intel.py, merge_signals.py, pulse_fetch.py, pulse_synth.py, render_report.py, SKILL.md, and references/ returned no TODOs, placeholders, empty implementations, or stub handlers relevant to Phase 12 deliverables.

---

### Human Verification Required

**One item approved by operator judgment (documented in 12-05-SUMMARY.md):**

Per the verification scope note in the prompt and 12-05-SUMMARY.md key-decisions: the operator (single-developer project) approved the e2e checkpoint without running the full 9-step manual smoke. The rationale is documented: production code is fully GREEN against the canonical audit gate, and residual empirical risk (WebFetch per-domain permission friction in a real Claude session) is handled by Phase 13 backlog (Serper /scrape vendor swap, defer-until-friction). This is operator judgment, not a verification gap.

The verifier does NOT treat this as a gap per the explicit scope instruction in the verification request.

---

### Gaps Summary

No gaps. All automated proxies are green:
- 250/250 tests pass (with correct `--with inflect` invocation)
- Zero Tavily matches in production code
- All 11 requirement IDs marked Complete in REQUIREMENTS.md with traceability rows
- Advertiser shape is exactly `{domain, url, title, description, position}`
- `load_news_items` single-arg signature confirmed
- `_load_competitor_landing_pages` sentinel exists in render_report.py (lifts Wave-0 skip-guard)
- SKILL.md is 486 lines (under 500 limit) and includes WebFetch in allowed-tools
- Phase 13 backlog row exists in ROADMAP.md
- STATE.md shows `milestone: v1.3`, `status: awaiting_next_milestone`

---

_Verified: 2026-05-15T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
