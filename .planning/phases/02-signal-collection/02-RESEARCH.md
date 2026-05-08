# Phase 2: Signal Collection — Research

**Researched:** 2026-05-08
**Domain:** Three-source SERP/content harvest (Serper.dev REST, Tavily SDK extract, Claude Code WebSearch tool) writing locale-correct raw JSON into the run folder, with per-keyword source attribution and lemmatized canonicalization before any scoring.
**Confidence:** HIGH (Serper/Tavily/httpx-retries APIs verified against official docs; project context inherited from Phase 1 RESEARCH and the locked stack/architecture/pitfalls research) / MEDIUM (lemmatization library choice — three viable candidates, recommendation is opinion-driven for the grocery-style English keyword case)

---

## Summary

Phase 2 is the project's first paid work: it wires three signal sources to the run folder produced by Phase 1, normalises their output, and produces a single canonicalized keyword set with full provenance. Every keyword that survives Phase 2 must (a) carry a `sources` array recording which source(s) surfaced it, (b) have a stable canonical form via lemmatised + token-sorted hashing, and (c) be reproducible from the verbatim raw JSON dumps in `raw/`.

Three subtle traps dominate this phase. First, the WebSearch tool is a Claude-side tool — there is no Python wrapper for it; the skill prompt invokes it directly and writes the digested findings to `raw/websearch-baseline.json` via the Write tool. Wrapping it in a script is an anti-pattern. Second, Tavily's `extract()` returns failed URLs in `failed_results[]` rather than raising — per-URL failures must be logged and persisted, not silently dropped. Third, locale plumbing has to be tested end-to-end: passing `gl=uk`/`hl=en-gb` to Serper is necessary but not sufficient — the test must assert those fields appear in the recorded request and in `searchParameters` on the response, or US drift slips through.

**Primary recommendation:** Build `lib/http.py` (httpx-retries-backed wrapper) first as a Wave 0 precondition, scaffold pytest fixtures for both new scripts in Wave 0 (RED state), then run `serp_fetch.py` and `tavily_extract.py` in parallel (Wave 1). Update SKILL.md last (Wave 2) once both scripts have stable CLI contracts. Use the Phase 1 stdout-JSON / stderr-logs / exit-code (0/2/3) convention everywhere. Skip spaCy/NLTK — `inflect` 7.x for singular_noun + token-sort hashing covers grocery-style English keyword merging.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

No `CONTEXT.md` exists for Phase 2 — no upstream `/gsd:discuss-phase` was run. Constraints below are inherited from `STATE.md` § Decisions, `ROADMAP.md` Phase 2 success criteria, and the additional context attached to the research request, treated as locked for this phase.

### Locked Decisions (from STATE.md / ROADMAP.md / Phase 1 outcomes / additional context)

- **Three signal sources, three roles:** WebSearch (free baseline), Serper.dev (structured SERP — organic + PAA + related + ads), Tavily (deep competitor LP content).
- **Tavily extract, never tavily_crawl.** Hard cap: 5 competitors × 5 URLs each. `extract_depth='basic'` default; no `'advanced'` opt-in in v1.
- **Locale fields (`gl`, `hl`) are passed explicitly to every Serper call**, derived from the brief's `location` and `language` fields.
- **WebSearch is invoked from the skill prompt directly**, not wrapped in a Python helper. The skill writes the captured WebSearch findings to `raw/websearch-baseline.json` via the Write tool.
- **Every harvested keyword must carry a `sources` array** recording which source(s) surfaced it; downstream phases depend on this for source-diversity-driven ranking.
- **Close variants merge via lemmatized + token-sorted hashing before scoring.** Surface forms ("grocery delivery" / "groceries delivery" / "grocery deliveries") collapse to one canonical row; the variant list is preserved in metadata.
- **Run isolation absolute.** All Phase 2 outputs land in `.runs/<ts>-<slug>/raw/` (and a Phase-2-final aggregated file at `.runs/<ts>-<slug>/keywords.json`); no cross-run mutation; no caching in v1.
- **Secrets via env-only.** Keys NEVER in CLI args, NEVER written to disk, NEVER appear in log lines. Inherits `lib/config.load_env(require=...)` from Phase 1.
- **Stdout/stderr/exit-code contract** inherits from Phase 1: stdout = single JSON line summary, stderr = human-readable progress, exit codes 0 (ok) / 2 (retryable upstream) / 3 (fatal — auth/config/IO).
- **Phase 2 must address Pitfalls 4, 6, 7, 8, 21** (per SUMMARY.md):
  - Pitfall 4: Geo/language drift — pass `gl`/`hl` explicitly, log them per call, post-run lint-able
  - Pitfall 6: Long-tail noise — extract-don't-generate; canonicalise + dedup before scoring
  - Pitfall 7: Close-variant duplicates — lemmatise + token-sort hash before any aggregation
  - Pitfall 8: Tavily cost blowup — extract-not-crawl, `basic` depth, hard caps
  - Pitfall 21: Provenance — every keyword traceable via `sources` array; raw/ dump preserved verbatim

### Claude's Discretion

- **Seed keyword generation strategy:** the skill prompt (LLM-driven from validated brief) or a pure-script approach. RECOMMENDATION: skill-prompt-LLM-driven, then passed via `--seeds` CLI arg (or stdin JSON list) into `serp_fetch.py`. The skill is best positioned to read the brief's industry/product/audience and produce 5–15 seed queries; a script would either duplicate that reasoning or use brittle string templates. Documented below.
- **Source attribution merge timing:** per-script raw dumps each include a `source` field, then a Phase 2 final step (`merge_signals.py`, optional helper, OR skill-prompt LLM-driven merge) aggregates them. RECOMMENDATION: a Phase 2 final helper script (`merge_signals.py`) that emits `keywords.json`. Reasoning: deterministic dedup math is well-suited to a script; the skill orchestrates and verifies. Alternative — let Phase 3 ranking start from raw and merge on the fly — is rejected because canonicalisation MUST run before any scoring sees the data (per Pitfall 7 mitigation).
- **Lemmatisation library choice:** `inflect` 7.x (singular_noun) + a small token-sort/hash routine in `lib/canon.py`. Justified below; alternatives `simplemma`, `lemminflect`, `nltk` evaluated.
- **HTTP retry strategy:** `httpx-retries` 0.5+ via `RetryTransport` rather than hand-rolling exponential backoff; aligns with the Phase 1 STACK research lean toward maintained ecosystem libraries.
- **Tavily SDK vs raw httpx:** SDK (`tavily-python` 0.7.24) — already a transitive dep of nothing-yet, but the SDK is small, exception-typed, and matches Phase 1 STACK research recommendation.
- **Per-script log file in raw/:** optional. RECOMMENDATION: write a per-call `raw/<source>-meta.json` capturing locale params, response time, credit count, retry count. Cheap; pays back immediately on debugging.
- **WebSearch query strategy:** how many queries, which variants. RECOMMENDATION: 3–5 queries — the seed product phrase, plus 1–2 PAA-style "how do I…" variations, plus a brand+location query if brand-terms field present. Documented below.

### Deferred Ideas (OUT OF SCOPE)

- Cost-ceiling / pre-run spend confirmation (PROJECT.md: out of scope; v1 trusts operator)
- SERP result caching by query hash (v2: TOOL-01)
- Multi-locale fan-out (v2: TOOL-04)
- Volume / CPC enrichment via Google Ads / DataForSEO (v2: VOLM-01/02)
- Concurrent / async Serper / Tavily fan-out (Phase 1 STACK noted: localised refactor target if v1 latency becomes a complaint; out of v1 scope)
- Per-keyword embedding distance for variant detection (v2 if lemma-hash proves insufficient)
- WebSearch query auto-tuning / iterative refinement (v1 = single-pass; iterative is v2)
- Affiliate filtering / advertiser-domain allowlist (Phase 5)
- Intent classification, scoring, ranking (Phase 3)
- Clustering (Phase 4)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| **SIGL-01** | `serp_fetch.py` calls Serper.dev REST and persists organic + PAA + related + ads block to `raw/serper.json` | § Serper.dev REST — Request/Response Schema; § serp_fetch.py CLI Contract; § lib/http.py — Retry Strategy |
| **SIGL-02** | `tavily_extract.py` runs Tavily extract on competitor URL list (max 5 competitors × 5 URLs, `extract_depth='basic'`); per-domain JSON written | § Tavily SDK — extract() Signature & Errors; § tavily_extract.py CLI Contract |
| **SIGL-03** | WebSearch tool invoked from skill prompt for free baseline signal | § WebSearch Tool — Skill-Prompt Integration; § SKILL.md — Phase 2 Additions |
| **SIGL-04** | Locale parameters (`gl`, `hl`, language hints) passed to all sources from brief fields | § Locale Plumbing — Source-by-Source; § Common Pitfalls — Pitfall 4 |
| **SIGL-05** | Each keyword retains source attribution (which source(s) surfaced it) for downstream ranking | § Source Attribution Data Model; § merge_signals.py Helper |
| **SIGL-06** | Keywords lemmatized + canonicalized to merge close variants before scoring | § Canonicalisation — Library Choice and Algorithm; § lib/canon.py |
</phase_requirements>

