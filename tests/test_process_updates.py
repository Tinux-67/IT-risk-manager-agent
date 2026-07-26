"""
Tests for process_updates.py module.
"""

import os
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.process_updates import (
    init_db,
    extract_text_from_pdf,
    extract_text_from_html,
    categorize_risk_area,
    assess_urgency,
    generate_summary,
    process_file,
)


@pytest.fixture
def temp_db():
    """Fixture to create a temporary database for testing."""
    # Use in-memory database for testing
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Fixture to create a sample PDF file."""
    pdf_path = tmp_path / "sample.pdf"
    # Create a minimal PDF file (this is a very basic PDF structure)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    pdf_path.write_bytes(pdf_content)
    return str(pdf_path)


@pytest.fixture
def sample_html_path(tmp_path):
    """Fixture to create a sample HTML file."""
    html_path = tmp_path / "sample.html"
    # Use "cybersecurity" in the text to match the keyword
    html_content = "<html><body><p>This is a test document about cybersecurity and IT risk.</p></body></html>"
    html_path.write_text(html_content)
    return str(html_path)


class TestInitDb:
    """Tests for init_db function."""

    def test_init_db_creates_tables(self):
        """Test that init_db creates required tables."""
        # Use a temporary file for testing
        test_db_path = ":memory:"
        conn = init_db()

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert "updates" in tables
        assert "metadata" in tables

        conn.close()

    def test_init_db_creates_indexes(self):
        """Test that init_db creates indexes."""
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        assert "idx_publication_date" in indexes
        assert "idx_risk_area" in indexes
        assert "idx_urgency" in indexes

        conn.close()


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf function."""

    def test_extract_text_from_pdf_success(self, sample_pdf_path):
        """Test successful PDF text extraction."""
        with patch("PyPDF2.PdfReader") as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test PDF content"
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            result = extract_text_from_pdf(sample_pdf_path)
            assert result == "Test PDF content"

    def test_extract_text_from_pdf_import_error(self, sample_pdf_path):
        """Test PDF extraction with PyPDF2 not installed."""
        with patch.dict("sys.modules", {"PyPDF2": None}):
            result = extract_text_from_pdf(sample_pdf_path)
            assert result == ""

    def test_extract_text_from_pdf_file_not_found(self):
        """Test PDF extraction with non-existent file."""
        result = extract_text_from_pdf("/nonexistent/file.pdf")
        assert result == ""


class TestExtractTextFromHtml:
    """Tests for extract_text_from_html function."""

    def test_extract_text_from_html_success(self, sample_html_path):
        """Test successful HTML text extraction."""
        result = extract_text_from_html(sample_html_path)
        assert "cybersecurity" in result

    def test_extract_text_from_html_file_not_found(self):
        """Test HTML extraction with non-existent file."""
        result = extract_text_from_html("/nonexistent/file.html")
        assert result == ""


class TestCategorizeRiskArea:
    """Tests for categorize_risk_area function."""

    @patch("scripts.process_updates.get_ollama_response")
    def test_categorize_risk_area_llm_success(self, mock_ollama):
        """Test categorization with LLM."""
        mock_ollama.return_value = "IT Risk Management"

        result = categorize_risk_area("This is a test about IT risk management.")
        assert result == "IT Risk Management"

    @patch("scripts.process_updates.get_ollama_response")
    def test_categorize_risk_area_llm_fallback(self, mock_ollama):
        """Test categorization with LLM returning None."""
        mock_ollama.return_value = None

        # Text contains "cybersecurity" which should match the keyword
        result = categorize_risk_area("This is a test about cybersecurity.")
        # The keyword matching should find "cybersecurity" and return "Cybersecurity"
        # Note: The function checks for keywords in the risk areas list
        assert result in ["Cybersecurity", "IT Risk Management"]

    @patch("scripts.process_updates.get_ollama_response")
    def test_categorize_risk_area_no_match(self, mock_ollama):
        """Test categorization with no matching keywords."""
        mock_ollama.return_value = None

        result = categorize_risk_area("This is a test about something else.")
        assert result == "Other"


