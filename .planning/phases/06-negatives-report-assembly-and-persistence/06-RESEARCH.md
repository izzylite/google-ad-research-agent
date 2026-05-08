# Phase 6: Negatives, Report Assembly, and Persistence - Research

**Researched:** 2026-05-08
**Domain:** Python report rendering, negative keyword generation, run persistence
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NEGT-01 | Negatives in three tiers: Strong, Considered, Investigate | Tiered schema + LLM prompt pattern in Architecture Patterns |
| NEGT-02 | Each negative tagged with category (6 types) + per-keyword justification | Category enum + negatives.json schema defined below |
| NEGT-03 | Negatives deduplicated against final positive keyword pool (ranked.json) | `dedupe_negatives()` helper pattern; set intersection against ranked keywords |
| RPRT-01 | `render_report.py` writes `report.md` with four sections + "How to read this" | Script pattern; tabulate 0.9.0 for tables; section structure defined |
| RPRT-02 | `report.json` twin with stable canonical schema | Schema defined verbatim; `"version": "v1"` field for future migration |
| RPRT-03 | "How to read this" section explaining signal_count != volume | Verbatim boilerplate text specified in Code Examples |
| RPRT-04 | Markdown sanitization on all table cells | `escape_md_cell()` in lib/io.py; escapes pipes, normalizes quotes, strips newlines |
| RPRT-05 | All raw per-stage API responses persisted to `raw/` subfolder | Already satisfied by Phases 1-5; Phase 6 persists negatives.json to raw/ |
| PRST-01 | Each run is isolated dated folder: brief.md, report.md, report.json, raw/ | Run folder contract from Phase 1; render_report.py writes final two files |
| PRST-02 | `.runs/INDEX.md` lists past runs (date, slug, status) | `update_index.py` append-only pattern defined |
</phase_requirements>

---

## Summary

Phase 6 is the integration phase: it consumes all upstream JSON artifacts (ranked.json, clusters.json, raw/competitor-intel.json, brief.md) and produces the two operator-facing deliverables (report.md, report.json) plus a persistent run index. It introduces no new API calls — all work is deterministic Python I/O plus one LLM step (negative keyword generation via the skill prompt).

Three new scripts are needed: `generate_negatives.py` does NOT call the LLM itself — instead the skill prompt (Step 21) generates negatives as a structured JSON blob and the operator writes it; `generate_negatives.py` is a validator/deduplicator that takes the LLM-produced negatives.json and enforces enum correctness + dedup against ranked.json. `render_report.py` reads all synthesis JSONs and writes report.md + report.json. `update_index.py` appends one row to .runs/INDEX.md.

The biggest risk in this phase is markdown escaping (Pitfall 18) — competitor ad copy frequently contains literal pipes and smart quotes. The mitigation is `escape_md_cell()` added to lib/io.py and tested in isolation before being used in report rendering.

