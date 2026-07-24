#!/usr/bin/env python3
"""
Process raw EBA regulatory updates and store them in a SQLite database.
Extracts metadata, text, and categorizes updates by risk area.
"""

import os
import sqlite3
import re
from datetime import datetime
import argparse
from pathlib import Path

# Constants
DB_PATH = "data/processed/regulatory_updates.db"
RAW_DATA_DIR = "data/raw/eba"

# Risk areas for categorization
RISK_AREAS = [
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
]


def init_db() -> sqlite3.Connection:
    """Initialize the SQLite database and create tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
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
            is_processed BOOLEAN DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    conn.commit()
    return conn


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() for page in reader.pages])
        return text
    except ImportError:
        print("⚠️ PyPDF2 not installed. Install with: pip install PyPDF2")
        return ""
    except Exception as e:
        print(f"⚠️ Error reading PDF {file_path}: {e}")
        return ""


def extract_text_from_html(file_path: str) -> str:
    """Extract text from an HTML file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(f.read(), "html.parser")
            return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"⚠️ Error reading HTML {file_path}: {e}")
        return ""


def categorize_risk_area(text: str) -> str:
    """Categorize the update based on keywords in the text."""
    text_lower = text.lower()
    
    for area in RISK_AREAS:
        keywords = [
            area.lower().replace(" ", "_"),
            area.lower().replace(" ", ""),
            area.lower().split()[0],  # First word
        ]
        for keyword in keywords:
            if keyword in text_lower:
                return area
    
    return "Other"


def assess_urgency(text: str) -> str:
    """Assess urgency level based on keywords."""
    urgent_keywords = [
        "urgent", "immediate", "critical", "deadline",
        "compliance failure", "enforcement", "breach",
    ]
    high_keywords = [
        "high risk", "significant", "mandatory", "requirement",
        "obligation", "regulation", "directive",
    ]
    
    text_lower = text.lower()
    
    for keyword in urgent_keywords:
        if keyword in text_lower:
            return "Urgent"
    for keyword in high_keywords:
        if keyword in text_lower:
            return "High"
    
    return "Medium"


def process_file(file_path: str, conn: sqlite3.Connection) -> bool:
    """Process a single raw file and store it in the database."""
    try:
        cursor = conn.cursor()
        
        # Extract metadata from filename (e.g., 20240101_120000_title.pdf)
        filename = os.path.basename(file_path)
        match = re.match(r"(\d{8}_\d{6})_(.+?)(?:\.pdf|\.html)", filename)
        timestamp_str = match.group(1) if match else ""
        title = match.group(2).replace("_", " ") if match else filename
        
        # Extract text based on file type
        if file_path.endswith(".pdf"):
            raw_text = extract_text_from_pdf(file_path)
        elif file_path.endswith(".html"):
            raw_text = extract_text_from_html(file_path)
        else:
            print(f"⚠️ Unsupported file type: {file_path}")
            return False
        
        if not raw_text:
            print(f"⚠️ No text extracted from {file_path}")
            return False
        
        # Categorize and assess
        risk_area = categorize_risk_area(raw_text)
        urgency = assess_urgency(raw_text)
        
        # Parse publication date from filename or text
        publication_date = timestamp_str[:8] if timestamp_str else "Unknown"
        try:
            publication_date = datetime.strptime(publication_date, "%Y%m%d").strftime("%Y-%m-%d")
        except:
            pass
        
        # Insert into database
        cursor.execute("""
            INSERT INTO updates (
                title, source_url, file_path, publication_date, 
                raw_text, risk_area, urgency_level, is_processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            "",  # source_url (can be updated later)
            file_path,
            publication_date,
            raw_text,
            risk_area,
            urgency,
            True,
        ))
        
        conn.commit()
        print(f"✅ Processed: {filename} (Risk: {risk_area}, Urgency: {urgency})")
        return True
        
    except Exception as e:
        print(f"⚠️ Error processing {file_path}: {e}")
        return False


def process_all_files(conn: sqlite3.Connection) -> None:
    """Process all files in the raw data directory."""
    raw_files = []
    
    # Find all PDF and HTML files in raw data directory
    for root, _, files in os.walk(RAW_DATA_DIR):
        for file in files:
            if file.lower().endswith((".pdf", ".html")):
                raw_files.append(os.path.join(root, file))
    
    if not raw_files:
        print("❌ No raw files found in data/raw/eba/")
        return
    
    print(f"📁 Found {len(raw_files)} raw files to process.")
    
    for file_path in raw_files:
        process_file(file_path, conn)


def main():
    parser = argparse.ArgumentParser(description="Process raw EBA updates and store in SQLite.")
    parser.add_argument("--file", type=str, help="Process a specific file.")
    parser.add_argument("--all", action="store_true", help="Process all files in data/raw/eba/.")
    args = parser.parse_args()
    
    conn = init_db()
    
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            return
        process_file(args.file, conn)
    elif args.all:
        process_all_files(conn)
    else:
        print("❌ Please specify --file or --all.")
    
    conn.close()


if __name__ == "__main__":
    main()
