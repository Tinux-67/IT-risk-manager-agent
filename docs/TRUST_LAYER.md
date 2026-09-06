# Trust Layer Architecture

The IT Risk Manager (ITRM) Trust Layer ensures that all LLM-generated summaries are **grounded in retrieved source text** with **cited evidence chains**. This document describes the architecture, components, and workflow.

---

## Overview

The Trust Layer addresses the "Sloppy Summary" bug where documents were being summarized with only reference codes (e.g., `EBA/ITS/2026/03`) instead of meaningful content. The solution implements a **Retrieval-Augmented Generation (RAG)** pipeline with veracity scoring.

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `retrieval.py` | `scripts/retrieval.py` | BM25/TF-IDF chunk retrieval |
| `veracity.py` | `scripts/veracity.py` | Groundedness scoring (0.0-1.0) |
| `process_updates.py` | `scripts/process_updates.py` | Integration point |
| `raw_chunks` table | SQLite DB | Stores chunked document text with versioning |

---

## Workflow

### 1. Document Processing Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      process_updates.py                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  File Ingestion                      Trust Layer                     │
│  ─────────────                      ────────────                     │
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐    │
│  │ Text         │───▶│ Chunk Text  │───▶│ Retrieve Relevant   │    │
│  │ Extraction   │    │ (chunk_text)│    │ Chunks              │    │
│  └─────────────┘    └─────────────┘    │ (retrieve_chunks)   │    │
│                                          └──────────┬────────────┘    │
│                                                 │                   │
│                                          ┌──────────▼────────────┐    │
│                                          │ Cited Reasoning Chain  │    │
│                                          │ (LLM with context)     │    │
│                                          └──────────┬────────────┘    │
│                                                 │                   │
│                                          ┌──────────▼────────────┐    │
│                                          │ Veracity Scoring       │    │
│                                          │ (score_groundedness)   │    │
│                                          └────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Database: updates table                                         │   │
│  │ - title, source_url, file_path, publication_date              │   │
│  │ - raw_text, summary, risk_area, urgency_level               │   │
│  │ - citation_sources (JSON), reasoning_chain, groundedness_score│   │
│  │ - chunk_count, is_processed                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. Step-by-Step Process

1. **Text Extraction**: Extract raw text from PDF/HTML/DOCX/Excel files
2. **Initial Classification**: Categorize risk area and urgency using LLM
3. **Summary Generation**: Generate initial summary (with retrieval context if available)
4. **Quality Gate**: Reject documents with empty/fallback content
5. **INSERT Record**: Store document in `updates` table to get `update_id`
6. **Chunking**: Split raw text into overlapping chunks (500 words, 50-word overlap)
   - Stored in `raw_chunks` table with `retriever_version` and `chunking_version`
7. **Retrieval**: Use BM25 to find top-5 most relevant chunks for the risk area
8. **Cited Reasoning**: LLM generates reasoning with cited chunk references
9. **Veracity Scoring**: Score how well the summary is grounded in cited text (0.0-1.0)
10. **UPDATE Record**: Store citation sources, reasoning chain, and groundedness score

---

## Database Schema

### `updates` Table (Trust Layer Columns)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-incrementing primary key |
| `citation_sources` | TEXT | JSON array of cited chunk references |
| `reasoning_chain` | TEXT | LLM-generated chain-of-thought reasoning |
| `groundedness_score` | REAL | Veracity score (0.0-1.0) |
| `chunk_count` | INTEGER | Number of chunks generated |

### `raw_chunks` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-incrementing primary key |
| `update_id` | INTEGER FK | References `updates(id)`, cascades on delete |
| `chunk_text` | TEXT | The actual text chunk |
| `char_start` | INTEGER | Character start position in original document |
| `char_end` | INTEGER | Character end position in original document |
| `source_file` | TEXT | Path to the source file |
| `chunk_index` | INTEGER | Sequential index of the chunk |
| `retriever_version` | TEXT | Version of the retriever (default: `'v1'`) |
| `chunking_version` | TEXT | Version of the chunking algorithm (default: `'v1'`) |
| `created_at` | TIMESTAMP | When the chunk was created |

### `schema_version` Table

| Column | Type | Description |
|--------|------|-------------|
| `version` | INTEGER PK | Schema version number |
| `applied_at` | TIMESTAMP | When the migration was applied |

---

## Migration Scripts

### `scripts/migrations/add_trust_columns.py` (Schema Version 2)

Adds the initial trust layer columns to the `updates` table:
- `citation_sources`
- `reasoning_chain`
- `groundedness_score`
- `chunk_count`

Also creates:
- `raw_chunks` table
- `schema_version` table

**Usage:**
```bash
python scripts/migrations/add_trust_columns.py [--dry-run] [--db PATH]
```

### `scripts/migrations/add_chunk_versions.py` (Schema Version 3)

Adds version columns to the `raw_chunks` table:
- `retriever_version` (default: `'v1'`)
- `chunking_version` (default: `'v1'`)

