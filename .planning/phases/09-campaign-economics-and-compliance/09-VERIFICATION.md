---
phase: 09-campaign-economics-and-compliance
verified: 2026-05-14T20:15:00Z
status: passed
score: 13/13 requirements verified (CMPL-05 correctly deferred to Phase 10)
re_verification:
  previous_status: none
  previous_score: n/a
goal: "The operator can answer the three economic questions a junior PPC manager asks — 'What should I bid?', 'How much will it cost?', 'Is this vertical regulated?' — directly from the report, with values baked into the JSON artifacts so downstream tooling can consume them."
---

# Phase 9: Campaign Economics and Compliance — Verification Report

**Phase Goal:** The operator can answer the three economic questions a junior PPC manager asks — "What should I bid?", "How much will it cost?", "Is this vertical regulated?" — directly from the report, with values baked into the JSON artifacts so downstream tooling can consume them.

**Verified:** 2026-05-14T20:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                  | Status     | Evidence                                                                                                                                                                                                |
| -- | ---------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | "What should I bid?" — every ranked keyword carries a `suggested_max_cpc_micros` value (or null + flag).                | VERIFIED   | `bid_suggest.py` (344 lines) exports `INTENT_MULTIPLIERS`, `compute_suggested_cpc`, `cluster_median_cpc`, `enrich_with_bids`. Live run: 73 rows enriched (26 direct, 32 cluster-median, 15 null-flagged). |
| 2  | "How much will it cost?" — `forecast.json` carries per-cluster + campaign-level click/spend bands.                      | VERIFIED   | `forecast_budget.py` (372 lines) writes forecast.json with metadata + methodology + clusters[] + campaign_totals. Live run: 14 clusters, $66.65/day mid spend, $1999.50/mo.                              |
| 3  | "Is this vertical regulated?" — `compliance-flags.json` scans brief + top-50 keywords against 5 verticals.              | VERIFIED   | `compliance_check.py` (398 lines), 5 verticals in `references/compliance-verticals.json`. Live run on medical brief: matched legal + medical with verification_url + evidence_tokens.                    |
| 4  | Report surfaces all three answers — "Suggested CPC" column, "Budget Forecast" section, "⚠ Compliance Required" block.   | VERIFIED   | report.md inspection: line 18 ⚠ block, line 402 Budget Forecast, line 425 "How this is calculated", line 696 "Suggested CPC" column header.                                                              |
| 5  | report.json bakes the values in for downstream tooling — `forecast` object + `compliance` array.                        | VERIFIED   | report.json line 7402 `"forecast": {...}`, line 7635 `"compliance": [...]`. `suggested_max_cpc_micros` on every ranked row.                                                                              |
| 6  | Tuning-knob discipline — INTENT_MULTIPLIERS / INTENT_CTRS / BAND_MULTIPLIERS each in single config block per file.       | VERIFIED   | bid_suggest.py L69-80 (INTENT_MULTIPLIERS + frozenset assert); forecast_budget.py L74-90 (INTENT_CTRS + AVG_CPC_RATIO + BAND_MULTIPLIERS + frozenset assert).                                            |
| 7  | Compliance tokens live in data not code — `references/compliance-verticals.json`, operator-editable.                    | VERIFIED   | 5 verticals (medical, legal, finance, gambling, crypto), each with name/tokens/verification_url/policy_note. Zero hardcoded vertical tokens in `compliance_check.py`.                                    |
| 8  | SKILL.md ≤ 500 lines after Phase 9 addition; pointer-only pattern used.                                                 | VERIFIED   | SKILL.md = 497 lines. Line 495: `## Phase 9: Campaign Economics and Compliance (optional, launch-kit prep)`. Reference file pattern preserved.                                                           |
| 9  | Operator reference rubric exists — `references/phase9-economics-compliance.md` with Steps 36-40.                        | VERIFIED   | File = 209 lines. Steps 36-40 all present. Names all four scripts (bid_suggest, forecast_budget, compliance_check, render_report). Documents Phase 10 contract.                                          |
| 10 | Phase 10 downstream contract is observable — verification_url present on every matched vertical.                        | VERIFIED   | Live run compliance-flags.json: legal entry verification_url = https://support.google.com/adspolicy/answer/2464998; medical entry verification_url = https://support.google.com/adspolicy/answer/176031. |

**Score:** 10/10 truths verified.

### Required Artifacts

