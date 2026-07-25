#!/usr/bin/env python3
"""
Process raw regulatory updates (EBA and MAS) and store them in a SQLite database.
Extracts metadata, text, and categorizes updates by risk area using Ollama (Mistral-7B).
"""

import os
import re
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

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


# LLM Prompts for Ollama
LLM_PROMPTS = {
    "categorize": """
    You are a regulatory compliance expert. Categorize the following regulatory text into ONE of these risk areas:
    {risk_areas}
    
    Respond with ONLY the name of the most relevant risk area. Do not add any explanation or text.
    If none fit, respond with "Other".
    
    Text: {text}
    
    Risk Area:
    """,
    "assess_urgency": """
    You are a risk management expert. Assess the urgency level of the following regulatory text.
    Respond with ONLY one of: Urgent, High, Medium, Low.
    Do not add any explanation or text.
    
    Consider:
    - "Urgent" for immediate action required, deadlines, or critical risks.
    - "High" for significant changes with near-term deadlines.
    - "Medium" for standard updates with reasonable timelines.
    - "Low" for informational or long-term guidance.
    
    Text: {text}
    
    Urgency:
    """,
    "summarize": """
    You are a compliance assistant. Provide a concise summary (2-3 sentences) of the following regulatory text.
    Focus on the key requirements, changes, or obligations.
    
    Text: {text}
    
    Summary:
    """,
}


def get_ollama_response(prompt: str, model: str = Config.OLLAMA_MODEL) -> Optional[str]:
    """
    Get a response from Ollama's LLM (Mistral-7B by default).
    Returns the generated text or None if Ollama is not available.
    """
    try:
        import ollama
        logger.debug(f"Generating LLM response for prompt (length: {len(prompt)} chars)")
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={"temperature": 0.1, "max_tokens": 200},
        )
        return response["response"].strip()
    except ImportError:
        logger.warning("Ollama is not installed. Install with: pip install ollama")
        return None
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return None


def init_db() -> sqlite3.Connection:
    """Initialize the SQLite database and create tables."""
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)

    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source_url TEXT,
            file_path TEXT,
            publication_date TEXT,
            processed_date TEXT DEFAULT CURRENT_TIMESTAMP,
            raw_text TEXT,
            summary TEXT,
            risk_area TEXT,
            urgency_level TEXT,
            source TEXT DEFAULT 'EBA',
            is_processed BOOLEAN DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_publication_date ON updates(publication_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_area ON updates(risk_area)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_urgency ON updates(urgency_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_processed ON updates(is_processed)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON updates(source)")

    conn.commit()
    logger.success(f"Database initialized at {Config.DB_PATH}")
    return conn


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        from PyPDF2 import PdfReader
        logger.debug(f"Extracting text from PDF: {file_path}")
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() for page in reader.pages])
        return text
    except ImportError:
        logger.warning("PyPDF2 not installed. Install with: pip install PyPDF2")
        return ""
    except Exception as e:
        logger.error(f"Error reading PDF {file_path}: {e}")
        return ""


