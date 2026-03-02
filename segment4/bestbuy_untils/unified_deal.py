"""
Unified Scraped Deal - Combines deals from multiple sources (BestBuy, Amazon).

This module provides a unified representation for scraped deals,
allowing deals from different sources to be combined into a single pool
for comparison and selection.

Example:
    from price_agents.bestbuy_deals import ScrapedBestBuyDeal
    from price_agents.amazon_deals import ScrapedAmazonDeal
    
    unified_deals = []
    for bb_deal in bestbuy_deals:
        unified_deals.append(UnifiedScrapedDeal.from_bestbuy(bb_deal))
    for az_deal in amazon_deals:
        unified_deals.append(UnifiedScrapedDeal.from_amazon(az_deal))
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from price_agents.bestbuy_deals import ScrapedBestBuyDeal
    from price_agents.amazon_deals import ScrapedAmazonDeal


class UnifiedScrapedDeal:
    """
    A unified representation of a scraped deal from any source (BestBuy or Amazon).
    
    This allows combining deals from different sources into a single pool
    for GPT to select the best ones.
    
    Attributes:
        title: Product title (max 200 chars)
        brand: Product brand (optional)
        price: Sale price in USD
        features: Product features text (max 1500 chars)
        url: Product URL
        source: 'BestBuy' or 'Amazon'
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
        Initialize unified deal.
        
        Args:
            title: Product title
            brand: Product brand (optional)
            price: Sale price in USD
            features: Product features/description text
            url: Product URL
            source: 'BestBuy' or 'Amazon'
        """
        self.title = title[:200] if title else "Unknown"
        self.brand = brand.strip() if brand else None
        self.price = price
        self.features = features[:1500] if features else ""
        self.url = url
        self.source = source
    
    def __repr__(self) -> str:
        """Return a short string description."""
        return f"<[{self.source}] {self.title[:40]}... | ${self.price}>"
    
    def describe(self) -> str:
        """
        Return a longer string to describe this deal for use in calling a model.
        
        Returns:
            Formatted string with Source, Title, Brand, Price, Features, URL
        """
        parts = [f"Source: {self.source}", f"Title: {self.title}"]
        
        if self.brand:
            parts.append(f"Brand: {self.brand}")
        
        parts.append(f"Price: ${self.price:.2f}")
        
        if self.features and len(self.features) > 10:
            parts.append(f"Features: {self.features.strip()}")
        
        parts.append(f"URL: {self.url}")
        
        return "\n".join(parts)
    
    @classmethod
    def from_bestbuy(cls, deal: "ScrapedBestBuyDeal") -> "UnifiedScrapedDeal":
        """
        Convert ScrapedBestBuyDeal to UnifiedScrapedDeal.
        
        Args:
            deal: A ScrapedBestBuyDeal instance
            
        Returns:
            UnifiedScrapedDeal with source='BestBuy'
        """
        return cls(
            title=deal.title,
            brand=deal.brand,
            price=deal.price,
            features=deal.features,
            url=deal.url,
            source="BestBuy"
        )
    
    @classmethod
    def from_amazon(cls, deal: "ScrapedAmazonDeal") -> "UnifiedScrapedDeal":
        """
        Convert ScrapedAmazonDeal to UnifiedScrapedDeal.
        
        Args:
            deal: A ScrapedAmazonDeal instance
            
        Returns:
            UnifiedScrapedDeal with source='Amazon'
        """
        return cls(
            title=deal.title,
            brand=deal.brand,
            price=deal.price,
            features=deal.features,
            url=deal.url,
            source="Amazon"
        )
