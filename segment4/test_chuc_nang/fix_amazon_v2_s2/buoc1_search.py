"""
Phase 1+2: Search Amazon, filter on-sale, scrape product details.

Pipeline:
1. Init curl_cffi session + set ZIP 96150
2. GET search page, parse product cards (ASIN, title, price, list_price, specs)
3. Filter: chi giu on_sale == True (co list_price > current_price)
4. Approach A: dung title + specs tu search page lam features
5. Neu features qua ngan -> Approach B: GET product page lay #feature-bullets

Output: list[ScrapedAmazonDeal]

Chay: cd segment4 && uv run test_chuc_nang/fix_amazon_v2_s2/buoc1_search.py
"""

import re
import time
import logging
from typing import Optional
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

ZIP_CODE = "96150"
MIN_FEATURES_LEN = 50  # Approach B threshold: neu features < 50 chars, lay tu product page


# ---------------------------------------------------------------------------
# ScrapedAmazonDeal (copy tu price_agents/amazon_deals.py de test doc lap)
# ---------------------------------------------------------------------------

class ScrapedAmazonDeal:
    """Raw scraped product data from Amazon."""

    def __init__(self, title: str, brand: Optional[str], price: float,
                 features: str, url: str):
        self.title = title[:200] if title else "Unknown"
        self.brand = brand.strip() if brand else None
        self.price = price
        self.features = features[:1500] if features else ""
        self.url = url

    def __repr__(self):
        return f"<{self.title[:50]}... | ${self.price:.2f}>"


# ---------------------------------------------------------------------------
# Step 0: Init session + set ZIP code
# ---------------------------------------------------------------------------

def init_amazon_session() -> curl_requests.Session:
    """Create curl_cffi session and set US delivery location."""
    session = curl_requests.Session(impersonate="chrome")

    # GET homepage to init cookies
    session.get("https://www.amazon.com", timeout=10)

    # Set ZIP code 96150 (South Lake Tahoe, CA)
    resp = session.post(
        "https://www.amazon.com/gp/delivery/ajax/address-change.html",
        data={
            "locationType": "LOCATION_INPUT",
            "zipCode": ZIP_CODE,
            "storeContext": "generic",
            "deviceType": "web",
            "pageType": "Search",
            "actionSource": "glow",
        },
        timeout=10,
    )

    try:
        result = resp.json()
        if result.get("isValidAddress"):
            log.info(f"[Init] ZIP {ZIP_CODE} set OK")
        else:
            log.warning(f"[Init] ZIP response: {result}")
    except Exception:
        log.warning(f"[Init] ZIP code setting failed: {resp.status_code}")

    return session


# ---------------------------------------------------------------------------
# Step 1: Search page -> parse product cards
# ---------------------------------------------------------------------------

