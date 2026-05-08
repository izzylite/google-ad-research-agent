"""lib/log.py — single-handler stderr logger for Phase 1.

Phase 2+ adds a per-run JSON sidecar handler.
"""
from __future__ import annotations

import logging
import sys


def configure_logger(name: str = "gar", level: int = logging.INFO) -> logging.Logger:
    """Return a stderr logger; idempotent across re-imports."""
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    log.addHandler(handler)
    log.propagate = False
    return log
