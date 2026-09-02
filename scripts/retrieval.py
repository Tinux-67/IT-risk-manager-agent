#!/usr/bin/env python3
"""
BM25 retrieval for cited evidence chunks.

chunk_text()      — split raw text into overlapping windows, store in raw_chunks
retrieve_chunks() — BM25 index over a document's chunks, return top-k matches
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from loguru import logger

# Lazy import — rank_bm25 is a runtime dependency, not a hard install requirement
# for the PoC.  If it is absent we fall back to naive keyword matching.
_bm25_available = False
try:
    from rank_bm25 import BM25Okapi

    _bm25_available = True
except ImportError:
    logger.warning(
        "rank-bm25 not installed — retrieval will use naive TF/IDF fallback. "
        "Install with: pip install rank-bm25"
    )

# ── Constants ────────────────────────────────────────────────────────────────

CHUNK_WORD_SIZE = 500      # words per chunk
CHUNK_WORD_OVERLAP = 50    # overlapping words between consecutive chunks
TOP_K_DEFAULT = 5          # default number of chunks to retrieve

# ── Chunking ────────────────────────────────────────────────────────────────


def chunk_text(
    raw_text: str,
    source_file: str,
    update_id: int,
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """
    Split *raw_text* into overlapping word windows and store in raw_chunks.

    Args:
        raw_text:    Full raw text of the regulatory document.
        source_file: Resolved path to the source file (e.g. "data/raw/eba/foo.pdf").
        update_id:   Foreign key into the updates table.
        conn:        Open sqlite3 connection (committed here).

    Returns:
        List of chunk dicts, each with keys:
        {id, update_id, chunk_text, char_start, char_end, source_file, chunk_index}
    """
    if not raw_text or not raw_text.strip():
        logger.warning(f"Empty raw_text for update_id={update_id} — skipping chunking")
        return []

    # Tokenise on whitespace (simple but deterministic)
    words = raw_text.split()
    chunk_size = CHUNK_WORD_SIZE
    overlap = CHUNK_WORD_OVERLAP

    chunks: list[str] = []
    start_word = 0

    while start_word < len(words):
        end_word = min(start_word + chunk_size, len(words))
        chunk = " ".join(words[start_word:end_word])

        # Character offsets relative to the original raw_text string
        # We recompute char boundaries from word positions by finding them in the
        # original text, which is slow but exact.  For large texts, cache the
        # word->char mapping on first call.
        char_start = raw_text.find(chunk)
        if char_start == -1:
            # Fallback: approximate from word count × avg_word_length
            avg_wl = len(raw_text) / max(len(words), 1)
            char_start = int(start_word * avg_wl)

        char_end = char_start + len(chunk)

        chunks.append(chunk)

        if end_word >= len(words):
            break
        start_word = end_word - overlap

    # Delete existing chunks for this update (allows re-chunking on re-process)
    conn.execute("DELETE FROM raw_chunks WHERE update_id = ?", (update_id,))

    rows: list[dict[str, Any]] = []
    for idx, chunk_str in enumerate(chunks):
        cursor = conn.execute(
            """
            INSERT INTO raw_chunks
                (update_id, chunk_text, char_start, char_end, source_file, chunk_index)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (update_id, chunk_str, char_start, char_end, source_file, idx),
        )
        rows.append(
            {
                "id": cursor.lastrowid,
                "update_id": update_id,
                "chunk_text": chunk_str,
                "char_start": char_start,
                "char_end": char_end,
                "source_file": source_file,
                "chunk_index": idx,
            }
        )

    conn.commit()
    logger.debug(f"Chunked update_id={update_id} into {len(chunks)} chunks")
    return rows


# ── Retrieval ────────────────────────────────────────────────────────────────


def _tokenise(text: str) -> list[str]:
    """Downcase and split on non-alphanumeric characters."""
    return re.findall(r"\b\w+\b", text.lower())


def _build_bm25(chunks: list[dict[str, Any]]) -> "BM25Okapi | None":
    """Build a BM25 index from a list of chunk dicts. Returns None if BM25 unavailable."""
    if not _bm25_available:
        return None
    tokenised = [_tokenise(c["chunk_text"]) for c in chunks]
    return BM25Okapi(tokenised)


def _naive_retrieve(
    chunks: list[dict[str, Any]],
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    """
    Naive fallback when rank-bm25 is not installed.

    Scores each chunk by counting query word occurrences (case-insensitive).
    Returns top-k chunks sorted by score descending.
    """
    query_words = set(_tokenise(query))
    scored: list[tuple[int, int]] = []  # (score, index)

    for idx, chunk in enumerate(chunks):
        chunk_words = set(_tokenise(chunk["chunk_text"]))
        score = len(query_words & chunk_words)
        scored.append((score, idx))

    scored.sort(reverse=True)
    return [chunks[idx] for _, idx in scored[:top_k]]


def retrieve_chunks(
    query: str,
    update_id: int,
    conn: sqlite3.Connection,
    top_k: int = TOP_K_DEFAULT,
) -> list[dict[str, Any]]:
    """
    Retrieve the *top_k* most relevant chunks for *query* from a document.

    Uses BM25 (rank-bm25) when available; falls back to naive word-overlap scoring.

    Args:
        query:     Search / relevance query (e.g. the risk-area label).
        update_id: Only search chunks belonging to this update.
        top_k:     Maximum number of chunks to return.
        conn:      Open sqlite3 connection.

    Returns:
        List of up to *top_k* chunk dicts, most relevant first.
    """
    rows = conn.execute(
        "SELECT * FROM raw_chunks WHERE update_id = ? ORDER BY chunk_index",
        (update_id,),
    ).fetchall()

    if not rows:
        logger.warning(f"No chunks found for update_id={update_id}")
        return []

    chunks: list[dict[str, Any]] = [dict(row) for row in rows]

    if _bm25_available:
        bm25 = _build_bm25(chunks)
        if bm25 is not None:
            query_tokens = _tokenise(query)
            scores = bm25.get_scores(query_tokens)
            # Pair chunks with scores, sort descending
            scored = sorted(zip(scores, chunks), reverse=True)
            return [c for _, c in scored[:top_k]]

    # Fallback
    logger.info("Using naive retrieval (rank-bm25 not available)")
    return _naive_retrieve(chunks, query, top_k)
