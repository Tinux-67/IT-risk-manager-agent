"""IT Risk Management Streamlit UX demo app.

Deze app demonstreert het Fase A component design system in een IT Risk
Management context. De app valt terug op inline fallback-implementaties als de
component library niet beschikbaar is.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import streamlit as st

# ---------------------------------------------------------------------------
# Realistische Fase A component imports + fallback
# ---------------------------------------------------------------------------

try:
    from components.ui import inject_design_system
except ImportError as _err:  # pragma: no cover - demo fallback
    def inject_design_system() -> None:
        """Injecteer het donkere design system als eerste Streamlit configuratie."""
        st.set_page_config(
            page_title="IT Risk Management Demo",
            page_icon="🛡️",
            layout="wide",
            initial_sidebar_state="expanded",
        )
        st.markdown(
            """
            <style>
                :root {
                    --color-bg: #0f1117;
                    --color-surface: #181b24;
                    --color-surface-elevated: #20242f;
                    --color-border: #2b303b;
                    --color-text: #e8eaed;
                    --color-text-muted: #9aa0a6;
                    --color-primary: #8ab4f8;
                    --color-success: #81c995;
                    --color-warning: #fdd663;
                    --color-danger: #f28b82;
                    --color-info: #8ab4f8;
                }
                body, .stApp { background-color: var(--color-bg) !important; color: var(--color-text) !important; }
                [data-testid="stSidebar"] { background-color: var(--color-surface) !important; }
                .block-container { padding-top: 1rem; }
            </style>
            """,
            unsafe_allow_html=True,
        )

try:
    from components.ui import render_button
except ImportError:  # pragma: no cover - demo fallback
    def render_button(
        label: str,
        variant: str = "primary",
        icon: str | None = None,
        danger: bool = False,
        ghost: bool = False,
        key: str | None = None,
        on_click: Callable[[], None] | None = None,
    ) -> bool:
        """Fallback button renderer die standaard Streamlit buttons gebruikt."""
        full_label = f"{icon} {label}" if icon else label
        if danger:
            return st.button(full_label, key=key, type="primary", on_click=on_click)
        if ghost:
            return st.button(full_label, key=key, type="tertiary", on_click=on_click)
        if variant in ("secondary", "default"):
            return st.button(full_label, key=key, type="secondary", on_click=on_click)
        return st.button(full_label, key=key, type="primary", on_click=on_click)

try:
    from components.ui import render_card, render_metric_card
except ImportError:  # pragma: no cover - demo fallback
    def render_card(
        title: str | None = None,
        body: str | None = None,
        footer: str | None = None,
        variant: str = "default",
        accent: str | None = None,
        key: str | None = None,
    ) -> None:
        """Fallback card renderer."""
        border = "1px solid var(--color-border)"
        if variant == "outlined":
            border = "1px solid var(--color-primary)"
        if accent == "danger":
            border = "1px solid var(--color-danger)"
        bg = "var(--color-surface)"
        if variant in ("interactive", "header"):
            bg = "var(--color-surface-elevated)"
        html = f"""
        <div style="background-color:{bg}; border:{border}; border-radius:8px; padding:16px; margin-bottom:12px;">
        """
        if title:
            html += f"<h4 style='margin-top:0; color:var(--color-text);'>{title}</h4>"
        if body:
            html += f"<p style='color:var(--color-text-muted); margin-bottom:0;'>{body}</p>"
        if footer:
            html += f"<div style='margin-top:12px; color:var(--color-text-muted); font-size:0.85rem;'>{footer}</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    def render_metric_card(
        label: str,
        value: str | int | float,
        delta: str | None = None,
        key: str | None = None,
    ) -> None:
        """Fallback metric card renderer."""
        delta_html = f"<span style='color:var(--color-success);'>{delta}</span>" if delta else ""
        html = f"""
        <div style="background-color:var(--color-surface); border:1px solid var(--color-border); border-radius:8px; padding:16px; margin-bottom:12px;">
            <div style="font-size:0.85rem; color:var(--color-text-muted);">{label}</div>
            <div style="font-size:2rem; font-weight:bold; color:var(--color-text);">{value}</div>
            {delta_html}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

