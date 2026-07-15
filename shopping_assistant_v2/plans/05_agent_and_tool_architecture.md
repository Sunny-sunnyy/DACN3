# Plan 05: Agent And Tool Architecture

## Purpose

Define the controlled agent workflow and tool boundaries.

## Principle

Use Router plus explicit tools for MVP. Do not use free-form ReAct in the first version.

Reason:

- Easier to test.
- Easier to debug.
- Less risk of infinite loops.
- Better for local demo reliability.

## Agent List

### Router

Classifies Vietnamese user intent.

Allowed intents:

- `search_deals`
- `estimate_price`
- `general_product_qa`
- `compare`
- `advisor`
- `unsupported`

MVP only executes `search_deals`.

### Deal Search Tool

Finds candidates from Amazon and/or BestBuy.

### Price Estimator Tool

Estimates fair value in USD using the English ensemble pipeline.

### Vietnamese Synthesizer

Produces final user-facing Vietnamese answer.

### Comparer

Later phase. Compares candidates by price/spec/value.

### Advisor

Later phase. Gives buying advice based on user need and tool evidence.

## Model Provider Policy

Use LiteLLM abstraction.

MVP default:

- OpenAI for Router and Synthesizer.

Future:

- Qwen/vLLM local or external OpenAI-compatible endpoint.

## Structured Output Policy

Router and Synthesizer should use structured schemas where possible.

Rules:

- Model output must be validated.
- Invalid output triggers fallback or retry.
- Tool evidence is source of truth for price/spec/URL.
- The assistant must not invent unavailable prices.

## Trace And Audit

Each agent/tool run should save:

- `job_id`.
- `agent_name` or `tool_name`.
- start/end time.
- model/provider if used.
- status.
- sanitized input summary.
- sanitized output summary.
- error if failed.

## Acceptance Criteria

- Router can classify Vietnamese search examples.
- Search tool can run from a normalized English query.
- Price tool can process normalized candidates.
- Synthesizer can produce Vietnamese answer from fixture evidence.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
