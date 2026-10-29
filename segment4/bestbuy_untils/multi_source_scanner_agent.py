"""
Multi-Source Scanner Agent - Selects best deals from combined BestBuy + Amazon pool.

Uses OpenAI gpt-6-luna with structured outputs to select
the top 3 deals from a unified pool containing products from both sources.

The model only returns the deal number + a product summary; price and URL are taken
from the scraped pool by code, so the model can never alter them (29/10).
"""

import re
from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from price_agents.agent import Agent as BaseAgent
from price_agents.deals import Deal, DealSelection
from bestbuy_untils.unified_deal import UnifiedScrapedDeal

# Từ chỉ màu ở cuối tên sản phẩm: cùng một mẫu khác màu (vd WH-1000XM5 x5 màu ở BestBuy) chỉ giữ một
COLOR_WORDS = {
    "black", "white", "silver", "gray", "grey", "blue", "red", "green", "pink", "purple", "gold",
    "beige", "navy", "midnight", "graphite", "charcoal", "cream", "sand", "teal", "yellow", "orange",
    "smoky", "platinum", "rose", "sage", "slate", "titanium", "brown", "ivory",
}


class PickedDeal(BaseModel):
    deal_number: int = Field(description="The number of the chosen deal, e.g. 4 for 'Deal 4'")
    product_description: str = Field(
        description="A 3-4 sentence summary of the product itself (features, specs), not the terms of the deal"
    )


class PickedDeals(BaseModel):
    deals: List[PickedDeal] = Field(description="Exactly 3 different products")


def _title_key(title: str) -> str:
    """Tên chuẩn hoá để so trùng: chữ thường, bỏ dấu câu, bỏ các từ chỉ màu ở cuối."""
    words = re.sub(r"[^a-z0-9]+", " ", title.lower()).split()
    while words and words[-1] in COLOR_WORDS:
        words.pop()
    return " ".join(words)


def dedupe_deals(deals: List[UnifiedScrapedDeal]) -> List[UnifiedScrapedDeal]:
    """Gộp sản phẩm trùng trong cùng nguồn (cùng URL, hoặc cùng tên khi bỏ màu): giữ bản rẻ nhất,
    ở vị trí lần xuất hiện đầu (thứ tự trang tìm kiếm).
    BestBuy trả các màu của một mẫu với cùng URL nhưng giá khác (29/10: WH-1000XM5 x5 màu, $228-$298)."""
    unique: List[UnifiedScrapedDeal] = []
    index_by_key = {}
    for d in deals:
        keys = [(d.source, "url", d.url), (d.source, "title", _title_key(d.title))]
        i = next((index_by_key[k] for k in keys if k in index_by_key), None)
        if i is None:
            i = len(unique)
            unique.append(d)
        elif d.price < unique[i].price:
            unique[i] = d
        for k in keys:
            index_by_key[k] = i
    return unique


class MultiSourceScannerAgent(BaseAgent):
    """Selects best 3 deals from combined BestBuy + Amazon pool using gpt-6-luna."""

    name = "Multi-Source Scanner Agent"
    color = BaseAgent.CYAN
    MODEL = "gpt-6-luna"
    # Đo 29/10 trên 2 pool đã lưu x 3 lượt: none 4,2-4,3 s, low 4,6-5,3 s; cả hai 6/6 lượt đủ 3 deal khác nhau
    REASONING_EFFORT = "none"

    SYSTEM_PROMPT = """You identify and summarize the 3 most detailed deals from a combined list of products from BestBuy and Amazon.
Select deals that have the most detailed, high quality description and the most clear price.
You can select from EITHER source (BestBuy or Amazon) - pick the best overall deals.

**IMPORTANT:**
1. Focus on the product features and specifications, not sales terms.
2. The product_description should be a 3-4 sentence summary of the product itself.
3. Pick 3 DIFFERENT products: never pick the same model twice (e.g. another color, or the same model from the other store).
4. Answer with the deal_number exactly as shown in the list ("Deal N")."""

    USER_PROMPT_PREFIX = """Respond with the most promising 3 deals from this COMBINED list (BestBuy + Amazon).
Select those which have the most detailed, high quality product description and a clear price.
You can pick from EITHER source - just choose the 3 best overall deals.

You should rephrase the description to be a summary of the product itself, not the terms of the deal.

Deals:

"""

    USER_PROMPT_SUFFIX = "\n\nInclude exactly 3 deals, no more. Pick the best from EITHER source."

    def __init__(self):
        self.log(f"Multi-Source Scanner Agent is initializing ({self.MODEL})")
        self.openai = OpenAI()
        self.reasoning_effort = self.REASONING_EFFORT
        self.log("Multi-Source Scanner Agent is ready")

    def make_user_prompt(self, deals: List[UnifiedScrapedDeal]) -> str:
        # URL không đưa vào prompt: mô hình không cần chép lại nó nữa
        blocks = [f"Deal {i}:\n{deal.describe(include_url=False)}" for i, deal in enumerate(deals, start=1)]
        return self.USER_PROMPT_PREFIX + "\n\n".join(blocks) + self.USER_PROMPT_SUFFIX

    def scan(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """Select top 3 deals from combined BestBuy + Amazon pool."""
        if not unified_deals:
            self.log("No deals to scan")
            return None

        valid_deals = dedupe_deals([d for d in unified_deals if d.price > 0])
        if not valid_deals:
            self.log("No deals with valid price > 0")
            return None
        if len(valid_deals) < len(unified_deals):
            self.log(f"Kept {len(valid_deals)}/{len(unified_deals)} deals (dropped price 0 / duplicate titles)")

        user_prompt = self.make_user_prompt(valid_deals)
        self.log(f"Calling {self.MODEL} (reasoning {self.reasoning_effort}) with {len(valid_deals)} deals...")

        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=PickedDeals,
            reasoning_effort=self.reasoning_effort,
        )

        picks = result.choices[0].message.parsed.deals
        deals = []
        used = set()
        for pick in picks:
            n = pick.deal_number
            if not 1 <= n <= len(valid_deals) or n in used:
                self.log(f"Ignoring invalid / repeated deal number {n}")
                continue
            used.add(n)
            source_deal = valid_deals[n - 1]
            # Giá và URL lấy từ dữ liệu đã cào, không lấy từ mô hình
            deals.append(Deal(
                product_description=f"[{source_deal.source}] {pick.product_description.strip()}",
                price=source_deal.price,
                url=source_deal.url,
            ))

        self.log(f"Selected {len(deals)} deals from combined pool")
        return DealSelection(deals=deals[:3])
