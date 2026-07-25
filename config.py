"""
Central configuration for the IT Risk Manager Agent.
"""

import os
from pathlib import Path
from typing import List, Optional


class Config:
    """Central configuration class for the application."""

    # --- Directories ---
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw" / "eba"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    LOGS_DIR: Path = BASE_DIR / "logs"
    TESTS_DIR: Path = BASE_DIR / "tests"

    # --- Database ---
    DB_PATH: Path = PROCESSED_DIR / "regulatory_updates.db"

    # --- EBA Scraping (Legacy) ---
    EBA_BASE_URL: str = "https://www.eba.europa.eu"
    EBA_PUBLICATIONS_URL: str = f"{EBA_BASE_URL}/publications-and-media/publications"
    DEFAULT_DELAY: float = 1.0  # seconds between requests
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # --- Ollama ---
    OLLAMA_MODEL: str = "mistral"
    OLLAMA_HOST: str = "http://localhost:11434"

    # --- Apify API (New) ---
    # Get API key from environment variable or use None
    APIFY_API_KEY: Optional[str] = os.getenv("APIFY_API_KEY")
    # Updated actor ID - check https://apify.com/actors for the correct one
    APIFY_EBA_ACTOR_ID: str = "apify/eu-business-data-search"  # Try this first
    # Alternative actor IDs (uncomment if the above doesn't work)
    # APIFY_EBA_ACTOR_ID: str = "apify/eba-regulations"
    # APIFY_EBA_ACTOR_ID: str = "eu-business-data-search"
    APIFY_BASE_URL: str = "https://api.apify.com/v2"
    APIFY_DEFAULT_DATASET: str = "eba-regulations"  # Default dataset for EBA regulations

    # --- Risk Areas ---
    RISK_AREAS: List[str] = [
        "IT Risk Management",
        "Cybersecurity",
        "AI Risk",
        "Compliance",
        "Governance",
        "Operational Risk",
        "Data Protection",
        "Third-Party Risk",
        "Cloud Computing",
        "Digital Operational Resilience (DORA)",
        "Financial Stability",
        "Resolution Planning",
        "Capital Requirements",
        "Liquidity Risk",
        "Market Risk",
        "Credit Risk",
    ]

    # --- Logging ---
    LOG_FILE: Path = LOGS_DIR / "{time}.log"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "7 days"
    LOG_LEVEL: str = "INFO"

    @classmethod
    def init_dirs(cls) -> None:
        """Initialize all required directories."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)

    @classmethod
    def check_apify_config(cls) -> bool:
        """Check if Apify API is configured."""
        if cls.APIFY_API_KEY is None:
            return False
        return True

    @classmethod
    def get_apify_actor_id(cls) -> str:
        """Get the Apify actor ID, trying alternatives if needed."""
        # Try the primary actor ID first
        primary_actor = "apify/eu-business-data-search"
        
        # List of alternative actor IDs to try
        alternatives = [
            "apify/eba-regulations",
            "eu-business-data-search",
            "apify/eu-financial-data",
        ]
        
        # For now, return the primary actor
        # In a real implementation, you could test which one works
        return primary_actor
