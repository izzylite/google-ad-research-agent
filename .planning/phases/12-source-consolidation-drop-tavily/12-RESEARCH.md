# Phase 12: Source Consolidation (Drop Tavily) — Research

**Researched:** 2026-05-14
**Domain:** Vendor consolidation / dependency removal + Claude WebFetch tool integration
**Confidence:** HIGH

## Summary

Phase 12 is overwhelmingly a **deletion/refactor phase** with one narrow integration twist: replacing the only Phase 5 customer-facing benefit Tavily provided (landing-page raw_content extraction) with Claude Code's built-in `WebFetch` tool, invoked directly from `SKILL.md` per the same pattern already used for WebSearch baseline in Step 7. There are no new libraries to introduce, no new APIs to learn — the work is finding every Tavily touchpoint and removing it cleanly while preserving the downstream contract that `render_report.py` expects (`raw/competitor-intel.json` with `clusters[].advertisers[].headline/cta/offer`-ish fields, plus a new `raw/competitor-landing-pages.json` that SKILL.md writes).

The "research" risk here is not technical novelty — it is **completeness**. Tavily references must be hunted across 11 distinct surfaces (script, config, env example, pyproject deps, tests, fixtures, references, SKILL.md, merge_signals source taxonomy, README, REQUIREMENTS.md). Missing even one breaks the "single source-list" invariant the project relies on (Pitfall 4: source attribution drift). The Pulse drop (PULSE-10..12) and Competitor-Intel drop (TVLY-01..04 + WFCH-01..04) are independently scoped — they share zero code paths after deletion — so plans can split cleanly.

**Primary recommendation:** Split Phase 12 into three plans + a Wave 0 audit:
1. **Wave 0** — RED: extend `test_competitor_intel.py` (Tavily mocks removed, WebFetch contract asserted via fixture file presence), simplify `test_pulse_synth.py` to single-source, delete `test_tavily_extract.py`. Plus a grep-based audit test that fails if any `tavily` string remains outside of git history.
2. **Wave 1 Plan A** — Code deletion + competitor refactor: delete `tavily_extract.py`, refactor `competitor_intel.py` to drop the Tavily branch, refactor `pulse_fetch.py` + `pulse_synth.py` to single-source, strip env/deps/config.
3. **Wave 2 Plan B** — Documentation refactor: rewrite SKILL.md Step 19 + `references/phase5-competitor-intel.md` Step 19 to use WebFetch (mirrors Step 7 pattern), strip Tavily mention from `references/phase7-niche-pulse.md` Steps 27-30, update `lib/config.py` REQUIRED_KEYS sentinel, mark PULSE-02 deprecated in REQUIREMENTS.md.
4. **Wave 3 Plan C** — E2E smoke + verifier: full test suite green, fresh run-folder demo produces report.md with competitor section populated via WebFetch path.

## User Constraints

