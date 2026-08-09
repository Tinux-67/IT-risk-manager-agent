"""
Tests for app.py helper functions (non-Streamlit, pure-Python logic).

Note: Streamlit widget rendering (st.button, st.expander, etc.) is not tested
here -- those require a running Streamlit server. We test pure-Python helpers
that can be imported and called in isolation.

Because Streamlit may not be installed in CI/test environments, we inject a
full mock of the ``streamlit`` package into ``sys.modules`` before importing
``app``, which prevents the ``st.set_page_config`` call at module level from
raising ModuleNotFoundError.
"""

import sqlite3
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Streamlit module stub (injected once at collection time)
# ---------------------------------------------------------------------------


def _make_streamlit_stub() -> types.ModuleType:
    """Return a minimal stub for the ``streamlit`` package."""
    st = types.ModuleType("streamlit")
    # Commonly called at module level in app.py
    st.set_page_config = MagicMock()
    st.markdown = MagicMock()
    st.error = MagicMock()
    st.stop = MagicMock()
    # Other st.* used inside functions -- provide no-op mocks
    for name in (
        "cache_data", "cache_resource", "button", "expander", "columns", "text_area",
        "info", "session_state", "rerun", "sidebar", "title", "header",
        "subheader", "write", "success", "warning", "spinner", "selectbox",
        "multiselect", "slider", "checkbox", "radio", "text_input",
        "number_input", "date_input", "time_input", "file_uploader",
        "download_button", "metric", "dataframe", "table", "map",
        "plotly_chart", "altair_chart", "bar_chart", "line_chart",
        "area_chart", "image", "audio", "video", "progress", "empty",
        "container", "tabs", "balloons", "snow",
    ):
        attr = MagicMock()
        # Make cache_data usable as a decorator: @st.cache_data(ttl=...)
        if name == "cache_data":
            attr.return_value = lambda fn: fn  # decorator passthrough
            attr.side_effect = None
        setattr(st, name, attr)

    # Also expose st.cache_data as a no-op decorator when called with args
    def _cache_data_decorator(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]  # @st.cache_data (no args)
        return lambda fn: fn  # @st.cache_data(ttl=...)

    st.cache_data = _cache_data_decorator

    def _cache_resource_decorator(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]  # @st.cache_resource (no args)
        return lambda fn: fn  # @st.cache_resource(...)

    st.cache_resource = _cache_resource_decorator
    return st


if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = _make_streamlit_stub()

# Also stub scripts.logging_config so setup_logging() is a no-op
if "scripts.logging_config" not in sys.modules:
    _lc = types.ModuleType("scripts.logging_config")
    _lc.setup_logging = MagicMock()
    sys.modules["scripts.logging_config"] = _lc


# ---------------------------------------------------------------------------
# Import app after stubs are in place
# ---------------------------------------------------------------------------


import app as _app_module  # noqa: E402 -- must come after sys.modules injection

# ---------------------------------------------------------------------------
# run_script
# ---------------------------------------------------------------------------


class TestRunScript:
    """Tests for run_script() in app.py."""

    def test_run_script_missing_file(self):
        """Should return (False, 'not found') when script path does not exist."""
        success, output = _app_module.run_script("nonexistent_script_xyz_abc.py")
        assert success is False
        assert "not found" in output.lower()

    def test_run_script_success(self, tmp_path):
        """Should return (True, stdout) when script exits with code 0."""
        script = tmp_path / "ok_script.py"
        script.write_text("print('hello from ok_script')\n")

        with patch.object(_app_module, "SCRIPTS_DIR", str(tmp_path)):
            success, output = _app_module.run_script("ok_script.py")

        assert success is True
        assert "hello from ok_script" in output

    def test_run_script_failure(self, tmp_path):
        """Should return (False, ...) when script exits with non-zero code."""
        script = tmp_path / "fail_script.py"
        script.write_text("import sys; sys.exit(1)\n")

        with patch.object(_app_module, "SCRIPTS_DIR", str(tmp_path)):
            success, output = _app_module.run_script("fail_script.py")

        assert success is False


# ---------------------------------------------------------------------------
# get_updates / get_risk_areas / get_urgency_levels (via direct SQLite)
# ---------------------------------------------------------------------------


class TestDBQueryFunctions:
    """Tests for database query helpers using an in-memory SQLite connection."""

    @pytest.fixture()
    def db_with_sample(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE updates (
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
            );
        """)
        conn.execute("""
            INSERT INTO updates
                (title, publication_date, risk_area, urgency_level, source, is_processed)
            VALUES ('DORA Update', '2024-01-01', 'Cybersecurity', 'High', 'EBA', 1)
        """)
        conn.execute("""
            INSERT INTO updates
                (title, publication_date, risk_area, urgency_level, source, is_processed)
            VALUES ('MAS Notice', '2024-02-01', 'Compliance', 'Medium', 'MAS', 1)
        """)
        conn.commit()
        yield conn
        conn.close()

    def test_get_updates_returns_list(self, db_with_sample):
        results = _app_module.get_updates(db_with_sample, days=3650)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_get_updates_filter_risk_area(self, db_with_sample):
        results = _app_module.get_updates(db_with_sample, days=3650, risk_area="Cybersecurity")
        assert len(results) >= 1
        assert all(r["risk_area"] == "Cybersecurity" for r in results)

    def test_get_updates_filter_urgency(self, db_with_sample):
        results = _app_module.get_updates(db_with_sample, days=3650, urgency="High")
        assert len(results) >= 1
        assert all(r["urgency_level"] == "High" for r in results)

    def test_get_risk_areas(self, db_with_sample):
        areas = _app_module.get_risk_areas(db_with_sample)
        assert "Cybersecurity" in areas
        assert "Compliance" in areas

    def test_get_urgency_levels(self, db_with_sample):
        levels = _app_module.get_urgency_levels(db_with_sample)
        assert "High" in levels
        assert "Medium" in levels
