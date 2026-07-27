"""
Tests for scraping_utils.py module.
"""

# Add parent directory to path for imports
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from scripts.scraping_utils import (
    build_url,
    download_file,
    extract_date_from_filename,
    extract_date_from_url,
    find_links,
    generate_filename,
    get_file_extension,
    get_session,
    sanitize_filename,
    save_raw_update,
)


class TestGetSession:
    """Tests for get_session function."""

    def test_get_session_headers(self):
        """Test that session has correct headers."""
        session = get_session()
        assert "User-Agent" in session.headers
        assert Config.USER_AGENT in session.headers["User-Agent"]
        assert "Accept" in session.headers
        assert "Accept-Language" in session.headers

    def test_get_session_reusable(self):
        """Test that session can be reused."""
        session = get_session()
        assert isinstance(session, requests.Session)


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_sanitize_filename_with_special_chars(self):
        """Test filename with special characters."""
        assert sanitize_filename("Test/File:Name.pdf") == "Test_File_Name.pdf"
        assert sanitize_filename("Doc*Name?.txt") == "Doc_Name_.txt"
        assert sanitize_filename('A|B<C>D"E') == "A_B_C_D_E"

    def test_sanitize_filename_with_url_encoded(self):
        """Test filename with URL-encoded characters."""
        result = sanitize_filename("Test%20File%3AName.pdf")
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

    def test_sanitize_filename_unicode(self):
        """Test filename with unicode characters."""
        result = sanitize_filename("Document_éàè.pdf")
        assert "Document_éàè.pdf" == result


class TestExtractDateFromUrl:
    """Tests for extract_date_from_url function."""

    def test_extract_date_from_url_with_iso_date(self):
        """Test URL with ISO date format (YYYY-MM)."""
        assert extract_date_from_url("/2024-01/doc.pdf") == "2024-01"
        assert extract_date_from_url("https://example.com/2023-12/file.html") == "2023-12"

    def test_extract_date_from_url_with_slash_date(self):
        """Test URL with slash-separated date (YYYY/MM)."""
        assert extract_date_from_url("/2024/01/doc.pdf") == "2024-01"
        assert extract_date_from_url("https://example.com/2023/12/file.html") == "2023-12"

    def test_extract_date_from_url_no_date(self):
        """Test URL without date."""
        assert extract_date_from_url("/documents/file.pdf") == "Unknown"
        assert extract_date_from_url("https://example.com/path/to/file") == "Unknown"

    def test_extract_date_from_url_multiple_dates(self):
        """Test URL with multiple date-like patterns (takes first)."""
        assert extract_date_from_url("/2024-01/2023-12/file.pdf") == "2024-01"


class TestExtractDateFromFilename:
    """Tests for extract_date_from_filename function."""

    def test_extract_date_from_filename_iso(self):
        """Test filename with ISO date format (YYYY-MM-DD)."""
        assert extract_date_from_filename("2024-01-15_Document.pdf") == "2024-01-15"

    def test_extract_date_from_filename_slashes(self):
        """Test filename with slash-separated date (YYYY/MM/DD)."""
        assert extract_date_from_filename("2024/01/15_Document.pdf") == "2024-01-15"

    def test_extract_date_from_filename_underscores(self):
        """Test filename with underscore-separated date (YYYY_MM_DD)."""
        assert extract_date_from_filename("2024_01_15_Document.pdf") == "2024-01-15"

    def test_extract_date_from_filename_spaces(self):
        """Test filename with space-separated date (YYYY MM DD)."""
        assert extract_date_from_filename("2024 01 15 Document.pdf") == "2024-01-15"

    def test_extract_date_from_filename_partial(self):
        """Test filename with partial date (YYYY-MM)."""
        assert extract_date_from_filename("2024-01_Document.pdf") == "2024-01"

    def test_extract_date_from_filename_no_date(self):
        """Test filename without date."""
        assert extract_date_from_filename("Document.pdf") == "Unknown"


