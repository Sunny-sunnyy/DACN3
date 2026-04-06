# SEARCH_KEY.PY - Multi-Source Deal Finder

## Tong quan

**Ten:** Multi-Source Deal Finder (search_key.py)
**Cap nhat:** 2026-04-06
**Ngon ngu:** Python 3.12 + `uv`

Ung dung web tim kiem va danh gia deals tot nhat tu **BestBuy** va **Amazon** dong thoi. Pipeline 4 buoc: search song song (curl_cffi) -> chon top 3 (GPT-5-nano) -> uoc luong gia (Ensemble 3 models) -> hien thi ket qua.

---

## Dau vao va Dau ra

**Dau vao:**

| Input | Mo ta | Vi du |
|-------|-------|-------|
| Keyword | Tu khoa san pham | "laptop", "Smart TV", "headphones" |
| Max URLs | So san pham toi da moi nguon | 3-20 (mac dinh: 6) |

**Dau ra:**

| Output | Mo ta |
|--------|-------|
| Bang ket qua | Top 3 deals: Ten, Gia sale, Gia uoc luong, Discount, URL (clickable) |
| Pipeline logs | Real-time logs hien thi tien trinh tung buoc |
| Push Notification | Thong bao qua Pushover (tuy chon) |

---

## Cau truc thu muc

```
segment4/
|
|-- search_key.py                        # ENTRY POINT - Gradio UI
|-- multi_source_framework.py            # FRAMEWORK - ChromaDB init, lazy agent loading
|
|-- price_agents/                        # TAT CA AGENTS
|   |-- __init__.py
|   |-- agent.py                         # Base class (ANSI logging)
|   |-- deals.py                         # Data models: Deal, DealSelection, Opportunity, ScrapedDeal
|   |
|   |-- multi_source_planning_agent.py   # CORE - Pipeline 4 buoc
|   |-- ensemble_agent.py                # Ket hop 3 models du doan gia
|   |-- messaging_agent.py               # Push notification (Pushover + GPT-5-nano)
|   |
|   |-- bestbuy_deals.py                 # BestBuy: curl_cffi + internal APIs
|   |-- amazon_deals.py                  # Amazon: curl_cffi + HTML parsing
|   |
|   |-- frontier_agent.py               # GPT-5.1 + RAG (ChromaDB)
|   |-- specialist_agent.py             # Fine-tuned Llama-3.2-3B (Modal)
|   |-- neural_network_agent.py         # PyTorch DNN local
|   |-- deep_neural_network.py          # DNN model class definition
|   |-- preprocessor.py                 # LiteLLM text preprocessing
|   |
|   |-- amazon_scanner_agent.py         # DEPRECATED - da xoa code
|   |-- bestbuy_scanner_agent.py        # DEPRECATED - khong duoc import boi pipeline
|   |-- autonomous_planning_agent.py    # Chi dung boi price_is_right.py
|   |-- planning_agent.py              # Chi dung boi price_is_right.py
|   |-- scanner_agent.py               # Chi dung boi price_is_right.py
|
|-- bestbuy_untils/                      # UTILITIES (ten thu muc co chu y)
|   |-- multi_source_scanner_agent.py    # GPT-5-nano chon top 3 tu pool
|   |-- unified_deal.py                  # Chuan hoa deal tu 2 nguon
|   |-- gradio_helpers.py                # Queue logging, HTML formatters
|   |-- clarification_agent.py           # Sinh cau hoi lam ro (hien KHONG dung trong pipeline)
|
|-- products_vectorstore/                # ChromaDB - 800K+ san pham da embed
|   |-- chroma.sqlite3
|
|-- deep_neural_network.pth              # PyTorch DNN model weights
|-- log_utils.py                         # ANSI -> HTML color formatter
|-- .env                                 # API keys (khong commit)
```

---

## Cach doc code (Reading Order)

Doc theo thu tu nay de hieu toan bo luong hoat dong:

