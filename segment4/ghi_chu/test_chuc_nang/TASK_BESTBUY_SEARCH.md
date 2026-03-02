# 🎯 BESTBUY KEYWORD SEARCH FEATURE

> **Cập nhật lần cuối:** 2026-02-02 21:42 (Chủ Nhật)
> **Trạng thái:** Task 1 & 2 hoàn thành ✅ | Task 3 & 4 sẽ làm ngày mai

---

## 📋 MÔ TẢ DỰ ÁN

### Dự án gốc: "The Price is Right" (`segment4/`)
Đây là **Autonomous AI Agent Framework** tự động săn deal với workflow:
1. 🔍 Quét deals từ RSS feeds (DealNews)
2. 🤖 Dự đoán giá trị thực bằng **EnsembleAgent** (3 models: GPT-5.1 RAG, Preprocessor, SpecialistAgent)
3. 📊 Tính discount = Estimated Price - Sale Price
4. 🔔 Thông báo khi tìm thấy deal tốt (Pushover)

### Tính năng mới đang phát triển:
Cho phép **user nhập keyword** (ví dụ: "Smart TV", "laptop") để tìm sản phẩm cụ thể trên **BestBuy**, thay vì chỉ quét RSS tự động.

---

## ✅ TIẾN ĐỘ CÔNG VIỆC

### 📅 Ngày 02/02/2026 (Hôm nay) - HOÀN THÀNH Task 1 & 2

| Task | Mô tả | Trạng thái |
|------|-------|------------|
| Task 1 | `price_agents/bestbuy_deals.py` | ✅ DONE |
| Task 2 | `price_agents/bestbuy_scanner_agent.py` | ✅ DONE |
| Task 3 | `bestbuy_search.py` (Gradio App) | ⏳ Ngày mai |
| Task 4 | Test full workflow | ⏳ Ngày mai |

---

## � NHỮNG GÌ ĐÃ HOÀN THÀNH

### ✅ Task 1: `price_agents/bestbuy_deals.py`
**File mới tạo** chứa:

```python
# Classes & Functions đã implement:
class ScrapedBestBuyDeal:
    """Lưu dữ liệu thô từ Playwright scraping"""
    title: str
    brand: Optional[str]
    price: float
    features: str
    url: str
    def describe(self) -> str  # Format cho LLM

def is_on_sale(url: str) -> bool:
    """Kiểm tra sản phẩm có đang sale không (BeautifulSoup)"""

def filter_sale_urls(urls: List[str]) -> List[str]:
    """Lọc URLs chỉ giữ sản phẩm đang khuyến mãi"""

async def scrape_bestbuy_products(urls: List[str]) -> List[ScrapedBestBuyDeal]:
    """Cào dữ liệu chi tiết với Playwright (headless=False)"""
```

### ✅ Task 2: `price_agents/bestbuy_scanner_agent.py`
**File mới tạo** chứa:

```python
class BestBuySearchAgent(Agent):
    """Tìm BestBuy product URLs từ keyword bằng Brave MCP"""
    MODEL = "gpt-5-nano"
    def search(keyword: str, max_urls: int = 15) -> List[str]

class BestBuyScannerAgent(Agent):
    """Chọn 5 deals tốt nhất bằng GPT-5-mini"""
    MODEL = "gpt-5-mini"
    def scan(scraped_deals: List[ScrapedBestBuyDeal]) -> DealSelection
```

### 📝 Full Pipeline Test - Thành công 100%
**Notebook test:** `segment4/test_chuc_nang/bestbuy_3-1-2026-toi.ipynb`

**Kết quả Cell 10 (Full Pipeline):**
```
============================================================
FULL PIPELINE TEST: BestBuy Keyword Search
============================================================

Step 1: Input 10 URLs
Step 2: Filtering sale items... → 10/10 products on sale
Step 3: Scraping with Playwright... → 10/10 products scraped
Step 4: Selecting best deals with GPT-5-mini... → 5 top deals selected

✅ FINAL RESULTS:
🏷️ Deal 1: TCL 65" QM8K - $999.99
🏷️ Deal 2: TCL 65" QM7K - $797.99
🏷️ Deal 3: TCL 55" QM6K - $449.99
🏷️ Deal 4: TCL 65" QM5K - $449.99
🏷️ Deal 5: TCL 55" QM5K - $329.99
```

### 💰 Kết quả dự đoán giá (từ notebook trước):
| Sản phẩm | Sale Price | Estimated | Discount |
|----------|------------|-----------|----------|
| Samsung 55" U7900 | $279.99 | $593.48 | **$313.49** 🏆 |
| TCL 65" QM8K | $999.99 | $1160.44 | **$160.45** |
| Westinghouse 24" HD | $79.99 | $155.95 | **$75.96** |

---

## ⏳ NHỮNG GÌ SẼ LÀM NGÀY MAI (03/02/2026)

### 📌 Task 3: Tạo `bestbuy_search.py` (Standalone Gradio App)
Gradio UI với các tính năng:

