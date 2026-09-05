"""Tests for the citation pipeline (chunking + retrieval + JSON parsing)."""

import json
import sqlite3
from pathlib import Path

import pytest

# Module under test
from scripts.retrieval import (
    CHUNK_WORD_OVERLAP,
    CHUNK_WORD_SIZE,
    _naive_retrieve,
    _tokenise,
    chunk_text,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_temp_db() -> tuple[Path, sqlite3.Connection]:
    """Create an in-memory SQLite DB with the full schema."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT DEFAULT 'EBA',
            is_processed BOOLEAN DEFAULT 0
        );
        INSERT INTO updates (id, title, is_processed) VALUES (1, 'Test Doc', 1);

        CREATE TABLE raw_chunks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            update_id    INTEGER REFERENCES updates(id) ON DELETE CASCADE,
            chunk_text   TEXT    NOT NULL,
            char_start   INTEGER NOT NULL,
            char_end     INTEGER NOT NULL,
            source_file  TEXT    NOT NULL,
            chunk_index  INTEGER NOT NULL
        );
    """)
    conn.commit()
    return Path(":memory:"), conn


# ── Tokenisation ──────────────────────────────────────────────────────────────


class TestTokenise:
    def test_lower_cases(self):
        assert _tokenise("Hello WORLD") == ["hello", "world"]

    def test_non_alnum_split(self):
        assert _tokenise("hello-world foo.bar") == ["hello", "world", "foo", "bar"]

    def test_empty(self):
        assert _tokenise("") == []


# ── Chunking ──────────────────────────────────────────────────────────────────


class TestChunkText:
    def _do_chunk(self, raw_text: str) -> list[dict]:
        _, conn = make_temp_db()
        chunks = chunk_text(raw_text, "eba/test.pdf", update_id=1, conn=conn)
        conn.close()
        return chunks

    def test_empty_text_returns_empty_list(self):
        assert self._do_chunk("") == []
        assert self._do_chunk("   \n\n  ") == []

    def test_chunk_word_size(self):
        words = " ".join(f"word{i}" for i in range(600))
        chunks = self._do_chunk(words)
        for ch in chunks:
            assert len(ch["chunk_text"].split()) <= CHUNK_WORD_SIZE

    def test_overlap_between_chunks(self):
        long_text = " ".join(f"word{i}" for i in range(CHUNK_WORD_SIZE + CHUNK_WORD_OVERLAP + 10))
        chunks = self._do_chunk(long_text)
        assert len(chunks) >= 2
        # Second chunk should contain the last N words of the first chunk (overlap)
        first_last_words = chunks[0]["chunk_text"].split()[-CHUNK_WORD_OVERLAP:]
        second_first_words = chunks[1]["chunk_text"].split()[:CHUNK_WORD_OVERLAP]
        assert first_last_words == second_first_words

    def test_stores_update_id_and_source(self):
        chunks = self._do_chunk("word0 word1 word2")
        assert len(chunks) == 1
        assert chunks[0]["update_id"] == 1
        assert chunks[0]["source_file"] == "eba/test.pdf"

    def test_re_chunk_deletes_old_chunks(self):
        _, conn = make_temp_db()
        chunk_text("first set of words", "eba/test.pdf", update_id=1, conn=conn)
        assert conn.execute("SELECT COUNT(*) FROM raw_chunks WHERE update_id=1").fetchone()[0] == 1
        chunk_text("second set of words that is longer and different", "eba/test.pdf", update_id=1, conn=conn)
        # After re-chunking, only new chunks remain
        assert conn.execute("SELECT COUNT(*) FROM raw_chunks WHERE update_id=1").fetchone()[0] == 1
        conn.close()


# ── Naive Retrieval ───────────────────────────────────────────────────────────