try:
    from components.ui import render_badge
except ImportError:  # pragma: no cover - demo fallback
    def render_badge(label: str, variant: str = "default", outline: bool = False) -> str:
        """Fallback badge renderer; rendert HTML direct en returned het ook."""
        colors = {
            "default": "#9aa0a6",
            "success": "#81c995",
            "warning": "#fdd663",
            "danger": "#f28b82",
            "info": "#8ab4f8",
        }
        color = colors.get(variant, colors["default"])
        bg = "transparent" if outline else f"{color}22"
        border = f"1px solid {color}"
        badge_html = f"""
        <span style="display:inline-block; background-color:{bg}; color:{color}; border:{border}; border-radius:999px; padding:2px 10px; font-size:0.75rem; font-weight:600;">
            {label}
        </span>
        """
        st.markdown(badge_html, unsafe_allow_html=True)
        return badge_html

try:
    from components.ui import render_alert
except ImportError:  # pragma: no cover - demo fallback
    def render_alert(message: str, kind: str = "info") -> None:
        """Fallback alert renderer via Streamlit native toasts."""
        mapping = {
            "info": st.info,
            "success": st.success,
            "warning": st.warning,
            "error": st.error,
        }
        renderer = mapping.get(kind, st.info)
        renderer(message)

try:
    from components.ui import show_spinner, show_notify
except ImportError:  # pragma: no cover - demo fallback
    def show_spinner(text: str = "Bezig...") -> None:
        """Fallback spinner renderer."""
        with st.spinner(text):
            time.sleep(0.5)

    def show_notify(message: str, kind: str = "info") -> None:
        """Fallback notify renderer via toast (indien beschikbaar)."""
        icon = "ℹ️" if kind == "info" else "✅" if kind == "success" else "⚠️"
        if hasattr(st, "toast"):
            st.toast(message, icon=icon)
        else:
            st.info(f"{icon} {message}")


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

RISICOS: list[dict[str, Any]] = [
    {
        "id": 1,
        "titel": "Datalek",
        "level": "critical",
        "status": "open",
        "eigenaar": "J. van Dijk",
        "datum": "2026-09-10",
        "beschrijving": "Mogelijk ongeautoriseerde toegang tot klantdata.",
    },
    {
        "id": 2,
        "titel": "Compliance audit ISO 27001",
        "level": "high",
        "status": "in_progress",
        "eigenaar": "M. de Vries",
        "datum": "2026-09-12",
        "beschrijving": "Openstaande acties voor ISO certificering.",
    },
    {
        "id": 3,
        "titel": "Downtime productieomgeving",
        "level": "medium",
        "status": "open",
        "eigenaar": "A. Smit",
        "datum": "2026-09-14",
        "beschrijving": "SLA risico bij ongeplande uitval.",
    },
    {
        "id": 4,
        "titel": "Budgetoverschrijding",
        "level": "low",
        "status": "closed",
        "eigenaar": "F. Bakker",
        "datum": "2026-09-05",
        "beschrijving": "Cloudkosten binnen verwachte marge gehouden.",
    },
    {
        "id": 5,
        "titel": "Phishing campagne",
        "level": "high",
        "status": "open",
        "eigenaar": "P. Jansen",
        "datum": "2026-09-15",
        "beschrijving": "Verhoogde phishing activiteit gemeld.",
    },
    {
        "id": 6,
        "titel": "Backup monitoring",
        "level": "medium",
        "status": "in_progress",
        "eigenaar": "L. Peters",
        "datum": "2026-09-13",
        "beschrijving": "Backup controles moeten worden verbeterd.",
    },
    {
        "id": 7,
        "titel": "Legacy systeem ondersteuning",
        "level": "low",
        "status": "open",
        "eigenaar": "K. Mulder",
        "datum": "2026-09-16",
        "beschrijving": "EOL planning vereist prioritering.",
    },
    {
        "id": 8,
        "titel": "Ransomware preventie",
        "level": "critical",
        "status": "open",
        "eigenaar": "S. Vermeer",
        "datum": "2026-09-16",
        "beschrijving": "Detectie en isolatie processen verouderd.",
    },
]

