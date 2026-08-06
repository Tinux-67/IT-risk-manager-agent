"""
Integration tests for the IT Risk Manager Agent.
Tests the full E2E pipeline: file ingestion → SQLite → alert generation.

Milestone 3 — test_integration.py
"""

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from scripts.generate_alerts import format_alert, get_updates_since_days
from scripts.process_updates import (
    assess_urgency,
    categorize_risk_area,
    init_db,
    process_file,
    process_files_parallel,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

HTML_CONTENT = """
<html><body>
<h1>EBA Regulatory Update on Cybersecurity Requirements</h1>
<p>Financial institutions must immediately implement mandatory cybersecurity controls.
This urgent requirement applies to all entities under DORA regulation.
Compliance failure will result in enforcement action without delay.</p>
<p>The regulation is mandatory and shall be implemented by Q1 2025.</p>
</body></html>
"""


@pytest.fixture()
def tmp_db(tmp_path):
    """Return a fresh SQLite connection backed by a temp file."""
    db_path = tmp_path / "test.db"
    original = Config.DB_PATH
    Config.DB_PATH = db_path
    conn = sqlite3.connect(str(db_path))
    # Bootstrap schema
    _bootstrap_schema(conn)
    yield conn
    conn.close()
    Config.DB_PATH = original


def _bootstrap_schema(conn: sqlite3.Connection) -> None:
    """Create the same schema as init_db() but on the given connection."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source_url TEXT,
            file_path TEXT,
            publication_date TEXT,
            processed_date TEXT DEFAULT CURRENT_TIMESTAMP,
            raw_text TEXT,
            summary TEXT,
            risk_area TEXT,
            urgency_level TEXT,
            source TEXT DEFAULT 'EBA',
            is_processed BOOLEAN DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS ollama_cache (
            cache_key TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_publication_date ON updates(publication_date);
        CREATE INDEX IF NOT EXISTS idx_risk_area ON updates(risk_area);
        CREATE INDEX IF NOT EXISTS idx_urgency ON updates(urgency_level);
        CREATE INDEX IF NOT EXISTS idx_is_processed ON updates(is_processed);
        CREATE INDEX IF NOT EXISTS idx_source ON updates(source);
        CREATE INDEX IF NOT EXISTS idx_source_risk_area ON updates(source, risk_area);
    """)
    conn.commit()


@pytest.fixture()
def eba_html_file(tmp_path):
    """Create a well-named EBA HTML file that process_file can parse."""
    f = tmp_path / "20240101_120000_eba_cybersecurity_update.html"
    f.write_text(HTML_CONTENT, encoding="utf-8")
    return str(f)


# ---------------------------------------------------------------------------
# 1. E2E Workflow
# ---------------------------------------------------------------------------


class TestE2EWorkflow:
    """Full pipeline: HTML file → process_file() → DB → format_alert()."""

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_process_and_alert(self, _mock_llm, tmp_db, eba_html_file):
        success, filename = process_file(eba_html_file, tmp_db)

        assert success is True, f"process_file failed for {filename}"

        cursor = tmp_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM updates WHERE is_processed = 1")
        assert cursor.fetchone()[0] == 1

        updates = get_updates_since_days(tmp_db, days=365 * 10)
        assert len(updates) == 1

        update = updates[0]
        assert update["title"]
        # source is not included in get_updates_since_days SELECT — verify via direct query
        cursor.execute("SELECT source FROM updates LIMIT 1")
        assert cursor.fetchone()[0] == "EBA"

        alert = format_alert(update, "workfloor", use_llm=False, conn=tmp_db)
        assert "WORKFLOOR" in alert.upper() or "workfloor" in alert.lower()
        assert update["title"] in alert or "Title" in alert

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_publication_date_parsed(self, _mock_llm, tmp_db, eba_html_file):
        process_file(eba_html_file, tmp_db)
        cursor = tmp_db.cursor()
        cursor.execute("SELECT publication_date FROM updates LIMIT 1")
        date = cursor.fetchone()[0]
        assert date and date != "Unknown", f"Date not parsed: {date}"


