# Phase 5: Competitor Ad Copy and LP Extraction — Research

**Researched:** 2026-05-08
**Domain:** Python orchestration script, Serper ads-block re-query, Tavily LP extraction, affiliate domain filtering
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | Per-cluster Serper requery extracts paid ad headlines + descriptions from ads block | `serp_fetch.py` `fetch_seed()` + `normalise_response()` are directly reusable; `ads` array is already normalised |
| COMP-02 | Ad copy deduplicated by advertiser domain; affiliate/aggregator domains filtered | New `filter_ads()` helper with regex URL param check + known-domain blocklist |
| COMP-03 | Tavily extracts landing-page value props (headline, primary CTA, offer) for top 3-5 advertisers per cluster | `tavily_extract.py` pattern reused; LLM does value-prop extraction from `raw_content` in skill prompt Step 18 |
</phase_requirements>

---

## Summary

Phase 5 is a thin orchestration layer on top of already-working infrastructure. The two hard problems — Serper REST calls and Tavily extract — are solved by `serp_fetch.py` and `tavily_extract.py` respectively. What Phase 5 adds is: per-cluster invocation (driving Serper once per cluster using the cluster's top-scored keyword), affiliate domain filtering, domain deduplication of the ads block, and Tavily LP extraction of the surviving top 3-5 advertiser URLs.

The primary deliverable is a new script `competitor_intel.py` that reads `clusters.json`, loops over clusters, calls Serper (reusing the `fetch_seed` + `normalise_response` logic verbatim or by import), filters/dedupes the ads block, picks top advertiser URLs, calls Tavily extract on those URLs, and writes `raw/competitor-intel.json` per cluster. The LLM in SKILL.md Step 18 reads the raw Tavily `raw_content` from each advertiser result and extracts headline, primary CTA, and offer language.

**Primary recommendation:** Single script `competitor_intel.py` with two internal phases (ads fetch → LP extract). Write `raw/competitor-intel.json` as the canonical output. LLM extraction of value props stays in the skill prompt.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.28 | Serper REST call (reuse pattern from serp_fetch.py) | Already a project dependency; RetryTransport in lib/http.py |
| tavily-python | >=0.7.24 | Tavily extract for LP content | Already a project dependency; extract() API established |
| python-dotenv | >=1.0 | Load SERPER_API_KEY + TAVILY_API_KEY | Project standard; lib/config.load_env() wrapper exists |
| python-slugify | >=8.0 | Sanitise domain name for output keys | Already in tavily_extract.py dependencies |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| urllib.parse | stdlib | Parse display URLs to extract domain, detect affiliate params | Use for `?ref=`, `aff_id` param detection; stdlib — no extra dep |
| re | stdlib | Regex pattern for affiliate URL parameter detection | Use for `aff_id`, `partner_id`, `affiliate_id` patterns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single `competitor_intel.py` | `cluster_ads_fetch.py` + `cluster_lp_extract.py` | Two scripts is cleaner separation but adds SKILL.md orchestration complexity; single script with `--phase ads\|lp\|all` subcommand is simpler given clusters.json must be read for both halves |
| Importing serp_fetch internals | Copying fetch_seed() inline | Import is cleaner; but `uv run` path isolation means `sys.path.insert` pattern from existing scripts applies |

**Installation:** No new packages required — all dependencies already present in serp_fetch.py and tavily_extract.py.

---

## Architecture Patterns

### Recommended Project Structure
```
scripts/
├── competitor_intel.py   # NEW — Phase 5 orchestrator
├── serp_fetch.py         # Phase 2 — reuse fetch_seed() / normalise_response()
├── tavily_extract.py     # Phase 2 — reuse client.extract() pattern
└── lib/
    ├── config.py
    ├── http.py
    ├── io.py
    └── log.py

.runs/<ts>-<slug>/
├── clusters.json          # Phase 4 input
└── raw/
    ├── competitor-intel.json   # Phase 5 output (written by competitor_intel.py)
    └── tavily-<domain>.json    # Phase 2 Tavily outputs (already present)
```

### Pattern 1: Per-cluster Serper re-query

**What:** For each cluster, pick the single highest-scored keyword as the representative query. Call Serper `/search` with that query. Extract only the `ads` block. Filter and dedupe.

**When to use:** Always for Phase 5. Fresher than re-using Phase 2 `raw/serper.json` — separate per-cluster queries target the paid ad auction for that specific intent space.

**Representative keyword selection:**
```python
# From clusters.json, each cluster has keywords sorted by score descending
# Pick index 0 — highest score = most signal-rich keyword for that cluster
representative = cluster["keywords"][0]["keyword"]
```

**Why fresh requery, not reuse of Phase 2 serper.json:**
- Phase 2 seeds are generic brand+product phrases. Per-cluster queries are intent-scoped.
- Pitfall 14: log freshness timestamp per Serper call; treat results > 30 min old as stale.
- Per-cluster ads block reflects the actual auction for that keyword's intent class.

### Pattern 2: Affiliate/aggregator filter

**What:** After extracting the ads block for a cluster, remove any ad whose `displayUrl` or `link` matches an affiliate signal.

**Filter logic (applied in this order):**

1. **URL parameter check** — parse the ad's `link` field with `urllib.parse.urlparse` / `urllib.parse.parse_qs`:
   - Drop if any query param key matches: `ref`, `aff_id`, `affiliate_id`, `partner_id`, `affid`, `aff_sub`
   - Drop if URL contains literal substrings: `?ref=`, `&ref=`, `/aff/`, `/affiliate/`

2. **Known affiliate domain blocklist** — extract eTLD+1 from `displayUrl`:
   ```python
   AFFILIATE_DOMAINS = frozenset({
       "awin.com", "awin1.com",
       "skimlinks.com",
       "partnerize.com",
       "viglink.com",
       "sovrn.com",
       "rakuten.com", "rakutenadvertising.com",
       "tradedoubler.com",
       "cj.com",           # Commission Junction
       "shareasale.com",
       "impactradius.com", "impact.com",
       "pepperjam.com",
       "webgains.com",
       "zanox.com",
       "affiliatefuture.com",
       "vouchercloud.com", "vouchercodes.co.uk",
       "myvouchercodes.co.uk", "hotukdeals.com",
       "topcashback.co.uk", "quidco.com",
       "cashbackkings.com",
   })
   ```
   Match on eTLD+1 (strip `www.` prefix before comparing). Subdomains of listed domains are also blocked.

3. **Log filtered count** per cluster to stderr (Pitfall 14 mitigation):
   ```
   cluster=same_day_delivery_transactional: 6 ads raw, 2 filtered (affiliate), 4 remaining
   ```

### Pattern 3: Domain deduplication

**What:** After affiliate filtering, keep at most one ad per advertiser display-URL domain. The highest-position ad for a domain wins (position 1 beats position 3).

```python
def dedupe_by_domain(ads: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for ad in sorted(ads, key=lambda a: a.get("position") or 99):
        domain = extract_domain(ad.get("displayUrl", ad.get("link", "")))
        if domain and domain not in seen:
            seen[domain] = ad
    return list(seen.values())
```

### Pattern 4: Top advertiser URL selection

**What:** After dedupe, take the top 3-5 advertisers by Serper position. Extract one LP URL per advertiser from the `link` field (the actual landing page Serper recorded, not the display URL root).

**Cap:** Hard cap at 5 advertisers per cluster (matches existing Tavily extract caps from Phase 2).

### Pattern 5: Tavily LP extraction

**What:** Reuse the `TavilyClient.extract()` pattern from `tavily_extract.py`. Pass the LP URLs directly. Store the `raw_content` per URL — do NOT do LLM value-prop extraction in Python.

**LLM extraction stays in SKILL.md** (Step 18): the skill prompt reads `raw_content` from `competitor-intel.json` and extracts `headline`, `cta`, `offer` for each advertiser. This is consistent with the project's orchestrator/script boundary: scripts do deterministic I/O, LLM does interpretation.

### Output Schema

`{run_dir}/raw/competitor-intel.json`:
```json
{
  "metadata": {
    "generated_at": "<ISO timestamp>",
    "clusters_input": "clusters.json",
    "serper_credits_used": 10,
    "tavily_credits_used": 6
  },
  "clusters": {
    "same_day_delivery_transactional": {
      "representative_keyword": "order same day grocery delivery",
      "serper_fetched_at": "<ISO timestamp>",
      "ads_raw_count": 6,
      "ads_filtered_count": 2,
      "ads": [
        {
          "title": "Same Day Grocery Delivery — Order Now",
          "description": "Fresh groceries at your door in 2 hours.",
          "domain": "ocado.com",
          "displayed_url": "ocado.com/same-day",
          "link": "https://www.ocado.com/landing/same-day",
          "position": 1
        }
      ],
      "advertisers": [
        {
          "domain": "ocado.com",
          "url": "https://www.ocado.com/landing/same-day",
          "raw_content": "<Tavily extracted markdown content>",
          "tavily_fetched_at": "<ISO timestamp>",
          "extract_status": "ok"
        }
      ]
    }
  }
}
```

**Note:** `headline`, `cta`, `offer` fields are NOT written by the script. The SKILL.md LLM step adds them when assembling the report.

### Anti-Patterns to Avoid

- **Re-using Phase 2 serper.json ads block:** That block was fetched for seed keywords, not per-cluster representative queries. It will miss advertisers competing in specific intent niches.
- **Calling `tavily_crawl` instead of `tavily_extract`:** Violates Pitfall 8 cap discipline. Always `client.extract()`.
- **LLM extraction inside the Python script:** Breaks the orchestrator/script boundary. Scripts are dumb I/O; LLM runs in the skill prompt.
- **Skipping domain deduplication before Tavily:** A single advertiser (e.g., tesco.com) could appear in 3 cluster ad blocks; without dedupe you'd Tavily-extract their LP 3 times per run, wasting credits.
- **Using `link` (the final landing page URL) for domain display, not dedup key:** Use `displayUrl` for the domain dedup key (what the user sees); use `link` as the Tavily extract URL.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry on Serper | Custom retry loop | `lib/http.build_client()` with RetryTransport | Already wired; handles 429 + 5xx with backoff |
| Tavily extract | Raw httpx POST to Tavily API | `TavilyClient.extract()` | SDK handles auth, error types, `include_usage` — already in tavily_extract.py |
| Domain extraction from URL | Custom regex | `urllib.parse.urlparse().netloc` + strip `www.` | Handles edge cases (ports, auth fragments); stdlib |
| eTLD+1 matching | Split-on-dot heuristics | Direct domain string comparison after `www.` strip | For a known blocklist of 20 domains, exact match is sufficient; `tldextract` is a heavy dep for no gain in v1 |

---

## Common Pitfalls

### Pitfall 13 (from PITFALLS.md): Affiliate/aggregator ads captured as competitor copy
**What goes wrong:** Voucher sites, cashback aggregators, and affiliate networks bid on brand + product terms. Their ads appear in the Serper ads block but aren't the direct competitors the report should analyse.
**Why it happens:** Google Ads auctions are open; anyone can bid on "tesco grocery delivery".
**How to avoid:** Apply the two-stage affiliate filter (URL params + domain blocklist) before dedupe. Log filtered count per cluster.
**Warning signs:** "Competitor" ad copy mentions discount codes, cashback, or "compare X sites". Display URL doesn't match any known brand.

### Pitfall 14 (from PITFALLS.md): Stale/cached ad block results
**What goes wrong:** Serper caches results 15-60 min. A cached ads block may not reflect the current auction.
**Why it happens:** SERP APIs trade freshness for cost. Single-keyword scrape is a sample of one.
**How to avoid:**
- Log `fetched_at` ISO timestamp per cluster Serper call (already in output schema above).
- Use a **fresh requery per cluster** rather than re-using Phase 2 serper.json (which may be hours old by Phase 5).
- Note in report: "Ads observed on {date}, {locale}/{device}; live auctions vary."
**Warning signs:** Same ad text repeats verbatim across multiple unrelated clusters. `ads_raw_count` = 0 for several clusters (likely cached from low-commercial intent).

### Pitfall: Empty ads block for some clusters
**What goes wrong:** Serper returns `ads: []` for informational-intent representative keywords — those queries don't trigger paid ads.
**How to avoid:** Handle gracefully — `competitor_intel.py` writes `"ads": [], "advertisers": []` for that cluster and logs a warning. Do not exit 3; proceed with other clusters. Informational clusters have no competitor ad copy by design.

### Pitfall: `displayUrl` malformed or absent
**What goes wrong:** Some Serper ad entries have `displayUrl: null` or a relative path. Domain extraction fails silently and the ad slips past deduplication.
**How to avoid:** Fall back to `urllib.parse.urlparse(link).netloc` when `displayUrl` is absent or fails to yield a parseable domain. Always normalise to lowercase and strip `www.` before inserting into the `seen` dict.

### Pitfall: Tavily extract fails for all LP URLs in a cluster
**What goes wrong:** All 3-5 advertiser landing pages return `failed_results` (JS-heavy SPAs, geo-blocked, rate-limited). The cluster's `advertisers` array is empty.
**How to avoid:** Write `extract_status: "failed"` per advertiser; continue to next cluster. SKILL.md step reads `extract_status` and skips value-prop extraction for failed entries. Do not exit 2/3 for individual URL failures — only exit 2 for Tavily quota exhaustion.

---

## Code Examples

### Serper ads-block fetch (reuse pattern from serp_fetch.py)
```python
# Source: existing serp_fetch.py fetch_seed() — call verbatim
# In competitor_intel.py, import or copy fetch_seed + normalise_response
from serp_fetch import fetch_seed, normalise_response  # sys.path.insert pattern

raw = fetch_seed(client, representative_kw, gl=gl, hl=hl, num=10, api_key=api_key)
normalised = normalise_response(raw, seed=representative_kw, gl=gl, hl=hl)
ads = normalised["ads"]  # already normalised: title, link, snippet, displayUrl, position
```

### Affiliate URL param detection
```python
import urllib.parse

AFFILIATE_PARAMS = frozenset({"ref", "aff_id", "affiliate_id", "partner_id", "affid", "aff_sub"})
AFFILIATE_PATH_FRAGMENTS = ("/aff/", "/affiliate/", "/out/", "/track/")

def is_affiliate_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    params = set(urllib.parse.parse_qs(parsed.query).keys())
    if params & AFFILIATE_PARAMS:
        return True
    path_lower = parsed.path.lower()
    return any(frag in path_lower for frag in AFFILIATE_PATH_FRAGMENTS)
```

### Domain extraction + blocklist check
```python
def extract_domain(url: str) -> str:
    """Return lowercase eTLD+1-ish domain, stripping www."""
    netloc = urllib.parse.urlparse(url).netloc.lower()
    return netloc.removeprefix("www.")

def is_affiliate_domain(url: str) -> bool:
    domain = extract_domain(url)
    # exact match OR subdomain match
    return domain in AFFILIATE_DOMAINS or any(
        domain.endswith("." + d) for d in AFFILIATE_DOMAINS
    )
```

### Cluster loop skeleton
```python
# competitor_intel.py main loop
clusters_data = json.loads((run_dir / "clusters.json").read_text(encoding="utf-8"))
output = {"metadata": {...}, "clusters": {}}

for cluster in clusters_data["clusters"]:
    name = cluster["name"]
    rep_kw = cluster["keywords"][0]["keyword"]  # highest-scored

    # 1. Serper ads fetch
    raw = fetch_seed(client, rep_kw, gl=gl, hl=hl, num=10, api_key=serper_key)
    ads_raw = normalise_response(raw, seed=rep_kw, gl=gl, hl=hl)["ads"]
    fetched_at = datetime.utcnow().isoformat() + "Z"

    # 2. Affiliate filter
    ads_clean = [a for a in ads_raw if not is_affiliate(a)]
    filtered_count = len(ads_raw) - len(ads_clean)
    log.info(f"{name}: {len(ads_raw)} ads, {filtered_count} filtered, {len(ads_clean)} remaining")

    # 3. Domain dedupe
    ads_deduped = dedupe_by_domain(ads_clean)

    # 4. Top N advertisers
    top_ads = ads_deduped[:MAX_ADVERTISERS]  # MAX_ADVERTISERS = 5

    # 5. Tavily LP extract
    lp_urls = [a["link"] for a in top_ads if a.get("link")]
    advertisers = []
    if lp_urls:
        response = tavily_client.extract(urls=lp_urls, extract_depth="basic",
                                         format="markdown", include_usage=True)
        for result in response.get("results", []):
            advertisers.append({
                "domain": extract_domain(result["url"]),
                "url": result["url"],
                "raw_content": result.get("raw_content", ""),
                "tavily_fetched_at": fetched_at,
                "extract_status": "ok",
            })
        for failed in response.get("failed_results", []):
            advertisers.append({
                "domain": extract_domain(failed.get("url", "")),
                "url": failed.get("url", ""),
                "raw_content": "",
                "extract_status": "failed",
            })

    output["clusters"][name] = {
        "representative_keyword": rep_kw,
        "serper_fetched_at": fetched_at,
        "ads_raw_count": len(ads_raw),
        "ads_filtered_count": filtered_count,
        "ads": [{"title": a["title"], "description": a.get("snippet",""),
                 "domain": extract_domain(a.get("displayUrl", a.get("link",""))),
                 "displayed_url": a.get("displayUrl",""),
                 "link": a.get("link",""), "position": a.get("position")}
                for a in ads_deduped],
        "advertisers": advertisers,
    }
```

### SKILL.md Step 18 value-prop extraction prompt pattern
```
For each cluster in competitor-intel.json where advertisers is non-empty:
  For each advertiser where extract_status == "ok":
    Read raw_content. Extract:
      - headline: the most prominent headline (first H1 or first bold phrase, ≤ 10 words)
      - cta: the primary call-to-action button text or imperative phrase
      - offer: any discount, free trial, delivery offer, or price claim (null if none)
    Write as {"domain": ..., "headline": ..., "cta": ..., "offer": ...}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Re-use Phase 2 serper.json ads block | Fresh per-cluster requery | Phase 5 design | Ads are scoped to cluster intent; fresher; more representative |
| Single keyword per run for competitor research | One representative keyword per cluster | Phase 5 design | 10 clusters = 10 Serper calls; captures intent-specific advertisers |

---

## API Cost Model

| Operation | Cost | Per Run (10 clusters) |
|-----------|------|-----------------------|
| Serper `/search` | 1 credit per call | 10 credits |
| Tavily `extract` basic | 1 credit per 5 URLs | ~6-10 credits (3-5 URLs × 10 clusters / 5) |
| **Total per run** | | **~16-20 API credits** |

Serper: $0.001/credit ≈ $0.01 per run. Tavily basic: ~$0.005-0.01/credit ≈ $0.06-0.10 per run.
**Estimated total Phase 5 cost per run: ~$0.07-0.11.**

This is within the existing Pitfall 8 guard framework. Document in SKILL.md Step 18 summary message to operator.

---

## Open Questions

1. **Serper `num` parameter for competitor_intel.py**
   - What we know: serp_fetch.py uses `num=20` for signal breadth
   - What's unclear: For ads-only queries, `num=10` is sufficient (ads block doesn't scale with num) and halves response size
   - Recommendation: Use `num=10` in competitor_intel.py; the ads block is independent of the organic results count

2. **Multi-keyword union per cluster (Pitfall 14 mitigation)**
   - What we know: Pitfall 14 says to query 3-5 representative keywords per cluster and union the ads
   - What's unclear: This triples Serper credit usage (30 calls for 10 clusters vs 10)
   - Recommendation: v1 uses 1 representative keyword per cluster (cost-controlled); add `--union-top N` flag as v2 option when stale-ad complaints arise from real runs

3. **`displayUrl` vs `link` for Tavily extract**
   - What we know: `displayUrl` is the pretty domain shown in the ad (e.g., `ocado.com/same-day`); `link` is the full landing page URL with UTM params
   - What's unclear: Some `link` values go through redirect chains that Tavily may not follow
   - Recommendation: Use `link` directly for Tavily extract; Tavily follows redirects. If `extract_status: failed` for a `link`, fallback to `https://{extract_domain(displayUrl)}` as secondary attempt (not implemented in v1 — log and skip)

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed — project uses pytest throughout phases 1-4) |
| Config file | None detected — tests discovered by convention |
| Quick run command | `uv run pytest tests/test_competitor_intel.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01 | Serper requery returns ads block per cluster | unit | `pytest tests/test_competitor_intel.py::test_ads_fetched_per_cluster -x` | Wave 0 |
| COMP-01 | Informational cluster with 0 ads handled gracefully (no exit 3) | unit | `pytest tests/test_competitor_intel.py::test_empty_ads_block_ok -x` | Wave 0 |
| COMP-02 | Affiliate URL param filter drops `?ref=` and `aff_id=` URLs | unit | `pytest tests/test_competitor_intel.py::test_affiliate_url_param_filter -x` | Wave 0 |
| COMP-02 | Known affiliate domain (awin.com, skimlinks.com) dropped by blocklist | unit | `pytest tests/test_competitor_intel.py::test_affiliate_domain_blocklist -x` | Wave 0 |
| COMP-02 | Subdomain of affiliate domain (sub.awin.com) also dropped | unit | `pytest tests/test_competitor_intel.py::test_affiliate_subdomain_blocked -x` | Wave 0 |
| COMP-02 | Domain dedup: two ads same domain → one ad retained (highest position wins) | unit | `pytest tests/test_competitor_intel.py::test_dedupe_by_domain -x` | Wave 0 |
| COMP-02 | Cap enforcement: > 5 clean ads → top 5 only in output | unit | `pytest tests/test_competitor_intel.py::test_advertiser_cap_enforcement -x` | Wave 0 |
| COMP-03 | Top 3-5 advertiser URLs passed to Tavily extract | unit | `pytest tests/test_competitor_intel.py::test_tavily_urls_built_from_top_ads -x` | Wave 0 |
| COMP-03 | Failed Tavily result written as extract_status=failed, not dropped | unit | `pytest tests/test_competitor_intel.py::test_tavily_failed_result_persisted -x` | Wave 0 |
| COMP-03 | Output schema: ads + advertisers present per cluster in competitor-intel.json | integration | `pytest tests/test_competitor_intel.py::test_output_schema_valid -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_competitor_intel.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Test Fixtures Required (Wave 0 Gaps)