METRICS: dict[str, int] = {
    "totaal_risicos": 42,
    "critical": 5,
    "high": 12,
    "medium": 18,
    "low": 7,
    "open_acties": 12,
    "gesloten_acties": 30,
}

LEVEL_ORDER = ["critical", "high", "medium", "low"]
STATUS_OPTIONS = ["open", "in_progress", "closed"]

LEVEL_BADGE_MAP = {
    "critical": "danger",
    "high": "warning",
    "medium": "default",
    "low": "success",
}

STATUS_BADGE_MAP = {
    "open": "warning",
    "in_progress": "info",
    "closed": "success",
}


# ---------------------------------------------------------------------------
# Helper functies
# ---------------------------------------------------------------------------

def _capitalize_label(value: str) -> str:
    """Human-readable label voor level/status."""
    # return value.replace("_", " ").title()


def _set_page(page: str) -> None:
    """Wijzig de huidige pagina in session state en ververs de app."""
    st.session_state.current_page = page
    _rerun()


def _rerun() -> None:
    """Herlaad de app met de best beschikbare Streamlit rerun API."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def _percentage(part: int, total: int) -> int:
    """Bereken percentage; geef 0 terug als total 0 is."""
    return int((part / total) * 100) if total else 0


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar() -> None:
    """Render de zijbalk met logo, navigatie, app-info en refresh."""
    with st.sidebar:
        st.markdown("## 🛡️ RiskManager")
        st.markdown("*IT Risk Management Demo*")
        st.divider()

        nav_pages = {
            "Dashboard": "🏠",
            "Risico's": "⚠️",
            "Settings": "⚙️",
        }
        for page, icon in nav_pages.items():
            is_active = st.session_state.get("current_page", "Dashboard") == page
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"{icon} {page}", key=f"nav_{page}", type=btn_type, use_container_width=True):
                _set_page(page)

        st.divider()

        render_card(
            title="App info",
            body="v1.0.0 • Streamlit UX demo<br>Componenten: Fase A design system",
            variant="outlined",
            key="sidebar_app_info",
        )

        if render_button("🔄 Refresh", variant="secondary", key="btn_refresh"):
            show_spinner("Data verversen...")
            show_notify("Dashboard data ververst", kind="success")


# ---------------------------------------------------------------------------
# Dashboard pagina
# ---------------------------------------------------------------------------

def _render_dashboard_page() -> None:
    """Render het Dashboard met metrics, status-distributie en quick actions."""
    st.markdown("# Dashboard")
    render_alert("Welkom terug. Hier is het overzicht van de huidige risico's en acties.", kind="info")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Totaal risico's", METRICS["totaal_risicos"], key="metric_total")
    with col2:
        render_metric_card("Critical", METRICS["critical"], delta="+2 deze week", key="metric_critical")
    with col3:
        render_metric_card("Open acties", METRICS["open_acties"], key="metric_open")
    with col4:
        # Iets relevants: gesloten acties / voortgang
        voortgang = _percentage(METRICS["gesloten_acties"], METRICS["totaal_risicos"])
        render_metric_card("Doorloopgraad", f"{voortgang}%", key="metric_progress")

    st.divider()

    col_left, col_right = st.columns([2, 3])
    with col_left:
        render_card(title="Status distributie", variant="outlined", key="dist_card")
        total = sum(METRICS[level] for level in LEVEL_ORDER)
        for level in LEVEL_ORDER:
            count = METRICS[level]
            pct = _percentage(count, total)
            label = f"{_capitalize_label(level)} ({count})"
            st.markdown(f"{render_badge(_capitalize_label(level), LEVEL_BADGE_MAP[level])} {label}", unsafe_allow_html=True)
            st.progress(pct / 100, text=f"{pct}%")

    with col_right:
        render_card(title="Recente risico's", variant="interactive", key="recent_card")
        recent = sorted(RISICOS, key=lambda r: r["datum"], reverse=True)[:3]
        for risico in recent:
            level_variant = LEVEL_BADGE_MAP.get(risico["level"], "default")
            status_variant = STATUS_BADGE_MAP.get(risico["status"], "default")
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--color-border);">
                    <div>
                        <strong>{risico['titel']}</strong>
                        <div style="color:var(--color-text-muted); font-size:0.8rem;">{risico['eigenaar']} • {risico['datum']}</div>
                    </div>
                    <div>{render_badge(_capitalize_label(risico['level']), level_variant)} {render_badge(_capitalize_label(risico['status']), status_variant)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    render_card(title="Quick actions", variant="default", key="quick_card")
    qa_col1, qa_col2, qa_col3 = st.columns(3)
    with qa_col1:
        if render_button("+ Nieuw risico", variant="primary", key="qa_new"):
            _set_page("Risico's")
    with qa_col2:
        if render_button("Export", variant="secondary", icon="📥", key="qa_export"):
            show_spinner("Exporteren...")
            show_notify("Export gegenereerd", kind="success")
    with qa_col3:
        if render_button("Notificaties", variant="ghost", icon="🔔", key="qa_notify"):
            show_notify("Geen nieuwe notificaties", kind="info")


# ---------------------------------------------------------------------------
# Risico's pagina
# ---------------------------------------------------------------------------

def _render_risks_page() -> None:
    """Render de Risico's pagina met filters, zoeken en risico cards."""
    st.markdown("# Risico's")
    st.markdown("Beheer en monitor alle geregistreerde IT-risico's.")

    # State voor filter en zoekterm
    if "risk_filter" not in st.session_state:
        st.session_state.risk_filter = "Alle"
    if "risk_search" not in st.session_state:
        st.session_state.risk_search = ""

    # Alerts afhankelijk van data
    critical_count = sum(1 for r in RISICOS if r["level"] == "critical")
    closed_count = sum(1 for r in RISICOS if r["status"] == "closed")
    if critical_count:
        render_alert(f"Let op: {critical_count} critical risico('s) vereisen directe aandacht.", kind="warning")
    if closed_count:
        render_alert(f"{closed_count} risico('s) zijn succesvol gesloten.", kind="success")

    st.divider()

    # Filter bar
    filter_options = ["Alle", "Open", "In Progress", "Closed"]
    cols = st.columns(len(filter_options))
    for idx, option in enumerate(filter_options):
        is_active = st.session_state.risk_filter == option
        btn_type = "primary" if is_active else "secondary"
        if cols[idx].button(option, key=f"filter_{option}", type=btn_type, use_container_width=True):
            st.session_state.risk_filter = option
            _rerun()

    search = st.text_input("🔍 Zoek risico's...", value=st.session_state.risk_search, key="risk_search_input")
    st.session_state.risk_search = search

    # Filter logica
    def _matches_filter(risico: dict[str, Any]) -> bool:
        selected = st.session_state.risk_filter
        if selected == "Alle":
            return True
        return risico["status"].lower() == selected.lower().replace(" ", "_")

    filtered = [
        r for r in RISICOS
        if _matches_filter(r)
        and (
            not search
            or search.lower() in r["titel"].lower()
            or search.lower() in r["beschrijving"].lower()
            or search.lower() in r["eigenaar"].lower()
        )
    ]

    if not filtered:
        render_alert("Geen risico's gevonden voor de huidige filter/zoekopdracht.", kind="info")

    st.markdown(f"*{len(filtered)} risico('s) gevonden*")

    # Risico cards grid (2 kolommen)
    for idx in range(0, len(filtered), 2):
        row_cards = filtered[idx : idx + 2]
        row_cols = st.columns(len(row_cards))
        for col, risico in zip(row_cols, row_cards):
            with col:
                level_variant = LEVEL_BADGE_MAP.get(risico["level"], "default")
                status_variant = STATUS_BADGE_MAP.get(risico["status"], "default")

                header = f"""
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:600;">{risico['titel']}</span>
                    {render_badge(_capitalize_label(risico['level']), level_variant)}
                </div>
                """
                body = f"""
                <p>{risico['beschrijving']}</p>
                <div style="font-size:0.85rem; color:var(--color-text-muted);">
                    Eigenaar: {risico['eigenaar']}<br>Datum: {risico['datum']}
                </div>
                """
                render_card(
                    title=header,
                    body=body,
                    variant="interactive",
                    key=f"risk_card_{risico['id']}",
                )

                footer_cols = st.columns([1, 1, 1])
                with footer_cols[0]:
                    st.markdown(render_badge(_capitalize_label(risico["status"]), status_variant), unsafe_allow_html=True)
                with footer_cols[1]:
                    if render_button("Bekijk", variant="secondary", key=f"view_{risico['id']}"):
                        render_alert(f"Risico #{risico['id']} - {risico['titel']}: {risico['beschrijving']}", kind="info")
                with footer_cols[2]:
                    if render_button("Escaleer", variant="danger", key=f"esc_{risico['id']}"):
                        show_spinner("Escalatie versturen...")
                        show_notify(f"Risico #{risico['id']} geëscaleerd", kind="warning")


