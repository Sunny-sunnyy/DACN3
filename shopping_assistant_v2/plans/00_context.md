# Plan 00: Context

## Purpose

Capture the current project state and the reason for Project Development Plan V2.

## Current Repo State

The repository has two major directions:

- `segment4/`: working English/US-market prototype.
- Vietnamese data/model experiments: research notebooks and reports for Vietnamese price prediction.

The working runtime is `segment4/search_key.py`, documented in `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`.

The old plan, `segment4/mo_ta_du_an/Project_Development_Plan.md`, focused on Vietnamese data, Vietnamese marketplace scraping, and Vietnamese price models. V2 replaces that active direction.

## Important Experimental Finding

Vietnamese text-based price prediction did not become strong enough to anchor the app. The research is still valuable for DATN documentation, but it should not block the working assistant.

The better practical path is to reuse the English pipeline:

- Amazon/BestBuy search.
- English product text.
- USD prices.
- Existing ensemble pricing.
- Vietnamese assistant layer on top.

## V2 Positioning

```text
Vietnamese-speaking US Deal Assistant
```

Users chat in Vietnamese. The assistant searches and evaluates US products, then explains the results in Vietnamese.

## Reference Documents

Read these before implementation:

- `shopping_assistant_v2/PROJECT_DEVELOPMENT_PLAN_V2.md`
- `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`
- `VIETNAMESE_PRICING_DEVELOPMENT_REPORT.md`
- `segment4/mo_ta_du_an/ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md`

## Rules For Coding Agents

- Do not modify `segment4/` unless an approved implementation plan says so.
- Do not claim V2 runtime exists until implemented.
- Use `uv` for Python commands.
- Default to mocks/fixtures for tests that would otherwise call paid APIs or live websites.
- Preserve existing worktree changes.

## Acceptance Criteria

- Agent understands why V2 pivots away from Vietnamese pricing-first.
- Agent can explain the MVP in one paragraph.
- Agent knows `segment4` is reference-only.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
