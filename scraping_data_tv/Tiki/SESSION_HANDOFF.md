# Session Handoff — Tiki Scraper

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-11 17:00)

**Trang thai:** Day 1 DA XONG (v3, 110K SP, 100K/5K/5K split, push HF Hub). Dang lam Day 0 tiep — cao FMCG bo sung "Bach Hoa". WinMart API DA TIM DUOC — san sang viet scraper.
**Branch:** `feature/data-preprocessing-vi`

### Da hoan thanh:
- [x] Step 1-5: Tiki scraper DONE — 49/49 categories, 79,382 SP
- [x] Kaggle CSV → JSONL — 41,603 SP (6 files thoi trang)
- [x] Hasaki scraper DONE — 128/130 categories, 11,410 SP
- [x] E-commerce plan (10 trang TMDT, 4 phases)
- [x] Day 1 pipeline v3: merge Hasaki → dedup/clean → 154K raw → 110K sample (100K/5K/5K)
  - HF dataset: `SeanSunny/items_raw_tv_v3`
  - 8 categories, penalties: Thoi Trang 0.40, Nha Cua 0.60
- [x] Bach Hoa scraping plan tao + nghien cuu ky thuat 4 trang FMCG
- [x] FujiMart: BO — khong co gia (hien thi "Lien he" tren tat ca SP)
- [x] WinMart API discovery THANH CONG (DevTools Network tab)
  - Endpoint: `api-crownx.winmart.vn/it/api/web/v3/item/category?slug={slug}&pageNumber={n}&pageSize={n}`
  - No auth (Bearer token rong), header `x-api-merchant: WCM` bat buoc
  - Data rat tot: name, price, brandName, shortDescription, longDescription, mch1-mch5
  - **LUU Y: API bi timeout tu server ngoai VN — can chay tu may local (mang VN)**

### Dang lam:
- [ ] **Day 0 tiep:** Viet WinMart scraper + API discovery cho BachHoaXanh / CoopMart
  - WinMart: API da co, can liet ke category slugs roi viet scraper
  - BachHoaXanh: JS-rendered, can API discovery tuong tu WinMart (DevTools)
  - CoopMart: SPA React, chua khao sat
- [ ] **Day 2:** LLM rewrite (Groq Batch API)
- [ ] **Day 3:** Baseline ML (XGBoost, LightGBM, CatBoost)
- [ ] **Day 4:** DNN + Frontier LLM

### Quyet dinh da dua ra:
- Fine-tune: Qwen 3.5 4B (tot hon cho tieng Viet)
- Du lieu hien co: Tiki 79K + Kaggle 42K + Hasaki 11K = 132K SP raw → 110K curated
- 8 categories (chot): Thoi Trang, Dien Tu, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Gia Dung, The Thao
- FujiMart bo (khong co gia), uu tien BachHoaXanh > CoopMart > WinMart
- Features FMCG ngan (~50-200 chars) — chap nhan, Day 2 LLM rewrite se bo sung

### Ket qua du lieu (2026-04-11):
- **Tiki:** 49/49 categories — 79,382 SP
- **Kaggle:** 6 JSONL — 41,603 SP
- **Hasaki:** 128/130 categories — 11,410 SP
- **Tong raw:** 132,395 SP → curated 110K (v3)
- **Bach Hoa hien tai:** 4,284 SP trong sample → can bo sung 3-6K tu FMCG

### Luu y ky thuat:
- Tiki API cap 2000 SP/category; dung Adaptive Price-Range Slicing de vuot
- BachHoaXanh HTML goc khong co SP data (JS-rendered, ~87K chars HTML shell)
- WinMart API: `api-crownx.winmart.vn`, dung slug (khong phai mch codes), storeCode=1535
- WinMart API bi timeout tu WSL/cloud — **chi chay duoc tu mang VN**
- WinMart /item/related endpoint hoat dong tu server (PageSize=40, 25 SP)
- Browser subagent bi loi ECONNREFUSED (khong dung duoc trong session hien tai)

