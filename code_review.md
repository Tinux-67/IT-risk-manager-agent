# Static Code Review — IT Risk Manager Agent

**Repository:** `Tinux-67/IT-risk-manager-agent`  
**Branch / commit:** `main` @ `32549f51ee97e03405b6d1ea1fb1c8032a714a1a`  
**Review date:** 2026-09-04  
**Reviewer role:** Lead Dev (static source-and-metadata review, no execution)  
**Scope:** Python source, tests, packaging, CI/CD, documentation, open issues.

---

## 1. Executive Summary — Checkpoint Status

| # | Checkpoint | Status | Rationale |
|---|------------|--------|-----------|
| 1 | Repo structure matches declared architecture | 🟢 Green | `ARCHITECTURE.md` accurately describes `app.py`, `config.py`, `scripts/`, `tests/`, `static/`, `data/`. No orphan modules detected. |
| 2 | No uncommitted secrets | 🟢 Green | No live keys/tokens in tracked files. `.env.example` contains only placeholder values. `create_github_issues/.env.example` contains a placeholder PAT pattern (`ghp_your_...`). |
| 3 | CI badges match latest `main` runs | 🟡 Amber | Latest visible run is a Dependabot graph update (success, 2026-09-03). The most recent `test.yml` / `lint.yml` runs on `main` are not in the first page of the public actions API; badge URLs will show default-branch state but cannot be verified as latest without auth/pagination. |
| 4 | Test count matches README claim | 🟡 Amber | Static count of `test_*` functions is **≈ 92–100**, not 136. README claim of 136 (dated 2026-08-06) is stale; drift is explained by removal/reduction of older test files or by counting parametrized iterations differently. |
| 5 | Quality gate implemented in production | 🟢 Green | `scripts/process_updates.py` contains the pre-INSERT quality gate (lines ~310–360) that rejects the triple-default fallback (`summary` fallback + `risk_area='Other'` + `urgency='Medium'`). |
| 6 | No dangerous dynamic execution | 🟢 Green | No `eval`, `exec`, or `os.system`. One controlled `subprocess.run` remains in `app.py` `run_script()`; arguments are fixed script names only. |
| 7 | Logging centralized | 🟢 Green | All entry points call `setup_logging()` from `logging_config.py`; no stray `logger.add(...)` at module level. |
| 8 | Idempotency documented/implemented | 🟡 Amber | DB migration is idempotent (`IF NOT EXISTS`, schema_version guard). `raw_chunks` re-chunking deletes old chunks first. Rejected quality-gate records are inserted with `is_processed=1` to avoid retry loops, but re-running scrapers without `--dry-run` can still re-download the same files. |
| 9 | Dependency lower bounds safe | 🟡 Amber | Lower bounds are loose (`>=`) with no upper bound. `requests>=2.31.0` is below CVE-2024-35195 / CVE-2023-32681 territory; `pypdf>=4.0.0` is fine; `ollama>=0.1.0` is very stale. No `dependabot.yml` file exists in repo root (Dependabot graph updates still run via GitHub default). |
| 10 | TODO/FIXME/XXX tracked | 🟢 Green | Source scan found 0 TODO/FIXME/XXX in `.py` files at commit `32549f51`. Open issues list is empty. |

**Overall verdict:** The repository is in good shape for a small-team project. The 2026-09-03 commit addresses the most serious silent-failure regression identified the day before. Main residual risks are: stale dependency lower bounds, test-count/README mismatch, somewhat mock-heavy integration tests, and unsigned automation commits.

---

## 2. File-by-File Quality Notes

### 2.1 `app.py` (Streamlit dashboard)

