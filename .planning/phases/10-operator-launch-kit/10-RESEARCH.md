# Phase 10: Operator Launch Kit — Research

**Researched:** 2026-05-14
**Domain:** CSV export (Google Ads Editor v2.x format) + Markdown/HTML/JSON checklist rendering on existing Python stdlib + tabulate stack
**Confidence:** HIGH (stack/patterns/pitfalls); MEDIUM (Editor case sensitivity for Match Type values — verified by behavior, not strict docs)

## Summary

Phase 10 is the v1.1 "launch kit" capstone — purely additive, zero new dependencies, zero external API calls. It mounts on top of Phase 9's three artefacts (`ranked-enriched.json` with `suggested_max_cpc_micros`, `forecast.json` with `campaign_totals.daily_spend_mid_usd`, `compliance-flags.json` with `matched_verticals[].verification_url`) and produces (a) three Google Ads Editor v2.x-importable CSVs under `{run_dir}/export/`, (b) a substituted "Next Steps" markdown checklist appended to `report.md`, (c) localStorage-backed HTML checkboxes for per-session progress, (d) two new top-level keys in `report.json` (`next_steps[]`, `exports[]`).

Three architectural choices are locked by upstream decisions and project conventions:
1. **Single `export_csv.py`** (not three scripts) — single workflow step, single test file, atomic output (mirrors `bid_suggest.py` / `forecast_budget.py` / `compliance_check.py` shape from Phase 9).
2. **Next-Steps rendering lives in `render_report.py`** (not a new sidecar) — substitution happens at render time from brief + forecast + compliance, which are already loaded in `main()`.
3. **SKILL.md extension is a pointer only** (3-line budget at most — currently 497/500). Detail lives in `references/phase10-operator-launch-kit.md`, mirroring Phase 5/7/8/9 pattern verbatim.

**Primary recommendation:** Treat Phase 10 as a thin output layer. All hard problems (bid math, forecast math, compliance scan, micros→USD display conversion) are solved in Phase 9. Don't re-derive; consume the existing `report.json` keys (`forecast.campaign_totals.daily_spend_mid_usd`, `compliance` array, `keywords[].suggested_max_cpc_micros`) and `brief.md` fields (location, language, audience). Stdlib `csv` module is sufficient — no third-party CSV library needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md file exists for Phase 10 (Phase 10 was scoped directly via ROADMAP.md success criteria + REQUIREMENTS.md IDs). The orchestrator-provided `additional_context` carries the equivalent locked-decision content; treating it as the user-constraint source for the planner.

### Locked Decisions (from orchestrator additional_context + roadmap success criteria)

- **Single `export_csv.py` script** writing all three CSVs to `{run_dir}/export/` (not three separate scripts).
- **Three Editor CSV files** with exact filenames: `positives.csv`, `negatives.csv`, `ad_groups.csv`.
- **Exact column headers** (Google Ads Editor v2.x spec):
  - `positives.csv`: `Campaign, Ad Group, Keyword, Match Type, Max CPC, Final URL`
  - `negatives.csv`: `Campaign, Ad Group, Keyword, Match Type, Level`
  - `ad_groups.csv`: `Campaign, Ad Group, Status, Default Max CPC`
- **Negatives level rule:** Strong tier → `campaign`; Considered/Investigate → `ad_group`.
- **CSV byte format:** UTF-8 **no BOM**, **CRLF (`\r\n`)** line endings, comma-delimited, RFC 4180 quoting via Python's `csv` module.
- **Next-Steps lives in `render_report.py`** (extend existing module — not a new sidecar script). Substitution happens at render time.
- **CMPL-05 reorder:** when `compliance-flags.json["matched_verticals"]` has ≥ 1 entry, prepend a single combined "Complete {verticals} verification at {URLs}" step as step 1 and renumber the remaining 8 ops steps. Multiple matched verticals → ONE combined step with all verticals and URLs (not multiple top-level steps).
- **HTML interactivity:** copy-able command snippets + `<input type="checkbox">` per step with localStorage persistence. localStorage key namespaced by run slug (`{run_slug}_step_{id}`) so cross-run progress does not bleed.
- **JSON contract additions:** `report.json` gains a top-level `next_steps[]` array (each entry `{n, text, id}`) and a top-level `exports[]` array (each entry a CSV file path string relative to `run_dir`).
- **No new dependencies.** Phase 10 is pure stdlib + existing tabulate. PEP 723 inline `dependencies = []` for `export_csv.py`.
- **No new external API calls.** Phase 10 is pure compute against existing `run_dir` artefacts.
- **Run-folder isolation respected:** CSVs land under `{run_dir}/export/` subfolder (NOT root run_dir).
- **Phase 10 is the final v1.1 phase.** No further phases consume Phase 10 output — `next_steps[]` and `exports[]` are leaves.

### Claude's Discretion

- **Campaign + Ad Group naming convention:**
  - **Campaign name source:** brief slug (already derived by `_derive_brief_slug(run_dir)` in `render_report.py:693`). Slug is human-readable, run-stable, and already shown to the operator in `report.md`. Title-case the slug for the Campaign column to match Editor norms (e.g., `same-day-grocery-delivery-uk` → `Same-Day Grocery Delivery UK`). Document the convention in the rubric.
  - **Ad Group name source:** cluster `name` field verbatim (e.g., `same_day_delivery_transactional`). The `theme_intent` format from Phase 4 is already operator-recognisable and used in `report.md`'s clusters section. Do NOT massage / hyphenate / title-case — Phase 4 owns the format.
