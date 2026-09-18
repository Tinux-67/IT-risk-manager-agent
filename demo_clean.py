"""
ITRM Demo Clean — Schone demonstratie van de Fase A component library.

Architectuur:
- Elke component retourneert een HTML-string (pure functies, geen side-effects).
- Rendering gebeurt uitsluitend via html() met unsafe_allow_html=True.
- Geen 'None'-output: componenten worden nooit rechtstreeks in een f-string
  als streamlit-element gebruikt.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Renderhulp — het ENIGE punt waar Streamlit-output plaatsvindt
# ---------------------------------------------------------------------------

def html(content: str) -> None:
    """Render een HTML-string veilig in Streamlit."""
    st.markdown(content, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Componenten — retourneren altijd een string, printen nooit zelf
# ---------------------------------------------------------------------------

def metric_card(title: str, value, delta: str = "", icon: str = "") -> str:
    """Genereer een metric card als HTML-string."""
    delta_html = (
        f"<span class='metric-delta'>{delta}</span>" if delta else ""
    )
    return f"""
    <div class="metric-card">
        <div class="metric-title">{icon} {title}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """


def badge(label: str, variant: str = "neutral") -> str:
    """Genereer een badge als HTML-string."""
    return f"<span class='badge badge-{variant}'>{label}</span>"


def alert(message: str, variant: str = "info") -> str:
    """Genereer een alert als HTML-string."""
    return f"<div class='alert alert-{variant}'>{message}</div>"


def risk_card(title: str, description: str,
              severity: str, owner: str, status: str) -> str:
    """Genereer een risico-card als HTML-string."""
    return f"""
    <div class="risk-card">
        <div class="risk-header">
            <h3 class="risk-title">{title}</h3>
            {badge(severity.upper(), variant=_variant_for(severity))}
        </div>
        <p class="risk-description">{description}</p>
        <div class="risk-footer">
            <span class="risk-meta">Eigenaar: {owner}</span>
            <span class="risk-meta">Status: {status}</span>
        </div>
    </div>
    """


def _variant_for(severity: str) -> str:
    """Map een ernst op een CSS-variant. Standaard is altijd gevuld."""
    mapping = {
        "kritiek": "danger",
        "critical": "danger",
        "hoog": "warning",
        "high": "warning",
        "middel": "info",
        "medium": "info",
        "laag": "success",
        "low": "success",
    }
    return mapping.get(severity.strip().lower(), "neutral")


# ---------------------------------------------------------------------------
# Benodigde CSS — expliciet horizontaal, minimaal, geen verticale regels
# ---------------------------------------------------------------------------

CLEAN_CSS = """
<style>
.metric-card {
    background: var(--color-bg-secondary, #161B22);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
}
.metric-title { font-size: 0.8rem; opacity: 0.8; }
.metric-value { font-size: 1.8rem; font-weight: bold; }

.badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-danger  { background: #DA3633; color: #FFF; }
.badge-warning { background: #D29922; color: #FFF; }
.badge-info    { background: #388BFD; color: #FFF; }
.badge-success { background: #2EA043; color: #FFF; }
.badge-neutral { background: #6E7681; color: #FFF; }

.alert {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
}
.alert-info    { background: rgba(56,139,253,0.15); border-left: 4px solid #388BFD; }
.alert-success { background: rgba(46,160,67,0.15); border-left: 4px solid #2EA043; }
.alert-warning { background: rgba(210,153,34,0.15); border-left: 4px solid #D29922; }
.alert-error   { background: rgba(218,54,51,0.15); border-left: 4px solid #DA3633; }

.risk-card {
    background: var(--color-bg-secondary, #161B22);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
}
.risk-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.risk-title { font-size: 1.1rem; margin: 0; }
.risk-description { font-size: 0.9rem; opacity: 0.9; }
.risk-footer {
    display: flex;
    gap: 1rem;
    font-size: 0.8rem;
    opacity: 0.7;
    margin-top: 0.5rem;
}
</style>
"""


# ---------------------------------------------------------------------------
# Demodata — platte strings, géén HTML in de data zelf
# ---------------------------------------------------------------------------

RISICO_DATA = [
    {
        "titel": "Datalek klantinformatie",
        "beschrijving": "Gevoelige persoonsgegevens onvoldoende versleuteld opgeslagen "
                        "in de primaire database.",
        "ernst": "kritiek",
        "eigenaar": "Security Team",
        "status": "Open",
    },
    {
        "titel": "Onvoldoende toegangscontrole",
        "beschrijving": "Medewerkers hebben breder toegangsrechten dan noodzakelijk "
                        "voor hun functie.",
        "ernst": "hoog",
        "eigenaar": "IAM Team",
        "status": "In behandeling",
    },
    {
        "titel": "Verouderde software versies",
        "beschrijving": "Drie kritieke servers draaien op niet-ondersteunde versies.",
        "ernst": "middel",
        "eigenaar": "Infrastructuur",
        "status": "Gepland",
    },
    {
        "titel": "Ontbrekende back-upprocedure",
        "beschrijving": "Back-ups worden niet periodiek getest op herstelbaarheid.",
        "ernst": "laag",
        "eigenaar": "Operations",
        "status": "Open",
    },
]


# ---------------------------------------------------------------------------
# Paginastructuur
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="ITRM Demo Clean", layout="wide")
    html(CLEAN_CSS)

    st.title("🛡️ IT Risk Management — Demo Clean")

    # --- Alert bovenaan ---
    html(alert(
        "Deze demo toont de Fase A componenten met een schone renderarchitectuur.",
        variant="info",
    ))

    # --- Metric cards in kolommen ---
    totaal = len(RISICO_DATA)
    kritiek = sum(1 for r in RISICO_DATA if r["ernst"] == "kritiek")

    cols = st.columns(4)
    with cols[0]:
        html(metric_card("Totaal risico's", totaal))
    with cols[1]:
        html(metric_card("Kritiek", kritiek, delta="→ prioriteit", icon="🔴"))
    with cols[2]:
        html(metric_card("Open", 3, icon="🔓"))
    with cols[3]:
        html(metric_card("Risicoscore", "71%", delta="↓ 4%", icon="📊"))

    st.divider()

    # --- Filter op ernst (werking van Streamlit zelf, geen custom HTML) ---
    ernsten = ["Alle"] + sorted({r["ernst"].capitalize() for r in RISICO_DATA})
    keuze = st.selectbox("Filter op ernst:", ernsten)

    st.subheader("Risico-overzicht")

    # --- Risico-cards ---
    for risico in RISICO_DATA:
        if keuze != "Alle" and risico["ernst"].capitalize() != keuze:
            continue
        html(risk_card(
            title=risico["titel"],
            description=risico["beschrijving"],
            severity=risico["ernst"],
            owner=risico["eigenaar"],
            status=risico["status"],
        ))

    # --- Afsluitende alert ---
    html(alert(
        "Alle componenten in deze pagina zijn pure functies die HTML-strings "
        "retourneren — de 'None'-bug kan hier structureel niet optreden.",
        variant="success",
    ))


if __name__ == "__main__":
    main()
