# IT Risk Manager Agent — Quality Review
**Date:** 2026-08-28  
**Reviewer:** OpenClaw assistant  
**Commit reviewed:** `07276b7` (HEAD/main) — Merge PR #34 *fix/review-fixes-2026-08-26*

## Executive Summary
The repo is in **good shape** for a single-author/small-team project. The latest merge addressed the most visible rough edges from the review cycle: centralized logging, proper license alignment (Apache-2.0 in `pyproject.toml` now matches `LICENSE`), real UTF-8 emoji (no broken surrogate escapes), and a much improved README. CI is broad (test, lint, Docker build, pre-commit) and the test count is 136/136 passing per project claims.

However, this review was **static only** — the sandbox host has a bare Python 3.14 installation without `pip` or `venv`, so I could not run `pytest`, `ruff`, `black`, `mypy`, or the Docker build locally. Syntax checks via `python3 -m py_compile` pass for all `.py` files.

## What’s Solid ✅

| Area | Verdict | Notes |
|------|---------|-------|
| **Packaging** | ✅ | Single source of truth in `pyproject.toml`; editable install path documented; dev extras declared. |
| **CI/CD** | ✅ | Four workflows: test (3.11+3.12), lint (ruff/black/isort/codespell), Docker build, pre-commit. `workflow_dispatch` added for manual re-runs. |
| **Code style enforcement** | ✅ | `pyproject.toml` configures black (100 cols), ruff, isort, pytest, coverage. Pre-commit hooks are local-system hooks, so they rely on tools being installed. |
| **Architecture** | ✅ | Clear separation: scrapers → processor → DB → alerts / Streamlit. `ARCHITECTURE.md` Mermaid diagram matches the layout. |
| **Security basics** | ✅ | SSRF allowlist in `scraping_utils.py` (`eba.europa.eu`, `mas.gov.sg`, `www.*`); non-root Docker user; no secrets committed. |
| **Testing breadth** | ✅ | Unit tests for every public scraper/processing/alert/app module plus an E2E integration test. Good fixtures in `conftest.py`. |
| **LLM resilience** | ✅ | Ollama failures are caught and fall back to keyword classification/summaries. Caching (24h TTL) is implemented in `llm_utils.py`. |
| **Logging** | ✅ | `logging_config.py` centralizes loguru setup and is idempotent. |
| **Documentation** | ✅ | README, CONTRIBUTING, ARCHITECTURE are thorough and up to date after the recent README overhaul. |

## Issues Found — Ranked by Impact

### 1. Python 3.14 Compatibility Risk 🔴
**File:** `pyproject.toml`  
**Current:** `requires-python = ">=3.11"`, classifiers list 3.11/3.12, CI runs 3.11/3.12.  
**Problem:** The host where this review ran has Python 3.14.4 and no older version. Several dependencies (e.g. `pandas>=2.0.0`, `pypdf>=4.0.0`, `pdfminer.six`, `python-docx`) may not have binary wheels for 3.14 yet, and CI does not test 3.13/3.14. The code itself uses modern syntax (`list[str]`, `str | None`) that is fine on 3.11+, but dependency resolution is the risk.

**Recommendation:**
- Add CI matrix entries for 3.13 and optionally 3.14-dev once dependencies support them, or
- Pin an upper bound in `pyproject.toml` until the project has been tested on newer Pythons (e.g. `requires-python = ">=3.11,<3.14"`).

### 2. Unused Dependencies 🔴
**Files:** `pyproject.toml` dependencies list vs. source usage  
**Findings:**
- `requests-cache>=1.0.0` is declared but **never used** in source code.
- `tenacity>=8.0.0` is declared but **never used**; no retries are configured for HTTP or Ollama calls.
- `pdfminer.six>=20221105` is declared but **never used**; PDF parsing uses `pypdf` only.
- `mypy` is configured but **not run in CI**; the lint workflow does not call `mypy`. CONTRIBUTING mentions it, but it is absent from `.github/workflows/lint.yml`. The pre-commit workflow does not run it either.

**Recommendation:**
- Remove unused runtime deps to shrink install size and attack surface.
- Add `mypy scripts/ app.py config.py` to the lint workflow (or remove mypy from CONTRIBUTING if intentionally dropped).

