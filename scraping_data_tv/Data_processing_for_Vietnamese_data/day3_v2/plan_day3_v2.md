# Plan Day 3 v2 — Traditional ML Baseline: Vietnamese Price Prediction

**Ngày tạo:** 2026-05-16  
**Cập nhật:** 2026-05-16 — đổi primary metric sang MAE, bỏ log1p, bám sát English pipeline  
**Branch:** feature/day5-qlora-qwen  
**Folder:** `Data_processing_for_Vietnamese_data/day3_v2/`  
**Support module:** `Data_processing_for_Vietnamese_data/pricer_vi_2/`

---

## 0. Tổng quan

### 0.1. Tại sao xây dựng lại từ đầu?

| Vấn đề cũ (Day 3 v1) | Giải pháp mới (Day 3 v2) |
|---|---|
| Dataset `items_tv_v6` (85,727 train) — nhỏ, không augmented | `items_tv_v9` (269,112 train) — 3.15× lớn hơn, đã augment |
| `price` dùng VND thực (55,000 — 1,000,000) — scale quá lớn | `price = round(price_vnd / 1000)` → range 5–1000, align với English pipeline |
| Primary metric RMSLE — không cần thiết khi range 5–1000 | **Primary metric MAE** — align English, đơn giản hơn, trực quan hơn |
| log1p transform bắt buộc | **Không dùng log1p** — train trực tiếp trên raw price (same as English) |
| evaluator.py hard-coded VND scale | evaluator.py mới: match English structure, MAE/MSE/R², hiển thị "k VND" |

### 0.2. Mục tiêu định lượng

| Mô hình | MAE target (k VND) | Ghi chú |
|---|---|---|
| Baseline (mean predictor) | ~200k | Upper bound |
| Linear Regression + NLP | ~100–130k | |
| XGBoost | ~80–110k | |
| **LightGBM Tuned (target Day 3 v2)** | **< 90k** | Sau khi chạy Section 0-4 sẽ confirm |
| **Best Model (stretch goal)** | **< 80k** | Xem sau khi có kết quả Section 0-4 |
| Day 3 v1 tham chiếu | ~110k VND | |

> **Lưu ý:** Target MAE cụ thể sẽ được confirm sau khi xem kết quả Section 0-4. Day 3 v1 không có MAE chuẩn vì đo trên VND thực (khác scale).

---

## 1. Dữ liệu đầu vào

### 1.1. Dataset: `SeanSunny/items_tv_v9`

| Split | Rows | Ghi chú |
|---|---|---|
| train | **269,112** | 85,727 gốc + 183,385 augmented (LLM paraphrase × 1–5x/bucket) |
| validation | 3,926 | Filter price <= 1M VND từ items_tv_v7 |
| test | 3,872 | Filter price <= 1M VND từ items_tv_v7 |

**Schema:**

| Column | Type | Mô tả |
|---|---|---|
| `title` | str | Tên sản phẩm |
| `category` | str | 1 trong 8 danh mục |
| `brand` | str | Thương hiệu |
| `summary` | str | 5-dòng LLM format (gốc hoặc augmented) |
| `price` | int | `round(price_vnd / 1000)` — **label** — range 5–1000 |
| `price_vnd_true` | int | Giá VND gốc — chỉ dùng để verify, không dùng làm label |

### 1.2. Format `summary` (5 dòng cố định)

```
Tieu de: Ao thun nam cotton thoang mat
Danh muc: Thoi Trang
Thuong hieu: UniStyle
Mo ta: Ao cotton 100%, thoang mat, thich hop mac thuong ngay.
Thong so: Chat lieu Cotton 100%, size S-XXL, nhieu mau sac.
```

### 1.3. Phân phối giá (items_tv_v9 train — thực tế đo được)

| Metric | Giá trị |
|---|---|
| Range | 5 – 1000 k VND |
| Mean | 330.5 k VND |
| Median | 215.0 k VND |
| Std | 268.8 k VND |

---

## 2. Module: `pricer_vi_2/`

### 2.1. `pricer_vi_2/items.py`

Kế thừa từ English `pricer/items.py`:
- Thêm field `brand`
- Bỏ `weight`, `full`, `prompt` (không có trong data tiếng Việt)
- Thêm `price_vnd_true` (Optional, chỉ để verify)
- `price` = float (round/1000), range 5–1000
- Method `from_hub("SeanSunny/items_tv_v9")` load 3 splits