| File | Purpose |
|------|---------|
| `tests/fixtures/clusters_phase5.json` | 3-cluster clusters.json (1 transactional with ads, 1 commercial with ads, 1 informational with empty ads) |
| `tests/fixtures/serper_ads_raw.json` | Serper response with 6 ads: 2 affiliate (one URL-param, one domain), 4 real advertisers, 2 same domain |
| `tests/fixtures/serper_ads_empty.json` | Serper response with `ads: []` |
| `tests/fixtures/tavily_lp_response.json` | Tavily extract response with 3 ok results + 1 failed_result |
| `tests/test_competitor_intel.py` | 10 test functions (all RED stubs) covering COMP-01, COMP-02, COMP-03 |

### Wave 0 Gaps
- [ ] `tests/fixtures/clusters_phase5.json` — 3-cluster input fixture
- [ ] `tests/fixtures/serper_ads_raw.json` — ads block with affiliate + duplicate + clean ads
- [ ] `tests/fixtures/serper_ads_empty.json` — empty ads block
- [ ] `tests/fixtures/tavily_lp_response.json` — LP extract response with failures
- [ ] `tests/test_competitor_intel.py` — 10 RED stubs covering COMP-01, COMP-02, COMP-03
- [ ] `scripts/competitor_intel.py` — script stub (MODULE_MISSING guard consistent with Phases 2-4)

