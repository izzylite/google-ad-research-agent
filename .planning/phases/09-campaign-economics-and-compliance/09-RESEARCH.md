# Phase 9: Campaign Economics and Compliance — Research

**Researched:** 2026-05-14
**Domain:** Pure-compute sidecars (Python, stdlib + existing lib/) that extend `ranked-enriched.json` and add two new JSON sidecars + new report sections.
**Confidence:** HIGH — phase is a pure consumer of existing v1.0 artifacts; no new external APIs; patterns are well-established by Phases 6, 7, 8.

## Summary

Phase 9 enriches v1.0 artifacts (`ranked-enriched.json`, `clusters.json`, `brief.md`) with three economic + compliance overlays — none of which require new network calls or new library dependencies. The bulk of the engineering risk is **integration**: keeping `render_report.py` from becoming an integration choke point, keeping `ranked-enriched.json` schema additive (not mutating), and keeping tuning knobs out of code (BIDS-04 + CMPL-02).

The Phase 8 pattern is the right template — sidecar JSON files (`forecast.json`, `compliance-flags.json`) that `render_report.py` auto-detects and gracefully degrades when absent, mirroring how `niche-pulse.json` / `account-perf.json` / `negatives-sync.json` already work. Three independent compute scripts (`bid_suggest.py`, `forecast_budget.py`, `compliance_check.py`) means Wave 1 parallelizes cleanly and a failure in one does not block the other two.

**Primary recommendation:** Implement Phase 9 as **three independent Python scripts plus render_report.py extension**, with `bid_suggest.py` running after `volume_enrich.py` and writing back to `ranked-enriched.json` in-place (additive new field only). `forecast_budget.py` and `compliance_check.py` write their own sidecar JSONs. Use the Phase 8 module-missing pytest guard pattern for Wave 0 RED tests. Extract Phase 9 step rubric to `references/phase9-economics-compliance.md` to keep SKILL.md under 500 lines.

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md was authored for Phase 9 — there is no `/gsd:discuss-phase` artifact in the phase folder. Constraints are inherited from:

### Locked Decisions (inherited from REQUIREMENTS.md v1.1 + ROADMAP Phase 9)

- **Bid multipliers are fixed at the values in BIDS-01:** transactional 1.2, commercial 0.8, informational 0.4, navigational 1.0. They must live in a single config block at the top of `bid_suggest.py` (BIDS-04). Operator tunes by editing one constant; no Python edit elsewhere.
- **CTR anchors are fixed at the values in FRCS-02:** transactional 6%, commercial 4%, informational 2%, navigational 8%. Documented in script header; configurable via the same config-block pattern as bid multipliers.
- **Avg-CPC ratio is fixed at FRCS-03:** `suggested_max_cpc × 0.65 = avg_cpc`. Low/mid/high bands at ×0.5 / ×1.0 / ×1.5. Mid is the operator-facing default.
- **Cluster-median fallback (BIDS-02):** keywords with no Ahrefs `cpc_micros` use the median CPC of their cluster's siblings × intent multiplier. If the cluster has zero CPC data at all, `suggested_max_cpc_micros = null` and the keyword is flagged `no_cpc_data` in the report.
- **Compliance token lists live in `references/compliance-verticals.json` (CMPL-02):** data, not code. Operator extends without Python edit. Each vertical entry has `tokens[]`, `verification_url`, `policy_note`, and (recommended) `name`.
- **Five verticals at v1 (PROJECT decision row 162):** medical, legal, finance, gambling, crypto. Operator can extend.
- **Schema additivity:** `ranked-enriched.json` gains `suggested_max_cpc_micros` per row. `report.json` gains `compliance[]` array. New sidecars: `forecast.json`, `compliance-flags.json`. No backward-incompatible mutations.
- **Skill is filesystem-only.** No new external APIs in Phase 9 — all compute is local against existing run-folder JSON.
- **`uv run` + PEP 723 inline metadata (CLAUDE.md).** Never `pip install`. Each new script declares its own `# /// script` block.
- **`.env` contract intact.** Phase 9 reads no secrets — pure compute on local JSON.
- **Run-folder isolation.** All Phase 9 output lands in the same `.runs/<ISO>-<slug>/` folder. No cross-run state.

### Claude's Discretion

- **Script placement of bid_suggest logic:** extend `volume_enrich.py` (one-pass enrichment) OR create separate `bid_suggest.py` reading/writing `ranked-enriched.json`. Recommendation in this RESEARCH.md: **separate script** (matches v1.0 separate-concern convention and lets bid logic be retested without re-firing Ahrefs).
- **Top-N value for compliance token matching:** how many top-ranked keywords does `compliance_check.py` scan against tokens (in addition to brief.md). Recommendation: **top 50** (covers high-signal keywords without false-positive flooding).
- **`forecast.json` schema details:** field names, nesting style — research recommends a `{metadata, clusters[], campaign_totals, methodology}` shape (detailed in §"forecast.json Schema" below).
- **SKILL.md step numbering:** Phase 9 steps will land at Steps 36-40 (Phase 8 ends at Step 35). Reference file recommended for full rubric (Phase 5/6/7/8 precedent).
- **Whether compliance scan reads `ranked-enriched.json` or `ranked.json`:** prefer `ranked-enriched.json` since Phase 9 strictly depends on it (Phase 8 already ran). Falls back to `ranked.json` if enriched not present — same defensive pattern render_report.py uses.

### Deferred Ideas (OUT OF SCOPE for Phase 9)

