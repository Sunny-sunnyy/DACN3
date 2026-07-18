# Sidekick Patterns Brainstorm Report

Date: 2026-07-18
Reviewer/Facilitator: Codex
Status: brainstorm approved by user; not an implementation approval

## Tóm Tắt

User asked to review `shopping_assistant_v2/README_Project_Sidekick.md` and
identify useful ideas for `shopping_assistant_v3`.

Decision: V3 should be treated as a domain-specific Vietnamese Shopping
Sidekick, but it must keep the current controlled FastAPI worker, Router, and
explicit tool architecture. Do not migrate V3 to LangChain/LangGraph or a
free-form autonomous browser agent.

## Approved Direction

- Use Sidekick patterns only, not the Sidekick framework.
- Keep V3 local-first, mock-safe, and evidence-first.
- Start with deterministic planning/progress.
- Add evidence evaluator as test-only first.
- Defer dynamic todo lists, runtime evaluators, LLM-as-a-Judge, HITL approvals,
  and budget middleware to later phases or roadmap.

## Cross-Phase Mapping

### Phase 4A

Prepare tool evidence contracts:

- `deal_search_tool` preserves source, normalized product fields, and warnings.
- `price_estimator_tool` preserves estimate fields, deal score, and warnings.
- Tool outputs should be enough for later progress mapping without reading raw
  scraped payloads.

### Phase 5

Add deterministic `progress_steps` to backend job response.

Initial contract:

```text
step_id
title_vi
status
detail_vi
```

Allowed `step_id` values:

```text
route_request
search_deals
estimate_prices
synthesize_answer
```

Allowed `status` values:

```text
pending
running
completed
failed
skipped
```

Future optional fields:

```text
component
started_at
completed_at
warnings
agent_run_id
```

### Phase 6

Render a Sidekick-style progress panel from backend `progress_steps`.

Frontend must not hardcode completed work that backend did not report.

### Phase 7

Add rule-based test-only evidence evaluator.

Validator should check:

- final answer does not invent prices, URLs, product titles, or warnings;
- product cards match tool/result evidence;
- progress steps do not claim completion when evidence is missing;
- default tests require no network, model calls, AWS, or secrets.

### Phase 8

Document optional future upgrades:

- evidence-linked progress fields;
- dynamic LLM-generated todo lists;
- runtime evidence validator;
- LLM-as-a-Judge;
- HITL approvals;
- budget and tool error policy hardening.

## Non-Goals

- No runtime implementation in this brainstorm step.
- No edits to `segment4/`.
- No edits to `shopping_assistant_v2/`.
- No live scraping.
- No paid model calls.
- No dependency installation.
- No project phase status change.

## Files Updated From This Brainstorm

```text
shopping_assistant_v3/guides/4_search_and_pricing_tools.md
shopping_assistant_v3/guides/5_router_and_synthesizer.md
shopping_assistant_v3/guides/6_frontend_chat.md
shopping_assistant_v3/guides/7_testing_and_demo.md
shopping_assistant_v3/guides/8_production_roadmap.md
shopping_assistant_v3/guides/agent_architecture.md
shopping_assistant_v3/guides/architecture.md
shopping_assistant_v3/gameplan.md
shopping_assistant_v3/README.md
shopping_assistant_v3/reports/sidekick_patterns_brainstorm_report.md
```

## Impact On Current Phase

This does not affect runtime behavior because it is documentation-only.

Because Phase 4A has not been implemented yet, adding this guidance now reduces
rework: the Phase 4A implementer can design mock tool evidence and warnings with
Phase 5 progress and Phase 7 evidence validation in mind.
