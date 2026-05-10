# SESSION HANDOFF — Dự án NLP "The Price Is Right"

> **Mục đích file này:** Cung cấp toàn bộ ngữ cảnh cho AI session tiếp theo để tiếp tục làm việc mà không cần đọc lại toàn bộ tài liệu.
>
> **Ghi chú quan trọng:** File này KHÔNG phải báo cáo cho giáo viên. Báo cáo sẽ được tạo riêng thành các file .md tách biệt cho từng phần:
> - `report_data_processing.md` — Xử lý dữ liệu (Day 1-2)
> - `report_fine_tune_llm.md` — Fine-tune Llama 3.2 (Week 7)
> - `report_system.md` — Xây dựng hệ thống (search_key + price_is_right)
>
> **Ngày cập nhật:** 2026-05-10 (session 3)
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

---

### PHASE 2: Data Pre-processing with LLM (Week 6 — Day 2)

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

**Kết quả:** Dataset lên HuggingFace: `SeanSunny/items_lite` (22k) và `SeanSunny/items_full` (820k)

---

### PHASE 3: Baseline Models — Traditional ML (Week 6 — Day 3)

| Model | MAE | Ghi chú |
|-------|-----|---------|
| Random Pricer | $382.08 | Đoán mò |
| Constant Pricer | $106.18 | Đoán giá trung bình $140.56 |
| Linear Regression (manual) | $101.56 | |
| NLP Linear Regression (BoW) | $76.81 | CountVectorizer 2000 từ |
| Random Forest | $72.28 | 100 trees |
| XGBoost | $68.23 | 1000 trees, full dataset |

---

### PHASE 4: Neural Networks + Frontier Models (Week 6 — Day 4)

**Vanilla NN:** 8 lớp, 669k params → **MAE $63.97**

**Frontier Models (zero-shot):**
| Model | MAE |
|-------|-----|
| Human (giảng viên) | $87.62 |
| GPT-4.1 Nano | $62.51 |
| Gemini 2.5 Flash Lite | $58.68 |
| Grok 4.1 Fast | $57.62 |
| Gemini 3 Pro | $50.54 |
| **Claude Opus 4.5** | **$47.10** |

**Bài học:** Zero-shot LLM đánh bại XGBoost trained 800k samples.

---

### PHASE 5: Deep Neural Network Redemption (Week 6 — Day 5)

**Kiến trúc:** HashingVectorizer(5000, binary=True) → Linear(5000→4096) + 8 ResidualBlocks(4096) + output

**Lưu ý quan trọng:** Model dùng **HashingVectorizer**, không phải BoW (CountVectorizer). Khác biệt:
- HashingVectorizer: hashing trick, stateless, không lưu vocabulary, không có OOV
- BoW (CountVectorizer): lưu vocabulary, cần fit trước, OOV → bỏ qua

**Thông số:** 289M params, 5 epochs, ~4h trên GPU  
**Test MAE: $46.02** — Thắng Claude Opus 4.5 ($47.10)

**File model:** `segment4/deep_neural_network.pth`

---

### PHASE 6: Fine-tuning Llama 3.2 với QLoRA (Week 7)

**Kỹ thuật:** QLoRA = 4-bit quantization + LoRA adapters (r=32, ~22M params, ~73MB)  
**Base model:** `meta-llama/Llama-3.2-3B`  
**Trained model:** `SeanSunny/price-2026-final` (HuggingFace)  
**Deployment:** Modal serverless T4 GPU (`pricer_service2.py`)

---

### PHASE 7: DL Model Experiments (Session 3 — 2026-05-10)

**Câu hỏi nghiên cứu:** Semantic representation (SentTrans, DistilBERT) có cải thiện HashingVec DNN không?

**Kết quả đã train:**

| Model | File | Epochs | Val MAE (best) | Test MAE |
|-------|------|--------|---------------|----------|
| HashingVec DNN (baseline) | `deep_neural_network.py` | 5 | $53.84 | **$46.02** |
| SentTrans frozen (1024) | `sentence_transformer_model.py` | 15 | $56.24 | $47.56 |
| SentTrans frozen (4096) | `sentence_transformer_model.py` | 15 | $49.99 | **$43.78** |
| DistilBERT CLS V1 (batch=32) | `distilbert_model.py` | 5 | $47.42 | $44.19 |