```
┌───────────────────────────────────────────────────────────┐
│  🔍 BestBuy Deal Finder                                   │
├───────────────────────────────────────────────────────────┤
│  Keyword: [Smart TV________________] [🔍 Search]          │
├───────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Product         │ Sale $ │ Est. $ │ Discount │ URL  │  │
│  ├─────────────────┼────────┼────────┼──────────┼──────┤  │
│  │ Samsung 55" U7  │ $279   │ $593   │ $313 🏆  │ Link │  │
│  │ TCL 65" QM8K    │ $999   │ $1160  │ $161     │ Link │  │
│  │ ...             │ ...    │ ...    │ ...      │ ...  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  [📱 Send Push Notification for Selected Deal]            │
└───────────────────────────────────────────────────────────┘
```

**Workflow trong Gradio:**
1. User nhập keyword → Click Search
2. BestBuySearchAgent.search() → Tìm URLs
3. filter_sale_urls() → Lọc sale items
4. scrape_bestbuy_products() → Cào dữ liệu
5. BestBuyScannerAgent.scan() → Chọn 5 deals
6. EnsembleAgent.price() → Dự đoán giá
7. Hiển thị bảng kết quả
8. Click row → Push notification

### 📌 Task 4: Test Full Workflow
- Chạy `python bestbuy_search.py`
- Test với nhiều keywords: "laptop", "headphones", "camera"
- Verify discount calculation
- Test push notification

---

## 📂 CẤU TRÚC FILES

```
segment4/
├── price_agents/
│   ├── bestbuy_deals.py          # ✅ MỚI - ScrapedBestBuyDeal, scraper
│   ├── bestbuy_scanner_agent.py  # ✅ MỚI - SearchAgent, ScannerAgent
│   ├── deals.py                  # Có sẵn - Deal, DealSelection, Opportunity
│   ├── ensemble_agent.py         # Có sẵn - EnsembleAgent (3 models)
│   ├── scanner_agent.py          # Có sẵn - ScannerAgent (RSS)
│   ├── messaging_agent.py        # Có sẵn - Push notification
│   └── agent.py                  # Có sẵn - Base Agent class
├── bestbuy_search.py             # ⏳ TODO - Standalone Gradio App
├── price_is_right.py             # Có sẵn - Auto-scan app
├── test_chuc_nang/
│   ├── TASK_BESTBUY_SEARCH.md    # 📋 File này
│   ├── bestbuy_3-1-2026-toi.ipynb  # ✅ Notebook test Task 1 & 2
│   └── ScrapedBestBuyDeal.ipynb  # ✅ Notebook thử nghiệm gốc
└── products_vectorstore/         # ChromaDB cho RAG
```

---

## � CÁCH SỬ DỤNG CODE ĐÃ VIẾT

```python
import asyncio
from price_agents.bestbuy_deals import (
    ScrapedBestBuyDeal,
    filter_sale_urls,
    scrape_bestbuy_products
)
from price_agents.bestbuy_scanner_agent import (
    BestBuySearchAgent,
    BestBuyScannerAgent
)
from price_agents.ensemble_agent import EnsembleAgent
from price_agents.deals import Opportunity

# Step 1: Search URLs
search_agent = BestBuySearchAgent()
urls = search_agent.search("Smart TV", max_urls=10)

# Step 2: Filter sale items
sale_urls = filter_sale_urls(urls)

# Step 3: Scrape with Playwright
scraped_deals = await scrape_bestbuy_products(sale_urls)

# Step 4: Select top 5 deals
scanner = BestBuyScannerAgent()
deal_selection = scanner.scan(scraped_deals)

# Step 5: Estimate prices
ensemble = EnsembleAgent()
for deal in deal_selection.deals:
    estimate = ensemble.price(deal)
    opportunity = Opportunity(deal, estimate)
    print(f"{deal.product_description[:50]}...")
    print(f"  Sale: ${deal.price} | Est: ${estimate:.2f} | Discount: ${opportunity.discount:.2f}")
```

---

## ⚠️ LƯU Ý KỸ THUẬT

1. **Working directory**: Phải chạy từ `segment4/` để load được model files
2. **Virtual environment**: Sử dụng `.venv` của project
3. **Playwright**: Sử dụng `headless=False` để tránh bị block
4. **Brave API**: Cần có `BRAVE_API_KEY` trong `.env`
5. **Price $0.0**: Một số sản phẩm có thể scrape price = 0, code đã tự động loại bỏ

---

## 📚 FILES CẦN ĐỌC ĐỂ LẤY CONTEXT

1. **File này**: `segment4/test_chuc_nang/TASK_BESTBUY_SEARCH.md`
2. **Module mới**: `segment4/price_agents/bestbuy_deals.py`
3. **Module mới**: `segment4/price_agents/bestbuy_scanner_agent.py`
4. **Notebook test**: `segment4/test_chuc_nang/bestbuy_3-1-2026-toi.ipynb`
5. **Reference Gradio app**: `segment4/price_is_right.py`

---

## 🎯 MỤC TIÊU CUỐI CÙNG

Tạo một **Gradio web app** cho phép user:
1. Nhập keyword tìm kiếm (ví dụ: "laptop", "Smart TV")
2. Xem danh sách deals với **giá sale** và **giá ước lượng**
3. Sắp xếp theo **discount** (ước lượng - sale)
4. Nhận **push notification** khi tìm thấy deal tốt

**Kết quả mong đợi:** Tìm được deals có discount cao (ví dụ: Samsung 55" U7900 với discount $313!)

---

*Hẹn gặp lại ngày mai! 🚀*
