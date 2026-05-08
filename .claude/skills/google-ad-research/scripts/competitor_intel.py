# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.28",
#     "httpx-retries>=0.5",
#     "tavily-python>=0.7.24",
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
"""competitor_intel.py — Per-cluster Serper requery, affiliate filter, domain dedup, Tavily LP extract.

CLI:
    uv run competitor_intel.py --run-dir <abs path> [--gl uk] [--hl en-GB] [--max-advertisers 5]

Reads:  <run_dir>/clusters.json
Writes: <run_dir>/raw/competitor-intel.json

Stdout (exactly one JSON line):
    {"run_dir": "...", "clusters_processed": N, "serper_credits_used": N, "tavily_credits_used": N}

Exit codes:
    0  ok
    2  retryable (Tavily quota exceeded)
    3  fatal (missing input file, bad API key, missing env var)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Make sibling lib/ importable when invoked via `uv run path/to/competitor_intel.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402

from lib.config import load_env  # noqa: E402
from lib.http import build_client  # noqa: E402
from lib.log import configure_logger  # noqa: E402

from tavily import TavilyClient  # noqa: E402
from tavily import (  # noqa: E402
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
)

# Re-use fetch_seed and normalise_response from serp_fetch.py
from serp_fetch import fetch_seed, normalise_response  # noqa: E402

log = configure_logger()

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

MAX_ADVERTISERS = 5

AFFILIATE_PARAMS = frozenset({"ref", "aff_id", "affiliate_id", "partner_id", "affid", "aff_sub"})

AFFILIATE_PATH_FRAGMENTS = ("/aff/", "/affiliate/", "/out/", "/track/")

AFFILIATE_DOMAINS = frozenset({
    "awin.com", "awin1.com",
    "skimlinks.com",
    "partnerize.com",
    "viglink.com",
    "sovrn.com",
    "rakuten.com", "rakutenadvertising.com",
    "tradedoubler.com",
    "cj.com",
    "shareasale.com",
    "impactradius.com", "impact.com",
    "pepperjam.com",
    "webgains.com",
    "zanox.com",
    "affiliatefuture.com",
    "vouchercloud.com", "vouchercodes.co.uk",
    "myvouchercodes.co.uk", "hotukdeals.com",
    "topcashback.co.uk", "quidco.com",
    "cashbackkings.com",
})


# ---------------------------------------------------------------------------
# Helper functions (all importable for unit tests without Serper/Tavily)
# ---------------------------------------------------------------------------

def extract_domain(url: str) -> str:
    """Return lowercase domain, stripping www. prefix.

    Handles schemeless URLs like 'tesco.com/path' by prepending '//' so that
    urlparse treats the leading component as netloc rather than path.
    """
    try:
        if url and "://" not in url and not url.startswith("//"):
            url = "//" + url
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return netloc.removeprefix("www.")
    except Exception:
        return ""


def is_affiliate_url(url: str) -> bool:
    """Return True if the URL contains affiliate query params or path fragments."""
    try:
        parsed = urllib.parse.urlparse(url)
        params = set(urllib.parse.parse_qs(parsed.query).keys())
        if params & AFFILIATE_PARAMS:
            return True
        path_lower = parsed.path.lower()
        return any(frag in path_lower for frag in AFFILIATE_PATH_FRAGMENTS)
    except Exception:
        return False


def is_affiliate_domain(url: str) -> bool:
    """Return True if the URL's domain matches the affiliate domain blocklist (exact or subdomain)."""
    domain = extract_domain(url)
    if not domain:
        return False
    # Exact match
    if domain in AFFILIATE_DOMAINS:
        return True
    # Subdomain match: e.g. sub.awin.com ends with ".awin.com"
    return any(domain.endswith("." + d) for d in AFFILIATE_DOMAINS)


def is_affiliate(ad: dict) -> bool:
    """Return True if the ad is from an affiliate (URL param or domain blocklist check)."""
    link = ad.get("link", "")
    display_url = ad.get("displayUrl") or link
    return is_affiliate_url(link) or is_affiliate_domain(display_url)


def dedupe_by_domain(ads: list[dict]) -> list[dict]:
    """Keep one ad per advertiser domain; highest position (lowest number) wins.

    Falls back to link netloc when displayUrl is absent or unparseable.
    """
    seen: dict[str, dict] = {}
    for ad in sorted(ads, key=lambda a: a.get("position") or 99):
        display = ad.get("displayUrl") or ""
        domain = extract_domain(display)
        if not domain:
            # Fallback: extract from link field
            link = ad.get("link", "")
            domain = extract_domain(link)
        if domain and domain not in seen:
            seen[domain] = ad
    return list(seen.values())


