"""Real price estimator orchestrator — Phase 4C.1.

Assembles PriceEstimateOutput from available components:
  - Neural adapter (via PRICER_NEURAL_WEIGHTS_PATH).
Deferred: Frontier (4C.2), Specialist (4C.3).

Mock path is in tool.py; this module is only reached when
ENABLE_REAL_MODEL_CALLS=true.
"""

from __future__ import annotations

import logging

from backend.shared.config import PRICER_NEURAL_WEIGHTS_PATH
from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.formatter import format_product_for_pricing
from backend.tools.price_estimator.neural.adapter import (
    NeuralEstimateResult,
    NeuralPriceAdapter,
)
from backend.tools.price_estimator.schemas import (
    ModelBreakdown,
    PriceEstimateOutput,
)

logger = logging.getLogger("shopping_assistant_v3.real_estimator")

# ── warning grammar (key:value, no space after colon) ──────────────────
_WARN_FRONTIER = "frontier_unavailable:deferred_to_4c2"
_WARN_SPECIALIST = "specialist_unavailable:deferred_to_4c3"
_WARN_ENSEMBLE_NEURAL = "ensemble_partial:neural_only"
_WARN_ENSEMBLE_FALLBACK = "ensemble_partial:fallback_only"
_WARN_FALLBACK_USED = "real_pricing_fallback_used:sale_price_markup"


def _compute_deal_score(sale_price_usd: float, estimated_value_usd: float) -> str:
    discount = estimated_value_usd - sale_price_usd
    if discount >= 200:
        return "hot"
    if discount >= 100:
        return "good"
    if discount > 0:
        return "ok"
    return "overpriced"


def _assemble_output(
    product: ProductCandidate,
    neural_result: NeuralEstimateResult,
) -> PriceEstimateOutput:
    """Pure function: assemble PriceEstimateOutput from neural result + product.

    Testable without any neural deps — just pass a real or fake NeuralEstimateResult.
    """
    sale_price = product.sale_price_usd or 0.0
    warnings: list[str] = [
        _WARN_FRONTIER,
        _WARN_SPECIALIST,
    ]

    if neural_result.available and neural_result.value_usd is not None:
        estimated_value = neural_result.value_usd
        neural_breakdown = neural_result.value_usd
        warnings.append(_WARN_ENSEMBLE_NEURAL)
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)
    else:
        # Safe fallback: 5% markup (intentionally different from mock 10%).
        # Fallback path always scores "ok" — not enough evidence for hot/good.
        estimated_value = round(sale_price * 1.05, 2)
        neural_breakdown = 0.0
        discount = round(estimated_value - sale_price, 2)
        deal_score = "ok"
        # Neural-specific warning
        if neural_result.error_code:
            warnings.append(f"neural_unavailable:{neural_result.error_code}")
        warnings.append(_WARN_FALLBACK_USED)
        warnings.append(_WARN_ENSEMBLE_FALLBACK)

    return PriceEstimateOutput(
        estimated_value_usd=estimated_value,
        discount_usd=discount,
        deal_score=deal_score,
        confidence=None,
        model_breakdown=ModelBreakdown(
            frontier=0.0,
            specialist=0.0,
            neural=neural_breakdown,
        ),
        warnings=warnings,
    )


def estimate_price_real(product: ProductCandidate) -> PriceEstimateOutput:
    """Real price estimation using available components.

    Current available (4C.1): neural via PRICER_NEURAL_WEIGHTS_PATH.
    Deferred: frontier (4C.2), specialist (4C.3).

    Never raises — all failure paths produce valid PriceEstimateOutput
    with explicit warnings.
    """
    # Format product description
    text = format_product_for_pricing(product)

    # Run neural adapter (lazy-loads on first call)
    adapter = NeuralPriceAdapter(weights_path=PRICER_NEURAL_WEIGHTS_PATH)
    neural_result = adapter.estimate(text)

    logger.debug(
        "Real estimator: neural available=%s value=%s error=%s",
        neural_result.available,
        neural_result.value_usd,
        neural_result.error_code,
    )

    return _assemble_output(product, neural_result)
