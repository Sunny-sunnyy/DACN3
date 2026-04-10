# Session Handoff — Tiki Scraper

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-10)

**Trang thai:** Day 0 — Can cao them du lieu (73 Tiki categories + trang khac). Day 1 da chay 1 lan (110K SP, push HF Hub) nhung can re-run sau khi co data moi.
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
- [ ] **Day 0:** Cao them 73 Tiki categories (~9K SP them)
- [ ] **Day 0:** Test + chay scraper co san (Hasaki, BiboMart, CoopMart...) → convert CSV→JSONL
- [ ] **Day 0:** (Uu tien 3) Viet scraper moi TGDD/FPT/Meta.vn
- [ ] **Day 1:** Re-run pipeline voi data moi, 9 categories, penalties
- [ ] **Day 2:** LLM rewrite (Groq Batch API)
- [ ] **Day 3:** Baseline ML (XGBoost, LightGBM, CatBoost)
- [ ] **Day 4:** DNN + Frontier LLM
- [ ] Cac giai doan tiep theo trong Project_Development_Plan.md (GD2: training Qwen 3.5 4B, GD3: scraping realtime, GD4: chatbot)

### Quyet dinh da dua ra:
- Se thue may de cao du lieu (khong chay tren WSL2)
- OVER_CAP: chon Adaptive Price-Range Slicing + Sort Rotation Fallback (industry-standard, Apify khuyen dung)
- Fine-tune: Qwen 3.5 4B thay vi Llama (tot hon cho tieng Viet)
- Du lieu hien co: Tiki scraper 79,382 SP + Kaggle 41,603 SP = **120,985 SP raw**
- Kaggle brand = ten the loai file (khong dung brand goc vi 74% la OEM/empty)
- Giu tat ca SP (khong loc gia, khong loc features length) — se xu ly o buoc tien xu ly
- **(2026-04-10) Cao them du lieu:** Them 73 Tiki categories + scraper co san (Hasaki, BiboMart, CoopMart...) + scraper moi (TGDD, FPT, Meta.vn)
- **(2026-04-10) 9 categories:** Gop DienLanh+DienGiaDung, PhuKienTT+ThoiTrang, DoChoi+MeVaBe. Bo NhaSach, TheThao.
- **(2026-04-10) Category penalties:** Thoi Trang 0.4, Nha Cua 0.7
- **(2026-04-10) TRAIN_SIZE:** Giam tu 100K xuong 80K (cho room penalty)

### Ket qua du lieu (2026-04-09):
- **Scraper:** 49/49 categories DONE — 48 JSONL files, 79,382 SP (8085 Laptop: 0 SP)
- **Kaggle:** 6 CSV → 6 JSONL, 41,603 SP (thoi trang: balo, giay, tui, phu kien)
- **Tong:** 54 JSONL files, **120,985 SP**
- Ty le thuc te scraper: 28.2% (281K uoc tinh API → 79K thuc te, nhieu SP bi xoa)

### Luu y ky thuat:
- Tiki API bao `paging.total = 2000` khi bi cap (khong bao so thuc). Detection phai dung `total >= 2000` (khong phai `> 2000`)
- API doi khi tra ve page ngan hon `limit` (VD: 39/40 items) nhung chua het data. Pagination check bang `len(all_items) >= total` thay vi `len(items) < limit`
- `--max N` cat items tu dau danh sach (khoang gia thap). Khi test voi --max, items co the bi filter bo do gia <50K. Chay khong co --max thi khong bi
- Checkpoint chi luu Step 3 (Detail), KHONG luu Step 1 (Listing). Khi resume category chua complete, Step 1 se chay lai
- Category da complete (flag trong checkpoint) se skip toan bo khi resume — ke ca Step 1

---

## Prompt dau tien cho session moi

### Prompt A: Day 0 — Thu thap them du lieu (HIEN TAI)

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan chi tiet (Day 0-4), 9 categories muc tieu, danh sach Tiki categories can them
2. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai hien tai
3. "scraping_data_tv/Tiki/tiki_scraper/config.py" — 49 categories da cao
4. "scraping_data_tv/Tiki/tiki_scraper/scraper.py" — pipeline scraper hien tai
5. "scraping_data_tv/e-commerce-sites-scraping/" — code scraper co san (Hasaki, BiboMart, CoopMart...)
6. "scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md" — ket qua Day 1 (EDA, phan tich)

