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
    SESSION_HANDOFF.md             # Trang thai session hien tai
    HUONG_DAN_CAO_DU_LIEU.md       # Huong dan cao tren may thue
    HUONG_DAN_VUOT_CAP_2000.md     # Van de OVER_CAP + 3 phuong an + ket qua test
    tiki_categories_report.csv     # Bang danh muc 122 sub-categories (CSV)
    tiki_categories_report.md      # Bang danh muc (Markdown)
    run_scraper.py                 # CLI: --test, --category ID, --all, --max N
    convert_kaggle_csv.py          # Convert Kaggle CSV -> JSONL (6 files thoi trang)
    Docs/                          # Tiki Open API docs
    Github/                        # 5 repos tham khao
    Tiki_dataset_1/                # Kaggle 41.6K (thoi trang, CSV)
    Tiki_dataset_scrape/           # OUTPUT: JSONL per category (scraper ghi vao day)
    step1/                         # Thu nghiem API
        00_test_tiki_api.py        # Test 2 API endpoints
        01_get_categories.py       # Scan 24 parent categories
        02_get_subcategories.py    # Scan 122 sub-categories
        03_export_categories_report.py  # Export CSV + bang danh muc
        04_test_overcap_solutions.py    # Test 3 phuong an vuot OVER_CAP
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
- Flag "complete" trong checkpoint — skip toan bo category da hoan thanh khi resume (ke ca listing)
- Thread-local session reuse per worker (tiet kiem TLS handshake)
- Session rotation moi 500 requests
- Batch sleep 2s moi 100 requests
- max_redirects=3 — fail nhanh cho SP bi redirect loop
- Skip ngay (khong retry) cho loi JSON parse va redirect loop
- Retry 3 lan cho loi mang, doi 5 phut khi bi 429/403
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

### Step 4b: Re-scan va bao cao categories (HOAN THANH)
**Files:** `step1/03_export_categories_report.py`, `tiki_categories_report.csv`, `tiki_categories_report.md`
**Ket qua (2026-04-07):**
- Re-scan xac nhan: 15 parent categories -> 122 sub-categories, ~585,374 SP
- 27 sub-categories co >2000 SP -> bi OVER_CAP boi Listing API
- Export CSV + Markdown report day du

---

### Step 4c: Phat hien va test OVER_CAP problem (HOAN THANH)
**Files:** `step1/04_test_overcap_solutions.py`, `HUONG_DAN_VUOT_CAP_2000.md`

**Van de:** Listing API cap ket qua o 2000 SP/query. 27 sub-categories co >2000 SP,
tong mat ~200K SP neu khong xu ly.

**Test thuc te tren sub 1951 (Dung cu nha bep, 14,478 SP):**

| Phuong an | SP lay duoc | Coverage | Cach hoat dong |
|-----------|------------|----------|----------------|
| Baseline (khong lam gi) | 2,000 | 14% | Listing binh thuong |
| Sort Rotation | ~5-7K (uoc tinh) | 35-48% | Doi sort param (price_asc, price_desc, newest) |
| **Price-Range Slicing** | **13,935** | **96%** | Chia query theo 8 khoang gia |
| Sub-Sub Drilling | 11,926 | 82% | Drill xuong sub-sub-categories |

**Quyet dinh:** Chon **Price-Range Slicing** — can implement vao `scraper.py` truoc Step 5.
Chi tiet: xem `HUONG_DAN_VUOT_CAP_2000.md`

---

### Step 4d: Implement Adaptive Price-Range Slicing (HOAN THANH)

**File:** `tiki_scraper/scraper.py`

**Thuat toan 2 tang:**
- **Tang 1 — Adaptive Slicing:** Khi total >=2000, chia 8 khoang gia → query tung khoang → neu van >=2000 thi chia doi (recursive) → dung khi khoang <1,000 VND
- **Tang 2 — Sort Rotation Fallback:** Khi khoang gia <1,000 VND ma van >=2000 SP → query 4 kieu sort (default, price_asc, price_desc, newest) → merge + dedup IDs
- Chi tiet: xem `HUONG_DAN_VUOT_CAP_2000.md` (muc "Phuong an cuoi cung")

**Cac ham moi trong scraper.py:**
- `_fetch_listing_total()` — lay nhanh total SP cho 1 khoang gia
- `_sort_rotation_merge()` — fallback: 4 sort orders, merge + dedup
- `_slice_recursive()` — recursive chia doi khoang gia
- `fetch_all_ids_with_slicing()` — entry point, tu dong chon normal/slicing

**Cap nhat ham cu:**
- `fetch_listing_page()` — them param `extra_params` (price, sort)
- `fetch_all_product_ids()` — them `extra_params` + fix pagination (dung `len >= total` thay vi `len < limit`)
- `scrape_category()` — goi `fetch_all_ids_with_slicing()` thay vi `fetch_all_product_ids()` truc tiep

