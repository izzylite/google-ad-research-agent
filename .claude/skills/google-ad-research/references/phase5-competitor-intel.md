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
> - Competitor intel: `{run_dir}/raw/competitor-intel.json`"

Exit code handling:
- **Exit 0:** continue to Step 19.
- **Exit 2:** retryable Serper HTTP error (rate limit / 5xx). Warn operator "Serper returned a transient error — retry? (y/n)". Re-run once if yes; if it fails again, surface stderr and stop.
- **Exit 3:** fatal (missing input file, bad API key, missing env var). Surface error from stderr. Do NOT proceed.

**Do not advance to Step 19 until competitor-intel.json exists in `{run_dir}/raw/`.**

### Step 19: Extract landing-page value props via WebFetch (COMP-03 + WFCH-01..02)

Read `{run_dir}/raw/competitor-intel.json` using the Read tool. For each cluster, the JSON contains an `advertisers` list whose entries carry `domain`, `url`, `title`, `description`, and `position` (Serper-only shape; no landing-page content yet).

For each cluster in `competitor-intel.json["clusters"]`:
  Pick the top 3-5 advertisers (sorted by `position` ascending; `position` 1 is the most prominent paid result). For each picked advertiser:

  1. Call **WebFetch** with the advertiser's `url` and a structured extraction prompt:

     > "From this landing page, extract three short fields verbatim from the visible content (do NOT invent or summarize):
     > - **headline**: the most prominent on-page heading — the first H1, or the first bold marketing phrase if H1 is generic. Maximum 10 words. `null` if not present.
     > - **cta**: the primary call-to-action button text or imperative verb phrase (e.g., 'Order Now', 'Book a Free Consult', 'Get a Quote'). `null` if not present.
     > - **offer**: any explicit discount, free trial, free delivery, or price claim found verbatim on the page (e.g., 'Free delivery over £40', '3 months free', '20% off first order'). `null` if not present.
     >
     > Return a single JSON object: `{\"headline\": ..., \"cta\": ..., \"offer\": ...}`."

  2. Follow redirects once at most. If the page is geo-blocked, JS-only, or returns an error, record `extract_status = "failed"` with `headline`/`cta`/`offer` set to `null`. Do NOT retry; failed extractions are expected on ~30% of paid landing pages and not a workflow error.

  3. Otherwise record `extract_status = "ok"` plus the extracted three fields.

After processing every picked advertiser across every cluster, aggregate into the following schema and Write it to `{run_dir}/raw/competitor-landing-pages.json` using the Write tool:

```json
{
  "captured_at": "<ISO timestamp>",
  "clusters": {
    "<cluster_name>": {
      "representative_keyword": "<keyword>",
      "advertisers": [
        {
          "domain": "<domain>",
          "url": "<url>",
          "headline": "<extracted verbatim or null>",
          "cta": "<extracted verbatim or null>",
          "offer": "<extracted verbatim or null>",
          "extract_status": "ok|failed"
        }
      ]
    }
  }
}
```

**Rules for extraction (Pitfall mitigations):**

- **Verbatim only.** Headline/CTA/offer must be present on the page text. Do NOT generate marketing copy. WebFetch is extraction, not generation.
- **Single redirect cap.** If the first WebFetch request returns a redirect, follow it once. If the second response also redirects, mark `failed`. Prevents redirect loops on tracking links.
- **Maximum 5 advertisers per cluster.** Skip the rest even if present — diminishing returns.
- **Failures are normal.** JS-heavy pages, age-gates, geo-blocks, and bot-detection all produce `failed` entries. Operator-facing report degrades gracefully via the fallback to Serper ad title + description.
- **Skip clusters with no advertisers.** No-ads clusters get no entry in `clusters` (do not write empty `advertisers` lists).

**Do not advance to Step 20 until `{run_dir}/raw/competitor-landing-pages.json` exists.**

### Step 20: Confirm Phase 5 complete and stop

Tell the operator:

> "Phase 5 complete. Competitor intel summary:
> - {N_clusters_with_ads} clusters had paid ads
> - {N_advertisers_extracted} advertiser landing pages successfully extracted via WebFetch
> - {N_advertisers_failed} advertiser pages failed extraction (JS-heavy, geo-blocked, or bot-protected)
>
> Competitor-intel raw data: `{run_dir}/raw/competitor-intel.json`
> Landing-page extracts: `{run_dir}/raw/competitor-landing-pages.json`
>
> Phase 6 (report assembly) begins at Step 21. Load `.claude/skills/google-ad-research/references/phase6-negatives-report.md` with the Read tool when entering Phase 6."
