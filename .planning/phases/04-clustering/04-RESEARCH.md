# Phase 4: Clustering - Research

**Researched:** 2026-05-08
**Domain:** LLM-driven intent-homogeneous keyword clustering + Python validation helper
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLST-01 | Keywords cluster within intent class only — no intent-mixed clusters allowed | Hard pre-split by intent before LLM semantic grouping; validate_clusters.py exit 3 on violation |
| CLST-02 | LLM produces clusters of 5-15 keywords (min size 3) with descriptive names combining theme + intent | Prompt instructs size range; validator enforces min 3 / max 25; merge/split loop handles violations |
| CLST-03 | Any cluster spanning more than one intent label is rejected and re-split | Validator detects distinct intent values per cluster; returns exit 3 with offending cluster IDs |
</phase_requirements>

---

## Summary

Phase 4 takes `ranked.json` (every keyword already has `intent`, `score`, `match_type`) and produces `clusters.json` — a list of named, intent-homogeneous ad groups a PPC manager can paste straight into Google Ads.

The architecture is a two-part split of concerns: the Claude skill prompt does the semantic judgment (grouping similar keywords within an intent class, naming each cluster), and a small Python script `validate_clusters.py` enforces all invariants deterministically (no mixed intent, size bounds, no orphans, name format). This matches the established project pattern — LLM for judgment, Python for deterministic validation.

The most important invariant is that **intent is a hard pre-split, not a soft constraint**. The skill partitions `ranked.json` by intent class before any semantic clustering begins. LLM clustering only ever sees keywords of a single intent. This prevents the Quality Score degradation from mixed-intent ad groups (Pitfall 5) and makes the validator trivially fast.

**Primary recommendation:** Partition by intent first (in skill prompt), cluster semantically within each partition (in skill prompt), then run `validate_clusters.py` in a fix loop — if the validator exits non-zero, the skill reads the reported violations and re-prompts for just those clusters.

---

## Input: ranked.json Schema

From `rank_keywords.py`, each row in `ranked.json` has these columns:

```json
{
  "keyword":          "same day grocery delivery uk",
  "intent":           "transactional",
  "match_type":       "phrase",
  "theme":            "",
  "signal_count":     4,
  "source_diversity": 3,
  "sources":          ["serper-organic", "serper-paa", "tavily"],
  "score":            325
}
```

`intent` is guaranteed to be one of `informational | commercial | transactional | navigational`. `theme` is empty — Phase 4 fills it as the cluster name.

---

## Output: clusters.json Schema

```json
{
  "metadata": {
    "clustered_at": "2026-05-08T14:30:00Z",
    "method": "llm-driven",
    "model": "claude-sonnet-4-6",
    "ranked_input": "ranked.json",
    "total_keywords": 47,
    "total_clusters": 8
  },
  "clusters": [
    {
      "name": "same_day_delivery_transactional",
      "intent": "transactional",
      "keywords": [
        {"keyword": "same day grocery delivery uk", "score": 325},
        {"keyword": "get groceries delivered today", "score": 310}
      ]
    }
  ],
  "orphans": []
}
```

**Field rules:**
- `name`: `{theme_slug}_{intent}` — lowercase snake_case, 2-4 meaningful words before the intent suffix
- `intent`: matches the intent of every keyword in the cluster (enforced by validator)
- `keywords`: objects with `keyword` and `score` only — no full ranked.json row duplication
- `orphans`: keywords not placed in any cluster — must be empty or validator warns

---

## Architecture Patterns

### Two-Pass Workflow

```
ranked.json
    │
    ├── [Skill Prompt] Partition by intent class
    │       transactional_kws = [...]
    │       commercial_kws    = [...]
    │       informational_kws = [...]
    │       navigational_kws  = [...]
    │
    ├── [Skill Prompt] Cluster semantically within each partition
    │       For each intent class: group by theme → name each group
    │
    ├── [Skill] Write clusters.json
    │
    └── [validate_clusters.py] Enforce invariants
            Exit 0 → done
            Exit 3 → report violations → skill re-prompts for offending clusters only
```