- **Final URL column:** `brief.md` has no website-URL field today. Render as empty string per row (operator pastes URLs in Editor). Document as a v1.2 candidate brief field. Do NOT block on this.
- **Match Type case:** Google Ads Editor accepts `Broad` / `Phrase` / `Exact` (title-case) for positives. For negatives, the Type column wants `Campaign negative` or `Negative {Phrase|Exact}` — but our `negatives.csv` uses a separate `Level` column (NOT the Editor's native `Type` column). The Editor `Match Type` column for the negatives CSV still takes the bare match type (`Phrase` / `Exact` / `Broad`); `Level` is our metadata signalling where the operator should paste. **Title-case at the CSV write boundary** — internal Python uses lowercase `phrase` / `exact` / `broad`. Single `_titlecase_match_type()` helper at the top of `export_csv.py`.
- **Empty inputs:** Empty `negatives.json` (or no Strong/Considered/Investigate rows) → write `negatives.csv` with HEADER ONLY, no data rows. Same for empty `clusters.json` → header-only `positives.csv` + `ad_groups.csv`. Do not crash. Do not omit the file.
- **Empty / zero-CPC clusters:** A cluster with 0 keywords having Ahrefs volume still gets one row in `ad_groups.csv` with `Default Max CPC = 0.00`. Operator override in Editor. (Documented in Phase 9 — clusters with all-null `suggested_max_cpc_micros` render `—` in markdown but `0.00` in CSV — Editor rejects empty numeric cells; "0.00" + an operator override is the safe escape hatch.)
- **HTML checkbox stable IDs:** SHA-1 hash of step text, truncated to 8 chars. Stable across re-renders of the same step content, namespaced per run slug.
- **Wave structure** (3 waves + a Wave 0):
  - Wave 0 — test scaffolding + golden CSV bytes fixtures + extended `test_render_report.py` for Next-Steps
  - Wave 1 — `export_csv.py` (EXPT-01..04) + `render_report.py` Next-Steps extension (STEP-01..04 + CMPL-05) in parallel (no shared file mutation: separate script vs. render extension)
  - Wave 2 — integration: EXPT-05 (`render_report.py` Export Files section + `report.json` `exports[]`); `next_steps[]` already wired in Wave 1's render extension
  - Wave 3 — SKILL.md pointer (3 lines under 500-cap) + `references/phase10-operator-launch-kit.md` + end-to-end human-verify smoke

### Deferred Ideas (OUT OF SCOPE for Phase 10)

- **Direct Google Ads API push** (TOOL-02 in v2 deferred bucket per REQUIREMENTS.md L168). Manual Editor import is the deliberate "bad-data gate."
- **Brief field for website URL** (Final URL column population) — defer to v1.2 brief schema.
- **Real-time / scheduled CSV regeneration** — out of scope per REQUIREMENTS.md "Real-time / scheduled / cron runs."
- **Multi-locale fan-out** — TOOL-04 v2.
- **Run-diff CSV comparison** — TOOL-03 v2.
- **Daily Clicks float-formatting cleanup** (e.g., 0.44000000000000006) — known cosmetic from Phase 9, deferred per STATE.md decision (not blocking).
- **Customizable Next-Steps templates per vertical** — generic 8-step ordering is the v1 contract.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXPT-01 | `export_csv.py` writes `{run_dir}/export/positives.csv` with columns `Campaign, Ad Group, Keyword, Match Type, Max CPC, Final URL` in Google Ads Editor v2.x format. | Use Python stdlib `csv.DictWriter` with `quoting=csv.QUOTE_MINIMAL`, file opened with `encoding="utf-8"`, `newline=""`, and `lineterminator="\r\n"` on the writer. Title-case match type at write boundary. Max CPC formatted from micros via `f"{micros/1_000_000:.2f}"`. Iterate `ranked-enriched.json` cross-referenced with cluster index from `clusters.json`. |
| EXPT-02 | `export_csv.py` writes `{run_dir}/export/negatives.csv` with `Campaign, Ad Group, Keyword, Match Type, Level`; Strong → `campaign`, Considered/Investigate → `ad_group`. | Read `{run_dir}/negatives.json` (Phase 6 schema: list of dicts with `tier`, `keyword`, `category`, `justification`). Tier-to-Level map literal at top of `export_csv.py` (single source of truth). When Level=`campaign`, Ad Group field is empty string (not "ALL" — Editor expects empty). Match Type defaults to `Phrase` per NEGT default. |
| EXPT-03 | `export_csv.py` writes `{run_dir}/export/ad_groups.csv` with `Campaign, Ad Group, Status, Default Max CPC`. | Iterate `clusters.json` clusters. Status = `Enabled` per row. Default Max CPC = cluster-median `suggested_max_cpc_micros` (already computed in Phase 9 `bid_suggest.py`); fall back to `0.00` for empty / all-null clusters. |
| EXPT-04 | Editor-importable verification — UTF-8 no BOM, CRLF, exact headers, `csv.DictReader` round-trip. | Write byte-level assertions in `test_export_csv.py`: `bytes_read[:3] != b"\xef\xbb\xbf"` (no BOM); `b"\r\n" in bytes_read`; `set(reader.fieldnames) == EXPECTED_HEADERS`; round-trip parses back to identical dicts. |
| EXPT-05 | `render_report.py` adds "Export Files" section linking CSVs; `report.json["exports"]` is stable array of paths. | New `render_export_section(run_dir)` helper returning markdown bullet list with relative paths (`export/positives.csv`, etc.). `build_report_json()` extends with `exports: list[str]` kwarg or computes from run_dir layout. Lives in `render_report.py` integration wave. |
| STEP-01 | `render_report.py` appends `## Next Steps` to `report.md` with ordered 8-step ops checklist. | New `render_next_steps_section(brief_fields, forecast, compliance, clusters_data)` helper. Returns markdown numbered list. Step template literal at top of `render_report.py` as `_NEXT_STEPS_TEMPLATE` constant. Pure-string substitution from inputs. |
| STEP-02 | Checklist substitutes brief values (location, language, audience, budget) and forecast values (mid spend) into each step. | Inputs already parsed: `_parse_brief_fields(brief_text)` exists at `render_report.py:676`; `forecast["campaign_totals"]["daily_spend_mid_usd"]` is already loaded. Substitute via `.format()` or f-string at render time. Format USD as `f"${X:.2f}"`. |
| STEP-03 | HTML report renders the checklist with copy-able command snippets and localStorage-backed checkboxes for per-session progress. | Extend `_HTML_TEMPLATE` with a `<section id="next-steps">` block. `renderNextSteps()` JS function reads `REPORT.next_steps`, emits `<li><input type="checkbox" id="step_{run_slug}_{step_id}">{text}</li>` + a `<pre><code>` snippet for any `command` field. Save/restore on input change via `localStorage.setItem`. Stable IDs: SHA-1 hash truncated to 8 chars. |
| STEP-04 | `report.json["next_steps"]` is ordered list of `{n, text, id}` entries. | Extend `build_report_json()` with `next_steps=None` kwarg + emit top-level key. List computed by same helper that renders markdown — single source of truth. |
| CMPL-05 | When `compliance-flags.json["matched_verticals"]` has ≥ 1 entry, prepend "Complete {vertical(s)} verification at {URL(s)}" as step 1; renumber remaining steps. | Implemented in the same `render_next_steps_section()` helper. Reorder logic: if `compliance and compliance.get("matched_verticals")`, prepend a single combined step (joining verticals with " + " and listing all URLs). All numbering derived from final list position — never hardcoded. Multiple verticals → ONE combined step (not N). |
</phase_requirements>

## Standard Stack

### Core (no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `csv` (stdlib) | 3.11+ | Write Editor-importable CSV with RFC 4180 quoting | Stdlib — already available. Handles quoting (commas in keywords), escaping, and explicit `lineterminator="\r\n"`. No third-party CSV lib needed. |
| Python `pathlib` (stdlib) | 3.11+ | `{run_dir}/export/` folder creation + atomic write via `.tmp` rename | Already used everywhere in the project (run_init, bid_suggest, forecast_budget, compliance_check). Pattern is established. |
| Python `hashlib` (stdlib) | 3.11+ | SHA-1 step IDs (truncated to 8 chars for HTML checkbox stable IDs) | Stdlib. Step IDs need to be deterministic across renders so localStorage state survives re-rendering. |
| `tabulate` | >=0.9.0 | Markdown table rendering (used by Next-Steps if rendered as a table; mostly used in Export Files section) | Already in `scripts/pyproject.toml` and `render_report.py` PEP 723 deps. Same usage pattern. |

### Supporting (already in `scripts/pyproject.toml`)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dotenv` | >=1.0 | Already loaded in render_report.py PEP 723; Phase 10 reads no env vars | No-op for Phase 10 — present for consistency only. |
| `python-slugify` | >=8.0 | Slug derivation if needed (run_init already derives slug; render_report has `_derive_brief_slug`) | Reuse `_derive_brief_slug(run_dir)` — do NOT re-import slugify. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stdlib `csv` | `pandas` `to_csv` | pandas adds ~50MB transitive deps, defeating PEP 723 inline-deps portability; stdlib `csv` handles the exact 3-column CSVs trivially. Rejected. |
| Stdlib `csv` | Manual string concatenation | Manual approach fails RFC 4180 quoting on keywords with commas/quotes — silent data corruption risk. Rejected. |
| Hand-coded HTML checkbox state | localForage / external lib | Stdlib + vanilla JS localStorage is sufficient; we already inline-render the HTML template (`_HTML_TEMPLATE`) with no JS deps. Rejected dependency add. |
| New `next_steps.py` sidecar | Inline render in `render_report.py` | Sidecar adds plumbing (one more CLI invocation, one more `--run-dir` arg, one more SKILL.md step). All inputs are already loaded in render_report.py's `main()`. Inline is strictly better. |

**Installation:** No new packages required. `export_csv.py` uses PEP 723 inline `dependencies = []`.

## Architecture Patterns

### Recommended Project Structure (Phase 10 additions)
```
.claude/skills/google-ad-research/
├── scripts/
│   ├── export_csv.py                    # NEW — single script, writes all 3 CSVs
│   ├── render_report.py                 # EXTENDED — adds render_next_steps_section,
│   │                                    #            render_export_section,
│   │                                    #            HTML template additions
│   └── tests/
│       ├── test_export_csv.py           # NEW — byte-level + round-trip tests
│       ├── test_render_report.py        # EXTENDED — Next-Steps + Export Files cases
│       └── fixtures/
│           ├── negatives_phase10.json   # NEW — Strong/Considered/Investigate spread
│           ├── compliance_with_match.json   # NEW — fixture for CMPL-05 reorder test
│           └── compliance_empty.json    # NEW — fixture for standard order test
├── references/
│   └── phase10-operator-launch-kit.md   # NEW — operator rubric (Steps 41-43 or 41-44)
└── SKILL.md                              # EXTENDED — 3-line pointer (currently 497/500)

{run_dir}/
└── export/                               # NEW subfolder — Phase 10 outputs
    ├── positives.csv
    ├── negatives.csv
    └── ad_groups.csv
```

### Pattern 1: Single-script, three-CSV writer (mirrors Phase 9 scripts)
**What:** One `export_csv.py` script that reads upstream artefacts once, writes three CSVs in sequence, prints one stdout summary JSON line, returns exit code.
**When to use:** Whenever multiple sibling output files share inputs and lifecycle. Phase 9's `bid_suggest.py` / `forecast_budget.py` / `compliance_check.py` are each single-output, but this case has three siblings that share `ranked-enriched.json` + `clusters.json` + `negatives.json` — splitting would triple the I/O.
**Example:**
```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""export_csv.py — Write Google Ads Editor v2.x importable CSVs."""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

# --- Constants ---
POSITIVES_HEADERS = ["Campaign", "Ad Group", "Keyword", "Match Type", "Max CPC", "Final URL"]
NEGATIVES_HEADERS = ["Campaign", "Ad Group", "Keyword", "Match Type", "Level"]
AD_GROUPS_HEADERS = ["Campaign", "Ad Group", "Status", "Default Max CPC"]

# Tier → Level (NEGT/EXPT-02 contract)
TIER_TO_LEVEL: dict[str, str] = {
    "Strong": "campaign",
    "Considered": "ad_group",
    "Investigate": "ad_group",
}

MATCH_TYPE_TITLECASE = {"phrase": "Phrase", "exact": "Exact", "broad": "Broad"}


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    """Write one Editor CSV (UTF-8 no BOM, CRLF, RFC 4180 quoting).

    EXPT-04 byte contract: no BOM, CRLF endings, comma-delimited, headers
    exactly match Editor v2.x spec. csv.DictWriter handles RFC 4180 quoting
    (cells containing commas, quotes, newlines wrapped in double quotes).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # encoding="utf-8" (NOT utf-8-sig — the latter writes a BOM, which breaks
    # Editor import on Windows). newline="" + lineterminator="\r\n" gives
    # platform-stable CRLF without double-line-ending bugs.
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=headers, lineterminator="\r\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
```

### Pattern 2: Compliance-aware checklist reorder (CMPL-05)
**What:** A single render function that decides step 1 based on compliance presence, then renumbers all downstream steps from list position (never hardcoded numbers).
**When to use:** Any time output ordering depends on input presence/absence — never hardcode step numbers in the template strings; derive `n` from the final list index at render time.
**Example:**
```python
def render_next_steps_section(
    brief_fields: dict[str, str],
    forecast: dict | None,
    compliance: dict | None,
    clusters_data: dict,
) -> tuple[str, list[dict]]:
    """Return (markdown string, list-of-step-dicts).

    The list is the single source of truth for both report.md and
    report.json["next_steps"]. STEP-01..04 + CMPL-05 in one function.
    """
    location = brief_fields.get("location", "<location>")
    language = brief_fields.get("language", "<language>")
    daily_spend_mid = (
        forecast.get("campaign_totals", {}).get("daily_spend_mid_usd", 0.0)
        if forecast else 0.0
    )
    cluster_names = [c.get("name", "") for c in clusters_data.get("clusters", [])]
    cluster_names_csv = ", ".join(cluster_names) if cluster_names else "<clusters>"

    steps_text: list[str] = []

    # CMPL-05: prepend a SINGLE combined verification step when verticals matched.
    matched_verticals = (compliance or {}).get("matched_verticals", []) or []
    if matched_verticals:
        names = " + ".join(v.get("name", "?").title() for v in matched_verticals)
        urls = "; ".join(v.get("verification_url", "") for v in matched_verticals)
        steps_text.append(
            f"Complete {names} verification at {urls} before launching."
        )

    # The standard 8 ops steps — renumbered when verification prepended.
    steps_text.extend([
        f"Create campaign in {location} ({language}).",
        f"Set daily budget to ${daily_spend_mid:.2f} (Phase 9 mid forecast).",
        f"Create ad groups: {cluster_names_csv}.",
        "Paste positives.csv via Google Ads Editor → Make multiple changes.",
        "Paste negatives.csv at the levels specified by the Level column "
        "(campaign for Strong, ad_group for Considered/Investigate).",
        "Write 3 responsive search ads per ad group using competitor "
        "headline / CTA / offer examples from the Competitor Ad Copy section.",
        "Set Max CPC per keyword from the Suggested CPC column "
        "(or leave Editor's default if Max CPC = $0.00).",
        "Review compliance flags and budget forecast before enabling.",
    ])

    # Build the final list with positional `n` and stable `id`.
    import hashlib
    step_list: list[dict] = []
    for n, text in enumerate(steps_text, start=1):
        step_id = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        step_list.append({"n": n, "text": text, "id": step_id})

    # Render markdown
    parts = ["## Next Steps\n\n"]
    parts.append(
        "_Ordered ops checklist for moving from `report.md` to a live "
        "Google Ads campaign. Check off each step as you complete it._\n\n"
    )
    for step in step_list:
        parts.append(f"{step['n']}. {step['text']}\n")
    parts.append("\n")
    return "".join(parts), step_list
```

### Pattern 3: HTML checkbox with localStorage namespacing (STEP-03)
**What:** Stable per-step ID derived from text hash, prefixed by run slug to prevent cross-run state bleed.
**When to use:** Any browser-persisted UI state that must survive page reload but be scoped per artefact.
**Example:**
```javascript
// In _HTML_TEMPLATE script block
function renderNextSteps() {{
  const steps = REPORT.next_steps || [];
  const slug = REPORT.meta.brief_slug || "default";
  const container = document.getElementById("nextStepsContent");
  if (!steps.length) {{ container.innerHTML = "<p>No checklist available.</p>"; return; }}
  container.innerHTML = "<ol>" + steps.map(s => {{
    const storageKey = `gar_${{slug}}_step_${{s.id}}`;
    const checked = localStorage.getItem(storageKey) === "1" ? "checked" : "";
    return `<li>
      <input type="checkbox" id="cb_${{s.id}}" data-key="${{storageKey}}" ${{checked}}>
      <label for="cb_${{s.id}}">${{htmlEscape(s.text)}}</label>
    </li>`;
  }}).join("") + "</ol>";
  container.querySelectorAll('input[type="checkbox"]').forEach(cb => {{
    cb.addEventListener("change", e => {{
      localStorage.setItem(e.target.dataset.key, e.target.checked ? "1" : "0");
    }});
  }});
}}
```

### Anti-Patterns to Avoid

- **Hardcoded step numbers in template strings** (e.g., `"Step 8: Review compliance flags..."`): defeats CMPL-05 reorder logic — step numbers must always be derived from final list position.
- **Three separate scripts (`export_positives.py` / `export_negatives.py` / `export_ad_groups.py`):** triples I/O, triples test surface, triples SKILL.md steps. Single script + single test file is the project convention (mirror `bid_suggest.py`).
- **`encoding="utf-8-sig"` on CSV writes:** silently writes a BOM and corrupts Editor import on Windows. Use plain `"utf-8"`.
- **`open(..., newline="\n")` or default newline:** Python translates `\n` to OS-default newlines unless `newline=""` — produces `\r\n\n` (double endings) on Windows. ALWAYS `newline=""` + explicit `lineterminator="\r\n"` on the writer.
- **Writing CSVs to `run_dir` root:** clutters the run folder and breaks the "exports[] are paths" contract that expects an `export/` prefix. Always `mkdir(parents=True, exist_ok=True)` on the subfolder.
- **Mutating `report.md` section order for compliance:** the section reorder is Phase 9's job (CMPL-03 ⚠ block above Ranked Keywords) and already done. Phase 10 reorders ONLY the Next-Steps numbered list, never moves other sections.
- **localStorage keys without slug namespace:** progress for run A bleeds into run B. ALWAYS prefix with `gar_{run_slug}_`.
- **Generating step IDs from index:** index changes when CMPL-05 reorders, breaking saved localStorage progress on re-render. Use SHA-1 hash of step TEXT — stable across renumber.
- **Rendering Next-Steps as a separate sidecar JSON file:** adds plumbing, adds a CLI invocation, adds a SKILL.md step. All inputs already live in `render_report.py`'s `main()`. Don't sidecar what already integrates.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RFC 4180 CSV quoting (commas/quotes/newlines in keyword strings) | Manual `",".join()` with quote handling | `csv.DictWriter` with `quoting=csv.QUOTE_MINIMAL` | "buy 1, get 1 free near me" needs proper quoting. csv module is bulletproof; rolling your own silently corrupts edge cases. |
| Cross-platform line endings | `os.linesep` or string-replace | `newline=""` + `lineterminator="\r\n"` | Python's I/O layer translates `\n` to platform default unless `newline=""`. Mixing layers gives `\r\n\n` on Windows. |
| UTF-8 detection / BOM stripping for round-trip tests | Manual `bytes_read[:3] == b"\xef\xbb\xbf"` checks AND `decode("utf-8-sig")` shenanigans | Write with plain `"utf-8"` + assert `bytes_read[:3] != b"\xef\xbb\xbf"` once | Never write a BOM in the first place; round-trip with `csv.DictReader` and plain UTF-8 — Editor consumes plain UTF-8. |
| Slug-stable step IDs | UUID4 per render | `hashlib.sha1(text)[:8]` | UUID4 is non-deterministic — localStorage state breaks on re-render. Hash of text is stable across reruns AND across CMPL-05 reorder (text is unchanged; only position is). |
| HTML escaping for `<input>` labels | Manual replacement | Existing `_html_escape()` helper at `render_report.py:846` | Already handles `& < > "`. Reuse — don't re-derive. |
| USD micros → display string | Inline `f"${m/1_000_000:.2f}"` per call site | Existing `_micros_to_usd()` at `render_report.py:142` | Single conversion boundary (Pitfall 8 invariant from Phase 9). Reuse. Note: that helper returns `"—"` for None; the CSV `Max CPC` column needs `"0.00"` for None instead — wrap a thin `_micros_to_csv_usd()` helper. |
| Section integration into report.md | Brand-new section-ordering logic | Append to existing `sections` list in `render_full_report()` at L746 | Order matters for operator UX. Next-Steps goes LAST (after Ranked Keywords) so the operator scrolls to it after reviewing the data. Export Files section can go IMMEDIATELY before Next-Steps so the file list is right above the instructions that consume it. |

**Key insight:** Everything Phase 10 needs to compute has already been computed by Phases 6 (negatives), 9 (forecast, compliance, suggested_max_cpc_micros), and the brief intake (location, language, audience). Phase 10 is pure assembly + presentation. Don't reach for new computational power; reach for the cleanest possible pass-through.

## Common Pitfalls

### Pitfall 1: BOM corruption on Windows-saved CSV
**What goes wrong:** File saves with `\xef\xbb\xbf` prefix; Google Ads Editor's first column header becomes `﻿Campaign` and import fails with "Required column missing: Campaign."
**Why it happens:** Using `encoding="utf-8-sig"` (writes BOM), or letting Excel re-save the file. Python doesn't write a BOM with plain `"utf-8"`, but `csv.DictReader` round-trip tests should affirm the bytes still don't have one.
**How to avoid:** Open with `encoding="utf-8"` (NOT `"utf-8-sig"`). Add a byte-level test asserting `read_bytes()[:3] != b"\xef\xbb\xbf"`.
**Warning signs:** Editor error "Required column missing: <first header>" on import; hex-dump of CSV shows `EF BB BF` at byte 0.

### Pitfall 2: Doubled line endings on Windows
**What goes wrong:** CSV has `\r\n\n` between rows; Editor reads phantom empty rows or fails with "Invalid keyword: (empty)".
**Why it happens:** Opening file in text mode with default `newline=None` translates `\n` → `\r\n` on write; if you ALSO set `lineterminator="\r\n"` on the writer, you get `\r\n\n` (writer writes `\r\n`, then I/O layer expands the trailing `\n` to `\r\n` again).
**How to avoid:** ALWAYS `open(path, "w", encoding="utf-8", newline="")` (empty string disables I/O-layer translation) + `csv.DictWriter(f, ..., lineterminator="\r\n")` (writer emits the CRLF). Both required together.
**Warning signs:** `len(file.read().split(b"\r\n"))` != number of rows + 1; phantom empty rows in Editor.

### Pitfall 3: Compliance reorder mutates `report.md` section order
**What goes wrong:** Plan author confuses CMPL-03 (Phase 9 ⚠ block above Ranked Keywords) with CMPL-05 (Phase 10 Next-Steps list reorder) and re-shuffles markdown sections.
**Why it happens:** Both are "compliance reorders" semantically; one is section-level (already done in Phase 9), the other is list-item level (Phase 10 scope).
**How to avoid:** CMPL-05 ONLY reorders the ordered list inside the `## Next Steps` section. The `## ⚠ Compliance Required` blockquote already sits above Ranked Keywords from Phase 9 and stays put. Plan and tests must assert section order is unchanged.
**Warning signs:** `report.md` diff after Phase 10 shows the ⚠ block moved or duplicated.

### Pitfall 4: Empty negatives.json crashes the CSV writer
**What goes wrong:** `negatives.json` is an empty list (e.g., test brief produced no negatives); `negatives.csv` is never written or crashes with `KeyError: 'tier'`.
**Why it happens:** Defensive code assumes ≥ 1 row; iterates `negatives[0]` for header derivation.
**How to avoid:** Header list is a module-level constant (`NEGATIVES_HEADERS`), not derived from data. Iteration over zero rows just writes the header line + EOF — that's a valid empty CSV. Test fixture: `negatives_empty.json = []`.
**Warning signs:** "Required column missing" on a successful Editor import on the standard run; non-zero exit code on a known-empty fixture.

### Pitfall 5: Match type case mismatch breaks Editor import
**What goes wrong:** CSV writes `phrase` (lowercase, from internal Python); Editor rejects with "Invalid match type."
**Why it happens:** Internal taxonomy is lowercase (`phrase` / `exact` / `broad`); Editor expects title-case (`Phrase` / `Exact` / `Broad`).
**How to avoid:** Single `MATCH_TYPE_TITLECASE` dict at top of `export_csv.py`; apply at the CSV write boundary only. Defensive on unknown values: `MATCH_TYPE_TITLECASE.get(raw, "Phrase")` — defaults to Phrase per project convention (RANK-03).
**Warning signs:** Editor import error "Invalid match type" or silent assignment of "Broad" as fallback.

### Pitfall 6: Ad Group naming drift from clusters.json
**What goes wrong:** Plan author massages cluster names (lowercases, hyphenates, title-cases) before writing to CSV; report.md and CSV no longer agree.
**Why it happens:** "Make it look nicer" instinct. Phase 4's cluster names are intentionally `theme_intent` snake_case so they're paste-ready as Ad Group labels.
**How to avoid:** Pass cluster names VERBATIM. Test: assert exact string equality between `clusters.json[i].name` and `ad_groups.csv` row `Ad Group` cell.
**Warning signs:** Ad Group column doesn't match cluster section in report.md; operator sees two different names for the same group.

### Pitfall 7: localStorage state bleed across runs
**What goes wrong:** Operator opens report.html for run A, checks 4 steps. Opens report.html for run B; the same 4 checkboxes appear checked. Cross-run contamination.
**Why it happens:** Step IDs are derived from text alone — two runs with identical step texts collide on localStorage keys.
**How to avoid:** Always namespace key as `gar_{run_slug}_step_{id}`. `run_slug` is in `REPORT.meta.brief_slug`. Test: render two HTML reports for two run slugs; assert generated localStorage keys differ.
**Warning signs:** Checkboxes persist between runs in browser dev tools localStorage inspector.

### Pitfall 8: Compliance reorder with 0 verticals still adds extra step
**What goes wrong:** Render function unconditionally adds a placeholder "Step 1: Complete verification at ..." even when `matched_verticals == []`, leaving a broken "..." in the operator's checklist.
**Why it happens:** Defensive `or "<vertical>"` fallback inside the prepend logic without an outer `if`.
**How to avoid:** Outer `if matched_verticals:` guard. Empty array → standard 8-step order, no prepend. Test both fixtures: `compliance_with_match.json` and `compliance_empty.json`.
**Warning signs:** Step 1 reads "Complete <vertical> verification at <URL>" with literal angle-brackets in a non-compliance run.

### Pitfall 9: Final URL column gets the brief slug or run dir accidentally
**What goes wrong:** Plan author "helpfully" fills Final URL with the run slug or some derived URL, which is wrong.
**Why it happens:** brief.md has no website-URL field; an empty cell feels wrong; author guesses.
**How to avoid:** Empty string per row (`""`). Document the v1.2 deferral in the rubric. Editor accepts empty Final URL (operator pastes the URL during import).
**Warning signs:** Editor imports keywords pointing at nonsensical URLs; operator has to nuke 73 rows.

### Pitfall 10: Default Max CPC = 0.00 looks broken to operator
**What goes wrong:** A cluster with all-null `suggested_max_cpc_micros` (Phase 9 BIDS-02 `no_cpc_data` path) renders as `0.00` in `ad_groups.csv`. Operator sees $0 budget and assumes the file is broken.
**Why it happens:** Editor rejects empty numeric cells; 0.00 is the safe escape. But "0.00" reads as "broken" without context.
**How to avoid:** Document in the operator rubric and in report.md "How to use this CSV" copy: "Ad groups showing $0.00 had no CPC data from Ahrefs — set manually in Editor before enabling." Optional: add a `_no_cpc_data` companion column? — no, breaks header contract. Just document.
**Warning signs:** Operator support question "why is my budget $0?"; Phase 10 verification has to clarify this.

## Code Examples

Verified patterns from this codebase and Python stdlib docs (HIGH confidence — pulled from existing project sources):

### CSV writer with strict CRLF + no BOM (stdlib `csv`)
```python
# Source: https://docs.python.org/3/library/csv.html#csv.DictWriter
# + project convention: open() args mirror render_report.py:1629 (utf-8 + newline)
import csv
from pathlib import Path

POSITIVES_HEADERS = ["Campaign", "Ad Group", "Keyword", "Match Type", "Max CPC", "Final URL"]

def write_positives(path: Path, rows: list[dict]) -> None:
    """Write positives.csv (EXPT-01)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=POSITIVES_HEADERS,
            lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)
```

### Round-trip read-back assertion (EXPT-04)
```python
# In test_export_csv.py
def test_positives_round_trip_no_bom_crlf(tmp_run_dir, ranked_with_cpc, clusters_phase9):
    """EXPT-04: bytes have no BOM, CRLF endings, csv.DictReader round-trips identically."""
    from export_csv import write_positives_from_run
    write_positives_from_run(tmp_run_dir, ranked_with_cpc, clusters_phase9)

    path = tmp_run_dir / "export" / "positives.csv"
    raw = path.read_bytes()

    # No BOM
    assert raw[:3] != b"\xef\xbb\xbf", f"BOM detected: {raw[:8]!r}"
    # CRLF endings present
    assert b"\r\n" in raw, "no CRLF found"
    # Each row terminated with CRLF (no bare \n)
    text = raw.decode("utf-8")
    assert "\n" not in text.replace("\r\n", ""), "bare \\n found in output"

    # Round-trip: DictReader produces dicts with the exact header set
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == POSITIVES_HEADERS
        rows = list(reader)
    assert len(rows) > 0
```

### Empty negatives.json → header-only CSV
```python
# In export_csv.py
def write_negatives(path: Path, negatives: list[dict]) -> None:
    """Write negatives.csv. Empty list → header-only file (still a valid empty CSV)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=NEGATIVES_HEADERS,
            lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for neg in negatives:
            tier = neg.get("tier", "Investigate")
            level = TIER_TO_LEVEL.get(tier, "ad_group")
            mt_raw = (neg.get("match_type") or "phrase").lower()
            writer.writerow({
                "Campaign": campaign_name,
                "Ad Group": "" if level == "campaign" else neg.get("cluster", ""),
                "Keyword": neg["keyword"],
                "Match Type": MATCH_TYPE_TITLECASE.get(mt_raw, "Phrase"),
                "Level": level,
            })
```

### Compliance-aware checklist reorder (CMPL-05)
```python
# See "Pattern 2" above for the full helper. Key invariant:
#   1. matched_verticals empty → standard 8-step order, step 1 is "Create campaign…"
#   2. matched_verticals non-empty → ONE combined verification step (not N), prepended
#      as new step 1, others renumbered 2..9 by position in the final list
# Numbering is ALWAYS derived from list index — never hardcoded.
```

### Reusing existing render_report.py helpers
```python
# Source: render_report.py:142 (_micros_to_usd) + L676 (_parse_brief_fields)
#   + L693 (_derive_brief_slug) + L846 (_html_escape)
# Phase 10 must reuse these — do not redefine.
from render_report import (
    _parse_brief_fields,      # brief.md → {industry, product, location, language, audience}
    _derive_brief_slug,       # run_dir → human-readable slug
    _micros_to_usd,           # int micros → "$X.XX" (returns "—" for None — wrap for CSV)
    _html_escape,             # HTML-safe escaping (already covers & < > ")
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual paste from `report.md` keyword tables into Google Ads UI | Editor-importable CSV (EXPT-01..05) | v1.1 | Operator goes from ~30 min hand-copy to <5 min Editor paste. Phase 10 is the deliverable. |
| Single fat Phase 9 with all v1.1 reqs | Phase 9 (data layer) + Phase 10 (output layer) split | ROADMAP.md decision 2026-05-14 | Each phase's success criteria observable in isolation; ~5-7 plans per phase rather than ~13. |
| `report.md` ends at "Negative Keywords" | `report.md` ends at "Next Steps" with ordered checklist | Phase 10 | Operator's last view is action-oriented, not data-oriented. |
| No persistent UI state | HTML checkboxes with localStorage progress | Phase 10 STEP-03 | Multi-session ops where operator returns mid-launch keeps progress. |

**Deprecated/outdated within this project:**
- `report.json["compliance"]` is a top-level array of matched_verticals[] (Phase 9 CMPL-04) — Phase 10 reads it directly, does NOT re-load `compliance-flags.json`.
- `forecast.json` sidecar is the source of truth; `report.json["forecast"]` is its mirror — Phase 10 SHOULD prefer `report.json["forecast"]["campaign_totals"]["daily_spend_mid_usd"]` for STEP-02 substitution, falling back to the sidecar only if render-time forecast was None.

## Open Questions

1. **What "Status" value does the Editor expect in `ad_groups.csv`?**
   - What we know: The Editor accepts `Enabled` / `Paused` / `Removed` for ad group status, case-insensitively per Google Ads policy norms.
   - What's unclear: Whether the column header is `Status` or `Ad Group Status` exactly. Google Ads Editor docs are inconsistent — see [CSV file columns](https://support.google.com/google-ads/editor/answer/57747).
   - Recommendation: Header literal `Status` per the orchestrator's locked decision. Value `Enabled` per row (lowercase fallback `enabled` if Editor is case-insensitive — defensible either way). MEDIUM confidence; the planner should add a manual smoke test of an actual Editor import in Wave 3 (human-verify task).

2. **Should `positives.csv` Match Type be set per-keyword or fixed per ad group?**
   - What we know: REQUIREMENTS.md / RANK-03 sets match_type per-keyword on `ranked-enriched.json`. Editor supports per-keyword Match Type in the same column.
   - What's unclear: Some Editor templates fix Match Type at the ad-group level. The phase brief is unambiguous — per-keyword wins.
   - Recommendation: Per-keyword via `ranked-enriched.json[i].match_type`, title-cased. HIGH confidence in the recommendation; MEDIUM confidence the Editor parses it correctly (mitigation: Wave 3 manual import smoke).

3. **Should the Next-Steps `command` field be auto-generated for any step?**
   - What we know: STEP-03 says "copy-able command snippets" — implies some steps have terminal commands.
   - What's unclear: Which steps actually have commands. "Create campaign in UK" is a UI action, not a CLI command. The only plausible commands are `cat {run_dir}/export/positives.csv` style file-inspection helpers.
   - Recommendation: Wave 1 plan: skip auto-generated commands in v1 (steps have only `text` + `id`). Add `command` field only if a specific step naturally has one (e.g., `cat negatives.csv | head`). LOW confidence; defer to plan-time decision after Wave 0.

4. **Campaign name source — slug vs `<industry> - <product>` vs operator-prompted?**
   - What we know: Brief slug is already derived (`_derive_brief_slug(run_dir)`); it's stable, run-keyed, and shown to operator.
   - What's unclear: Whether operators want the verbose "Online Groceries - Same Day Delivery UK" Campaign name or the terser "Same Day Grocery Delivery UK" slug.
   - Recommendation: Slug, title-cased, with hyphens kept (e.g., `Same-Day Grocery Delivery UK`). Document. v1.2 brief field can override.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.3 (per scripts/pyproject.toml dev deps) |
| Config file | `.claude/skills/google-ad-research/scripts/pyproject.toml` `[tool.pytest.ini_options]` with `testpaths = ["tests"]` |
| Quick run command | `uv run --project .claude/skills/google-ad-research/scripts --with pytest pytest .claude/skills/google-ad-research/scripts/tests/test_export_csv.py .claude/skills/google-ad-research/scripts/tests/test_render_report.py -x` |
| Full suite command | `uv run --project .claude/skills/google-ad-research/scripts --with pytest pytest .claude/skills/google-ad-research/scripts/tests/ -x` |
| Per-task commit | quick run command above |
| Per-wave merge | full suite command above |
| Phase gate | full suite green + manual Editor import smoke on a real run-folder |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXPT-01 | `positives.csv` exists at `{run_dir}/export/positives.csv` with exact headers and per-keyword rows | unit | `pytest tests/test_export_csv.py::test_positives_headers_and_rows -x` | ❌ Wave 0 |
| EXPT-01 | Max CPC column formatted as `f"${X:.2f}"` from `suggested_max_cpc_micros` (or `0.00` for None) | unit | `pytest tests/test_export_csv.py::test_positives_max_cpc_format -x` | ❌ Wave 0 |
| EXPT-01 | Match Type title-cased at write boundary (`phrase` → `Phrase`) | unit | `pytest tests/test_export_csv.py::test_positives_match_type_titlecase -x` | ❌ Wave 0 |
| EXPT-02 | `negatives.csv` Level column maps Strong→campaign, Considered→ad_group, Investigate→ad_group | unit | `pytest tests/test_export_csv.py::test_negatives_level_mapping -x` | ❌ Wave 0 |
| EXPT-02 | Empty `negatives.json` produces header-only CSV (no crash, no missing file) | unit | `pytest tests/test_export_csv.py::test_negatives_empty_input -x` | ❌ Wave 0 |
| EXPT-03 | `ad_groups.csv` has one row per cluster with `Status=Enabled` and Default Max CPC from cluster-median suggested CPC | unit | `pytest tests/test_export_csv.py::test_ad_groups_one_row_per_cluster -x` | ❌ Wave 0 |
| EXPT-03 | Cluster with all-null suggested CPC renders `0.00` (not blank, not crash) | unit | `pytest tests/test_export_csv.py::test_ad_groups_zero_cpc_for_no_data -x` | ❌ Wave 0 |
| EXPT-04 | All three CSVs: no BOM (bytes[0:3] != b"\xef\xbb\xbf") | unit | `pytest tests/test_export_csv.py::test_all_csvs_no_bom -x` | ❌ Wave 0 |
| EXPT-04 | All three CSVs: CRLF line endings (no bare `\n`) | unit | `pytest tests/test_export_csv.py::test_all_csvs_crlf -x` | ❌ Wave 0 |
| EXPT-04 | All three CSVs: `csv.DictReader` round-trip parses fieldnames matching project headers | unit | `pytest tests/test_export_csv.py::test_all_csvs_round_trip -x` | ❌ Wave 0 |
| EXPT-04 | Exit code 0 on a known-good run folder; 3 on missing inputs; 2 on disk error | unit | `pytest tests/test_export_csv.py::test_exit_codes -x` | ❌ Wave 0 |
| EXPT-05 | `report.md` contains `## Export Files` section linking each CSV with relative path | unit | `pytest tests/test_render_report.py::test_export_files_section -x` | ✅ (extend existing) |
| EXPT-05 | `report.json["exports"]` is a list of strings matching `["export/positives.csv", "export/negatives.csv", "export/ad_groups.csv"]` | unit | `pytest tests/test_render_report.py::test_report_json_exports_array -x` | ✅ (extend existing) |
| STEP-01 | `report.md` ends with `## Next Steps` section containing an ordered list (8 items absent compliance) | unit | `pytest tests/test_render_report.py::test_next_steps_section_default_order -x` | ✅ (extend existing) |
| STEP-02 | Step 1 contains brief's location + language; step 2 contains `f"${daily_spend_mid:.2f}"`; step 3 contains all cluster names | unit | `pytest tests/test_render_report.py::test_next_steps_substitution -x` | ✅ (extend existing) |
| STEP-03 | `report.html` contains `<section id="next-steps">` with `<input type="checkbox">` per step and inline JS reading `REPORT.next_steps` | unit | `pytest tests/test_render_report.py::test_next_steps_html_checkboxes -x` | ✅ (extend existing) |
| STEP-03 | localStorage keys namespaced as `gar_{slug}_step_{id}` (assert via grep on HTML string) | unit | `pytest tests/test_render_report.py::test_next_steps_localstorage_namespacing -x` | ✅ (extend existing) |
| STEP-04 | `report.json["next_steps"]` is a list of dicts each with `n` (int), `text` (str), `id` (str of length 8) | unit | `pytest tests/test_render_report.py::test_report_json_next_steps_array -x` | ✅ (extend existing) |
| CMPL-05 | Compliance present → step 1 contains all matched vertical names and verification URLs; standard step 1 ("Create campaign…") is now step 2 | unit | `pytest tests/test_render_report.py::test_next_steps_compliance_reorder -x` | ✅ (extend existing) |
| CMPL-05 | Compliance present with 2 verticals → ONE combined step (not 2 separate steps) | unit | `pytest tests/test_render_report.py::test_next_steps_compliance_combined_step -x` | ✅ (extend existing) |
| CMPL-05 | Compliance empty → standard 8-step order, no verification step | unit | `pytest tests/test_render_report.py::test_next_steps_no_compliance_standard_order -x` | ✅ (extend existing) |
| CMPL-05 | Section order in report.md unchanged (⚠ block still above Ranked Keywords) | integration | `pytest tests/test_render_report.py::test_section_order_invariant -x` | ✅ (already exists from Phase 9) |
| Integration | End-to-end: run `export_csv.py` then `render_report.py` on a fixture run-folder; assert all 3 CSVs + report.md Export Files + report.json next_steps/exports populated | integration | `pytest tests/test_render_report.py::test_phase10_e2e_on_fixture_run -x` | ❌ Wave 2 |
| Manual | Open `{run_dir}/export/positives.csv` in Google Ads Editor on a real OS; verify clean import | manual-only | human-verify in Wave 3 (justified — Editor is a desktop app; cannot script the import without Selenium-style automation, which dwarfs the gain) | n/a |

### Sampling Rate
- **Per task commit:** quick run command (target files only) — < 5 sec
- **Per wave merge:** full suite command — runs all ~150 tests, < 30 sec
- **Phase gate:** Full suite green + manual Editor import smoke before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `scripts/tests/test_export_csv.py` — new file; covers EXPT-01..04
- [ ] `scripts/tests/fixtures/negatives_phase10.json` — Strong+Considered+Investigate row mix
- [ ] `scripts/tests/fixtures/negatives_empty.json` — empty list for empty-input test
- [ ] `scripts/tests/fixtures/compliance_with_match.json` — 1+ matched_verticals[] for CMPL-05 reorder
- [ ] `scripts/tests/fixtures/compliance_two_verticals.json` — 2 matched verticals for combined-step test
- [ ] `scripts/tests/fixtures/compliance_empty.json` — empty matched_verticals[] for standard-order test
- [ ] `scripts/tests/fixtures/forecast_phase10.json` — minimal forecast.json with `campaign_totals.daily_spend_mid_usd` populated
- [ ] `scripts/tests/test_render_report.py` extension — add ~10 new test functions for Next-Steps + Export Files + JSON additions (existing file — don't create new)
- [ ] `export_csv.py` MODULE_MISSING stub (pattern from `bid_suggest.py`) so test imports collect cleanly during RED state
- [ ] No framework install needed — pytest already in dev deps

## Sources

### Primary (HIGH confidence)
- **Project source (HIGH):** `.claude/skills/google-ad-research/scripts/bid_suggest.py` — PEP 723 + module-level config-block + atomic-write pattern that Phase 10 `export_csv.py` mirrors.
- **Project source (HIGH):** `.claude/skills/google-ad-research/scripts/forecast_budget.py` — frozenset assertion + methodology block + USD-conversion-only-at-display-boundary pattern.
- **Project source (HIGH):** `.claude/skills/google-ad-research/scripts/compliance_check.py` — load_verticals + word-boundary regex + atomic .tmp rename pattern.
- **Project source (HIGH):** `.claude/skills/google-ad-research/scripts/render_report.py` (1646 lines) — existing `render_full_report()` + `build_report_json()` signature + section-order list + HTML template + helper functions (`_parse_brief_fields`, `_derive_brief_slug`, `_micros_to_usd`, `_html_escape`).
- **Project source (HIGH):** `.claude/skills/google-ad-research/references/phase9-economics-compliance.md` — downstream-contract section explicitly names `suggested_max_cpc_micros`, `forecast.campaign_totals.daily_spend_mid_usd`, and `matched_verticals[].verification_url` as Phase 10 inputs.
- **Project source (HIGH):** `.planning/REQUIREMENTS.md` — verbatim EXPT-01..05 + STEP-01..04 + CMPL-05 contracts.
- **Project source (HIGH):** `.planning/STATE.md` — Phase 9 outcomes (BIDS+FRCS+CMPL-01..04 complete; CMPL-05 deferred to Phase 10) + decisions log.
- **Project source (HIGH):** `.planning/ROADMAP.md` — Phase 10 success criteria verbatim (5 criteria).
- **Project source (HIGH):** `.planning/phases/09-campaign-economics-and-compliance/09-VERIFICATION.md` — Phase 9 contract verified, including CMPL-05 deferred-to-Phase-10 note.
- **Python stdlib docs (HIGH):** [`csv` module](https://docs.python.org/3/library/csv.html) — `DictWriter`, `QUOTE_MINIMAL`, `lineterminator` semantics.
- **Python stdlib docs (HIGH):** [`open()` `newline` parameter](https://docs.python.org/3/library/functions.html#open) — empty string disables newline translation, required for CRLF control.

### Secondary (MEDIUM confidence)
- **Google Ads Editor Help (MEDIUM):** [CSV file columns](https://support.google.com/google-ads/editor/answer/57747) — confirms Campaign / Ad Group / Keyword / Type columns and Negative-vs-Campaign-negative semantics.
- **Google Ads Editor Help (MEDIUM):** [Prepare a CSV file](https://support.google.com/google-ads/editor/answer/56368) — UTF-8 encoding required; CRLF/BOM specifics not explicitly stated.
- **Google Ads Editor Help (MEDIUM):** [Import a CSV file](https://support.google.com/google-ads/editor/answer/30564) — import flow + column-mapping UI affordance.

### Tertiary (LOW confidence)
- **WebSearch result (LOW — needs validation):** Whether Editor accepts lowercase `phrase` / `exact` / `broad` or strictly title-case `Phrase` / `Exact` / `Broad`. Recommendation: title-case (defensive). Wave 3 manual smoke validates.
- **WebSearch result (LOW):** Whether the Status column header is `Status` or `Ad Group Status` for `ad_groups.csv`. Recommendation: `Status` per orchestrator's locked decision. Wave 3 manual smoke validates.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure stdlib, established in-project patterns from Phase 9; zero new deps.
- Architecture: HIGH — directly mirrors `bid_suggest.py` / `forecast_budget.py` / `compliance_check.py` shape; extending an existing `render_report.py` whose pattern (`render_*_section()` helpers + section list + optional kwargs in `build_report_json()`) is well-established.
- Pitfalls: HIGH — BOM/CRLF/encoding pitfalls are standard Python CSV gotchas with deterministic mitigations; compliance-reorder pitfalls are local to this project but exhaustively traced through Phase 9 source.
- Editor-specific format details: MEDIUM — Match Type case and Status column header are documented inconsistently across Google's help pages; manual Wave 3 smoke is the planned final validator.

**Research date:** 2026-05-14
**Valid until:** 2026-06-14 (stable — stdlib + existing project patterns; Editor v2.x format is multi-year stable per its support docs)
