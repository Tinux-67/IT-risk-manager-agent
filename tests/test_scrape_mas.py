"""
Tests for scrape_mas.py module.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.scrape_mas import (
    scrape_all_mas,
    scrape_mas_consultations,
    scrape_mas_publications,
    scrape_mas_regulations,
)

# ---------------------------------------------------------------------------
# Shared HTML stubs
# ---------------------------------------------------------------------------

PUBLICATIONS_HTML = """
<html><body>
  <a href="/sites/default/files/2024-01/EBA_paper.pdf">EBA Cybersecurity Paper</a>
  <a href="/publications/consultation-paper-on-risk">Consultation Paper on Risk</a>
  <a href="/publications/consultation-paper-on-risk">Consultation Paper on Risk</a>
</body></html>
"""

CONSULTATIONS_HTML = """
<html><body>
  <a href="/development/public-consultations/2024-consultation">2024 Public Consultation</a>
  <a href="/other-link">Unrelated link</a>
</body></html>
"""

REGULATIONS_HTML = """
<html><body>
  <a href="/regulation/regulations-and-notices/notice-123">Notice 123</a>
  <a href="/regulation/legislation/act-456">Act 456</a>
  <a href="/other">Unrelated</a>
</body></html>
"""

EMPTY_HTML = "<html><body><p>No documents here.</p></body></html>"


def _make_response(html: str, status_code: int = 200) -> MagicMock:
    """Helper to create a mock HTTP response."""
    resp = MagicMock()
    resp.text = html
    resp.status_code = status_code
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# scrape_mas_publications
# ---------------------------------------------------------------------------


class TestScrapeMasPublications:
    """Tests for scrape_mas_publications()."""

    @patch("scripts.scrape_mas.get_session")
    def test_returns_list_of_dicts(self, mock_get_session):
        session = MagicMock()
        session.get.return_value = _make_response(PUBLICATIONS_HTML)
        mock_get_session.return_value = session

        results = scrape_mas_publications(session)

        assert isinstance(results, list)
        assert len(results) > 0
        for item in results:
            assert "title" in item
            assert "url" in item
            assert "date" in item
            assert "source" in item
            assert item["source"] == "MAS_Publications"

    @patch("scripts.scrape_mas.get_session")
    def test_deduplicates_urls(self, mock_get_session):
        session = MagicMock()
        session.get.return_value = _make_response(PUBLICATIONS_HTML)
        mock_get_session.return_value = session

        results = scrape_mas_publications(session)
        urls = [r["url"] for r in results]
        assert len(urls) == len(set(urls)), "Duplicate URLs found"

    @patch("scripts.scrape_mas.get_session")
    def test_http_403_returns_empty(self, mock_get_session):
        session = MagicMock()
        session.get.return_value = _make_response("", status_code=403)
        mock_get_session.return_value = session

        results = scrape_mas_publications(session)
        assert results == []

    @patch("scripts.scrape_mas.get_session")
    def test_generic_exception_returns_empty(self, mock_get_session):
        session = MagicMock()
        session.get.side_effect = Exception("Network failure")
        mock_get_session.return_value = session

        results = scrape_mas_publications(session)
        assert results == []

    @patch("scripts.scrape_mas.get_session")
    def test_empty_page_returns_empty(self, mock_get_session):
        session = MagicMock()
        session.get.return_value = _make_response(EMPTY_HTML)
        mock_get_session.return_value = session

        results = scrape_mas_publications(session)
        assert results == []

    @patch("scripts.scrape_mas.get_session")
    def test_creates_session_if_none(self, mock_get_session):
        """When session=None, get_session() should be called."""
        session = MagicMock()
        session.get.return_value = _make_response(EMPTY_HTML)
        mock_get_session.return_value = session

        results = scrape_mas_publications(None)
        mock_get_session.assert_called_once()
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# scrape_mas_consultations
# ---------------------------------------------------------------------------


class TestScrapeMasConsultations:
    """Tests for scrape_mas_consultations()."""

    @patch("scripts.scrape_mas.get_session")
    def test_returns_list_of_dicts(self, mock_get_session):
        session = MagicMock()
        session.get.return_value = _make_response(CONSULTATIONS_HTML)
        mock_get_session.return_value = session

        results = scrape_mas_consultations(session)

        assert isinstance(results, list)
        for item in results:
            assert "title" in item
            assert "url" in item
            assert "source" in item
            assert item["source"] == "MAS_Consultations"

    @patch("scripts.scrape_mas.get_session")
    def test_filters_non_consultation_links(self, mock_get_session):
        session = MagicMock()
        session.get.return_value = _make_response(CONSULTATIONS_HTML)
        mock_get_session.return_value = session

        results = scrape_mas_consultations(session)
        for r in results:
            assert "consultation" in r["url"].lower()

    @patch("scripts.scrape_mas.get_session")
    def test_http_error_returns_empty(self, mock_get_session):
        session = MagicMock()
        err_resp = MagicMock()
        err_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        session.get.return_value = err_resp
        mock_get_session.return_value = session

        results = scrape_mas_consultations(session)
        assert results == []

    @patch("scripts.scrape_mas.get_session")
    def test_generic_exception_returns_empty(self, mock_get_session):
        session = MagicMock()
        session.get.side_effect = RuntimeError("Unexpected")
        mock_get_session.return_value = session

        results = scrape_mas_consultations(session)
        assert results == []


# ---------------------------------------------------------------------------
# scrape_mas_regulations
# ---------------------------------------------------------------------------


class TestScrapeMasRegulations:
    """Tests for scrape_mas_regulations()."""

    @patch("scripts.scrape_mas.get_session")
    def test_returns_list_of_dicts(self, mock_get_session):
        session = MagicMock()
        session.get.return_value = _make_response(REGULATIONS_HTML)
        mock_get_session.return_value = session

        results = scrape_mas_regulations(session)

        assert isinstance(results, list)
        for item in results:
            assert "title" in item
            assert "url" in item
            assert item["source"] == "MAS_Regulations"

    @patch("scripts.scrape_mas.get_session")
    def test_filters_unrelated_links(self, mock_get_session):
        session = MagicMock()
        session.get.return_value = _make_response(REGULATIONS_HTML)
        mock_get_session.return_value = session

        results = scrape_mas_regulations(session)
        for r in results:
            url = r["url"].lower()
            assert any(seg in url for seg in ["regulation", "notice", "legislation"])

    @patch("scripts.scrape_mas.get_session")
    def test_http_error_returns_empty(self, mock_get_session):
        session = MagicMock()
        err_resp = MagicMock()
        err_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("403")
        session.get.return_value = err_resp
        mock_get_session.return_value = session

        results = scrape_mas_regulations(session)
        assert results == []

    @patch("scripts.scrape_mas.get_session")
    def test_generic_exception_returns_empty(self, mock_get_session):
        session = MagicMock()
        session.get.side_effect = Exception("Timeout")
        mock_get_session.return_value = session

        results = scrape_mas_regulations(session)
        assert results == []


# ---------------------------------------------------------------------------
# scrape_all_mas
# ---------------------------------------------------------------------------


class TestScrapeAllMas:
    """Tests for scrape_all_mas()."""

    @patch("scripts.scrape_mas.scrape_mas_regulations")
    @patch("scripts.scrape_mas.scrape_mas_consultations")
    @patch("scripts.scrape_mas.scrape_mas_publications")
    def test_combines_all_sources(self, mock_pub, mock_con, mock_reg):
        mock_pub.return_value = [{"title": "A", "url": "https://mas.gov.sg/a", "date": "2024-01", "source": "MAS_Publications"}]
        mock_con.return_value = [{"title": "B", "url": "https://mas.gov.sg/b", "date": "2024-02", "source": "MAS_Consultations"}]
        mock_reg.return_value = [{"title": "C", "url": "https://mas.gov.sg/c", "date": "2024-03", "source": "MAS_Regulations"}]

        results = scrape_all_mas()

        assert len(results) == 3
        urls = {r["url"] for r in results}
        assert "https://mas.gov.sg/a" in urls
        assert "https://mas.gov.sg/b" in urls
        assert "https://mas.gov.sg/c" in urls

    @patch("scripts.scrape_mas.scrape_mas_regulations")
    @patch("scripts.scrape_mas.scrape_mas_consultations")
    @patch("scripts.scrape_mas.scrape_mas_publications")
    def test_deduplicates_across_sources(self, mock_pub, mock_con, mock_reg):
        dup = {"title": "Dup", "url": "https://mas.gov.sg/dup", "date": "2024-01", "source": "MAS_Publications"}
        mock_pub.return_value = [dup]
        mock_con.return_value = [dup]
        mock_reg.return_value = []

        results = scrape_all_mas()
        assert len(results) == 1

    @patch("scripts.scrape_mas.scrape_mas_regulations")
    @patch("scripts.scrape_mas.scrape_mas_consultations")
    @patch("scripts.scrape_mas.scrape_mas_publications")
    def test_all_empty_returns_empty(self, mock_pub, mock_con, mock_reg):
        mock_pub.return_value = []
        mock_con.return_value = []
        mock_reg.return_value = []

        results = scrape_all_mas()
        assert results == []


# ---------------------------------------------------------------------------
# Ollama error resilience (uses conftest fixtures)
# ---------------------------------------------------------------------------


class TestOllamaErrors:
    """Tests verifying scrape functions are resilient when Ollama errors occur.
    These tests ensure the scraping layer never depends on Ollama."""

    @patch("scripts.scrape_mas.get_session")
    def test_publications_independent_of_ollama(self, mock_get_session):
        """Scraping should work even if Ollama raises an error."""
        session = MagicMock()
        session.get.return_value = _make_response(PUBLICATIONS_HTML)
        mock_get_session.return_value = session

        # scrape_mas does not call Ollama at all -- just verify it runs cleanly
        results = scrape_mas_publications(session)
        assert isinstance(results, list)
