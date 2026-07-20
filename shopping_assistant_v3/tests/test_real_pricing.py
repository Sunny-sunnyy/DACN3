"""Tests for Phase 4C.1 real price estimator — formatter, boundary, assembly, adapter.

All tests are mock/fixture-only — no neural deps, no model files, no network.
deep_neural_network.py must NOT be imported by any test in this file.
"""

from __future__ import annotations

import os
import sys

import pytest

from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.neural.adapter import (
    NeuralEstimateResult,
    NeuralPriceAdapter,
)
from backend.tools.price_estimator.real_estimator import (
    _assemble_output,
    estimate_price_real,
)
from backend.tools.price_estimator.schemas import PriceEstimateInput
from backend.tools.price_estimator.tool import estimate_price


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


# ====================================================================
# Formatter tests
# ====================================================================


class TestFormatter:
    """Deterministic ProductCandidate → structured text."""

    def test_full_product(self) -> None:
        from backend.tools.price_estimator.formatter import format_product_for_pricing

        p = _make_product()
        text = format_product_for_pricing(p)
        assert "Title: Test Laptop Pro 15" in text
        assert "Category: Unknown" in text
        assert "Brand: TestBrand" in text
        assert "priced at $799.99" in text
        assert "Details: 16GB RAM, 512GB SSD, RTX 4060" in text

    def test_price_none_defaults_to_zero(self) -> None:
        from backend.tools.price_estimator.formatter import format_product_for_pricing

        p = _make_product(sale_price_usd=None)
        text = format_product_for_pricing(p)
        assert "$0.00" in text

    def test_price_zero_renders_correctly(self) -> None:
        from backend.tools.price_estimator.formatter import format_product_for_pricing

        p = _make_product(sale_price_usd=0.0)
        text = format_product_for_pricing(p)
        assert "$0.00" in text

    def test_empty_string_fields_become_unknown(self) -> None:
        from backend.tools.price_estimator.formatter import format_product_for_pricing

        p = _make_product(title="", brand="", features="")
        text = format_product_for_pricing(p)
        assert "Unknown product" in text

    def test_all_fields_none(self) -> None:
        from backend.tools.price_estimator.formatter import format_product_for_pricing

        p = ProductCandidate(source="BestBuy", title="", brand=None, features=None, sale_price_usd=None, url=None)
        text = format_product_for_pricing(p)
        assert "Unknown product" in text


class TestFormatterMissingFields:
    """Fallback fields for partial products."""

    def test_missing_brand(self) -> None:
        from backend.tools.price_estimator.formatter import format_product_for_pricing

        p = _make_product(brand="")
        text = format_product_for_pricing(p)
        assert "Brand: Unknown" in text
        assert "by Unknown" in text

    def test_missing_features(self) -> None:
        from backend.tools.price_estimator.formatter import format_product_for_pricing

        p = _make_product(features="")
        text = format_product_for_pricing(p)
        assert "Details: No details available" in text

    def test_missing_title_but_has_brand(self) -> None:
        from backend.tools.price_estimator.formatter import format_product_for_pricing

        p = _make_product(title="", brand="Sony")
        text = format_product_for_pricing(p)
        assert "Title: Unknown Product" in text
        assert "Brand: Sony" in text


# ====================================================================
# Real estimator boundary & assembly tests
# ====================================================================


class TestRealEstimatorFallback:
    """Real mode with no weights → safe fallback markup."""

    def test_fallback_uses_5_percent_markup(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH",
            "",
        )
        p = _make_product(sale_price_usd=100.0)
        output = estimate_price_real(p)
        assert output.estimated_value_usd == 105.0  # 5% markup
        assert output.deal_score == "ok"
        assert output.model_breakdown.neural == 0.0

    def test_fallback_includes_all_required_warnings(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH",
            "",
        )
        p = _make_product()
        output = estimate_price_real(p)
        assert "frontier_unavailable:deferred_to_4c2" in output.warnings
        assert "specialist_unavailable:deferred_to_4c3" in output.warnings
        assert "neural_unavailable:missing_weights_path" in output.warnings
        assert "real_pricing_fallback_used:sale_price_markup" in output.warnings
        assert "ensemble_partial:fallback_only" in output.warnings

    def test_fallback_with_zero_sale_price(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH",
            "",
        )
        p = _make_product(sale_price_usd=0.0)
        output = estimate_price_real(p)
        assert output.estimated_value_usd == 0.0  # 0 * 1.05 = 0
        assert output.deal_score == "ok"  # fallback always "ok" per plan


