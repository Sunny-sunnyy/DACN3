# Spec: Testing Strategy

## Purpose

Define required tests for the V2 project.

## Default Test Mode

Default tests must not:

- scrape live Amazon/BestBuy.
- call OpenAI.
- call Modal.
- require AWS.

Use fixtures and mocks.

## Backend Unit Tests

Required:

- API request validation.
- database repository create/update/read.
- job status transition.
- Router fixture classification.
- tool input/output schema validation.
- Synthesizer fixture validation.

## Backend Integration Tests

Required:

```text
create job
-> process by worker in mock mode
-> poll completed result
```

## Tool Tests

Required:

- deal search mock fixture.
- price estimator mock fixture.
- warnings preserved.
- invalid input rejected.

Optional manual:

- real Amazon search.
- real BestBuy search.
- real ensemble pricing.

## Frontend Tests

Required:

- component render smoke.
- API client handles pending/completed/failed.
- product cards render expected fields.

## Manual Demo Checklist

- Start backend.
- Start frontend.
- Submit Vietnamese request.
- Observe status.
- Verify Vietnamese answer.
- Verify product cards.
- Verify logs contain `job_id`.

## Acceptance Criteria

- Local tests pass without network/model calls.
- There is a separate opt-in path for real external tests.
- Failed cases are tested.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