The fix loop is: validate → if violations exist, skill reads error JSON → re-prompts for just the offending cluster IDs → overwrites those clusters in clusters.json → re-validates. Maximum 2 fix iterations before surfacing to operator.

### Project Structure Addition

```
scripts/
├── validate_clusters.py     # new — deterministic invariant checks
├── tests/
│   ├── test_validate_clusters.py   # new — unit tests
│   └── fixtures/
│       └── clusters_valid.json     # new fixture
│       └── clusters_mixed_intent.json  # new fixture
│       └── clusters_oversize.json      # new fixture
```

---

## Cluster Naming Convention

Format: `{theme_slug}_{intent}` — lowercase, snake_case.

Rules enforced by `validate_clusters.py`:
1. Must match regex `^[a-z][a-z0-9_]+_(transactional|commercial|informational|navigational)$`
2. Theme slug must be ≥ 2 words (i.e., at least one underscore before the intent suffix)
3. Rejected names: anything matching `^(cluster|theme|topic|group|k)_?\d` or single-word themes

Valid examples:
- `same_day_delivery_transactional`
- `grocery_brand_comparison_commercial`
- `delivery_how_it_works_informational`
- `ocado_brand_navigational`

Invalid examples (validator rejects):
- `cluster_1_transactional` — numeric / "cluster" prefix
- `grocery_transactional` — single-word theme
- `Grocery_Delivery_Transactional` — uppercase
- `same-day-delivery_transactional` — hyphens not underscores

Skill prompt guidance: name should be derivable from 2-3 most-frequent words in the cluster's keyword list + the intent class.

---

## validate_clusters.py Specification

### CLI

```
uv run validate_clusters.py --run-dir <abs>
```

Reads: `{run_dir}/clusters.json`, `{run_dir}/ranked.json`

