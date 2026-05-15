"""RED test stubs for rank_keywords.py — Wave 0.

All tests skip when rank_keywords.py does not exist (MODULE_MISSING pattern).
Tests become GREEN in Wave 1 when rank_keywords.py is implemented.

Requirements covered: RANK-01, RANK-02, RANK-03, RANK-04.
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

# RED import — rank_keywords.py does not exist until Wave 1.
try:
    import rank_keywords  # type: ignore
    RK_MISSING = False
except ImportError:
    rank_keywords = None  # type: ignore
    RK_MISSING = True

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_keywords() -> list[dict]:
    return json.loads((FIXTURES_DIR / "keywords_phase2.json").read_text())


def _load_intent_labels() -> list[dict]:
    return json.loads((FIXTURES_DIR / "intent_labels.json").read_text())


# ---------------------------------------------------------------------------
# RANK-02: Composite scoring formula
# ---------------------------------------------------------------------------


def test_compute_score_formula():
    """compute_score(4, 'transactional', 5) == 435."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    # score = source_diversity * 100 + intent_weight + signal_count
    # transactional weight = 30  →  4*100 + 30 + 5 = 435
    assert rank_keywords.compute_score(4, "transactional", 5) == 435


def test_source_diversity_dominates_signal_count():
    """score(4, 'informational', 1) > score(1, 'transactional', 99)."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    high_diversity = rank_keywords.compute_score(4, "informational", 1)
    low_diversity = rank_keywords.compute_score(1, "transactional", 99)
    assert high_diversity > low_diversity


def test_intent_weight_ordering():
    """Within same diversity tier: transactional > commercial > informational."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    diversity = 2
    sig = 5
    t_score = rank_keywords.compute_score(diversity, "transactional", sig)
    c_score = rank_keywords.compute_score(diversity, "commercial", sig)
    i_score = rank_keywords.compute_score(diversity, "informational", sig)
    assert t_score > c_score > i_score


def test_sort_tiebreak():
    """Tie on score → higher signal_count wins; tie on both → alphabetical."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    # Two keywords with same source_diversity and intent → score tie; higher signal_count wins
    kws = [
        {"canonical": "z keyword", "lemma_hash": "hash_z", "signal_count": 3, "source_diversity": 2,
         "sources": [{"source": "serper-organic"}, {"source": "websearch-baseline"}]},
        {"canonical": "a keyword", "lemma_hash": "hash_a", "signal_count": 5, "source_diversity": 2,
         "sources": [{"source": "serper-organic"}, {"source": "websearch-baseline"}]},
        {"canonical": "b keyword", "lemma_hash": "hash_b", "signal_count": 5, "source_diversity": 2,
         "sources": [{"source": "serper-organic"}, {"source": "websearch-baseline"}]},
    ]
    labels_list = [
        {"canonical": "z keyword", "lemma_hash": "hash_z", "intent": "commercial", "match_type": "phrase"},
        {"canonical": "a keyword", "lemma_hash": "hash_a", "intent": "commercial", "match_type": "phrase"},
        {"canonical": "b keyword", "lemma_hash": "hash_b", "intent": "commercial", "match_type": "phrase"},
    ]
    labels = rank_keywords.validate_labels(labels_list)
    result = rank_keywords.build_ranked(kws, labels)
    # "a keyword" and "b keyword" both have signal_count=5, score tie → alphabetical
    assert result[0]["signal_count"] == 5
    assert result[0]["keyword"] == "a keyword"
    assert result[1]["keyword"] == "b keyword"
    # "z keyword" has signal_count=3, same score tier → comes last
    assert result[2]["keyword"] == "z keyword"


# ---------------------------------------------------------------------------
# RANK-01: validate_labels — rejects invalid entries
# ---------------------------------------------------------------------------


def test_validate_labels_rejects_invalid_intent():
    """validate_labels raises ValueError on intent='unknown'."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    labels = [{"canonical": "bad keyword", "lemma_hash": "badhash1",
               "intent": "unknown", "match_type": "phrase"}]
    with pytest.raises(ValueError):
        rank_keywords.validate_labels(labels)


def test_validate_labels_rejects_invalid_match_type():
    """validate_labels raises ValueError on match_type='unknown'."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    labels = [{"canonical": "bad keyword", "lemma_hash": "badhash2",
               "intent": "commercial", "match_type": "unknown"}]
    with pytest.raises(ValueError):
        rank_keywords.validate_labels(labels)


# ---------------------------------------------------------------------------
# RANK-02: build_ranked — missing label exits 3
# ---------------------------------------------------------------------------


def test_missing_label_exits_3():
    """build_ranked raises ValueError when a keyword has no matching label."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    kws = [{"canonical": "unlabeled keyword", "lemma_hash": "no_match_hash",
             "signal_count": 2, "source_diversity": 1,
             "sources": [{"source": "serper-organic"}]}]
    labels = {}  # empty — no matching entry
    with pytest.raises(ValueError):
        rank_keywords.build_ranked(kws, labels)


# ---------------------------------------------------------------------------
# RANK-03: match_type assignment
# ---------------------------------------------------------------------------


