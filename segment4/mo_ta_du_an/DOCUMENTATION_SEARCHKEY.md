# 🔍 SEARCH_KEY.PY - MULTI-SOURCE DEAL FINDER

## 📌 Tổng quan dự án

**Tên dự án:** Multi-Source Deal Finder (search_key.py)  
**Phiên bản:** v5.0 (Refactored)  
**Ngày cập nhật:** 2026-02-07  
**Ngôn ngữ:** Python 3.10+

### Mục tiêu dự án

Dự án này là một ứng dụng web giúp người dùng **tìm kiếm và đánh giá deals tốt nhất** từ **hai marketplace lớn nhất**: **BestBuy** và **Amazon**. Ứng dụng sử dụng AI để:

1. **Tìm kiếm song song** trên cả BestBuy và Amazon
2. **Lọc sản phẩm đang sale** (có giảm giá)
3. **Trích xuất thông tin chi tiết** (tên, giá, features)
4. **Chọn top 5 deals tốt nhất** bằng GPT-5-mini
5. **Ước lượng giá trị thực** bằng Ensemble AI (3 models)
6. **Thông báo tự động** qua Push Notification nếu có deal tốt

---

## 🎯 Đầu vào và Đầu ra

### Đầu vào (Input)

| Input | Mô tả | Ví dụ |
|-------|-------|-------|
| **Keyword** | Từ khóa sản phẩm cần tìm | "laptop", "Smart TV", "headphones" |
| **Câu trả lời** (tùy chọn) | Trả lời 3 câu hỏi làm rõ nhu cầu | "gaming", "under $1000", "15 inch" |
| **Max URLs** | Số URLs tối đa mỗi nguồn | 5-20 (mặc định: 10) |

### Đầu ra (Output)

| Output | Mô tả |
|--------|-------|
| **Bảng kết quả** | Top 5 deals với: Tên sản phẩm, Giá sale, Giá ước lượng, Discount ($), Discount (%), URL |
| **Pipeline logs** | Real-time logs hiển thị tiến trình từng bước |
| **Push Notification** | Thông báo đến điện thoại qua Pushover (tùy chọn) |

### Ví dụ cụ thể

**Input:**
```
Keyword: "laptop"
Answers: ["gaming", "under $1000", "15 inch"]
Max URLs: 10
```

**Output:**
| Product | Sale $ | Estimate $ | Discount $ | Discount % |
|---------|--------|------------|------------|------------|
| [Amazon] Dell Gaming Laptop 15.6" RTX 3050... | $519.99 | $822.54 | $302.55 | 37% 🔥 |
| [BestBuy] Acer Aspire 15" Intel i7... | $429.99 | $747.14 | $317.15 | 42% 🔥 |
| [BestBuy] HP Pavilion 15"... | $389.99 | $658.06 | $268.07 | 41% 🔥 |

---

## 🔄 Workflow - Luồng hoạt động

