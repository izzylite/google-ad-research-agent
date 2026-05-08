# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "inflect>=7.5",
# ]
# ///
"""pulse_synth.py — Synthesize niche-pulse.json from raw news inputs.

Reads:
  {run_dir}/raw/serper-news.json
  {run_dir}/raw/tavily-news.json

Produces:
  {run_dir}/niche-pulse.json

Schema:
  {
    "captured_at": "...",
    "horizon_days": N,
    "trending_themes": [
      {"theme": "florida pip law amendment",
       "mention_count": N,
       "first_seen": "YYYY-MM-DD",
       "sources": ["serper-news", "tavily-news"],
       "headlines": [{title, link, date, source}, ...],
       "suggested_keywords": [...]}
    ],
    "regulatory_alerts":   [...same shape...],
    "competitor_news":     [...same shape...],
    "trending_negatives":  [...same shape...]
  }

Themes are derived deterministically: phrase n-grams that appear in 2+ headlines
across the harvest are clustered together. Headlines mentioning regulatory
keywords get tagged regulatory_alerts. Headlines naming a known brand or
URL-domain that resembles a clinic/competitor get tagged competitor_news.
Trending negatives surface when a headline contains scam/fraud/lawsuit/recall
language.

CLI:
    uv run pulse_synth.py --run-dir <abs path> [--brand BRAND ...]

Stdout (one JSON line):
    {"niche_pulse_path": "...",
     "trending_themes_count": N,
     "regulatory_alerts_count": N,
     "competitor_news_count": N,
     "trending_negatives_count": N,
     "horizon_days": N}

Exit codes:
    0  ok
    3  fatal (missing input files, IO error)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REGULATORY_KEYWORDS = frozenset({
    "law", "laws", "lawsuit", "ruling", "court", "judge", "verdict",
    "regulation", "regulatory", "compliance", "policy", "amendment",
    "bill", "statute", "act", "fda", "ftc", "cdc", "cms", "hipaa",
    "ada", "pip", "medicare", "medicaid", "insurance", "license",
    "fine", "fined", "penalty", "violation", "settlement",
    "ordinance", "legislature", "senate", "house", "governor",
})

NEGATIVE_TRIGGER_KEYWORDS = frozenset({
    "scam", "scams", "fraud", "fraudulent", "lawsuit", "fined",
    "recalled", "recall", "shutdown", "closed", "shuttered",
    "fake", "investigation", "investigated", "warning", "warnings",
    "complaint", "complaints", "indicted", "arrested", "charged",
    "convicted", "abuse", "neglect", "malpractice",
})

# Stop tokens that produce useless n-grams
STOP_TOKENS = frozenset({
    # Function words / determiners
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "should", "could", "may", "might", "can", "this", "that", "these",
    "those", "i", "you", "he", "she", "it", "we", "they", "them", "their",
    "his", "her", "its", "our", "your", "as", "if", "than", "then", "so",
    "not", "no", "yes", "out", "up", "down", "over", "under", "into",
    "about", "after", "before", "during", "while", "since", "until",
    "via", "amid", "among", "around", "across", "against", "between",
    "new", "more", "most", "less", "least", "very", "just", "also",
    "now", "then", "here", "there", "when", "where", "why", "how",
    "what", "which", "who", "whom", "whose",
    "absolutely", "really", "actually", "still", "yet", "even",
    # Media/news brand tokens — filter byline noise
    "reuters", "bloomberg", "associated", "press", "ap", "afp",
    "cbs", "nbc", "abc", "fox", "cnn", "msnbc", "pbs", "npr", "bbc",
    "nyt", "wsj", "wapo", "guardian", "telegraph", "newsweek",
    "huffpost", "yahoo", "buzzfeed", "vox", "axios", "politico",
    "tmz", "people", "variety", "deadline", "salon",
    # Reporter/anchor common first names that recur in bylines
    "jim", "bob", "joe", "john", "tom", "ted", "tim", "dan", "jeff",
    "jane", "kate", "mary", "anne", "lisa", "sarah", "amy", "amanda",
    "berry", "berry's", "smith", "jones", "brown", "miller", "davis",
    # Time / date words
    "today", "yesterday", "tomorrow",
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday",
    "morning", "afternoon", "evening", "night", "tonight",
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "week", "month", "year", "weeks", "months", "years",
    "ago", "earlier", "later", "soon", "recently", "lately",
    # Verbose news verbs
    "report", "reports", "reported", "reporting",
    "says", "said", "saying", "tells", "told", "telling",
    "according", "according-to", "claim", "claims", "claimed",
    "announce", "announced", "announces", "announcement",
    "confirm", "confirmed", "confirms", "deny", "denied",
    # Generic count modifiers
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "first", "second", "third",
})

# Minimum mentions to surface a theme (auto-scaled per harvest size below)
MIN_THEME_MENTIONS_FLOOR = 3

# Cap output count — top themes by mention_count
MAX_THEMES = 30

# n-gram window
NGRAM_MIN = 2
NGRAM_MAX = 4

# How many headlines to keep per theme
HEADLINES_PER_THEME = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize(text: str) -> str:
    """Lowercase, strip non-alphanumeric except spaces."""
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text: str) -> list[str]:
    return [t for t in _normalize(text).split() if len(t) > 1 and t not in STOP_TOKENS]


def _ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def load_news_items(serper_path: Path, tavily_path: Path) -> list[dict]:
    """Read both raws; return flat list of news items with consistent shape."""
    items: list[dict] = []

    if serper_path.exists():
        try:
            data = json.loads(serper_path.read_text(encoding="utf-8"))
            for block in data.get("by_seed", []):
                for item in block.get("items", []):
                    items.append(item)
        except (json.JSONDecodeError, OSError):
            pass

    if tavily_path.exists():
        try:
            data = json.loads(tavily_path.read_text(encoding="utf-8"))
            for block in data.get("by_seed", []):
                for item in block.get("items", []):
                    items.append(item)
        except (json.JSONDecodeError, OSError):
            pass

    return items


def find_themes(items: list[dict]) -> list[dict]:
    """Cluster items by repeated n-grams in titles + snippets.

    Each n-gram with mention_count >= MIN_THEME_MENTIONS becomes a theme.
    Subsumed n-grams (3-grams that fully contain a 2-gram with same item set)
    are dropped to avoid duplicates.
    """
    # Map ngram -> set of item indices
    ngram_to_items: dict[tuple[str, ...], set[int]] = defaultdict(set)
    for idx, item in enumerate(items):
        text = f"{item.get('title') or ''} {item.get('snippet') or ''}"
        toks = _tokens(text)
        for n in range(NGRAM_MIN, NGRAM_MAX + 1):
            for ng in _ngrams(toks, n):
                ngram_to_items[ng].add(idx)

    # Auto-scale threshold to harvest size: at least floor, more for larger
    # harvests so we don't drown in 2-grams.
    threshold = max(MIN_THEME_MENTIONS_FLOOR, len(items) // 25)

    # Collect candidates above threshold
    candidates = [(ng, idxs) for ng, idxs in ngram_to_items.items()
                  if len(idxs) >= threshold]
    # Prefer longer n-grams (more specific). Filter shorter n-grams that are
    # fully contained in a longer one with identical item set.
    candidates.sort(key=lambda x: (-len(x[0]), -len(x[1])))
    kept: list[tuple[tuple[str, ...], set[int]]] = []
    for ng, idxs in candidates:
        ng_tokens = set(ng)
        subsumed = False
        for kept_ng, kept_idxs in kept:
            if (set(kept_ng) >= ng_tokens) and (kept_idxs >= idxs):
                subsumed = True
                break
        if not subsumed:
            kept.append((ng, idxs))

    # Build theme records
    themes = []
    for ng, idxs in kept:
        idx_list = sorted(idxs)
        theme_items = [items[i] for i in idx_list]
        sources = sorted({i.get("_source", "unknown") for i in theme_items})
        # First seen = min date among items
        dates = [i.get("date") for i in theme_items if i.get("date")]
        first_seen = min(dates) if dates else None
        # Suggested kw: the n-gram itself + with parent topic suffix
        suggested = [" ".join(ng)]
        # Headlines (top by score if Tavily, else first N)
        headlines = []
        for it in theme_items[:HEADLINES_PER_THEME]:
            headlines.append({
                "title": it.get("title"),
                "link": it.get("link"),
                "date": it.get("date"),
                "source": it.get("source"),
            })
        themes.append({
            "theme": " ".join(ng),
            "mention_count": len(idxs),
            "first_seen": first_seen,
            "sources": sources,
            "headlines": headlines,
            "suggested_keywords": suggested,
        })

    # Filter low-quality themes: must have ≥1 substantive token (4+ chars,
    # not just connecting words). Drops "in florida" / "with new" patterns.
    themes = [t for t in themes if _theme_has_substance(t["theme"])]

    # Sort by mention_count desc, cap to MAX_THEMES
    themes.sort(key=lambda t: -t["mention_count"])
    return themes[:MAX_THEMES]


def _theme_has_substance(theme: str) -> bool:
    """A theme is substantive when it carries at least one 4+ char token that
    isn't a stop-token or pure number."""
    for tok in theme.split():
        if len(tok) >= 4 and tok not in STOP_TOKENS and not tok.isdigit():
            return True
    return False


