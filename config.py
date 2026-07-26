"""
Central configuration for the IT Risk Manager Agent.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional


class Config:
    """Central configuration class for the application."""

    # --- Directories ---
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    EBA_RAW_DATA_DIR: Path = RAW_DATA_DIR / "eba"
    MAS_RAW_DATA_DIR: Path = RAW_DATA_DIR / "mas"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    LOGS_DIR: Path = BASE_DIR / "logs"
    TESTS_DIR: Path = BASE_DIR / "tests"

    # --- Database ---
    DB_PATH: Path = PROCESSED_DIR / "regulatory_updates.db"

    # --- EBA Scraping ---
    EBA_BASE_URL: str = "https://www.eba.europa.eu"
    EBA_PUBLICATIONS_URL: str = f"{EBA_BASE_URL}/publications-and-media/publications"

    # --- MAS Scraping ---
    MAS_BASE_URL: str = "https://www.mas.gov.sg"
    MAS_PUBLICATIONS_URL: str = f"{MAS_BASE_URL}/publications"
    MAS_CONSULTATIONS_URL: str = f"{MAS_BASE_URL}/development/public-consultations"
    MAS_REGULATIONS_URL: str = f"{MAS_BASE_URL}/regulation/regulations-and-notices"

    # --- Scraping Settings ---
    DEFAULT_DELAY: float = 1.0  # seconds between requests
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # --- Ollama ---
    OLLAMA_MODEL: str = "mistral"
    OLLAMA_HOST: str = "http://localhost:11434"

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
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "7 days"
    LOG_LEVEL: str = "INFO"

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