**Test thuc te (sub 1951, Dung cu nha bep):**

| Metric | Ket qua |
|--------|---------|
| Unique items | 14,346 |
| Coverage | ~99% (vs 14,478 API total) |
| Baseline (khong slicing) | 2,000 (14%) |
| Thoi gian listing | ~10 phut (WSL2) |
| Ranges chia | 5/8 ranges can split (0-50K, 50K-100K, 100K-200K, 200K-500K, 500K-1M) |
| Sort Rotation | Khong can (tat ca ranges <2000 sau khi chia doi) |

**Bugs phat hien va fix:**
- API bao `total=2000` khi bi cap → detection dung `total >= 2000` (khong phai `> 2000`)
- Pagination dung som khi page tra ve <limit items → fix check `len(all_items) >= total`

---

### Step 5: Scale — cao 100K+ san pham (HOAN THANH)

**Hoan thanh:** 2026-04-09 — 49/49 categories, **79,382 SP** tu 48 JSONL files.

**May thue (RTX 5060 Ti, i7-12700K, 28GB RAM, 1Gbps VN):**
- 7 workers, ~7.7 SP/s
- 12 categories lon (>5K SP uoc tinh)

**May ca nhan (WSL2, i5-11400H, 7.6GB RAM):**
- 3 workers, ~3.5 SP/s
- 37 categories nho-vua (<5K SP uoc tinh)

**Ket qua thuc te:**
- API uoc tinh: 281,056 SP → Thuc te: 79,382 SP (ty le 28.2%)
- Nhieu SP bi xoa/redirect → scraper skip ngay (non-JSON, redirect loop)
- 8085 (Laptop): 0 SP — tat ca 21 SP bi filter/xoa, khong tao JSONL
- Categories cong nghe/phu kien: ty le thap (6-55%)
- Categories dien lanh/the thao: ty le cao (51-87%)

---

### Step 5b: Convert Kaggle CSV → JSONL (HOAN THANH)

**File:** `convert_kaggle_csv.py`
**Hoan thanh:** 2026-04-09 — 6 CSV → 6 JSONL, **41,603 SP**

**Mapping:** name→title, description→features, price→price (int), category→category
**Brand:** Gan tu ten file CSV (khong dung brand goc vi 74% la OEM/empty):

| File CSV | Brand | SP |
|---|---|---:|
| backpacks_suitcases | Balo vali | 5,361 |
| fashion_accessories | phụ kiện thời trang | 16,019 |
| men_bags | túi xách nam | 4,234 |
| men_shoes | giày nam | 5,745 |
| women_bags | túi xách nữ | 4,325 |
| women_shoes | giày nữ | 5,919 |

**Fix:** Xoa ky tu LS (U+2028) / PS (U+2029) trong description, price float→int
**Khong loc gia, khong loc features length** — giu tat ca SP, se xu ly o buoc tien xu ly

**Tong du lieu hien co:** Scraper 79,382 + Kaggle 41,603 = **120,985 SP** (54 JSONL files)

---

### Step 6: Tien xu ly du lieu

- Load 120,985 SP tu 54 JSONL files
- Dedup theo title
- Weighted sampling: price² + penalty category lon (VD: Phu Kien Dien Thoai)
- Tao LLM summary bang Qwen (tuong tu tieng Anh dung GPT)
- Muc tieu: ~200K SP (co them nguon khac ngoai Tiki)

---

## Anti-Bot Strategy

Tiki it chong bot hon Shopee, nhung van can than trong:

1. **curl_cffi + impersonate="chrome"** (proven trong project)
2. **User-Agent** header hop le
3. **Random delays**: 1-2s listing, 0.3-0.8s detail (per worker)
4. **Batch sleep**: sleep 2s moi 100 requests (toan bo workers)
5. **Checkpoint + resume**: save progress moi 100 SP, resume khi bi ngat
6. **Thread-local session reuse**: moi worker tai su dung 1 session, rotate moi 500 requests
7. **Neu bi 429/403**: doi 5 phut, rotate session moi, retry
8. **max_redirects=3**: fail nhanh cho SP bi redirect loop (thay vi 30 redirects)
9. **Skip ngay** (khong retry): loi JSON parse va redirect loop — SP bi xoa, retry vo ich

---

## Uoc tinh thoi gian