### Sơ đồ tổng quan

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           WORKFLOW TỔNG QUAN                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  [User]                                                                       │
│     │                                                                         │
│     ▼                                                                         │
│  ╔══════════════════════════════════════╗                                    │
│  ║  1. NHẬP KEYWORD                      ║                                    │
│  ║     VD: "laptop"                      ║                                    │
│  ╚══════════════════════════════════════╝                                    │
│     │                                                                         │
│     ▼                                                                         │
│  ╔══════════════════════════════════════╗                                    │
│  ║  2. SINH CÂU HỎI LÀM RÕ              ║  ← ClarificationAgent (GPT-5-nano) │
│  ║     - Mục đích sử dụng?              ║                                    │
│  ║     - Ngân sách?                      ║                                    │
│  ║     - Kích thước màn hình?           ║                                    │
│  ╚══════════════════════════════════════╝                                    │
│     │                                                                         │
│     ├───────────────┬───────────────────┐                                    │
│     ▼               ▼                   │                                    │
│  [TRẢ LỜI]      [BỎ QUA]               │                                    │
│     │               │                   │                                    │
│     ▼               ▼                   │                                    │
│  [Refined Query]  [Original Query]     │                                    │
│     │               │                   │                                    │
│     └───────┬───────┘                   │                                    │
│             ▼                           │                                    │
│  ╔══════════════════════════════════════════════════════════════════════╗   │
│  ║  3. PIPELINE 6 BƯỚC                                                    ║   │
│  ║  ┌──────────────────────────────────────────────────────────────────┐ ║   │
│  ║  │ Step 1: Search BestBuy + Amazon (PARALLEL)                       │ ║   │
│  ║  │        ├── BestBuySearchAgent (Brave MCP) → 10 URLs              │ ║   │
│  ║  │        └── AmazonSearchAgent (Brave MCP)  → 10 URLs              │ ║   │
│  ║  ├──────────────────────────────────────────────────────────────────┤ ║   │
│  ║  │ Step 2: Filter Sale Items                                        │ ║   │
│  ║  │        ├── BestBuy: BeautifulSoup (nhanh)                        │ ║   │
│  ║  │        └── Amazon: Playwright (chống bot)                        │ ║   │
│  ║  ├──────────────────────────────────────────────────────────────────┤ ║   │
│  ║  │ Step 3: Scrape Product Details (Playwright)                      │ ║   │
│  ║  │        → Title, Brand, Price, Features                           │ ║   │
│  ║  ├──────────────────────────────────────────────────────────────────┤ ║   │
│  ║  │ Step 4: Combine into Unified Pool                                │ ║   │
│  ║  │        → UnifiedScrapedDeal (chuẩn hóa format)                   │ ║   │
│  ║  ├──────────────────────────────────────────────────────────────────┤ ║   │
│  ║  │ Step 5: Select Top 5 Deals                                       │ ║   │
│  ║  │        → MultiSourceScannerAgent (GPT-5-mini)                    │ ║   │
│  ║  ├──────────────────────────────────────────────────────────────────┤ ║   │
│  ║  │ Step 6: Estimate Prices                                          │ ║   │
│  ║  │        → EnsembleAgent (80% Frontier + 10% Specialist + 10% NN)  │ ║   │
│  ║  └──────────────────────────────────────────────────────────────────┘ ║   │
│  ╚══════════════════════════════════════════════════════════════════════╝   │
│             │                                                                 │
│             ▼                                                                 │
│  ╔══════════════════════════════════════╗                                    │
│  ║  4. HIỂN THỊ KẾT QUẢ                  ║                                    │
│  ║     - Bảng deals (sorted by discount)║                                    │
│  ║     - Real-time logs                  ║                                    │
│  ╚══════════════════════════════════════╝                                    │
│             │                                                                 │
│             ▼                                                                 │
│  ╔══════════════════════════════════════╗                                    │
│  ║  5. AUTO-NOTIFY (nếu discount > $100)║  ← MessagingAgent (Pushover)       │
│  ╚══════════════════════════════════════╝                                    │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu trúc thư mục và Files

### Sơ đồ thư mục