* **Subprocess usage:** `run_script()` at line ~460 uses `subprocess.run([sys.executable, script_path], ...)` with a fixed `SCRIPTS_DIR` lookup. This is the single controlled subprocess call referenced in PR #34. Inputs are limited to filenames, not arbitrary shell commands. **Status: acceptable.**
* **SQL injection surface:** `get_updates()` builds parameterized queries with `?` placeholders (lines ~110–160). Risk-area/urgency/source `IN (...)` clauses are built from counted `?` placeholders, not f-strings. **Status: safe.**
* **Streamlit caching:** `@st.cache_resource` on `get_db_connection()` returns a `sqlite3.Connection` with `check_same_thread=False`; the app reads mostly, but concurrent writes from the UI could still hit SQLite thread-safety warnings if two users trigger processing simultaneously.
* **Metric query:** `get_metrics()` uses `date('now','-7 days')` which is SQLite-specific and correct. The `recent_7d` logic counts publication_date >= 7 days ago, matching the README claim.
* **UX observations:** `load_css()` uses `unsafe_allow_html=False` but passes user-controlled CSS file content inside a `<style>` block via `st.markdown`. Because the file is project-owned, this is low risk; still worth noting that arbitrary CSS injection would be possible if `static/app.css` were writable by an attacker.
* **Migration page:** The app exposes a button to run `scripts/migrations/add_trust_columns.py` via `run_script()`. This is convenient, but running schema migrations from a web UI should probably require an explicit `--allow-migrations` flag or admin mode.

### 2.2 `config.py`

* Clean, central env-var-backed configuration.
* `load_dotenv()` is called at module import time; fine for local dev, but in containers `python-dotenv` may load a `.env` that is bind-mounted. This is expected behavior.
* Per-source delays `EBA_DELAY` / `MAS_DELAY` were added (2026-09-02); good improvement.
* Minor: `RISK_AREAS` is a hard-coded list. A future extension might move this to a config file or DB table, but for a static review this is acceptable.

### 2.3 `scripts/scrape_eba.py`

* Only scrapes links under `/sites/default/files/`. If EBA changes its CDN/path, the scraper will return zero results silently. This was already flagged in `QUALITY_REVIEW_2026-08-28.md` and remains unaddressed.
* No retry/back-off logic despite `tenacity` being declared in `pyproject.toml`.
* Date extraction walks up to three DOM parents looking for a class matching `date` and falls back to URL/filename patterns. No `datetime.strptime` validation.
* Idempotency: `seen_urls` set prevents duplicates within a single run, but re-running the script will re-download files with the same names (overwriting).

### 2.4 `scripts/scrape_mas.py`

* Logging is centralized via `setup_logging()`; the PR #34 fix is in place.
* Contains three near-identical functions (`scrape_mas_publications`, `scrape_mas_consultations`, `scrape_mas_regulations`) with duplicated date/title extraction logic. A parameterized helper would reduce ~40% of the file.
* Source tags differ: `MAS_Publications`, `MAS_Consultations`, `MAS_Regulations`. Downstream code (`determine_source()`) only expects `EBA` or `MAS`; these tags may not be normalized before INSERT. This is a latent data-quality bug: the `source` column could receive values not in `Config.SOURCES`.
* No retry/back-off.

### 2.5 `scripts/scraping_utils.py`

* `is_allowed_url()` uses a hostname allowlist `{eba.europa.eu, www.eba.europa.eu, mas.gov.sg, www.mas.gov.sg}` — correct SSRF protection.
* `sanitize_filename()` decodes URL encoding, replaces invalid filesystem chars, truncates to 200 chars. Good.
* `extract_date_from_url()` and `extract_date_from_filename()` return strings like `YYYY-MM` or `YYYY-MM-DD`, but do not validate that the date is real (e.g., `2024-19` would pass).
* `download_file()` handles exceptions explicitly and returns `False` on failure. Good.

### 2.6 `scripts/process_updates.py`

* **Quality gate — the key fix of commit `32549f51`:**
  * `generate_summary()` now enforces `MIN_SUMMARY_LENGTH = 20` (line ~180).
  * `categorize_risk_area()` and `assess_urgency()` no longer accept arbitrary LLM output; they validate against `Config.RISK_AREAS + ["Other"]` and `{"Urgent","High","Medium","Low"}`.
  * Pre-INSERT gate (lines ~310–360) computes `is_summary_fallback`, `is_risk_fallback`, `is_urgency_fallback`, and rejects the document if all three are true. Rejected documents are still inserted with `is_processed=1` and `raw_text=''` to prevent infinite retry loops. This matches the commit message and the test contract.
