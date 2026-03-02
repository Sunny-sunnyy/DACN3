"""
Amazon Deal Finder - Gradio Web App

Allows users to search for specific products on Amazon by keyword.
Uses AI to estimate true value and find the best deals.

NOTE: Amazon blocks requests library, so we use Playwright for all operations.

Workflow:
1. Search URLs (Brave MCP)
2. Filter sale items (Playwright + US Zip Code)
3. Scrape details (Playwright + Multi-selector)
4. Select top 5 deals (GPT-5-mini)
5. Estimate prices (EnsembleAgent: 3 models)
"""

import os
import sys
import logging
import queue
import threading
import time
import asyncio
from typing import List, Tuple

import gradio as gr
import chromadb
from dotenv import load_dotenv

# Import Amazon modules
from price_agents.amazon_deals import (
    ScrapedAmazonDeal,
    filter_amazon_sale_urls_playwright,
    scrape_amazon_products
)
from price_agents.amazon_scanner_agent import (
    AmazonSearchAgent,
    AmazonScannerAgent
)

# Import existing agents
from price_agents.ensemble_agent import EnsembleAgent
from price_agents.messaging_agent import MessagingAgent
from price_agents.deals import Deal, DealSelection, Opportunity
from log_utils import reformat


# ============================================================================
# SECTION 1: SETUP & CONFIGURATION
# ============================================================================

# Load environment variables
load_dotenv(override=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
root = logging.getLogger()
root.setLevel(logging.INFO)

# Database path
DB_PATH = "products_vectorstore"


# ============================================================================
# SECTION 2: GLOBAL VARIABLES
# ============================================================================

ensemble = None
messenger = None
current_opportunities = []
log_queue = None


# ============================================================================
# SECTION 3: AGENT INITIALIZATION
# ============================================================================

def init_agents():
    """
    Initialize ChromaDB, EnsembleAgent, and MessagingAgent.
    This is called once at startup.
    """
    global ensemble, messenger
    
    if ensemble is None:
        print("Initializing ChromaDB...")
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_or_create_collection('products')
        print(f"ChromaDB collection: {collection.name}")
        print(f"Number of documents: {collection.count()}")
        
        print("\nInitializing EnsembleAgent...")
        ensemble = EnsembleAgent(collection)
        print("✅ EnsembleAgent ready!")
        
        print("\nInitializing MessagingAgent...")
        messenger = MessagingAgent()
        print("✅ MessagingAgent ready!")
        
        print("\n🎉 All agents initialized successfully!\n")


# ============================================================================
# SECTION 4: PIPELINE FUNCTIONS
# ============================================================================

def search_amazon(keyword: str, max_urls: int = 15) -> List[str]:
    """
    Step 1: Search for Amazon product URLs using Brave Search.
    
    Args:
        keyword: Search keyword (e.g., "Smart TV")
        max_urls: Maximum number of URLs to return
    
    Returns:
        List of Amazon product URLs
    """
    search_agent = AmazonSearchAgent()
    urls = search_agent.search(keyword, max_urls=max_urls)
    return urls


async def filter_sales(urls: List[str]) -> List[Tuple[str, dict]]:
    """
    Step 2: Filter URLs to keep only products on sale.
    
    NOTE: Uses Playwright because Amazon blocks requests library.
    
    Args:
        urls: List of product URLs
    
    Returns:
        List of (url, price_info) tuples for products on sale
    """
    return await filter_amazon_sale_urls_playwright(urls, headless=False)


async def scrape_products(sale_items: List[Tuple[str, dict]]) -> List[ScrapedAmazonDeal]:
    """
    Step 3: Scrape product details using Playwright.
    
    Args:
        sale_items: List of (url, price_info) tuples from filter step
    
    Returns:
        List of scraped product data
    """
    return await scrape_amazon_products(sale_items, headless=False)


def select_top_deals(scraped_deals: List[ScrapedAmazonDeal]) -> DealSelection:
    """
    Step 4: Select top 5 deals using GPT-5-mini.
    
    Args:
        scraped_deals: List of scraped products
    
    Returns:
        DealSelection with top 5 deals
    """
    scanner = AmazonScannerAgent()
    return scanner.scan(scraped_deals)


def estimate_prices(deal_selection: DealSelection, ensemble_agent: EnsembleAgent) -> List[Opportunity]:
    """
    Step 5: Estimate prices and calculate discounts.
    
    Args:
        deal_selection: Top deals selected
        ensemble_agent: Initialized EnsembleAgent
    
    Returns:
        List of opportunities sorted by discount (descending)
    """
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
    
    # Sort by discount descending
    opportunities.sort(key=lambda x: x.discount, reverse=True)
    return opportunities


# ============================================================================
# SECTION 5: GRADIO HELPERS
# ============================================================================

class QueueHandler(logging.Handler):
    """Custom logging handler that puts logs into a queue for Gradio."""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))


