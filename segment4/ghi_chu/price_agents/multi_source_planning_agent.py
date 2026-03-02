"""
=============================================================================
MULTI-SOURCE PLANNING AGENT - PIPELINE LOGIC 6 BƯỚC
=============================================================================
File: price_agents/multi_source_planning_agent.py

MỤC ĐÍCH:
- Đây là file chứa TOÀN BỘ LOGIC của pipeline tìm kiếm deals
- Pattern theo: planning_agent.py
- Điều phối 6 bước từ search → estimate prices

PIPELINE 6 BƯỚC:
    Step 1: Search BestBuy + Amazon (parallel)
    Step 2: Filter sale items
    Step 3: Scrape product details (Playwright)
    Step 4: Combine into unified pool
    Step 5: Select top 5 deals (GPT-5-mini)
    Step 6: Estimate prices (EnsembleAgent 3 models)

KIẾN TRÚC:
    MultiSourceFramework
        ↓ gọi plan()
    MultiSourcePlanningAgent (file này)
        ├── EnsembleAgent          (dự đoán giá)
        ├── MessagingAgent         (push notification)
        ├── ClarificationAgent     (sinh câu hỏi)
        ├── MultiSourceScannerAgent (chọn top 5)
        ├── BestBuySearchAgent     (tìm URLs BestBuy)
        └── AmazonSearchAgent      (tìm URLs Amazon)

TẠI SAO CẦN FILE NÀY?
- Tách logic ra khỏi UI (search_key.py chỉ chứa UI)
- Dễ test pipeline độc lập
- Single Responsibility: 1 file = 1 trách nhiệm

Author: Refactored from bestbuy4.py
Date: 2026-02-07
=============================================================================
"""

import asyncio
import logging
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor  # Để chạy parallel

from price_agents.agent import Agent
from price_agents.deals import Deal, DealSelection, Opportunity
from price_agents.ensemble_agent import EnsembleAgent
from price_agents.messaging_agent import MessagingAgent

# ============================================================================
# BESTBUY IMPORTS
# ============================================================================
from price_agents.bestbuy_deals import (
    ScrapedBestBuyDeal,       # Data class cho BestBuy product
    filter_sale_urls,         # BeautifulSoup filter sale items
    scrape_bestbuy_products   # Playwright scrape details
)
from price_agents.bestbuy_scanner_agent import BestBuySearchAgent  # Brave MCP search

# ============================================================================
# AMAZON IMPORTS
# ============================================================================
from price_agents.amazon_deals import (
    ScrapedAmazonDeal,                  # Data class cho Amazon product
    filter_amazon_sale_urls_playwright,  # Playwright filter (Amazon chặn BeautifulSoup)
    scrape_amazon_products              # Playwright scrape details
)
from price_agents.amazon_scanner_agent import AmazonSearchAgent  # Brave MCP search

# ============================================================================
# REFACTORED MODULES
# ============================================================================
from bestbuy_untils.clarification_agent import (
    ClarificationAgent,       # Agent sinh câu hỏi làm rõ
    ClarificationQuestion,    # 1 câu hỏi
    ClarificationResponse,    # Response chứa 3 câu hỏi
    RefinedQuery              # Query sau khi refined
)
from bestbuy_untils.unified_deal import UnifiedScrapedDeal  # Gộp deals từ 2 nguồn
from bestbuy_untils.multi_source_scanner_agent import MultiSourceScannerAgent  # Chọn top 5


