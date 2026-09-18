#!/usr/bin/env bash
# =============================================================================
# run_demo.sh — Qualiteitspoort voor de ITRM demo
#
# Volgorde:
#   1. Voorwaarden controleren (pytest, streamlit, bestanden)
#   2. Acceptatietests draaien (test_acceptance.py)
#   3. Bij groen resultaat: Streamlit starten
#   4. Bij rood resultaat: AFBOUWEN met duidelijke foutrapportage
#
# Gebruik:     ./run_demo.sh
# Test-only:   ./run_demo.sh --check
# =============================================================================

set -euo pipefail

# --- Configuratie ------------------------------------------------------------
APP_BESTAND="demo_app.py"    # Migratie voltooid → wijzigen naar "demo_app.py"
TEST_BESTAND="test_acceptance.py"
CSS_BESTAND="design_system.css"
LOG_DIR=".logs"

ROOD='\033[0;31m'
GROEN='\033[0;32m'
GEEL='\033[1;33m'
WIT='\033[0m'

mkdir -p "${LOG_DIR}"
TIJDSTIP=$(date +%Y%m%d-%H%M%S)
LOG="${LOG_DIR}/run-${TIJDSTIP}.log"

echo -e "${WIT}━━━ ITRM Deploy — ${TIJDSTIP} ━━━${WIT}"

# --- Stap 1: Voorwaarden -----------------------------------------------------
echo "[1/3] Voorwaarden controleren..."

command -v python >/dev/null 2>&1 || { echo -e "${ROOD}❌ python niet gevonden op PATH.${WIT}"; exit 1; }

if [[ ! -f "${APP_BESTAND}" ]]; then
    echo -e "${ROOD}❌ ${APP_BESTAND} bestaat niet in de huidige map (${PWD}).${WIT}"
    exit 1
fi

if [[ ! -f "${TEST_BESTAND}" ]]; then
    echo -e "${ROOD}❌ ${TEST_BESTAND} bestaat niet in de huidige map (${PWD}).${WIT}"
    exit 1
fi

python -c "import pytest" 2>/dev/null || {
    echo -e "${GEEL}⚠️  pytest niet geïnstalleerd — nu installeren...${WIT}"
    python -m pip install pytest -q
}

python -c "import streamlit" 2>/dev/null || {
    echo -e "${GEEL}⚠️  streamlit niet geïnstalleerd — nu installeren...${WIT}"
    python -m pip install streamlit -q
}

echo -e "${GROEN}✓ Voorwaarden in orde.${WIT}"

# --- Stap 2: Acceptatietests -------------------------------------------------
echo "[2/3] Acceptatietests draaien..."

if python -m pytest "${TEST_BESTAND}" -v --tb=short 2>&1 | tee "${LOG}"; then
    AANTAL_GESLAAGD=$(grep -c "PASSED" "${LOG}" || true)
    echo -e "${GROEN}✓ Alle ${AANTAL_GESLAAGD} acceptatietests geslaagd (log: ${LOG}).${WIT}"
else
    echo ""
    echo -e "${ROOD}════════════════════════════════════════════════${WIT}"
    echo -e "${ROOD}❌ ACCEPTATIE GEFAALD — de app start NIET.${WIT}"
    echo -e "${ROOD}════════════════════════════════════════════════${WIT}"
    echo ""
    echo -e "Waarschijnlijke oorzaak per falende test:"
    echo -e "  AT-1 (None-output)     → component met side-effect rendering"
    echo -e "  AT-2 (ruwe HTML)       → data met markup, of html() zonder flag"
    echo -e "  AT-3 (verticale tekst) → writing-mode / rotate in CSS"
    echo ""
    echo -e "Volledige rapportage: ${LOG}"
    echo -e "Terugvalprotocol: zie migratieplan — keert terug naar de laatste"
    echo -e "groene milestone en isoleert het defect."
    exit 1
fi

# --- Stap 3: Starten (overslaan bij --check) ---------------------------------
if [[ "${1:-}" == "--check" ]]; then
    echo -e "${GROEN}✓ Alleen-controlemodus (--check): tests groen, app niet gestart.${WIT}"
    exit 0
fi

echo "[3/3] Streamlit starten: ${APP_BESTAND}"
exec streamlit run "${APP_BESTAND}" --server.address 127.0.0.1 --server.port 8502
