# Architecture Research

**Domain:** Claude Code skill — Google Ads keyword research agent (markdown report generator, filesystem-only)
**Researched:** 2026-05-08
**Confidence:** HIGH (skill conventions verified against Anthropic official docs; pipeline architecture conventional Python ETL — high confidence; specific stage boundaries are opinionated proposals — medium confidence until first usage)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Claude Code Session (operator)                      │
│                                                                      │
│   User: "Research keywords for [campaign brief]"                     │
│         ↓                                                            │
│   Claude reads SKILL.md frontmatter → triggers skill                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────────┐
│           SKILL.md (orchestrator — prompt + workflow)                │
│                                                                      │
│   Phase 1: Conversational brief intake (LLM-only, no scripts)       │
│   Phase 2: Initialize run folder      → scripts/run_init.py         │
│   Phase 3: Seed expansion             → scripts/serp_fetch.py       │
│                                       → WebSearch tool (direct)     │
│   Phase 4: Competitor mining          → scripts/tavily_extract.py   │
│   Phase 5: Rank + cluster (LLM-led, optional helper for math)       │
│   Phase 6: Assemble report            → scripts/render_report.py    │
└─────┬─────────────────────────────────────────────────┬─────────────┘
      │                                                 │
┌─────┴─────────────────────────┐         ┌────────────┴──────────────┐
│   Helper Scripts (Python)      │         │   Built-in Claude tools   │
│                                │         │                            │
│   serp_fetch.py    (Serper)    │         │   WebSearch (free)         │
│   tavily_extract.py (Tavily)   │         │   Read / Write / Bash      │
│   run_init.py      (folder)    │         │                            │
│   render_report.py (markdown)  │         │                            │
│   lib/ (shared modules)        │         │                            │
└──────────────┬─────────────────┘         └────────────────────────────┘
               │
┌──────────────┴──────────────────────────────────────────────────────┐
│                          Filesystem                                  │
│                                                                      │
│   .runs/<timestamp>-<slug>/                                          │
│       ├── brief.md         (captured operator intake)                │
│       ├── raw/             (per-stage JSON dumps for debugging)      │
│       │   ├── serper-*.json                                          │
│       │   ├── tavily-*.json                                          │
│       │   └── websearch-*.json                                       │
│       └── report.md        (final deliverable)                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `SKILL.md` | Orchestrator — owns workflow, brief intake dialogue, judgement calls (intent scoring, clustering, anti-spam filtering) | Markdown with YAML frontmatter + checklist workflow + script invocations |
| `scripts/run_init.py` | Create dated run folder, slugify campaign name, write `brief.md` | Python stdlib only (datetime, pathlib, re) |
| `scripts/serp_fetch.py` | Hit Serper.dev `/search` endpoint, normalize organic + PAA + related + ads block, dump JSON to `raw/` | `requests` + retry decorator |
| `scripts/tavily_extract.py` | Call Tavily `extract` / `search` for competitor URLs, return content blocks | `tavily-python` SDK |
| `scripts/render_report.py` | Take consolidated keyword JSON + cluster JSON + ad copy JSON, produce final `report.md` | Jinja2 templates (or f-strings) |
| `scripts/lib/` | Shared helpers — env loading, slugify, retry, logging, IO conventions | Pure functions, no I/O surprises |
| WebSearch (Claude tool) | Free baseline signal — direct tool call from skill, no script wrapper | Built-in Claude Code tool |
| Claude (LLM) | Brief clarification, intent scoring, clustering decisions, ad copy selection, negative keyword judgement | Skill prompt instructions |
| `.env` (gitignored) | `SERPER_API_KEY`, `TAVILY_API_KEY` | Loaded by `python-dotenv` in `lib/config.py` |
| `.runs/` | Append-only run history — one folder per run, never modified after report.md is written | Filesystem |

