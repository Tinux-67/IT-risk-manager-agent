# Technisch Implementatieplan — UX-verbeteringen IT Risk Manager Agent

> Rol: Lead Dev  
> Input: UX Audit Rapport (Systems Architect)  
> Doel: technisch plan voor productie-waardige UX in de Streamlit app. Geen code.

---

## 1. Component library review — hergebruik vs. nieuwbouw

### Bestaande Streamlit componenten die we blijven gebruiken
| Streamlit primitive | Gebruik | Wijziging nodig |
|---------------------|---------|-----------------|
| `st.button` | primaire / secundaire acties | wrapper toevoegen voor consistente kleur/grootte |
| `st.text_input`, `st.text_area`, `st.selectbox` | formulieren | centrale validatie + foutmelding helper |
| `st.columns` | layout | defensiever gebruiken, max. 2-3 kolommen |
| `st.metric` | KPI / risicoscore kaarten | wrapper voor consistente card-styling |
| `st.dataframe` | risicotabellen | wrapper: scrollbaar + compact + badges |
| `st.expander` | detail secties | consistente titel + icoon styling |
| `st.sidebar` | navigatie | actieve state + iconen + breadcrumbs |
| `st.spinner` / `st.toast` / `st.error` / `st.success` | feedback | centrale helper om aanroepconsistentie af te dwingen |
| `@st.cache_data` / `@st.cache_resource` | performance | structureel toepassen op BM25 & veracity |

### Nieuwe interne componenten (verplicht)
| Component | Bestand | Doel |
|-----------|---------|------|
| `PrimaryButton`, `SecondaryButton`, `DangerButton`, `GhostButton` | `components/ui/buttons.py` | uniforme CTA's, outline/ghost varianten |
| `Card`, `MetricCard`, `RiskCard` | `components/ui/cards.py` | visuele groepering + hiërarchie |
| `Badge` | `components/ui/badges.py` | status / impact / confidence (success/warning/danger/neutral) |
| `Alert` | `components/ui/alerts.py` | error / success / info / warning met iconen + aria |
| `Skeleton` | `components/ui/skeleton.py` | placeholder tijdens BM25 & veracity acties |
| `DataTable` | `components/ui/tables.py` | wrapper om `st.dataframe` met horizontale scroll + header styling |
| `Fieldset`, `FormGroup` | `components/ui/forms.py` | groeperen van gerelateerde velden |
| `Breadcrumbs`, `SidebarNav` | `components/ui/navigation.py` | actieve state + navigatiepad |

---

## 2. CSS / thema audit — realistisch Streamlit advies

### Huidige verwachte problemen (typisch voor Streamlit)
- `.streamlit/config.toml` ontbreekt of bevat geen `theme` block.
- Kleuren worden inline of via `st.markdown(..., unsafe_allow_html=True)` gezet, niet centraal.
- Geen typografische schaal; `st.title`, `st.header`, `st.subheader` gebruikt ad-hoc.
- Custom CSS via `st.markdown("<style>...</style>", unsafe_allow_html=True)` verspreid over pagina's.
- Geen dark-mode support; app valt terug op Streamlit defaults.

### Realistische oplossing
1. **Thema-configuratie (`config.toml`) als bron van waarheid**
   - Definieer `primaryColor`, `backgroundColor`, `secondaryBackgroundColor`, `textColor`.
   - Streamlit's thema geeft contrast op UI componenten; extra CSS override voor badges/cards.

2. **Centrale CSS-module (`assets/css/design_system.css`)**
   - Variabelen gebaseerd op tokens uit `config.toml` en extra custom properties.
   - Selectoren gericht op Streamlit classes: `.stButton>button`, `.stTextInput`, `.stMarkdown`, `.stDataFrame`, etc.
   - Responsiviteit via media queries: `@media (max-width: 768px)` en `@media (max-width: 480px)`.
   - Focus states en visible focus rings toevoegen.

3. **CSS injectie helper**
   - Eén functie `inject_design_system()` in `components/ui/__init__.py`.
   - Verwijdert alle losse `<style>` injecties elders.

4. **Tailwind? Nee.**
   - Streamlit laadt geen Tailwind; custom utility-classes via eigen CSS file zijn effectiever en lichter.

