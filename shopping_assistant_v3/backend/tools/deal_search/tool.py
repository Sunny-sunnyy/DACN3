"""deal_search_tool — mock + real search implementations.

Phase 4A mock path (default): JSON fixture keyword matching.
Phase 4B real path (opt-in): ENABLE_REAL_SEARCH=true dispatches to
BestBuy and Amazon curl_cffi search modules.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.shared.config import ENABLE_REAL_SEARCH
from backend.tools.deal_search import real_search
from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput, ProductCandidate

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mock_products.json"


def _load_products() -> list[ProductCandidate]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [ProductCandidate(**item) for item in raw]


def _keyword_match(product: ProductCandidate, query: str) -> bool:
    """Case-insensitive ANY-token match in title or features.

    A product matches if at least one query token appears in its title or
    features. Empty query matches everything. Uses any-token (not all-token)
    so Vietnamese messages that have been normalized still match.
    """
    q = query.strip()
    if not q:
        return True
    searchable = product.title.lower()
    if product.features:
        searchable += " " + product.features.lower()
    tokens = q.split()
    return any(token in searchable for token in tokens)


def deal_search(input: DealSearchInput) -> DealSearchOutput:
    """Run a product search — mock (default) or real (opt-in).

    When ENABLE_REAL_SEARCH=false (default): keyword match against
    local JSON fixture products (Phase 4A mock path).

    When ENABLE_REAL_SEARCH=true: dispatch to BestBuy and Amazon
    real search via curl_cffi (Phase 4B real path).

    Args:
        input: DealSearchInput with query_en, source filter, and result limit.

    Returns:
        DealSearchOutput with matching products and any sanitized warnings.
    """
    if ENABLE_REAL_SEARCH:
        return real_search.real_deal_search(input)

    all_products = _load_products()
    warnings: list[str] = []

    # Filter by source.
    if input.source in ("Amazon", "BestBuy"):
        candidates = [p for p in all_products if p.source == input.source]
    else:
        candidates = list(all_products)

    # Filter by keyword match if query is provided.
    if input.query_en.strip():
        candidates = [p for p in candidates if _keyword_match(p, input.query_en)]

    if not candidates:
        return DealSearchOutput(
            products=[],
            warnings=[f"No products found for query: {input.query_en}"],
        )

    # Limit per source.
    per_source_limit = input.max_results_per_source
    by_source: dict[str, list[ProductCandidate]] = {}
    for p in candidates:
        by_source.setdefault(p.source, []).append(p)

    limited: list[ProductCandidate] = []
    for source_products in by_source.values():
        limited.extend(source_products[:per_source_limit])

    if len(candidates) > len(limited):
        warnings.append(
            f"Results truncated to {per_source_limit} per source. "
            f"Total: {len(candidates)} matched, returning {len(limited)}."
        )

    return DealSearchOutput(products=limited, warnings=warnings)