### 2.2. `pricer_vi_2/evaluator.py`

**Match English `pricer/evaluator.py` — cùng cấu trúc, chỉ thay đơn vị:**

| Điểm thay đổi | English | Vietnamese v2 |
|---|---|---|
| Price unit | $1–999 | 5–1000 k VND |
| Error display | `$43.9` | `43.9k VND` |
| Hover text | `"Guess=$g Actual=$y"` | `"Du doan: g k VND Thuc te: y k VND"` |
| Chart labels | `"Actual Price"` | `"Gia thuc te (k VND)"` |
| Metrics | MAE, MSE, R² | MAE, MSE, R² ✓ |
| log1p | Không | Không ✓ |
| RMSLE, MAPE | Không | Không ✓ |

**Evaluate output format:** `Error: 43.9k VND  MSE: xxx  R²: 64.1%`  
**Training values:** raw numbers (45, không phải 45k) — same as English

### 2.3. Không cần file mới nào khác trong `pricer_vi_2/`

Day 3 chỉ cần `items.py` + `evaluator.py`.

---

## 3. Text Tokenization — Benchmark 3 Vectorizer

### 3.1. Vấn đề với Underthesea

| Vấn đề | Chi tiết |
|---|---|
| Tốc độ | 50K docs → ~20-30 phút (single-thread) |
| Thread-safety | KHÔNG thread-safe |
| Không chính xác với e-commerce | "ip14", "128GB", "4K" bị mis-segment |

### 3.2. Char N-gram TF-IDF — Vectorizer chính

```python
TfidfVectorizer(
    analyzer='char_wb',
    ngram_range=(2, 4),
    max_features=100_000,
    sublinear_tf=True,
)
```

Hoạt động tốt với tiếng Việt không cần word segmentation — bắt được pattern dù có dấu, không dấu, viết tắt.

### 3.3. Benchmark strategy (Section 3)

Chạy 3 vectorizer với LGB default trên **50K subset**, chọn cái có **MAE thấp nhất** trên test (200 samples):

| # | Vectorizer | Ghi chú |
|---|---|---|
| A | `CountVectorizer(max_features=2000)` | Baseline nhanh nhất |
| B | `TfidfVectorizer(char_wb, ngram=(2,4))` | **Khuyến nghị chính** |
| C | `Underthesea + TfidfVectorizer(word)` | Chạy bắt buộc để có benchmark đủ 3 |

---

## 4. Kết quả thực tế Section 0-5 (2026-05-16/17)

### Section 0-4

| Model | MAE (k VND) | R² | Ghi chú |
|---|---|---|---|
| 2a. LR Simple (text_length) | ~225k | -0.002 | Worse than mean — vô dụng |
| 2b. LR + BoW (2K) | 131.7k | 44.3% | Baseline NLP |
| **2c. Ridge + TF-IDF char_wb** | **112.1k** | **59.2%** | Best linear model |
| 3A. BoW + LGB (50K) | 120.8k | 50.8% | |
| 3B. char_wb + LGB (50K, n=1000) | 108.8k | 59.6% | Best Section 0-4 |
| 3C. Underthesea + LGB (50K) | 118.0k | 50.8% | Tokenize 30 phút, thua char_wb |
| 4a. RandomForest (15K, TF-IDF 100K) | 129.7k | 42.3% | Underfit |
| 4b. XGBoost (269K, TF-IDF 100K) | 125.2k | 43.5% | High-dim → XGB bão hòa |

### Section 5 — Kết quả thực tế (2026-05-17)

> MAE ước tính từ 200 giá trị lỗi trong output. Xem notebook `day3_v2_section5.ipynb`.

| Model | MAE (k VND) | Ghi chú |
|---|---|---|
| **5A. LGB + char_wb TF-IDF 100K (MSE, 269K)** | **92.6k** | **BEST — cải thiện 15% vs 3B** |
| 5B. LGB + char_wb TF-IDF 100K (MAE obj, 269K) | 95.1k | MAE obj thua MSE obj — bất ngờ |
| 5F. LGB + CountVect word 50K (MSE, 269K) | 97.3k | TF-IDF char_wb tốt hơn CountVect ~5k |
| 5G. LGB + CountVect word 50K (MAE obj, 269K) | 100.0k | |
| 5E. XGBoost + CountVect word 50K (269K) | 113.2k | Cải thiện vs 4b (125k) — hypothesis confirmed |
| 5D. RF + CountVect word 50K (15K subset) | 123.3k | Cải thiện vs 4a (130k) — hypothesis confirmed |
| 5C. Blend 5A+5B | — | **CHƯA implement** |

