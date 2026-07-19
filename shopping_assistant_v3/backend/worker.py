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
    create_price_estimate,
    create_product,
    get_job_by_id,
    update_agent_run,
    update_job_error,
    update_job_result,
    update_job_status,
)
from backend.database.session import get_session_factory
from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput
from backend.tools.price_estimator.schemas import PriceEstimateInput, PriceEstimateOutput

logger = logging.getLogger("shopping_assistant_v3.worker")

DealSearchRunner = Callable[[DealSearchInput], DealSearchOutput]
PriceEstimatorRunner = Callable[[PriceEstimateInput], PriceEstimateOutput]

PLACEHOLDER_ANSWER_VI = (
    "Minh da tim thay mot so san pham phu hop. Duoi day la ket qua phan tich deal."
)

VIETNAMESE_STOP_WORDS = {
    "tìm", "tim", "mua", "cho", "giúp", "giup", "mình", "minh",
    "tôi", "toi", "với", "voi", "cần", "can", "muốn", "muon",
    "một", "mot", "cái", "cai", "nào", "nao", "giá", "gia",
    "dưới", "duoi", "trên", "tren", "khoảng", "khoang",
}


# ---------------------------------------------------------------------------
# Query normalization (Phase 4A bridge — Router replaces this in Phase 5)
# ---------------------------------------------------------------------------

def _normalize_query(message: str) -> str:
    """Normalize a Vietnamese user message into English-like search tokens.

    Phase 4A temporary bridge: lowercase + strip Vietnamese intent/filler words.
    Phase 5 Router will replace this with actual translation/intent extraction.
    """
    tokens = message.strip().lower().split()
    meaningful = [t for t in tokens if t not in VIETNAMESE_STOP_WORDS]
    return " ".join(meaningful)


# ---------------------------------------------------------------------------
# Tool runner helpers
# ---------------------------------------------------------------------------

def _run_deal_search(
    session: Any,
    job_id: str,
    query_en: str,
    source: str,
    max_results_per_source: int,
    runner: DealSearchRunner,
) -> DealSearchOutput:
    """Execute deal_search_tool and return output.

    Audit row is created in the main session by the caller (process_job)
    so that it survives commit/rollback decisions correctly.
    """
    search_input = DealSearchInput(
        query_en=query_en,
        source=source,
        max_results_per_source=max_results_per_source,
    )
    return runner(search_input)


