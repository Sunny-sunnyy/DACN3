"""price_estimator_tool — deterministic mock estimation using JSON fixture lookup.

Phase 4A: fixed lookup + rule-based fallback. Real model calls (Phase 4C) gated
behind ENABLE_REAL_MODEL_CALLS, which raises NotImplementedError in this phase.
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
    """Estimate fair USD value for a product using fixture lookup or fallback rule.

    Args:
        input: PriceEstimateInput wrapping a ProductCandidate.

    Returns:
        PriceEstimateOutput with estimated value, discount, deal score, and breakdown.

    Raises:
        NotImplementedError: If ENABLE_REAL_MODEL_CALLS is True (Phase 4A mock-only).
    """
    if ENABLE_REAL_MODEL_CALLS:
        raise NotImplementedError(
            "Real model calls are not available in Phase 4A mock-only mode. "
            "Set ENABLE_REAL_MODEL_CALLS=false or wait for Phase 4C."
        )

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