**Nhận xét Section 5:**
1. **5A là BEST** (92.6k): Scale LGB từ 50K → 269K cải thiện đáng kể (-15%)
2. **MSE obj tốt hơn MAE obj** (5A 92.6k vs 5B 95.1k): Với 269K data lớn, MSE ổn định hơn
3. **char_wb TF-IDF tốt hơn CountVect word** (5A 92.6k vs 5F 97.3k): IDF weighting + char-level features mang lại ~5k MAE
4. **Hypothesis confirmed**: XGB/RF với low-dim (50K CountVect) đều cải thiện so với high-dim (100K TF-IDF)
5. **Stretch goal <90k CHƯA đạt** (best = 92.6k). 5C (blend) chưa implement có thể giúp thêm ~1-3k

**Nhận xét quan trọng (Section 0-4):**
- XGBoost full 269K (125k) THUA Ridge+TF-IDF (112k) — LGB phù hợp hơn với sparse TF-IDF
- LGB trên 50K subset đã đạt 108.8k — **train trên full 269K sẽ là Section 5 ưu tiên cao nhất**
- char_wb vượt Underthesea (tốn 30 phút tokenize) → giữ char_wb làm vectorizer chính

---

## 4b. Approach: Section 5+ (đã thực hiện + còn lại)

### Đã thực hiện (Section 5, session 17)

| Approach | Kết quả | Nhận xét |
|---|---|---|
| P0: LGB full 269K (MSE) → 5A | **92.6k** ✓ | Đạt kỳ vọng, BEST model |
| P1: LGB MAE obj → 5B | 95.1k ✓ | Thua MSE obj — không khuyến nghị |
| P1 variant: CountVect → 5F/5G | 97-100k ✓ | Thua char_wb TF-IDF |
| Hypothesis test RF/XGB → 5D/5E | 113-123k ✓ | Hypothesis confirmed |

### Còn lại nếu cần đạt <90k

**P2 — Blend 5A + một model khác (5C):**
5A=92.6k, 5B=95.1k — blend có thể giảm thêm 1-3k nếu uncorrelated errors.

**P3 — Add category OHE features:**
Category mean pricer cho thấy signal mạnh. Nối one-hot category vào TF-IDF có thể giảm thêm 2-5k.

> Nếu 92.6k đủ để tổng kết Day 3 v2, không cần implement thêm.

---

### Section 5+ — MAE Optimization (TODO — nghiên cứu sau khi có kết quả Section 0-4)

Sau khi xem kết quả Section 0-4, sẽ áp dụng các kỹ thuật tối ưu MAE trực tiếp:

#### Hướng B1 — MAE loss trực tiếp trong model

```python
# LightGBM với MAE objective
LGBMRegressor(objective='regression_l1', ...)

# XGBoost với MAE objective  
XGBRegressor(objective='reg:absoluteerror', ...)
```

**Ưu điểm:** Model tối ưu trực tiếp cho MAE thay vì MSE → MAE thấp hơn.  
**Trade-off:** Training chậm hơn, có thể không stable với data noisy.

#### Hướng B2 — Quantile Regression tại q=0.5 (= MAE minimizer)

```python
from sklearn.linear_model import QuantileRegressor
qr = QuantileRegressor(quantile=0.5, alpha=0.01)
```

Tối ưu MAE về mặt toán học (median regression).

#### Hướng B3 — Huber Regression (compromise MAE/MSE)

```python
from sklearn.linear_model import HuberRegressor
hr = HuberRegressor(epsilon=1.35)
```

Robust với outlier hơn MSE, MAE tốt hơn pure MSE khi có outliers.

#### Hướng B4 — Feature Engineering for MAE

- Category OHE + brand encoding → giảm bias theo category
- Price bucket feature → giúp model phân biệt cheap/expensive
- Brand tier encoding (luxury vs budget brand)

