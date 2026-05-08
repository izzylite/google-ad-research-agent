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


def render_niche_pulse_section(pulse: dict) -> str:
    """Render the Niche Pulse section (markdown).

    pulse is the niche-pulse.json dict produced by pulse_synth.py. Empty / missing
    pulse renders a stub note.
    """
    if not pulse or not isinstance(pulse, dict):
        return ""
    parts = ["## Niche Pulse — last "
             f"{pulse.get('horizon_days', 7)} days "
             f"(captured {pulse.get('captured_at', 'n/a')})\n"]
    parts.append(
        f"\n_News-derived signals across "
        f"{pulse.get('total_news_items', 0)} headlines. "
        f"Time-sensitive — shelf life days to weeks. NOT merged into the "
        f"main keyword ranking._\n"
    )

    themes = pulse.get("trending_themes", [])
    parts.append(f"\n### Trending Themes ({len(themes)})\n")
    if not themes:
        parts.append("\n_No repeated themes surfaced in the harvest window._\n")
    else:
        for t in themes[:15]:
            theme = escape_md_cell(t.get("theme", ""))
            count = t.get("mention_count", 0)
            first = t.get("first_seen", "—")
            sources = ", ".join(t.get("sources", []))
            parts.append(f"\n- **{theme}** — {count} mentions · first seen {first} · sources: {sources}\n")
            for h in t.get("headlines", [])[:3]:
                title = escape_md_cell(h.get("title", ""))
                date = h.get("date") or ""
                parts.append(f"    - _{date}_ {title}\n")

    reg = pulse.get("regulatory_alerts", [])
    parts.append(f"\n### Regulatory Alerts ({len(reg)})\n")
    if not reg:
        parts.append("\n_No regulatory keywords detected._\n")
    else:
        for r in reg[:10]:
            title = escape_md_cell(r.get("title", ""))
            date = r.get("date") or ""
            kws = ", ".join(r.get("matched_keywords", []))
            parts.append(f"\n- _{date}_ **{title}** — matched: `{kws}`\n")

    comp = pulse.get("competitor_news", [])
    parts.append(f"\n### Competitor News ({len(comp)})\n")
    if not comp:
        parts.append("\n_No competitor brand mentions in the news harvest._\n")
    else:
        for c in comp[:10]:
            title = escape_md_cell(c.get("title", ""))
            brand = c.get("matched_brand", "")
            date = c.get("date") or ""
            parts.append(f"\n- _{date}_ **{title}** — brand: `{brand}`\n")

    negs = pulse.get("trending_negatives", [])
    parts.append(f"\n### Trending Negative Candidates ({len(negs)})\n")
    if not negs:
        parts.append("\n_No scam/fraud/lawsuit triggers in the news window._\n")
    else:
        for n in negs[:10]:
            title = escape_md_cell(n.get("title", ""))
            trig = ", ".join(n.get("trigger_keywords", []))
            parts.append(f"\n- **{title}** — triggers: `{trig}`\n")

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
    niche_pulse: dict | None = None,
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
    pulse_md = render_niche_pulse_section(niche_pulse or {})
    if pulse_md:
        sections.append("\n")
        sections.append(pulse_md)
    return "".join(sections)


def render_html_report(report_json: dict) -> str:
    """Return self-contained HTML report (no external CDN/network deps).

    Embeds report_json as a JS object so the page can offer CSV export of
    every section without round-tripping back to disk.
    """
    payload = json.dumps(report_json, ensure_ascii=False)
    meta = report_json.get("meta", {})
    brief = report_json.get("brief", {})
    title = f"Keyword Research — {meta.get('brief_slug', '')}"

    return _HTML_TEMPLATE.format(
        title=_html_escape(title),
        run_id=_html_escape(meta.get("run_id", "")),
        generated_at=_html_escape(meta.get("generated_at", "")),
        brief_slug=_html_escape(meta.get("brief_slug", "")),
        industry=_html_escape(brief.get("industry", "")),
        product=_html_escape(brief.get("product", "")),
        location=_html_escape(brief.get("location", "")),
        language=_html_escape(brief.get("language", "")),
        audience=_html_escape(brief.get("audience", "")),
        version=_html_escape(meta.get("version", "v1")),
        payload_json=payload,
    )


