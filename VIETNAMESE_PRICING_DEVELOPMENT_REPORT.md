# Báo Cáo Phát Triển Hệ Thống Ước Giá Sản Phẩm Tiếng Việt

**Ngày báo cáo:** 2026-07-12
**Người thực hiện:** Phạm Minh Hiếu — Sunny-sunnyy
**Mục đích:** Đồ án tốt nghiệp (DATN) — Trợ lý mua sắm thông minh tiếng Việt
**Phạm vi:** Báo cáo toàn bộ quá trình từ scraping dữ liệu, tiền xử lý, tăng cường dữ liệu, đến huấn luyện các mô hình ML/DL/LLM cho bài toán ước giá sản phẩm tiếng Việt.

> File này được tạo ra để coding agent (Claude Code) có thể nhanh chóng nạp lại toàn bộ ngữ cảnh dự án mà không cần đọc từng file .md riêng lẻ. Mỗi phần đều có tham chiếu (link) đến file nguồn chi tiết và thư mục code tương ứng.

---

## 1. Tổng Quan và Mục Tiêu

### 1.1. Nguồn gốc

Dự án phát triển từ hệ thống "AI Price Intelligence System" (tiếng Anh, thị trường Mỹ) — một multi-agent system tìm deal trên BestBuy/Amazon, ước giá bằng ML ensemble, và gửi push notification. Phiên bản mới chuyển hoàn toàn sang tiếng Việt, thị trường Việt Nam.

**Tài liệu tham chiếu:**
- [Project_Development_Plan.md](segment4/mo_ta_du_an/Project_Development_Plan.md) — Kế hoạch 8 tháng (04/2026–12/2026)
- [README.md](README.md) — Tổng quan repo, trạng thái hiện tại

### 1.2. Kiến trúc mục tiêu

Kiến trúc hybrid B+C (theo [Project_Development_Plan.md](segment4/mo_ta_du_an/Project_Development_Plan.md) Section 1.3):

- **Tầng B (Router):** Qwen2.5-7B-Instruct phân loại intent người dùng thành 4 nhánh (hỏi đáp / tìm sản phẩm / so sánh giá / tư vấn)
- **Tầng C (ReAct):** Nhánh tìm sản phẩm được nâng cấp thành ReAct agent (Thought → Action → Observation → lặp lại)
- **Ensemble ước giá:** Giữ nguyên kiến trúc 3 mô hình (Frontier 80% + Specialist 10% + DNN 10%), thay bằng các mô hình fine-tuned trên dữ liệu tiếng Việt

### 1.3. Các giai đoạn

| Giai đoạn | Thời gian dự kiến | Nội dung | Trạng thái |
|-----------|-------------------|----------|-----------|
| Giai đoạn 1 | Tháng 1-3 | Thu thập & xử lý dữ liệu tiếng Việt | **HOÀN TẤT** |
| Giai đoạn 2 | Tháng 3-5 | Huấn luyện mô hình tiếng Việt | **ĐANG THỰC HIỆN** |
| Giai đoạn 3 | Tháng 4-6 | Pipeline scraping sàn TMĐT Việt Nam | Chưa bắt đầu |
| Giai đoạn 4 | Tháng 5-7 | Chatbot trợ lý mua sắm | Chưa bắt đầu |
| Giai đoạn 5 | Tháng 7-8 | Hoàn thiện, testing & viết báo cáo | Chưa bắt đầu |

### 1.4. Lịch sử phát triển

```
2026-04-09 ... 2026-04-15: Day 0-3 — Scraping + Data Curation + Baseline ML
2026-04-15 ... 2026-04-24: Day 4 — Deep Learning BERT models (v1 → v8 stacking)
2026-04-24 ... 2026-05-02: Day 5 — QLoRA Qwen3.5-4B (v0/v1/v3/v4)
2026-05-02 ... 2026-05-19: Day 4 v2 — BERT Vietnamese models (NB01-NB14)
2026-05-19:              Qwen V2 — MAE-optimized rewrite (code done, chưa train)
2026-05-19 ... 2026-07-12: GIÁN ĐOẠN 3 THÁNG — không hoạt động
```

---

## 2. Giai Đoạn 1: Thu Thập và Xử Lý Dữ Liệu Tiếng Việt

**Thư mục code:**
- [`scraping_data_tv/Tiki/`](scraping_data_tv/Tiki/) — Tiki scraper (`curl_cffi` + BeautifulSoup4)
- [`scraping_data_tv/e-commerce-sites-scraping/`](scraping_data_tv/e-commerce-sites-scraping/) — Scraper có sẵn (Hasaki, WinMart, CoopMart, BiboMart, ConCung...)
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/`](scraping_data_tv/Data_processing_for_Vietnamese_data/) — Toàn bộ pipeline xử lý dữ liệu
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/day1/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day1/) — Day 1 notebooks
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/day2/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day2/) — Day 2 notebooks

**Tài liệu tham chiếu:**
- [plan_data_preprocessing_vi.md](scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md) — Kế hoạch chi tiết Day 0-4
- [data_augmentation.md](fine_tune_qwen/data_augmentation.md) — Pipeline từ scraping đến augmentation
- [SESSION_HANDOFF.md](scraping_data_tv/SESSION_HANDOFF.md) — Session logs Day 3/4/5

### 2.1. Thu thập dữ liệu (Day 0)

**4 nguồn dữ liệu — 158,362 sản phẩm thô:**

| Nguồn | Phương pháp | Số SP | Chất lượng | Thư mục |
|-------|-------------|-------|-----------|---------|
| Tiki (scraper) | `curl_cffi` + BeautifulSoup, crawl 111/113 danh mục | 102,117 | Mô tả dài 2K-3K ký tự, tốt nhất | [`Tiki/`](scraping_data_tv/Tiki/) |
| Kaggle | CSV công khai | 41,603 | Mô tả ngắn ~188 ký tự, chủ yếu Thời Trang | — |
| Hasaki | Requests (JSON API), 128/130 danh mục | 11,410 | Tập trung Làm Đẹp – Sức Khỏe | [`e-commerce-sites-scraping/`](scraping_data_tv/e-commerce-sites-scraping/) |
| WinMart | Selenium, 18 danh mục | 3,232 | Hàng FMCG giá thấp 5K-50K VND | [`e-commerce-sites-scraping/`](scraping_data_tv/e-commerce-sites-scraping/) |

Định dạng JSONL: `title`, `category`, `price`, `full` (mô tả gốc), `brand`.

### 2.2. Pipeline làm sạch (Day 1 — 9 bước)

Thư mục: [`Data_processing_for_Vietnamese_data/day1/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day1/)

