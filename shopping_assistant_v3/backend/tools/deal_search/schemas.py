"""Pydantic schemas for deal_search_tool matching agent_architecture.md contract."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DealSearchInput(BaseModel):
    query_en: str = Field(..., min_length=1, description="English search query")
    source: Literal["All", "Amazon", "BestBuy"] = "All"
    max_results_per_source: int = Field(default=5, ge=1, le=20)


class ProductCandidate(BaseModel):
    source: Literal["Amazon", "BestBuy"]
    title: str
    brand: str | None = None
    sale_price_usd: float | None = None
    url: str | None = None
    features: str | None = None
    raw_source_payload: dict[str, Any] = Field(default_factory=dict)


class DealSearchOutput(BaseModel):
    products: list[ProductCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