```
segment4/
│
├── search_key.py                        # 🎯 ENTRY POINT - Gradio UI
├── multi_source_framework.py            # 📦 FRAMEWORK - Điều phối trung tâm
│
├── price_agents/                        # 🤖 THƯ MỤC CHỨA TẤT CẢ AGENTS
│   ├── __init__.py
│   ├── agent.py                         # Base class cho tất cả agents
│   ├── deals.py                         # Data classes (Deal, Opportunity)
│   ├── preprocessor.py                  # Làm sạch text trước khi estimate
│   │
│   ├── multi_source_planning_agent.py   # 🎯 CORE - Pipeline 6 bước
│   ├── ensemble_agent.py                # Kết hợp 3 models dự đoán giá
│   ├── messaging_agent.py               # Gửi push notification
│   │
│   ├── bestbuy_deals.py                 # Scraping functions cho BestBuy
│   ├── bestbuy_scanner_agent.py         # Search + Scan BestBuy
│   │
│   ├── amazon_deals.py                  # Scraping functions cho Amazon
│   └── amazon_scanner_agent.py          # Search + Scan Amazon
│
├── bestbuy_untils/                      # 🛠️ UTILITIES
│   ├── clarification_agent.py           # Sinh câu hỏi làm rõ
│   ├── unified_deal.py                  # Chuẩn hóa deal từ 2 nguồn
│   ├── multi_source_scanner_agent.py    # Chọn top 5 từ pool
│   └── gradio_helpers.py                # Helper functions cho UI
│
└── products_vectorstore/                # 📊 CHROMADB - 800K sản phẩm đã embed
    └── chroma.sqlite3
```

---

## 📄 Chi tiết từng File

### 1. Tầng UI (User Interface)

#### `search_key.py` - Entry Point (~290 dòng)

**Mục đích:** Chứa Gradio UI và event handlers. Không chứa business logic.

**Class chính:**
```python
class App:
    """Gradio App for Multi-Source Deal Finder."""
    
    def __init__(self):
        self.framework = None            # Lazy init
        self.current_questions = None    # Lưu câu hỏi
        self.current_keyword = ""        # Keyword hiện tại
    
    def get_framework(self):
        """Lazy initialization của framework."""
        if not self.framework:
            self.framework = MultiSourceFramework()
        return self.framework
    
    # Event handlers
    def generate_questions_handler(...)   # Xử lý khi click "Generate Questions"
    def submit_answers_handler(...)       # Xử lý khi click "Submit & Search"
    def skip_handler(...)                 # Xử lý khi click "Skip, Search Now"
    def _run_pipeline(...)                # Generator chạy pipeline + yield updates
    def push_notification_handler(...)    # Gửi notification
    
    def run(self):
        """Build và launch Gradio app."""
```

**Liên kết với:**
- `multi_source_framework.py` → Gọi framework để chạy pipeline
- `bestbuy_untils/gradio_helpers.py` → Helper functions cho UI

---

### 2. Tầng Framework (Orchestrator)

#### `multi_source_framework.py` - Điều phối trung tâm (~164 dòng)

**Mục đích:** Quản lý resources, lazy init agents, cung cấp high-level methods.

**Class chính:**
```python
class MultiSourceFramework:
    """Framework orchestrator for Multi-Source deal finding."""
    
    DB = "products_vectorstore"
    
    def __init__(self):
        # 1. Load .env
        # 2. Init ChromaDB (400K products)
        # 3. Lazy init planner = None
    
    def init_agents_as_needed(self):
        """Lazy init planning agent khi cần."""
        if not self.planner:
            self.planner = MultiSourcePlanningAgent(self.collection)
    
    # Public methods cho UI gọi
    def generate_questions(keyword)       # Sinh câu hỏi
    def run(keyword, max_urls)            # Chạy pipeline (Skip mode)
    def run_with_answers(...)             # Chạy với clarification
    def send_notification(index)          # Gửi notification
```

**Liên kết với:**
- `search_key.py` ← Được gọi từ UI
- `price_agents/multi_source_planning_agent.py` → Delegate xuống

---

### 3. Tầng Pipeline Logic

#### `price_agents/multi_source_planning_agent.py` - Core Pipeline (~324 dòng)

**Mục đích:** Chứa toàn bộ logic pipeline 6 bước.

