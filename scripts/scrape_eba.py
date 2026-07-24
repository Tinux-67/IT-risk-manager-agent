#!/usr/bin/env python3
"""
Scrape EBA (European Banking Authority) regulatory updates from their official publications page.
Saves raw data (PDF/HTML) to data/raw/eba/.

Target URL: https://www.eba.europa.eu/publications-and-media/publications
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode, unquote
import re
from datetime import datetime
import argparse
import time

# Constants
EBA_BASE_URL = "https://www.eba.europa.eu"
EBA_PUBLICATIONS_URL = "https://www.eba.europa.eu/publications-and-media/publications"
RAW_DATA_DIR = "data/raw/eba"

# Default filter parameters for regulations/guidelines
DEFAULT_PARAMS = {
    "text": "",
    "document_type": "248",  # 248 = Regulations/Guidelines
    "media_topics": "All",
}

# User-Agent to mimic a browser
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Ensure raw data directory exists
os.makedirs(RAW_DATA_DIR, exist_ok=True)


def get_session():
    """Create a requests session with headers to mimic a browser."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
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
        
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"⚠️ Failed to download {url}: {e}")
        return False


def build_eba_url(params: dict = None) -> str:
    """Build the EBA publications URL with query parameters."""
    if params is None:
        params = DEFAULT_PARAMS.copy()
    return f"{EBA_PUBLICATIONS_URL}?{urlencode(params)}"


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
        print(f"🔍 Fetching {url}...")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # EBA's publication links are typically in a list with PDF/HTML links
        # The structure seems to be: <a href="/sites/default/files/.../document.pdf">
        # We'll look for all <a> tags with href containing /sites/default/files/
        
        all_links = soup.find_all("a", href=True)
        
        for link in all_links:
            href = link["href"]
            full_url = urljoin(EBA_BASE_URL, href)
            
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
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("⚠️ 403 Forbidden: The website may be blocking scrapers.")
            print("💡 Try adding a delay between requests or using a proxy.")
        else:
            print(f"⚠️ HTTP Error: {e}")
    except Exception as e:
        print(f"⚠️ Error scraping EBA website: {e}")
    
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
    save_path = os.path.join(RAW_DATA_DIR, filename)
    
    # Download and save
    if download_file(update["url"], save_path, session):
        print(f"✅ Saved: {filename}")
        return save_path
    return ""


def main():
    parser = argparse.ArgumentParser(description="Scrape EBA regulatory updates.")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of updates to scrape.")
    parser.add_argument("--dry-run", action="store_true", help="Only list updates without downloading.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds (default: 1.0).")
    parser.add_argument("--document-type", type=str, default="248", 
                        help="Filter by document type (default: 248 for regulations/guidelines).")
    parser.add_argument("--all-types", action="store_true", 
                        help="Scrape all document types (no filter).")
    args = parser.parse_args()
    
    print("🔍 Scraping EBA regulatory updates...")
    
    # Build parameters
    params = DEFAULT_PARAMS.copy()
    if args.all_types:
        params.pop("document_type", None)  # Remove document_type filter
    else:
        params["document_type"] = args.document_type
    
    # Create a session for all requests
    session = get_session()
    
    # Add delay to avoid rate limiting
    if args.delay > 0:
        time.sleep(args.delay)
    
    updates = scrape_eba_regulations(session, params)
    
    if not updates:
        print("❌ No updates found.")
        return
    
    print(f"📋 Found {len(updates)} updates.")
    
    for i, update in enumerate(updates[:args.limit]):
        print(f"\n{i+1}. {update['title']}")
        print(f"   📅 Date: {update['date']}")
        print(f"   🔗 URL: {update['url']}")
        
        if not args.dry_run:
            save_raw_update(update, session)
            # Add delay between downloads
            if args.delay > 0:
                time.sleep(args.delay)
    
    if args.dry_run:
        print("\n🔹 Dry run: No files were downloaded.")
    
    session.close()


if __name__ == "__main__":
    main()