| Buoc | Thoi gian code | Thoi gian chay | Trang thai |
|------|---------------|----------------|------------|
| Step 1: Test API | 30 phut | 5 phut | HOAN THANH |
| Step 2: Categories | 30 phut | 5 phut | HOAN THANH |
| Step 3: Scraper | 2-3 gio | - | HOAN THANH |
| Step 4: Test 1 category | - | ~2 phut | HOAN THANH |
| Step 4b: Re-scan + report | 30 phut | ~1 phut | HOAN THANH |
| Step 4c: Test OVER_CAP | 1 gio | ~2 phut | HOAN THANH |
| Step 4d: Adaptive Slicing + Sort Fallback | 2 gio | ~10 phut test | HOAN THANH |
| Step 5: Scale full (VPS + local) | - | ~14-20 gio | HOAN THANH (49/49, 79,382 SP) |
| Step 5b: Convert Kaggle CSV→JSONL | 30 phut | <1 phut | HOAN THANH (6 files, 41,603 SP) |
| Step 6: Tien xu ly du lieu | 1 gio | 30 phut | CHUA LAM |

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

**Toi uu hoa (2026-04-08): Thread-local session + skip JSON retry**

2 thay doi trong `scraper.py`:
1. **Thread-local session reuse** — moi worker tai su dung 1 session thay vi tao moi moi request (tiet kiem TLS handshake)
2. **Skip retry cho loi JSON parse** — SP bi xoa/redirect tra ve HTML thay JSON, retry khong giup gi → bo qua ngay (tiet kiem ~15s/SP loi)

Benchmark (Tivi, 49 SP, workers=3):

| Phien ban | Toc do | Thoi gian |
|-----------|--------|-----------|
| Truoc toi uu | 2.9 SP/s | 16s |
| Sau toi uu | 3.4 SP/s | 14s |

Tang ~17% tren data sach. Tren data thuc (6% SP loi), cai thien lon hon do tiet kiem retry.

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
| So categories | 15-20 parent categories | 49 sub-categories (vuot gioi han 2000/query) |
| Output folder | `data/raw/` | `Tiki_dataset_scrape/` |
| Category breadcrumb | Full breadcrumb (gom ten SP) | Toi da 3 cap, bo ten SP |
| Listing limit | 100/page | 40/page (an toan hon) |
| Muc tieu | 60K+ | 100K+ (49 sub-categories, thuc te ~60-80K SP do nhieu SP bi xoa) |
| Detail fetching | Sequential (1 request/luc) | Concurrent (N workers song song) |
| DETAIL_DELAY | 0.5-1.5s | 0.3-0.8s (per worker) |
| BATCH_SLEEP | 3s moi 50 req | 2s moi 100 req |
| Toc do | 0.8 SP/s | 2.7 SP/s (3 workers), ~4.5 SP/s (5 workers) |
| Listing strategy | 1 query/sub-category | Price-Range Slicing cho sub >2000 SP |
| Moi truong chay | WSL2 local | VPS thue (IP VN) + WSL2 local (song song) |
| Session management | Tao moi moi request | Thread-local reuse, rotate moi 500 req |
| Error handling | Retry tat ca loi 3 lan x 5s | Skip ngay JSON/redirect, retry chi mang/429 |
| Category resume | Chay lai listing khi resume | Skip toan bo category da complete |


---

## Van de da phat hien

### OVER_CAP 2000 SP/query (2026-04-07)

Listing API cap ket qua o 2000 SP/query (50 pages x 40 items). 27/122 sub-categories bi anh huong.
Tong mat ~200K SP neu khong xu ly.

**Test thuc te (sub 1951, Dung cu nha bep, 14,478 SP):**
- Baseline: chi lay duoc 2,000/14,478 SP (14%)
- Price-Range Slicing: lay duoc 13,935/14,478 SP (96%) — **phuong an tot nhat**
- Sort Rotation: ~35-48% coverage
- Sub-Sub Drilling: 82% coverage

**Giai phap da chon:** Adaptive Price-Range Slicing + Sort Rotation Fallback.
- Tang 1: Chia khoang gia, recursive chia doi khi >2000 SP
- Tang 2: Sort Rotation fallback khi khoang gia <1,000 VND ma van >2000 SP
- Chi tiet: xem `HUONG_DAN_VUOT_CAP_2000.md` (muc "Phuong an cuoi cung")

---

### Van de moi phat hien (2026-04-08)

**Ty le SP thuc te thap hon uoc tinh:**
- Tiki API bao total cao nhung nhieu SP da bi xoa/redirect
- Category 8214: uoc tinh 79K → listing 19K → saved ~5K (chi ~6% uoc tinh)
- Category 8039: 1,006 listing → 594 saved (59%)
- Category nho (dien lanh, suc khoe): 50-80% saved — tot hon
- **Uoc tinh tong thuc te: ~60-80K SP** (thay vi 281K theo API)

**Nguyen nhan:**
- Nhieu seller nho tren Tiki, SP bi xoa lien tuc
- Categories cong nghe/phu kien co ty le xoa cao nhat
- Categories dien lanh/bach hoa on dinh hon

---

*Cap nhat: 2026-04-09 — Step 5 + Kaggle convert DONE. 120,985 SP (54 files). Chuyen sang tien xu ly.*
