# 🛡️ IT Risk Manager (ITRM) — Demo App

**Versie:** v2.0 (Clean Architectuur)  
**Status:** ✅ Productie-gereed  
**Laatste update:** 2026-09-18

Een Streamlit-demo applicatie voor IT Risk Management, gebouwd met een schone component-architectuur.

---

## 📋 Inhoud

- [Features](#-features)
- [Installatie](#-installatie)
- [Gebruik](#-gebruik)
- [Tests](#-tests)
- [Migratie v2.0](#-migratie-v20)
- [Bestandsstructuur](#-bestandsstructuur)
- [Beveiliging](#-beveiliging)
- [License](#-license)

---

## ✨ Features

### Dashboard
- **4 metric cards** — Totaal risico's, Kritiek, Openstaand, Risicoscore
- **Status distributie** — Dynamische aggregatie met progress bars
- **Recente risico's** — Snel overzicht van laatste updates

### Risico's Pagina
- **8 risico cards** — Volledig overzicht met filters
- **Filters** — Op ernst (KRITIEK/HOOG/MIDDEL/LAAG) en status
- **Zoekveld** — Zoeken op titel of beschrijving
- **Resultatenteller** — Toont aantal gevonden risico's

### Settings Pagina
- **Gebruikersinstellingen** — Naam, E-mail, Rol
- **Notificaties** — E-mail, Push, Critical alerts
- **Thema** — Donker/Licht modus
- **Risico-weergave** — Limiet instellen (1-12 kaarten)
- **Export** — CSV download van risico-overzicht
- **Danger Zone** — Cache legen, Data resetten

---

## 🚀 Installatie

### Vereisten

- Python 3.12+
- pip

### Stap 1: Clone de Repository

```bash
git clone https://github.com/Tinux-67/IT-risk-manager-agent.git
cd IT-risk-manager-agent
```

### Stap 2: Installeer Dependencies

```bash
pip install -r requirements.txt
```

**Vereiste packages:**
- `streamlit` (≥1.28)
- `pytest` (voor tests)

---

## 📖 Gebruik

### Start de App

```bash
./run_demo.sh
```

**Of handmatig:**
```bash
streamlit run demo_app.py --server.address 127.0.0.1 --server.port 8502
```

### Toegang via Browser

**Lokaal:** `http://localhost:8502`  
**Network:** `http://<IP>:8502` (alleen binnen je netwerk)

### SSH Tunnel (Aanbevolen voor VPS)

```bash
ssh -L 8502:localhost:8502 ubuntu@<vps-ip>
```

Open daarna: `http://localhost:8502`

---

## 🧪 Tests

### Acceptatietests Uitvoeren

```bash
# Tests draaien (start app niet)
./run_demo.sh --check

# Of handmatig
pytest test_acceptance.py -v
```

### Verwachte Output

```
======================== test session starts =========================
test_at1_componenten_retourneren_string_niet_none::: PASSED
test_at1_componenten_bevatten_geen_streamlit_calls::: PASSED
test_at1_geen_string_none_in_output::: PASSED
test_at1_statusdistributie_zonder_none::: PASSED
test_at2_data_is_plat_zonder_html_tags::: PASSED
test_at2_renderpad_gebruikt_unsafe_allow_html::: PASSED
test_at3_css_bevat_geen_verticale_regels::: PASSED
test_at3_design_system_css_controleren::: PASSED
test_integratie_volledige_risicopagina_zonder_defecten::: PASSED
======================== 9 passed in 0.32s =========================
✓ Alle 9 acceptatietests geslaagd.
```

---

## 🔄 Migratie v2.0

Deze versie (v2.0) is een complete herschrijving van de oorspronkelijke demo-app om drie rendering-bugs op te lossen.

### Opgeloste Bugs

| Bug | Symptoom | Oplossing |
|-----|----------|-----------|
| #1 | "None" output bij badges | Componenten retourneren strings, geen side-effects |
| #2 | Ruwe HTML zichtbaar | Énkel renderpad met `unsafe_allow_html=True` |
| #3 | Verticale tekst | CSS zonder `writing-mode`/`rotate` |

### Architectuur Principes

1. **Data is plat** — Geen HTML in data-velden
2. **Componenten zijn pure functies** — Alleen `return`, geen `st.*` calls
3. **Één renderpad** — Alle HTML via `html()` met `unsafe_allow_html=True`

### Zie Ook

- [MIGRATIE_LOG.md](./MIGRATIE_LOG.md) — Volledige migratiedocumentatie
- Tag: `v2.0-migratie-complete`

---

## 📁 Bestandsstructuur

```
IT-risk-manager-agent/
├── demo_app.py                 # Hoofdapplicatie (v2.0)
├── test_acceptance.py          # Acceptatietests (9 tests)
├── run_demo.sh                 # Deploy script + kwaliteitspoort
├── requirements.txt            # Python dependencies
├── README.md                   # Deze file
├── MIGRATIE_LOG.md             # Migratiedocumentatie
├── archives/                   # Gearchiveerde bestanden (optioneel)
│   ├── demo_app_oud.py         # Oorspronkelijke app (bugged)
│   └── backups/                # Fase-backups
└── .logs/                      # Test logs (automatisch)
    └── run-<tijdstip>.log
```

---

## 🔒 Beveiliging

### Firewall Configuraties

- **UFW:** `default deny incoming` — alleen SSH (22) publiek toegestaan
- **Bind-adres:** App bindt op `127.0.0.1` — niet publiek toegankelijk
- **Toegang:** Via SSH-tunnel of binnen je netwerk

### Aanbevelingen

- Gebruik **SSH-tunnel** voor toegang vanaf externe locaties
- Publiceer Docker-containers altijd met expliciete IP-binding
- Houd dependencies up-to-date (`pip install --upgrade streamlit pytest`)

---

## 📊 Versie Geschiedenis

| Versie | Datum | Beschrijving |
|--------|-------|--------------|
| v2.0 | 2026-09-18 | Clean Architectuur — 3 bugs opgelost |
| v1.0 | — | Oorspronkelijke demo (bugged) |

---

## 🤝 Bijdragen

Bijdragen zijn welkom! Zie de migratiedocumentatie voor het gebruikte migratiepatroon.

### Kwaliteitseisen

- Alle tests moeten groen zijn (`./run_demo.sh --check`)
- Nieuwe features moeten tests hebben
- Volg de drie architectuur-principes (zie [Migratie v2.0](#-migratie-v20))

---

## 📝 License

Dit project is onderdeel van het IT Risk Manager platform.

---

## 📞 Contact

- **Repository:** https://github.com/Tinux-67/IT-risk-manager-agent
- **Issues:** https://github.com/Tinux-67/IT-risk-manager-agent/issues

---

**Gebouwd met** ❤️ **en Streamlit**
