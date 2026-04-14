# Day 3: Baseline ML — Plan chi tiet

**Ngay:** 2026-04-12
**Cap nhat:** 2026-04-14
**Trang thai:** HOAN TAT (v1 — all steps done, ket qua o Section 8+12)
**Branch:** `feature/data-preprocessing-vi`
**Input:** `SeanSunny/items_tv_v6` filtered <= 1,000,000 VND (85K train / 3.9K val / 3.9K test)

---

## 1. Muc tieu

Xay dung va danh gia 7+ baseline models du doan gia san pham tieng Viet:
- **Baseline don gian:** Random, Mean, Median
- **Traditional ML:** Linear Regression (BoW)
- **Ensemble ML:** Random Forest, XGBoost, LightGBM, CatBoost

**Metrics chinh:** RMSLE (primary), MAE (VND), MAPE (%), R2

---

## 2. Nghien cuu: Vietnamese Text Vectorization

### 2.1. Van de cot loi

Tieng Viet la ngon ngu **da am tiet** (polysyllabic) — mot tu co the gom nhieu am tiet cach nhau boi dau cach:
- "may tinh" = 1 tu (2 am tiet)
- "dien thoai thong minh" = 2 tu (4 am tiet)

Neu dung `CountVectorizer` mac dinh (split theo dau cach), se tach "may" va "tinh" thanh 2 token rieng biet → mat nghia.

### 2.2. Ba kien truc de xuat

#### Kien truc A: TF-IDF + n-gram (Khong tach tu)

```python
vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
X = vectorizer.fit_transform(summaries)
```

| | Chi tiet |
|---|---|
| **Cach lam** | Dung TfidfVectorizer voi bigram, split theo khoang trang |
| **Uu diem** | Nhanh nhat (~2 giay), khong can cai them gi |
| **Uu diem** | n-gram bat duoc cum tu "may tinh", "dien thoai" tu nhien |
| **Uu diem** | Summary da duoc LLM rewrite — cau truc sach, tu vung nhat quan |
| **Nhuoc diem** | Bigram tang feature space, can max_features lon hon |
| **Nhuoc diem** | Khong hoan hao cho tu 3+ am tiet ("dien thoai thong minh") |
| **Toc do** | ~1-2 giay cho 110K documents |
| **Khi nao dung** | Baseline nhanh, so sanh voi B |

#### Kien truc B: Underthesea Pre-tokenize + TF-IDF (Recommended)

```python
from underthesea import word_tokenize
from multiprocessing import Pool

# Pre-tokenize 1 lan, luu cache
def tokenize_one(text):
    return word_tokenize(text, format="text")

with Pool(4) as p:
    tokenized_summaries = p.map(tokenize_one, summaries)

# Dung TfidfVectorizer binh thuong (da tach tu san)
vectorizer = TfidfVectorizer(max_features=10000)
X = vectorizer.fit_transform(tokenized_summaries)
```

| | Chi tiet |
|---|---|
| **Cach lam** | Pre-tokenize toan bo corpus 1 lan (multiprocessing) → luu ket qua → TF-IDF |
| **Uu diem** | Nhan dien dung tu ghep: "may_tinh", "dien_thoai_thong_minh" |
| **Uu diem** | Chi tokenize 1 lan, dung lai cho nhieu model |
| **Uu diem** | Multiprocessing tang toc 3-4x |
| **Nhuoc diem** | Can cai underthesea (~150MB), cham hon A (~30-60 giay) |
| **Nhuoc diem** | Mot so truong hop tach sai (ten san pham ngoai, ky tu dac biet) |
| **Toc do** | ~30-60 giay cho 110K documents (4 workers) |
| **Khi nao dung** | So sanh voi A de chon final approach |

### 2.3. Quyet dinh

**Chien luoc:** Thuc hien **ca A va B**, so sanh ket qua:
1. Chay model voi **Kien truc A** (TF-IDF + n-gram) truoc — baseline nhanh
2. Chay model voi **Kien truc B** (underthesea pre-tokenize) — xem cai thien bao nhieu
3. So sanh RMSLE/MAE/MAPE giua 2 cach → quyet dinh dung cach nao cho final
4. Nghiên cứu thêm về:  Underthesea Unigram + Scikit-learn N-gram (Hybrid Word-Ngram) (gemini đề xuất)
5. Nghiên cứu thêm: Chọn hướng đi Hybrid kết hợp Character N-gram:

