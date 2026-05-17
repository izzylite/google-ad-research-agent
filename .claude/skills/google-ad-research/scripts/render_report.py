# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "tabulate>=0.9.0",
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
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
  {run_dir}/report.html
  {run_dir}/report.pdf  (best-effort — requires Edge/Chrome/Chromium on PATH)

Exports: render_full_report(), build_report_json()
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
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
Serper PAA, Serper related, Serper ads) that surfaced the keyword. Higher diversity = more
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
    "**What this is for:** negative keywords block irrelevant searches from "
    "triggering your ads. Untreated noise (recruitment queries, DIY "
    "tutorials, wrong-audience searches, far-away geos) eats budget without "
    "ever converting. Adding these up front prevents the bleed.\n\n"
    "**Tier glossary** — read this before scrolling the list:\n\n"
    "- **Strong** = zero plausible buyer intent for this campaign. "
    "Recruitment (`jobs`, `careers`), DIY (`how to`, `home remedies`), "
    "wrong audience (pediatric for an adult clinic; lawyers when you're a "
    "doctor), wrong geo (other states / far-away cities), wrong reimbursement "
    "model (`free clinic`, `low income`). **Action: add to the campaign on "
    "Day 1, no review needed.**\n"
    "- **Considered** = probably off-target, but depends on positioning. "
    "Direct competitor brand names (you may bid on them as a counter-attack), "
    "price-comparison terms (`cheap`, `discount`), premium qualifiers if "
    "you're a value brand. **Action: read each row's justification against "
    "your brand positioning, then add or skip.**\n"
    "- **Investigate** = edge cases that might be relevant. Related-but-"
    "different insurance regimes, generic out-of-region but possibly-"
    "serviceable areas. **Action: skip on launch. Watch search-term reports "
    "for 2-4 weeks; if these queries actually appear and don't convert, "
    "promote to Strong then.**\n\n"
    "Tip: keywords are also grouped by **category** within each tier "
    "(jobs-careers, free-DIY-tutorial, competitor-brand, wrong-geo, wrong-"
    "audience, used-refurb-wholesale) so you can scan or import in batches."
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
    "**What this is for:** cross-references the negatives we generated "
    "against the negatives already in your Google Ads account, so you only "
    "see net-new candidates to add — no duplicate Editor work.\n\n"
    "**Bucket glossary:**\n\n"
    "- **already in account** = our generated negative already exists in "
    "your account's negative list (matched via normalised string). "
    "**Action: none — already covered.**\n"
    "- **new candidate** = negative isn't in your account yet. "
    "**Action: paste into the Editor from `negatives.csv`.**\n\n"
    "Within the new-candidate bucket, rows keep their **tier** (Strong / "
    "Considered / Investigate — see the Negative Keywords section above "
    "for tier definitions). **Add Strong first, review Considered against "
    "brand positioning, skip Investigate until search-term data justifies "
    "them.**"
)
USAGE_POS_SYNC = (
    "**What this is for:** cross-references our ranked positives against "
    "the live keyword list in your Google Ads account, so you don't waste "
    "Editor imports on keywords that already exist.\n\n"
    "**Bucket glossary:**\n\n"
    "- **already active** = our keyword is already ENABLED in your "
    "campaign (exact match or normalised close variant). "
    "**Action: none — covered.**\n"
    "- **paused in account** = the keyword exists in the account but is "
    "PAUSED. **Action: decide whether to re-enable the existing one, or "
    "add a fresh variant if performance was the reason it was paused.**\n"
    "- **covered by broad** = an active broad / phrase keyword in the "
    "account would already match this query. **Action: none — broad "
    "coverage exists; only narrow into exact if you want tighter ad "
    "copy for a SKAG.**\n"
    "- **new to add** = our keyword is genuinely net-new — not in the "
    "account in any form. **Action: paste from `positives.csv` into "
    "the Editor.**\n\n"
    "Bucket detection runs a normalised string match first, then a Claude "
    "re-tag pass (Step 34a) catches token reorders, semantic synonyms "
    "(e.g. *physician* = *doctor*), and match-type drift. The `retag_"
    "reason` field on individual rows in `positives-sync.json` shows which "
    "rule applied."
)

TIER_ORDER = ["Strong", "Considered", "Investigate"]

# EXPT-05: canonical Export Files manifest. Drives both the report.md section
# and the report.json exports[] array. Order matters — files appear in this
# order in the bullet list and the JSON array.
_EXPORT_FILE_DESCRIPTIONS: list[tuple[str, str]] = [
    ("positives.csv", "keywords, ad-group assignments, suggested Max CPC."),
    ("negatives.csv", "tiered negatives with Level column (campaign vs ad_group)."),
    ("ad_groups.csv", "ad group definitions with Default Max CPC."),
]

# ADGM-06: strict `>` threshold for the Next Steps step-3 rewrite. When
# ad_group_mapping.mapping_coverage_pct exceeds this value, step 3 is
# rewritten from "Create ad groups: ..." to "Add keywords to existing ad
# groups: ...". 50.0 exactly does NOT trigger the rewrite (Pitfall 7 /
# Open-Q 4 strict-greater-than gate). Single source of truth for tuning.
_COVERAGE_REWRITE_PCT: float = 50.0

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
    "Strong": (
        "Zero plausible buyer intent (jobs, DIY, wrong audience, wrong "
        "geo, wrong reimbursement model). **Add to all campaigns "
        "unconditionally on Day 1.**"
    ),
    "Considered": (
        "Probably off-target but depends on positioning (competitor "
        "brands, price-comparison terms, premium/value qualifiers). "
        "**Read each justification against your brand stance, then add "
        "or skip.**"
    ),
    "Investigate": (
        "Edge cases that *might* be relevant (related insurance regimes, "
        "borderline geos). **Skip on launch. Promote to Strong if they "
        "appear in search-term reports without converting.**"
    ),
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


def _load_competitor_landing_pages(run_dir: Path) -> dict:
    """Load raw/competitor-landing-pages.json (Phase 12 WFCH-02).

    Returns {} if file absent — graceful degrade. Wave 0
    test_competitor_section_joins_webfetch_results asserts on
    hasattr(render_report, '_load_competitor_landing_pages') to lift its
    skip-guard, so this symbol is the sentinel that wires WFCH-02.
    """
    path = run_dir / "raw" / "competitor-landing-pages.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _normalise_domain(domain: str | None) -> str:
    """Case-insensitive + leading-www-strip for JOIN matching."""
    if not domain:
        return ""
    return domain.lower().removeprefix("www.")


def _join_advertisers_with_landing_pages(
    advertisers: list[dict],
    cluster_name: str,
    landing_pages_doc: dict,
) -> list[dict]:
    """Per (cluster, domain) JOIN — overlay headline/cta/offer onto Serper advertiser entries.

    Each output entry is the original Serper advertiser dict augmented with optional
    `headline`, `cta`, `offer`, `extract_status` keys when a matching landing-pages
    record exists. Domain match is case-insensitive with `www.` stripped on both sides.
    """
    lp_cluster = landing_pages_doc.get("clusters", {}).get(cluster_name, {})
    lp_advertisers = lp_cluster.get("advertisers", [])
    lp_by_domain = {_normalise_domain(a.get("domain")): a for a in lp_advertisers}

    out = []
    for adv in advertisers:
        joined = dict(adv)
        lp = lp_by_domain.get(_normalise_domain(adv.get("domain")))
        if lp:
            joined["headline"] = lp.get("headline")
            joined["cta"] = lp.get("cta")
            joined["offer"] = lp.get("offer")
            joined["extract_status"] = lp.get("extract_status")
        out.append(joined)
    return out


def render_competitor_section(competitor_intel: dict, run_dir: Path | None = None) -> str:
    """Render the Competitor Ad Copy section.

    When `raw/competitor-landing-pages.json` (Phase 12 WFCH-02) is present, the
    section JOINs WebFetch-extracted headline/CTA/offer onto each Serper advertiser
    by (cluster_name, domain). Falls back to Serper ad title/description for
    advertisers without a landing-pages entry, or when `extract_status == "failed"`.

    `run_dir` is optional for backward compatibility: when omitted, no JOIN is
    attempted and the legacy Serper-only rendering applies.
    """
    parts = ["## Competitor Ad Copy\n\n", USAGE_COMPETITORS, "\n"]
    clusters = competitor_intel.get("clusters", {})
    if not clusters:
        parts.append("\n_No competitor ad copy extracted for this run._\n")
        return "".join(parts)

    landing_pages = _load_competitor_landing_pages(run_dir) if run_dir else {}

    for cluster_name, cluster_data in clusters.items():
        escaped_name = escape_md_cell(cluster_name)
        source_label = cluster_data.get("advertiser_source", "ads")
        parts.append(f"\n### {escaped_name}  \n_(source: {source_label})_\n")
        ads = cluster_data.get("ads", [])
        advertisers = cluster_data.get("advertisers", [])
        if advertisers and landing_pages:
            advertisers = _join_advertisers_with_landing_pages(
                advertisers, cluster_name, landing_pages,
            )

        # Prefer advertisers (richer data — JOINed with WebFetch LP content when present)
        if advertisers:
            for adv in advertisers:
                title = (adv.get("ad_title") or adv.get("title") or "").strip()
                desc = (adv.get("ad_description") or adv.get("description") or "").strip()
                domain = adv.get("domain", "") or ""
                url = adv.get("url", "") or ""
                # WebFetch-extracted fields (present after WFCH-02 JOIN)
                headline_lp = (adv.get("headline") or "").strip()
                cta = (adv.get("cta") or "").strip()
                offer = (adv.get("offer") or "").strip()
                extract_status = adv.get("extract_status")

                if headline_lp:
                    # Landing-page headline wins as the bold line; CTA + offer
                    # render as sub-bullets. Serper title (ad copy) shown below
                    # for additional context.
                    parts.append(f"- **{escape_md_cell(headline_lp)}**\n")
                    if cta:
                        parts.append(f"  - CTA: {escape_md_cell(cta)}\n")
                    if offer:
                        parts.append(f"  - Offer: {escape_md_cell(offer)}\n")
                    if title:
                        parts.append(f"  - Ad title: {escape_md_cell(title)}\n")
                    if desc:
                        parts.append(f"  - Ad description: {escape_md_cell(desc)}\n")
                    if domain:
                        parts.append(f"  - Domain: `{escape_md_cell(domain)}`\n")
                    if url:
                        parts.append(f"  - URL: <{escape_md_cell(url)}>\n")
                else:
                    # No WebFetch landing-page data — fall back to ad title/description.
                    # Headline fallback chain: ad_title → domain → "(no headline)"
                    headline = title if title else (domain if domain else "(no headline extracted)")
                    parts.append(f"- **{escape_md_cell(headline)}**\n")
                    if desc:
                        parts.append(f"  - {escape_md_cell(desc)}\n")
                    if extract_status == "failed":
                        parts.append("  - _(landing page extraction failed)_\n")
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


