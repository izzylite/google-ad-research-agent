---
phase: 3
slug: ranking-and-scoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 3 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x via `uv run --with pytest` |
| **Quick run** | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_rank_keywords.py -x` |
| **Full suite** | `uv run --with pytest --with python-dotenv --with python-slugify --with respx --with httpx --with httpx-retries --with tavily-python --with inflect pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~16s full suite |

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 3-W0 | 03-00 | 0 | (test infra) | scaffold | `pytest tests/test_rank_keywords.py --collect-only` | ⬜ |
| 3-A-01 | 03-A | 1 | RANK-02 (composite score primary=source_diversity) | unit | `pytest tests/test_rank_keywords.py::test_score_formula -x` | ⬜ |
| 3-A-02 | 03-A | 1 | RANK-02 (sort order) | unit | `pytest tests/test_rank_keywords.py::test_diversity_dominates -x` | ⬜ |
| 3-A-03 | 03-A | 1 | RANK-03 (match_type heuristic) | unit | `pytest tests/test_rank_keywords.py::test_match_type_logic -x` | ⬜ |
| 3-A-04 | 03-A | 1 | RANK-04 (8-column schema, no "volume") | unit | `pytest tests/test_rank_keywords.py::test_schema_columns -x` | ⬜ |
| 3-A-05 | 03-A | 1 | (theme empty in Phase 3) | unit | `pytest tests/test_rank_keywords.py::test_theme_empty -x` | ⬜ |
| 3-B-01 | 03-B | 2 | RANK-01 (intent rubric in SKILL.md) | manual | SKILL.md Step 11 has 4-class rubric + anchor examples + temp=0 instruction | ⬜ |
| 3-B-02 | 03-B | 2 | (intent labels feeding rank script) | manual | SKILL.md Step 12 invokes rank_keywords.py with --intents-file | ⬜ |

## Wave 0 Requirements

- [ ] `tests/test_rank_keywords.py` — RED stubs for score formula, sort order, match_type, schema, theme empty, intent join
- [ ] `tests/fixtures/keywords_phase2.json` — sample input shape from Phase 2

## Manual-Only Verifications

| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| 4-class intent labeling consistency | RANK-01 | LLM behavior in skill prompt; ≥90% reproducibility validated against fresh CC session |
| Match-type recommendation conservatism | RANK-03 (qualitative) | Operator review of recommendations across mixed real-run keywords |

## Validation Sign-Off

- [ ] All tasks have `<automated>` or Wave 0 dep
- [ ] Sampling continuity OK
- [ ] `nyquist_compliant: true` on completion

**Approval:** pending
