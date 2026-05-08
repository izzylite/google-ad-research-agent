"""RED test stubs for validate_clusters.py — Wave 0.

All tests skip when validate_clusters.py does not exist.
Tests become GREEN in Wave 1 when validate_clusters.py is implemented.

Requirements covered: CLST-01, CLST-02, CLST-03.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import pytest

# RED import — validate_clusters.py does not exist until Wave 1.
try:
    import validate_clusters  # type: ignore
    VC_MISSING = False
except ImportError:
    validate_clusters = None  # type: ignore
    VC_MISSING = True

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_ranked_index() -> dict[str, str]:
    """Build ranked_index {keyword: intent} from ranked_phase3.json."""
    rows = json.loads((FIXTURES_DIR / "ranked_phase3.json").read_text())
    return {row["keyword"]: row["intent"] for row in rows}


# ---------------------------------------------------------------------------
# CLST-01: Intent purity
# ---------------------------------------------------------------------------


def test_pure_intent_passes():
    """Pure-intent clusters produce no mixed_intent violations."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    data = json.loads((FIXTURES_DIR / "clusters_valid.json").read_text())
    clusters = data["clusters"]
    ranked_index = _load_ranked_index()
    hard, _warn = validate_clusters.check_clusters(clusters, ranked_index)
    mixed = [v for v in hard if v["type"] == "mixed_intent"]
    assert mixed == [], f"Expected no mixed_intent violations, got: {mixed}"


def test_mixed_intent_exit3():
    """Cluster containing both transactional and commercial keywords triggers mixed_intent."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    data = json.loads((FIXTURES_DIR / "clusters_mixed_intent.json").read_text())
    clusters = data["clusters"]
    ranked_index = _load_ranked_index()
    hard, _warn = validate_clusters.check_clusters(clusters, ranked_index)
    assert any(v["type"] == "mixed_intent" for v in hard), (
        f"Expected mixed_intent violation, hard violations were: {hard}"
    )
    assert len(hard) >= 1


# ---------------------------------------------------------------------------
# CLST-02: Cluster size bounds
# ---------------------------------------------------------------------------


def test_target_size_valid():
    """Cluster with 7 keywords in target range produces no size violations."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    ranked_index = _load_ranked_index()
    # Add 3 inline transactional keywords to reach 7 total
    ranked_index["grocery home delivery uk"] = "transactional"
    ranked_index["weekly grocery delivery service"] = "transactional"
    ranked_index["next day grocery delivery"] = "transactional"
    clusters = [
        {
            "name": "fresh_produce_delivery_transactional",
            "intent": "transactional",
            "keywords": [
                {"keyword": "order groceries uk", "score": 325},
                {"keyword": "get groceries delivered today", "score": 310},
                {"keyword": "same day grocery delivery", "score": 290},
                {"keyword": "grocery delivery near me", "score": 275},
                {"keyword": "grocery home delivery uk", "score": 200},
                {"keyword": "weekly grocery delivery service", "score": 190},
                {"keyword": "next day grocery delivery", "score": 180},
            ],
        }
    ]
    hard, warn = validate_clusters.check_clusters(clusters, ranked_index)
    assert hard == [], f"Expected no hard violations, got: {hard}"
    undersize_types = [w["type"] for w in warn if "undersize" in w["type"]]
    assert undersize_types == [], f"Expected no undersize warnings, got: {undersize_types}"


def test_undersize_warns():
    """Cluster with 2 keywords produces an undersize warning and no hard violations."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    ranked_index = {
        "order groceries uk": "transactional",
        "get groceries delivered today": "transactional",
    }
    clusters = [
        {
            "name": "tiny_delivery_transactional",
            "intent": "transactional",
            "keywords": [
                {"keyword": "order groceries uk", "score": 325},
                {"keyword": "get groceries delivered today", "score": 310},
            ],
        }
    ]
    hard, warn = validate_clusters.check_clusters(clusters, ranked_index)
    assert hard == [], f"Expected no hard violations, got: {hard}"
    assert any(w["type"] == "undersize" for w in warn), (
        f"Expected undersize warning, warnings were: {warn}"
    )


def test_oversize_exit3():
    """Cluster with 26 keywords triggers oversize hard violation."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    data = json.loads((FIXTURES_DIR / "clusters_oversize.json").read_text())
    clusters = data["clusters"]
    # Build ranked_index that includes ALL 26 keywords as transactional
    # so only oversize fires (not unknown_keyword)
    ranked_index = _load_ranked_index()
    for i in range(5, 27):
        ranked_index[f"filler keyword {i:02d}"] = "transactional"
    hard, _warn = validate_clusters.check_clusters(clusters, ranked_index)
    assert any(v["type"] == "oversize" for v in hard), (
        f"Expected oversize violation, hard violations were: {hard}"
    )


