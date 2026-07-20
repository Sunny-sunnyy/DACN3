"""BestBuy real search — adapted from segment4/price_agents/bestbuy_deals.py.

Phase 4B: curl_cffi + internal APIs. No Playwright.
Product pages blocked from WSL2 (HTTP/2 + Akamai CDN). Uses:
1. Search page -> Apollo SSR cache -> skuIds + pdpUrls
2. priceBlocks API -> batch price, brand, onSale
3. v2 product API -> features, clean URL

Adapted functions (segment4 -> V3, copy+adapt, no runtime imports):
  _init_session           -> _create_session
  search_bestbuy          -> _parse_apollo_search_page (testable parser)
  get_price_blocks        -> _fetch_price_blocks
  get_product_details     -> _fetch_product_details
  search_filter_scrape_bestbuy -> search_bestbuy_real

Timeout note: BESTBUY_TIMEOUT is a per-request timeout applied to each
HTTP call, not a source-level deadline. One BestBuy search makes up to
1 (search) + 1 (priceBlocks) + max_results (product details) requests.
Worst-case wall time ~ BESTBUY_TIMEOUT * (2 + max_results).
Source-level deadline wrapping is deferred to a future hardening milestone.

Warning grammar (sanitized, bounded reason codes):
  bestbuy_search_failed: request_failed
  bestbuy_no_results
  bestbuy_no_sale_products
"""

from __future__ import annotations

import logging
import re
from typing import Any

try:
    from curl_cffi import requests as curl_requests
    _CURL_CFFI_AVAILABLE = True
except ImportError:
    curl_requests = None  # type: ignore[assignment]
    _CURL_CFFI_AVAILABLE = False

from backend.tools.deal_search.schemas import ProductCandidate

logger = logging.getLogger("shopping_assistant_v3.bestbuy_search")

BESTBUY_TIMEOUT = 15  # per-request timeout, not source-level deadline


# ---------------------------------------------------------------------------
# Testable parser (no network, no curl_cffi)
# ---------------------------------------------------------------------------


def _parse_apollo_search_page(html: str) -> list[dict[str, str]]:
    """Parse BestBuy search page HTML for Apollo SSR cache entries.

    Extracts unique (skuId, pdpUrl) pairs from inline JSON. Testable with
    saved HTML fixture — no network required.

    Args:
        html: Raw HTML from BestBuy /site/searchpage.jsp response.

    Returns:
        List of dicts with keys "skuId" and "pdpUrl".
    """
    products: dict[str, dict[str, str]] = {}
    all_skus = set(re.findall(r'"skuId":"(\d{5,8})"', html))

    for sku_id in all_skus:
        pattern = (
            rf'"skuId":"{sku_id}"\}},"pdpUrl":"'
            rf'(https://www\.bestbuy\.com/product/[^"]+)"'
        )
        for m in re.finditer(pattern, html):
            pdp_url = m.group(1)
            if "openbox" in pdp_url or "refurbished" in pdp_url:
                continue
            clean_url = re.sub(r"/sku/\d+/?$", "", pdp_url)
            products[sku_id] = {"skuId": sku_id, "pdpUrl": clean_url}
            break

    for sku_id in all_skus:
        if sku_id not in products:
            products[sku_id] = {"skuId": sku_id, "pdpUrl": ""}

    logger.debug("Apollo parse: %d unique SKUs from %d raw matches",
                 len(products), len(all_skus))
    return list(products.values())


# ---------------------------------------------------------------------------
# Network functions (require curl_cffi)
# ---------------------------------------------------------------------------


def _create_session() -> curl_requests.Session:
    """Create curl_cffi session with Chrome impersonation, bypass country splash."""
    session = curl_requests.Session(impersonate="chrome")
    session.get("https://www.bestbuy.com/?intl=nosplash", timeout=BESTBUY_TIMEOUT)
    return session


