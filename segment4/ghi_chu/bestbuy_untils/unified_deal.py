"""
=============================================================================
UNIFIED SCRAPED DEAL - GỘP DEALS TỪ NHIỀU NGUỒN (BESTBUY + AMAZON)
=============================================================================
File: bestbuy_untils/unified_deal.py

MỤC ĐÍCH:
- Tạo format thống nhất cho deals từ BestBuy và Amazon
- Cho phép gộp deals từ cả 2 nguồn vào 1 pool để so sánh
- GPT có thể chọn top 5 từ pool tổng hợp

TẠI SAO CẦN FILE NÀY?
- BestBuy và Amazon có format deals khác nhau (ScrapedBestBuyDeal vs ScrapedAmazonDeal)
- Cần 1 format chung để gộp vào 1 list
- MultiSourceScannerAgent cần 1 format duy nhất để chọn top 5

VÍ DỤ SỬ DỤNG:
    # Sau khi scrape từ cả 2 nguồn
    bestbuy_scraped = [ScrapedBestBuyDeal(...), ...]
    amazon_scraped = [ScrapedAmazonDeal(...), ...]
    
    # Gộp vào pool thống nhất
    unified_deals = []
    for deal in bestbuy_scraped:
        unified_deals.append(UnifiedScrapedDeal.from_bestbuy(deal))
    for deal in amazon_scraped:
        unified_deals.append(UnifiedScrapedDeal.from_amazon(deal))
    
    # unified_deals giờ chứa deals từ cả 2 nguồn, cùng format
    # GPT có thể chọn top 5 từ pool này
"""

from typing import Optional, TYPE_CHECKING

# TYPE_CHECKING: Import chỉ khi type checking, tránh circular import
if TYPE_CHECKING:
    from price_agents.bestbuy_deals import ScrapedBestBuyDeal
    from price_agents.amazon_deals import ScrapedAmazonDeal


class UnifiedScrapedDeal:
    """
    Format thống nhất cho deal từ BÀT KỲ nguồn nào (BestBuy hoặc Amazon).
    
    Cho phép gộp deals từ nhiều nguồn vào 1 pool để:
    - So sánh deals giữa các nguồn
    - GPT chọn top 5 từ pool tổng hợp
    - Không quan trọng deal đến từ đâu, chỉ cần chất lượng
    
    Attributes:
        title: Tên sản phẩm (tối đa 200 ký tự)
        brand: Thương hiệu (optional, VD: "Acer", "Samsung")
        price: Giá sale hiện tại (USD)
        features: Mô tả/tính năng sản phẩm (tối đa 1500 ký tự)
        url: Link sản phẩm gốc
        source: Nguồn gốc - 'BestBuy' hoặc 'Amazon'
    
    VD:
        deal = UnifiedScrapedDeal(
            title="Acer Aspire 5 Laptop...",
            brand="Acer",
            price=449.99,
            features="15.6 inch, AMD Ryzen 5, 8GB RAM...",
            url="https://www.bestbuy.com/site/...",
            source="BestBuy"
        )
    """
    
    def __init__(
        self,
        title: str,
        brand: Optional[str],
        price: float,
        features: str,
        url: str,
        source: str
    ):
        """
        Khởi tạo UnifiedScrapedDeal.
        
        Tự động truncate title (200 chars) và features (1500 chars)
        để tránh prompt quá dài khi gửi cho GPT.
        
        Args:
            title: Tên sản phẩm
            brand: Thương hiệu (có thể None)
            price: Giá sale (USD)
            features: Mô tả/tính năng
            url: Link sản phẩm
            source: 'BestBuy' hoặc 'Amazon'
        """
        # Truncate title tối đa 200 ký tự (tránh prompt quá dài)
        self.title = title[:200] if title else "Unknown"
        
        # Brand có thể None, strip whitespace nếu có
        self.brand = brand.strip() if brand else None
        
        # Giá sale (float, USD)
        self.price = price
        
        # Truncate features tối đa 1500 ký tự
        self.features = features[:1500] if features else ""
        
        # URL gốc (giữ nguyên)
        self.url = url
        
        # Nguồn: 'BestBuy' hoặc 'Amazon'
        self.source = source
    
    def __repr__(self) -> str:
        """
        String ngắn gọn để debug.
        
        VD: <[BestBuy] Acer Aspire 5 Laptop 15.6 inch AMD R... | $449.99>
        """
        return f"<[{self.source}] {self.title[:40]}... | ${self.price}>"
    
    def describe(self) -> str:
        """
        Tạo string dài để gửi cho GPT.
        
        Format được thiết kế để GPT dễ đọc và extract thông tin:
        - Source: BestBuy
        - Title: Acer Aspire 5...
        - Brand: Acer
        - Price: $449.99
        - Features: 15.6 inch, AMD Ryzen 5...
        - URL: https://...
        
        Returns:
            String đa dòng với đầy đủ thông tin sản phẩm
        """
        parts = [f"Source: {self.source}", f"Title: {self.title}"]
        
        # Chỉ thêm brand nếu có
        if self.brand:
            parts.append(f"Brand: {self.brand}")
        
        parts.append(f"Price: ${self.price:.2f}")
        
        # Chỉ thêm features nếu có nội dung (> 10 chars)
        if self.features and len(self.features) > 10:
            parts.append(f"Features: {self.features.strip()}")
        
        parts.append(f"URL: {self.url}")
        
        return "\n".join(parts)
    
    # =========================================================================
    # CLASS METHODS: FACTORY PATTERN - TẠO TỪ CÁC NGUỒN KHÁC NHAU
    # =========================================================================
    
    @classmethod
    def from_bestbuy(cls, deal: "ScrapedBestBuyDeal") -> "UnifiedScrapedDeal":
        """
        Factory method: Chuyển đổi ScrapedBestBuyDeal → UnifiedScrapedDeal.
        
        Sử dụng @classmethod để có thể gọi:
            unified = UnifiedScrapedDeal.from_bestbuy(bestbuy_deal)
        
        Args:
            deal: ScrapedBestBuyDeal từ price_agents/bestbuy_deals.py
            
        Returns:
            UnifiedScrapedDeal với source='BestBuy'
        """
        return cls(
            title=deal.title,
            brand=deal.brand,
            price=deal.price,
            features=deal.features,
            url=deal.url,
            source="BestBuy"  # Đánh dấu nguồn
        )
    
    @classmethod
    def from_amazon(cls, deal: "ScrapedAmazonDeal") -> "UnifiedScrapedDeal":
        """
        Factory method: Chuyển đổi ScrapedAmazonDeal → UnifiedScrapedDeal.
        
        Sử dụng @classmethod để có thể gọi:
            unified = UnifiedScrapedDeal.from_amazon(amazon_deal)
        
        Args:
            deal: ScrapedAmazonDeal từ price_agents/amazon_deals.py
            
        Returns:
            UnifiedScrapedDeal với source='Amazon'
        """
        return cls(
            title=deal.title,
            brand=deal.brand,
            price=deal.price,
            features=deal.features,
            url=deal.url,
            source="Amazon"  # Đánh dấu nguồn
        )
