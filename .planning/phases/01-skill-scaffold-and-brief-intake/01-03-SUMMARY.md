---
phase: 01-skill-scaffold-and-brief-intake
plan: 03
subsystem: cli
tags: [uv, pep723, python-slugify, python-dotenv, argparse, subprocess]

# Dependency graph
requires:
  - phase: 01-01
    provides: lib/io.create_run_dir, lib/io.write_brief, lib/config.load_env, lib/log.configure_logger
  - phase: 01-02
    provides: CLAUDE.md with uv run + PEP 723 conventions

provides:
  - run_init.py CLI: uv run run_init.py --slug-source "<phrase>" [--runs-root PATH] < brief.md
  - Sealed run folder: .runs/<ISO-timestamp>-<slug>/ with brief.md (verbatim) + raw/.gitkeep
  - JSON-line stdout contract: {run_dir, slug, timestamp, brief_path}
  - Exit codes: 0 success, 2 bad input, 3 filesystem/env error

affects:
  - 01-04 (SKILL.md — must quote path and parse stdout JSON)
  - All Phase 2-6 plans (write raw API responses into run_dir/raw/)

# Tech tracking
tech-stack:
  added:
    - python-slugify>=8.0 (slug derivation via PEP 723, not installed globally)
    - python-dotenv>=1.0 (env loading via PEP 723)
  patterns:
    - PEP 723 inline metadata: `# /// script` block as FIRST content of script file
    - sys.path.insert(0, str(Path(__file__).resolve().parent)) for sibling lib/ import
    - Validate inputs before all filesystem writes (slug-source, then stdin)
    - Derive slug/timestamp from run_dir.name (disk = stdout, no clock skew)
    - sys.stdin.buffer.read().decode("utf-8") for Windows CRLF-safe brief reading

key-files:
  created:
    - .claude/skills/google-ad-research/scripts/run_init.py
  modified: []

key-decisions:
  - "Derive slug and timestamp from run_dir.name rather than re-calling iso_timestamp() — guarantees stdout reflects actual on-disk folder name, including collision suffix"
  - "Validate --slug-source BEFORE reading stdin so argparse failure is first operator feedback on botched invocation"
  - "Read stdin via sys.stdin.buffer.read().decode('utf-8') — bypasses Windows CRLF translation, reads brief bytes verbatim"
  - "use_find_project_root() walk only when --runs-root not supplied; tests always supply --runs-root, keeping test isolation clean"

patterns-established:
  - "PEP 723 block is FIRST content of script file (no shebang, no leading docstring above it)"
  - "All Python CLI helpers: validate inputs before filesystem writes (exit 2), wrap IO in try/except OSError (exit 3)"
  - "SKILL.md invocation must quote the path: uv run \"${CLAUDE_SKILL_DIR}/scripts/run_init.py\" (handles spaces in operator paths)"

requirements-completed: ["SCFD-02", "SCFD-05", "INTK-04"]

# Metrics
duration: 8min
completed: 2026-05-08
---

# Phase 1 Plan 03: run_init.py Summary

**PEP 723 CLI entry point that creates sealed `.runs/<ISO-timestamp>-<slug>/` with verbatim `brief.md` + `raw/.gitkeep`, emitting one JSON line on stdout for SKILL.md to parse**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-08T03:23:39Z
- **Completed:** 2026-05-08T03:32:00Z
- **Tasks:** 2/2
- **Files modified:** 1 created

## Accomplishments

- `run_init.py` implemented with PEP 723 inline metadata — `uv run` self-provisions python-dotenv and python-slugify on first call
- All 6 `test_run_init.py` test cases flipped from RED to GREEN (happy path, verbatim brief, collision retry, empty stdin exit 2, empty slug exit 2, single JSON line)
- Smoke test confirmed: cold start ~115ms (packages already cached from lib/ plan), warm start ~300ms; `--help` exits 0 with argparse usage

## CLI Contract (for SKILL.md reference)

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" \
  --slug-source "<phrase>" \
  [--runs-root /path/to/.runs] \
  < brief.md
```

**Stdout** (exactly one JSON line):
```json
{"run_dir": "/abs/path/.runs/2026-05-08T032429Z-smoke", "slug": "smoke", "timestamp": "2026-05-08T032429Z", "brief_path": "/abs/path/.runs/2026-05-08T032429Z-smoke/brief.md"}
```

**Exit codes:**
- `0` — success
- `2` — missing/empty `--slug-source` or empty stdin
- `3` — filesystem IO error or env error

**Stderr:** `[HH:MM:SS] INFO gar: Created run folder: ...` and `[HH:MM:SS] INFO gar: Wrote brief: ...`

## PEP 723 Dependency Block (pin for SKILL.md)

```
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
```

## Smoke Test Results

| Check | Result |
|-------|--------|
| `uv run run_init.py --help` exits 0 | PASS |
| `--slug-source` flag in usage text | PASS |
| `--runs-root` flag in usage text | PASS |
| Cold-start provisioning | ~115ms (cache warm from lib/ plan) |
| Warm-start re-run | ~300ms |
| End-to-end: folder + brief.md + raw/.gitkeep | PASS |
| JSON keys: run_dir, slug, timestamp, brief_path | PASS |
| Stderr carries INFO log lines | PASS |

## Requirements Satisfied

| Requirement | Status |
|-------------|--------|
| SCFD-02: `uv run` + PEP 723 metadata recognized | SATISFIED |
| SCFD-05: run folder + brief.md + raw/ created before any API call | SATISFIED |
| INTK-04: brief written verbatim before paid API call fires | SATISFIED |

## Task Commits

1. **Task 1: Implement run_init.py with PEP 723 metadata** - `e9d1df6` (feat)
2. **Task 2: Smoke-test PEP 723 metadata via `uv run --help`** — no file modifications, smoke test only

**Plan metadata:** (final commit to follow)

## Files Created/Modified

- `.claude/skills/google-ad-research/scripts/run_init.py` — CLI entry point; 131 lines; creates sealed run folder, writes verbatim brief, emits JSON-line stdout

## Decisions Made

- Derive slug and timestamp from `run_dir.name` (not re-calling `iso_timestamp()`) — guarantees stdout reflects the actual on-disk folder name, including any `-<4hex>` collision suffix
- Validate `--slug-source` before reading stdin — so argparse/validator failure is first operator feedback on a botched invocation
- Read stdin via `sys.stdin.buffer.read().decode("utf-8")` — bypasses Windows CRLF translation, reads brief bytes verbatim
- `_find_project_root()` walk only triggered when `--runs-root` is not supplied; tests always supply `--runs-root`, keeping test isolation clean

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for this script. `.env` file optional at Phase 1 (no API keys needed); `load_env(require=())` is called for side-effect only.

## Note for SKILL.md (Plan 04)

SKILL.md MUST quote the path when invoking `run_init.py`:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" --slug-source "..." < brief.md
```

Quoted braces handle spaces in operator paths. Parse `stdout` as JSON to extract `run_dir` for subsequent steps.

## Next Phase Readiness

- `run_init.py` is complete and tested — SKILL.md (Plan 04) can hardcode the exact invocation
- Phase 2-6 plans can write raw API responses to `<run_dir>/raw/` (folder structure guaranteed by this script)
- No blockers

---
*Phase: 01-skill-scaffold-and-brief-intake*
*Completed: 2026-05-08*
