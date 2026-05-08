# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.28",
#     "httpx-retries>=0.5",
#     "tavily-python>=0.7.24",
#     "python-dotenv>=1.0",
# ]
# ///
"""pulse_fetch.py — Time-sensitive news harvest for niche pulse phase.

Calls Serper /news endpoint (last 7 days) and Tavily search(topic="news")
per seed keyword. Persists raw responses to:
  {run_dir}/raw/serper-news.json
  {run_dir}/raw/tavily-news.json

These feed pulse_synth.py which produces the canonical niche-pulse.json.

CLI:
    uv run pulse_fetch.py --run-dir <abs path> --seeds "kw1" "kw2" ... \\
        --gl us --hl en [--days 7] [--num 10]

Stdout (one JSON line):
    {"raw_paths": {...}, "seed_count": N,
     "serper_news_count": N, "tavily_news_count": N,
     "serper_credits_used": N, "tavily_credits_used": N}

Exit codes:
    0  ok
    2  retryable (Serper transient / Tavily quota)
    3  fatal (auth, missing args, IO)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make sibling lib/ importable
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

log = configure_logger()
SERPER_NEWS_URL = "https://google.serper.dev/news"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_serper_news(
    client: httpx.Client,
    seed: str,
    *,
    gl: str,
    hl: str,
    days: int = 7,
    num: int = 10,
    api_key: str,
) -> dict:
    """One Serper /news call. Last `days` window via tbs=qdr param.

    Serper supports `qdr:h` (hour), `qdr:d` (day), `qdr:w` (week),
    `qdr:m` (month). We map days → coarsest matching qdr.
    """
    if days <= 1:
        qdr = "qdr:d"
    elif days <= 7:
        qdr = "qdr:w"
    elif days <= 31:
        qdr = "qdr:m"
    else:
        qdr = "qdr:y"

    payload = {"q": seed, "gl": gl, "hl": hl, "num": num, "tbs": qdr}
    response = client.post(
        SERPER_NEWS_URL,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json=payload,
    )
    response.raise_for_status()
    return json.loads(response.content.decode("utf-8", errors="replace"))


def normalise_serper_news(raw: dict, *, seed: str, gl: str, hl: str) -> list[dict]:
    """Pull the news array; defensive .get() everywhere."""
    return [
        {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
            "date": item.get("date"),
            "source": item.get("source"),
            "image_url": item.get("imageUrl"),
            "from_seed": seed,
            "locale": {"gl": gl, "hl": hl},
            "_source": "serper-news",
        }
        for item in raw.get("news", [])
    ]


def fetch_tavily_news(
    client: TavilyClient,
    seed: str,
    *,
    days: int = 7,
    max_results: int = 10,
) -> dict:
    """One Tavily search call with topic='news'."""
    return client.search(
        query=seed,
        topic="news",
        days=days,
        max_results=max_results,
        search_depth="basic",
        include_raw_content=False,
    )


def normalise_tavily_news(raw: dict, *, seed: str, days: int) -> list[dict]:
    """Pull Tavily news results; tag every item with source = tavily-news."""
    return [
        {
            "title": item.get("title"),
            "link": item.get("url"),
            "snippet": item.get("content"),
            "date": item.get("published_date"),
            "source": item.get("source") or item.get("url", ""),
            "score": item.get("score"),
            "from_seed": seed,
            "horizon_days": days,
            "_source": "tavily-news",
        }
        for item in raw.get("results", [])
    ]


def main_with_args(argv: list[str]) -> int:
    """Parse argv, fetch news from both providers, persist raws."""
    parser = argparse.ArgumentParser(
        description="Fetch news signals from Serper /news + Tavily search(topic=news).",
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--seeds", required=True, nargs="+",
                        help="Seed keywords (typically same set used for serp_fetch).")
    parser.add_argument("--gl", required=True, help="Locale country (e.g. us, uk).")
    parser.add_argument("--hl", required=True, help="Locale language (e.g. en, en-GB).")
    parser.add_argument("--days", type=int, default=7,
                        help="Look-back window in days (default 7).")
    parser.add_argument("--num", type=int, default=10,
                        help="Results per call per provider (default 10).")
    args = parser.parse_args(argv)

    if not args.run_dir.exists():
        log.error(f"--run-dir does not exist: {args.run_dir}")
        return 3

    try:
        load_env(require=("SERPER_API_KEY", "TAVILY_API_KEY"))
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    serper_key = os.environ["SERPER_API_KEY"]
    tavily_key = os.environ["TAVILY_API_KEY"]

    raw_dir = args.run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    serper_path = raw_dir / "serper-news.json"
    tavily_path = raw_dir / "tavily-news.json"

    serper_aggregated: dict = {
        "captured_at": _now_iso(),
        "horizon_days": args.days,
        "by_seed": [],
    }
    tavily_aggregated: dict = {
        "captured_at": _now_iso(),
        "horizon_days": args.days,
        "by_seed": [],
    }

    serper_total = 0
    tavily_total = 0
    serper_credits = 0
    tavily_credits = 0

    # --- Serper /news ---
    with build_client(timeout=30.0) as client:
        for seed in args.seeds:
            log.info(f"Serper /news: {seed!r} (qdr last {args.days}d, gl={args.gl})")
            try:
                raw = fetch_serper_news(
                    client, seed, gl=args.gl, hl=args.hl,
                    days=args.days, num=args.num, api_key=serper_key,
                )
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (401, 403):
                    log.error(f"Serper auth failure: {status}")
                    return 3
                log.warning(f"Serper /news failure for {seed!r}: {exc}")
                continue
            except httpx.HTTPError as exc:
                log.warning(f"Serper /news transient error for {seed!r}: {exc}")
                continue

            items = normalise_serper_news(raw, seed=seed, gl=args.gl, hl=args.hl)
            serper_aggregated["by_seed"].append({
                "seed": seed,
                "fetched_at": _now_iso(),
                "items": items,
                "raw": {"news": raw.get("news", [])[:args.num]},
            })
            serper_total += len(items)
            serper_credits += 1

    # --- Tavily news search ---
    tavily_client = TavilyClient(api_key=tavily_key)
    for seed in args.seeds:
        log.info(f"Tavily news: {seed!r} (last {args.days}d)")
        try:
            raw = fetch_tavily_news(
                tavily_client, seed,
                days=args.days, max_results=args.num,
            )
        except (InvalidAPIKeyError, MissingAPIKeyError) as exc:
            log.error(f"Tavily auth failure: {exc}")
            return 3
        except UsageLimitExceededError as exc:
            log.error(f"Tavily quota exceeded: {exc}")
            return 2
        except Exception as exc:
            log.warning(f"Tavily news failure for {seed!r}: {exc}")
            continue

        items = normalise_tavily_news(raw, seed=seed, days=args.days)
        tavily_aggregated["by_seed"].append({
            "seed": seed,
            "fetched_at": _now_iso(),
            "items": items,
        })
        tavily_total += len(items)
        # Tavily basic search costs 1 credit
        tavily_credits += 1

    serper_path.write_text(json.dumps(serper_aggregated, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    tavily_path.write_text(json.dumps(tavily_aggregated, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    log.info(f"Wrote {serper_path}")
    log.info(f"Wrote {tavily_path}")

    print(json.dumps({
        "raw_paths": {
            "serper_news": str(serper_path),
            "tavily_news": str(tavily_path),
        },
        "seed_count": len(args.seeds),
        "serper_news_count": serper_total,
        "tavily_news_count": tavily_total,
        "serper_credits_used": serper_credits,
        "tavily_credits_used": tavily_credits,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv[1:]))