**Primary recommendation:** LLM generates negatives via skill prompt (Step 21) as a structured JSON array; Python validates (enum + dedup) and rejects invalid entries before render. Pure-Python render_report.py with tabulate 0.9.0 for keyword tables; manual string building for cluster and competitor sections where content is prose-heavy.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tabulate` | 0.9.0 | Ranked keyword table rendering | Already chosen in project research; `tablefmt="github"` produces GFM tables; zero transitive deps |
| `python-dotenv` | 1.0.x | Config loading (already present) | Already in pyproject.toml; lib/config.py wraps it |
| `python-slugify` | 8.0.x | Slug derivation for INDEX.md (already present) | Already in pyproject.toml |

All Phase 6 scripts are **stdlib-only except tabulate** for report rendering. `generate_negatives.py` and `update_index.py` need zero new deps (stdlib pathlib + json + re).

### PEP 723 Header for render_report.py
```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "tabulate>=0.9.0",
#     "python-dotenv>=1.0",
# ]
# ///
```

`generate_negatives.py` and `update_index.py` use `dependencies = []` — stdlib-only.

**Installation (add to pyproject.toml):**
```bash
# pyproject.toml dependencies += "tabulate>=0.9.0"
```

---

## Architecture Patterns

### Script Boundaries

| Script | Inputs | Outputs | LLM? |
|--------|--------|---------|------|
| Skill prompt Step 21 | brief.md + ranked.json themes | negatives.json (LLM writes via Write tool) | YES |
| `generate_negatives.py` | negatives.json (LLM-written) + ranked.json | validated negatives.json (overwrites) | NO |
| `render_report.py` | ranked.json, clusters.json, raw/competitor-intel.json, negatives.json, brief.md | report.md + report.json | NO |
| `update_index.py` | run_dir (reads brief.md for slug+industry) | .runs/INDEX.md (append) | NO |

### Recommended Project Structure (additions)
```
scripts/
├── generate_negatives.py   # validator + deduplicator (NEW)
├── render_report.py        # report.md + report.json renderer (NEW)
├── update_index.py         # .runs/INDEX.md append (NEW)
├── lib/
│   └── io.py               # ADD: escape_md_cell() here
tests/
├── test_negatives.py       # NEW (Wave 0 RED stubs)
├── test_render_report.py   # NEW (Wave 0 RED stubs)
references/
└── phase6-negatives-report.md  # SKILL.md progressive-disclosure rubric
```

### Pattern 1: Negatives Schema (negatives.json)

LLM writes this file in Step 21; `generate_negatives.py` validates and overwrites it.

```json
[
  {
    "keyword": "grocery delivery jobs",
    "tier": "Strong",
    "category": "jobs-careers",
    "justification": "Contains 'jobs' — recruitment intent, never converts for delivery service"
  },
  {
    "keyword": "free grocery delivery",
    "tier": "Considered",
    "category": "free-DIY-tutorial",
    "justification": "Free-seeking modifier; exclude for premium positioning; keep if brand offers free trial"
  },
  {
    "keyword": "diy meal delivery",
    "tier": "Investigate",
    "category": "free-DIY-tutorial",
    "justification": "DIY framing implies self-service; low conversion probability but not zero"
  }
]
```

**Valid tiers:** `Strong` | `Considered` | `Investigate`

**Valid categories:** `jobs-careers` | `free-DIY-tutorial` | `used-refurb-wholesale` | `competitor-brand` | `wrong-geo` | `wrong-audience`

### Pattern 2: generate_negatives.py — Validator

```python
VALID_TIERS = frozenset({"Strong", "Considered", "Investigate"})
VALID_CATEGORIES = frozenset({
    "jobs-careers", "free-DIY-tutorial", "used-refurb-wholesale",
    "competitor-brand", "wrong-geo", "wrong-audience",
})

def validate_negatives(negatives: list[dict]) -> tuple[list[dict], list[dict]]:
    """Returns (valid_rows, error_rows). Checks tier + category enums."""
    valid, errors = [], []
    for row in negatives:
        if row.get("tier") not in VALID_TIERS:
            errors.append({**row, "error": f"invalid tier: {row.get('tier')!r}"})
        elif row.get("category") not in VALID_CATEGORIES:
            errors.append({**row, "error": f"invalid category: {row.get('category')!r}"})
        else:
            valid.append(row)
    return valid, errors


def dedupe_negatives(negatives: list[dict], ranked: list[dict]) -> tuple[list[dict], list[str]]:
    """Remove negatives whose keyword appears in the positive pool.

    Args:
        negatives: Validated negative rows.
        ranked: Rows from ranked.json (positive keyword pool).

    Returns:
        (deduped_negatives, collisions) where collisions is a list of keywords removed.
    """
    positive_keywords = {row["keyword"].lower().strip() for row in ranked}
    deduped, collisions = [], []
    for neg in negatives:
        kw = neg["keyword"].lower().strip()
        if kw in positive_keywords:
            collisions.append(neg["keyword"])
        else:
            deduped.append(neg)
    return deduped, collisions
```

Exit codes: `0` ok | `1` warnings (enum errors fixed, collisions removed — surfaced to operator) | `3` fatal (negatives.json missing or unparseable)

### Pattern 3: escape_md_cell() — Add to lib/io.py

```python
import re

_SMART_QUOTE_MAP = str.maketrans({
    "‘": "'", "’": "'",   # left/right single
    "“": '"', "”": '"',   # left/right double
    "–": "-", "—": "-",   # en/em dash
})

