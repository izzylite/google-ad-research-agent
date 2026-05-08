"""lib/canon.py — close-variant detection via lemma + token-sort hashing.

Algorithm:
    1. Lowercase + strip punctuation (keep hyphens).
    2. Tokenize on whitespace.
    3. Drop empty tokens; preserve question-keyword order if first token is a question word.
    4. For non-question keywords:
         - Singularise each noun via inflect.singular_noun (returns False if already singular).
         - Sort tokens alphabetically.
    5. Join + sha256 first 16 hex chars = lemma_hash.

    Question keywords (start with how/what/why/is/are/can/who/where/when/do/does):
         - Preserve word order; lowercase + singularise but do NOT sort.
         - Reason: "how to deliver groceries" != "groceries delivery how".

Returns (canonical_form, lemma_hash). canonical_form is the lowercased + punctuation-stripped
input; merge_signals.py picks the *shortest* surface form within a hash group as the display form.
"""
from __future__ import annotations

import hashlib
import re

import inflect

_INF = inflect.engine()
_QUESTION_PREFIXES = {"how", "what", "why", "is", "are", "can", "who", "where", "when", "do", "does"}
_PUNCT = re.compile(r"[^\w\s-]")  # keep hyphens; strip everything else


def _singularise(token: str) -> str:
    sing = _INF.singular_noun(token)
    return sing if sing else token


def canonicalise(keyword: str) -> tuple[str, str]:
    """Return (canonical_form, lemma_hash). Empty input raises ValueError."""
    if not keyword or not keyword.strip():
        raise ValueError("empty keyword")
    norm = _PUNCT.sub(" ", keyword.lower()).strip()
    norm = re.sub(r"\s+", " ", norm)
    tokens = norm.split()
    if not tokens:
        raise ValueError(f"keyword {keyword!r} produced no tokens after normalisation")

    is_question = tokens[0] in _QUESTION_PREFIXES
    lemmas = [_singularise(t) for t in tokens]

    if is_question:
        hash_input = " ".join(lemmas)  # preserve order
    else:
        hash_input = " ".join(sorted(lemmas))

    digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]
    return norm, digest
