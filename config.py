"""
Central configuration for the IT Risk Manager Agent.
Uses environment variables for flexible configuration.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class for the application."""

    # --- Directories ---
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    RAW_DATA_DIR: Path = Path(os.getenv("RAW_DATA_DIR", str(DATA_DIR / "raw")))
    EBA_RAW_DATA_DIR: Path = RAW_DATA_DIR / "eba"
    MAS_RAW_DATA_DIR: Path = RAW_DATA_DIR / "mas"
    PROCESSED_DIR: Path = Path(os.getenv("PROCESSED_DIR", str(DATA_DIR / "processed")))
    LOGS_DIR: Path = Path(os.getenv("LOGS_DIR", str(BASE_DIR / "logs")))
    TESTS_DIR: Path = BASE_DIR / "tests"

    # --- Database ---
    DB_PATH: Path = Path(os.getenv("DB_PATH", str(PROCESSED_DIR / "regulatory_updates.db")))

    # --- EBA Scraping ---
    EBA_BASE_URL: str = os.getenv("EBA_BASE_URL", "https://www.eba.europa.eu")
    EBA_PUBLICATIONS_URL: str = f"{EBA_BASE_URL}/publications-and-media/publications"

    # --- MAS Scraping ---
    MAS_BASE_URL: str = os.getenv("MAS_BASE_URL", "https://www.mas.gov.sg")
    MAS_PUBLICATIONS_URL: str = f"{MAS_BASE_URL}/publications"
    MAS_CONSULTATIONS_URL: str = f"{MAS_BASE_URL}/development/public-consultations"
    MAS_REGULATIONS_URL: str = f"{MAS_BASE_URL}/regulation/regulations-and-notices"

    # --- Scraping Settings ---
    DEFAULT_DELAY: float = float(os.getenv("DEFAULT_DELAY", "1.0"))  # seconds between requests
    USER_AGENT: str = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    # --- Ollama ---
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

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

    # --- Sources ---
    SOURCES: List[str] = ["EBA", "MAS"]

    # --- Logging ---
    LOG_ROTATION: str = os.getenv("LOG_ROTATION", "1 day")
    LOG_RETENTION: str = os.getenv("LOG_RETENTION", "7 days")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def get_log_file(cls) -> Path:
        """
        Generate a dynamic log filename with current timestamp.
        
        Returns:
            Path: Full path to the log file (e.g., logs/app_2026-07-26.log)
        """
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d")
        return cls.LOGS_DIR / f"app_{timestamp}.log"

    @classmethod
    def init_dirs(cls) -> None:
        """Initialize all required directories."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.RAW_DATA_DIR.mkdir(exist_ok=True)
        cls.EBA_RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.MAS_RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
