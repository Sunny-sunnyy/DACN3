"""
Multi-Source Deal Finder v4 - Gradio Web App (bestbuy4.py)

Search on BOTH BestBuy AND Amazon simultaneously.
Refactored version with modular imports.

Supports 2 flows:
1. Clarification Flow: User answers 3 questions -> Refined query -> Better deals
2. Skip Flow: User skips questions -> Search with original keyword

Workflow:
1. [ClarificationAgent] Generate clarification questions (GPT-5-mini)
2. [ClarificationAgent] Build refined query from answers OR skip
3. [PARALLEL] Search URLs on BestBuy + Amazon (Brave MCP)
4. [Filter] BestBuy: BeautifulSoup | Amazon: Playwright
5. [Scrape] Both: Playwright
6. [GPT] Select top 5 deals from COMBINED pool
7. [EnsembleAgent] Estimate prices (3 models)
"""

import os
import sys
import logging
import queue
import threading
import time
import asyncio
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import gradio as gr
import chromadb
from dotenv import load_dotenv

# Import BestBuy modules
from price_agents.bestbuy_deals import (
    ScrapedBestBuyDeal,
    filter_sale_urls,
    scrape_bestbuy_products
)
from price_agents.bestbuy_scanner_agent import BestBuySearchAgent

# Import Amazon modules
from price_agents.amazon_deals import (
    ScrapedAmazonDeal,
    filter_amazon_sale_urls_playwright,
    scrape_amazon_products
)
from price_agents.amazon_scanner_agent import AmazonSearchAgent

# Import refactored modules
from bestbuy_untils.clarification_agent import (
    ClarificationAgent,
    ClarificationQuestion,
    ClarificationResponse,
    RefinedQuery
)
from bestbuy_untils.unified_deal import UnifiedScrapedDeal
from bestbuy_untils.multi_source_scanner_agent import MultiSourceScannerAgent
from bestbuy_untils.gradio_helpers import (
    QueueHandler,
    setup_logging,
    html_for_logs,
    opportunities_to_table,
    format_questions_html
)

# Import existing agents
from price_agents.ensemble_agent import EnsembleAgent
from price_agents.messaging_agent import MessagingAgent
from price_agents.deals import Deal, DealSelection, Opportunity


# ============================================================================
# SETUP & CONFIGURATION
# ============================================================================

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
root = logging.getLogger()
root.setLevel(logging.INFO)

DB_PATH = "products_vectorstore"


# ============================================================================
# GLOBAL VARIABLES
# ============================================================================

ensemble: Optional[EnsembleAgent] = None
messenger: Optional[MessagingAgent] = None
clarification_agent: Optional[ClarificationAgent] = None
multi_scanner: Optional[MultiSourceScannerAgent] = None
current_opportunities: List[Opportunity] = []

# Clarification state
current_questions: Optional[ClarificationResponse] = None
current_keyword: str = ""
current_max_urls: int = 10


# ============================================================================
# AGENT INITIALIZATION
# ============================================================================

def init_agents() -> None:
    """
    Initialize ChromaDB, EnsembleAgent, MessagingAgent, ClarificationAgent, and MultiSourceScanner.
    This is called once at startup.
    """
    global ensemble, messenger, clarification_agent, multi_scanner
    
    if ensemble is None:
        print("Initializing ChromaDB...")
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_or_create_collection('products')
        print(f"ChromaDB collection: {collection.name}")
        print(f"Number of documents: {collection.count()}")
        
        print("\nInitializing EnsembleAgent...")
        ensemble = EnsembleAgent(collection)
        print("EnsembleAgent ready!")
        
        print("\nInitializing MessagingAgent...")
        messenger = MessagingAgent()
        print("MessagingAgent ready!")
        
        print("\nInitializing ClarificationAgent...")
        clarification_agent = ClarificationAgent()
        print("ClarificationAgent ready!")
        
        print("\nInitializing MultiSourceScannerAgent...")
        multi_scanner = MultiSourceScannerAgent()
        print("MultiSourceScannerAgent ready!")
        
        print("\nAll agents initialized successfully!\n")


# ============================================================================
# PIPELINE FUNCTIONS
# ============================================================================

def search_bestbuy(keyword: str, max_urls: int = 10) -> List[str]:
    """Search for BestBuy product URLs using Brave Search."""
    try:
        search_agent = BestBuySearchAgent()
        return search_agent.search(keyword, max_urls=max_urls)
    except Exception as e:
        logging.error(f"BestBuy search error: {e}")
        return []