### Contrast roadmap (WCAG 2.1 AA)
- Body text ≥ 4.5:1 tegen achtergrond.
- UI componenten / grafische objecten ≥ 3:1.
- Donker schema gebruiken als basis voor productie; licht schema kan later worden toegevoegd.
- Testen met browser DevTools contrast checker of Python `wcag_contrast_ratio` helper.

---

## 3. Implementatievolgorde

### Fase A — Fundering (Quick wins, structural)
1. **Design tokens in `config.toml`** — primary, secondary, neutral, feedback kleuren + typografie. (S)
2. **Centrale CSS module + injectie helper** — vervangt alle losse stijlen. (M)
3. **Component library skelet** — buttons, badges, alerts, cards wrappers. (M)
4. **Consistente feedback helper** — wrapper voor spinner, toast, error, success. (S)

### Fase B — Pagina's herbouw
5. **Sidebar navigatie actieve state + breadcrumbs** — navigatie-IA expliciet maken. (M)
6. **Pagina templates** — elke pagina krijgt H1, intro, fieldsets/cards. (M)
7. **Risico-overzicht → Detail → Analyse/Actie flow** — contentstructuur herschrijven. (M)
8. **Data tables wrapper** — horizontale scroll, compact, badges. (S)

### Fase C — Interactie & performance
9. **Skeleton screens** — BM25 retrieval, veracity scoring. (M)
10. **Caching zware functies** — `@st.cache_data` / `@st.cache_resource`. (S)
11. **Formulier-validatie helper** — visuele + tekstuele foutmeldingen. (M)
12. **Progress indicators** — langdurige acties > 1 seconde. (S)

### Fase D — Polish
13. **Responsive kolom-audit** — 320/768/1024/1440. (M)
14. **Accessibility audit** — focus states, aria-labels, keyboard test. (M)
15. **Contrast / WCAG AA controle** — fixes doorvoeren. (M)
16. **Animaties / micro-interacties** — hover, transitions. (L)
17. **Thema-switcher licht/donker/hoog contrast** — nice-to-have. (L)
18. **Design documentatie + UX-copy styleguide** — low priority. (L)

---

## 4. Geschatte effort

| Verbetering | Effort | Opmerking |
|-------------|--------|-----------|
| Design tokens (`config.toml`) | S | 2-4 uur inclusief contrastcheck |
| Centrale CSS module + injectie | M | 4-8 uur, afhankelijk van huidige verspreide CSS |
| Component library (buttons, cards, badges, alerts) | M | 8-16 uur inclusief hergebruik bestaande pagina's |
| Feedback helper (spinner/toast/error/success) | S | 2-4 uur |
| Sidebar + breadcrumbs | M | 4-8 uur |
| Pagina templates (H1, intro, fieldsets) | M | 8-16 uur per pagina-cluster |
| Data table wrapper | S | 2-4 uur |
| Skeleton screens | M | 4-8 uur |
| Caching BM25 / veracity | S | 2-4 uur, testen op invalidatie gedrag |
| Formulier-validatie helper | M | 4-8 uur |
| Progress indicators | S | 2-4 uur |
| Responsive kolom-audit | M | 4-8 uur incl. testen |
| Accessibility audit + fixes | M | 8-16 uur |
| WCAG contrast fixes | M | 4-8 uur na audit |
| Animaties / micro-interacties | L | 8-16 uur, lage ROI |
| Thema-switcher | L | 8-16 uur |
| Design docs / styleguide | L | 8-16 uur |

**Realistisch totaal:** 80–140 uur voor een volledige productie-UX, verdeeld over 3 sprints.

---

## 5. Dependencies / volgorde

```
[Design tokens in config.toml]
        ↓
[Centrale CSS module + injectie helper]
        ↓
[Component library (buttons, badges, cards, alerts)]
        ↓
        ├─→ [Sidebar navigatie + breadcrumbs]
        ├─→ [Pagina templates + contentstructuur]
        ├─→ [Data table wrapper]
        └─→ [Feedback helper: spinner/toast/error/success]
                  ↓
        [Formulier-validatie helper]
                  ↓
        [Skeleton screens]
                  ↓
        [Caching + progress indicators]
                  ↓
        [Responsive audit]
                  ↓
        [Accessibility + contrast audit]
                  ↓
        [Polish: animaties, thema-switcher, docs]
```

