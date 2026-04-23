# Day 3 — Baseline ML: Vietnamese Price Prediction

**Mục tiêu:** Xây dựng các model ML baseline để dự đoán giá sản phẩm tiếng Việt.  
**Metric chính:** RMSLE (Root Mean Squared Logarithmic Error) — chuẩn Kaggle cho price prediction.  
**Kết quả tốt nhất:** Blended RMSLE = **0.5164**

---

## 1. Dữ liệu đầu vào

**Dataset:** `SeanSunny/items_tv_v6` (HuggingFace Hub)  
**Nguồn gốc:** Tiki 102K + Kaggle 42K + Hasaki 11K + WinMart 3K = ~158K sản phẩm  
**Sau khi filter** giá <= 1,000,000 VND (loại 22.1% outlier đắt):

| Split | Số lượng |
|-------|---------|
| Train | 85,727 |
| Val   | 3,926   |
| Test  | 3,872   |

**Mỗi sản phẩm (Item) gồm:**

| Field | Kiểu | Nội dung |
|-------|------|---------|
| `title` | str | Tên sản phẩm ngắn |
| `summary` | str | Mô tả 5 dòng (đã rewrite bằng LLM ở Day 2) |
| `category` | str | 1 trong 8 danh mục |
| `price` | int | Giá VND — **label cần dự đoán** |
| `full` | str | Mô tả gốc đầy đủ (không dùng ở Day 3) |

**8 danh mục:** Thời Trang, Điện Tử Công Nghệ, Nhà Cửa, Bách Hóa, Làm Đẹp, Mẹ và Bé, Điện Lạnh Gia Dụng, Ô Tô Xe Máy

**Phân phối giá:**
- Range: 4,900 — 1,000,000 VND
- Mean: ~301,000 VND | Median: ~229,000 VND
- Phân phối lệch phải (right-skewed) → cần log-transform

---

## 2. Xử lý dữ liệu đầu vào

### 2a. Lọc dữ liệu

```
Raw dataset (~110K) → filter price <= 1,000,000 VND → 93,525 items
```

Lý do filter: giá > 1M VND chiếm 22.1% nhưng là outlier (xe máy, thiết bị điện nặng),  
làm tăng skewness từ 6.85 → 1.23 sau khi loại bỏ.

### 2b. Tách từ tiếng Việt (Underthesea)

Tiếng Việt viết liền, TF-IDF raw sẽ không nhận diện được từ ghép:

```
Raw:       "điện thoại thông minh pin 5000mah"
Tokenized: "điện_thoại thông_minh pin 5000mah"
```

**Thư viện:** `underthesea.word_tokenize(text, format="text")`  
**Lưu ý:** Không thread-safe → phải tokenize single-thread, cache vào `.pkl`.  
**Cache files:** `tokenized_train_1m.pkl` / `tokenized_val_1m.pkl` / `tokenized_test_1m.pkl`

### 2c. Log-transform target

```python
y_train = log1p(price)   # train
y_pred  = expm1(pred)    # inference
```

**Tại sao cần log-transform?**
- RMSLE đo lỗi trên log-scale → train trên log-space align với metric
- Linear model không bị predict âm sau transform
- Giảm ảnh hưởng của outlier giá cao
- Tác động: giảm RMSLE từ ~0.57 xuống ~0.52 (-8.8%) — **cải tiến lớn nhất**

---

## 3. Feature Engineering

### 3a. Text Vectorization — 3 Architectures

**Architecture A** — TF-IDF raw (không tách từ)
```
Raw summary → TF-IDF(ngram=(1,2), max_features=10K) → 10,000 features
```
Đơn giản nhất. Không nhận diện từ ghép tiếng Việt.

**Architecture B** — Underthesea + TF-IDF word
```
Raw summary → word_tokenize → TF-IDF(word unigram, max_features=10K) → 10,000 features
```
Cải thiện so với A vì từ ghép như `"điện_thoại"`, `"máy_tính"` được nhận diện đúng.

**Architecture C** — Underthesea + TF-IDF hybrid (word + char_wb)
```
Raw summary → word_tokenize → FeatureUnion:
    ├── TF-IDF(word, bigram, 5K features)
    └── TF-IDF(char_wb, 3-5gram, 5K features)
→ 10,000 features
```
`char_wb` bắt patterns như `"samsung"`, `"128gb"`, `"iphone_14"` dù viết tắt hay không dấu.  
Tốt hơn B sau hyperparameter tuning, nhưng cần tuning (default params kém hơn B).

### 3b. Category Feature (One-Hot Encoding)

```python
OneHotEncoder(8 categories) → 8 sparse features
scipy.sparse.hstack([X_tfidf, X_cat]) → combined matrix
```

**Arch B + Cat** = TF-IDF_B (10K) + OneHot (8) = **10,008 features**  
**Arch C + Cat** = TF-IDF_C (10K) + OneHot (8) = **10,008 features**

Thêm category giúp ~2-5% vì mỗi danh mục có price range khác nhau:
- Ô Tô Xe Máy: 200K–1M VND
- Bách Hóa: 5K–100K VND

---

## 4. Các mô hình sử dụng

### Tier 1 — Statistical Baselines (không ML, không text)

| Model | Dự đoán | RMSLE |
|-------|---------|-------|
| Random | random(min, max) | ~1.31 |
| Mean | mean(train_prices) = 301K | ~0.88 |
| Median | median(train_prices) = 229K | ~0.77 |

