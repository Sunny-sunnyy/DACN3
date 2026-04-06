# Plan: Fix Amazon Search - Thay Brave MCP bang curl_cffi truc tiep

**Date:** 2026-04-05 (updated 2026-04-06)
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

**Pipeline moi (da kiem chung):**

| Step | Phuong phap | Thuc te |
|------|-------------|---------|
| 1. Init | curl_cffi session + POST set ZIP 96150 | ~0.5s |
| 2. Search + Filter | GET search page -> parse HTML -> loc on_sale | ~1.5s |
| 3. Scrape features | Approach A (specs tu search page) hoac B (GET product page) | ~0s (A) hoac ~2-3s/product (B) |
| **Tong** | | **~2s (Approach A), ~14s (Approach B)** |

---

## Phases

### Phase 0: Diagnostic — DONE

**File:** `diagnostic.py`

**Ket qua:**

| Test | Ket qua |
|------|---------|
| Homepage | 202 OK (redirect nhe) |
| Search page | 200, 22 products, 1.4s, KHONG CAPTCHA |
| Product page | 200, co #productTitle + #feature-bullets + price |
| ZIP code 96150 | Set thanh cong qua POST API (isValidAddress: 1) |
| Search after ZIP | 22 products, ZIP 96150 hien thi trong page |
| Chrome impersonate | chrome, chrome120, chrome131 deu OK. Safari bi block 503 |

**Ket luan:** curl_cffi truy cap duoc CA search page + product page Amazon tu WSL2. Khong can Playwright fallback.

---

### Phase 1+2: Search + Filter + Scrape — DONE

**File:** `buoc1_search.py`

**Pipeline 3 ham chinh:**

| Ham | Chuc nang |
|-----|-----------|
| `init_amazon_session()` | Tao curl_cffi session (impersonate Chrome) + POST set ZIP 96150 |
| `search_amazon(session, keyword)` | GET search page, parse product cards, return list[dict] |
| `search_filter_scrape_amazon(keyword, max_results)` | Pipeline gop: init -> search -> filter on_sale -> scrape features -> return list[ScrapedAmazonDeal] |

**HTML parsing (da xac nhan voi search_page_sample.html):**

| Field | Selector / Source |
|-------|-------------------|
| ASIN | `div[data-component-type="s-search-result"][data-asin]` |
| Title | `h2[aria-label]` (day du), fallback `img.s-image[alt]` neu title < 20 chars |
| Current price | `span.a-price[data-a-size="xl"] > span.a-offscreen` |
| List price | `span.a-price[data-a-strike="true"] > span.a-offscreen` |
| On sale | `list_price > current_price` |
| Specs | `div[data-cy="product-details-recipe"]` -> label:value pairs |
| Brand | Tu specs ("Brand: X") hoac tu product page `#bylineInfo` |
| URL | `https://www.amazon.com/dp/{ASIN}` |

**Approach A vs B (tu dong chon):**

| Approach | Khi nao | Toc do | Features |
|----------|---------|--------|----------|
| A: Search page only | Specs >= 50 chars (electronics, laptop, phone) | ~0s them | Display Size, RAM, Disk, OS, Brand |
| B: GET product page | Specs < 50 chars (headphones, accessories) | ~2-3s/product | #feature-bullets (500-1500 chars) + #bylineInfo |

**Fix da ap dung:**
- Title: `h2 aria-label` thay vi `h2 > span` (tranh bi cat ngan). Them fallback `img.s-image alt`
- Brand: Extract tu specs block ("Brand: X") hoac tu product page `#bylineInfo`
- Sponsored prefix: Tu dong bo "Sponsored Ad - " khoi title

**Ket qua test (3 keywords):**

| Keyword | Products | On sale | Time | Approach |
|---------|----------|---------|------|----------|
| laptop gaming | 22 | 8-10 | **~2s** | A (specs du) |
| headphones | 22 | 16-18 | **~14s** | B (khong co specs) |
| samsung galaxy | 22 | 6-8 | **~2s** | A (specs du) |

---

### Phase 3: Full Pipeline Test — DONE

**File:** `buoc1.ipynb`

**Pipeline:** Amazon search (curl_cffi) -> UnifiedScrapedDeal -> GPT-5-mini select top 5 -> EnsembleAgent estimate

| Step | Time | Result |
|------|------|--------|
| Step 1+2: Search + Filter + Scrape | **~2s** | 10 sale products (Approach A) |
| Step 3: Select top 5 (GPT-5-mini) | **12.8s** | 5 deals |
| Step 4: Estimate (EnsembleAgent) | **65.0s** | 5 opportunities |
| **Total** | **~80s** | |

**Ket qua:**
- 2/5 deals la Good Deal (discount 19-31%)
- 3/5 deals la Overpriced — do san pham moi (RTX 5070/5080) chua co nhieu data trong ChromaDB. Khong phai loi pipeline.
- UnifiedScrapedDeal.from_amazon() hoat dong dung
- Khong CAPTCHA, khong loi

**So sanh voi pipeline cu:**

| Metric | Cu (Brave MCP + Playwright) | Moi (curl_cffi) | Giam |
|--------|---------------------------|-----------------|------|
| Search | ~60-70s | ~1s | **98%** |
| Filter | ~70s | ~0s (parse HTML) | **100%** |
| Scrape | ~40s | ~1s (Approach A) | **97%** |
| **Tong S+F+S** | **~170s** | **~2s** | **99%** |

---

### Phase 4: Integration (cap nhat code chinh) — DONE

**Chi thuc hien SAU KHI Phase 3 test OK.** -> Phase 3 da OK.

