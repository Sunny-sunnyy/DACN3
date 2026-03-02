"""
=============================================================================
BESTBUY SCANNER AGENT MODULE - TÌM KIẾM VÀ CHỌN DEALS TỪ BESTBUY
=============================================================================
File: price_agents/bestbuy_scanner_agent.py

MỤC ĐÍCH:
- Tìm kiếm URLs sản phẩm BestBuy bằng Brave Search (BestBuySearchAgent)
- Chọn top 5 deals tốt nhất bằng GPT-5-mini (BestBuyScannerAgent)

CÁC AGENT TRONG FILE:
1. BestBuySearchAgent: Tìm URLs sản phẩm trên BestBuy
   - Input: Keyword (VD: "laptop")
   - Tool: Brave MCP Server + GPT-5-nano
   - Output: List URLs sản phẩm

2. BestBuyScannerAgent: Chọn top 5 deals từ danh sách đã scrape
   - Input: List[ScrapedBestBuyDeal] (từ Playwright)
   - Tool: GPT-5-mini + Structured Outputs
   - Output: DealSelection (5 deals tốt nhất)

WORKFLOW TRONG PIPELINE:
1. BestBuySearchAgent.search("laptop") → 15 URLs
2. filter_sale_urls(urls) → 8 URLs đang sale
3. scrape_bestbuy_products(sale_urls) → 8 ScrapedBestBuyDeal
4. BestBuyScannerAgent.scan(deals) → DealSelection (5 deals)
"""

import os
import asyncio
import logging
from typing import Optional, List

from openai import OpenAI
from pydantic import BaseModel, Field
from agents import Agent, Runner, trace    # OpenAI Agents SDK
from agents.mcp import MCPServerStdio       # MCP Server cho Brave Search
from dotenv import load_dotenv

from price_agents.agent import Agent as BaseAgent   # Base class với logging
from price_agents.deals import Deal, DealSelection  # Pydantic schemas
from price_agents.bestbuy_deals import ScrapedBestBuyDeal


load_dotenv(override=True)  # Load BRAVE_API_KEY từ .env


# Logging setup
logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC SCHEMA CHO KẾT QUẢ TÌM KIẾM
# =============================================================================

class SearchResults(BaseModel):
    """
    Schema cho kết quả trả về từ BestBuySearchAgent.
    
    Dùng Pydantic để GPT trả về đúng format với Structured Outputs.
    
    Attributes:
        product_urls: List URLs sản phẩm BestBuy
    """
    product_urls: List[str] = Field(description="List of BestBuy product URLs")


# =============================================================================
# BESTBUY SEARCH AGENT - TÌM KIẾM URLS SẢN PHẨM
# =============================================================================