| Artifact                                                                                          | Expected                                                                                                              | Status     | Details                                                                                                                                                              |
| -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.claude/skills/google-ad-research/scripts/bid_suggest.py`                                         | Adds `suggested_max_cpc_micros` to ranked-enriched.json; INTENT_MULTIPLIERS single config block; cluster-median fallback. | VERIFIED   | 344 lines. All required exports present. Live: 73 rows enriched (26 direct CPC, 32 cluster-median, 15 null-flagged).                                                  |
| `.claude/skills/google-ad-research/scripts/forecast_budget.py`                                     | Writes forecast.json with per-cluster + campaign-level click/spend bands + methodology block.                          | VERIFIED   | 372 lines. INTENT_CTRS + AVG_CPC_RATIO=0.65 + BAND_MULTIPLIERS frozenset-asserted. Live forecast.json has full schema and $66.65/day mid spend.                       |
| `.claude/skills/google-ad-research/scripts/compliance_check.py`                                    | Writes compliance-flags.json with matched_verticals[] + evidence_tokens + verification_url.                            | VERIFIED   | 398 lines. COMPLIANCE_SCAN_TOP_N=50. Word-boundary regex (Pitfall 3). Live: matched legal+medical on car-accident/medical brief.                                      |
| `.claude/skills/google-ad-research/references/compliance-verticals.json`                           | 5 verticals each with name/tokens/verification_url/policy_note (CMPL-02 data-not-code).                                | VERIFIED   | 113 lines. All 5 verticals (medical/legal/finance/gambling/crypto), 4 keys per entry. Real Google Policy URLs (176031, 2464998, 176019, 9870661).                     |
| `.claude/skills/google-ad-research/scripts/render_report.py` extension                             | Adds Suggested CPC column, Budget Forecast section, ⚠ Compliance block, report.json forecast/compliance keys.          | VERIFIED   | render_report.py = 1554 lines. `render_compliance_warning` L475, `render_forecast_section` L523, "Suggested CPC" column header L357.                                  |
| `.claude/skills/google-ad-research/SKILL.md` (Phase 9 pointer)                                     | Pointer added (≤ 500 lines), references the new rubric file.                                                            | VERIFIED   | 497 lines (under cap). Phase 9 section at L495. Reference file pointer pattern matches Phase 5/7/8.                                                                   |
| `.claude/skills/google-ad-research/references/phase9-economics-compliance.md`                      | Operator-readable rubric with Steps 36-40, prerequisites, exit codes, downstream contract for Phase 10.                | VERIFIED   | 209 lines. All five step headings (36-40) present. Names all four scripts. Documents Phase 10 downstream contract (suggested_max_cpc_micros, forecast, verification_url). |

### Key Link Verification

| From                                          | To                                                       | Via                                                                | Status | Details                                                                                                                                       |
| --------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------ | ------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `bid_suggest.py`                              | `{run_dir}/ranked-enriched.json`                         | read → mutate (add suggested_max_cpc_micros per row) → write back  | WIRED  | Live run shows `suggested_max_cpc_micros` on every ranked row in report.json.                                                                  |
| `bid_suggest.py`                              | `{run_dir}/clusters.json`                                | read-only; builds keyword→cluster index for median fallback        | WIRED  | Cluster-median fallback path exercised: 32/73 rows in live run used cluster-median fallback.                                                   |
| `forecast_budget.py`                          | `{run_dir}/forecast.json`                                | json.dumps + write_text                                            | WIRED  | Live forecast.json on disk with complete schema (metadata + methodology + 14 clusters + campaign_totals).                                      |
| `forecast_budget.py`                          | `ranked-enriched.json` (with suggested_max_cpc_micros)   | read-only after bid_suggest.py wrote suggested_max_cpc_micros      | WIRED  | Sequential pipeline confirmed by orchestrator end-to-end run.                                                                                  |
| `compliance_check.py`                         | `references/compliance-verticals.json`                   | json.loads of operator-editable token data                         | WIRED  | `load_verticals()` resolves via Path(__file__).parent.parent/references/. Live run consumed all 5 verticals.                                   |
| `compliance_check.py`                         | `{run_dir}/compliance-flags.json`                        | json.dumps + write_text                                            | WIRED  | Live compliance-flags.json with metadata + matched_verticals[] (legal + medical entries).                                                      |
| `render_report.py` `render_full_report`       | forecast.json + compliance-flags.json                    | Path.exists() auto-detect (mirrors niche-pulse + account-perf)     | WIRED  | report.md L18 has ⚠ Compliance block, L402 Budget Forecast section, L425 "How this is calculated".                                             |
| sections list                                 | Compliance block index                                   | inserted before Ranked Keywords (CMPL-03 contract)                  | WIRED  | report.md: ⚠ block at L18 < Budget Forecast L402 < Ranked Keywords table L696. Section order matches contract.                                  |
| `build_report_json`                           | `report.json['compliance']` + `report.json['forecast']`  | kwarg pass-through                                                  | WIRED  | report.json L7402 `"forecast": {...}`, L7635 `"compliance": [...]`. Both populated from sidecars.                                               |
| SKILL.md Phase 9 section                      | `references/phase9-economics-compliance.md`              | explicit "Load it with the Read tool when entering Phase 9" pattern | WIRED  | SKILL.md L495-497 contains the pointer with explicit-load instruction; reference filename matches.                                            |

### Requirements Coverage

| Requirement | Source Plan        | Description                                                                                                                                                | Status     | Evidence                                                                                                                                                       |
| ----------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BIDS-01     | 09-00, 09-01       | bid_suggest.py adds suggested_max_cpc_micros via cpc_micros × intent_multiplier (1.2/0.8/0.4/1.0).                                                          | SATISFIED  | bid_suggest.py L69-78 INTENT_MULTIPLIERS dict with exact values; `compute_suggested_cpc` L91+. Live: 26 rows used direct CPC × multiplier.                     |
| BIDS-02     | 09-00, 09-01       | Cluster-median fallback when cpc_micros null; null + no_cpc_data flag when cluster empty.                                                                  | SATISFIED  | `cluster_median_cpc` L120+, `enrich_with_bids` L214+ flags rows with `no_cpc_data: true` on null. Live: 32 cluster-median + 15 null-flagged.                   |
| BIDS-03     | 09-00, 09-04, 09-05| Suggested Max CPC column in enriched table (USD with cents).                                                                                                | SATISFIED  | render_report.py L357 "Suggested CPC" in headers list. report.md L696 column visible. Em-dash for null.                                                         |
| BIDS-04     | 09-00, 09-01       | Multipliers in single config block at top of bid_suggest.py.                                                                                                | SATISFIED  | bid_suggest.py L69-78 INTENT_MULTIPLIERS dict; L80-81 frozenset assertion. No magic numbers elsewhere (per plan-01 verify grep).                                |
| FRCS-01     | 09-00, 09-02       | forecast_budget.py emits {run_dir}/forecast.json with per-cluster + campaign rollup.                                                                       | SATISFIED  | Live forecast.json: 14 clusters + campaign_totals object with daily_spend bands.                                                                                |
| FRCS-02     | 09-00, 09-02       | Click estimates use intent-class CTRs (6%/4%/2%/8%).                                                                                                       | SATISFIED  | forecast_budget.py L74-79 INTENT_CTRS = {transactional:0.06, commercial:0.04, informational:0.02, navigational:0.08}. Live forecast.methodology mirrors.        |
| FRCS-03     | 09-00, 09-02, 09-04| Spend = suggested_max_cpc × 0.65; bands × 0.5/1.0/1.5.                                                                                                     | SATISFIED  | forecast_budget.py L81 AVG_CPC_RATIO=0.65; L83 BAND_MULTIPLIERS={low:0.5, mid:1.0, high:1.5}. Live methodology block confirms.                                  |
| FRCS-04     | 09-00, 09-04, 09-05| Report renders Budget Forecast section per cluster + campaign totals.                                                                                      | SATISFIED  | report.md L402 `## Budget Forecast` + per-cluster table + campaign totals line.                                                                                 |
| FRCS-05     | 09-00, 09-04, 09-05| "How this is calculated" subsection — directional disclaimer.                                                                                              | SATISFIED  | report.md L425 `### How this is calculated`. Methodology notes verbatim in forecast.json.                                                                       |
| CMPL-01     | 09-00, 09-03       | compliance_check.py scans brief + ranked-enriched → compliance-flags.json with matched verticals + evidence + URLs.                                        | SATISFIED  | Live compliance-flags.json: legal+medical with evidence_tokens, evidence_sources, matched_keyword_count, verification_url, policy_note.                         |
| CMPL-02     | 09-00, 09-03       | Tokens in references/compliance-verticals.json (data, not code); each entry has tokens[], verification_url, policy_note.                                   | SATISFIED  | references/compliance-verticals.json has 5 verticals × {name, tokens, verification_url, policy_note}. Zero hardcoded vertical tokens in compliance_check.py.   |
| CMPL-03     | 09-00, 09-04, 09-05| "⚠ Compliance Required" block above Ranked Keywords when any vertical matches; warning-yellow HTML; blockquote markdown.                                   | SATISFIED  | report.md L18 `> ## ⚠ Compliance Required` blockquote — above L696 Ranked Keywords table. CMPL-03 contract satisfied.                                          |
| CMPL-04     | 09-00, 09-04       | report.json compliance[] array; build_report_json signature extends with compliance kwarg.                                                                  | SATISFIED  | report.json L7635 `"compliance": [...]`. build_report_json signature includes `compliance=None` kwarg (per 09-04 plan verified).                                |
| CMPL-05     | n/a (Phase 10)     | Next-Steps checklist (STEP-01) reorders compliance step to step 1 when matched_verticals non-empty.                                                        | DEFERRED   | Out of Phase 9 scope per RESEARCH.md. Phase 9 emits matched_verticals[].verification_url (contract). Phase 10 STEP-01 consumes it. REQUIREMENTS.md tracks as Pending. |

