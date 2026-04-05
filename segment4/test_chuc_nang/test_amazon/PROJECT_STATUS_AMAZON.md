# 🛒 AMAZON SCRAPER - PROJECT STATUS

> **Ngày cập nhật:** 2026-02-06 11:17  
> **File notebook:** `test_amazon/amazon_search_2_5_toi.ipynb`  
> **Gradio App:** `segment4/amazon_search.py` ✅ **WORKING!**  
> **Trạng thái:** ✅ **HOÀN THÀNH & TESTED** - Gradio App đã chạy thành công!

---

## 📋 MỤC TIÊU DỰ ÁN

Mở rộng hệ thống cào dữ liệu deals từ **BestBuy** sang **Amazon**. Pipeline tương tự BestBuy:

```
1️⃣ Search URLs (Brave MCP) → 2️⃣ Filter Sale Items → 3️⃣ Scrape Details (Playwright) 
→ 4️⃣ Select Top Deals (GPT) → 5️⃣ Estimate Prices (EnsembleAgent)
```

---

## ✅ TỔNG KẾT CÔNG VIỆC ĐÃ HOÀN THÀNH

### 📊 Pipeline Overview

| Step | Function | Model/Tool | Status |
|------|----------|------------|--------|
| 1️⃣ Search URLs | `AmazonSearchAgent.search()` | Brave MCP + GPT-5-nano | ✅ Done |
| 2️⃣ Filter Sale | `filter_amazon_sale_urls_playwright()` | Playwright + US Zip Code | ✅ Done |
| 3️⃣ Scrape Details | `scrape_amazon_products()` | Playwright + Multi-selector | ✅ Done |
| 4️⃣ Select Top 5 | `AmazonScannerAgent.scan()` | GPT-5-mini Structured Output | ✅ Done |
| 5️⃣ Estimate Price | `EnsembleAgent.price()` | Frontier + Specialist + Neural | ✅ Done |

---

## 📌 Step 1: AmazonSearchAgent - Tìm URLs sản phẩm

**Trạng thái:** ✅ HOÀN THÀNH

**Mô tả:**
- Sử dụng Brave MCP Server để tìm kiếm Amazon product URLs
- Model: GPT-5-nano
- Trả về list URLs với format `/dp/ASIN`
- Giới hạn ~10 URLs mỗi query (Brave Free Tier)

**Test result:**
```
Keyword: "Smart TV"
Found: 10 product URLs
Format: https://www.amazon.com/*/dp/XXXXXXXXXX ✓
```

---

## 📌 Step 2: Filter Sale Items - Lọc sản phẩm đang giảm giá

**Trạng thái:** ✅ HOÀN THÀNH

**Thách thức đã giải quyết:**
- ❌ `requests` bị Amazon block (CAPTCHA/Robot check)
- ✅ **Giải pháp:** Playwright + Set US Zip Code qua UI

**Sale Indicators:**
| Selector | Mô tả |
|----------|-------|
| `span.savingsPercentage` | Phần trăm giảm giá (e.g., "-15%") |
| `span.basisPrice` | Chứa "List Price:" |
| `[data-a-strike="true"]` | Giá gốc bị gạch ngang |

**Configuration:**
- US Zip Code: `96150` (California)
- Phải set location trước khi check URLs

---

## 📌 Step 3: Scrape Product Details - Cào chi tiết sản phẩm

**Trạng thái:** ✅ HOÀN THÀNH

**Class đã tạo:** `ScrapedAmazonDeal`
- Attributes: `title`, `brand`, `price`, `features`, `url`
- Methods: `__repr__()`, `describe()`

**Chiến lược Multi-Selector Fallback:**
```python
TITLE_SELECTORS = ["#productTitle", "h1.product-title-word-break", ...]
BRAND_SELECTORS = ["#bylineInfo", "a#bylineInfo", "#brand", ...]
FEATURES_SELECTORS = ["#feature-bullets ul", "#productDescription p", ...]
```

**Lý do dùng Fallback:**
- Amazon có hàng trăm triệu sản phẩm với layout khác nhau
- Mỗi category (TV, Laptop, Giày...) có format riêng
- Một số sản phẩm thiếu fields → graceful degradation

**Test result:**
```
Scraped: 2/2 products successfully
- Title: ✓ (extracted)
- Brand: ✓ (extracted)  
- Price: ✓ (from Step 2)
- Features: ✓ (1000-1500 chars)
```

---

## 📌 Step 4: AmazonScannerAgent - Chọn top deals

**Trạng thái:** ✅ HOÀN THÀNH

**Mô tả:**
- Model: GPT-5-mini
- Input: `List[ScrapedAmazonDeal]`
- Output: `DealSelection` (reuse từ `price_agents.deals`)
- Chọn tối đa 5 deals có description tốt nhất

