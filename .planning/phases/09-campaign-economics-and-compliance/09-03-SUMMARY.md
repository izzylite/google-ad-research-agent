---
phase: 09-campaign-economics-and-compliance
plan: 03
subsystem: compliance
tags: [python, regex, stdlib, word-boundary, compliance, json-sidecar, pep723]

# Dependency graph
requires:
  - phase: 09-00
    provides: "Wave 0 RED stubs — test_compliance_check.py with MODULE_MISSING guard and brief_medical.md / brief_neutral.md / ranked_with_cpc.json fixtures"
  - phase: 09-00
    provides: "references/compliance-verticals.json — operator-editable 5-vertical token data (medical / legal / finance / gambling / crypto) with verification_url + policy_note per vertical"
provides:
  - "compliance_check.py — scans brief.md (full) + top-N (default 50) ranked keywords against operator-editable vertical token lists"
  - "{run_dir}/compliance-flags.json sidecar — emitted on every successful run; empty matched_verticals[] on neutral briefs is a positive 'scan ran' signal"
  - "CMPL-05 contract for Phase 10: every matched_verticals[] entry carries a non-empty verification_url string the Next-Steps checklist can link to"
  - "Word-boundary token matcher (find_matches) blocks the 'loaner mug' false-positive on the 'loan' token while still matching 'personal loan'"
affects:
  - "09-04 (render_report.py extension) — consumes compliance-flags.json.matched_verticals[] for the CMPL-03 ⚠ Compliance Required warning block and CMPL-04 report.json compliance[] array"
  - "Phase 10 (Operator Launch Kit) — CMPL-05 contract: STEP-01 checklist reorders compliance to step 1 and links matched_verticals[].verification_url when the sidecar is non-empty"

# Tech tracking
tech-stack:
  added:
    - "stdlib re with \\b word boundary + re.escape + re.IGNORECASE for token matching (Don't Hand-Roll guidance from RESEARCH.md)"
  patterns:
    - "Two-commit TDD-style task split: Task 1 lifts MODULE_MISSING via stub main_with_args(NotImplementedError) + core logic; Task 2 replaces stub with full CLI (mirrors 09-01 bid_suggest pattern)"
    - "Data-not-code reference loader: load_verticals() reads JSON, validates schema (name + tokens + verification_url + policy_note), zero vertical-specific strings in Python source (CMPL-02 contract)"

key-files:
  created:
    - ".claude/skills/google-ad-research/scripts/compliance_check.py (322 lines including docstring; ~140 lines of executable logic)"
  modified: []

key-decisions:
  - "main_with_args stub (NotImplementedError) committed in Task 1 alongside core to lift MODULE_MISSING guard immediately — full CLI lands in Task 2 commit, preserving atomic per-task commit discipline (same precedent as 09-01 bid_suggest)"
  - "Top-N selection sorts by 'score' descending when any row has the key, else preserves input order — survives both fully-ranked v1.0 fixtures and freshly-synthesized test rows without a score field"
  - "matched_verticals[] sorted ascending by name AND evidence_tokens/brief/keywords each sorted-unique-lowercase — deterministic output unblocks future golden-file fixtures in 09-04"
  - "matched_keyword_count reuses find_matches() on each top-N keyword string rather than re-tokenizing — single source of truth for the word-boundary algorithm; per-keyword cost negligible for top_n=50"
  - "Schema-violation errors raised by load_verticals() are translated to exit 3 in main_with_args (fatal, not retryable) — operator-edited references/compliance-verticals.json with a missing key should fail fast, not silently emit empty flags"

patterns-established:
  - "Tuning-knob discipline: COMPLIANCE_SCAN_TOP_N as a module-level int constant immediately after imports, mirrors INTENT_MULTIPLIERS (09-01) and INTENT_CTRS (09-02) — operator tunes in one place"
  - "Atomic-ish sidecar write: write to .tmp suffix then .replace(out_path) — matches forecast_budget.py / bid_suggest.py so a crashed run never leaves a partially-written compliance-flags.json"

requirements-completed:
  - CMPL-01
  - CMPL-02

# Metrics
duration: ~4min
completed: 2026-05-14
---

# Phase 09 Plan 03: compliance_check Summary

**Stdlib-only word-boundary token scanner that emits compliance-flags.json sidecar — 5 starter verticals (medical/legal/finance/gambling/crypto) loaded from operator-editable JSON, zero vertical tokens hardcoded in Python.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-14T18:13:47Z
- **Completed:** 2026-05-14T18:17:44Z
- **Tasks:** 2 / 2
- **Files modified:** 1 (compliance_check.py created)

## Accomplishments

