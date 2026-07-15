# Agent Architecture

## MVP Pattern

Use controlled routing, not free-form ReAct.

```text
Router
  -> deal_search_tool
  -> price_estimator_tool
  -> Vietnamese Synthesizer
```

## Router

Responsibilities:

- classify Vietnamese user intent.
- produce English query for search tool.
- decide source filter.
- reject unsupported tasks safely.

## Tools

Tools are not conversational agents. They provide structured evidence.

Required tools:

- `deal_search_tool`
- `price_estimator_tool`

## Synthesizer

Responsibilities:

- answer in Vietnamese.
- preserve USD prices.
- explain deal value.
- show warnings.
- avoid hallucinating unavailable facts.

## Later Agents

- Comparer.
- Advisor.

These are planned but not required for MVP.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