```
1. search_key.py              -- Gradio UI, event handlers, threading
   |
2. multi_source_framework.py  -- ChromaDB init, goi planner.plan()
   |
3. multi_source_planning_agent.py  -- Pipeline 4 buoc (doc ky file nay)
   |
   |-- 4a. bestbuy_deals.py   -- curl_cffi + BestBuy APIs
   |-- 4b. amazon_deals.py    -- curl_cffi + Amazon HTML parsing
   |-- 4c. unified_deal.py    -- Chuan hoa ScrapedBestBuyDeal/ScrapedAmazonDeal -> UnifiedScrapedDeal
   |-- 4d. multi_source_scanner_agent.py  -- GPT-5-nano chon top 3
   |-- 4e. ensemble_agent.py  -- Goi 3 models (doc tiep frontier/specialist/neural)
   |
5. deals.py                   -- Data models (Deal, Opportunity, DealSelection)
6. agent.py                   -- Base class voi ANSI logging
```

---

## Pipeline 4 buoc

`MultiSourcePlanningAgent.plan(keyword, max_urls)` dieu phoi:

```
User nhap keyword
    |
    v
Step 1: search_and_scrape()
    |-- _bestbuy_pipeline() ----+  ThreadPoolExecutor
    |-- _amazon_pipeline()  ----+  (chay song song)
    |                           |
    v                           v
    List[ScrapedBestBuyDeal]    List[ScrapedAmazonDeal]
    |
    v
Step 2: combine()
    |-- UnifiedScrapedDeal.from_bestbuy()
    |-- UnifiedScrapedDeal.from_amazon()
    |
    v
    List[UnifiedScrapedDeal]  (pool chung tu 2 nguon)
    |
    v
Step 3: select_top_deals()
    |-- MultiSourceScannerAgent.scan()  (GPT-5-nano, Structured Outputs)
    |
    v
    DealSelection (top 3 Deal objects)
    |
    v
Step 4: estimate_prices()
    |-- EnsembleAgent.price() cho moi deal:
    |   |-- Preprocessor (LiteLLM) -> rewrite text
    |   |-- FrontierAgent (GPT-5.1 + RAG 5 similar products)  -> 80%
    |   |-- SpecialistAgent (Llama-3.2-3B fine-tuned, Modal)   -> 10%
    |   |-- NeuralNetworkAgent (PyTorch DNN local)             -> 10%
    |   |-- combined = frontier*0.8 + specialist*0.1 + neural*0.1
    |
    v
    List[Opportunity]  (sorted by discount desc)
    |
    v
Auto-notify neu discount > $100 (MessagingAgent -> Pushover)
```

---

## Chi tiet tung file

### Tang UI

#### `search_key.py` (~187 dong)

Entry point. Gradio web app.

| Thanh phan | Chuc nang |
|------------|-----------|
| `App.__init__()` | Lazy init framework, luu keyword + max_urls |
| `App.get_framework()` | Tao `MultiSourceFramework` lan dau goi |
| `App.search_handler()` | Validate input, goi `_run_pipeline()` |
| `App._run_pipeline()` | Generator: chay pipeline trong thread rieng, yield log updates cho Gradio |
| `App.push_notification_handler()` | Gui push notification cho deal tai index |
| `App.run()` | Build Gradio Blocks UI, bind events |

**Ky thuat:** Dung `threading.Thread` + `queue.Queue` de stream logs real-time. Worker thread chay pipeline, main thread poll queue va yield cho Gradio.

---

#### `multi_source_framework.py` (~91 dong)

Orchestrator. Quan ly resources.

| Thanh phan | Chuc nang |
|------------|-----------|
| `MultiSourceFramework.__init__()` | Load .env, init ChromaDB (800K+ products), planner = None |
| `init_agents_as_needed()` | Lazy init `MultiSourcePlanningAgent` (tao 1 lan, giu suot session) |
| `run(keyword, max_urls)` | Goi `planner.plan()`, luu ket qua |
| `send_notification(index)` | Gui push notification cho deal tai index |