- Editor CSV export (EXPT-01..05) — **Phase 10**.
- Operator Next-Steps checklist (STEP-01..04) — **Phase 10**. Phase 9 must NOT write `## Next Steps` section — it belongs to Phase 10.
- Full Google Ads policy engine — v1 ships a token-match + verification-URL pointer, not a policy verdict. Operator confirms policy compliance externally.
- Multi-locale token lists — `compliance-verticals.json` is en-language only at v1; non-English vertical tokens deferred.
- Dynamic CTR / avg-CPC from real Ahrefs SERP data — v1 uses fixed anchors. Calibration after first 3 v1.1 runs (STATE open questions row 161).
- Per-cluster bid bands (low/mid/high max-CPC per cluster) — v1 emits single suggested_max_cpc_micros per keyword. Cluster-level bid bands are out of scope; budget bands are at cluster level instead.
- Real-time Google Ads forecast tool integration — explicitly out of scope per FRCS-05 ("not Google's official forecast tool").
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BIDS-01 | `bid_suggest.py` adds `suggested_max_cpc_micros` to ranked-enriched.json via `cpc_micros × intent_multiplier` | See "bid_suggest.py logic" section + "Cluster-median fallback algorithm" |
| BIDS-02 | Fall back to cluster-median CPC × multiplier; null + flag `no_cpc_data` when no data | See "Cluster-median fallback algorithm" (handles orphans, empty clusters) |
| BIDS-03 | Report shows `Suggested Max CPC` column (USD); HTML tooltip on hover shows multiplier | See "render_report.py extension points" — extends render_enriched_keyword_table |
| BIDS-04 | Multipliers in single config block at top of `bid_suggest.py` | Pattern: module-level `INTENT_MULTIPLIERS = {...}` dict + frozenset assertion |
| FRCS-01 | `forecast_budget.py` emits forecast.json with per-cluster + campaign-level click + spend bands | See "forecast.json Schema" + "Aggregation algorithm" |
| FRCS-02 | Click = volume × intent-CTR (T=6%, C=4%, I=2%, N=8%); configurable in script header | Pattern: module-level `INTENT_CTRS = {...}` mirrors BIDS-04 |
| FRCS-03 | Avg-CPC = suggested_max_cpc × 0.65; bands = ×0.5 / ×1.0 / ×1.5 | See "forecast.json Schema" — bands applied at aggregation, not per-keyword |
| FRCS-04 | Report renders Budget Forecast section per cluster + campaign totals | See "render_report.py extension points" — new section between Clusters and Negatives |
| FRCS-05 | "How this is calculated" subsection naming CTR + avg-CPC assumptions | See "Methodology section pattern" — copy assumptions from script config block |
| CMPL-01 | `compliance_check.py` scans ranked-enriched.json + brief.md against vertical token lists; emits compliance-flags.json | See "Token matching algorithm" |
| CMPL-02 | Token lists in `references/compliance-verticals.json` (data, not code); `{tokens[], verification_url, policy_note}` per vertical | See "compliance-verticals.json structure" |
| CMPL-03 | "⚠ Compliance Required" block above Ranked Keywords table; HTML warning-yellow; MD blockquote with ⚠ prefix | See "render_report.py extension points" — section positioning matters |
| CMPL-04 | `report.json` gains `compliance[]` array; `build_report_json` signature extends with `compliance` kwarg | See "build_report_json signature changes" |
| CMPL-05 | Next-Steps checklist reorders compliance step to step 1 when flags present | **Out of Phase 9 scope** — STEP-01 is Phase 10. Phase 9 emits the data; Phase 10 consumes it. Document this contract clearly to the planner. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`json`, `statistics`, `pathlib`, `argparse`) | 3.11+ | All Phase 9 logic | Phase 9 is pure compute; no new deps |
| `statistics.median` | stdlib | Cluster-median CPC fallback (BIDS-02) | Standard, handles even-count case correctly (mean of two middles); no numpy/pandas needed |
| `tabulate` >= 0.9.0 | already in pyproject.toml | New report.md tables (forecast, suggested CPC column) | Already used by render_report.py — `tablefmt="github"` |
| `python-dotenv` >= 1.0 | already declared | Only if compliance_check.py needs to read .env config (it doesn't — pure file IO) | Loaded once by Phase 1; Phase 9 inherits — no new use case |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` >= 9.0.3 | already in dev deps | Unit tests for all three new scripts | Phase 9 testing pattern; no respx needed (no HTTP) |
| `lib.io.escape_md_cell` | existing project module | Sanitize all new markdown cells (forecast cluster names, compliance evidence tokens) | Mandatory for any cell that surfaces user / external text (RPRT-04 contract) |
| `lib.log.configure_logger` | existing project module | Structured logging in all three scripts | Phase 8 precedent — every script calls `log = configure_logger()` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `statistics.median` | numpy.median | numpy adds ~30MB dep for one function — rejected; same skill-portability argument that killed sentence-transformers |
| Extend `volume_enrich.py` to compute bids | Separate `bid_suggest.py` | Extension keeps one pass but couples Ahrefs to bid logic; separate script lets operator retune bids without re-firing Ahrefs (~$0.05 per Phase 8 run). **Recommend separate script.** |
| Mutate ranked-enriched.json in place | Write `ranked-bid.json` sidecar | In-place mutation simpler and matches "ranked-enriched.json gains suggested_max_cpc_micros field" requirement language. Sidecar adds a third filename to track. **Recommend in-place additive mutation.** Phase 8 also writes `ranked-enriched.json` once; bid_suggest reads + writes the same file. |
| Regex for token matching | Substring (case-insensitive, word-boundary-aware) | Regex is overkill for short token list; substring with `\b` boundary is enough. **Recommend** `re.search(r"\b" + re.escape(token) + r"\b", text, re.IGNORECASE)` per token. |

**Installation:** No new packages — all scripts use existing project deps via inline PEP 723 metadata. Example header for `bid_suggest.py`:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
```

`forecast_budget.py` and `compliance_check.py` are also stdlib-only.

## Architecture Patterns

### Recommended Project Structure

```
.claude/skills/google-ad-research/
├── scripts/
│   ├── bid_suggest.py             # NEW — reads + writes ranked-enriched.json (additive)
│   ├── forecast_budget.py         # NEW — writes forecast.json sidecar
│   ├── compliance_check.py        # NEW — writes compliance-flags.json sidecar
│   ├── render_report.py           # MODIFIED — new sections + new kwargs
│   ├── volume_enrich.py           # UNCHANGED (BIDS lives in its own script)
│   └── tests/
│       ├── test_bid_suggest.py    # NEW
│       ├── test_forecast_budget.py # NEW
│       ├── test_compliance_check.py # NEW
│       ├── test_render_report.py  # MODIFIED — adds forecast + compliance assertions
│       └── fixtures/
│           ├── ranked_with_cpc.json    # NEW
│           ├── ranked_no_cpc.json      # NEW
│           ├── ranked_partial_cpc.json # NEW (some keywords have CPC, some don't)
│           ├── clusters_phase9.json    # NEW (mirrors clusters.json shape)
│           ├── brief_medical.md        # NEW
│           ├── brief_legal.md          # NEW
│           ├── brief_neutral.md        # NEW (no regulated tokens)
│           ├── compliance_verticals_phase9.json # NEW (test-isolated copy)
│           ├── forecast_expected.json  # NEW (golden file)
│           └── compliance_expected.json # NEW (golden file)
└── references/
    ├── phase9-economics-compliance.md  # NEW — SKILL.md step rubric
    └── compliance-verticals.json       # NEW — operator-editable token data
```

### Pattern 1: Sidecar JSON with Graceful Degradation
**What:** Each Phase 9 script writes a JSON sidecar to `run_dir`. `render_report.py` auto-detects each via `Path.exists()` and gracefully degrades to no-section / pass-through when absent.

**When to use:** Every Phase 9 output. Matches Phase 7 (`niche-pulse.json`) and Phase 8 (`account-perf.json`, `negatives-sync.json`) patterns verbatim.

**Example (from render_report.py lines 1273-1297):**

```python
# Sidecar load pattern — copy verbatim for forecast + compliance
forecast: dict | None = None
forecast_path = run_dir / "forecast.json"
if forecast_path.exists():
    try:
        forecast = json.loads(forecast_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        forecast = None

compliance: dict | None = None
compliance_path = run_dir / "compliance-flags.json"
if compliance_path.exists():
    try:
        compliance = json.loads(compliance_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        compliance = None

# Both default to None — sections render empty / skip when absent
```

### Pattern 2: Module-Level Config Block (BIDS-04, FRCS-02)
**What:** Tuning knobs (multipliers, CTRs, avg-CPC ratio) declared as a `dict` at the top of the script, immediately after imports. **No magic numbers anywhere else.**

**When to use:** Any value the operator might tune. Single block per script.

**Example pattern (apply to `bid_suggest.py`):**

```python
# bid_suggest.py
"""bid_suggest.py — Add suggested_max_cpc_micros to ranked-enriched.json.

Tuning knobs below. Edit in one place; nothing else in the file uses
literal multipliers. (BIDS-04)
"""
from __future__ import annotations

# --- Tuning knobs (BIDS-04) ---
INTENT_MULTIPLIERS: dict[str, float] = {
    "transactional": 1.2,
    "commercial":    0.8,
    "informational": 0.4,
    "navigational":  1.0,
}

# Sanity check: keys must match the 4-class rubric exactly
_REQUIRED_INTENTS = frozenset({"transactional", "commercial", "informational", "navigational"})
assert frozenset(INTENT_MULTIPLIERS) == _REQUIRED_INTENTS, (
    f"INTENT_MULTIPLIERS keys must match 4-class rubric: {_REQUIRED_INTENTS}"
)
```

Same pattern for `forecast_budget.py`:

```python
# forecast_budget.py
INTENT_CTRS: dict[str, float] = {
    "transactional": 0.06,
    "commercial":    0.04,
    "informational": 0.02,
    "navigational":  0.08,
}
AVG_CPC_RATIO: float = 0.65          # avg_cpc = max_cpc × this
BAND_MULTIPLIERS: dict[str, float] = {"low": 0.5, "mid": 1.0, "high": 1.5}
```

### Pattern 3: Reference JSON for Data-Driven Lists (CMPL-02)
**What:** Operator-tunable lists ship as JSON in `references/`, loaded at script start. Never coded into Python.

**When to use:** Any list the operator may extend without redeploying.

**Example structure for `references/compliance-verticals.json`:**

```json
{
  "$schema_version": "v1",
  "generated_at": "2026-05-14",
  "verticals": [
    {
      "name": "medical",
      "tokens": [
        "doctor", "physician", "clinic", "hospital", "patient",
        "medical", "medicine", "prescription", "diagnosis", "treatment",
        "surgery", "therapy", "pharmaceutical", "rx", "telehealth",
        "mental health", "rehab"
      ],
      "verification_url": "https://support.google.com/adspolicy/answer/176031",
      "policy_note": "Healthcare advertisers may require LegitScript certification or country-specific licensing. Verify before launching."
    },
    {
      "name": "legal",
      "tokens": [
        "lawyer", "attorney", "law firm", "legal", "litigation",
        "lawsuit", "injury attorney", "dui", "personal injury",
        "class action", "settlement"
      ],
      "verification_url": "https://support.google.com/adspolicy/answer/2464998",
      "policy_note": "Legal services subject to lawyer-advertising rules in most jurisdictions."
    },
    {
      "name": "finance",
      "tokens": [
        "loan", "mortgage", "credit", "credit card", "personal loan",
        "payday", "installment loan", "consumer credit", "bnpl",
        "buy now pay later", "broker", "trading", "forex", "cfd",
        "investment", "wealth management", "robo-advisor"
      ],
      "verification_url": "https://support.google.com/adspolicy/answer/2464998",
      "policy_note": "Financial services verification expanded April 2026 — 14 new jurisdictions, vertical-specific KYC for loans, BNPL."
    },
    {
      "name": "gambling",
      "tokens": [
        "casino", "betting", "sportsbook", "gambling", "poker",
        "slots", "lottery", "wager", "bingo", "online casino",
        "fantasy sports", "prediction market"
      ],
      "verification_url": "https://support.google.com/adspolicy/answer/176019",
      "policy_note": "Gambling + games policy update March 2026 adds account-health eligibility. Prediction Markets US only with CFTC DCM authorization."
    },
    {
      "name": "crypto",
      "tokens": [
        "crypto", "cryptocurrency", "bitcoin", "btc", "ethereum",
        "eth", "blockchain", "nft", "defi", "stablecoin",
        "crypto wallet", "crypto exchange", "web3", "token sale", "ico"
      ],
      "verification_url": "https://support.google.com/adspolicy/answer/9870661",
      "policy_note": "Crypto exchange + wallet ads expanded to Indonesia (OJK licence) Feb 2026. US still requires FinCEN MSB + state licensure."
    }
  ]
}
```

(Verification URLs verified via Google Ads Policy Help Center — see Sources. These are stable URLs as of May 2026.)

### Pattern 4: Module-Missing Pytest Guard (Wave 0 RED)
**What:** Wave 0 commits failing tests that import the not-yet-written module behind a try/except that turns ImportError into `pytest.skip`. Wave 1 implements the module — tests automatically flip RED→GREEN.

**When to use:** Every new Phase 9 script. Established by Phases 2-8.

**Example (test_bid_suggest.py header):**

```python
import pytest

try:
    from bid_suggest import (
        compute_suggested_cpc,
        cluster_median_cpc,
        enrich_with_bids,
        main_with_args,
    )
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="bid_suggest.py not yet implemented")
```

### Anti-Patterns to Avoid

- **Hand-coding multipliers/CTRs scattered throughout the script** — violates BIDS-04 / FRCS-02. One config block at top, asserted complete.
- **Coding token lists in Python** — violates CMPL-02. Always load from JSON.
- **Writing `## Next Steps` section in render_report.py during Phase 9** — that's Phase 10 (STEP-01). Phase 9 emits the data; Phase 10 consumes it.
- **Mutating `ranked.json`** — never. Phase 8 wrote `ranked-enriched.json` precisely so the original ranking stays auditable. Phase 9 mutates `ranked-enriched.json` (additive only — new field, never removes existing field).
- **Coupling forecast to bid_suggest's import** — `forecast_budget.py` reads `ranked-enriched.json` after bid_suggest has run; it does NOT import bid_suggest. Decoupled scripts, ordered by skill prompt.
- **Hard-coding Ahrefs field names** — the field is `cpc_micros` (set by `volume_enrich.py` line 139). Read defensively: `row.get("cpc_micros")` — never KeyError.
- **Mutating clusters.json** — Phase 9 reads it but does not write it. forecast.json carries derived data.
- **Failing the whole render when one sidecar is missing** — render_report.py must gracefully degrade per Pattern 1 above.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Median of numeric list | Custom sort-and-pick | `statistics.median` | Handles even/odd count correctly; numpy not needed |
| Case-insensitive substring with word boundary | Custom char loop | `re.search(r"\b" + re.escape(t) + r"\b", text, re.IGNORECASE)` | re.escape handles tokens with special chars (e.g., "rx" with periods); \b handles "loan" not matching "loaner" partially |
| Markdown table generation | f-string row-by-row | `tabulate(rows, headers, tablefmt="github")` | Already in pyproject.toml; matches render_report.py existing tables |
| Markdown cell sanitization | Hand-strip pipes/quotes | `lib.io.escape_md_cell` | Already exists; RPRT-04 contract; one place to fix bugs |
| HTML escaping | Manual `.replace("<", "&lt;")` | `render_report.py`'s `_html_escape` (line 651) | Already defined; consistent with rest of HTML output |
| JSON sidecar load with graceful degradation | Repeat try/except blob in main() | Mirror Phase 8 sidecar pattern (render_report.py lines 1273-1297) | Five sidecars handled identically; new ones must match |
| Argparse setup | Reinvent CLI scaffolding | Mirror `volume_enrich.py` `main_with_args(argv)` pattern | Test-friendly (argv as param); consistent exit codes (0/2/3) |

**Key insight:** Phase 9 is integration on top of mature primitives. Every "I might need to write a small helper" should first check `lib/` and existing scripts. The hand-roll-budget for Phase 9 is bid math + CTR math + token matching — nothing else.

## Common Pitfalls

### Pitfall 1: Orphan Keywords During Cluster-Median Fallback
**What goes wrong:** BIDS-02 says "fall back to cluster-median CPC." But what if a keyword is in `clusters.json["orphans"]` (i.e., not assigned to any named cluster)? Current `clusters.json` schema (Phase 4) has an `orphans: []` array at the top level.

**Why it happens:** Phase 4 puts undocked keywords into `orphans`. Phase 9 logic that joins on cluster name won't find them.

**How to avoid:**
- Build a `keyword_lower → cluster_name` index up-front (mirrors `_build_cluster_index` in render_report.py line 489).
- If a keyword has no cluster (orphan): the fallback **cannot use a cluster median**. Choice: (a) use overall-median CPC × multiplier across all keywords with CPC data, or (b) emit `null + no_cpc_data` flag.
- **Recommendation:** option (b) — null + flag. It's honest. Option (a) makes orphan bids over-confident.

**Warning signs:** unit tests with orphan-only fixtures show non-null suggested_max_cpc; report shows no `no_cpc_data` flag despite orphan keywords.

### Pitfall 2: Empty Cluster CPC Pool
**What goes wrong:** Cluster has 5 keywords; all 5 have `cpc_micros: null`. `statistics.median([])` raises `StatisticsError`.

**Why it happens:** Ahrefs returns null for long-tail keywords (~40% of keywords per Phase 8 docs). A small cluster can have zero CPC data.

**How to avoid:**
```python
def cluster_median_cpc(cluster_keywords: list[dict]) -> int | None:
    cpcs = [k["cpc_micros"] for k in cluster_keywords if k.get("cpc_micros") is not None]
    if not cpcs:
        return None  # signal to caller: use no_cpc_data flag
    return int(statistics.median(cpcs))
```

**Warning signs:** Test fixture with 100%-null cluster crashes with `StatisticsError`.

### Pitfall 3: Compliance Token False Positives
**What goes wrong:** Token list contains "loan" → matches keyword "loaner mug" (a household item). False positive triggers spurious compliance warning.

**Why it happens:** Substring matching without word boundary.

**How to avoid:** Use `\b` regex word boundary as in the Architecture pattern.

**Edge cases to test:**
- "personal loan" should match "loan" token (word boundary "loan" present)
- "loaner" should NOT match "loan" token
- "rx" must match exactly (don't accidentally match "fox"). For very short tokens, consider requiring the token to be a full word: `r"(?:^|\s)" + re.escape(t) + r"(?:\s|$|[.,!?])"` — but the simpler `\b\w` boundary handles most cases.

**Warning signs:** `brief_neutral.md` (kitchenware vertical) flags as `finance` because of "loaner mug" or similar.

### Pitfall 4: Top-N Compliance Scan Window
**What goes wrong:** Scan all ranked keywords → false positive flood. Scan only top 10 → miss a regulated keyword at rank 15.

**Why it happens:** No principled threshold defined by requirements.

**How to avoid:** Use top 50 by default (covers all clusters in typical 5-7 cluster runs). Make it a script-level constant `COMPLIANCE_SCAN_TOP_N = 50` so operator can tune. Always scan `brief.md` in full (it's short).

**Warning signs:** Operator complains "you missed obvious medical keyword" → expand top-N; or "spurious finance flag because rank-80 keyword contained 'credit'" → reduce top-N.

### Pitfall 5: render_report.py Becoming a Choke Point
**What goes wrong:** Phase 9 adds 3 new kwargs (`suggested_max_cpc_micros` already on rows, but `forecast=`, `compliance=`). Each new section requires HTML + Markdown + JSON rendering. The single file grows past maintainability.

**Why it happens:** render_report.py is already ~1335 lines.

**How to avoid:**
- Add minimal new code paths: extend `render_full_report` signature with `forecast=None, compliance=None`; extend `build_report_json` similarly.
- New Markdown sections via two new dedicated functions: `render_forecast_section(forecast)` and `render_compliance_warning(compliance)`. Mirror the structure of `render_account_perf_section` (line 344).
- HTML extension: add two new `<section>` blocks in `_HTML_TEMPLATE` + two new JS render functions (`renderForecast`, `renderCompliance`). Follow `renderAccountPerf` (line 906) shape exactly.
- New `report.json` keys: `forecast` (object or empty), `compliance` (array).
- Compliance warning **must appear above Ranked Keywords table** (CMPL-03) — insert into `sections` list before the enriched/plain keyword table.

**Warning signs:** render_report.py jumps past 1700 lines or the new functions duplicate code rather than calling helpers.

### Pitfall 6: Cluster Aggregation Mismatch
**What goes wrong:** `forecast.json` sums per-keyword click estimates into per-cluster totals. But `ranked-enriched.json` is a flat list and `clusters.json` is the cluster→keywords mapping. Join key is the keyword string. Casing or whitespace drift between the two = silent under-count.

**Why it happens:** Phase 4 may normalize cluster keyword strings differently than Phase 2's canonicalization.

**How to avoid:**
- Always join on `keyword.lower().strip()` — mirrors render_report.py's `_build_cluster_index` (line 489-496).
- Unit test: fixture where cluster keyword "Same-Day Delivery" matches ranked keyword "same-day delivery" — assert match succeeds.
- Surface `unjoined_count` in forecast.json metadata so operator detects silent failures.

**Warning signs:** Sum of per-cluster `keyword_count` < total keywords with CPC data in `ranked-enriched.json`.

### Pitfall 7: Compliance Section Render Order
**What goes wrong:** CMPL-03 specifies "above the Ranked Keywords table." If accidentally placed after, the operator misses the warning until scrolling past 100 keywords.

**Why it happens:** Easy to append at end of `sections` list.

**How to avoid:** Insert compliance section into `sections` list **immediately before** the `## Ranked Keywords` block (existing render_report.py lines 596-608). In HTML, it's a new `<section>` before `<section id="keywords">`. Test verifies markdown ordering with regex / index lookups.

### Pitfall 8: `cpc_micros` Unit Confusion
**What goes wrong:** Code multiplies `cpc_micros` (e.g., 250000 = $0.25) by 1.2 and treats it as USD ($300,000). All downstream math is 1M× too large.

**Why it happens:** `cpc_micros` is in micros (USD × 1,000,000). volume_enrich.py line 139 computes it as `cpc_cents × 10_000` (so 25 cents → 250,000 micros). render_report.py line 323 converts back via `cpc_micros / 10_000 / 100 = USD`.

**How to avoid:**
- Stay in micros for all arithmetic; only convert to USD at the **display boundary** (markdown / HTML cell).
- Write a helper `micros_to_usd(m: int) -> str` that returns `"$X.XX"` format.
- Document the unit at module top: "All CPC values are stored in micros (USD × 1,000,000). Convert only at display."
- Unit-test the multiplier: 250000 × 1.2 = 300000 micros = $0.30 (not $300k).

**Warning signs:** Forecast bands of $50k/day per cluster on a small campaign. Bid suggestions in the thousands of dollars.

## Code Examples

### bid_suggest.py logic (BIDS-01, BIDS-02, BIDS-04)

```python
# bid_suggest.py
import statistics
from typing import Optional

INTENT_MULTIPLIERS: dict[str, float] = {
    "transactional": 1.2,
    "commercial":    0.8,
    "informational": 0.4,
    "navigational":  1.0,
}

def compute_suggested_cpc(
    cpc_micros: Optional[int],
    intent: str,
    cluster_median_micros: Optional[int],
) -> tuple[Optional[int], bool]:
    """Return (suggested_max_cpc_micros, used_fallback).

    used_fallback=True signals 'no_cpc_data' flag in report when value is null
    OR when fallback was used (BIDS-02).
    """
    multiplier = INTENT_MULTIPLIERS.get(intent)
    if multiplier is None:
        # Unknown intent — defensive null
        return (None, True)

    base_micros = cpc_micros if cpc_micros is not None else cluster_median_micros
    if base_micros is None:
        return (None, True)  # null + flag no_cpc_data

    suggested = int(round(base_micros * multiplier))
    used_fallback = cpc_micros is None
    return (suggested, used_fallback)

def cluster_median_cpc(
    keyword_to_cluster: dict[str, str],
    cluster_to_keywords: dict[str, list[dict]],
    cluster_name: Optional[str],
) -> Optional[int]:
    """Median CPC (in micros) across cluster siblings with CPC data.

    Returns None if cluster_name is None (orphan) or no siblings have CPC.
    """
    if cluster_name is None:
        return None
    siblings = cluster_to_keywords.get(cluster_name, [])
    cpcs = [k["cpc_micros"] for k in siblings if k.get("cpc_micros") is not None]
    if not cpcs:
        return None
    return int(statistics.median(cpcs))
```

### forecast.json Schema (FRCS-01, FRCS-04)

```json
{
  "metadata": {
    "generated_at": "2026-05-14T18:30:00Z",
    "run_id": "2026-05-14T183000Z-grocery-delivery-uk",
    "schema_version": "v1",
    "horizon": "daily"
  },
  "methodology": {
    "intent_ctrs": {
      "transactional": 0.06,
      "commercial":    0.04,
      "informational": 0.02,
      "navigational":  0.08
    },
    "avg_cpc_ratio": 0.65,
    "band_multipliers": {"low": 0.5, "mid": 1.0, "high": 1.5},
    "notes": "Directional estimates. Not Google's official forecast (see Keyword Planner). Assumes one impression per searched keyword and intent-class CTR anchors derived from industry medians."
  },
  "clusters": [
    {
      "name": "same_day_delivery_transactional",
      "intent": "transactional",
      "keyword_count": 8,
      "keywords_with_volume": 6,
      "total_monthly_volume": 12400,
      "daily_clicks_low": 12,
      "daily_clicks_mid": 25,
      "daily_clicks_high": 37,
      "daily_spend_low_usd": 8.42,
      "daily_spend_mid_usd": 16.85,
      "daily_spend_high_usd": 25.27,
      "monthly_spend_mid_usd": 505.50
    }
  ],
  "campaign_totals": {
    "cluster_count": 5,
    "keyword_count": 42,
    "daily_clicks_low": 35,
    "daily_clicks_mid": 70,
    "daily_clicks_high": 105,
    "daily_spend_low_usd": 22.50,
    "daily_spend_mid_usd": 45.00,
    "daily_spend_high_usd": 67.50,
    "monthly_spend_mid_usd": 1350.00,
    "unjoined_keywords": 0
  }
}
```

### Aggregation algorithm (FRCS-01)

```python
# Per keyword: monthly_clicks_keyword = volume × intent_ctr
# Per cluster: daily_clicks_mid = sum(monthly_clicks_keyword for kw in cluster) / 30
# Per cluster: daily_spend_mid_usd = daily_clicks_mid × (suggested_max_cpc × 0.65) / 1e6
# Bands: low = mid × 0.5, high = mid × 1.5
# Skip keywords where volume is None OR suggested_max_cpc_micros is None
```

### compliance-flags.json shape (CMPL-01)

```json
{
  "metadata": {
    "generated_at": "2026-05-14T18:30:00Z",
    "run_id": "2026-05-14T183000Z-medical-clinic-london",
    "schema_version": "v1",
    "scanned_top_n_keywords": 50
  },
  "matched_verticals": [
    {
      "name": "medical",
      "evidence_tokens": ["clinic", "physician", "telehealth"],
      "evidence_sources": {
        "brief": ["clinic", "physician"],
        "keywords": ["telehealth", "clinic"]
      },
      "matched_keyword_count": 7,
      "verification_url": "https://support.google.com/adspolicy/answer/176031",
      "policy_note": "Healthcare advertisers may require LegitScript..."
    }
  ]
}
```

When no vertical matches: `"matched_verticals": []`. `compliance-flags.json` is still written (empty array) so downstream tooling can rely on it existing once compliance_check.py runs successfully.

### Token matching algorithm (CMPL-01)

```python
import re

def find_matches(text: str, tokens: list[str]) -> list[str]:
    """Return sorted list of unique tokens that appear in text (case-insensitive,
    word-boundary-aware). Empty list if no matches."""
    if not text or not tokens:
        return []
    found: set[str] = set()
    for token in tokens:
        if not token.strip():
            continue
        pattern = r"\b" + re.escape(token) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            found.add(token.lower())
    return sorted(found)
```

### render_report.py extension points

**Signature change for `render_full_report`:**

```python
def render_full_report(
    ranked, clusters_data, competitor_intel, negatives, brief_text, run_dir,
    *,
    top_n=100,
    niche_pulse=None,
    account_perf=None,
    negatives_sync=None,
    forecast=None,        # NEW
    compliance=None,      # NEW
) -> str:
```

**Section ordering inside `sections` list:**

1. Header + HOW_TO_READ
2. **Compliance warning block (NEW — CMPL-03)** — only when `compliance and compliance.get("matched_verticals")`
3. Niche Pulse
4. Account Performance
5. Negatives Sync
6. Ad Group Clusters
7. **Budget Forecast (NEW — FRCS-04)** — after clusters, before negatives (operator decides daily budget right after seeing ad groups)
8. Negatives
9. Competitor Ad Copy
10. Ranked Keywords / Volume-Enriched table (**now with Suggested Max CPC column — BIDS-03**)

**Enriched table column addition (BIDS-03):** modify `render_enriched_keyword_table` (line 317) to append a new column `Suggested CPC` formatted as `f"${r['suggested_max_cpc_micros']/1_000_000:.2f}"` (or "—" + flag when null). Test golden file must reflect new column.

**HTML extension:** add two new `<section>` blocks + two `renderForecast()` / `renderCompliance()` JS functions in the `<script>` block. Compliance section uses `background: #fef3c7` (warning yellow, already used for pulse highlights). Forecast section uses `background: #ecfdf5` (success green, already used for account perf totals).

### build_report_json signature changes (CMPL-04)

```python
def build_report_json(
    ranked, clusters_data, competitor_intel, negatives, brief_text, run_dir,
    *,
    niche_pulse=None, account_perf=None, negatives_sync=None,
    forecast=None,        # NEW
    compliance=None,      # NEW
) -> dict:
    return {
        # ... existing keys ...
        "forecast": forecast or {},
        "compliance": (compliance or {}).get("matched_verticals", []),  # CMPL-04: array, not object
    }
```

### Methodology section pattern (FRCS-05)

Forecast section MD body ends with:

```markdown
### How this is calculated

These are directional estimates, not Google's official forecast. Use Keyword Planner for Google's projections.

- **Clicks** = monthly search volume × intent-class CTR anchor (transactional 6%, commercial 4%, informational 2%, navigational 8%) ÷ 30 days
- **Spend** = clicks × (suggested max CPC × 0.65) — the 0.65 ratio approximates the typical avg-CPC-to-max-CPC gap
- **Bands** = mid × 0.5 (low) / × 1.0 (mid) / × 1.5 (high) to express uncertainty
- Keywords with no Ahrefs volume or no suggested CPC are skipped in this forecast — the cluster total reflects only keywords with both fields.
```

Surface these directly from `forecast.json` `methodology` block so editing the script config also edits the report disclaimer (single source of truth).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hard-code policy strings in Python | Data-driven JSON in `references/` | Phase 9 (CMPL-02) | Operator extends without redeploying |
| Mutate ranked.json in place | Write ranked-enriched.json with new fields (additive) | Phase 8 precedent | Original ranking auditable; Phase 9 inherits the discipline |
| Single fat render_report.py kwargs | Sidecar JSON + auto-detect via Path.exists() | Phase 7 (niche-pulse) | Phase 9 must follow this pattern, not invent a new one |

**Currency check (Google Ads policy verticals, May 2026):**

- **Medical:** healthcare advertisers may require LegitScript certification depending on jurisdiction. Policy page stable.
- **Legal:** lawyer-advertising rules; policy page stable.
- **Finance:** Financial Services Verification expanded April 2026 to 14 additional jurisdictions with KYC tightening for crypto, consumer loans, BNPL. Token list should include `bnpl`, `buy now pay later`.
- **Gambling:** new "account health" eligibility criteria March 23, 2026. Prediction Markets US-only with CFTC DCM authorization (January 2026 update).
- **Crypto:** crypto exchange + wallet ads expanded to Indonesia (OJK licensing) February 2026. US still requires FinCEN MSB + state licensure.

**Implication for `references/compliance-verticals.json`:** the `policy_note` field should reference these 2026 changes; the `verification_url` should point to Google's Advertising Policies Help Center (stable URLs in §Sources).

**Deprecated/outdated:**
- None — Phase 9 uses no deprecated APIs. All decisions tracked in STATE row 162 are valid as of May 2026.

## Open Questions

1. **Are intent-CTR anchors (T=6/C=4/I=2/N=8) defensible?**
   - What we know: These come from PROJECT.md / requirements and STATE row 161 notes them as a starting point for calibration.
   - What's unclear: Industry-median CTRs vary widely by vertical (Wordstream / Search Engine Land 2023+ benchmarks suggest ranges 3-9% for transactional retail).
   - Recommendation: Ship the anchors as-is; document in methodology section that they are directional; calibrate after 3 v1.1 runs (per STATE open questions).

2. **Should compliance scan include cluster names?**
   - What we know: Cluster names follow `theme_intent` pattern (e.g., "medical_clinic_transactional").
   - What's unclear: Scanning cluster names could double-count (theme tokens are derived from keywords already scanned).
   - Recommendation: **Do not scan cluster names.** Scan brief.md + top-N keywords only. Cluster names are derived, not independent evidence.

3. **What's the right top-N for keyword compliance scan?**
   - What we know: Total keywords typically 30-100 per run.
   - What's unclear: Performance vs accuracy tradeoff.
   - Recommendation: **50**. Constant `COMPLIANCE_SCAN_TOP_N = 50` at top of compliance_check.py so operator can override.

4. **Should `bid_suggest.py` be invoked even when `ranked-enriched.json` lacks any CPC data?**
   - What we know: Without Ahrefs (Phase 8 skipped), `ranked-enriched.json` does not exist.
   - What's unclear: Should Phase 9 work on `ranked.json` (no CPC) and emit all-null `suggested_max_cpc_micros`?
   - Recommendation: **Require `ranked-enriched.json` to exist.** Exit 3 with clear message: "Phase 9 requires Phase 8 (volume_enrich.py) — no CPC data to base bids on." Reduces unhelpful null-output noise.

5. **Should `forecast.json` be written even with zero CPC data?**
   - Recommendation: Yes — write a valid forecast.json with all clusters at `daily_spend_*=0` and `unjoined_keywords` populated. Render section degrades to "No volume data available — run Phase 8 first."

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.3 (already declared in `scripts/pyproject.toml` dev deps) |
| Config file | `.claude/skills/google-ad-research/scripts/pyproject.toml` (`[tool.pytest.ini_options]` testpaths=["tests"]) |
| Quick run command | `cd .claude/skills/google-ad-research/scripts && uv run --with pytest pytest tests/test_bid_suggest.py tests/test_forecast_budget.py tests/test_compliance_check.py -x` |
| Full suite command | `uv run --with pytest --with python-dotenv --with python-slugify --with tabulate pytest .claude/skills/google-ad-research/scripts/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BIDS-01 | `bid_suggest.py` adds `suggested_max_cpc_micros` from cpc × multiplier | unit | `pytest tests/test_bid_suggest.py::test_compute_suggested_cpc_transactional -x` | ❌ Wave 0 |
| BIDS-01 | Multipliers applied correctly to each of 4 intents | unit | `pytest tests/test_bid_suggest.py::test_all_four_intents_multiplied -x` | ❌ Wave 0 |
| BIDS-02 | Falls back to cluster-median when keyword has no CPC | unit | `pytest tests/test_bid_suggest.py::test_cluster_median_fallback -x` | ❌ Wave 0 |
| BIDS-02 | Returns null + flags `no_cpc_data` when cluster has zero CPC | unit | `pytest tests/test_bid_suggest.py::test_null_when_cluster_empty_cpc -x` | ❌ Wave 0 |
| BIDS-02 | Orphan keyword (no cluster) → null + flag | unit | `pytest tests/test_bid_suggest.py::test_orphan_returns_null -x` | ❌ Wave 0 |
| BIDS-03 | Report renders Suggested Max CPC column | unit | `pytest tests/test_render_report.py::test_enriched_table_has_suggested_cpc_column -x` | ❌ Wave 0 |
| BIDS-03 | HTML tooltip on hover shows multiplier | manual-only | (visual check in browser; document in VALIDATION.md) | n/a |
| BIDS-04 | INTENT_MULTIPLIERS dict is the only place numbers appear | unit | `pytest tests/test_bid_suggest.py::test_no_magic_numbers_in_code -x` (grep-based smoke) | ❌ Wave 0 |
| FRCS-01 | Emits forecast.json with per-cluster + campaign-level fields | unit | `pytest tests/test_forecast_budget.py::test_forecast_json_schema -x` | ❌ Wave 0 |
| FRCS-02 | Click estimates use intent-CTR anchors | unit | `pytest tests/test_forecast_budget.py::test_click_estimates_use_intent_ctrs -x` | ❌ Wave 0 |
| FRCS-03 | Spend = max-CPC × 0.65; bands × 0.5/1.0/1.5 | unit | `pytest tests/test_forecast_budget.py::test_band_arithmetic -x` | ❌ Wave 0 |
| FRCS-04 | Report renders Budget Forecast section | unit | `pytest tests/test_render_report.py::test_forecast_section_in_report -x` | ❌ Wave 0 |
| FRCS-05 | "How this is calculated" subsection present with assumptions | unit | `pytest tests/test_render_report.py::test_forecast_methodology_present -x` | ❌ Wave 0 |
| CMPL-01 | Scans brief + top-N keywords; emits compliance-flags.json | unit | `pytest tests/test_compliance_check.py::test_scans_and_emits -x` | ❌ Wave 0 |
| CMPL-01 | Word-boundary matching: "loaner" does NOT match "loan" | unit | `pytest tests/test_compliance_check.py::test_word_boundary -x` | ❌ Wave 0 |
| CMPL-02 | Token lists loaded from references/compliance-verticals.json | unit | `pytest tests/test_compliance_check.py::test_loads_from_json_reference -x` | ❌ Wave 0 |
| CMPL-03 | Report renders compliance warning above Ranked Keywords table | unit | `pytest tests/test_render_report.py::test_compliance_warning_position -x` | ❌ Wave 0 |
| CMPL-03 | No warning rendered when no vertical matches | unit | `pytest tests/test_render_report.py::test_no_compliance_block_when_clean -x` | ❌ Wave 0 |
| CMPL-04 | report.json gains compliance[] array; empty when no flags | unit | `pytest tests/test_render_report.py::test_report_json_compliance_array -x` | ❌ Wave 0 |
| CMPL-05 | Phase 9 emits the data; Phase 10 consumes (verify contract: matched_verticals[].verification_url present) | unit | `pytest tests/test_compliance_check.py::test_verification_url_present_per_vertical -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_<module>.py -x` (the script under change)
- **Per wave merge:** `pytest .claude/skills/google-ad-research/scripts/tests/ -x` (full suite — Phase 9 tests + Phases 1-8 regression)
- **Phase gate:** Full suite green before `/gsd:verify-work`. Manual smoke: run Phase 9 end-to-end on a real run-folder (use one from `.runs/` if available) and inspect rendered report.md + report.html.

### Wave 0 Gaps
- [ ] `tests/test_bid_suggest.py` — MODULE_MISSING guard + tests for BIDS-01..04
- [ ] `tests/test_forecast_budget.py` — MODULE_MISSING guard + tests for FRCS-01..05
- [ ] `tests/test_compliance_check.py` — MODULE_MISSING guard + tests for CMPL-01..05
- [ ] `tests/test_render_report.py` — add new test cases for Suggested CPC column, Forecast section, Compliance warning (modify existing file)
- [ ] `tests/fixtures/ranked_with_cpc.json` — 10-15 keywords, all with cpc_micros, 4 intents represented
- [ ] `tests/fixtures/ranked_no_cpc.json` — 10 keywords, all cpc_micros: null
- [ ] `tests/fixtures/ranked_partial_cpc.json` — mix of with/without CPC, including orphan keyword
- [ ] `tests/fixtures/clusters_phase9.json` — clusters matching the ranked_*_cpc fixtures
- [ ] `tests/fixtures/brief_medical.md` — triggers medical vertical
- [ ] `tests/fixtures/brief_legal.md` — triggers legal vertical
- [ ] `tests/fixtures/brief_neutral.md` — no regulated tokens (must NOT trigger any)
- [ ] `tests/fixtures/compliance_verticals_phase9.json` — test-isolated copy of references/compliance-verticals.json so test stays stable when operator extends the real file
- [ ] `tests/fixtures/forecast_expected.json` — golden output for a known ranked+clusters input
- [ ] `tests/fixtures/compliance_expected.json` — golden output for brief_medical + medical keywords
- [ ] No framework install needed — pytest already in `scripts/pyproject.toml` dev deps

## Sources

### Primary (HIGH confidence)
- `.planning/REQUIREMENTS.md` (lines 108-135) — BIDS-01..04, FRCS-01..05, CMPL-01..05 specifications verbatim
- `.planning/ROADMAP.md` (lines 141-152) — Phase 9 goal, depends, success criteria
- `.planning/STATE.md` (lines 150-152, 160-162) — v1.1 roadmap decisions on Phase 9 split and config-block discipline
- `.claude/skills/google-ad-research/CLAUDE.md` / project CLAUDE.md — PEP 723, .env, run-folder isolation conventions
- `.claude/skills/google-ad-research/scripts/volume_enrich.py` (lines 1-241) — Phase 8 pattern: enrichment script that writes ranked-enriched.json
- `.claude/skills/google-ad-research/scripts/render_report.py` (lines 317-341, 344-453, 535-609, 1188-1224, 1273-1297) — render extension points + sidecar load patterns
- `.claude/skills/google-ad-research/references/phase8-account-data.md` — sidecar reference-file template Phase 9 must mirror

### Secondary (MEDIUM confidence)
- [Google Ads Account Certification Application (February 2026)](https://almcorp.com/blog/google-ads-account-certification-application-2026/) — 2026 policy currency check; verified against multiple sources
- [Update to the Google Ads Certification Process (May 2026)](https://support.google.com/adspolicy/answer/17067928?hl=en) — official Google Ads Policy Help Center; verification URL stability for compliance-verticals.json
- [Google Ads Financial Services Verification April 2026](https://www.auditsocials.com/blog/google-ads-financial-services-verification-expansion-april-2026-new-jurisdictions-kyc-crypto-loan-bnpl) — confirms April 2026 expansion to 14 jurisdictions + BNPL/crypto tightening
- [Google Ads Cryptocurrency Certification in 2026](https://almcorp.com/blog/google-ads-cryptocurrency-certification-2026/) — confirms Indonesia OJK licensing addition Feb 2026
- [Update to Prediction Markets (January 2026)](https://support.google.com/adspolicy/answer/16749907) — CFTC DCM authorization for US prediction markets
- Google Advertising Policy stable URLs (verification_url candidates): `support.google.com/adspolicy/answer/176031` (healthcare), `2464998` (finance/legal — same page lists both), `176019` (gambling), `9870661` (crypto)

### Tertiary (LOW confidence)
- None — all Phase 9 claims rest on either local code/spec inspection (HIGH) or verified Google policy pages (MEDIUM).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Phase 9 reuses existing project deps; no new libraries
- Architecture: HIGH — Phases 6, 7, 8 establish identical sidecar pattern; Phase 9 mirrors verbatim
- Pitfalls: HIGH — drawn from inspecting volume_enrich.py + render_report.py code, plus STATE.md decisions
- Compliance vertical token currency: MEDIUM — Google policy URLs verified May 2026; tokens are reasonable starter lists subject to operator extension (operator-tunable per CMPL-02)
- CTR/bid multiplier defensibility: MEDIUM — values come from PROJECT.md decisions; calibration deferred to post-launch per STATE row 161

**Research date:** 2026-05-14
**Valid until:** 2026-08-14 (90 days; the only fast-moving piece is Google Ads policy verification URLs — sanity-check those at planning time if the run is in 2027+)
