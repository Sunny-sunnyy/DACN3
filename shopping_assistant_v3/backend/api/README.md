# api

FastAPI app with validation, safe error responses, and async job endpoints:

- `GET /health`
- `POST /api/chat-jobs`
- `GET /api/chat-jobs/{job_id}`

Route handlers stay thin and never run scraping/model work directly. Contract
details: `shopping_assistant_v3/guides/architecture.md`.

Implemented in Phase 2. No code yet.
