# =============================================================================
# Minimal UX Test — Fase A
# =============================================================================
import streamlit as st
from components.ui import inject_design_system

# VERPLICHT: Injecteer design system EERST
inject_design_system()

# Simpele test
st.title("🧪 UX Test — Fase A")

# Check of CSS werkt
st.markdown("""
<div style='background: #262730; padding: 20px; border-radius: 8px; margin: 20px 0;'>
    <h3 style='color: #FAFAFA;'>Als deze card donkergrijs is met witte tekst → CSS werkt! ✅</h3>
    <p style='color: #A0A0A0;'>Achtergrond: #262730 | Tekst: #FAFAFA</p>
</div>
""", unsafe_allow_html=True)

# Test button
st.header("Test Buttons")
col1, col2 = st.columns(2)

with col1:
    if st.button("Primary Button (moet blauw zijn)"):
        st.success("✅ Button werkt!")

with col2:
    if st.button("Danger Button (moet rood zijn)", key="btn2"):
        st.error("❌ Danger button geklikt!")

# Test badge
st.header("Test Badge")
st.markdown('<span class="badge badge-success" style="padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; text-transform: uppercase;">SUCCESS</span>', unsafe_allow_html=True)

st.info("💡 **Tip:** Druk Ctrl+Shift+R in je browser om cache te legen!")
