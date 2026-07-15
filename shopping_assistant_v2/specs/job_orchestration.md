# Spec: Job Orchestration

## Purpose

Define the async `job_id` backbone.

## Job Lifecycle

```text
pending -> running -> completed
pending -> running -> failed
```

Future:

```text
pending -> queued -> running -> partial -> completed
```

## Create Job Flow

```text
POST /api/chat-jobs
-> validate request
-> sanitize message
-> create jobs row
-> return job_id immediately
-> local worker picks job
```

## Worker Flow

```text
worker receives job_id
-> load job
-> if status is not pending, skip or report idempotent result
-> set status running
-> run router
-> run required tools
-> run synthesizer
-> save result_payload
-> set status completed
```

On error:

```text
catch exception
-> log structured failure
-> save sanitized error_message
-> set status failed
```

## Router Execution

Router must:

- load original Vietnamese message.
- classify intent.
- execute only allowed MVP path for `search_deals`.
- produce fallback for unsupported intent.
- save an `agent_runs` record.

## Tool Execution

Each tool must:

- validate input.
- log start/completion.
- return structured output.
- save audit event.
- raise typed errors for recoverable failure.

## Idempotency

If the same job is processed twice:

- do not duplicate product rows if they already exist.
- do not append conflicting final result.
- safe option: if status is `completed`, return existing result.

## Timeouts

MVP recommended local timeouts:

- Router: 20 seconds.
- Search tool: 120 seconds if real network enabled.
- Price estimator: 180 seconds if real model enabled.
- Synthesizer: 60 seconds.

Mock mode should complete much faster.

## Acceptance Criteria

- API returns immediately with `job_id`.
- Job status changes are visible through polling.
- Failed job stores safe error.
- Logs can be correlated by `job_id`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
