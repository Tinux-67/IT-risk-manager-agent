"""Sanity-test pagina voor Fase A componenten.

Rendert elk component uit de IT Risk Manager Agent UI-bibliotheek één keer,
zodat visuele regressies handmatig kunnen worden gecontroleerd via::

    streamlit run tests/test_fase_a_components.py
"""

import streamlit as st

from components.ui import inject_design_system
from components.ui.alerts import Alert
from components.ui.badges import Badge
from components.ui.buttons import (
    DangerButton,
    GhostButton,
    PrimaryButton,
    SecondaryButton,
)
from components.ui.cards import Card, MetricCard, RiskCard
from components.ui.feedback import (
    show_error,
    show_info,
    show_spinner,
    show_success,
    show_toast,
    show_warning,
)

st.set_page_config(
    page_title="Fase A Component Sanity Test",
    page_icon="🧪",
    layout="wide",
)

inject_design_system()

st.title("Fase A — IT Risk Manager Agent componenten")
st.caption("Visuele sanity-check voor het nieuwe design system.")

# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------
with Card("Buttons"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        clicked_primary = PrimaryButton("Primary", key="btn_primary")
        st.write("Geklikt:", clicked_primary)
    with col2:
        clicked_secondary = SecondaryButton("Secondary", key="btn_secondary")
        st.write("Geklikt:", clicked_secondary)
    with col3:
        clicked_danger = DangerButton("Danger", key="btn_danger")
        st.write("Geklikt:", clicked_danger)
    with col4:
        clicked_ghost = GhostButton("Ghost", key="btn_ghost")
        st.write("Geklikt:", clicked_ghost)

    st.divider()
    PrimaryButton("Volledige breedte", key="btn_full", full_width=True, icon="🚀")
    SecondaryButton("Gedisabled", key="btn_disabled", disabled=True)

# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------
with Card("Cards"):
    col1, col2 = st.columns(2)
    with col1:
        MetricCard(label="Openstaande risico's", value=12, delta="+3 sinds vorige maand")
    with col2:
        with RiskCard(
            "Ongeautoriseerde toegang",
            level="critical",
            description="Detectie van inlogpogingen vanuit niet-toegestane regio's.",
            key="risk_critical",
        ):
            st.write("Actie vereist: toegangsregels herzien")

        with RiskCard(
            "Verlopen certificaat",
            level="medium",
            description="TLS-certificaat van API gateway verloopt over 14 dagen.",
            key="risk_medium",
        ):
            st.write("Actie vereist: certificaat verlengen")

# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------
with Card("Badges"):
    cols = st.columns(5)
    variants = ["success", "warning", "danger", "neutral", "info"]
    labels = ["Goedgekeurd", "Review", "Kritiek", "Concept", "Info"]
    for col, variant, label in zip(cols, variants, labels, strict=True):
        with col:
            Badge(label, variant=variant)

# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
with Card("Alerts"):
    Alert(
        "Er is een probleem opgetreden tijdens het synchroniseren van de risicodata.",
        variant="error",
        title="Synchronisatie mislukt",
    )
    Alert(
        "De laatste audit is succesvol afgerond.",
        variant="success",
        title="Audit voltooid",
    )
    Alert(
        "Gepland onderhoud staat gepland voor komende zaterdag 02:00 UTC.",
        variant="warning",
        title="Onderhoudsvenster",
    )
    Alert(
        "Nieuwe compliance-rapportage is beschikbaar.",
        variant="info",
    )

# ---------------------------------------------------------------------------
# Feedback helpers
# ---------------------------------------------------------------------------
with Card("Feedback helpers"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if PrimaryButton("Toon error", key="fb_error"):
            show_error("Verbinding met database mislukt.", title="Database fout")
    with col2:
        if PrimaryButton("Toon success", key="fb_success"):
            show_success("Rapport succesvol geëxporteerd.", title="Export voltooid")
    with col3:
        if PrimaryButton("Toon warning", key="fb_warning"):
            show_warning("Groot aantal openstaande items.", title="Attentie")
    with col4:
        if PrimaryButton("Toon info", key="fb_info"):
            show_info("Controle is gestart op de achtergrond.", title="Bezig")

    if PrimaryButton("Toon toast", key="fb_toast"):
        show_toast("Korte statusupdate", variant="info")

    if PrimaryButton("Toon spinner", key="fb_spinner"):
        with show_spinner("Risico's worden geanalyseerd..."):
            import time

            time.sleep(1)
        st.write("Analyse voltooid (gesimuleerd).")
