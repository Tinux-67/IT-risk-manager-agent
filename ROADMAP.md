# IT Risk Manager Agent — Longer-Term Improvement Plan

## Summary

| # | Improvement | Phase | Effort | Priority |
|---|---|---|---|---|
| 1 | Plugin architecture for scrapers | 1 — Foundation | M (4–6h) | High |
| 2 | Database migrations | 1 — Foundation | S (2–3h) | High |
| 3 | LLMProvider abstraction | 1 — Foundation | M (4–6h) | High |
| 4 | Streamlit authentication | 2 — Hardening | S (2–3h) | Medium |
| 5 | Scheduled scraping | 2 — Hardening | S (2–3h) | Medium |
| 6 | Push notifications | 3 — Polish | M (4–6h) | Low |
| 7 | Separate LLM cache DB | 3 — Polish | S (1–2h) | Low |

**Total estimated effort: ~20–30 hours.** Order is deliberate — Foundation removes structural debt, Hardening secures the operational surface, Polish adds quality-of-life.

---

## Phase 1 — Foundation (10–15h)

**Goal:** After Phase 1, adding a regulator, switching LLM backends, and evolving the schema are all single-file changes.

### 1. Plugin Architecture for Scrapers

**Rationale:** `scrape_eba.py` and `scrape_mas.py` share ~80% of their structure. Every new regulator currently means copy-pasting, which guarantees divergence bugs.

**Implementation** — `scripts/scrapers/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ScrapedItem:
    title: str
    url: str
    published_date: datetime
    source: str       # e.g. "eba", "mas"
    raw_metadata: dict

class BaseRegulatorScraper(ABC):
    source: str       # set in subclass

    @abstractmethod
    def fetch_page(self) -> str: ...

    @abstractmethod
    def parse_items(self, raw: str) -> list[ScrapedItem]: ...

    def run(self) -> list[ScrapedItem]:
        items = self.parse_items(self.fetch_page())
        for item in items:
            item.source = self.source
        return items
```

Existing scrapers become `EbaScraper(BaseRegulatorScraper)` and `MasScraper(BaseRegulatorScraper)`. A central runner holds the registry:

```python
REGISTRY = {"eba": EbaScraper(), "mas": MasScraper()}
# Adding FCA = one new subclass + one line here
```

Scraping orchestration (deduplication, DB writes) lives once in the runner, not duplicated per scraper.

**Effort: 4–6h.** Most time is untangling per-scraper logic from the orchestration currently inside each script.

---

### 2. Database Migrations

**Rationale:** "DROP TABLE and recreate" works until you have production data. Any schema change is currently a manual, lossy operation.

**Implementation:** Alembic is the right call — ties directly to existing SQLAlchemy models, minimal complexity.

1. Extract models to `scripts/models.py` with `Base = declarative_base()`
2. `alembic init migrations/`
3. Set `sqlalchemy.url` in `alembic.ini` → `DB_PATH`
4. Set `target_metadata = models.Base.metadata` in `env.py`
5. `alembic revision --autogenerate -m "initial"` — captures current schema
6. Future: modify model → `alembic revision --autogenerate -m "add column X"` → commit

**Effort: 2–3h.** Most time goes into extracting models cleanly.

---

### 3. LLMProvider Abstraction

**Rationale:** `llm_utils.py` is hardwired to Ollama. Switching providers requires rewriting the integration. With an abstraction, it's a config change. Also makes the project portable — Ollama locally, OpenAI in CI.

**Implementation** — `scripts/llm_provider.py`:

```python
from typing import Protocol

class LLMProvider(Protocol):
    def complete(self, prompt: str, system: str | None = None) -> str: ...
    def health_check(self) -> bool: ...

class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url, self.model = base_url, model

    def complete(self, prompt: str, system: str | None = None) -> str:
        # current ollama.chat() logic extracted here
        ...

class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key, self.model = api_key, model

    def complete(self, prompt: str, system: str | None = None) -> str:
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return client.chat.completions.create(
            model=self.model, messages=messages
        ).choices[0].message.content
```

