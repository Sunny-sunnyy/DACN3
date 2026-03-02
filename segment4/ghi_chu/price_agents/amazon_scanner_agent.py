"""
=============================================================================
AMAZON SCANNER AGENT MODULE - TÌM KIẾM VÀ CHỌN DEALS TỪ AMAZON
=============================================================================
File: price_agents/amazon_scanner_agent.py

MỤC ĐÍCH:
- Tìm kiếm URLs sản phẩm Amazon bằng Brave Search (AmazonSearchAgent)
- Chọn top 5 deals tốt nhất bằng GPT-5-mini (AmazonScannerAgent)

CÁC AGENT:
1. AmazonSearchAgent: Tìm URLs với Brave MCP + GPT-5-nano
2. AmazonScannerAgent: Chọn top 5 với GPT-5-mini + Structured Outputs
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
logger = logging.getLogger(__name__)


class SearchResults(BaseModel):
    """URLs từ Brave Search."""
    product_urls: List[str] = Field(description="List of Amazon product URLs")


# =============================================================================
# AMAZON SEARCH AGENT - TÌM URLs
# =============================================================================

class AmazonSearchAgent(BaseAgent):
    """
    Tìm URLs sản phẩm Amazon bằng Brave Search.
    
    Sử dụng:
    - Brave MCP Server: Query Brave Search API
    - GPT-5-nano: Extract URLs đúng format /dp/ASIN
    """
    
    name = "Amazon Search Agent"
    color = BaseAgent.GREEN
    MODEL = "gpt-5-nano"
    
    INSTRUCTIONS = """You are a web search agent. Your job is to find product URLs on Amazon.

STEPS:
1. Use brave_web_search with the given search query
2. Extract product URLs from results
3. Return ONLY URLs that are Amazon product pages

VALID Amazon product URL patterns:
- https://www.amazon.com/PRODUCT-NAME/dp/XXXXXXXXXX
- The ASIN code (after /dp/) is 10 characters

IMPORTANT:
- Do NOT return search pages (amazon.com/s?k=...)
- Do NOT return category pages
- Return as many product URLs as you can find
"""
    
    def __init__(self):
        self.log("Amazon Search Agent is initializing")
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        if not self.brave_api_key:
            raise ValueError("BRAVE_API_KEY not found")
        self.log("Amazon Search Agent is ready")
    
    def get_brave_params(self) -> dict:
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": self.brave_api_key}
        }
    
    def run_async_task(self, coro):
        """Chạy async trong sync context."""
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
                
                result = await Runner.run(
                    search_agent,
                    f"Search for '{keyword}' on Amazon. Return Amazon product URLs with /dp/ pattern.",
                    max_turns=30
                )
                
                urls = result.final_output.product_urls[:max_urls]
                self.log(f"Found {len(urls)} product URLs")
                return urls
    
    def search(self, keyword: str, max_urls: int = 15) -> List[str]:
        """Tìm URLs sản phẩm Amazon."""
        return self.run_async_task(self._search_async(keyword, max_urls))


# =============================================================================
# AMAZON SCANNER AGENT - CHỌN TOP 5
# =============================================================================

class AmazonScannerAgent(BaseAgent):
    """
    Chọn top 5 deals từ danh sách Amazon đã scrape.
    
    Sử dụng GPT-5-mini + Structured Outputs.
    """
    
    name = "Amazon Scanner Agent"
    color = BaseAgent.CYAN
    MODEL = "gpt-5-mini"
    
    SYSTEM_PROMPT = """You identify and summarize the 5 most detailed deals from a list.
    Select deals with detailed description and clear price > 0.
    Respond strictly in JSON.
    
    IMPORTANT:
    1. Focus on product features, not sales terms.
    2. product_description should be 3-4 sentence summary.
    3. Price must be greater than 0.
    4. Keep original URL exactly as provided.
    """
    
    USER_PROMPT_PREFIX = """Respond with the most promising deals (up to 5).
    Rephrase description as product summary.
    
    Deals:
    
    """
    
    USER_PROMPT_SUFFIX = "\n\nInclude up to 5 deals, no more."
    
    def __init__(self):
        self.log("Amazon Scanner Agent is initializing")
        self.openai = OpenAI()
        self.log("Amazon Scanner Agent is ready")
    
    def make_user_prompt(self, scraped_deals: List[ScrapedAmazonDeal]) -> str:
        user_prompt = self.USER_PROMPT_PREFIX
        user_prompt += "\n\n".join([deal.describe() for deal in scraped_deals])
        user_prompt += self.USER_PROMPT_SUFFIX
        return user_prompt
    
    def scan(self, scraped_deals: List[ScrapedAmazonDeal]) -> Optional[DealSelection]:
        """Gọi GPT-5-mini chọn top 5 deals."""
        if not scraped_deals:
            self.log("No deals to scan")
            return None
        
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
        selection.deals = [deal for deal in selection.deals if deal.price > 0]
        
        self.log(f"Selected {len(selection.deals)} deals")
        return selection