def _html_escape(s: str) -> str:
    """Minimal HTML escape for text content + attribute values."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       margin: 0; padding: 0; background: #f7f7f9; color: #1a1a1a; line-height: 1.5; }}
header {{ background: #1f2937; color: #fff; padding: 24px 32px; }}
header h1 {{ margin: 0 0 4px; font-size: 22px; }}
header .meta {{ font-size: 13px; opacity: 0.85; }}
main {{ max-width: 1280px; margin: 0 auto; padding: 24px 32px 64px; }}
.brief-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
              gap: 12px; background: #fff; padding: 16px; border-radius: 8px;
              box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 24px; }}
.brief-grid div {{ font-size: 13px; }}
.brief-grid label {{ font-weight: 600; color: #555; display: block; font-size: 11px;
                   text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }}
section {{ background: #fff; padding: 20px; border-radius: 8px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 20px; }}
section h2 {{ margin: 0 0 12px; font-size: 18px; border-bottom: 2px solid #e5e7eb;
             padding-bottom: 8px; }}
.disclaimer {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px;
              font-size: 13px; margin-bottom: 16px; border-radius: 4px; }}
.toolbar {{ display: flex; gap: 8px; align-items: center; margin-bottom: 12px;
           flex-wrap: wrap; }}
.toolbar input {{ flex: 1; min-width: 220px; padding: 6px 10px; border: 1px solid #d1d5db;
                 border-radius: 4px; font-size: 13px; }}
.toolbar button {{ padding: 6px 12px; background: #2563eb; color: #fff; border: none;
                  border-radius: 4px; font-size: 13px; cursor: pointer; }}
.toolbar button:hover {{ background: #1d4ed8; }}
.toolbar .count {{ font-size: 12px; color: #666; margin-left: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f3f4f6; cursor: pointer; user-select: none; position: sticky; top: 0; }}
th:hover {{ background: #e5e7eb; }}
th.sort-asc::after {{ content: " ▲"; }}
th.sort-desc::after {{ content: " ▼"; }}
tbody tr:hover {{ background: #f9fafb; }}
.intent-tag {{ display: inline-block; padding: 1px 8px; border-radius: 10px;
              font-size: 11px; font-weight: 600; }}
.intent-transactional {{ background: #d1fae5; color: #065f46; }}
.intent-commercial    {{ background: #dbeafe; color: #1e40af; }}
.intent-informational {{ background: #fef3c7; color: #92400e; }}
.intent-navigational  {{ background: #f3e8ff; color: #6b21a8; }}
.tier-Strong      {{ background: #fee2e2; color: #991b1b; padding: 1px 8px;
                    border-radius: 10px; font-size: 11px; font-weight: 600; }}
.tier-Considered  {{ background: #fef3c7; color: #92400e; padding: 1px 8px;
                    border-radius: 10px; font-size: 11px; font-weight: 600; }}
.tier-Investigate {{ background: #e0e7ff; color: #3730a3; padding: 1px 8px;
                    border-radius: 10px; font-size: 11px; font-weight: 600; }}
details {{ margin: 8px 0; }}
details summary {{ cursor: pointer; font-weight: 600; padding: 8px;
                  background: #f3f4f6; border-radius: 4px; }}
details summary:hover {{ background: #e5e7eb; }}
details ul {{ margin: 8px 16px; padding-left: 16px; }}
details li {{ font-size: 13px; padding: 2px 0; }}
.cluster-meta {{ font-size: 11px; color: #666; font-weight: normal; margin-left: 8px; }}
code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 3px;
       font-size: 12px; font-family: ui-monospace, SFMono-Regular, monospace; }}
</style>
</head>
<body>
<header>
  <h1>Keyword Research Report</h1>
  <div class="meta">{run_id} · Generated {generated_at} · Schema {version}</div>
</header>
<main>

<div class="brief-grid">
  <div><label>Industry</label>{industry}</div>
  <div><label>Product</label>{product}</div>
  <div><label>Location</label>{location}</div>
  <div><label>Language</label>{language}</div>
  <div><label>Audience</label>{audience}</div>
  <div><label>Brief Slug</label><code>{brief_slug}</code></div>
</div>

<div class="disclaimer">
<strong>How to read this:</strong> <code>signal_count</code> is NOT search volume —
it counts how many source fragments mentioned the keyword.
<code>source_diversity</code> is the number of distinct signal sources (WebSearch,
Serper organic / PAA / related / ads, Tavily) that surfaced it. The ranking is
primarily sorted by <code>source_diversity</code>. Paste keywords into Google
Keyword Planner for actual volume + CPC.
</div>

<section>
  <h2>Ranked Keywords</h2>
  <div class="toolbar">
    <input id="kwFilter" placeholder="Filter keywords (case-insensitive)…">
    <select id="intentFilter">
      <option value="">All intents</option>
      <option value="transactional">transactional</option>
      <option value="commercial">commercial</option>
      <option value="informational">informational</option>
      <option value="navigational">navigational</option>
    </select>
    <button onclick="exportCSV('keywords')">Export CSV</button>
    <span class="count" id="kwCount"></span>
  </div>
  <table id="kwTable">
    <thead>
      <tr>
        <th data-sort="string">Keyword</th>
        <th data-sort="string">Intent</th>
        <th data-sort="string">Match Type</th>
        <th data-sort="string">Cluster</th>
        <th data-sort="number">Signals</th>
        <th data-sort="number">Src Div</th>
        <th data-sort="number">Score</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
</section>

<section>
  <h2>Ad Group Clusters</h2>
  <div class="toolbar">
    <button onclick="exportCSV('clusters')">Export CSV</button>
    <span class="count" id="clusterCount"></span>
  </div>
  <div id="clustersList"></div>
</section>

<section>
  <h2>Competitor Ad Copy</h2>
  <div id="competitorList"></div>
</section>

<section id="niche-pulse">
  <h2>Niche Pulse <span class="cluster-meta" id="pulseMeta"></span></h2>
  <div id="pulseContent">
    <p style="color:#666;font-size:13px;">No niche-pulse.json found in this run — run Phase 7 (pulse_fetch + pulse_synth) to populate.</p>
  </div>
</section>

<section>
  <h2>Negative Keywords</h2>
  <div class="toolbar">
    <input id="negFilter" placeholder="Filter negatives…">
    <select id="negTierFilter">
      <option value="">All tiers</option>
      <option value="Strong">Strong</option>
      <option value="Considered">Considered</option>
      <option value="Investigate">Investigate</option>
    </select>
    <button onclick="exportCSV('negatives')">Export CSV</button>
    <span class="count" id="negCount"></span>
  </div>
  <table id="negTable">
    <thead>
      <tr>
        <th data-sort="string">Keyword</th>
        <th data-sort="string">Tier</th>
        <th data-sort="string">Category</th>
        <th data-sort="string">Justification</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
</section>

</main>

<script>
const REPORT = {payload_json};

function htmlEscape(s) {{
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}}

function renderKeywords() {{
  const tbody = document.querySelector("#kwTable tbody");
  const filter = document.getElementById("kwFilter").value.toLowerCase();
  const intent = document.getElementById("intentFilter").value;
  let rows = REPORT.keywords || [];
  if (filter)  rows = rows.filter(r => (r.keyword||"").toLowerCase().includes(filter));
  if (intent)  rows = rows.filter(r => r.intent === intent);
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${{htmlEscape(r.keyword)}}</td>
      <td><span class="intent-tag intent-${{r.intent}}">${{r.intent}}</span></td>
      <td>${{r.match_type}}</td>
      <td>${{r.cluster_id ? `<code>${{r.cluster_id}}</code>` : ""}}</td>
      <td>${{r.signal_count}}</td>
      <td>${{r.source_diversity}}</td>
      <td>${{r.score}}</td>
    </tr>`).join("");
  document.getElementById("kwCount").textContent = `${{rows.length}} of ${{(REPORT.keywords||[]).length}} keywords`;
}}

function renderClusters() {{
  const target = document.getElementById("clustersList");
  const clusters = REPORT.clusters || [];
  target.innerHTML = clusters.map(c => `
    <details>
      <summary>${{htmlEscape(c.name)}}<span class="cluster-meta">${{(c.keywords||[]).length}} keywords · ${{c.intent}}</span></summary>
      <ul>${{(c.keywords||[]).map(k => `<li>${{htmlEscape(k.keyword)}} <span class="cluster-meta">score ${{k.score}}</span></li>`).join("")}}</ul>
    </details>`).join("");
  document.getElementById("clusterCount").textContent = `${{clusters.length}} clusters`;
}}

function renderCompetitors() {{
  const target = document.getElementById("competitorList");
  const ci = (REPORT.competitor_intel || {{}}).clusters || {{}};
  const entries = Object.entries(ci);
  if (!entries.length) {{
    target.innerHTML = "<p style='color:#666;font-size:13px;'>No competitor ad copy extracted for this run.</p>";
    return;
  }}
  target.innerHTML = entries.map(([name, data]) => {{
    const ads = data.ads || [];
    const advs = data.advertisers || [];
    if (!ads.length && !advs.length) return "";
    const items = (advs.length ? advs : ads).map(a => `
      <li><strong>${{htmlEscape(a.ad_title || a.title || a.domain || "")}}</strong>
          ${{a.ad_description || a.description ? "<br><span>"+htmlEscape(a.ad_description||a.description)+"</span>" : ""}}
          ${{a.domain ? "<br><code>"+htmlEscape(a.domain)+"</code>" : ""}}
      </li>`).join("");
    return `<details><summary>${{htmlEscape(name)}}<span class="cluster-meta">${{ads.length}} ads · ${{advs.length}} advertisers</span></summary><ul>${{items}}</ul></details>`;
  }}).join("");
}}

function renderNichePulse() {{
  const pulse = REPORT.niche_pulse || {{}};
  const meta = document.getElementById("pulseMeta");
  const content = document.getElementById("pulseContent");
  if (!pulse || !pulse.captured_at) {{
    return;  // keep stub message
  }}
  meta.textContent = `last ${{pulse.horizon_days||7}} days · ${{pulse.total_news_items||0}} headlines · captured ${{pulse.captured_at}}`;
  const themes = pulse.trending_themes || [];
  const reg = pulse.regulatory_alerts || [];
  const comp = pulse.competitor_news || [];
  const negs = pulse.trending_negatives || [];

  let html = "";
  // Trending themes
  html += `<details open><summary>Trending Themes <span class="cluster-meta">${{themes.length}}</span></summary>`;
  if (!themes.length) html += "<p style='color:#666;font-size:13px;padding:8px 0'>No repeated themes in window.</p>";
  else {{
    html += "<ul>";
    themes.slice(0,15).forEach(t => {{
      html += `<li><strong>${{htmlEscape(t.theme)}}</strong> <span class="cluster-meta">${{t.mention_count}} mentions · first seen ${{htmlEscape(t.first_seen||'—')}} · ${{(t.sources||[]).join(", ")}}</span>`;
      if (t.headlines && t.headlines.length) {{
        html += "<ul>";
        t.headlines.slice(0,3).forEach(h => {{
          html += `<li><em>${{htmlEscape(h.date||'')}}</em> ${{h.link?`<a href="${{htmlEscape(h.link)}}" target="_blank">${{htmlEscape(h.title||'')}}</a>`:htmlEscape(h.title||'')}}</li>`;
        }});
        html += "</ul>";
      }}
      html += "</li>";
    }});
    html += "</ul>";
  }}
  html += "</details>";

  // Regulatory alerts
  html += `<details><summary>Regulatory Alerts <span class="cluster-meta">${{reg.length}}</span></summary>`;
  if (!reg.length) html += "<p style='color:#666;font-size:13px;padding:8px 0'>No regulatory keywords detected.</p>";
  else {{
    html += "<ul>";
    reg.slice(0,15).forEach(r => {{
      html += `<li><em>${{htmlEscape(r.date||'')}}</em> ${{r.link?`<a href="${{htmlEscape(r.link)}}" target="_blank"><strong>${{htmlEscape(r.title||'')}}</strong></a>`:`<strong>${{htmlEscape(r.title||'')}}</strong>`}} <span class="cluster-meta">matched: ${{(r.matched_keywords||[]).map(k=>`<code>${{k}}</code>`).join(" ")}}</span></li>`;
    }});
    html += "</ul>";
  }}
  html += "</details>";

  // Competitor news
  html += `<details><summary>Competitor News <span class="cluster-meta">${{comp.length}}</span></summary>`;
  if (!comp.length) html += "<p style='color:#666;font-size:13px;padding:8px 0'>No competitor brand mentions in window.</p>";
  else {{
    html += "<ul>";
    comp.slice(0,15).forEach(c => {{
      html += `<li><em>${{htmlEscape(c.date||'')}}</em> ${{c.link?`<a href="${{htmlEscape(c.link)}}" target="_blank"><strong>${{htmlEscape(c.title||'')}}</strong></a>`:`<strong>${{htmlEscape(c.title||'')}}</strong>`}} <span class="cluster-meta">brand: <code>${{htmlEscape(c.matched_brand||'')}}</code></span></li>`;
    }});
    html += "</ul>";
  }}
  html += "</details>";

  // Trending negatives
  html += `<details><summary>Trending Negative Candidates <span class="cluster-meta">${{negs.length}}</span></summary>`;
  if (!negs.length) html += "<p style='color:#666;font-size:13px;padding:8px 0'>No scam/fraud/lawsuit triggers in window.</p>";
  else {{
    html += "<ul>";
    negs.slice(0,15).forEach(n => {{
      html += `<li><strong>${{htmlEscape(n.title||'')}}</strong> <span class="cluster-meta">triggers: ${{(n.trigger_keywords||[]).map(k=>`<code>${{k}}</code>`).join(" ")}}</span></li>`;
    }});
    html += "</ul>";
  }}
  html += "</details>";

  content.innerHTML = html;
}}

function renderNegatives() {{
  const tbody = document.querySelector("#negTable tbody");
  const filter = document.getElementById("negFilter").value.toLowerCase();
  const tier = document.getElementById("negTierFilter").value;
  let rows = REPORT.negatives || [];
  if (filter) rows = rows.filter(r => (r.keyword||"").toLowerCase().includes(filter)
                                   || (r.justification||"").toLowerCase().includes(filter));
  if (tier)   rows = rows.filter(r => r.tier === tier);
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><code>${{htmlEscape(r.keyword)}}</code></td>
      <td><span class="tier-${{r.tier}}">${{r.tier}}</span></td>
      <td>${{r.category}}</td>
      <td>${{htmlEscape(r.justification||"")}}</td>
    </tr>`).join("");
  document.getElementById("negCount").textContent = `${{rows.length}} of ${{(REPORT.negatives||[]).length}} negatives`;
}}

function exportCSV(kind) {{
  let rows, header;
  if (kind === "keywords") {{
    header = ["keyword","intent","match_type","cluster_id","signal_count","source_diversity","score"];
    rows = REPORT.keywords || [];
  }} else if (kind === "negatives") {{
    header = ["keyword","tier","category","justification"];
    rows = REPORT.negatives || [];
  }} else if (kind === "clusters") {{
    header = ["cluster_name","intent","keyword","score"];
    rows = [];
    (REPORT.clusters||[]).forEach(c => (c.keywords||[]).forEach(k =>
      rows.push({{cluster_name:c.name, intent:c.intent, keyword:k.keyword, score:k.score}})
    ));
  }} else return;
  const esc = v => {{ const s = String(v ?? ""); return /[",\n\r]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s; }};
  const csv = [header.join(",")].concat(rows.map(r => header.map(h => esc(r[h])).join(","))).join("\n");
  const blob = new Blob([csv], {{type:"text/csv;charset=utf-8"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `${{REPORT.meta.brief_slug}}_${{kind}}.csv`;
  a.click(); URL.revokeObjectURL(url);
}}

function makeSortable(tableId) {{
  const table = document.getElementById(tableId);
  table.querySelectorAll("th").forEach((th, idx) => {{
    th.addEventListener("click", () => {{
      const tbody = table.querySelector("tbody");
      const rows = Array.from(tbody.querySelectorAll("tr"));
      const isNum = th.dataset.sort === "number";
      const asc = !th.classList.contains("sort-asc");
      table.querySelectorAll("th").forEach(h => h.classList.remove("sort-asc","sort-desc"));
      th.classList.add(asc ? "sort-asc" : "sort-desc");
      rows.sort((a,b) => {{
        const av = a.cells[idx].textContent.trim();
        const bv = b.cells[idx].textContent.trim();
        if (isNum) return (asc?1:-1)*(parseFloat(av)-parseFloat(bv));
        return (asc?1:-1)*av.localeCompare(bv);
      }});
      rows.forEach(r => tbody.appendChild(r));
    }});
  }});
}}

document.getElementById("kwFilter").addEventListener("input", renderKeywords);
document.getElementById("intentFilter").addEventListener("change", renderKeywords);
document.getElementById("negFilter").addEventListener("input", renderNegatives);
document.getElementById("negTierFilter").addEventListener("change", renderNegatives);

renderKeywords(); renderClusters(); renderCompetitors(); renderNichePulse(); renderNegatives();
makeSortable("kwTable"); makeSortable("negTable");
</script>
</body>
</html>
"""


