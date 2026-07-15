# Decisions

## Decision 1: V2 Product Positioning

Use Vietnamese-speaking US deal assistant.

Reason:

- English search/pricing pipeline is more practical.
- Vietnamese pricing experiments are not strong enough for product core.
- DATN/CV value comes from a working agentic app.

## Decision 2: New App Folder

Use `shopping_assistant_v2/`.

Reason:

- avoid breaking `segment4`.
- clean story for CV/demo.
- easier for coding agents to work in isolated structure.

## Decision 3: Router Plus Controlled Tools

Use controlled Router for MVP, not free-form ReAct.

Reason:

- easier to test.
- safer for demo.
- fewer loops and hidden failures.

## Decision 4: Async Job Local-First

Use `job_id` from the start.

Reason:

- scraping and model calls can be slow.
- frontend should not wait on one long request.
- maps cleanly to future queue/SQS.

## Decision 5: SQLite First

Use SQLite for local MVP, keep schema migration-friendly.

Reason:

- simplest local setup.
- enough for demo.
- Postgres/Supabase can come later.

## Decision 6: OpenAI/LiteLLM First

Use LiteLLM with OpenAI defaults for Router/Synthesizer.

Reason:

- stable local demo.
- provider can be swapped later.
- avoids requiring GPU for MVP.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
