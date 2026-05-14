# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""export_csv.py — Write Google Ads Editor v2.x importable CSVs (EXPT-01..04).

STUB — Wave 1 (Phase 10 plan 10-01) implements the actual writers. This
module currently exposes the locked contracts (header lists, tier→level
map, match-type title-case map) so that:

  1. Wave 0 RED tests can import the module and reference the constants
     without ImportError.
  2. The MODULE_INCOMPLETE sentinel (absence of `write_positives`) keeps
     all Wave 0 tests SKIPPED until Wave 1 lands them.
  3. `python export_csv.py` (or `uv run export_csv.py --run-dir …`) raises
     NotImplementedError immediately so accidental invocation is loud.

Contracts (Wave 1 must satisfy):
    {run_dir}/export/positives.csv   — Campaign, Ad Group, Keyword,
                                       Match Type, Max CPC, Final URL
    {run_dir}/export/negatives.csv   — Campaign, Ad Group, Keyword,
                                       Match Type, Level
    {run_dir}/export/ad_groups.csv   — Campaign, Ad Group, Status,
                                       Default Max CPC

Byte contract (EXPT-04):
    UTF-8 (NOT utf-8-sig — no BOM), CRLF line endings, RFC 4180 quoting
    via csv.DictWriter with quoting=csv.QUOTE_MINIMAL.

CLI (Wave 1):
    uv run export_csv.py --run-dir <abs>

Exit codes (Wave 1 will implement):
    0  ok — all three CSVs written
    2  retryable (transient disk error)
    3  fatal (missing input, malformed JSON)
"""
from __future__ import annotations

import sys

# --- Header contracts (EXPT-01..03) -----------------------------------------
# Wave 0 tests import these. Wave 1 helpers write them via DictWriter.
POSITIVES_HEADERS: list[str] = [
    "Campaign", "Ad Group", "Keyword", "Match Type", "Max CPC", "Final URL",
]
NEGATIVES_HEADERS: list[str] = [
    "Campaign", "Ad Group", "Keyword", "Match Type", "Level",
]
AD_GROUPS_HEADERS: list[str] = [
    "Campaign", "Ad Group", "Status", "Default Max CPC",
]

# Tier → Level mapping (EXPT-02 / NEGT-* contract):
#   Strong tier      → campaign-level negative (Ad Group cell stays empty)
#   Considered tier  → ad_group-level negative (Ad Group = cluster name)
#   Investigate tier → ad_group-level negative (operator decides cluster)
TIER_TO_LEVEL: dict[str, str] = {
    "Strong": "campaign",
    "Considered": "ad_group",
    "Investigate": "ad_group",
}

# Internal taxonomy is lowercase (rank_keywords.py / Phase 3); Editor v2.x
# CSV format expects title-case. Convert at the write boundary only.
MATCH_TYPE_TITLECASE: dict[str, str] = {
    "phrase": "Phrase",
    "exact": "Exact",
    "broad": "Broad",
}


def main(argv: list[str] | None = None) -> int:
    """STUB — Wave 1 implements. Raises NotImplementedError on call."""
    raise NotImplementedError(
        "export_csv.py not yet implemented (Phase 10 Wave 0 stub). "
        "Wave 1 (plan 10-01) ships write_positives / write_negatives / "
        "write_ad_groups + CLI."
    )


if __name__ == "__main__":  # pragma: no cover — stub
    sys.exit(main(sys.argv))