Không dùng text, chỉ dùng thống kê phân phối giá. Kết quả tệ nhưng là lower bound để so sánh.

### Tier 2 — LR + TF-IDF (không log-transform)

| Model | Feature | RMSLE |
|-------|---------|-------|
| Linear Regression | Arch A (raw bigram) | ~1.73 |
| Linear Regression | Arch B (Underthesea) | ~1.75 |

Train trên raw VND → RMSLE rất cao vì:
1. LR predict âm cho sản phẩm giá rẻ → clip về 0 → lỗi lớn
2. Không align với RMSLE metric (MSE trên raw VND ≠ RMSLE)

> Tier 2 là minh họa — mục đích cho thấy log-transform quan trọng như thế nào.

### Tier 3 — ML với log-transform + category feature

Tất cả train trên `log1p(price)`, predict `expm1(pred)`.

**Ridge + Arch B + Cat**
```
L2 regularization: loss = MSE + alpha * ||w||²
alpha = 1.0
```
- Linear model với regularization, train ~1 giây
- Bất ngờ cạnh tranh với GBDT (kém LGB chỉ 2.4%)
- TF-IDF sparse matrix phù hợp với linear model
- RMSLE: **0.5415**

**LightGBM Default + Arch B + Cat**
```
n_estimators = 1000
learning_rate = 0.1
```
- GBDT nhanh nhất (Leaf-wise tree growth + histogram-based)
- Default params đã tốt hơn RF/XGBoost/CatBoost
- RMSLE: **0.5286**

**LightGBM Tuned + Arch C + Cat**
```
num_leaves        = 173    # độ phức tạp cây
min_child_samples = 50     # regularize leaf size
feature_fraction  = 0.689  # dùng 68.9% features/cây
lambda_l1         = 0.011  # L1 regularization
lambda_l2         = 0.155  # L2 regularization
learning_rate     = 0.032  # nhỏ hơn default → generalize tốt hơn
n_estimators      = 1500   # nhiều cây hơn vì lr nhỏ
```
Hyperparameter tìm bằng **Optuna** (50 trials, ~1.5h, optimize val RMSLE).  
- RMSLE: **0.5217**

### Tier 4 — Weighted Blending

Kết hợp predictions của 3 model tốt nhất:
```
final = w1 * LGB_Tuned_C + w2 * LGB_Default_B + w3 * Ridge_B
```

Weights tìm bằng `scipy.optimize.minimize` (Nelder-Mead) trên val set:
```
LightGBM Tuned C+Cat : 0.704
LightGBM B+Cat       : 0.188
XGBoost B+Cat        : 0.108   (v3 gốc dùng XGBoost thay Ridge)
```

- RMSLE: **0.5164** — best Day 3

---

## 5. So sánh kết quả

| Model | RMSLE | MAE (VND) | MAPE | R2 |
|-------|------:|----------:|-----:|---:|
| Blended (3 models) | **0.5164** | 109,725 | 44.0% | 47.1% |
| LightGBM Tuned C+Cat | 0.5217 | 110,530 | 44.0% | 46.2% |
| LightGBM B+Cat | 0.5286 | 112,889 | 45.1% | 44.7% |
| Ridge B+Cat | 0.5415 | 114,785 | 46.6% | 42.5% |
| Median (baseline) | 0.7736 | 169,571 | 77.4% | -10.4% |

---

## 6. Kết quả đầu ra

**Dự đoán:** Giá sản phẩm tính bằng VND (số nguyên dương)

**Pipeline inference:**
```
item.summary
  → word_tokenize (load từ cache)
  → TF-IDF Arch C transform
  → hstack với OneHot(category)
  → LGBMRegressor.predict()
  → log1p → expm1
  → clip(0, None)
  → price_vnd
```

**File output:**
- `tokenized_train/val/test_1m.pkl` — tokenized text cache
- `items_train/val/test.pkl` — Item objects cache

---

## 7. Impact của từng cải tiến

| Cải tiến | RMSLE trước → sau | % giảm |
|----------|-------------------|--------|
| Log-transform target | ~0.579 → ~0.529 | **-8.8%** |
| Category feature | ~0.529 → ~0.502 | ~-5% |
| Optuna tuning | 0.539 → 0.522 | -3.2% |
| Arch C (char_wb) | 0.529 → 0.522 | -1.3% |
| Blending | 0.522 → 0.516 | -1.0% |

---

## 8. Giới hạn và hướng Day 4

**Tại sao Day 3 bị giới hạn ở ~0.52?**

TF-IDF là bag-of-words — không hiểu:
- **Thứ tự từ:** "điện thoại giá rẻ" vs "giá rẻ điện thoại" → cùng vector
- **Ngữ nghĩa:** "Samsung" và "Oppo" là 2 từ khác nhau, không biết cả 2 đều là điện thoại
- **Ngữ cảnh:** "pin 5000mAh" vs "màn hình 5 inch" → không biết loại spec nào quan trọng hơn

**Day 4 giải pháp:** Dense embeddings từ pre-trained language models

| Approach | Model | RMSLE |
|----------|-------|-------|
| Frozen embeddings | AITeamVN BGE-M3 (1024d) + MLP | 0.4986 |
| Full fine-tune | PhoBERT-base-v2 | 0.4418 |
| Fine-tune + LLRD + EMA | PhoBERT++ | 0.4322 |
| Stacking 7 models | Ridge + ElasticNet + LGB meta | **0.4059** |
