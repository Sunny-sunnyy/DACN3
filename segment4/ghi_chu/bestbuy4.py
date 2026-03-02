"""
=============================================================================
MULTI-SOURCE DEAL FINDER V4 - GRADIO WEB APP
=============================================================================
File: bestbuy4.py (Phiên bản đã refactor từ bestbuy3.py - giảm từ 1226 dòng xuống ~420 dòng)

MỤC ĐÍCH:
- Tìm kiếm deals (sản phẩm giảm giá) trên CÙNG LÚC BestBuy VÀ Amazon
- Sử dụng AI để làm rõ nhu cầu người dùng (Clarification Flow)
- Dự đoán giá trị thực của sản phẩm bằng 3 models AI (EnsembleAgent)

2 LUỒNG HOẠT ĐỘNG:
1. Clarification Flow: User trả lời 3 câu hỏi → Query được tinh chỉnh → Kết quả tốt hơn
2. Skip Flow: User bỏ qua câu hỏi → Tìm kiếm với keyword gốc

PIPELINE 6 BƯỚC:
1. [ClarificationAgent] Tạo 3 câu hỏi làm rõ nhu cầu (GPT-5-mini)
2. [ClarificationAgent] Tạo refined query từ câu trả lời HOẶC user skip
3. [SONG SONG] Tìm URLs sản phẩm trên BestBuy + Amazon (Brave Search MCP)
4. [Lọc] BestBuy: BeautifulSoup | Amazon: Playwright - Chỉ giữ sản phẩm đang sale
5. [Scrape] Cả 2: Playwright - Lấy thông tin chi tiết sản phẩm
6. [GPT] Chọn top 5 deals tốt nhất từ pool tổng hợp
7. [EnsembleAgent] Dự đoán giá trị thực (3 models: Frontier 80% + Specialist 10% + Neural 10%)

CÁC FILE LIÊN QUAN (ĐÃ REFACTOR):
- bestbuy_untils/clarification_agent.py  → ClarificationAgent + Pydantic schemas
- bestbuy_untils/unified_deal.py         → UnifiedScrapedDeal class (gộp deals từ cả 2 nguồn)
- bestbuy_untils/multi_source_scanner_agent.py → MultiSourceScannerAgent (chọn top 5)
- bestbuy_untils/gradio_helpers.py       → Helper functions cho Gradio UI
"""

# =============================================================================
# PHẦN 1: IMPORT THƯ VIỆN
# =============================================================================

import os
import sys
import logging      # Ghi log quá trình chạy
import queue        # Queue cho multi-threading logs
import threading    # Chạy pipeline trong thread riêng
import time
import asyncio      # Xử lý async/await cho Playwright
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor  # Chạy song song BestBuy + Amazon

import gradio as gr      # Tạo Web UI
import chromadb          # Vector database cho RAG (400K sản phẩm)
from dotenv import load_dotenv  # Load biến môi trường từ .env

# =============================================================================
# PHẦN 2: IMPORT CÁC MODULES ĐÃ REFACTOR
# =============================================================================

# --- Import modules BestBuy (từ price_agents/) ---
from price_agents.bestbuy_deals import (
    ScrapedBestBuyDeal,      # Class chứa thông tin sản phẩm BestBuy
    filter_sale_urls,         # Lọc URLs chỉ giữ sản phẩm đang sale (BeautifulSoup)
    scrape_bestbuy_products   # Scrape chi tiết sản phẩm (Playwright)
)
from price_agents.bestbuy_scanner_agent import BestBuySearchAgent  # Tìm kiếm URLs BestBuy

# --- Import modules Amazon (từ price_agents/) ---
from price_agents.amazon_deals import (
    ScrapedAmazonDeal,                    # Class chứa thông tin sản phẩm Amazon
    filter_amazon_sale_urls_playwright,   # Lọc URLs sale (phải dùng Playwright vì Amazon block requests)
    scrape_amazon_products                # Scrape chi tiết sản phẩm (Playwright)
)
from price_agents.amazon_scanner_agent import AmazonSearchAgent  # Tìm kiếm URLs Amazon

# --- Import modules đã refactor (từ bestbuy_untils/) ---
from bestbuy_untils.clarification_agent import (
    ClarificationAgent,       # Agent tạo câu hỏi làm rõ nhu cầu
    ClarificationQuestion,    # Schema cho 1 câu hỏi
    ClarificationResponse,    # Schema cho response (3 câu hỏi)
    RefinedQuery              # Schema cho query đã tinh chỉnh
)
from bestbuy_untils.unified_deal import UnifiedScrapedDeal  # Class gộp deals từ BestBuy + Amazon
from bestbuy_untils.multi_source_scanner_agent import MultiSourceScannerAgent  # Chọn top 5 từ pool tổng hợp
from bestbuy_untils.gradio_helpers import (
    QueueHandler,             # Handler đưa logs vào queue
    setup_logging,            # Cấu hình logging
    html_for_logs,            # Format logs thành HTML hiển thị trên Gradio
    opportunities_to_table,   # Chuyển opportunities thành table data
    format_questions_html     # Format câu hỏi thành HTML cards
)