Stdout: one JSON line with validation summary
```json
{"valid": true, "cluster_count": 8, "orphan_count": 0, "violations": []}
```
Or on failure:
```json
{"valid": false, "violations": [
  {"type": "mixed_intent", "cluster": "bad_cluster_transactional", "found_intents": ["transactional", "commercial"]},
  {"type": "oversize", "cluster": "big_theme_transactional", "size": 28},
  {"type": "bad_name", "cluster": "cluster_3_informational"}
]}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All invariants satisfied |
| 1 | Warnings only (undersize cluster 3-4 kw; orphans present) — skill should address but may proceed |
| 3 | Hard violations (mixed intent, bad name, oversize >25) — skill MUST fix before proceeding |

Note: exit code 2 is reserved for infrastructure errors (missing file, bad JSON).

### Invariant Checks

| Check | Condition | Exit Code | Violation Type |
|-------|-----------|-----------|----------------|
| Mixed intent | `len(set(kw["intent"] for kw in cluster)) > 1` | 3 | `mixed_intent` |
| Oversize | `len(cluster["keywords"]) > 25` | 3 | `oversize` |
| Undersize | `len(cluster["keywords"]) < 3` | 1 | `undersize` (warn) |
| Target undersize | `len(cluster["keywords"]) < 5` | 1 | `target_undersize` (warn) |
| Bad name | name fails regex or "cluster/theme/topic" prefix | 3 | `bad_name` |
| Orphans | `len(clusters_json["orphans"]) > 0` | 1 | `orphans` (warn) |
| Avg size | `total_kws / cluster_count < 5` | 1 | `avg_size_low` (warn, Pitfall 10) |
| Keyword not in ranked | cluster keyword missing from ranked.json | 3 | `unknown_keyword` |
| Duplicate assignment | same keyword in 2+ clusters | 3 | `duplicate_keyword` |

### Intent Cross-Check

`validate_clusters.py` joins cluster keywords against `ranked.json` to get their authoritative intent values. It does NOT trust the keyword-level intent stored inside `clusters.json` — it always reads from the ranked source of truth. This prevents the skill from accidentally changing intents during clustering.

---

## Skill Prompt Pattern (Steps 14-16)

### Step 14: Pre-split by intent

```
Read {run_dir}/ranked.json.
Partition all keywords into four lists by their `intent` field.
Print counts: transactional=N, commercial=N, informational=N, navigational=N.
```

### Step 15: Cluster within each partition

For each non-empty intent class:
1. Show the keyword list for that intent class (keyword + score, sorted by score desc)
2. Group into thematic clusters (5-15 per cluster, min 3)
3. Name each cluster `{theme_slug}_{intent}`
4. If a class has < 3 keywords, create a single `misc_{intent}` cluster with all of them

Prompt instruction to Claude: "Group only by semantic theme. Do NOT re-assign intent. Do NOT create clusters that span more than one intent class. Produce cluster names from the most frequent 2-3 words in the group's keywords."

### Step 16: Write and validate

Write `clusters.json`, then:
```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/validate_clusters.py" --run-dir "{run_dir}"
```

Parse stdout. If `valid: true` (exit 0): proceed to confirm.
If exit 1 (warnings): surface warnings to operator, offer to fix or accept.
If exit 3: read `violations` list, re-prompt for only the offending clusters, rewrite those sections of `clusters.json`, re-validate. Max 2 fix iterations.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Intent validation across keyword list | custom set-intersection logic | `frozenset` comparison in validator; intent values already locked by `rank_keywords.py` |
| Name format enforcement | ad-hoc string checks | Compile one regex at module level, reuse |
| Cluster size bounds | scattered `if` checks | Single `_check_sizes()` helper, called once per cluster |
| Orphan detection | traversal of both data structures | Build a seen-set from all cluster keywords, diff against ranked.json keys |
| JSON schema for clusters.json | Pydantic model | Too heavy for this; simple `dict` + explicit key checks is sufficient at this scale |

---

## Common Pitfalls

### Pitfall 5: Mixed intent in clusters (CRITICAL)
**What goes wrong:** LLM groups "grocery delivery near me" (transactional) with "how does grocery delivery work" (informational) because they share the "grocery delivery" stem.
**Prevention:** Pre-split by intent before any clustering prompt. The LLM never sees a mixed list.
**Validator check:** `mixed_intent` violation, exit 3.

### Pitfall 10: Over-clustering
**What goes wrong:** 60 clusters for 80 keywords. Avg cluster size < 3.
**Prevention:** Prompt instructs "minimum 5 per cluster; fold small fragments into nearest theme."
**Validator check:** `avg_size_low` warning (exit 1) when avg < 5.

### Pitfall 11: Under-clustering
**What goes wrong:** 3 clusters: "Grocery", "Delivery", "Other". Max cluster size 40+.
**Prevention:** Any cluster > 25 gets `oversize` exit 3; skill must split.
**Validator check:** `oversize` violation.

### Pitfall 12: Bad cluster names
**What goes wrong:** "Cluster 3", "Theme A", "K1_transactional".
**Prevention:** Regex enforcement in validator; prompt explicitly says "derive name from keywords, not from index."
**Validator check:** `bad_name` violation, exit 3.

### Orphan keywords
**What goes wrong:** Keywords left unassigned silently reduce report coverage.
**Prevention:** Skill must either fold into existing cluster or create `misc_{intent}` cluster. Orphans in `clusters.json["orphans"]` trigger exit 1.

### Same keyword in two clusters
**What goes wrong:** Keyword bidding strategy ambiguous; PPC manager double-bids.
**Prevention:** `duplicate_keyword` check in validator (exit 3).

---

## Code Examples

### validate_clusters.py skeleton

```python
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""validate_clusters.py — enforce clustering invariants.

Exit codes: 0=valid, 1=warnings, 2=infra error, 3=hard violations
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

NAME_RE = re.compile(
    r'^[a-z][a-z0-9]+(_[a-z0-9]+)*_(transactional|commercial|informational|navigational)$'
)
BAD_PREFIX_RE = re.compile(r'^(cluster|theme|topic|group|k)_?\d')
MAX_SIZE = 25
MIN_SIZE = 3
TARGET_MIN = 5

