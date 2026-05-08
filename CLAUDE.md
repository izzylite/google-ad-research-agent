# Google Ad Research Agent — Claude Code Context

A Claude Code skill that turns one campaign brief into campaign-ready Google Ads
keyword research: ranked keyword tables, ad-group clusters, competitor ad copy,
and tiered negative keyword lists. Single internal operator. Markdown-first
deliverable. Filesystem-only — no server, no UI.

## Skill location

The skill lives at `.claude/skills/google-ad-research/`. Project-scoped (committed
with this repo, not personal-scoped under `~/.claude/skills/`).

- `SKILL.md` — operator-facing prompt and workflow checklist.
- `scripts/` — Python helpers, invoked from SKILL.md via `Bash(uv run ...)`.
- `scripts/lib/` — shared package: `config.py`, `io.py`, `log.py` (Phase 1);
  `http.py` lands in Phase 2.
- `scripts/tests/` — pytest unit + smoke tests; no `pyproject.toml` until Phase 2.
- `references/` — progressive-disclosure rubrics loaded on demand by SKILL.md.

## Conventions (NON-NEGOTIABLE)

- **Always run Python helpers via `uv run`.** Never `pip install`. Each script
  declares dependencies in PEP 723 inline metadata (`# /// script` block).
  Claude Code's Bash tool starts a fresh shell every call — venvs do not persist.
- **`SKILL.md` must stay ≤500 lines.** If it grows past 500, extract rubrics into
  `.claude/skills/google-ad-research/references/<name>.md` and load them on demand.
  Per-step constraint design (each step has its own "do not advance unless..."
  gate) beats global blob rules.
- **Secrets only via `.env`.** Loaded by `lib/config.py` through `python-dotenv`
  with `override=False` (OS exports win). API keys NEVER appear in CLI args, in
  run folders, in stdout/stderr, or in this repo outside `.env`. `.env.example`
  is committed; `.env` is git-ignored.
- **Run isolation.** Every research run lands in a sealed `.runs/<ISO-timestamp>-<slug>/`
  folder containing `brief.md`, `raw/`, `report.md`, `report.json`. No cross-run
  mutable state. No caching in v1.

## Run the tests

```bash
uv run --with pytest --with python-dotenv --with python-slugify \
  pytest .claude/skills/google-ad-research/scripts/tests/ -x
```

Phase 1 runs ad-hoc (no `pytest.ini`); Phase 2 promotes to a proper pyproject.toml.

## Run-folder retention

`.runs/*/raw/` is git-ignored — raw API responses are local debugging artifacts.
Recommend purging `raw/` subfolders older than 30 days (not enforced in v1).

## Where to look first

- Architecture: `.planning/research/ARCHITECTURE.md`
- Stack & versions: `.planning/research/STACK.md`
- Phase status: `.planning/STATE.md`, `.planning/ROADMAP.md`
- Active phase: `.planning/phases/<NN>-<slug>/`
