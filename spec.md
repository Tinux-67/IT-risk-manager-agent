# Systems Architect — Review Blueprint

## Repository: Tinux-67/IT-risk-manager-agent
**Branch under review:** `main` @ `32549f51` (2026-09-03 07:50:57 UTC)
**Review type:** Static, source-and-metadata only. **No local execution.**

---

## 1. Scope and boundaries

### In scope
- All Python source: `app.py`, `config.py`, `scripts/*.py`, `scripts/migrations/*.py`, `scripts/create_github_issues/*.py`.
- Test suite: `tests/*.py`, `tests/conftest.py`, `pytest.ini`, `[tool.pytest.ini_options]` in `pyproject.toml`.
- Packaging/config: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.pre-commit-config.yaml`, `.env.example`, `.gitignore`, `.dockerignore`.
- CI/CD: `.github/workflows/{test,lint,pre-commit,docker-build}.yml` plus Dependabot signal.
- Documentation & governance: `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `.github/PROJECT_PLAN.md`, `QUALITY_REVIEW_2026-08-28.md`, `LICENSE`.
- Repository metadata: issues, PRs, CI run history, branch protection signals visible via public API.

### Out of scope / hard limits
- **No execution.** We will not run `pytest`, `pip install`, `docker build`, or the app. Test coverage is inferred from static test-source inspection and CI logs only; no real coverage percentages will be claimed.
- **No git clone.** All files fetched via `https://raw.githubusercontent.com/...` or the GitHub REST API (`/repos/.../contents`, `/git/trees/...?recursive=1`).
- **No secrets verification.** We can grep for accidental secret patterns in tracked files, but we cannot verify the contents of real `.env` / GitHub Secrets.
- **No runtime behavior validation** for the Streamlit UI, Ollama LLM calls, EBA/MAS scrapers against live sites, or DB migrations against a live SQLite file. Findings here remain hypotheses to be validated by the operator on a real host.
- **No verification of the yesterday-claimed "288 CI runs" health** beyond aggregation stats accessible without auth (recent runs only; full history would require pagination we will sample, not exhaust).
- **No historical diff archaeology** beyond the last ~30 commits / 30 PRs / 30 issues. Deeper history is sampled opportunistically.

### Prior-review linkage
A previous review attempt on 2026-09-03 failed. A tracked artifact `QUALITY_REVIEW_2026-08-28.md` exists in the repository root and **must be cross-referenced** by the Lead Dev: any finding from that document that is still reproducible on `main` counts as a regression or unaddressed debt.

---

## 2. Target areas & hypotheses

### A. Code quality & structure
- **Single-package layout.** `py-modules = ["app", "config"]` plus `packages = ["scripts"]` means `scripts/` is imported as a namespace package. Check for import cycles, inconsistent `__init__.py` usage, and module-level side effects.
- **Idempotency guards.** The project heavily relies on "safe to re-run" scripts. Verify that every scraper/migration/backup writes with idempotency checks and does not corrupt state on duplicate runs.
- **Module-level logging.** PR #34 fixed `scripts/scrape_mas.py` to use centralized `setup_logging()`. Verify the fix is complete and that no other module still calls `logger.add(...)` directly.
- **Silent-failure pattern.** Commit `32549f51` fixed PDF extraction and LLM quality gating. The Lead Dev must verify the pre-INSERT quality gate is implemented in production code, not only in tests, and that fallback logic is deterministic.

### B. Test coverage & hygiene
- **136 tests passing claim** (per README, dated 2026-08-06). Verify test count matches the static test files. Look for skipped/xfail tests, mock-only coverage, and duplication of production logic inside tests.
- **Quality-gate test duplication hypothesis.** `tests/test_quality_gate.py` appears to re-implement the gate predicate rather than exercising the real `_process_file_impl`. This is a structural red flag: tests should call public/internal functions, not duplicate them.
- **Integration test realism.** `tests/test_integration.py` and `tests/test_app.py` likely mock Ollama and network calls. Verify they actually assert on state changes, not just "no exception".

### C. Dependencies & security patches
- **Lower-bound only pins.** All dependencies use `>=` with no upper bound (`pypdf>=4.0.0`, `ollama>=0.1.0`, etc.). Check for known CVEs in current lower bounds and whether `dependabot.yml` exists to auto-bump.
- **Subprocess usage.** Search for `subprocess.run`, `os.system`, `eval`, `exec`. The 2026-08-26 PR claimed "only one controlled `subprocess.run` in `app.py`." Verify that no new dangerous calls were added in recent dashboard commits.
- **Secret leakage.** Grep for API keys, tokens, `.env` values committed by accident, hardcoded credentials in test fixtures.

### D. Open issues / TODOs
- **Issue zero hypothesis.** API shows 0 open issues. Verify if issues are disabled or truly closed. Search README, code comments, and `QUALITY_REVIEW_2026-08-28.md` for TODO/FIXME/XXX.
- **Dependabot signals.** Latest run is a graph update (2026-09-03, success). No open Dependabot PRs visible in last 30 issues. Confirm whether this means dependencies are current or whether Dependabot is configured to group/open PRs differently.

