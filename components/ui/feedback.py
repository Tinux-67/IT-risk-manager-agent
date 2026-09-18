"""Feedback helpers voor het IT Risk Manager Agent design system.

Deze wrappers dwingen consistente defaults af voor Streamlit's
spinner/toast/meldingen, zodat meldingen altijd met een icon verschijnen en
toast-notificaties standaard 4 seconden zichtbaar zijn.
"""

from typing import Literal

import streamlit as st

AlertVariant = Literal["error", "success", "warning", "info"]

_TOAST_ICON = {
    "error": "🛑",
    "success": "✅",
    "warning": "⚠️",
    "info": "ℹ️",
}


def show_spinner(
    text: str = "Laden...",
    *,
    delay_ms: int = 0,
) -> st.spinner:
    """Uniforme spinner; optioneel na delay.

    Parameters
    ----------
    text:
        Tekst die naast de spinner wordt getoond.
    delay_ms:
        Niet ondersteund door ``st.spinner``; opgenomen voor API-compatibiliteit
        met het specificatiecontract. De waarde wordt genegeerd.

    Returns
    -------
    st.spinner
        Context manager voor de spinner.
    """
    return st.spinner(text)


def show_toast(
    message: str,
    *,
    variant: AlertVariant = "info",
    duration: int = 4,
    icon: str | None = None,
) -> None:
    """Korte melding met consistent icoon en duur.

    Parameters
    ----------
    message:
        De inhoud van de toast.
    variant:
        Visuele variant die het standaard-icoon bepaalt.
    duration:
        Aantal seconden dat de toast zichtbaar blijft (default 4).
    icon:
        Optioneel emoji/icoon; overschrijft het variant-icoon.
    """
    chosen_icon = icon if icon is not None else _TOAST_ICON[variant]
    st.toast(f"{chosen_icon} {message}", icon=chosen_icon, duration=duration)


def show_error(
    message: str,
    *,
    title: str | None = None,
    icon: str = "🛑",
) -> None:
    """Foutmelding met icon en optionele titel."""
    display = f"**{title}**\n\n{message}" if title else message
    st.error(f"{icon} {display}", icon=icon)


def show_success(
    message: str,
    *,
    title: str | None = None,
    icon: str = "✅",
) -> None:
    """Succesmelding met icon en optionele titel."""
    display = f"**{title}**\n\n{message}" if title else message
    st.success(f"{icon} {display}", icon=icon)


def show_warning(
    message: str,
    *,
    title: str | None = None,
    icon: str = "⚠️",
) -> None:
    """Waarschuwingsmelding met icon en optionele titel."""
    display = f"**{title}**\n\n{message}" if title else message
    st.warning(f"{icon} {display}", icon=icon)


def show_info(
    message: str,
    *,
    title: str | None = None,
    icon: str = "ℹ️",
) -> None:
    """Informatieve melding met icon en optionele titel."""
    display = f"**{title}**\n\n{message}" if title else message
    st.info(f"{icon} {display}", icon=icon)