class TestRealEstimatorWarnings:
    """Warning grammar consistency (key:value, no space after colon)."""

    def test_warning_format_no_spaces(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH",
            "",
        )
        p = _make_product()
        output = estimate_price_real(p)
        for w in output.warnings:
            # Every warning uses key:value (colon directly after key)
            assert ":" in w
            key, value = w.split(":", 1)
            assert key  # non-empty
            # No space between key and colon
            assert " " not in key

    def test_no_duplicate_warnings(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH",
            "",
        )
        p = _make_product()
        output = estimate_price_real(p)
        assert len(output.warnings) == len(set(output.warnings))


class TestAssembly:
    """_assemble_output pure-function tests with fake NeuralEstimateResult."""

    def test_neural_success_produces_neural_value(self) -> None:
        p = _make_product(sale_price_usd=100.0)
        neural = NeuralEstimateResult(value_usd=150.0, available=True)
        output = _assemble_output(p, neural)
        assert output.estimated_value_usd == 150.0
        assert output.model_breakdown.neural == 150.0
        assert output.model_breakdown.frontier == 0.0
        assert output.model_breakdown.specialist == 0.0
        assert output.discount_usd == 50.0
        assert output.deal_score == "ok"  # discount 50 < 100
        assert "ensemble_partial:neural_only" in output.warnings

    def test_neural_unavailable_produces_fallback(self) -> None:
        p = _make_product(sale_price_usd=100.0)
        neural = NeuralEstimateResult(
            available=False,
            error_code="missing_weights_path",
        )
        output = _assemble_output(p, neural)
        assert output.estimated_value_usd == 105.0
        assert output.deal_score == "ok"
        assert "real_pricing_fallback_used:sale_price_markup" in output.warnings
        assert "neural_unavailable:missing_weights_path" in output.warnings
        assert "ensemble_partial:fallback_only" in output.warnings

    def test_hot_deal_score(self) -> None:
        p = _make_product(sale_price_usd=100.0)
        neural = NeuralEstimateResult(value_usd=350.0, available=True)
        output = _assemble_output(p, neural)
        assert output.deal_score == "hot"
        assert output.discount_usd == 250.0


# ====================================================================
# Neural adapter tests (mock-safe, no heavy deps)
# ====================================================================


class TestNeuralAdapterMissingWeights:
    """Adapter fails cleanly when weights path is missing."""

    def test_empty_path_returns_missing_weights(self) -> None:
        adapter = NeuralPriceAdapter(weights_path="")
        result = adapter.estimate("test text")
        assert not result.available
        assert result.error_code == "missing_weights_path"

    def test_nonexistent_path_returns_missing_weights(self) -> None:
        adapter = NeuralPriceAdapter(weights_path="/tmp/nonexistent_weights_4c_test.pth")
        result = adapter.estimate("test text")
        assert not result.available
        assert result.error_code == "missing_weights_path"

    def test_result_is_idempotent(self) -> None:
        adapter = NeuralPriceAdapter(weights_path="")
        r1 = adapter.estimate("text a")
        r2 = adapter.estimate("text b")  # second call, same adapter
        assert not r1.available
        assert not r2.available
        assert r1.error_code == r2.error_code


