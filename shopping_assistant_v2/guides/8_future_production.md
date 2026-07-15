# Guide 8: Future Production

## Goal

Document the production roadmap without implementing it before local MVP is stable.

## Future Work

### Auth

- Add Clerk frontend auth.
- Verify Clerk JWT in backend.
- Enforce per-user job ownership.

### Database

- Evaluate Supabase/Postgres.
- Migrate SQLite schema to Postgres.
- Add migrations.

### Queue

- Replace local worker with queue-backed worker.
- Later AWS SQS if deploying AWS.

### Deployment

- Deploy only after local MVP passes tests.
- Define secrets handling.
- Define CORS origins.
- Define cost controls.

### Observability

- Add traces.
- Add dashboards.
- Add error metrics.
- Add audit events.

## Stop Gates

Do not proceed to production until:

- local MVP works.
- tests pass.
- UI demo is stable.
- user explicitly approves production phase.

## Verify

- Future tasks are documented as planned, not implemented.
- No AWS command is run from this guide without approval.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
