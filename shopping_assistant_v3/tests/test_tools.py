"""Tool schema validation and mock behavior tests.

All tests use JSON fixtures only. No network, no model calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput, ProductCandidate
from backend.tools.deal_search.tool import deal_search
from backend.tools.price_estimator.schemas import (
    ModelBreakdown,
    PriceEstimateInput,
    PriceEstimateOutput,
)
from backend.tools.price_estimator.tool import estimate_price

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

PRODUCTS_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "backend" / "tools" / "deal_search" / "fixtures" / "mock_products.json"
)
ESTIMATES_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "backend" / "tools" / "price_estimator" / "fixtures" / "mock_estimates.json"
)


# ====================================================================
# Deal search schema tests
# ====================================================================

class TestDealSearchInput:
    def test_valid_input(self) -> None:
        inp = DealSearchInput(query_en="gaming laptop")
        assert inp.query_en == "gaming laptop"
        assert inp.source == "All"
        assert inp.max_results_per_source == 5

    def test_default_max_results_is_5(self) -> None:
        inp = DealSearchInput(query_en="test")
        assert inp.max_results_per_source == 5

    def test_empty_query_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DealSearchInput(query_en="")

    def test_invalid_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DealSearchInput(query_en="laptop", source="Ebay")  # type: ignore[arg-type]

    def test_max_results_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DealSearchInput(query_en="laptop", max_results_per_source=0)
        with pytest.raises(ValidationError):
            DealSearchInput(query_en="laptop", max_results_per_source=21)


class TestDealSearchOutput:
    def test_empty_output(self) -> None:
        out = DealSearchOutput()
        assert out.products == []
        assert out.warnings == []

    def test_output_with_products(self) -> None:
        p = ProductCandidate(source="Amazon", title="Test Product")
        out = DealSearchOutput(products=[p], warnings=["warning text"])
        assert len(out.products) == 1
        assert out.warnings == ["warning text"]


# ====================================================================
# Price estimator schema tests
# ====================================================================

class TestPriceEstimateInput:
    def test_valid_input(self) -> None:
        p = ProductCandidate(source="Amazon", title="Test Laptop", sale_price_usd=100.0)
        inp = PriceEstimateInput(product=p)
        assert inp.product.title == "Test Laptop"


class TestModelBreakdown:
    def test_valid_breakdown(self) -> None:
        mb = ModelBreakdown(frontier=100.0, specialist=90.0, neural=95.0)
        assert mb.frontier == 100.0
        assert mb.specialist == 90.0
        assert mb.neural == 95.0

    def test_missing_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelBreakdown(frontier=100.0, specialist=90.0)  # type: ignore[arg-type]


class TestPriceEstimateOutput:
    def test_valid_output(self) -> None:
        mb = ModelBreakdown(frontier=100.0, specialist=90.0, neural=95.0)
        out = PriceEstimateOutput(
            estimated_value_usd=110.0,
            discount_usd=10.0,
            deal_score="ok",
            model_breakdown=mb,
        )
        assert out.deal_score == "ok"
        assert out.discount_usd == 10.0

    def test_invalid_deal_score_rejected(self) -> None:
        mb = ModelBreakdown(frontier=100.0, specialist=90.0, neural=95.0)
        with pytest.raises(ValidationError):
            PriceEstimateOutput(
                estimated_value_usd=110.0,
                discount_usd=10.0,
                deal_score="amazing",  # type: ignore[arg-type]
                model_breakdown=mb,
            )


# ====================================================================
# Fixture integrity tests
# ====================================================================

class TestMockProductsFixture:
    def test_json_is_parseable(self) -> None:
        data = json.loads(PRODUCTS_FIXTURE.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 10

    def test_all_products_have_required_fields(self) -> None:
        data = json.loads(PRODUCTS_FIXTURE.read_text(encoding="utf-8"))
        for product in data:
            assert "source" in product
            assert product["source"] in ("Amazon", "BestBuy")
            assert "title" in product
            assert len(product["title"]) > 0
            assert "sale_price_usd" in product
            assert isinstance(product["sale_price_usd"], (int, float))
            assert "url" in product

    def test_source_counts(self) -> None:
        data = json.loads(PRODUCTS_FIXTURE.read_text(encoding="utf-8"))
        amazon_count = sum(1 for p in data if p["source"] == "Amazon")
        bestbuy_count = sum(1 for p in data if p["source"] == "BestBuy")
        assert amazon_count == 5
        assert bestbuy_count == 5


class TestMockEstimatesFixture:
    def test_json_is_parseable(self) -> None:
        data = json.loads(ESTIMATES_FIXTURE.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert len(data) >= 1

    def test_entries_have_required_fields(self) -> None:
        data = json.loads(ESTIMATES_FIXTURE.read_text(encoding="utf-8"))
        for key, entry in data.items():
            assert "|" in key
            assert "estimated_value_usd" in entry
            assert "model_breakdown" in entry
            mb = entry["model_breakdown"]
            assert "frontier" in mb
            assert "specialist" in mb
            assert "neural" in mb


# ====================================================================
# Mock deal_search behavior tests
# ====================================================================

class TestDealSearchMock:
    def test_returns_both_sources_when_source_is_all(self) -> None:
        result = deal_search(DealSearchInput(query_en="gaming laptop", source="All"))
        sources = {p.source for p in result.products}
        assert "Amazon" in sources
        assert "BestBuy" in sources

    def test_returns_only_amazon_when_filtered(self) -> None:
        result = deal_search(DealSearchInput(query_en="gaming laptop", source="Amazon"))
        sources = {p.source for p in result.products}
        assert sources == {"Amazon"}

    def test_returns_only_bestbuy_when_filtered(self) -> None:
        result = deal_search(DealSearchInput(query_en="gaming laptop", source="BestBuy"))
        sources = {p.source for p in result.products}
        assert sources == {"BestBuy"}

    def test_keyword_match_filters_results(self) -> None:
        result = deal_search(DealSearchInput(query_en="gaming laptop", source="All"))
        assert len(result.products) >= 2
        for p in result.products:
            text = (p.title + " " + (p.features or "")).lower()
            assert "gaming" in text or "laptop" in text

    def test_empty_results_sets_warning(self) -> None:
        result = deal_search(DealSearchInput(query_en="xyznonexistent12345", source="All"))
        assert result.products == []
        assert len(result.warnings) >= 1
        assert "No products found" in result.warnings[0]

    def test_results_dont_exceed_max_per_source(self) -> None:
        result = deal_search(
            DealSearchInput(query_en="laptop", source="All", max_results_per_source=1)
        )
        by_source: dict[str, int] = {}
        for p in result.products:
            by_source[p.source] = by_source.get(p.source, 0) + 1
        for count in by_source.values():
            assert count <= 1


# ====================================================================
# Mock price_estimator behavior tests
# ====================================================================

def _make_product(
    source: str = "Amazon",
    title: str = "Test Product",
    sale_price: float = 100.0,
) -> ProductCandidate:
    return ProductCandidate(
        source=source, title=title, sale_price_usd=sale_price, url="https://example.com"
    )


class TestPriceEstimatorMock:
    def test_fixture_lookup_returns_exact_value(self) -> None:
        p = _make_product(
            source="BestBuy",
            title="ASUS ROG Strix G16 Gaming Laptop",
            sale_price=749.99,
        )
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.estimated_value_usd == 949.99
        assert result.discount_usd == 200.0
        assert result.deal_score == "hot"
        assert result.warnings == []

    def test_fallback_rule_for_unknown_product(self) -> None:
        p = _make_product(
            source="Amazon",
            title="Unknown Gadget XYZ",
            sale_price=100.0,
        )
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.estimated_value_usd == 110.0  # 100.0 * 1.10
        assert result.discount_usd == 10.0
        assert result.deal_score == "ok"
        assert len(result.warnings) >= 1
        assert "fallback" in result.warnings[0].lower()
        assert result.model_breakdown.frontier == 110.0
        assert result.model_breakdown.specialist == 110.0
        assert result.model_breakdown.neural == 110.0

    def test_identical_inputs_produce_identical_outputs(self) -> None:
        p = _make_product(
            source="Amazon",
            title="Consistent Test Product",
            sale_price=50.0,
        )
        r1 = estimate_price(PriceEstimateInput(product=p))
        r2 = estimate_price(PriceEstimateInput(product=p))
        assert r1.estimated_value_usd == r2.estimated_value_usd
        assert r1.discount_usd == r2.discount_usd
        assert r1.deal_score == r2.deal_score

    def test_deal_score_hot(self) -> None:
        p_big = _make_product(
            source="BestBuy",
            title="ASUS ROG Strix G16 Gaming Laptop",
            sale_price=749.99,
        )
        result = estimate_price(PriceEstimateInput(product=p_big))
        assert result.deal_score == "hot"
        assert result.discount_usd >= 200

    def test_deal_score_overpriced(self) -> None:
        p = _make_product(
            source="BestBuy",
            title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
            sale_price=500.00,
        )
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.deal_score == "overpriced"
        assert result.discount_usd < 0

    def test_model_breakdown_present(self) -> None:
        p = _make_product(sale_price=100.0)
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.model_breakdown.frontier > 0
        assert result.model_breakdown.specialist > 0
        assert result.model_breakdown.neural > 0


# ====================================================================
# ENABLE_REAL_* flag tests
# ====================================================================

class TestRealModeFlags:
    def test_real_search_raises_not_implemented(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.deal_search.tool.ENABLE_REAL_SEARCH", True
        )
        with pytest.raises(NotImplementedError, match="Phase 4A"):
            deal_search(DealSearchInput(query_en="laptop"))

    def test_real_model_calls_raises_not_implemented(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.tool.ENABLE_REAL_MODEL_CALLS", True
        )
        p = _make_product()
        with pytest.raises(NotImplementedError, match="Phase 4A"):
            estimate_price(PriceEstimateInput(product=p))
