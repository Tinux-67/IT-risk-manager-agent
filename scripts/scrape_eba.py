#!/usr/bin/env python3
"""
Scrape EBA (European Banking Authority) regulatory updates from their official publications page.
Saves raw data (PDF/HTML) to data/raw/eba/.

Target URL: https://www.eba.europa.eu/publications-and-media/publications

NOTE: This script is being replaced by fetch_eba_api.py which uses the Apify API.
     Use --use-apify to switch to the new API-based approach.
"""

import os
import re
import time
import argparse
from datetime import datetime
from urllib.parse import urljoin, urlencode, unquote

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import Config

# Ensure raw data directory exists
os.makedirs(Config.RAW_DATA_DIR, exist_ok=True)

# Configure logging
logger.add(
    Config.LOG_FILE,
    rotation=Config.LOG_ROTATION,
    retention=Config.LOG_RETENTION,
    level=Config.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
)


def use_apify_instead():
    """Check if Apify API is configured and suggest using it."""
    if Config.check_apify_config():
        logger.info(
            "Apify API is configured. Consider using fetch_eba_api.py instead for more reliable results."
        )
        print(
            "\u26a0\ufe0f Apify API is configured. "
            "Consider using 'python scripts/fetch_eba_api.py' for more reliable results."
        )


def get_session() -> requests.Session:
    """Create a requests session with headers to mimic a browser."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": Config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
    })
    return session


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    # Decode URL-encoded characters first
    filename = unquote(filename)
    # Remove invalid characters
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', " ", filename).strip()
    return filename


def extract_date_from_url(url: str) -> str:
    """Extract date from URL (e.g., /2026-07/... -> 2026-07)."""
    # Look for YYYY-MM pattern in the URL
    match = re.search(r'/(\d{4}-\d{2})/', url)
    if match:
        return match.group(1)
    return "Unknown"


def extract_date_from_filename(filename: str) -> str:
    """Extract date from filename (e.g., '2026 07 15 Document.pdf' -> 2026-07-15)."""
    # Look for YYYY MM DD or YYYY-MM-DD pattern
    match = re.search(r'(\d{4}[-_\s]\d{2}[-_\s]\d{2})', filename)
    if match:
        date_str = match.group(1)
        # Standardize to YYYY-MM-DD
        date_str = date_str.replace(" ", "-")
        return date_str
    return "Unknown"


def download_file(url: str, save_path: str, session: requests.Session = None) -> bool:
    """Download a file from a URL and save it to the specified path."""
    try:
        if session is None:
            session = get_session()

        logger.info(f"Downloading: {url}")
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.success(f"Downloaded: {save_path}")
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error downloading {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False


def build_eba_url(params: dict = None) -> str:
    """Build the EBA publications URL with query parameters."""
    if params is None:
        params = {"document_type": "248"}  # Default: Regulations/Guidelines
    return f"{Config.EBA_PUBLICATIONS_URL}?{urlencode(params)}"


def scrape_eba_regulations(session: requests.Session = None, params: dict = None) -> list[dict]:
    """
    Scrape the EBA publications page for regulatory updates.
    Returns a list of dictionaries with title, URL, and date.
    """
    updates = []
    seen_urls = set()  # To avoid duplicates

    if session is None:
        session = get_session()

    url = build_eba_url(params)

    try:
        logger.info(f"Fetching EBA publications from: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all links that point to files in /sites/default/files/
        all_links = soup.find_all("a", href=True)

        for link in all_links:
            href = link["href"]
            full_url = urljoin(Config.EBA_BASE_URL, href)

            # Only process direct file links (PDFs, etc.) from /sites/default/files/
            if "/sites/default/files/" not in href:
                continue

            # Skip if we've already seen this URL
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Extract title from link text or filename
            title = link.get_text(strip=True)
            if not title or title == "":
                # Extract title from URL filename
                filename = os.path.basename(href)
                title = os.path.splitext(filename)[0]  # Remove extension
                title = sanitize_filename(title)
            else:
                title = sanitize_filename(title)

            # Try to extract date from multiple sources
            date = "Unknown"

            # 1. Try to find date in parent elements
            parent = link.parent
            for _ in range(3):  # Go up 3 levels
                date_elem = parent.find(class_=re.compile("date", re.I)) if parent else None
                if date_elem:
                    date = date_elem.get_text(strip=True)
                    break
                parent = parent.parent if parent else None

            # 2. If no date found, try to extract from URL
            if date == "Unknown":
                date = extract_date_from_url(href)

            # 3. If still no date, try to extract from filename
            if date == "Unknown":
                date = extract_date_from_filename(href)

            updates.append({
                "title": title,
                "url": full_url,
                "date": date,
            })

        logger.success(f"Found {len(updates)} updates on EBA publications page")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error("403 Forbidden: The website may be blocking scrapers.")
            logger.warning("Try adding a delay between requests or using a proxy.")
        else:
            logger.error(f"HTTP Error: {e}")
    except Exception as e:
        logger.error(f"Error scraping EBA website: {e}")

    return updates


def save_raw_update(update: dict, session: requests.Session = None) -> str:
    """
    Save a raw update (PDF/HTML) to the data/raw/eba/ directory.
    Returns the path to the saved file.
    """
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = sanitize_filename(update["title"][:50])

    # Determine file extension from URL
    url_lower = update["url"].lower()
    if url_lower.endswith(".pdf"):
        ext = ".pdf"
    elif url_lower.endswith(".html") or url_lower.endswith(".htm"):
        ext = ".html"
    elif url_lower.endswith(".xlsx") or url_lower.endswith(".xls"):
        ext = ".xlsx"
    elif url_lower.endswith(".docx") or url_lower.endswith(".doc"):
        ext = ".docx"
    else:
        ext = ".bin"  # Fallback for unknown types

    filename = f"{timestamp}_{safe_title}{ext}"
    save_path = os.path.join(Config.RAW_DATA_DIR, filename)

    # Download and save
    if download_file(update["url"], save_path, session):
        logger.success(f"Saved raw update: {filename}")
        return save_path
    logger.error(f"Failed to save raw update: {filename}")
    return ""


def main():
    parser = argparse.ArgumentParser(description="Scrape EBA regulatory updates.")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of updates to scrape.")
    parser.add_argument("--dry-run", action="store_true", help="Only list updates without downloading.")
    parser.add_argument("--delay", type=float, default=Config.DEFAULT_DELAY, 
                        help=f"Delay between requests in seconds (default: {Config.DEFAULT_DELAY}).")
    parser.add_argument("--document-type", type=str, default="248", 
                        help="Filter by document type (default: 248 for regulations/guidelines).")
    parser.add_argument("--all-types", action="store_true", 
                        help="Scrape all document types (no filter).")
    parser.add_argument("--use-apify", action="store_true",
                        help="Use Apify API instead of scraping (recommended)")
    args = parser.parse_args()

    logger.info("Starting EBA scrape...")
    
    # Check if Apify should be used
    if args.use_apify or Config.check_apify_config():
        logger.info("Using Apify API (recommended)")
        print("\u2705 Using Apify API for fetching EBA updates...")
        
        # Import here to avoid circular imports
        from scripts.fetch_eba_api import main as apify_main
        import sys
        
        # Pass arguments to Apify script
        apify_args = [
            "--days", str(args.limit),  # Use limit as days for Apify
            "--limit", str(args.limit),
        ]
        if args.dry_run:
            apify_args.append("--dry-run")
        
        sys.argv = ["fetch_eba_api.py"] + apify_args
        apify_main()
        return

    use_apify_instead()

    # Build parameters
    params = {"document_type": args.document_type}
    if args.all_types:
        params.pop("document_type", None)  # Remove document_type filter

    # Create a session for all requests
    session = get_session()

    # Add delay to avoid rate limiting
    if args.delay > 0:
        logger.info(f"Waiting {args.delay} seconds before first request...")
        time.sleep(args.delay)

    updates = scrape_eba_regulations(session, params)

    if not updates:
        logger.warning("No updates found.")
        return

    logger.info(f"Found {len(updates)} updates. Processing first {args.limit}...")

    for i, update in enumerate(updates[:args.limit]):
        logger.info(f"Processing update {i+1}/{min(args.limit, len(updates))}: {update['title']}")
        print(f"\n{i+1}. {update['title']}")
        print(f"   \u001b[36mDate:\u001b[0m {update['date']}")
        print(f"   \u001b[36mURL:\u001b[0m {update['url']}")

        if not args.dry_run:
            save_raw_update(update, session)
            # Add delay between downloads
            if args.delay > 0:
                time.sleep(args.delay)

    if args.dry_run:
        logger.info("Dry run: No files were downloaded.")
        print("\n\u001b[33mDry run: No files were downloaded.\u001b[0m")

    session.close()
    logger.info("EBA scrape completed.")


if __name__ == "__main__":
    main()
