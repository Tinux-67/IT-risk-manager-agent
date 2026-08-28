#!/usr/bin/env python3
"""
Utility functions for web scraping (EBA and MAS).
Shared between scrape_eba.py and scrape_mas.py to avoid code duplication.
"""

import os
import re
from datetime import datetime
from urllib.parse import unquote, urlencode, urljoin

import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger

from config import Config
from scripts.logging_config import setup_logging

setup_logging()

_ALLOWED_HOSTNAMES = {"eba.europa.eu", "www.eba.europa.eu", "mas.gov.sg", "www.mas.gov.sg"}


def is_allowed_url(url: str) -> bool:
    """Return True only if the URL's hostname is in the allowlist."""
    from urllib.parse import urlparse

    try:
        return (urlparse(url).hostname or "") in _ALLOWED_HOSTNAMES
    except Exception:
        return False


def get_session() -> requests.Session:
    """
    Create a requests session with headers to mimic a browser.

    Returns:
        requests.Session: Configured session with user-agent and headers.
    """
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": Config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
        }
    )
    return session


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters and URL-encoded sequences.

    Args:
        filename: The original filename (may contain URL-encoded characters).

    Returns:
        str: Sanitized filename safe for filesystem use.
    """
    # Decode URL-encoded characters first
    filename = unquote(filename)
    # Remove invalid characters for filesystem
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # Replace multiple spaces with single space
    filename = re.sub(r"\s+", " ", filename).strip()
    # Truncate to 200 chars to stay well within the 255-char OS limit
    return filename[:200]


def extract_date_from_url(url: str) -> str:
    """
    Extract date from URL path (e.g., /2024-01/... -> 2024-01 or /2024/01/... -> 2024-01).

    Args:
        url: The URL to extract date from.

    Returns:
        str: Extracted date in YYYY-MM format, or "Unknown" if not found.
    """
    # Look for YYYY-MM or YYYY/MM pattern in the URL
    match = re.search(r"/(\d{4})[-/](\d{2})", url)
    if match:
        year, month = match.groups()
        return f"{year}-{month}"
    return "Unknown"


def extract_date_from_filename(filename: str) -> str:
    """
    Extract date from filename (e.g., '2024-01-15_Document.pdf' -> 2024-01-15).
    Supports YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD, and space-separated formats.

    Args:
        filename: The filename to extract date from.

    Returns:
        str: Extracted date in YYYY-MM-DD format, or "Unknown" if not found.
    """
    # Look for YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD, or YYYY MM DD pattern
    match = re.search(r"(\d{4})[-/_\s](\d{2})[-/_\s](\d{2})", filename)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    # Look for YYYY-MM or YYYYMMDD pattern
    match = re.search(r"(\d{4})[-_](\d{2})", filename)
    if match:
        year, month = match.groups()
        return f"{year}-{month}"
    return "Unknown"


def download_file(
    url: str,
    save_path: str,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> bool:
    """
    Download a file from a URL and save it to the specified path.

    Args:
        url: URL of the file to download.
        save_path: Local path to save the file.
        session: Optional requests.Session for connection reuse.
        timeout: Request timeout in seconds (default: 30).

    Returns:
        bool: True if download succeeded, False otherwise.
    """
    if not is_allowed_url(url):
        logger.error(f"SSRF protection: URL not in allowlist: {url}")
        return False

    try:
        if session is None:
            session = get_session()

        logger.debug(f"Downloading: {url}")
        response = session.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.success(f"Downloaded: {save_path}")
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error downloading {url}: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error downloading {url}: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout downloading {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False


def build_url(base_url: str, params: dict | None = None) -> str:
    """
    Build a URL with query parameters.

    Args:
        base_url: The base URL (e.g., "https://example.com/path").
        params: Dictionary of query parameters (default: None).

    Returns:
        str: Full URL with query parameters (omits '?' if params is empty or None).
    """
    if params is None or not params:
        return base_url
    return f"{base_url}?{urlencode(params)}"


def get_file_extension(url: str) -> str:
    """
    Determine the file extension from a URL.

    Args:
        url: The URL of the file.

    Returns:
        str: File extension (e.g., ".pdf", ".html", ".bin" for unknown).
    """
    url_lower = url.lower()
    if url_lower.endswith(".pdf"):
        return ".pdf"
    elif url_lower.endswith(".html") or url_lower.endswith(".htm"):
        return ".html"
    elif url_lower.endswith(".xlsx") or url_lower.endswith(".xls"):
        return ".xlsx"
    elif url_lower.endswith(".docx") or url_lower.endswith(".doc"):
        return ".docx"
    else:
        return ".bin"  # Fallback for unknown types


def generate_filename(
    title: str,
    source: str,
    extension: str = ".pdf",
    timestamp: str | None = None,
) -> str:
    """
    Generate a sanitized filename for a downloaded file.

    Args:
        title: The title of the document.
        source: The source (e.g., "EBA", "MAS").
        extension: File extension (default: ".pdf").
        timestamp: Optional timestamp (default: current time in YYYYMMDD_HHMMSS format).

    Returns:
        str: Sanitized filename.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = sanitize_filename(title[:50])  # Limit title length
    # Replace spaces with underscores for consistency in filenames
    safe_title = safe_title.replace(" ", "_")
    safe_source = sanitize_filename(source).replace("_", "").lower()
    return f"{timestamp}_{safe_source}_{safe_title}{extension}"


