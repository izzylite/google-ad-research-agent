# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "inflect>=7.5",
# ]
# ///
"""merge_signals.py — raw/*.json → keywords.json (canonicalised + sourced).

CLI:
    uv run merge_signals.py --run-dir <abs>

Stdout (exactly one JSON line):
    {"keywords_count": N, "source_diversity_avg": float, "variants_merged": N}

Exit codes:
    0  ok
    3  fatal (IO / run_dir not found / no readable raw files)

Source taxonomy (locked — all 6 must be handled):
    "serper-organic"    from serper.json  by_seed[].organic[].title
    "serper-paa"        from serper.json  by_seed[].peopleAlsoAsk[].question
    "serper-related"    from serper.json  by_seed[].relatedSearches[].query
    "serper-ads"        from serper.json  by_seed[].ads[].title
    "tavily-extract"    from tavily-<domain>.json results[].raw_content (first phrase)
    "websearch-baseline" from websearch-baseline.json extracted_keywords[].keyword

Output row shape (keywords.json):
    {
        "canonical": str,       # shortest surface form in lemma_hash group
        "lemma_hash": str,      # sha256[:16] of sorted singularised tokens
        "variants": [str, ...], # sorted list of all observed surface forms
        "signal_count": int,    # len(sources)
        "source_diversity": int,# len({s["source"] for s in sources})
        "sources": [            # one entry per keyword occurrence
            {
                "source": str,
                "snippet"?: str,
                "url"?: str,
                "from_seed"?: str,
                "competitor_domain"?: str,
                "from_query"?: str,
                "captured_at"?: str,
            },
            ...
        ]
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator

# Make sibling lib/ importable when invoked via `uv run path/to/merge_signals.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.canon import canonicalise  # noqa: E402

# US state ambiguity — when brief location names a state, drop keywords
# containing other state's tokens. Prevents "Lake Worth, FL" → Texas drift.
US_STATE_TOKENS = {
    "al", "alabama", "ak", "alaska", "az", "arizona", "ar", "arkansas",
    "ca", "california", "co", "colorado", "ct", "connecticut",
    "de", "delaware", "fl", "florida", "ga", "georgia", "hi", "hawaii",
    "id", "idaho", "il", "illinois", "in", "indiana", "ia", "iowa",
    "ks", "kansas", "ky", "kentucky", "la", "louisiana", "me", "maine",
    "md", "maryland", "ma", "massachusetts", "mi", "michigan",
    "mn", "minnesota", "ms", "mississippi", "mo", "missouri",
    "mt", "montana", "ne", "nebraska", "nv", "nevada",
    "nh", "new hampshire", "nj", "new jersey", "nm", "new mexico",
    "ny", "new york", "nc", "north carolina", "nd", "north dakota",
    "oh", "ohio", "ok", "oklahoma", "or", "oregon",
    "pa", "pennsylvania", "ri", "rhode island", "sc", "south carolina",
    "sd", "south dakota", "tn", "tennessee", "tx", "texas",
    "ut", "utah", "vt", "vermont", "va", "virginia", "wa", "washington",
    "wv", "west virginia", "wi", "wisconsin", "wy", "wyoming",
}

# Common place-name disambiguation hints — cities that exist in multiple
# states. Maps city → set of states where the city is well-known. When a
# brief mentions "Lake Worth, FL", the merge filter rejects keywords whose
# only US-state token is one OTHER than FL.
AMBIGUOUS_CITIES = {
    "lake worth": {"fl", "florida", "tx", "texas"},
    "springfield": {"il", "ma", "mo", "or"},
    "kansas city": {"ks", "mo"},
    "portland": {"or", "me"},
    "columbus": {"oh", "ga"},
    "rochester": {"ny", "mn"},
    "richmond": {"va", "ca"},
    "memphis": {"tn", "ny"},
    "fort worth": {"tx"},
    "dallas": {"tx"},
}
from lib.log import configure_logger  # noqa: E402

log = configure_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_KEYWORD_WORDS = 7
VALID_SOURCES = frozenset({
    "serper-organic",
    "serper-paa",
    "serper-related",
    "serper-ads",
    "tavily-extract",
    "websearch-baseline",
})

_PUNCT_STRIP = re.compile(r"[^\w\s]")


# ---------------------------------------------------------------------------
# Reader functions — each yields (keyword_text, attribution_dict)
# ---------------------------------------------------------------------------

def read_serper(path: Path) -> Iterator[tuple[str, dict]]:
    """Read raw/serper.json and yield (keyword_text, attribution_dict) for each signal.

    Handles:
        by_seed[].organic     → title as keyword,  source="serper-organic"
        by_seed[].peopleAlsoAsk → question text,  source="serper-paa"
        by_seed[].relatedSearches → query text,   source="serper-related"
        by_seed[].ads         → title as keyword,  source="serper-ads"
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(f"Could not read {path}: {exc}")
        return

    for seed_block in data.get("by_seed", []):
        seed = seed_block.get("seed", "")

        # organic — keyword text = title
        for item in seed_block.get("organic", []):
            text = item.get("title") or ""
            if text.strip():
                attr = {
                    "source": "serper-organic",
                    "snippet": item.get("snippet"),
                    "url": item.get("link"),
                    "from_seed": seed,
                }
                yield text.strip(), attr

        # peopleAlsoAsk — keyword text = question
        for item in seed_block.get("peopleAlsoAsk", []):
            text = item.get("question") or ""
            if text.strip():
                attr = {
                    "source": "serper-paa",
                    "snippet": item.get("snippet"),
                    "url": item.get("link"),
                    "from_seed": seed,
                }
                yield text.strip(), attr

        # relatedSearches — keyword text = query
        for item in seed_block.get("relatedSearches", []):
            text = item.get("query") or ""
            if text.strip():
                attr = {
                    "source": "serper-related",
                    "from_query": text.strip(),
                    "from_seed": seed,
                }
                yield text.strip(), attr

        # ads — keyword text = title
        for item in seed_block.get("ads", []):
            text = item.get("title") or ""
            if text.strip():
                attr = {
                    "source": "serper-ads",
                    "snippet": item.get("snippet"),
                    "url": item.get("link"),
                    "from_seed": seed,
                }
                yield text.strip(), attr


