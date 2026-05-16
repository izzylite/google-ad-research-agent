# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "google-ads>=24.0",
#     "python-dotenv>=1.0",
# ]
# ///
"""perf_fetch.py — Pull live Google Ads data for an account.

Three queries:
    1. search_term_view (last 30 days) — what real users typed + cost/conv
    2. campaign + ad_group performance (last 30 days)
    3. campaign_criterion + ad_group_criterion negatives (existing list)

Writes:
    {run_dir}/raw/google-ads-search-terms.json
    {run_dir}/raw/google-ads-perf.json
    {run_dir}/raw/google-ads-negatives.json

CLI:
    uv run perf_fetch.py --run-dir <abs> [--customer-id XXXX] [--days 30]
        [--campaign-filter "<name>"]   # single, or pipe-separated 'A|B|C'

Stdout (one JSON line):
    {"search_terms_count": N, "campaigns_count": N, "ad_groups_count": N,
     "existing_negatives_count": N, "customer_id": "..."}

Exit codes:
    0  ok
    2  retryable (transient API error)
    3  fatal (auth, missing input, IO)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.config import load_env  # noqa: E402
from lib.gads_client import build_gads_client, get_target_customer_id  # noqa: E402
from lib.log import configure_logger  # noqa: E402

log = configure_logger()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _date_literal(days: int) -> str:
    """Map int days to Google Ads date literal. Limited set is allowed."""
    if days <= 7:
        return "LAST_7_DAYS"
    if days <= 14:
        return "LAST_14_DAYS"
    return "LAST_30_DAYS"


def _escape_gaql_string(value: str) -> str:
    """Escape a string for safe inclusion in a single-quoted GAQL literal.

    GAQL string literals are single-quoted; embedded single quotes are
    escaped by doubling them: `O'Brien` → `O''Brien`. Newlines / backslashes
    are NOT special in GAQL string literals — only single quotes need handling.
    Campaign names with pipes are fine (pipe is only a CLI-level list separator).
    """
    return value.replace("'", "''")


def _apply_campaign_filter(campaign_filter: list[str] | None) -> str:
    """Build the `AND campaign.name = '...'` (single) or `IN (...)` (list) GAQL fragment.

    Returns an empty string when filter is None or [] — caller appends to
    the WHERE clause unconditionally, so empty string preserves v1.4
    behavior bit-for-bit (CAMP-04 backward compat).
    """
    if not campaign_filter:
        return ""
    names = [n.strip() for n in campaign_filter if n.strip()]
    if not names:
        return ""
    if len(names) == 1:
        return f"AND campaign.name = '{_escape_gaql_string(names[0])}'"
    quoted = ", ".join(f"'{_escape_gaql_string(n)}'" for n in names)
    return f"AND campaign.name IN ({quoted})"


def fetch_search_terms(client, customer_id: str, *, days: int = 30, campaign_filter: list[str] | None = None) -> list[dict]:
    """Pull last-N-day search terms with metrics."""
    svc = client.get_service("GoogleAdsService")
    date_lit = _date_literal(days)
    campaign_clause = _apply_campaign_filter(campaign_filter)
    query = f"""
        SELECT
            search_term_view.search_term,
            segments.search_term_match_type,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            campaign.name,
            ad_group.name
        FROM search_term_view
        WHERE segments.date DURING {date_lit}
        {campaign_clause}
        ORDER BY metrics.cost_micros DESC
        LIMIT 500
    """
    out: list[dict] = []
    for batch in svc.search_stream(customer_id=customer_id, query=query):
        for row in batch.results:
            out.append({
                "search_term": row.search_term_view.search_term,
                "match_type": row.segments.search_term_match_type.name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost_micros": row.metrics.cost_micros,
                "cost_usd": row.metrics.cost_micros / 1_000_000,
                "conversions": row.metrics.conversions,
                "conversions_value": row.metrics.conversions_value,
                "campaign_name": row.campaign.name,
                "ad_group_name": row.ad_group.name,
            })
    return out


def fetch_customer_name(client, customer_id: str) -> str:
    """Pull customer.descriptive_name for the queried account.

    Used as a defense-in-depth signal for the negatives brand-safety guard
    (generate_negatives.py) — the account's own brand should never be labelled
    as a competitor-brand negative. Returns empty string on lookup failure;
    caller treats absent name as "no signal" rather than a hard error.
    """
    svc = client.get_service("GoogleAdsService")
    try:
        for batch in svc.search_stream(
            customer_id=customer_id,
            query="SELECT customer.descriptive_name FROM customer",
        ):
            for row in batch.results:
                name = row.customer.descriptive_name or ""
                if name:
                    return name
    except Exception:
        return ""
    return ""


def fetch_perf(client, customer_id: str, *, days: int = 30, campaign_filter: list[str] | None = None) -> dict:
    """Pull campaign + ad_group performance metrics."""
    svc = client.get_service("GoogleAdsService")
    date_lit = _date_literal(days)
    campaign_clause = _apply_campaign_filter(campaign_filter)

    campaigns: list[dict] = []
    q1 = f"""
        SELECT
            campaign.id, campaign.name, campaign.status,
            campaign.advertising_channel_type,
            metrics.impressions, metrics.clicks, metrics.cost_micros,
            metrics.conversions, metrics.conversions_value
        FROM campaign
        WHERE segments.date DURING {date_lit}
        {campaign_clause}
        ORDER BY metrics.cost_micros DESC
    """
    for batch in svc.search_stream(customer_id=customer_id, query=q1):
        for row in batch.results:
            cost = row.metrics.cost_micros / 1_000_000
            campaigns.append({
                "campaign_id": str(row.campaign.id),
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "channel": row.campaign.advertising_channel_type.name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost_usd": cost,
                "conversions": row.metrics.conversions,
                "conversions_value": row.metrics.conversions_value,
                "cpa_usd": (cost / row.metrics.conversions) if row.metrics.conversions else None,
                "roas": (row.metrics.conversions_value / cost) if cost else None,
            })

    ad_groups: list[dict] = []
    q2 = f"""
        SELECT
            ad_group.id, ad_group.name, ad_group.status,
            campaign.name,
            metrics.impressions, metrics.clicks, metrics.cost_micros,
            metrics.conversions, metrics.conversions_value
        FROM ad_group
        WHERE segments.date DURING {date_lit}
        {campaign_clause}
        ORDER BY metrics.cost_micros DESC
        LIMIT 200
    """
    for batch in svc.search_stream(customer_id=customer_id, query=q2):
        for row in batch.results:
            cost = row.metrics.cost_micros / 1_000_000
            ad_groups.append({
                "ad_group_id": str(row.ad_group.id),
                "name": row.ad_group.name,
                "status": row.ad_group.status.name,
                "campaign_name": row.campaign.name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost_usd": cost,
                "conversions": row.metrics.conversions,
                "conversions_value": row.metrics.conversions_value,
            })

    return {
        "campaigns": campaigns,
        "ad_groups": ad_groups,
        "fetched_at": _now_iso(),
        "horizon_days": days,
    }


def fetch_existing_negatives(client, customer_id: str, *, campaign_filter: list[str] | None = None) -> list[dict]:
    """Pull all current negative keywords from campaign + ad group level."""
    svc = client.get_service("GoogleAdsService")
    campaign_clause = _apply_campaign_filter(campaign_filter)
    negatives: list[dict] = []

    # Campaign-level negatives
    q1 = f"""
        SELECT
            campaign.name,
            campaign_criterion.keyword.text,
            campaign_criterion.keyword.match_type,
            campaign_criterion.type
        FROM campaign_criterion
        WHERE campaign_criterion.negative = TRUE
          AND campaign_criterion.type = 'KEYWORD'
          {campaign_clause}
    """
    try:
        for batch in svc.search_stream(customer_id=customer_id, query=q1):
            for row in batch.results:
                negatives.append({
                    "level": "campaign",
                    "campaign": row.campaign.name,
                    "ad_group": None,
                    "keyword": row.campaign_criterion.keyword.text,
                    "match_type": row.campaign_criterion.keyword.match_type.name,
                })
    except Exception as exc:
        log.warning(f"Campaign-level negatives query failed: {exc}")

    # Ad group-level negatives
    q2 = f"""
        SELECT
            campaign.name,
            ad_group.name,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type
        FROM ad_group_criterion
        WHERE ad_group_criterion.negative = TRUE
          AND ad_group_criterion.type = 'KEYWORD'
          {campaign_clause}
    """
    try:
        for batch in svc.search_stream(customer_id=customer_id, query=q2):
            for row in batch.results:
                negatives.append({
                    "level": "ad_group",
                    "campaign": row.campaign.name,
                    "ad_group": row.ad_group.name,
                    "keyword": row.ad_group_criterion.keyword.text,
                    "match_type": row.ad_group_criterion.keyword.match_type.name,
                })
    except Exception as exc:
        log.warning(f"Ad-group-level negatives query failed: {exc}")

    return negatives


def fetch_keyword_view(client, customer_id: str, *, days: int = 30, campaign_filter: list[str] | None = None) -> list[dict]:
    """Pull last-N-day account keywords (active + paused) with metrics.

    Used by perf_synth.cross_ref_positives for POS-02 sync.
    PMax campaigns silently absent (no keyword-level data exposed).
    REMOVED keywords excluded — only ENABLED + PAUSED matter for sync.
    """
    svc = client.get_service("GoogleAdsService")
    date_lit = _date_literal(days)
    campaign_clause = _apply_campaign_filter(campaign_filter)
    query = f"""
        SELECT
            ad_group.id,
            ad_group.name,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.status,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM keyword_view
        WHERE segments.date DURING {date_lit}
          AND ad_group_criterion.status != 'REMOVED'
          {campaign_clause}
    """
    out: list[dict] = []
    for batch in svc.search_stream(customer_id=customer_id, query=query):
        for row in batch.results:
            out.append({
                "keyword": row.ad_group_criterion.keyword.text,
                "match_type": row.ad_group_criterion.keyword.match_type.name,
                "status": row.ad_group_criterion.status.name,
                "ad_group_id": str(row.ad_group.id),
                "ad_group_name": row.ad_group.name,
                "campaign_name": row.campaign.name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "conversions": row.metrics.conversions,
                "cost_micros": row.metrics.cost_micros,
            })
    return out


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Pull live Google Ads data (search terms, perf, negatives).",
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument(
        "--customer-id", default=None,
        help="Override target customer ID (defaults to GOOGLE_ADS_CUSTOMER_ID).",
    )
    parser.add_argument(
        "--login-customer-id", default=None,
        help="Override login_customer_id. Default = env. For direct (non-MCC) "
             "access, set login = customer.",
    )
    parser.add_argument("--days", type=int, default=30,
                        help="Performance horizon in days (default 30).")
    parser.add_argument(
        "--campaign-filter", default=None,
        help="Optional campaign name filter — single name or pipe-separated list "
             "(e.g., 'Search | Lake Worth Accident Exams | Manual CPC' or "
             "'Campaign A|Campaign B'). When set, all 4 GAQL queries gain "
             "AND campaign.name = '<focus>' (single) or IN (...) (list). "
             "Omit for account-wide pull (v1.4 behavior). CAMP-02.",
    )
    args = parser.parse_args(argv)

    # Normalize --campaign-filter into list[str] | None.
    # Heuristic: Google Ads naming convention uses ' | ' (space-pipe-space) as
    # part of a single campaign name (e.g. 'Search | Lake Worth Accident Exams
    # | Manual CPC' is ONE campaign). The list form requires bare pipes
    # (no spaces): 'A|B|C'. So we only split when '|' is present AND ' | '
    # is NOT present.
    campaign_filter: list[str] | None = None
    if args.campaign_filter:
        raw = args.campaign_filter
        if "|" in raw and " | " not in raw:
            campaign_filter = [s.strip() for s in raw.split("|") if s.strip()]
        else:
            campaign_filter = [raw.strip()] if raw.strip() else None
        if campaign_filter:
            log.info(f"Narrowing to campaign(s): {campaign_filter}")

    if not args.run_dir.exists():
        log.error(f"--run-dir does not exist: {args.run_dir}")
        return 3

    try:
        load_env()
        customer_id = args.customer_id or get_target_customer_id()
        # Default: login = customer (direct access). Owner of MCC token will
        # need to override --login-customer-id.
        login_id = args.login_customer_id or customer_id
        client = build_gads_client(login_customer_id=login_id)
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    # google-ads exception types are loaded only when client imports succeed
    from google.ads.googleads.errors import GoogleAdsException

    raw_dir = args.run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    try:
        log.info(f"Pulling search terms (last {args.days}d, customer={customer_id})...")
        terms = fetch_search_terms(client, customer_id, days=args.days, campaign_filter=campaign_filter)
        (raw_dir / "google-ads-search-terms.json").write_text(
            json.dumps({"fetched_at": _now_iso(), "horizon_days": args.days,
                        "customer_id": customer_id, "items": terms},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info(f"  → {len(terms)} search terms")

        log.info("Pulling campaign + ad_group perf...")
        perf = fetch_perf(client, customer_id, days=args.days, campaign_filter=campaign_filter)
        perf["customer_id"] = customer_id
        # Customer descriptive name — defense-in-depth for negatives brand-safety
        # guard (generate_negatives.py reads this to never label the client's own
        # brand as competitor-brand). Empty string on lookup failure — guard
        # degrades gracefully to brand_terms-only.
        perf["customer_descriptive_name"] = fetch_customer_name(client, customer_id)
        (raw_dir / "google-ads-perf.json").write_text(
            json.dumps(perf, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info(f"  → {len(perf['campaigns'])} campaigns, {len(perf['ad_groups'])} ad groups · account: {perf['customer_descriptive_name'] or '(name unavailable)'}")

        log.info("Pulling existing negative keywords...")
        negs = fetch_existing_negatives(client, customer_id, campaign_filter=campaign_filter)
        (raw_dir / "google-ads-negatives.json").write_text(
            json.dumps({"fetched_at": _now_iso(), "customer_id": customer_id,
                        "items": negs}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info(f"  → {len(negs)} existing negatives")

        log.info("Pulling keyword_view (active + paused account keywords)...")
        kws = fetch_keyword_view(client, customer_id, days=args.days, campaign_filter=campaign_filter)
        (raw_dir / "google-ads-keywords.json").write_text(
            json.dumps({"fetched_at": _now_iso(), "horizon_days": args.days,
                        "customer_id": customer_id, "items": kws},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info(f"  → {len(kws)} active+paused keywords")

    except GoogleAdsException as exc:
        log.error(f"Google Ads API failure: {exc.error.code().name}")
        for err in exc.failure.errors:
            log.error(f"  {err.message}")
        return 2
    except Exception as exc:
        log.error(f"Unexpected error: {type(exc).__name__}: {exc}")
        return 3

    print(json.dumps({
        "search_terms_count": len(terms),
        "campaigns_count": len(perf["campaigns"]),
        "ad_groups_count": len(perf["ad_groups"]),
        "existing_negatives_count": len(negs),
        "keyword_count": len(kws),
        "customer_id": customer_id,
        "horizon_days": args.days,
        "campaign_filter": campaign_filter,  # null when absent — CAMP-02 traceability
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv[1:]))
