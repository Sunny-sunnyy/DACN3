# Phase 2 Backend API And Database — Implementation Report

## Phase

`Phase 2: Backend API And Database`

Implementer: Claude Code (DeepSeek Implementer)

Date: 2026-07-15

Branch: TTTN

Commit reviewed: `not committed yet`

## Tóm Tắt

Đã implement toàn bộ Phase 2 scope theo
`guides/2_backend_api_and_database.md` với các điều chỉnh được user approve:

- FastAPI app với 3 endpoints: `GET /health`, `POST /api/chat-jobs`, `GET /api/chat-jobs/{job_id}`.
- SQLite persistence qua SQLAlchemy ORM với `Base.metadata.create_all()` — 6 tables: jobs, conversations, messages, agent_runs, products, price_estimates.
- Real repository layer (không stubs): `create_job`, `get_job_by_id`, `create_conversation`, `create_message`.
- `POST /api/chat-jobs` tạo conversation mới khi `conversation_id` là null, lưu user message, và tạo pending job linked tới `demo_user`.
- Custom error handlers trả về safe error shape compliant với guide `{error: {code, message, details}}` cho validation (422), not-found (404), và app errors (500).
- Toàn bộ 20 tests pass bằng pytest + FastAPI TestClient + temp SQLite. Không network, không model calls, không scraping.
- Không CORS (deferred tới Phase 6).
- V3 có `.venv` và `pyproject.toml` isolated riêng — root project (tech2ai) không bị touched.

## Files Đã Tạo

```text
shopping_assistant_v3/pyproject.toml - uv project config, deps: fastapi, uvicorn[standard], sqlalchemy, httpx, pytest
shopping_assistant_v3/uv.lock - generated lockfile (chỉ V3, không phải root)
shopping_assistant_v3/backend/__init__.py - package marker
shopping_assistant_v3/backend/shared/__init__.py - package marker
shopping_assistant_v3/backend/shared/config.py - env loading, safety flags, DATABASE_URL, không secret logging
shopping_assistant_v3/backend/shared/errors.py - AppError, ValidationError, NotFoundError, error_response()
shopping_assistant_v3/backend/database/__init__.py - package marker
shopping_assistant_v3/backend/database/session.py - engine singleton, session factory, get_db FastAPI dependency, init_db()
shopping_assistant_v3/backend/database/schema.py - 6 SQLAlchemy models (jobs, conversations, messages, agent_runs, products, price_estimates)
shopping_assistant_v3/backend/database/repository.py - create_job, get_job_by_id, create_conversation, create_message (real persistence)
shopping_assistant_v3/backend/api/__init__.py - package marker
shopping_assistant_v3/backend/api/schemas.py - Pydantic models: ChatJobRequest, ChatJobResponse, JobStatusResponse, ProductResult, ErrorDetail
shopping_assistant_v3/backend/api/main.py - FastAPI app, 3 endpoints, lifespan (init_db), custom error handlers, không CORS
shopping_assistant_v3/tests/__init__.py - package marker
shopping_assistant_v3/tests/conftest.py - temp SQLite isolation, TestClient fixture, dependency override
shopping_assistant_v3/tests/test_api.py - 20 tests: health, create job (6), validation (7), get job status (3), repository (3), cộng với unknown conversation_id guard
```

## Files Đã Sửa

```text
shopping_assistant_v3/backend/api/main.py - thêm conversation lookup với non-null conversation_id; raise NotFoundError nếu missing (Codex review fix)
shopping_assistant_v3/tests/test_api.py - thêm test_unknown_conversation_id_returns_404_and_no_orphans (Codex review fix)
```

Chỉ có post-review modifications; tất cả initial files được tạo trong first
pass. segment4/ và shopping_assistant_v2/ không bị touched.

## Commands Đã Chạy

