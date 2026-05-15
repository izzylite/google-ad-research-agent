# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""One-shot fixture slimmer for Phase 16 plan 16-00.

Reads the real Lake Worth run and writes 5 golden fixtures under
.claude/skills/google-ad-research/scripts/tests/fixtures/.

Idempotent: re-running produces byte-identical output (sorted keys, no random).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / ".runs" / "2026-05-15T153121Z-car-accident-injury-care-services"
DST = REPO / ".claude" / "skills" / "google-ad-research" / "scripts" / "tests" / "fixtures"

# Hardcoded for reproducibility (3 AGs from the real account; only 1 is ENABLED).
NARROWED_AG_NAMES = {
    "Accident Exams – Lake Worth",            # ENABLED
    "AG1 - Accident Urgent Care / Doctor",        # PAUSED
    "AG2 - PIP / No-Fault Exam",                  # PAUSED
}
# Per-source narrative: only Accident Exams ENABLED in real data.
CAMPAIGN_NAME = "Search | Lake Worth Accident Exams | Manual CPC"


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE {path.relative_to(REPO)}  ({path.stat().st_size} bytes)")


def main() -> int:
    # 1. ranked_lake_worth.json — copy verbatim from real run (sorted for determinism).
    ranked_src = SRC / "ranked-enriched.json"
    ranked = json.loads(ranked_src.read_text(encoding="utf-8"))
    _write(DST / "ranked_lake_worth.json", ranked)

    # 2. google-ads-perf-lake-worth.json — keep the single campaign + its 3 AGs
    #    (preserve status field so _build_ad_group_index filters correctly).
    perf_full = json.loads((SRC / "raw" / "google-ads-perf.json").read_text(encoding="utf-8"))
    perf_slim = {
        "fetched_at": perf_full.get("fetched_at"),
        "horizon_days": perf_full.get("horizon_days"),
        "customer_id": perf_full.get("customer_id"),
        "campaigns": [
            {"name": c.get("name"), "status": c.get("status")}
            for c in perf_full.get("campaigns", [])
            if c.get("name") == CAMPAIGN_NAME
        ],
        "ad_groups": [
            {
                "name": ag.get("name"),
                "status": ag.get("status"),
                "ad_group_id": ag.get("ad_group_id"),
            }
            for ag in perf_full.get("ad_groups", [])
            if ag.get("name") in NARROWED_AG_NAMES
        ],
    }
    _write(DST / "google-ads-perf-lake-worth.json", perf_slim)

    # 3. google-ads-search-terms-lake-worth.json — narrowed to the 3 AGs,
    #    keep only fields used by _build_ad_group_index + (Phase 16) _build_ag_token_bag.
    st_full = json.loads((SRC / "raw" / "google-ads-search-terms.json").read_text(encoding="utf-8"))
    st_items = [
        {
            "ad_group_name": it.get("ad_group_name"),
            "search_term": it.get("search_term"),
            "clicks": it.get("clicks"),
            "impressions": it.get("impressions"),
        }
        for it in st_full.get("items", [])
        if it.get("ad_group_name") in NARROWED_AG_NAMES
    ]
    st_slim = {
        "fetched_at": st_full.get("fetched_at"),
        "horizon_days": st_full.get("horizon_days"),
        "customer_id": st_full.get("customer_id"),
        "items": st_items,
    }
    _write(DST / "google-ads-search-terms-lake-worth.json", st_slim)

    # 4. google-ads-keywords-lake-worth.json — narrowed to the 3 AGs.
    #    NOTE: Real Phase 14 schema has top-level `keyword` field. To match the
    #    Phase 16 plan 16-01 contract (which expects ad_group_criterion.keyword.text),
    #    we ALSO emit the nested shape so wave-2 implementation can read either.
    #    Drop REMOVED rows (none present in real data; all are PAUSED or ENABLED).
    kw_full = json.loads((SRC / "raw" / "google-ads-keywords.json").read_text(encoding="utf-8"))
    kw_items = []
    for it in kw_full.get("items", []):
        if it.get("ad_group_name") not in NARROWED_AG_NAMES:
            continue
        status = (it.get("status") or "").upper()
        if status == "REMOVED":
            continue
        kw_items.append({
            "ad_group_name": it.get("ad_group_name"),
            "ad_group_criterion": {
                "keyword": {
                    "text": it.get("keyword"),
                    "match_type": it.get("match_type"),
                },
                "status": it.get("status"),
            },
        })
    kw_slim = {
        "fetched_at": kw_full.get("fetched_at"),
        "horizon_days": kw_full.get("horizon_days"),
        "customer_id": kw_full.get("customer_id"),
        "items": kw_items,
    }
    _write(DST / "google-ads-keywords-lake-worth.json", kw_slim)

    # 5. golden_mapping_lake_worth.json — shape-contract floor + AG name list.
    enabled_names = sorted(
        ag["name"] for ag in perf_slim["ad_groups"]
        if (ag.get("status") or "").upper() == "ENABLED"
    )
    golden = {
        "mapping_coverage_pct_floor": 50.0,
        "expected_ad_groups": enabled_names,
        "total_ranked": len(ranked),
        "notes": (
            "Generated 2026-05-15 from Lake Worth real run "
            "(.runs/2026-05-15T153121Z-car-accident-injury-care-services). "
            "Real account has 1 ENABLED AG (Accident Exams – Lake Worth) + 2 PAUSED "
            "(AG1/AG2). Phase 11 today yields 0% coverage because search-term-only "
            "bag is missing kw_criteria. Phase 16 floor: >=50% high+medium after "
            "_build_ag_token_bag unions kw_criteria + AG name tokens + top-N search "
            "terms. Floor not equality — Wave 2 calibration may yield 55-75% "
            "depending on threshold tuning."
        ),
    }
    _write(DST / "golden_mapping_lake_worth.json", golden)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
