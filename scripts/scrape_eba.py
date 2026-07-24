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

# Constants
EBA_BASE_URL = "https://www.eba.europa.eu"
EBA_REGULATIONS_URL = "https://www.eba.europa.eu/regulation-and-policy"
RAW_DATA_DIR = "data/raw/eba"

# Ensure raw data directory exists
os.makedirs(RAW_DATA_DIR, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


def download_file(url: str, save_path: str) -> bool:
    """Download a file from a URL and save it to the specified path."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"⚠️ Failed to download {url}: {e}")
        return False


def scrape_eba_regulations() -> list[dict]:
    """
    Scrape the EBA regulations page for new updates.
    Returns a list of dictionaries with title, URL, and date.
    """
    updates = []
    
    try:
        response = requests.get(EBA_REGULATIONS_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all regulation items (adjust selector based on EBA's actual HTML structure)
        # Example: Look for <div class="regulation-item"> or similar
        regulation_items = soup.select("div.eba-publication, div.regulation-item, article")
        
        if not regulation_items:
            print("⚠️ No regulation items found. Check the HTML structure of EBA's website.")
            return updates
        
        for item in regulation_items:
            title_elem = item.select_one("h2, h3, .title")
            date_elem = item.select_one("time, .date, .publication-date")
            link_elem = item.select_one("a[href]")
            
            if not title_elem or not link_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            url = urljoin(EBA_BASE_URL, link_elem["href"])
            date = date_elem.get_text(strip=True) if date_elem else "Unknown"
            
            updates.append({
                "title": title,
                "url": url,
                "date": date,
            })
        
    except Exception as e:
        print(f"⚠️ Error scraping EBA website: {e}")
    
    return updates


def save_raw_update(update: dict) -> str:
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
    if download_file(update["url"], save_path):
        print(f"✅ Saved: {filename}")
        return save_path
    return ""


def main():
    parser = argparse.ArgumentParser(description="Scrape EBA regulatory updates.")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of updates to scrape.")
    parser.add_argument("--dry-run", action="store_true", help="Only list updates without downloading.")
    args = parser.parse_args()
    
    print("🔍 Scraping EBA regulatory updates...")
    updates = scrape_eba_regulations()
    
    if not updates:
        print("❌ No updates found.")
        return
    
    print(f"📋 Found {len(updates)} updates.")
    
    for i, update in enumerate(updates[:args.limit]):
        print(f"\n{i+1}. {update['title']}")
        print(f"   📅 Date: {update['date']}")
        print(f"   🔗 URL: {update['url']}")
        
        if not args.dry_run:
            save_raw_update(update)
    
    if args.dry_run:
        print("\n🔹 Dry run: No files were downloaded.")


if __name__ == "__main__":
    main()
