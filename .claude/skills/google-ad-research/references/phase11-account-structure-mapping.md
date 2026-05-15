# Phase 11 — Account-Structure Mapping

Geographic refinement (GEO-01..05) + ad-group mapping onto the client's
existing Google Ads account structure (ADGM-01..06). Last v1.2 phase.
Operator's brief narrows research to specific counties/cities; existing
ad-group names from Phase 8 perf data are preserved in the CSV export
and Next Steps checklist when coverage justifies it.

Two concerns share one phase because they are both "make the research
land inside the client's actual account" — geo precision (which sub-area
to target) and structural fit (which existing ad groups to extend).

## When to run

Optional, after Phase 10 (Operator Launch Kit). Phase 11 splits into two
contracts that are partially independent:

- **GEO-01..05** activates the moment the brief carries a `**Geo focus:**`
  line. The serp_fetch augmentation (Step 8) and the merge_signals city
  filter (Step 9) run inside Phases 2-3; Phase 11 only re-renders the
  `## Geographic Focus` callout via render_report.py. Works standalone —
  no Phase 8 dependency.
- **ADGM-01..06** requires Phase 8 artifacts (`raw/google-ads-perf.json`
  + `raw/google-ads-search-terms.json`). If absent, ad_group_match.py
  exits 0 with `skipped_reason: "phase8_artifacts_absent"` and downstream
  renders/CSVs degrade gracefully to Phase 10 behavior (ADGM-01).

Pure-compute phase. No API costs. No `.env` changes.

## Prerequisites

- Phase 1 complete (run folder + `brief.md`; ideally with `**Geo focus:**`
  line for GEO-* path)
- Phase 2 complete (`keywords.json` — city filter already ran during
  merge_signals if state_code + geo_focus both present)
- Phase 8 complete for ADGM-* path (`raw/google-ads-perf.json` +
  `raw/google-ads-search-terms.json`); absent → graceful skip, GEO path
  still works
- Phase 9 complete (`ranked-enriched.json` with `suggested_max_cpc_micros`
  — ad_group_match.py reads ranked-enriched.json with `ranked.json`
  fallback)
- Phase 10 complete (`export_csv.py` + `render_report.py` already wired
  to auto-detect `ad-group-mapping.json` when present)
- `references/us-cities.json` exists in this skill (committed top-~4800
  US cities across 50 states + DC — GEO-04 catalogue)

## Step 44: Confirm operator wants Phase 11

Ask:

> "Run Phase 11 (Account-Structure Mapping)? Maps ranked keywords to
> the client's existing ad groups (from Phase 8 perf data) so
> `positives.csv` uses existing ad-group names instead of new cluster
> slugs, and rewrites Next Steps step 3 when coverage > 50%. Pure
> compute — no API costs. Skip silently if Phase 8 not run; the GEO
> callout still renders if the brief carried `**Geo focus:**`."

If no → stop. If yes → continue.

## Step 45: Validate brief.md carries geo_focus (if relevant)

Read `{run_dir}/brief.md`. If it has a `**Geo focus:**` line, the GEO-*
pipeline is already active:

- `serp_fetch.py` was invoked with `--geo-focus "..." "..."` at Step 8
  (Pitfall 8 dedup applied — see SKILL.md Step 8)
- `merge_signals.py` applied the city filter at Step 9, scoping the
  ranked keyword pool to cities inside the focus area
- The state_code was inferred from the brief's `**Location:**` line via
  `merge_signals._infer_state_code`

No action needed here — geo refinement already happened in earlier
phases. Phase 11's contribution to the GEO contract is render-only
(see Step 47).

If the brief lacks `**Geo focus:**` and the operator wants to add it
now, re-run from Step 2 with the updated brief. (Mid-pipeline geo
addition would require re-fetching serp + re-merging signals; cheaper
to re-run.)