def save_raw_update(
    update: dict,
    base_dir: str,
    session: requests.Session | None = None,
) -> str:
    """
    Save a raw update (PDF/HTML/DOCX) to the specified directory.

    Args:
        update: Dictionary with 'title', 'url', 'date', and optionally 'source'.
        base_dir: Base directory to save the file (e.g., Config.RAW_DATA_DIR).
        session: Optional requests.Session for connection reuse.

    Returns:
        str: Path to the saved file, or empty string if failed.
    """
    # SSRF protection: validate URL before fetching
    if not is_allowed_url(update["url"]):
        logger.error(f"SSRF protection: URL not in allowlist: {update['url']}")
        return ""

    # Determine file extension from URL
    extension = get_file_extension(update["url"])

    # Generate filename
    source = update.get("source", "unknown")
    filename = generate_filename(update["title"], source, extension)
    save_path = os.path.join(base_dir, filename)

    # Download and save
    if download_file(update["url"], save_path, session):
        logger.success(f"Saved raw update: {filename}")
        return save_path
    logger.error(f"Failed to save raw update: {filename}")
    return ""


def find_links(
    soup: BeautifulSoup,
    base_url: str,
    link_selectors: list | None = None,
    text_selectors: list | None = None,
) -> list[dict]:
    """
    Find and extract links from a BeautifulSoup object with optional filtering.

    Args:
        soup: BeautifulSoup parsed HTML.
        base_url: Base URL to join with relative links.
        link_selectors: List of CSS selectors to filter links (default: ["a[href]"]).
        text_selectors: List of CSS selectors to extract text from parent elements.

    Returns:
        list[dict]: List of dictionaries with 'title', 'url', 'date', and 'source'.
    """
    if link_selectors is None:
        link_selectors = ["a[href]"]
    if text_selectors is None:
        text_selectors = []

    updates = []
    seen_urls = set()

    for selector in link_selectors:
        all_links = soup.select(selector)
        for link in all_links:
            if not isinstance(link, Tag):
                continue
            href_raw = link.get("href")
            if not isinstance(href_raw, str) or not href_raw:
                continue
            href = href_raw

            full_url = urljoin(base_url, href)

            # Skip if we've already seen this URL
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Extract title from link text or filename
            title = link.get_text(strip=True)
            if not title:
                filename = os.path.basename(href)
                title = os.path.splitext(filename)[0]
            title = sanitize_filename(title)

            # Try to extract date from multiple sources
            date = "Unknown"

            # 1. Try to find date in parent elements using text_selectors
            parent = link.parent
            for _ in range(3):  # Go up 3 levels
                for selector in text_selectors:
                    date_elem = parent.select_one(selector) if parent else None
                    if date_elem:
                        date = date_elem.get_text(strip=True)
                        break
                if date != "Unknown":
                    break
                parent = parent.parent if parent else None

            # 2. If no date found, try to extract from URL
            if date == "Unknown":
                date = extract_date_from_url(href)

            # 3. If still no date, try to extract from filename
            if date == "Unknown":
                date = extract_date_from_filename(href)

            updates.append(
                {
                    "title": title,
                    "url": full_url,
                    "date": date,
                }
            )

    return updates