Chạy Underthesea trên văn bản (như cấu hình bạn định làm): Cứ để nó tách từ tiếng Việt. Nó sẽ giúp bạn ghép các cụm từ quan trọng lại với nhau (như điện_thoại). Mặc kệ việc nó cắt sai từ tiếng Anh.

Cấu hình TfidfVectorizer (Cú "Hack" sức mạnh): Thay vì chỉ dùng từ vựng (word), bạn hãy chạy đồng thời 2 luồng TF-IDF (bằng FeatureUnion của sklearn) hoặc chọn luồng Character N-gram.

Luồng 1 (Semantic): TfidfVectorizer(analyzer='word', ngram_range=(1, 2))

Luồng 2 (Robustness): TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5)) (gemini đề xuất)
### 2.4. Chon TF-IDF thay vi CountVectorizer

Nghien cuu cho thay **TF-IDF tot hon CountVectorizer** cho bai toan price prediction:
- TF-IDF tu dong giam trong so cua tu xuat hien nhieu (noise) va tang trong so cua tu hiem (signal)
- VD: tu "san pham" xuat hien khap noi → trong so thap; tu "iPhone" chi xuat hien o 1 so SP → trong so cao
- Trong bai toan gia, cac tu chi diem thuong la tu hiem (ten model, thuong hieu cao cap)

### 2.5. Stop words

- **Khong dung stop words** o buoc dau tien
- Ly do: Summary da duoc LLM rewrite → cau truc sach, it tu thua
- Neu can, se them sau khi phan tich feature importance

---

## 3. Architecture tong the

### 3.1. Pipeline

```
HF Hub (items_tv_v6)
    → Item.from_hub()
    → [train, val, test] (Item objects)
    → item.summary (text)
    → TfidfVectorizer (A hoac C)
    → Sparse Matrix X
    → Models (7+)
    → Predictions
    → Evaluator (RMSLE, MAE, MAPE, R2)
    → Results table + Charts
```

### 3.2. Models

| # | Model | Loai | Mo ta | Thoi gian uoc tinh |
|---|---|---|---|---|
| 1 | Random | Baseline | Random int trong range gia | < 1 giay |
| 2 | Mean | Baseline | Luon tra ve gia trung binh tap train | < 1 giay |
| 3 | Median | Baseline | Luon tra ve gia trung vi tap train | < 1 giay |
| 4 | Linear Regression | ML | sklearn LinearRegression + TF-IDF | < 10 giay |
| 5 | Random Forest | Ensemble | sklearn RandomForestRegressor (subset) | 1-3 phut |
| 6 | XGBoost | Ensemble | xgb.XGBRegressor | 1-5 phut |
| 7 | LightGBM | Ensemble | lgb.LGBMRegressor | 1-3 phut |
| 8 | CatBoost | Ensemble | catboost.CatBoostRegressor | 2-5 phut |

Nghiên cứu thêm:
Đề xuất 1: Thay Linear Regression bằng Ridge Regression (L2 Regularization)
Đề xuất 2: Bổ sung Truncated SVD (LSA) trước khi đưa vào Tree-based Models
Đề xuất 3: Khai thác tính năng Text Feature gốc của CatBoost

### 3.3. Metrics

**Tai sao can nhieu metrics?** Price range VND rat lon (1K-50M):
- SP 600K du doan 640K → MAE=40K (lon) nhung MAPE=6.7% (tot)
- SP 10K du doan 15K → MAE=5K (nho) nhung MAPE=50% (te)
→ MAE thien vi SP dat, MAPE thien vi SP re. Can RMSLE de cong bang.

| Metric | Vai tro | Cong thuc | Y nghia |
|---|---|---|---|
| **RMSLE** | **Primary** | sqrt(mean((log(pred+1) - log(true+1))^2)) | Sai so tuong doi tren thang log — cong bang cho moi muc gia |
| **MAE** | Reporting | mean(\|pred - true\|) | Sai so tuyet doi trung binh (VND) |
| **MAPE** | Reporting | mean(\|pred - true\| / true) x 100 | Sai so phan tram trung binh (%) |
| **R2** | Reporting | 1 - SS_res / SS_tot | Mo hinh giai thich duoc bao nhieu % bien thien |

