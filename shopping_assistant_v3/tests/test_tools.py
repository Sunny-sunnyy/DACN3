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
    def test_real_search_dispatches_to_real_path(
        self, monkeypatch
    ) -> None:
        """Phase 4B: ENABLE_REAL_SEARCH=true calls real_deal_search."""
        from backend.tools.deal_search import real_search

        called_with = []

        def fake_real_search(inp):
            called_with.append(inp)
            return DealSearchOutput(products=[], warnings=["ok"])

        monkeypatch.setattr(real_search, "real_deal_search", fake_real_search)
        monkeypatch.setattr(
            "backend.tools.deal_search.tool.ENABLE_REAL_SEARCH", True
        )
        result = deal_search(DealSearchInput(query_en="laptop"))
        assert len(called_with) == 1
        assert called_with[0].query_en == "laptop"
        assert result.warnings == ["ok"]

    def test_real_model_calls_dispatches_to_real_path(
        self, monkeypatch
    ) -> None:
        """Phase 4C.1: ENABLE_REAL_MODEL_CALLS=true dispatches to real path.

        Without PRICER_NEURAL_WEIGHTS_PATH, neural is unavailable.
        Real estimator returns fallback markup + explicit warnings.
        """
        monkeypatch.setattr(
            "backend.tools.price_estimator.tool.ENABLE_REAL_MODEL_CALLS",
            True,
        )
        p = _make_product()
        result = estimate_price(PriceEstimateInput(product=p))
        # Real path with missing weights → fallback
        assert result.estimated_value_usd > 0
        assert result.model_breakdown.neural == 0.0  # neural unavailable
        assert "real_pricing_fallback_used:sale_price_markup" in result.warnings
        assert "neural_unavailable:missing_weights_path" in result.warnings


# ====================================================================
# BestBuy Apollo parser tests (fixture-based, no network)
# ====================================================================

BESTBUY_FIXTURE_HTML = (
    Path(__file__).resolve().parent
    / "fixtures" / "bestbuy_search_page.html"
)


class TestBestBuyApolloParser:
    """Deterministic parser tests using saved BestBuy search page HTML."""

    def test_parse_extracts_sku_ids(self) -> None:
        from backend.tools.deal_search.bestbuy_search import (
            _parse_apollo_search_page,
        )

        html = BESTBUY_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_apollo_search_page(html)
        assert len(result) >= 2, f"Expected >= 2 SKUs, got {len(result)}"
        assert all("skuId" in item for item in result)
        assert all("pdpUrl" in item for item in result)

    def test_parse_sku_ids_are_numeric(self) -> None:
        from backend.tools.deal_search.bestbuy_search import (
            _parse_apollo_search_page,
        )

        html = BESTBUY_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_apollo_search_page(html)
        for item in result:
            assert item["skuId"].isdigit(), (
                f"skuId must be numeric, got {item['skuId']}"
            )
            assert len(item["skuId"]) >= 5, (
                f"skuId too short: {item['skuId']}"
            )

    def test_parse_excludes_openbox_urls(self) -> None:
        from backend.tools.deal_search.bestbuy_search import (
            _parse_apollo_search_page,
        )

        html_with_openbox = (
            BESTBUY_FIXTURE_HTML.read_text(encoding="utf-8")
            + '\n{"skuId":"99999999"},"pdpUrl":"https://www.bestbuy.com/product/openbox/99999999"'
        )
        result = _parse_apollo_search_page(html_with_openbox)
        for item in result:
            if item["skuId"] == "99999999":
                assert "openbox" not in item.get("pdpUrl", ""), (
                    "openbox URL should be excluded"
                )

    def test_parse_empty_html_returns_empty(self) -> None:
        from backend.tools.deal_search.bestbuy_search import (
            _parse_apollo_search_page,
        )

        result = _parse_apollo_search_page("<html></html>")
        assert result == []


# ====================================================================
# Amazon search page parser tests (fixture-based, no network)
# ====================================================================

AMAZON_FIXTURE_HTML = (
    Path(__file__).resolve().parent
    / "fixtures" / "amazon_search_page.html"
)


