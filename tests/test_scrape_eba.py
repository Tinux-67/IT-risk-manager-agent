"""
Tests for scrape_eba.py module.
"""

# Add parent directory to path for imports
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from scripts.scraping_utils import (
    build_url,
    extract_date_from_filename,
    extract_date_from_url,
    get_session,
    sanitize_filename,
)


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_sanitize_filename_with_special_chars(self):
        """Test filename with special characters."""
        assert sanitize_filename("Test/File:Name.pdf") == "Test_File_Name.pdf"
        assert sanitize_filename("Doc*Name?.txt") == "Doc_Name_.txt"

    def test_sanitize_filename_with_url_encoded(self):
        """Test filename with URL-encoded characters."""
        # URL-encoded space is %20, colon is %3A
        result = sanitize_filename("Test%20File%3AName.pdf")
        # After unquote: "Test File:Name.pdf", then sanitize: "Test File_Name.pdf"
        assert "Test File" in result
        assert result.endswith(".pdf")

    def test_sanitize_filename_with_multiple_spaces(self):
        """Test filename with multiple spaces."""
        assert sanitize_filename("Test   File   Name.pdf") == "Test File Name.pdf"

    def test_sanitize_filename_empty(self):
        """Test empty filename."""
        assert sanitize_filename("") == ""

    def test_sanitize_filename_normal(self):
        """Test normal filename."""
        assert sanitize_filename("NormalFile.pdf") == "NormalFile.pdf"


class TestExtractDateFromUrl:
    """Tests for extract_date_from_url function."""

    def test_extract_date_from_url_with_date(self):
        """Test URL with date in path."""
        assert extract_date_from_url("/2024-01/doc.pdf") == "2024-01"
        assert extract_date_from_url("https://example.com/2023-12/file.html") == "2023-12"

    def test_extract_date_from_url_no_date(self):
        """Test URL without date."""
        assert extract_date_from_url("/documents/file.pdf") == "Unknown"

    def test_extract_date_from_url_multiple_dates(self):
        """Test URL with multiple date-like patterns."""
        assert extract_date_from_url("/2024-01/2023-12/file.pdf") == "2024-01"


class TestExtractDateFromFilename:
    """Tests for extract_date_from_filename function."""

    def test_extract_date_from_filename_iso(self):
        """Test filename with ISO date format."""
        assert extract_date_from_filename("2024-01-15_Document.pdf") == "2024-01-15"

    def test_extract_date_from_filename_spaces(self):
        """Test filename with spaces in date."""
        result = extract_date_from_filename("2024 01 15 Document.pdf")
        assert result == "2024-01-15"

    def test_extract_date_from_filename_no_date(self):
        """Test filename without date."""
        assert extract_date_from_filename("Document.pdf") == "Unknown"


class TestBuildUrl:
    """Tests for build_url function."""

    def test_build_url_default(self):
        """Test default URL building."""
        url = build_url(Config.EBA_PUBLICATIONS_URL)
        assert Config.EBA_PUBLICATIONS_URL in url

    def test_build_url_custom_params(self):
        """Test URL building with custom parameters."""
        params = {"document_type": "123", "text": "test"}
        url = build_url(Config.EBA_PUBLICATIONS_URL, params)
        assert "document_type=123" in url
        assert "text=test" in url


class TestGetSession:
    """Tests for get_session function."""

    def test_get_session_headers(self):
        """Test that session has correct headers."""
        session = get_session()
        assert "User-Agent" in session.headers
        assert Config.USER_AGENT in session.headers["User-Agent"]
        assert "Accept" in session.headers


class TestScrapeEbaRegulations:
    """Tests for scrape_eba_regulations function."""

    @patch("scripts.scrape_eba.requests.Session.get")
    @patch("scripts.scrape_eba.BeautifulSoup")
    def test_scrape_eba_regulations_success(self, mock_soup, mock_get):
        """Test successful scraping."""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "<html><a href='/sites/default/files/test.pdf'>Test</a></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Mock BeautifulSoup
        mock_soup_instance = MagicMock()
        mock_link = MagicMock(spec=["get", "get_text", "parent"])
        mock_link.configure_mock(
            **{
                "get.return_value": "/sites/default/files/test.pdf",
                "get_text.return_value": "Test Document",
                "parent": None,
            }
        )
        # Make isinstance(link, Tag) pass under the production type guard
        from bs4 import Tag as _Tag

        mock_link.__class__ = _Tag
        mock_soup_instance.find_all.return_value = [mock_link]
        mock_soup.return_value = mock_soup_instance

        from scripts.scrape_eba import scrape_eba_regulations

        updates = scrape_eba_regulations()

        assert len(updates) == 1
        assert updates[0]["title"] == "Test Document"
        assert Config.EBA_BASE_URL in updates[0]["url"]

    @patch("scripts.scrape_eba.requests.Session.get")
    def test_scrape_eba_regulations_http_error(self, mock_get):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response

        from scripts.scrape_eba import scrape_eba_regulations

        updates = scrape_eba_regulations()

        assert len(updates) == 0


class TestDownloadFile:
    """Tests for download_file function (from scraping_utils)."""

    @patch("scripts.scraping_utils.requests.Session.get")
    @patch("builtins.open", create=True)
    def test_download_file_success(self, mock_open, mock_get):
        """Test successful file download."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"test content"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        from scripts.scraping_utils import download_file

        result = download_file(
            "https://www.eba.europa.eu/sites/default/files/test.pdf", "/tmp/test.pdf"
        )

        assert result is True
        mock_file.write.assert_called_with(b"test content")

    @patch("scripts.scraping_utils.requests.Session.get")
    def test_download_file_http_error(self, mock_get):
        """Test HTTP error during download."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response

        from scripts.scraping_utils import download_file

        result = download_file(
            "https://www.eba.europa.eu/sites/default/files/test.pdf", "/tmp/test.pdf"
        )

        assert result is False


class TestSaveRawUpdate:
    """Tests for save_raw_update function (from scraping_utils)."""

    @patch("scripts.scraping_utils.download_file")
    @patch("scripts.scraping_utils.datetime")
    def test_save_raw_update_success(self, mock_datetime, mock_download):
        """Test successful save of raw update."""
        mock_download.return_value = True
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

        from scripts.scraping_utils import save_raw_update

        update = {
            "title": "Test Document",
            "url": "https://www.eba.europa.eu/sites/default/files/test.pdf",
            "date": "2024-01-01",
            "source": "EBA",
        }
        result = save_raw_update(update, "/tmp/test_raw")

        assert result != ""
        # The filename will be: timestamp + _ + sanitized_source + _ + sanitized_title + .pdf
        assert "20240101_120000" in result
        assert "eba" in result.lower()
        assert result.endswith(".pdf")

    @patch("scripts.scraping_utils.download_file")
    def test_save_raw_update_failure(self, mock_download):
        """Test failed save of raw update."""
        mock_download.return_value = False

        from scripts.scraping_utils import save_raw_update

        update = {
            "title": "Test Document",
            "url": "https://www.eba.europa.eu/sites/default/files/test.pdf",
            "date": "2024-01-01",
            "source": "EBA",
        }
        result = save_raw_update(update, "/tmp/test_raw")

        assert result == ""