def _run_price_estimator(
    session: Any,
    job_id: str,
    product: Any,
    runner: PriceEstimatorRunner,
) -> PriceEstimateOutput:
    """Execute price_estimator_tool for a single product and return output.

    Audit row is created in the main session by the caller (process_job)
    so that it survives commit/rollback decisions correctly.
    """
    from backend.tools.deal_search.schemas import ProductCandidate as PC

    candidate = PC(
        source=product.source,
        title=product.title,
        brand=product.brand,
        sale_price_usd=product.sale_price_usd,
        url=product.url,
        features=product.features,
        raw_source_payload=(
            json.loads(product.raw_source_payload)
            if product.raw_source_payload
            else {}
        ),
    )
    est_input = PriceEstimateInput(product=candidate)
    return runner(est_input)


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
    *,
    deal_search_runner: DealSearchRunner | None = None,
    price_estimator_runner: PriceEstimatorRunner | None = None,
) -> None:
    """Process a single job through the mock search/pricing pipeline.

    Args:
        job_id: The job to process.
        deal_search_runner: Injectable deal_search function. Defaults to mock.
        price_estimator_runner: Injectable estimate_price function. Defaults to mock.

    Idempotency:
        - completed: return existing result, no new processing.
        - failed: skip.
        - running: skip unless stale (>5 min).
        - pending: process normally.
    """
    if deal_search_runner is None:
        from backend.tools.deal_search.tool import deal_search as deal_search_runner
    if price_estimator_runner is None:
        from backend.tools.price_estimator.tool import (
            estimate_price as price_estimator_runner,
        )

    factory = get_session_factory()
    session = factory()
    started_at = datetime.datetime.now(datetime.timezone.utc)
    t0 = time.monotonic()
    _tool_timings: list[dict[str, object]] = []

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

        # --- Parse request ---
        request = json.loads(job.request_payload or "{}")
        message = request.get("message", "")
        source = request.get("source", "All")
        max_results = request.get("max_results_per_source", 5)
        query_en = _normalize_query(message)

        # --- Start job ---
        update_job_status(session, job, "running", started_at=started_at)
        _log_event("JOB_STARTED", job_id)

        # Create worker-level audit record (preserved from Phase 3).
        worker_run = create_agent_run(
            session,
            job_id=job_id,
            component="worker",
            run_type="worker",
            status="started",
        )

        # --- Phase 4A pipeline ---

        # Step 1: Deal search.
        _tool_timings.append({
            "component": "deal_search_tool",
            "input_summary": f"query_en={query_en}, source={source}",
            "t0": time.monotonic(),
        })
        search_output = _run_deal_search(
            session, job_id, query_en, source, max_results, deal_search_runner
        )
        # Success: create completed audit row in main session.
        _finalize_tool_run(
            session, job_id, _tool_timings[-1], search_output
        )

        # Step 2: Persist products.
        all_warnings: list[str] = list(search_output.warnings)
        db_products: list[Any] = []
        for sp in search_output.products:
            p = create_product(
                session,
                job_id=job_id,
                source=sp.source,
                title=sp.title,
                brand=sp.brand,
                sale_price_usd=sp.sale_price_usd,
                url=sp.url,
                features=sp.features,
                raw_source_payload=sp.raw_source_payload,
            )
            db_products.append(p)

        # Step 3: Estimate prices per product.
        result_products: list[dict[str, Any]] = []
        for db_p in db_products:
            _tool_timings.append({
                "component": "price_estimator_tool",
                "input_summary": f"product={db_p.title[:80]}, source={db_p.source}",
                "t0": time.monotonic(),
            })
            est_output = _run_price_estimator(
                session, job_id, db_p, price_estimator_runner
            )
            _finalize_tool_run(
                session, job_id, _tool_timings[-1], est_output
            )
            create_price_estimate(
                session,
                product_id=db_p.id,
                estimated_value_usd=est_output.estimated_value_usd,
                discount_usd=est_output.discount_usd,
                deal_score=est_output.deal_score,
                confidence=est_output.confidence,
                model_breakdown=est_output.model_breakdown.model_dump(),
                warnings=est_output.warnings,
            )
            all_warnings.extend(est_output.warnings)
            result_products.append(
                {
                    "source": db_p.source,
                    "title": db_p.title,
                    "brand": db_p.brand,
                    "sale_price_usd": db_p.sale_price_usd,
                    "estimated_value_usd": est_output.estimated_value_usd,
                    "discount_usd": est_output.discount_usd,
                    "deal_score": est_output.deal_score,
                    "url": db_p.url,
                }
            )

        # Step 4: Build result payload.
        result = {
            "answer_vi": PLACEHOLDER_ANSWER_VI,
            "products": result_products,
            "warnings": all_warnings,
        }
        update_job_result(session, job, result)

        duration_ms = int((time.monotonic() - t0) * 1000)
        update_agent_run(
            session,
            worker_run,
            status="completed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            duration_ms=duration_ms,
            output_summary=f"{len(result_products)} products",
        )

        _log_event(
            "JOB_COMPLETED",
            job_id,
            duration_ms=duration_ms,
            product_count=len(result_products),
        )

        session.commit()

    except NotImplementedError:
        session.rollback()
        safe_error = (
            "Real search/model calls are not available in Phase 4A mock-only mode."
        )
        logger.exception("Worker NotImplementedError for job %s", job_id)
        try:
            _save_pipeline_failure(
                job_id, started_at, t0, safe_error, _tool_timings
            )
        except Exception:
            logger.exception("Failed to persist job failure for %s", job_id)
        _log_event("JOB_FAILED", job_id, reason="not_implemented")

    except Exception:
        session.rollback()
        safe_error = "Worker failed. Try again later."
        logger.exception("Worker internal failure for job %s", job_id)
        try:
            _save_pipeline_failure(
                job_id, started_at, t0, safe_error, _tool_timings
            )
        except Exception:
            logger.exception("Failed to persist job failure for %s", job_id)
        _log_event("JOB_FAILED", job_id)

    finally:
        session.close()


