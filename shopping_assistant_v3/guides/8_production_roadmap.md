# Phase 8: Production Roadmap

## Purpose

Document the production path after the local MVP is stable. This phase is a
planning and hardening roadmap, not a deployment phase by default.

## Current Status

Production work must not start until:

- local MVP works;
- tests pass;
- demo script exists;
- known failure modes are documented;
- user explicitly approves production work.

## Scope

Plan future work for:

- Clerk auth.
- Postgres/Supabase/Aurora migration.
- queue-backed workers.
- production deployment.
- production observability.
- cost controls.
- scraper safety.
- optional Compare and Advisor agents.

## Non-Goals

Unless explicitly approved:

- no AWS commands;
- no Terraform;
- no production deploy;
- no Clerk implementation;
- no database migration execution;
- no paid production observability setup;
- no live scraping scale work.

## Inputs From Previous Phases

Required:

- Phase 7 test/demo report.
- Current architecture and known limitations.
- Any approved implementation reports that changed contracts.

Optional references:

- `segment4/mo_ta_du_an/ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md` for
  production patterns.

## Contracts

Future production mapping:

| Local MVP | Production Candidate |
|---|---|
| SQLite | Postgres, Supabase, Aurora |
| local worker | queue-backed worker, SQS |
| console logs | CloudWatch, LangFuse, OpenAI traces |
| `demo_user` | Clerk user id |
| localhost CORS | explicit production origins |
| mock defaults | opt-in real service configs |

Production readiness concerns:

- CORS restrictions.
- auth and per-user authorization.
- rate limiting.
- prompt injection guardrails.
- structured logs.
- audit events.
- retries and timeouts.
- dead-letter queue.
- model timeout/fallback.
- scraper source safety.
- dashboard and alarms.
- cost tracking.

## Workflow Gate

Before coding or production planning:

- Load `using-superpowers`.
- Use `brainstorming` with the user.
- Ask only questions that change scope, design, tests, or implementation plan.
- Confirm production work is explicitly approved.
- Present the Phase 8 plan.
- Wait for explicit approval.

## Implementation Order

1. Review Phase 7 report and current known limitations.
2. Identify blockers to production readiness.
3. Decide production target:
   - local Docker only;
   - Supabase/Postgres local/managed;
   - AWS;
   - another deployment platform.
4. Write an architecture decision for the next production step if approved.
5. Split production work into separate future guides or update this guide.
6. Do not deploy until the user approves a specific production implementation
   plan.

## Verification

This phase verifies documentation quality, not deployed infrastructure.

Checks:

- roadmap clearly says what is planned versus implemented;
- no production task is marked complete without evidence;
- local MVP remains the baseline;
- cost and secret handling are explicit;
- next production step has a review gate.

## Report Requirements

If Phase 8 is run as a planning phase, write:

```text
shopping_assistant_v3/reports/phase_8_production_roadmap_report.md
```

Include:

- production option chosen or deferred;
- risks;
- estimated cost categories;
- docs updated;
- next phase recommendation.

## Risks And Open Questions

- AWS can add cost and operational complexity before the product is stable.
- Clerk auth changes database ownership assumptions.
- Real scraping at scale may need proxy/session/rate-limit strategy.
- Production observability should not expose user data or secrets.
- Compare/Advisor agents should wait until search + price + summary are stable.
