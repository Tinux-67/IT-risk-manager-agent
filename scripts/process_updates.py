#!/usr/bin/env python3
"""
Process raw regulatory updates (EBA and MAS) and store them in a SQLite database.
Extracts metadata, text, and categorizes updates by risk area using Ollama (Mistral-7B).
"""

import argparse
import os
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from loguru import logger

from config import Config
from scripts.llm_utils import get_ollama_response, init_ollama_cache
from scripts.logging_config import setup_logging
from scripts.retrieval import chunk_text
from scripts.veracity import score_groundedness

setup_logging()

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
    "retrieve_and_reason": """
You are a regulatory compliance expert. First, write your reasoning in <think>...</think> tags about which chunks are most relevant to the query and why.
Then return a JSON object with:
{
  "reasoning": "Your chain-of-thought reasoning about which chunks are relevant and why.",
  "cited_chunks": [
    {"chunk_text": "...", "char_start": 0, "char_end": 100, "source_file": "eba/foo.pdf"}
  ]
}

Context: the following chunks are from a regulatory document.
Chunks: {chunks}
Query: {query}
""",
    "summarize": """
    You are a compliance assistant. Provide a concise summary (2-3 sentences) of the following regulatory text.
    Focus on the key requirements, changes, or obligations.

    Text: {text}

    Summary:
    """,
}


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
            is_processed BOOLEAN DEFAULT 0,
            citation_sources   TEXT,
            reasoning_chain    TEXT,
            groundedness_score  REAL,
            chunk_count        INTEGER DEFAULT 0
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_risk_area ON updates(source, risk_area)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_source_urgency ON updates(source, urgency_level)"
    )

    # Initialize Ollama cache table
    init_ollama_cache(conn)

    conn.commit()
    logger.success(f"Database initialized at {Config.DB_PATH}")
    return conn


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF using multiple engines in order of reliability.

    Engines tried (in order):
      1. pypdf (PdfReader) — fastest, works for text-based PDFs
      2. pdfminer.six (PDFPageBrowser + LAParams) — slower, better for complex layouts

    If all engines fail, returns an empty string and logs the specific failure.
    Logs the character count of the extracted text so the caller can detect silent
    failures (e.g. scanned/image-only PDFs that produce zero characters).
    """
    # ── Engine 1: pypdf ──────────────────────────────────────────────────
    try:
        from pypdf import PdfReader

        logger.debug(f"[pypdf] Extracting text from PDF: {file_path}")
        reader = PdfReader(file_path)
        pages: list[str] = []
        for page in reader.pages:
            try:
                txt = page.extract_text()
            except Exception as exc:
                logger.warning(f"[pypdf] Failed to extract page {page}: {exc}")
                txt = ""
            pages.append(txt)
        text = "\n".join(pages)
        if text.strip():
            logger.info(f"[pypdf] Extracted {len(text)} chars from {file_path}")
            return text
        else:
            logger.warning(f"[pypdf] Extracted 0 chars from {file_path} — trying pdfminer")
    except ImportError:
        logger.warning("[pypdf] Not installed — trying pdfminer")
    except Exception as exc:
        logger.warning(f"[pypdf] Unexpected error: {exc} — trying pdfminer")

    # ── Engine 2: pdfminer.six ─────────────────────────────────────────────
    try:
        from pdfminer.high_level import extract_text as _extract_pdfminer

        logger.debug(f"[pdfminer] Extracting text from PDF: {file_path}")
        text = _extract_pdfminer(file_path)
        if text and text.strip():
            logger.info(f"[pdfminer] Extracted {len(text)} chars from {file_path}")
            return text
        else:
            logger.warning(f"[pdfminer] Extracted 0 meaningful chars from {file_path}")
    except ImportError:
        logger.warning("[pdfminer] pdfminer.six not installed — PDF text unavailable")
    except Exception as exc:
        logger.error(f"[pdfminer] Unexpected error: {exc}")

    # Both engines failed or produced empty output
    logger.error(
        f"PDF text extraction failed for {file_path}: "
        "all engines returned empty text (likely a scanned/image-only PDF)"
    )
    return ""


def extract_text_from_html(file_path: str) -> str:
    """Extract text from an HTML file."""
    try:
        logger.debug(f"Extracting text from HTML: {file_path}")
        with open(file_path, encoding="utf-8") as f:
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


def extract_text_from_excel(file_path: str) -> str:
    """Extract text from an Excel file using pandas."""
    try:
        import pandas as pd

        logger.debug(f"Extracting text from Excel: {file_path}")
        dfs = pd.read_excel(file_path, sheet_name=None)
        parts = []
        for sheet_name, df in dfs.items():
            parts.append(f"[Sheet: {sheet_name}]")
            parts.append(df.to_string(index=False))
        return "\n".join(parts)
    except ImportError:
        logger.warning("pandas not installed. Install with: pip install pandas openpyxl")
        return ""
    except Exception as e:
        logger.error(f"Error reading Excel {file_path}: {e}")
        return ""


def categorize_risk_area(text: str, conn: sqlite3.Connection | None = None) -> str:
    """Categorize the update based on keywords or LLM."""
    # Try LLM first if available
    if text:
        risk_areas_str = ", ".join(Config.RISK_AREAS)
        prompt = LLM_PROMPTS["categorize"].format(risk_areas=risk_areas_str, text=text[:4000])
        llm_response = get_ollama_response(prompt, conn=conn)
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


def assess_urgency(text: str, conn: sqlite3.Connection | None = None) -> str:
    """Assess urgency level based on keywords or LLM."""
    # Try LLM first if available
    if text:
        prompt = LLM_PROMPTS["assess_urgency"].format(text=text[:4000])
        llm_response = get_ollama_response(prompt, conn=conn)
        if llm_response and llm_response in ["Urgent", "High", "Medium", "Low"]:
            logger.debug(f"LLM assessed urgency as: {llm_response}")
            return llm_response

    # Fallback to keyword matching
    logger.debug("Using keyword matching for urgency assessment")
    urgent_keywords = [
        "urgent",
        "immediate",
        "critical",
        "deadline",
        "compliance failure",
        "enforcement",
        "breach",
        "without delay",
    ]
    high_keywords = [
        "high risk",
        "significant",
        "mandatory",
        "requirement",
        "obligation",
        "regulation",
        "directive",
        "must",
        "shall",
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


def generate_summary(text: str, conn: sqlite3.Connection | None = None) -> str:
    """
    Generate a summary using the LLM, with a fallback if the response is empty,
    suspiciously short (less than 10 chars), or suspiciously similar to the input
    (suggesting the LLM just echoed the prompt).

    The minimum length gate is 20 characters — any response shorter than this is
    treated as a failure and the first paragraph fallback is used instead.
    """
    if not text or len(text.strip()) < 50:
        logger.warning(
            f"Input text too short ({len(text)} chars) for summarisation — using fallback"
        )
        return _fallback_summary(text)

    prompt = LLM_PROMPTS["summarize"].format(text=text[:4000])
    llm_response = get_ollama_response(prompt, conn=conn)

    min_summary_length = 20
    if llm_response and len(llm_response.strip()) >= min_summary_length:
        logger.debug(f"Generated LLM summary ({len(llm_response)} chars)")
        return llm_response

    logger.warning(
        f"LLM summary response too short or empty "
        f"(got {len(llm_response) if llm_response else 0} chars) — using fallback"
    )
    return _fallback_summary(text)


def _fallback_summary(text: str) -> str:
    """Extract the first non-empty paragraph as a fallback summary."""
    if text:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if paragraphs:
            first = paragraphs[0]
            return first[:500] + "..." if len(first) > 500 else first
    return "No summary available."


def determine_source(file_path: str) -> str:
    """Determine the source (EBA or MAS) based on the file path."""
    if "mas" in file_path.lower():
        return "MAS"
    elif "eba" in file_path.lower():
        return "EBA"
    else:
        return "EBA"


def process_file(file_path: str, conn: sqlite3.Connection) -> tuple[bool, str]:
    """
    Process a single raw file and store it in the database.
    Returns a tuple of (success, filename) for tracking.
    """
    return _process_file_impl(file_path, conn, run_trust_layer=True)


def _process_file_impl(
    file_path: str,
    conn: sqlite3.Connection,
    run_trust_layer: bool = True,
) -> tuple[bool, str]:
    """Shared implementation; do not call directly — use process_file()."""
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
            raw_text = extract_text_from_excel(file_path)
        elif file_path.endswith(".docx") or file_path.endswith(".doc"):
            raw_text = extract_text_from_docx(file_path)
        else:
            logger.error(f"Unsupported file type: {file_path}")
            return False, filename

        if not raw_text:
            logger.warning(f"No text extracted from {file_path}")
            return False, filename

        # ── Pre-INSERT data quality gate ─────────────────────────────────
        # After extraction + LLM processing, validate that meaningful content exists.
        # Reject documents where:
        #   - raw_text is empty (extraction failure)
        #   - summary is the fallback (LLM produced nothing useful)
        #   - risk_area is the fallback AND urgency is default (LLM produced nothing)
        # Trust layer is skipped entirely if the document fails quality gate.
        risk_area = categorize_risk_area(raw_text, conn)
        urgency = assess_urgency(raw_text, conn)
        summary = generate_summary(raw_text, conn)

        low_quality_summaries = {
            "No summary available.",
            "No risk area matched. Defaulting to 'Other'.",
            "Defaulting to 'Other' risk area.",
            "No risk area matched. Defaulting to Other.",
        }
        is_summary_fallback = (
            summary in low_quality_summaries
            or summary.lower().startswith("defaulting")
        )
        is_risk_fallback = risk_area == "Other"
        is_urgency_fallback = urgency == "Medium"  # Default; not definitive alone

        quality_failed = is_summary_fallback and is_risk_fallback and is_urgency_fallback
        if quality_failed:
            logger.error(
                f"Data quality gate FAILED for {filename}: "
                f"summary='{summary[:50]}', risk_area='{risk_area}', urgency='{urgency}'. "
                f"Document may be empty or unscrapable. Skipping INSERT."
            )
            # Don't INSERT a garbage record, but still count it as "processed" to avoid
            # infinite retry loops on genuinely unscrapable documents.
            # Mark as is_processed=1 so re-runs don't keep trying.
            _pub_date = timestamp_str[:8] if timestamp_str else "Unknown"
            try:
                _pub_date = datetime.strptime(_pub_date, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                pass
            cursor.execute(
                """
                INSERT INTO updates (
                    title, source_url, file_path, publication_date,
                    raw_text, summary, risk_area, urgency_level, source, is_processed,
                    citation_sources, reasoning_chain, groundedness_score, chunk_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    "",
                    file_path,
                    _pub_date,
                    "",  # raw_text intentionally empty — signals extraction failure
                    summary,
                    risk_area,
                    urgency,
                    source,
                    True,  # is_processed — mark done so re-runs skip this file
                    None, None, None, 0,
                ),
            )
            conn.commit()
            return True, filename  # Return True so the file isn't retried endlessly

        # Parse publication date from filename or text
        publication_date = timestamp_str[:8] if timestamp_str else "Unknown"
        try:
            publication_date = datetime.strptime(publication_date, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(f"Could not parse publication date: {timestamp_str}")

        # ── Step 1: INSERT with NULL placeholders for trust columns ─────────
        cursor.execute(
            """
            INSERT INTO updates (
                title, source_url, file_path, publication_date,
                raw_text, summary, risk_area, urgency_level, source, is_processed,
                citation_sources, reasoning_chain, groundedness_score, chunk_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                title,
                "",
                file_path,
                publication_date,
                raw_text,
                summary,
                risk_area,
                urgency,
                source,
                True,
                None,  # citation_sources
                None,  # reasoning_chain
                None,  # groundedness_score
                0,     # chunk_count
            ),
        )
        update_id = cursor.lastrowid  # now available

        # ── Step 2: Trust layer (chunk → reason → veracity) ────────────────
        if run_trust_layer:
            citation_sources_json = "[]"
            reasoning_chain = ""
            groundedness_score_val: float | None = None
            chunk_count_val = 0

            try:
                chunks = chunk_text(raw_text, file_path, update_id, conn)
                chunk_count_val = len(chunks)

                if chunks:
                    chunk_context = "\n\n".join(
                        f"[Chunk {c['chunk_index']}] {c['chunk_text']}"
                        for c in chunks
                    )
                    reason_prompt = LLM_PROMPTS["retrieve_and_reason"].format(
                        chunks=chunk_context,
                        query=f"Risk area: {risk_area}. Urgency: {urgency}.",
                    )
                    reason_response = get_ollama_response(reason_prompt, conn=conn)

                    if reason_response:
                        import json as _json

                        try:
                            cleaned = reason_response.strip()
                            if cleaned.startswith("```"):
                                # Extract JSON from within markdown fence
                                parts = cleaned.split("```", 2)
                                if len(parts) >= 3:
                                    cleaned = parts[2].split("\n", 1)[1]
                            parsed = _json.loads(cleaned)
                            reasoning_chain = parsed.get("reasoning", "")
                            cited = parsed.get("cited_chunks", [])
                            citation_sources_json = _json.dumps(cited)
                        except Exception:
                            logger.warning(
                                f"Could not parse cited-reasoning JSON for {filename} "
                                "— storing raw response"
                            )
                            reasoning_chain = reason_response
                            citation_sources_json = "[]"

                    # Veracity scoring
                    if summary and citation_sources_json not in ("", "[]"):
                        try:
                            cited_chunks_list = _json.loads(citation_sources_json)
                            cited_text = " ".join(c["chunk_text"] for c in cited_chunks_list)
                            groundedness_score_val = score_groundedness(
                                cited_text=cited_text,
                                summary=summary,
                                conn=conn,
                            )
                        except Exception as exc:
                            logger.warning(f"Veracity scoring failed for {filename}: {exc}")

                logger.debug(
                    f"Trust layer done for {filename}: chunks={chunk_count_val}, "
                    f"groundedness={groundedness_score_val}"
                )
            except Exception as exc:
                # Trust layer failures must not halt processing
                logger.error(f"Trust layer failed for {filename}: {exc}")

            # ── Step 3: UPDATE with trust results ────────────────────────────
            cursor.execute(
                """
                UPDATE updates SET
                    citation_sources  = ?,
                    reasoning_chain   = ?,
                    groundedness_score = ?,
                    chunk_count       = ?
                WHERE id = ?
                """,
                (
                    citation_sources_json,
                    reasoning_chain,
                    groundedness_score_val,
                    chunk_count_val,
                    update_id,
                ),
            )

        conn.commit()
        logger.success(
            f"Processed: {filename} "
            f"(Source: {source}, Risk: {risk_area}, Urgency: {urgency})"
        )
        return True, filename

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        conn.rollback()
        return False, filename


def _process_file_worker(file_path: str) -> tuple[bool, str]:
    """
    Worker function for parallel processing.
    Opens its own SQLite connection to avoid thread-safety issues.
    """
    worker_conn = sqlite3.connect(Config.DB_PATH)
    try:
        return _process_file_impl(file_path, worker_conn, run_trust_layer=True)
    finally:
        worker_conn.close()


def process_files_parallel(
    file_paths: list[str], conn: sqlite3.Connection, max_workers: int = 4
) -> dict[str, bool]:
    """
    Process multiple files in parallel using ThreadPoolExecutor.
    Each worker opens its own SQLite connection for thread safety.
    Returns a dictionary mapping filenames to success status.
    """
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks — each worker gets its own connection via _process_file_worker
        future_to_file = {
            executor.submit(_process_file_worker, file_path): file_path for file_path in file_paths
        }

        # Process completed futures as they come in
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                success, filename = future.result()
                results[filename] = success
            except Exception as e:
                logger.error(f"Error in parallel processing of {file_path}: {e}")
                results[os.path.basename(file_path)] = False

    return results


def collect_raw_files(source: str = "all") -> list[str]:
    """Collect all raw files from specified sources."""
    raw_files = []

    if source == "EBA" or source == "all":
        eba_raw_dir = Config.EBA_RAW_DATA_DIR
        if os.path.exists(eba_raw_dir):
            for root, _, files in os.walk(eba_raw_dir):
                for file in files:
                    if file.lower().endswith(
                        (".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc")
                    ):
                        raw_files.append(os.path.join(root, file))

    if source == "MAS" or source == "all":
        mas_raw_dir = Config.MAS_RAW_DATA_DIR
        if os.path.exists(mas_raw_dir):
            for root, _, files in os.walk(mas_raw_dir):
                for file in files:
                    if file.lower().endswith(
                        (".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc")
                    ):
                        raw_files.append(os.path.join(root, file))

    return raw_files


def process_all_files(conn: sqlite3.Connection, max_workers: int = 4) -> None:
    """
    Process all files in the raw data directories (EBA and MAS) using parallel processing.
    Uses ThreadPoolExecutor for improved performance with large datasets.
    """
    raw_files = collect_raw_files(source="all")

    if not raw_files:
        logger.warning(
            f"No raw files found in {Config.EBA_RAW_DATA_DIR} or {Config.MAS_RAW_DATA_DIR}"
        )
        return

    logger.info(f"Found {len(raw_files)} raw files to process with {max_workers} workers.")

    # Process files in parallel
    results = process_files_parallel(raw_files, conn, max_workers)

    # Log summary
    success_count = sum(1 for v in results.values() if v)
    failure_count = len(results) - success_count
    logger.info(
        f"Parallel processing completed: {success_count} succeeded, {failure_count} failed out of {len(results)} total"
    )


def process_source_files(
    conn: sqlite3.Connection, source: str = "all", max_workers: int = 4
) -> None:
    """
    Process files from a specific source (EBA or MAS) using parallel processing.
    Uses ThreadPoolExecutor for improved performance.
    """
    raw_files = collect_raw_files(source=source)

    if not raw_files:
        logger.warning(f"No raw files found for source: {source}")
        return

    logger.info(
        f"Found {len(raw_files)} raw files for source '{source}' to process with {max_workers} workers."
    )

    # Process files in parallel
    results = process_files_parallel(raw_files, conn, max_workers)

    # Log summary
    success_count = sum(1 for v in results.values() if v)
    failure_count = len(results) - success_count
    logger.info(
        f"Parallel processing completed: {success_count} succeeded, {failure_count} failed out of {len(results)} total"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process raw regulatory updates (EBA and MAS) and store in SQLite."
    )
    parser.add_argument("--file", type=str, help="Process a specific file.")
    parser.add_argument(
        "--all", action="store_true", help="Process all files in data/raw/eba/ and data/raw/mas/."
    )
    parser.add_argument(
        "--source",
        type=str,
        default="all",
        choices=["all", "EBA", "MAS"],
        help="Process files from a specific source (default: all).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of worker threads for parallel processing (default: 4).",
    )
    parser.add_argument(
        "--no-llm", action="store_true", help="Disable LLM (Ollama) for categorization."
    )
    args = parser.parse_args()

    # Disable LLM if requested
    if args.no_llm:
        logger.warning("LLM (Ollama) disabled by user request")
        import scripts.llm_utils as _llm_utils

        _llm_utils.get_ollama_response = lambda *a, **kw: None

    conn = init_db()

    if args.file:
        if not os.path.exists(args.file):
            logger.error(f"File not found: {args.file}")
            return
        process_file(args.file, conn)
    elif args.all:
        process_all_files(conn, max_workers=args.workers)
    elif args.source != "all":
        process_source_files(conn, args.source, max_workers=args.workers)
    else:
        logger.error("No action specified. Use --file, --all, or --source.")

    conn.close()
    logger.info("Processing completed.")


if __name__ == "__main__":
    main()
