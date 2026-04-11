# Session Handoff — Tiki Scraper

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-11)

**Trang thai:** Day 0 dang tien hanh — Hasaki DONE (11,410 SP). Can cao tiep Cocolux + merge vao pipeline. Day 1 da chay 1 lan (110K SP, push HF Hub) nhung can re-run sau khi co data moi tu e-commerce sites.
**Branch:** `feature/data-preprocessing-vi`

### Da hoan thanh:
- [x] Step 1: Test Tiki API v2 — thanh cong, khong bi anti-bot
- [x] Step 2: Scan 122 sub-categories (~585K SP kha dung)
- [x] Step 3: Build scraper (models + config + scraper + CLI)
- [x] Step 4: Test full category Smartphone (103 SP) — OK
- [x] Concurrent workers (ThreadPoolExecutor): 3 workers = 2.7 SP/s (tang 3.4x)
- [x] Resume/checkpoint: test OK (30 SP -> dung -> tiep 73 SP = 103 SP)
- [x] Step 4b: Re-scan categories (2026-04-07) — xac nhan 15 parent, 122 sub, ~585K SP
- [x] Step 4b: Export categories report (CSV + MD)
- [x] Step 4c: Phat hien va test OVER_CAP problem — 27 sub-categories >2000 SP
- [x] Step 4c: Chon phuong an Adaptive Price-Range Slicing + Sort Rotation Fallback
- [x] Step 4d: Implement Adaptive Slicing vao `scraper.py` — test OK
  - 4 ham moi: `_fetch_listing_total`, `_sort_rotation_merge`, `_slice_recursive`, `fetch_all_ids_with_slicing`
  - Test sub 1951: **14,346 unique items** (99% coverage, vs baseline 2,000)
  - Bug phat hien va fix: API bao total=2000 (bi cap) nen detection dung `<` thay `<=`; pagination dung som do short page — fix bang cach check `len >= total`
- [x] Cap nhat docs: HUONG_DAN_VUOT_CAP_2000.md, plan_scraping_tiki.md, HUONG_DAN_CAO_DU_LIEU.md
- [x] Toi uu scraper: thread-local session reuse + skip JSON retry (tang ~17% toc do)
- [x] Toi uu scraper: max_redirects=3 + skip redirect loop ngay (khong retry)
- [x] Them skip category da hoan thanh khi resume (flag "complete" trong checkpoint)
- [x] Step 5: Scale — 49/49 categories DONE, 79,382 SP (may thue + may ca nhan song song)
- [x] Step 5b: Convert Kaggle CSV → JSONL — 41,603 SP (6 files thoi trang)
  - Script: `convert_kaggle_csv.py` — map name→title, description→features, brand tu filename
  - Brand mapping: tui xach nam/nu, Balo vali, phu kien thoi trang, giay nam/nu
  - Fix: LS/PS line terminators, price float→int

### Chua lam:
- [ ] **Day 0:** Cao Cocolux (~5-10K SP) → bo sung "Lam Dep - Suc Khoe"
- [ ] **Day 0:** Merge Hasaki + Cocolux JSONL vao Tiki_dataset_scrape/
- [ ] **Day 0:** (Uu tien 2) Cao BiboMart, ConCung, KidsPlaza (Me va Be)
- [ ] **Day 0:** (Uu tien 3) Cao CoopMart, WinMart, BachHoaXanh (Bach Hoa)
- [ ] **Day 1:** Re-run pipeline voi data moi, 9 categories, penalties
- [ ] **Day 2:** LLM rewrite (Groq Batch API)
- [ ] **Day 3:** Baseline ML (XGBoost, LightGBM, CatBoost)
- [ ] **Day 4:** DNN + Frontier LLM
- [ ] Cac giai doan tiep theo trong Project_Development_Plan.md (GD2: training Qwen 3.5 4B, GD3: scraping realtime, GD4: chatbot)

