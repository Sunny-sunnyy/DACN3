# 🎯 THE PRICE IS RIGHT - COMPLETE PROJECT DOCUMENTATION

> **Cập nhật:** 2026-02-07  
> **Version:** 4.1 (Refactored Multi-Source v4 với modular architecture)  
> **Author:** Minh Hiếu - Sunny

---

## 📋 MỤC LỤC

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Kiến trúc tổng thể](#2-kiến-trúc-tổng-thể)
3. [Dự án 1: Auto Deal Finder (RSS)](#3-dự-án-1-auto-deal-finder-rss)
4. [Dự án 2: BestBuy Keyword Search v1](#4-dự-án-2-bestbuy-keyword-search-v1)
5. [Dự án 3: BestBuy v2 với Clarification Agent](#5-dự-án-3-bestbuy-v2-với-clarification-agent)
6. [Dự án 4: Amazon Search v1](#6-dự-án-4-amazon-search-v1)
7. [Dự án 5: Multi-Source v3 (BestBuy + Amazon)](#7-dự-án-5-multi-source-v3-bestbuy--amazon)
8. [Dự án 6: Multi-Source v5 Refactored (search_key.py)](#8-dự-án-6-multi-source-v5-refactored-searchkeypy) 🆕
9. [Chi tiết các AI Agents](#9-chi-tiết-các-ai-agents)
10. [Tech Stack & Dependencies](#10-tech-stack--dependencies)
11. [Cấu trúc thư mục](#11-cấu-trúc-thư-mục)
12. [Setup & Installation](#12-setup--installation)
13. [Usage Guide](#13-usage-guide)
14. [API Keys & Environment Variables](#14-api-keys--environment-variables)
15. [Troubleshooting](#15-troubleshooting)
16. [Performance Metrics](#16-performance-metrics)
17. [Future Improvements](#17-future-improvements)

---

## 1. TỔNG QUAN DỰ ÁN

### 🎯 **Mục tiêu:**
**"The Price is Right"** là hệ thống AI Agents tự động tìm kiếm và phân tích deals (giảm giá) trên internet, sử dụng Machine Learning để dự đoán giá trị thực của sản phẩm và tìm ra những cơ hội mua hàng tốt nhất.

### 🔑 **Core Concept:**
```
Estimated True Value - Sale Price = Discount (Deal Value)
```

Nếu discount > 0 và đủ lớn → Đây là deal tốt!

### 📊 **7 Phương thức hoạt động:**

| Phương thức | File chính | Input | Output | Use Case |
|-------------|------------|-------|--------|----------|
| **Auto Deal Finder** | `price_is_right.py` | RSS Feeds (DealNews) | Top deal mỗi 5 phút | Passive hunting |
| **BestBuy Search v1** | `bestbuy_search.py` | Keyword từ user | Top 5 deals | Active searching |
| **BestBuy Search v2** | `bestbuy2.py` | Keyword + Clarification | Refined top 5 deals | Smart searching |
| **Amazon Search v1** | `amazon_search.py` | Keyword từ user | Top 5 deals Amazon | Amazon hunting |
| **Multi-Source v3** | `bestbuy3.py` | Keyword + Clarification | Top 5 từ BestBuy + Amazon | Combined hunting |
| **Multi-Source v4** | `bestbuy4.py` | Keyword + Clarification | Top 5 từ BestBuy + Amazon | Modular version |
| **Multi-Source v5** 🆕 | `search_key.py` | Keyword + Clarification | Top 5 từ BestBuy + Amazon | **REFACTORED CLEAN CODE** |

### 🏗️ **Multi-Source v5 (search_key.py) - Refactored Architecture:**

| File | Lines | Responsibility |
|------|-------|----------------|
| `search_key.py` | ~290 | Gradio UI (App class) |
| `multi_source_framework.py` | ~164 | Framework orchestrator |
| `price_agents/multi_source_planning_agent.py` | ~324 | Pipeline logic (6 steps) |

### 🤖 **AI Models sử dụng:**

#### **Ensemble Agent (3 models) - Dự đoán giá:**
1. **FrontierAgent (80%)** - GPT-5.1 + RAG (ChromaDB với 400K products)
2. **SpecialistAgent (10%)** - Fine-tuned Llama-3.2-3B (Modal Serverless)
3. **NeuralNetworkAgent (10%)** - PyTorch Deep NN (local)

**Formula:**
```python
final_estimate = frontier * 0.8 + specialist * 0.1 + neural * 0.1
```

#### **Other Agents:**
- **MultiSourcePlanningAgent** 🆕 - Orchestrates 6-step pipeline (refactored)
- **ClarificationAgent** - GPT-5-mini: Sinh câu hỏi làm rõ nhu cầu user
- **BestBuySearchAgent** - GPT-5-nano + Brave MCP: Tìm kiếm BestBuy URLs
- **BestBuyScannerAgent** - GPT-5-mini: Chọn top 5 deals từ BestBuy
- **AmazonSearchAgent** - GPT-5-nano + Brave MCP: Tìm kiếm Amazon URLs
- **AmazonScannerAgent** - GPT-5-mini: Chọn top 5 deals từ Amazon
- **MultiSourceScannerAgent** - GPT-5-mini: Chọn top 5 từ pool BestBuy + Amazon
- **ScannerAgent** - GPT-5-mini: Quét RSS feeds
- **MessagingAgent** - GPT-5-nano: Tạo message và gửi notification
- **AutonomousPlanningAgent** - GPT-5.1: Điều phối toàn bộ pipeline tự động

---

## 2. KIẾN TRÚC TỔNG THỂ

### 🏗️ **System Architecture:**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SEGMENT4 PROJECT v4.0                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────┐ │
│  │  Auto Deal Finder   │ │ BestBuy Search v1   │ │ BestBuy Search v2       │ │
│  │  (price_is_right.py)│ │ (bestbuy_search.py) │ │ (bestbuy2.py)           │ │
│  │                     │ │                     │ │ + ClarificationAgent    │ │
│  │  [Auto RSS Scan]    │ │ [Direct Search]     │ │ [Smart Q&A Search]      │ │
│  └──────────┬──────────┘ └──────────┬──────────┘ └────────────┬────────────┘ │
│             │                       │                          │              │
│             └───────────────────────┴──────────────────────────┘              │
│                                     │                                          │
│                                     ▼                                          │
│           ┌────────────────────────────────────────┐                          │
│           │      deal_agent_framework.py           │                          │
│           │      - ChromaDB Initialization         │                          │
│           │      - Memory Management (memory.json) │                          │
│           │      - Agent Lifecycle                 │                          │
│           └─────────────────────┬──────────────────┘                          │
│                                 │                                              │
│                                 ▼                                              │
│           ┌─────────────────────────────────────────────────────────────────┐ │
│           │                    AGENT ECOSYSTEM (price_agents/)               │ │
│           │                                                                   │ │
│           │  ┌───────────────────────────────────────────────────────────┐  │ │
│           │  │                    DATA COLLECTION                         │  │ │
│           │  │  • ScannerAgent (RSS feeds từ DealNews)                   │  │ │
│           │  │  • BestBuySearchAgent (Brave MCP → Product URLs)          │  │ │
│           │  │  • filter_sale_urls() (BeautifulSoup check sale)          │  │ │
│           │  │  • scrape_bestbuy_products() (Playwright scraping)        │  │ │
│           │  └───────────────────────────────────────────────────────────┘  │ │
│           │                                                                   │ │
│           │  ┌───────────────────────────────────────────────────────────┐  │ │
│           │  │                    USER INTERACTION                        │  │ │
│           │  │  • ClarificationAgent (GPT-5-mini)                        │  │ │
│           │  │    - generate_questions(keyword)                          │  │ │
│           │  │    - build_refined_query(keyword, questions, answers)     │  │ │
│           │  └───────────────────────────────────────────────────────────┘  │ │
│           │                                                                   │ │
│           │  ┌───────────────────────────────────────────────────────────┐  │ │
│           │  │                    DEAL SELECTION                          │  │ │
│           │  │  • BestBuyScannerAgent (GPT-5-mini Structured Output)     │  │ │
│           │  │  • ScannerAgent (GPT-5-mini Structured Output)            │  │ │
│           │  └───────────────────────────────────────────────────────────┘  │ │
│           │                                                                   │ │
│           │  ┌───────────────────────────────────────────────────────────┐  │ │
│           │  │                 PRICE ESTIMATION                           │  │ │
│           │  │  • EnsembleAgent (orchestrates 3 models)                  │  │ │
│           │  │    ├─ FrontierAgent (GPT-5.1 + RAG)        → 80%         │  │ │
│           │  │    ├─ SpecialistAgent (Modal fine-tuned)   → 10%         │  │ │
│           │  │    └─ NeuralNetworkAgent (PyTorch local)   → 10%         │  │ │
│           │  │  • Preprocessor (Groq/Ollama text cleanup)                │  │ │
│           │  └───────────────────────────────────────────────────────────┘  │ │
│           │                                                                   │ │
│           │  ┌───────────────────────────────────────────────────────────┐  │ │
│           │  │                 ORCHESTRATION                              │  │ │
│           │  │  • AutonomousPlanningAgent (GPT-5.1 + MCP tools)          │  │ │
│           │  │    - scan_the_internet_for_bargains()                     │  │ │
│           │  │    - estimate_true_value(description)                     │  │ │
│           │  │    - notify_user_of_deal(deal_info)                       │  │ │
│           │  │  • PlanningAgent (non-autonomous legacy)                  │  │ │
│           │  └───────────────────────────────────────────────────────────┘  │ │
│           │                                                                   │ │
│           │  ┌───────────────────────────────────────────────────────────┐  │ │
│           │  │                 NOTIFICATION                               │  │ │
│           │  │  • MessagingAgent (GPT-5-nano + Pushover API)             │  │ │
│           │  │    - craft_message() → Witty sales tone                   │  │ │
│           │  │    - push() → Pushover notification                       │  │ │
│           │  └───────────────────────────────────────────────────────────┘  │ │
│           │                                                                   │ │
│           └─────────────────────────────────────────────────────────────────┘ │
│                                     │                                          │
│                                     ▼                                          │
│           ┌─────────────────────────────────────────────────────────────────┐ │
│           │                      INFRASTRUCTURE                              │ │
│           │                                                                   │ │
│           │  • ChromaDB (products_vectorstore/) - 400K product vectors      │ │
│           │  • Modal Serverless (pricer_service2.py) - T4 GPU inference     │ │
│           │  • PyTorch Model (deep_neural_network.pth) - 1.1GB weights      │ │
│           │  • Brave Search API (MCP server) - Web search                   │ │
│           │  • OpenAI API - GPT-5.1, GPT-5-mini, GPT-5-nano                 │ │
│           │  • Groq API - Fast preprocessing                                 │ │
│           │  • Pushover API - Push notifications                             │ │
│           │  • Playwright - Browser automation                               │ │
│           │                                                                   │ │
│           └─────────────────────────────────────────────────────────────────┘ │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. DỰ ÁN 1: AUTO DEAL FINDER (RSS)

### 📝 **Mô tả:**
Tự động quét RSS feeds từ DealNews mỗi 5 phút, chọn top 5 deals, estimate giá, và gửi notification cho deal tốt nhất.

### 🔄 **Workflow Chi Tiết:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTO DEAL FINDER WORKFLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1️⃣ TIMER TRIGGER (Every 5 minutes)                                        │
│  └─► Gradio gr.Timer(value=300, active=True)                                │
│                                                                              │
│  2️⃣ ScannerAgent.scan(memory)                                              │
│  ├─► ScrapedDeal.fetch()                                                    │
│  │   ├─► Fetch từ 5 RSS feeds (DealNews)                                   │
│  │   ├─► BeautifulSoup extract summary + details + features                │
│  │   └─► Return List[ScrapedDeal]                                          │
│  ├─► Filter deals not in memory                                             │
│  ├─► GPT-5-mini với Structured Outputs                                      │
│  └─► Return DealSelection (top 5 deals)                                     │
│                                                                              │
│  3️⃣ AutonomousPlanningAgent.plan(memory)                                   │
│  ├─► Task: "Find great deals, estimate value, notify user"                 │
│  ├─► GPT-5.1 tự động reasoning và gọi tools:                               │
│  │   ├─► scan_the_internet_for_bargains()                                  │
│  │   ├─► estimate_true_value(description) × 5 deals                        │
│  │   └─► notify_user_of_deal(best_deal)                                    │
│  └─► MCP filesystem tool → Write sandbox/deals.md                           │
│                                                                              │
│  4️⃣ EnsembleAgent.price(description) × 5 deals                             │
│  ├─► Preprocessor.preprocess()                                              │
│  │   └─► Groq/Ollama normalize text format                                  │
│  ├─► [PARALLEL] 3 models inference:                                         │
│  │   ├─► FrontierAgent: ChromaDB RAG → 5 similar → GPT-5.1                 │
│  │   ├─► SpecialistAgent: Modal remote call → Fine-tuned Llama            │
│  │   └─► NeuralNetworkAgent: Local PyTorch inference                       │
│  └─► Weighted ensemble: estimate = F*0.8 + S*0.1 + N*0.1                   │
│                                                                              │
│  5️⃣ Select Best Deal                                                        │
│  ├─► Sort by discount (estimate - price) descending                        │
│  └─► Pick if discount > threshold ($50)                                     │
│                                                                              │
│  6️⃣ MessagingAgent.notify(description, price, estimate, url)               │
│  ├─► craft_message() → GPT-5-nano với witty sales tone                     │
│  └─► push() → Pushover API notification                                     │
│                                                                              │
│  7️⃣ Update Memory                                                           │
│  └─► memory.json += Opportunity(deal, estimate, discount)                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 📂 **Files liên quan:**

| File | Mô tả |
|------|-------|
| `price_is_right.py` | Gradio Web UI với auto-refresh 5 phút |
| `deal_agent_framework.py` | Framework coordinator, ChromaDB init, memory |
| `price_agents/autonomous_planning_agent.py` | Main orchestrator với GPT-5.1 |
| `price_agents/planning_agent.py` | Non-autonomous version (legacy) |
| `price_agents/scanner_agent.py` | RSS scraper với GPT-5-mini |
| `price_agents/deals.py` | Data models: ScrapedDeal, Deal, DealSelection, Opportunity |
| `price_agents/ensemble_agent.py` | 3-model ensemble |
| `memory.json` | Lưu các deals đã found |
| `sandbox/deals.md` | Output markdown file |

### 🎨 **UI Features:**
- Real-time logs với ANSI color → HTML formatting
- Dataframe: Product | Price | Estimate | Discount | URL
- 3D t-SNE visualization (ChromaDB vectors)
- Click row → Send push notification
- Auto-refresh timer 5 phút

### 🔧 **Configuration:**

```python
# RSS Feeds (deals.py)
feeds = [
    "https://www.dealnews.com/c142/Electronics/?rss=1",
    "https://www.dealnews.com/c39/Computers/?rss=1",
    "https://www.dealnews.com/f1912/Smart-Home/?rss=1",
    "https://www.dealnews.com/c238/Automotive/?rss=1",
    "https://www.dealnews.com/c196/Home-Garden/?rss=1",
]

# Timer interval (price_is_right.py)
timer = gr.Timer(value=300, active=True)  # 300 seconds = 5 minutes
```

---

## 4. DỰ ÁN 2: BESTBUY KEYWORD SEARCH V1

### 📝 **Mô tả:**
Cho phép user nhập keyword (ví dụ: "Smart TV") để tìm sản phẩm cụ thể trên BestBuy, thay vì chỉ quét RSS tự động.

### 🎯 **Why BestBuy?**
- ✅ Structured product pages → Easy to scrape
- ✅ Clear sale indicators → Easy to filter
- ✅ Large inventory → Many deals
- ✅ Real-time prices → Up-to-date

### 🔄 **Workflow Chi Tiết:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BESTBUY KEYWORD SEARCH V1 WORKFLOW                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER INPUT: "Smart TV" + Max URLs: 10                                      │
│                                                                              │
│  1️⃣ BestBuySearchAgent.search(keyword, max_urls)                           │
│  ├─► MCPServerStdio(brave-search)                                           │
│  ├─► Query: "Smart TV site:bestbuy.com/product"                            │
│  ├─► GPT-5-nano extract URLs từ search results                              │
│  └─► Return List[str] (up to max_urls URLs)                                 │
│                                                                              │
│  2️⃣ filter_sale_urls(urls)                                                  │
│  ├─► For each URL: requests.get() + BeautifulSoup                          │
│  ├─► Check sale indicators:                                                 │
│  │   ├─► data-testid="price-block-total-savings-text"                      │
│  │   └─► data-lu-target="comp_value"                                       │
│  └─► Return only URLs with sale indicators                                  │
│                                                                              │
│  3️⃣ scrape_bestbuy_products(sale_urls)                                     │
│  ├─► Playwright browser (headless=False)                                    │
│  ├─► For each URL:                                                          │
│  │   ├─► page.goto(url)                                                    │
│  │   ├─► Extract: h1.h4 → Title                                            │
│  │   ├─► Extract: a.c-button-link → Brand                                  │
│  │   ├─► Extract: [data-testid="price-block-customer-price"] → Price      │
│  │   ├─► Click: button "Features"                                          │
│  │   └─► Extract: [data-testid="brix-sheet-content"] → Features           │
│  └─► Return List[ScrapedBestBuyDeal]                                        │
│                                                                              │
│  4️⃣ BestBuyScannerAgent.scan(scraped_deals)                                │
│  ├─► GPT-5-mini với Structured Outputs                                      │
│  ├─► Prompt: "Select 5 most detailed deals with clear price"               │
│  └─► Return DealSelection (top 5)                                           │
│                                                                              │
│  5️⃣ EnsembleAgent.price(deal.product_description) × 5                      │
│  └─► Same as Auto Deal Finder                                               │
│                                                                              │
│  6️⃣ Display Results                                                         │
│  ├─► Sort by discount (descending)                                          │
│  ├─► Gradio Dataframe với status icons:                                     │
│  │   🔥 > $200 | ✅ > $100 | 👍 > $0 | ❌ Overpriced                        │
│  └─► Show real-time logs                                                    │
│                                                                              │
│  7️⃣ (Optional) Push Notification                                            │
│  └─► User click button → MessagingAgent.notify()                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 📂 **Files liên quan:**

| File | Mô tả |
|------|-------|
| `bestbuy_search.py` | Standalone Gradio app |
| `price_agents/bestbuy_deals.py` | ScrapedBestBuyDeal, is_on_sale(), filter_sale_urls(), scrape_bestbuy_products() |
| `price_agents/bestbuy_scanner_agent.py` | BestBuySearchAgent, BestBuyScannerAgent |

### 🔧 **Key Functions:**

```python
# 1. Search - BestBuySearchAgent uses Brave MCP
def search_bestbuy(keyword: str, max_urls: int = 10) -> List[str]:
    search_agent = BestBuySearchAgent()
    return search_agent.search(keyword, max_urls)

# 2. Filter - BeautifulSoup check sale indicators
def filter_sales(urls: List[str]) -> List[str]:
    return filter_sale_urls(urls)

# 3. Scrape - Playwright browser automation
async def scrape_products(urls: List[str]) -> List[ScrapedBestBuyDeal]:
    return await scrape_bestbuy_products(urls, headless=False)

# 4. Select - GPT-5-mini structured outputs
def select_top_deals(scraped: List[ScrapedBestBuyDeal]) -> DealSelection:
    scanner = BestBuyScannerAgent()
    return scanner.scan(scraped)

# 5. Estimate - 3-model ensemble
def estimate_prices(deals: DealSelection, ensemble: EnsembleAgent) -> List[Opportunity]:
    opportunities = []
    for deal in deals.deals:
        estimate = ensemble.price(deal.product_description)
        discount = estimate - deal.price
        opportunities.append(Opportunity(deal=deal, estimate=estimate, discount=discount))
    return sorted(opportunities, key=lambda x: x.discount, reverse=True)
```

---

## 5. DỰ ÁN 3: BESTBUY V2 VỚI CLARIFICATION AGENT

### 📝 **Mô tả:**
Phiên bản nâng cao của BestBuy Search, thêm **ClarificationAgent** để hỏi user 3 câu hỏi làm rõ nhu cầu trước khi search, giúp tìm được deals phù hợp hơn.

### 🆕 **New Features:**
- **Clarification Flow**: 3 câu hỏi động theo sản phẩm
- **Refined Query**: Xây dựng query tối ưu từ câu trả lời
- **Skip Option**: Có thể bỏ qua để search trực tiếp
- **Query Comparison**: Hiển thị Original vs Refined query
- **Better Results**: Test cho thấy improved discount 68% vs 27%

### 🔄 **Workflow Chi Tiết:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BESTBUY V2 WITH CLARIFICATION WORKFLOW                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER INPUT: "laptop"                                                        │
│                                                                              │
│  1️⃣ [NEW] ClarificationAgent.generate_questions(keyword)                   │
│  ├─► GPT-5-mini with Pydantic Structured Output                             │
│  ├─► Generate 3 dynamic questions based on product type                     │
│  │   Example for "laptop":                                                   │
│  │   Q1: "What brand do you prefer?" [Dell, HP, Lenovo, Acer, Any]         │
│  │   Q2: "Primary use case?" [Gaming, Work, Study, General, Any]           │
│  │   Q3: "Budget range?" [Under $500, $500-800, $800-1200, Any]            │
│  └─► Return ClarificationResponse(product_category, questions[3])           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         USER CHOICE                                    │   │
│  │                                                                        │   │
│  │    ┌─────────────────────┐    ┌─────────────────────────────────┐    │   │
│  │    │   CLARIFICATION     │    │   SKIP FLOW                      │    │   │
│  │    │   FLOW              │    │                                  │    │   │
│  │    │                     │    │   User clicks "Skip, search now" │    │   │
│  │    │   User answers:     │    │   ↓                              │    │   │
│  │    │   A1: "Acer"        │    │   SEARCH_QUERY = "laptop"        │    │   │
│  │    │   A2: "for students"│    │   (original keyword)             │    │   │
│  │    │   A3: "under $800"  │    │                                  │    │   │
│  │    │   ↓                 │    └─────────────────────────────────┘    │   │
│  │    │   build_refined_query()                                          │   │
│  │    │   ↓                 │                                            │   │
│  │    │   SEARCH_QUERY =    │                                            │   │
│  │    │   "Acer laptops for │                                            │   │
│  │    │   students under    │                                            │   │
│  │    │   $800"             │                                            │   │
│  │    └─────────────────────┘                                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  [Display] 🔄 Original: "laptop" → Refined: "Acer laptops for students..."  │
│                                                                              │
│  2️⃣ BestBuySearchAgent.search(SEARCH_QUERY, max_urls)                      │
│  └─► (Same as v1)                                                            │
│                                                                              │
│  3️⃣ filter_sale_urls(urls)                                                  │
│  └─► (Same as v1)                                                            │
│                                                                              │
│  4️⃣ scrape_bestbuy_products(sale_urls)                                     │
│  └─► (Same as v1)                                                            │
│                                                                              │
│  5️⃣ BestBuyScannerAgent.scan(scraped_deals)                                │
│  └─► (Same as v1)                                                            │
│                                                                              │
│  6️⃣ EnsembleAgent.price() × 5                                              │
│  └─► (Same as v1)                                                            │
│                                                                              │
│  7️⃣ Display Results + Real-time Logs                                        │
│  └─► (Enhanced with logs_html output)                                        │
│                                                                              │
│  8️⃣ (Optional) Push Notification                                            │
│  └─► (Same as v1)                                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 📂 **Files liên quan:**

| File | Mô tả |
|------|-------|
| `bestbuy2.py` | Gradio app với Clarification flow |
| `price_agents/bestbuy_deals.py` | Scraping functions |
| `price_agents/bestbuy_scanner_agent.py` | Search & Select agents |

### 🆕 **ClarificationAgent Code:**

```python
class ClarificationQuestion(BaseModel):
    """A single clarification question with options."""
    question: str = Field(description="The clarification question in English")
    options: List[str] = Field(
        description="4-6 options for the user. Last option = 'Any' or 'No preference'",
        min_length=3, max_length=6
    )

class ClarificationResponse(BaseModel):
    """Response containing clarification questions generated by LLM."""
    product_category: str = Field(description="Detected product category")
    questions: List[ClarificationQuestion] = Field(
        description="Exactly 3 clarification questions",
        min_length=3, max_length=3
    )

class RefinedQuery(BaseModel):
    """Refined search query built from user answers."""
    query: str = Field(description="Optimized search query for BestBuy")
    summary: str = Field(description="Brief summary of user's needs")

class ClarificationAgent:
    MODEL = "gpt-5-mini"
    
    def generate_questions(self, keyword: str) -> ClarificationResponse:
        """Generate 3 clarification questions based on keyword."""
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.GENERATE_QUESTIONS_PROMPT},
                {"role": "user", "content": f"Product keyword: {keyword}"}
            ],
            response_format=ClarificationResponse
        )
        return result.choices[0].message.parsed
    
    def build_refined_query(
        self, keyword: str, questions: List[ClarificationQuestion], answers: List[str]
    ) -> RefinedQuery:
        """Build refined search query from user's answers."""
        # Format Q&A for the prompt
        qa_text = ""
        for i, (q, a) in enumerate(zip(questions, answers), 1):
            qa_text += f"Q{i}: {q.question}\nA{i}: {a}\n\n"
        
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.BUILD_QUERY_PROMPT},
                {"role": "user", "content": f"Original: {keyword}\nAnswers:\n{qa_text}"}
            ],
            response_format=RefinedQuery
        )
        return result.choices[0].message.parsed
```

### 📊 **Test Results Comparison:**

| Metric | Clarification Flow | Skip Flow |
|--------|-------------------|-----------|
| Input | "laptop" | "laptop" |
| Answers | Acer, for students, under $800 | N/A |
| Search Query | "Acer laptops for students under $800" | "laptop" |
| Deals Found | 4 | 5 |
| Best Deal | Acer Nitro 17.3" | HP OmniBook 5 Flip |
| Best Price | $279.99 | $542.99 |
| Best Discount | **$609.17 (68.5%)** | $204.64 (27.4%) |

**Kết luận:** Clarification flow giúp tìm được deals tốt hơn đáng kể!

---

## 6. DỰ ÁN 4: AMAZON SEARCH V1

### 📝 **Mô tả:**
Mở rộng hệ thống sang **Amazon** - marketplace lớn nhất thế giới. Pipeline tương tự BestBuy nhưng cần dùng Playwright cho tất cả operations vì Amazon block requests.

### 🎯 **Thách thức đã giải quyết:**
- ❌ `requests` bị Amazon block (CAPTCHA/Robot check)
- ✅ **Giải pháp:** Playwright + Set US Zip Code (96150) qua UI

### 🔄 **Workflow Chi Tiết:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AMAZON SEARCH V1 WORKFLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER INPUT: "Smart TV" + Max URLs: 15                                       │
│                                                                              │
│  1️⃣ AmazonSearchAgent.search(keyword, max_urls)                             │
│  ├─► MCPServerStdio(brave-search)                                           │
│  ├─► Query: "Smart TV site:amazon.com/dp"                                   │
│  ├─► GPT-5-nano extract URLs (format: /dp/ASIN)                             │
│  └─► Return List[str] (up to max_urls URLs)                                 │
│                                                                              │
│  2️⃣ filter_amazon_sale_urls_playwright(urls)                                │
│  ├─► Playwright browser (headless=False)                                    │
│  ├─► Set US Zip Code: 96150 (California)                                    │
│  ├─► Check sale indicators:                                                 │
│  │   ├─► span.savingsPercentage ("-15%")                                    │
│  │   ├─► span.basisPrice ("List Price:")                                    │
│  │   └─► [data-a-strike="true"] (strikethrough)                             │
│  └─► Return List[(url, price_info)] for sale items                          │
│                                                                              │
│  3️⃣ scrape_amazon_products(sale_items)                                      │
│  ├─► Playwright browser                                                      │
│  ├─► Multi-selector fallback strategy:                                       │
│  │   ├─► TITLE_SELECTORS: #productTitle, h1.product-title-word-break, ...   │
│  │   ├─► BRAND_SELECTORS: #bylineInfo, a#bylineInfo, #brand, ...            │
│  │   └─► FEATURES_SELECTORS: #feature-bullets ul, #productDescription p, ...│
│  └─► Return List[ScrapedAmazonDeal]                                          │
│                                                                              │
│  4️⃣ AmazonScannerAgent.scan(scraped_deals)                                  │
│  ├─► GPT-5-mini với Structured Outputs                                      │
│  ├─► Prompt: "Select 5 most detailed deals with clear price"               │
│  └─► Return DealSelection (top 5)                                           │
│                                                                              │
│  5️⃣ EnsembleAgent.price(deal.product_description) × 5                       │
│  └─► Same as BestBuy pipeline                                                │
│                                                                              │
│  6️⃣ Display Results + Optional Push Notification                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 📂 **Files liên quan:**

| File | Mô tả |
|------|-------|
| `amazon_search.py` | Gradio Web App cho Amazon search |
| `price_agents/amazon_deals.py` | `ScrapedAmazonDeal`, `filter_amazon_sale_urls_playwright()`, `scrape_amazon_products()` |
| `price_agents/amazon_scanner_agent.py` | `AmazonSearchAgent`, `AmazonScannerAgent` |

### 📊 **Test Results (2026-02-05):**

| Product | Sale Price | Est. Value | Discount | % |
|---------|------------|------------|----------|---|
| Amazon Fire TV 43" 4K | $199.99 | $286.54 | **$86.55** | 30.2% |
| INSIGNIA 24" LED FHD | $69.99 | $126.43 | **$56.44** | 44.6% |

### ⚠️ **Lưu ý quan trọng:**
1. Amazon **bắt buộc dùng Playwright** (không dùng requests được)
2. Phải set US Zip Code (96150) trước khi check URLs
3. Browser window sẽ mở 2 lần: 1 filter, 1 scrape
4. Multi-selector strategy để handle nhiều layout khác nhau của Amazon

---

## 7. DỰ ÁN 5: MULTI-SOURCE V3 (BESTBUY + AMAZON) 🆕

### 📝 **Mô tả:**
Phiên bản cao cấp nhất - tìm kiếm **ĐỒNG THỜI trên cả BestBuy VÀ Amazon**, gộp kết quả lại và chọn TOP 5 từ pool kết hợp.

### 🆕 **New Features:**
- **Dual-Source Search**: Tìm trên cả BestBuy và Amazon cùng lúc
- **Unified Scraped Deal**: Chuẩn hóa data từ 2 nguồn
- **MultiSourceScannerAgent**: GPT chọn top 5 từ pool kết hợp
- **Source Indicator**: Hiển thị [BestBuy] hoặc [Amazon] cho mỗi deal
- **Clarification Flow**: Vẫn có 3 câu hỏi làm rõ như v2

### 🔄 **Workflow Chi Tiết:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                MULTI-SOURCE V3 WORKFLOW (BESTBUY + AMAZON)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER INPUT: "laptop"                                                        │
│                                                                              │
│  1️⃣ ClarificationAgent.generate_questions(keyword)                          │
│  ├─► GPT-5-mini with Pydantic Structured Output                             │
│  ├─► Generate 3 dynamic questions based on product type                     │
│  │   Q1: "What brand do you prefer?" [Dell, HP, Lenovo, Acer, Any]          │
│  │   Q2: "Primary use case?" [Gaming, Work, Study, General, Any]            │
│  │   Q3: "Budget range?" [Under $500, $500-800, $800-1200, Any]             │
│  └─► Return ClarificationResponse                                            │
│                                                                              │
│  2️⃣ User Answers OR Skip                                                     │
│  ├─► [Clarification]: build_refined_query() → "Acer laptops under $800"     │
│  └─► [Skip]: Use original keyword "laptop"                                   │
│                                                                              │
│  3️⃣ [PARALLEL] Search BOTH Sources                                          │
│  ├─► ThreadPoolExecutor(max_workers=2)                                       │
│  │   ├─► BestBuySearchAgent.search(query, max_urls) → BestBuy URLs          │
│  │   └─► AmazonSearchAgent.search(query, max_urls)  → Amazon URLs           │
│  └─► Total: ~20 URLs (10 BestBuy + 10 Amazon)                                │
│                                                                              │
│  4️⃣ Filter Sale Items                                                        │
│  ├─► BestBuy: filter_sale_urls() → BeautifulSoup (fast)                     │
│  └─► Amazon: filter_amazon_sale_urls_playwright() → Playwright (required)   │
│                                                                              │
│  5️⃣ Scrape Product Details                                                   │
│  ├─► BestBuy: scrape_bestbuy_products() → Playwright                        │
│  └─► Amazon: scrape_amazon_products()  → Playwright                         │
│                                                                              │
│  6️⃣ Combine into Unified Pool                                                │
│  ├─► UnifiedScrapedDeal.from_bestbuy(deal) × N                              │
│  ├─► UnifiedScrapedDeal.from_amazon(deal)  × M                              │
│  └─► Combined pool: N + M products with source indicator                    │
│                                                                              │
│  7️⃣ MultiSourceScannerAgent.scan(unified_deals)                             │
│  ├─► GPT-5-mini với Structured Outputs                                      │
│  ├─► Prompt: "Select 5 best from COMBINED pool (can be from either)"        │
│  └─► Return DealSelection with [BestBuy] or [Amazon] prefix                 │
│                                                                              │
│  8️⃣ EnsembleAgent.price() × 5                                               │
│  └─► Same as other pipelines                                                 │
│                                                                              │
│  9️⃣ Display Results (sorted by discount)                                     │
│  └─► Shows source for each deal: 🟦 BestBuy | 🟠 Amazon                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 📂 **Files liên quan:**

| File | Mô tả |
|------|-------|
| `bestbuy3.py` | 🆕 Gradio Web App cho Multi-Source search |
| `price_agents/bestbuy_deals.py` | BestBuy scraping functions |
| `price_agents/amazon_deals.py` | Amazon scraping functions |
| `price_agents/bestbuy_scanner_agent.py` | BestBuy search & select agents |
| `price_agents/amazon_scanner_agent.py` | Amazon search & select agents |

### 🆕 **UnifiedScrapedDeal Class:**

```python
class UnifiedScrapedDeal:
    """Unified representation of a deal from any source."""
    
    title: str
    brand: Optional[str]
    price: float
    features: str
    url: str
    source: str  # 'BestBuy' or 'Amazon'
    
    @classmethod
    def from_bestbuy(cls, deal: ScrapedBestBuyDeal) -> "UnifiedScrapedDeal":
        return cls(..., source="BestBuy")
    
    @classmethod
    def from_amazon(cls, deal: ScrapedAmazonDeal) -> "UnifiedScrapedDeal":
        return cls(..., source="Amazon")
```

### 🆕 **MultiSourceScannerAgent:**

```python
class MultiSourceScannerAgent(BaseAgent):
    """Select top 5 from combined BestBuy + Amazon pool."""
    
    SYSTEM_PROMPT = """Select 5 most detailed deals from COMBINED list.
    You can select from EITHER source - pick the best overall deals.
    Include [BestBuy] or [Amazon] at the beginning of product_description."""
    
    def scan(self, unified_deals: List[UnifiedScrapedDeal]) -> DealSelection:
        # GPT-5-mini selects from combined pool
        ...
```

### 📊 **Test Results (2026-02-06):**

| Product | Source | Sale $ | Est. $ | Discount |
|---------|--------|--------|--------|----------|
| Laptop 1 | [Amazon] | $399.99 | $548.37 | **$148.38** (27%) |
| Laptop 2 | [BestBuy] | $179.99 | $250.65 | **$70.66** (28%) |
| Laptop 3 | [Amazon] | $149.99 | $225.03 | **$75.04** (33%) |
| Monitor 1 | [BestBuy] | $89.99 | $138.19 | **$48.20** (35%) |
| Accessory | [Amazon] | $49.99 | $107.56 | **$57.57** (54%) |

**Kết luận:** Multi-Source v3 cho phép tìm deals tốt nhất từ CẢ 2 marketplace lớn nhất!

### ⏱️ **Latency:**
```
Multi-Source v3 (10 URLs per source):    ~90-150s
  ├─ Generate questions:                 3-5s
  ├─ Build refined query:                2-3s
  ├─ Search BestBuy + Amazon (parallel): 10-20s
  ├─ Filter BestBuy (BeautifulSoup):     5-10s
  ├─ Filter Amazon (Playwright):         15-25s
  ├─ Scrape BestBuy (Playwright):        10-20s
  ├─ Scrape Amazon (Playwright):         15-25s
  ├─ GPT select top 5:                   3-5s
  └─ Estimate (3 models × 5):            20-30s
```

---

## 8. DỰ ÁN 6: MULTI-SOURCE V5 REFACTORED (search_key.py) 🆕

### 📝 **Mô tả:**
Phiên bản **refactored** của Multi-Source v4, được tách thành 3 files với **Single Responsibility Principle**. Giữ nguyên chức năng nhưng code sạch hơn, dễ maintain hơn.

### 🎯 **Mục tiêu Refactor:**
- ✅ Tách Gradio UI ra riêng (như `price_is_right.py`)
- ✅ Tạo Framework class (như `deal_agent_framework.py`)
- ✅ Tạo Planning Agent (như `planning_agent.py`)
- ✅ Remove try-except không cần thiết
- ✅ Mỗi function ≤ 30 dòng

### 🏗️ **Kiến trúc 3 Files:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SEARCH_KEY.PY ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ search_key.py (~290 lines)                                              ││
│  │ ┌───────────────────────────────────────────────────────────────────┐   ││
│  │ │ App class                                                          │   ││
│  │ │ ├─ __init__()                                                     │   ││
│  │ │ ├─ get_framework() → lazy init                                    │   ││
│  │ │ ├─ generate_questions_handler()                                   │   ││
│  │ │ ├─ submit_answers_handler()                                       │   ││
│  │ │ ├─ skip_handler()                                                 │   ││
│  │ │ ├─ _run_pipeline() → generator for Gradio                        │   ││
│  │ │ └─ run() → Gradio UI                                              │   ││
│  │ └───────────────────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ multi_source_framework.py (~164 lines)                                  ││
│  │ ┌───────────────────────────────────────────────────────────────────┐   ││
│  │ │ MultiSourceFramework class                                        │   ││
│  │ │ ├─ __init__() → ChromaDB init                                    │   ││
│  │ │ ├─ init_agents_as_needed() → lazy agent init                     │   ││
│  │ │ ├─ generate_questions() → delegates to planner                   │   ││
│  │ │ ├─ run() → run pipeline with keyword                             │   ││
│  │ │ ├─ run_with_answers() → run with clarification                   │   ││
│  │ │ └─ send_notification()                                           │   ││
│  │ └───────────────────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ price_agents/multi_source_planning_agent.py (~324 lines)                ││
│  │ ┌───────────────────────────────────────────────────────────────────┐   ││
│  │ │ MultiSourcePlanningAgent class (extends Agent)                    │   ││
│  │ │ ├─ __init__() → init sub-agents                                  │   ││
│  │ │ ├─ generate_questions() / build_refined_query()                  │   ││
│  │ │ ├─ search_both_sources() → Step 1                                │   ││
│  │ │ ├─ filter_sales() → Step 2                                       │   ││
│  │ │ ├─ scrape_and_combine() → Step 3 & 4                             │   ││
│  │ │ ├─ select_top_deals() → Step 5                                   │   ││
│  │ │ ├─ estimate_prices() → Step 6                                    │   ││
│  │ │ └─ plan() → MAIN PIPELINE orchestrator                           │   ││
│  │ └───────────────────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 📂 **Files liên quan:**

| File | Lines | Responsibility |
|------|-------|----------------|
| `search_key.py` | ~290 | Gradio UI (App class) |
| `multi_source_framework.py` | ~164 | Framework orchestrator |
| `price_agents/multi_source_planning_agent.py` | ~324 | Pipeline logic (6 steps) |
| **Tổng** | **~778** | Clean modular code |

### 🔄 **So sánh với bestbuy4.py:**

| Metric | bestbuy4.py | Refactored (3 files) |
|--------|-------------|----------------------|
| **Total Lines** | 673 | 778 (+docstrings) |
| **Number of Files** | 1 | 3 |
| **Longest Function** | ~135 lines | ~30 lines |
| **Try-Except Blocks** | 8 | 3 |
| **Responsibility** | Mixed | Single per file |

### 🆕 **MultiSourcePlanningAgent.plan() - 6 Steps:**

```python
def plan(self, keyword: str, max_urls: int = 10) -> List[Opportunity]:
    """Run the full 6-step pipeline."""
    # Step 1: Search
    bb_urls, az_urls = self.search_both_sources(keyword, max_urls)
    
    # Step 2: Filter
    bb_sales, az_sales = self.filter_sales(bb_urls, az_urls)
    
    # Step 3 & 4: Scrape and Combine
    unified_deals = self.scrape_and_combine(bb_sales, az_sales)
    
    # Step 5: Select top 5
    deal_selection = self.select_top_deals(unified_deals)
    
    # Step 6: Estimate prices
    opportunities = self.estimate_prices(deal_selection)
    
    # Auto-notify if best deal exceeds threshold
    if opportunities and opportunities[0].discount > self.DEAL_THRESHOLD:
        self.messenger.notify(...)
    
    return opportunities
```

### 📊 **Test Results (2026-02-07):**

| Product | Source | Sale $ | Est. $ | Discount |
|---------|--------|--------|--------|----------|
| Dell Laptop | [Amazon] | $519.99 | $822.54 | **$302.55** (37%) 🔥 |
| Dell Business Laptop | [Amazon] | $569.00 | $651.39 | **$82.39** (13%) |
| Acer Laptop | [BestBuy] | $429.99 | $747.14 | **$317.15** (42%) 🔥 |
| HP Laptop | [BestBuy] | $389.99 | $658.06 | **$268.07** (41%) 🔥 |

**Pipeline hoàn tất thành công với auto-notification!**

### ⏱️ **Latency:** (Tương tự v3)
```
~90-150s cho full pipeline
```

---

## 9. CHI TIẾT CÁC AI AGENTS

### 🤖 **A. EnsembleAgent**
**Purpose:** Dự đoán giá trị thực của sản phẩm  
**Model:** 3 models combined  
**Weight:** Frontier (80%) + Specialist (10%) + Neural (10%)

```python
class EnsembleAgent(Agent):
    def price(self, description: str) -> float:
        rewrite = self.preprocessor.preprocess(description)
        specialist = self.specialist.price(rewrite)
        frontier = self.frontier.price(rewrite)
        neural_network = self.neural_network.price(rewrite)
        combined = frontier * 0.8 + specialist * 0.1 + neural_network * 0.1
        return combined
```

---

### 🧠 **B. FrontierAgent**
**Purpose:** RAG-based price estimation  
**Model:** GPT-5.1 + ChromaDB  
**Approach:** 
1. Encode description với SentenceTransformer
2. Query ChromaDB → 5 similar products
3. Build context với similar products + prices
4. GPT-5.1 estimates price based on context

```python
class FrontierAgent(Agent):
    MODEL = "gpt-5.1"
    
    def find_similars(self, description: str):
        vector = self.model.encode([description])
        results = self.collection.query(query_embeddings=vector, n_results=5)
        return results["documents"][0], [m["price"] for m in results["metadatas"][0]]
    
    def price(self, description: str) -> float:
        documents, prices = self.find_similars(description)
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=self.messages_for(description, documents, prices),
        )
        return self.get_price(response.choices[0].message.content)
```

---

### 🎯 **C. SpecialistAgent**
**Purpose:** Fine-tuned model prediction  
**Model:** Llama-3.2-3B (fine-tuned on product data)  
**Platform:** Modal Serverless (T4 GPU)

```python
class SpecialistAgent(Agent):
    def __init__(self):
        Pricer = modal.Cls.from_name("pricer-service", "Pricer")
        self.pricer = Pricer()
    
    def price(self, description: str) -> float:
        return self.pricer.price.remote(description)
```

---

### 🔮 **D. NeuralNetworkAgent**
**Purpose:** Deep NN local inference  
**Model:** Custom PyTorch DNN (1.1GB weights)  
**Architecture:** [384] → [512, 256, 128, 64] → [1]

```python
class NeuralNetworkAgent(Agent):
    def __init__(self):
        self.neural_network = DeepNeuralNetworkInference()
        self.neural_network.setup()
        self.neural_network.load("deep_neural_network.pth")
    
    def price(self, description: str) -> float:
        return self.neural_network.inference(description)
```

---

### 🔍 **E. BestBuySearchAgent**
**Purpose:** Find product URLs on BestBuy  
**Model:** GPT-5-nano  
**Tool:** Brave MCP Server

```python
class BestBuySearchAgent(BaseAgent):
    MODEL = "gpt-5-nano"
    
    async def _search_async(self, keyword: str, max_urls: int = 15) -> List[str]:
        async with MCPServerStdio(params=self.get_brave_params()) as brave_server:
            search_agent = Agent(
                instructions="Search for products on BestBuy...",
                mcp_servers=[brave_server],
                output_type=SearchResults
            )
            result = await Runner.run(search_agent, f"Search for {keyword} on BestBuy")
            return result.final_output.product_urls[:max_urls]
```

---

### 📦 **F. BestBuyScannerAgent**
**Purpose:** Select top 5 deals from scraped data  
**Model:** GPT-5-mini  
**Output:** DealSelection (Pydantic)

```python
class BestBuyScannerAgent(BaseAgent):
    MODEL = "gpt-5-mini"
    
    def scan(self, scraped_deals: List[ScrapedBestBuyDeal]) -> Optional[DealSelection]:
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": self.make_user_prompt(scraped_deals)},
            ],
            response_format=DealSelection,
        )
        return result.choices[0].message.parsed
```

---

### 🤖 **G. ClarificationAgent (NEW in v3)**
**Purpose:** Generate clarification questions + build refined query  
**Model:** GPT-5-mini  
**Output:** ClarificationResponse, RefinedQuery (Pydantic)

*See full implementation in Section 5*

---

### 📣 **H. MessagingAgent**
**Purpose:** Send push notifications  
**Model:** GPT-5-nano (for message crafting)  
**Platform:** Pushover API

```python
class MessagingAgent(Agent):
    MODEL = "gpt-5-nano"
    
    def craft_message(self, description: str, deal_price: float, estimated_true_value: float) -> str:
        response = completion(
            model=self.MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    
    def notify(self, description: str, deal_price: float, estimated_true_value: float, url: str):
        text = self.craft_message(description, deal_price, estimated_true_value)
        self.push(text[:200] + "... " + url)
```

---

### 🧭 **I. AutonomousPlanningAgent**
**Purpose:** Orchestrate entire pipeline with autonomous reasoning  
**Model:** GPT-5.1  
**Tools:** MCP function tools

```python
@function_tool
def scan_the_internet_for_bargains() -> str:
    return planner.scanner.scan(memory=planner.memory).model_dump_json()

@function_tool
def estimate_true_value(description: str) -> str:
    estimate = planner.ensemble.price(description)
    return json.dumps({"description": description, "estimated_true_value": estimate})

@function_tool
def notify_user_of_deal(description: str, deal_price: float, estimated_true_value: float, url: str) -> str:
    planner.messenger.notify(description, deal_price, estimated_true_value, url)
    return "notification sent"

class AutonomousPlanningAgent(BaseAgent):
    MODEL = "gpt-5.1"
    
    task = """
    You are an Autonomous AI Agent that makes use of tools.
    Your mission is to find great deals and notify the user.
    First scan the internet for bargains.
    Then for each deal, estimate its true value.
    Finally, pick the most compelling deal and notify the user.
    """
    
    async def go(self):
        async with MCPServerStdio(params=files_params) as server:
            agent = Agent(
                model=self.MODEL,
                tools=[scan_the_internet_for_bargains, estimate_true_value, notify_user_of_deal],
                mcp_servers=[server],
            )
            reply = await Runner.run(agent, self.task)
        return reply.final_output
```

---

## 7. TECH STACK & DEPENDENCIES

### 🐍 **Core:**
```
Python 3.12+
```

### 📦 **ML/AI:**
| Package | Purpose |
|---------|---------|
| `torch>=2.9.0` | PyTorch cho Deep Neural Network |
| `transformers` | HuggingFace models |
| `sentence-transformers` | Embedding models (all-MiniLM-L6-v2) |
| `openai` | GPT API |
| `litellm` | LLM abstraction layer |
| `agents` | OpenAI Agents SDK with MCP |

### 🗄️ **Data & Storage:**
| Package | Purpose |
|---------|---------|
| `chromadb` | Vector database (400K products) |
| `pandas` | Data processing |
| `scikit-learn` | Feature extraction |
| `pydantic` | Data validation & schemas |

### 🌐 **Web & Scraping:**
| Package | Purpose |
|---------|---------|
| `gradio` | Web UI framework |
| `playwright` | Browser automation |
| `beautifulsoup4` | HTML parsing |
| `feedparser` | RSS parsing |
| `requests` | HTTP client |

### ☁️ **Infrastructure:**
| Package | Purpose |
|---------|---------|
| `modal` | Serverless GPU inference |
| `python-dotenv` | Environment variables |
| `tqdm` | Progress bars |
| `nest_asyncio` | Async handling in Jupyter |

### 📊 **Visualization:**
| Package | Purpose |
|---------|---------|
| `plotly` | Interactive 3D charts |
| `matplotlib` | Static plots |

### 🔔 **External APIs:**
| API | Purpose |
|-----|---------|
| OpenAI | GPT-5.1, GPT-5-mini, GPT-5-nano |
| Groq | Fast preprocessing |
| Modal | Serverless GPU |
| Brave Search | Web search via MCP |
| Pushover | Push notifications |

---

## 8. CẤU TRÚC THƯ MỤC

```
segment4/
├── 📁 price_agents/                        # Core AI Agents
│   ├── agent.py                            # Base Agent class (logging, colors)
│   ├── autonomous_planning_agent.py        # 🤖 Main orchestrator (GPT-5.1 + MCP)
│   ├── planning_agent.py                   # Non-autonomous legacy version
│   ├── scanner_agent.py                    # 📰 RSS scraper (DealNews)
│   ├── ensemble_agent.py                   # 🎯 3-model ensemble coordinator
│   ├── specialist_agent.py                 # 🎓 Fine-tuned LLM (Modal)
│   ├── frontier_agent.py                   # 🧠 GPT-5.1 + RAG (ChromaDB)
│   ├── neural_network_agent.py             # 🔮 Deep NN local
│   ├── deep_neural_network.py              # PyTorch DNN architecture
│   ├── preprocessor.py                     # Text preprocessing (Groq/Ollama)
│   ├── messaging_agent.py                  # 📣 Push notifications
│   ├── deals.py                            # Data models (Deal, Opportunity)
│   ├── bestbuy_deals.py                    # 🛒 BestBuy scraper (Playwright)
│   └── bestbuy_scanner_agent.py            # 🔍 BestBuy search & select
│
├── 📁 products_vectorstore/                # ChromaDB database (400K products)
│   └── chroma.sqlite3
│
├── 📁 test_chuc_nang/                      # Test notebooks (v1)
│   ├── task3.ipynb
│   ├── TASK_BESTBUY_SEARCH.md
│   └── ...
│
├── 📁 test_chuc_nang_v2/                   # Test notebooks (v2)
│   ├── clarification_agent_test.ipynb      # ClarificationAgent test
│   ├── skipflow.ipynb                      # Skip flow test
│   └── PROJECT_STATUS.md                   # Progress tracker
│
├── 📁 sandbox/                             # Output files
│   └── deals.md                            # Deals markdown (MCP writes here)
│
├── 📁 mo_ta_du_an/                         # Documentation
│   └── COMPLETE_PROJECT_DOCUMENTATION.md   # 📄 This file
│
├── 📄 price_is_right.py                    # 🌟 Auto Deal Finder Web App
├── 📄 bestbuy_search.py                    # 🌟 BestBuy Search v1 Web App
├── 📄 bestbuy2.py                          # 🌟 BestBuy Search v2 with Clarification
├── 📄 deal_agent_framework.py              # Framework coordinator
├── 📄 pricer_service2.py                   # Modal serverless LLM definition
├── 📄 evaluator.py                         # Testing & visualization
├── 📄 items.py                             # Data preprocessing utils
├── 📄 testing.py                           # Simple tester
├── 📄 log_utils.py                         # ANSI → HTML color formatting
├── 📄 keep_warm.py                         # Keep Modal warm
├── 📄 memory.json                          # Deals memory
├── 📄 deep_neural_network.pth              # Trained weights (1.1GB)
└── 📄 .env                                 # API keys (not in repo)
```

---

## 9. SETUP & INSTALLATION

### 📋 **Prerequisites:**
- Python 3.12+
- Node.js (for MCP servers - npx)
- GPU optional (có thì tốt, không có vẫn chạy được)

### 🔧 **Step 1: Clone & Virtual Environment**

```bash
cd segment4

# Tạo virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate  # Linux/Mac
# hoặc: .venv\Scripts\activate  # Windows
```

### 📦 **Step 2: Install Dependencies**

```bash
# Option 1: UV (recommended - faster)
uv pip install -r requirements.txt

# Option 2: Regular pip
pip install gradio chromadb sentence-transformers openai torch \
            transformers feedparser beautifulsoup4 requests plotly \
            pydantic python-dotenv litellm modal tqdm scikit-learn \
            agents nest_asyncio playwright

# Install Playwright browsers
playwright install chromium
```

### 🔑 **Step 3: Environment Variables**

Tạo file `.env` trong `segment4/`:

```env
# =========================================
# REQUIRED FOR ALL FEATURES
# =========================================

# OpenAI API (REQUIRED)
OPENAI_API_KEY=sk-your-openai-key

# =========================================
# REQUIRED FOR BESTBUY SEARCH
# =========================================

# Brave Search (REQUIRED for BestBuy search)
BRAVE_API_KEY=your-brave-api-key

# =========================================
# REQUIRED FOR FULL PIPELINE
# =========================================

# Modal (for fine-tuned model)
MODAL_TOKEN_ID=your-modal-id
MODAL_TOKEN_SECRET=your-modal-secret

# HuggingFace (for fine-tuned model)
HF_TOKEN=hf_your_token

# Pushover (for notifications)
PUSHOVER_USER=your-pushover-user
PUSHOVER_TOKEN=your-pushover-token

# =========================================
# OPTIONAL
# =========================================

# Preprocessor (default: groq, alternatives: ollama/llama3.2)
PRICER_PREPROCESSOR_MODEL=groq/openai/gpt-oss-20b

# Groq (for fast preprocessing)
GROQ_API_KEY=your-groq-key

# DeepSeek (alternative to OpenAI)
DEEPSEEK_API_KEY=your-deepseek-key
```

### ☁️ **Step 4: Setup Modal (Fine-tuned LLM)**

```bash
# Login to Modal
modal token new

# Deploy service
modal deploy pricer_service2.py

# Test
modal run pricer_service2.py

# Keep warm (optional - run in background)
python keep_warm.py
```

### 🗄️ **Step 5: Setup ChromaDB**

Nếu chưa có `products_vectorstore/`:

```bash
# Option A: Run preprocessing notebook
jupyter notebook experiment-preprocessing.ipynb
# Run cells to:
# 1. Load training data (train.pkl)
# 2. Encode với SentenceTransformer
# 3. Save to ChromaDB

# Option B: Download pre-built database (if shared)
```

---

## 10. USAGE GUIDE

### 🚀 **Method 1: Auto Deal Finder (RSS)**

```bash
cd segment4
python price_is_right.py
# Or: uv run price_is_right.py
```

**Access:** `http://localhost:7860`

**Features:**
- Auto-refresh mỗi 5 phút
- Hiển thị deals trong table
- 3D vector visualization
- Click row → Send notification
- Real-time logs

---

### 🔍 **Method 2: BestBuy Keyword Search v1**

```bash
cd segment4
python bestbuy_search.py
# Or: uv run bestbuy_search.py
```

**Access:** `http://localhost:7860`

**Usage:**
1. Nhập keyword (ví dụ: "Smart TV", "laptop")
2. Chọn Max URLs (default: 10)
3. Click "🔍 Search"
4. Đợi pipeline chạy (~30-60s)
5. Xem results table
6. (Optional) Click "📱 Send Push Notification"

---

### 🆕 **Method 3: BestBuy v2 with Clarification (Recommended)**

```bash
cd segment4
python bestbuy2.py
# Or: uv run bestbuy2.py
```

**Access:** `http://localhost:7860`

**Usage:**
1. Nhập keyword (ví dụ: "laptop")
2. Chọn Max URLs (default: 10)
3. Click "🤖 Generate Questions"
4. Xem 3 câu hỏi AI tạo ra
5. **Option A (Clarification):**
   - Điền 3 câu trả lời
   - Click "✅ Submit & Search"
6. **Option B (Skip):**
   - Click "⏩ Skip, Search Now"
7. Xem Query Comparison (Original → Refined)
8. Xem real-time logs trong Pipeline Logs
9. Xem results table
10. (Optional) Click "📱 Send Push Notification"

---

### 🎛️ **Method 4: CLI (Framework)**

```bash
cd segment4
python deal_agent_framework.py
```

Chạy 1 lần, không có UI.

---

### 🧪 **Method 5: Testing**

```bash
# Test imports
python -c "from price_agents.ensemble_agent import EnsembleAgent; print('OK')"

# Test evaluator
python evaluator.py

# Test simple pricing
python testing.py

# Jupyter notebooks
jupyter notebook test_chuc_nang/task3.ipynb
jupyter notebook test_chuc_nang_v2/clarification_agent_test.ipynb
```

---

## 11. API KEYS & ENVIRONMENT VARIABLES

### 🔑 **Required API Keys:**

| API | Purpose | Get it from | Free tier |
|-----|---------|-------------|-----------|
| **OPENAI_API_KEY** | GPT models | https://platform.openai.com | Pay per use |
| **BRAVE_API_KEY** | Web search | https://brave.com/search/api | 2000 queries/month |
| **HF_TOKEN** | HuggingFace | https://huggingface.co/settings/tokens | Free |

### 🔐 **Optional API Keys:**

| API | Purpose | Get it from |
|-----|---------|-------------|
| **GROQ_API_KEY** | Fast preprocessing | https://console.groq.com |
| **PUSHOVER_USER/TOKEN** | Push notifications | https://pushover.net |
| **MODAL_TOKEN_ID/SECRET** | Serverless GPU | https://modal.com |
| **DEEPSEEK_API_KEY** | Alternative to OpenAI | https://deepseek.com |

### 💡 **Minimal Setup (BestBuy Search only):**

```env
OPENAI_API_KEY=sk-your-openai-key
BRAVE_API_KEY=your-brave-api-key
```

---

## 12. TROUBLESHOOTING

### ❌ **Common Issues:**

#### **1. Import Error: No module named 'price_agents'**

```bash
cd segment4  # Đảm bảo ở đúng thư mục
export PYTHONPATH=$PWD:$PYTHONPATH  # Linux/Mac
python bestbuy2.py
```

#### **2. ChromaDB Error: Collection not found**

```bash
ls -la products_vectorstore/  # Kiểm tra folder
jupyter notebook experiment-preprocessing.ipynb  # Nếu không có
```

#### **3. Modal Error: Service not found**

```bash
modal deploy pricer_service2.py
modal app list
```

#### **4. Playwright Error: Browser not installed**

```bash
playwright install chromium
```

#### **5. BestBuy Error: No products found**

- Check `BRAVE_API_KEY` trong `.env`
- Try different keywords
- Reduce `max_urls`

#### **6. GPU Out of Memory**

```python
# Trong deep_neural_network.py, force CPU:
self.device = torch.device("cpu")
```

#### **7. Gradio không mở browser**

```python
# Thay trong bestbuy2.py
app.launch(share=False, inbrowser=False)
# Mở manual: http://localhost:7860
```

#### **8. Logs không hiển thị trong UI**

- Đảm bảo `logs_html` trong outputs của `.click()` handlers
- Check `html_for_logs()` function

#### **9. ClarificationAgent không generate questions**

- Check `OPENAI_API_KEY`
- Keyword phải >= 2 characters
- Check console for errors

---

## 13. PERFORMANCE METRICS

### ⏱️ **Latency:**

```
Auto Deal Finder (1 run):              ~30-60s
BestBuy Search v1 (10 URLs):           ~40-80s
BestBuy Search v2 with Clarification:  ~50-90s
  ├─ Generate questions:               3-5s
  ├─ Build refined query:              2-3s
  ├─ Search URLs:                      5-10s
  ├─ Filter sales:                     5-10s
  ├─ Scrape (Playwright):              10-20s
  ├─ Select top 5:                     3-5s
  └─ Estimate (3 models × 5):          20-30s
```

### 💰 **Cost per run (estimated):**

```
GPT-5-mini (clarification + select):   ~$0.01
GPT-5.1 (frontier × 5):                ~$0.05
GPT-5-nano (search + notify):          ~$0.002
Modal (T4 × 5):                        ~$0.02
Groq (preprocessing × 5):              ~$0.001
PyTorch (local):                       $0
Brave Search:                          $0 (free tier)
Pushover:                              $0 (free tier)
────────────────────────────────────────────
Total:                                 ~$0.08-0.10/run
```

### 🎯 **Accuracy:**

```
Average Error:       < $50 (typical)
R² Score:            ~85-90%
Hit Rate:            ~75% (within 20% error)
Clarification boost: +40% discount (68% vs 27% in tests)
```

---

## 14. FUTURE IMPROVEMENTS

### 🚀 **Short-term:**
- [ ] Add caching cho preprocessing results
- [ ] Batch inference để giảm API calls
- [ ] Better error recovery (skip failed URLs)
- [ ] Export results to CSV/Excel
- [ ] Add product category filter

### 🎯 **Medium-term:**
- [ ] Fine-tune ensemble weights (meta-learning)
- [ ] Add more scrapers: Amazon, Walmart, Target
- [ ] User preferences: Brand filter, price range
- [ ] A/B testing framework cho prompts
- [ ] Historical price tracking và trends
- [ ] Multi-language support cho questions

### 🌟 **Long-term:**
- [ ] Distributed system (Kafka + workers)
- [ ] Auto-retrain models weekly
- [ ] Advanced RAG (hybrid search + reranking)
- [ ] Mobile app (iOS/Android)
- [ ] Multi-user support với authentication
- [ ] Cloud deployment (AWS/GCP)
- [ ] Voice-based clarification

---

## 📝 CHANGELOG

### Version 4.0 (2026-02-06) 🆕
- ✅ **NEW:** Amazon Search v1 - Tìm kiếm deals trên Amazon
- ✅ **NEW:** `amazon_search.py` - Gradio app cho Amazon
- ✅ **NEW:** Multi-Source v3 (BestBuy + Amazon combined)
- ✅ **NEW:** `bestbuy3.py` - Gradio app tìm trên cả 2 nguồn
- ✅ **NEW:** `AmazonSearchAgent` - GPT-5-nano + Brave MCP
- ✅ **NEW:** `AmazonScannerAgent` - GPT-5-mini select top 5
- ✅ **NEW:** `MultiSourceScannerAgent` - GPT-5-mini select từ combined pool
- ✅ **NEW:** `UnifiedScrapedDeal` class - Chuẩn hóa data từ 2 nguồn
- ✅ **NEW:** Parallel search với ThreadPoolExecutor
- ✅ **NEW:** Multi-selector fallback cho Amazon scraping
- ✅ **FIX:** Set US Zip Code cho Amazon (96150)
- ✅ **DOCS:** Complete documentation v4.0

### Version 3.0 (2026-02-04)
- ✅ **NEW:** ClarificationAgent for user interaction
- ✅ **NEW:** bestbuy2.py with clarification flow
- ✅ **NEW:** Pydantic schemas: ClarificationQuestion, ClarificationResponse, RefinedQuery
- ✅ **NEW:** Skip flow option
- ✅ **NEW:** Query comparison display
- ✅ **FIX:** Max URLs input
- ✅ **FIX:** Real-time logs display
- ✅ **DOCS:** Complete documentation update

### Version 2.0 (2026-02-03)
- ✅ Added BestBuy Keyword Search
- ✅ New agents: BestBuySearchAgent, BestBuyScannerAgent
- ✅ New scraping: Playwright-based product scraper
- ✅ New UI: bestbuy_search.py with real-time logging

### Version 1.0 (2025-12)
- ✅ Auto Deal Finder from RSS
- ✅ Ensemble Agent with 3 models
- ✅ Modal serverless deployment
- ✅ Gradio UI with 3D visualization
- ✅ Push notifications via Pushover

---

## 🙏 CREDITS

- **OpenAI**: GPT-5.1, GPT-5-mini, GPT-5-nano
- **Meta**: Llama-3.2-3B (fine-tuned)
- **ChromaDB**: Vector database
- **Modal**: Serverless GPU infrastructure
- **Gradio**: Web UI framework
- **Playwright**: Browser automation
- **HuggingFace**: Model hub
- **Brave**: Search API

---

## 📞 SUPPORT

Nếu gặp vấn đề:
1. Đọc lại [Troubleshooting](#14-troubleshooting)
2. Check logs trong Gradio UI
3. Run test scripts
4. Check API keys trong `.env`
5. Verify Modal service running

---

**🎉 END OF DOCUMENTATION**

*Last updated: 2026-02-06*  
*Version: 4.0 (with Multi-Source: BestBuy + Amazon)*  
*For questions or contributions, contact the AI Engineering Team.*

