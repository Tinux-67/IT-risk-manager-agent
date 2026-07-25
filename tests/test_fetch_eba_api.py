"""
Tests for fetch_eba_api.py module.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fetch_eba_api import (
    ApifyClient,
    fetch_eba_updates,
    save_updates,
    _process_apify_item,
    _sanitize_filename,
)
from config import Config


class TestSanitizeFilename:
    """Tests for _sanitize_filename function."""

    def test_sanitize_filename_with_special_chars(self):
        """Test filename with special characters."""
        assert _sanitize_filename("Test/File:Name.pdf") == "Test_File_Name.pdf"
        assert _sanitize_filename("Doc*Name?.txt") == "Doc_Name_.txt"

    def test_sanitize_filename_with_url_encoded(self):
        """Test filename with URL-encoded characters."""
        result = _sanitize_filename("Test%20File%3AName.pdf")
        assert "Test File" in result

    def test_sanitize_filename_with_multiple_spaces(self):
        """Test filename with multiple spaces."""
        assert _sanitize_filename("Test   File   Name.pdf") == "Test File Name.pdf"


class TestProcessApifyItem:
    """Tests for _process_apify_item function."""

    def test_process_apify_item_basic(self):
        """Test processing a basic Apify item."""
        item = {
            "title": "Test Regulation",
            "url": "https://example.com/reg1",
            "date": "2024-01-01",
            "text": "This is a test regulation.",
        }
        result = _process_apify_item(item, "eba")
        
        assert result is not None
        assert result["title"] == "Test Regulation"
        assert result["url"] == "https://example.com/reg1"
        assert result["source"] == "eba"
        assert result["date"] == "2024-01-01"

    def test_process_apify_item_missing_fields(self):
        """Test processing an item with missing fields."""
        item = {
            "name": "Test Regulation",
            "sourceUrl": "https://example.com/reg1",
            "publicationDate": "2024-01-01",
            "description": "This is a test regulation.",
        }
        result = _process_apify_item(item, "eba")
        
        assert result is not None
        assert result["title"] == "Test Regulation"
        assert result["url"] == "https://example.com/reg1"

    def test_process_apify_item_invalid(self):
        """Test processing an invalid item."""
        item = {}  # Empty item
        result = _process_apify_item(item, "eba")
        
        assert result is None


class TestApifyClient:
    """Tests for ApifyClient class."""

    @patch("scripts.fetch_eba_api.requests.post")
    def test_apify_client_init(self, mock_post):
        """Test ApifyClient initialization."""
        # Temporarily set API key
        os.environ["APIFY_API_KEY"] = "test_api_key"
        
        try:
            client = ApifyClient()
            assert client.api_key == "test_api_key"
            assert client.base_url == Config.APIFY_BASE_URL
            assert "Authorization" in client.headers
        finally:
            del os.environ["APIFY_API_KEY"]

    @patch("scripts.fetch_eba_api.requests.post")
    def test_apify_client_no_api_key(self, mock_post):
        """Test ApifyClient without API key."""
        # Ensure no API key is set
        os.environ.pop("APIFY_API_KEY", None)
        
        with pytest.raises(ValueError, match="Apify API key is required"):
            ApifyClient()

    @patch("scripts.fetch_eba_api.requests.post")
    @patch("scripts.fetch_eba_api.requests.get")
    def test_run_actor(self, mock_get, mock_post):
        """Test running an Apify actor."""
        # Setup mock responses
        mock_post.return_value.json.return_value = {
            "id": "test_run_id",
            "status": "FINISHED",
            "defaultDatasetId": "test_dataset_id"
        }
        mock_post.return_value.raise_for_status.return_value = None
        
        mock_get.return_value.json.return_value = {
            "items": [
                {"title": "Test Item", "url": "https://example.com"}
            ]
        }
        mock_get.return_value.raise_for_status.return_value = None
        
        # Temporarily set API key
        os.environ["APIFY_API_KEY"] = "test_api_key"
        
        try:
            client = ApifyClient()
            result = client.run_actor("test_actor", {"test": "input"})
            
            assert "items" in result
        finally:
            del os.environ["APIFY_API_KEY"]


class TestFetchEbaUpdates:
    """Tests for fetch_eba_updates function."""

    @patch("scripts.fetch_eba_api.ApifyClient")
    def test_fetch_eba_updates_success(self, mock_client):
        """Test successful fetch of EBA updates."""
        # Setup mock client
        mock_instance = MagicMock()
        mock_instance.run_actor.return_value = {
            "defaultDatasetId": "test_dataset_id"
        }
        mock_instance.get_dataset_items.return_value = [
            {
                "title": "Test Update 1",
                "url": "https://example.com/1",
                "date": "2024-01-01",
                "text": "Test content 1"
            },
            {
                "title": "Test Update 2",
                "url": "https://example.com/2",
                "date": "2024-01-02",
                "text": "Test content 2"
            }
        ]
        mock_client.return_value = mock_instance
        
        # Temporarily set API key
        os.environ["APIFY_API_KEY"] = "test_api_key"
        
        try:
            updates = fetch_eba_updates(days_back=7, limit=10)
            
            assert len(updates) == 2
            assert updates[0]["title"] == "Test Update 1"
            assert updates[1]["title"] == "Test Update 2"
        finally:
            del os.environ["APIFY_API_KEY"]

    @patch("scripts.fetch_eba_api.ApifyClient")
    def test_fetch_eba_updates_no_api_key(self, mock_client):
        """Test fetch without API key."""
        # Ensure no API key is set
        os.environ.pop("APIFY_API_KEY", None)
        
        updates = fetch_eba_updates()
        
        assert updates == []


class TestSaveUpdates:
    """Tests for save_updates function."""

    def test_save_updates_json(self, tmp_path):
        """Test saving updates as JSON files."""
        updates = [
            {
                "title": "Test Update 1",
                "url": "https://example.com/1",
                "date": "2024-01-01",
                "text": "Test content"
            },
            {
                "title": "Test Update 2",
                "url": "https://example.com/2",
                "date": "2024-01-02",
                "text": "Test content 2"
            }
        ]
        
        # Use temporary directory
        output_dir = tmp_path / "test_output"
        saved_files = save_updates(updates, output_dir=output_dir)
        
        assert len(saved_files) == 2
        assert all(file.endswith(".json") for file in saved_files)
        
        # Check file content
        with open(saved_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["title"] == "Test Update 1"

    def test_save_updates_empty(self, tmp_path):
        """Test saving empty updates list."""
        output_dir = tmp_path / "test_output"
        saved_files = save_updates([], output_dir=output_dir)
        
        assert len(saved_files) == 0