def _fetch_price_blocks(
    session: curl_requests.Session, sku_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Batch fetch price, brand, onSale from BestBuy /api/3.0/priceBlocks."""
    skus_param = ",".join(sku_ids)
    url = f"https://www.bestbuy.com/api/3.0/priceBlocks?skus={skus_param}"
    logger.debug("Fetching priceBlocks for %d SKUs", len(sku_ids))

    resp = session.get(
        url, timeout=BESTBUY_TIMEOUT, headers={"Accept": "application/json"}
    )

    results: dict[str, dict[str, Any]] = {}
    for item in resp.json():
        sku = item.get("sku", {})
        if "error" in item:
            continue
        sku_id = sku.get("buttonState", {}).get("skuId", "")
        price_data = sku.get("price", {})
        price_domain = price_data.get("priceDomain", {})
        results[sku_id] = {
            "brand": sku.get("brand", {}).get("brand", ""),
            "name": sku.get("names", {}).get("short", ""),
            "currentPrice": price_data.get("currentPrice", 0),
            "regularPrice": price_data.get("regularPrice", 0),
            "savingsAmount": price_data.get("savingsAmount", 0),
            "totalSavingsPercent": price_domain.get("totalSavingsPercent", 0),
            "onSale": price_data.get("pricingType") == "onSale",
        }

    logger.debug("priceBlocks: got %d/%d SKUs", len(results), len(sku_ids))
    return results


def _fetch_product_details(
    session: curl_requests.Session, sku_id: str
) -> dict[str, str]:
    """Fetch features + clean URL from BestBuy /api/v2/product/<skuId>."""
    url = f"https://www.bestbuy.com/api/v2/product/{sku_id}"
    resp = session.get(
        url, timeout=BESTBUY_TIMEOUT, headers={"Accept": "application/json"}
    )

    if resp.status_code != 200:
        return {"features": "", "url": ""}

    data = resp.json()
    product_url = data.get("links", {}).get("seoPdpUrl", {}).get("href", "")

    features_list = data.get("features", [])
    parts = []
    for f in features_list:
        title = f.get("title", "")
        desc = f.get("description", "")
        if title and desc:
            parts.append(f"{title}: {desc}")
        elif title:
            parts.append(title)

    return {"features": ". ".join(parts), "url": product_url}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def search_bestbuy_real(
    query: str,
    max_results: int = 5,
    timeout: int = BESTBUY_TIMEOUT,
) -> tuple[list[ProductCandidate], list[str]]:
    """Real BestBuy search: session -> search -> priceBlocks -> product details.

    Pipeline:
    1. Create curl_cffi session (Chrome impersonation).
    2. GET /site/searchpage.jsp, parse Apollo SSR cache for SKU ids.
    3. Batch GET /api/3.0/priceBlocks for price + brand + onSale status.
    4. For each on-sale SKU: GET /api/v2/product/<skuId> for features + URL.
    5. Return normalized ProductCandidate list + sanitized warnings.

    Never raises — expected failures become sanitized warning strings
    using bounded reason codes. No raw exceptions, HTML, or stack traces
    in warnings.

    Args:
        query: English search query (e.g. "gaming laptop under 800").
        max_results: Max sale products to return.
        timeout: Per-request timeout in seconds (NOT source-level deadline).

    Returns:
        (products, warnings) — both lists may be empty.
    """
    if not _CURL_CFFI_AVAILABLE:
        return [], ["bestbuy_search_failed: request_failed"]

    try:
        session = _create_session()
    except Exception:
        logger.warning("BestBuy session creation failed for query=%s", query)
        return [], ["bestbuy_search_failed: request_failed"]

    try:
        # Step 1: Search page -> SKU ids.
        url = (
            "https://www.bestbuy.com/site/searchpage.jsp?"
            f"st={query.replace(' ', '+')}"
        )
        resp = session.get(url, timeout=timeout)
        apollo_products = _parse_apollo_search_page(resp.text)

        if not apollo_products:
            logger.info("BestBuy: no products found for query=%s", query)
            return [], ["bestbuy_no_results"]

        # Step 2: Batch price check.
        sku_ids = [p["skuId"] for p in apollo_products]
        price_data = _fetch_price_blocks(session, sku_ids)

        # Step 3: Filter onSale + fetch details.
        products: list[ProductCandidate] = []
        for sku, pd in price_data.items():
            if not pd["onSale"]:
                continue

            details = _fetch_product_details(session, sku)

            products.append(
                ProductCandidate(
                    source="BestBuy",
                    title=pd["name"][:200] if pd["name"] else "Unknown",
                    brand=pd["brand"] if pd["brand"] else None,
                    sale_price_usd=float(pd["currentPrice"]),
                    url=details["url"] or f"https://www.bestbuy.com/site/{sku}.p",
                    features=details["features"] or pd["name"],
                )
            )

            if len(products) >= max_results:
                break

        if not products:
            logger.info("BestBuy: no sale products for query=%s", query)
            return [], ["bestbuy_no_sale_products"]

        logger.info("BestBuy real search: %d products for query=%s",
                     len(products), query)
        return products, []

    except Exception:
        logger.warning("BestBuy real search failed for query=%s", query)
        return [], ["bestbuy_search_failed: request_failed"]
