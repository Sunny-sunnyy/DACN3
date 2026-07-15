# Plan 07: Testing And Validation

## Purpose

Define how to verify the app without relying on paid APIs or fragile live scraping.

## Test Philosophy

Default tests must be cheap, deterministic, and local.

Real network/model tests are opt-in and manual until the local architecture is stable.

## Required Test Layers

### Unit Tests

Cover:

- request validation.
- database repository functions.
- job status transitions.
- Router classification fixtures.
- tool schema validation.
- Synthesizer output validation.

### Integration Tests

Cover:

- create job.
- worker processes job.
- job completes.
- result payload is readable.

### Frontend Smoke Tests

Cover:

- submit message.
- show pending/running status.
- render completed product cards.
- render failure state.

### Manual Opt-In Tests

Cover:

- real Amazon/BestBuy search.
- real ensemble pricing.
- real model provider calls.

Manual tests must be documented with expected cost/risk.

## Fixtures

Create fixture data for:

- Amazon candidate.
- BestBuy candidate.
- price estimate output.
- Router intent output.
- Synthesizer final answer.

## Validation Rules

- Product URL must come from tool output.
- Price must come from tool output.
- Missing data must be `unknown`, `not_available`, or warning.
- Job must not stay stuck in `running` after an exception.

## Acceptance Criteria

- Local CI/test command passes without network/model calls.
- Integration test proves job lifecycle.
- Manual real tests are documented and opt-in.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
