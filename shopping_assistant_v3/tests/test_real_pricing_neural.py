"""Opt-in neural smoke tests — skipped by default.

Requires ALL of:
  - ENABLE_REAL_MODEL_CALLS=true
  - PRICER_NEURAL_WEIGHTS_PATH set and file exists
  - neural extras installed (torch, sklearn, numpy)

Run manually:
  ENABLE_REAL_MODEL_CALLS=true \
  PRICER_NEURAL_WEIGHTS_PATH=/path/to/deep_neural_network.pth \
  uv run pytest tests/test_real_pricing_neural.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _neural_deps_available() -> bool:
    """Return True if torch, sklearn, numpy are installed (neural extras)."""
    try:
        import numpy  # noqa: F401
        import sklearn  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def _setup_ok() -> bool:
    return (
        os.getenv("ENABLE_REAL_MODEL_CALLS") == "true"
        and bool(os.getenv("PRICER_NEURAL_WEIGHTS_PATH"))
        and Path(os.getenv("PRICER_NEURAL_WEIGHTS_PATH", "")).exists()
        and _neural_deps_available()
    )


pytestmark = [
    pytest.mark.skipif(
        os.getenv("ENABLE_REAL_MODEL_CALLS") != "true",
        reason="Requires ENABLE_REAL_MODEL_CALLS=true",
    ),
    pytest.mark.skipif(
        not os.getenv("PRICER_NEURAL_WEIGHTS_PATH"),
        reason="Requires PRICER_NEURAL_WEIGHTS_PATH set",
    ),
    pytest.mark.skipif(
        not Path(os.getenv("PRICER_NEURAL_WEIGHTS_PATH", "")).exists(),
        reason="Weights file does not exist at configured path",
    ),
    pytest.mark.skipif(
        not _neural_deps_available(),
        reason="Requires neural extras installed (uv sync --extra neural)",
    ),
]


# ====================================================================
# Helpers
# ====================================================================


def _make_product(**overrides) -> "ProductCandidate":
    from backend.tools.deal_search.schemas import ProductCandidate

    defaults = {
        "source": "BestBuy",
        "title": "Test Laptop Pro 15",
        "brand": "TestBrand",
        "sale_price_usd": 799.99,
        "url": "https://example.com/test-laptop",
        "features": "16GB RAM, 512GB SSD, RTX 4060",
    }
    defaults.update(overrides)
    return ProductCandidate(**defaults)


# ====================================================================
# Real neural smoke tests (opt-in only)
# ====================================================================


class TestNeuralAdapterRealLoad:
    """Neural adapter loads weights and runs inference."""

    def test_loads_weights_and_returns_value(self) -> None:
        weights_path = os.environ["PRICER_NEURAL_WEIGHTS_PATH"]
        assert Path(weights_path).exists(), f"Weights file missing: {weights_path}"

        from backend.tools.price_estimator.neural.adapter import NeuralPriceAdapter

        adapter = NeuralPriceAdapter(weights_path=weights_path)
        result = adapter.estimate(
            "Title: Gaming Laptop\n"
            "Category: Unknown\n"
            "Brand: ASUS\n"
            "Description: ASUS gaming laptop, priced at $1200\n"
            "Details: RTX 4070, 32GB RAM"
        )
        assert result.available, f"Neural unavailable: {result.error_code}"
        assert result.value_usd is not None
        assert result.value_usd > 0.0, f"Expected positive price, got {result.value_usd}"

    def test_inference_on_minimal_text(self) -> None:
        weights_path = os.environ["PRICER_NEURAL_WEIGHTS_PATH"]

        from backend.tools.price_estimator.neural.adapter import NeuralPriceAdapter

        adapter = NeuralPriceAdapter(weights_path=weights_path)
        result = adapter.estimate("Unknown product")
        assert result.available, f"Neural unavailable: {result.error_code}"
        assert result.value_usd is not None
        assert result.value_usd >= 0.0


class TestRealEstimatorFullFlow:
    """estimate_price_real end-to-end with neural."""

    def test_real_estimator_with_neural_success(self) -> None:
        from backend.tools.price_estimator.real_estimator import estimate_price_real

        p = _make_product()
        output = estimate_price_real(p)
        assert output.estimated_value_usd > 0
        assert "ensemble_partial:neural_only" in output.warnings
        assert "real_pricing_fallback_used:sale_price_markup" not in output.warnings

    def test_real_estimator_with_minimal_product(self) -> None:
        from backend.tools.price_estimator.real_estimator import estimate_price_real

        p = _make_product(title="Headphones", brand="", features="", sale_price_usd=49.99)
        output = estimate_price_real(p)
        assert output.estimated_value_usd > 0
        # Neural might succeed or not; output must be valid either way
        assert isinstance(output.estimated_value_usd, float)