---

### Tang Pipeline

#### `multi_source_planning_agent.py` (~197 dong)

**File quan trong nhat.** Chua toan bo logic pipeline 4 buoc.

| Method | Step | Chuc nang |
|--------|------|-----------|
| `_bestbuy_pipeline()` | 1 | Goi `search_filter_scrape_bestbuy()` |
| `_amazon_pipeline()` | 1 | Goi `search_filter_scrape_amazon()` |
| `search_and_scrape()` | 1 | `ThreadPoolExecutor(max_workers=2)` chay 2 pipeline song song |
| `combine()` | 2 | Convert sang `UnifiedScrapedDeal` |
| `select_top_deals()` | 3 | Goi `MultiSourceScannerAgent.scan()` |
| `estimate_prices()` | 4 | Goi `EnsembleAgent.price()` cho moi deal |
| `plan()` | ALL | Chay 4 buoc, log timer, auto-notify |

**Dependencies:** `bestbuy_deals`, `amazon_deals`, `unified_deal`, `multi_source_scanner_agent`, `ensemble_agent`, `messaging_agent`

---

### Tang Scraping

#### `bestbuy_deals.py` (~193 dong)

Scrape BestBuy bang `curl_cffi` + internal APIs. **KHONG dung Playwright**.

| Ham | Chuc nang |
|-----|-----------|
| `_init_session()` | curl_cffi session (impersonate Chrome) + bypass country selection |
| `search_bestbuy(session, keyword)` | GET `/site/searchpage.jsp`, parse Apollo SSR cache -> list `{skuId, pdpUrl}` |
| `get_price_blocks(session, sku_ids)` | GET `/api/3.0/priceBlocks` (batch) -> price, brand, name, onSale |
| `get_product_details(session, sku_id)` | GET `/api/v2/product/<skuId>` -> features, clean URL |
| `search_filter_scrape_bestbuy(keyword, max_results)` | **Pipeline gop:** search -> filter onSale -> scrape details -> `List[ScrapedBestBuyDeal]` |

**Class:** `ScrapedBestBuyDeal` (title, brand, price, features, url)

**Thoi gian:** ~4-8s cho 6 san pham sale

---

#### `amazon_deals.py` (~257 dong)

Scrape Amazon bang `curl_cffi` + HTML parsing. **KHONG dung Playwright**.

| Ham | Chuc nang |
|-----|-----------|
| `init_amazon_session()` | curl_cffi session (impersonate Chrome) + POST set ZIP 96150 |
| `parse_search_results(html)` | Parse search page HTML -> list product dicts (ASIN, title, price, specs) |
| `search_amazon(session, keyword)` | GET search page, check CAPTCHA, parse results |
| `scrape_product_page(session, url)` | **Approach B fallback:** GET product page -> #feature-bullets, #bylineInfo |
| `search_filter_scrape_amazon(keyword, max_results)` | **Pipeline gop:** init -> search -> filter on_sale -> scrape features -> `List[ScrapedAmazonDeal]` |

**Class:** `ScrapedAmazonDeal` (title, brand, price, features, url)

**2 Approach:**

| Approach | Khi nao | Toc do |
|----------|---------|--------|
| A: Search page only | specs >= 50 chars (laptop, TV, phone) | ~0s them |
| B: GET product page | specs < 50 chars (headphones, accessories) | ~2-3s/product |

**Thoi gian:** ~2s (Approach A), ~14s (Approach B)

---

### Tang Utilities

#### `bestbuy_untils/unified_deal.py` (~133 dong)

Chuan hoa deals tu 2 nguon ve 1 format chung.