class MultiSourcePlanningAgent(Agent):
    """
    Planning Agent điều phối pipeline 6 bước tìm deals từ BestBuy + Amazon.
    
    Kế thừa từ Agent để có:
    - self.log(): Log với màu sắc
    - name, color attributes
    
    Sub-agents được khởi tạo:
    - ensemble: EnsembleAgent (3 models dự đoán giá)
    - messenger: MessagingAgent (push notification)
    - clarification: ClarificationAgent (sinh câu hỏi)
    - multi_scanner: MultiSourceScannerAgent (chọn top 5)
    
    Main Method:
    - plan(): Chạy pipeline 6 bước
    - plan_with_answers(): Refined query + plan()
    
    Attributes:
        DEAL_THRESHOLD: Ngưỡng discount để auto-notify (default $100)
    """

    name = "Multi-Source Planning Agent"
    color = Agent.GREEN
    
    # Nếu discount > threshold → tự động gửi push notification
    DEAL_THRESHOLD = 100

    def __init__(self, collection):
        """
        Khởi tạo tất cả sub-agents.
        
        Args:
            collection: ChromaDB collection cho FrontierAgent (RAG search)
        """
        self.log("Đang khởi tạo Multi-Source Planning Agent")
        
        # EnsembleAgent: Dự đoán giá bằng 3 models
        # - FrontierAgent (80%): GPT-5.1 + RAG với ChromaDB
        # - SpecialistAgent (10%): Fine-tuned Llama-3.2-3B
        # - NeuralNetworkAgent (10%): PyTorch DNN
        self.ensemble = EnsembleAgent(collection)
        
        # MessagingAgent: Gửi push notification qua Pushover
        self.messenger = MessagingAgent()
        
        # ClarificationAgent: Sinh 3 câu hỏi làm rõ nhu cầu
        self.clarification = ClarificationAgent()
        
        # MultiSourceScannerAgent: GPT-5-mini chọn top 5 từ pool
        self.multi_scanner = MultiSourceScannerAgent()
        
        self.log("Multi-Source Planning Agent đã sẵn sàng")

    # =========================================================================
    # CLARIFICATION METHODS - SINH CÂU HỎI LÀM RÕ
    # =========================================================================

    def generate_questions(self, keyword: str) -> ClarificationResponse:
        """
        Sinh 3 câu hỏi làm rõ cho keyword.
        
        VD: keyword = "laptop"
        → Questions:
           1. "Bạn dùng laptop cho mục đích gì?" (gaming, work, study)
           2. "Ngân sách của bạn là bao nhiêu?"
           3. "Bạn thích kích thước màn hình nào?"
        
        Args:
            keyword: Từ khóa người dùng nhập
            
        Returns:
            ClarificationResponse với 3 câu hỏi
        """
        self.log(f"Đang sinh câu hỏi làm rõ cho: {keyword}")
        return self.clarification.generate_questions(keyword)

    def build_refined_query(
        self,
        keyword: str,
        questions: List[ClarificationQuestion],
        answers: List[str]
    ) -> RefinedQuery:
        """
        Xây dựng query refined từ câu trả lời.
        
        VD:
        - keyword = "laptop"
        - answers = ["gaming", "under $1000", "15 inch"]
        → refined_query = "gaming laptops 15 inch screen under $1000"
        
        Args:
            keyword: Từ khóa gốc
            questions: 3 câu hỏi
            answers: 3 câu trả lời
            
        Returns:
            RefinedQuery với query mới
        """
        self.log("Đang xây dựng refined query từ câu trả lời")
        return self.clarification.build_refined_query(keyword, questions, answers)

    # =========================================================================
    # PIPELINE STEP 1: SEARCH - TÌM KIẾM URLS
    # =========================================================================

    def _search_bestbuy(self, keyword: str, max_urls: int) -> List[str]:
        """
        Tìm kiếm URLs sản phẩm trên BestBuy.
        
        Sử dụng BestBuySearchAgent với Brave MCP để search.
        
        Flow:
        1. BestBuySearchAgent gọi Brave Search API
        2. Filter URLs thuộc domain bestbuy.com
        3. Trả về list URLs (max = max_urls)
        
        Args:
            keyword: Từ khóa tìm kiếm
            max_urls: Số URLs tối đa
            
        Returns:
            List URLs BestBuy
        """
        search_agent = BestBuySearchAgent()
        return search_agent.search(keyword, max_urls=max_urls)

    def _search_amazon(self, keyword: str, max_urls: int) -> List[str]:
        """
        Tìm kiếm URLs sản phẩm trên Amazon.
        
        Sử dụng AmazonSearchAgent với Brave MCP để search.
        
        Lưu ý: Amazon có nhiều domains
        - www.amazon.com
        - us.amazon.com
        
        Args:
            keyword: Từ khóa tìm kiếm
            max_urls: Số URLs tối đa
            
        Returns:
            List URLs Amazon
        """
        search_agent = AmazonSearchAgent()
        return search_agent.search(keyword, max_urls=max_urls)

    def search_both_sources(
        self, keyword: str, max_urls: int = 10
    ) -> Tuple[List[str], List[str]]:
        """
        STEP 1: Tìm kiếm trên CẢ BestBuy và Amazon ĐỒNG THỜI.
        
        PARALLEL EXECUTION với ThreadPoolExecutor:
        - 2 workers chạy song song
        - BestBuy và Amazon search cùng lúc
        - Tiết kiệm ~50% thời gian so với sequential
        
        Flow:
            ThreadPoolExecutor(max_workers=2)
                ├── Thread 1: _search_bestbuy()
                └── Thread 2: _search_amazon()
            → Collect results
        
        Args:
            keyword: Từ khóa tìm kiếm
            max_urls: Số URLs tối đa MỖI nguồn (tổng = max_urls * 2)
            
        Returns:
            Tuple (bestbuy_urls, amazon_urls)
        """
        self.log(f"[Step 1/6] Đang tìm '{keyword}' trên BestBuy + Amazon...")

        bestbuy_urls = []
        amazon_urls = []

        # Chạy 2 search song song
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit 2 tasks
            future_bb = executor.submit(self._search_bestbuy, keyword, max_urls)
            future_az = executor.submit(self._search_amazon, keyword, max_urls)

            # Chờ kết quả (timeout 120s)
            bestbuy_urls = future_bb.result(timeout=120)
            self.log(f"  BestBuy: Tìm thấy {len(bestbuy_urls)} URLs")

            amazon_urls = future_az.result(timeout=120)
            self.log(f"  Amazon: Tìm thấy {len(amazon_urls)} URLs")

        self.log(f"Tổng: {len(bestbuy_urls)} (BestBuy) + {len(amazon_urls)} (Amazon)")
        return bestbuy_urls, amazon_urls

    # =========================================================================
    # PIPELINE STEP 2: FILTER SALES - LỌC SẢN PHẨM ĐANG SALE
    # =========================================================================

    def _get_event_loop(self):
        """
        Lấy hoặc tạo event loop cho async operations.
        
        Tại sao cần?
        - Playwright functions là async
        - Gradio chạy trong sync context
        - Cần bridge sync → async với run_until_complete()
        
        Returns:
            asyncio event loop
        """
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            # Nếu không có loop → tạo mới
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def filter_sales(
        self, bestbuy_urls: List[str], amazon_urls: List[str]
    ) -> Tuple[List[str], List[Tuple[str, dict]]]:
        """
        STEP 2: Lọc URLs chỉ giữ sản phẩm đang SALE.
        
        KHÁC NHAU GIỮA 2 NGUỒN:
        
        BestBuy:
        - Dùng BeautifulSoup (nhanh, ~0.5s/URL)
        - Kiểm tra HTML static
        - Tìm class "savings-regular" hoặc "price-reduced"
        
        Amazon:
        - Dùng Playwright (chậm, ~2s/URL)
        - Amazon chặn requests thường → cần browser
        - Kiểm tra presence của "savings" element
        
        Args:
            bestbuy_urls: List URLs BestBuy
            amazon_urls: List URLs Amazon
            
        Returns:
            Tuple:
            - bestbuy_sales: List[str] URLs đang sale
            - amazon_sales: List[Tuple[url, price_data]] URLs đang sale + giá
        """
        self.log("[Step 2/6] Đang lọc sản phẩm đang sale...")

        # BESTBUY: BeautifulSoup filter (nhanh)
        bestbuy_sales = []
        if bestbuy_urls:
            self.log(f"  Lọc {len(bestbuy_urls)} URLs BestBuy (BeautifulSoup)...")
            bestbuy_sales = filter_sale_urls(bestbuy_urls)
            self.log(f"  BestBuy: {len(bestbuy_sales)} sản phẩm đang sale")

        # AMAZON: Playwright filter (bắt buộc dùng browser)
        amazon_sales = []
        if amazon_urls:
            self.log(f"  Lọc {len(amazon_urls)} URLs Amazon (Playwright)...")
            loop = self._get_event_loop()
            amazon_sales = loop.run_until_complete(
                filter_amazon_sale_urls_playwright(amazon_urls, headless=False)
            )
            self.log(f"  Amazon: {len(amazon_sales)} sản phẩm đang sale")

        return bestbuy_sales, amazon_sales

    # =========================================================================
    # PIPELINE STEP 3 & 4: SCRAPE AND COMBINE
    # =========================================================================

    def scrape_and_combine(
        self,
        bestbuy_urls: List[str],
        amazon_items: List[Tuple[str, dict]]
    ) -> List[UnifiedScrapedDeal]:
        """
        STEP 3 & 4: Scrape chi tiết sản phẩm và gộp vào pool chung.
        
        STEP 3: SCRAPE với Playwright
        - Mở browser (headless=False để tránh bị chặn)
        - Trích xuất: title, brand, price, features
        - BestBuy: Click nút "Features" để lấy sidebar
        - Amazon: Trích xuất từ product page
        
        STEP 4: COMBINE vào pool chung
        - Convert ScrapedBestBuyDeal → UnifiedScrapedDeal
        - Convert ScrapedAmazonDeal → UnifiedScrapedDeal
        - Unified format để GPT dễ so sánh
        
        Args:
            bestbuy_urls: List URLs BestBuy đang sale
            amazon_items: List (url, price_data) Amazon đang sale
            
        Returns:
            List[UnifiedScrapedDeal] - Pool chung để chọn top 5
        """
        self.log("[Step 3/6] Đang scrape chi tiết sản phẩm (Playwright)...")

        loop = self._get_event_loop()
        bestbuy_scraped = []
        amazon_scraped = []

        # SCRAPE BESTBUY
        if bestbuy_urls:
            self.log(f"  Scraping {len(bestbuy_urls)} sản phẩm BestBuy...")
            bestbuy_scraped = loop.run_until_complete(
                scrape_bestbuy_products(bestbuy_urls, headless=False)
            )
            self.log(f"  BestBuy: Đã scrape {len(bestbuy_scraped)} sản phẩm")

        # SCRAPE AMAZON
        if amazon_items:
            self.log(f"  Scraping {len(amazon_items)} sản phẩm Amazon...")
            amazon_scraped = loop.run_until_complete(
                scrape_amazon_products(amazon_items, headless=False)
            )
            self.log(f"  Amazon: Đã scrape {len(amazon_scraped)} sản phẩm")

        # STEP 4: COMBINE vào pool chung
        self.log("[Step 4/6] Đang gộp sản phẩm từ cả 2 nguồn...")
        unified_deals = []
        
        # Convert BestBuy → Unified
        for deal in bestbuy_scraped:
            unified_deals.append(UnifiedScrapedDeal.from_bestbuy(deal))
        
        # Convert Amazon → Unified
        for deal in amazon_scraped:
            unified_deals.append(UnifiedScrapedDeal.from_amazon(deal))

        self.log(f"Pool tổng hợp: {len(unified_deals)} sản phẩm")
        return unified_deals

    # =========================================================================
    # PIPELINE STEP 5: SELECT TOP DEALS
    # =========================================================================

    def select_top_deals(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """
        STEP 5: Dùng GPT-5-mini chọn top 5 deals từ pool.
        
        Tại sao dùng GPT?
        - Pool có thể có 10-30 sản phẩm
        - GPT đánh giá chất lượng mô tả
        - Chọn deals có thông tin đầy đủ nhất
        
        Delegate xuống MultiSourceScannerAgent.scan()
        
        Args:
            unified_deals: Pool tổng hợp từ cả 2 nguồn
            
        Returns:
            DealSelection với tối đa 5 deals
        """
        self.log("[Step 5/6] GPT đang chọn top 5 từ pool tổng hợp...")
        selection = self.multi_scanner.scan(unified_deals)

        if selection and selection.deals:
            self.log(f"Đã chọn {len(selection.deals)} deals tốt nhất")
        return selection

    # =========================================================================
    # PIPELINE STEP 6: ESTIMATE PRICES
    # =========================================================================

    def estimate_prices(self, deal_selection: DealSelection) -> List[Opportunity]:
        """
        STEP 6: Ước lượng giá trị thực bằng EnsembleAgent.
        
        ENSEMBLE 3 MODELS:
        - FrontierAgent (80%): GPT-5.1 + RAG với ChromaDB 400K products
        - SpecialistAgent (10%): Fine-tuned Llama-3.2-3B trên Modal
        - NeuralNetworkAgent (10%): PyTorch DNN local
        
        Formula:
            estimate = frontier * 0.8 + specialist * 0.1 + neural * 0.1
            discount = estimate - sale_price
        
        Args:
            deal_selection: Top 5 deals từ Step 5
            
        Returns:
            List[Opportunity] sorted by discount (cao nhất đầu tiên)
            
        Opportunity schema:
            deal: Deal (product_description, price, url)
            estimate: float (giá ước lượng)
            discount: float (chênh lệch)
        """
        self.log("[Step 6/6] Ước lượng giá với EnsembleAgent (3 models)...")

        opportunities = []
        for deal in deal_selection.deals:
            # Gọi EnsembleAgent.price() cho mỗi deal
            estimate = self.ensemble.price(deal.product_description)
            
            # Tính discount = estimate - sale_price
            discount = estimate - deal.price
            
            opportunity = Opportunity(deal=deal, estimate=estimate, discount=discount)
            opportunities.append(opportunity)

        # Sort theo discount (cao nhất đầu tiên = deal tốt nhất)
        opportunities.sort(key=lambda x: x.discount, reverse=True)
        self.log(f"Đã ước lượng {len(opportunities)} cơ hội")

        # Log best deal
        if opportunities:
            best = opportunities[0]
            self.log(f"DEAL TỐT NHẤT: ${best.deal.price:.2f} → Est: ${best.estimate:.2f} = Discount ${best.discount:.2f}")

        return opportunities

    # =========================================================================
    # MAIN PIPELINE - HÀM CHÍNH
    # =========================================================================

    def plan(self, keyword: str, max_urls: int = 10) -> List[Opportunity]:
        """
        CHẠY PIPELINE ĐẦY ĐỦ 6 BƯỚC.
        
        ĐÂY LÀ HÀM QUAN TRỌNG NHẤT!
        
        Flow:
            Step 1: search_both_sources()  → BestBuy + Amazon URLs
            Step 2: filter_sales()         → Chỉ giữ sản phẩm đang sale
            Step 3: scrape_and_combine()   → Scrape chi tiết
            Step 4: (trong step 3)         → Gộp vào pool chung
            Step 5: select_top_deals()     → GPT chọn top 5
            Step 6: estimate_prices()      → EnsembleAgent ước lượng
        
        AUTO-NOTIFY:
        - Nếu best deal có discount > DEAL_THRESHOLD ($100)
        - Tự động gửi push notification qua MessagingAgent
        
        Args:
            keyword: Từ khóa tìm kiếm (gốc hoặc refined)
            max_urls: Số URLs tối đa mỗi nguồn
            
        Returns:
            List[Opportunity] sorted by discount (cao nhất đầu tiên)
        """
        self.log(f"Bắt đầu pipeline cho: '{keyword}' (max {max_urls} URLs/nguồn)")

        # ===================== STEP 1: SEARCH =====================
        bb_urls, az_urls = self.search_both_sources(keyword, max_urls)
        if not bb_urls and not az_urls:
            self.log("Không tìm thấy sản phẩm. Thử keyword khác.")
            return []

        # ===================== STEP 2: FILTER =====================
        bb_sales, az_sales = self.filter_sales(bb_urls, az_urls)
        if not bb_sales and not az_sales:
            self.log("Không có sản phẩm đang sale. Thử keyword khác.")
            return []

        # ===================== STEP 3 & 4: SCRAPE AND COMBINE =====================
        unified_deals = self.scrape_and_combine(bb_sales, az_sales)
        if not unified_deals:
            self.log("Không thể scrape chi tiết sản phẩm.")
            return []

        # ===================== STEP 5: SELECT TOP 5 =====================
        deal_selection = self.select_top_deals(unified_deals)
        if not deal_selection or not deal_selection.deals:
            self.log("Không thể chọn deals.")
            return []

        # ===================== STEP 6: ESTIMATE PRICES =====================
        opportunities = self.estimate_prices(deal_selection)

        # ===================== AUTO-NOTIFY =====================
        # Nếu discount > $100 → gửi push notification tự động
        if opportunities and opportunities[0].discount > self.DEAL_THRESHOLD:
            best = opportunities[0]
            self.log(f"Auto-notify: Discount ${best.discount:.2f} > ngưỡng ${self.DEAL_THRESHOLD}")
            self.messenger.notify(
                description=best.deal.product_description[:200],
                deal_price=best.deal.price,
                estimated_true_value=best.estimate,
                url=best.deal.url
            )

        self.log("Pipeline hoàn tất thành công!")
        return opportunities

    def plan_with_answers(
        self,
        keyword: str,
        questions: List[ClarificationQuestion],
        answers: List[str],
        max_urls: int = 10
    ) -> List[Opportunity]:
        """
        Chạy pipeline với câu trả lời clarification.
        
        Flow:
        1. build_refined_query() → Tạo query tốt hơn từ answers
        2. plan() → Chạy pipeline với refined query
        
        VD:
        - keyword = "laptop", answers = ["gaming", "$800", "15 inch"]
        - refined = "gaming laptops 15 inch under $800"
        - plan("gaming laptops 15 inch under $800")
        
        Args:
            keyword: Từ khóa gốc
            questions: 3 câu hỏi
            answers: 3 câu trả lời
            max_urls: Số URLs tối đa mỗi nguồn
            
        Returns:
            List[Opportunity] sorted by discount
        """
        refined = self.build_refined_query(keyword, questions, answers)
        self.log(f"Refined query: '{keyword}' → '{refined.query}'")
        return self.plan(refined.query, max_urls)
