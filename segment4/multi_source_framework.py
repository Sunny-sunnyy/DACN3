"""
Multi-Source Framework - Orchestrator

Handles:
- ChromaDB initialization
- Lazy agent initialization
- High-level methods for Gradio UI
"""

import logging
import time
from typing import List, Optional

import chromadb
from dotenv import load_dotenv

from price_agents.multi_source_planning_agent import MultiSourcePlanningAgent
from price_agents.deals import Opportunity

BG_CYAN = '\033[46m'
WHITE = '\033[37m'
RESET = '\033[0m'


def init_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)


class MultiSourceFramework:
    """Framework orchestrator for Multi-Source deal finding."""

    DB = "products_vectorstore"

    def __init__(self):
        load_dotenv(override=True)
        init_logging()

        self.log("Initializing Multi-Source Framework")
        client = chromadb.PersistentClient(path=self.DB)
        self.collection = client.get_or_create_collection('products')
        self.log(f"ChromaDB collection: {self.collection.name}, count: {self.collection.count()}")

        self.planner: Optional[MultiSourcePlanningAgent] = None
        self.current_opportunities: List[Opportunity] = []
        self.log("Multi-Source Framework is ready")

    def log(self, message: str):
        text = BG_CYAN + WHITE + "[Multi-Source Framework] " + message + RESET
        logging.info(text)

    def init_agents_as_needed(self):
        if not self.planner:
            self.log("Initializing Multi-Source Planning Agent...")
            t0 = time.time()
            self.planner = MultiSourcePlanningAgent(self.collection)
            self.log(f"[TIMER] All agents initialized in {time.time() - t0:.1f}s")

    def run(self, keyword: str, max_urls: int = 10) -> List[Opportunity]:
        """Run the full pipeline with keyword."""
        self.init_agents_as_needed()
        self.log(f"Running pipeline: '{keyword}' (max {max_urls} URLs/source)")
        opportunities = self.planner.plan(keyword, max_urls)
        self.current_opportunities = opportunities
        return opportunities

    def send_notification(self, index: int = 0) -> str:
        """Send push notification for the deal at specified index."""
        if not self.current_opportunities:
            return "No deals available. Search first!"

        if index < 0 or index >= len(self.current_opportunities):
            return f"Invalid index. Choose 0-{len(self.current_opportunities) - 1}"

        opp = self.current_opportunities[index]
        self.init_agents_as_needed()

        self.planner.messenger.notify(
            description=opp.deal.product_description[:200],
            deal_price=opp.deal.price,
            estimated_true_value=opp.estimate,
            url=opp.deal.url,
        )

        return f"Sent! Deal #{index}: {opp.deal.product_description[:40]}... (${opp.deal.price:.2f})"


if __name__ == "__main__":
    framework = MultiSourceFramework()
    print("Framework initialized successfully!")
