"""Pydantic request/response schemas matching the architecture guide API contract."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class SourceEnum(str, Enum):
    All = "All"
    Amazon = "Amazon"
    BestBuy = "BestBuy"


class ChatJobRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=1000)
    conversation_id: str | None = Field(default=None)
    source: SourceEnum = Field(default=SourceEnum.All)
    max_results_per_source: int = Field(default=5, ge=1, le=20)


# ---------------------------------------------------------------------------
# Response: create job
# ---------------------------------------------------------------------------

class ChatJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# Response: get job status
# ---------------------------------------------------------------------------

class ProductResult(BaseModel):
    source: str
    title: str
    brand: str | None = None
    sale_price_usd: float | None = None
    estimated_value_usd: float | None = None
    discount_usd: float | None = None
    deal_score: str | None = None
    url: str | None = None


class ChatJobResult(BaseModel):
    answer_vi: str
    products: list[ProductResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime.datetime | None = None
    started_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None
    result: ChatJobResult | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Error shape
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[Any] = Field(default_factory=list)
