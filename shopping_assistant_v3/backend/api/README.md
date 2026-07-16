# api

FastAPI app với validation, safe error responses, và async job endpoints:

- `GET /health`
- `POST /api/chat-jobs`
- `GET /api/chat-jobs/{job_id}`

Route handlers phải mỏng và không bao giờ chạy trực tiếp scraping/model work.
Chi tiết contract: `shopping_assistant_v3/guides/architecture.md`.

Được implement trong Phase 2. Chưa có code.
