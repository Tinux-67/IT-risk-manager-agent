#!/usr/bin/env python3
"""
Centralized logging setup for the IT Risk Manager Agent.
Call setup_logging() once at the start of each entry point.
Subsequent calls are no-ops (idempotent guard).
"""

import sys

from loguru import logger

from config import Config

_configured: bool = False


def setup_logging() -> None:
    """Configure loguru with stderr + rotating file handler (idempotent)."""
    global _configured
    if _configured:
        return

    logger.remove()  # drop the default handler

    fmt = "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {file}:{line} | {message}"

    logger.add(sys.stderr, level=Config.LOG_LEVEL, format=fmt, colorize=True)
    logger.add(
        Config.get_log_file(),
        rotation=Config.LOG_ROTATION,
        retention=Config.LOG_RETENTION,
        level=Config.LOG_LEVEL,
        format=fmt,
    )

    _configured = True
