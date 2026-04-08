# Session Handoff — Tiki Scraper

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-07, 22:30)

**Trang thai:** Step 4d HOAN THANH. San sang Step 5 (scale tren may thue).
**Branch:** `feature/tiki-scraper`

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

### Chua lam:
- [ ] Step 5: Scale — cao 100K+ SP tren may thue (VPS) — DANG CHAY (may RTX 5060 Ti, i7-12700K, 5 workers)
- [ ] Step 6: Merge Kaggle 41K (thoi trang) + Tiki scraper (dien tu, gia dung)
- [ ] Cac giai doan tiep theo trong Project_Development_Plan.md (GD2: training, GD3: scraping realtime, GD4: chatbot)

### Quyet dinh da dua ra:
- Se thue may de cao du lieu (khong chay tren WSL2)
- Muc tieu dau tien: 100K SP de test, sau do scale len
- OVER_CAP: chon Adaptive Price-Range Slicing + Sort Rotation Fallback (industry-standard, Apify khuyen dung)

### Luu y ky thuat:
- Tiki API bao `paging.total = 2000` khi bi cap (khong bao so thuc). Detection phai dung `total >= 2000` (khong phai `> 2000`)
- API doi khi tra ve page ngan hon `limit` (VD: 39/40 items) nhung chua het data. Pagination check bang `len(all_items) >= total` thay vi `len(items) < limit`
- `--max N` cat items tu dau danh sach (khoang gia thap). Khi test voi --max, items co the bi filter bo do gia <50K. Chay khong co --max thi khong bi

---

## Prompt dau tien cho session moi

Copy va paste prompt nay khi bat dau session moi:

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai hien tai
2. "scraping_data_tv/Tiki/plan_scraping_tiki.md" — plan chi tiet Tiki scraper
3. "segment4/mo_ta_du_an/Project_Development_Plan.md" — ke hoach tong the du an
4. "scraping_data_tv/Tiki" chứa codebase và docs cào dữ liệu ở tiki

Sau do cho toi biet ban da nam duoc gi va buoc tiep theo la gi. Hãy hỏi tôi những câu hỏi cần thiết để hiểu rõ yêu cầu.
```

### Khi nao can doc them:
- Neu lam viec voi **search_key pipeline** (segment4): doc them `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`
- Neu lam viec voi **scraper code**: doc them `scraping_data_tv/Tiki/tiki_scraper/scraper.py`
- Neu can **huong dan chay tren may thue**: doc `scraping_data_tv/Tiki/HUONG_DAN_CAO_DU_LIEU.md`
- Neu can **ket qua test chi tiet**: doc `scraping_data_tv/Tiki/step1/step1_notes.md`
- Neu can **van de OVER_CAP 2000**: doc `scraping_data_tv/Tiki/HUONG_DAN_VUOT_CAP_2000.md`
- Neu can **danh sach categories**: doc `scraping_data_tv/Tiki/tiki_categories_report.csv` hoac `.md`

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
| `scraping_data_tv/Tiki/tiki_scraper/config.py` | 47 categories, rate limits, delays |
| `scraping_data_tv/Tiki/step1/step1_notes.md` | Ket qua test API + benchmark |
| `scraping_data_tv/Tiki/step1/04_test_overcap_solutions.py` | Script test 3 phuong an vuot OVER_CAP |
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

*Cap nhat: 2026-04-07 22:30 — Step 4d hoan thanh. Adaptive Slicing test OK (14,346 SP, 99% coverage). San sang Step 5.*
