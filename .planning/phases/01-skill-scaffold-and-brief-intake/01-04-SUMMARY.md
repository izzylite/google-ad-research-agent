---
phase: 01-skill-scaffold-and-brief-intake
plan: 04
subsystem: skill-prompt
tags: [claude-code-skill, brief-intake, run-init, uv, pep-723]

# Dependency graph
requires:
  - phase: 01-skill-scaffold-and-brief-intake
    plan: 03
    provides: run_init.py CLI contract frozen — slug-source flag, stdin brief, stdout JSON shape

provides:
  - SKILL.md operator-facing prompt with 5-step Phase 1 brief-intake workflow
  - Required-field loop (industry, product, location, language, audience)
  - Conditional optional field solicitation (budget, geo-excl, lang-excl, brand terms, competitor URLs)
  - run_init.py invocation wired to "${CLAUDE_SKILL_DIR}/scripts/run_init.py"
  - Hard Phase 1 STOP — no signal collection in this skill version
affects:
  - 02-signal-collection
  - plan-05-validation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-step constraint design: each workflow step ends with a 'Do not advance unless...' gate (Pitfall 17 mitigation)"
    - "Trigger-gated optional fields: conditional solicitation prevents operator noise overload"
    - "SKILL.md line cap: 162 lines of 500-line hard cap — extract to references/ if cap approached"

key-files:
  created:
    - .claude/skills/google-ad-research/SKILL.md
  modified: []

key-decisions:
  - "SKILL.md quotes ${CLAUDE_SKILL_DIR} in run_init.py invocation — handles spaces in operator paths (Windows C:/Users/Some Name/)"
  - "Phase 1 ends with hard STOP at Step 5 — no Phase 2 signal collection wired yet; future skill update replaces Step 5"
  - "Operator trigger phrases front-loaded in description field — 'keyword research', 'Google Ads research', 'PPC keywords', 'ad group clusters' ensure auto-load on brief paste"
  - "Brief rendered via Write tool to OS temp file before piping to run_init.py — avoids shell quoting issues with multiline briefs"

patterns-established:
  - "Pattern: SKILL.md workflow as numbered checklist with per-step gates — prevents prompt drift"
  - "Pattern: Treat 'n/a', 'tbd', 'you decide', 'any' as EMPTY — enforces minimum brief schema (Pitfall 1 / INTK-02)"

requirements-completed: [SCFD-01, INTK-01, INTK-02, INTK-03]

# Metrics
duration: 4min
completed: 2026-05-08
---

# Phase 1 Plan 04: SKILL.md Summary

**5-step conversational brief-intake skill prompt with per-step gates, required-field loop, conditional optional fields, and hardwired run_init.py handoff at 162 lines**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-08T03:27:23Z
- **Completed:** 2026-05-08T03:31:00Z
- **Tasks:** 1/1
- **Files modified:** 1 created

## Accomplishments

- Authored `SKILL.md` at `.claude/skills/google-ad-research/SKILL.md` — 162 lines, well within the 100-300 Phase 1 target and 500-line hard cap
- Frontmatter `description` (375 chars) front-loads operator trigger phrases ("keyword research", "Google Ads research", "PPC keywords", "ad group clusters") for Claude Code skill auto-discovery
- 5-step workflow: capture brief → validate 5 required fields → conditional optional fields → render + invoke run_init.py → hard STOP
- Each of the 5 steps ends with a "Do not advance..." gate — Pitfall 17 (skill prompt drift) mitigation
- Required-field validation loop treats "n/a", "tbd", "you decide", "any", "?" as empty — enforces minimum brief schema (INTK-02)
- Optional fields (budget, geo exclusions, language exclusions, brand terms, competitor URLs) solicited only when brief triggers fire (INTK-03)
- run_init.py invocation uses quoted `"${CLAUDE_SKILL_DIR}/scripts/run_init.py"` with `--slug-source` and stdin pipe — matches frozen CLI contract from Plan 03
- Step 5 hard-STOPs Phase 1 with explicit "do NOT call Serper or Tavily, do not invoke WebSearch" directive

## Task Commits

1. **Task 1: Author SKILL.md with frontmatter + Phase 1 workflow** — `6c2ef43` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `.claude/skills/google-ad-research/SKILL.md` — Operator-facing skill prompt: YAML frontmatter (description + allowed-tools), 5-step Phase 1 workflow, brief template, run_init.py invocation, anti-patterns, tool reference

## Decisions Made

- SKILL.md quotes `${CLAUDE_SKILL_DIR}` in the run_init.py invocation — handles Windows paths with spaces (operator paths like `C:\Users\Some Name\`)
- Phase 1 ends with hard STOP at Step 5 — signal collection (Phase 2) will replace Step 5 in a future skill update; no Phase 2 stubs added now
- Operator trigger phrases front-loaded in the `description` field — ensures Claude Code auto-loads the skill when an operator pastes a campaign brief
- Brief rendered to OS temp file via Write tool before piping to run_init.py — avoids multiline shell quoting issues

## run_init.py Invocation (frozen contract)

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" --slug-source "{product field value}" < "/tmp/gar-brief.md"
```

Stdout JSON contract:
```json
{"run_dir": "<abs path>", "slug": "<derived slug>", "timestamp": "<iso>", "brief_path": "<abs path to brief.md>"}
```

Exit codes: 0 = ok, 2 = empty slug-source or empty stdin, 3 = filesystem/env error.

## Requirements Status

- **SCFD-01** — Skill installed at `.claude/skills/google-ad-research/` with `SKILL.md`: SATISFIED
- **INTK-01** — Skill prompts operator for campaign brief in chat: SATISFIED (Step 1)
- **INTK-02** — 5 required fields validated with re-prompt loop: SATISFIED (Step 2)
- **INTK-03** — Optional fields solicited only when relevant: SATISFIED (Step 3)

Manual smoke checks (1-D-01 through 1-D-04 in VALIDATION.md) deferred to Plan 05 sign-off.

## Deviations from Plan

None — plan executed exactly as written. SKILL.md content follows the exact structure specified in the plan task action block.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for Phase 1 SKILL.md.

## Next Phase Readiness

- Phase 1 infrastructure complete: lib/ package (Plans 01-02), CLAUDE.md conventions (Plan 02), run_init.py (Plan 03), SKILL.md (Plan 04)
- Plan 05 (validation / smoke tests) is the final Phase 1 gate — manual VALIDATION.md checks 1-D-01 through 1-D-04
- After Plan 05 sign-off, Phase 2 signal collection can begin — Phase 2 will replace Step 5 of SKILL.md with signal-collection workflow

---
*Phase: 01-skill-scaffold-and-brief-intake*
*Completed: 2026-05-08*