def check_clusters(clusters: list[dict], ranked_index: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """Returns (hard_violations, warnings)."""
    hard, warn = [], []
    seen: set[str] = set()
    for c in clusters:
        name = c.get("name", "")
        kws = c.get("keywords", [])
        # Name checks
        if not NAME_RE.match(name) or BAD_PREFIX_RE.match(name):
            hard.append({"type": "bad_name", "cluster": name})
        # Size checks
        if len(kws) > MAX_SIZE:
            hard.append({"type": "oversize", "cluster": name, "size": len(kws)})
        if len(kws) < MIN_SIZE:
            warn.append({"type": "undersize", "cluster": name, "size": len(kws)})
        elif len(kws) < TARGET_MIN:
            warn.append({"type": "target_undersize", "cluster": name, "size": len(kws)})
        # Intent purity — cross-check against ranked.json, not cluster's own intent field
        intents = {ranked_index[kw["keyword"]] for kw in kws if kw["keyword"] in ranked_index}
        if len(intents) > 1:
            hard.append({"type": "mixed_intent", "cluster": name, "found_intents": sorted(intents)})
        # Unknown keyword
        for kw in kws:
            if kw["keyword"] not in ranked_index:
                hard.append({"type": "unknown_keyword", "cluster": name, "keyword": kw["keyword"]})
        # Duplicate assignment
        for kw in kws:
            if kw["keyword"] in seen:
                hard.append({"type": "duplicate_keyword", "cluster": name, "keyword": kw["keyword"]})
            seen.add(kw["keyword"])
    return hard, warn
```

### Test pattern (following existing project conventions)

```python
# test_validate_clusters.py — Wave 0 RED stubs
try:
    import validate_clusters
    VC_MISSING = False
except ImportError:
    validate_clusters = None
    VC_MISSING = True

pytestmark = pytest.mark.skipif(VC_MISSING, reason="validate_clusters.py not yet implemented")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SKAGs (single keyword ad groups) | STAGs (single theme ad groups, 5-15 kws) | ~2021 Google broad-match update | Matches Google's keyword consolidation direction; fewer ad groups easier to manage |
| Embedding-based clustering (sentence-transformers) | LLM semantic clustering | Phase 4 decision | Removes ~700MB torch dep; works well for < 200 keywords |
| Cluster-then-classify intent | Classify-then-cluster | Always the right order | Intent is a hard split; doing it after produces mixed clusters |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already installed, used in Phases 1-3) |
| Config file | `scripts/tests/` directory, `conftest.py` with `SCRIPTS_DIR` path injection |
| Quick run command | `uv run --directory .claude/skills/google-ad-research/scripts pytest tests/test_validate_clusters.py -x -q` |
| Full suite command | `uv run --directory .claude/skills/google-ad-research/scripts pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLST-01 | Mixed intent cluster → exit 3 + `mixed_intent` violation | unit | `pytest tests/test_validate_clusters.py::test_mixed_intent_exit3 -x` | Wave 0 |
| CLST-01 | Pure intent cluster → no mixed_intent violation | unit | `pytest tests/test_validate_clusters.py::test_pure_intent_passes -x` | Wave 0 |
| CLST-02 | Cluster with 5-15 kws → valid | unit | `pytest tests/test_validate_clusters.py::test_target_size_valid -x` | Wave 0 |
| CLST-02 | Cluster with 2 kws → exit 1 undersize warning | unit | `pytest tests/test_validate_clusters.py::test_undersize_warns -x` | Wave 0 |
| CLST-02 | Cluster with 26 kws → exit 3 oversize | unit | `pytest tests/test_validate_clusters.py::test_oversize_exit3 -x` | Wave 0 |
| CLST-02 | Cluster name `{theme}_{intent}` valid → passes | unit | `pytest tests/test_validate_clusters.py::test_valid_name -x` | Wave 0 |
| CLST-03 | Cluster name "Cluster 3" → exit 3 bad_name | unit | `pytest tests/test_validate_clusters.py::test_bad_name_numeric -x` | Wave 0 |
| CLST-03 | Duplicate keyword in 2 clusters → exit 3 | unit | `pytest tests/test_validate_clusters.py::test_duplicate_keyword_exit3 -x` | Wave 0 |
| CLST-03 | Orphans in clusters.json → exit 1 | unit | `pytest tests/test_validate_clusters.py::test_orphans_warn -x` | Wave 0 |
| CLST-01/02/03 | Skill clustering quality | manual | Run full skill with grocery-delivery brief; inspect clusters.json | manual-only |
| CLST-01/02/03 | Fix loop: validator exit 3 → re-prompt → re-validate → exit 0 | manual | Run skill, intentionally provide mixed cluster in prompt, verify loop recovers | manual-only |

### Sampling Rate

- **Per task commit:** `uv run --directory .claude/skills/google-ad-research/scripts pytest tests/test_validate_clusters.py -x -q`
- **Per wave merge:** `uv run --directory .claude/skills/google-ad-research/scripts pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `scripts/tests/test_validate_clusters.py` — covers CLST-01, CLST-02, CLST-03 (RED stubs, MODULE_MISSING guard)
- [ ] `scripts/tests/fixtures/clusters_valid.json` — 2 well-formed clusters, pure intent, target size
- [ ] `scripts/tests/fixtures/clusters_mixed_intent.json` — 1 cluster with transactional + commercial kws
- [ ] `scripts/tests/fixtures/clusters_oversize.json` — 1 cluster with 26 keywords
- [ ] `scripts/validate_clusters.py` — not yet created (Wave 1)