```
Dữ liệu thô  →  [1] NFC normalize  →  [2] Lọc HTML entities  →  [3] Xóa emoji
             →  [4] Xóa SKU/mã SP   →  [5] Chuẩn hóa khoảng trắng
             →  [6] Lọc giá 1K-50M VND  →  [7] Lọc tối thiểu 50 ký tự
             →  [8] Dedup theo title  →  [9] Dedup theo full text
```

**Kết quả dedup:** 158,362 → 146,850 SP (loại bỏ 11,512 = 7.3% trùng lặp)

### 2.3. Weighted Sampling — Cân bằng dữ liệu

**Vấn đề:** Thời Trang chiếm 38% raw (chủ yếu từ Kaggle, chất lượng thấp), Bách Hóa bị ép vì giá quá rẻ.

**Giải pháp:** Kết hợp `price²` weighting + category penalty:

```python
CATEGORY_PENALTIES = {
    "Thời Trang":          0.40,  # 38% raw → 25% final
    "Nhà Cửa - Đời Sống":  0.60,  # 22% raw → 25% final
}
```

**8 danh mục sau sampling:**

| Danh mục | Trước (raw %) | Sau (final %) |
|----------|--------------|---------------|
| Thời Trang | 38% | 25% |
| Nhà Cửa - Đời Sống | 22% | 25% |
| Điện Tử - Công Nghệ | 15% | 19% |
| Làm Đẹp - Sức Khỏe | 14% | 13% |
| Mẹ và Bé | 5% | 6% |
| Điện Lạnh - Gia Dụng | 4% | 5% |
| Bách Hóa | 5% | 5% |
| Ô Tô - Xe Máy | 2% | 2% |

**Dataset đầu ra:** `SeanSunny/items_raw_tv_v6` — 110,000 SP (100K train / 5K val / 5K test)

### 2.4. LLM Preprocessing (Day 2) — Groq Batch API

Thư mục: [`Data_processing_for_Vietnamese_data/day2/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day2/)

**Package:** [`pricer_vi/`](scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/) — `preprocessor.py`, `batch.py`, `items.py`, `parser.py`

**Thiết kế quan trọng:** LLM chỉ tạo 2 trường (Mô tả + Thông số), 3 trường Tiêu đề/Danh mục/Thương hiệu giữ nguyên từ data gốc → đảm bảo chính xác 100%.

**System prompt:**
```
Tạo mô tả ngắn gọn cho một sản phẩm. Chỉ trả lời đúng 2 dòng theo định dạng sau.
Không bao gồm mã sản phẩm.
Mô tả: 1 câu mô tả sản phẩm
Thông số: 1 câu về tính năng nổi bật
```

**Định dạng summary 5 dòng:**
```
Tiêu đề: [data gốc]
Danh mục: [data gốc]
Thương hiệu: [data gốc hoặc "Không rõ"]
Mô tả: [LLM tạo]
Thông số: [LLM tạo]
```

| Thông số | Giá trị |
|----------|---------|
| Model | `openai/gpt-oss-20b` qua Groq Batch API |
| Số batch | 120 (1,000 items/batch) |
| Tổng requests | ~120,000 |
| Avg tokens/item | ~640 input + 97 output |
| Chi phí | ~$9-10 |
| Thời gian | ~20-30 phút |

**Dataset đầu ra:** `SeanSunny/items_tv_v6` — 110,000 SP, thêm cột `summary` (5 dòng)

### 2.5. Data Augmentation (Stage 2) — 85K → 269K

**Code:** [`fine_tune_qwen/08_augment_dataset_v4_version3.ipynb`](fine_tune_qwen/08_augment_dataset_v4_version3.ipynb),
[`fine_tune_qwen/08_augment_dataset_v4_version4.ipynb`](fine_tune_qwen/08_augment_dataset_v4_version4.ipynb),
[`fine_tune_qwen/push_dataset_v4.py`](fine_tune_qwen/push_dataset_v4.py)

**Tài liệu:** [data_augmentation.md](fine_tune_qwen/data_augmentation.md) (Giai đoạn 4)

**Chiến lược: Price Bucket Multiplier A5**

| Nhóm giá | Hệ số nhân | Lý do |
|-----------|-----------|-------|
| < 50K VND | 5× | FMCG rẻ — model hay bias cao |
| 50-100K | 3× | Phổ biến nhưng thiếu đa dạng |
| 100-200K | 2× | Cần thêm biến thể |
| 200-500K | 1× | Đã đủ, KHÔNG augment |
| 500K-1M | 4× | Outlier tail, hard cases |

**Cơ chế:** LLM viết lại chỉ 2 dòng (Mô tả + Thông số) theo cách khác, giữ nguyên 3 dòng header. Dùng `full` (mô tả gốc ~2K ký tự) làm ngữ cảnh.

**Kết quả augmentation:**

| Chỉ số | Giá trị |
|--------|---------|
| Tổng requests gửi đi | 185,584 |
| Số batch | 186 |
| Parse thành công | **183,385** (98.8%) |
| Parse thất bại (format sai) | 2,199 (1.2%) |
| Model | `openai/gpt-oss-20b` |
| Chi phí | ~$3-5 |

**Output cuối cùng:** `items_prompts_tv_4` (train: 85,727 gốc + 183,385 aug = **269,112**), shuffle seed=42

### 2.6. Dataset inventory (HuggingFace Hub)

Tất cả dataset dưới org `SeanSunny`:

| Dataset | Bước tạo | Train | Val | Test | Các cột chính | Mục đích |
|---------|-------|-------|-----|------|--------------|----------|
| `items_raw_tv_v6` | Day 1 | 100,000 | 5,000 | 5,000 | title, category, price, full, brand | Dữ liệu sau làm sạch |
| `items_tv_v6` | Day 2 | 110,000 | 5,000 | 5,000 | + summary (5 dòng) | Sau LLM preprocessing |
| `items_tv_v7` | Aug prep | 110,000 | 5,000 | 5,000 | + full merge lại | Chuẩn bị augmentation |
| `items_tv_v8` | Aug output | 183,385 | 5,000 | 5,000 | + summary_version2, aug_version | Augmented rows |
| `items_prompts_tv_3` | Fine-tune prep | 85,727 | 3,926 | 3,872 | prompt, completion, price_vnd_true | Prompt cho Qwen v1/v3 (lọc ≤ 1M VND) |
| **`items_prompts_tv_4`** | **Augmented** | **269,112** | **3,926** | **3,872** | prompt, completion, price_vnd_true | Prompt cho Qwen v4/V2 |
| `items_tv_v9` | Day3/4 retrain | 269,112 | 3,926 | 3,872 | title, category, brand, summary, price | Dataset cho Day3/Day4 retrain |

**Tổng chi phí LLM:**

| Giai đoạn | Model | Requests | Chi phí |
|-----------|-------|----------|---------|
| Day 2 — chuẩn hóa summary | gpt-oss-20b | 120,000 | ~$9-10 |
| Stage 2 — augmentation | gpt-oss-20b | 185,584 | ~$3-5 |
| **Tổng** | | **305,584** | **~$13-15** |

### 2.7. Định dạng prompt cho fine-tuning

```
[PROMPT]
Sản phẩm này có giá bao nhiêu ?
Tiêu đề: {title}
Danh mục: {category}
Thương hiệu: {brand}
Mô tả: {description}
Thông số: {features}

Giá là:
```

**Completion:** `round(price / 1000)` — ví dụ 150,000 VND → `"150"`. Lý do: đưa về đơn vị nghìn đồng giúp model sinh số ngắn (2-4 chữ số) thay vì 6-7 chữ số, giảm `max_new_tokens` từ ~8 xuống còn 4 token.

---

## 3. Giai Đoạn 2: Baseline ML Models (Day 3)

**Thư mục code:**
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/day3/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day3/) — Day 3 gốc (120K data)
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/day3_v2/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day3_v2/) — Day 3 v2 (retrain với 269K)
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi_2/`](scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi_2/) — Package V2: `items.py`, `evaluator.py`