Buoc tiep: Them 73 Tiki categories vao config.py, chay scraper. Sau do test scraper co san (Hasaki, BiboMart...).
Hay hoi toi nhung cau hoi can thiet.
```

### Prompt B: Day 1-4 — Tien xu ly du lieu tieng Viet (sau khi Day 0 xong)

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan chi tiet tien xu ly tieng Viet
2. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai du lieu hien tai
3. "scraping_data_tv/Tiki/tiki_categories_report.md" — bao cao categories
4. "segment4/mo_ta_du_an/Project_Development_Plan.md" — ke hoach tong the du an
5. "scraping_data_tv/Data_processing_for_English_data" chua code va tai lieu xu ly du lieu tieng Anh (tham khao)
6. "scraping_data_tv/Tiki" chua codebase va docs cao du lieu Tiki
7. "scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md" — ket qua Day 1
8. "scraping_data_tv/Data_processing_for_Vietnamese_data" — code hien tai (pricer_vi/, day1_data_curation.py)

Sau do cho toi biet ban da nam duoc gi va buoc tiep theo la gi. Hay hoi toi nhung cau hoi can thiet.
```

### Prompt C: Scraping du lieu Tiki (chi dung khi can sua scraper)

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai hien tai
2. "scraping_data_tv/Tiki/plan_scraping_tiki.md" — plan chi tiet Tiki scraper
3. "segment4/mo_ta_du_an/Project_Development_Plan.md" — ke hoach tong the du an

Sau do cho toi biet ban da nam duoc gi va buoc tiep theo la gi. Hay hoi toi nhung cau hoi can thiet.
```

### Khi nao can doc them:
- Neu lam viec voi **tien xu ly du lieu**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md`
- Neu lam viec voi **search_key pipeline** (segment4): doc them `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`
- Neu lam viec voi **scraper code Tiki**: doc them `scraping_data_tv/Tiki/tiki_scraper/scraper.py`
- Neu lam viec voi **scraper code khac**: doc them `scraping_data_tv/e-commerce-sites-scraping/`
- Neu can **code tham khao tieng Anh**: doc `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/pricer/`

---

## Files quan trong

| File | Muc dich |
|------|----------|
| `scraping_data_tv/Tiki/plan_scraping_tiki.md` | Plan Tiki scraper (trang thai, benchmark, cach chay) |
| `scraping_data_tv/Tiki/HUONG_DAN_CAO_DU_LIEU.md` | Huong dan cao tren may thue + resume nhieu buoi |
| `scraping_data_tv/Tiki/HUONG_DAN_VUOT_CAP_2000.md` | Van de OVER_CAP + 3 phuong an + ket qua test |
| `scraping_data_tv/Tiki/tiki_categories_report.csv` | Bang danh muc 122 sub-categories voi SP count + OVER_CAP status |
| `scraping_data_tv/Tiki/tiki_categories_report.md` | Bang danh muc (Markdown) |
| `scraping_data_tv/Tiki/run_scraper.py` | CLI: `--test`, `--all`, `--category`, `--workers`, `--max` |
| `scraping_data_tv/Tiki/tiki_scraper/scraper.py` | Pipeline chinh: listing -> filter -> detail -> JSONL |
| `scraping_data_tv/Tiki/tiki_scraper/config.py` | 49 categories, rate limits, delays |
| `scraping_data_tv/Tiki/step1/step1_notes.md` | Ket qua test API + benchmark |
| `scraping_data_tv/Tiki/step1/04_test_overcap_solutions.py` | Script test 3 phuong an vuot OVER_CAP |
| `scraping_data_tv/Tiki/convert_kaggle_csv.py` | Convert Kaggle CSV → JSONL (6 files thoi trang) |
| `segment4/mo_ta_du_an/Project_Development_Plan.md` | Ke hoach tong the 5 giai doan (8 thang) |

| `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md` | Tai lieu search_key pipeline (tieng Anh) |
| `CLAUDE.md` | Quy tac code, workflow, debugging |
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

*Cap nhat: 2026-04-10 — Day 1 da chay (110K SP, push HF). Can cao them 73 Tiki cat + trang khac truoc khi re-run Day 1.*
