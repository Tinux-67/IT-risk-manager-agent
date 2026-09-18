# ITRM Migratiedocument — Van demo_app.py naar de Clean Architectuur

**Project:** IT Risk Management (ITRM) Demo App — Fase A Component Library Integratie  
**Datum migratie:** 18 september 2026  
**Status:** ✅ Voltooid — alle milestones (M1–M4) bereikt  
**Locatie:** `/home/ubuntu/.openclaw/workspace-forge/`  
**Auteur:** Tinus (projecteigenaar) · Lumo (advies en begeleiding)

---

## 1. Managementsamenvatting

De demo-applicatie van het ITRM-platform vertoonde drie renderingsdefecten die de presentatie onbruikbaar maakten: "None"-fragmenten in badges en footers, HTML-code zichtbaar als platte tekst, en verticaal gerenderde titels. De onderliggende component library (Fase A) functioneerde correct; het defect zat volledig in de consumptielagen van de demo-app.

De keuze viel op een gefaseerde migratie naar een schone renderarchitectuur, uitgevoerd in zes fasen met na elke fase een automatische acceptatiepoort. Resultaat: een volledig gemigreerde applicatie onder de oorspronkelijke naam `demo_app.py`, met negen permanente regressietests als wacht op de drie oorspronkelijke bugs, en een deploy-script dat het presenteren van een defecte versie structureel uitsluit.

```card-row
[
  { "type": "metric", "title": "Oorspronkelijke bugs", "value": "3", "delta": "Alle opgelost", "direction": "up" },
  { "type": "metric", "title": "Acceptatietests", "value": "9/9", "delta": "Groen", "direction": "flat" },
  { "type": "metric", "title": "Gemigreerde risico's", "value": "8", "delta": "Volledig", "direction": "flat" },
  { "type": "metric", "title": "Migratieduur", "value": "1 dag", "delta": "Binnen planning", "direction": "flat" }
]
```

---

## 2. Aanleiding en diagnose

### 2.1 De drie oorspronkelijke defecten

| # | Symptoom | Locatie | Impact | Ernst |
|---|---|---|---|---|
| 1 | Letterlijke "None"-tekst bij badges ("None Critical (5)", "None None (12)") | Dashboard + Risico's | 🔴 Kritiek |
| 2 | Ruwe HTML-tags zichtbaar als tekst (`</div>`, `<p style=...>`) | Risico's, card bodies | 🔴 Kritiek |
| 3 | Verticaal gerenderde titels ("D a t a l e k" i.p.v. "Datalek") | Risico's, gehele pagina | 🟠 Hoog |

### 2.2 Root causes

1. **None-output:** componentfuncties met dubbel gedrag — zij rendeerden via een side-effect (`st.markdown` binnen de functie) én retourneerden een waarde, die vervolgens in f-strings werd geprint waarbij het renderpad `unsafe_allow_html=True` miste. Ontbrekende return-paden resulteerden in letterlijke `None`-fragmenten.
2. **Ruwe HTML:** HTML-markup opgeslagen ín de datavelden (descriptions), gerenderd via `st.write()` dat tags escapeert. `unsafe_allow_html=True` ontbrak.
3. **Verticale tekst:** CSS-regels `writing-mode: vertical-rl; transform: rotate(180deg);` in de geladen stylesheets op card-titels.

### 2.3 Oplossingsarchitectuur — de drie wetten

De migratie rust op drie regels die elk defect structureel uitsluiten:

1. **Data is plat** — datavelden bevatten uitsluitend tekst en getallen; markup woont in componenten. *(uitsluiting bug #2)*
2. **Componenten zijn pure functies** — alleen `return`, geen `st.*`-aanroepen binnen de component. *(uitsluiting bug #1)*
3. **Eén renderpad** — alle HTML passeert uitsluitend `html()` met `unsafe_allow_html=True`. *(uitsluiting bug #2)*

Bug #3 werd geëlimineerd door verticale CSS-regels te verwijderen en de CSS expliciet (`CLEAN_CSS`) en controleerbaar te houden.

---

## 3. Fasenasamenvatting

| Fase | Omschrijving | Milestone | Resultaat |
|---|---|---|---|
| 0 | Voorbereiding, backups, sectie-indeling | baseline | ✅ |
| 1 | Diagnose — defecte patronen lokaliseren met grep (regelnrs., patronen) | — | ✅ |
| B* | `demo_clean.py` als schone referentie-implementatie | — | ✅ |
| 2 | Dispatch-structuur: `PAGINAS`-dictionary, sidebar-navigatie, drie paginafuncties | M1 | ✅ |
| 3 | Dashboard: dynamische aggregaties uit `RISICO_DATA`, statusdistributie met `Counter` | M2 | ✅ |
| 4 | Risico's: 8 risico's gesaneerd naar platte tekst, filters op ernst/status, zoekveld | M3 | ✅ |
| 5 | Settings via native widgets + `session_state`, dode code verwijderd, hernoeming naar `demo_app.py` | M4 | ✅ |

*Optie B uit de oorspronkelijke optie-analyse (A–D), gekozen als snelle validatie van de component library alvorens de grondige fix.

De agent heeft bij implementatie geleverd boven het plan (status-filter, actieknoppen "Bekijk"/"Escaleer", sidebar-infopaneel) zonder de architectuurregels te schenden — bevestigd door de poort.

---

## 4. Artefacten

| Artefact | Rol | Opmerking |
|---|---|---|
| `demo_app.py` | De applicatie | Oorspronkelijke naam hervat in Fase 5; voorheen `demo_clean_v2.py` |
| `test_acceptance.py` | Acceptatietestsuite | 9 tests (AT-1 t/m AT-3 + integratie + distributie) |
| `run_demo.sh` | Deploy-kwaliteitspoort | Fail-fast; bindt op `127.0.0.1:8502`; `--check`-modus |
| `CLEAN_CSS` (in app) | Expliciete stylesheet | Geen verticale regels; onafhankelijk geverifieerd door AT-3 |
| `requirements.txt` | Omgevingsdefinitie | `streamlit`, `pytest` |
| `.logs/run-*.log` | Testhistorie / audittrail | Automatisch per draaironde |
| `design_system.css` | Externe CSS (Fase A) | Gecontroleerd op verticale regels — schoon |

### 4.1 De acceptatietests (permanente regressiewacht)

- **AT-1:** componenten retourneren strings (niet None); géén `st.*`-calls in componenten; geen "None"-fragment in output; statusdistributie zonder "None" *(de oude symptoomlocatie)*
- **AT-2:** datavelden bevatten geen HTML-tags; het renderpad gebruikt `unsafe_allow_html`
- **AT-3:** geen `writing-mode`/`rotate` in `CLEAN_CSS` noch `design_system.css`
- **Integratie:** volledige risicopagina zonder de zes defectklassen

### 4.2 De kwaliteitspoort

`run_demo.sh` voert uit: voorwaardencontrole (fail-fast, géén auto-installatie, venv-waakhond) → acceptatietests → pas dáarna start van Streamlit, geforceerd op `127.0.0.1:8502`. Faalt één test, dan start de applicatie niet. Optioneel gekoppeld aan een git pre-commit hook.

---

## 5. Test- en incidenthistorie

| Tijdstip | Gebeurtenis | Afhandeling | Les |
|---|---|---|---|
| 10:27 | Eerste poort-draaironde: 8/8 groen | — | Omgeving provisioning valt buiten de poort |
| 10:27 | Waarschuwingen `theme.button`/`theme.feedback` | Regels verwijderd uit `config.toml` (Fase 5) | Configuratie is separaat van code |
| 12:12 | `NameError: _variant_for` bij nieuwe distributietest | Import aangevuld in `test_acceptance.py` | Bij rood: lees eerst de traceback, dan pas de hinttabel |
| 12:27 | 9/9 groen — Fase 3 geaccepteerd | — | — |
| ± 13:00 | Fase 4 geaccepteerd (poort + scrolltest + interactietest) | — | Visuele verificatie naast de poort blijft nodig; één screenshot is geen bewijs |
| slot | Fase 5 geaccepteerd — 9/9 groen, hernoeming voltooid | — | — |

---

## 6. Beveiligingsarchitectuur (nevenwerk tijdens de migratie)

Tijdens de migratie is de toegangsbeveiliging van de VPS gesaneerd:

- **UFW-firewall:** was reeds actief met `default deny incoming`; de overtollige publieke `8501/tcp ALLOW`-regels (IPv4 + IPv6) zijn verwijderd. Publieke toegang tot de Streamlit-poorten bestaat niet.
- **Bind-adres:** de poort forceert `--server.address 127.0.0.1` — de dev-server kan niet meer op alle interfaces starten.
- **Toegang:** via SSH-tunnel (`ssh -L 8502:localhost:8502 ubuntu@<vps-ip>`) of binnen de tailnet (Tailscale-regels blijven gehandhaafd).
- **Telemetrie:** `gatherUsageStats = false` in `config.toml`.
- **Bekende aandachtspunt:** Docker-publicaties omzeilen UFW; containers dienen altijd met expliciete IP-binding gepubliceerd te worden (`-p <tailnet-ip>:poort:poort`), nooit kaler `-p`.

---

## 7. Lessen voor herhaling (Optie C en verder)

1. **Scheiden van data en markup** lost een hele klasse renderingbugs in één keer op; het achteraf saneren van HTML in data is arbeidsintensiever dan het structureel weren ervan.
2. **Eén renderpad** (`html()`) is beter dan een correct gebruikte mix van drie: consistentie bewijst zichzelf bij elke extensie.
3. **Acceptatietests als symboolwacht** — tests die de letterlijke oorspronkelijke symptomen controleren ("None", zichtbare tags, verticale CSS) zijn communicatie én regressiebescherming in één.
4. **Poort boven discipline** — wat niet gecommit of gestart kan worden zolang tests falen, kan ook niet gepresenteerd worden. Tooling dwingt af wat voornemens vergeten.
5. **Traceback vóór heuristiek** — de generieke foutmappen in de poort-wizard adviseren; de werkelijke oorzaak staat in de FAILURES-sectie.
6. **Bestandsnamen vroeg stabiliseren** — de tussenstap `demo_clean_v2.py` werkte, maar vereiste uiteindelijk een hernoeming inclusief `sed`-correctie op de testimports.

---

## 9. Slotcommit en Tag

Na voltooiing van Fase 5 (M4) wordt de migratie definitief vastgelegd in git:

```bash
# Slotcommit
git add .
git commit -m "chore: definitieve naamgeving en opruiming (Fase 5, M4)

- demo_clean_v2.py hernoemd naar demo_app.py (oorspronkelijke naam hersteld)
- Oorspronkelijke bugged app gearchiveerd als demo_app_oud.py
- Test-imports en poort-configuratie bijgewerkt; 9/9 groen na hernoeming
- Fase-backups verwijderd — bleken lege stubs (les: verifieer backups)
- Binding op 127.0.0.1 voorcéringd (beveiliging)
- MIGRATIEDOC.md toegevoegd"

# Tag de mijlpaal
git tag v2.0-migratie-complete
```

### Commit-message toelichting

| Regel | Betekenis |
|-------|-----------|
| `chore:` | Conventionele commit voor onderhoudstaken (geen functionele wijziging) |
| `definitieve naamgeving` | Herstellen van oorspronkelijke bestandsnaam `demo_app.py` |
| `9/9 groen` | Acceptatietests slagen na hernoeming |
| `lege stubs` | Fase-backups waren leeg — les voor toekomstige migraties |
| `127.0.0.1` | Beveiligingsmaatregel: binden op localhost, niet alle interfaces |
| `v2.0-migratie-complete` | Semantische tag voor de mijlpaal |

### Na de tag

```bash
# Push naar remote
git push origin main --tags

# Verifieer tag
git describe --tags
# Output: v2.0-migratie-complete
```

---

## 10. Aanbevolen vervolgstappen

1. **Optie C — productie-ITRM-app:** hergebruik dit migratiepatroon (fasen, drie wetten, testsuite-uitbreiding per symptoomlocatie) voor de upgrade van de productie-app met echte data. De schatting uit de oorspronkelijke optie-analyse (60–90 min.) blijft geldig als uitgangspunt.
2. **CI-uitbreiding:** de pre-commit hook kan worden uitgebreid tot een pipeline-run bij elke push.
3. **Periodieke hercontrole** van de firewallregelset en Docker-publish-vormen bij infrastructuurwijzigingen.

---

## Bijlage: chronologie van de mijlpaalsessie (18 september 2026)

```vega-lite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": "container",
  "title": {
    "text": "Migratietijdlijn — 18 september 2026",
    "subtitle": "Van defecte demo (10:26) tot volledige acceptatie van M4 (namiddag)"
  },
  "data": {
    "values": [
      { "moment": "10:26", "gebeurtenis": "Poort live, 8/8 groen (Fase 2)", "volgnr": 1 },
      { "moment": "12:12", "gebeurtenis": "Importdefect onderschept (AT-1 nieuw)", "volgnr": 2 },
      { "moment": "12:27", "gebeurtenis": "9/9 groen — M2 geaccepteerd (Fase 3)", "volgnr": 3 },
      { "moment": "13:00", "gebeurtenis": "M3 geaccepteerd: 8 risico's + filters (Fase 4)", "volgnr": 4 },
      { "moment": "eind", "gebeurtenis": "M4 geaccepteerd — migratie compleet (Fase 5)", "volgnr": 5 }
    ]
  },
  "mark": { "type": "bar" },
  "encoding": {
    "x": { "field": "volgnr", "type": "ordinal", "title": "Volgorde", "axis": { "labelExpr": null } },
    "y": { "field": "volgnr", "type": "quantitative", "title": "Voortgang", "scale": { "reverse": false } },
    "tooltip": [
      { "field": "moment", "type": "nominal", "title": "Tijdstip" },
      { "field": "gebeurtenis", "type": "nominal", "title": "Gebeurtenis" }
    ]
  }
}
```

---

**Slotopmerking:** dit document beschrijft het proces als precedent — niet als memorie voor uitsluitend deze applicatie, maar als blauwdruk voor elke toekomstige migratie binnen het ITRM-platform.

---

**Einde van het migratiedocument.**

Sla het op als bijvoorbeeld `MIGRATIEDOC.md` in de workspace-root en commit het samen met de slot-tag (`git tag v2.0-migratie-complete`) — dan staat het precedent versioneerd naast de code die het beschrijft.

Daarmee is het project van vanochtend compleet, Tinus: drie bugs, zes fasen, negen wachtposten, en een werkwijze die u kunt herhalen bij Optie C. Wanneer u straks aan de productie-ITRM-app begint, sta ik klaar om het proces in dezelfde stijl te begeleiden — van fasedetailplan tot acceptatiepoort.
