#!/usr/bin/env python3
"""
Scrape EBA (European Banking Authority) regulatory updates from their official publications page.
Saves raw data (PDF/HTML) to data/raw/eba/.

Target URL: https://www.eba.europa.eu/publications-and-media/publications?text=&document_type=248&media_topics=All
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
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
    "document_type": "248",  # 248 = Regulations/Guidelines (adjust as needed)
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
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


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
    
    if session is None:
        session = get_session()
    
    url = build_eba_url(params)
    
    try:
        print(f"🔍 Fetching {url}...")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # EBA's publication items are typically in div.publication-list-item or similar
        # Try multiple selectors to find publication items
        publication_selectors = [
            "div.publication-list-item",
            "div.views-row",
            "article.publication",
            "div.node--type-publication",
            "div.eba-publication",
            "tr.publication-row",  # If it's a table
        ]
        
        publication_items = []
        for selector in publication_selectors:
            items = soup.select(selector)
            if items:
                publication_items = items
                break
        
        if not publication_items:
            print("⚠️ No publication items found. Trying to find any links...")
            # Fallback: Find all links that look like publications
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                href = link["href"]
                if any(keyword in href.lower() for keyword in ["/publications", ".pdf", ".html", "/document"]):
                    title = link.get_text(strip=True) or "Untitled"
                    date_elem = link.find_previous("time") or link.find_previous(class_=re.compile("date", re.I))
                    date = date_elem.get_text(strip=True) if date_elem else "Unknown"
                    updates.append({
                        "title": title,
                        "url": urljoin(EBA_BASE_URL, href),
                        "date": date,
                    })
            return updates
        
        # Process each publication item
        for item in publication_items:
            # Try to find title, URL, and date
            title_elem = item.select_one("h2, h3, .title, a")
            date_elem = item.select_one("time, .date, .publication-date, .field-date")
            link_elem = item.select_one("a[href]")
            
            if not title_elem or not link_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            href = link_elem["href"]
            date = date_elem.get_text(strip=True) if date_elem else "Unknown"
            
            # Clean up title (remove extra whitespace, newlines, etc.)
            title = " ".join(title.split())
            
            full_url = urljoin(EBA_BASE_URL, href)
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
    safe_title = sanitize_filename(update["title"][:50])  # Truncate long titles
    ext = ".pdf" if update["url"].lower().endswith(".pdf") else ".html"
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
