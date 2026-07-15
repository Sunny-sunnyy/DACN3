# Phase 2 Backend API And Database — Implementation Report

## Phase

`Phase 2: Backend API And Database`

Implementer: Claude Code (DeepSeek Implementer)

Date: 2026-07-15

Branch: TTTN

Commit reviewed: `not committed yet`

## Summary

Implemented the full Phase 2 scope per `guides/2_backend_api_and_database.md` with user-approved adjustments:

- FastAPI app with 3 endpoints: `GET /health`, `POST /api/chat-jobs`, `GET /api/chat-jobs/{job_id}`.
- SQLite persistence via SQLAlchemy ORM with `Base.metadata.create_all()` — 6 tables: jobs, conversations, messages, agent_runs, products, price_estimates.
- Real repository layer (no stubs): `create_job`, `get_job_by_id`, `create_conversation`, `create_message`.
- `POST /api/chat-jobs` creates a new conversation when `conversation_id` is null, stores the user message, and creates a pending job linked to `demo_user`.
- Custom error handlers return the guide-compliant safe error shape `{error: {code, message, details}}` for validation (422), not-found (404), and app errors (500).
- All 20 tests pass using pytest + FastAPI TestClient + temp SQLite. No network, no model calls, no scraping.
- No CORS (deferred to Phase 6).
- V3 has its own isolated `.venv` and `pyproject.toml` — root project (tech2ai) untouched.

## Files Created

```text
shopping_assistant_v3/pyproject.toml - uv project config, deps: fastapi, uvicorn[standard], sqlalchemy, httpx, pytest
shopping_assistant_v3/uv.lock - generated lockfile (V3 only, not root)
shopping_assistant_v3/backend/__init__.py - package marker
shopping_assistant_v3/backend/shared/__init__.py - package marker
shopping_assistant_v3/backend/shared/config.py - env loading, safety flags, DATABASE_URL, no secret logging
shopping_assistant_v3/backend/shared/errors.py - AppError, ValidationError, NotFoundError, error_response()
shopping_assistant_v3/backend/database/__init__.py - package marker
shopping_assistant_v3/backend/database/session.py - engine singleton, session factory, get_db FastAPI dependency, init_db()
shopping_assistant_v3/backend/database/schema.py - 6 SQLAlchemy models (jobs, conversations, messages, agent_runs, products, price_estimates)
shopping_assistant_v3/backend/database/repository.py - create_job, get_job_by_id, create_conversation, create_message (real persistence)
shopping_assistant_v3/backend/api/__init__.py - package marker
shopping_assistant_v3/backend/api/schemas.py - Pydantic models: ChatJobRequest, ChatJobResponse, JobStatusResponse, ProductResult, ErrorDetail
shopping_assistant_v3/backend/api/main.py - FastAPI app, 3 endpoints, lifespan (init_db), custom error handlers, no CORS
shopping_assistant_v3/tests/__init__.py - package marker
shopping_assistant_v3/tests/conftest.py - temp SQLite isolation, TestClient fixture, dependency override
shopping_assistant_v3/tests/test_api.py - 20 tests: health, create job (6), validation (7), get job status (3), repository (3), plus unknown conversation_id guard
```

## Files Modified

```text
shopping_assistant_v3/backend/api/main.py - added conversation lookup on non-null conversation_id; raises NotFoundError if missing (Codex review fix)
shopping_assistant_v3/tests/test_api.py - added test_unknown_conversation_id_returns_404_and_no_orphans (Codex review fix)
```

Post-review modifications only; all initial files were created in the first pass.
segment4/ and shopping_assistant_v2/ were not touched.

## Commands Run

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

## Tests Run

20 automated tests, all passing:

| Test group | Count | Result |
|---|---|---|
| Health endpoint | 1 | PASSED |
| Create chat job — happy path | 6 | PASSED |
| Create chat job — validation | 7 | PASSED |
| Get chat job — status/error/result | 3 | PASSED |
| Repository — direct DB | 3 | PASSED |

