# Phase 2: Backend API And Database

## Mục Đích

Implement local FastAPI backend skeleton và SQLite persistence backbone.

Phase này chứng minh backend có thể nhận Vietnamese chat request, tạo durable
job, và trả về job status qua polling mà không chạy long scraping/model work
trong request handler.

## Trạng Thái Hiện Tại

Phase 2 bắt đầu sau khi Phase 1 đã tạo hoặc xác nhận V3 runtime structure.

Runtime folders kỳ vọng:

```text
backend/shared/
backend/database/
backend/api/
```

## Scope

Implement:

- FastAPI app.
- `GET /health`.
- `POST /api/chat-jobs`.
- `GET /api/chat-jobs/{job_id}`.
- safe validation/error response shape.
- SQLite schema initialization.
- repository functions cho jobs và minimal conversation/message records.
- config loading không in secrets.

## Non-Goals

- Chưa có worker execution.
- Không Router/Synthesizer logic.
- Không search/pricing tools.
- Không frontend.
- Không live scraping/model/API calls.
- Không production auth.
- Không AWS/Terraform.

## Inputs From Previous Phases

Required:

- Phase 1 runtime folder structure.
- `gameplan.md`.
- `guides/architecture.md`.

Recommended:

- Chỉ review `guides/agent_architecture.md` cho future result payload shape.

## Contracts

### Health Endpoint

`GET /health`

```json
{
  "status": "ok",
  "service": "shopping-assistant-v3"
}
```

### Create Chat Job

`POST /api/chat-jobs`

Request:

```json
{
  "message": "Tìm laptop gaming dưới 800 đô",
  "conversation_id": null,
  "source": "All",
  "max_results_per_source": 5
}
```

Validation:

- `message`: string, 2 to 1000 chars.
- `conversation_id`: nullable string.
- `source`: `All`, `Amazon`, hoặc `BestBuy`.
- `max_results_per_source`: integer, 1 to 20.

Response:

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Job created. Poll status endpoint for results."
}
```

### Get Chat Job

`GET /api/chat-jobs/{job_id}`

Required fields:

- `job_id`
- `status`
- `created_at`
- `started_at`
- `completed_at`
- `result`
- `error_message`

### Safe Error Shape

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request.",
    "details": []
  }
}
```

### SQLite Tables

Minimum tables cho phase này:

- `jobs`
- `conversations`
- `messages`
- `agent_runs`
- `products`
- `price_estimates`

The implementation may create all tables in Phase 2 even if later phases fill
them.

Required `jobs` fields:

- `id`
- `user_id`
- `job_type`
- `status`
- `request_payload`
- `result_payload`
- `error_message`
- `created_at`
- `started_at`
- `completed_at`
- `updated_at`

MVP statuses:

```text
pending
running
completed
failed
```

## Workflow Gate

Trước khi code:

- Load `using-superpowers`.
- Dùng `brainstorming` với user.
- Chỉ hỏi các câu thay đổi scope, design, tests, hoặc implementation plan.
- Trình bày Phase 2 plan.
- Chờ explicit approval.

## Implementation Order

1. Xác nhận Phase 1 report hoặc current runtime structure.
2. Định nghĩa backend config mà không logging secrets.
3. Định nghĩa database schema initialization.
4. Implement repository functions để tạo và đọc jobs.
5. Implement FastAPI app.
6. Implement Pydantic request/response schemas.
7. Implement `GET /health`.
8. Implement `POST /api/chat-jobs`.
9. Implement `GET /api/chat-jobs/{job_id}`.
10. Thêm focused tests cho validation, repository operations, và endpoint smoke.
11. Viết Phase 2 report.

## Verification

Minimum commands, điều chỉnh theo actual backend layout:

```bash
uv run pytest <backend tests>
uv run <backend start command>
curl -s http://localhost:8000/health
```

Manual API checks:

- Valid `POST /api/chat-jobs` trả về `pending`.
- Invalid short message trả về safe validation error.
- `GET /api/chat-jobs/{job_id}` trả về created job.
- Unknown job trả về safe 404-style error.

Verification không được yêu cầu network/model/scraping calls.

## Report Requirements

Viết:

```text
shopping_assistant_v3/reports/phase_2_backend_api_and_database_report.md
```

Bao gồm:

- API endpoints đã implement;
- schema/tables đã tạo;
- exact commands đã chạy;
- test results;
- deviations từ guide này;
- known database/API risks;
- docs có thể cần update.

## Risks And Open Questions

- SQLite migration tooling chưa được chọn. Simple schema initializer chấp nhận
  được cho MVP nếu được documented.
- Route handlers phải giữ mỏng. Nếu API code bắt đầu trực tiếp xử lý jobs, dừng
  lại và chuyển work đó sang Phase 3.
- Exact backend package layout nên giữ đơn giản; tránh abstractions không cần
  cho Phase 2.