def escape_md_cell(s: str, *, max_len: int = 120) -> str:
    """Sanitize a string for safe use in a GFM markdown table cell.

    Operations (in order):
    1. Normalize smart quotes and dashes to ASCII equivalents.
    2. Replace literal newlines/carriage returns with a single space.
    3. Escape pipe characters as \\|.
    4. Truncate to max_len with ellipsis if needed.
    """
    if not isinstance(s, str):
        s = str(s)
    s = s.translate(_SMART_QUOTE_MAP)
    s = re.sub(r"[\r\n]+", " ", s)
    s = s.replace("|", r"\|")
    if len(s) > max_len:
        s = s[:max_len - 1] + "…"
    return s
```

**All table cell content** in render_report.py must pass through `escape_md_cell()`. No raw string from upstream JSON goes directly into a markdown table row.

### Pattern 4: render_report.py — Section Structure

```python
from tabulate import tabulate

def render_keyword_table(ranked: list[dict], top_n: int = 100) -> str:
    rows = [
        [
            escape_md_cell(r["keyword"]),
            r["intent"],
            r["match_type"],
            str(r["signal_count"]),
            str(r["source_diversity"]),
            str(r["score"]),
        ]
        for r in ranked[:top_n]
    ]
    headers = ["Keyword", "Intent", "Match Type", "Signals", "Src Div", "Score"]
    return tabulate(rows, headers=headers, tablefmt="github")
```

Section order in report.md:
1. Header (run path, date, brief slug, `generated_at`)
2. "How to read this" disclaimer
3. Ranked Keyword Table (top 100, configurable)
4. Ad Group Clusters (one `###` subsection per cluster, keyword list as bullet points)
5. Competitor Ad Copy (one `###` subsection per cluster, ads as sub-bullets; value props if available)
6. Negative Keywords (three `###` subsections: Strong / Considered / Investigate; bullets grouped by category within each tier)

### Pattern 5: report.json Canonical Schema

```json
{
  "meta": {
    "run_id": "2026-05-08T143024Z-grocery-delivery-uk",
    "brief_slug": "grocery-delivery-uk",
    "generated_at": "2026-05-08T14:30:24Z",
    "version": "v1"
  },
  "brief": {
    "industry": "online groceries",
    "product": "same-day grocery delivery",
    "location": "UK",
    "language": "en-GB",
    "audience": "households 25-45 in metro areas"
  },
  "keywords": [
    {
      "keyword": "order groceries uk",
      "intent": "transactional",
      "match_type": "exact",
      "signal_count": 3,
      "source_diversity": 4,
      "sources": ["serper-organic", "serper-paa", "tavily", "serper-related"],
      "score": 325,
      "cluster_id": "same_day_delivery_transactional"
    }
  ],
  "clusters": [
    {
      "name": "same_day_delivery_transactional",
      "intent": "transactional",
      "keywords": [{"keyword": "order same day grocery delivery", "score": 95}]
    }
  ],
  "competitor_intel": {
    "metadata": {"generated_at": "...", "clusters_input": "clusters.json"},
    "clusters": {}
  },
  "negatives": [
    {
      "keyword": "grocery delivery jobs",
      "tier": "Strong",
      "category": "jobs-careers",
      "justification": "..."
    }
  ]
}
```

**Stability rule:** Never rename or remove top-level keys in v1. Add new keys only. `"version": "v1"` enables migration detection in future run-diff tooling (PRST-02 prerequisite for v2 TOOL-03).

`cluster_id` in each keyword row (report.json only — not in ranked.json) is derived by looking up which cluster contains that keyword. This is the only field added to keywords at render time.

### Pattern 6: update_index.py

