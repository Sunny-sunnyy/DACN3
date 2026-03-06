# 🎯 GAMEPLAN — AI Price Intelligence System (DACN3)

> **Tài liệu Ngữ cảnh Chính dành cho các Trợ lý AI (Master Context Document)**
> **Phiên bản:** 1.0 — Tháng 3, 2026
> **Tác giả:** Phạm Minh Hiếu ([@Sunny-sunnyy](https://github.com/Sunny-sunnyy))
> **Cập nhật lần cuối:** 2026-03-05

---

## 1. Tổng quan dự án

### 1.1 Mục đích cốt lõi

Đây là **đồ án tốt nghiệp (DACN3 — Đồ Án Chuyên Ngành 3)** xây dựng một **Hệ thống Đa Tác tử (Multi-Agent System) bằng AI** để săn deal sản phẩm thông minh và ước tính giá. Hệ thống tự động tìm kiếm, trích xuất dữ liệu (scrape), phân tích và ước lượng giá trị thị trường thực tế của sản phẩm từ **BestBuy** và **Amazon**, sau đó thông báo cho người dùng về các deal cực tốt.

### 1.2 Đối tượng mục tiêu

| Thuộc tính           | Chi tiết                                                       |
| -------------------- | ------------------------------------------------------------ |
| **Người dùng**       | Sinh viên ngành Kỹ thuật AI (AI/ML/DL)             |
| **Hệ điều hành**     | Linux (WSL2 trên Windows)                                      |
| **IDE**              | VS Code với các extension Cursor / Copilot / Claude            |
| **Package Manager**  | **`uv`** (chính, bắt buộc), `npm`/`npx` cho các MCP server   |
| **Phiên bản Python** | 3.12+                                                        |
| **GPU**              | Khuyến nghị GPU có CUDA (có thể chuyển sang MPS → CPU)       |

### 1.3 Sản phẩm hoàn chỉnh

Hai **ứng dụng web Gradio** đầy đủ chức năng:

1. **Multi-Source Deal Finder** (`search_key.py`) — Tìm kiếm theo từ khóa do người dùng cung cấp trên BestBuy + Amazon cùng lúc, với sự trợ giúp của AI đặt câu hỏi nhằm làm rõ nhu cầu để tối ưu tìm kiếm.
2. **Autonomous Deal Hunter** (`price_is_right.py`) — Tác tử hoàn toàn tự động, chạy mỗi 5 phút, quét các RSS feed từ DealNews.com, ước lượng giá trị sản phẩm và tự động gửi thông báo tải về thiết bị các deal có mức giá hời.

### 1.4 Các tính năng chính

- 🔍 **Tìm kiếm đa nguồn song song** trên BestBuy & Amazon qua Brave Search API + MCP
- 🤖 **Clarification Agent** — Tự động sinh ra 3 câu hỏi thông minh để làm rõ ý định của người dùng trước khi tìm kiếm
- 🏷️ **Lọc khuyến mãi theo thời gian thực** bằng BeautifulSoup (BestBuy) và Playwright (Amazon)
- 🧠 **Dự báo Giá Đa Mô hình (Ensemble AI Price Estimation)** — Sự kết hợp của 3 mô hình: GPT-5.1 RAG (80%) + Fine-tuned Llama (10%) + PyTorch DNN (10%)
- 📲 **Thông báo tự động** qua Pushover API cho các deal đạt ngưỡng giảm giá mục tiêu
- 🔄 **Chế độ tự động (Autonomous mode)** — Quét định kỳ kết hợp cơ chế loại bỏ trùng lặp qua `memory.json`
- 📊 **Trực quan hoá t-SNE 3D** cho không gian vector sản phẩm bằng ChromaDB

---

## 2. Cấu trúc thư mục

```
tech2ai/                                    # Thư mục gốc của dự án
│
├── .env                                    # ⚠️ API keys (GITIGNORED — KHÔNG BAO GIỜ COMMIT)
├── .gitignore                              # Quy tắc bỏ qua file .env, .pth, vectorstore, v.v.
├── .python-version                         # Đóng phiên bản Python (3.12)
├── pyproject.toml                          # 📦 Cấu hình uv project + tất cả dependencies
├── uv.lock                                 # Lock file để cài đặt đồng nhất, tái diễn được
├── requirements.txt                        # requirements chuẩn của pip (bản backup dự phòng)
├── environment.yml                         # Cấu hình môi trường Conda (chọn lựa thay thế)
├── package.json                            # Cấu hình Node.js cho các MCP server
├── README.md                               # 📖 File README của dự án (Tiếng Việt)
│
├── segment4/                               # 🎯 THƯ MỤC DỰ ÁN CHÍNH
│   │
│   ├── search_key.py                       # 🚀 Entry Point 1 — Multi-Source Deal Finder (Gradio)
│   ├── price_is_right.py                   # 🚀 Entry Point 2 — Autonomous Deal Hunter (Gradio)
│   ├── multi_source_framework.py           # 📦 Framework orchestrator (ChromaDB, lazy init)
│   ├── deal_agent_framework.py             # 📦 Framework cho chế độ tự động
│   │
│   ├── price_agents/                       # 🤖 TOÀN BỘ CÁC AI AGENT
│   │   ├── agent.py                        # Lớp cơ sở (Base Agent class) (logging, ANSI colors)
│   │   ├── deals.py                        # Pydantic models: Deal, DealSelection, Opportunity, ScrapedDeal
│   │   ├── multi_source_planning_agent.py  # 🧠 LÕI DỰ ÁN: pipeline 6 bước (tìm kiếm → ước tính)
│   │   ├── planning_agent.py               # Tác tử lên kế hoạch đơn giản (chế độ RSS)
│   │   ├── autonomous_planning_agent.py    # OpenAI Agents SDK cho việc lập kế hoạch tự động
│   │   ├── ensemble_agent.py               # 🧪 Mô hình kết hợp (Ensemble): Kết hợp 3 mô hình ước tính giá
│   │   ├── frontier_agent.py               # GPT-5.1 + RAG (ChromaDB) — trọng số: 80%
│   │   ├── specialist_agent.py             # Llama-3.2-3B Fine-tuned trên Modal — trọng số: 10%
│   │   ├── neural_network_agent.py         # PyTorch DNN (cục bộ) — trọng số: 10%
│   │   ├── deep_neural_network.py          # Kiến trúc mô hình PyTorch (ResidualBlocks)
│   │   ├── preprocessor.py                 # Chuẩn hóa văn bản qua LiteLLM
│   │   ├── scanner_agent.py                # Quét feed RSS (DealNews)
│   │   ├── bestbuy_scanner_agent.py        # Tìm kiếm BestBuy qua Brave MCP
│   │   ├── amazon_scanner_agent.py         # Tìm kiếm Amazon qua Brave MCP
│   │   ├── bestbuy_deals.py                # Logic scrape BestBuy (Playwright + BS4)
│   │   ├── amazon_deals.py                 # Logic scrape Amazon (Playwright)
│   │   └── messaging_agent.py              # Thông báo tự động qua Pushover
│   │
│   ├── bestbuy_untils/                     # 🛠️ MODULE TIỆN ÍCH
│   │   ├── clarification_agent.py          # Tác tử tạo 3 câu hỏi làm rõ
│   │   ├── unified_deal.py                 # UnifiedScrapedDeal — gộp deal từ BB + AZ
│   │   ├── multi_source_scanner_agent.py   # Lọc 5 deal tốt nhất từ nhóm gộp
│   │   └── gradio_helpers.py               # Các helper cho UI: logging, định dạng HTML
│   │
│   ├── mo_ta_du_an/                        # 📚 TÀI LIỆU DỰ ÁN (Tiếng Việt)
│   │   ├── COMPLETE_PROJECT_DOCUMENTATION.md
│   │   ├── DOCUMENTATION_SEARCHKEY.md
│   │   ├── DOCUMENTATION_PRICE_IS_RIGHT.md
│   │   └── READING_ROADMAP_SEARCHKEY.md
│   │
│   ├── ghi_chu/                            # 📝 Ghi chú phát triển & file test Jupyter notebooks
│   │   ├── test_chuc_nang/                 # Các notebook test chức năng (BestBuy)
│   │   ├── test_chuc_nang_v2/              # Các notebook test chức năng bản v2
│   │   ├── test_amazon/                    # Notebook test tích hợp Amazon
│   │   └── price_agents/                   # Ghi chú test dành cho từng tác tử
│   │
│   ├── products_vectorstore/               # 🗄️ ChromaDB (800K+ sản phẩm) — GITIGNORED
│   ├── deep_neural_network.pth             # 🧠 Trọng số PyTorch (~1.1GB) — GITIGNORED
│   ├── memory.json                         # 💾 Bộ nhớ trạng thái cho chế độ tự động — GITIGNORED
│   ├── sandbox/                            # 📂 Hệ thống sandbox file của MCP
│   │   └── deals.md                        # Thống kê nhanh tóm tắt các Deal
│   │
│   ├── evaluator.py                        # 📊 Đánh giá mô hình dùng plotly biểu đồ
│   ├── testing.py                          # 📊 Kiểm thử mô hình dùng matplotlib biểu đồ
│   ├── items.py                            # Item data class cho dữ liệu huấn luyện (training data)
│   ├── pricer_service2.py                  # Mã nguồn triển khai Llama fine-tuned trên Modal
│   ├── hello.py                            # Test hello-world cho Modal
│   ├── keep_warm.py                        # Giữ cho Modal container 'warm' (chống cold start)
│   └── log_utils.py                        # Chuyển đổi màu bảng mã ANSI → HTML 
│
├── tailieu/                                # 📄 Báo cáo chuyên ngành (DACN)
├── week7/                                  # 📓 Notebook quá trình Fine-tune Llama
├── day_mcp/                                # 🧪 Các cuộc thử nghiệm về MCP protocol
└── day_openai/                             # 🧪 Các cuộc thử nghiệm về OpenAI API
```

### ⚠️ Các Tệp tin Quan trọng (Critical Files)

| File / Thư mục | Trạng thái | Ghi chú |
|---|---|---|
| `.env` | **GITIGNORED** | Chứa tất cả API key. **KHÔNG BAO GIỜ** được commit. |
| `products_vectorstore/` | **GITIGNORED** | Khoảng 800K embedding sản phẩm. Phải được xây dựng ở máy local. |
| `deep_neural_network.pth` | **GITIGNORED** | Khoảng ~1.1GB weights của Pytorch. Phải tự tải xuống/huấn luyện. |
| `memory.json` | **GITIGNORED** | Trạng thái thực thi cho chế độ tự động (Autonomous mode). |

---

## 3. Technology Stack & Kiến trúc Cốt lõi

### 3.1 Technology Stack

| Tầng / Xếp lớp | Công nghệ | Mục đích |
|---|---|---|
| **Giao diện (UI)** | Gradio 5.x | Giao diện web có tương tác với log hệ thống thời gian thực |
| **Tìm kiếm Web** | Brave Search API + MCP Protocol | Khám phá URL thông tin sản phẩm |
| **Trích xuất Web** | Playwright (async) + BeautifulSoup4 | Cào dữ liệu thông tin chi tiết của sản phẩm |
| **Điều hành LLM** | OpenAI SDK, OpenAI Agents SDK, LiteLLM | Điều phối hoạt động các Agent |
| **Các LLM Models** | GPT-5.1, GPT-5-mini, GPT-5-nano | Lựa chọn, tinh chỉnh và định giá sản phẩm |
| **Fine-tuned Model** | Llama-3.2-3B (LoRA, 4-bit NF4) | Đóng vai trò chuyên gia phân tích giá trên Modal |
| **Neural Network** | PyTorch DNN (10 layers, ResidualBlocks) | Ước lượng giá ở phiên bản thu gọn chạy Local |
| **Vector DB** | ChromaDB (không mất dữ liệu) | Database 800K vector products cho RAG |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 | Chuyển đổi Text → Vector |
| **Kiểm tra dữ liệu** | Pydantic v2 | Đảm bảo định dạng chuẩn đầu ra |
| **Thông báo** | Pushover API | Gửi Push notifications tới thiết bị di động |
| **Tiền xử lý văn bản** | LiteLLM (Groq/Ollama/OpenAI) | Chuẩn hoá chuỗi mô tả sản phẩm |
| **Serverless GPU** | Modal | Chạy model Llama fine-tuned trên T4 GPU đám mây |
| **Quản lý Package** | **uv** (Python), npm (Node.js cho MCP) | Quản lý các dependencies cần cài đặt |
| **Trực quan hóa đồ thị**| Plotly, Matplotlib | t-SNE 3D, biểu đồ thông số đánh giá |

### 3.2 Sơ đồ Kiến trúc Hệ Thống

```mermaid
graph TB
    subgraph "👤 Giao diện Người dùng"
        A[search_key.py<br>Gradio App<br>Chế độ Keyword Search]
        B[price_is_right.py<br>Gradio App<br>Chế độ Tự động]
    end

    subgraph "📦 Tầng Framework"
        C[MultiSourceFramework<br>ChromaDB Init + Lazy Agent Init]
        D[DealAgentFramework<br>Memory + Auto-run Timer]
    end

    subgraph "🧠 Planning Agents (Tác tử Kế hoạch)"
        E[MultiSourcePlanningAgent<br>Pipeline 6 Bước]
        F[AutonomousPlanningAgent<br>OpenAI Agents SDK + MCP Tools]
    end

    subgraph "🔍 Tầng Tìm Kiếm / Scraping"
        G[BestBuySearchAgent<br>Brave MCP → URLs]
        H[AmazonSearchAgent<br>Brave MCP → URLs]
        I[BestBuy Scraper<br>BS4 + Playwright]
        J[Amazon Scraper<br>Playwright]
        K[ScannerAgent<br>DealNews RSS]
    end

    subgraph "🤖 Tầng Phân tích Trí tuệ (AI Estimation)"
        L[EnsembleAgent]
        M[FrontierAgent<br>GPT-5.1 + RAG<br>Trọng số: 80%]
        N[SpecialistAgent<br>Llama-3.2-3B<br>Trọng số: 10%]
        O[NeuralNetworkAgent<br>PyTorch DNN<br>Trọng số: 10%]
    end

    subgraph "🛠️ Các Đặc vụ Hỗ trợ (Supporting Agents)"
        P[ClarificationAgent<br>GPT-5-mini]
        Q[MultiSourceScannerAgent<br>Top 5 GPT-5-mini]
        R[MessagingAgent<br>Pushover + GPT-5-nano]
        S[Preprocessor<br>Chuẩn hoá chuỗi văn bản bằng LiteLLM]
    end

    subgraph "💾 Tầng Dữ liệu"
        T[(ChromaDB<br>800K Sản phẩm)]
        U[(memory.json<br>Data các deal đã xử lý)]
        V[(sandbox/deals.md<br>MCP Output)]
    end

    subgraph "☁️ Dịch vụ Ngoài hệ thống"
        W[Brave Search API]
        X[OpenAI API<br>GPT-5.1 / mini / nano]
        Y[Modal<br>Llama T4 GPU (Fine-tuned)]
        Z[Pushover API<br>Thông báo Mobile]
    end

    A --> C --> E
    B --> D --> F

    E --> P
    E --> G --> W
    E --> H --> W
    E --> I
    E --> J
    E --> Q --> X
    E --> L
    E --> R --> Z

    F --> K
    F --> L
    F --> R

    L --> S
    L --> M --> X
    L --> N --> Y
    L --> O

    M --> T
    D --> U
    F --> V
```

### 3.3 Các Quyết định Kiến trúc Cốt lõi

| Quyết định | Lý do (Rationale) |
|---|---|
| **Cấu trúc Multi-Agent** | Mỗi một Agent đảm trách 1 nhiệm vụ duy nhất (search, scrape, estimate, notify). Hỗ trợ thực thi song song, dễ dàng nâng cấp hoặc debug. |
| **Giá Ensemble (3 Model)** | Kết hợp giữa GPT-5.1 RAG (cho ra kết quả chính xác), Llama fine-tuned (chuyên gia ở 1 vùng cụ thể) và DNN (tốc độ cao) làm giảm tỷ lệ sai sót. GPT chiếm ưu thế cao nhất (80%) bởi vì được trang bị ngữ cảnh lên đến 800K sản phẩm. |
| **Sử dụng MCP Protocol** | Các máy chủ của Brave Search MCP cung cấp cách thức truy cập chuẩn tới Web thay cho LLM, cho phép tìm kiếm và hoán đổi, nâng cấp Agent dễ dàng. |
| **ChromaDB cho RAG** | Vector DB cục bộ mạnh mẽ cung cấp cho máy khả năng lưu trữ tới 800k sản phẩm phục vụ tìm kiếm similarity (tương đồng). Sử dụng mô hình `sentence-transformers/all-MiniLM-L6-v2` cho embedding chuẩn xác. |
| **Triển khai Llama lên Modal** | Cần sử dụng GPU T4 để có thể đưa khả năng chạy mô hình có Adapter LoRA của Llama-3.2-3B. Khi không có tác vụ nào chạy tốn CPU, chi phí duy trì trên Modal rẻ tới mức tiệm cận không. |
| **Playwright thay vì Selenium** | Cung cấp interface Async-native, hiện đại, tích hợp mạnh chống detect là robot, cho phép native support Headless Chromium. Rất quan trọng dùng Amazon scraping vì nó cần thiết cho Render ra JS. |
| **Sử dụng Gradio thay Streamlit** | Cung cấp UI support cực mạnh với khả năng cập nhật biểu đồ với Plotly, Event binding nhanh chóng và cung cấp chức năng streaming realtime. |
| **Pydantic Structured Outputs** | Nhận đầu ra JSON chuẩn nhất và an toàn định dạng bằng cách gọi `.parse()` cùng với parameter `response_format=PydanticModel` tới OpenAI. |

---

## 4. Workflows & Rules (Quy trình làm việc & Quy tắc) (QUAN TRỌNG)

### 4.1 ⚠️ QUY TẮC NGHIÊM NGẶT DÀNH CHO TRỢ LÝ AI

> **Đọc và bắt buộc tuân theo những luật lệ sau ĐÚNG VỚI NGUYÊN BẢN.** Bất cứ sự cố tình hay vô tình làm sai nào sẽ gây ra lỗi và khiến dự án "vỡ vụn".

#### Quản lý Package (Package Management)
- ✅ **LUÔN LUÔN** dùng lệnh `uv add <package>` để cài version python dependencies mới
- ✅ **LUÔN LUÔN** dùng lệnh `uv sync` để tiến hành cài đặt từ `pyproject.toml`
- ✅ **LUÔN LUÔN** dùng lệnh `uv run <script.py>` để chạy mã Python
- ❌ **KHÔNG BAO GIỜ** dùng lệnh `pip install` cách trực tiếp
- ❌ **KHÔNG BAO GIỜ** thực hiện việc tự chỉnh file `uv.lock` bằng tay
- ❌ **KHÔNG BAO GIỜ** tuỳ chỉnh kích hoạt venv bằng lệnh - `uv run` đã tự quản lý nó

#### Biến môi trường & Bảo mật (Environment & Secrets)
- ✅ **LUÔN LUÔN** khai báo cho phép nạp các env variables thông qua `load_dotenv(override=True)` ở module level
- ✅ **LUÔN LUÔN** dùng lệnh `os.getenv("KEY")` để gọi các thông tin nhạy cảm (secrets)
- ❌ **KHÔNG BAO GIỜ** được phép hardcode các API Key, token đăng nhập ngay trong mã nguồn gốc
- ❌ **KHÔNG BAO GIỜ** để `.env` được đẩy lên git (Mặc định nó đã nằm trong danh sách bỏ qua `.gitignore`)
- ⚠️ File `.env` chứa tại **thư mục cài đặt gốc (project root)** (`tech2ai/.env`), CHỨ KHÔNG PHẢI trong `segment4/`

#### Phong cách Code (Code Style)
- ✅ **LUÔN LUÔN** sử dụng định dạng Type Hinting vào mọi function và kiểu dữ liệu trả về 
- ✅ **LUÔN LUÔN** viết ghi chú giải thích (docstrings) cho public method hay các Class
- ✅ **LUÔN LUÔN** đi theo các mẫu design pattern đã cho ở class **Agent base** (xem Phần 6)
- ✅ **LUÔN LUÔN** sử dụng hàm `logging.info()` cho các tin nhắn log thay vì hàm `print()`
- ✅ **LUÔN LUÔN** dùng lệnh `self.log()` trong Agent nhằm trace logic trong pipeline một cách dễ dàng nhất
- ❌ **KHÔNG BAO GIỜ** sử dụng lệnh bare `except:` — Luôn phải đi kèm với loại expect lỗi rõ ràng

#### Kiến trúc (Architecture)
- ✅ **LUÔN LUÔN** sử dụng mô hình lập trình 3 tầng (3-layer pattern): `UI (Gradio) → Framework → Planning Agent`
- ✅ **LUÔN LUÔN** cho phép tạo thông qua phương thức Khởi động trễ (lazy initialization) với database nặng hay ChromaDB hoặc Model
- ✅ **LUÔN LUÔN** tạo thông qua **Pydantic BaseModel** cho cách xử lý đầu ra LLM Models
- ❌ **KHÔNG BAO GIỜ** để logic tính toán tại cùng cấp file giao diện Gradio UI
- ❌ **KHÔNG BAO GIỜ** import hàm trực tiếp từ folder `ghi_chu/` — nơi này chỉ sử dụng dành riêng cho ghi nhớ tiến trình hoàn thiện 

#### Git & An toàn (Git & Safety)
- ✅ **LUÔN LUÔN** check qua lệnh `.gitignore` để đảm bảo file ko bị upload lên git
- ❌ **KHÔNG BAO GIỜ** commit các dạng file lớn có hậu tố sau: `*.pth`, `*.pkl`, thư mục `products_vectorstore/`, `memory.json`, `.env`
- ❌ **KHÔNG BAO GIỜ** tuỳ ý thao tác trên file hệ thống cho đến khi được Users cấp quyền hoàn toàn

### 4.2 Hướng dẫn chạy các tính năng

```bash
# Sẽ cần ở môi trường segment4 để mọi mã nguồn thực thi tốt không bị gãy dependencies
cd segment4

# Chạy hệ thống dò tìm (search) các URL (Với chế độ gõ thủ công từng từ khoá định tâm)
uv run search_key.py
# Khởi chạy ở port local http://127.0.0.1:7860

# Nếu đang ở chế độ Agent AI rà soát mỗi 5 phút 1 lần 
uv run price_is_right.py
# Khởi chạy ở port local http://127.0.0.1:7860
```

### 4.3 Chiến lược kiểm thử (Testing Strategy)

| Loại Test | Công Cụ | Chức Năng Cốt Lõi |
|---|---|---|
| **Quick smoke test** | `uv run search_key.py` | Test xem App có crash khi launch không |
| **Agent unit test** | Jupyter notebooks nằm trong `ghi_chu/` | Test qua từng logic agent hoạt động |
| **Evaluation** | `evaluator.py` / `testing.py` | Benchmark bài tính cho 250 dòng datapoint đánh giá độ chính xác |
| **Modal test** | `uv run hello.py` | Kiểm tra kết nối API tới server của Model máy |
| **Playwright test** | Trong sổ tay tại thư mục `ghi_chu/test_chuc_nang/` | Cho phép chạy cào logic data chuẩn nhất |

⚠️ **Vẫn chưa có hệ thống tự động kiểm thử cụ thể (pytest).** Phần nhiều được test thông qua Giao diện web Gradio interface hoặc check qua Jupyter Notebook. Khi code một chức năng mới, luôn đề xuất thêm script để chạy test code cho nó.

---

## 5. Lộ trình triển khai (Implementation Roadmap) / Hướng dẫn

### Giai đoạn 1: Nền tảng Dữ liệu
| Module | File chứa | Chuẩn đoán logic |
|---|---|---|
| Data Models | `price_agents/deals.py` | Chứa những phần cứng như Pydantic: `Deal`, `DealSelection`, `Opportunity`, `ScrapedDeal` |
| Unified Deal | `bestbuy_untils/unified_deal.py` | Chức năng `UnifiedScrapedDeal` — chuyển đổi dữ liệu thô sang luồng chuẩn Amazon hay BestBuy format |
| Items | `items.py` | Item của luồng Model Train vào File Llama cho mục đích Fine-tune |

### Giai đoạn 2: Cào Web (Scraping) & Tìm kiếm
| Module | File chứa | Chuẩn đoán logic |
|---|---|---|
| BestBuy Scraper | `price_agents/bestbuy_deals.py` | Chạy lệnh theo model BS4 qua sale, dùng Playwright để dò các giá trong trang web |
| Amazon Scraper | `price_agents/amazon_deals.py` | Setup theo Pipeline Playwright để dò chi tiết và cào nội dung qua html |
| BestBuy Dò Tìm Giá | `price_agents/bestbuy_scanner_agent.py` | Sử dụng Brave MCP thông qua url sản phẩm (product url)|
| Amazon Dò Tìm Giá | `price_agents/amazon_scanner_agent.py` | Sử dụng Brave MCP thông qua url sản phẩm (product url) |
| Lấy Feed RSS | `price_agents/scanner_agent.py` | Lọc các rss feed báo giá của trang DealNews |

### Giai đoạn 3: AI Model Engine Đánh giá Giá trị
| Module | File chứa | Chuẩn đoán logic |
|---|---|---|
| AI Front (RAG) | `price_agents/frontier_agent.py` | Khởi tạo với GPT-5.1 cộng với module ChromaDB đo khoảng cách vector cho 5 neighbor |
| AI Spec (Kiểm Dữ liệu) | `price_agents/specialist_agent.py` + `pricer_service2.py` | Sử dụng Llama-3.2-3B trên card T4 GPU thông qua 4bit quantization NF4|
| AI Local Net | `price_agents/neural_network_agent.py` + `price_agents/deep_neural_network.py` | Model PyTorch DNN dùng cùng với HashingVectorizer với cấu trúc lớp ResidualBlocks |
| Kỹ thuật Mix (Ensemble) | `price_agents/ensemble_agent.py` | Theo công thức nội suy `price = frontier × 0.8 + specialist × 0.1 + neural × 0.1` |
| Prep | `price_agents/preprocessor.py` | Module hỗ trợ chuẩn hoá Text LiteLLM qua lại cho khâu estimate sau |

### Giai đoạn 4: Lão hóa Agent Orchestration
| Module | File chứa | Chuẩn đoán logic |
|---|---|---|
| Xác Minh | `bestbuy_untils/clarification_agent.py` | Module khởi tạo 3 câu Query nhỏ cùng GPT-5-mini đi kèm lọc ý đồ tìm |
| Tool 5 Chọn lọc Multi Scanner | `bestbuy_untils/multi_source_scanner_agent.py` | GPT-5 lấy ra 5 danh sách đánh giá top cuối nhất đi kèm |
| Trạm Phân Phối Agent | `price_agents/multi_source_planning_agent.py` | **ĐÂY LÀ PHẦN LÕI** — Hệ thống giao tác 6 bước theo tiêu chuẩn |
| Chuối Tự Trị | `price_agents/autonomous_planning_agent.py` | Dùng chuẩn theo SDK API từ OpenAI đi chung với các tools Function Calling |
| Chức Năng Báo Push Push | `price_agents/messaging_agent.py` | Tạo báo trên điện thoại dùng Push qua tin nhắn làm lại nhờ module Nano của GPT 5 |

### Giai đoạn 5: Phát Triển Tầng Khách Web Application
| Module | File chứa | Chuẩn đoán logic |
|---|---|---|
| Tầng Lõi Frame | `multi_source_framework.py` | Core init cho vector API với Agent ở chế độ lazy |
| Tầng Framework tự động | `deal_agent_framework.py` | Đặt module t-SNE visualize, thiết lập theo mốc bộ nhớ Memory tự động chạy |
| Giao diện Gradio Trực quan Search | `search_key.py` | Handler dành cho bắt UI Event tương tác từ app, gọi module logs stream realtime |
| Giao Diện Gradio AI Tự Hành Auto | `price_is_right.py` | App cho màn hình 3-D Chart đi kèm hẹn giờ logic Plot |
| Bộ Dụng cụ (Helpers) | `bestbuy_untils/gradio_helpers.py` | QueueHandler setup cùng module format và xuất ra Table (Dạng bảng) |

### Giai đoạn 6: Deploy & Benchmark
| Module | File chứa | Chuẩn đoán logic |
|---|---|---|
| Evaluation File | `evaluator.py` | Chart với xu hướng sai số phân kì dựa trên module Plotly scatter |
| Test file Benchmark | `testing.py` | Dùng đồ thị qua module Matplotlib nhằm Benchmark |
| Modal Host | `pricer_service2.py` | Câu lệnh `modal deploy pricer_service2.py` |
| Hâm Tự Động Server | `keep_warm.py` | Ngăn server T4 khởi động lâu nhờ tính năng chống ngủ lạnh Cold start|

---

## 6. Code Style & Các mẫu thiết kế (Idiomatic Patterns)

### 6.1 Mẫu tạo Base Agent (Agent Base Class Pattern)

Tất cả các agent mở rộng từ lớp cơ sở `Agent` để đảm bảo hệ thống log đồng bộ:

```python
# price_agents/agent.py — Lớp cơ sở (Base class)
class Agent:
    """Lớp cha trừu tượng cho mọi agent."""
    RED = '\033[31m'
    GREEN = '\033[32m'
    # ... Các mã màu ANSI khác
    RESET = '\033[0m'
    
    name: str = ""
    color: str = '\033[37m'

    def log(self, message):
        color_code = self.BG_BLACK + self.color
        message = f"[{self.name}] {message}"
        logging.info(color_code + message + self.RESET)
```

**✅ Cách tạo một Agent đúng chuẩn:**
```python
from price_agents.agent import Agent

class MyNewAgent(Agent):
    name = "My Agent"           # Bắt buộc: để xác định agent trong log
    color = Agent.CYAN          # Bắt buộc: Màu của đoạn dòng Log message
    MODEL = "gpt-5-mini"       # Tiêu chuẩn: Gắn model với class biến này không được thiếu

    def __init__(self):
        self.log("My Agent is initializing")
        # ... thiết lập 
        self.log("My Agent is ready")

    def some_action(self, param: str) -> float:
        """
        Diễn giải những gì đoạn phương thức mã này làm ở đây.
        
        Args:
            param: Nội dung parameter param
            
        Returns:
            float: Nội dung float trả về
        """
        self.log("My Agent is performing action")
        result = ...
        self.log(f"My Agent completed - result: {result}")
        return result
```

### 6.2 Mô thức định dạng Output trả kết quả dùng Pydantic

Sử dụng phương thức `.parse()` của chuẩn OpenAI với Pydantic đảm bảo định dạng model và output 100% trả về cùng JSON chính xác:

```python
from pydantic import BaseModel, Field
from openai import OpenAI

class MyOutput(BaseModel):
    """Pydantic model mô tả cấu trúc JSON để parse OpenAI LLM output."""
    name: str = Field(description="Tên sản phẩm")
    price: float = Field(description="Mức giá tính bằng Dollar USD, bắt buộc lớn hơn > 0")

# ✅ Đúng chuẩn — output có cấu trúc nghiêm ngặt (structured output)
result = self.openai.chat.completions.parse(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ],
    response_format=MyOutput,       # Gắn Pydantic model vào đây
)
parsed = result.choices[0].message.parsed  # Object này tự động ép kiểu thành  MyOutput instance!
```

### 6.3 Kiến trúc mô hình chia ba vòng (Three-Layer Architecture Pattern)

```
┌────────────────────────────────┐
│ Tầng Giao Diện UI (Gradio App) │  search_key.py / price_is_right.py
│  - Theo sát Event handlers     │  - Không để các mảng Business logic ở đây 
│  - Stream Log hệ thống trực tiếp│  - Các logic Gradio Component giao diện
│  - Formatter để tuỳ biến View HTML/Table │
├────────────────────────────────┤
│ Tầng Trung Chuyển Framework    │  multi_source_framework.py / deal_agent_framework.py
│  - Tạo vector ChromaDB local   │  - Tuỳ biến khởi tạo logic Lazy Agents
│  - Thiết đặt API cho Front End │  - Quản trị bộ máy điều kiện Memory cho Bot
├────────────────────────────────┤
│ Tầng Xử Lý Tác vụ Agent AI     │  price_agents/*.py + bestbuy_untils/*.py
│  - Mảng Pipeline tuần hoàn     │  - Search (Tìm), Scrape (Cào), Estimate (Tính Giá), Notify (Báo)
│  - Actions độc lập tương ứng   │  - Mỗi agent = chịu trách nhiệm tuỳ 1 nhiệm vụ duy nhất 
└────────────────────────────────┘
```

**✅ Chuẩn xác — Framework lấy ra thông tin từ Pipeline PlanningAgent thông qua hàm này:**
```python
class MultiSourceFramework:
    def run(self, keyword: str, max_urls: int = 10) -> List[Opportunity]:
        self.init_agents_as_needed()  # Gọi Init trễ (Lazy init) 
        return self.planner.plan(keyword, max_urls)  # Uỷ quyền qua agent
```

**❌ Sai cách cấu trúc thiết kế logic — nhường Pipeline qua phía UI UI Gradio:**
```python
# ĐỪNG LÀM ĐIỀU NÀY MỌI GIÁ:
class MultiSourceFramework:
    def run(self, keyword):
        urls = brave_search(keyword)     # ← Logic kinh doanh nhảy vào bộ Framework!
        products = scrape(urls)          # ← Hàm này đáng lý dời nó tuốc sang thư mục Agent PlanningAgent mới phải
```

### 6.4 Brave MCP Server Pattern (Mẫu tích hợp Brave MCP)

Sử dụng SDK Agents từ OpenAI kèm theo `MCPServerStdio` đáp ứng nhu cầu search kết quả trên mạng (Web search):

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def _search_async(self, keyword: str) -> List[str]:
    async with MCPServerStdio(
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": self.brave_api_key}
        },
        client_session_timeout_seconds=60
    ) as brave_server:
        search_agent = Agent(
            name="SearchAgent",
            instructions=self.INSTRUCTIONS,
            model="gpt-5-nano",             # Chạy các mã dòng siêu nhẹ cho chức năng cơ bản dò đường
            mcp_servers=[brave_server],
            output_type=SearchResults        # Gọi thông số cấu trúc Output của Pydantic 
        )
        result = await Runner.run(search_agent, f"Search for {keyword}", max_turns=30)
        return result.final_output.product_urls
```

### 6.5 Cơ chế định giá bằng Mô hình kết hợp (Ensemble Pricing Pattern)

```python
class EnsembleAgent(Agent):
    def price(self, description: str) -> float:
        rewrite = self.preprocessor.preprocess(description)   # Chuẩn hoá văn bản cho sạch để test
        specialist = self.specialist.price(rewrite)           # API truyền lệnh Cloud remote Mode
        frontier = self.frontier.price(rewrite)               # GPT-5.1 kết hợp CSDL lớn Vector RAG
        neural_network = self.neural_network.price(rewrite)   # Máy Local chạy DNN Deep model Pytorch DNN
        combined = frontier * 0.8 + specialist * 0.1 + neural_network * 0.1
        return combined
```

### 6.6 Định hướng chạy tuỳ biến thiết bị (PyTorch CUDA Detect)

```python
if torch.cuda.is_available():
    self.device = torch.device("cuda")
elif torch.backends.mps.is_available():
    self.device = torch.device("mps")
else:
    self.device = torch.device("cpu")
logging.info(f"Neural Network is using {self.device}")
```

---

## 7. Lỗi thường gặp & Giải pháp Debug (Troubleshooting)

> ⚠️ **HƯỚNG DẪN DÀNH CHO CÁC TRỢ LÝ AI (AI ASSISTANTS):** Khi bạn bị kẹp vào trạng thái lỗi ứng dụng chạy, **Kiểm chứng chẩn đoán lỗi đầu tiên (diagnose first)**. Xem hết đoạn lỗi (trace stack bug), Xem thử luồng tin log có vấn đề nào ở đó, và **KHÔNG BAO GIỜ tự sửa đổi mã (blind defensive code modify) cho đến khi hiểu ra nguyên do cội nguồn cốt lõi (Root Cause) bị cái gì.**

### 7.1 Lỗi API Token Keys

| Triệu chứng lỗi (Symptom) | Nguyên nhân cội (Root Cause) | Giải pháp Fixing |
|---|---|---|
| `AuthenticationError: Incorrect API key` | Đang mất file `.env` config file hoặc thiết lập chưa tải lại. | 1. Xem qua cẩn thận nếu file `.env` tồn tại tại thu mục root path (`tech2ai/.env`)<br>2. Xác định API Keys được call thông qua mã `load_dotenv(override=True)` trong code<br>3. Kiểm tra mã key xem có bị dán lộn form không: `OPENAI_API_KEY=sk-proj-...` |
| `BRAVE_API_KEY not found` | Rơi mất Brave API Key  | 1. Tiến cấp qua trang lấy API Keys tại [brave.com/search/api](https://brave.com/search/api)<br>2. Nhập nó lại thông qua biến `BRAVE_API_KEY=BSA-...` nằm ở file `.env` |
| `RateLimitError` | Cấu hình gọi qua mức yêu cầu chịu tải OpenAI  | 1. Quãng ngưng dùng chạy vòng chờ khoảng 60s và gọi loop<br>2. Gọi lệnh truyển api sang phiên bản tiết kiệm cost hơn (`gpt-5-nano`)<br>3. Điều hoà tuỳ chỉnh rút ngắn biến số `max_urls` lại một mức nhất định |

### 7.2 Quá trình Scrape hoặc Playwright Error Bug 

| Triệu chứng lỗi (Symptom) | Nguyên nhân cội (Root Cause) | Giải pháp Fixing |
|---|---|---|
| `Playwright browsers not installed` | Thiếu file tải Chromium Core  | Fix bằng lệnh gọi cmd vào terminal shell gõ: `uv run playwright install chromium` |
| `TimeoutError` during scraping | Render Website load siêu siêu chậm | 1. Ép thời gian thông số đợi Limit Timeout tăng lên ở hàm Call của module Node JS Playwright<br>2. Tra soát HTML Element coi web nó có đổi mã DOM hay không<br>3. Tuỳ biến bật option cho nó chạy `headless=False` để xem bug debug cụ thể |
| `Amazon blocks scraping` | Bị trang bắt lỗi IP Block dò bot | 1. Gắn vòng delays xen giữa 2 luồng requests cho giống con người thật<br>2. Xoá cookies ngẫu nhiên luân phiên Agents đổi user header<br>3. Thay `headless=False` để xem nó Captcha không |
| `BestBuy returns empty results` | Định dạng path dẫn cấu trúc URL sai | Xác nhận mẫu URL form regex check theo form `bestbuy.com/product/` nếu có cập nhật version Url mới không |

### 7.3 Các mã lỗi liên quan cơ sở ChromaDB 

| Triệu chứng lỗi (Symptom) | Nguyên nhân cội (Root Cause) | Giải pháp Fixing |
|---|---|---|
| `ValueError: collection products not found` | Thư mục thư viện `products_vectorstore/` hiện trống rỗng| 1. Đi dạo ngang `products_vectorstore/` xem các nhánh node nó sinh có đầy đủ chưa<br>2. Kích hoạt jupyter notebook Ingestion DB file lên kéo lại Vector Cache Store cho Database |
| `ChromaDB takes too long to load` | Cập nhật tệp quá khủng khiếp trên (800K+ docs) file | 1. Việc chạy lên (30-60s) là siêu bình thường từ Database nặng khủng khi load lần đầu (initial launch)<br>2. Load thư viện lần Cache tiếp theo thì vài giây là xong ngay |
| `Embedding dimension mismatch` | Chọn mô hình file weight embedding lệch kích thước (wrong dimensions) | Tiến độ sửa để bắt file quy chuẩn cấu hình embedding tải `sentence-transformers/all-MiniLM-L6-v2` gọi API qua module hàm cho đúng |

### 7.4 Máy Host từ model T4 Modal hoặc file Fine-Tune Modal Tuning Lỗi Xung Đột

| Triệu chứng lỗi (Symptom) | Nguyên nhân cội (Root Cause) | Giải pháp Fixing |
|---|---|---|
| `Modal: lookup failed for pricer-service` | Lệnh chưa gọi Deploy | Triển khai lệnh chạy Model deploy: `modal deploy pricer_service2.py` |
| `Modal cold start takes 60s+` | Bị rớt container máy host xoá đi sau 30p chưa vào ngắt ngủ | 1. Chạy mã loop Python lên cho chức năng Keep Alive model dùng gọi `keep_warm.py`<br>2. Không nên cấu hình `MIN_CONTAINERS = 1` ở tệp config params set trong `pricer_service2.py` (cái này sẽ làm trừ rất nhiều chi phí tiền ở tài khoản) |
| `CUDA out of memory on Modal` | Giới hạn vRAM bị kẹt bởi GPU card chuẩn 16GB Memory limit | 1. Check chắc ăn là config 4-bit quantization tải lên đầy đủ ko lỗi config<br>2. Validate kiểm thử các node settings qua bộ param setup `BitsAndBytesConfig` |

### 7.5 Fix Debug Từ Model MCP Engine / Hoặc File Chạy Node.js

| Triệu chứng lỗi (Symptom) | Nguyên nhân cội (Root Cause) | Giải pháp Fixing |
|---|---|---|
| `npx: command not found` | Chưa có cấu trúc Node Runtime Core | Set môi trường chạy JS Runtime Version 18+: gõ shell `sudo apt install nodejs npm` |
| `MCP server timeout` | Luồng không tiếp nạp Timeout Server Response | 1. Can thiệp thời gian chạy thông qua config cấu hình `client_session_timeout_seconds`<br>2. Xem thử file cấu trúc command line của JS: gọi code terminal Node test xem check file `npx -y @modelcontextprotocol/server-brave-search --help` |
| `EACCES permission denied` | Hệ thống uỷ quyền cho Node Package Lỗi | Test thử gọi lệnh Bypass Global Path qua `npm config set prefix ~/.npm-global` cùng với PATH bashrc update file |

### 7.6 Khía Cạnh Trực quan Form web bằng UI Gradio Apps Bugs

| Triệu chứng lỗi (Symptom) | Nguyên nhân cội (Root Cause) | Giải pháp Fixing |
|---|---|---|
| `Port 7860 already in use` | Kẹt mã Port vì có Script cũ tồn ở luồng nhớ Thread Process| 1. Tiến trình ngắt qua lệnh ở Linux cmd Shell gõ: `lsof -i :7860 \| kill`<br>2. Kéo tuỳ cấu hình đổi config qua port 7861 bằng code sửa: `ui.launch(server_port=7861)` |
| `Logs not updating in real-time` | QueueHandler thread loop Chưa gọi module setup| Xác nhận file config của code này: kiểm tra hàm `setup_logging(log_queue)` trước khi gọi start pipelines thread |
| `plt.show() hangs` | Chạy lệnh trong luồng bị khoá (SSH block Thread UI loop) | Đổi qua export đồ thị file PNG Image bằng cách chỉnh `plt.savefig("output.png")` thay vì gọi show API |

### 7.7 Gặp Trục Trặc với Code Pytorch AI / Hệ DNN Model

| Triệu chứng lỗi (Symptom) | Nguyên nhân cội (Root Cause) | Giải pháp Fixing |
|---|---|---|
| `FileNotFoundError: deep_neural_network.pth` | Chặn Load File Weight Model bị xoá hay làm hỏng | 1. Re-download (Tải lại lần mới) file Training weight param Pytorch weights model (pre-trained weight)<br>2. Cho training Local API Load qua mã (re-train notebook model file) |
| `RuntimeError: CUDA not available` | Máy Local bị mất File Driver VGA nhận định Card Module (GPU detect API file missing) | 1. Thiết bị cấu trúc sẽ chạy lùi qua cơ cấu (Fallback module) sử dụng máy bằng CPU thuần tự động (CPU-auto fallbacks API)<br>2. Cài lại thư viện và thiết lập check với Code Torch GPU: Code chạy file `python -c "import torch; print(torch.cuda.is_available())"` |
| `Prediction returns 0.0` | Device Memory Pointers đang truyền luồng Tensor (Model loaded) sai máy Device Module | Thiết lập dòng ép cho Model chạy thông qua `model.to(self.device)` bắt buộc được gọi khởi chạy Load trước bằng method setup `load_state_dict()` |

---

## 💡 Nội Dung Tham Khảo Nhanh Bổ Trợ Tư Duy (Quick Reference)

### Bản phân tích phí tổn chạy Server (Cost per Run)

| Tên Mô-đun (Component Component) | Core Engine (Model) | Phí Tổn Ước Toán (Cost API) |
|---|---|---|
| Mã Khởi Tạo Trí Tuệ Kép Tìm URL (Search Agents) (×2) | GPT-5-nano | Tầm -$0.001 |
| Bộ Rà Lọc Intent Users (Clarification) | GPT-5-nano | Tầm -$0.001 |
| Filter Danh Sách Đầu TOP Cứu Deal (Select top 5) | GPT-5-mini | Tầm -$0.002 |
| Chức Năng Bóc Tách Ước Giá API Mạng (Estimate) (×5) | GPT-5.1 | Tầm -$0.005 |
| Bơm Thông Số File Check Chuẩn (Preprocess Codec) | Groq/Ollama | Tầm -$0 |
| **Giá Cuối Cho 1 Vòng Chạy Toàn Hệ (Total cost run)** | | **Rơi vào khoảng -$0.01/run loop** |

### Tổ Hợp Các Công Cụ/Khởi Chạy Nhanh (Key Commands)

```bash
# Code thực thi lấy các modules install dependency file pyproject uv sync 
uv sync

# Khởi Tạo Download Chức năng Load Data qua Headless Engine trình duyệt Google Chromium Edge
uv run playwright install chromium

# Code API Khởi tạo Test hệ Giao Kéo Đầu Search Bằng App UI Gradio File Code Entry
uv run search_key.py

# Auto Lập Lịch Task chạy (Scan Agent Tự Khởi Chạy Mỗi Vòng Auto Time loop)
uv run price_is_right.py

# Build/Export Model Cho Module Llama Trên Máy Host Modal Deploy AI Server
uv run modal deploy pricer_service2.py

# Test qua Hello-API cho phép ping mạng check Modal File Request Client Ping API 
uv run hello.py

# Đặt Code chạy nền Background task cho Script chặn tắt Modal Cold Start Down T4 File Code Tool Task Check Modal Loop
uv run keep_warm.py
```

---

*Tài liệu này được thiết kế và biên soạn theo quy chuẩn tối ưu hóa cho AI Assistant tiêu hóa và xử lý, để phục vụ cho các ứng dụng thực tiễn của Đồ án. Vui lòng cập nhật tài liệu khi có những nâng cấp mạnh vào quy trình Core kiến trúc.*
