"""IT Risk Manager Agent — UI component library (Fase A).

Deze package bundelt herbruikbare Streamlit componenten en een helper om het
centrale design system één keer per pagina in te laden.
"""

from pathlib import Path

import streamlit as st

__all__ = ["inject_design_system"]

_CSS_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "css" / "design_system.css"
_CSS_CACHE_KEY = "_itrm_design_system_injected"


def inject_design_system() -> None:
    """Laadt ``assets/css/design_system.css`` één keer in de huidige pagina.

    Dubbele injectie wordt voorkomen via een cache-sleutel in
    ``st.session_state``. Het stylesheet wordt ingevoegd als ``<style>``-blok
    in de ``<head>`` van de pagina.
    """
    if st.session_state.get(_CSS_CACHE_KEY):
        return

    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.session_state[_CSS_CACHE_KEY] = True
