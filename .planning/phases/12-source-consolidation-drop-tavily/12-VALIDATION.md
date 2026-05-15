---
phase: 12
slug: source-consolidation-drop-tavily
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.3 (declared in `.claude/skills/google-ad-research/scripts/pyproject.toml` dev group) |
| **Config file** | `.claude/skills/google-ad-research/scripts/pyproject.toml` (`[tool.pytest.ini_options]` testpaths=`["tests"]`) |
| **Quick run command** | `uv run --project .claude/skills/google-ad-research/scripts --with pytest --with respx pytest .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py .claude/skills/google-ad-research/scripts/tests/test_pulse_synth.py .claude/skills/google-ad-research/scripts/tests/test_audit_tavily_removed.py -x` |
| **Full suite command** | `uv run --project .claude/skills/google-ad-research/scripts --with pytest --with respx --with python-dotenv --with python-slugify --with tabulate pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~15 sec (quick) / ~3-5 min (full, ~252 tests post-Phase-12) |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run full suite command above
- **Before `/gsd:verify-work`:** Full suite green + `grep -rni tavily .` (excl `.planning/`, `.git/`, `uv.lock`) returns zero matches
- **Max feedback latency:** ~15 sec quick / ~300 sec full

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-W0-01 | 00 | 0 | TVLY-01..04, WFCH-01, PULSE-12 | smoke (filesystem+grep) | `pytest tests/test_audit_tavily_removed.py -x` | ❌ W0 | ⬜ pending |
| 12-W0-02 | 00 | 0 | PULSE-10 | unit | `pytest tests/test_pulse_fetch.py -x` | ❌ W0 | ⬜ pending |
| 12-W0-03 | 00 | 0 | WFCH-02 | integration | `pytest tests/test_render_report.py::test_competitor_section_joins_webfetch_results -x` | ❌ W0 | ⬜ pending |
| 12-W0-04 | 00 | 0 | WFCH-03 | unit | `pytest tests/test_competitor_intel.py::test_advertisers_shape_post_phase12 -x` | ❌ W0 | ⬜ pending |
| 12-W0-05 | 00 | 0 | WFCH-04 | unit | `pytest tests/test_merge_signals.py::test_valid_sources_post_phase12 -x` | ❌ W0 | ⬜ pending |
| 12-W0-06 | 00 | 0 | PULSE-11 | unit | `pytest tests/test_pulse_synth.py::test_load_news_items_serper_only -x` | ❌ W0 | ⬜ pending |
| 12-01-01 | 01 | 1 | TVLY-01 | smoke | `pytest tests/test_audit_tavily_removed.py::test_tavily_extract_deleted -x` | ✅ via W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | TVLY-02 | smoke | `pytest tests/test_audit_tavily_removed.py::test_tavily_env_keys_stripped -x` | ✅ via W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | TVLY-03 | smoke | `pytest tests/test_audit_tavily_removed.py::test_tavily_deps_and_fixtures_stripped -x` | ✅ via W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | TVLY-04 | smoke | `pytest tests/test_audit_tavily_removed.py::test_tavily_test_artifacts_stripped -x` | ✅ via W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | WFCH-03 | unit | `pytest tests/test_competitor_intel.py::test_advertisers_shape_post_phase12 -x` | ✅ via W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | WFCH-04 | unit | `pytest tests/test_merge_signals.py::test_valid_sources_post_phase12 -x` | ✅ via W0 | ⬜ pending |
| 12-03-01 | 03 | 1 | PULSE-10 | unit+smoke | `pytest tests/test_pulse_fetch.py::test_only_serper_news_written -x` | ✅ via W0 | ⬜ pending |
| 12-03-02 | 03 | 1 | PULSE-11 | unit | `pytest tests/test_pulse_synth.py::test_load_news_items_serper_only -x` | ✅ via W0 | ⬜ pending |
| 12-04-01 | 04 | 2 | WFCH-01 | smoke (grep) | `pytest tests/test_audit_tavily_removed.py::test_skill_md_uses_webfetch_for_step19 -x` | ✅ via W0 | ⬜ pending |
| 12-04-02 | 04 | 2 | WFCH-02 | integration | `pytest tests/test_render_report.py::test_competitor_section_joins_webfetch_results -x` | ✅ via W0 | ⬜ pending |
| 12-04-03 | 04 | 2 | PULSE-12 | smoke (grep) | `pytest tests/test_audit_tavily_removed.py::test_phase7_docs_tavily_free -x` | ✅ via W0 | ⬜ pending |
| 12-05-01 | 05 | 3 | all (e2e) | manual+full | full suite + `grep -rni tavily .` returns 0 + e2e smoke on `brief_sample.md` | ✅ existing infra | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_audit_tavily_removed.py` — repo-wide grep + filesystem audit (8 test methods covering TVLY-01..04, WFCH-01, PULSE-12)
- [ ] `tests/test_pulse_fetch.py` — new file; Phase 7 had no pulse_fetch tests; locks single-source contract (PULSE-10)
- [ ] `tests/test_render_report.py::test_competitor_section_joins_webfetch_results` — new test: render_report joins competitor-intel.json + competitor-landing-pages.json (WFCH-02)
- [ ] `tests/test_competitor_intel.py::test_advertisers_shape_post_phase12` — new test asserting Tavily-shape fields absent, Serper-shape present (WFCH-03)
- [ ] `tests/test_merge_signals.py::test_valid_sources_post_phase12` — new test pinning VALID_SOURCES to 5-source post-Phase-12 set (WFCH-04)
- [ ] `tests/test_pulse_synth.py` modifications — update existing dual-source tests to single-source signatures (PULSE-11)
- [ ] `tests/conftest.py` modifications — delete `tavily_fixture` (lines 53-56)
- [ ] **Wave 0 RED state:** all above tests written and FAILING against Phase 11 codebase. Wave 1 flips them GREEN.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude correctly invokes WebFetch per SKILL.md Step 19 on real advertisers | WFCH-01 (behavioral) | WebFetch is a Claude built-in tool — only callable from inside a Claude session, not from pytest. Automated grep asserts SKILL.md instructs the call; only manual e2e proves Claude follows the instruction. | Run real brief → reach Phase 5 → confirm Claude WebFetches top 3 advertiser URLs and writes valid `raw/competitor-landing-pages.json` with `{headline, cta, offer}` shape |
| E2E smoke on real brief produces report.md with non-empty competitor section, zero Tavily strings | WFCH-02, all | Requires real API keys (Serper) and live network; pytest tier doesn't make live API calls | Phase gate manual: copy `.env.example` → `.env` with real `SERPER_API_KEY` only (no TAVILY_API_KEY); run `brief_sample.md` end-to-end; final `grep -rni tavily <run-dir>` → 0 matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test_audit_tavily_removed.py, test_pulse_fetch.py, render_report join test, advertisers_shape test, VALID_SOURCES test)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s (quick) / < 300s (full)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