class BestBuySearchAgent(BaseAgent):
    """
    Agent tìm kiếm URLs sản phẩm trên BestBuy bằng Brave Search.
    
    Sử dụng:
    - Brave MCP Server: Query Brave Search API
    - GPT-5-nano: Xử lý kết quả, extract URLs đúng format
    
    Workflow:
    1. Nhận keyword (VD: "Smart TV")
    2. Query Brave: keyword + "site:bestbuy.com/product"
    3. GPT-5-nano filter và trả về URLs đúng format
    
    Attributes:
        name: Tên agent (hiển thị trong logs)
        color: Màu ANSI cho logs
        MODEL: Model sử dụng (gpt-5-nano - nhẹ và rẻ)
        brave_api_key: API key cho Brave Search
    
    VD sử dụng:
        agent = BestBuySearchAgent()
        urls = agent.search("laptop", max_urls=10)
        # → ["https://www.bestbuy.com/site/...", ...]
    """
    
    name = "BestBuy Search Agent"
    color = BaseAgent.CYAN
    MODEL = "gpt-5-nano"  # Model nhẹ, rẻ cho task đơn giản
    
    # -----------------------------------------------------------------
    # INSTRUCTIONS CHO GPT-5-NANO
    # -----------------------------------------------------------------
    INSTRUCTIONS = """
You are a web search agent. Your job is to find product URLs on BestBuy.

STEPS:
1. Use brave_web_search with: keyword + "site:bestbuy.com/product"
2. Extract product URLs from results
3. Return ONLY URLs matching: https://www.bestbuy.com/product/...

IMPORTANT:
- Do NOT return search page URLs
- Do NOT return category page URLs
- Return up to 15 product URLs
- Focus on products that are likely to be on sale
"""
    # Giải thích:
    # - site:bestbuy.com/product: Chỉ tìm trong subdomain product
    # - Loại bỏ search pages (bestbuy.com/s?...)
    # - Loại bỏ category pages (bestbuy.com/category/...)
    
    def __init__(self):
        """
        Khởi tạo agent.
        
        Load BRAVE_API_KEY từ environment variable.
        Raise ValueError nếu không tìm thấy key.
        """
        self.log("BestBuy Search Agent is initializing")
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        if not self.brave_api_key:
            raise ValueError("BRAVE_API_KEY not found in environment variables")
        self.log("BestBuy Search Agent is ready")
    
    def get_brave_params(self) -> dict:
        """
        Tạo params cho Brave MCP Server.
        
        MCP Server sẽ được spawn bằng npx với API key.
        
        Returns:
            Dict params cho MCPServerStdio
        """
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": self.brave_api_key}
        }
    
    def run_async_task(self, coro):
        """
        Helper để chạy async task trong sync context.
        
        Xử lý trường hợp:
        - Không có event loop → tạo mới
        - Đã có event loop (VD: trong Jupyter) → dùng nest_asyncio
        
        Args:
            coro: Coroutine cần chạy
            
        Returns:
            Kết quả của coroutine
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Không có loop → tạo mới
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        else:
            # Đã có loop (Jupyter, etc.) → dùng nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
    
    async def _search_async(self, keyword: str, max_urls: int = 15) -> List[str]:
        """
        Async implementation của search.
        
        Sử dụng OpenAI Agents SDK với Brave MCP Server.
        
        Args:
            keyword: Từ khóa tìm kiếm (VD: "Smart TV")
            max_urls: Số URLs tối đa trả về
            
        Returns:
            List URLs sản phẩm BestBuy
        """
        self.log(f"Searching for: {keyword}")
        
        # Khởi động Brave MCP Server
        async with MCPServerStdio(
            params=self.get_brave_params(),
            client_session_timeout_seconds=60
        ) as brave_server:
            
            # Tạo OpenAI Agent với MCP Server
            search_agent = Agent(
                name="SearchAgent",
                instructions=self.INSTRUCTIONS,
                model=self.MODEL,
                mcp_servers=[brave_server],  # Gắn MCP Server
                output_type=SearchResults    # Structured Output
            )
            
            # Chạy agent
            result = await Runner.run(
                search_agent,
                f"Search for {keyword} on BestBuy",
                max_turns=30  # Số lượt tối đa agent được gọi tools
            )
            
            # Lấy URLs từ kết quả
            urls = result.final_output.product_urls[:max_urls]
            self.log(f"Found {len(urls)} product URLs")
            return urls
    
    def search(self, keyword: str, max_urls: int = 15) -> List[str]:
        """
        Tìm kiếm URLs sản phẩm BestBuy bằng Brave Search.
        
        Đây là sync wrapper cho _search_async.
        
        Args:
            keyword: Từ khóa tìm kiếm (VD: "Smart TV", "laptop")
            max_urls: Số URLs tối đa trả về (default: 15)
            
        Returns:
            List URLs sản phẩm BestBuy
        
        VD:
            agent = BestBuySearchAgent()
            urls = agent.search("laptop", max_urls=10)
        """
        return self.run_async_task(self._search_async(keyword, max_urls))


# =============================================================================
# BESTBUY SCANNER AGENT - CHỌN TOP 5 DEALS
# =============================================================================

class BestBuyScannerAgent(BaseAgent):
    """
    Agent chọn top 5 deals từ danh sách sản phẩm BestBuy đã scrape.
    
    Sử dụng:
    - GPT-5-mini với Structured Outputs
    - Đánh giá chất lượng mô tả và giá
    
    Workflow:
    1. Nhận List[ScrapedBestBuyDeal] từ Playwright scraping
    2. Filter deals có price > 0
    3. Gọi GPT-5-mini để chọn 5 deals tốt nhất
    4. Trả về DealSelection
    
    Tiêu chí chọn deals:
    - Mô tả chi tiết, chất lượng cao
    - Giá rõ ràng (> 0)
    - Focus vào product features, không phải sales terms
    
    VD sử dụng:
        scanner = BestBuyScannerAgent()
        selection = scanner.scan(scraped_deals)
        # → DealSelection với 5 deals
    """
    
    name = "BestBuy Scanner Agent"
    color = BaseAgent.CYAN
    MODEL = "gpt-5-mini"
    
    # -----------------------------------------------------------------
    # PROMPTS CHO GPT-5-MINI
    # -----------------------------------------------------------------
    SYSTEM_PROMPT = """You identify and summarize the 5 most detailed deals from a list, by selecting deals that have the most detailed, high quality description and the most clear price.
    Respond strictly in JSON with no explanation, using this format. You should provide the price as a number derived from the description.
    Most important is that you respond with the 5 deals that have the most detailed product description with price.
    
    **IMPORTANT:**
    1. Focus on the product features and specifications, not sales terms.
    2. The product_description should be a 3-4 sentence summary of the product itself.
    3. Price must be greater than 0.
    4. Keep the original URL exactly as provided.
    """
    # Giải thích:
    # - Rule 1: Focus vào product, không phải "50% off" hay "limited time"
    # - Rule 2: Summary ngắn gọn 3-4 câu
    # - Rule 3: Bỏ qua deals có price = 0 (lỗi scrape)
    # - Rule 4: Giữ URL gốc để user có thể click
    
    USER_PROMPT_PREFIX = """Respond with the most promising 5 deals from this list, selecting those which have the most detailed, high quality product description and a clear price that is greater than 0.
    You should rephrase the description to be a summary of the product itself, not the terms of the deal.
    Remember to respond with a short paragraph of text in the product_description field for each of the 5 items that you select.
    
    Deals:
    
    """
    
    USER_PROMPT_SUFFIX = "\n\nInclude up to 5 deals, no more."
    
    def __init__(self):
        """Khởi tạo với OpenAI client."""
        self.log("BestBuy Scanner Agent is initializing")
        self.openai = OpenAI()
        self.log("BestBuy Scanner Agent is ready")
    
    def make_user_prompt(self, scraped_deals: List[ScrapedBestBuyDeal]) -> str:
        """
        Tạo user prompt từ danh sách deals đã scrape.
        
        Format:
            [PREFIX]
            Title: Acer Aspire 5...
            Brand: Acer
            Price: $449.99
            Features: ...
            URL: https://...
            
            Title: Dell Inspiron...
            ...
            [SUFFIX]
        
        Args:
            scraped_deals: List deals đã scrape
            
        Returns:
            String prompt để gửi cho GPT
        """
        user_prompt = self.USER_PROMPT_PREFIX
        user_prompt += "\n\n".join([deal.describe() for deal in scraped_deals])
        user_prompt += self.USER_PROMPT_SUFFIX
        return user_prompt
    
    def scan(self, scraped_deals: List[ScrapedBestBuyDeal]) -> Optional[DealSelection]:
        """
        Gọi GPT-5-mini để chọn top 5 deals với mô tả và giá tốt nhất.
        
        Sử dụng OpenAI Structured Outputs:
        - response_format = DealSelection (Pydantic)
        - GPT trả về JSON đúng format
        - SDK tự động parse
        
        Args:
            scraped_deals: List ScrapedBestBuyDeal từ Playwright
            
        Returns:
            DealSelection với tối đa 5 deals, hoặc None nếu không có deals hợp lệ
        """
        if not scraped_deals:
            self.log("No deals to scan")
            return None
        
        # Filter deals có price > 0 (bỏ deals lỗi)
        valid_deals = [d for d in scraped_deals if d.price > 0]
        if not valid_deals:
            self.log("No deals with valid price > 0")
            return None
        
        user_prompt = self.make_user_prompt(valid_deals)
        
        self.log(f"Calling {self.MODEL} with {len(valid_deals)} deals...")
        
        # Gọi GPT-5-mini với Structured Outputs
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=DealSelection,  # Pydantic schema
        )
        
        selection = result.choices[0].message.parsed
        
        # Filter lại: GPT đôi khi vẫn trả về deals với price <= 0
        selection.deals = [deal for deal in selection.deals if deal.price > 0]
        
        self.log(f"Selected {len(selection.deals)} deals")
        
        return selection
