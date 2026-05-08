---
phase: 06-negatives-report-assembly-and-persistence
plan: "02"
subsystem: testing
tags: [python, markdown, escape, gfm, table, sanitize, io]

# Dependency graph
requires:
  - phase: 06-negatives-report-assembly-and-persistence
    provides: lib/io.py with iso_timestamp, slugify_brief, create_run_dir, write_brief

provides:
  - escape_md_cell() function in lib/io.py for GFM markdown table cell sanitization
  - _SMART_QUOTE_MAP translate table for smart quote + dash normalization

affects:
  - 06-03 (render_report.py uses escape_md_cell from lib.io)
  - Any future script writing GFM table cells

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "str.maketrans + str.translate() for O(n) Unicode normalization (no regex)"
    - "re.sub(r'[\\r\\n]+', ' ', s) for newline collapse"
    - "s.replace('|', '\\|') for pipe escaping in GFM cells"
    - "Truncate with Unicode ellipsis (U+2026) at max_len - 1 to keep total length <= max_len"

key-files:
  created: []
  modified:
    - .claude/skills/google-ad-research/scripts/lib/io.py

key-decisions:
  - "Used str.maketrans/_SMART_QUOTE_MAP at module level (not closure) — one-pass O(n), no regex overhead"
  - "Escape order: normalize quotes first, strip newlines second, escape pipes third, truncate last — matches Pattern 3 in research doc exactly"
  - "Truncate as s[:max_len-1] + ellipsis so final len == max_len (not max_len+1)"

patterns-established:
  - "Pattern: All GFM table cell content must pass through escape_md_cell() before tabulate call"
  - "Pattern: _SMART_QUOTE_MAP is module-level constant; reused across calls without re-building"

requirements-completed: [RPRT-04]

# Metrics
duration: 5min
completed: 2026-05-08
---

# Phase 6 Plan 02: escape_md_cell() Summary

**GFM markdown table cell sanitizer added to lib/io.py: escapes pipes, normalizes smart quotes + dashes, strips newlines, truncates with ellipsis — all 12 lib_io tests GREEN**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-08T06:52:00Z
- **Completed:** 2026-05-08T06:57:59Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `import re` to lib/io.py (previously missing)
- Added module-level `_SMART_QUOTE_MAP` with 6 Unicode mappings (left/right single, left/right double quotes, en-dash, em-dash)
- Implemented `escape_md_cell(s, *, max_len=120) -> str` following Pattern 3 from research doc exactly
- All 4 previously-skipped escape_md_cell tests now pass GREEN (pipe, smart_quotes, newline, truncate)
- Zero regressions — all 8 pre-existing lib_io tests remain GREEN (12/12 total)

## Task Commits

1. **Task 1: Add escape_md_cell() to lib/io.py** - `81957f3` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/lib/io.py` - Added `import re`, `_SMART_QUOTE_MAP`, and `escape_md_cell()` function at bottom of file

## Decisions Made

- Used module-level `_SMART_QUOTE_MAP = str.maketrans({...})` — built once at import time, reused on every call (O(n) per-call, zero overhead for map construction)
- Escape order matches research spec (Pattern 3): normalize -> strip newlines -> escape pipes -> truncate
- Truncation: `s[:max_len - 1] + "…"` ensures `len(result) == max_len` (not max_len+1), satisfying the `<=` assertion

## Deviations from Plan

None — plan executed exactly as written. Implementation matches Pattern 3 from 06-RESEARCH.md verbatim.

## Issues Encountered

- `uv run --project scripts/ -m pytest` fails (pytest not in venv). Correct invocation is `uv run --project scripts/ --with pytest pytest`. This is a pre-existing environment quirk, not introduced by this plan. The plan's verify command used `-m pytest` but the working form uses `--with pytest pytest`. All tests passed with the correct invocation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `escape_md_cell` is importable from `lib.io` — ready for `render_report.py` (06-03)
- Function signature matches the plan's interface spec exactly: `escape_md_cell(s: str, *, max_len: int = 120) -> str`
- `update_index.py` (06-05) can also use it for the industry field in INDEX.md rows

---
*Phase: 06-negatives-report-assembly-and-persistence*
*Completed: 2026-05-08*
