"""
ITRM Demo App V2 — Complete migratie met schone architectuur.

Architectuur principes:
1. Data is plat — geen HTML in data velden
2. Componenten zijn pure functies — retourneren HTML strings
3. Één renderpad — html() met unsafe_allow_html=True
"""

import streamlit as st

# =============================================================================
# Renderhulp — het ENIGE punt waar Streamlit output plaatsvindt
# =============================================================================

def html(content: str) -> None:
    """Render een HTML-string veilig in Streamlit."""
    st.markdown(content, unsafe_allow_html=True)


# =============================================================================
# Componenten — retourneren altijd een string, printen nooit zelf
# =============================================================================

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
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
    }
    icon = icons.get(variant, "ℹ️")
    return f"""
    <div class='alert alert-{variant}'>
        <span class='alert-icon'>{icon}</span>
        <span class='alert-message'>{message}</span>
    </div>
    """


def risk_card(titel: str, ernst: str, aantal: int, 
              eigenaar: str, status: str, beschrijving: str) -> str:
    """Genereer een risico-card als HTML-string."""
    return f"""
    <div class="risk-card">
        <div class="risk-header">
            <h3 class="risk-title">{titel}</h3>
            {badge(ernst.upper(), variant=_variant_for(ernst))}
        </div>
        <p class="risk-description">{beschrijving}</p>
        <div class="risk-footer">
            <span class="risk-meta">Eigenaar: {eigenaar}</span>
            <span class="risk-meta">Status: {status} ({aantal})</span>
        </div>
        <div class="risk-actions">
            <button class="btn btn-primary">👁️ Bekijk</button>
            <button class="btn btn-secondary">⚠️ Escaleer</button>
        </div>
    </div>
    """


def _variant_for(ernst: str) -> str:
    """Map een ernst op een CSS-variant."""
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
    return mapping.get(ernst.strip().lower(), "neutral")


# =============================================================================
# CSS — Expliciet horizontaal, geen verticale tekst
# =============================================================================

CLEAN_CSS = """
<style>
/* Metric cards */
.metric-card {
    background: #161B22;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
}
.metric-title { font-size: 0.8rem; opacity: 0.8; }
.metric-value { font-size: 1.8rem; font-weight: bold; margin: 0.25rem 0; }
.metric-delta { font-size: 0.85rem; opacity: 0.7; }

/* Badges */
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

/* Alerts */
.alert {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.alert-icon { font-size: 1.2rem; }
.alert-message { flex: 1; }
.alert-info    { background: rgba(56,139,253,0.15); border-left: 4px solid #388BFD; }
.alert-success { background: rgba(46,160,67,0.15); border-left: 4px solid #2EA043; }
.alert-warning { background: rgba(210,153,34,0.15); border-left: 4px solid #D29922; }
.alert-error   { background: rgba(218,54,51,0.15); border-left: 4px solid #DA3633; }

/* Risk cards */
.risk-card {
    background: #161B22;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
}
.risk-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}
.risk-title { font-size: 1.1rem; margin: 0; }
.risk-description { font-size: 0.9rem; opacity: 0.9; margin: 0.5rem 0; }
.risk-footer {
    display: flex;
    gap: 1rem;
    font-size: 0.8rem;
    opacity: 0.7;
    margin-top: 0.5rem;
}
.risk-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
}

/* Buttons */
.btn {
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    border: none;
}
.btn-primary { background: #1f6feb; color: #FFF; }
.btn-secondary { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
.btn:hover { opacity: 0.9; }

/* Status distributie */
.status-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0.25rem 0;
}
.progress-bar {
    flex: 1;
    height: 8px;
    background: #21262d;
    border-radius: 4px;
    overflow: hidden;
}
.progress-fill { height: 100%; }
.progress-fill-danger { background: #DA3633; }
.progress-fill-warning { background: #D29922; }
.progress-fill-info { background: #388BFD; }
.progress-fill-success { background: #2EA043; }
</style>
"""


# =============================================================================
# Demodata — 8 risico's uit demo_app.py, getransformeerd naar PLATTE TEKST
# =============================================================================

