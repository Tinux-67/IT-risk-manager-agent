import streamlit as st
from pathlib import Path

st.title("CSS Test")

css_path = Path("assets/css/design_system.css")

if css_path.exists():
    css = css_path.read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.success("CSS geladen!")
else:
    st.error("CSS niet gevonden!")

st.markdown("<h1 style='color: #4C9AFF;'>Blauwe tekst = CSS werkt</h1>", unsafe_allow_html=True)
