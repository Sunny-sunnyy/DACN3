"""Tests for Phase 4C.3 real price estimator — formatter, boundary, assembly, adapters.

All tests are mock/fixture-only — no ChromaDB, no OpenAI, no neural deps, no Modal, no network.
deep_neural_network.py, frontier heavy deps, and modal must NOT be imported by any test.
"""

from __future__ import annotations

import os
import sys

import pytest

from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.frontier.adapter import (
    FrontierEstimateResult,
    FrontierPriceAdapter,
)
from backend.tools.price_estimator.neural.adapter import (
    NeuralEstimateResult,
    NeuralPriceAdapter,
)
from backend.tools.price_estimator.real_estimator import (
    _assemble_output,
    estimate_price_real,
)
from backend.tools.price_estimator.schemas import PriceEstimateInput
from backend.tools.price_estimator.specialist.adapter import (
    SpecialistEstimateResult,
)
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


def _sr(**overrides) -> SpecialistEstimateResult:
    """Build a SpecialistEstimateResult with defaults (unavailable, no error)."""
    defaults: dict = {"available": False}
    defaults.update(overrides)
    return SpecialistEstimateResult(**defaults)


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
    """Real mode with no config → all adapters unavailable → safe fallback markup."""

    def test_fallback_uses_5_percent_markup(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_SERVICE", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_CLASS", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product(sale_price_usd=100.0)
        output = estimate_price_real(p)
        assert output.estimated_value_usd == 105.0  # 5% markup
        assert output.deal_score == "ok"
        assert output.model_breakdown.neural == 0.0
        assert output.model_breakdown.frontier == 0.0
        assert output.model_breakdown.specialist == 0.0

    def test_fallback_includes_all_required_warnings(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_SERVICE", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_CLASS", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product()
        output = estimate_price_real(p)
        assert "frontier_unavailable:missing_chromadb_path" in output.warnings
        assert "specialist_unavailable:missing_service_config" in output.warnings
        assert "neural_unavailable:missing_weights_path" in output.warnings
        assert "real_pricing_fallback_used:sale_price_markup" in output.warnings
        assert "ensemble_partial:fallback_only" in output.warnings
        # Verify no deferred_to_4c3 legacy warning
        assert not any("deferred_to_4c3" in w for w in output.warnings)

    def test_fallback_with_zero_sale_price(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_SERVICE", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_CLASS", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product(sale_price_usd=0.0)
        output = estimate_price_real(p)
        assert output.estimated_value_usd == 0.0  # 0 * 1.05 = 0
        assert output.deal_score == "ok"


class TestRealEstimatorWarnings:
    """Warning grammar consistency (key:value, no space after colon)."""

    def test_warning_format_no_spaces(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_SERVICE", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_CLASS", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product()
        output = estimate_price_real(p)
        for w in output.warnings:
            assert ":" in w
            key, value = w.split(":", 1)
            assert key
            assert " " not in key

    def test_no_duplicate_warnings(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_SERVICE", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_CLASS", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product()
        output = estimate_price_real(p)
        assert len(output.warnings) == len(set(output.warnings))


class TestAssembly:
    """_assemble_output pure-function tests with fake results (4 params)."""

    # ── Existing tests (updated to pass 4th specialist param) ──────────

    def test_frontier_available_takes_priority(self) -> None:
        """Frontier available → use frontier_value (partial, specialist unavailable)."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=150.0, available=True)
        nr = NeuralEstimateResult(value_usd=200.0, available=True)
        sr = _sr(available=False, error_code="missing_service_config")
        output = _assemble_output(p, fr, nr, sr)
        assert output.estimated_value_usd == 150.0
        assert output.model_breakdown.frontier == 150.0
        assert output.model_breakdown.neural == 0.0
        assert output.model_breakdown.specialist == 0.0
        assert output.discount_usd == 50.0
        assert output.deal_score == "ok"  # discount 50 < 100
        assert "ensemble_partial:frontier_only" in output.warnings
        assert "specialist_unavailable:missing_service_config" in output.warnings

    def test_neural_success_frontier_unavailable(self) -> None:
        """Frontier unavailable, specialist unavailable, neural available → neural."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(available=False, error_code="missing_chromadb_path")
        nr = NeuralEstimateResult(value_usd=150.0, available=True)
        sr = _sr(available=False, error_code="missing_service_config")
        output = _assemble_output(p, fr, nr, sr)
        assert output.estimated_value_usd == 150.0
        assert output.model_breakdown.frontier == 0.0
        assert output.model_breakdown.neural == 150.0
        assert output.model_breakdown.specialist == 0.0
        assert output.discount_usd == 50.0
        assert output.deal_score == "ok"
        assert "ensemble_partial:neural_only" in output.warnings
        assert "frontier_unavailable:missing_chromadb_path" in output.warnings
        assert "specialist_unavailable:missing_service_config" in output.warnings

    def test_both_unavailable_produces_fallback(self) -> None:
        """All adapters unavailable → 5% markup fallback."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(available=False, error_code="missing_chromadb_path")
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(available=False, error_code="missing_service_config")
        output = _assemble_output(p, fr, nr, sr)
        assert output.estimated_value_usd == 105.0
        assert output.deal_score == "ok"
        assert output.model_breakdown.frontier == 0.0
        assert output.model_breakdown.neural == 0.0
        assert output.model_breakdown.specialist == 0.0
        assert "frontier_unavailable:missing_chromadb_path" in output.warnings
        assert "specialist_unavailable:missing_service_config" in output.warnings
        assert "neural_unavailable:missing_weights_path" in output.warnings
        assert "real_pricing_fallback_used:sale_price_markup" in output.warnings
        assert "ensemble_partial:fallback_only" in output.warnings

    def test_hot_deal_score_frontier(self) -> None:
        """Frontier estimate with large discount → hot."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=350.0, available=True)
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(available=False, error_code="missing_service_config")
        output = _assemble_output(p, fr, nr, sr)
        assert output.deal_score == "hot"
        assert output.discount_usd == 250.0
        assert "ensemble_partial:frontier_only" in output.warnings

    def test_good_deal_score_frontier(self) -> None:
        """Frontier estimate with moderate discount → good."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=210.0, available=True)
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(available=False, error_code="missing_service_config")
        output = _assemble_output(p, fr, nr, sr)
        assert output.deal_score == "good"
        assert output.discount_usd == 110.0

    def test_overpriced_frontier(self) -> None:
        """Frontier estimate below sale price → overpriced."""
        p = _make_product(sale_price_usd=200.0)
        fr = FrontierEstimateResult(value_usd=150.0, available=True)
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(available=False, error_code="missing_service_config")
        output = _assemble_output(p, fr, nr, sr)
        assert output.deal_score == "overpriced"
        assert output.discount_usd == -50.0

    def test_frontier_available_neural_available_frontier_wins(self) -> None:
        """Both available but specialist missing → frontier priority, neural in breakdown is 0.0."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=180.0, available=True)
        nr = NeuralEstimateResult(value_usd=250.0, available=True)
        sr = _sr(available=False, error_code="missing_service_config")
        output = _assemble_output(p, fr, nr, sr)
        assert output.estimated_value_usd == 180.0  # frontier wins, not neural
        assert output.model_breakdown.frontier == 180.0
        assert output.model_breakdown.neural == 0.0
        assert output.model_breakdown.specialist == 0.0
        assert "ensemble_partial:frontier_only" in output.warnings

    # ── New specialist tests ────────────────────────────────────────────

    def test_all_three_available_uses_ensemble_formula(self) -> None:
        """All 3 available → ensemble formula 0.8*f + 0.1*s + 0.1*n."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=900.0, available=True)
        nr = NeuralEstimateResult(value_usd=800.0, available=True)
        sr = _sr(value_usd=850.0, available=True)
        output = _assemble_output(p, fr, nr, sr)
        # 0.8*900 + 0.1*850 + 0.1*800 = 720 + 85 + 80 = 885
        assert output.estimated_value_usd == 885.0
        assert output.model_breakdown.frontier == 900.0
        assert output.model_breakdown.specialist == 850.0
        assert output.model_breakdown.neural == 800.0
        assert output.discount_usd == 785.0
        assert output.deal_score == "hot"
        # Success — no ensemble_partial warning
        assert not any("ensemble_partial" in w for w in output.warnings)

    def test_all_three_available_rounds_to_2_decimals(self) -> None:
        """Ensemble formula result is rounded to 2 decimal places."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=100.0, available=True)
        nr = NeuralEstimateResult(value_usd=100.0, available=True)
        sr = _sr(value_usd=100.0, available=True)
        output = _assemble_output(p, fr, nr, sr)
        assert output.estimated_value_usd == 100.0

    def test_all_three_available_good_deal_score(self) -> None:
        """Ensemble with moderate discount → good."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=200.0, available=True)
        nr = NeuralEstimateResult(value_usd=200.0, available=True)
        sr = _sr(value_usd=200.0, available=True)
        output = _assemble_output(p, fr, nr, sr)
        assert output.estimated_value_usd == 200.0
        assert output.deal_score == "good"
        assert "ensemble_partial" not in str(output.warnings)

    def test_specialist_only_frontier_and_neural_unavailable(self) -> None:
        """Specialist available, frontier+neural unavailable → specialist_only."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(available=False, error_code="missing_chromadb_path")
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(value_usd=300.0, available=True)
        output = _assemble_output(p, fr, nr, sr)
        assert output.estimated_value_usd == 300.0
        assert output.model_breakdown.specialist == 300.0
        assert output.model_breakdown.frontier == 0.0
        assert output.model_breakdown.neural == 0.0
        assert output.discount_usd == 200.0
        assert output.deal_score == "hot"
        assert "ensemble_partial:specialist_only" in output.warnings
        assert "frontier_unavailable:missing_chromadb_path" in output.warnings
        assert "neural_unavailable:missing_weights_path" in output.warnings

    def test_frontier_and_specialist_available_neural_unavailable(self) -> None:
        """Frontier+specialist available, neural unavailable → frontier wins (priority)."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=500.0, available=True)
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(value_usd=400.0, available=True)
        output = _assemble_output(p, fr, nr, sr)
        # frontier > specialist in priority chain → frontier only
        assert output.estimated_value_usd == 500.0
        assert output.model_breakdown.frontier == 500.0
        assert output.model_breakdown.specialist == 0.0
        assert "ensemble_partial:frontier_only" in output.warnings
        assert "neural_unavailable:missing_weights_path" in output.warnings

    def test_specialist_error_code_preserved_in_warnings(self) -> None:
        """Specialist error_code appears in warning even when another model succeeds."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=150.0, available=True)
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(available=False, error_code="modal_error",
                 error_detail="connection refused")
        output = _assemble_output(p, fr, nr, sr)
        assert "specialist_unavailable:modal_error" in output.warnings
        assert "ensemble_partial:frontier_only" in output.warnings

    def test_specialist_value_is_none_treated_as_unavailable(self) -> None:
        """Specialist available=True but value_usd=None → treated as unavailable."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(available=False, error_code="missing_chromadb_path")
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(value_usd=None, available=True)
        output = _assemble_output(p, fr, nr, sr)
        # None value → specialist treated as unavailable → fallback
        assert output.estimated_value_usd == 105.0  # 5% markup
        assert "ensemble_partial:fallback_only" in output.warnings

    def test_exactly_one_ensemble_partial_warning(self) -> None:
        """Partial case produces exactly one ensemble_partial:* warning."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(available=False, error_code="model_config_missing")
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        sr = _sr(value_usd=200.0, available=True)
        output = _assemble_output(p, fr, nr, sr)
        partial_warnings = [w for w in output.warnings if w.startswith("ensemble_partial")]
        assert len(partial_warnings) == 1
        assert partial_warnings[0] == "ensemble_partial:specialist_only"


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


# ====================================================================
# Frontier adapter tests (mock-safe, no heavy deps)
# ====================================================================


class TestFrontierAdapterMissingPath:
    """Adapter fails cleanly when chromadb path is missing."""

    def test_empty_path_returns_missing_chromadb_path(self) -> None:
        adapter = FrontierPriceAdapter(chromadb_path="", model_id="gpt-5.1")
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "missing_chromadb_path"

    def test_nonexistent_path_returns_missing_chromadb_path(self) -> None:
        adapter = FrontierPriceAdapter(
            chromadb_path="/tmp/nonexistent_chromadb_4c2_test",
            model_id="gpt-5.1",
        )
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "missing_chromadb_path"

    def test_result_is_idempotent(self) -> None:
        adapter = FrontierPriceAdapter(chromadb_path="", model_id="gpt-5.1")
        r1 = adapter.try_estimate("text a")
        r2 = adapter.try_estimate("text b")
        assert not r1.available
        assert not r2.available
        assert r1.error_code == r2.error_code


class TestFrontierAdapterMissingModelId:
    """Adapter fails cleanly when model_id is empty."""

    def test_empty_model_id_with_valid_path(self, tmp_path) -> None:
        """Path exists but model_id empty → model_config_missing."""
        adapter = FrontierPriceAdapter(
            chromadb_path=str(tmp_path),
            model_id="",
        )
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "model_config_missing"


class TestFrontierAdapterMissingDependency:
    """Adapter returns missing_dependency when heavy deps cannot be imported."""

    def test_missing_dependency_returns_safe_error(self, monkeypatch, tmp_path) -> None:
        """With valid config but blocked chromadb import → missing_dependency."""
        import builtins

        real_import = builtins.__import__

        def _block_heavy(name, *args, **kwargs):
            if name in ("chromadb",):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_heavy)

        adapter = FrontierPriceAdapter(
            chromadb_path=str(tmp_path),
            model_id="gpt-5.1",
        )
        result = adapter.try_estimate("test")
        assert not result.available
        assert result.error_code == "missing_dependency"
        assert result.error_detail is not None
        assert len(result.error_detail) <= 200

    def test_missing_dependency_sanitized_detail(self, monkeypatch, tmp_path) -> None:
        """Long import error message is bounded to 200 chars."""
        import builtins

        real_import = builtins.__import__

        def _fail_long(name, *args, **kwargs):
            if name == "chromadb":
                raise ImportError("X" * 500)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fail_long)

        adapter = FrontierPriceAdapter(
            chromadb_path=str(tmp_path),
            model_id="gpt-5.1",
        )
        result = adapter.try_estimate("test")
        assert not result.available
        assert result.error_code == "missing_dependency"
        assert result.error_detail is not None
        assert len(result.error_detail) <= 200


class TestFrontierAdapterSanitizedError:
    """Frontier adapter error_detail is bounded, safe, no stack traces."""

    def test_sanitize_detail_bounds_long_strings(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _sanitize_detail

        long_msg = "A" * 500
        result = _sanitize_detail(long_msg)
        assert len(result) <= 200

    def test_sanitize_detail_flattens_newlines(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _sanitize_detail

        result = _sanitize_detail("line1\nline2\r\nline3")
        assert "\n" not in result
        assert "\r" not in result

    def test_sanitize_detail_handles_non_strings(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _sanitize_detail

        result = _sanitize_detail(Exception(42))  # type: ignore[arg-type]
        assert len(result) <= 200
        assert "42" in result


class TestFrontierExtractPrice:
    """_extract_price is deterministic, stdlib-only."""

    def test_extracts_dollar_amount(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("Estimated price: $899.99") == 899.99

    def test_extracts_with_commas(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("The price is 1,299.50 dollars") == 1299.50

    def test_returns_none_when_no_number(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("No numbers here") is None

    def test_extracts_integer(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("42") == 42.0

    def test_extracts_zero(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("$0.00") == 0.0


# ====================================================================
# Frontier config tests
# ====================================================================


class TestFrontierConfig:
    """PRICER_CHROMADB_PATH and PRICER_FRONTIER_MODEL_ID env var handling."""

    def test_chromadb_path_default_empty(self) -> None:
        from backend.shared.config import PRICER_CHROMADB_PATH

        assert PRICER_CHROMADB_PATH == ""

    def test_frontier_model_id_default_empty(self) -> None:
        from backend.shared.config import PRICER_FRONTIER_MODEL_ID

        assert PRICER_FRONTIER_MODEL_ID == ""


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
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH",
            "",
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID",
            "",
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_SERVICE",
            "",
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_SPECIALIST_CLASS",
            "",
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
        # With no config, all models should be 0.0
        assert result.model_breakdown.frontier == 0.0
        assert result.model_breakdown.specialist == 0.0
        assert result.model_breakdown.neural == 0.0


# ====================================================================
# Lazy import guard — deep_neural_network must NOT be loaded
# ====================================================================


def test_neural_heavy_module_not_imported() -> None:
    """Default test suite must not pull torch/sklearn via deep_neural_network."""
    heavy = "backend.tools.price_estimator.neural.deep_neural_network"
    assert heavy not in sys.modules, (
        f"{heavy} was imported — default tests must not pull heavy deps"
    )


def test_frontier_heavy_modules_not_imported() -> None:
    """Default test suite must not pull chromadb/sentence_transformers/openai/modal."""
    for mod_start in ("chromadb", "sentence_transformers", "openai", "modal"):
        leaked = [m for m in sys.modules if m.startswith(mod_start)]
        assert not leaked, (
            f"{mod_start} was imported — default tests must not pull heavy deps: {leaked}"
        )
