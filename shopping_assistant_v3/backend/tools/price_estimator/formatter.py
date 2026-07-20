"""Deterministic ProductCandidate-to-text formatter for neural inference.

No model calls, no network, no file I/O. Replaces the LiteLLM Preprocessor
from segment4 with a fixed template that always produces structured output.
"""

from __future__ import annotations

from backend.tools.deal_search.schemas import ProductCandidate


def format_product_for_pricing(product: ProductCandidate) -> str:
    """Convert a ProductCandidate into structured text for neural inference.

    Returns a fixed-format string with fallback values for every missing field.
    Only returns "Unknown product" when title, brand, and features are all empty.

    Template:
        Title: {title or "Unknown Product"}
        Category: Unknown
        Brand: {brand or "Unknown"}
        Description: {title} by {brand}, priced at ${sale_price_usd}
        Details: {features or "No details available"}
    """
    title = (product.title or "").strip()
    brand = (product.brand or "").strip()
    features = (product.features or "").strip()
    price = product.sale_price_usd

    # Guard: all meaningful fields empty
    if not title and not brand and not features:
        return "Unknown product"

    safe_title = title if title else "Unknown Product"
    safe_brand = brand if brand else "Unknown"
    safe_features = features if features else "No details available"

    price_str = f"${price:.2f}" if price is not None else "$0.00"

    return (
        f"Title: {safe_title}\n"
        f"Category: Unknown\n"
        f"Brand: {safe_brand}\n"
        f"Description: {safe_title} by {safe_brand}, priced at {price_str}\n"
        f"Details: {safe_features}"
    )
