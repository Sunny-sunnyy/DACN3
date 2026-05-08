# SESSION HANDOFF — Dự án NLP "The Price Is Right"

> **Mục đích file này:** Cung cấp toàn bộ ngữ cảnh cho AI session tiếp theo để tiếp tục làm việc mà không cần đọc lại toàn bộ tài liệu.
>
> **Ghi chú quan trọng:** File này KHÔNG phải báo cáo cho giáo viên. Báo cáo sẽ được tạo riêng thành các file .md tách biệt cho từng phần:
> - `report_data_processing.md` — Xử lý dữ liệu (Day 1-2)
> - `report_fine_tune_llm.md` — Fine-tune Llama 3.2 (Week 7)
> - `report_system.md` — Xây dựng hệ thống (search_key + price_is_right)
>
> **Ngày cập nhật:** 2026-05-08 (session 2)
> **Nhánh git hiện tại:** `claudedev`
> **Working directory:** `/home/hieu0606sunny/price2026wsl/tech2ai`

---

## 1. Tổng quan dự án

**Tên:** The Price Is Right — AI Price Intelligence System (DACN3)

**Mục tiêu:** Hệ thống multi-agent tự động:
1. Tìm kiếm sản phẩm giảm giá trên BestBuy và Amazon
2. Ước lượng giá thực bằng Ensemble AI (3 models)
3. Gửi push notification khi phát hiện deal tốt

**Hai ứng dụng chính:**
- `segment4/search_key.py` — Người dùng nhập keyword, pipeline 4 bước trả về top 3 deals
- `segment4/price_is_right.py` — Autonomous: quét RSS feeds DealNews mỗi 5 phút, tự notify

---

## 2. Hành trình xây dựng — Từ dữ liệu đến hệ thống

### PHASE 1: Data Curation (Week 6 — Day 1)

**Nguồn dữ liệu:**
- Dataset: `McAuley-Lab/Amazon-Reviews-2023` trên Hugging Face
- 8 categories: Automotive, Electronics, Office_Products, Tools_and_Home_Improvement, Cell_Phones_and_Accessories, Toys_and_Games, Appliances, Musical_Instruments

**Số liệu:**
| Giai đoạn | Số mẫu |
|-----------|--------|
| Raw total | ~2,933,577 |
| Sau deduplication | ~2,887,890 |
| Final dataset (weighted sampling) | 820,000 |
| Train / Val / Test | 800k / 10k / 10k |

**Bộ lọc (parser.py):**
- Giá: $0.5 — $999.49
- Độ dài text tối thiểu: 600 ký tự
- Xóa: Part Numbers, Best Sellers Rank, model numbers
- Regex xóa mã sản phẩm: `r"\b(?=[A-Z0-9]{7,}\b)(?=.*\d)[A-Z0-9]+\b"`

**Weighted Sampling (giải quyết imbalanced data):**
```python
w = price²           # Ưu tiên hàng đắt → kéo giá TB từ $59 lên $140
w[Automotive] *= 0.05          # Penalize category chiếm đa số
w[Tools_and_Home_Improvement] *= 0.5
```

**Lý do cần weighted sampling:** Automotive chiếm ~33% raw data, phần lớn hàng giá rẻ → model sẽ bias đoán giá thấp nếu không cân bằng.

---

### PHASE 2: Data Pre-processing with LLM (Week 6 — Day 2)

**Mục tiêu:** Biến raw text lộn xộn → summary sạch, chuẩn format

**Công cụ:** Groq Batch API (model: `llama-3.1-8b-instant`)

**System prompt:**
```
Create a concise description of a product. Respond only in this format. Do not include part numbers.
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features
```

**Quy trình Batch:**
1. Chia 820k items thành các chunks (1000 items/file JSONL)
2. Upload lên Groq server
3. Wait (Groq thường xong trong vài giờ)
4. Retrieve results, map bằng `custom_id`
5. Lưu vào `item.summary`, xóa `item.full`

**Chi phí:**
- Lite (22k items): <$1, vài phút
- Full (820k items): ~$30, vài giờ
- Tiết kiệm 50% so với gọi API synchronous (batch discount)

