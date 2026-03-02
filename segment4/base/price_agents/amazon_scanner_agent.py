"""
Amazon Scanner Agent Module

This module contains agents for searching and selecting Amazon products:
- AmazonSearchAgent: Uses Brave MCP to search for product URLs
- AmazonScannerAgent: Uses GPT-5-mini to select the best 5 deals
"""

import os
import asyncio
import logging
from typing import Optional, List

from openai import OpenAI
from pydantic import BaseModel, Field
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

from price_agents.agent import Agent as BaseAgent
from price_agents.deals import Deal, DealSelection
from price_agents.amazon_deals import ScrapedAmazonDeal


load_dotenv(override=True)


# Logging setup
logger = logging.getLogger(__name__)


class SearchResults(BaseModel):
    """URLs found from Brave Search."""
    product_urls: List[str] = Field(description="List of Amazon product URLs")


class AmazonSearchAgent(BaseAgent):
    """
    Agent that uses Brave MCP Server to search for Amazon product URLs.
    
    This agent:
    1. Takes a keyword (e.g., "laptop")
    2. Uses Brave Search with site:amazon.com filter
    3. Returns a list of Amazon product URLs (format: /dp/ASIN or /gp/product/ASIN)
    """
    
    name = "Amazon Search Agent"
    color = BaseAgent.GREEN
    MODEL = "gpt-5-nano"
    
    # INSTRUCTIONS cho việc tìm kiếm Amazon
    INSTRUCTIONS = """You are a web search agent. Your job is to find product URLs on Amazon.

STEPS:
1. Use brave_web_search with the given search query
2. Extract product URLs from results
3. Return ONLY URLs that are Amazon product pages

VALID Amazon product URL patterns (based on actual results):
- https://www.amazon.com/PRODUCT-NAME/dp/XXXXXXXXXX
- https://www.amazon.com/*/dp/XXXXXXXXXX
- Examples:
  - https://www.amazon.com/amazon-fire-tv-43-inch-4-series-4k-smart-tv/dp/B0CZ9WV2ZX
  - https://www.amazon.com/Apple-2025-MacBook-13-inch-Laptop/dp/B0DZD9S5GC
  - https://www.amazon.com/ASUS-Gaming-Laptop-Nebula-Display/dp/B0DW1X5YCQ

IMPORTANT:
- The ASIN code (after /dp/) is 10 characters (letters and numbers)
- Do NOT return search pages (amazon.com/s?k=...)
- Do NOT return category or brand pages
- Do NOT return Amazon homepage
- Return as many product URLs as you can find
"""
    
    def __init__(self):
        """Initialize the search agent."""
        self.log("Amazon Search Agent is initializing")
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        if not self.brave_api_key:
            raise ValueError("BRAVE_API_KEY not found in environment variables")
        self.log("Amazon Search Agent is ready")
    
    def get_brave_params(self) -> dict:
        """Get Brave MCP server parameters."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": self.brave_api_key}
        }
    
    def run_async_task(self, coro):
        """Run async task, handling existing event loops."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        else:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
    
    async def _search_async(self, keyword: str, max_urls: int = 15) -> List[str]:
        """
        Async implementation of search.
        
        Args:
            keyword: Product keyword to search (e.g., "Smart TV")
            max_urls: Maximum number of URLs to return
            
        Returns:
            List of Amazon product URLs
        """
        self.log(f"Searching for: {keyword}")
        
        async with MCPServerStdio(
            params=self.get_brave_params(),
            client_session_timeout_seconds=60
        ) as brave_server:
            
            with trace(workflow_name="Amazon Search", group_id=keyword):
                search_agent = Agent(
                    name="AmazonSearchAgent",
                    instructions=self.INSTRUCTIONS,
                    model=self.MODEL,
                    mcp_servers=[brave_server],
                    output_type=SearchResults
                )
                
                # Prompt emphasizes count=10
                result = await Runner.run(
                    search_agent,
                    f"Search for '{keyword}' on Amazon. Return Amazon product URLs with /dp/ pattern.",
                    max_turns=30
                )
                
                urls = result.final_output.product_urls[:max_urls]
                self.log(f"Found {len(urls)} product URLs")
                return urls
    
    def search(self, keyword: str, max_urls: int = 15) -> List[str]:
        """
        Search for Amazon products using Brave Search.
        
        Args:
            keyword: Product keyword to search (e.g., "Smart TV", "laptop")
            max_urls: Maximum number of URLs to return (default: 10)
            
        Returns:
            List of Amazon product URLs
        """
        return self.run_async_task(self._search_async(keyword, max_urls))


