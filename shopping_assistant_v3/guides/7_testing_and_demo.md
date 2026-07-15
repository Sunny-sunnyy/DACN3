# Phase 7: Testing And Demo

## Purpose

Harden the local MVP for reliable DATN/CV demonstration.

This phase turns the working local app into a repeatable demo with deterministic
tests, fixtures, known limitations, and opt-in real-mode instructions.

## Current Status

Phase 7 starts after backend, worker, mock tools, Router/Synthesizer, and
frontend chat flow work locally.

## Scope

Implement or complete:

- backend unit tests;
- backend integration test for job lifecycle;
- tool fixture tests;
- Router/Synthesizer fixture tests;
- frontend smoke/component tests;
- manual demo script/checklist;
- opt-in real search/model test documentation;
- known limitations;
- verification commands in docs.

## Non-Goals

- No new major feature development.
- No production deployment.
- No Clerk auth.
- No AWS/Terraform.
- No default live scraping/model tests.
- No broad UI redesign unless required for demo reliability.

## Inputs From Previous Phases

Required:

- Phase 2 API.
- Phase 3 async jobs.
- Phase 4 mock tools.
- Phase 5 Router/Synthesizer.
- Phase 6 frontend chat.

## Contracts

Default tests must not:

- scrape live Amazon/BestBuy;
- call OpenAI;
- call Modal;
- require AWS;
- require secrets.

Required backend tests:

- request validation;
- repository create/update/read;
- job status transition;
- Router fixture classification;
- tool input/output schema validation;
- Synthesizer fixture validation.

Required backend integration test:

```text
create job
-> process by worker in mock mode
-> poll completed result
```

Required frontend tests:

- component render smoke;
- API client handles pending/completed/failed;
- product cards render expected fields.

Manual demo checklist:

- start backend;
- start frontend;
- submit Vietnamese request;
- observe status;
- verify Vietnamese answer;
- verify product cards;
- verify logs contain `job_id`;
- verify failure state if possible.

## Workflow Gate

Before coding:

- Load `using-superpowers`.
- Use `brainstorming` with the user.
- Ask only questions that change scope, design, tests, or implementation plan.
- Confirm which test stacks and demo commands are in scope.
- Present the Phase 7 plan.
- Wait for explicit approval.

## Implementation Order

1. Inventory existing tests.
2. Add missing backend unit tests.
3. Add backend integration test for mock job lifecycle.
4. Add tool fixture tests.
5. Add Router/Synthesizer fixture tests.
6. Add frontend smoke tests.
7. Add manual demo script/checklist.
8. Document opt-in real search/model tests separately.
9. Document known limitations.
10. Run full local verification.
11. Write Phase 7 report.

## Verification

Expected local verification:

```bash
uv run pytest
npm run test
npm run lint
```

Exact commands depend on implementation and must be recorded in the report.

Manual verification must show:

- mock mode demo works reliably;
- no default test requires network/model calls;
- failed job path is visible and safe;
- logs can be traced by `job_id`.

## Report Requirements

Write:

```text
shopping_assistant_v3/reports/phase_7_testing_and_demo_report.md
```

Include:

- commands run;
- tests passed/failed;
- manual demo evidence;
- opt-in real-mode instructions added;
- known limitations;
- whether MVP is demo-ready.

## Risks And Open Questions

- Frontend testing stack may need dependency decisions.
- Live scraper reliability should not block mock demo readiness.
- Real model costs must remain opt-in and documented.
- Demo script should be short enough for repeatable DATN presentation.
