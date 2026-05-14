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
import hashlib
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

# Per-section usage descriptions — surfaced inline so the operator knows what
# to DO with each section, not just what it contains.
USAGE_KEYWORDS = (
    "**How to use:** export this list to CSV, paste into Google Keyword "
    "Planner to get monthly volume + CPC, then build ad groups around the "
    "transactional + commercial keywords with `source_diversity` ≥ 2. "
    "Skip navigational keywords unless you're conquesting competitor brand "
    "terms — they're brand searches, not category demand."
)
USAGE_CLUSTERS = (
    "**How to use:** each cluster is a ready-to-paste Google Ads ad group. "
    "Cluster name follows `theme_intent` so you can copy it directly as the "
    "ad group label. Only bid on transactional and commercial clusters; "
    "informational clusters belong in a separate awareness campaign with "
    "lower CPC ceilings."
)
USAGE_COMPETITORS = (
    "**How to use:** scan competitor headlines and value props for angles "
    "to differentiate against (or copy if they're working). Pay attention "
    "to repeated CTAs (\"book online\", \"walk-in welcome\", \"PIP "
    "accepted\") — those are validated by competitor spend. Use them in "
    "your responsive search ad headlines and descriptions."
)
USAGE_NEGATIVES = (
    "**How to use:** add Strong-tier negatives to all campaigns immediately "
    "(they're high-confidence noise filters). Review Considered-tier "
    "negatives against your specific brand positioning before adding — some "
    "may be valid traffic for your tier. Skip Investigate-tier until you "
    "see them eat budget in search-term reports."
)
USAGE_PULSE_HIGHLIGHTS = (
    "**How to use:** the operator's punchline. Every item is a time-sensitive "
    "action — regulatory shifts mean ad copy claims need review, competitor "
    "news means messaging adjustments, trending themes mean early-mover "
    "keyword opportunities. Address these THIS WEEK; they age out fast."
)
USAGE_PULSE_THEMES = (
    "**How to use:** treat as opportunity candidates with a 1-4 week shelf "
    "life. Themes with high mention counts across both sources are real; "
    "single-source themes are noisier. For each one worth pursuing, add a "
    "phrase-match keyword to a dedicated 'trending' ad group with its own "
    "budget cap so the spike doesn't blow up your CPA."
)
USAGE_PULSE_REGULATORY = (
    "**How to use:** every alert here can affect what claims you're allowed "
    "to make in ad copy and what the audience is searching for. Read titles "
    "now; if anything mentions PIP, your state's no-fault law, or your "
    "service category specifically, pause affected ad groups and review "
    "creative before resuming."
)
USAGE_PULSE_COMPETITOR_NEWS = (
    "**How to use:** competitor moves are signals. Acquisitions or "
    "expansions mean their bid pressure rises in your geo. Lawsuits or "
    "scandals are conquesting opportunities — increase bids on their brand "
    "terms with comparison ad copy."
)
USAGE_ENRICHED = (
    "**How to use:** real Ahrefs data — monthly volume, CPC, Keyword "
    "Difficulty (KD), and parent topic. Bid first on transactional/commercial "
    "rows with `volume ≥ 100` and `KD ≤ 30`. Skip rows where Ahrefs returned "
    "no data — they're too niche to have measurable search volume. Use "
    "`parent_topic` to spot which of our LLM clusters Ahrefs would group "
    "differently."
)
USAGE_ACCOUNT_PERF = (
    "**How to use:** what your account actually did in the last 30 days. "
    "**Converted search terms** are gold — bid harder on those keywords or "
    "create dedicated ad groups. **Lossy search terms** (clicks but no "
    "conversions) are negative keyword candidates — review before adding. "
    "**Top by ROAS** tells you which campaigns to scale, **top by CPA** "
    "shows which are most efficient at conversion."
)
USAGE_NEG_SYNC = (
    "**How to use:** `already_in_account` rows are negatives your account "
    "already excludes — no action. `new_candidate` rows are missing — add "
    "**Strong** tier to all campaigns now, review **Considered** + "
    "**Investigate** before adding. Saves duplicate work between research "
    "and account audit."
)
USAGE_PULSE_NEGATIVES = (
    "**How to use:** quick-add candidates for your negative keyword list. "
    "Unlike the main negatives section, these are reactive — driven by news "
    "events you'd want to avoid being associated with. Review and either "
    "promote to Strong negatives or dismiss as transient noise."
)

TIER_ORDER = ["Strong", "Considered", "Investigate"]

# STEP-01: locked 8-step ops template. Step numbers derived from list
# position at render time (CMPL-05 prepends a verification step when
# compliance is non-empty — never hardcode step numbers in these strings).
_STANDARD_NEXT_STEPS_TEMPLATE: list[str] = [
    "Create campaign in {location} ({language}).",
    "Set daily budget to ${daily_spend_mid_usd:.2f} (Phase 9 mid forecast).",
    "Create ad groups: {cluster_names_csv}.",
    "Paste positives.csv via Google Ads Editor -> Make multiple changes.",
    "Paste negatives.csv at the levels specified by the Level column "
    "(campaign for Strong, ad_group for Considered/Investigate).",
    "Write 3 responsive search ads per ad group using competitor "
    "headline / CTA / offer examples from the Competitor Ad Copy section.",
    "Set Max CPC per keyword from the Suggested CPC column "
    "(or leave Editor's default if Max CPC = $0.00).",
    "Review compliance flags and budget forecast before enabling.",
]


def _micros_to_usd(micros: int | None) -> str:
    """Format a cpc_micros (or suggested_max_cpc_micros) integer as USD with cents.

    micros = USD × 1_000_000 (Pitfall 8 invariant). Returns '—' (em-dash) for
    None / falsy values so missing-data rows render consistently across the
    enriched-keyword table.
    """
    if micros is None:
        return "—"
    return f"${micros / 1_000_000:.2f}"

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
    parts = ["## Ad Group Clusters\n\n", USAGE_CLUSTERS, "\n"]
    clusters = clusters_data.get("clusters", [])
    for cluster in clusters:
        name = escape_md_cell(cluster.get("name", ""))
        parts.append(f"\n### {name}\n")
        for kw_entry in cluster.get("keywords", []):
            kw = escape_md_cell(kw_entry["keyword"])
            parts.append(f"- {kw}\n")
    return "".join(parts)


