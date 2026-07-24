#!/usr/bin/env python3
"""
Process raw EBA regulatory updates and store them in a SQLite database.
Extracts metadata, text, and categorizes updates by risk area using Ollama (Mistral-7B).
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
    "Financial Stability",
    "Resolution Planning",
    "Capital Requirements",
    "Liquidity Risk",
    "Market Risk",
    "Credit Risk",
]

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


def get_ollama_response(prompt: str, model: str = "mistral") -> str:
    """
    Get a response from Ollama's LLM (Mistral-7B by default).
    Returns the generated text or a fallback value if Ollama is not available.
    """
    try:
        import ollama
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={"temperature": 0.1, "max_tokens": 200},
        )
        return response["response"].strip()
    except ImportError:
        print("⚠️ Ollama is not installed. Install with: pip install ollama")
        return None
    except Exception as e:
        print(f"⚠️ Error generating LLM response: {e}")
        return None


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
    """Categorize the update based on keywords or LLM."""
    # Try LLM first if available
    use_llm = True
    if use_llm:
        risk_areas_str = ", ".join(RISK_AREAS)
        prompt = LLM_PROMPTS["categorize"].format(
            risk_areas=risk_areas_str,
            text=text[:4000]  # Limit input length
        )
        llm_response = get_ollama_response(prompt)
        if llm_response and llm_response in RISK_AREAS + ["Other"]:
            return llm_response
    
    # Fallback to keyword matching
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
    """Assess urgency level based on keywords or LLM."""
    # Try LLM first if available
    use_llm = True
    if use_llm:
        prompt = LLM_PROMPTS["assess_urgency"].format(text=text[:4000])
        llm_response = get_ollama_response(prompt)
        if llm_response and llm_response in ["Urgent", "High", "Medium", "Low"]:
            return llm_response
    
    # Fallback to keyword matching
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
            return "Urgent"
    for keyword in high_keywords:
        if keyword in text_lower:
            return "High"
    
    return "Medium"


def generate_summary(text: str) -> str:
    """Generate a summary using LLM or fallback to first paragraph."""
    # Try LLM first if available
    use_llm = True
    if use_llm and text and len(text) > 50:
        prompt = LLM_PROMPTS["summarize"].format(text=text[:4000])
        llm_response = get_ollama_response(prompt)
        if llm_response:
            return llm_response
    
    # Fallback to first paragraph
    if text:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if paragraphs:
            summary = paragraphs[0][:500] + "..." if len(paragraphs[0]) > 500 else paragraphs[0]
            return summary
    
    return "No summary available."


def process_file(file_path: str, conn: sqlite3.Connection) -> bool:
    """Process a single raw file and store it in the database."""
    try:
        cursor = conn.cursor()
        
        # Extract metadata from filename (e.g., 20240101_120000_title.pdf)
        filename = os.path.basename(file_path)
        match = re.match(r"(\d{8}_\d{6})_(.+?)(?:\.pdf|\.html|\.xlsx|\.docx)", filename)
        timestamp_str = match.group(1) if match else ""
        title = match.group(2).replace("_", " ") if match else filename
        
        # Extract text based on file type
        if file_path.endswith(".pdf"):
            raw_text = extract_text_from_pdf(file_path)
        elif file_path.endswith(".html") or file_path.endswith(".htm"):
            raw_text = extract_text_from_html(file_path)
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            # For Excel files, we'd need openpyxl or pandas
            raw_text = "[Excel file - text extraction not implemented]"
        elif file_path.endswith(".docx") or file_path.endswith(".doc"):
            raw_text = "[Word file - text extraction not implemented]"
        else:
            print(f"⚠️ Unsupported file type: {file_path}")
            return False
        
        if not raw_text:
            print(f"⚠️ No text extracted from {file_path}")
            return False
        
        # Categorize and assess using LLM or keywords
        risk_area = categorize_risk_area(raw_text)
        urgency = assess_urgency(raw_text)
        summary = generate_summary(raw_text)
        
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
                raw_text, summary, risk_area, urgency_level, is_processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            "",  # source_url (can be updated later)
            file_path,
            publication_date,
            raw_text,
            summary,
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
    
    # Find all supported files in raw data directory
    for root, _, files in os.walk(RAW_DATA_DIR):
        for file in files:
            if file.lower().endswith((".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc")):
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
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM (Ollama) for categorization.")
    args = parser.parse_args()
    
    # Disable LLM if requested
    if args.no_llm:
        global get_ollama_response
        def get_ollama_response(*args, **kwargs):
            return None
    
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
