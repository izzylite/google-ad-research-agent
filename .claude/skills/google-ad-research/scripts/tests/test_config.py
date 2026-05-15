"""Tests for scripts/lib/config.py — load_env, REQUIRED_KEYS, find_dotenv walk."""
from __future__ import annotations
import os
from pathlib import Path

import pytest


def test_required_keys_defined() -> None:
    from lib.config import REQUIRED_KEYS
    assert "SERPER_API_KEY" in REQUIRED_KEYS
    # Phase 12 (v1.3 — Drop Tavily): TAVILY_API_KEY removed from REQUIRED_KEYS.
    assert "TAVILY_API_KEY" not in REQUIRED_KEYS


def test_load_env_no_require_returns_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 1 callers pass require=() — should never raise even if keys absent."""
    from lib.config import load_env
    # Move into a temp dir with no .env so the find_dotenv walk fails over
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = load_env(require=())
    assert isinstance(result, Path)


def test_load_env_missing_required_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 2+ callers pass require=('SERPER_API_KEY',) — raise EnvironmentError on miss."""
    from lib.config import load_env
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    with pytest.raises(EnvironmentError):
        load_env(require=("SERPER_API_KEY",))


def test_load_env_override_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing OS env vars win over .env file values."""
    from lib.config import load_env
    env_file = tmp_path / ".env"
    env_file.write_text("MY_TEST_VAR=from_file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MY_TEST_VAR", "from_shell")
    load_env(require=())
    assert os.environ["MY_TEST_VAR"] == "from_shell"
