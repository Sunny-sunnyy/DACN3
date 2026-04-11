# E-Commerce Sites Scraping Plan

**Ngay tao:** 2026-04-11
**Cap nhat:** 2026-04-11
**Muc tieu:** Cao du lieu tu 10 trang TMDT Viet Nam → bo sung cho 9 categories muc tieu
**Uu tien:** Hasaki + Cocolux (thay Cocoshop) → "Lam Dep - Suc Khoe"
**Output format:** JSONL (giong Tiki pipeline: title, price, features, brand, category)

## TRANG THAI HIEN TAI

| Phase | Trang | Trang thai | SP | Ghi chu |
|---|---|---|---|---|
| **P1a** | **Hasaki** | **DONE** | **11,410** | 128/130 categories, 0 blocks, 3 workers |
| P1b | Cocolux | Chua bat dau | 0 | Thay Cocoshop (da chet) |
| P2 | BiboMart, ConCung, KidsPlaza | Chua bat dau | 0 | |
| P3 | CoopMart, WinMart, BachHoaXanh, FujiMart | Chua bat dau | 0 | |

### Hasaki — Ket qua thuc hien (2026-04-11)

**Scraper:** `scrap/hasaki_scraper.py` (280 dong)
**Huong dan:** `scrap/HUONG_DAN_CAO_DU_LIEU_HASAKI.md`

**Cach hoat dong:**
1. Goi `HOME_API` → lay tat ca 130 leaf categories tu menu tree (de quy)
2. Cho moi category, goi `LISTING_API` voi pagination → lay danh sach product IDs
3. Cho moi product ID, goi `PRODUCT_API` → lay detail JSON
4. Build `features` = `short_description` + `attribute_show[]` + `description` (HTML → text)
5. Ghi JSONL: `{title, price, features, brand, category}`

**Ky thuat:**
- **ThreadPoolExecutor** cho concurrent workers (thread-local sessions)
- **Rate limiting**: 0.3s/request/worker
- **HTML entity decoding**: `html.unescape()` cho tieng Viet dung dau
- **Retry**: 3 lan voi backoff cho 429/500/502/503

**Benchmark (may i5-11400H, 7.6GB RAM):**

| Workers | Toc do (SP/s) | Uoc tinh 10K SP |
|---|---|---|
| 1 | 1.4 | ~2 gio |
| 3 | 3.7 | ~45 phut |
| 5 | ~5-6 | ~30 phut |

