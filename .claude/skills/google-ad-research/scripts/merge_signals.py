# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "inflect>=7.5",
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
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

Source taxonomy (5 sources):
    "serper-organic"    from serper.json  by_seed[].organic[].title
    "serper-paa"        from serper.json  by_seed[].peopleAlsoAsk[].question
    "serper-related"    from serper.json  by_seed[].relatedSearches[].query
    "serper-ads"        from serper.json  by_seed[].ads[].title
    "websearch-baseline" from websearch-baseline.json extracted_keywords[].keyword

NOTE: webfetch-landing is NOT a keyword source. Landing-page extraction is
a Phase 5 Step 19 sidecar (Claude WebFetch) and feeds the competitor section
of report.md only — it never enters the keyword pool (WFCH-04 contract).

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

# Phase 11 plan 11-01 — geographic city filter helpers consumed by merge.
# `_parse_optional_geo_focus` is the GEO-01 helper that lives in run_init.py.
from run_init import _parse_optional_geo_focus  # noqa: E402

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
# Source taxonomy: 5 sources. webfetch-landing NOT included — landing-page
# extraction is Phase 5 Step 19 only (WebFetch sidecar), not a keyword harvest
# source per WFCH-04 contract.
VALID_SOURCES = frozenset({
    "serper-organic",
    "serper-paa",
    "serper-related",
    "serper-ads",
    "websearch-baseline",
})

# ---------------------------------------------------------------------------
# Phase 11 plan 11-01 — city-level geo filter (GEO-03 / GEO-04)
# ---------------------------------------------------------------------------

# Path resolution: scripts/ → ../references/us-cities.json. Tests may
# monkeypatch this constant (or pass --us-cities-path) to swap in the fixture.
_US_CITIES_DATA_PATH: Path = (
    Path(__file__).resolve().parent.parent / "references" / "us-cities.json"
)

_COUNTY_SUFFIX_RE: re.Pattern[str] = re.compile(r"\s+county\s*$", re.IGNORECASE)

# State name → 2-letter USPS code, lowercase. Used by `_infer_state_code`.
_STATE_NAME_TO_CODE: dict[str, str] = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
    "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de",
    "district of columbia": "dc", "florida": "fl", "georgia": "ga", "hawaii": "hi",
    "idaho": "id", "illinois": "il", "indiana": "in", "iowa": "ia",
    "kansas": "ks", "kentucky": "ky", "louisiana": "la", "maine": "me",
    "maryland": "md", "massachusetts": "ma", "michigan": "mi", "minnesota": "mn",
    "mississippi": "ms", "missouri": "mo", "montana": "mt", "nebraska": "ne",
    "nevada": "nv", "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm",
    "new york": "ny", "north carolina": "nc", "north dakota": "nd", "ohio": "oh",
    "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa", "rhode island": "ri",
    "south carolina": "sc", "south dakota": "sd", "tennessee": "tn", "texas": "tx",
    "utah": "ut", "vermont": "vt", "virginia": "va", "washington": "wa",
    "west virginia": "wv", "wisconsin": "wi", "wyoming": "wy",
}
_STATE_CODES_2: frozenset[str] = frozenset(_STATE_NAME_TO_CODE.values())


def _load_us_cities(path: Path | None = None) -> dict[str, dict[str, str]]:
    """Load us-cities.json. Returns {state_code_lower: {city_lower: county_lower}}.

    Empty dict if file absent or unparseable — allows backward compat (no filter
    fires) and easy test injection.
    """
    p = path or _US_CITIES_DATA_PATH
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def _strip_county_suffix(name: str) -> str:
    """Normalize a geo_focus entry to match us-cities.json county values.

    'Palm Beach County' → 'palm beach'
    'Tarrant County'    → 'tarrant'
    'Lake Worth'        → 'lake worth' (no suffix to strip)
    """
    return _COUNTY_SUFFIX_RE.sub("", name.strip()).strip().lower()