def extract_text_from_html(file_path: str) -> str:
    """Extract text from an HTML file."""
    try:
        logger.debug(f"Extracting text from HTML: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(f.read(), "html.parser")
            return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.error(f"Error reading HTML {file_path}: {e}")
        return ""


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a Word DOCX file."""
    try:
        from docx import Document
        logger.debug(f"Extracting text from DOCX: {file_path}")
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except ImportError:
        logger.warning("python-docx not installed. Install with: pip install python-docx")
        return ""
    except Exception as e:
        logger.error(f"Error reading DOCX {file_path}: {e}")
        return ""


def categorize_risk_area(text: str) -> str:
    """Categorize the update based on keywords or LLM."""
    # Try LLM first if available
    use_llm = True
    if use_llm and text:
        risk_areas_str = ", ".join(Config.RISK_AREAS)
        prompt = LLM_PROMPTS["categorize"].format(
            risk_areas=risk_areas_str,
            text=text[:4000]  # Limit input length
        )
        llm_response = get_ollama_response(prompt)
        if llm_response and llm_response in Config.RISK_AREAS + ["Other"]:
            logger.debug(f"LLM categorized as: {llm_response}")
            return llm_response

    # Fallback to keyword matching
    logger.debug("Using keyword matching for risk area categorization")
    text_lower = text.lower()
    for area in Config.RISK_AREAS:
        keywords = [
            area.lower().replace(" ", "_"),
            area.lower().replace(" ", ""),
            area.lower().split()[0],  # First word
        ]
        for keyword in keywords:
            if keyword in text_lower:
                logger.debug(f"Keyword match: {keyword} -> {area}")
                return area

    logger.warning("No risk area matched, defaulting to 'Other'")
    return "Other"


def assess_urgency(text: str) -> str:
    """Assess urgency level based on keywords or LLM."""
    # Try LLM first if available
    use_llm = True
    if use_llm and text:
        prompt = LLM_PROMPTS["assess_urgency"].format(text=text[:4000])
        llm_response = get_ollama_response(prompt)
        if llm_response and llm_response in ["Urgent", "High", "Medium", "Low"]:
            logger.debug(f"LLM assessed urgency as: {llm_response}")
            return llm_response

    # Fallback to keyword matching
    logger.debug("Using keyword matching for urgency assessment")
    urgent_keywords = [
        "urgent", "immediate", "critical", "deadline",
        "compliance failure", "enforcement", "breach", "without delay",
    ]
    high_keywords = [
        "high risk", "significant", "mandatory", "requirement",
        "obligation", "regulation", "directive", "must", "shall",
    ]

    text_lower = text.lower()

    for keyword in urgent_keywords:
        if keyword in text_lower:
            logger.debug(f"Urgent keyword match: {keyword}")
            return "Urgent"
    for keyword in high_keywords:
        if keyword in text_lower:
            logger.debug(f"High keyword match: {keyword}")
            return "High"

    logger.debug("Defaulting to Medium urgency")
    return "Medium"


def generate_summary(text: str) -> str:
    """Generate a summary using LLM or fallback to first paragraph."""
    # Try LLM first if available
    use_llm = True
    if use_llm and text and len(text) > 50:
        prompt = LLM_PROMPTS["summarize"].format(text=text[:4000])
        llm_response = get_ollama_response(prompt)
        if llm_response:
            logger.debug("Generated LLM summary")
            return llm_response

    # Fallback to first paragraph
    logger.debug("Using fallback summary (first paragraph)")
    if text:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if paragraphs:
            summary = paragraphs[0][:500] + "..." if len(paragraphs[0]) > 500 else paragraphs[0]
            return summary

    return "No summary available."


def determine_source(file_path: str) -> str:
    """Determine the source (EBA or MAS) based on the file path."""
    if "mas" in file_path.lower():
        return "MAS"
    elif "eba" in file_path.lower():
        return "EBA"
    else:
        # Default to EBA for backward compatibility
        return "EBA"


def process_file(file_path: str, conn: sqlite3.Connection) -> bool:
    """Process a single raw file and store it in the database."""
    try:
        cursor = conn.cursor()
        logger.info(f"Processing file: {file_path}")

        # Extract metadata from filename (e.g., 20240101_120000_title.pdf)
        filename = os.path.basename(file_path)
        match = re.match(r"(\d{8}_\d{6})_(.+?)(?:\.pdf|\.html|\.xlsx|\.docx|\.doc)", filename)
        timestamp_str = match.group(1) if match else ""
        title = match.group(2).replace("_", " ") if match else filename

        # Determine source from file path
        source = determine_source(file_path)

        # Extract text based on file type
        if file_path.endswith(".pdf"):
            raw_text = extract_text_from_pdf(file_path)
        elif file_path.endswith(".html") or file_path.endswith(".htm"):
            raw_text = extract_text_from_html(file_path)
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            # For Excel files, we'd need openpyxl or pandas
            raw_text = "[Excel file - text extraction not implemented]"
            logger.warning(f"Excel file detected, text extraction not implemented: {file_path}")
        elif file_path.endswith(".docx") or file_path.endswith(".doc"):
            raw_text = extract_text_from_docx(file_path)
        else:
            logger.error(f"Unsupported file type: {file_path}")
            return False

        if not raw_text:
            logger.warning(f"No text extracted from {file_path}")
            return False

        # Categorize and assess using LLM or keywords
        risk_area = categorize_risk_area(raw_text)
        urgency = assess_urgency(raw_text)
        summary = generate_summary(raw_text)

        # Parse publication date from filename or text
        publication_date = timestamp_str[:8] if timestamp_str else "Unknown"
        try:
            publication_date = datetime.strptime(publication_date, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(f"Could not parse publication date: {timestamp_str}")

        # Insert into database
        cursor.execute("""
            INSERT INTO updates (
                title, source_url, file_path, publication_date, 
                raw_text, summary, risk_area, urgency_level, source, is_processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            "",  # source_url (can be updated later)
            file_path,
            publication_date,
            raw_text,
            summary,
            risk_area,
            urgency,
            source,
            True,
        ))

        conn.commit()
        logger.success(f"Processed: {filename} (Source: {source}, Risk: {risk_area}, Urgency: {urgency})")
        return True

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        conn.rollback()
        return False