| Method | Chuc nang |
|--------|-----------|
| `UnifiedScrapedDeal.from_bestbuy(deal)` | Convert `ScrapedBestBuyDeal` -> unified (source="BestBuy") |
| `UnifiedScrapedDeal.from_amazon(deal)` | Convert `ScrapedAmazonDeal` -> unified (source="Amazon") |
| `describe()` | Format cho LLM prompt (Source, Title, Brand, Price, Features, URL) |

---

#### `bestbuy_untils/multi_source_scanner_agent.py` (~91 dong)

Chon top 3 deals tu pool chung.

| Thanh phan | Chuc nang |
|------------|-----------|
| `MODEL` | `gpt-5-nano` |
| `scan(unified_deals)` | GPT-5-nano + Structured Outputs -> `DealSelection` (top 3) |
| `reasoning_effort` | `"minimal"` (nhanh, re) |

**Prompt:** Yeu cau GPT chon 3 deals co description chi tiet nhat, prefix [BestBuy] hoac [Amazon].

---

#### `bestbuy_untils/gradio_helpers.py` (~184 dong)

Helper functions cho Gradio UI.

| Ham | Chuc nang |
|-----|-----------|
| `QueueHandler` | Custom logging handler, dua logs vao queue |
| `setup_logging(log_queue)` | Cau hinh root logger dung QueueHandler |
| `html_for_logs(log_data)` | Convert log messages -> styled HTML (dark theme) |
| `opportunities_to_html(opps)` | Convert opportunities -> HTML table voi URL clickable |
| `format_questions_html(questions)` | Format clarification questions (hien KHONG dung) |

---

#### `bestbuy_untils/clarification_agent.py`

Sinh 3 cau hoi lam ro nhu cau nguoi dung. **Hien KHONG duoc goi trong pipeline** (da bo clarification flow). Chi duoc import boi `gradio_helpers.py` de lay class `ClarificationQuestion`.

---

### Tang AI Estimation

#### `ensemble_agent.py` (~41 dong)

Ket hop 3 models du doan gia.

```
EnsembleAgent.price(description):
    rewrite = Preprocessor.preprocess(description)
    frontier = FrontierAgent.price(rewrite)       # 80%
    specialist = SpecialistAgent.price(rewrite)   # 10%
    neural = NeuralNetworkAgent.price(rewrite)    # 10%
    return frontier * 0.8 + specialist * 0.1 + neural * 0.1
```

| Model | Class | Weight | Resource |
|-------|-------|--------|----------|
| Frontier | `FrontierAgent` | 80% | OpenAI GPT-5.1 + ChromaDB RAG (5 similar products) |
| Specialist | `SpecialistAgent` | 10% | Fine-tuned Llama-3.2-3B tren Modal (remote call) |
| Neural Network | `NeuralNetworkAgent` | 10% | PyTorch DNN local (`deep_neural_network.pth`) |

**Luu y:** 3 models hien chay **sequential**. Se toi uu parallel trong tuong lai (Step 4 cua plan_fix.md).

---

#### `preprocessor.py` (~49 dong)

Lam sach text truoc khi estimate. Dung LiteLLM.

| Thanh phan | Chuc nang |
|------------|-----------|
| `MODEL` | `PRICER_PREPROCESSOR_MODEL` env var, default `ollama/llama3.2` |
| `preprocess(text)` | Rewrite text thanh format: Title, Category, Brand, Description, Details |

---

#### `messaging_agent.py` (~73 dong)

Gui push notification qua Pushover API.

| Method | Chuc nang |
|--------|-----------|
| `push(text)` | POST Pushover API |
| `craft_message(...)` | GPT-5-nano viet message vui, FOMO |
| `notify(description, price, estimate, url)` | Craft message + push |
| `alert(opportunity)` | Format va push (dung boi price_is_right.py) |

---

### Tang Base va Data Models

#### `agent.py` (~33 dong)

Base class cho tat ca agents. Cung cap ANSI color-coded logging.

```python
class Agent:
    RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = ...
    name: str
    color: str
    def log(self, message):  # logging.info voi color code
```