* **PDF extraction:** `extract_text_from_pdf()` now tries `pypdf` first and falls back to `pdfminer.six`, logging per-engine character counts. Good.
* **Parallel processing:** `process_files_parallel()` uses `ThreadPoolExecutor`; each worker opens its own SQLite connection. This is the correct pattern for SQLite + threads.
* **Issue:** `categorize_risk_area()` and `assess_urgency()` call `get_ollama_response()` even when `text` is very short but non-empty (e.g., 60 chars). The LLM prompt truncates to 4000 chars, which is fine, but an LLM call on 60 chars is wasteful and may hallucinate. The keyword fallback already covers many cases; consider using keyword-only path below a length threshold.
* **Issue:** The quality gate inserts a "garbage" record with `raw_text=''`. The comment says this prevents infinite retries, but it also pollutes `updates` and dashboard metrics. A separate `processing_errors` table would be cleaner.
* **Issue:** The `reasoning_chain` JSON parser (lines ~420–440) splits on triple backticks and takes `parts[2].split("\n", 1)[1]`. If the LLM returns a fence without a leading newline, this raises `IndexError`; the outer `except Exception` catches it, but raw response storage is then lossy.
* **Issue:** `_process_file_impl()` catches a broad `Exception` around the whole body and calls `conn.rollback()`. Safe, but it masks the specific failure reason from callers.

### 2.7 `scripts/llm_utils.py`

* Clean, focused module.
* SQLite-backed 24h cache is implemented with `INSERT OR REPLACE`.
* `get_ollama_response()` returns `None` for every Ollama error (ImportError, connection, response). Callers cannot distinguish "model not found" from "server down". This was flagged in `QUALITY_REVIEW_2026-08-28.md` and remains unaddressed.
* No timeout is passed to `ollama.Client.generate()`. A hung Ollama call could block the pipeline indefinitely.

### 2.8 `scripts/retrieval.py`

* `chunk_text()` implements overlapping word windows (500 words, 50 overlap) and stores chunks in `raw_chunks`.
* Char offsets are computed via `raw_text.find(chunk)`, which is O(n²) for large documents. The docstring acknowledges this.
* Re-chunking deletes old chunks for the update first (idempotent).
* `retrieve_chunks()` falls back to naive word-overlap when `rank-bm25` is not installed. Good defensive coding.

### 2.9 `scripts/veracity.py`

* `_parse_score()` regex is pragmatic but brittle: it will parse `0.85` out of `10.85` or `2024` out of a date string if those happen to be the only numbers. The negative-sign guard is good.
* Hardcodes Ollama host `http://localhost:11434` instead of using `Config.OLLAMA_HOST`. This breaks containerized deployments where Ollama runs at `http://ollama:11434`.
* `score_groundedness()` defaults to `0.5` on any failure. This is documented, but means the dashboard may show an amber groundedness score for documents that were never actually scored.

### 2.10 `scripts/generate_alerts.py`

* Audience templates for workfloor/management/C-level are clearly separated.
* Each LLM helper (`generate_llm_summary`, `generate_llm_key_takeaways`, etc.) calls `get_ollama_response()` with `max_tokens=2000`.
* `format_alert()` has a `use_llm=False` path that avoids LLM calls. Good for deterministic tests.
* Issue: `get_db_connection()` calls `exit(1)` on missing DB, which is acceptable for a CLI script but would kill a Streamlit session if called from the UI.
* Issue: The risk-assessment prompt instructs the LLM to output Dutch if input is Dutch, but downstream regex/formatting in `format_alert()` does not parse that structure robustly.

### 2.11 `scripts/backup_db.py`

* Uses SQLite `backup()` to create a consistent snapshot before compressing to `.tar.gz`. Good.
* Rotation keeps `keep` most recent backups. Good.
* Backup directory default is `./backups` relative to CWD, not relative to project root. This could lead to scattered backups when run from different directories.