def _extract_first_phrase(raw_content: str) -> str:
    """Extract a short keyword phrase from Tavily raw_content.

    Strategy (v1 — intentionally simple):
        1. Take the first sentence (split on '. ' or first 100 chars).
        2. Strip punctuation.
        3. Take the first MAX_KEYWORD_WORDS words.
    Phase 3 will apply intent classification; Phase 2 just surfaces the text.
    """
    if not raw_content:
        return ""
    # First sentence — split on sentence-ending punctuation
    sentence = re.split(r"[.!?]\s", raw_content.strip())[0]
    # Strip non-word characters (keep spaces)
    cleaned = _PUNCT_STRIP.sub(" ", sentence)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    tokens = cleaned.split()[:MAX_KEYWORD_WORDS]
    return " ".join(tokens)


def read_tavily(path: Path) -> Iterator[tuple[str, dict]]:
    """Read raw/tavily-<domain>.json and yield (keyword_text, attribution_dict).

    Skips failed_results.
    Extracts a short phrase from results[].raw_content.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(f"Could not read {path}: {exc}")
        return

    domain = data.get("domain", "")
    for result in data.get("results", []):
        url = result.get("url", "")
        raw_content = result.get("raw_content", "")
        phrase = _extract_first_phrase(raw_content)
        if phrase.strip():
            attr = {
                "source": "tavily-extract",
                "competitor_domain": domain,
                "url": url,
                "snippet_excerpt": phrase,
            }
            yield phrase.strip(), attr


def read_websearch(path: Path) -> Iterator[tuple[str, dict]]:
    """Read raw/websearch-baseline.json and yield (keyword_text, attribution_dict)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(f"Could not read {path}: {exc}")
        return

    for item in data.get("extracted_keywords", []):
        text = item.get("keyword") or ""
        if text.strip():
            attr = {
                "source": "websearch-baseline",
                "snippet": item.get("snippet"),
            }
            yield text.strip(), attr


# ---------------------------------------------------------------------------
# Core merge logic
# ---------------------------------------------------------------------------

def _build_state_filter(brief_text: str) -> set[str]:
    """Detect target US state(s) in brief.md and return states to KEEP.

    Returns empty set when brief has no detectable US state — no filtering
    applied. Returns {"fl", "florida"} for a brief mentioning Lake Worth, FL.

    Used downstream to drop keywords containing OTHER state tokens.
    """
    if not brief_text:
        return set()
    matched = set()
    # 2-letter codes — require UPPERCASE in original brief to avoid false
    # positives on common words ("mi" = miles, "or" = or, "in" = in,
    # "ok" = ok, "hi" = hi, "ma" = ma, etc).
    for token in US_STATE_TOKENS:
        if len(token) == 2:
            if re.search(rf"\b{token.upper()}\b", brief_text):
                matched.add(token)
        else:
            if token in brief_text.lower():
                matched.add(token)
    # Coalesce — if both "fl" and "florida" matched, keep both
    return matched


def _keyword_drifts_geo(text: str, allowed_states: set[str]) -> bool:
    """Return True when the keyword references a US state NOT in allowed_states.

    Used to drop keywords like "accident clinic dallas" when brief targets FL.
    """
    if not allowed_states or not text:
        return False
    lower_tokens = re.findall(r"\b[a-z]+\b", text.lower())
    multi_word = " ".join(lower_tokens)

    # Check 2-letter codes
    found_states = {t for t in lower_tokens if t in US_STATE_TOKENS and len(t) == 2}
    # Check multi-word state names
    for full in {s for s in US_STATE_TOKENS if len(s) > 2}:
        if full in multi_word:
            found_states.add(full)

    if not found_states:
        return False

    # Drift if NONE of the found states are allowed
    return found_states.isdisjoint(allowed_states)