**Bo MSE** — kho dien giai voi VND (don vi VND^2), thong tin trung lap voi RMSLE.

**RMSLE la metric chuan cua Kaggle** cho e-commerce price prediction (VD: Mercari Price Suggestion Challenge). No tinh sai so tuong doi tren thang log → SP 10K va SP 10M duoc doi xu cong bang.

---

## 4. File structure

```
Data_processing_for_Vietnamese_data/
    pricer_vi/
        evaluator.py              # MOI — Evaluator class (MAE, MAPE, MSE, R2, charts)
    day3_baseline_ml.py           # MOI — Script chay tu dong (output ket qua)
    day3_baseline_ml.ipynb        # MOI — Notebook tuong tac (cho user chay)
    day3/
        plan_day3.md              # File nay
```

---

## 5. Tien trinh thuc hien (step-by-step)

### Step 1: Cai dat dependencies
```bash
uv add xgboost lightgbm catboost plotly scikit-learn underthesea
```
**Tieu chi:** Import thanh cong tat ca packages.

### Step 2: Tao `pricer_vi/evaluator.py`
- Adapt tu code tieng Anh nhung cho VND
- Metrics: RMSLE (primary), MAE (VND), MAPE (%), R2
- Default size: 200 items (nhanh) + option `size="all"` cho full test
- Charts: Scatter plot (actual vs predicted), Error trend
- VND formatting: `{price:,.0f} VND` thay vi `${price:,.2f}`
- Color thresholds dua tren MAPE (% sai so):
  - Green: MAPE < 20% (du doan tot)
  - Orange: MAPE < 40% (chap nhan duoc)
  - Red: MAPE >= 40% (sai nhieu)

**Tieu chi:** `from pricer_vi.evaluator import evaluate` chay thanh cong.

### Step 3: Tao `day3_baseline_ml.py` — Baseline models
- Load data tu HF Hub
- Random pricer
- Mean pricer (gia trung binh)
- Median pricer (gia trung vi)
- Evaluate ca 3, in ket qua

**Tieu chi:** 3 models chay, in duoc MAE/MAPE.

### Step 4: Them Linear Regression + TF-IDF (Kien truc A)
- TfidfVectorizer voi ngram_range=(1,2), max_features=10000
- Linear Regression tren TF-IDF features
- Evaluate

**Tieu chi:** MAE giam dang ke so voi Mean/Median.

### Step 5: Them Underthesea tokenization (Kien truc B)
- Pre-tokenize summaries (multiprocessing, 4 workers)
- TfidfVectorizer tren tokenized text
- So sanh voi Kien truc A

**Tieu chi:** Co ket qua so sanh A vs B.


# Lưu ý: Lưu kết quả ra file: Sau khi tokenize xong 1 lần, hãy dùng pickle hoặc lưu thành file .txt để lần sau chạy code không cần tokenize lại từ đầu.

### Step 6: Them XGBoost, LightGBM, CatBoost
- XGBoost: n_estimators=1000, learning_rate=0.1
- LightGBM: n_estimators=1000, learning_rate=0.1
- CatBoost: iterations=1000, learning_rate=0.1

**Tieu chi:** 3 ensemble models chay thanh cong, in ket qua.

### Step 7: Tong hop + Charts
- Bang ket qua tat ca models
- Bar chart so sanh MAE
- Scatter plot cho model tot nhat
- Nhan xet va danh gia

**Tieu chi:** Co bang tong hop day du.

### Step 8: Tao notebook `day3_baseline_ml.ipynb`
- Convert logic tu .py sang notebook
- Them markdown cells giai thich
- Them visualization cells

**Tieu chi:** User co the chay notebook tu dau den cuoi.

---

## 6. Khac biet voi pipeline tieng Anh