def setup_logging(q):
    """Setup logging to capture all logs into queue."""
    global log_queue
    log_queue = q
    
    handler = QueueHandler(q)
    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    
    # Add handler to root logger
    logger = logging.getLogger()
    # Remove existing QueueHandlers to avoid duplicates
    for h in logger.handlers[:]:
        if isinstance(h, QueueHandler):
            logger.removeHandler(h)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def html_for_logs(log_data: List[str]) -> str:
    """Convert log data to HTML for display."""
    # Keep last 20 logs
    recent_logs = log_data[-20:]
    # Format each log with color
    formatted = [reformat(log) for log in recent_logs]
    output = '<br>'.join(formatted)
    return f"""
    <div style="height: 350px; overflow-y: auto; border: 1px solid #444; 
                background-color: #1a1a2e; padding: 10px; font-family: monospace; 
                font-size: 12px; border-radius: 8px;">
    {output}
    </div>
    """


def opportunities_to_table(opportunities: List[Opportunity]) -> list:
    """
    Convert opportunities to data for Gradio Dataframe.
    
    Returns:
        List of rows: [Product, Sale $, Estimate $, Discount $, Discount %, URL]
    """
    rows = []
    for opp in opportunities:
        discount_pct = (opp.discount / opp.estimate * 100) if opp.estimate > 0 else 0
        status = "🔥" if opp.discount > 200 else ("✅" if opp.discount > 100 else ("👍" if opp.discount > 0 else "❌"))
        rows.append([
            opp.deal.product_description[:60] + "...",
            f"${opp.deal.price:.2f}",
            f"${opp.estimate:.2f}",
            f"${opp.discount:.2f}",
            f"{discount_pct:.1f}% {status}",
            opp.deal.url
        ])
    return rows


# ============================================================================
# SECTION 6: MAIN SEARCH FUNCTION (WITH THREADING & LOGGING)
# ============================================================================

