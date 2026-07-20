"""Opt-in real search integration tests.

ALL tests are skipped by default. They require:
- ENABLE_REAL_SEARCH=true
- curl_cffi installed
- Live network access to Amazon.com and BestBuy.com

Run manually with:
  ENABLE_REAL_SEARCH=true uv run pytest tests/test_real_search.py -v
"""

from __future__ import annotations

import os

import pytest

from backend.tools.deal_search.schemas import DealSearchInput

REAL_SEARCH_ENABLED = (
    os.getenv("ENABLE_REAL_SEARCH", "false").strip().lower()
    in ("1", "true", "yes", "on")
)

pytestmark = pytest.mark.skipif(
    not REAL_SEARCH_ENABLED,
    reason="ENABLE_REAL_SEARCH is not true. Set ENABLE_REAL_SEARCH=true to run.",
)

# Allowed warning prefixes per bounded grammar.
_ALLOWED_WARNING_PREFIXES = (
    "bestbuy_search_failed:",
    "amazon_search_failed:",
    "bestbuy_no_results",
    "amazon_no_results",
    "bestbuy_no_sale_products",
    "amazon_no_sale_products",
    "amazon_features_limited:",
    "partial_results:",
    "no_products_found:",
)

# Banned substrings in warnings (safety check).
_BANNED_IN_WARNINGS = (
    "Traceback", "<html", "cookie", "Bearer ", "sk-",
)


def _validate_warnings(warnings: list[str]) -> None:
    """Assert all warnings use bounded grammar and contain no raw data."""
    for w in warnings:
        assert len(w) < 500, f"Warning too long ({len(w)} chars): {w[:100]}..."
        for banned in _BANNED_IN_WARNINGS:
            assert banned not in w, (
                f"Warning contains banned substring '{banned}': {w[:100]}..."
            )
        assert any(
            w.startswith(prefix) for prefix in _ALLOWED_WARNING_PREFIXES
        ), f"Warning does not match allowed grammar: {w[:100]}..."


def _validate_products(products) -> None:
    """Assert all products have required fields with valid values."""
    for p in products:
        assert p.source in ("Amazon", "BestBuy"), f"Bad source: {p.source}"
        assert p.title and len(p.title) > 0, "Missing title"
        assert p.sale_price_usd is not None and p.sale_price_usd > 0, (
            f"Bad sale_price_usd: {p.sale_price_usd}"
        )
        assert p.url and len(p.url) > 0, "Missing url"
        if p.source == "BestBuy":
            assert "bestbuy.com" in p.url
        elif p.source == "Amazon":
            assert "amazon.com" in p.url


class TestBestBuyRealSearch:
    """Live BestBuy search — requires network."""

    def test_search_returns_products_or_sanitized_warnings(self) -> None:
        from backend.tools.deal_search.bestbuy_search import (
            search_bestbuy_real,
        )

        products, warnings = search_bestbuy_real(
            query="laptop", max_results=3
        )
        _validate_warnings(warnings)
        if products:
            _validate_products(products)

    def test_no_results_for_nonsense_query(self) -> None:
        from backend.tools.deal_search.bestbuy_search import (
            search_bestbuy_real,
        )

        products, warnings = search_bestbuy_real(
            query="xyznonexistentproduct12345zzz", max_results=3
        )
        _validate_warnings(warnings)
        assert len(products) == 0
        assert any(
            w.startswith("bestbuy_no") for w in warnings
        ), f"Expected bestbuy_no_* warning, got: {warnings}"


class TestAmazonRealSearch:
    """Live Amazon search — requires network."""

    def test_search_returns_products_or_sanitized_warnings(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            search_amazon_real,
        )

        products, warnings = search_amazon_real(
            query="laptop", max_results=3
        )
        _validate_warnings(warnings)
        if products:
            _validate_products(products)

    def test_no_results_for_nonsense_query(self) -> None:
        from backend.tools.deal_search.amazon_search import (
            search_amazon_real,
        )

        products, warnings = search_amazon_real(
            query="xyznonexistentproduct12345zzz", max_results=3
        )
        _validate_warnings(warnings)
        assert len(products) == 0
        assert any(
            w.startswith("amazon_no") for w in warnings
        ), f"Expected amazon_no_* warning, got: {warnings}"


class TestRealSearchOrchestrator:
    """End-to-end real search dispatch — requires network."""

    def test_all_source_returns_results_or_clean_warnings(self) -> None:
        from backend.tools.deal_search.real_search import real_deal_search

        output = real_deal_search(
            DealSearchInput(
                query_en="laptop", source="All", max_results_per_source=2
            )
        )
        _validate_warnings(output.warnings)
        if output.products:
            _validate_products(output.products)
            sources = {p.source for p in output.products}
            assert len(sources) >= 1

    def test_source_filter_returns_only_requested_source(self) -> None:
        from backend.tools.deal_search.real_search import real_deal_search

        output = real_deal_search(
            DealSearchInput(
                query_en="headphones", source="Amazon",
                max_results_per_source=2,
            )
        )
        _validate_warnings(output.warnings)
        if output.products:
            for p in output.products:
                assert p.source == "Amazon"
        # No bestbuy_skipped warnings for normal source filter.
        assert not any(
            "bestbuy" in w for w in output.warnings
        ), f"Source filter should not produce bestbuy warnings: {output.warnings}"

    def test_nonsense_query_returns_no_products_found(self) -> None:
        from backend.tools.deal_search.real_search import real_deal_search

        output = real_deal_search(
            DealSearchInput(
                query_en="xyznonexistent987654321zzz", source="All",
                max_results_per_source=2,
            )
        )
        _validate_warnings(output.warnings)
        assert len(output.products) == 0
        assert any(
            w.startswith("no_products_found:") for w in output.warnings
        ), f"Expected no_products_found warning, got: {output.warnings}"

    def test_all_warnings_are_sanitized(self) -> None:
        from backend.tools.deal_search.real_search import real_deal_search

        output = real_deal_search(
            DealSearchInput(
                query_en="laptop", source="All", max_results_per_source=2,
            )
        )
        _validate_warnings(output.warnings)
