# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bid_suggest.py — Add suggested_max_cpc_micros to ranked-enriched.json.

Implements:
    BIDS-01  cpc_micros × intent_multiplier as the base bid suggestion
    BIDS-02  Cluster-median CPC fallback when cpc_micros is null;
             null + no_cpc_data flag when cluster has no CPC data or
             keyword is orphaned
    BIDS-04  Tuning knobs (INTENT_MULTIPLIERS) live in ONE module-level
             dict at the top of this file. Frozenset assertion guards
             the 4-class rubric. No magic multipliers anywhere else.

UNIT CONTRACT (Pitfall 8):
    All CPC values are stored in micros (USD × 1,000,000). NEVER convert
    to USD inside this file — display conversion is render_report.py's
    job. Sanity: 250_000 micros × 1.2 = 300_000 micros = $0.30.

This module exposes:
    INTENT_MULTIPLIERS          (BIDS-04 tuning knobs)
    compute_suggested_cpc       (per-keyword bid math)
    cluster_median_cpc          (BIDS-02 fallback helper)
    enrich_with_bids            (top-level: ranked + clusters → enriched list)
    main_with_args              (CLI entrypoint — argv → exit code)

Reads:
    {run_dir}/ranked-enriched.json   (output of volume_enrich.py)
    {run_dir}/clusters.json          (output of validate_clusters.py)

Writes:
    {run_dir}/ranked-enriched.json   (additive: adds suggested_max_cpc_micros
                                      per row, plus no_cpc_data flag where
                                      neither row nor cluster has CPC data;
                                      all original keys preserved)

CLI:
    uv run bid_suggest.py --run-dir <abs>

Stdout (one JSON line):
    {"rows_enriched": N,
     "rows_with_cpc": N,
     "rows_using_fallback": N,
     "rows_no_cpc_data": N}

Exit codes:
    0  ok
    2  retryable (transient disk error)
    3  fatal (missing input, schema violation, malformed JSON)