def parse_search_results(html: str) -> list[dict]:
    """Parse Amazon search page HTML, extract product info from each card.

    Returns list of dicts with keys:
        asin, title, brand, current_price, list_price, on_sale, specs, url
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find all product cards
    cards = soup.select('div[data-component-type="s-search-result"][data-asin]')
    products = []

    for card in cards:
        asin = card.get("data-asin", "").strip()
        if not asin:
            continue

        # --- Title (aria-label has full text, span may be truncated) ---
        h2 = card.select_one("h2")
        if not h2:
            continue
        title = h2.get("aria-label", "") or h2.get_text(strip=True)
        # Remove "Sponsored Ad - " prefix from sponsored products
        if title.startswith("Sponsored Ad - "):
            title = title[len("Sponsored Ad - "):]
        # Fallback: img alt often has longer title
        if len(title) < 20:
            img = card.select_one("img.s-image")
            if img:
                alt = img.get("alt", "")
                alt = re.sub(r"^Sponsored Ad - ", "", alt)
                if len(alt) > len(title):
                    title = alt.rstrip(".")
        if not title:
            continue

        # --- Brand (extracted from specs block later, or from product page) ---
        brand = None

        # --- Current price ---
        # First a-price with data-a-size="xl" is the current price
        price_block = card.select_one('div[data-cy="price-recipe"]')
        current_price = 0.0
        list_price = 0.0

        if price_block:
            # Current price: first span.a-offscreen inside a-price (non-strike)
            price_spans = price_block.select("span.a-price")
            for ps in price_spans:
                if ps.get("data-a-strike") == "true":
                    # This is the list/original price (strikethrough)
                    offscreen = ps.select_one("span.a-offscreen")
                    if offscreen:
                        list_price = _parse_price(offscreen.get_text())
                else:
                    # Current/sale price
                    if current_price == 0.0:
                        offscreen = ps.select_one("span.a-offscreen")
                        if offscreen:
                            current_price = _parse_price(offscreen.get_text())

        if current_price <= 0:
            continue

        # --- On sale detection ---
        on_sale = list_price > current_price

        # --- Specs from search page (Approach A features) ---
        specs_parts = []
        specs_block = card.select_one('div[data-cy="product-details-recipe"]')
        if specs_block:
            # Each spec: span.a-color-secondary (label) + span.a-text-bold (value)
            labels = specs_block.select("span.a-color-secondary")
            values = specs_block.select("span.a-text-bold")
            for label, value in zip(labels, values):
                l_text = label.get_text(strip=True).rstrip(":")
                v_text = value.get_text(strip=True)
                if l_text and v_text and v_text != "-":
                    specs_parts.append(f"{l_text}: {v_text}")

        specs = ", ".join(specs_parts)

        # Extract brand from specs if available (e.g. "Brand: Samsung")
        for part in specs_parts:
            if part.startswith("Brand:"):
                brand = part.split(":", 1)[1].strip()
                break

        # --- URL ---
        url = f"https://www.amazon.com/dp/{asin}"

        products.append({
            "asin": asin,
            "title": title,
            "brand": brand,
            "current_price": current_price,
            "list_price": list_price,
            "on_sale": on_sale,
            "specs": specs,
            "url": url,
        })

    return products


def search_amazon(session, keyword: str) -> list[dict]:
    """Search Amazon and parse results. Returns list of product dicts."""
    url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"
    log.info(f"[Step 1] Search: {url}")

    resp = session.get(url, timeout=20)
    log.info(f"  Status: {resp.status_code} | Size: {len(resp.text):,} bytes")

    # Check CAPTCHA
    if "/errors/validateCaptcha" in resp.text:
        log.error("  CAPTCHA detected! Aborting.")
        return []

    products = parse_search_results(resp.text)
    sale_count = sum(1 for p in products if p["on_sale"])
    log.info(f"  Found {len(products)} products ({sale_count} on sale)")

    return products


# ---------------------------------------------------------------------------
# Step 2: Scrape features from product page (Approach B - fallback)
# ---------------------------------------------------------------------------

def scrape_product_page(session, url: str) -> dict:
    """GET product page, extract features and brand.

    Returns dict with keys: features, brand (both may be empty string/None).
    """
    result = {"features": "", "brand": None}
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return result

        soup = BeautifulSoup(resp.text, "html.parser")

        # --- Features ---
        # Try #feature-bullets first
        bullets = soup.select_one("#feature-bullets")
        if bullets:
            items = bullets.select("li span.a-list-item")
            features = [item.get_text(strip=True) for item in items
                        if item.get_text(strip=True) and "See more product details" not in item.get_text()]
            if features:
                result["features"] = " | ".join(features)

        # Fallback: #productDescription
        if not result["features"]:
            desc = soup.select_one("#productDescription")
            if desc:
                result["features"] = desc.get_text(strip=True)

        # --- Brand ---
        byline = soup.select_one("#bylineInfo")
        if byline:
            brand_text = byline.get_text(strip=True)
            # Clean: "Visit the Samsung Store" -> "Samsung"
            #         "Brand: Samsung" -> "Samsung"
            brand_text = re.sub(r"^(Visit the |Brand:\s*)", "", brand_text)
            brand_text = re.sub(r"\s*(Store|Brand)$", "", brand_text)
            if brand_text:
                result["brand"] = brand_text

        return result
    except Exception as e:
        log.warning(f"  Failed to scrape {url}: {e}")
        return result


# ---------------------------------------------------------------------------
# Step 3: Combined pipeline
# ---------------------------------------------------------------------------

def search_filter_scrape_amazon(
    keyword: str,
    max_results: int = 5,
    session: curl_requests.Session | None = None,
) -> list[ScrapedAmazonDeal]:
    """Search Amazon, filter on-sale, scrape details.

    Pipeline:
    1. Init session + ZIP 96150
    2. GET search page, parse product cards
    3. Filter on_sale only
    4. Build features (Approach A: title + specs)
    5. If features too short -> Approach B: GET product page for #feature-bullets
    6. Return list[ScrapedAmazonDeal]
    """
    total_start = time.time()

    # Step 0: Init session
    if session is None:
        session = init_amazon_session()

    # Step 1: Search
    products = search_amazon(session, keyword)
    if not products:
        log.warning("No products found")
        return []

    # Step 2: Filter on-sale only
    sale_products = [p for p in products if p["on_sale"]]
    log.info(f"[Step 2] Filtered: {len(sale_products)} on sale (from {len(products)} total)")

    if not sale_products:
        log.warning("No on-sale products found")
        return []

    # Limit to max_results
    sale_products = sale_products[:max_results]

    # Step 3: Build ScrapedAmazonDeal objects
    deals = []
    approach_b_count = 0

    for p in sale_products:
        # Approach A: features = title context + specs from search page
        features = p["specs"]

        brand = p["brand"]

        # Approach B fallback: if specs too short, get from product page
        if len(features) < MIN_FEATURES_LEN:
            log.info(f"  [Approach B] Features too short ({len(features)} chars), scraping product page: {p['asin']}")
            page_data = scrape_product_page(session, p["url"])
            if page_data["features"]:
                features = page_data["features"]
                approach_b_count += 1
            if page_data["brand"] and not brand:
                brand = page_data["brand"]

        deal = ScrapedAmazonDeal(
            title=p["title"],
            brand=brand,
            price=p["current_price"],
            features=features,
            url=p["url"],
        )
        deals.append(deal)

    elapsed = time.time() - total_start
    log.info(f"\n[Result] {len(deals)} deals in {elapsed:.1f}s "
             f"(Approach A: {len(deals) - approach_b_count}, Approach B: {approach_b_count})")

    return deals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_price(text: str) -> float:
    """Parse '$1,799.00' -> 1799.0"""
    if not text:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Main - test standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    keywords = ["laptop gaming", "headphones", "samsung galaxy"]

    for kw in keywords:
        print(f"\n{'='*60}")
        print(f"  KEYWORD: {kw}")
        print(f"{'='*60}")

        deals = search_filter_scrape_amazon(kw, max_results=5)

        for i, d in enumerate(deals, 1):
            print(f"\n  [{i}] {d.title[:80]}")
            print(f"      Price: ${d.price:.2f}")
            print(f"      Brand: {d.brand or 'N/A'}")
            print(f"      Features ({len(d.features)} chars): {d.features[:100]}...")
            print(f"      URL: {d.url}")

        if not deals:
            print("  No on-sale products found")
