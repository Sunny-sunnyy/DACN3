# Guide 1: Local Setup

## Goal

Prepare the local environment for V2 implementation.

## What You Will Build

No runtime feature yet. This guide prepares local tooling and verifies assumptions.

## Prerequisites

- Read `PROJECT_DEVELOPMENT_PLAN_V2.md`.
- Read `plans/00_context.md`.
- Read `specs/repo_structure.md`.
- Check `git status --short`.

## Files Involved

- `shopping_assistant_v2/`
- future `backend/`
- future `frontend/`

## Steps

1. Confirm `segment4/` is reference-only.
2. Confirm no secrets are printed.
3. Confirm Python commands will use `uv`.
4. Confirm frontend will use Next.js.
5. Confirm local MVP uses SQLite default.
6. Create runtime folders only after implementation plan approval.

## Verify

- You can explain the V2 app in one paragraph.
- You know where backend and frontend will live.
- You know which files are specs versus guides.

## Troubleshooting

If the scope feels too large, return to `plans/01_mvp_scope.md` and remove anything not required for search + price + Vietnamese summary.

## Next Guide

Continue to `guides/2_backend_api.md`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