## Step 46: Run ad_group_match.py (ADGM-01..04)

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/ad_group_match.py" --run-dir "{run_dir}"
```

Parse the stdout JSON line. Keys to surface:

- `mapping_path` → `{run_dir}/ad-group-mapping.json` (always emitted —
  empty matches[] on graceful skip)
- `total_ranked` → count of ranked keywords scored
- `matched_high`, `matched_medium`, `unmapped` → tier counts
- `coverage_pct` → `(high + medium) / total * 100.0` (Pitfall 7: strict
  high+medium only; low tier does NOT count toward coverage)
- `skipped` → `true` when Phase 8 artifacts absent; mapping is empty but
  downstream renders/CSVs still work (ADGM-01)

Exit codes (project taxonomy — mirrors Phase 8 `perf_synth.py` /
Phase 9 `compliance_check.py`):

- **0** → continue (including graceful skip)
- **2** → retryable disk-write error (`PermissionError` / `OSError`);
  offer the operator one retry
- **3** → fatal (`--run-dir` missing; `ranked.json` AND
  `ranked-enriched.json` both absent); stop and surface stderr

Surface coverage to the operator:

> "Mapping complete: {matched_high} high-confidence, {matched_medium}
> medium, {unmapped} unmapped → coverage {coverage_pct}%. {when
> coverage_pct > 50.0: 'Next Steps step 3 will rewrite to use existing
> ad groups.'} {when coverage_pct ≤ 50.0: 'Next Steps step 3 will keep
> the default — create new cluster ad groups.'}"

**Do not advance to Step 47 until** `{run_dir}/ad-group-mapping.json`
exists on disk (verify with the Read tool or quick `ls`) and stdout
parsed cleanly.

## Step 47: Re-render report and re-export CSVs (ADGM-05, ADGM-06, GEO-05)

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/export_csv.py" --run-dir "{run_dir}"

uv run --with python-slugify --with python-dotenv --with tabulate \
  "${CLAUDE_SKILL_DIR}/scripts/render_report.py" --run-dir "{run_dir}"
```

`export_csv.py` auto-detects `ad-group-mapping.json`:

- `positives.csv` `Ad Group` column = existing ad-group name for
  high/medium matches; cluster slug for low/unmapped (ADGM-05)
- `ad_groups.csv` filters out existing ad-group names so Editor v2.x
  does not throw "Ad group already exists" errors on import
- Stdout JSON gains `existing_ad_groups_used`, `new_ad_groups_emitted`,
  `mapping_coverage_pct`

`render_report.py` auto-detects `ad-group-mapping.json` + brief `Geo focus`:

- New `## Geographic Focus` callout under the report Header when brief
  has `**Geo focus:**` (GEO-05): `**Location:** ... → **Focus:** ...`
- Next Steps step 3 rewrites to
  `"Add keywords to existing ad groups: <name> (<N> kw), ..."` when
  `mapping_coverage_pct > 50.0` strict (ADGM-06; see Failure modes for
  the boundary case)
- `report.json` adds top-level `geographic_focus` (always — empty focus
  list when brief has no geo line) + `ad_group_mapping_summary` (only
  when sidecar present)

Surface to operator: `report.md` / `positives.csv` / `ad_groups.csv`
updated. Phase 11 done.

## Anti-patterns

- **Don't run `ad_group_match.py` before Phase 8.** Without
  `raw/google-ads-perf.json` + `raw/google-ads-search-terms.json` the
  script exits 0 with an empty mapping
  (`skipped_reason: "phase8_artifacts_absent"`), which downstream
  tooling handles fine — but you've gained nothing. Run Phase 8 first.
- **Don't mutate `ad-group-mapping.json` by hand.** It's regenerated by
  `ad_group_match.py` each run. Edit `ranked.json` /
  `ranked-enriched.json` or `brief.md` upstream instead; manual sidecar
  edits are clobbered.
- **Don't normalise Unicode characters in existing ad-group names.**
  En-dash (U+2013) and em-dash (U+2014) are common in Google Ads
  account names (e.g., "Accident Exams – Lake Worth"). The whole
  pipeline preserves them byte-for-byte (Pitfall 2 — verified by
  `test_unicode_dash_preserved_in_csv`). Manual edits that strip them
  WILL break the CSV byte contract.
- **Don't expect coverage > 50% in narrow verticals.** A 3-ad-group
  account vs. a 20-keyword ranked list often shows 30-40% coverage —
  that's correct behaviour, not a bug. The Next Steps step-3 keeps the
  "Create ad groups" default; operator manually decides if existing
  names apply.
- **Don't pass `--geo-focus` values that collapse the County suffix
  without spaces.** `"PalmBeachCounty"` fails the lookup;
  `"Palm Beach County"` works (the suffix is stripped during
  `_build_city_filter` normalisation; see Pitfall 5 in
  `11-RESEARCH.md`).

## Failure modes

- **`report.md` missing `## Geographic Focus` section even though brief
  has `Geo focus`:** the brief's `**Geo focus:**` line is malformed.
  Verify with `grep '\*\*Geo focus:' {run_dir}/brief.md`. The parsing
  regex (`run_init._parse_optional_geo_focus`) requires `**` markers
  on both sides; smart quotes, single asterisks, or stray whitespace
  before `**Geo` break the match. Fix the brief, re-run from Step 2.
- **Next Steps step 3 still says "Create ad groups" despite high
  coverage:** check
  ```bash
  python -c "import json,sys; print(json.load(open(sys.argv[1]))['mapping_coverage_pct'])" \
    {run_dir}/ad-group-mapping.json
  ```
  If it prints exactly `50.0`, that's correct — the rewrite threshold
  is **strict** `> 50.0` via `_COVERAGE_REWRITE_PCT = 50.0` (open
  question 4 in 11-RESEARCH.md; Pitfall 7). 50.1 fires; 50.0 does not.
