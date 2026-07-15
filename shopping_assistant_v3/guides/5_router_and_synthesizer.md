# Phase 5: Router And Synthesizer

## Purpose

Implement assistant behavior around the tool contracts: route Vietnamese user
requests, run the allowed tool path, and produce a Vietnamese answer from
structured evidence.

## Current Status

Phase 5 starts after job lifecycle exists and mock tools are available.

The app can create/process jobs, but it does not yet understand Vietnamese user
intent or synthesize final answers from tool evidence.

## Scope

Implement:

- Router schemas.
- deterministic/mock Router behavior.
- optional LiteLLM/OpenAI Router provider behind opt-in config.
- Vietnamese Synthesizer schemas.
- deterministic/mock Synthesizer behavior from evidence.
- optional model-backed Synthesizer behind opt-in config.
- unsupported intent fallback.
- validation that final answers do not invent price/spec/URL fields.
- `agent_runs` audit records for Router and Synthesizer.

## Non-Goals

- No free-form ReAct loop.
- No compare/advisor execution.
- No frontend implementation.
- No default paid model calls.
- No live scraping/model calls in tests.

## Inputs From Previous Phases

Required:

- Phase 3 async jobs.
- Phase 4A mock tools.
- `guides/agent_architecture.md`.

Recommended:

- Phase 4B/4C real tools can be absent; mock tools are enough for this phase.

## Contracts

### Router Input

```json
{
  "message_vi": "Tìm laptop gaming dưới 800 đô",
  "conversation_context": []
}
```

### Router Output

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

MVP executes only:

```text
search_deals
```

Other intents return safe Vietnamese fallback.

### Synthesizer Input

```json
{
  "message_vi": "Tìm laptop gaming dưới 800 đô",
  "products": [],
  "price_estimates": [],
  "warnings": []
}
```

### Synthesizer Output

```json
{
  "answer_vi": "Mình tìm được vài lựa chọn đáng chú ý...",
  "summary_cards": [],
  "warnings_vi": []
}
```

Rules:

- answer in Vietnamese;
- preserve USD;
- preserve English product names when clearer;
- mention source/tool warnings if relevant;
- never invent fields not provided by tools.

## Workflow Gate

Before coding:

- Load `using-superpowers`.
- Use `brainstorming` with the user.
- Ask only questions that change scope, design, tests, or implementation plan.
- Confirm whether model-backed Router/Synthesizer is allowed or mock-only.
- Present the Phase 5 plan.
- Wait for explicit approval.

## Implementation Order

1. Confirm Phase 4A report and tests pass.
2. Add Router schemas and fixture tests.
3. Implement deterministic Router for common Vietnamese search queries.
4. Add unsupported fallback behavior.
5. Add Synthesizer schemas and fixture tests.
6. Implement deterministic Synthesizer from product and estimate evidence.
7. Integrate Router -> tools -> Synthesizer into worker path.
8. Add validation that product cards and final text are backed by evidence.
9. Add optional model provider wrapper only if user approves paid/local provider
   behavior.
10. Write Phase 5 report.

## Verification

Default required tests:

- Vietnamese query routes to `search_deals`.
- Router produces English query.
- unsupported query returns fallback.
- Synthesizer returns Vietnamese answer from fixtures.
- Synthesizer preserves warnings.
- Worker completes with Router/tools/Synthesizer mock path.
- No default test calls OpenAI or live scraping.

Example:

```bash
uv run pytest <router and synthesizer tests>
uv run pytest <worker integration test>
```

Manual checks:

- Submit: `Tìm laptop gaming dưới 800 đô`.
- Confirm result includes Vietnamese answer and product cards.
- Confirm no price/URL appears unless present in tool output.

## Report Requirements

Write:

```text
shopping_assistant_v3/reports/phase_5_router_and_synthesizer_report.md
```

Include:

- Router strategy: deterministic, model-backed, or both.
- Synthesizer strategy.
- model calls made, if any.
- validation evidence.
- unsupported intent behavior.
- remaining hallucination risks.

## Risks And Open Questions

- Deterministic Router may be too limited, but it is safer for mock MVP.
- Model-backed Router/Synthesizer require paid/local provider risk management.
- Vietnamese answer quality should improve later, but correctness from evidence
  is more important than style in MVP.
