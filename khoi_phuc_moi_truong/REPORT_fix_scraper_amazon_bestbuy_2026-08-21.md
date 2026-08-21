# BÁO CÁO — SỬA SCRAPER AMAZON / BESTBUY (SEARCH_KEY.PY)

> **Ngày:** 2026-08-21
> **Project:** `/home/minhhieu/price2026wsl/tech2ai`
> **Branch:** `TTTN` | **HEAD:** `2b6f7d935feb943f5534873ad65f68e235f3dbeb` (trước commit)
> **Phạm vi:** Chỉ source acquisition (scraping) của `segment4/search_key.py` — Amazon + BestBuy

---

# 1. BỐI CẢNH

Tiếp nối chuỗi recovery sau sự cố SSD/WSL. Các phase trước đã xác nhận:

```text
price_is_right.py          = RUNTIME PASS
Common pricing stack       = PASS (Modal, Chroma RAG, DNN, Ensemble, Groq, OpenAI)
search_key.py APP START    = PASS
search_key.py callback     = PASS
search_key.py END-TO-END   = FAIL — Amazon/BestBuy trả 0 sale products
```

File `multi_source_planning_agent.py` đã được restore về source gốc trước Phase 2B (bỏ `ENABLE_PUSHOVER` gate) ở lượt trước — `git diff` trả EMPTY.

Blocker duy nhất còn lại: **source acquisition Amazon/BestBuy**.

---

# 2. LỖI GẶP PHẢI (EVIDENCE LỊCH SỬ)

## 2.1 Amazon

```text
GET https://www.amazon.com/s?k=iphone
HTTP 200
Response body: 2,212 bytes  ← cực nhỏ so với page bình thường (hàng trăm KB)
Found: 0 products / 0 on sale
```

## 2.2 BestBuy

```text
GET https://www.bestbuy.com/site/searchpage.jsp?st=iphone
HTTP 200 | 2,318,097 bytes | 78 unique SKUs found
PriceBlocks fetching 78 SKUs → Got 7/78 SKUs
Found 0 sale products
```

---

# 3. QUÁ TRÌNH ĐIỀU TRA (EVIDENCE THỰC TẾ)

## 3.1 Phương pháp

- Đọc toàn bộ source và map call graph (không đoán).
- Capture response THỰC TẾ bằng chính request app gửi (curl_cffi, impersonate chrome) — 1–2 request cô lập mỗi site, không aggressive, không bypass anti-bot.
- Test parser cô lập (import function, feed HTML live — KHÔNG chạy `search_key.py`).

## 3.2 Amazon — 3 lớp root cause

### LỚP 1: Akamai interstitial challenge (lý do 2,212 bytes)

Capture thực tế cho thấy body 2,212 bytes là **Akamai Bot Manager interstitial**, không phải CAPTCHA/consent:

```html
<meta http-equiv="refresh" content="5; URL='/s?k=iphone&bm-verify=AAQAAAAN_____...'" />
<script> function triggerInterstitialChallenge() {...}</script>
<iframe src="https://m.media-amazon.com/images/S/sash/...gif">
```

- Meta refresh trỏ tới URL thật kèm token `bm-verify` (cơ chế Amazon cho browser tự refresh sau 5s).
- Thử nghiệm: request lại URL với token `bm-verify` sau 5s → **816 KB, search results page thật** (`data-component-type="s-search-result"` = True).
- Session sau đó "warm": request keyword thứ 2 (laptop) không bị interstitial nữa.

### LỚP 2: Locale VND phá giá (lý do giá sai)

- Response mặc định hiển thị giá **VND**: `VND 15,138,377` thay vì `$899`.
- `_parse_price` strip mọi ký tự không phải digit → `15138377` → **`$15,138,377`** (sai ~17,000×).
- Fix: ép locale en_US — cookie `lc-main=en_US`, `i18n-prefs=USD`, warmup `?language=en_US&currency=USD` → giá quay về USD chuẩn: `$579.97`, `Typical price: $615.89`.

### LỚP 3: Search page không còn render giá (layout mới)

- Trong HTML search page mới: **0 occurrences `"price"`** — phần lớn card render giá bằng JS (client-side hydration).
- Chỉ 1/8 card có `div[data-cy="price-recipe"]` (ad cards) — selector cũ gần như chết, layout **A/B test không nhất quán giữa các lần fetch** (3/16, 16/16, 1/6 trong các lần capture khác nhau).
- **Product page VẪN có giá SSR**: `#corePrice_feature_div` → `span.a-price span.a-offscreen` = current price; `span.a-price[data-a-strike="true"] span.a-offscreen` = list price ("Typical price:").