| | Tieng Anh (ed-donner) | Tieng Viet (cua minh) |
|---|---|---|
| **Price** | USD (float, $0-999) | VND (int, 1K-50M) |
| **Scale** | Nho (~$100 trung binh) | Lon (~500K VND trung binh) |
| **Weight feature** | Co (item.weight) | Khong co |
| **Text source** | item.summary | item.summary (5 truong) |
| **Stop words** | `stop_words='english'` | Khong dung (hoac custom) |
| **Tokenization** | Default (English) | underthesea word_tokenize |
| **Vectorizer** | CountVectorizer(max_features=2000) | TfidfVectorizer(max_features=10000) |
| **Models** | Random, Mean, LR, RF, XGBoost | + Median, LightGBM, CatBoost |
| **Evaluate size** | 200 (co dinh) | 200 default + option full (5K) |
| **Metrics** | MAE ($), MSE, R2 | **RMSLE (primary)**, MAE (VND), MAPE (%), R2 |
| **Dataset** | 800K train / 10K test | 110K train / 5K test |

---

## 7. Tieu chi thanh cong Day 3

- [x] `evaluator.py` hoat dong: evaluate mo hinh bat ky, in metrics + ve charts
- [x] 3 baselines (Random, Mean, Median) chay va co ket qua
- [x] Linear Regression + TF-IDF chay, MAE giam so voi baselines
- [x] So sanh Kien truc A vs B (co/khong underthesea)
- [x] XGBoost, LightGBM, CatBoost chay thanh cong
- [x] Bang tong hop ket qua tat ca models
- [x] File `.py` tu chay va in ket qua
- [x] File `.ipynb` san sang cho user chay
- [x] Cap nhat `SESSION_HANDOFF.md`

---

## 8. Ket qua kiem chung

### v1 — Full dataset (4.9K - 50M VND, 200 test items) — DA BO

| Step | Trang thai | Ket qua | Ghi chu |
|---|---|---|---|
| 3. Baselines | DONE | Median RMSLE=1.41 | Mean/Median gap 4.3x, phan phoi lech rat manh |
| 4. LR + TF-IDF (A) | DONE | RMSLE=6.08, R2=52.1% | Predict am → clip 0 → RMSLE cuc cao |

**Quyet dinh:** Chuyen sang filter <= 1M VND de giam skewness va de huan luyen hon.

### v2 — Filtered <= 1M VND (85K train / 3.9K test, 200 test items) — KET QUA CHINH

| Step | Trang thai | Ket qua | Ghi chu |
|---|---|---|---|
| 1. Dependencies | DONE | OK | xgboost, lightgbm, catboost, plotly, underthesea |
| 2. Evaluator | DONE | OK | RMSLE primary, VND tick format (100k, 200k...) |
| 3. Baselines | DONE | Median RMSLE=0.82 | Mean=0.88, Random=1.31 |
| 4. LR + TF-IDF (A) | DONE | RMSLE=1.73, R2=50.7% | MAE tot (124K) nhung RMSLE te vi predict am |
| 5. Underthesea (B) | DONE | RMSLE=1.75, R2=52.9% | Arch B cai thien MAE/MAPE/R2 so voi A |
| 6. Ensemble models | DONE | LightGBM best=0.58 | RF=0.64, XGB=0.64, CatBoost=0.63 |
| 7. Tong hop | DONE | Bang + nhan xet | day3/ketquaday3_v1.txt |
| 8. Files | DONE | OK | day3_baseline_ml_1m.py + .ipynb |

---

## 9. Luu y: Data cleaning (neu ket qua khong tot)

**Van de phat hien:** 28% titles (33,583/120K) chua SKU codes (TEBAT870, BR6221A, UG40369MM128TK...).
**Phan tich:** Scan cho thay ~83% "codes" thuc ra la thong so ky thuat co gia tri (1500W, 500ML, SPF50, 1080P).
SKU that su (TEBAT870...) xuat hien 1x → TF-IDF voi max_features=5000 se tu dong loai.

**Quyet dinh hien tai:** De nguyen, chay Day 3 truoc.

**Neu RMSLE/MAE khong tot (VD: ensemble models khong cai thien dang ke so voi baselines):**
1. **Phuong an 1 (Nhanh, mien phi):** Regex post-processing xoa SKU codes tu summary
2. **Phuong an 2 (Tot hon, ~$1):** Re-run Day 2 voi SYSTEM_PROMPT v3 (3 truong: Tieu de + Mo ta + Thong so). LLM se rewrite title, tu dong loai SKU codes. Da test 8 items — LLM phan biet tot specs vs noise (giu 1500W, bo TEBAT870).
3. Kiem tra feature importance cua top models — xem co SKU codes nao lot vao top features khong.