#### Hướng B5 — Ensemble/Blending

```python
# Blend trong raw-space (không cần log khi metric là MAE)
blend = 0.3 * ridge_pred + 0.7 * lgb_pred
# Optimize weights trên val set
```

> **Ghi nhớ:** Chọn hướng nào sau khi xem kết quả baseline Section 0-4. Ưu tiên hướng đơn giản nhất có cải thiện đáng kể.

---

## 5. Roadmap Notebook: `day3_v2_baseline_ml.ipynb`

### Section 0 — Setup & Load Data

```
Cell: Imports (sklearn, lightgbm, xgboost, datasets, pricer_vi_2)
Cell: Load items_tv_v9 → Item objects
Cell: EDA: price distribution, category counts, summary length
Cell: results = {}
```

### Section 1 — Statistical Baselines

```
Cell 1a: random_pricer → random.randrange(5, 1001)
Cell 1b: constant_pricer → mean(train prices)
Cell 1c: median_pricer → median(train prices)
Cell 1d: category_mean_pricer → mean theo từng category
```
Evaluate trên test (200 samples).

### Section 2 — Linear Regression Baselines

```
Cell: prices = np.array([item.price for item in train])  # raw, NO log1p
Cell 2a: LR với features đơn giản (text_length, title_length)
Cell 2b: LR + CountVectorizer (BoW, 2000 features)
Cell 2c: LR + TF-IDF char_wb (2-4gram, 100K)
```

### Section 3 — Benchmark Vectorizer

```
Cell: Install underthesea
Cell: 50K subset → docs_sub, prices_sub (raw)
Cell 3A: BoW + LGB → evaluate
Cell 3B: char_wb + LGB → evaluate
Cell 3C: Underthesea + LGB → evaluate (~30 min)
Cell: Bảng so sánh MAE 3 vectorizer
```

### Section 4 — RandomForest & XGBoost

```
Cell: Refit best vectorizer (char_wb) trên full 269K train
Cell 4a: RandomForest(100 trees, 15K subset) → evaluate
Cell 4b: XGBoost(1000 trees, full 269K) → evaluate (~30-60 min)
Cell: BẢNG SO SÁNH TỔNG HỢP Section 0-4 (MAE / MSE / R²)
```

### Section 5+ — MAE Optimization (TODO — sau khi có kết quả Section 0-4)

Chọn kỹ thuật từ Section 4 của plan này dựa trên phân tích kết quả baseline.

### Section Final — Evaluation & Save

```
Cell: Chạy best model trên test (3,872)
Cell: Save day3_v2_results.json
Cell: Tạo day3_v2_summary.md
```

---

## 5. Section 5 — Kết quả (2026-05-16/17)

**File:** `day3_v2/day3_v2_section5.ipynb`

| Section | Model | Config thực tế | MAE thực tế |
|---|---|---|---|
| **5A** | **LGB + char_wb TF-IDF** | **MSE obj, num_leaves=63, n=1000, 269K** | **92.6k ← BEST** |
| 5B | LGB + char_wb TF-IDF | MAE obj (regression_l1), 269K | 95.1k |
| 5C | Blend 5A+5B | **CHƯA implement** | — |
| 5D | RF + CountVect word (1,2) 50K | 15K subset | 123.3k |
| 5E | XGBoost + CountVect word (1,2) 50K | 269K | 113.2k |
| 5F | LGB + CountVect word (1,2) 50K | MSE obj, 269K | 97.3k |
| 5G | LGB + CountVect word (1,2) 50K | MAE obj, 269K | 100.0k |

**Ghi chú thực tế so với kế hoạch:**
- 5D/5E dùng CountVect 50K (không phải BoW 2000) — vì muốn test properly với large vocab
- 5F/5G thêm ngoài kế hoạch: so sánh CountVect vs TF-IDF trực tiếp với LGB
- 5C (blend) chưa implement — có thể cải thiện thêm ~1-3k nếu cần

**Root cause 4a/4b thua — xác nhận (hypothesis confirmed):**
- XGB + TF-IDF 100K (4b): 125.2k → XGB + CountVect 50K (5E): 113.2k (cải thiện 9.6k)
- RF + TF-IDF 100K (4a): 129.7k → RF + CountVect 50K (5D): 123.3k (cải thiện 6.4k)
- LGB không bị ảnh hưởng bởi high-dim vì xử lý sparse matrix tốt hơn

