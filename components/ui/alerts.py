"""Alert componenten voor het IT Risk Manager Agent design system."""

from typing import Literal

import streamlit as st

AlertVariant = Literal["error", "success", "warning", "info"]

_DEFAULT_ICON = {
    "error": "🛑",
    "success": "✅",
    "warning": "⚠️",
    "info": "ℹ️",
}

_ROLE = {
    "error": "alert",
    "success": "status",
    "warning": "alert",
    "info": "status",
}


def Alert(
    message: str,
    *,
    variant: AlertVariant = "info",
    title: str | None = None,
    icon: str | None = None,
    key: str | None = None,
) -> None:
    """Rendert een toegankelijke alert met ARIA role='alert'.

    Parameters
    ----------
    message:
        De body-tekst van de alert.
    variant:
        Visuele variant (error, success, warning, info).
    title:
        Optionele titelregel boven de message.
    icon:
        Optioneel emoji/icoon; standaard afhankelijk van variant.
    key:
        Optionele Streamlit-sleutel voor reproduceerbare widgets.
    """
    chosen_icon = icon if icon is not None else _DEFAULT_ICON[variant]
    role = _ROLE[variant]
    aria_key = f" itrm-alert-{key}" if key else ""

    title_html = f"<strong class='itrm-alert__title'>{title}</strong><br>" if title else ""

    html = f"""
    <div class="itrm-alert itrm-alert--{variant}{aria_key}" role="{role}" aria-live="polite">
        <span class="itrm-alert__icon" aria-hidden="true">{chosen_icon}</span>
        <div class="itrm-alert__content">
            {title_html}
            {message}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
