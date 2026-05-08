# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "tabulate>=0.9.0",
#     "python-dotenv>=1.0",
# ]
# ///
"""render_report.py — Assembles report.md + report.json from all upstream JSONs.

Reads:
  {run_dir}/brief.md
  {run_dir}/ranked.json
  {run_dir}/clusters.json
  {run_dir}/negatives.json
  {run_dir}/raw/competitor-intel.json  (optional)

Writes:
  {run_dir}/report.md
  {run_dir}/report.json

Exports: render_full_report(), build_report_json()
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from tabulate import tabulate

from lib.io import escape_md_cell

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOW_TO_READ = """\
## How to Read This Report

**signal_count** is the number of source-data fragments that mentioned this keyword.
It is NOT search volume. Do not treat a higher signal_count as "more searches per month."

**source_diversity** is the number of distinct signal sources (WebSearch, Serper organic,
Serper PAA, Serper related, Tavily) that surfaced the keyword. Higher diversity = more
reliable signal. The ranking is primarily sorted by source_diversity.

To estimate actual search volume, paste the keyword list into Google Keyword Planner.
"""

TIER_ORDER = ["Strong", "Considered", "Investigate"]

TIER_DESCRIPTIONS = {
    "Strong": "Add to all campaigns unconditionally.",
    "Considered": "Add if brand is premium-positioned; review before adding for value-tier brands.",
    "Investigate": "Needs operator review — may be valid traffic depending on campaign goal.",
}


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def render_keyword_table(ranked: list[dict], top_n: int = 100) -> str:
    """Render ranked keywords as a GFM pipe table using tabulate."""
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
    headers = ["Keyword", "Intent", "Match Type", "Signals", "Src Div", "Score"]
    return tabulate(rows, headers=headers, tablefmt="github")


def render_clusters_section(clusters_data: dict) -> str:
    """Render the Ad Group Clusters section."""
    parts = ["## Ad Group Clusters\n"]
    clusters = clusters_data.get("clusters", [])
    for cluster in clusters:
        name = escape_md_cell(cluster.get("name", ""))
        parts.append(f"\n### {name}\n")
        for kw_entry in cluster.get("keywords", []):
            kw = escape_md_cell(kw_entry["keyword"])
            parts.append(f"- {kw}\n")
    return "".join(parts)


def render_competitor_section(competitor_intel: dict) -> str:
    """Render the Competitor Ad Copy section."""
    parts = ["## Competitor Ad Copy\n"]
    clusters = competitor_intel.get("clusters", {})
    if not clusters:
        parts.append("\nNo competitor ad copy extracted for this run.\n")
        return "".join(parts)

    for cluster_name, cluster_data in clusters.items():
        escaped_name = escape_md_cell(cluster_name)
        parts.append(f"\n### {escaped_name}\n")
        ads = cluster_data.get("ads", [])
        advertisers = cluster_data.get("advertisers", [])
        # Prefer advertisers (richer data) if available, else fall back to ads
        if advertisers:
            for adv in advertisers:
                title = escape_md_cell(adv.get("ad_title", ""))
                desc = escape_md_cell(adv.get("ad_description", ""))
                domain = escape_md_cell(adv.get("domain", ""))
                parts.append(f"- **{title}**\n")
                if desc:
                    parts.append(f"  - {desc}\n")
                if domain:
                    parts.append(f"  - Domain: {domain}\n")
        elif ads:
            for ad in ads:
                title = escape_md_cell(ad.get("title", ""))
                desc = escape_md_cell(ad.get("description", ""))
                parts.append(f"- **{title}**\n")
                if desc:
                    parts.append(f"  - {desc}\n")
    return "".join(parts)


def render_negatives_section(negatives: list[dict]) -> str:
    """Render the Negative Keywords section with Strong/Considered/Investigate tiers."""
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_cluster_index(clusters_data: dict) -> dict[str, str]:
    """Return mapping of keyword.lower() -> cluster_name for cluster_id lookup."""
    index: dict[str, str] = {}
    for cluster in clusters_data.get("clusters", []):
        name = cluster.get("name", "")
        for kw_entry in cluster.get("keywords", []):
            kw = kw_entry.get("keyword", "")
            index[kw.lower()] = name
    return index


def _parse_brief_fields(brief_text: str) -> dict[str, str]:
    """Extract industry, product, location, language, audience from brief.md markdown.

    Looks for "**Field:** value" pattern (case-insensitive field matching).
    """
    fields = ["industry", "product", "location", "language", "audience"]
    result: dict[str, str] = {}
    for line in brief_text.splitlines():
        m = re.search(r"\*\*(\w+)\*\*:\s*(.+)", line)
        if m:
            key = m.group(1).lower()
            value = m.group(2).strip()
            if key in fields:
                result[key] = value
    return result


def _derive_brief_slug(run_dir: Path) -> str:
    """Extract brief slug from run directory name.

    run_dir.name format: "2026-05-08T143024Z-grocery-delivery-uk"
    Slug is everything after the 18-char timestamp prefix.
    """
    name = run_dir.name
    # Timestamp format: YYYY-MM-DDTHHMMSSZ = 18 chars
    if len(name) > 18 and name[17] == "Z":
        return name[19:]  # skip "Z-" separator
    return name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_full_report(
    ranked: list[dict],
    clusters_data: dict,
    competitor_intel: dict,
    negatives: list[dict],
    brief_text: str,
    run_dir: Path,
    *,
    top_n: int = 100,
) -> str:
    """Return full report.md content as a string."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    brief_slug = _derive_brief_slug(run_dir)

    header = (
        f"# Keyword Research Report\n\n"
        f"**Run:** {run_dir.name}  \n"
        f"**Generated:** {generated_at}  \n"
        f"**Brief slug:** {brief_slug}  \n\n"
    )

    sections = [
        header,
        HOW_TO_READ,
        "\n## Ranked Keywords\n\n",
        render_keyword_table(ranked, top_n=top_n),
        "\n\n",
        render_clusters_section(clusters_data),
        "\n",
        render_competitor_section(competitor_intel),
        "\n",
        render_negatives_section(negatives),
    ]
    return "".join(sections)


