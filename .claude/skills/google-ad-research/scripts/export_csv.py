# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""export_csv.py — Write Google Ads Editor v2.x importable CSVs (EXPT-01..04).

Reads:
    {run_dir}/ranked-enriched.json
    {run_dir}/clusters.json
    {run_dir}/negatives.json
    {run_dir}/brief.md

Writes:
    {run_dir}/export/positives.csv   — Campaign, Ad Group, Keyword,
                                       Match Type, Max CPC, Final URL
    {run_dir}/export/negatives.csv   — Campaign, Ad Group, Keyword,
                                       Match Type, Level
    {run_dir}/export/ad_groups.csv   — Campaign, Ad Group, Status,
                                       Default Max CPC

Byte contract (EXPT-04):
    UTF-8 (NOT utf-8-sig — no BOM), CRLF line endings, RFC 4180 quoting
    via csv.DictWriter with quoting=csv.QUOTE_MINIMAL.

CLI:
    uv run export_csv.py --run-dir <abs>

Stdout (one JSON line on success):
    {"positives_rows": N, "negatives_rows": N, "ad_groups_rows": N,
     "exports_dir": "<absolute path>"}

Exit codes:
    0  ok — all three CSVs written
    2  retryable (transient disk error — PermissionError / OSError on write)
    3  fatal (missing input file — ranked-enriched.json / clusters.json /
             negatives.json / brief.md)
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any

# --- Header contracts (EXPT-01..03) -----------------------------------------
# Locked in Wave 0 (plan 10-00); Wave 1 helpers write them via DictWriter.
POSITIVES_HEADERS: list[str] = [
    "Campaign", "Ad Group", "Keyword", "Match Type", "Max CPC", "Final URL",
]
NEGATIVES_HEADERS: list[str] = [
    "Campaign", "Ad Group", "Keyword", "Match Type", "Level",
]
AD_GROUPS_HEADERS: list[str] = [
    "Campaign", "Ad Group", "Status", "Default Max CPC",
]

# Tier → Level mapping (EXPT-02 / NEGT-* contract):
#   Strong tier      → campaign-level negative (Ad Group cell stays empty)
#   Considered tier  → ad_group-level negative (Ad Group = cluster name)
#   Investigate tier → ad_group-level negative (operator decides cluster)
TIER_TO_LEVEL: dict[str, str] = {
    "Strong": "campaign",
    "Considered": "ad_group",
    "Investigate": "ad_group",
}

# Internal taxonomy is lowercase (rank_keywords.py / Phase 3); Editor v2.x
# CSV format expects title-case. Convert at the write boundary only (Pitfall 5).
MATCH_TYPE_TITLECASE: dict[str, str] = {
    "phrase": "Phrase",
    "exact": "Exact",
    "broad": "Broad",
}

# Drift guards — fail fast at import if upstream taxonomies change.
assert frozenset(TIER_TO_LEVEL.keys()) == frozenset(
    {"Strong", "Considered", "Investigate"}
), "TIER_TO_LEVEL drift — Phase 6 tier taxonomy changed?"
assert frozenset(MATCH_TYPE_TITLECASE.keys()) == frozenset(
    {"phrase", "exact", "broad"}
), "MATCH_TYPE_TITLECASE drift — RANK-03 taxonomy changed?"

# Phase 14 POS-04 sentinel — flipped on once --include-existing flag + positives-sync
# filter lands. Wave 0 test skip-guards check this attr via getattr default-False.
_POSITIVES_SYNC_SUPPORTED = True


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _micros_to_csv_usd(micros: int | None) -> str:
    """Convert micros (USD × 1_000_000) to a CSV-friendly USD string.

    Differs from render_report._micros_to_usd which returns "—" for None;
    Editor rejects empty / dash numeric cells (Pitfall 10) so we emit "0.00".
    """
    if micros is None:
        return "0.00"
    return f"{micros / 1_000_000:.2f}"


def _titlecase_match_type(raw: str | None) -> str:
    """Title-case the internal lowercase match_type at the write boundary.

    Defensive: unknown / missing → "Phrase" (RANK-03 default).
    """
    if not raw:
        return "Phrase"
    return MATCH_TYPE_TITLECASE.get(raw.lower(), "Phrase")


