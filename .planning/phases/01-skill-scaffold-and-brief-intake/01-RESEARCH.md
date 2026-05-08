# Phase 1: Skill Scaffold and Brief Intake — Research

**Researched:** 2026-05-08
**Domain:** Claude Code skill scaffolding (`.claude/skills/google-ad-research/`), PEP 723 / `uv` Python helpers, conversational brief intake, dated run-folder layout
**Confidence:** HIGH (skill conventions, PEP 723, folder layout) / MEDIUM (intake-loop pattern — verified design but only validated in real use post-Phase 1)

---

## Summary

Phase 1 builds the foundation under every later phase: the skill folder shape, the secrets contract, the run-folder convention, the `scripts/lib/` package, and a conversational brief intake that refuses to advance until five required fields are non-empty. No paid API call fires until a sealed `.runs/<ISO-timestamp>-<slug>/` exists on disk with a verbatim `brief.md`.

The big technical risks for this phase are (1) Claude Code's stateless Bash sessions making `pip install` / venv activation painful — solved by `uv run` + PEP 723 inline metadata so each helper script provisions its own environment per call (cached after first run), (2) skill prompt drift from a sprawling SKILL.md — solved by a strict per-step checklist structure with explicit "do not advance unless..." gates, and (3) operator-pasted briefs being too thin to drive useful research — solved by an explicit five-field validation loop that re-prompts (rather than degrading) when fields are missing.

**Primary recommendation:** Build the skill folder + lib/ + run_init.py + .env wiring in parallel (Wave 1). Wire SKILL.md last (Wave 2) once `run_init.py`'s CLI contract is fixed, so the SKILL.md can hardcode the exact invocation. Defer `lib/http.py` to Phase 2 — Phase 1 has no HTTP calls.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

No `CONTEXT.md` exists for Phase 1. No upstream `/gsd:discuss-phase` was run. The constraints below are inherited from the **roadmap-locked decisions** in `STATE.md` § Decisions and `ROADMAP.md` Phase 1 success criteria, treated as locked for this phase.

### Locked Decisions (from STATE.md / ROADMAP.md / PROJECT.md)

- **Claude Code skill (not standalone app)** — operator already lives in Claude Code; second runtime adds no value.
- **Skill location:** `.claude/skills/google-ad-research/` (project-scoped, committed with the repo). Not `~/.claude/skills/` (personal-scoped).
- **`uv run` + PEP 723 inline metadata** for all Python helper scripts — no shared `requirements.txt`, no venv activation in the Bash tool's stateless shell.
- **Secrets via `.env` + `python-dotenv`** — `.env` git-ignored, `.env.example` committed. Keys NEVER passed as CLI args, NEVER written to disk in run folders.
- **Conversational brief intake** (not structured form) — skill loops on 5 mandatory fields: industry, product, location, language, audience.
- **Optional fields solicited only when relevant**: budget, geo exclusions, language exclusions, brand terms, competitor URLs.
- **Run folder isolation** — each run = sealed dated folder `.runs/<ISO-timestamp>-<slug>/`. No cross-run mutable state. No caching in v1.
- **Phase 1 must address Pitfalls 1, 9, 17, 19, 20** (per SUMMARY.md):
  - Pitfall 1: Thin brief / GIGO — enforce required fields
  - Pitfall 9: API key leakage — env-only contract
  - Pitfall 17: Skill prompt drift — top-level SKILL.md < 500 lines, per-step constraints
  - Pitfall 19: Run folder bloat — `.gitignore` covers `.runs/*/raw/` from day 1
  - Pitfall 20: Inconsistent briefs — required-field gate enforces minimum schema

### Claude's Discretion

- Exact ISO-timestamp format (UTC vs local; precision; collision suffix)
- Slug derivation rule (which brief field(s) seed the slug; transliteration approach)
- `brief.md` internal layout (frontmatter + prose vs prose-only)
- Whether `lib/http.py` and `lib/log.py` are stubbed in Phase 1 or deferred to Phase 2 (recommendation: defer `http.py`, ship a minimal `log.py` now)
- Run-folder name: `.runs/` (current decision per ROADMAP) — confirmed locked
- Frontmatter `paths` glob to scope skill activation — optional, recommended off in v1 (skill should activate from any directory in the repo)

### Deferred Ideas (OUT OF SCOPE)

- Cost-ceiling / pre-run spend confirmation (PROJECT.md: out of scope)
- Cross-run inheritance (`--brief-from runs/.../brief.yaml`) — Pitfall 20 mitigation deferred to v2; v1 only enforces per-run schema
- `keyring` / OS credential manager (deferred to v2)
- MCP server (out of scope per STACK.md: stateless `uv run` is the pattern)
- Volume / CPC API (v2)
- Vertical presets (v2)
- Multi-locale fan-out (v2)
- v2 ranking weight tuning, intent rubric calibration — irrelevant to Phase 1 scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| **SCFD-01** | Skill installed at `.claude/skills/google-ad-research/` with `SKILL.md` and `scripts/` subfolder | § Claude Code Skill Folder Layout (verified against code.claude.com/docs/en/skills) |
| **SCFD-02** | Python helper scripts run via `uv run` with PEP 723 inline dependency metadata | § PEP 723 Inline Script Metadata (verified against PEP 723 + docs.astral.sh) |
| **SCFD-03** | API keys (Serper, Tavily) loaded from `.env` via python-dotenv; `.env` git-ignored, `.env.example` committed | § Secret Loading Contract (existing `.env`/`.env.example`/`.gitignore` already match) |
| **SCFD-04** | `scripts/lib/` package provides shared HTTP client (httpx + retry), config loader, IO helpers, structured logging | § scripts/lib/ Package Shape — Phase 1 scope (recommend: ship `config.py`, `io.py`, `log.py`; defer `http.py` to Phase 2) |
| **SCFD-05** | `run_init.py` creates dated run folder `.runs/<ISO-timestamp>-<slug>/` containing `brief.md`, `raw/` subfolder | § run_init.py Specifics (CLI contract, exit codes, stdout/stderr split, slug rules) |
| **INTK-01** | Skill prompts operator for campaign brief in chat; operator pastes free-form context | § Conversational Brief Intake (SKILL.md prompt structure with explicit intake checklist) |
| **INTK-02** | Skill validates 5 required fields (industry, product, location, language, audience); loops until all non-empty | § Brief Validation Loop (prompt-side validation with re-prompt; canonical "INTAKE COMPLETE" sentinel before run_init.py runs) |
| **INTK-03** | Skill solicits optional fields (budget, geo/language exclusions, brand terms, competitor URLs) when relevant | § Optional Field Solicitation (only ask when brief mentions a trigger or after required fields are complete) |
| **INTK-04** | Validated brief saved verbatim to `brief.md` in run folder before any paid API call | § brief.md Format & Verbatim-Save Contract (run_init.py reads brief from stdin / temp file, writes verbatim) |
</phase_requirements>

---

## Standard Stack

### Core (Phase 1 only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13.x or 3.14.x | Runtime for `run_init.py` and `lib/` modules | 3.13 is the safe floor; 3.14 (Oct 2025) is current production. Inherited from STACK.md decision. |
| `uv` | 0.11.11+ (May 2026) | Script runner + Python manager; reads PEP 723 inline metadata | One Rust binary; cold-start ~150ms after first run; eliminates venv-activation pain in Claude Code's stateless Bash sessions. Inherited from STACK.md. |
| `python-dotenv` | 1.0.x | Load `SERPER_API_KEY` + `TAVILY_API_KEY` from `.env` at module import | Standard 12-factor secrets. `override=False` lets OS env vars win. No new alternatives have displaced it as of May 2026. |
| `python-slugify` | 8.x | Slugify brief fields into folder-safe names (e.g., `Same-Day Grocery Delivery` → `same-day-grocery-delivery`) | Handles Unicode transliteration cleanly; widely-used; alternative is hand-rolling regex which gets edge cases wrong. |
| stdlib `logging` | (stdlib) | Stderr-only operator-facing logs from `run_init.py` | Phase 1 has no per-run JSON log handler yet (deferred to Phase 2 once API failures need structured logging). Plain `logging.basicConfig(level=logging.INFO, stream=sys.stderr)` suffices. |
| stdlib `pathlib`, `datetime`, `re`, `argparse`, `json` | (stdlib) | Folder creation, timestamp, slug normalization, CLI parsing, structured stdout | `run_init.py` is pure stdlib + dotenv + slugify. No HTTP, no third-party APIs. |

