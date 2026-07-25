#!/usr/bin/env python3
"""
Fetch EBA (European Banking Authority) regulatory updates using the Apify EU Business Data Search API.
Saves structured data (JSON/CSV) to data/raw/eba/.

This script replaces the legacy scrape_eba.py and provides:
- More reliable data fetching (official API)
- Structured output (JSON, CSV, Excel)
- Support for 21 EU regulatory sources (EBA, ECB, ESMA, EIOPA)
- Better filtering and automation

NOTE: You need a valid Apify API key. Get one at https://console.apify.com/
"""

import os
import json
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Union

import requests
from loguru import logger

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config

# Configure logging
logger.add(
    Config.LOG_FILE,
    rotation=Config.LOG_ROTATION,
    retention=Config.LOG_RETENTION,
    level=Config.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
)


class ApifyClient:
    """Client for interacting with the Apify API."""

    # List of possible actor IDs for EU business data
    POSSIBLE_ACTOR_IDS = [
        "apify/eu-business-data-search",  # Primary choice
        "apify/eba-regulations",           # EBA-specific
        "eu-business-data-search",        # Without apify/ prefix
        "apify/eu-financial-data",        # Alternative
    ]

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Apify client."""
        self.api_key = api_key or Config.APIFY_API_KEY
        if not self.api_key:
            raise ValueError(
                "Apify API key is required. Set APIFY_API_KEY environment variable "
                "or pass it to the client."
            )
        self.base_url = Config.APIFY_BASE_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        logger.success("Apify client initialized")

    def find_working_actor(self) -> Optional[str]:
        """
        Find a working Apify actor ID by testing each possibility.
        
        Returns:
            The first working actor ID, or None if none work
        """
        for actor_id in self.POSSIBLE_ACTOR_IDS:
            if self._test_actor(actor_id):
                logger.success(f"Found working actor: {actor_id}")
                return actor_id
        
        logger.error(f"No working actor found. Tried: {', '.join(self.POSSIBLE_ACTOR_IDS)}")
        return None

    def _test_actor(self, actor_id: str) -> bool:
        """Test if an actor exists and is accessible."""
        url = f"{self.base_url}/acts/{actor_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def run_actor(self, actor_id: Optional[str] = None, input_data: Dict = None, wait_for_finish: bool = True) -> Dict:
        """
        Run an Apify actor and return the results.
        
        Args:
            actor_id: The Apify actor ID (optional, will try to find working one)
            input_data: Input parameters for the actor
            wait_for_finish: Whether to wait for the actor to finish
            
        Returns:
            Dictionary with actor run results
        """
        # If no actor_id provided, find a working one
        if actor_id is None:
            actor_id = self.find_working_actor()
            if actor_id is None:
                raise ValueError("No working Apify actor found. Check your actor ID.")

        url = f"{self.base_url}/acts/{actor_id}/runs"
        
        if input_data is None:
            input_data = {}
            
        payload = {
            "input": input_data,
            "waitForFinish": wait_for_finish,
        }
        
        try:
            logger.info(f"Running Apify actor: {actor_id}")
            response = requests.post(url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            logger.success(f"Apify actor run started: {result.get('id')}")
            
            if wait_for_finish:
                return self._get_run_results(actor_id, result["id"])
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error running Apify actor {actor_id}: {e}")
            
            # If we got a 404, try the next actor
            if e.response.status_code == 404 and actor_id in self.POSSIBLE_ACTOR_IDS:
                next_index = self.POSSIBLE_ACTOR_IDS.index(actor_id) + 1
                if next_index < len(self.POSSIBLE_ACTOR_IDS):
                    next_actor = self.POSSIBLE_ACTOR_IDS[next_index]
                    logger.info(f"Trying next actor: {next_actor}")
                    return self.run_actor(next_actor, input_data, wait_for_finish)
            
            raise
        except Exception as e:
            logger.error(f"Error running Apify actor {actor_id}: {e}")
            raise

    def _get_run_results(self, actor_id: str, run_id: str) -> Dict:
        """Get the results of a finished Apify actor run."""
        url = f"{self.base_url}/acts/{actor_id}/runs/{run_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting Apify run results: {e}")
            raise

    def get_dataset_items(self, dataset_id: str, limit: int = 100) -> List[Dict]:
        """
        Get items from an Apify dataset.
        
        Args:
            dataset_id: The Apify dataset ID
            limit: Maximum number of items to return
            
        Returns:
            List of items from the dataset
        """
        url = f"{self.base_url}/datasets/{dataset_id}/items"
        params = {"limit": limit}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=120)
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            logger.error(f"Error getting Apify dataset items: {e}")
            raise


def fetch_eba_updates(
    api_key: Optional[str] = None,
    days_back: int = 30,
    source: str = "eba",
    output_format: str = "json",
    limit: int = 50,
) -> List[Dict]:
    """
    Fetch EBA regulatory updates using the Apify EU Business Data Search API.
    
    Args:
        api_key: Apify API key (optional, uses Config.APIFY_API_KEY if not provided)
        days_back: Number of days to look back for updates
        source: Source filter (eba, ecb, esma, eiopa, or all)
        output_format: Output format (json, csv, excel)
        limit: Maximum number of results to return
        
    Returns:
        List of regulatory updates
    """
    try:
        client = ApifyClient(api_key)
        
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # Prepare input for the Apify actor
        input_data = {
            "search": "",  # Empty search returns all results
            "source": source.upper(),
            "startDate": start_date,
            "endDate": end_date,
            "limit": limit,
            "outputFormat": output_format,
        }
        
        logger.info(f"Fetching EBA updates from {start_date} to {end_date}")
        
        # Run the actor (will try multiple actor IDs if needed)
        result = client.run_actor(None, input_data)  # Pass None to auto-find actor
        
        # Extract and process the results
        updates = []
        
        # Check if we got a dataset ID
        if "defaultDatasetId" in result:
            dataset_id = result["defaultDatasetId"]
            items = client.get_dataset_items(dataset_id, limit=limit)
            
            for item in items:
                update = _process_apify_item(item, source)
                if update:
                    updates.append(update)
        
        # If no dataset, try to extract from output
        elif "output" in result:
            output = result["output"]
            if isinstance(output, dict) and "results" in output:
                for item in output["results"][:limit]:
                    update = _process_apify_item(item, source)
                    if update:
                        updates.append(update)
        
        logger.success(f"Fetched {len(updates)} updates from Apify API")
        return updates
        
    except Exception as e:
        logger.error(f"Error fetching EBA updates: {e}")
        return []


def _process_apify_item(item: Dict, source: str) -> Optional[Dict]:
    """
    Process a raw Apify item into a standardized format.
    
    Args:
        item: Raw item from Apify API
        source: Source of the data (eba, ecb, etc.)
        
    Returns:
        Processed update dictionary or None if invalid
    """
    try:
        # Extract basic fields
        title = item.get("title", item.get("name", "Untitled"))
        url = item.get("url", item.get("sourceUrl", ""))
        date = item.get("date", item.get("publicationDate", "Unknown"))
        
        # Extract text content
        text = item.get("text", item.get("description", item.get("content", "")))
        
        # Extract additional metadata
        source_url = item.get("sourceUrl", url)
        file_type = item.get("type", "document")
        
        # Create standardized output
        update = {
            "title": title,
            "url": url,
            "source_url": source_url,
            "date": date,
            "text": text,
            "source": source,
            "file_type": file_type,
            "raw_data": item,  # Keep raw data for reference
        }
        
        return update
        
    except Exception as e:
        logger.warning(f"Error processing Apify item: {e}")
        return None


def save_updates(updates: List[Dict], output_dir: Path = Config.RAW_DATA_DIR) -> List[str]:
    """
    Save updates to files in the output directory.
    
    Args:
        updates: List of updates to save
        output_dir: Directory to save files to
        
    Returns:
        List of saved file paths
    """
    saved_files = []
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for i, update in enumerate(updates, 1):
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = _sanitize_filename(update["title"][:50])
            
            # Use JSON format by default
            filename = f"{timestamp}_{i:03d}_{safe_title}.json"
            file_path = output_dir / filename
            
            # Save as JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(update, f, indent=2, ensure_ascii=False)
            
            logger.success(f"Saved update: {filename}")
            saved_files.append(str(file_path))
            
        except Exception as e:
            logger.error(f"Error saving update {i}: {e}")
    
    return saved_files


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    import re
    from urllib.parse import unquote
    
    # Decode URL-encoded characters first
    filename = unquote(filename)
    # Remove invalid characters
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', " ", filename).strip()
    return filename


def main():
    parser = argparse.ArgumentParser(
        description="Fetch EBA regulatory updates using Apify EU Business Data Search API"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back for updates (default: 30)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="eba",
        choices=["eba", "ecb", "esma", "eiopa", "all"],
        help="Source filter: eba, ecb, esma, eiopa, or all (default: eba)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of results to return (default: 50)",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="json",
        choices=["json", "csv", "excel"],
        help="Output format for Apify API (default: json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only fetch and display updates without saving",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Apify API key (overrides APIFY_API_KEY environment variable)",
    )
    parser.add_argument(
        "--list-actors",
        action="store_true",
        help="List available Apify actors for EU business data",
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Apify EBA data fetch...")
    
    # List actors and exit if requested
    if args.list_actors:
        print("Available Apify actors for EU business data:")
        for i, actor_id in enumerate(ApifyClient.POSSIBLE_ACTOR_IDS, 1):
            print(f"  {i}. {actor_id}")
        return
    
    # Check if API key is available
    api_key = args.api_key or Config.APIFY_API_KEY
    if not api_key:
        logger.error(
            "Apify API key is required. Set APIFY_API_KEY environment variable "
            "or use --api-key argument."
        )
        print("\u274c Error: Apify API key is required.")
        print("   Set APIFY_API_KEY environment variable or use --api-key argument.")
        print("\n   To get an API key:")
        print("   1. Go to https://console.apify.com/")
        print("   2. Sign up (free tier available)")
        print("   3. Get your API key from Settings > API Keys")
        return
    
    # Fetch updates
    updates = fetch_eba_updates(
        api_key=api_key,
        days_back=args.days,
        source=args.source,
        output_format=args.output_format,
        limit=args.limit,
    )
    
    if not updates:
        logger.warning("No updates fetched from Apify API")
        print("\u274c No updates fetched. Check logs for details.")
        print("\nPossible issues:")
        print("  1. Invalid API key - check your APIFY_API_KEY")
        print("  2. Actor not found - try --list-actors to see available actors")
        print("  3. No data available for the selected date range")
        return
    
    logger.info(f"Fetched {len(updates)} updates")
    
    # Display updates
    for i, update in enumerate(updates, 1):
        print(f"\n{i}. {update['title']}")
        print(f"   \u001b[36mSource:\u001b[0m {update['source']}")
        print(f"   \u001b[36mDate:\u001b[0m {update['date']}")
        print(f"   \u001b[36mURL:\u001b[0m {update['url']}")
    
    # Save updates if not dry run
    if not args.dry_run:
        saved_files = save_updates(updates)
        logger.success(f"Saved {len(saved_files)} files to {Config.RAW_DATA_DIR}")
        print(f"\n\u001b[32m\u001b[1mSaved {len(saved_files)} files to {Config.RAW_DATA_DIR}/\u001b[0m")
    else:
        logger.info("Dry run: No files were saved")
        print("\n\u001b[33mDry run: No files were saved.\u001b[0m")


if __name__ == "__main__":
    main()
