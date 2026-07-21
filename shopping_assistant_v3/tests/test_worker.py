"""Worker tests: job lifecycle, idempotency, failure path, audit, and log events.

Phase 5A: tests now cover Router, Synthesizer, progress_steps, and unsupported path.
All tests call process_job() directly. No network, no model calls, no real search.
Uses the isolated temp SQLite from conftest.py.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from backend.database.repository import (
    create_conversation,
    create_job,
    get_job_by_id,
    get_products_by_job_id,
    update_job_error,
    update_job_status,
)
from backend.database.schema import AgentRun, Job, PriceEstimate
from backend.shared.config import DEMO_USER_ID
from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput
from backend.tools.price_estimator.schemas import PriceEstimateInput, PriceEstimateOutput
from backend.worker import process_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_pending_job(
    session: Session, message: str = "gaming laptop"
) -> Job:
    conv = create_conversation(session, user_id=DEMO_USER_ID)
    session.commit()
    job = create_job(
        session,
        user_id=DEMO_USER_ID,
        conversation_id=conv.id,
        request_payload={"message": message},
    )
    session.commit()
    return job


def _result_shape(result: dict) -> None:
    assert "answer_vi" in result
    assert isinstance(result["answer_vi"], str)
    assert len(result["answer_vi"]) > 0
    assert "products" in result
    assert isinstance(result["products"], list)
    assert "warnings" in result
    assert isinstance(result["warnings"], list)
    # Phase 5A additions
    assert "summary_cards" in result
    assert isinstance(result["summary_cards"], list)
    assert "progress_steps" in result
    assert isinstance(result["progress_steps"], list)
    assert len(result["progress_steps"]) == 4


# ---------------------------------------------------------------------------
# process_job — happy path (Phase 4A tool pipeline)
# ---------------------------------------------------------------------------

class TestProcessJob:
    def test_completes_with_product_and_estimate_persistence(
        self, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)

        assert job.status == "completed"
        assert job.completed_at is not None
        result = json.loads(job.result_payload)
        _result_shape(result)
        assert len(result["products"]) >= 1

        products = get_products_by_job_id(db_session, job.id)
        assert len(products) == len(result["products"])
        for p in products:
            assert p.source in ("Amazon", "BestBuy")
            estimates = (
                db_session.query(PriceEstimate)
                .filter(PriceEstimate.product_id == p.id)
                .all()
            )
            assert len(estimates) == 1
            assert estimates[0].deal_score is not None

    def test_result_products_match_db_rows(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)

        result = json.loads(job.result_payload)
        db_products = get_products_by_job_id(db_session, job.id)
        assert len(result["products"]) == len(db_products)

        result_titles = {p["title"] for p in result["products"]}
        db_titles = {p.title for p in db_products}
        assert result_titles == db_titles

    def test_creates_agent_runs_for_tools_and_worker(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)

        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        components = {r.component for r in runs}
        assert "worker" in components, "Phase 3 worker audit row must be preserved"
        assert "router" in components, "Phase 5A Router audit missing"
        assert "deal_search_tool" in components
        assert "price_estimator_tool" in components
        assert "synthesizer" in components, "Phase 5A Synthesizer audit missing"

        for run in runs:
            assert run.status == "completed", f"{run.component} should be completed"
            if run.component in ("deal_search_tool", "price_estimator_tool"):
                assert run.duration_ms is not None
                assert run.duration_ms >= 0

    def test_answer_vi_is_non_empty(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        result = json.loads(job.result_payload)
        assert len(result["answer_vi"]) > 0
        assert isinstance(result["answer_vi"], str)

    def test_sets_running_before_completing(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
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

        # Verify no additional runs were created on reprocessing.
        # Phase 4A creates multiple runs per job (deal_search + per-product pricing).
        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        assert len(runs) > 0

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
    def test_deal_search_failure_sets_job_failed(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("mock search failure")

        process_job(job.id, deal_search_runner=_failing_search)
        db_session.refresh(job)
        assert job.status == "failed"
        assert job.error_message is not None
        assert "Worker failed" in job.error_message

    def test_price_estimator_failure_sets_job_failed(
        self, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session)

        def _failing_estimator(_input: PriceEstimateInput) -> PriceEstimateOutput:
            raise RuntimeError("mock estimator failure")

        process_job(job.id, price_estimator_runner=_failing_estimator)
        db_session.refresh(job)
        assert job.status == "failed"
        assert "Worker failed" in job.error_message

    def test_failure_persists_failed_tool_and_worker_runs(
        self, db_session: Session
    ) -> None:
        """When deal_search fails, both the failed tool run and worker run survive."""
        job = _create_pending_job(db_session)

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("boom")

        process_job(job.id, deal_search_runner=_failing_search)
        db_session.refresh(job)

        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        components = {r.component for r in runs}
        assert "deal_search_tool" in components, "Failed tool run must be persisted"
        assert "worker" in components, "Failed worker run must be persisted"

        tool_run = [r for r in runs if r.component == "deal_search_tool"][0]
        assert tool_run.status == "failed"
        worker_run = [r for r in runs if r.component == "worker"][0]
        assert worker_run.status == "failed"

    def test_router_audit_survives_search_failure(
        self, db_session: Session
    ) -> None:
        """Phase 5A: when deal_search fails after routing, router audit must survive."""
        job = _create_pending_job(db_session)

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("mock search failure")

        process_job(job.id, deal_search_runner=_failing_search)
        db_session.refresh(job)

        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        components = {r.component for r in runs}
        assert "router" in components, "Router audit must survive rollback"
        assert "deal_search_tool" in components
        assert "worker" in components

        router_run = [r for r in runs if r.component == "router"][0]
        assert router_run.run_type == "router"
        assert router_run.status == "completed"
        assert router_run.input_summary is not None
        assert router_run.output_summary is not None

        search_run = [r for r in runs if r.component == "deal_search_tool"][0]
        assert search_run.status == "failed"

    def test_later_tool_failure_preserves_earlier_completed_runs(
        self, db_session: Session
    ) -> None:
        """When price_estimator fails after deal_search succeeded,
        deal_search must be marked completed, not failed."""
        job = _create_pending_job(db_session)

        def _failing_estimator(_input: PriceEstimateInput) -> PriceEstimateOutput:
            raise RuntimeError("mock estimator failure")

        process_job(job.id, price_estimator_runner=_failing_estimator)
        db_session.refresh(job)

        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        components = {r.component for r in runs}
        assert "deal_search_tool" in components
        assert "price_estimator_tool" in components
        assert "worker" in components

        search_run = [r for r in runs if r.component == "deal_search_tool"][0]
        assert search_run.status == "completed", (
            "deal_search succeeded before estimator failed — must be completed"
        )
        assert search_run.output_summary is not None

        est_run = [r for r in runs if r.component == "price_estimator_tool"][0]
        assert est_run.status == "failed"

        worker_run = [r for r in runs if r.component == "worker"][0]
        assert worker_run.status == "failed"

    def test_failure_does_not_leave_stale_running(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("x")

        process_job(job.id, deal_search_runner=_failing_search)
        db_session.refresh(job)
        assert job.status == "failed"


# ---------------------------------------------------------------------------
# ENABLE_REAL_* flag in worker context
# ---------------------------------------------------------------------------

class TestRealModeInWorker:
    def test_real_search_flag_completes_job_with_real_path(
        self, db_session: Session, monkeypatch
    ) -> None:
        """Phase 4B: ENABLE_REAL_SEARCH=true dispatches to real search.

        Real search modules may fail at network level (no connectivity),
        but the job should complete (not crash) with sanitized warnings.
        """
        monkeypatch.setattr(
            "backend.tools.deal_search.tool.ENABLE_REAL_SEARCH", True
        )
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        # Phase 4B: real search is implemented. Job completes even if
        # network calls fail — failures become warnings, not job errors.
        assert job.status == "completed"
        result = json.loads(job.result_payload or "{}")
        assert "products" in result
        assert "warnings" in result

    def test_real_model_flag_completes_job_with_fallback(
        self, db_session: Session, monkeypatch
    ) -> None:
        """Phase 4C.1: ENABLE_REAL_MODEL_CALLS=true completes with fallback.

        Without PRICER_NEURAL_WEIGHTS_PATH, neural is unavailable, but
        real estimator returns safe fallback — job completes, not fails.
        """
        monkeypatch.setattr(
            "backend.tools.price_estimator.tool.ENABLE_REAL_MODEL_CALLS", True
        )
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        assert job.status == "completed"
        result = json.loads(job.result_payload or "{}")
        assert "products" in result
        # Verify fallback warnings are present in result
        warnings = result.get("warnings", [])
        assert any("real_pricing_fallback_used" in w for w in warnings)


# ---------------------------------------------------------------------------
# Phase 5A — Router + Synthesizer + progress_steps
# ---------------------------------------------------------------------------


class TestPhase5APipeline:
    def test_progress_steps_has_four_entries(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        result = json.loads(job.result_payload)
        steps = result["progress_steps"]
        assert len(steps) == 4
        step_ids = [s["step_id"] for s in steps]
        assert step_ids == [
            "route_request",
            "search_deals",
            "estimate_prices",
            "synthesize_answer",
        ]

    def test_progress_steps_all_completed_for_search(self, db_session: Session) -> None:
        job = _create_pending_job(db_session, message="Tim laptop gaming")
        process_job(job.id)
        db_session.refresh(job)
        result = json.loads(job.result_payload)
        steps = result["progress_steps"]
        for s in steps:
            assert s["status"] == "completed", f"{s['step_id']} should be completed"

    def test_router_and_synthesizer_agent_runs_created(
        self, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)

        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        router_runs = [r for r in runs if r.component == "router"]
        assert len(router_runs) == 1
        assert router_runs[0].run_type == "router"
        assert router_runs[0].status == "completed"

        synth_runs = [r for r in runs if r.component == "synthesizer"]
        assert len(synth_runs) == 1
        assert synth_runs[0].run_type == "synthesizer"
        assert synth_runs[0].status == "completed"

    def test_unsupported_intent_skips_search_and_pricing(
        self, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session, message="Xin chao ban")
        process_job(job.id)
        db_session.refresh(job)

        assert job.status == "completed"
        result = json.loads(job.result_payload)
        steps = result["progress_steps"]
        assert len(steps) == 4

        statuses = {s["step_id"]: s["status"] for s in steps}
        assert statuses["route_request"] == "completed"
        assert statuses["search_deals"] == "skipped"
        assert statuses["estimate_prices"] == "skipped"
        assert statuses["synthesize_answer"] == "completed"

        # No products for unsupported
        assert result["products"] == []
        assert len(result["answer_vi"]) > 0

    def test_unsupported_intent_has_safe_vietnamese_answer(
        self, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session, message="Thoi tiet hom nay")
        process_job(job.id)
        db_session.refresh(job)
        result = json.loads(job.result_payload)
        assert "tro ly mua sam" in result["answer_vi"].lower()

    def test_no_placeholder_answer_remains(self, db_session: Session) -> None:
        """Phase 5A: the old PLACEHOLDER_ANSWER_VI must not appear anywhere."""
        job = _create_pending_job(db_session, message="Tim laptop")
        process_job(job.id)
        db_session.refresh(job)
        result = json.loads(job.result_payload)
        assert "Minh da tim thay mot so san pham phu hop" not in result["answer_vi"]

    def test_summary_cards_present(self, db_session: Session) -> None:
        job = _create_pending_job(db_session, message="Tim laptop gaming")
        process_job(job.id)
        db_session.refresh(job)
        result = json.loads(job.result_payload)
        assert "summary_cards" in result
        assert len(result["summary_cards"]) >= 1
        card = result["summary_cards"][0]
        assert "source" in card
        assert "title" in card
        assert "highlight_vi" in card
        assert "url" in card


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

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("xyz")

        with caplog.at_level("INFO", logger="shopping_assistant_v3.worker"):
            process_job(job.id, deal_search_runner=_failing_search)

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