# ---------------------------------------------------------------------------
# 2. Multi-source
# ---------------------------------------------------------------------------


class TestMultiSource:
    """EBA and MAS files should get the correct source tag."""

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_eba_source_tag(self, _mock_llm, tmp_db, tmp_path):
        f = tmp_path / "20240101_120000_eba_update.html"
        f.write_text(HTML_CONTENT, encoding="utf-8")
        success, _ = process_file(str(f), tmp_db)
        assert success
        cursor = tmp_db.cursor()
        cursor.execute("SELECT source FROM updates LIMIT 1")
        assert cursor.fetchone()[0] == "EBA"

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_mas_source_tag(self, _mock_llm, tmp_db, tmp_path):
        f = tmp_path / "20240201_080000_mas_regulatory_notice.html"
        f.write_text(HTML_CONTENT, encoding="utf-8")
        success, _ = process_file(str(f), tmp_db)
        assert success
        cursor = tmp_db.cursor()
        cursor.execute("SELECT source FROM updates LIMIT 1")
        assert cursor.fetchone()[0] == "MAS"

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_both_sources_stored(self, _mock_llm, tmp_db, tmp_path):
        for prefix in ("eba", "mas"):
            f = tmp_path / f"20240101_120000_{prefix}_notice.html"
            f.write_text(HTML_CONTENT, encoding="utf-8")
            process_file(str(f), tmp_db)

        cursor = tmp_db.cursor()
        cursor.execute("SELECT DISTINCT source FROM updates ORDER BY source")
        sources = {row[0] for row in cursor.fetchall()}
        assert "EBA" in sources
        assert "MAS" in sources


# ---------------------------------------------------------------------------
# 3. Ollama fallback
# ---------------------------------------------------------------------------


class TestOllamaFallback:
    """When LLM returns None, keyword matching and first-paragraph summary apply."""

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_categorize_fallback(self, _mock_llm):
        result = categorize_risk_area("This document covers cybersecurity controls.")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_urgency_fallback_urgent(self, _mock_llm):
        result = assess_urgency("This is an urgent requirement with immediate deadline.")
        assert result == "Urgent"

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_urgency_fallback_high(self, _mock_llm):
        result = assess_urgency("This is a mandatory regulation that shall be implemented.")
        assert result == "High"

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_urgency_fallback_medium(self, _mock_llm):
        result = assess_urgency("General guidance on risk practices.")
        assert result == "Medium"

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_process_file_without_llm(self, _mock_llm, tmp_db, eba_html_file):
        success, _ = process_file(eba_html_file, tmp_db)
        assert success
        cursor = tmp_db.cursor()
        cursor.execute("SELECT risk_area, urgency_level, summary FROM updates LIMIT 1")
        row = cursor.fetchone()
        assert row[0]  # risk_area not empty
        assert row[1]  # urgency_level not empty
        assert row[2]  # summary not empty


# ---------------------------------------------------------------------------
# 4. Alert audiences
# ---------------------------------------------------------------------------


