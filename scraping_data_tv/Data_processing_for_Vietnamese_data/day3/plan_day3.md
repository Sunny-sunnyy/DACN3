# Day 3: Baseline ML — Vietnamese Price Prediction

**Ngay:** 2026-04-12 — 2026-04-15
**Trang thai:** HOAN TAT (v2 + v3)
**Branch:** `feature/data-preprocessing-vi`
**Dataset:** `SeanSunny/items_tv_v6` filtered <= 1,000,000 VND
**Best:** Blended RMSLE=0.5164 (3,872 test items)

---

## 1. Muc tieu

Xay dung va danh gia baseline ML models du doan gia san pham tieng Viet.
- **v2:** 9 models, evaluate 200 items, train tren raw VND
- **v3:** 12 models, evaluate 3,872 items (full), train tren log1p(price)
- **Primary metric:** RMSLE (chuan Kaggle cho e-commerce price prediction)

---

## 2. Du lieu

| | So luong | Chi tiet |
|---|---------|---------|
| **Raw** | 120K items | SeanSunny/items_tv_v6 (Tiki + Kaggle + Hasaki + WinMart) |
| **Filter** | <= 1M VND | 77.9% data, giam skew tu 6.85 → 1.23 |
| **Train** | 85,727 | |
| **Val** | 3,926 | Dung cho Optuna tuning (v3) |
| **Test** | 3,872 | Evaluate final |
| **Price range** | 4,900 — 1,000,000 VND | Mean: 301K, Median: 229K |
| **8 categories** | Thoi Trang, Dien Tu, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Lanh, O To | |

---

## 3. Phuong phap

### 3.1. Text Vectorization — 3 Architecture

| Arch | Mo ta | Dung cho |
|------|-------|----------|
| **A** | TfidfVectorizer raw, ngram_range=(1,2), max_features=10K | v2 baseline |
| **B** | Underthesea word_tokenize → TfidfVectorizer word, max_features=10K | v2 + v3 |
| **C** | Underthesea → FeatureUnion(word bigram 5K + char_wb 3-5gram 5K) | v3 |

- **Underthesea:** Tach tu tieng Viet ("dien_thoai", "may_tinh"). Pre-tokenize 1 lan, luu cache `.pkl`
- **char_wb:** Bat subword patterns (brand names, model numbers, specs: "500ml", "128gb")
- **Ket luan:** B tot hon A. C + tuning tot nhat, nhung C + default kem B.

### 3.2. Target Transform

| | v2 | v3 |
|---|---|---|
| **Target** | Raw VND | **log1p(price)** |
| **Predict** | VND truc tiep | expm1(pred_log) |
| **Tac dong** | LR predict am → RMSLE=1.75 | LR luon duong → RMSLE=0.55 |

Log-transform la cai thien co impact lon nhat (-8.8% RMSLE).

### 3.3. Feature Engineering (v3)

- Category one-hot: `OneHotEncoder(8 categories)` → 8 sparse features
- scipy.sparse `hstack([TF-IDF, category])` → 10,008 features
- Tat ca models dung cung feature matrix

### 3.4. Models

| Model | Library | Config chinh |
|-------|---------|-------------|
| Random | numpy | random.randint(min, max) |
| Mean | numpy | mean(train_prices) |
| Median | numpy | median(train_prices) |
| LR | sklearn | LinearRegression |
| Ridge | sklearn | Ridge(alpha=1.0) |
| RF | sklearn | n_estimators=300, n_jobs=6, subset=40K |
| XGBoost | xgboost | n_est=1000, lr=0.1, tree_method="hist" |
| LightGBM | lightgbm | n_est=1000, lr=0.1, n_jobs=6 |
| CatBoost | catboost | iterations=1000, lr=0.1 |
| LGB Tuned | lightgbm+optuna | num_leaves=173, lr=0.032, n_est=1500 |

### 3.5. Hyperparameter Tuning (v3)

```python
# Optuna — 50 trials tren validation set
{
    "num_leaves": 173,
    "min_child_samples": 50,
    "feature_fraction": 0.689,
    "lambda_l1": 0.011,
    "lambda_l2": 0.155,
    "learning_rate": 0.032,
    "n_estimators": 1500,
}
# Best val RMSLE: 0.5588 (1h28m)
```

### 3.6. Blending (v3)

