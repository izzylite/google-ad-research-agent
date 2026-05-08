---
phase: 6
slug: negatives-report-assembly-and-persistence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 6 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x via `uv run --with pytest` |
| **Quick** | `pytest tests/test_render_report.py -x` |
| **Full** | `pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~20s |

## Per-Task Map

| Task | Plan | Wave | Req | Type | Command | Status |
|------|------|------|-----|------|---------|--------|
| 6-W0 | 06-00 | 0 | (test infra) | scaffold | `pytest --collect-only` | ⬜ |
| 6-A-01 | 06-A | 1 | (md sanitize) | unit | `pytest tests/test_lib_io.py::test_escape_md_cell -x` | ⬜ |
| 6-B-01 | 06-B | 1 | NEGT-01 (3 tiers enum) | unit | `pytest tests/test_generate_negatives.py::test_tier_enum -x` | ⬜ |
| 6-B-02 | 06-B | 1 | NEGT-02 (6 categories) | unit | `pytest tests/test_generate_negatives.py::test_category_enum -x` | ⬜ |
| 6-B-03 | 06-B | 1 | NEGT-03 (dedup vs positives) | unit | `pytest tests/test_generate_negatives.py::test_dedupe_against_positives -x` | ⬜ |
| 6-C-01 | 06-C | 2 | RPRT-01 (4 sections) | unit | `pytest tests/test_render_report.py::test_four_sections -x` | ⬜ |
| 6-C-02 | 06-C | 2 | RPRT-02 (json twin schema) | unit | `pytest tests/test_render_report.py::test_json_schema -x` | ⬜ |
| 6-C-03 | 06-C | 2 | RPRT-03 ("How to read this") | unit | `pytest tests/test_render_report.py::test_disclaimer -x` | ⬜ |
| 6-C-04 | 06-C | 2 | RPRT-04 (md sanitize cells) | unit | `pytest tests/test_render_report.py::test_pipe_escaped -x` | ⬜ |
| 6-C-05 | 06-C | 2 | RPRT-05 (raw/ persistence) | unit | `pytest tests/test_render_report.py::test_raw_preserved -x` | ⬜ |
| 6-D-01 | 06-D | 2 | PRST-01 (sealed run folder) | unit | `pytest tests/test_render_report.py::test_run_folder_isolated -x` | ⬜ |
| 6-D-02 | 06-D | 2 | PRST-02 (.runs/INDEX.md) | unit | `pytest tests/test_update_index.py -x` | ⬜ |
| 6-E-01 | 06-E | 3 | (skill chain) | manual | SKILL.md Steps 21-26 invoke negatives + render + index | ⬜ |

## Wave 0 Requirements

- [ ] tests/test_generate_negatives.py — RED stubs
- [ ] tests/test_render_report.py — RED stubs
- [ ] tests/test_update_index.py — RED stubs
- [ ] tests/test_lib_io.py — extend with escape_md_cell tests
- [ ] tests/fixtures/ranked_full.json + clusters_full.json + competitor_intel_full.json + brief_sample.md
- [ ] Add `tabulate>=0.9.0` to scripts/pyproject.toml

## Manual

| Behavior | Req | Why |
|----------|-----|-----|
| LLM-generated negatives match brief context | NEGT-01..03 | Quality only verifiable in real run |
| End-to-end report quality | RPRT-01..05 | Live render w/ real artifacts |

**Approval:** pending