class AmazonScannerAgent(BaseAgent):
    """
    Agent that uses GPT-5-mini to select the best 5 deals from scraped Amazon products.
    
    This agent:
    1. Takes a list of ScrapedAmazonDeal objects
    2. Uses GPT-5-mini with structured outputs
    3. Returns a DealSelection with the best 5 deals
    """
    
    name = "Amazon Scanner Agent"
    color = BaseAgent.CYAN
    MODEL = "gpt-5-mini"
    
    SYSTEM_PROMPT = """You identify and summarize the 5 most detailed deals from a list, by selecting deals that have the most detailed, high quality description and the most clear price.
    Respond strictly in JSON with no explanation, using this format. You should provide the price as a number derived from the description.
    Most important is that you respond with the 5 deals that have the most detailed product description with price.
    
    **IMPORTANT:**
    1. Focus on the product features and specifications, not sales terms.
    2. The product_description should be a 3-4 sentence summary of the product itself.
    3. Price must be greater than 0.
    4. Keep the original URL exactly as provided.
    """
    
    USER_PROMPT_PREFIX = """Respond with the most promising deals from this list (up to 5), selecting those which have the most detailed, high quality product description and a clear price that is greater than 0.
    You should rephrase the description to be a summary of the product itself, not the terms of the deal.
    Remember to respond with a short paragraph of text in the product_description field for each item that you select.
    
    Deals:
    
    """
    
    USER_PROMPT_SUFFIX = "\n\nInclude up to 5 deals, no more."
    
    def __init__(self):
        """Initialize with OpenAI client."""
        self.log("Amazon Scanner Agent is initializing")
        self.openai = OpenAI()
        self.log("Amazon Scanner Agent is ready")
    
    def make_user_prompt(self, scraped_deals: List[ScrapedAmazonDeal]) -> str:
        """
        Create user prompt from scraped deals.
        
        Args:
            scraped_deals: List of ScrapedAmazonDeal objects
            
        Returns:
            Formatted prompt string for GPT
        """
        user_prompt = self.USER_PROMPT_PREFIX
        user_prompt += "\n\n".join([deal.describe() for deal in scraped_deals])
        user_prompt += self.USER_PROMPT_SUFFIX
        return user_prompt
    
    def scan(self, scraped_deals: List[ScrapedAmazonDeal]) -> Optional[DealSelection]:
        """
        Call GPT-5-mini to select the best deals with good descriptions and prices.
        
        Uses OpenAI structured outputs to ensure response conforms to DealSelection schema.
        
        Args:
            scraped_deals: List of ScrapedAmazonDeal from Playwright scraping
            
        Returns:
            DealSelection with up to 5 best deals, or None if no valid deals
        """
        if not scraped_deals:
            self.log("No deals to scan")
            return None
        
        # Filter deals with price > 0
        valid_deals = [d for d in scraped_deals if d.price > 0]
        if not valid_deals:
            self.log("No deals with valid price > 0")
            return None
        
        user_prompt = self.make_user_prompt(valid_deals)
        
        self.log(f"Calling {self.MODEL} with {len(valid_deals)} deals...")
        
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
        
        self.log(f"Selected {len(selection.deals)} deals")
        
        return selection