**Test result:**
```
Input: 2 scraped deals
Output: 2 deals selected with refined descriptions
```

---

## 📌 Step 5: EnsembleAgent - Estimate Prices

**Trạng thái:** ✅ HOÀN THÀNH

**Mô tả:**
- Reuse `EnsembleAgent` từ `price_agents/ensemble_agent.py`
- 3 Models: Frontier (80%) + Specialist (10%) + Neural (10%)
- Output: `List[Opportunity]` với estimate và discount

**Test result (2026-02-05):**

| Product | Sale Price | Est. Value | Discount | % |
|---------|------------|------------|----------|---|
| Amazon Fire TV 43" 4K | $199.99 | $286.54 | **$86.55** | 30.2% |
| INSIGNIA 24" LED FHD | $69.99 | $126.43 | **$56.44** | 44.6% |

---

## 📊 SO SÁNH VỚI BESTBUY PIPELINE

| Component | BestBuy | Amazon | Notes |
|-----------|---------|--------|-------|
| Search Agent | `BestBuySearchAgent` | `AmazonSearchAgent` | Same pattern |
| Filter Sale | `filter_sale_urls()` | `filter_amazon_sale_urls_playwright()` | Amazon cần Playwright |
| Scrape | `scrape_bestbuy_products()` | `scrape_amazon_products()` | Multi-selector fallback |
| Scanner | `BestBuyScannerAgent` | `AmazonScannerAgent` | Same pattern |
| Ensemble | `EnsembleAgent` | `EnsembleAgent` | **Reuse 100%** |
| Deal Model | `ScrapedBestBuyDeal` | `ScrapedAmazonDeal` | Same structure |

---

## 📂 CẤU TRÚC FILE HIỆN TẠI

```
segment4/
├── amazon_search.py                    # ✅ NEW! Gradio UI cho Amazon search
├── test_amazon/
│   ├── amazon_search_2_5_toi.ipynb     # ✅ Notebook hoàn chỉnh (tested)
│   ├── amazon_search_2_4_toi.ipynb     # Old version
│   └── PROJECT_STATUS_AMAZON.md        # File này
│
├── price_agents/
│   ├── amazon_deals.py                 # ✅ NEW! ScrapedAmazonDeal, filter, scrape
│   ├── amazon_scanner_agent.py         # ✅ NEW! AmazonSearchAgent, AmazonScannerAgent
│   ├── bestbuy_deals.py                # Reference: BestBuy scraper
│   ├── bestbuy_scanner_agent.py        # Reference: BestBuy agents
│   ├── ensemble_agent.py               # ✅ Reuse cho Amazon
│   └── deals.py                        # ✅ Reuse: Deal, DealSelection, Opportunity
│
└── test_chuc_nang/
    └── bestbuy_3-1-2026-toi-ok.ipynb   # Reference: BestBuy notebook
---

## 🔜 CÔNG VIỆC TIẾP THEO

### ✅ Priority 1: Migrate Code to Python Files - DONE!

- [x] Tạo `price_agents/amazon_deals.py`
  - `ScrapedAmazonDeal` class
  - `set_amazon_us_location()`
  - `is_on_sale_amazon_playwright()`
  - `filter_amazon_sale_urls_playwright()`
  - `scrape_amazon_products()`

- [x] Tạo `price_agents/amazon_scanner_agent.py`
  - `AmazonSearchAgent` class
  - `AmazonScannerAgent` class

### ✅ Priority 2: Create Gradio App - DONE!

- [x] Tạo `amazon_search.py` - Gradio UI cho Amazon search

---

## 🆕 NHIỆM VỤ CHIỀU 06/02: Amazon v2 với ClarificationAgent

> **Mục tiêu:** Thêm ClarificationAgent cho Amazon, tương tự như `bestbuy2.py`
> **Reference:** `bestbuy2.py`, `test_chuc_nang_v2/PROJECT_STATUS.md`

### � Mô tả
Thay vì search trực tiếp với keyword (ví dụ: "laptop"), hệ thống sẽ:
1. **Hỏi 3 câu hỏi làm rõ** (brand, use case, budget...)
2. **Xây dựng refined query** từ câu trả lời
3. **Search với query tối ưu** → Kết quả tốt hơn

### 🔄 Workflow Amazon v2 (Target)
```
User: "laptop"
     ↓
🤖 ClarificationAgent.generate_questions("laptop")
     ↓
Q1: "Preferred brand?" → [Dell, HP, Lenovo, Acer, Any]
Q2: "Primary use?" → [Gaming, Work, Study, Any]
Q3: "Budget range?" → [Under $500, $500-800, $800-1200, Any]
     ↓
