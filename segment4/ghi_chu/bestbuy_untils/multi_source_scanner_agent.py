"""
=============================================================================
MULTI-SOURCE SCANNER AGENT - CHỌN TOP 5 DEALS TỪ POOL BESTBUY + AMAZON
=============================================================================
File: bestbuy_untils/multi_source_scanner_agent.py

MỤC ĐÍCH:
- Nhận pool deals từ CẢ BestBuy và Amazon (đã gộp thành UnifiedScrapedDeal)
- Sử dụng GPT-5-mini để chọn ra 5 deals TỐT NHẤT
- Không phân biệt nguồn - chỉ chọn dựa trên chất lượng mô tả và giá

TẠI SAO CẦN AGENT NÀY?
- Pool deals có thể có 10-30 sản phẩm từ cả 2 nguồn
- Cần AI để đánh giá chất lượng và chọn top 5
- GPT có thể hiểu context và so sánh deals

VÍ DỤ SỬ DỤNG:
    # Sau khi gộp deals từ cả 2 nguồn
    unified_deals = [
        UnifiedScrapedDeal(source="BestBuy", ...),
        UnifiedScrapedDeal(source="Amazon", ...),
        ...
    ]
    
    # Chọn top 5
    scanner = MultiSourceScannerAgent()
    selection = scanner.scan(unified_deals)
    # → DealSelection với 5 deals tốt nhất (có thể có cả BestBuy và Amazon)

Author: Refactored from bestbuy4.py
Date: 2026-02-07
=============================================================================
"""

import logging
from typing import List, Optional

from openai import OpenAI

# Import base class và data models
from price_agents.agent import Agent as BaseAgent             # Base class với logging
from price_agents.deals import DealSelection                  # Pydantic schema cho output
from bestbuy_untils.unified_deal import UnifiedScrapedDeal    # Input format


