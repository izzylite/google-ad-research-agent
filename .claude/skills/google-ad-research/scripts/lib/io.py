"""lib/io.py — filesystem + naming helpers."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from slugify import slugify


def iso_timestamp() -> str:
    """UTC ISO 8601, seconds resolution, filesystem-safe.

    Returns e.g. "2026-05-08T143024Z" (no colons — Windows-safe).
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def slugify_brief(slug_source: str, *, max_length: int = 60) -> str:
    """Convert an arbitrary brief phrase into a filesystem-safe slug.

    Empty / whitespace-only input or empty slug result raises ValueError.
    """
    if not slug_source or not slug_source.strip():
        raise ValueError("slug_source is empty")
    slug = slugify(slug_source, max_length=max_length, word_boundary=True, save_order=True)
    if not slug:
        raise ValueError(f"slug_source {slug_source!r} produced empty slug")
    return slug


def create_run_dir(runs_root: Path, *, slug_source: str) -> Path:
    """Create .runs/<ts>-<slug>/ + raw/.gitkeep ; return absolute path.

    Retries with a 4-hex suffix on collision (rapid re-run within same second).
    """
    runs_root.mkdir(parents=True, exist_ok=True)
    ts = iso_timestamp()
    slug = slugify_brief(slug_source)
    base = f"{ts}-{slug}"
    run_dir = runs_root / base
    attempts = 0
    while attempts < 5:
        try:
            run_dir.mkdir(parents=False, exist_ok=False)
            break
        except FileExistsError:
            suffix = secrets.token_hex(2)  # 4 hex chars
            run_dir = runs_root / f"{base}-{suffix}"
            attempts += 1
    else:
        raise OSError(f"Could not create unique run dir under {runs_root}")
    raw_dir = run_dir / "raw"
    raw_dir.mkdir()
    (raw_dir / ".gitkeep").write_bytes(b"")
    return run_dir.resolve()


def write_brief(run_dir: Path, brief_text: str) -> Path:
    """Write brief.md verbatim with LF newlines. Returns the path."""
    brief_path = run_dir / "brief.md"
    brief_path.write_text(brief_text, encoding="utf-8", newline="\n")
    return brief_path


# ---------------------------------------------------------------------------
# Markdown table cell sanitizer
# ---------------------------------------------------------------------------

_SMART_QUOTE_MAP = str.maketrans({
    "‘": "'",  # left single quotation mark
    "’": "'",  # right single quotation mark
    "“": '"',  # left double quotation mark
    "”": '"',  # right double quotation mark
    "–": "-",  # en dash
    "—": "-",  # em dash
})


def escape_md_cell(s: str, *, max_len: int = 120) -> str:
    """Sanitize a string for safe use in a GFM markdown table cell.

    Operations (in order):
    1. Coerce non-strings to str.
    2. Normalize smart quotes and dashes to ASCII equivalents.
    3. Replace literal newlines/carriage returns with a single space.
    4. Escape pipe characters as \\|.
    5. Truncate to max_len with ellipsis if needed.
    """
    if not isinstance(s, str):
        s = str(s)
    s = s.translate(_SMART_QUOTE_MAP)
    s = re.sub(r"[\r\n]+", " ", s)
    s = s.replace("|", r"\|")
    if len(s) > max_len:
        s = s[:max_len - 1] + "…"
    return s