**Key boundary:** scripts handle deterministic I/O (HTTP, file writes, JSON normalization). Claude handles judgement (which keywords are commercial, which cluster a term belongs in, which competitors matter). This split is the entire reason for the skill+scripts pattern — scripts for what code does well, prompt for what LLM does well.

## Recommended Project Structure

```
google-ad-research-agent/
├── .claude/
│   └── skills/
│       └── google-ad-research/         # skill folder name = skill identifier
│           ├── SKILL.md                # main orchestrator (YAML frontmatter + workflow)
│           ├── references/             # progressive-disclosure docs (loaded on demand)
│           │   ├── intent-scoring.md   # commercial intent rubric
│           │   ├── clustering.md       # ad group clustering heuristics
│           │   ├── negatives.md        # negative keyword discovery patterns
│           │   └── report-template.md  # final markdown report shape
│           ├── scripts/                # executable Python helpers
│           │   ├── run_init.py
│           │   ├── serp_fetch.py
│           │   ├── tavily_extract.py
│           │   ├── render_report.py
│           │   ├── lib/
│           │   │   ├── __init__.py
│           │   │   ├── config.py       # env loading, paths
│           │   │   ├── http.py         # requests session + retry
│           │   │   ├── io.py           # JSON dump/load, slugify
│           │   │   └── log.py          # stderr logging
│           │   └── requirements.txt    # requests, tavily-python, python-dotenv, jinja2
│           └── assets/
│               └── report.md.j2        # Jinja2 template for final report
├── .runs/                              # gitignored — one folder per run
│   └── 2026-05-08T1430-acme-saas/
│       ├── brief.md
│       ├── raw/
│       │   ├── serper-seed.json
│       │   ├── serper-paa.json
│       │   ├── tavily-competitor1.json
│       │   └── websearch-baseline.json
│       └── report.md
├── .planning/                          # GSD planning artifacts
│   ├── PROJECT.md
│   └── research/
├── .env.example                        # template — committed
├── .env                                # gitignored — operator fills locally
├── .gitignore                          # excludes .env, .runs/, __pycache__/
└── README.md                           # operator quickstart
```

### Structure Rationale

