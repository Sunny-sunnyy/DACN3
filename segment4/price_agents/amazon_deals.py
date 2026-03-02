"""
Amazon Deals Module

This module contains classes and functions for scraping Amazon products:
- ScrapedAmazonDeal: Data class for raw scraped product data
- set_amazon_us_location(): Set delivery location to US (Zip: 96150)
- is_on_sale_amazon_playwright(): Check if product is on sale
- filter_amazon_sale_urls_playwright(): Filter URLs to keep only sale products
- scrape_amazon_products(): Scrape product details using Playwright

NOTE: Amazon blocks requests library, so we MUST use Playwright for all operations.
"""

import re
import logging
from typing import Optional, List, Tuple

from playwright.async_api import async_playwright


# Logging setup
logger = logging.getLogger(__name__)


# US Zip Code - California (for Amazon delivery location)
US_ZIP_CODE = "96150"


class ScrapedAmazonDeal:
    """
    A class to represent a Deal scraped from Amazon using Playwright.
    This is the raw data before being processed by GPT.
    
    Attributes:
        title: Product title (max 200 chars)
        brand: Product brand (optional)
        price: Sale price in USD
        features: Product features text (max 1500 chars)
        url: Amazon product URL
    """
    
    title: str
    brand: Optional[str]
    price: float
    features: str
    url: str
    
    def __init__(
        self,
        title: str,
        brand: Optional[str],
        price: float,
        features: str,
        url: str
    ):
        """
        Initialize with scraped data from Amazon product page.
        
        Args:
            title: Product title
            brand: Product brand (optional)
            price: Sale price in USD
            features: Product features/description text
            url: Amazon product URL
        """
        self.title = title[:200] if title else "Unknown"
        self.brand = brand.strip() if brand else None
        self.price = price
        self.features = features[:1500] if features else ""
        self.url = url
    
    def __repr__(self) -> str:
        """Return a short string description."""
        return f"<{self.title[:50]}... | ${self.price}>"
    
    def describe(self) -> str:
        """
        Return a longer string to describe this deal for use in calling a model.
        Similar to ScrapedBestBuyDeal.describe() format.
        
        Returns:
            Formatted string with Title, Brand, Price, Features, URL
        """
        parts = [f"Title: {self.title}"]
        
        if self.brand:
            parts.append(f"Brand: {self.brand}")
        
        parts.append(f"Price: ${self.price:.2f}")
        
        if self.features and len(self.features) > 10:
            parts.append(f"Features: {self.features.strip()}")
        
        parts.append(f"URL: {self.url}")
        
        return "\n".join(parts)


async def set_amazon_us_location(page) -> bool:
    """
    Set Amazon delivery location to US by entering zip code.
    This needs to be done once before checking URLs.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if successfully set location
    """
    try:
        logger.info(f"Setting Amazon location to US (Zip: {US_ZIP_CODE})...")
        
        # Go to Amazon homepage first
        await page.goto("https://www.amazon.com", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        # Click on "Deliver to" location selector
        # This element is usually at top left, with id "nav-global-location-popover-link"
        location_btn = page.locator("#nav-global-location-popover-link")
        
        if await location_btn.count() > 0:
            await location_btn.click()
            await page.wait_for_timeout(1500)
            
            # Find zip code input field
            zip_input = page.locator('input[data-action="GLUXPostalInputAction"]')
            
            if await zip_input.count() > 0:
                # Clear and enter zip code
                await zip_input.fill(US_ZIP_CODE)
                await page.wait_for_timeout(500)
                
                # Click Apply button
                apply_btn = page.locator('input[aria-labelledby="GLUXZipUpdate-announce"]')
                if await apply_btn.count() > 0:
                    await apply_btn.click()
                    await page.wait_for_timeout(2000)
                    logger.info(f"Location set to US (Zip: {US_ZIP_CODE})")
                    return True
                else:
                    # Try alternative apply button
                    apply_btn2 = page.locator('span[data-action="GLUXPostalUpdateAction"] input')
                    if await apply_btn2.count() > 0:
                        await apply_btn2.click()
                        await page.wait_for_timeout(2000)
                        logger.info(f"Location set to US (Zip: {US_ZIP_CODE})")
                        return True
            else:
                # Maybe need to click "Change" first if already has location
                change_btn = page.locator('a[id="GLUXChangePostalCodeLink"]')
                if await change_btn.count() > 0:
                    await change_btn.click()
                    await page.wait_for_timeout(1000)
                    # Retry entering zip code
                    zip_input = page.locator('input[data-action="GLUXPostalInputAction"]')
                    if await zip_input.count() > 0:
                        await zip_input.fill(US_ZIP_CODE)
                        apply_btn = page.locator('input[aria-labelledby="GLUXZipUpdate-announce"]')
                        if await apply_btn.count() > 0:
                            await apply_btn.click()
                            await page.wait_for_timeout(2000)
                            logger.info(f"Location set to US (Zip: {US_ZIP_CODE})")
                            return True
        
        logger.warning("Could not find location elements, but continuing...")
        return False
        
    except Exception as e:
        logger.warning(f"Error setting location: {e}")
        return False


async def is_on_sale_amazon_playwright(url: str, page) -> Tuple[bool, dict]:
    """
    Check if Amazon product is on sale using Playwright.
    
    Sale Indicators:
    - span.savingsPercentage: Percentage discount (e.g., "-15%")
    - span.basisPrice: Contains "List Price:"
    - [data-a-strike="true"]: Original price with strikethrough
    
    Args:
        url: Amazon product URL
        page: Playwright page object
        
    Returns:
        Tuple of (is_on_sale: bool, price_info: dict)
    """
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        
        price_info = {}
        
        # Check sale indicator 1: savingsPercentage
        savings_elem = page.locator("span.savingsPercentage")
        has_savings = await savings_elem.count() > 0
        
        if has_savings:
            savings_text = await savings_elem.first.text_content()
            price_info["savings_pct"] = savings_text.strip()
        
        # Check sale indicator 2: basisPrice
        basis_elem = page.locator("span.basisPrice")
        has_basis = await basis_elem.count() > 0
        
        # Check sale indicator 3: data-a-strike
        strike_elem = page.locator('[data-a-strike="true"]')
        has_strike = await strike_elem.count() > 0
        
        # Get current price
        price_elem = page.locator("span.priceToPay")
        if await price_elem.count() > 0:
            price_text = await price_elem.first.text_content()
            price_info["sale_price"] = price_text.strip()
        
        is_sale = has_savings or has_basis or has_strike
        return is_sale, price_info
        
    except Exception as e:
        logger.warning(f"Error checking {url}: {e}")
        return False, {}


async def filter_amazon_sale_urls_playwright(
    urls: List[str],
    headless: bool = False
) -> List[Tuple[str, dict]]:
    """
    Filter Amazon URLs to keep only products on sale.
    Sets US location first, then checks each URL.
    
    NOTE: This function uses Playwright because Amazon blocks requests library.
    
    Args:
        urls: List of Amazon product URLs
        headless: Run browser in headless mode (default: False for reliability)
        
    Returns:
        List of (url, price_info) tuples for products on sale
    """
    sale_items = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )
        
        page = await context.new_page()
        
        # Step 1: Set US Location
        await set_amazon_us_location(page)
        
        # Step 2: Check each URL
        logger.info(f"Checking {len(urls)} URLs for sale items...")
        
        for i, url in enumerate(urls, 1):
            is_sale, price_info = await is_on_sale_amazon_playwright(url, page)
            
            if is_sale:
                sale_items.append((url, price_info))
                savings = price_info.get("savings_pct", "N/A")
                price = price_info.get("sale_price", "N/A")
                logger.info(f"[{i}/{len(urls)}] SALE | {savings} | {price}")
            else:
                price = price_info.get("sale_price", "No price found")
                logger.info(f"[{i}/{len(urls)}] Skip | Price: {price}")
            
            await page.wait_for_timeout(500)
        
        await browser.close()
    
    logger.info(f"Filtered {len(urls)} URLs -> {len(sale_items)} sale URLs")
    
    return sale_items


