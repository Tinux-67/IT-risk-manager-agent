# 🛡️ IT Risk Manager Agent

[![Test](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/test.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/test.yml)
[![Lint](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/lint.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/lint.yml)
[![Docker Build](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/docker-build.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/docker-build.yml)
[![codecov](https://codecov.io/github/Tinux-67/IT-risk-manager-agent/graph/badge.svg?token=MIDSV8D4B2)](https://codecov.io/github/Tinux-67/IT-risk-manager-agent)
[![Pre-commit](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/pre-commit.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

> **Automated regulatory intelligence for IT risk management — local-first, open-source, zero vendor lock-in.**

---

## Introduction

IT Risk Manager Agent automatically monitors regulatory publications from the **European Banking Authority (EBA)** and the **Monetary Authority of Singapore (MAS)**, extracts key risk areas and urgency levels, and surfaces actionable intelligence — all running locally on your own machine.

### Why This Matters

Tracking regulatory updates across jurisdictions is slow, manual, and expensive. Compliance teams scan PDFs, cross-reference risk categories, and summarize changes by hand — work that's ripe for automation. The IT Risk Manager Agent replaces that manual dragnet with an automated pipeline: **scrape → process → analyze → alert** — in a single workflow that respects your privacy by keeping everything local.

### Key Highlights

- **Multi-regulator scrapers** — Fetches publications, consultations, and regulations from both EBA and MAS with SSRF protection built in.
- **Local LLM inference** — Processes extracted text through Ollama (Mistral-7B) to identify risk areas, determine urgency, and generate concise summaries. No API calls, no data leaving your machine.
- **Smart caching** — 24-hour LLM response cache and `@st.cache_resource`-backed SQLite database keep repeated queries fast without stale data.
- **Role-aware alerts** — Generate tailored summaries for workfloor, management, or C-level audiences, with optional urgency filtering.
- **Streamlit dashboard** — Browse, filter, and search processed updates through a clean web UI.

### Tech Stack

**Python 3.11+** · **Streamlit** · **Ollama** (Mistral-7B) · **SQLite** · **Docker**

The architecture is modular and testable — 136 passing tests cover scrapers, app helpers, and integration workflows, with GitHub Actions keeping CI green across lint, test, Docker build, and pre-commit checks.

### Open Source, Local-First, Extensible

This project is Apache 2.0 licensed and built to be forked, customized, and extended. Want to add a new regulator? Drop in a scraper module. Prefer a different model? Swap the Ollama backend. The local-first design means zero vendor lock-in and no data exposure — your regulatory intelligence stays yours.

---

## Quick Start

Get up and running in five steps.

### Prerequisites

- **Python 3.11** or later
- **Ollama** installed and running ([ollama.com](https://ollama.com))
- **Git** for cloning the repository

### 1. Clone the Repository

```bash
git clone https://github.com/Tinux-67/IT-risk-manager-agent.git
cd IT-risk-manager-agent
```

### 2. Install Dependencies

```bash
pip install -e .
```

The package uses modern Python packaging (`pyproject.toml`). The `-e` flag installs it in editable mode, so changes to source files are reflected immediately.

### 3. Pull the Mistral Model

```bash
ollama pull mistral
```

This downloads Mistral-7B (~4 GB) for local LLM processing. You can use any Ollama-compatible model by setting the `OLLAMA_MODEL` environment variable later.

### 4. Initialize the Directory Structure

```bash
python -c "from config import Config; Config.init_dirs()"
```

This creates the `data/` and `logs/` directories that the agent uses at runtime.

### 5. Launch the Dashboard

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser. You'll see the dashboard with metrics, recent updates, and navigation to scrape, process, and generate alerts.

### Optional: Run with Docker

```bash
docker-compose up -d
```

This spins up the Streamlit app and an Ollama container with Mistral pre-loaded. Access the dashboard at **http://localhost:8501**.

---

## Usage

### Dashboard Overview

The Streamlit dashboard has four main pages:

| Page | What It Does |
|------|--------------|
| 🏠 **Overview** | Key metrics (total updates, urgent items, recent activity) and a filterable list of all processed updates |
| 🔍 **Detail View** | Full-text view of individual regulatory updates with summaries and risk classifications |
| 🚨 **Alert Generator** | Create audience-specific alerts for workfloor, management, or C-level |
| 🔄 **Scrape & Process** | Run EBA and MAS scrapers with configurable limits, then process downloaded files through the LLM pipeline |

### Scraping Regulatory Updates

From the **Scrape & Process** page or the command line:

```bash
# Scrape EBA publications (limit to 10 results, 1s delay between requests)
python scripts/scrape_eba.py --limit 10 --delay 1.0

# Scrape MAS publications
python scripts/scrape_mas.py --limit 10 --delay 1.0

# Process all downloaded files through the LLM pipeline
python scripts/process_updates.py --all
```

### Generating Alerts

```bash
# Workfloor alerts for the last 7 days
python scripts/generate_alerts.py --days 7 --audience workfloor

# Management summary for the last 30 days
python scripts/generate_alerts.py --days 30 --audience management

# C-level brief — urgent items only
python scripts/generate_alerts.py --days 30 --audience c-level --urgent-only
```

### Database Backup

```bash
python scripts/backup_db.py
```

Creates a timestamped backup of the SQLite database in a `backups/` directory.

---

## Features

### 🌐 Multi-Regulator Coverage

Dedicated scrapers for two major financial regulators:

- **EBA** (European Banking Authority) — Publications, consultations, guidelines, and technical standards
- **MAS** (Monetary Authority of Singapore) — Publications, public consultations, and regulations/notices

Each scraper respects rate limits, sanitizes filenames, and supports extensible CSS selectors for different page layouts.

### 🧠 Local LLM Processing

All text analysis runs on your hardware:

- **Mistral-7B** via Ollama for summarization, risk area classification, and urgency assessment
- **Full offline operation** — no internet required after scraping
- **Configurable models** — set `OLLAMA_MODEL` to any model you have pulled in Ollama
- **Temperature** locked to 0.1 for deterministic, reproducible outputs

### 📊 Streamlit Dashboard

A responsive web interface for day-to-day operations:

- **At-a-glance metrics** — total updates, urgent counts, high-priority items, and 7-day activity
- **Filtering** — by risk area, urgency level, and date range
- **Role-based alerting** — UI-driven alert generation for different audiences
- **Scrape controls** — run scrapers and process files directly from the dashboard

### 🔒 Security-First Design

- **SSRF protection** — URL allowlisting restricts scrapers to `eba.europa.eu` and `mas.gov.sg` domains only
- **Non-root Docker user** — container runs as `appuser` (UID 1000)
- **No data egress** — LLM processing stays local, regulatory data never leaves your environment
- **Input validation** — dashboard inputs are validated before passing to subprocesses

### ⚡ Performance

- **24-hour LLM cache** — SHA-256 keyed prompt/response cache in SQLite prevents redundant Ollama calls
- **Streamlit `@st.cache_data`** — 5-minute TTL on database queries for instant dashboard updates
- **Thread-safe processing** — `process_updates.py` uses thread-local database connections for parallel document ingestion
- **Multi-format ingestion** — handles PDF, HTML, and Excel (`.xlsx`) documents

### 🧩 Risk Area Taxonomy

The agent classifies updates into 16 risk areas:

| | | | |
|---|---|---|---|
| IT Risk Management | Cybersecurity | AI Risk | Compliance |
| Governance | Operational Risk | Data Protection | Third-Party Risk |
| Cloud Computing | DORA | Financial Stability | Resolution Planning |
| Capital Requirements | Liquidity Risk | Market Risk | Credit Risk |

---

## Architecture

```
IT-risk-manager-agent/
├── app.py                        # Streamlit dashboard (entry point)
├── config.py                     # Central configuration (env vars, paths, constants)
├── pyproject.toml                # Package metadata, dependencies, tool config
├── Dockerfile                    # Multi-stage production Docker image
├── docker-compose.yml            # App + Ollama service orchestration
│
├── scripts/
│   ├── scrape_eba.py             # EBA regulatory scraper
│   ├── scrape_mas.py             # MAS regulatory scraper
│   ├── process_updates.py        # Document processing (PDF/HTML/XLSX → SQLite)
│   ├── generate_alerts.py        # Audience-specific alert engine
│   ├── backup_db.py              # Database backup utility
│   ├── llm_utils.py              # Shared Ollama interface with 24h caching
│   ├── logging_config.py         # Idempotent centralized logging (loguru)
│   └── scraping_utils.py         # Shared scraping utilities + SSRF protection
│
├── tests/
│   ├── conftest.py               # Shared fixtures and mocks
│   ├── test_scrape_eba.py        # EBA scraper unit tests
│   ├── test_scrape_mas.py        # MAS scraper unit tests
│   ├── test_process_updates.py   # Document processing + risk classification
│   ├── test_generate_alerts.py   # Alert formatting + audience logic
│   ├── test_app.py               # Dashboard helper functions
│   └── test_integration.py       # End-to-end workflows
│
├── data/
│   ├── raw/eba/                  # Downloaded EBA publications (PDF/HTML)
│   ├── raw/mas/                  # Downloaded MAS publications
│   └── processed/                # regulatory_updates.db (SQLite)
│
└── .github/workflows/
    ├── test.yml                  # CI: pytest with coverage
    ├── lint.yml                  # CI: ruff, black, isort, mypy
    ├── docker-build.yml          # CI: Docker image build verification
    └── pre-commit.yml            # CI: pre-commit hook validation
```

### Data Flow

```
EBA/MAS Website
      │
      ▼
[ scrape_eba.py / scrape_mas.py ]  ← scraping_utils.py (SSRF guard)
      │
      ▼
data/raw/eba/*.pdf, *.html, *.xlsx
      │
      ▼
[ process_updates.py ]            ← llm_utils.py (Ollama + cache)
      │                              logging_config.py (loguru)
      ▼
data/processed/regulatory_updates.db
      │
      ├──► [ app.py ]             Streamlit dashboard
      │
      └──► [ generate_alerts.py ] CLI alert generation (workfloor / mgmt / C-level)
```

### Design Principles

- **Separation of concerns** — Scraping, processing, and presentation are independent layers
- **Centralized utilities** — `scraping_utils.py`, `llm_utils.py`, and `logging_config.py` prevent code duplication across modules
- **Config-driven** — All paths, URLs, and thresholds live in `config.py` with environment variable overrides
- **Idempotent operations** — Logging setup and cache initialization are safe to call multiple times

---

## Testing

The project maintains **136 passing tests** with 100% CI pass rate.

### Test Structure

| Test File | Coverage |
|-----------|----------|
| `test_scrape_eba.py` | EBA scraper logic, URL construction, date extraction |
| `test_scrape_mas.py` | MAS scraper logic, regulatory vs consultation handling |
| `test_scraping_utils.py` | SSRF validation, filename sanitization, link extraction, file download |
| `test_process_updates.py` | PDF/HTML/Excel parsing, risk area categorization, urgency assessment, database operations |
| `test_generate_alerts.py` | Alert formatting per audience, urgency filtering, LLM integration |
| `test_app.py` | Dashboard helper functions, DB queries, cache behavior |
| `test_integration.py` | End-to-end pipeline: HTML ingestion → SQLite write → urgency/risk classification → alert generation |

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests with coverage
pytest tests/ -v

# Run a specific test file
pytest tests/test_scrape_eba.py -v

# Run tests matching a keyword
pytest tests/ -v -k "integration"

# Generate HTML coverage report
pytest tests/ --cov=scripts --cov-report=html
open htmlcov/index.html
```

### What CI Checks

Every push triggers:

- **Tests** — `pytest tests/` with coverage reporting to Codecov
- **Lint** — `ruff check`, `black --check`, `isort --check-only`, `mypy`
- **Docker Build** — Verifies the multi-stage Docker image builds cleanly
- **Pre-commit** — Validates that all pre-commit hooks pass

---

## Configuration

All settings are controlled through environment variables. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `mistral` | Model name for LLM inference |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `DB_PATH` | `data/processed/regulatory_updates.db` | SQLite database location |
| `DATA_DIR` | `./data` | Root directory for all data |
| `DEFAULT_DELAY` | `1.0` | Seconds between scraper requests |
| `USER_AGENT` | Mozilla/5.0 ... | HTTP User-Agent header |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_ROTATION` | `1 day` | Log file rotation interval |
| `LOG_RETENTION` | `7 days` | How long to keep rotated logs |

### Customizing the Model

To use a different Ollama model:

```bash
# In .env
OLLAMA_MODEL=llama3.2

# Or when running a script
OLLAMA_MODEL=phi3 python scripts/generate_alerts.py --all
```

### Adding a New Risk Area

1. Add the area to `Config.RISK_AREAS` in `config.py`:
   ```python
   RISK_AREAS: list[str] = [
       # ... existing areas ...
       "Quantum Computing Risk",  # your new area
   ]
   ```
2. The LLM will automatically pick it up for classification (the prompt includes all categories).
3. Update the prompt template in `scripts/process_updates.py` if you want more specific classification guidance.

### Adding a New Regulator

1. Create a new scraper in `scripts/scrape_YOURREGULATOR.py` following the pattern in `scrape_eba.py`.
2. Add the regulator's domains to `_ALLOWED_HOSTNAMES` in `scripts/scraping_utils.py`:
   ```python
   _ALLOWED_HOSTNAMES = {
       "eba.europa.eu", "www.eba.europa.eu",
       "mas.gov.sg", "www.mas.gov.sg",
       "your-regulator.gov", "www.your-regulator.gov",  # add here
   }
   ```
3. Add a directory in `config.py` for raw data storage.
4. Add a test file in `tests/`.
5. Reuse `scraping_utils.py` for SSRF protection, filename generation, and file downloading.

---

## Contributing

We welcome contributions — bug fixes, new scrapers, features, and documentation improvements.

### Development Setup

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/Tinux-67/IT-risk-manager-agent.git
cd IT-risk-manager-agent
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Verify everything works
pytest tests/ -v
ruff check .
black --check .
isort --check-only .
mypy scripts/
```

### Pre-Commit Hooks

The project uses pre-commit to enforce code quality at commit time:

- **ruff** — Linting and auto-fixes
- **black** — Code formatting (100 character line length)
- **isort** — Import sorting (black profile)
- **Trailing whitespace / EOF** — Whitespace hygiene

### Branch Strategy

1. **Fork** the repository
2. Create a **feature branch**: `git checkout -b feature/your-feature-name`
3. Make your changes and ensure tests pass: `pytest tests/ -v`
4. Run the full quality check: `ruff check . && black --check . && isort --check-only . && mypy scripts/`
5. **Commit** with a descriptive message
6. **Push** and open a Pull Request against `main`

### Code Style

- **Line length**: 100 characters (configured in `pyproject.toml`)
- **Type hints**: All public functions must have type annotations (`mypy` enforces this)
- **Docstrings**: Google-style for all public functions
- **Imports**: `isort` handles ordering; `from config import Config` is the standard entry point
- **Logging**: Import `logger` from `loguru` and call `setup_logging()` once at the top of each entry point

### Running CI Checks Locally

```bash
# Full CI simulation
pytest tests/ --cov=scripts --cov-report=term-missing
ruff check .
black --check .
isort --check-only .
mypy scripts/
```

---

## License

Copyright 2025–2026 Martijn (Tinux-67)

Licensed under the **Apache License, Version 2.0** (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

---

<p align="center">
  <sub>Built with ❤️ for compliance teams who value their data sovereignty.</sub>
</p>