*(conftest.py and pytest infrastructure already exist from Phase 1)*

---

## Open Questions

1. **Narrow verticals with < 15 total keywords**
   - What we know: min cluster size 3; but if the whole ranked.json has 12 keywords, forcing 5-per-cluster means at most 4 clusters
   - What's unclear: should the size guards relax for small runs?
   - Recommendation: Document in skill prompt — if `total_keywords < 15`, skip the "target 5-15" constraint; min 3 is still enforced. Validator should receive `--small-run` flag to suppress `target_undersize` warnings.

2. **`theme` field in ranked.json is empty**
   - What we know: `rank_keywords.py` writes `"theme": ""` for every row
   - What's unclear: should Phase 4 backfill the `theme` field in ranked.json, or leave it empty and rely only on clusters.json?
   - Recommendation: Phase 4 writes theme into clusters.json only; do not mutate ranked.json. Downstream Phase 5 reads clusters.json directly.

---

## Sources

### Primary (HIGH confidence)
- Project PITFALLS.md Pitfalls 5, 10, 11, 12 — direct specification for all clustering invariants
- Project SUMMARY.md — confirmed LLM-driven clustering decision, sentence-transformers rejection
- Project STATE.md — confirmed decisions: LLM-driven v1, scikit-learn v2 fallback only
- `rank_keywords.py` source — confirmed ranked.json schema (exact field names, types, exit codes)
- Existing test infrastructure (`conftest.py`, `test_rank_keywords.py`) — confirms MODULE_MISSING pattern, fixture conventions

### Secondary (MEDIUM confidence)
- PITFALLS.md Pitfall 5 source: "Avoid Mixing Informational and Transactional Keywords in Google Ads" (2026) — Quality Score impact of mixed-intent ad groups
- PITFALLS.md Pitfall 10/11 sources: Google Ads clustering consolidation from STAG pattern (~2021+)

### Tertiary (LOW confidence)
- Optimal cluster count for narrow verticals (grocery vertical < 20 keywords) — extrapolated from general PPC consensus; needs real-run calibration

---

## Metadata

**Confidence breakdown:**
- clusters.json schema: HIGH — derived directly from existing ranked.json schema and project decisions
- validate_clusters.py spec: HIGH — all invariants explicitly stated in PITFALLS.md and focus brief
- Naming convention: HIGH — specified verbatim in focus brief, consistent with Pitfall 12 guidance
- Skill prompt pattern: HIGH — follows established SKILL.md step structure from Phases 2-3
- Test map: HIGH — follows existing project test patterns (MODULE_MISSING guard, conftest fixtures)

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (stable domain — no external library changes expected)
