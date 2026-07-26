#!/usr/bin/env python3
"""
Scrape EBA (European Banking Authority) regulatory updates from their official publications page.
Saves raw data (PDF/HTML) to data/raw/eba/.

Target URL: https://www.eba.europa.eu/publications-and-media/publications
"""

import os
import re
import time
import argparse
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import Config
from scripts.scraping_utils import (
    get_session,
    sanitize_filename,
    extract_date_from_url,
    extract_date_from_filename,
    download_file,
    build_url,
    save_raw_update,
)

# Ensure raw data directory exists
os.makedirs(Config.EBA_RAW_DATA_DIR, exist_ok=True)

# Configure logging
logger.add(
    Config.LOG_FILE,
    rotation=Config.LOG_ROTATION,
    retention=Config.LOG_RETENTION,
    level=Config.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
)


def build_eba_url(params: dict = None) -> str:
    """
    Build the EBA publications URL with query parameters.
    
    Args:
        params: Dictionary of query parameters (default: {"document_type": "248"}).
        
    Returns:
        str: Full EBA publications URL with query parameters.
    """
    if params is None:
        params = {"document_type": "248"}  # Default: Regulations/Guidelines
    return build_url(Config.EBA_PUBLICATIONS_URL, params)


def scrape_eba_regulations(session: requests.Session = None, params: dict = None) -> list[dict]:
    """
    Scrape the EBA publications page for regulatory updates.
    Returns a list of dictionaries with title, URL, and date.
    
    Args:
        session: Optional requests.Session for connection reuse.
        params: Dictionary of query parameters for the EBA URL.
        
    Returns:
        list[dict]: List of updates with 'title', 'url', 'date', and 'source'.
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
                "source": "EBA",
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
    args = parser.parse_args()

    logger.info("Starting EBA scrape...")

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
            save_raw_update(update, str(Config.EBA_RAW_DATA_DIR), session)
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
