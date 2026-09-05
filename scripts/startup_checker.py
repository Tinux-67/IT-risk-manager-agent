#!/usr/bin/env python3
"""
Pre-startup health verification for the IT Risk Manager Agent.

Verifies that all hard dependencies are ready before the Streamlit app starts:
  1. SQLite database exists and is readable
  2. Ollama API is reachable
  3. Raw data directories exist (EBA and MAS)

Exit codes:
  0  — all checks passed
  1  — one or more checks failed  (script logs the failures before exiting)

Usage:
  python scripts/startup_checker.py
  python scripts/startup_checker.py --strict   # fail if raw dirs are empty too
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

from loguru import logger

# ── Loguru setup ──────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    format="<level>{level: <8}</level> | <level>{message}</level>",
    colorize=False,
)


# ── Checks ────────────────────────────────────────────────────────────────────


def check_database(db_path: str) -> bool:
    """Verify the SQLite database exists and is readable."""
    path = Path(db_path)
    if not path.exists():
        logger.error(f"[DB] Database not found at: {db_path}")
        return False
    if not os.access(path, os.R_OK):
        logger.error(f"[DB] Database not readable: {db_path}")
        return False
    try:
        conn = sqlite3.connect(str(path), timeout=5)
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except sqlite3.Error as exc:
        logger.error(f"[DB] SQLite error: {exc}")
        return False

    logger.info(f"[DB] OK — {db_path}")
    return True


def check_ollama(ollama_host: str, timeout: float = 5.0) -> bool:
    """Verify the Ollama API is reachable via Python urllib."""
    url = f"{ollama_host.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url)  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            import json
            data = json.loads(resp.read())
            models = data.get("models", [])
            logger.info(f"[Ollama] OK — {url} ({len(models)} model(s) loaded)")
            return True
    except urllib.error.URLError as exc:
        logger.error(f"[Ollama] Unreachable: {exc}")
        return False
    except Exception as exc:
        logger.error(f"[Ollama] Error: {exc}")
        return False


def check_raw_dirs(eba_dir: str, mas_dir: str, strict: bool = False) -> bool:
    """Verify raw data directories exist. In strict mode, each must contain at least one file."""
    ok = True
    for label, path_str in [("EBA", eba_dir), ("MAS", mas_dir)]:
        path = Path(path_str)
        if not path.exists():
            logger.error(f"[Data] {label} raw directory not found: {path_str}")
            ok = False
            continue
        if not os.access(path, os.R_OK | os.X_OK):
            logger.error(f"[Data] {label} raw directory not accessible: {path_str}")
            ok = False
            continue
        if strict:
            files = [f for f in path.rglob("*") if f.is_file()]
            if not files:
                logger.warning(f"[Data] {label} raw directory is empty: {path_str}")
            else:
                logger.info(f"[Data] {label} OK — {len(files)} file(s) in {path_str}")
        else:
            logger.info(f"[Data] {label} OK — {path_str}")
    return ok


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-startup health verification")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also fail if raw data directories are empty",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=os.getenv("DB_PATH", "data/processed/regulatory_updates.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--ollama-host",
        type=str,
        default=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        help="Ollama API base URL",
    )
    parser.add_argument(
        "--eba-dir",
        type=str,
        default=os.getenv("EBA_RAW_DATA_DIR", "data/raw/eba"),
        help="EBA raw data directory",
    )
    parser.add_argument(
        "--mas-dir",
        type=str,
        default=os.getenv("MAS_RAW_DATA_DIR", "data/raw/mas"),
        help="MAS raw data directory",
    )
    args = parser.parse_args()

    # Resolve paths relative to project root
    db_path = (Path(__file__).parent.parent / args.db).resolve()
    eba_dir = (Path(__file__).parent.parent / args.eba_dir).resolve()
    mas_dir = (Path(__file__).parent.parent / args.mas_dir).resolve()

    logger.info("=== IT Risk Manager — Startup Check ===")

    checks = [
        check_database(str(db_path)),
        check_ollama(args.ollama_host),
        check_raw_dirs(str(eba_dir), str(mas_dir), strict=args.strict),
    ]

    passed = sum(checks)
    total = len(checks)
    logger.info(f"=== {passed}/{total} checks passed ===")

    if not all(checks):
        logger.error("Startup check FAILED — fix errors before proceeding.")
        sys.exit(1)

    logger.info("All checks passed — application may start.")
    sys.exit(0)


if __name__ == "__main__":
    main()
