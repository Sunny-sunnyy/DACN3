# Session Handoff — Tiki Scraper

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-12 15:00)

**Trang thai:** Day 0-2 HOAN TAT. Dataset final `SeanSunny/items_tv_v4` da push (120K items co summary + prompt). Buoc tiep: **Day 3 Baseline ML**.
**Branch:** `feature/data-preprocessing-vi`

### Da hoan thanh:
- [x] Tiki scraper — 111/113 categories, 102,117 SP
- [x] Kaggle CSV → JSONL — 41,603 SP (6 files thoi trang)
- [x] Hasaki scraper — 128/130 categories, 11,410 SP
- [x] WinMart scraper — 18 categories, 3,232 SP (API discovery + scraper)
- [x] Day 1 v1-v4: iterate pipeline, chot v4 config
- [x] HF dataset `SeanSunny/items_raw_tv_v4` da push (120K items raw)
- [x] **Day 2 HOAN TAT:** 120K items rewrite thanh cong
  - LLM (gpt-oss-20b) tao Mo ta + Thong so, title/category/brand tu data goc
  - 120 batches, resubmit 44 failed (spend limit) + fix 3 partial
  - Missing summaries: 0, push thanh cong `SeanSunny/items_tv_v4`

### Dang lam / Buoc tiep:
- [ ] **Day 3:** Baseline ML (Random, Mean, Median, LinearRegression, XGBoost, LightGBM, CatBoost)
- [ ] **Day 4:** DNN + Frontier LLM

### Quyet dinh da dua ra:
- Fine-tune: Qwen 3.5 4B (tot hon cho tieng Viet)
- Du lieu: Tiki 102K + Kaggle 42K + Hasaki 11K + WinMart 3.2K = 158K raw → 147K dedup → 120K sample
- Day 1 v4: TRAIN_SIZE=110K, total=120K (110K/5K/5K), HF=v4
- 8 categories (chot): Thoi Trang, Dien Tu Cong Nghe, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Lanh Gia Dung, O To Xe May
- Penalty: Thoi Trang 0.40, Nha Cua 0.60
- **Day 2:** LLM chi tao 2 truong (Mo ta + Thong so), title/category/brand lay tu data goc
- **Day 2:** Model: groq/openai/gpt-oss-20b, chi phi uoc tinh ~$9-10
- **Day 2:** SYSTEM_PROMPT 2 truong + build_summary() ghep 5 truong
- **Day 2:** Column names giu tieng Anh (title, category, price, summary, prompt)
- **Day 2:** Brand rong → "Khong ro" trong summary
- **Day 2:** Output dataset: SeanSunny/items_tv_v4 (bo `_raw` vi da qua preprocessing)

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

---

## Prompt dau tien cho session moi

### Prompt A: Day 3-4 — ML + DNN (HIEN TAI)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai tong the
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan chi tiet Day 3-4
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/" — tat ca file .py
3. "scraping_data_tv/Data_processing_for_Vietnamese_data/day2/2026-04-12-day2-llm-preprocessing-vi.md" — ket qua Day 2
4. "scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/" — code tieng Anh Day 3-4 (tham khao)

Trang thai:
- Day 0-2 HOAN TAT.
- Dataset final: SeanSunny/items_tv_v4 (120K items co summary + prompt)
- Summary format: Tieu de/Danh muc/Thuong hieu (data goc) + Mo ta/Thong so (LLM)
- Prompt format: "San pham nay gia bao nhieu?\n\n[summary]\n\nGia: [price VND]"
- 8 categories, 110K train / 5K val / 5K test

Buoc tiep:
1. Day 3: Baseline ML (Random, Mean, Median, Linear Regression, XGBoost, LightGBM, CatBoost)
2. Day 4: DNN + Frontier LLM
Metrics: MAE (VND), MAPE (%), MSE, R2

Luon dung uv de chay code.
Hay hoi toi nhung cau hoi can thiet.
```

### Khi nao can doc them:
- **Tien xu ly du lieu**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md`
- **Ke hoach du an**: doc `segment4/mo_ta_du_an/Project_Development_Plan.md`
- **Ket qua Day 1**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md`

---

## Files quan trong

| File | Muc dich |
|------|----------|
| **E-COMMERCE SCRAPERS** | |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/e-commerce-plan.md` | Plan cao 10 trang TMDT |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/bachhoa_scrap_plan.md` | Plan FMCG + ket qua nghien cuu |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py` | Hasaki scraper (DONE, reference) |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_categories_report.md` | Bao cao 130 categories Hasaki (DONE) |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/data/` | Output JSONL files |
| **TIKI** | |
| `scraping_data_tv/Tiki/tiki_categories_report.md` | Bao cao Tiki (DONE) |
| `scraping_data_tv/Tiki/tiki_scraper/scraper.py` | Tiki scraper |
| **DATA PROCESSING** | |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md` | Plan Day 0-4 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py` | Day 1 pipeline (v4 config) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.ipynb` | Day 1 notebook (interactive) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md` | Day 1 log + EDA analysis (v1-v4) |
| **DAY 2** | |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/preprocessor.py` | SYSTEM_PROMPT (2 truong) + build_summary() |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/batch.py` | Batch class (Groq Batch API) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day2_llm_preprocessing_v2.ipynb` | Day 2 notebook chinh (v2) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day2_llm_preprocessing.py` | Day 2 test script (items 21-30) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day2/2026-04-12-day2-llm-preprocessing-vi.md` | Day 2 huong dan chi tiet |
| `segment4/mo_ta_du_an/Project_Development_Plan.md` | Ke hoach tong the |

---

## Lenh chay nhanh

```bash
cd tech2ai

# Dem tong SP da cao
uv run python -c "from pathlib import Path; files=list(Path('scraping_data_tv/Tiki/Tiki_dataset_scrape').glob('*.jsonl')); total=sum(sum(1 for _ in open(f,encoding='utf-8')) for f in files); print(f'Tong: {total:,} SP tu {len(files)} files')"

# Chay Day 1 pipeline (script)
cd scraping_data_tv/Data_processing_for_Vietnamese_data && uv run day1_data_curation.py

# Hoac mo notebook (khuyen nghi — de xem EDA tung buoc)
# Mo day1_data_curation.ipynb trong IDE
```

---

*Cap nhat: 2026-04-12 15:00 — Day 0-2 HOAN TAT. Dataset SeanSunny/items_tv_v4 da push (120K items). Buoc tiep: Day 3 Baseline ML.*
