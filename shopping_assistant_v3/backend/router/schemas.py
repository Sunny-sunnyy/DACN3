"""Router schemas — Phase 5A deterministic-only.

Phase 5B will add an optional SDK provider behind the same RouterOutput contract.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class IntentEnum(str, Enum):
    SEARCH_DEALS = "search_deals"
    ESTIMATE_PRICE = "estimate_price"
    GENERAL_PRODUCT_QA = "general_product_qa"
    COMPARE = "compare"
    ADVISOR = "advisor"
    UNSUPPORTED = "unsupported"


class RouterInput(BaseModel):
    message_vi: str = Field(..., min_length=1, max_length=1000)
    conversation_context: list[dict] = Field(default_factory=list)


class RouterOutput(BaseModel):
    intent: IntentEnum
    query_en: str = ""
    source: Literal["All", "Amazon", "BestBuy"] = "All"
    max_results_per_source: int = 5
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    needs_tool: bool = True