---

## Sources

### Primary (HIGH confidence)
- `scripts/serp_fetch.py` (project source) — `fetch_seed()`, `normalise_response()`, `ads` block shape, exit codes, `build_client()` usage
- `scripts/tavily_extract.py` (project source) — `TavilyClient.extract()` pattern, error handling, output shape, credit calculation
- `scripts/merge_signals.py` (project source) — `keywords.json` output schema, `source_diversity` field names, source taxonomy
- `.planning/research/PITFALLS.md` Pitfall 13 and 14 — affiliate filter requirements, freshness logging requirements
- `.planning/STATE.md` Accumulated Decisions — `tavily_extract` not `crawl`, extract_depth=basic, hard cap 5 competitors × 5 URLs, run-folder isolation patterns

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` — Phase 5 architecture rationale, cost estimate ($0.09-0.30 Tavily per run)
- `.planning/REQUIREMENTS.md` COMP-01/02/03 — exact success criteria definitions
- `.planning/ROADMAP.md` Phase 5 section — goal statement and dependency ordering

### Tertiary (LOW confidence)
- Affiliate network domain list — synthesised from common affiliate networks known to operate in UK ecommerce; validate against actual Serper ads block output in first real run

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all reuse established project patterns
- Architecture: HIGH — single orchestrator script pattern matches phases 2-4; file I/O contract clear
- Affiliate filter: MEDIUM — URL param list is comprehensive for common networks; domain blocklist covers major UK/EU affiliates but first real run may surface additional domains
- Output schema: HIGH — matches focus brief exactly; consistent with merge_signals.py row shape conventions
- Pitfalls: HIGH — directly sourced from PITFALLS.md 13 and 14

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (Serper and Tavily APIs are stable; affiliate network list may drift)
