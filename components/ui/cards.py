"""Card componenten voor het IT Risk Manager Agent design system.

``Card`` en ``RiskCard`` retourneren een context manager; de inhoud wordt
tussen openende en sluitende HTML-tags gerenderd, zodat
``assets/css/design_system.css`` de juiste kaart-styling kan toepassen.

Voorbeeld:

    with Card("Samenvatting"):
        st.write("Inhoud van de kaart")
"""

from collections.abc import Sequence
from types import TracebackType
from typing import Literal, Self

import streamlit as st

RiskLevel = Literal["critical", "high", "medium", "low"]


class _CardContext:
    """Interne context manager die een kaart-wrapper opent en sluit."""

    def __init__(self, open_html: str, close_html: str = "</div>") -> None:
        self.open_html = open_html
        self.close_html = close_html

    def __enter__(self) -> Self:
        st.markdown(self.open_html, unsafe_allow_html=True)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        st.markdown(self.close_html, unsafe_allow_html=True)
        return False


def Card(
    title: str | None = None,
    *,
    key: str | None = None,
    children: Sequence[st.delta_generator.DeltaGenerator] | None = None,
) -> _CardContext:
    """Generieke container met card-styling.

    Retourneert een context manager. Gebruik als ``with Card("Titel"):``.

    Parameters
    ----------
    title:
        Optionele titel binnen de kaart.
    key:
        Niet-functioneel in deze implementatie; aanwezig voor API-compatibiliteit.
    children:
        Niet ondersteund; gebruik de ``with``-vorm voor inhoud.
    """
    title_html = f"<h3 class='itrm-card__title'>{title}</h3>" if title else ""
    open_html = f"<div class='itrm-card'>{title_html}"
    return _CardContext(open_html)


def MetricCard(
    label: str,
    value: str | int | float,
    *,
    delta: str | None = None,
    delta_color: Literal["normal", "inverse", "off"] = "normal",
    key: str | None = None,
) -> st.delta_generator.DeltaGenerator:
    """KPI-kaart met uniforme stijl.

    Rendert direct; retourneert de gebruikte Streamlit-container.
    """
    container = st.container(key=key) if key else st.container()
    with container:
        st.markdown("<div class='itrm-metric-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='itrm-metric-card__label'>{label}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='itrm-metric-card__value'>{value}</div>", unsafe_allow_html=True)
        if delta:
            st.markdown(f"<div class='itrm-metric-card__delta'>{delta}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    return container


def RiskCard(
    title: str,
    level: RiskLevel,
    *,
    description: str | None = None,
    key: str | None = None,
    children: Sequence[st.delta_generator.DeltaGenerator] | None = None,
) -> _CardContext:
    """Kaart voor risico-items met gekleurde accentrand.

    Gebruik als ``with RiskCard("Titel", level="critical"):``.
    """
    title_html = f"<h3 class='itrm-card__title'>{title}</h3>"
    description_html = f"<p class='itrm-card__body'>{description}</p>" if description else ""
    open_html = (
        f"<div class='itrm-risk-card itrm-risk-card--{level}'>"
        f"{title_html}{description_html}"
    )
    return _CardContext(open_html)