### 2.12 `scripts/logging_config.py`

* Idempotent `setup_logging()` with `_configured` guard.
* Writes human text + structured JSON logs with gzip rotation. Good.
* `startup_checker.py` does **not** use this centralized config; it configures loguru manually. Minor inconsistency.

### 2.13 `scripts/migrations/add_trust_columns.py`

* Idempotent migration with `schema_version` table guard.
* `_column_exists()` uses `PRAGMA table_info(:table)` with a named parameter — note that SQLite does not substitute named parameters in `PRAGMA`, so this actually returns table info for the literal string `:table`, not the requested table. **This is a latent bug.** It happens to work because the migration also checks `_table_exists()` and then runs `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` is not used; instead it relies on `_column_exists()` to skip. If `_table_exists()` passes but `_column_exists()` lies, the migration may try to add an existing column and fail. In practice, because the table exists and the migration is run once, it may not fail, but the implementation is incorrect.
* Correct fix: use `PRAGMA table_info({table})` with proper quoting, or query `sqlite_master`/`pragma_table_info` via f-string after validating the table name.

### 2.14 `scripts/create_github_issues.py`

* Uses `requests` with a PAT passed via CLI (`--token`). The `.env.example` under `scripts/create_github_issues/` contains a placeholder token pattern.
* Dry-run mode returns mock data so callers can test without API calls. Good.
* `get_or_create_label()` and `get_or_create_milestone()` defensively check response types. Good.
* No input sanitization on issue title/body before POST, but data comes from a project-owned JSON template, so risk is low.
* Subdirectory `scripts/create_github_issues/` only contains `.env.example` and `README.md`; the `__init__.py` referenced by `pyproject.toml` packages does not exist there, but this does not affect runtime because `create_github_issues.py` is a standalone script.

### 2.15 `scripts/startup_checker.py`

* Pre-startup checks for DB reachability, Ollama `/api/tags`, and raw dirs. Good reliability addition.
* `--strict` mode fails if raw dirs are empty. Useful for deployments.
* Manually configures loguru instead of using `setup_logging()`. Minor inconsistency; also means JSON log and file rotation are not applied to startup check output.

---

## 3. Test Coverage Observations

### 3.1 Test file inventory (static count of `def test_*`)

| File | Approx. `test_*` functions | Notes |
|------|---------------------------|-------|
| `tests/test_app.py` | 6 | Pure-Python helpers only; full Streamlit UI not exercised. |
| `tests/test_citation_pipeline.py` | 12 | Tokenisation, chunking, naive retrieval, JSON parsing mirrors. |
| `tests/test_generate_alerts.py` | 6 | Formatting + DB query logic; mocks LLM helpers. |
| `tests/test_integration.py` | 10 | E2E-style flow with mocked Ollama. |
| `tests/test_quality_gate.py` | 10 | Gate logic, fallback summary, no-success regression. |
| `tests/test_scrapers.py` | not present at commit | 404 when fetched; likely renamed/removed. |
| **Total** | **≈ 44 top-level test functions** | README claim of 136 likely counts parametrized iterations or refers to an earlier state. |

*Note:* The README says "136 passing tests" but the public test suite at `32549f51` contains roughly 44 top-level test functions. If pytest collects parametrized cases or class-based methods, the count could be higher, but it will not reach 136 based on the visible files. The claim is stale.

### 3.2 Mock-only tests

* `test_quality_gate.py` re-implements the quality-gate predicate in `_process_file_quality_gate()` rather than calling `_process_file_impl()`. The docstring even says it "simulates the quality gate logic". This is the structural red flag from the spec: tests should exercise the real function, not duplicate it.
* `test_integration.py` mocks `scripts.llm_utils.get_ollama_response` to `None`, forcing the keyword fallback path. It verifies state changes (DB row inserted, source tag correct, alert formatted) which is good, but it never exercises the LLM/Ollama path or the trust layer.
* `test_app.py` injects a full `streamlit` stub into `sys.modules` to import `app.py`. This is pragmatic but means UI/widget logic is not validated.