---

## 10. Dependencies

```toml
# pyproject.toml — can them
[project.dependencies]
scikit-learn = ">=1.4"
xgboost = ">=2.0"
lightgbm = ">=4.0"
catboost = ">=1.2"
plotly = ">=5.0"
underthesea = ">=6.0"
```
- Co dinh Random Seed (Kha nang tai lap)
- Thiet lap Early Stopping cho Ensemble Models
- So sanh Kien truc A vs B de chon final tokenization

**Tham khao code tieng Anh:**
- `Code_Data_processing/pricer/evaluator.py` — Tester class, Plotly charts, evaluate() function
- `Code_Data_processing/pricer/deep_neural_network.py` — ResidualBlock, DeepNeuralNetwork, Runner class
- `Code_Data_processing/day3.ipynb` — Random, LR, RF, XGBoost baselines

---

*Tao: 2026-04-12. Cap nhat: 2026-04-14. Day 3 v2 DONE. Buoc tiep: Day 3 v3 (ML optimization, Section 13).*

---

## 11. Nhat ky thuc hien

### 2026-04-13 20h: Day 2 hoan tat
- Da chay lai toan bo data, ket qua da xoa SKU codes, giu lai cac thong so ky thuat co gia tri
- Xem ket qua: `day2_llm_preprocessing_v4.ipynb`
- Su dung bo du lieu: `SeanSunny/items_tv_v6`

### 2026-04-14: Day 3 v1 — Full dataset (DA BO)

Chay full dataset (4.9K-50M VND). Phan phoi lech qua manh (Mean/Median = 4.3x, skew=6.85).
Quyet dinh chuyen sang filter <= 1M VND (77.9% data, skew=1.23).

### 2026-04-14: Day 3 v2 — Filtered <= 1M VND — KET QUA CHINH

**Du lieu:**
- Dataset: `SeanSunny/items_tv_v6` filtered <= 1,000,000 VND
- Train: 85,727 | Val: 3,926 | Test: 3,872
- Price range: 4,900 - 1,000,000 VND
- Mean: 301,687 | Median: 229,000 | Std: 228,179 VND
- Mean/Median = 1.32x (gan symmetric, tot cho ML)

**Bang tong hop ket qua (200 test items):**

| Model | RMSLE | MAE (VND) | MAPE (%) | R2 (%) |
|-------|------:|----------:|---------:|-------:|
| Random | 1.3126 | 343,784 | 227.0 | -200.5 |
| Mean | 0.8786 | 189,799 | 119.4 | -0.0 |
| Median | 0.8184 | 175,995 | 86.3 | -8.6 |
| LR + TF-IDF (Arch A) | 1.7339 | 123,860 | 72.1 | 50.7 |
| LR + TF-IDF (Arch B) | 1.7549 | 121,230 | 63.9 | 52.9 |
| Random Forest (Arch B) | 0.6360 | 128,385 | 66.9 | 41.1 |
| XGBoost (Arch B) | 0.6385 | 124,993 | 70.9 | 47.6 |
| **LightGBM (Arch B)** | **0.5799** | **114,290** | **59.7** | 52.0 |
| CatBoost (Arch B) | 0.6307 | 125,425 | 70.0 | 46.8 |

**Best model: LightGBM — RMSLE=0.5799**

---

## 12. Phan tich ket qua

### 12.1. Ranking theo RMSLE (primary metric)

1. **LightGBM: 0.5799** — Thang toan dien (RMSLE, MAE, MAPE tot nhat)
2. CatBoost: 0.6307
3. Random Forest: 0.6360 (chi dung 40K/85K subset)
4. XGBoost: 0.6385
5. Median: 0.8184 (baseline benchmark)
6. Mean: 0.8786
7. Random: 1.3126
8. LR Arch A: 1.7339
9. LR Arch B: 1.7549

### 12.2. Tai sao LR co R2 tot (52.9%) nhung RMSLE te (1.75)?

**Van de cot loi: LR predict gia am cho SP re → clip ve 0 → RMSLE phat nang.**

