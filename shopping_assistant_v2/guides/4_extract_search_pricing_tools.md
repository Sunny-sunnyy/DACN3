# Guide 4: Extract Search And Pricing Tools

## Goal

Adapt the working `segment4` search/pricing behavior into V2 tool modules.

## What You Will Build

- `deal_search_tool`
- `price_estimator_tool`
- fixtures and mock mode
- optional real mode

## Prerequisites

- `specs/tool_contracts.md`
- `specs/migration_from_segment4.md`
- CodeGraph status for `segment4`

## Files Involved

Reference files:

```text
segment4/price_agents/bestbuy_deals.py
segment4/price_agents/amazon_deals.py
segment4/price_agents/ensemble_agent.py
segment4/price_agents/frontier_agent.py
segment4/price_agents/specialist_agent.py
segment4/price_agents/neural_network_agent.py
segment4/bestbuy_untils/unified_deal.py
```

Future V2 files:

```text
backend/tools/deal_search/
backend/tools/price_estimator/
```

## Steps

1. Use CodeGraph to inspect relevant `segment4` call paths.
2. Write V2 schemas first.
3. Add mock fixtures.
4. Implement mock tool mode.
5. Add tests for schemas and fixtures.
6. Adapt BestBuy/Amazon logic into deal search tool.
7. Adapt ensemble logic into price estimator tool.
8. Add opt-in real tests.

## Verify

- Mock tool tests pass without network/model calls.
- Real mode can be manually enabled.
- V2 output uses new schemas.
- `segment4` files are unchanged.

## Troubleshooting

- If dependencies become heavy, isolate them inside the specific tool.
- If live scraping fails, preserve mock tests and return source warning.
- If model calls fail, preserve product search results with pricing warning.

## Next Guide

Continue to `guides/5_router_and_synthesizer.md`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
