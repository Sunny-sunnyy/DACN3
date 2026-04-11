# Bach Hoa Scraping Plan — Bo sung category "Bach Hoa"

**Ngay tao:** 2026-04-11
**Cap nhat:** 2026-04-11 20:20
**Muc tieu:** Cao 5-10K SP tu trang FMCG → bo sung "Bach Hoa" (hien co 4,284 SP trong sample)
**Output format:** JSONL (title, price, features, brand, category)
**Category map:** Tat ca → "Bach Hoa"
**Reference scraper:** `hasaki_scraper.py` (pattern thanh cong: JSON API, ThreadPoolExecutor, per-category JSONL)

---

## TRANG THAI HIEN TAI

| # | Trang | Trang thai | SP | Do kho | Uu tien |
|---|---|---|---|---|---|
| ~~1~~ | ~~**FujiMart** (fujimart.vn)~~ | **BO — KHONG CO GIA** | 0 | N/A | ~~P1~~ |
| 2 | **WinMart** (winmart.vn) | **DONE** — 3,232 SP scraped | 3,232 | THAP | **P1** |
| 3 | **BachHoaXanh** (bachhoaxanh.com) | CHUA BAT DAU — can API discovery | 0 | CAO | P2 |
| 4 | **CoopMart** (cooponline.vn) | CHUA BAT DAU — SPA React | 0 | TRUNG BINH | P3 |

---

## KET QUA KHAO SAT THUC TE (2026-04-11)

### FujiMart — BO
- WordPress HTML tinh, de parse nhat
- **NHUNG: Tat ca SP hien thi "Lien he" thay vi gia**
- Day la site catalog, KHONG CO GIA ONLINE
- **Ket luan: Khong dung duoc cho price prediction dataset**

### WinMart — API DA TIM DUOC (17:00)

**Phuong phap:** DevTools > Network tab > Fetch/XHR > navigate category page

**API Base:** `https://api-crownx.winmart.vn/it/api/web/v3/`

**Endpoint chinh — Category Listing:**
```
GET /it/api/web/v3/item/category
    ?orderByDesc=true
    &pageNumber={page}
    &pageSize={size}         # da test: 8, 40 deu work
    &slug={category-slug}    # VD: rau-cu-trai-cay--c02
    &storeCode=1535
    &storeGroupCode=1998
```

**Endpoint phu — Related Products:**
```
GET /it/api/web/v3/item/related
    ?PageNumber={page}
    &PageSize={size}
    &itemNo={item_no}
    &mch5={mch5_code}
    &storeCode=1535
    &storeGroupCode=1998
```

**Headers bat buoc:**
```
authorization: Bearer          # token RONG — khong can auth
x-api-merchant: WCM            # BAT BUOC
origin: https://winmart.vn
referer: https://winmart.vn/
accept: application/json
```

**Ket qua test:**
- /item/related: DA TEST THANH CONG tu server (25 SP, PageSize=40)
- /item/category: DA TEST THANH CONG tu browser (149 SP, pageSize=8)
- /item/category: **BI TIMEOUT tu server WSL** (khong phai IP VN)
- **=> CAN CHAY SCRAPER TU MAY CO IP VIET NAM**

**Data quality:** RAT TOT
- `name`: ten day du
- `price` / `salePrice`: gia goc va gia khuyen mai
- `brandName`: thuong hieu
- `shortDescription` + `longDescription`: mo ta ngan + dai (HTML)
- `mch1`-`mch5`: 5 cap category hierarchy
- `categoryName`: ten category
- `barcode`, `uom` (don vi tinh: KG, Goi, Thung, Chai...)

### BachHoaXanh — CAN NGHIEN CUU TIEP
- curl OK (200, 87K HTML chars)
- Nhung HTML shell rong — **KHONG CO san pham trong HTML goc** (JS-rendered)
- Khong tim thay gia, link SP, ten SP tu static HTML
- Can API discovery qua browser DevTools (Network tab) hoac Playwright
- BHX thuoc MWG → thuong co API `/ajax/` hoac `/api/`
- Claim 15,000+ SP → dataset lon nhat

### CoopMart — CHUA KHAO SAT
- curl OK (200), SPA React
- Can API discovery qua DevTools

---

## PHUONG AN THUC HIEN

### WinMart (P1 — DA XONG)
1. ~~Liet ke tat ca category slugs~~ → 92 slugs tu sitemap.xml, dung 18 parent slugs
2. ~~Viet `winmart_scraper.py`~~ → DONE (test/report/scrape modes)
3. ~~CHAY TU MAY LOCAL~~ → DA CHAY OK tu WSL (khong bi timeout)
4. Output: 18 JSONL files, 3,232 SP → da copy sang Tiki_dataset_scrape/
5. **CATEGORY_MAP da fix:** them "Thuc pham" + "Phi thuc pham" → "Bach Hoa"

### BachHoaXanh (P2)
- **Phuong an uu tien:** DevTools API discovery (giong da lam voi WinMart)
- Mo browser, F12, Network, Fetch/XHR, navigate category → tim JSON endpoint
- Neu khong co API: Playwright headless

### CoopMart (P3)
- Tuong tu BachHoaXanh — DevTools API discovery truoc

---

## JSONL Output Schema

Giong Tiki pipeline (de `day1_data_curation.py` tu dong load):

```json
{
  "title": "Nuoc mam Chin Su Huong Ca Hoi Chai 500ml",
  "price": 35000,
  "features": "Nuoc mam Chin Su huong ca hoi chai 500ml. Chat luong dam da...",
  "brand": "Chin Su",
  "category": "Bach Hoa Online > Gia Vi > Nuoc Mam"
}
```

**Luu y FMCG:**
- **features se NGAN** (~50-200 chars) so voi my pham Hasaki (~2000 chars) — CHAP NHAN
- San pham bach hoa thuong chi co: ten, gia, dung tich, xuat xu
- **Gia THAP** hon: range 5,000 - 500,000 VND (trung binh ~50K)
- Brand thuong co (Chin Su, Vinamilk, Omo, Sunlight...)

**Luu y WinMart cu the:**
- Co ca `price` (gia goc) va `salePrice` (gia KM) — **dung `price` cho dataset**
- Don vi tinh `uom`: KG, G1 (Goi), T (Thung), Chai... — **BO don vi Thung (ban si)**
- `longDescription` la HTML — can strip tags
- `quantity` la ton kho — khong can

---

*Cap nhat: 2026-04-11 21:30. WinMart DONE (3,232 SP). FujiMart BO. BachHoaXanh/CoopMart TAM DUNG — du lieu hien tai du (Bach Hoa 8,137 raw, 5,538 trong sample). Co the quay lai neu Day 2-4 cho thay can them.*
