"""
RED stubs for merge_signals.py — raw/*.json → keywords.json (canonicalised + sourced).

Tests go GREEN in Phase 2 Plan D (Wave 3) when merge_signals.py is implemented.
"""
import pytest

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import merge_signals  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="merge_signals.py not yet implemented")


def test_sources_array_per_keyword(tmp_run_dir):
    """Every keyword in keywords.json has a non-empty sources array."""
    raise NotImplementedError


def test_close_variants_merge(tmp_run_dir):
    """Close variants ('grocery delivery', 'groceries delivery') merge to one canonical row."""
    raise NotImplementedError


def test_six_source_taxonomy(tmp_run_dir):
    """Source values in keywords.json are drawn only from the 6-value taxonomy."""
    raise NotImplementedError


def test_source_diversity_count(tmp_run_dir):
    """source_diversity field equals len(set(sources)) for each keyword row."""
    raise NotImplementedError


def test_every_keyword_has_sources(tmp_run_dir):
    """No keyword row in keywords.json has an empty or missing sources field."""
    raise NotImplementedError


def test_end_to_end_with_fixtures(tmp_run_dir):
    """merge_signals produces a valid keywords.json from fixture-style raw/ inputs."""
    raise NotImplementedError
