"""Tests for scripts/run_init.py — folder creation, collision retry, verbatim brief write."""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "run_init.py"


def _run(brief: str, slug_source: str, runs_root: Path) -> subprocess.CompletedProcess[str]:
    """Invoke run_init.py with brief on stdin. Returns CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH),
         "--slug-source", slug_source,
         "--runs-root", str(runs_root)],
        input=brief,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_creates_run_folder(tmp_runs_root: Path, sample_brief_text: str) -> None:
    """Happy path: brief on stdin → folder + brief.md + raw/.gitkeep on disk."""
    proc = _run(sample_brief_text, "grocery delivery", tmp_runs_root)
    assert proc.returncode == 0, f"stderr:\n{proc.stderr}"
    payload = json.loads(proc.stdout.strip())
    run_dir = Path(payload["run_dir"])
    assert run_dir.exists()
    assert (run_dir / "brief.md").is_file()
    assert (run_dir / "raw").is_dir()
    assert (run_dir / "raw" / ".gitkeep").is_file()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{6}Z-grocery-delivery", run_dir.name)


def test_brief_written_verbatim(tmp_runs_root: Path, sample_brief_text: str) -> None:
    """brief.md content equals stdin bytes — INTK-04 contract."""
    proc = _run(sample_brief_text, "grocery delivery", tmp_runs_root)
    assert proc.returncode == 0, f"stderr:\n{proc.stderr}"
    payload = json.loads(proc.stdout.strip())
    brief_path = Path(payload["brief_path"])
    assert brief_path.read_text(encoding="utf-8") == sample_brief_text


def test_collision_retry(tmp_runs_root: Path, sample_brief_text: str) -> None:
    """Two rapid invocations within the same second produce two distinct folders."""
    p1 = _run(sample_brief_text, "x", tmp_runs_root)
    p2 = _run(sample_brief_text, "x", tmp_runs_root)
    assert p1.returncode == 0 and p2.returncode == 0
    d1 = Path(json.loads(p1.stdout.strip())["run_dir"])
    d2 = Path(json.loads(p2.stdout.strip())["run_dir"])
    assert d1 != d2
    assert d1.is_dir() and d2.is_dir()


def test_empty_brief_exits_2(tmp_runs_root: Path) -> None:
    """Empty stdin → exit 2 (gate), no folder created."""
    proc = _run("", "x", tmp_runs_root)
    assert proc.returncode == 2
    # Stdout should be empty (script exits before printing the JSON line)
    assert proc.stdout.strip() == ""
    assert list(tmp_runs_root.iterdir()) == []


def test_empty_slug_source_exits_2(tmp_runs_root: Path, sample_brief_text: str) -> None:
    """Empty / whitespace-only --slug-source → exit 2."""
    proc = _run(sample_brief_text, "   ", tmp_runs_root)
    assert proc.returncode == 2


def test_stdout_is_single_json_line(tmp_runs_root: Path, sample_brief_text: str) -> None:
    """SKILL.md parses stdout as one JSON object — no extra prose."""
    proc = _run(sample_brief_text, "grocery", tmp_runs_root)
    assert proc.returncode == 0
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert set(payload.keys()) >= {"run_dir", "slug", "timestamp", "brief_path"}
