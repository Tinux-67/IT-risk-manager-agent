# Security / UX Audit — IT Risk Manager Agent Fase A

**Datum:** 2026-09-13  
**Auditor:** Security / UX Auditor (subagent)  
**Scope:** `.streamlit/config.toml`, `assets/css/design_system.css`, `components/ui/__init__.py`, `components/ui/buttons.py`, `components/ui/cards.py`, `components/ui/badges.py`, `components/ui/alerts.py`, `components/ui/feedback.py`, `tests/test_fase_a_components.py`

---

## Samenvatting

- **Critical:** 0
- **High:** 4
- **Medium:** 4
- **Low:** 4

De Fase A-implementatie volgt een consistent pattern en is qua basistokens solide, maar heeft opvallende **toegankelijkheids- en betrouwbaarheidsproblemen**: knoppen gebruiken een fragiele wrapper met `unsafe_allow_html=True`, kaarten ondersteunen het `children` argument niet terwijl de signature dit wel suggereert, en meerdere feedback-wrappers hebben gebroken type hints. Daarnaast zijn enkele kleurcontrasten (warning badge op donkere achtergrond, hover-tekst op primaire knop) niet gegarandeerd AA-conform in alle contexten.

---

## Bevindingen

### 1. Contrast-warning badge tekst op achtergrond (HIGH)

