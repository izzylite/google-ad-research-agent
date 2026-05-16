# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""forecast_budget.py — Per-cluster + campaign-level click + spend forecast.

Implements:
    FRCS-01  Emits {run_dir}/forecast.json with per-cluster + campaign-level
             click and spend bands (low / mid / high).
    FRCS-02  Click estimates use intent-class CTR anchors
             (transactional 6%, commercial 4%, informational 2%, navigational 8%).
             All tuning knobs live in ONE module-level dict (INTENT_CTRS) at the
             top of this file. Frozenset assertion guards the 4-class rubric.
    FRCS-03  Spend = clicks × (suggested_max_cpc × AVG_CPC_RATIO=0.65).
             Bands at × 0.5 / × 1.0 / × 1.5 (BAND_MULTIPLIERS).
    FRCS-05  forecast.json carries a methodology block that mirrors the
             script constants verbatim — single source of truth for the
             report disclaimer.

UNIT CONTRACT (Pitfall 8):
    suggested_max_cpc_micros is stored in micros (USD × 1,000,000). All
    arithmetic stays in micros UNTIL the display boundary; convert ONCE
    via `usd = micros / 1_000_000` when emitting the *_usd fields.

This module exposes:
    INTENT_CTRS               (FRCS-02 tuning knobs)
    AVG_CPC_RATIO             (FRCS-03 anchor)
    BAND_MULTIPLIERS          (FRCS-03 band spread)
    compute_cluster_forecast  (per-cluster click + spend math)
    build_forecast            (top-level structure: metadata + methodology +
                               clusters + campaign_totals)
    main_with_args            (CLI entrypoint — argv → exit code)

Reads:
    {run_dir}/ranked-enriched.json   (post-bid_suggest; carries
                                      suggested_max_cpc_micros per row)
    {run_dir}/clusters.json          (validate_clusters.py output)

Writes:
    {run_dir}/forecast.json          (FRCS-01 schema — see <output_schema>
                                      in 09-02-PLAN.md)

CLI:
    uv run forecast_budget.py --run-dir <abs>

Stdout (one JSON line):
    {"clusters_forecast": N,
     "keywords_in_forecast": N,
     "daily_spend_mid_usd": X.XX,
     "unjoined_keywords": N}

Exit codes:
    0  ok
    2  retryable (transient disk error)
    3  fatal (missing input, malformed JSON)
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

# Make sibling lib/ importable (mirror volume_enrich.py / bid_suggest.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.log import configure_logger  # noqa: E402


# --- Tuning knobs (FRCS-02, FRCS-03) ---
# Edit values here; nothing else in this file uses literal CTRs / ratios.
INTENT_CTRS: dict[str, float] = {
    "transactional": 0.06,
    "commercial":    0.04,
    "informational": 0.02,
    "navigational":  0.08,
}

AVG_CPC_RATIO: float = 0.65          # avg_cpc = suggested_max_cpc × this

BAND_MULTIPLIERS: dict[str, float] = {"low": 0.5, "mid": 1.0, "high": 1.5}

# Sanity check: keys must match the 4-class rubric exactly.
_REQUIRED_INTENTS = frozenset(
    {"transactional", "commercial", "informational", "navigational"}
)
assert frozenset(INTENT_CTRS) == _REQUIRED_INTENTS, (
    f"INTENT_CTRS keys must match 4-class rubric: {_REQUIRED_INTENTS}"
)

# Single source of truth for the FRCS-05 disclaimer text (methodology block).
_METHODOLOGY_NOTES: str = (
    "Directional estimates. Not Google's official forecast (see Keyword "
    "Planner). Assumes one impression per searched keyword and intent-class "
    "CTR anchors derived from industry medians."
)

log = configure_logger(__name__)


# ---------------------------------------------------------------------------
# Join-index helpers (Pitfall 6 — lower+strip casing)
# ---------------------------------------------------------------------------

def _build_ranked_index(ranked: list[dict]) -> dict[str, dict]:
    """Map keyword.lower().strip() → ranked row.

    Mirrors render_report.py's `_build_cluster_index` casing rules so the
    join between clusters.json and ranked-enriched.json never silently
    misses rows due to case/whitespace drift.
    """
    index: dict[str, dict] = {}
    for row in ranked or []:
        key = (row.get("keyword") or "").lower().strip()
        if key:
            index[key] = row
    return index


