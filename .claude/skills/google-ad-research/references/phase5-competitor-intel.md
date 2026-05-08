## Phase 5: Competitor Ad Copy and Landing Page Extraction

> Prerequisites: Phase 4 complete — `{run_dir}/clusters.json` exists and validator exited 0.

### Step 18: Run competitor_intel.py (COMP-01, COMP-02)

Derive locale parameters from brief (same as Step 8):
- `gl` = lowercased country code from Location field
- `hl` = language tag from Language field

Run the competitor intel script:
```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/competitor_intel.py" \
  --run-dir "{run_dir}" \
  --gl {gl} \
  --hl {hl}
```

Parse stdout JSON. Surface to operator:
> "Phase 5 signal collection:
> - Clusters processed: {clusters_processed}
> - Serper credits used: {serper_credits_used} (~${serper_credits_used * 0.001:.3f})
> - Tavily credits used: {tavily_credits_used} (~${tavily_credits_used * 0.005:.3f})
> - Competitor intel: `{run_dir}/raw/competitor-intel.json`"

Exit code handling:
- **Exit 0:** continue to Step 19.
- **Exit 2 (Tavily quota):** Warn operator "Tavily quota reached — partial LP data available. Proceed to Step 19 with available data? (y/n)". Continue only if yes.
- **Exit 3:** Surface error from stderr. Do NOT proceed.

**Do not advance to Step 19 until competitor-intel.json exists in `{run_dir}/raw/`.**

### Step 19: Extract headline, CTA, and offer from landing pages (COMP-03)

Read `{run_dir}/raw/competitor-intel.json` using the Read tool.

For each cluster in `competitor-intel.json["clusters"]`:
  For each advertiser in the cluster's `advertisers` list where `extract_status == "ok"` and `raw_content` is non-empty:

    Read the advertiser's `raw_content`. Extract:
    - **headline**: the most prominent heading — the first H1 line (line starting with `# `) or, if absent, the first bold phrase (`**...**`). Truncate to ≤ 10 words. Do NOT invent; if no heading or bold phrase found, use `null`.
    - **cta**: the primary call-to-action — the first imperative verb phrase or button text found (e.g., in a Markdown link like `[Order Now](#order)` extract "Order Now"). If none found, use `null`.
    - **offer**: any discount, free trial, free delivery, or price claim found verbatim in the text (e.g., "Free delivery on orders over £40", "3 months free"). If none, use `null`.

Compile results per cluster into a `competitor_summary` list:

```json
[
  {
    "cluster": "<cluster_name>",
    "representative_keyword": "<keyword>",
    "advertisers": [
      {
        "domain": "<domain>",
        "headline": "<extracted or null>",
        "cta": "<extracted or null>",
        "offer": "<extracted or null>"
      }
    ]
  }
]
```

Skip clusters with no ok-status advertisers (log internally, do not surface).

**Do not advance to Step 20 until you have processed every cluster with ≥ 1 ok advertiser.**

### Step 20: Confirm Phase 5 complete and stop

Tell the operator:

> "Phase 5 complete. Competitor intel summary:
> - {N_clusters_with_ads} clusters had paid ads
> - {N_advertisers_extracted} advertiser landing pages successfully extracted
> - {N_advertisers_failed} advertiser pages failed extraction (JS-heavy or geo-blocked)
>
> Competitor-intel raw data: `{run_dir}/raw/competitor-intel.json`
>
> Phase 6 (report assembly) is not yet available in this skill."

**STOP. Do not proceed to any Phase 6+ activity.**
