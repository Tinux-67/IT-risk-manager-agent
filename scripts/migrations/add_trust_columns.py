#!/usr/bin/env python3
"""
Idempotent migration: add Trust layer columns to the regulatory_updates.db.

Adds:
  - updates.citation_sources   (TEXT)
  - updates.reasoning_chain    (TEXT)
  - updates.groundedness_score (REAL)
  - updates.chunk_count        (INTEGER)
  - raw_chunks table
  - schema_version table (records applied migrations)

Usage:
    python scripts/migrations/add_trust_columns.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Add project root to path so config.py imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

SCHEMA_VERSION = 2


def _get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(
        "PRAGMA table_info(:table)", {"table": table}
    ).fetchall()
    return column in {row["name"] for row in rows}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table",
        {"table": table},
    ).fetchall()
    return len(rows) > 0


def _get_schema_version(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "schema_version"):
        return 1  # Original schema before this migration
    row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
    return int(row["version"]) if row else 1


def _apply_migration(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    current_version = _get_schema_version(conn)
    if current_version >= SCHEMA_VERSION:
        logger.info(f"Schema already at version {current_version} — nothing to do.")
        return

    if dry_run:
        logger.info(f"[DRY RUN] Would apply migration to version {SCHEMA_VERSION}")
        return

    # ── Add columns to updates ────────────────────────────────────────────────
    new_columns = [
        ("citation_sources", "TEXT"),
        ("reasoning_chain", "TEXT"),
        ("groundedness_score", "REAL"),
        ("chunk_count", "INTEGER DEFAULT 0"),
    ]

    for col_name, col_type in new_columns:
        if not _column_exists(conn, "updates", col_name):
            logger.info(f"Adding column: updates.{col_name} {col_type}")
            conn.execute(f"ALTER TABLE updates ADD COLUMN {col_name} {col_type}")

    # ── Create raw_chunks table ───────────────────────────────────────────────
    if not _table_exists(conn, "raw_chunks"):
        logger.info("Creating table: raw_chunks")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_chunks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                update_id    INTEGER REFERENCES updates(id) ON DELETE CASCADE,
                chunk_text   TEXT    NOT null,
                char_start   INTEGER NOT null,
                char_end     INTEGER NOT null,
                source_file  TEXT    NOT null,
                chunk_index  INTEGER NOT null,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunk_update ON raw_chunks(update_id)"
        )

    # ── Record schema version ────────────────────────────────────────────────
    if not _table_exists(conn, "schema_version"):
        conn.execute("""
            CREATE TABLE schema_version (
                version     INTEGER PRIMARY KEY,
                applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.execute(
        "INSERT INTO schema_version (version) VALUES (:v)",
        {"v": SCHEMA_VERSION},
    )

    conn.commit()
    logger.info(f"Migration to v{SCHEMA_VERSION} complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add Trust layer columns")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be done, commit nothing"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/processed/regulatory_updates.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()

    # Resolve db path relative to project root
    db_path = (Path(__file__).parent.parent / args.db).resolve()

    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        sys.exit(1)

    logger.info(f"Connecting to {db_path}")
    conn = _get_connection(db_path)
    try:
        _apply_migration(conn, dry_run=args.dry_run)
    finally:
        conn.close()

    if args.dry_run:
        logger.info("Dry run complete — no changes written.")
    else:
        logger.info("Migration complete.")


if __name__ == "__main__":
    main()
