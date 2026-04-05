# Step 1 Fix: BestBuy Filter

**Date:** 2026-04-04
**Branch:** claudedev
**Status:** DONE - Full pipeline test thanh cong

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
| 1. Search | GET `/site/searchpage.jsp?st=<keyword>` | Parse Apollo SSR cache -> lay danh sach `skuId` (dang so) | ~4s |
| 2. Price (batch) | GET `/api/3.0/priceBlocks?skus=SKU1,SKU2,...` | brand, name, currentPrice, regularPrice, savingsAmount, onSale | ~2s |
| 3. Features + URL (per SKU) | GET `/api/v2/product/<skuId>` | features[].title + features[].description, URL (links.seoPdpUrl.href) | ~0.5s/SKU |

**5 fields can thiet:**

| Field | Source |
|-------|--------|
| title | priceBlocks `sku.names.short` |
| brand | priceBlocks `sku.brand.brand` |
| price | priceBlocks `sku.price.currentPrice` |
| features | v2 `features[].title: features[].description` (noi dung nut "Features", KHONG phai "About this item") |
| url | v2 `links.seoPdpUrl.href` (URL sach, khong co openbox/refurbished) |

## Test Results

### buoc1.py - Unit test (chi Step 1-3)

Keyword: "laptop" | Time: ~10s | 9 sale products | 9/9 co features + URL sach.

### buoc1.ipynb - Full pipeline (GPT-5-mini)

| Step | Time | Result |
|------|------|--------|
| Step 1: Search | 3.5s | 118 SKUs |
| Step 2: Filter (priceBlocks) | 1.8s | 5 on sale / 12 total |
| Step 3: Scrape (v2 API) | 3.3s | 5/5 features + URL |
| Step 4: Select top 5 (GPT-5-mini) | **22.9s** | 5 deals |
| Step 5: Estimate (EnsembleAgent) | 51.5s | 5 opportunities |
| **Total** | **~83s** | |

### buoc1a.ipynb - Optimized pipeline (Cerebras + gop Step 2+3)

Thay doi so voi buoc1.ipynb:
- Step 2+3 gop lai: phat hien sale -> scrape features ngay (1 vong lap)
- Step 4: Cerebras (`openrouter/openai/gpt-oss-120b`) thay GPT-5-mini

| Step | Time | Result |
|------|------|--------|
| Step 1: Search | 4.0s | 136 SKUs |
| Step 2+3: Filter + Scrape (gop) | **4.0s** | 7 sale products |
| Step 4: Select top 5 (Cerebras) | **16.6s** | 5 deals |
| Step 5: Estimate (EnsembleAgent) | 49.7s | 5 opportunities |
| **Total** | **~74s** | |

**So sanh Step 4:**
- GPT-5-mini (OpenAI truc tiep): 22.9s
- Cerebras (OpenRouter): 16.6s (-27%)

## Files

| File | Muc dich |
|------|----------|
| `buoc1.py` | 3 functions: `search_bestbuy()`, `get_price_blocks()`, `get_product_details()` |
| `buoc1.ipynb` | Full pipeline test voi GPT-5-mini |
| `buoc1a.ipynb` | Optimized pipeline: gop Step 2+3, Cerebras thay GPT-5-mini |
| `diagnostic.py` | Script chan doan network (7 methods) |

## Luu y ky thuat

- `curl_cffi` (impersonate='chrome') la BAT BUOC - cac library khac deu bi block tu WSL2
- Phai goi `/?intl=nosplash` truoc moi session de lay cookies va bypass country selection
- SKU phai la dang so (VD: `6615731`), KHONG phai slug (VD: `JJGGLH7HXW`)
- priceBlocks ho tro batch (nhieu SKU/request), v2 chi 1 SKU/request
- Mot so SKU co the inactive -> priceBlocks tra ve error, can skip
- Cerebras goi qua `litellm.acompletion()` (async), response_format nam trong `extra_body`

## Integrated (2026-04-05)

Da tich hop vao code chinh (commit `ef9084c`):

| File | Thay doi |
|------|----------|
| `bestbuy_deals.py` | Xoa `requests`/`BeautifulSoup`/`Playwright`. Them `search_bestbuy()`, `get_price_blocks()`, `get_product_details()`, `search_filter_scrape_bestbuy()` (gop 3 buoc) |
| `multi_source_planning_agent.py` | Bo `BestBuySearchAgent` (Brave MCP). Pipeline 6 buoc -> 4 buoc. Amazon tam an |
| `multi_source_scanner_agent.py` | Chuyen GPT-5-mini (OpenAI) -> Cerebras (`openrouter/openai/gpt-oss-120b`) via LiteLLM |
| `multi_source_framework.py` | Bo clarification |
| `search_key.py` | Bo UI 3 cau hoi. Chuyen `gr.Dataframe` -> `gr.HTML` (URL clickable) |
| `gradio_helpers.py` | Them `opportunities_to_html()` voi link clickable |

**Ket qua chay thuc te:** Pipeline hoan thanh trong **95.7s (1.6 min)** — giam tu 375.9s (6.3 min)
