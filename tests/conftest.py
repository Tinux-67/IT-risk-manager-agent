"""
Shared pytest fixtures and configuration for the IT Risk Manager Agent test suite.
"""

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_db():
    """Provide a fresh in-memory SQLite database with the full schema."""
    conn = sqlite3.connect(":memory:")
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
        CREATE INDEX IF NOT EXISTS idx_source_urgency ON updates(source, urgency_level);
    """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def sample_update_row(in_memory_db):
    """Insert and return a single sample update row."""
    in_memory_db.execute("""
        INSERT INTO updates
            (title, source_url, file_path, publication_date, raw_text,
             summary, risk_area, urgency_level, source, is_processed)
        VALUES
            ('Test DORA Update', 'https://eba.europa.eu/test', '/tmp/test.html',
             '2024-01-01', 'Mandatory cybersecurity requirement under DORA.',
             'DORA requires immediate action.', 'Cybersecurity', 'High', 'EBA', 1)
    """)
    in_memory_db.commit()
    cursor = in_memory_db.cursor()
    cursor.execute("SELECT * FROM updates ORDER BY id DESC LIMIT 1")
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, cursor.fetchone()))


# ---------------------------------------------------------------------------
# Ollama mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_ollama_none():
    """Mock Ollama to return None (simulates unavailable LLM)."""
    with patch("scripts.llm_utils.get_ollama_response", return_value=None) as m:
        yield m


@pytest.fixture()
def mock_ollama_timeout():
    """Mock Ollama to raise a timeout error."""
    import requests
    with patch("scripts.llm_utils.get_ollama_response",
               side_effect=requests.exceptions.Timeout("Ollama timed out")) as m:
        yield m


@pytest.fixture()
def mock_ollama_connection_error():
    """Mock Ollama to raise a connection error."""
    import requests
    with patch("scripts.llm_utils.get_ollama_response",
               side_effect=requests.exceptions.ConnectionError("Ollama unreachable")) as m:
        yield m


@pytest.fixture()
def mock_ollama_value_error():
    """Mock Ollama to raise a ValueError (unexpected response format)."""
    with patch("scripts.llm_utils.get_ollama_response",
               side_effect=ValueError("Unexpected Ollama response")) as m:
        yield m


# ---------------------------------------------------------------------------
# HTML content fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_html_content():
    return """
<html><body>
<h1>EBA Regulatory Update on Cybersecurity Requirements</h1>
<p>Financial institutions must immediately implement mandatory cybersecurity controls.
This urgent requirement applies to all entities under DORA regulation.</p>
</body></html>
"""


@pytest.fixture()
def eba_html_file(tmp_path, sample_html_content):
    """Create a well-named EBA HTML file for process_file tests."""
    f = tmp_path / "20240101_120000_eba_cybersecurity_update.html"
    f.write_text(sample_html_content, encoding="utf-8")
    return str(f)