R2 va RMSLE do 2 thu khac nhau:
- **R2** do correlation tren thang tuyen tinh (VND). LR hieu text tot → du doan dung xu huong → R2 cao.
- **RMSLE** do sai so tuong doi tren thang log. Predict 0 cho SP gia 5,000 VND → log(1) - log(5001) = -8.5 → squared = 72.

VD minh hoa:
- SP gia 5,000 VND, LR predict -50,000 → clip 0 → RMSLE error = 8.5 (cuc lon)
- SP gia 500,000 VND, LR predict 450,000 → RMSLE error = 0.1 (nho)
- R2 chi quan tam "xu huong" (predict cao cho SP dat, thap cho SP re) → van tot
- RMSLE phat tung prediction sai → LR bi phat nang vi negative predictions

Tree-based models (RF, XGB, LGBM, CatBoost) KHONG predict am → RMSLE tot hon.

### 12.3. Tai sao LR R2 > XGBoost/CatBoost/RF R2?

| Model | R2 |
|-------|---:|
| LR Arch B | 52.9% |
| LightGBM | 52.0% |
| LR Arch A | 50.7% |
| XGBoost | 47.6% |
| CatBoost | 46.8% |
| RF (40K subset) | 41.1% |

**3 nguyen nhan:**
1. **Sample size nho (200 items):** R2 co variance cao. Chenh lech 5% giua LR va XGBoost co the la noise. Can chay size="all" (3,872 items) de kiem chung.
2. **LR extrapolate, trees khong:** LR predict tuyen tinh ra ngoai training range. Trees bi gioi han boi gia min/max trong training leaves. Voi SP co features cuc tri, LR co the predict sat hon.
3. **RF chi dung 40K subset:** Giai thich R2=41.1% thap nhat. XGBoost/CatBoost dung full 85K nhung van thap hon LR, co the do default hyperparameters chua toi uu cho TF-IDF sparse features.

### 12.4. Architecture A vs B

| | Arch A (raw n-gram) | Arch B (underthesea) |
|---|---|---|
| RMSLE | 1.7339 | 1.7549 |
| MAE | 123,860 | **121,230** |
| MAPE | 72.1% | **63.9%** |
| R2 | 50.7% | **52.9%** |

- Arch B cai thien MAE (-2.1%), MAPE (-11.4%), R2 (+4.3%) so voi A
- RMSLE tuong duong (ca 2 deu te vi negative predictions, khong phai do tokenization)
- **Ket luan:** Underthesea tokenization giup, tat ca ensemble models dung Arch B la hop ly

### 12.5. Nhan xet tong the

**Tot:**
- LightGBM RMSLE=0.58 — cai thien 29% so voi Median baseline (0.82)
- MAE=114K VND — trung binh sai 114K cho SP duoi 1M (sai ~38% so voi mean price)
- Filter <= 1M VND giup: phan phoi gan symmetric (skew 1.23 vs 6.85), models hoc tot hon

**Chua tot:**
- MAPE=59.7% — trung binh sai 60% gia, van cao
- R2=52% — chi giai thich 52% variance, 48% con lai la noise
- LR negative prediction van la van de (RMSLE=1.75 du R2 tot)

**Huong cai thien cho session tiep:**
1. Chay evaluate size="all" (3,872 items) de co ket qua stable hon
2. Log-transform target: `y = log1p(price)` → train → `expm1(pred)` — giai quyet LR negative va RMSLE truc tiep
3. Them category feature (one-hot) ket hop voi TF-IDF
4. Hyperparameter tuning cho LightGBM (best model)
5. Ridge/Lasso thay LR (regularization tranh overfit TF-IDF sparse)
6. Hybrid tokenization: Underthesea + char_wb n-gram (Arch C)

### Cau hinh chay

- May thue: AMD Ryzen 5 7500F (6C/12T), 28GB RAM, RTX 5060 Ti 16GB
- GPU: KHONG DUNG (XGBoost/CatBoost GPU treo voi sparse matrix 85K x 10K)
- CPU: n_jobs=6, Pool(4)
- Tokenize cache: `day3/tokenized_train_1m.pkl` + `day3/tokenized_test_1m.pkl`
- Thoi gian: RF ~27 phut, XGBoost ~3.5 phut, LightGBM ~42 giay, CatBoost ~2.6 phut

### Luu y ky thuat