**Kết quả:** Dataset lên Hugging Face: `SeanSunny/items_lite` (22k) và `SeanSunny/items_full` (820k)

---

### PHASE 3: Baseline Models — Traditional ML (Week 6 — Day 3)

**Kỹ thuật:** Bag of Words (CountVectorizer) + scikit-learn

**Bảng kết quả baseline:**
| Model | MAE (sai số) | Ghi chú |
|-------|-------------|---------|
| Random Pricer | $382.08 | Đoán mò |
| Constant Pricer | $106.18 | Đoán giá trung bình $140.56 |
| Linear Regression (manual features) | $101.56 | Features: weight, text_length |
| NLP Linear Regression (BoW) | **$76.81** | CountVectorizer 2000 từ |
| Random Forest | $72.28 | 100 trees, 15k subset |
| XGBoost | **$68.23** | 1000 trees, full dataset |

**Code xử lý text:**
```python
vectorizer = CountVectorizer(max_features=2000, stop_words='english')
X = vectorizer.fit_transform(documents)  # documents = [item.summary for item in train]
```

**Evaluator (evaluator.py):**
- Chạy 200 mẫu test với ThreadPoolExecutor
- Màu sắc: xanh (error<$40 hoặc <20%), cam (<$80 hoặc <40%), đỏ (còn lại)
- Vẽ Scatter plot (Predicted vs Actual) + Error Trend Chart

---

### PHASE 4: Neural Networks + Frontier Models (Week 6 — Day 4)

**Cải tiến xử lý text:**
```python
# HashingVectorizer thay CountVectorizer (nhanh hơn, không cần từ điển)
vectorizer = HashingVectorizer(n_features=5000, binary=True)
```

**Vanilla Neural Network (PyTorch):**
- 8 lớp Linear + ReLU
- Input: 5000 features, Hidden: 128→64 (×6), Output: 1
- Params: ~669,000
- Loss: MSELoss, Optimizer: Adam(lr=0.001), Epochs: 2
- **MAE: $63.97**

**So sánh Frontier Models (zero-shot, không fine-tune):**
| Model | MAE | Ghi chú |
|-------|-----|---------|
| Human (giảng viên) | $87.62 | Baseline con người |
| GPT-4.1 Nano (≈GPT-4o-mini) | $62.51 | Nhanh & rẻ |
| Gemini 2.5 Flash Lite | $58.68 | Nhanh |
| Grok 4.1 Fast | $57.62 | xAI |
| Gemini 3 Pro | $50.54 | Google |
| **Claude Opus 4.5** | **$47.10** | **🏆 Best** |

**Bài học:** Zero-shot LLM (dùng world knowledge) đã đánh bại XGBoost trained trên 800k samples.

---

### PHASE 5: Deep Neural Network Redemption (Week 6 — Day 5)

**Kiến trúc: DeepNeuralNetwork với Residual Blocks**

```python
class ResidualBlock(nn.Module):
    def forward(self, x):
        residual = x
        out = self.block(x)   # Linear → LayerNorm → ReLU → Dropout → Linear → LayerNorm
        out += residual        # Skip connection (tránh vanishing gradient)
        return self.relu(out)

class DeepNeuralNetwork(nn.Module):
    def __init__(self, input_size=5000, num_layers=10, hidden_size=4096, dropout_prob=0.2):
        self.input_layer = nn.Sequential(Linear(5000, 4096), LayerNorm, ReLU)
        self.residual_blocks = ModuleList([ResidualBlock(4096) for _ in range(10)])
        self.output_layer = nn.Linear(4096, 1)
```

**Thông số:**
- Parameters: **289 triệu** (so với 669k của Vanilla NN)
- Training: ~40 phút/epoch, 5 epochs → ~4 giờ trên GPU mạnh
- Data: Full 800k samples
- **MAE: $46.49** → Đánh bại Claude Opus 4.5 ($47.10)!

**File model đã train sẵn:** `segment4/deep_neural_network.pth`