**Tài liệu tham chiếu:**
- [SESSION_HANDOFF.md](scraping_data_tv/SESSION_HANDOFF.md) — Session 14-17 (Day 3 v2 execution)

### 3.1. Day 3 gốc (120K data)

- 12 models: Random, Mean, Median, LR, Ridge, RF, XGBoost, LightGBM, CatBoost, LGB Tuned, Blended
- 3 kiến trúc tokenization: TF-IDF n-gram (A), Underthesea + TF-IDF word (B), Underthesea + FeatureUnion (C)
- Best: **Blended RMSLE=0.5164**, MAE=110K, MAPE=44.0%, R²=47.1%
- Log-transform là cải thiện lớn nhất (-8.8% RMSLE)

### 3.2. Day 3 v2 (269K data — items_tv_v9)

**Notebook:** [`day3_v2/day3_v2_baseline_ml.ipynb`](scraping_data_tv/Data_processing_for_Vietnamese_data/day3_v2/day3_v2_baseline_ml.ipynb) + [`day3_v2/day3_v2_section5.ipynb`](scraping_data_tv/Data_processing_for_Vietnamese_data/day3_v2/day3_v2_section5.ipynb)

**Thay đổi so với Day 3 gốc:**
- Primary metric: **MAE** (thay vì RMSLE) — vì price range 5-1000 đã giống English (1-999)
- Bỏ log1p transform — train trên raw price

**Kết quả các model:**

| Model | MAE (VND) | Ghi chú |
|-------|-----------|---------|
| 5A: LGB + char_wb 269K (MSE) | **92,600** | **TỐT NHẤT** |
| 5B: LGB + char_wb 269K (MAE obj) | 95,100 | |
| 5F: LGB + CountVect word 50K (MSE) | 97,300 | |
| 5G: LGB + CountVect word 50K (MAE obj) | 100,000 | |
| 5E: XGBoost + CountVect word 50K | 113,200 | |
| 5D: RF + CountVect word 50K (15K subset) | 123,300 | |
| 5C: Blend 5A+5B | — | **CHƯA IMPLEMENT** |

**Phát hiện quan trọng:**
- MSE objective (92.6k) THẮNG MAE objective (95.1k) — với 269K data lớn, MSE ổn định hơn
- TF-IDF char_wb (92.6k) thắng CountVect word (97.3k) — IDF + char ngrams có giá trị
- RF/XGB overloaded với TF-IDF 100K features → chuyển sang CountVect 50K

### 3.3. Thống kê dữ liệu

**Tài liệu:** [dataset_stats.md](fine_tune_qwen/dataset_stats.md) (cho `items_prompts_tv_1`, cấu trúc tương tự `tv_3`)

Train (85,727 items): Price mean=301,687 VND, median=229,000 VND, min=4,900, max=1,000,000
Phân bố danh mục có trong [`dataset_stats.md`](fine_tune_qwen/dataset_stats.md)

---

## 4. Giai Đoạn 3: Deep Learning Models (Day 4)

**Thư mục code:**
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/day4/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day4/) — Day 4 gốc (v1-v8 stacking)
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/) — Day 4 v2 (VN BERT models, 269K)
- [`scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi_2/`](scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi_2/) — Package V2: `senttrans_model.py`, `deep_neural_network_sparse.py`, `bert_finetune_model.py`, `phobert_model.py`, `bert_finetune_phased_model.py`, `evaluator.py`

**Tài liệu tham chiếu:**
- [SESSION_HANDOFF.md](scraping_data_tv/SESSION_HANDOFF.md) — Session 18-25 (Day 4 v2 execution)

### 4.1. Day 4 gốc — Stacking models (v1-v8)

**5 DL models:**
- Model 0: DNN ResidualBlock (HashingVectorizer / TF-IDF)
- Model 1: PhoBERT-base-v2 fine-tune
- Model 2: Vietnamese Embedding (dangvantuan) frozen + MLP
- Model 3: XLM-RoBERTa-base fine-tune
- Model 4: Vietnamese Embedding + LightGBM hybrid

**Tiến trình stacking:**

| Version | Mô tả | RMSLE | MAE | Gap vs 0.40 |
|---------|-------|-------|-----|-------------|
| v6 Blended | PhoBERT + PCA+LGB + v4 + Day3 | 0.4187 | 82,766 | 0.0187 |
| v7 Stacked (7M) | + thêm model | 0.4059 | 81,776 | 0.0059 |
| **v8 Stacked (8M)** | **+ PhoBERT-large** | **0.4004** | **79,853** | **0.0004** |

**Ceiling encoder-only + stacking ≈ 0.40.** Mục tiêu 0.38 chưa đạt.

