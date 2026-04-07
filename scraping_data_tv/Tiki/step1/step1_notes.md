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
    00_test_tiki_api.py        # Test script
    step1_notes.md             # File nay
    data/raw/
        test_listing_response.json    # Raw listing response
        test_detail_278218808.json    # Raw detail response
```
