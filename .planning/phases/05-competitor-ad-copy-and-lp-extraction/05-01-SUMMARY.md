---
phase: 05-competitor-ad-copy-and-lp-extraction
plan: "01"
subsystem: api
tags: [serper, tavily, httpx, affiliate-filter, domain-dedup, competitor-intel, python]

# Dependency graph
requires:
  - phase: 05-00-competitor-ad-copy-and-lp-extraction
    provides: "10 RED test stubs, competitor_intel.py MODULE_MISSING stub, 4 fixture JSONs (clusters_phase5, serper_ads_raw, serper_ads_empty, tavily_lp_response)"
provides:
  - "competitor_intel.py: per-cluster Serper requery + affiliate filter + domain dedup + Tavily LP extract"
  - "is_affiliate_url, is_affiliate_domain, dedupe_by_domain, filter_ads — all unit-testable without live APIs"
  - "scripts/pyproject.toml: declares httpx-retries + tavily-python so uv run --with pytest resolves imports"
  - "10 GREEN tests covering COMP-01, COMP-02, COMP-03"
affects: [05-02-plan, phase-6-negatives-report]

# Tech tracking
tech-stack:
  added: [tavily-python>=0.7.24, httpx-retries>=0.5 (pyproject.toml)]
  patterns:
    - "schemeless displayUrl handling — prepend '//' before urlparse to extract netloc correctly"
    - "monkeypatch pattern for TavilyClient constructor: monkeypatch.setattr('competitor_intel.TavilyClient', lambda api_key: mock)"
    - "pyproject.toml in scripts/ as uv project to declare transitive test deps"

key-files:
  created:
    - ".claude/skills/google-ad-research/scripts/competitor_intel.py"
    - ".claude/skills/google-ad-research/scripts/pyproject.toml"
  modified:
    - ".claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py"

key-decisions:
  - "extract_domain prepends '//' to schemeless URLs before urlparse — handles displayUrl values like 'awin1.com/grocery' that have no scheme, making affiliate domain checks reliable"
  - "pyproject.toml added to scripts/ to declare httpx-retries + tavily-python as project deps — enables uv run --with pytest --with respx to resolve imports without extra --with flags"
  - "TavilyClient monkeypatched at module level (not instance) in tests — lambda api_key: mock_obj pattern avoids needing to import and re-construct"
  - "filter_ads returns (clean_ads, filtered_count) tuple — lets caller log raw/filtered counts without re-iterating"

patterns-established:
  - "schemeless URL normalization: if '://' not in url and not url.startswith('//'): url = '//' + url before urlparse"
  - "Tavily failed_results persisted as advertiser entries with extract_status='failed' and raw_content='' — downstream consumers can distinguish ok vs failed without KeyError"

requirements-completed: [COMP-01, COMP-02]

# Metrics
duration: 25min
completed: 2026-05-08
---

# Phase 5 Plan 01: Competitor Intel Summary

**Per-cluster Serper requery + affiliate filter (AFFILIATE_DOMAINS blocklist + param check) + domain dedup + Tavily LP extraction writing competitor-intel.json, with schemeless displayUrl bug fixed**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-08T06:10:00Z
- **Completed:** 2026-05-08T06:35:00Z
- **Tasks:** 2 / 2
- **Files modified:** 3 (competitor_intel.py, test_competitor_intel.py, pyproject.toml new)

## Accomplishments
- competitor_intel.py fully implements COMP-01 (per-cluster Serper requery using highest-scored keyword) and COMP-02 (affiliate URL param + domain blocklist filter + domain dedup + advertiser cap)
- All 10 test stubs replaced with real assertions using monkeypatch for both fetch_seed and TavilyClient — zero live API calls in the test suite
- Fixed schemeless displayUrl bug where `urlparse("awin1.com/grocery").netloc` returns empty string, causing affiliate domain checks to silently pass
- Added scripts/pyproject.toml declaring httpx-retries + tavily-python as project deps so `uv run --with pytest --with respx` resolves transitive imports

## Task Commits

1. **Task 1: Implement competitor_intel.py** — `d1c1624` (feat)
2. **Task 2: Fill test stubs GREEN + pyproject.toml** — `6ee94e4` (test)

