# Migration Guide — Fase A

Doel: bestaande pagina's migreren naar de centrale design system componenten.

## 1. Verwijder losse CSS injecties

Zoek in de codebase naar:

```python
st.markdown("""
<style>
  ...
</style>
""", unsafe_allow_html=True)
```

Vervang deze door:

```python
from components.ui import inject_design_system
inject_design_system()
```

Dit moet één keer bovenaan elke pagina gebeuren.

## 2. Vervang inline gestijlde HTML

**Was:**
```python
st.markdown(
    '<span style="color: green; padding: 4px 8px; border-radius: 12px;">Goedgekeurd</span>',
    unsafe_allow_html=True,
)
```

**Wordt:**
```python
from components.ui.badges import Badge
Badge("Goedgekeurd", variant="success")
```

## 3. Knoppen vervangen

**Was:**
```python
st.button("Analyseer", type="primary")
```

**Wordt:**
```python
from components.ui.buttons import PrimaryButton
if PrimaryButton("Analyseer"):
    analyze()
```

Gebruik de juiste variant:
- Primaire actie -> `PrimaryButton`
- Secundaire actie / annuleren -> `SecondaryButton`
- Destructief (verwijderen, stoppen) -> `DangerButton`
- Subtiele actie (meer info, terug) -> `GhostButton`

## 4. Kaarten gebruiken

**Was:**
```python
st.subheader("Risico details")
st.write("...")
```

**Wordt:**
```python
from components.ui.cards import Card
with Card("Risico details"):
    st.write("...")
```

## 5. Feedback standaardiseren

**Was:**
```python
st.error("Er ging iets mis")
```

**Wordt:**
```python
from components.ui.feedback import show_error
show_error("Er ging iets mis")
```

Hetzelfde geldt voor `show_success`, `show_warning`, `show_info`, `show_toast` en `show_spinner`.

## 6. Checklijst per pagina

- [ ] `inject_design_system()` bovenaan geïmporteerd en aangeroepen.
- [ ] Geen overgebleven `<style>` blocks.
- [ ] Alle knoppen via button componenten.
- [ ] Alle statuslabels via `Badge`.
- [ ] Alle meldingen via feedback helpers.
- [ ] Kaarten voor logische groepering.

## 7. Risico's

- Oude inline styles kunnen de design-system CSS overschrijven. Verwijder deze altijd.
- Streamlit `type="primary"` knoppen gebruiken het thema, maar component helpers voegen extra consistentie en ARIA toe.