No CONTEXT.md exists for Phase 12 (this is a research-led phase). Phase scope is fully constrained by the requirement IDs and roadmap entry — no operator decision points to defer to.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TVLY-01 | Delete `scripts/tavily_extract.py`; any `lib/` Tavily helper removed | File exists at `.claude/skills/google-ad-research/scripts/tavily_extract.py` (162 lines, PEP 723 inline deps); no Tavily helper in `lib/`. Simple file delete. |
| TVLY-02 | Strip `TAVILY_API_KEY` from `.env.example`, `lib/config.py` REQUIRED_KEYS, project docs | `lib/config.py` line 19 has `REQUIRED_KEYS: tuple[str, ...] = ("SERPER_API_KEY", "TAVILY_API_KEY")` — sentinel only, not enforced at module load (load_env signature requires `require=` arg). `.env.example` line 2 has `TAVILY_API_KEY=tvly-...`. README + CLAUDE.md need scrub. |
| TVLY-03 | Remove `tavily-python` from `pyproject.toml`; rename/delete `tavily-*` fixture files; remove `tavily-*.json` glob references | `scripts/pyproject.toml` line 8 has `"tavily-python>=0.7.24"`. Fixture files: `tavily_extract_2urls.json`, `tavily_lp_response.json`, `tavily_news.json` (3 files). Glob: `merge_signals.py:511` (`raw_dir.glob("tavily-*.json")`). |
| TVLY-04 | Delete `tests/test_tavily_extract.py`; prune conftest fixtures; remove respx Tavily mocks | `test_tavily_extract.py` exists (131 lines, 4 tests). `conftest.py` line 53-56 has `tavily_fixture` pytest fixture — remove. No respx Tavily mocks (Tavily uses SDK, not HTTP — mocks are monkeypatch-based, see `test_tavily_extract.py:36`). |
| WFCH-01 | SKILL.md Step 19 rewritten — Claude invokes WebFetch from prompt for top 3-5 advertisers per cluster | Step 19 today (in `references/phase5-competitor-intel.md`) instructs Claude to extract headline/CTA/offer from Tavily `raw_content`. WebFetch pattern in Step 7 of SKILL.md (lines 186-217) is the template: WebSearch is invoked, results aggregated, JSON written via Write tool. |
| WFCH-02 | Skill writes `{headline, cta, offer}` per advertiser to `raw/competitor-landing-pages.json` via Write tool (replaces `raw/tavily-<domain>.json`) | New file path. Schema must be backward-compatible with `render_report.py` competitor section (lines 242-278) which reads `clusters[].advertisers[].title/description/domain/url`. Schema decision: nested `{clusters: {cluster_name: {advertisers: [{domain, url, headline, cta, offer}]}}}` mirroring `competitor-intel.json` shape. |
| WFCH-03 | `competitor_intel.py` drops Tavily code path; keeps Serper requery + Serper-organic fallback for advertiser identity | Current `competitor_intel.py` lines 230-381 contain Tavily-specific blocks (lines 317-360). Serper requery (lines 254-275) + organic fallback (lines 287-302) are independent — preserve. Output schema changes: `advertisers[]` no longer has `raw_content` or `tavily_fetched_at`; gets `domain/url/title/description/position` from Serper ad block, no LP extract (WebFetch fills that gap via SKILL.md). |
| WFCH-04 | Source taxonomy in `merge_signals.py` removes `tavily-extract`; `webfetch-landing` is NOT merged into main keyword pool (LP extract = Phase 5 only, not keyword harvest) | `merge_signals.py:111-118` `VALID_SOURCES = frozenset({..., "tavily-extract", ...})`. Drop the string. `merge_signals.py:336-360` `read_tavily()` and `merge_signals.py:510-512` glob loop need deletion. **Do NOT add `webfetch-landing` to VALID_SOURCES** — WebFetch output stays in `raw/competitor-landing-pages.json` and is read only by `render_report.py`, never by `merge_signals.py`. |
| PULSE-10 | `pulse_fetch.py` removes `_tavily_news` call; only Serper `/news` (PULSE-01) survives | `pulse_fetch.py:118-151` defines `fetch_tavily_news()` + `normalise_tavily_news()`. Lines 234-261 are the Tavily call loop. Lines 264-265 write `tavily-news.json`. Strip all. |
| PULSE-11 | `pulse_synth.py` drops Tavily branch in trending-themes source merging | `pulse_synth.py:166-188` `load_news_items()` reads BOTH serper-news.json AND tavily-news.json — collapse to serper-only. Line 24, 446-453 reference `tavily-news.json`. Source taxonomy in theme records (line 233 `sources = sorted({...})`) will naturally become single-source `["serper-news"]`. |
| PULSE-12 | SKILL.md Steps 27-30 (Phase 7) drop Tavily news mention; REQUIREMENTS.md marks PULSE-02 deprecated | `references/phase7-niche-pulse.md` mentions "~12 Tavily credits" in Step 27 prompt and "Tavily quota" exit-code handling in Step 28. Strip both. REQUIREMENTS.md PULSE-02 (line 86) marked `[x]` complete — needs `~~PULSE-02~~ DEPRECATED — superseded by PULSE-10` strikethrough. |

## Standard Stack

### Core (unchanged from Phase 11)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.28 | Serper REST client | Already in pyproject; Phase 2 baseline |
| httpx-retries | >=0.5 | RetryTransport for Serper | Phase 2 standard; status_forcelist excludes 401 |
| python-dotenv | >=1.0 | .env loading | Phase 1 baseline; `lib/config.load_env(require=...)` API |
| python-slugify | >=8.0 | Domain → filename slug | Used by run_init.py + (formerly) tavily_extract.py |
| tabulate | >=0.9.0 | Markdown tables in render_report | Phase 6 standard |
| pytest | >=9.0.3 | Test runner | Repo-wide standard |
| respx | (transitive via pytest extras) | HTTP mocking for httpx | Serper test pattern |

### Removed (this phase)

| Library | Version | Why Removed |
|---------|---------|-------------|
| tavily-python | >=0.7.24 | Replaced by Claude Code WebFetch tool (built-in, zero deps); Serper /news covers Phase 7 single-handedly |

### Claude Code Tooling (new in this phase's SKILL.md)

| Tool | Source | Purpose |
|------|--------|---------|
| WebFetch | Claude Code built-in | Fetch advertiser landing page → markdown summary against an extraction prompt. Replaces Tavily extract for Phase 5 COMP-03 |

**Installation:**
```bash
# Remove tavily-python via uv
cd .claude/skills/google-ad-research/scripts
uv remove tavily-python  # or hand-edit pyproject.toml then `uv lock`
```

