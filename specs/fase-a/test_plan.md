# Fase A — Test Plan

## 1. Contrast (WCAG 2.1 AA)
- Gebruik WebAIM Contrast Checker of axe DevTools in Chrome/Firefox.
- Controleer body tekst (#FAFAFA) op app-achtergrond (#0E1117): ≥ 4.5:1 (doel 16.6:1).
- Controleer body tekst op kaartachtergrond (#262730): ≥ 4.5:1 (doel 14.2:1).
- Controleer primaire knoptekst (#FFFFFF) op #1A5FB4: ≥ 4.5:1.
- Controleer badge-tekst op badge-achtergronden: ≥ 4.5:1.
- Controleer UI componenten / grafische objecten: ≥ 3:1.
- Automatische smoke-test: importeer componenten en verifieer dat geen inline `style="..."` attributen voorkomen.

## 2. Accessibility
- Keyboard: Tab door pagina, controleer dat elke knop/link focus heeft met zichtbare focus ring.
- ARIA: inspecteer alerts op `role="alert"` en knoppen op `aria-label` indien alleen icon.
- Screenreader: controleer dat badges als tekst worden voorgelezen, niet als afbeelding.
- axe DevTools scan: 0 kritieke of ernstige bevindingen.

## 3. Responsive
- Test viewports: 320px, 768px, 1024px, 1440px (Chrome DevTools Device Toolbar).
- Controleer dat kaarten niet horizontaal scrollen op 320px.
- Controleer dat knoppen op ≤ 768px `width: 100%` hebben en netjes stacken.
- Controleer dat metrics leesbaar blijven op 320px.

## 4. Consistentie
- Inspecteer alle pagina's op overgebleven `<style>` injecties; verwacht 0 losse blocks buiten `inject_design_system()`.
- Controleer dat alle buttons via `PrimaryButton` / `SecondaryButton` / etc. worden aangeroepen.
- Controleer dat badges/alerts altijd via de componenten worden gerenderd.

## 5. Functioneel
- Start Streamlit app (`streamlit run app.py`); controleer geen CSS-laadfouten in browser console.
- Controleer dat `inject_design_system()` precies één `<style>` block injecteert per pagina.
- Controleer dat toast duur 4 seconden is en error/success/warning/info altijd een icon tonen.
