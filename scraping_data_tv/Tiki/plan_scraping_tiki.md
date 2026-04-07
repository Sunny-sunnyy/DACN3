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
    Docs/                          # Tiki Open API docs
    Github/                        # 5 repos tham khao
    Tiki_dataset_1/                # Kaggle 41.6K (thoi trang)
    step1/                         # Thu nghiem API
        00_test_tiki_api.py        # Test thu 2 API endpoints
        step1_notes.md             # Ghi chep ket qua
        data/raw/                  # Raw JSON responses
    tiki_scraper/                  # Code chinh (tao sau khi step1 OK)
        models.py                  # Pydantic: TikiProduct
        scraper.py                 # Orchestrator: listing -> filter -> detail -> save
        config.py                  # Categories, price range, delays
    data/
        raw/                       # Raw JSONL per category
        cleaned/                   # Sau khi clean
        final/                     # Train/val/test splits
    checkpoints/                   # Scraping progress (resume khi bi ngat)
```

---

## Implementation Steps

### Step 1: Thu nghiem API (DANG LAM)
**File:** `step1/00_test_tiki_api.py`

Thu goi 2 API endpoints, xem:
- Co tra ve data khong? Bi block khong?
- Response format nhu the nao?
- Fields nao co san, fields nao thieu?
- Rate limit cua Tiki la bao nhieu?

Chi can 1 file .py don gian, chay xong thay ket qua ngay.

---

### Step 2: Lay danh sach categories
**File:** `step1/01_get_categories.py` (hoac tich hop vao scraper)

- Goi Tiki homepage hoac API de lay tat ca category IDs
- Loc categories phu hop: Dien tu, Gia dung, May tinh, Dien thoai, Phu kien...
- Loai bo categories da co trong Kaggle (thoi trang, giay dep, tui xach)

Muc tieu: ~15-20 categories, moi category ~3000-5000 san pham

---

### Step 3: Xay dung scraper chinh
**Files:** `tiki_scraper/models.py`, `tiki_scraper/scraper.py`, `tiki_scraper/config.py`

**models.py** — Pydantic model:
```python
class TikiProduct(BaseModel):
    product_id: int
    title: str
    brand: str
    price: int              # VND
    features: str           # description + specifications gop lai
    url: str
    category: str
    category_id: int
```

**config.py** — Constants:
- CATEGORIES: dict mapping category_name -> category_id
- PRICE_MIN = 50_000, PRICE_MAX = 50_000_000
- LISTING_DELAY = (1.0, 2.0)   # delay giua cac listing pages
- DETAIL_DELAY = (0.5, 1.5)    # delay giua cac detail requests
- BATCH_SLEEP_EVERY = 50       # sleep them 3s moi 50 requests
- MAX_RETRIES = 3

**scraper.py** — Pipeline:
1. Listing API: lay het product IDs tu 1 category (paginate cho den khi het)
2. Filter: bo san pham ngoai khoang gia, khong co brand
3. Detail API: lay full info cho tung san pham
4. Save: append JSONL + checkpoint moi 100 san pham
5. Resume: doc checkpoint, bo qua product IDs da cao

---

### Step 4: Test voi 1 category (~1000 san pham)

Chay thu 1 category (vd: "tai nghe") tren WSL2.

Kiem tra:
- [ ] Data dung format? title, brand, price, features, url deu co?
- [ ] Price dung (VND, khong can chia 100K nhu Shopee)?
- [ ] Features du dai (>100 chars)?
- [ ] URL hop le?
- [ ] Checkpoint hoat dong (resume duoc)?
- [ ] Khong bi block sau 1000 requests?

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
3. **Random delays**: 1-2s listing, 0.5-1.5s detail
4. **Batch sleep**: sleep 3s moi 50 requests (giong Repo 3)
5. **Checkpoint + resume**: save progress, resume neu bi ngat
6. **Session rotation**: tao session moi moi 500 requests (phong truoc)
7. **Neu bi 429/403**: doi 5 phut, retry voi session moi

---

## Uoc tinh thoi gian

| Buoc | Thoi gian code | Thoi gian chay |
|------|---------------|----------------|
| Step 1: Test API | 30 phut | 5 phut |
| Step 2: Categories | 30 phut | 5 phut |
| Step 3: Scraper | 2-3 gio | - |
| Step 4: Test 1 category | - | 1-2 gio |
| Step 5: Scale full | - | 20-48 gio |
| Step 6: Merge | 1 gio | 30 phut |

**Tong code:** ~4-5 gio
**Tong chay (WSL2 test):** ~2 gio
**Tong chay (full scale):** ~20-48 gio (tren may thue)

---

## Dependencies

Tat ca da co trong project: `curl_cffi`, `pydantic`, `tqdm`. Khong can them package moi.