### 4.2. Day 4 v2 — Vietnamese BERT Models (269K data — items_tv_v9)

#### Các file model

| File | Mô tả |
|------|-------|
| `deep_neural_network_sparse.py` | `ResidualBlock` + `PriceDNN` (8 blocks, hidden=4096), `SparseDataset` (per-row toarray), `SparseDNNRunner` |
| `senttrans_model.py` | `SentTransRunner`: frozen encoder (e5-small/AITeamVN), `encode_and_cache()`, reuse `PriceDNN` |
| `bert_finetune_model.py` | `BERTFinetuneRegressor` (AutoModel + mean_pooling + price_head + aux category_head), `BERTFinetuneRunner` (LLRD + EMA + HuberLoss + AMP + CosineWarmup), `freeze_bottom_layers()`, `build_llrd_param_groups()` |
| `phobert_model.py` | `PhoBERTRunner`: `word_segment()` bằng Underthesea + joblib pkl cache TRƯỚC tokenizer, reuse `BERTFinetuneRunner` |
| `bert_finetune_phased_model.py` | `PhasedBERTRegressor` (price_bin_head 5 bins), `PhasedBERTRunner` (3-phase training: top-4 lr=2e-5 → top-8 lr=1e-5 → top-16 lr=5e-6) |

#### Kỹ thuật áp dụng

| Kỹ thuật | Mô tả | Áp dụng trong |
|----------|------|--------------|
| **LLRD** (Layer-wise Learning Rate Decay) | `heads=base_lr`, layer i = base_lr × decay^(num_layers-i-1), `llrd_decay=0.85-0.90` | NB06, NB09, NB10, NB12, NB13, NB14 |
| **EMA** (Exponential Moving Average) | `AveragedModel` với decay 0.999-0.9999, window 1K-10K steps | Tất cả BERT notebooks |
| **R-Drop** | 2× forward, MSE consistency loss giữa 2 lần dropout, `alpha=0.3` | NB09, NB10 |
| **keep_top_layers** | Freeze bottom layers, chỉ fine-tune top 4/8/16/24 layers | NB06 (top-4), NB09 (top-8), NB10 (top-8), NB12 (top-24), NB13 (top-8) |
| **Phased training** | 3 phase: top-4 → top-8 → top-16, rebuild optimizer+scheduler mỗi phase | NB14 |
| **Price bin auxiliary head** | Multi-task: price regression + price bin classification (5 bins) | NB14 |
| **Gradient accumulation** | `grad_accum=2` (batch=16 → effective 32) | NB12 |
| **HuberLoss** | delta=1.0 — robust với outlier | Tất cả BERT notebooks |
| **CosineWarmup** | `warmup_ratio=0.05-0.10` | Tất cả notebooks |

#### Kết quả từng notebook (chạy trên RTX 3090 Ti, trừ khi ghi chú)

| NB | Mô tả | Test MAE (VND) | R² | Trạng thái |
|----|-------|---------------|-----|-----------|
| NB01 | DNN + TF-IDF char_wb 100K | 77,300 | — | ĐÃ CHẠY |
| NB02 | DNN + HashingVec 5000 | 80,000 | — | ĐÃ CHẠY |
| NB04 | e5-small frozen + DNN | 102,700 | 50.3% | ĐÃ CHẠY |
| NB05 | AITeamVN frozen + DNN | 76,100 | 71.7% | ĐÃ CHẠY |
| **NB06** | **AITeamVN fine-tune top-4, batch=32, lr=2e-5** | **74,200** | **72.8%** | **ĐÃ CHẠY — TỐT NHẤT HIỆN TẠI** |
| NB10 | PhoBERT-base top-8 + R-Drop, batch=48 | 77,600 | 70.8% | ĐÃ CHẠY |
| NB07 | PhoBERT-base gốc | — | — | ĐÃ XÓA (thay bằng NB10) |
| NB08 | PhoBERT-large gốc | — | — | ĐÃ XÓA (thay bằng NB13) |
| NB09 | AITeamVN top-8 + R-Drop, batch=24 | ? | ? | **PENDING — chưa chạy** |
| NB11 | Ridge stacking ensemble (reference) | — | — | ĐÃ TẠO (optional) |
| NB12 | AITeamVN full 24 layers, grad_accum=2 | ? | ? | **SẴN SÀNG — chưa chạy** |
| NB13 | PhoBERT-large top-8, reuse pkl NB10 | ? | ? | **SẴN SÀNG — chưa chạy** |
| **NB14** | **AITeamVN phased 3-phase + price bins, aux_alpha=0.15** | ? | ? | **SẴN SÀNG — kỳ vọng MAE < 65k** |

**Lưu ý kỹ thuật quan trọng:**
- PhoBERT bắt buộc Underthesea word segmentation TRƯỚC tokenizer → Cache `phobert_seg_{train,val,test}.pkl` (reuse từ NB10 cho NB13)
- `BERTFinetuneRunner.train()` dùng AveragedModel (EMA) → inference phải dùng `ema_model`
- Checkpoint keys (NB12/13): `ema_state_dict`, `y_mean`, `y_std`, `model_name`, `keep_top_layers`, `cat_classes`
- Checkpoint keys (NB14): thêm `price_bin_boundaries`
- `num_workers=0` bắt buộc trên Linux/WSL2

#### So sánh embedding models

| Model | Params | Dim | VN-MTEB Score | Classification | Ghi chú |
|-------|--------|-----|---------------|---------------|---------|
| `intfloat/multilingual-e5-small` | 118M | 384 | 60.66 | — | 512 tokens, thay MiniLM (128-token limit) |
| `dangvantuan/vietnamese-embedding` | 135M | 768 | STS 88.33 | — | Cần PyVi tokenize → ĐÃ BỎ |
| `AITeamVN/Vietnamese_Embedding` | 568M | 1024 | **63.34** | **69.06** | Tốt nhất, BGE-M3 base, dot product similarity |

---

## 5. Giai Đoạn 4: QLoRA Fine-tune Qwen3.5-4B (Day 5)

**Thư mục code:**
- [`fine_tune_qwen/`](fine_tune_qwen/) — Day 5 notebooks, utils, results, weights
- [`fine_tune_qwen/utils/`](fine_tune_qwen/utils/) — `prompt_builder.py`, `evaluator.py`, `inference.py`, `hf_upload.py`, `rmsle_callback.py`

