# ITRM Trust Layer — Specificatie

**Versie:** 1.0  
**Datum:** 2026-09-06  
**Status:** Definitief  
**Auteur:** Systems Architect (The Forge Pipeline)

---

## 1. Probleemstelling

De IT Risk Manager Agent produceert "sloppy summaries" — gegenereerde samenvattingen bevatten alleen referentiecodes in plaats van inhoudelijke teksten. De trust layer is gedeeltelijk geïmplementeerd maar heeft kritieke gaten:

1. **Retrieval** is beperkt tot chunks van één enkel document (`update_id`) — cross-document retrieval is onmogelijk.
2. **`citation_sources`** bevat ongestructureerde LLM-output (raw JSON of fallback strings) in plaats van een gestandaardiseerd schema met chunk IDs en scores.
3. **`groundedness_score`** wordt alleen berekend als er citations zijn — anders blijft het NULL.
4. **`reasoning_chain`** is een vrije tekststring zonder schema, waardoor traceerbaarheid ontbreekt.
5. **Chunk-metadata ontbreekt**: er is geen versie-informatie voor de chunking- of retrieval-strategie, waardoor reproduceerbaarheid onmogelijk is.

---

## 2. Architectuur-overzicht

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Raw Document   │────→│   chunk_text()   │────→│  raw_chunks DB  │
│  (PDF/HTML/etc)  │     │  (retrieval.py)  │     │  + metadata     │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                               ┌──────────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │  retrieve_chunks()   │  ← BM25 over ALLE chunks
                    │   (retrieval.py)     │    (niet alleen update_id)
                    └──────────┬──────────┘
                               │  top-k chunks + scores
                               ▼
                    ┌─────────────────────┐
                    │  Cited Reasoning     │  ← LLM selecteert + motiveert
                    │  (process_updates.py)│    welke chunks relevant zijn
                    └──────────┬──────────┘
                               │  reasoning + cited_chunk_ids
                               ▼
                    ┌─────────────────────┐
                    │  generate_summary()  │  ← LLM schrijft summary
                    │  (process_updates.py)│    gebaseerd op cited chunks
                    └──────────┬──────────┘
                               │  final summary
                               ▼
                    ┌─────────────────────┐
                    │ score_groundedness() │  ← LLM evalueert summary
                    │   (veracity.py)      │    tegen source chunks
                    └──────────┬──────────┘
                               │  score 0.0–1.0 + verklaring
                               ▼
                    ┌─────────────────────┐
                    │   updates tabel      │  ← citation_sources (JSON),
                    │   (trust columns)    │    reasoning_chain (JSON),
                    │                      │    groundedness_score (REAL)
                    └─────────────────────┘
