"""
Multi-Source Framework - Orchestrator

Pattern follows: deal_agent_framework.py
Handles:
- ChromaDB initialization
- Lazy agent initialization
- High-level methods for Gradio UI

Author: Refactored from bestbuy4.py
Date: 2026-02-07
"""

import logging
from typing import List, Optional

import chromadb
from dotenv import load_dotenv

from price_agents.multi_source_planning_agent import MultiSourcePlanningAgent
from price_agents.deals import Opportunity
from bestbuy_untils.clarification_agent import (
    ClarificationQuestion,
    ClarificationResponse
)

# Colors for logging
BG_CYAN = '\033[46m'
WHITE = '\033[37m'
RESET = '\033[0m'


def init_logging():
    """Initialize logging configuration."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)


class MultiSourceFramework:
    """
    Framework orchestrator for Multi-Source deal finding.
    Pattern follows DealAgentFramework.
    """

    DB = "products_vectorstore"

    def __init__(self):
        """Initialize ChromaDB and load environment variables."""
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
        """Log message with framework identifier."""
        text = BG_CYAN + WHITE + "[Multi-Source Framework] " + message + RESET
        logging.info(text)

    def init_agents_as_needed(self):
        """Lazy initialization of planning agent."""
        if not self.planner:
            self.log("Initializing Multi-Source Planning Agent...")
            self.planner = MultiSourcePlanningAgent(self.collection)
            self.log("Planning Agent initialized successfully")

    # =========================================================================
    # CLARIFICATION METHODS
    # =========================================================================

    def generate_questions(self, keyword: str) -> ClarificationResponse:
        """Generate clarification questions for the keyword."""
        self.init_agents_as_needed()
        return self.planner.generate_questions(keyword)

    # =========================================================================
    # PIPELINE METHODS
    # =========================================================================

    def run(self, keyword: str, max_urls: int = 10) -> List[Opportunity]:
        """
        Run the full pipeline with original keyword (skip mode).

        Args:
            keyword: Original search keyword
            max_urls: Max URLs per source

        Returns:
            List of Opportunity sorted by discount
        """
        self.init_agents_as_needed()
        self.log(f"Running pipeline: '{keyword}' (max {max_urls} URLs/source)")
        opportunities = self.planner.plan(keyword, max_urls)
        self.current_opportunities = opportunities
        return opportunities

    def run_with_answers(
        self,
        keyword: str,
        questions: List[ClarificationQuestion],
        answers: List[str],
        max_urls: int = 10
    ) -> List[Opportunity]:
        """
        Run the pipeline with clarification answers.

        Args:
            keyword: Original search keyword
            questions: Clarification questions generated earlier
            answers: User's answers to the questions
            max_urls: Max URLs per source

        Returns:
            List of Opportunity sorted by discount
        """
        self.init_agents_as_needed()
        self.log(f"Running pipeline with clarification: '{keyword}'")
        opportunities = self.planner.plan_with_answers(keyword, questions, answers, max_urls)
        self.current_opportunities = opportunities
        return opportunities

    # =========================================================================
    # NOTIFICATION
    # =========================================================================

    def send_notification(self, index: int = 0) -> str:
        """
        Send push notification for the deal at specified index.

        Args:
            index: Index in current_opportunities (0 = best deal)

        Returns:
            Status message
        """
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
            url=opp.deal.url
        )

        return f"Sent! Deal #{index}: {opp.deal.product_description[:40]}... (${opp.deal.price:.2f})"


if __name__ == "__main__":
    # Quick test
    framework = MultiSourceFramework()
    print("Framework initialized successfully!")
