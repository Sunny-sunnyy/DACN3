"""Specialist Price Adapter — lazy-loading wrapper for Modal fine-tuned estimator.

Module-level imports are stdlib only. The heavy dependency (modal) is
imported lazily inside _load() on first try_estimate() call. This keeps
the mock path free of Modal deps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("shopping_assistant_v3.specialist")


@dataclass
class SpecialistEstimateResult:
    """Result of a specialist price estimation attempt.

    When available=False, error_code describes the failure mode using a
    bounded grammar. error_detail is capped at 200 chars and must never
    contain raw exceptions, stack traces, or secrets.
    """

    value_usd: float | None = None
    available: bool = False
    error_code: str | None = None
    error_detail: str | None = None


def _sanitize_detail(raw: str) -> str:
    """Return a bounded, safe detail string (max 200 chars, single line)."""
    cleaned = str(raw).replace("\n", " ").replace("\r", "").strip()
    if len(cleaned) > 200:
        cleaned = cleaned[:197] + "..."
    return cleaned


class SpecialistPriceAdapter:
    """Lazy-loading adapter for the Modal fine-tuned specialist estimator.

    Heavy dependency (modal) is imported only when try_estimate() is first
    called — never at module import time.

    The adapter connects to a Modal-deployed pricer service via
    modal.Cls.from_name(). If the service is unavailable, config is missing,
    or modal is not installed, try_estimate() returns SpecialistEstimateResult
    with available=False and a machine-readable error_code.

    Usage:
        adapter = SpecialistPriceAdapter(
            service_name="pricer-service",
            class_name="Pricer",
        )
        result = adapter.try_estimate("Title: Laptop ...")
        if result.available:
            print(result.value_usd)
    """

    def __init__(self, service_name: str, class_name: str) -> None:
        """Store config. No heavy imports, no Modal connection at init."""
        self._service_name = service_name
        self._class_name = class_name
        self._pricer = None       # Modal Pricer instance or None
        self._init_error: SpecialistEstimateResult | None = None
        self._init_attempted = False

    def try_estimate(self, text: str) -> SpecialistEstimateResult:
        """Run specialist inference. Lazy-loads modal + connects on first call.

        Never raises — failures become SpecialistEstimateResult metadata.
        """
        if not self._init_attempted:
            self._init_attempted = True
            self._load()

        if self._init_error is not None:
            return self._init_error

        try:
            result = self._pricer.price.remote(text)
            value = float(max(0, result))
            return SpecialistEstimateResult(
                value_usd=round(value, 2),
                available=True,
            )

        except Exception as exc:
            logger.warning(
                "Specialist inference failed: %s", _sanitize_detail(str(exc))
            )
            return SpecialistEstimateResult(
                available=False,
                error_code="modal_error",
                error_detail=_sanitize_detail(str(exc)),
            )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Lazy init: validate config, import modal, connect to service.

        Sets self._init_error on any failure. Called once by try_estimate().
        """
        # Step 1: validate config
        if not self._service_name or not self._class_name:
            self._init_error = SpecialistEstimateResult(
                available=False,
                error_code="missing_service_config",
                error_detail=(
                    "PRICER_SPECIALIST_SERVICE or PRICER_SPECIALIST_CLASS "
                    "is not set"
                ),
            )
            return

        # Step 2: lazy-import modal
        try:
            import modal  # noqa: F401
        except ImportError as exc:
            self._init_error = SpecialistEstimateResult(
                available=False,
                error_code="missing_dependency",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 3: connect to Modal service
        try:
            Pricer = modal.Cls.from_name(
                self._service_name, self._class_name
            )
            self._pricer = Pricer()
        except Exception as exc:
            self._init_error = SpecialistEstimateResult(
                available=False,
                error_code="modal_error",
                error_detail=_sanitize_detail(str(exc)),
            )
            return
