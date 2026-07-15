# Frontend

Next.js chat-first frontend for Shopping Assistant V3. Created in Phase 1 as
structure only; no app is scaffolded yet.

## Stack Decisions

- Framework: Next.js with App Router.
- Local URL: `http://localhost:3000`.
- Talks to backend at `http://localhost:8000` via async job polling
  (`POST /api/chat-jobs`, then poll `GET /api/chat-jobs/{job_id}`).
- Package manager: not fixed yet; decided with user approval in Phase 6.

## Planned Structure

```text
frontend/
├── app/
├── components/   (ChatPanel, JobStatus, ProductCard, ProductResults, DebugLogPanel)
├── lib/          (apiClient, types)
└── styles/
```

Required UI states: `idle`, `submitting`, `pending`, `running`, `completed`,
`failed`.

Implemented in Phase 6. Contract details:
`shopping_assistant_v3/guides/architecture.md`.
