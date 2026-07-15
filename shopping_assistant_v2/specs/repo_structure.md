# Spec: Repository Structure

## Purpose

Define the target folder structure for `shopping_assistant_v2/`.

## Current Phase Structure

```text
shopping_assistant_v2/
├── README.md
├── PROJECT_DEVELOPMENT_PLAN_V2.md
├── plans/
├── specs/
├── guides/
├── docs/
└── scripts/
```

## Future Runtime Structure

```text
shopping_assistant_v2/
├── backend/
│   ├── README.md
│   ├── shared/
│   ├── database/
│   ├── api/
│   ├── router/
│   ├── tools/
│   │   ├── deal_search/
│   │   └── price_estimator/
│   ├── synthesizer/
│   ├── comparer/
│   └── advisor/
├── frontend/
├── scripts/
├── plans/
├── specs/
├── guides/
└── docs/
```

## Backend Folder Requirements

Each backend module should eventually include:

- `README.md`
- `schemas.py` when it owns structured input/output
- `test_simple.py` for local tests
- `test_full.py` only when integration or real external calls exist

Agent/model modules may include:

- `agent.py`
- `templates.py`
- `client.py`

Tool modules may include:

- `tool.py`
- `schemas.py`
- `fixtures/`
- `tests/`

## Ownership

| Folder | Owner Responsibility |
|---|---|
| `backend/shared` | utilities only |
| `backend/database` | schema and persistence |
| `backend/api` | FastAPI routes and validation |
| `backend/router` | job orchestration and intent routing |
| `backend/tools/deal_search` | Amazon/BestBuy candidate search |
| `backend/tools/price_estimator` | USD fair value estimation |
| `backend/synthesizer` | Vietnamese final answer |
| `backend/comparer` | later product comparison |
| `backend/advisor` | later buying advice |
| `frontend` | Next.js UI |
| `guides` | implementation runbooks |
| `specs` | technical contracts |
| `plans` | phase strategy |
| `docs` | architecture and decisions |

## Rules

- Do not put runtime code directly under `shopping_assistant_v2/` root.
- Do not import from `segment4` directly unless the migration spec is updated and approved.
- Do not put secrets or `.env` values in docs.
- Do not let `shared` depend on specific tools/agents.

## Acceptance Criteria

- A coding agent can create folders without guessing responsibilities.
- Every runtime folder has a clear owner.
- Future implementation can happen incrementally.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
