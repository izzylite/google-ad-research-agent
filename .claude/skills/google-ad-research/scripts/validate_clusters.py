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


def check_clusters(
    clusters: list[dict],
    ranked_index: dict[str, str],
    small_run: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Returns (hard_violations, warnings).

    Args:
        clusters: List of cluster dicts from clusters.json["clusters"].
        ranked_index: Mapping of keyword -> intent from ranked.json (source of truth).
        small_run: If True, suppress target_undersize warnings (for narrow verticals).
    """
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
            if not small_run:
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


def check_orphans(clusters_data: dict) -> list[dict]:
    """Returns orphan warnings if clusters_data["orphans"] is non-empty."""
    return (
        [{"type": "orphans", "count": len(clusters_data.get("orphans", []))}]
        if clusters_data.get("orphans")
        else []
    )


def check_avg_size(clusters: list[dict]) -> list[dict]:
    """Returns avg_size_low warning when average cluster size < TARGET_MIN."""
    if not clusters:
        return []
    total_kws = sum(len(c.get("keywords", [])) for c in clusters)
    avg = total_kws / len(clusters)
    if avg < TARGET_MIN:
        return [{"type": "avg_size_low", "avg_size": round(avg, 2)}]
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate clusters.json against ranked.json invariants.",
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="Absolute path to the run folder containing clusters.json and ranked.json.",
    )
    parser.add_argument(
        "--clusters-file",
        type=Path,
        default=None,
        help="Override path to clusters.json (default: {run_dir}/clusters.json).",
    )
    parser.add_argument(
        "--small-run",
        action="store_true",
        default=False,
        help="Suppress target_undersize warnings for narrow verticals (< 15 keywords).",
    )
    args = parser.parse_args()

    run_dir: Path = args.run_dir
    clusters_path: Path = args.clusters_file if args.clusters_file else run_dir / "clusters.json"
    ranked_path: Path = run_dir / "ranked.json"

    # Load files — exit 2 on infra errors
    try:
        if not run_dir.exists():
            print(json.dumps({"valid": False, "error": f"--run-dir does not exist: {run_dir}"}))
            sys.exit(2)
        if not clusters_path.exists():
            print(json.dumps({"valid": False, "error": f"clusters.json not found: {clusters_path}"}))
            sys.exit(2)
        if not ranked_path.exists():
            print(json.dumps({"valid": False, "error": f"ranked.json not found: {ranked_path}"}))
            sys.exit(2)

        clusters_json: dict = json.loads(clusters_path.read_text(encoding="utf-8"))
        ranked_json: list[dict] = json.loads(ranked_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(json.dumps({"valid": False, "error": f"JSON parse error: {exc}"}))
        sys.exit(2)
    except OSError as exc:
        print(json.dumps({"valid": False, "error": f"IO error: {exc}"}))
        sys.exit(2)

    # Build ranked_index: keyword -> intent (source of truth)
    ranked_index: dict[str, str] = {row["keyword"]: row["intent"] for row in ranked_json}

    # Orphan check: keywords in ranked.json not assigned to any cluster
    clustered_keywords: set[str] = {
        kw["keyword"]
        for c in clusters_json.get("clusters", [])
        for kw in c.get("keywords", [])
    }
    file_orphans = [kw for kw in ranked_index if kw not in clustered_keywords]
    if file_orphans:
        # Merge into clusters_json orphans so check_orphans picks them up
        existing_orphans = clusters_json.get("orphans", [])
        clusters_json["orphans"] = list({*existing_orphans, *file_orphans})

    # Run invariant checks
    hard, warn = check_clusters(
        clusters_json.get("clusters", []),
        ranked_index,
        small_run=args.small_run,
    )
    orphan_warnings = check_orphans(clusters_json)
    avg_warnings = check_avg_size(clusters_json.get("clusters", []))

    all_warnings = warn + orphan_warnings + avg_warnings
    all_violations = hard + all_warnings

    orphan_count = len(clusters_json.get("orphans", []))
    cluster_count = len(clusters_json.get("clusters", []))
    # `valid` reflects hard-violation status only; warnings still allow downstream use.
    is_valid = len(hard) == 0
    has_warnings = len(all_warnings) > 0

    result = {
        "valid": is_valid,
        "warnings": has_warnings,
        "cluster_count": cluster_count,
        "orphan_count": orphan_count,
        "hard_violations": hard,
        "warnings_list": all_warnings,
    }
    print(json.dumps(result))

    if hard:
        sys.exit(3)
    elif all_warnings:
        sys.exit(1)
    else:
        sys.exit(0)