```python
# Reads: run_dir/brief.md (for industry), run_dir name (for date + slug)
# Writes: .runs/INDEX.md (appends one row)

INDEX_HEADER = """# Run History

| Date | Slug | Industry | Status |
|------|------|----------|--------|
"""

def append_run_to_index(runs_root: Path, run_dir: Path, industry: str, status: str = "complete") -> None:
    index_path = runs_root / "INDEX.md"
    # Parse date and slug from run_dir.name: "2026-05-08T143024Z-grocery-delivery-uk"
    name = run_dir.name
    date = name[:10]               # "2026-05-08"
    slug = name[18:] if len(name) > 18 else name  # strip timestamp prefix
    row = f"| {date} | {slug} | {escape_md_cell(industry)} | {status} |\n"
    if not index_path.exists():
        index_path.write_text(INDEX_HEADER + row, encoding="utf-8")
    else:
        with index_path.open("a", encoding="utf-8") as f:
            f.write(row)
```

INDEX.md lives at `.runs/INDEX.md` (sibling to run folders, not inside them). It is the only cross-run mutable file in the system — all other writes are run-isolated (PRST-01).

### Anti-Patterns to Avoid

- **Do not call the LLM from generate_negatives.py.** The script is a validator only. LLM work stays in the skill prompt (Step 21). This maintains the skill-orchestrates / scripts-validate boundary established in Phases 1-5.
- **Do not write report.md using raw f-strings for table cells.** Always route through `escape_md_cell()` + tabulate. Even columns that look safe (keyword, theme) can contain pipes if an operator's product name includes one.
- **Do not mutate ranked.json.** The `cluster_id` enrichment lives only in report.json — ranked.json is a stable upstream artifact read by multiple scripts.
- **Do not append to INDEX.md with a read-modify-write pattern.** Open in append mode (`"a"`) to avoid race conditions on rapid re-runs.
- **Do not persist negatives.json to run_dir root.** Write to `run_dir/raw/negatives.json` (raw/ is the home for all machine-generated stage outputs). `negatives.json` in run_dir root would be ambiguous with report-level outputs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown table formatting | Custom f-string column alignment | `tabulate` 0.9.0 `tablefmt="github"` | Column width math, pipe alignment, header separator all handled; hand-rolled breaks with multi-byte chars |
| Smart quote normalization | Regex over `‘..”` | `str.translate()` with a static char map | One-pass O(n), no regex backtracking, covers all four curly-quote variants + dashes in a single call |
| Slug parsing from run_dir.name | Re-derive from brief fields | Parse `run_dir.name` directly (already canonical) | run_init.py derives the name from the brief; parsing it back avoids round-trip divergence |

---

## Common Pitfalls

### Pitfall 15: Over-aggressive negatives (from PITFALLS.md)
**What goes wrong:** Strong negatives include brand positioning words (e.g., `cheap` negated for a value-tier brand) — blocks converting traffic.
**How to avoid:** Tier split enforces review discipline. Strong = unconditional blockers (jobs/careers/wikipedia). Considered = brand-positioning-dependent. Investigate = needs operator review before adding. LLM prompt must read brief positioning before generating Considered-tier negatives.
**Warning signs:** Negatives list contains words from the brief's USP (e.g., "fast", "same-day", "affordable").

### Pitfall 16: Missing obvious negatives (from PITFALLS.md)
**What goes wrong:** LLM focuses on "interesting" patterns; forgets `jobs`, `salary`, `wikipedia`.
**How to avoid:** Inject a baseline checklist into the Step 21 skill prompt. The prompt must output at least one row per category. `generate_negatives.py` warns if any of the 6 categories has zero representatives.
**Baseline always-check triggers:** `job|jobs|career|careers|salary|internship|hiring` → jobs-careers. `free|diy|tutorial|how.to|guide|pdf|download` → free-DIY-tutorial. `used|second.hand|refurb|wholesale|bulk` → used-refurb-wholesale.

### Pitfall 18: Markdown escaping (from PITFALLS.md)
**What goes wrong:** Ad copy like "Free Delivery | Same Day | Order Now" breaks the GFM table row.
**How to avoid:** `escape_md_cell()` in lib/io.py applied to every cell before tabulate call. Test with a fixture containing a literal pipe in a title field.
**Warning signs:** `test_escape_md_cell_pipe` test fails; table renders with extra columns.

### Pitfall 22: Run comparability (from PITFALLS.md)
**What goes wrong:** Future run-diff tooling cannot compare March and May reports because report.json schema changed.
**How to avoid:** `"version": "v1"` in meta block. Never rename existing keys. Document schema changes in CHANGELOG comment inside render_report.py. The planner must not add new top-level keys without bumping the version in a future phase.

