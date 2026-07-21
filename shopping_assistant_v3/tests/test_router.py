"""Router unit tests — Phase 5A deterministic, mock-only, no model calls."""

from __future__ import annotations

import pytest

from backend.router.deterministic import deterministic_route
from backend.router.schemas import IntentEnum, RouterInput, RouterOutput


# ====================================================================
# Router schemas
# ====================================================================


class TestRouterInput:
    def test_valid_input(self) -> None:
        inp = RouterInput(message_vi="Tim laptop gaming duoi 800 do")
        assert inp.message_vi == "Tim laptop gaming duoi 800 do"
        assert inp.conversation_context == []

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ValueError):
            RouterInput(message_vi="")

    def test_with_context(self) -> None:
        inp = RouterInput(
            message_vi="Tim laptop",
            conversation_context=[{"role": "user", "content": "hello"}],
        )
        assert len(inp.conversation_context) == 1


class TestRouterOutput:
    def test_search_deals_output(self) -> None:
        out = RouterOutput(
            intent=IntentEnum.SEARCH_DEALS,
            query_en="gaming laptop under 800 dollars",
            source="All",
            confidence=0.7,
            needs_tool=True,
        )
        assert out.intent == IntentEnum.SEARCH_DEALS
        assert out.needs_tool is True

    def test_unsupported_output(self) -> None:
        out = RouterOutput(
            intent=IntentEnum.UNSUPPORTED,
            query_en="",
            confidence=0.3,
            needs_tool=False,
        )
        assert out.intent == IntentEnum.UNSUPPORTED
        assert out.needs_tool is False
        assert out.query_en == ""


# ====================================================================
# Intent detection
# ====================================================================


class TestSearchDealsDetection:
    """Common Vietnamese shopping queries → search_deals."""

    def test_tim_laptop_gaming(self) -> None:
        out = deterministic_route("Tim laptop gaming duoi 800 do")
        assert out.intent == IntentEnum.SEARCH_DEALS
        assert out.needs_tool is True

    def test_mua_dien_thoai(self) -> None:
        out = deterministic_route("Mua dien thoai Samsung gia re")
        assert out.intent == IntentEnum.SEARCH_DEALS

    def test_tai_nghe_bluetooth(self) -> None:
        out = deterministic_route("Tim tai nghe Bluetooth khong day")
        assert out.intent == IntentEnum.SEARCH_DEALS

    def test_deal_tivi(self) -> None:
        out = deterministic_route("Co deal nao tot cho tivi 55 inch khong")
        assert out.intent == IntentEnum.SEARCH_DEALS

    def test_chuot_gaming(self) -> None:
        out = deterministic_route("Can mua chuot gaming")
        assert out.intent == IntentEnum.SEARCH_DEALS

    def test_laptop_van_phong(self) -> None:
        out = deterministic_route("Tim laptop cho sinh vien duoi 500")
        assert out.intent == IntentEnum.SEARCH_DEALS

    def test_ssd_1tb(self) -> None:
        out = deterministic_route("Mua o cung SSD 1TB")
        assert out.intent == IntentEnum.SEARCH_DEALS


class TestUnsupportedDetection:
    """Queries with no shopping intent → unsupported."""

    def test_greeting(self) -> None:
        out = deterministic_route("Xin chao ban")
        assert out.intent == IntentEnum.UNSUPPORTED
        assert out.needs_tool is False
        assert out.query_en == ""

    def test_chitchat(self) -> None:
        out = deterministic_route("Hom nay thoi tiet the nao")
        assert out.intent == IntentEnum.UNSUPPORTED

    def test_ambiguous(self) -> None:
        out = deterministic_route("Toi can giup do")
        assert out.intent == IntentEnum.UNSUPPORTED


# ====================================================================
# Query extraction
# ====================================================================


class TestQueryExtraction:
    """English query is extracted from Vietnamese messages."""

    def test_preserves_product_terms(self) -> None:
        out = deterministic_route("Tim laptop gaming")
        assert "laptop" in out.query_en.lower()
        assert "gaming" in out.query_en.lower()

    def test_vi_to_en_category(self) -> None:
        out = deterministic_route("Mua dien thoai")
        assert "phone" in out.query_en.lower()

    def test_vi_to_en_headphones(self) -> None:
        out = deterministic_route("Tim tai nghe")
        assert "headphones" in out.query_en.lower()

    def test_strips_stop_words(self) -> None:
        out = deterministic_route("Tim cho toi mot cai laptop")
        # Stop words "cho", "toi", "mot", "cai" should be stripped
        assert "cho" not in out.query_en.lower().split()
        assert "toi" not in out.query_en.lower().split()


# ====================================================================
# Price pattern detection
# ====================================================================


class TestPricePatterns:
    """Vietnamese price expressions → English price tokens."""

    def test_duoi_pattern(self) -> None:
        out = deterministic_route("Tim laptop duoi 800 do")
        assert "under 800 dollars" in out.query_en.lower()

    def test_tren_pattern(self) -> None:
        out = deterministic_route("Tim laptop tren 1000 usd")
        assert "above 1000 dollars" in out.query_en.lower()

    def test_khoang_pattern(self) -> None:
        out = deterministic_route("Tim laptop khoang 500 do")
        assert "around 500 dollars" in out.query_en.lower()


# ====================================================================
# Source detection
# ====================================================================


class TestSourceDetection:
    """Source preference extracted from message."""

    def test_amazon_mentioned(self) -> None:
        out = deterministic_route("Tim laptop tren Amazon duoi 800")
        assert out.source == "Amazon"

    def test_bestbuy_mentioned(self) -> None:
        out = deterministic_route("Tim laptop tren Best Buy")
        assert out.source == "BestBuy"

    def test_both_defaults_to_all(self) -> None:
        out = deterministic_route("Tim laptop tren Amazon va BestBuy")
        assert out.source == "All"

    def test_no_source_defaults_to_all(self) -> None:
        out = deterministic_route("Tim laptop gaming")
        assert out.source == "All"


# ====================================================================
# Confidence
# ====================================================================


class TestConfidence:
    """Confidence values are in expected ranges."""

    def test_search_deals_has_higher_confidence(self) -> None:
        out = deterministic_route("Tim laptop gaming")
        assert out.intent == IntentEnum.SEARCH_DEALS
        assert out.confidence >= 0.5

    def test_unsupported_has_lower_confidence(self) -> None:
        out = deterministic_route("Xin chao")
        assert out.intent == IntentEnum.UNSUPPORTED
        assert out.confidence <= 0.5

    def test_confidence_in_range(self) -> None:
        """All outputs have confidence in [0.0, 1.0]."""
        queries = [
            "Tim laptop gaming duoi 800 do",
            "Xin chao ban",
            "Mua dien thoai Samsung",
            "Co deal nao tot khong",
        ]
        for q in queries:
            out = deterministic_route(q)
            assert 0.0 <= out.confidence <= 1.0, f"Bad confidence for: {q}"
