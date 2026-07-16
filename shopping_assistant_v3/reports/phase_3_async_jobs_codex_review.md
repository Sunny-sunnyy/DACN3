# Codex Review: Phase 3 Async Jobs

Decision: approved
Reviewer: Codex
Date: 2026-07-15
Implementer report: `shopping_assistant_v3/reports/phase_3_async_jobs_report.md`

## Tóm Tắt

Phase 3 đã được approve. Worker lifecycle, API-triggered async path,
stale-running recovery, sanitized failure handling, structured logs, và audit
rows đã được verify. Implementation dùng documented daemon-thread MVP worker
thay vì FastAPI `BackgroundTasks`.

## Findings

Không có blocker hoặc major findings.

Minor residual risk: daemon-thread worker chỉ dành cho local-MVP. Nó không có
bounded queue/backpressure và không survive process restart. Report đã document
limitation này; production worker design vẫn là concern của phase sau.

## Verification

Commands đã chạy:

```bash
git status --short
```

Result: Phase 3 modified/new files cộng với hai pre-existing untracked files
`brainstorming.md` và `prompt_session.md`.

```bash
cd shopping_assistant_v3 && uv run pytest tests/ -v
```

Result: `34 passed, 1 warning in 3.96s`.

```bash
cd shopping_assistant_v3 && uv run python -c "exec(\"import time\\nfrom fastapi.testclient import TestClient\\nfrom backend.api.main import app\\nstatuses = {}\\nwith TestClient(app) as c:\\n    for i in range(20):\\n        r = c.post('/api/chat-jobs', json={'message': f'probe {i}'})\\n        job_id = r.json()['job_id']\\n        last = None\\n        for _ in range(20):\\n            time.sleep(0.1)\\n            body = c.get(f'/api/chat-jobs/{job_id}').json()\\n            last = body['status']\\n            if last in ('completed', 'failed'):\\n                break\\n        statuses[last] = statuses.get(last, 0) + 1\\nprint(statuses)\")"
```

Result: `{'pending': 20}`.

Review artifacts được tạo bởi probe/test run (`backend/database/app.db`,
`__pycache__`, `.pytest_cache`) đã được remove sau verification.

Re-review sau implementer sanitization update:

```bash
cd shopping_assistant_v3 && uv run pytest tests/ -v
```

Result: `34 passed, 1 warning in 4.01s`.

```bash
cd shopping_assistant_v3 && uv run python -c "exec(\"import time\\nfrom fastapi.testclient import TestClient\\nfrom backend.api.main import app\\nstatuses = {}\\nwith TestClient(app) as c:\\n    for i in range(5):\\n        r = c.post('/api/chat-jobs', json={'message': f'probe {i}'})\\n        job_id = r.json()['job_id']\\n        last = None\\n        for _ in range(20):\\n            time.sleep(0.1)\\n            body = c.get(f'/api/chat-jobs/{job_id}').json()\\n            last = body['status']\\n            if last in ('completed', 'failed'):\\n                break\\n        statuses[last] = statuses.get(last, 0) + 1\\nprint(statuses)\")"
```

Result tại thời điểm review đó: `{'pending': 5}`. API-triggered async blocker
vẫn chưa được resolve trước final fix.

Final re-review sau các fix commit-before-thread và stale-running recovery:

```bash
cd shopping_assistant_v3 && uv run pytest tests/ -v
```

Result: `36 passed, 1 warning in 4.24s`.

```bash
cd shopping_assistant_v3 && uv run python -c "exec(\"import time\\nfrom fastapi.testclient import TestClient\\nfrom backend.api.main import app\\nstatuses = {}\\nwith TestClient(app) as c:\\n    for i in range(5):\\n        r = c.post('/api/chat-jobs', json={'message': f'probe {i}'})\\n        job_id = r.json()['job_id']\\n        last = None\\n        for _ in range(20):\\n            time.sleep(0.1)\\n            body = c.get(f'/api/chat-jobs/{job_id}').json()\\n            last = body['status']\\n            if last in ('completed', 'failed'):\\n                break\\n        statuses[last] = statuses.get(last, 0) + 1\\nprint(statuses)\")"
```

Result: `{'completed': 5}`.

## Scope Check

Scope nằm trong Phase 3 runtime files và report. Tôi không thấy thay đổi
`segment4/` hoặc `shopping_assistant_v2/` nào trong phase này.

## Thay Đổi Bắt Buộc

Không có.

## Resolved Findings

- resolved: `shopping_assistant_v3/backend/worker.py:153` - finding về raw exception text đã được sửa. Worker hiện persist sanitized message `Worker failed. Try again later.` và tests assert sanitized user/API-visible failure text. Giữ raw exception details khỏi API/database surfaces trong các tool/model phases tương lai.
- resolved: `shopping_assistant_v3/backend/api/main.py:131` - API-trigger race đã được sửa bằng cách commit request session trước khi start daemon thread. API-level test và Codex probe đều verify jobs đạt `completed`.
- resolved: `shopping_assistant_v3/backend/worker.py:117` - stale `running` jobs hiện recover khi `started_at` cũ hơn 5 phút hoặc missing; fresh `running` jobs vẫn được skip để tránh duplicate processing.

## Approval Notes

Approved cho Phase 4A planning. Implementation milestone được phép tiếp theo là
`Phase 4A: Mock Search/Pricing Tools`.