def do_search_pipeline(keyword: str, max_urls: int, result_queue: queue.Queue):
    """
    Worker function that runs in a separate thread.
    Executes the full search pipeline and puts result in queue.
    
    Args:
        keyword: Search keyword
        max_urls: Maximum URLs to search
        result_queue: Queue to put final result
    """
    global current_opportunities
    
    try:
        # Step 1: Search
        logging.info(f"🔍 [Step 1/5] Searching for '{keyword}' on Amazon...")
        urls = search_amazon(keyword, max_urls)
        if not urls:
            result_queue.put(([], "❌ No products found. Try a different keyword."))
            return
        logging.info(f"✅ Found {len(urls)} product URLs")
        
        # Step 2: Filter sales (async - Playwright required for Amazon)
        logging.info(f"🏷️ [Step 2/5] Filtering sale items from {len(urls)} URLs (Playwright)...")
        
        # Handle async in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        sale_items = loop.run_until_complete(filter_sales(urls))
        if not sale_items:
            result_queue.put(([], "❌ No sale items found. Try a different keyword."))
            return
        logging.info(f"✅ Found {len(sale_items)} products on SALE")
        
        # Step 3: Scrape (async)
        logging.info(f"📦 [Step 3/5] Scraping {len(sale_items)} products with Playwright...")
        
        scraped = loop.run_until_complete(scrape_products(sale_items))
        if not scraped:
            result_queue.put(([], "❌ Could not scrape product details."))
            return
        logging.info(f"✅ Scraped {len(scraped)} products successfully")
        
        # Step 4: Select top deals
        logging.info(f"🤖 [Step 4/5] Selecting top 5 deals with GPT-5-mini...")
        deal_selection = select_top_deals(scraped)
        if not deal_selection or not deal_selection.deals:
            result_queue.put(([], "❌ Could not select deals."))
            return
        logging.info(f"✅ Selected {len(deal_selection.deals)} best deals")
        
        # Step 5: Estimate prices
        logging.info(f"💰 [Step 5/5] Estimating prices with EnsembleAgent (3 models)...")
        opportunities = estimate_prices(deal_selection, ensemble)
        current_opportunities = opportunities  # Save for push notification
        logging.info(f"✅ Estimated {len(opportunities)} opportunities")
        
        if opportunities:
            best = opportunities[0]
            logging.info(f"🏆 BEST DEAL: ${best.deal.price:.2f} → Est: ${best.estimate:.2f} = Discount ${best.discount:.2f}")
        
        # Return results
        table = opportunities_to_table(opportunities)
        status = f"✅ Found {len(opportunities)} deals! Best discount: ${opportunities[0].discount:.2f}" if opportunities else "No deals found."
        
        result_queue.put((table, status))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        result_queue.put(([], f"❌ Error: {str(e)}"))


def run_search_with_logging(keyword: str, max_urls: int, initial_log_data: List[str]):
    """
    Generator function for Gradio that yields updates during pipeline execution.
    
    Args:
        keyword: Search keyword
        max_urls: Maximum URLs
        initial_log_data: Previous log data (from gr.State)
    
    Yields:
        Tuple of (table_data, status_text, logs_html)
    """
    if not keyword or len(keyword.strip()) < 2:
        yield [], "❌ Please enter a keyword (at least 2 characters)", html_for_logs(["❌ Invalid keyword"])
        return
    
    # Setup
    log_q = queue.Queue()
    result_q = queue.Queue()
    setup_logging(log_q)
    
    log_data = initial_log_data.copy() if initial_log_data else []
    log_data.append(f"🚀 Starting Amazon search for: {keyword}")
    
    # Start worker thread
    thread = threading.Thread(
        target=do_search_pipeline,
        args=(keyword, int(max_urls), result_q)
    )
    thread.start()
    
    # Yield updates while thread is running
    final_result = None
    while thread.is_alive() or not log_q.empty() or final_result is None:
        # Check for new logs
        try:
            while True:
                message = log_q.get_nowait()
                log_data.append(message)
        except queue.Empty:
            pass
        
        # Check for result
        try:
            final_result = result_q.get_nowait()
        except queue.Empty:
            pass
        
        # Yield current state
        if final_result:
            table, status = final_result
            yield table, status, html_for_logs(log_data)
        else:
            yield [], "⏳ Processing...", html_for_logs(log_data)
        
        time.sleep(0.1)
    
    # Final yield
    if final_result:
        table, status = final_result
        log_data.append(f"✅ Pipeline completed!")
        yield table, status, html_for_logs(log_data)


# ============================================================================
# SECTION 7: PUSH NOTIFICATION
# ============================================================================

def send_push_notification(selected_index: int) -> str:
    """
    Send push notification for selected deal.
    
    Args:
        selected_index: Index of deal in table (0-based)
    
    Returns:
        Status message
    """
    global current_opportunities
    
    if not current_opportunities:
        return "❌ No deals available. Search first!"
    
    idx = int(selected_index)
    if idx < 0 or idx >= len(current_opportunities):
        return f"❌ Invalid selection. Choose 0-{len(current_opportunities)-1}"
    
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
        return f"❌ Failed: {str(e)}"


