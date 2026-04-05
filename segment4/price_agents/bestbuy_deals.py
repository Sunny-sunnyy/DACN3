"""
BestBuy Deals Module

Scrapes BestBuy products using curl_cffi + internal APIs (not Playwright).
Product pages are blocked from WSL2 due to HTTP/2 incompatibility with Akamai CDN,
so we use BestBuy's search page + priceBlocks API + v2 product API instead.

Pipeline:
1. search_bestbuy() - Search via /site/searchpage.jsp, parse Apollo SSR cache -> skuIds
2. get_price_blocks() - Batch API -> price, brand, name, onSale
3. get_product_details() - Per-SKU API -> features, clean URL
4. search_filter_scrape_bestbuy() - Combined: search + filter sale + scrape details
"""

import re
import logging
from typing import Optional

from curl_cffi import requests as curl_requests


logger = logging.getLogger(__name__)


class ScrapedBestBuyDeal:
    """Raw scraped product data from BestBuy APIs."""

    title: str
    brand: Optional[str]
    price: float
    features: str
    url: str

    def __init__(self, title: str, brand: Optional[str], price: float, features: str, url: str):
        self.title = title[:200] if title else "Unknown"
        self.brand = brand.strip() if brand else None
        self.price = price
        self.features = features[:1500] if features else ""
        self.url = url

    def __repr__(self) -> str:
        return f"<{self.title[:50]}... | ${self.price}>"

    def describe(self) -> str:
        """Format for LLM prompt."""
        parts = [f"Title: {self.title}"]
        if self.brand:
            parts.append(f"Brand: {self.brand}")
        parts.append(f"Price: ${self.price:.2f}")
        if self.features and len(self.features) > 10:
            parts.append(f"Features: {self.features.strip()}")
        parts.append(f"URL: {self.url}")
        return "\n".join(parts)


def _init_session() -> curl_requests.Session:
    """Create curl_cffi session with Chrome impersonation and bypass country selection."""
    session = curl_requests.Session(impersonate="chrome")
    session.get("https://www.bestbuy.com/?intl=nosplash", timeout=15)
    return session


def search_bestbuy(session: curl_requests.Session, keyword: str) -> list[dict]:
    """Search BestBuy, parse Apollo SSR cache, return list of {skuId, pdpUrl}."""
    url = f"https://www.bestbuy.com/site/searchpage.jsp?st={keyword.replace(' ', '+')}"
    logger.info(f"[BestBuy Search] {url}")

    resp = session.get(url, timeout=20)
    logger.info(f"[BestBuy Search] Status: {resp.status_code} | Size: {len(resp.content):,} bytes")

    text = resp.text
    products = {}

    all_skus = set(re.findall(r'"skuId":"(\d{5,8})"', text))

    for sku_id in all_skus:
        pattern = rf'"skuId":"{sku_id}"\}},"pdpUrl":"(https://www\.bestbuy\.com/product/[^"]+)"'
        for m in re.finditer(pattern, text):
            pdp_url = m.group(1)
            if "openbox" in pdp_url or "refurbished" in pdp_url:
                continue
            clean_url = re.sub(r'/sku/\d+/?$', '', pdp_url)
            products[sku_id] = {"skuId": sku_id, "pdpUrl": clean_url}
            break

    for sku_id in all_skus:
        if sku_id not in products:
            products[sku_id] = {"skuId": sku_id, "pdpUrl": ""}

    result = list(products.values())
    logger.info(f"[BestBuy Search] Found {len(result)} unique SKUs")
    return result


def get_price_blocks(session: curl_requests.Session, sku_ids: list[str]) -> dict:
    """Batch fetch price+brand+name for multiple SKUs. Returns {skuId: data}."""
    skus_param = ",".join(sku_ids)
    url = f"https://www.bestbuy.com/api/3.0/priceBlocks?skus={skus_param}"
    logger.info(f"[BestBuy PriceBlocks] Fetching {len(sku_ids)} SKUs")

    resp = session.get(url, timeout=15, headers={"Accept": "application/json"})

    results = {}
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

    logger.info(f"[BestBuy PriceBlocks] Got {len(results)}/{len(sku_ids)} SKUs")
    return results


def get_product_details(session: curl_requests.Session, sku_id: str) -> dict:
    """Fetch features + URL for a single SKU from /api/v2/product/."""
    url = f"https://www.bestbuy.com/api/v2/product/{sku_id}"
    resp = session.get(url, timeout=10, headers={"Accept": "application/json"})

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


def search_filter_scrape_bestbuy(
    keyword: str, max_results: int = 10
) -> list[ScrapedBestBuyDeal]:
    """Combined: search BestBuy + filter sale items + scrape details.

    Returns list of ScrapedBestBuyDeal for products currently on sale.
    """
    session = _init_session()

    # Step 1: Search -> skuIds
    apollo_products = search_bestbuy(session, keyword)
    if not apollo_products:
        logger.info("[BestBuy] No products found")
        return []

    # Step 2: Batch price check
    sku_ids = [p["skuId"] for p in apollo_products]
    price_data = get_price_blocks(session, sku_ids)

    # Step 2+3 combined: filter on sale -> scrape features immediately
    scraped_deals = []
    for sku, pd in price_data.items():
        if not pd["onSale"]:
            continue

        details = get_product_details(session, sku)

        deal = ScrapedBestBuyDeal(
            title=pd["name"],
            brand=pd["brand"],
            price=pd["currentPrice"],
            features=details["features"] or pd["name"],
            url=details["url"] or f"https://www.bestbuy.com/site/{sku}.p",
        )
        scraped_deals.append(deal)
        logger.info(f"[BestBuy] SALE: ${pd['currentPrice']} | {pd['name'][:60]}")

        if len(scraped_deals) >= max_results:
            break

    logger.info(f"[BestBuy] Found {len(scraped_deals)} sale products")
    return scraped_deals
