"""
Multi-Source Scanner Agent - Selects best deals from combined BestBuy + Amazon pool.

Uses GPT-5-mini with structured outputs to select the top 5 deals
from a unified pool containing products from both BestBuy and Amazon.

Example:
    from price_agents.unified_deal import UnifiedScrapedDeal
    
    unified_deals = [...]  # List of UnifiedScrapedDeal from both sources
    scanner = MultiSourceScannerAgent()
    selection = scanner.scan(unified_deals)
    # Returns DealSelection with top 5 deals (may include both sources)
"""

import logging
from typing import List, Optional

from openai import OpenAI

from price_agents.agent import Agent as BaseAgent
from price_agents.deals import DealSelection
from bestbuy_untils.unified_deal import UnifiedScrapedDeal


class MultiSourceScannerAgent(BaseAgent):
    """
    Agent that uses GPT-5-mini to select the best 5 deals from BOTH BestBuy and Amazon.
    
    This agent:
    1. Takes a list of UnifiedScrapedDeal objects (from both sources)
    2. Uses GPT-5-mini with structured outputs
    3. Returns a DealSelection with the best 5 deals (may include both sources)
    
    Attributes:
        name: Agent name for logging
        color: ANSI color for logs
        MODEL: OpenAI model to use
        openai: OpenAI client instance
    """
    
    name = "Multi-Source Scanner Agent"
    color = BaseAgent.CYAN
    MODEL = "gpt-5-mini"
    
    SYSTEM_PROMPT = """You identify and summarize the 5 most detailed deals from a combined list of products from BestBuy and Amazon.
Select deals that have the most detailed, high quality description and the most clear price.
You can select from EITHER source (BestBuy or Amazon) - pick the best overall deals.

Respond strictly in JSON with no explanation. You should provide the price as a number derived from the description.
Most important is that you respond with the 5 deals that have the most detailed product description with price.

**IMPORTANT:**
1. Focus on the product features and specifications, not sales terms.
2. The product_description should be a 3-4 sentence summary of the product itself.
3. Include the SOURCE (BestBuy or Amazon) at the beginning of product_description.
4. Price must be greater than 0.
5. Keep the original URL exactly as provided.
"""
    
    USER_PROMPT_PREFIX = """Respond with the most promising 5 deals from this COMBINED list (BestBuy + Amazon).
Select those which have the most detailed, high quality product description and a clear price that is greater than 0.
You can pick from EITHER source - just choose the 5 best overall deals.

You should rephrase the description to be a summary of the product itself, not the terms of the deal.
START the product_description with "[BestBuy]" or "[Amazon]" to indicate the source.

Deals:

"""
    
    USER_PROMPT_SUFFIX = "\n\nInclude up to 5 deals, no more. Pick the best from EITHER source."
    
    def __init__(self):
        """Initialize with OpenAI client."""
        self.log("Multi-Source Scanner Agent is initializing")
        self.openai = OpenAI()
        self.log("Multi-Source Scanner Agent is ready")
    
    def make_user_prompt(self, unified_deals: List[UnifiedScrapedDeal]) -> str:
        """
        Create user prompt from unified deals.
        
        Args:
            unified_deals: List of UnifiedScrapedDeal objects from both sources
            
        Returns:
            Formatted prompt string for GPT
        """
        user_prompt = self.USER_PROMPT_PREFIX
        user_prompt += "\n\n".join([deal.describe() for deal in unified_deals])
        user_prompt += self.USER_PROMPT_SUFFIX
        return user_prompt
    
    def scan(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """
        Call GPT-5-mini to select the best 5 deals from combined BestBuy + Amazon pool.
        
        Uses OpenAI structured outputs to ensure response conforms to DealSelection schema.
        
        Args:
            unified_deals: List of UnifiedScrapedDeal from both sources
            
        Returns:
            DealSelection with up to 5 best deals, or None if no valid deals
        """
        if not unified_deals:
            self.log("No deals to scan")
            return None
        
        # Filter deals with price > 0
        valid_deals = [d for d in unified_deals if d.price > 0]
        if not valid_deals:
            self.log("No deals with valid price > 0")
            return None
        
        user_prompt = self.make_user_prompt(valid_deals)
        
        self.log(f"Calling {self.MODEL} with {len(valid_deals)} deals (BestBuy + Amazon)...")
        
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=DealSelection,
        )
        
        selection = result.choices[0].message.parsed
        
        # Filter out any deals with price <= 0
        selection.deals = [deal for deal in selection.deals if deal.price > 0]
        
        self.log(f"Selected {len(selection.deals)} deals from combined pool")
        
        return selection