**Usage:**
```bash
python scripts/migrations/add_chunk_versions.py [--dry-run] [--db PATH]
```

---

## Configuration

### Chunking Parameters (in `retrieval.py`)

```python
CHUNK_WORD_SIZE = 500    # Words per chunk
CHUNK_WORD_OVERLAP = 50  # Overlapping words between consecutive chunks
TOP_K_DEFAULT = 5        # Number of chunks to retrieve
```

### Retrieval

- Uses **BM25Okapi** from `rank_bm25` package when available
- Falls back to **naive TF/IDF** (word overlap counting) if `rank_bm25` is not installed
- Tokenization: splits on non-alphanumeric characters, lowercases

### Veracity Scoring

- Uses a **dedicated LLM prompt** to score groundedness
- Score range: **0.0 to 1.0**
  - 0.0: Summary contradicts or fabricates information
  - 0.5: Summary is partially supported but has omissions
  - 1.0: Summary is fully and accurately derived from source
- Cached in `ollama_cache` table to avoid redundant LLM calls

---

## LLM Prompts

### Retrieval + Reasoning Prompt

```
You are a regulatory compliance expert. First, write your reasoning in <think>...</think> tags about which chunks are most relevant to the query and why.
Then return a JSON object with:
{
  "reasoning": "Your chain-of-thought reasoning about which chunks are relevant and why.",
  "cited_chunks": [
    {"chunk_text": "...", "char_start": 0, "char_end": 100, "source_file": "eba/foo.pdf"}
  ]
}

Context: the following chunks are from a regulatory document.
Chunks: {chunks}
Query: {query}
```

### Veracity Scoring Prompt

```
You are a factual accuracy evaluator. Your task is to assess whether a summary is faithfully grounded in the cited source text.

Rate the groundedness of the summary on a scale from 0.0 to 1.0:
  0.0 — the summary contradicts or fabricates information not present in the source
  0.5 — the summary is partially supported but contains omissions or inaccuracies
  1.0 — the summary is fully and accurately derived from the source

Respond with ONLY a single number between 0.0 and 1.0. No explanation, no units.

---
SOURCE:
{cited_text}
---
SUMMARY:
{summary}
---
SCORE:
```

---

## Testing

### Unit Tests

See `tests/test_citation_pipeline.py` for comprehensive tests:

- **`TestTokenise`**: Tokenization logic
- **`TestChunkText`**: Chunking functionality
- **`TestNaiveRetrieve`**: Fallback retrieval
- **`TestReasoningChainParsing`**: JSON parsing of LLM responses
- **`TestMigrationIdempotent`**: Schema migration idempotency
- **`TestTrustLayerIntegration`**: End-to-end trust layer integration

Run tests:
```bash
pytest tests/test_citation_pipeline.py -v
```

### Test Coverage

All trust layer components are covered by tests:
- Chunking with version columns
- Retrieval (BM25 and naive fallback)
- JSON parsing of cited reasoning
- Migration idempotency
- Integration with `process_updates.py`

---

## Deployment

### Prerequisites

```bash
pip install rank-bm25  # For BM25 retrieval (optional, has naive fallback)
pip install ollama    # For LLM integration
```

### Running Migrations

```bash
# Apply all migrations
python scripts/migrations/add_trust_columns.py
python scripts/migrations/add_chunk_versions.py

# Or with dry-run first
python scripts/migrations/add_trust_columns.py --dry-run
python scripts/migrations/add_chunk_versions.py --dry-run
```

### Processing Documents

The trust layer is **enabled by default** in `process_updates.py`. To process documents:

```bash
# Process all files
python scripts/process_updates.py --all

# Process specific source
python scripts/process_updates.py --source EBA
python scripts/process_updates.py --source MAS
```

---

## Monitoring

### Logs

The trust layer logs key events:

```
INFO: Chunked update_id={id} into {n} chunks
INFO: Trust layer done for {filename}: chunks={count}, groundedness={score}
WARNING: Veracity scoring failed for {filename}: {error}
ERROR: Trust layer failed for {filename}: {error}
```

### Quality Metrics

- **Chunk count**: Number of chunks generated per document
- **Groundedness score**: Average score across all documents
- **Citation coverage**: Percentage of documents with non-empty citations

---

## Future Enhancements

1. **BM25 Fine-tuning**: Adjust k1, b parameters for regulatory text
2. **Hybrid Retrieval**: Combine BM25 with semantic search (embeddings)
3. **Multi-document Retrieval**: Retrieve across all documents, not just per-document
4. **Confidence Thresholds**: Reject summaries below a configurable groundedness threshold
5. **Citation Visualization**: Generate HTML reports with highlighted citations
6. **Version Tracking**: Increment `retriever_version` and `chunking_version` on algorithm changes

---

## References

- [BM25Okapi Documentation](https://github.com/jina-ai/rank-bm25)
- [RAG Pattern](https://arxiv.org/abs/2005.11401)
- [Groundedness in LLM Evaluation](https://arxiv.org/abs/2305.14575)
