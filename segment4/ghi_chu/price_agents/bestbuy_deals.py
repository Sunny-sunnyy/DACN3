"""
=============================================================================
BESTBUY DEALS MODULE - SCRAPING SẢN PHẨM TỪ BESTBUY
=============================================================================
File: price_agents/bestbuy_deals.py

MỤC ĐÍCH:
- Cung cấp các hàm và class để scrape sản phẩm từ BestBuy
- Lọc sản phẩm đang sale trước khi scrape (tiết kiệm thời gian)
- Lấy thông tin chi tiết: title, brand, price, features

CÁC THÀNH PHẦN CHÍNH:
1. ScrapedBestBuyDeal: Class chứa data sản phẩm đã scrape
2. is_on_sale(): Check 1 URL có đang sale không (BeautifulSoup)
3. filter_sale_urls(): Lọc nhiều URLs, chỉ giữ sản phẩm sale
4. scrape_bestbuy_products(): Scrape chi tiết bằng Playwright

TẠI SAO DÙNG 2 CÔNG CỤ?
- BeautifulSoup: Nhanh, nhẹ → Dùng để CHECK sale (bước lọc)
- Playwright: Chậm hơn, mạnh hơn → Dùng để SCRAPE chi tiết (sau khi lọc)
- Lọc trước rồi scrape → Tiết kiệm thời gian đáng kể

WORKFLOW:
1. filter_sale_urls(urls) → Lọc ra URLs đang sale (BeautifulSoup, nhanh)
2. scrape_bestbuy_products(sale_urls) → Scrape chi tiết (Playwright, chậm)
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


# =============================================================================
# PHẦN 1: DATA CLASS - CHỨA THÔNG TIN SẢN PHẨM ĐÃ SCRAPE
# =============================================================================

class ScrapedBestBuyDeal:
    """
    Class chứa dữ liệu sản phẩm BestBuy đã scrape bằng Playwright.
    
    Đây là dữ liệu THÔ, chưa qua xử lý bởi GPT.
    Sẽ được chuyển thành UnifiedScrapedDeal để gộp với Amazon.
    
    Attributes:
        title: Tên sản phẩm (tối đa 200 ký tự)
        brand: Thương hiệu (có thể None)
        price: Giá sale hiện tại (USD)
        features: Mô tả tính năng (tối đa 1500 ký tự)
        url: URL sản phẩm trên BestBuy
    
    VD:
        deal = ScrapedBestBuyDeal(
            title="Acer Aspire 5 - 15.6\" Laptop - AMD Ryzen 5...",
            brand="Acer",
            price=449.99,
            features="15.6 inch FHD display, AMD Ryzen 5, 8GB RAM, 512GB SSD...",
            url="https://www.bestbuy.com/site/acer-aspire-5/..."
        )
    """
    
    # Type hints (không phải Pydantic, chỉ là annotation)
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
        Khởi tạo với dữ liệu đã scrape từ trang sản phẩm BestBuy.
        
        Tự động truncate title (200 chars) và features (1500 chars)
        để tránh prompt quá dài khi gửi cho GPT.
        
        Args:
            title: Tên sản phẩm
            brand: Thương hiệu (có thể None nếu không tìm thấy)
            price: Giá sale (USD)
            features: Mô tả/tính năng
            url: URL sản phẩm
        """
        self.title = title[:200] if title else "Unknown"
        self.brand = brand.strip() if brand else None
        self.price = price
        self.features = features[:1500] if features else ""
        self.url = url
    
    def __repr__(self) -> str:
        """String ngắn gọn để debug. VD: <Acer Aspire 5 - 15.6" Laptop - AMD R... | $449.99>"""
        return f"<{self.title[:50]}... | ${self.price}>"
    
    def describe(self) -> str:
        """
        Tạo string dài để gửi cho GPT (tương tự format của ScrapedDeal).
        
        Format:
            Title: Acer Aspire 5 - 15.6" Laptop...
            Brand: Acer
            Price: $449.99
            Features: 15.6 inch FHD display...
            URL: https://...
        
        Returns:
            String đa dòng với đầy đủ thông tin sản phẩm
        """
        parts = [f"Title: {self.title}"]
        
        if self.brand:
            parts.append(f"Brand: {self.brand}")
        
        parts.append(f"Price: ${self.price:.2f}")
        
        if self.features and len(self.features) > 10:
            parts.append(f"Features: {self.features.strip()}")
        
        parts.append(f"URL: {self.url}")
        
        return "\n".join(parts)


# =============================================================================
# PHẦN 2: KIỂM TRA SẢN PHẨM CÓ ĐANG SALE KHÔNG (BEAUTIFULSOUP)
# =============================================================================

def is_on_sale(url: str, timeout: int = 10) -> bool:
    """
    Check xem sản phẩm BestBuy có đang SALE không.
    
    Sử dụng BeautifulSoup (nhanh, không cần browser):
    - Fetch HTML của trang
    - Tìm các indicators cho thấy sản phẩm đang sale
    
    Sale Indicators:
    - data-testid="price-block-total-savings-text": Hiển thị số tiền tiết kiệm
    - data-lu-target="comp_value": Giá so sánh (giá gốc)
    
    Args:
        url: URL sản phẩm BestBuy
        timeout: Timeout cho request (giây, default: 10)
        
    Returns:
        True nếu sản phẩm đang sale, False nếu không
    
    VD:
        is_on_sale("https://www.bestbuy.com/site/acer-laptop/...")
        # → True (đang sale)
    """
    try:
        # Fake User-Agent để tránh bị block
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Indicator 1: Element hiển thị "You save $XX" hoặc "Save $XX"
        savings_elem = soup.find(attrs={"data-testid": "price-block-total-savings-text"})
        
        # Indicator 2: Element hiển thị giá gốc (comparison value)
        comp_value_elem = soup.find(attrs={"data-lu-target": "comp_value"})
        
        # Nếu có ít nhất 1 indicator → đang sale
        return savings_elem is not None or comp_value_elem is not None
        
    except Exception as e:
        logger.warning(f"Error checking sale status for {url}: {e}")
        return False  # An toàn: không sale nếu có lỗi


