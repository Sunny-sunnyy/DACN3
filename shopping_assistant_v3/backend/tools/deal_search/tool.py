"""deal_search_tool — mock implementation using JSON fixtures.

Phase 4A: always returns fixture data. Real search (Phase 4B) gated behind
ENABLE_REAL_SEARCH, which raises NotImplementedError in this phase.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.shared.config import ENABLE_REAL_SEARCH
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
    """Run a mock product search using local JSON fixtures.

    Args:
        input: DealSearchInput with query_en, source filter, and result limit.

    Returns:
        DealSearchOutput with matching products and any warnings.

    Raises:
        NotImplementedError: If ENABLE_REAL_SEARCH is True (Phase 4A mock-only).
    """
    if ENABLE_REAL_SEARCH:
        raise NotImplementedError(
            "Real search is not available in Phase 4A mock-only mode. "
            "Set ENABLE_REAL_SEARCH=false or wait for Phase 4B."
        )

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
