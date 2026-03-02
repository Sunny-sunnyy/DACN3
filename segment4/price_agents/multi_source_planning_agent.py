"""
Multi-Source Planning Agent - Pipeline Logic

Pattern follows: planning_agent.py
Handles the 6-step pipeline:
1. Search BestBuy + Amazon (parallel)
2. Filter sale items
3. Scrape product details
4. Combine into unified pool
5. Select top 5 deals
6. Estimate prices

Author: Refactored from bestbuy4.py
Date: 2026-02-07
"""

import asyncio
import logging
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

from price_agents.agent import Agent
from price_agents.deals import Deal, DealSelection, Opportunity
from price_agents.ensemble_agent import EnsembleAgent
from price_agents.messaging_agent import MessagingAgent

# BestBuy imports
from price_agents.bestbuy_deals import (
    ScrapedBestBuyDeal,
    filter_sale_urls,
    scrape_bestbuy_products
)
from price_agents.bestbuy_scanner_agent import BestBuySearchAgent

# Amazon imports
from price_agents.amazon_deals import (
    ScrapedAmazonDeal,
    filter_amazon_sale_urls_playwright,
    scrape_amazon_products
)
from price_agents.amazon_scanner_agent import AmazonSearchAgent

# Refactored modules
from bestbuy_untils.clarification_agent import (
    ClarificationAgent,
    ClarificationQuestion,
    ClarificationResponse,
    RefinedQuery
)
from bestbuy_untils.unified_deal import UnifiedScrapedDeal
from bestbuy_untils.multi_source_scanner_agent import MultiSourceScannerAgent


