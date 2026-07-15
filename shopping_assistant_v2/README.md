# Shopping Assistant V2

Vietnamese-speaking US Deal Assistant.

This folder is the documentation-first starting point for Project Development Plan V2. It replaces the direction of the old Vietnamese pricing-first plan without modifying `segment4/`.

## Positioning

The assistant talks to users in Vietnamese, but searches and prices products from US sources:

- Amazon
- BestBuy

The core search and pricing behavior will be extracted from the working prototype documented in:

- `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`

`segment4/` remains a read-only prototype/reference for V2 planning. Do not refactor it directly unless a later approved implementation plan says so.

## Current Phase

This folder currently contains plans, specs, guides, and design notes only. It does not claim that the V2 runtime app is implemented.

The intended implementation path is:

1. Read the project plan.
2. Read the plans for strategy and phase order.
3. Read the specs for exact contracts.
4. Follow the guides when implementing each phase.
5. Update docs if research or implementation reveals a better approach.

## Recommended Reading Order

1. `PROJECT_DEVELOPMENT_PLAN_V2.md`
2. `plans/00_context.md`
3. `plans/01_mvp_scope.md`
4. `specs/repo_structure.md`
5. `specs/job_orchestration.md`
6. `specs/tool_contracts.md`
7. `guides/1_local_setup.md`

## Target App Shape

```text
shopping_assistant_v2/
├── backend/      # Future FastAPI backend, local-first
├── frontend/     # Future Next.js chat-first frontend
├── plans/        # Strategic implementation plans
├── specs/        # Technical contracts for coding agents
├── guides/       # Step-by-step implementation runbooks
├── docs/         # Architecture notes, decisions, UI/UX research
└── scripts/      # Future local helper scripts
```

## Core MVP

```text
Vietnamese user message
-> async chat job
-> controlled router
-> Amazon/BestBuy deal search tool
-> English ensemble price estimator tool
-> Vietnamese synthesizer
-> Next.js chat response and product cards
```

## Non-Goals For The First MVP

- No Vietnamese e-commerce scraping.
- No Vietnamese pricing model training.
- No AWS deployment.
- No Clerk auth in the first local MVP.
- No direct modification of `segment4/`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