## Files Created/Modified
- `.claude/skills/google-ad-research/scripts/competitor_intel.py` — Full Phase 5 orchestrator: PEP 723 header, AFFILIATE_DOMAINS constant, is_affiliate_url / is_affiliate_domain / dedupe_by_domain / filter_ads helpers, main_with_args CLI
- `.claude/skills/google-ad-research/scripts/tests/test_competitor_intel.py` — 10 GREEN tests covering COMP-01 (per-cluster fetch, empty ads), COMP-02 (affiliate URL param, domain blocklist, subdomain, dedup, cap), COMP-03 (Tavily URL list, failed result persistence, output schema)
- `.claude/skills/google-ad-research/scripts/pyproject.toml` — project manifest with httpx-retries>=0.5, tavily-python>=0.7.24, python-slugify>=8.0; [tool.pytest.ini_options] testpaths=["tests"]

## Decisions Made
- `extract_domain` prepends `//` to schemeless URLs before `urlparse` — handles the common Serper `displayUrl` pattern of bare domain+path (e.g. `tesco.com/groceries`) rather than full URL; without this, `netloc` is empty and affiliate domain checks silently pass for known affiliate domains like `awin1.com/grocery`
- `pyproject.toml` added to scripts/ (not project root) — keeps it co-located with the scripts it describes and creates a proper uv project for the test environment; running `uv run --project .claude/.../scripts --with pytest` or `cd scripts && uv run --with pytest` both work
- TavilyClient patched as constructor lambda (`monkeypatch.setattr("competitor_intel.TavilyClient", lambda api_key: mock)`) — matches how the module binds the name at import time

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed extract_domain schemeless URL handling**
- **Found during:** Task 2 (filling test_tavily_urls_built_from_top_ads stub)
- **Issue:** `urlparse("awin1.com/grocery").netloc` returns `""` because urlparse treats the string as a path when no scheme is present. This caused `is_affiliate_domain("awin1.com/grocery")` to return False, meaning the awin1 ad in the serper_ads_raw fixture was NOT being filtered out.
- **Fix:** In `extract_domain`, if the URL has no `://` and doesn't already start with `//`, prepend `//` before calling `urlparse`. This makes `urlparse("//awin1.com/grocery").netloc` correctly return `"awin1.com"`.
- **Files modified:** `.claude/skills/google-ad-research/scripts/competitor_intel.py`
- **Verification:** `test_tavily_urls_built_from_top_ads` passed; full suite 10/10 GREEN
- **Committed in:** `d1c1624` (feat(05-01) commit)

**2. [Rule 3 - Blocking] Added scripts/pyproject.toml for test dependency resolution**
- **Found during:** Task 2 verify (plan's uv run --with pytest --with respx command)
- **Issue:** `uv run --with pytest --with respx pytest` from project root creates an ephemeral env without `httpx-retries` or `tavily-python`. The module-level `import competitor_intel` in the test file caught the resulting `ModuleNotFoundError` (subclass of `ImportError`) and set `MODULE_MISSING=True`, causing all 10 tests to skip instead of run.
- **Fix:** Created `scripts/pyproject.toml` declaring all transitive test deps. Running with `--project .claude/.../scripts` or from the scripts/ directory resolves all imports correctly.
- **Files modified:** `.claude/skills/google-ad-research/scripts/pyproject.toml` (created)
- **Verification:** `uv run --project .claude/skills/google-ad-research/scripts --with pytest --with respx pytest .claude/.../test_competitor_intel.py -v` → 10 passed
- **Committed in:** `6ee94e4` (test(05-01) commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes essential for correctness and test runnability. No scope creep.

## Issues Encountered
- The plan's exact verify command (`uv run --with pytest --with respx pytest .claude/.../test_competitor_intel.py`) does not include `httpx-retries` or `tavily-python` in `--with` flags; adding scripts/pyproject.toml as a uv project is the idiomatic fix per CLAUDE.md conventions (uv run, PEP 723)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- COMP-01 and COMP-02 are satisfied: competitor_intel.py is a complete, tested orchestrator
- COMP-03 (LLM value-prop extraction from raw_content) is the remaining requirement — addressed in Plan 05-02 (SKILL.md Steps 18-20)
- `raw_content` is written verbatim by competitor_intel.py exactly as planned; LLM extraction stays in 05-02

---
*Phase: 05-competitor-ad-copy-and-lp-extraction*
*Completed: 2026-05-08*
