"""Tests for scripts/lib/io.py — slugify_brief, iso_timestamp, create_run_dir, write_brief."""
from __future__ import annotations
import re
from pathlib import Path

import pytest


def test_iso_timestamp_format() -> None:
    """iso_timestamp() returns YYYY-MM-DDTHHMMSSZ — UTC, no colons (Windows-safe)."""
    from lib.io import iso_timestamp
    ts = iso_timestamp()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{6}Z", ts), f"unexpected format: {ts}"


def test_slugify_brief_basic() -> None:
    from lib.io import slugify_brief
    assert slugify_brief("Same-Day Grocery Delivery") == "same-day-grocery-delivery"


def test_slugify_brief_unicode() -> None:
    """Unicode transliteration (café → cafe) — relies on python-slugify."""
    from lib.io import slugify_brief
    assert slugify_brief("Café Naïve") == "cafe-naive"


def test_slugify_brief_empty_raises() -> None:
    from lib.io import slugify_brief
    with pytest.raises(ValueError):
        slugify_brief("")
    with pytest.raises(ValueError):
        slugify_brief("   ")


def test_slugify_brief_max_length() -> None:
    from lib.io import slugify_brief
    long = "very " * 50
    out = slugify_brief(long, max_length=20)
    assert len(out) <= 20


def test_create_run_dir_creates_layout(tmp_runs_root: Path) -> None:
    """create_run_dir produces <ts>-<slug>/raw/.gitkeep."""
    from lib.io import create_run_dir
    run_dir = create_run_dir(tmp_runs_root, slug_source="grocery delivery")
    assert run_dir.is_dir()
    assert (run_dir / "raw").is_dir()
    assert (run_dir / "raw" / ".gitkeep").is_file()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{6}Z-grocery-delivery", run_dir.name)


def test_create_run_dir_collision_retry(tmp_runs_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same-second double-call gets a 4-hex suffix on the second."""
    from lib.io import create_run_dir
    import lib.io as io_mod
    monkeypatch.setattr(io_mod, "iso_timestamp", lambda: "2026-05-08T143024Z")
    first = create_run_dir(tmp_runs_root, slug_source="x")
    second = create_run_dir(tmp_runs_root, slug_source="x")
    assert first.name == "2026-05-08T143024Z-x"
    assert second.name.startswith("2026-05-08T143024Z-x-")
    assert re.fullmatch(r"2026-05-08T143024Z-x-[0-9a-f]{4}", second.name)


def test_write_brief_verbatim(tmp_runs_root: Path, sample_brief_text: str) -> None:
    """write_brief writes byte-identical content (LF newlines on Windows)."""
    from lib.io import create_run_dir, write_brief
    run_dir = create_run_dir(tmp_runs_root, slug_source="x")
    path = write_brief(run_dir, sample_brief_text)
    assert path.read_text(encoding="utf-8") == sample_brief_text
    # No CR injected on Windows — explicit LF newlines
    assert b"\r\n" not in path.read_bytes()
