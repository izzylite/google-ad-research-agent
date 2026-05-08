# Stack Research

**Domain:** Claude Code skill (Python helper scripts) orchestrating Serper.dev + Tavily + WebSearch for Google Ads keyword research
**Researched:** 2026-05-08
**Confidence:** HIGH (core stack), MEDIUM (clustering), HIGH (skill conventions)

---

## TL;DR (Prescriptive)

- **Runtime:** Python 3.13 minimum (3.14 preferred), shipped as a Claude Code skill at `.claude/skills/google-ad-research/`.
- **Package manager:** `uv` with PEP 723 inline script metadata — one self-contained script per helper, no venv juggling, no `pip install` pre-step.
- **Skill invocation pattern:** `Bash` tool calls `uv run ${CLAUDE_SKILL_DIR}/scripts/<name>.py --<arg>` with JSON in / JSON out. No MCP server. No long-running daemons.
- **HTTP:** `httpx` 0.28+ (sync mode). Already a transitive dep via `tavily-python` and `anthropic` — no extra install needed.
- **Serper.dev:** Direct REST via `httpx` — no first-party SDK exists. POST `https://google.serper.dev/search` (and `/news`, `/places`) with `X-API-KEY` header.
- **Tavily:** `tavily-python` 0.7.24 official SDK. `TavilyClient.search()` for queries, `TavilyClient.extract()` for competitor page mining.
- **Markdown tables:** `tabulate` 0.9.0 with `tablefmt="github"`. Battle-tested, also used by `pandas.to_markdown()`.
- **Secrets:** `python-dotenv` reading `.env` from project root, with `.env.example` committed and `.env` git-ignored. No keyring in v1.
- **Logging:** stdlib `logging` configured with `RichHandler` for the operator-facing console + a JSON file handler per run. No structlog/loguru in v1 — over-kill for a single-operator skill.
- **Clustering:** LLM-driven (Claude in the skill prompt) for v1. Defer `scikit-learn` TF-IDF/k-means to v2 only if LLM clustering proves inconsistent. Skip `sentence-transformers` entirely (~500MB transformer downloads kill skill portability).

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.13.x or 3.14.x | Runtime for all helper scripts | 3.14 (released Oct 2025) is the current production-recommended; 3.13 still receives maintenance. `tavily-python` requires `>=3.8`, so 3.13 is the safe floor. Avoid 3.15 (alpha as of May 2026). [HIGH confidence] |
| uv | 0.11.11 (May 2026) | Package + Python version manager, script runner | Single Rust binary; 10-100× faster than pip; native PEP 723 support means each helper script declares its own deps inline — no shared `requirements.txt`, no venv-activation pain across Claude Code's stateless Bash calls. [HIGH confidence] |
| httpx | 0.28.x | HTTP client for Serper.dev REST + general fetches | Used internally by `anthropic` and `openai` SDKs; sync API matches `requests` ergonomically; has connection pooling, timeouts, HTTP/2 if ever needed. Already pulled in by `tavily-python`, so it's effectively free. [HIGH confidence] |
| tavily-python | 0.7.24 (Apr 2026) | Competitor / landing page extraction + supplementary search | Official Tavily SDK. `search()` and `extract()` cover the v1 use cases. Active development (releases roughly monthly through 2026). [HIGH confidence] |
| tabulate | 0.9.0 | Markdown table rendering for the report | Industry standard; powers `pandas.DataFrame.to_markdown()`; `tablefmt="github"` produces GitHub-flavored markdown that pastes cleanly into docs/Slack. Zero alternative dependencies. [HIGH confidence] |
| python-dotenv | 1.0.x | Load API keys from `.env` at script start | Standard 12-factor approach; supports `.env` not overwriting existing OS env vars (so the operator can override per-shell); well-known to operators. [HIGH confidence] |
| Rich | 13.x or 14.x | Console output (progress bars, log formatting) | Optional but high-leverage for a CLI-style operator UX inside Claude Code's terminal stream. `RichHandler` for `logging` gives colored, readable run logs without writing custom formatters. [MEDIUM confidence — nice to have, not required] |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.x | Validate the parsed brief / API response shapes | When you want typed dataclasses for `Brief`, `KeywordCandidate`, `AdGroup`, `CompetitorAd`. Worth it once the data model has >3 fields and is passed between scripts via JSON. [HIGH confidence] |
| orjson | 3.10.x | Fast JSON serialization for run-history dumps | Drop-in faster `json` replacement; only matters if a run produces >1MB of JSON. For v1 the stdlib `json` is fine. [LOW priority — optional] |
| scikit-learn | 1.8.0 | TF-IDF + k-means fallback clustering | Only if LLM clustering proves unreliable in v2. Adds ~30MB; pulls numpy/scipy. Defer. [MEDIUM confidence — v2 only] |
| python-slugify | 8.x | Generate filesystem-safe run-folder names from briefs | When the run history folder needs deterministic names (e.g. `2026-05-08_acme-saas-trial-keywords/`). Trivial to hand-roll otherwise. [LOW priority] |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| ruff | Lint + format (replaces black, flake8, isort) | `ruff check` and `ruff format`; configure via `pyproject.toml`. Standard 2026 choice — single tool, Rust-fast. |
| pytest | Test runner for helper script unit tests | One `tests/` directory at the skill root; mock Serper/Tavily HTTP calls with `respx` (httpx-aware) or `responses` (requests-style). |
| respx | Mock httpx requests in tests | httpx-native mocking; cleaner than `unittest.mock` for HTTP calls. |
| mypy or pyright | Static type checking | Optional but recommended once `pydantic` models are in. pyright is faster; mypy has broader plugin ecosystem. |

