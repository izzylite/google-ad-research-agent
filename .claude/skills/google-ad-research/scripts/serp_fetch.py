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

Stdout:
    {"raw_path": "<abs>", "seed_count": 3, "organic_count": 28, "paa_count": 12,
     "related_count": 22, "ads_count": 4, "credits_used": 3}

Stderr: progress per seed.
Exit codes: 0 ok, 2 retryable upstream (429 after retries / 5xx after retries),
            3 fatal (auth / IO / config).
"""
from __future__ import annotations

# Stub — implementation pending (GREEN phase)


def fetch_seed(client, seed: str, *, gl: str, hl: str, num: int = 20, api_key: str) -> dict:
    raise NotImplementedError


def normalise_response(raw: dict, *, seed: str, gl: str, hl: str) -> dict:
    raise NotImplementedError


def main_with_args(argv: list[str]) -> int:
    raise NotImplementedError


def main() -> int:
    import sys
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