RISICO_DATA = [
    {
        "id": 1,
        "titel": "Datalek",
        "beschrijving": "Mogelijk ongeautoriseerde toegang tot klantdata.",
        "ernst": "kritiek",
        "eigenaar": "J. van Dijk",
        "status": "Open",
        "aantal": 5,
    },
    {
        "id": 2,
        "titel": "Compliance audit ISO 27001",
        "beschrijving": "Openstaande acties voor ISO certificering.",
        "ernst": "hoog",
        "eigenaar": "M. de Vries",
        "status": "In behandeling",
        "aantal": 12,
    },
    {
        "id": 3,
        "titel": "Downtime productieomgeving",
        "beschrijving": "SLA risico bij ongeplande uitval.",
        "ernst": "middel",
        "eigenaar": "A. Smit",
        "status": "Open",
        "aantal": 18,
    },
    {
        "id": 4,
        "titel": "Budgetoverschrijding",
        "beschrijving": "Cloudkosten binnen verwachte marge gehouden.",
        "ernst": "laag",
        "eigenaar": "F. Bakker",
        "status": "Gesloten",
        "aantal": 7,
    },
    {
        "id": 5,
        "titel": "Phishing campagne",
        "beschrijving": "Verhoogde phishing activiteit gemeld.",
        "ernst": "hoog",
        "eigenaar": "P. Jansen",
        "status": "Open",
        "aantal": 3,
    },
    {
        "id": 6,
        "titel": "Backup monitoring",
        "beschrijving": "Backup controles moeten worden verbeterd.",
        "ernst": "middel",
        "eigenaar": "L. Peters",
        "status": "In behandeling",
        "aantal": 4,
    },
    {
        "id": 7,
        "titel": "Legacy systeem ondersteuning",
        "beschrijving": "EOL planning vereist prioritering.",
        "ernst": "laag",
        "eigenaar": "K. Mulder",
        "status": "Open",
        "aantal": 11,
    },
    {
        "id": 8,
        "titel": "Ransomware preventie",
        "beschrijving": "Detectie en isolatie processen verouderd.",
        "ernst": "kritiek",
        "eigenaar": "S. Vermeer",
        "status": "Open",
        "aantal": 2,
    },
]


# =============================================================================
# Pagina functies
# =============================================================================

def toon_status_distributie() -> None:
    """Statusdistributie — telling in Python, markup in het component.
    
    Dit is de historische 'None Critical (5)' symptoomlocatie.
    Implementatie volgt het kernpatroon: telling buiten component,
    badge binnen HTML-string.
    """
    from collections import Counter
    
    st.subheader("📈 Status distributie")
    
    # Dynamische telling uit RISICO_DATA
    distributie = Counter(r["ernst"] for r in RISICO_DATA)
    
    # Volgorde van ernst — voorspelbare presentatie, geen dict-willekeur
    VOLGORDE = ["kritiek", "hoog", "middel", "laag"]
    
    for ernst in VOLGORDE:
        if ernst in distributie:
            aantal = distributie[ernst]
            percentage = round((aantal / len(RISICO_DATA) * 100))
            variant = _variant_for(ernst)
            
            html(f"""
            <div class="status-row">
                {badge(ernst.upper(), variant)}
                <span>({aantal})</span>
                <div class="progress-bar">
                    <div class="progress-fill progress-fill-{variant}" style="width: {percentage}%"></div>
                </div>
                <span>{percentage}%</span>
            </div>
            """)


def toon_dashboard() -> None:
    """Render de Dashboard pagina met dynamische aggregaties."""
    st.title("📊 Dashboard")
    
    # Welkom alert
    html(alert(
        "Welkom terug, Risk Manager. Hier is je overzicht van alle risico's.",
        variant="info",
    ))
    
    # --- Dynamische aggregaties (één bron van waarheid: RISICO_DATA) ---
    totaal = len(RISICO_DATA)
    kritiek = sum(1 for r in RISICO_DATA if r["ernst"] == "kritiek")
    openstaand = sum(1 for r in RISICO_DATA if r["status"] == "Open")
    score = 71  # Hardcoded voor demo
    
    # Metric cards in kolommen
    cols = st.columns(4)
    with cols[0]:
        html(metric_card("Totaal risico's", totaal, icon="📋"))
    with cols[1]:
        html(metric_card("Kritiek", kritiek, delta="→ prioriteit", icon="🔴"))
    with cols[2]:
        html(metric_card("Openstaand", openstaand, icon="🔓"))
    with cols[3]:
        html(metric_card("Risicoscore", f"{score}%", delta="↓ 4%", icon="📊"))
    
    st.divider()
    
    # Status distributie — aparte functie (historische symptoomlocatie)
    toon_status_distributie()
    
    st.divider()
    
    # Recente risico's
    st.subheader("📋 Recente risico's")
    
    for risico in RISICO_DATA[:3]:
        html(risk_card(
            titel=risico["titel"],
            ernst=risico["ernst"],
            aantal=risico["aantal"],
            eigenaar=risico["eigenaar"],
            status=risico["status"],
            beschrijving=risico["beschrijving"],
        ))
    
    # Success alert
    html(alert(
        "Dashboard volledig geladen. Alle data is actueel.",
        variant="success",
    ))


