"""Opt-in frontier smoke tests — skipped by default.

Requires ALL of:
  - ENABLE_REAL_MODEL_CALLS=true
  - PRICER_CHROMADB_PATH set and directory exists
  - PRICER_FRONTIER_MODEL_ID set
  - OPENAI_API_KEY set (used by openai.OpenAI())
  - frontier extras installed (chromadb, sentence-transformers, openai)

Run manually:
  ENABLE_REAL_MODEL_CALLS=true \
  PRICER_CHROMADB_PATH=/path/to/products_vectorstore \
  PRICER_FRONTIER_MODEL_ID=gpt-5.1 \
  OPENAI_API_KEY=<set locally> \
  uv run pytest tests/test_real_pricing_frontier.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Module-level skips use stdlib only — no heavy imports at collection time.
# Heavy deps are checked inside test bodies via pytest.importorskip().
pytestmark = [
    pytest.mark.skipif(
        os.getenv("ENABLE_REAL_MODEL_CALLS") != "true",
        reason="Requires ENABLE_REAL_MODEL_CALLS=true",
    ),
    pytest.mark.skipif(
        not os.getenv("PRICER_CHROMADB_PATH"),
        reason="Requires PRICER_CHROMADB_PATH set",
    ),
    pytest.mark.skipif(
        not Path(os.getenv("PRICER_CHROMADB_PATH", "")).exists(),
        reason="ChromaDB directory does not exist at configured path",
    ),
    pytest.mark.skipif(
        not os.getenv("PRICER_FRONTIER_MODEL_ID"),
        reason="Requires PRICER_FRONTIER_MODEL_ID set",
    ),
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY set",
    ),
]


def _require_frontier_deps() -> None:
    """Skip if frontier extras not installed. Call inside test body.

    Uses pytest.importorskip so heavy deps are only checked after
    env-based pytestmark skips have already passed.
    """
    pytest.importorskip("chromadb", reason="Requires frontier extras (chromadb)")
    pytest.importorskip(
        "sentence_transformers",
        reason="Requires frontier extras (sentence-transformers)",
    )
    pytest.importorskip("openai", reason="Requires frontier extras (openai)")


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
# Frontier adapter real load tests (opt-in only)
# ====================================================================


class TestFrontierAdapterRealLoad:
    """Frontier adapter loads ChromaDB, embedding model, and returns estimates."""

    def test_loads_and_returns_value(self) -> None:
        _require_frontier_deps()
        chromadb_path = os.environ["PRICER_CHROMADB_PATH"]
        model_id = os.environ["PRICER_FRONTIER_MODEL_ID"]
        assert Path(chromadb_path).exists(), f"ChromaDB missing: {chromadb_path}"

        from backend.tools.price_estimator.frontier.adapter import FrontierPriceAdapter

        adapter = FrontierPriceAdapter(
            chromadb_path=chromadb_path,
            model_id=model_id,
        )
        result = adapter.try_estimate(
            "Title: Gaming Laptop\n"
            "Category: Unknown\n"
            "Brand: ASUS\n"
            "Description: ASUS gaming laptop, priced at $1200\n"
            "Details: RTX 4070, 32GB RAM"
        )
        assert result.available, f"Frontier unavailable: {result.error_code} — {result.error_detail}"
        assert result.value_usd is not None
        assert result.value_usd > 0.0, f"Expected positive price, got {result.value_usd}"

    def test_inference_on_minimal_text(self) -> None:
        _require_frontier_deps()
        chromadb_path = os.environ["PRICER_CHROMADB_PATH"]
        model_id = os.environ["PRICER_FRONTIER_MODEL_ID"]

        from backend.tools.price_estimator.frontier.adapter import FrontierPriceAdapter

        adapter = FrontierPriceAdapter(
            chromadb_path=chromadb_path,
            model_id=model_id,
        )
        result = adapter.try_estimate("Unknown product")
        assert result.available, f"Frontier unavailable: {result.error_code}"
        assert result.value_usd is not None
        assert result.value_usd >= 0.0


class TestRealEstimatorFullFlowFrontier:
    """estimate_price_real end-to-end with frontier available."""

    def test_real_estimator_frontier_primary(self) -> None:
        _require_frontier_deps()
        from backend.tools.price_estimator.real_estimator import estimate_price_real

        p = _make_product()
        output = estimate_price_real(p)
        assert output.estimated_value_usd > 0
        # With real frontier available, short-circuit means neural skipped.
        assert "ensemble_partial:frontier_only" in output.warnings
        assert output.model_breakdown.frontier > 0.0
        assert output.model_breakdown.neural == 0.0
        assert "real_pricing_fallback_used" not in output.warnings

    def test_real_estimator_with_minimal_product(self) -> None:
        _require_frontier_deps()
        from backend.tools.price_estimator.real_estimator import estimate_price_real

        p = _make_product(
            title="Headphones", brand="", features="", sale_price_usd=49.99
        )
        output = estimate_price_real(p)
        assert output.estimated_value_usd > 0
        assert isinstance(output.estimated_value_usd, float)
