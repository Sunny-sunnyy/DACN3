# Step 1: Thu nghiem Tiki API v2

**Ngay:** 2026-04-07
**Muc tieu:** Test 2 API endpoints cua Tiki, xac nhan co lay duoc data khong.
**Ket qua:** THANH CONG — ca 2 API deu tra ve data day du, khong bi block.

---

## Ket qua test

### Test 1: Listing API — 200 OK

```
GET https://tiki.vn/api/v2/products?category=8594&limit=10&page=1&include=advertisement&aggregations=1
```

- Status: 200
- Tra ve 10 san pham dung yeu cau
- Fields co san: id, name, price, brand_name, url_path, discount, rating, quantity_sold
- Paging: `total=2000`, `last_page=200` (toi da 10K+ san pham/category)
- KHONG can login, KHONG can token dac biet

### Test 2: Detail API — 200 OK

```
GET https://tiki.vn/api/v2/products/278218808
```

- Status: 200
- description: 2717 chars (HTML format)
- specifications: co (brand, origin, attributes)
- short_description: co
- breadcrumbs: category hierarchy day du
- url_path: co

### Test 3: Pagination — Hoat dong

- 3 pages lien tiep (page 1, 2, 3), moi page 40 san pham
- Tong: 120 san pham, khong bi block
- Paging info nhat quan giua cac pages

---

## Fields mapping

| Field can | API field | Source |
|-----------|-----------|--------|
| title | `name` | Listing + Detail |
| brand | `brand_name` (Listing) hoac `brand.name` (Detail) | Ca 2 |
| price | `price` | Ca 2 (don vi VND, KHONG can chia 100K) |
| features | `description` + `specifications` | Chi co trong Detail API |
| url | `https://tiki.vn/{url_path}` | Ca 2 |

---

## Luu y ky thuat

- `curl_cffi` voi `impersonate="chrome"` + User-Agent header la du
- Price la VND truc tiep (khac Shopee phai chia 100K)
- Description la HTML, can strip tags khi clean
- Listing API `limit` toi da 100 (da test 10 va 40, deu OK)
- Listing API `total` cap o 2000 (du lieu thuc co the nhieu hon, can nhieu category)
- Detail API tra ve full JSON rat chi tiet (~50+ fields)

## So sanh voi Shopee

| | Shopee | Tiki |
|---|---|---|
| curl_cffi | 403 (can JS tokens) | 200 OK |
| Selenium | Bi redirect login | Khong can |
| Anti-bot | 5 lop (JS cookies, encrypted tokens, bot detection, login wall, CAPTCHA) | Gan nhu khong co |
| Approach thanh cong | Khong co (sau 7 lan thu) | Lan thu dau tien |

---

## Files

```
step1/
    00_test_tiki_api.py        # Test 2 API endpoints
    01_get_categories.py       # Scan 24 parent categories
    02_get_subcategories.py    # Scan 122 sub-categories (~585K SP)
    03_test_scraper.py         # Test scraper pipeline (Tivi, 30 SP)
    step1_notes.md             # File nay
    data/raw/
        test_listing_response.json    # Raw listing response
        test_detail_278218808.json    # Raw detail response
        categories_scan.json          # 24 parent categories + totals
        subcategories_scan.json       # 122 sub-categories (nested)
        subcategories_flat.json       # 122 sub-categories (flat, sorted)
    data/test_output/
        tiki_5015.jsonl               # Test output: Tivi (30 SP)
        tiki_1795.jsonl               # Test output: Dien thoai Smartphone (103 SP)
```

---

## Step 2: Scan categories (da hoan thanh)

**01_get_categories.py** — Scan 24 parent categories:
- 20 categories hoat dong, tong ~32K san pham (cap o 2000/category)
- Listing API cap `total` o 2000 — so thuc nhieu hon

**02_get_subcategories.py** — Scan 122 sub-categories:
- Tong uoc tinh: ~585K san pham
- 100 sub-categories co >= 100 san pham, tong ~584K
- Sub-categories lon nhat: Sach tieng Viet (241K), Phu kien dien thoai (79K), Noi that (19K)

**Cach vuot gioi han 2000:** Listing API chi tra ve toi da 2000 san pham/query. Giai phap: query theo sub-category (nho hon) thay vi parent category. Moi sub-category co total rieng, co the paginate het.

---

## Step 3: Build scraper (da hoan thanh)

**03_test_scraper.py** — Test pipeline voi category Tivi (5015):
- 30/30 san pham, ~36 giay, khong bi block
- Data day du: title, brand, price, features (avg 5130 chars), url, category

**Scraper package** (`tiki_scraper/`):
- `models.py`: TikiProduct (Pydantic)
- `config.py`: 47 sub-categories, rate limits, headers
- `scraper.py`: listing -> filter price -> detail -> save JSONL + checkpoint

---

## Step 4: Full category test (da hoan thanh)

**Test: Dien thoai Smartphone (1795) — 103 san pham:**
- 103/103 san pham, ~2 phut 17 giay (~1.3s/SP)
- Price range: 210,000 - 40,990,000 VND
- Features avg: 3,379 chars
- Brands: Xiaomi (39), Samsung (31), OPPO (13), Apple (7), Realme (5), Vivo (5), Tecno (1), OnePlus (1), Nokia (1)
- Khong bi block sau 103 requests lien tuc
- Checkpoint va resume hoat dong

**Thay doi so voi plan ban dau:**
- Category breadcrumb: lay toi da 3 cap, bo ten san pham o cuoi (truoc do lay full breadcrumb)
- Output folder: `Tiki_dataset_scrape/` (thay vi `data/raw/`)
- Listing limit: dung 40/page (thay vi 100, an toan hon)

---

## Ket luan

Tiki API v2 hoat dong on dinh, khong co anti-bot dang ke. Scraper san sang de scale len 100K+ san pham. Buoc tiep theo: chay `run_scraper.py --all` tren may thue de cao toan bo 47 sub-categories.
