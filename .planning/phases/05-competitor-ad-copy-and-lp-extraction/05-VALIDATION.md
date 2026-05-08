---
phase: 5
slug: competitor-ad-copy-and-lp-extraction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 5 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x via `uv run --with pytest` |
| **Mocking** | respx (Serper REST), monkeypatch (TavilyClient.extract) |
| **Quick** | `pytest tests/test_competitor_intel.py -x` |
| **Full** | `pytest .claude/skills/google-ad-research/scripts/tests/ -x` |

## Per-Task Map

| Task ID | Plan | Wave | Req | Type | Command | Status |
|---------|------|------|-----|------|---------|--------|
| 5-W0 | 05-00 | 0 | (test infra) | scaffold | `pytest tests/test_competitor_intel.py --collect-only` | ⬜ |
| 5-A-01 | 05-A | 1 | COMP-01 | unit | `pytest tests/test_competitor_intel.py::test_per_cluster_serper -x` | ⬜ |
| 5-A-02 | 05-A | 1 | COMP-02 (affiliate filter) | unit | `pytest tests/test_competitor_intel.py::test_affiliate_filter -x` | ⬜ |
| 5-A-03 | 05-A | 1 | COMP-02 (domain dedupe) | unit | `pytest tests/test_competitor_intel.py::test_domain_dedupe -x` | ⬜ |
| 5-A-04 | 05-A | 1 | COMP-03 (Tavily 3-5 caps) | unit | `pytest tests/test_competitor_intel.py::test_tavily_caps -x` | ⬜ |
| 5-B-01 | 05-B | 2 | (skill steps) | manual | SKILL.md Steps 18-19 invoke competitor_intel.py + LLM extraction | ⬜ |

## Wave 0 Requirements

- [ ] tests/test_competitor_intel.py — RED stubs covering filter, dedupe, caps, per-cluster fetch
- [ ] tests/fixtures/clusters_with_keywords.json
- [ ] tests/fixtures/serper_with_affiliates.json (mixed legit + affiliate ads)
- [ ] tests/fixtures/tavily_lp_extract.json
- [ ] tests/fixtures/affiliate_domains.txt (or inline in test)

## Manual

| Behavior | Req | Why |
|----------|-----|-----|
| Skill chains competitor_intel + LLM value-prop extraction | COMP-03 | Live LLM extraction quality depends on real Tavily raw_content |

**Approval:** pending
