#!/usr/bin/env python3
"""
Fetch EBA (European Banking Authority) regulatory updates using the Apify EU Business Data Search API.
Saves structured data (JSON/CSV) to data/raw/eba/.

This script replaces the legacy scrape_eba.py and provides:
- More reliable data fetching (official API)
- Structured output (JSON, CSV, Excel)
- Support for 21 EU regulatory sources (EBA, ECB, ESMA, EIOPA)
- Better filtering and automation
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

    def run_actor(self, actor_id: str, input_data: Dict, wait_for_finish: bool = True) -> Dict:
        """
        Run an Apify actor and return the results.
        
        Args:
            actor_id: The Apify actor ID (e.g., 'eu-business-data-search')
            input_data: Input parameters for the actor
            wait_for_finish: Whether to wait for the actor to finish
            
        Returns:
            Dictionary with actor run results
        """
        url = f"{self.base_url}/acts/{actor_id}/runs"
        
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
            logger.error(f"HTTP Error running Apify actor: {e}")
            raise
        except Exception as e:
            logger.error(f"Error running Apify actor: {e}")
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
        
        # Run the actor
        result = client.run_actor(Config.APIFY_EBA_ACTOR_ID, input_data)
        
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
    
    args = parser.parse_args()
    
    logger.info("Starting Apify EBA data fetch...")
    
    # Check if API key is available
    api_key = args.api_key or Config.APIFY_API_KEY
    if not api_key:
        logger.error(
            "Apify API key is required. Set APIFY_API_KEY environment variable "
            "or use --api-key argument."
        )
        print("\u274c Error: Apify API key is required.")
        print("   Set APIFY_API_KEY environment variable or use --api-key argument.")
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
        return
    
    logger.info(f"Fetched {len(updates)} updates")
    
    # Display updates
    for i, update in enumerate(updates, 1):
        print(f"\n{i}. {update['title']}")
        print(f"   [36mSource:[0m {update['source']}")
        print(f"   [36mDate:[0m {update['date']}")
        print(f"   [36mURL:[0m {update['url']}")
    
    # Save updates if not dry run
    if not args.dry_run:
        saved_files = save_updates(updates)
        logger.success(f"Saved {len(saved_files)} files to {Config.RAW_DATA_DIR}")
        print(f"\n[32m[1mSaved {len(saved_files)} files to {Config.RAW_DATA_DIR}/[0m")
    else:
        logger.info("Dry run: No files were saved")
        print("\n[33mDry run: No files were saved.[0m")


if __name__ == "__main__":
    main()