**Class chính:**
```python
class MultiSourcePlanningAgent(Agent):
    """Planning Agent điều phối pipeline 6 bước."""
    
    DEAL_THRESHOLD = 100  # Auto-notify threshold
    
    def __init__(self, collection):
        # Init tất cả sub-agents
        self.ensemble = EnsembleAgent(collection)
        self.messenger = MessagingAgent()
        self.clarification = ClarificationAgent()
        self.multi_scanner = MultiSourceScannerAgent()
    
    # Clarification
    def generate_questions(keyword) → ClarificationResponse
    def build_refined_query(keyword, questions, answers) → RefinedQuery
    
    # Pipeline steps
    def search_both_sources(keyword, max_urls)    # Step 1: Search parallel
    def filter_sales(bb_urls, az_urls)            # Step 2: Filter sale items
    def scrape_and_combine(bb_urls, az_items)     # Step 3 & 4: Scrape + combine
    def select_top_deals(unified_deals)           # Step 5: GPT select top 5
    def estimate_prices(deal_selection)           # Step 6: Ensemble estimate
    
    # Main method
    def plan(keyword, max_urls) → List[Opportunity]
    def plan_with_answers(...) → List[Opportunity]
```

**Liên kết với:**
- `multi_source_framework.py` ← Được gọi từ framework
- `bestbuy_scanner_agent.py` → Search BestBuy
- `amazon_scanner_agent.py` → Search Amazon
- `bestbuy_deals.py` → Filter và scrape BestBuy
- `amazon_deals.py` → Filter và scrape Amazon
- `bestbuy_untils/multi_source_scanner_agent.py` → Chọn top 5
- `ensemble_agent.py` → Estimate giá
- `messaging_agent.py` → Gửi notification

---

### 4. Tầng Search Agents

#### `price_agents/bestbuy_scanner_agent.py` (~244 dòng)

**Mục đích:** Tìm kiếm URLs BestBuy bằng Brave Search.

**Classes:**
```python
class BestBuySearchAgent(BaseAgent):
    """Search BestBuy using Brave MCP."""
    MODEL = "gpt-5-nano"
    
    def search(keyword, max_urls) → List[str]
        # Sử dụng Brave Search API với site:bestbuy.com/product


class BestBuyScannerAgent(BaseAgent):
    """Select top 5 deals from BestBuy products."""
    MODEL = "gpt-5-mini"
    
    def scan(scraped_deals) → DealSelection
```

#### `price_agents/amazon_scanner_agent.py` (~255 dòng)

**Mục đích:** Tìm kiếm URLs Amazon bằng Brave Search.

**Classes:**
```python
class AmazonSearchAgent(BaseAgent):
    """Search Amazon using Brave MCP."""
    MODEL = "gpt-5-nano"
    
    def search(keyword, max_urls) → List[str]
        # Tìm URLs có pattern /dp/XXXXXXXXXX


class AmazonScannerAgent(BaseAgent):
    """Select top 5 deals from Amazon products."""
    MODEL = "gpt-5-mini"
    
    def scan(scraped_deals) → DealSelection
```

---

### 5. Tầng Scraping

#### `price_agents/bestbuy_deals.py` (~243 dòng)

**Mục đích:** Scrape thông tin sản phẩm từ BestBuy.

**Functions và Classes:**
```python
class ScrapedBestBuyDeal:
    """Data class cho sản phẩm BestBuy đã scrape."""
    title: str
    brand: Optional[str]
    price: float
    features: str
    url: str

def is_on_sale(url) → bool
    """Check sale bằng BeautifulSoup (nhanh)."""

def filter_sale_urls(urls) → List[str]
    """Filter chỉ giữ sản phẩm đang sale."""

async def scrape_bestbuy_products(urls, headless) → List[ScrapedBestBuyDeal]
    """Scrape chi tiết bằng Playwright."""
```

#### `price_agents/amazon_deals.py` (~414 dòng)

**Mục đích:** Scrape thông tin sản phẩm từ Amazon.

**Lưu ý:** Amazon chặn requests library → PHẢI dùng Playwright.