**Bài học:** Model chuyên biệt (specialized) cho 1 tác vụ trên dữ liệu đủ lớn có thể đánh bại Frontier LLM đa năng.

**Lý do Fine-tuning GPT-4o-mini thất bại:**
- LLM Frontier đã có world knowledge khổng lồ về giá cả
- 820k samples chỉ như "muối bỏ bể", gây noise thay vì cải thiện
- Nên fine-tune LLM khi muốn thay đổi: style, format, behavior — không phải knowledge

---

### PHASE 6: Fine-tuning Llama 3.2 với QLoRA (Week 7)

**Mục tiêu:** Tạo mô hình open-source nhỏ, rẻ có performance tương đương Frontier Model

**Kỹ thuật: QLoRA = Quantization + LoRA**

**Quantization (nén model gốc):**
| Precision | VRAM Llama 3.2 3B |
|-----------|------------------|
| 32-bit | ~13 GB |
| 8-bit | ~3.6 GB |
| 4-bit (QLoRA) | ~2.2 GB |

```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",        # Normal Float 4
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16
)
```

**LoRA (chỉ train adapters nhỏ):**
```python
lora_config = LoraConfig(
    r=32,                              # Rank
    lora_alpha=64,                     # Alpha = 2 × r
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    task_type="CAUSAL_LM"
)
```

**Tính toán Adapter size (với r=32, hidden=3072, 4 modules, 28 layers):**
- 1 module: (3072×32) + (32×3072) = 196,608 params
- Total: 196,608 × 4 × 28 ≈ 22M params = **~73MB** (so với 2.2GB base)

**Môi trường training:** Google Colab T4 GPU (miễn phí)

**Base model:** `meta-llama/Llama-3.2-3B`

**Model đã fine-tune:** `SeanSunny/price-2026-final` (HuggingFace)

**Deployment:** Modal serverless GPU (T4)
```python
# segment4/khong_su_dung/pricer_service2.py (đã deploy lên modal)
@app.cls(gpu="T4", image=image, secrets=secrets)
class Pricer:
    @modal.enter()
    def setup(self):  # Load Llama + LoRA weights
    
    @modal.method()
    def price(self, description: str) -> float:
        # Prompt: "What does this cost? {description} Price is $"
```

**Notebook:** `scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune/Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb`

---

## 3. Kiến trúc hệ thống cuối (Production)

### 3.1 Ensemble Price Estimation

```
EnsembleAgent.price(description):
    rewrite = Preprocessor.preprocess(description)   # LiteLLM, default: groq/openai/gpt-oss-20b
    frontier  = FrontierAgent.price(rewrite)          # GPT-5.1 + RAG ChromaDB → 80% weight
    specialist = SpecialistAgent.price(rewrite)       # Llama-3.2-3B fine-tuned (Modal) → 10%
    neural    = NeuralNetworkAgent.price(rewrite)     # PyTorch DNN 289M params (local) → 10%
    return frontier*0.8 + specialist*0.1 + neural*0.1
```

### 3.2 App 1: search_key.py (Pipeline 4 bước)

```
User nhập keyword
    ↓
Step 1: search_and_scrape() [parallel, ThreadPoolExecutor]
    ├── BestBuy: curl_cffi + internal APIs (searchpage + priceBlocks + v2)
    └── Amazon:  curl_cffi + HTML parsing (CAPTCHA-aware, ZIP=96150)
    ↓
Step 2: combine() → List[UnifiedScrapedDeal]
    ↓
Step 3: select_top_deals() → GPT-5-nano Structured Outputs → DealSelection (top 3)
    ↓
Step 4: estimate_prices() → EnsembleAgent × 3 deals → List[Opportunity]
    ↓
Gradio HTML table (clickable URLs) + Real-time logs
Auto-notify nếu discount > $100 (Pushover)
```

### 3.3 App 2: price_is_right.py (Autonomous)