### 3. Dead-Code / Over-Broad Exception Handling 🟡
**Files:** `scripts/process_updates.py`, `scripts/scrape_eba.py`, `scripts/scrape_mas.py`, `scripts/llm_utils.py`, `app.py`, `scripts/backup_db.py`, `scripts/scraping_utils.py`  
**Findings:**
- 17 bare `except Exception` clauses. Many are sensible (network/filesystem fallbacks), but several swallow programming errors silently:
  - `process_updates.py:362` wraps the entire `process_file()` body in `except Exception` and calls `conn.rollback()` — good safety, but it masks the failure details from callers.
  - `llm_utils.py:114` returns `None` on every Ollama error, making it impossible for callers to distinguish "model not found", "timeout", or "server down".
  - `scraping_utils.py:30` returns `False` for *any* URL parse error, which is fine but slightly opaque.
- `generate_alerts.py` has no dedicated test file name in the README coverage table, but tests exist; the README table says `test_generate_alerts.py` coverage is alert formatting + audience logic, which is accurate.

**Recommendation:**
- Where appropriate, catch narrower exception classes (`requests.RequestException`, `sqlite3.Error`, `ollama.ResponseError`, `FileNotFoundError`).
- Add an error taxonomy to `llm_utils.py` so callers can decide whether to retry.

### 4. Scraping Robustness Gaps 🟡
**Files:** `scripts/scrape_eba.py`, `scripts/scrape_mas.py`  
**Findings:**
- No retry/back-off logic despite `tenacity` being a dependency.
- EBA scraper only looks for `/sites/default/files/` links. If EBA changes its CDN/path, scraping returns zero results silently.
- MAS scraper has three near-identical functions (`scrape_mas_publications`, `scrape_mas_consultations`, `scrape_mas_regulations`) with duplicated date/title extraction logic. They could be collapsed into one parameterized helper.
- Date extraction is fragile: it walks up three DOM parents looking for any class matching `date`, and falls back to URL/filename patterns. No validation that the extracted string is actually a date.
- No rate-limit handling beyond a fixed sleep.

**Recommendation:**
- Add `tenacity` retries with exponential back-off on `requests` calls (or remove `tenacity` from deps).
- Add a smoke test / integration test that at least parses a saved snapshot of the EBA/MAS page HTML so layout regressions are caught.
- Validate extracted dates with `datetime.strptime` and log warnings on unparseable values.

### 5. Parallel Processing Caveat 🟡
**File:** `scripts/process_updates.py` (`process_files_parallel`)  
**Current:** Uses `ThreadPoolExecutor` with per-thread SQLite connections.  
**Problem:** This is correct for SQLite thread-safety, but it opens the DB from many threads and each worker re-runs `init_db()` indirectly. It also does not bound queue depth or handle `max_workers > CPU count` gracefully. More importantly, LLM calls inside `process_file` are CPU/GPU-bound on the Ollama side; threads help with file I/O but may not help with LLM latency.

**Recommendation:**
- Consider separating "download + extract text" (I/O, good in threads) from "LLM classify/summarize" (could be batched).
- Add a progress bar or structured logging for long runs.

### 6. App.py Maintainability 🟡
**File:** `app.py` (516 lines)  
**Findings:**
- `app.py` mixes UI, business logic, and subprocess orchestration. All functions are free functions; there is no class/module split.
- `run_script()` shells out to `python scripts/<name>.py` and uses `subprocess.run(..., shell=False)` correctly, but it can only run scripts in the hardcoded `SCRIPTS_DIR = "scripts"`. It is not tested against the real scripts (only against temp scripts in tests).
- Dashboard query is a single aggregated SQL statement — good — but `get_updates` builds SQL with string concatenation and parameter substitution. It is safe because only `days`, `risk_area`, and `urgency` are interpolated from controlled UI widgets, but it is still a style that could drift toward injection risk if extended.

**Recommendation:**
- Split `app.py` into modules (e.g. `ui/pages/`, `ui/components/`, `services/`).
- Convert the dynamic SQL to parameterized only (the current code is already parameterized for the filter values, but `days` controls `cutoff_date` construction, which is fine).