- `compliance_check.py` (PEP 723, stdlib-only) lands at 322 lines — `find_matches` + `load_verticals` + `scan` + `main_with_args` with strict word-boundary regex (`\b` + `re.escape` + `re.IGNORECASE`) blocking the "loaner" false-positive on "loan".
- 10/10 `test_compliance_check.py` tests flip from RED (MODULE_MISSING SKIP) → GREEN: word_boundary (both directions), case_insensitive, loads_from_json_reference (5 verticals × 4 required keys), scans_brief_and_keywords (medical brief), neutral_brief_no_matches (kitchenware brief), scans_top_n_only (token at rank 80 NOT picked up with top_n=50), verification_url_present_per_vertical, main_with_args_writes_compliance_flags, emits_empty_array_on_no_match.
- Full project suite remains green: **131 passed + 10 skipped** in 21.42s. No regressions in Phases 1-8 or 9-01 / 9-02.
- CMPL-02 contract verified: `grep -iE "(doctor|lawyer|casino|crypto|bitcoin|\bloan\b|medical|legal|finance|gambling|attorney|mortgage)"` against compliance_check.py finds matches ONLY in docstrings/comments — never in executable strings or assignments. Operator extends references/compliance-verticals.json with zero Python edits.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement find_matches + load_verticals + scan** — `ecc106b` (feat)
2. **Task 2: Implement main_with_args CLI + compliance-flags.json writeback** — `271240a` (feat)

_Note: Task 1 included a `main_with_args(NotImplementedError)` stub to lift the MODULE_MISSING guard in the test file — non-CLI tests passed in Task 1's commit; CLI tests passed in Task 2's commit._

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/compliance_check.py` — new stdlib-only script. Exports `COMPLIANCE_SCAN_TOP_N`, `load_verticals`, `find_matches`, `scan`, `main_with_args`. Reads `{run_dir}/brief.md` + `{run_dir}/ranked-enriched.json` + `references/compliance-verticals.json` (overridable via `--verticals-path`). Writes `{run_dir}/compliance-flags.json` atomically (.tmp + .replace).

## compliance-flags.json shape (sample evidence)

### Medical-positive (smoke test with `brief_medical.md` + `ranked_with_cpc.json`)

```json
{
  "metadata": {
    "generated_at": "2026-05-14T18:17:00Z",
    "run_id": "tmp.CVISM6X59D",
    "schema_version": "v1",
    "scanned_top_n_keywords": 50
  },
  "matched_verticals": [
    {
      "name": "medical",
      "evidence_tokens": ["clinic", "physician", "telehealth"],
      "evidence_sources": {
        "brief": ["clinic", "physician", "telehealth"],
        "keywords": []
      },
      "matched_keyword_count": 0,
      "verification_url": "https://support.google.com/adspolicy/answer/176031",
      "policy_note": "Healthcare advertisers may require LegitScript certification or country-specific licensing. Verify before launching."
    }
  ]
}
```

### Neutral-empty (smoke test with `brief_neutral.md` + cookware rows)

```json
{
  "metadata": {
    "generated_at": "2026-05-14T18:17:12Z",
    "run_id": "tmp.o1GWEUX1oO",
    "schema_version": "v1",
    "scanned_top_n_keywords": 50
  },
  "matched_verticals": []
}
```

The file is **always written** on a successful run — an empty `matched_verticals[]` is a positive signal that the scan executed, not a "missing data" signal. Phase 10 STEP-01 can rely on `compliance-flags.json` existing (or use `Path.exists()` to confirm Phase 9 ran at all).

## CMPL-05 contract for Phase 10

Every entry in `matched_verticals[]` carries:

| Field | Type | Contract |
|-------|------|----------|
| `name` | `str` | One of the 5 starter verticals or any operator-extended name; stable identifier for STEP-01 checklist text |
| `verification_url` | `str (non-empty, starts with http)` | Google Ads Policy Help Center URL — STEP-01 inserts this into the checklist's "verify policy compliance" step when the matched_verticals[] array is non-empty |
| `policy_note` | `str` | Verbatim copy of references/compliance-verticals.json `policy_note` — render_report.py CMPL-03 surfaces this in the ⚠ block |
| `evidence_tokens[]` | `list[str]` | Sorted unique lowercase tokens; lets the report explain *why* the vertical was flagged |
| `evidence_sources.brief[]` / `.keywords[]` | `list[str]` | Per-source provenance — distinguishes brief-only matches from keyword-driven matches |
| `matched_keyword_count` | `int` | How many of the top-N keywords contained any evidence token (helps the operator gauge signal strength) |

Phase 10 reorders the Next-Steps checklist so the compliance verification step is **step 1** whenever `compliance-flags.json.matched_verticals` is non-empty — the `verification_url` becomes the link target.

## CMPL-02 contract: zero hardcoded tokens

Grep verification (executable lines only — docstrings/comments unavoidable):

```
$ grep -iE "(doctor|lawyer|casino|crypto|bitcoin|\bloan\b|medical|legal|finance|gambling|attorney|mortgage)" compliance_check.py
14:    not code. NO vertical-specific tokens (medical/legal/finance/         # docstring
15:    gambling/crypto strings) appear in this Python file. Operator         # docstring
25:    "loan" must NOT match "loaner mug" — the \\b regex boundary blocks the # docstring
26:    false positive. "personal loan" (with `loan` as a whole word) DOES match. # docstring
48:    {"matched_verticals_count": N, "verticals": ["medical", ...]}         # docstring example
136:    This combination is what blocks "loaner mug" from matching the `loan` # docstring
137:    token while still matching "personal loan".                          # docstring
143:        find_matches("", ["loan"])    → []  (empty text)                  # docstring example
145:        find_matches("text", ["", "loan"]) → []  (empty token entries skipped) # docstring example
```

All hits are in docstrings or example-output strings. **No vertical-specific token data appears in executable code, dict literals, list literals, or string concatenations.** The operator can swap the 5 starter verticals for a healthcare-only deployment (or add a sixth vertical) by editing only `references/compliance-verticals.json`.

## Test Results

```
$ uv run --with pytest pytest tests/test_compliance_check.py -x -v
============================= test session starts =============================
collected 10 items

