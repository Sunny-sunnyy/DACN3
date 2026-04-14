# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-13)

**Trang thai:** Day 0-2 HOAN TAT. Day 3 SAN SANG THUC HIEN. Dataset final `SeanSunny/items_tv_v4` da push (120K items co summary + prompt). Buoc tiep: **Day 3 Baseline ML**.
**Branch:** `feature/data-preprocessing-vi`

### Da hoan thanh:
- [x] Tiki scraper — 111/113 categories, 102,117 SP
- [x] Kaggle CSV → JSONL — 41,603 SP (6 files thoi trang)
- [x] Hasaki scraper — 128/130 categories, 11,410 SP
- [x] WinMart scraper — 18 categories, 3,232 SP (API discovery + scraper)
- [x] Day 1 v1-v4: iterate pipeline, chot v4 config
- [x] HF dataset `SeanSunny/items_raw_tv_v4` da push (120K items raw)
- [x] **Day 2 HOAN TAT:** 120K items rewrite thanh cong (mất khoảng 6 tiếng để chạy và hết 5$ cho 120k sản phẩm)
  - LLM (gpt-oss-20b) tao Mo ta + Thong so, title/category/brand tu data goc 
  - 120 batches, resubmit 44 failed (spend limit) + fix 3 partial
  - Missing summaries: 0, push thanh cong `SeanSunny/items_tv_v4`

### Dang lam / Buoc tiep:
- [ ] **Day 3:** Baseline ML — Plan chi tiet tai `day3/plan_day3.md`
  - Models: Random, Mean, Median, LR, RF, XGBoost, LightGBM, CatBoost
  - Metrics: RMSLE (primary), MAE (VND), MAPE (%), R2
  - Tokenization: So sanh Kien truc A (TF-IDF + n-gram) vs B (underthesea pre-tokenize)
- [ ] **Day 4:** DNN + Frontier LLM

### Quyet dinh da dua ra:
- Fine-tune: Qwen 3.5 4B (tot hon cho tieng Viet)
- Du lieu: Tiki 102K + Kaggle 42K + Hasaki 11K + WinMart 3.2K = 158K raw → 147K dedup → 120K sample
- Day 1 v4: TRAIN_SIZE=110K, total=120K (110K/5K/5K), HF=v4
- 8 categories (chot): Thoi Trang, Dien Tu Cong Nghe, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Lanh Gia Dung, O To Xe May
- Penalty: Thoi Trang 0.40, Nha Cua 0.60
- **Day 2:** LLM chi tao 2 truong (Mo ta + Thong so), title/category/brand lay tu data goc
- **Day 2:** Model: groq/openai/gpt-oss-20b, chi phi thuc te cho 120k san pham la 5$, thời gian chạy: 6h
- **Day 2:** SYSTEM_PROMPT 2 truong + build_summary() ghep 5 truong
- **Day 2:** Column names giu tieng Anh (title, category, price, summary, prompt)
- **Day 2:** Brand rong → "Khong ro" trong summary
- **Day 2:** Output dataset: SeanSunny/items_tv_v4 (bo `_raw` vi da qua preprocessing)
- **Day 3:** RMSLE lam primary metric (chuan Kaggle cho e-commerce price prediction)
- **Day 3:** So sanh 2 kien truc tokenization: A (TF-IDF + n-gram) vs B (underthesea pre-tokenize)
- **Day 3:** SKU codes trong titles (28% items) — de nguyen, review lai neu ket qua khong tot

### Ket qua du lieu:
- **Day 1 (v4):** 158K raw → 147K dedup → 120K sample (110K/5K/5K)
- **Day 2 (DONE):** 120K items, 0 missing, push `SeanSunny/items_tv_v4`
  - Summary: Tieu de/Danh muc/Thuong hieu (data goc) + Mo ta/Thong so (LLM)
  - Prompt: "San pham nay gia bao nhieu?\n\n[summary]\n\nGia: [price VND]"
  - Schema final: title, category, price, summary, prompt (full/brand/id = null)

### Luu y ky thuat:
- Tiki API cap 2000 SP/category; dung Adaptive Price-Range Slicing de vuot
- WinMart API: `api-crownx.winmart.vn`, chi dung parent slugs
- **Day 2:** Groq spend limit gay fail 44 batches + 3 partial → resubmit thanh cong
- **Day 2:** Batch.save() ngay sau Batch.run() de khong mat batch_ids
- **Day 3 data note:** 28% titles co SKU codes (TEBAT870, BR6221A...). Da test LLM v3 (3 truong) — LLM phan biet tot specs (giu 1500W, SPF50) vs noise (bo TEBAT870). Neu can clean: re-run Day 2 voi v3 SYSTEM_PROMPT (~$1). Chi tiet: day3/plan_day3.md Section 9.

---

## Prompt dau tien cho session moi

### Prompt A: Day 3 — Baseline ML (HIEN TAI)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md" — plan chi tiet Day 3
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/" — tat ca file .py
3. "scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/" — code tieng Anh (tham khao)

Trang thai:
- Day 0-2 HOAN TAT. Day 3 SAN SANG THUC HIEN.
- Dataset final: SeanSunny/items_tv_v4 (120K items co summary + prompt)
- Summary format: Tieu de/Danh muc/Thuong hieu (data goc) + Mo ta/Thong so (LLM)
- Prompt format: "San pham nay gia bao nhieu?\n\n[summary]\n\nGia: [price VND]"
- 8 categories, 110K train / 5K val / 5K test

Buoc tiep — Day 3:
1. Tao evaluator.py (RMSLE primary, MAE, MAPE, R2, Plotly charts). Tham khao: Code_Data_processing/pricer/evaluator.py
2. Baseline models: Random, Mean, Median
3. Linear Regression + TF-IDF (Kien truc A: ngram_range=(1,2))
4. Underthesea pre-tokenize (Kien truc B) — so sanh voi A
5. Ensemble: Random Forest, XGBoost, LightGBM, CatBoost
6. Tong hop ket qua + charts

Luu y:
- Luon dung uv de chay code (uv run, uv add)
- 28% titles co SKU codes — de nguyen, review sau neu ket qua khong tot (xem Section 9 trong plan_day3.md)
- Tao ca file .py (tu chay) va .ipynb (tuong tac)
- Cap nhat SESSION_HANDOFF.md moi khi ket thuc session

Hay hoi toi nhung cau hoi can thiet truoc khi bat dau implement.
```

### Prompt B: Day 4 — DNN + Frontier LLM (SAU KHI DAY 3 XONG)

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
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py` | Day 1 pipeline (v4 config) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.ipynb` | Day 1 notebook (interactive) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day2_llm_preprocessing_v2.ipynb` | Day 2 notebook chinh (v2) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day2_llm_preprocessing_v4.ipynb` | Day 2 notebook chinh (v4) |
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

# Chay Day 3 script
cd scraping_data_tv/Data_processing_for_Vietnamese_data && uv run day3_baseline_ml.py

# Hoac mo notebook
# Mo day3_baseline_ml.ipynb trong IDE
```

---


*Cap nhat: 2026-04-13 — Day 0-2 HOAN TAT. Day 3 san sang thuc hien. Dataset SeanSunny/items_tv_v4 (120K items). Plan: day3/plan_day3.md.*



# Cập nhật 20h ngày 13/4/2026: Đã chạy lại toàn bộ data, kết quả đã xoá SKU codes, giữ lại các thông số kỹ thuật có giá trị, xem kết quả ở file day2_llm_preprocessing_v4.ipynb

# Hãy sử dụng bổ dữ liệu Dataset SeanSunny/items_tv_v6 
