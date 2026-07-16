# Frontend

Next.js frontend ưu tiên chat cho Shopping Assistant V3. Được tạo trong Phase
1 dưới dạng cấu trúc thư mục; chưa scaffold app.

## Quyết Định Stack

- Framework: Next.js with App Router.
- Local URL: `http://localhost:3000`.
- Giao tiếp với backend tại `http://localhost:8000` thông qua async job polling
  (`POST /api/chat-jobs`, sau đó poll `GET /api/chat-jobs/{job_id}`).
- Package manager: chưa cố định; quyết định với user approval trong Phase 6.

## Cấu Trúc Dự Kiến

```text
frontend/
├── app/
├── components/   (ChatPanel, JobStatus, ProductCard, ProductResults, DebugLogPanel)
├── lib/          (apiClient, types)
└── styles/
```

Các UI states bắt buộc: `idle`, `submitting`, `pending`, `running`, `completed`,
`failed`.

Được implement trong Phase 6. Chi tiết contract:
`shopping_assistant_v3/guides/architecture.md`.
