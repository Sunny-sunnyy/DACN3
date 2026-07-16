# Backend

FastAPI backend cho Shopping Assistant V3. Được tạo trong Phase 1 dưới dạng
cấu trúc thư mục; chưa có runtime code nào được implement.

## Quyết Định Stack

- Chỉ dùng Python thông qua `uv`. Không gọi trực tiếp `python` hoặc `pip`.
- Web framework: FastAPI.
- Persistence: SQLite (schema giữ tương thích với Postgres).
- Async jobs: local worker, lifecycle theo `job_id`.
- Model calls: LiteLLM abstraction, provider tương thích OpenAI.
- Default mode: mock/fixture. Real search và real model calls là opt-in.

Layout dependency Python (`pyproject.toml`) được hoãn đến Phase 2.

## Bản Đồ Module

| Module | Trách nhiệm |
|---|---|
| `shared/` | Config, logging, schemas chung, guardrails, error types. |
| `database/` | SQLite schema, repositories, persistence cho job/product/estimate. |
| `api/` | FastAPI app, validation, safe errors, job endpoints. |
| `router/` | Job orchestration, intent routing, tool invocation. |
| `tools/deal_search/` | Amazon/BestBuy search, normalized candidates. |
| `tools/price_estimator/` | Ước tính fair value USD, deal score. |
| `synthesizer/` | Câu trả lời tiếng Việt cuối cùng từ structured evidence. |

Quy tắc:

- `shared/` không được import từ tools hoặc agents.
- Route handlers phải mỏng và không bao giờ chạy trực tiếp scraping/model work.
- Database access đi qua repositories.

## Environment Variables

Xem `shopping_assistant_v3/.env.example` để biết danh sách đầy đủ. Các safety
flags quan trọng:

```text
ENABLE_REAL_SEARCH=false
ENABLE_REAL_MODEL_CALLS=false
```

Default tests không bao giờ được scrape live Amazon/BestBuy hoặc gọi paid model
APIs.

## Local Service

- Backend URL: `http://localhost:8000`
- Contracts: xem `shopping_assistant_v3/guides/architecture.md` (API, database)
  và `shopping_assistant_v3/guides/agent_architecture.md` (Router, tools,
  Synthesizer).