---

## Prompt dau tien cho session moi

### Prompt A: Viet WinMart scraper + API discovery BachHoaXanh/CoopMart (HIEN TAI)

```
Doc cac file sau de nap ngu canh:
0. "segment4/mo_ta_du_an/Project_Development_Plan.md" — Ke hoach tong the du an
1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai tong the
2. "scraping_data_tv/e-commerce-sites-scraping/scrap/bachhoa_scrap_plan.md" — plan + API details FMCG
3. "scraping_data_tv/e-commerce-sites-scraping/scrap/bachhoa_categories_report.md" — bao cao FMCG (WinMart API da tim)
4. "scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py" — reference scraper pattern
5. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan tien xu ly

WinMart API DA TIM DUOC:
- Endpoint: api-crownx.winmart.vn/it/api/web/v3/item/category?slug={slug}&pageNumber={n}&pageSize={n}&storeCode=1535&storeGroupCode=1998
- Headers: authorization=Bearer (rong), x-api-merchant=WCM, origin=https://winmart.vn
- Data: name, price, brandName, shortDescription, longDescription, mch1-mch5, categoryName
- LUU Y: API bi timeout tu server ngoai VN — can chay tu may local (mang VN)
- Category slugs da biet: rau-cu-trai-cay--c02 (149 SP), mi-thuc-pham-an-lien--c34

Buoc tiep:
1. Liet ke tat ca category slugs WinMart (toi se dung DevTools)
2. Viet winmart_scraper.py theo pattern hasaki_scraper.py
3. API discovery cho BachHoaXanh va CoopMart (tuong tu WinMart — DevTools Network tab)

Luon dung uv de chay code.
Sau do cho toi biet ban da nam duoc gi va buoc tiep theo la gi.
```

### Prompt B: Day 2-4 — LLM rewrite + Training (sau khi Day 0-1 xong)

```
Doc cac file sau de nap ngu canh:
0. "segment4/mo_ta_du_an/Project_Development_Plan.md" — Ke hoach tong the du an
1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai tong the
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan chi tiet Day 2-4
3. "scraping_data_tv/Data_processing_for_Vietnamese_data" — code hien tai
4. "scraping_data_tv/Data_processing_for_English_data" — code va tai lieu tieng Anh (tham khao)
5. "scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md" — ket qua Day 1

Day 0-1 done. 110K SP curated (v3). Buoc tiep: Day 2 LLM rewrite (Groq Batch API), Day 3 ML baseline, Day 4 DNN.
Hay hoi toi nhung cau hoi can thiet.
```

### Khi nao can doc them:
- **Scraper e-commerce moi**: doc `scraping_data_tv/e-commerce-sites-scraping/scrap/e-commerce-plan.md` + `hasaki_scraper.py`
- **Tien xu ly du lieu**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md`
- **Ke hoach du an**: doc `segment4/mo_ta_du_an/Project_Development_Plan.md`

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
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py` | Day 1 pipeline |
| `segment4/mo_ta_du_an/Project_Development_Plan.md` | Ke hoach tong the |

---

## Lenh chay nhanh

```bash
cd tech2ai

# Dem tong SP da cao
uv run python -c "from pathlib import Path; files=list(Path('scraping_data_tv/Tiki/Tiki_dataset_scrape').glob('*.jsonl')); total=sum(sum(1 for _ in open(f,encoding='utf-8')) for f in files); print(f'Tong: {total:,} SP tu {len(files)} files')"

# Re-run Day 1 pipeline
cd scraping_data_tv/Data_processing_for_Vietnamese_data && uv run day1_data_curation.py
```

---

*Cap nhat: 2026-04-11 17:00 — Day 1 DONE (v3, 110K). WinMart API DA TIM. FujiMart BO. Can API discovery cho BachHoaXanh/CoopMart.*