```
[Khởi động] → Load ChromaDB + memory.json
    ↓ (mỗi 5 phút)
ScannerAgent: Fetch 5 RSS feeds DealNews → GPT-5-mini chọn top 5 → DealSelection
    ↓
EnsembleAgent: estimate × 5 deals
    ↓
Sort by discount → nếu best.discount > $50: MessagingAgent → Pushover
    ↓
Save to memory.json + update Gradio dashboard
```

### 3.4 Cấu trúc file quan trọng

```
tech2ai/
├── segment4/                        # ← Toàn bộ production code
│   ├── search_key.py                # Entry point App 1
│   ├── price_is_right.py            # Entry point App 2
│   ├── multi_source_framework.py    # Framework App 1
│   ├── deal_agent_framework.py      # Framework App 2
│   ├── plan.md                      # Kế hoạch cải thiện (mới tạo 2026-05-08)
│   ├── memory.json                  # Persistent memory (deals đã xử lý)
│   ├── deep_neural_network.pth      # Weights DNN 289M params
│   ├── products_vectorstore/        # ChromaDB 800K+ products
│   ├── price_agents/                # Tất cả agents
│   │   ├── agent.py                 # Base class + ANSI logging
│   │   ├── deals.py                 # Data models (Deal, Opportunity, DealSelection)
│   │   ├── ensemble_agent.py        # Ensemble 3 models
│   │   ├── frontier_agent.py        # GPT-5.1 + RAG
│   │   ├── specialist_agent.py      # Llama Modal remote call
│   │   ├── neural_network_agent.py  # PyTorch DNN wrapper
│   │   ├── preprocessor.py          # LiteLLM text rewrite (có fallback khi API fail)
│   │   ├── multi_source_planning_agent.py  # Pipeline 4 bước (App 1)
│   │   ├── planning_agent.py        # Simple orchestrator (App 2)
│   │   ├── autonomous_planning_agent.py    # GPT-5.1 controller (App 2 default)
│   │   ├── scanner_agent.py         # RSS scanner (App 2)
│   │   ├── messaging_agent.py       # Pushover notifications
│   │   ├── bestbuy_deals.py         # BestBuy scraper
│   │   └── amazon_deals.py          # Amazon scraper
│   └── bestbuy_untils/              # Utilities (tên folder có typo, intentional)
│       ├── multi_source_scanner_agent.py   # GPT-5-nano chọn top 3
│       ├── unified_deal.py          # Normalize BestBuy + Amazon → UnifiedScrapedDeal
│       └── gradio_helpers.py        # QueueHandler, HTML formatters
├── scraping_data_tv/                # Data processing & fine-tune code (untracked)
│   └── Data_processing_for_English_data/
│       ├── Code_Data_processing/    # day1-4 notebooks + pricer/ utilities
│       └── Code_Fine_tune/          # Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb
└── w8/                              # Notebooks tuần 8
    └── d1_specialist_agent.ipynb    # Notes về Modal warm-up
```

---

## 4. Tech Stack

| Component | Technology |
|-----------|-----------|
| Python | 3.12, `uv` package manager |
| LLM (Frontier) | GPT-5.1, GPT-5-nano (OpenAI) |
| LLM (Specialist) | Llama-3.2-3B fine-tuned LoRA, deployed Modal T4 |
| Neural Network | PyTorch DNN ResidualBlocks, 289M params |
| Vector DB | ChromaDB + sentence-transformers/all-MiniLM-L6-v2 |
| LLM Abstraction | LiteLLM (multi-provider) |
| Web Scraping | curl_cffi (Chrome impersonation) + BeautifulSoup4 |
| UI | Gradio |
| Notifications | Pushover API |
| Fine-tune | QLoRA (bitsandbytes + PEFT), Google Colab T4 |
| Serverless GPU | Modal.com |
| Dataset | HuggingFace: SeanSunny/items_lite, SeanSunny/items_full, SeanSunny/price-2026-final |

---

## 5. Environment Variables (.env trong segment4/)

