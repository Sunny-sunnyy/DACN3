"""Amazon real search — adapted from segment4/price_agents/amazon_deals.py.

Phase 4B: curl_cffi + HTML parsing. Approach A only (search page parsing).
Product page scraping (Approach B) deferred to reduce live scraping risk.

Adapted functions (segment4 -> V3, copy+adapt, no runtime imports):
  init_amazon_session     -> _create_session
  search_amazon           -> inline fetch + _parse_amazon_search_page
  parse_search_results    -> _parse_amazon_search_page (testable parser)
  _parse_price            -> _parse_price (identical)
  scrape_product_page     -> DEFERRED (see bottom-of-file boundary comment)
  search_filter_scrape_amazon -> search_amazon_real

Timeout note: AMAZON_TIMEOUT is a per-request timeout. One Amazon search
makes 1 (search page) request total in Phase 4B. Approach B would add
1 request per product with thin features.

Warning grammar (sanitized, bounded reason codes):
  amazon_search_failed: <reason>   reason in {timeout, blocked, request_failed}
  amazon_no_results
  amazon_no_sale_products
  amazon_features_limited: <title_truncated_80_chars>
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as curl_requests
    _CURL_CFFI_AVAILABLE = True
except ImportError:
    curl_requests = None  # type: ignore[assignment]
    _CURL_CFFI_AVAILABLE = False

from backend.tools.deal_search.schemas import ProductCandidate

logger = logging.getLogger("shopping_assistant_v3.amazon_search")

ZIP_CODE = "96150"
AMAZON_TIMEOUT = 15  # per-request timeout, not source-level deadline
MIN_FEATURES_LEN = 50  # threshold for amazon_features_limited warning


# ---------------------------------------------------------------------------
# Testable parser + helpers (no network, no curl_cffi)
# ---------------------------------------------------------------------------


def _parse_price(text: str) -> float:
    """Parse '$1,799.00' -> 1799.0."""
    if not text:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_amazon_search_page(html: str) -> list[dict]:
    """Parse Amazon search page HTML for product cards.

    Extracts asin, title, brand, current_price, list_price, on_sale,
    specs, and url from each s-search-result card.

    Testable with saved HTML fixture — no network required.

    Args:
        html: Raw HTML from Amazon /s?k= search page.

    Returns:
        List of dicts with keys: asin, title, brand, current_price,
        list_price, on_sale, specs, url. Products with current_price <= 0
        are excluded.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('div[data-component-type="s-search-result"][data-asin]')
    products: list[dict] = []

    for card in cards:
        asin = card.get("data-asin", "").strip()
        if not asin:
            continue

        # --- Title ---
        h2 = card.select_one("h2")
        if not h2:
            continue
        title = h2.get("aria-label", "") or h2.get_text(strip=True)
        if title.startswith("Sponsored Ad - "):
            title = title[len("Sponsored Ad - "):]
        if len(title) < 20:
            img = card.select_one("img.s-image")
            if img:
                alt = img.get("alt", "")
                alt = re.sub(r"^Sponsored Ad - ", "", alt)
                if len(alt) > len(title):
                    title = alt.rstrip(".")
        if not title:
            continue

        # --- Prices ---
        brand = None
        price_block = card.select_one('div[data-cy="price-recipe"]')
        current_price = 0.0
        list_price = 0.0

        if price_block:
            for ps in price_block.select("span.a-price"):
                if ps.get("data-a-strike") == "true":
                    offscreen = ps.select_one("span.a-offscreen")
                    if offscreen:
                        list_price = _parse_price(offscreen.get_text())
                else:
                    if current_price == 0.0:
                        offscreen = ps.select_one("span.a-offscreen")
                        if offscreen:
                            current_price = _parse_price(offscreen.get_text())

        if current_price <= 0:
            continue

        on_sale = list_price > current_price

        # --- Specs ---
        specs_parts: list[str] = []
        specs_block = card.select_one(
            'div[data-cy="product-details-recipe"]'
        )
        if specs_block:
            labels = specs_block.select("span.a-color-secondary")
            values = specs_block.select("span.a-text-bold")
            for label, value in zip(labels, values):
                l_text = label.get_text(strip=True).rstrip(":")
                v_text = value.get_text(strip=True)
                if l_text and v_text and v_text != "-":
                    specs_parts.append(f"{l_text}: {v_text}")

        specs = ", ".join(specs_parts)

        # Extract brand from specs.
        for part in specs_parts:
            if part.startswith("Brand:"):
                brand = part.split(":", 1)[1].strip()
                break

        products.append({
            "asin": asin,
            "title": title,
            "brand": brand,
            "current_price": current_price,
            "list_price": list_price,
            "on_sale": on_sale,
            "specs": specs,
            "url": f"https://www.amazon.com/dp/{asin}",
        })

    logger.debug("Amazon parse: %d cards -> %d valid products",
                 len(cards), len(products))
    return products


