# Guide 2: Backend API

## Goal

Implement the local FastAPI backend skeleton.

## What You Will Build

- `GET /health`
- `POST /api/chat-jobs`
- `GET /api/chat-jobs/{job_id}`
- request/response schemas
- safe error format

## Prerequisites

- `specs/api_contract.md`
- `specs/database_schema.md`
- `specs/job_orchestration.md`

## Files Involved

Future files:

```text
backend/api/
backend/shared/
backend/database/
```

## Steps

1. Create backend structure.
2. Add FastAPI app.
3. Add Pydantic schemas.
4. Add SQLite database initialization.
5. Implement health endpoint.
6. Implement job creation endpoint.
7. Implement job status endpoint.
8. Add validation errors with safe response shape.

## Verify

- `GET /health` returns ok.
- Invalid message returns validation error.
- `POST /api/chat-jobs` returns `job_id`.
- `GET /api/chat-jobs/{job_id}` returns pending status.

## Troubleshooting

- If route handlers start doing long-running work, stop and move that logic to worker/router.
- If database code appears inside route bodies, move it to repository layer.

## Next Guide

Continue to `guides/3_async_jobs.md`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
