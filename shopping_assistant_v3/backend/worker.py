"""Local async job worker.

process_job(job_id) is called by FastAPI BackgroundTasks after POST /api/chat-jobs.
It runs in the same process, no separate worker or queue.

Lifecycle: pending -> running -> completed (or failed).
Idempotent: completed jobs return existing result; running/failed jobs are skipped.
All persistence goes through repository helpers. Structured JSON logs include job_id.

Phase 5A: deterministic Router + Synthesizer integrated into the pipeline.
Phase 4A _normalize_query() and PLACEHOLDER_ANSWER_VI have been removed.
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
from backend.shared.progress import build_progress_steps
from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput
from backend.tools.price_estimator.schemas import PriceEstimateInput, PriceEstimateOutput

logger = logging.getLogger("shopping_assistant_v3.worker")

DealSearchRunner = Callable[[DealSearchInput], DealSearchOutput]
PriceEstimatorRunner = Callable[[PriceEstimateInput], PriceEstimateOutput]


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

        # --- Start job ---
        update_job_status(session, job, "running", started_at=started_at)
        _log_event("JOB_STARTED", job_id)

        # Create worker-level audit record.
        worker_run = create_agent_run(
            session,
            job_id=job_id,
            component="worker",
            run_type="worker",
            status="started",
        )

        # --- Phase 5A pipeline ---

        # Step 1: Router — classify intent.
        from backend.router.deterministic import deterministic_route

        route_output = deterministic_route(message)
        _log_event(
            "ROUTER_COMPLETED",
            job_id,
            intent=route_output.intent.value,
            query_en=route_output.query_en,
            confidence=route_output.confidence,
        )
        router_audit = create_agent_run(
            session,
            job_id=job_id,
            component="router",
            run_type="router",
            status="started",
            input_summary=f"message_vi={message[:200]}",
        )
        update_agent_run(
            session,
            router_audit,
            status="completed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            output_summary=(
                f"intent={route_output.intent.value}, "
                f"query_en={route_output.query_en[:100]}, "
                f"confidence={route_output.confidence}"
            ),
        )
        # Track router completion so _save_pipeline_failure can recreate it
        # when a later tool fails and the main session is rolled back.
        _tool_timings.append({
            "component": "router",
            "run_type": "router",
            "input_summary": f"message_vi={message[:200]}",
            "t0": time.monotonic(),
        })
        _tool_timings[-1]["status"] = "completed"
        _tool_timings[-1]["output_summary"] = (
            f"intent={route_output.intent.value}, "
            f"query_en={route_output.query_en[:100]}"
        )

        if not route_output.needs_tool or route_output.intent.value == "unsupported":
            # --- Unsupported path ---
            from backend.synthesizer.deterministic import deterministic_synthesize
            from backend.synthesizer.schemas import SynthesizerInput

            synth_input = SynthesizerInput(
                message_vi=message,
                intent=route_output.intent.value,
                products=[],
                price_estimates=[],
                warnings=[],
            )
            synth_output = deterministic_synthesize(synth_input)

            # Synthesizer audit
            synth_audit = create_agent_run(
                session,
                job_id=job_id,
                component="synthesizer",
                run_type="synthesizer",
                status="started",
                input_summary=(
                    f"intent={route_output.intent.value}, "
                    f"products=0, warnings=0"
                ),
            )
            update_agent_run(
                session,
                synth_audit,
                status="completed",
                ended_at=datetime.datetime.now(datetime.timezone.utc),
                output_summary=f"answer_vi={synth_output.answer_vi[:200]}",
            )

            progress_steps = build_progress_steps(
                route_completed=True,
                search_skipped=True,
                pricing_skipped=True,
                synth_completed=True,
                route_detail=(
                    f"Da xac dinh yeu cau: {route_output.intent.value}."
                    if route_output.intent.value != "unsupported"
                    else "Yeu cau chua duoc ho tro. Vui long thu tim san pham cu the."
                ),
                synth_detail="Da tao cau tra loi cho ban.",
            )

            result = {
                "answer_vi": synth_output.answer_vi,
                "products": [],
                "warnings": [],
                "summary_cards": [],
                "progress_steps": [s.model_dump() for s in progress_steps],
            }
            update_job_result(session, job, result)

            duration_ms = int((time.monotonic() - t0) * 1000)
            update_agent_run(
                session,
                worker_run,
                status="completed",
                ended_at=datetime.datetime.now(datetime.timezone.utc),
                duration_ms=duration_ms,
                output_summary="unsupported intent — safe fallback",
            )

            _log_event("JOB_COMPLETED", job_id, duration_ms=duration_ms, product_count=0)
            session.commit()
            return

        # --- Supported path (search_deals) ---

        query_en = route_output.query_en or message
        source = route_output.source if route_output.source != "All" else source
        max_results = route_output.max_results_per_source

        # Step 2: Deal search.
        _tool_timings.append({
            "component": "deal_search_tool",
            "run_type": "tool",
            "input_summary": f"query_en={query_en}, source={source}",
            "t0": time.monotonic(),
        })
        search_output = _run_deal_search(
            session, job_id, query_en, source, max_results, deal_search_runner
        )
        _finalize_tool_run(
            session, job_id, _tool_timings[-1], search_output
        )

        # Step 3: Persist products.
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

        # Step 4: Estimate prices per product.
        result_products: list[dict[str, Any]] = []
        price_estimates: list[PriceEstimateOutput] = []
        for db_p in db_products:
            _tool_timings.append({
                "component": "price_estimator_tool",
                "run_type": "tool",
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
            price_estimates.append(est_output)
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

        # Step 5: Synthesizer — Vietnamese answer from evidence.
        from backend.synthesizer.deterministic import deterministic_synthesize
        from backend.synthesizer.schemas import SynthesizerInput
        from backend.tools.deal_search.schemas import ProductCandidate as PC

        synth_products = [
            PC(
                source=db_p.source,
                title=db_p.title,
                brand=db_p.brand,
                sale_price_usd=db_p.sale_price_usd,
                url=db_p.url,
                features=db_p.features,
            )
            for db_p in db_products
        ]
        synth_input = SynthesizerInput(
            message_vi=message,
            intent=route_output.intent.value,
            products=synth_products,
            price_estimates=price_estimates,
            warnings=all_warnings,
        )
        synth_output = deterministic_synthesize(synth_input)

        synth_audit = create_agent_run(
            session,
            job_id=job_id,
            component="synthesizer",
            run_type="synthesizer",
            status="started",
            input_summary=(
                f"intent={route_output.intent.value}, "
                f"products={len(synth_products)}, "
                f"warnings={len(all_warnings)}"
            ),
        )
        update_agent_run(
            session,
            synth_audit,
            status="completed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            output_summary=f"answer_vi={synth_output.answer_vi[:200]}",
        )

        # Step 6: Build progress_steps.
        search_detail = (
            f"Da tim thay {len(search_output.products)} san pham phu hop."
            if search_output.products
            else "Khong tim thay san pham nao."
        )
        pricing_detail = (
            f"Da uoc tinh gia tri cho {len(price_estimates)} san pham."
            if price_estimates
            else "Khong co san pham de uoc tinh gia."
        )
        progress_steps = build_progress_steps(
            route_completed=True,
            search_completed=True,
            pricing_completed=bool(price_estimates),
            synth_completed=True,
            route_detail=f"Da xac dinh yeu cau: tim san pham.",
            search_detail=search_detail,
            pricing_detail=pricing_detail,
            synth_detail="Da tong hop ket qua cho ban.",
        )

        # Step 7: Build result payload.
        result = {
            "answer_vi": synth_output.answer_vi,
            "products": result_products,
            "warnings": all_warnings,
            "summary_cards": [c.model_dump() for c in synth_output.summary_cards],
            "progress_steps": [s.model_dump() for s in progress_steps],
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

        # Recreate component runs with their true status.
        # Components that completed before the failure are recreated as
        # completed; the active failing component is recreated as failed.
        # Phase 5A: router entries use run_type from timing dict, not
        # hardcoded "tool".
        for timing in tool_timings:
            t0_val = float(timing["t0"])  # type: ignore[arg-type]
            duration_ms = int((time.monotonic() - t0_val) * 1000)
            component = str(timing["component"])
            run_type = str(timing.get("run_type", "tool"))
            input_summary = str(timing.get("input_summary", ""))
            was_completed = timing.get("status") == "completed"

            if was_completed:
                run = create_agent_run(
                    session,
                    job_id=job_id,
                    component=component,
                    run_type=run_type,
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
                    run_type=run_type,
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
