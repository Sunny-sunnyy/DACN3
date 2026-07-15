# Phase 2: Backend API And Database

## Purpose

Implement the local FastAPI backend skeleton and SQLite persistence backbone.

This phase proves that the backend can accept a Vietnamese chat request, create
a durable job, and return job status through polling without running long
scraping/model work in the request handler.

## Current Status

Phase 2 starts after Phase 1 has created or confirmed the V3 runtime structure.

Expected runtime folders:

```text
backend/shared/
backend/database/
backend/api/
```

## Scope

Implement:

- FastAPI app.
- `GET /health`.
- `POST /api/chat-jobs`.
- `GET /api/chat-jobs/{job_id}`.
- safe validation/error response shape.
- SQLite schema initialization.
- repository functions for jobs and minimal conversation/message records.
- config loading without printing secrets.

## Non-Goals

- No worker execution yet.
- No Router/Synthesizer logic.
- No search/pricing tools.
- No frontend.
- No live scraping/model/API calls.
- No production auth.
- No AWS/Terraform.

## Inputs From Previous Phases

Required:

- Phase 1 runtime folder structure.
- `gameplan.md`.
- `guides/architecture.md`.

Recommended:

- Review `guides/agent_architecture.md` only for future result payload shape.

## Contracts

### Health Endpoint

`GET /health`

```json
{
  "status": "ok",
  "service": "shopping-assistant-v3"
}
```

### Create Chat Job

`POST /api/chat-jobs`

Request:

```json
{
  "message": "Tìm laptop gaming dưới 800 đô",
  "conversation_id": null,
  "source": "All",
  "max_results_per_source": 6
}
```

Validation:

- `message`: string, 2 to 1000 chars.
- `conversation_id`: nullable string.
- `source`: `All`, `Amazon`, or `BestBuy`.
- `max_results_per_source`: integer, 1 to 20.

Response:

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Job created. Poll status endpoint for results."
}
```

### Get Chat Job

`GET /api/chat-jobs/{job_id}`

Required fields:

- `job_id`
- `status`
- `created_at`
- `started_at`
- `completed_at`
- `result`
- `error_message`

### Safe Error Shape

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request.",
    "details": []
  }
}
```

### SQLite Tables

Minimum tables for this phase:

- `jobs`
- `conversations`
- `messages`
- `agent_runs`
- `products`
- `price_estimates`

The implementation may create all tables in Phase 2 even if later phases fill
them.

Required `jobs` fields:

- `id`
- `user_id`
- `job_type`
- `status`
- `request_payload`
- `result_payload`
- `error_message`
- `created_at`
- `started_at`
- `completed_at`
- `updated_at`

MVP statuses:

```text
pending
running
completed
failed
```

## Workflow Gate

Before coding:

- Load `using-superpowers`.
- Use `brainstorming` with the user.
- Ask only questions that change scope, design, tests, or implementation plan.
- Present the Phase 2 plan.
- Wait for explicit approval.

## Implementation Order

1. Confirm Phase 1 report or current runtime structure.
2. Define backend config without logging secrets.
3. Define database schema initialization.
4. Implement repository functions for creating and reading jobs.
5. Implement FastAPI app.
6. Implement Pydantic request/response schemas.
7. Implement `GET /health`.
8. Implement `POST /api/chat-jobs`.
9. Implement `GET /api/chat-jobs/{job_id}`.
10. Add focused tests for validation, repository operations, and endpoint smoke.
11. Write Phase 2 report.

## Verification

Minimum commands, adjusted to actual backend layout:

```bash
uv run pytest <backend tests>
uv run <backend start command>
curl -s http://localhost:8000/health
```

Manual API checks:

- Valid `POST /api/chat-jobs` returns `pending`.
- Invalid short message returns safe validation error.
- `GET /api/chat-jobs/{job_id}` returns the created job.
- Unknown job returns a safe 404-style error.

Verification must not require network/model/scraping calls.

## Report Requirements

Write:

```text
shopping_assistant_v3/reports/phase_2_backend_api_and_database_report.md
```

Include:

- API endpoints implemented;
- schema/tables created;
- exact commands run;
- test results;
- deviations from this guide;
- known database/API risks;
- docs that may need update.

## Risks And Open Questions

- SQLite migration tooling is not selected yet. A simple schema initializer is
  acceptable for MVP if documented.
- Route handlers must stay thin. If API code starts processing jobs directly,
  stop and move that work to Phase 3.
- The exact backend package layout should remain simple; avoid abstractions that
  are not needed for Phase 2.