class TestBuildUrl:
    """Tests for build_url function."""

    def test_build_url_no_params(self):
        """Test URL building without parameters."""
        url = build_url("https://example.com/path")
        assert url == "https://example.com/path"

    def test_build_url_with_params(self):
        """Test URL building with parameters."""
        params = {"key1": "value1", "key2": "value2"}
        url = build_url("https://example.com/path", params)
        assert "key1=value1" in url
        assert "key2=value2" in url
        assert "?" in url

    def test_build_url_empty_params(self):
        """Test URL building with empty parameters."""
        url = build_url("https://example.com/path", {})
        assert url == "https://example.com/path"

    def test_build_url_none_params(self):
        """Test URL building with None parameters."""
        url = build_url("https://example.com/path", None)
        assert url == "https://example.com/path"


class TestGetFileExtension:
    """Tests for get_file_extension function."""

    def test_get_file_extension_pdf(self):
        """Test PDF extension."""
        assert get_file_extension("https://example.com/doc.pdf") == ".pdf"
        assert get_file_extension("doc.PDF") == ".pdf"

    def test_get_file_extension_html(self):
        """Test HTML extension."""
        assert get_file_extension("https://example.com/page.html") == ".html"
        assert get_file_extension("page.HTM") == ".html"

    def test_get_file_extension_xlsx(self):
        """Test XLSX extension."""
        assert get_file_extension("https://example.com/data.xlsx") == ".xlsx"
        assert get_file_extension("data.XLS") == ".xlsx"

    def test_get_file_extension_docx(self):
        """Test DOCX extension."""
        assert get_file_extension("https://example.com/doc.docx") == ".docx"
        assert get_file_extension("doc.DOC") == ".docx"

    def test_get_file_extension_unknown(self):
        """Test unknown extension."""
        assert get_file_extension("https://example.com/file.txt") == ".bin"
        assert get_file_extension("https://example.com/file") == ".bin"


class TestGenerateFilename:
    """Tests for generate_filename function."""

    @patch("scripts.scraping_utils.datetime")
    def test_generate_filename_default(self, mock_datetime):
        """Test filename generation with default timestamp."""
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        filename = generate_filename("Test Document", "EBA", ".pdf")
        assert "20240101_120000" in filename
        assert "eba" in filename
        assert "Test_Document" in filename  # Spaces are replaced with underscores
        assert filename.endswith(".pdf")

    @patch("scripts.scraping_utils.datetime")
    def test_generate_filename_custom_timestamp(self, mock_datetime):
        """Test filename generation with custom timestamp."""
        filename = generate_filename("Test", "MAS", ".html", timestamp="20231225_103000")
        assert "20231225_103000" in filename
        assert "mas" in filename
        assert filename.endswith(".html")

    @patch("scripts.scraping_utils.datetime")
    def test_generate_filename_long_title(self, mock_datetime):
        """Test filename generation with long title (truncated)."""
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        long_title = "A" * 100
        filename = generate_filename(long_title, "EBA", ".pdf")
        assert len(filename) < 150  # Should be truncated


class TestSaveRawUpdate:
    """Tests for save_raw_update function."""

    @patch("scripts.scraping_utils.download_file")
    @patch("scripts.scraping_utils.datetime")
    def test_save_raw_update_success(self, mock_datetime, mock_download):
        """Test successful save of raw update."""
        mock_download.return_value = True
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

        update = {
            "title": "Test Document",
            "url": "http://example.com/test.pdf",
            "date": "2024-01-01",
            "source": "EBA",
        }
        result = save_raw_update(update, "/tmp/test_raw")

        assert result != ""
        assert "20240101_120000" in result
        assert "eba" in result.lower()
        assert "Test_Document" in result  # Spaces are replaced with underscores
        assert result.endswith(".pdf")

    @patch("scripts.scraping_utils.download_file")
    def test_save_raw_update_failure(self, mock_download):
        """Test failed save of raw update."""
        mock_download.return_value = False

        update = {
            "title": "Test Document",
            "url": "http://example.com/test.pdf",
            "date": "2024-01-01",
            "source": "EBA",
        }
        result = save_raw_update(update, "/tmp/test_raw")

        assert result == ""

    @patch("scripts.scraping_utils.download_file")
    @patch("scripts.scraping_utils.datetime")
    def test_save_raw_update_mas_source(self, mock_datetime, mock_download):
        """Test save with MAS source."""
        mock_download.return_value = True
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

        update = {
            "title": "MAS Document",
            "url": "http://example.com/test.docx",
            "date": "2024-01-01",
            "source": "MAS_Publications",
        }
        result = save_raw_update(update, "/tmp/test_raw")

        assert "mas" in result.lower()
        assert result.endswith(".docx")


