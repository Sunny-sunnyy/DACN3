"""Repository layer for job, conversation, message, and agent_run persistence.

All database access goes through these functions. No scattered SQL elsewhere.
"""

from __future__ import annotations

import datetime
import json
from typing import Any

from sqlalchemy.orm import Session

from backend.database.schema import AgentRun, Conversation, Job, Message


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Job repository
# ---------------------------------------------------------------------------

def create_job(
    session: Session,
    *,
    user_id: str,
    conversation_id: str,
    request_payload: dict[str, Any],
    job_type: str = "chat",
) -> Job:
    """Create a pending job linked to a conversation and user."""
    job = Job(
        user_id=user_id,
        job_type=job_type,
        status="pending",
        conversation_id=conversation_id,
        request_payload=json.dumps(request_payload, ensure_ascii=False),
    )
    session.add(job)
    session.flush()
    return job


def get_job_by_id(session: Session, job_id: str) -> Job | None:
    """Retrieve a job by its primary key."""
    return session.query(Job).filter(Job.id == job_id).first()


def update_job_status(
    session: Session,
    job: Job,
    status: str,
    *,
    started_at: datetime.datetime | None = None,
    completed_at: datetime.datetime | None = None,
) -> None:
    """Update job status and optional timestamp fields."""
    job.status = status
    job.updated_at = _utcnow()
    if started_at is not None:
        job.started_at = started_at
    if completed_at is not None:
        job.completed_at = completed_at
    session.flush()


def update_job_result(
    session: Session,
    job: Job,
    result_payload: dict[str, Any],
) -> None:
    """Set job result and mark completed."""
    job.status = "completed"
    job.result_payload = json.dumps(result_payload, ensure_ascii=False)
    job.completed_at = _utcnow()
    job.updated_at = _utcnow()
    session.flush()


def update_job_error(
    session: Session,
    job: Job,
    error_message: str,
) -> None:
    """Set job error and mark failed."""
    job.status = "failed"
    job.error_message = error_message
    job.completed_at = _utcnow()
    job.updated_at = _utcnow()
    session.flush()


# ---------------------------------------------------------------------------
# Conversation repository
# ---------------------------------------------------------------------------

def create_conversation(
    session: Session,
    *,
    user_id: str,
    title: str | None = None,
) -> Conversation:
    """Create a new conversation for a user."""
    conversation = Conversation(user_id=user_id, title=title)
    session.add(conversation)
    session.flush()
    return conversation


def get_conversation_by_id(session: Session, conversation_id: str) -> Conversation | None:
    """Retrieve a conversation by its primary key."""
    return session.query(Conversation).filter(Conversation.id == conversation_id).first()


# ---------------------------------------------------------------------------
# Message repository
# ---------------------------------------------------------------------------

def create_message(
    session: Session,
    *,
    conversation_id: str,
    role: str,
    content: str,
) -> Message:
    """Store a message (user, assistant, system, or tool)."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    session.add(message)
    session.flush()
    return message


# ---------------------------------------------------------------------------
# Agent run repository
# ---------------------------------------------------------------------------

def create_agent_run(
    session: Session,
    *,
    job_id: str,
    component: str,
    run_type: str,
    status: str = "started",
    model_provider: str | None = None,
    model_name: str | None = None,
    input_summary: str | None = None,
) -> AgentRun:
    """Create an audit record for a component run within a job."""
    run = AgentRun(
        job_id=job_id,
        component=component,
        run_type=run_type,
        status=status,
        model_provider=model_provider,
        model_name=model_name,
        input_summary=input_summary,
    )
    session.add(run)
    session.flush()
    return run


def update_agent_run(
    session: Session,
    run: AgentRun,
    *,
    status: str,
    ended_at: datetime.datetime | None = None,
    duration_ms: int | None = None,
    output_summary: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update an agent run record with completion or failure details."""
    run.status = status
    if ended_at is not None:
        run.ended_at = ended_at
    if duration_ms is not None:
        run.duration_ms = duration_ms
    if output_summary is not None:
        run.output_summary = output_summary
    if error_message is not None:
        run.error_message = error_message
    session.flush()