def _build_city_filter(
    state_code: str,
    geo_focus: list[str],
    us_cities: dict[str, dict[str, str]],
) -> dict[str, set[str]]:
    """Return {'in': <cities in focus>, 'out': <cities not in focus>} for state.

    A city is 'in focus' if either the city name itself OR its county appears
    in geo_focus (case-insensitive; ' county' suffix stripped from geo_focus
    entries before lookup — Pitfall 5 hierarchy).

    Backward compat: empty geo_focus OR no cities for state → both sets empty
    (the filter is effectively inactive).
    """
    state_cities = us_cities.get(state_code.lower(), {}) if state_code else {}
    if not geo_focus or not state_cities:
        return {"in": set(), "out": set()}
    focus_norm = {_strip_county_suffix(g) for g in geo_focus if g and g.strip()}
    if not focus_norm:
        return {"in": set(), "out": set()}
    in_focus: set[str] = set()
    out_of_focus: set[str] = set()
    for city, county in state_cities.items():
        city_l = city.lower()
        county_l = (county or "").lower()
        if city_l in focus_norm or (county_l and county_l in focus_norm):
            in_focus.add(city_l)
        else:
            out_of_focus.add(city_l)
    return {"in": in_focus, "out": out_of_focus}


def _keyword_drifts_city(text: str, city_filter: dict[str, set[str]]) -> bool:
    """True iff `text` contains any out-of-focus city name (multi-word substring match).

    Empty city_filter['out'] → False (filter inactive, backward compat).
    Case-insensitive. Uses literal substring match because city names are
    multi-word (e.g., 'west palm beach', 'boca raton') and regex word-boundary
    matching would mis-handle multi-token cities.
    """
    out = city_filter.get("out") if city_filter else None
    if not out or not text:
        return False
    lower = text.lower()
    return any(c in lower for c in out)


def _infer_state_code(brief_text: str) -> str:
    """Best-effort: pick a 2-letter US state code from a brief markdown.

    Strategy:
      1. Match a full state name in brief_text (case-insensitive) — most specific.
      2. Fall back to a 2-letter uppercase code on a word boundary (`\bFL\b`).
    Returns "" when nothing matches.
    """
    if not brief_text:
        return ""
    lower = brief_text.lower()
    # Sort longest-first so "new york" wins over "new" or "york" partials.
    for name in sorted(_STATE_NAME_TO_CODE, key=len, reverse=True):
        if name in lower:
            return _STATE_NAME_TO_CODE[name]
    # Uppercase 2-letter fallback — case-sensitive on the ORIGINAL text to avoid
    # false positives on common lowercase words ("or", "in", "ok", "hi", "ma").
    for code in _STATE_CODES_2:
        if re.search(rf"\b{code.upper()}\b", brief_text):
            return code
    return ""


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

# ---------------------------------------------------------------------------
# Exclusions filter (EXCL-01) — service-line + audience exclusion enforcement
# ---------------------------------------------------------------------------
#
# Why this exists: the brief's `**Product:**` field carries "NOT chiropractor,
# NOT physical therapy" prose that the LLM clustering / negative-gen step
# reads but doesn't always honour — 2026-05-16 dogfood leaked 2 chiropractor
# keywords + 1 pediatric keyword into positives despite Product saying NOT
# chiropractor + Audience implying adult MVA. Operators were having to
# manually scrub positives.csv before Editor import.
#
# Solution: a deterministic substring-match drop at merge_signals (same
# layer as the geo-drift filter). Operator lists exclusion phrases in
# `**Exclusions:**` and ANY keyword whose normalised text contains any
# exclusion phrase is dropped from the pool BEFORE clustering / ranking /
# report generation. The same exclusions get fed to the negatives prompt
# (SKILL.md Step 21) as required-include Strong negatives — defense in
# depth at the campaign level.

