# Step 1 Fix: BestBuy Filter

**Date:** 2026-04-04
**Branch:** claudedev
**Status:** DONE - Test thanh cong

---

## Problem

BestBuy product pages (`/product/...`) khong truy cap duoc tu WSL2 Ubuntu. Tat ca cac phuong phap deu fail (requests, Playwright, curl, httpx - tong cong 12+ methods).

## Root Cause

**HTTP/2 protocol incompatibility giua WSL2 virtual network va BestBuy/Akamai CDN.**

- `curl_cffi` cho error ro nhat: `HTTP/2 stream was not closed cleanly: INTERNAL_ERROR (err 2)`
- Chi anh huong `/product/` URLs - search pages, category pages, APIs deu OK
- KHONG phai do response size (category page 1.89MB load binh thuong)
- `requests`, `httpx`, `curl` command deu bi block vi TLS fingerprint khong giong Chrome
- Force HTTP/1.1 -> product page timeout (CDN khong serve HTTP/1.1 cho product pages)

## Solution

Dung `curl_cffi` (impersonate Chrome) + BestBuy internal APIs thay vi scrape product pages.

**Pipeline 3 buoc:**

| Step | API | Data | Time |
|------|-----|------|------|
| 1. Search | GET `/site/searchpage.jsp?st=<keyword>` | Parse Apollo SSR cache -> lay danh sach `skuId` (dang so) | ~3s |
| 2. Price (batch) | GET `/api/3.0/priceBlocks?skus=SKU1,SKU2,...` | brand, name, currentPrice, regularPrice, savingsAmount, onSale | ~2s |
| 3. Features (per SKU) | GET `/api/v2/product/<skuId>` | features[].title + features[].description, URL (links.seoPdpUrl.href) | ~0.5s/SKU |

**5 fields can thiet:**

| Field | Source |
|-------|--------|
| title | priceBlocks `sku.names.short` |
| brand | priceBlocks `sku.brand.brand` |
| price | priceBlocks `sku.price.currentPrice` |
| features | v2 `features[].title: features[].description` (noi dung nut "Features", KHONG phai "About this item") |
| url | v2 `links.seoPdpUrl.href` (URL sach, khong co openbox/refurbished) |

## Test Result

File: `buoc1.py` - keyword: "laptop"

```
Total time: ~10s
Products found: 107 SKUs from Apollo cache
With price data: 12 (priceBlocks API)
On sale: 9
Features: 9/9 co features
URL: 9/9 co URL sach
```

Moi deal tra ve day du: title, brand, price, features, url. Vi du:

```
title:    Dell - Plus 2-in-1 16" 2K Touch Screen Laptop - Intel Core Ultra 7...
brand:    Dell
price:    $779.99 (was $1099.99, save $320.0)
features: Stunning function in every mode: Experience seamless productivity...
url:      https://www.bestbuy.com/product/dell-plus-copilot-pc-16-2k-2-in-1-.../J3K4L6XF7K
```

## Luu y ky thuat

- `curl_cffi` (impersonate='chrome') la BAT BUOC - cac library khac deu bi block tu WSL2
- Phai goi `/?intl=nosplash` truoc moi session de lay cookies va bypass country selection
- SKU phai la dang so (VD: `6615731`), KHONG phai slug (VD: `JJGGLH7HXW`)
- priceBlocks ho tro batch (nhieu SKU/request), v2 chi 1 SKU/request
- Mot so SKU co the inactive -> priceBlocks tra ve error, can skip

## Next Step

Integrate vao `bestbuy_deals.py` - thay the `filter_sale_urls()` (dung requests, bi block) bang pipeline moi dung curl_cffi + APIs.
