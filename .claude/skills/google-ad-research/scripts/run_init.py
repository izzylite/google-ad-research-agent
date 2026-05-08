# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv>=1.0",
#     "python-slugify>=8.0",
# ]
# ///
"""run_init.py — create a sealed run folder + write brief.md verbatim.

CLI:
    uv run run_init.py --slug-source "<phrase>" [--runs-root PATH] < brief.md

Stdout (exactly one JSON line):
    {"run_dir": "<abs path>", "slug": "...", "timestamp": "...", "brief_path": "..."}

Stderr: human-readable progress messages.

Exit codes:
    0 ok
    2 missing or empty --slug-source, or empty stdin
    3 filesystem or env error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make sibling lib/ importable when invoked via `uv run path/to/run_init.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.config import load_env  # noqa: E402
from lib.io import create_run_dir, write_brief  # noqa: E402
from lib.log import configure_logger  # noqa: E402

log = configure_logger()


def _find_project_root(start: Path) -> Path | None:
    """Walk up from `start` looking for a directory containing `.git/` or `.planning/`."""
    for parent in start.parents:
        if (parent / ".git").exists() or (parent / ".planning").exists():
            return parent
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a sealed run folder for the google-ad-research skill.",
    )
    parser.add_argument(
        "--slug-source",
        required=True,
        help="Phrase to derive the slug from (typically the brief's 'product' field).",
    )
    parser.add_argument(
        "--runs-root",
        default=None,
        help="Override the default .runs/ location (mostly for tests).",
    )
    args = parser.parse_args()

    # Validate slug-source BEFORE touching the filesystem so empty-input tests
    # observe an empty runs_root.
    if not args.slug_source or not args.slug_source.strip():
        log.error("--slug-source is empty")
        return 2

    # Read brief from stdin (bytes → UTF-8) before creating any folder so empty
    # input does not leave a half-built run on disk.
    brief_text = sys.stdin.buffer.read().decode("utf-8")
    if not brief_text.strip():
        log.error("Empty brief on stdin")
        return 2

    # Phase 1 has no API keys to require. load_env() is called for its side
    # effect (populating os.environ from .env) so Phase 2+ scripts that share a
    # process can rely on it. Safe to call without `require`.
    try:
        load_env(require=())
    except EnvironmentError as exc:
        log.error(str(exc))
        return 3

    # Resolve runs_root.
    if args.runs_root:
        runs_root = Path(args.runs_root).resolve()
    else:
        here = Path(__file__).resolve()
        project_root = _find_project_root(here)
        if project_root is None:
            log.error(
                "Could not locate project root (no .git or .planning/ found above this script)"
            )
            return 3
        runs_root = project_root / ".runs"

    # Create the run folder + write the brief.
    try:
        run_dir = create_run_dir(runs_root, slug_source=args.slug_source)
        brief_path = write_brief(run_dir, brief_text)
    except (ValueError, OSError) as exc:
        log.error(f"Failed to initialize run dir: {exc}")
        return 3

    log.info(f"Created run folder: {run_dir}")
    log.info(f"Wrote brief: {brief_path}")

    # Derive slug + timestamp from the run_dir name itself rather than re-calling
    # iso_timestamp() — guarantees stdout matches what's actually on disk.
    name = run_dir.name
    # Format: YYYY-MM-DDTHHMMSSZ-<slug>[ -<4hex>]
    # Split on first 'Z-' to separate timestamp from the slug+suffix.
    if "Z-" in name:
        ts, slug = name.split("Z-", 1)
        ts = ts + "Z"
    else:  # defensive — should never happen
        ts, slug = name, ""

    print(json.dumps({
        "run_dir": str(run_dir),
        "slug": slug,
        "timestamp": ts,
        "brief_path": str(brief_path),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