### Harde afhankelijkheden
- Pagina-herbouw kan pas na component library.
- Skeleton screens hebben de CSS-module nodig.
- Formulier-validatie heeft feedback helper nodig.
- Accessibility audit pas nadat componenten en pagina's stabiel zijn.

### Technische vereisten
- Python ≥ 3.10, Streamlit ≥ 1.32 (voor `st.toast`, verbeterd thema).
- `streamlit-extras` optioneel voor geavanceerde UI primitives (mag pas later).
- Geen extra frontend build chain; houdt het pure Python/CSS.

---

## 6. Risk assessment

| Wijziging | Risico's | Mitigatie |
|-----------|----------|-----------|
| Thema in `config.toml` | Streamlit thema kan custom CSS overschrijven of vice versa. | CSS variabelen afleiden uit Streamlit thema; één injectie helper testen. |
| Centrale CSS module | Verwijderen van losse `<style>` blocks kan pagina's breken als iets gemist wordt. | Incrementeel migreren; pagina's 1 voor 1 aanpassen. |
| Component library wrappers | Bestaande button-/input callbacks kunnen anders gedragen door extra markup. | Behoud exact dezelfde Streamlit API signature's; wrappers zijn puur presentatie. |
| Sidebar actieve state | `st.session_state` navigatie logica kan pagina-states verstoren. | Beperk actieve state tot visueel; gebruik Streamlit native page routing. |
| Breadcrumbs | Manuele breadcrumb logica kan out-of-sync raken. | Breadcrumb afleiden van huidige page + geklikt risico-id. |
| Caching BM25/veracity | `@st.cache_data` kan stale data geven als brondata wijzigt. | TTL instellen; cache wissen bij import/upload. |
| Skeleton screens | Custom HTML/CSS kan toegankelijkheidsproblemen veroorzaken. | Gebruik ARIA `aria-busy="true"` + `aria-live` regio's. |
| Formulier-validatie | Strictere validatie kan bestaande workflows blokkeren. | Begin met waarschuwingen, later blocking. |
| Responsive kolom-audit | Wijzigen van `st.columns` ratio's kan dashboard lay-out verstoren. | Test met echte schermgroottes / DevTools device mode. |
| Accessibility fixes | Focus rings / labels kunnen visuele styling veranderen. | Test met toetsenbord + screen reader (NVDA/VoiceOver). |
| Thema-switcher | Dynamisch wisselen van thema in Streamlit vereist herladen. | Indien gewenst: config-only, geen runtime switch. |

### Hoogste risico's
1. **Centrale CSS migratie** — hoogste kans op regressie in lay-out.  
   *Mitigatie:* pagina per pagina, visuele diff per pagina.
2. **Caching** — stale retrieval resultaten kunnen verkeerde risico-analyses geven.  
   *Mitigatie:* cache key op brondata hash, cache invalidatie bij data-import.
3. **Navigatie state in `st.session_state`** — kan race-conditions veroorzaken bij snelle klikken.  
   *Mitigatie:* gebruik Streamlit's native multi-page routing indien beschikbaar, anders alleen leesbare navigatie-state.

---

## 7. Deliverables per fase (voor controle door Tech Lead)

| Fase | Deliverable |
|------|-------------|
| A | `config.toml` thema, `assets/css/design_system.css`, `components/ui/` library, feedback helper |
| B | Sidebar + breadcrumbs, pagina templates, data table wrapper, herschreven pagina's |
| C | Skeleton screens, caching, formulier-validatie, progress indicators |
| D | Responsive & accessibilty auditrapport, contrast fixes, polish items |

---

## 8. Aanbeveling aan Tech Lead

Start met **Fase A** (tokens, CSS, component library, feedback helper). Dit geeft de grootste visuele impact met het minste regressierisico en vormt de basis voor alle latere pagina-wijzigingen. Vervolgens Fase B pagina per pagina herbouwen. Fase C pas inzetten zodra de UI consistent is, om interactie-problemen op te lossen. Fase D is polish en kan in een aparte iteratie.

Plan is klaar voor review / doorgave naar Code-fase.