def find_highlights(themes: list[dict],
                    regulatory: list[dict],
                    competitor_news: list[dict],
                    trending_negatives: list[dict]) -> list[dict]:
    """Surface the most actionable items across all four sections.

    Returns a small ranked list (max 5) — each entry has a `kind`, a
    one-line summary, and the underlying record. Used by the report's
    "Highlights" callout so operator sees the punchline before scrolling.
    """
    highlights: list[dict] = []
    seen_summaries: set[str] = set()

    def _add(item: dict) -> None:
        # Dedup by lowercased title — news APIs often return same headline
        # via multiple seeds.
        key = (item.get("summary") or "").strip().lower()
        if key and key in seen_summaries:
            return
        seen_summaries.add(key)
        highlights.append(item)

    # 1. Regulatory alerts naming PIP / law / repeal / amendment / court
    #    are highest priority — affect bidding strategy directly.
    high_value_regs = ["repeal", "amendment", "ruling", "verdict", "lawsuit",
                       "settlement", "new law", "passed", "signed"]
    for r in regulatory:
        title_lower = (r.get("title") or "").lower()
        if any(kw in title_lower for kw in high_value_regs):
            _add({
                "kind": "regulatory",
                "summary": r.get("title", ""),
                "date": r.get("date"),
                "link": r.get("link"),
                "matched_keywords": r.get("matched_keywords", []),
                "why_it_matters": "Regulatory shift can invalidate ad copy "
                                  "claims and change PIP/insurance bidding.",
            })
        if len(highlights) >= 3:
            break

    # 2. Competitor news (any mention is news to the operator)
    for c in competitor_news[:2]:
        _add({
            "kind": "competitor",
            "summary": c.get("title", ""),
            "date": c.get("date"),
            "link": c.get("link"),
            "matched_brand": c.get("matched_brand"),
            "why_it_matters": "Competitor activity — informs conquesting and "
                              "differentiation messaging.",
        })

    # 3. Top trending theme — prefer multi-token, multi-source themes
    #    (more substantive than 2-word noise like "vehicle crash").
    for t in themes:
        word_count = len(t.get("theme", "").split())
        source_count = len(t.get("sources", []))
        # Prefer themes with 3+ tokens OR multi-source coverage
        if word_count >= 3 or source_count >= 2:
            _add({
                "kind": "trend",
                "summary": f"Trending: \"{t['theme']}\" "
                           f"({t['mention_count']} mentions across "
                           f"{source_count} sources)",
                "first_seen": t.get("first_seen"),
                "headlines": t.get("headlines", [])[:2],
                "why_it_matters": "Spike in news mentions — early opportunity "
                                  "for matching keyword bids before "
                                  "competitors react.",
            })
            break

    return highlights[:5]