No new installs — WebFetch is built into Claude Code (verified 2026-05-14, see [Tools reference](https://code.claude.com/docs/en/tools#webfetch-tool-behavior)).

## Architecture Patterns

### Recommended Refactor Order (per-plan)

```
Wave 0: Audit + RED tests
  - Grep audit: zero "tavily" / "TAVILY" strings outside .planning/ + git history
  - test_tavily_extract.py: deleted
  - test_competitor_intel.py: Tavily mocks removed, advertiser entries asserted to have {domain, url, title, description} (no raw_content)
  - test_pulse_synth.py: single-source assertions (tavily-news source absent)
  - conftest.py: tavily_fixture removed

Wave 1: Code deletion + refactor (3 parallel sub-plans possible)
  - 1A: scripts/tavily_extract.py DELETED
  - 1B: scripts/competitor_intel.py — strip Tavily branch (lines 317-360), drop tavily-python import, refactor advertiser entry shape to Serper-only
  - 1C: scripts/pulse_fetch.py + pulse_synth.py — single-source

Wave 2: Config + env scrubbing
  - lib/config.py REQUIRED_KEYS tuple → ("SERPER_API_KEY",)
  - .env.example: remove TAVILY_API_KEY line
  - pyproject.toml: remove tavily-python>=0.7.24, regenerate uv.lock
  - merge_signals.py: VALID_SOURCES drops "tavily-extract"; read_tavily() deleted; glob loop deleted

Wave 3: Docs refactor
  - SKILL.md Phase 5 pointer text adjusted (no mention of Tavily credits)
  - references/phase5-competitor-intel.md Step 19 rewritten: WebFetch pattern
  - references/phase7-niche-pulse.md Steps 27-30: strip Tavily mentions
  - REQUIREMENTS.md PULSE-02: strikethrough + deprecation note
  - README.md / CLAUDE.md: remove TAVILY_API_KEY references

Wave 4: E2E smoke + verifier
  - Fresh run on sample brief → report.md has competitor section populated
  - 252+ tests green
  - Repo grep confirms zero "tavily" residue (outside .planning/)
```

### Pattern 1: WebFetch invocation from SKILL.md (mirrors Step 7 WebSearch baseline)

**What:** Claude reads `raw/competitor-intel.json`, iterates over top 3-5 advertiser `link` fields per cluster, invokes `WebFetch` for each with an extraction prompt, aggregates results to a single JSON, and writes via the Write tool.

**When to use:** Phase 5 Step 19 (replaces today's Tavily-driven extraction loop).

**Example — proposed SKILL.md Step 19 body:**

```markdown
### Step 19: Extract landing-page value props via WebFetch (COMP-03 + WFCH-01..02)

Read `{run_dir}/raw/competitor-intel.json` using the Read tool. For each cluster in
`competitor-intel.json["clusters"]`, iterate over the top 3-5 ads in `cluster.ads[]`
(after dedupe, advertiser_source preserved).

For each advertiser URL, invoke WebFetch with this extraction prompt:

> Extract from this landing page:
> - **headline**: the most prominent H1 or hero heading (≤10 words, verbatim — null if none).
> - **cta**: the primary call-to-action button/link text (e.g., "Order Now", "Start Free Trial" — null if none).
> - **offer**: any discount, free trial, free delivery, or price claim found verbatim
>   (e.g., "Free delivery on orders over £40", "3 months free" — null if none).
> Respond as JSON only: `{"headline": "...", "cta": "...", "offer": "..."}`.

Aggregate WebFetch responses per cluster into this schema, then write via the Write tool to
`{run_dir}/raw/competitor-landing-pages.json`:

\`\`\`json
{
  "captured_at": "<ISO timestamp>",
  "clusters": {
    "<cluster_name>": {
      "representative_keyword": "<from competitor-intel.json>",
      "advertisers": [
        {
          "domain": "<from competitor-intel.json>",
          "url": "<from competitor-intel.json>",
          "headline": "<extracted or null>",
          "cta": "<extracted or null>",
          "offer": "<extracted or null>",
          "extract_status": "ok" | "failed" | "blocked"
        }
      ]
    }
  }
}
\`\`\`

**Rules** (mirrors Step 7 WebSearch baseline rules):
- Extract VERBATIM — do not paraphrase or generate. If no headline visible, set null.
- WebFetch may redirect to a different host — if so, retry with the redirect URL once,
  then mark `extract_status: "failed"` if still no result.
- Failures (JS-heavy SPA, paywall, geo-block, 4xx/5xx) are normal — mark `failed` and
  continue. Do NOT retry beyond one redirect-follow.
- Max 5 advertisers per cluster (hard cap mirrors old Tavily cap).

**Do not advance to Step 20 until `{run_dir}/raw/competitor-landing-pages.json` exists.**
```

### Pattern 2: SKILL.md frontmatter — add WebFetch to allowed-tools

**What:** SKILL.md line 3 today reads `allowed-tools: Bash(uv run *) Read Write WebSearch`. Add `WebFetch`.

**When to use:** Required before Step 19 can invoke WebFetch — otherwise Claude Code will permission-prompt mid-run.

**Example:**
```yaml
allowed-tools: Bash(uv run *) Read Write WebSearch WebFetch
```

No domain restriction (`WebFetch(domain:example.com)`) — operator's brief can name any competitor URL, can't enumerate domains in advance.

### Anti-Patterns to Avoid

- **Do NOT add a webfetch-based Python helper script.** The whole point is mirroring SKILL.md Step 7 (WebSearch baseline) — Claude invokes WebFetch directly, writes JSON via Write tool, no helper script wraps it. Adding `webfetch_extract.py` would re-introduce the Tavily pattern this phase is dismantling.
- **Do NOT add `webfetch-landing` to `merge_signals.VALID_SOURCES`.** WFCH-04 explicitly excludes landing-page extraction from the keyword harvest pool. Competitor LP content is descriptive (headline/CTA/offer) — not source attribution for keywords.
- **Do NOT preserve `raw/tavily-<domain>.json` shape for backward compat.** Old fixture files have a `results[].raw_content` shape Tavily SDK returned; WebFetch returns a digested string per call. Schema must change — `render_report.py` is the only consumer and is in scope to refactor.
- **Do NOT delete `competitor-intel.json`.** It's still produced by `competitor_intel.py` (Serper requery is preserved). Only the `advertisers[]` array shape changes — `raw_content` and `tavily_fetched_at` fields removed.
- **Do NOT leave `tavily-python` as a "harmless transitive."** Deleting only the import lines while keeping the dep in pyproject.toml leaves a 5-minute landmine for the next operator. Audit must be exhaustive.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL → markdown extraction | `httpx + html2text` Python pipeline | Claude Code's built-in WebFetch tool | WebFetch already converts HTML→Markdown server-side with a small fast model, handles 15-min cache, and runs against an extraction prompt — re-implementing in Python re-invents 100+ lines for zero benefit |
| Landing-page "find the H1" parser | BeautifulSoup + regex heuristic stack | WebFetch with a prompt asking for headline/CTA/offer | The model does this better than any heuristic; we already pay for the LLM call via Claude Code |
| Single-source niche-pulse "is this trending?" detection | Building a second news source (RSS feed reader, Google News scraper) | Serper /news alone, accept reduced theme coverage | The original PULSE-02 Tavily call cost ~12 credits/run for marginal de-duplication value; single-source is the explicit design decision |
| Backward-compat shim that reads both old and new advertiser schemas | Try/except branching on `raw_content` presence | Hard cut — Phase 12 explicitly breaks the old shape; no run folder created before Phase 12 will be re-rendered | Run folders are immutable per `PRST-01`; old runs stay readable from their own archived report.md. Forward compat is unnecessary. |

**Key insight:** Vendor-removal phases are where over-engineering creeps in. Resist the temptation to add a "webfetch_extract.py wrapper helper" or a "schema migration shim." Both are anti-patterns — the design choice is "Claude does this work directly from SKILL.md," not "we add another Python helper for the new vendor."

## Common Pitfalls

### Pitfall 1: Incomplete Tavily grep

**What goes wrong:** A `tavily` string survives in a fixture filename, a comment, a glob pattern, or a docstring. The skill runs fine for 95% of operators, but the 5% hit a `FileNotFoundError` when `merge_signals.py` globs `raw/tavily-*.json` against a Phase 12-built run folder.

**Why it happens:** 11 distinct surfaces × 2 case variants (`tavily` / `TAVILY`) × inconsistent grep coverage. Test suite passes because mocked fixtures hide the gap.

**How to avoid:**
- Make the audit a test: `tests/test_audit_tavily_removed.py` that fails if any source file (excluding `.planning/`, `.git/`, and `uv.lock`) contains the substring `tavily` (case-insensitive). One source of truth.
- Run a final pass: `grep -rni tavily . --exclude-dir=.planning --exclude-dir=.git --exclude=uv.lock` before merge.

**Warning signs:** Test suite green but operator reports cryptic FileNotFound or KeyError on a fresh run.

### Pitfall 2: WebFetch redirect explosion

**What goes wrong:** WebFetch returns "redirect detected" responses for ~30% of advertiser links (consumer brands love affiliate-style tracker URLs). If SKILL.md auto-follows every redirect without a counter, a single advertiser URL can cost 2-3 WebFetch invocations.

**Why it happens:** WebFetch's design (per official docs): "When a URL redirects to a different host, WebFetch returns a text result that names the original URL and the redirect target instead of following it. Claude then fetches the new URL with a second WebFetch call."

**How to avoid:**
- SKILL.md Step 19 explicit rule: "Retry with redirect URL **at most once**, then mark extract_status: failed and move on."
- The 3-5 advertiser cap per cluster + 1-redirect-follow cap bounds the worst case at 10 WebFetch calls per cluster (vs Tavily's 1 SDK call). Still fine for a 5-cluster run.

**Warning signs:** Run time for Phase 5 doubles vs Tavily era; many `extract_status: "failed"` entries in `competitor-landing-pages.json`.

### Pitfall 3: render_report.py reads wrong schema

**What goes wrong:** `render_report.py:242-278` reads `cluster.advertisers[].title/description/domain/url`. After Phase 12, those fields no longer come from Tavily — Serper requery owns `domain/url`, and WebFetch fills `headline/cta/offer`. But the render code expects `title`/`description` which previously fell through `ad_title or title` fallback chain (line 252).

**Why it happens:** Phase 5's `competitor_intel.py` historically wrote Tavily's `raw_content` into `advertisers[].raw_content` (used by Phase 6 Step 19 LLM extraction); `title`/`description` came from re-mapping the Serper ad block. After Phase 12, the rendering code may receive `headline`/`cta`/`offer` (new WebFetch shape) but render `ad_title or title or domain` (legacy fallback chain).

**How to avoid:**
- WFCH-02 schema must be **additive**, not replacing: keep `title`/`description` from Serper ad block in `competitor-intel.json`; layer `headline`/`cta`/`offer` from WebFetch into `competitor-landing-pages.json`; have `render_report.py` JOIN the two files at render time on `(cluster_name, domain)`.
- OR: have SKILL.md Step 19 merge WebFetch results back into `competitor-intel.json` instead of writing a separate file. Trade-off: single file is simpler for render_report.py but mixes "machine-produced" (Serper) and "Claude-produced" (WebFetch) data. **Recommendation: separate file** (WFCH-02 phrasing supports this), JOIN at render time.

**Warning signs:** report.md competitor section renders headlines as `(no headline extracted)` despite `competitor-landing-pages.json` containing data.

### Pitfall 4: Single-source pulse undercounts themes

**What goes wrong:** Before Phase 12, `pulse_synth.find_themes()` clustered n-grams across BOTH `serper-news` and `tavily-news` sources. Tavily/Serper deduplication boosted theme `mention_count` for real signals (same story covered by both). After Phase 12, themes only have one source — `mention_count` drops by ~50%, and the existing `MIN_THEME_MENTIONS_FLOOR = 3` threshold + `len(items) // 25` scaling may push real themes below the cutoff.

**Why it happens:** Threshold was calibrated against dual-source harvests. Single-source harvest produces fewer items → smaller threshold under `// 25` scaling → lower bar, but ALSO fewer mentions per theme. Net effect is uncertain — could be either direction.

**How to avoid:**
- Phase 12 e2e smoke MUST exercise pulse_synth against a real news brief. If trending themes count drops to zero on a known-active vertical (e.g., urgent care / PIP law), tune `MIN_THEME_MENTIONS_FLOOR` down to 2 in pulse_synth.py.
- Track theme counts in the smoke artifacts and flag as Phase 12 follow-up if visibly worse.

**Warning signs:** Niche Pulse section empty in report.md for a brief that had several themes before Phase 12.

### Pitfall 5: Exit-code semantics shift

**What goes wrong:** `competitor_intel.py` today returns exit 2 on Tavily quota exhaustion (per current line 332-336). Operator's SKILL.md Step 18 has explicit `exit 2 → prompt operator to continue with partial data` branching (see `references/phase5-competitor-intel.md` line 27-29). After Phase 12, Tavily quota path is gone — exit 2 has no remaining producer, but the SKILL.md prompt logic still references it.

**Why it happens:** Removal of an error producer without updating downstream error-handling docs.

**How to avoid:**
- Update SKILL.md Step 18 + `references/phase5-competitor-intel.md` Step 18 to reflect: "Exit 2 retains its retryable-Serper meaning; no Tavily quota branch."
- Same applies to `pulse_fetch.py` exit codes (line 31 docstring mentions Tavily quota → drop the mention).

**Warning signs:** Operator reports skill prompts for "Tavily quota" never appear in production but documentation still references them. Cosmetic but signals incomplete docs sweep.

### Pitfall 6: REQUIREMENTS.md history rewrite

**What goes wrong:** PULSE-02 was marked `[x]` Complete on 2026-05-08 (Phase 7 ship). Phase 12 marks it deprecated. Naive approach: flip `[x]` to `[ ]` and add a strikethrough. But the Traceability table at line 226+ has `| PULSE-02 | Phase 7 | Complete |` — that's a historical fact about Phase 7's scope, not a current state claim.

**Why it happens:** Treating retroactive deprecation as identical to "rolling back a feature."

**How to avoid:**
- Leave PULSE-02 row in Traceability table as-is (`Phase 7 | Complete` — historically true).
- In the v1.0 requirements section, change `PULSE-02` line to: `- [x] ~~**PULSE-02**: `pulse_fetch.py` calls Tavily `search` with `topic="news"`...~~ **DEPRECATED in v1.3 Phase 12 — superseded by PULSE-10.**`
- Add a row to Traceability for the deprecation pointer.

**Warning signs:** Future operator reads REQUIREMENTS.md and assumes Tavily news is still live because PULSE-02 is `[x]`.

## Code Examples

### Removing Tavily from competitor_intel.py advertiser loop

```python
# BEFORE (current line 317-360):
if lp_urls:
    try:
        tavily_response = tavily_client.extract(
            urls=lp_urls, extract_depth="basic",
            format="markdown", include_usage=True,
        )
    except (InvalidAPIKeyError, MissingAPIKeyError) as exc:
        log.error(f"Tavily auth failure: {exc}")
        serper_client.close()
        return 3
    except UsageLimitExceededError as exc:
        log.error(f"Tavily quota exceeded: {exc}")
        serper_client.close()
        return 2
    ...
    for result in tavily_response.get("results", []):
        advertisers.append({
            "domain": extract_domain(result.get("url", "")),
            "url": result.get("url", ""),
            "raw_content": result.get("raw_content", ""),
            "tavily_fetched_at": tavily_fetched_at,
            "extract_status": "ok",
        })

# AFTER (Phase 12):
# Advertisers list is derived directly from top_ads (post-dedup, post-filter).
# WebFetch happens at SKILL.md Step 19, not in this script.
advertisers = [
    {
        "domain": extract_domain(ad.get("displayUrl") or ad.get("link", "")),
        "url": ad.get("link", ""),
        "title": ad.get("title"),
        "description": ad.get("snippet", ""),
        "position": ad.get("position"),
    }
    for ad in top_ads
]
```

### Removing tavily-news from pulse_synth.load_news_items()

```python
# BEFORE (current lines 166-188):
def load_news_items(serper_path: Path, tavily_path: Path) -> list[dict]:
    items: list[dict] = []
    if serper_path.exists():
        try:
            data = json.loads(serper_path.read_text(encoding="utf-8"))
            for block in data.get("by_seed", []):
                for item in block.get("items", []):
                    items.append(item)
        except (json.JSONDecodeError, OSError):
            pass
    if tavily_path.exists():
        try:
            data = json.loads(tavily_path.read_text(encoding="utf-8"))
            for block in data.get("by_seed", []):
                for item in block.get("items", []):
                    items.append(item)
        except (json.JSONDecodeError, OSError):
            pass
    return items

# AFTER (Phase 12):
def load_news_items(serper_path: Path) -> list[dict]:
    """Read serper-news.json; return flat list of news items."""
    items: list[dict] = []
    if serper_path.exists():
        try:
            data = json.loads(serper_path.read_text(encoding="utf-8"))
            for block in data.get("by_seed", []):
                for item in block.get("items", []):
                    items.append(item)
        except (json.JSONDecodeError, OSError):
            pass
    return items
```

Signature change: `load_news_items(serper_path, tavily_path)` → `load_news_items(serper_path)`. Test file `test_pulse_synth.py:23-28` (helper `_items_from_fixtures()`) must update to pass only `serper_path`.

### Stripping TAVILY_API_KEY from lib/config.py

```python
# BEFORE (line 19):
REQUIRED_KEYS: tuple[str, ...] = ("SERPER_API_KEY", "TAVILY_API_KEY")

# AFTER:
REQUIRED_KEYS: tuple[str, ...] = ("SERPER_API_KEY",)
```

Note: `REQUIRED_KEYS` is a documentation sentinel — `load_env(require=...)` callers pass their own tuples. After this change, no caller passes `("TAVILY_API_KEY",)` anymore.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tavily SDK for landing-page extraction (Phase 5 COMP-03) | Claude Code WebFetch tool invoked from SKILL.md | Phase 12 (this phase) | -1 paid vendor; -1 API key; -1 Python dep; +0 new code |
| Tavily search(topic="news") + Serper /news dual-source for niche pulse | Serper /news only | Phase 12 (this phase) | ~50% fewer items per harvest; ~12 fewer Tavily credits per Phase 7 run; theme threshold may need re-tune |
| 6-source taxonomy in merge_signals.VALID_SOURCES (incl. tavily-extract) | 5-source taxonomy (serper-organic/paa/related/ads + websearch-baseline) | Phase 12 | Source diversity ceiling drops from 6 to 5; ranking compositeness slightly less granular but functionally identical (single-source vs multi-source signal preserved) |

**Deprecated/outdated:**
- **Tavily SDK** (entire vendor): removed from project. Last used 2026-05-15 before Phase 12.
- **PULSE-02**: deprecated by PULSE-10. Functional behavior subsumed by PULSE-01 (Serper /news already provides what PULSE-02 did, minus dedup-across-sources).
- **`tavily_extract.py` script**: deleted in Phase 12 Plan 12-01.
- **`raw/tavily-<domain>.json` file pattern**: no longer written. Old run folders retain their files immutably (per PRST-01).
- **`raw/tavily-news.json` file**: no longer written. Same immutability rule applies.

## Open Questions

1. **Does WebFetch's 15-minute cache help or hurt repeat runs?**
   - What we know: WebFetch caches per-URL for 15 minutes (per official docs).
   - What's unclear: If operator re-runs Phase 5 on the same run folder within 15 minutes (e.g., during a debug loop), the second invocation hits cache — fast but stale. Probably fine; Phase 5 is rarely re-run within the same brief session.
   - Recommendation: No special handling. Document in Step 19 anti-patterns: "WebFetch caches 15 min — if you need fresh extraction, wait or change the URL."

2. **What happens if an operator's brief has NO competitor URLs and `competitor_intel.py` ad block fallback also fails?**
   - What we know: Today's behavior — competitor-intel.json produced with empty `advertisers` array, Phase 5 Step 19 produces empty competitor-summary, render_report.py renders "_No ads or advertisers captured for this cluster._" (line 277).
   - What's unclear: After Phase 12, the same empty-cluster scenario still works (no new dependency on advertisers). Confirmed safe.
   - Recommendation: E2E smoke should include a brief with no competitor URLs to verify the empty path stays green.

3. **Should `references/phase5-competitor-intel.md` be renamed to drop "LP" from the filename?**
   - What we know: File is `phase5-competitor-intel.md`; SKILL.md line 475 references it by name.
   - What's unclear: Phase 12 changes the LP-extraction technique (Tavily → WebFetch) but not the LP-extraction goal. Filename stays accurate.
   - Recommendation: Keep filename. Update content only. The `references/` directory is operator-facing; filename stability matters.

4. **Does Claude Code's WebFetch permission rule auto-prompt on each new domain?**
   - What we know: Per official docs: "In the default and `acceptEdits` permission modes, WebFetch prompts the first time it reaches a new domain."
   - What's unclear: Phase 5 hits 5-25 unique advertiser domains per run. First-run experience: 5-25 permission prompts. Disruptive.
   - Recommendation: Document in Step 19 anti-patterns and in `references/phase5-competitor-intel.md`: "WebFetch will prompt for permission per new advertiser domain on first run. Operator can pre-allow with `WebFetch(domain:*)` in settings, OR run skill in `bypassPermissions` mode (yolo mode in `.planning/config.json`)." This project IS already in `mode: yolo` (per `.planning/config.json`), but `mode: yolo` in this codebase is gsd-orchestrator-only, not Claude Code permission-mode. **Open question** — need to verify what permission mode the operator typically runs the skill under, and whether that auto-accepts WebFetch domain prompts. **LOW confidence.**

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.3 (declared in `scripts/pyproject.toml` dev group) |
| Config file | `.claude/skills/google-ad-research/scripts/pyproject.toml` (`[tool.pytest.ini_options]` testpaths=`["tests"]`) |
| Quick run command | `uv run --project .claude/skills/google-ad-research/scripts --with pytest --with respx pytest .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py .claude/skills/google-ad-research/scripts/tests/test_pulse_synth.py -x` |
| Full suite command | `uv run --project .claude/skills/google-ad-research/scripts --with pytest --with respx --with python-dotenv --with python-slugify --with tabulate pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| Phase gate | Full suite green + zero `tavily` substring in source tree (excluding `.planning/`, `.git/`, `uv.lock`) before `/gsd:verify-work` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TVLY-01 | `tavily_extract.py` does not exist; `lib/` has no Tavily helper | smoke (filesystem) | `pytest tests/test_audit_tavily_removed.py::test_tavily_extract_deleted -x` | ❌ Wave 0 |
| TVLY-02 | `TAVILY_API_KEY` absent from `.env.example`, `lib/config.py`, README | smoke (grep) | `pytest tests/test_audit_tavily_removed.py::test_tavily_env_keys_stripped -x` | ❌ Wave 0 |
| TVLY-03 | `tavily-python` not in `pyproject.toml` deps; no `tavily-*` fixture filenames; no `tavily-*.json` glob | smoke (parse + filesystem) | `pytest tests/test_audit_tavily_removed.py::test_tavily_deps_and_fixtures_stripped -x` | ❌ Wave 0 |
| TVLY-04 | `test_tavily_extract.py` deleted; `conftest.tavily_fixture` removed | smoke (filesystem + import) | `pytest tests/test_audit_tavily_removed.py::test_tavily_test_artifacts_stripped -x` | ❌ Wave 0 |
| WFCH-01 | SKILL.md Step 19 (in `references/phase5-competitor-intel.md`) references WebFetch, not Tavily | smoke (grep) | `pytest tests/test_audit_tavily_removed.py::test_skill_md_uses_webfetch_for_step19 -x` | ❌ Wave 0 |
| WFCH-02 | `competitor-landing-pages.json` schema documented in SKILL.md + render_report.py can JOIN it on (cluster_name, domain) | integration (synthetic fixture + render dry-run) | `pytest tests/test_render_report.py::test_competitor_section_joins_webfetch_results -x` | ❌ Wave 0 |
| WFCH-03 | `competitor_intel.py` produces advertisers entries with `{domain, url, title, description, position}` — no `raw_content`, no `tavily_fetched_at` | unit | `pytest tests/test_competitor_intel.py::test_advertisers_shape_post_phase12 -x` | ✅ extend existing |
| WFCH-04 | `merge_signals.VALID_SOURCES` does NOT contain `tavily-extract` AND does NOT contain `webfetch-landing` | unit | `pytest tests/test_merge_signals.py::test_valid_sources_post_phase12 -x` | ✅ extend existing |
| PULSE-10 | `pulse_fetch.py` produces only `raw/serper-news.json` (no `raw/tavily-news.json`); no `fetch_tavily_news` symbol exported | unit + smoke | `pytest tests/test_pulse_fetch.py::test_only_serper_news_written -x` | ❌ Wave 0 (test_pulse_fetch.py absent today) |
| PULSE-11 | `pulse_synth.load_news_items()` accepts single `serper_path` arg; produces themes with `sources=["serper-news"]` only | unit | `pytest tests/test_pulse_synth.py::test_load_news_items_serper_only -x` | ✅ extend existing |
| PULSE-12 | `references/phase7-niche-pulse.md` Steps 27-30 contain no Tavily references; REQUIREMENTS.md PULSE-02 marked deprecated | smoke (grep) | `pytest tests/test_audit_tavily_removed.py::test_phase7_docs_tavily_free -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest .claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py tests/test_pulse_synth.py tests/test_audit_tavily_removed.py -x` (~15 sec)
- **Per wave merge:** full suite (~3-5 min, ~252 tests post-Phase-12)
- **Phase gate:** Full suite green + `tests/test_audit_tavily_removed.py` all GREEN + e2e smoke: fresh run on `tests/fixtures/brief_sample.md` produces `report.md` with non-empty competitor section AND `report.md` references no Tavily strings.

### Wave 0 Gaps

- [ ] `tests/test_audit_tavily_removed.py` — repo-wide grep audit + filesystem checks (8 test methods, one per requirement category)
- [ ] `tests/test_pulse_fetch.py` — currently absent from test suite (Phase 7 had no pulse_fetch tests, only pulse_synth); Phase 12 adds it to lock down the single-source contract
- [ ] `tests/test_render_report.py::test_competitor_section_joins_webfetch_results` — new test asserting render_report.py reads both competitor-intel.json + competitor-landing-pages.json and renders headline/cta/offer per advertiser
- [ ] `tests/test_competitor_intel.py::test_advertisers_shape_post_phase12` — new test asserting Tavily-shape fields are absent and Serper-shape fields are present
- [ ] `tests/test_merge_signals.py::test_valid_sources_post_phase12` — new test pinning VALID_SOURCES to the 5-source post-Phase-12 set
- [ ] `tests/test_pulse_synth.py` modifications — existing tests assume dual-source; update signatures and assertions per PULSE-11
- [ ] `tests/conftest.py` modifications — delete `tavily_fixture` (line 53-56)
- [ ] **Wave 0 RED state:** above tests written and FAILING against the Phase 11 codebase. Wave 1 implementation flips them to GREEN.

### E2E Smoke Plan (Wave 3)

Run on real fresh run-folder (not just unit tests):

1. **Setup:** Copy `.env.example` to `.env` with real `SERPER_API_KEY` only (no TAVILY_API_KEY). Confirm `lib/config.load_env(require=("SERPER_API_KEY",))` succeeds and `TAVILY_API_KEY` validation no longer runs.
2. **Brief:** Use `tests/fixtures/brief_sample.md` (UK grocery delivery) or a known-good real brief.
3. **Phases 1-4:** Run as normal — should be unchanged.
4. **Phase 5:** Run `competitor_intel.py --run-dir <run>` — confirm `raw/competitor-intel.json` produced with `advertisers[]` having Serper-shape fields only. Then manually invoke WebFetch per SKILL.md Step 19 instructions for top 3 advertisers in 1 cluster, write `raw/competitor-landing-pages.json` via Write tool.
5. **Phase 6:** Run `render_report.py` — confirm `report.md` competitor section shows headline/CTA/offer from WebFetch results (or "(no headline)" for failures), no `(no headline extracted)` regression.
6. **Phase 7 (optional):** Run `pulse_fetch.py` + `pulse_synth.py` — confirm only `raw/serper-news.json` written, `niche-pulse.json` produced with themes (mention_count may be lower than dual-source era — acceptable).
7. **Final greps:** `grep -rni tavily .` against the entire run folder + source tree (excluding `.planning/`, `.git/`, `uv.lock`) → ZERO matches.

## Sources

### Primary (HIGH confidence)
- **Claude Code Tools reference** — https://code.claude.com/docs/en/tools — WebFetch section verified 2026-05-14. Confirms: WebFetch returns model-extracted content (not raw HTML); 15-min cache; redirect-to-different-host returns text result (Claude must re-fetch); HTTPS upgrade automatic; large pages truncated; HTML→Markdown conversion server-side via small fast model. WebFetch permission rules use `WebFetch(domain:example.com)` form.
- **In-repo file inspection** — `competitor_intel.py`, `tavily_extract.py`, `pulse_fetch.py`, `pulse_synth.py`, `lib/config.py`, `merge_signals.py`, `render_report.py`, `SKILL.md`, `pyproject.toml`, `conftest.py`, `test_tavily_extract.py`, `test_competitor_intel.py`, `test_pulse_synth.py`, `references/phase5-competitor-intel.md`, `references/phase7-niche-pulse.md`, `.env.example` — all read directly; line numbers and code snippets cited from current source.
- **REQUIREMENTS.md + ROADMAP.md + STATE.md** — Phase 12 scope and requirement IDs cross-checked. PULSE-02 deprecation flow documented.

### Secondary (MEDIUM confidence)
- **Phase 7 reference doc** (`references/phase7-niche-pulse.md`) — operator-facing Steps 27-30 confirms current dual-source flow; Phase 12 must drop the Tavily mentions in this file.

### Tertiary (LOW confidence)
- **WebFetch permission-mode prompt behavior in skill context** — official docs describe domain-prompting in default/acceptEdits modes; unclear whether the project's existing `mode: yolo` (in `.planning/config.json`) maps to Claude Code's `bypassPermissions` mode (which auto-allows) or if that is gsd-orchestrator-only. Flagged in Open Questions #4 for operator verification before Phase 12 ships.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — vendor removal only; no new libraries; Claude Code WebFetch verified via official docs
- Architecture: HIGH — WebFetch-from-SKILL.md pattern mirrors existing Step 7 WebSearch baseline (already in production, 4 phases consume it)
- Pitfalls: HIGH on grep audit, schema drift, exit-code shift, REQUIREMENTS.md history; MEDIUM on single-source pulse threshold tuning (empirical — must verify in e2e smoke)
- WebFetch integration: HIGH on official docs behavior; LOW on permission-mode interaction in skill context (Open Question #4)

**Research date:** 2026-05-14
**Valid until:** 2026-06-13 (30 days — stable phase; Claude Code WebFetch behavior may evolve but core contract stable)