def search_amazon(keyword: str, max_urls: int = 10) -> List[str]:
    """Search for Amazon product URLs using Brave Search."""
    try:
        search_agent = AmazonSearchAgent()
        return search_agent.search(keyword, max_urls=max_urls)
    except Exception as e:
        logging.error(f"Amazon search error: {e}")
        return []


def filter_bestbuy_sales(urls: List[str]) -> List[str]:
    """Filter BestBuy URLs to keep only products on sale."""
    return filter_sale_urls(urls)


async def filter_amazon_sales(urls: List[str]) -> List[Tuple[str, dict]]:
    """Filter Amazon URLs to keep only products on sale (requires Playwright)."""
    return await filter_amazon_sale_urls_playwright(urls, headless=False)


async def scrape_bestbuy(urls: List[str]) -> List[ScrapedBestBuyDeal]:
    """Scrape BestBuy product details using Playwright."""
    return await scrape_bestbuy_products(urls, headless=False)


async def scrape_amazon(sale_items: List[Tuple[str, dict]]) -> List[ScrapedAmazonDeal]:
    """Scrape Amazon product details using Playwright."""
    return await scrape_amazon_products(sale_items, headless=False)


def estimate_prices(deal_selection: DealSelection, ensemble_agent: EnsembleAgent) -> List[Opportunity]:
    """Estimate prices and calculate discounts."""
    opportunities = []
    
    for deal in deal_selection.deals:
        estimate = ensemble_agent.price(deal.product_description)
        discount = estimate - deal.price
        opportunity = Opportunity(
            deal=deal,
            estimate=estimate,
            discount=discount
        )
        opportunities.append(opportunity)
    
    opportunities.sort(key=lambda x: x.discount, reverse=True)
    return opportunities


# ============================================================================
# CLARIFICATION FLOW HANDLERS
# ============================================================================

def generate_questions_handler(keyword: str):
    """Handle keyword input and generate clarification questions."""
    global current_questions, current_keyword
    
    if not keyword or len(keyword.strip()) < 2:
        return (
            "",
            "Please enter a keyword (at least 2 characters)",
            gr.update(visible=False),
            gr.update(visible=False),
        )
    
    try:
        current_keyword = keyword.strip()
        logging.info(f"Generating questions for: {current_keyword}")
        
        response = clarification_agent.generate_questions(current_keyword)
        current_questions = response
        
        questions_html = format_questions_html(response.questions)
        
        return (
            questions_html,
            f"Category: {response.product_category} | Answer the questions below or skip to search directly.",
            gr.update(visible=True),
            gr.update(visible=True),
        )
        
    except Exception as e:
        logging.error(f"Error generating questions: {e}")
        return (
            "",
            f"Error: {str(e)}",
            gr.update(visible=False),
            gr.update(visible=False),
        )


def submit_answers_handler(answer1: str, answer2: str, answer3: str, max_urls: int, initial_log_data: List[str]):
    """Handle submit answers and run clarification flow."""
    global current_questions, current_keyword, current_max_urls
    
    if not current_questions:
        yield [], "Please generate questions first!", "", html_for_logs(["Please generate questions first!"])
        return
    
    current_max_urls = int(max_urls) if max_urls else 10
    answers = [answer1.strip(), answer2.strip(), answer3.strip()]
    
    try:
        refined = clarification_agent.build_refined_query(
            current_keyword,
            current_questions.questions,
            answers
        )
        search_query = refined.query
        comparison_text = f"🔄 Original: \"{current_keyword}\" → Refined: \"{search_query}\""
    except Exception as e:
        logging.error(f"Error building refined query: {e}")
        search_query = current_keyword
        comparison_text = f"Using original keyword: \"{current_keyword}\""
    
    yield from run_search_pipeline(search_query, comparison_text, initial_log_data)


def skip_and_search_handler(max_urls: int, initial_log_data: List[str]):
    """Handle skip button - search with original keyword."""
    global current_keyword, current_max_urls
    
    if not current_keyword:
        yield [], "Please enter a keyword first!", "", html_for_logs(["Please enter a keyword first!"])
        return
    
    current_max_urls = int(max_urls) if max_urls else 10
    comparison_text = f"⏩ Skip mode - searching with: \"{current_keyword}\""
    
    yield from run_search_pipeline(current_keyword, comparison_text, initial_log_data)


