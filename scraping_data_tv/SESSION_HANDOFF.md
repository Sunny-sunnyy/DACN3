# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-14)

**Trang thai:** Day 0-3 HOAN TAT. Day 3 v2 done (filtered <= 1M VND). Best model: LightGBM RMSLE=0.5799. Buoc tiep: **Day 3 v3 — ML optimization**.
**Branch:** `feature/data-preprocessing-vi`

### Da hoan thanh:
- [x] Tiki scraper — 111/113 categories, 102,117 SP
- [x] Kaggle CSV → JSONL — 41,603 SP (6 files thoi trang)
- [x] Hasaki scraper — 128/130 categories, 11,410 SP
- [x] WinMart scraper — 18 categories, 3,232 SP (API discovery + scraper)
- [x] Day 1 v1-v4: iterate pipeline, chot v4 config
- [x] HF dataset `SeanSunny/items_raw_tv_v4` da push (120K items raw)
- [x] **Day 2 HOAN TAT:** 120K items rewrite thanh cong (6h, $5)
  - LLM (gpt-oss-20b) tao Mo ta + Thong so, title/category/brand tu data goc
  - Dataset: `SeanSunny/items_tv_v6`
- [x] **Day 3 v2 HOAN TAT:** 9 baseline models, filtered <= 1M VND
  - Data: 85K train / 3.9K val / 3.9K test (tu 120K, filter <= 1M)
  - Best: **LightGBM RMSLE=0.5799**, MAE=114K, MAPE=59.7%, R2=52%
  - So sanh Arch A (n-gram) vs Arch B (underthesea): B tot hon (MAE, MAPE, R2)
  - LR paradox: R2=52.9% nhung RMSLE=1.75 (predict am → clip 0)
  - GPU treo voi sparse matrix → dung CPU cho tat ca models

### Dang lam / Buoc tiep:
- [ ] **Day 3 v3:** ML optimization — thuc nghiem them
  - Log-transform target: train tren log1p(price), giai quyet LR negative prediction
  - Evaluate size="all" (3,872 items) thay vi 200
  - Them category feature (one-hot + TF-IDF)
  - Hyperparameter tuning LightGBM
  - Ridge/Lasso thay LR
  - Hybrid tokenization Arch C (underthesea + char_wb n-gram)
- [ ] **Day 4:** DNN + Frontier LLM

### Quyet dinh da dua ra:
- Fine-tune: Qwen 3.5 4B (tot hon cho tieng Viet)
- Du lieu: Tiki 102K + Kaggle 42K + Hasaki 11K + WinMart 3.2K = 158K raw → 147K dedup → 120K sample
- Day 1 v4: TRAIN_SIZE=110K, total=120K (110K/5K/5K), HF=v4
- 8 categories (chot): Thoi Trang, Dien Tu Cong Nghe, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Lanh Gia Dung, O To Xe May
- Penalty: Thoi Trang 0.40, Nha Cua 0.60
- **Day 2:** LLM chi tao 2 truong (Mo ta + Thong so), title/category/brand lay tu data goc
- **Day 2:** Model: groq/openai/gpt-oss-20b, chi phi thuc te cho 120k san pham la 5$, thoi gian: 6h
- **Day 2:** Output dataset: SeanSunny/items_tv_v6
- **Day 3:** RMSLE lam primary metric (chuan Kaggle cho e-commerce price prediction)
- **Day 3:** Filter <= 1M VND (77.9% data). Ly do: phan phoi full dataset lech qua manh (skew=6.85)
- **Day 3:** So sanh Arch A (n-gram) vs B (underthesea): B tot hon, tat ca ensemble dung B
- **Day 3:** GPU treo voi sparse matrix → dung CPU cho tat ca models (XGBoost hist, CatBoost CPU)
- **Day 3:** Best model: LightGBM RMSLE=0.5799 (cai thien 29% so voi Median baseline)

### Ket qua du lieu:
- **Day 1 (v4):** 158K raw → 147K dedup → 120K sample (110K/5K/5K)
- **Day 2 (DONE):** 120K items, 0 missing, push `SeanSunny/items_tv_v6`
  - Summary: Tieu de/Danh muc/Thuong hieu (data goc) + Mo ta/Thong so (LLM)
  - Prompt: "San pham nay gia bao nhieu?\n\n[summary]\n\nGia: [price VND]"
- **Day 3 (DONE):** Best: LightGBM RMSLE=0.5799, MAE=114K, MAPE=59.7%, R2=52%
  - Filter: <= 1M VND → 85K train / 3.9K val / 3.9K test
  - Tokenization: Arch B (underthesea) tot hon Arch A (n-gram)

### Luu y ky thuat:
- Tiki API cap 2000 SP/category; dung Adaptive Price-Range Slicing de vuot
- WinMart API: `api-crownx.winmart.vn`, chi dung parent slugs
- **Day 3:** XGBoost/CatBoost GPU treo voi sparse matrix 85K x 10K → dung CPU
- **Day 3:** Underthesea KHONG thread-safe, phai pre-tokenize va luu cache .pkl
- **Day 3:** LR predict am cho SP re → clip 0 → RMSLE cuc cao (1.75) du R2 tot (52.9%)

