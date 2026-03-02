# 🤖 AI Price Intelligence System — DACN3

> **Hệ thống AI tự động săn deal & ước lượng giá sản phẩm từ BestBuy và Amazon**

---

## 📌 Giới thiệu dự án

Đây là **đồ án chuyên ngành (DACN3)** xây dựng một hệ thống AI đa tác nhân (Multi-Agent System) có khả năng:

- 🔍 **Tìm kiếm song song** sản phẩm trên BestBuy và Amazon theo từ khóa
- 🏷️ **Lọc sản phẩm đang giảm giá** (on sale) theo thời gian thực
- 🧠 **Ước lượng giá trị thực** bằng Ensemble AI gồm 3 models kết hợp
- 📲 **Thông báo tự động** qua Pushover khi phát hiện deal tốt
- 🤖 **Chạy tự động hoàn toàn** (Autonomous mode) hoặc theo yêu cầu người dùng

---

## 🗂️ Cấu trúc dự án

```
tech2ai/
│
├── segment4/                          # 🎯 DỰ ÁN CHÍNH
│   │
│   ├── search_key.py                  # Entry point — Multi-Source Deal Finder (Gradio UI)
│   ├── price_is_right.py              # Entry point — Autonomous Deal Hunter (Gradio UI)
│   ├── multi_source_framework.py      # Framework điều phối trung tâm
│   ├── deal_agent_framework.py        # Framework cho autonomous mode
│   │
│   ├── price_agents/                  # 🤖 Tất cả AI Agents
│   │   ├── multi_source_planning_agent.py   # Pipeline 6 bước (BestBuy + Amazon)
│   │   ├── ensemble_agent.py                # Kết hợp 3 models dự đoán giá
│   │   ├── frontier_agent.py                # GPT-5.1 + RAG (ChromaDB)
│   │   ├── specialist_agent.py              # Fine-tuned Llama-3.2-3B (Modal)
│   │   ├── neural_network_agent.py          # PyTorch DNN (local)
│   │   ├── bestbuy_deals.py                 # Scraping BestBuy
│   │   ├── amazon_deals.py                  # Scraping Amazon
│   │   ├── bestbuy_scanner_agent.py         # Search BestBuy (Brave MCP)
│   │   ├── amazon_scanner_agent.py          # Search Amazon (Brave MCP)
│   │   ├── scanner_agent.py                 # RSS feed scanner
│   │   ├── messaging_agent.py               # Push notification (Pushover)
│   │   ├── planning_agent.py                # Simple planning agent
│   │   ├── autonomous_planning_agent.py     # Autonomous planning agent
│   │   ├── preprocessor.py                  # Text normalization
│   │   ├── deep_neural_network.py           # PyTorch model architecture
│   │   ├── deals.py                         # Data classes
│   │   └── agent.py                         # Base class
│   │
│   ├── bestbuy_untils/                # 🛠️ Utilities
│   │   ├── clarification_agent.py     # Sinh câu hỏi làm rõ nhu cầu
│   │   ├── unified_deal.py            # Chuẩn hóa deal từ 2 nguồn
│   │   ├── multi_source_scanner_agent.py  # Chọn top 5 từ pool
│   │   └── gradio_helpers.py          # Helper cho Gradio UI
│   │
│   ├── mo_ta_du_an/                   # 📚 Tài liệu
│   │   ├── DOCUMENTATION_SEARCHKEY.md
│   │   ├── DOCUMENTATION_PRICE_IS_RIGHT.md
│   │   └── COMPLETE_PROJECT_DOCUMENTATION.md
│   │
│   └── products_vectorstore/          # ChromaDB (800K products) — không up GitHub
│
├── tailieu/                           # 📄 Báo cáo DACN
├── week7/                             # Fine-tune Llama notebook
└── day_mcp/                           # MCP experiments
```

---

## 🔄 Hai ứng dụng chính

### 1. 🔍 Multi-Source Deal Finder (`search_key.py`)

Người dùng **nhập từ khóa** → AI tìm kiếm và chọn deal tốt nhất từ BestBuy + Amazon.

```
[Nhập keyword: "laptop"]
       │
       ▼
[ClarificationAgent] → 3 câu hỏi làm rõ nhu cầu
       │
       ▼
[Step 1] Search song song BestBuy + Amazon (Brave Search API)
[Step 2] Filter sản phẩm đang sale (BeautifulSoup + Playwright)
[Step 3] Scrape chi tiết sản phẩm (Playwright)
[Step 4] Gộp vào unified pool
[Step 5] GPT-5-mini chọn top 5 deals tốt nhất
[Step 6] EnsembleAgent ước lượng giá trị thực
       │
       ▼
[Hiển thị bảng kết quả + Push Notification nếu discount > $100]
```

