# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.28",
#     "httpx-retries>=0.5",
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
"""competitor_intel.py — Per-cluster Serper requery, affiliate filter, domain dedup.

CLI:
    uv run competitor_intel.py --run-dir <abs path> [--gl uk] [--hl en-GB] [--max-advertisers 5]

Reads:  <run_dir>/clusters.json
Writes: <run_dir>/raw/competitor-intel.json

Stdout (exactly one JSON line):
    {"run_dir": "...", "clusters_processed": N, "serper_credits_used": N}

Exit codes:
    0  ok
    2  retryable (Serper HTTP error)
    3  fatal (missing input file, bad Serper API key, missing env var)

Landing-page extraction is Phase 5 Step 19 (Claude WebFetch in SKILL.md), not Python.
Advertisers are emitted directly from the post-dedupe Serper ad block.
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
# Helper functions (all importable for unit tests without Serper)
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
    """Parse argv, run per-cluster Serper requery + fallback pipeline, write competitor-intel.json."""
    parser = argparse.ArgumentParser(
        description="Per-cluster competitor ad copy (Serper-only).",
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

    # Load env / validate keys (Serper only; LP extraction moved to Phase 5 WebFetch)
    try:
        load_env(require=("SERPER_API_KEY",))
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    serper_key = os.environ["SERPER_API_KEY"]

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
        },
        "clusters": {},
    }

    serper_credits = 0

    # Build Serper client
    serper_client = build_client(timeout=30.0)

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
        source_label = "ads"

        # 2a. Fall back to top organic when ads block is empty/sparse.
        # Top organic results for the cluster's representative keyword are, by
        # definition, the businesses competing on that intent — their landing
        # pages contain the same value props paid advertisers would highlight.
        # Serper's ads block is unreliable (often empty even when Google shows
        # ads); organic is consistently populated.
        if not ads_raw:
            organic = normalised.get("organic", [])
            ads_raw = [
                {
                    "title": o.get("title"),
                    "snippet": o.get("snippet"),
                    "link": o.get("link"),
                    # treat link as displayUrl so dedupe + affiliate logic works
                    "displayUrl": o.get("link"),
                    "position": o.get("position"),
                }
                for o in organic
                if o.get("link")
            ]
            source_label = "organic"
            log.info(f"{name}: ads block empty, falling back to top organic ({len(ads_raw)} results)")

        # 2b. Affiliate filter
        ads_clean, filtered_count = filter_ads(ads_raw)
        log.info(
            f"{name}: {len(ads_raw)} {source_label} raw, {filtered_count} filtered (affiliate), "
            f"{len(ads_clean)} remaining"
        )

        # 3. Domain dedupe
        ads_deduped = dedupe_by_domain(ads_clean)

        # 4. Top N advertisers
        top_ads = ads_deduped[:max_adv]

        # 5. Build advertisers list directly from Serper top_ads.
        #    Landing-page extraction is Phase 5 Step 19 (Claude WebFetch in
        #    SKILL.md), not Python. The render_report _load_competitor_landing_pages
        #    helper (WFCH-02, Plan 12-04) joins raw/competitor-landing-pages.json
        #    onto these advertisers entries for the final report.
        advertisers = [
            {
                "domain": extract_domain(ad.get("displayUrl") or ad.get("link", "")),
                "url": ad.get("link", ""),
                "title": ad.get("title"),
                "description": ad.get("snippet", ""),
                "position": ad.get("position"),
            }
            for ad in top_ads
        ]

        # Build cluster output entry
        output["clusters"][name] = {
            "representative_keyword": rep_kw,
            "serper_fetched_at": fetched_at,
            "advertiser_source": source_label,  # "ads" or "organic" fallback
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

    # Write output
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    log.info(f"Wrote {out_path}")

    print(json.dumps({
        "run_dir": str(run_dir),
        "clusters_processed": len(clusters_list),
        "serper_credits_used": serper_credits,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv[1:]))