# ---------------------------------------------------------------------------
# Per-cluster compute (FRCS-01, FRCS-02, FRCS-03)
# ---------------------------------------------------------------------------

def compute_cluster_forecast(
    cluster: dict,
    ranked_index: dict[str, dict],
) -> dict:
    """Compute per-cluster forecast.

    Returns dict with keys: name, intent, keyword_count, keywords_with_volume,
    total_monthly_volume, daily_clicks_low/mid/high, daily_spend_low/mid/high_usd,
    monthly_spend_mid_usd, unjoined_keywords.

    Skip keywords with volume is None OR suggested_max_cpc_micros is None.
    All math stays in micros until the final USD conversion (Pitfall 8).
    """
    cluster_keywords = cluster.get("keywords", []) or []
    keyword_count = len(cluster_keywords)
    keywords_with_volume = 0
    total_monthly_volume = 0
    total_daily_clicks_mid = 0.0
    total_daily_spend_micros_mid = 0.0
    unjoined = 0

    for kw_entry in cluster_keywords:
        kw_str = (kw_entry.get("keyword") or "").lower().strip()
        if not kw_str:
            unjoined += 1
            continue
        row = ranked_index.get(kw_str)
        if row is None:
            unjoined += 1
            continue
        volume = row.get("volume")
        sugg_cpc = row.get("suggested_max_cpc_micros")
        intent = row.get("intent", "") or ""
        if volume is None or sugg_cpc is None:
            # Skipped — not in keywords_with_volume, no contribution to totals.
            continue
        ctr = INTENT_CTRS.get(intent, 0.0)
        monthly_clicks_kw = float(volume) * ctr
        avg_cpc_micros = float(sugg_cpc) * AVG_CPC_RATIO
        daily_clicks_kw = monthly_clicks_kw / 30.0
        daily_spend_micros_kw = daily_clicks_kw * avg_cpc_micros

        keywords_with_volume += 1
        total_monthly_volume += int(volume)
        total_daily_clicks_mid += daily_clicks_kw
        total_daily_spend_micros_mid += daily_spend_micros_kw

    # Apply bands at the cluster aggregate (FRCS-03).
    daily_clicks_mid_f = total_daily_clicks_mid
    daily_clicks_low = int(round(daily_clicks_mid_f * BAND_MULTIPLIERS["low"]))
    daily_clicks_mid = int(round(daily_clicks_mid_f * BAND_MULTIPLIERS["mid"]))
    daily_clicks_high = int(round(daily_clicks_mid_f * BAND_MULTIPLIERS["high"]))

    # Convert spend ONCE at the display boundary (Pitfall 8).
    daily_spend_mid_usd = round(total_daily_spend_micros_mid / 1_000_000, 2)
    daily_spend_low_usd = round(
        daily_spend_mid_usd * BAND_MULTIPLIERS["low"], 2
    )
    daily_spend_high_usd = round(
        daily_spend_mid_usd * BAND_MULTIPLIERS["high"], 2
    )
    monthly_spend_mid_usd = round(daily_spend_mid_usd * 30, 2)

    return {
        "name": cluster.get("name"),
        "intent": cluster.get("intent"),
        "keyword_count": keyword_count,
        "keywords_with_volume": keywords_with_volume,
        "total_monthly_volume": total_monthly_volume,
        "daily_clicks_low": daily_clicks_low,
        # Keep the precise mid (float) — tests compare with pytest.approx so
        # we need the un-rounded value for daily_clicks_mid to satisfy
        # `daily_clicks_mid == 6.0 ± 1%` for a 3000 × 0.06 / 30 = 6.0 case.
        "daily_clicks_mid": daily_clicks_mid_f,
        "daily_clicks_high": daily_clicks_high,
        "daily_spend_low_usd": daily_spend_low_usd,
        "daily_spend_mid_usd": daily_spend_mid_usd,
        "daily_spend_high_usd": daily_spend_high_usd,
        "monthly_spend_mid_usd": monthly_spend_mid_usd,
        "unjoined_keywords": unjoined,
    }


# ---------------------------------------------------------------------------
# Budget clamp (FRCS-06 — read Budget: from brief; emit what-fits-cap subset)
# ---------------------------------------------------------------------------