### 7. Test Quality Observations 🟡
**Files:** `tests/`  
**Findings:**
- Tests patch `sys.path` at module top in almost every file. A shared `conftest.py` already exists; consider removing the duplication.
- `test_app.py` manually constructs a large Streamlit stub. It works, but it is brittle if Streamlit API changes.
- Several tests rely on mocking `pypdf.PdfReader` at the module path; this is correct after the PyPDF2→pypdf migration.
- No test for `create_github_issues.py` (the most complex module by cyclomatic complexity). It is a utility script, but it has 498 lines and prints extensively.

**Recommendation:**
- Add at least unit tests for `_api_request`, `get_or_create_label`, and `create_issue` in `create_github_issues.py`.
- Consider using `pytest-streamlit` for UI tests instead of the hand-rolled stub, or document why the stub is preferred.

### 8. Docker / Compose Nits 🟢
**Files:** `Dockerfile`, `docker-compose.yml`  
**Findings:**
- `Dockerfile` uses `as builder` lowercase syntax — still accepted by Docker but BuildKit best practice is uppercase `AS`.
- `docker-compose.yml` pins `user: "1000:1000"`, which assumes the host has UID 1000. On systems where the user is different, bind-mounted `data/` and `logs/` volumes may have permission issues.
- Health check in Dockerfile uses `sqlite3.connect` but does not verify the Streamlit server is actually serving.
- `ollama-setup` runs as UID 1000 and writes to `/root/.ollama` via the `ollama-data` volume owned by root inside the container. This can fail with permission errors if the volume was previously initialized by root.

**Recommendation:**
- Use `AS builder`.
- Use a build arg or remove the hardcoded UID/GID.
- Add a proper Streamlit health check to the Dockerfile or rely on the compose health check.

### 9. Minor Code Issues 🟢
- `config.py` calls `load_dotenv()` at import time. This is common, but it can make testing with different env files awkward. Consider guarding with `if os.getenv("ENV_FILE"):` or documenting.
- `scripts/backup_db.py` writes a temporary `.db` copy next to backups, then compresses. If backup dir is on a different filesystem, the temp copy is fine; otherwise it briefly doubles disk use. Acceptable.
- `create_github_issues.py` uses the classic Projects REST API + GraphQL (`/graphql`) mix. GitHub has deprecated classic projects; new projects (v2) use different GraphQL mutations. This script may stop working for new repos using Projects v2.
- `ISSUES_TEMPLATE.json` still references Dutch tasks and `requirements.txt` in old issue bodies. It should be updated to match current `pyproject.toml` packaging.

## Suggested Priority Order
1. **Resolve Python 3.14/dependency drift** — decide supported versions and test them in CI.
2. **Remove unused dependencies** (`requests-cache`, `tenacity`, `pdfminer.six`) or actually use them.
3. **Add `mypy` to CI** or remove it from the documented checks.
4. **Refactor MAS scrapers** to reduce duplication and add date validation.
5. **Add tests for `create_github_issues.py`** and modernize project-board API usage.
6. **Split `app.py`** into smaller modules as the UI grows.
7. **Tighten exception handling** where narrow exceptions are available.

## Quick Verdict
| Criterion | Score |
|-----------|-------|
| Correctness (static) | 8/10 |
| Test coverage | 8/10 |
| Code organization | 7/10 |
| CI/DevEx | 8/10 |
| Security baseline | 8/10 |
| Documentation | 9/10 |
| Packaging | 8/10 |
| **Overall** | **8/10 — solid, with clear next steps** |

## Files Reviewed
- `app.py`, `config.py`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`
- `scripts/scrape_eba.py`, `scripts/scrape_mas.py`, `scripts/scraping_utils.py`
- `scripts/process_updates.py`, `scripts/generate_alerts.py`, `scripts/llm_utils.py`
- `scripts/logging_config.py`, `scripts/backup_db.py`, `scripts/create_github_issues.py`
- `tests/*.py`, `tests/conftest.py`
- `.github/workflows/*`, `.pre-commit-config.yaml`
- `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `.github/PROJECT_PLAN.md`, `.github/ISSUES_TEMPLATE.json`
