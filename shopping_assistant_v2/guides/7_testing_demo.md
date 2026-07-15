# Guide 7: Testing And Demo

## Goal

Prepare the project for reliable local demonstration.

## What You Will Build

- local test commands.
- mock-mode test fixtures.
- manual real-mode checklist.
- demo script.

## Prerequisites

- `specs/testing_strategy.md`
- backend and frontend implemented enough for MVP.

## Steps

1. Add backend unit tests.
2. Add backend integration test for job lifecycle.
3. Add tool fixture tests.
4. Add frontend smoke tests.
5. Add manual demo script.
6. Add opt-in real search/model test instructions.
7. Document known limitations.

## Verify

- Local tests pass without paid APIs.
- Demo can run with mock mode.
- Real mode instructions are clearly marked opt-in.
- Logs can be filtered by `job_id`.

## Troubleshooting

- If tests require network unexpectedly, replace with fixture.
- If demo is flaky, reduce live dependencies and use stable mock path.

## Next Guide

Continue to `guides/8_future_production.md` when local MVP is stable.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
