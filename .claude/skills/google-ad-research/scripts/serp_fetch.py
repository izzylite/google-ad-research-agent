# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx>=0.28",
#     "httpx-retries>=0.5",
#     "python-dotenv>=1.0",
# ]
# ///
"""serp_fetch.py — POST google.serper.dev/search per seed; persist raw/serper.json.

CLI:
    uv run serp_fetch.py --run-dir <abs path> --seeds "kw1" "kw2" "kw3" --gl uk --hl en-GB

Stdout (exactly one JSON line):
    {"raw_path": "<abs>", "seed_count": 3, "organic_count": 28, "paa_count": 12,
     "related_count": 22, "ads_count": 4, "credits_used": 3}

Stderr: human-readable progress per seed (via lib/log.configure_logger()).

Exit codes:
    0  ok
    2  retryable upstream (429 after retries / 5xx after retries)
    3  fatal (auth 401/403 / IO / config)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make sibling lib/ importable when invoked via `uv run path/to/serp_fetch.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402

from lib.config import load_env  # noqa: E402
from lib.http import build_client  # noqa: E402
from lib.log import configure_logger  # noqa: E402

log = configure_logger()
SERPER_URL = "https://google.serper.dev/search"


def fetch_seed(
    client: httpx.Client,
    seed: str,
    *,
    gl: str,
    hl: str,
    num: int = 20,
    location: str | None = None,
    api_key: str,
) -> dict:
    """One Serper call; returns parsed JSON. Raises httpx.HTTPStatusError after retries."""
    payload = {"q": seed, "gl": gl, "hl": hl, "num": num}
    if location:
        payload["location"] = location
    response = client.post(
        SERPER_URL,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json=payload,
    )
    response.raise_for_status()
    # Force UTF-8 decode regardless of Content-Type charset declaration
    # (Serper sometimes omits charset, which makes httpx fall back wrong and
    # produce mojibake on non-ASCII results).
    return json.loads(response.content.decode("utf-8", errors="replace"))


def normalise_response(raw: dict, *, seed: str, gl: str, hl: str) -> dict:
    """Pull out the four signal arrays with defensive .get() everywhere."""
    return {
        "seed": seed,
        "locale": {"gl": gl, "hl": hl},
        "organic": [
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "position": item.get("position"),
                "source": "serper-organic",
                "from_seed": seed,
            }
            for item in raw.get("organic", [])
        ],
        "peopleAlsoAsk": [
            {
                "question": item.get("question"),
                "snippet": item.get("snippet"),
                "title": item.get("title"),
                "link": item.get("link"),
                "source": "serper-paa",
                "from_seed": seed,
            }
            for item in raw.get("peopleAlsoAsk", [])
        ],
        "relatedSearches": [
            {
                "query": item.get("query"),
                "source": "serper-related",
                "from_seed": seed,
            }
            for item in raw.get("relatedSearches", [])
        ],
        "ads": [
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "displayUrl": item.get("displayUrl"),
                "position": item.get("position"),
                "source": "serper-ads",
                "from_seed": seed,
            }
            for item in raw.get("ads", [])
        ],
        # Verbatim echo of Serper's searchParameters — contains gl/hl/q for downstream
        # locale lint (Pitfall 4 mitigation: asserted in test_locale_persisted).
        "searchParameters": raw.get("searchParameters", {}),
    }


def main_with_args(argv: list[str]) -> int:
    """Parse argv, run Serper fetch, write raw/serper.json. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Fetch Serper SERP signals per seed keyword.",
    )
    parser.add_argument("--run-dir", required=True, type=Path,
                        help="Absolute path to the sealed run folder.")
    parser.add_argument("--seeds", required=True, nargs="+",
                        help="One or more seed keyword strings.")
    parser.add_argument("--gl", required=True,
                        help="Google locale country code (e.g. uk, us).")
    parser.add_argument("--hl", required=True,
                        help="Google locale language code (e.g. en-GB, en-US).")
    parser.add_argument("--num", type=int, default=20,
                        help="Results per Serper call (default 20).")
    parser.add_argument("--location", default=None,
                        help="Optional Serper location string for finer geo targeting "
                             "(e.g. 'Lake Worth, Florida, United States').")
    args = parser.parse_args(argv)

    # Validate run-dir up front (exit 3 — fatal IO/config error).
    if not args.run_dir.exists():
        log.error(f"--run-dir does not exist: {args.run_dir}")
        return 3

    # Load .env; require SERPER_API_KEY (exit 3 if missing).
    try:
        load_env(require=("SERPER_API_KEY",))
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    # Read key from env — never pass as CLI arg (Pitfall 9 / CLAUDE.md secret discipline).
    api_key = os.environ["SERPER_API_KEY"]

    raw_dir = args.run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    out_path = raw_dir / "serper.json"

    aggregated: dict = {"by_seed": []}

    with build_client(timeout=30.0) as client:
        for seed in args.seeds:
            log.info(f"Serper: {seed!r} (gl={args.gl}, hl={args.hl})")
            try:
                raw = fetch_seed(
                    client, seed,
                    gl=args.gl, hl=args.hl,
                    num=args.num, location=args.location, api_key=api_key,
                )
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (401, 403):
                    log.error(f"Serper auth failure: {status}")
                    return 3
                log.error(f"Serper retryable failure for {seed!r}: {exc}")
                return 2

            aggregated["by_seed"].append(
                normalise_response(raw, seed=seed, gl=args.gl, hl=args.hl)
            )

    out_path.write_text(json.dumps(aggregated, indent=2), encoding="utf-8")
    log.info(f"Wrote {out_path}")

    organic_total = sum(len(s["organic"]) for s in aggregated["by_seed"])
    paa_total = sum(len(s["peopleAlsoAsk"]) for s in aggregated["by_seed"])
    related_total = sum(len(s["relatedSearches"]) for s in aggregated["by_seed"])
    ads_total = sum(len(s["ads"]) for s in aggregated["by_seed"])

    print(json.dumps({
        "raw_path": str(out_path),
        "seed_count": len(args.seeds),
        "organic_count": organic_total,
        "paa_count": paa_total,
        "related_count": related_total,
        "ads_count": ads_total,
        "credits_used": len(args.seeds),  # 1 credit per /search call per Serper pricing
    }))
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