# ============================================================================
# MAIN SEARCH PIPELINE (MULTI-SOURCE)
# ============================================================================

def do_search_pipeline(search_query: str, max_urls: int, result_queue: queue.Queue) -> None:
    """
    Worker function that runs in a separate thread.
    Executes the full MULTI-SOURCE search pipeline and puts result in queue.
    """
    global current_opportunities
    
    try:
        # STEP 1: SEARCH BOTH SOURCES
        logging.info(f"🔍 [Step 1/6] Searching '{search_query}' on BestBuy + Amazon...")
        
        bestbuy_urls = []
        amazon_urls = []
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_bb = executor.submit(search_bestbuy, search_query, max_urls)
            future_az = executor.submit(search_amazon, search_query, max_urls)
            
            try:
                bestbuy_urls = future_bb.result(timeout=120)
                logging.info(f"  📦 BestBuy: {len(bestbuy_urls)} URLs")
            except Exception as e:
                logging.warning(f"  ⚠️ BestBuy search failed: {e}")
            
            try:
                amazon_urls = future_az.result(timeout=120)
                logging.info(f"  📦 Amazon: {len(amazon_urls)} URLs")
            except Exception as e:
                logging.warning(f"  ⚠️ Amazon search failed: {e}")
        
        if not bestbuy_urls and not amazon_urls:
            result_queue.put(([], "No products found. Try a different keyword."))
            return
        
        logging.info(f"✅ Total URLs: {len(bestbuy_urls)} (BestBuy) + {len(amazon_urls)} (Amazon)")
        
        # STEP 2: FILTER SALES
        logging.info(f"🏷️ [Step 2/6] Filtering sale items...")
        
        bestbuy_sale_urls = []
        if bestbuy_urls:
            logging.info(f"  🔎 Filtering {len(bestbuy_urls)} BestBuy URLs (BeautifulSoup)...")
            bestbuy_sale_urls = filter_bestbuy_sales(bestbuy_urls)
            logging.info(f"  ✅ BestBuy: {len(bestbuy_sale_urls)} sale items")
        
        amazon_sale_items = []
        if amazon_urls:
            logging.info(f"  🔎 Filtering {len(amazon_urls)} Amazon URLs (Playwright)...")
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            amazon_sale_items = loop.run_until_complete(filter_amazon_sales(amazon_urls))
            logging.info(f"  ✅ Amazon: {len(amazon_sale_items)} sale items")
        
        if not bestbuy_sale_urls and not amazon_sale_items:
            result_queue.put(([], "No sale items found. Try a different keyword."))
            return
        
        # STEP 3: SCRAPE PRODUCTS
        logging.info(f"📦 [Step 3/6] Scraping product details (Playwright)...")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        bestbuy_scraped = []
        amazon_scraped = []
        
        if bestbuy_sale_urls:
            logging.info(f"  🛒 Scraping {len(bestbuy_sale_urls)} BestBuy products...")
            bestbuy_scraped = loop.run_until_complete(scrape_bestbuy(bestbuy_sale_urls))
            logging.info(f"  ✅ BestBuy: Scraped {len(bestbuy_scraped)} products")
        
        if amazon_sale_items:
            logging.info(f"  🛒 Scraping {len(amazon_sale_items)} Amazon products...")
            amazon_scraped = loop.run_until_complete(scrape_amazon(amazon_sale_items))
            logging.info(f"  ✅ Amazon: Scraped {len(amazon_scraped)} products")
        
        if not bestbuy_scraped and not amazon_scraped:
            result_queue.put(([], "Could not scrape product details."))
            return
        
        # STEP 4: COMBINE INTO UNIFIED POOL
        logging.info(f"🔀 [Step 4/6] Combining products from both sources...")
        
        unified_deals = []
        for deal in bestbuy_scraped:
            unified_deals.append(UnifiedScrapedDeal.from_bestbuy(deal))
        for deal in amazon_scraped:
            unified_deals.append(UnifiedScrapedDeal.from_amazon(deal))
        
        logging.info(f"✅ Combined pool: {len(unified_deals)} products")
        
        # STEP 5: SELECT TOP 5
        logging.info(f"🤖 [Step 5/6] GPT selecting top 5 from combined pool...")
        
        deal_selection = multi_scanner.scan(unified_deals)
        
        if not deal_selection or not deal_selection.deals:
            result_queue.put(([], "Could not select deals."))
            return
        
        logging.info(f"✅ Selected {len(deal_selection.deals)} best deals")
        
        # STEP 6: ESTIMATE PRICES
        logging.info(f"💰 [Step 6/6] Estimating prices with EnsembleAgent (3 models)...")
        
        opportunities = estimate_prices(deal_selection, ensemble)
        current_opportunities = opportunities
        
        logging.info(f"✅ Estimated {len(opportunities)} opportunities")
        
        if opportunities:
            best = opportunities[0]
            logging.info(f"🏆 BEST DEAL: ${best.deal.price:.2f} → Est: ${best.estimate:.2f} = Discount ${best.discount:.2f}")
        
        table = opportunities_to_table(opportunities)
        status = f"✅ Found {len(opportunities)} deals! Best discount: ${opportunities[0].discount:.2f}" if opportunities else "No deals found."
        
        result_queue.put((table, status))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        result_queue.put(([], f"Error: {str(e)}"))


