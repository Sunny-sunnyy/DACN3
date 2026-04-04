# Error Report: search_key.py

**Date:** 2026-03-23
**Branch:** claudedev

---

## Test Run 1 (User - keyword: "laptop" -> "Lenovo gaming laptop")

- Step 1: BestBuy 10 URLs, Amazon 10 URLs
- Step 2 BestBuy: 10/10 timeout -> 0 sale items
- Step 2 Amazon: set_amazon_us_location() FAILED lan 1 -> gia VND/N/A. OK lan 2 (scrape)
- Ket qua: 2 san pham, gia VND bi parse thanh USD -> discount -$16,812,516 (vo nghia)

## Test Run 2 (User - keyword: "Phone" -> "Samsung smartphone")

Timing (tu [TIMER] logs):
| Step | Thoi gian | Ket qua |
|------|-----------|---------|
| Init agents | 16.9s | OK |
| Generate questions | 13.8s | OK |
| Build refined query | 6.7s | OK |
| Step 1: Search | 73.0s | BB: 10 URLs, AZ: 8 URLs |
| Step 2: Filter | 172.9s | BB: 0/10 (all timeout), AZ: 6/8 sale |
| Step 3-4: Scrape+Combine | 41.4s | 6 products, gia USD chinh xac |
| Step 5: Select | 29.1s | 5 deals |
| Step 6: Estimate | 45.7s | 5 opportunities |
| **Total pipeline** | **375.9s (6.3 min)** | |

Ket qua: Amazon hoat dong tot (set_amazon_us_location OK, gia USD chinh xac). Best deal: Galaxy S25 $476 -> Est $939 = Discount $463.

---

## Fix Applied

| Fix | File | Change |
|-----|------|--------|
| Timeout too short | multi_source_planning_agent.py:119-122 | `timeout=120` -> `timeout=600` |
| Timing logs | multi_source_planning_agent.py + multi_source_framework.py | Them `[TIMER]` cho moi step |

---

## Error 1: BestBuy bi block hoan toan (CRITICAL)

**File:** `price_agents/bestbuy_deals.py` — `is_on_sale()` / `filter_sale_urls()`

**Hien tuong:** Tat ca BestBuy URLs deu fail voi:
```
HTTPSConnectionPool(host='www.bestbuy.com', port=443): Read timed out. (read timeout=10)
```
- Test Run 1: 10/10 timeout
- Test Run 2: 10/10 timeout
- Ket qua: 0 sale items -> BestBuy hoan toan khong hoat dong

**Nhan xet cua user:** Da kiem tra thu cong — nhieu san pham BestBuy CO giam gia that su, nhung do bi block nen `requests.get()` khong lay duoc trang -> khong the check sale status -> tat ca bi skip. Khong chi filter bi loi ma ca scrape cung khong the thuc hien duoc. 2 thang truoc van chay on dinh, co the BestBuy da cap nhat anti-scraping.

**Nguyen nhan:** `filter_sale_urls()` dung `requests.get()` (Python requests library). BestBuy block request nay (co the do: IP Vietnam, thieu headers/cookies, hoac anti-bot moi).

**De xuat fix:**
1. Chuyen sang Playwright cho BestBuy (giong Amazon) — kha nang vuot anti-bot cao hon
2. Hoac them proper headers (User-Agent, Accept, Referer, cookies)
3. Tang read timeout tu 10s len 30s
4. Them retry logic voi backoff

**Anh huong:** Waste 100-170s cho 10 requests timeout. Mat toan bo nguon BestBuy.

---

## Error 2: Amazon set_amazon_us_location() khong stable (MEDIUM - da tot hon)

**File:** `price_agents/amazon_deals.py` — `set_amazon_us_location()`

- Test Run 1: FAILED ("Could not find location elements") -> gia VND/N/A
- Test Run 2: OK ca 2 lan (filter + scrape) -> gia USD chinh xac