# Priority order for fitting the cap: highest-intent first, then by score desc.
# Transactional keywords are the only ones with launch-day buyer-intent ROI;
# commercial sits below; navigational only fires on its own brand searches;
# informational rarely converts in the launch budget. The order matters when
# we're trimming a too-broad pool to a tight cap.
_INTENT_PRIORITY: dict[str, int] = {
    "transactional": 0,
    "commercial":    1,
    "navigational":  2,
    "informational": 3,
}


def _parse_daily_budget_usd(brief_path: Path) -> float | None:
    """Extract a daily-budget cap from `**Budget:**` in brief.md.

    Accepts common shorthand forms:
        "$82/day"            → 82.0
        "$82/day / $1,600/mo" → 82.0  (prefers /day when both present)
        "$1,600/mo"          → 53.33 (monthly / 30)
        "$82"                → 82.0  (no period — assume daily)

    Returns None when brief.md is missing, the line is absent, or no
    dollar amount can be parsed. Caller treats None as "no cap" — no
    clamp applied, full forecast surfaces unmodified.
    """
    if not brief_path.exists():
        return None
    try:
        text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(
        r"^\s*-?\s*\*\*Budget:\*\*\s*(.+)$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return None
    raw = m.group(1).strip()

    # Try "/day" first — it's the canonical daily cap.
    day_match = re.search(
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:/|\s)*day",
        raw, re.IGNORECASE,
    )
    if day_match:
        try:
            return float(day_match.group(1).replace(",", ""))
        except ValueError:
            return None

    # Fall back to "/mo" or "/month" — divide by 30.
    mo_match = re.search(
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:/|\s)*(?:mo|month)",
        raw, re.IGNORECASE,
    )
    if mo_match:
        try:
            return round(float(mo_match.group(1).replace(",", "")) / 30.0, 2)
        except ValueError:
            return None

    # No period — first dollar amount, assume daily.
    bare_match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", raw)
    if bare_match:
        try:
            return float(bare_match.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _per_keyword_daily_spend_usd(row: dict) -> float | None:
    """Compute per-keyword mid daily spend in USD, or None when unbidable.

    Mirrors the cluster-aggregate math but for a single ranked-enriched row.
    Returns None when volume or suggested_max_cpc_micros is absent — those
    rows can't be bid on at any budget.
    """
    volume = row.get("volume")
    sugg_cpc = row.get("suggested_max_cpc_micros")
    intent = row.get("intent", "") or ""
    if volume is None or sugg_cpc is None:
        return None
    ctr = INTENT_CTRS.get(intent, 0.0)
    if ctr == 0.0:
        return None
    monthly_clicks = float(volume) * ctr
    daily_clicks = monthly_clicks / 30.0
    avg_cpc_micros = float(sugg_cpc) * AVG_CPC_RATIO
    daily_spend_micros = daily_clicks * avg_cpc_micros
    return round(daily_spend_micros / 1_000_000, 4)


def compute_budget_clamp(
    ranked_enriched: list[dict],
    clusters_data: dict,
    daily_cap_usd: float | None,
    daily_spend_mid_usd_total: float,
) -> dict | None:
    """Build the budget-clamp subsection of forecast.json.

    Returns None when daily_cap_usd is None (no Budget: in brief). When a
    cap is set, returns a dict carrying:
      - daily_cap_usd            (echo of brief field)
      - daily_spend_mid_usd      (total forecast across the full pool)
      - over_cap_ratio           (total / cap; <1.0 = fits, >1.0 = trim needed)
      - keywords_fitting_cap[]   (priority-sorted keywords whose cumulative
                                  daily spend stays ≤ cap — the launch list)
      - keywords_dropped[]       (everything else by keyword name; summary)
      - fitting_count / dropped_count
      - cumulative_spend_mid_usd (sum across the fitting list — what to
                                  actually budget for)

    Priority: intent class (transactional > commercial > navigational >
    informational), then signal_count desc, then score desc — keeps the
    highest-conviction-buyer-intent keywords at the top of the cap.
    """
    if daily_cap_usd is None:
        return None

    # Build kw → cluster_name index so each "what fits" row carries its
    # destination cluster for the operator.
    kw_to_cluster: dict[str, str] = {}
    for cluster in clusters_data.get("clusters", []) or []:
        name = cluster.get("name", "") or ""
        for kw_entry in cluster.get("keywords", []) or []:
            key = (kw_entry.get("keyword") or "").lower().strip()
            if key:
                kw_to_cluster[key] = name

    # Annotate each row with per-keyword spend; drop unbidable.
    annotated: list[dict] = []
    for row in ranked_enriched:
        spend = _per_keyword_daily_spend_usd(row)
        if spend is None or spend <= 0:
            continue
        kw = (row.get("keyword") or "").lower().strip()
        annotated.append({
            "keyword": row.get("keyword"),
            "intent": row.get("intent", ""),
            "score": row.get("score", 0),
            "signal_count": row.get("signal_count", 0),
            "match_type": row.get("match_type", "phrase"),
            "daily_spend_mid_usd": spend,
            "cluster": kw_to_cluster.get(kw, ""),
        })

    # Priority sort: transactional first, then commercial, then navigational,
    # then informational; within an intent class, signal_count desc, score desc.
    annotated.sort(
        key=lambda r: (
            _INTENT_PRIORITY.get(r["intent"], 99),
            -r.get("signal_count", 0),
            -r.get("score", 0),
        )
    )

    # Walk in priority order; accept rows until cumulative spend would
    # exceed cap. A row that would overshoot is dropped (we never partially
    # bid on a keyword).
    fitting: list[dict] = []
    dropped: list[str] = []
    cumulative = 0.0
    for row in annotated:
        if cumulative + row["daily_spend_mid_usd"] <= daily_cap_usd:
            cumulative = round(cumulative + row["daily_spend_mid_usd"], 4)
            fitting.append({**row, "cumulative_spend_usd": cumulative})
        else:
            dropped.append(row["keyword"])

    over_cap_ratio = (
        round(daily_spend_mid_usd_total / daily_cap_usd, 2)
        if daily_cap_usd > 0 else None
    )

    return {
        "daily_cap_usd": round(daily_cap_usd, 2),
        "daily_spend_mid_usd": round(daily_spend_mid_usd_total, 2),
        "over_cap_ratio": over_cap_ratio,
        "fitting_count": len(fitting),
        "dropped_count": len(dropped),
        "cumulative_spend_mid_usd": round(cumulative, 2),
        "keywords_fitting_cap": fitting,
        "keywords_dropped": dropped,
    }


# ---------------------------------------------------------------------------
# Top-level forecast structure (FRCS-01, FRCS-05)
# ---------------------------------------------------------------------------

def _utc_iso_now() -> str:
    """Return UTC ISO timestamp like `2026-05-14T18:30:00Z` (deterministic format)."""
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_forecast(
    ranked_enriched: list[dict],
    clusters_data: dict,
    run_id: str,
    daily_cap_usd: float | None = None,
) -> dict:
    """Build full forecast.json structure (FRCS-01 schema).

    Aggregates campaign_totals as the SUM of per-cluster fields (no
    recomputation — Pitfall 5).
    """
    ranked_index = _build_ranked_index(ranked_enriched)

    cluster_forecasts: list[dict] = []
    total_unjoined = 0
    for cluster in clusters_data.get("clusters", []) or []:
        cf = compute_cluster_forecast(cluster, ranked_index)
        total_unjoined += cf.pop("unjoined_keywords", 0)
        cluster_forecasts.append(cf)

    # Campaign totals = SUM of per-cluster aggregates (no double-counting).
    daily_clicks_low_sum = sum(c["daily_clicks_low"] for c in cluster_forecasts)
    daily_clicks_mid_sum = sum(c["daily_clicks_mid"] for c in cluster_forecasts)
    daily_clicks_high_sum = sum(c["daily_clicks_high"] for c in cluster_forecasts)
    daily_spend_low_sum = round(
        sum(c["daily_spend_low_usd"] for c in cluster_forecasts), 2
    )
    daily_spend_mid_sum = round(
        sum(c["daily_spend_mid_usd"] for c in cluster_forecasts), 2
    )
    daily_spend_high_sum = round(
        sum(c["daily_spend_high_usd"] for c in cluster_forecasts), 2
    )
    monthly_spend_mid_sum = round(
        sum(c["monthly_spend_mid_usd"] for c in cluster_forecasts), 2
    )

    campaign_totals = {
        "cluster_count": len(cluster_forecasts),
        "keyword_count": sum(c["keyword_count"] for c in cluster_forecasts),
        "daily_clicks_low": daily_clicks_low_sum,
        "daily_clicks_mid": daily_clicks_mid_sum,
        "daily_clicks_high": daily_clicks_high_sum,
        "daily_spend_low_usd": daily_spend_low_sum,
        "daily_spend_mid_usd": daily_spend_mid_sum,
        "daily_spend_high_usd": daily_spend_high_sum,
        "monthly_spend_mid_usd": monthly_spend_mid_sum,
        "unjoined_keywords": total_unjoined,
    }

    # Budget clamp (FRCS-06) — only populated when brief carries `**Budget:**`.
    budget_clamp = compute_budget_clamp(
        ranked_enriched,
        clusters_data,
        daily_cap_usd=daily_cap_usd,
        daily_spend_mid_usd_total=daily_spend_mid_sum,
    )

    out = {
        "metadata": {
            "generated_at": _utc_iso_now(),
            "run_id": run_id,
            "schema_version": "v1",
            "horizon": "daily",
        },
        "methodology": {
            "intent_ctrs": dict(INTENT_CTRS),
            "avg_cpc_ratio": AVG_CPC_RATIO,
            "band_multipliers": dict(BAND_MULTIPLIERS),
            "notes": _METHODOLOGY_NOTES,
        },
        "clusters": cluster_forecasts,
        "campaign_totals": campaign_totals,
    }
    if budget_clamp is not None:
        out["budget_clamp"] = budget_clamp
    return out


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main_with_args(argv: list[str]) -> int:
    """CLI: forecast_budget --run-dir <path>.

    Reads {run_dir}/ranked-enriched.json + {run_dir}/clusters.json,
    writes {run_dir}/forecast.json with the FRCS-01 schema.

    Exit codes:
        0  ok
        2  retryable (transient disk error)
        3  fatal (missing input, malformed JSON)
    """
    parser = argparse.ArgumentParser(
        prog="forecast_budget",
        description=(
            "Write {run_dir}/forecast.json with per-cluster + campaign-level "
            "click and spend bands (FRCS-01..05)."
        ),
    )
    parser.add_argument("--run-dir", required=True, type=Path)

    # argv[0]-skip heuristic — matches serp_fetch.py / volume_enrich.py /
    # bid_suggest.py. Accept either full sys.argv or args-only list.
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

    for p, label in (
        (ranked_path, "ranked-enriched.json"),
        (clusters_path, "clusters.json"),
    ):
        if not p.exists():
            log.error("%s not found at %s", label, p)
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

    # FRCS-06: read Budget: from brief.md so build_forecast can emit the
    # budget-clamp subset. Absent line → clamp omitted, full forecast renders
    # unchanged (backward compat).
    daily_cap_usd = _parse_daily_budget_usd(run_dir / "brief.md")
    forecast = build_forecast(
        ranked, clusters_data,
        run_id=run_dir.name,
        daily_cap_usd=daily_cap_usd,
    )

    # Atomic-ish write: write to .tmp then rename.
    out_path = run_dir / "forecast.json"
    try:
        tmp = out_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(forecast, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(out_path)
    except OSError as exc:
        log.error("Failed to write forecast.json: %s", exc)
        return 2

    summary = {
        "clusters_forecast": len(forecast["clusters"]),
        "keywords_in_forecast": forecast["campaign_totals"]["keyword_count"],
        "daily_spend_mid_usd": forecast["campaign_totals"]["daily_spend_mid_usd"],
        "unjoined_keywords": forecast["campaign_totals"]["unjoined_keywords"],
    }
    if "budget_clamp" in forecast:
        bc = forecast["budget_clamp"]
        summary["budget_cap_usd"] = bc["daily_cap_usd"]
        summary["over_cap_ratio"] = bc["over_cap_ratio"]
        summary["fitting_count"] = bc["fitting_count"]
        summary["dropped_count"] = bc["dropped_count"]
        summary["cumulative_spend_mid_usd"] = bc["cumulative_spend_mid_usd"]
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv))