```env
OPENAI_API_KEY=sk-xxx              # Bắt buộc
PUSHOVER_USER=xxx                  # Tùy chọn (notifications)
PUSHOVER_TOKEN=xxx                 # Tùy chọn
PRICER_PREPROCESSOR_MODEL=groq/openai/gpt-oss-20b   # Default nếu không đặt: ollama/llama3.2
GROQ_API_KEY=xxx                   # Nếu dùng Groq cho preprocessor
HF_TOKEN=hf_xxx                    # Cho Modal download Llama weights
```

---

## 6. Lỗi đã fix & Lessons learned

### Fix đã thực hiện (2026-05-08)

**`preprocessor.py` — Groq API 522 timeout:**
- Lỗi: Groq server trả về 522 Connection Timeout → crash toàn bộ pipeline
- Fix: Thêm try-except trong `preprocess()`, fallback trả về text gốc thay vì crash
- File: `segment4/price_agents/preprocessor.py`

### Lessons về reliability

1. **Groq API không ổn định** — luôn cần fallback
2. **Modal Llama cold start** — lần đầu chạy sau khi container ngủ: 30-60s
3. **Amazon CAPTCHA** — curl_cffi + Chrome impersonation giảm thiểu nhưng không loại hoàn toàn
4. **BestBuy product pages bị block từ WSL2** — dùng internal APIs thay vì scrape HTML
5. **Preprocessor dùng Groq** — set `PRICER_PREPROCESSOR_MODEL=groq/openai/gpt-oss-20b`, cần GROQ_API_KEY

---

## 7. Kế hoạch cải thiện (plan.md)

Chi tiết đầy đủ: `segment4/plan.md`

| Thứ tự | Feature | Trạng thái |
|--------|---------|------------|
| 1 | **Pipeline Profiling** — Đo thời gian từng bước | Chưa làm |
| 2 | **Modal Warm-up Button** — Thêm button Gradio gọi `pricer.update_autoscaler(scaledown_window=1200)` | Chưa làm |
| 3 | **SQLite Deal History** — Lưu deals vào DB, hiển thị price history chart | Chưa làm |
| 4 | **Review Sentiment Agent** — Scrape Amazon reviews + GPT-5-nano phân tích | Chưa làm |

**Để warm up Modal thủ công (từ notebook d1_specialist_agent.ipynb):**
```python
import modal
Pricer = modal.Cls.from_name("pricer-service", "Pricer")
pricer = Pricer()
pricer.update_autoscaler(scaledown_window=1200)  # Giữ warm 20 phút
```

---

## 8. Hướng dẫn chạy

```bash
# Cài dependencies
cd tech2ai && uv sync

# App 1: Search by keyword
cd segment4 && uv run search_key.py
# → http://127.0.0.1:7860

# App 2: Autonomous RSS hunter
cd segment4 && uv run price_is_right.py
# → http://127.0.0.1:7860

# Deploy Modal service (nếu cần)
cd segment4 && uv run modal deploy -m khong_su_dung.pricer_service2
```

---

## 9. Những gì đã làm — Session 2 (2026-05-08)

### Tài liệu đã tạo

**`scraping_data_tv/Data_processing_for_English_data/Report_data_processing_v2.md`** (MỚI)

Report chi tiết toàn bộ quy trình Day 1–5 + Redemption DNN. Cover:
- **Day 1:** `items.py`, `parser.py`, `loaders.py`, `day1.ipynb` — giải thích từng hàm + lý do kỹ thuật
- **Day 2:** `preprocessor.py`, `batch.py` — Groq Batch API pipeline đầy đủ
- **Day 3:** `evaluator.py`, `day3.ipynb` — 6 baseline models + bảng MAE
- **Day 4:** `day4.ipynb` — Vanilla NN + Frontier LLMs so sánh
- **Redemption:** `deep_neural_network.py`, `redemption_train.ipynb` — ResidualBlock, Skip Connection, Log-normalize, AdamW, CosineAnnealingLR
- Style: Tiếng Việt + English thuật ngữ kỹ thuật có giải thích trong ngoặc

---

## 10. Câu hỏi cần trả lời trong session tiếp theo

Đây là các vấn đề chưa giải quyết / cần làm tiếp:

