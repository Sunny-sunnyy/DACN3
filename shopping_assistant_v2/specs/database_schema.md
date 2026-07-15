# Spec: Database Schema

## Purpose

Define the SQLite-first schema with future Postgres compatibility.

## Status Values

MVP statuses:

```text
pending
running
completed
failed
```

Future statuses:

```text
queued
partial
cancelled
```

## Tables

### `jobs`

Stores async job lifecycle.

Fields:

- `id`: text primary key, UUID.
- `user_id`: text, default `demo_user`.
- `job_type`: text, e.g. `chat_search`.
- `status`: text.
- `request_payload`: JSON text.
- `result_payload`: JSON text nullable.
- `error_message`: text nullable.
- `created_at`: timestamp.
- `started_at`: timestamp nullable.
- `completed_at`: timestamp nullable.
- `updated_at`: timestamp.

Indexes:

- `(user_id, created_at)`
- `(status, created_at)`

### `conversations`

Stores chat sessions.

Fields:

- `id`: text primary key.
- `user_id`: text.
- `title`: text nullable.
- `created_at`: timestamp.
- `updated_at`: timestamp.

### `messages`

Stores chat messages.

Fields:

- `id`: text primary key.
- `conversation_id`: text.
- `job_id`: text nullable.
- `role`: `user`, `assistant`, `system`, `tool`.
- `content`: text.
- `metadata`: JSON text nullable.
- `created_at`: timestamp.

### `agent_runs`

Stores audit trail.

Fields:

- `id`: text primary key.
- `job_id`: text.
- `agent_name`: text.
- `run_type`: `router`, `tool`, `synthesizer`, `worker`.
- `status`: text.
- `model_provider`: text nullable.
- `model_name`: text nullable.
- `input_summary`: text nullable.
- `output_summary`: text nullable.
- `error_message`: text nullable.
- `started_at`: timestamp.
- `completed_at`: timestamp nullable.
- `duration_ms`: integer nullable.
- `metadata`: JSON text nullable.

### `products`

Stores normalized product candidates.

Fields:

- `id`: text primary key.
- `job_id`: text.
- `source`: `Amazon` or `BestBuy`.
- `title`: text.
- `brand`: text nullable.
- `sale_price_usd`: real.
- `url`: text.
- `features`: text nullable.
- `raw_payload`: JSON text nullable.
- `created_at`: timestamp.

Indexes:

- `(job_id)`
- `(source)`

### `price_estimates`

Stores fair price estimation results.

Fields:

- `id`: text primary key.
- `job_id`: text.
- `product_id`: text.
- `estimated_value_usd`: real.
- `discount_usd`: real.
- `deal_score`: text.
- `confidence`: real nullable.
- `model_breakdown`: JSON text nullable.
- `created_at`: timestamp.

## Migration Notes

Use SQLite JSON as text. For Postgres, migrate JSON text fields to `jsonb`.

Avoid SQLite-only behavior that is hard to migrate.

## Acceptance Criteria

- A job can be created, updated, completed, and failed.
- Product candidates can be linked to a job.
- Price estimates can be linked to product candidates.
- Agent/tool runs can be audited by `job_id`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
