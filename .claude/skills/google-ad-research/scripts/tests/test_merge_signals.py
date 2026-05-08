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
    # Three variant forms — each from a different source type
    _write_serper(raw_dir, [{
        "seed": "grocery delivery",
        "locale": {"gl": "uk", "hl": "en-GB"},
        "organic": [{"title": "grocery delivery", "link": "https://ex.com/1", "snippet": "shop online", "source": "serper-organic", "from_seed": "grocery delivery"}],
        "peopleAlsoAsk": [{"question": "groceries delivery near me?", "snippet": "", "title": "", "link": "", "source": "serper-paa", "from_seed": "grocery delivery"}],
        "relatedSearches": [{"query": "grocery deliveries uk", "source": "serper-related", "from_seed": "grocery delivery"}],
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
    _write_tavily(raw_dir, "tesco.com", [{
        "url": "https://tesco.com/delivery",
        "raw_content": kw + " available now at tesco online shop.",
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
    _write_tavily(raw_dir, "tesco.com", [{
        "url": "https://tesco.com/delivery",
        "raw_content": kw + " home delivery service.",
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
