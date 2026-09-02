#!/usr/bin/env python3
"""
Centralized logging setup for the IT Risk Manager Agent.
Call setup_logging() once at the start of each entry point.
Subsequent calls are no-ops (idempotent guard).

R5 — loguru configured to write:
  1. Human-readable rotating text log  → logs/app_{date}.log
  2. Machine-readable JSON log        → logs/app_{date}.json
"""

from __future__ import annotations

import sys

from loguru import logger

from config import Config

_configured: bool = False


def _json_log_path() -> str:
    from datetime import datetime
    stamp = datetime.now().strftime("%Y-%m-%d")
    return str(Config.LOGS_DIR / f"app_{stamp}.json")


def setup_logging() -> None:
    """Configure loguru with stderr + rotating text file + rotating JSON file (idempotent)."""
    global _configured
    if _configured:
        return

    logger.remove()

    # ── Human-readable format ────────────────────────────────────────────────
    fmt = "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {file}:{line} | {message}"
    logger.add(
        sys.stderr,
        level=Config.LOG_LEVEL,
        format=fmt,
        colorize=True,
    )

    # ── Rotating text log ──────────────────────────────────────────────────
    logger.add(
        Config.get_log_file(),
        rotation=Config.LOG_ROTATION,
        retention=Config.LOG_RETENTION,
        level=Config.LOG_LEVEL,
        format=fmt,
        compression="gz",
    )

    # ── Structured JSON log (machine-parseable) ────────────────────────────
    logger.add(
        _json_log_path(),
        rotation=Config.LOG_ROTATION,
        retention=Config.LOG_RETENTION,
        level=Config.LOG_LEVEL,
        serialize=True,       # loguru serialises to JSON automatically
        compression="gz",
    )

    _configured = True
    logger.info("Logging configured — text + JSON handlers active")
