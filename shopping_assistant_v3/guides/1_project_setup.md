# Phase 1: Project Setup

## Purpose

Prepare the V3 runtime structure and local development assumptions without
building user-facing functionality yet.

This phase exists to make later coding agents start from a clean structure
instead of recreating V2's scattered documentation and unclear boundaries.

## Current Status

Phase 1 has been implemented and approved. V3 now contains the documentation
source of truth plus runtime skeleton folders:

```text
shopping_assistant_v3/
├── README.md
├── .env.example
├── backend/
│   ├── README.md
│   ├── shared/
│   ├── database/
│   ├── api/
│   ├── router/
│   ├── tools/
│   └── synthesizer/
├── frontend/
│   └── README.md
├── gameplan.md
├── guides/
├── reports/
└── scripts/
    ├── README.md
    └── verify_setup.sh
```

No runtime backend API, database schema, worker, tool, or frontend UI code is
implemented yet. Phase 2 is the next implementation phase.

## Scope

Phase 1 may create:

- runtime folder skeletons for `backend/`, `frontend/`, and `scripts/`;
- minimal README files for runtime folders;
- local environment documentation;
- project-level ignore/config files only if needed and approved;
- a setup verification command that does not call network/model/scraping APIs.

Phase 1 must confirm:

- Python commands use `uv`;
- backend will be FastAPI;
- frontend will be Next.js;
- local persistence will be SQLite;
- default mode will be mock/fixture;
- `segment4/` is reference-only;
- `shopping_assistant_v2/` is reference-only.

## Non-Goals

- No backend API endpoints.
- No database schema implementation.
- No worker.
- No tool implementation.
- No frontend UI.
- No dependency installation unless explicitly approved.
- No live scraping or paid model calls.
- No modification to `segment4/` or `shopping_assistant_v2/`.

## Inputs From Previous Phases

Required reading:

- `shopping_assistant_v3/gameplan.md`
- `shopping_assistant_v3/guides/architecture.md`
- `shopping_assistant_v3/guides/agent_architecture.md`

No previous implementation phase is required.

## Contracts

Target runtime structure:

```text
shopping_assistant_v3/
├── backend/
│   ├── README.md
│   ├── shared/
│   ├── database/
│   ├── api/
│   ├── router/
│   ├── tools/
│   │   ├── deal_search/
│   │   └── price_estimator/
│   └── synthesizer/
├── frontend/
│   └── README.md
├── scripts/
├── guides/
└── reports/
```

If the implementation agent wants a different runtime layout, it must
brainstorm with the user and update this guide after approval.

## Workflow Gate

Before coding:

- Load `using-superpowers`.
- Use `brainstorming` with the user.
- Ask only questions that change scope, design, tests, or implementation plan.
- Present the Phase 1 plan.
- Wait for explicit approval.

## Implementation Order

1. Confirm `git status --short` and preserve existing changes.
2. Read required V3 docs.
3. Brainstorm Phase 1 scope with the user.
4. Create only approved runtime folders and minimal documentation.
5. Document local commands and assumptions.
6. Avoid runtime feature implementation.
7. Write a Phase 1 implementation report.

## Verification

Minimum verification:

```bash
find shopping_assistant_v3 -maxdepth 3 -type f -print | sort
git status --short
```

If runtime folders are created, verify that:

- no file under `segment4/` changed;
- no file under `shopping_assistant_v2/` changed;
- no secrets were read or printed;
- no network/model/scraping commands were run.

## Report Requirements

Write:

```text
shopping_assistant_v3/reports/phase_1_project_setup_report.md
```

The report must list:

- folders/files created;
- any docs updated;
- commands run;
- whether dependencies were installed;
- whether V2 or `segment4` remained unchanged;
- remaining setup risks.

## Risks And Open Questions

- Frontend package manager is not fixed by this guide. Next.js creation may use
  npm, pnpm, or another tool only after user approval.
- Python dependency layout is not fixed yet. Later backend phases should choose
  the minimal project structure that works with `uv`.
- Creating too much scaffolding in Phase 1 can overfit the architecture before
  API/database contracts are implemented.
