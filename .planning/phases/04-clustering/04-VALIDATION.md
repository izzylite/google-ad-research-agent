---
phase: 4
slug: clustering
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 4 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x via `uv run --with pytest` |
| **Quick run** | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_validate_clusters.py -x` |
| **Full suite** | `uv run --with pytest --with python-dotenv --with python-slugify --with respx --with httpx --with httpx-retries --with tavily-python --with inflect pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~17s |

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 4-W0 | 04-00 | 0 | (test infra) | scaffold | `pytest tests/test_validate_clusters.py --collect-only` | ⬜ |
| 4-A-01 | 04-A | 1 | CLST-01 (no mixed intent) | unit | `pytest tests/test_validate_clusters.py::test_mixed_intent_rejected -x` | ⬜ |
| 4-A-02 | 04-A | 1 | CLST-02 (size 5-15 min 3) | unit | `pytest tests/test_validate_clusters.py::test_size_enforcement -x` | ⬜ |
| 4-A-03 | 04-A | 1 | CLST-02 (descriptive names) | unit | `pytest tests/test_validate_clusters.py::test_name_pattern -x` | ⬜ |
| 4-A-04 | 04-A | 1 | CLST-03 (orphans/duplicates) | unit | `pytest tests/test_validate_clusters.py::test_orphans_and_duplicates -x` | ⬜ |
| 4-B-01 | 04-B | 2 | (skill clustering steps) | manual | SKILL.md Steps 14-16 invoke clustering + validate_clusters | ⬜ |

## Wave 0 Requirements

- [ ] `tests/test_validate_clusters.py` — RED stubs covering all 9 invariants
- [ ] `tests/fixtures/clusters_valid.json`
- [ ] `tests/fixtures/clusters_mixed_intent.json`
- [ ] `tests/fixtures/clusters_oversize.json`
- [ ] `tests/fixtures/ranked_phase3.json` (input shape from Phase 3)

## Manual-Only Verifications

| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| LLM clustering quality | CLST-02 (semantic coherence) | Claude judgment in skill prompt — quality only verifiable in fresh CC session |

**Approval:** pending