**Tài liệu tham chiếu:**
- [plan_day5.md](fine_tune_qwen/plan_day5.md) — Kế hoạch chi tiết Day 5 (Phase 0-5)
- [phase2_execution_log.md](fine_tune_qwen/phase2_execution_log.md) — Execution log Run #1-#5
- [data_augmentation.md](fine_tune_qwen/data_augmentation.md) — Data augmentation pipeline
- [dataset_stats.md](fine_tune_qwen/dataset_stats.md) — Thống kê dataset

### 5.1. Kiến trúc và Cấu hình

**Model:** `Qwen/Qwen3.5-4B-Base` (Apache 2.0)
**Framework:** PEFT + bitsandbytes + TRL 0.24 (KHÔNG Unsloth — lỗi VLProcessor với Hybrid architecture)
**Quantization:** QLoRA 4-bit NF4 + double quant, `torch_dtype=torch.bfloat16` BẮT BUỘC

**Đặc điểm Qwen3.5 tokenizer:** Tokenize từng chữ số riêng (digit-by-digit). `max_new_tokens=4` đủ cho completion range [5, 1000].

**Cấu hình cơ bản (từ English Llama recipe):**

| Hyperparam | Giá trị |
|-----------|---------|
| LoRA r / alpha / dropout | 64 / 128 / 0.1 |
| Target modules | 7: q,k,v,o,gate,up,down |
| LR / scheduler | 2e-4 / cosine |
| warmup_ratio | 0.03 |
| weight_decay | 0.001 |
| max_grad_norm | 0.3 |
| Optim | paged_adamw_32bit |
| Epochs / eff_batch | 3 / 64 |
| max_seq_length | 192 (p99=168, trunc ~0.1%) |

### 5.2. Các version đã chạy

#### v0 — Zero-shot Baseline
- Notebook: `02_baseline_v1.ipynb`
- RMSLE = **4.4428** | MAE = 296,807 VND | MAPE = 105.9% | R² = -2.09
- Model không biết gì về giá cả sản phẩm — dự đoán lung tung

#### v1 — Smoke Test (20K data)
- Notebook: `03_train_v1_smoke.ipynb`
- Cấu hình: r=32, 4 modules (q,k,v,o), 20K data, 2 epochs
- **RMSLE = 0.6084** (epoch 2) | MAE = 116,769 VND | R² = 0.398
- Train time: 162 phút | VRAM peak: 12.81 GB
- Validate pipeline + phát hiện bug `torch_dtype=bfloat16`, manual `DataCollatorForCompletionOnlyLM`

#### v3 — Full Train (85K data) — QWEN TỐT NHẤT
- Notebook: `04_train_v3.ipynb`
- Cấu hình: **r=64, alpha=128, 7 modules, 85,727 data, 3 epochs, gradient_checkpointing=True**
- Train time: **773 phút (~12.9h)** | VRAM peak: **13.46 GB** trên RTX 3090 Ti
- **RMSLE = 0.4426** | **MAE = 80,100 VND** | MAPE = 37.6% | R² = 0.664
- HF: `SeanSunny/qwen3.5-4b-vn-pricer-v3` (private)

| Epoch | RMSLE | MAE (VND) | MAPE |
|-------|-------|-----------|------|
| 1 | 0.5424 | 94,854 | 41.0% |
| 2 | 0.4618 | 82,440 | 38.9% |
| **3** | **0.4426** | **80,100** | **37.6%** |

**Insights quan trọng từ v3:**
1. **CE ↔ RMSLE divergence:** Eval CE loss đáy ở step 2600 nhưng generative RMSLE vẫn cải thiện đến epoch 3 → Best checkpoint PHẢI chọn theo generative metric, KHÔNG theo CE loss
2. **Diminishing returns:** e1→e2 = -15%, e2→e3 = -4.2%
3. **Failure modes:**
   - Bỏ qua số định lượng trong title ("0.6ml" → predict 600K vs true 60K, 900% error)
   - Anchor theo category mean (túi xách 55K → predict 129K)
   - Under-predict outlier > 500K (< 5% mẫu train có giá > 500K)
4. **MAE v3 (80,100 VND) chỉ cao hơn Day4 v8 (79,853 VND) 0.3%** — gap RMSLE chủ yếu do outlier

#### v4-scratch-v2 — THẤT BẠI (Mode Collapse)
- Notebook: `06_train_v4_scratch_v2.ipynb`
- Cấu hình: **r=128, alpha=256, DoRA + RSLoRA + NEFTune=5, 269K data**
- **RSLoRA scale = 22.6×** (alpha/sqrt(r)) → gradient spike step 200 → model collapse về "199"
- RMSLE = **0.9739**, R² = **-0.28** (tệ hơn cả mean predictor)
- 17/20 val samples predict chính xác "199"

**Root cause:** RSLoRA scale = `alpha / sqrt(r)` = 256 / sqrt(128) = 22.6× (thay vì 2.0× standard). Với 170M trainable params (DoRA r=128) × 22.6× gradient → spike thảm họa.

#### v4-scratch-v4 — Đã sửa (269K data)
- Notebook: `06_train_v4_scratch_v4.ipynb`
- Cấu hình: **r=64/alpha=128, KHÔNG DoRA, KHÔNG RSLoRA, NEFTune=5, wd=0.001, batch=24**
- Train time: **~6h** (early stop patience=3 tại step 6000/8412)
- VRAM peak: 23.62 GB trên RTX 5090
- **RMSLE = 0.4608** | **MAE = 79,589 VND** | MAPE = 32.78% | R² = 62.93%

**RMSLE timeline:**

| Step | RMSLE | Ghi chú |
|------|-------|------|
| 500 | 0.6843 | |
| 1500 | 0.5832 | |
| 2500 | 0.5137 | |
| 3500 | 0.4522 | |
| **4500** | **0.4304** | **BEST CKPT (subset 500)** |
| 6000 | 0.4586 | STOP |

**Nhận xét:** v4 (269K data) KHÔNG thắng được v3 (85K data) về RMSLE (0.4608 vs 0.4426) mặc dù dataset gấp 3.15×. MAE gần bằng Day4 v8 (79,589 vs 79,853). RMSLE full val (0.4608) chênh đáng kể so với subset 500 (0.4304) — val subset không đại diện tốt.

### 5.3. Bài học tổng hợp