### Moi truong chay:
- **May thue (ML/DL):** RTX 4060 Ti 16GB VRAM | i5-13400F 12C | 28GB RAM | CUDA 4352 (toi thieu)
  - Hoac RTX 5060 Ti 16GB | Ryzen 5 7500F 6C/12T | 28GB RAM
  - Thue 3-5 tieng/lan, co the thue nhieu lan. Moi lan co the may khac nhau.
- **May thue (Fine-tune QLoRA):** RTX 3090 24GB VRAM | i5-13400F 12C | 56GB RAM | CUDA 10496
  - Hoac GPU A100 tren Google Colab
- **Workflow:** git clone → uv sync → chay .py hoac .ipynb → copy ket qua ve
- Moi lan thue may moi: can `uv sync` lai va tokenize sẽ được tải từ gg drive về 

---

## Prompt dau tien cho session moi

### Prompt A: Day 3 v3 — ML Optimization (HIEN TAI)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md" — plan Day 3 + ket qua (Section 8, 12)
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/" — tat ca file .py
3. "scraping_data_tv/Data_processing_for_Vietnamese_data/day3/day3_baseline_ml_1m.py" — code Day 3 v2

Trang thai:
- Day 3 v2 HOAN TAT. Best: LightGBM RMSLE=0.5799, MAE=114K, R2=52%
- Dataset: SeanSunny/items_tv_v6, filtered <= 1M VND (85K train / 3.9K test)
- Tokenization: Arch B (underthesea) tot hon Arch A (n-gram)
- GPU treo voi sparse matrix → dung CPU

Buoc tiep — Day 3 v3 (thuc nghiem them):
1. Evaluate size="all" (3,872 items) thay vi 200 — ket qua stable hon
2. Log-transform target: train tren log1p(price), predict, expm1 — giai quyet LR negative
3. Them category feature (one-hot) ket hop voi TF-IDF
4. Hyperparameter tuning cho LightGBM (best model)
5. Ridge/Lasso thay Linear Regression
6. Hybrid tokenization Arch C: underthesea + char_wb n-gram (FeatureUnion)
7. Tong hop ket qua v3 + so sanh voi v2

Luu y:
- Luon dung uv (uv run, uv add)
- Tao file .py (tu chay) va .ipynb (tuong tac) — KHONG cap nhat .ipynb cu (loi IDE)
- Cap nhat SESSION_HANDOFF.md moi khi ket thuc session
```

### Prompt B: Day 4 — DNN + Frontier LLM (SAU KHI DAY 3 v3 XONG)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan tong the
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/" — tat ca file .py (bao gom evaluator.py tu Day 3)
3. "scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/pricer/deep_neural_network.py" — code DNN tieng Anh (tham khao)
4. "scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md" — ket qua Day 3

Buoc tiep — Day 4: DNN + Frontier LLM
Tham khao: Code_Data_processing/day4.ipynb va Code_Data_processing/redemption_train.ipynb
Luon dung uv de chay code.
```

### Khi nao can doc them:
- **Tien xu ly du lieu**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md`
- **Ke hoach du an**: doc `segment4/mo_ta_du_an/Project_Development_Plan.md`
- **Ket qua Day 1**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md`
- **Ket qua Day 2**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/day2/2026-04-12-day2-llm-preprocessing-vi.md`

---

## Files quan trong

| File | Muc dich |
|------|----------|
| **DATA PROCESSING** | |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md` | Plan Day 0-4 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md` | Plan chi tiet Day 3 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/` | Package chinh (items, parser, preprocessor, batch) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day3_baseline_ml_1m.py` | Day 3 script (filtered <= 1M) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day3_baseline_ml_1m.ipynb` | Day 3 notebook (filtered <= 1M) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/ketquaday3_v1.txt` | Day 3 output ket qua |
| **ENGLISH REFERENCE** | |
| `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/pricer/evaluator.py` | Evaluator (Plotly, tham khao cho Day 3) |
| `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/pricer/deep_neural_network.py` | DNN (tham khao cho Day 4) |
| `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/day3.ipynb` | Day 3 notebook tieng Anh |
| **E-COMMERCE SCRAPERS** | |
| `scraping_data_tv/Tiki/tiki_scraper/scraper.py` | Tiki scraper |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py` | Hasaki scraper |
| **PROJECT** | |
| `segment4/mo_ta_du_an/Project_Development_Plan.md` | Ke hoach tong the |
| `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md` | Doc search_key.py |

---

## Lenh chay nhanh

```bash
cd tech2ai

# Chay Day 3 script (filtered <= 1M VND)
cd scraping_data_tv/Data_processing_for_Vietnamese_data && uv run day3_baseline_ml_1m.py

# Hoac mo notebook
# Mo day3_baseline_ml_1m.ipynb trong IDE
```

---


*Cap nhat: 2026-04-14 — Day 0-3 HOAN TAT. Best: LightGBM RMSLE=0.5799. Dataset SeanSunny/items_tv_v6 filtered <= 1M VND. Plan: day3/plan_day3.md.*
