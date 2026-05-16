# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-slugify>=8.0",
# ]
# ///
"""update_index.py — append one row to .runs/INDEX.md after each completed run.

CLI:
    uv run update_index.py --run-dir <abs>

Stdout (exactly one JSON line):
    {"index_path": "...", "run_slug": "..."}

Exit codes:
    0  always (non-fatal; missing brief.md → industry = "unknown")
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import escape_md_cell from lib/io.py
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.io import escape_md_cell  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INDEX_HEADER = """# Run History

| Date | Slug | Industry | Status |
|------|------|----------|--------|
"""


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def append_run_to_index(
    runs_root: Path,
    run_dir: Path,
    industry: str,
    status: str = "complete",
) -> None:
    """Appends one row to runs_root/INDEX.md. Creates file + header on first call.

    Args:
        runs_root: Directory that contains INDEX.md (parent of run_dir, typically .runs/).
        run_dir:   The sealed run folder — its .name encodes date and slug.
        industry:  Industry label from brief.md (pass through escape_md_cell).
        status:    Run status string, default "complete".
    """
    name = run_dir.name
    # Folder name format: "YYYY-MM-DDTHHMMSSZ-<slug>" (18-char timestamp + dash + slug).
    # Use regex so optional collision suffix is preserved as part of slug.
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T\d{6}Z-(.+)$", name)
    if m:
        date = m.group(1)
        slug = m.group(2)
    else:  # fallback: raw name
        date = name[:10] if len(name) >= 10 else name
        slug = name

    row = f"| {date} | {slug} | {escape_md_cell(industry)} | {status} |\n"

    index_path = runs_root / "INDEX.md"
    if not index_path.exists():
        index_path.write_text(INDEX_HEADER + row, encoding="utf-8")
    else:
        with index_path.open("a", encoding="utf-8") as fh:
            fh.write(row)


# ---------------------------------------------------------------------------
# Industry extractor
# ---------------------------------------------------------------------------

_INDUSTRY_RE = re.compile(r"\*\*[Ii]ndustry:\*\*\s*(.+)", re.IGNORECASE)


def _extract_industry(brief_path: Path) -> str:
    """Read brief.md and extract the industry field value.

    Returns:
        Stripped industry string, or "unknown" if not found or file missing.
    """
    try:
        text = brief_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return "unknown"
    match = _INDUSTRY_RE.search(text)
    if match:
        return match.group(1).strip()
    return "unknown"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse args, extract industry, append INDEX.md row, print JSON. Returns 0."""
    parser = argparse.ArgumentParser(
        description="Append one row to .runs/INDEX.md for a completed run.",
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="Absolute path to the sealed run folder.",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=None,
        help="Directory containing INDEX.md. Defaults to run_dir.parent.",
    )
    args = parser.parse_args()

    run_dir: Path = args.run_dir
    runs_root: Path = args.runs_root if args.runs_root is not None else run_dir.parent

    industry = _extract_industry(run_dir / "brief.md")
    append_run_to_index(runs_root, run_dir, industry)

    name = run_dir.name
    m = re.match(r"^\d{4}-\d{2}-\d{2}T\d{6}Z-(.+)$", name)
    run_slug = m.group(1) if m else name

    print(json.dumps({
        "index_path": str(runs_root / "INDEX.md"),
        "run_slug": run_slug,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