| Bài học | Hành động |
|--------|--------|
| `torch_dtype=torch.bfloat16` BẮT BUỘC trong `from_pretrained` | Áp dụng mọi notebook |
| `DataCollatorForCompletionOnlyLM` đã bị xóa khỏi TRL 0.24 | Dùng manual impl |
| CE loss ≠ generative RMSLE/MAE | Chọn best ckpt theo eval generative metric, KHÔNG theo CE |
| `val_eval_size=200` quá nhiễu | Tăng lên 500+ cho callback |
| `group_by_length` đã bị drop khỏi SFTConfig TRL 0.24 | KHÔNG truyền arg này |
| `use_cache=False` cho grad checkpointing, toggle `True` trong callback generate | Inference nhanh gấp 5× |
| Push `best_checkpoint`, KHÔNG push `trainer.model` cuối cùng | Model cuối có thể đã overfit |
| RSLoRA với r=128 gây mode collapse | Dùng standard LoRA scaling (alpha/r) |
| Data augmentation không phải lúc nào cũng tốt | Chất lượng aug data > số lượng |

### 5.4. Bảng xếp hạng Qwen V1

| Version | Data | Epoch | r/mod | RMSLE | MAE (VND) | R² |
|---------|------|-------|-------|-------|-----------|-----|
| Day4 v8 (baseline) | full | — | — | **0.4004** | 79,853 | — |
| v3 Qwen | 85K | 3 | 64/7 | 0.4426 | 80,100 | 0.664 |
| v4-scratch-v4 | 269K | 1.1* | 64/7 | 0.4608 | 79,589 | 0.629 |
| v1 smoke | 20K | 2 | 32/4 | 0.6084 | 116,769 | 0.398 |
| v0 zero-shot | — | 0 | — | 4.4428 | 296,807 | -2.09 |
| v4-scratch-v2 | 269K | FAIL | — | 0.9739 | 175,989 | -0.28 |

*\*early stop patience=3*

### 5.5. Các notebook chưa chạy (Day 5)

| Notebook | Mục đích | Trạng thái |
|----------|----------|-----------|
| `05_train_v4_resume.ipynb` | Resume từ v3 epoch 2, LR=5e-5, NEFTune=3 | ĐÃ BỎ QUA — ensemble 3-model |
| `07_ensemble.ipynb` | Ridge log-space blend v3+v4-scratch+v8 | **CHƯA CHẠY** |
| `09_eval_full.ipynb` | Final eval tất cả version trên test 3,872 | **CHƯA TẠO** |
| `day5_summary.md` | Tổng kết Day 5 | **CHƯA TẠO** |

---

## 6. Qwen V2 — Tối Ưu MAE (Viết Lại Toàn Bộ)

**Thư mục:** [`fine_tune_qwen_v2/`](fine_tune_qwen_v2/)

**Tài liệu tham chiếu:**
- [plan_v2.md](fine_tune_qwen_v2/plan_v2.md) — Kế hoạch triển khai đầy đủ (1160 dòng)
- [SESSION_FINE_TUNE_QWEN_V2.md](fine_tune_qwen_v2/SESSION_FINE_TUNE_QWEN_V2.md) — Session handoff

**Trạng thái: CODE HOÀN TẤT — đã commit + push, CHƯA TRAIN**
**Branch:** `feature/day5-qlora-qwen`

### 6.1. Khác biệt so với Qwen V1

| Khía cạnh | V1 | V2 |
|-----------|-----|-----|
| **Metric chính** | RMSLE | **MAE** (bám English recipe) |
| **Dataset** | items_prompts_tv_3 (85K) + tv_4 (269K) | `items_prompts_tv_4` (269K) |
| **max_new_tokens** | 4 | **8** (safety margin) |
| **Batch trên 5090** | 16 × 4 (eff=64) | **32 × 2 (eff=64)** — giảm accum, tăng batch |
| **group_by_length** | V1 cố gắng dùng | **KHÔNG truyền** (đã bị TRL 0.24 drop) |
| **Best checkpoint** | Theo eval CE + generative RMSLE | **`MaeEvalCallback`** — generate MAE mỗi 500 steps trên 500 val |
| **Codebase** | Notebooks riêng lẻ, copy-paste | Utils shared (`items_vn.py`, `evaluator_vn.py`, `training_utils.py`) |
| **Push Hub** | Push `trainer.model` cuối cùng | **Push `best_mae_checkpoint`** (không push model cuối) |
| **Hardware target** | 3090 Ti 24GB + 5090 32GB | **5090 32GB** (batch 32) |

### 6.2. Bản chất bài toán (nhận thức lại)

Mặc dù output là số nguyên (5-1000 K VND), với LLM đây là bài toán **phân loại token / next-token prediction**, không phải hồi quy. Model học để dự đoán xác suất của token kế tiếp sau chuỗi `"Giá là: "`.

**Hệ quả thiết kế quan trọng:**
- CE loss ≠ MAE thực → Best ckpt theo `MaeEvalCallback`, KHÔNG theo eval_loss
- Chỉ completion tokens vào loss → `DataCollatorCompletionOnly` mask prompt = -100
- Greedy generation cần `use_cache=True` → toggle trong callback
- Không có "target distribution" → KHÔNG log-scale / standardize target như DNN regression

### 6.3. Cấu trúc thư mục

```
fine_tune_qwen_v2/
├── plan_v2.md                       ✅ Kế hoạch đầy đủ (1160 dòng)
├── SESSION_FINE_TUNE_QWEN_V2.md     ✅ Session handoff
├── utils/
│   ├── __init__.py                  ✅
│   ├── items_vn.py                  ✅ Item dataclass + load_items()
│   ├── evaluator_vn.py              ✅ VnTester (MAE/RMSLE/R²/MSE + charts)
│   └── training_utils.py            ✅ BnB/LoRA/SFTConfig + DataCollatorCompletionOnly + MaeEvalCallback
├── 00_explore.ipynb                 ✅ Exploration trên Colab T4 16GB (19 code cells)
├── 01_zero_shot.ipynb               ✅ Baseline MAE 200 test items
├── 02_pilot_20k.ipynb               ✅ Pilot 20K, verify VRAM/settings
├── 03_train_v2.ipynb                ✅ Full 269K, 3 epochs, batch 32×2
├── 04_eval_v2.ipynb                 ✅ Final eval + charts
└── results/
    ├── zero_shot_results.json       (sau khi chạy 01)
    ├── pilot_20k_results.json       (sau khi chạy 02)
    └── v2_results.json              (sau khi chạy 04)
```

### 6.4. Cấu hình V2