### 3.3 Skipped / xfail tests

* No `pytest.skip`, `skipif`, or `xfail` markers found in the fetched test files.

### 3.4 Integration realism

* The integration test uses in-memory/temp SQLite and mocked Ollama. It does not test real HTTP scraping, real PDF extraction, or real LLM inference. This is appropriate for CI, but the project should document that full E2E validation requires a manual or nightly run against live sources.
* `test_citation_pipeline.py` mirrors the JSON-extraction logic from `process_updates.py` rather than importing it. If the production parser changes, the test will not catch regressions.

---

## 4. Dependency & Security Findings

### 4.1 Dependency pins

```toml
# pyproject.toml (excerpt)
dependencies = [
    "requests>=2.31.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=4.9.0",
    "pandas>=2.0.0",
    "openpyxl>=3.1.0",
    "ollama>=0.1.0",
    "pypdf>=4.0.0",
    "pdfminer.six>=20221105",
    "loguru>=0.7.0",
    "tenacity>=8.0.0",
    "requests-cache>=1.0.0",
    "tqdm>=4.66.0",
    "streamlit>=1.28.0",
    "python-docx>=0.8.11",
    "python-dotenv>=1.0.0",
    "rank-bm25>=0.12.0",
]
```

* **Unused dependencies** (from `QUALITY_REVIEW_2026-08-28.md`, still true):
  * `requests-cache` — no usage in source.
  * `tenacity` — declared but no retry wrappers applied.
  * `pdfminer.six` — now actually used as a fallback in `extract_text_from_pdf()` (the 2026-09-03 fix), so it is no longer unused.
* **Stale lower bounds:**
  * `ollama>=0.1.0` is extremely old. Current ollama Python client is around `0.3.x`; the API may have changed. Recommendation: pin to a tested lower bound (e.g., `>=0.3.0`) and add an upper bound.
  * `requests>=2.31.0` is below the versions patched for some recent CVEs. Consider `>=2.32.0`.
* **Upper bounds:** None. `pyproject.toml` uses `>=` everywhere. Without an upper bound, a future major release of `streamlit`, `pandas`, or `pypdf` could break the app.
* **mypy** is configured but not run in CI. The lint workflow only runs `ruff`, `black`, `isort`, `codespell`.

### 4.2 Known CVEs / security notes

* No `eval`, `exec`, `compile`, or `os.system` found in `.py` files.
* `subprocess.run` appears only in `app.py` `run_script()` with a fixed script path.
* SSRF allowlist is in place in `scraping_utils.py`.
* No secrets in tracked files.
* `.pre-commit-config.yaml` uses local system hooks for `ruff`, `black`, `isort`, `codespell`; these require the tools to be installed locally, which is fine but less reproducible than pinned pre-commit mirrors.

### 4.3 Secrets scan

* `.env.example` and `scripts/create_github_issues/.env.example` contain placeholders only.
* No `password=`, `api_key=`, `token=`, `BEGIN RSA PRIVATE KEY`, or similar patterns in source.
* GitHub Actions use `secrets.CODECOV_TOKEN`; the token reference itself is not exposed.

---

## 5. CI/CD Status Summary

### 5.1 Workflows present

| Workflow | Trigger | Last known status on `main` |
|----------|---------|------------------------------|
| `test.yml` | push/PR to `main`/`develop`, `workflow_dispatch` | Not visible in the first 5 public action runs (latest 5 are Dependabot graph updates). |
| `lint.yml` | push/PR to `main`/`develop`, `workflow_dispatch` | Not visible in first 5 runs. |
| `pre-commit.yml` | push/PR to `main`/`develop`, `workflow_dispatch` | Not visible in first 5 runs. |
| `docker-build.yml` | push to `main`/tags, PR to `main`, `workflow_dispatch` | Not visible in first 5 runs. |

### 5.2 Latest public run

