"""
Tests for generate_alerts.py module.
"""

import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_alerts import (
    get_updates_since_days,
    format_alert,
)


@pytest.fixture
def temp_db_with_data():
    """Fixture to create a temporary database with sample data."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE updates (
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
            is_processed BOOLEAN DEFAULT 0
        )
    """)

    # Insert sample data with dates that are guaranteed to be within the test range
    # Use dates relative to today to avoid time-sensitive test failures
    today = datetime.now().strftime("%Y-%m-%d")
    one_day_ago = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    five_days_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    ten_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    sample_updates = [
        {
            "title": "Test Update 1",
            "source_url": "http://example.com/1",
            "file_path": "/data/raw/eba/test1.pdf",
            "publication_date": one_day_ago,
            "raw_text": "This is a test update about IT Risk Management.",
            "summary": "Test summary 1",
            "risk_area": "IT Risk Management",
            "urgency_level": "High",
            "is_processed": 1,
        },
        {
            "title": "Test Update 2",
            "source_url": "http://example.com/2",
            "file_path": "/data/raw/eba/test2.pdf",
            "publication_date": five_days_ago,
            "raw_text": "This is another test update about Cybersecurity.",
            "summary": "Test summary 2",
            "risk_area": "Cybersecurity",
            "urgency_level": "Urgent",
            "is_processed": 1,
        },
        {
            "title": "Test Update 3",
            "source_url": "http://example.com/3",
            "file_path": "/data/raw/eba/test3.pdf",
            "publication_date": ten_days_ago,
            "raw_text": "This is an old test update.",
            "summary": "Test summary 3",
            "risk_area": "Compliance",
            "urgency_level": "Medium",
            "is_processed": 1,
        },
    ]

    for update in sample_updates:
        cursor.execute("""
            INSERT INTO updates (
                title, source_url, file_path, publication_date, 
                raw_text, summary, risk_area, urgency_level, is_processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            update["title"],
            update["source_url"],
            update["file_path"],
            update["publication_date"],
            update["raw_text"],
            update["summary"],
            update["risk_area"],
            update["urgency_level"],
            update["is_processed"],
        ))

    conn.commit()
    yield conn
    conn.close()


class TestGetUpdatesSinceDays:
    """Tests for get_updates_since_days function."""

    def test_get_updates_since_days_all(self, temp_db_with_data):
        """Test getting all updates."""
        updates = get_updates_since_days(temp_db_with_data, days=365)
        assert len(updates) == 3

    def test_get_updates_since_days_recent(self, temp_db_with_data):
        """Test getting recent updates (last 2 days)."""
        updates = get_updates_since_days(temp_db_with_data, days=2)
        # Should get updates from 1 day ago (update 1)
        assert len(updates) >= 1

    def test_get_updates_since_days_none(self, temp_db_with_data):
        """Test getting updates with no results."""
        updates = get_updates_since_days(temp_db_with_data, days=0)
        assert len(updates) == 0


class TestFormatAlert:
    """Tests for format_alert function."""

    def test_format_alert_workfloor_with_llm(self, temp_db_with_data):
        """Test formatting a workfloor alert with LLM."""
        cursor = temp_db_with_data.cursor()
        cursor.execute("SELECT * FROM updates WHERE title = 'Test Update 1'")
        update = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))

        with patch('scripts.generate_alerts.generate_llm_summary') as mock_summary:
            with patch('scripts.generate_alerts.generate_llm_key_takeaways') as mock_takeaways:
                mock_summary.return_value = "Test summary"
                mock_takeaways.return_value = "- Takeaway 1\n- Takeaway 2"

                alert = format_alert(update, "workfloor", use_llm=True)

                assert "WORKFLOOR ALERT" in alert
                assert "Test Update 1" in alert
                assert "IT Risk Management" in alert
                assert "High" in alert
                assert "Test summary" in alert

    def test_format_alert_management_with_llm(self, temp_db_with_data):
        """Test formatting a management alert with LLM."""
        cursor = temp_db_with_data.cursor()
        cursor.execute("SELECT * FROM updates WHERE title = 'Test Update 2'")
        update = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))

        with patch('scripts.generate_alerts.generate_llm_business_impact') as mock_impact:
            with patch('scripts.generate_alerts.generate_llm_risk_assessment') as mock_risk:
                mock_impact.return_value = "- Impact 1"
                mock_risk.return_value = "- **Risk Level**: Urgent"

                alert = format_alert(update, "management", use_llm=True)

                assert "MANAGEMENT ALERT" in alert
                assert "Test Update 2" in alert
                assert "Cybersecurity" in alert
                assert "Urgent" in alert

    def test_format_alert_c_level_with_llm(self, temp_db_with_data):
        """Test formatting a C-level alert with LLM."""
        cursor = temp_db_with_data.cursor()
        cursor.execute("SELECT * FROM updates WHERE title = 'Test Update 1'")
        update = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))

        with patch('scripts.generate_alerts.generate_llm_executive_summary') as mock_summary:
            with patch('scripts.generate_alerts.generate_llm_strategic_implications') as mock_implications:
                with patch('scripts.generate_alerts.generate_llm_long_term_outlook') as mock_outlook:
                    mock_summary.return_value = "Executive summary"
                    mock_implications.return_value = "- Implication 1"
                    mock_outlook.return_value = "Long-term outlook"

                    alert = format_alert(update, "c-level", use_llm=True)

                    assert "C-LEVEL ALERT" in alert
                    assert "Test Update 1" in alert
                    assert "Executive summary" in alert

    def test_format_alert_workfloor_no_llm(self, temp_db_with_data):
        """Test formatting a workfloor alert without LLM."""
        cursor = temp_db_with_data.cursor()
        cursor.execute("SELECT * FROM updates WHERE title = 'Test Update 1'")
        update = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))

        alert = format_alert(update, "workfloor", use_llm=False)

        assert "WORKFLOOR ALERT" in alert
        assert "Test Update 1" in alert
        assert "Review the full document" in alert