**No orphaned requirements:** Phase 9 plans 00-05 collectively cover BIDS-01..04, FRCS-01..05, CMPL-01..04. CMPL-05 explicitly deferred to Phase 10 per RESEARCH.md scope decision; verification_url contract observable in Phase 9 output.

### Anti-Patterns Found

| File                 | Line     | Pattern                                                                              | Severity | Impact                                                                                                            |
| -------------------- | -------- | ------------------------------------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------- |
| (none)               | —        | No TODO/FIXME/PLACEHOLDER/stub patterns surfaced in Phase 9 scripts during grep scan. | none     | All four artifacts (bid_suggest, forecast_budget, compliance_check, render_report extensions) are substantive code. |

Tuning-knob discipline checks (BIDS-04 / FRCS-02-03):
- `bid_suggest.py`: INTENT_MULTIPLIERS at L69 is the single source of truth; frozenset assertion at L80 guards typos.
- `forecast_budget.py`: INTENT_CTRS + AVG_CPC_RATIO + BAND_MULTIPLIERS together at L74-83; frozenset assertion at L89.
- `compliance_check.py`: COMPLIANCE_SCAN_TOP_N at L76; zero hardcoded vertical tokens (CMPL-02 contract).
- `render_report.py`: USD conversion routed through display-boundary helper (`_micros_to_usd`); no scattered `/1_000_000` math.

