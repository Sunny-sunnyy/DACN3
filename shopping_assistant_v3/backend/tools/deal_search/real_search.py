"""Real search orchestrator for Phase 4B.

Dispatches to BestBuy and Amazon real search modules based on source filter.
Sequential execution for source="All": BestBuy first, then Amazon.

A source failure becomes a sanitized warning — partial results are returned
when at least one source succeeds. Only when all queried sources return
empty or fail is the output truly empty.
"""

from __future__ import annotations

import logging

from backend.tools.deal_search.bestbuy_search import search_bestbuy_real
from backend.tools.deal_search.amazon_search import search_amazon_real
from backend.tools.deal_search.schemas import (
    DealSearchInput,
    DealSearchOutput,
    ProductCandidate,
)

logger = logging.getLogger("shopping_assistant_v3.real_search")


def _source_list(source: str) -> str:
    """Return the grammar-compliant source_list value for no_products_found."""
    if source == "All":
        return "all_sources"
    elif source == "BestBuy":
        return "bestbuy_only"
    else:
        return "amazon_only"


def real_deal_search(input: DealSearchInput) -> DealSearchOutput:
    """Execute real deal search against Amazon and/or BestBuy.

    Sequential execution when source="All" (BestBuy first, then Amazon).
    Each source that fails adds a sanitized warning using bounded reason
    codes — the other source's results are preserved.

    Source filter is normal operation: no warning is emitted when a source
    is skipped due to the source field (e.g. source="Amazon" does not
    produce "bestbuy_skipped").

    Args:
        input: DealSearchInput with query_en, source filter, and limit.

    Returns:
        DealSearchOutput with products from all queried sources and
        sanitized bounded warnings.
    """
    all_products: list[ProductCandidate] = []
    all_warnings: list[str] = []
    bb_failed = False
    az_failed = False

    # --- BestBuy ---
    if input.source in ("All", "BestBuy"):
        bb_products, bb_warnings = search_bestbuy_real(
            query=input.query_en,
            max_results=input.max_results_per_source,
        )
        all_products.extend(bb_products)
        all_warnings.extend(bb_warnings)
        bb_failed = any(
            w.startswith("bestbuy_search_failed") for w in bb_warnings
        )
        logger.info(
            "real_search BestBuy: %d products, %d warnings",
            len(bb_products), len(bb_warnings),
        )

    # --- Amazon ---
    if input.source in ("All", "Amazon"):
        az_products, az_warnings = search_amazon_real(
            query=input.query_en,
            max_results=input.max_results_per_source,
        )
        all_products.extend(az_products)
        all_warnings.extend(az_warnings)
        az_failed = any(
            w.startswith("amazon_search_failed") for w in az_warnings
        )
        logger.info(
            "real_search Amazon: %d products, %d warnings",
            len(az_products), len(az_warnings),
        )

    # --- Cross-source partial results summary (source="All" only) ---
    if input.source == "All":
        if bb_failed and not az_failed:
            all_warnings.append(
                "partial_results: bestbuy_failed=true amazon_ok=true"
            )
        elif az_failed and not bb_failed:
            all_warnings.append(
                "partial_results: bestbuy_ok=true amazon_failed=true"
            )

    # --- Final emptiness check scoped to requested sources ---
    if not all_products:
        all_warnings.append(
            f"no_products_found: {_source_list(input.source)}"
        )

    logger.info(
        "real_search total: %d products, %d warnings",
        len(all_products), len(all_warnings),
    )
    return DealSearchOutput(products=all_products, warnings=all_warnings)
