# =============================================================================
# IT Risk Manager Agent — UX Fase A Component Test
# =============================================================================
# Gebruik deze pagina om alle Fase A componenten te testen.
# 
# Start met: streamlit run test_ux_fase_a.py
# =============================================================================

import streamlit as st
import time

# Importeer alle componenten
from components.ui import inject_design_system
from components.ui.buttons import PrimaryButton, SecondaryButton, DangerButton, GhostButton
from components.ui.cards import Card, MetricCard, RiskCard
from components.ui.badges import Badge
from components.ui.alerts import Alert
from components.ui.feedback import loading, notify

# VERPLICHT: Injecteer design system (één keer per pagina)
inject_design_system()

# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------
st.title("🧪 UX Fase A — Component Test")
st.write("Testpagina voor alle Fase A componenten")
st.info("Gebruik `Tab` om keyboard navigation te testen — focus rings moeten zichtbaar zijn.")

st.divider()

# -----------------------------------------------------------------------------
# 1. BUTTONS
# -----------------------------------------------------------------------------
st.header("1. Buttons — 4 Varianten")
st.write("Test alle button varianten met iconen en verschillende groottes.")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("Primary")
    if PrimaryButton("Primary", icon="🚀"):
        st.success("✅ Primary button geklikt!")
    if PrimaryButton("Small", size="sm"):
        st.toast("Small primary")
    if PrimaryButton("Large", size="lg"):
        st.toast("Large primary")

with col2:
    st.subheader("Secondary")
    if SecondaryButton("Secondary"):
        st.info("ℹ️ Secondary button geklikt!")
    if SecondaryButton("Small", size="sm"):
        st.toast("Small secondary")
    if SecondaryButton("Large", size="lg"):
        st.toast("Large secondary")

with col3:
    st.subheader("Danger")
    if DangerButton("Danger", icon="⚠️"):
        st.warning("⚠️ Danger button geklikt!")
    if DangerButton("Small", size="sm"):
        st.toast("Small danger")
    if DangerButton("Large", size="lg"):
        st.toast("Large danger")

with col4:
    st.subheader("Ghost")
    if GhostButton("Ghost"):
        st.toast("👻 Ghost button geklikt!")
    if GhostButton("Small", size="sm"):
        st.toast("Small ghost")
    if GhostButton("Large", size="lg"):
        st.toast("Large ghost")

st.divider()

# -----------------------------------------------------------------------------
# 2. CARDS
# -----------------------------------------------------------------------------
st.header("2. Cards — 3 Types")

st.subheader("Metric Card")
col1, col2, col3 = st.columns(3)
with col1:
    MetricCard("Totaal Risico's", 42, delta="+3 deze week")
with col2:
    MetricCard("Critical", 5, delta="+1 vandaag")
with col3:
    MetricCard("Open Acties", 12, delta="-2 voltooid")

st.subheader("Risk Cards")
with RiskCard("Datalek risico", level="critical", description="Gevoelige data onbeschermd"):
    Badge("CRITICAL", variant="danger")
    st.write("Dit risico vereist onmiddellijke actie.")
    if DangerButton("Verwijder Risico", icon="🗑️", size="sm"):
        st.success("Risico verwijderd!")

with RiskCard("Compliance risico", level="high", description="AVG niet nageleefd"):
    Badge("HIGH", variant="warning")
    st.write("Audit staat gepland voor volgende week.")
    if SecondaryButton("Plan Audit", size="sm"):
        st.info("Audit ingepland!")

with RiskCard("Operationeel risico", level="medium", description="Systeem downtime"):
    Badge("MEDIUM", variant="neutral")
    st.write("Back-up procedure getest.")

with RiskCard("Financieel risico", level="low", description="Budget overschrijding"):
    Badge("LOW", variant="success")
    st.write("Budget binnen marge.")

st.divider()

# -----------------------------------------------------------------------------
# 3. BADGES
# -----------------------------------------------------------------------------
st.header("3. Badges — 5 Varianten")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    Badge("SUCCESS", variant="success")
    st.caption("success")

with col2:
    Badge("WARNING", variant="warning")
    st.caption("warning")

with col3:
    Badge("DANGER", variant="danger")
    st.caption("danger")

with col4:
    Badge("NEUTRAL", variant="neutral")
    st.caption("neutral")

with col5:
    Badge("INFO", variant="info")
    st.caption("info")

st.divider()