def build_report_json(
    ranked: list[dict],
    clusters_data: dict,
    competitor_intel: dict,
    negatives: list[dict],
    brief_text: str,
    run_dir: Path,
) -> dict:
    """Return canonical v1 report.json dict (not serialized)."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    brief_slug = _derive_brief_slug(run_dir)
    run_id = f"{run_dir.name}"

    cluster_index = _build_cluster_index(clusters_data)
    brief_fields = _parse_brief_fields(brief_text)

    # Enrich keywords with cluster_id (do NOT mutate originals)
    enriched_keywords = []
    for kw in ranked:
        cluster_id = cluster_index.get(kw["keyword"].lower()) or None
        enriched_keywords.append({**kw, "cluster_id": cluster_id})

    return {
        "meta": {
            "run_id": run_id,
            "brief_slug": brief_slug,
            "generated_at": generated_at,
            "version": "v1",
        },
        "brief": {
            "industry": brief_fields.get("industry", ""),
            "product": brief_fields.get("product", ""),
            "location": brief_fields.get("location", ""),
            "language": brief_fields.get("language", ""),
            "audience": brief_fields.get("audience", ""),
        },
        "keywords": enriched_keywords,
        "clusters": clusters_data.get("clusters", []),
        "competitor_intel": competitor_intel,
        "negatives": negatives,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Accepts optional argv for testability."""
    parser = argparse.ArgumentParser(
        description="Render report.md and report.json from a research run directory."
    )
    parser.add_argument("--run-dir", required=True, type=Path,
                        help="Path to the research run directory.")
    parser.add_argument("--top-n", type=int, default=100,
                        help="Maximum number of keywords to include in the ranked table.")
    args = parser.parse_args(argv)
    run_dir: Path = args.run_dir

    # Validate required files — exit 3 if any are missing
    required_files = ["ranked.json", "clusters.json", "negatives.json", "brief.md"]
    for name in required_files:
        if not (run_dir / name).exists():
            print(f"ERROR: {name} not found in {run_dir}", file=sys.stderr)
            return 3

    # Load required inputs
    try:
        ranked = json.loads((run_dir / "ranked.json").read_text(encoding="utf-8"))
        clusters_data = json.loads((run_dir / "clusters.json").read_text(encoding="utf-8"))
        negatives = json.loads((run_dir / "negatives.json").read_text(encoding="utf-8"))
        brief_text = (run_dir / "brief.md").read_text(encoding="utf-8")
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Failed to load required input: {exc}", file=sys.stderr)
        return 3

    # Load optional competitor intel
    ci_path = run_dir / "raw" / "competitor-intel.json"
    if ci_path.exists():
        try:
            competitor_intel = json.loads(ci_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            competitor_intel = {}
    else:
        competitor_intel = {}

    # Render
    report_md = render_full_report(
        ranked, clusters_data, competitor_intel, negatives,
        brief_text, run_dir, top_n=args.top_n,
    )
    report_json = build_report_json(
        ranked, clusters_data, competitor_intel, negatives,
        brief_text, run_dir,
    )

    # Write outputs (LF newlines, utf-8)
    (run_dir / "report.md").write_text(report_md, encoding="utf-8", newline="\n")
    (run_dir / "report.json").write_text(
        json.dumps(report_json, indent=2), encoding="utf-8", newline="\n"
    )

    print(json.dumps({
        "report_md": str(run_dir / "report.md"),
        "report_json": str(run_dir / "report.json"),
        "keywords_in_report": len(ranked),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
