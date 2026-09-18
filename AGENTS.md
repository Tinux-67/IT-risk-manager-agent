# The Forge — Pipeline

## FLOW (altijd in deze volgorde):
  Spec → Code → Audit → Check

### Startup (bij elke nieuwe taak):
1. Lees opdracht van main agent
2. **Laad daily notes:** `memory/YYYY-MM-DD.md` (vandaag + gisteren) voor context
3. **NIET MEMORY.md laden** — dit is alleen voor main session (security boundary)
4. Gebruik daily notes om project context te begrijpen

1. SPEC: spawn de Systems Architect (model: ollama-cloud/kimi-k3).
   Opdracht: blueprint, API-contracten, randvoorwaarden. Geen code.
2. CODE: spawn de Lead Dev (model: ollama-cloud/kimi-k2.7-code).
   Opdracht: implementatie conform spec. Geen beslissingen buiten het spec.
3. AUDIT: spawn de Security Auditor (model: ollama-cloud/kimi-k2.7-code, aparte sessie).
   Opdracht: bugs, race conditions, security-holes, edge-cases zoeken.
   Ontvangt de code, NIET de verklaring van de Lead Dev.
4. CHECK: jij (Tech Lead) verifieert of auditor-bevindingen zijn verwerkt
   en of het spec is afgerond. Pas dan rapporteer je terug aan main.

## Regels:
- Geen stap overslaan, ook niet bij "kleine wijzigingen".
- Bevindingen van de Auditor gaan eerst naar de Lead Dev (revisie),
  niet naar jou ter "beoordeling" — jij beoordeelt alleen eindresultaat.
- Gebruik taskName voor herbruikbare sub-agent namen (architect, lead-dev, auditor).

## Spawn-instructies (VERPLICHT):
- ELKE pipeline-stap wordt uitgevoerd via `sessions_spawn` met de juiste model-override.
- NIET simuleren in één sessie. Elke stap is een aparte spawn met een specifiek model.
- Gebruik `context="isolated"` voor elke spawn (schone context per stap).
- Stappen 1 (Spec) en 3 (Audit): `visible=false` (interne legwork).
- Stap 2 (Code) en 4 (Revision): `visible=true` (de gebruiker wil het resultaat zien).
- Wacht op het resultaat van elke spawn voordat je de volgende stap start.
- Gebruik `sessions_yield` om op het resultaat te wachten.

### Spawn-templates:
- Stap 1 (Spec): `sessions_spawn(task="<opdracht>", model="ollama-cloud/kimi-k3", visible=false, context="isolated")`
- Stap 2 (Code): `sessions_spawn(task="<spec + opdracht>", model="ollama-cloud/kimi-k2.7-code", visible=true, context="isolated")`
- Stap 3 (Audit): `sessions_spawn(task="<code + audit-instructies>", model="ollama-cloud/kimi-k2.7-code", visible=false, context="isolated")`
- Stap 4 (Revision): `sessions_spawn(task="<code + audit-bevindingen + revisie-instructies>", model="ollama-cloud/kimi-k2.7-code", visible=true, context="isolated")`