def run_search_pipeline(search_query: str, comparison_text: str, initial_log_data: List[str]):
    """Generator function for Gradio that yields updates during pipeline execution."""
    global current_max_urls
    max_urls = current_max_urls if current_max_urls else 10
    
    log_q = queue.Queue()
    result_q = queue.Queue()
    setup_logging(log_q)
    
    log_data = initial_log_data.copy() if initial_log_data else []
    log_data.append(f"🚀 Starting MULTI-SOURCE search: {search_query} (max {max_urls} URLs per source)")
    log_data.append("📦 Sources: BestBuy + Amazon")
    
    thread = threading.Thread(
        target=do_search_pipeline,
        args=(search_query, max_urls, result_q)
    )
    thread.start()
    
    final_result = None
    while thread.is_alive() or not log_q.empty() or final_result is None:
        try:
            while True:
                message = log_q.get_nowait()
                log_data.append(message)
        except queue.Empty:
            pass
        
        try:
            final_result = result_q.get_nowait()
        except queue.Empty:
            pass
        
        if final_result:
            table, status = final_result
            yield table, status, comparison_text, html_for_logs(log_data)
        else:
            yield [], "⏳ Processing...", comparison_text, html_for_logs(log_data)
        
        time.sleep(0.1)
    
    if final_result:
        table, status = final_result
        log_data.append(f"✅ Pipeline completed!")
        yield table, status, comparison_text, html_for_logs(log_data)


# ============================================================================
# PUSH NOTIFICATION
# ============================================================================

def send_push_notification(selected_index: int) -> str:
    """Send push notification for selected deal."""
    global current_opportunities
    
    if not current_opportunities:
        return "No deals available. Search first!"
    
    idx = int(selected_index)
    if idx < 0 or idx >= len(current_opportunities):
        return f"Invalid selection. Choose 0-{len(current_opportunities)-1}"
    
    opp = current_opportunities[idx]
    
    try:
        messenger.notify(
            description=opp.deal.product_description[:200],
            deal_price=opp.deal.price,
            estimated_true_value=opp.estimate,
            url=opp.deal.url
        )
        return f"✅ Sent! Deal #{idx}: {opp.deal.product_description[:40]}... (${opp.deal.price:.2f})"
    except Exception as e:
        return f"Failed: {str(e)}"


# ============================================================================
# GRADIO UI DEFINITION
# ============================================================================