# --- Import agents dự đoán giá và gửi notification ---
from price_agents.ensemble_agent import EnsembleAgent    # Ensemble 3 models dự đoán giá
from price_agents.messaging_agent import MessagingAgent  # Gửi push notification
from price_agents.deals import Deal, DealSelection, Opportunity  # Data classes


# =============================================================================
# PHẦN 3: CẤU HÌNH BAN ĐẦU
# =============================================================================

load_dotenv(override=True)  # Load API keys từ file .env

# Cấu hình logging cơ bản
logging.basicConfig(level=logging.INFO)
root = logging.getLogger()
root.setLevel(logging.INFO)

# Đường dẫn ChromaDB (vector database chứa 400K sản phẩm cho RAG)
DB_PATH = "products_vectorstore"


# =============================================================================
# PHẦN 4: BIẾN TOÀN CỤC (GLOBAL VARIABLES)
# =============================================================================

# --- Các agents (khởi tạo 1 lần khi app start) ---
ensemble: Optional[EnsembleAgent] = None           # Ensemble 3 models dự đoán giá
messenger: Optional[MessagingAgent] = None         # Gửi push notification
clarification_agent: Optional[ClarificationAgent] = None  # Tạo câu hỏi làm rõ
multi_scanner: Optional[MultiSourceScannerAgent] = None   # Chọn top 5 deals

# --- Kết quả tìm kiếm (dùng cho push notification) ---
current_opportunities: List[Opportunity] = []  # Danh sách deals đã tìm được

# --- Trạng thái flow làm rõ nhu cầu ---
current_questions: Optional[ClarificationResponse] = None  # Câu hỏi đã generate
current_keyword: str = ""                                   # Keyword user nhập
current_max_urls: int = 10                                  # Số URLs tối đa mỗi nguồn


# =============================================================================
# PHẦN 5: KHỞI TẠO AGENTS (GỌI 1 LẦN KHI APP START)
# =============================================================================

def init_agents() -> None:
    """
    Khởi tạo tất cả agents và ChromaDB.
    
    Được gọi MỘT LẦN DUY NHẤT khi app khởi động.
    Quá trình này mất khoảng 5-10 giây.
    
    Khởi tạo:
    - ChromaDB: Load vector database 400K sản phẩm
    - EnsembleAgent: 3 models (Frontier + Specialist + Neural)
    - MessagingAgent: GPT-5-nano + Pushover API
    - ClarificationAgent: GPT-5-mini
    - MultiSourceScannerAgent: GPT-5-mini
    """
    global ensemble, messenger, clarification_agent, multi_scanner
    
    # Chỉ khởi tạo nếu chưa có (tránh khởi tạo lại)
    if ensemble is None:
        # 1. Khởi tạo ChromaDB - vector database cho RAG
        print("Initializing ChromaDB...")
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_or_create_collection('products')
        print(f"ChromaDB collection: {collection.name}")
        print(f"Number of documents: {collection.count()}")  # Khoảng 400K sản phẩm
        
        # 2. Khởi tạo EnsembleAgent - dự đoán giá bằng 3 models
        print("\nInitializing EnsembleAgent...")
        ensemble = EnsembleAgent(collection)  # Truyền collection cho RAG
        print("EnsembleAgent ready!")
        
        # 3. Khởi tạo MessagingAgent - gửi push notification
        print("\nInitializing MessagingAgent...")
        messenger = MessagingAgent()
        print("MessagingAgent ready!")
        
        # 4. Khởi tạo ClarificationAgent - tạo câu hỏi làm rõ
        print("\nInitializing ClarificationAgent...")
        clarification_agent = ClarificationAgent()
        print("ClarificationAgent ready!")
        
        # 5. Khởi tạo MultiSourceScannerAgent - chọn top 5 deals
        print("\nInitializing MultiSourceScannerAgent...")
        multi_scanner = MultiSourceScannerAgent()
        print("MultiSourceScannerAgent ready!")
        
        print("\nAll agents initialized successfully!\n")


# =============================================================================
# PHẦN 6: CÁC HÀM PIPELINE (TÌM KIẾM, LỌC, SCRAPE)
# =============================================================================