- Underthesea KHONG thread-safe — phai pre-tokenize test set truoc khi evaluate
- XGBoost/CatBoost GPU treo voi sparse matrix — dung CPU (tree_method="hist")
- File pickle portable giua cac may cung Python 3.x va cung dataset
- Evaluate default 200 items. Size="all" cho full 3,872 items

### Files

- `pricer_vi/evaluator.py` — Evaluator (RMSLE, MAE, MAPE, R2, VND tick format)
- `day3_baseline_ml_1m.py` — Script chay tu dong (filtered <= 1M)
- `day3_baseline_ml_1m.ipynb` — Notebook tuong tac
- `day3/ketquaday3_v1.txt` — Output .py chay tren may thue
- `day3_baseline_ml.py` — Script cu (full dataset, da bo)
- `day3_baseline_ml_notebook.ipynb` — Notebook cu
- `day3_baseline_ml_notebook_5060ti.ipynb` — Notebook cu

---

## 13. Day 3 v3 — ML Optimization Plan

**Ngay:** 2026-04-14
**Muc tieu:** Toi uu RMSLE tu 0.5799 xuong 0.45-0.50 bang traditional ML truoc khi chuyen sang Deep Learning.
**Benchmark:** Kaggle Mercari top ML solutions ~0.43. Target: **RMSLE <= 0.50**

### 13.1. Nghien cuu va quyet dinh

**Tai sao log-transform la uu tien #1?**
RMSLE = RMSE tren log scale. Hien tai models train toi uu MSE tren raw VND, nhung evaluate bang RMSLE (log). Khi train tren `log1p(price)`, model truc tiep toi uu metric ma ta quan tam. Ngoai ra:
- LR het predict am (log-space luon duong sau expm1)
- Phan phoi log(price) gan normal → tat ca models hoc tot hon
- Ky vong: RMSLE giam 15-25%

**Tai sao them category feature?**
8 categories co price range rat khac nhau (Thoi Trang ~200K, Dien Tu ~500K). Hien tai model phai "doan" category tu text. Them category truc tiep giup model split chinh xac hon.

**Tai sao KHONG dung TruncatedSVD?**
Tree models (LightGBM, XGBoost) xu ly sparse matrix truc tiep — SVD lam mat thong tin ma khong cai thien. Chi can SVD khi dung neural network (Day 4).

### 13.2. 4 Phase thuc hien

#### Phase 1: Stable Baseline + Log Transform (~30 phut)

**Step 1:** Evaluate v2 models tren FULL test set (3,872 items thay vi 200)
- Tao stable baseline de so sanh cong bang
- Ky vong: ket qua thay doi ~5-10% so voi 200 items

**Step 2:** Log-transform target cho TAT CA models
```python
y_train = np.log1p(prices)              # train tren log scale
model.fit(X_train, y_train)
pred_log = model.predict(X_test)
pred_price = np.expm1(pred_log)          # convert lai VND
pred_price = np.clip(pred_price, 0, None)
```
- Chay lai: LR (Arch A + B), RF, XGBoost, LightGBM, CatBoost
- Evaluate: size="all" (3,872 items)
- **Ky vong: LightGBM RMSLE giam tu ~0.58 xuong ~0.48**
- **LR RMSLE giam tu ~1.75 xuong ~0.60-0.70 (khong con predict am)**

#### Phase 2: Feature Engineering (~1 tieng)

**Step 3:** Them category feature (one-hot)
```python
from scipy.sparse import hstack
from sklearn.preprocessing import OneHotEncoder

categories = [[item.category] for item in train]
cat_encoder = OneHotEncoder(sparse_output=True, handle_unknown='ignore')
X_cat_train = cat_encoder.fit_transform(categories)
X_combined = hstack([X_tfidf_train, X_cat_train])  # sparse
```
- 8 categories → 8 one-hot features + 10K TF-IDF = 10,008 features
- **Ky vong: RMSLE giam them 0.02-0.05**

**Step 4:** Architecture C — Hybrid tokenization (FeatureUnion)
```python
from sklearn.pipeline import FeatureUnion

arch_c = FeatureUnion([
    ('word', TfidfVectorizer(analyzer='word', ngram_range=(1, 2), max_features=5000)),
    ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=5000)),
])
X_train_c = arch_c.fit_transform(tokenized_train)  # 10K features
```
- char_wb bat duoc: brand names, model numbers, ky thuat (500ml, 128gb)
- So sanh voi Arch B de chon final
- **Ky vong: RMSLE giam them 0.01-0.03**