```

**Principe:** Elke summary moet traceerbaar zijn naar specifieke bron-chunks via een reproduceerbare keten: *chunk → retrieval → reasoning → summary → veracity score*.

---

## 3. Component-specificaties

### 3.1 BM25 Retrieval (`scripts/retrieval.py`)

#### 3.1.1 `chunk_text()`

Zoals bestaand, maar met toevoeging van versie-metadata.

**Signature (aangepast):**
```python
def chunk_text(
    raw_text: str,
    source_file: str,
    update_id: int,
    conn: sqlite3.Connection,
    *,
    chunking_version: str = "sentence-v1",
) -> list[dict[str, Any]]:
```

**Wijzigingen t.o.v. bestaand:**
- Nieuwe parameter `chunking_version` (default `"sentence-v1"`).
- Sla `chunking_version` op in `raw_chunks.chunking_version` kolom.
- Sla `retriever_version` op als `"bm25-v1"` bij elke insert.

**Output per chunk-dict (ongewijzigd):**
```python
{
    "id": int,               # autoincrement PK
    "update_id": int,        # FK naar updates
    "chunk_text": str,       # tekst van de chunk
    "char_start": int,       # start-positie in originele tekst
    "char_end": int,         # eind-positie
    "source_file": str,      # pad naar bronbestand
    "chunk_index": int,      # volgnummer binnen document
    "retriever_version": str,  # NIEUW — "bm25-v1"
    "chunking_version": str,   # NIEUW — "sentence-v1"
}
```

#### 3.1.2 `retrieve_chunks()`

**Kritieke wijziging:** Moet cross-document retrieval ondersteunen.

**Signature (aangepast):**
```python
def retrieve_chunks(
    query: str,
    conn: sqlite3.Connection,
    *,
    update_id: int | None = None,
    top_k: int = TOP_K_DEFAULT,
) -> list[dict[str, Any]]:
```

**Gedrag:**
- `update_id=None` (default): doorzoek **alle** chunks in `raw_chunks` (cross-document retrieval).
- `update_id=<int>`: beperk zoekopdracht tot chunks van dat ene document (backwards compatible).
- Retourneert altijd een **gesorteerde lijst** (meest relevant eerst) met score bij elk chunk.

**Output per chunk-dict (uitgebreid):**
```python
{
    "id": int,
    "update_id": int,
    "chunk_text": str,
    "char_start": int,
    "char_end": int,
    "source_file": str,
    "chunk_index": int,
    "score": float,          # NIEUW — BM25 relevance score
    "retriever_version": str,  # "bm25-v1"
    "chunking_version": str,   # "sentence-v1"
}
```

**Determinisme-eis:** Bij identieke query + database-inhoud moet de output identiek zijn. Geen randomness in tie-breaking.

---

### 3.2 Veracity Check (`scripts/veracity.py`)

**Signature (aangepast):**
```python
def score_groundedness(
    cited_texts: list[str],       # ← was cited_text: str
    summary: str,
    model: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:              # ← was float
```

**Wijzigingen t.o.v. bestaand:**
1. **`cited_texts: list[str]`** — accepteert een lijst van individuele chunk-teksten in plaats van één geconcateneerde string. De functie jointe ze intern met `\n\n---\n\n` als scheiding.
2. **Return type `dict`** in plaats van `float`, met:
   ```python
   {
       "score": float,           # 0.0–1.0
       "explanation": str,       # korte toelichting (max 200 chars)
       "model": str,             # gebruikt model
       "chunks_evaluated": int,  # aantal bron-chunks
   }
   ```
3. **Prompt-aanpassing:** Vraag de LLM om een score ÉN een éénregelige verklaring.
4. **Cache-key** wordt berekend over `json.dumps(cited_texts, sort_keys=True) + summary` voor deterministische caching.

**Aangepaste prompt:**
```
You are a factual accuracy evaluator. Rate how well the SUMMARY is grounded in the SOURCE chunks below.

For each claim in the summary, verify it appears in at least one source chunk.

Rate groundedness 0.0–1.0:
  0.0 = fabricated/contradicts sources
  0.5 = partially supported
  1.0 = fully supported

Respond in EXACTLY this format:
SCORE: <number>
EXPLANATION: <one sentence, max 200 characters>

---
SOURCES:
{cited_texts}
---
SUMMARY:
{summary}
---
```

**Fallback gedrag (ongewijzigd):** Bij LLM-fout of parse-fout → `score=0.5, explanation="default (LLM unavailable or parse error)"`.

---

### 3.3 Integratie in `scripts/process_updates.py`

#### 3.3.1 Nieuwe flow: Retrieval → Cited Reasoning → Final Summary

De bestaande flow wordt aangepast als volgt:

```
Stap 1: INSERT update row (metadata + raw_text)     [ongewijzigd]
Stap 2: chunk_text(raw_text) → raw_chunks            [+ metadata]
Stap 3: retrieve_chunks(query) → top-k chunks        [cross-document]
Stap 4: Cited Reasoning LLM-call                     [gestructureerd]
Stap 5: generate_summary(cited_chunks_text)          [alleen cited text]
Stap 6: score_groundedness(cited_texts, summary)     [dict return]
Stap 7: UPDATE update row met trust layer velden    [JSON schema's]
```

#### 3.3.2 Functie-signaturen

**`generate_summary()` (aangepast):**
```python
def generate_summary(
    text: str,
    conn: sqlite3.Connection | None = None,
    *,
    cited_chunk_texts: list[str] | None = None,
) -> str:
```

Gedrag:
- Als `cited_chunk_texts` is meegegeven en niet-leeg: gebruik **alleen** die teksten als input voor de LLM-samenvatting (niet de volledige `raw_text`).
- Als `cited_chunk_texts` None of leeg is: val terug op bestaande flow (full text → LLM → fallback).
- De fallback (`_fallback_summary()`) blijft ongewijzigd.

**Nieuwe functie: `_run_trust_layer()`**

```python
def _run_trust_layer(
    update_id: int,
    raw_text: str,
    file_path: str,
    risk_area: str,
    urgency: str,
    summary: str,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
```

Dit is de geëxtraheerde trust layer logica (nu inline in `_process_file_impl`). Retourneert:
```python
{
    "citation_sources": str,      # JSON string conform schema §4.1
    "reasoning_chain": str,       # JSON string conform schema §4.2
    "groundedness_score": float,  # 0.0–1.0
    "chunk_count": int,
}
```

#### 3.3.3 Cited Reasoning prompt (aangepast)

```
You are a regulatory compliance expert.

You are given:
1. A risk classification query
2. A set of candidate text chunks from a regulatory document

Your task has TWO steps:

STEP 1 — REASONING: In 2-3 sentences, explain which chunks are most relevant to the query and why.

STEP 2 — CITATION: Select the chunks (by index) that support your reasoning. Rate each chunk's relevance 0.0-1.0.

Respond in EXACTLY this JSON format (no markdown fences, no extra text):
{
  "reasoning": "Your 2-3 sentence explanation...",
  "cited_chunks": [
    {
      "chunk_index": 0,
      "relevance_score": 0.95,
      "justification": "Contains the key requirement about..."
    }
  ]
}

---
QUERY: Risk area: {risk_area}. Urgency: {urgency}.

CHUNKS:
{chunk_context}
---
```

---

### 3.4 Database Migratie (`scripts/migrations/add_trust_columns.py`)

**Schema versie:** 3 (huidige is 2).

**Wijzigingen:**

1. **`raw_chunks` tabel** wordt uitgebreid met:
   - `retriever_version TEXT DEFAULT 'bm25-v1'` — versie van de retrieval-strategie
   - `chunking_version TEXT DEFAULT 'sentence-v1'` — versie van de chunking-strategie

2. **Migratie is idempotent** — controleert per kolom of deze al bestaat.

**Upgrade-pad:**
- Bij migratie van v2 → v3: voeg de twee kolommen toe aan `raw_chunks`.
- Bestaande rows krijgen de default-waarden (`'bm25-v1'`, `'sentence-v1'`).
- Geen data-verlies; alle bestaande chunks blijven intact.
- `SCHEMA_VERSION` constante wordt bijgewerkt naar `3`.

**CLI-interface (ongewijzigd):**
```bash
python scripts/migrations/add_trust_columns.py [--dry-run] [--db PATH]
```

**Nieuwe functie-signaturen:**

```python
SCHEMA_VERSION = 3

def _apply_migration(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    """Apply migration to current SCHEMA_VERSION. Idempotent."""
```

---

### 3.5 Documentatie (`docs/TRUST_LAYER.md`)

Max 500 woorden. Bevat:
1. Architectuur-diagram (ASCII, zie §2).
2. Voorbeeld citation chain (JSON).
3. Uitleg groundedness score-berekening.
4. Versie-strategie voor chunking en retrieval.

---

## 4. JSON-schema's

### 4.1 `citation_sources` (kolom `updates.citation_sources`, TEXT)

**Schema:** JSON array van citation-objecten.

```json
[
  {
    "chunk_id": 42,
    "chunk_index": 0,
    "update_id": 7,
    "source_file": "data/raw/eba/20240315_dora_guidelines.pdf",
    "relevance_score": 0.92,
    "char_start": 0,
    "char_end": 2847,
    "chunk_text_preview": "Financial institutions shall implement..."
  }
]
```

| Veld | Type | Verplicht | Beschrijving |
|-------|------|-----------|--------------|
| `chunk_id` | integer | ✅ | Primary key in `raw_chunks` |
| `chunk_index` | integer | ✅ | Volgnummer binnen document |
| `update_id` | integer | ✅ | FK naar `updates.id` |
| `source_file` | string | ✅ | Pad naar bronbestand |
| `relevance_score` | float | ✅ | 0.0–1.0 (BM25 of LLM-assigned) |
| `char_start` | integer | ✅ | Start byte-offset in originele tekst |
| `char_end` | integer | ✅ | Eind byte-offset |
| `chunk_text_preview` | string | ✅ | Eerste 200 chars van chunk |

**Lege waarde:** `"[]"` (lege JSON array) als er geen citations zijn — **nooit NULL of lege string**.

### 4.2 `reasoning_chain` (kolom `updates.reasoning_chain`, TEXT)

**Schema:** JSON object.

```json
{
  "steps": [
    {
      "step": "retrieval",
      "description": "BM25 retrieval over 12 chunks, top-5 selected",
      "timestamp": "2026-09-06T07:30:00Z",
      "details": {
        "query": "Risk area: Cybersecurity. Urgency: Urgent.",
        "chunks_searched": 12,
        "chunks_returned": 5,
        "retriever_version": "bm25-v1"
      }
    },
    {
      "step": "cited_reasoning",
      "description": "LLM evaluated relevance of retrieved chunks",
      "timestamp": "2026-09-06T07:30:01Z",
      "details": {
        "chunks_cited": [0, 2, 4],
        "reasoning_text": "Chunks 0, 2, and 4 contain the key..."
      }
    },
    {
      "step": "summarization",
      "description": "Summary generated from 3 cited chunks",
      "timestamp": "2026-09-06T07:30:02Z",
      "details": {
        "input_chunk_ids": [42, 44, 46],
        "summary_length": 187
      }
    },
    {
      "step": "veracity",
      "description": "Groundedness score computed",
      "timestamp": "2026-09-06T07:30:03Z",
      "details": {
        "score": 0.85,
        "explanation": "Summary accurately reflects source requirements."
      }
    }
  ],
  "version": "trust-layer-v1"
}
```

| Veld | Type | Beschrijving |
|-------|------|--------------|
| `steps` | array | Geordende lijst van verwerkingsstappen |
| `steps[].step` | string | `"retrieval"`, `"cited_reasoning"`, `"summarization"`, `"veracity"` |
| `steps[].description` | string | Menselijke beschrijving |
| `steps[].timestamp` | string | ISO 8601 UTC |
| `steps[].details` | object | Stap-specifieke metadata |
| `version` | string | Trust layer versie (bijv. `"trust-layer-v1"`) |

**Lege waarde:** `'{"steps": [], "version": "trust-layer-v1"}'` als trust layer niet gedraaid heeft.

---

## 5. Testplan — 18 Tests

### 5.1 Retrieval Tests (5 tests) — `tests/test_retrieval.py`

| # | Testnaam | Input | Verwacht gedrag |
|---|----------|-------|-----------------|
| R1 | `test_chunk_text_creates_chunks` | raw_text van 1200 woorden, update_id=1 | ≥3 chunks aangemaakt in `raw_chunks`; elk heeft `chunk_index`, `char_start`, `char_end`, `retriever_version='bm25-v1'`, `chunking_version='sentence-v1'` |
| R2 | `test_chunk_text_empty_input` | raw_text="" | Retourneert lege lijst; geen rows in DB |
| R3 | `test_retrieve_chunks_single_document` | 2 updates gechunked (5 chunks totaal), query="cybersecurity mandatory", `update_id=1` | Alleen chunks van update_id=1; gesorteerd op relevance score (desc); elke chunk heeft `score` veld |
| R4 | `test_retrieve_chunks_cross_document` | 3 updates gechunked (15 chunks totaal), query="DORA compliance", `update_id=None` | Chunks van **meerdere** update_ids in resultaat; top_k gerespecteerd; scores in [0.0, ∞) |
| R5 | `test_retrieve_chunks_deterministic` | Zelfde query 2× uitgevoerd op identieke DB | Beide runs retourneren identieke chunk IDs in identieke volgorde |

### 5.2 Veracity Tests (5 tests) — `tests/test_veracity.py`

| # | Testnaam | Input | Verwacht gedrag |
|---|----------|-------|-----------------|
| V1 | `test_score_groundedness_returns_dict` | cited_texts=["chunk1", "chunk2"], summary="Test summary" | Return type is dict met keys: `score`, `explanation`, `model`, `chunks_evaluated` |
| V2 | `test_score_groundedness_range` | Identieke source en summary (perfect match) | `score` in [0.0, 1.0]; bij perfecte match ≥ 0.7 |
| V3 | `test_score_groundedness_contradiction` | Source zegt "X is verplicht", summary zegt "X is optioneel" | `score` < 0.5 (lage groundedness) |
| V4 | `test_score_groundedness_caching` | Twee identieke calls met conn | Tweede call retourneert cached resultaat; `ollama_cache` tabel bevat entry; cache key is deterministisch |
| V5 | `test_score_groundedness_llm_unavailable` | Ollama gemocked als falend | Retourneert `score=0.5, explanation="default (LLM unavailable or parse error)"` zonder exceptie |

### 5.3 Process Updates Tests (5 tests) — `tests/test_process_updates.py`

| # | Testnaam | Input | Verwacht gedrag |
|---|----------|-------|-----------------|
| P1 | `test_process_file_populates_trust_fields` | Geldig HTML-bestand, trust layer enabled | `citation_sources` is geldige JSON array; `reasoning_chain` is geldige JSON object met `steps`; `groundedness_score` is float in [0.0, 1.0]; `chunk_count` > 0 |
| P2 | `test_process_file_citation_sources_schema` | Geslaagde verwerking | Elk element in `citation_sources` heeft verplichte velden: `chunk_id`, `chunk_index`, `update_id`, `source_file`, `relevance_score`, `char_start`, `char_end`, `chunk_text_preview` |
| P3 | `test_process_file_reasoning_chain_schema` | Geslaagde verwerking | `reasoning_chain.steps` bevat minimaal entries voor `"retrieval"` en `"summarization"`; elke stap heeft `step`, `description`, `timestamp`, `details`; root heeft `version` |
| P4 | `test_process_file_summary_traceable_to_chunks` | Document met bekende inhoud | De gegenereerde summary bevat **geen** kale referentiecodes zoals "REF-001"; inhoud wordt ondersteund door ten minste één cited chunk |
| P5 | `test_process_file_trust_layer_failure_graceful` | chunk_text() gooit exception | Bestand wordt toch verwerkt (success=True); trust velden zijn `"[]"`, `'{"steps": [], "version": "trust-layer-v1"}'`, `NULL`, `0`; geen crash |

### 5.4 Migratie Tests (3 tests) — `tests/test_migrations.py`

| # | Testnaam | Input | Verwacht gedrag |
|---|----------|-------|-----------------|
| M1 | `test_migration_v2_to_v3_adds_columns` | DB met raw_chunks zonder `retriever_version`/`chunking_version` | Na migratie: beide kolommen aanwezig; `PRAGMA table_info(raw_chunks)` bevat ze |
| M2 | `test_migration_preserves_existing_data` | DB met 10 bestaande raw_chunks rows | Na migratie: alle 10 rows intact; bestaande rows hebben default versie-waarden |
| M3 | `test_migration_idempotent` | Migratie 2× uitgevoerd op dezelfde DB | Tweede run is een no-op; geen error; schema versie blijft 3 |

---

## 6. Aanbevelingen voor wijzigingen t.o.v. bestaande code

### 6.1 `scripts/retrieval.py`

| # | Aanbeveling | Prioriteit | Rationale |
|---|-------------|-----------|-----------|
| 1 | **`retrieve_chunks()`: maak `update_id` optioneel** (`int \| None = None`) | 🔴 Kritiek | Cross-document retrieval is de kern van de bug-fix; de huidige signatuur dwingt single-document zoeken af |
| 2 | **Voeg `score` toe aan elk geretourneerd chunk-dict** | 🔴 Kritiek | Zonder score is er geen traceerbaarheid van relevance ranking |
| 3 | **Voeg `retriever_version` en `chunking_version` toe aan chunk-dicts** | 🟡 Hoog | Nodig voor reproduceerbaarheid en debugging |
| 4 | **Maak `_tokenise()` deterministisch** (sorteer na dedup) | 🟡 Hoog | Voorkomt niet-deterministische BM25-scores bij gelijke term-frequenties |
| 5 | **Voeg `TOP_K_DEFAULT` toe aan module-niveau configuratie** | 🟢 Laag | Maakt testen eenvoudiger |

### 6.2 `scripts/veracity.py`

| # | Aanbeveling | Prioriteit | Rationale |
|---|-------------|-----------|-----------|
| 6 | **Wijzig return type van `float` naar `dict`** | 🔴 Kritiek | De opdracht vereist score + verklaring; float alleen is onvoldoende |
| 7 | **Wijzig `cited_text: str` naar `cited_texts: list[str]`** | 🟡 Hoog | Behoudt granulariteit van individuele chunks; intern joinen met scheidingsteken |
| 8 | **Voeg `chunks_evaluated` toe aan return dict** | 🟡 Hoog | Traceerbaarheid: hoeveel bron-chunks zijn meegenomen in de beoordeling |
| 9 | **Maak de cache-key deterministisch** via `json.dumps(sorted(...))` | 🟡 Hoog | Voorkomt cache-misses door volgorde-variaties in chunk-lijsten |

### 6.3 `scripts/process_updates.py`

| # | Aanbeveling | Prioriteit | Rationale |
|---|-------------|-----------|-----------|
| 10 | **Extraheer trust layer logica naar `_run_trust_layer()`** | 🔴 Kritiek | Nu inline in `_process_file_impl()` — ontestbaar en te complex; een aparte functie maakt unit tests mogelijk |
| 11 | **`generate_summary()` moet `cited_chunk_texts` accepteren** | 🔴 Kritiek | De "sloppy summaries" bug ontstaat doordat de summary over de volledige tekst gaat in plaats van over de cited chunks |
| 12 | **Valideer `citation_sources` als JSON vóór UPDATE** | 🟡 Hoog | Nu wordt raw LLM-output direct opgeslagen; valideer tegen het schema en fallback naar `"[]"` bij parse-fout |
| 13 | **Voeg `quality_failed` check toe vóór trust layer** | 🟡 Hoog | Bestaande code heeft een quality gate, maar de trust layer draait alsnog op edge cases; skip trust layer als quality gate faalt |
| 14 | **Gebruik `json.dumps()` met `ensure_ascii=False` voor alle JSON-velden** | 🟢 Laag | Behoudt leesbaarheid van niet-ASCII teksten |

### 6.4 `scripts/migrations/add_trust_columns.py`

| # | Aanbeveling | Prioriteit | Rationale |
|---|-------------|-----------|-----------|
| 15 | **Bump `SCHEMA_VERSION` naar 3** | 🔴 Kritiek | Nieuwe kolommen vereisen versie-increment |
| 16 | **Voeg `retriever_version` en `chunking_version` toe aan `raw_chunks`** | 🔴 Kritiek | Kern vereiste van de opdracht |
| 17 | **Gebruik `DEFAULT` waarden bij `ALTER TABLE ADD COLUMN`** | 🟡 Hoog | Bestaande rows krijgen automatisch de juiste defaults |
| 18 | **Log het aantal gemigreerde rows** | 🟢 Laag | Operationele inzichtelijkheid |

---

## 7. Randvoorwaarden

1. **Python 3.11+** — geen wijziging.
2. **`rank-bm25`** is al in `pyproject.toml` dependencies — geen nieuwe dependency nodig.
3. **Alle nieuwe kolommen zijn backwards compatibel** — bestaande code die ze niet leest blijft werken.
4. **Trust layer failure mag NOOIT de hoofdflow blokkeren** — proces moet altijd doorgaan met NULL/lege trust velden.
5. **LLM-temperature voor veracity: 0.0** (strikt deterministisch); voor reasoning: 0.1 (minimale variatie toegestaan).
6. **Alle JSON-velden in de DB zijn TEXT kolommen** met JSON-serialized inhoud — SQLite heeft geen native JSON type nodig.
7. **Bestaande tests** (`test_veracity.py`, `test_process_updates.py`, `test_integration.py`) moeten blijven slagen na aanpassingen — backwards compatibility van publieke functies waar mogelijk.

---

## 8. Acceptatiecriteria

| # | Criterium | Verificatie |
|---|-----------|-------------|
| 1 | Cross-document retrieval werkt | Test R4 slaagt |
| 2 | Elke summary is traceerbaar naar chunks | Test P4 slaagt; `citation_sources` is nooit leeg bij succesvolle trust layer |
| 3 | Groundedness score heeft verklaring | Test V1 slaagt; return type is dict |
| 4 | Migratie is backwards compatibel | Tests M1–M3 slagen |
| 5 | Geen "sloppy summaries" meer | Test P4: geen referentiecodes in output |
| 6 | Alle 18 tests slagen | `pytest tests/ -v` toont 18 nieuwe + bestaande tests passed |
| 7 | Trust layer failure is graceful | Test P5 slaagt |

---

*Einde specificatie — klaar voor Stap 2: Code (Lead Dev).*