# ---------------------------------------------------------------------------
# Settings pagina
# ---------------------------------------------------------------------------

def _render_settings_page() -> None:
    """Render de Settings pagina met gebruikers-, notificatie-, thema- en danger-zone cards."""
    st.markdown("# Instellingen")
    render_alert("Hier kun je je voorkeuren en app-instellingen beheren.", kind="info")

    col_left, col_right = st.columns(2)

    with col_left:
        render_card(title="Gebruikersinstellingen", variant="outlined", key="user_card")
        name = st.text_input("Naam", value="Risico Beheerder", key="settings_name")
        email = st.text_input("E-mail", value="risico@voorbeeld.nl", key="settings_email")
        role = st.selectbox("Rol", ["Beheerder", "Analyst", "Lezer"], key="settings_role")

        render_card(title="Notificatie-instellingen", variant="default", key="notif_card")
        st.checkbox("E-mail notificaties", value=True, key="settings_email_notif")
        st.checkbox("Push notificaties", value=False, key="settings_push_notif")
        st.checkbox("Critical alerts", value=True, key="settings_critical_notif")

    with col_right:
        render_card(title="Thema", variant="outlined", key="theme_card")
        theme_cols = st.columns(2)
        with theme_cols[0]:
            if render_button("🌙 Donker", variant="primary", key="theme_dark"):
                show_notify("Donker thema actief", kind="info")
        with theme_cols[1]:
            if render_button("☀️ Licht", variant="secondary", key="theme_light"):
                show_notify("Licht thema gedemonstreerd", kind="info")

        render_card(
            title="DANGER ZONE",
            body="Deze acties zijn destructief en niet ongedaan te maken.",
            variant="outlined",
            accent="danger",
            key="danger_card",
        )
        if render_button("🗑️ Reset demo data", variant="danger", key="danger_reset"):
            show_spinner("Resetten...")
            render_alert("Demo data is gereset (simulatie).", kind="error")
            show_notify("Demo data gereset", kind="error")
        if render_button("Verwijder account", variant="danger", ghost=True, key="danger_delete"):
            render_alert("Account verwijderen is niet toegestaan in demo modus.", kind="error")

    st.divider()
    if render_button("💾 Instellingen opslaan", variant="primary", key="settings_save"):
        show_spinner("Opslaan...")
        render_alert(f"Instellingen opgeslagen voor {name} ({email}).", kind="success")
        show_notify("Instellingen opgeslagen", kind="success")


# ---------------------------------------------------------------------------
# Hoofd app
# ---------------------------------------------------------------------------

def main() -> None:
    """Startpunt van de IT Risk Management demo app."""
    inject_design_system()  # MOET als eerste worden aangeroepen

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    _render_sidebar()

    current_page = st.session_state.current_page
    if current_page == "Dashboard":
        _render_dashboard_page()
    elif current_page == "Risico's":
        _render_risks_page()
    elif current_page == "Settings":
        _render_settings_page()
    else:
        st.error(f"Onbekende pagina: {current_page}")


if __name__ == "__main__":
    main()
