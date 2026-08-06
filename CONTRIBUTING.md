# Contributing

Thank you for your interest in contributing to the IT Risk Manager Agent!

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) or `pip` for dependency management
- Docker + Docker Compose (for full-stack testing)
- [pre-commit](https://pre-commit.com/)

### Setup

```bash
# Clone
git clone https://github.com/Tinux-67/IT-risk-manager-agent.git
cd IT-risk-manager-agent

# Install dependencies (including dev extras)
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### Branching

| Branch pattern | Purpose |
|---|---|
| `main` | Production-ready code |
| `feature/<name>` | New features |
| `fix/<name>` | Bug fixes |
| `phase<N>-<name>` | Milestone-scoped work |

Always branch off `main`:

```bash
git checkout main && git pull
git checkout -b feature/my-feature
```

### Code Style

This project uses:

- **[black](https://black.readthedocs.io/)** — code formatting (line length 100)
- **[ruff](https://docs.astral.sh/ruff/)** — linting (replaces flake8/isort)
- **[mypy](https://mypy.readthedocs.io/)** — static type checking
- **[isort](https://pycqa.github.io/isort/)** — import sorting

All checks run automatically via pre-commit. You can also run them manually:

```bash
black .
ruff check . --fix
mypy scripts/ app.py config.py
```

### Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=scripts --cov-report=term-missing

# Run a specific test file
pytest tests/test_scrape_mas.py -v
```

Tests live in `tests/`. Shared fixtures are in `tests/conftest.py`.

**Rules:**
- New features must include tests
- Bug fixes must include a regression test
- Target ≥ 80% coverage for new code

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add MAS scraper for notices
fix: correct urgency keyword matching
test: add integration tests for E2E workflow
docs: update ARCHITECTURE.md
perf: cache DB connection with @st.cache_resource
chore: update pyproject.toml dependencies
```

## Pull Requests

1. Open a PR against `main`
2. Fill in the PR description — what changed and why
3. Reference related issues: `Closes #12`
4. Ensure all CI checks pass (lint, tests, Docker build)
5. Request a review

## Issue Labels

| Label | Meaning |
|---|---|
| `bug` | Something is broken |
| `testing` | Test coverage gaps |
| `performance` | Speed or resource improvements |
| `docker` | Container / deployment |
| `documentation` | Docs updates |
| `database` | SQLite schema or query work |

## Project Structure

```
it-risk-manager-agent/
├── app.py                  # Streamlit web UI
├── config.py               # Central configuration
├── scripts/
│   ├── scrape_eba.py        # EBA scraper
│   ├── scrape_mas.py        # MAS scraper
│   ├── scraping_utils.py    # Shared scraping helpers
│   ├── process_updates.py   # Text extraction + DB storage
│   ├── generate_alerts.py   # Alert formatting
│   ├── llm_utils.py         # Ollama integration
│   ├── logging_config.py    # Loguru setup
│   └── backup_db.py         # Database backup
├── tests/
│   ├── conftest.py          # Shared fixtures
│   └── test_*.py            # Test modules
├── data/
│   ├── raw/                 # Scraped files
│   └── processed/           # SQLite database
├── backups/                 # Database backups (git-ignored)
├── docker-compose.yml
├── Dockerfile
├── ARCHITECTURE.md
└── pyproject.toml
```

## License

MIT — see [LICENSE](LICENSE).
