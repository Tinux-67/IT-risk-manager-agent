# IT Risk Manager Agent

A **CLI and web-based agent** for tracking and interpreting EBA and MAS regulations, powered by **Mistral-7B** and **SQLite**.

[![Test](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/test.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/test.yml)
[![Lint](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/lint.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/lint.yml)
[![Docker Build](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/docker-build.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/docker-build.yml)
[![codecov](https://codecov.io/github/Tinux-67/IT-risk-manager-agent/graph/badge.svg?token=MIDSV8D4B2)](https://codecov.io/github/Tinux-67/IT-risk-manager-agent)

## ✅ Status: All Badges Green
All CI/CD workflows are currently passing:
- ✅ **Tests** - All unit tests pass
- ✅ **Lint** - Code passes ruff, black, and isort checks
- ✅ **Docker Build** - Container builds successfully

## Scope
- **Regulators**: EBA (European Banking Authority) and MAS (Monetary Authority of Singapore)
- **Focus Areas**: IT Risk Management, Cybersecurity, AI Risk, Compliance, Governance, Operational Risk, Data Protection, Third-Party Risk, Cloud Computing, DORA
- **Output**: CLI alerts for workfloor, management, and C-level audiences

## Features
- **Web Scraping**: Automatically scrape regulatory updates from EBA and MAS websites with SSRF protection
- **LLM Processing**: Use Mistral-7B (via Ollama) for intelligent summarization and categorization with 24-hour cached responses
- **Alert Generation**: Generate audience-specific alerts (workfloor, management, C-level)
- **Database Storage**: SQLite database for structured storage of regulatory updates with optimized indexing
- **Streamlit Dashboard**: Web interface for viewing and filtering updates with single-query optimization
- **Excel Support**: Extract and process text from Excel (.xlsx) documents
- **Thread-Safe Processing**: Parallel document processing with thread-local database connections

## Setup

### Prerequisites
- Python 3.11+
- Ollama (for LLM functionality)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Tinux-67/IT-risk-manager-agent.git
   cd IT-risk-manager-agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Ollama and Mistral-7B:
   ```bash
   ollama pull mistral
   ```

4. Initialize directories:
   ```bash
   python -c "from config import Config; Config.init_dirs()"
   ```

## Usage

### Scrape and Process Updates
```bash
# Scrape EBA updates
python scripts/scrape_eba.py --limit 10 --delay 1.0

# Scrape MAS updates
python scripts/scrape_mas.py --limit 10 --delay 1.0

# Process all scraped files (including Excel documents)
python scripts/process_updates.py --all
```

### Generate Alerts
```bash
# Generate alerts for the last 7 days
python scripts/generate_alerts.py --days 7 --audience workfloor

# Generate alerts for management
python scripts/generate_alerts.py --days 30 --audience management

# Generate alerts for C-level
python scripts/generate_alerts.py --days 30 --audience c-level --urgent-only
```

### Run Streamlit Dashboard
```bash
streamlit run app.py
```
Access the dashboard at http://localhost:8501

## Architecture

The codebase follows a modular architecture with centralized shared utilities:

### Core Modules
- **`scripts/llm_utils.py`** — Centralized Ollama LLM interface with 24-hour response caching using SHA-256 keys. Replaces duplicated LLM logic across `generate_alerts.py` and `process_updates.py`.
- **`scripts/logging_config.py`** — Idempotent centralized logging setup called once per entry point. Replaces scattered `logger.add()` calls throughout the codebase.
- **`scripts/scraping_utils.py`** — Shared web scraping utilities with SSRF protection via URL allowlisting. Used by `scrape_eba.py` and `scrape_mas.py`.

### Entry Points
- `scripts/scrape_eba.py` — EBA regulatory scraper
- `scripts/scrape_mas.py` — MAS regulatory scraper
- `scripts/process_updates.py` — Document processing pipeline (PDF, HTML, Excel) with thread-safe SQLite operations
- `scripts/generate_alerts.py` — Alert generation engine with audience-specific formatting
- `app.py` — Streamlit dashboard with optimized query performance

## Folder Structure
```
.
├── data/
│   ├── raw/
│   │   ├── eba/           # Raw EBA regulatory updates (PDFs/HTML)
│   │   └── mas/           # Raw MAS regulatory updates
│   └── processed/         # SQLite database with processed updates
├── scripts/
│   ├── scrape_eba.py              # Scrape EBA publications
│   ├── scrape_mas.py              # Scrape MAS publications
│   ├── process_updates.py         # Process raw updates into database
│   ├── generate_alerts.py         # Generate audience-specific alerts
│   ├── create_github_issues.py    # Create GitHub issues from templates
│   ├── llm_utils.py               # Shared Ollama interface with caching
│   ├── logging_config.py          # Centralized logging setup
│   └── scraping_utils.py          # Shared scraping utilities with SSRF protection
├── tests/                 # Unit tests
├── app.py                # Streamlit web interface
├── config.py             # Central configuration
└── README.md
```

## Security

### SSRF Protection
The codebase includes Server-Side Request Forgery (SSRF) protection through URL allowlisting:

- **Allowed Domains**: `eba.europa.eu`, `mas.gov.sg`
- **Implementation**: `scripts/scraping_utils.py` includes `is_allowed_url()` validation
- **Usage**: All web scraping operations validate URLs before making HTTP requests

## Development

### Running Tests Locally
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest tests/ --cov=scripts -v

# Run specific test file
pytest tests/test_scrape_eba.py -v
```

### Linting and Formatting
```bash
# Run linting
ruff check .

# Format code with black
black .

# Sort imports
isort .

# Check all formatting
ruff check . && black --check . && isort --check-only .
```

### Docker
```bash
# Build and run with Docker Compose (includes Ollama)
docker-compose up -d

# Access Streamlit at http://localhost:8501

# View logs
docker-compose logs -f
```

## Configuration
Environment variables can be set in a `.env` file:
```bash
# Database settings
DB_PATH=./data/processed/regulatory_updates.db
DATA_DIR=./data

# Scraping settings
DEFAULT_DELAY=1.0
USER_AGENT="Mozilla/5.0 ..."

# Ollama settings
OLLAMA_MODEL=mistral
OLLAMA_HOST=http://localhost:11434

# Logging settings
LOG_LEVEL=INFO
LOG_ROTATION=1 day
LOG_RETENTION=7 days
```

## Risk Areas
The following risk areas are tracked:
- IT Risk Management
- Cybersecurity
- AI Risk
- Compliance
- Governance
- Operational Risk
- Data Protection
- Third-Party Risk
- Cloud Computing
- Digital Operational Resilience (DORA)
- Financial Stability
- Resolution Planning
- Capital Requirements
- Liquidity Risk
- Market Risk
- Credit Risk

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License
Apache 2.0

---

**Last Updated**: 2026-08-01
**Status**: All CI/CD workflows passing ✅