def _finalize_tool_run(
    session: Any,
    job_id: str,
    timing: dict[str, object],
    output: object,
) -> None:
    """Create a completed tool agent_run in the main session."""
    t0_val = float(timing["t0"])  # type: ignore[arg-type]
    duration_ms = int((time.monotonic() - t0_val) * 1000)
    component = str(timing["component"])
    input_summary = str(timing.get("input_summary", ""))

    if hasattr(output, "products"):
        output_summary = (
            f"{len(output.products)} products, "  # type: ignore[arg-type]
            f"{len(output.warnings)} warnings"  # type: ignore[arg-type]
        )
    else:
        output_summary = (
            f"estimated={output.estimated_value_usd}, "  # type: ignore[union-attr]
            f"discount={output.discount_usd}, "  # type: ignore[union-attr]
            f"score={output.deal_score}"  # type: ignore[union-attr]
        )

    run = create_agent_run(
        session,
        job_id=job_id,
        component=component,
        run_type="tool",
        status="completed",
        input_summary=input_summary[:500],
    )
    update_agent_run(
        session,
        run,
        status="completed",
        ended_at=datetime.datetime.now(datetime.timezone.utc),
        duration_ms=duration_ms,
        output_summary=output_summary[:500],
    )
    # Mark timing entry so _save_pipeline_failure can recreate the correct
    # status if a later tool fails and the main session is rolled back.
    timing["status"] = "completed"
    timing["output_summary"] = output_summary[:500]


def _save_pipeline_failure(
    job_id: str,
    started_at: datetime.datetime,
    t0: float,
    error_message: str,
    tool_timings: list[dict[str, object]],
) -> None:
    """Persist job failure AND all failed tool runs in a fresh session.

    Called after the main session has been rolled back, so there is no
    SQLite lock contention.
    """
    factory = get_session_factory()
    session = factory()
    try:
        job = get_job_by_id(session, job_id)
        if job is None:
            return
        update_job_error(session, job, error_message)
        now = datetime.datetime.now(datetime.timezone.utc)

        # Recreate tool runs with their true status.
        # Tools that completed before the failure are recreated as
        # completed; the active failing tool is recreated as failed.
        for timing in tool_timings:
            t0_val = float(timing["t0"])  # type: ignore[arg-type]
            duration_ms = int((time.monotonic() - t0_val) * 1000)
            component = str(timing["component"])
            input_summary = str(timing.get("input_summary", ""))
            was_completed = timing.get("status") == "completed"

            if was_completed:
                run = create_agent_run(
                    session,
                    job_id=job_id,
                    component=component,
                    run_type="tool",
                    status="completed",
                    input_summary=input_summary[:500],
                )
                update_agent_run(
                    session,
                    run,
                    status="completed",
                    ended_at=now,
                    duration_ms=duration_ms,
                    output_summary=str(timing.get("output_summary", "")),
                )
            else:
                run = create_agent_run(
                    session,
                    job_id=job_id,
                    component=component,
                    run_type="tool",
                    status="failed",
                    input_summary=input_summary[:500],
                )
                update_agent_run(
                    session,
                    run,
                    status="failed",
                    ended_at=now,
                    duration_ms=duration_ms,
                    error_message=f"{component} failed.",
                )

        # Create failed worker run.
        duration_ms = int((time.monotonic() - t0) * 1000)
        worker_fail_run = create_agent_run(
            session,
            job_id=job_id,
            component="worker",
            run_type="worker",
            status="failed",
            input_summary="Phase 4A pipeline",
        )
        update_agent_run(
            session,
            worker_fail_run,
            status="failed",
            ended_at=now,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