---

#### `deals.py` (~152 dong)

Data models. Bao gom ca logic RSS fetch (dung boi `price_is_right.py`).

| Class | Dung boi | Fields |
|-------|----------|--------|
| `ScrapedDeal` | price_is_right.py (RSS) | category, title, summary, url, details, features |
| `Deal` (Pydantic) | Ca 2 apps | product_description, price, url |
| `DealSelection` (Pydantic) | Ca 2 apps | deals: List[Deal] |
| `Opportunity` (Pydantic) | Ca 2 apps | deal, estimate, discount |

---

## Lien ket giua cac files

```
search_key.py
    |
    v
multi_source_framework.py
    |                     \
    v                      v
multi_source_planning_agent.py          deals.py (Opportunity)
    |
    +-- bestbuy_deals.py ---------> ScrapedBestBuyDeal
    +-- amazon_deals.py ----------> ScrapedAmazonDeal
    |                                    |
    +-- unified_deal.py <--------- from_bestbuy() / from_amazon()
    |                                    |
    +-- multi_source_scanner_agent.py    v
    |       |                       UnifiedScrapedDeal
    |       v
    |   DealSelection (top 3 Deal)
    |
    +-- ensemble_agent.py
    |       |-- preprocessor.py (LiteLLM)
    |       |-- frontier_agent.py (GPT-5.1 + ChromaDB)
    |       |-- specialist_agent.py (Modal Llama)
    |       |-- neural_network_agent.py (PyTorch DNN)
    |       v
    |   float (estimated price)
    |
    +-- messaging_agent.py (Pushover)
    |
    v
List[Opportunity] -> Gradio HTML table
```

---

## Setup va Chay

### Yeu cau

- Python 3.12, `uv` package manager
- API keys: `OPENAI_API_KEY` (bat buoc), `PUSHOVER_USER` + `PUSHOVER_TOKEN` (tuy chon)
- ChromaDB vectorstore da co san (800K+ products)

### Cai dat

```bash
cd tech2ai
uv sync
```

### Chay

```bash
cd segment4
uv run search_key.py
# Mo browser tai http://127.0.0.1:7860
```

### Environment Variables (`.env` trong `segment4/`)

```env
OPENAI_API_KEY=sk-xxx              # Bat buoc
PUSHOVER_USER=xxx                  # Tuy chon (push notification)
PUSHOVER_TOKEN=xxx                 # Tuy chon
PRICER_PREPROCESSOR_MODEL=ollama/llama3.2  # Tuy chon (default)
```

---

## Thoi gian thuc thi (uoc tinh)

```
Total: ~70-100s (tuy keyword va so san pham sale)

  |-- Step 1: Search+Filter+Scrape (parallel)  ~6s
  |     |-- BestBuy (curl_cffi + APIs)          ~4-8s
  |     |-- Amazon (curl_cffi + HTML)           ~2-14s
  |
  |-- Step 2: Combine                           <1s
  |
  |-- Step 3: Select top 3 (GPT-5-nano)        ~5-10s
  |
  |-- Step 4: Estimate (3 models x 3 deals)    ~40-60s
```

---

## Luu y ky thuat

- `curl_cffi` voi `impersonate="chrome"` la BAT BUOC cho ca BestBuy va Amazon tu WSL2
- BestBuy product pages bi block tu WSL2 (HTTP/2 + Akamai CDN) -> dung internal APIs thay vi scrape
- Amazon: set ZIP 96150 qua POST API de co gia USD
- `ThreadPoolExecutor(max_workers=2)` chay BestBuy + Amazon song song
- Structured Outputs: `response_format=DealSelection` dam bao GPT tra ve JSON hop le
- Log streaming: `QueueHandler` -> `queue.Queue` -> Gradio yield moi 0.1s
- Auto-notify: neu deal tot nhat co discount > $100, tu dong gui Pushover

---

*Cap nhat: 2026-04-06*
