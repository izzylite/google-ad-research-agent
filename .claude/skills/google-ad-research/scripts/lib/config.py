"""lib/config.py — locate and load .env from project root.

Phase 1 callers pass require=() because run_init.py needs no API keys.
Phase 2+ scripts pass require=("SERPER_API_KEY",) etc. to fail loud on missing keys.

Contract:
- Walk up the filesystem to find a `.env`; load it with override=False so the
  operator's shell exports always win over file values.
- Never log key values. Never accept keys via CLI args (callers must read from os.environ
  AFTER load_env() returns).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

REQUIRED_KEYS: tuple[str, ...] = ("SERPER_API_KEY", "TAVILY_API_KEY")


def load_env(*, require: tuple[str, ...] = ()) -> Path:
    """Locate, load, and (optionally) require env vars from .env + the OS environment.

    Args:
        require: Tuple of env var names that MUST be set after loading. Pass () in Phase 1.
                 Phase 2+ helpers should pass the keys they actually need.

    Returns:
        Path to the .env file that was loaded (or `Path()` if none was found).

    Raises:
        EnvironmentError: if any required key is still unset after loading.
    """
    dotenv_path = find_dotenv(usecwd=True, raise_error_if_not_found=False)
    if dotenv_path:
        load_dotenv(dotenv_path, override=False)  # OS env wins
    missing = [k for k in require if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required env vars: {', '.join(missing)}. "
            f"Check .env or shell exports."
        )
    return Path(dotenv_path) if dotenv_path else Path()