class MultiSourcePlanningAgent(Agent):
    """
    Planning Agent for Multi-Source deal finding.
    Coordinates search across BestBuy and Amazon, then estimates prices.
    """

    name = "Multi-Source Planning Agent"
    color = Agent.GREEN
    DEAL_THRESHOLD = 100  # Discount threshold for auto-notification

    def __init__(self, collection):
        """Initialize all sub-agents."""
        self.log("Initializing Multi-Source Planning Agent")
        self.ensemble = EnsembleAgent(collection)
        self.messenger = MessagingAgent()
        self.clarification = ClarificationAgent()
        self.multi_scanner = MultiSourceScannerAgent()
        self.log("Multi-Source Planning Agent is ready")

    # =========================================================================
    # CLARIFICATION METHODS
    # =========================================================================

    def generate_questions(self, keyword: str) -> ClarificationResponse:
        """Generate 3 clarification questions for the keyword."""
        self.log(f"Generating clarification questions for: {keyword}")
        return self.clarification.generate_questions(keyword)

    def build_refined_query(
        self,
        keyword: str,
        questions: List[ClarificationQuestion],
        answers: List[str]
    ) -> RefinedQuery:
        """Build refined search query from user answers."""
        self.log("Building refined query from answers")
        return self.clarification.build_refined_query(keyword, questions, answers)

    # =========================================================================
    # PIPELINE STEP 1: SEARCH
    # =========================================================================

    def _search_bestbuy(self, keyword: str, max_urls: int) -> List[str]:
        """Search BestBuy for product URLs."""
        search_agent = BestBuySearchAgent()
        return search_agent.search(keyword, max_urls=max_urls)

    def _search_amazon(self, keyword: str, max_urls: int) -> List[str]:
        """Search Amazon for product URLs."""
        search_agent = AmazonSearchAgent()
        return search_agent.search(keyword, max_urls=max_urls)

    def search_both_sources(
        self, keyword: str, max_urls: int = 10
    ) -> Tuple[List[str], List[str]]:
        """Search BestBuy + Amazon in parallel using ThreadPoolExecutor."""
        self.log(f"[Step 1/6] Searching '{keyword}' on BestBuy + Amazon...")

        bestbuy_urls = []
        amazon_urls = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_bb = executor.submit(self._search_bestbuy, keyword, max_urls)
            future_az = executor.submit(self._search_amazon, keyword, max_urls)

            bestbuy_urls = future_bb.result(timeout=120)
            self.log(f"  BestBuy: {len(bestbuy_urls)} URLs found")

            amazon_urls = future_az.result(timeout=120)
            self.log(f"  Amazon: {len(amazon_urls)} URLs found")

        self.log(f"Total: {len(bestbuy_urls)} (BestBuy) + {len(amazon_urls)} (Amazon)")
        return bestbuy_urls, amazon_urls

    # =========================================================================
    # PIPELINE STEP 2: FILTER SALES
    # =========================================================================

    def _get_event_loop(self):
        """Get or create event loop for async operations."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def filter_sales(
        self, bestbuy_urls: List[str], amazon_urls: List[str]
    ) -> Tuple[List[str], List[Tuple[str, dict]]]:
        """Filter URLs to keep only products on sale."""
        self.log("[Step 2/6] Filtering sale items...")

        # BestBuy: BeautifulSoup (fast)
        bestbuy_sales = []
        if bestbuy_urls:
            self.log(f"  Filtering {len(bestbuy_urls)} BestBuy URLs (BeautifulSoup)...")
            bestbuy_sales = filter_sale_urls(bestbuy_urls)
            self.log(f"  BestBuy: {len(bestbuy_sales)} sale items")

        # Amazon: Playwright (required)
        amazon_sales = []
        if amazon_urls:
            self.log(f"  Filtering {len(amazon_urls)} Amazon URLs (Playwright)...")
            loop = self._get_event_loop()
            amazon_sales = loop.run_until_complete(
                filter_amazon_sale_urls_playwright(amazon_urls, headless=False)
            )
            self.log(f"  Amazon: {len(amazon_sales)} sale items")

        return bestbuy_sales, amazon_sales

    # =========================================================================
    # PIPELINE STEP 3 & 4: SCRAPE AND COMBINE
    # =========================================================================

    def scrape_and_combine(
        self,
        bestbuy_urls: List[str],
        amazon_items: List[Tuple[str, dict]]
    ) -> List[UnifiedScrapedDeal]:
        """Scrape product details and combine into unified pool."""
        self.log("[Step 3/6] Scraping product details (Playwright)...")

        loop = self._get_event_loop()
        bestbuy_scraped = []
        amazon_scraped = []

        # Scrape BestBuy
        if bestbuy_urls:
            self.log(f"  Scraping {len(bestbuy_urls)} BestBuy products...")
            bestbuy_scraped = loop.run_until_complete(
                scrape_bestbuy_products(bestbuy_urls, headless=False)
            )
            self.log(f"  BestBuy: Scraped {len(bestbuy_scraped)} products")

        # Scrape Amazon
        if amazon_items:
            self.log(f"  Scraping {len(amazon_items)} Amazon products...")
            amazon_scraped = loop.run_until_complete(
                scrape_amazon_products(amazon_items, headless=False)
            )
            self.log(f"  Amazon: Scraped {len(amazon_scraped)} products")

        # Step 4: Combine into unified pool
        self.log("[Step 4/6] Combining products from both sources...")
        unified_deals = []
        for deal in bestbuy_scraped:
            unified_deals.append(UnifiedScrapedDeal.from_bestbuy(deal))
        for deal in amazon_scraped:
            unified_deals.append(UnifiedScrapedDeal.from_amazon(deal))

        self.log(f"Combined pool: {len(unified_deals)} products")
        return unified_deals

    # =========================================================================
    # PIPELINE STEP 5: SELECT TOP DEALS
    # =========================================================================

    def select_top_deals(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """Select top 5 deals from combined pool using GPT."""
        self.log("[Step 5/6] GPT selecting top 5 from combined pool...")
        selection = self.multi_scanner.scan(unified_deals)

        if selection and selection.deals:
            self.log(f"Selected {len(selection.deals)} best deals")
        return selection

    # =========================================================================
    # PIPELINE STEP 6: ESTIMATE PRICES
    # =========================================================================

    def estimate_prices(self, deal_selection: DealSelection) -> List[Opportunity]:
        """Estimate prices using EnsembleAgent and calculate discounts."""
        self.log("[Step 6/6] Estimating prices with EnsembleAgent (3 models)...")

        opportunities = []
        for deal in deal_selection.deals:
            estimate = self.ensemble.price(deal.product_description)
            discount = estimate - deal.price
            opportunity = Opportunity(deal=deal, estimate=estimate, discount=discount)
            opportunities.append(opportunity)

        # Sort by discount (best first)
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
        """
        Run the full 6-step pipeline:
        1. Search BestBuy + Amazon (parallel)
        2. Filter sale items
        3. Scrape product details
        4. Combine into unified pool
        5. Select top 5 deals
        6. Estimate prices

        Args:
            keyword: Search keyword (original or refined)
            max_urls: Max URLs per source

        Returns:
            List of Opportunity sorted by discount (best first)
        """
        self.log(f"Starting pipeline for: '{keyword}' (max {max_urls} URLs/source)")

        # Step 1: Search
        bb_urls, az_urls = self.search_both_sources(keyword, max_urls)
        if not bb_urls and not az_urls:
            self.log("No products found. Try a different keyword.")
            return []

        # Step 2: Filter
        bb_sales, az_sales = self.filter_sales(bb_urls, az_urls)
        if not bb_sales and not az_sales:
            self.log("No sale items found. Try a different keyword.")
            return []

        # Step 3 & 4: Scrape and Combine
        unified_deals = self.scrape_and_combine(bb_sales, az_sales)
        if not unified_deals:
            self.log("Could not scrape product details.")
            return []

        # Step 5: Select top 5
        deal_selection = self.select_top_deals(unified_deals)
        if not deal_selection or not deal_selection.deals:
            self.log("Could not select deals.")
            return []

        # Step 6: Estimate prices
        opportunities = self.estimate_prices(deal_selection)

        # Auto-notify if best deal exceeds threshold
        if opportunities and opportunities[0].discount > self.DEAL_THRESHOLD:
            best = opportunities[0]
            self.log(f"Auto-notifying: Discount ${best.discount:.2f} > threshold ${self.DEAL_THRESHOLD}")
            self.messenger.notify(
                description=best.deal.product_description[:200],
                deal_price=best.deal.price,
                estimated_true_value=best.estimate,
                url=best.deal.url
            )

        self.log("Pipeline completed successfully!")
        return opportunities

    def plan_with_answers(
        self,
        keyword: str,
        questions: List[ClarificationQuestion],
        answers: List[str],
        max_urls: int = 10
    ) -> List[Opportunity]:
        """
        Run pipeline with clarification answers.
        Builds refined query first, then runs full pipeline.
        """
        refined = self.build_refined_query(keyword, questions, answers)
        self.log(f"Refined query: '{keyword}' -> '{refined.query}'")
        return self.plan(refined.query, max_urls)
