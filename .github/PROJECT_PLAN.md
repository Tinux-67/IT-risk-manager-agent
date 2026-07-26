# 📋 IT Risk Manager Agent - Refactoring & Optimizations Project Plan

> **Project Board:** [IT Risk Manager Agent - Refactoring & Optimizations](https://github.com/Tinux-67/IT-risk-manager-agent/projects)
> **Status:** 🟡 **In Progress** (Week 1: Code Kwaliteit & Bugfixes)

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
**Status:** ⚠️ **In Progress** (1/4 taken voltooid)

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ✅ **Scraping Utils Refactor** | Maak `scraping_utils.py` voor gedeelde functies in `scrape_eba.py` en `scrape_mas.py` | ✅ **Done** | `refactor`, `scraping` | - | [#2](https://github.com/Tinux-67/IT-risk-manager-agent/pull/2) |
| ⬜ **Fix Logging Configuratie** | Fix `{time}` in `LOG_FILE` (dynamische bestandsnamen) | ⬜ **Todo** | `bug`, `logging` | - | - |
| ⬜ **Environment Variables** | Voeg `.env.example` toe en gebruik `os.getenv()` in `config.py` | ⬜ **Todo** | `enhancement`, `config` | - | - |
| ⬜ **Pre-commit Hooks** | Voeg `ruff`, `black`, `isort`, `mypy` hooks toe | ⬜ **Todo** | `testing`, `ci` | - | - |

---

### **🟡 Milestone 2: Prestatie Optimalisaties** *(Week 2)*
**Doel:** Snelheid verbeteren voor grote datasets.
**Prioriteit:** ⭐⭐⭐⭐
**Status:** ⬜ **Not Started**

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ⬜ **Parallelle Verwerking** | Gebruik `ThreadPoolExecutor` in `process_updates.py` | ⬜ **Todo** | `performance`, `refactor` | - | - |
| ⬜ **Ollama Caching** | Voeg `requests-cache` toe voor Ollama API calls | ⬜ **Todo** | `performance`, `llm` | - | - |
| ⬜ **Database Indexes** | Voeg ontbrekende indexes toe (bv. `idx_source_risk_area`) | ⬜ **Todo** | `database`, `performance` | - | - |
| ⬜ **Streamlit Caching** | Verbeter caching in `app.py` (singleton DB connectie) | ⬜ **Todo** | `performance`, `streamlit` | - | - |

---

### **🔵 Milestone 3: Testing & Kwaliteitscontrole** *(Week 3)*
**Doel:** Betere testdekking en codekwaliteit.
**Prioriteit:** ⭐⭐⭐
**Status:** ⬜ **Not Started**

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ⬜ **Integratietests** | Voeg `test_integration.py` toe voor E2E workflow | ⬜ **Todo** | `testing`, `integration` | - | - |
| ⬜ **Ollama Mocking** | Verbeter mocking in tests voor Ollama foutscenario's | ⬜ **Todo** | `testing`, `llm` | - | - |
| ⬜ **Test Coverage** | Voeg tests toe voor `scrape_mas.py` (ontbrekende functies) | ⬜ **Todo** | `testing`, `scraping` | - | - |
| ⬜ **Streamlit Tests** | Voeg tests toe voor `app.py` (gebruik `pytest-streamlit`) | ⬜ **Todo** | `testing`, `streamlit` | - | - |

---

### **🟣 Milestone 4: Docker & Deployment** *(Week 4)*
**Doel:** Betere deployment en monitoring.
**Prioriteit:** ⭐⭐⭐
**Status:** ⬜ **Not Started**

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ⬜ **Dockerfile** | Voeg een `Dockerfile` toe (multi-stage build) | ⬜ **Todo** | `docker`, `deployment` | - | - |
| ⬜ **Health Checks** | Voeg health checks toe aan `docker-compose.yml` | ⬜ **Todo** | `docker`, `monitoring` | - | - |
| ⬜ **Ollama Volume** | Maak Ollama model data persistent | ⬜ **Todo** | `docker`, `ollama` | - | - |
| ⬜ **Backup Script** | Voeg een backup mechanisme toe voor de database | ⬜ **Todo** | `deployment`, `database` | - | - |

---

### **⚫ Milestone 5: Veiligheid & Documentatie** *(Week 4)*
**Doel:** Veiligheid verbeteren en documentatie bijwerken.
**Prioriteit:** ⭐⭐⭐
**Status:** ⬜ **Not Started**

| **Taak** | **Beschrijving** | **Status** | **Labels** | **Assignee** | **PR** |
|---------|------------------|------------|-----------|--------------|---------|
| ⬜ **URL Validatie** | Voeg SSRF preventie toe in scrapers | ⬜ **Todo** | `security`, `scraping` | - | - |
| ⬜ **Secrets Management** | Voeg `.env.example` toe en gebruik GitHub Secrets | ⬜ **Todo** | `security`, `config` | - | - |
| ⬜ **ARCHITECTURE.md** | Voeg architectuur diagram toe | ⬜ **Todo** | `documentation` | - | - |
| ⬜ **CONTRIBUTING.md** | Voeg bijdrage gids toe | ⬜ **Todo** | `documentation` | - | - |

---

## 📊 Voortgang Overzicht

| **Milestone** | **Taken** | **Voltooid** | **Voortgang** |
|--------------|----------|--------------|---------------|
| 🟢 Milestone 1 | 4 | 1 | 25% |
| 🟡 Milestone 2 | 4 | 0 | 0% |
| 🔵 Milestone 3 | 4 | 0 | 0% |
| 🟣 Milestone 4 | 4 | 0 | 0% |
| ⚫ Milestone 5 | 4 | 0 | 0% |
| **Totaal** | **20** | **1** | **5%** |

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

**Laatste update:** 2026-07-26
**Beheerder:** @Tinux-67