**Quyet dinh (2026-04-06):**
- Parallel BestBuy + Amazon: `ThreadPoolExecutor` (ca 2 deu sync curl_cffi)
- Scanner: dung `MultiSourceScannerAgent` (GPT-5-nano, chon top 3 tu pool chung)
- `AmazonScannerAgent`: XOA (khong can, MultiSourceScannerAgent da chon tu pool chung)
- `AmazonSearchAgent`: XOA (khong con dung Brave MCP)
- `max_results`: 6 cho ca BestBuy va Amazon (truoc BestBuy la 10)
- UI (`search_key.py`): CHUA SUA — se lam sau de cho user chon BestBuy/Amazon/Both

| File | Thay doi |
|------|----------|
| `price_agents/amazon_deals.py` | Xoa toan bo Playwright code. Them `init_amazon_session()`, `search_amazon()`, `parse_search_results()`, `scrape_product_page()`, `search_filter_scrape_amazon()` tu `buoc1_search.py`. Giu `ScrapedAmazonDeal` (them method `describe()`) |
| `price_agents/amazon_scanner_agent.py` | Xoa toan bo code, giu deprecation notice |
| `price_agents/multi_source_planning_agent.py` | Re-enable Amazon import. Them `_amazon_pipeline()`. Dung `ThreadPoolExecutor` chay BestBuy + Amazon song song. max_results=6 |
| `multi_source_framework.py` | Default max_urls: 10 -> 6 |
| `search_key.py` | Default max_urls: 10 -> 6, UI text cap nhat multi-source |

**Files KHONG can sua:**
- `bestbuy_untils/unified_deal.py` — `from_amazon()` da co san, hoat dong dung
- `bestbuy_untils/multi_source_scanner_agent.py` — Da doi sang GPT-5-nano, chon top 3
- `price_agents/deals.py` — Data models khong doi
- `price_agents/bestbuy_deals.py` — Khong sua (max_results truyen tu pipeline, khong dung default)

**Ket qua test_integration.py (commit `c98733d`):**

| Test | Ket qua |
|------|---------|
| Amazon standalone | 6 deals, 2.3s, Approach A |
| BestBuy standalone | 2 deals, 6.9s |
| Parallel (ThreadPoolExecutor) | 8 deals, 6.0s (nhanh hon sequential 9.2s) |
| UnifiedScrapedDeal conversion | 8 unified deals, BestBuy + Amazon OK |

**Ghi chu:** Amazon deals co Brand: N/A (specs khong co field "Brand:" cho laptop gaming). Khong anh huong pipeline.

### Success Criteria (Phase 4)
- [x] test_integration.py 4/4 tests PASSED
- [ ] `uv run search_key.py` chay thanh cong (chua test Gradio UI)
- [ ] Pipeline BestBuy + Amazon hoan thanh < 2 min
- [ ] Ket qua hien thi dung tren Gradio UI

---

## File Structure

```
segment4/test_chuc_nang/fix_amazon_v2_s2/
    plan_amazon.md             -- Ke hoach (file nay)
    diagnostic.py              -- Phase 0: DONE - curl_cffi OK, ZIP OK
    buoc1_search.py            -- Phase 1+2: Search + Filter + Scrape
    buoc1.ipynb                -- Phase 3: DONE - Full pipeline test
    test_integration.py        -- Phase 4: DONE - 4 tests (standalone + parallel + unified)
    search_page_sample.html    -- HTML mau (laptop gaming search page)
    Amazon_scraping_docs/      -- Tai lieu tham khao
```

---

## Execution Order

```
Phase 0 (Diagnostic)           -- DONE: curl_cffi OK, ZIP OK, khong CAPTCHA
    |
Phase 1+2 (Search + Filter + Scrape) -- DONE: 2s (Approach A), 14s (Approach B)
    |
Phase 3 (Full Pipeline Test)   -- DONE: 80s tong, GPT-5-mini + EnsembleAgent OK
    |
Phase 4 (Integration)         -- DONE: commit c98733d, test_integration 4/4 PASSED, chua test Gradio UI
```

---

## Key Risks (cap nhat)

| Risk | Muc do | Thuc te |
|------|--------|---------|
| Amazon CAPTCHA/block curl_cffi | ~~Cao~~ | **Khong xay ra** - Chrome impersonate OK |
| HTML structure thay doi | Trung binh | Da xac nhan selectors voi HTML thuc te |
| ZIP code setting qua curl_cffi | ~~Trung binh~~ | **OK** - POST API tra ve isValidAddress: 1 |
| Product page bi block (giong BestBuy) | ~~Cao~~ | **Khong xay ra** - Product page accessible |
| Rate limiting sau N requests | Thap | Chua gap (chi 10-20 requests/session) |
| Brand thieu khi dung Approach A | Thap | Specs co "Brand:" cho 1 so category, title chua brand name |

---

## Luu y ky thuat

- `curl_cffi` (impersonate='chrome') la BAT BUOC — safari, safari_ios bi block 503
- Homepage GET tra ve 202 (redirect), nhung session van lay duoc cookies
- ZIP code: POST `https://www.amazon.com/gp/delivery/ajax/address-change.html` voi data `locationType=LOCATION_INPUT&zipCode=96150`
- Sale detection: `span.a-price[data-a-strike="true"]` chua list price (gia goc)
- Title: uu tien `h2[aria-label]`, fallback `img.s-image[alt]` khi title < 20 chars
- Sponsored products: tu dong bo prefix "Sponsored Ad - " khoi title
- MIN_FEATURES_LEN = 50 chars: nguong chuyen tu Approach A sang B
