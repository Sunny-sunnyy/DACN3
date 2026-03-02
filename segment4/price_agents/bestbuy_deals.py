"""
BestBuy Deals Module

This module contains classes and functions for scraping BestBuy products:
- ScrapedBestBuyDeal: Data class for raw scraped product data
- is_on_sale(): Check if a BestBuy product is on sale
- filter_sale_urls(): Filter URLs to keep only sale products
- scrape_bestbuy_products(): Scrape product details using Playwright
"""

import re
import time
import logging
import requests
from typing import Optional, List
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# Logging setup
logger = logging.getLogger(__name__)


class ScrapedBestBuyDeal:
    """
    A class to represent a Deal scraped from BestBuy using Playwright.
    This is the raw data before being processed by GPT.
    
    Attributes:
        title: Product title (max 200 chars)
        brand: Product brand (optional)
        price: Sale price in USD
        features: Product features text (max 1500 chars)
        url: BestBuy product URL
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
        Initialize with scraped data from BestBuy product page.
        
        Args:
            title: Product title
            brand: Product brand (optional)
            price: Sale price in USD
            features: Product features/description text
            url: BestBuy product URL
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
        Similar to ScrapedDeal.describe() format.
        
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


def is_on_sale(url: str, timeout: int = 10) -> bool:
    """
    Check if a BestBuy product is currently on sale.
    
    Uses BeautifulSoup to check for sale indicators in the HTML:
    - data-testid="price-block-total-savings-text" (savings amount)
    - data-lu-target="comp_value" (comparison value)
    
    Args:
        url: BestBuy product URL
        timeout: Request timeout in seconds (default: 10)
        
    Returns:
        True if product is on sale, False otherwise
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Check for sale indicators
        savings_elem = soup.find(attrs={"data-testid": "price-block-total-savings-text"})
        comp_value_elem = soup.find(attrs={"data-lu-target": "comp_value"})
        
        return savings_elem is not None or comp_value_elem is not None
        
    except Exception as e:
        logger.warning(f"Error checking sale status for {url}: {e}")
        return False


def filter_sale_urls(urls: List[str], delay: float = 0.05) -> List[str]:
    """
    Filter list of BestBuy URLs to keep only products currently on sale.
    
    Args:
        urls: List of BestBuy product URLs
        delay: Delay between requests in seconds (default: 0.05)
        
    Returns:
        List of URLs for products that are on sale
    """
    sale_urls = []
    
    for i, url in enumerate(urls, 1):
        if is_on_sale(url):
            sale_urls.append(url)
            logger.info(f"[{i}/{len(urls)}] SALE")
        else:
            logger.info(f"[{i}/{len(urls)}] Skip")
        
        time.sleep(delay)
    
    logger.info(f"Filtered {len(urls)} URLs → {len(sale_urls)} sale URLs")
    return sale_urls


async def scrape_bestbuy_products(
    urls: List[str],
    headless: bool = False
) -> List[ScrapedBestBuyDeal]:
    """
    Scrape BestBuy products and return as List[ScrapedBestBuyDeal].
    
    Uses Playwright to:
    1. Navigate to each product page
    2. Extract title, brand, price
    3. Click "Features" button and extract feature text
    4. Return list of ScrapedBestBuyDeal objects
    
    Args:
        urls: List of BestBuy product URLs (preferably sale items)
        headless: Run browser in headless mode (default: False for reliability)
        
    Returns:
        List[ScrapedBestBuyDeal] - Raw scraped data from each product
    """
    scraped_deals = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Scraping: {url[:60]}...")
            
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
                # Extract Title
                title_elem = page.locator("h1.h4")
                title = await title_elem.text_content() if await title_elem.count() > 0 else "Unknown"
                title = title.strip() if title else "Unknown"
                
                # Extract Brand
                brand_elem = page.locator('div[data-component-name="ProductHeader"] a.c-button-link')
                brand = await brand_elem.first.text_content() if await brand_elem.count() > 0 else None
                brand = brand.strip() if brand else None
                
                # Extract Sale Price
                price_elem = page.locator('[data-testid="price-block-customer-price"] span')
                price_text = await price_elem.first.text_content() if await price_elem.count() > 0 else "$0"
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                price = float(price_match.group()) if price_match else 0.0
                
                # Click Features button and extract
                features = ""
                features_btn = page.locator('button:has(h3:text("Features"))')
                
                if await features_btn.count() > 0:
                    await features_btn.first.click()
                    try:
                        await page.locator('[data-testid="brix-sheet-content"]').wait_for(timeout=5000)
                        features_elem = page.locator('[data-testid="brix-sheet-content"]')
                        features = await features_elem.first.text_content() or ""
                    except Exception:
                        pass
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)
                
                # Create ScrapedBestBuyDeal
                deal = ScrapedBestBuyDeal(
                    title=title,
                    brand=brand,
                    price=price,
                    features=features,
                    url=url
                )
                scraped_deals.append(deal)
                logger.info(f"  ✓ {deal}")
                
            except Exception as e:
                logger.warning(f"  ✗ Error scraping {url}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"Successfully scraped {len(scraped_deals)}/{len(urls)} products")
    return scraped_deals
