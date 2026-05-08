"""
Tests for lib/canon.py — canonicalise() lemmatized + token-sorted hashing.

Tests verify:
- Plural variants merge to the same lemma_hash
- Question keywords preserve word order (different hash from sorted variant)
- Empty/whitespace-only input raises ValueError
- Token order does not affect lemma_hash for non-question keywords
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
    _, h1 = canonicalise("grocery delivery")
    _, h2 = canonicalise("groceries delivery")
    _, h3 = canonicalise("grocery deliveries")
    assert h1 == h2 == h3, (
        f"Expected all variants to share the same lemma_hash, got: {h1!r}, {h2!r}, {h3!r}"
    )


def test_question_keywords_no_sort():
    """Question-style keywords preserve word order, not token-sorted."""
    # "how to find grocery delivery" — question prefix "how" means tokens are NOT sorted
    _, h_question = canonicalise("how to find grocery delivery")
    # The sorted version of those same words — should produce a different hash
    _, h_sorted = canonicalise("grocery delivery how find")
    assert h_question != h_sorted, (
        "Question keyword should preserve word order, producing a different hash from sorted tokens"
    )


def test_empty_raises():
    """canonicalise('') and canonicalise('   ') both raise ValueError."""
    with pytest.raises(ValueError):
        canonicalise("")
    with pytest.raises(ValueError):
        canonicalise("   ")


def test_token_sort_produces_stable_hash():
    """'delivery grocery' and 'grocery delivery' produce the same canonical hash (tokens sorted)."""
    _, h1 = canonicalise("delivery grocery")
    _, h2 = canonicalise("grocery delivery")
    assert h1 == h2, (
        f"Non-question keywords should produce the same hash regardless of input order, got: {h1!r}, {h2!r}"
    )
