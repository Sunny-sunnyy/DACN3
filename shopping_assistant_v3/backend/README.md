# Backend

FastAPI backend for Shopping Assistant V3. Created in Phase 1 as structure
only; no runtime code is implemented yet.

## Stack Decisions

- Python via `uv` only. Never call `python` or `pip` directly.
- Web framework: FastAPI.
- Persistence: SQLite (schema kept Postgres-compatible).
- Async jobs: local worker, `job_id` lifecycle.
- Model calls: LiteLLM abstraction, OpenAI-compatible provider.
- Default mode: mock/fixture. Real search and real model calls are opt-in.

Python dependency layout (`pyproject.toml`) is deferred to Phase 2.

## Module Map

| Module | Responsibility |
|---|---|
| `shared/` | Config, logging, common schemas, guardrails, error types. |
| `database/` | SQLite schema, repositories, job/product/estimate persistence. |
| `api/` | FastAPI app, validation, safe errors, job endpoints. |
| `router/` | Job orchestration, intent routing, tool invocation. |
| `tools/deal_search/` | Amazon/BestBuy search, normalized candidates. |
| `tools/price_estimator/` | USD fair value estimation, deal score. |
| `synthesizer/` | Vietnamese final answer from structured evidence. |

Rules:

- `shared/` must not import from tools or agents.
- Route handlers stay thin and never run scraping/model work directly.
- Database access goes through repositories.

## Environment Variables

See `shopping_assistant_v3/.env.example` for the full list. Key safety flags:

```text
ENABLE_REAL_SEARCH=false
ENABLE_REAL_MODEL_CALLS=false
```

Default tests must never scrape live Amazon/BestBuy or call paid model APIs.

## Local Service

- Backend URL: `http://localhost:8000`
- Contracts: see `shopping_assistant_v3/guides/architecture.md` (API, database)
  and `shopping_assistant_v3/guides/agent_architecture.md` (Router, tools,
  Synthesizer).