def test_match_type_exact_transactional():
    """transactional + source_diversity >= 3 → match_type == 'exact'."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    keywords = _load_keywords()
    intent_labels = _load_intent_labels()
    labels = rank_keywords.validate_labels(intent_labels)
    # "order groceries uk": transactional, diversity=4 → exact
    result = rank_keywords.build_ranked(keywords, labels)
    row = next(r for r in result if r["keyword"] == "order groceries uk")
    assert row["match_type"] == "exact"


def test_match_type_exact_navigational():
    """navigational + source_diversity >= 3 → match_type == 'exact'."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    # Fabricated inline: navigational keyword with diversity >= 3
    kws = [
        {"canonical": "ocado login", "lemma_hash": "nav3_hash", "signal_count": 2,
         "source_diversity": 3,
         "sources": [{"source": "s1"}, {"source": "s2"}, {"source": "s3"}]}
    ]
    labels_list = [
        {"canonical": "ocado login", "lemma_hash": "nav3_hash",
         "intent": "navigational", "match_type": "exact"}
    ]
    labels = rank_keywords.validate_labels(labels_list)
    result = rank_keywords.build_ranked(kws, labels)
    assert result[0]["match_type"] == "exact"


def test_match_type_phrase_default():
    """commercial and informational → match_type == 'phrase'."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    keywords = _load_keywords()
    intent_labels = _load_intent_labels()
    labels = rank_keywords.validate_labels(intent_labels)
    result = rank_keywords.build_ranked(keywords, labels)
    commercial_rows = [r for r in result if r["intent"] == "commercial"]
    informational_rows = [r for r in result if r["intent"] == "informational"]
    for row in commercial_rows + informational_rows:
        assert row["match_type"] == "phrase", (
            f"Expected phrase for {row['intent']} keyword {row['keyword']!r}, "
            f"got {row['match_type']!r}"
        )


# ---------------------------------------------------------------------------
# RANK-03: broad never assigned
# ---------------------------------------------------------------------------


def test_no_broad_in_output():
    """No row in build_ranked output has match_type == 'broad'."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    keywords = _load_keywords()
    intent_labels = _load_intent_labels()
    labels = rank_keywords.validate_labels(intent_labels)
    result = rank_keywords.build_ranked(keywords, labels)
    broad_rows = [r for r in result if r["match_type"] == "broad"]
    assert broad_rows == [], f"Unexpected broad match rows: {broad_rows}"


# ---------------------------------------------------------------------------
# RANK-04: Output schema
# ---------------------------------------------------------------------------

CANONICAL_KEYS = {"keyword", "intent", "match_type", "theme", "signal_count",
                  "source_diversity", "sources", "score"}


def test_output_schema_columns():
    """Every row has exactly the 8 canonical keys."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    keywords = _load_keywords()
    intent_labels = _load_intent_labels()
    labels = rank_keywords.validate_labels(intent_labels)
    result = rank_keywords.build_ranked(keywords, labels)
    for row in result:
        assert set(row.keys()) == CANONICAL_KEYS, (
            f"Row has wrong keys: {set(row.keys())} expected {CANONICAL_KEYS}"
        )


def test_no_volume_field_name():
    """'volume' not in any row key."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    keywords = _load_keywords()
    intent_labels = _load_intent_labels()
    labels = rank_keywords.validate_labels(intent_labels)
    result = rank_keywords.build_ranked(keywords, labels)
    for row in result:
        for key in row.keys():
            assert "volume" not in key.lower(), (
                f"Field name {key!r} contains 'volume' — use 'signal_count'"
            )


def test_theme_empty_string():
    """theme == '' for all rows (Phase 4 fills it)."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    keywords = _load_keywords()
    intent_labels = _load_intent_labels()
    labels = rank_keywords.validate_labels(intent_labels)
    result = rank_keywords.build_ranked(keywords, labels)
    for row in result:
        assert row["theme"] == "", (
            f"Expected empty theme for {row['keyword']!r}, got {row['theme']!r}"
        )


def test_sources_compact_form():
    """sources field is list of strings (not dicts)."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    keywords = _load_keywords()
    intent_labels = _load_intent_labels()
    labels = rank_keywords.validate_labels(intent_labels)
    result = rank_keywords.build_ranked(keywords, labels)
    for row in result:
        assert isinstance(row["sources"], list), (
            f"sources is not a list for {row['keyword']!r}"
        )
        for src in row["sources"]:
            assert isinstance(src, str), (
                f"sources entry {src!r} is not a string for {row['keyword']!r} "
                f"— expected compact string form, not dict"
            )


# ---------------------------------------------------------------------------
# RANK-01: Deterministic output
# ---------------------------------------------------------------------------


def test_deterministic_output():
    """Same inputs → identical ranked list on two calls."""
    if RK_MISSING:
        pytest.skip("rank_keywords not yet implemented")
    keywords = _load_keywords()
    intent_labels = _load_intent_labels()
    labels = rank_keywords.validate_labels(intent_labels)
    result_1 = rank_keywords.build_ranked(keywords, labels)
    result_2 = rank_keywords.build_ranked(keywords, labels)
    assert result_1 == result_2
