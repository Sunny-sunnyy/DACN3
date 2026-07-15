# Guide 3: Async Jobs

## Goal

Implement the local async job lifecycle.

## What You Will Build

- job status transitions.
- local worker.
- mock result generation.
- structured logs by `job_id`.

## Prerequisites

- `guides/2_backend_api.md`
- `specs/job_orchestration.md`
- `specs/logging_observability.md`

## Files Involved

Future files:

```text
backend/router/
backend/shared/logging.py
backend/database/
```

## Steps

1. Add worker entry point.
2. Worker receives or polls `job_id`.
3. Worker loads job.
4. Worker sets status `running`.
5. Worker writes deterministic mock result.
6. Worker sets status `completed`.
7. On exception, worker sets status `failed`.
8. API polling reads current status.

## Verify

- Create a job.
- Worker completes it.
- Polling shows completed result.
- Failed mock path stores safe error.
- Logs include `JOB_CREATED`, `JOB_STARTED`, `JOB_COMPLETED`.

## Troubleshooting

- If jobs get stuck in `running`, add exception handling around the whole worker.
- If repeated worker runs duplicate rows, add idempotency checks.

## Next Guide

Continue to `guides/4_extract_search_pricing_tools.md`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
