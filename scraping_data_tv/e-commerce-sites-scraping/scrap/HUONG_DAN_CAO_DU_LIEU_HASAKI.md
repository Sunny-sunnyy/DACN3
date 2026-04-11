# Huong dan cao du lieu Hasaki

## Tong quan

- **Trang:** hasaki.vn (my pham chinh hang)
- **Tech:** JSON API (khong can Selenium/Chrome)
- **Category:** Tat ca 130 categories map vao **"Lam Dep - Suc Khoe"**
- **Tong SP:** ~11,407 san pham (xem `hasaki_categories_report.md`)
- **Output:** JSONL files trong `scrap/data/`
- **File naming:** `hasaki_category_{id}.jsonl` (khi cao 1 category), `hasaki_all_{date}.jsonl` (khi cao tat ca)
- **Block handling:** Tu dong doi 60s + rotate session khi bi 403/429
- **Schema:** `{title, price, features, brand, category}` — tuong thich Tiki pipeline

---

## Thong so may tinh

| Thong so | Gia tri |
|---|---|
| CPU | i5-11400H @ 2.70GHz (12 threads) |
| RAM | 7.6 GB |
| Latency toi Hasaki | ~0.47s/request |
| **Workers de xuat** | **3** (an toan, khong overload server) |

### Benchmark toc do

| Workers | Toc do (SP/s) | Tang x | Uoc tinh 10K SP |
|---|---|---|---|
| 1 | 1.4 | 1x | ~2 gio |
| 3 | 3.7 | 2.6x | **~45 phut** |
| 5 | ~5-6 | ~4x | ~30 phut |

**Khuyen nghi:** Dung 3 workers. Tang len 5 neu muon nhanh hon nhung co the bi rate-limit.

---

## Buoc 1: Chuan bi (1 lan)

```bash
cd tech2ai
uv sync
```

---

## Buoc 2: Xem report categories (1 lan)

```bash
# Xem toan bo categories va so SP
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --report
```

Ket qua: file `hasaki_categories_report.md` gom 130 categories, tong ~11,407 SP.

---

## Buoc 3: Test nhanh (2 phut)

### 3.1. Test 1 category, 5 SP

```bash
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --test
```

Ket qua mong doi:
```
Fetching categories from Hasaki API...
Found 130 leaf categories
--- Category: My Pham High-End (id=1907) ---
  Found 5 product IDs, workers=1
  Done: 5 products in 3.5s (1.4 SP/s), 0 errors
=== DONE: 5 products total ===
```

### 3.2. Test 1 category cu the, nhieu SP hon

```bash
# Cao 50 SP tu "Sua Rua Mat" (id=19) voi 3 workers
# File output: scrap/data/hasaki_category_19.jsonl
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py \
    --category 19 --max 50 --workers 3
```

### 3.3. Kiem tra output

```bash
# Dem so dong
wc -l scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki*.jsonl

# Xem 1 SP
head -1 scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki*.jsonl | \
    uv run python3 -c "import sys,json; d=json.loads(sys.stdin.read()); \
    print('title:', d['title']); print('price:', d['price']); \
    print('brand:', d['brand']); print('features:', len(d['features']), 'chars')"
```

Kiem tra:
- [ ] `title` — co noi dung tieng Viet, khong rong
- [ ] `price` — > 0 (VND)
- [ ] `brand` — co ten thuong hieu
- [ ] `features` — >= 100 chars, co mo ta co y nghia (khong phai HTML)
- [ ] `category` — bat dau bang "Lam Dep - Suc Khoe >"

---

## Buoc 4: Cao het 1 category (test full)

```bash
# Cao het tat ca san pham trong "Chong Nang Da Mat" (id=11)
# File output: scrap/data/hasaki_category_11.jsonl
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py \
    --category 11 --workers 3
```

Se hien:
```
--- Category: Chong Nang Da Mat (id=11) ---
  Found 200+ product IDs, workers=3
  Progress: 50/200 (48 saved, 3.7 SP/s, ETA 40s)
  Progress: 100/200 (97 saved, 3.5 SP/s, ETA 28s)
  ...
  Done: 195 products in 55s (3.5 SP/s), 3 errors
```

---

## Buoc 5: Cao tat ca categories (full run)

```bash
# Cao tat ca 130 categories voi 3 workers
# File output: scrap/data/hasaki_all_2026-04-11.jsonl
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --workers 3
```

**Uoc tinh:**
- 130 leaf categories
- **~11,407 SP** (da scan tu report)
- 3 workers = 3.7 SP/s
- **Thoi gian: ~50-60 phut**

### Theo doi tien do

Scraper se in progress moi 50 SP:
```
[1/130] Category: Tay Trang Mat (id=48) — 150 SP, 3.5 SP/s
[2/130] Category: Sua Rua Mat (id=19) — 200 SP, 3.7 SP/s
...
[130/130] Done!
DONE: 12,345 products total in 3600s (60 min)
Speed: 3.4 SP/s
```

---

## Buoc 5: Merge vao Tiki pipeline

Sau khi cao xong, copy JSONL vao folder Tiki data de Day 1 pipeline co the load:

```bash
cp scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_*.jsonl \
   scraping_data_tv/Tiki/Tiki_dataset_scrape/
```

Sau do cap nhat `CATEGORY_MAP` trong `day1_data_curation.py` (neu chua co):
```python
# Them mapping cho Hasaki
"Làm Đẹp - Sức Khỏe": "Làm Đẹp - Sức Khỏe",
```

Re-run Day 1:
```bash
uv run scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py
```

---

## Cac lenh tham khao

| Lenh | Muc dich | Output file |
|------|----------|-------------|
| `--test` | Test nhanh: 1 category, 5 SP | `hasaki_test_{date}.jsonl` |
| `--report` | Scan tat ca categories, in so SP | `hasaki_categories_report.md` |
| `--category 11 --max 50 --workers 3` | Cao 50 SP tu 1 category | `hasaki_category_11.jsonl` |
| `--category 11 --workers 3` | Cao het 1 category | `hasaki_category_11.jsonl` |
| `--workers 3` | Cao tat ca 130 categories | `hasaki_all_{date}.jsonl` |
| `--workers 5` | Cao tat ca (nhanh hon) | `hasaki_all_{date}.jsonl` |

| Folder | Noi dung |
|--------|---------|
| `scrap/data/` | Output JSONL files |
| `scrap/hasaki_scraper.py` | Code scraper |
| `scrap/e-commerce-plan.md` | Plan tong the |

---

## Xu ly su co

### Hasaki rate-limit (429)
- Giam workers: `--workers 1`
- Doi 5 phut roi chay lai (scraper tu retry 3 lan)

### Bi ngat giua chung (Ctrl+C, mat mang)
- **Chua co checkpoint** — chay lai tu dau
- Output file se bi append trung → xoa file rong truoc khi chay lai:
```bash
rm -f scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_*.jsonl
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --workers 3
```

### Loi JSON parse
- Thuong do Hasaki thay doi API → kiem tra API response bang:
```bash
curl -s "https://hasaki.vn/wap/v2/product/detail?id=86972" | uv run python3 -m json.tool | head -20
```

---

*Tao ngay: 2026-04-11. Hasaki API JSON, 130 categories, ~10-15K SP.*
