#!/usr/bin/env python3
"""
Database backup script for IT Risk Manager Agent.

Creates a timestamped .tar.gz backup of the SQLite database in ./backups/.
Run manually or schedule via cron / GitHub Actions.

Usage:
    python scripts/backup_db.py [--backup-dir ./backups] [--keep 7]
"""

import argparse
import sqlite3
import tarfile
from datetime import datetime
from pathlib import Path

from loguru import logger

from config import Config
from scripts.logging_config import setup_logging

setup_logging()


def create_backup(backup_dir: Path, keep: int = 7) -> Path | None:
    """
    Create a timestamped .tar.gz backup of the SQLite database.

    Args:
        backup_dir: Directory to store backups.
        keep: Number of most recent backups to retain (older ones are deleted).

    Returns:
        Path to the created backup file, or None on failure.
    """
    db_path = Path(Config.DB_PATH)

    if not db_path.exists():
        logger.error(f"Database not found at {db_path}. Nothing to back up.")
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"regulatory_updates_{timestamp}.tar.gz"
    backup_path = backup_dir / backup_filename

    # Use SQLite's online backup API for a consistent snapshot
    tmp_copy = backup_dir / f"regulatory_updates_{timestamp}.db"
    try:
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(tmp_copy))
        src.backup(dst)
        dst.close()
        src.close()
        logger.debug(f"SQLite online backup written to {tmp_copy}")
    except Exception as e:
        logger.error(f"Failed to create SQLite snapshot: {e}")
        return None

    # Compress into .tar.gz
    try:
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(tmp_copy, arcname=tmp_copy.name)
        logger.success(f"Backup created: {backup_path} ({backup_path.stat().st_size} bytes)")
    except Exception as e:
        logger.error(f"Failed to compress backup: {e}")
        return None
    finally:
        tmp_copy.unlink(missing_ok=True)

    # Rotate old backups
    _rotate_backups(backup_dir, keep)

    return backup_path


def _rotate_backups(backup_dir: Path, keep: int) -> None:
    """Delete oldest backups, keeping only `keep` most recent."""
    backups = sorted(backup_dir.glob("regulatory_updates_*.tar.gz"))
    to_delete = backups[: max(0, len(backups) - keep)]
    for old in to_delete:
        old.unlink()
        logger.info(f"Removed old backup: {old.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup the IT Risk Manager Agent database.")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("backups"),
        help="Directory to store backups (default: ./backups).",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=7,
        help="Number of recent backups to keep (default: 7).",
    )
    args = parser.parse_args()

    logger.info(f"Starting database backup → {args.backup_dir}")
    result = create_backup(args.backup_dir, keep=args.keep)

    if result:
        print(f"✅ Backup saved: {result}")
    else:
        print("❌ Backup failed. Check logs for details.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