def toon_risicos() -> None:
    """Render de Risico's pagina met filters en zoekveld — alle 8 risico's."""
    st.title("⚠️ Risico's")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        ernsten = ["Alle"] + sorted({r["ernst"].capitalize() for r in RISICO_DATA})
        filter_ernst = st.selectbox(
            "Filter op ernst:",
            ernsten,
            key="filter_ernst",
        )
    
    with col2:
        zoekterm = st.text_input(
            "🔍 Zoek op titel",
            "",
            key="zoek_titel",
        )
    
    # Status filter
    statussen = ["Alle", "Open", "In behandeling", "Gesloten"]
    filter_status = st.selectbox(
        "Filter op status:",
        statussen,
        key="filter_status",
    )
    
    # Filter logica — eerst ernst, dan status, dan zoeken
    zichtbaar = RISICO_DATA.copy()
    
    if filter_ernst != "Alle":
        zichtbaar = [r for r in zichtbaar if r["ernst"].lower() == filter_ernst.lower()]
    
    if filter_status != "Alle":
        zichtbaar = [r for r in zichtbaar if r["status"] == filter_status]
    
    if zoekterm:
        zoekterm_lower = zoekterm.lower()
        zichtbaar = [
            r for r in zichtbaar 
            if zoekterm_lower in r["titel"].lower() or zoekterm_lower in r["beschrijving"].lower()
        ]
    
    # --- Koppeling met Settings: max_kaarten limitering ---
    max_kaarten = st.session_state.get("max_kaarten", 8)
    
    if len(zichtbaar) > max_kaarten:
        # Toon alert met toelichting
        html(alert(
            f"⚠️ Er zijn {len(zichtbaar)} risico's gevonden, maar er worden er maximaal {max_kaarten} getoond. "
            f"Pas de limiet aan in de Settings pagina om meer te zien.",
            variant="warning",
        ))
        zichtbaar = zichtbaar[:max_kaarten]
    
    st.divider()
    
    # Resultaten
    st.subheader(f"Resultaten ({len(zichtbaar)} van {len(RISICO_DATA)})")
    
    if not zichtbaar:
        html(alert("Geen risico's gevonden die voldoen aan je filters.", variant="warning"))
    else:
        for risico in zichtbaar:
            html(risk_card(
                titel=risico["titel"],
                ernst=risico["ernst"],
                aantal=risico["aantal"],
                eigenaar=risico["eigenaar"],
                status=risico["status"],
                beschrijving=risico["beschrijving"],
            ))
    
    # Info alert
    html(alert(
        "Tip: Gebruik de filters om snel specifieke risico's te vinden. Klik op 'Bekijk' voor meer details.",
        variant="info",
    ))


def laad_instellingen() -> dict:
    """Instellingen uit session_state, met zinnige standaardwaarden."""
    standaard = {
        "thematoon": "Donker",
        "max_kaarten": 8,
        "notificaties": True,
        "email_notificaties": True,
        "push_notificaties": False,
        "critical_alerts": True,
    }
    for sleutel, waarde in standaard.items():
        st.session_state.setdefault(sleutel, waarde)
    return {k: st.session_state[k] for k in standaard}