### Quyet dinh da dua ra:
- Se thue may de cao du lieu (khong chay tren WSL2)
- OVER_CAP: chon Adaptive Price-Range Slicing + Sort Rotation Fallback (industry-standard, Apify khuyen dung)
- Fine-tune: Qwen 3.5 4B thay vi Llama (tot hon cho tieng Viet)
- Du lieu hien co: Tiki 79,382 SP + Kaggle 41,603 SP + **Hasaki 11,410 SP** = **132,395 SP raw**
- Kaggle brand = ten the loai file (khong dung brand goc vi 74% la OEM/empty)
- Giu tat ca SP (khong loc gia, khong loc features length) — se xu ly o buoc tien xu ly
- **(2026-04-10) 9 categories:** Gop DienLanh+DienGiaDung, PhuKienTT+ThoiTrang, DoChoi+MeVaBe. Bo NhaSach, TheThao.
- **(2026-04-10) Category penalties:** Thoi Trang 0.4, Nha Cua 0.7
- **(2026-04-10) TRAIN_SIZE:** Giam tu 100K xuong 80K (cho room penalty)
- **(2026-04-11) Hasaki:** Cao xong 128/130 categories = 11,410 SP. Khong bi block. Scraper co workers, resume, report.
- **(2026-04-11) E-commerce plan:** He thong 10 trang TMDT, 4 phases. Phase 1a (Hasaki) DONE.

### Ket qua du lieu (2026-04-11):
- **Tiki scraper:** 49/49 categories DONE — 48 JSONL files, 79,382 SP (8085 Laptop: 0 SP)
- **Kaggle:** 6 CSV → 6 JSONL, 41,603 SP (thoi trang: balo, giay, tui, phu kien)
- **Hasaki:** 128/130 categories DONE — 128 JSONL files, **11,410 SP** (2 cat 0 SP: Son Mong, Nuoc Rua Mong)
- **Tong:** 182 JSONL files, **132,395 SP**
- Ty le thuc te Tiki: 28.2% (281K uoc tinh API → 79K thuc te, nhieu SP bi xoa)
- Ty le thuc te Hasaki: ~100% (11,407 uoc tinh → 11,410 thuc te)

### Luu y ky thuat:
- Tiki API bao `paging.total = 2000` khi bi cap (khong bao so thuc). Detection phai dung `total >= 2000` (khong phai `> 2000`)
- API doi khi tra ve page ngan hon `limit` (VD: 39/40 items) nhung chua het data. Pagination check bang `len(all_items) >= total` thay vi `len(items) < limit`
- `--max N` cat items tu dau danh sach (khoang gia thap). Khi test voi --max, items co the bi filter bo do gia <50K. Chay khong co --max thi khong bi
- Checkpoint chi luu Step 3 (Detail), KHONG luu Step 1 (Listing). Khi resume category chua complete, Step 1 se chay lai
- Category da complete (flag trong checkpoint) se skip toan bo khi resume — ke ca Step 1

---

## Prompt dau tien cho session moi

### Prompt A: Cao tiep du lieu e-commerce (HIEN TAI — Phase 1b Cocolux)

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai tong the hien tai
2. "scraping_data_tv/e-commerce-sites-scraping/scrap/e-commerce-plan.md" — plan cao 10 trang TMDT, trang thai cac phases
3. "scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py" — scraper Hasaki da hoan thanh (tham khao pattern)
4. "scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_categories_report.md" — bao cao Hasaki (128/130 cat, 11,410 SP)
5. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan Day 0-4

Hasaki da DONE (11,410 SP). Buoc tiep: Viet scraper Cocolux (cocolux.com), sau do merge tat ca vao pipeline.
Hay hoi toi nhung cau hoi can thiet.
```

### Prompt B: Merge du lieu + Re-run Day 1 pipeline

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai tong the
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan tien xu ly tieng Viet
3. "scraping_data_tv/Tiki/tiki_categories_report.md" — bao cao Tiki categories
4. "scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_categories_report.md" — bao cao Hasaki (DONE)
5. "scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md" — ket qua Day 1 lan truoc
6. "scraping_data_tv/Data_processing_for_Vietnamese_data" — code hien tai (pricer_vi/, day1_data_curation.py)

Du lieu: Tiki 79K + Kaggle 42K + Hasaki 11K = 132K SP. Can merge Hasaki JSONL vao Tiki_dataset_scrape/, re-run Day 1 pipeline.
Hay hoi toi nhung cau hoi can thiet.
```