def _load_brief_slug(run_dir: Path) -> str:
    """Derive a title-cased Campaign name from the run-dir name.

    Mirrors render_report._derive_brief_slug then title-cases each
    hyphen-separated token and rejoins with spaces.

    Example:
        2026-05-14T120000Z-phase-10-test-brief
          → slug "phase-10-test-brief"
          → "Phase 10 Test Brief"
    """
    name = run_dir.name
    # Timestamp prefix: YYYY-MM-DDTHHMMSSZ = 18 chars; the "-" at index 18.
    if len(name) > 18 and name[17] == "Z":
        slug = name[19:]
    else:
        slug = name
    if not slug:
        return ""
    return " ".join(part.title() for part in slug.split("-") if part)


def _load_ad_group_mapping(run_dir: Path) -> dict | None:
    """ADGM-05: Read ad-group-mapping.json (sidecar from ad_group_match.py).

    Returns None when absent or unparseable (backward compat — Phase 10 still
    works when no mapping has been computed for the run).
    """
    mapping_path = run_dir / "ad-group-mapping.json"
    if not mapping_path.exists():
        return None
    try:
        return json.loads(mapping_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_positives_sync(run_dir: Path) -> dict | None:
    """POS-04: Read positives-sync.json (sidecar from perf_synth.cross_ref_positives).

    Returns None when absent or unparseable (POS-05 graceful fallback — Phase 14
    only filters positives.csv when sync is available; otherwise emit the full
    ranked list per pre-Phase-14 behaviour).
    """
    sync_path = run_dir / "positives-sync.json"
    if not sync_path.exists():
        return None
    try:
        return json.loads(sync_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _resolve_ad_group_from_mapping(
    keyword: str,
    cluster_slug: str,
    mapping: dict | None,
) -> str:
    """ADGM-05: Return existing ad-group name for matched keyword; else cluster_slug.

    Match rule: case-sensitive keyword equality with a mapping.matches[] entry
    where confidence ∈ {high, medium} AND existing_ad_group is non-null. Preserves
    Unicode characters in existing_ad_group byte-for-byte (Pitfall 2).
    """
    if not mapping:
        return cluster_slug
    for match in mapping.get("matches", []) or []:
        if match.get("keyword") != keyword:
            continue
        if match.get("confidence") not in {"high", "medium"}:
            continue
        existing = match.get("existing_ad_group")
        if existing:
            return existing
        return cluster_slug
    return cluster_slug


def _existing_ad_group_names_in_mapping(mapping: dict | None) -> set[str]:
    """ADGM-05: Set of existing ad-group names with high/medium confidence.

    Used to filter ad_groups.csv — these ad groups already exist in the
    client's account, so emitting them again would trigger an Editor
    duplicate-name error on import.
    """
    if not mapping:
        return set()
    names: set[str] = set()
    for match in mapping.get("matches", []) or []:
        if match.get("confidence") not in {"high", "medium"}:
            continue
        name = match.get("existing_ad_group")
        if name:
            names.add(name)
    return names


def _build_cluster_index(clusters_data: dict) -> dict[str, str]:
    """Map keyword.lower() → cluster name (Pitfall 6 — verbatim cluster names).

    Mirrors render_report._build_cluster_index to keep the join contract
    consistent (lowercase keyword as the join key). Inline duplication is
    accepted because cross-importing render_report from a PEP 723 script
    breaks `uv run` invocation.
    """
    index: dict[str, str] = {}
    for cluster in clusters_data.get("clusters", []) or []:
        name = cluster.get("name", "")
        for kw_entry in cluster.get("keywords", []) or []:
            kw = (kw_entry.get("keyword") or "").lower()
            if kw:
                index[kw] = name
    return index


def _cluster_median_max_cpc_micros(
    cluster: dict,
    ranked_index: dict[str, dict],
) -> int | None:
    """Median suggested_max_cpc_micros across this cluster's keywords.

    Looks up each cluster keyword (lowercased) in ranked_index and collects
    non-null suggested_max_cpc_micros values. Returns int(median) or None
    when the cluster is empty or every keyword's suggested CPC is null.
    """
    micros_values: list[int] = []
    for kw_entry in cluster.get("keywords", []) or []:
        kw = (kw_entry.get("keyword") or "").lower()
        ranked_row = ranked_index.get(kw)
        if not ranked_row:
            continue
        m = ranked_row.get("suggested_max_cpc_micros")
        if m is not None:
            micros_values.append(int(m))
    if not micros_values:
        return None
    return int(statistics.median(micros_values))


# ---------------------------------------------------------------------------
# CSV writers (EXPT-01..04 byte contract)
# ---------------------------------------------------------------------------

def write_positives(path: Path, rows: list[dict], *, include_status: bool = False) -> None:
    """Write positives.csv (EXPT-01).

    Byte contract: UTF-8 no BOM (encoding='utf-8', NOT 'utf-8-sig'), CRLF
    via lineterminator='\\r\\n', newline='' on the open() call (Pitfall 1+2).
    csv.QUOTE_MINIMAL gives RFC 4180 quoting only when a cell contains a
    comma / quote / newline.

    rows: list of dicts with the six POSITIVES_HEADERS keys (plus an optional
    'Status' key when ``include_status`` is True — POS-04 --include-existing).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = POSITIVES_HEADERS + (["Status"] if include_status else [])
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=headers,
            lineterminator="\r\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_negatives(path: Path, rows: list[dict]) -> None:
    """Write negatives.csv (EXPT-02).

    Empty rows → header-only CSV (no crash, file still created — Pitfall 4).
    Same byte contract as write_positives.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=NEGATIVES_HEADERS,
            lineterminator="\r\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_ad_groups(path: Path, rows: list[dict]) -> None:
    """Write ad_groups.csv (EXPT-03).

    Same byte contract as write_positives.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=AD_GROUPS_HEADERS,
            lineterminator="\r\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def _build_positives_rows(
    ranked_enriched: list[dict],
    cluster_index: dict[str, str],
    campaign: str,
    mapping: dict | None = None,
    positives_sync: dict | None = None,
    include_existing: bool = False,
) -> list[dict]:
    """Build positives.csv rows from ranked-enriched rows joined to clusters.

    Iterate ranked-enriched in score-desc order (stable for ties). Skip rows
    whose keyword doesn't map to any cluster — orphans don't enter the
    campaign (Pitfall 6).

    ADGM-05: when `mapping` is supplied and a keyword has a high/medium-confidence
    match in the ad-group-mapping.json sidecar, substitute the existing
    ad-group name for the cluster slug in the Ad Group column. Backward compat:
    mapping=None → identical pre-Phase-11 output (cluster slug only).

    POS-04: when ``positives_sync`` is provided + ``include_existing=False``,
    filter rows to those whose keyword (case-insensitive) appears in
    ``sync['new_to_add']``. When ``include_existing=True``, emit all rows + a
    ``Status`` column tagging the bucket. When ``positives_sync`` is None,
    pre-Phase-14 behaviour (full list, no Status column).
    """
    # POS-04: build bucket-lookup table at function entry so per-row filtering
    # stays O(1). Buckets are checked in priority order so the priority chain
    # (ENABLED-exact > PAUSED-exact > BROAD-cover > new) is preserved if the
    # sync ever surfaces overlapping rows.
    bucket_by_kw: dict[str, str] = {}
    if positives_sync:
        for bucket_name in (
            "new_to_add",
            "already_active",
            "paused_in_account",
            "covered_by_broad",
        ):
            for r in positives_sync.get(bucket_name, []) or []:
                kw_lc = (r.get("keyword") or "").lower()
                if kw_lc and kw_lc not in bucket_by_kw:
                    bucket_by_kw[kw_lc] = bucket_name

    rows: list[dict] = []
    ordered = sorted(
        ranked_enriched, key=lambda r: r.get("score", 0) or 0, reverse=True
    )
    # _row_score: needed for the post-sort by ad group; track score per row
    # so the final sort can keep same-ad-group rows contiguous AND order
    # within each ad group by score desc.
    interim: list[tuple[str, float, dict]] = []
    for row in ordered:
        kw = (row.get("keyword") or "")
        cluster_slug = cluster_index.get(kw.lower())
        # ADGM-05: a mapping match overrides cluster assignment entirely —
        # mapped keywords belong in the existing client ad group even if our
        # clustering algorithm would have orphaned them.
        ag = _resolve_ad_group_from_mapping(kw, cluster_slug or "", mapping)
        if not ag:
            continue
        # POS-04 default-filter path: when sync present + flag NOT set, drop any
        # ranked row not in new_to_add (operator workflow ships only new kws to
        # paste into Editor — already-active / paused / broad-covered are skipped).
        bucket = bucket_by_kw.get(kw.lower()) if positives_sync else None
        if positives_sync and not include_existing:
            if bucket != "new_to_add":
                continue
        payload = {
            "Campaign": campaign,
            "Ad Group": ag,
            "Keyword": kw,
            "Match Type": _titlecase_match_type(row.get("match_type")),
            "Max CPC": _micros_to_csv_usd(row.get("suggested_max_cpc_micros")),
            "Final URL": "",
        }
        # POS-04 include-existing path: surface the bucket as a trailing column
        # so operator can see which kws are already_active / paused / covered.
        # Default to new_to_add when the kw isn't in the sync — defensive, but
        # signals the row may not have been processed by cross_ref_positives.
        if positives_sync and include_existing:
            payload["Status"] = bucket or "new_to_add"
        interim.append((
            ag,
            float(row.get("score", 0) or 0),
            payload,
        ))
    # Sort by (Ad Group asc, Score desc) so same-ad-group rows are contiguous
    # in the CSV — operator pastes one ad group's keywords together in Editor
    # without manual re-grouping. "Sort the keywords by the structure of ads
    # and ad groups we have" (team request, Phase 11 follow-up).
    interim.sort(key=lambda t: (t[0].lower(), -t[1]))
    for _ag, _sc, payload in interim:
        rows.append(payload)
    return rows


def _build_negatives_rows(
    negatives: list[dict],
    campaign: str,
) -> list[dict]:
    """Build negatives.csv rows. Empty negatives list → empty rows list."""
    rows: list[dict] = []
    for neg in negatives:
        tier = neg.get("tier", "Investigate")
        level = TIER_TO_LEVEL.get(tier, "ad_group")
        ad_group = "" if level == "campaign" else (neg.get("cluster") or "")
        rows.append({
            "Campaign": campaign,
            "Ad Group": ad_group,
            "Keyword": neg.get("keyword", ""),
            "Match Type": _titlecase_match_type(neg.get("match_type")),
            "Level": level,
        })
    return rows


def _build_ad_groups_rows(
    clusters_data: dict,
    ranked_index: dict[str, dict],
    campaign: str,
    mapping: dict | None = None,
) -> list[dict]:
    """Build ad_groups.csv rows — one per cluster, Status=Enabled.

    Default Max CPC = USD-formatted cluster-median of suggested_max_cpc_micros
    across the cluster's keywords. All-null cluster → "0.00" (Pitfall 10).

    ADGM-05: when `mapping` is supplied, skip cluster rows whose name matches
    an existing ad group from the mapping (high/medium confidence). This
    prevents Editor "Ad group already exists" duplicate-name errors on import.
    """
    existing_names = _existing_ad_group_names_in_mapping(mapping)
    rows: list[dict] = []
    for cluster in clusters_data.get("clusters", []) or []:
        name = cluster.get("name", "")
        if name in existing_names:
            continue  # ADGM-05: defer to the existing client ad group
        median_micros = _cluster_median_max_cpc_micros(cluster, ranked_index)
        rows.append({
            "Campaign": campaign,
            "Ad Group": name,
            "Status": "Enabled",
            "Default Max CPC": _micros_to_csv_usd(median_micros),
        })
    return rows


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI: export_csv --run-dir <path>.

    Reads ranked-enriched.json + clusters.json + negatives.json + brief.md
    from --run-dir, writes three Editor-importable CSVs to {run_dir}/export/.

    Returns:
        0  ok
        2  retryable disk error (PermissionError / OSError on write)
        3  fatal — missing input file or unparseable JSON
    """
    parser = argparse.ArgumentParser(
        prog="export_csv",
        description=(
            "Write Google Ads Editor v2.x importable CSVs "
            "(positives / negatives / ad_groups) to {run_dir}/export/."
        ),
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument(
        "--include-existing",
        action="store_true",
        default=False,
        help=(
            "POS-04: When positives-sync.json is present, by default "
            "positives.csv contains only new_to_add rows. Pass "
            "--include-existing to emit all ranked rows with an added Status "
            "column."
        ),
    )

    # argv[0]-skip heuristic — accept full sys.argv or args-only list.
    if argv is None:
        argv = sys.argv[1:]
    args_only = (
        argv[1:] if argv and not argv[0].startswith("-") else argv
    )
    args = parser.parse_args(args_only)

    run_dir: Path = args.run_dir
    if not run_dir.exists():
        print(
            f"export_csv: --run-dir does not exist: {run_dir}",
            file=sys.stderr,
        )
        return 3

    ranked_path = run_dir / "ranked-enriched.json"
    clusters_path = run_dir / "clusters.json"
    negatives_path = run_dir / "negatives.json"
    brief_path = run_dir / "brief.md"

    for p in (ranked_path, clusters_path, negatives_path, brief_path):
        if not p.exists():
            print(
                f"export_csv: missing required input: {p}", file=sys.stderr
            )
            return 3

    try:
        ranked_enriched: list[dict] = json.loads(
            ranked_path.read_text(encoding="utf-8")
        )
        clusters_data: dict[str, Any] = json.loads(
            clusters_path.read_text(encoding="utf-8")
        )
        negatives: list[dict] = json.loads(
            negatives_path.read_text(encoding="utf-8")
        )
        # brief.md not parsed for fields in v1 (only for slug derivation,
        # which comes from run_dir.name) — just confirm it exists above.
    except json.JSONDecodeError as exc:
        print(
            f"export_csv: failed to parse input JSON: {exc}",
            file=sys.stderr,
        )
        return 3
    except OSError as exc:
        print(
            f"export_csv: failed to read input file: {exc}", file=sys.stderr
        )
        return 2

    campaign = _load_brief_slug(run_dir)
    ranked_index: dict[str, dict] = {
        (r.get("keyword") or "").lower(): r for r in ranked_enriched
    }
    cluster_index = _build_cluster_index(clusters_data)
    # ADGM-05: ad-group-mapping.json is an optional sidecar. Absence is a
    # silent fallback to pre-Phase-11 cluster-slug behaviour (backward compat).
    mapping = _load_ad_group_mapping(run_dir)
    # POS-04 / POS-05: positives-sync.json is an optional sidecar. Absence is a
    # graceful fallback to pre-Phase-14 full-ranked-list behaviour.
    positives_sync = _load_positives_sync(run_dir)
    include_existing: bool = args.include_existing
    if positives_sync is None:
        filter_mode = "no_sync_full_list"
    elif include_existing:
        filter_mode = "include_existing"
    else:
        filter_mode = "new_to_add"

    positives_rows = _build_positives_rows(
        ranked_enriched, cluster_index, campaign, mapping=mapping,
        positives_sync=positives_sync, include_existing=include_existing,
    )
    negatives_rows = _build_negatives_rows(negatives, campaign)
    ad_groups_rows = _build_ad_groups_rows(
        clusters_data, ranked_index, campaign, mapping=mapping
    )

    exports_dir = run_dir / "export"
    positives_path = exports_dir / "positives.csv"
    negatives_csv_path = exports_dir / "negatives.csv"
    ad_groups_path = exports_dir / "ad_groups.csv"

    try:
        write_positives(
            positives_path,
            positives_rows,
            include_status=(filter_mode == "include_existing"),
        )
        write_negatives(negatives_csv_path, negatives_rows)
        write_ad_groups(ad_groups_path, ad_groups_rows)
    except (PermissionError, OSError) as exc:
        print(
            f"export_csv: failed to write CSV: {exc}", file=sys.stderr
        )
        return 2

    # Defensive: confirm all three files materialised before reporting success.
    for p in (positives_path, negatives_csv_path, ad_groups_path):
        if not p.exists():
            print(
                f"export_csv: expected CSV not written: {p}",
                file=sys.stderr,
            )
            return 2

    summary = {
        "positives_rows": len(positives_rows),
        "negatives_rows": len(negatives_rows),
        "ad_groups_rows": len(ad_groups_rows),
        "exports_dir": exports_dir.resolve().as_posix(),
        # ADGM-05 telemetry — silent fallback when no mapping was provided.
        "existing_ad_groups_used": len(
            _existing_ad_group_names_in_mapping(mapping)
        ),
        "new_ad_groups_emitted": len(ad_groups_rows),
        "mapping_coverage_pct": (
            mapping.get("mapping_coverage_pct") if mapping else None
        ),
        # POS-04 telemetry — filter mode applied to positives.csv.
        "positives_filter": filter_mode,
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
