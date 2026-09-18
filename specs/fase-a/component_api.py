"""
IT Risk Manager Agent — Component API design (Fase A)
Pseudo-code / contracten; de Lead Dev implementeert deze signatures.
Alle componenten renderen via Streamlit + centrale CSS; geen inline styles.
"""

from collections.abc import Sequence
from typing import Literal

import streamlit as st


# ---------------------------------------------------------------------------
# Injectie helper
# ---------------------------------------------------------------------------
def inject_design_system() -> None:
    """Laadt assets/css/design_system.css één keer in de pagina."""
    ...


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------
Size = Literal["sm", "md", "lg"]
ButtonVariant = Literal["primary", "secondary", "danger", "ghost"]


def PrimaryButton(
    label: str,
    *,
    key: str | None = None,
    icon: str | None = None,
    size: Size = "md",
    disabled: bool = False,
    aria_label: str | None = None,
    full_width: bool = False,
) -> bool:
    """Rendert een primaire CTA-knop. Retourneert True indien geklikt."""
    ...


def SecondaryButton(
    label: str,
    *,
    key: str | None = None,
    icon: str | None = None,
    size: Size = "md",
    disabled: bool = False,
    aria_label: str | None = None,
    full_width: bool = False,
) -> bool:
    """Rendert een secundaire outline-knop."""
    ...


def DangerButton(
    label: str,
    *,
    key: str | None = None,
    icon: str | None = None,
    size: Size = "md",
    disabled: bool = False,
    aria_label: str | None = None,
    full_width: bool = False,
) -> bool:
    """Rendert een destructieve actie-knop."""
    ...


def GhostButton(
    label: str,
    *,
    key: str | None = None,
    icon: str | None = None,
    size: Size = "md",
    disabled: bool = False,
    aria_label: str | None = None,
    full_width: bool = False,
) -> bool:
    """Rendert een subtiele knop zonder vulling."""
    ...


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------
RiskLevel = Literal["critical", "high", "medium", "low"]


def Card(
    title: str | None = None,
    *,
    key: str | None = None,
    children: Sequence[st.delta_generator.DeltaGenerator] | None = None,
) -> st.delta_generator.DeltaGenerator:
    """Generieke container met card-styling; retourneert container."""
    ...


def MetricCard(
    label: str,
    value: str | int | float,
    *,
    delta: str | None = None,
    delta_color: Literal["normal", "inverse", "off"] = "normal",
    key: str | None = None,
) -> st.delta_generator.DeltaGenerator:
    """KPI-kaart met uniforme stijl."""
    ...


def RiskCard(
    title: str,
    level: RiskLevel,
    *,
    description: str | None = None,
    key: str | None = None,
    children: Sequence[st.delta_generator.DeltaGenerator] | None = None,
) -> st.delta_generator.DeltaGenerator:
    """Kaart voor risico-items met gekleurde accentrand."""
    ...


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------
BadgeVariant = Literal["success", "warning", "danger", "neutral", "info"]


def Badge(
    label: str,
    *,
    variant: BadgeVariant = "neutral",
    icon: str | None = None,
    key: str | None = None,
) -> None:
    """Rendert een klein statuslabel."""
    ...


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
AlertVariant = Literal["error", "success", "warning", "info"]


def Alert(
    message: str,
    *,
    variant: AlertVariant = "info",
    title: str | None = None,
    icon: str | None = None,
    key: str | None = None,
) -> None:
    """Rendert een toegankelijke alert met ARIA role='alert'."""
    ...


# ---------------------------------------------------------------------------
# Feedback helper
# ---------------------------------------------------------------------------
def show_spinner(
    text: str = "Laden...",
    *,
    delay_ms: int = 0,
) -> st.spinner:
    """Uniforme spinner; optioneel na delay."""
    ...


def show_toast(
    message: str,
    *,
    variant: AlertVariant = "info",
    duration: int = 4,
    icon: str | None = None,
) -> None:
    """Korte melding met consistent icoon en duur."""
    ...


def show_error(
    message: str,
    *,
    title: str | None = None,
    icon: str = "🛑",
) -> None:
    """Foutmelding met icon en optionele titel."""
    ...


def show_success(
    message: str,
    *,
    title: str | None = None,
    icon: str = "✅",
) -> None:
    """Succesmelding met icon en optionele titel."""
    ...


def show_warning(
    message: str,
    *,
    title: str | None = None,
    icon: str = "⚠️",
) -> None:
    """Waarschuwingsmelding met icon en optionele titel."""
    ...


def show_info(
    message: str,
    *,
    title: str | None = None,
    icon: str = "ℹ️",
) -> None:
    """Informatieve melding met icon en optionele titel."""
    ...
