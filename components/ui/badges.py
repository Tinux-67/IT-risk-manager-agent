"""Badge componenten voor het IT Risk Manager Agent design system."""

from typing import Literal

import streamlit as st

BadgeVariant = Literal["success", "warning", "danger", "neutral", "info"]

_DEFAULT_ICON = {
    "success": "✅",
    "warning": "⚠️",
    "danger": "🛑",
    "neutral": "",
    "info": "ℹ️",
}


def Badge(
    label: str,
    *,
    variant: BadgeVariant = "neutral",
    icon: str | None = None,
    key: str | None = None,
) -> None:
    """Rendert een klein statuslabel.

    Parameters
    ----------
    label:
        De tekst van het badge.
    variant:
        Visuele variant (success, warning, danger, neutral, info).
    icon:
        Optioneel emoji/icoon dat voor de tekst wordt getoond.
    key:
        Optionele Streamlit-sleutel voor reproduceerbare widgets.
    """
    chosen_icon = icon if icon is not None else _DEFAULT_ICON.get(variant, "")
    content = f"{chosen_icon} {label}".strip()

    html = f"""
    <span class="badge badge-{variant}" key="{key or ''}">
        {content}
    </span>
    """
    st.markdown(html, unsafe_allow_html=True)
