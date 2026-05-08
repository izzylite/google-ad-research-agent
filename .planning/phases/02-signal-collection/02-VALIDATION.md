---
phase: 2
slug: signal-collection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x via `uv run --with pytest` (continued from Phase 1) |
| **Mocking** | `respx` for httpx (Serper, lib/http); `monkeypatch` for `tavily.TavilyClient.extract` |
| **Config file** | None (still ad-hoc; promote in Phase 6) |
| **Quick run command** | `uv run --with pytest --with python-dotenv --with python-slugify --with respx --with httpx --with httpx-retries --with tavily-python --with inflect pytest .claude/skills/google-ad-research/scripts/tests/test_serp_fetch.py -x` |
| **Full suite command** | `uv run --with pytest --with python-dotenv --with python-slugify --with respx --with httpx --with httpx-retries --with tavily-python --with inflect pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~15 seconds full suite (Phase 1 18 tests + Phase 2 ~25 tests) |

---

## Sampling Rate

- **After every task commit:** Targeted test file (~3-5s)
- **After every plan wave:** Full suite (~15s)
- **Before `/gsd:verify-work`:** Full suite green + 1 manual full-flow smoke
- **Max feedback latency:** 15s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-W0-01 | 02-00 | 0 | (test infra) | scaffold | RED test stubs collect cleanly | ❌ W0 | ⬜ pending |
| 2-W0-02 | 02-00 | 0 | (fixtures) | scaffold | 3 fixture JSONs in tests/fixtures/ | ❌ W0 | ⬜ pending |
| 2-A-01 | 02-A | 1 | (lib/http) | unit | `pytest tests/test_lib_http.py -x` | ❌ W0 | ⬜ pending |
| 2-A-02 | 02-A | 1 | SIGL-06 (canon) | unit | `pytest tests/test_lib_canon.py -x` | ❌ W0 | ⬜ pending |
| 2-B-01 | 02-B | 2 | SIGL-01 (Serper organic+PAA+related+ads) | unit (respx) | `pytest tests/test_serp_fetch.py::test_writes_all_blocks -x` | ❌ W0 | ⬜ pending |
| 2-B-02 | 02-B | 2 | SIGL-04 (gl/hl from brief) | unit (respx) | `pytest tests/test_serp_fetch.py::test_locale_params_passed -x` | ❌ W0 | ⬜ pending |
| 2-B-03 | 02-B | 2 | (Pitfall 4 retry) | unit (respx) | `pytest tests/test_serp_fetch.py::test_retries_on_429 -x` | ❌ W0 | ⬜ pending |
| 2-C-01 | 02-C | 2 | SIGL-02 (Tavily basic, capped 5x5) | unit (monkeypatch) | `pytest tests/test_tavily_extract.py::test_caps_enforced -x` | ❌ W0 | ⬜ pending |
| 2-C-02 | 02-C | 2 | SIGL-02 (extract_depth='basic') | unit (monkeypatch) | `pytest tests/test_tavily_extract.py::test_uses_basic_depth -x` | ❌ W0 | ⬜ pending |
| 2-C-03 | 02-C | 2 | (failed_results persisted) | unit (monkeypatch) | `pytest tests/test_tavily_extract.py::test_failed_results_persisted -x` | ❌ W0 | ⬜ pending |
| 2-D-01 | 02-D | 3 | SIGL-05 (sources array) | unit | `pytest tests/test_merge_signals.py::test_sources_array_per_keyword -x` | ❌ W0 | ⬜ pending |
| 2-D-02 | 02-D | 3 | SIGL-06 (variants merge) | unit | `pytest tests/test_merge_signals.py::test_close_variants_merge -x` | ❌ W0 | ⬜ pending |
| 2-D-03 | 02-D | 3 | SIGL-05 (6-source taxonomy) | unit | `pytest tests/test_merge_signals.py::test_six_source_taxonomy -x` | ❌ W0 | ⬜ pending |
| 2-E-01 | 02-E | 4 | SIGL-03 (WebSearch in skill) | manual | SKILL.md Phase 2 step references WebSearch tool + write to `raw/websearch-baseline.json` | ❌ W4 | ⬜ pending |
| 2-E-02 | 02-E | 4 | (skill chains scripts) | manual | SKILL.md Phase 2 step calls `serp_fetch.py` then `tavily_extract.py` then `merge_signals.py` with run_dir from Phase 1 stdout | ❌ W4 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · auto-verified-by-inspection*

---

## Wave 0 Requirements

- [ ] `tests/test_lib_http.py` — respx-based retry + 429 tests
- [ ] `tests/test_lib_canon.py` — canonicalize + token-sort hash + variant merge
- [ ] `tests/test_serp_fetch.py` — respx mocks for Serper REST, locale assertions, all-blocks writeback
- [ ] `tests/test_tavily_extract.py` — monkeypatch TavilyClient.extract, caps, depth, failed_results
- [ ] `tests/test_merge_signals.py` — sources array, variant merge, taxonomy
- [ ] `tests/fixtures/serper_response.json` — captured Serper response (sanitized of any actual API key signals)
- [ ] `tests/fixtures/tavily_response.json` — captured Tavily extract response
- [ ] `tests/fixtures/websearch_dump.json` — sample WebSearch baseline output

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WebSearch invocation in skill | SIGL-03 | Tool only callable inside Claude Code session | Fresh CC session; complete Phase 1 + 2; confirm `raw/websearch-baseline.json` exists with WebSearch findings |
| End-to-end three-source flow | SIGL-01..06 | Real APIs need real keys + live calls | Run skill end-to-end with real `.env`; confirm `raw/serper.json`, `raw/tavily-*.json`, `raw/websearch-baseline.json`, `keywords.json` all created |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