def filter_sale_urls(urls: List[str], delay: float = 0.05) -> List[str]:
    """
    Lọc list URLs BestBuy, chỉ giữ sản phẩm đang SALE.
    
    Dùng hàm is_on_sale() cho mỗi URL.
    
    Args:
        urls: List URLs cần lọc
        delay: Delay giữa các request (giây, default: 0.05)
               Delay nhỏ để tránh rate limiting
        
    Returns:
        List URLs của sản phẩm đang sale
    
    VD:
        urls = ["https://...product1", "https://...product2", "https://...product3"]
        sale_urls = filter_sale_urls(urls)
        # → ["https://...product1", "https://...product3"]  # product2 không sale
    """
    sale_urls = []
    
    for i, url in enumerate(urls, 1):
        if is_on_sale(url):
            sale_urls.append(url)
            logger.info(f"[{i}/{len(urls)}] SALE")  # Log progress
        else:
            logger.info(f"[{i}/{len(urls)}] Skip")
        
        time.sleep(delay)  # Tránh rate limiting
    
    logger.info(f"Filtered {len(urls)} URLs → {len(sale_urls)} sale URLs")
    return sale_urls


# =============================================================================
# PHẦN 3: SCRAPE CHI TIẾT SẢN PHẨM (PLAYWRIGHT)
# =============================================================================

async def scrape_bestbuy_products(
    urls: List[str],
    headless: bool = False
) -> List[ScrapedBestBuyDeal]:
    """
    Scrape chi tiết sản phẩm BestBuy bằng Playwright.
    
    Dùng Playwright thay vì BeautifulSoup vì:
    - Cần click nút "Features" để lấy mô tả chi tiết
    - Một số content load bằng JavaScript
    - Tránh bị detect là bot
    
    Thông tin được extract:
    - Title: Từ h1.h4
    - Brand: Từ link trong ProductHeader
    - Price: Từ price-block-customer-price
    - Features: Từ sidebar sau khi click nút "Features"
    
    Args:
        urls: List URLs sản phẩm (nên là URLs đã lọc qua filter_sale_urls)
        headless: Chạy browser ẩn (False = hiển thị browser, reliable hơn)
        
    Returns:
        List[ScrapedBestBuyDeal] - Dữ liệu thô từ mỗi sản phẩm
    
    VD:
        sale_urls = filter_sale_urls(all_urls)
        deals = await scrape_bestbuy_products(sale_urls)
        # → [ScrapedBestBuyDeal(...), ScrapedBestBuyDeal(...), ...]
    """
    scraped_deals = []
    
    async with async_playwright() as p:
        # Khởi động Chromium với các options chống bot detection
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        # Tạo context với User-Agent giả lập Chrome thật
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Scrape từng URL
        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Scraping: {url[:60]}...")
            
            try:
                # Navigate đến trang sản phẩm
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)  # Đợi page load
                
                # === EXTRACT TITLE ===
                # Selector: h1 với class h4 (BestBuy dùng h4 class cho product title)
                title_elem = page.locator("h1.h4")
                title = await title_elem.text_content() if await title_elem.count() > 0 else "Unknown"
                title = title.strip() if title else "Unknown"
                
                # === EXTRACT BRAND ===
                # Selector: Link trong ProductHeader (VD: "Acer Store")
                brand_elem = page.locator('div[data-component-name="ProductHeader"] a.c-button-link')
                brand = await brand_elem.first.text_content() if await brand_elem.count() > 0 else None
                brand = brand.strip() if brand else None
                
                # === EXTRACT SALE PRICE ===
                # Selector: price-block-customer-price (giá hiện tại, đã giảm)
                price_elem = page.locator('[data-testid="price-block-customer-price"] span')
                price_text = await price_elem.first.text_content() if await price_elem.count() > 0 else "$0"
                # Parse price: "$449.99" → 449.99
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                price = float(price_match.group()) if price_match else 0.0
                
                # === CLICK "FEATURES" BUTTON VÀ EXTRACT ===
                # BestBuy có nút Features → click để mở sidebar với mô tả chi tiết
                features = ""
                features_btn = page.locator('button:has(h3:text("Features"))')
                
                if await features_btn.count() > 0:
                    await features_btn.first.click()  # Click nút Features
                    try:
                        # Đợi sidebar mở
                        await page.locator('[data-testid="brix-sheet-content"]').wait_for(timeout=5000)
                        features_elem = page.locator('[data-testid="brix-sheet-content"]')
                        features = await features_elem.first.text_content() or ""
                    except Exception:
                        pass  # Không lấy được features cũng OK
                    await page.keyboard.press("Escape")  # Đóng sidebar
                    await page.wait_for_timeout(500)
                
                # === TẠO SCRAPED DEAL ===
                deal = ScrapedBestBuyDeal(
                    title=title,
                    brand=brand,
                    price=price,
                    features=features,
                    url=url
                )
                scraped_deals.append(deal)
                logger.info(f"  ✓ {deal}")  # Log success
                
            except Exception as e:
                logger.warning(f"  ✗ Error scraping {url}: {e}")
                continue  # Bỏ qua URL lỗi, tiếp tục URL tiếp theo
        
        await browser.close()  # Đóng browser sau khi xong
    
    logger.info(f"Successfully scraped {len(scraped_deals)}/{len(urls)} products")
    return scraped_deals