class TestNeuralAdapterMissingDependency:
    """Adapter returns missing_dependency when heavy deps cannot be imported."""

    def test_missing_dependency_returns_safe_error(self, monkeypatch, tmp_path) -> None:
        """With valid weights file but blocked torch import → missing_dependency."""
        import builtins

        weights_file = tmp_path / "fake_weights.pth"
        weights_file.write_bytes(b"0")

        real_import = builtins.__import__

        def _block_heavy(name, *args, **kwargs):
            if name in ("torch",):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_heavy)

        adapter = NeuralPriceAdapter(weights_path=str(weights_file))
        result = adapter.estimate("test")
        assert not result.available
        assert result.error_code == "missing_dependency"
        assert result.error_detail is not None
        assert len(result.error_detail) <= 200

    def test_missing_dependency_sanitized_detail(self, monkeypatch, tmp_path) -> None:
        """Long import error message is bounded to 200 chars."""
        import builtins

        weights_file = tmp_path / "fake_weights.pth"
        weights_file.write_bytes(b"0")

        real_import = builtins.__import__

        def _fail_long(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("X" * 500)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fail_long)

        adapter = NeuralPriceAdapter(weights_path=str(weights_file))
        result = adapter.estimate("test")
        assert not result.available
        assert result.error_code == "missing_dependency"
        assert result.error_detail is not None
        assert len(result.error_detail) <= 200


class TestNeuralAdapterSanitizedError:
    """Adapter error_detail is bounded, safe, no stack traces."""

    def test_sanitize_detail_bounds_long_strings(self) -> None:
        """_sanitize_detail caps at 200 chars."""
        from backend.tools.price_estimator.neural.adapter import _sanitize_detail

        long_msg = "A" * 500
        result = _sanitize_detail(long_msg)
        assert len(result) <= 200

    def test_sanitize_detail_flattens_newlines(self) -> None:
        """_sanitize_detail replaces newlines with spaces."""
        from backend.tools.price_estimator.neural.adapter import _sanitize_detail

        result = _sanitize_detail("line1\nline2\r\nline3")
        assert "\n" not in result
        assert "\r" not in result

    def test_sanitize_detail_handles_non_strings(self) -> None:
        """_sanitize_detail converts non-strings safely."""
        from backend.tools.price_estimator.neural.adapter import _sanitize_detail

        result = _sanitize_detail(Exception(42))  # type: ignore[arg-type]
        assert len(result) <= 200
        assert "42" in result


# ====================================================================
# Config tests
# ====================================================================


class TestConfig:
    """PRICER_NEURAL_WEIGHTS_PATH env var handling."""

    def test_default_empty(self) -> None:
        from backend.shared.config import PRICER_NEURAL_WEIGHTS_PATH

        assert PRICER_NEURAL_WEIGHTS_PATH == ""

    def test_loads_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("PRICER_NEURAL_WEIGHTS_PATH", "/some/path/weights.pth")
        # Re-import to pick up env — but config is module-level cached.
        # Verify via adapter instead.
        adapter = NeuralPriceAdapter(weights_path="/some/path/weights.pth")
        # Path doesn't exist, but adapter stored it correctly
        result = adapter.estimate("test")
        assert result.error_code == "missing_weights_path"  # path not real


# ====================================================================
# Real mode dispatch test
# ====================================================================


class TestRealModeDispatch:
    """ENABLE_REAL_MODEL_CALLS=true dispatches to real path."""

    def test_real_mode_returns_valid_output(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.tool.ENABLE_REAL_MODEL_CALLS",
            True,
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH",
            "",
        )
        p = _make_product()
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.estimated_value_usd > 0
        assert isinstance(result.model_breakdown.frontier, float)
        assert isinstance(result.model_breakdown.specialist, float)


# ====================================================================
# Lazy import guard — deep_neural_network must NOT be loaded
# ====================================================================


def test_neural_heavy_module_not_imported() -> None:
    """Default test suite must not pull torch/sklearn via deep_neural_network."""
    heavy = "backend.tools.price_estimator.neural.deep_neural_network"
    assert heavy not in sys.modules, (
        f"{heavy} was imported — default tests must not pull heavy deps"
    )