def render_competitor_section(competitor_intel: dict) -> str:
    """Render the Competitor Ad Copy section.

    When advertiser titles/descriptions are missing (LLM extraction not yet
    populated, or competitor LP yielded no extractable headlines), fall back
    to the domain + URL so the operator at least sees WHO is competing.
    """
    parts = ["## Competitor Ad Copy\n\n", USAGE_COMPETITORS, "\n"]
    clusters = competitor_intel.get("clusters", {})
    if not clusters:
        parts.append("\n_No competitor ad copy extracted for this run._\n")
        return "".join(parts)

    for cluster_name, cluster_data in clusters.items():
        escaped_name = escape_md_cell(cluster_name)
        source_label = cluster_data.get("advertiser_source", "ads")
        parts.append(f"\n### {escaped_name}  \n_(source: {source_label})_\n")
        ads = cluster_data.get("ads", [])
        advertisers = cluster_data.get("advertisers", [])

        # Prefer advertisers (richer data — has Tavily-extracted LP content)
        if advertisers:
            for adv in advertisers:
                title = (adv.get("ad_title") or adv.get("title") or "").strip()
                desc = (adv.get("ad_description") or adv.get("description") or "").strip()
                domain = adv.get("domain", "") or ""
                url = adv.get("url", "") or ""
                # Headline fallback chain: ad_title → domain → "(no headline)"
                headline = title if title else (domain if domain else "(no headline extracted)")
                parts.append(f"- **{escape_md_cell(headline)}**\n")
                if desc:
                    parts.append(f"  - {escape_md_cell(desc)}\n")
                if domain and title:  # only show domain separately if title was real
                    parts.append(f"  - Domain: `{escape_md_cell(domain)}`\n")
                if url:
                    parts.append(f"  - URL: <{escape_md_cell(url)}>\n")
        elif ads:
            for ad in ads:
                title = (ad.get("title") or "").strip()
                desc = (ad.get("description") or "").strip()
                domain = ad.get("domain", "") or ""
                headline = title if title else (domain or "(no ad title)")
                parts.append(f"- **{escape_md_cell(headline)}**\n")
                if desc:
                    parts.append(f"  - {escape_md_cell(desc)}\n")
                if domain and title:
                    parts.append(f"  - Domain: `{escape_md_cell(domain)}`\n")
        else:
            parts.append("- _No ads or advertisers captured for this cluster._\n")
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

    # --- Highlights (top of section, action-first) ---
    highlights = pulse.get("highlights", [])
    parts.append(f"\n### Highlights — Action This Week ({len(highlights)})\n\n"
                 f"{USAGE_PULSE_HIGHLIGHTS}\n")
    if not highlights:
        parts.append("\n_No high-priority items in this harvest._\n")
    else:
        for h in highlights:
            kind = h.get("kind", "?")
            summary = escape_md_cell(h.get("summary", ""))
            why = h.get("why_it_matters", "")
            parts.append(f"\n- **[{kind.upper()}]** {summary}  \n  _Why it matters:_ {why}\n")

    themes = pulse.get("trending_themes", [])
    parts.append(f"\n### Trending Themes ({len(themes)})\n\n{USAGE_PULSE_THEMES}\n")
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
    parts.append(f"\n### Regulatory Alerts ({len(reg)})\n\n{USAGE_PULSE_REGULATORY}\n")
    if not reg:
        parts.append("\n_No regulatory keywords detected._\n")
    else:
        for r in reg[:10]:
            title = escape_md_cell(r.get("title", ""))
            date = r.get("date") or ""
            kws = ", ".join(r.get("matched_keywords", []))
            parts.append(f"\n- _{date}_ **{title}** — matched: `{kws}`\n")

    comp = pulse.get("competitor_news", [])
    parts.append(f"\n### Competitor News ({len(comp)})\n\n{USAGE_PULSE_COMPETITOR_NEWS}\n")
    if not comp:
        parts.append("\n_No competitor brand mentions in the news harvest._\n")
    else:
        for c in comp[:10]:
            title = escape_md_cell(c.get("title", ""))
            brand = c.get("matched_brand", "")
            date = c.get("date") or ""
            parts.append(f"\n- _{date}_ **{title}** — brand: `{brand}`\n")

    negs = pulse.get("trending_negatives", [])
    parts.append(f"\n### Trending Negative Candidates ({len(negs)})\n\n{USAGE_PULSE_NEGATIVES}\n")
    if not negs:
        parts.append("\n_No scam/fraud/lawsuit triggers in the news window._\n")
    else:
        for n in negs[:10]:
            title = escape_md_cell(n.get("title", ""))
            trig = ", ".join(n.get("trigger_keywords", []))
            parts.append(f"\n- **{title}** — triggers: `{trig}`\n")

    return "".join(parts)


def render_enriched_keyword_table(ranked: list[dict], top_n: int = 100) -> str:
    """Volume-enriched keyword table. Used when at least one row has Ahrefs data.

    Carries CPC (Ahrefs) AND Suggested CPC (Phase 9 bid_suggest output) side by
    side so the operator can compare market price vs the recommended max bid.
    Both columns use the single `_micros_to_usd` helper (Pitfall 8 — micros to
    USD conversion happens in one place).
    """
    rows = []
    for r in ranked[:top_n]:
        vol = r.get("volume")
        cpc = _micros_to_usd(r.get("cpc_micros"))
        sugg = _micros_to_usd(r.get("suggested_max_cpc_micros"))
        kd = r.get("difficulty")
        parent = r.get("parent_topic") or ""
        rows.append([
            escape_md_cell(r["keyword"]),
            escape_md_cell(r["intent"]),
            r["match_type"],
            f"{vol:,}" if vol is not None else "—",
            cpc,
            sugg,
            f"{kd}" if kd is not None else "—",
            escape_md_cell(parent),
            str(r["source_diversity"]),
            str(r["score"]),
        ])
    headers = [
        "Keyword", "Intent", "Match", "Vol/mo", "CPC", "Suggested CPC", "KD",
        "Parent Topic", "Src Div", "Score",
    ]
    return tabulate(rows, headers=headers, tablefmt="github")


def render_account_perf_section(perf: dict) -> str:
    """Render the Account Performance section (markdown)."""
    if not perf or not isinstance(perf, dict):
        return ""
    parts = [
        f"## Account Performance — last {perf.get('horizon_days', 30)} days\n\n",
        USAGE_ACCOUNT_PERF, "\n",
    ]
    t = perf.get("totals", {})
    cpa = t.get("blended_cpa_usd")
    roas = t.get("blended_roas")
    cpa_str = f"${cpa:.2f}" if cpa else "—"
    roas_str = f"{roas:.2f}x" if roas else "—"
    parts.append(
        f"\n**Totals:** spend ${t.get('spend_usd', 0):,.2f} · "
        f"clicks {t.get('clicks', 0):,} · "
        f"conversions {t.get('conversions', 0)} · "
        f"blended CPA {cpa_str} · "
        f"blended ROAS {roas_str}\n"
    )

    converted = perf.get("converted_search_terms", [])
    parts.append(f"\n### Converted search terms ({len(converted)})\n")
    if not converted:
        parts.append("\n_No converted search terms in this window — too few "
                     "conversions tracked in active campaigns._\n")
    else:
        rows = [[
            escape_md_cell(t["search_term"]),
            f"{t['conversions']:.1f}",
            t["clicks"],
            f"${t['cost_usd']:.2f}",
            escape_md_cell(t["campaign_name"]),
        ] for t in converted[:15]]
        parts.append("\n")
        parts.append(tabulate(
            rows, headers=["Search Term", "Conv", "Clicks", "Cost", "Campaign"],
            tablefmt="github",
        ))
        parts.append("\n")

    lossy = perf.get("lossy_search_terms", [])
    parts.append(f"\n### Lossy search terms — negative keyword candidates ({len(lossy)})\n")
    if not lossy:
        parts.append("\n_No lossy terms detected._\n")
    else:
        rows = [[
            escape_md_cell(t["search_term"]),
            t["clicks"],
            f"${t['cost_usd']:.2f}",
            escape_md_cell(t["campaign_name"]),
        ] for t in lossy[:15]]
        parts.append("\n")
        parts.append(tabulate(
            rows, headers=["Search Term", "Clicks", "Cost", "Campaign"],
            tablefmt="github",
        ))
        parts.append("\n")

    by_roas = perf.get("top_by_roas", [])
    parts.append(f"\n### Top campaigns by ROAS ({len(by_roas)})\n")
    if not by_roas:
        parts.append("\n_No campaigns with positive ROAS in window._\n")
    else:
        rows = [[
            escape_md_cell(c["name"]),
            c["status"],
            f"${c['cost_usd']:.2f}",
            c["clicks"],
            f"{c['conversions']:.1f}",
            f"{c['roas']:.2f}x",
        ] for c in by_roas[:10]]
        parts.append("\n")
        parts.append(tabulate(
            rows, headers=["Campaign", "Status", "Spend", "Clicks", "Conv", "ROAS"],
            tablefmt="github",
        ))
        parts.append("\n")

    return "".join(parts)