tests/test_compliance_check.py::test_word_boundary PASSED                [ 10%]
tests/test_compliance_check.py::test_word_boundary_positive PASSED       [ 20%]
tests/test_compliance_check.py::test_case_insensitive PASSED             [ 30%]
tests/test_compliance_check.py::test_loads_from_json_reference PASSED    [ 40%]
tests/test_compliance_check.py::test_scans_brief_and_keywords PASSED     [ 50%]
tests/test_compliance_check.py::test_neutral_brief_no_matches PASSED     [ 60%]
tests/test_compliance_check.py::test_scans_top_n_only PASSED             [ 70%]
tests/test_compliance_check.py::test_verification_url_present_per_vertical PASSED [ 80%]
tests/test_compliance_check.py::test_main_with_args_writes_compliance_flags PASSED [ 90%]
tests/test_compliance_check.py::test_emits_empty_array_on_no_match PASSED [100%]

============================= 10 passed in 0.20s ==============================

$ uv run --with pytest --with respx --with python-dotenv --with python-slugify --with tabulate pytest tests/
====================== 131 passed, 10 skipped in 21.42s =======================
```

## Decisions Made

- **Top-N selection algorithm**: sort by `score` descending when ANY row has the key, else preserve input order — survives both Phase-1..8 fixtures (with score) and freshly-synthesized test rows without a score field. Python's sort is stable so ties preserve input order.
- **matched_keyword_count uses find_matches recursively**: rather than re-tokenizing or building a substring index, count each top-N keyword that contains any evidence token via the same word-boundary regex. Per-keyword cost is negligible for the default top_n=50 and avoids drift between two different matching algorithms.
- **Schema-violation as exit 3**: ValueError raised by load_verticals when references/compliance-verticals.json has a missing key is mapped to exit 3 (fatal, not retryable) so operator-edited token data with a typo fails fast rather than silently emitting an empty matched_verticals[].
- **`--verticals-path` flag added for test isolation**: lets pytest point at fixture copies without touching the canonical references/ tree. Default resolves to skill-root/references/compliance-verticals.json via `Path(__file__).resolve().parent.parent`.

## Deviations from Plan

None — plan executed exactly as written. All success criteria met:

- [x] compliance_check.py implemented (PEP 723, stdlib-only — `dependencies = []`)
- [x] All 10 tests in tests/test_compliance_check.py pass (flipped from MODULE_MISSING SKIP)
- [x] {run_dir}/compliance-flags.json written with matched_verticals[] array (even when empty)
- [x] Word-boundary regex blocks "loaner" false positive on "loan" (test_word_boundary GREEN)
- [x] Scans full brief.md + top-N (default 50) keywords from ranked-enriched.json (test_scans_top_n_only GREEN — rank-80 keyword NOT picked up)
- [x] Loads vertical token lists from references/compliance-verticals.json (CMPL-02 — zero hardcoded tokens grep verified)
- [x] Empty matched_verticals[] on neutral brief (test_neutral_brief_no_matches + test_emits_empty_array_on_no_match GREEN)
- [x] No regression — full suite 131 passed + 10 skipped
- [x] Each task committed atomically (Task 1: ecc106b, Task 2: 271240a)

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. compliance_check.py is pure-compute, stdlib-only, reads/writes only files inside the run-folder + the in-repo references/.

## Next Phase Readiness

- **09-04 (render_report.py extension) unblocked**: compliance-flags.json sidecar shape locked in. render_report.py needs to (a) auto-detect via `Path.exists()` (Pattern 1 from RESEARCH.md), (b) render the CMPL-03 ⚠ block above the Ranked Keywords table when `matched_verticals` is non-empty, (c) extend `build_report_json` with the CMPL-04 `compliance[]` array.
- **Phase 10 STEP-01 contract documented**: matched_verticals[].verification_url is the contract Phase 10 will consume to reorder the Next-Steps checklist compliance-first. Phase 9 emits the data; Phase 10 consumes it (per RESEARCH.md scope boundary).
- **No blockers.**

## Self-Check: PASSED

- compliance_check.py exists: FOUND
- Task 1 commit (ecc106b): FOUND
- Task 2 commit (271240a): FOUND
- All 10 compliance_check tests GREEN
- Full suite 131 passed + 10 skipped (no regressions)
- CMPL-02 grep clean (no hardcoded vertical tokens in executable code)

---
*Phase: 09-campaign-economics-and-compliance*
*Completed: 2026-05-14*
