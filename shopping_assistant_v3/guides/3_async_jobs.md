# Phase 3: Async Jobs

## Purpose

Implement the local async job lifecycle and deterministic mock completion path.

This phase proves that jobs move from `pending` to `running` to `completed` or
`failed`, and that the frontend will later be able to poll status without the API
blocking on long work.

## Current Status

Phase 3 starts after Phase 2 backend API and SQLite repositories work.

The API can create and read `pending` jobs, but no worker processes them yet.

## Scope

Implement:

- local worker entry point or background worker path;
- status transitions;
- idempotency for already completed jobs;
- deterministic mock result payload;
- failed job path with sanitized error;
- structured logs by `job_id`;
- `agent_runs` audit rows for worker execution.

## Non-Goals

- No real Router model calls.
- No real search/pricing tools.
- No frontend implementation.
- No queue/SQS.
- No production observability.
- No live scraping or paid API calls.

## Inputs From Previous Phases

Required:

- Phase 2 API endpoints.
- Phase 2 SQLite schema/repository.
- `guides/architecture.md`.

## Contracts

Job lifecycle:

```text
pending -> running -> completed
pending -> running -> failed
```

Worker flow:

```text
worker receives job_id
-> load job
-> if completed, return existing result
-> if not pending, skip or report safe state
-> set running
-> write deterministic mock result
-> set completed
```

Error flow:

```text
catch exception
-> log JOB_FAILED
-> save sanitized error_message
-> set failed
```

Mock completed result shape:

```json
{
  "answer_vi": "Mình đã tìm thấy một số lựa chọn mẫu để kiểm tra luồng demo.",
  "products": [
    {
      "source": "BestBuy",
      "title": "Mock Gaming Laptop",
      "brand": "MockBrand",
      "sale_price_usd": 699.99,
      "estimated_value_usd": 899.99,
      "discount_usd": 200.0,
      "deal_score": "hot",
      "url": "https://www.bestbuy.com/"
    }
  ],
  "warnings": []
}
```

Required log events:

- `JOB_STARTED`
- `JOB_COMPLETED`
- `JOB_FAILED`

## Workflow Gate

Before coding:

- Load `using-superpowers`.
- Use `brainstorming` with the user.
- Ask only questions that change scope, design, tests, or implementation plan.
- Present the Phase 3 plan.
- Wait for explicit approval.

## Implementation Order

1. Confirm Phase 2 report and tests pass.
2. Choose worker mode for MVP:
   - FastAPI background task for simplest local slice; or
   - separate local worker process for cleaner future queue mapping.
3. Add worker function for one `job_id`.
4. Add repository update helpers for status/result/error.
5. Add deterministic mock result.
6. Add full-worker exception handling.
7. Add structured logs and `agent_runs` rows.
8. Add tests for completed and failed paths.
9. Write Phase 3 report.

## Verification

Required checks:

- Create job through API.
- Process job through local worker.
- Poll job and see `completed` result.
- Trigger controlled failure and see `failed` status.
- Confirm logs include `job_id`.
- Confirm rerunning completed job does not duplicate/conflict.

Example commands depend on implementation:

```bash
uv run pytest <job tests>
curl -s http://localhost:8000/api/chat-jobs/<job_id>
```

No test in this phase may require network/model/scraping.

## Report Requirements

Write:

```text
shopping_assistant_v3/reports/phase_3_async_jobs_report.md
```

Include:

- chosen worker mode and why;
- job transition evidence;
- failure-path evidence;
- exact commands run;
- test results;
- idempotency behavior;
- remaining risks.

## Risks And Open Questions

- Background tasks are simpler but less production-like than a separate worker.
  Either is acceptable if documented.
- If jobs can get stuck in `running`, the implementation is not acceptable.
- The mock result should be obviously mocked to avoid claiming real search.
