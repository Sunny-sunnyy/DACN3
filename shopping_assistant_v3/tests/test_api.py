"""Endpoint smoke tests, validation tests, and repository tests.

All tests use an isolated temp SQLite database. No network, no model calls.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.database.repository import (
    create_conversation,
    create_job,
    create_message,
    get_job_by_id,
)
from backend.shared.config import DEMO_USER_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_shape(response_json: dict, expected_code: str) -> None:
    """Assert the response body matches the guide error shape."""
    assert "error" in response_json, f"Expected 'error' key, got: {response_json}"
    err = response_json["error"]
    assert err["code"] == expected_code, f"Expected code {expected_code}, got {err['code']}"
    assert isinstance(err["message"], str)
    assert isinstance(err["details"], list)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "shopping-assistant-v3"


# ---------------------------------------------------------------------------
# POST /api/chat-jobs — happy path
# ---------------------------------------------------------------------------

class TestCreateChatJob:
    def test_valid_request_returns_pending_job(self, client: TestClient) -> None:
        payload = {"message": "Tim laptop gaming duoi 800 do"}
        response = client.post("/api/chat-jobs", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert "job_id" in body
        assert body["status"] == "pending"
        assert "Poll status" in body["message"]

    def test_creates_conversation_when_conversation_id_is_null(
        self, client: TestClient, db_session: Session
    ) -> None:
        response = client.post(
            "/api/chat-jobs",
            json={"message": "Tim laptop gaming duoi 800 do"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        job = get_job_by_id(db_session, job_id)
        assert job is not None
        assert job.conversation_id is not None
        # Verify conversation was created.
        from backend.database.repository import get_conversation_by_id

        conv = get_conversation_by_id(db_session, job.conversation_id)
        assert conv is not None
        assert conv.user_id == DEMO_USER_ID

    def test_creates_user_message(self, client: TestClient, db_session: Session) -> None:
        msg_text = "Tim laptop gaming duoi 800 do"
        response = client.post("/api/chat-jobs", json={"message": msg_text})
        assert response.status_code == 201
        body = response.json()

        job = get_job_by_id(db_session, body["job_id"])
        assert job is not None
        # The message should be linked via the conversation.
        from backend.database.schema import Conversation, Message

        messages = (
            db_session.query(Message)
            .join(Conversation)
            .filter(Conversation.id == job.conversation_id)
            .all()
        )
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == msg_text

    def test_reuses_existing_conversation_id(self, client: TestClient, db_session: Session) -> None:
        # Create a conversation first.
        conv = create_conversation(db_session, user_id=DEMO_USER_ID, title="test conv")
        db_session.commit()

        response = client.post(
            "/api/chat-jobs",
            json={"message": "hello", "conversation_id": conv.id},
        )
        assert response.status_code == 201
        body = response.json()

        job = get_job_by_id(db_session, body["job_id"])
        assert job is not None
        assert job.conversation_id == conv.id

    def test_unknown_conversation_id_returns_404_and_no_orphans(
        self, client: TestClient, db_session: Session
    ) -> None:
        response = client.post(
            "/api/chat-jobs",
            json={"message": "Tim laptop", "conversation_id": "missing-conv"},
        )
        assert response.status_code == 404
        _error_shape(response.json(), "NOT_FOUND")

        # Verify no orphan job or message was created.
        from backend.database.schema import Job, Message

        job_count = db_session.query(Job).count()
        msg_count = db_session.query(Message).count()
        assert job_count == 0, f"Expected 0 jobs, found {job_count}"
        assert msg_count == 0, f"Expected 0 messages, found {msg_count}"

    def test_request_payload_is_stored(self, client: TestClient, db_session: Session) -> None:
        payload = {
            "message": "Tim laptop",
            "source": "Amazon",
            "max_results_per_source": 10,
        }
        response = client.post("/api/chat-jobs", json=payload)
        assert response.status_code == 201
        body = response.json()

        job = get_job_by_id(db_session, body["job_id"])
        assert job is not None
        stored = json.loads(job.request_payload)
        assert stored["message"] == "Tim laptop"
        assert stored["source"] == "Amazon"
        assert stored["max_results_per_source"] == 10


# ---------------------------------------------------------------------------
# POST /api/chat-jobs — validation
# ---------------------------------------------------------------------------

class TestCreateChatJobValidation:
    def test_empty_message_rejected(self, client: TestClient) -> None:
        response = client.post("/api/chat-jobs", json={"message": ""})
        assert response.status_code == 422
        _error_shape(response.json(), "VALIDATION_ERROR")

    def test_too_short_message_rejected(self, client: TestClient) -> None:
        response = client.post("/api/chat-jobs", json={"message": "a"})
        assert response.status_code == 422
        _error_shape(response.json(), "VALIDATION_ERROR")

    def test_missing_message_rejected(self, client: TestClient) -> None:
        response = client.post("/api/chat-jobs", json={})
        assert response.status_code == 422
        _error_shape(response.json(), "VALIDATION_ERROR")

    def test_invalid_source_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/chat-jobs",
            json={"message": "Tim laptop", "source": "Ebay"},
        )
        assert response.status_code == 422
        _error_shape(response.json(), "VALIDATION_ERROR")

    def test_max_results_too_low(self, client: TestClient) -> None:
        response = client.post(
            "/api/chat-jobs",
            json={"message": "Tim laptop", "max_results_per_source": 0},
        )
        assert response.status_code == 422
        _error_shape(response.json(), "VALIDATION_ERROR")

    def test_max_results_too_high(self, client: TestClient) -> None:
        response = client.post(
            "/api/chat-jobs",
            json={"message": "Tim laptop", "max_results_per_source": 21},
        )
        assert response.status_code == 422
        _error_shape(response.json(), "VALIDATION_ERROR")

    def test_error_details_is_list(self, client: TestClient) -> None:
        """Validation error details must be a list, not null or dict."""
        response = client.post("/api/chat-jobs", json={"message": ""})
        assert response.status_code == 422
        body = response.json()
        assert isinstance(body["error"]["details"], list)


# ---------------------------------------------------------------------------
# GET /api/chat-jobs/{job_id}
# ---------------------------------------------------------------------------

class TestGetChatJob:
    def test_existing_job_returns_full_status(self, client: TestClient) -> None:
        # Create a job first.
        create_resp = client.post(
            "/api/chat-jobs",
            json={"message": "Tim laptop gaming"},
        )
        job_id = create_resp.json()["job_id"]

        # Get it.
        response = client.get(f"/api/chat-jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == job_id
        assert body["status"] == "pending"
        assert body["created_at"] is not None
        assert body["error_message"] is None
        assert body["result"] is None

    def test_unknown_job_returns_404_error_shape(self, client: TestClient) -> None:
        response = client.get("/api/chat-jobs/nonexistent-id")
        assert response.status_code == 404
        _error_shape(response.json(), "NOT_FOUND")

    def test_completed_job_returns_result(self, client: TestClient, db_session: Session) -> None:
        from backend.database.schema import Job

        # Directly set a completed job in the database.
        job = Job(
            user_id=DEMO_USER_ID,
            status="completed",
            result_payload=json.dumps(
                {"answer_vi": "Khong co deal nao.", "products": [], "warnings": []}
            ),
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/chat-jobs/{job.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert body["result"] is not None
        assert body["result"]["answer_vi"] == "Khong co deal nao."


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestRepository:
    def test_create_and_get_job(self, db_session: Session) -> None:
        conv = create_conversation(db_session, user_id=DEMO_USER_ID)
        db_session.commit()

        job = create_job(
            db_session,
            user_id=DEMO_USER_ID,
            conversation_id=conv.id,
            request_payload={"message": "hello"},
        )
        db_session.commit()

        fetched = get_job_by_id(db_session, job.id)
        assert fetched is not None
        assert fetched.status == "pending"
        assert fetched.user_id == DEMO_USER_ID
        assert fetched.conversation_id == conv.id

    def test_create_conversation_and_message(self, db_session: Session) -> None:
        conv = create_conversation(db_session, user_id=DEMO_USER_ID, title="test")
        db_session.commit()
        assert conv.id is not None
        assert conv.title == "test"

        msg = create_message(db_session, conversation_id=conv.id, role="user", content="xin chao")
        db_session.commit()
        assert msg.id is not None
        assert msg.role == "user"
        assert msg.content == "xin chao"

    def test_get_job_by_id_returns_none_for_unknown(self, db_session: Session) -> None:
        assert get_job_by_id(db_session, "no-such-id") is None
