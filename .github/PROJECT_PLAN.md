# 📋 IT Risk Manager Agent - Refactoring & Optimizations Project Plan

**Laatste Refactoring:** refactor/optimizations branch (2026-08-01)

> **Project Board:** [IT Risk Manager Agent - Refactoring & Optimizations](https://github.com/Tinux-67/IT-risk-manager-agent/projects)
> **Status:** 🟢 **Milestones 1 & 2 Complete**

---

## 🎯 Overzicht
Dit project board volgt de **aanbevolen implementatie volgorde** uit de code review om de **IT Risk Manager Agent** te optimaliseren.

### **Doelstellingen**
✅ **Code Kwaliteit Verbeteren** (Week 1)
✅ **Prestaties Optimaliseren** (Week 2)
✅ **Testing & CI/CD Verbeteren** (Week 3)
✅ **Docker & Deployment Optimaliseren** (Week 4)
✅ **Veiligheid & Documentatie** (Week 4)

---

## 📅 Mijlpalen (Milestones)

### **🟢 Milestone 1: Code Kwaliteit & Bugfixes** *(Week 1)*
**Doel:** Duplicatie verwijderen, logging fixen, configuratie verbeteren.
**Prioriteit:** ⭐⭐⭐⭐⭐
**Status:** ✅ **Complete** (4/4 taken voltooid)

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ✅ **Scraping Utils Refactor** | Maak `scraping_utils.py` voor gedeelde functies in `scrape_eba.py` en `scrape_mas.py` | ✅ **Done** | `refactor`, `scraping` | - | [#2](https://github.com/Tinux-67/IT-risk-manager-agent/pull/2) |
| ✅ **Fix Logging Configuratie** | Centralized `logging_config.py` met idempotente `setup_logging()` | ✅ **Done** | `bug`, `logging` | - | refactor/optimizations |
| ✅ **Environment Variables** | `.env.example` aanwezig, `os.getenv()` gebruikt in `config.py` | ✅ **Done** | `enhancement`, `config` | - | - |
| ✅ **Pre-commit Hooks** | `.pre-commit-config.yaml` aanwezig met `ruff`, `black`, `isort` | ✅ **Done** | `testing`, `ci` | - | - |

---

### **🟡 Milestone 2: Prestatie Optimalisaties** *(Week 2)*
**Doel:** Snelheid verbeteren voor grote datasets.
**Prioriteit:** ⭐⭐⭐⭐
**Status:** ✅ **Complete** (4/4 taken voltooid)

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ✅ **Parallelle Verwerking** | `ThreadPoolExecutor` met per-thread SQLite connecties (thread-safe) | ✅ **Done** | `performance`, `refactor` | - | refactor/optimizations |
| ✅ **Ollama Caching** | SQLite-backed 24h TTL cache via `llm_utils.py` | ✅ **Done** | `performance`, `llm` | - | refactor/optimizations |
| ✅ **Database Indexes** | `idx_source_risk_area` composite index toegevoegd | ✅ **Done** | `database`, `performance` | - | refactor/optimizations |
| ✅ **Streamlit Caching** | `@st.cache_data(ttl=300)` en geoptimaliseerde dashboard query | ✅ **Done** | `performance`, `streamlit` | - | refactor/optimizations |

---

### **🔵 Milestone 3: Testing & Kwaliteitscontrole** *(Week 3)*
**Doel:** Betere testdekking en codekwaliteit.
**Prioriteit:** ⭐⭐⭐
**Status:** ✅ **Complete** (4/4 taken voltooid)

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ✅ **Integratietests** | `test_integration.py` toegevoegd voor E2E workflow | ✅ **Done** | `testing`, `integration` | - | - |
| ✅ **Ollama Mocking** | Verbeterde mocking in `conftest.py` voor foutscenario's | ✅ **Done** | `testing`, `llm` | - | - |
| ✅ **Test Coverage** | Uitgebreide tests voor `scrape_mas.py` en andere modules | ✅ **Done** | `testing`, `scraping` | - | - |
| ✅ **Streamlit Tests** | `test_app.py` toegevoegd voor dashboard helpers | ✅ **Done** | `testing`, `streamlit` | - | - |

---

### **🟣 Milestone 4: Docker & Deployment** *(Week 4)*
**Doel:** Betere deployment en monitoring.
**Prioriteit:** ⭐⭐⭐
**Status:** ✅ **Complete** (4/4 taken voltooid)

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ✅ **Dockerfile** | `Dockerfile` aanwezig (multi-stage build) | ✅ **Done** | `docker`, `deployment` | - | - |
| ✅ **Health Checks** | Health checks toegevoegd aan `docker-compose.yml` | ✅ **Done** | `docker`, `monitoring` | - | - |
| ✅ **Ollama Volume** | `ollama-data` volume aanwezig in `docker-compose.yml` | ✅ **Done** | `docker`, `ollama` | - | - |
| ✅ **Backup Script** | `scripts/backup_db.py` toegevoegd voor database back-ups | ✅ **Done** | `deployment`, `database` | - | - |

---

### **⚫ Milestone 5: Veiligheid & Documentatie** *(Week 4)*
**Doel:** Veiligheid verbeteren en documentatie bijwerken.
**Prioriteit:** ⭐⭐⭐
**Status:** ✅ **Complete** (4/4 taken voltooid)

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ✅ **URL Validatie** | `is_allowed_url()` + `_ALLOWED_HOSTNAMES` in `scraping_utils.py` | ✅ **Done** | `security`, `scraping` | - | refactor/optimizations |
| ✅ **Secrets Management** | `.env.example` aanwezig in repo root | ✅ **Done** | `security`, `config` | - | - |
| ✅ **ARCHITECTURE.md** | Architectuur diagram en componenten beschreven | ✅ **Done** | `documentation` | - | - |
| ✅ **CONTRIBUTING.md** | Bijdrage gids toegevoegd | ✅ **Done** | `documentation` | - | - |

---

## 📊 Voortgang Overzicht

| **Milestone** | **Taken** | **Voltooid** | **Voortgang** |
|--------------|----------|--------------|---------------|
| 🟢 Milestone 1 | 4 | 4 | 100% ✅ |
| 🟡 Milestone 2 | 4 | 4 | 100% ✅ |
| 🔵 Milestone 3 | 4 | 4 | 100% ✅ |
| 🟣 Milestone 4 | 4 | 4 | 100% ✅ |
| ⚫ Milestone 5 | 4 | 4 | 100% ✅ |
| **Totaal** | **20** | **20** | **100%** |

---

## 🚀 Hoe te Gebruiken

### **1. Project Board Aanmaken (Handmatig)**
1. Ga naar: [https://github.com/Tinux-67/IT-risk-manager-agent/projects](https://github.com/Tinux-67/IT-risk-manager-agent/projects)
2. Klik op **"New project"** → Kies **"Board"** (Kanban).
3. Vul in:
   - **Titel:** `IT Risk Manager Agent - Refactoring & Optimizations`
   - **Beschrijving:** `Project board for tracking refactoring and optimization tasks.`
4. Klik op **"Create project"**.

### **2. Kolommen Aanmaken**
Maak de volgende kolommen aan:
- **📥 Backlog** (voor toekomstige taken)
- **🟡 Todo** (voor geplande taken)
- **🟠 In Progress** (voor actieve taken)
- **✅ Done** (voor voltooide taken)

### **3. Issues Toevoegen**
Voeg voor elke taak in de bovenstaande tabel een **Issue** toe en voeg deze toe aan het project board.

---

## 🔗 Gerelateerde Documenten
- [Code Review & Optimalisatie Voorstellen](../docs/CODE_REVIEW.md) *(als deze bestaat)*
- [Architectuur Overzicht](../ARCHITECTURE.md) *(toe te voegen)*
- [Bijdrage Gids](../CONTRIBUTING.md) *(toe te voegen)*

---

## 💡 Tips
- **Prioriteer Milestone 1** (Code Kwaliteit) eerst, omdat dit de basis legt voor de rest.
- **Gebruik GitHub Issues** voor elke taak, zodat je de voortgang kunt tracken.
- **Voeg labels toe** aan Issues (bv. `refactor`, `testing`, `performance`).
- **Gebruik milestones** om taken te groeperen per week.

---

**Laatste update:** 2026-08-01
**Beheerder:** @Tinux-67
