#!/usr/bin/env python3
"""
Scrape EBA (European Banking Authority) regulatory updates from their official website.
Saves raw data (PDF/HTML) to data/raw/eba/.
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from datetime import datetime
import argparse
import time

# Constants
EBA_BASE_URL = "https://www.eba.europa.eu"
EBA_REGULATIONS_URL = "https://www.eba.europa.eu/regulation-and-policy"
RAW_DATA_DIR = "data/raw/eba"

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


def scrape_eba_regulations(session: requests.Session = None) -> list[dict]:
    """
    Scrape the EBA regulations page for new updates.
    Returns a list of dictionaries with title, URL, and date.
    """
    updates = []
    
    if session is None:
        session = get_session()
    
    try:
        print(f"🔍 Fetching {EBA_REGULATIONS_URL}...")
        response = session.get(EBA_REGULATIONS_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Try to find publication items - EBA uses specific classes
        # Common selectors for EBA's website:
        # - div.eba-publication
        # - div.views-field.views-field-title a
        # - div.node--type-publication
        
        # Try multiple selectors to find publication links
        selectors = [
            "div.eba-publication a",
            "div.views-field.views-field-title a",
            "div.node--type-publication a",
            "article a",
            "div.publication-list-item a",
            "h2 a, h3 a",  # Fallback: any heading links
        ]
        
        found_items = False
        for selector in selectors:
            items = soup.select(selector)
            if items:
                found_items = True
                break
        
        if not found_items:
            print("⚠️ No publication items found. Trying alternative approach...")
            # Try to find all links and filter for PDFs or regulation pages
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                href = link["href"]
                if any(ext in href.lower() for ext in [".pdf", ".html", "/regulation", "/publication"]):
                    title = link.get_text(strip=True) or "Untitled"
                    date_elem = link.find_previous("time") or link.find_previous(class_=re.compile("date", re.I))
                    date = date_elem.get_text(strip=True) if date_elem else "Unknown"
                    updates.append({
                        "title": title,
                        "url": urljoin(EBA_BASE_URL, href),
                        "date": date,
                    })
            
            if not updates:
                print("⚠️ Could not find any regulation links. The website structure may have changed.")
                print("💡 Tip: Check the HTML structure of https://www.eba.europa.eu/regulation-and-policy manually.")
            return updates
        
        # Process found items
        for item in items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if not href:
                continue
            
            # Try to find date from parent or sibling elements
            date_elem = item.find_previous("time") or item.find_next("time") or \
                        item.find_previous(class_=re.compile("date", re.I)) or \
                        item.find_next(class_=re.compile("date", re.I))
            date = date_elem.get_text(strip=True) if date_elem else "Unknown"
            
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
    args = parser.parse_args()
    
    print("🔍 Scraping EBA regulatory updates...")
    
    # Create a session for all requests
    session = get_session()
    
    # Add delay to avoid rate limiting
    if args.delay > 0:
        time.sleep(args.delay)
    
    updates = scrape_eba_regulations(session)
    
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