### 2. 🤖 Autonomous Deal Hunter (`price_is_right.py`)

Hệ thống **chạy tự động mỗi 5 phút**, tự scan RSS feeds từ DealNews.com.

```
[Khởi động] → [Tự động scan DealNews RSS mỗi 5 phút]
       │
       ▼
[ScannerAgent] → GPT-5-mini chọn top 5 deals
[EnsembleAgent] → Ước lượng giá trị thực
[MessagingAgent] → Push notification nếu discount > $50
[Lưu vào memory.json] → Tránh duplicate
```

---

## 🧠 Ensemble AI — 3 Models Kết Hợp

| Model | Trọng số | Mô tả |
|-------|----------|-------|
| **FrontierAgent** | 80% | GPT-5.1 + RAG (ChromaDB 800K products) |
| **SpecialistAgent** | 10% | Fine-tuned Llama-3.2-3B chạy trên Modal GPU |
| **NeuralNetworkAgent** | 10% | PyTorch DNN 10-layer (ResidualBlocks) chạy local |

**Công thức:**
```
estimated_price = frontier × 0.8 + specialist × 0.1 + neural × 0.1
discount = estimated_price - sale_price
```

---

## ⚙️ Cài đặt và Chạy

### Yêu cầu hệ thống

- Python 3.10+
- Node.js 18+ (cho MCP servers)
- CUDA GPU (khuyến nghị, cho PyTorch)
- Chromium browser (cho Playwright)

### 1. Cài đặt dependencies

```bash
cd segment4

# Cài Python packages
uv sync

# Cài Playwright browsers
uv run playwright install
```

### 2. Cấu hình file `.env`

Tạo file `.env` trong thư mục `segment4/`:

```env
# Bắt buộc
OPENAI_API_KEY=sk-...
BRAVE_API_KEY=BSA-...

# Tùy chọn (cho push notification)
PUSHOVER_USER=...
PUSHOVER_TOKEN=...

# Tùy chọn (preprocessor model)
PRICER_PREPROCESSOR_MODEL=ollama/llama3.2
```

### 3. Chạy ứng dụng

**Multi-Source Deal Finder (tìm theo keyword):**
```bash
cd segment4
uv run search_key.py
```

**Autonomous Deal Hunter (tự động mỗi 5 phút):**
```bash
cd segment4
uv run price_is_right.py
```

Ứng dụng mở tại: `http://127.0.0.1:7860`

---

## 📊 Kết quả mẫu

**Keyword:** `"Dell laptop"` | **Thời gian:** ~90-120 giây

| Sản phẩm | Nguồn | Giá Sale | Ước lượng | Discount |
|----------|-------|----------|-----------|----------|
| Dell Inspiron 15.6" i5 512GB | Amazon | $639.99 | $945.86 | $305.87 🔥 |
| Dell XPS 14 OLED i7 32GB | BestBuy | $999.99 | $1,450.00 | $450.01 🔥 |

---

## 💰 Chi phí ước tính mỗi lần chạy

| Component | Model | Chi phí |
|-----------|-------|---------|
| Search Agents | GPT-5-nano | ~$0.001 |
| Clarification | GPT-5-nano | ~$0.001 |
| Scan top 5 | GPT-5-mini | ~$0.002 |
| Estimate (5 deals) | GPT-5.1 | ~$0.005 |
| Preprocess | Llama local | $0 |
| **Tổng cộng** | | **~$0.01/lần** |

---

## 🛠️ Tech Stack

| Lớp | Công nghệ |
|-----|-----------|
| **UI** | Gradio |
| **Search** | Brave Search API + MCP |
| **Scraping** | Playwright, BeautifulSoup |
| **LLM** | OpenAI GPT-5.1 / GPT-5-mini / GPT-5-nano |
| **Fine-tuned Model** | Llama-3.2-3B (LoRA, 4-bit NF4) trên Modal |
| **Neural Network** | PyTorch DNN (10 layers, ResidualBlocks) |
| **Vector DB** | ChromaDB (800K products) |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 |
| **Notification** | Pushover API |
| **Package Manager** | uv |

---

## 📚 Tài liệu chi tiết

- [`DOCUMENTATION_SEARCHKEY.md`](segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md) — Chi tiết về Multi-Source Deal Finder
- [`DOCUMENTATION_PRICE_IS_RIGHT.md`](segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md) — Chi tiết về Autonomous Deal Hunter
- [`COMPLETE_PROJECT_DOCUMENTATION.md`](segment4/mo_ta_du_an/COMPLETE_PROJECT_DOCUMENTATION.md) — Tài liệu tổng quan đầy đủ

---

## 👤 Tác giả

**Nguyễn Minh Hiếu** — [@Sunny-sunnyy](https://github.com/Sunny-sunnyy)

Đồ án chuyên ngành — 2026
