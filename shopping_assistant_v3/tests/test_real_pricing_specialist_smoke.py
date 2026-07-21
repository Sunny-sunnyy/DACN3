"""Opt-in smoke tests for real Modal specialist — Phase 4C.3.

All tests are skipped by default. Requires ENABLE_REAL_MODEL_CALLS=true
and valid Modal config (PRICER_SPECIALIST_SERVICE, PRICER_SPECIALIST_CLASS,
Modal token/environment).

WARNING: These tests make real Modal calls that may incur cost and latency.
Only run with explicit opt-in.
"""

from __future__ import annotations

import os

import pytest

from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.specialist.adapter import (
    SpecialistPriceAdapter,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("ENABLE_REAL_MODEL_CALLS"),
    reason="ENABLE_REAL_MODEL_CALLS not set",
)


def _make_product(**overrides) -> ProductCandidate:
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


@pytest.mark.skipif(
    not os.getenv("PRICER_SPECIALIST_SERVICE")
    or not os.getenv("PRICER_SPECIALIST_CLASS"),
    reason="PRICER_SPECIALIST_SERVICE and PRICER_SPECIALIST_CLASS not set",
)
class TestSpecialistRealCall:
    """Real Modal specialist calls — only when config is complete."""

    def test_estimate_returns_positive_value(self) -> None:
        from backend.shared.config import (
            PRICER_SPECIALIST_CLASS,
            PRICER_SPECIALIST_SERVICE,
        )

        adapter = SpecialistPriceAdapter(
            service_name=PRICER_SPECIALIST_SERVICE,
            class_name=PRICER_SPECIALIST_CLASS,
        )
        result = adapter.try_estimate(
            "Title: Gaming Laptop | Brand: ASUS | priced at $799.99 | "
            "Details: 16GB RAM, 512GB SSD, RTX 4060"
        )
        assert result.available, (
            f"Specialist unavailable: {result.error_code} — {result.error_detail}"
        )
        assert result.value_usd is not None
        assert result.value_usd > 0

    def test_estimate_returns_reasonable_value(self) -> None:
        """Value should be within reasonable range for a laptop."""
        from backend.shared.config import (
            PRICER_SPECIALIST_CLASS,
            PRICER_SPECIALIST_SERVICE,
        )

        adapter = SpecialistPriceAdapter(
            service_name=PRICER_SPECIALIST_SERVICE,
            class_name=PRICER_SPECIALIST_CLASS,
        )
        result = adapter.try_estimate(
            "Title: Budget Chromebook | Brand: Acer | priced at $199.99 | "
            "Details: 4GB RAM, 64GB eMMC, Celeron"
        )
        assert result.available
        assert result.value_usd is not None
        # A Chromebook should be roughly $100-$500
        assert 50 < result.value_usd < 1000, (
            f"Unexpected specialist value: {result.value_usd}"
        )
