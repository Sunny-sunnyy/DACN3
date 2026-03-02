# 📚 LỘ TRÌNH ĐỌC CODE - SEARCH_KEY.PY PROJECT

> **Ngày cập nhật:** 2026-02-07  
> **Version:** Refactored v4.1  
> **Mục đích:** Hướng dẫn đọc hiểu code dự án Multi-Source Deal Finder (Refactored)

---

## 🎯 TỔNG QUAN

Dự án `search_key.py` là một ứng dụng Gradio tìm kiếm deals từ **BestBuy + Amazon** đồng thời, sử dụng AI để:
1. Làm rõ nhu cầu user (ClarificationAgent)
2. Tìm kiếm và lọc sản phẩm đang sale
3. Chọn top 5 deals tốt nhất (MultiSourceScannerAgent)
4. Dự đoán giá trị thực (EnsembleAgent)

### 🆕 ĐÃ REFACTOR TỪ `bestbuy4.py`

| Trước (bestbuy4.py) | Sau (Refactored) |
|---------------------|------------------|
| 1 file lớn (673 dòng) | 3 files nhỏ |
| Mixed responsibility | Single responsibility |
| 8 try-except blocks | 3 try-except blocks |

---

## 📁 CẤU TRÚC THƯ MỤC (REFACTORED)

```
segment4/
├── search_key.py                        # 🎯 GRADIO UI (App class) ~290 dòng
├── multi_source_framework.py            # 📦 FRAMEWORK ORCHESTRATOR ~164 dòng
│
├── price_agents/
│   ├── multi_source_planning_agent.py   # 📦 PIPELINE LOGIC (NEW) ~324 dòng
│   ├── agent.py                         # Base class cho agents
│   ├── deals.py                         # Pydantic schemas
│   ├── bestbuy_deals.py                 # BestBuy scraping
│   ├── bestbuy_scanner_agent.py         # BestBuy search + select
│   ├── amazon_deals.py                  # Amazon scraping
│   ├── amazon_scanner_agent.py          # Amazon search + select
│   ├── ensemble_agent.py                # Ensemble 3 models
│   └── messaging_agent.py               # Push notification
│
├── bestbuy_untils/                      # Supporting modules
│   ├── clarification_agent.py           # Agent tạo câu hỏi làm rõ
│   ├── unified_deal.py                  # Class gộp deals từ nhiều nguồn
│   ├── multi_source_scanner_agent.py    # Agent chọn top 5 từ pool
│   └── gradio_helpers.py                # Helper functions cho UI
│
└── products_vectorstore/                # ChromaDB với 400K sản phẩm
```

---

## 🚀 LỘ TRÌNH ĐỌC CODE (4 PHASES)

### 📖 PHASE 1: HIỂU DATA STRUCTURES (30 phút)

**Đọc trước để hiểu các data class được sử dụng xuyên suốt project.**

| Thứ tự | File | Nội dung cần hiểu |
|--------|------|-------------------|
| 1️⃣ | `price_agents/deals.py` | `Deal`, `DealSelection`, `Opportunity` - Pydantic schemas |
| 2️⃣ | `price_agents/bestbuy_deals.py` | `ScrapedBestBuyDeal` class |
| 3️⃣ | `price_agents/amazon_deals.py` | `ScrapedAmazonDeal` class |
| 4️⃣ | `bestbuy_untils/unified_deal.py` | `UnifiedScrapedDeal` - gộp deals |

**Mục tiêu:** Hiểu flow dữ liệu:
```
ScrapedBestBuyDeal  ─┐
                     ├─→ UnifiedScrapedDeal ─→ Deal ─→ Opportunity
ScrapedAmazonDeal   ─┘
```

---

### 📖 PHASE 2: HIỂU AI AGENTS (45 phút)

**Đọc để hiểu cách sử dụng AI trong pipeline.**

| Thứ tự | File | Nội dung cần hiểu |
|--------|------|-------------------|
| 1️⃣ | `price_agents/agent.py` | `BaseAgent` class - logging, colors |
| 2️⃣ | `bestbuy_untils/clarification_agent.py` | `ClarificationAgent` - câu hỏi + refined query |
| 3️⃣ | `bestbuy_untils/multi_source_scanner_agent.py` | `MultiSourceScannerAgent` - chọn top 5 |
| 4️⃣ | `price_agents/ensemble_agent.py` | `EnsembleAgent` - 3 models dự đoán giá |
| 5️⃣ | `price_agents/messaging_agent.py` | `MessagingAgent` - push notification |

**Key concepts:**
- **MCP (Model Context Protocol)**: LLM gọi external tools (Brave Search)
- **Structured Outputs**: GPT trả về Pydantic objects
- **Ensemble**: 80% Frontier + 10% Specialist + 10% Neural

---

### 📖 PHASE 3: HIỂU REFACTORED ARCHITECTURE (60 phút)

**Đây là phần quan trọng nhất - hiểu cách code được tổ chức.**

| Thứ tự | File | Pattern tham khảo | Nội dung |
|--------|------|-------------------|----------|
| 1️⃣ | `price_agents/multi_source_planning_agent.py` | `planning_agent.py` | **CORE PIPELINE** - 6 bước |
| 2️⃣ | `multi_source_framework.py` | `deal_agent_framework.py` | **FRAMEWORK** - ChromaDB, lazy init |
| 3️⃣ | `search_key.py` | `price_is_right.py` | **GRADIO UI** - App class |

