# Project Research Summary

**Project:** Google Ad Research Agent
**Domain:** Claude Code skill — Google Ads keyword research (Python helpers + LLM orchestration)
**Researched:** 2026-05-08
**Confidence:** HIGH

## Executive Summary

Single-operator Claude Code skill that replaces a multi-tab manual PPC keyword research workflow. Operator pastes a campaign brief; skill clarifies missing fields, fans out across three signal sources (WebSearch free baseline, Serper.dev for structured SERP data, Tavily for competitor page content), and produces a single markdown report with four sections: ranked keyword table, ad group clusters, competitor ad copy, negative keyword candidates. Filesystem-only — no server, no UI, no daemon. Skill lives at `.claude/skills/google-ad-research/`.

Recommended approach: Python 3.13+ helper scripts invoked via `uv run` from the Claude Code Bash tool, each with PEP 723 inline dependency metadata. Claude is the orchestrator and LLM engine (intent scoring, clustering, negative generation); scripts handle deterministic I/O (HTTP, JSON normalization, file writes, report assembly). Strict boundary — scripts for what code does well, prompt for what LLM does well — is the canonical Claude Code skill pattern.

Two highest risks: (1) no-volume-data thesis failing to produce trustworthy rankings, mitigated by `source_diversity` (count of distinct signal sources) as primary ranking signal and explicit "not search volume" labeling; (2) LLM intent scoring drifting between runs, mitigated by categorical rubrics (not 0-1 scalars), temperature=0, anchor examples in every scoring prompt. Both detectable quickly with real usage; both have low-cost mitigations.

## Key Findings

### Recommended Stack

Deliberately minimal. `uv` 0.11.x with PEP 723 inline script metadata eliminates venv-activation friction in Claude Code's stateless shell. `httpx` 0.28+ for Serper.dev REST (no official SDK exists). `tavily-python` 0.7.24 official Tavily SDK. `tabulate` 0.9.0 with `tablefmt="github"` for markdown tables. `python-dotenv` 1.0.x for secrets. LLM-driven clustering via skill prompt in v1 — `scikit-learn` TF-IDF/k-means as v2 fallback only if Claude clustering proves inconsistent. `sentence-transformers` explicitly avoided (~700MB torch transitive deps).

**Core technologies:**
- `uv` 0.11.x — script runner + Python manager, PEP 723 inline metadata
- `httpx` 0.28+ — HTTP client for Serper.dev, transitive dep of `tavily-python`
- `tavily-python` 0.7.24 — official Tavily SDK (`search()` and `extract()`)
- `tabulate` 0.9.0 — markdown table rendering with GFM
- `python-dotenv` 1.0.x — `.env` git-ignored, `.env.example` committed
- `pydantic` 2.x — data model validation when >3 fields pass between scripts
- `rich` 13/14.x — `RichHandler` for operator console logs

### Expected Features

**Must have (table stakes):**
- Conversational brief intake with canonical schema (industry, product, location, language, audience, budget, geo exclusions, language exclusions, brand terms, competitor URLs) + pre-API validation gate
- Three-source signal harvest with per-keyword source attribution
- Deduplication + lemmatized canonicalization before scoring
- LLM 4-class intent classification (informational / commercial / transactional / navigational)
- `signal_count` + `source_diversity` composite ranking with explainable score
- Ranked keyword table: keyword, intent, match-type recommendation, theme tag, score, sources
- LLM clustering: intent-homogeneous, 5-15 keywords per group, descriptive names
- Per-cluster competitor ad copy from Serper ads block, deduplicated by advertiser domain
- Tavily LP value-prop extraction for top 3-5 advertisers per cluster
- Categorized negatives (6+ categories) with per-negative justification and tiering
- Markdown report + dated run folder w/ brief.md, report.md, raw/ API dumps
- `report.json` twin for future run diffing (stable canonical keys required from v1)

**Should have (differentiators):**
- Three-source signal triangulation with role separation
- `source_diversity` as primary ranking signal (multi-source echo more reliable than single-source volume proxy)
- Competitor LP value-prop extraction — most tools stop at the ads block
- Brief-aware negative generation (30-50 tiered negatives vs generic 3,000-keyword dumps)
- Per-run cost estimate + confirmation gate before paid API calls fire