def render_negatives_sync_section(sync: dict) -> str:
    """Render the Negative Keyword Sync section."""
    if not sync or not isinstance(sync, dict):
        return ""
    stats = sync.get("stats", {})
    parts = [
        f"## Negative Keyword Sync\n\n",
        USAGE_NEG_SYNC, "\n",
        f"\n**Stats:** our list = {stats.get('our_total', 0)} · "
        f"already in account = {stats.get('already_covered', 0)} · "
        f"new to add = **{stats.get('new_to_add', 0)}** "
        f"(Strong {stats.get('new_strong', 0)}, "
        f"Considered {stats.get('new_considered', 0)}, "
        f"Investigate {stats.get('new_investigate', 0)})\n",
    ]
    by_tier = sync.get("new_by_tier", {})
    for tier in ("Strong", "Considered", "Investigate"):
        items = by_tier.get(tier, [])
        parts.append(f"\n### New {tier} negatives to add ({len(items)})\n")
        if not items:
            parts.append("\n_None._\n")
            continue
        for n in items:
            kw = escape_md_cell(n["keyword"])
            cat = n.get("category", "")
            just = escape_md_cell(n.get("justification", ""))
            parts.append(f"- `{kw}` · _{cat}_ — {just}\n")
    return "".join(parts)


def render_compliance_warning(compliance: dict | None) -> str:
    """Render the ⚠ Compliance Required block (CMPL-03) as markdown blockquote.

    Returns an empty string when compliance is None or matched_verticals is
    empty / absent — caller can append unconditionally; graceful-degrade is
    built in. Pipe characters and other table-hostile content in policy_note
    + evidence_tokens are sanitised via escape_md_cell so downstream tooling
    that reads the markdown line-by-line stays safe.

    Block sits immediately after the header + HOW_TO_READ and BEFORE all
    other sections (above Niche Pulse, Account Perf, Clusters, Negatives,
    and the Ranked Keywords table) — surfaced before any keyword work so
    the operator addresses verification first.
    """
    if not compliance or not isinstance(compliance, dict):
        return ""
    matched = compliance.get("matched_verticals") or []
    if not matched:
        return ""

    parts = [
        "> ## ⚠ Compliance Required\n",
        ">\n",
        f"> This campaign matches **{len(matched)}** regulated vertical(s). "
        f"Verify compliance before launching.\n",
        ">\n",
    ]
    for v in matched:
        name = v.get("name", "") or ""
        tokens = v.get("evidence_tokens", []) or []
        kw_count = v.get("matched_keyword_count", 0)
        url = v.get("verification_url", "") or ""
        note = v.get("policy_note", "") or ""

        parts.append(f"> **{escape_md_cell(name.title())}**\n")
        if tokens:
            token_str = ", ".join(f"`{escape_md_cell(t)}`" for t in tokens)
            parts.append(f"> - Evidence tokens: {token_str}\n")
        parts.append(f"> - Matched keywords: {kw_count}\n")
        if url:
            parts.append(f"> - Verification: <{url}>\n")
        if note:
            parts.append(f"> - Policy note: {escape_md_cell(note, max_len=400)}\n")
        parts.append(">\n")

    return "".join(parts)


def _fmt_clicks(v) -> str:
    """Format daily click counts. Integers render as-is; floats round to 1dp
    and drop trailing `.0` so 6.0 → '6', 0.7333 → '0.7'."""
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.1f}".rstrip("0").rstrip(".") or "0"
    return str(v)


def render_forecast_section(forecast: dict | None) -> str:
    """Render the Budget Forecast section (FRCS-04 + FRCS-05) as markdown.

    Returns an empty string when forecast is None / missing clusters[] —
    callers can append unconditionally; graceful-degrade is built in.

    Sections:
      * Per-cluster table (Cluster | Intent | Keywords | Daily Clicks | Daily Spend | Monthly Spend)
      * Campaign Totals one-liner
      * "How this is calculated" subsection naming CTR anchors, avg-CPC ratio,
        band multipliers, and the verbatim methodology.notes disclaimer
        (single source of truth for FRCS-05 — sourced from forecast_budget.py).
    """
    if not forecast or not isinstance(forecast, dict):
        return ""
    clusters = forecast.get("clusters") or []
    if not clusters:
        return ""

    parts = ["## Budget Forecast\n\n"]
    parts.append(
        "_Directional estimates — not Google's official forecast. Use the "
        "**mid** band for a sane Day 1 budget; bracket with low/high once "
        "click-through data lands._\n\n"
    )

    # Per-cluster table
    rows = []
    for c in clusters:
        name = escape_md_cell(c.get("name", "") or "")
        intent = escape_md_cell(c.get("intent", "") or "")
        kw_count = c.get("keyword_count", 0)
        with_vol = c.get("keywords_with_volume", 0)
        clicks_low = c.get("daily_clicks_low", 0)
        clicks_mid = c.get("daily_clicks_mid", 0)
        clicks_high = c.get("daily_clicks_high", 0)
        spend_low = c.get("daily_spend_low_usd", 0)
        spend_mid = c.get("daily_spend_mid_usd", 0)
        spend_high = c.get("daily_spend_high_usd", 0)
        monthly_mid = c.get("monthly_spend_mid_usd", 0)
        rows.append([
            name,
            intent,
            f"{kw_count} ({with_vol} with vol)",
            f"{_fmt_clicks(clicks_low)}/{_fmt_clicks(clicks_mid)}/{_fmt_clicks(clicks_high)}",
            f"${spend_low:.2f}/${spend_mid:.2f}/${spend_high:.2f}",
            f"${monthly_mid:.2f}",
        ])
    headers = [
        "Cluster", "Intent", "Keywords",
        "Daily Clicks (lo/mid/hi)", "Daily Spend USD (lo/mid/hi)",
        "Monthly Spend Mid USD",
    ]
    parts.append(tabulate(rows, headers=headers, tablefmt="github"))
    parts.append("\n\n")

    # Campaign totals one-liner
    totals = forecast.get("campaign_totals", {}) or {}
    if totals:
        parts.append(
            f"**Campaign Totals:** Daily "
            f"{_fmt_clicks(totals.get('daily_clicks_low', 0))}/"
            f"{_fmt_clicks(totals.get('daily_clicks_mid', 0))}/"
            f"{_fmt_clicks(totals.get('daily_clicks_high', 0))} clicks · "
            f"${totals.get('daily_spend_low_usd', 0):.2f}/"
            f"${totals.get('daily_spend_mid_usd', 0):.2f}/"
            f"${totals.get('daily_spend_high_usd', 0):.2f} daily spend · "
            f"${totals.get('monthly_spend_mid_usd', 0):.2f} monthly (mid).\n\n"
        )

    # "How this is calculated" — FRCS-05 methodology mirrors module constants
    method = forecast.get("methodology", {}) or {}
    ctrs = method.get("intent_ctrs", {}) or {}
    ratio = method.get("avg_cpc_ratio", 0.65)
    bands = method.get("band_multipliers", {}) or {}
    notes = method.get("notes", "") or ""

    parts.append("### How this is calculated\n\n")
    parts.append(
        f"- **Clicks** = monthly search volume × intent-class CTR ÷ 30 days. "
        f"CTR anchors: transactional {ctrs.get('transactional', 0)*100:.0f}%, "
        f"commercial {ctrs.get('commercial', 0)*100:.0f}%, "
        f"informational {ctrs.get('informational', 0)*100:.0f}%, "
        f"navigational {ctrs.get('navigational', 0)*100:.0f}%.\n"
    )
    parts.append(
        f"- **Spend** = clicks × (suggested max CPC × {ratio}) (avg-CPC ratio).\n"
    )
    parts.append(
        f"- **Bands** = mid × {bands.get('low', 0.5)} (low) / "
        f"× {bands.get('mid', 1.0)} (mid) / "
        f"× {bands.get('high', 1.5)} (high).\n"
    )
    if notes:
        parts.append(f"- {escape_md_cell(notes, max_len=400)}\n")

    return "".join(parts)