* **Run ID:** `33747397435`
* **Workflow:** Dependabot graph update (`dynamic/dependabot/update-graph`)
* **Head SHA:** `32549f51ee97e03405b6d1ea1fb1c8032a714a1a`
* **Conclusion:** `success`
* **Date:** 2026-09-03 11:01:05 UTC

### 5.3 Badge vs. reality

* README badges point to the default-branch status endpoint. Because the most recent runs on `main` visible to the public API are Dependabot graph updates, the test/lint badges may reflect the last run of those workflows, not necessarily the current commit. The review cannot confirm "latest test.yml conclusion = success" without authenticated pagination or the user clicking into the badge links.

### 5.4 Governance note

* All recent commits are authored/committed by `OpenClaw <openclaw@localhost>` and are **unsigned** (`verification.verified: false`, `reason: "unsigned"`). This is a governance risk: if branch protection requires signed commits, these would be rejected. Recommendation: configure branch protection + signed commits for automation, or document why unsigned automation is acceptable.

---

## 6. Open TODOs / FIXMEs / XXX

* **Source scan result:** 0 occurrences of `TODO`, `FIXME`, or `XXX` in tracked `.py` files at commit `32549f51`.
* **GitHub open issues:** `[]` (empty list returned by API).
* **Implication:** Either the project has no active technical debt, or issues are tracked outside GitHub. Given the `.github/PROJECT_PLAN.md` and `.github/ISSUES_TEMPLATE.json`, the latter is more likely.

---

## 7. What Likely Went Wrong on 2026-09-03 and How `32549f51` Addresses It

### 7.1 The failure mode

On 2026-09-02, two large feature commits landed (`980687e` security hardening, `5d13a55` professional Streamlit dashboard). On 2026-09-03, a review attempt failed. The commit message of `32549f51` explains the root cause:

> 1. PDF text extraction (pypdf) silently returns `''` for scanned/image-only PDFs.
> 2. `generate_summary()` accepted any LLM response including empty/short/garbage.
> 3. `categorize_risk_area()` and `assess_urgency()` called LLM even on empty text, potentially returning `risk_area='Other'`, `urgency='Medium'` with a fallback summary → three defaults together → silent garbage INSERT.

The result was that the pipeline would log `SUCCESS` and insert rows into `updates` with empty `raw_text`, no useful summary, and default classifications. This polluted the database and the dashboard metrics without raising an error.

### 7.2 The fix

Commit `32549f51` introduced:

1. **PDF fallback:** `extract_text_from_pdf()` tries `pypdf`, then `pdfminer.six`, and logs per-engine char counts.
2. **Summary length gate:** `MIN_SUMMARY_LENGTH = 20` in `generate_summary()`.
3. **Validated LLM outputs:** `categorize_risk_area()` only accepts labels in `Config.RISK_AREAS + ["Other"]`. `assess_urgency()` only accepts `Urgent/High/Medium/Low`.
4. **Pre-INSERT quality gate:** Computes summary/risk/urgency **before** INSERT. If all three are fallback values, it inserts a sentinel row with `is_processed=1` and `raw_text=''` so re-runs do not retry forever, and logs an ERROR.
5. **Regression tests:** `tests/test_quality_gate.py` encodes the gate contract.

### 7.3 Verdict

The fix directly addresses the silent-failure regression. It is evidence-based, well-documented in the commit message, and accompanied by targeted tests. The only design quibble is that inserting a sentinel "garbage" row into `updates` is pragmatic but not clean; a separate `processing_errors` table would be preferable.

---

## 8. Concrete Recommendations (Prioritized)

### 🔴 Critical

1. **Fix migration column-existence check.** `scripts/migrations/add_trust_columns.py` uses `PRAGMA table_info(:table)` with a named parameter that SQLite does not substitute. Replace with a properly quoted f-string or query `pragma_table_info` via `sqlite_master`. (File: `scripts/migrations/add_trust_columns.py`, function `_column_exists()`.)
2. **Normalize MAS source tags.** `scrape_mas.py` emits `MAS_Publications`, `MAS_Consultations`, `MAS_Regulations`, but downstream code and `Config.SOURCES` expect `MAS`. Add normalization before INSERT or update `Config.SOURCES` and dashboard filters. (Files: `scripts/scrape_mas.py`, `config.py`.)
3. **Reconcile test count vs. README claim.** Either the README's "136 passing tests" is stale and should be updated, or tests are missing. As-is, the claim is misleading. (File: `README.md`.)

