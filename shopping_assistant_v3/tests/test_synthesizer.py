"""Synthesizer unit tests — Phase 5A deterministic, mock-only, no model calls."""

from __future__ import annotations

import pytest

from backend.synthesizer.deterministic import (
    _build_highlight_vi,
    _translate_warnings,
    deterministic_synthesize,
)
from backend.synthesizer.schemas import (
    SummaryCard,
    SynthesizerInput,
    SynthesizerOutput,
)
from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.schemas import (
    ModelBreakdown,
    PriceEstimateOutput,
)


# ====================================================================
# Helpers
# ====================================================================


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


def _make_estimate(**overrides) -> PriceEstimateOutput:
    defaults = {
        "estimated_value_usd": 900.0,
        "discount_usd": 100.01,
        "deal_score": "good",
        "confidence": None,
        "model_breakdown": ModelBreakdown(
            frontier=900.0, specialist=0.0, neural=0.0
        ),
        "warnings": [],
    }
    defaults.update(overrides)
    return PriceEstimateOutput(**defaults)


# ====================================================================
# Schemas
# ====================================================================


class TestSynthesizerSchemas:
    def test_empty_input(self) -> None:
        inp = SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=[],
            price_estimates=[],
            warnings=[],
        )
        assert inp.message_vi == "Tim laptop"

    def test_output_has_required_fields(self) -> None:
        out = SynthesizerOutput(
            answer_vi="Test answer",
            summary_cards=[],
            warnings_vi=[],
        )
        assert out.answer_vi == "Test answer"

    def test_summary_card_preserves_url(self) -> None:
        card = SummaryCard(
            source="Amazon",
            title="Test",
            sale_price_usd=100.0,
            url="https://example.com",
            highlight_vi="Giam $50.00 — deal tot.",
        )
        assert card.url == "https://example.com"


# ====================================================================
# Highlight builder
# ====================================================================


class TestHighlightBuilder:
    def test_hot_deal(self) -> None:
        h = _build_highlight_vi(250.0, "hot")
        assert "deal rat tot" in h
        assert "250.00" in h

    def test_good_deal(self) -> None:
        h = _build_highlight_vi(150.0, "good")
        assert "deal tot" in h
        assert "rat tot" not in h

    def test_overpriced(self) -> None:
        h = _build_highlight_vi(-50.0, "overpriced")
        assert "cao hon gia tri uoc tinh" in h.lower() or "gia hoi cao" in h.lower()

    def test_none_values(self) -> None:
        h = _build_highlight_vi(None, None)
        assert len(h) > 0  # should produce a safe message


# ====================================================================
# Warning translation
# ====================================================================


class TestWarningTranslation:
    def test_frontier_unavailable(self) -> None:
        result = _translate_warnings(["frontier_unavailable:missing_chromadb_path"])
        assert len(result) >= 1
        assert any("nang cao" in r or "Frontier" in r for r in result)

    def test_specialist_unavailable(self) -> None:
        result = _translate_warnings(["specialist_unavailable:missing_service_config"])
        assert len(result) >= 1

    def test_neural_unavailable(self) -> None:
        result = _translate_warnings(["neural_unavailable:missing_weights_path"])
        assert len(result) >= 1

    def test_fallback_used(self) -> None:
        result = _translate_warnings(["real_pricing_fallback_used:sale_price_markup"])
        assert len(result) >= 1

    def test_empty_warnings(self) -> None:
        result = _translate_warnings([])
        assert result == []

    def test_deduplicates_by_prefix(self) -> None:
        result = _translate_warnings([
            "frontier_unavailable:missing_chromadb_path",
            "frontier_unavailable:model_config_missing",
        ])
        assert len(result) == 1  # deduplicated


# ====================================================================
# Synthesizer output — products
# ====================================================================


class TestSynthesizerNoProducts:
    def test_empty_result(self) -> None:
        inp = SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=[],
            price_estimates=[],
            warnings=[],
        )
        out = deterministic_synthesize(inp)
        assert len(out.answer_vi) > 0
        assert "Khong tim thay" in out.answer_vi or "khong tim thay" in out.answer_vi.lower()
        assert out.summary_cards == []

    def test_no_products_with_warnings(self) -> None:
        inp = SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=[],
            price_estimates=[],
            warnings=["source_partial:amazon_failed"],
        )
        out = deterministic_synthesize(inp)
        assert len(out.answer_vi) > 0
        assert len(out.warnings_vi) >= 1