- **`positives.csv` shows cluster slugs instead of existing ad-group
  names:** coverage may be < 50% (low-confidence matches don't
  substitute — Pitfall 7), OR a specific keyword fell below the
  medium-tier threshold (raw jaccard 0.4). Inspect the mapping JSON;
  for any keyword expected to land in an existing AG, find its entry
  in `matches[]` and check `confidence` + `reason`. Jaccard < 0.4
  means the search-term token bag for that AG doesn't overlap enough
  with the keyword vocabulary.
- **`ad_group_match.py` crashes on `ranked-enriched.json` schema
  mismatch:** Phase 8 + Phase 9 must have completed cleanly. If
  `ranked-enriched.json` was manually edited and the script can't
  parse it, the script falls back to `ranked.json` (the bare Phase 3
  output) — but if that's also broken, it exits 3. Restore from git
  or re-run from Phase 3.

## Downstream contract

Phase 11 output that downstream tooling depends on (stable from v1.2
forward — v2 features must not break this contract):

- **`{run_dir}/ad-group-mapping.json`** — schema:
  - `matches[]` — list of
    `{keyword, existing_ad_group | null, confidence, score, reason}`
  - `unmapped_count` — count of confidence=low rows
  - `mapping_coverage_pct` — `(high + medium) / total * 100.0`
    (Pitfall 7)
  - `computed_at` — ISO-Z UTC timestamp
  - `skipped_reason` — `null` on happy path; `"phase8_artifacts_absent"`
    on graceful skip
- **`report.md`** — `## Geographic Focus` section (below Header,
  above the main body) + conditional Next Steps step-3 rewrite
- **`report.json`** — top-level keys:
  - `geographic_focus: {location, focus[]}` — always emitted; empty
    focus list when brief has no geo line
  - `ad_group_mapping_summary: {coverage_pct, matched_high, matched_medium, unmapped}`
    — only when mapping sidecar exists
- **`export/positives.csv`** — `Ad Group` column substituted for
  high/medium matches (cluster slug otherwise); Unicode dashes
  preserved byte-for-byte
- **`export/ad_groups.csv`** — existing ad-group names filtered out
  so Editor v2.x import doesn't error on duplicate-name

This contract is the upstream API spec for any v2 work
(report-diffing, multi-account rollups, automated bid management).

## Phase 16: Token-Bag Enrichment (ADGM-07..11)

