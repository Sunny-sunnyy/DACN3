"""Real price estimator orchestrator — Phase 4C.2.

Assembles PriceEstimateOutput from available components:
  - Frontier adapter (via PRICER_CHROMADB_PATH + PRICER_FRONTIER_MODEL_ID) — Phase 4C.2.
  - Neural adapter (via PRICER_NEURAL_WEIGHTS_PATH) — Phase 4C.1.
Deferred: Specialist (4C.3).

Mock path is in tool.py; this module is only reached when
ENABLE_REAL_MODEL_CALLS=true.

Priority: frontier > neural > fallback 5% markup.
Frontier short-circuits neural when available.
"""

from __future__ import annotations

import logging

from backend.shared.config import (
    PRICER_CHROMADB_PATH,
    PRICER_FRONTIER_MODEL_ID,
    PRICER_NEURAL_WEIGHTS_PATH,
)
from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.formatter import format_product_for_pricing
from backend.tools.price_estimator.frontier.adapter import (
    FrontierEstimateResult,
    FrontierPriceAdapter,
)
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
_WARN_SPECIALIST = "specialist_unavailable:deferred_to_4c3"
_WARN_ENSEMBLE_FRONTIER = "ensemble_partial:frontier_only"
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
    frontier_result: FrontierEstimateResult,
    neural_result: NeuralEstimateResult,
) -> PriceEstimateOutput:
    """Pure function: assemble PriceEstimateOutput with frontier > neural > fallback.

    Priority:
      1. Frontier available → use frontier_value directly (dominant model, 80% weight).
      2. Frontier unavailable, neural available → use neural_value (4C.1 behavior).
      3. Neither available → 5% markup fallback.

    Testable without any heavy deps — just pass real or fake result objects.
    """
    sale_price = product.sale_price_usd or 0.0
    warnings: list[str] = [_WARN_SPECIALIST]

    frontier_value = 0.0
    neural_value = 0.0

    # ── Priority 1: Frontier ──
    if frontier_result.available and frontier_result.value_usd is not None:
        estimated_value = frontier_result.value_usd
        frontier_value = frontier_result.value_usd
        warnings.append(_WARN_ENSEMBLE_FRONTIER)
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)

    # ── Priority 2: Neural (frontier unavailable) ──
    elif neural_result.available and neural_result.value_usd is not None:
        estimated_value = neural_result.value_usd
        neural_value = neural_result.value_usd
        if frontier_result.error_code:
            warnings.append(f"frontier_unavailable:{frontier_result.error_code}")
        warnings.append(_WARN_ENSEMBLE_NEURAL)
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)

    # ── Priority 3: Fallback ──
    else:
        estimated_value = round(sale_price * 1.05, 2)
        discount = round(estimated_value - sale_price, 2)
        deal_score = "ok"

        if frontier_result.error_code:
            warnings.append(f"frontier_unavailable:{frontier_result.error_code}")
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
            frontier=frontier_value,
            specialist=0.0,
            neural=neural_value,
        ),
        warnings=warnings,
    )


def estimate_price_real(product: ProductCandidate) -> PriceEstimateOutput:
    """Real price estimation using available components.

    Current available:
      - Frontier (4C.2): GPT + ChromaDB RAG via PRICER_CHROMADB_PATH
      - Neural (4C.1): PyTorch DNN via PRICER_NEURAL_WEIGHTS_PATH
    Deferred: Specialist (4C.3).

    Short-circuits: if frontier succeeds, neural is skipped entirely.
    This makes ensemble_partial:frontier_only accurate and avoids
    unnecessary neural deps loading. If frontier fails, falls back
    to neural, then to 5% markup.

    Never raises — all failure paths produce valid PriceEstimateOutput
    with explicit warnings.
    """
    text = format_product_for_pricing(product)

    # Run frontier adapter (lazy-loads on first call)
    frontier_adapter = FrontierPriceAdapter(
        chromadb_path=PRICER_CHROMADB_PATH,
        model_id=PRICER_FRONTIER_MODEL_ID,
    )
    frontier_result = frontier_adapter.try_estimate(text)

    logger.debug(
        "Real estimator: frontier available=%s value=%s error=%s",
        frontier_result.available,
        frontier_result.value_usd,
        frontier_result.error_code,
    )

    # Short-circuit: if frontier available, skip neural entirely.
    if frontier_result.available:
        neural_result = NeuralEstimateResult(
            available=False, error_code="skipped_frontier_available"
        )
    else:
        # Run neural adapter (lazy-loads on first call)
        neural_adapter = NeuralPriceAdapter(weights_path=PRICER_NEURAL_WEIGHTS_PATH)
        neural_result = neural_adapter.estimate(text)

        logger.debug(
            "Real estimator: neural available=%s value=%s error=%s",
            neural_result.available,
            neural_result.value_usd,
            neural_result.error_code,
        )

    return _assemble_output(product, frontier_result, neural_result)