```bash
# Dependency install (user-approved)
cd shopping_assistant_v3 && uv sync
uv sync --extra dev
# pass - 29 packages installed into isolated .venv (Python 3.13.12)

# Automated tests (initial)
uv run pytest tests/ -v
# pass - 19 passed, 1 warning (starlette/httpx deprecation, 3rd-party)

# Automated tests (after Codex review fix — unknown conversation_id guard)
uv run pytest tests/ -v
# pass - 20 passed, 1 warning (starlette/httpx deprecation, 3rd-party)

# Manual API verification
uv run uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 &
curl -s http://127.0.0.1:8000/health
# pass - {"status": "ok", "service": "shopping-assistant-v3"}

curl -s -X POST http://127.0.0.1:8000/api/chat-jobs \
  -H "Content-Type: application/json" \
  -d '{"message": "Tim laptop gaming duoi 800 do"}'
# pass - 201, {"job_id": "...", "status": "pending", ...}

curl -s -X POST http://127.0.0.1:8000/api/chat-jobs \
  -H "Content-Type: application/json" \
  -d '{"message": "a"}'
# pass - 422, error shape: {error: {code: "VALIDATION_ERROR", message: "Invalid request.", details: [...]}}

curl -s http://127.0.0.1:8000/api/chat-jobs/<job_id>
# pass - 200, full status with created_at, started_at, completed_at, result, error_message

curl -s http://127.0.0.1:8000/api/chat-jobs/nonexistent
# pass - 404, error shape: {error: {code: "NOT_FOUND", ...}}

# Clean up test artifacts
rm -f shopping_assistant_v3/backend/database/app.db

# Final git status
git status --short
# pass - only new files under shopping_assistant_v3/ + 3 pre-existing untracked files
```

## Tests Đã Chạy

20 automated tests, tất cả passing:

| Test group | Count | Result |
|---|---|---|
| Health endpoint | 1 | PASSED |
| Create chat job — happy path | 6 | PASSED |
| Create chat job — validation | 7 | PASSED |
| Get chat job — status/error/result | 3 | PASSED |
| Repository — direct DB | 3 | PASSED |

Key test assertions:
- Error shape: `{"error": {"code": ..., "message": ..., "details": [...]}}` — được assert trong mọi validation/error test, không chỉ status code.
- POST /api/chat-jobs tạo conversation + user message + pending job.
- Reuse existing conversation khi `conversation_id` được cung cấp.
- Unknown `conversation_id` trả về 404 NOT_FOUND và tạo zero orphan jobs/messages.
- Request payload được lưu dạng JSON trong `jobs.request_payload`.
- Unknown job trả về 404 với error code `NOT_FOUND`.
- Completed job có `result_payload` trả về parsed result.

## Bằng Chứng Verification

- 20/20 pytest pass với temp SQLite (không network).
- Manual curl: health (200), create job (201), get job (200), validation error (422 với guide shape), not found (404 với guide shape).
- `git status --short` xác nhận không có changes ở segment4/ hoặc shopping_assistant_v2/.
- 3 pre-existing untracked files được preserve: `brainstorming.md`, `prompt_session.md`, `segment4/mo_ta_du_an/PROMPT_NEW_SESSION_APPLY_ALEX_TRANSFER_TO_DATN.md`.
- Không secrets nào bị read, printed, hoặc logged — `.env.example` chỉ chứa empty placeholders.
- Không live Amazon/BestBuy scraping, không OpenAI/Modal/model API calls.
- Không CORS middleware configured (deferred tới Phase 6).
- V3 `.venv` fully isolated khỏi root `tech2ai/.venv`.

## Known Issues

Minor: starlette TestClient emit `StarletteDeprecationWarning: Using httpx with
starlette.testclient is deprecated; install httpx2 instead.` Đây là 3rd-party
deprecation từ combo version `starlette` + `httpx` bundled bởi FastAPI. Không
có functional impact. Có thể resolve khi FastAPI update starlette dependency.

## Deviations From Guide