**Functions và Classes:**
```python
class ScrapedAmazonDeal:
    """Data class cho sản phẩm Amazon đã scrape."""
    title: str
    brand: Optional[str]
    price: float
    features: str
    url: str

async def set_amazon_us_location(page) → bool
    """Set delivery location về US (Zip: 96150)."""

async def is_on_sale_amazon_playwright(url, page) → Tuple[bool, dict]
    """Check sale bằng Playwright (chậm nhưng bắt buộc)."""

async def filter_amazon_sale_urls_playwright(urls, headless) → List[Tuple[str, dict]]
    """Filter sản phẩm đang sale."""

async def scrape_amazon_products(sale_items, headless) → List[ScrapedAmazonDeal]
    """Scrape chi tiết sản phẩm."""
```

---

### 6. Tầng AI Estimation

#### `price_agents/ensemble_agent.py` (~41 dòng)

**Mục đích:** Kết hợp 3 models để dự đoán giá trị thực của sản phẩm.

```python
class EnsembleAgent(Agent):
    """Ensemble 3 models dự đoán giá."""
    
    def __init__(self, collection):
        self.specialist = SpecialistAgent()      # Fine-tuned Llama (10%)
        self.frontier = FrontierAgent(collection) # GPT-5.1 + RAG (80%)
        self.neural_network = NeuralNetworkAgent() # PyTorch DNN (10%)
        self.preprocessor = Preprocessor()
    
    def price(description) → float:
        rewrite = self.preprocessor.preprocess(description)
        specialist = self.specialist.price(rewrite)
        frontier = self.frontier.price(rewrite)
        neural = self.neural_network.price(rewrite)
        
        # Trọng số: 80% Frontier + 10% Specialist + 10% Neural
        combined = frontier * 0.8 + specialist * 0.1 + neural * 0.1
        return combined
```

**3 Models:**
| Model | Weight | Mô tả |
|-------|--------|-------|
| **FrontierAgent** | 80% | GPT-5.1 + RAG (ChromaDB 400K products) |
| **SpecialistAgent** | 10% | Fine-tuned Llama-3.2-3B trên Modal |
| **NeuralNetworkAgent** | 10% | PyTorch DNN local |

---

### 7. Tầng Base và Data Models

#### `price_agents/agent.py` (~33 dòng)

**Mục đích:** Base class cho tất cả agents.

```python
class Agent:
    """Abstract superclass for all agents."""
    
    # ANSI Color codes cho logs
    RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = ...
    
    name: str = ""
    color: str = WHITE
    
    def log(self, message):
        """Log với màu sắc identify agent."""
        logging.info(f"[{self.name}] {message}")
```

#### `price_agents/deals.py` (~152 dòng)

**Mục đích:** Định nghĩa data classes cho deals.

```python
class ScrapedDeal:
    """Deal từ RSS feed (DealNews)."""
    category, title, summary, url, details, features

class Deal(BaseModel):
    """Pydantic model cho deal đã xử lý."""
    product_description: str  # Summary 3-4 câu
    price: float              # Giá sale
    url: str                  # Link sản phẩm

class DealSelection(BaseModel):
    """Output của GPT - chứa top 5 deals."""
    deals: List[Deal]

class Opportunity(BaseModel):
    """Deal + giá ước lượng + discount."""
    deal: Deal
    estimate: float   # Giá ước lượng
    discount: float   # estimate - price
```

#### `price_agents/preprocessor.py` (~49 dòng)

**Mục đích:** Làm sạch và chuẩn hóa text trước khi estimate.

```python
class Preprocessor:
    """Preprocess text using LLM."""
    MODEL = "ollama/llama3.2"  # Hoặc GPT
    
    def preprocess(text) → str:
        """Chuẩn hóa text thành format:
        Title: ...
        Category: ...
        Brand: ...
        Description: ...
        Details: ...
        """
```

---

### 8. Tầng Utilities

#### `bestbuy_untils/clarification_agent.py`

**Mục đích:** Sinh 3 câu hỏi làm rõ nhu cầu người dùng.