### E. CI/CD status
- **Workflow set:** Test (matrix 3.11/3.12), Lint (ruff/black/isort/codespell), Pre-commit, Docker Build.
- **Badge vs. reality.** README badges may reflect default branch status; verify latest runs for `test.yml` and `lint.yml` on `main`.
- **Unsigned automation commits.** All recent commits are authored by `OpenClaw <openclaw@localhost>` and are unsigned. Flag as governance risk: branch protection / signature verification should be considered.

---

## 3. Concrete checkpoints & acceptance criteria

| # | Checkpoint | Acceptance criterion | Priority |
|---|---|---|---|
| 1 | Repo structure matches declared architecture | `ARCHITECTURE.md` accurately describes `app.py`, `config.py`, `scripts/`, `tests/`, `static/`, `data/`; no orphan modules. | Must |
| 2 | No uncommitted secrets | Grep across tracked files for `password`, `token`, `api_key`, `secret`, `BEGIN`. Any hit must be explainable as placeholder/example. | Must |
| 3 | CI badges match latest `main` runs | `test.yml` and `lint.yml` last runs on `main` are `success` or `failure` is explained. | Must |
| 4 | Test count matches README claim | Static count of `test_*` functions across `tests/` ≈ 136, with explanation for drift. | Must |
| 5 | Quality gate implemented in production | `scripts/` code contains pre-INSERT gate matching the test contract (reject triple-default fallback). | Must |
| 6 | No dangerous dynamic execution | `eval`, `exec`, `os.system`, uncontrolled `subprocess.run` absent outside documented, safe call in `app.py`. | Must |
| 7 | Logging centralized | All scrapers/entry points use `setup_logging()`; no stray `logger.add` at module level. | Should |
| 8 | Idempotency documented/implemented | Re-run of migrations/scrapers/backup does not produce duplicates or corruption. | Should |
| 9 | Dependency lower bounds safe | No known high-severity CVE in pinned lower-bound versions; upper-bound policy documented. | Should |
| 10 | TODO/FIXME tracked | All TODO/FIXME/XXX in source have matching issue or are explicitly in-project-plan. | Could |

---

## 4. Lead Dev fetch & inspection plan

### Phase 1 — Skeleton (fast, read-only)
1. Fetch `pyproject.toml`, `pytest.ini`, `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `.github/PROJECT_PLAN.md`, `QUALITY_REVIEW_2026-08-28.md`, `.pre-commit-config.yaml`.
2. Fetch `.github/workflows/{test,lint,pre-commit,docker-build}.yml`.
3. Fetch root tree via `git/trees/main?recursive=1`; list all `.py` files with sizes.

### Phase 2 — Core modules (priority order)
1. `app.py` — Streamlit entry point; subprocess usage; smart caching; SQL queries.
2. `config.py` — Configuration, directory initialization, env handling.
3. `scripts/analyze.py` / `scripts/scrape_eba.py` / `scripts/scrape_mas.py` — The trust-layer pipeline and the 2026-09-03 fix.
4. `scripts/db.py` / `scripts/migrations/*.py` — DB schema, migration idempotency.
5. `scripts/alert_generator.py` / `scripts/create_github_issues.py` — Output/egress paths.
6. `scripts/backup_db.py` — Backup script.

### Phase 3 — Tests (deep)
1. `tests/conftest.py` — fixtures and mocking strategy.
2. `tests/test_quality_gate.py` — gate contract; check for duplication.
3. `tests/test_integration.py` and `tests/test_app.py` — integration realism.
4. Remaining `tests/test_*.py` files — count and inspect for mock-only coverage.

### Phase 4 — Cross-reference
1. Compare findings against `QUALITY_REVIEW_2026-08-28.md` and open issues.
2. Document regressions, unaddressed debt, and newly introduced risks.

### Output expected from Lead Dev
A structured Markdown report containing:
- Executive summary (status: green/amber/red per checkpoint).
- File-by-file quality notes.
- Test-coverage observations.
- Dependency/security findings.
- CI/CD status summary.
- List of open TODOs/FIXMEs.
- Identification of what likely failed yesterday and how the 2026-09-03 commit addresses it.

---

## 5. Key signals summary

- **Recent fix:** `32549f51` (2026-09-03) — silent data-quality failures in trust layer. This is the strongest clue to yesterday's failure: the pipeline was inserting low-quality records without raising errors.
- **Issue hygiene:** 0 open issues in API, but many closed PRs (#33, #34). This suggests the project is actively fixing review findings.
- **Automation risk:** All recent commits are unsigned and authored by `OpenClaw <openclaw@localhost>`. Branch protection / commit signing should be reviewed.
- **Test hygiene risk:** `tests/test_quality_gate.py` duplicates gate logic. This indicates tests may be written to pass rather than to validate the real implementation.
- **Dependency risk:** Lower-bound-only pins with no upper bounds. Stability over time depends entirely on CI catching breaking changes, which is fragile.
