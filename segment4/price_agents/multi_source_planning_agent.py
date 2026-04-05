"""
Multi-Source Planning Agent - Pipeline Logic

Handles the pipeline:
1. Search + Filter + Scrape BestBuy (curl_cffi + APIs) and Amazon (Playwright) in parallel
2. Combine into unified pool
3. Select top 5 deals (Cerebras)
4. Estimate prices (EnsembleAgent)
"""

import asyncio
import logging
import time
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

from price_agents.agent import Agent
from price_agents.deals import Deal, DealSelection, Opportunity
from price_agents.ensemble_agent import EnsembleAgent
from price_agents.messaging_agent import MessagingAgent

# BestBuy: curl_cffi + APIs (replaces Brave MCP + Playwright)
from price_agents.bestbuy_deals import (
    ScrapedBestBuyDeal,
    search_filter_scrape_bestbuy,
)

# Amazon: still uses Brave MCP + Playwright
from price_agents.amazon_deals import (
    ScrapedAmazonDeal,
    filter_amazon_sale_urls_playwright,
    scrape_amazon_products,
)
from price_agents.amazon_scanner_agent import AmazonSearchAgent

from bestbuy_untils.unified_deal import UnifiedScrapedDeal
from bestbuy_untils.multi_source_scanner_agent import MultiSourceScannerAgent