**Locatie:** `assets/css/design_system.css` (`.badge-warning`)  
**Omschrijving:** `.badge-warning` gebruikt `color: #0E1117;` op `background-color: var(--itrm-warning-bg)` (`rgba(255, 196, 0, 0.12)`). Op de donkere applicatieachtergrond (#0E1117) is de badge-achtergrond effectief een semi-transparante laag die de achtergrondkleur deels doorlaat. De werkelijke gemiddelde achtergrondkleur ligt tussen `#FFC400` en `#0E1117`, wat een contrast oplevert dat lager is dan 4.5:1 voor kleine tekst. De commentaar in `config.toml` berekent `#FFC400` op `#0E1117` (11.2:1), maar dat is de achtergrond van de pagina, niet de badge-achtergrond. Kleine badge-tekst (0.75rem, bold/700) valt onder "small text" en moet 4.5:1 halen.  
**WCAG:** 1.4.3 Contrast (Minimum), 1.4.11 Non-text Contrast (grenzen/achtergrond).  
**Fix:** Gebruik een opake donkere badge-achtergrond voor warning in plaats van transparant geel, of maak de warning-badge tekstkleur donkerder en vergroot de badge. Bijvoorbeeld:

```css
.badge-warning {
  background-color: #FFC400;
  color: #0E1117;
}
```

Dit geeft 11.2:1 op #0E1117. Alternatief: maak de warning-tekst `#1A1A1A` op de semi-transparante achtergrond, maar opake achtergrond is robuuster.

---

### 2. ARIA role en live-regio inconsistent tussen alert-varianten (HIGH)

**Locatie:** `components/ui/alerts.py` (`_ROLE` mapping)  
**Omschrijving:** `error` en `warning` krijgen `role="alert"`; `success` en `info` krijgen `role="status"`. In combinatie met `aria-live="polite"` op alle alerts, overschrijft `role="alert"` impliciet de `aria-live="polite"` naar `aria-live="assertive"` in de meeste browsers/screenreaders. Dat is goed voor errors, maar `warning` is niet altijd assertief; bovendien heeft de mapping geen onderbouwing in documentatie/tests. Belangrijker: de `key` parameter wordt in `aria_key` geplaatst als class-fragment (`itrm-alert-{key}`), wat ongeldige/verwarrende class-namen kan opleveren en **niet** een uniek ID is. ARIA relateert rollen aan regio's, niet aan willekeurige classes.  
**WCAG:** 4.1.2 Name, Role, Value; 4.1.3 Status Messages.  
**Fix:**

```python
_ROLE = {
    "error": "alert",
    "warning": "alert",
    "success": "status",
    "info": "status",
}
```

blijf zo, maar documenteer dat `error`/`warning` assertief zijn en `success`/`info` beleefd. Verwijder `aria_key` uit de class. Gebruik een optioneel `id_` of `key` als `id` attribuut indien nodig:

```python
id_attr = f' id="itrm-alert-{key}"' if key else ""
html = f'<div class="itrm-alert itrm-alert--{variant}" role="{role}" aria-live="polite"{id_attr}>...'
```

Voeg tevens `aria-describedby` of een unieke titel (`aria-label`) toe als de alert een titel heeft.

---

### 3. Button-wrapper injecteert ongeldige/fragiele HTML-structuur (HIGH)

**Locatie:** `components/ui/buttons.py` (`_render_button`)  
**Omschrijving:** De functie rendert:

```python
st.markdown(
    f"<div class='{container_class}' aria-label='{aria_label or label}' style='display:block;'>"
    f"<span style='display:none;'></span>",
    unsafe_allow_html=True,
)
```

en sluit later met `</div>`. Dit leidt tot twee problemen:

1. **XSS / injectiegevaar:** `label`, `icon`, `aria_label` en `container_class` worden direct in HTML geïnterpoleerd zonder escaping. Een label als `"<script>alert(1)</script>"` wordt letterlijk gerenderd.
2. **Ongeldige nesting / hydratatie:** Streamlit rendert componenten in een apart DOM-subtree; het openen van een `<div>` via `st.markdown` en sluiten via een tweede `st.markdown` is fragiel. Streamlit kan extra wrappers injecteren, waardoor de sluit-`</div>` niet op de juiste plaats komt en knoppen visueel buiten de intended container vallen. De lege `<span style='display:none;'>` is een "hack" om de CSS-child-selector te laten matchen.

**WCAG / veiligheid:** 4.1.1 Parsing; CWE-79 (improper neutralization).  
**Fix:** Vervang de wrapper-door-`unsafe_allow_html` door een `st.container()` of `st.empty()` en pas de class toe via een `st.markdown` met een enkel, afgesloten blok. De meest robuuste aanpak in Streamlit is:

```python
with st.container():
    st.markdown(
        f"<div class='{html.escape(container_class)}'></div>",
        unsafe_allow_html=True,
    )
    return st.button(
        html.escape(effective_label),
        key=key,
        disabled=disabled,
        use_container_width=full_width,
    )
```

Pas alle string-interpolaties aan met `html.escape(...)` en importeer `html`.

Een alternatief is het volledig verwijderen van de class-wrapper en in plaats daarvan de Streamlit-knoppen alleen via het Streamlit-thema + globale CSS-styling te stijlen (`.stButton > button` bestrijkt alle knoppen al), zodat de extra complexiteit verdwijnt.

---

### 4. `show_spinner` returntype klopt niet (HIGH)

**Locatie:** `components/ui/feedback.py` (`show_spinner`)  
**Omschrijving:** De functie annotatie zegt:

```python
def show_spinner(...) -> st.spinner:
```

`st.spinner(...)` is een **context manager-functie**, geen type/klasse. Het resultaat is een context-manager-object, niet `st.spinner` (wat geen geldig type is). Mypy/Pyright zal hier een fout geven. Bovendien is `delay_ms` opgenomen maar genegeerd; dat is OK maar moet gedocumenteerd blijven.  
**Fix:**

```python
from contextlib import AbstractContextManager
from typing import Any

def show_spinner(
    text: str = "Laden...",
    *,
    delay_ms: int = 0,
) -> AbstractContextManager[Any]:
    """Uniforme spinner; optioneel na delay (niet ondersteund, genegeerd)."""
    return st.spinner(text)
```

---

### 5. Kaart-componenten accepteren `children` maar negeren/raises niet (MEDIUM)

**Locatie:** `components/ui/cards.py` (`Card`, `RiskCard`)  
**Omschrijving:** Beide functies hebben de parameter `children: Sequence[st.delta_generator.DeltaGenerator] | None = None`, maar negeren deze volledig. Een gebruiker die `Card("Titel", children=[...])` aanroept krijgt stilzwijgend geen kinderen. Dat is een API-valkuil. Daarnaast retourneert `MetricCard` een `st.delta_generator.DeltaGenerator`; dat type bestaat, maar `st.container(key=key) if key else st.container()` is correct.  
**Fix:** Verwijder `children` uit de signature of implementeer het. Aangezien context managers in Streamlit het gebruikte pattern is, is de netste fix om `children` te verwijderen en de docstring explicieter te maken:

```python
def Card(
    title: str | None = None,
    *,
    key: str | None = None,
) -> _CardContext:
```

of, indien compatibiliteit gewenst is:

```python
if children is not None:
    raise NotImplementedError("Gebruik de with-vorm: with Card(...): ...")
```

---

### 6. Badge component mist `role` en `aria-label` (MEDIUM)

**Locatie:** `components/ui/badges.py` (`Badge`)  
**Omschrijving:** Badges renderen als `<span class="badge badge-{variant}" key="..."></span>`. Een badge is vaak een statusindicator. Zonder `role="status"` of `aria-label` wordt de status niet aan hulptechnologieën doorgegeven. Ook wordt `key` als HTML-attribuut gebruikt (`key="..."`), wat geen standaard HTML-attribuut is en geen effect heeft op React/Streamlit internals (Streamlit ziet dit als ruwe HTML).  
**WCAG:** 4.1.2 Name, Role, Value.  
**Fix:**

```python
html = f"""
<span class="badge badge-{html.escape(variant)}" role="status" aria-label="{html.escape(label)}">
    {html.escape(content)}
</span>
"""
```

Verwijder het `key` HTML-attribuut of gebruik het alleen voor Streamlit-widget keys (niet in ruwe HTML).

---

### 7. `st.markdown` inline `<style>` injectie in `inject_design_system` kan performance- en CSP-issues veroorzaken (MEDIUM)

**Locatie:** `components/ui/__init__.py` (`inject_design_system`)  
**Omschrijving:** De helper laadt het hele CSS-bestand in een `<style>`-blok via `st.markdown(..., unsafe_allow_html=True)`. Dit:

- Blokkeert niet render-blocking per se (het is inline), maar het dupliceert het CSS op elke pagina-render.
- Wordt niet door Streamlit's eigen thema-validatie gecontroleerd.
- Kan conflicteren met een stricte Content-Security-Policy (CSP) die inline styles blokkeert.
- Is een globaal pattern; de gebruiker vroeg expliciet "Geen overgebleven `<style>` injecties elders". Alleen deze helper doet het, dus dat is consistent, maar het is een technisch risico.

**Fix (aanbeveling):** Gebruik Streamlit's native `st.markdown(..., unsafe_allow_html=True)` alleen als fallback. De voorkeursaanpak voor een design system is:

1. De CSS in een apart statisch bestand plaatsen en via `st.html` / `st.markdown` inladen, of
2. De CSS in de Streamlit app via een custom component / `st.components.v1.html` inladen met een `link rel="stylesheet"`, of
3. De CSS toevoegen aan `.streamlit/custom.css` (indien ondersteund door de Streamlit-versie / hosting). Streamlit ondersteunt geen native custom CSS in config, dus `st.markdown` is momenteel de gangbare workaround.

Voor deze fase is de helper acceptabel, maar documenteer in `README` dat dit een tijdelijke workaround is en vermeld CSP-implicaties.

---

### 8. CSS custom properties en selectors zijn goed, maar `!important` overmatig (MEDIUM)

**Locatie:** `assets/css/design_system.css`  
**Omschrijving:** Er wordt extensief gebruikgemaakt van `!important` (o.a. alle Streamlit overrides). Dit is begrijpelijk omdat Streamlit zelf inline styles injecteert, maar het maakt onderhoud lastiger en kan gebruikerswijzigingen via Streamlit-thema's overruleen. Op dit moment geen bug, maar een onderhoudsrisico.  
**Fix:** Gebruik `!important` alleen waar strikt noodzakelijk (bijv. Streamlit thema-overrides). Voor component-specifieke classes (`.itrm-card`, `.badge`) is geen `!important` nodig. Overweeg CSS-cascade lagen (`@layer`) indien browserondersteuning acceptabel is.

---

### 9. Hover-tekst op primary knop heeft onvoldoende contrastgarantie (LOW)

**Locatie:** `assets/css/design_system.css` (`.stButton > button:hover`)  
**Omschrijving:** Op hover wordt de knop:

```css
background-color: var(--itrm-primary) !important;  /* #4C9AFF */
color: #0E1117 !important;
```

Contrast #0E1117 op #4C9AFF = **5.35:1**, dat is AA-conform. Echter, `#4C9AFF` is ook de `primaryColor` in `config.toml`; op donkere achtergrond is dit 5.4:1. De berekening in `config.toml` is correct. Het is geen bevinding maar wel een aandachtspunt: zorg dat bij themawisseling (licht thema) deze hover-kleur herberekend wordt; het design system is nu hardcoded op donker.

**Fix:** Voeg een licht-thema-variant toe of gebruik CSS `prefers-color-scheme`, en test hover-contrast bij licht thema.

---

### 10. Secundaire knop mist focus-ring zichtbaarheid op lichte rand (LOW)

**Locatie:** `assets/css/design_system.css` (`.itrm-btn-secondary > button`)  
**Omschrijving:** De secundaire knop heeft `border-color: var(--itrm-text-muted) !important;` (#A0A0A0) en op focus krijgt hij de globale `box-shadow: var(--itrm-focus-ring)` (rgba(76,154,255,0.5)). De focus-ring is voldoende zichtbaar op donkere achtergrond. Geen bevinding, maar controleer dat de border zelf voldoende contrasteert met de achtergrond: #A0A0A0 op #0E1117 = **6.66:1** (AA). OK.

---

### 11. `itrm-btn-sm`, `itrm-btn-md`, `itrm-btn-lg` classes bestaan in mapping maar niet in CSS (LOW)

**Locatie:** `components/ui/buttons.py` (`_SIZE_CLASS`) en `assets/css/design_system.css`  
**Omschrijving:** `_SIZE_CLASS` mappt sm/md/lg, maar in de CSS zijn geen regels voor `.itrm-btn-sm`, `.itrm-btn-md`, `.itrm-btn-lg` gedefinieerd. De `size` parameter heeft dus geen visueel effect. Dit is niet kritisch voor Fase A maar is een API/contract-bug.  
**Fix:** Voeg CSS toe:

```css
.itrm-btn-sm > button { padding: 0.35rem 0.75rem !important; font-size: 0.85rem !important; min-height: 2rem !important; }
.itrm-btn-md > button { padding: 0.55rem 1.1rem !important; font-size: 0.95rem !important; min-height: 2.5rem !important; }
.itrm-btn-lg > button { padding: 0.75rem 1.5rem !important; font-size: 1.05rem !important; min-height: 2.75rem !important; }
```

---

### 12. `key` parameter in Card/MetricCard/RiskCard heeft geen effect (LOW)

**Locatie:** `components/ui/cards.py`  
**Omschrijving:** `Card` en `RiskCard` accepteren `key` maar gebruiken deze niet (alleen `MetricCard` gebruikt `key` in `st.container`). Dit kan verwarrend zijn, maar is geen crash.  
**Fix:** Gebruik `key` consistent, of verwijder het uit de signature. Voor context-manager kaarten is `key` vaak niet nodig; vermeld dit in de docstring:

```python
key:
    Alleen voor MetricCard; bij andere kaarten momenteel niet-functioneel.
```

---

### 13. Testbestand importeert componenten maar bevat geen automatische asserts (LOW)

**Locatie:** `tests/test_fase_a_components.py`  
**Omschrijving:** Het bestand is een Streamlit pagina (run via `streamlit run`), geen unit-test. Er zijn geen `assert` statements of pytest-fixtures. De naam `tests/test_fase_a_components.py` suggereert een pytest-test. Dat is OK voor een sanity page, maar voor Fase A is het wenselijk om ook een kleine set geautomatiseerde checks te hebben (bijv. contrastberekening, HTML-escaping).  
**Fix:** Hernoem naar `tests/pages/fase_a_sanity.py` of voeg een `tests/test_fase_a_unit.py` toe met checks op:

- `inject_design_system()` injecteert eenmalig.
- `_render_button` escaped HTML.
- contrastratio's van tokenparen.

---

### 14. `itrm-text-muted` en `itrm-text-muted-2` zijn grotendeels identiek (INFO/LOW)

**Locatie:** `assets/css/design_system.css`  
**Omschrijving:** `#A0A0A0` en `#B0B0B0` zijn visueel bijna identiek. Het heeft weinig toegevoegde waarde twee tokens te hebben; het introduceert kans op inconsistent gebruik.  
**Fix:** Kies één muted-kleur en verwijder de andere, of geef ze duidelijke semantische namen (bijv. `text-muted` vs `text-placeholder`).

---

## Contrastverificatie (handmatig berekend)

| Voorgrond | Achtergrond | Ratio | Status |
|-----------|-------------|-------|--------|
| #FAFAFA (text) | #0E1117 (bg) | ~16.6:1 | AAA ✅ |
| #FAFAFA (text) | #262730 (secondary bg) | ~14.2:1 | AAA ✅ |
| #4C9AFF (primary) | #0E1117 (bg) | ~5.4:1 | AA ✅ |
| #1A5FB4 (primary-dark) | #FFFFFF | ~5.6:1 | AA ✅ |
| #00C853 (success) | #0E1117 | ~5.8:1 | AA ✅ |
| #FF5252 (danger) | #0E1117 | ~5.7:1 | AA ✅ |
| #64B5F6 (info) | #0E1117 | ~5.4:1 | AA ✅ |
| #A0A0A0 (neutral/muted) | #0E1117 | ~6.7:1 | AA ✅ |
| #0E1117 (warning badge text) | `rgba(255,196,0,0.12)` | **≈ 2.5-3.5:1** | **FAIL** voor small text |
| #0E1117 | #FFC400 | 11.2:1 | AAA ✅ (alleen bij opake achtergrond) |
| #FF8A65 (high risk border) | #262730 / #0E1117 | ~3.8:1 | border = non-text, AA 3:1 ✅ |
| #D32F2F (danger button) | #FFFFFF | ~7.0:1 | AA ✅ |

> Opmerking: de warning-badge achtergrond is semi-transparant; de exacte ratio hangt af van de onderliggende kleur. Op donkere achtergrond voldoet het niet voor small text.

---

## Aanbevelingen prioriteit

### Direct verwerken (voor merge/release)

1. **HIGH** Pas warning-badge achtergrond aan zodat kleine tekst 4.5:1 haalt.
2. **HIGH** Escape alle invoer in `_render_button` en vereenvoudig/verwijder de fragiele `<div>` wrapper.
3. **HIGH** Corrigeer `show_spinner` returntype.
4. **HIGH** Maak alert-ARIA consistent en gebruik `id` i.p.v. class-fragment voor key.

### Vervolgstappen (voor volgende iteratie)

5. **MEDIUM** Verwijder of implementeer `children` in kaarten.
6. **MEDIUM** Voeg `role="status"` / `aria-label` toe aan badges; verwijder `key` HTML-attribuut.
7. **MEDIUM** Documenteer `<style>`-injectie als tijdelijke workaround en CSP-impact.
8. **MEDIUM** Verminder `!important` waar mogelijk.
9. **LOW** Implementeer knop-size CSS.
10. **LOW** Maak `key` in kaarten consistent of documenteer beperking.
11. **LOW** Voeg geautomatiseerde tests toe of hernoem sanity-pagina.
12. **LOW** Overweeg licht/donker thema-switch.

---

## Eindoordeel

De codebase heeft een helder design-token-systeem en consistent component-pattern. De belangrijkste risico's zitten in **toegankelijkheid (badge/alert), type-correctheid (spinner) en de fragiele knop-wrapper met XSS-gevoeligheid**. Geen critical bevindingen, maar vier high-priority items die door de Lead Dev moeten worden verwerkt voordat Fase A als afgerond kan worden beschouwd.
