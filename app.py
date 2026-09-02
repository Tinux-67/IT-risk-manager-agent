#!/usr/bin/env python3
"""
Streamlit web interface for the IT Risk Manager Agent.
Allows users to view, filter, and generate alerts from EBA/MAS regulatory updates.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
from loguru import logger

from config import Config
from scripts.logging_config import setup_logging

setup_logging()
logger.info("Starting Streamlit application")

# ── Page Config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IT Risk Manager Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Loading ────────────────────────────────────────────────────────────────

def load_css() -> None:
    """Load static/app.css into the page via st.markdown."""
    css_path = Path(__file__).parent / "static" / "app.css"
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=False)
    else:
        logger.warning(f"CSS file not found at {css_path} — skipping stylesheet")


load_css()

# ── Constants ────────────────────────────────────────────────────────────────

DB_PATH = Config.DB_PATH
RAW_DATA_DIR = Config.RAW_DATA_DIR
SCRIPTS_DIR = "scripts"

# ── Database Connection ────────────────────────────────────────────────────────

@st.cache_resource
def get_db_connection() -> sqlite3.Connection:
    """Cached database connection."""
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        st.error(f"Database not found. Run `python scripts/process_updates.py --all` first.")
        st.stop()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    return conn


# ── Data Queries ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_metrics(conn: sqlite3.Connection) -> dict:
    """Return a single-row dict of dashboard metrics."""
    c = conn.execute("""
        SELECT
            COUNT(*)                                                                       AS total,
            SUM(CASE WHEN urgency_level='Urgent'  THEN 1 ELSE 0 END)                       AS urgent,
            SUM(CASE WHEN urgency_level='High'    THEN 1 ELSE 0 END)                       AS high,
            SUM(CASE WHEN urgency_level='Medium'  THEN 1 ELSE 0 END)                       AS medium,
            SUM(CASE WHEN urgency_level='Low'     THEN 1 ELSE 0 END)                       AS low,
            SUM(CASE WHEN source='EBA'            THEN 1 ELSE 0 END)                       AS eba_count,
            SUM(CASE WHEN source='MAS'            THEN 1 ELSE 0 END)                       AS mas_count,
            SUM(CASE WHEN publication_date >= date('now','-7 days')  THEN 1 ELSE 0 END)    AS recent_7d,
            MAX(publication_date)                                                               AS last_update
        FROM updates
        WHERE is_processed = 1
    """)
    row = c.fetchone()
    names = [d[0] for d in c.description]
    return dict(zip(names, row)) if row else {}


@st.cache_data(ttl=300)
def get_updates(
    _conn: sqlite3.Connection,
    days: int = 0,
    risk_areas: list[str] | None = None,
    urgencies: list[str] | None = None,
    sources: list[str] | None = None,
    search_query: str = "",
) -> list[dict]:
    """
    Fetch updates with multi-dimensional filtering.
    All filtering is done in SQL for performance.
    """
    query = "SELECT * FROM updates WHERE is_processed = 1"
    params: list = []

    if days > 0:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query += " AND publication_date >= ?"
        params.append(cutoff)

    if risk_areas:
        placeholders = ",".join("?" * len(risk_areas))
        query += f" AND risk_area IN ({placeholders})"
        params.extend(risk_areas)

    if urgencies:
        placeholders = ",".join("?" * len(urgencies))
        query += f" AND urgency_level IN ({placeholders})"
        params.extend(urgencies)

    if sources:
        placeholders = ",".join("?" * len(sources))
        query += f" AND source IN ({placeholders})"
        params.extend(sources)

    if search_query:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    query += " ORDER BY publication_date DESC"

    c = _conn.execute(query, params)
    cols = [d[0] for d in c.description]
    return [dict(zip(cols, row)) for row in c.fetchall()]


@st.cache_data(ttl=300)
def get_filter_options(conn: sqlite3.Connection) -> dict:
    """Return the selectable options for each filter dimension."""
    c = conn.execute(
        "SELECT DISTINCT risk_area FROM updates WHERE risk_area IS NOT NULL ORDER BY risk_area"
    )
    risk_areas = [r[0] for r in c.fetchall() if r[0]]

    c = conn.execute(
        "SELECT DISTINCT urgency_level FROM updates WHERE urgency_level IS NOT NULL ORDER BY urgency_level"
    )
    urgencies = [r[0] for r in c.fetchall() if r[0]]

    c = conn.execute(
        "SELECT DISTINCT source FROM updates WHERE source IS NOT NULL ORDER BY source"
    )
    sources = [r[0] for r in c.fetchall() if r[0]]

    return {"risk_areas": risk_areas, "urgencies": urgencies, "sources": sources}


# ── UI Components ─────────────────────────────────────────────────────────────

def _urgency_class(level: str) -> str:
    return {"Urgent": "urgent", "High": "high", "Medium": "medium", "Low": "low"}.get(level, "medium")


def _groundedness_html(score: float | None) -> str:
    """Return a coloured dot + label for the groundedness score."""
    if score is None:
        return "<span class='groundedness-label'>—</span>"
    if score >= 0.8:
        cls = "groundedness-high"
        label = f"Groundedness: {score:.0%}"
    elif score >= 0.5:
        cls = "groundedness-mid"
        label = f"Groundedness: {score:.0%}"
    else:
        cls = "groundedness-low"
        label = f"Groundedness: {score:.0%}"
    return (
        f"<span class='groundedness-dot {cls}'></span>"
        f"<span class='groundedness-label'>{label}</span>"
    )


def _citation_badge_html(citation_json: str | None) -> str:
    """Return a compact citation badge showing the number of cited chunks."""
    if not citation_json:
        return "<span class='citation-badge'>📎 No citations</span>"
    try:
        chunks = json.loads(citation_json)
        if not chunks:
            return "<span class='citation-badge'>📎 No citations</span>"
        sources = {c.get("source_file", "unknown") for c in chunks}
        return (
            f"<span class='citation-badge'>"
            f"📎 {len(chunks)} chunk(s) · {len(sources)} source(s)"
            f"</span>"
        )
    except Exception:
        return "<span class='citation-badge'>📎 Citation parse error</span>"


def display_metrics_row(metrics: dict) -> None:
    """Render the top-level KPI metrics row."""
    cols = st.columns(6)
    delta_inverse = "inverse"

    def cell(col, label: str, value, delta: str | None = None, delta_col: str = "off"):
        with col:
            kw = {"label": label, "value": value}
            if delta:
                kw["delta"] = delta
                kw["delta_color"] = delta_col
            st.metric(**kw)

    cell(cols[0], "Total Updates",    metrics.get("total", 0))
    cell(cols[1], "EBA",              metrics.get("eba_count", 0))
    cell(cols[2], "MAS",              metrics.get("mas_count", 0))
    cell(cols[3], "High + Urgent",
          (metrics.get("urgent", 0) or 0) + (metrics.get("high", 0) or 0),
          delta_col="inverse")
    cell(cols[4], "Last 7 Days",     metrics.get("recent_7d", 0))
    last = metrics.get("last_update") or "—"
    cell(cols[5], "Last Update",      str(last)[:10])


def display_filter_panel(options: dict) -> tuple:
    """
    Render the collapsible advanced filter panel.
    Returns (days, risk_areas, urgencies, sources, search_query).
    """
    with st.expander("🔽 Advanced Filters", expanded=False):
        row1 = st.columns([1, 1, 1, 2])

        with row1[0]:
            days = st.number_input(
                "Look back (days, 0 = all)", min_value=0, max_value=365, value=30, step=1
            )
        with row1[1]:
            selected_sources = st.multiselect(
                "Sources", options=options.get("sources", []), default=[]
            )
        with row1[2]:
            selected_urgencies = st.multiselect(
                "Urgency", options=options.get("urgencies", []), default=[]
            )
        with row1[3]:
            search = st.text_input("🔍 Search (title or summary)", "")

        row2 = st.columns(1)
        with row2[0]:
            selected_risk_areas = st.multiselect(
                "Risk Areas",
                options=options.get("risk_areas", []),
                default=[],
                help="Filter by one or more risk areas",
            )

    return days, selected_risk_areas, selected_urgencies, selected_sources, search


def display_update_card(update: dict) -> None:
    """Render a single update as an expander card with citation and CoT."""
    urgency_cls = _urgency_class(update.get("urgency_level", "Medium"))
    citation_badge = _citation_badge_html(update.get("citation_sources"))
    groundedness_html = _groundedness_html(update.get("groundedness_score"))

    with st.expander(
        f"📄 {update['title']}  ·  "
        f"<span class='urgency-badge {urgency_cls}'>{update.get('urgency_level','—')}</span>",
        expanded=False,
    ):
        # ── Header row ──────────────────────────────────────────────────────
        col_meta, col_trust = st.columns([3, 1])

        with col_meta:
            date = update.get("publication_date", "—")
            source = update.get("source", "—")
            risk = update.get("risk_area", "—")
            st.markdown(
                f"**📅 {date}** &nbsp; **🏷️ {risk}** &nbsp; **🌐 {source}** &nbsp; "
                f"{citation_badge}",
                unsafe_allow_html=True,
            )

        with col_trust:
            st.markdown(groundedness_html, unsafe_allow_html=True)

        # ── Summary ────────────────────────────────────────────────────────
        if update.get("summary"):
            st.markdown("**📝 Summary**")
            st.markdown(update["summary"])

        # ── Reasoning Chain (CoT) ──────────────────────────────────────────
        reasoning = update.get("reasoning_chain")
        if reasoning:
            with st.expander("🧠 Chain-of-Thought Reasoning"):
                st.markdown(
                    f"<div class='reasoning-panel'>{reasoning}</div>",
                    unsafe_allow_html=True,
                )

        # ── Cited chunks ───────────────────────────────────────────────────
        raw_citations = update.get("citation_sources")
        if raw_citations:
            try:
                cited = json.loads(raw_citations)
                if cited:
                    with st.expander(f"📎 Cited Evidence ({len(cited)} chunk(s))"):
                        for i, chunk in enumerate(cited, 1):
                            st.markdown(
                                f"**Chunk {i}** — chars {chunk.get('char_start','?')}–{chunk.get('char_end','?')} "
                                f"· `{chunk.get('source_file', 'unknown')}`"
                            )
                            st.markdown(f"> {chunk.get('chunk_text', '')[:300]}{'…' if len(chunk.get('chunk_text',''))>300 else ''}")
                            st.markdown("---")
            except Exception:
                st.caption("⚠️ Could not parse citation sources.")

        # ── File ───────────────────────────────────────────────────────────
        fp = update.get("file_path", "")
        if fp:
            st.caption(f"📁 `{fp}`")


# ── Page: Dashboard ───────────────────────────────────────────────────────────

def page_dashboard() -> None:
    st.markdown('<p class="main-header">🛡️ IT Risk Manager Agent</p>', unsafe_allow_html=True)

    conn = get_db_connection()
    metrics = get_metrics(conn)
    options = get_filter_options(conn)

    display_metrics_row(metrics)

    days, risk_areas, urgencies, sources, search = display_filter_panel(options)

    st.markdown("---")
    st.markdown("### 📋 Updates")

    updates = get_updates(
        conn,
        days=days,
        risk_areas=risk_areas if risk_areas else None,
        urgencies=urgencies if urgencies else None,
        sources=sources if sources else None,
        search_query=search,
    )

    if not updates:
        st.info("No updates match the current filters.")
        return

    st.info(f"Showing {len(updates)} update(s)")
    for u in updates:
        display_update_card(u)


# ── Page: Scrape & Process ────────────────────────────────────────────────────

def page_scrape_process() -> None:
    st.markdown("## 🔄 Scrape & Process")

    # EBA scraper
    st.markdown("### 🌐 Scrape EBA")
    col_limit, col_delay, col_doctype = st.columns(3)
    with col_limit:
        limit = st.number_input("Limit", min_value=1, max_value=100, value=10, key="scrape_limit")
    with col_delay:
        delay = st.slider("Delay (s)", 0.0, 5.0, Config.EBA_DELAY, 0.1, key="scrape_delay")
    with col_doctype:
        doctype = st.text_input("Document type", value="248", key="scrape_doctype")

    if st.button("🚀 Scrape EBA", type="primary"):
        if not doctype.isdigit():
            st.error("Document type must be numeric.")
        else:
            with st.spinner("Scraping EBA…"):
                try:
                    from scripts.scrape_eba import scrape_eba
                    count = scrape_eba(limit=limit, delay=delay, document_type=doctype)
                    st.success(f"Scraped {count} publication(s).")
                except Exception as exc:
                    st.error(f"Scraping failed: {exc}")
                    logger.error(f"EBA scrape error: {exc}")

    st.markdown("---")

    # MAS scraper
    st.markdown("### 🌐 Scrape MAS")
    col_limit_m, col_delay_m = st.columns(2)
    with col_limit_m:
        limit_m = st.number_input("Limit", min_value=1, max_value=100, value=10, key="scrape_mas_limit")
    with col_delay_m:
        delay_m = st.slider("Delay (s)", 0.0, 5.0, Config.MAS_DELAY, 0.1, key="scrape_mas_delay")

    if st.button("🚀 Scrape MAS", type="primary"):
        with st.spinner("Scraping MAS…"):
            try:
                from scripts.scrape_mas import scrape_mas
                count = scrape_mas(limit=limit_m, delay=delay_m)
                st.success(f"Scraped {count} publication(s).")
            except Exception as exc:
                st.error(f"Scraping failed: {exc}")
                logger.error(f"MAS scrape error: {exc}")

    st.markdown("---")

    # Process
    st.markdown("### ⚙️ Process All Raw Files")
    if st.button("🔄 Process Files", type="primary"):
        with st.spinner("Processing…"):
            try:
                from scripts.process_updates import process_all_files
                from config import Config

                conn = sqlite3.connect(str(Config.DB_PATH))
                process_all_files(conn, max_workers=4)
                conn.close()
                st.success("Processing complete.")
                st.rerun()
            except Exception as exc:
                st.error(f"Processing failed: {exc}")
                logger.error(f"Process error: {exc}")


# ── Page: Alert Generator ─────────────────────────────────────────────────────

def page_alert_generator() -> None:
    st.markdown("## 🚨 Alert Generator")

    conn = get_db_connection()

    col_days, col_audience = st.columns(2)
    with col_days:
        days = st.number_input("Look back (days)", min_value=1, max_value=365, value=30)
    with col_audience:
        audience = st.selectbox("Audience", ["workfloor", "management", "c-level"])

    if st.button("🔄 Generate Alerts"):
        with st.spinner("Generating alerts…"):
            try:
                from scripts.generate_alerts import format_alert
                updates = get_updates(conn, days=days)
                if not updates:
                    st.warning(f"No updates found in the last {days} days.")
                    return

                for i, update in enumerate(updates, 1):
                    alert = format_alert(update, audience, use_llm=False)
                    with st.expander(f"Alert {i}: {update['title']}", expanded=i <= 3):
                        st.markdown(alert)

                # ── Export button ──────────────────────────────────────────
                full_text = "\n\n---\n\n".join(
                    format_alert(u, audience, use_llm=False) for u in updates
                )
                st.download_button(
                    "📥 Download All Alerts (.txt)",
                    data=full_text,
                    file_name=f"it_risk_alerts_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                )
            except Exception as exc:
                st.error(f"Alert generation failed: {exc}")
                logger.error(f"Alert generation error: {exc}")


# ── Page: Run Migration ───────────────────────────────────────────────────────

def page_migration() -> None:
    st.markdown("## 🗄️ Database Migration")

    st.info(
        "The Trust layer migration adds citation, reasoning chain, and "
        "groundedness score columns. Run this once after upgrading."
    )

    conn = get_db_connection()
    c = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    has_version = c.fetchone() is not None

    if has_version:
        row = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        st.success(f"Migration schema version: **{row[0] if row else 'unknown'}**")
    else:
        st.warning("No schema version record found — migration may not have been run.")

    if st.button("▶️ Run Trust Layer Migration"):
        try:
            from scripts.migrations.add_trust_columns import _apply_migration
            _apply_migration(conn, dry_run=False)
            st.success("Migration applied successfully.")
            st.rerun()
        except Exception as exc:
            st.error(f"Migration failed: {exc}")
            logger.error(f"Migration error: {exc}")
        finally:
            conn.close()


# ── Main ──────────────────────────────────────────────────────────────────────

PAGES = {
    "🏠 Overview": page_dashboard,
    "🔄 Scrape & Process": page_scrape_process,
    "🚨 Alert Generator": page_alert_generator,
    "🗄️ Migration": page_migration,
}


def main() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "🏠 Overview"

    st.sidebar.title("📋 Navigation")
    st.sidebar.markdown("---")

    selection = st.sidebar.radio("Go to", list(PAGES.keys()))
    st.session_state.page = selection

    PAGES[selection]()

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "IT Risk Manager Agent · Powered by Mistral-7B & SQLite · "
        "[GitHub](https://github.com/Tinux-67/IT-risk-manager-agent)"
    )
    logger.info(f"Page viewed: {selection}")


if __name__ == "__main__":
    main()