def process_all_files(conn: sqlite3.Connection) -> None:
    """Process all files in the raw data directories (EBA and MAS)."""
    raw_files = []

    # Find all supported files in EBA raw data directory
    eba_raw_dir = Config.EBA_RAW_DATA_DIR
    if os.path.exists(eba_raw_dir):
        for root, _, files in os.walk(eba_raw_dir):
            for file in files:
                if file.lower().endswith((".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc")):
                    raw_files.append(os.path.join(root, file))

    # Find all supported files in MAS raw data directory
    mas_raw_dir = Config.MAS_RAW_DATA_DIR
    if os.path.exists(mas_raw_dir):
        for root, _, files in os.walk(mas_raw_dir):
            for file in files:
                if file.lower().endswith((".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc")):
                    raw_files.append(os.path.join(root, file))

    if not raw_files:
        logger.warning(f"No raw files found in {eba_raw_dir} or {mas_raw_dir}")
        return

    logger.info(f"Found {len(raw_files)} raw files to process.")

    for file_path in raw_files:
        process_file(file_path, conn)


def process_source_files(conn: sqlite3.Connection, source: str = "all") -> None:
    """Process files from a specific source (EBA or MAS)."""
    raw_files = []
    source_dir = None

    if source == "EBA" or source == "all":
        source_dir = Config.EBA_RAW_DATA_DIR
        if os.path.exists(source_dir):
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.lower().endswith((".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc")):
                        raw_files.append(os.path.join(root, file))

    if source == "MAS" or source == "all":
        source_dir = Config.MAS_RAW_DATA_DIR
        if os.path.exists(source_dir):
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.lower().endswith((".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc")):
                        raw_files.append(os.path.join(root, file))

    if not raw_files:
        logger.warning(f"No raw files found for source: {source}")
        return

    logger.info(f"Found {len(raw_files)} raw files for source '{source}' to process.")

    for file_path in raw_files:
        process_file(file_path, conn)


def main():
    parser = argparse.ArgumentParser(description="Process raw regulatory updates (EBA and MAS) and store in SQLite.")
    parser.add_argument("--file", type=str, help="Process a specific file.")
    parser.add_argument("--all", action="store_true", help="Process all files in data/raw/eba/ and data/raw/mas/.")
    parser.add_argument("--source", type=str, default="all", choices=["all", "EBA", "MAS"],
                        help="Process files from a specific source (default: all).")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM (Ollama) for categorization.")
    args = parser.parse_args()

    # Disable LLM if requested
    if args.no_llm:
        logger.warning("LLM (Ollama) disabled by user request")
        global get_ollama_response
        def get_ollama_response(*args, **kwargs):
            return None

    conn = init_db()

    if args.file:
        if not os.path.exists(args.file):
            logger.error(f"File not found: {args.file}")
            return
        process_file(args.file, conn)
    elif args.all:
        process_all_files(conn)
    elif args.source != "all":
        process_source_files(conn, args.source)
    else:
        logger.error("No action specified. Use --file, --all, or --source.")

    conn.close()
    logger.info("Processing completed.")


if __name__ == "__main__":
    main()
