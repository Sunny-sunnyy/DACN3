# Spec: Migration From Segment4

## Purpose

Define how to reuse the working `segment4` prototype without turning V2 into a tangled dependency.

## Source Reference

Primary reference:

- `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`

Important code areas:

- `segment4/search_key.py`
- `segment4/multi_source_framework.py`
- `segment4/price_agents/multi_source_planning_agent.py`
- `segment4/price_agents/bestbuy_deals.py`
- `segment4/price_agents/amazon_deals.py`
- `segment4/bestbuy_untils/unified_deal.py`
- `segment4/bestbuy_untils/multi_source_scanner_agent.py`
- `segment4/price_agents/ensemble_agent.py`
- `segment4/price_agents/frontier_agent.py`
- `segment4/price_agents/specialist_agent.py`
- `segment4/price_agents/neural_network_agent.py`

## Migration Rule

Do not import directly from `segment4` in V2 by default.

Recommended approach:

1. Read relevant code with CodeGraph.
2. Identify minimal behavior needed.
3. Extract/adapt into V2 tool modules.
4. Add fixture tests.
5. Add optional real tests.
6. Leave `segment4` unchanged.

## What To Extract

### Deal Search

Extract/adapt:

- BestBuy search and scrape.
- Amazon search and scrape.
- source selection.
- result normalization.

Target:

- `backend/tools/deal_search/`

### Price Estimation

Extract/adapt:

- Preprocessor behavior if needed.
- Frontier GPT+RAG call.
- Specialist model call.
- DNN inference wrapper.
- weighted ensemble.

Target:

- `backend/tools/price_estimator/`

## What Not To Extract Initially

- Gradio UI.
- `price_is_right.py` autonomous RSS workflow.
- legacy DealNews scanner.
- Pushover notification.
- t-SNE visualization.

## Compatibility Notes

V2 tool outputs must use new schemas, even if source code comes from old classes.

Use USD fields:

- `sale_price_usd`
- `estimated_value_usd`
- `discount_usd`

## Risks

| Risk | Mitigation |
|---|---|
| Direct import creates hidden coupling | copy/adapt after code review |
| Live scraping flaky | mock mode first |
| Ensemble has heavy dependencies | isolate in price tool |
| Old logs not structured | wrap with V2 logging |

## Acceptance Criteria

- `segment4` remains unchanged.
- V2 has clean tool interfaces.
- Tests can run without live network/model calls.
- Real behavior can be enabled manually.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
