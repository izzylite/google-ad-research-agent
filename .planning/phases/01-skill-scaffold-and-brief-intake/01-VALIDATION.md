---
phase: 1
slug: skill-scaffold-and-brief-intake
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (provisioned via PEP 723 `--with pytest`, no project-level dep) |
| **Config file** | None — Wave 0 ships ad-hoc `scripts/tests/`; promote to `pyproject.toml` in Phase 2 |
| **Quick run command** | `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/test_run_init.py -x` |
| **Full suite command** | `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| **Estimated runtime** | ~10 seconds full suite, ~3 seconds quick |

---

## Sampling Rate

- **After every task commit:** Run targeted test file for the task's deliverable (~2-3s)
- **After every plan wave:** Run full suite (~10s)
- **Before `/gsd:verify-work`:** Full suite green + every manual-only smoke ticked off
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-A-01 | A | 1a | SCFD-04 (lib package) | unit | `pytest scripts/tests/test_lib_io.py -x` | ❌ W0 | ⬜ pending |
| 1-A-02 | A | 1a | SCFD-04 (config loader) | unit | `pytest scripts/tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 1-A-03 | A | 1a | SCFD-03 (env contract) | smoke | `git check-ignore .env && git ls-files .env.example` | ✅ | ⬜ pending |
| 1-B-01 | B | 1b | SCFD-05 (run folder + brief.md) | unit | `pytest scripts/tests/test_run_init.py::test_creates_run_folder -x` | ❌ W0 | ⬜ pending |
| 1-B-02 | B | 1b | SCFD-05 (collision suffix) | unit | `pytest scripts/tests/test_run_init.py::test_collision_retry -x` | ❌ W0 | ⬜ pending |
| 1-B-03 | B | 1b | INTK-04 (verbatim brief) | unit | `pytest scripts/tests/test_run_init.py::test_brief_written_verbatim -x` | ❌ W0 | ⬜ pending |
| 1-B-04 | B | 1b | SCFD-02 (uv run + PEP 723) | smoke | `uv run "$CLAUDE_SKILL_DIR/scripts/run_init.py" --help` exits 0 | ❌ W1b | ⬜ pending |
| 1-C-01 | C | 1a | (SCFD-03 audit) | smoke | `cat .gitignore .env.example` validates required entries present | ✅ | ⬜ pending |
| 1-C-02 | C | 1a | (Project conventions) | manual | Root `CLAUDE.md` documents skill location + `uv run` rule + SKILL.md ≤500 lines | ❌ W1a | ⬜ pending |
| 1-D-01 | D | 2 | SCFD-01 (skill folder) | smoke | `test -f .claude/skills/google-ad-research/SKILL.md && test -d .claude/skills/google-ad-research/scripts` | ❌ W2 | ⬜ pending |
| 1-D-02 | D | 2 | INTK-01 (skill discovery) | manual | Fresh CC session — paste a brief, confirm `google-ad-research` activates | ❌ W2 | ⬜ pending |
| 1-D-03 | D | 2 | INTK-02 (required-field loop) | manual | Paste brief omitting `audience`; skill re-prompts; refuses to advance. Repeat for each of 5 required fields. | ❌ W2 | ⬜ pending |
| 1-D-04 | D | 2 | INTK-03 (optional fields) | manual | Brief mentioning budget → skill asks budget follow-up. Brief without → skill does NOT ask. | ❌ W2 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Test infrastructure must exist before any unit test command runs. Files Wave 0 creates:

- [ ] `.claude/skills/google-ad-research/scripts/tests/__init__.py` — empty package marker
- [ ] `.claude/skills/google-ad-research/scripts/tests/conftest.py` — shared fixtures (`tmp_runs_root`, `sample_brief_text`)
- [ ] `.claude/skills/google-ad-research/scripts/tests/test_run_init.py` — stubs for SCFD-05, INTK-04
- [ ] `.claude/skills/google-ad-research/scripts/tests/test_lib_io.py` — stubs for SCFD-04 (`slugify_brief`, `iso_timestamp`, `create_run_dir`)
- [ ] `.claude/skills/google-ad-research/scripts/tests/test_config.py` — stubs for SCFD-03 (`load_env`, REQUIRED_KEYS, find_dotenv walk)

Pytest itself is sourced via `--with pytest` on the `uv run` invocation — no project-level dep added.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Skill auto-loads from chat | INTK-01 | Only verifiable via Claude Code's actual skill discovery; not unit-testable | Fresh CC session in repo. Paste: "research keywords for our same-day grocery delivery launch in the UK" — confirm `google-ad-research` activates |
| Required-field loop | INTK-02 | LLM behavior in SKILL.md prompt; not unit-testable | Paste a one-line brief omitting `audience`. Confirm skill asks for it; refuses to advance. Repeat omitting each of 5 required fields. |
| Optional-field conditional ask | INTK-03 | Prompt-conditional behavior depends on LLM | Paste brief mentioning a budget → skill asks budget follow-up. Paste brief without budget → skill does NOT ask budget. |
| Pre-API folder seal | SCFD-05 + INTK-04 | Half automatable (`pytest`) but final visual confirmation needs full intake flow | Complete intake flow once; confirm `.runs/<ts>-<slug>/brief.md` and empty `raw/` exist before any paid API stage would fire |
| Root `CLAUDE.md` quality | (none formally) | Documentation quality is judgmental | Read root `CLAUDE.md`; verify it states: skill location, `uv run` invocation rule, SKILL.md size cap, .env handling. ≤30 lines. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
