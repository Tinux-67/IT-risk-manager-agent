"""
Acceptatietests voor de ITRM-clean architectuur.

Doelstellingen (gekoppeld aan de drie bugs):
  AT-1: geen "None"-output (componenten zijn pure functies)
  AT-2: geen ruwe HTML als tekst (één renderpad met unsafe_allow_html)
  AT-3: geen verticale tekst (geen writing-mode / rotate in geladen CSS)

Uitvoeren:  pytest test_acceptance.py -v
"""

import re
import os
import inspect
import streamlit as st

from demo_app import (
    badge, alert, metric_card, risk_card, html, CLEAN_CSS,
    RISICO_DATA, _variant_for,
)

# ===========================================================================
# AT-1 — Geen "None"-output (Bug #1)
# ===========================================================================

def test_at1_componenten_retourneren_string_niet_none():
    """Elke component moet een niet-lege string retourneren — nooit None."""
    resultaten = [
        badge("CRITICAL", variant="danger"),
        alert("Testbericht", variant="info"),
        metric_card("Totaal", 42),
        risk_card(
            titel="Datalek", ernst="kritiek", aantal=5,
            eigenaar="Security Team", status="Open",
            beschrijving="Testbeschrijving.",
        ),
    ]
    for resultaat in resultaten:
        assert resultaat is not None, \
            "Component retourneerde None — Bug #1-structuur aanwezig"
        assert isinstance(resultaat, str), \
            f"Component retourneerde {type(resultaat)} i.p.v. str"
        assert len(resultaat.strip()) > 0, "Component retourneerde lege string"


def test_at1_componenten_bevatten_geen_streamlit_calls():
    """Pure functies: géén st.*()-aanroepen binnen component-body's."""
    componenten = [badge, alert, metric_card, risk_card]
    verboden_patronen = re.compile(r"\bst\.[a-z_]+\s*\(")
    for component in componenten:
        bron = inspect.getsource(component)
        matches = verboden_patronen.findall(bron)
        assert not matches, (
            f"'{component.__name__}' bevat Streamlit-aanroepen "
            f"({matches}) — side-effect rendering is teruggekeerd"
        )


def test_at1_geen_string_none_in_output():
    """De letterlijke tekst 'None' mag nergens als los element voorkomen."""
    html_output = risk_card(
        titel="Datalek", ernst="kritiek", aantal=5,
        eigenaar="Security Team", status="Open",
        beschrijving="Testbeschrijving.",
    )
    # "None" als zelfstandig tekstfragment tussen tags (>None<) of vóór tags
    patroon = re.compile(r"(>|^|\s)None(\s|<|$)")
    assert not patroon.search(html_output), \
        "Letterlijke 'None' gevonden in gerenderde HTML"


def test_at1_statusdistributie_zonder_none():
    """
    De statusdistributie mag nergens 'None' tonen (oude symptoomlocatie).
    
    Dit is de regressiewacht voor "None Critical (5)" en "None None (12)".
    Test dat de Counter-aggregatie correct werkt en badge() strings retourneert.
    """
    from collections import Counter
    
    distributie = Counter(r["ernst"] for r in RISICO_DATA)
    
    for ernst, aantal in distributie.items():
        regel = f"{badge(ernst.capitalize(), variant=_variant_for(ernst))} ({aantal})"
        
        # AT-1: geen "None"-fragment
        assert not re.search(r"(>|^|\s)None(\s|<|$)", regel), \
            f"'None' gevonden in distributie-regel: {regel}"
        
        # AT-2: de telling is een integer, geen "None None"-dubbeling
        assert isinstance(aantal, int), \
            f"Aantal is geen integer: {type(aantal)}"
        
        # Structuur: badge-string gevolgd door een getal tussen haakjes
        assert regel.endswith(f"({aantal})"), \
            f"Regel eindigt niet correct: {regel}"
        assert regel.startswith("<span class='badge"), \
            f"Regel begint niet met badge: {regel}"


# ===========================================================================
# AT-2 — Geen ruwe HTML als tekst (Bug #2)
# ===========================================================================

def test_at2_data_is_plat_zonder_html_tags():
    """Datavelden mogen geen markup bevatten — markup hoort bij componenten."""
    tag_patroon = re.compile(r"<[^>]+>")
    for risico in RISICO_DATA:
        for veld, waarde in risico.items():
            assert not tag_patroon.search(str(waarde)), (
                f"HTML-tag gevonden in dataveld '{veld}': {waarde[:50]}... "
                "— beschrijf data plat en verplaats markup naar het component"
            )


def test_at2_renderpad_gebruikt_unsafe_allow_html():
    """De enige renderfunctie moet unsafe_allow_html=True doorgeven."""
    bron = inspect.getsource(html)
    assert "unsafe_allow_html" in bron, (
        "html() mist unsafe_allow_html — HTML zal ge-escapet worden"
    )


# ===========================================================================
# AT-3 — Geen verticale tekst (Bug #3)
# ===========================================================================

def test_at3_css_bevat_geen_verticale_regels():
    """writing-mode en rotate mogen niet in de geladen CSS voorkomen."""
    verboden = ["writing-mode", "rotate("]
    for regel in verboden:
        assert regel not in CLEAN_CSS, (
            f"'{regel}' gevonden in CSS — dit veroorzaakt verticale tekst"
        )


def test_at3_design_system_css_controleren():
    """
    Zelfde controle op het externe design_system.css, indien aanwezig.
    Verificatie dat uw bestaande CSS niet opnieuw Bug #3 introduceert.
    """
    css_pad = "assets/css/design_system.css"
    if not os.path.exists(css_pad):
        return  # bestand niet gevonden in werkmap — sla controle over
    with open(css_pad, encoding="utf-8") as bestand:
        inhoud = bestand.read()
    for regel in ["writing-mode", "rotate("]:
        assert regel not in inhoud, (
            f"'{regel}' gevonden in {css_pad} — "
            "verwijder deze regel of overbrug het bestand met CLEAN_CSS"
        )


# ===========================================================================
# Integratie — end-to-end render van een volledige pagina
# ===========================================================================

def test_integratie_volledige_risicopagina_zonder_defecten():
    """Simuleer de pagina-output en verifieer álle acceptatiecriteria tegelijk."""
    pagina_html = "".join(
        risk_card(
            titel=r["titel"],
            ernst=r["ernst"],
            aantal=r.get("aantal", 1),
            eigenaar=r.get("eigenaar", "Onbekend"),
            status=r.get("status", "Open"),
            beschrijving=r["beschrijving"],
        )
        for r in RISICO_DATA
    )

    # AT-1: geen "None"-fragmenten
    assert not re.search(r"(>|^|\s)None(\s|<|$)", pagina_html)
    # AT-2: geen ge-escapete tags als tekst (&lt;div&gt;)
    assert "&lt;" not in pagina_html and "&gt;" not in pagina_html
    # AT-3: titels zijn horizontaal (geen CSS-verticale regels toegepast)
    assert "writing-mode" not in pagina_html + CLEAN_CSS
