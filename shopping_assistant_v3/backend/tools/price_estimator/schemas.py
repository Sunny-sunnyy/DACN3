"""Pydantic schemas for price_estimator_tool matching agent_architecture.md contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.tools.deal_search.schemas import ProductCandidate


class PriceEstimateInput(BaseModel):
    product: ProductCandidate


class ModelBreakdown(BaseModel):
    frontier: float
    specialist: float
    neural: float


class PriceEstimateOutput(BaseModel):
    estimated_value_usd: float
    discount_usd: float
    deal_score: Literal["hot", "good", "ok", "overpriced"]
    confidence: float | None = None
    model_breakdown: ModelBreakdown
    warnings: list[str] = Field(default_factory=list)