### NOT Needed Yet (Defer to Later Phases)

| Library | When | Why Defer |
|---------|------|-----------|
| `httpx` | Phase 2 | Phase 1 makes zero HTTP calls. Adding `lib/http.py` now means writing untested code for unknown retry/auth requirements. |
| `tavily-python` | Phase 2 | Same — no Tavily call in Phase 1. |
| `pydantic` | Phase 2 or 3 | Phase 1's data shape is just the brief (5 strings + a few optional strings). `dict` is fine. Pydantic earns its weight when ≥3 cross-script JSON contracts exist. |
| `tabulate` | Phase 6 | No tables rendered in Phase 1. |
| `rich` (`RichHandler`) | Optional Phase 1, mandatory Phase 2 | Nice-to-have for colored CLI output. Not blocking. Can be added in Phase 2 alongside HTTP work. |
| `respx` (httpx mocking) | Phase 2 testing | No HTTP to mock in Phase 1. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff / Rejected Because |
|------------|-----------|-----------------------------|
| `uv` + PEP 723 | `pip install -r requirements.txt` + venv | Claude Code's Bash tool starts a fresh shell every invocation; venv activation does NOT persist. Operator hits "ModuleNotFoundError" repeatedly. **Rejected — Architecture-blocking.** |
| `python-slugify` | Hand-rolled `re.sub(r"[^a-z0-9]+", "-", ...)` | Unicode transliteration gets messy ("café" → "caf"? "cafe"?). Fine for ASCII-only English briefs but fails on real operator input. **Use python-slugify.** |
| stdlib `logging` | `loguru` / `structlog` | Phase 1 only logs to stderr from one script. Stdlib is enough. Defer richer logging to Phase 2. |
| `argparse` | `click` / `typer` | `run_init.py` has 1-2 args. argparse is stdlib. Click adds value once a script has subcommands or multi-flag UX, neither of which Phase 1 has. |
| ISO 8601 with seconds (`2026-05-08T143024Z`) | Date-only (`2026-05-08`) | Multiple runs in one day collide. Seconds resolution + UTC + a slug is collision-resistant for any single operator. |
| UTC | Local time | UTC is unambiguous for sorting and avoids DST surprises. Operator may be confused at first ("why does my 3pm run say T1500Z?"); a one-line README note covers it. |

### Installation (operator one-time)

```powershell
# Windows
winget install --id=astral-sh.uv -e
uv python install 3.13

# Verify
uv --version              # expect 0.11.x or newer
uv python list            # confirm 3.13 installed
```

No project-wide `pip install` step. Each helper script declares its own deps in its PEP 723 header; `uv run` provisions and caches.

---

## Architecture Patterns

### Recommended Phase-1 Project Structure

```
google-ad-research-agent/
├── .claude/
│   └── skills/
│       └── google-ad-research/
│           ├── SKILL.md                    # operator-facing prompt (target ≤300 lines in Phase 1)
│           ├── references/                 # progressive-disclosure docs (empty in Phase 1; populated Phase 3+)
│           │   └── intake-checklist.md     # OPTIONAL — extracted required-field rubric if SKILL.md grows
│           └── scripts/
│               ├── run_init.py             # CREATES run folder + writes brief.md
│               ├── lib/
│               │   ├── __init__.py         # marks lib/ as importable package
│               │   ├── config.py           # load_env() — locates .env via parents-walk; raises if keys missing
│               │   ├── io.py               # slugify_brief(), write_brief(), iso_timestamp()
│               │   └── log.py              # configure_logger() — stderr-only, INFO level default
│               └── (http.py deferred to Phase 2)
├── .runs/                                  # gitignored except brief.md/report.md (raw/ ignored)
│   └── 2026-05-08T143024Z-same-day-grocery-delivery/
│       ├── brief.md                        # verbatim operator brief
│       └── raw/                            # empty in Phase 1; populated Phase 2+
├── .env                                    # ALREADY EXISTS, git-ignored, contains real keys
├── .env.example                            # ALREADY EXISTS, committed
├── .gitignore                              # ALREADY EXISTS, covers .env, .runs/*/raw/
└── .planning/                              # GSD planning artifacts (not touched by Phase 1)
```

**Files already in place (do NOT recreate):**
- `.env` (with real `TAVILY_API_KEY` and `SERPER_API_KEY`)
- `.env.example` (committed template)
- `.gitignore` (covers `.env`, `.runs/*/raw/`, `__pycache__/`)
- Master git branch initialized

**Phase 1 net-new files:**
- `.claude/skills/google-ad-research/SKILL.md`
- `.claude/skills/google-ad-research/scripts/run_init.py`
- `.claude/skills/google-ad-research/scripts/lib/__init__.py`
- `.claude/skills/google-ad-research/scripts/lib/config.py`
- `.claude/skills/google-ad-research/scripts/lib/io.py`
- `.claude/skills/google-ad-research/scripts/lib/log.py`
- (Optional) `.claude/skills/google-ad-research/references/intake-checklist.md`
- (Optional) `CLAUDE.md` at repo root noting the skill

### Pattern 1: Skill Prompt as Orchestrator, Scripts as Tools

**What:** `SKILL.md` is the conductor. It walks Claude through phases as a checklist; invokes scripts via Bash for deterministic work; reasons directly for judgement work. Scripts know nothing about each other — they read CLI args, write to disk, exit. Phase 1 has exactly one script (`run_init.py`) and zero LLM-judgement work in code.

**When to use:** Every Claude Code skill that combines LLM reasoning with deterministic file/HTTP I/O. Canonical pattern from Anthropic skill best-practices.

**Phase-1 application:**
- SKILL.md owns: brief intake dialogue, required-field validation, optional-field solicitation
- `run_init.py` owns: timestamp, slug derivation, folder creation, brief.md write
- Boundary: `run_init.py` accepts the brief content; it does NOT validate fields. Validation happens in the SKILL.md prompt before invocation.