```python
class ClarificationAgent:
    def generate_questions(keyword) → ClarificationResponse
        # Sinh 3 câu hỏi: purpose, budget, preferences
    
    def build_refined_query(keyword, questions, answers) → RefinedQuery
        # Kết hợp keyword + answers → query tốt hơn
```

#### `bestbuy_untils/unified_deal.py`

**Mục đích:** Chuẩn hóa deals từ BestBuy và Amazon thành format chung.

```python
class UnifiedScrapedDeal:
    source: str    # "BestBuy" hoặc "Amazon"
    title: str
    brand: Optional[str]
    price: float
    features: str
    url: str
    
    @classmethod
    def from_bestbuy(deal: ScrapedBestBuyDeal) → UnifiedScrapedDeal
    
    @classmethod
    def from_amazon(deal: ScrapedAmazonDeal) → UnifiedScrapedDeal
    
    def describe() → str
        # Format cho GPT
```

#### `bestbuy_untils/multi_source_scanner_agent.py`

**Mục đích:** Chọn top 5 deals từ pool BestBuy + Amazon.

```python
class MultiSourceScannerAgent(BaseAgent):
    MODEL = "gpt-5-mini"
    
    def scan(unified_deals: List[UnifiedScrapedDeal]) → DealSelection
        # GPT chọn 5 deals tốt nhất từ cả 2 nguồn
```

#### `bestbuy_untils/gradio_helpers.py`

**Mục đích:** Helper functions cho Gradio UI.

```python
class QueueHandler(logging.Handler):
    """Capture logs vào queue."""

def setup_logging(log_queue)
def html_for_logs(log_data) → str
def opportunities_to_table(opportunities) → List[List[str]]
def format_questions_html(questions) → str
```

---

## 🔗 Sơ đồ liên kết giữa các Files

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            FILE DEPENDENCY DIAGRAM                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        search_key.py (UI)                                │   │
│  │                              │                                           │   │
│  │                    imports ↓                                            │   │
│  │              multi_source_framework.py                                   │   │
│  │              gradio_helpers.py                                           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                │                                                │
│                        imports ↓                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                 multi_source_framework.py (Framework)                    │   │
│  │                              │                                           │   │
│  │                    imports ↓                                            │   │
│  │              multi_source_planning_agent.py                              │   │
│  │              deals.py (Opportunity)                                      │   │
│  │              clarification_agent.py                                      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                │                                                │
│                        imports ↓                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │             multi_source_planning_agent.py (Pipeline)                    │   │
│  │                              │                                           │   │
│  │                    imports ↓                                            │   │
│  │    ┌──────────────────┬──────────────────┬─────────────────┐            │   │
│  │    │                  │                  │                 │            │   │
│  │    ▼                  ▼                  ▼                 ▼            │   │
│  │ ensemble_agent.py  messaging_agent.py  bestbuy_*.py  amazon_*.py       │   │
│  │    │                  │                  │                 │            │   │
│  │    ▼                  ▼                  ▼                 ▼            │   │
│  │ (estimate)        (notify)           (search+scrape)  (search+scrape)  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         BASE CLASSES & DATA                              │   │
│  │                                                                          │   │
│  │     agent.py ◄──── Tất cả agents kế thừa                                │   │
│  │     deals.py ◄──── Deal, DealSelection, Opportunity                     │   │
│  │     preprocessor.py ◄──── EnsembleAgent sử dụng                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Cách Setup và Chạy

### 1. Yêu cầu hệ thống

- Python 3.10+
- Node.js 18+ (cho MCP servers)
- Chromium browser (cho Playwright)

### 2. Cài đặt dependencies

```bash
# Clone repo
cd segment4

# Cài đặt Python packages
uv sync

# Cài đặt Playwright browsers
uv run playwright install
```

### 3. Cấu hình Environment Variables