**Config keys to add to `.env.example`:**
```
LLM_PROVIDER=ollama       # ollama | openai | anthropic
LLM_MODEL=mistral
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

A `get_provider()` factory reads `LLM_PROVIDER` and returns the right instance. No direct Ollama imports outside the provider module.

**Effort: 4–6h.** Protocol extraction is fast; the time is updating call sites and testing with two providers.

---

## Phase 2 — Hardening (4–6h)

**Goal:** Safe to leave running unattended, safe to expose on a network.

### 4. Streamlit Authentication

**Rationale:** An unauthenticated dashboard that triggers scraping and subprocess calls is a real security risk.

**Implementation:** Streamlit native auth (≥1.35) — least friction, no extra infrastructure.

```python
# app.py — top of main(), before any other UI
if not st.experimental_user.is_logged_in:
    st.login()
    st.stop()
```

Add credentials to `.streamlit/secrets.toml`:
```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2/callback"
cookie_secret = "<random-secret>"
```

Alternative: if you're already behind Caddy/nginx, HTTP basic auth in the reverse proxy is one less Streamlit dependency.

**Effort: 2–3h** including Docker Compose update and secrets setup.

---

### 5. Scheduled Scraping

**Rationale:** Manual scraping defeats the purpose of an alerting tool.

**Recommendation: cron wrapper first.** A thin `scripts/scheduled_scrape.py` wired to a cron job is battle-tested, decoupled from app uptime, and consistent with how this ecosystem already schedules tasks (weather mail, energy report).

```bash
# cron: run daily at 07:00 Amsterdam time
0 5,6 * * * /path/to/run-at-ams-hour.sh 07 python3 scripts/scheduled_scrape.py --sources eba,mas >> /var/log/it-risk-scrape.log 2>&1
```

`scheduled_scrape.py` calls the scraper runner, logs results, and exits. APScheduler (embedded) is a natural follow-on if you want schedule visibility in the dashboard.

**Effort: 2–3h** including the wrapper script, error handling, and log setup.

---

## Phase 3 — Polish (5–8h)

**Goal:** Quality-of-life for day-to-day use.

### 6. Push Notifications

**Rationale:** Urgent regulatory items shouldn't require opening the dashboard to find. Proactive delivery is the difference between a monitoring tool and a compliance tool.

**Implementation:** Post-processing hook in `process_updates.py` — after an item is classified as `Urgent` or `High`, call a notifier:

```python
class Notifier(Protocol):
    def send(self, subject: str, body: str) -> None: ...

class ResendNotifier:
    """Reuse Resend API pattern from existing tooling."""
    def send(self, subject: str, body: str) -> None:
        # same RESEND_API_KEY + urllib approach as haarlem-weather-mail.py
        ...
```

Wire into `process_updates.py`:
```python
if item.urgency in ("Urgent", "High"):
    notifier.send(
        subject=f"[{item.urgency}] {item.source}: {item.title}",
        body=item.summary or item.raw_text[:500],
    )
```

Key detail: track notified item IDs to avoid re-sending the same item on every run.

**Effort: 4–6h** including deduplication tracking and the Resend integration.

---

### 7. Separate LLM Cache Database

**Rationale:** LLM cache and domain data have completely different lifecycles — domain data is permanent, cache is ephemeral. Keeping them in the same DB complicates migrations and makes cache invalidation harder.

**Implementation:**

```python
# config.py — add one line
LLM_CACHE_DB: Path = Path(os.getenv("LLM_CACHE_DB", str(PROCESSED_DIR / "llm_cache.db")))
```

In `llm_utils.py`, open the cache connection against `Config.LLM_CACHE_DB` instead of `Config.DB_PATH`. Run a one-time migration to move existing cache rows to the new file.

**Effort: 1–2h.**

---

*Last updated: 2026-08-06*