---

## 6. Folder Structure

```
Data_processing_for_Vietnamese_data/
├── day3_v2/
│   ├── plan_day3_v2.md                    # File này — CANONICAL
│   ├── day3_v2_baseline_ml.ipynb          # Notebook chính (Section 0-4)
│   ├── day3_v2_results.json               # Kết quả cuối (sau khi chạy xong)
│   └── day3_v2_summary.md                 # Summary (TODO)
│
└── pricer_vi_2/
    ├── items.py                            # Item class (price = round/1000)
    └── evaluator.py                        # Match English: MAE/MSE/R², hiển thị k VND
```

---

## 7. Acceptance Criteria

| Yêu cầu | Mức độ |
|---|---|
| `pricer_vi_2/items.py` load được `items_tv_v9` (3 splits) | Bắt buộc |
| `pricer_vi_2/evaluator.py` match English: MAE/MSE/R², hiển thị "k VND" | Bắt buộc |
| Baseline pipelines chạy được: random, mean, LR, LR+NLP, RF, XGB | Bắt buộc |
| Evaluate trên test set 200 samples (giống English) | Bắt buộc |
| Không dùng log1p transform (train trên raw price) | Bắt buộc |
| Section 3 benchmark đủ 3 vectorizer (BoW / char_wb / Underthesea) | Bắt buộc |
| day3_v2_results.json lưu đủ metrics (MAE, MSE, R²) của từng model | Bắt buộc |
| **Stretch: best model MAE < 90k VND** | **CHƯA đạt** — best = 92.6k (5A). Cần blend/OHE để đạt |

---

## 8. Key Technical Decisions (Chốt)

| Quyết định | Giá trị | Lý do |
|---|---|---|
| Price unit | `round(price_vnd / 1000)` — range 5–1000 | Align với English pipeline |
| Primary metric | **MAE (k VND)** | Range 5–1000 giống English → MAE trực quan, đủ dùng |
| Log transform | **Không dùng** | Không cần cho MAE; align với English day3 |
| Training target | raw price (5–1000) | Same as English |
| Evaluate data | `test` set, 200 samples | Giống English day3 |
| Primary vectorizer | `TfidfVectorizer(char_wb, ngram=(2,4), 100K)` | Mạnh nhất cho e-commerce Việt |
| Underthesea | Benchmark Section 3 — bắt buộc chạy để so sánh | Có thể tốt hơn char_wb |
| MAE optimization | **TODO Section 5+** — xem kết quả baseline trước | Hướng B1/B2/B3/B4/B5 trong Section 4 plan |
| Metrics xem | MAE (primary), MSE, R² | Nất quán với English evaluator |

---

## 9. Lưu Ý Kỹ Thuật

### 9.1. Tại sao KHÔNG dùng log1p với metric MAE

English day3 không dùng log1p. Lý do:
- RMSLE cần log1p vì RMSLE = RMSE trong log-space
- MAE không có lý do toán học cần log1p
- Train MSE trên raw price → model tối ưu cho MSE, báo cáo MAE → fine
- Range 5–1000 đã đủ nhỏ, không cần normalize thêm

### 9.2. LightGBM với sparse TF-IDF — không cần TruncatedSVD

Thực tế từ Section 5: LGB xử lý sparse CSR matrix trực tiếp tốt (cả TF-IDF 100K và CountVect 50K). Không cần SVD. SVD thường làm mất thông tin và không cải thiện MAE với LGB.

### 9.3. Blend trong raw-space khi metric là MAE

```python
# MAE → blend trong raw-space là đúng (không cần log-space)
blend = 0.3 * ridge_pred + 0.7 * lgb_pred
# Optimize trên val set để tìm weights tốt nhất
```

### 9.4. MAE Optimization — Tại sao để Section 5+

Baseline Section 0-4 xác định "mức sàn" và "mức trần" của từng approach. Chỉ sau khi biết gap giữa các model mới biết kỹ thuật nào cho ROI cao nhất. Không optimize sớm.

---

*Tạo: 2026-05-16 — Cập nhật 2026-05-16: đổi primary metric sang MAE, bỏ log1p, bám sát English pipeline.*
