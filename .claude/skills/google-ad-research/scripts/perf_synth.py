# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""perf_synth.py — Synthesize Google Ads performance + negative cross-ref.

Reads:
    {run_dir}/raw/google-ads-search-terms.json
    {run_dir}/raw/google-ads-perf.json
    {run_dir}/raw/google-ads-negatives.json
    {run_dir}/negatives.json                (our generated list)

Writes:
    {run_dir}/account-perf.json — top campaigns/ad groups/search terms,
                                   converted vs lossy terms, perf summary
    {run_dir}/negatives-sync.json — our negatives flagged
                                     `already_in_account` vs `new_candidate`

CLI:
    uv run perf_synth.py --run-dir <abs>

Stdout (one JSON line):
    {"account_perf_path": "...",
     "negatives_sync_path": "...",
     "top_search_terms_count": N,
     "already_in_account": N,
     "new_candidates": N}

Exit codes:
    0  ok
    3  fatal (missing input, IO)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _norm_neg(text: str) -> str:
    """Normalize negative keyword for comparison.

    Lowercase, strip leading/trailing whitespace + match-type punctuation
    (Google Ads stores "+phrase" / "[exact]" / "\"phrase\"" depending on
    match type — strip those for cross-reference).
    """
    if not text:
        return ""
    s = text.lower().strip()
    s = s.strip('"[]')
    s = " ".join(t.lstrip("+") for t in s.split())
    return s


def synth_account_perf(perf: dict, terms_data: dict) -> dict:
    """Build report-ready summary from perf + search-term raws."""
    campaigns = perf.get("campaigns", [])
    ad_groups = perf.get("ad_groups", [])
    terms = terms_data.get("items", [])

    # Active spend only
    active_camps = [c for c in campaigns if c.get("cost_usd", 0) > 0]
    active_camps.sort(key=lambda c: -c.get("cost_usd", 0))

    # Top campaigns by ROAS (filter zero-cost or zero-conv noise)
    by_roas = [c for c in active_camps if c.get("roas") and c["roas"] > 0]
    by_roas.sort(key=lambda c: -c["roas"])

    # Top campaigns by CPA (lower better, exclude zero-conv)
    by_cpa = [c for c in active_camps if c.get("cpa_usd") and c["cpa_usd"] > 0]
    by_cpa.sort(key=lambda c: c["cpa_usd"])

    # Converted search terms (terms w/ conversions > 0)
    converted = [t for t in terms if t.get("conversions", 0) > 0]
    converted.sort(key=lambda t: -t.get("conversions", 0))

    # Lossy terms — clicks but no conversions (best negative candidates)
    lossy = [
        t for t in terms
        if t.get("clicks", 0) > 0 and t.get("conversions", 0) == 0
    ]
    lossy.sort(key=lambda t: -t.get("cost_usd", 0))

    # Totals
    total_cost = sum(c.get("cost_usd", 0) for c in campaigns)
    total_clicks = sum(c.get("clicks", 0) for c in campaigns)
    total_conv = sum(c.get("conversions", 0) for c in campaigns)
    total_conv_value = sum(c.get("conversions_value", 0) for c in campaigns)

    return {
        "synthesized_at": _now_iso(),
        "horizon_days": perf.get("horizon_days"),
        "customer_id": perf.get("customer_id"),
        "totals": {
            "spend_usd": round(total_cost, 2),
            "clicks": total_clicks,
            "conversions": round(total_conv, 1),
            "conversions_value_usd": round(total_conv_value, 2),
            "blended_cpa_usd": round(total_cost / total_conv, 2) if total_conv else None,
            "blended_roas": round(total_conv_value / total_cost, 2) if total_cost else None,
        },
        "active_campaigns": active_camps[:20],
        "top_by_roas": by_roas[:10],
        "top_by_cpa": by_cpa[:10],
        "top_ad_groups_by_spend": sorted(ad_groups, key=lambda a: -a.get("cost_usd", 0))[:15],
        "converted_search_terms": converted[:25],
        "lossy_search_terms": lossy[:25],
        "total_search_terms": len(terms),
    }


