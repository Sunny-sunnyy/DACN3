"""
Amazon Deals Module

Scrapes Amazon products using a hybrid approach: Playwright + curl_cffi + HTML parsing.
Amazon protects pages with an AWS WAF JavaScript challenge that curl_cffi cannot solve,
so a headless Chromium opens the homepage once to get the `aws-waf-token` cookie,
then curl_cffi reuses those cookies for the fast search / product page requests.

Pipeline:
1. init_amazon_session() - Get WAF cookies via Playwright + force USD prices
2. search_amazon() - GET search page, parse product cards
3. search_filter_scrape_amazon() - Combined: search + filter sale + scrape details
"""

import re
import time
import logging
from typing import Optional

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright


logger = logging.getLogger(__name__)

MIN_FEATURES_LEN = 50  # Approach B threshold: if features < 50 chars, scrape product page
WAF_TOKEN_COOKIE = "aws-waf-token"
WAIT_SEARCH_BOX_MS = 3000
# Direct /s?k= links without these get 503 from WAF; mimic a search-box submit from the homepage
SEARCH_REF = "nb_sb_noss"
SEARCH_HEADERS = {"Referer": "https://www.amazon.com/"}


class ScrapedAmazonDeal:
    """Raw scraped product data from Amazon."""

    title: str
    brand: Optional[str]
    price: float
    features: str
    url: str

    def __init__(self, title: str, brand: Optional[str], price: float,
                 features: str, url: str):
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


# ---------------------------------------------------------------------------
# Session init
# ---------------------------------------------------------------------------

def _get_waf_cookies() -> list[dict]:
    """Open amazon.com in headless Chromium so the WAF JS challenge runs, return its cookies."""
    t0 = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chromium")
        try:
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            page.goto("https://www.amazon.com/", wait_until="domcontentloaded", timeout=45000)
            # Challenge page (202) runs JS, sets the token, then reloads into the real homepage
            for _ in range(30):
                if any(c["name"] == WAF_TOKEN_COOKIE for c in ctx.cookies()):
                    break
                time.sleep(0.5)
            # 29/10: sau khi qua WAF, Amazon có lúc hiện trang "Continue shopping" (không có ô tìm kiếm).
            # Chờ ô tìm kiếm 20 s rồi ném lỗi làm mất luôn cookie WAF đã có (mỗi lần mất ~22 s).
            # Token có sau ~1,6 s và một mình nó đủ cho curl_cffi tìm kiếm (đo 29/10: 16 sản phẩm).
            try:
                page.wait_for_selector("#twotabsearchtextbox", timeout=WAIT_SEARCH_BOX_MS)
            except PlaywrightTimeoutError:
                logger.info("[Amazon Init] No search box (interstitial page) - using WAF cookies as is")
            cookies = ctx.cookies()
        finally:
            browser.close()

    has_token = any(c["name"] == WAF_TOKEN_COOKIE for c in cookies)
    logger.info(f"[Amazon Init] Browser cookies: {len(cookies)} (WAF token: {has_token}) in {time.time() - t0:.1f}s")
    return cookies


def init_amazon_session() -> curl_requests.Session:
    """Create curl_cffi session with WAF cookies from a real browser, prices forced to USD."""
    session = curl_requests.Session(impersonate="chrome")

    try:
        for c in _get_waf_cookies():
            session.cookies.set(c["name"], c["value"], domain=c["domain"])
    except Exception as e:
        logger.error(f"[Amazon Init] Could not get WAF cookies via browser: {e}")

    # Outside the US Amazon shows local currency (e.g. VND); the currency cookie forces USD.
    # (The old ZIP-code POST no longer works: it now needs a CSRF token.)
    session.cookies.set("i18n-prefs", "USD", domain=".amazon.com")
    return session


def _is_waf_blocked(resp) -> bool:
    """AWS WAF block / challenge page instead of real content."""
    return resp.status_code in (202, 503) or "awsWafCookieDomainList" in resp.text


# ---------------------------------------------------------------------------
# Search page parsing
# ---------------------------------------------------------------------------