def search_bestbuy(keyword: str, max_urls: int = 10) -> List[str]:
    """
    Tìm kiếm URLs sản phẩm trên BestBuy.
    
    Sử dụng BestBuySearchAgent với:
    - GPT-5-nano để xử lý query
    - Brave Search MCP để tìm kiếm web
    
    Args:
        keyword: Từ khóa tìm kiếm (đã được refine hoặc gốc)
        max_urls: Số URLs tối đa cần lấy
    
    Returns:
        List URLs sản phẩm BestBuy (VD: ["https://www.bestbuy.com/site/...", ...])
    """
    try:
        search_agent = BestBuySearchAgent()
        return search_agent.search(keyword, max_urls=max_urls)
    except Exception as e:
        logging.error(f"BestBuy search error: {e}")
        return []


def search_amazon(keyword: str, max_urls: int = 10) -> List[str]:
    """
    Tìm kiếm URLs sản phẩm trên Amazon.
    
    Sử dụng AmazonSearchAgent với:
    - GPT-5-nano để xử lý query
    - Brave Search MCP để tìm kiếm web
    
    Args:
        keyword: Từ khóa tìm kiếm
        max_urls: Số URLs tối đa cần lấy
    
    Returns:
        List URLs sản phẩm Amazon (VD: ["https://www.amazon.com/dp/...", ...])
    """
    try:
        search_agent = AmazonSearchAgent()
        return search_agent.search(keyword, max_urls=max_urls)
    except Exception as e:
        logging.error(f"Amazon search error: {e}")
        return []


def filter_bestbuy_sales(urls: List[str]) -> List[str]:
    """
    Lọc URLs BestBuy - chỉ giữ sản phẩm đang SALE.
    
    Sử dụng BeautifulSoup (nhanh, không cần browser):
    - Fetch HTML của trang
    - Check có class "priceView-subscription-price" không
    - Nếu có → sản phẩm đang sale
    
    Args:
        urls: List URLs cần lọc
    
    Returns:
        List URLs sản phẩm đang sale
    """
    return filter_sale_urls(urls)


async def filter_amazon_sales(urls: List[str]) -> List[Tuple[str, dict]]:
    """
    Lọc URLs Amazon - chỉ giữ sản phẩm đang SALE.
    
    PHẢI dùng Playwright (Amazon block requests thông thường):
    - Mở browser thật
    - Load trang sản phẩm
    - Check có price info không
    
    Args:
        urls: List URLs cần lọc
    
    Returns:
        List tuples (url, price_info) cho sản phẩm đang sale
    """
    return await filter_amazon_sale_urls_playwright(urls, headless=False)


async def scrape_bestbuy(urls: List[str]) -> List[ScrapedBestBuyDeal]:
    """
    Scrape chi tiết sản phẩm từ BestBuy.
    
    Sử dụng Playwright để:
    - Lấy tên sản phẩm, brand
    - Lấy giá sale
    - Lấy features (click nút "Features")
    
    Args:
        urls: List URLs sản phẩm đang sale
    
    Returns:
        List ScrapedBestBuyDeal với đầy đủ thông tin
    """
    return await scrape_bestbuy_products(urls, headless=False)


async def scrape_amazon(sale_items: List[Tuple[str, dict]]) -> List[ScrapedAmazonDeal]:
    """
    Scrape chi tiết sản phẩm từ Amazon.
    
    Sử dụng Playwright để:
    - Lấy tên sản phẩm, brand
    - Lấy giá sale
    - Lấy features/description
    
    Args:
        sale_items: List tuples (url, price_info)
    
    Returns:
        List ScrapedAmazonDeal với đầy đủ thông tin
    """
    return await scrape_amazon_products(sale_items, headless=False)


def estimate_prices(deal_selection: DealSelection, ensemble_agent: EnsembleAgent) -> List[Opportunity]:
    """
    Dự đoán giá trị thực và tính discount cho mỗi deal.
    
    Sử dụng EnsembleAgent (3 models):
    - FrontierAgent (80%): GPT-5.1 + RAG (ChromaDB 400K products)
    - SpecialistAgent (10%): Fine-tuned Llama (Modal serverless)
    - NeuralNetworkAgent (10%): PyTorch Deep NN (local)
    
    Formula: estimate = frontier * 0.8 + specialist * 0.1 + neural * 0.1
    Discount = estimate - sale_price
    
    Args:
        deal_selection: DealSelection chứa top 5 deals
        ensemble_agent: EnsembleAgent đã khởi tạo
    
    Returns:
        List Opportunity, sorted by discount (cao nhất đầu tiên)
    """
    opportunities = []
    
    for deal in deal_selection.deals:
        # Dự đoán giá trị thực bằng ensemble
        estimate = ensemble_agent.price(deal.product_description)
        
        # Tính discount = giá trị thực - giá sale
        # Discount > 0 nghĩa là deal tốt (mua rẻ hơn giá trị thực)
        discount = estimate - deal.price
        
        opportunity = Opportunity(
            deal=deal,
            estimate=estimate,
            discount=discount
        )
        opportunities.append(opportunity)
    
    # Sắp xếp theo discount giảm dần (deal tốt nhất lên đầu)
    opportunities.sort(key=lambda x: x.discount, reverse=True)
    return opportunities