---

## Installation

This skill uses **per-script inline metadata (PEP 723)**, not a shared `requirements.txt`. Each helper script declares its own dependencies in a header comment, and `uv run` provisions an isolated environment on first invocation (then caches it).

### One-time operator setup

```powershell
# Install uv (Windows)
winget install --id=astral-sh.uv -e
# or: irm https://astral.sh/uv/install.ps1 | iex

# Verify
uv --version    # expect 0.11.x or newer
uv python install 3.13
```

### Per-script dependency declaration (example)

```python
# scripts/serper_search.py
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx>=0.28",
#     "python-dotenv>=1.0",
#     "pydantic>=2.6",
#     "rich>=13.7",
# ]
# ///
"""Run a Serper.dev search and emit JSON to stdout."""
import httpx, os, sys, json
from dotenv import load_dotenv
...
```

Claude Code's `Bash` tool then invokes:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/serper_search.py --query "saas trial onboarding" --type search
```

`uv` reads the inline metadata, ensures the right Python + deps are available (cached after first run), and executes the script. No `pip install` step. No venv activation. No fight with Claude Code's stateless shell.

### Optional shared `pyproject.toml`

If multiple scripts share a large dep set (e.g. `pydantic` models reused across helpers), promote to a `pyproject.toml` at the skill root and use `uv sync` once. For v1 the inline approach is simpler.

---

## Claude Code Skill Integration Pattern

### Folder Layout

```
.claude/skills/google-ad-research/
├── SKILL.md                    # Operator-facing prompt (≤500 lines)
├── references/
│   ├── api-cheatsheet.md       # Serper/Tavily endpoint refs (loaded on demand)
│   └── output-spec.md          # Markdown report schema
├── scripts/
│   ├── serper_search.py        # POSTs to google.serper.dev/search|news|places
│   ├── tavily_extract.py       # TavilyClient.extract() for competitor pages
│   ├── tavily_search.py        # TavilyClient.search() supplementary signal
│   ├── rank_keywords.py        # Frequency + LLM-intent ranking
│   ├── build_report.py         # Assembles markdown via tabulate
│   └── _common.py              # Shared: env loading, logging, JSON helpers
├── templates/
│   └── report.md.j2            # Optional Jinja template if structure complex
└── tests/
    └── test_serper.py
