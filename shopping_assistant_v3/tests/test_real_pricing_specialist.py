"""Tests for Phase 4C.3 specialist adapter — mock-only, no Modal.

All tests are mock/fixture-only — no Modal, no network, no model calls.
modal must NOT be imported by any test.
"""

from __future__ import annotations

import sys

import pytest

from backend.tools.price_estimator.specialist.adapter import (
    SpecialistEstimateResult,
    SpecialistPriceAdapter,
    _sanitize_detail,
)


# ====================================================================
# SpecialistEstimateResult tests
# ====================================================================


class TestSpecialistEstimateResult:
    """Dataclass default values and behavior."""

    def test_default_values(self) -> None:
        result = SpecialistEstimateResult()
        assert result.value_usd is None
        assert result.available is False
        assert result.error_code is None
        assert result.error_detail is None

    def test_available_with_value(self) -> None:
        result = SpecialistEstimateResult(value_usd=150.0, available=True)
        assert result.value_usd == 150.0
        assert result.available is True
        assert result.error_code is None

    def test_unavailable_with_error_code(self) -> None:
        result = SpecialistEstimateResult(
            available=False,
            error_code="missing_service_config",
            error_detail="PRICER_SPECIALIST_SERVICE is not set",
        )
        assert result.value_usd is None
        assert result.available is False
        assert result.error_code == "missing_service_config"
        assert result.error_detail is not None


# ====================================================================
# Specialist adapter — missing config
# ====================================================================


class TestSpecialistAdapterMissingConfig:
    """Adapter fails cleanly when service/class config is empty."""

    def test_empty_service_name_returns_missing_service_config(self) -> None:
        adapter = SpecialistPriceAdapter(service_name="", class_name="Pricer")
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "missing_service_config"

    def test_empty_class_name_returns_missing_service_config(self) -> None:
        adapter = SpecialistPriceAdapter(
            service_name="pricer-service", class_name=""
        )
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "missing_service_config"

    def test_both_empty_returns_missing_service_config(self) -> None:
        adapter = SpecialistPriceAdapter(service_name="", class_name="")
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "missing_service_config"

    def test_result_is_idempotent(self) -> None:
        adapter = SpecialistPriceAdapter(service_name="", class_name="")
        r1 = adapter.try_estimate("text a")
        r2 = adapter.try_estimate("text b")
        assert not r1.available
        assert not r2.available
        assert r1.error_code == r2.error_code


# ====================================================================
# Specialist adapter — missing dependency
# ====================================================================


class TestSpecialistAdapterMissingDependency:
    """Adapter returns missing_dependency when modal cannot be imported."""

    def test_missing_dependency_returns_safe_error(
        self, monkeypatch
    ) -> None:
        """With valid config but blocked modal import → missing_dependency."""
        import builtins

        real_import = builtins.__import__

        def _block_modal(name, *args, **kwargs):
            if name in ("modal",):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_modal)

        adapter = SpecialistPriceAdapter(
            service_name="pricer-service",
            class_name="Pricer",
        )
        result = adapter.try_estimate("test")
        assert not result.available
        assert result.error_code == "missing_dependency"
        assert result.error_detail is not None
        assert len(result.error_detail) <= 200

    def test_missing_dependency_sanitized_detail(
        self, monkeypatch
    ) -> None:
        """Long import error message is bounded to 200 chars."""
        import builtins

        real_import = builtins.__import__

        def _fail_long(name, *args, **kwargs):
            if name == "modal":
                raise ImportError("X" * 500)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fail_long)

        adapter = SpecialistPriceAdapter(
            service_name="pricer-service",
            class_name="Pricer",
        )
        result = adapter.try_estimate("test")
        assert not result.available
        assert result.error_code == "missing_dependency"
        assert result.error_detail is not None
        assert len(result.error_detail) <= 200


# ====================================================================
# Sanitized error detail
# ====================================================================


class TestSpecialistAdapterSanitizedError:
    """Adapter error_detail is bounded, safe, no stack traces."""

    def test_sanitize_detail_bounds_long_strings(self) -> None:
        long_msg = "A" * 500
        result = _sanitize_detail(long_msg)
        assert len(result) <= 200

    def test_sanitize_detail_flattens_newlines(self) -> None:
        result = _sanitize_detail("line1\nline2\r\nline3")
        assert "\n" not in result
        assert "\r" not in result

    def test_sanitize_detail_handles_non_strings(self) -> None:
        result = _sanitize_detail(Exception(42))  # type: ignore[arg-type]
        assert len(result) <= 200
        assert "42" in result


# ====================================================================
# Config tests
# ====================================================================


class TestSpecialistConfig:
    """PRICER_SPECIALIST_SERVICE and PRICER_SPECIALIST_CLASS env var handling."""

    def test_service_default_empty(self) -> None:
        from backend.shared.config import PRICER_SPECIALIST_SERVICE

        assert PRICER_SPECIALIST_SERVICE == ""

    def test_class_default_empty(self) -> None:
        from backend.shared.config import PRICER_SPECIALIST_CLASS

        assert PRICER_SPECIALIST_CLASS == ""


# ====================================================================
# Lazy import guard — modal must NOT be loaded
# ====================================================================


def test_specialist_heavy_module_not_imported() -> None:
    """Default test suite must not pull modal."""
    leaked = [m for m in sys.modules if m.startswith("modal")]
    assert not leaked, (
        f"modal was imported — default tests must not pull specialist deps: {leaked}"
    )
