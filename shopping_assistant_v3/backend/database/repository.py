"""Repository layer for job, conversation, and message persistence.

All database access goes through these functions. No scattered SQL elsewhere.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from backend.database.schema import Conversation, Job, Message


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