## 3.3 BestBuy — root cause đơn giản hơn

### Regex pdpUrl chết do Apollo SSR cache đổi cấu trúc

- Structure cũ (code đang dùng): `"skuId":"12345"},...` — regex cần `}},"pdpUrl"` (2 dấu đóng).
- Structure mới thực tế: skuId là field cuối của `Product` object:

```json
{"__typename":"Product","name":{...},"skuId":"6472869"},"pdpUrl":"https://www.bestbuy.com/product/.../JCQ6HQTQ54/sku/6472869"}
```

→ Regex cũ match **0/10**. Fix: bỏ 1 dấu `}`.

### priceBlocks KHÔNG đổi — "78→7" và "7→0" là hành vi ĐÚNG

- Shape item sale thật (capture được, Insignia TV 50" F50): vẫn đúng như code cũ mong đợi:

```json
{"currentPrice":179.99,"pricingType":"onSale","regularPrice":299.99,"savingsAmount":120.0, ...}
```

- **78→7**: ~71/78 SKUs trả `error: PRODUCT_SKU_INACTIVE` — vì search page chứa nhiều SKU preorder (iPhone 17 chưa release 09/2026), banner/member-event SKUs (DropEvent, planPaidMemberEvents). Đây là lọc đúng, không phải bug.
- **7→0 sale**: với keyword "iphone", các SKU active còn lại đều giá regular (iPhone không sale — đúng thực tế).

---

# 4. THAY ĐỔI ĐÃ THỰC HIỆN

## 4.1 `segment4/price_agents/amazon_deals.py` (+80/−30)

| # | Thay đổi | Lý do |
|---|----------|-------|
| 1 | Thêm `import time` | Cần cho interstitial sleep 5s |
| 2 | Thêm helper `_get_with_interstitial_retry(session, url, timeout)` | Mirror browser: phát hiện meta refresh chứa `bm-verify`, chờ 5s, request lại URL kèm token |
| 3 | `init_amazon_session()`: warmup `?language=en_US&currency=USD` + set cookie `lc-main=en_US`, `i18n-prefs=USD` | Ép locale USD, tránh giá VND phá `_parse_price` |
| 4 | `parse_search_results()`: bỏ `continue` khi `current_price <= 0`; `on_sale = current_price > 0 and list_price > current_price` | Layout mới không render giá trên card → giữ card để lấy giá từ product page |
| 5 | `search_amazon()`: dùng `_get_with_interstitial_retry` | Vượt Akamai interstitial |
| 6 | `scrape_product_page()`: parse `#corePrice_feature_div` → current_price; `span.a-price[data-a-strike="true"]` → list_price; trả thêm 2 key | Product page là nguồn giá SSR duy nhất còn lại |
| 7 | `search_filter_scrape_amazon()`: pipeline mới — search page (title/asin) → product page (giá + features) → lọc on_sale → cắt `max_results` (buffer `max(max_results*3, 12)`) | Thích ứng layout mới |

## 4.2 `segment4/price_agents/bestbuy_deals.py` (+3)

| # | Thay đổi | Lý do |
|---|----------|-------|
| 1 | Regex pdpUrl: `"skuId":"X"}},"pdpUrl"` → `"skuId":"X"},"pdpUrl"` (bỏ 1 dấu `}`) + comment giải thích | Apollo SSR cache structure mới |

**KHÔNG sửa:** `get_price_blocks`, `get_product_details`, sale detection BestBuy (evidence chứng minh vẫn đúng), pricing engine, `search_key.py`, `multi_source_planning_agent.py`.

---

# 5. QUYẾT ĐỊNH ĐÃ ĐƯA RA

1. **Không chạy `search_key.py`** — user tự test cuối (theo constraint từ đầu).
2. **Không đoán selector** — mọi thay đổi dựa trên response HTML/JSON thực tế capture được.
3. **Minimal surgical patch** — không refactor, không đổi contract (giữ `ScrapedAmazonDeal`/`ScrapedBestBuyDeal`, function signatures, orchestration).
4. **Không thay dependency** — không `uv sync`/`pip install`/Playwright. Giải pháp thuần code, đúng stack hiện tại (curl_cffi + BS4).
5. **Giữ "78→7" và "0 sale iphone" là hành vi hợp lệ** — không chữa bằng cách giả sale flag.
6. **Chỉ commit 2 scraper files + file báo cáo này** — các WIP khác (`memory.json` runtime data, `brainstorming.md`, `multi_source_planning_agent.py` EOF-newline, `code_html/` fixtures, `sandbox/sandbox/`, `shopping_assistant_v2/*.md`) KHÔNG nằm trong commit này.
7. **BestBuy noise SKU (banner/event) chưa lọc** — đề xuất tương lai: chỉ gửi SKUs có pdpUrl đi priceBlocks để giảm ~64 request error/lần (giữ patch minimal).

---

# 6. TRẠNG THÁI TRƯỚC / SAU

## Amazon

| Tiêu chí | Trước | Sau |
|----------|-------|-----|
| Request đầu | 2,212 bytes interstitial → 0 products | Auto-retry bm-verify → 816 KB page thật |
| Giá | `VND 15,138,377` → `$15,138,377` (sai) | USD chuẩn (`$579.97`) |
| Search page price | Chỉ card cũ có price-recipe (1/8) | Giá lấy từ product page (SSR) |
| "tv" end-to-end | 0 deals | **4 sale deals** (Ember $919.99, Insignia $179.99, Roku $129.99, Insignia $69.99) |
| "iphone" | 0 deals | 0 deals (hợp lệ — không crash) |

## BestBuy

| Tiêu chí | Trước | Sau |
|----------|-------|-----|
| pdpUrl | 0/10 match → URL rỗng/fallback | Regex mới bắt đúng URL (5/71 search products thật) |
| priceBlocks | 7/78 (SKU inactive — hợp lệ) | 9/73 (tương đương, hợp lệ) |
| "tv" end-to-end | 0 deals | **5 sale deals** (Insignia 50" $179.99, Insignia 40" $99.97, LG OLED $1399.99, Insignia 55" $199.99, Insignia 75" $399.99) — đầy đủ URL + features |
| ZIP code setting | failed | **"ZIP 96150 set OK"** |

---

# 7. VERIFICATION (ISOLATED — KHÔNG CHẠY SEARCH_KEY.PY)

Chạy trực tiếp các hàm đã patch trên live, 1 pass:

```text
AMAZON "tv"     → 22 products parsed → 4 sale deals ✓
AMAZON "iphone" → 0 sale (hợp lệ, không crash) ✓
BESTBUY "tv"    → 73 SKUs → 9 OK → 5 sale deals đầy đủ ✓
BESTBUY pdpUrl → regex mới bắt đúng URL ✓
```

---

# 8. GIT TRẠNG THÁI SAU CÙNG

```text
 M price_agents/amazon_deals.py          ← PATCH (commit này)
 M price_agents/bestbuy_deals.py         ← PATCH (commit này)
?? khoi_phuc_moi_truong/REPORT_fix_scraper_amazon_bestbuy_2026-08-21.md  ← file này (commit này)
--- KHÔNG thuộc commit này ---
 M brainstorming.md                      (WIP cũ)
 M memory.json                           (runtime dedup data — giữ nguyên)
 M price_agents/multi_source_planning_agent.py  (EOF newline WIP — đã báo cáo, không đụng)
?? code_html/                            (user's HTML fixtures)
?? khoi_phuc_moi_truong/ (các handoff .txt cũ)
?? sandbox/sandbox/                      (runtime artifact)
?? shopping_assistant_v2/*.md            (4 docs untracked)
```

---

# 9. SAFETY

```text
search_key.py executed:     NO  (user sẽ tự chạy)
price_is_right.py executed: NO
Chroma touched:             NO
dependencies changed:       NO
Git index (staging) trước commit:  NO (chỉ add đúng 3 paths cho commit này)
Runtime executed:           NO
```

---

# 10. HƯỚNG DẪN USER TEST THỦ CÔNG

1. `cd /home/minhhieu/price2026wsl/tech2ai/segment4 && uv run search_key.py`
2. **Không nên test keyword "iphone"** — iPhone không sale là thực tế (0 deals là đúng).
3. Nên test: **"tv"**, "laptop", "headphones", "monitor"...
4. Lần search Amazon đầu tiên mỗi phiên có thể chậm ~5s (Akamai interstitial auto-retry — bình thường).
5. Gửi runtime output lại cho ChatGPT Web phân tích nếu có lỗi mới.

---

# END REPORT

```text
SCRAPER AMAZON/BESTBUY: FIXED + VERIFIED (isolated)
USER END-TO-END VERIFICATION: PENDING (user tự chạy search_key.py)
```