class TestAlertAudiences:
    """Each audience produces a distinct header."""

    @pytest.fixture()
    def sample_update(self, tmp_db):
        tmp_db.execute("""
            INSERT INTO updates
                (title, source_url, file_path, publication_date, raw_text,
                 summary, risk_area, urgency_level, source, is_processed)
            VALUES
                ('Test DORA Update', '', '/tmp/test.html', '2024-01-01',
                 'Mandatory cybersecurity requirement under DORA regulation.',
                 'DORA requires immediate action.', 'Cybersecurity', 'High', 'EBA', 1)
        """)
        tmp_db.commit()
        updates = get_updates_since_days(tmp_db, days=365 * 10)
        assert updates
        return updates[0]

    def test_workfloor_alert(self, sample_update, tmp_db):
        alert = format_alert(sample_update, "workfloor", use_llm=False, conn=tmp_db)
        assert "WORKFLOOR" in alert.upper() or "workfloor" in alert.lower()

    def test_management_alert(self, sample_update, tmp_db):
        alert = format_alert(sample_update, "management", use_llm=False, conn=tmp_db)
        assert "MANAGEMENT" in alert.upper() or "management" in alert.lower()

    def test_clevel_alert(self, sample_update, tmp_db):
        alert = format_alert(sample_update, "c-level", use_llm=False, conn=tmp_db)
        assert "C-LEVEL" in alert.upper() or "c-level" in alert.lower()

    def test_all_alerts_contain_title(self, sample_update, tmp_db):
        for audience in ("workfloor", "management", "c-level"):
            alert = format_alert(sample_update, audience, use_llm=False, conn=tmp_db)
            assert "Test DORA Update" in alert or sample_update["title"] in alert


# ---------------------------------------------------------------------------
# 5. Parallel processing
# ---------------------------------------------------------------------------


class TestParallelProcessing:
    """process_files_parallel processes multiple files with per-thread connections."""

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_three_files_parallel(self, _mock_llm, tmp_db, tmp_path):
        files = []
        for i in range(3):
            f = tmp_path / f"2024010{i+1}_120000_eba_doc{i}.html"
            f.write_text(
                f"<html><body><p>Regulatory document {i}: cybersecurity mandatory.</p></body></html>",
                encoding="utf-8",
            )
            files.append(str(f))

        results = process_files_parallel(files, tmp_db, max_workers=2)

        assert len(results) == 3

        # Check DB via a fresh connection (parallel workers use Config.DB_PATH)
        check_conn = sqlite3.connect(str(Config.DB_PATH))
        cursor = check_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM updates WHERE is_processed = 1")
        count = cursor.fetchone()[0]
        check_conn.close()

        assert count == 3, f"Expected 3 records, got {count}"

    @patch("scripts.llm_utils.get_ollama_response", return_value=None)
    def test_parallel_results_dict(self, _mock_llm, tmp_db, tmp_path):
        files = []
        for i in range(2):
            f = tmp_path / f"20240101_12000{i}_eba_doc.html"
            f.write_text("<html><body><p>Cybersecurity mandatory regulation.</p></body></html>")
            files.append(str(f))

        results = process_files_parallel(files, tmp_db, max_workers=2)
        assert isinstance(results, dict)
        assert all(isinstance(v, bool) for v in results.values())


# ---------------------------------------------------------------------------
# 6. DB Schema
# ---------------------------------------------------------------------------


class TestDBSchema:
    """init_db() is idempotent and creates the expected schema."""

    def test_init_db_idempotent(self, tmp_path):
        Config.DB_PATH = tmp_path / "schema_test.db"
        conn1 = init_db()
        conn1.close()
        conn2 = init_db()  # second call — must not raise
        conn2.close()

    def test_required_tables_exist(self, tmp_path):
        Config.DB_PATH = tmp_path / "schema_test2.db"
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "updates" in tables
        assert "metadata" in tables
        assert "ollama_cache" in tables

    def test_required_indexes_exist(self, tmp_path):
        Config.DB_PATH = tmp_path / "schema_test3.db"
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()
        expected = {
            "idx_publication_date",
            "idx_risk_area",
            "idx_urgency",
            "idx_is_processed",
            "idx_source",
            "idx_source_risk_area",
            "idx_source_urgency",
        }
        missing = expected - indexes
        assert not missing, f"Missing indexes: {missing}"

    def test_updates_table_columns(self, tmp_path):
        Config.DB_PATH = tmp_path / "schema_test4.db"
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(updates)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        required = {
            "id",
            "title",
            "source_url",
            "file_path",
            "publication_date",
            "raw_text",
            "summary",
            "risk_area",
            "urgency_level",
            "source",
            "is_processed",
        }
        assert required.issubset(columns), f"Missing columns: {required - columns}"