- **`.claude/skills/google-ad-research/`:** Project-scoped skill location per Anthropic conventions ([Claude Code skills docs](https://code.claude.com/docs/en/skills)). Project-scoped (not `~/.claude/skills/`) so the skill is committed with the repo and versioned alongside helper code.
- **`SKILL.md` at the skill root:** Required by skill loader. YAML frontmatter (`name`, `description`) drives discovery; body holds the workflow.
- **`references/` for progressive disclosure:** Anthropic best practice — keep `SKILL.md` under 500 lines, push detailed rubrics (intent scoring, clustering rules) into `references/*.md` loaded only when that step runs. Keeps token usage low.
- **`scripts/lib/` shared package:** Avoids copy-pasting env-loading / retry / slugify across the four scripts. Single source for `.env` parsing and HTTP retry config.
- **`scripts/requirements.txt` inside skill folder:** Operator runs `pip install -r .claude/skills/google-ad-research/scripts/requirements.txt` once. Keeps skill self-contained — the skill folder is portable.
- **`assets/report.md.j2`:** Jinja2 templates are an asset, not a script. Separation lets non-Python users tweak the report format without touching code.
- **`.runs/<timestamp>-<slug>/` (not `runs/`):** Hidden folder so `ls` of repo root stays clean. Timestamp-prefixed for chronological sort; slug suffix so operator can `cd` by name. Per-run folder = full state isolation; no shared mutable state between runs.
- **`raw/` subfolder per run:** Every API response written verbatim before any transformation. Lets operator (or Claude) re-derive the report from raw without re-paying API costs, and gives a forensic trail when results look weird.
- **`.env.example` committed, `.env` gitignored:** Standard pattern. Operator copies once, fills both keys.

## Architectural Patterns

### Pattern 1: Skill Prompt as Orchestrator, Scripts as Tools

**What:** `SKILL.md` is the conductor. It walks Claude through phases as a checklist, invoking scripts via `bash` for deterministic work and reasoning directly for judgement work. Scripts know nothing about each other — they read CLI args, write JSON to a path the skill specifies, exit. The skill stitches stage outputs together.

**When to use:** Every Claude Code skill that needs both LLM reasoning and external API calls. This is *the* canonical skill pattern from Anthropic's [skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

**Trade-offs:**
- ✅ Scripts are testable in isolation (just CLI in, JSON out)
- ✅ Script bodies never enter Claude's context window — only their output does
- ✅ Easy to swap a script (e.g., DataForSEO replaces Serper later) without rewriting the skill
- ❌ Cross-stage state lives in files, not memory — slightly more I/O than a monolithic Python program
- ❌ Skill prompt is the single point of orchestration — if it gets long, progressive-disclosure references are mandatory

**Example workflow snippet in SKILL.md:**

```markdown
## Phase 3: Seed expansion

Run: `python .claude/skills/google-ad-research/scripts/serp_fetch.py \
        --run-dir "$RUN_DIR" --seeds-from "$RUN_DIR/brief.md"`

Reads brief.md, expands seeds via Serper, writes:
- `$RUN_DIR/raw/serper-seed.json`     (organic + PAA + related)
- `$RUN_DIR/raw/serper-ads.json`      (ads block, kept separate)

If exit code 0, proceed to Phase 4.
If exit code 2 (rate limit), wait 60s and retry once.
If exit code 3 (auth), stop and surface error to operator.
```

### Pattern 2: Stage = Script + JSON Dump + LLM Synthesis

**What:** Every pipeline stage produces a JSON artefact in `raw/` first. The next stage reads that JSON. Final synthesis (clustering, ranking, report assembly) is done by the skill prompt reading several JSONs and writing report.md via the render script.

**When to use:** Multi-stage research pipelines where stages may be re-run independently and where intermediate state is valuable for debugging.

**Trade-offs:**
- ✅ Each stage independently re-runnable — operator can `python serp_fetch.py --run-dir <existing>` to refresh just one stage
- ✅ Forensic trail when a report looks wrong — raw JSONs show whether the bug is upstream (bad SERP data) or downstream (bad clustering)
- ✅ Future caching trivially bolted on (skip the call if `raw/serper-seed.json` exists and is fresh) — even though caching is out of scope for v1
- ❌ More files on disk per run (~5–15 JSONs)
- ❌ Operator must understand stage order if they want to re-run partial pipelines

**Example flow:**

```
brief.md
   │
   ├── serp_fetch.py    ──→ raw/serper-seed.json, raw/serper-ads.json
   ├── (WebSearch tool) ──→ raw/websearch-baseline.json  (skill writes via Write tool)
   ├── tavily_extract   ──→ raw/tavily-<domain>.json (one per competitor)
   │
   ├── [Claude reads all raw/*.json]
   ├── [Claude assembles consolidated keywords.json + clusters.json + negatives.json]
   │
   └── render_report.py ──→ report.md
```

### Pattern 3: Conversational Intake Captured to brief.md First

**What:** Phase 1 of the skill is pure dialogue — Claude reads any rough brief the operator pastes, asks clarifying questions, then writes a structured `brief.md` to the run folder *before* any API calls. All downstream scripts read `brief.md` (via the `--run-dir` arg) rather than receiving inline arguments.

**When to use:** When upstream input is fuzzy and downstream stages need consistent structured fields. Also: when you want a permanent record of "what was asked" for the run history folder.

**Trade-offs:**
- ✅ One source of truth for the run — `brief.md` is the contract
- ✅ Scripts have one input convention (`--run-dir <path>`), not 10 CLI flags each
- ✅ Operator can re-read past `brief.md` files to see how they framed prior research
- ❌ One extra file write before "real" work begins — negligible cost

### Pattern 4: WebSearch as a Direct Tool Call, Not a Script

**What:** Serper and Tavily get script wrappers (HTTP, retries, JSON normalization). WebSearch does NOT — Claude calls the WebSearch tool directly from within the skill workflow and writes the digested findings to `raw/websearch-baseline.json` via the Write tool.

**When to use:** When a Claude built-in tool exists for the job. Wrapping built-in tools in Python scripts is an anti-pattern — adds friction with zero benefit, since Claude can call them natively and the results enter context directly.

**Trade-offs:**
- ✅ Zero plumbing for the free signal source
- ✅ Claude can iterate (re-search with refined query) without spawning a subprocess
- ❌ WebSearch results don't auto-persist to `raw/` — skill must explicitly Write them. Acceptable cost.

### Pattern 5: Library Package for Cross-Script Concerns

**What:** `scripts/lib/` holds `config.py` (env + paths), `http.py` (a `requests.Session` with retry adapter), `io.py` (slugify, JSON helpers), `log.py` (stderr-only logging). Every script imports from `lib`, never copies utility code.

**When to use:** Whenever ≥2 scripts share a concern. Trivially worth the indirection.

**Trade-offs:**
- ✅ One place to change retry policy, log format, env-var names
- ✅ Test surface: `lib` is unit-testable independent of scripts
- ❌ Scripts must run with `lib/` on the path — handled by running them as `python -m` or by structuring scripts inside the package

## Data Flow

### Request Flow

```
Operator pastes brief in Claude Code
        ↓
Claude reads SKILL.md frontmatter (description) → activates skill
        ↓
Claude reads SKILL.md body (workflow checklist)
        ↓
Phase 1: Brief intake (LLM dialogue, no scripts)
        ↓
Phase 2: bash run_init.py    →  .runs/<ts>-<slug>/brief.md
        ↓
Phase 3a: bash serp_fetch.py →  .runs/.../raw/serper-*.json
Phase 3b: WebSearch tool     →  .runs/.../raw/websearch-baseline.json (via Write)
        ↓
Phase 4: bash tavily_extract.py → .runs/.../raw/tavily-<domain>.json (one per competitor)
        ↓
Phase 5: Claude reads all raw/*.json
         Claude reads references/intent-scoring.md (loaded on demand)
         Claude reads references/clustering.md      (loaded on demand)
         Claude produces consolidated keywords + clusters + negatives (in context)
         Claude writes intermediate JSONs via Write tool: keywords.json, clusters.json, negatives.json
        ↓
Phase 6: bash render_report.py → .runs/.../report.md
        ↓
Operator reads report.md (in Claude Code session) and distributes
```

### State Management

```
Per-run state (lives in .runs/<ts>-<slug>/):
    brief.md             — input, written once, never mutated
    raw/*.json           — append-only API dumps
    keywords.json        — Claude-synthesized, Phase 5
    clusters.json        — Claude-synthesized, Phase 5
    negatives.json       — Claude-synthesized, Phase 5
    report.md            — final deliverable, written once

In-memory state (only during a single script invocation):
    HTTP session, response objects, parsed JSON
    All discarded on script exit

Cross-run state:
    NONE in v1 (caching explicitly out of scope per PROJECT.md)
    .runs/ folders are append-only history; no run reads from another run
    Each run is fully isolated by its folder

Global state:
    .env (API keys) — read at script start, never written
```

**Run isolation:** A run is uniquely identified by its folder name (`<ISO-timestamp>-<slug>`). Two concurrent runs (unlikely but possible) get different timestamps and are fully independent. No shared lock files, no shared cache. The filesystem is the database.

### Key Data Flows

1. **Brief → Seed expansion:** `brief.md` contains industry/product/audience fields. `serp_fetch.py` reads brief, derives 5–15 seed queries (could be Claude-generated and passed via CLI, or script-derived from explicit brief fields). Each seed → one Serper call → organic results, PAA questions, related searches all flattened into `raw/serper-seed.json` keyed by source seed.
2. **Seed results → Competitor URLs:** Claude reads `raw/serper-seed.json`, identifies top recurring domains in organic results (frequency-of-occurrence across seeds). Picks 3–5 competitors. Passes URLs to `tavily_extract.py` via CLI.
3. **Competitor pages → Vocabulary mining:** `tavily_extract.py` calls Tavily for each URL, dumps page content + extracted entities to `raw/tavily-<domain>.json`. Claude reads these to mine value-prop language, terminology, offer keywords.
4. **All raw signals → Ranked keyword set:** Claude synthesizes — frequency-of-occurrence (count distinct sources mentioning each candidate) + commercial-intent score (LLM rubric from `references/intent-scoring.md`). Writes `keywords.json`.
5. **Keywords → Clusters:** Claude applies clustering rubric (`references/clustering.md`) — semantic groups, ad-group-sized chunks. Writes `clusters.json`.
6. **Serper ads block → Competitor ad copy:** Claude reads `raw/serper-ads.json`, selects representative paid headlines + descriptions per cluster theme. Inlined into report at render time.
7. **Negatives:** Claude scans all signals for adjacent-but-wrong-intent terms (e.g., "free", "tutorial" for a paid SaaS). Writes `negatives.json`.
8. **All synthesis JSONs → report.md:** `render_report.py` reads `keywords.json`, `clusters.json`, `negatives.json`, `raw/serper-ads.json`, fills `assets/report.md.j2`, writes `report.md`.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1–10 runs/week (v1 reality) | Current architecture as-described. No optimization needed. |
| 10–50 runs/week | Add SERP cache keyed by `(query, gl, hl, date)` → `raw/_cache/`. Cuts Serper costs ~60% on overlapping queries. Still single-operator. |
| 50+ runs/week, multi-operator | Move from filesystem `.runs/` to a shared store (S3 bucket or sqlite index). Add a `runs/index.json` listing past runs for searchability. Out of v1 scope. |
| Multi-vertical preset library | Reorganize `references/` by vertical: `references/verticals/ecommerce.md`, etc. Skill prompt routes to the right reference. Out of v1 scope. |

### Scaling Priorities

1. **First bottleneck:** Serper cost per run (every keyword research run hits Serper 5–15× for seed expansion). Mitigation: cache hot queries to disk once cost stings. Architecture is already cache-friendly because every API response is already written to `raw/`.
2. **Second bottleneck:** Operator throughput — manually copy-pasting reports out of Claude Code. Mitigation: add a `csv_export.py` helper that converts `keywords.json` to a Google Ads Editor-importable CSV. Out of v1 scope but trivially additive given the JSON-first pipeline.
3. **Third bottleneck:** Claude context window when many competitors × many seeds produce many raw JSONs. Mitigation: progressive-disclosure references already mitigate; if needed, add a `summarize_raw.py` that pre-digests `raw/*.json` into smaller summaries before Claude reads them.

## Anti-Patterns

### Anti-Pattern 1: Building One Monolithic `research.py` That Does Everything

**What people do:** Single `research.py` script that takes a brief and orchestrates Serper + Tavily + LLM calls + report generation internally — calling the Claude API from inside Python.
**Why it's wrong:** Defeats the entire skill model. Now you have a Python program that calls an LLM API, which means: a second runtime, second API key (Anthropic), second deployment surface, and the orchestration logic is in code instead of natural-language prompt where humans can tweak it. The whole point of a Claude Code skill is "Claude *is* the runtime; scripts are *its* tools." PROJECT.md is explicit: "Runtime: Claude Code only — no standalone CLI."
**Do this instead:** Skill prompt orchestrates. Scripts are dumb single-purpose CLIs. Claude (the operator's session) does the LLM work natively.

### Anti-Pattern 2: Scripts That Print Markdown to Stdout for Claude to Read

**What people do:** `serp_fetch.py` prints "Found 47 keywords:\n- foo\n- bar..." to stdout, expecting Claude to parse the prose.
**Why it's wrong:** Stdout becomes context-window pollution. Prose is harder to re-parse than JSON. Worse, it conflates the script's *operational logging* (which should be stderr) with its *data output* (which should be a JSON file).
**Do this instead:** Scripts write JSON to `--out <path>` (or to a deterministic path inside `--run-dir`). Stdout returns the path written and a one-line summary ("wrote 47 keywords to raw/serper-seed.json"). Stderr gets logging. Claude reads the JSON file.

### Anti-Pattern 3: Stuffing API Keys Into SKILL.md or Script Defaults

**What people do:** Hardcode `SERPER_API_KEY = "abc123..."` somewhere "to make it work for the operator."
**Why it's wrong:** Skill will be committed to the repo. Keys leak. Project-scoped skills are versioned with the project per Anthropic docs.
**Do this instead:** `.env` (gitignored) holds keys. `lib/config.py` loads via `python-dotenv`. Scripts fail loud (exit code 3 + clear stderr message) if keys missing. `.env.example` is committed as a template.

### Anti-Pattern 4: Brief Intake That Just Reads a Pre-Filled Template File

**What people do:** Skill expects `brief.yaml` to exist before running and errors if any field is missing.
**Why it's wrong:** PROJECT.md mandates conversational intake — "skill prompts operator for missing context...instead of expecting a filled template." A template-driven UX defeats the chat-native value prop.
**Do this instead:** Phase 1 of SKILL.md is pure dialogue. Claude reads whatever the operator pasted (rough text, bullets, partial structured form, anything), asks targeted follow-ups for missing fields, *then* writes the structured `brief.md`. The structured file is an *output* of intake, not an input.

### Anti-Pattern 5: Cross-Run Mutable State

**What people do:** Maintain a project-wide `keywords_master.json` that every run appends to, or a `seen_competitors.json` that affects future runs.
**Why it's wrong:** Breaks run isolation. Now Run #47 can be polluted by a bad Run #12. Reproducibility dies. Debugging "why did this run come out weird" requires understanding global state.
**Do this instead:** Each run is a sealed folder. If the operator wants to compare runs, they read both folders. Future "memory" features should be a separate, opt-in artefact (e.g., `lessons.md` the operator chooses to read into a new run's brief), not implicit shared state.

### Anti-Pattern 6: Fail-Fast on Any API Error

**What people do:** Single Tavily 5xx aborts the whole run. Operator loses their brief intake work.
**Why it's wrong:** Three signal sources exist *because* any one can fail. WebSearch alone produces a usable (lower-quality) report. Aborting wastes operator time and Serper spend.
**Do this instead:** **Degrade gracefully per source, fail fast on auth/config.** See Error Handling below.

## Error Handling Philosophy

The PROJECT.md question — fail fast vs. degrade gracefully — has different answers per failure class. Architecture proposal:

| Failure class | Response | Rationale |
|---|---|---|
| Missing/invalid API key (auth) | **Fail fast.** Script exits 3, skill surfaces error and stops. | Run cannot meaningfully complete. Operator action required. Cheap to recover (fix `.env`, re-run). |
| Brief validation (missing critical fields after dialogue) | **Fail fast.** Skill keeps asking until brief is complete. | Don't burn API credits on a half-defined brief. Cost of asking another question is zero. |
| Serper rate limit (HTTP 429) | **Retry with exponential backoff** (3 attempts, 2s/8s/32s). After exhaustion, exit 2. Skill waits 60s and retries the script once. After that, **degrade**: skill marks Serper data as partial in the report and continues. | Rate limits are transient. But operator's time matters more than perfect data. |
| Serper 5xx | Same retry policy as 429. **Degrade after retries exhausted.** | Same logic. |
| Tavily 5xx or timeout (per URL) | Retry once, then **skip that URL**. Continue with remaining competitors. Log skipped URLs in report. | Per-URL failure shouldn't kill the run; competitors are independent. |
| Tavily quota exceeded | **Degrade.** Skip remaining Tavily calls. Report notes "competitor mining incomplete — Tavily quota." | Operator can re-run after quota resets. |
| WebSearch failure | **Degrade silently.** Continue without baseline. Note in report. | WebSearch is the cheapest signal; losing it is least painful. |
| All three signal sources fail | **Fail.** No data = no report. Surface clear error. | Nothing useful to deliver. |
| `render_report.py` fails | **Fail loudly** but preserve all `raw/*.json` and synthesis JSONs. Operator can re-run just the render step. | Final-stage failure shouldn't lose the upstream work that already cost money. |

**Implementation hooks:**
- Scripts use exit codes: `0` success, `2` retryable failure (rate limit, transient), `3` fatal (auth, missing config), `1` other.
- `lib/http.py` provides a `requests.Session` with `urllib3.Retry` adapter (`backoff_factor=2`, `status_forcelist=[429, 500, 502, 503, 504]`, `allowed_methods=["GET", "POST"]`, `total=3`). Standard pattern verified against Python ecosystem retry conventions.
- Tavily SDK exceptions (`MissingAPIKeyError`, `InvalidAPIKeyError`, `UsageLimitExceededError`) map to exit codes 3/3/2 respectively per Tavily SDK docs.
- Skill prompt's workflow checklist includes explicit "if exit code 2, [specific action]" branches at each phase. This makes the degradation policy visible in the skill rather than hidden in scripts.
- Every degraded run gets a `## Run Quality` section at the top of `report.md` summarizing what worked / what was partial. Operator sees data quality at a glance.

## Suggested Build Order

Dependencies between components dictate phase ordering. Build bottom-up so each piece can be smoke-tested before the next layer depends on it:

1. **`scripts/lib/` foundation** (`config.py`, `http.py`, `io.py`, `log.py`, `requirements.txt`) — every other script imports these. Smoke test: `python -c "from lib.config import load_env; print(load_env())"`.
2. **`scripts/run_init.py`** — pure stdlib, no APIs, no dependencies on other scripts. Smoke test: creates a `.runs/<ts>-test/brief.md`. Validates folder layout decisions before any API work.
3. **`scripts/serp_fetch.py`** — first API integration. Validates `lib/http.py` retry behaviour against a real flaky external service. Most-used signal source, so debugging it early pays off.
4. **`scripts/tavily_extract.py`** — second API integration. Pattern is now established by `serp_fetch.py`; this is largely shape-following.
5. **`assets/report.md.j2` + `scripts/render_report.py`** — needs sample `keywords.json` / `clusters.json` / `negatives.json` to template against. Build with hand-written sample JSONs first; the skill produces the real ones later.
6. **`SKILL.md` skeleton** (frontmatter + phase headers + script invocations, but minimal prose) — wires the pieces. First end-to-end run with a hardcoded brief produces a report.
7. **`references/intent-scoring.md`, `references/clustering.md`, `references/negatives.md`, `references/report-template.md`** — the rubrics that turn the skeleton into a real research tool. Write these *after* the first end-to-end run reveals where the prompt actually needs guidance.
8. **Conversational intake (Phase 1 of SKILL.md)** — last because it depends on knowing exactly which fields downstream scripts and rubrics need. Doing intake first is tempting but produces a brief schema that will then need revision once the pipeline is real.
9. **Error handling polish** — exit code conventions, degraded-run reporting, retry tuning. Done after first 3–5 real runs reveal which failures actually happen.

**Critical-path note:** Steps 1→6 are the MVP loop. Operator can run a research session end-to-end after step 6, even if intent scoring is naive and intake is a hardcoded brief. Steps 7–9 are quality.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Serper.dev | `requests.post("https://google.serper.dev/search", headers={"X-API-KEY": ...})` from `serp_fetch.py`. Retry adapter handles 429/5xx. | No official Python SDK; raw HTTP is fine. ~$0.001/query. Default rate limit is generous (300 qps) — practical limit is monthly credit budget, not throttling. |
| Tavily | `tavily-python` SDK in `tavily_extract.py`. Catch `MissingAPIKeyError`, `InvalidAPIKeyError`, `UsageLimitExceededError`. | SDK is well-maintained, simpler than raw HTTP. ~$0.005–0.01/call — most expensive signal source, so per-URL failure handling matters. |
| WebSearch (Claude built-in) | Direct tool call from skill prompt. Skill writes findings to `raw/websearch-baseline.json` via the Write tool. | Free. No script wrapper. Counts against Claude Code session, not API budget. |
| `python-dotenv` | `lib/config.py` loads `.env` at module import. Fails loudly with named missing key. | Standard pattern. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| SKILL.md ↔ scripts | `bash` invocations with CLI args. JSON files in `--run-dir` for data. Stderr for logs, stdout for status, exit codes for state. | One-way: skill calls script, script writes file, skill reads file. No callbacks, no IPC. |
| Scripts ↔ scripts | None directly. Communicate only via JSON files in `.runs/<run>/`. | This is what makes stages independently re-runnable. |
| Scripts ↔ `lib/` | Python imports. `lib/` is a package; scripts run from the `scripts/` directory with `lib/` on the path (or scripts are inside the package). | Single shared utility namespace. |
| SKILL.md ↔ `references/*.md` | Claude reads on demand via Read tool. References linked one level deep from SKILL.md per Anthropic best practice. | Progressive disclosure — references don't consume tokens until loaded. |
| `.runs/<run>/` ↔ outside world | The run folder is the deliverable. Operator copy-pastes `report.md` content. No automated downstream pipeline. | Filesystem-only is the intentional scope boundary. |

## Sources

- [Skill authoring best practices — Anthropic](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — HIGH confidence. Authoritative source for SKILL.md structure, scripts/ conventions, progressive disclosure, anti-patterns, runtime model.
- [Extend Claude with skills — Claude Code Docs](https://code.claude.com/docs/en/skills) — HIGH confidence. Confirms `.claude/skills/` for project-scoped skills, `~/.claude/skills/` for personal.
- [anthropics/skills GitHub repository](https://github.com/anthropics/skills) — HIGH confidence. First-party reference skills (skill-creator, pdf-reader, claude-api) showing real structure conventions.
- [Agent Skills overview — Anthropic](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) — HIGH confidence. Filesystem-based architecture, progressive disclosure, script execution model.
- [Tavily Python SDK Reference](https://docs.tavily.com/sdk/python/reference) — HIGH confidence. Exception types and error handling pattern.
- [Error Handling in Tavily Search API — Tavily Community](https://community.tavily.com/t/error-handling-in-tavily-search-api/105) — MEDIUM confidence (community thread, but official-channel).
- [Serper.dev — rramos.github.io](https://rramos.github.io/2024/06/13/serper/) — MEDIUM confidence (third-party walkthrough; cross-checked against Serper's own docs for rate limits).
- [Python requests retry guide — Rebrowser](https://rebrowser.net/blog/python-requests-retry-the-ultimate-guide-to-handling-failed-http-requests-in-python) — MEDIUM confidence (third-party but widely-corroborated standard `urllib3.Retry` pattern).
- PROJECT.md (this repository) — HIGH confidence. Source of constraints (filesystem-only, no caching, no UI, two paid APIs + WebSearch).

---
*Architecture research for: Claude Code skill — Google Ads keyword research agent (markdown report generator)*
*Researched: 2026-05-08*