---

## Standard Stack

### Core (Phase 2 net-new)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | 0.28.x | HTTP client for Serper.dev REST | Already a transitive dep of `tavily-python`; sync API; connection pooling; broad ecosystem (respx, httpx-retries built on it). [HIGH — verified Phase 1] |
| `httpx-retries` | 0.5.0 (Apr 20 2026) | `RetryTransport` for httpx — exponential backoff, status-code retry | Maintained, sync+async support, near-`urllib3.Retry` API surface. Cleaner than hand-rolling `tenacity` decorators. Stars/release cadence indicate active maintenance. [HIGH — verified against pypi/github] |
| `tavily-python` | 0.7.24 (Apr 27 2026) | Tavily extract SDK | Official SDK; typed exceptions (`InvalidAPIKeyError`, `UsageLimitExceededError`, `MissingAPIKeyError`, `BadRequestError`); per-URL failures returned in `failed_results[]` not raised. Phase 1 STACK pinned this. [HIGH] |
| `inflect` | 7.5+ | English singular_noun for canonicalisation | Pure-Python (no models, no torch); maintained by jaraco; standard in PPC/SEO toolchains. Exposes `engine().singular_noun(word)` returning `False` if already singular. [HIGH] |
| `respx` | 0.22.x or newer | Mock httpx requests in pytest for `serp_fetch.py` and `tavily_extract.py` (Tavily SDK uses httpx internally) | httpx-native; cleaner than `unittest.mock` patching; supports request-pattern matching to assert locale params landed in the body. [HIGH — verified Phase 1] |
| `pytest` | 8.x | Test runner (already used Phase 1) | Inherited; conftest.py exists at `scripts/tests/conftest.py`. |

### Supporting (carried from Phase 1)

| Library | Version | Purpose |
|---------|---------|---------|
| `python-dotenv` | 1.0.x | `lib/config.load_env(require=("SERPER_API_KEY","TAVILY_API_KEY"))` |
| `python-slugify` | 8.x | Slugifying competitor domains for `raw/tavily-<domain>.json` filenames |
| stdlib `logging`, `json`, `pathlib`, `argparse`, `re`, `hashlib` | — | All Phase-1 tooling reused |

### NOT Needed (Considered and Rejected)

| Library | Why Rejected |
|---------|--------------|
| `tenacity` | Decorator API works fine but adds a second retry abstraction adjacent to `httpx-retries`; pick one. `httpx-retries` integrates at the transport layer (cleaner separation). |
| `urllib3.Retry` | Requires `requests` ecosystem; we're on httpx. `httpx-retries` ports the API. |
| `spaCy` | ~600MB models for English; massive overkill for "merge groceries → grocery"; STACK.md already rejected for `sentence-transformers`-style portability hit. |
| `NLTK` | ~30MB plus `wordnet` corpus download (manual `nltk.download('wordnet')` step); fragile in `uv run` ephemeral envs (corpus path discovery is hostile to per-script caches). |
| `lemminflect` | Higher quality than `inflect` for verb forms, but PPC keywords are noun-phrase-dominated; the 1-2% accuracy gain doesn't justify the larger dictionary footprint or the spaCy-extension dependency path. |
| `simplemma` | Multilingual is nice but unused; pure-Python is good but the model files are downloaded on first call (~5MB per language) which adds first-run latency on `uv run` cache miss. `inflect` is rule-based with zero downloads. |
| `TextBlob` | Pulls NLTK transitively. Same trap. |
| `pydantic` | Phase 2's data shapes are 4–5 fields per row; `dict` works fine. STACK.md threshold ("≥3 cross-script JSON contracts") is just barely tripped here, but we have JSON-schema in markdown comments and tests; no runtime gain from pydantic until Phase 3 introduces intent labels. Defer to Phase 3. |
| `httpx.AsyncClient` / `asyncio.gather` | v1 runs one brief at a time; serial Serper + serial Tavily is < 60 s for typical brief. Async is a Phase 5 / v2 refactor target, not a Phase 2 scope item. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `httpx-retries` | hand-rolled exponential-backoff loop in `lib/http.py` (~30 lines) | Hand-roll is fewer deps but reinvents jitter, Retry-After parsing, status_forcelist. `httpx-retries` is small enough to prefer. |
| `tavily-python` | direct `httpx.post("https://api.tavily.com/extract", ...)` | SDK exception types are valuable; direct HTTP loses them. SDK is < 10KB. Use SDK. |
| `inflect` + token-sort | full lemmatiser (`spacy`/`nltk`) | Full lemmatiser handles "running" → "run" (verbs), "better" → "good" (adj). PPC keywords are noun phrases ("grocery delivery", "same day groceries") — singular-form normalisation + stop-word strip + token sort handles the realistic close-variant cases without 600MB of models. |
| Per-script raw + final merge step | Each script writes already-merged keywords | Per-script raw with `source` field preserves debuggability — operator can re-run merge alone if it goes wrong. Matches Phase 1 STACK pattern: scripts produce per-stage JSON, downstream stages compose. |
| `merge_signals.py` script | Skill-prompt LLM merging | Merge is deterministic math (lemma hash → group → pick canonical surface form). LLM merge is non-deterministic; per Pitfall 3 (drift), use code for math, LLM for judgement. |

### Installation (per-script PEP 723 inline, no shared requirements)

```python
# scripts/serp_fetch.py
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx>=0.28",
#     "httpx-retries>=0.5",
#     "python-dotenv>=1.0",
# ]
# ///
```

```python
# scripts/tavily_extract.py
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "tavily-python>=0.7.24",
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
```

```python
# scripts/merge_signals.py
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "inflect>=7.5",
# ]
# ///
```

Test deps (run via `uv run --with pytest --with respx ... pytest ...`) — no `pyproject.toml` needs creating in Phase 2 if Phase 1's ad-hoc style is preserved; CLAUDE.md notes Phase 2 may promote to a shared `pyproject.toml`. Recommendation: defer the promotion to Phase 6 unless lib/ tests outgrow ad-hoc invocation; for now, document the pytest invocation in `scripts/tests/README.md` (one paragraph) and keep PEP 723 per-script.

---

## Architecture Patterns

### Recommended Phase-2 File Layout (additions to existing skill)

```
.claude/skills/google-ad-research/scripts/
├── run_init.py                  # Phase 1 — UNCHANGED
├── serp_fetch.py                # NEW — Serper REST → raw/serper.json
├── tavily_extract.py            # NEW — Tavily SDK → raw/tavily-<domain>.json
├── merge_signals.py             # NEW — raw/*.json → keywords.json (canonicalised + sourced)
├── lib/
│   ├── __init__.py              # UNCHANGED
│   ├── config.py                # UNCHANGED (already supports require=())
│   ├── io.py                    # UNCHANGED
│   ├── log.py                   # UNCHANGED (Phase 1 stderr logger; per-run JSON sidecar deferred)
│   ├── http.py                  # NEW — httpx.Client factory with httpx-retries RetryTransport
│   └── canon.py                 # NEW — canonicalise(keyword) -> (canonical_form, lemma_hash)
└── tests/
    ├── conftest.py              # EXTEND — add fixtures for run_dir, mocked Serper response, mocked Tavily SDK
    ├── fixtures/                # NEW
    │   ├── serper_search_uk.json        # recorded Serper response for "grocery delivery uk"
    │   ├── serper_empty_ads.json        # response with empty ads array
    │   └── tavily_extract_2urls.json    # recorded Tavily extract response (2 URLs, 1 success, 1 failed)
    ├── test_lib_http.py         # NEW — retry behaviour on 429/500/503; success path
    ├── test_lib_canon.py        # NEW — close-variant collapse, question-keyword preservation
    ├── test_serp_fetch.py       # NEW — locale params land in request, response normalised, exit codes
    ├── test_tavily_extract.py   # NEW — caps enforced, failed_results persisted, exit codes
    └── test_merge_signals.py    # NEW — sources array correct, lemma-hash dedup, canonical surface form

.runs/<ts>-<slug>/raw/           # Phase 2 outputs land here
├── serper.json                  # SIGL-01
├── tavily-<domain>.json (×N)    # SIGL-02 — one per competitor domain
├── websearch-baseline.json      # SIGL-03 — written by skill prompt via Write tool
└── (optional) <source>-meta.json # call metadata: locale, response_time, credits, retries
.runs/<ts>-<slug>/keywords.json  # Phase 2 final — canonicalised + sourced
```

