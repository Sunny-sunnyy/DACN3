"""
Multi-Source Scanner Agent - Selects best deals from combined BestBuy + Amazon pool.

Uses Cerebras (via LiteLLM + OpenRouter) with structured outputs to select
the top 5 deals from a unified pool containing products from both sources.
"""

import asyncio
import logging
from typing import List, Optional

import litellm

from price_agents.agent import Agent as BaseAgent
from price_agents.deals import DealSelection
from bestbuy_untils.unified_deal import UnifiedScrapedDeal


class MultiSourceScannerAgent(BaseAgent):
    """Selects best 5 deals from combined BestBuy + Amazon pool using Cerebras."""

    name = "Multi-Source Scanner Agent"
    color = BaseAgent.CYAN
    MODEL = "openrouter/openai/gpt-oss-120b"

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
5. Keep the original URL exactly as provided."""

    USER_PROMPT_PREFIX = """Respond with the most promising 5 deals from this COMBINED list (BestBuy + Amazon).
Select those which have the most detailed, high quality product description and a clear price that is greater than 0.
You can pick from EITHER source - just choose the 5 best overall deals.

You should rephrase the description to be a summary of the product itself, not the terms of the deal.
START the product_description with "[BestBuy]" or "[Amazon]" to indicate the source.

Deals:

"""

    USER_PROMPT_SUFFIX = "\n\nInclude up to 5 deals, no more. Pick the best from EITHER source."

    def __init__(self):
        self.log("Multi-Source Scanner Agent is initializing (Cerebras)")
        self.log("Multi-Source Scanner Agent is ready")

    def make_user_prompt(self, unified_deals: List[UnifiedScrapedDeal]) -> str:
        user_prompt = self.USER_PROMPT_PREFIX
        user_prompt += "\n\n".join([deal.describe() for deal in unified_deals])
        user_prompt += self.USER_PROMPT_SUFFIX
        return user_prompt

    def _run_async(self, coro):
        """Run async coroutine from sync context."""
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

    async def _scan_async(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """Call Cerebras via LiteLLM to select top 5 deals."""
        valid_deals = [d for d in unified_deals if d.price > 0]
        if not valid_deals:
            self.log("No deals with valid price > 0")
            return None

        user_prompt = self.make_user_prompt(valid_deals)
        self.log(f"Calling Cerebras with {len(valid_deals)} deals...")

        response = await litellm.acompletion(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            extra_body={
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "deal_selection",
                        "strict": True,
                        "schema": DealSelection.model_json_schema(),
                    },
                },
                "provider": {
                    "order": ["Cerebras"],
                    "allow_fallbacks": True,
                },
            },
        )

        selection = DealSelection.model_validate_json(response.choices[0].message.content)
        selection.deals = [d for d in selection.deals if d.price > 0]
        self.log(f"Selected {len(selection.deals)} deals from combined pool")
        return selection

    def scan(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """Select top 5 deals from combined BestBuy + Amazon pool."""
        if not unified_deals:
            self.log("No deals to scan")
            return None
        return self._run_async(self._scan_async(unified_deals))
