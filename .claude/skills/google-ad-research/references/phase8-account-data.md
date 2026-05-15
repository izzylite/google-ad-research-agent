# Phase 8 — Account Data + Volume Enrichment

Live Google Ads account data (campaigns, search terms, existing negatives)
plus Ahrefs volume / CPC / Keyword Difficulty enrichment. Sidecar phase —
runs alongside main pipeline when credentials available.

## When to run

After Phase 6 (report assembly) produces `ranked.json` + `negatives.json`.

Phase 8 is **optional but high-value**:
- Adds volume + CPC + KD to keyword table (the #1 missing feature pre-Phase-8)
- Surfaces real search terms from active account (proves which queries convert)
- Cross-references our negatives against existing account negatives (no duplicate work)
- Shows account performance snapshot (top campaigns by ROAS/CPA)

## Prerequisites

`.env` at repo root must contain:

```
AHREFS_API_KEY=...
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=...
GOOGLE_ADS_CUSTOMER_ID=...
```

If any missing, the relevant sub-step skips silently.

## Step 31: Confirm operator wants Phase 8

Ask:

> "Run Phase 8 (account data + volume enrichment)? Pulls Ahrefs volumes for
> all keywords (~$0.05 in Ahrefs credits) and Google Ads campaign data
> (free, quota-based). Adds real performance metrics to the report."

If no → stop. If yes → continue.

## Step 32: Volume + CPC enrichment via Ahrefs

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/volume_enrich.py" \
  --run-dir "{run_dir}" \
  [--country us]
```

Country auto-detected from `brief.md` if omitted.

Parse stdout JSON. Surface `keywords_enriched` and `keywords_no_data` to
operator. ~60% enrichment rate is normal (long-tail keywords often have no
measurable volume).

Exit codes:
- 0 → continue
- 2 → Ahrefs transient error; offer retry
- 3 → auth/IO fatal; stop

Produces:
- `{run_dir}/ranked-enriched.json` (ranked.json + volume/cpc/kd/parent_topic)
- `{run_dir}/raw/ahrefs-overview.json`

## Step 33: Google Ads account data fetch

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/perf_fetch.py" \
  --run-dir "{run_dir}" \
  [--customer-id 4580213643] \
  [--login-customer-id 4580213643] \
  [--days 30]
```

Defaults pulled from `GOOGLE_ADS_CUSTOMER_ID` env var.

For direct (non-MCC) access, set `--login-customer-id = --customer-id`
(default behaviour). If account is parented by an MCC the operator
controls, pass the MCC ID as `--login-customer-id`.

Parse stdout JSON. Surface counts (search terms, campaigns, ad groups,
existing negatives).

Produces three `raw/google-ads-*.json` files.

Exit codes:
- 0 → continue
- 2 → API transient; offer retry
- 3 → auth/perm fatal; surface error from stderr

## Step 34: Synthesize performance + negative cross-reference

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/perf_synth.py" --run-dir "{run_dir}"
```

Produces:
- `{run_dir}/account-perf.json` — top campaigns/ad groups, converted search
  terms, lossy search terms, blended CPA/ROAS
- `{run_dir}/negatives-sync.json` — our negatives flagged
  `already_in_account` vs `new_candidate`, bucketed by tier

Surface to operator:
- Account totals (spend, conv, ROAS)
- `new_to_add` count broken down by tier
- Count of lossy search terms (review them as additional negative
  candidates)

## Step 34a: LLM re-tag for positives-sync (POS-06)

**Trigger condition:** Runs ONLY when `{run_dir}/positives-sync.json` exists AND
Phase 14 is enabled (i.e., `perf_synth.py` produced the file in Step 34).
Skips silently otherwise — graceful no-op when Phase 14 was bypassed (no
Google Ads OAuth, or `raw/google-ads-keywords.json` absent).

**What Claude does:** Read `{run_dir}/positives-sync.json` plus
`{run_dir}/ranked-enriched.json` (fallback `ranked.json`) and — if present —
`{run_dir}/competitor-intel.json`. Re-classify borderline cases the
script-only `cross_ref_positives` cross-reference missed (token reorder,
match-type drift, semantic synonyms) using the 5 anchor examples below.
Write the refined buckets back to `{run_dir}/positives-sync.json` with the
Write tool, overwriting the script-only output.

The script catches the ~80% of cases plain string-norm dedup handles
correctly. This LLM step catches the remaining ~20% — the operator-visible
failure mode if skipped.

**Borderline cases LLM must catch (anchor examples):**

1. **Token reorder** — `urgent care lake worth` (ranked) vs `lake worth urgent care` (active) → re-tag to `already_active`.
2. **Match-type drift** — ranked exact `pip insurance clinic` vs account broad `pip clinic` → re-tag to `covered_by_broad`.
3. **Semantic synonym** — ranked `open 24 hours` vs account `24 hour clinic` (both transactional) → re-tag to `already_active`.
4. **Narrowing opportunity** — ranked exact `car accident chiropractor` vs account broad `car accident` → re-tag to `covered_by_broad` AND flag in justification: "Exact narrows targeting — operator review".
5. **Locale variant** — ranked Spanish `clinica de accidente` vs account English `accident clinic` → STAY `new_to_add` (locale gap is a legitimate net-new opportunity).

**LLM output contract (Write tool to {run_dir}/positives-sync.json):**

- Preserve all top-level keys from the input file (`synthesized_at`, `our_total`, `existing_total`, `stats`).
- Only re-distribute entries BETWEEN the 4 existing bucket arrays: `already_active`, `paused_in_account`, `covered_by_broad`, `new_to_add`. Do NOT introduce new bucket names.
- For each re-tagged entry, append a `"retag_reason"` field with one of the 5 anchor case labels (e.g., `"token_reorder"`, `"match_type_drift"`, `"semantic_synonym"`, `"narrowing_opportunity"`).
- Recompute the `stats` block to reflect the new bucket counts. Total entries must remain unchanged (no kw added or dropped).
- Untouched entries: leave verbatim.

**Anti-patterns:**

- **Don't invent new bucket names.** The 4 buckets are locked — re-tag entries between them; do NOT create `maybe_active` or similar.
- **Don't drop entries.** Re-tagging must preserve total kw count. Operator-side audit relies on the count staying constant.
- **Don't re-tag without evidence.** Each re-tagged entry must have a `retag_reason` matching one of the 5 anchor cases. If a case doesn't fit any, leave the entry alone.
- **Don't run on briefs without `positives-sync.json`.** Phase 14 graceful-skip (POS-05) means absent file = nothing to re-tag. Halt the step silently.

**Downstream contract:** After this step, re-invoke `render_report.py`
(Step 35) so `report.md` / `report.html` / `report.json` pick up the refined
buckets. `export/positives.csv` consumes the same refined
`positives-sync.json` automatically on the next `export_csv.py` invocation
(no separate re-run needed for the CSV — `render_report.py` is the only
script that has to re-read the refined sidecar).

## Step 35: Re-render report

```bash
uv run --with python-slugify --with python-dotenv --with tabulate \
  "${CLAUDE_SKILL_DIR}/scripts/render_report.py" --run-dir "{run_dir}"
```

`render_report.py` auto-detects `ranked-enriched.json`, `account-perf.json`,
and `negatives-sync.json` — adds new sections to the report:

- **Account Performance** — totals, converted terms, lossy terms, top by ROAS
- **Negative Keyword Sync** — already-in-account vs new candidates
- **Ranked Keywords — Volume-Enriched** — replaces the plain ranked table
  when Ahrefs data is present; adds Vol/mo, CPC, KD, Parent Topic columns

Surface to operator: report.md / report.json / report.html updated. Phase 8 done.

## Anti-patterns

- **Don't run volume_enrich without Phase 6 first.** Needs `ranked.json` as input.
- **Don't commit `google-ads.yaml` or `.env`.** Both must stay git-ignored.
- **Don't mutate `ranked.json` in place.** volume_enrich writes a separate
  `ranked-enriched.json` so the original ranking stays auditable.
- **Don't run perf_fetch against a customer the operator hasn't been
  granted Admin role on.** PERMISSION_DENIED errors waste no quota but
  confuse the operator.
- **Don't bid on keywords with KD > 70 in the same campaign budget as
  KD ≤ 30 keywords.** Different ad group strategy required. Skill report
  presents data; bidding decisions remain operator's call.

## Failure modes

- **Ahrefs quota exhausted**: surface `429` from stderr. Operator either
  upgrades plan or runs fewer enrichments per month.
- **Google Ads token wrong tier**: `KeywordPlanIdeaService` (not used in
  Phase 8) requires Basic+. `search_term_view`, `campaign`,
  `campaign_criterion` queries used here work with all tiers — so this
  shouldn't surface unless token is fully invalid.
- **MCC mismatch**: `login_customer_id` must parent the `customer_id`
  being queried, OR `login = customer` for direct access. Empirically,
  for Appflow's setup direct access (`login == target`) works.