Tạo file `.env` trong folder `segment4/`:

```env
# OpenAI API Key (bắt buộc)
OPENAI_API_KEY=sk-xxx...

# Brave Search API Key (bắt buộc cho search)
BRAVE_API_KEY=BSA-xxx...

# Pushover Notification (tùy chọn)
PUSHOVER_USER=xxx
PUSHOVER_TOKEN=xxx

# Preprocessor Model (tùy chọn)
PRICER_PREPROCESSOR_MODEL=ollama/llama3.2
```

### 4. Chạy ứng dụng

```bash
cd segment4
uv run search_key.py
```

Ứng dụng sẽ mở trình duyệt tại `http://127.0.0.1:7860`

---

## 🕐 Thời gian thực thi (Latency)

```
Total Pipeline Time: ~90-150 giây

  ├── Generate questions:                 3-5s
  ├── Build refined query:                2-3s
  ├── Search BestBuy + Amazon (parallel): 10-20s
  ├── Filter BestBuy (BeautifulSoup):     5-10s
  ├── Filter Amazon (Playwright):         15-25s
  ├── Scrape BestBuy (Playwright):        10-20s
  ├── Scrape Amazon (Playwright):         15-25s
  ├── GPT select top 5:                   3-5s
  └── Estimate (3 models × 5 deals):      20-30s
```

---

## 💰 Chi phí ước tính (Cost)

| Component | Model | Cost per Run |
|-----------|-------|--------------|
| Search Agents | GPT-5-nano | ~$0.001 |
| Clarification | GPT-5-nano | ~$0.001 |
| Scan top 5 | GPT-5-mini | ~$0.002 |
| Estimate (5 deals) | GPT-5.1 | ~$0.005 |
| Preprocess (5 deals) | Llama local | $0 |
| **Total** | | **~$0.01/run** |

---

## 📊 Kết quả mẫu

**Keyword:** "gaming laptop"  
**Date:** 2026-02-07

| # | Product | Source | Sale $ | Est. $ | Discount |
|---|---------|--------|--------|--------|----------|
| 1 | ASUS ROG Strix G16 Gaming Laptop 16" RTX 4060... | [Amazon] | $999.99 | $1,450.00 | $450 (31%) 🔥 |
| 2 | MSI Katana 15.6" Gaming Laptop RTX 4050... | [BestBuy] | $799.99 | $1,150.00 | $350 (30%) 🔥 |
| 3 | Dell G15 Gaming Laptop 15.6" RTX 3050... | [Amazon] | $649.99 | $920.00 | $270 (29%) 🔥 |
| 4 | HP Victus 15.6" Gaming Laptop GTX 1650... | [BestBuy] | $549.99 | $780.00 | $230 (30%) 🔥 |
| 5 | Acer Nitro 5 Gaming Laptop 15.6" RTX 3050... | [Amazon] | $599.99 | $820.00 | $220 (27%) ✅ |

**Best Deal:** ASUS ROG Strix G16 - Discount $450 (31%)  
**Auto-notification:** Đã gửi! (Discount > $100 threshold)

---

## 🎯 Tóm tắt

| Mục | Chi tiết |
|-----|----------|
| **Mục tiêu** | Tìm deals tốt nhất từ BestBuy + Amazon |
| **Input** | Keyword + (tùy chọn) câu trả lời làm rõ |
| **Output** | Top 5 deals với giá ước lượng và discount % |
| **Công nghệ AI** | GPT-5-nano, GPT-5-mini, GPT-5.1, Llama-3.2-3B, PyTorch DNN |
| **Scraping** | BeautifulSoup (BestBuy), Playwright (Amazon) |
| **Search** | Brave Search API via MCP |
| **Database** | ChromaDB (400K products embedded) |
| **UI** | Gradio |
| **Latency** | 90-150 giây |
| **Cost** | ~$0.01/run |

---

*Documentation generated on 2026-02-07*