**Cách đọc `multi_source_planning_agent.py`:**
```
1. __init__() - Khởi tạo sub-agents
2. generate_questions() / build_refined_query() - Clarification
3. search_both_sources() - Step 1: Search parallel
4. filter_sales() - Step 2: Filter
5. scrape_and_combine() - Step 3 & 4: Scrape + Combine
6. select_top_deals() - Step 5: GPT select
7. estimate_prices() - Step 6: EnsembleAgent
8. plan() - MAIN PIPELINE - orchestrates all steps
```

---

### 📖 PHASE 4: HIỂU GRADIO APP (30 phút)

**Cuối cùng, đọc UI layer.**

| Thứ tự | File | Nội dung |
|--------|------|----------|
| 1️⃣ | `bestbuy_untils/gradio_helpers.py` | `QueueHandler`, `html_for_logs()`, `opportunities_to_table()` |
| 2️⃣ | `search_key.py` | **App class** với các event handlers |

**Cách đọc `search_key.py`:**
```
1. App.__init__() - Lazy framework init
2. get_framework() - Pattern như price_is_right.py
3. Event handlers:
   - generate_questions_handler()
   - submit_answers_handler()
   - skip_handler()
   - push_notification_handler()
4. _run_pipeline() - Generator cho real-time updates
5. run() - Gradio UI definition
```

---

## 🔄 PIPELINE FLOW (TỔNG HỢP)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: USER INPUT                                                      │
│ User nhập keyword (VD: "laptop")                                        │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: CLARIFICATION (Optional)                                        │
│ ClarificationAgent tạo 3 câu hỏi → User trả lời → Refined query         │
│ VD: "laptop" → "Acer laptops for students under $800"                   │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PIPELINE in MultiSourcePlanningAgent.plan()                             │
│                                                                          │
│ Step 1: search_both_sources() - BestBuy + Amazon parallel               │
│ Step 2: filter_sales() - BeautifulSoup (BB) + Playwright (AZ)           │
│ Step 3-4: scrape_and_combine() - Playwright → UnifiedScrapedDeal        │
│ Step 5: select_top_deals() - GPT-5-mini → DealSelection                 │
│ Step 6: estimate_prices() - EnsembleAgent → List[Opportunity]           │
│                                                                          │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ RESULTS + AUTO-NOTIFICATION                                              │
│ Hiển thị table sorted by discount                                        │
│ Auto-notify if discount > $100                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ ARCHITECTURE COMPARISON

### Trước (bestbuy4.py - 1 file lớn):
```
bestbuy4.py (673 lines)
├── imports
├── global variables
├── init_agents()
├── pipeline functions (search_*, filter_*, scrape_*, estimate_*)
├── clarification handlers
├── do_search_pipeline() - 135 lines!
├── run_search_pipeline()
├── push notification
└── Gradio UI
```

### Sau (Refactored - 3 files):
```
search_key.py (290 lines)          ← Gradio UI only (App class)
├── App class
├── Event handlers
└── run()

multi_source_framework.py (164 lines)   ← Orchestrator
├── ChromaDB init
├── Lazy agent init
└── High-level methods

price_agents/multi_source_planning_agent.py (324 lines)   ← Pipeline logic
├── MultiSourcePlanningAgent class
├── 6-step pipeline methods
└── plan() orchestrates all
```

---

## 💡 TIPS KHI ĐỌC CODE

### 1. Bắt đầu từ entry point
```bash
python search_key.py
```
Xem app chạy, rồi trace ngược lại code.

### 2. Focus vào `MultiSourcePlanningAgent.plan()`
Đây là hàm quan trọng nhất chứa toàn bộ 6-step pipeline.

### 3. Hiểu pattern
- `search_key.py` → `price_is_right.py` (App class pattern)
- `multi_source_framework.py` → `deal_agent_framework.py` (Framework pattern)
- `multi_source_planning_agent.py` → `planning_agent.py` (Agent pattern)

### 4. Hiểu Structured Outputs
```python
result = openai.chat.completions.parse(
    model="gpt-5-mini",
    response_format=DealSelection,  # Pydantic class
)
selection = result.choices[0].message.parsed  # Đã là object
```

---

## 📊 THỜI GIAN ĐỌC DỰ KIẾN

| Phase | Thời gian | Mức độ |
|-------|-----------|--------|
| Phase 1: Data Structures | 30 phút | ⭐ Cơ bản |
| Phase 2: AI Agents | 45 phút | ⭐⭐ Trung bình |
| Phase 3: Refactored Architecture | 60 phút | ⭐⭐⭐ Nâng cao |
| Phase 4: Gradio App | 30 phút | ⭐⭐ Trung bình |
| **Tổng** | **~2.75 giờ** | |

---

## 📝 CHECKLIST ĐỌC CODE

- [ ] Phase 1: Hiểu Deal, DealSelection, Opportunity
- [ ] Phase 1: Hiểu UnifiedScrapedDeal và factory methods
- [ ] Phase 2: Hiểu ClarificationAgent workflow
- [ ] Phase 2: Hiểu EnsembleAgent 3 models
- [ ] Phase 3: Hiểu MultiSourcePlanningAgent.plan() 6 bước
- [ ] Phase 3: Hiểu MultiSourceFramework lazy init
- [ ] Phase 4: Hiểu App class event handlers
- [ ] Phase 4: Hiểu _run_pipeline() generator
- [ ] Đã chạy thử app

---

*Created: 2026-02-07*  
*Refactored from: READING_ROADMAP_BESTBUY4.md*  
*Author: AI Assistant*
