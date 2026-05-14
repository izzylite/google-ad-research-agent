# Phase 9 — Campaign Economics and Compliance

Starter Max-CPC bids, per-cluster budget forecast bands, and regulated-vertical
compliance flags. Pure-compute phase — no new external APIs. All output enriches
existing v1.0 artifacts or writes new sidecar JSON files. Runs after Phase 8
because bid logic and budget forecast both consume Ahrefs `cpc_micros` from
`ranked-enriched.json`.

## When to run

After Phase 8 (`ranked-enriched.json` exists with `cpc_micros` field).

Phase 9 is **mandatory for the v1.1 launch-kit workflow** — Phase 10 (Editor
CSVs + Next-Steps checklist) reads Phase 9's `suggested_max_cpc_micros`,
`forecast.campaign_totals.daily_spend_mid_usd`, and
`compliance-flags.json.matched_verticals[]` directly. Skip Phase 9 only if the
operator explicitly wants the v1.0 report without launch-kit data.

Recommended cadence:
- **Per campaign brief** — once after Phase 8 lands.
- **Re-run on the same run folder** — safe and idempotent. `bid_suggest.py`
  mutates `ranked-enriched.json` additively; `forecast_budget.py` and
  `compliance_check.py` overwrite their sidecars from scratch each call.

## Prerequisites

- `{run_dir}/ranked-enriched.json` exists (from Phase 8 `volume_enrich.py`).
- `{run_dir}/clusters.json` exists (from Phase 4 cluster validation).
- `{run_dir}/brief.md` exists (from Phase 1).
- `.claude/skills/google-ad-research/references/compliance-verticals.json`
  exists with 5 starter verticals (shipped in plan 09-00; operator-editable —
  add, remove, or extend any vertical without touching Python).
- No new `.env` keys — Phase 9 reads no secrets and makes zero API calls.

## Step 36: Confirm operator wants Phase 9

Ask the operator:

> "Run Phase 9 (Campaign Economics + Compliance)? Adds Suggested Max CPC per
> keyword, per-cluster + campaign-level budget forecast bands, and a
> regulated-vertical compliance scan. No API costs — pure compute against
> existing run-folder data. ~10 seconds runtime."

If no → stop. If yes → continue to Step 37.

## Step 37: Run `bid_suggest.py`

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/bid_suggest.py" --run-dir "{run_dir}"
```

Parse stdout JSON. Surface `rows_enriched`, `rows_with_cpc`,
`rows_using_fallback`, `rows_no_cpc_data` to the operator. A healthy run has
`rows_enriched == len(ranked-enriched.json)` and `rows_no_cpc_data` only
non-zero when clusters are too small or sparse to produce a median CPC.

Exit codes:
- **0** → continue.
- **3** → fatal (missing `ranked-enriched.json` or `clusters.json`); surface
  stderr; do not proceed. Phase 8 likely did not run, or the run-folder was
  partially deleted.

Produces: `ranked-enriched.json` mutated additively — every row now has
`suggested_max_cpc_micros` (int or null) and rows that could not be priced have
`no_cpc_data: true`. Original keys (`keyword`, `intent`, `score`, `cpc_micros`,
etc.) are preserved verbatim.

## Step 38: Run `forecast_budget.py`

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/forecast_budget.py" --run-dir "{run_dir}"
```

Parse stdout JSON. Surface `clusters_forecast`, `keywords_in_forecast`,
`daily_spend_mid_usd`, `unjoined_keywords` to the operator.

If `unjoined_keywords > 0`: warn the operator — cluster keyword strings did not
match `ranked-enriched.json` strings (likely casing or whitespace drift
introduced by re-clustering or hand-edits). Do not block; surface the count and
let the operator decide. Drift > 5% typically warrants re-running Phase 4
clustering.

Exit codes:
- **0** → continue.
- **3** → fatal; surface stderr; do not proceed. Usually means `bid_suggest`
  was skipped (no `suggested_max_cpc_micros` on any row) or a fixture file is
  malformed.

