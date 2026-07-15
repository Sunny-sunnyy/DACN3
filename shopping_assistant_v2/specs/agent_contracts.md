# Spec: Agent Contracts

## Purpose

Define agent responsibilities and structured outputs.

## Router Agent

### Input

```json
{
  "message_vi": "Tìm laptop gaming dưới 800 đô",
  "conversation_context": []
}
```

### Output

```json
{
  "intent": "search_deals",
  "query_en": "gaming laptop under 800 dollars",
  "source": "All",
  "max_results_per_source": 6,
  "confidence": 0.9,
  "needs_tool": true
}
```

### Allowed Intents

- `search_deals`
- `estimate_price`
- `general_product_qa`
- `compare`
- `advisor`
- `unsupported`

MVP executes only `search_deals`.

## Vietnamese Synthesizer

### Input

```json
{
  "message_vi": "Tìm laptop gaming dưới 800 đô",
  "products": [],
  "price_estimates": [],
  "warnings": []
}
```

### Output

```json
{
  "answer_vi": "Mình tìm được vài lựa chọn đáng chú ý...",
  "summary_cards": [],
  "warnings_vi": []
}
```

### Rules

- Answer in Vietnamese.
- Preserve product names in English when clearer.
- Prices remain USD.
- Do not invent price/spec/source.
- Mention source failures if relevant.

## Comparer Agent

Later phase.

Input:

- products.
- price estimates.
- user criteria.

Output:

- comparison table.
- ranked recommendation.
- pros/cons.

## Advisor Agent

Later phase.

Input:

- user need.
- comparison result.
- price estimates.

Output:

- recommended pick.
- explanation.
- caveats.

## Model Provider

Use LiteLLM abstraction.

Required config:

- `MODEL_ID_ROUTER`
- `MODEL_ID_SYNTHESIZER`

Defaults can be OpenAI models for MVP stability.

## Validation

Every model output must be schema-validated.

If validation fails:

1. retry once with stricter instruction, or
2. use fallback deterministic response.

## Acceptance Criteria

- Router classifies Vietnamese examples.
- Synthesizer produces Vietnamese output from fixtures.
- Unsupported intents return safe fallback.
- Agent runs are logged in `agent_runs`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
