"""Neural Price Adapter — lazy-loading wrapper for the PyTorch DNN estimator.

Module-level imports are stdlib only. Heavy dependencies (torch, sklearn, numpy)
and deep_neural_network are imported lazily inside _load_model() on first call.
This keeps the mock path free of neural deps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("shopping_assistant_v3.neural")


@dataclass
class NeuralEstimateResult:
    """Result of a neural price estimation attempt.

    When available=False, error_code describes the failure mode using a
    bounded grammar (see implementation plan for full list).
    error_detail is capped at 200 chars and must never contain raw
    exceptions, stack traces, or secrets.
    """

    value_usd: float | None = None
    available: bool = False
    error_code: str | None = None
    error_detail: str | None = None


def _sanitize_detail(raw: str) -> str:
    """Return a bounded, safe detail string (max 200 chars, single line)."""
    cleaned = str(raw).replace("\n", " ").replace("\r", "").strip()
    if len(cleaned) > 200:
        cleaned = cleaned[:197] + "..."
    return cleaned


class NeuralPriceAdapter:
    """Lazy-loading adapter for the PyTorch DNN price estimator.

    Heavy dependencies (torch, sklearn, numpy) and the deep_neural_network
    module are imported only when estimate() is first called — never at
    module import time.

    Usage:
        adapter = NeuralPriceAdapter(weights_path="/path/to/weights.pth")
        result = adapter.estimate("Title: Laptop ...")
        if result.available:
            print(result.value_usd)
    """

    def __init__(self, weights_path: str) -> None:
        """Store config. No file I/O, no heavy imports at init."""
        self._weights_path = weights_path
        self._model = None          # DeepNeuralNetworkInference or None
        self._init_error: NeuralEstimateResult | None = None
        self._init_attempted = False

    def estimate(self, text: str) -> NeuralEstimateResult:
        """Run neural inference. Lazy-loads deps + model on first call.

        Never raises — failures become NeuralEstimateResult metadata.
        """
        if not self._init_attempted:
            self._init_attempted = True
            self._load_model()

        if self._init_error is not None:
            return self._init_error

        try:
            value = self._model.inference(text)
            value = float(max(0, value))
            return NeuralEstimateResult(
                value_usd=round(value, 2),
                available=True,
            )
        except Exception as exc:
            logger.warning("Neural inference failed: %s", _sanitize_detail(str(exc)))
            return NeuralEstimateResult(
                available=False,
                error_code="inference_failed",
                error_detail=_sanitize_detail(str(exc)),
            )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Lazy init: import heavy deps, setup vectorizer, load weights.

        Sets self._init_error on any failure. Called once by estimate().
        """
        # Step 1: validate weights path
        if not self._weights_path:
            self._init_error = NeuralEstimateResult(
                available=False,
                error_code="missing_weights_path",
                error_detail="PRICER_NEURAL_WEIGHTS_PATH is not set",
            )
            return

        weights = Path(self._weights_path)
        if not weights.exists():
            self._init_error = NeuralEstimateResult(
                available=False,
                error_code="missing_weights_path",
                error_detail="Weights file not found",
            )
            return

        # Step 2: lazy-import heavy dependencies (inside function — NOT at module level)
        try:
            import torch  # noqa: F401
            import sklearn  # noqa: F401
            import numpy  # noqa: F401
        except ImportError as exc:
            self._init_error = NeuralEstimateResult(
                available=False,
                error_code="missing_dependency",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 3: lazy-import neural module (also inside function)
        try:
            from backend.tools.price_estimator.neural.deep_neural_network import (
                DeepNeuralNetworkInference,
            )
        except Exception as exc:
            self._init_error = NeuralEstimateResult(
                available=False,
                error_code="missing_dependency",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 4: setup + load weights
        try:
            self._model = DeepNeuralNetworkInference()
            self._model.setup()
            self._model.load(str(weights))
        except Exception as exc:
            self._init_error = NeuralEstimateResult(
                available=False,
                error_code="model_load_failed",
                error_detail=_sanitize_detail(str(exc)),
            )
