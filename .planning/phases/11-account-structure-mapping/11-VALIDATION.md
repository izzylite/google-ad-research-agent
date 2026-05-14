---
phase: 11
slug: account-structure-mapping
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `.claude/skills/google-ad-research/scripts/pyproject.toml` |
| **Quick run command** | `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/test_geo_filter.py .claude/skills/google-ad-research/scripts/tests/test_ad_group_match.py -x` |
| **Full suite command** | `uv run --with pytest --with python-dotenv --with python-slugify --with respx --with tabulate pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~30 seconds (full), ~5 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** quick command (Phase 11 test files)
- **After every plan wave:** full suite
- **Before `/gsd:verify-work`:** full suite green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Planner refines during plan creation. Initial rows:

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-00-01 | 00 | 0 | GEO-01..05 | unit-stub | `pytest tests/test_geo_filter.py -x` | ❌ W0 | ⬜ pending |
| 11-00-02 | 00 | 0 | ADGM-01..06 | unit-stub | `pytest tests/test_ad_group_match.py -x` | ❌ W0 | ⬜ pending |
| 11-01-01 | 01 | 1 | GEO-02..05 | unit | `pytest tests/test_geo_filter.py -x` | ✅ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | ADGM-01..04 | unit | `pytest tests/test_ad_group_match.py -x` | ✅ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | GEO-01, ADGM-05, ADGM-06 | integration | `pytest tests/test_export_csv.py tests/test_render_report.py -x` | ✅ | ⬜ pending |
| 11-04-01 | 04 | 3 | (SKILL wiring) | manual-smoke | smoke: SKILL.md ≤ 500 lines + Phase 11 reference exists + e2e on real run | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_geo_filter.py` — RED stubs for GEO-01..05 (city filter logic, state lookup, county hierarchy)
- [ ] `tests/test_ad_group_match.py` — RED stubs for ADGM-01..06 (similarity math, confidence tiering, sidecar shape)
- [ ] `tests/fixtures/us_cities_subset.json` — small FL+CA subset for filter testing
- [ ] `tests/fixtures/perf_with_ad_groups.json` — sample Phase 8 perf data w/ 3 existing ad groups
- [ ] `tests/fixtures/search_terms_phase11.json` — sample search terms keyed by ad_group_name
- [ ] `tests/fixtures/ad_group_mapping_50pct.json` — boundary case at 50.0% (no rewrite)
- [ ] `tests/fixtures/ad_group_mapping_60pct.json` — coverage triggers rewrite
- [ ] `tests/fixtures/brief_with_geo_focus.md` — brief w/ `**Geo focus:**` line
- [ ] `tests/fixtures/brief_no_geo_focus.md` — backward compat baseline
- [ ] `ad_group_match.py` MODULE_INCOMPLETE stub
- [ ] MODULE_MISSING guards matching Phase 2-10 pattern

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Re-run skill on Lake Worth FL brief w/ `geo_focus: [Palm Beach County, Lake Worth]` and confirm Tampa/Jacksonville keywords disappear | GEO-03 | End-to-end visual check | Run full skill against `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/brief.md` w/ added geo_focus; diff keywords.json before/after |
| Operator imports positives.csv w/ existing ad group names into Google Ads Editor without "Ad group not found" errors | ADGM-05 | Editor GUI | Manual Editor import smoke test on real account |
| Next Steps section reads "Add keywords to existing ad groups: ..." instead of "Create ad groups: ..." on >50% coverage | ADGM-06 | Visual confirmation | Read rendered report.md after ad_group_match runs on real account |
| us-cities.json operator-extensible without breaking filter | GEO-04 | Operator workflow test | Add a city to FL state in JSON, re-run filter, confirm new entry honored |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (2 new test files + 7 fixtures + reference data + MODULE stub)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner refines)

**Approval:** pending
