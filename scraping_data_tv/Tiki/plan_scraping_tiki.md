# Plan: Scraping Tiki VN — 100K san pham

## Context

Du an tot nghiep "Tro ly mua sam thong minh tieng Viet" can 1M+ san pham tieng Viet. Shopee anti-bot qua manh (da thu 7 approach, tat ca that bai — xem `Shopee/step1/step1_notes.md`). Chuyen sang Tiki VN — it chong bot hon, co public JSON API.

**Du lieu hien co:** 41.6K san pham tu Kaggle (toan thoi trang: balo, giay, tui, phu kien). Thieu electronics va gia dung.

**Muc tieu:** Cao them ~60K+ san pham tu Tiki (uu tien dien tu, gia dung, do gia dung) de dat tong 100K+. Sau do scale len 1M.

**Fields can thiet:** title, brand, price, features, url

**Khoang gia:** 50.000 - 50.000.000 VND

**Working directory:** `tech2ai/scraping_data_tv/Tiki/`

---

## Approach: Tiki Public API v2

Dua tren phan tich 5 repos tham khao (folder `Github/`), Tiki co 2 API endpoints chinh:

### API 1: Listing (danh sach san pham theo category)
```
GET https://tiki.vn/api/v2/products?category={category_id}&limit=100&page={page_num}&include=advertisement&aggregations=1
```
- Tra ve: id, name, price, brand, rating, sold, thumbnail
- Pagination: `page=1,2,3...`, moi page toi da 100 san pham
- KHONG co description/features chi tiet

### API 2: Product Detail (thong tin chi tiet 1 san pham)
```
GET https://tiki.vn/api/v2/products/{product_id}
```
- Tra ve: FULL JSON — name, price, brand, description, specifications, breadcrumbs, images, url
- Day la noi lay features/specs chi tiet

### Pipeline:
```
Listing API (lay danh sach IDs)  -->  Filter (gia, co brand)  -->  Detail API (lay full info)
     ~1000 requests                    bo ~30% rac                   ~70K requests
     ~1-2 gio                                                        ~24-48 gio
```

---

## Folder Structure

```
scraping_data_tv/Tiki/
    plan_scraping_tiki.md          # File nay
    run_scraper.py                 # CLI: --test, --category ID, --all, --max N
    Docs/                          # Tiki Open API docs
    Github/                        # 5 repos tham khao
    Tiki_dataset_1/                # Kaggle 41.6K (thoi trang, CSV)
    Tiki_dataset_scrape/           # OUTPUT: JSONL per category (scraper ghi vao day)
    step1/                         # Thu nghiem API
        00_test_tiki_api.py        # Test 2 API endpoints
        01_get_categories.py       # Scan 24 parent categories
        02_get_subcategories.py    # Scan 122 sub-categories
        03_test_scraper.py         # Test scraper (Tivi, 30 SP)
        step1_notes.md             # Ghi chep ket qua chi tiet
        data/raw/                  # Raw JSON responses + category scans
        data/test_output/          # Test JSONL outputs
    tiki_scraper/                  # Code chinh
        __init__.py
        models.py                  # Pydantic: TikiProduct
        scraper.py                 # Pipeline: listing -> filter -> detail -> save JSONL
        config.py                  # 47 sub-categories, rate limits, headers
    checkpoints/                   # Scraping progress (resume khi bi ngat)
```

---

## Implementation Steps

### Step 1: Thu nghiem API (HOAN THANH)
**File:** `step1/00_test_tiki_api.py`
**Ket qua:** Ca 2 API deu 200 OK, data day du, khong bi block. Chi tiet: `step1/step1_notes.md`

---

### Step 2: Lay danh sach categories (HOAN THANH)
**Files:** `step1/01_get_categories.py`, `step1/02_get_subcategories.py`
**Ket qua:**
- 24 parent categories -> 122 sub-categories, tong ~585K san pham
- Listing API cap `total` o 2000/query -> giai phap: query theo sub-category
- Chon 47 sub-categories da dang (dien tu, gia dung, phu kien, suc khoe...) vao `config.py`
- Loai bo: Sach (241K — khong phu hop), Thoi trang (da co 41K tu Kaggle)

---

### Step 3: Xay dung scraper chinh (HOAN THANH)
**Files:** `tiki_scraper/models.py`, `tiki_scraper/scraper.py`, `tiki_scraper/config.py`, `run_scraper.py`