### Pitfall: INDEX.md header written on every run
**What goes wrong:** `update_index.py` writes the header row every time, producing duplicate headers in INDEX.md.
**How to avoid:** Check `index_path.exists()` before writing header. If file exists, append row only.

---

## Code Examples

### escape_md_cell with tabulate integration
```python
# Source: lib/io.py (new function) + render_report.py
from tabulate import tabulate
from lib.io import escape_md_cell

def render_keyword_table(ranked: list[dict], top_n: int = 100) -> str:
    rows = [
        [
            escape_md_cell(r["keyword"]),
            escape_md_cell(r["intent"]),
            r["match_type"],
            str(r["signal_count"]),
            str(r["source_diversity"]),
            str(r["score"]),
        ]
        for r in ranked[:top_n]
    ]
    return tabulate(
        rows,
        headers=["Keyword", "Intent", "Match Type", "Signals", "Src Div", "Score"],
        tablefmt="github",
    )
```

### "How to read this" boilerplate (verbatim — RPRT-03)
```python
HOW_TO_READ = """\
## How to Read This Report

**signal_count** is the number of source-data fragments that mentioned this keyword.
It is NOT search volume. Do not treat a higher signal_count as "more searches per month."

**source_diversity** is the number of distinct signal sources (WebSearch, Serper organic,
Serper PAA, Serper related, Tavily) that surfaced the keyword. Higher diversity = more
reliable signal. The ranking is primarily sorted by source_diversity.

To estimate actual search volume, paste the keyword list into Google Keyword Planner.
"""
```

### Negatives section rendering
```python
TIER_ORDER = ["Strong", "Considered", "Investigate"]
TIER_DESCRIPTIONS = {
    "Strong": "Add to all campaigns unconditionally.",
    "Considered": "Add if brand is premium-positioned; review before adding for value-tier brands.",
    "Investigate": "Needs operator review — may be valid traffic depending on campaign goal.",
}

def render_negatives_section(negatives: list[dict]) -> str:
    by_tier: dict[str, list[dict]] = {t: [] for t in TIER_ORDER}
    for neg in negatives:
        tier = neg.get("tier", "Investigate")
        if tier in by_tier:
            by_tier[tier].append(neg)

    parts = ["## Negative Keywords\n"]
    for tier in TIER_ORDER:
        items = by_tier[tier]
        parts.append(f"\n### {tier} Negatives\n_{TIER_DESCRIPTIONS[tier]}_\n")
        if not items:
            parts.append("_None suggested for this tier._\n")
            continue
        # Group by category within tier
        by_cat: dict[str, list[dict]] = {}
        for neg in items:
            by_cat.setdefault(neg["category"], []).append(neg)
        for cat, cat_items in sorted(by_cat.items()):
            parts.append(f"\n**{cat}**\n")
            for neg in cat_items:
                kw = escape_md_cell(neg["keyword"])
                just = escape_md_cell(neg.get("justification", ""))
                parts.append(f"- `{kw}` — {just}\n")
    return "".join(parts)
```