User answers: Acer, for students, under $800
     ↓
🤖 ClarificationAgent.build_refined_query()
     ↓
Refined: "Acer laptops for students under $800"
     ↓
[Existing Pipeline: Search → Filter → Scrape → Select → Estimate]
```

### 📌 Tasks

#### Step 1: Test trong Notebook (ƯU TIÊN)
- [ ] Tạo file `test_amazon/amazon_clarification_test.ipynb`
- [ ] Copy `ClarificationAgent` từ `bestbuy2.py` (reuse 100%)
- [ ] Test với Amazon pipeline:
  - Input: "Smart TV"
  - Trả lời 3 câu hỏi
  - Xem refined query
  - Chạy full pipeline với refined query
- [ ] So sánh kết quả: Clarification vs Direct search

#### Step 2: Tạo Gradio App `amazon2.py`
- [ ] Copy structure từ `bestbuy2.py`
- [ ] Thay BestBuy functions → Amazon functions
- [ ] UI Components:
  - Keyword input + Max URLs
  - "🤖 Generate Questions" button
  - 3 Dropdown/Text fields cho câu trả lời
  - "✅ Submit & Search" button
  - "⏩ Skip, Search Now" button
  - Query comparison display
  - Real-time logs
  - Results table

#### Step 3: (Optional) Optimization
- [ ] Caching: Lưu results vào memory.json
- [ ] Error handling: Retry logic cho failed URLs
- [ ] Parallel scraping: Tăng tốc với multiple pages
- [ ] Merge Amazon + BestBuy vào 1 app với dropdown chọn source

### 📊 Expected Results (dựa trên BestBuy v2)

| Flow | Discount Improvement |
|------|---------------------|
| Direct Search | ~27% discount |
| With Clarification | ~68% discount |
| **Improvement** | **+40%** |

### 📁 Files sẽ tạo

```
segment4/
├── amazon2.py                              # 🆕 Gradio App v2 với Clarification
└── test_amazon/
    ├── amazon_clarification_test.ipynb     # 🆕 Test notebook
    └── PROJECT_STATUS_AMAZON.md            # This file
```

### 🔗 Reference Files

| File | Mô tả |
|------|-------|
| `bestbuy2.py` | Reference cho UI structure & ClarificationAgent |
| `test_chuc_nang_v2/PROJECT_STATUS.md` | Kết quả test BestBuy v2 |
| `test_chuc_nang_v2/clarification_agent_test.ipynb` | Test notebook BestBuy |
| `amazon_search.py` | Amazon v1 (base để build v2) |

---

## ⚠️ LƯU Ý QUAN TRỌNG

1. **Amazon Anti-bot:** 
   - `requests` bị block → **phải dùng Playwright**
   - Cần set US Zip Code qua UI, không chỉ geolocation

2. **Location:**
   - US Zip Code: `96150` (California)
   - Phải set location trước khi check bất kỳ URL nào

3. **Multi-selector Strategy:**
   - Amazon có nhiều layout khác nhau
   - Dùng fallback selectors để handle đa dạng format
   - Nếu field không có → để trống, KHÔNG crash

4. **Brave API Limit:**
   - Free tier: ~10 results mỗi query
   - Sau filter còn ~2-5 sale items (đủ dùng)

---

## 🔧 ENVIRONMENT SETUP

**API Keys cần thiết (trong .env):**
```
BRAVE_API_KEY=...      # ✅ Đang dùng
OPENAI_API_KEY=...     # ✅ Đang dùng
```

**Dependencies:**
```
playwright          # Browser automation
agents             # OpenAI Agents SDK
pydantic           # Data schemas
chromadb           # Vector database
```

**Playwright browser:**
```bash
playwright install chromium
```

---

## 📝 CHANGELOG

### 2026-02-06 (Sáng)
- ✅ **BUG FIX:** `AmazonSearchAgent` gọi `self.log()` nhưng không inherit từ `BaseAgent`
  - Fix: Thêm `class AmazonSearchAgent(BaseAgent)` và `color = BaseAgent.GREEN`
  - File: `price_agents/amazon_scanner_agent.py`
- ✅ **TESTED:** Gradio App `amazon_search.py` đã chạy thành công!

### 2026-02-05 (Tối)
- ✅ Created `price_agents/amazon_deals.py` - Scraping functions
- ✅ Created `price_agents/amazon_scanner_agent.py` - Search & Scanner agents
- ✅ Created `amazon_search.py` - Gradio Web App
- ✅ Full pipeline tested trong notebook

---

**🎉 AMAZON PIPELINE HOÀN THÀNH & TESTED!**

*Cập nhật lần cuối: 2026-02-06 11:17*
