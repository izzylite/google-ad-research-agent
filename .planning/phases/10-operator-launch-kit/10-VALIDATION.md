---
phase: 10
slug: operator-launch-kit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — 122 tests in v1.0 + Phase 9) |
| **Config file** | `.claude/skills/google-ad-research/scripts/pyproject.toml` |
| **Quick run command** | `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/test_export_csv.py .claude/skills/google-ad-research/scripts/tests/test_render_report.py -x -k "csv or next_steps or compliance_reorder"` |
| **Full suite command** | `uv run --with pytest --with python-dotenv --with python-slugify --with respx --with tabulate pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~25 seconds (full), ~5 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run quick command (Phase 10 test files only)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Planner refines during plan creation. Initial rows:

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-00-01 | 00 | 0 | EXPT-01..04 | unit-stub | `pytest tests/test_export_csv.py -x` | ❌ W0 | ⬜ pending |
| 10-00-02 | 00 | 0 | STEP-01..04, CMPL-05 | unit-stub | `pytest tests/test_render_report.py -k "next_steps" -x` | ❌ W0 | ⬜ pending |
| 10-01-01 | 01 | 1 | EXPT-01..04 | unit | `pytest tests/test_export_csv.py -x -v` | ✅ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | STEP-01..04, CMPL-05 | unit | `pytest tests/test_render_report.py -k "next_steps" -x` | ✅ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | EXPT-05 | integration | `pytest tests/test_render_report.py -k "exports" -x` | ✅ | ⬜ pending |
| 10-04-01 | 04 | 3 | (SKILL wiring) | manual-smoke | smoke: SKILL.md ≤500 lines + Editor import test (manual) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_export_csv.py` — RED stubs for EXPT-01..04 (3 CSVs, header exactness, level assignment, BOM-free, CRLF, round-trip)
- [ ] `tests/test_render_report.py` extension — RED stubs for STEP-01..04 + CMPL-05 (substitution, ordered list, compliance reorder, HTML checkbox + localStorage scaffolding)
- [ ] `tests/fixtures/negatives_phase10.json` — sample w/ all 3 tiers
- [ ] `tests/fixtures/clusters_phase10.json` — sample for ad-group naming + iteration order
- [ ] `tests/fixtures/forecast_phase10.json` — sample w/ campaign_totals.daily_spend_mid_usd
- [ ] `tests/fixtures/compliance_with_match.json` — non-empty matched_verticals[]
- [ ] `tests/fixtures/compliance_empty.json` — empty matched_verticals[] (no-reorder baseline)
- [ ] `tests/fixtures/golden_positives.csv` — byte-for-byte expected output (CRLF, no BOM)
- [ ] `tests/fixtures/golden_negatives.csv` — byte-for-byte expected output
- [ ] `tests/fixtures/golden_ad_groups.csv` — byte-for-byte expected output
- [ ] MODULE_MISSING guards matching Phases 2-9 pattern

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Three CSVs import cleanly into Google Ads Editor v2.x without column-mapping errors | EXPT-04 | Editor is GUI software, no programmatic API for import validation | Open Google Ads Editor, File → Import → CSV. Confirm all 3 files import w/ zero column-mapping warnings. Verify Strong negatives land at campaign level, Considered/Investigate at ad-group level. |
| Operator opens HTML report, ticks 3 checkboxes, refreshes browser, state persists | STEP-03 | localStorage behavior cross-session needs human eyeball | Open `report.html`, tick steps 1+3+5, hard refresh (Ctrl+F5), confirm same boxes still ticked. Open same report in incognito → all unchecked (new localStorage scope). |
| Operator on regulated-vertical run sees verification step at position 1 not 8 | CMPL-05 | Visual confirmation matters more than test assertion | Open report.md from medical brief run, confirm step 1 says "Complete medical verification at https://support.google.com/adspolicy/answer/176031". Open neutral brief run, confirm step 1 is "Create campaign..." instead. |
| Match Type capitalization accepted by Editor (Phrase vs phrase) | EXPT-01 | Google Editor docs inconsistent on case sensitivity | Wave 3 manual smoke: import positives.csv, confirm zero match-type errors. If errors, drop to lowercase. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (2 new test files/extensions + 8 fixtures including 3 golden CSVs)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner refines per-task map)

**Approval:** pending