**Why `keywords.json` lives at run-dir root, not in `raw/`:** `raw/` is verbatim API output (Pitfall 21 mitigation — re-derive the report from raw without re-paying API costs). `keywords.json` is project-canonical post-processing; it belongs alongside `brief.md` and the eventual `report.md`.

### Pattern 1: Per-Script Raw Dump + Centralised Merge

**What:** Each signal-source script writes a verbatim dump to `raw/<source>.json` (or `raw/<source>-<domain>.json` for Tavily's per-domain split). Each entry includes `source` (one of `"serper-organic"`, `"serper-paa"`, `"serper-related"`, `"serper-ads"`, `"tavily-extract"`, `"websearch-baseline"`). `merge_signals.py` reads all `raw/*.json`, canonicalises terms via `lib/canon.canonicalise()`, groups by `lemma_hash`, picks a canonical surface form, and emits `keywords.json` with each row carrying its `sources: [...]` array.

**When to use:** Anywhere multiple sources contribute to a single canonical aggregate. Standard ETL pattern; matches Phase 1 STACK research § Pattern 2 (Stage = Script + JSON Dump + LLM Synthesis), with the synthesis demoted to deterministic Python because the math is well-defined.

**Trade-offs:**
- Re-running `merge_signals.py` alone is free (no API cost) — operator can iterate on canonicalisation without re-burning Serper/Tavily credits
- Three sources × ~3 files keeps `raw/` browsable; <20 files per typical run
- Per-script dumps preserve the Pitfall 21 trace: every keyword has a verifiable upstream snippet

### Pattern 2: Skill-Prompt WebSearch (No Script Wrapper)

**What:** SKILL.md instructs Claude to call the WebSearch tool 3–5 times with locale-aware queries derived from the brief, then captures the digested results to `raw/websearch-baseline.json` via the Write tool. There is NO Python wrapper for WebSearch — STACK.md / ARCHITECTURE.md § Pattern 4 explicitly identifies wrapping built-in Claude tools as an anti-pattern.

**When to use:** Whenever a Claude Code built-in tool exists for the job. Wrapping built-ins in scripts adds friction with no benefit — Claude can call them natively, and the results enter context directly without an intermediate process boundary.

**WebSearch from inside Claude Code (the in-skill tool):** Returns ranked results with `title`, `url`, `snippet`, and a `page_age` freshness hint. The tool auto-handles request execution; the skill prompt parses the returned content (text + cited URLs) and writes a structured JSON dump.

**Why a structured JSON dump matters for Phase 2:** `merge_signals.py` reads `raw/*.json` uniformly. WebSearch output that lands as free-form prose breaks the merge contract. The skill must write a JSON object shaped like:

```json
{
  "source": "websearch-baseline",
  "queries": [
    {"q": "same day grocery delivery uk", "locale": "uk/en-GB"},
    {"q": "best online grocery delivery london 2026", "locale": "uk/en-GB"},
    {"q": "how to choose grocery delivery service", "locale": "uk/en-GB"}
  ],
  "results": [
    {"query": "same day grocery delivery uk", "title": "...", "url": "...", "snippet": "...", "page_age": "..."}
  ],
  "extracted_keywords": [
    {"keyword": "same day grocery delivery", "from_query": "same day grocery delivery uk", "snippet_excerpt": "..."},
    {"keyword": "online grocery delivery london", "from_query": "...", "snippet_excerpt": "..."}
  ],
  "captured_at": "2026-05-08T14:30:24Z"
}
```

The skill prompt is responsible for the keyword extraction step (LLM judgement: "what keyword phrases does each result snippet surface?"). `extracted_keywords` is what `merge_signals.py` consumes; `results` is preserved verbatim for Pitfall 21 provenance.

**Locale handling:** The Claude Code WebSearch tool accepts a `user_location` parameter on the API side (city/region/country/timezone). Whether the in-tool surface exposes that to skill prompts varies; the safe path — mandated by Pitfall 4 — is to **embed the locale in the query string itself** ("UK", "London", "in en-GB"). This is verified across Phase 1 PITFALLS.md Pitfall 4 ("For WebSearch, include the country in the query string itself since locale params are unreliable there.")

### Pattern 3: Run-Folder is the Database

**What:** No central index, no SQLite, no in-memory sharing. Every script reads its inputs from `.runs/<ts>-<slug>/` and writes outputs back. `serp_fetch.py --run-dir <path>` is the universal CLI shape. Inherits from Phase 1 ARCHITECTURE.md § Pattern.

**When to use:** Always. The single-operator skill model with stateless `uv run` calls makes filesystem the simplest, most debuggable shared state.

### Pattern 4: Defensive Response Parsing (Pitfall 4 mitigation)

**What:** Serper's response shape varies by query — `peopleAlsoAsk`, `relatedSearches`, `ads`, `knowledgeGraph`, `answerBox` are all sometimes-present-sometimes-not. Code must use `.get(key, [])` everywhere, not bracket access. Empty arrays are valid; missing keys are valid; `None` for sub-keys is valid. Tests assert this with a fixture that has empty `ads`.

**When to use:** Every external API response. PITFALLS.md § "Integration Gotchas" calls this out: "Assuming ads block always present — many queries return zero ads; handle empty `ads` array gracefully."

### Anti-Patterns to Avoid (Phase 2 specific)

- **Wrapping WebSearch in a Python script.** The tool is in-Claude; wrapping it forces a subprocess boundary and re-parses prose into JSON twice. Skill prompt + Write tool is correct.
- **Calling Tavily without `extract_depth='basic'`.** SDK default is `'basic'`, but explicit > implicit. Pitfall 8 mitigation requires the parameter visible in code.
- **Calling `tavily_crawl()` instead of `tavily_extract()`.** Crawl spiders sites; extract is bounded. Crawl is forbidden in v1 — ROADMAP Phase 2 success criterion 2 says so verbatim.
- **Building close-variant detection without a hash.** Pairwise string distance scales O(n²); `inflect.singular_noun` + sorted-token-string + sha256 is O(n) and deterministic.
- **Letting `keywords.json` be the only source of truth.** `raw/` is the truth; `keywords.json` is post-processed and re-derivable.
- **Skipping the locale assertion test.** Pitfall 4 is a quiet failure; mock-asserted `gl=uk` in the request body is the only durable mitigation.
- **Logging the API key, even at DEBUG level.** Pitfall 9. `lib/log.py` filters high-entropy strings (Phase 1 deferred to Phase 2 in CLAUDE.md note — but: the simpler discipline is "never pass the key into the logger"; the env var is read inside `lib/http.py` and `lib/config.py` only).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry with jittered backoff on 429/5xx | Custom retry loop with `time.sleep(2**n)` | `httpx-retries` `Retry(total=3, backoff_factor=1.0, status_forcelist=[429,500,502,503,504])` via `RetryTransport` | Hand-rolled retry forgets Retry-After header parsing, jitter, max wait cap. Library is 0 deps beyond httpx. |
| Singular ↔ plural normalisation for English | Manual rules ("if ends in s, strip s") | `inflect.engine().singular_noun(word)` | Edge cases are legion ("buses" / "boxes" / "deliveries" / "leaves"). Inflect has 20 years of edge-case dictionary. |
| Mocking httpx for tests | `unittest.mock.patch("httpx.post")` | `respx.mock` with route patterns matching URL + query params | respx asserts request shape (URL, headers, body, query); plain mock just intercepts. |
| Tavily REST | Direct `httpx.post("https://api.tavily.com/extract", ...)` | `tavily.TavilyClient` SDK | SDK has typed exceptions and credit accounting; rolling our own duplicates this. |
| Slugifying domain names for tavily-<domain>.json filenames | Custom `re.sub` | `slugify(domain)` from `python-slugify` (already in Phase 1 deps) | Already imported; consistent with run-folder slug rule. |
| Token-sort hashing for variant detection | Manual sorted-list-of-words string | sha256 of `" ".join(sorted(tokens))` | One stdlib line; deterministic; collision-resistant beyond what we need. |
| URL normalisation for tavily competitor URL deduplication | Custom URL parsing | `urllib.parse.urlsplit` + lowercase netloc | Stdlib; never roll your own URL parser. |

**Key insight:** Phase 2's value is *correctness of the data pipeline*, not infrastructure. Every line spent on retry math or singular_noun rules is a line not spent on the locale-assertion test, the canonical-form selection rule, or the source-attribution edge case ("what if Serper PAA and Serper related surface the same exact phrase — does it have `source_diversity` 1 or 2?"). Spec says 2 — distinct sources within Serper count as distinct.

---

## Code Examples

Verified patterns adapted from official sources (Tavily SDK reference, httpx-retries README, Serper community docs).

### serp_fetch.py — Serper.dev request shape

```python
# /// script
# requires-python = ">=3.13"
# dependencies = ["httpx>=0.28", "httpx-retries>=0.5", "python-dotenv>=1.0"]
# ///
"""serp_fetch.py — POST google.serper.dev/search per seed; persist raw/serper.json.

CLI:
    uv run serp_fetch.py --run-dir <abs path> --seeds "kw1" "kw2" "kw3" --gl uk --hl en-GB

Stdout:
    {"raw_path": "<abs>", "seed_count": 3, "organic_count": 28, "paa_count": 12,
     "related_count": 22, "ads_count": 4, "credits_used": 3}

Stderr: progress per seed.
Exit codes: 0 ok, 2 retryable upstream (429 after retries / 5xx after retries), 3 fatal (auth / IO / config).
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path

# Make sibling lib/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.config import load_env
from lib.http import build_client
from lib.log import configure_logger

log = configure_logger()
SERPER_URL = "https://google.serper.dev/search"


def fetch_seed(client, seed: str, *, gl: str, hl: str, num: int = 20, api_key: str) -> dict:
    """One Serper call; returns parsed JSON. Raises httpx.HTTPStatusError after retries."""
    response = client.post(
        SERPER_URL,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": seed, "gl": gl, "hl": hl, "num": num},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def normalise_response(raw: dict, *, seed: str, gl: str, hl: str) -> dict:
    """Pull out the four signal arrays with defensive .get() everywhere."""
    return {
        "seed": seed,
        "locale": {"gl": gl, "hl": hl},
        "organic": [
            {"title": item.get("title"), "link": item.get("link"),
             "snippet": item.get("snippet"), "position": item.get("position"),
             "source": "serper-organic", "from_seed": seed}
            for item in raw.get("organic", [])
        ],
        "peopleAlsoAsk": [
            {"question": item.get("question"), "snippet": item.get("snippet"),
             "title": item.get("title"), "link": item.get("link"),
             "source": "serper-paa", "from_seed": seed}
            for item in raw.get("peopleAlsoAsk", [])
        ],
        "relatedSearches": [
            {"query": item.get("query"),
             "source": "serper-related", "from_seed": seed}
            for item in raw.get("relatedSearches", [])
        ],
        "ads": [
            {"title": item.get("title"), "link": item.get("link"),
             "snippet": item.get("snippet"), "displayUrl": item.get("displayUrl"),
             "position": item.get("position"),
             "source": "serper-ads", "from_seed": seed}
            for item in raw.get("ads", [])
        ],
        "searchParameters": raw.get("searchParameters", {}),  # echo of gl/hl/q — assert in tests
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--seeds", required=True, nargs="+")
    parser.add_argument("--gl", required=True)
    parser.add_argument("--hl", required=True)
    parser.add_argument("--num", type=int, default=20)
    args = parser.parse_args()

    if not args.run_dir.exists():
        log.error(f"run-dir does not exist: {args.run_dir}")
        return 3

    try:
        load_env(require=("SERPER_API_KEY",))
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3
    api_key = os.environ["SERPER_API_KEY"]

    raw_dir = args.run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    out_path = raw_dir / "serper.json"

    aggregated = {"by_seed": []}
    with build_client(timeout=30.0) as client:
        for seed in args.seeds:
            log.info(f"Serper: {seed!r} (gl={args.gl}, hl={args.hl})")
            try:
                raw = fetch_seed(client, seed, gl=args.gl, hl=args.hl,
                                 num=args.num, api_key=api_key)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (401, 403):
                    log.error(f"Serper auth failure: {exc.response.status_code}")
                    return 3
                log.error(f"Serper retryable failure for {seed!r}: {exc}")
                return 2
            aggregated["by_seed"].append(normalise_response(raw, seed=seed,
                                                             gl=args.gl, hl=args.hl))

    out_path.write_text(json.dumps(aggregated, indent=2), encoding="utf-8")

    organic_total = sum(len(s["organic"]) for s in aggregated["by_seed"])
    paa_total = sum(len(s["peopleAlsoAsk"]) for s in aggregated["by_seed"])
    related_total = sum(len(s["relatedSearches"]) for s in aggregated["by_seed"])
    ads_total = sum(len(s["ads"]) for s in aggregated["by_seed"])

    print(json.dumps({
        "raw_path": str(out_path),
        "seed_count": len(args.seeds),
        "organic_count": organic_total,
        "paa_count": paa_total,
        "related_count": related_total,
        "ads_count": ads_total,
        "credits_used": len(args.seeds),  # 1 credit per /search call per Serper pricing
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### tavily_extract.py — Tavily SDK with caps and failure persistence

```python
# /// script
# requires-python = ">=3.13"
# dependencies = ["tavily-python>=0.7.24", "python-dotenv>=1.0", "python-slugify>=8.0"]
# ///
"""tavily_extract.py — TavilyClient.extract() per competitor URL list; persist raw/tavily-<domain>.json.

CLI:
    uv run tavily_extract.py --run-dir <abs> \
        --competitor "tesco.com:https://tesco.com,https://tesco.com/groceries/...,..." \
        --competitor "ocado.com:https://ocado.com,..."

Caps: --max-competitors 5 (default), --max-urls-per-competitor 5 (default), extract_depth='basic'.

Stdout:
    {"competitor_count": 3, "urls_attempted": 12, "urls_succeeded": 11, "urls_failed": 1,
     "credits_used": 3}

Exit codes: 0 ok, 2 (UsageLimitExceededError → degraded; report partial), 3 fatal (auth, IO).
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.config import load_env
from lib.log import configure_logger

from slugify import slugify
from tavily import TavilyClient
from tavily import (
    InvalidAPIKeyError, MissingAPIKeyError,
    UsageLimitExceededError, BadRequestError,
)

log = configure_logger()


def parse_competitor_arg(arg: str) -> tuple[str, list[str]]:
    """'tesco.com:https://a,https://b' -> ('tesco.com', ['https://a','https://b'])."""
    domain, urls_csv = arg.split(":", 1)
    return domain.strip(), [u.strip() for u in urls_csv.split(",") if u.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--competitor", action="append", default=[],
                        help="Format: 'domain:url1,url2,...' — repeat per competitor")
    parser.add_argument("--max-competitors", type=int, default=5)
    parser.add_argument("--max-urls-per-competitor", type=int, default=5)
    args = parser.parse_args()

    if not args.competitor:
        log.error("At least one --competitor required")
        return 2

    competitors = [parse_competitor_arg(c) for c in args.competitor]
    if len(competitors) > args.max_competitors:
        log.warning(f"Trimming competitors {len(competitors)} -> {args.max_competitors} (Pitfall 8)")
        competitors = competitors[:args.max_competitors]

    if not args.run_dir.exists():
        log.error(f"run-dir does not exist: {args.run_dir}")
        return 3

    try:
        load_env(require=("TAVILY_API_KEY",))
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    raw_dir = args.run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

    total_attempted = total_succeeded = total_failed = 0
    for domain, urls in competitors:
        urls = urls[: args.max_urls_per_competitor]
        if not urls:
            continue
        log.info(f"Tavily extract: {domain} ({len(urls)} URLs, basic depth)")
        try:
            response = client.extract(
                urls=urls,
                extract_depth="basic",      # explicit per Pitfall 8
                format="markdown",
                include_usage=True,
            )
        except (InvalidAPIKeyError, MissingAPIKeyError) as exc:
            log.error(f"Tavily auth failure: {exc}")
            return 3
        except UsageLimitExceededError as exc:
            log.error(f"Tavily quota exceeded — degrading: {exc}")
            return 2
        except BadRequestError as exc:
            log.error(f"Tavily bad request for {domain}: {exc}")
            # skip this competitor, continue with others
            continue

        out_path = raw_dir / f"tavily-{slugify(domain)}.json"
        # Annotate every result with source + competitor so merge_signals can fan out
        annotated = {
            "domain": domain,
            "source": "tavily-extract",
            "results": [
                {**r, "source": "tavily-extract", "competitor_domain": domain}
                for r in response.get("results", [])
            ],
            "failed_results": response.get("failed_results", []),
            "response_time": response.get("response_time"),
            "request_id": response.get("request_id"),
            "usage": response.get("usage", {}),
        }
        out_path.write_text(json.dumps(annotated, indent=2), encoding="utf-8")

        total_attempted += len(urls)
        total_succeeded += len(annotated["results"])
        total_failed += len(annotated["failed_results"])

    print(json.dumps({
        "competitor_count": len(competitors),
        "urls_attempted": total_attempted,
        "urls_succeeded": total_succeeded,
        "urls_failed": total_failed,
        "credits_used": -(-total_succeeded // 5),  # ceil(succeeded / 5) — basic = 1 credit / 5 URLs
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### lib/http.py — httpx client factory with retries

```python
"""lib/http.py — shared httpx.Client builder with httpx-retries RetryTransport.

Used by serp_fetch.py (Serper REST). Tavily uses its own SDK-managed client.

Retry policy (verified against PITFALLS § Error Handling):
    total=3 retries
    backoff_factor=1.0  (sleep 1s, 2s, 4s with jitter)
    status_forcelist=[429, 500, 502, 503, 504]
    Retry-After header honoured (httpx-retries default)
"""
from __future__ import annotations
import httpx
from httpx_retries import Retry, RetryTransport


def build_client(*, timeout: float = 30.0) -> httpx.Client:
    """Return a configured sync httpx.Client; caller is responsible for context-manager close."""
    retry = Retry(total=3, backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504])
    transport = RetryTransport(retry=retry)
    return httpx.Client(
        transport=transport,
        timeout=timeout,
        follow_redirects=False,  # Serper returns direct JSON; redirects would be suspicious
    )
```

### lib/canon.py — canonicalisation (Pitfall 7 mitigation)

```python
"""lib/canon.py — close-variant detection via lemma + token-sort hashing.

Algorithm:
    1. Lowercase + strip punctuation.
    2. Tokenize on whitespace.
    3. Drop empty tokens; preserve question-keyword order if first token is a question word.
    4. For non-question keywords:
         - Singularise each noun via inflect.singular_noun (returns False if already singular).
         - Sort tokens alphabetically.
    5. Join + sha256 first 16 hex chars = lemma_hash.

    Question keywords (start with how/what/why/is/can/who/where/when):
         - Preserve word order; lowercase + singularise but do NOT sort.
         - Reason: "how to deliver groceries" != "groceries delivery how".

Returns (canonical_form, lemma_hash). canonical_form is the lowercased + punctuation-stripped
input; merge_signals.py picks the *shortest* surface form within a hash group as the display form.
"""
from __future__ import annotations
import hashlib
import re
import inflect

_INF = inflect.engine()
_QUESTION_PREFIXES = {"how", "what", "why", "is", "are", "can", "who", "where", "when", "do", "does"}
_PUNCT = re.compile(r"[^\w\s-]")  # keep hyphens; strip everything else


def _singularise(token: str) -> str:
    sing = _INF.singular_noun(token)
    return sing if sing else token


def canonicalise(keyword: str) -> tuple[str, str]:
    """Return (canonical_form, lemma_hash). Empty input raises ValueError."""
    if not keyword or not keyword.strip():
        raise ValueError("empty keyword")
    norm = _PUNCT.sub(" ", keyword.lower()).strip()
    norm = re.sub(r"\s+", " ", norm)
    tokens = norm.split()
    if not tokens:
        raise ValueError(f"keyword {keyword!r} produced no tokens after normalisation")

    is_question = tokens[0] in _QUESTION_PREFIXES
    lemmas = [_singularise(t) for t in tokens]

    if is_question:
        hash_input = " ".join(lemmas)  # preserve order
    else:
        hash_input = " ".join(sorted(lemmas))

    digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]
    return norm, digest
```

### Test pattern (respx mocking Serper)

```python
# scripts/tests/test_serp_fetch.py
import json
import pytest
import respx
from httpx import Response


@respx.mock
def test_serp_fetch_passes_locale_in_request_body(tmp_path, monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    run_dir = tmp_path / "run"
    (run_dir / "raw").mkdir(parents=True)

    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "serper_search_uk.json").read_text()
    )
    route = respx.post("https://google.serper.dev/search").mock(
        return_value=Response(200, json=fixture)
    )

    import serp_fetch
    rc = serp_fetch.main_with_args([
        "--run-dir", str(run_dir),
        "--seeds", "grocery delivery",
        "--gl", "uk",
        "--hl", "en-GB",
    ])
    assert rc == 0

    # Assert the OUTGOING request carried the locale params
    assert route.called
    sent_body = json.loads(route.calls[0].request.content)
    assert sent_body["gl"] == "uk"
    assert sent_body["hl"] == "en-GB"
    assert sent_body["q"] == "grocery delivery"
```

### Source: code patterns above synthesised from
- Tavily SDK reference (https://docs.tavily.com/sdk/python/reference) — verified extract() signature, response shape, exception classes
- Tavily extract API reference (https://docs.tavily.com/documentation/api-reference/endpoint/extract) — verified credit cost (1 / 5 URLs basic)
- httpx-retries README (https://github.com/will-ockmore/httpx-retries) — Retry/RetryTransport API (v0.5.0)
- Phase 1 lib/config.py + lib/io.py + run_init.py for invocation conventions
- Serper community walkthroughs (rramos.github.io, scrape.do, sim.ai docs) for response shape
- inflect 7.5+ docs (https://inflect.readthedocs.io/) for singular_noun behaviour

---

## State of the Art

| Old Approach | Current Approach (May 2026) | When Changed | Impact |
|--------------|------------------------------|--------------|--------|
| `requests` + `urllib3.Retry` adapter | `httpx` + `httpx-retries` `RetryTransport` | httpx 0.28 stable; httpx-retries 0.5.0 (Apr 2026) | Single client across sync/async; transport-layer retry instead of adapter wrapping |
| Mock with `unittest.mock.patch("httpx.post")` | `respx.mock` route patterns | respx 0.20+ (2024) | Asserts request shape (URL, headers, query, body); cleaner than mock chain |
| spaCy/NLTK lemmatisation for keyword normalisation | `inflect.singular_noun` + token-sort hash for noun-phrase domains | jaraco/inflect 7.x (2024) | 200KB pure Python vs 600MB models; sufficient for PPC keyword space |
| `tavily_crawl` for competitor LP mining | `tavily_extract` with curated URL list, `extract_depth='basic'` | Tavily community guidance + ROADMAP Phase 2 SC2 | 5–20× cost reduction per run; bounded vs unbounded |
| Wrapping every Claude tool in a Python script | Skill-prompt direct tool calls (WebSearch, Read, Write) for built-ins | Anthropic skill best-practices (2025) | Removes subprocess boundary; lets Claude orchestrate naturally |

**Deprecated/outdated:**
- `aiohttp` for sync-only PPC tooling — `httpx` covers both with one library and matches the SDK ecosystem
- Hand-rolled exponential backoff loops — `httpx-retries` is small and maintained
- `requests-cache` for SERP caching — explicitly out of v1 scope; v2 caching will use a hash-keyed `raw/_cache/` directory anyway
- `pickle`-based variant detection — JSON-only on disk; sha256 lemma hashes are language-stable

---

## Common Pitfalls

### Pitfall 4: Geo / Language Drift (Phase 2 owns)

**What goes wrong:** Brief says UK; Serper returns US results because `gl`/`hl` weren't passed. Currency/spelling drift through to ad copy section.

**Why it happens:** Serper defaults follow the API key's account region or fall back to US. WebSearch tool inside Claude Code may not honour a locale param the same way Serper does.

**How to avoid:**
- `serp_fetch.py` REQUIRES `--gl` and `--hl` flags (no defaults, fail loud). Skill prompt derives them from brief.md `Location` and `Language` fields.
- Tavily extract has no built-in country param, but `country=` is documented for `tavily.search()` (out of scope). For extract, the URL itself encodes the locale (use `.co.uk` competitor URLs when brief is UK).
- WebSearch: embed locale terms in the query string itself ("UK", "London", "in en-GB"). Don't rely on `user_location` API params.
- Test asserts `gl=uk`/`hl=en-GB` appear in the recorded outgoing request body (via respx).
- Persist `searchParameters` (Serper's echo of the locale) in `raw/serper.json`; deferred Phase 4 lint reads it back.

**Warning signs:** Currency symbols mismatch the brief's region. Competitor names in the report aren't operating in the brief's geography. Spelling drifts (favorite/favourite mixed).

### Pitfall 6: Long-Tail Noise (Phase 2 owns)

**What goes wrong:** PAA + LLM expansion generates hundreds of grammatically-valid-but-zero-volume keywords. Report bloats; PPC manager wastes review time.

**Why it happens:** LLMs *expand* on PAA snippets and invent variations. No volume API in v1 to filter zero-volume terms.

**How to avoid:**
- **Extract, don't generate.** Phase 2 surfaces only verbatim n-grams that appeared in source data — Serper PAA, related, organic titles/snippets; Tavily extracted page chunks; WebSearch snippets. The skill prompt's keyword extraction step is "what phrases appear in this text", NOT "what phrases are similar to this".
- Cap keyword length at 7 words (drop longer); document threshold in `merge_signals.py`.
- Defer `source_diversity ≥ 2` filter to Phase 3 (it's a ranking concern, not a harvest one), but Phase 2 keeps the data needed to apply that filter.
- `merge_signals.py` deduplicates first — single-mention noise is at least collapsed.

**Warning signs:** Report has >200 keywords. >30% have `source_diversity` = 1 (Phase 3 can warn). Multiple keywords differ only by stop-words.

### Pitfall 7: Close-Variant Duplicates (Phase 2 owns)

**What goes wrong:** "grocery delivery", "groceries delivery", "grocery deliveries" become 3 rows. Each has frequency 1; canonical "grocery delivery" should have frequency 3.

**Why it happens:** Naive dedup uses exact-string match. Source data is messy (PAA gives "Grocery Delivery", related gives "grocery deliveries", Tavily gives "delivered groceries").

**How to avoid:**
- `lib/canon.py` (designed above): lowercase → strip punctuation → singularise nouns via `inflect` → token-sort (non-question keywords) → sha256 first 16 hex chars = `lemma_hash`.
- Group by `lemma_hash` in `merge_signals.py`; pick the shortest surface form as canonical; preserve all observed surfaces in `variants[]`.
- Question keywords (start with how/what/why/is/can/who/where/when) preserve word order — "how to deliver groceries" ≠ "groceries delivery how".
- Apply BEFORE source-diversity counting (otherwise distinct sources for the same canonical term are spread across variant rows).

**Warning signs:** Two rows differ by 1 character. Frequency distribution is suspiciously flat (everything is 1).

### Pitfall 8: Tavily Cost Blowup (Phase 2 owns)

**What goes wrong:** `tavily_crawl` spiders 500+ pages per competitor; bill hits $25–100 per run.

**Why it happens:** Crawl combines mapping + extraction; "1 URL" can spider hundreds of pages. Defaults prefer broad over narrow.

**How to avoid:**
- `tavily_extract` (NOT `tavily_crawl`); enforced in code (only `client.extract()` is called; `client.crawl` is never imported).
- Hard caps in CLI: `--max-competitors 5` (default), `--max-urls-per-competitor 5` (default). `argparse` defaults; user can lower but not raise via env without explicit code change.
- `extract_depth='basic'` explicit (1 credit per 5 successful URLs vs 2 for advanced).
- Per-call credit count logged to stderr and surfaced in stdout JSON (`credits_used`).
- Persist `failed_results` — they don't bill in some Tavily plans but visibility prevents silent retries.

**Warning signs:** Run consumes >50 Tavily credits. Run duration exceeds 5 minutes. Tavily monthly bill exceeds Serper monthly bill (Tavily ~5–10× per call).

### Pitfall 21: Provenance — Untraceable Keyword Inclusion (Phase 2 owns)

**What goes wrong:** PPC manager asks "why is `grocery delivery sunday` in the report?". Operator can't answer; trust erodes.

**Why it happens:** Per-keyword provenance not logged. Aggregation throws away the source URL/snippet.

**How to avoid:**
- Every keyword in `keywords.json` carries `sources: [{source, snippet, url, from_seed | competitor_domain | from_query, captured_at}, ...]` — at least one entry per source-fragment that contributed.
- `raw/` is preserved verbatim (already mandated by ROADMAP Phase 6 SC4 + .gitignore exception for `raw/`); merge step does not delete from raw.
- Phase 6 report includes a hidden `<details>` block per keyword surfacing top 2 sources (deferred to Phase 6, but the data must be ready in Phase 2).
- `merge_signals.py` test asserts: given a keyword that appears in 2 raw files, its merged row has `len(sources) >= 2`.

**Warning signs:** Operator answers "I don't know why it's there." Same question asked twice for two different keywords.

### Phase-2-cross-cutting: Tavily silent partial failures

**What goes wrong:** `client.extract(urls=[a, b, c])` returns 200 with `results=[{a}, {b}]` and `failed_results=[{c, error: timeout}]`. Code that reads only `results` silently drops `c`.

**How to avoid:** Persist `failed_results` to `raw/tavily-<domain>.json` and surface count in stdout JSON. Test fixture `tavily_extract_2urls.json` has one success + one failed_result; assertions check both arrays land on disk.

### Phase-2-cross-cutting: Serper ads block sometimes empty

**What goes wrong:** Code does `raw["ads"][0]["title"]` and KeyErrors on a brief whose seeds are all informational queries.

**How to avoid:** Defensive `.get("ads", [])` everywhere. Fixture `serper_empty_ads.json` exercises this; test asserts no exception and `ads_count: 0` in stdout.

---

## Locale Plumbing — Source-by-Source

| Source | How locale is passed | Verification |
|--------|----------------------|--------------|
| Serper | `gl` and `hl` keys in POST body to `/search`. `gl` is country code (e.g., `"uk"`), `hl` is language tag (e.g., `"en-GB"`). | Test asserts both fields present in respx-captured request body. `searchParameters` in response echoes them; persist for downstream lint. |
| Tavily extract | No native country param on `/extract`. Locale is implicit in the competitor URLs supplied (use country-TLD URLs when applicable). | Skill prompt curates URLs; Phase 2 doesn't enforce TLD match (would be brittle for global brands). Phase 5 will revisit when ad-copy sourcing fans out. |
| WebSearch (Claude Code in-skill tool) | API surface accepts `user_location` (city/region/country/timezone) but the in-skill exposure is unreliable. **Mitigation:** embed locale in the query string itself ("UK same-day grocery delivery", "London grocery delivery 2026"). | Skill prompt records each WebSearch query in `raw/websearch-baseline.json` `queries[]` with the locale annotation; merge step asserts queries reflect brief locale. |

**Brief → Locale derivation (skill prompt):**
- `gl`: lowercased country code from `Location` field (e.g., "UK" → "uk", "US-California" → "us"). Skill applies a lookup for common cases ("United Kingdom", "Britain", "England" → "uk").
- `hl`: language tag from `Language` field (e.g., "en-GB" stays "en-GB"; "English" → "en"; "German" → "de-DE" only if location implies it).

---

## Seed Keyword Generation Strategy

**Recommendation:** LLM-driven, in the skill prompt, after Phase 1 brief.md is sealed.

**Reasoning:**
- The skill has the validated brief in context (industry, product, location, audience, optional brand/competitor terms).
- A Python script would either re-implement that reasoning naively (string templates) or call out to Claude (defeats the purpose).
- Seed count: **5–15 phrases**, derived from product + audience modifiers + 2–3 PAA-anticipating angles. Skill prompt enumerates 5–8 as MUST and 5–7 as STRETCH; if brief is rich, more; if narrow vertical, fewer. Don't force a fixed count.

**SKILL.md additions (Phase 2 Step 1, after Phase 1 Step 5 confirm):**

```markdown
### Step 6: Generate seed keywords

From the validated brief (read brief.md if needed), generate 5–15 seed phrases:
1. The exact product phrase ("same-day grocery delivery")
2. 2–3 product+audience composites ("grocery delivery for busy parents")
3. 2–3 product+location composites ("london grocery delivery", "uk same-day delivery")
4. 1–2 product+intent variations ("best grocery delivery", "cheap grocery delivery uk")
5. 1–2 brand-comparison variations IF Brand terms field present ("tesco vs ocado delivery")

Skip variations that contradict explicit Geo exclusions or Language exclusions in brief.

Write the seeds list to a temp file (one per line) for visibility, then pass via --seeds CLI:
    --seeds "same day grocery delivery uk" "london grocery delivery" "tesco delivery" ...
```

**Why per-line temp file plus `--seeds` CLI args:** Reading from stdin would conflict with run_init.py's stdin convention; CLI args are the cleanest pass-through. Quoting handled by Bash; SKILL.md exemplifies once.

---

## Source Attribution Data Model

Every keyword in `keywords.json` carries provenance:

```json
{
  "canonical": "grocery delivery",
  "lemma_hash": "a4b2c8d1e7f93502",
  "variants": ["grocery delivery", "groceries delivery", "grocery deliveries"],
  "signal_count": 5,
  "source_diversity": 3,
  "sources": [
    {
      "source": "serper-paa",
      "snippet": "How does grocery delivery work?",
      "url": "https://google.com/search?q=...",
      "from_seed": "same day grocery delivery uk",
      "captured_at": "2026-05-08T14:30:30Z"
    },
    {
      "source": "serper-related",
      "query": "grocery delivery near me",
      "from_seed": "same day grocery delivery uk",
      "captured_at": "2026-05-08T14:30:30Z"
    },
    {
      "source": "tavily-extract",
      "competitor_domain": "tesco.com",
      "url": "https://tesco.com/groceries/...",
      "snippet_excerpt": "Order grocery delivery in 1 hour...",
      "captured_at": "2026-05-08T14:31:12Z"
    }
  ]
}
```

**Source taxonomy** (locked here so Phase 3's `source_diversity` counts the same way):

| Source string | Producer | Counts as 1 of `source_diversity` |
|---------------|----------|----------------------------------|
| `serper-organic` | serp_fetch.py | yes |
| `serper-paa` | serp_fetch.py | yes |
| `serper-related` | serp_fetch.py | yes |
| `serper-ads` | serp_fetch.py | yes (caveat: Phase 5 may treat ads-only keywords specially) |
| `tavily-extract` | tavily_extract.py | yes |
| `websearch-baseline` | skill prompt → Write tool | yes |

**Max `source_diversity` = 6.** A keyword surfaced across all four Serper feature types + Tavily + WebSearch is exceptionally well-attested. Phase 3 ranking will weight this highly.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (already in use Phase 1) |
| Config file | none (Phase 1 ad-hoc style); CLAUDE.md notes Phase 2 promotion to `pyproject.toml` deferred to a later phase. Quick start uses `uv run --with` flags. |
| Quick run command | `uv run --with pytest --with respx --with python-dotenv --with python-slugify --with httpx --with httpx-retries --with tavily-python --with inflect pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| Full suite command | (same) — Phase 2 has no slow tests; all unit + integration with mocked HTTP |
| Mocking library | `respx` 0.22+ (httpx-native; mocks both serp_fetch.py and tavily_extract.py because Tavily SDK uses httpx internally) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIGL-01 | `serp_fetch.py` produces `raw/serper.json` with organic + PAA + related + ads | unit | `pytest tests/test_serp_fetch.py::test_writes_serper_json -x` | ❌ Wave 0 |
| SIGL-01 | `serp_fetch.py` defensively handles empty ads block | unit | `pytest tests/test_serp_fetch.py::test_empty_ads_no_error -x` | ❌ Wave 0 |
| SIGL-01 | `serp_fetch.py` returns exit 2 on retried 429, exit 3 on 401 | unit | `pytest tests/test_serp_fetch.py::test_exit_codes -x` | ❌ Wave 0 |
| SIGL-02 | `tavily_extract.py` writes per-domain JSON via SDK | unit | `pytest tests/test_tavily_extract.py::test_writes_per_domain -x` | ❌ Wave 0 |
| SIGL-02 | `tavily_extract.py` enforces 5×5 caps | unit | `pytest tests/test_tavily_extract.py::test_caps_enforced -x` | ❌ Wave 0 |
| SIGL-02 | `tavily_extract.py` persists failed_results | unit | `pytest tests/test_tavily_extract.py::test_failed_results_persisted -x` | ❌ Wave 0 |
| SIGL-02 | `tavily_extract.py` uses `extract_depth='basic'` | unit | `pytest tests/test_tavily_extract.py::test_extract_depth_basic -x` | ❌ Wave 0 |
| SIGL-03 | WebSearch invocation flow documented in SKILL.md | manual smoke | run skill, paste brief, observe WebSearch call → `raw/websearch-baseline.json` written via Write | manual — VALIDATION.md row |
| SIGL-04 | Locale params land in Serper request body | unit (respx-asserted) | `pytest tests/test_serp_fetch.py::test_locale_in_request -x` | ❌ Wave 0 |
| SIGL-04 | Locale params logged in `raw/serper.json` (`searchParameters` echo) | unit | `pytest tests/test_serp_fetch.py::test_locale_persisted -x` | ❌ Wave 0 |
| SIGL-04 | Skill prompt embeds locale in WebSearch queries | manual smoke | inspect SKILL.md Phase 2 Step 7 for "include UK / London in query" rule | manual — VALIDATION.md row |
| SIGL-05 | Every keyword in `keywords.json` has non-empty `sources[]` | unit | `pytest tests/test_merge_signals.py::test_every_keyword_has_sources -x` | ❌ Wave 0 |
| SIGL-05 | `source_diversity` reflects distinct sources | unit | `pytest tests/test_merge_signals.py::test_source_diversity_count -x` | ❌ Wave 0 |
| SIGL-06 | Close variants merge via lemma hash | unit | `pytest tests/test_lib_canon.py::test_grocery_variants_merge -x` | ❌ Wave 0 |
| SIGL-06 | Question keywords preserve word order | unit | `pytest tests/test_lib_canon.py::test_question_keywords_no_sort -x` | ❌ Wave 0 |
| SIGL-06 | Empty / whitespace input raises ValueError | unit | `pytest tests/test_lib_canon.py::test_empty_raises -x` | ❌ Wave 0 |
| (cross) | `lib/http.py` retries 429 then 200 on third attempt | unit | `pytest tests/test_lib_http.py::test_retry_on_429 -x` | ❌ Wave 0 |
| (cross) | `lib/http.py` does not retry 401 | unit | `pytest tests/test_lib_http.py::test_no_retry_on_401 -x` | ❌ Wave 0 |
| (cross) | `merge_signals.py` writes valid `keywords.json` | integration | `pytest tests/test_merge_signals.py::test_end_to_end_with_fixtures -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest .claude/skills/google-ad-research/scripts/tests/ -x` (full Phase 2 suite — all tests are fast, no real API calls).
- **Per wave merge:** same.
- **Phase gate:** Full suite green AND a manual smoke test with a real (free) brief, real Serper credit, real Tavily credit (acceptable cost: ~5 Serper + ~3 Tavily credits = pennies) before `/gsd:verify-work`. Document the smoke run in `VALIDATION.md` ("Manual: ran `keyword research for same-day grocery delivery in UK targeting busy parents`; observed `raw/serper.json`, `raw/tavily-tesco-com.json`, `raw/websearch-baseline.json`, and `keywords.json` populated; spot-checked 10 keywords had non-empty `sources[]`.").

### Wave 0 Gaps

All required tests/ files are NEW. Wave 0 must scaffold:

- [ ] `scripts/tests/fixtures/serper_search_uk.json` — recorded full Serper response for a UK grocery query (record once with real key, scrub PII, commit; ~30 KB JSON)
- [ ] `scripts/tests/fixtures/serper_empty_ads.json` — variant of the above with `ads: []` (hand-edit)
- [ ] `scripts/tests/fixtures/tavily_extract_2urls.json` — recorded Tavily extract response with 1 success + 1 failed_result (record once; ~10 KB)
- [ ] `scripts/tests/test_lib_http.py` — retries 429 / 5xx; doesn't retry 401; honours Retry-After
- [ ] `scripts/tests/test_lib_canon.py` — variant collapse; question preservation; empty raises
- [ ] `scripts/tests/test_serp_fetch.py` — locale assertion (respx); empty ads; exit codes
- [ ] `scripts/tests/test_tavily_extract.py` — caps; failed_results; extract_depth; exit codes (mock TavilyClient via respx since SDK uses httpx; or monkeypatch `TavilyClient.extract` directly — recommendation: monkeypatch is simpler given SDK has its own URL conventions)
- [ ] `scripts/tests/test_merge_signals.py` — sources array; source_diversity; canonical surface form selection
- [ ] `scripts/tests/conftest.py` — extend with `tmp_run_dir` (creates `<tmp>/run/raw/`), `mock_env` (sets SERPER_API_KEY/TAVILY_API_KEY), `serper_fixture` (loads JSON), `tavily_fixture`

Framework install: covered by `uv run --with` flags; no project-wide install needed. If the operator wants a single `uv sync` invocation, Phase 2 may emit a minimal `pyproject.toml` but that is optional — keep PEP 723 inline metadata as the contract (matches Phase 1 STATE decision).

---

## Wave Plan (information for the planner — not prescriptive)

The planner will choose the wave structure; this is the dependency graph the research surfaces:

- **Wave 0 (RED state):** test scaffolding + fixtures. All tests in the table above must exist and FAIL because no production code exists yet. Includes `scripts/tests/conftest.py` extension and the three fixture JSONs. No production code in this wave.
- **Wave 1 (foundation):** `lib/http.py` + `lib/canon.py` + their tests turning GREEN. These are pure libraries with no script entry points; they're prerequisites for everything in Wave 2.
- **Wave 2 (parallel):** `serp_fetch.py` + `tavily_extract.py` developed in parallel — different APIs, different output files, no shared module beyond `lib/`. Tests in `test_serp_fetch.py` and `test_tavily_extract.py` turn GREEN.
- **Wave 3:** `merge_signals.py` + `test_merge_signals.py`. Depends on Wave 2 outputs (consumes `raw/*.json`).
- **Wave 4 (sequential, last):** SKILL.md update — adds Phase 2 Steps 6–10 (seed gen → run scripts → invoke WebSearch → run merge → confirm + stop). Depends on Waves 1–3 because the skill quotes script invocations.

**Justification for Wave 2 parallelism:** `serp_fetch.py` and `tavily_extract.py` share `lib/http.py` only at import-time and `lib/config.py` for env loading; they touch disjoint output files; their tests use disjoint fixtures; they can be merged independently.

---

## Open Questions

1. **WebSearch query count and locale embedding strategy**
   - What we know: Pitfall 4 says embed locale in query string (e.g., "UK", "London") because `user_location` exposure to skills is unreliable.
   - What's unclear: Whether to issue 3 broad + 2 narrow queries, or 5 narrow ones; whether to include brand-vs-competitor as a baseline query.
   - Recommendation: Skill prompt issues 3–5 queries (product, product+location, product+audience, optional brand+location); SKILL.md exemplifies the count.

2. **Promote ad-hoc tests to `pyproject.toml` now or later?**
   - What we know: CLAUDE.md says "Phase 2 promotes to a proper pyproject.toml" — but Phase 1's STATE.md decision says "Phase 1 runs ad-hoc (no pytest.ini)".
   - What's unclear: Whether the lift is worth it now, given `uv run --with` works.
   - Recommendation: Defer to Phase 6 (when Phase 6 introduces `render_report.py` + tabulate, which may share more deps); keep Phase 2 ad-hoc with a one-paragraph `scripts/tests/README.md` documenting the invocation.

3. **Per-call meta JSON (`raw/<source>-meta.json`) — ship in Phase 2 or wait?**
   - What we know: Pitfall 4/8/21 all benefit from per-call timing/locale/credit metadata.
   - What's unclear: Whether merging meta into the existing `raw/serper.json` or a sidecar is better.
   - Recommendation: Keep meta inline in `raw/serper.json` (`searchParameters` echo + `credits_used`) and `raw/tavily-<domain>.json` (`response_time` + `usage`); skip the sidecar in v1.

4. **Tavily SDK mock strategy**
   - What we know: Tavily uses httpx internally; respx CAN intercept it.
   - What's unclear: Whether respx routes match the SDK's exact URL shape across SDK versions.
   - Recommendation: Use `monkeypatch.setattr("tavily.TavilyClient.extract", lambda self, **kw: <fixture>)` for `test_tavily_extract.py` — robust against SDK URL changes. Use respx for `lib/http.py` and `serp_fetch.py` where we own the URL.

5. **Should the skill prompt verify `raw/keywords.json` exists before declaring Phase 2 complete?**
   - What we know: Run isolation + filesystem-as-database means stale state from a previous failed run is possible if operator re-runs without cleaning.
   - What's unclear: Whether the merge step should error on partial inputs or proceed defensively.
   - Recommendation: `merge_signals.py` errors with exit 3 if at least one of `raw/serper.json` or `raw/tavily-*.json` is missing (websearch-baseline is optional — skill may have skipped it). Skill prompt verifies the existence of `keywords.json` post-merge before printing "Phase 2 complete."

---

## Sources

### Primary (HIGH confidence)

- [Tavily Python SDK Reference (docs.tavily.com)](https://docs.tavily.com/sdk/python/reference) — verified extract() signature: `extract(urls, include_images=False, extract_depth="basic", format="markdown", timeout=None, include_favicon=False, include_usage=False, query=None, chunks_per_source=3)`; response shape `{results, failed_results, response_time, request_id}`; max 20 URLs.
- [Tavily Extract API Reference (docs.tavily.com)](https://docs.tavily.com/documentation/api-reference/endpoint/extract) — verified credit cost: 1 credit per 5 URLs basic, 2 credits per 5 URLs advanced; HTTP error codes 400/401/429/432/433/500.
- [tavily-python on PyPI](https://pypi.org/project/tavily-python/) — verified version 0.7.24 (Apr 27 2026); exception classes `InvalidAPIKeyError, UsageLimitExceededError, MissingAPIKeyError, BadRequestError` exported from `tavily`; `ForbiddenError, TimeoutError` in `tavily.errors`.
- [httpx-retries on GitHub](https://github.com/will-ockmore/httpx-retries) — verified version 0.5.0 (Apr 20 2026); `Retry(total, backoff_factor, ...)` + `RetryTransport(retry=...)`; sync + async support; pip install pkg.
- [Web Search Tool — Anthropic API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool) — verified result shape `{url, title, page_age, encrypted_content}`; `user_location` parameter for API; `max_uses` cap; pricing $10 per 1,000 searches.
- [Extend Claude with skills — Claude Code docs](https://code.claude.com/docs/en/skills) — verified `${CLAUDE_SKILL_DIR}` substitution, `allowed-tools` frontmatter pre-approval, dynamic-context `!`backtick injection; skill content lifecycle; subagent fork for context isolation.
- [respx on GitHub](https://github.com/lundberg/respx) and [respx user guide](https://lundberg.github.io/respx/guide/) — verified pytest fixture / decorator / context manager modes; route patterns; request assertions.
- [PEP 723 — Inline script metadata](https://peps.python.org/pep-0723/) — inline metadata syntax inherited Phase 1.
- [inflect on PyPI](https://pypi.org/project/inflect/) and [inflect docs (readthedocs)](https://inflect.readthedocs.io/) — `singular_noun(word)` returns singular or False; pure Python; current 7.5+.

### Secondary (MEDIUM confidence — verified against authoritative)

- [Serper.dev landing page](https://serper.dev/) — pricing $0.30 / 1k, 2,500 free credits; endpoint /search /news /places.
- [Serper community walkthroughs](https://docs.sim.ai/tools/serper) — `q`, `gl`, `hl`, `num`, `type` parameters; response includes `searchParameters`, `organic`, `peopleAlsoAsk`, `relatedSearches`, `ads`, `knowledgeGraph`. Cross-verified against [rramos.github.io/2024/06/13/serper](https://rramos.github.io/2024/06/13/serper/) and [scrape.do guide](https://scrape.do/blog/google-serp-api/).
- [HTTPX vs Requests vs AIOHTTP comparison (Speakeasy 2026)](https://www.speakeasy.com/blog/python-http-clients-requests-vs-httpx-vs-aiohttp) — supports httpx + httpx-retries recommendation.

### Tertiary (LOW confidence — needs validation)

- Lemmatisation library trade-offs across `inflect` / `simplemma` / `lemminflect` for English noun-phrase canonicalisation: cross-checked GeeksforGeeks, Stackabuse, Bomberbot guides — none authoritative; recommendation is opinion-driven and should be calibrated after first 3–5 real runs (does the lemma-hash actually merge close variants in production data?).

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Serper REST + Tavily SDK + httpx-retries verified against official sources May 2026.
- Architecture: HIGH — three-file pattern (per-script raw + central merge) inherits cleanly from Phase 1 + STACK + ARCHITECTURE research, no novel patterns introduced.
- Pitfalls: HIGH — pitfalls 4, 6, 7, 8, 21 already enumerated in PITFALLS.md with concrete mitigations; this phase implements them rather than discovering new ones.
- Code examples: MEDIUM — patterns are verified individually but the exact Python signatures will be validated by the test suite in Wave 0–2; small adjustments expected during implementation.
- Validation architecture: HIGH — every requirement has a unit-testable assertion via respx + monkeypatch; manual smoke covers SIGL-03 (skill prompt) and the locale-embedding rule.
- Lemmatisation library: MEDIUM — `inflect` is the right pick for grocery-style English noun phrases, but real-world keyword data may surface edge cases the recommendation doesn't anticipate. Calibrate after 3–5 runs.

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days for stable APIs; revisit sooner if Tavily SDK has a minor-version bump or Serper introduces breaking response-shape changes — unlikely in window).