class TestSynthesizerSingleProduct:
    def test_one_product(self) -> None:
        p = _make_product()
        est = _make_estimate()
        inp = SynthesizerInput(
            message_vi="Tim laptop gaming",
            intent="search_deals",
            products=[p],
            price_estimates=[est],
            warnings=[],
        )
        out = deterministic_synthesize(inp)
        assert len(out.answer_vi) > 0
        assert p.title in out.answer_vi
        assert len(out.summary_cards) == 1
        assert out.summary_cards[0].source == "BestBuy"

    def test_one_product_preserves_url(self) -> None:
        p = _make_product(url="https://www.amazon.com/test")
        est = _make_estimate()
        inp = SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=[p],
            price_estimates=[est],
            warnings=[],
        )
        out = deterministic_synthesize(inp)
        assert out.summary_cards[0].url == "https://www.amazon.com/test"


class TestSynthesizerMultipleProducts:
    def test_three_products(self) -> None:
        products = [
            _make_product(title="Laptop A", sale_price_usd=500.0),
            _make_product(title="Laptop B", sale_price_usd=700.0),
            _make_product(title="Laptop C", sale_price_usd=600.0),
        ]
        estimates = [
            _make_estimate(
                estimated_value_usd=800.0, discount_usd=300.0, deal_score="hot"
            ),
            _make_estimate(
                estimated_value_usd=750.0, discount_usd=50.0, deal_score="ok"
            ),
            _make_estimate(
                estimated_value_usd=700.0, discount_usd=100.0, deal_score="good"
            ),
        ]
        inp = SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=products,
            price_estimates=estimates,
            warnings=[],
        )
        out = deterministic_synthesize(inp)
        assert len(out.answer_vi) > 0
        assert len(out.summary_cards) == 3
        # Best deal (highest discount) should be first
        assert out.summary_cards[0].discount_usd == 300.0

    def test_best_deal_not_first_input_order(self) -> None:
        """Best discount is on second product, not first — verify ordering."""
        products = [
            _make_product(title="Cheap Laptop", sale_price_usd=300.0),
            _make_product(title="Premium Deal", sale_price_usd=700.0),
            _make_product(title="Mid Laptop", sale_price_usd=500.0),
        ]
        estimates = [
            _make_estimate(
                estimated_value_usd=320.0, discount_usd=20.0, deal_score="ok"
            ),
            _make_estimate(
                estimated_value_usd=1000.0, discount_usd=300.0, deal_score="hot"
            ),
            _make_estimate(
                estimated_value_usd=600.0, discount_usd=100.0, deal_score="good"
            ),
        ]
        inp = SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=products,
            price_estimates=estimates,
            warnings=[],
        )
        out = deterministic_synthesize(inp)
        # Best deal (discount 300) should be first in summary_cards
        assert out.summary_cards[0].title == "Premium Deal"
        assert out.summary_cards[0].discount_usd == 300.0
        # answer_vi should mention the best deal product
        assert "Premium Deal" in out.answer_vi


# ====================================================================
# Synthesizer — unsupported intent
# ====================================================================


class TestSynthesizerUnsupported:
    def test_unsupported_returns_help_message(self) -> None:
        inp = SynthesizerInput(
            message_vi="Xin chao",
            intent="unsupported",
            products=[],
            price_estimates=[],
            warnings=[],
        )
        out = deterministic_synthesize(inp)
        assert len(out.answer_vi) > 0
        assert "tro ly mua sam" in out.answer_vi.lower()


# ====================================================================
# Evidence rules — no hallucination
# ====================================================================


class TestEvidenceRules:
    def test_no_invented_prices(self) -> None:
        p = _make_product(sale_price_usd=None)
        est = _make_estimate(
            estimated_value_usd=0.0, discount_usd=0.0, deal_score="ok",
            model_breakdown=ModelBreakdown(frontier=0.0, specialist=0.0, neural=0.0),
        )
        inp = SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=[p],
            price_estimates=[est],
            warnings=[],
        )
        out = deterministic_synthesize(inp)
        card = out.summary_cards[0]
        # Sale price is None (product had no price) — synthesizer must not invent it
        assert card.sale_price_usd is None

    def test_answer_vi_never_empty(self) -> None:
        """For any input, answer_vi must be non-empty."""
        inp = SynthesizerInput(
            message_vi="",
            intent="search_deals",
            products=[],
            price_estimates=[],
            warnings=[],
        )
        out = deterministic_synthesize(inp)
        assert len(out.answer_vi) > 0