def _parse_price(text: str) -> float:
    """Parse '$1,799.00' -> 1799.0. Non-USD prices (e.g. 'VND 4,649,862') -> 0.0 (skipped)."""
    if not text or "$" not in text:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_search_results(html: str) -> list[dict]:
    """Parse Amazon search page HTML, extract product info from each card."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('div[data-component-type="s-search-result"][data-asin]')
    products = []

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
        specs_parts = []
        specs_block = card.select_one('div[data-cy="product-details-recipe"]')
        if specs_block:
            labels = specs_block.select("span.a-color-secondary")
            values = specs_block.select("span.a-text-bold")
            for label, value in zip(labels, values):
                l_text = label.get_text(strip=True).rstrip(":")
                v_text = value.get_text(strip=True)
                if l_text and v_text and v_text != "-":
                    specs_parts.append(f"{l_text}: {v_text}")

        specs = ", ".join(specs_parts)

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

    return products


def search_amazon(session: curl_requests.Session, keyword: str) -> list[dict]:
    """Search Amazon and parse results."""
    url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}&ref={SEARCH_REF}"
    logger.info(f"[Amazon Search] {url}")

    resp = session.get(url, timeout=20, headers=SEARCH_HEADERS)
    logger.info(f"[Amazon Search] Status: {resp.status_code} | Size: {len(resp.text):,} bytes")

    if "/errors/validateCaptcha" in resp.text:
        logger.error("[Amazon Search] CAPTCHA detected!")
        return []
    if _is_waf_blocked(resp):
        logger.error(f"[Amazon Search] Blocked by AWS WAF (status {resp.status_code})")
        return []

    products = parse_search_results(resp.text)
    card_count = resp.text.count('data-component-type="s-search-result"')
    if card_count and not products:
        logger.warning(f"[Amazon Search] {card_count} cards but 0 USD prices parsed - currency not USD?")
    sale_count = sum(1 for p in products if p["on_sale"])
    logger.info(f"[Amazon Search] Found {len(products)} products ({sale_count} on sale)")
    return products


# ---------------------------------------------------------------------------
# Product page scraping (Approach B fallback)
# ---------------------------------------------------------------------------

def scrape_product_page(session: curl_requests.Session, url: str) -> dict:
    """GET product page, extract features and brand."""
    result = {"features": "", "brand": None}
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return result

        soup = BeautifulSoup(resp.text, "html.parser")

        # Features: #feature-bullets
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

        # Brand: #bylineInfo
        byline = soup.select_one("#bylineInfo")
        if byline:
            brand_text = byline.get_text(strip=True)
            brand_text = re.sub(r"^(Visit the |Brand:\s*)", "", brand_text)
            brand_text = re.sub(r"\s*(Store|Brand)$", "", brand_text)
            if brand_text:
                result["brand"] = brand_text

        return result
    except Exception as e:
        logger.warning(f"[Amazon] Failed to scrape {url}: {e}")
        return result


# ---------------------------------------------------------------------------
# Combined pipeline
# ---------------------------------------------------------------------------

def search_filter_scrape_amazon(
    keyword: str,
    max_results: int = 6,
    session: curl_requests.Session | None = None,
) -> list[ScrapedAmazonDeal]:
    """Search Amazon, filter on-sale, scrape details.

    Pipeline:
    1. Init session + ZIP 96150
    2. GET search page, parse product cards
    3. Filter on_sale only
    4. Approach A: title + specs from search page
    5. If features too short -> Approach B: GET product page for #feature-bullets
    """
    if session is None:
        session = init_amazon_session()

    products = search_amazon(session, keyword)
    if not products:
        # WAF is flaky: an occasional block / slow homepage -> retry once with fresh cookies
        logger.info("[Amazon] No products, retrying once with a fresh browser session")
        time.sleep(2)
        session = init_amazon_session()
        products = search_amazon(session, keyword)
    if not products:
        return []

    sale_products = [p for p in products if p["on_sale"]]
    logger.info(f"[Amazon Filter] {len(sale_products)} on sale (from {len(products)} total)")

    if not sale_products:
        return []

    sale_products = sale_products[:max_results]

    deals = []
    approach_b_count = 0

    for p in sale_products:
        features = p["specs"]
        brand = p["brand"]

        if len(features) < MIN_FEATURES_LEN:
            logger.info(f"[Amazon Approach B] specs too short ({len(features)} chars), scraping: {p['asin']}")
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

    logger.info(f"[Amazon] {len(deals)} deals (Approach A: {len(deals) - approach_b_count}, B: {approach_b_count})")
    return deals
