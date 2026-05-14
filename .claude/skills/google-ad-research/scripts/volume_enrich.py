# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.28",
#     "httpx-retries>=0.5",
#     "python-dotenv>=1.0",
# ]
# ///
"""volume_enrich.py — Add Ahrefs volume + CPC + KD + parent_topic to ranked.json.

Reads:
    {run_dir}/ranked.json

Writes:
    {run_dir}/ranked-enriched.json  (ranked.json + 4 new columns per kw)
    {run_dir}/raw/ahrefs-overview.json  (raw responses)

Adds these keys per keyword:
    volume          (int, monthly searches; null if Ahrefs has no data)
    cpc_micros      (int, cost-per-click in micros = cents * 10000; null possible)
    difficulty      (int, 0-100 Keyword Difficulty; null possible)
    parent_topic    (str, Ahrefs-derived topic cluster name; null possible)

CLI:
    uv run volume_enrich.py --run-dir <abs> --country us [--batch-size 100]

Stdout (one JSON line):
    {"ranked_enriched_path": "...",
     "keywords_total": N,
     "keywords_enriched": N,
     "keywords_no_data": N,
     "ahrefs_calls": N}

Exit codes:
    0  ok
    2  retryable (Ahrefs rate limit / transient)
    3  fatal (auth, missing input, IO)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make sibling lib/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402

from lib.ahrefs_client import (  # noqa: E402
    build_client,
    chunk_keywords,
    fetch_overview,
    get_api_key,
)
from lib.config import load_env  # noqa: E402
from lib.log import configure_logger  # noqa: E402

log = configure_logger()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _country_from_locale(brief_text: str) -> str:
    """Best-effort country code from brief.md.

    Looks for explicit 'gl=us' style markers, then 2-letter state codes
    that imply US, then language codes. Defaults to 'us'.
    """
    if not brief_text:
        return "us"
    lower = brief_text.lower()
    # Explicit en-US / en-GB / es-US patterns
    if "en-gb" in lower or "uk" in lower.split():
        return "gb"
    if "en-ca" in lower or "canada" in lower:
        return "ca"
    if "en-au" in lower or "australia" in lower:
        return "au"
    # Default
    return "us"


def enrich_keywords(
    keywords: list[dict],
    *,
    country: str,
    api_key: str,
    batch_size: int = 100,
) -> tuple[list[dict], list[dict], int]:
    """Call Ahrefs and merge enrichment into each keyword row.

    Returns (enriched_rows, raw_responses, num_calls).
    """
    surface_forms = [k["keyword"] for k in keywords]
    # Build lookup by lowercased keyword so we can merge regardless of casing
    by_lower = {k["keyword"].lower(): k for k in keywords}

    raw_responses: list[dict] = []
    num_calls = 0
    with build_client() as client:
        for batch in chunk_keywords(surface_forms, size=batch_size):
            log.info(f"Ahrefs overview: {len(batch)} keywords (country={country})")
            try:
                resp = fetch_overview(
                    client, batch, country=country, api_key=api_key,
                )
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                log.error(f"Ahrefs HTTP {status}: {exc.response.text[:200]}")
                if status in (401, 403):
                    raise EnvironmentError(
                        f"Ahrefs auth failure: {status}. Check AHREFS_API_KEY."
                    )
                # Other status: surface as transient
                raise

            raw_responses.append({
                "fetched_at": _now_iso(),
                "country": country,
                "batch_size": len(batch),
                "response": resp,
            })
            num_calls += 1

            # Merge results back
            for row in resp.get("keywords", []):
                kw_text = (row.get("keyword") or "").lower()
                target = by_lower.get(kw_text)
                if not target:
                    continue
                # cpc returned in cents → convert to micros (cents * 10000)
                cpc_cents = row.get("cpc")
                target["volume"] = row.get("volume")
                target["cpc_micros"] = (
                    int(cpc_cents) * 10_000 if cpc_cents is not None else None
                )
                target["difficulty"] = row.get("difficulty")
                target["parent_topic"] = row.get("parent_topic")

    # Ensure every row has the enrichment keys (None when missing)
    for k in keywords:
        k.setdefault("volume", None)
        k.setdefault("cpc_micros", None)
        k.setdefault("difficulty", None)
        k.setdefault("parent_topic", None)

    return keywords, raw_responses, num_calls


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Enrich ranked.json with Ahrefs volume + CPC + KD + parent_topic.",
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument(
        "--country", default=None,
        help="2-letter Ahrefs country code (us, gb, ca, au, ...). "
             "Auto-detected from brief.md if omitted.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=100,
        help="Keywords per Ahrefs call (max 100 default).",
    )
    args = parser.parse_args(argv)

    run_dir: Path = args.run_dir
    if not run_dir.exists():
        log.error(f"--run-dir does not exist: {run_dir}")
        return 3

    ranked_path = run_dir / "ranked.json"
    if not ranked_path.exists():
        log.error(f"ranked.json not found: {ranked_path}")
        return 3

    try:
        load_env()
        api_key = get_api_key()
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    try:
        ranked = json.loads(ranked_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.error(f"Failed to load ranked.json: {exc}")
        return 3

    # Country: explicit > brief > default
    country = (args.country or "").lower().strip()
    if not country:
        brief_path = run_dir / "brief.md"
        brief_text = brief_path.read_text(encoding="utf-8") if brief_path.exists() else ""
        country = _country_from_locale(brief_text)
    log.info(f"Country: {country}")

    try:
        enriched, raw, calls = enrich_keywords(
            ranked, country=country, api_key=api_key,
            batch_size=args.batch_size,
        )
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3
    except httpx.HTTPStatusError:
        return 2

    # Persist
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / "ahrefs-overview.json").write_text(
        json.dumps({"country": country, "calls": raw}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    out_path = run_dir / "ranked-enriched.json"
    out_path.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    keywords_with_data = sum(1 for k in enriched if k.get("volume") is not None)

    print(json.dumps({
        "ranked_enriched_path": str(out_path),
        "keywords_total": len(enriched),
        "keywords_enriched": keywords_with_data,
        "keywords_no_data": len(enriched) - keywords_with_data,
        "ahrefs_calls": calls,
        "country": country,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv[1:]))
