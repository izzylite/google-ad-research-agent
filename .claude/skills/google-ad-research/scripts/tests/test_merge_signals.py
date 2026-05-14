"""
Tests for merge_signals.py — raw/*.json → keywords.json (canonicalised + sourced).

Covers:
  - sources array present on every row
  - close variants merge via lemma_hash
  - all 6 source types from taxonomy handled
  - source_diversity computed correctly
  - no keyword row lacks sources
  - end-to-end with fixture files
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make scripts/ importable so tests can do `import merge_signals`.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import merge_signals  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="merge_signals.py not yet implemented")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _skip_unless_city_filter() -> None:
    """Phase 11 GEO-03 guard — Wave 1 plan 11-01 adds the city filter."""
    if MODULE_MISSING:
        pytest.skip("merge_signals module incomplete")
    if not hasattr(merge_signals, "_keyword_drifts_city"):
        pytest.skip("merge_signals city filter — Wave 1 plan 11-01")


# ---------------------------------------------------------------------------
# Helpers to write minimal raw fixture files into tmp_run_dir/raw/
# ---------------------------------------------------------------------------

def _write_serper(raw_dir: Path, by_seed: list[dict]) -> None:
    """Write a serper.json with the given by_seed list."""
    (raw_dir / "serper.json").write_text(
        json.dumps({"by_seed": by_seed}), encoding="utf-8"
    )


def _write_tavily(raw_dir: Path, domain: str, results: list[dict]) -> None:
    """Write a tavily-<domain>.json file."""
    slug = domain.replace(".", "-")
    (raw_dir / f"tavily-{slug}.json").write_text(
        json.dumps({
            "domain": domain,
            "source": "tavily-extract",
            "results": [
                {**r, "source": "tavily-extract", "competitor_domain": domain}
                for r in results
            ],
            "failed_results": [],
        }),
        encoding="utf-8",
    )


def _write_websearch(raw_dir: Path, keywords: list[str]) -> None:
    """Write a websearch-baseline.json with extracted_keywords list."""
    (raw_dir / "websearch-baseline.json").write_text(
        json.dumps({
            "extracted_keywords": [
                {"keyword": kw, "source": "websearch-baseline"}
                for kw in keywords
            ]
        }),
        encoding="utf-8",
    )


def _read_keywords(run_dir: Path) -> list[dict]:
    """Load keywords.json from run_dir root."""
    out_path = run_dir / "keywords.json"
    assert out_path.exists(), f"keywords.json not found at {out_path}"
    return json.loads(out_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sources_array_per_keyword(tmp_run_dir):
    """Every keyword in keywords.json has a non-empty sources array."""
    raw_dir = tmp_run_dir / "raw"
    # One keyword from serper-organic, one from tavily
    _write_serper(raw_dir, [{
        "seed": "grocery delivery",
        "locale": {"gl": "uk", "hl": "en-GB"},
        "organic": [{"title": "Grocery Delivery UK", "link": "https://ex.com", "snippet": "Fast grocery delivery", "source": "serper-organic", "from_seed": "grocery delivery"}],
        "peopleAlsoAsk": [],
        "relatedSearches": [],
        "ads": [],
        "searchParameters": {},
    }])
    _write_tavily(raw_dir, "tesco.com", [{
        "url": "https://tesco.com/delivery",
        "raw_content": "Order groceries online for home delivery today.",
    }])

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    keywords = _read_keywords(tmp_run_dir)
    assert len(keywords) >= 1, "Should have at least 1 keyword"
    for kw in keywords:
        assert "sources" in kw, f"Missing 'sources' key on: {kw}"
        assert isinstance(kw["sources"], list), f"sources should be a list: {kw}"
        assert len(kw["sources"]) >= 1, f"sources must be non-empty: {kw}"


def test_close_variants_merge(tmp_run_dir):
    """Close variants ('grocery delivery', 'groceries delivery', 'grocery deliveries') merge to one canonical row."""
    raw_dir = tmp_run_dir / "raw"
    # Three variant forms — each from a different source type.
    # lib/canon.canonicalise() singularises nouns and sorts tokens, so all three
    # map to the same lemma_hash.  Use the exact variant strings as input text.
    _write_serper(raw_dir, [{
        "seed": "grocery delivery",
        "locale": {"gl": "uk", "hl": "en-GB"},
        "organic": [{"title": "grocery delivery", "link": "https://ex.com/1", "snippet": "shop online", "source": "serper-organic", "from_seed": "grocery delivery"}],
        "peopleAlsoAsk": [{"question": "groceries delivery", "snippet": "", "title": "", "link": "", "source": "serper-paa", "from_seed": "grocery delivery"}],
        "relatedSearches": [{"query": "grocery deliveries", "source": "serper-related", "from_seed": "grocery delivery"}],
        "ads": [],
        "searchParameters": {},
    }])
    # No tavily needed; websearch not written = optional
    # Avoid creating websearch-baseline.json so merge handles missing file gracefully

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    keywords = _read_keywords(tmp_run_dir)
    # All three surface forms should share the same lemma_hash → 1 merged row
    # Find the row(s) that contain "grocery delivery" / "groceries delivery" / "grocery deliveries"
    variant_set = {"grocery delivery", "groceries delivery", "grocery deliveries"}
    matching = [
        kw for kw in keywords
        if variant_set.intersection(set(kw.get("variants", [])))
    ]
    assert len(matching) == 1, (
        f"Expected 1 merged row for grocery delivery variants, got {len(matching)}.\n"
        f"keywords.json rows: {[k['canonical'] for k in keywords]}"
    )
    merged_row = matching[0]
    assert len(merged_row["variants"]) == 3, (
        f"Expected 3 variants in merged row, got {merged_row['variants']}"
    )


def test_six_source_taxonomy(tmp_run_dir):
    """All 6 source types produce entries in keywords.json and source_diversity == 6 for the keyword present in all."""
    raw_dir = tmp_run_dir / "raw"
    kw = "grocery delivery"

    _write_serper(raw_dir, [{
        "seed": "grocery delivery",
        "locale": {"gl": "uk", "hl": "en-GB"},
        "organic": [{"title": kw, "link": "https://ex.com/1", "snippet": "fast grocery delivery", "source": "serper-organic", "from_seed": kw}],
        "peopleAlsoAsk": [{"question": kw, "snippet": "", "title": kw, "link": "", "source": "serper-paa", "from_seed": kw}],
        "relatedSearches": [{"query": kw, "source": "serper-related", "from_seed": kw}],
        "ads": [{"title": kw, "link": "https://ex.com/ad", "snippet": "ad snippet", "displayUrl": "ex.com", "position": 1, "source": "serper-ads", "from_seed": kw}],
        "searchParameters": {},
    }])
    # Use raw_content that is short enough to produce exactly kw as the extracted phrase
    _write_tavily(raw_dir, "tesco.com", [{
        "url": "https://tesco.com/delivery",
        "raw_content": kw + ".",
    }])
    _write_websearch(raw_dir, [kw])

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    keywords = _read_keywords(tmp_run_dir)
    # Find the row for "grocery delivery"
    matches = [k for k in keywords if k["canonical"] == "grocery delivery" or "grocery delivery" in k.get("variants", [])]
    assert matches, "No row found for 'grocery delivery'"
    row = matches[0]

    all_source_strings = {s["source"] for s in row["sources"]}
    expected_taxonomy = {"serper-organic", "serper-paa", "serper-related", "serper-ads", "tavily-extract", "websearch-baseline"}
    assert expected_taxonomy == all_source_strings, (
        f"Expected all 6 source types, got: {all_source_strings}"
    )
    assert row["source_diversity"] == 6, (
        f"Expected source_diversity == 6, got {row['source_diversity']}"
    )


def test_source_diversity_count(tmp_run_dir):
    """source_diversity == len(set(s['source'] for s in sources)), not len(sources)."""
    raw_dir = tmp_run_dir / "raw"
    kw = "grocery delivery"

    # Two different source types — serper-organic and tavily-extract
    _write_serper(raw_dir, [{
        "seed": kw,
        "locale": {"gl": "uk", "hl": "en-GB"},
        "organic": [
            {"title": kw, "link": "https://ex.com/1", "snippet": "snippet 1", "source": "serper-organic", "from_seed": kw},
            {"title": kw + " fast", "link": "https://ex.com/2", "snippet": "snippet 2", "source": "serper-organic", "from_seed": kw},
        ],
        "peopleAlsoAsk": [],
        "relatedSearches": [],
        "ads": [],
        "searchParameters": {},
    }])
    # Use short raw_content that produces exactly kw as the extracted phrase
    _write_tavily(raw_dir, "tesco.com", [{
        "url": "https://tesco.com/delivery",
        "raw_content": kw + ".",
    }])

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    keywords = _read_keywords(tmp_run_dir)
    matches = [k for k in keywords if k["canonical"] == kw or kw in k.get("variants", [])]
    assert matches, f"No row found for '{kw}'"
    row = matches[0]

    computed_diversity = len({s["source"] for s in row["sources"]})
    assert row["source_diversity"] == computed_diversity, (
        f"source_diversity {row['source_diversity']} != computed {computed_diversity}"
    )
    # The two serper-organic entries count as 1 towards diversity, tavily as 1 → diversity == 2
    assert row["source_diversity"] == 2, (
        f"Expected source_diversity == 2 (serper-organic + tavily-extract), got {row['source_diversity']}"
    )


def test_every_keyword_has_sources(tmp_run_dir):
    """No keyword row in keywords.json has an empty or missing sources field."""
    raw_dir = tmp_run_dir / "raw"
    _write_serper(raw_dir, [
        {
            "seed": "grocery delivery",
            "locale": {"gl": "uk", "hl": "en-GB"},
            "organic": [
                {"title": "grocery delivery uk", "link": "https://ex.com/1", "snippet": "Get groceries delivered", "source": "serper-organic", "from_seed": "grocery delivery"},
                {"title": "online grocery shopping", "link": "https://ex.com/2", "snippet": "Shop online", "source": "serper-organic", "from_seed": "grocery delivery"},
            ],
            "peopleAlsoAsk": [
                {"question": "how to order groceries online", "snippet": "", "title": "", "link": "", "source": "serper-paa", "from_seed": "grocery delivery"},
            ],
            "relatedSearches": [
                {"query": "supermarket delivery uk", "source": "serper-related", "from_seed": "grocery delivery"},
            ],
            "ads": [],
            "searchParameters": {},
        }
    ])
    _write_websearch(raw_dir, ["grocery home delivery", "same day grocery delivery"])

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    keywords = _read_keywords(tmp_run_dir)
    assert len(keywords) >= 1
    for kw in keywords:
        sources = kw.get("sources")
        assert sources is not None, f"Missing 'sources' key: {kw['canonical']}"
        assert len(sources) >= 1, f"Empty sources on: {kw['canonical']}"


def test_end_to_end_with_fixtures(tmp_run_dir):
    """merge_signals produces a valid keywords.json from fixture-style raw/ inputs."""
    raw_dir = tmp_run_dir / "raw"

    # Adapt the serper_search_uk.json fixture to what serp_fetch.py produces (by_seed[] wrapper)
    raw_serper = json.loads((FIXTURES_DIR / "serper_search_uk.json").read_text())
    by_seed_entry = {
        "seed": "grocery delivery uk",
        "locale": {"gl": "uk", "hl": "en-GB"},
        "organic": [
            {**item, "source": "serper-organic", "from_seed": "grocery delivery uk"}
            for item in raw_serper.get("organic", [])
        ],
        "peopleAlsoAsk": [
            {**item, "source": "serper-paa", "from_seed": "grocery delivery uk"}
            for item in raw_serper.get("peopleAlsoAsk", [])
        ],
        "relatedSearches": [
            {**item, "source": "serper-related", "from_seed": "grocery delivery uk"}
            for item in raw_serper.get("relatedSearches", [])
        ],
        "ads": [
            {**item, "source": "serper-ads", "from_seed": "grocery delivery uk"}
            for item in raw_serper.get("ads", [])
        ],
        "searchParameters": raw_serper.get("searchParameters", {}),
    }
    (raw_dir / "serper.json").write_text(
        json.dumps({"by_seed": [by_seed_entry]}), encoding="utf-8"
    )

    # Adapt the tavily_extract_2urls.json fixture to what tavily_extract.py produces
    raw_tavily = json.loads((FIXTURES_DIR / "tavily_extract_2urls.json").read_text())
    adapted_tavily = {
        "domain": "tesco.com",
        "source": "tavily-extract",
        "results": [
            {**r, "source": "tavily-extract", "competitor_domain": "tesco.com"}
            for r in raw_tavily.get("results", [])
        ],
        "failed_results": raw_tavily.get("failed_results", []),
    }
    (raw_dir / "tavily-tesco-com.json").write_text(
        json.dumps(adapted_tavily), encoding="utf-8"
    )

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    out_path = tmp_run_dir / "keywords.json"
    assert out_path.exists(), "keywords.json not written to run_dir root"
    keywords = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(keywords) >= 1, "keywords.json should have at least 1 keyword"

    # Every row must have required fields
    required_fields = {"canonical", "lemma_hash", "variants", "signal_count", "source_diversity", "sources"}
    for kw in keywords:
        missing = required_fields - set(kw.keys())
        assert not missing, f"Row missing fields {missing}: {kw}"
        assert len(kw["sources"]) >= 1, f"Row has empty sources: {kw['canonical']}"


# ===========================================================================
# Phase 11 Wave 0 — GEO-03 integration RED stubs (per-function hasattr guards)
#
# Wave 1 plan 11-01 will add a --us-cities-path CLI flag to merge_signals.py
# defaulting to references/us-cities.json so tests can swap in a fixture file.
# ===========================================================================

def _stage_geo_run(tmp_run_dir: Path, brief_path: Path) -> None:
    """Drop a minimal serper.json + brief.md + us-cities-subset.json into run_dir."""
    raw_dir = tmp_run_dir / "raw"
    # Three serper organic hits, all FL location-flavoured.
    _write_serper(raw_dir, [{
        "seed": "accident doctor",
        "locale": {"gl": "us", "hl": "en-US"},
        "organic": [
            {"title": "lake worth chiropractor", "link": "https://ex.com/1",
             "snippet": "Lake Worth FL chiropractor", "source": "serper-organic",
             "from_seed": "accident doctor"},
            {"title": "boca raton dentist", "link": "https://ex.com/2",
             "snippet": "Boca Raton dental care", "source": "serper-organic",
             "from_seed": "accident doctor"},
            {"title": "tampa pain clinic", "link": "https://ex.com/3",
             "snippet": "Tampa pain management", "source": "serper-organic",
             "from_seed": "accident doctor"},
        ],
        "peopleAlsoAsk": [],
        "relatedSearches": [],
        "ads": [],
        "searchParameters": {"gl": "us", "hl": "en-US"},
    }])
    (tmp_run_dir / "brief.md").write_text(
        brief_path.read_text(encoding="utf-8"), encoding="utf-8",
    )


def test_city_filter_active(tmp_run_dir, monkeypatch):
    """GEO-03 integration: brief with geo_focus → Tampa-flavoured keyword dropped."""
    _skip_unless_city_filter()
    _stage_geo_run(tmp_run_dir, FIXTURES_DIR / "brief-with-geo-focus.md")
    # Wave 1: merge_signals.py grows --us-cities-path. Today: monkeypatch
    # the module-level constant so the fixture subset is used.
    if hasattr(merge_signals, "_US_CITIES_DATA_PATH"):
        monkeypatch.setattr(
            merge_signals, "_US_CITIES_DATA_PATH",
            FIXTURES_DIR / "us-cities-subset.json",
        )

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    keywords = _read_keywords(tmp_run_dir)
    canonicals = {kw["canonical"] for kw in keywords}
    variants = {v for kw in keywords for v in kw.get("variants", [])}
    all_surfaces = canonicals | variants
    # Tampa NOT in Palm Beach focus → dropped.
    assert not any("tampa" in s for s in all_surfaces), (
        f"tampa pain clinic should be dropped; surfaces: {all_surfaces}"
    )
    # Lake Worth IS in Palm Beach focus → kept.
    assert any("lake worth" in s for s in all_surfaces), (
        f"lake worth should be kept; surfaces: {all_surfaces}"
    )


def test_city_filter_inactive_when_geo_focus_empty(tmp_run_dir, monkeypatch):
    """GEO-03 backward compat: no geo_focus line → Tampa NOT dropped."""
    _skip_unless_city_filter()
    _stage_geo_run(tmp_run_dir, FIXTURES_DIR / "brief-no-geo-focus.md")
    if hasattr(merge_signals, "_US_CITIES_DATA_PATH"):
        monkeypatch.setattr(
            merge_signals, "_US_CITIES_DATA_PATH",
            FIXTURES_DIR / "us-cities-subset.json",
        )

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    keywords = _read_keywords(tmp_run_dir)
    all_surfaces = (
        {kw["canonical"] for kw in keywords}
        | {v for kw in keywords for v in kw.get("variants", [])}
    )
    # Empty geo_focus disables filter — Tampa must remain.
    assert any("tampa" in s for s in all_surfaces), (
        f"tampa pain clinic should NOT be dropped when geo_focus empty: {all_surfaces}"
    )


def test_city_filter_preserves_county_hierarchy(tmp_run_dir, monkeypatch):
    """GEO-03 Pitfall 5: Boca Raton (Palm Beach county) kept under Palm Beach focus."""
    _skip_unless_city_filter()
    _stage_geo_run(tmp_run_dir, FIXTURES_DIR / "brief-with-geo-focus.md")
    if hasattr(merge_signals, "_US_CITIES_DATA_PATH"):
        monkeypatch.setattr(
            merge_signals, "_US_CITIES_DATA_PATH",
            FIXTURES_DIR / "us-cities-subset.json",
        )

    merge_signals.main_with_args(["--run-dir", str(tmp_run_dir)])

    keywords = _read_keywords(tmp_run_dir)
    all_surfaces = (
        {kw["canonical"] for kw in keywords}
        | {v for kw in keywords for v in kw.get("variants", [])}
    )
    # Boca Raton's county IS Palm Beach → must survive the filter.
    assert any("boca raton" in s for s in all_surfaces), (
        f"boca raton dentist should be kept via county hierarchy: {all_surfaces}"
    )