# ---------------------------------------------------------------------------
# Network functions (require curl_cffi)
# ---------------------------------------------------------------------------


def _create_session() -> curl_requests.Session:
    """Create curl_cffi session with Chrome impersonation and US ZIP 96150."""
    session = curl_requests.Session(impersonate="chrome")
    session.get("https://www.amazon.com", timeout=AMAZON_TIMEOUT)

    try:
        session.post(
            "https://www.amazon.com/gp/delivery/ajax/address-change.html",
            data={
                "locationType": "LOCATION_INPUT",
                "zipCode": ZIP_CODE,
                "storeContext": "generic",
                "deviceType": "web",
                "pageType": "Search",
                "actionSource": "glow",
            },
            timeout=AMAZON_TIMEOUT,
        )
    except Exception:
        logger.warning("Amazon ZIP code setting failed — continuing anyway")

    return session


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def search_amazon_real(
    query: str,
    max_results: int = 5,
    timeout: int = AMAZON_TIMEOUT,
) -> tuple[list[ProductCandidate], list[str]]:
    """Real Amazon search using curl_cffi + HTML parsing (Approach A only).

    Pipeline:
    1. Create curl_cffi session + set ZIP 96150.
    2. GET /s?k= search page, check CAPTCHA.
    3. Parse product cards via _parse_amazon_search_page.
    4. Filter on_sale, apply max_results limit.
    5. Return normalized ProductCandidate list + sanitized warnings.

    Phase 4B limitation: search page only (Approach A). Products with
    thin specs (< 50 chars) get an amazon_features_limited warning.
    Product page scraping (Approach B) is deferred.

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
        return [], ["amazon_search_failed: request_failed"]

    try:
        session = _create_session()
    except Exception:
        logger.warning("Amazon session creation failed for query=%s", query)
        return [], ["amazon_search_failed: request_failed"]

    try:
        url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
        resp = session.get(url, timeout=timeout)

        if "/errors/validateCaptcha" in resp.text:
            logger.warning("Amazon CAPTCHA detected for query=%s", query)
            return [], ["amazon_search_failed: blocked"]

        parsed = _parse_amazon_search_page(resp.text)

        if not parsed:
            logger.info("Amazon: no products parsed for query=%s", query)
            return [], ["amazon_no_results"]

        sale_products = [p for p in parsed if p["on_sale"]]
        if not sale_products:
            logger.info("Amazon: no sale products for query=%s", query)
            return [], ["amazon_no_sale_products"]

        sale_products = sale_products[:max_results]

        products: list[ProductCandidate] = []
        warnings: list[str] = []
        for p in sale_products:
            features = p["specs"]

            if len(features) < MIN_FEATURES_LEN:
                short_title = (
                    p["title"][:80] if len(p["title"]) > 80 else p["title"]
                )
                logger.info(
                    "Amazon features_limited: asin=%s title=%s len=%d",
                    p["asin"], short_title, len(features),
                )
                warnings.append(
                    f"amazon_features_limited: {short_title}"
                )

            products.append(
                ProductCandidate(
                    source="Amazon",
                    title=p["title"][:200],
                    brand=p["brand"] if p["brand"] else None,
                    sale_price_usd=p["current_price"],
                    url=p["url"],
                    features=features if features else p["title"],
                )
            )

        logger.info("Amazon real search: %d products for query=%s",
                     len(products), query)
        return products, warnings

    except Exception:
        logger.warning("Amazon real search failed for query=%s", query)
        return [], ["amazon_search_failed: request_failed"]


# ---------------------------------------------------------------------------
# Future boundary: Approach B — product page detail enrichment
#
# To add optional product-page scraping in a future milestone (e.g. 4B.1):
# 1. Gate behind ENABLE_AMAZON_DETAIL_SCRAPE=true flag in shared/config.py.
# 2. Implement _fetch_product_details(session, url) -> {"features", "brand"}
#    that GETs the product page and extracts #feature-bullets + #bylineInfo,
#    adapted from segment4/price_agents/amazon_deals.scrape_product_page().
# 3. In search_amazon_real, after the on_sale filter, call
#    _fetch_product_details for products with len(features) < 50.
# 4. Add opt-in test gated by the same flag.
#
# Do NOT add empty stub functions in Phase 4B. This comment is the boundary.
# ---------------------------------------------------------------------------
