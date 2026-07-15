# Plan 06: Data And Persistence

## Purpose

Define local persistence and future migration path.

## Local MVP Database

Use SQLite first.

Reasons:

- Minimal setup.
- Easy for coding agents.
- Good enough for local DATN demo.
- Avoids blocking on Docker/Postgres.

## Docker Local Support

Even with SQLite default, the project should plan for Docker:

- Backend container.
- Frontend container.
- Optional Postgres/Supabase-like service later.

Docker is for reproducible local development, not a requirement for the first documentation phase.

## Future Database Direction

Future options:

- Supabase as local/managed Postgres research path.
- Postgres Docker.
- Aurora/Postgres if AWS deployment is pursued.

## Core Tables

Required logical tables:

- `jobs`
- `conversations`
- `messages`
- `agent_runs`
- `products`
- `price_estimates`

## Data Ownership

MVP uses `demo_user`.

Future Clerk phase replaces `demo_user` with verified `clerk_user_id`.

Every user-owned table should be designed with `user_id` or ownership path where applicable.

## JSON Payloads

Use JSON columns/text for:

- request payload.
- result payload.
- tool metadata.
- warning lists.

Keep large scraped raw payloads out of core tables unless needed for debugging.

## Acceptance Criteria

- Schema supports job lifecycle.
- Schema supports conversation history.
- Schema supports product and price estimate records.
- Schema can migrate to Postgres without redesigning the app.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
