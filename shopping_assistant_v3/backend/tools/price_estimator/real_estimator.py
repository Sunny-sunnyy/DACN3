"""Real price estimator orchestrator — Phase 4C.3.

Assembles PriceEstimateOutput from available components:
  - Frontier adapter (via PRICER_CHROMADB_PATH + PRICER_FRONTIER_MODEL_ID) — Phase 4C.2.
  - Specialist adapter (via PRICER_SPECIALIST_SERVICE + PRICER_SPECIALIST_CLASS) — Phase 4C.3.
  - Neural adapter (via PRICER_NEURAL_WEIGHTS_PATH) — Phase 4C.1.

Mock path is in tool.py; this module is only reached when
ENABLE_REAL_MODEL_CALLS=true.

Assembly policy:
  - All 3 available → ensemble formula 0.8*f + 0.1*s + 0.1*n (success, no partial warning).
  - Partial → priority fallback: frontier > specialist > neural > 5% markup.
    Exactly one ensemble_partial:<mode> warning + model-specific unavailable codes.
"""

from __future__ import annotations

import logging

from backend.shared.config import (
    PRICER_CHROMADB_PATH,
    PRICER_FRONTIER_MODEL_ID,
    PRICER_NEURAL_WEIGHTS_PATH,
    PRICER_SPECIALIST_CLASS,
    PRICER_SPECIALIST_SERVICE,
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
from backend.tools.price_estimator.specialist.adapter import (
    SpecialistEstimateResult,
    SpecialistPriceAdapter,
)

logger = logging.getLogger("shopping_assistant_v3.real_estimator")

# ── warning grammar (key:value, no space after colon) ──────────────────
_WARN_ENSEMBLE_FRONTIER = "ensemble_partial:frontier_only"
_WARN_ENSEMBLE_SPECIALIST = "ensemble_partial:specialist_only"
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
    specialist_result: SpecialistEstimateResult,
) -> PriceEstimateOutput:
    """Pure function: assemble PriceEstimateOutput from 3 adapter results.

    Assembly policy:
      1. All 3 available → ensemble formula 0.8*f + 0.1*s + 0.1*n.
         This is a success state — no ensemble_partial warning.
      2. Frontier available (partial) → use frontier value.
      3. Frontier unavailable, specialist available → use specialist value.
      4. Frontier+specialist unavailable, neural available → use neural value.
      5. None available → 5% markup fallback.

    Partial cases (2-5) always include exactly one ensemble_partial:<mode>
    warning plus model-specific unavailable codes.

    Testable without any heavy deps — just pass real or fake result objects.
    """
    sale_price = product.sale_price_usd or 0.0
    warnings: list[str] = []

    f_ok = frontier_result.available and frontier_result.value_usd is not None
    s_ok = specialist_result.available and specialist_result.value_usd is not None
    n_ok = neural_result.available and neural_result.value_usd is not None

    f_raw = frontier_result.value_usd if f_ok else 0.0
    s_raw = specialist_result.value_usd if s_ok else 0.0
    n_raw = neural_result.value_usd if n_ok else 0.0

    # Breakdown shows only contributing model values (non-winning = 0.0).
    b_frontier = 0.0
    b_specialist = 0.0
    b_neural = 0.0

    # ── Case 1: All 3 available → ensemble formula ──
    if f_ok and s_ok and n_ok:
        estimated_value = round(
            0.8 * f_raw + 0.1 * s_raw + 0.1 * n_raw, 2
        )
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)
        b_frontier = f_raw
        b_specialist = s_raw
        b_neural = n_raw
        # Success state — no ensemble_partial warning.

    # ── Case 2: Frontier available (partial) ──
    elif f_ok:
        estimated_value = f_raw
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)
        b_frontier = f_raw
        warnings.append(_WARN_ENSEMBLE_FRONTIER)

    # ── Case 3: Specialist available (frontier unavailable) ──
    elif s_ok:
        estimated_value = s_raw
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)
        b_specialist = s_raw
        warnings.append(_WARN_ENSEMBLE_SPECIALIST)

    # ── Case 4: Neural available (frontier+specialist unavailable) ──
    elif n_ok:
        estimated_value = n_raw
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)
        b_neural = n_raw
        warnings.append(_WARN_ENSEMBLE_NEURAL)

    # ── Case 5: Fallback ──
    else:
        estimated_value = round(sale_price * 1.05, 2)
        discount = round(estimated_value - sale_price, 2)
        deal_score = "ok"
        warnings.append(_WARN_FALLBACK_USED)
        warnings.append(_WARN_ENSEMBLE_FALLBACK)

    # ── Model-specific unavailable warnings (partial/fallback cases) ──
    if not f_ok and frontier_result.error_code:
        warnings.append(f"frontier_unavailable:{frontier_result.error_code}")
    if not s_ok and specialist_result.error_code:
        warnings.append(f"specialist_unavailable:{specialist_result.error_code}")
    if not n_ok and neural_result.error_code:
        warnings.append(f"neural_unavailable:{neural_result.error_code}")

    return PriceEstimateOutput(
        estimated_value_usd=estimated_value,
        discount_usd=discount,
        deal_score=deal_score,
        confidence=None,
        model_breakdown=ModelBreakdown(
            frontier=b_frontier,
            specialist=b_specialist,
            neural=b_neural,
        ),
        warnings=warnings,
    )


def estimate_price_real(product: ProductCandidate) -> PriceEstimateOutput:
    """Real price estimation using all configured adapters.

    Attempts all adapters whose config is present. Fail-fast on missing
    config (returns unavailable result immediately, no network calls).
    Then assembles output via _assemble_output.

    Current adapters:
      - Frontier (4C.2): GPT + ChromaDB RAG
      - Specialist (4C.3): Modal fine-tuned Llama
      - Neural (4C.1): PyTorch DNN

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

    # Run specialist adapter (lazy-loads on first call)
    specialist_adapter = SpecialistPriceAdapter(
        service_name=PRICER_SPECIALIST_SERVICE,
        class_name=PRICER_SPECIALIST_CLASS,
    )
    specialist_result = specialist_adapter.try_estimate(text)

    logger.debug(
        "Real estimator: specialist available=%s value=%s error=%s",
        specialist_result.available,
        specialist_result.value_usd,
        specialist_result.error_code,
    )

    # Run neural adapter (lazy-loads on first call)
    neural_adapter = NeuralPriceAdapter(weights_path=PRICER_NEURAL_WEIGHTS_PATH)
    neural_result = neural_adapter.estimate(text)

    logger.debug(
        "Real estimator: neural available=%s value=%s error=%s",
        neural_result.available,
        neural_result.value_usd,
        neural_result.error_code,
    )

    return _assemble_output(product, frontier_result, neural_result, specialist_result)