### CLI skeleton for render_report.py
```python
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()
    run_dir = args.run_dir

    # Load all inputs — exit 3 on any missing required file
    required = ["ranked.json", "clusters.json", "negatives.json", "brief.md"]
    for name in required:
        if not (run_dir / name).exists():
            print(f"ERROR: {name} not found in {run_dir}", file=sys.stderr)
            return 3

    ranked = json.loads((run_dir / "ranked.json").read_text(encoding="utf-8"))
    clusters_data = json.loads((run_dir / "clusters.json").read_text(encoding="utf-8"))
    negatives = json.loads((run_dir / "negatives.json").read_text(encoding="utf-8"))
    brief_text = (run_dir / "brief.md").read_text(encoding="utf-8")

    # Competitor intel is optional (may not have competitor URLs)
    ci_path = run_dir / "raw" / "competitor-intel.json"
    competitor_intel = json.loads(ci_path.read_text(encoding="utf-8")) if ci_path.exists() else {}

    # Render sections
    report_md = render_full_report(ranked, clusters_data, competitor_intel, negatives,
                                   brief_text, run_dir, top_n=args.top_n)
    report_json = build_report_json(ranked, clusters_data, competitor_intel, negatives,
                                    brief_text, run_dir)

    (run_dir / "report.md").write_text(report_md, encoding="utf-8", newline="\n")
    (run_dir / "report.json").write_text(
        json.dumps(report_json, indent=2), encoding="utf-8", newline="\n"
    )
    print(json.dumps({"report_md": str(run_dir / "report.md"),
                      "report_json": str(run_dir / "report.json"),
                      "keywords_in_report": len(ranked)}))
    return 0
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Flat negatives list (one tier) | Three-tier system (Strong/Considered/Investigate) | Prevents operator blanket-pasting; forces review of Considered/Investigate |
| Markdown-only output | report.md + report.json twin | JSON enables future run-diff (TOOL-03 v2); JSON is machine-readable for campaign automation |
| No run history | .runs/INDEX.md | Operator can audit past work without `ls`-ing dated folders |

---

## SKILL.md Step Additions (Steps 21-26)

The planner must add these steps to SKILL.md (or to `references/phase6-negatives-report.md` if the 500-line budget is tight):

| Step | Action | Gate |
|------|--------|------|
| 21 | LLM reads ranked.json themes + brief positioning; generates negatives as JSON array (3 tiers, 6 categories, justification per row); writes to `{run_dir}/negatives.json` via Write tool | negatives.json exists with ≥ 1 entry per tier |
| 22 | `uv run generate_negatives.py --run-dir {run_dir}` validates + deduplicates; surfaces collisions and enum errors to operator | exit 0 or operator accepts exit 1 |
| 23 | `uv run render_report.py --run-dir {run_dir}` writes report.md + report.json | both files exist |
| 24 | `uv run update_index.py --run-dir {run_dir}` appends row to .runs/INDEX.md | INDEX.md updated |
| 25 | Operator reviews report.md in chat (Read tool); confirm sections present | operator confirms |
| 26 | Final summary to operator: run path, report path, keyword count, cluster count, negative count; hard STOP | STOP — skill workflow complete |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | `scripts/pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| Quick run command | `uv run --project scripts/ -m pytest scripts/tests/test_negatives.py scripts/tests/test_render_report.py -x` |
| Full suite command | `uv run --project scripts/ -m pytest scripts/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NEGT-01 | negatives.json has exactly 3 tiers | unit | `pytest tests/test_negatives.py::test_three_tiers_present -x` | Wave 0 |
| NEGT-02 | each negative has valid category + justification | unit | `pytest tests/test_negatives.py::test_category_enum_valid -x` | Wave 0 |
| NEGT-03 | positive-negative collision removed | unit | `pytest tests/test_negatives.py::test_dedupe_removes_collision -x` | Wave 0 |
| RPRT-01 | report.md contains all four section headings | integration | `pytest tests/test_render_report.py::test_report_md_sections -x` | Wave 0 |
| RPRT-02 | report.json has all top-level schema keys | unit | `pytest tests/test_render_report.py::test_report_json_schema -x` | Wave 0 |
| RPRT-03 | "How to read this" block present in report.md | unit | `pytest tests/test_render_report.py::test_how_to_read_present -x` | Wave 0 |
| RPRT-04 | escape_md_cell escapes pipes, smart quotes, newlines | unit | `pytest tests/test_negatives.py::test_escape_md_cell_pipe -x` | Wave 0 |
| RPRT-05 | raw/ subfolder contains upstream API responses | smoke | manual inspection (already validated by Phases 1-5 tests) | existing |
| PRST-01 | run folder contains brief.md + report.md + report.json + raw/ | integration | `pytest tests/test_render_report.py::test_run_folder_complete -x` | Wave 0 |
| PRST-02 | INDEX.md row appended with correct date+slug | unit | `pytest tests/test_render_report.py::test_index_append -x` | Wave 0 |

### Test Patterns (consistent with Phases 2-5)

**Module-missing guard** (same pattern as all prior phases):
```python
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import generate_negatives  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="generate_negatives.py not yet implemented")
```

**Key unit tests for `escape_md_cell`** — importable from lib.io (no module guard needed once added):
```python
def test_escape_md_cell_pipe():
    from lib.io import escape_md_cell
    assert escape_md_cell("Free Delivery | Same Day") == r"Free Delivery \| Same Day"