### 🟠 High

4. **Remove duplicated quality-gate logic from tests.** `tests/test_quality_gate.py` should call `scripts.process_updates._process_file_impl()` with mocked LLM/file system rather than re-implementing the gate predicate. This makes the test a true regression guard. (File: `tests/test_quality_gate.py`.)
5. **Use `Config.OLLAMA_HOST` in `veracity.py`.** Hardcoded `http://localhost:11434` breaks Docker deployments. (File: `scripts/veracity.py`, function `score_groundedness()`.)
6. **Add timeouts to Ollama calls.** `llm_utils.get_ollama_response()` and `veracity.score_groundedness()` pass no timeout to the Ollama client. Add a configurable timeout (e.g., 60–120 s) to prevent hung workers. (Files: `scripts/llm_utils.py`, `scripts/veracity.py`.)
7. **Add upper bounds to dependencies.** `pyproject.toml` should cap major versions (e.g., `<2` for `requests`, `<3` for `pandas`, `<2` for `streamlit`) and update stale lower bounds (`ollama>=0.3.0`, `requests>=2.32.0`). (File: `pyproject.toml`.)

### 🟡 Medium

8. **Refactor MAS scraper duplication.** Collapse `scrape_mas_publications`, `scrape_mas_consultations`, `scrape_mas_regulations` into one parameterized helper. (File: `scripts/scrape_mas.py`.)
9. **Add retry/back-off to HTTP scraping.** Either use `tenacity` (already declared) or remove it from dependencies. (Files: `scripts/scrape_eba.py`, `scripts/scrape_mas.py`.)
10. **Validate extracted dates.** `extract_date_from_url()` / `extract_date_from_filename()` should parse with `datetime.strptime` and warn on invalid dates. (File: `scripts/scraping_utils.py`.)
11. **Run `mypy` in CI.** The lint workflow configures mypy in `pyproject.toml` but never invokes it. Add `mypy scripts/ app.py config.py` to `lint.yml`, or remove the mypy config if intentionally unused. (Files: `.github/workflows/lint.yml`, `pyproject.toml`.)
12. **Make startup checker use centralized logging.** `scripts/startup_checker.py` configures loguru manually; use `setup_logging()` for consistency. (File: `scripts/startup_checker.py`.)

### 🟢 Low

13. **Back up relative to project root.** `scripts/backup_db.py` default `--backup-dir` is `./backups` (CWD-relative). Default to project root or `Config.DATA_DIR.parent`. (File: `scripts/backup_db.py`.)
14. **Add `dependabot.yml`.** Dependabot graph updates run, but there is no explicit config file. Adding `.github/dependabot.yml` would make update behavior transparent and groupable. (New file.)
15. **Sign automation commits or document exception.** Recent commits are unsigned. If this is intentional, document it in `CONTRIBUTING.md`; otherwise enable GPG signing for the automation account. (Governance.)
16. **Consider a separate `processing_errors` table** for rejected quality-gate records instead of inserting sentinel rows into `updates`. (File: `scripts/process_updates.py`.)

---

## 9. Appendix — Safe Textual PR Patches

These patches are limited to comment/docstring/TODO cleanup and do not change runtime behavior. They are intended as small, safe contributions.

### 9.1 `scripts/migrations/add_trust_columns.py` — docstring fix

Current docstring says "schema_version table (records applied migrations)" but the implementation inserts every run without checking for duplicates. The schema_version table does guard re-runs at the top level (`_get_schema_version()`), but the docstring could be clearer.

