# Phase 12 — Deferred Items

Out-of-scope discoveries logged during Phase 12 execution.

## test_config.py::test_required_keys_defined

**Status:** RED (pre-existing failure from Plan 12-01)

**Failure:**
```
assert "TAVILY_API_KEY" in REQUIRED_KEYS
AssertionError: assert 'TAVILY_API_KEY' in ('SERPER_API_KEY',)
```

**Origin:** Plan 12-01 stripped `TAVILY_API_KEY` from `lib/config.py:REQUIRED_KEYS`
but did not update this Phase 1 test. Acknowledged in `12-02-SUMMARY.md` as
"Plan 12-01 territory or a Plan 12-05 final-gate cleanup."

**Why deferred from Plan 12-04:** This test failure pre-dates Plan 12-04 and lives
in `test_config.py` (Phase 1 SCFD config validation), not in any file owned by
Plan 12-04. Per the executor's scope-boundary rule, only failures directly caused
by the current task's changes are auto-fixed. This is a Plan 12-01 leftover.

**Recommended fix (1-line):** In `test_config.py:12`, replace
`assert "TAVILY_API_KEY" in REQUIRED_KEYS` with
`assert "TAVILY_API_KEY" not in REQUIRED_KEYS` (or delete the assertion). Plan
12-05 closes residuals.

---

*Logged: 2026-05-15 (Plan 12-04 execution)*
