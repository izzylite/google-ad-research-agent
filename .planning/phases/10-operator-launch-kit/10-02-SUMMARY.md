---
phase: 10-operator-launch-kit
plan: 02
status: complete
completed: 2026-05-14
self_check: PASSED
---

# Plan 10-02 — Summary

## Objective

Extend `render_report.py` with Next Steps checklist (STEP-01..04) + CMPL-05
compliance reorder. Single source of truth: `render_next_steps_section()`
returns `(markdown, step_list)` consumed by report.md, report.json, HTML.

## Shipped

| Artifact | Status |
|----------|--------|
| `_STANDARD_NEXT_STEPS_TEMPLATE` constant | locked 8-step template |
| `render_next_steps_section()` | 80-line helper |
| `build_report_json` `next_steps` kwarg | w/ internal fallback computation |
| HTML `<section id="next-steps">` | container |
| `renderNextSteps()` JS function | checkboxes w/ localStorage |
| `gar_${slug}_step_${id}` namespacing | cross-run isolation |

## CMPL-05 contract

Compliance present → ONE combined verification step prepended at position 1.
Multi-vertical → `Names1 + Names2 verification at URL1; URL2 ...`.
Step numbers derive from final list position (never hardcoded).

Live smoke (Lake Worth medical run): step 1 = "Complete Legal + Medical
verification at https://support.google.com/adspolicy/answer/2464998;
https://support.google.com/adspolicy/answer/176031 before launching."

## Verification

- 34 render_report tests pass (2 EXPT-05 skips for Wave 3)
- Full suite: 163 passing, zero regressions

## Self-Check: PASSED

Commit: `76abfca` feat(10-02)