### Human Verification Required

Phase 9 includes a `task type="checkpoint:human-verify" gate="blocking"` step in Plan 09-05 Task 3 (end-to-end smoke on a real run-folder). Per orchestrator notes, this checkpoint was already exercised:

- Run folder: `.runs/2026-05-08T081041Z-primary-urgent-care-car-accident-lake-worth/`
- Outputs verified on disk: ranked-enriched.json (with suggested_max_cpc_micros), forecast.json, compliance-flags.json, report.md/html/json (all sections present).
- Test suite: 56/56 Phase 9 tests GREEN; 122 total passing; 0 v1.0 regressions.

No outstanding human checks required for goal achievement. Optional re-inspection of report.html visual styling (yellow ⚠ background, green forecast background) is a polish concern, not a goal-blocker.

### Gaps Summary

**No gaps blocking goal achievement.**

The three economic questions are answerable from the report:
1. "What should I bid?" → Suggested CPC column in the enriched table + `suggested_max_cpc_micros` on every ranked row in report.json.
2. "How much will it cost?" → Budget Forecast section in report.md + `report.json["forecast"]["campaign_totals"]["daily_spend_mid_usd"]` ($66.65/day on live run).
3. "Is this vertical regulated?" → ⚠ Compliance Required blockquote above Ranked Keywords + `report.json["compliance"]` array with verification URLs (legal + medical matched on the live medical brief).

Downstream Phase 10 contract is observable: `matched_verticals[].verification_url` populated on every entry (legal: support.google.com/adspolicy/answer/2464998; medical: support.google.com/adspolicy/answer/176031). CMPL-05 (checklist reorder) is correctly deferred to Phase 10 STEP-01 per RESEARCH.md scope decision.

All 13 in-scope requirement IDs (BIDS-01..04, FRCS-01..05, CMPL-01..04) verified SATISFIED. CMPL-05 DEFERRED as designed.

---

_Verified: 2026-05-14T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
