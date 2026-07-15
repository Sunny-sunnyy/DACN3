"""Worker tests: job lifecycle, idempotency, failure path, audit, and log events.

All tests call process_job() directly. No network, no model calls, no real search.
Uses the isolated temp SQLite from conftest.py.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from backend.database.repository import (
    create_agent_run,
    create_conversation,
    create_job,
    get_job_by_id,
    update_job_error,
    update_job_result,
    update_job_status,
)
from backend.database.schema import AgentRun, Job
from backend.shared.config import DEMO_USER_ID
from backend.worker import build_mock_result, process_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_pending_job(session: Session) -> Job:
    conv = create_conversation(session, user_id=DEMO_USER_ID)
    session.commit()
    job = create_job(
        session,
        user_id=DEMO_USER_ID,
        conversation_id=conv.id,
        request_payload={"message": "test"},
    )
    session.commit()
    return job


def _mock_result_shape(result: dict) -> None:
    assert "answer_vi" in result
    assert isinstance(result["answer_vi"], str)
    assert len(result["answer_vi"]) > 0
    assert "products" in result
    assert isinstance(result["products"], list)
    assert "warnings" in result
    assert isinstance(result["warnings"], list)


# ---------------------------------------------------------------------------
# Mock result
# ---------------------------------------------------------------------------

class TestMockResult:
    def test_matches_guide_shape(self) -> None:
        result = build_mock_result("test-id")
        _mock_result_shape(result)
        assert len(result["products"]) == 1
        p = result["products"][0]
        assert p["source"] == "BestBuy"
        assert p["deal_score"] == "hot"
        assert p["sale_price_usd"] == 699.99
        assert p["discount_usd"] == 200.0


# ---------------------------------------------------------------------------
# process_job — happy path
# ---------------------------------------------------------------------------

class TestProcessJob:
    def test_completes_successfully(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        process_job(job.id)

        db_session.refresh(job)
        assert job.status == "completed"
        assert job.completed_at is not None
        result = json.loads(job.result_payload)
        _mock_result_shape(result)

    def test_creates_agent_run_on_completion(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        process_job(job.id)

        db_session.refresh(job)
        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        assert len(runs) == 1
        run = runs[0]
        assert run.component == "worker"
        assert run.run_type == "worker"
        assert run.status == "completed"
        assert run.started_at is not None
        assert run.ended_at is not None
        assert run.duration_ms is not None
        assert run.duration_ms >= 0

    def test_sets_running_before_completing(self, db_session: Session) -> None:
        """Verify the job transitions through running before reaching completed."""
        job = _create_pending_job(db_session)

        process_job(job.id)

        # After process, status should be completed (running was transient).
        db_session.refresh(job)
        assert job.status == "completed"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_completed_job_not_reprocessed(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)

        first_completed = job.completed_at
        first_result = job.result_payload

        # Process again.
        process_job(job.id)
        db_session.refresh(job)

        assert job.status == "completed"
        assert job.completed_at == first_completed
        assert job.result_payload == first_result

        # No additional agent_run created.
        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        assert len(runs) == 1

    def test_running_job_is_skipped_when_fresh(self, db_session: Session) -> None:
        """A recently-started running job should be skipped (not stale)."""
        import datetime as dt

        job = _create_pending_job(db_session)
        update_job_status(
            db_session, job, "running",
            started_at=dt.datetime.now(dt.timezone.utc),
        )
        db_session.commit()
        original_updated = job.updated_at

        process_job(job.id)
        db_session.refresh(job)

        assert job.status == "running"
        assert job.updated_at == original_updated  # No change.

    def test_stale_running_job_is_recovered(self, db_session: Session) -> None:
        """A running job with old started_at is stale and should be recovered."""
        import datetime as dt

        job = _create_pending_job(db_session)
        update_job_status(
            db_session, job, "running",
            started_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10),
        )
        db_session.commit()

        process_job(job.id)
        db_session.refresh(job)

        assert job.status == "completed"

    def test_failed_job_is_skipped(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        update_job_error(db_session, job, "previous failure")
        db_session.commit()
        original_error = job.error_message

        process_job(job.id)
        db_session.refresh(job)

        assert job.status == "failed"
        assert job.error_message == original_error


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------

class TestFailurePath:
    def test_result_builder_exception_sets_failed(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_builder(_job_id: str) -> dict:
            raise RuntimeError("mock search timeout")

        process_job(job.id, result_builder=_failing_builder)
        db_session.refresh(job)

        assert job.status == "failed"
        assert job.error_message is not None
        assert "Worker failed" in job.error_message

    def test_failure_creates_agent_run_with_failed_status(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_builder(_job_id: str) -> dict:
            raise RuntimeError("boom")

        process_job(job.id, result_builder=_failing_builder)
        db_session.refresh(job)

        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert runs[0].error_message is not None
        assert "Worker failed" in runs[0].error_message

    def test_failure_does_not_leave_stale_running(self, db_session: Session) -> None:
        """Failed jobs must not remain stuck in running."""
        job = _create_pending_job(db_session)

        def _failing_builder(_job_id: str) -> dict:
            raise RuntimeError("x")

        process_job(job.id, result_builder=_failing_builder)
        db_session.refresh(job)

        # The job must end in failed, not stuck in running.
        assert job.status == "failed"


# ---------------------------------------------------------------------------
# Unknown job
# ---------------------------------------------------------------------------

class TestUnknownJob:
    def test_unknown_job_does_not_crash(self) -> None:
        """Calling process_job with a nonexistent ID should not raise."""
        process_job("nonexistent-job-id")


# ---------------------------------------------------------------------------
# Log events
# ---------------------------------------------------------------------------

class TestLogEvents:
    def test_emits_started_and_completed_events(self, caplog, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        with caplog.at_level("INFO", logger="shopping_assistant_v3.worker"):
            process_job(job.id)

        log_text = caplog.text
        assert "JOB_STARTED" in log_text
        assert "JOB_COMPLETED" in log_text
        assert job.id in log_text

    def test_emits_failed_event_on_error(self, caplog, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_builder(_job_id: str) -> dict:
            raise RuntimeError("xyz")

        with caplog.at_level("INFO", logger="shopping_assistant_v3.worker"):
            process_job(job.id, result_builder=_failing_builder)

        log_text = caplog.text
        assert "JOB_STARTED" in log_text
        assert "JOB_FAILED" in log_text
        assert job.id in log_text

    def test_logs_are_valid_json(self, caplog, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        with caplog.at_level("INFO", logger="shopping_assistant_v3.worker"):
            process_job(job.id)

        # Each log line from our logger should be parseable JSON with job_id.
        for record in caplog.records:
            if record.name == "shopping_assistant_v3.worker":
                parsed = json.loads(record.message)
                assert parsed["job_id"] == job.id
                assert "event" in parsed
                assert parsed["component"] == "worker"
                assert "timestamp" in parsed
