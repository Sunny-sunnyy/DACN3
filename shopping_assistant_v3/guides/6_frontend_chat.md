# Phase 6: Frontend Chat

## Purpose

Build the Next.js chat-first frontend that submits Vietnamese messages, polls
job status, and renders Vietnamese answers with product cards.

## Current Status

Phase 6 starts after the backend can complete a mock end-to-end job and return a
result payload matching the API contract.

No frontend exists until this phase or Phase 1 creates a skeleton.

## Scope

Implement:

- Next.js frontend app.
- API client for backend job endpoints.
- chat input and submit flow.
- job polling.
- status display.
- Vietnamese answer rendering.
- product cards.
- warnings display.
- debug panel with `job_id`.
- failed state display.

## Non-Goals

- No marketing landing page.
- No production auth.
- No payment/subscription.
- No advanced UI polish before backend contracts work.
- No direct scraping/model calls from frontend.
- No server-side product search in frontend.

## Inputs From Previous Phases

Required:

- Phase 2 API contract.
- Phase 3/5 completed job result shape.
- `guides/architecture.md`.

Optional:

- Phase 7 may later expand demo polish and tests.

## Contracts

Frontend flow:

```text
user enters Vietnamese message
-> POST /api/chat-jobs
-> receive job_id
-> poll GET /api/chat-jobs/{job_id}
-> render pending/running/completed/failed
```

Required UI states:

- `idle`
- `submitting`
- `pending`
- `running`
- `completed`
- `failed`

Required components:

- `ChatPanel`
- `JobStatus`
- `ProductResults`
- `ProductCard`
- `DebugLogPanel`

Product card fields:

```json
{
  "source": "Amazon",
  "title": "Example Laptop",
  "brand": "Example",
  "sale_price_usd": 699.99,
  "estimated_value_usd": 890.0,
  "discount_usd": 190.01,
  "deal_score": "good",
  "url": "https://www.amazon.com/..."
}
```

Polling:

- every 1 second while `pending` or `running`;
- stop on `completed` or `failed`;
- show a timeout/long wait warning if needed.

Accessibility minimum:

- inputs have labels;
- buttons have readable text;
- status is visible;
- product links open safely.

## Workflow Gate

Before coding:

- Load `using-superpowers`.
- Use `brainstorming` with the user.
- Ask only questions that change scope, design, tests, or implementation plan.
- Confirm frontend package/router choices before scaffolding.
- Present the Phase 6 plan.
- Wait for explicit approval.

## Implementation Order

1. Confirm backend can return completed mock result.
2. Choose App Router or Pages Router explicitly.
3. Create frontend structure.
4. Define TypeScript types matching API contract.
5. Implement API client.
6. Implement chat input and submit state.
7. Implement polling.
8. Implement status display.
9. Implement answer and product card rendering.
10. Implement warning and failed state display.
11. Add debug panel with `job_id`.
12. Add frontend smoke tests if project tooling supports them.
13. Write Phase 6 report.

## Verification

Manual checks:

- User can submit Vietnamese query.
- UI receives `job_id`.
- UI shows `pending`/`running`.
- UI renders completed Vietnamese answer.
- UI renders product cards.
- Failed job renders safe error.
- Debug `job_id` is visible.

Commands depend on frontend tooling. Expected examples:

```bash
npm run lint
npm run test
npm run dev
```

Only run dependency install or package scripts after the user has approved the
frontend package setup.

## Report Requirements

Write:

```text
shopping_assistant_v3/reports/phase_6_frontend_chat_report.md
```

Include:

- router choice: App Router or Pages Router;
- files/components created;
- API contract assumptions;
- commands run;
- screenshot/manual validation notes if available;
- remaining UI risks.

## Risks And Open Questions

- UI visual style is intentionally not fixed yet.
- CORS may require backend config updates.
- Product text can be long; card layout must not break on long English titles.
- Debug panel is useful for DATN demo but should not expose secrets or stack
  traces.