def create_gradio_app():
    """Create and return Gradio app with multi-source search and clarification flow."""
    
    with gr.Blocks(
        title="Multi-Source Deal Finder v4",
        theme=gr.themes.Soft(),
        fill_width=True,
    ) as app:
        
        log_data_state = gr.State([])
        
        # Header
        gr.Markdown("""
        # 🛒 Multi-Source Deal Finder v4
        
        Search on **BOTH** BestBuy AND Amazon simultaneously!
        
        **Flow:** 1️⃣ Enter Keyword → 2️⃣ Answer Questions (or Skip) → 3️⃣ Search BestBuy + Amazon → 4️⃣ Estimate Prices
        
        ⚠️ **Note:** Browser windows will open for Playwright scraping.
        """)
        
        # Step 1: Keyword Input
        with gr.Group():
            gr.Markdown("### 📝 Step 1: Enter Product Keyword")
            with gr.Row():
                keyword_input = gr.Textbox(
                    label="🔎 What are you looking for?",
                    placeholder="Enter product keyword (e.g., laptop, Smart TV, headphones)",
                    scale=3
                )
                max_urls_input = gr.Number(
                    label="Max URLs (per source)",
                    value=10,
                    minimum=5,
                    maximum=20,
                    precision=0,
                    scale=1
                )
                generate_btn = gr.Button("🤖 Generate Questions", variant="primary", scale=1)
        
        status_text = gr.Textbox(
            label="Status",
            interactive=False,
            value="Enter a keyword and click 'Generate Questions'"
        )
        
        # Step 2: Clarification Questions
        with gr.Group():
            questions_html = gr.HTML(
                value='<div style="padding: 20px; text-align: center; color: #888;">Questions will appear here after you enter a keyword...</div>'
            )
        
        # Step 3: Answers Input
        with gr.Group(visible=False) as answers_section:
            gr.Markdown("### ✍️ Step 2: Answer the Questions")
            gr.Markdown("*Type your answers freely (e.g., 'Acer', 'for students', 'under $800') or use options above*")
            
            with gr.Row():
                answer1 = gr.Textbox(label="Answer 1", placeholder="Your answer to Q1...")
                answer2 = gr.Textbox(label="Answer 2", placeholder="Your answer to Q2...")
                answer3 = gr.Textbox(label="Answer 3", placeholder="Your answer to Q3...")
            
            with gr.Row():
                submit_btn = gr.Button("✅ Submit & Search (BestBuy + Amazon)", variant="primary", scale=2)
                skip_btn = gr.Button("⏩ Skip, Search Now", variant="secondary", scale=1)
        
        # Query Comparison
        query_comparison = gr.Textbox(
            label="🔄 Query Comparison",
            interactive=False,
            visible=True,
            placeholder="Original vs Refined query will appear here..."
        )
        
        # Results
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("### 🏆 Deal Results (BestBuy + Amazon combined)")
                results_table = gr.Dataframe(
                    headers=["Product", "Sale $", "Estimate $", "Discount $", "Discount %", "URL"],
                    label="Sorted by discount (best first)",
                    wrap=True,
                    column_widths=[4, 1, 1, 1, 1, 2],
                    max_height=350,
                )
            
            with gr.Column(scale=2):
                gr.Markdown("### 📋 Pipeline Logs")
                logs_html = gr.HTML(
                    value='<div style="height: 400px; background-color: #1a1a2e; border-radius: 8px; padding: 10px; font-family: monospace; color: #87CEEB;">Ready to search...</div>'
                )
        
        # Push Notification
        with gr.Row():
            deal_index = gr.Number(
                label="Deal # to notify (0 = best deal)",
                value=0,
                minimum=0,
                precision=0,
                scale=1
            )
            push_btn = gr.Button("📱 Send Push Notification", variant="secondary", scale=1)
        
        push_status = gr.Textbox(
            label="📱 Notification Status",
            interactive=False,
            placeholder="Click 'Send Push Notification' to send...",
            lines=2,
        )
        
        # Event Handlers
        generate_btn.click(
            fn=generate_questions_handler,
            inputs=[keyword_input],
            outputs=[questions_html, status_text, answers_section, answers_section],
        )
        
        submit_btn.click(
            fn=submit_answers_handler,
            inputs=[answer1, answer2, answer3, max_urls_input, log_data_state],
            outputs=[results_table, status_text, query_comparison, logs_html],
        )
        
        skip_btn.click(
            fn=skip_and_search_handler,
            inputs=[max_urls_input, log_data_state],
            outputs=[results_table, status_text, query_comparison, logs_html],
        )
        
        push_btn.click(
            fn=send_push_notification,
            inputs=[deal_index],
            outputs=[push_status],
        )
        
        # Footer
        gr.Markdown("""
        ---
        **Legend:** 🔥 Discount > $200 | ✅ Discount > $100 | 👍 Positive discount | ❌ Overpriced
        
        **Sources:** 
        - 🟦 BestBuy: Filter uses BeautifulSoup, scrape uses Playwright
        - 🟠 Amazon: Both filter and scrape use Playwright
        
        **Notes:** Browser windows will open during Amazon operations
        """)
    
    return app


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Multi-Source Deal Finder v4 - Starting up...")
    print("   Sources: BestBuy + Amazon")
    print("   Refactored modular version")
    print("=" * 60)
    
    init_agents()
    
    app = create_gradio_app()
    
    print("\n" + "=" * 60)
    print("✅ Ready! Opening browser...")
    print("=" * 60 + "\n")
    
    app.launch(share=False, inbrowser=True)