```

### Invocation Pattern: Bash → uv run → JSON

**Decision: Use Bash tool calls to `uv run`, not MCP servers.**

| Pattern | Verdict | Reason |
|---------|---------|--------|
| `Bash` → `uv run scripts/foo.py --json` | **CHOSEN** | Stateless, debuggable, exits cleanly. Matches Claude Code's documented skill pattern. Each call is a fresh process — no stale state. |
| MCP server (long-running) | Avoid for v1 | Adds infrastructure (server lifecycle, transport config). MCP shines for cross-skill reuse and persistent state — neither applies to a single-operator skill making transactional API calls. |
| Inline `!` shell injection in SKILL.md | Use sparingly | Good for one-off context (e.g. `!`ls .planning/runs/``); bad for the main work because output becomes part of the prompt before Claude can react. |

### Recommended I/O Contract

Every helper script:
1. Reads args via `argparse` (or `--brief-json` for complex input piped in).
2. Reads secrets from environment (loaded by `python-dotenv` at top).
3. Writes structured progress logs to **stderr** (so Claude Code shows them to the operator without polluting return value).
4. Writes a **single JSON object** to **stdout** as the return value — this is what Claude reads back into context.
5. Exits non-zero on hard failure with a JSON error on stdout (so Claude can retry/recover).

Example SKILL.md fragment:

```markdown
## Step 2: Pull SERP signals

Run the Serper helper for each seed keyword:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/serper_search.py \
  --query "$SEED" \
  --type search \
  --gl us \
  --hl en
```

The script returns JSON with: `organic[]`, `peopleAlsoAsk[]`, `relatedSearches[]`, `ads[]`. Pass each result block to the ranking step.
```

### Why JSON-in / JSON-out

- Survives Claude Code's truncation heuristics (it preserves structure on long outputs).
- Lets Claude reason about results without re-parsing free-form text.
- Easy to persist to `runs/<date>/raw/serper-<seed>.json` for the run-history requirement.
- Trivially mockable in tests.

---

## Secret Management

### Recommendation: `python-dotenv` + `.env` (git-ignored)

| Approach | Verdict | Reason |
|----------|---------|--------|
| `.env` + `python-dotenv` | **CHOSEN** | Standard for Python tools; operator skill level (per `PROJECT.md`) is "manage API keys via env vars"; works identically on Windows/macOS/Linux; one file to back up. |
| OS environment variables (no `.env`) | Acceptable fallback | More secure (no plaintext on disk in repo dir) but adds shell-config friction. Document as the production option for paranoid operators. |
| `keyring` (OS credential manager) | Defer to v2 | More secure but adds setup friction; Windows credential manager + DPAPI works but means the skill stops being plug-and-play. Not justified for a single internal operator. |
| Hardcode in SKILL.md or scripts | **NEVER** | Skill files get committed; keys would leak to git instantly. |

### Concrete pattern

```
.planning/
.claude/skills/google-ad-research/
└── ...
.env                # git-ignored, real keys
.env.example        # committed, dummy values + comments
.gitignore          # contains: .env
```

```bash
# .env.example
# Get key at https://serper.dev (2,500 free credits on signup)
SERPER_API_KEY=your_serper_key_here

# Get key at https://app.tavily.com (1,000 free credits/month)
TAVILY_API_KEY=tvly-your_tavily_key_here

# Optional: override default Serper region/language
SERPER_DEFAULT_GL=us
SERPER_DEFAULT_HL=en
```

```python
# scripts/_common.py
from pathlib import Path
from dotenv import load_dotenv

# Walk up from script file to find project root .env
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
```

`override=False` means OS-level env vars win, so an operator who exports `SERPER_API_KEY` in their shell can override the file without editing it.

---

## Markdown Table Generation

### Recommendation: `tabulate` with `tablefmt="github"`

```python
from tabulate import tabulate

rows = [
    {"keyword": "saas trial", "frequency": 18, "intent": "high", "ad_group": "Trial Signups"},
    {"keyword": "free trial software", "frequency": 14, "intent": "high", "ad_group": "Trial Signups"},
]
print(tabulate(rows, headers="keys", tablefmt="github"))
```