class TestNaiveRetrieve:
    def _do_retrieve(self, chunks: list[dict], query: str, top_k: int = 3) -> list[dict]:
        _, conn = make_temp_db()
        result = _naive_retrieve(chunks, query, top_k)
        conn.close()
        return result

    def test_returns_top_k(self):
        chunks = [
            {"chunk_text": "apple banana apple", "chunk_index": 0},
            {"chunk_text": "banana cherry", "chunk_index": 1},
            {"chunk_text": "cherry date", "chunk_index": 2},
        ]
        result = self._do_retrieve(chunks, "apple banana", top_k=2)
        assert len(result) <= 2

    def test_query_word_overlap_scoring(self):
        chunks = [
            {"chunk_text": "regulatory compliance DORA", "chunk_index": 0},
            {"chunk_text": "random unrelated text", "chunk_index": 1},
        ]
        result = self._do_retrieve(chunks, "DORA compliance", top_k=2)
        assert result[0]["chunk_index"] == 0

    def test_empty_chunks(self):
        assert self._do_retrieve([], "anything") == []


# ── JSON Parsing (canned examples) ───────────────────────────────────────────


class TestReasoningChainParsing:
    """Unit tests for the JSON parsing logic that lives inside process_updates.py."""

    @staticmethod
    def _parse_reasoning(raw_response: str) -> tuple[str, list]:
        """Mirrors the JSON-extraction logic in process_updates.py."""
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```", 2)
            if len(parts) >= 2:
                content_part = parts[1]
                if "\n" in content_part:
                    cleaned = content_part.split("\n", 1)[1]
        parsed = json.loads(cleaned)
        reasoning = parsed.get("reasoning", "")
        cited = parsed.get("cited_chunks", [])
        return reasoning, cited

    def test_clean_json(self):
        raw = '{"reasoning": "High urgency due to deadline.", "cited_chunks": []}'
        r, c = self._parse_reasoning(raw)
        assert r == "High urgency due to deadline."
        assert c == []

    def test_json_with_cited_chunks(self):
        raw = '{"reasoning": "Relevant to IT Risk.", "cited_chunks": [{"chunk_text": "art. 5", "char_start": 10, "char_end": 20, "source_file": "eba/foo.pdf"}]}'
        r, c = self._parse_reasoning(raw)
        assert r == "Relevant to IT Risk."
        assert len(c) == 1
        assert c[0]["chunk_text"] == "art. 5"

    def test_markdown_fenced_json(self):
        raw = '```json\n{"reasoning": "Compliance required.", "cited_chunks": []}\n```'
        r, c = self._parse_reasoning(raw)
        assert r == "Compliance required."

    def test_malformed_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            self._parse_reasoning("this is not json at all")

    def test_missing_keys_use_defaults(self):
        raw = '{"reasoning": "Only reasoning field."}'
        r, c = self._parse_reasoning(raw)
        assert r == "Only reasoning field."
        assert c == []  # defaults to empty list

    def test_truncated_json_in_fence(self):
        """Handles the case where the LLM returns a truncated markdown fence."""
        raw = '```json\n{"reasoning": "partial'
        with pytest.raises(json.JSONDecodeError):
            self._parse_reasoning(raw)


# ── Migration idempotency ─────────────────────────────────────────────────────


class TestMigrationIdempotent:
    def test_add_trust_columns_idempotent(self, tmp_path: Path):
        # Create a minimal DB at the old schema
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE updates (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT
            )
        """)
        conn.execute("INSERT INTO updates (title) VALUES ('old record')")
        conn.commit()
        conn.close()

        # Apply migration twice
        from scripts.migrations.add_trust_columns import _apply_migration

        for _ in range(2):
            conn2 = sqlite3.connect(str(db_path))
            _apply_migration(conn2, dry_run=False)
            conn2.close()

        # Verify columns exist
        conn3 = sqlite3.connect(str(db_path))
        cols = [r[1] for r in conn3.execute("PRAGMA table_info(updates)").fetchall()]
        conn3.close()
        for col in ("citation_sources", "reasoning_chain", "groundedness_score", "chunk_count"):
            assert col in cols, f"{col} missing"

    def test_schema_version_recorded(self, tmp_path: Path):
        from scripts.migrations.add_trust_columns import SCHEMA_VERSION, _apply_migration

        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE updates (id INTEGER PRIMARY KEY)")
        conn.close()

        conn = sqlite3.connect(str(db_path))
        _apply_migration(conn, dry_run=False)
        conn.close()

        conn = sqlite3.connect(str(db_path))
        version = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()[0]
        conn.close()
        assert version == SCHEMA_VERSION