def build_report_json(
    ranked: list[dict],
    clusters_data: dict,
    competitor_intel: dict,
    negatives: list[dict],
    brief_text: str,
    run_dir: Path,
    *,
    niche_pulse: dict | None = None,
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
        "niche_pulse": niche_pulse or {},
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

    # Load optional niche pulse (Phase 7 sidecar)
    pulse_path = run_dir / "niche-pulse.json"
    niche_pulse: dict | None = None
    if pulse_path.exists():
        try:
            niche_pulse = json.loads(pulse_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            niche_pulse = None

    # Render
    report_md = render_full_report(
        ranked, clusters_data, competitor_intel, negatives,
        brief_text, run_dir, top_n=args.top_n, niche_pulse=niche_pulse,
    )
    report_json = build_report_json(
        ranked, clusters_data, competitor_intel, negatives,
        brief_text, run_dir, niche_pulse=niche_pulse,
    )

    report_html = render_html_report(report_json)

    # Write outputs (LF newlines, utf-8)
    (run_dir / "report.md").write_text(report_md, encoding="utf-8", newline="\n")
    (run_dir / "report.json").write_text(
        json.dumps(report_json, indent=2, ensure_ascii=False),
        encoding="utf-8", newline="\n",
    )
    (run_dir / "report.html").write_text(report_html, encoding="utf-8", newline="\n")

    print(json.dumps({
        "report_md": str(run_dir / "report.md"),
        "report_json": str(run_dir / "report.json"),
        "report_html": str(run_dir / "report.html"),
        "keywords_in_report": len(ranked),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