**Defer (v2+):**
- Volume/CPC enrichment (DataForSEO / Google Ads API)
- Vertical presets (ecommerce / SaaS / lead-gen / local)
- SERP result caching
- CSV export for Google Ads Editor
- Run-diff / compare script
- Multi-locale fan-out in a single run

### Architecture Approach

`SKILL.md` orchestrates (checklist-driven workflow, brief intake dialogue, all LLM judgment). Python helper scripts are dumb single-purpose CLIs that call one external service, write JSON to the run folder, exit. Scripts communicate only via files in `.runs/<timestamp>-<slug>/` — no IPC, no shared mutable state, no cross-run contamination. WebSearch is a direct Claude tool call (not wrapped in a script).

**Major components:**
1. `SKILL.md` — orchestrator; brief intake, phase checklist, all LLM scoring/clustering/naming
2. `scripts/run_init.py` — creates dated run folder, writes brief.md; stdlib-only
3. `scripts/serp_fetch.py` — Serper.dev REST (organic + PAA + related + ads); writes raw/
4. `scripts/tavily_extract.py` — Tavily extract on curated competitor URL list; per-domain JSON
5. `scripts/render_report.py` — reads synthesis JSONs, produces report.md + report.json
6. `scripts/lib/` — shared: config.py, http.py (httpx + retry), io.py (slugify/JSON), log.py
7. `references/*.md` — progressive-disclosure rubrics (intent, clustering, negatives, report template)
8. `.runs/<ts>-<slug>/` — append-only history; each run isolated; raw/ gitignored after 30 days

### Critical Pitfalls

1. **Thin brief producing plausible-but-wrong output** — enforce field schema; skill loops on missing fields; brief confirmation gate before any paid API call; save brief.md verbatim.
2. **Frequency-of-occurrence misread as search volume** — name column `signal_count`; use `source_diversity` as primary signal; cap any single source at 1 contribution per keyword; "How to read this" disclaimer in every report.
3. **LLM intent scoring drifting between runs** — categorical rubrics (not 0-1 scalars); anchor examples per class in every prompt; temperature=0; log model name + prompt version per run.
4. **Geo/language drift** — `country` and `language` mandatory brief fields; pass `gl`/`hl` to every Serper call; embed locale terms in WebSearch queries; post-run linter catches currency/spelling mismatches.
5. **Intent-mixed clusters** — classify intent before clustering; cluster within intent class only; reject any cluster spanning more than one intent label.
6. **Tavily cost blowup** — `tavily_extract` not `tavily_crawl`; hard cap 5 URLs per competitor, 5 competitors per run, `extract_depth='basic'` default; cost estimate + operator confirmation before run starts.

## Implications for Roadmap

### Phase 1: Skill Scaffold and Brief Intake
**Rationale:** Brief quality drives everything downstream; every pitfall compounds on a weak brief. Scaffold (env contract, folder structure, lib/) must exist before any API call to prevent key leakage and state contamination from day 1.
**Delivers:** Project structure, .env/.env.example, lib/ package, run_init.py, conversational brief intake in SKILL.md producing validated brief.md, cost ceiling check.
**Addresses:** Pitfalls 1, 9, 17, 19, 20.

### Phase 2: Signal Collection
**Rationale:** Three signal sources w/ attribution must be wired before ranking or clustering. Dedup + canonicalization belong here — if variants aren't merged at harvest time, frequency counts are permanently wrong.
**Delivers:** serp_fetch.py (Serper), tavily_extract.py (competitor LP), WebSearch tool call, per-keyword source attribution, lemmatized canonicalization, locale plumbing.
**Addresses:** Pitfalls 4, 6, 7, 8, 21.

### Phase 3: Ranking and Scoring
**Rationale:** Intent classification must run before clustering (intent class is hard clustering split). Ranking schema must be locked now; changing column names later breaks downstream report.json consumers.
**Delivers:** LLM intent classification (4-class, categorical rubric, temperature=0), signal_count + source_diversity composite ranking, match-type recommendation heuristic, "How to read this" section in report template.
**Addresses:** Pitfalls 2, 3, 5 (intent must be assigned before clustering).

### Phase 4: Clustering
**Rationale:** Depends on Phase 3 intent labels. Cluster quality is what makes the report "paste into Google Ads"-ready vs a keyword dump.
**Delivers:** LLM semantic clustering within intent classes, 5-15 keywords/cluster, min size 3, descriptive names, intent-homogeneity enforcement, over/under-clustering guards.
**Addresses:** Pitfalls 5, 10, 11, 12.

