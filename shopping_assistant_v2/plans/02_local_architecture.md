# Plan 02: Local Architecture

## Purpose

Define the local-first architecture before AWS or production infrastructure.

## Architecture

```text
Next.js frontend
  -> FastAPI backend
  -> SQLite database
  -> local async worker
  -> router
  -> tools
  -> synthesizer
```

## Local Services

### Frontend

- Runs on `http://localhost:3000`.
- Sends requests to backend.
- Polls job status.
- Renders assistant messages and product cards.

### Backend API

- Runs on `http://localhost:8000`.
- Provides health check.
- Creates chat jobs.
- Returns job status/results.
- Owns validation and persistence.

### Local Worker

MVP can use one of these:

1. FastAPI background task.
2. Separate local worker process.

Recommended for MVP: separate local worker once job lifecycle is stable, but FastAPI background task is acceptable for the very first local slice if documented.

### Database

- SQLite file in local dev.
- Schema written to remain close to Postgres.
- Do not use JSON files for job state.

## Environment Variables

Expected categories:

- `DATABASE_URL`
- `MODEL_PROVIDER`
- `OPENAI_API_KEY`
- `PRICER_PREPROCESSOR_MODEL`
- `ENABLE_REAL_SEARCH`
- `ENABLE_REAL_MODEL_CALLS`

Do not log secret values.

## Local Run Principles

- Mock mode must work without paid APIs.
- Real search/model calls must be explicit opt-in.
- Logs should be readable in terminal.
- Failures should update job status, not leave jobs stuck.

## Future Production Mapping

| Local MVP | Future |
|---|---|
| SQLite | Postgres, Supabase, Aurora |
| Local worker | SQS plus worker service |
| Console logs | CloudWatch/LangFuse/OpenAI traces |
| demo_user | Clerk user id |
| localhost CORS | configured production origins |

## Acceptance Criteria

- Backend starts locally.
- Frontend starts locally.
- Database initializes locally.
- A mock job completes end-to-end.
- No AWS required.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
