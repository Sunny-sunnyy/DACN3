"""
=============================================================================
MULTI-SOURCE FRAMEWORK - BỘ ĐIỀU PHỐI TRUNG TÂM
=============================================================================
File: multi_source_framework.py

MỤC ĐÍCH:
- Đây là "Framework" hay "Orchestrator" - điều phối toàn bộ hệ thống
- Pattern theo: deal_agent_framework.py
- Là cầu nối giữa UI (search_key.py) và Logic (MultiSourcePlanningAgent)

TRÁCH NHIỆM:
1. Khởi tạo ChromaDB (vector database 400K sản phẩm)
2. Lazy initialization của agents (chỉ init khi cần)
3. Cung cấp high-level methods cho Gradio UI gọi
4. Quản lý state (current_opportunities)

KIẾN TRÚC:
    Gradio UI (search_key.py)
        ↓ gọi
    MultiSourceFramework (file này)
        ↓ delegate tới
    MultiSourcePlanningAgent (pipeline logic)
        ↓ sử dụng
    Các agents (EnsembleAgent, ClarificationAgent, etc.)

TẠI SAO CẦN FRAMEWORK?
- Tách biệt UI và business logic
- Quản lý resources (ChromaDB) tập trung
- Lazy loading để startup nhanh
- Dễ test và maintain

Author: Refactored from bestbuy4.py
Date: 2026-02-07
=============================================================================
"""

import logging
from typing import List, Optional

import chromadb
from dotenv import load_dotenv

# Import planning agent - chứa pipeline logic 6 bước
from price_agents.multi_source_planning_agent import MultiSourcePlanningAgent

# Import data types
from price_agents.deals import Opportunity
from bestbuy_untils.clarification_agent import (
    ClarificationQuestion,
    ClarificationResponse
)

# ============================================================================
# ANSI COLOR CODES CHO LOGGING
# ============================================================================
# Giúp logs dễ đọc hơn trong terminal
BG_CYAN = '\033[46m'   # Background màu cyan
WHITE = '\033[37m'     # Text màu trắng  
RESET = '\033[0m'      # Reset về mặc định


