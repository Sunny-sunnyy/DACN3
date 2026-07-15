"""FastAPI application for Shopping Assistant V3.

Endpoints: GET /health, POST /api/chat-jobs, GET /api/chat-jobs/{job_id}.
No CORS in Phase 2. No worker execution. Route handlers are thin.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.api.schemas import ChatJobRequest, ChatJobResponse, JobStatusResponse
from backend.database.repository import (
    create_conversation,
    create_job,
    create_message,
    get_conversation_by_id,
    get_job_by_id,
)
from backend.database.session import get_db, init_db
from backend.shared.config import DEMO_USER_ID
from backend.shared.errors import (
    AppError,
    NotFoundError,
    ValidationError,
    error_response,
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(title="Shopping Assistant V3", version="0.1.0", lifespan=_lifespan)


# ---------------------------------------------------------------------------
# Custom error handlers — ensure responses match the guide error shape.
# ---------------------------------------------------------------------------

@app.exception_handler(ValidationError)
async def _validation_handler(_request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_response(exc.code, exc.message, exc.details),
    )


@app.exception_handler(NotFoundError)
async def _not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_response(exc.code, exc.message),
    )


@app.exception_handler(AppError)
async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_response(exc.code, exc.message, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def _fastapi_validation_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    details: list[str] = []
    for err in exc.errors():
        loc = " -> ".join(str(p) for p in err["loc"])
        details.append(f"{loc}: {err['msg']}")
    return JSONResponse(
        status_code=422,
        content=error_response("VALIDATION_ERROR", "Invalid request.", details),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "shopping-assistant-v3"}


@app.post("/api/chat-jobs", response_model=ChatJobResponse, status_code=201)
def create_chat_job(body: ChatJobRequest, session: Session = Depends(get_db)) -> dict[str, str]:
    conversation_id = body.conversation_id
    if conversation_id is None:
        conversation = create_conversation(session, user_id=DEMO_USER_ID)
        conversation_id = conversation.id
    else:
        existing = get_conversation_by_id(session, conversation_id)
        if existing is None:
            raise NotFoundError(f"Conversation {conversation_id} not found.")

    create_message(
        session,
        conversation_id=conversation_id,
        role="user",
        content=body.message,
    )

    job = create_job(
        session,
        user_id=DEMO_USER_ID,
        conversation_id=conversation_id,
        request_payload=body.model_dump(mode="json"),
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "message": "Job created. Poll status endpoint for results.",
    }


@app.get("/api/chat-jobs/{job_id}", response_model=JobStatusResponse)
def get_chat_job(job_id: str, session: Session = Depends(get_db)) -> dict[str, object]:
    job = get_job_by_id(session, job_id)
    if job is None:
        raise NotFoundError(f"Job {job_id} not found.")

    result = None
    if job.result_payload:
        result = json.loads(job.result_payload)

    return {
        "job_id": job.id,
        "status": job.status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "result": result,
        "error_message": job.error_message,
    }