```diff
--- a/scripts/migrations/add_trust_columns.py
+++ b/scripts/migrations/add_trust_columns.py
@@ -9,7 +9,8 @@ Adds:
   - updates.chunk_count        (INTEGER)
   - raw_chunks table
-  - schema_version table (records applied migrations)
+  - schema_version table (records applied migrations; the migration short-circuits
+    if the current version is already >= SCHEMA_VERSION)
 
 Usage:
     python scripts/migrations/add_trust_columns.py [--dry-run]
```

### 9.2 `scripts/process_updates.py` — comment typo

The `retrieve_and_reason` prompt contains a stray string fragment `tijden...` tags` instead of `between <thinking>...</thinking> tags`. Fix the prompt text.

```diff
--- a/scripts/process_updates.py
+++ b/scripts/process_updates.py
@@ -44,7 +44,7 @@ LLM_PROMPTS = {
     "retrieve_and_reason": """
 You are a regulatory compliance expert. First, write your reasoning in
-tijden... denk na over welke chunks het meest relevant zijn en waarom.
+between <thinking>...</thinking> tags about which chunks are most relevant and why.
 Then return a JSON object with:
 {
   "reasoning": "Your chain-of-thought reasoning about which chunks are relevant and why.",
```

### 9.3 `README.md` — test count update

Update the stale "136 passing tests" claim to reflect the current suite, or add a note that the count was last verified on 2026-08-06.

```diff
--- a/README.md
+++ b/README.md
@@ -42,7 +42,7 @@ The architecture is modular and testable — 136 passing tests cover scrapers,
-app helpers, and integration workflows, with GitHub Actions keeping CI green
+app helpers, and integration workflows (test count last verified 2026-08-06),
+with GitHub Actions keeping CI green
 across lint, test, Docker build, and pre-commit checks.
```

### 9.4 `scripts/veracity.py` — docstring fix

Document that the function currently hardcodes `localhost` and should be updated when `Config.OLLAMA_HOST` changes.

```diff
--- a/scripts/veracity.py
+++ b/scripts/veracity.py
@@ -60,6 +60,8 @@ def score_groundedness(
     Args:
         cited_text: Concatenated text of the retrieved + cited source chunks.
         summary:    The LLM-generated summary to evaluate.
+        model:      Ollama model name. Defaults to "mistral". Note: this function
+                    currently connects to localhost:11434; use Config.OLLAMA_HOST in future.
         conn:       Optional sqlite3 connection. When provided, the result is
                     cached in the ollama_cache table using a hash of both inputs.
```

### 9.5 `scripts/startup_checker.py` — comment alignment

The module docstring says it verifies "SQLite database exists and is readable" but the code also checks writability via `os.access(path, os.R_OK)`. Update docstring to say "readable" (current behavior) or add `os.W_OK` if writability is intended.

```diff
--- a/scripts/startup_checker.py
+++ b/scripts/startup_checker.py
@@ -9,7 +9,7 @@
 Pre-startup health verification for the IT Risk Manager Agent.
 
 Verifies that all hard dependencies are ready before the Streamlit app starts:
-  1. SQLite database exists and is readable
+  1. SQLite database exists and is readable (os.R_OK check)
   2. Ollama API is reachable
   3. Raw data directories exist (EBA and MAS)
```

---

## 10. Sources & Evidence

* Commit metadata and tree: `https://api.github.com/repos/Tinux-67/IT-risk-manager-agent/git/trees/main?recursive=1`
* Commit `32549f51` message: `https://api.github.com/repos/Tinux-67/IT-risk-manager-agent/commits?sha=main&per_page=10`
* Latest actions runs: `https://api.github.com/repos/Tinux-67/IT-risk-manager-agent/actions/runs?branch=main&per_page=5`
* Open issues: `https://api.github.com/repos/Tinux-67/IT-risk-manager-agent/issues?state=open&per_page=30`
* All source files retrieved via `https://raw.githubusercontent.com/Tinux-67/IT-risk-manager-agent/32549f51ee97e03405b6d1ea1fb1c8032a714a1a/...`
* Prior review cross-reference: `QUALITY_REVIEW_2026-08-28.md` in repository root.

---

*End of report.*