# -----------------------------------------------------------------------------
# 4. ALERTS
# -----------------------------------------------------------------------------
st.header("4. Alerts — 4 Types")

Alert("Dit is een error melding — actie vereist!", variant="error")
Alert("Dit is een success melding — voltooid!", variant="success")
Alert("Dit is een warning melding — let op!", variant="warning")
Alert("Dit is een info melding — ter kennis.", variant="info")

st.divider()

# -----------------------------------------------------------------------------
# 5. FEEDBACK
# -----------------------------------------------------------------------------
st.header("5. Feedback — Loading & Notifications")

st.subheader("Loading State")
if st.checkbox("Toon loading state (simuleer 2 seconden wachttijd)"):
    with loading("Bezig met laden van data..."):
        time.sleep(2)
    st.success("✅ Laden voltooid!")

st.subheader("Notificaties")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if PrimaryButton("Success", size="sm"):
        notify("success", "✅ Actie voltooid!")

with col2:
    if SecondaryButton("Error", size="sm"):
        notify("error", "❌ Er ging iets mis!")

with col3:
    if SecondaryButton("Warning", size="sm"):
        notify("warning", "⚠️ Let op — controleer de invoer!")

with col4:
    if SecondaryButton("Info", size="sm"):
        notify("info", "ℹ️ Nieuwe update beschikbaar.")

st.divider()

# -----------------------------------------------------------------------------
# 6. ACCESSIBILITY TEST
# -----------------------------------------------------------------------------
st.header("6. Accessibility — Keyboard Navigation")

st.write("**Test instructies:**")
st.write("1. Druk op `Tab` om door de pagina te navigeren")
st.write("2. Focus rings moeten zichtbaar zijn (blauwe gloed)")
st.write("3. Druk `Enter` om gekozen element te activeren")
st.write("4. Gebruik `Escape` om dialogs te sluiten")

st.write("**Test knoppen:**")
col1, col2, col3 = st.columns(3)
with col1:
    PrimaryButton("Tab naar mij", aria_label="Test knop 1")
with col2:
    SecondaryButton("En dan naar mij", aria_label="Test knop 2")
with col3:
    DangerButton("Laatste knop", aria_label="Test knop 3")

st.info("🎯 **Doel:** Alle knoppen moeten bereikbaar zijn met alleen keyboard.")

st.divider()

# -----------------------------------------------------------------------------
# 7. RESPONSIVE TEST
# -----------------------------------------------------------------------------
st.header("7. Responsive — Browser Formaat")

st.write("**Test instructies:**")
st.write("1. Verklein browser naar 320px (mobile)")
st.write("2. Check op 768px (tablet)")
st.write("3. Check op 1440px (desktop)")
st.write("4. Componenten moeten correct schalen")

st.subheader("Test Layout — 2 Kolommen")
col1, col2 = st.columns(2)
with col1:
    with Card("Linker Card"):
        st.write("Deze card staat in de linker kolom.")
        MetricCard("Links", "50%")
with col2:
    with Card("Rechter Card"):
        st.write("Deze card staat in de rechter kolom.")
        MetricCard("Rechts", "50%")

st.write("**Verwacht gedrag:**")
st.write("- **Desktop (>1024px):** 2 kolommen naast elkaar")
st.write("- **Tablet (768px-1024px):** 2 kolommen, smaller")
st.write("- **Mobile (<768px):** Kolommen stacken verticaal")

st.divider()

# -----------------------------------------------------------------------------
# 8. CONTRAST CHECK
# -----------------------------------------------------------------------------
st.header("8. WCAG Contrast — Handmatige Check")

st.write("**Gebruik een van deze tools:**")
st.write("- Browser DevTools → Accessibility → Contrast checker")
st.write("- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/")
st.write("- axe DevTools extensie (Chrome/Firefox)")

st.write("**Te checken combinaties:**")
st.code("""
- Tekst (#FAFAFA) op achtergrond (#0E1117) → moet ≥ 4.5:1 zijn
- Primary button tekst (#FFFFFF) op #1A5FB4 → moet ≥ 4.5:1 zijn
- Badge tekst op achtergrond → moet ≥ 4.5:1 zijn
""")

st.info("Alle kleuren in `design_system.css` zijn getest op WCAG 2.1 AA compliance.")

# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------
st.divider()
st.write("✅ **Test voltooid!** Noteer eventuele issues en meld ze aan de Forge.")
st.write("**Bestand:** `test_ux_fase_a.py`")
