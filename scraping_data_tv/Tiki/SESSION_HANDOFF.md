# Session Handoff — Tiki Scraper

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-11 21:30)

**Trang thai:** Day 0-1 HOAN TAT. Day 1 v4 config san sang (TRAIN_SIZE=110K, HF=v4). Notebook `day1_data_curation.ipynb` da tao. Can chay notebook de push HF Hub. Buoc tiep: **Day 2 LLM rewrite**.
**Branch:** `feature/data-preprocessing-vi`

### Da hoan thanh:
- [x] Tiki scraper — 111/113 categories, 102,117 SP
- [x] Kaggle CSV → JSONL — 41,603 SP (6 files thoi trang)
- [x] Hasaki scraper — 128/130 categories, 11,410 SP
- [x] WinMart scraper — 18 categories, 3,232 SP (API discovery + scraper)
- [x] Day 1 v1-v3: iterate pipeline (v1: 110K, v2: 90K, v3: 110K)
- [x] **Day 1 v4 config DONE:** TRAIN_SIZE=110K, total=120K (110K/5K/5K)
  - HF dataset: `SeanSunny/items_raw_tv_v4`
  - 8 categories, penalties: Thoi Trang 0.40, Nha Cua 0.60
  - 158K raw → 147K dedup → 120K sample
  - Bach Hoa tang tu 4,284 (v3) → 8,137 raw (v4)
- [x] Notebook `day1_data_curation.ipynb` da tao
- [x] Quyet dinh: KHONG can cao them data

### Dang lam / Buoc tiep:
- [ ] **Chay notebook Day 1 v4** → push HF Hub `SeanSunny/items_raw_tv_v4`
- [ ] **Day 2:** LLM rewrite (Groq Batch API)
- [ ] **Day 3:** Baseline ML (XGBoost, LightGBM, CatBoost)
- [ ] **Day 4:** DNN + Frontier LLM

### Quyet dinh da dua ra:
- Fine-tune: Qwen 3.5 4B (tot hon cho tieng Viet)
- Du lieu: Tiki 102K + Kaggle 42K + Hasaki 11K + WinMart 3.2K = 158K raw → 147K dedup → 120K sample
- Day 1 v4: TRAIN_SIZE=110K, total=120K (110K/5K/5K), HF=v4
- 8 categories (chot): Thoi Trang, Dien Tu Cong Nghe, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Lanh Gia Dung, O To Xe May
- Penalty: Thoi Trang 0.40, Nha Cua 0.60 (khong them Bach Hoa boost — phan bo 5% chap nhan)
- Khong can cao them data — du cho Day 2+ (BachHoaXanh/CoopMart tam dung)
- Phan bo category sau sampling gan voi thuc te TMDT VN (da phan tich va chap nhan)

### Ket qua du lieu (v4, 2026-04-11):
- **Tiki Scraper:** 111 categories — 102,117 SP
- **Kaggle:** 6 JSONL — 41,603 SP
- **Hasaki:** 128 categories — 11,410 SP
- **WinMart:** 18 categories — 3,232 SP
- **Tong raw:** 158,362 SP (263 JSONL files)
- **Sau dedup:** ~146,850 SP
- **Sau sampling:** 120,000 SP (110K train / 5K val / 5K test)

### Luu y ky thuat:
- Tiki API cap 2000 SP/category; dung Adaptive Price-Range Slicing de vuot
- BachHoaXanh HTML goc khong co SP data (JS-rendered, ~87K chars HTML shell)
- WinMart API: `api-crownx.winmart.vn`, chi dung parent slugs (leaf bi rong do storeCode)
- WinMart API: totalCount luon tra 0 — pagination bang fetch-until-empty
- WinMart API: pageSize=100 OK, khong can auth, API nhe (~50 SP/s)
- WinMart API: DA CHAY THANH CONG tu WSL (khong bi timeout)
- WinMart: mch1 categories la "Thuc pham" va "Phi thuc pham" — KHAC Tiki naming
- day1_data_curation.py: DA FIX CATEGORY_MAP (them 2 keys moi cho WinMart)

---

## Prompt dau tien cho session moi

### Prompt A: Day 2 — LLM rewrite (HIEN TAI)

```
Doc cac file sau de nap ngu canh:
0. "segment4/mo_ta_du_an/Project_Development_Plan.md" — Ke hoach tong the du an
1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai tong the
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan chi tiet Day 0-4
3. "scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py" — Day 1 pipeline (v4 config)
4. "scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md" — ket qua Day 1 (EDA, phan tich v1-v4)
5. "scraping_data_tv/Data_processing_for_English_data" — code va tai lieu tieng Anh (tham khao)

Trang thai:
- Day 0-1 HOAN TAT. 158K raw → 147K dedup → 120K sample (110K/5K/5K)
- HF dataset: SeanSunny/items_raw_tv_v4 (can chay notebook push truoc)
- 8 categories, penalties: Thoi Trang 0.40, Nha Cua 0.60
- KHONG can cao them data

Buoc tiep:
1. (Neu chua push) Chay day1_data_curation.ipynb de push HF Hub v4
2. Day 2: LLM rewrite (Groq Batch API) — viet lai descriptions thanh format chuan
3. Day 3: Baseline ML, Day 4: DNN + Frontier LLM

Luon dung uv de chay code.
Hay hoi toi nhung cau hoi can thiet truoc khi bat dau.
```

### Prompt B: Day 3-4 — ML + DNN (sau khi Day 2 xong)

```
Doc cac file sau de nap ngu canh:
0. "segment4/mo_ta_du_an/Project_Development_Plan.md" — Ke hoach tong the du an
1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai tong the
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan chi tiet Day 3-4
3. "scraping_data_tv/Data_processing_for_Vietnamese_data" — code hien tai (pricer_vi/, day1, day2)
4. "scraping_data_tv/Data_processing_for_English_data" — code va tai lieu tieng Anh (tham khao)

Day 0-2 done. Dataset da co summary tu LLM rewrite.
Buoc tiep: Day 3 Baseline ML (XGBoost, LightGBM, CatBoost), Day 4 DNN + Frontier LLM.
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

*Cap nhat: 2026-04-11 21:30 — Day 0-1 HOAN TAT. Day 1 v4 config (110K train, 120K total, HF=v4). Notebook da tao. Buoc tiep: Day 2 LLM rewrite.*