# ============================================================================
# SECTION 8: GRADIO UI DEFINITION
# ============================================================================

def create_gradio_app():
    """Create and return Gradio app with real-time logging."""
    
    with gr.Blocks(
        title="Amazon Deal Finder",
        theme=gr.themes.Soft(),
        fill_width=True,
    ) as app:
        
        # State for logs
        log_data_state = gr.State([])
        
        # Header
        gr.Markdown("""
        # 🛒 Amazon Deal Finder
        
        Tìm kiếm sản phẩm trên Amazon và phát hiện deals tốt nhất bằng AI!
        
        **Pipeline:** 1️⃣ Search → 2️⃣ Filter Sales (Playwright) → 3️⃣ Scrape → 4️⃣ Select Top 5 → 5️⃣ Estimate Prices
        
        ⚠️ **Note:** Amazon yêu cầu Playwright cho tất cả operations. Browser sẽ mở tự động.
        """)
        
        # Search Section
        with gr.Row():
            keyword_input = gr.Textbox(
                label="🔎 Keyword",
                placeholder="Enter product keyword (e.g., Smart TV, laptop, headphones)",
                scale=4
            )
            max_urls_input = gr.Number(
                label="Max URLs",
                value=15,
                minimum=5,
                maximum=30,
                precision=0,
                scale=1
            )
            search_btn = gr.Button("🔍 Search Amazon", variant="primary", scale=1)
        
        # Status
        status_text = gr.Textbox(
            label="Status",
            interactive=False,
            value="Ready to search..."
        )
        
        # Main content: Results + Logs side by side
        with gr.Row():
            # Left: Results Table
            with gr.Column(scale=3):
                results_table = gr.Dataframe(
                    headers=["Product", "Sale $", "Estimate $", "Discount $", "Discount %", "URL"],
                    label="🏆 Deal Results (sorted by discount)",
                    wrap=True,
                    column_widths=[4, 1, 1, 1, 1, 2],
                    max_height=350,
                )
            
            # Right: Real-time Logs
            with gr.Column(scale=2):
                gr.Markdown("### 📋 Pipeline Logs")
                logs_html = gr.HTML(
                    value='<div style="height: 350px; background-color: #1a1a2e; border-radius: 8px; padding: 10px; font-family: monospace; color: #87CEEB;">Ready to search...</div>'
                )
        
        # Push Notification Section
        with gr.Row():
            deal_index = gr.Number(
                label="Deal # to notify (0 = best deal)",
                value=0,
                minimum=0,
                precision=0,
                scale=1
            )
            push_btn = gr.Button("📱 Send Push Notification", variant="secondary", scale=1)
        
        # Notification status
        push_status = gr.Textbox(
            label="📱 Notification Status",
            interactive=False,
            placeholder="Click 'Send Push Notification' to send...",
            lines=2,
        )
        
        # Event handlers
        search_btn.click(
            fn=run_search_with_logging,
            inputs=[keyword_input, max_urls_input, log_data_state],
            outputs=[results_table, status_text, logs_html]
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
        
        **Notes:** 
        - Browser window sẽ mở 2 lần: 1 lần filter sale, 1 lần scrape details
        - Amazon sử dụng US Zip Code 96150 (California)
        - Push notifications require Pushover setup
        """)
    
    return app


# ============================================================================
# SECTION 9: MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Amazon Deal Finder - Starting up...")
    print("=" * 60)
    
    # Initialize agents (this may take 5-10 seconds)
    init_agents()
    
    # Create and launch Gradio app
    app = create_gradio_app()
    
    print("\n" + "=" * 60)
    print("✅ Ready! Opening browser...")
    print("=" * 60 + "\n")
    
    app.launch(share=False, inbrowser=True)
