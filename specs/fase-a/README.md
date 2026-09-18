# `components/ui/` — UI Component Library

Centrale, herbruikbare componenten voor de IT Risk Manager Agent Streamlit app.

## Installatie

Zet in elke pagina bovenaan:

```python
from components.ui import inject_design_system

inject_design_system()
```

De helper laadt `assets/css/design_system.css` één keer in de pagina.

## Componenten

### Buttons

```python
from components.ui.buttons import PrimaryButton, SecondaryButton, DangerButton, GhostButton

if PrimaryButton("Analyseer risico", icon="🔍"):
    run_analysis()

SecondaryButton("Annuleren")
DangerButton("Verwijder", aria_label="Verwijder dit risico")
GhostButton("Meer info")
```

### Cards

```python
from components.ui.cards import Card, MetricCard, RiskCard

with Card("Samenvatting"):
    st.write("Inhoud van de kaart")

MetricCard("Open risico's", value=12, delta="+2 sinds vorige week")

with RiskCard("Datalek", level="critical"):
    st.write("Mogelijk datalek in productiedatabase")
```

### Badges

```python
from components.ui.badges import Badge

Badge("Goedgekeurd", variant="success")
Badge("In behandeling", variant="warning")
Badge("Kritiek", variant="danger")
Badge("Concept", variant="neutral")
```

### Alerts

```python
from components.ui.alerts import Alert

Alert("Rapport gegenereerd", variant="success")
Alert("Verbinding mislukt", variant="error", title="Fout")
```

### Feedback

```python
from components.ui.feedback import show_spinner, show_toast, show_error, show_success

with show_spinner("Risico's worden geanalyseerd..."):
    result = analyze_risks()

show_success("Analyse voltooid")
show_toast("Synchronisatie gelukt", variant="success")
```

## Conventies

- Geen inline CSS — gebruik altijd componenten uit deze module.
- Voor elke interactieve component: geef een unieke `key` mee als je er meerdere van rendert.
- ARIA labels zijn optioneel maar verplicht bij icon-only knoppen.