**Why Phase 16 exists.** Phase 11's search-terms-only token bag returned 0%
Lake Worth coverage (2026-05-15 dogfood) — three ad groups with sparse
30-day search history (one ENABLED, two PAUSED) yielded bags too thin to
overlap ranked-keyword vocabulary. Phase 16 unions the AG name + active
`kw_criteria` (from Phase 14's `raw/google-ads-keywords.json`) + top-10
search terms by clicks so each AG bag carries enough signal to score.

**Bag composition.** `bag(ag) = _tokens(ag.name) ∪ _tokens(kw.text) for kw
in active kw_criteria where ad_group_name == ag.name ∪ _tokens(st.search_term)
for st in top-10 search_terms by clicks desc (tiebreak impressions desc, drop
impressions==0)`. Active = `kw.status != "REMOVED"`. Top-N defaults to 10
(`_build_ag_token_bag(top_n_terms=10)`). Same `_tokens()` regex + stopword
filter from Phase 11 across all sources — no per-source vocabulary drift.

**Per-source attribution.** High/medium matches carry partial Jaccards in
`match.reason` so operators can audit which source pulled the match. Format:
`jaccard=X.XX (name=Y.YY kw-criterion=Z.ZZ search-term=W.WW) intent_match=B`.
`jaccard` is the score pre-intent-multiplier — pre-16-04: full-union;
post-16-04: `max(name_j, crit_j, term_j)`. Low matches keep the simpler
`jaccard=X.XX intent_match=B` shape (no spurious partials against unmatched
bags).

**Threshold calibration.** 16-01 lowered `_THRESHOLDS` from Phase 11
`{high: 0.7, medium: 0.4}` to the loosening-cap FLOOR `{0.30, 0.10}`
(operator option-a, lowest pair preserving Phase 11's 80% invariant + C5
garbage-low guard). **Superseded by 16-04** which ships `{0.30, 0.08}`
under the max-Jaccard algorithm (next subsection). Under full-union, no
threshold pair in the loosening cap reached ADGM-11's ≥50% floor —
Lake Worth's 34-token bag vs 4-6-token queries capped scores at
0.15-0.25 (structural ceiling, not tuning miss). Plans 16-03 + 16-04
closed ADGM-11 via per-source max-Jaccard.

**Backward-compat contract.** When `raw/google-ads-keywords.json` is absent
(no Phase 14 OAuth opt-in, or pre-v1.4 account), the bag gracefully
degrades to `_tokens(ag.name) ∪ top-10 search-term tokens`. Coverage on
Lake Worth-shape accounts will sit in the Phase 11 ballpark (<20%) in that
mode — the enrichment is additive, not load-bearing. Test fixture:
`tests/test_ad_group_match.py::test_backward_compat_keywords_absent`.

### Plan 16-04: Per-Source Max-Jaccard Structural Fix (ADGM-11)

**Why full-union Jaccard underperformed.** 16-02 live e2e reason field:
`jaccard=0.10 (name=0.33 kw-criterion=0.00 search-term=0.00) intent_match=True`.
Name alone scored 0.33 — well above the high threshold — but the full-union
denominator (~34 AG bag tokens vs 4–6 query tokens) diluted the combined
score to 0.10, structurally masking the strongest channel. Per-source
max-Jaccard preserves it directly: same match → 0.33.

**Algorithm one-liner.** `ad_group_match.py::build_mapping` (Plan 16-04):

```python
# 16-04: per-source max replaces full-union jaccard.
name_j = _jaccard(kw_tokens, ag["name_tokens"])
crit_j = _jaccard(kw_tokens, ag["criterion_tokens"])
term_j = _jaccard(kw_tokens, ag["search_term_tokens"])
raw_j  = max(name_j, crit_j, term_j)
# intent_multiplier still applies multiplicatively to raw_j
```

The cached `best_partials` tuple inside the per-AG loop powers the
reason-field rendering — reason now causally aligned with the score (was
decorative under full-union).

**Calibration sweep (Plan 16-04 Task 2).** Sweep over the goldenfile +
Phase 11 fixture under max-Jaccard:

| `{high, medium}` | Lake Worth (offline/live) | Phase 11 | C5 garbage-low | Outcome |
|------------------|---------------------------|----------|----------------|---------|
| {0.30, 0.10}     | 54.55% / 50.75%           | 80%      | 0.0%           | PASS (16-01 floor; medium guard structurally obsolete under max) |
| {0.30, 0.08}     | 54.55% / 50.75%           | 80%      | 0.0%           | **PASS (option-d shipped)** — admits `name_j ≈ 0.083` borderline matches |

Garbage keywords (`tomato sandwich`, `quantum mechanics tutorial`) score
exactly 0.0 under max-Jaccard (no shared tokens → all partials 0.0). The
16-01 medium=0.10 floor was a defensive guard against full-union dilution
producing low-but-nonzero garbage scores — structurally eliminated by
`max()`. Option-d lowers medium to 0.08 to admit legitimate name-only
matches where `name_j = 1/12 ≈ 0.083`.

**Live e2e closeout.** Real Lake Worth OAuth account observed
`mapping_coverage_pct = 50.75%` post-Plan 16-04 (operator-approved); 52
of 67 matches show non-zero `kw_criterion` contribution (vs all-zero
pre-shape-fix). Trajectory: 0% (Phase 11) → 16.67% / 16.42% (16-01/02
full-union) → 41.79% (16-04 max-Jaccard pre-shape-fix) → **50.75%**
(16-04 post-shape-fix).

**Reader/writer shape-contract fix (Task 2.5 deviation, commit `56d4196`).**
Task 3 initial measurement was 41.79% (below offline prediction).
Investigation surfaced a **preexisting** bug latent since 16-01:
`ad_group_match.py` read keywords via nested Google Ads raw API shape
(`kw.ad_group_criterion.keyword.text` / `.status` / `.ad_group.name`),
while the canonical OAuth writer at `perf_fetch.py:292-303` emits **flat**
shape (`kw["keyword"]`, `kw["status"]`, `kw["ad_group_name"]`). The 16-00
fixture was hand-reshaped to nested, matching the broken reader and papering
over the divergence offline (both sides wrong-but-matched). Every live run
from 16-01 through pre-fix silently had zero `kw_criterion` contribution.
Fix: 4 field accesses flipped nested→flat (Rule 3 Blocking deviation).
Lesson: shape contracts surface at live e2e, not unit tests — sample the
live OAuth response, not just the goldenfile.

**ADGM-11 status: Complete.** Floor met (>=50%); 16-01's `xfail` removed
in 16-03; per-source max-Jaccard + shape-fix shipped 16-04. Watch-item:
next-account calibration cycle (2nd OAuth account) — re-run the sweep
table on that account before treating {0.30, 0.08} as universally locked.