class MultiSourceScannerAgent(BaseAgent):
    """
    Agent sử dụng GPT-5-mini để chọn 5 deals tốt nhất từ pool BestBuy + Amazon.
    
    Kế thừa từ BaseAgent để có:
    - self.log(): Log với màu sắc
    - Color constants (CYAN, GREEN, etc.)
    
    Workflow:
    1. Nhận list UnifiedScrapedDeal (từ cả 2 nguồn)
    2. Filter deals có price > 0
    3. Gọi GPT-5-mini với Structured Outputs
    4. Trả về DealSelection với top 5 deals
    
    Attributes:
        name: Tên agent (hiển thị trong logs)
        color: Màu ANSI cho logs (CYAN)
        MODEL: Model sử dụng (gpt-5-mini)
        openai: OpenAI client instance
    """
    
    # Tên agent (hiển thị trong logs)
    name = "Multi-Source Scanner Agent"
    
    # Màu CYAN cho logs
    color = BaseAgent.CYAN
    
    # Model: GPT-5-mini (cân bằng chi phí và chất lượng)
    MODEL = "gpt-5-mini"
    
    # =========================================================================
    # SYSTEM PROMPT - HƯỚNG DẪN GPT CÁCH CHỌN DEALS
    # =========================================================================
    
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
    # Giải thích prompt:
    # - Rule 1: Focus vào product, không phải terms như "50% off"
    # - Rule 2: Summary ngắn gọn 3-4 câu
    # - Rule 3: QUAN TRỌNG! Prefix [BestBuy] hoặc [Amazon] để biết nguồn
    # - Rule 4: Price > 0 (có deals price = 0 do scrape lỗi)
    # - Rule 5: Giữ URL gốc để user có thể click
    
    # =========================================================================
    # USER PROMPT - TEMPLATE GỬI DEALS CHO GPT
    # =========================================================================
    
    USER_PROMPT_PREFIX = """Respond with the most promising 5 deals from this COMBINED list (BestBuy + Amazon).
Select those which have the most detailed, high quality product description and a clear price that is greater than 0.
You can pick from EITHER source - just choose the 5 best overall deals.

You should rephrase the description to be a summary of the product itself, not the terms of the deal.
START the product_description with "[BestBuy]" or "[Amazon]" to indicate the source.

Deals:

"""
    # Sau PREFIX sẽ là danh sách deals, mỗi deal có format:
    # Source: BestBuy
    # Title: Acer Aspire 5 Laptop
    # Price: $399.99
    # Features: ...
    # URL: https://...
    # ---
    
    USER_PROMPT_SUFFIX = "\n\nInclude up to 5 deals, no more. Pick the best from EITHER source."
    
    def __init__(self):
        """
        Khởi tạo agent với OpenAI client.
        
        OpenAI client sử dụng OPENAI_API_KEY từ environment variables.
        """
        self.log("Multi-Source Scanner Agent đang khởi tạo")
        self.openai = OpenAI()  # Tự động lấy API key từ env
        self.log("Multi-Source Scanner Agent đã sẵn sàng")
    
    def make_user_prompt(self, unified_deals: List[UnifiedScrapedDeal]) -> str:
        """
        Tạo user prompt từ list deals.
        
        Format của prompt:
            [PREFIX]
            Source: BestBuy
            Title: Acer Aspire 5...
            Price: $399.99
            ...
            ---
            Source: Amazon
            Title: Dell Inspiron...
            Price: $449.99
            ...
            [SUFFIX]
        
        Args:
            unified_deals: List deals từ cả 2 nguồn
            
        Returns:
            String prompt để gửi cho GPT
        """
        user_prompt = self.USER_PROMPT_PREFIX
        
        # Gọi deal.describe() cho mỗi deal
        # UnifiedScrapedDeal.describe() trả về formatted string
        user_prompt += "\n\n".join([deal.describe() for deal in unified_deals])
        
        user_prompt += self.USER_PROMPT_SUFFIX
        return user_prompt
    
    def scan(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """
        Gọi GPT-5-mini để chọn top 5 deals từ pool BestBuy + Amazon.
        
        SỬ DỤNG STRUCTURED OUTPUTS:
        - response_format = DealSelection (Pydantic class)
        - GPT trả về JSON đúng format
        - SDK tự động parse thành object
        - Không cần parse JSON thủ công!
        
        Flow:
        1. Validate: Có deals không? Có price > 0 không?
        2. Tạo prompt từ deals
        3. Gọi GPT-5-mini với structured outputs
        4. Filter lại deals có price <= 0 (GPT đôi khi trả về sai)
        5. Return DealSelection
        
        Args:
            unified_deals: List UnifiedScrapedDeal từ cả 2 nguồn
            
        Returns:
            DealSelection với tối đa 5 deals, hoặc None nếu không có deals hợp lệ
            
        DealSelection schema:
            class DealSelection(BaseModel):
                deals: List[Deal]  # Tối đa 5 deals
                
            class Deal(BaseModel):
                product_description: str
                price: float
                url: str
        """
        # VALIDATE 1: Có deals không?
        if not unified_deals:
            self.log("Không có deals để scan")
            return None
        
        # VALIDATE 2: Filter deals có price > 0
        # Một số deals có price = 0 do scrape lỗi
        valid_deals = [d for d in unified_deals if d.price > 0]
        if not valid_deals:
            self.log("Không có deals với price > 0")
            return None
        
        # TẠO PROMPT
        user_prompt = self.make_user_prompt(valid_deals)
        
        self.log(f"Đang gọi {self.MODEL} với {len(valid_deals)} deals (BestBuy + Amazon)...")
        
        # GỌI GPT-5-MINI VỚI STRUCTURED OUTPUTS
        # Key point: response_format=DealSelection
        # GPT sẽ trả về JSON đúng format của DealSelection
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=DealSelection,  # Pydantic schema
        )
        
        # PARSE RESPONSE
        # result.choices[0].message.parsed đã là DealSelection object
        # Không cần json.loads() hay parse thủ công!
        selection = result.choices[0].message.parsed
        
        # FILTER LẠI: GPT đôi khi vẫn trả về deals với price <= 0
        selection.deals = [deal for deal in selection.deals if deal.price > 0]
        
        self.log(f"Đã chọn {len(selection.deals)} deals từ pool tổng hợp")
        
        return selection