def render_negatives_section(negatives: list[dict]) -> str:
    """Render the Negative Keywords section with Strong/Considered/Investigate tiers."""
    by_tier: dict[str, list[dict]] = {t: [] for t in TIER_ORDER}
    for neg in negatives:
        tier = neg.get("tier", "Investigate")
        if tier in by_tier:
            by_tier[tier].append(neg)

    parts = ["## Negative Keywords\n\n", USAGE_NEGATIVES, "\n"]
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


def render_next_steps_section(
    brief_fields: dict[str, str],
    forecast: dict | None,
    compliance: dict | None,
    clusters_data: dict,
) -> tuple[str, list[dict]]:
    """Render the Next Steps checklist (STEP-01..04 + CMPL-05).

    Returns (markdown_string, step_list) where step_list is the canonical
    ordered list of step dicts shared by report.md, report.json, and the
    HTML renderer. Step numbers are derived from final list position so the
    CMPL-05 reorder (compliance present -> verification step prepended)
    never produces wrong numbering.

    Rules:
        - 8 standard ops steps from the locked template.
        - If compliance.matched_verticals is non-empty, prepend ONE combined
          verification step (multi-vertical -> ONE step, not N).
        - Step IDs = sha1(text)[:8] — stable across renders for HTML
          localStorage keys.
    """
    location = (brief_fields or {}).get("location") or "<location>"
    language = (brief_fields or {}).get("language") or "<language>"

    totals = (forecast or {}).get("campaign_totals", {}) or {}
    raw_mid = totals.get("daily_spend_mid_usd", 0.0)
    try:
        daily_spend_mid_usd = float(raw_mid) if raw_mid is not None else 0.0
    except (TypeError, ValueError):
        daily_spend_mid_usd = 0.0

    cluster_names = [
        c.get("name", "")
        for c in (clusters_data or {}).get("clusters", []) or []
        if c.get("name")
    ]
    cluster_names_csv = ", ".join(cluster_names) if cluster_names else "<clusters>"

    fmt = {
        "location": location,
        "language": language,
        "daily_spend_mid_usd": daily_spend_mid_usd,
        "cluster_names_csv": cluster_names_csv,
    }

    try:
        steps_text = [t.format(**fmt) for t in _STANDARD_NEXT_STEPS_TEMPLATE]
    except KeyError as exc:
        raise KeyError(
            f"_STANDARD_NEXT_STEPS_TEMPLATE drift: missing substitution {exc}"
        ) from exc

    matched_verticals = (compliance or {}).get("matched_verticals") or []
    if matched_verticals:
        names = " + ".join(
            (v.get("name", "") or "").title() for v in matched_verticals
        ) or "<vertical>"
        urls = "; ".join(
            v.get("verification_url", "") or "" for v in matched_verticals
        )
        verify_step = (
            f"Complete {names} verification at {urls} before launching."
        )
        steps_text = [verify_step] + steps_text

    step_list: list[dict] = []
    for n, text in enumerate(steps_text, start=1):
        sid = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        step_list.append({"n": n, "text": text, "id": sid})

    parts = [
        "## Next Steps\n\n",
        "_Ordered ops checklist for moving from `report.md` to a live Google "
        "Ads campaign. Check off each step as you complete it._\n\n",
    ]
    for step in step_list:
        parts.append(f"{step['n']}. {step['text']}\n")
    parts.append("\n")

    return "".join(parts), step_list


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
    account_perf: dict | None = None,
    negatives_sync: dict | None = None,
    forecast: dict | None = None,
    compliance: dict | None = None,
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

    # Section order: action items first (pulse highlights, clusters,
    # negatives), reference data last (full ranked keyword table, full pulse
    # tables, competitor LP details). Operator scrolls less to find what to
    # do this week.
    # Detect whether Ahrefs enrichment is present (any row w/ a volume value)
    has_enrichment = any(
        r.get("volume") is not None for r in ranked
    )

    sections = [
        header,
        HOW_TO_READ,
    ]
    # Compliance warning ABOVE all other sections (CMPL-03) — operator's
    # first signal before they look at keywords / clusters / negatives. Empty
    # string when matched_verticals is empty/absent (graceful degrade).
    compliance_md = render_compliance_warning(compliance)
    if compliance_md:
        sections.append("\n")
        sections.append(compliance_md)
    # Niche pulse first (action this week)
    pulse_md = render_niche_pulse_section(niche_pulse or {})
    if pulse_md:
        sections.append("\n")
        sections.append(pulse_md)
    # Account perf next (real campaign data, also action-this-week)
    if account_perf:
        sections.append("\n")
        sections.append(render_account_perf_section(account_perf))
    # Negatives sync (action: what to add to account)
    if negatives_sync:
        sections.append("\n")
        sections.append(render_negatives_sync_section(negatives_sync))
    # Ad groups (evergreen)
    sections.extend([
        "\n",
        render_clusters_section(clusters_data),
    ])
    # Budget Forecast (Phase 9 FRCS-04) — between Clusters and Negatives.
    # render_forecast_section returns "" when forecast is None / clusters absent,
    # so we can append unconditionally (graceful degrade).
    forecast_md = render_forecast_section(forecast)
    if forecast_md:
        sections.append("\n")
        sections.append(forecast_md)
    # Negatives + Competitor (evergreen)
    sections.extend([
        "\n",
        render_negatives_section(negatives),
        "\n",
        render_competitor_section(competitor_intel),
    ])
    # Volume-enriched table replaces the plain ranked table when present
    if has_enrichment:
        sections.extend([
            "\n## Ranked Keywords — Volume-Enriched\n\n",
            USAGE_ENRICHED, "\n\n",
            render_enriched_keyword_table(ranked, top_n=top_n),
            "\n\n",
        ])
    else:
        sections.extend([
            "\n## Ranked Keywords\n\n",
            USAGE_KEYWORDS, "\n\n",
            render_keyword_table(ranked, top_n=top_n),
            "\n\n",
        ])
    # Next Steps (Phase 10 STEP-01..04 + CMPL-05) — LAST section.
    brief_fields = _parse_brief_fields(brief_text)
    next_steps_md, _ = render_next_steps_section(
        brief_fields, forecast, compliance, clusters_data
    )
    sections.append("\n")
    sections.append(next_steps_md)
    return "".join(sections)


