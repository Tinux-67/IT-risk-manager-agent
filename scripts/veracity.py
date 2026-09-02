#!/usr/bin/env python3
"""
Groundedness / veracity scoring for cited LLM outputs.

Given a cited source text and a summary, asks the LLM to rate how well
the summary is grounded in the source on a 0.0–1.0 scale.

The score is cached in the existing ollama_cache table.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timedelta

from loguru import logger

# ── Prompt ────────────────────────────────────────────────────────────────────

VERACITY_PROMPT = """
You are a factual accuracy evaluator. Your task is to assess whether a summary is
faithfully grounded in the cited source text.

Rate the groundedness of the summary on a scale from 0.0 to 1.0:
  0.0 — the summary contradicts or fabricates information not present in the source
  0.5 — the summary is partially supported but contains omissions or inaccuracies
  1.0 — the summary is fully and accurately derived from the source

Respond with ONLY a single number between 0.0 and 1.0. No explanation, no units.

---
SOURCE:
{cited_text}
---
SUMMARY:
{summary}
---
SCORE:
"""

# ── Score Parsing ─────────────────────────────────────────────────────────────

# Matches 0.0-1.0 numbers with optional leading/trailing text.
# Handles: "0.9", "1.0", "0", "1", "0.85 is the score", "Score:0.72"
# Rejects: negative numbers (checked at call-site), numbers > 1.0 (clamped).
_SCORE_RE = re.compile(r"\b(0|[1-9]\d*)(?:\.(\d{1,3}))?\b|\b(1\.0+)\b")


def _parse_score(raw: str) -> float | None:
    """Extract a 0.0–1.0 score from an LLM response string.

    Handles LLM formatting quirks: leading zeros, trailing text, embedded scores.
    Rejects negative numbers (e.g. "-0.3") by checking the character before the
    match start, and numbers > 1.0 by clamping via max/min.
    """
    m = _SCORE_RE.search(raw)
    if not m:
        return None
    # Reject if immediately preceded by a minus sign (negation, not formatting)
    if m.start() > 0 and raw[m.start() - 1] == "-":
        return None
    try:
        score = float(m.group())
    except ValueError:
        return None
    return max(0.0, min(1.0, score))


# ── Main Function ──────────────────────────────────────────────────────────────


def score_groundedness(
    cited_text: str,
    summary: str,
    model: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> float:
    """
    Score how well *summary* is grounded in *cited_text*.

    Args:
        cited_text: Concatenated text of the retrieved + cited source chunks.
        summary:    The LLM-generated summary to evaluate.
        model:      Ollama model name. Defaults to "mistral".
        conn:       Optional sqlite3 connection. When provided, the result is
                    cached in the ollama_cache table using a hash of both inputs.

    Returns:
        A float in [0.0, 1.0]. Defaults to 0.5 on parse failure or LLM error.
    """
    # ── Try to load Ollama lazily ────────────────────────────────────────────
    try:
        import ollama as _ollama
    except ImportError:
        logger.warning("ollama package not installed — cannot score groundedness")
        return 0.5

    # ── Cache lookup ─────────────────────────────────────────────────────────
    cache_key = hashlib.sha256((cited_text + summary).encode()).hexdigest()
    if conn:
        row = conn.execute(
            "SELECT response FROM ollama_cache WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP",
            (cache_key,),
        ).fetchone()
        if row:
            try:
                return float(row[0])
            except ValueError:
                pass

    # ── LLM call ─────────────────────────────────────────────────────────────
    prompt = VERACITY_PROMPT.format(cited_text=cited_text, summary=summary)

    try:
        client = _ollama.Client(host="http://localhost:11434")
        resp = client.generate(
            model=model or "mistral",
            prompt=prompt,
            options={"temperature": 0.0, "num_predict": 16},  # only need a short score
        )
        raw = str(resp.get("response", "")).strip()

    except Exception as exc:
        logger.error(f"Ollama veracity call failed: {exc}")
        return 0.5

    # ── Parse + cache ────────────────────────────────────────────────────────
    score = _parse_score(raw)
    if score is None:
        logger.warning(f"Could not parse veracity score from: {raw!r} — defaulting to 0.5")
        score = 0.5

    if conn:
        key = hashlib.sha256((cited_text + summary).encode()).hexdigest()
        expires_at = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            INSERT OR REPLACE INTO ollama_cache
                (cache_key, model, prompt, response, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, model or "mistral", prompt, str(score), expires_at),
        )
        conn.commit()
        logger.debug(f"Cached veracity score: {score}")

    return score