class TestDownloadFile:
    """Tests for download_file function."""

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

        result = download_file("http://example.com/test.pdf", "/tmp/test.pdf")

        assert result is True
        mock_file.write.assert_called_with(b"test content")

    @patch("scripts.scraping_utils.requests.Session.get")
    def test_download_file_http_error(self, mock_get):
        """Test HTTP error during download."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("HTTP Error")
        mock_get.return_value = mock_response

        result = download_file("http://example.com/test.pdf", "/tmp/test.pdf")

        assert result is False

    @patch("scripts.scraping_utils.requests.Session.get")
    def test_download_file_connection_error(self, mock_get):
        """Test connection error during download."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.ConnectionError(
            "Connection Error"
        )
        mock_get.return_value = mock_response

        result = download_file("http://example.com/test.pdf", "/tmp/test.pdf")

        assert result is False

    @patch("scripts.scraping_utils.requests.Session.get")
    def test_download_file_timeout(self, mock_get):
        """Test timeout during download."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.Timeout("Timeout")
        mock_get.return_value = mock_response

        result = download_file("http://example.com/test.pdf", "/tmp/test.pdf")

        assert result is False

    @patch("scripts.scraping_utils.requests.Session.get")
    @patch("builtins.open", create=True)
    def test_download_file_creates_directory(self, mock_open, mock_get):
        """Test that download_file creates parent directories."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"test"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Path with non-existent directory
        result = download_file("http://example.com/test.pdf", "/tmp/nonexistent/dir/test.pdf")

        assert result is True


class TestFindLinks:
    """Tests for find_links function."""

    def test_find_links_basic(self):
        """Test basic link finding."""
        html = "<html><body><a href='/test.pdf'>Test</a></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        links = find_links(soup, "https://example.com")

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/test.pdf"
        assert links[0]["title"] == "Test"

    def test_find_links_multiple(self):
        """Test finding multiple links."""
        html = """
        <html><body>
            <a href='/test1.pdf'>Test 1</a>
            <a href='/test2.html'>Test 2</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = find_links(soup, "https://example.com")

        assert len(links) == 2

    def test_find_links_with_selectors(self):
        """Test finding links with custom selectors."""
        html = """
        <html><body>
            <div class="download"><a href='/test.pdf'>Test</a></div>
            <a href='/other.html'>Other</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = find_links(soup, "https://example.com", link_selectors=["div.download a"])

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/test.pdf"

    def test_find_links_duplicate_urls(self):
        """Test that duplicate URLs are filtered."""
        html = """
        <html><body>
            <a href='/test.pdf'>Test 1</a>
            <a href='/test.pdf'>Test 2</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = find_links(soup, "https://example.com")

        assert len(links) == 1  # Only one unique URL

    def test_find_links_with_date_in_parent(self):
        """Test extracting date from parent element."""
        html = """
        <html><body>
            <div class="date">2024-01-01</div>
            <a href='/test.pdf'>Test</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = find_links(soup, "https://example.com", text_selectors=[".date"])

        assert len(links) == 1
        assert links[0]["date"] == "2024-01-01"