# =============================================================================
# PHẦN 7: XỬ LÝ FLOW LÀM RÕ NHU CẦU (CLARIFICATION HANDLERS)
# =============================================================================

def generate_questions_handler(keyword: str):
    """
    Xử lý khi user nhập keyword và click "Generate Questions".
    
    Flow:
    1. Validate keyword (>= 2 ký tự)
    2. Gọi ClarificationAgent.generate_questions()
    3. Format câu hỏi thành HTML
    4. Hiển thị section trả lời
    
    Args:
        keyword: Từ khóa user nhập (VD: "laptop")
    
    Returns:
        Tuple (questions_html, status_text, answers_visible, answers_visible)
    """
    global current_questions, current_keyword
    
    # Validate: keyword phải >= 2 ký tự
    if not keyword or len(keyword.strip()) < 2:
        return (
            "",
            "Please enter a keyword (at least 2 characters)",
            gr.update(visible=False),  # Ẩn section trả lời
            gr.update(visible=False),
        )
    
    try:
        # Lưu keyword hiện tại vào global
        current_keyword = keyword.strip()
        logging.info(f"Generating questions for: {current_keyword}")
        
        # Gọi GPT-5-mini tạo 3 câu hỏi làm rõ
        response = clarification_agent.generate_questions(current_keyword)
        current_questions = response  # Lưu để dùng sau
        
        # Format câu hỏi thành HTML cards
        questions_html = format_questions_html(response.questions)
        
        return (
            questions_html,
            f"Category: {response.product_category} | Answer the questions below or skip to search directly.",
            gr.update(visible=True),   # Hiện section trả lời
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
    """
    Xử lý khi user submit câu trả lời.
    
    Flow:
    1. Gọi ClarificationAgent.build_refined_query() để tạo query tối ưu
    2. Chạy pipeline tìm kiếm với refined query
    
    Args:
        answer1, answer2, answer3: Câu trả lời của user
        max_urls: Số URLs tối đa mỗi nguồn
        initial_log_data: Log data ban đầu
    
    Yields:
        Tuple (table_data, status, comparison_text, logs_html)
    """
    global current_questions, current_keyword, current_max_urls
    
    # Validate: phải có câu hỏi đã generate
    if not current_questions:
        yield [], "Please generate questions first!", "", html_for_logs(["Please generate questions first!"])
        return
    
    current_max_urls = int(max_urls) if max_urls else 10
    answers = [answer1.strip(), answer2.strip(), answer3.strip()]
    
    try:
        # Gọi GPT-5-mini tạo refined query từ câu trả lời
        # VD: "laptop" + ["Acer", "for students", "under $800"]
        #   → "Acer laptops for students under $800"
        refined = clarification_agent.build_refined_query(
            current_keyword,
            current_questions.questions,
            answers
        )
        search_query = refined.query
        comparison_text = f"🔄 Original: \"{current_keyword}\" → Refined: \"{search_query}\""
    except Exception as e:
        logging.error(f"Error building refined query: {e}")
        # Fallback: dùng keyword gốc
        search_query = current_keyword
        comparison_text = f"Using original keyword: \"{current_keyword}\""
    
    # Chạy pipeline tìm kiếm (generator yields updates)
    yield from run_search_pipeline(search_query, comparison_text, initial_log_data)


def skip_and_search_handler(max_urls: int, initial_log_data: List[str]):
    """
    Xử lý khi user click "Skip" - tìm kiếm với keyword gốc.
    
    Args:
        max_urls: Số URLs tối đa mỗi nguồn
        initial_log_data: Log data ban đầu
    
    Yields:
        Tuple (table_data, status, comparison_text, logs_html)
    """
    global current_keyword, current_max_urls
    
    # Validate: phải có keyword
    if not current_keyword:
        yield [], "Please enter a keyword first!", "", html_for_logs(["Please enter a keyword first!"])
        return
    
    current_max_urls = int(max_urls) if max_urls else 10
    comparison_text = f"⏩ Skip mode - searching with: \"{current_keyword}\""
    
    # Chạy pipeline với keyword gốc
    yield from run_search_pipeline(current_keyword, comparison_text, initial_log_data)


# =============================================================================
# PHẦN 8: MAIN PIPELINE (TÌM KIẾM ĐA NGUỒN - CHẠY TRONG THREAD RIÊNG)
# =============================================================================

def do_search_pipeline(search_query: str, max_urls: int, result_queue: queue.Queue) -> None:
    """
    Worker function - chạy trong thread riêng.
    Thực hiện TOÀN BỘ pipeline tìm kiếm 6 bước và đưa kết quả vào queue.
    
    PIPELINE 6 BƯỚC:
    1. Search: Tìm URLs trên BestBuy + Amazon (SONG SONG)
    2. Filter: Lọc chỉ giữ sản phẩm đang sale
    3. Scrape: Lấy chi tiết sản phẩm bằng Playwright
    4. Combine: Gộp deals từ cả 2 nguồn vào pool thống nhất
    5. Select: GPT chọn top 5 deals tốt nhất
    6. Estimate: Dự đoán giá trị thực và tính discount
    
    Args:
        search_query: Query tìm kiếm (đã refine hoặc gốc)
        max_urls: Số URLs tối đa mỗi nguồn
        result_queue: Queue để đưa kết quả ra
    """
    global current_opportunities
    
    try:
        # =====================================================================
        # STEP 1: TÌM KIẾM URLS TRÊN CẢ 2 NGUỒN (CHẠY SONG SONG)
        # =====================================================================
        logging.info(f"🔍 [Step 1/6] Searching '{search_query}' on BestBuy + Amazon...")
        
        bestbuy_urls = []
        amazon_urls = []
        
        # Dùng ThreadPoolExecutor để chạy song song 2 search agents
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_bb = executor.submit(search_bestbuy, search_query, max_urls)
            future_az = executor.submit(search_amazon, search_query, max_urls)
            
            # Đợi kết quả từ BestBuy (timeout 120s)
            try:
                bestbuy_urls = future_bb.result(timeout=120)
                logging.info(f"  📦 BestBuy: {len(bestbuy_urls)} URLs")
            except Exception as e:
                logging.warning(f"  ⚠️ BestBuy search failed: {e}")
            
            # Đợi kết quả từ Amazon (timeout 120s)
            try:
                amazon_urls = future_az.result(timeout=120)
                logging.info(f"  📦 Amazon: {len(amazon_urls)} URLs")
            except Exception as e:
                logging.warning(f"  ⚠️ Amazon search failed: {e}")
        
        # Kiểm tra có kết quả không
        if not bestbuy_urls and not amazon_urls:
            result_queue.put(([], "No products found. Try a different keyword."))
            return
        
        logging.info(f"✅ Total URLs: {len(bestbuy_urls)} (BestBuy) + {len(amazon_urls)} (Amazon)")
        
        # =====================================================================
        # STEP 2: LỌC CHỈ GIỮ SẢN PHẨM ĐANG SALE
        # =====================================================================
        logging.info(f"🏷️ [Step 2/6] Filtering sale items...")
        
        # BestBuy: Dùng BeautifulSoup (nhanh)
        bestbuy_sale_urls = []
        if bestbuy_urls:
            logging.info(f"  🔎 Filtering {len(bestbuy_urls)} BestBuy URLs (BeautifulSoup)...")
            bestbuy_sale_urls = filter_bestbuy_sales(bestbuy_urls)
            logging.info(f"  ✅ BestBuy: {len(bestbuy_sale_urls)} sale items")
        
        # Amazon: Dùng Playwright (Amazon block requests thông thường)
        amazon_sale_items = []
        if amazon_urls:
            logging.info(f"  🔎 Filtering {len(amazon_urls)} Amazon URLs (Playwright)...")
            
            # Xử lý async trong sync context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            amazon_sale_items = loop.run_until_complete(filter_amazon_sales(amazon_urls))
            logging.info(f"  ✅ Amazon: {len(amazon_sale_items)} sale items")
        
        # Kiểm tra có sản phẩm sale không
        if not bestbuy_sale_urls and not amazon_sale_items:
            result_queue.put(([], "No sale items found. Try a different keyword."))
            return
        
        # =====================================================================
        # STEP 3: SCRAPE CHI TIẾT SẢN PHẨM BẰNG PLAYWRIGHT
        # =====================================================================
        logging.info(f"📦 [Step 3/6] Scraping product details (Playwright)...")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        bestbuy_scraped = []
        amazon_scraped = []
        
        # Scrape BestBuy
        if bestbuy_sale_urls:
            logging.info(f"  🛒 Scraping {len(bestbuy_sale_urls)} BestBuy products...")
            bestbuy_scraped = loop.run_until_complete(scrape_bestbuy(bestbuy_sale_urls))
            logging.info(f"  ✅ BestBuy: Scraped {len(bestbuy_scraped)} products")
        
        # Scrape Amazon
        if amazon_sale_items:
            logging.info(f"  🛒 Scraping {len(amazon_sale_items)} Amazon products...")
            amazon_scraped = loop.run_until_complete(scrape_amazon(amazon_sale_items))
            logging.info(f"  ✅ Amazon: Scraped {len(amazon_scraped)} products")
        
        if not bestbuy_scraped and not amazon_scraped:
            result_queue.put(([], "Could not scrape product details."))
            return
        
        # =====================================================================
        # STEP 4: GỘP DEALS TỪ CẢ 2 NGUỒN VÀO POOL THỐNG NHẤT
        # =====================================================================
        logging.info(f"🔀 [Step 4/6] Combining products from both sources...")
        
        unified_deals = []
        
        # Chuyển đổi BestBuy deals sang UnifiedScrapedDeal
        for deal in bestbuy_scraped:
            unified_deals.append(UnifiedScrapedDeal.from_bestbuy(deal))
        
        # Chuyển đổi Amazon deals sang UnifiedScrapedDeal
        for deal in amazon_scraped:
            unified_deals.append(UnifiedScrapedDeal.from_amazon(deal))
        
        logging.info(f"✅ Combined pool: {len(unified_deals)} products")
        
        # =====================================================================
        # STEP 5: GPT CHỌN TOP 5 DEALS TỐT NHẤT TỪ POOL
        # =====================================================================
        logging.info(f"🤖 [Step 5/6] GPT selecting top 5 from combined pool...")
        
        # Gọi MultiSourceScannerAgent (GPT-5-mini)
        # Agent sẽ đọc qua tất cả deals và chọn 5 deals có description tốt nhất
        deal_selection = multi_scanner.scan(unified_deals)
        
        if not deal_selection or not deal_selection.deals:
            result_queue.put(([], "Could not select deals."))
            return
        
        logging.info(f"✅ Selected {len(deal_selection.deals)} best deals")
        
        # =====================================================================
        # STEP 6: DỰ ĐOÁN GIÁ TRỊ THỰC VỚI ENSEMBLEAGENT (3 MODELS)
        # =====================================================================
        logging.info(f"💰 [Step 6/6] Estimating prices with EnsembleAgent (3 models)...")
        
        # Dự đoán giá và tính discount cho mỗi deal
        opportunities = estimate_prices(deal_selection, ensemble)
        current_opportunities = opportunities  # Lưu để dùng cho push notification
        
        logging.info(f"✅ Estimated {len(opportunities)} opportunities")
        
        # Log best deal
        if opportunities:
            best = opportunities[0]
            logging.info(f"🏆 BEST DEAL: ${best.deal.price:.2f} → Est: ${best.estimate:.2f} = Discount ${best.discount:.2f}")
        
        # Chuyển đổi thành table data cho Gradio
        table = opportunities_to_table(opportunities)
        status = f"✅ Found {len(opportunities)} deals! Best discount: ${opportunities[0].discount:.2f}" if opportunities else "No deals found."
        
        # Đưa kết quả vào queue
        result_queue.put((table, status))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        result_queue.put(([], f"Error: {str(e)}"))


def run_search_pipeline(search_query: str, comparison_text: str, initial_log_data: List[str]):
    """
    Generator function - chạy pipeline trong thread và yield updates cho Gradio.
    
    Tại sao dùng generator?
    - Gradio cần nhận updates liên tục để hiển thị logs real-time
    - Pipeline chạy lâu (30-60 giây) nên cần yield updates
    - Thread riêng cho pipeline, main thread cho UI
    
    Args:
        search_query: Query tìm kiếm
        comparison_text: Text so sánh original vs refined
        initial_log_data: Log data ban đầu
    
    Yields:
        Tuple (table_data, status, comparison_text, logs_html)
    """
    global current_max_urls
    max_urls = current_max_urls if current_max_urls else 10
    
    # Setup logging vào queue (để hiển thị real-time trên Gradio)
    log_q = queue.Queue()
    result_q = queue.Queue()
    setup_logging(log_q)
    
    # Khởi tạo log data
    log_data = initial_log_data.copy() if initial_log_data else []
    log_data.append(f"🚀 Starting MULTI-SOURCE search: {search_query} (max {max_urls} URLs per source)")
    log_data.append("📦 Sources: BestBuy + Amazon")
    
    # Chạy pipeline trong thread riêng
    thread = threading.Thread(
        target=do_search_pipeline,
        args=(search_query, max_urls, result_q)
    )
    thread.start()
    
    # Yield updates liên tục trong khi thread đang chạy
    final_result = None
    while thread.is_alive() or not log_q.empty() or final_result is None:
        # Lấy logs mới từ queue
        try:
            while True:
                message = log_q.get_nowait()
                log_data.append(message)
        except queue.Empty:
            pass
        
        # Kiểm tra có kết quả chưa
        try:
            final_result = result_q.get_nowait()
        except queue.Empty:
            pass
        
        # Yield state hiện tại
        if final_result:
            table, status = final_result
            yield table, status, comparison_text, html_for_logs(log_data)
        else:
            yield [], "⏳ Processing...", comparison_text, html_for_logs(log_data)
        
        time.sleep(0.1)  # Delay nhỏ để không spam updates
    
    # Yield kết quả cuối cùng
    if final_result:
        table, status = final_result
        log_data.append(f"✅ Pipeline completed!")
        yield table, status, comparison_text, html_for_logs(log_data)


# =============================================================================
# PHẦN 9: GỬI PUSH NOTIFICATION
# =============================================================================

def send_push_notification(selected_index: int) -> str:
    """
    Gửi push notification cho deal được chọn.
    
    Sử dụng MessagingAgent với:
    - GPT-5-nano để craft message hấp dẫn
    - Pushover API để gửi notification tới điện thoại
    
    Args:
        selected_index: Index của deal trong bảng (0 = deal tốt nhất)
    
    Returns:
        Status message (thành công hoặc lỗi)
    """
    global current_opportunities
    
    # Validate: phải có opportunities
    if not current_opportunities:
        return "No deals available. Search first!"
    
    # Validate: index hợp lệ
    idx = int(selected_index)
    if idx < 0 or idx >= len(current_opportunities):
        return f"Invalid selection. Choose 0-{len(current_opportunities)-1}"
    
    opp = current_opportunities[idx]
    
    try:
        # Gọi MessagingAgent gửi notification
        messenger.notify(
            description=opp.deal.product_description[:200],  # Giới hạn 200 ký tự
            deal_price=opp.deal.price,
            estimated_true_value=opp.estimate,
            url=opp.deal.url
        )
        return f"✅ Sent! Deal #{idx}: {opp.deal.product_description[:40]}... (${opp.deal.price:.2f})"
    except Exception as e:
        return f"Failed: {str(e)}"


# =============================================================================
# PHẦN 10: ĐỊNH NGHĨA GIAO DIỆN GRADIO
# =============================================================================

def create_gradio_app():
    """
    Tạo và trả về Gradio app.
    
    Giao diện gồm:
    - Step 1: Input keyword + Max URLs
    - Step 2: Hiển thị câu hỏi làm rõ
    - Step 3: Input câu trả lời + Submit/Skip buttons
    - Results: Bảng kết quả + Logs real-time
    - Footer: Push notification
    
    Returns:
        Gradio Blocks app
    """
    
    with gr.Blocks(
        title="Multi-Source Deal Finder v4",
        theme=gr.themes.Soft(),  # Theme sáng, dễ nhìn
        fill_width=True,
    ) as app:
        
        # State lưu log data giữa các lần yield
        log_data_state = gr.State([])
        
        # =====================================================================
        # HEADER
        # =====================================================================
        gr.Markdown("""
        # 🛒 Multi-Source Deal Finder v4
        
        Search on **BOTH** BestBuy AND Amazon simultaneously!
        
        **Flow:** 1️⃣ Enter Keyword → 2️⃣ Answer Questions (or Skip) → 3️⃣ Search BestBuy + Amazon → 4️⃣ Estimate Prices
        
        ⚠️ **Note:** Browser windows will open for Playwright scraping.
        """)
        
        # =====================================================================
        # STEP 1: NHẬP KEYWORD
        # =====================================================================
        with gr.Group():
            gr.Markdown("### 📝 Step 1: Enter Product Keyword")
            with gr.Row():
                # Input keyword
                keyword_input = gr.Textbox(
                    label="🔎 What are you looking for?",
                    placeholder="Enter product keyword (e.g., laptop, Smart TV, headphones)",
                    scale=3
                )
                # Input max URLs
                max_urls_input = gr.Number(
                    label="Max URLs (per source)",
                    value=10,
                    minimum=5,
                    maximum=20,
                    precision=0,
                    scale=1
                )
                # Button generate questions
                generate_btn = gr.Button("🤖 Generate Questions", variant="primary", scale=1)
        
        # Status text
        status_text = gr.Textbox(
            label="Status",
            interactive=False,
            value="Enter a keyword and click 'Generate Questions'"
        )
        
        # =====================================================================
        # STEP 2: HIỂN THỊ CÂU HỎI LÀM RÕ
        # =====================================================================
        with gr.Group():
            questions_html = gr.HTML(
                value='<div style="padding: 20px; text-align: center; color: #888;">Questions will appear here after you enter a keyword...</div>'
            )
        
        # =====================================================================
        # STEP 3: NHẬP CÂU TRẢ LỜI
        # =====================================================================
        with gr.Group(visible=False) as answers_section:
            gr.Markdown("### ✍️ Step 2: Answer the Questions")
            gr.Markdown("*Type your answers freely (e.g., 'Acer', 'for students', 'under $800') or use options above*")
            
            # 3 ô input cho 3 câu trả lời
            with gr.Row():
                answer1 = gr.Textbox(label="Answer 1", placeholder="Your answer to Q1...")
                answer2 = gr.Textbox(label="Answer 2", placeholder="Your answer to Q2...")
                answer3 = gr.Textbox(label="Answer 3", placeholder="Your answer to Q3...")
            
            # Buttons Submit và Skip
            with gr.Row():
                submit_btn = gr.Button("✅ Submit & Search (BestBuy + Amazon)", variant="primary", scale=2)
                skip_btn = gr.Button("⏩ Skip, Search Now", variant="secondary", scale=1)
        
        # =====================================================================
        # SO SÁNH QUERY
        # =====================================================================
        query_comparison = gr.Textbox(
            label="🔄 Query Comparison",
            interactive=False,
            visible=True,
            placeholder="Original vs Refined query will appear here..."
        )
        
        # =====================================================================
        # KẾT QUẢ: BẢNG + LOGS
        # =====================================================================
        with gr.Row():
            # Cột trái: Bảng kết quả
            with gr.Column(scale=3):
                gr.Markdown("### 🏆 Deal Results (BestBuy + Amazon combined)")
                results_table = gr.Dataframe(
                    headers=["Product", "Sale $", "Estimate $", "Discount $", "Discount %", "URL"],
                    label="Sorted by discount (best first)",
                    wrap=True,
                    column_widths=[4, 1, 1, 1, 1, 2],
                    max_height=350,
                )
            
            # Cột phải: Logs real-time
            with gr.Column(scale=2):
                gr.Markdown("### 📋 Pipeline Logs")
                logs_html = gr.HTML(
                    value='<div style="height: 400px; background-color: #1a1a2e; border-radius: 8px; padding: 10px; font-family: monospace; color: #87CEEB;">Ready to search...</div>'
                )
        
        # =====================================================================
        # PUSH NOTIFICATION
        # =====================================================================
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
        
        # =====================================================================
        # KẾT NỐI EVENT HANDLERS
        # =====================================================================
        
        # Click "Generate Questions" → Gọi generate_questions_handler
        generate_btn.click(
            fn=generate_questions_handler,
            inputs=[keyword_input],
            outputs=[questions_html, status_text, answers_section, answers_section],
        )
        
        # Click "Submit" → Gọi submit_answers_handler (generator)
        submit_btn.click(
            fn=submit_answers_handler,
            inputs=[answer1, answer2, answer3, max_urls_input, log_data_state],
            outputs=[results_table, status_text, query_comparison, logs_html],
        )
        
        # Click "Skip" → Gọi skip_and_search_handler (generator)
        skip_btn.click(
            fn=skip_and_search_handler,
            inputs=[max_urls_input, log_data_state],
            outputs=[results_table, status_text, query_comparison, logs_html],
        )
        
        # Click "Send Push Notification" → Gọi send_push_notification
        push_btn.click(
            fn=send_push_notification,
            inputs=[deal_index],
            outputs=[push_status],
        )
        
        # =====================================================================
        # FOOTER
        # =====================================================================
        gr.Markdown("""
        ---
        **Legend:** 🔥 Discount > $200 | ✅ Discount > $100 | 👍 Positive discount | ❌ Overpriced
        
        **Sources:** 
        - 🟦 BestBuy: Filter uses BeautifulSoup, scrape uses Playwright
        - 🟠 Amazon: Both filter and scrape use Playwright
        
        **Notes:** Browser windows will open during Amazon operations
        """)
    
    return app


# =============================================================================
# PHẦN 11: ENTRY POINT (CHẠY APP)
# =============================================================================

if __name__ == "__main__":
    # Banner khởi động
    print("=" * 60)
    print("🚀 Multi-Source Deal Finder v4 - Starting up...")
    print("   Sources: BestBuy + Amazon")
    print("   Refactored modular version")
    print("=" * 60)
    
    # Khởi tạo tất cả agents (mất 5-10 giây)
    init_agents()
    
    # Tạo Gradio app
    app = create_gradio_app()
    
    print("\n" + "=" * 60)
    print("✅ Ready! Opening browser...")
    print("=" * 60 + "\n")
    
    # Launch app (tự động mở browser)
    app.launch(share=False, inbrowser=True)
