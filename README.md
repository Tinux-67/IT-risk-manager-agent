# Regulatory Agent PoC

A **CLI-based agent** for tracking and interpreting EBA regulations, powered by **Mistral-7B** and **SQLite**.

[![Test](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/test.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/test.yml)
[![Lint](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/lint.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/lint.yml)
[![Docker Build](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/docker-build.yml/badge.svg)](https://github.com/Tinux-67/IT-risk-manager-agent/actions/workflows/docker-build.yml)
[![Codecov](https://codecov.io/gl/Tinux-67/IT-risk-manager-agent/branch/main/graph/badge.svg)](https://codecov.io/gl/Tinux-67/IT-risk-manager-agent)

## Scope
- **Regulator**: EBA (European Banking Authority)
- **Focus Areas**: IT Risk Management, Cybersecurity, AI Risk
- **Output**: CLI alerts for workfloor, management, and C-level audiences.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up Ollama and Mistral-7B:
   ```bash
   ollama pull mistral
   ```
3. Run the scripts:
   ```bash
   python scripts/scrape_eba.py
   python scripts/process_updates.py
   python scripts/generate_alerts.py --days 7
   ```

## Folder Structure
- `data/raw/eba/`: Raw regulatory updates (PDFs/HTML).
- `data/processed/`: SQLite database with processed updates.
- `scripts/`: Python scripts for scraping, processing, and generating alerts.

## Development

### Running Tests Locally
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests with coverage
pytest tests/ --cov=scripts -v

# Run linting
ruff check scripts/ tests/ app.py config.py
black --check scripts/ tests/ app.py config.py
isort --check-only scripts/ tests/ app.py config.py
```

### Docker
```bash
# Build and run with Docker Compose (includes Ollama)
docker-compose up -d

# Access Streamlit at http://localhost:8501
```

---

**Note**: Codecov token updated and retesting integration. Last updated: 2026-07-24.

## License
MIT