def render_html_report(report_json: dict) -> str:
    """Return self-contained HTML report (no external CDN/network deps).

    Embeds report_json as a JS object so the page can offer CSV export of
    every section without round-tripping back to disk.

    Security: API responses (Tavily/Serper) may contain arbitrary remote
    content including `</script>` strings. Escape so the embedded JSON
    cannot break out of the script tag (XSS hardening).
    """
    payload = json.dumps(report_json, ensure_ascii=False)
    # Prevent </script> in any field from terminating the inline script tag.
    # Also escape <!-- and U+2028/U+2029 line separators that some browsers
    # treat as JS line terminators.
    payload = (
        payload.replace("</", "<\\/")
        .replace("<!--", "<\\!--")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )
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
.usage {{ background: #ecfeff; border-left: 4px solid #0891b2; padding: 10px 14px;
         font-size: 13px; margin: 0 0 14px; border-radius: 4px; color: #0c4a6e; }}
.usage strong {{ color: #155e75; }}
.highlight-card {{ background: #fff7ed; border-left: 4px solid #ea580c; padding: 10px 14px;
                  margin: 8px 0; border-radius: 4px; font-size: 13px; }}
.highlight-card .kind {{ display: inline-block; padding: 1px 8px; border-radius: 10px;
                        font-size: 10px; font-weight: 700; margin-right: 6px;
                        background: #ea580c; color: #fff; text-transform: uppercase; }}
.highlight-card .why {{ color: #6b7280; font-size: 12px; margin-top: 4px; font-style: italic; }}
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

<section id="compliance" style="display:none">
  <h2>⚠ Compliance Required <span class="cluster-meta" id="complianceMeta"></span></h2>
  <div class="usage"><strong>How to use:</strong> this campaign matched a regulated vertical. Complete verification at the URL below <em>before</em> launching. Google may reject ads or suspend the account otherwise.</div>
  <div id="complianceContent"></div>
</section>

<section id="forecast" style="display:none">
  <h2>Budget Forecast <span class="cluster-meta" id="forecastMeta"></span></h2>
  <div class="usage"><strong>How to use:</strong> directional estimates only. Use the <strong>mid</strong> band for a sane Day 1 budget; bracket with low/high once click-through data lands. NOT Google's official forecast.</div>
  <div id="forecastContent"></div>
</section>

<section id="account-perf">
  <h2>Account Performance <span class="cluster-meta" id="perfMeta"></span></h2>
  <div class="usage"><strong>How to use:</strong> what your account actually did. <strong>Converted search terms</strong> are gold — bid harder. <strong>Lossy search terms</strong> (clicks no conv) = negative candidates. <strong>Top by ROAS</strong> = scale candidates.</div>
  <div id="perfContent">
    <p style="color:#666;font-size:13px;">No account-perf.json — run Phase 8 perf_fetch + perf_synth.</p>
  </div>
</section>

<section id="negatives-sync">
  <h2>Negative Keyword Sync <span class="cluster-meta" id="negSyncMeta"></span></h2>
  <div class="usage"><strong>How to use:</strong> cross-references our generated negatives vs your account's existing negative list. <strong>New candidates</strong> are what to add to the account — Strong tier first.</div>
  <div id="negSyncContent">
    <p style="color:#666;font-size:13px;">No negatives-sync.json — run Phase 8 perf_synth.</p>
  </div>
</section>

<section id="niche-pulse">
  <h2>Niche Pulse <span class="cluster-meta" id="pulseMeta"></span></h2>
  <div class="usage"><strong>What this is:</strong> news-derived signals from the last 7 days. Time-sensitive (1-4 week shelf life). NOT merged into the main keyword ranking. The four sub-sections below each have their own action — start with <strong>Highlights</strong>.</div>
  <div id="pulseContent">
    <p style="color:#666;font-size:13px;">No niche-pulse.json found in this run — run Phase 7 (pulse_fetch + pulse_synth) to populate.</p>
  </div>
</section>

<section>
  <h2>Ad Group Clusters</h2>
  <div class="usage"><strong>How to use:</strong> each cluster is a ready-to-paste Google Ads ad group. Cluster name follows <code>theme_intent</code> — copy directly as the ad group label. Bid on transactional + commercial clusters; informational clusters belong in a separate awareness campaign with lower CPC ceilings.</div>
  <div class="toolbar">
    <button onclick="exportCSV('clusters')">Export CSV</button>
    <span class="count" id="clusterCount"></span>
  </div>
  <div id="clustersList"></div>
</section>

<section>
  <h2>Negative Keywords</h2>
  <div class="usage"><strong>How to use:</strong> add <span class="tier-Strong">Strong</span> negatives to all campaigns immediately (high-confidence noise filters). Review <span class="tier-Considered">Considered</span> negatives against your brand positioning before adding. Skip <span class="tier-Investigate">Investigate</span> until they show up eating budget in search-term reports.</div>
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

<section>
  <h2>Competitor Ad Copy</h2>
  <div class="usage"><strong>How to use:</strong> scan competitor headlines and value props for angles to differentiate against (or copy if working). Repeated CTAs (<em>"book online"</em>, <em>"walk-in welcome"</em>, <em>"PIP accepted"</em>) are validated by competitor spend — use them in your responsive search ad headlines.</div>
  <div id="competitorList"></div>
</section>

<section>
  <h2>Ranked Keywords</h2>
  <div class="usage"><strong>How to use:</strong> export to CSV, paste into Google Keyword Planner for monthly volume + CPC, then build ad groups around the transactional + commercial keywords with <code>source_diversity ≥ 2</code>. Skip navigational keywords unless conquesting competitor brand terms.</div>
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
      <tr id="kwHeaderRow">
        <th data-sort="string">Keyword</th>
        <th data-sort="string">Intent</th>
        <th data-sort="string">Match</th>
        <th data-sort="number" data-enriched>Vol/mo</th>
        <th data-sort="number" data-enriched>CPC</th>
        <th data-sort="number" data-enriched>KD</th>
        <th data-sort="string" data-enriched>Parent Topic</th>
        <th data-sort="string">Cluster</th>
        <th data-sort="number">Signals</th>
        <th data-sort="number">Src Div</th>
        <th data-sort="number">Score</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
</section>

<section id="next-steps">
  <h2>Next Steps</h2>
  <div class="usage"><em>Ordered ops checklist. Progress saves locally in your browser per run.</em></div>
  <div id="nextStepsContent"></div>
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
  // Detect Ahrefs enrichment — show/hide enriched columns
  const enriched = rows.some(r => r.volume !== undefined && r.volume !== null);
  document.querySelectorAll("#kwTable th[data-enriched]").forEach(th => {{
    th.style.display = enriched ? "" : "none";
  }});
  if (filter)  rows = rows.filter(r => (r.keyword||"").toLowerCase().includes(filter));
  if (intent)  rows = rows.filter(r => r.intent === intent);
  tbody.innerHTML = rows.map(r => {{
    const cpc = r.cpc_micros ? `$${{(r.cpc_micros / 1_000_000).toFixed(2)}}` : "—";
    const vol = r.volume != null ? r.volume.toLocaleString() : "—";
    const kd  = r.difficulty != null ? r.difficulty : "—";
    const pt  = r.parent_topic ? htmlEscape(r.parent_topic) : "—";
    const enrichedCols = enriched
      ? `<td>${{vol}}</td><td>${{cpc}}</td><td>${{kd}}</td><td>${{pt}}</td>`
      : "";
    return `<tr>
      <td>${{htmlEscape(r.keyword)}}</td>
      <td><span class="intent-tag intent-${{r.intent}}">${{r.intent}}</span></td>
      <td>${{r.match_type}}</td>
      ${{enrichedCols}}
      <td>${{r.cluster_id ? `<code>${{r.cluster_id}}</code>` : ""}}</td>
      <td>${{r.signal_count}}</td>
      <td>${{r.source_diversity}}</td>
      <td>${{r.score}}</td>
    </tr>`;
  }}).join("");
  document.getElementById("kwCount").textContent = `${{rows.length}} of ${{(REPORT.keywords||[]).length}} keywords`;
}}

function renderAccountPerf() {{
  const perf = REPORT.account_perf || {{}};
  const meta = document.getElementById("perfMeta");
  const content = document.getElementById("perfContent");
  if (!perf || !perf.synthesized_at) return;
  const t = perf.totals || {{}};
  meta.textContent = `last ${{perf.horizon_days||30}} days · $${{(t.spend_usd||0).toLocaleString()}} spend · ${{t.conversions||0}} conv`;
  const tbl = (rows, headers, fmt) => {{
    if (!rows.length) return "<p style='color:#666;font-size:13px'>None.</p>";
    return `<table style="margin-bottom:12px"><thead><tr>${{headers.map(h => `<th>${{h}}</th>`).join("")}}</tr></thead><tbody>${{rows.map(r => `<tr>${{fmt(r).map(c => `<td>${{c}}</td>`).join("")}}</tr>`).join("")}}</tbody></table>`;
  }};
  let html = `<div style="background:#ecfdf5;border-left:4px solid #10b981;padding:10px 14px;margin-bottom:12px;border-radius:4px;font-size:13px">
    <strong>Totals:</strong> spend $${{(t.spend_usd||0).toLocaleString()}} · clicks ${{(t.clicks||0).toLocaleString()}} · conv ${{t.conversions||0}} · blended CPA ${{t.blended_cpa_usd ? '$'+t.blended_cpa_usd : '—'}} · ROAS ${{t.blended_roas ? t.blended_roas+'x' : '—'}}
  </div>`;

  const conv = perf.converted_search_terms || [];
  html += `<details open><summary>Converted search terms <span class="cluster-meta">${{conv.length}}</span></summary>` + tbl(conv.slice(0,15),
    ["Search Term","Conv","Clicks","Cost","Campaign"],
    r => [htmlEscape(r.search_term), r.conversions.toFixed(1), r.clicks, `$${{r.cost_usd.toFixed(2)}}`, htmlEscape(r.campaign_name)]
  ) + `</details>`;

  const lossy = perf.lossy_search_terms || [];
  html += `<details><summary>Lossy search terms — negative candidates <span class="cluster-meta">${{lossy.length}}</span></summary>` + tbl(lossy.slice(0,15),
    ["Search Term","Clicks","Cost","Campaign"],
    r => [htmlEscape(r.search_term), r.clicks, `$${{r.cost_usd.toFixed(2)}}`, htmlEscape(r.campaign_name)]
  ) + `</details>`;

  const roas = perf.top_by_roas || [];
  html += `<details><summary>Top campaigns by ROAS <span class="cluster-meta">${{roas.length}}</span></summary>` + tbl(roas.slice(0,10),
    ["Campaign","Status","Spend","Clicks","Conv","ROAS"],
    r => [htmlEscape(r.name), r.status, `$${{r.cost_usd.toFixed(2)}}`, r.clicks, r.conversions.toFixed(1), `${{r.roas.toFixed(2)}}x`]
  ) + `</details>`;

  content.innerHTML = html;
}}

function renderNegativesSync() {{
  const sync = REPORT.negatives_sync || {{}};
  const meta = document.getElementById("negSyncMeta");
  const content = document.getElementById("negSyncContent");
  if (!sync || !sync.synthesized_at) return;
  const s = sync.stats || {{}};
  meta.textContent = `${{s.our_total||0}} ours · ${{s.already_covered||0}} already in account · ${{s.new_to_add||0}} new to add`;
  const by_tier = sync.new_by_tier || {{}};
  let html = `<div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:10px 14px;margin-bottom:12px;border-radius:4px;font-size:13px">
    <strong>Stats:</strong> our list = ${{s.our_total||0}} · already in account = ${{s.already_covered||0}} · new to add = <strong>${{s.new_to_add||0}}</strong> (Strong ${{s.new_strong||0}}, Considered ${{s.new_considered||0}}, Investigate ${{s.new_investigate||0}})
  </div>`;
  for (const tier of ["Strong","Considered","Investigate"]) {{
    const items = by_tier[tier] || [];
    html += `<details${{tier==='Strong'?' open':''}}><summary>New <span class="tier-${{tier}}">${{tier}}</span> negatives <span class="cluster-meta">${{items.length}}</span></summary>`;
    if (!items.length) html += "<p style='color:#666;font-size:13px'>None.</p>";
    else html += "<ul>" + items.map(n => `<li><code>${{htmlEscape(n.keyword)}}</code> <span class="cluster-meta">${{htmlEscape(n.category||'')}}</span> — ${{htmlEscape(n.justification||'')}}</li>`).join("") + "</ul>";
    html += "</details>";
  }}
  content.innerHTML = html;
}}

function renderCompliance() {{
  const list = REPORT.compliance || [];
  if (!list.length) return;
  const section = document.getElementById("compliance");
  const meta = document.getElementById("complianceMeta");
  const content = document.getElementById("complianceContent");
  section.style.display = "block";
  meta.textContent = `${{list.length}} regulated vertical(s) matched`;
  let html = `<div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:12px 16px;margin-bottom:12px;border-radius:4px;font-size:14px"><strong>Verify before launching.</strong> Google may reject ads or suspend the account if the regulated-vertical certification path is not completed.</div>`;
  for (const v of list) {{
    const name = htmlEscape((v.vertical || "").toUpperCase());
    const tokens = (v.evidence_tokens || []).map(t => `<code>${{htmlEscape(t)}}</code>`).join(", ") || "—";
    const url = v.verification_url || "";
    const note = htmlEscape(v.policy_note || "");
    const kwCount = v.matched_keyword_count != null ? v.matched_keyword_count : (v.matched_keywords||[]).length;
    html += `<details open style="margin-bottom:8px;background:#fffbeb;border:1px solid #fde68a;border-radius:4px;padding:8px 12px">
      <summary><strong>${{name}}</strong> <span class="cluster-meta">${{kwCount}} keyword matches</span></summary>
      <ul style="margin:8px 0">
        <li><strong>Evidence tokens:</strong> ${{tokens}}</li>
        <li><strong>Verification:</strong> ${{url ? `<a href="${{htmlEscape(url)}}" target="_blank" rel="noopener">${{htmlEscape(url)}}</a>` : '—'}}</li>
        <li><strong>Policy note:</strong> ${{note}}</li>
      </ul>
    </details>`;
  }}
  content.innerHTML = html;
}}

function renderForecast() {{
  const forecast = REPORT.forecast || {{}};
  const clusters = forecast.clusters || [];
  if (!clusters.length) return;
  const section = document.getElementById("forecast");
  const meta = document.getElementById("forecastMeta");
  const content = document.getElementById("forecastContent");
  section.style.display = "block";
  const totals = forecast.campaign_totals || {{}};
  const fmtClicks = v => {{
    if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(1).replace(/\\.0$/, "");
    return String(v);
  }};
  meta.textContent = `${{clusters.length}} clusters · $${{(totals.daily_spend_mid_usd||0).toFixed(2)}}/day mid · $${{(totals.monthly_spend_mid_usd||0).toFixed(2)}}/mo`;
  let html = `<div style="background:#ecfdf5;border-left:4px solid #10b981;padding:10px 14px;margin-bottom:12px;border-radius:4px;font-size:13px"><strong>Campaign Totals:</strong> Daily ${{fmtClicks(totals.daily_clicks_low||0)}}/${{fmtClicks(totals.daily_clicks_mid||0)}}/${{fmtClicks(totals.daily_clicks_high||0)}} clicks · $${{(totals.daily_spend_low_usd||0).toFixed(2)}}/$${{(totals.daily_spend_mid_usd||0).toFixed(2)}}/$${{(totals.daily_spend_high_usd||0).toFixed(2)}} daily spend · $${{(totals.monthly_spend_mid_usd||0).toFixed(2)}} monthly (mid)</div>`;
  html += `<table><thead><tr><th>Cluster</th><th>Intent</th><th>Keywords</th><th>Daily Clicks (lo/mid/hi)</th><th>Daily Spend (lo/mid/hi)</th><th>Monthly Spend Mid</th></tr></thead><tbody>`;
  for (const c of clusters) {{
    html += `<tr>
      <td>${{htmlEscape(c.name||"")}}</td>
      <td>${{htmlEscape(c.intent||"")}}</td>
      <td>${{c.keyword_count||0}} (${{c.keywords_with_volume||0}} w/vol)</td>
      <td>${{fmtClicks(c.daily_clicks_low||0)}}/${{fmtClicks(c.daily_clicks_mid||0)}}/${{fmtClicks(c.daily_clicks_high||0)}}</td>
      <td>$${{(c.daily_spend_low_usd||0).toFixed(2)}}/$${{(c.daily_spend_mid_usd||0).toFixed(2)}}/$${{(c.daily_spend_high_usd||0).toFixed(2)}}</td>
      <td>$${{(c.monthly_spend_mid_usd||0).toFixed(2)}}</td>
    </tr>`;
  }}
  html += `</tbody></table>`;
  const method = forecast.methodology || {{}};
  const ctrs = method.intent_ctrs || {{}};
  const ratio = method.avg_cpc_ratio || 0.65;
  const bands = method.band_multipliers || {{}};
  html += `<details style="margin-top:12px"><summary><strong>How this is calculated</strong></summary>
    <ul style="font-size:13px">
      <li><strong>Clicks</strong> = monthly volume × intent CTR ÷ 30 days. CTRs: T ${{((ctrs.transactional||0)*100).toFixed(0)}}% · C ${{((ctrs.commercial||0)*100).toFixed(0)}}% · I ${{((ctrs.informational||0)*100).toFixed(0)}}% · N ${{((ctrs.navigational||0)*100).toFixed(0)}}%.</li>
      <li><strong>Spend</strong> = clicks × (suggested max CPC × ${{ratio}}) (avg-CPC ratio).</li>
      <li><strong>Bands</strong> = mid × ${{bands.low||0.5}} (low) / × ${{bands.mid||1.0}} (mid) / × ${{bands.high||1.5}} (high).</li>
      <li>Directional estimates only. Not Google's official forecast — use Keyword Planner for that.</li>
    </ul>
  </details>`;
  content.innerHTML = html;
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
    const sourceLabel = data.advertiser_source || "ads";
    if (!ads.length && !advs.length) return "";
    const items = (advs.length ? advs : ads).map(a => {{
      const title = (a.ad_title || a.title || "").trim();
      const desc = (a.ad_description || a.description || "").trim();
      const domain = a.domain || "";
      const url = a.url || a.link || "";
      // Fallback chain — never show empty bullet
      const headline = title || domain || "(no headline extracted)";
      return `<li><strong>${{htmlEscape(headline)}}</strong>
          ${{desc ? "<br><span>"+htmlEscape(desc)+"</span>" : ""}}
          ${{domain && title ? "<br><code>"+htmlEscape(domain)+"</code>" : ""}}
          ${{url ? `<br><a href="${{htmlEscape(url)}}" target="_blank" style="font-size:11px;color:#2563eb;">${{htmlEscape(url)}}</a>` : ""}}
      </li>`;
    }}).join("");
    return `<details><summary>${{htmlEscape(name)}}<span class="cluster-meta">${{ads.length}} ads · ${{advs.length}} advertisers · source: ${{sourceLabel}}</span></summary><ul>${{items}}</ul></details>`;
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
  const highlights = pulse.highlights || [];
  const themes = pulse.trending_themes || [];
  const reg = pulse.regulatory_alerts || [];
  const comp = pulse.competitor_news || [];
  const negs = pulse.trending_negatives || [];

  let html = "";

  // Highlights — top of section
  html += `<details open><summary>Highlights — Action This Week <span class="cluster-meta">${{highlights.length}}</span></summary>`;
  html += `<div class="usage" style="margin-top:8px"><strong>How to use:</strong> the operator's punchline. Every item below is a time-sensitive action — regulatory shifts mean ad copy claims need review, competitor news means messaging adjustments, trending themes mean early-mover keyword opportunities. Address these THIS WEEK; they age out fast.</div>`;
  if (!highlights.length) {{
    html += `<p style="color:#666;font-size:13px;padding:8px 0">No high-priority items in this harvest window. Re-run Phase 7 next week.</p>`;
  }} else {{
    highlights.forEach(h => {{
      html += `<div class="highlight-card"><span class="kind">${{htmlEscape(h.kind||'')}}</span> ${{h.link?`<a href="${{htmlEscape(h.link)}}" target="_blank">${{htmlEscape(h.summary||'')}}</a>`:`<strong>${{htmlEscape(h.summary||'')}}</strong>`}}`;
      if (h.date) html += ` <span class="cluster-meta">${{htmlEscape(h.date)}}</span>`;
      if (h.matched_brand) html += ` <span class="cluster-meta">brand: <code>${{htmlEscape(h.matched_brand)}}</code></span>`;
      if (h.matched_keywords && h.matched_keywords.length) html += ` <span class="cluster-meta">matched: ${{h.matched_keywords.map(k=>`<code>${{k}}</code>`).join(" ")}}</span>`;
      if (h.why_it_matters) html += `<div class="why">Why it matters: ${{htmlEscape(h.why_it_matters)}}</div>`;
      html += `</div>`;
    }});
  }}
  html += `</details>`;

  // Trending themes
  html += `<details><summary>Trending Themes <span class="cluster-meta">${{themes.length}}</span></summary>`;
  html += `<div class="usage" style="margin-top:8px"><strong>How to use:</strong> opportunity candidates with 1-4 week shelf life. High mention counts across BOTH sources (serper-news + tavily-news) are real; single-source themes are noisier. For each one worth pursuing, add a phrase-match keyword to a dedicated 'trending' ad group with its own budget cap so the spike doesn't blow up your CPA.</div>`;
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
  html += `<div class="usage" style="margin-top:8px"><strong>How to use:</strong> every alert here can affect what claims you're allowed to make in ad copy and what the audience is searching for. Read titles now; if anything mentions PIP, your state's no-fault law, or your service category specifically, pause affected ad groups and review creative before resuming.</div>`;
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
  html += `<div class="usage" style="margin-top:8px"><strong>How to use:</strong> competitor moves are signals. Acquisitions or expansions mean their bid pressure rises in your geo. Lawsuits or scandals are conquesting opportunities — increase bids on their brand terms with comparison ad copy.</div>`;
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
  html += `<div class="usage" style="margin-top:8px"><strong>How to use:</strong> quick-add candidates for your negative keyword list. Unlike the main Negatives section, these are reactive — driven by news events you'd want to avoid being associated with. Review and either promote to Strong negatives or dismiss as transient noise.</div>`;
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

function renderNextSteps() {{
  var steps = (REPORT.next_steps || []);
  var slug = (REPORT.meta && REPORT.meta.brief_slug) || "default";
  var container = document.getElementById("nextStepsContent");
  if (!container) return;
  if (!steps.length) {{
    container.innerHTML = "<p style='color:#666;font-size:13px'>No checklist available.</p>";
    return;
  }}
  var items = steps.map(function(s) {{
    var storageKey = `gar_${{slug}}_step_${{s.id}}`;
    var saved = localStorage.getItem(storageKey);
    var checked = (saved === "1") ? " checked" : "";
    return '<li style="margin:6px 0"><label><input type="checkbox" data-key="' + storageKey + '"' + checked + '> ' + htmlEscape(s.text) + '</label></li>';
  }}).join("");
  container.innerHTML = "<ol>" + items + "</ol>";
  container.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {{
    cb.addEventListener("change", function(e) {{
      localStorage.setItem(e.target.dataset.key, e.target.checked ? "1" : "0");
    }});
  }});
}}

renderKeywords(); renderClusters(); renderCompetitors(); renderNichePulse();
renderCompliance(); renderForecast();
renderAccountPerf(); renderNegativesSync(); renderNegatives();
renderNextSteps();
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
    account_perf: dict | None = None,
    negatives_sync: dict | None = None,
    forecast: dict | None = None,
    compliance: dict | None = None,
    next_steps: list[dict] | None = None,
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

    # CMPL-04: surface matched_verticals[] as a top-level array (not the wrapping object)
    compliance_list: list[dict] = []
    if isinstance(compliance, dict):
        matched = compliance.get("matched_verticals") or []
        if isinstance(matched, list):
            compliance_list = matched

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
        "account_perf": account_perf or {},
        "negatives_sync": negatives_sync or {},
        "forecast": forecast or {},
        "compliance": compliance_list,
        "next_steps": next_steps if next_steps is not None else (
            render_next_steps_section(
                brief_fields, forecast, compliance, clusters_data
            )[1]
        ),
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

    # Load required inputs — prefer ranked-enriched.json over ranked.json
    enriched_path = run_dir / "ranked-enriched.json"
    ranked_path = enriched_path if enriched_path.exists() else (run_dir / "ranked.json")
    try:
        ranked = json.loads(ranked_path.read_text(encoding="utf-8"))
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

    # Load optional account perf + negatives sync (Phase 8 sidecars)
    account_perf: dict | None = None
    perf_path = run_dir / "account-perf.json"
    if perf_path.exists():
        try:
            account_perf = json.loads(perf_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            account_perf = None

    negatives_sync: dict | None = None
    sync_path = run_dir / "negatives-sync.json"
    if sync_path.exists():
        try:
            negatives_sync = json.loads(sync_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            negatives_sync = None

    # Load optional Phase 9 sidecars (forecast.json + compliance-flags.json).
    # Missing files degrade gracefully — sections are simply omitted from the
    # report. Mirrors the niche-pulse / account-perf / negatives-sync pattern.
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

    # Phase 10 STEP-01..04 + CMPL-05 — compute Next Steps once, share between
    # report.md (via render_full_report internally) and report.json/HTML.
    brief_fields_for_steps = _parse_brief_fields(brief_text)
    _, next_steps_list = render_next_steps_section(
        brief_fields_for_steps, forecast, compliance, clusters_data
    )

    # Render
    report_md = render_full_report(
        ranked, clusters_data, competitor_intel, negatives,
        brief_text, run_dir, top_n=args.top_n,
        niche_pulse=niche_pulse,
        account_perf=account_perf,
        negatives_sync=negatives_sync,
        forecast=forecast,
        compliance=compliance,
    )
    report_json = build_report_json(
        ranked, clusters_data, competitor_intel, negatives,
        brief_text, run_dir,
        niche_pulse=niche_pulse,
        account_perf=account_perf,
        negatives_sync=negatives_sync,
        forecast=forecast,
        compliance=compliance,
        next_steps=next_steps_list,
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
