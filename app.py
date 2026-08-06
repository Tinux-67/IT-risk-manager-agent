#!/usr/bin/env python3
"""
Streamlit web interface for the IT Risk Manager Agent.
Allows users to view, filter, and generate alerts from EBA regulatory updates.
"""

import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta

import streamlit as st
from loguru import logger

from config import Config
from scripts.logging_config import setup_logging

setup_logging()
logger.info("Starting Streamlit application")

# Constants
DB_PATH = Config.DB_PATH
RAW_DATA_DIR = Config.RAW_DATA_DIR
SCRIPTS_DIR = "scripts"

# Page configuration
st.set_page_config(
    page_title="IT Risk Manager Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .urgency-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
        display: inline-block;
    }
    .urgent { background-color: #ff4444; color: white; }
    .high { background-color: #ff8800; color: white; }
    .medium { background-color: #ffcc00; color: black; }
    .low { background-color: #44ff44; color: black; }
    .risk-area-tag {
        background-color: #e0e0e0;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
        display: inline-block;
        margin-right: 0.5rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}. Please run `process_updates.py` first.")
        st.error(f"Database not found at {DB_PATH}. Please run `process_updates.py` first.")
        st.stop()
    logger.debug(f"Connecting to database at {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def run_script(script_name: str, args: list[str] | None = None) -> tuple[bool, str]:
    """Run a Python script and return (success, output)."""
    if args is None:
        args = []

    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        logger.error(f"Script {script_name} not found at {script_path}")
        return False, f"Script {script_name} not found."

    try:
        logger.info(f"Running script: {script_name} with args: {args}")
        cmd = [sys.executable, script_path] + args
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
        )
        if result.returncode == 0:
            logger.success(f"Script {script_name} completed successfully")
            return True, result.stdout
        else:
            logger.error(f"Script {script_name} failed with return code {result.returncode}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"Script {script_name} timed out")
        return False, "Script execution timed out."
    except Exception as e:
        logger.error(f"Error running script {script_name}: {e}")
        return False, str(e)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_updates(
    _conn: sqlite3.Connection,
    days: int = 365,
    risk_area: str | None = None,
    urgency: str | None = None,
) -> list[dict]:
    """Get updates from the database with optional filters."""
    logger.debug(
        f"Getting updates with filters: days={days}, risk_area={risk_area}, urgency={urgency}"
    )
    cursor = _conn.cursor()

    query = """
        SELECT id, title, publication_date, risk_area, urgency_level, raw_text, file_path, summary
        FROM updates
        WHERE is_processed = 1
    """
    params = []

    if days > 0:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query += " AND publication_date >= ?"
        params.append(cutoff_date)

    if risk_area:
        query += " AND risk_area = ?"
        params.append(risk_area)

    if urgency:
        query += " AND urgency_level = ?"
        params.append(urgency)

    query += " ORDER BY publication_date DESC"

    cursor.execute(query, params)
    columns = [col[0] for col in cursor.description]
    updates = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    logger.debug(f"Found {len(updates)} updates matching criteria")
    return updates


@st.cache_data(ttl=300)
def get_risk_areas(_conn: sqlite3.Connection) -> list[str]:
    """Get all unique risk areas from the database."""
    logger.debug("Getting unique risk areas from database")
    cursor = _conn.cursor()
    cursor.execute("SELECT DISTINCT risk_area FROM updates WHERE risk_area IS NOT NULL")
    return [row[0] for row in cursor.fetchall() if row[0]]


@st.cache_data(ttl=300)
def get_urgency_levels(_conn: sqlite3.Connection) -> list[str]:
    """Get all unique urgency levels from the database."""
    logger.debug("Getting unique urgency levels from database")
    cursor = _conn.cursor()
    cursor.execute("SELECT DISTINCT urgency_level FROM updates WHERE urgency_level IS NOT NULL")
    return [row[0] for row in cursor.fetchall() if row[0]]


def display_update_card(update: dict) -> None:
    """Display a single update as a card."""
    urgency_class = {
        "Urgent": "urgent",
        "High": "high",
        "Medium": "medium",
        "Low": "low",
    }.get(update["urgency_level"], "medium")

    with st.expander(f"\ud83d\udcc4 {update['title']}", expanded=False):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**\ud83d\udcc5 Date:** {update['publication_date']}")
            st.markdown(
                f"**\ud83c\udff7\ufe0f Risk Area:** <span class='risk-area-tag'>{update['risk_area']}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"**\u26a0\ufe0f Urgency:** <span class='urgency-badge {urgency_class}'>{update['urgency_level']}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**\ud83d\udcc1 File:** `{update['file_path']}`")

        with col2:
            if st.button("\ud83d\udd0d View Details", key=f"view_{update['id']}"):
                st.session_state["selected_update"] = update
                st.session_state["page"] = "Detail View"
                st.rerun()

        if update.get("summary"):
            st.markdown("**\ud83d\udcdd Summary:**")
            st.markdown(update["summary"])


def display_update_detail(update: dict) -> None:
    """Display detailed view of a single update."""
    logger.debug(f"Displaying details for update: {update['title']}")
    st.markdown("## \ud83d\udcc4 Update Details")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"**Title:** {update['title']}")
        st.markdown(f"**Publication Date:** {update['publication_date']}")
        st.markdown(f"**Risk Area:** {update['risk_area']}")
        st.markdown(f"**Urgency Level:** {update['urgency_level']}")
        st.markdown(f"**File Path:** `{update['file_path']}`")

    with col2:
        if st.button("\u2b05 Back to Overview"):
            st.session_state.pop("selected_update", None)
            st.session_state["page"] = "Overview"
            st.rerun()

    st.markdown("---")

    # Display raw text
    st.markdown("### \ud83d\udcdd Full Text")
    if update.get("raw_text"):
        st.text_area("", update["raw_text"], height=300, key=f"text_{update['id']}")
    else:
        st.info("No text available.")

    # Display summary
    if update.get("summary"):
        st.markdown("### \ud83d\udccc Summary")
        st.markdown(update["summary"])


def display_alert_generator() -> None:
    """Display the alert generator interface."""
    logger.debug("Displaying alert generator interface")
    st.markdown("## \ud83d\udea8 Alert Generator")

    conn = get_db_connection()

    col1, col2, col3 = st.columns(3)
    with col1:
        days = st.number_input("Look back (days)", min_value=1, max_value=365, value=30)
    with col2:
        audience = st.selectbox("Audience", ["workfloor", "management", "c-level"])
    with col3:
        use_llm = st.checkbox("Use LLM (Ollama)", value=True)

    if st.button("\ud83d\udd04 Generate Alerts"):
        with st.spinner("Generating alerts..."):
            # Get updates
            updates = get_updates(conn, days=days)

            if not updates:
                logger.warning(f"No updates found in the last {days} days")
                st.warning(f"No updates found in the last {days} days.")
                return

            logger.info(f"Generating alerts for {len(updates)} updates")

            # Generate alerts for each update
            from scripts.generate_alerts import format_alert  # noqa: PLC0415
            for i, update in enumerate(updates, 1):
                with st.expander(f"Alert {i}: {update['title']}", expanded=True):
                    # Simulate the alert generation
                    if use_llm:
                        try:
                            alert = format_alert(update, audience, use_llm=True)
                            st.markdown(alert)
                        except Exception as e:
                            logger.error(f"Error generating LLM alert: {e}")
                            st.error(f"Error generating LLM alert: {e}")
                            st.markdown(
                                f"**Title:** {update['title']}\n**Date:** {update['publication_date']}\n**Risk Area:** {update['risk_area']}"
                            )
                    else:
                        st.markdown(
                            f"**Title:** {update['title']}\n**Date:** {update['publication_date']}\n**Risk Area:** {update['risk_area']}"
                        )
                        st.markdown(
                            f"**Summary:** {update.get('summary', 'No summary available.')}"
                        )

    conn.close()


def display_scrape_and_process() -> None:
    """Display the scrape and process interface."""
    logger.debug("Displaying scrape and process interface")
    st.markdown("## \ud83d\udd04 Scrape & Process")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### \ud83c\udf10 Scrape EBA Updates")
        limit = st.number_input("Number of updates to scrape", min_value=1, max_value=50, value=5)
        delay = st.slider("Delay between requests (seconds)", 0.0, 5.0, 1.0, 0.1)
        document_type = st.text_input("Document type filter", value="248")

        # Prevent concurrent scrape runs
        if "scraping_running" not in st.session_state:
            st.session_state["scraping_running"] = False

        if st.button("\ud83d\ude80 Start Scraping", disabled=st.session_state["scraping_running"]):
            st.session_state["scraping_running"] = True
            with st.spinner("Scraping EBA website..."):
                # Input validation: document_type must be numeric
                if not document_type.strip().isdigit():
                    st.session_state["scraping_running"] = False
                    st.error("Document type must be a numeric value (e.g. 248).")
                    return
                success, output = run_script(
                    "scrape_eba.py",
                    [
                        "--limit",
                        str(limit),
                        "--delay",
                        str(delay),
                        "--document-type",
                        document_type.strip(),
                    ],
                )
                if success:
                    logger.success("Scraping completed successfully")
                    st.success("Scraping completed successfully!")
                    st.text(output)
                else:
                    logger.error(f"Scraping failed: {output}")
                    st.error(f"Scraping failed:\n{output}")
            st.session_state["scraping_running"] = False

    with col2:
        st.markdown("### \ud83d\udcc1 Process Updates")

        if st.button("\ud83d\udd04 Process All Files"):
            with st.spinner("Processing files..."):
                success, output = run_script("process_updates.py", ["--all"])
                if success:
                    logger.success("Processing completed successfully")
                    st.success("Processing completed successfully!")
                    st.text(output)
                else:
                    logger.error(f"Processing failed: {output}")
                    st.error(f"Processing failed:\n{output}")


def display_dashboard() -> None:
    """Display the main dashboard with metrics."""
    logger.debug("Displaying dashboard")
    st.markdown(
        '<p class="main-header">\ud83d\udee1\ufe0f IT Risk Manager Agent</p>',
        unsafe_allow_html=True,
    )

    conn = get_db_connection()

    # Get metrics — single query for performance
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN urgency_level='Urgent' THEN 1 ELSE 0 END) AS urgent,
            SUM(CASE WHEN urgency_level='High' THEN 1 ELSE 0 END) AS high,
            SUM(CASE WHEN publication_date >= date('now','-7 days') THEN 1 ELSE 0 END) AS recent
        FROM updates WHERE is_processed = 1
    """)
    row = cursor.fetchone()
    total_updates = row[0] or 0
    urgent_count = row[1] or 0
    high_count = row[2] or 0
    recent_count = row[3] or 0

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Updates", total_updates)
    with col2:
        st.metric("Urgent", urgent_count, delta_color="inverse")
    with col3:
        st.metric("High Priority", high_count, delta_color="inverse")
    with col4:
        st.metric("Recent (7d)", recent_count)

    conn.close()


def main() -> None:
    """Main function for the Streamlit app."""
    logger.info("Streamlit app main function started")

    # Initialize session state
    if "page" not in st.session_state:
        st.session_state["page"] = "Overview"

    if "selected_update" not in st.session_state:
        st.session_state["selected_update"] = None

    # Sidebar navigation
    st.sidebar.title("\ud83d\udccc Navigation")

    # Define pages without emojis for session state
    pages = ["Overview", "Detail View", "Alert Generator", "Scrape & Process"]
    page_labels = [
        "\ud83c\udfe0 Overview",
        "\ud83d\udd0d Detail View",
        "\ud83d\udea8 Alert Generator",
        "\ud83d\udd04 Scrape & Process",
    ]

    # Find the current page index
    try:
        current_index = pages.index(st.session_state["page"])
    except ValueError:
        current_index = 0
        st.session_state["page"] = pages[0]

    # Display radio buttons with emojis
    selected_page = st.sidebar.radio(
        "Go to",
        page_labels,
        index=current_index,
    )

    # Map the selected page label back to the page name
    st.session_state["page"] = pages[page_labels.index(selected_page)]

    # Display the selected page
    if st.session_state["page"] == "Overview":
        display_dashboard()

        st.markdown("---")
        st.markdown("## \ud83d\udccb Recent Updates")

        conn = get_db_connection()

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            days = st.number_input(
                "Last N days", min_value=0, max_value=365, value=30, key="filter_days"
            )
        with col2:
            risk_areas = ["All"] + get_risk_areas(conn)
            selected_risk_area = st.selectbox("Risk Area", risk_areas)
        with col3:
            urgency_levels = ["All"] + get_urgency_levels(conn)
            selected_urgency = st.selectbox("Urgency", urgency_levels)

        # Get filtered updates
        risk_area_filter = selected_risk_area if selected_risk_area != "All" else None
        urgency_filter = selected_urgency if selected_urgency != "All" else None
        updates = get_updates(conn, days=days, risk_area=risk_area_filter, urgency=urgency_filter)

        if not updates:
            st.info("No updates found matching the filters.")
        else:
            st.info(f"Found {len(updates)} updates")
            for update in updates:
                display_update_card(update)

        conn.close()

    elif st.session_state["page"] == "Detail View":
        if st.session_state["selected_update"]:
            display_update_detail(st.session_state["selected_update"])
        else:
            st.info("Select an update from the Overview page to view details.")
            if st.button("Go to Overview"):
                st.session_state["page"] = "Overview"
                st.rerun()

    elif st.session_state["page"] == "Alert Generator":
        display_alert_generator()

    elif st.session_state["page"] == "Scrape & Process":
        display_scrape_and_process()

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>IT Risk Manager Agent | Powered by Mistral-7B & SQLite | <a href="https://github.com/Tinux-67/IT-risk-manager-agent">GitHub</a></p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    logger.info("Streamlit app main function completed")


if __name__ == "__main__":
    main()