Produces:
```
| keyword              |   frequency | intent   | ad_group       |
|----------------------|-------------|----------|----------------|
| saas trial           |          18 | high     | Trial Signups  |
| free trial software  |          14 | high     | Trial Signups  |
```

### Alternatives considered

| Option | Verdict | Reason |
|--------|---------|--------|
| `tabulate` 0.9.0 | **CHOSEN** | Most widely used; supports dicts and lists; `pandas.DataFrame.to_markdown()` uses it under the hood; `tablefmt="github"` matches the GFM tables Claude Code renders. [HIGH confidence] |
| `py-markdown-table` | Skip | Zero-dep is nice but tabulate is already a dep of nearly every data-Python stack and the extra ergonomics aren't worth a second library. |
| Hand-rolled f-string templates | Skip for tables | Painful to handle column-width alignment and pipe escaping; tabulate solves it for free. |
| Jinja2 template | **Use for outer report structure**, not the tables | Jinja shines for the overall report layout (header, sections, footer). Inside it, render each table block with `tabulate`. Optional — pure-string concatenation works fine for v1. |

---

## Logging

### Recommendation: stdlib `logging` + `rich.logging.RichHandler`

```python
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
log = logging.getLogger("gar")
```

Plus a per-run JSON file handler:

```python
import json, logging

class JsonLineHandler(logging.Handler):
    def __init__(self, path):
        super().__init__()
        self.path = path
    def emit(self, record):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": record.created,
                "level": record.levelname,
                "msg": record.getMessage(),
                "logger": record.name,
            }) + "\n")
```

### Alternatives considered

| Option | Verdict | Reason |
|--------|---------|--------|
| stdlib `logging` + `RichHandler` | **CHOSEN** | Zero new core dep (Rich is already useful for console UX); standard, well-documented; trivial JSON sidecar. |
| `loguru` | Skip | "Zero-config" appeal is real but loguru is a poor library citizen (monkey-patches stdlib logging) and per 2026 reviews "not something you should depend on for production." |
| `structlog` | Overkill for v1 | Excellent for large codebases with processor pipelines / OpenTelemetry. Single-operator skill doesn't need it. Revisit only if the skill grows into a fleet. |

---

## Optional: Clustering for Ad Groups

### Recommendation: LLM-driven clustering in v1; defer ML libs