def toon_settings() -> None:
    """Render de Settings pagina met functionele instellingen."""
    st.title("⚙️ Settings")
    
    html(alert(
        "Hier kun je je voorkeuren en app-instellingen beheren.",
        variant="info",
    ))
    
    instellingen = laad_instellingen()
    
    # --- Gebruikersinstellingen ---
    st.subheader("👤 Gebruikersinstellingen")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.text_input(
            "Naam",
            value="Risico Beheerder",
            key="settings_name",
        )
        st.text_input(
            "E-mail",
            value="risico@voorbeeld.nl",
            key="settings_email",
        )
        st.selectbox(
            "Rol",
            ["Beheerder", "Analyst", "Lezer"],
            key="settings_role",
        )
    
    with col_right:
        # --- Notificatie-instellingen ---
        st.subheader("🔔 Notificatie-instellingen")
        
        st.session_state["email_notificaties"] = st.checkbox(
            "E-mail notificaties",
            value=instellingen["email_notificaties"],
            key="widget_email_notif",
        )
        st.session_state["push_notificaties"] = st.checkbox(
            "Push notificaties",
            value=instellingen["push_notificaties"],
            key="widget_push_notif",
        )
        st.session_state["critical_alerts"] = st.checkbox(
            "Critical alerts",
            value=instellingen["critical_alerts"],
            key="widget_critical_notif",
        )
    
    st.divider()
    
    # --- Thema-instellingen ---
    st.subheader("🎨 Thema")
    
    thema_col1, thema_col2 = st.columns(2)
    
    with thema_col1:
        if st.button("🌙 Donker", key="theme_dark", type="primary", use_container_width=True):
            st.session_state["thematoon"] = "Donker"
            html(alert("Donker thema actief", variant="info"))
    
    with thema_col2:
        if st.button("☀️ Licht", key="theme_light", type="secondary", use_container_width=True):
            st.session_state["thematoon"] = "Licht"
            html(alert("Licht thema gedemonstreerd — CSS aanpassing vereist", variant="warning"))
    
    st.divider()
    
    # --- Risico-weergave instellingen ---
    st.subheader("📊 Risico-weergave")
    
    st.session_state["max_kaarten"] = st.slider(
        "Maximaal zichtbare risico's per pagina",
        min_value=1,
        max_value=12,
        value=instellingen["max_kaarten"],
        key="widget_max_kaarten",
    )
    
    html(alert(
        "Instellingen worden bewaard voor de duur van de sessie.",
        variant="success",
    ))
    
    st.divider()
    
    # --- Danger Zone ---
    st.subheader("⚠️ Danger Zone")
    
    danger_col1, danger_col2, danger_col3 = st.columns(3)
    
    with danger_col1:
        if st.button("🔄 Cache legen", key="btn_clear_cache", use_container_width=True):
            st.success("Cache geleegd")
    
    with danger_col2:
        if st.button("📊 Data resetten", key="btn_reset_data", use_container_width=True):
            st.warning("Data resetten — demo data wordt herladen")
    
    with danger_col3:
        if st.button("🗑️ Alle risico's verwijderen", key="btn_delete_all", type="secondary", use_container_width=True):
            st.error("Verwijderen niet beschikbaar in demo-modus")
    
    st.divider()
    
    # --- Export functionaliteit ---
    st.subheader("📤 Export")
    
    if st.button("Exporteer risico-overzicht (CSV)", key="btn_export", use_container_width=True):
        csv_content = "Titel;Ernst;Status;Eigenaar\n"
        for r in RISICO_DATA:
            csv_content += f"{r['titel']};{r['ernst']};{r['status']};{r['eigenaar']}\n"
        
        st.download_button(
            label="Download CSV",
            data=csv_content,
            file_name="risico_overzicht.csv",
            mime="text/csv",
            key="btn_download_csv",
        )


# =============================================================================
# Main app met sidebar navigatie
# =============================================================================

def main() -> None:
    """Hoofdapplicatie met sidebar navigatie."""
    st.set_page_config(page_title="IT Risk Management", layout="wide")
    
    # Injecteer CSS
    html(CLEAN_CSS)
    
    # Sidebar navigatie
    st.sidebar.title("🛡️ ITRM")
    st.sidebar.markdown("---")
    
    pagina_keuze = st.sidebar.radio(
        "Navigatie",
        ["Dashboard", "Risico's", "Settings"],
        index=0,
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Info")
    st.sidebar.markdown("""
    **Versie:** v2.0  
    **Laatste update:** 2026-09-18  
    **Architectuur:** Clean (geen None bugs)
    """)
    
    # Pagina routering
    if pagina_keuze == "Dashboard":
        toon_dashboard()
    elif pagina_keuze == "Risico's":
        toon_risicos()
    elif pagina_keuze == "Settings":
        toon_settings()


if __name__ == "__main__":
    main()
