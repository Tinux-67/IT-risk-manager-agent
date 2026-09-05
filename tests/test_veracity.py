"""Tests for the veracity / groundedness scoring module."""

import sqlite3
from pathlib import Path

import pytest

from scripts.veracity import _parse_score, score_groundedness

# ── Score Parsing ─────────────────────────────────────────────────────────────


class TestParseScore:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("0.9", 0.9),
            ("0.75", 0.75),
            ("1.0", 1.0),
            ("0.0", 0.0),
            ("0.5", 0.5),
            ("  0.8  ", 0.8),
            # Edge cases
            ("0.85 is the score", 0.85),
            ("Score:0.72", 0.72),
            # bare 0 is parsed as 0.0 (valid score)
            ("0", 0.0),
            # Negative numbers are rejected
            ("-0.3", None),
            ("-1.0", None),
        ],
    )
    def test_valid_scores(self, raw: str, expected: float):
        assert _parse_score(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "not a number at all",
            "high",
            "",
            "point seven",
            "zero point five",
        ],
    )
    def test_invalid_scores_return_none(self, raw: str):
        assert _parse_score(raw) is None


# ── Caching ───────────────────────────────────────────────────────────────────


class TestVeracityCaching:
    def _make_db(self) -> tuple[Path, sqlite3.Connection]:
        """Minimal in-memory DB with ollama_cache table."""
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE ollama_cache (
                cache_key  TEXT PRIMARY KEY,
                model      TEXT NOT NULL,
                prompt     TEXT NOT NULL,
                response   TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at  TIMESTAMP
            )
        """)
        conn.commit()
        return Path(":memory:"), conn

    def test_caches_result(self, tmp_path: Path):
        db_path = tmp_path / "veracity.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE ollama_cache (
                cache_key  TEXT PRIMARY KEY,
                model      TEXT NOT NULL,
                prompt     TEXT NOT NULL,
                response   TEXT NOT NULL,
                expires_at  TIMESTAMP
            )
        """)

        # No Ollama available — this will return 0.5 (default) but should cache it
        score1 = score_groundedness(
            cited_text="The regulation requires immediate compliance by March 2024.",
            summary="The regulation requires compliance by March 2024.",
            conn=conn,
        )

        # Second call should hit the cache (and still return 0.5 since nothing is cached with a real score)
        score2 = score_groundedness(
            cited_text="The regulation requires immediate compliance by March 2024.",
            summary="The regulation requires compliance by March 2024.",
            conn=conn,
        )

        assert score1 == score2

        # Verify cache entry was written
        rows = conn.execute("SELECT COUNT(*) FROM ollama_cache").fetchone()[0]
        assert rows >= 1, f"Expected at least one cache entry, got {rows}"
        conn.close()


# ── Score Range ────────────────────────────────────────────────────────────────


class TestScoreRange:
    """Veracity scores must always fall within [0.0, 1.0]."""

    def test_score_always_in_range(self, tmp_path: Path):
        db_path = tmp_path / "range.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE ollama_cache (
                cache_key  TEXT PRIMARY KEY,
                model      TEXT NOT NULL,
                prompt     TEXT NOT NULL,
                response   TEXT NOT NULL,
                expires_at  TIMESTAMP
            )
        """)

        score = score_groundedness(
            cited_text="Banks must hold Tier 1 capital of at least 6%.",
            summary="Banks must hold Tier 1 capital of at least 6%.",
            conn=conn,
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0, f"Score {score} outside valid range [0.0, 1.0]"
        conn.close()