The skill prompt asks Claude to cluster ranked keywords into ad groups by semantic theme. Claude is already in-process, has full context (the brief, the SERP signals, the operator's vertical hints from the conversation), and produces clusters with human-readable labels for free. This is the simplest and highest-quality option for v1.

### Why not sentence-transformers

| Option | Verdict | Reason |
|--------|---------|--------|
| LLM clustering (Claude in the skill) | **CHOSEN v1** | Best quality; already in context; produces named clusters; no extra deps; no model download. Cost is trivial vs. the value of accurate ad groups. [HIGH confidence] |
| `scikit-learn` TF-IDF + KMeans | Defer to v2 fallback | Fast (no GPU, no model download), but TF-IDF can't tell `"saas trial"` and `"free software trial"` are the same theme. Cluster labels need a second LLM pass anyway. Worth the ~30MB only if v2 needs deterministic offline clustering. [MEDIUM confidence] |
| `sentence-transformers` (e.g. `all-MiniLM-L6-v2`) | **AVOID** | Best embedding quality of the three options, but: (a) ~90MB model download on first run, (b) pulls torch as transitive dep (~700MB), (c) needs a second clustering algorithm anyway, (d) duplicates what Claude already does well. Skill becomes painful to install/distribute. [HIGH confidence — strong avoid] |
| BERTopic / hdbscan | **AVOID** | Same downsides as sentence-transformers plus more pinning pain. Not justified for ad-group clustering of <500 keywords. |

### When LLM clustering breaks down (v2 trigger)

If real usage shows Claude producing inconsistent cluster boundaries across runs of the same brief, fall back to TF-IDF + KMeans:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = ["scikit-learn>=1.8", "numpy>=2.0"]
# ///
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
X = vec.fit_transform(keywords)
km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
# Then ask Claude to LABEL each cluster (cheap)
```

Hybrid (deterministic clustering + LLM labeling) is the v2 sweet spot if v1 LLM-only clustering isn't reliable.

---

## Concrete API Patterns

### Serper.dev (REST via httpx)

```python
import httpx, os
from dotenv import load_dotenv
load_dotenv()

def serper_search(query: str, *, endpoint: str = "search", num: int = 20,
                  gl: str = "us", hl: str = "en") -> dict:
    """endpoint: 'search' | 'news' | 'places' | 'images' | 'shopping' | 'scholar'"""
    r = httpx.post(
        f"https://google.serper.dev/{endpoint}",
        headers={
            "X-API-KEY": os.environ["SERPER_API_KEY"],
            "Content-Type": "application/json",
        },
        json={"q": query, "num": num, "gl": gl, "hl": hl},
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()
```

Response shape (for `/search`): `organic[]`, `peopleAlsoAsk[]`, `relatedSearches[]`, `ads[]`, `knowledgeGraph`, `answerBox`. The PAA + related arrays are gold for keyword expansion; the `ads[]` block gives competitor headlines/descriptions for the ad-copy section.

Pricing: ~$0.30 per 1,000 queries; 2,500 free credits on signup. [HIGH confidence — verified against serper.dev landing page]

### Tavily (official SDK)

```python
from tavily import TavilyClient
import os

client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Search — supplementary signal alongside Serper
search_response = client.search(
    query="best onboarding software for SaaS",
    search_depth="advanced",  # 'basic' | 'advanced' | 'fast' | 'ultra-fast'
    max_results=10,
    include_raw_content=False,
    topic="general",          # or 'news', 'finance'
    include_answer=False,
)

# Extract — pull body text from competitor URLs (up to 20 at once)
extract_response = client.extract(
    urls=["https://competitor1.com/pricing", "https://competitor2.com/features"],
    extract_depth="advanced",
)
```

Note: `search_depth="advanced"` costs 2 credits per call vs. 1 for `basic`. Use `basic` for the bulk of v1 calls; reserve `advanced` for high-stakes briefs. [HIGH confidence — verified against docs.tavily.com and community forum]

### Async note

Both `httpx` and `tavily-python` ship async clients (`httpx.AsyncClient`, `AsyncTavilyClient`). For v1 the operator runs one brief at a time, so sync is simpler. If a future version fans out 10+ Serper calls in parallel, switching to `asyncio.gather` over `httpx.AsyncClient` is a localized refactor.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `httpx` | `requests` | If you literally only ever make sync calls and want the most familiar API. Fine for v1 — but `tavily-python` already pulls `httpx`, so adding `requests` doubles the HTTP-client footprint for nothing. |
| `httpx` (sync) | `httpx` (async) + `asyncio.gather` | When you need to fan out 5+ concurrent SERP calls per brief. Refactor target for v2 if run latency becomes an operator complaint. |
| Direct REST for Serper | Community wrapper libs | None of the third-party Serper Python libraries are well-maintained as of May 2026. `httpx.post` is 6 lines — wrapping is overhead. |
| `tavily-python` SDK | Direct REST to Tavily | SDK is officially maintained by Tavily, releases monthly, handles auth + retries. No reason to roll your own. |
| `tabulate` + plain string concat | Jinja2 templates for the whole report | Jinja makes sense once the report has 6+ sections with conditional blocks. For v1's four-section report, simple string concatenation + `tabulate` is more readable. |
| LLM clustering | `scikit-learn` TF-IDF | When you need deterministic, repeatable clusters across runs (audit/reporting use case). v2 only. |
| `python-dotenv` | `keyring` | Multi-tenant scenarios or compliance environments requiring OS-level secret storage. Not v1. |
| `uv` + PEP 723 | Poetry / pip + venv | Multi-package monorepos with shared lockfiles. Overkill for a single skill folder; uv's inline-script pattern is purpose-built for this. |
| Bash → `uv run` | MCP server | Cross-skill reuse, persistent state, real-time streaming. None of these apply to v1's transactional flow. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pip install -r requirements.txt` from inside Claude Code Bash calls | Claude Code starts a fresh shell every Bash call; venv activation does not persist; constant fights to find the right interpreter. | `uv run script.py` — uv handles ephemeral envs per invocation. |
| Hardcoded API keys in SKILL.md, scripts, or `.claude/settings.json` | Skill folders are designed to be committable/shareable. Keys leak instantly. | `.env` + `python-dotenv`, `.env` in `.gitignore`. |
| `loguru` for v1 logging | Monkey-patches stdlib; reviews in 2026 flag it as not production-grade; adds a dep for marginal value when stdlib + `RichHandler` covers 95%. | `logging` + `rich.logging.RichHandler` + a small JSON file handler. |
| `sentence-transformers` for ad-group clustering | ~700MB transitive deps (torch); skill becomes huge; LLM clustering is higher quality and free in-context. | LLM clustering (Claude already has the data) or `sklearn` TF-IDF as v2 fallback. |
| `pandas` just for `to_markdown()` | Pulls numpy + 50MB; overkill if you only want a markdown table. | `tabulate` directly (which is what `pandas.to_markdown` calls anyway). |
| Caching SERP results to disk in v1 | `PROJECT.md` explicitly defers this. Adds plumbing without payoff at v1 volumes. | Always fetch fresh; persist raw responses to `runs/<date>/raw/` for run history. |
| Long-running daemon / FastAPI server | Out of scope per PROJECT.md ("no server, no deploy target"). | Stateless `uv run` invocations from Claude Code's Bash tool. |
| Selenium / Playwright for SERP scraping | Brittle, blocked by Google quickly; Serper.dev exists precisely to avoid this. | Serper.dev for SERPs; Tavily for content extraction. |
| Python 3.12 or older | Tavily SDK requires `>=3.8` so technically works, but 3.13/3.14 give better error messages, faster startup, and free-threaded mode availability. | Python 3.13.x (LTS-ish maintenance) or 3.14.x (latest stable). |
| Python 3.15 alpha | Pre-release; library compat unverified. | Pin floor to 3.13. |

---

## Stack Patterns by Variant

**If the operator runs the skill on Windows (the documented case in `PROJECT.md`):**
- Use `winget install astral-sh.uv` for uv installation.
- Use forward slashes in script paths inside SKILL.md (Claude Code normalizes them).
- Set `shell: powershell` in SKILL.md frontmatter only if you need PowerShell-specific commands; default `bash` (Git Bash on Windows) works for everything in v1.

**If the skill needs to be shared with other PPC team members in v2:**
- Promote from `.claude/skills/` (project-local) to a Git repo distributed via Claude Code plugins.
- Add a `pyproject.toml` at the skill root for shared deps; keep PEP 723 inline metadata for one-off helpers.
- Move secrets out of `.env` and into per-user `~/.claude/.env` or OS keychain via `keyring`.

**If API costs become an issue (Serper or Tavily bills sting):**
- Add a SHA1-keyed disk cache in `runs/_cache/` keyed on `(endpoint, query, params)` with a 24h TTL.
- Use Serper's `num` param to cap result sets (default 10 is usually enough for keyword research).
- Default Tavily `search_depth` to `basic`; only escalate to `advanced` for tier-1 competitor analysis.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.13.x | tavily-python ≥0.7.0, httpx ≥0.27, scikit-learn ≥1.5 | All current as of May 2026 |
| Python 3.14.x | Same as above | Released Oct 2025, broadly supported by mid-2026 |
| tavily-python 0.7.24 | httpx (transitive), Python ≥3.8 | SDK pins httpx as a dep — no extra install needed |
| httpx 0.28 | h2 (optional, for HTTP/2), httpcore | Sync `httpx.Client` and `httpx.post` are stable; no breaking changes from 0.27 |
| tabulate 0.9.0 | Pure stdlib; no transitive deps | `tablefmt` values: `github`, `pipe`, `grid`, `simple`, etc. — `github` is the right one for GFM |
| python-dotenv 1.0.x | Pure stdlib | API stable since 1.0; `load_dotenv()` signature unchanged |
| uv 0.11.x | Reads PEP 723 metadata; manages CPython 3.8–3.14 | Self-updating via `uv self update` |

---

## Sources

### Verified High Confidence

- [Claude Code — Extend Claude with skills](https://code.claude.com/docs/en/skills) — skill folder structure, SKILL.md frontmatter reference, `${CLAUDE_SKILL_DIR}` substitution, bash invocation pattern, Live change detection. Read in full.
- [Tavily Python SDK on PyPI](https://pypi.org/project/tavily-python/) — version 0.7.24 (Apr 27, 2026), Python ≥3.8 requirement.
- [Tavily Python SDK on GitHub](https://github.com/tavily-ai/tavily-python) — `TavilyClient.search()`, `extract()`, `crawl()`, `map()`, `research()` method surfaces.
- [Tavily docs welcome page](https://docs.tavily.com/welcome) — install, basic usage examples for search and extract.
- [Tavily community: search_depth parameter](https://community.tavily.com/t/how-to-interpret-search-depth-parameter-what-does-advanced-mean/502) — `basic`/`advanced`/`fast`/`ultra-fast` options and credit costs.
- [Serper landing page](https://serper.dev/) — pricing $0.30/1k, 2,500 free credits, endpoint URLs.
- [Python 3.15.0a8, 3.14.4 and 3.13.13 are out!](https://blog.python.org/2026/04/python-3150a8-3144-31313/) — Python version landscape as of April 2026.
- [uv on PyPI](https://pypi.org/project/uv/) and [astral-sh/uv on GitHub](https://github.com/astral-sh/uv) — uv 0.11.11 (May 6, 2026), PEP 723 inline script metadata support.
- [PEP 723 — Inline script metadata](https://peps.python.org/pep-0723/) — official spec.
- [scikit-learn 1.8.0 docs — TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) and [KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html) — current stable APIs for the v2 fallback path.
- [tabulate on PyPI](https://pypi.org/project/tabulate/) — current 0.9.0; `tablefmt="github"` documented.
- [python-dotenv on GitHub](https://github.com/theskumar/python-dotenv) — `.env` loading, `override` flag behavior.

### Verified Medium Confidence

- [HTTPX vs Requests vs AIOHTTP comparison (Speakeasy, 2026)](https://www.speakeasy.com/blog/python-http-clients-requests-vs-httpx-vs-aiohttp) — performance and recommendations.
- [Choosing a Python Logging Library in 2026 (Dash0)](https://www.dash0.com/guides/python-logging-libraries) — structlog/loguru/stdlib comparison.
- [How to use Python skills with Claude Code (pydevtools)](https://pydevtools.com/handbook/how-to/how-to-use-python-skills-with-claude-code/) — skill conventions for Python helper invocation.
- [How to configure Claude Code to use uv (pydevtools)](https://pydevtools.com/handbook/how-to/how-to-configure-claude-code-to-use-uv/) — `uv run` inside Claude Code's stateless shell.
- [Best Practices for Storing API Keys (KDnuggets, 2026)](https://www.kdnuggets.com/managing-secrets-and-api-keys-in-python-projects-env-guide) — `.env` + `python-dotenv` standard pattern.

### Lower Confidence / Background

- [LLM Embeddings vs TF-IDF (MachineLearningMastery)](https://machinelearningmastery.com/llm-embeddings-vs-tf-idf-vs-bag-of-words-which-works-better-in-scikit-learn/) — clustering quality tradeoffs; informed v1 LLM-clustering recommendation.
- [py-markdown-table on PyPI](https://pypi.org/project/py-markdown-table/) — alternative considered and rejected.

---

*Stack research for: Claude Code skill (Python helpers) for Google Ads keyword research via Serper.dev + Tavily + WebSearch*
*Researched: 2026-05-08*