"""
from __future__ import annotations

import argparse
import copy
import json
import statistics
import sys
from pathlib import Path
from typing import Any

# Make sibling lib/ importable (mirror volume_enrich.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.log import configure_logger  # noqa: E402

# --- Tuning knobs (BIDS-04) ---
# Edit values here; nothing else in this file uses literal multipliers.
INTENT_MULTIPLIERS: dict[str, float] = {
    "transactional": 1.2,
    "commercial":    0.8,
    "informational": 0.4,
    "navigational":  1.0,
}

# Sanity check: keys must match the 4-class rubric exactly.
_REQUIRED_INTENTS = frozenset(
    {"transactional", "commercial", "informational", "navigational"}
)
assert frozenset(INTENT_MULTIPLIERS) == _REQUIRED_INTENTS, (
    f"INTENT_MULTIPLIERS keys must match 4-class rubric: {_REQUIRED_INTENTS}"
)

log = configure_logger(__name__)


# ---------------------------------------------------------------------------
# Core compute (BIDS-01, BIDS-02)
# ---------------------------------------------------------------------------

def compute_suggested_cpc(
    cpc_micros: int | None,
    intent: str,
    cluster_median_micros: int | None,
) -> tuple[int | None, bool]:
    """Return (suggested_max_cpc_micros, used_fallback).

    Semantics:
        cpc_micros present                   → cpc_micros × multiplier, fallback=False
        cpc_micros null, cluster_median set  → cluster_median × multiplier, fallback=True
        both null                            → (None, True)  [signals no_cpc_data]
        unknown intent                       → (None, True)  [defensive]

    All math stays in micros; never convert to USD here (Pitfall 8).
    """
    multiplier = INTENT_MULTIPLIERS.get(intent)
    if multiplier is None:
        # Unknown / missing intent — emit null and flag.
        return (None, True)

    base_micros = cpc_micros if cpc_micros is not None else cluster_median_micros
    if base_micros is None:
        return (None, True)

    suggested = int(round(base_micros * multiplier))
    used_fallback = cpc_micros is None
    return (suggested, used_fallback)


def cluster_median_cpc(
    keyword_to_cluster: dict[str, str | None],
    cluster_to_keywords: dict[str, list[dict]],
    cluster_name: str | None,
) -> int | None:
    """Median CPC (in micros) across cluster siblings with non-null cpc_micros.

    Returns None when:
        - cluster_name is None (orphan keyword)
        - cluster has no rows registered
        - every sibling has cpc_micros = null (empty pool, Pitfall 2)
    """
    # The keyword_to_cluster argument is unused for the median compute itself,
    # but kept in the signature so callers can pass a single consistent set of
    # join-indices. It also documents the join contract.
    _ = keyword_to_cluster
    if cluster_name is None:
        return None
    siblings = cluster_to_keywords.get(cluster_name, [])
    cpcs = [
        row["cpc_micros"]
        for row in siblings
        if row.get("cpc_micros") is not None
    ]
    if not cpcs:
        return None
    return int(statistics.median(cpcs))


# ---------------------------------------------------------------------------
# Join-index helpers (Pitfall 6 — lower+strip casing)
# ---------------------------------------------------------------------------

def _build_keyword_to_cluster(clusters_data: dict) -> dict[str, str | None]:
    """Map keyword.lower().strip() → cluster name (None for orphans).

    Mirrors render_report.py's `_build_cluster_index` casing rules so the
    join between clusters.json and ranked-enriched.json never silently
    misses rows due to case/whitespace drift.
    """
    index: dict[str, str | None] = {}
    for cluster in clusters_data.get("clusters", []) or []:
        name = cluster.get("name")
        for kw in cluster.get("keywords", []) or []:
            key = (kw.get("keyword") or "").lower().strip()
            if key:
                index[key] = name
    # Register orphans explicitly with None (so .get returns None too,
    # but having them in the map makes presence checks honest).
    for kw in clusters_data.get("orphans", []) or []:
        key = (kw.get("keyword") or "").lower().strip()
        if key and key not in index:
            index[key] = None
    return index


def _build_cluster_to_keywords(
    clusters_data: dict,
    ranked: list[dict],
) -> dict[str, list[dict]]:
    """Map cluster name → list of ranked rows (with cpc_micros) in that cluster.

    We use the *ranked* rows (not the trimmed cluster keyword dicts) because
    clusters.json only stores keyword + score, while CPC data lives in
    ranked-enriched.json.
    """
    # Build a reverse index from cluster name → set of normalised keywords.
    cluster_keys: dict[str, set[str]] = {}
    for cluster in clusters_data.get("clusters", []) or []:
        name = cluster.get("name")
        if not name:
            continue
        keys = {
            (kw.get("keyword") or "").lower().strip()
            for kw in cluster.get("keywords", []) or []
        }
        keys.discard("")
        cluster_keys[name] = keys

    # Walk ranked rows once; bucket each into the cluster it belongs to.
    result: dict[str, list[dict]] = {name: [] for name in cluster_keys}
    for row in ranked:
        norm = (row.get("keyword") or "").lower().strip()
        for name, keys in cluster_keys.items():
            if norm in keys:
                result[name].append(row)
                break
    return result


# ---------------------------------------------------------------------------
# Public enrichment API (BIDS-01 + BIDS-02 combined)
# ---------------------------------------------------------------------------

def enrich_with_bids(
    ranked_enriched: list[dict],
    clusters_data: dict,
) -> list[dict]:
    """Return a NEW list with suggested_max_cpc_micros added to every row.

    Does NOT mutate the input list or its rows. Rows where the fallback
    path produced None additionally carry `no_cpc_data: True`.
    """
    keyword_to_cluster = _build_keyword_to_cluster(clusters_data)
    cluster_to_keywords = _build_cluster_to_keywords(clusters_data, ranked_enriched)

    out: list[dict] = []
    for original in ranked_enriched:
        row = copy.deepcopy(original)
        key = (row.get("keyword") or "").lower().strip()
        cluster_name = keyword_to_cluster.get(key)  # None if orphan / unknown
        cm = cluster_median_cpc(
            keyword_to_cluster, cluster_to_keywords, cluster_name
        )
        sugg, _used_fallback = compute_suggested_cpc(
            row.get("cpc_micros"),
            row.get("intent", "") or "",
            cm,
        )
        row["suggested_max_cpc_micros"] = sugg
        if sugg is None:
            row["no_cpc_data"] = True
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main_with_args(argv: list[str]) -> int:
    """CLI: bid_suggest --run-dir <path>.

    Reads {run_dir}/ranked-enriched.json + {run_dir}/clusters.json,
    enriches each row with suggested_max_cpc_micros (additive — original
    keys preserved), writes the result back to ranked-enriched.json.

    Exit codes:
        0  ok
        2  retryable (transient disk error)
        3  fatal (missing input, malformed JSON, schema violation)
    """
    parser = argparse.ArgumentParser(
        prog="bid_suggest",
        description=(
            "Add suggested_max_cpc_micros to ranked-enriched.json "
            "using BIDS-01/02/04."
        ),
    )
    parser.add_argument("--run-dir", required=True, type=Path)

    # argv[0]-skip heuristic — matches serp_fetch.py / volume_enrich.py.
    # Accept either full sys.argv (e.g., ["bid_suggest.py", "--run-dir", ...])
    # or an args-only list (e.g., ["--run-dir", ...]).
    args_only = (
        argv[1:] if argv and not argv[0].startswith("-") else argv
    )
    args = parser.parse_args(args_only)

    run_dir: Path = args.run_dir
    if not run_dir.exists():
        log.error("--run-dir does not exist: %s", run_dir)
        return 3

    ranked_path = run_dir / "ranked-enriched.json"
    clusters_path = run_dir / "clusters.json"

    if not ranked_path.exists():
        log.error(
            "ranked-enriched.json not found at %s — "
            "Phase 9 requires Phase 8 (volume_enrich.py) to have run.",
            ranked_path,
        )
        return 3
    if not clusters_path.exists():
        log.error("clusters.json not found at %s", clusters_path)
        return 3

    try:
        ranked: list[dict] = json.loads(
            ranked_path.read_text(encoding="utf-8")
        )
        clusters_data: dict[str, Any] = json.loads(
            clusters_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        log.error("Failed to parse input JSON: %s", exc)
        return 3
    except OSError as exc:
        log.error("Failed to read input file: %s", exc)
        return 2

    enriched = enrich_with_bids(ranked, clusters_data)

    # Atomic-ish write: write to .tmp then rename.
    try:
        tmp = ranked_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(enriched, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(ranked_path)
    except OSError as exc:
        log.error("Failed to write ranked-enriched.json: %s", exc)
        return 2

    summary = {
        "rows_enriched": len(enriched),
        "rows_with_cpc": sum(
            1 for r in enriched if r.get("cpc_micros") is not None
        ),
        "rows_using_fallback": sum(
            1
            for r in enriched
            if r.get("suggested_max_cpc_micros") is not None
            and r.get("cpc_micros") is None
        ),
        "rows_no_cpc_data": sum(1 for r in enriched if r.get("no_cpc_data")),
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv))
