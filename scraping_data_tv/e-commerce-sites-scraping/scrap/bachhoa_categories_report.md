# Bach Hoa (FMCG) Categories Report

**Cap nhat:** 2026-04-11 20:20
**Trang thai:** WinMart DONE (3,232 SP). BachHoaXanh/CoopMart CHUA BAT DAU.
**Muc tieu:** Bo sung category "Bach Hoa" (hien 4,284 SP), target 8K-10K+
**Category map:** Tat ca → Bach Hoa

---

## Tong quan cac trang FMCG

| # | Trang | Trang thai | SP da cao | SP uoc tinh | Ghi chu |
|---|---|---|---:|---:|---|
| ~~1~~ | ~~FujiMart (fujimart.vn)~~ | **BO** | 0 | ~~500-1,500~~ | Khong co gia ("Lien he") |
| 2 | **WinMart** (winmart.vn) | **DONE** | 3,232 | 5,000-8,000 | JSON API, 18 categories |
| 3 | BachHoaXanh (bachhoaxanh.com) | CHUA BAT DAU | 0 | 5,000-10,000 | JS-rendered, can API discovery |
| 4 | CoopMart (cooponline.vn) | CHUA BAT DAU | 0 | 3,000-5,000 | SPA React, can API discovery |
| | **TONG** | | **3,232** | **13,000-23,000** | |

**Thu tu uu tien:** ~~WinMart (P1, DONE)~~ > BachHoaXanh (P2) > CoopMart (P3)

---

## FujiMart — BO (2026-04-11)

**Ly do:** WordPress HTML tinh — de parse nhat NHUNG **tat ca san pham hien thi "Lien he" thay vi gia**.
Site chi la catalog offline, khong co gia online. Khong dung duoc cho price prediction dataset.

**Categories da khao sat:**
- Banh va Snack: 175 SP, gia = "Lien he"  
- Dau an: 11 SP, gia = "Lien he"
- Ket luan: KHONG DUNG DUOC

---

## WinMart — API DA TIM DUOC (2026-04-11 17:00)

**Cong nghe:** Next.js SSR, backend API rieng biet tai `api-crownx.winmart.vn`
**Trang thai:** API discovery THANH CONG — san sang viet scraper

### API Discovery (qua DevTools Network tab)

**Category Listing Endpoint (CHINH):**
```
GET https://api-crownx.winmart.vn/it/api/web/v3/item/category
    ?orderByDesc=true
    &pageNumber={page}
    &pageSize={size}
    &slug={category-slug}
    &storeCode=1535
    &storeGroupCode=1998
```

**Related Products Endpoint (PHU — da test thanh cong tu server):**
```
GET https://api-crownx.winmart.vn/it/api/web/v3/item/related
    ?PageNumber={page}
    &PageSize={size}
    &itemNo={item_no}
    &mch5={mch5_code}
    &storeCode=1535
    &storeGroupCode=1998
```

### Headers bat buoc

| Header | Gia tri | Ghi chu |
|---|---|---|
| `authorization` | `Bearer` | Token rong — KHONG CAN AUTH |
| `x-api-merchant` | `WCM` | **BAT BUOC** — header rieng cua WinMart |
| `origin` | `https://winmart.vn` | CORS check |
| `referer` | `https://winmart.vn/` | CORS check |
| `accept` | `application/json` | |

### Response structure (category listing)

```json
{
  "data": {
    "name": "Rau - Cu - Trai Cay",
    "description": "<p>...</p>",
    "seoName": "rau-cu-trai-cay--c02",
    "items": [
      {
        "name": "Dua hau Hac My Nhan (Long An)",
        "price": 29900,
        "salePrice": 19900,
        "brandName": "DUA HAU",
        "shortDescription": "Dua hau Hac My Nhan",
        "description": "Dua hau Hac My Nhan (Long An)",
        "longDescription": "<h2>...</h2><p>...</p>",
        "categoryName": "Trai cay tuoi",
        "categoryCode": "MENU01173",
        "mch1": "1", "mch1Name": "Thuc pham",
        "mch2": "101", "mch2Name": "Thuc pham Tuoi song, Che bien",
        "mch3": "10106", "mch3Name": "Trai cay",
        "mch4": "1010601", "mch4Name": "Trai cay noi dia",
        "mch5": "101060108", "mch5Name": "Dua ND",
        "itemNo": "10055026",
        "barcode": "2606955000000",
        "sku": "10055026KG",
        "uom": "KG",
        "uomName": "Kg",
        "quantity": 594.584,
        "isAlcohol": false
      }
    ],
    "paging": {
      "totalCount": 149,
      "pageNumber": 1,
      "pageSize": 8,
      "totalPages": 19
    }
  }
}
```

### Map fields → JSONL output

