#!/usr/bin/env python3
"""
Shared LLM utilities for the IT Risk Manager Agent.
Provides Ollama integration with SQLite-backed response caching.
"""

import hashlib
import sqlite3
from datetime import datetime, timedelta

from loguru import logger

from config import Config

# 24h TTL — regulatory documents change rarely
OLLAMA_CACHE_EXPIRY_HOURS = 24


def get_cache_key(prompt: str, model: str) -> str:
    """Generate a deterministic SHA-256 cache key from prompt and model."""
    return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()


def init_ollama_cache(conn: sqlite3.Connection) -> None:
    """Create the ollama_cache table if it does not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ollama_cache (
            cache_key  TEXT PRIMARY KEY,
            model      TEXT NOT NULL,
            prompt     TEXT NOT NULL,
            response   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)
    conn.commit()


def get_cached_response(conn: sqlite3.Connection, prompt: str, model: str) -> str | None:
    """Return a valid (non-expired) cached response, or None."""
    key = get_cache_key(prompt, model)
    row = conn.execute(
        "SELECT response FROM ollama_cache WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP",
        (key,),
    ).fetchone()
    return row[0] if row else None


def cache_response(conn: sqlite3.Connection, prompt: str, model: str, response: str) -> None:
    """Persist an Ollama response with a 24-hour TTL."""
    key = get_cache_key(prompt, model)
    expires_at = (datetime.now() + timedelta(hours=OLLAMA_CACHE_EXPIRY_HOURS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO ollama_cache
            (cache_key, model, prompt, response, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (key, model, prompt, response, expires_at),
    )
    conn.commit()
    logger.debug(f"Cached Ollama response (key={key[:8]}…, expires={expires_at})")


def get_ollama_response(
    prompt: str,
    model: str | None = None,
    conn: sqlite3.Connection | None = None,
    max_tokens: int = 200,
) -> str | None:
    """
    Query Ollama with SQLite caching.

    Args:
        prompt:     The prompt to send.
        model:      Model name; defaults to Config.OLLAMA_MODEL.
        conn:       Optional DB connection for cache read/write.
        max_tokens: Maximum tokens in the response.

    Returns:
        The model response string, or None if Ollama is unavailable.
    """
    if model is None:
        model = Config.OLLAMA_MODEL

    if conn:
        cached = get_cached_response(conn, prompt, model)
        if cached:
            logger.debug("Returning cached Ollama response")
            return cached

    try:
        import ollama as _ollama

        client = _ollama.Client(host=Config.OLLAMA_HOST)
        logger.debug(f"Calling Ollama (model={model}, prompt_len={len(prompt)})")
        resp = client.generate(
            model=model,
            prompt=prompt,
            options={"temperature": 0.1, "num_predict": max_tokens},
        )
        text = str(resp["response"]).strip()

        if conn and text:
            cache_response(conn, prompt, model, text)

        return text

    except ImportError:
        logger.warning("ollama package not installed – run: pip install ollama")
        return None
    except Exception as exc:
        logger.error(f"Ollama error: {exc}")
        return None