Key test assertions:
- Error shape: `{"error": {"code": ..., "message": ..., "details": [...]}}` — asserted on every validation/error test, not just status code.
- POST /api/chat-jobs creates conversation + user message + pending job.
- Reuses existing conversation when `conversation_id` is provided.
- Unknown `conversation_id` returns 404 NOT_FOUND and creates zero orphan jobs/messages.
- Request payload stored as JSON in `jobs.request_payload`.
- Unknown job returns 404 with `NOT_FOUND` error code.
- Completed job with `result_payload` returns parsed result.

## Verification Evidence

- 20/20 pytest pass with temp SQLite (no network).
- Manual curl: health (200), create job (201), get job (200), validation error (422 with guide shape), not found (404 with guide shape).
- `git status --short` confirms no segment4/ or shopping_assistant_v2/ changes.
- 3 pre-existing untracked files preserved: `brainstorming.md`, `prompt_session.md`, `segment4/mo_ta_du_an/PROMPT_NEW_SESSION_APPLY_ALEX_TRANSFER_TO_DATN.md`.
- No secrets read, printed, or logged — `.env.example` contains only empty placeholders.
- No live Amazon/BestBuy scraping, no OpenAI/Modal/model API calls.
- No CORS middleware configured (deferred to Phase 6).
- V3 `.venv` is fully isolated from root `tech2ai/.venv`.

## Known Issues

Minor: the starlette TestClient emits `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` This is a 3rd-party deprecation from the `starlette` + `httpx` version combo bundled by FastAPI. No functional impact. Can be resolved when FastAPI updates its starlette dependency.

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
No documentation updates appear necessary at Phase 2.
Phase 2 implementation matches the approved scope and does not change any guide contract.
```

## Dual .venv Note

The V3 project uses its own isolated virtual environment:

- **V3 .venv**: `shopping_assistant_v3/.venv/` — Python 3.13.12, created by `uv sync` in the V3 directory. Contains fastapi, uvicorn, sqlalchemy, httpx, pytest.
- **Root .venv**: `tech2ai/.venv/` — Python 3.12, created separately for the segment4 prototype. Contains the full prototype dependencies (openai, litellm, torch, chromadb, gradio, etc).

Key rules:
- All V3 commands must be run from `shopping_assistant_v3/` directory: `cd shopping_assistant_v3 && uv run <command>`.
- `uv run` automatically activates the correct `.venv` based on the nearest `pyproject.toml`.
- Do NOT run V3 code from the root project directory or vice versa — the environments are incompatible.
- Root `uv.lock` and root `.venv` were not modified by this phase.

## Codex Review Response

Review file: `shopping_assistant_v3/reports/phase_2_backend_api_and_database_codex_review.md`

Decision: `changes_requested`, 1 major finding.

### Fix applied: unknown conversation_id guard

**Finding:** `POST /api/chat-jobs` accepted any non-null `conversation_id` without verifying the conversation exists, creating orphan messages and jobs.

**Changes:**

1. `backend/api/main.py:101-107` — added `get_conversation_by_id` lookup in the `else` branch. Raises `NotFoundError` if conversation does not exist, preventing orphan records.
2. `tests/test_api.py` — added `test_unknown_conversation_id_returns_404_and_no_orphans`:
   - Asserts 404 status code
   - Asserts error shape with `NOT_FOUND` code
   - Queries `Job` and `Message` tables to confirm zero rows were created

**Verification after fix:**

```bash
uv run pytest tests/ -v
# 20 passed, 1 warning in 2.29s
# New test: test_unknown_conversation_id_returns_404_and_no_orphans PASSED
```

All Codex-requested changes are resolved. No other findings.

## Reviewer Checklist

Reviewer should inspect:

- [x] Scope stayed within the approved Phase 2.
- [x] No `segment4/` files changed unless explicitly approved.
- [x] No `shopping_assistant_v2/` files changed.
- [x] No secrets were read, printed, or committed.
- [x] Default tests do not call paid APIs or live scraping.
- [x] API/schema/tool contracts match the relevant guide.
- [x] Failure paths store safe errors.
- [ ] Logs/audit events include `job_id` — not yet applicable (no worker execution in Phase 2).
- [x] Docs that changed reality are updated after approval — no changes needed.

Reviewer decision:

```text
Decision: pending
Reviewer:
Date:
Required changes:
Docs to update after approval:
```
