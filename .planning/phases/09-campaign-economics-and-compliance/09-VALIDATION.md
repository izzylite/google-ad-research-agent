---
phase: 9
slug: campaign-economics-and-compliance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — 108 tests in v1.0) |
| **Config file** | `.claude/skills/google-ad-research/scripts/pyproject.toml` |
| **Quick run command** | `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/test_bid_suggest.py .claude/skills/google-ad-research/scripts/tests/test_forecast_budget.py .claude/skills/google-ad-research/scripts/tests/test_compliance_check.py -x` |
| **Full suite command** | `uv run --with pytest --with python-dotenv --with python-slugify --with respx --with tabulate pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~25 seconds (full), ~5 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run quick command (phase 9 test files only)
- **After every plan wave:** Run full suite command (all 108+ tests)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Populated by gsd-planner during plan creation. Each task maps to one or more requirement IDs and gets an automated verification command.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-00-01 | 00 | 0 | BIDS-01..04 | unit-stub | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_bid_suggest.py -x` | ❌ W0 | ⬜ pending |
| 9-00-02 | 00 | 0 | FRCS-01..05 | unit-stub | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_forecast_budget.py -x` | ❌ W0 | ⬜ pending |
| 9-00-03 | 00 | 0 | CMPL-01..04 | unit-stub | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_compliance_check.py -x` | ❌ W0 | ⬜ pending |
| 9-01-01 | 01 | 1 | BIDS-01..04 | unit | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_bid_suggest.py -x` | ✅ W0 | ⬜ pending |
| 9-02-01 | 02 | 1 | FRCS-01..05 | unit | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_forecast_budget.py -x` | ✅ W0 | ⬜ pending |
| 9-03-01 | 03 | 1 | CMPL-01..04 | unit | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_compliance_check.py -x` | ✅ W0 | ⬜ pending |
| 9-04-01 | 04 | 2 | BIDS-03, FRCS-04, CMPL-03 | integration | `uv run --with pytest --with tabulate pytest .claude/skills/google-ad-research/scripts/tests/test_render_report.py -x` | ✅ v1.0 | ⬜ pending |
| 9-05-01 | 05 | 3 | (SKILL.md wiring) | manual-smoke | smoke check: SKILL.md ≤ 500 lines + Phase 9 reference exists | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Note:** Planner refines this table during plan creation. Each PLAN.md file references back to its row(s) here.

---

## Wave 0 Requirements

- [ ] `tests/test_bid_suggest.py` — RED stubs covering BIDS-01..04 (intent-multiplier math, cluster-median fallback, null+flag edge case, config single-source)
- [ ] `tests/test_forecast_budget.py` — RED stubs covering FRCS-01..05 (intent-CTR anchors, max-CPC × 0.65 avg ratio, low/mid/high band math × 0.5/1.0/1.5, JSON schema, "how calculated" string presence)
- [ ] `tests/test_compliance_check.py` — RED stubs covering CMPL-01..04 (token matching word-boundary, brief.md + top-50-keyword scan, references/compliance-verticals.json schema, report.json compliance[] array shape)
- [ ] `tests/fixtures/ranked_with_cpc.json` — sample ranked-enriched rows w/ cpc_micros populated
- [ ] `tests/fixtures/ranked_no_cpc.json` — sample rows w/ cpc_micros=null (forces cluster-median fallback)
- [ ] `tests/fixtures/clusters_phase9.json` — clusters.json fixture for cluster-median grouping
- [ ] `tests/fixtures/brief_medical.md` — brief w/ "Primary & Urgent Care" + medical tokens (CMPL trigger)
- [ ] `tests/fixtures/brief_neutral.md` — brief w/ no regulated tokens (CMPL no-flag baseline)
- [ ] `.claude/skills/google-ad-research/references/compliance-verticals.json` — 5 vertical entries (medical/legal/finance/gambling/crypto) w/ tokens + verification_url + policy_note
- [ ] MODULE_MISSING guards in test files matching Phase 2-8 pattern (try/except ImportError + pytestmark skipif) so Wave 0 lands RED-not-error

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Operator reads "Suggested Max CPC" column in report.md and trusts the value | BIDS-03 | Subjective UX check — column legibility, USD formatting (`$1.42` not `1.42`), hover tooltip in HTML | Open `.runs/<latest>/report.md` and `report.html`, confirm column present, USD formatted with cents, HTML hover tooltip shows multiplier ratio |
| Operator reads "Budget Forecast" section and understands the disclaimer prevents over-promising to client | FRCS-05 | Subjective — "How this is calculated" copy must be plain English | Read report.md Budget Forecast section, confirm CTR anchors named, avg-CPC ratio named, low/mid/high band rationale named |
| Operator sees ⚠ Compliance Required block on a regulated-vertical run and not on a neutral run | CMPL-03 | End-to-end visual check — yellow background in HTML, blockquote in MD | Run skill once with medical brief, once with grocery brief; diff report.md and confirm block appears only in medical run |
| Operator extends `compliance-verticals.json` w/ a new vertical entry without editing Python | CMPL-02 | Operator-extensibility test | Add a 6th vertical entry, re-run compliance_check.py, confirm new vertical surfaces in compliance-flags.json |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (3 new test files + 6 fixtures + compliance-verticals.json)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner refines per-task map)

**Approval:** pending