```python
# Scipy minimize (Nelder-Mead) tim weights toi uu tren val set
weights = {
    "LightGBM Tuned C": 0.704,   # Dominant
    "LightGBM Tuned B": 0.188,
    "XGBoost B":         0.108,
    "CatBoost B":        0.000,   # Bi loai
}
```

---

## 4. Ket qua

### 4.1. v2 — Raw VND, 200 test items

| Model | RMSLE | MAE (VND) | MAPE (%) | R2 (%) |
|-------|------:|----------:|---------:|-------:|
| Random | 1.3126 | 343,784 | 227.0 | -200.5 |
| Mean | 0.8786 | 189,799 | 119.4 | -0.0 |
| Median | 0.8184 | 175,995 | 86.3 | -8.6 |
| LR (Arch A) | 1.7339 | 123,860 | 72.1 | 50.7 |
| LR (Arch B) | 1.7549 | 121,230 | 63.9 | 52.9 |
| RF (Arch B) | 0.6360 | 128,385 | 66.9 | 41.1 |
| XGBoost (Arch B) | 0.6385 | 124,993 | 70.9 | 47.6 |
| **LightGBM (Arch B)** | **0.5799** | **114,290** | **59.7** | 52.0 |
| CatBoost (Arch B) | 0.6307 | 125,425 | 70.0 | 46.8 |

### 4.2. v3 — Log-transform, 3,872 test items (FULL)

| # | Model | RMSLE | MAE (VND) | MAPE (%) | R2 (%) |
|---|-------|------:|----------:|---------:|-------:|
| 1 | **Blended (4 models)** | **0.5164** | **109,725** | **44.0** | **47.1** |
| 2 | LightGBM Tuned (C+Cat) | 0.5217 | 110,530 | 44.0 | 46.2 |
| 3 | LightGBM (B+Cat) | 0.5286 | 112,889 | 45.1 | 44.7 |
| 4 | LightGBM (C+Cat) | 0.5392 | 114,505 | 46.0 | 43.0 |
| 5 | Ridge (B+Cat) | 0.5415 | 114,785 | 46.6 | 42.5 |
| 6 | LightGBM Tuned (B+Cat) | 0.5459 | 114,852 | 46.9 | 43.1 |
| 7 | LR (B+Cat) | 0.5493 | 117,714 | 47.3 | 36.3 |
| 8 | XGBoost (B+Cat) | 0.5522 | 118,905 | 48.1 | 39.0 |
| 9 | CatBoost (B+Cat) | 0.5609 | 121,815 | 49.4 | 36.5 |
| 10 | Ridge (C+Cat) | 0.5697 | 121,307 | 49.6 | 37.3 |
| 11 | RF (B+Cat) | 0.5801 | 124,061 | 51.2 | 34.5 |
| 12 | Median baseline | 0.7736 | 169,571 | 77.4 | -10.4 |

### 4.3. v2 vs v3

| Metric | v2 (200 items) | v3 (3,872 items) | Thay doi |
|--------|---------------|-------------------|----------|
| RMSLE | 0.5799 | **0.5164** | **-10.9%** |
| MAE | 114,290 | **109,725** | -4.0% |
| MAPE | 59.7% | **44.0%** | **-26.3%** |
| R2 | 52.0% | 47.1% | -9.4% (stable hon) |

---

## 5. Pipeline tot nhat (Day 3 Final)

```
Text (summary)
  → Underthesea word_tokenize (cache .pkl)
  → FeatureUnion (Arch C):
      |- TfidfVectorizer(word, bigram, 5K features)
      |- TfidfVectorizer(char_wb, 3-5gram, 5K features)
  → hstack with OneHotEncoder(category, 8 features)  → 10,008 features
  → log1p(price) target
  → LightGBM Tuned (Optuna)
  → expm1(prediction) → VND
  → RMSLE = 0.5217 (single) | 0.5164 (blended)
```

### So sanh Architecture

| Arch | LGB Default | LGB Tuned | Nhan xet |
|------|-------------|-----------|----------|
| **B** (word only) | **0.5286** | 0.5459 | Default tot, tuning overfit |
| **C** (word+char) | 0.5392 | **0.5217** | Default kem, tuning tot nhat |

### So sanh Model (Arch B+Cat, log-transform)