class TestAmazonSearchPageParser:
    """Deterministic parser tests using saved Amazon search page HTML."""

    def test_parse_extracts_product_cards(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            _parse_amazon_search_page,
        )

        html = AMAZON_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_amazon_search_page(html)
        assert len(result) == 2, f"Expected 2 products, got {len(result)}"

    def test_parse_extracts_asin(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            _parse_amazon_search_page,
        )

        html = AMAZON_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_amazon_search_page(html)
        asins = {p["asin"] for p in result}
        assert "B0TEST0001" in asins
        assert "B0TEST0002" in asins

    def test_parse_extracts_title(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            _parse_amazon_search_page,
        )

        html = AMAZON_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_amazon_search_page(html)
        titles = [p["title"] for p in result]
        assert any("ASUS" in t for t in titles)
        assert any("Headphones" in t for t in titles)

    def test_parse_extracts_prices(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            _parse_amazon_search_page,
        )

        html = AMAZON_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_amazon_search_page(html)
        for p in result:
            assert p["current_price"] > 0, (
                f"current_price must be > 0 for {p['asin']}"
            )

    def test_parse_detects_on_sale(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            _parse_amazon_search_page,
        )

        html = AMAZON_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_amazon_search_page(html)
        for p in result:
            assert p["on_sale"] is True, (
                f"Fixture products should be on_sale (list > current), "
                f"got on_sale={p['on_sale']} for {p['asin']}"
            )

    def test_parse_extracts_specs(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            _parse_amazon_search_page,
        )

        html = AMAZON_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_amazon_search_page(html)
        # First product has detailed specs.
        asus = [p for p in result if p["asin"] == "B0TEST0001"][0]
        assert len(asus["specs"]) >= 30, (
            f"ASUS product should have detailed specs, got {len(asus['specs'])} chars"
        )
        # Second product has thin specs (< 50 chars).
        sa = [p for p in result if p["asin"] == "B0TEST0002"][0]
        assert len(sa["specs"]) < 50, (
            f"SimpleAudio product should have thin specs, got {len(sa['specs'])} chars"
        )

    def test_parse_extracts_brand_from_specs(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            _parse_amazon_search_page,
        )

        html = AMAZON_FIXTURE_HTML.read_text(encoding="utf-8")
        result = _parse_amazon_search_page(html)
        asus = [p for p in result if p["asin"] == "B0TEST0001"][0]
        assert asus["brand"] == "ASUS"

    def test_parse_empty_html_returns_empty(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            _parse_amazon_search_page,
        )

        result = _parse_amazon_search_page("<html></html>")
        assert result == []


# ====================================================================
# _parse_price unit tests
# ====================================================================


class TestAmazonParsePrice:
    """Unit tests for Amazon price string parser."""

    def test_standard_price(self) -> None:
        from backend.tools.deal_search.amazon_search import _parse_price

        assert _parse_price("$1,099.99") == 1099.99

    def test_whole_dollar(self) -> None:
        from backend.tools.deal_search.amazon_search import _parse_price

        assert _parse_price("$499") == 499.0

    def test_cents_only(self) -> None:
        from backend.tools.deal_search.amazon_search import _parse_price

        assert _parse_price("$0.99") == 0.99

    def test_empty_string(self) -> None:
        from backend.tools.deal_search.amazon_search import _parse_price

        assert _parse_price("") == 0.0

    def test_invalid_string(self) -> None:
        from backend.tools.deal_search.amazon_search import _parse_price

        assert _parse_price("not a price") == 0.0


# ====================================================================
# amazon_features_limited warning test (mock-safe, no network)
# ====================================================================


class TestAmazonFeaturesLimitedWarning:
    """Verify amazon_features_limited warning is returned in tool output.

    Uses a fake curl_cffi session + local Amazon fixture HTML so the test
    runs without network. Default test — always runs.
    """

    def test_thin_specs_product_emits_features_limited_warning(
        self, monkeypatch
    ) -> None:
        from backend.tools.deal_search import amazon_search
        from backend.tools.deal_search.amazon_search import (
            search_amazon_real,
        )

        # Load the fixture HTML (contains 1 thin-specs product).
        fixture_html = AMAZON_FIXTURE_HTML.read_text(encoding="utf-8")

        # Fake session that returns the fixture.
        class FakeResponse:
            text = fixture_html

        class FakeSession:
            def get(self, url, timeout=None):
                return FakeResponse()
            def post(self, url, data=None, timeout=None):
                return FakeResponse()

        # Patch the module-level guard and session factory.
        monkeypatch.setattr(amazon_search, "_CURL_CFFI_AVAILABLE", True)
        monkeypatch.setattr(
            amazon_search, "_create_session", lambda: FakeSession()
        )

        products, warnings = search_amazon_real(
            query="gaming laptop", max_results=5
        )

        # Fixture has 2 products, both on_sale.
        assert len(products) == 2

        # Second product (B0TEST0002) has thin specs — must get warning.
        features_limited = [
            w for w in warnings if w.startswith("amazon_features_limited:")
        ]
        assert len(features_limited) == 1, (
            f"Expected 1 amazon_features_limited warning, got {len(features_limited)}: {warnings}"
        )
        assert "Simple Budget Headphones" in features_limited[0]

        # Verify the warning is properly truncated (< 80 chars title + prefix).
        assert len(features_limited[0]) < 120, (
            f"Warning too long: {len(features_limited[0])} chars"
        )