_EXCLUSIONS_FIELD_RE: re.Pattern[str] = re.compile(
    r"^\s*-?\s*\*\*Exclusions:\*\*\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)


def _parse_exclusions(brief_text: str) -> list[str]:
    """Extract normalised exclusion phrases from `**Exclusions:**` in brief.md.

    Returns a list of lowercased, single-space-normalised phrases. Comma-
    separated; minimum 3 chars per phrase to avoid over-matching common short
    words. Returns [] when the field is absent or the value is blank
    (filter inactive, full backward compat with pre-EXCL-01 briefs).
    """
    if not brief_text:
        return []
    m = _EXCLUSIONS_FIELD_RE.search(brief_text)
    if not m:
        return []
    phrases: list[str] = []
    for chunk in m.group(1).split(","):
        norm = re.sub(r"\s+", " ", chunk.lower()).strip()
        # Strip punctuation that would prevent substring match against
        # keywords like "pain-management" vs operator's "pain management".
        norm = re.sub(r"[^\w\s]", " ", norm)
        norm = re.sub(r"\s+", " ", norm).strip()
        if norm and len(norm) >= 3:
            phrases.append(norm)
    return phrases


def _keyword_drifts_exclusions(text: str, exclusions: list[str]) -> bool:
    """True iff `text` contains any exclusion phrase as a normalised substring.

    Empty exclusions → False (filter inactive, backward compat).
    Case-insensitive. Substring match (not whole-word) so an exclusion
    "chiropract" catches "chiropractor", "chiropractic", "chiropractors";
    operator can use either the stem or the full word.
    """
    if not exclusions or not text:
        return False
    # Match the same normalisation pipeline used for the exclusions phrase
    # list so "pain-management" in a keyword is comparable to "pain
    # management" in the exclusions list.
    norm = re.sub(r"[^\w\s]", " ", text.lower())
    norm = re.sub(r"\s+", " ", norm).strip()
    return any(p in norm for p in exclusions)


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
                    *, allowed_states: set[str] | None = None,
                    city_filter: dict[str, set[str]] | None = None,
                    exclusions: list[str] | None = None,
                    dropped_counter: dict[str, int] | None = None,
                    ) -> dict[str, dict]:
    """Read all raw/*.json files and merge signals into a dict keyed by lemma_hash.

    Args:
        raw_dir: directory containing serper.json + websearch-baseline.json.
            (Landing-page content is a Phase 5 WebFetch sidecar — never feeds
            the keyword pool.)
        allowed_states: when non-empty, drop keywords containing US state
            tokens not in this set (geo-drift filter).
        city_filter: optional {'in': set, 'out': set} from `_build_city_filter`.
            When 'out' is non-empty, keywords containing any of those city
            names are dropped (GEO-03 Pitfall 5 hierarchy applied via the
            filter construction, not here).
        exclusions: optional list of normalised phrases from brief's
            `**Exclusions:**` field (EXCL-01). Keywords whose normalised text
            contains any phrase as a substring are dropped — used to
            deterministically enforce service-line + audience exclusions that
            the Product / Audience prose alone can't guarantee.
        dropped_counter: optional dict the function increments to record
            keyword drops per filter ('city', 'state', 'exclusion'); enables
            telemetry in stdout JSON.

    Returns:
        {lemma_hash: {"canonical": str, "lemma_hash": str, "variants": set, "sources": list}}
    """
    groups: dict[str, dict] = {}
    allowed_states = allowed_states or set()
    city_filter = city_filter or {"in": set(), "out": set()}
    exclusions = exclusions or []
    if dropped_counter is None:
        dropped_counter = {"city": 0, "state": 0, "exclusion": 0}
    else:
        dropped_counter.setdefault("city", 0)
        dropped_counter.setdefault("state", 0)
        dropped_counter.setdefault("exclusion", 0)

    def _add(text: str, attr: dict) -> None:
        """Canonicalise text and add attribution to the appropriate group."""
        # Drop keywords containing Unicode replacement chars (mojibake from
        # mis-decoded API responses). Such keywords are unusable as Google Ads
        # match terms anyway.
        if text and "�" in text:
            return

        # Drop keywords whose only US-state reference is wrong-geo
        if _keyword_drifts_geo(text, allowed_states):
            dropped_counter["state"] += 1
            return

        # Drop keywords mentioning a city outside the brief's geo_focus
        # (city filter inactive when geo_focus empty — backward compat).
        if _keyword_drifts_city(text, city_filter):
            dropped_counter["city"] += 1
            return

        # EXCL-01: drop keywords matching any operator-defined exclusion
        # phrase. Backward compat — exclusions empty → no-op. Runs AFTER
        # geo filters so the telemetry distinguishes drop reasons clearly
        # (operator can audit each filter's effectiveness independently).
        if _keyword_drifts_exclusions(text, exclusions):
            dropped_counter["exclusion"] += 1
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
    parser.add_argument(
        "--us-cities-path",
        type=Path,
        default=None,
        help="Override path to us-cities.json (tests inject fixture subset). "
             "Defaults to references/us-cities.json relative to the script. GEO-04.",
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

    # Read brief.md once — drives BOTH the state-level filter AND the
    # Phase 11 city-level filter (GEO-03).
    brief_path = run_dir / "brief.md"
    brief_text = ""
    if brief_path.exists():
        try:
            brief_text = brief_path.read_text(encoding="utf-8")
        except OSError:
            brief_text = ""

    # Existing state-level filter (pre-Phase-11 behaviour preserved).
    allowed_states = _build_state_filter(brief_text)
    if allowed_states:
        log.info(f"Geo-drift filter active: keep states {sorted(allowed_states)}")

    # Phase 11 — city-level filter wiring (GEO-01 → GEO-03 → GEO-04).
    geo_focus = _parse_optional_geo_focus(brief_text)
    state_code = _infer_state_code(brief_text)
    # Tests may monkeypatch _US_CITIES_DATA_PATH; honour --us-cities-path first.
    us_cities_path = args.us_cities_path or _US_CITIES_DATA_PATH
    us_cities = _load_us_cities(us_cities_path)
    city_filter = _build_city_filter(state_code, geo_focus, us_cities)
    if geo_focus and city_filter["out"]:
        log.info(
            f"City filter active: state={state_code!r} "
            f"in-focus={len(city_filter['in'])} "
            f"out-of-focus={len(city_filter['out'])} cities"
        )
    elif geo_focus:
        log.info(
            f"City filter inactive (no cities matched): state={state_code!r} "
            f"geo_focus={geo_focus}"
        )

    # EXCL-01: read `**Exclusions:**` from brief. Empty list → filter inactive
    # (backward compat — pre-EXCL-01 briefs continue to work unchanged).
    exclusions = _parse_exclusions(brief_text)
    if exclusions:
        log.info(f"Exclusions filter active: {len(exclusions)} phrases — {exclusions}")

    dropped_counter: dict[str, int] = {"city": 0, "state": 0, "exclusion": 0}
    groups = merge_raw_files(
        raw_dir,
        allowed_states=allowed_states,
        city_filter=city_filter,
        exclusions=exclusions,
        dropped_counter=dropped_counter,
    )
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
        # GEO-* telemetry (empty when filter inactive — backward compat for
        # downstream Phase 3 consumers that don't read these keys).
        "geo_focus": geo_focus,
        "state_code": state_code,
        "cities_in_focus": sorted(city_filter["in"]),
        "cities_filtered_out": sorted(city_filter["out"]),
        "keywords_dropped_city_filter": dropped_counter["city"],
        "keywords_dropped_state_filter": dropped_counter["state"],
        # EXCL-01 telemetry — operator audits per-run effectiveness of the
        # exclusions list, decides whether to add/remove phrases for next run.
        "exclusions": exclusions,
        "keywords_dropped_exclusion_filter": dropped_counter["exclusion"],
    }))
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