**Source:** [Skill authoring best practices — Anthropic](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

### Pattern 2: SKILL.md Frontmatter as Discovery Contract

**What:** YAML frontmatter at the top of `SKILL.md` controls when Claude auto-loads the skill. The `description` field drives skill triggering — Claude reads it (truncated at 1,536 chars) when deciding whether to invoke. Optional `allowed-tools` pre-approves tool use to avoid permission prompts. `name` is optional (directory name is used by default). Source: [code.claude.com/docs/en/skills § Frontmatter reference](https://code.claude.com/docs/en/skills).

**Phase-1 frontmatter recommendation:**

```yaml
---
description: Run keyword research for a Google Ads campaign — produces a ranked keyword table, ad-group clusters, competitor ad copy, and negative keyword candidates from a campaign brief. Use when the operator asks for "keyword research", "Google Ads research", "PPC keywords", "ad group clusters", or pastes a campaign brief.
allowed-tools: Bash(uv run *) Read Write WebSearch
---
```

**Why these fields:**
- `description`: trigger phrases at the front (operator-spoken language: "keyword research", "Google Ads research", "PPC keywords"). Avoids generic phrasing. The 1,536-char cap on combined `description + when_to_use` is enforced; aim for ~300-400 chars for the intent + 200 chars of trigger phrases.
- `allowed-tools`: pre-approves `uv run *` (so the operator doesn't get a permission prompt on every script call), plus `Read`, `Write`, and `WebSearch` (Phase 2 use). Listing `Bash(uv run *)` rather than blanket `Bash` keeps the principle-of-least-privilege intact.
- **Omit `name`** — directory name `google-ad-research` is used automatically.
- **Omit `paths`** — skill should activate from any directory in the project, not only when editing certain files.
- **Omit `disable-model-invocation`** — we DO want Claude to auto-load when the operator pastes a brief.

### Pattern 3: `${CLAUDE_SKILL_DIR}` for Path Resolution

**What:** Claude Code substitutes `${CLAUDE_SKILL_DIR}` in skill content with the directory containing `SKILL.md`. Use it in every `uv run` invocation so paths resolve regardless of which working directory the operator is in. Source: [code.claude.com/docs/en/skills § Available string substitutions](https://code.claude.com/docs/en/skills).

**Phase-1 invocation pattern (in SKILL.md):**

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" --brief-stdin
```

**Why this matters:**
- The operator might be in repo root, in a subfolder, or in `~/Documents`. Hardcoding `.claude/skills/...` breaks when CWD ≠ repo root.
- `${CLAUDE_SKILL_DIR}` is the *only* documented way to reference skill-bundled scripts robustly.
- Forward slashes work on Windows in `uv run`'s argument parsing; no need to switch to backslashes. **Do quote the path** because `Documents` paths often contain spaces on Windows (`C:\Users\Some Name\...`).

### Pattern 4: PEP 723 Inline Script Metadata

**What:** Each helper script declares its dependencies in a top-of-file comment block. `uv run` reads the block, provisions an isolated environment (cached after first run), and executes. No `requirements.txt`. No venv activation.

**Phase-1 `run_init.py` header:**

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
"""Initialize a sealed run folder with verbatim brief.md.

Reads the brief from stdin (or --brief-file PATH).
Writes:
  .runs/<ISO-timestamp>-<slug>/brief.md       (verbatim, no edits)
  .runs/<ISO-timestamp>-<slug>/raw/.gitkeep   (empty raw/ subfolder)

Stdout: single JSON object with run_dir absolute path and slug
Stderr: human-readable progress messages
Exit codes: 0 ok, 2 missing slug-source, 3 io error
"""
```

**Why these versions:**
- `python-dotenv>=1.0` — stable since 2023; no breaking changes through 2026.
- `python-slugify>=8.0` — current major; v8 cleaned up Unicode handling.

**Cold-start cost:**
- First `uv run`: ~3-8s (Python download if 3.13 missing, dep resolution, env build).
- Subsequent `uv run` (same script unchanged): ~150-300ms (cache hit, only Python startup).
- Cache location on Windows: `%LOCALAPPDATA%\uv\cache` (default; verified via `uv cache dir`).

**Lockfile (optional, recommended):** Run `uv lock --script run_init.py` once after the script's deps stabilize. Produces `run_init.py.lock` adjacent to the script. Reproducibility win; not blocking for Phase 1.

**Source:** [PEP 723 — Inline script metadata](https://peps.python.org/pep-0723/) and [docs.astral.sh/uv/guides/scripts](https://docs.astral.sh/uv/guides/scripts/).

### Pattern 5: SKILL.md Phase Checklist with Hard Gates

**What:** SKILL.md walks Claude through Phase 1 of the run as a numbered checklist. Each step has an explicit "do not advance unless..." gate. This is the canonical mitigation for Pitfall 17 (skill prompt drift / instruction overrun) per [How to Stop Claude Code Skills from Drifting (DEV Community)](https://dev.to/akari_iku/how-to-stop-claude-code-skills-from-drifting-with-per-step-constraint-design-2ogd) — per-step constraint design beats global blob rules.

**Phase-1 SKILL.md skeleton:**

```markdown
# Google Ad Research

[1-paragraph mission statement]

## Workflow

### Step 1: Capture the brief

Ask the operator to paste a campaign brief. Free-form prose is fine.

After they paste, extract these five required fields:
1. **industry** — what sector / vertical (e.g., "online groceries")
2. **product** — what specific product/service this campaign promotes
3. **location** — country/region targeted (e.g., "UK", "London", "US-California")
4. **language** — primary search language (e.g., "en-GB")
5. **audience** — who the campaign targets (e.g., "households 25-45 in metro areas")

**Do not advance to Step 2 if any of the five required fields is empty, "n/a", "tbd", or "you decide".**
Re-prompt with: "I still need {missing fields}. What should I use?"

### Step 2: Solicit optional fields (only when relevant)

Ask follow-ups for these optional fields ONLY when the brief mentions a trigger:
- **budget** — ask if brief mentions cost, scale, or spend ceiling
- **geo exclusions** — ask if brief targets a region with known sub-market overlap (e.g., UK excluding Northern Ireland)
- **language exclusions** — ask if location is multilingual (e.g., Belgium, Switzerland)
- **brand terms** — ask if brief names the brand or competitors
- **competitor URLs** — ask if brief names competitors but not URLs

Skip an optional field silently if no trigger fires. Don't ask all five every time.

### Step 3: Save the brief

When all required fields are non-empty, render the full brief as plain markdown
(see template below) and save it via run_init.py.

Run:
```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" --slug-source "{product}"
```

Then pipe the rendered brief markdown to stdin of run_init.py (use Write tool to put
it in a temp location, or use heredoc if shell supports it).

run_init.py prints a JSON line to stdout containing:
  {"run_dir": "<absolute path>", "slug": "<derived-slug>", "timestamp": "<iso>"}

Capture the run_dir for downstream phases.

**Do not proceed to Phase 2 (signal collection) if the JSON line is missing or run_dir
does not exist on disk.**

### Brief template (rendered before run_init.py)

```markdown
# Campaign Brief

**Captured:** {iso_timestamp_local}

## Required

- **Industry:** {industry}
- **Product:** {product}
- **Location:** {location}
- **Language:** {language}
- **Audience:** {audience}

## Optional

{only include fields that were filled; omit empty optional fields entirely}
- **Budget:** {budget}
- **Geo exclusions:** {geo_exclusions}
- **Language exclusions:** {language_exclusions}
- **Brand terms:** {brand_terms}
- **Competitor URLs:** {competitor_urls}

## Raw operator paste

> {verbatim original brief, indented as blockquote}
```
```

**Why this structure:**
- Numbered, gated steps prevent the LLM from "helpfully" skipping ahead with assumptions.
- Re-prompt language is explicit so Claude doesn't default to "I'll guess based on context" (which is what Pitfall 1 is).
- The "Do not advance unless..." line is the per-step constraint; one per step.
- Total length target: 200-300 lines for Phase 1 SKILL.md. Phases 2-6 will add their own steps.

### Anti-Patterns to Avoid

- **Hardcoded API keys in SKILL.md or scripts.** Skill folder is committed; keys leak. Always env-only.
- **Brief intake that requires a pre-filled template file.** PROJECT.md mandates conversational intake. The structured `brief.md` is an *output* of intake, not an input.
- **`pip install` from inside Bash tool calls.** Stateless shell; venv doesn't persist; constant fights. Use `uv run`.
- **Writing the brief BEFORE all required fields are validated.** A half-validated brief on disk gives later phases something to read; the gate must come BEFORE `run_init.py`.
- **Generating a folder name from the timestamp alone (no slug).** `2026-05-08T143024Z` is not human-scannable; operators need to recognize past runs by name. Always slug-suffix.
- **Putting the slug AHEAD of the timestamp.** `same-day-grocery-2026-05-08T143024Z` doesn't sort chronologically. Always `<timestamp>-<slug>`.
- **`run_init.py` printing free-form prose to stdout.** SKILL.md needs to parse the run_dir; stdout must be a single JSON object. Logs go to stderr.
- **Embedding the operator's brief into the `run_init.py` CLI args** (e.g., `--brief "<huge text>"`). Shell escaping nightmare. Use stdin or a temp file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Locating `.env` from a script that lives in `.claude/skills/google-ad-research/scripts/` | Hand-rolled `Path(__file__).parents[N]` walk that breaks if folder depth changes | `lib/config.py` with `find_dotenv()` from `python-dotenv` (walks up to repo root automatically) | `find_dotenv()` returns the path or empty string; documented since dotenv 0.21; survives folder restructuring. |
| Slugifying campaign names with Unicode/punctuation | `re.sub(r"[^a-z0-9]+", "-", name.lower())` | `python-slugify` (`from slugify import slugify`) | Unicode transliteration ("café" → "cafe", "naïve" → "naive"), edge-case handling (consecutive separators, leading/trailing dashes, max length), well-tested. |
| ISO 8601 timestamps with timezone | Hand-rolled `datetime.now().strftime(...)` | `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")` (stdlib) | This one *is* hand-rolled — but with the right format string from stdlib. The trap is forgetting `timezone.utc` and getting naive timestamps. **Lock format in `lib/io.py:iso_timestamp()`.** |
| Required-field validation | Custom regex-y "is this empty?" checks | Plain Python `all(brief[f].strip() for f in required)` in the SKILL.md prompt | This is *prompt-side* validation — not a script function. Claude reads each field and asks if any is empty/n/a/tbd. No code needed. |
| Reading `brief.md` content from stdin in `run_init.py` | `sys.stdin.read()` directly | Same — but wrapped: `sys.stdin.buffer.read().decode("utf-8")` to avoid Windows CR/LF surprises | Plain `sys.stdin.read()` is correct on POSIX but on Windows can introduce `\r\n` artifacts. Reading bytes + explicit UTF-8 decode is safer. |

**Key insight:** Phase 1 has surprisingly few "don't hand-roll" temptations because it's mostly stdlib + dotenv + slugify. The discipline is to *not* prematurely abstract — `lib/config.py` should be ~30 lines, not a full settings framework.

---

## Common Pitfalls

These are the five Phase 1 owns from PITFALLS.md, plus three Phase-1-specific ones surfaced during this research.

### Pitfall 1 (PITFALLS.md): Thin brief / GIGO

**What goes wrong:** Operator pastes a one-liner ("Run keywords for our same-day grocery delivery"). Skill produces a 200-keyword report dominated by generic terms. Looks complete; PPC manager wastes a week before realizing framing was wrong.

**Why it happens:** LLMs produce plausible output from sparse input. Operators under pressure skip clarifying questions or answer "you decide".

**How Phase 1 prevents it:**
- SKILL.md Step 1 explicitly tracks five required fields and refuses to advance if any is empty.
- "you decide" / "n/a" / "tbd" are treated as empty (re-prompt fires).
- `brief.md` is written verbatim, including a blockquote of the original raw paste, so audit trail survives.

**Warning signs:**
- Brief.md shorter than 5 non-blank lines.
- More than two required fields say "not specified" — should be impossible if gate is wired correctly.
- Operator skipped clarifying-question turn.

**Verification:** Smoke test in VALIDATION.md — paste a one-line brief, confirm skill re-prompts at least once.

### Pitfall 9 (PITFALLS.md): API key leakage in run-history files

**What goes wrong:** Run folder contains a debug log or shell command echo with `--serper-key=abc123` or env-dumped headers. Operator commits run folder to git; key leaks.

**Why it happens:** Debug-friendly logging dumps request objects. Convenience scripts hardcode keys "just for now". Stack traces include header fragments.

**How Phase 1 prevents it:**
- Hard contract: keys read from `os.environ` only, after `load_dotenv()`. Never from CLI args. Never written to disk.
- `lib/config.py` is the *only* module that touches `os.environ['SERPER_API_KEY']` or `os.environ['TAVILY_API_KEY']` (Phase 2+ enforces).
- `run_init.py` does NOT read or log API keys (it doesn't need them).
- `.gitignore` already covers `.env` and `.runs/*/raw/`.
- `brief.md` template excludes any system-environment dump — only operator-provided fields.

**Warning signs:**
- Any file in `.runs/` contains a string longer than 24 chars of mixed alphanumeric (high-entropy heuristic).
- `git status` shows `.env` staged.
- Stack trace in any `.runs/<run>/` file contains the substring `SERPER_API_KEY` or `TAVILY_API_KEY`.

**Verification:** Smoke test — `grep -rEi "([A-Za-z0-9+/]{32,}|tvly-)" .runs/` should return nothing inside any run folder. Also `git status` after creating a run should show no staged secrets.

### Pitfall 17 (PITFALLS.md): Skill prompt drift / instruction overrun

**What goes wrong:** SKILL.md grows over months — every fixed bug adds a "do X" line, every misbehaviour adds a "never do Y". After 6 months it's 3000 lines, the LLM ignores the middle, behaviour regresses on edge cases.

**Why it happens:** One-skill-one-job rule violated as features accrete. Negative instructions accumulate without dedup. Context rot sets in.

**How Phase 1 prevents it:**
- Top-level SKILL.md target: ≤300 lines for Phase 1 (≤500 lines through Phase 6).
- Per-step constraint design: each step has its own "do not advance unless..." gate, not a global blob.
- `references/*.md` is the escape valve — once SKILL.md exceeds 500 lines, extract rubrics into referenced files loaded only when needed.
- Phase 1 leaves `references/` empty (or just `intake-checklist.md` if SKILL.md grows). Phases 3+ will populate it heavily (intent rubric, clustering rules, negatives baseline).
- Add a Phase-1 line-count assertion to CLAUDE.md: "SKILL.md must stay ≤500 lines; if it exceeds, extract a reference."

**Warning signs:**
- SKILL.md > 500 lines after Phase 1.
- Same behavior rule restated in two different phrasings (e.g., "always pass `gl`/`hl`" + "remember to set the locale" — pick one).
- New rule contradicts an existing one.

**Verification:** `wc -l .claude/skills/google-ad-research/SKILL.md` ≤ 500. Listed in VALIDATION.md.

### Pitfall 19 (PITFALLS.md): Run folder bloat

**What goes wrong:** After 6 months, `.runs/` has 500 dated subfolders, each 5-50MB of raw API responses. Repo size 20GB; clone takes 10 minutes; grep slow.

**Why it happens:** Every run dumps raw Serper + Tavily JSON. No retention policy. Run folders committed to git instead of `.gitignored`.

**How Phase 1 prevents it:**
- `.gitignore` already covers `.runs/*/raw/` and `.runs/*/.tmp/` (verified — see § Already-In-Place Artifacts).
- Folder naming is `<ISO-timestamp>-<slug>` so chronological sort is automatic; old runs are obvious.
- Phase 1 leaves `raw/` empty — created with a `.gitkeep` so the folder exists for Phase 2 to write into.
- Retention policy is documented in CLAUDE.md (recommend purging `raw/` after 30 days; not enforced in v1).

**Warning signs:**
- `git status` after a run shows `.runs/<run>/raw/*.json` staged.
- Repo > 100MB after 50 runs.
- A single run folder > 100MB.

**Verification:** Smoke test — create a run, run `git status`, confirm `.runs/` is not staged. ISO format check via regex on folder name.

### Pitfall 20 (PITFALLS.md): Inconsistent briefs across operator sessions

**What goes wrong:** Even with one operator, briefs drift in detail — Monday is exhaustive, Friday is two lines. Reports are wildly different quality. Comparison across runs is meaningless.

**Why it happens:** Conversational intake permits "good enough" answers. No template enforcement.

**How Phase 1 prevents it:**
- Five required fields are enforced (no "good enough" — all five non-empty before run_init.py runs).
- `brief.md` template is fixed: required fields always present, optional fields shown only when filled.
- Verbatim raw-paste blockquote at the bottom captures the original framing for audit.
- v2 inheritance (`--brief-from <prior-run>`) is deferred but the brief.md format is stable enough to support it later.

**Warning signs:**
- Brief.md files vary 5× in line count across same-campaign runs.
- Two consecutive runs of the same campaign produce different cluster structures unexpectedly.

**Verification:** Smoke test — create two runs with the same brief; confirm both `brief.md` files have identical structure (frontmatter + required + raw paste sections).

### New Pitfall (Phase-1-specific): Folder-name collisions on rapid re-runs

**What goes wrong:** Operator runs the skill twice in the same second (rare but possible if `run_init.py` is part of a quick re-test loop). Both runs derive the same `<timestamp>-<slug>` folder name; second run overwrites first.

**Why it happens:** Seconds-resolution timestamp is not unique across same-second invocations.

**How to avoid:**
- ISO timestamp with seconds is *almost always* unique for human-paced operation. Add a 4-char random hex suffix only on collision (`mkdir` returns `FileExistsError` → retry with `-<4-hex>` appended).
- Alternative: millisecond resolution (`%Y-%m-%dT%H%M%S_%fZ` with `[:-3]` truncation) but this clutters folder names.
- **Recommendation:** Seconds + collision-retry loop. Cleaner names; correctness preserved.

**Verification:** Edge-case test — manually call `run_init.py` twice in a tight loop; confirm both succeed and produce different folders.

### New Pitfall (Phase-1-specific): SKILL.md frontmatter description not triggering discovery

**What goes wrong:** Operator types "research keywords for our launch" and Claude does not load the skill. Invokes WebSearch directly instead.

**Why it happens:** `description` in SKILL.md frontmatter is too generic, doesn't match natural operator phrasing, or is truncated (combined `description + when_to_use` is capped at 1,536 chars in the skill listing).

**How to avoid:**
- Lead the description with concrete operator phrases ("keyword research", "Google Ads research", "PPC keywords", "ad group clusters"), not abstract capability prose.
- Keep description under ~400 chars total — leaves room for `when_to_use` and avoids the 1,536-char truncation cliff.
- Test discovery explicitly in VALIDATION.md: ask Claude "What skills are available?" and confirm `google-ad-research` appears with full description.

**Verification:** Smoke test — fresh Claude Code session; ask "research keywords for [brief]"; confirm skill auto-loads. Listed in VALIDATION.md.

### New Pitfall (Phase-1-specific): `${CLAUDE_SKILL_DIR}` not resolving in nested Bash invocations

**What goes wrong:** `${CLAUDE_SKILL_DIR}` is substituted by Claude Code before the bash command runs, but if the SKILL.md uses it inside a heredoc or a `bash -c "..."`, the variable may not expand correctly on Windows.

**Why it happens:** Some Windows shell configurations don't preserve quoting around variable substitution.

**How to avoid:**
- Always quote the path: `"${CLAUDE_SKILL_DIR}/scripts/run_init.py"` — handles spaces in `Documents` paths.
- Don't nest the variable inside heredocs — use it only at the top level of the bash command.
- Test with a path that contains spaces (the actual project path is `C:\Users\Izzy\Documents\Projects\google-ad-research-agent` — no spaces, but operators on other machines may have spaces).

**Verification:** Smoke test — `uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" --help` runs successfully from any CWD.

---

## Code Examples

### Example 1: SKILL.md frontmatter (Phase 1 minimum)

```yaml
---
description: Run Google Ads keyword research from a campaign brief — produces ranked keyword tables, ad-group clusters, competitor ad copy, and negative keyword lists. Use when the operator says "keyword research", "Google Ads research", "PPC keywords", "ad group clusters", or pastes a campaign brief mentioning industry/product/location/language/audience.
allowed-tools: Bash(uv run *) Read Write WebSearch
---
```

**Source pattern:** [code.claude.com/docs/en/skills § Frontmatter reference](https://code.claude.com/docs/en/skills) (verified May 2026).

### Example 2: PEP 723 inline metadata for run_init.py

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
"""run_init.py — create sealed run folder + write brief.md verbatim.

CLI:
    uv run run_init.py --slug-source "<product or industry phrase>" < brief.md

Stdout (single JSON line):
    {"run_dir": "<abs path>", "slug": "...", "timestamp": "..."}

Exit codes:
    0  ok
    2  --slug-source missing or empty
    3  filesystem io error
"""
```

**Source pattern:** [PEP 723](https://peps.python.org/pep-0723/) (verified). Format is exactly: `# /// script` opener, one or more `# field = value` lines, `# ///` closer. Single space after the `#`.

### Example 3: lib/config.py — env loading

```python
"""lib/config.py — locate and load .env from project root."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

REQUIRED_KEYS = ("SERPER_API_KEY", "TAVILY_API_KEY")  # Phase 2+ uses; Phase 1 can skip the assertion


def load_env(*, require: tuple[str, ...] = ()) -> Path:
    """Walk up from this file until a .env is found; load it; return its path.

    Phase 1 callers can pass `require=()` (default) since run_init.py needs no API keys.
    Phase 2+ scripts pass `require=("SERPER_API_KEY",)` etc. to fail fast on missing keys.
    """
    dotenv_path = find_dotenv(usecwd=False, raise_error_if_not_found=False)
    if not dotenv_path:
        # Fall back to walking up from this file
        for parent in Path(__file__).resolve().parents:
            candidate = parent / ".env"
            if candidate.exists():
                dotenv_path = str(candidate)
                break
    if dotenv_path:
        load_dotenv(dotenv_path, override=False)  # OS env wins
    missing = [k for k in require if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required env vars: {', '.join(missing)}. "
            f"Check .env or shell exports."
        )
    return Path(dotenv_path) if dotenv_path else Path()
```

**Source pattern:** [python-dotenv on GitHub](https://github.com/theskumar/python-dotenv) — `find_dotenv()` walks up the directory tree; `override=False` lets shell exports win.

### Example 4: lib/io.py — slugify + timestamp + folder creation

```python
"""lib/io.py — filesystem + naming helpers."""
from __future__ import annotations
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from slugify import slugify


def iso_timestamp() -> str:
    """UTC ISO 8601, seconds resolution, filesystem-safe.

    Returns e.g. "2026-05-08T143024Z" (no colons — Windows-safe).
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def slugify_brief(slug_source: str, *, max_length: int = 60) -> str:
    """Convert an arbitrary brief phrase into a filesystem-safe slug.

    Empty / whitespace-only input → ValueError (caller should exit 2).
    """
    if not slug_source or not slug_source.strip():
        raise ValueError("slug_source is empty")
    slug = slugify(slug_source, max_length=max_length, word_boundary=True, save_order=True)
    if not slug:
        raise ValueError(f"slug_source {slug_source!r} produced empty slug")
    return slug


def create_run_dir(runs_root: Path, *, slug_source: str) -> Path:
    """Create .runs/<ts>-<slug>/ + raw/.gitkeep ; return absolute path.

    Retries with a 4-hex suffix on collision (rapid re-run within same second).
    """
    runs_root.mkdir(parents=True, exist_ok=True)
    ts = iso_timestamp()
    slug = slugify_brief(slug_source)
    base = f"{ts}-{slug}"
    run_dir = runs_root / base
    attempts = 0
    while attempts < 5:
        try:
            run_dir.mkdir(parents=False, exist_ok=False)
            break
        except FileExistsError:
            suffix = secrets.token_hex(2)  # 4 chars
            run_dir = runs_root / f"{base}-{suffix}"
            attempts += 1
    else:
        raise OSError(f"Could not create unique run dir under {runs_root}")
    raw_dir = run_dir / "raw"
    raw_dir.mkdir()
    (raw_dir / ".gitkeep").write_bytes(b"")
    return run_dir.resolve()


def write_brief(run_dir: Path, brief_text: str) -> Path:
    """Write brief.md verbatim. Returns the path."""
    brief_path = run_dir / "brief.md"
    brief_path.write_text(brief_text, encoding="utf-8", newline="\n")
    return brief_path
```

**Notes:**
- `%Y-%m-%dT%H%M%SZ` (no colons) sidesteps Windows path issues — Windows treats `:` as drive separator and forbids it in filenames. Verified via Microsoft Learn filesystem reference.
- `secrets.token_hex(2)` = 4 hex chars = 65k-collision-resistant suffix.
- `newline="\n"` forces LF line endings on Windows so brief.md content is byte-identical regardless of OS.
- `slug-source` is the **product** or **industry** field from the brief — recommend passing `product` (more specific). SKILL.md picks.

### Example 5: lib/log.py — minimal stderr logging

```python
"""lib/log.py — single-handler stderr logger for Phase 1.

Phase 2+ adds a per-run JSON sidecar handler.
"""
from __future__ import annotations
import logging
import sys


def configure_logger(name: str = "gar", level: int = logging.INFO) -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log  # idempotent across re-imports
    log.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    log.addHandler(handler)
    log.propagate = False
    return log
```

### Example 6: run_init.py — full script

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
"""run_init.py — create sealed run folder + write brief.md verbatim."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Add lib/ to path (script lives in scripts/, lib/ is sibling)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.config import load_env  # noqa: E402
from lib.io import create_run_dir, write_brief, iso_timestamp  # noqa: E402
from lib.log import configure_logger  # noqa: E402

log = configure_logger()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a sealed run folder.")
    parser.add_argument("--slug-source", required=True,
                        help="Phrase to derive the slug from (typically the brief's 'product' field)")
    parser.add_argument("--runs-root", default=None,
                        help="Override default .runs/ location (mostly for tests)")
    args = parser.parse_args()

    try:
        load_env(require=())  # Phase 1: no API keys required
    except EnvironmentError as e:
        log.error(str(e))
        return 3

    # Determine project root: walk up until we find .git or .planning/ or .env
    here = Path(__file__).resolve()
    project_root: Path | None = None
    for parent in here.parents:
        if (parent / ".git").exists() or (parent / ".planning").exists():
            project_root = parent
            break
    if project_root is None:
        log.error("Could not locate project root (no .git or .planning/ found above this script)")
        return 3

    runs_root = Path(args.runs_root) if args.runs_root else (project_root / ".runs")

    # Read brief from stdin
    brief_text = sys.stdin.buffer.read().decode("utf-8")
    if not brief_text.strip():
        log.error("Empty brief on stdin")
        return 2

    if not args.slug_source.strip():
        log.error("--slug-source is empty")
        return 2

    try:
        run_dir = create_run_dir(runs_root, slug_source=args.slug_source)
        brief_path = write_brief(run_dir, brief_text)
    except (ValueError, OSError) as e:
        log.error(f"Failed to initialize run dir: {e}")
        return 3

    log.info(f"Created run folder: {run_dir}")
    log.info(f"Wrote brief: {brief_path}")

    # Single JSON line to stdout — what SKILL.md parses
    print(json.dumps({
        "run_dir": str(run_dir),
        "slug": run_dir.name.split("-", 5)[-1],  # everything after timestamp
        "timestamp": iso_timestamp(),
        "brief_path": str(brief_path),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Notes:**
- Brief comes from **stdin**, not `--brief` CLI arg — avoids shell-escaping pain and supports arbitrarily long briefs.
- `--slug-source` IS a CLI arg because it's a short single-line phrase.
- `sys.path.insert(0, str(Path(__file__).resolve().parent))` lets the script find `lib/` as a sibling. Alternative: package the scripts and run via `python -m`. CLI arg approach is simpler for a skill that just needs to fire `uv run path/to/script.py`.

### Example 7: SKILL.md invocation block (Phase 1 Step 3)

```markdown
### Step 3: Save the brief

Render the brief markdown using the template above. Then save it via run_init.py.

Use the Write tool to put the rendered brief in a temp location (e.g., `/tmp/brief-{timestamp}.md`).
Then run:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" --slug-source "{product}" < /tmp/brief-{timestamp}.md
```

(On Windows, use `%TEMP%\brief-{timestamp}.md` and the same `<` redirection in bash.)

The script prints a single JSON line on stdout. Parse it to get:
  - `run_dir` — absolute path to the new run folder
  - `slug` — derived slug
  - `timestamp` — UTC ISO timestamp
  - `brief_path` — absolute path to the saved brief.md

Capture `run_dir` for downstream phases.

If the script exits non-zero or stdout is empty/non-JSON, STOP and surface the stderr to the operator. Do not advance to Phase 2.
```

### Example 8: .gitignore additions (verify already in place)

```
# Already in .gitignore (verified):
.env
.env.local
*.key
__pycache__/
*.pyc
.uv/
.claude/settings.local.json
.runs/*/raw/
.runs/*/.tmp/
```

The existing `.gitignore` already covers Phase 1 needs. **No additions required.** Verification step in VALIDATION.md confirms.

---

## State of the Art

### What changed recently (relevant to Phase 1)

| Old Approach | Current Approach (May 2026) | When Changed | Impact for Phase 1 |
|--------------|------------------------------|--------------|---------------------|
| `pip install -r requirements.txt` + venv | `uv run` + PEP 723 inline metadata | uv 0.4 (mid-2024); PEP 723 stabilized 2024 | **Critical** — only `uv run` works reliably in Claude Code's stateless Bash. |
| Custom commands at `.claude/commands/*.md` | Skills at `.claude/skills/<name>/SKILL.md` | Late 2025 / early 2026 — Anthropic merged commands into skills | **Adopt skills.** Old `.claude/commands/` files keep working but skills get supporting files + frontmatter + auto-loading. |
| `name` field required in SKILL.md frontmatter | `name` is optional (directory name used by default) | 2026 | Drop `name`. Saves a line and one source of drift. |
| `keyring` recommended for API keys | `python-dotenv` standard for single-operator tools | Stable since 2023 | Use `.env` (already done). Revisit `keyring` only if multi-operator. |
| `requests` ubiquitous | `httpx` increasingly default (sync API match + async option) | 2023+ | Phase 2 uses httpx. Phase 1 has no HTTP, so moot here. |

### Deprecated / outdated patterns

- **`python setup.py install` / `pip install -e .`** for skill scripts: deprecated. Use PEP 723 inline metadata.
- **`.claude/commands/*.md` for new work:** still supported but skills are the recommended pattern (per Anthropic docs as of May 2026). Existing commands keep working.
- **Dating folder names with colons (`2026-05-08T14:30:24Z`):** breaks on Windows (colon is path separator). Always strip colons → `T143024Z`.
- **Hardcoding `name:` in SKILL.md frontmatter just to match directory name:** redundant; the docs explicitly say it defaults to directory name. Leaving it in invites drift if the directory is renamed.

---

## Open Questions

1. **Should Phase 1 stub `lib/http.py` to lock the retry contract early, or wait until Phase 2?**
   - What we know: STACK.md and ARCHITECTURE.md both call for `httpx + urllib3.Retry` in Phase 2. Phase 1 does not need it.
   - What's unclear: writing untested stub code now risks the stub's API not matching Phase 2's actual needs (e.g., async vs sync, retry tuning, header injection).
   - **Recommendation:** **Defer.** Ship `lib/__init__.py`, `config.py`, `io.py`, `log.py` in Phase 1. Add `http.py` in Phase 2 as the first task. SCFD-04 says "scripts/lib/ package provides shared HTTP client" — this can be satisfied across Phases 1+2 since Phase 1 has no HTTP.
   - **If planner disagrees:** the stub should be exactly: `def get_session() -> httpx.Client: raise NotImplementedError("Phase 2")`. Anything more is speculative.

2. **Should `brief.md` use YAML frontmatter or plain markdown?**
   - What we know: PITFALLS.md Pitfall 20 mentions "save as both prose (for the LLM) and structured YAML (for diffing across runs)" as a v2 enhancement — for v1, plain prose is fine.
   - What's unclear: whether downstream phases (Phase 2 reads `brief.md` for locale fields) parse the markdown or re-prompt Claude to extract fields.
   - **Recommendation:** Plain markdown with bold-labeled fields ("**Industry:** value"). Phase 2 can either grep for these labels or have Claude re-read brief.md and extract. No YAML frontmatter in v1 — keeps brief.md operator-readable. Phase 6's `report.json` provides the structured-twin pattern; brief stays human-first.

3. **Does the skill need a `paths:` glob in frontmatter to scope activation?**
   - What we know: `paths` limits when Claude auto-loads the skill based on which files the operator is editing.
   - What's unclear: this skill should activate from anywhere in the repo (or even when the operator isn't editing any file — pure chat-driven).
   - **Recommendation:** **Omit `paths`** — skill should be globally available within the project. Add `paths` only if discovery becomes too noisy in v2.

4. **Should `run_init.py` accept `--brief-file PATH` in addition to stdin?**
   - What we know: SKILL.md needs to pass a multi-line markdown brief to the script. Stdin works but requires the SKILL.md to emit `< brief.md` shell syntax.
   - What's unclear: whether Claude Code's Bash tool reliably handles `<` redirection on Windows.
   - **Recommendation:** Support both. `--brief-file PATH` as primary (Claude writes the brief via the Write tool, then passes the path). `< stdin` as fallback. Costs ~5 LOC; eliminates Bash-redirection edge cases.

5. **Should the project gain a root `CLAUDE.md` in Phase 1?**
   - What we know: No `CLAUDE.md` exists at project root. Anthropic docs recommend one for project-wide context. Phase 1 is the first time we have anything to put in it.
   - What's unclear: whether Phase 1 should write `CLAUDE.md` or defer to a later phase.
   - **Recommendation:** **Yes — write a minimal root `CLAUDE.md` in Phase 1.** Content: 1) repo purpose (1 paragraph from PROJECT.md), 2) where the skill lives (`.claude/skills/google-ad-research/`), 3) "always use `uv run`, never `pip install`", 4) "SKILL.md must stay ≤500 lines; extract to references/ if larger". Keeps future Claude sessions on-rails without operator re-explaining context every time.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (will be installed via PEP 723 in test-runner script, not as project dep) |
| Config file | None — Phase 1 uses ad-hoc smoke tests run via `uv run`, no `pytest.ini` yet |
| Quick run command | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_run_init.py -x` |
| Full suite command | `uv run --with pytest pytest .claude/skills/google-ad-research/scripts/tests/ -x` |

**Rationale for ad-hoc / no-config approach:** Phase 1 has exactly one script under test (`run_init.py`) plus a tiny `lib/`. A full pytest config + conftest.py is overhead. By Phase 2 (when `serp_fetch.py` and `tavily_extract.py` ship with HTTP mocking), promote to `pyproject.toml` with pytest config. Phase 1's job is to NOT block on infrastructure that doesn't exist yet.

**Manual / smoke checks** are the primary verification mode for Phase 1 — most requirements are observable behaviors (skill discovery, folder creation on disk) rather than pure-Python unit-testable functions. Listed below.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| **SCFD-01** | Skill folder exists at `.claude/skills/google-ad-research/` with `SKILL.md` and `scripts/` | smoke (filesystem assertion) | `test -f .claude/skills/google-ad-research/SKILL.md && test -d .claude/skills/google-ad-research/scripts` | Manual smoke / single bash assertion |
| **SCFD-02** | `uv run` runs `run_init.py` successfully with PEP 723 metadata | smoke (subprocess) | `uv run "${CLAUDE_SKILL_DIR}/scripts/run_init.py" --help` exits 0 | Manual smoke |
| **SCFD-03** | `.env` is git-ignored; `.env.example` is committed; required keys load via `python-dotenv` | smoke + unit | `git check-ignore .env` exits 0; `git ls-files .env.example` returns the file; `uv run --with python-dotenv python -c "from dotenv import load_dotenv; load_dotenv(); import os; assert os.environ.get('TAVILY_API_KEY')"` | Existing files; tests live in `scripts/tests/test_config.py` (Wave 0) |
| **SCFD-04** | `scripts/lib/` package importable; provides `config`, `io`, `log` (and future `http`) | unit | `uv run --with python-dotenv --with python-slugify python -c "from scripts.lib import config, io, log; assert callable(io.slugify_brief)"` | `scripts/tests/test_lib_io.py` (Wave 0) |
| **SCFD-05** | `run_init.py` creates `.runs/<ISO>-<slug>/brief.md` + empty `raw/` | unit + smoke | `pytest scripts/tests/test_run_init.py::test_creates_run_folder -x` plus a manual smoke (paste a brief, run skill, `ls .runs/`) | `scripts/tests/test_run_init.py` (Wave 0) |
| **INTK-01** | Skill auto-loads when operator pastes a brief | manual-only | Fresh Claude Code session: paste "research keywords for our same-day grocery delivery launch in the UK" — confirm `google-ad-research` activates. Justification: only verifiable by Claude Code's actual skill discovery, not unit-testable. | Manual smoke (VALIDATION.md) |
| **INTK-02** | Skill loops when required field missing | manual-only | Paste a one-line brief omitting `audience`. Confirm skill asks for it; refuse to advance. Repeat for each of 5 required fields. Justification: validates LLM behavior in SKILL.md prompt; not unit-testable. | Manual smoke (VALIDATION.md) |
| **INTK-03** | Skill solicits optional fields only when relevant | manual-only | Paste brief mentioning a budget — confirm skill asks budget follow-up. Paste brief without budget mention — confirm skill does NOT ask. Justification: prompt-conditional behavior. | Manual smoke (VALIDATION.md) |
| **INTK-04** | `brief.md` saved verbatim BEFORE any paid API call | unit + manual | `pytest scripts/tests/test_run_init.py::test_brief_written_verbatim` (compares stdin bytes to file bytes). Manual: complete intake flow, confirm `brief.md` exists before Phase 2 step would fire. | `scripts/tests/test_run_init.py` (Wave 0) |

### Sampling Rate

- **Per task commit:** Run the targeted test file for the task's deliverable. E.g., after lib/io.py changes: `uv run --with pytest --with python-slugify pytest scripts/tests/test_lib_io.py -x` (~2-3s).
- **Per wave merge:** Full Phase 1 suite — `uv run --with pytest --with python-dotenv --with python-slugify pytest .claude/skills/google-ad-research/scripts/tests/ -x` (~10s).
- **Phase gate:** Full suite green + all manual-only smokes ticked off VALIDATION.md before `/gsd:verify-work` runs.

### Wave 0 Gaps

These files do not exist yet and must be created during Wave 0 of Phase 1 implementation (or at minimum before any test command runs):

- [ ] `.claude/skills/google-ad-research/scripts/tests/__init__.py` — empty package marker
- [ ] `.claude/skills/google-ad-research/scripts/tests/test_run_init.py` — tests for folder creation, slug derivation, brief verbatim write, collision retry
- [ ] `.claude/skills/google-ad-research/scripts/tests/test_lib_io.py` — tests for `slugify_brief()`, `iso_timestamp()`, `create_run_dir()`
- [ ] `.claude/skills/google-ad-research/scripts/tests/test_config.py` — tests for `load_env()` (find_dotenv walk, override=False, REQUIRED_KEYS check)
- [ ] `.claude/skills/google-ad-research/scripts/tests/conftest.py` — shared fixtures: `tmp_runs_root`, `sample_brief_text`
- [ ] `pytest` install: covered by `--with pytest` flag in `uv run`; no separate install step. (Alternative: PEP 723 metadata in a dedicated `_run_tests.py` runner — not blocking.)

**Test infrastructure decision:** Pytest fixtures + `tmp_path` for filesystem isolation. No HTTP mocking needed (Phase 1 has no HTTP). `monkeypatch` for env-var manipulation in `test_config.py`. Standard pytest patterns.

---

## Wave / Parallelization Opportunities

Phase 1's natural decomposition into work waves, with dependencies marked.

### Wave 0: Test infrastructure (sequential prerequisite, ~30 minutes)

- Create `.claude/skills/google-ad-research/scripts/tests/` directory with `__init__.py`, `conftest.py`
- Document the test commands in CLAUDE.md (root) so future agents know how to run them

### Wave 1: Parallel — independent foundation pieces (~2-3 hours, three agents in parallel)

These have no dependencies on each other. Three separate plans, three parallel agents:

| Plan | Files Touched | Depends On |
|------|---------------|------------|
| **Plan A: lib/ package** | `scripts/lib/__init__.py`, `scripts/lib/config.py`, `scripts/lib/io.py`, `scripts/lib/log.py`, `scripts/tests/test_lib_io.py`, `scripts/tests/test_config.py` | Wave 0 |
| **Plan B: run_init.py** | `scripts/run_init.py`, `scripts/tests/test_run_init.py` | Wave 0 + needs lib/ stubs (define interface contract first; mock or stub lib/io if Plan A not done yet) |
| **Plan C: Project root files** | Root `CLAUDE.md`, verify `.gitignore`/`.env.example` correctness, optionally a `README.md` quickstart section | Wave 0 |

**Parallelization caveat for Plan B:** strictly speaking, `run_init.py` imports from `lib/`. If Plan A and Plan B run truly in parallel, Plan B should write against a known interface contract (the function signatures from § Code Examples 3, 4, 5) and the integration test runs after both merge. Simpler: serialize Plan A → Plan B (Plan A is small, ~1 hour). Recommend parallelizing **Plan A + C**, then sequencing **B** after A.

**Revised Wave 1 plan:**
- Wave 1a (parallel): Plan A (lib/) + Plan C (root files)
- Wave 1b (sequential after A): Plan B (run_init.py)

### Wave 2: Sequential — SKILL.md authoring (~1-2 hours, single agent)

| Plan | Files Touched | Depends On |
|------|---------------|------------|
| **Plan D: SKILL.md** | `.claude/skills/google-ad-research/SKILL.md`, optionally `references/intake-checklist.md` if SKILL.md > 300 lines | All of Wave 1 — needs the exact `run_init.py` CLI contract to hardcode |

**Why sequential:** SKILL.md must reference the exact `--slug-source` CLI flag and the exact stdout JSON shape from `run_init.py`. Authoring SKILL.md against an in-flight CLI contract risks drift — finish run_init.py first.

### Wave 3: Sequential — VALIDATION.md and end-to-end smoke (~30 min)

| Plan | Files Touched | Depends On |
|------|---------------|------------|
| **Plan E: VALIDATION.md** | `.planning/phases/01-skill-scaffold-and-brief-intake/01-VALIDATION.md` | All prior waves |

Manual smoke: fresh Claude Code session, paste a brief, confirm skill loads, intake loops on missing field, run folder created, brief.md verbatim. Sign off requirements SCFD-01 through INTK-04.

### Total estimated effort

- Wave 0: 30 min
- Wave 1a: 2 hr (parallel — wall clock)
- Wave 1b: 1 hr
- Wave 2: 1.5 hr
- Wave 3: 30 min
- **Total: ~5.5 hr wall-clock** (vs ~7 hr fully sequential)

---

## Sources

### Primary (HIGH confidence)

- [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) — fetched and read in full May 2026. Authoritative for: SKILL.md frontmatter fields (name, description, when_to_use, allowed-tools, paths, disable-model-invocation, user-invocable, model, effort, context, agent, hooks, shell), `${CLAUDE_SKILL_DIR}` substitution, project-scoped vs personal-scoped skills, live change detection, content lifecycle, 1,536-char description cap, the 500-line SKILL.md target.
- [PEP 723 — Inline script metadata](https://peps.python.org/pep-0723/) — fetched and read May 2026. Exact comment-block syntax (`# /// script` / `# ///`), `requires-python` and `dependencies` fields, PEP 508 dependency specs.
- [docs.astral.sh/uv/guides/scripts](https://docs.astral.sh/uv/guides/scripts/) — fetched May 2026. `uv run` PEP 723 handling, `uv lock --script`, `uv add --script`, environment caching, lockfile-per-script.
- [github.com/theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) — verified for `find_dotenv()`, `load_dotenv(override=False)` semantics. Stable since 1.0.
- [pypi.org/project/python-slugify](https://pypi.org/project/python-slugify/) — `slugify(s, max_length=, word_boundary=, save_order=)` API, Unicode transliteration. Current 8.x.
- Existing in-repo research: `STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `SUMMARY.md`, `ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md`, `PROJECT.md` — all read in full and cross-referenced; these supersede external sources where they conflict because they encode operator-specific decisions.

### Secondary (MEDIUM confidence)

- [Skill authoring best practices — Anthropic](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — referenced in ARCHITECTURE.md; orchestrator/script boundary, progressive disclosure, anti-patterns. Cross-confirmed by code.claude.com/docs/en/skills.
- [How to Stop Claude Code Skills from Drifting (DEV Community, 2026)](https://dev.to/akari_iku/how-to-stop-claude-code-skills-from-drifting-with-per-step-constraint-design-2ogd) — per-step constraint design pattern (Pitfall 17 mitigation).
- [pydevtools.com — uv inside Claude Code](https://pydevtools.com/handbook/how-to/how-to-configure-claude-code-to-use-uv/) — `uv run` in stateless Bash; corroborates STACK.md.
- [Microsoft Learn — Naming Files, Paths, and Namespaces](https://learn.microsoft.com/windows/win32/fileio/naming-a-file) — Windows reserved characters (colon prohibited in filenames), informs the `T143024Z` no-colons timestamp choice.

### Tertiary (LOW confidence — flagged for validation in real use)

- [neonwatty.com — Claude Code Skills Tutorial: AskUserQuestion](https://neonwatty.com/posts/interview-skills-claude-code/) — informational only; we are NOT building Phase 1 around AskUserQuestion (it has known issues in plugin skills as of Feb 2026 per [GitHub issue 29547](https://github.com/anthropics/claude-code/issues/29547), and our project-scoped skill should rely on standard chat dialogue for intake).
- Optimal slug `max_length` (60 chars chosen) — operator preference; no source. Easy to tune later.
- Random hex collision suffix length (4 chars chosen) — pragmatic; 65k same-second runs is impossible for human-paced ops.

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — every recommended library is verified against PyPI/GitHub and against the existing STACK.md decisions; all stable as of May 2026.
- Architecture (skill folder layout, frontmatter, ${CLAUDE_SKILL_DIR}, PEP 723): **HIGH** — verified in full against current Anthropic and Astral docs (May 2026).
- Brief-intake loop pattern: **MEDIUM** — design is sound and follows skill best practices, but only validated post-implementation in real Claude Code session. Smoke tests in VALIDATION.md will surface any prompt-side validation gaps.
- Pitfalls: **HIGH** — all five Phase-1-owned pitfalls (1, 9, 17, 19, 20) are corroborated by PITFALLS.md and 2026 PPC literature; mitigations match existing-research recommendations.
- Folder collision handling: **MEDIUM** — design is reasonable; only Wave 0 testing reveals if the retry loop has off-by-one issues.

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days for stable infrastructure docs); 2026-05-22 (14 days for Claude Code skill docs which may iterate faster).
