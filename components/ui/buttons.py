"""Button componenten voor het IT Risk Manager Agent design system.

Elke button-helper rendert via ``st.button`` en retourneert ``True`` indien de
gebruiker op de knop heeft geklikt tijdens dit rerun-cyclus. De visuele
varianten worden gerealiseerd door de Streamlit-button in een wrapper-div met
de juiste CSS-class te plaatsen; ``design_system.css`` zorgt voor de styling.
"""

from typing import Literal

import streamlit as st

Size = Literal["sm", "md", "lg"]
ButtonVariant = Literal["primary", "secondary", "danger", "ghost"]

_VARIANT_CLASS = {
    "primary": "itrm-btn-primary",
    "secondary": "itrm-btn-secondary",
    "danger": "itrm-btn-danger",
    "ghost": "itrm-btn-ghost",
}

_SIZE_CLASS = {
    "sm": "itrm-btn-sm",
    "md": "itrm-btn-md",
    "lg": "itrm-btn-lg",
}


def _render_button(
    variant: ButtonVariant,
    label: str,
    *,
    key: str | None,
    icon: str | None,
    size: Size,
    disabled: bool,
    aria_label: str | None,
    full_width: bool,
) -> bool:
    """Interne helper die een gestijlde Streamlit-button rendert."""
    container_class = f"{_VARIANT_CLASS[variant]} {_SIZE_CLASS[size]}"
    effective_label = f"{icon} {label}" if icon else label
    # Een lege div als eerste child voorziet de container van de juiste class.
    # De button komt als tweede child in dezelfde container, waardoor
    # ``.itrm-btn-* > button`` in CSS correct matcht.
    st.markdown(
        f"<div class='{container_class}' aria-label='{aria_label or label}' style='display:block;'>"
        f"<span style='display:none;'></span>",
        unsafe_allow_html=True,
    )
    try:
        clicked = st.button(
            effective_label,
            key=key,
            disabled=disabled,
            use_container_width=full_width,
        )
    finally:
        st.markdown("</div>", unsafe_allow_html=True)
    return clicked


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
    """Rendert een primaire CTA-knop. Retourneert ``True`` indien geklikt."""
    return _render_button(
        "primary",
        label,
        key=key,
        icon=icon,
        size=size,
        disabled=disabled,
        aria_label=aria_label,
        full_width=full_width,
    )


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
    return _render_button(
        "secondary",
        label,
        key=key,
        icon=icon,
        size=size,
        disabled=disabled,
        aria_label=aria_label,
        full_width=full_width,
    )


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
    return _render_button(
        "danger",
        label,
        key=key,
        icon=icon,
        size=size,
        disabled=disabled,
        aria_label=aria_label,
        full_width=full_width,
    )


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
    return _render_button(
        "ghost",
        label,
        key=key,
        icon=icon,
        size=size,
        disabled=disabled,
        aria_label=aria_label,
        full_width=full_width,
    )
