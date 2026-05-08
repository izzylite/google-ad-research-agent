# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "tavily-python>=0.7.24",
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
"""tavily_extract.py — TavilyClient.extract() per competitor URL list; persist raw/tavily-<domain>.json.

CLI:
    uv run tavily_extract.py --run-dir <abs> \\
        --competitor "tesco.com:https://tesco.com,https://tesco.com/groceries/..." \\
        --competitor "ocado.com:https://ocado.com,..."

Caps: --max-competitors 5 (default), --max-urls-per-competitor 5 (default), extract_depth='basic'.

Stdout:
    {"competitor_count": 3, "urls_attempted": 12, "urls_succeeded": 11, "urls_failed": 1,
     "credits_used": 3}

Exit codes: 0 ok, 2 UsageLimitExceededError, 3 fatal (auth, IO).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make sibling lib/ importable when invoked via `uv run path/to/tavily_extract.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.config import load_env  # noqa: E402
from lib.log import configure_logger  # noqa: E402

from slugify import slugify  # noqa: E402
from tavily import TavilyClient  # noqa: E402
from tavily import (  # noqa: E402
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
    BadRequestError,
)

log = configure_logger()


def parse_competitor_arg(arg: str) -> tuple[str, list[str]]:
    """Parse 'tesco.com:https://a,https://b' -> ('tesco.com', ['https://a','https://b'])."""
    domain, urls_csv = arg.split(":", 1)
    return domain.strip(), [u.strip() for u in urls_csv.split(",") if u.strip()]


def main_with_args(argv: list[str]) -> int:
    """Parse argv, run Tavily extract per competitor, write raw/tavily-<domain>.json. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Tavily extract per competitor URL list → raw/tavily-<domain>.json.",
    )
    parser.add_argument("--run-dir", required=True, type=Path,
                        help="Absolute path to the sealed run folder.")
    parser.add_argument("--competitor", action="append", default=[],
                        help="Format: 'domain:url1,url2,...' — repeat per competitor.")
    parser.add_argument("--max-competitors", type=int, default=5,
                        help="Hard cap on number of competitors to process (default 5).")
    parser.add_argument("--max-urls-per-competitor", type=int, default=5,
                        help="Hard cap on URLs per competitor (default 5).")
    # argv may be full sys.argv (script name at index 0) or args-only list.
    # If the first element doesn't start with '-' it is the script name — skip it.
    parsed_argv = argv[1:] if (argv and not argv[0].startswith("-")) else argv
    args = parser.parse_args(parsed_argv)

    if not args.competitor:
        log.error("At least one --competitor required")
        return 2

    competitors = [parse_competitor_arg(c) for c in args.competitor]
    if len(competitors) > args.max_competitors:
        log.warning(
            f"Trimming competitors {len(competitors)} -> {args.max_competitors} (Pitfall 8)"
        )
        competitors = competitors[: args.max_competitors]

    if not args.run_dir.exists():
        log.error(f"--run-dir does not exist: {args.run_dir}")
        return 3

    try:
        load_env(require=("TAVILY_API_KEY",))
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    raw_dir = args.run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

    total_attempted = total_succeeded = total_failed = 0
    for domain, urls in competitors:
        urls = urls[: args.max_urls_per_competitor]
        if not urls:
            continue

        log.info(f"Tavily extract: {domain} ({len(urls)} URLs, basic depth)")
        try:
            response = client.extract(
                urls=urls,
                extract_depth="basic",  # explicit per Pitfall 8 — never omit
                format="markdown",
                include_usage=True,
            )
        except (InvalidAPIKeyError, MissingAPIKeyError) as exc:
            log.error(f"Tavily auth failure: {exc}")
            return 3
        except UsageLimitExceededError as exc:
            log.error(f"Tavily quota exceeded: {exc}")
            return 2
        except BadRequestError as exc:
            log.error(f"Tavily bad request for {domain}: {exc}")
            # Skip this competitor; continue with others
            continue

        out_path = raw_dir / f"tavily-{slugify(domain)}.json"
        # Annotate every result with source + competitor_domain so merge_signals can fan out
        annotated = {
            "domain": domain,
            "source": "tavily-extract",
            "results": [
                {**r, "source": "tavily-extract", "competitor_domain": domain}
                for r in response.get("results", [])
            ],
            "failed_results": response.get("failed_results", []),
            "response_time": response.get("response_time"),
            "request_id": response.get("request_id"),
            "usage": response.get("usage", {}),
        }
        out_path.write_text(json.dumps(annotated, indent=2), encoding="utf-8")
        log.info(f"Wrote {out_path}")

        total_attempted += len(urls)
        total_succeeded += len(annotated["results"])
        total_failed += len(annotated["failed_results"])

    print(json.dumps({
        "competitor_count": len(competitors),
        "urls_attempted": total_attempted,
        "urls_succeeded": total_succeeded,
        "urls_failed": total_failed,
        "credits_used": -(-total_succeeded // 5),  # ceil(succeeded / 5) — basic = 1 credit / 5 URLs
    }))
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