def init_logging():
    """
    Khởi tạo logging configuration.
    
    Set level = INFO để capture logs từ tất cả agents.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)


# =============================================================================
# MULTI-SOURCE FRAMEWORK CLASS
# =============================================================================

class MultiSourceFramework:
    """
    Framework orchestrator cho Multi-Source deal finding.
    
    Pattern theo DealAgentFramework trong deal_agent_framework.py.
    
    Lifecycle:
    1. __init__(): Load .env, init ChromaDB
    2. init_agents_as_needed(): Lazy init planning agent khi cần
    3. run() hoặc run_with_answers(): Chạy pipeline
    4. send_notification(): Gửi push notification
    
    Attributes:
        DB: Đường dẫn tới ChromaDB folder
        collection: ChromaDB collection chứa 400K products
        planner: MultiSourcePlanningAgent instance (lazy)
        current_opportunities: Kết quả tìm kiếm gần nhất
    """

    # Đường dẫn tới ChromaDB - vector store với 400K sản phẩm đã embed
    DB = "products_vectorstore"

    def __init__(self):
        """
        Khởi tạo framework.
        
        Flow:
        1. Load biến môi trường từ .env
        2. Setup logging
        3. Kết nối ChromaDB và get collection
        4. Khởi tạo state variables
        
        ChromaDB:
        - PersistentClient: Lưu data trên disk
        - Collection 'products': Chứa 400K products đã embed
        - Được sử dụng bởi FrontierAgent cho RAG search
        """
        # Load .env file (chứa API keys)
        load_dotenv(override=True)
        init_logging()

        self.log("Đang khởi tạo Multi-Source Framework")
        
        # Kết nối ChromaDB
        # PersistentClient: Data được lưu trên disk, không mất khi restart
        client = chromadb.PersistentClient(path=self.DB)
        
        # Get hoặc create collection 'products'
        self.collection = client.get_or_create_collection('products')
        self.log(f"ChromaDB collection: {self.collection.name}, số lượng: {self.collection.count()}")

        # State variables
        self.planner: Optional[MultiSourcePlanningAgent] = None  # Lazy init
        self.current_opportunities: List[Opportunity] = []        # Kết quả gần nhất
        
        self.log("Multi-Source Framework đã sẵn sàng")

    def log(self, message: str):
        """
        Log message với identifier của framework.
        
        Format: [Multi-Source Framework] message
        Màu: Background cyan, text trắng
        
        Args:
            message: Nội dung cần log
        """
        text = BG_CYAN + WHITE + "[Multi-Source Framework] " + message + RESET
        logging.info(text)

    def init_agents_as_needed(self):
        """
        Lazy initialization của planning agent.
        
        TẠI SAO LAZY INIT?
        - MultiSourcePlanningAgent init mất ~5-10s vì cần load:
          - EnsembleAgent (3 models)
          - MessagingAgent
          - ClarificationAgent
          - MultiSourceScannerAgent
        - Nếu init ngay từ đầu → App startup chậm
        - Lazy init: Chỉ init khi user thực sự cần (click button)
        
        Pattern:
            if not self.planner:   # Chưa có?
                self.planner = ...  # Tạo mới
        """
        if not self.planner:
            self.log("Đang khởi tạo Multi-Source Planning Agent...")
            # Truyền collection vào để FrontierAgent dùng cho RAG
            self.planner = MultiSourcePlanningAgent(self.collection)
            self.log("Planning Agent đã khởi tạo thành công")

    # =========================================================================
    # CLARIFICATION METHODS - SINH CÂU HỎI LÀM RÕ
    # =========================================================================

    def generate_questions(self, keyword: str) -> ClarificationResponse:
        """
        Sinh câu hỏi làm rõ cho keyword.
        
        Delegate xuống ClarificationAgent thông qua planner.
        
        Args:
            keyword: Từ khóa người dùng nhập (VD: "laptop")
            
        Returns:
            ClarificationResponse chứa:
            - product_category: Danh mục sản phẩm (VD: "Laptops")
            - questions: List 3 ClarificationQuestion
        """
        self.init_agents_as_needed()  # Đảm bảo agent đã init
        return self.planner.generate_questions(keyword)

    # =========================================================================
    # PIPELINE METHODS - CHẠY PIPELINE TÌM KIẾM
    # =========================================================================

    def run(self, keyword: str, max_urls: int = 10) -> List[Opportunity]:
        """
        Chạy pipeline đầy đủ với keyword gốc (chế độ Skip).
        
        Đây là method được gọi khi user click "Skip, Search Now".
        
        Pipeline 6 bước:
        1. Search BestBuy + Amazon (parallel)
        2. Filter sale items
        3. Scrape product details
        4. Combine into unified pool
        5. Select top 5 deals
        6. Estimate prices
        
        Args:
            keyword: Từ khóa tìm kiếm gốc
            max_urls: Số URLs tối đa mỗi nguồn (default 10)
            
        Returns:
            List[Opportunity] sorted by discount (cao nhất đầu tiên)
        """
        self.init_agents_as_needed()
        self.log(f"Chạy pipeline: '{keyword}' (max {max_urls} URLs/nguồn)")
        
        # Delegate xuống planner
        opportunities = self.planner.plan(keyword, max_urls)
        
        # Lưu kết quả vào state để dùng cho notification
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
        Chạy pipeline với câu trả lời clarification.
        
        Đây là method được gọi khi user click "Submit & Search".
        
        Flow:
        1. Build refined query từ keyword + answers
           VD: "laptop" + ["gaming", "under $800", "15 inch"]
               → "gaming laptops 15 inch under $800"
        2. Chạy pipeline với refined query
        
        Args:
            keyword: Từ khóa gốc
            questions: List câu hỏi đã sinh trước đó
            answers: List câu trả lời của user
            max_urls: Số URLs tối đa mỗi nguồn
            
        Returns:
            List[Opportunity] sorted by discount
        """
        self.init_agents_as_needed()
        self.log(f"Chạy pipeline với clarification: '{keyword}'")
        
        # Delegate xuống planner
        opportunities = self.planner.plan_with_answers(keyword, questions, answers, max_urls)
        
        # Lưu kết quả
        self.current_opportunities = opportunities
        
        return opportunities

    # =========================================================================
    # NOTIFICATION - GỬI PUSH NOTIFICATION
    # =========================================================================

    def send_notification(self, index: int = 0) -> str:
        """
        Gửi push notification cho deal tại index chỉ định.
        
        Sử dụng Pushover API để gửi notification tới điện thoại.
        
        Args:
            index: Vị trí deal trong current_opportunities
                   0 = best deal (discount cao nhất)
            
        Returns:
            Status message ("Sent!" hoặc error message)
            
        Lưu ý:
        - Cần có PUSHOVER_USER và PUSHOVER_TOKEN trong .env
        - Phải search trước mới có current_opportunities
        """
        # Validate: Có kết quả chưa?
        if not self.current_opportunities:
            return "Chưa có deals. Hãy tìm kiếm trước!"

        # Validate: Index hợp lệ?
        if index < 0 or index >= len(self.current_opportunities):
            return f"Index không hợp lệ. Chọn 0-{len(self.current_opportunities) - 1}"

        # Lấy opportunity tại index
        opp = self.current_opportunities[index]
        self.init_agents_as_needed()

        # Gọi MessagingAgent thông qua planner
        self.planner.messenger.notify(
            description=opp.deal.product_description[:200],  # Cắt 200 ký tự
            deal_price=opp.deal.price,
            estimated_true_value=opp.estimate,
            url=opp.deal.url
        )

        return f"Đã gửi! Deal #{index}: {opp.deal.product_description[:40]}... (${opp.deal.price:.2f})"


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    # Test khởi tạo framework
    framework = MultiSourceFramework()
    print("Framework đã khởi tạo thành công!")
    print(f"ChromaDB collection count: {framework.collection.count()}")
