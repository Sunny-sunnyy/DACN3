# Plan 04: Frontend Architecture

## Purpose

Define the Next.js frontend direction.

## UX Direction

The frontend is chat-first. It should feel like a Vietnamese assistant, not just a search form.

MVP user experience:

```text
User enters Vietnamese request
-> assistant shows job status
-> assistant returns Vietnamese answer
-> product cards appear below answer
```

## Target Structure

```text
frontend/
├── README.md
├── app/ or pages/
├── components/
│   ├── ChatPanel
│   ├── JobStatus
│   ├── ProductCard
│   ├── ProductResults
│   └── DebugLogPanel
├── lib/
│   ├── apiClient
│   └── types
└── styles/
```

The implementation agent must choose App Router or Pages Router explicitly before coding. Recommended for a new app: App Router, unless the team prefers Pages Router simplicity.

## Frontend States

Required states:

- idle.
- submitting.
- pending.
- running.
- completed.
- failed.

## Product Card Fields

Each product card should show:

- source.
- title.
- brand if available.
- sale price USD.
- estimated value USD.
- discount USD.
- deal score.
- URL.
- warning if data is partial.

## Debug UX

For DATN/demo, a debug panel is useful:

- job id.
- status transitions.
- latest log events.
- warnings.

Debug UI can be collapsible.

## UI/UX Research Later

Do not over-design UI in the first implementation. After backend contracts are stable, research:

- product card layout.
- chat result hierarchy.
- mobile responsiveness.
- color/typography.
- demo storytelling.

## Acceptance Criteria

- User can submit a Vietnamese request.
- UI does not freeze during backend work.
- Job status updates while polling.
- Completed result renders answer and cards.
- Failed result renders useful error.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