### Prompt C: Day 2-4 — LLM rewrite + Training (sau khi Day 1 xong)

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai tong the
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan chi tiet Day 2-4
3. "segment4/mo_ta_du_an/Project_Development_Plan.md" — ke hoach tong the du an
4. "scraping_data_tv/Data_processing_for_English_data" chua code va tai lieu xu ly du lieu tieng Anh (tham khao)
5. "scraping_data_tv/Data_processing_for_Vietnamese_data" — code hien tai

Day 0-1 done. Buoc tiep: Day 2 LLM rewrite (Groq Batch API), Day 3 ML baseline, Day 4 DNN.
Hay hoi toi nhung cau hoi can thiet.
```

### Khi nao can doc them:
- **Scraper e-commerce moi**: doc `scraping_data_tv/e-commerce-sites-scraping/scrap/e-commerce-plan.md` + `hasaki_scraper.py` (tham khao pattern)
- **Tien xu ly du lieu**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md`
- **Scraper Tiki**: doc `scraping_data_tv/Tiki/tiki_scraper/scraper.py`
- **Code tham khao tieng Anh**: doc `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/pricer/`
- **Ke hoach du an**: doc `segment4/mo_ta_du_an/Project_Development_Plan.md`

---

## Files quan trong

| File | Muc dich |
|------|----------|
| **E-COMMERCE SCRAPERS** | |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/e-commerce-plan.md` | Plan cao 10 trang TMDT (trang thai, benchmark) |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py` | Hasaki scraper (DONE, 11,410 SP) |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_categories_report.md` | Bao cao 130 categories Hasaki (DONE) |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/HUONG_DAN_CAO_DU_LIEU_HASAKI.md` | Huong dan chay Hasaki scraper |
| `scraping_data_tv/e-commerce-sites-scraping/scrap/data/` | Output JSONL files (128 files Hasaki) |
| **TIKI** | |
| `scraping_data_tv/Tiki/tiki_categories_report.md` | Bao cao 122 sub-categories Tiki (DONE) |
| `scraping_data_tv/Tiki/HUONG_DAN_CAO_DU_LIEU.md` | Huong dan cao Tiki |
| `scraping_data_tv/Tiki/tiki_scraper/scraper.py` | Pipeline chinh Tiki |
| `scraping_data_tv/Tiki/run_scraper.py` | CLI Tiki scraper |
| **DATA PROCESSING** | |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md` | Plan tien xu ly Day 0-4 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py` | Day 1 pipeline |
| `segment4/mo_ta_du_an/Project_Development_Plan.md` | Ke hoach tong the 5 giai doan |
---

## Lenh chay nhanh

```bash
cd tech2ai

# Test nhanh
uv run scraping_data_tv/Tiki/run_scraper.py --test

# Cao 1 category
uv run scraping_data_tv/Tiki/run_scraper.py --category 1795 --workers 3

# Cao tat ca (tren may thue)
uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 5

# Dem tong SP da cao
uv run python -c "from pathlib import Path; files=list(Path('scraping_data_tv/Tiki/Tiki_dataset_scrape').glob('*.jsonl')); total=sum(sum(1 for _ in open(f,encoding='utf-8')) for f in files); print(f'Tong: {total:,} SP tu {len(files)} files')"

# Re-scan categories (cap nhat so luong SP)
uv run scraping_data_tv/Tiki/step1/02_get_subcategories.py

# Export categories report
uv run scraping_data_tv/Tiki/step1/03_export_categories_report.py

# Test phuong an vuot OVER_CAP
uv run scraping_data_tv/Tiki/step1/04_test_overcap_solutions.py
```

---

*Cap nhat: 2026-04-11 — Hasaki DONE (11,410 SP). Tong 132K SP. Can cao Cocolux, merge, re-run Day 1.*