**Nhận xét quan trọng:**
- SentTrans 1024 tệ hơn DNN vì 13M params không đủ capacity so với 289M của DNN
- SentTrans 4096 tốt hơn DNN — capacity lớn hơn là yếu tố quan trọng, không chỉ semantic
- DistilBERT V1 val MAE vẫn giảm đều tại epoch 5 → chưa hội tụ, cần train thêm
- HashingVec mạnh vì: dữ liệu đã LLM pre-process (brand/category explicit), price là keyword-driven

**4 models mới được thiết kế + code (TODO train):**

| Model | File `.py` | Notebook | Thay đổi chính |
|-------|------------|----------|---------------|
| DistilBERT V2 | `distilbert_model_v2.py` | `model2_distilbert_train_v2.ipynb` | batch=64, 15 epochs |
| DistilBERT V3 | `distilbert_model_v3.py` | `model2_distilbert_train_v3.ipynb` | Mean pooling thay CLS |
| SentTrans E2E | `senttrans_e2e_model.py` | `model3_senttrans_e2e_train.ipynb` | Encoder fine-tuned, LR=5e-5 |
| Feature Fusion | `fusion_model.py` | `model4_fusion_train.ipynb` | HashingVec(512) + SentTrans(512) → concat(1024) |

**Design doc đầy đủ:** `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/2026-05-08-dl-models-design.md`

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
User nhập keyword → search_and_scrape() [BestBuy + Amazon parallel, curl_cffi]
→ combine() → List[UnifiedScrapedDeal]
→ select_top_deals() [GPT-5-nano Structured Outputs] → DealSelection (top 3)
→ estimate_prices() [EnsembleAgent × 3 deals] → List[Opportunity]
→ Gradio HTML table + logs | Auto-notify discount > $100
```

### 3.3 App 2: price_is_right.py (Autonomous)

```
[every 5 min] → Fetch 5 RSS DealNews → GPT-5-mini top 5
→ EnsembleAgent estimate × 5 deals
→ Sort by discount → if best > $50: Pushover notification
→ Save memory.json + update Gradio dashboard
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
PUSHOVER_USER=xxx                  # Tùy chọn
PUSHOVER_TOKEN=xxx                 # Tùy chọn
PRICER_PREPROCESSOR_MODEL=groq/openai/gpt-oss-20b
GROQ_API_KEY=xxx
HF_TOKEN=hf_xxx
```

---

## 6. Lỗi đã fix & Lessons learned

- **`preprocessor.py` Groq 522 timeout** (2026-05-08): Thêm try-except, fallback trả về text gốc
- **Groq API không ổn định** — luôn cần fallback
- **Modal Llama cold start** — 30-60s lần đầu sau khi container ngủ
- **BestBuy WSL2 block** — dùng internal APIs thay scrape HTML

---

## 7. Kế hoạch cải thiện (segment4/plan.md)

| Thứ tự | Feature | Trạng thái |
|--------|---------|------------|
| 1 | Pipeline Profiling — Đo thời gian từng bước | Chưa làm |
| 2 | Modal Warm-up Button — Gradio button gọi `update_autoscaler` | Chưa làm |
| 3 | SQLite Deal History — price history chart | Chưa làm |
| 4 | Review Sentiment Agent — Amazon reviews + GPT | Chưa làm |

---

## 8. Hướng dẫn chạy

```bash
cd tech2ai && uv sync
cd segment4 && uv run search_key.py        # App 1 → http://127.0.0.1:7860
cd segment4 && uv run price_is_right.py    # App 2 → http://127.0.0.1:7860
```

---

## 9. Lịch sử sessions

### Session 1 (2026-05-xx)
- Xây dựng toàn bộ hệ thống production (search_key + price_is_right)
- Fine-tune Llama 3.2 QLoRA, deploy Modal

### Session 2 (2026-05-08)
- Fix `preprocessor.py` Groq 522 timeout
- Tạo `Report_data_processing_v2.md` — tài liệu chi tiết Day 1-5 + Redemption DNN

### Session 3 (2026-05-10) — Hiện tại
- Phân tích kết quả Model 1 (SentTrans) và Model 2 V1 (DistilBERT)
- Thảo luận tại sao HashingVec DNN mạnh (keyword-driven price, LLM pre-processed data)
- Thiết kế và implement 4 models mới: DistilBERT V2/V3, SentTrans E2E, Feature Fusion
- Cập nhật `2026-05-08-dl-models-design.md` với kết quả thực tế + design mới
- Commit `56e4150` push lên `claudedev`
- **Đang chờ:** Train 4 notebooks trên GPU thuê (RTX 5090 32GB)

---

## 10. Câu hỏi / việc cần làm trong session tiếp theo

1. **[NGAY] Cập nhật kết quả train 4 models mới** — nhận kết quả test MAE từ 4 notebooks và cập nhật vào design doc + SESSION_HANDOFF + leaderboard

2. **Báo cáo cho giáo viên còn thiếu:**
   - `report_fine_tune_llm.md` — QLoRA Week 7
   - `report_system.md` — kiến trúc 2 apps

3. **Demo cho giáo viên** — keyword tốt nhất: `wireless headphones`, `gaming monitor`, `acoustic guitar`, `air fryer` (giá $80-$400, tránh Automotive)

4. **Features từ plan.md** — Pipeline Profiling là ưu tiên 1

---

## 11. Prompt cho session tiếp theo (SAU KHI TRAIN XONG)

```
Đọc file sau để nắm ngữ cảnh:
SESSION_HANDOFF_NLP.md
scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/2026-05-08-dl-models-design.md

