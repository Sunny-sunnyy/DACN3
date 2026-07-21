"""Synthesizer schemas — Phase 5A deterministic-only.

Phase 5B will add an optional SDK provider behind the same SynthesizerOutput contract.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.schemas import PriceEstimateOutput


class SummaryCard(BaseModel):
    source: str
    title: str
    sale_price_usd: float | None = None
    estimated_value_usd: float | None = None
    discount_usd: float | None = None
    deal_score: str | None = None
    url: str | None = None
    highlight_vi: str = ""


class SynthesizerInput(BaseModel):
    message_vi: str
    intent: str
    products: list[ProductCandidate] = Field(default_factory=list)
    price_estimates: list[PriceEstimateOutput] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SynthesizerOutput(BaseModel):
    answer_vi: str
    summary_cards: list[SummaryCard] = Field(default_factory=list)
    warnings_vi: list[str] = Field(default_factory=list)
