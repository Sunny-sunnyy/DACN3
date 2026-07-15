# Plan 03: Backend Architecture

## Purpose

Define backend modules and responsibilities.

## Target Structure

```text
backend/
├── README.md
├── shared/
├── database/
├── api/
├── router/
├── tools/
│   ├── deal_search/
│   └── price_estimator/
├── synthesizer/
├── comparer/
└── advisor/
```

## Module Responsibilities

### `shared/`

Reusable utilities:

- config loading.
- structured logging.
- common schemas.
- error types.
- guardrails.
- retry helpers.
- HTTP client helpers.

Rule: `shared` must not import from specific agents/tools.

### `database/`

Persistence layer:

- schema creation.
- repositories.
- migrations if needed.
- seed/demo data.

Rule: API and agents should use repositories, not raw SQL scattered across modules.

### `api/`

FastAPI app:

- routes.
- request validation.
- response schemas.
- job creation.
- job status.

Rule: no long-running scraping/model work inside route handlers.

### `router/`

Orchestrates job execution:

- loads job.
- classifies intent.
- chooses allowed tool path.
- invokes tools.
- invokes synthesizer.
- saves results.

### `tools/deal_search/`

Searches Amazon/BestBuy and normalizes candidates.

### `tools/price_estimator/`

Estimates fair USD price from normalized product information.

### `synthesizer/`

Generates Vietnamese final answer from structured evidence.

### `comparer/` and `advisor/`

Defined for later phases. They should not block MVP.

## Error Handling Policy

- User errors return 4xx with safe message.
- Internal errors are logged with `job_id`.
- Job failures store sanitized `error_message`.
- Partial failures should produce warnings if results are still useful.
- Never expose stack traces to frontend.

## Retry Policy

Use retry only for transient operations:

- HTTP timeouts.
- rate limits.
- temporary model provider errors.

Do not retry validation errors.

## Acceptance Criteria

- Each module has a README when created.
- Tool/agent boundaries are clear.
- FastAPI routes are thin.
- Job lifecycle is owned by backend, not frontend.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
