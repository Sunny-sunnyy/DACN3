"""Deterministic progress steps for the fixed shopping pipeline.

Phase 5A: progress_steps are computed by the worker during job processing
and persisted in job.result_payload. They are NOT stored in a separate
table or DB column.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProgressStep(BaseModel):
    step_id: str
    title_vi: str
    status: StepStatus
    detail_vi: str


# Fixed shopping pipeline — always 4 steps in this order.
PROGRESS_STEPS_TEMPLATE: list[dict[str, str]] = [
    {"step_id": "route_request",     "title_vi": "Hiểu nhu cầu mua sắm"},
    {"step_id": "search_deals",      "title_vi": "Tìm sản phẩm từ Amazon và BestBuy"},
    {"step_id": "estimate_prices",   "title_vi": "Ước tính giá trị thực"},
    {"step_id": "synthesize_answer", "title_vi": "Tổng hợp kết quả"},
]


def build_progress_steps(
    route_completed: bool = False,
    search_completed: bool = False,
    search_skipped: bool = False,
    pricing_completed: bool = False,
    pricing_skipped: bool = False,
    synth_completed: bool = False,
    route_detail: str = "",
    search_detail: str = "",
    pricing_detail: str = "",
    synth_detail: str = "",
) -> list[ProgressStep]:
    """Build a deterministic progress_steps list from pipeline state.

    Only one of (completed, skipped) should be True per step except for
    the starting state where both are False (pending/running).
    """
    steps: list[ProgressStep] = []

    # Step 1: route_request
    if route_completed:
        steps.append(ProgressStep(
            step_id="route_request",
            title_vi="Hiểu nhu cầu mua sắm",
            status=StepStatus.COMPLETED,
            detail_vi=route_detail or "Đã xác định yêu cầu và tạo truy vấn tìm kiếm.",
        ))
    else:
        steps.append(ProgressStep(
            step_id="route_request",
            title_vi="Hiểu nhu cầu mua sắm",
            status=StepStatus.RUNNING,
            detail_vi="Đang phân tích yêu cầu của bạn.",
        ))

    # Step 2: search_deals
    if search_skipped:
        steps.append(ProgressStep(
            step_id="search_deals",
            title_vi="Tìm sản phẩm từ Amazon và BestBuy",
            status=StepStatus.SKIPPED,
            detail_vi="Tìm kiếm không cần thiết cho yêu cầu này.",
        ))
    elif search_completed:
        steps.append(ProgressStep(
            step_id="search_deals",
            title_vi="Tìm sản phẩm từ Amazon và BestBuy",
            status=StepStatus.COMPLETED,
            detail_vi=search_detail or "Đã tìm thấy sản phẩm phù hợp.",
        ))
    else:
        steps.append(ProgressStep(
            step_id="search_deals",
            title_vi="Tìm sản phẩm từ Amazon và BestBuy",
            status=StepStatus.PENDING,
            detail_vi="Đang chờ tìm kiếm sản phẩm.",
        ))

    # Step 3: estimate_prices
    if pricing_skipped:
        steps.append(ProgressStep(
            step_id="estimate_prices",
            title_vi="Ước tính giá trị thực",
            status=StepStatus.SKIPPED,
            detail_vi="Ước tính giá không cần thiết cho yêu cầu này.",
        ))
    elif pricing_completed:
        steps.append(ProgressStep(
            step_id="estimate_prices",
            title_vi="Ước tính giá trị thực",
            status=StepStatus.COMPLETED,
            detail_vi=pricing_detail or "Đã ước tính giá trị cho các sản phẩm.",
        ))
    else:
        steps.append(ProgressStep(
            step_id="estimate_prices",
            title_vi="Ước tính giá trị thực",
            status=StepStatus.PENDING,
            detail_vi="Đang chờ ước tính giá.",
        ))

    # Step 4: synthesize_answer
    if synth_completed:
        steps.append(ProgressStep(
            step_id="synthesize_answer",
            title_vi="Tổng hợp kết quả",
            status=StepStatus.COMPLETED,
            detail_vi=synth_detail or "Đã tổng hợp kết quả cho bạn.",
        ))
    else:
        steps.append(ProgressStep(
            step_id="synthesize_answer",
            title_vi="Tổng hợp kết quả",
            status=StepStatus.PENDING,
            detail_vi="Đang chờ tổng hợp kết quả.",
        ))

    return steps
