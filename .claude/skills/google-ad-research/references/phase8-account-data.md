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
  [--days 30] \
  [--campaign-filter "{campaign_focus}"]
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

### Campaign focus auto-pass (CAMP-03 / CAMP-04)

> **CAMP-03 (v1.5):** When `brief.md` carries a `**Campaign focus:**` line, read
> it (grep `^- \*\*Campaign focus:\*\*` or via `_parse_brief_fields`) and
> auto-append `--campaign-filter "<value>"` to the `perf_fetch.py` invocation
> above — one quoted arg, pipe-separated list form `'A|B|C'` for multi-campaign.
> The flag adds `AND campaign.name = '<focus>'` (single) or
> `AND campaign.name IN (...)` (list) to all 4 GAQL queries (`keyword_view`,
> `search_term_view`, `campaign`+`ad_group`, `campaign_criterion`+`ad_group_criterion`).
> Announce to the operator BEFORE fetch: `Narrowing to campaign: <focus>`.
>
> **CAMP-04 graceful degrade:** Omit `--campaign-filter` and `perf_fetch.py`
> runs account-wide — current v1.4 behavior preserved bit-for-bit. No code
> path changes; the GAQL queries simply omit the `campaign.name` clause when
> the kwarg is `None`/empty (helper returns `""`). Re-running an existing
> pre-v1.5 brief produces identical raw artifacts.
>
> **Single-quote escape:** Campaign names containing apostrophes (e.g.
> `O'Brien Auto`) are SQL-escaped by `perf_fetch.py` automatically
> (`'O''Brien Auto'`). Operator passes the raw name; the script handles
> GAQL string escaping.
>
> **Pipe-list parsing rule:** ` | ` (space-pipe-space) inside a single quoted
> value is part of a Google-Ads campaign-naming convention (e.g.
> `Search | Lake Worth Accident Exams | Manual CPC` is ONE campaign name).
> Use the bare-pipe form `'A|B|C'` (no spaces) for the multi-campaign list
> form. `perf_fetch.py` applies the same `' | '` vs `'|'` heuristic as
> `render_report.py` so brief field and CLI flag agree.
>
> **Typo handling:** When the focus name doesn't exist in the account, the
> GAQL query returns 0 rows — raw artifacts are empty but valid. The typo
> warning fires later at Step 35 (`render_report.py` cross-checks the focus
> name against `raw/google-ads-perf.json` campaigns list and renders
> `⚠ Campaign name not found in account: '<name>' — check for typo` in
> `## Campaign Focus`). Do NOT fail-fast here; empty raw is its own signal.

### 5 anchor cases (verbatim from CAMP-01..04 design)

1. **Single value (the common case)** — brief has
   `**Campaign focus:** Search | Lake Worth Accident Exams | Manual CPC` →
   skill appends `--campaign-filter "Search | Lake Worth Accident Exams | Manual CPC"`
   (one quoted arg, spaced pipes preserved as one name). GAQL gains
   `AND campaign.name = 'Search | Lake Worth Accident Exams | Manual CPC'`.
2. **List form (rare but real)** — brief has
   `**Campaign focus:** Campaign A|Campaign B|Campaign C` → skill appends
   `--campaign-filter "Campaign A|Campaign B|Campaign C"` (one quoted arg,
   bare pipes split). GAQL gains
   `AND campaign.name IN ('Campaign A', 'Campaign B', 'Campaign C')`.
3. **Single-quote escape** — brief has
   `**Campaign focus:** O'Brien Auto Search` → skill appends
   `--campaign-filter "O'Brien Auto Search"`. GAQL gains
   `AND campaign.name = 'O''Brien Auto Search'` (single quote doubled per
   SQL-string convention; `perf_fetch.py._escape_gaql_string` handles this).
4. **Typo (focus name not in account)** — brief has
   `**Campaign focus:** Search | Lake Worth Accident Examzz | Manual CPC` →
   skill still appends the flag; `perf_fetch.py` returns empty raw artifacts
   (0 rows match the misspelled name); Step 35 `render_report.py` renders
   `⚠ Campaign name not found in account: 'Search | Lake Worth Accident Examzz | Manual CPC' — check for typo`
   in the `## Campaign Focus` section. Operator fixes the brief and re-runs
   Step 33 — the fetch is free quota.
5. **Absent (account-wide v1.4 behavior)** — brief has NO
   `**Campaign focus:**` line → skill omits `--campaign-filter` entirely
   from the invocation; `perf_fetch.py` runs every GAQL query account-wide
   (no `campaign.name` clause); raw artifacts contain every campaign in the
   account; `report.md` has NO `## Campaign Focus` section. Pre-v1.5 briefs
   are unaffected — bit-for-bit byte-identical raw output modulo the
   `campaign_filter: null` traceability key in stdout JSON.

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
- **Don't manually filter raw artifacts by campaign after fetching
  account-wide.** That defeats CAMP-04's clean separation. If you forgot
  the `--campaign-filter` flag, re-run `perf_fetch.py` with the flag set
  — the fetch is free quota; no penalty.
- **Don't quote the pipe-list value with surrounding pipes.** `'A|B|C'`
  (correct) vs `'|A|B|C|'` (wrong — produces empty-name list entries that
  get filtered out, silently turning a 3-campaign list into a 0-clause /
  account-wide fetch).

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

## Phase 15 downstream contract (CAMP-04 inheritance)

The `--campaign-filter` flag narrows the 4 raw artifacts at the source.
Every downstream consumer reads `raw/google-ads-*.json` as-is — no
per-script wiring needed:

- **`perf_synth.py` → `negatives-sync.json`** (Phase 8 GADS-04): cross-refs
  use the already-narrowed `raw/google-ads-negatives.json`; sync section
  reflects only target-campaign negatives.
- **`perf_synth.py` → `positives-sync.json`** (Phase 14 POS-02): same —
  `already_active` / `paused_in_account` buckets reflect only the
  target campaign's keywords. Step 34a LLM re-tag (POS-06) operates on
  the already-narrowed buckets — no campaign-awareness needed in the
  LLM prompt.
- **`ad_group_match.py` → `ad-group-mapping.json`** (Phase 11 ADGM-01..04):
  maps against ad groups inside the target campaign only (e.g. 3 AGs
  under "Lake Worth Accident Exams" instead of 35 account-wide).
  Coverage percentages calibrate against the narrowed denominator —
  Phase 16 enrichment thresholds tune against this narrowed dataset.
- **`render_report.py`**: `## Campaign Focus` callout renders in the
  report header beside `## Geographic Focus` (CAMP-05); typo warning
  fires when brief's focus name not in `raw/google-ads-perf.json`
  campaigns list.

No script needs to know about `campaign_focus` — narrowing is a property
of the raw data, not the synth layer. This is the same architectural
pattern as Phase 11 `geo_focus` (filters at SERP harvest + city-token
merge_signals layer; downstream rank/cluster/render unaware).