| Hyperparam | Giá trị | Ghi chú |
|-----------|---------|---------|
| LoRA r / alpha / dropout | 64 / 128 / 0.1 | English recipe |
| Target modules | 7: q,k,v,o,gate,up,down | English recipe |
| LR / scheduler | 2e-4 / cosine | English recipe |
| warmup_ratio | 0.03 | |
| weight_decay / max_grad_norm | 0.001 / 0.3 | |
| Epochs | 3 | |
| eff_batch_size | **64 (32×2)** | 5090 32GB |
| MAX_SEQ_LENGTH | 192 | Reuse v1 profiling |
| MAX_NEW_TOKENS | 8 | Safety margin |
| VAL_EVAL_SIZE | 500 | Bài học từ v1 (200 quá nhiễu) |
| EVAL_MAE_STEPS | 500 | |
| Best ckpt metric | **eval generative MAE** | `MaeEvalCallback` |

### 6.5. Mục tiêu

| Target | MAE |
|--------|-----|
| Thắng zero-shot baseline | Bắt buộc |
| **MAE < 80,000 VND (thắng v1)** | **P0** |
| MAE < 70,000 VND | P1 |
| MAE < 60,000 VND | Stretch |

### 6.6. Thứ tự thực hiện (chưa thực hiện)

```
00_explore.ipynb       → Colab T4 16GB (~5-10 phút) — quan sát dataset, tokenizer, kiến trúc
01_zero_shot.ipynb     → 5090 (~10 phút) — baseline MAE
02_pilot_20k.ipynb     → 5090 (~35-45 phút) — verify VRAM/settings
03_train_v2.ipynb      → 5090 (~7-10h) — full training, push best ckpt
04_eval_v2.ipynb       → sau training — final charts + results JSON
```

---

## 7. Bảng Xếp Hạng Tổng Hợp (các mô hình tốt nhất)

**Cập nhật: 2026-07-12**

| Hạng | Mô hình | MAE (VND) | RMSLE | R² | Trạng thái |
|------|-------|-----------|-------|-----|-----------|
| **1** | **Day4 v2 NB06 — AITeamVN BERT fine-tune top-4** | **74,200** | — | **72.8%** | **ĐÃ CHẠY — TỐT NHẤT HIỆN TẠI** |
| 2 | Day4 v2 NB05 — AITeamVN frozen + DNN | 76,100 | — | 71.7% | ĐÃ CHẠY |
| 3 | Day4 v2 NB01 — DNN TF-IDF char_wb 100K | 77,300 | — | — | ĐÃ CHẠY |
| 4 | Day4 v2 NB10 — PhoBERT-base top-8 + R-Drop | 77,600 | — | 70.8% | ĐÃ CHẠY |
| 5 | Day5 v4-scratch-v4 — Qwen 269K | 79,589 | 0.4608 | 62.9% | ĐÃ CHẠY |
| 6 | Day4 v8 — Stacked 8 models | 79,853 | **0.4004** | — | ĐÃ CHẠY (SOTA RMSLE) |
| 7 | Day5 v3 — Qwen 85K | 80,100 | 0.4426 | 66.4% | ĐÃ CHẠY |
| 8 | Day3 v2 — LGB char_wb 269K | 92,600 | — | — | ĐÃ CHẠY |
| 9 | Day5 v1 — Qwen smoke 20K | 116,769 | 0.6084 | 39.8% | ĐÃ CHẠY |
| 10 | Day5 v0 — Qwen zero-shot | 296,807 | 4.4428 | -209% | ĐÃ CHẠY |

**Nhận xét:**
- AITeamVN BERT (NB06, MAE=74.2k) là SOTA hiện tại, vượt cả Qwen 4B (80k)
- RMSLE tốt nhất vẫn là Day4 v8 (stacking 8 models)
- BERT fine-tune với 269K mẫu vẫn rất cạnh tranh so với decoder LLM
- NB14 (AITeamVN phased + price bins) chưa chạy — kỳ vọng MAE < 65k
- Qwen V2 chưa train — kỳ vọng MAE < 70k

---

## 8. Những Việc Chưa Hoàn Thành (Checklist Ưu Tiên)

| Ưu tiên | Việc cần làm | Tác động | Thư mục/File liên quan |
|---------|--------------|----------|----------------------|
| **CAO** | Chạy NB14 — AITeamVN phased + price bins | Kỳ vọng MAE < 65k, có thể thành SOTA mới | [`day4_v2/day4_v2_14_aitvn_phased.ipynb`](scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/) |
| **CAO** | Train Qwen V2 (`03_train_v2.ipynb`) | Cần RTX 5090, ~7-10h, kỳ vọng MAE < 70k | [`fine_tune_qwen_v2/`](fine_tune_qwen_v2/) |
| **CAO** | Chạy NB09 (AITeamVN top-8 + R-Drop) | Có thể cải thiện NB06 | [`day4_v2/day4_v2_09_aitvn_improved.ipynb`](scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/) |
| CAO | Chạy NB12 (AITeamVN full 24 layers) | Full encoder, nhiều tham số hơn | [`day4_v2/day4_v2_12_aitvn_full.ipynb`](scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/) |
| CAO | Chạy NB13 (PhoBERT-large top-8) | Model lớn hơn, đa dạng embedding hơn | [`day4_v2/day4_v2_13_phobert_large.ipynb`](scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/) |
| TRUNG BÌNH | Chạy Day5 `07_ensemble.ipynb` | Blend v3+v4+v8 — có thể giảm RMSLE | [`fine_tune_qwen/07_ensemble.ipynb`](fine_tune_qwen/07_ensemble.ipynb) |
| TRUNG BÌNH | Tạo Day5 `09_eval_full.ipynb` + `day5_summary.md` | Tổng kết Day 5 | [`fine_tune_qwen/`](fine_tune_qwen/) |
| THẤP | Đóng Day3 v2 (save `day3_v2_results.json` + `day3_v2_summary.md`) | Hoàn thiện pipeline docs | [`day3_v2/`](scraping_data_tv/Data_processing_for_Vietnamese_data/day3_v2/) |
| THẤP | Tạo Ridge ensemble NB11 cho Day4 v2 | Free lunch nếu models có uncorrelated errors | [`day4_v2/day4_v2_11_ensemble.ipynb`](scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/) |
| THẤP | Day5 `05_train_v4_resume.ipynb` | Resume từ v3 → đã BỎ QUA (quyết định session 11) | [`fine_tune_qwen/05_train_v4_resume.ipynb`](fine_tune_qwen/05_train_v4_resume.ipynb) |