**Da trien khai:**
- `models.py`: TikiProduct (Pydantic) — product_id, title, brand, price, features, url, category, category_id
- `config.py`: 47 sub-categories, PRICE_MIN=50K, PRICE_MAX=50M, rate limits
- `scraper.py`: Pipeline listing -> filter price -> detail -> save JSONL + checkpoint
- `run_scraper.py`: CLI interface (`--test`, `--category ID`, `--all`, `--max N`)

**Tinh nang:**
- Checkpoint moi 100 san pham, resume khi bi ngat
- Session rotation moi 500 requests
- Batch sleep 3s moi 50 requests
- Retry 3 lan khi loi, doi 5 phut khi bi 429/403
- Category breadcrumb: lay toi da 3 cap, bo ten san pham
- Output: JSONL, moi category 1 file (`Tiki_dataset_scrape/tiki_{id}.jsonl`)

---

### Step 4: Test voi 1 category (HOAN THANH)

**Test 1: Tivi (5015) — 30 san pham:**
- [x] Data dung format? title, brand, price, features, url deu co
- [x] Price dung (VND, khong can chia 100K)
- [x] Features du dai (avg 5130 chars)
- [x] URL hop le (https://tiki.vn/...)
- [x] Checkpoint hoat dong
- [x] Khong bi block

**Test 2: Dien thoai Smartphone (1795) — 103 san pham (FULL category):**
- [x] 103/103 san pham, ~2 phut 17 giay (~1.3s/SP)
- [x] Price range: 210K - 41M VND
- [x] Features avg: 3,379 chars
- [x] 9 brands: Xiaomi, Samsung, OPPO, Apple, Realme, Vivo, Tecno, OnePlus, Nokia
- [x] Khong bi block sau 103 requests lien tuc

---

### Step 5: Scale — cao tat ca categories (~60K+ san pham)

Neu step 4 OK tren WSL2:
- Thue may manh hon (VPS hoac Vast.ai)
- Chay cho tat ca categories
- Uoc tinh: ~60-70K detail requests, delay 1s/req = ~20-24 gio
- Checkpoint moi 100 san pham -> resume duoc neu bi ngat

---

### Step 6: Merge voi Kaggle dataset

- Load 41.6K tu Kaggle (thoi trang)
- Load ~60K tu Tiki scraper (dien tu, gia dung)
- Chuan hoa fields: title, brand, price, features, url (Kaggle khong co url -> de trong)
- Dedup theo title
- Tong: ~100K san pham da dang categories

---

## Anti-Bot Strategy

Tiki it chong bot hon Shopee, nhung van can than trong:

1. **curl_cffi + impersonate="chrome"** (proven trong project)
2. **User-Agent** header hop le
3. **Random delays**: 1-2s listing, 0.3-0.8s detail (per worker)
4. **Batch sleep**: sleep 2s moi 100 requests (toan bo workers)
5. **Checkpoint + resume**: save progress moi 100 SP, resume khi bi ngat
6. **Session rieng moi worker**: moi thread co curl_cffi session doc lap
7. **Neu bi 429/403**: doi 5 phut, retry voi session moi

---

## Uoc tinh thoi gian

| Buoc | Thoi gian code | Thoi gian chay | Trang thai |
|------|---------------|----------------|------------|
| Step 1: Test API | 30 phut | 5 phut | HOAN THANH |
| Step 2: Categories | 30 phut | 5 phut | HOAN THANH |
| Step 3: Scraper | 2-3 gio | - | HOAN THANH |
| Step 4: Test 1 category | - | ~2 phut | HOAN THANH |
| Step 5: Scale full | - | ~36 gio | CHUA LAM |
| Step 6: Merge | 1 gio | 30 phut | CHUA LAM |

---

## Cau hinh may test (WSL2)

| Thanh phan | Thong so |
|------------|----------|
| CPU | Intel i5-11400H @ 2.70GHz, 12 cores |
| RAM | 7.6 GB (5.6 GB available) |
| Disk | 1 TB SSD (909 GB free) |
| OS | WSL2 — Linux 6.6.87.2-microsoft-standard-WSL2 |
| Python | 3.12.3 (uv) |
| Tiki API latency | ~240ms/request |

## Benchmark thuc te

**Test: Dien thoai Smartphone (1795) — 103 san pham, full category:**

```
16:53:05 Step 1: Fetching listing... (3 pages, 103 items)
16:53:08 Step 2: After price filter: 103 items (removed 0)
16:53:08 Step 3: Fetching details...
16:54:11   Progress: 50/103 done, 50 saved | 0.8 SP/s | ETA: 1m 6s
16:55:14   Progress: 100/103 done, 100 saved | 0.8 SP/s | ETA: 0m 3s
16:55:19 Done: 103 products | Time: 0h 2m 10s (0.8 SP/s)
```

| Metric | Gia tri |
|--------|---------|
| Tong san pham | 103/103 (100%) |
| Thoi gian | 2 phut 10 giay |
| Toc do | 0.8 SP/giay (~1.25s/SP) |
| Bi block | Khong |
| Features avg | 3,379 chars |
| Price range | 210,000 - 40,990,000 VND |
| Brands | 9 (Xiaomi 39, Samsung 31, OPPO 13, Apple 7, ...) |

**Benchmark concurrent (workers=3, cung 103 SP Smartphone):**

```
17:18:33 Step 3: Fetching details (workers=3)...
17:18:55   Progress: 50/103 done, 50 saved | 2.7 SP/s | ETA: 0h 0m 19s
17:19:14 Done: 103 products | Time: 0h 0m 38s (2.7 SP/s)
```

| Workers | Toc do | Thoi gian (103 SP) | Tang toc |
|---------|--------|-------------------|---------|
| 1 | 0.8 SP/s | 2m 10s | 1x |
| 3 | 2.7 SP/s | 38s | 3.4x |

**Benchmark resume (da test thuc te):**

```
Lan 1: cao 30 SP -> Ctrl+C -> checkpoint luu 30 IDs
Lan 2: chay lai  -> "Resuming: 30 already done, To scrape: 73 items"
Ket qua: 30 + 73 = 103 SP (dung, khong trung lap, khong mat data)
```

**Uoc tinh scale:**

| Muc tieu | 1 worker (0.8 SP/s) | 3 workers (2.7 SP/s) | 5 workers (~4.5 SP/s) |
|----------|--------------------|--------------------|---------------------|
| 1,000 SP | ~21 phut | ~6 phut | ~4 phut |
| 10,000 SP | ~3.5 gio | ~1 gio | ~37 phut |
| 60,000 SP | ~21 gio | ~6 gio | ~3.7 gio |
| 100,000 SP | ~35 gio | ~10 gio | ~6 gio |

Luu y: Toc do co the thay doi tuy vao mang va Tiki rate limit.
May thue (1Gbps, IP VN) nhanh hon WSL2 ~30-50%.

---

## Dependencies

Tat ca da co trong project: `curl_cffi`, `pydantic`, `tqdm`. Khong can them package moi.

---

## Cach chay

```bash
cd tech2ai

# Test nhanh (Tivi, 50 SP)
uv run scraping_data_tv/Tiki/run_scraper.py --test

# Cao 1 category, 3 workers
uv run scraping_data_tv/Tiki/run_scraper.py --category 1795 --workers 3

# Cao TAT CA 47 categories, 3 workers (~10 gio)
uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 3

# Cao tat ca, 5 workers, gioi han 500 SP/category (~3 gio)
uv run scraping_data_tv/Tiki/run_scraper.py --all --max 500 --workers 5
```

**Options:**
- `--workers N`: so luong requests song song (mac dinh 1, khuyen nghi 3-5)
- `--max N`: gioi han so SP moi category
- `--category ID`: cao 1 category
- `--name "ten"`: ten category (neu ID ngoai config)

**Output:** `Tiki_dataset_scrape/tiki_{category_id}.jsonl` — moi category 1 file rieng.
**Resume:** neu bi ngat, chay lai cung lenh — tu dong bo qua SP da cao.
**Cao nhieu buoi:** push checkpoint + data len GitHub truoc khi tra may, pull lai buoi sau.
Chi tiet: xem `HUONG_DAN_CAO_DU_LIEU.md`

---

## Thay doi so voi plan ban dau

| Thay doi | Truoc | Sau |
|----------|-------|-----|
| So categories | 15-20 parent categories | 47 sub-categories (vuot gioi han 2000/query) |
| Output folder | `data/raw/` | `Tiki_dataset_scrape/` |
| Category breadcrumb | Full breadcrumb (gom ten SP) | Toi da 3 cap, bo ten SP |
| Listing limit | 100/page | 40/page (an toan hon) |
| Muc tieu | 60K+ | 100K+ (47 sub-categories, tong ~270K SP kha dung) |
| Detail fetching | Sequential (1 request/luc) | Concurrent (N workers song song) |
| DETAIL_DELAY | 0.5-1.5s | 0.3-0.8s (per worker) |
| BATCH_SLEEP | 3s moi 50 req | 2s moi 100 req |
| Toc do | 0.8 SP/s | 2.7 SP/s (3 workers), ~4.5 SP/s (5 workers) |

---

*Cap nhat: 2026-04-07 — Step 1-4 hoan thanh. Concurrent workers + resume da test.*
