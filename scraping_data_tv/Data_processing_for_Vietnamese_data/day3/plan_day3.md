# Day 3: Baseline ML — Plan chi tiet

**Ngay:** 2026-04-12
**Cap nhat:** 2026-04-13
**Trang thai:** SAN SANG THUC HIEN
**Branch:** `feature/data-preprocessing-vi`
**Input:** `SeanSunny/items_tv_v6` (120K items: 110K train / 5K val / 5K test)

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
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
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
vectorizer = TfidfVectorizer(max_features=5000)
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
HF Hub (items_tv_v4)
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
- TfidfVectorizer voi ngram_range=(1,2), max_features=5000
- Linear Regression tren TF-IDF features
- Evaluate

**Tieu chi:** MAE giam dang ke so voi Mean/Median.

### Step 5: Them Underthesea tokenization (Kien truc B)
- Pre-tokenize summaries (multiprocessing, 4 workers)
- TfidfVectorizer tren tokenized text
- So sanh voi Kien truc A

**Tieu chi:** Co ket qua so sanh A vs B.

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
| **Vectorizer** | CountVectorizer(max_features=2000) | TfidfVectorizer(max_features=5000) |
| **Models** | Random, Mean, LR, RF, XGBoost | + Median, LightGBM, CatBoost |
| **Evaluate size** | 200 (co dinh) | 200 default + option full (5K) |
| **Metrics** | MAE ($), MSE, R2 | **RMSLE (primary)**, MAE (VND), MAPE (%), R2 |
| **Dataset** | 800K train / 10K test | 110K train / 5K test |

---

## 7. Tieu chi thanh cong Day 3

- [ ] `evaluator.py` hoat dong: evaluate mo hinh bat ky, in metrics + ve charts
- [ ] 3 baselines (Random, Mean, Median) chay va co ket qua
- [ ] Linear Regression + TF-IDF chay, MAE giam so voi baselines
- [ ] So sanh Kien truc A vs C (co/khong underthesea)
- [ ] XGBoost, LightGBM, CatBoost chay thanh cong
- [ ] Bang tong hop ket qua tat ca models
- [ ] File `.py` tu chay va in ket qua
- [ ] File `.ipynb` san sang cho user chay
- [ ] Cap nhat `SESSION_HANDOFF.md` va `plan_data_preprocessing_vi.md`

---

## 8. Ket qua kiem chung

(Se cap nhat sau moi step)

| Step | Trang thai | Ket qua | Ghi chu |
|---|---|---|---|
| 1. Dependencies | | | | ( đã cài đặt )
| 2. Evaluator | | | |
| 3. Baselines | | | |
| 4. LR + TF-IDF (A) | | | |
| 5. Underthesea (B) | | | |
| 6. Ensemble models | | | |
| 7. Tong hop | | | |
| 8. Notebook | | | |

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

*Tao: 2026-04-12. Cap nhat: 2026-04-13. Buoc tiep: Step 1 cai dependencies.*

# Cập nhật 20h ngày 13/4/2026: Đã chạy lại toàn bộ data, kết quả đã xoá SKU codes, giữ lại các thông số kỹ thuật có giá trị, xem kết quả ở file day2_llm_preprocessing_v4.ipynb

# Sử dụng bộ dữ liệu: SeanSunny/items_tv_v6