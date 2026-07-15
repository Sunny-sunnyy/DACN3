# Guide 6: Frontend Chat

## Goal

Implement the Next.js chat-first frontend.

## What You Will Build

- chat input.
- job submission.
- job polling.
- Vietnamese answer rendering.
- product result cards.
- debug job panel.

## Prerequisites

- `specs/frontend_contract.md`
- `specs/api_contract.md`
- backend API running locally.

## Files Involved

Future files:

```text
frontend/
frontend/components/
frontend/lib/
```

## Steps

1. Choose App Router or Pages Router explicitly.
2. Create API client.
3. Create chat page.
4. Submit message to `POST /api/chat-jobs`.
5. Poll `GET /api/chat-jobs/{job_id}`.
6. Render status states.
7. Render final answer.
8. Render product cards.
9. Add debug panel with job id and warnings.

## Verify

- User can submit Vietnamese query.
- UI shows pending/running state.
- Completed job renders answer and cards.
- Failed job renders safe error.

## Troubleshooting

- If CORS fails, verify backend CORS origins include `http://localhost:3000`.
- If polling never stops, check backend job status.
- If product card fields are missing, validate API response shape.

## Next Guide

Continue to `guides/7_testing_demo.md`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