### Phase 5: Competitor Ad Copy and LP Extraction
**Rationale:** Depends on clusters (per-cluster Serper requery for scoped ad copy). Most expensive Tavily spend happens here — cost ceiling from Phase 1 must already be in place.
**Delivers:** Per-cluster competitor ad copy from Serper ads block (deduplicated by domain, affiliate-filtered), Tavily LP value-prop extraction for top 3-5 advertisers per cluster.
**Addresses:** Pitfalls 13, 14.

### Phase 6: Negatives, Report Assembly, Quality Gates
**Rationale:** Negatives must run after positive keyword pool is final (to dedup against positives). Report assembly is last step + integration test for all upstream stages.
**Delivers:** Tiered negative keywords (Strong / Considered / Investigate), baseline negatives list, render_report.py producing report.md + report.json, markdown sanitization, locale linter, runs/INDEX.md, error handling polish.
**Addresses:** Pitfalls 15, 16, 18, 22.

### Phase Ordering Rationale

- Scaffold before signals: key leakage and state contamination unrecoverable from day 1
- Signals before scoring: source attribution must be embedded at harvest time
- Scoring before clustering: intent class is hard prerequisite for clustering
- Clustering before ad copy: per-cluster Serper requery requires clusters to exist
- Positives before negatives: negative dedup requires final positive pool
- Report assembly last: render is integration test for all upstream stages

### Research Flags

Standard patterns (no additional research needed):
- Phase 1 (Scaffold): well-documented Claude Code skill conventions
- Phase 2 (Signal Collection): Serper REST and Tavily SDK fully documented
- Phase 6 (Report Assembly): tabulate + template assembly is standard

Needs real-run calibration (not more research, but operator validation):
- Phase 3 (Ranking): source_diversity × intent composite weighting is v1 hypothesis; tune after first 3-5 real runs
- Phase 4 (Clustering): optimal cluster count needs real-run validation
- Phase 5 (Ad Copy): per-cluster Serper requery count needs calibration vs actual ad-block density

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against PyPI, GitHub, Anthropic skill docs |
| Features | HIGH | Four-section report shape, intent classification, STAG clustering, categorized negatives confirmed across multiple 2026 PPC sources |
| Architecture | HIGH | Orchestrator/script pattern verified against Anthropic official skill docs and first-party reference skills |
| Pitfalls | HIGH | 22 pitfalls across 8 categories, well-corroborated by 2026 PPC literature and Anthropic skill best-practice docs |

**Overall confidence:** HIGH

### Gaps to Address

- **Composite ranking weight tuning:** relative weighting of source_diversity vs signal_count vs LLM intent is unvalidated. v1 hypothesis; add operator feedback loop after first 5 real runs.
- **Tavily credit consumption per run:** estimated $0.09-0.30. Measure and log from run 1; adjust caps if needed.
- **Cluster count vs vertical:** narrow verticals may yield fewer clusters than 5-10 general recommendation. Don't force the range.
- **Match-type recommendation conservatism:** v1 defaults conservative. Validate w/ operator after first campaign launch.

## Sources

### Primary (HIGH confidence)
- Anthropic Claude Code skills docs — folder structure, SKILL.md conventions, script invocation
- Anthropic agent skills best practices — orchestrator/tool boundary, progressive disclosure, anti-patterns
- Tavily Python SDK on PyPI/GitHub (v0.7.24) — SDK surface, exception types, credit model
- Serper.dev official site — pricing, endpoints, gl/hl params
- uv on PyPI/GitHub (v0.11.11) — PEP 723 inline script metadata
- Google Ads Help: match types, ad group structure

### Secondary (MEDIUM confidence)
- 2026 PPC practitioner posts (Stackmatix, Store Growers, sitecentre) — STAG clustering, cluster size
- Tavily community forum — search_depth costs, error handling
- pydevtools.com — uv run inside Claude Code's stateless shell
- Search Engine Land, Karooya — negative keyword strategy

### Tertiary (LOW confidence / needs validation)
- Composite ranking weight design — synthesized from intent-classification literature; no industry standard; v1 hypothesis
- Cluster count calibration for narrow verticals — extrapolated from general PPC consensus

---
*Research completed: 2026-05-08*
*Ready for roadmap: yes*