**Chat luong output (test 50 SP tu "Sua Rua Mat"):**
- 50/50 SP thanh cong (0 errors)
- Features trung binh: ~2,300 chars (rat dai, chat luong tot)
- Price range: 59,000 - 2,144,000 VND
- Brand: 100% co (Martiderm, L'Oreal, Obagi...)
- HTML entities decoded dung (tieng Viet co dau)

---

## 1. Tong quan

### 1.1. Van de hien tai

Code scraper co san (`e-commerce-sites-scraping/websites/`) **THIEU 2 truong quan trong**:
- **features / description**: Khong lay mo ta san pham → khong the dung cho price prediction
- **price**: Mot so scraper (BiboMart, ConCung) khong lay gia

Scraper hien tai chi lay: `product_name, image, cat_l0-l3, barcode, brand, manufacturer, capacity, effect, price, source, href`

→ **Can viet lai scraper** de lay them `features` (mo ta san pham) va dam bao co `price`.

### 1.2. Nghien cuu API/HTML

#### Hasaki (hasaki.vn) — JSON API, KHONG CAN SELENIUM

| Thong tin | Chi tiet |
|---|---|
| **Category API** | `https://hasaki.vn/wap/v2/master/?page=newHeaderHome` → `cate_menu[]` |
| **Listing API** | `https://hasaki.vn/wap/v2/catalog/category/get-listing-product?cat={id}&p={page}&product_list_limit=12&more_data=1&lstType=1&lstId=0` |
| **Product API** | `https://hasaki.vn/wap/v2/product/detail?id={id}` |
| **Features co san?** | Co — `description` (HTML) + `short_description` + `attribute_show[]` |
| **Brand co san?** | Co — `brand.name` |
| **Price co san?** | Co — `price` (VND, int) |
| **Anti-bot** | Thap — dung requests.Session la du |
| **Uoc tinh SP** | ~10,000-15,000 SP (8 parent categories, ~100 sub-categories) |
| **Tech** | Pure JSON API (requests) |

**Hasaki `cate_menu` gom 8 parent categories:**
1. My Pham High-End
2. Cham Soc Da Mat (~70 sub-cats)
3. Trang Diem (~30 sub-cats)
4. Cham Soc Toc va Da Dau (~20 sub-cats)
5. Cham Soc Co The (~15 sub-cats)
6. Nuoc Hoa (~5 sub-cats)
7. Cham Soc Ca Nhan (~25 sub-cats)
8. Thuc Pham Chuc Nang (~15 sub-cats)

→ Tat ca map vao **"Lam Dep - Suc Khoe"**

#### Cocolux (cocolux.com) — thay the Cocoshop (da chet)

| Thong tin | Chi tiet |
|---|---|
| **URL pattern** | `https://cocolux.com/danh-muc/{slug}-i.{id}` |
| **Listing** | HTML rendering — co pagination |
| **Product page** | HTML — co mo ta, brand, gia |
| **Features co san?** | Can kiem tra — thuong co mo ta san pham trong tab "Mo ta" |
| **Anti-bot** | Thap — HTML tinh, co the dung requests |
| **Uoc tinh SP** | ~5,000-10,000 SP (10+ categories) |
| **Luu y** | Product listing co the dung JavaScript render → can test requests truoc, fallback Selenium |
| **Tech** | Requests + BeautifulSoup (hoac Selenium neu can) |

**Cocolux gom 10 parent categories:**
1. Son Moi (Lips)
2. Trang Diem (Makeup)
3. Cham Soc Da (Skincare)
4. Dung Cu (Tools/Brushes)
5. Mascara
6. Nuoc Hoa (Perfume)
7. Cham Soc Co The (Bodycare)
8. Cham Soc Toc (Haircare)
9. My Pham High-End
10. Thuc Pham Chuc Nang

→ Tat ca map vao **"Lam Dep - Suc Khoe"**

### 1.3. 10 trang TMDT (khong co TopCV)

| # | Trang | Category map | Tech hien tai | Uoc tinh SP | Uu tien |
|---:|---|---|---|---:|---|
| 1 | **Hasaki** | Lam Dep - Suc Khoe | JSON API (requests) | 10-15K | **P1** |
| 2 | **Cocolux** (thay Cocoshop) | Lam Dep - Suc Khoe | Requests + BS4 | 5-10K | **P1** |
| 3 | **BiboMart** | Me va Be | Requests + BS4 | 3-5K | P2 |
| 4 | **ConCung** | Me va Be | Requests + BS4 | 5-8K | P2 |
| 5 | **KidsPlaza** | Me va Be | Selenium + Requests | 5-8K | P2 |
| 6 | **CoopMart** | Bach Hoa | Selenium | 3-5K | P3 |
| 7 | **WinMart** | Bach Hoa | Selenium (infinite scroll) | 5-8K | P3 |
| 8 | **BachHoaXanh** | Bach Hoa | Selenium | 5-8K | P3 |
| 9 | **FujiMart** | Bach Hoa | Requests | 1-2K | P3 |
| 10 | **ThiTruongSi** | Bach Hoa (B2B) | JSON API (requests) | 3-5K | P4 (thap) |

---

## 2. Ke hoach thuc hien

### Phase 1: Hasaki + Cocolux (1-2 ngay) — HIEN TAI

**Muc tieu:** Cao 10-20K SP my pham → bo sung "Lam Dep - Suc Khoe" (hien co ~10K tu Tiki)

#### 1a. Hasaki Scraper (viet moi)

**Vi sao viet moi thay vi sua code cu?**
- Code cu dung codebase rieng (`CSV_write`, `Session`, `PROJECT_PATH` imports)
- Can output JSONL (khong phai CSV)
- Can lay `features` (description) — code cu khong lay
- Code cu cu, khong co type hints, khong co error handling tot

**File moi:** `scrap/hasaki_scraper.py`

**Pipeline:**
```
1. Get categories tu API → list[dict]
2. Cho moi category:
   a. Listing API → lay tat ca product IDs (pagination)
   b. Product Detail API → lay: name, price, brand, description, attributes
   c. Build JSONL row: {title, price, features, brand, category}
   d. Ghi vao file JSONL
3. Rate limiting: 0.5s/request, retry 3 lan
```

**Fields can lay tu Hasaki Product API:**
- `name` → title
- `price` → price (VND, int)
- `brand.name` → brand
- `description` (HTML) → features (strip HTML tags)
- `short_description` → features (bo sung)
- `attribute_show[]` → features (bo sung: barcode, xuat xu, nsx...)
- Category tu listing step → category

**Cach xay dung `features`:**
```python
parts = []
if short_description:
    parts.append(strip_html(short_description))
for attr in attribute_show:
    parts.append(f"{attr['label']}: {attr['val']}")
if description:
    parts.append(strip_html(description))
features = " | ".join(parts)
```

#### 1b. Cocolux Scraper (viet moi)

**File moi:** `scrap/cocolux_scraper.py`

**Pipeline:**
```
1. Get categories tu homepage HTML (hoac hardcode danh sach)
2. Cho moi category:
   a. Listing page → lay tat ca product URLs (pagination)
   b. Product page → parse: name, price, brand, description
   c. Build JSONL row
   d. Ghi vao file JSONL
3. Rate limiting: 1s/request
```

**Luu y Cocolux:**
- Listing page co the render bang JS → can test requests truoc
- Neu JS required → dung Selenium headless
- Product page thuong co tab "Mo ta san pham" → parse HTML

#### 1c. Convert & Merge

**Output folder:** `scrap/data/`
**File naming:** `hasaki_{date}.jsonl`, `cocolux_{date}.jsonl`

**JSONL schema (giong Tiki):**
```json
{
  "title": "Son Kem Black Rouge Air Fit Velvet Tint",
  "price": 185000,
  "features": "Xuat xu: Han Quoc | Thuong hieu: Black Rouge | Dung tich: 4.5g | Son kem li mien man huong popcorn...",
  "brand": "Black Rouge",
  "category": "Làm Đẹp - Sức Khỏe > Trang Điểm > Son Kem"
}
```

**Sau khi cao xong:**
- Copy JSONL files vao `Tiki/Tiki_dataset_scrape/` (de `day1_data_curation.py` load duoc)
- Them mapping trong `CATEGORY_MAP` cho categories tu Hasaki/Cocolux

### Phase 2: Me va Be (BiboMart, ConCung, KidsPlaza) — 1-2 ngay

**Muc tieu:** Cao 5-15K SP → bo sung "Me va Be" (hien co ~6K tu Tiki)

Scraper cu co san nhung THIEU:
- `price` (BiboMart, ConCung chi lay name + brand)
- `features` / `description`

→ Can sua `scrap_data()` de:
1. Vao product page → parse price + mo ta san pham
2. Output JSONL thay vi CSV

### Phase 3: Bach Hoa (CoopMart, WinMart, BachHoaXanh, FujiMart) — 2-3 ngay

**Muc tieu:** Cao 5-15K SP → bo sung "Bach Hoa" (hien co ~6K tu Tiki)

**Do kho cao hon:**
- CoopMart, WinMart dung Selenium (infinite scroll)
- BachHoaXanh dung Selenium
- FujiMart dung Requests

**Luu y:** San pham bach hoa thuong co mo ta ngan → features se ngan hon my pham.

### Phase 4: ThiTruongSi (tuy chon)

**Muc tieu:** 3-5K SP si le → ho tro Bach Hoa

**Luu y:** Gia si khac gia le → can xem xet co phu hop cho price prediction khong.

---

## 3. Tieu chi thanh cong

### 3.1. Tieu chi ky thuat

| # | Tieu chi | Muc tieu | Cach do |
|---:|---|---|---|
| 1 | **JSONL output** | Dung schema: title, price, features, brand, category | Validate bang script |
| 2 | **Features length** | >= 100 chars trung binh | Thong ke tu JSONL |
| 3 | **Price valid** | 100% items co price > 0 (VND) | Count items voi price <= 0 |
| 4 | **Dedup** | < 5% trung lap trong cung nguon | Check duplicates by title |
| 5 | **Error rate** | < 5% loi khi cao | Log errors, count total |

### 3.2. Tieu chi du lieu

| Phase | Trang | Muc tieu SP | Category map |
|---|---|---:|---|
| P1 | Hasaki | >= 5,000 | Lam Dep - Suc Khoe |
| P1 | Cocolux | >= 2,000 | Lam Dep - Suc Khoe |
| P2 | BiboMart + ConCung + KidsPlaza | >= 5,000 | Me va Be |
| P3 | CoopMart + WinMart + BachHoaXanh + FujiMart | >= 5,000 | Bach Hoa |
| **Tong** | **10 trang** | **>= 17,000** | |

### 3.3. Tieu chi tich hop

- [ ] JSONL files co the load boi `day1_data_curation.py` khong loi
- [ ] Category mapping trong `CATEGORY_MAP` da cap nhat
- [ ] Re-run Day 1 pipeline thanh cong voi data moi
- [ ] EDA cho thay cac categories yeu da tang

---

## 4. Cach kiem tra (Testing)

### 4.1. Test tung scraper (truoc khi chay full)

```bash
# Test Hasaki: cao 1 category, 5 SP max
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --test --max 5

# Kiem tra output
head -5 scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_test.jsonl | python3 -m json.tool
```

**Kiem tra cho moi SP:**
1. `title` — co noi dung, khong rong
2. `price` — > 0, la so nguyen (VND)
3. `features` — >= 50 chars, co mo ta co nghia
4. `brand` — co ten thuong hieu (co the rong cho SP khong brand)
5. `category` — dung format "Parent > Sub"

### 4.2. Validate JSONL sau khi cao xong

```bash
# Script validate
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/validate_jsonl.py \
    scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_*.jsonl
```

**Validate script se kiem tra:**
- JSON valid (moi dong parse duoc)
- Required fields: title, price, features, brand, category
- Price range: 1,000 - 50,000,000 VND
- Features length: >= 50 chars
- Duplicates by title
- In ra: tong SP, trung binh features length, phan phoi price, % missing fields

### 4.3. Tich hop test (sau khi merge vao Tiki data)

```bash
# Copy JSONL vao Tiki_dataset_scrape
cp scraping_data_tv/e-commerce-sites-scraping/scrap/data/*.jsonl \
   scraping_data_tv/Tiki/Tiki_dataset_scrape/

# Re-run Day 1 pipeline
uv run scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py
```

**Kiem tra:**
- Tong items tang (tu ~143K len ~160K+)
- Category "Lam Dep - Suc Khoe" tang (tu ~10K len ~15K+)
- EDA charts cap nhat dung
- Khong co loi parse/loading

---

## 5. Chung minh ket qua

### 5.1. Bao cao sau moi Phase

- **So luong:** Bao nhieu SP da cao thanh cong
- **Chat luong:** Trung binh features length, % missing fields
- **Phan phoi:** Gia trung binh, min, max cho tung category
- **So sanh:** Truoc va sau khi them data moi (EDA charts)

### 5.2. EDA sau khi merge

- **Bieu do Category Distribution:** So sanh truoc/sau
- **Bieu do Price Distribution:** Kiem tra phan phoi gia co bi lech khong
- **Bieu do Text Length:** Kiem tra features length co du dai khong

### 5.3. Validation metrics

| Metric | Muc tieu | Thuc te |
|---|---|---|
| Tong SP moi | >= 17,000 | ? |
| Features avg length | >= 200 chars | ? |
| Price valid rate | >= 99% | ? |
| Dedup rate | < 5% | ? |
| Day 1 pipeline load OK | Yes | ? |

---

## 6. Folder structure

```
e-commerce-sites-scraping/
    scrap/
        e-commerce-plan.md          # File nay
        hasaki_scraper.py           # Hasaki scraper moi (JSONL output)
        cocolux_scraper.py          # Cocolux scraper moi (JSONL output)
        validate_jsonl.py           # Script kiem tra JSONL quality
        data/                       # Output JSONL files
            hasaki_2026-04-11.jsonl
            cocolux_2026-04-11.jsonl
    websites/                       # Code cu (tham khao)
        hasaki.py
        cocoshop.py
        bibomart.py
        ...
```

---

## 7. Uoc tinh thoi gian

| Phase | Cong viec | Code | Chay scraper | Tong |
|---|---|---|---|---|
| **P1** | Hasaki + Cocolux | 3-4 gio | 4-6 gio | **1-2 ngay** |
| P2 | BiboMart + ConCung + KidsPlaza | 2-3 gio | 3-5 gio | 1-2 ngay |
| P3 | CoopMart + WinMart + BachHoaXanh + FujiMart | 3-5 gio | 5-8 gio | 2-3 ngay |
| P4 | ThiTruongSi | 1 gio | 1-2 gio | 0.5 ngay |
| **Tong** | | | | **~5-8 ngay** |

---

*Cap nhat: 2026-04-11. Phase 1: Hasaki + Cocolux. Tieu chi: JSONL output voi features/description, tich hop vao Day 1 pipeline.*