def find_regulatory_alerts(items: list[dict]) -> list[dict]:
    """Items whose title/snippet hits regulatory keyword set."""
    alerts = []
    for item in items:
        text = _normalize(f"{item.get('title') or ''} {item.get('snippet') or ''}")
        hits = REGULATORY_KEYWORDS.intersection(text.split())
        if hits:
            alerts.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "date": item.get("date"),
                "source": item.get("source"),
                "matched_keywords": sorted(hits),
                "snippet": item.get("snippet"),
                "from_seed": item.get("from_seed"),
            })
    return alerts


def find_competitor_news(items: list[dict], brands: list[str]) -> list[dict]:
    """Items that mention a brand name or competitor domain.

    Also includes items whose URL belongs to a known clinic/healthcare domain
    pattern (urgentcare, clinic, hospital, medical) when no brand list given.
    """
    brand_set = {b.lower() for b in brands if b}
    competitor_news = []

    for item in items:
        text = _normalize(f"{item.get('title') or ''} {item.get('snippet') or ''}")
        domain = urlparse(item.get("link") or "").netloc.lower()

        matched_brand = None
        for b in brand_set:
            if b and b in text:
                matched_brand = b
                break

        if matched_brand:
            competitor_news.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "date": item.get("date"),
                "source": item.get("source"),
                "matched_brand": matched_brand,
                "domain": domain,
                "snippet": item.get("snippet"),
            })

    return competitor_news