1. **Demo cho giáo viên** — Nên search keyword nào để demo tốt nhất?
   - Gợi ý tốt nhất: `wireless headphones`, `gaming monitor`, `acoustic guitar`, `air fryer`
   - Sweet spot giá: $80–$400 (Electronics/Instruments/Appliances, không bị downsampled)
   - Tránh: Automotive parts (95% downsampled, model ít data)

2. **Báo cáo giáo viên còn thiếu** — Cần tạo thêm:
   - `report_fine_tune_llm.md` — QLoRA Week 7 (fine-tune Llama 3.2)
   - `report_system.md` — search_key + price_is_right architecture

3. **Bắt đầu feature từ plan.md** — Pipeline Profiling trước (ưu tiên 1)

4. **Kiểm tra file tài liệu còn thiếu:**
   - `scraping_data_tv/Data_processing_for_English_data/Data_processing_for_English_data.txt` — File rất lớn (74k tokens), chưa đọc hết
   - `fine_tune_LLM.txt` — File rất lớn (67k tokens), chưa đọc hết (mới đọc ~400 dòng đầu về QLoRA Week 7 Day 1)

---

## 11. Prompt cho session tiếp theo

Dán đoạn sau vào đầu session mới:

```
Đọc các file sau để nắm ngữ cảnh (theo thứ tự):
1. SESSION_HANDOFF_NLP.md — trạng thái tổng thể dự án
2. segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md — kiến trúc App 1
3. segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md — kiến trúc App 2

Dự án hiện tại: "The Price Is Right" — AI Price Intelligence System (DACN3)
Nhánh git: claudedev | Working dir: /home/hieu0606sunny/price2026wsl/tech2ai

Những gì đã hoàn thành:
- Report_data_processing_v2.md: tài liệu chi tiết Day 1-5 + Redemption DNN
- Report_data_processing.md (v1): tài liệu tổng quan hành trình
- Cả hai app (search_key.py, price_is_right.py) đang hoạt động production

Việc cần làm tiếp (chọn 1):
A) Viết report_fine_tune_llm.md — đọc fine_tune_LLM.txt + Code_Fine_tune/Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb
B) Viết report_system.md — mô tả kiến trúc 2 apps cho giáo viên
C) Implement feature từ segment4/plan.md — Pipeline Profiling (đo thời gian từng bước)
D) Chuẩn bị demo cho giáo viên — test app với các keywords tốt nhất
```

---

## 10. Bảng xếp hạng cuối — "The Price Is Right" Leaderboard

| Hạng | Model | Loại | MAE | Ghi chú |
|------|-------|------|-----|---------|
| 1 | GPT-5.1 (giả định) | Frontier LLM | <$46 | Vua |
| 2 🏅 | **Deep Neural Network** | Specialized DL | **$46.49** | Tự xây! 289M params |
| 3 | Claude Opus 4.5 | Frontier LLM | $47.10 | Bị DNN đánh bại |
| 4 | Gemini 3 Pro | Frontier LLM | $50.54 | |
| 5 | Grok 4.1 Fast | Fast LLM | $57.62 | |
| 6 | Gemini 2.5 Flash | Fast LLM | $58.68 | |
| 7 | GPT-4.1 Nano | Fast LLM | $62.51 | ≈GPT-4o-mini |
| 8 | Vanilla Neural Net | Basic DL | $63.97 | 8 lớp PyTorch |
| 9 | XGBoost | ML | $68.23 | Best traditional ML |
| 10 | NLP Linear Regression | ML | $76.81 | BoW + CountVectorizer |
| 11 | Human | Bio | $87.62 | Giảng viên |
| 12 | Random Forest | ML | $72.28 | |
| 13 | Constant Pricer | Trivial | $106.18 | Đoán trung bình |
| 14 | Random Pricer | Trivial | $382.08 | Đoán mò |

*Metric: Mean Absolute Error (MAE) trên tập test 200 mẫu*

---

*File này cần được update mỗi khi có thay đổi lớn về kiến trúc, tính năng mới hoặc kết quả quan trọng.*
