# Guide 5: Router And Synthesizer

## Goal

Implement the assistant behavior around tools.

## What You Will Build

- controlled Router.
- Vietnamese Synthesizer.
- schema validation.
- unsupported intent fallback.

## Prerequisites

- `specs/agent_contracts.md`
- `specs/tool_contracts.md`
- backend job lifecycle works.

## Files Involved

Future files:

```text
backend/router/
backend/synthesizer/
backend/shared/guardrails.py
```

## Steps

1. Define Router schemas.
2. Add fixture tests for Vietnamese queries.
3. Implement LiteLLM/OpenAI provider wrapper.
4. Implement Router with structured output.
5. Implement fallback Router behavior for mock/no-model mode.
6. Define Synthesizer schemas.
7. Implement Vietnamese Synthesizer from structured evidence.
8. Reject hallucinated prices/specs by validating against tool outputs.

## Verify

- Vietnamese search intent routes to `search_deals`.
- Unsupported question returns safe fallback.
- Synthesizer answer is Vietnamese.
- Product prices in answer match tool output.

## Troubleshooting

- If model structured output is invalid, retry once or use deterministic fallback.
- If the model translates product names poorly, preserve English product names in cards.

## Next Guide

Continue to `guides/6_frontend_chat.md`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