def merge_raw_files(raw_dir: Path,
                    *, allowed_states: set[str] | None = None) -> dict[str, dict]:
    """Read all raw/*.json files and merge signals into a dict keyed by lemma_hash.

    Args:
        raw_dir: directory containing serper.json, tavily-*.json, websearch-baseline.json.
        allowed_states: when non-empty, drop keywords containing US state
            tokens not in this set (geo-drift filter).

    Returns:
        {lemma_hash: {"canonical": str, "lemma_hash": str, "variants": set, "sources": list}}
    """
    groups: dict[str, dict] = {}
    allowed_states = allowed_states or set()

    def _add(text: str, attr: dict) -> None:
        """Canonicalise text and add attribution to the appropriate group."""
        # Drop keywords containing Unicode replacement chars (mojibake from
        # mis-decoded API responses). Such keywords are unusable as Google Ads
        # match terms anyway.
        if text and "�" in text:
            return

        # Drop keywords whose only US-state reference is wrong-geo
        if _keyword_drifts_geo(text, allowed_states):
            return

        try:
            canonical_form, lemma_hash = canonicalise(text)
        except ValueError:
            return  # skip empty or un-parseable keywords

        # Drop keywords longer than MAX_KEYWORD_WORDS words (Pitfall 6 filter)
        if len(canonical_form.split()) > MAX_KEYWORD_WORDS:
            return

        if lemma_hash not in groups:
            groups[lemma_hash] = {
                "lemma_hash": lemma_hash,
                "variants": set(),
                "sources": [],
            }
        groups[lemma_hash]["variants"].add(canonical_form)
        groups[lemma_hash]["sources"].append(attr)

    # --- serper.json ---
    serper_path = raw_dir / "serper.json"
    if serper_path.exists():
        for text, attr in read_serper(serper_path):
            _add(text, attr)
    else:
        log.debug(f"No serper.json in {raw_dir}")

    # --- tavily-*.json ---
    for tavily_path in sorted(raw_dir.glob("tavily-*.json")):
        for text, attr in read_tavily(tavily_path):
            _add(text, attr)

    # --- websearch-baseline.json (optional) ---
    websearch_path = raw_dir / "websearch-baseline.json"
    if websearch_path.exists():
        for text, attr in read_websearch(websearch_path):
            _add(text, attr)

    return groups


def build_keywords_json(groups: dict[str, dict]) -> list[dict]:
    """Convert merge groups into sorted keyword rows ready for keywords.json.

    For each group:
      - canonical = shortest surface form (min by len)
      - variants = sorted list of all observed surface forms
      - signal_count = len(sources)
      - source_diversity = len({s["source"] for s in sources})

    Rows sorted by source_diversity desc, then signal_count desc.
    """
    rows = []
    for group in groups.values():
        variants_list = sorted(group["variants"])
        canonical = min(group["variants"], key=len)
        sources = group["sources"]
        signal_count = len(sources)
        source_diversity = len({s["source"] for s in sources})

        rows.append({
            "canonical": canonical,
            "lemma_hash": group["lemma_hash"],
            "variants": variants_list,
            "signal_count": signal_count,
            "source_diversity": source_diversity,
            "sources": sources,
        })

    rows.sort(key=lambda r: (-r["source_diversity"], -r["signal_count"]))
    return rows


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

def main_with_args(argv: list[str]) -> int:
    """Parse argv, merge raw files, write keywords.json. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Merge raw/*.json signal files → keywords.json with sources array.",
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="Absolute path to the sealed run folder.",
    )
    args = parser.parse_args(argv)

    run_dir: Path = args.run_dir
    if not run_dir.exists():
        log.error(f"--run-dir does not exist: {run_dir}")
        return 3

    raw_dir = run_dir / "raw"
    if not raw_dir.exists():
        log.error(f"raw/ subdirectory not found in {run_dir}")
        return 3

    # Detect target US state(s) from brief.md to filter wrong-geo drift.
    brief_path = run_dir / "brief.md"
    allowed_states: set[str] = set()
    if brief_path.exists():
        try:
            allowed_states = _build_state_filter(brief_path.read_text(encoding="utf-8"))
        except OSError:
            pass
    if allowed_states:
        log.info(f"Geo-drift filter active: keep states {sorted(allowed_states)}")

    groups = merge_raw_files(raw_dir, allowed_states=allowed_states)
    if not groups:
        log.warning("No keywords extracted — keywords.json will be empty")

    keywords = build_keywords_json(groups)

    out_path = run_dir / "keywords.json"
    out_path.write_text(json.dumps(keywords, indent=2), encoding="utf-8")
    log.info(f"Wrote {out_path} ({len(keywords)} keywords)")

    # Compute summary stats
    variants_merged = sum(1 for kw in keywords if len(kw["variants"]) > 1)
    diversity_avg = (
        sum(kw["source_diversity"] for kw in keywords) / len(keywords)
        if keywords
        else 0.0
    )

    print(json.dumps({
        "keywords_count": len(keywords),
        "source_diversity_avg": round(diversity_avg, 3),
        "variants_merged": variants_merged,
    }))
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
