# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""rank_keywords.py — keywords.json + intent-labels.json → ranked.json (pure math).

CLI:
    uv run rank_keywords.py --run-dir <abs>

Stdout (exactly one JSON line):
    {"ranked_count": N, "avg_score": float, "intent_distribution": {"transactional": N, ...}}

Exit codes:
    0  ok
    3  fatal (missing input / join failure / unlabeled keywords / validation error)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTENT_WEIGHTS: dict[str, int] = {
    "transactional":  30,
    "commercial":     20,
    "navigational":   10,
    "informational":   5,
}

VALID_INTENTS: frozenset[str] = frozenset(INTENT_WEIGHTS.keys())
VALID_MATCH_TYPES: frozenset[str] = frozenset({"phrase", "exact", "broad"})


# ---------------------------------------------------------------------------
# Core scoring
# ---------------------------------------------------------------------------

def compute_score(source_diversity: int, intent: str, signal_count: int) -> int:
    """Compute composite keyword score.

    Formula: source_diversity * 100 + intent_weight + signal_count

    Args:
        source_diversity: Count of distinct signal sources (1-6).
        intent: One of informational / commercial / transactional / navigational.
        signal_count: Number of source-fragment occurrences.

    Returns:
        Integer composite score. source_diversity is the dominant signal.
    """
    weight = INTENT_WEIGHTS.get(intent, 5)
    return source_diversity * 100 + weight + signal_count


# ---------------------------------------------------------------------------
# Label validation
# ---------------------------------------------------------------------------

def validate_labels(labels_list: list[dict]) -> dict[str, dict]:
    """Parse and validate intent-labels.json entries.

    Args:
        labels_list: Parsed JSON list from intent-labels.json.

    Returns:
        Dict keyed by lemma_hash → label row.

    Raises:
        ValueError: If any entry has an invalid intent or match_type value.
    """
    out: dict[str, dict] = {}
    for row in labels_list:
        if row.get("intent") not in VALID_INTENTS:
            raise ValueError(
                f"Invalid intent {row.get('intent')!r} for {row.get('canonical')!r}. "
                f"Must be one of: {sorted(VALID_INTENTS)}"
            )
        if row.get("match_type") not in VALID_MATCH_TYPES:
            raise ValueError(
                f"Invalid match_type {row.get('match_type')!r} for {row.get('canonical')!r}. "
                f"Must be one of: {sorted(VALID_MATCH_TYPES)}"
            )
        out[row["lemma_hash"]] = row
    return out


# ---------------------------------------------------------------------------
# Ranked output builder
# ---------------------------------------------------------------------------

def build_ranked(keywords: list[dict], labels: dict[str, dict]) -> list[dict]:
    """Join keywords with intent labels, compute scores, and sort.

    Args:
        keywords: Rows from keywords.json (canonical, lemma_hash, signal_count,
                  source_diversity, sources[]).
        labels: Dict keyed by lemma_hash from validate_labels().

    Returns:
        Ranked rows sorted by (score desc, signal_count desc, keyword asc).
        Each row has exactly the 8 canonical columns:
        keyword, intent, match_type, theme, signal_count, source_diversity,
        sources, score.

    Raises:
        ValueError: If any keyword has no matching intent label.
    """
    rows: list[dict] = []
    for kw in keywords:
        lh = kw["lemma_hash"]
        label = labels.get(lh)
        if label is None:
            raise ValueError(
                f"No intent label for lemma_hash={lh!r} canonical={kw['canonical']!r}. "
                "Run intent labeling (Step 11) before rank_keywords.py."
            )
        intent = label["intent"]
        match_type = label["match_type"]
        score = compute_score(kw["source_diversity"], intent, kw["signal_count"])
        # Compact sources: distinct source strings only, sorted for determinism
        distinct_sources = sorted({s["source"] for s in kw["sources"]})
        rows.append({
            "keyword":          kw["canonical"],
            "intent":           intent,
            "match_type":       match_type,
            "theme":            "",
            "signal_count":     kw["signal_count"],
            "source_diversity": kw["source_diversity"],
            "sources":          distinct_sources,
            "score":            score,
        })
    rows.sort(key=lambda r: (-r["score"], -r["signal_count"], r["keyword"]))
    return rows


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse args, load inputs, write ranked.json, print summary. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Join keywords.json + intent-labels.json → ranked.json.",
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="Absolute path to the sealed run folder.",
    )
    args = parser.parse_args()
    run_dir: Path = args.run_dir

    try:
        keywords_path = run_dir / "keywords.json"
        labels_path = run_dir / "intent-labels.json"

        if not run_dir.exists():
            print(f"ERROR: --run-dir does not exist: {run_dir}", file=sys.stderr)
            return 3

        if not keywords_path.exists():
            print(f"ERROR: keywords.json not found in {run_dir}", file=sys.stderr)
            return 3

        if not labels_path.exists():
            print(f"ERROR: intent-labels.json not found in {run_dir}", file=sys.stderr)
            return 3

        keywords: list[dict] = json.loads(keywords_path.read_text(encoding="utf-8"))
        labels_list: list[dict] = json.loads(labels_path.read_text(encoding="utf-8"))

        labels = validate_labels(labels_list)
        ranked = build_ranked(keywords, labels)

        out_path = run_dir / "ranked.json"
        out_path.write_text(json.dumps(ranked, indent=2), encoding="utf-8")

        # Compute summary stats for stdout
        avg_score = sum(r["score"] for r in ranked) / len(ranked) if ranked else 0.0
        intent_dist: dict[str, int] = {}
        for r in ranked:
            intent_dist[r["intent"]] = intent_dist.get(r["intent"], 0) + 1

        print(json.dumps({
            "ranked_count": len(ranked),
            "avg_score": round(avg_score, 3),
            "intent_distribution": intent_dist,
        }))
        return 0

    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
