# Regulatory Agent PoC

A **CLI-based agent** for tracking and interpreting EBA regulations, powered by **Mistral-7B** and **SQLite**.

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
