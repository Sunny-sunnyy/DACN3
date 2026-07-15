# Plan 08: Roadmap To Production

## Purpose

Define later production-oriented steps without blocking the local MVP.

## Phase After Local MVP

### Auth

Add Clerk:

- frontend login.
- backend JWT verification.
- per-user authorization.
- replace `demo_user`.

### Database

Move from SQLite to:

- Supabase/Postgres for local/managed development, or
- Aurora/Postgres for AWS production.

### Queue

Move from local worker to:

- SQS-compatible local queue, or
- AWS SQS.

### Deployment

Only after local app is stable:

- backend deployment plan.
- frontend deployment plan.
- secrets management.
- cost controls.

## Production-Like Concerns

Required later:

- CORS restrictions.
- rate limiting.
- prompt injection guardrails.
- structured logs.
- tracing.
- audit events.
- retries.
- DLQ.
- model timeout/fallback.
- scraper source safety.

## AWS Is Later

Do not implement AWS before local app works.

AWS target can eventually include:

- API Gateway/FastAPI.
- SQS workers.
- Postgres/Aurora.
- CloudWatch.
- S3/static frontend.

But for the current project stage, AWS is explicitly deferred.

## Acceptance Criteria For Moving Beyond Local

- Local MVP works reliably.
- Tests pass.
- Tool contracts are stable.
- Demo script exists.
- Known failure modes are documented.
- User explicitly approves production phase.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
