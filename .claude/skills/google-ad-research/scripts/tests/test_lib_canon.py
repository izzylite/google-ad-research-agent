"""
RED stubs for lib/canon.py — canonicalise() lemmatized + token-sorted hashing.

Tests go GREEN in Phase 2 Plan A (Wave 1) when lib/canon.py is implemented.
"""
import pytest

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from lib.canon import canonicalise  # noqa: F401
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True

pytestmark = pytest.mark.skipif(MODULE_MISSING, reason="lib/canon.py not yet implemented")


def test_grocery_variants_merge():
    """'grocery delivery', 'groceries delivery', 'grocery deliveries' all produce the same lemma hash."""
    raise NotImplementedError


def test_question_keywords_no_sort():
    """Question-style keywords ('what is same day delivery') preserve word order, not token-sorted."""
    raise NotImplementedError


def test_empty_raises():
    """canonicalise('') raises ValueError."""
    raise NotImplementedError


def test_token_sort_produces_stable_hash():
    """'delivery grocery uk' and 'grocery uk delivery' produce the same canonical hash."""
    raise NotImplementedError