| WinMart field | → JSONL field | Ghi chu |
|---|---|---|
| `name` | `title` | Ten san pham day du |
| `price` | `price` | Gia goc (VND) |
| `shortDescription` + `longDescription` | `features` | Strip HTML, gop lai |
| `brandName` | `brand` | Ten thuong hieu |
| `categoryName` + mch hierarchy | `category` | Map tat ca → "Bach Hoa Online > ..." |

### Luu y quan trong

1. **Slug-based**: Endpoint dung `slug` (VD: `rau-cu-trai-cay--c02`), KHONG dung mch codes
2. **storeCode=1535**: Ma cua hang cu the — co the anh huong den gia va ton kho
3. **storeGroupCode=1998**: Nhom cua hang
4. **Gia kep**: Co ca `price` (gia goc) va `salePrice` (gia khuyen mai) — dung `price` cho dataset
5. **pageSize toi da**: Can test, da xac nhan `pageSize=8` va `pageSize=40` deu work
6. **IP restriction**: API **BI TIMEOUT tu server ngoai VN** (WSL/cloud) — chi chay duoc tu mang VN hoac can VPN VN
7. **Endpoint /related**: Da test thanh cong tu server (khong bi block), nhung can `itemNo` cu the
8. **No auth token**: Header `Authorization: Bearer` (khong co token) — API public
9. **Don vi tinh**: Co `uom` (KG, G1=Goi, T=Thung...) — can loc chi lay don vi le (G1, Goi, Chai...), BO don vi Thung

### Categories da phat hien (can khao sat them)

URL pattern: `winmart.vn/{slug}--c{id}`

| Slug | ID | Name (uoc tinh) | totalCount |
|---|---|---|---:|
| `rau-cu-trai-cay--c02` | c02 | Rau - Cu - Trai Cay | 149 |
| `mi-thuc-pham-an-lien--c34` | c34 | Mi - Thuc pham an lien | ? |
| (can khao sat them) | | | |

**Can lam tiep:**
- Navigate tat ca categories tren WinMart, ghi lai slug + totalCount
- Hoac: Tim API endpoint liet ke tat ca categories (co the co `/category` endpoint)
- Test pageSize toi da (40? 100?)
- Xac nhan API chay duoc tu may local (tren mang VN)

---

## BachHoaXanh — CHUA BAT DAU

**Cong nghe:** JS-rendered (MWG / The Gioi Di Dong)
**Ket qua khao sat:**
- curl 200 OK, 87K HTML chars
- HTML goc la shell rong (khong co SP data)
- Khong tim thay gia/ten SP tu static HTML
- Can API discovery qua DevTools hoac Playwright intercept

**Categories (can khao sat qua browser):**
- Thuc pham tuoi song
- Thuc pham kho
- Gia vi, dau an
- Do uong, sua
- Banh keo, snack
- (va nhieu nhom khac...)

**Uoc tinh:** 5,000-10,000 SP (claim 15,000+ tren site)

---

## CoopMart — CHUA BAT DAU

**Cong nghe:** SPA React (CSS-in-JS)
**Categories preliminary (tu homepage):**
1. Rau cu, trai cay
2. Thit, trung, hai san
3. Thuc an che bien, bun tuoi
4. Thuc pham dong, mat
5. Sua, san pham tu sua
6. Thuc uong
7. Banh, keo, snack
8. Gia vi, gao, thuc pham kho

> Cac category BO (khong lay): San pham cho be, Cham soc ca nhan, Nha cua va doi song

**Uoc tinh:** 3,000-5,000 SP

---

## Tong ket

| Trang | Trang thai | Uoc tinh SP | Da cao | Ghi chu |
|---|---|---:|---:|---|
| ~~FujiMart~~ | BO | ~~500-1,500~~ | 0 | Khong co gia |
| **WinMart** | **DONE** | 5,000-8,000 | 3,232 | 18 categories, CATEGORY_MAP da fix |
| BachHoaXanh | CHUA BAT DAU | 5,000-10,000 | 0 | Can API discovery |
| CoopMart | CHUA BAT DAU | 3,000-5,000 | 0 | Can API discovery |
| **TONG** | | **13,000-23,000** | **3,232** | |

### Buoc tiep theo (thu tu uu tien)

1. ~~**WinMart scraper**~~ — **DONE (3,232 SP)**, da copy sang Tiki_dataset_scrape/
   - CATEGORY_MAP da fix: "Thuc pham" + "Phi thuc pham" → "Bach Hoa"
2. **BachHoaXanh** — API discovery (DevTools Network tab)
3. **CoopMart** — API discovery (DevTools Network tab)

---

*Cap nhat: 2026-04-11 21:30. WinMart DONE (3,232 SP). BachHoaXanh/CoopMart TAM DUNG — du lieu hien tai du cho Day 1 v4 (Bach Hoa 8,137 raw). Co the quay lai sau neu can.*
