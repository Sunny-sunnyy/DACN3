# Architecture

## Summary

V2 is a Vietnamese-speaking assistant layered over a US product search and pricing backend.

```text
Vietnamese Chat UI
-> FastAPI job API
-> Router
-> Search/Pricing tools
-> Vietnamese Synthesizer
-> Product cards
```

## Local MVP Diagram

```text
Browser
  |
  v
Next.js Frontend
  |
  v
FastAPI Backend
  |
  +--> SQLite
  |
  +--> Local Worker
          |
          +--> Router
          +--> Deal Search Tool
          +--> Price Estimator Tool
          +--> Synthesizer
```

## Design Principles

- Local-first before production.
- Async jobs before long blocking requests.
- Tool evidence before model narrative.
- Vietnamese UX, English product data.
- `segment4` remains reference-only.
- Tests use fixtures by default.

## Future Architecture

Future production can map:

- SQLite -> Postgres/Supabase/Aurora.
- local worker -> queue/SQS.
- console logs -> CloudWatch/traces.
- demo_user -> Clerk user id.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
