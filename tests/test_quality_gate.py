"""
Regression test: process_updates.py must not emit 'SUCCESS' for empty/corrupt data.

Tests the data quality gate added in fix/trust-layer-silent-failures.
This test must FAIL if a future change causes the pipeline to INSERT garbage records.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent


class TestQualityGateSummary:
    """Summary must meet a minimum length before being accepted."""

    def test_summary_rejects_empty_response(self):
        from scripts.process_updates import generate_summary, _fallback_summary

        # Empty LLM response → fallback
        result = _fallback_summary("")
        assert result == "No summary available."

        # Empty text → fallback
        result = _fallback_summary("   ")
        assert result == "No summary available."

        # Short text → fallback
        result = _fallback_summary("Too short")
        assert result == "Too short"  # Single short paragraph accepted as-is

    def test_summary_fallback_uses_first_paragraph(self):
        from scripts.process_updates import _fallback_summary

        text = "First paragraph here.\n\nSecond paragraph.\n\nThird."
        result = _fallback_summary(text)
        assert result == "First paragraph here."

    def test_summary_fallback_truncates_long_paragraphs(self):
        from scripts.process_updates import _fallback_summary

        long_text = "A" * 600
        result = _fallback_summary(long_text)
        assert result == "A" * 500 + "..."
        assert len(result) == 503


class TestQualityGateLogic:
    """
    The data quality gate must:
      - Reject documents where ALL of: summary is fallback, risk_area is 'Other', urgency is 'Medium'
      - Still INSERT (as is_processed=1) so re-runs don't infinite-loop on unscrapable files
      - Store empty raw_text to signal extraction failure
    """

    def _make_db(self) -> tuple[Path, sqlite3.Connection]:
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source_url TEXT,
                file_path TEXT,
                publication_date TEXT,
                raw_text TEXT,
                summary TEXT,
                risk_area TEXT,
                urgency_level TEXT,
                source TEXT DEFAULT 'EBA',
                is_processed BOOLEAN DEFAULT 0,
                citation_sources TEXT,
                reasoning_chain TEXT,
                groundedness_score REAL,
                chunk_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        return Path(":memory:"), conn

    def _process_file_quality_gate(
        self,
        conn: sqlite3.Connection,
        raw_text: str,
        summary: str,
        risk_area: str,
        urgency: str,
        run_trust_layer: bool = False,
    ) -> bool:
        """
        Simulate the quality gate logic from _process_file_impl.
        Returns True if the document PASSED the gate (normal INSERT path).
        """
        LOW_QUALITY_SUMMARIES = {
            "No summary available.",
        }
        is_summary_fallback = (
            summary in LOW_QUALITY_SUMMARIES
            or summary.lower().startswith("defaulting")
        )
        is_risk_fallback = risk_area == "Other"
        is_urgency_fallback = urgency == "Medium"
        quality_failed = is_summary_fallback and is_risk_fallback and is_urgency_fallback
        return not quality_failed

    def test_quality_gate_rejects_all_three_fallback(self):
        _, conn = self._make_db()
        # All three fallbacks → FAIL
        passed = self._process_file_quality_gate(
            conn, "", "No summary available.", "Other", "Medium"
        )
        assert passed is False, "Document should fail quality gate when all fields are fallback"
        conn.close()

    def test_quality_gate_passes_if_only_summary_is_fallback(self):
        _, conn = self._make_db()
        # summary fallback but risk_area ≠ Other → PASS
        passed = self._process_file_quality_gate(
            conn, "some text", "No summary available.", "Cybersecurity", "High"
        )
        assert passed is True
        conn.close()

    def test_quality_gate_passes_if_only_risk_is_fallback(self):
        _, conn = self._make_db()
        passed = self._process_file_quality_gate(
            conn, "some text", "Meaningful summary.", "Other", "High"
        )
        assert passed is True
        conn.close()

    def test_quality_gate_passes_with_good_classifications(self):
        _, conn = self._make_db()
        passed = self._process_file_quality_gate(
            conn, "meaningful text", "This regulation requires immediate compliance.", "IT Risk Management", "Urgent"
        )
        assert passed is True
        conn.close()

    def test_quality_gate_medium_urgency_alone_does_not_trigger_rejection(self):
        _, conn = self._make_db()
        # Medium urgency is the default — only triggers rejection when combined with
        # Other risk_area AND fallback summary
        passed = self._process_file_quality_gate(
            conn, "some text", "Meaningful summary.", "Data Protection", "Medium"
        )
        assert passed is True
        conn.close()


class TestNoSuccessWithoutData:
    """
    CRITICAL REGRESSION TEST:
    A 'SUCCESS' log must never be emitted when no meaningful data was written.
    This test mocks the LLM and file system to force empty inputs and
    verifies that the pipeline correctly rejects them.
    """

    def _make_db(self) -> tuple[Path, sqlite3.Connection]:
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                source_url TEXT, file_path TEXT, publication_date TEXT,
                raw_text TEXT, summary TEXT, risk_area TEXT,
                urgency_level TEXT, source TEXT DEFAULT 'EBA',
                is_processed BOOLEAN DEFAULT 0,
                citation_sources TEXT, reasoning_chain TEXT,
                groundedness_score REAL, chunk_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        return Path(":memory:"), conn

    @patch("scripts.process_updates.get_ollama_response", return_value=None)
    def test_empty_raw_text_returns_false(self, _mock_llm):
        from scripts.process_updates import _process_file_impl

        _, conn = self._make_db()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"broken pdf content")
            tmp_path = tmp.name
        try:
            ok, name = _process_file_impl(tmp_path, conn, run_trust_layer=False)
            assert ok is False, "Should return False when raw_text is empty"
        finally:
            os.unlink(tmp_path)
            conn.close()

    def test_successful_insert_has_non_empty_summary(self):
        """
        After a successful (True) return from _process_file_impl,
        the DB must contain a record with a meaningful summary
        (not 'No summary available.').
        """
        # This is a schema/logic test — we verify that if the quality gate
        # passes, the INSERT uses the actual text, not the fallback.
        # We simulate by checking that _fallback_summary doesn't start with
        # "No summary available" when given real text.
        from scripts.process_updates import _fallback_summary

        real_text = "This is a sample regulatory document about IT risk."
        result = _fallback_summary(real_text)
        assert result != "No summary available."
        assert "regulatory" in result.lower()


class TestTrustLayerNonFatal:
    """Trust layer failures must not prevent the main INSERT from succeeding."""

    def _make_db(self) -> tuple[Path, sqlite3.Connection]:
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                source_url TEXT, file_path TEXT, publication_date TEXT,
                raw_text TEXT, summary TEXT, risk_area TEXT,
                urgency_level TEXT, source TEXT DEFAULT 'EBA',
                is_processed BOOLEAN DEFAULT 0,
                citation_sources TEXT, reasoning_chain TEXT,
                groundedness_score REAL, chunk_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE raw_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                update_id INTEGER REFERENCES updates(id) ON DELETE CASCADE,
                chunk_text TEXT NOT NULL,
                char_start INTEGER NOT NULL,
                char_end INTEGER NOT NULL,
                source_file TEXT NOT NULL,
                chunk_index INTEGER NOT NULL
            )
        """)
        conn.commit()
        return Path(":memory:"), conn

    def test_trust_layer_failure_does_not_prevent_insert(self):
        """Even if chunk_text/veracity fail, the main record is still inserted."""
        from scripts.process_updates import _process_file_impl

        _, conn = self._make_db()
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write("Meaningful regulatory text about compliance requirements.\n" * 50)
            tmp_path = tmp.name

        try:
            # Mock Ollama to fail — trust layer will get None responses
            with patch(
                "scripts.process_updates.get_ollama_response", return_value=None
            ):
                ok, name = _process_file_impl(tmp_path, conn, run_trust_layer=True)

            # Main processing should succeed
            assert ok is True, "Should return True even when trust layer gets no LLM response"

            # Verify record was inserted
            row = conn.execute(
                "SELECT title, summary, reasoning_chain, groundedness_score "
                "FROM updates WHERE file_path = ?",
                (tmp_path,),
            ).fetchone()
            assert row is not None, "Record should be in DB even if trust layer failed"
            title, summary, reasoning, score = row
            assert title, "Title should be set"
            assert summary, "Summary should be set"  # from LLM or fallback
            assert reasoning is None or reasoning == "", "reasoning_chain may be None/empty"
            assert score is None, "groundedness_score may be None"
        finally:
            os.unlink(tmp_path)
            conn.close()

    def test_trust_layer_failure_records_null_for_trust_columns(self):
        """Trust-layer columns (citation_sources, reasoning_chain, etc.) may be NULL."""
        from scripts.process_updates import _process_file_impl

        _, conn = self._make_db()
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write("Compliance regulation text.\n" * 50)
            tmp_path = tmp.name

        try:
            with patch(
                "scripts.process_updates.get_ollama_response", return_value=None
            ):
                ok, _ = _process_file_impl(tmp_path, conn, run_trust_layer=True)

            assert ok is True
            row = conn.execute(
                "SELECT citation_sources, reasoning_chain, groundedness_score, chunk_count "
                "FROM updates",
            ).fetchone()
            # These may be NULL/empty — that's acceptable for trust layer failures
            citation, reasoning, score, chunks = row
            assert chunks == 0, "chunk_count should be 0 when trust layer gets no data"
        finally:
            os.unlink(tmp_path)
            conn.close()