def render_account_perf_section(
    perf: dict, campaign_focus: list[str] | None = None,
) -> str:
    """Render the Account Performance section (markdown).

    When ``campaign_focus`` is non-empty, the section is labelled
    "Campaign Performance" because perf_fetch narrowed the raw data to
    those campaigns — "Account Performance" would misrepresent scope.
    """
    if not perf or not isinstance(perf, dict):
        return ""
    heading = "Campaign Performance" if campaign_focus else "Account Performance"
    parts = [
        f"## {heading} — last {perf.get('horizon_days', 30)} days\n\n",
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
    parts.append(
        "\n_Real user queries that triggered a conversion in the last 30 "
        "days — not your bid keywords, what was actually typed. These prove "
        "buyer intent. **Action:** bid harder on the matching keywords, or "
        "promote them into a dedicated single-keyword ad group with tighter "
        "ad copy._\n"
    )
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
    parts.append(
        "\n_Queries that got clicks but never converted — they're eating "
        "budget. **Action:** add as Strong negatives unless the gap is "
        "attribution lag (long sales cycle) or the query is genuinely "
        "relevant and just needs better landing-page match._\n"
    )
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
    parts.append(
        "\n_Revenue per ad dollar (1.0x = breakeven, 3.0x = $3 returned per "
        "$1 spent). **Action:** scale top performers (add budget); pause "
        "anything well below your target ROAS. With a `Campaign focus:` set "
        "in the brief, this narrows to the targeted campaign(s) only._\n"
    )
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


def render_positives_sync_section(sync: dict) -> str:
    """POS-03: Render the Positives Sync section.

    Mirrors render_negatives_sync_section. Returns "" when sync is None /
    empty (graceful omit per POS-05 — caller appends unconditionally).

    Bucket display strategy:
        - new_to_add        enumerated (this is what the operator acts on)
        - already_active    count-only (audit trail, full list in JSON)
        - paused_in_account count-only
        - covered_by_broad  count-only
    """
    if not sync or not isinstance(sync, dict):
        return ""
    stats = sync.get("stats") or {}
    if not stats:
        return ""

    parts = [
        "## Positives Sync\n\n",
        USAGE_POS_SYNC, "\n",
        f"\n**Stats:** our list = {stats.get('our_total', 0)} · "
        f"already active = {stats.get('already_active', 0)} · "
        f"paused = {stats.get('paused_in_account', 0)} · "
        f"covered by broad = {stats.get('covered_by_broad', 0)} · "
        f"new to add = **{stats.get('new_to_add', 0)}**\n",
    ]

    new_to_add = sync.get("new_to_add") or []
    parts.append(f"\n### New positives to add ({len(new_to_add)})\n\n")
    if not new_to_add:
        parts.append(
            "_None — your ranked list is fully covered by the active "
            "account._\n"
        )
    else:
        for r in new_to_add:
            kw = escape_md_cell(r.get("keyword", ""))
            intent = r.get("intent", "") or ""
            just = escape_md_cell(
                r.get("justification", "") or r.get("theme", "") or ""
            )
            if just:
                parts.append(f"- `{kw}` · _{intent}_ — {just}\n")
            else:
                parts.append(f"- `{kw}` · _{intent}_\n")

    # Count-only audit sections — operator drills into positives-sync.json
    # for full per-row data. Keeps the report scannable.
    for label, key in (
        ("Already active", "already_active"),
        ("Paused in account", "paused_in_account"),
        ("Covered by broad-match", "covered_by_broad"),
    ):
        items = sync.get(key) or []
        parts.append(f"\n### {label} ({len(items)})\n")
        parts.append("_See positives-sync.json for the full list._\n")

    return "".join(parts)


def render_compliance_warning(compliance: dict | None) -> str:
    """Render the ⚠ Compliance Required block (CMPL-03) as markdown blockquote.

    Returns an empty string when compliance is None or matched_verticals is
    empty / absent — caller can append unconditionally; graceful-degrade is
    built in. Pipe characters and other table-hostile content in policy_note
    + evidence_tokens are sanitised via escape_md_cell so downstream tooling
    that reads the markdown line-by-line stays safe.

    Block sits immediately after the header + HOW_TO_READ and BEFORE all
    other sections (above Account Perf, Clusters, Negatives,
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


def render_geographic_focus_section(brief_fields: dict[str, str]) -> str:
    """GEO-05: render the '## Geographic Focus' callout for geo-targeted briefs.

    Returns markdown with the location → focus line, or '' when geo_focus is
    empty (graceful degrade — caller appends unconditionally). Pipes / angle
    brackets / smart quotes routed through escape_md_cell for HTML safety
    inside the rendered markdown.

        ## Geographic Focus

        **Location:** Florida → **Focus:** Palm Beach County, Lake Worth
    """
    geo_focus = (brief_fields or {}).get("geo_focus", "").strip()
    if not geo_focus:
        return ""
    location = (brief_fields or {}).get("location", "").strip() or "(location unset)"
    return (
        "## Geographic Focus\n\n"
        f"**Location:** {escape_md_cell(location)} → "
        f"**Focus:** {escape_md_cell(geo_focus)}\n\n"
    )


def _split_campaign_focus(raw: str) -> list[str]:
    """Mirror perf_fetch.py pipe-split heuristic: space-pipe-space (' | ')
    stays as ONE Google-Ads naming-convention campaign name; bare '|' splits
    into a list. Empty raw → []."""
    raw = (raw or "").strip()
    if not raw:
        return []
    if "|" in raw and " | " not in raw:
        return [n.strip() for n in raw.split("|") if n.strip()]
    return [raw]


def render_campaign_focus_section(
    brief_fields: dict[str, str],
    *,
    perf_path: Path | None = None,
) -> str:
    """CAMP-05: render the '## Campaign Focus' callout + validate vs perf.json.

    Returns markdown with:
        - Empty string when brief_fields["campaign_focus"] is empty.
        - Single-campaign block: `**Campaign:** <name>`
        - Multi-campaign bulleted list (one name per line).
        - Either form may include a `> ⚠ Campaign name not found in
          account: '<name>' — check for typo` line per mismatched name when
          perf_path is provided and the name is absent from the campaigns
          list (case-sensitive — Google Ads campaign names are unique +
          case-preserved by the API).

    Pipes / angle brackets inside campaign names are NOT routed through
    escape_md_cell — Google Ads campaign names like
    `Search | Lake Worth Accident Exams | Manual CPC` deliberately use
    pipes as a labelling convention, and escaping breaks operator
    recognition. (Phase 11 GEO-05 escapes because city names rarely contain
    markdown-special chars.)
    """
    raw = (brief_fields or {}).get("campaign_focus", "").strip()
    if not raw:
        return ""

    names = _split_campaign_focus(raw)

    # Validate against perf.json campaigns list when path provided.
    warnings: list[str] = []
    if perf_path is not None:
        try:
            perf_data = json.loads(Path(perf_path).read_text(encoding="utf-8"))
            known = {c.get("name", "") for c in perf_data.get("campaigns", [])}
            for n in names:
                if n not in known:
                    warnings.append(
                        f"> ⚠ Campaign name not found in account: '{n}' "
                        f"— check for typo\n"
                    )
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            # Graceful: validation needs the file to exist + parse.
            pass

    parts: list[str] = ["## Campaign Focus\n\n"]
    if len(names) == 1:
        parts.append(f"**Campaign:** {names[0]}\n\n")
    else:
        for n in names:
            parts.append(f"- {n}\n")
        parts.append("\n")
    parts.extend(warnings)
    if warnings:
        parts.append("\n")
    return "".join(parts)


def _load_ad_group_mapping_for_render(run_dir: Path) -> dict | None:
    """Mirror of export_csv._load_ad_group_mapping (kept module-local to avoid
    cross-script imports). Returns None when ad-group-mapping.json is absent
    or unparseable — backward compat: render proceeds with standard step-3.
    """
    mapping_path = run_dir / "ad-group-mapping.json"
    if not mapping_path.exists():
        return None
    try:
        return json.loads(mapping_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_existing_ad_groups(run_dir: Path) -> list[dict] | None:
    """Load `raw/google-ads-perf.json` ad_groups list so the Mapping section
    can always enumerate the operator's account structure, even when no
    keyword matches an existing ad group with high/medium confidence.

    Returns None when perf data is absent or unparseable.
    """
    perf_path = run_dir / "raw" / "google-ads-perf.json"
    if not perf_path.exists():
        return None
    try:
        data = json.loads(perf_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    ags = data.get("ad_groups") or []
    if not ags:
        return None
    return ags


def render_ad_group_mapping_section(
    ad_group_mapping: dict | None,
    existing_ad_groups: list[dict] | None = None,
) -> str:
    """Render the Ad Group Mapping section (ADGM-04 visualization).

    Returns "" when ad_group_mapping is None/empty — caller appends
    unconditionally; graceful-degrade built in.

    Sections:
      * Coverage % + tier counts (high/medium/low)
      * Top 15 matches table (Keyword | Existing Ad Group | Confidence | Score)
      * Keywords by Existing Ad Group (when matched count > 0)
      * Existing Ad Groups in Account (always when perf data present — lets
        operator see their full account structure even when no kw matched
        with high/medium confidence)
      * Unmapped count
    """
    if not ad_group_mapping or not isinstance(ad_group_mapping, dict):
        return ""
    matches = ad_group_mapping.get("matches") or []
    if not matches:
        return ""

    high = sum(1 for m in matches if m.get("confidence") == "high")
    medium = sum(1 for m in matches if m.get("confidence") == "medium")
    low = sum(1 for m in matches if m.get("confidence") == "low")
    total = len(matches)
    coverage = ad_group_mapping.get("mapping_coverage_pct", 0.0) or 0.0
    skipped_reason = ad_group_mapping.get("skipped_reason")

    parts = ["## Ad Group Mapping\n\n"]
    if skipped_reason:
        parts.append(
            f"_Skipped: {escape_md_cell(skipped_reason)}._\n\n"
        )
        return "".join(parts)

    parts.append(
        "_Maps our ranked keywords to your existing Google Ads ad groups via "
        "Jaccard token overlap × intent match (Phase 8 perf data). "
        "**High** = ≥0.7 (paste into existing); **medium** = 0.4–0.7 (review "
        "first); **low** = <0.4 (create new ad group)._\n\n"
    )
    parts.append(
        f"**Coverage:** {coverage:.1f}% "
        f"(high+medium of {total} ranked keywords) · "
        f"High **{high}** · Medium **{medium}** · Low **{low}**\n\n"
    )

    mapped = [
        m for m in matches if m.get("confidence") in ("high", "medium")
    ]
    if mapped:
        # Sort by score descending; top 15 flat view.
        mapped_sorted = sorted(
            mapped, key=lambda m: m.get("score", 0) or 0, reverse=True
        )[:15]
        rows = [
            [
                escape_md_cell(m.get("keyword", "")),
                escape_md_cell(m.get("existing_ad_group", "")),
                escape_md_cell(m.get("confidence", "")),
                f"{(m.get('score', 0) or 0):.2f}",
            ]
            for m in mapped_sorted
        ]
        headers = ["Keyword", "Existing Ad Group", "Confidence", "Score"]
        parts.append("### Matched Keywords (top 15)\n\n")
        parts.append(tabulate(rows, headers=headers, tablefmt="github"))
        parts.append("\n\n")

        # Grouped view — team's "sort by structure" request: same-ad-group
        # keywords listed under each existing ad group header for paste-and-go.
        from collections import defaultdict
        by_ag: dict[str, list[dict]] = defaultdict(list)
        for m in mapped:
            by_ag[m.get("existing_ad_group", "") or "(unknown)"].append(m)
        parts.append("### Keywords by Existing Ad Group\n\n")
        parts.append(
            "_Same-ad-group keywords contiguous. positives.csv is sorted to "
            "match — paste each block into the corresponding existing ad "
            "group in Google Ads Editor._\n\n"
        )
        for ag_name in sorted(by_ag.keys(), key=lambda s: s.lower()):
            kw_list = sorted(
                by_ag[ag_name],
                key=lambda m: m.get("score", 0) or 0,
                reverse=True,
            )
            parts.append(
                f"**{escape_md_cell(ag_name)}** "
                f"<span style=\"color:#666\">({len(kw_list)} keyword"
                f"{'s' if len(kw_list) != 1 else ''})</span>\n\n"
            )
            for m in kw_list:
                kw = escape_md_cell(m.get("keyword", ""))
                conf = m.get("confidence", "")
                score = m.get("score", 0) or 0
                parts.append(
                    f"- {kw} <span class=\"cluster-meta\">"
                    f"{conf} · {score:.2f}</span>\n"
                )
            parts.append("\n")
    else:
        parts.append(
            "_No high or medium-confidence matches in this run. All ranked "
            "keywords fall back to new cluster ad groups (see Ad Group "
            "Clusters section above)._\n\n"
        )

    if low:
        parts.append(
            f"_{low} low-confidence keyword(s) routed to new cluster ad "
            f"groups (cluster slug used as ad group name in positives.csv)._\n\n"
        )

    # Existing ad groups list — surfaces operator's account structure even
    # when no kw matched with high/medium confidence. Without this, low-Jaccard
    # accounts (short AG names vs long ranked kw) leave the operator unable
    # to see which ad groups they actually have. Dedup by (name, campaign)
    # to avoid noise from repeat names across campaigns.
    if existing_ad_groups:
        seen: set[tuple[str, str]] = set()
        deduped: list[dict] = []
        for ag in existing_ad_groups:
            name = (ag.get("name") or "").strip()
            campaign = (ag.get("campaign_name") or "").strip()
            key = (name.lower(), campaign.lower())
            if not name or key in seen:
                continue
            seen.add(key)
            deduped.append(ag)
        if deduped:
            # Sort by clicks desc so active ad groups surface first; alpha
            # tiebreak for stable rendering across runs.
            deduped.sort(
                key=lambda a: (
                    -(a.get("clicks") or 0),
                    (a.get("name") or "").lower(),
                )
            )
            parts.append(
                f"### Existing Ad Groups in Account ({len(deduped)})\n\n"
            )
            parts.append(
                "_Your full account structure pulled from Phase 8 perf data. "
                "Listed here regardless of match quality so you can manually "
                "pick a destination ad group when the algorithm cannot find "
                "a confident bucket._\n\n"
            )
            rows = []
            for ag in deduped:
                clicks = ag.get("clicks") or 0
                impr = ag.get("impressions") or 0
                cost = ag.get("cost_usd") or 0.0
                conv = ag.get("conversions") or 0
                rows.append([
                    escape_md_cell(ag.get("name", "")),
                    escape_md_cell(ag.get("campaign_name", "")),
                    escape_md_cell(ag.get("status", "")),
                    f"{int(clicks)}" if clicks else "—",
                    f"{int(impr)}" if impr else "—",
                    f"${cost:,.0f}" if cost else "—",
                    f"{conv:.0f}" if conv else "—",
                ])
            parts.append(
                tabulate(
                    rows,
                    headers=[
                        "Ad Group", "Campaign", "Status",
                        "Clicks", "Impr", "Cost", "Conv",
                    ],
                    tablefmt="github",
                )
            )
            parts.append("\n\n")

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
        "**What this is for:** previews what this keyword list would cost "
        "to run, before you commit budget. Each cluster gets **low / mid / "
        "high** bands for daily clicks, daily spend, and a mid monthly "
        "total. The bands capture auction volatility — actual numbers "
        "land inside the range on most accounts.\n\n"
        "**How to use:**\n\n"
        "1. **Set Day 1 daily budget** from the campaign **mid** total. "
        "If it exceeds the client's cap, trim informational clusters or "
        "tighten Max CPCs in [Suggested CPC] before launch.\n"
        "2. **Sanity-check ROAS.** Mid spend × target CPA = conversions "
        "needed to break even. If that number looks unrealistic given "
        "the mid clicks band, the brief needs more budget or a "
        "narrower keyword scope.\n"
        "3. **Brief stakeholders with low / high.** Use the low band "
        "to show downside risk; use high to set upside expectations. "
        "Have that conversation **before** launch, not after week 1.\n\n"
        "_Directional only — not Google's Performance Planner. Real "
        "numbers shift ±30-50% with ad relevance, quality scores, and "
        "seasonality. Re-run forecast after 2 weeks of live data for "
        "an account-calibrated version._\n\n"
    )

    # FRCS-06 over-cap warning — sits ABOVE the cluster table so the operator
    # sees the scope mismatch before scrolling the numbers.
    clamp = forecast.get("budget_clamp")
    if clamp and clamp.get("over_cap_ratio") is not None and clamp["over_cap_ratio"] > 1.0:
        parts.append(
            f"> ⚠ **Forecast is {clamp['over_cap_ratio']}x your "
            f"${clamp['daily_cap_usd']:.2f}/day cap.** The full keyword "
            f"pool can't be bid at this budget. See the **What Fits Your "
            f"Cap** subsection below for the priority-sorted launch list "
            f"({clamp['fitting_count']} keywords, "
            f"${clamp['cumulative_spend_mid_usd']:.2f}/day mid). The "
            f"keywords NOT in the launch list stay in research output for "
            f"future campaign expansion (either they'd push spend over cap, "
            f"or they lack the volume/CPC data needed to forecast).\n\n"
        )
    elif clamp and clamp.get("over_cap_ratio") is not None:
        parts.append(
            f"> ✓ **Forecast fits your ${clamp['daily_cap_usd']:.2f}/day cap** "
            f"({clamp['over_cap_ratio']}x ratio). All {clamp['fitting_count']} "
            f"bidable keywords land within budget — full pool is the launch "
            f"list.\n\n"
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

    # FRCS-06: "What fits your cap" priority-sorted launch list — only renders
    # when brief carries `**Budget:**`. Operator sees the actual keywords they
    # should put behind the budget cap, sorted highest-intent first with a
    # running cumulative spend column so they can eyeball the cutoff.
    if clamp and clamp.get("keywords_fitting_cap"):
        parts.append("\n### What Fits Your Cap\n\n")
        parts.append(
            f"_Priority-sorted launch list at the **${clamp['daily_cap_usd']:.2f}/day** "
            f"cap. Sort: transactional → commercial → navigational → informational; "
            f"within each, signal_count desc then score desc. Cumulative spend "
            f"tops out at **${clamp['cumulative_spend_mid_usd']:.2f}/day "
            f"({clamp['fitting_count']} keywords)** — well within the "
            f"${clamp['daily_cap_usd']:.2f}/day cap. This is your Day 1 "
            f"launch list; everything else stays in research output for "
            f"future expansion._\n\n"
        )
        rows = []
        for r in clamp["keywords_fitting_cap"]:
            rows.append([
                escape_md_cell(r.get("keyword", "")),
                escape_md_cell(r.get("intent", "")),
                escape_md_cell(r.get("cluster", "")),
                r.get("score", 0),
                f"${r.get('daily_spend_mid_usd', 0):.2f}",
                f"${r.get('cumulative_spend_usd', 0):.2f}",
            ])
        parts.append(tabulate(
            rows,
            headers=[
                "Keyword", "Intent", "Cluster",
                "Score", "Daily Spend Mid", "Cumulative",
            ],
            tablefmt="github",
        ))
        parts.append("\n\n")
        if clamp.get("keywords_dropped"):
            dropped_preview = clamp["keywords_dropped"][:10]
            more = len(clamp["keywords_dropped"]) - len(dropped_preview)
            preview_str = ", ".join(
                f"`{escape_md_cell(k)}`" for k in dropped_preview
            )
            parts.append(
                f"**Dropped from launch list** ({clamp['dropped_count']} "
                f"keywords): {preview_str}"
            )
            if more > 0:
                parts.append(f", and {more} more")
            parts.append(
                ". See `forecast.json` → `budget_clamp.keywords_dropped[]` "
                "for the complete list.\n\n"
            )

    # FRCS-07: "Deferred Brand Conquest" subsection — only renders when the
    # budget-clamp identified competitor brand-navigational keywords that
    # should NOT enter the launch list at this budget tier. Surfaces them
    # as Consider-negative candidates with the operator's reasoning so they
    # can be flipped to negatives in the Editor or re-enabled when budget
    # grows. Skip when brand_conquest_override is set (operator opted in).
    if (
        clamp
        and clamp.get("brand_conquest_active")
        and clamp.get("keywords_deferred_brand_conquest")
    ):
        deferred = clamp["keywords_deferred_brand_conquest"]
        threshold = clamp.get("brand_conquest_threshold_usd", 200.0)
        deferred_spend = clamp.get("deferred_brand_conquest_spend_usd", 0.0)
        parts.append("\n### Deferred Brand Conquest (Consider as Negatives)\n\n")
        parts.append(
            f"_At your **${clamp['daily_cap_usd']:.2f}/day** cap (below the "
            f"**${threshold:.2f}/day** brand-conquest threshold), the skill "
            f"deferred **{len(deferred)} competitor brand-navigational "
            f"keywords** from the launch list — they would have consumed "
            f"**${deferred_spend:.2f}/day** ({deferred_spend / clamp['daily_cap_usd'] * 100:.0f}% "
            f"of your budget) on conquest attempts at 2-3x normal CPC._\n\n"
            f"**Recommended action: add these as Considered-tier negatives "
            f"in your campaign instead.** Bidding competitor brands at this "
            f"budget burns money against advertisers with 8+ Quality Score "
            f"on their own brand, with no Smart Bidding data yet to know if "
            f"conquest CPL is even visible.\n\n"
            f"**To re-enable** (e.g., when budget grows past "
            f"${threshold:.2f}/day): add `Brand conquest: yes` to the brief "
            f"and re-run forecast — the deferred keywords will compete for "
            f"the launch list like any other navigational keyword.\n\n"
        )
        rows = []
        for r in deferred:
            rows.append([
                escape_md_cell(r.get("keyword", "")),
                escape_md_cell(r.get("cluster", "")),
                f"${r.get('daily_spend_mid_usd', 0):.2f}",
                r.get("score", 0),
            ])
        parts.append(tabulate(
            rows,
            headers=["Keyword (→ Add as Negative)", "From Cluster",
                     "Would Have Spent", "Score"],
            tablefmt="github",
        ))
        parts.append("\n\n")

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
    """Extract industry, product, location, language, audience, geo_focus, campaign_focus from brief.md.

    Looks for "**Field:** value" pattern (case-insensitive field matching).
    GEO-05 extension: also reads the optional `**Geo focus:**` list-item line
    (e.g. `- **Geo focus:** Palm Beach County, Lake Worth`) and exposes the
    comma-joined raw value under key `"geo_focus"`. Empty string when absent
    (graceful degrade — Phase 11 callers omit the section).
    CAMP-01 extension: also reads the optional `**Campaign focus:**` list-item
    line and exposes the raw value under key `"campaign_focus"`. Empty string
    when absent (mirrors geo_focus contract — Plan 15-02 callers omit the
    section).
    """
    fields = ["industry", "product", "location", "language", "audience"]
    result: dict[str, str] = {}
    # Brief template (SKILL.md Step 4) emits `**Field:** value`. Older Phase 6
    # code used `\*\*(\w+)\*\*:` (asterisks BEFORE colon), which never matches
    # the template — leaving location/industry empty for all downstream
    # consumers (GEO-05 callout, Next Steps location substitution,
    # report.json.brief). Accept both forms for robustness.
    for line in brief_text.splitlines():
        m = re.search(r"\*\*(\w+):\*\*\s*(.+)", line) or re.search(
            r"\*\*(\w+)\*\*:\s*(.+)", line
        )
        if m:
            key = m.group(1).lower()
            value = m.group(2).strip()
            if key in fields:
                result[key] = value

    # GEO-05: optional "**Geo focus:**" line. Tolerates leading list markers
    # (-, *) and whitespace so both bare and bulleted forms parse identically.
    geo_match = re.search(
        r"^[-*\s]*\*\*Geo\s*focus:\*\*\s*(.+)$",
        brief_text,
        re.IGNORECASE | re.MULTILINE,
    )
    result["geo_focus"] = geo_match.group(1).strip() if geo_match else ""

    # CAMP-01: optional "**Campaign focus:**" line. Tolerates leading list
    # markers (-, *) and whitespace so both bare and bulleted forms parse
    # identically. Mirrors GEO-05 regex shape.
    camp_match = re.search(
        r"^[-*\s]*\*\*Campaign\s*focus:\*\*\s*(.+)$",
        brief_text,
        re.IGNORECASE | re.MULTILINE,
    )
    result["campaign_focus"] = camp_match.group(1).strip() if camp_match else ""
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


def _scan_exports(run_dir: Path) -> list[tuple[str, str]]:
    """Scan {run_dir}/export/ for canonical CSVs. Returns list of
    (filename, description) tuples in canonical order, or [] when absent.
    """
    export_dir = run_dir / "export"
    if not export_dir.exists() or not export_dir.is_dir():
        return []
    return [
        (name, desc)
        for name, desc in _EXPORT_FILE_DESCRIPTIONS
        if (export_dir / name).exists()
    ]


def list_export_paths(run_dir: Path) -> list[str]:
    """Return POSIX-style relative export paths for report.json.exports[]."""
    return [f"export/{name}" for name, _ in _scan_exports(run_dir)]


def render_export_section(run_dir: Path) -> str:
    """Render the Export Files section (EXPT-05) as markdown string.

    Graceful degrade: missing export/ dir OR all 3 CSVs absent → "".
    Partial presence: lists only files that exist.
    """
    present = _scan_exports(run_dir)
    if not present:
        return ""
    parts = [
        "## Export Files\n\n",
        "_Google Ads Editor v2.x-importable CSVs produced by `export_csv.py`. "
        "Paths are relative to this run folder._\n\n",
    ]
    for name, desc in present:
        parts.append(f"- `export/{name}` — {desc}\n")
    parts.append("\n")
    return "".join(parts)


def render_next_steps_section(
    brief_fields: dict[str, str],
    forecast: dict | None,
    compliance: dict | None,
    clusters_data: dict,
    ad_group_mapping: dict | None = None,
) -> tuple[str, list[dict]]:
    """Render the Next Steps checklist (STEP-01..04 + CMPL-05 + ADGM-06).

    Returns (markdown_string, step_list) where step_list is the canonical
    ordered list of step dicts shared by report.md, report.json, and the
    HTML renderer. Step numbers are derived from final list position so the
    CMPL-05 reorder (compliance present -> verification step prepended)
    never produces wrong numbering.

    Rules:
        - 8 standard ops steps from the locked template.
        - ADGM-06: if ad_group_mapping is supplied AND its
          mapping_coverage_pct is strictly greater than _COVERAGE_REWRITE_PCT
          (50.0), step 3 is rewritten from "Create ad groups: ..." to
          "Add keywords to existing ad groups: <name> (<N> kw), ...".
          Groups ordered by descending match count, alphabetical tie-break.
          The rewrite happens BEFORE the compliance prepend so it always
          targets the original template index 2 (not the post-prepend index).
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

    # ADGM-06: conditional step-3 rewrite when mapping coverage exceeds threshold.
    # Applied to the static template index (2) BEFORE compliance prepend, so
    # the original "Create ad groups" slot is targeted regardless of CMPL-05.
    if ad_group_mapping:
        try:
            coverage = float(
                ad_group_mapping.get("mapping_coverage_pct", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            coverage = 0.0
        if coverage > _COVERAGE_REWRITE_PCT:
            from collections import Counter
            by_ag: Counter[str] = Counter()
            for m in ad_group_mapping.get("matches", []) or []:
                if m.get("confidence") not in {"high", "medium"}:
                    continue
                name = m.get("existing_ad_group")
                if name:
                    by_ag[name] += 1
            if by_ag:
                # Descending by count, alphabetical tie-break for stable output.
                ordered = sorted(by_ag.items(), key=lambda kv: (-kv[1], kv[0]))
                add_to = ", ".join(f"{name} ({n} kw)" for name, n in ordered)
                steps_text[2] = (
                    f"Add keywords to existing ad groups: {add_to}."
                )

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
    account_perf: dict | None = None,
    negatives_sync: dict | None = None,
    positives_sync: dict | None = None,
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

    # Section order: action items first (clusters, negatives), reference
    # data last (full ranked keyword table, competitor LP details).
    # Operator scrolls less to find what to do this week.
    # Detect whether Ahrefs enrichment is present (any row w/ a volume value)
    has_enrichment = any(
        r.get("volume") is not None for r in ranked
    )

    sections = [
        header,
        HOW_TO_READ,
    ]
    # GEO-05: Geographic Focus callout sits between header/HOW_TO_READ and
    # the compliance warning so operators see the geo targeting context
    # before any keyword work. Empty string when brief has no Geo focus line.
    brief_fields_for_geo = _parse_brief_fields(brief_text)
    geo_md = render_geographic_focus_section(brief_fields_for_geo)
    if geo_md:
        sections.append("\n")
        sections.append(geo_md)
    # CAMP-05: Campaign Focus callout sits between Geographic Focus and the
    # compliance warning so operators see the narrowed scope context before
    # any keyword work. Empty string when brief has no Campaign focus line.
    # Validates focus names against raw/google-ads-perf.json when present —
    # mismatched names trigger a typo warning (CAMP-05).
    _perf_path_for_camp = run_dir / "raw" / "google-ads-perf.json"
    camp_md = render_campaign_focus_section(
        brief_fields_for_geo,
        perf_path=_perf_path_for_camp if _perf_path_for_camp.exists() else None,
    )
    if camp_md:
        sections.append("\n")
        sections.append(camp_md)
    # Compliance warning ABOVE all other sections (CMPL-03) — operator's
    # first signal before they look at keywords / clusters / negatives. Empty
    # string when matched_verticals is empty/absent (graceful degrade).
    compliance_md = render_compliance_warning(compliance)
    if compliance_md:
        sections.append("\n")
        sections.append(compliance_md)
    # Account perf first (real campaign data, action-this-week)
    if account_perf:
        sections.append("\n")
        _camp_focus_for_perf = _split_campaign_focus(
            (brief_fields_for_geo.get("campaign_focus") or "").strip()
        )
        sections.append(render_account_perf_section(
            account_perf, campaign_focus=_camp_focus_for_perf,
        ))
    # Negatives sync (action: what to add to account)
    if negatives_sync:
        sections.append("\n")
        sections.append(render_negatives_sync_section(negatives_sync))
    # Positives sync (Phase 14 POS-03) — sits adjacent to Negative Keyword
    # Sync. render_positives_sync_section returns "" when sync absent (POS-05).
    if positives_sync:
        sections.append("\n")
        sections.append(render_positives_sync_section(positives_sync))
    # Ad groups (evergreen)
    sections.extend([
        "\n",
        render_clusters_section(clusters_data),
    ])
    # Ad Group Mapping (Phase 11 ADGM-04 visualization) — after Clusters since
    # both are organization-related; mapping shows how export_csv routes
    # keywords to existing client ad groups. Returns "" when no sidecar.
    _ad_group_mapping_for_section = _load_ad_group_mapping_for_render(run_dir)
    _existing_ad_groups_for_section = _load_existing_ad_groups(run_dir)
    mapping_md = render_ad_group_mapping_section(
        _ad_group_mapping_for_section,
        existing_ad_groups=_existing_ad_groups_for_section,
    )
    if mapping_md:
        sections.append("\n")
        sections.append(mapping_md)
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
        render_competitor_section(competitor_intel, run_dir),
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
    # Export Files (EXPT-05) — positioned above Next Steps so file list
    # sits right above the ops checklist that references them.
    export_md = render_export_section(run_dir)
    if export_md:
        sections.append("\n")
        sections.append(export_md)

    # Next Steps (Phase 10 STEP-01..04 + CMPL-05; Phase 11 ADGM-06) — LAST section.
    brief_fields = _parse_brief_fields(brief_text)
    ad_group_mapping = _load_ad_group_mapping_for_render(run_dir)
    next_steps_md, _ = render_next_steps_section(
        brief_fields, forecast, compliance, clusters_data,
        ad_group_mapping=ad_group_mapping,
    )
    sections.append("\n")
    sections.append(next_steps_md)
    return "".join(sections)


def render_html_report(report_json: dict) -> str:
    """Return self-contained HTML report (no external CDN/network deps).

    Embeds report_json as a JS object so the page can offer CSV export of
    every section without round-tripping back to disk.

    Security: API responses (Serper) and WebFetch extracts may contain arbitrary
    remote content including `</script>` strings. Escape so the embedded JSON
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
Serper organic / PAA / related / ads) that surfaced it. The ranking is
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
  <div class="usage">
    <p style="margin:0 0 8px"><strong>What this is for:</strong> previews what this keyword list would cost to run, before you commit budget. Each cluster gets <strong>low / mid / high</strong> bands for daily clicks, daily spend, and a mid monthly total. The bands capture auction volatility — actual numbers land inside the range on most accounts.</p>
    <p style="margin:0 0 4px"><strong>How to use:</strong></p>
    <ol style="margin:0 0 8px;padding-left:20px">
      <li><strong>Set Day 1 daily budget</strong> from the campaign <strong>mid</strong> total. If it exceeds the client's cap, trim informational clusters or tighten Max CPCs before launch.</li>
      <li><strong>Sanity-check ROAS.</strong> Mid spend × target CPA = conversions needed to break even. If that number looks unrealistic given the mid clicks band, the brief needs more budget or a narrower keyword scope.</li>
      <li><strong>Brief stakeholders with low / high.</strong> Use the low band to show downside risk; use high to set upside expectations. Have that conversation <em>before</em> launch, not after week 1.</li>
    </ol>
    <p style="margin:0;font-size:12px;color:#555"><em>Directional only — not Google's Performance Planner. Real numbers shift ±30-50% with ad relevance, quality scores, and seasonality. Re-run forecast after 2 weeks of live data for an account-calibrated version.</em></p>
  </div>
  <div id="forecastContent"></div>
</section>

<section id="account-perf">
  <h2><span id="perfTitle">Account Performance</span> <span class="cluster-meta" id="perfMeta"></span></h2>
  <div class="usage"><strong>How to use:</strong> what your account actually did. <strong>Converted search terms</strong> are gold — bid harder. <strong>Lossy search terms</strong> (clicks no conv) = negative candidates. <strong>Top by ROAS</strong> = scale candidates.</div>
  <div id="perfContent">
    <p style="color:#666;font-size:13px;">No account-perf.json — run Phase 8 perf_fetch + perf_synth.</p>
  </div>
</section>

<section id="negatives-sync">
  <h2>Negative Keyword Sync <span class="cluster-meta" id="negSyncMeta"></span></h2>
  <div class="usage">
    <p style="margin:0 0 8px"><strong>What this is for:</strong> cross-references the negatives we generated against the negatives already in your Google Ads account, so you only see net-new candidates to add — no duplicate Editor work.</p>
    <p style="margin:0 0 4px"><strong>Bucket glossary:</strong></p>
    <ul style="margin:0 0 8px;padding-left:20px">
      <li><strong>already in account</strong> = our generated negative already exists in your account's negative list (matched via normalised string). <em>Action: none — already covered.</em></li>
      <li><strong>new candidate</strong> = negative isn't in your account yet. <em>Action: paste into the Editor from <code>negatives.csv</code>.</em></li>
    </ul>
    <p style="margin:0;font-size:12px;color:#555">Within the new-candidate bucket, rows keep their <strong>tier</strong> (Strong / Considered / Investigate — see the Negative Keywords section below for full tier definitions). <strong>Add Strong first</strong>, review Considered against brand positioning, skip Investigate until search-term data justifies them.</p>
  </div>
  <div id="negSyncContent">
    <p style="color:#666;font-size:13px;">No negatives-sync.json — run Phase 8 perf_synth.</p>
  </div>
</section>

<section id="positives-sync">
  <h2>Positives Sync <span class="cluster-meta" id="posSyncMeta"></span></h2>
  <div class="usage">
    <p style="margin:0 0 8px"><strong>What this is for:</strong> cross-references our ranked positives against the live keyword list in your Google Ads account, so you don't waste Editor imports on keywords that already exist.</p>
    <p style="margin:0 0 4px"><strong>Bucket glossary:</strong></p>
    <ul style="margin:0 0 8px;padding-left:20px">
      <li><strong>already active</strong> = our keyword is already ENABLED in your campaign (exact match or normalised close variant). <em>Action: none — covered.</em></li>
      <li><strong>paused in account</strong> = the keyword exists in the account but is PAUSED. <em>Action: decide whether to re-enable, or add a fresh variant if performance was the reason it was paused.</em></li>
      <li><strong>covered by broad</strong> = an active broad / phrase keyword in the account would already match this query. <em>Action: none — broad coverage exists; only narrow into exact if you want tighter ad copy for a SKAG.</em></li>
      <li><strong>new to add</strong> = our keyword is genuinely net-new — not in the account in any form. <em>Action: paste from <code>positives.csv</code> into the Editor.</em></li>
    </ul>
    <p style="margin:0;font-size:12px;color:#555">Bucket detection runs a normalised string match first, then a Claude re-tag pass (Step 34a) catches token reorders, semantic synonyms (e.g. <em>physician</em> = <em>doctor</em>), and match-type drift. The <code>retag_reason</code> field on individual rows in <code>positives-sync.json</code> shows which rule applied.</p>
  </div>
  <div id="posSyncContent">
    <p style="color:#666;font-size:13px;">No positives-sync.json — run Phase 14 perf_synth.</p>
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

<section id="ad-group-mapping" style="display:none">
  <h2>Ad Group Mapping <span class="cluster-meta" id="agmMeta"></span></h2>
  <div class="usage"><strong>How to use:</strong> shows which of your existing Google Ads ad groups each ranked keyword maps to (Phase 8 perf data + Jaccard token overlap × intent match). <strong>High</strong> (≥0.7) = paste into existing ad group. <strong>Medium</strong> (0.4–0.7) = review before pasting. <strong>Low</strong> (&lt;0.4) = create new ad group from cluster slug.</div>
  <div id="agmContent"></div>
</section>

<section>
  <h2>Negative Keywords</h2>
  <div class="usage">
    <p style="margin:0 0 8px"><strong>What this is for:</strong> negative keywords block irrelevant searches from triggering your ads. Untreated noise (recruitment queries, DIY tutorials, wrong-audience searches, far-away geos) eats budget without ever converting. Adding these up front prevents the bleed.</p>
    <p style="margin:0 0 4px"><strong>Tier glossary</strong> — read this before scrolling the list:</p>
    <ul style="margin:0 0 8px;padding-left:20px">
      <li><span class="tier-Strong">Strong</span> = zero plausible buyer intent for this campaign. Recruitment (<code>jobs</code>, <code>careers</code>), DIY (<code>how to</code>, <code>home remedies</code>), wrong audience (pediatric for an adult clinic; lawyers when you're a doctor), wrong geo (other states / far-away cities), wrong reimbursement model (<code>free clinic</code>, <code>low income</code>). <strong>Action: add to the campaign on Day 1, no review needed.</strong></li>
      <li><span class="tier-Considered">Considered</span> = probably off-target, but depends on positioning. Direct competitor brand names (you may bid on them as a counter-attack), price-comparison terms (<code>cheap</code>, <code>discount</code>), premium qualifiers if you're a value brand. <strong>Action: read each row's justification against your brand positioning, then add or skip.</strong></li>
      <li><span class="tier-Investigate">Investigate</span> = edge cases that <em>might</em> be relevant. Related-but-different insurance regimes, generic out-of-region but possibly-serviceable areas. <strong>Action: skip on launch. Watch search-term reports for 2-4 weeks; if these queries actually appear and don't convert, promote to Strong then.</strong></li>
    </ul>
    <p style="margin:0;font-size:12px;color:#555">Keywords are also grouped by <strong>category</strong> within each tier (jobs-careers, free-DIY-tutorial, competitor-brand, wrong-geo, wrong-audience, used-refurb-wholesale) so you can scan or import in batches. Use the filter input above to narrow by keyword text or justification; use the tier dropdown to focus on one tier at a time.</p>
  </div>
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
  const title = document.getElementById("perfTitle");
  const meta = document.getElementById("perfMeta");
  const content = document.getElementById("perfContent");
  if (!perf || !perf.synthesized_at) return;
  const t = perf.totals || {{}};
  if (title) {{
    const isFiltered = (REPORT.campaign_focus || []).length > 0;
    title.textContent = isFiltered ? "Campaign Performance" : "Account Performance";
  }}
  meta.textContent = `last ${{perf.horizon_days||30}} days · $${{(t.spend_usd||0).toLocaleString()}} spend · ${{t.conversions||0}} conv`;
  const tbl = (rows, headers, fmt) => {{
    if (!rows.length) return "<p style='color:#666;font-size:13px'>None.</p>";
    return `<table style="margin-bottom:12px"><thead><tr>${{headers.map(h => `<th>${{h}}</th>`).join("")}}</tr></thead><tbody>${{rows.map(r => `<tr>${{fmt(r).map(c => `<td>${{c}}</td>`).join("")}}</tr>`).join("")}}</tbody></table>`;
  }};
  let html = `<div style="background:#ecfdf5;border-left:4px solid #10b981;padding:10px 14px;margin-bottom:12px;border-radius:4px;font-size:13px">
    <strong>Totals:</strong> spend $${{(t.spend_usd||0).toLocaleString()}} · clicks ${{(t.clicks||0).toLocaleString()}} · conv ${{t.conversions||0}} · blended CPA ${{t.blended_cpa_usd ? '$'+t.blended_cpa_usd : '—'}} · ROAS ${{t.blended_roas ? t.blended_roas+'x' : '—'}}
  </div>`;

  const subUsage = (txt) => `<p style="margin:8px 0 10px;font-size:12px;color:#555;line-height:1.5">${{txt}}</p>`;

  const conv = perf.converted_search_terms || [];
  html += `<details open><summary>Converted search terms <span class="cluster-meta">${{conv.length}}</span></summary>`
    + subUsage("Real user queries that triggered a conversion in the last 30 days — not your bid keywords, what was actually typed. These prove buyer intent. <strong>Action:</strong> bid harder on the matching keywords, or promote them into a dedicated single-keyword ad group with tighter ad copy.")
    + tbl(conv.slice(0,15),
    ["Search Term","Conv","Clicks","Cost","Campaign"],
    r => [htmlEscape(r.search_term), r.conversions.toFixed(1), r.clicks, `$${{r.cost_usd.toFixed(2)}}`, htmlEscape(r.campaign_name)]
  ) + `</details>`;

  const lossy = perf.lossy_search_terms || [];
  html += `<details><summary>Lossy search terms — negative candidates <span class="cluster-meta">${{lossy.length}}</span></summary>`
    + subUsage("Queries that got clicks but never converted — they're eating budget. <strong>Action:</strong> add as Strong negatives unless the gap is attribution lag (long sales cycle) or the query is genuinely relevant and just needs better landing-page match.")
    + tbl(lossy.slice(0,15),
    ["Search Term","Clicks","Cost","Campaign"],
    r => [htmlEscape(r.search_term), r.clicks, `$${{r.cost_usd.toFixed(2)}}`, htmlEscape(r.campaign_name)]
  ) + `</details>`;

  const roas = perf.top_by_roas || [];
  html += `<details><summary>Top campaigns by ROAS <span class="cluster-meta">${{roas.length}}</span></summary>`
    + subUsage("Revenue per ad dollar (1.0x = breakeven, 3.0x = $3 returned per $1 spent). <strong>Action:</strong> scale top performers (add budget); pause anything well below your target ROAS. With a <code>Campaign focus:</code> set in the brief, this narrows to the targeted campaign(s) only.")
    + tbl(roas.slice(0,10),
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

function renderPositivesSync() {{
  const sync = REPORT.positives_sync || {{}};
  const meta = document.getElementById("posSyncMeta");
  const content = document.getElementById("posSyncContent");
  if (!sync || !sync.stats) return;
  const s = sync.stats || {{}};
  meta.textContent = `${{s.our_total||0}} ours · ${{s.already_active||0}} active · ${{s.paused_in_account||0}} paused · ${{s.covered_by_broad||0}} broad-cover · ${{s.new_to_add||0}} new`;
  let html = `<div style="background:#ecfdf5;border-left:4px solid #10b981;padding:10px 14px;margin-bottom:12px;border-radius:4px;font-size:13px">
    <strong>Stats:</strong> our list = ${{s.our_total||0}} · already active = ${{s.already_active||0}} · paused = ${{s.paused_in_account||0}} · covered by broad = ${{s.covered_by_broad||0}} · new to add = <strong>${{s.new_to_add||0}}</strong>
  </div>`;
  const newRows = sync.new_to_add || [];
  html += `<details open><summary>New positives to add <span class="cluster-meta">${{newRows.length}}</span></summary>`;
  if (!newRows.length) html += "<p style='color:#666;font-size:13px'>None — your ranked list is fully covered by the active account.</p>";
  else html += "<ul>" + newRows.map(r => `<li><code>${{htmlEscape(r.keyword||"")}}</code> <span class="cluster-meta">${{htmlEscape(r.intent||"")}}</span>${{r.justification?" — "+htmlEscape(r.justification):""}}</li>`).join("") + "</ul>";
  html += "</details>";
  // Count-only audit buckets — collapsible with full per-row data inline
  const buckets = [
    ["Already active", "already_active"],
    ["Paused in account", "paused_in_account"],
    ["Covered by broad-match", "covered_by_broad"],
  ];
  for (const [label, key] of buckets) {{
    const items = sync[key] || [];
    html += `<details><summary>${{label}} <span class="cluster-meta">${{items.length}}</span></summary>`;
    if (!items.length) html += "<p style='color:#666;font-size:13px'>None.</p>";
    else html += "<ul>" + items.map(r => `<li><code>${{htmlEscape(r.keyword||"")}}</code> <span class="cluster-meta">${{htmlEscape(r.intent||"")}} · ${{htmlEscape(r.match_type||"")}}</span></li>`).join("") + "</ul>";
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
  let html = "";

  // FRCS-06 over-cap warning — sits ABOVE Campaign Totals so the budget
  // mismatch is the first thing the operator sees in this section.
  const clamp = forecast.budget_clamp;
  if (clamp && clamp.over_cap_ratio != null) {{
    if (clamp.over_cap_ratio > 1.0) {{
      html += `<div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;margin-bottom:12px;border-radius:4px;font-size:14px">
        ⚠ <strong>Forecast is ${{clamp.over_cap_ratio}}x your $${{clamp.daily_cap_usd.toFixed(2)}}/day cap.</strong>
        The full ${{totals.keyword_count||0}}-keyword pool can't be bid at this budget.
        See <strong>What Fits Your Cap</strong> below for the priority-sorted launch list
        (${{clamp.fitting_count}} keywords, $${{clamp.cumulative_spend_mid_usd.toFixed(2)}}/day mid).
        The remaining ${{clamp.dropped_count}} keywords stay in research output for future campaign expansion.
      </div>`;
    }} else {{
      html += `<div style="background:#ecfdf5;border-left:4px solid #10b981;padding:10px 14px;margin-bottom:12px;border-radius:4px;font-size:13px">
        ✓ <strong>Forecast fits your $${{clamp.daily_cap_usd.toFixed(2)}}/day cap</strong>
        (${{clamp.over_cap_ratio}}x ratio). All ${{clamp.fitting_count}} bidable keywords land within budget.
      </div>`;
    }}
  }}

  html += `<div style="background:#ecfdf5;border-left:4px solid #10b981;padding:10px 14px;margin-bottom:12px;border-radius:4px;font-size:13px"><strong>Campaign Totals:</strong> Daily ${{fmtClicks(totals.daily_clicks_low||0)}}/${{fmtClicks(totals.daily_clicks_mid||0)}}/${{fmtClicks(totals.daily_clicks_high||0)}} clicks · $${{(totals.daily_spend_low_usd||0).toFixed(2)}}/$${{(totals.daily_spend_mid_usd||0).toFixed(2)}}/$${{(totals.daily_spend_high_usd||0).toFixed(2)}} daily spend · $${{(totals.monthly_spend_mid_usd||0).toFixed(2)}} monthly (mid)</div>`;
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

  // FRCS-06: "What Fits Your Cap" subsection — only renders when brief
  // carried `**Budget:**` so the clamp was computed. Operator sees the
  // priority-sorted launch list inline; full dropped list lives in
  // forecast.json → budget_clamp.keywords_dropped[] for audit.
  if (clamp && clamp.keywords_fitting_cap && clamp.keywords_fitting_cap.length) {{
    html += `<h3 style="margin-top:20px">What Fits Your Cap</h3>`;
    html += `<p style="font-size:13px;color:#555;margin:0 0 8px">
      Priority-sorted launch list at the <strong>$${{clamp.daily_cap_usd.toFixed(2)}}/day</strong> cap.
      Sort: transactional → commercial → navigational → informational; within each, signal_count desc then score desc.
      Cumulative spend tops out at <strong>$${{clamp.cumulative_spend_mid_usd.toFixed(2)}}/day (${{clamp.fitting_count}} keywords)</strong>.
      The remaining ${{clamp.dropped_count}} ranked keywords are research output only — drop from the Editor import or import paused, revisit when budget grows.
    </p>`;
    html += `<table><thead><tr><th>Keyword</th><th>Intent</th><th>Cluster</th><th data-sort="number">Score</th><th data-sort="number">Daily Spend Mid</th><th data-sort="number">Cumulative</th></tr></thead><tbody>`;
    for (const r of clamp.keywords_fitting_cap) {{
      html += `<tr>
        <td><code>${{htmlEscape(r.keyword||"")}}</code></td>
        <td><span class="intent-tag intent-${{r.intent||""}}">${{r.intent||""}}</span></td>
        <td>${{htmlEscape(r.cluster||"")}}</td>
        <td>${{r.score||0}}</td>
        <td>$${{(r.daily_spend_mid_usd||0).toFixed(2)}}</td>
        <td>$${{(r.cumulative_spend_usd||0).toFixed(2)}}</td>
      </tr>`;
    }}
    html += `</tbody></table>`;
    if (clamp.keywords_dropped && clamp.keywords_dropped.length) {{
      const preview = clamp.keywords_dropped.slice(0, 10).map(k => `<code>${{htmlEscape(k)}}</code>`).join(", ");
      const more = clamp.keywords_dropped.length - 10;
      html += `<details style="margin-top:10px"><summary><strong>Dropped from launch list</strong> <span class="cluster-meta">${{clamp.keywords_dropped.length}} keywords</span></summary>
        <p style="font-size:13px;color:#555;margin-top:8px">${{preview}}${{more > 0 ? ", and "+more+" more" : ""}}.</p>
        <p style="font-size:12px;color:#888">Full list: <code>forecast.json → budget_clamp.keywords_dropped[]</code></p>
      </details>`;
    }}
  }}

  // FRCS-07: Deferred Brand Conquest subsection — only renders when the
  // budget-clamp identified competitor brand-navigational keywords that were
  // deferred from the launch list at this budget tier. Operator sees them as
  // Consider-negative candidates instead of accidentally bidding competitor
  // brands without Smart Bidding data.
  if (clamp && clamp.brand_conquest_active && clamp.keywords_deferred_brand_conquest && clamp.keywords_deferred_brand_conquest.length) {{
    const deferred = clamp.keywords_deferred_brand_conquest;
    const threshold = clamp.brand_conquest_threshold_usd || 200;
    const deferredSpend = clamp.deferred_brand_conquest_spend_usd || 0;
    const pctOfBudget = clamp.daily_cap_usd > 0 ? Math.round(deferredSpend / clamp.daily_cap_usd * 100) : 0;
    html += `<h3 style="margin-top:20px">Deferred Brand Conquest <span style="font-weight:normal;color:#666;font-size:14px">(Consider as Negatives)</span></h3>`;
    html += `<div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:12px 16px;margin-bottom:12px;border-radius:4px;font-size:13px;line-height:1.5">
      At your <strong>$${{clamp.daily_cap_usd.toFixed(2)}}/day</strong> cap (below the <strong>$${{threshold.toFixed(2)}}/day</strong> brand-conquest threshold), the skill deferred <strong>${{deferred.length}} competitor brand-navigational keywords</strong> from the launch list — they would have consumed <strong>$${{deferredSpend.toFixed(2)}}/day (${{pctOfBudget}}% of your budget)</strong> on conquest attempts at 2-3x normal CPC.
      <br><br>
      <strong>Recommended action:</strong> add these as Considered-tier negatives in your campaign instead. Bidding competitor brands at this budget burns money against advertisers with 8+ Quality Score on their own brand, with no Smart Bidding data yet to know if conquest CPL is even visible.
      <br><br>
      <strong>To re-enable</strong> (e.g., when budget grows past $${{threshold.toFixed(2)}}/day): add <code>Brand conquest: yes</code> to the brief and re-run forecast.
    </div>`;
    html += `<table><thead><tr><th>Keyword (→ Add as Negative)</th><th>From Cluster</th><th data-sort="number">Would Have Spent</th><th data-sort="number">Score</th></tr></thead><tbody>`;
    for (const r of deferred) {{
      html += `<tr>
        <td><code>${{htmlEscape(r.keyword||"")}}</code></td>
        <td>${{htmlEscape(r.cluster||"")}}</td>
        <td>$${{(r.daily_spend_mid_usd||0).toFixed(2)}}</td>
        <td>${{r.score||0}}</td>
      </tr>`;
    }}
    html += `</tbody></table>`;
  }}

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

function renderAdGroupMapping() {{
  var agm = REPORT.ad_group_mapping;
  if (!agm) return;
  var matches = agm.matches || [];
  var existingAgs = agm.existing_ad_groups || [];
  // Show section when EITHER matches OR a raw ad-group list is present.
  if (!matches.length && !existingAgs.length) return;
  var section = document.getElementById("ad-group-mapping");
  var meta = document.getElementById("agmMeta");
  var content = document.getElementById("agmContent");
  if (!section || !content) return;
  section.style.display = "block";
  var high = matches.filter(function(m){{ return m.confidence === "high"; }}).length;
  var medium = matches.filter(function(m){{ return m.confidence === "medium"; }}).length;
  var low = matches.filter(function(m){{ return m.confidence === "low"; }}).length;
  var total = matches.length;
  var coverage = (agm.mapping_coverage_pct || 0).toFixed(1);
  meta.textContent = "coverage " + coverage + "% · " + total + " ranked · high " + high + " · medium " + medium + " · low " + low;
  var skipped = agm.skipped_reason;
  if (skipped) {{
    content.innerHTML = "<p style='color:#666;font-size:13px'><em>Skipped: " + htmlEscape(skipped) + "</em></p>";
    return;
  }}
  var mapped = matches.filter(function(m){{ return m.confidence === "high" || m.confidence === "medium"; }});
  mapped.sort(function(a, b){{ return (b.score || 0) - (a.score || 0); }});
  var top15 = mapped.slice(0, 15);
  var html = "";
  if (top15.length) {{
    html += '<h3 style="margin-top:8px">Matched Keywords (top 15)</h3>';
    html += '<table><thead><tr><th>Keyword</th><th>Existing Ad Group</th><th>Confidence</th><th>Score</th></tr></thead><tbody>';
    html += top15.map(function(m){{
      var conf = m.confidence || "";
      var color = conf === "high" ? "#15803d" : (conf === "medium" ? "#a16207" : "#666");
      return '<tr><td>' + htmlEscape(m.keyword || "") + '</td>'
        + '<td>' + htmlEscape(m.existing_ad_group || "") + '</td>'
        + '<td style="color:' + color + ';font-weight:600">' + htmlEscape(conf) + '</td>'
        + '<td>' + (m.score || 0).toFixed(2) + '</td></tr>';
    }}).join("");
    html += '</tbody></table>';
    if (mapped.length > 15) {{
      html += '<p style="color:#666;font-size:13px">…and ' + (mapped.length - 15) + ' more matched keyword(s).</p>';
    }}

    // Grouped view — same-ad-group keywords contiguous (team's "sort by
    // structure" request). Each existing ad group as collapsible <details>.
    var byAg = {{}};
    mapped.forEach(function(m){{
      var ag = m.existing_ad_group || "(unknown)";
      if (!byAg[ag]) byAg[ag] = [];
      byAg[ag].push(m);
    }});
    var agNames = Object.keys(byAg).sort(function(a, b){{
      return a.toLowerCase().localeCompare(b.toLowerCase());
    }});
    html += '<h3 style="margin-top:16px">Keywords by Existing Ad Group</h3>';
    html += '<p style="color:#666;font-size:13px"><em>positives.csv is sorted to match — paste each block into the corresponding existing ad group in Google Ads Editor.</em></p>';
    html += agNames.map(function(ag){{
      var kws = byAg[ag].slice().sort(function(a, b){{ return (b.score || 0) - (a.score || 0); }});
      var items = kws.map(function(m){{
        var conf = m.confidence || "";
        var color = conf === "high" ? "#15803d" : "#a16207";
        return '<li>' + htmlEscape(m.keyword || "")
          + ' <span class="cluster-meta" style="color:' + color + '">' + htmlEscape(conf) + ' · ' + (m.score || 0).toFixed(2) + '</span></li>';
      }}).join("");
      return '<details><summary><strong>' + htmlEscape(ag) + '</strong> <span class="cluster-meta">' + kws.length + ' keyword' + (kws.length !== 1 ? 's' : '') + '</span></summary><ul>' + items + '</ul></details>';
    }}).join("");
  }} else if (matches.length) {{
    html += '<p style="color:#666;font-size:13px"><em>No high or medium-confidence matches in this run. All ranked keywords fall back to new cluster ad groups (see Ad Group Clusters section above).</em></p>';
  }}
  if (low) {{
    html += '<p style="color:#666;font-size:13px"><em>' + low + ' low-confidence keyword(s) routed to new cluster ad groups (cluster slug used as ad group name in positives.csv).</em></p>';
  }}
  // Existing Ad Groups in Account — always render when perf data has them
  // so operator can see their account structure regardless of match quality.
  if (existingAgs.length) {{
    var seen = {{}};
    var dedup = [];
    existingAgs.forEach(function(ag){{
      var name = (ag.name || "").trim();
      var camp = (ag.campaign_name || "").trim();
      var key = name.toLowerCase() + "|" + camp.toLowerCase();
      if (!name || seen[key]) return;
      seen[key] = true;
      dedup.push(ag);
    }});
    dedup.sort(function(a, b){{
      var ca = (a.clicks || 0), cb = (b.clicks || 0);
      if (cb !== ca) return cb - ca;
      return (a.name || "").toLowerCase().localeCompare((b.name || "").toLowerCase());
    }});
    html += '<h3 style="margin-top:24px">Existing Ad Groups in Account (' + dedup.length + ')</h3>';
    html += '<p style="color:#666;font-size:13px"><em>Your full account structure pulled from Phase 8 perf data. Listed here regardless of match quality so you can manually pick a destination ad group when the algorithm cannot find a confident bucket.</em></p>';
    html += '<table><thead><tr><th>Ad Group</th><th>Campaign</th><th>Status</th><th>Clicks</th><th>Impr</th><th>Cost</th><th>Conv</th></tr></thead><tbody>';
    html += dedup.map(function(ag){{
      var clicks = ag.clicks || 0;
      var impr = ag.impressions || 0;
      var cost = ag.cost_usd || 0;
      var conv = ag.conversions || 0;
      var statusColor = ag.status === "ENABLED" ? "#15803d" : "#a16207";
      return '<tr>'
        + '<td>' + htmlEscape(ag.name || "") + '</td>'
        + '<td style="color:#666">' + htmlEscape(ag.campaign_name || "") + '</td>'
        + '<td style="color:' + statusColor + ';font-weight:600">' + htmlEscape(ag.status || "") + '</td>'
        + '<td>' + (clicks ? clicks.toLocaleString() : '—') + '</td>'
        + '<td>' + (impr ? impr.toLocaleString() : '—') + '</td>'
        + '<td>' + (cost ? '$' + Math.round(cost).toLocaleString() : '—') + '</td>'
        + '<td>' + (conv ? Math.round(conv).toLocaleString() : '—') + '</td>'
        + '</tr>';
    }}).join('');
    html += '</tbody></table>';
  }}
  // Update meta line if there were no matches at all (matches.length === 0)
  // — meta was set earlier only when matches existed.
  if (!matches.length) {{
    meta.textContent = dedupedAgsMeta(existingAgs);
  }}
  content.innerHTML = html;
}}

function dedupedAgsMeta(agsList) {{
  var seen = {{}};
  var n = 0;
  agsList.forEach(function(ag){{
    var name = (ag.name || "").trim();
    var camp = (ag.campaign_name || "").trim();
    var key = name.toLowerCase() + "|" + camp.toLowerCase();
    if (name && !seen[key]) {{ seen[key] = true; n++; }}
  }});
  return n + " existing ad group" + (n !== 1 ? "s" : "") + " in account";
}}

renderKeywords(); renderClusters(); renderCompetitors();
renderCompliance(); renderForecast();
renderAccountPerf(); renderNegativesSync(); renderPositivesSync(); renderNegatives();
renderAdGroupMapping();
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
    account_perf: dict | None = None,
    negatives_sync: dict | None = None,
    positives_sync: dict | None = None,
    forecast: dict | None = None,
    compliance: dict | None = None,
    next_steps: list[dict] | None = None,
    exports: list[str] | None = None,
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

    # GEO-05: geographic_focus surfaces brief's location + parsed geo_focus
    # tokens. Always present (empty focus list when brief has no Geo line).
    geo_focus_raw = (brief_fields.get("geo_focus") or "").strip()
    geo_focus_list = [
        s.strip() for s in geo_focus_raw.split(",") if s.strip()
    ] if geo_focus_raw else []
    geographic_focus_obj = {
        "location": brief_fields.get("location", ""),
        "focus": geo_focus_list,
    }

    # CAMP-05: campaign_focus surfaces brief's parsed campaign focus list.
    # Always present as a top-level key (empty list when brief has no
    # Campaign focus line). Uses the shared pipe-split heuristic — spaced
    # pipes (' | ') preserved as ONE name; bare '|' splits to list.
    campaign_focus_list = _split_campaign_focus(
        (brief_fields.get("campaign_focus") or "").strip()
    )

    # ADGM-06: ad_group_mapping_summary surfaces only when the sidecar exists.
    # Schema mirrors the operator-facing telemetry: coverage_pct + per-tier
    # counts. Absent key when no mapping (Phase-8-absent or pre-Phase-11 runs).
    ad_group_mapping = _load_ad_group_mapping_for_render(run_dir)
    ad_group_mapping_summary: dict | None = None
    if ad_group_mapping:
        counts = {"high": 0, "medium": 0, "low": 0}
        for m in ad_group_mapping.get("matches", []) or []:
            tier = m.get("confidence", "low")
            counts[tier] = counts.get(tier, 0) + 1
        ad_group_mapping_summary = {
            "coverage_pct": ad_group_mapping.get("mapping_coverage_pct", 0.0),
            "matched_high": counts.get("high", 0),
            "matched_medium": counts.get("medium", 0),
            "unmapped": counts.get("low", 0),
        }

    report = {
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
        "account_perf": account_perf or {},
        "negatives_sync": negatives_sync or {},
        "positives_sync": positives_sync or {},
        "forecast": forecast or {},
        "compliance": compliance_list,
        "geographic_focus": geographic_focus_obj,
        "campaign_focus": campaign_focus_list,
        "next_steps": next_steps if next_steps is not None else (
            render_next_steps_section(
                brief_fields, forecast, compliance, clusters_data,
                ad_group_mapping=ad_group_mapping,
            )[1]
        ),
        "exports": exports if exports is not None else list_export_paths(run_dir),
    }
    if ad_group_mapping_summary is not None:
        report["ad_group_mapping_summary"] = ad_group_mapping_summary
    if ad_group_mapping is not None:
        report["ad_group_mapping"] = ad_group_mapping
    # Surface the operator's full existing-ad-group list so the HTML JS
    # renderAdGroupMapping() can always show their account structure even
    # when no kw matched with high/medium confidence (low-Jaccard accounts).
    existing_ad_groups = _load_existing_ad_groups(run_dir)
    if existing_ad_groups:
        if ad_group_mapping is None:
            report["ad_group_mapping"] = {"matches": [], "existing_ad_groups": existing_ad_groups}
        else:
            report["ad_group_mapping"] = {
                **ad_group_mapping,
                "existing_ad_groups": existing_ad_groups,
            }
    return report


# ---------------------------------------------------------------------------
# PDF rendering — calls a headless system browser (Edge/Chrome/Chromium)
# ---------------------------------------------------------------------------

_BROWSER_CANDIDATES_BY_PLATFORM: dict[str, list[str]] = {
    "win32": [
        "msedge", "chrome", "chromium",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "darwin": [
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "linux": [
        "microsoft-edge", "google-chrome", "chromium", "chromium-browser",
    ],
}


def _find_headless_browser() -> Path | None:
    """Return a path to a usable headless-capable browser, or None.

    Tries PATH lookups first (msedge/chrome/chromium), then well-known
    install paths on Windows/macOS. Returns None if nothing usable found.
    """
    for cand in _BROWSER_CANDIDATES_BY_PLATFORM.get(sys.platform, []):
        if "/" in cand or "\\" in cand:
            p = Path(cand)
            if p.exists():
                return p
        else:
            found = shutil.which(cand)
            if found:
                return Path(found)
    return None


def _render_pdf_from_html(html_path: Path, pdf_path: Path) -> bool:
    """Render report.html → report.pdf via headless system browser.

    Best-effort. Returns False (and logs to stderr) on any failure
    (browser missing, timeout, non-zero exit, empty output). The rest
    of the pipeline completes regardless — PDF is an optional artifact.
    """
    browser = _find_headless_browser()
    if browser is None:
        print(
            "render_report: no headless browser found (msedge/chrome/chromium); skipping PDF",
            file=sys.stderr,
        )
        return False
    file_url = html_path.resolve().as_uri()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path.resolve()}",
        "--virtual-time-budget=5000",
        file_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(
            f"render_report: PDF generation failed ({type(exc).__name__}); skipping PDF",
            file=sys.stderr,
        )
        return False
    if result.returncode != 0:
        print(
            f"render_report: browser exited {result.returncode}; skipping PDF",
            file=sys.stderr,
        )
        return False
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        print(
            "render_report: browser produced empty/missing PDF; skipping",
            file=sys.stderr,
        )
        return False
    return True


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

    # Phase 14 POS-03 / POS-05 — Positives Sync sidecar (graceful absent path)
    positives_sync: dict | None = None
    pos_sync_path = run_dir / "positives-sync.json"
    if pos_sync_path.exists():
        try:
            positives_sync = json.loads(pos_sync_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            positives_sync = None

    # Load optional Phase 9 sidecars (forecast.json + compliance-flags.json).
    # Missing files degrade gracefully — sections are simply omitted from the
    # report. Mirrors the account-perf / negatives-sync pattern.
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

    # Phase 10 STEP-01..04 + CMPL-05 + Phase 11 ADGM-06 — compute Next Steps
    # once, share between report.md (via render_full_report internally) and
    # report.json/HTML. Mapping is read from the run_dir sidecar; absence
    # falls back to the standard step-3 ("Create ad groups: ...").
    brief_fields_for_steps = _parse_brief_fields(brief_text)
    ad_group_mapping_for_steps = _load_ad_group_mapping_for_render(run_dir)
    _, next_steps_list = render_next_steps_section(
        brief_fields_for_steps, forecast, compliance, clusters_data,
        ad_group_mapping=ad_group_mapping_for_steps,
    )
    # Phase 10 EXPT-05 — Export Files list (relative POSIX paths).
    exports_list = list_export_paths(run_dir)

    # Render
    report_md = render_full_report(
        ranked, clusters_data, competitor_intel, negatives,
        brief_text, run_dir, top_n=args.top_n,
        account_perf=account_perf,
        negatives_sync=negatives_sync,
        positives_sync=positives_sync,
        forecast=forecast,
        compliance=compliance,
    )
    report_json = build_report_json(
        ranked, clusters_data, competitor_intel, negatives,
        brief_text, run_dir,
        account_perf=account_perf,
        negatives_sync=negatives_sync,
        positives_sync=positives_sync,
        forecast=forecast,
        compliance=compliance,
        next_steps=next_steps_list,
        exports=exports_list,
    )

    report_html = render_html_report(report_json)

    # Write outputs (LF newlines, utf-8)
    (run_dir / "report.md").write_text(report_md, encoding="utf-8", newline="\n")
    (run_dir / "report.json").write_text(
        json.dumps(report_json, indent=2, ensure_ascii=False),
        encoding="utf-8", newline="\n",
    )
    (run_dir / "report.html").write_text(report_html, encoding="utf-8", newline="\n")

    pdf_path = run_dir / "report.pdf"
    pdf_ok = _render_pdf_from_html(run_dir / "report.html", pdf_path)

    print(json.dumps({
        "report_md": str(run_dir / "report.md"),
        "report_json": str(run_dir / "report.json"),
        "report_html": str(run_dir / "report.html"),
        "report_pdf": str(pdf_path) if pdf_ok else None,
        "keywords_in_report": len(ranked),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
