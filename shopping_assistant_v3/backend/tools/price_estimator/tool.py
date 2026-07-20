"""price_estimator_tool — deterministic mock estimation using JSON fixture lookup.

Phase 4A: fixed lookup + rule-based fallback.
Phase 4C.2: real path dispatched to real_estimator when ENABLE_REAL_MODEL_CALLS=true.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.shared.config import ENABLE_REAL_MODEL_CALLS
from backend.tools.price_estimator.schemas import (
    ModelBreakdown,
    PriceEstimateInput,
    PriceEstimateOutput,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mock_estimates.json"


def _load_estimates() -> dict[str, dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _compute_deal_score(sale_price_usd: float, estimated_value_usd: float) -> str:
    discount = estimated_value_usd - sale_price_usd
    if discount >= 200:
        return "hot"
    if discount >= 100:
        return "good"
    if discount > 0:
        return "ok"
    return "overpriced"


def _fallback_estimate(sale_price: float) -> tuple[float, ModelBreakdown]:
    """Simple deterministic fallback: 10% markup, all models equal.

    Phase 4A uses a fixed 10% markup rule. model_breakdown values are all
    equal to the estimated value since no real model distinction exists.
    """
    estimated = round(sale_price * 1.10, 2)
    breakdown = ModelBreakdown(
        frontier=estimated,
        specialist=estimated,
        neural=estimated,
    )
    return estimated, breakdown


def estimate_price(input: PriceEstimateInput) -> PriceEstimateOutput:
    """Estimate fair USD value for a product.

    When ENABLE_REAL_MODEL_CALLS=false (default): fixture lookup with
    deterministic 10% markup fallback rule.

    When ENABLE_REAL_MODEL_CALLS=true (Phase 4C.2): dispatches to
    real_estimator, which tries Frontier first, falls back to Neural,
    then uses safe fallback markup with explicit component warnings.

    Args:
        input: PriceEstimateInput wrapping a ProductCandidate.

    Returns:
        PriceEstimateOutput with estimated value, discount, deal score,
        model breakdown, and warnings.
    """
    if ENABLE_REAL_MODEL_CALLS:
        # Imported inline so mock path never touches real pricing deps.
        from backend.tools.price_estimator.real_estimator import estimate_price_real
        return estimate_price_real(input.product)

    product = input.product
    sale_price = product.sale_price_usd or 0.0
    lookup_key = f"{product.source}|{product.title}"
    estimates = _load_estimates()
    warnings: list[str] = []

    if lookup_key in estimates:
        entry = estimates[lookup_key]
        estimated_value = entry["estimated_value_usd"]
        breakdown = ModelBreakdown(**entry["model_breakdown"])
    else:
        estimated_value, breakdown = _fallback_estimate(sale_price)
        warnings.append("Price estimate from fallback rule — not in fixture lookup.")

    discount = round(estimated_value - sale_price, 2)
    deal_score = _compute_deal_score(sale_price, estimated_value)

    return PriceEstimateOutput(
        estimated_value_usd=estimated_value,
        discount_usd=discount,
        deal_score=deal_score,
        confidence=None,
        model_breakdown=breakdown,
        warnings=warnings,
    )
