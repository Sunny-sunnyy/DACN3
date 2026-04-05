# Plan: Fix Amazon Search - Thay Brave MCP bang curl_cffi truc tiep

**Date:** 2026-04-05
**Branch:** claudedev
**Workflow:** Plan -> Test in .ipynb/.py -> Confirm OK -> Update into .py

---

## Problem

Amazon pipeline hien dang **disabled** (commit `566544e`). Pipeline cu:

| Step | Phuong phap | Thoi gian | Van de |
|------|-------------|-----------|--------|
| Search | Brave MCP + GPT-5-nano | ~60-70s | Spawn npx process, cham |
| Filter | Playwright (tung URL) | ~70s | Mo browser rieng, check tung trang |
| Scrape | Playwright (tung URL) | ~40s | Mo browser MOI, set location LAI |
| **Tong** | | **~170s** | |

**Muc tieu:** Search truc tiep tren amazon.com (giong da lam voi BestBuy), giam xuong <20s cho search+filter+scrape.

---

## Solution Overview

Thay toan bo Brave MCP + Playwright bang `curl_cffi` (impersonate Chrome) + parse HTML truc tiep.

**Pipeline moi (3 buoc):**

| Step | Phuong phap | Du kien |
|------|-------------|---------|
| 1. Search | GET `https://www.amazon.com/s?k=<keyword>` | ~3-5s |
| 2. Filter + Scrape | Parse HTML search page -> loc on sale -> lay details | ~0s (cung 1 response) hoac ~5-10s neu can vao product page |
| **Tong** | | **<15s (target)** |

**Tham khao:** BestBuy da fix thanh cong bang curl_cffi + 3 internal APIs (search -> priceBlocks -> v2 product). Xem `fix_bestbuy/buoc1.md`.

---

## Phases

### Phase 0: Diagnostic — curl_cffi co truy cap duoc Amazon khong?

**File:** `diagnostic.py`

**Muc dich:** Xac dinh curl_cffi co bi Amazon block khong truoc khi code gi them.

**Tests:**

| # | Test | URL | Thanh cong neu |
|---|------|-----|----------------|
| 1 | Homepage | `https://www.amazon.com` | Status 200, HTML chua `<title>Amazon.com` |
| 2 | Search page | `https://www.amazon.com/s?k=laptop` | Status 200, HTML chua `data-component-type="s-search-result"` |
| 3 | Product page | `https://www.amazon.com/dp/B0DXQK3RJK` | Status 200, HTML chua `#productTitle` |
| 4 | CAPTCHA check | Tat ca URLs | HTML KHONG chua `"/errors/validateCaptcha"` |

**Anti-bot tricks can thu:**
- Init session: GET homepage truoc -> lay cookies -> roi moi search
- Headers: `Accept`, `Accept-Language`, `Accept-Encoding`, `Referer`
- Impersonate variants: `"chrome"`, `"chrome120"`, `"chrome131"`
- Set ZIP code 96150: POST `https://www.amazon.com/gp/delivery/ajax/address-change.html`

**QUAN TRONG — Can tai lieu tham khao:**
Truoc khi bat dau Phase 0, user cung cap cac GitHub repos ve Amazon scraping (VD: cach vuot anti-bot, HTML structure, ZIP code API, headers can thiet). Dieu nay giup chon dung approach tu dau, tranh mat thoi gian thu sai.

**Ket qua co the xay ra:**
- **curl_cffi OK cho ca search + product page** -> Ly tuong, dung curl_cffi cho moi thu
- **curl_cffi OK cho search, block product page** -> curl_cffi search + Playwright/curl cho product page
- **curl_cffi bi block hoan toan** -> Chuyen sang Playwright (chi 1 lan load search page)

### Success Criteria
- [ ] Xac dinh duoc curl_cffi co truy cap duoc Amazon search page khong
- [ ] Xac dinh duoc curl_cffi co truy cap duoc Amazon product page khong
- [ ] Xac dinh duoc cach set ZIP code 96150

