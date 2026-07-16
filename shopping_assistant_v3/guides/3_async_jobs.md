# Phase 3: Async Jobs

## Mục Đích

Implement local async job lifecycle và deterministic mock completion path.

Phase này chứng minh jobs chuyển từ `pending` sang `running` sang `completed`
hoặc `failed`, và frontend sau này có thể poll status mà API không block vì
long work.

## Trạng Thái Hiện Tại

Phase 3 bắt đầu sau khi Phase 2 backend API và SQLite repositories hoạt động.

API có thể tạo và đọc `pending` jobs, nhưng chưa có worker xử lý chúng.

## Scope

Implement:

- local worker entry point hoặc background worker path;
- status transitions;
- idempotency cho jobs đã completed;
- deterministic mock result payload;
- failed job path với sanitized error;
- structured logs theo `job_id`;
- `agent_runs` audit rows cho worker execution.

## Non-Goals

- Không real Router model calls.
- Không real search/pricing tools.
- Không frontend implementation.
- Không queue/SQS.
- Không production observability.
- Không live scraping hoặc paid API calls.

## Inputs From Previous Phases

Required:

- Phase 2 API endpoints.
- Phase 2 SQLite schema/repository.
- `guides/architecture.md`.

## Contracts

Job lifecycle:

```text
pending -> running -> completed
pending -> running -> failed
```

Worker flow:

```text
worker receives job_id
-> load job
-> if completed, return existing result
-> if not pending, skip or report safe state
-> set running
-> write deterministic mock result
-> set completed
```

Error flow:

```text
catch exception
-> log JOB_FAILED
-> save sanitized error_message
-> set failed
```

Mock completed result shape:

```json
{
  "answer_vi": "Mình đã tìm thấy một số lựa chọn mẫu để kiểm tra luồng demo.",
  "products": [
    {
      "source": "BestBuy",
      "title": "Mock Gaming Laptop",
      "brand": "MockBrand",
      "sale_price_usd": 699.99,
      "estimated_value_usd": 899.99,
      "discount_usd": 200.0,
      "deal_score": "hot",
      "url": "https://www.bestbuy.com/"
    }
  ],
  "warnings": []
}
```

Required log events:

- `JOB_STARTED`
- `JOB_COMPLETED`
- `JOB_FAILED`

## Workflow Gate

Trước khi code:

- Load `using-superpowers`.
- Dùng `brainstorming` với user.
- Chỉ hỏi các câu thay đổi scope, design, tests, hoặc implementation plan.
- Trình bày Phase 3 plan.
- Chờ explicit approval.

## Implementation Order

1. Xác nhận Phase 2 report và tests pass.
2. Chọn worker mode cho MVP:
   - FastAPI background task cho simplest local slice; hoặc
   - daemon thread sau explicit job commit để tương thích local MVP; hoặc
   - separate local worker process để future queue mapping sạch hơn.
3. Thêm worker function cho một `job_id`.
4. Thêm repository update helpers cho status/result/error.
5. Thêm deterministic mock result.
6. Thêm full-worker exception handling.
7. Thêm structured logs và `agent_runs` rows.
8. Thêm tests cho completed và failed paths.
9. Viết Phase 3 report.

## Verification

Required checks:

- Tạo job qua API.
- Xử lý job qua local worker.
- Poll job và thấy result `completed`.
- Trigger controlled failure và thấy status `failed`.
- Xác nhận logs có `job_id`.
- Xác nhận rerun completed job không duplicate/conflict.

Example commands phụ thuộc implementation:

```bash
uv run pytest <job tests>
curl -s http://localhost:8000/api/chat-jobs/<job_id>
```

Không test nào trong phase này được yêu cầu network/model/scraping.

## Report Requirements

Viết:

```text
shopping_assistant_v3/reports/phase_3_async_jobs_report.md
```

Bao gồm:

- chosen worker mode và lý do;
- job transition evidence;
- failure-path evidence;
- exact commands đã chạy;
- test results;
- idempotency behavior;
- remaining risks.

## Risks And Open Questions

- Background tasks và daemon threads đơn giản hơn nhưng ít production-like hơn
  separate worker. Một trong hai local approach đều chấp nhận được nếu được
  documented và nếu API-created jobs được commit trước khi worker có thể đọc.
- Daemon-thread workers chỉ dành cho local-MVP: chúng không survive process
  restart và phải được thay bằng bounded queue/worker trước production.
- Nếu jobs có thể bị stuck ở `running`, implementation không acceptable.
- Mock result nên rõ ràng là mocked để tránh claim real search.
