"""
Multi-Source Planning Agent - Pipeline Logic

Handles the pipeline:
1. Search + Filter + Scrape BestBuy and Amazon in PARALLEL (ThreadPoolExecutor)
2. Combine into unified pool
3. Select top deals (GPT-5-nano)
4. Estimate prices (EnsembleAgent)
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from price_agents.agent import Agent
from price_agents.deals import Deal, DealSelection, Opportunity
from price_agents.ensemble_agent import EnsembleAgent
from price_agents.messaging_agent import MessagingAgent

# BestBuy: curl_cffi + APIs
from price_agents.bestbuy_deals import (
    ScrapedBestBuyDeal,
    search_filter_scrape_bestbuy,
)

# Amazon: curl_cffi + HTML parsing
from price_agents.amazon_deals import (
    ScrapedAmazonDeal,
    search_filter_scrape_amazon,
)

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

    def _bestbuy_pipeline(self, keyword: str, max_results: int) -> List[ScrapedBestBuyDeal]:
        """BestBuy: search + filter sale + scrape in one call (curl_cffi + APIs)."""
        self.log(f"[BestBuy] Starting search+filter+scrape for '{keyword}'...")
        deals = search_filter_scrape_bestbuy(keyword, max_results=max_results)
        self.log(f"[BestBuy] Got {len(deals)} sale products")
        return deals

    def _amazon_pipeline(self, keyword: str, max_results: int) -> List[ScrapedAmazonDeal]:
        """Amazon: search + filter sale + scrape in one call (curl_cffi + HTML)."""
        self.log(f"[Amazon] Starting search+filter+scrape for '{keyword}'...")
        deals = search_filter_scrape_amazon(keyword, max_results=max_results)
        self.log(f"[Amazon] Got {len(deals)} sale products")
        return deals

    def search_and_scrape(
        self, keyword: str, max_results: int = 6, source: str = "All"
    ) -> tuple[List[ScrapedBestBuyDeal], List[ScrapedAmazonDeal]]:
        """Search and scrape based on source selection."""
        if source == "All":
            self.log(f"[Step 1/4] Search+Filter+Scrape '{keyword}' (BestBuy + Amazon parallel)...")
            with ThreadPoolExecutor(max_workers=2) as executor:
                bb_future = executor.submit(self._bestbuy_pipeline, keyword, max_results)
                az_future = executor.submit(self._amazon_pipeline, keyword, max_results)
                bb_deals = bb_future.result()
                az_deals = az_future.result()
        elif source == "BestBuy":
            self.log(f"[Step 1/4] Search+Filter+Scrape '{keyword}' (BestBuy only)...")
            bb_deals = self._bestbuy_pipeline(keyword, max_results)
            az_deals = []
        elif source == "Amazon":
            self.log(f"[Step 1/4] Search+Filter+Scrape '{keyword}' (Amazon only)...")
            bb_deals = []
            az_deals = self._amazon_pipeline(keyword, max_results)

        self.log(f"Total: {len(bb_deals)} BestBuy + {len(az_deals)} Amazon = {len(bb_deals) + len(az_deals)} products")
        return bb_deals, az_deals

    # =========================================================================
    # PIPELINE STEP 2: COMBINE
    # =========================================================================

    def combine(
        self,
        bb_deals: List[ScrapedBestBuyDeal],
        az_deals: List[ScrapedAmazonDeal],
    ) -> List[UnifiedScrapedDeal]:
        """Convert BestBuy + Amazon deals to unified pool."""
        self.log("[Step 2/4] Converting to unified format...")
        unified = []
        for deal in bb_deals:
            unified.append(UnifiedScrapedDeal.from_bestbuy(deal))
        for deal in az_deals:
            unified.append(UnifiedScrapedDeal.from_amazon(deal))
        self.log(f"Unified pool: {len(unified)} products (BestBuy: {len(bb_deals)}, Amazon: {len(az_deals)})")
        return unified

    # =========================================================================
    # PIPELINE STEP 3: SELECT TOP DEALS
    # =========================================================================

    def select_top_deals(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """Select top deals using GPT-5-nano."""
        self.log("[Step 3/4] GPT-5-nano selecting top deals from combined pool...")
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

    def plan(self, keyword: str, max_urls: int = 6, source: str = "All") -> List[Opportunity]:
        """Run the full pipeline.

        1. Search + Filter + Scrape (based on source selection)
        2. Combine into unified pool
        3. Select top deals (GPT-5-nano)
        4. Estimate prices (EnsembleAgent)
        """
        pipeline_start = time.time()
        self.log(f"Starting pipeline for: '{keyword}' (max {max_urls} per source, source: {source})")

        # Step 1: Search + Filter + Scrape
        t0 = time.time()
        bb_deals, az_deals = self.search_and_scrape(keyword, max_urls, source)
        self.log(f"[TIMER] Step 1 (Search+Filter+Scrape) completed in {time.time() - t0:.1f}s")
        if not bb_deals and not az_deals:
            self.log("No products found from either source. Try a different keyword.")
            return []

        # Step 2: Combine
        t0 = time.time()
        unified_deals = self.combine(bb_deals, az_deals)
        self.log(f"[TIMER] Step 2 (Combine) completed in {time.time() - t0:.1f}s")
        if not unified_deals:
            self.log("No products to combine.")
            return []

        # Step 3: Select top deals
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