---

### Phase 1: Search + Filter (parse search results page)

**File:** `buoc1_search.py`

**Muc dich:** Tu keyword, lay danh sach san pham ON SALE tu search page.

**Pipeline:**

```
1. Init session (curl_cffi + cookies + ZIP 96150)
2. GET https://www.amazon.com/s?k={keyword}
3. Parse HTML:
   - Moi san pham: <div data-component-type="s-search-result" data-asin="ASIN">
   - Extract: ASIN, title, price, brand
4. Phat hien ON SALE:
   - Strikethrough price (data-a-strike="true")
   - Savings text ("Save X%", "$X off")
   - Coupon/Deal badge
   - original_price > current_price
5. Tra ve danh sach san pham on sale
```

**5 fields can lay tu search page:**

| Field | Vi tri trong HTML | Ghi chu |
|-------|-------------------|---------|
| title | `<h2>` trong search card | Day du |
| brand | Brand line duoi title | Co the co hoac khong |
| price | `span.a-price > span.a-offscreen` | Gia hien tai |
| features | Description snippet trong card | Co the NGAN, can xem thu |
| url | `https://www.amazon.com/dp/{ASIN}` | Tu data-asin |

**Luu y:** CSS selectors tren la DU KIEN, can xac nhan voi HTML thuc te tu Phase 0. Amazon thay doi HTML thuong xuyen.

### Success Criteria
- [ ] Extract 20+ san pham tu 1 trang search
- [ ] Phan biet dung sale vs non-sale
- [ ] Khong bi CAPTCHA/block

---

### Phase 2: Scrape (lay features day du)

**File:** `buoc1_scrape.py`

**Muc dich:** Voi moi san pham on sale, lay du 5 fields (dac biet la features).

**2 approaches:**

| Approach | Mo ta | Toc do | Rui ro |
|----------|-------|--------|--------|
| A: Search page only | Dung snippet tu search page lam features | Cuc nhanh (0 request them) | Features co the qua ngan |
| B: Search + Product page | GET tung product page lay `#feature-bullets` | +0.5-2s/san pham | De bi block hon |

**Quyet dinh:** Chon A hay B tuy vao:
1. Chat luong features snippet tren search page (kiem tra o Phase 1)
2. curl_cffi co truy cap duoc product page khong (kiem tra o Phase 0)

**Fallback chain (neu chon Approach B):**
1. curl_cffi GET product page -> parse `#feature-bullets ul`
2. Neu bi block -> Playwright cho product pages
3. Neu Playwright cung fail -> dung search page snippet

**Product page selectors (tu amazon_deals.py hien tai):**
- Title: `#productTitle`
- Brand: `#bylineInfo` (can clean: bo "Visit the X Store", "Brand: X")
- Features: `#feature-bullets ul` (bullet points "About this item")
- Price: da co tu search page

### Success Criteria
- [ ] 5 fields day du cho moi san pham sale
- [ ] Features >= 50 ky tu (co noi dung co nghia)
- [ ] Output: `ScrapedAmazonDeal(title, brand, price, features, url)`

---

### Phase 3: Combined Pipeline + Test

**Files:**
- `buoc1_combined.py` — Ham gop pipeline
- `buoc1.ipynb` — Test interactive trong notebook

**Function:**
```python
def search_filter_scrape_amazon(keyword: str, max_results: int = 10) -> list[ScrapedAmazonDeal]:
    """Search Amazon, filter on-sale products, scrape details.
    
    Pipeline:
    1. Init curl_cffi session + cookies + ZIP 96150
    2. GET search page, parse product cards
    3. Filter: chi giu on_sale == True
    4. Scrape features (approach A hoac B)
    5. Return list[ScrapedAmazonDeal] (max max_results items)
    """
```

**Test keywords:** "laptop", "headphones", "samsung galaxy"