async def scrape_amazon_products(
    sale_items: List[Tuple[str, dict]],
    headless: bool = False
) -> List[ScrapedAmazonDeal]:
    """
    Scrape Amazon products and return as List[ScrapedAmazonDeal].
    
    Uses Playwright with multi-selector fallback strategy because
    Amazon has many different product page layouts.
    
    Args:
        sale_items: List of (url, price_info) tuples from filter step
        headless: Run browser in headless mode (default: False for reliability)
        
    Returns:
        List[ScrapedAmazonDeal] - Raw scraped data from each product
    """
    scraped_deals = []
    
    # Multi-selector fallback lists (Amazon has many different layouts)
    TITLE_SELECTORS = [
        "#productTitle",
        "h1.product-title-word-break", 
        "h1 span#productTitle",
        "#title span"
    ]
    
    BRAND_SELECTORS = [
        "#bylineInfo",
        "a#bylineInfo", 
        "#brand",
        ".po-brand .a-span9 span",
        "a.contributorNameID"
    ]
    
    FEATURES_SELECTORS = [
        "#feature-bullets ul",
        "#featurebullets_feature_div ul",
        "#productDescription p",
        "#aplus-content-area",
        ".a-unordered-list.a-vertical"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = await context.new_page()
        
        # Set US location first
        await set_amazon_us_location(page)
        
        logger.info(f"Scraping {len(sale_items)} sale products...")
        
        for i, (url, price_info) in enumerate(sale_items, 1):
            logger.info(f"[{i}/{len(sale_items)}] Scraping: {url[:60]}...")
            
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)
                
                # === EXTRACT TITLE (with fallback) ===
                title = "Unknown"
                for selector in TITLE_SELECTORS:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        title = await elem.first.text_content()
                        title = title.strip() if title else "Unknown"
                        break
                
                # === EXTRACT BRAND (with fallback) ===
                brand = None
                for selector in BRAND_SELECTORS:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        brand_text = await elem.first.text_content()
                        if brand_text:
                            # Clean up brand text (remove "Visit the X Store", "Brand: X")
                            brand = brand_text.strip()
                            brand = re.sub(r'^Visit the\s+', '', brand)
                            brand = re.sub(r'\s+Store$', '', brand)
                            brand = re.sub(r'^Brand:\s*', '', brand)
                        break
                
                # === EXTRACT FEATURES (with fallback) ===
                features = ""
                for selector in FEATURES_SELECTORS:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        features = await elem.first.text_content()
                        features = features.strip() if features else ""
                        # Clean up features text
                        features = re.sub(r'\s+', ' ', features)
                        break
                
                # === EXTRACT PRICE (from price_info dict) ===
                price = 0.0
                price_text = price_info.get("sale_price", "$0")
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    price = float(price_match.group())
                
                # Create ScrapedAmazonDeal
                deal = ScrapedAmazonDeal(
                    title=title,
                    brand=brand,
                    price=price,
                    features=features,
                    url=url
                )
                scraped_deals.append(deal)
                logger.info(f"  -> {deal}")
                
            except Exception as e:
                logger.warning(f"  -> Error scraping {url}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"Successfully scraped {len(scraped_deals)}/{len(sale_items)} products")
    return scraped_deals