class MultiSourcePlanningAgent(Agent):
    """Planning Agent for Multi-Source deal finding."""

    name = "Multi-Source Planning Agent"
    color = Agent.GREEN
    DEAL_THRESHOLD = 100

    def __init__(self, collection):
        self.log("Initializing Multi-Source Planning Agent")
        self.ensemble = EnsembleAgent(collection)
        self.messenger = MessagingAgent()
        self.multi_scanner = MultiSourceScannerAgent()
        self.log("Multi-Source Planning Agent is ready")

    # =========================================================================
    # PIPELINE STEP 1: SEARCH + FILTER + SCRAPE (parallel BestBuy + Amazon)
    # =========================================================================

    def _bestbuy_pipeline(self, keyword: str, max_urls: int) -> List[ScrapedBestBuyDeal]:
        """BestBuy: search + filter sale + scrape in one call (curl_cffi + APIs)."""
        self.log(f"[BestBuy] Starting search+filter+scrape for '{keyword}'...")
        deals = search_filter_scrape_bestbuy(keyword, max_results=max_urls)
        self.log(f"[BestBuy] Got {len(deals)} sale products")
        return deals

    def _amazon_pipeline(self, keyword: str, max_urls: int) -> List[ScrapedAmazonDeal]:
        """Amazon: search (Brave MCP) + filter + scrape (Playwright)."""
        self.log(f"[Amazon] Starting search for '{keyword}'...")
        search_agent = AmazonSearchAgent()
        urls = search_agent.search(keyword, max_urls=max_urls)
        self.log(f"[Amazon] Found {len(urls)} URLs")

        if not urls:
            return []

        loop = self._get_event_loop()

        # Filter sale items
        self.log(f"[Amazon] Filtering {len(urls)} URLs (Playwright)...")
        sale_items = loop.run_until_complete(
            filter_amazon_sale_urls_playwright(urls, headless=True)
        )
        self.log(f"[Amazon] {len(sale_items)} sale items")

        if not sale_items:
            return []

        # Scrape details
        self.log(f"[Amazon] Scraping {len(sale_items)} products...")
        scraped = loop.run_until_complete(
            scrape_amazon_products(sale_items, headless=True)
        )
        self.log(f"[Amazon] Scraped {len(scraped)} products")
        return scraped

    def _get_event_loop(self):
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def search_and_scrape(
        self, keyword: str, max_urls: int = 10
    ) -> Tuple[List[ScrapedBestBuyDeal], List[ScrapedAmazonDeal]]:
        """Run BestBuy and Amazon pipelines in parallel."""
        self.log(f"[Step 1/4] Search+Filter+Scrape '{keyword}' (BestBuy + Amazon parallel)...")

        bb_deals = []
        az_deals = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_bb = executor.submit(self._bestbuy_pipeline, keyword, max_urls)
            future_az = executor.submit(self._amazon_pipeline, keyword, max_urls)

            bb_deals = future_bb.result(timeout=600)
            az_deals = future_az.result(timeout=600)

        self.log(f"Total: {len(bb_deals)} BestBuy + {len(az_deals)} Amazon")
        return bb_deals, az_deals

    # =========================================================================
    # PIPELINE STEP 2: COMBINE
    # =========================================================================

    def combine(
        self,
        bb_deals: List[ScrapedBestBuyDeal],
        az_deals: List[ScrapedAmazonDeal],
    ) -> List[UnifiedScrapedDeal]:
        """Combine BestBuy + Amazon into unified pool."""
        self.log("[Step 2/4] Combining products from both sources...")
        unified = []
        for deal in bb_deals:
            unified.append(UnifiedScrapedDeal.from_bestbuy(deal))
        for deal in az_deals:
            unified.append(UnifiedScrapedDeal.from_amazon(deal))
        self.log(f"Combined pool: {len(unified)} products")
        return unified

    # =========================================================================
    # PIPELINE STEP 3: SELECT TOP DEALS
    # =========================================================================

    def select_top_deals(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """Select top 5 deals using Cerebras."""
        self.log("[Step 3/4] Cerebras selecting top 5 from combined pool...")
        selection = self.multi_scanner.scan(unified_deals)
        if selection and selection.deals:
            self.log(f"Selected {len(selection.deals)} best deals")
        return selection

    # =========================================================================
    # PIPELINE STEP 4: ESTIMATE PRICES
    # =========================================================================

    def estimate_prices(self, deal_selection: DealSelection) -> List[Opportunity]:
        """Estimate prices using EnsembleAgent."""
        self.log("[Step 4/4] Estimating prices with EnsembleAgent (3 models)...")

        opportunities = []
        for deal in deal_selection.deals:
            estimate = self.ensemble.price(deal.product_description)
            discount = estimate - deal.price
            opportunities.append(Opportunity(deal=deal, estimate=estimate, discount=discount))

        opportunities.sort(key=lambda x: x.discount, reverse=True)
        self.log(f"Estimated {len(opportunities)} opportunities")

        if opportunities:
            best = opportunities[0]
            self.log(f"BEST DEAL: ${best.deal.price:.2f} -> Est: ${best.estimate:.2f} = Discount ${best.discount:.2f}")

        return opportunities

    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================

    def plan(self, keyword: str, max_urls: int = 10) -> List[Opportunity]:
        """Run the full pipeline.

        1. Search + Filter + Scrape (BestBuy + Amazon parallel)
        2. Combine into unified pool
        3. Select top 5 deals (Cerebras)
        4. Estimate prices (EnsembleAgent)
        """
        pipeline_start = time.time()
        self.log(f"Starting pipeline for: '{keyword}' (max {max_urls} URLs/source)")

        # Step 1: Search + Filter + Scrape
        t0 = time.time()
        bb_deals, az_deals = self.search_and_scrape(keyword, max_urls)
        self.log(f"[TIMER] Step 1 (Search+Filter+Scrape) completed in {time.time() - t0:.1f}s")
        if not bb_deals and not az_deals:
            self.log("No products found. Try a different keyword.")
            return []

        # Step 2: Combine
        t0 = time.time()
        unified_deals = self.combine(bb_deals, az_deals)
        self.log(f"[TIMER] Step 2 (Combine) completed in {time.time() - t0:.1f}s")
        if not unified_deals:
            self.log("No products to combine.")
            return []

        # Step 3: Select top 5
        t0 = time.time()
        deal_selection = self.select_top_deals(unified_deals)
        self.log(f"[TIMER] Step 3 (Select) completed in {time.time() - t0:.1f}s")
        if not deal_selection or not deal_selection.deals:
            self.log("Could not select deals.")
            return []

        # Step 4: Estimate prices
        t0 = time.time()
        opportunities = self.estimate_prices(deal_selection)
        self.log(f"[TIMER] Step 4 (Estimate) completed in {time.time() - t0:.1f}s")

        # Auto-notify
        if opportunities and opportunities[0].discount > self.DEAL_THRESHOLD:
            best = opportunities[0]
            self.log(f"Auto-notifying: Discount ${best.discount:.2f} > threshold ${self.DEAL_THRESHOLD}")
            self.messenger.notify(
                description=best.deal.product_description[:200],
                deal_price=best.deal.price,
                estimated_true_value=best.estimate,
                url=best.deal.url,
            )

        total = time.time() - pipeline_start
        self.log(f"Pipeline completed! Total time: {total:.1f}s ({total/60:.1f} min)")
        return opportunities