---

## 9. Cấu Trúc Thư Mục Liên Quan

```
tech2ai/
├── segment4/                                      # Runtime chính (tiếng Anh/US market) — HOÀN TẤT
│   ├── search_key.py                              # App chính: keyword search BestBuy + Amazon
│   ├── multi_source_framework.py                  # Framework search_key
│   ├── price_agents/                              # Agent layer
│   ├── bestbuy_untils/                            # Utilities
│   └── mo_ta_du_an/                               # Tài liệu dự án
│       ├── DOCUMENTATION_SEARCHKEY.md
│       ├── DOCUMENTATION_PRICE_IS_RIGHT.md
│       ├── Project_Development_Plan.md
│       └── ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md
│
├── scraping_data_tv/                              # Dữ liệu tiếng Việt — pipeline
│   ├── Tiki/                                      # Tiki scraper
│   ├── e-commerce-sites-scraping/                 # Scraper có sẵn (Hasaki, WinMart...)
│   ├── Data_processing_for_Vietnamese_data/
│   │   ├── plan_data_preprocessing_vi.md          # Kế hoạch Day 0-4
│   │   ├── day1/                                  # Day 1: data curation
│   │   ├── day2/                                  # Day 2: LLM preprocessing
│   │   ├── day3/ + day3_v2/                       # Day 3: baseline ML
│   │   ├── day4/ + day4_v2/                       # Day 4: deep learning BERT
│   │   ├── pricer_vi/                             # Package V1
│   │   └── pricer_vi_2/                           # Package V2 (BERT, DNN sparse, PhoBERT)
│   └── SESSION_HANDOFF.md                         # Session logs
│
├── fine_tune_qwen/                                # Day 5: QLoRA Qwen (RMSLE)
│   ├── plan_day5.md                               # Kế hoạch Day 5
│   ├── phase2_execution_log.md                    # Run logs
│   ├── data_augmentation.md                       # Pipeline từ scraping → augmentation
│   ├── dataset_stats.md                           # Thống kê dataset
│   ├── utils/                                     # prompt_builder, evaluator, inference, rmsle_callback
│   ├── results/                                   # v0/v1/v3/v4 results JSON
│   ├── weights/                                   # Adapter weights (v1, v3, v4)
│   └── *.ipynb                                    # Training notebooks
│
├── fine_tune_qwen_v2/                             # Qwen V2: MAE-optimized (CHƯA TRAIN)
│   ├── plan_v2.md                                 # Kế hoạch triển khai
│   ├── SESSION_FINE_TUNE_QWEN_V2.md               # Session handoff
│   ├── utils/                                     # items_vn, evaluator_vn, training_utils
│   └── 0*.ipynb                                   # 5 notebooks (explore → eval)
│
├── VIETNAMESE_PRICING_DEVELOPMENT_REPORT.md       # FILE NÀY
├── README.md
├── pyproject.toml
└── uv.lock
```

---

## 10. Tham Chiếu Nhanh

### Tài liệu thiết kế & kế hoạch

| File | Nội dung |
|------|---------|
| [README.md](README.md) | Tổng quan repo, cách chạy, roadmap |
| [Project_Development_Plan.md](segment4/mo_ta_du_an/Project_Development_Plan.md) | Kế hoạch 8 tháng DATN |
| [DOCUMENTATION_SEARCHKEY.md](segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md) | Tài liệu app chính search_key.py |
| [DOCUMENTATION_PRICE_IS_RIGHT.md](segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md) | Tài liệu app legacy price_is_right.py |
| [ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md](segment4/mo_ta_du_an/ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md) | Tài liệu chuyển giao kiến trúc Alex cho DATN |
| [PROMPT_NEW_SESSION_APPLY_ALEX_TRANSFER_TO_DATN.md](segment4/mo_ta_du_an/PROMPT_NEW_SESSION_APPLY_ALEX_TRANSFER_TO_DATN.md) | Prompt áp dụng kiến trúc Alex |

### Dữ liệu tiếng Việt

| File | Nội dung |
|------|---------|
| [plan_data_preprocessing_vi.md](scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md) | Kế hoạch Day 0-4 dữ liệu tiếng Việt |
| [SESSION_HANDOFF.md](scraping_data_tv/SESSION_HANDOFF.md) | Session logs Day 3/4/5 (session 13-25) |
| [data_augmentation.md](fine_tune_qwen/data_augmentation.md) | Pipeline từ scraping đến data augmentation |
| [dataset_stats.md](fine_tune_qwen/dataset_stats.md) | Thống kê dataset items_prompts_tv_1 |

### Fine-tune Qwen

| File | Nội dung |
|------|---------|
| [plan_day5.md](fine_tune_qwen/plan_day5.md) | Kế hoạch QLoRA Qwen3.5-4B (Phase 0-5) |
| [phase2_execution_log.md](fine_tune_qwen/phase2_execution_log.md) | Execution log Run #1-#5 |
| [plan_v2.md](fine_tune_qwen_v2/plan_v2.md) | Kế hoạch Qwen V2 MAE-optimized |
| [SESSION_FINE_TUNE_QWEN_V2.md](fine_tune_qwen_v2/SESSION_FINE_TUNE_QWEN_V2.md) | Qwen V2 session handoff |

### Dataset trên HuggingFace Hub

| Dataset | URL |
|---------|-----|
| items_raw_tv_v6 | `https://huggingface.co/datasets/SeanSunny/items_raw_tv_v6` |
| items_tv_v6 | `https://huggingface.co/datasets/SeanSunny/items_tv_v6` |
| items_prompts_tv_3 | `https://huggingface.co/datasets/SeanSunny/items_prompts_tv_3` |
| items_prompts_tv_4 | `https://huggingface.co/datasets/SeanSunny/items_prompts_tv_4` |
| items_tv_v9 | `https://huggingface.co/datasets/SeanSunny/items_tv_v9` |
| qwen3.5-4b-vn-pricer-v3 | `https://huggingface.co/SeanSunny/qwen3.5-4b-vn-pricer-v3` (private) |

---

*Báo cáo được tạo ngày 2026-07-12 sau 3 tháng gián đoạn. Cập nhật lần cuối của các file nguồn: 2026-05-19.*

*Tổng số dòng: ~740 dòng | Tổng số file .md tham chiếu: 12 | Tổng số thư mục code tham chiếu: 15+*