# ---------------------------------------------------------------------------
# CLST-02 / CLST-03: Cluster naming
# ---------------------------------------------------------------------------


def test_valid_name():
    """Cluster with valid {theme_slug}_{intent} name produces no bad_name violation."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    ranked_index = {
        "order groceries uk": "transactional",
        "get groceries delivered today": "transactional",
        "same day grocery delivery": "transactional",
        "grocery delivery near me": "transactional",
        "best grocery delivery uk": "transactional",
    }
    clusters = [
        {
            "name": "same_day_delivery_transactional",
            "intent": "transactional",
            "keywords": [
                {"keyword": "order groceries uk", "score": 325},
                {"keyword": "get groceries delivered today", "score": 310},
                {"keyword": "same day grocery delivery", "score": 290},
                {"keyword": "grocery delivery near me", "score": 275},
                {"keyword": "best grocery delivery uk", "score": 220},
            ],
        }
    ]
    hard, _warn = validate_clusters.check_clusters(clusters, ranked_index)
    bad_name_violations = [v for v in hard if v["type"] == "bad_name"]
    assert bad_name_violations == [], (
        f"Expected no bad_name violations, got: {bad_name_violations}"
    )


def test_bad_name_numeric():
    """Cluster named 'cluster_3_informational' triggers bad_name hard violation."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    ranked_index = {
        "how does grocery delivery work": "informational",
        "grocery delivery explained": "informational",
        "what is grocery delivery": "informational",
        "grocery delivery options uk": "informational",
        "grocery delivery services review": "informational",
    }
    clusters = [
        {
            "name": "cluster_3_informational",
            "intent": "informational",
            "keywords": [
                {"keyword": "how does grocery delivery work", "score": 150},
                {"keyword": "grocery delivery explained", "score": 140},
                {"keyword": "what is grocery delivery", "score": 130},
                {"keyword": "grocery delivery options uk", "score": 120},
                {"keyword": "grocery delivery services review", "score": 110},
            ],
        }
    ]
    hard, _warn = validate_clusters.check_clusters(clusters, ranked_index)
    assert any(v["type"] == "bad_name" for v in hard), (
        f"Expected bad_name violation, hard violations were: {hard}"
    )


# ---------------------------------------------------------------------------
# CLST-03: Duplicate keyword across clusters
# ---------------------------------------------------------------------------


def test_duplicate_keyword_exit3():
    """Same keyword appearing in two clusters triggers duplicate_keyword hard violation."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    ranked_index = {
        "order groceries uk": "transactional",
        "get groceries delivered today": "transactional",
        "same day grocery delivery": "transactional",
        "grocery delivery near me": "transactional",
        "best grocery delivery uk": "commercial",
        "grocery delivery comparison": "commercial",
        "ocado vs tesco delivery": "commercial",
    }
    clusters = [
        {
            "name": "same_day_delivery_transactional",
            "intent": "transactional",
            "keywords": [
                {"keyword": "order groceries uk", "score": 325},
                {"keyword": "get groceries delivered today", "score": 310},
                {"keyword": "same day grocery delivery", "score": 290},
                {"keyword": "grocery delivery near me", "score": 275},
            ],
        },
        {
            "name": "grocery_brand_comparison_commercial",
            "intent": "commercial",
            "keywords": [
                {"keyword": "order groceries uk", "score": 325},  # duplicate!
                {"keyword": "best grocery delivery uk", "score": 220},
                {"keyword": "grocery delivery comparison", "score": 195},
                {"keyword": "ocado vs tesco delivery", "score": 180},
            ],
        },
    ]
    hard, _warn = validate_clusters.check_clusters(clusters, ranked_index)
    assert any(v["type"] == "duplicate_keyword" for v in hard), (
        f"Expected duplicate_keyword violation, hard violations were: {hard}"
    )


# ---------------------------------------------------------------------------
# CLST-03: Orphan keywords
# ---------------------------------------------------------------------------


def test_orphans_warn():
    """clusters.json with orphans triggers orphan warning or check_clusters exposes the surface."""
    if VC_MISSING:
        pytest.skip("validate_clusters not yet implemented")
    # Wave 1: validate_clusters must expose orphan checking
    # Exact call TBD based on implementation surface
    assert hasattr(validate_clusters, "check_clusters"), "check_clusters must be importable"