def filter_ads(ads: list[dict]) -> tuple[list[dict], int]:
    """Filter out affiliate ads. Returns (clean_ads, filtered_count)."""
    clean = [a for a in ads if not is_affiliate(a)]
    filtered_count = len(ads) - len(clean)
    return clean, filtered_count


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main_with_args(argv: list[str]) -> int:
    """Parse argv, run per-cluster Serper + Tavily pipeline, write competitor-intel.json."""
    parser = argparse.ArgumentParser(
        description="Per-cluster competitor ad copy + LP extraction.",
    )
    parser.add_argument("--run-dir", required=True, type=Path,
                        help="Absolute path to the sealed run folder.")
    parser.add_argument("--gl", default="uk",
                        help="Google locale country code (default: uk).")
    parser.add_argument("--hl", default="en-GB",
                        help="Google locale language code (default: en-GB).")
    parser.add_argument("--max-advertisers", type=int, default=MAX_ADVERTISERS,
                        help=f"Max advertisers per cluster (default: {MAX_ADVERTISERS}, min: 3).")
    args = parser.parse_args(argv)

    # Enforce minimum
    max_adv = max(args.max_advertisers, 3)

    run_dir = args.run_dir

    # Load env / validate keys
    try:
        load_env(require=("SERPER_API_KEY", "TAVILY_API_KEY"))
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    serper_key = os.environ["SERPER_API_KEY"]
    tavily_key = os.environ["TAVILY_API_KEY"]

    # Read clusters.json
    clusters_path = run_dir / "clusters.json"
    if not clusters_path.exists():
        log.error(f"clusters.json not found: {clusters_path}")
        return 3

    try:
        clusters_data = json.loads(clusters_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.error(f"Failed to read clusters.json: {exc}")
        return 3

    # Prepare output
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    out_path = raw_dir / "competitor-intel.json"

    output: dict = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "clusters_input": "clusters.json",
            "serper_credits_used": 0,
            "tavily_credits_used": 0,
        },
        "clusters": {},
    }

    serper_credits = 0
    tavily_credits = 0

    # Build clients
    serper_client = build_client(timeout=30.0)
    tavily_client = TavilyClient(api_key=tavily_key)

    clusters_list = clusters_data.get("clusters", [])

    for cluster in clusters_list:
        name = cluster.get("name", "unknown")
        keywords = cluster.get("keywords", [])

        if not keywords:
            log.warning(f"{name}: no keywords — skipping Serper call")
            output["clusters"][name] = {
                "representative_keyword": "",
                "serper_fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "ads_raw_count": 0,
                "ads_filtered_count": 0,
                "ads": [],
                "advertisers": [],
            }
            continue

        rep_kw = keywords[0]["keyword"]

        # 1. Serper ads fetch
        try:
            raw = fetch_seed(
                serper_client,
                rep_kw,
                gl=args.gl,
                hl=args.hl,
                num=10,
                api_key=serper_key,
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                log.error(f"Serper auth failure for {name!r}: {status}")
                serper_client.close()
                return 3
            log.error(f"Serper retryable failure for {name!r}: {exc}")
            serper_client.close()
            return 2

        fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        serper_credits += 1

        normalised = normalise_response(raw, seed=rep_kw, gl=args.gl, hl=args.hl)
        ads_raw = normalised.get("ads", [])

        # 2. Affiliate filter
        ads_clean, filtered_count = filter_ads(ads_raw)
        log.info(
            f"{name}: {len(ads_raw)} ads raw, {filtered_count} filtered (affiliate), "
            f"{len(ads_clean)} remaining"
        )

        # 3. Domain dedupe
        ads_deduped = dedupe_by_domain(ads_clean)

        # 4. Top N advertisers
        top_ads = ads_deduped[:max_adv]

        # 5. Tavily LP extract
        lp_urls = [a["link"] for a in top_ads if a.get("link")]
        advertisers: list[dict] = []

        if lp_urls:
            try:
                tavily_response = tavily_client.extract(
                    urls=lp_urls,
                    extract_depth="basic",
                    format="markdown",
                    include_usage=True,
                )
            except (InvalidAPIKeyError, MissingAPIKeyError) as exc:
                log.error(f"Tavily auth failure: {exc}")
                serper_client.close()
                return 3
            except UsageLimitExceededError as exc:
                log.error(f"Tavily quota exceeded: {exc}")
                serper_client.close()
                return 2
            except Exception as exc:
                log.warning(f"Tavily extract failed for {name!r}: {exc}")
                tavily_response = {"results": [], "failed_results": [], "usage": {}}

            tavily_fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            usage = tavily_response.get("usage", {})
            tavily_credits += usage.get("extract_credits", 0)

            for result in tavily_response.get("results", []):
                advertisers.append({
                    "domain": extract_domain(result.get("url", "")),
                    "url": result.get("url", ""),
                    "raw_content": result.get("raw_content", ""),
                    "tavily_fetched_at": tavily_fetched_at,
                    "extract_status": "ok",
                })

            for failed in tavily_response.get("failed_results", []):
                advertisers.append({
                    "domain": extract_domain(failed.get("url", "")),
                    "url": failed.get("url", ""),
                    "raw_content": "",
                    "extract_status": "failed",
                })

        # Build cluster output entry
        output["clusters"][name] = {
            "representative_keyword": rep_kw,
            "serper_fetched_at": fetched_at,
            "ads_raw_count": len(ads_raw),
            "ads_filtered_count": filtered_count,
            "ads": [
                {
                    "title": a.get("title"),
                    "description": a.get("snippet", ""),
                    "domain": extract_domain(a.get("displayUrl") or a.get("link", "")),
                    "displayed_url": a.get("displayUrl", ""),
                    "link": a.get("link", ""),
                    "position": a.get("position"),
                }
                for a in ads_deduped
            ],
            "advertisers": advertisers,
        }

    serper_client.close()

    # Update metadata credits
    output["metadata"]["serper_credits_used"] = serper_credits
    output["metadata"]["tavily_credits_used"] = tavily_credits

    # Write output
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    log.info(f"Wrote {out_path}")

    print(json.dumps({
        "run_dir": str(run_dir),
        "clusters_processed": len(clusters_list),
        "serper_credits_used": serper_credits,
        "tavily_credits_used": tavily_credits,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv[1:]))