#### Phase 3: Model Tuning (~1-2 tieng)

**Step 5:** Ridge/Lasso thay Linear Regression
```python
from sklearn.linear_model import Ridge, Lasso
ridge_model = Ridge(alpha=1.0)  # L2 regularization
```
- Regularization tranh overfit voi 10K sparse features
- Grid search alpha: [0.01, 0.1, 1.0, 10, 100]

**Step 6:** LightGBM hyperparameter tuning (Optuna)
```python
import optuna

def objective(trial):
    params = {
        'num_leaves': trial.suggest_int('num_leaves', 50, 200),
        'min_child_samples': trial.suggest_int('min_child_samples', 50, 200),
        'feature_fraction': trial.suggest_float('feature_fraction', 0.3, 0.7),
        'lambda_l1': trial.suggest_float('lambda_l1', 0.01, 1.0, log=True),
        'learning_rate': trial.suggest_float('learning_rate', 0.03, 0.1, log=True),
        'n_estimators': 1500,
    }
    model = lgb.LGBMRegressor(**params, random_state=42, n_jobs=6, verbose=-1)
    model.fit(X_train, y_train, ...)
    pred = np.expm1(model.predict(X_val))
    return rmsle(val_prices, pred)

study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=50)  # ~1-2 tieng
```
- Dung validation set (3,926 items) de tune, evaluate tren test set
- **Ky vong: RMSLE giam them 0.03-0.07**

#### Phase 4: Ensemble + Final Evaluation (~30 phut)

**Step 7:** Weighted blending top 3 models
```python
from scipy.optimize import minimize

def blend_rmsle(weights, preds_list, y_true):
    blended = sum(w * p for w, p in zip(weights, preds_list))
    return rmsle(y_true, blended)

# Tim weights toi uu tren validation set
result = minimize(blend_rmsle, x0=[0.5, 0.25, 0.25], args=(val_preds, val_prices), ...)
```
- Blend: LightGBM + CatBoost + XGBoost (hoac RF)
- **Ky vong: RMSLE giam them 0.01-0.02**

**Step 8:** Final evaluation + tong hop
- Evaluate best single model + best blend tren full test set
- Bang so sanh v2 vs v3
- Charts: actual vs predicted cho best model
- Per-category evaluation (RMSLE per category)

### 13.3. Tieu chi thanh cong v3

- [ ] Full test evaluation (3,872 items) cho v2 baseline
- [ ] Log-transform cai thien RMSLE dang ke (target < 0.50)
- [ ] Category feature da them va co impact
- [ ] Arch C da so sanh voi Arch B
- [ ] LightGBM tuning hoan tat (Optuna >= 30 trials)
- [ ] Best RMSLE <= 0.50 (target)
- [ ] Bang tong hop v2 vs v3

### 13.4. Ky vong cai thien (cumulative)

| Improvement | RMSLE estimate | Giam |
|---|---|---|
| v2 baseline (200 items) | 0.5799 | — |
| + Full eval (3,872 items) | ~0.55-0.60 | stable |
| + Log-transform | ~0.45-0.50 | -15-25% |
| + Category feature | ~0.43-0.48 | -3-5% |
| + Arch C (char_wb) | ~0.42-0.47 | -1-3% |
| + LightGBM tuning | ~0.40-0.45 | -3-7% |
| + Blending | ~0.39-0.44 | -1-2% |
| **Target** | **<= 0.45** | |

### 13.5. Dependencies them

```bash
uv add optuna  # hyperparameter tuning
```

### 13.6. File structure v3

```
Data_processing_for_Vietnamese_data/
    day3_baseline_ml_1m_v3.py       # MOI — Script v3 (log-transform + features + tuning)
    day3_baseline_ml_1m_v3.ipynb    # MOI — Notebook v3
    day3/
        plan_day3.md                # File nay
        ketquaday3_v1.txt           # Ket qua v2
        ketquaday3_v3.txt           # MOI — Ket qua v3
        tokenized_train_1m.pkl      # Cache (tu v2)
        tokenized_test_1m.pkl       # Cache (tu v2)
```