```text
Guide expectation: "SQLite migration tooling is not selected yet. A simple schema initializer is acceptable"
Actual implementation: SQLAlchemy Base.metadata.create_all() via lifespan event
Reason: user chose Option C during brainstorming (SQLAlchemy ORM, no Alembic)
Should docs be updated? no — guide explicitly allows this approach.

Guide expectation: guide mentions "repository functions for jobs and minimal conversation/message records"
Actual implementation: full create_conversation + create_message + create_job with real persistence, no stubs
Reason: user explicitly required "real persistence, no stubs/pass/TODO" during scope review
Should docs be updated? no — exceeds minimum, which is acceptable.

Guide expectation: FastAPI app may have CORS
Actual implementation: no CORS configured
Reason: user explicitly required removing CORS from Phase 2, deferred to Phase 6
Should docs be updated? no — Phase 6 guide already covers CORS.

Guide expectation: @app.on_event("startup") was used initially
Actual implementation: modern lifespan context manager pattern
Reason: on_event is deprecated in FastAPI ≥ 0.115; lifespan is the recommended replacement
Should docs be updated? no — implementation detail, contract unchanged.
```

## Suggested Doc Updates

```text
Không thấy cần documentation updates ở Phase 2.
Phase 2 implementation khớp approved scope và không thay đổi guide contract nào.
```

## Dual .venv Note

V3 project dùng virtual environment isolated riêng:

- **V3 .venv**: `shopping_assistant_v3/.venv/` — Python 3.13.12, được tạo bởi `uv sync` trong V3 directory. Chứa fastapi, uvicorn, sqlalchemy, httpx, pytest.
- **Root .venv**: `tech2ai/.venv/` — Python 3.12, được tạo riêng cho segment4 prototype. Chứa full prototype dependencies (openai, litellm, torch, chromadb, gradio, etc).

Key rules:
- Mọi V3 commands phải chạy từ directory `shopping_assistant_v3/`: `cd shopping_assistant_v3 && uv run <command>`.
- `uv run` tự động activate đúng `.venv` dựa trên `pyproject.toml` gần nhất.
- KHÔNG chạy V3 code từ root project directory hoặc ngược lại — environments không compatible.
- Root `uv.lock` và root `.venv` không bị modify bởi phase này.

## Codex Review Response

Review file: `shopping_assistant_v3/reports/phase_2_backend_api_and_database_codex_review.md`

Decision: `changes_requested`, 1 major finding.

### Fix applied: unknown conversation_id guard

**Finding:** `POST /api/chat-jobs` accepted bất kỳ non-null `conversation_id`
nào mà không verify conversation tồn tại, tạo orphan messages và jobs.

**Changes:**

1. `backend/api/main.py:101-107` — thêm `get_conversation_by_id` lookup trong `else` branch. Raises `NotFoundError` nếu conversation không tồn tại, ngăn orphan records.
2. `tests/test_api.py` — thêm `test_unknown_conversation_id_returns_404_and_no_orphans`:
   - Assert 404 status code
   - Assert error shape với code `NOT_FOUND`
   - Query bảng `Job` và `Message` để confirm zero rows được tạo

**Verification sau fix:**

```bash
uv run pytest tests/ -v
# 20 passed, 1 warning in 2.29s
# New test: test_unknown_conversation_id_returns_404_and_no_orphans PASSED
```

Tất cả Codex-requested changes đã được resolve. Không có findings khác.

## Reviewer Checklist

Reviewer nên kiểm tra:

- [x] Scope nằm trong approved Phase 2.
- [x] Không có file `segment4/` nào thay đổi trừ khi explicitly approved.
- [x] Không có file `shopping_assistant_v2/` nào thay đổi.
- [x] Không có secrets nào bị đọc, in, hoặc commit.
- [x] Default tests không gọi paid APIs hoặc live scraping.
- [x] API/schema/tool contracts khớp relevant guide.
- [x] Failure paths lưu safe errors.
- [ ] Logs/audit events có `job_id` — chưa applicable (không có worker execution trong Phase 2).
- [x] Docs phản ánh thay đổi thực tế được cập nhật sau approval — không cần changes.

Reviewer decision:

```text
Decision: pending
Reviewer:
Date:
Required changes:
Docs to update after approval:
```
