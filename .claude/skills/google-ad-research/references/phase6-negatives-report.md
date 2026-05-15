## Phase 6: Negatives, Report Assembly, and Persistence

> Prerequisites: Phase 5 complete — `{run_dir}/raw/competitor-intel.json` exists.

### Step 21: Generate negative keywords (NEGT-01, NEGT-02)

Read `{run_dir}/ranked.json` to identify the keyword themes across all clusters. Read `{run_dir}/brief.md` for brand positioning (especially USP, budget tier, and any brand terms).

Generate a JSON array of negative keyword objects. Every object **must** have exactly these four fields:

| Field | Type | Valid values |
|-------|------|--------------|
| `keyword` | string | 1-7 word phrase; NOT a keyword from ranked.json |
| `tier` | string | `Strong` \| `Considered` \| `Investigate` |
| `category` | string | `jobs-careers` \| `free-DIY-tutorial` \| `used-refurb-wholesale` \| `competitor-brand` \| `wrong-geo` \| `wrong-audience` |
| `justification` | string | ≤ 120 chars explaining why this keyword should be excluded |

**Rules:**
- Include ≥ 1 row per tier (Strong, Considered, Investigate)
- Include ≥ 1 row per category (all 6)
- Total: 30-50 negatives
- Do NOT include any keyword that appears in `ranked.json` (that is the positive pool)
- Read the brief positioning before generating Considered-tier negatives — do not negate words that ARE the brand's USP (e.g., do not negate "fast" for a speed-focused brand)
- Always include at least one row matching each baseline trigger: `jobs|careers|salary` → jobs-careers; `free|diy|tutorial|how to|guide` → free-DIY-tutorial; `used|refurb|wholesale` → used-refurb-wholesale

**Example row:**
```json
{
  "keyword": "grocery delivery jobs",
  "tier": "Strong",
  "category": "jobs-careers",
  "justification": "Contains 'jobs' — recruitment intent, never converts for delivery service"
}
```

Write the full array to `{run_dir}/negatives.json` using the Write tool.

**Gate: Do not advance to Step 22 until `{run_dir}/negatives.json` exists with ≥ 1 entry per tier.**

---

### Step 22: Validate and deduplicate negatives (NEGT-03)

Run the validator:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/generate_negatives.py" --run-dir "{run_dir}"
```

Parse stdout JSON. Fields: `valid_count`, `error_count`, `collision_count`, `category_warnings`.

**Exit code handling:**

- **Exit 0:** All rows valid, no collisions, all 6 categories present. Continue to Step 23.
- **Exit 1 (warnings):** Enum errors were auto-fixed, collisions were removed, or one or more categories have zero representatives. Surface to operator:

  > "Negatives validator warnings:
  > - Enum errors fixed: {error_count}
  > - Positive-pool collisions removed: {collision_count}
  > - Missing categories: {category_warnings}
  > - Valid negatives remaining: {valid_count}
  >
  > Proceed with these warnings, or fix and re-run Step 21 for affected rows? (proceed/fix)"

  If operator says **fix**: re-run Step 21 targeting only the missing categories or invalid rows. Then re-run Step 22.
  If operator says **proceed**: continue to Step 23.

- **Exit 3 (fatal):** Surface error from stderr. Do NOT proceed. Tell operator to check that `negatives.json` and `ranked.json` both exist and are valid JSON.

**Gate: Do not advance to Step 23 until validator exits 0 (or operator accepts exit 1 warnings).**

---

### Step 23: Render report (RPRT-01, RPRT-02, RPRT-03, RPRT-04, PRST-01)

Run the report renderer:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/render_report.py" --run-dir "{run_dir}"
```

Parse stdout JSON. Fields: `report_md`, `report_json`, `report_html`, `report_pdf` (may be `null`), `keywords_in_report`.

Surface to operator:
> "Report rendered:
> - report.md: `{report_md}`
> - report.json: `{report_json}`
> - report.html: `{report_html}`
> - report.pdf: `{report_pdf}` (skipped if no system browser found)
> - Keywords in report: {keywords_in_report}"

PDF rendering is best-effort — calls the system's headless Edge/Chrome/Chromium to print the HTML report. If no browser is available the field is `null` and the operator gets a stderr line explaining the skip. The other three outputs are unaffected.

**Gate: Do not advance to Step 24 until both `{run_dir}/report.md` and `{run_dir}/report.json` exist.**

If exit code 3: surface error from stderr. The script prints which required input file is missing. Resolve the missing file and retry.

---

### Step 24: Update run index (PRST-02)

Run the index updater:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/update_index.py" --run-dir "{run_dir}"
```

Parse stdout JSON. Fields: `index_path`, `run_slug`.

Surface to operator:
> "Run index updated: `{index_path}` (slug: `{run_slug}`)"

**Gate: Do not advance to Step 25 until `.runs/INDEX.md` has been updated (verify via the Read tool if needed).**

This script always exits 0. If `brief.md` is missing, industry defaults to "unknown" in the index row.

---

### Step 25: Operator review

Load `{run_dir}/report.md` using the Read tool.

Confirm these sections are present in the file:

- `## How to Read This Report`
- `## Ranked Keywords`
- `## Ad Group Clusters`
- `## Competitor Ad Copy`
- `## Negative Keywords`
  - `### Strong Negatives`
  - `### Considered Negatives`
  - `### Investigate Negatives`

If any section is missing, surface it to the operator and do NOT advance to Step 26.

Summarize the report contents to the operator:
> "Report review complete. Sections confirmed: [list]. Top 3 keywords by score: [keyword — score]. Cluster count: {N}. Negative breakdown: Strong {N}, Considered {N}, Investigate {N}."

**Gate: Operator confirms report is satisfactory before advancing to Step 26.**

---

### Step 26: Final summary and STOP

Tell the operator the complete run summary:

> **Google Ad Research — Run Complete**
>
> - **Run path:** `{run_dir}`
> - **Report (markdown):** `{run_dir}/report.md`
> - **Report (JSON):** `{run_dir}/report.json`
> - **Keywords in report:** {keywords_in_report}
> - **Clusters:** {cluster_count}
> - **Negatives:** {total_negatives} (Strong: {strong_count}, Considered: {considered_count}, Investigate: {investigate_count})
> - **Index updated:** `.runs/INDEX.md` (slug: `{run_slug}`)

**STOP. The Google Ad Research skill workflow is complete for this run.**