**Do thoi gian tung buoc** (giong buoc1.ipynb cua BestBuy).

### Success Criteria
- [ ] >= 3 san pham sale voi du 5 fields
- [ ] Tong thoi gian < 15s
- [ ] Khong bi CAPTCHA/block
- [ ] Ket qua khop voi ket qua manual (mo browser, search cung keyword)

---

### Phase 4: Integration (cap nhat code chinh)

**Chi thuc hien SAU KHI Phase 3 test OK.**

| File | Thay doi |
|------|----------|
| `price_agents/amazon_deals.py` | Them `search_filter_scrape_amazon()` + curl_cffi functions. Giu nguyen class `ScrapedAmazonDeal` |
| `price_agents/amazon_scanner_agent.py` | Xoa `AmazonSearchAgent` (Brave MCP). Giu/chuyen `AmazonScannerAgent` sang Cerebras |
| `price_agents/multi_source_planning_agent.py` | Uncomment Amazon imports, goi `search_filter_scrape_amazon()`, chay BestBuy + Amazon |

**Files KHONG can sua:**
- `bestbuy_untils/unified_deal.py` — `from_amazon()` da co san
- `price_agents/deals.py` — Data models khong doi
- `search_key.py` — UI da ho tro multi-source

### Success Criteria
- [ ] `uv run search_key.py` chay thanh cong
- [ ] Pipeline BestBuy + Amazon hoan thanh < 2 min
- [ ] Amazon tra ve >= 3 san pham sale
- [ ] Ket qua hien thi dung tren Gradio UI

---

## File Structure

```
segment4/test_chuc_nang/fix_amazon_v2/
    plan_amazon.md         -- Ke hoach (file nay)
    diagnostic.py          -- Phase 0: curl_cffi vs Amazon anti-bot
    buoc1_search.py        -- Phase 1+2: Search + Filter + Scrape
    buoc1_combined.py      -- Phase 3: Ham gop pipeline
    buoc1.ipynb            -- Phase 3: Test interactive
    buoc1.md               -- Ghi lai ket qua (sau khi xong)
```

---

## Execution Order

```
Phase 0 (Diagnostic)           -- User cung cap GitHub repos -> test curl_cffi
    |
Phase 1 (Search + Filter)     -- Parse search page HTML
    |
Phase 2 (Scrape)              -- Lay features (approach A hoac B)
    |
Phase 3 (Combined + Test)     -- Gop pipeline, test notebook
    |
Phase 4 (Integration)         -- Cap nhat code chinh, re-enable Amazon
```

---

## Key Risks

| Risk | Muc do | Giai phap |
|------|--------|-----------|
| Amazon CAPTCHA/block curl_cffi | Cao | Fallback Playwright (1 search page load) |
| HTML structure thay doi | Trung binh | Xac nhan CSS selectors voi HTML thuc te |
| ZIP code setting qua curl_cffi | Trung binh | Tham khao GitHub repos, hoac dung Playwright cho buoc nay |
| Product page bi block (giong BestBuy) | Cao | Dung search page snippet lam features |
| Rate limiting sau N requests | Thap | Chi can 5-10 requests/session |

---

## So sanh voi BestBuy Fix

| Aspect | BestBuy | Amazon (du kien) |
|--------|---------|-------------------|
| HTTP client | curl_cffi | curl_cffi (hoac Playwright fallback) |
| Search | Internal search page -> Apollo SSR cache | Search page -> HTML parse |
| Price/Sale | priceBlocks batch API (JSON) | HTML parse (strikethrough, savings) |
| Features | v2 product API (JSON) | Product page HTML hoac search snippet |
| Anti-bot | Thap (chi can impersonate Chrome) | **Cao** (CAPTCHA, fingerprinting) |
| ZIP code | `/?intl=nosplash` | POST API hoac UI automation |
| Thoi gian | ~8s | <15s (target) |