def test_escape_md_cell_smart_quotes():
    from lib.io import escape_md_cell
    assert escape_md_cell("“Best”") == '"Best"'

def test_escape_md_cell_newline():
    from lib.io import escape_md_cell
    assert "\n" not in escape_md_cell("line1\nline2")

def test_escape_md_cell_truncates():
    from lib.io import escape_md_cell
    long = "x" * 200
    result = escape_md_cell(long, max_len=120)
    assert len(result) <= 120
    assert result.endswith("…")
```

**Key integration test for report.md structure:**
```python
def test_report_md_sections(tmp_run_dir, ranked_fixture, clusters_fixture,
                             competitor_intel_fixture, negatives_fixture, brief_fixture):
    from render_report import render_full_report
    md = render_full_report(ranked_fixture, clusters_fixture, competitor_intel_fixture,
                            negatives_fixture, brief_fixture, tmp_run_dir)
    assert "## How to Read This Report" in md
    assert "signal_count" in md          # disclaimer uses exact column name
    assert "## Ranked Keywords" in md
    assert "## Ad Group Clusters" in md
    assert "## Competitor Ad Copy" in md
    assert "## Negative Keywords" in md
    assert "### Strong Negatives" in md
    assert "### Considered Negatives" in md
    assert "### Investigate Negatives" in md
```

### Sampling Rate

- **Per task commit:** `uv run --project scripts/ -m pytest scripts/tests/test_negatives.py scripts/tests/test_render_report.py -x`
- **Per wave merge:** `uv run --project scripts/ -m pytest scripts/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `scripts/tests/test_negatives.py` — covers NEGT-01, NEGT-02, NEGT-03, RPRT-04 (escape_md_cell); 8 test functions, all skipping via MODULE_MISSING guard
- [ ] `scripts/tests/test_render_report.py` — covers RPRT-01, RPRT-02, RPRT-03, PRST-01, PRST-02; 6 test functions, all skipping via MODULE_MISSING guard
- [ ] `scripts/tests/fixtures/negatives_valid.json` — 6 rows across 3 tiers and all 6 categories
- [ ] `scripts/tests/fixtures/negatives_with_collision.json` — includes one keyword present in ranked_phase3.json (for dedupe test)
- [ ] `tabulate>=0.9.0` added to `scripts/pyproject.toml` dependencies

---

## Sources

### Primary (HIGH confidence)
- Project PITFALLS.md (pitfalls 15, 16, 18, 22) — directly maps to this phase's design decisions
- Project SUMMARY.md / STACK.md — tabulate 0.9.0 chosen; confirmed in planning research
- Existing scripts (rank_keywords.py, validate_clusters.py, competitor_intel.py) — confirmed data shapes for ranked.json, clusters.json, competitor-intel.json
- lib/io.py current source — confirmed `escape_md_cell()` does not yet exist; needs adding
- pyproject.toml — confirmed `tabulate` is not yet a declared dependency (must add)

### Secondary (MEDIUM confidence)
- tabulate PyPI 0.9.0 — `tablefmt="github"` produces GFM pipe tables; confirmed in STACK.md research
- Python str.translate() docs — O(n) char map approach for smart quote normalization; standard library, stable API

### Tertiary (LOW confidence — needs operator validation)
- Baseline negatives checklist (jobs/careers/free/DIY etc.) — synthesized from Pitfall 16 guidance; tune against first real run
- Negative count per run (30-50 expected) — extrapolated from Pitfall 15 warning sign (">30 negatives is a red flag for over-negating")

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tabulate already project-chosen; all other deps in pyproject.toml
- Architecture: HIGH — script boundary pattern established by Phases 1-5; no new external dependencies
- Pitfalls: HIGH — directly derived from project PITFALLS.md pitfalls 15, 16, 18, 22

**Research date:** 2026-05-08
**Valid until:** 2026-08-08 (stable domain — tabulate/stdlib; no fast-moving APIs)
