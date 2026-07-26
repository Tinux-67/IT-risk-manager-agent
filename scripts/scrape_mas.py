#!/usr/bin/env python3
"""
Scrape MAS (Monetary Authority of Singapore) regulatory updates from their official websites.
Saves raw data (PDF/HTML) to data/raw/mas/.

Target URLs:
- https://www.mas.gov.sg/publications
- https://www.mas.gov.sg/development/public-consultations
- https://www.mas.gov.sg/regulation/regulations-and-notices
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
    save_raw_update,
)

# Ensure raw data directory exists
os.makedirs(Config.MAS_RAW_DATA_DIR, exist_ok=True)

# Configure logging
logger.add(
    Config.LOG_FILE,
    rotation=Config.LOG_ROTATION,
    retention=Config.LOG_RETENTION,
    level=Config.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
)


def scrape_mas_publications(session: requests.Session = None) -> list[dict]:
    """
    Scrape the MAS publications page for regulatory updates.
    Returns a list of dictionaries with title, URL, and date.
    
    Args:
        session: Optional requests.Session for connection reuse.
        
    Returns:
        list[dict]: List of updates with 'title', 'url', 'date', and 'source'.
    """
    updates = []
    seen_urls = set()

    if session is None:
        session = get_session()

    url = Config.MAS_PUBLICATIONS_URL

    try:
        logger.info(f"Fetching MAS publications from: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all links that point to documents
        # MAS typically has links to PDFs and detail pages
        all_links = soup.find_all("a", href=True)

        for link in all_links:
            href = link["href"]
            full_url = urljoin(Config.MAS_BASE_URL, href)

            # Skip if we've already seen this URL
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Only process direct file links (PDFs, etc.)
            if not any(href.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xlsx", ".xls"]):
                # Check if it's a detail page that might contain a document
                if not any(segment in href.lower() for segment in ["publication", "consultation", "regulation", "notice"]):
                    continue

            # Extract title from link text or filename
            title = link.get_text(strip=True)
            if not title or title == "":
                filename = os.path.basename(href)
                title = os.path.splitext(filename)[0]
                title = sanitize_filename(title)
            else:
                title = sanitize_filename(title)

            # Try to extract date from multiple sources
            date = "Unknown"

            # 1. Try to find date in parent elements
            parent = link.parent
            for _ in range(3):
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
                "source": "MAS_Publications",
            })

        logger.success(f"Found {len(updates)} updates on MAS publications page")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error("403 Forbidden: The website may be blocking scrapers.")
            logger.warning("Try adding a delay between requests or using a proxy.")
        else:
            logger.error(f"HTTP Error: {e}")
    except Exception as e:
        logger.error(f"Error scraping MAS publications website: {e}")

    return updates


def scrape_mas_consultations(session: requests.Session = None) -> list[dict]:
    """
    Scrape the MAS public consultations page for regulatory updates.
    Returns a list of dictionaries with title, URL, and date.
    
    Args:
        session: Optional requests.Session for connection reuse.
        
    Returns:
        list[dict]: List of updates with 'title', 'url', 'date', and 'source'.
    """
    updates = []
    seen_urls = set()

    if session is None:
        session = get_session()

    url = Config.MAS_CONSULTATIONS_URL

    try:
        logger.info(f"Fetching MAS consultations from: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all consultation links
        all_links = soup.find_all("a", href=True)

        for link in all_links:
            href = link["href"]
            full_url = urljoin(Config.MAS_BASE_URL, href)

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Only process consultation-related links
            if "consultation" not in href.lower() and "consultations" not in href.lower():
                continue

            title = link.get_text(strip=True)
            if not title:
                filename = os.path.basename(href)
                title = os.path.splitext(filename)[0]
                title = sanitize_filename(title)
            else:
                title = sanitize_filename(title)

            date = "Unknown"
            parent = link.parent
            for _ in range(3):
                date_elem = parent.find(class_=re.compile("date", re.I)) if parent else None
                if date_elem:
                    date = date_elem.get_text(strip=True)
                    break
                parent = parent.parent if parent else None

            if date == "Unknown":
                date = extract_date_from_url(href)

            if date == "Unknown":
                date = extract_date_from_filename(href)

            updates.append({
                "title": title,
                "url": full_url,
                "date": date,
                "source": "MAS_Consultations",
            })

        logger.success(f"Found {len(updates)} updates on MAS consultations page")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error scraping MAS consultations: {e}")
    except Exception as e:
        logger.error(f"Error scraping MAS consultations: {e}")

    return updates


def scrape_mas_regulations(session: requests.Session = None) -> list[dict]:
    """
    Scrape the MAS regulations and notices page for regulatory updates.
    Returns a list of dictionaries with title, URL, and date.
    
    Args:
        session: Optional requests.Session for connection reuse.
        
    Returns:
        list[dict]: List of updates with 'title', 'url', 'date', and 'source'.
    """
    updates = []
    seen_urls = set()

    if session is None:
        session = get_session()

    url = Config.MAS_REGULATIONS_URL

    try:
        logger.info(f"Fetching MAS regulations from: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all regulation/notice links
        all_links = soup.find_all("a", href=True)

        for link in all_links:
            href = link["href"]
            full_url = urljoin(Config.MAS_BASE_URL, href)

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Only process regulation/notice-related links
            if not any(segment in href.lower() for segment in ["regulation", "notice", "notices", "legislation"]):
                continue

            title = link.get_text(strip=True)
            if not title:
                filename = os.path.basename(href)
                title = os.path.splitext(filename)[0]
                title = sanitize_filename(title)
            else:
                title = sanitize_filename(title)

            date = "Unknown"
            parent = link.parent
            for _ in range(3):
                date_elem = parent.find(class_=re.compile("date", re.I)) if parent else None
                if date_elem:
                    date = date_elem.get_text(strip=True)
                    break
                parent = parent.parent if parent else None

            if date == "Unknown":
                date = extract_date_from_url(href)

            if date == "Unknown":
                date = extract_date_from_filename(href)

            updates.append({
                "title": title,
                "url": full_url,
                "date": date,
                "source": "MAS_Regulations",
            })

        logger.success(f"Found {len(updates)} updates on MAS regulations page")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error scraping MAS regulations: {e}")
    except Exception as e:
        logger.error(f"Error scraping MAS regulations: {e}")

    return updates


def scrape_all_mas(session: requests.Session = None) -> list[dict]:
    """
    Scrape all MAS pages (publications, consultations, regulations).
    Returns a combined list of updates.
    
    Args:
        session: Optional requests.Session for connection reuse.
        
    Returns:
        list[dict]: Combined list of updates from all MAS pages.
    """
    all_updates = []

    if session is None:
        session = get_session()

    # Scrape each MAS page
    all_updates.extend(scrape_mas_publications(session))
    all_updates.extend(scrape_mas_consultations(session))
    all_updates.extend(scrape_mas_regulations(session))

    # Remove duplicates by URL
    seen_urls = set()
    unique_updates = []
    for update in all_updates:
        if update["url"] not in seen_urls:
            seen_urls.add(update["url"])
            unique_updates.append(update)

    logger.success(f"Total unique MAS updates found: {len(unique_updates)}")
    return unique_updates


def main():
    parser = argparse.ArgumentParser(description="Scrape MAS regulatory updates.")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of updates to scrape.")
    parser.add_argument("--dry-run", action="store_true", help="Only list updates without downloading.")
    parser.add_argument("--delay", type=float, default=Config.DEFAULT_DELAY,
                        help=f"Delay between requests in seconds (default: {Config.DEFAULT_DELAY}).")
    parser.add_argument("--page", type=str, default="all",
                        choices=["all", "publications", "consultations", "regulations"],
                        help="Which MAS page to scrape (default: all).")
    args = parser.parse_args()

    logger.info("Starting MAS scrape...")

    # Create a session for all requests
    session = get_session()

    # Add delay to avoid rate limiting
    if args.delay > 0:
        logger.info(f"Waiting {args.delay} seconds before first request...")
        time.sleep(args.delay)

    # Scrape based on page selection
    if args.page == "publications":
        updates = scrape_mas_publications(session)
    elif args.page == "consultations":
        updates = scrape_mas_consultations(session)
    elif args.page == "regulations":
        updates = scrape_mas_regulations(session)
    else:
        updates = scrape_all_mas(session)

    if not updates:
        logger.warning("No updates found.")
        return

    logger.info(f"Found {len(updates)} updates. Processing first {args.limit}...")

    for i, update in enumerate(updates[:args.limit]):
        logger.info(f"Processing update {i+1}/{min(args.limit, len(updates))}: {update['title']}")
        print(f"\n{i+1}. {update['title']}")
        print(f"   \u001b[36mSource:\u001b[0m {update.get('source', 'MAS')}")
        print(f"   \u001b[36mDate:\u001b[0m {update['date']}")
        print(f"   \u001b[36mURL:\u001b[0m {update['url']}")

        if not args.dry_run:
            save_raw_update(update, str(Config.MAS_RAW_DATA_DIR), session)
            # Add delay between downloads
            if args.delay > 0:
                time.sleep(args.delay)

    if args.dry_run:
        logger.info("Dry run: No files were downloaded.")
        print("\n\u001b[33mDry run: No files were downloaded.\u001b[0m")

    session.close()
    logger.info("MAS scrape completed.")


if __name__ == "__main__":
    main()
