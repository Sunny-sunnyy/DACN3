"""Local async job worker.

process_job(job_id) is called by FastAPI BackgroundTasks after POST /api/chat-jobs.
It runs in the same process, no separate worker or queue.

Lifecycle: pending -> running -> completed (or failed).
Idempotent: completed jobs return existing result; running/failed jobs are skipped.
All persistence goes through repository helpers. Structured JSON logs include job_id.
"""

from __future__ import annotations

import datetime
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from backend.database.repository import (
    create_agent_run,
    get_job_by_id,
    update_agent_run,
    update_job_error,
    update_job_result,
    update_job_status,
)
from backend.database.session import get_session_factory

logger = logging.getLogger("shopping_assistant_v3.worker")


# ---------------------------------------------------------------------------
# Mock result
# ---------------------------------------------------------------------------

def build_mock_result(job_id: str) -> dict[str, Any]:
    """Deterministic mock result matching the Phase 3 guide contract.

    Exists as a separate function so tests can inject a failing builder
    via process_job(result_builder=...).
    """
    return {
        "answer_vi": "Minh da tim thay mot so lua chon mau de kiem tra luong demo.",
        "products": [
            {
                "source": "BestBuy",
                "title": "Mock Gaming Laptop",
                "brand": "MockBrand",
                "sale_price_usd": 699.99,
                "estimated_value_usd": 899.99,
                "discount_usd": 200.0,
                "deal_score": "hot",
                "url": "https://www.bestbuy.com/",
            }
        ],
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------

def _log_event(event: str, job_id: str, **extra: object) -> None:
    """Emit a structured JSON log line with job_id correlation."""
    payload = {
        "event": event,
        "job_id": job_id,
        "component": "worker",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **extra,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------

def process_job(
    job_id: str,
    result_builder: Callable[[str], dict[str, Any]] = build_mock_result,
) -> None:
    """Process a single job: pending -> running -> completed (or failed).

    Args:
        job_id: The job to process.
        result_builder: Injectable function(job_id) -> result dict.
                        Tests inject a failing callable to exercise the error path.

    Idempotency:
        - completed: return existing result, no new agent_run.
        - running/failed: skip safe, no overwrite.
        - pending: process normally.
    """
    factory = get_session_factory()
    session = factory()
    started_at = datetime.datetime.now(datetime.timezone.utc)
    t0 = time.monotonic()

    try:
        job = get_job_by_id(session, job_id)
        if job is None:
            _log_event("JOB_FAILED", job_id, reason="unknown_job_id")
            return

        # --- Idempotency gates ---
        if job.status == "completed":
            _log_event("JOB_SKIPPED", job_id, reason="already_completed")
            return

        if job.status == "failed":
            _log_event("JOB_SKIPPED", job_id, reason="already_failed")
            return

        if job.status == "running":
            # Allow reprocessing if the job appears stale (server crash, stuck thread).
            # SQLite may strip timezone, so normalize to naive UTC before comparison.
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            started = job.started_at
            if started is not None and started.tzinfo is not None:
                started = started.replace(tzinfo=None)
            stale = (
                started is None
                or (now_utc.replace(tzinfo=None) - started).total_seconds() > 300
            )
            if not stale:
                _log_event("JOB_SKIPPED", job_id, reason="already_running")
                return
            _log_event("JOB_RECOVERING", job_id, reason="stale_running")

        # --- Normal processing ---
        update_job_status(session, job, "running", started_at=started_at)
        _log_event("JOB_STARTED", job_id)

        agent_run = create_agent_run(
            session,
            job_id=job_id,
            component="worker",
            run_type="worker",
            status="started",
        )

        result = result_builder(job_id)

        update_job_result(session, job, result)
        duration_ms = int((time.monotonic() - t0) * 1000)
        update_agent_run(
            session,
            agent_run,
            status="completed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            duration_ms=duration_ms,
            output_summary="mock_result",
        )

        _log_event(
            "JOB_COMPLETED",
            job_id,
            duration_ms=duration_ms,
            product_count=len(result.get("products", [])),
        )

        session.commit()

    except Exception as exc:
        session.rollback()
        # API-visible error: sanitized, no raw exception text.
        safe_error = "Worker failed. Try again later."
        # Log raw details to internal logger only (never to DB or API).
        logger.exception("Worker internal failure for job %s", job_id)
        try:
            _save_failure(job_id, started_at, t0, safe_error)
        except Exception:
            logger.exception("Failed to persist job failure for %s", job_id)
        _log_event("JOB_FAILED", job_id)

    finally:
        session.close()


def _save_failure(
    job_id: str,
    started_at: datetime.datetime,
    t0: float,
    error_message: str,
) -> None:
    """Persist job failure in a fresh session."""
    factory = get_session_factory()
    session = factory()
    try:
        job = get_job_by_id(session, job_id)
        if job is None:
            return
        update_job_error(session, job, error_message)
        duration_ms = int((time.monotonic() - t0) * 1000)
        agent_run = create_agent_run(
            session,
            job_id=job_id,
            component="worker",
            run_type="worker",
            status="failed",
            input_summary="mock_result",
        )
        update_agent_run(
            session,
            agent_run,
            status="failed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            duration_ms=duration_ms,
            error_message=error_message,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
