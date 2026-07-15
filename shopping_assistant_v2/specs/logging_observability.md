# Spec: Logging And Observability

## Purpose

Define local structured logs and future observability readiness.

## Correlation Key

Every backend log related to a request or worker run must include:

```text
job_id
```

If no job exists yet, use `request_id`.

## Required Events

- `JOB_CREATED`
- `JOB_STARTED`
- `ROUTER_STARTED`
- `ROUTER_COMPLETED`
- `TOOL_STARTED`
- `TOOL_COMPLETED`
- `SYNTHESIZER_STARTED`
- `SYNTHESIZER_COMPLETED`
- `JOB_COMPLETED`
- `JOB_FAILED`

## Log Shape

Recommended JSON-like structure:

```json
{
  "event": "TOOL_COMPLETED",
  "job_id": "uuid",
  "component": "deal_search_tool",
  "duration_ms": 1234,
  "status": "success",
  "timestamp": "iso8601"
}
```

## What Not To Log

Never log:

- API keys.
- tokens.
- `.env` content.
- full raw credentials.
- private auth headers.

Avoid logging huge raw scraped payloads. Store sanitized summaries.

## Agent Runs

Every agent/tool should write an `agent_runs` row with:

- component name.
- status.
- duration.
- model/provider if used.
- summarized input/output.
- sanitized error.

## Frontend Debug Panel

Optional local debug panel can show:

- job id.
- status.
- last events.
- warnings.

## Future Observability

Later phases can add:

- LangFuse.
- OpenAI traces.
- CloudWatch.
- dashboard by job status.
- error rate metrics.

## Acceptance Criteria

- A failed job can be debugged by `job_id`.
- Logs are readable in local terminal.
- No secrets appear in logs.
- Agent/tool duration is visible.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