class TestAssessUrgency:
    """Tests for assess_urgency function."""

    @patch("scripts.process_updates.get_ollama_response")
    def test_assess_urgency_llm_success(self, mock_ollama):
        """Test urgency assessment with LLM."""
        mock_ollama.return_value = "Urgent"

        result = assess_urgency("This is an urgent matter.")
        assert result == "Urgent"

    @patch("scripts.process_updates.get_ollama_response")
    def test_assess_urgency_llm_fallback(self, mock_ollama):
        """Test urgency assessment with LLM returning None."""
        mock_ollama.return_value = None

        result = assess_urgency("This is an urgent matter with deadline.")
        assert result == "Urgent"

    @patch("scripts.process_updates.get_ollama_response")
    def test_assess_urgency_high_keywords(self, mock_ollama):
        """Test urgency assessment with high priority keywords."""
        mock_ollama.return_value = None

        result = assess_urgency("This is a high risk mandatory requirement.")
        assert result == "High"

    @patch("scripts.process_updates.get_ollama_response")
    def test_assess_urgency_medium_default(self, mock_ollama):
        """Test urgency assessment defaulting to Medium."""
        mock_ollama.return_value = None

        result = assess_urgency("This is a normal update.")
        assert result == "Medium"


class TestGenerateSummary:
    """Tests for generate_summary function."""

    @patch("scripts.process_updates.get_ollama_response")
    def test_generate_summary_llm_success(self, mock_ollama):
        """Test summary generation with LLM."""
        mock_ollama.return_value = "This is a test summary."

        # Use a long enough text to pass the length check
        long_text = "This is a long text that needs summarizing. " * 10
        result = generate_summary(long_text)
        assert result == "This is a test summary."

    @patch("scripts.process_updates.get_ollama_response")
    def test_generate_summary_llm_fallback(self, mock_ollama):
        """Test summary generation with LLM returning None."""
        mock_ollama.return_value = None

        long_text = "This is the first paragraph.\n\nThis is the second paragraph."
        result = generate_summary(long_text)
        assert "This is the first paragraph" in result

    @patch("scripts.process_updates.get_ollama_response")
    def test_generate_summary_short_text(self, mock_ollama):
        """Test summary generation with short text."""
        result = generate_summary("Short text")
        # For short text, it returns the first paragraph (which is the text itself)
        assert result == "Short text"


class TestProcessFile:
    """Tests for process_file function."""

    @patch("scripts.process_updates.extract_text_from_pdf")
    @patch("scripts.process_updates.categorize_risk_area")
    @patch("scripts.process_updates.assess_urgency")
    @patch("scripts.process_updates.generate_summary")
    def test_process_file_pdf_success(self, mock_summary, mock_urgency, mock_risk, mock_extract):
        """Test processing a PDF file."""
        mock_extract.return_value = "Test PDF content about IT Risk Management"
        mock_risk.return_value = "IT Risk Management"
        mock_urgency.return_value = "High"
        mock_summary.return_value = "Test summary"

        # Create a temporary PDF file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4\n")
            temp_pdf_path = f.name

        try:
            # Use a temporary database
            conn = sqlite3.connect(":memory:")
            # Create the table first
            cursor = conn.cursor()
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
                    is_processed BOOLEAN DEFAULT 0,
                    source TEXT DEFAULT "EBA"
                )
            """)
            conn.commit()

            result = process_file(temp_pdf_path, conn)
            assert result is True

            # Check if data was inserted
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM updates")
            count = cursor.fetchone()[0]
            assert count == 1

            conn.close()
        finally:
            os.unlink(temp_pdf_path)

    @patch("scripts.process_updates.extract_text_from_pdf")
    def test_process_file_no_text(self, mock_extract):
        """Test processing a file with no text."""
        mock_extract.return_value = ""

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4\n")
            temp_pdf_path = f.name

        try:
            conn = sqlite3.connect(":memory:")
            result = process_file(temp_pdf_path, conn)
            assert result is False
            conn.close()
        finally:
            os.unlink(temp_pdf_path)

    def test_process_file_unsupported_type(self):
        """Test processing an unsupported file type."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Test content")
            temp_txt_path = f.name

        try:
            conn = sqlite3.connect(":memory:")
            result = process_file(temp_txt_path, conn)
            assert result is False
            conn.close()
        finally:
            os.unlink(temp_txt_path)
