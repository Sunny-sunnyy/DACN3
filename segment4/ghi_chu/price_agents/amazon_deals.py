"""
=============================================================================
AMAZON DEALS MODULE - SCRAPING SẢN PHẨM TỪ AMAZON
=============================================================================
File: price_agents/amazon_deals.py

MỤC ĐÍCH:
- Scrape sản phẩm từ Amazon
- Lọc sản phẩm đang sale
- LƯU Ý: Amazon BLOCK requests, PHẢI dùng Playwright

CÁC THÀNH PHẦN:
1. ScrapedAmazonDeal: Class chứa data sản phẩm
2. set_amazon_us_location(): Set vị trí giao hàng US
3. is_on_sale_amazon_playwright(): Check sale
4. filter_amazon_sale_urls_playwright(): Lọc URLs sale
5. scrape_amazon_products(): Scrape chi tiết
"""

import re
import logging
from typing import Optional, List, Tuple
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)
US_ZIP_CODE = "96150"  # California

# =============================================================================
# DATA CLASS
# =============================================================================

class ScrapedAmazonDeal:
    """Data sản phẩm Amazon đã scrape."""
    
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
        """Tạo string cho GPT."""
        parts = [f"Title: {self.title}"]
        if self.brand:
            parts.append(f"Brand: {self.brand}")
        parts.append(f"Price: ${self.price:.2f}")
        if self.features and len(self.features) > 10:
            parts.append(f"Features: {self.features.strip()}")
        parts.append(f"URL: {self.url}")
        return "\n".join(parts)

# =============================================================================
# SET US LOCATION
# =============================================================================

async def set_amazon_us_location(page) -> bool:
    """Set vị trí giao hàng Amazon về US (Zip: 96150)."""
    try:
        logger.info(f"Setting Amazon location to US (Zip: {US_ZIP_CODE})...")
        await page.goto("https://www.amazon.com", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        location_btn = page.locator("#nav-global-location-popover-link")
        if await location_btn.count() > 0:
            await location_btn.click()
            await page.wait_for_timeout(1500)
            
            zip_input = page.locator('input[data-action="GLUXPostalInputAction"]')
            if await zip_input.count() > 0:
                await zip_input.fill(US_ZIP_CODE)
                await page.wait_for_timeout(500)
                apply_btn = page.locator('input[aria-labelledby="GLUXZipUpdate-announce"]')
                if await apply_btn.count() > 0:
                    await apply_btn.click()
                    await page.wait_for_timeout(2000)
                    logger.info(f"Location set to US")
                    return True
        return False
    except Exception as e:
        logger.warning(f"Error setting location: {e}")
        return False

# =============================================================================
# CHECK SALE
# =============================================================================

async def is_on_sale_amazon_playwright(url: str, page) -> Tuple[bool, dict]:
    """Check sản phẩm có đang sale không. Return (is_sale, price_info)."""
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        
        price_info = {}
        savings_elem = page.locator("span.savingsPercentage")
        has_savings = await savings_elem.count() > 0
        if has_savings:
            price_info["savings_pct"] = (await savings_elem.first.text_content()).strip()
        
        has_basis = await page.locator("span.basisPrice").count() > 0
        has_strike = await page.locator('[data-a-strike="true"]').count() > 0
        
        price_elem = page.locator("span.priceToPay")
        if await price_elem.count() > 0:
            price_info["sale_price"] = (await price_elem.first.text_content()).strip()
        
        return (has_savings or has_basis or has_strike), price_info
    except Exception as e:
        logger.warning(f"Error checking {url}: {e}")
        return False, {}

# =============================================================================
# FILTER SALE URLs
# =============================================================================

async def filter_amazon_sale_urls_playwright(urls: List[str], headless: bool = False) -> List[Tuple[str, dict]]:
    """Lọc URLs Amazon chỉ giữ sản phẩm sale."""
    sale_items = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent='Mozilla/5.0 Chrome/121.0.0.0',
            viewport={'width': 1920, 'height': 1080},
            locale="en-US", timezone_id="America/New_York"
        )
        page = await context.new_page()
        await set_amazon_us_location(page)
        
        for i, url in enumerate(urls, 1):
            is_sale, price_info = await is_on_sale_amazon_playwright(url, page)
            if is_sale:
                sale_items.append((url, price_info))
                logger.info(f"[{i}/{len(urls)}] SALE")
            else:
                logger.info(f"[{i}/{len(urls)}] Skip")
            await page.wait_for_timeout(500)
        
        await browser.close()
    
    logger.info(f"Filtered {len(urls)} -> {len(sale_items)} sale URLs")
    return sale_items

# =============================================================================
# SCRAPE PRODUCTS
# =============================================================================

async def scrape_amazon_products(sale_items: List[Tuple[str, dict]], headless: bool = False) -> List[ScrapedAmazonDeal]:
    """Scrape chi tiết sản phẩm Amazon."""
    scraped_deals = []
    
    TITLE_SELECTORS = ["#productTitle", "h1.product-title-word-break", "#title span"]
    BRAND_SELECTORS = ["#bylineInfo", "#brand", ".po-brand .a-span9 span"]
    FEATURES_SELECTORS = ["#feature-bullets ul", "#productDescription p"]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent='Mozilla/5.0 Chrome/121.0.0.0', viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        await set_amazon_us_location(page)
        
        for i, (url, price_info) in enumerate(sale_items, 1):
            logger.info(f"[{i}/{len(sale_items)}] Scraping: {url[:50]}...")
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)
                
                # Title
                title = "Unknown"
                for sel in TITLE_SELECTORS:
                    if await page.locator(sel).count() > 0:
                        title = (await page.locator(sel).first.text_content()).strip()
                        break
                
                # Brand
                brand = None
                for sel in BRAND_SELECTORS:
                    if await page.locator(sel).count() > 0:
                        brand = (await page.locator(sel).first.text_content()).strip()
                        brand = re.sub(r'^Visit the\s+|\s+Store$|^Brand:\s*', '', brand)
                        break
                
                # Features
                features = ""
                for sel in FEATURES_SELECTORS:
                    if await page.locator(sel).count() > 0:
                        features = re.sub(r'\s+', ' ', (await page.locator(sel).first.text_content()).strip())
                        break
                
                # Price
                price = 0.0
                price_match = re.search(r'[\d,]+\.?\d*', price_info.get("sale_price", "$0").replace(',', ''))
                if price_match:
                    price = float(price_match.group())
                
                scraped_deals.append(ScrapedAmazonDeal(title=title, brand=brand, price=price, features=features, url=url))
                logger.info(f"  -> ${price}")
            except Exception as e:
                logger.warning(f"  -> Error: {e}")
        
        await browser.close()
    
    logger.info(f"Scraped {len(scraped_deals)}/{len(sale_items)} products")
    return scraped_deals