Produces: `{run_dir}/forecast.json` (new sidecar). The file carries
per-cluster click and spend bands (low/mid/high) plus a `campaign_totals` block
and a `methodology` block that mirrors the script's tuning constants verbatim
(intent CTRs, avg-CPC ratio, band multipliers, and the "directional, not
Google's official forecast" disclaimer). The methodology block is the
single-source-of-truth for the FRCS-05 disclaimer rendered in `report.md`.

## Step 39: Run `compliance_check.py`

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/compliance_check.py" --run-dir "{run_dir}"
```

Parse stdout JSON. Surface `matched_verticals_count` and the `verticals` list
(e.g., `["medical"]`) to the operator.

If any vertical matched, tell the operator:

> "⚠ Compliance flagged: {verticals}. Verification URLs are in
> `{run_dir}/compliance-flags.json`. Phase 10 will reorder the Next-Steps
> checklist to put policy verification first."

If `matched_verticals_count == 0`, surface that too — an empty match is a
positive "scan ran" signal, not a missing-data signal. The sidecar is always
written.

Exit codes:
- **0** → continue.
- **3** → fatal (missing `brief.md` / `ranked-enriched.json` /
  `compliance-verticals.json`, or schema violation in operator-edited
  vertical data); surface stderr; do not proceed.

Produces: `{run_dir}/compliance-flags.json` (always written, even when
`matched_verticals` is empty). Each entry in `matched_verticals[]` carries
`name`, `evidence_tokens`, `evidence_sources` (brief vs keywords split),
`matched_keyword_count`, `verification_url`, and `policy_note`.

## Step 40: Re-render report

```bash
uv run --with python-slugify --with python-dotenv --with tabulate \
  "${CLAUDE_SKILL_DIR}/scripts/render_report.py" --run-dir "{run_dir}"
```

`render_report.py` auto-detects the three Phase 9 artifacts and surfaces each:

- `ranked-enriched.json` rows carrying `suggested_max_cpc_micros` →
  "Suggested CPC" column added to the Volume-Enriched keyword table. Em-dash
  (`—`) renders for null / `no_cpc_data: true` rows.
- `forecast.json` → new **Budget Forecast** section between Ad Group Clusters
  and Negatives, containing per-cluster bands, `campaign_totals`, and a
  "### How this is calculated" subsection that names the four intent CTRs,
  the 0.65 avg-CPC ratio, the band multipliers, and the FRCS-05 "directional,
  not Google's official forecast" disclaimer.
- `compliance-flags.json` with non-empty `matched_verticals[]` → ⚠
  **Compliance Required** blockquote prepended above the Ranked Keywords table
  (yellow `#fef3c7` background in `report.html`). Empty `matched_verticals[]`
  renders nothing — graceful degrade.

`report.json` also gains a top-level `forecast` object and `compliance` array
so Phase 10 (Editor CSV + Next-Steps) can consume the same data without
re-reading the sidecars.

Surface to the operator: `report.md`, `report.json`, `report.html` refreshed;
Phase 9 done.

## Anti-patterns (do not do these)

- **Don't run Phase 9 before Phase 8.** Bid logic needs `cpc_micros` from
  `ranked-enriched.json`. Without Phase 8, every row falls through to the
  null + `no_cpc_data` path and the forecast collapses to zero.
- **Don't hand-edit `references/compliance-verticals.json` from Python.** The
  file is data, not code — operator extends or trims it directly. The 5
  starter verticals are a defensible default, not a contract.
- **Don't mutate `ranked-enriched.json` outside `bid_suggest.py`.** The
  additive-only contract is what lets the script be re-run idempotently. Hand
  edits between bid_suggest and forecast_budget defeat the join.
- **Don't write the Next-Steps checklist in Phase 9.** That's Phase 10
  STEP-01's job. Phase 9 emits the data; Phase 10 assembles the launch kit.
- **Don't manually format USD inside the three scripts.** All math stays in
  micros; USD conversion happens only in `render_report.py` at the display
  boundary (Pitfall 8 invariant). Mixing units inside compute is how you ship
  a $5.78M daily budget instead of $5.78.

## Failure modes

- **Missing `ranked-enriched.json`:** Phase 8 must run first. Surface the
  actionable error from `bid_suggest.py` stderr; do not invent a fallback.
- **Empty cluster CPC pool:** Some keywords land with `suggested_max_cpc_micros
  = null` and `no_cpc_data: true`. This is correct behavior — the report
  renders an em-dash and the operator can override Max CPC manually in the
  Google Ads Editor.
- **Compliance false positive on neutral brief:** Operator can remove the
  offending token from `references/compliance-verticals.json`. The
  substring-with-word-boundary algorithm is intentionally conservative; "loan"
  matches "personal loan" but not "loaner mug". Rare false positives still
  possible — operator edits the JSON, no Python changes.
- **Unjoined keywords > 0 in forecast:** Cluster keyword string casing drifted
  from `ranked-enriched.json`. Cluster names typically come from Phase 4; if
  drift > 5%, re-cluster. Acceptable on first run if < 5% — surface and move
  on.
- **Schema violation in compliance-verticals.json:** `compliance_check.py`
  exits 3 with a `ValueError` message naming the missing field. Operator-edited
  data should fail fast, not silently emit an empty `matched_verticals[]`.

## Downstream contract (read by Phase 10)

- `ranked-enriched.json[i]["suggested_max_cpc_micros"]` → Phase 10 fills the
  Editor CSV `Max CPC` column (EXPT-01). USD conversion happens in the CSV
  builder, not here.
- `forecast.json["campaign_totals"]["daily_spend_mid_usd"]` → Phase 10 fills
  "Set daily budget to $X" in the Next-Steps checklist (STEP-02).
- `compliance-flags.json["matched_verticals"][i]["verification_url"]` →
  Phase 10 reorders Step 1 of the Next-Steps checklist to
  "Complete {vertical} verification at {verification_url}" whenever
  `matched_verticals[]` is non-empty (CMPL-05 / STEP-01). When the array is
  empty, Step 1 reverts to its standard "review keyword list" copy.
- `report.json["forecast"]` + `report.json["compliance"]` (CMPL-04) →
  downstream tooling (dashboards, audit logs, future v2 phases) can consume
  the same data without re-reading the sidecars. Single source of truth for
  the launch kit.