def synth_negatives_sync(our_negs: list[dict],
                         existing_negs: list[dict]) -> dict:
    """Cross-reference our negatives.json vs account negatives.

    Returns dict w/ already_in_account[], new_candidates[], and a stat block.
    """
    existing_set = {_norm_neg(n.get("keyword", "")) for n in existing_negs}

    already = []
    new_candidates = []
    for n in our_negs:
        norm = _norm_neg(n.get("keyword", ""))
        if norm and norm in existing_set:
            already.append({**n, "status": "already_in_account"})
        else:
            new_candidates.append({**n, "status": "new_candidate"})

    # Bucket new candidates by tier
    by_tier: dict[str, list[dict]] = {"Strong": [], "Considered": [], "Investigate": []}
    for n in new_candidates:
        tier = n.get("tier", "Investigate")
        if tier in by_tier:
            by_tier[tier].append(n)

    return {
        "synthesized_at": _now_iso(),
        "our_total": len(our_negs),
        "existing_total": len(existing_negs),
        "already_in_account": already,
        "new_candidates": new_candidates,
        "new_by_tier": {t: by_tier[t] for t in ("Strong", "Considered", "Investigate")},
        "stats": {
            "our_total": len(our_negs),
            "existing_in_account": len(existing_negs),
            "already_covered": len(already),
            "new_to_add": len(new_candidates),
            "new_strong": len(by_tier["Strong"]),
            "new_considered": len(by_tier["Considered"]),
            "new_investigate": len(by_tier["Investigate"]),
        },
    }


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Synthesize Google Ads perf + negative cross-ref.",
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    run_dir = args.run_dir
    if not run_dir.exists():
        print(json.dumps({"error": f"--run-dir does not exist: {run_dir}"}),
              file=sys.stderr)
        return 3

    raw_dir = run_dir / "raw"
    terms_path = raw_dir / "google-ads-search-terms.json"
    perf_path = raw_dir / "google-ads-perf.json"
    negs_existing_path = raw_dir / "google-ads-negatives.json"
    our_negs_path = run_dir / "negatives.json"

    missing = [p for p in (terms_path, perf_path) if not p.exists()]
    if missing:
        print(json.dumps({
            "error": f"Missing required input(s): {[str(p) for p in missing]}. "
                     f"Run perf_fetch.py first.",
        }), file=sys.stderr)
        return 3

    try:
        terms_data = json.loads(terms_path.read_text(encoding="utf-8"))
        perf = json.loads(perf_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"error": f"Failed to load raws: {exc}"}), file=sys.stderr)
        return 3

    account_perf = synth_account_perf(perf, terms_data)
    out_perf = run_dir / "account-perf.json"
    out_perf.write_text(json.dumps(account_perf, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    # Negatives sync only when we have both sides
    new_candidates_count = 0
    already_count = 0
    if negs_existing_path.exists() and our_negs_path.exists():
        try:
            existing = json.loads(negs_existing_path.read_text(encoding="utf-8")).get("items", [])
            ours = json.loads(our_negs_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(json.dumps({"error": f"Failed to load negatives: {exc}"}),
                  file=sys.stderr)
            return 3
        sync = synth_negatives_sync(ours, existing)
        (run_dir / "negatives-sync.json").write_text(
            json.dumps(sync, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        new_candidates_count = sync["stats"]["new_to_add"]
        already_count = sync["stats"]["already_covered"]

    print(json.dumps({
        "account_perf_path": str(out_perf),
        "negatives_sync_path": str(run_dir / "negatives-sync.json"),
        "top_search_terms_count": len(account_perf.get("converted_search_terms", [])),
        "lossy_terms_count": len(account_perf.get("lossy_search_terms", [])),
        "already_in_account": already_count,
        "new_candidates": new_candidates_count,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv[1:]))