| Model | RMSLE | Train time | Nhan xet |
|-------|------:|--------:|----------|
| **LightGBM** | **0.5286** | 34s | Nhanh nhat, tot nhat |
| Ridge | 0.5415 | 1s | Bat ngo tot — canh tranh ensemble |
| XGBoost | 0.5522 | 3.2 phut | |
| CatBoost | 0.5609 | 2.7 phut | |
| RF | 0.5801 | 19 phut | Cham nhat, kem nhat |

### Tac dong cua tung cai thien

| Cai thien | RMSLE truoc → sau | % giam | Impact |
|-----------|-------------------|--------|--------|
| **Log-transform** | 0.5799 → 0.5286 | -8.8% | **LON NHAT** |
| Category feature | (khong co) → (co) | ~2-5% | Trung binh |
| Optuna tuning | 0.5392 → 0.5217 | -3.2% | Trung binh |
| Arch C (char_wb) | 0.5286 → 0.5217 | -1.3% | Nho |
| Blending | 0.5217 → 0.5164 | -1.0% | Nho |

---

## 6. Bai hoc chinh

1. **Log-transform bat buoc** khi dung RMSLE. LR het predict am, tat ca models cai thien.
2. **Ridge canh tranh ensemble** voi TF-IDF sparse (chi kem LGB 2.4%) — regularization quan trong.
3. **Arch C can tuning** — char_wb them noise khi default, nhung tuning khai thac duoc.
4. **Optuna co the overfit val** — tuned B te hon default B tren test.
5. **Blending diminishing returns** khi models tuong tu (chi giam 1%).
6. **RMSLE ~0.52 la tran** cua TF-IDF bag-of-words — can dense embeddings cho < 0.45.

---

## 7. Luu y ky thuat

- Underthesea KHONG thread-safe — phai pre-tokenize va cache .pkl
- XGBoost/CatBoost GPU treo voi sparse matrix 85K x 10K → dung CPU
- v2: LR predict am cho SP re → clip 0 → RMSLE=1.75 du R2=52.9%
- v3: Log-transform giai quyet hoan toan van de nay
- R2 v2 (52%) cao hon v3 (47%) vi evaluate 200 items inflate (variance cao)

---

## 8. Files

```
day3/
    plan_day3.md                    # File nay
    day3_baseline_ml_1m.py          # v2 script (9 models, raw VND, 200 items)
    day3_baseline_ml_1m.ipynb       # v2 notebook
    day3_baseline_ml_1m_v3.py       # v3 script (12 models, log, full eval, tuning, blend)
    day3_baseline_ml_1m_v3.ipynb    # v3 notebook
    day3_baseline_ml_1m_v3.txt      # v3 output (.py)
    ketquaday3_v1.txt               # v2 output (.py)
    day3_baseline_ml.py             # v1 script (full dataset, DA BO)
    day3_baseline_ml_notebook_5060ti.ipynb  # v1 notebook cu
    tokenized_train_1m.pkl          # Underthesea cache train (85K docs)
    tokenized_test_1m.pkl           # Underthesea cache test (3.9K docs)
    tokenized_val_1m.pkl            # Underthesea cache val (3.9K docs)
```

### Dependencies

```bash
uv add scikit-learn xgboost lightgbm catboost plotly underthesea optuna
```

### Cau hinh chay

- May thue: i5-13400F 12C / Ryzen 5 7500F 6C | 28GB RAM | RTX 5060 Ti 16GB (chi dung CPU)
- Tong thoi gian v3: ~3 tieng (RF 19 phut, Optuna 1h28m)
- Tokenize cache portable giua cac may cung Python 3.x va cung dataset

---

## 9. Huong di tiep — Day 4

**Gioi han Day 3:** TF-IDF mat thong tin thu tu, ngu nghia, ngu canh. R2=47%, MAPE=44%.

**Day 4 can:**
1. Dense text embeddings (PhoBERT, Sentence-BERT) thay TF-IDF
2. DNN (ResidualBlock) voi dense features
3. Fine-tune LLM (Qwen 3.5 4B) — ky vong RMSLE < 0.40
4. So sanh: TF-IDF+LightGBM (0.52) vs Embeddings+DNN vs Fine-tuned LLM

**Target Day 4:** RMSLE <= 0.40

---

*Cap nhat: 2026-04-15. Day 3 DONE. Best: Blended RMSLE=0.5164. Buoc tiep: Day 4.*