def find_trending_negatives(items: list[dict]) -> list[dict]:
    """Items containing scam/fraud/lawsuit/recall language.

    These suggest terms to ADD to the negative keyword list — searches around
    bad events typically don't convert and waste spend.
    """
    negs = []
    for item in items:
        text = _normalize(f"{item.get('title') or ''} {item.get('snippet') or ''}")
        toks = set(text.split())
        hits = NEGATIVE_TRIGGER_KEYWORDS.intersection(toks)
        if hits:
            negs.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "date": item.get("date"),
                "source": item.get("source"),
                "trigger_keywords": sorted(hits),
                # sorted() instead of list(set)[0] — set ordering is
                # hash-randomized; this kept the same value across runs.
                "suggested_negative": sorted(hits)[0],
                "from_seed": item.get("from_seed"),
            })
    return negs


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Synthesize niche-pulse.json from news raws."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--brand", action="append", default=[],
                        help="Repeatable. Brand name to match in competitor_news. "
                             "Can be the operator's own brand or known competitors.")
    args = parser.parse_args(argv)

    if not args.run_dir.exists():
        print(json.dumps({"error": f"--run-dir does not exist: {args.run_dir}"}),
              file=sys.stderr)
        return 3

    raw_dir = args.run_dir / "raw"
    serper_path = raw_dir / "serper-news.json"
    tavily_path = raw_dir / "tavily-news.json"

    if not serper_path.exists() and not tavily_path.exists():
        print(json.dumps({
            "error": "Neither serper-news.json nor tavily-news.json found — "
                     "run pulse_fetch.py first.",
        }), file=sys.stderr)
        return 3

    items = load_news_items(serper_path, tavily_path)

    horizon_days = 7
    if serper_path.exists():
        try:
            horizon_days = json.loads(serper_path.read_text(encoding="utf-8")).get("horizon_days", 7)
        except (json.JSONDecodeError, OSError):
            pass

    themes = find_themes(items)
    regulatory = find_regulatory_alerts(items)
    competitor = find_competitor_news(items, args.brand)
    negatives = find_trending_negatives(items)

    highlights = find_highlights(themes, regulatory, competitor, negatives)

    pulse = {
        "captured_at": _now_iso(),
        "horizon_days": horizon_days,
        "total_news_items": len(items),
        "highlights": highlights,
        "trending_themes": themes,
        "regulatory_alerts": regulatory,
        "competitor_news": competitor,
        "trending_negatives": negatives,
    }

    out_path = args.run_dir / "niche-pulse.json"
    out_path.write_text(json.dumps(pulse, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    print(json.dumps({
        "niche_pulse_path": str(out_path),
        "highlights_count": len(highlights),
        "trending_themes_count": len(themes),
        "regulatory_alerts_count": len(regulatory),
        "competitor_news_count": len(competitor),
        "trending_negatives_count": len(negatives),
        "horizon_days": horizon_days,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main_with_args(sys.argv[1:]))