**Phan tich:** Ham nay co ve khong on dinh — luc hoat dong luc khong, phu thuoc vao timing cua Amazon page load. Khi fail -> hau qua nghiem trong (gia VND bi parse thanh USD).

**De xuat fix:**
1. Them retry logic (thu lai 3 lan neu fail)
2. Verify sau khi set: check text "Deliver to" da chuyen sang US chua
3. Neu van fail sau 3 lan -> raise exception thay vi tiep tuc voi gia sai

---

## Error 3: Gia VND bi parse thanh USD (CRITICAL - xay ra khi Error 2 fail)

**File:** `price_agents/amazon_deals.py`, line 390-393

```python
price_text = price_info.get("sale_price", "$0")  # co the la "VND49,862,029"
price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
price = float(price_match.group())  # -> 49862029.0 (nghi la USD!)
```

**Hien tuong (Test Run 1):**
- Lenovo Legion Pro 7i: gia $49,862,029 (that ra la 49,862,029 VND ~ $1,994 USD)
- Lenovo LOQ: gia $16,813,368 (that ra la 16,813,368 VND ~ $672 USD)
- Best deal: $16,813,368 -> Est $851 = Discount -$16,812,516 (hoan toan sai)

**De xuat fix:**
1. Check currency symbol truoc khi parse: chi chap nhan `$` hoac `USD`
2. Validate price range: san pham dien tu thuong $50-$10,000
3. Skip san pham neu gia khong hop ly

---

## Error 4: Brave Search tra ve URL sai (LOW)

**Test Run 2, line 91:**
```
Error checking https://www.SAMSUNG-Smartphone-Processor-ProScaler-Manufacturer/dp/B0DYVMVZSY
net::ERR_NAME_NOT_RESOLVED
```

Brave Search tra ve URL voi domain sai (`www.SAMSUNG-Smartphone-...` thay vi `www.amazon.com/...`). Day la loi tu OpenAI Agent khi extract URL tu search results.

**De xuat fix:** Validate URL format truoc khi su dung (phai bat dau bang `https://www.amazon.com/`).

---

## Error 5: Worker thread khong co error handling (MEDIUM)

**File:** `search_key.py`, line 124-128

Khong co `try/except`. Neu exception xay ra -> Gradio UI treo "Processing..." mai mai.

---

## Performance Analysis (Test Run 2 - thanh cong)

| Step | Thoi gian | % Total | Bottleneck? |
|------|-----------|---------|-------------|
| Init agents | 16.9s | 4.5% | SentenceTransformer + PyTorch load |
| Generate questions | 13.8s | 3.7% | OpenAI API (1 call) |
| Build refined query | 6.7s | 1.8% | OpenAI API (1 call) |
| **Step 1: Search** | **73.0s** | **19.4%** | **MCP server startup + Brave API** |
| **Step 2: Filter** | **172.9s** | **46.0%** | **BestBuy timeout waste (100s) + Amazon Playwright** |
| Step 3-4: Scrape | 41.4s | 11.0% | Playwright per product |
| Step 5: Select | 29.1s | 7.7% | GPT-5-mini |
| Step 6: Estimate | 45.7s | 12.2% | 5 x (LiteLLM + Specialist + Frontier + Neural) |
| **TOTAL** | **375.9s (6.3 min)** | 100% | |

**Top bottleneck:** Step 2 Filter chiem 46% thoi gian, trong do ~100s la waste do BestBuy timeout.

---

## Summary

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 0 | CRITICAL | Timeout too short (120s) | FIXED -> 600s |
| 1 | CRITICAL | BestBuy bi block (requests timeout) | Open — SP co sale nhung khong lay duoc |
| 2 | MEDIUM | Amazon location khong stable | Open — Test Run 2 OK nhung Test Run 1 fail |
| 3 | CRITICAL | Gia VND parse thanh USD | Open — xay ra khi Error 2 fail |
| 4 | LOW | Brave Search tra ve URL sai | Open |
| 5 | MEDIUM | Worker thread khong co error handling | Open |