Dự án: "The Price Is Right" — AI Price Intelligence System (DACN3)
Nhánh git: claudedev | Working dir: /home/hieu0606sunny/price2026wsl/tech2ai

Kết quả train đã có (cần cập nhật vào doc):
- Model 2 V2 (DistilBERT CLS, batch=64, 15 epochs): Test MAE = ???
- Model 2 V3 (DistilBERT mean pooling, batch=64, 15 epochs): Test MAE = ???
- Model 3 (SentTrans E2E fine-tuned, batch=128, 15 epochs): Test MAE = ???
- Model 4 (Feature Fusion HashingVec+SentTrans, batch=256, 15 epochs): Test MAE = ???

Việc cần làm:
1. Cập nhật kết quả vào 2026-05-08-dl-models-design.md (section 11 Implementation Status + section 13 Leaderboard)
2. Cập nhật SESSION_HANDOFF_NLP.md leaderboard
3. Commit + push
4. Thảo luận: model nào tốt nhất? Có nên tích hợp vào EnsembleAgent không?
5. Tùy kết quả: viết report DL models cho báo cáo giáo viên
```

---

## 12. Leaderboard — "The Price Is Right"

*Metric: Mean Absolute Error (MAE) trên tập test 200 mẫu*

| Hạng | Model | Loại | MAE | Ghi chú |
|------|-------|------|-----|---------|
| ? | DistilBERT V2 (15 epochs) | Fine-tuned LM | TBD | Chờ train |
| ? | DistilBERT V3 (mean pool) | Fine-tuned LM | TBD | Chờ train |
| ? | SentTrans E2E | Fine-tuned LM | TBD | Chờ train |
| ? | Feature Fusion | Hybrid DL | TBD | Chờ train |
| 1 | SentTrans frozen (4096) | Specialized DL | **$43.78** | Model 1 |
| 2 | DistilBERT V1 (5 epochs) | Fine-tuned LM | $44.19 | Chưa hội tụ |
| 3 | HashingVec DNN | Specialized DL | $46.02 | Baseline |
| 4 | Claude Opus 4.5 | Frontier LLM | $47.10 | Zero-shot |
| 5 | SentTrans frozen (1024) | Specialized DL | $47.56 | Capacity nhỏ |
| 6 | Gemini 3 Pro | Frontier LLM | $50.54 | |
| 7 | Grok 4.1 Fast | Fast LLM | $57.62 | |
| 8 | Gemini 2.5 Flash | Fast LLM | $58.68 | |
| 9 | GPT-4.1 Nano | Fast LLM | $62.51 | |
| 10 | Vanilla Neural Net | Basic DL | $63.97 | 8 lớp, 669k params |
| 11 | XGBoost | ML | $68.23 | Best traditional ML |
| 12 | NLP Linear Regression | ML | $76.81 | BoW + CountVec |
| 13 | Human (giảng viên) | Bio | $87.62 | |
| 14 | Random Forest | ML | $72.28 | |
| 15 | Constant Pricer | Trivial | $106.18 | |
| 16 | Random Pricer | Trivial | $382.08 | |

---

*File này cần được update mỗi khi có thay đổi lớn về kiến trúc, tính năng mới hoặc kết quả quan trọng.*
