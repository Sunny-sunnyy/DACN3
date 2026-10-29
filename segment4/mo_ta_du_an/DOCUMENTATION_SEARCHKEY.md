# SEARCH_KEY.PY — Multi-Source Deal Finder

**Cập nhật lần cuối:** 14:02, 29/10/2026 (đợt tối ưu: luna, chống sập, giữ ấm Modal, song song Bước 4; bổ sung cơ chế cào, song song, tối ưu, chống sập, chi phí, giới hạn — xem `docs/changelog/`)
**Ngôn ngữ:** Python 3.12 + `uv`

Ứng dụng web tìm deal tốt nhất từ **BestBuy** và **Amazon** cùng lúc. Pipeline 4 bước: cào song song (curl_cffi) → chọn
top 3 (gpt-6-luna) → ước lượng giá (ensemble 3 mô hình, chạy song song) → bảng kết quả + thông báo Pushover.

---

## Đầu vào và đầu ra

| Đầu vào | Mô tả | Ví dụ |
|---|---|---|
| Keyword | Từ khoá sản phẩm | `noise cancelling headphones`, `gaming monitor` |
| Max URLs | Số sản phẩm đang sale tối đa mỗi nguồn | 3–20 (giao diện mặc định 5) |
| Source | All / BestBuy / Amazon | All |

| Đầu ra | Mô tả |
|---|---|
| Bảng kết quả | Tối đa 3 deal: mô tả, giá sale, giá ước lượng, discount, URL |
| Status | Số deal + trạng thái từng nguồn, ví dụ `BestBuy: ok (6), Amazon: ok (6)`; lỗi pipeline cũng hiện ở đây |
| Pipeline logs | Log thời gian thực của từng bước |
| Push Notification | Tự gửi khi discount > $100 (chỉ cho link bestbuy.com / amazon.com); có nút gửi tay |

---

## Cấu trúc thư mục (phần search_key dùng)

```
segment4/
|-- search_key.py                        # ĐIỂM VÀO — Gradio UI; nạp mô hình + đánh thức Modal ở luồng nền
|-- multi_source_framework.py            # FRAMEWORK — ChromaDB, nạp agent (có khoá), gửi thông báo tay
|-- price_agents/
|   |-- multi_source_planning_agent.py   # LÕI — pipeline 4 bước, trạng thái từng nguồn, is_store_url
|   |-- bestbuy_deals.py                 # BestBuy: curl_cffi + API nội bộ
|   |-- amazon_deals.py                  # Amazon: Playwright (cookie WAF) + curl_cffi + HTML; AmazonBlockedError
|   |-- ensemble_agent.py                # 3 mô hình song song, bỏ mô hình lỗi / trả 0, chia lại trọng số
|   |-- frontier_agent.py                # gpt-6-luna (low) + RAG ChromaDB
|   |-- specialist_agent.py              # Llama-3.2-3B trên Modal: timeout, giữ ấm, wake_up_modal
|   |-- neural_network_agent.py          # PyTorch DNN chạy trên máy (có khoá khi chạy song song)
|   |-- deep_neural_network.py           # định nghĩa DNN
|   |-- preprocessor.py                  # LiteLLM viết lại mô tả (.env đang đặt groq/openai/gpt-oss-20b)
|   |-- messaging_agent.py               # Pushover + gpt-6-luna viết tin nhắn
|   |-- deals.py                         # Deal, DealSelection, Opportunity
|   |-- agent.py                         # lớp cơ sở (log màu ANSI)
|-- bestbuy_untils/
|   |-- multi_source_scanner_agent.py    # gpt-6-luna chọn top 3 theo số thứ tự; dedupe_deals
|   |-- unified_deal.py                  # chuẩn hoá deal của 2 nguồn
|   |-- gradio_helpers.py                # hàng đợi log, HTML bảng kết quả
|   |-- clarification_agent.py           # câu hỏi làm rõ (KHÔNG dùng trong pipeline)
|-- products_vectorstore/                # ChromaDB 800.000 sản phẩm (không commit)
|-- deep_neural_network.pth              # trọng số DNN (1,1 GB)
|-- khong_su_dung/                       # code cũ: amazon_scanner_agent.py, bestbuy_scanner_agent.py (Brave MCP), pricer_service2.py
```

Phần dùng chung với `price_is_right.py`: `EnsembleAgent`, `FrontierAgent`, `SpecialistAgent`, `NeuralNetworkAgent`,
`MessagingAgent`, `deals.py` — sửa ở đây là sửa luôn app 2.

---

## Thứ tự đọc code

```
1. search_key.py                    — Gradio, luồng nền preload, threading + hàng đợi log
2. multi_source_framework.py        — ChromaDB, init_agents_as_needed (có khoá), run
3. multi_source_planning_agent.py   — pipeline 4 bước (đọc kỹ)
   |-- bestbuy_deals.py / amazon_deals.py
   |-- unified_deal.py, multi_source_scanner_agent.py
   |-- ensemble_agent.py → frontier / specialist / neural_network / preprocessor
4. deals.py, agent.py
```

---

## Pipeline 4 bước

```
Mở app: luồng nền → wake_up_modal() → nạp framework + agent (~9–20 s) → giữ ấm Modal (ping mỗi 50 s)
Người dùng nhập từ khoá
    |
Bước 1: search_and_scrape()   ThreadPoolExecutor(2): _run_source("BestBuy") ‖ _run_source("Amazon")
    |                         mỗi nguồn: ok (n) / empty / blocked / error — nguồn lỗi không làm hỏng nguồn kia
Bước 2: combine()             → List[UnifiedScrapedDeal]
Bước 3: select_top_deals()    MultiSourceScannerAgent.scan(): dedupe_deals → gpt-6-luna (reasoning none)
    |                         trả deal_number + tóm tắt; code lấy giá / URL / tên gốc từ danh sách → DealSelection (≤ 3)
Bước 4: estimate_prices()     ThreadPoolExecutor: 3 deal song song; mỗi deal EnsembleAgent.price():
    |                           preprocess → [Specialist ‖ Frontier ‖ DNN] → combine (bỏ mô hình lỗi / trả 0)
    |                         deal không ước được → bỏ deal đó, các deal khác vẫn có kết quả
    v
List[Opportunity] (sắp theo discount) → nếu discount > $100 và is_store_url(url) → MessagingAgent.notify
```

---

## Chi tiết từng file

### Tầng giao diện — `search_key.py`

| Thành phần | Chức năng |
|---|---|
| `App.get_framework()` | tạo `MultiSourceFramework` một lần (khoá `threading.Lock`) |
| `App.preload()` | chạy ở luồng nền lúc mở app: `wake_up_modal()` (khối try riêng), nạp agent, `start_keep_warm()` |
| `App._run_pipeline()` | luồng worker chạy pipeline; lỗi → ô Status ghi `Error: ...` (trước 29/10 bị treo "Processing...") |
| `App.push_notification_handler()` | gửi thông báo tay cho deal ở vị trí được chọn |

### Tầng framework — `multi_source_framework.py`

| Thành phần | Chức năng |
|---|---|
| `__init__()` | `load_dotenv` (tìm `.env` ở `tech2ai/`), mở ChromaDB collection `products` |
| `init_agents_as_needed()` | tạo `MultiSourcePlanningAgent` một lần (có khoá) |
| `run(keyword, max_urls, source)` | gọi `planner.plan()` |
| `send_notification(index)` | kiểm `is_store_url`, gửi; gửi lỗi → trả chuỗi "Not sent: ..." |

### Tầng pipeline — `multi_source_planning_agent.py`

| Thành phần | Bước | Chức năng |
|---|---|---|
| `DEAL_THRESHOLD = 100` | 4 | ngưỡng tự gửi thông báo |
| `SPECIALIST_TIMEOUT_SECONDS = 10` | 4 | chờ Llama tối đa 10 s (chỉ search_key; price_is_right chờ không giới hạn) |
| `_run_source(name, pipeline, ...)` | 1 | chạy một nguồn, ghi `source_status` |
| `search_and_scrape()` | 1 | 2 nguồn song song |
| `combine()` | 2 | chuyển sang `UnifiedScrapedDeal` |
| `select_top_deals()` | 3 | gọi `MultiSourceScannerAgent.scan()` |
| `_estimate_one()` / `estimate_prices()` | 4 | ước giá song song, sắp theo discount |
| `plan()` | tất cả | chạy 4 bước, log `[TIMER]`, tự gửi thông báo (gửi lỗi không làm mất bảng kết quả) |
| `is_store_url(url)` | — | chỉ chấp nhận host `bestbuy.com` / `amazon.com` (và tên miền con) |

### Tầng cào dữ liệu

**`bestbuy_deals.py`** — curl_cffi + API nội bộ (không dùng Playwright):

| Hàm | Chức năng |
|---|---|
| `_init_session()` | session giả Chrome + bỏ qua trang chọn quốc gia |
| `search_bestbuy(session, keyword)` | trang tìm kiếm → danh sách SKU (giữ thứ tự trên trang) |
| `get_price_blocks(session, sku_ids)` | `/api/3.0/priceBlocks`, **tối đa 25 SKU mỗi request** → gọi theo lô |
| `get_product_details(session, sku)` | `/api/v2/product/<sku>` → tính năng, URL |
| `search_filter_scrape_bestbuy(keyword, max_results)` | lô priceBlocks → lọc hàng sale → lấy chi tiết, dừng sớm khi đủ |

Thời gian (29/10): 7–12 s cho 4–6 deal.

**`amazon_deals.py`** — cách lai Playwright + curl_cffi:

| Hàm | Chức năng |
|---|---|
| `_get_waf_cookies()` | Chromium chạy ngầm mở trang chủ, chờ cookie `aws-waf-token` (~1,6 s), chờ ô tìm kiếm tối đa 3 s (Amazon có lúc hiện trang "Continue shopping") → ~5 s |
| `init_amazon_session()` | curl_cffi + cookie trình duyệt + `i18n-prefs=USD` (IP Việt Nam hiện giá VND) |
| `search_amazon(session, keyword)` | `/s?k=...&ref=nb_sb_noss` + Referer; WAF / CAPTCHA → `AmazonBlockedError`; trang không có sản phẩm → log tiêu đề + chữ đầu trang |
| `scrape_product_page(session, url)` | trang chi tiết → `#feature-bullets`, hãng |
| `search_filter_scrape_amazon(keyword, max_results)` | tìm → rỗng thì nghỉ 2 s, lấy cookie mới, thử lại 1 lần (lần 2 vẫn bị chặn → `AmazonBlockedError`) → lọc hàng sale → lấy tính năng |

Approach A (thông số ngay trên trang tìm kiếm ≥ 50 ký tự) hiếm khi xảy ra từ 28/10 — trang tìm kiếm gần như không còn khối
thông số, nên hầu hết sản phẩm đi Approach B (mở trang chi tiết, **lần lượt từng trang**, 0,5–4,1 s / trang). Đây là chỗ
chậm nhất còn lại của Bước 1 (Amazon ~9–28 s).

### Tầng tiện ích

**`unified_deal.py`** — `UnifiedScrapedDeal(title, brand, price, features[:1500], url, source)`; `describe(include_url=True)`
(Bước 3 gọi với `include_url=False`).

**`multi_source_scanner_agent.py`**

| Thành phần | Chức năng |
|---|---|
| `MODEL = "gpt-6-luna"`, `REASONING_EFFORT = "none"` | đo 29/10 trên danh sách deal đã lưu × 3 lượt: none 4,2–4,3 s, low 4,6–5,3 s, cả hai 6/6 lượt đủ 3 deal khác nhau |
| `dedupe_deals()` | gộp hàng cùng nguồn + (cùng URL hoặc cùng tên khi bỏ từ chỉ màu), giữ bản rẻ nhất |
| `PickedDeals` | schema: `deal_number` + `product_description` |
| `scan()` | prompt đánh số "Deal N" (không có URL) → parse → code ghép `Deal("[Nguồn] <tên gốc>. <tóm tắt>", giá, URL)` |

**`gradio_helpers.py`** — `QueueHandler`, `setup_logging`, `html_for_logs`, `opportunities_to_html`.

### Tầng ước giá

**`ensemble_agent.py`**

```
EnsembleAgent.price(description):
    rewrite = Preprocessor.preprocess(description)
    song song: specialist / frontier / neural_network = _safe_price(...)   # lỗi → None
    combine(): chỉ lấy giá > 0; trọng số 0.8 / 0.1 / 0.1 chia lại trên các mô hình còn lại; không mô hình nào → ValueError
```

| Mô hình | Class | Trọng số | Ghi chú |
|---|---|---|---|
| Frontier | `FrontierAgent` | 80 % | gpt-6-luna reasoning `low` + 5 sản phẩm giống nhất trong ChromaDB (encode + query có khoá) |
| Specialist | `SpecialistAgent` | 10 % | Llama-3.2-3B QLoRA, app Modal `pricer-service`; `spawn()` + `get(timeout)` |
| Neural Network | `NeuralNetworkAgent` | 10 % | DNN PyTorch chạy trên máy (có khoá) |

Frontier đo 29/10 trên 200 mẫu test `SeanSunny/items_full`, 1 lượt / cấu hình: gpt-5.1 none MAE $31,16 · luna none
$31,42 · **luna low $29,69** · terra none $28,51 — chênh lệch chưa vượt nhiễu; chọn luna low (không kém, rẻ hơn).

**`specialist_agent.py`** — Modal tự tắt máy sau 60 s rảnh (khởi động lại mất 32–46 s):

| Thành phần | Giá trị / chức năng |
|---|---|
| `timeout_seconds` | `None` = chờ như cũ (price_is_right); search_key truyền 10 s |
| `COLD_SKIP_SECONDS = 45` | vừa quá giờ → 45 s sau bỏ qua Llama luôn (kiểm bên trong khoá) |
| `PING_SECONDS = 50`, `KEEP_WARM_IDLE_STOP = 900` | ping giữ ấm; dừng sau 15 phút không có lượt tìm, tự bật lại khi tìm |
| `wake_up_modal()` | gửi một lượt gọi không chờ kết quả để Modal bật máy sớm |

Đo thật 29/10: máy nguội → báo quá giờ sau 14,2 s (trước phải chờ 32–46 s); 3 lời gọi song song lúc nguội: 12,7 s cả nhóm;
giữ ấm, rảnh 150 s → 0,9 s. App Modal mới (giữ ấm phía server) chưa deploy được vì Modal đòi gắn thẻ.

**`preprocessor.py`** — LiteLLM viết lại mô tả theo khuôn `Title / Category / Brand / Description / Details`; mô hình lấy
từ `PRICER_PREPROCESSOR_MODEL` (`.env` đang đặt `groq/openai/gpt-oss-20b`; mặc định trong code `ollama/llama3.2`); lỗi →
trả lại chữ gốc.

**`messaging_agent.py`**

| Method | Chức năng |
|---|---|
| `craft_message(...)` | gpt-6-luna reasoning none qua LiteLLM (`allowed_openai_params=["reasoning_effort"]`) |
| `push(text)` | POST Pushover, `timeout=15`, HTTP ≠ 200 → RuntimeError |
| `notify(...)` | viết tin + gửi |

---

> Các mục dưới giải thích **vì sao** hệ thống làm như vậy, **đã đo được gì** và **còn giới hạn gì**. Nhãn: **[đã đo]** = chạy
> thật có số · **[có trong code]** = đọc code, chưa đo riêng · **[suy luận]** = suy ra, chưa kiểm · **[đề xuất]** = chưa làm.

## Cào dữ liệu — cơ chế chi tiết

### BestBuy: gọi API nội bộ thay vì đọc trang HTML

- **Vì sao:** trang sản phẩm BestBuy chặn request từ WSL2 (HTTP/2 + CDN Akamai) [có trong code — chú thích đầu
  `bestbuy_deals.py`]. Trang tìm kiếm và các API JSON nội bộ thì vẫn trả dữ liệu khi dùng `curl_cffi` giả dấu vân tay TLS của
  Chrome (`impersonate="chrome"`).
- **Luồng** [có trong code]:
  1. `_init_session()` mở `/?intl=nosplash` để bỏ qua trang chọn quốc gia.
  2. `search_bestbuy()` tải trang tìm kiếm, tìm mọi `"skuId":"…"` trong dữ liệu dựng sẵn của trang (Apollo SSR cache);
     `dict.fromkeys` bỏ trùng nhưng **giữ thứ tự trên trang** (liên quan nhất đứng trước); bỏ link `openbox` / `refurbished`.
  3. `get_price_blocks()` gọi `/api/3.0/priceBlocks?skus=…` theo **lô 25 SKU**: tên, hãng, `currentPrice`, `regularPrice`,
     `savingsAmount`, `totalSavingsPercent`, và **"đang sale" = `pricingType == "onSale"`**.
  4. Với mỗi SKU đang sale: `get_product_details()` gọi `/api/v2/product/<sku>` lấy danh sách tính năng (`title: description`)
     và URL chuẩn `seoPdpUrl`.
  5. **Dừng sớm** khi đủ `max_results` deal — không gọi hết các lô còn lại.
- **Lỗi đã sửa ngày 28/10** [đã đo] (commit `1a67113`):
  - priceBlocks **chỉ trả tối đa 25 SKU mỗi lần** dù gửi 40 hay 199 SKU ⇒ trước đó chỉ 25 / 200+ sản phẩm được kiểm giá
    (`wireless headphones` 2 ⇒ 6 deal, `air fryer` 3 ⇒ 6, `laptop` 1 ⇒ 3).
  - `set()` làm mất thứ tự liên quan của trang ⇒ đổi sang `dict.fromkeys`.
  - Khoá `buttonState.skuId` thiếu ở 21 / 25 mục ⇒ dùng `sku.skuId`.
- **Đặc điểm dữ liệu** [đã đo 29/10]: BestBuy trả các màu của cùng một mẫu với **cùng URL nhưng giá khác** (5 màu
  WH-1000XM5, $228–$298) ⇒ Bước 3 gộp lại, giữ bản rẻ nhất.

### Amazon: cách lai trình duyệt ngầm + curl_cffi

- **Lớp chặn:** Amazon bật **AWS WAF JavaScript challenge** — trang đầu trả mã 202 kèm đoạn JS bắt trình duyệt tự chứng minh
  là người thật. `curl_cffi` chỉ giả TLS, **không chạy JavaScript** ⇒ không tự qua được [đã đo 28/10: 6 kiểu giả trình duyệt
  đều 503].
- **Cách làm** [có trong code + đã đo]:
  1. `_get_waf_cookies()`: Playwright mở Chromium chạy ngầm (`channel="chromium"`), vào **trang chủ** (vào thẳng link tìm
     kiếm thì vẫn 503), chờ cookie `aws-waf-token` (~1,6 s), đóng trình duyệt ngay (`finally`).
  2. `init_amazon_session()`: chép cookie sang session `curl_cffi` + cookie `i18n-prefs=USD`.
  3. `search_amazon()`: `/s?k=<từ khoá>&ref=nb_sb_noss` + header `Referer: https://www.amazon.com/` — giả như bấm ô tìm kiếm
     trên trang chủ; **thiếu một trong hai là 503**.
  4. `parse_search_results()`: mỗi thẻ sản phẩm lấy ASIN, tên, giá hiện tại, giá gạch ngang; **"đang sale" = có giá gạch
     ngang lớn hơn giá hiện tại**; URL dựng từ ASIN (`/dp/<ASIN>`).
  5. `scrape_product_page()`: trang chi tiết ⇒ `#feature-bullets` (không có thì `#productDescription`), hãng từ `#bylineInfo`.
- **Bẫy đã gặp** [đã đo]:
  - **Giá VND:** IP Việt Nam ⇒ Amazon hiện giá VND; hàm cũ bỏ hết ký tự không phải số ⇒ số VND bị đọc như USD. Nay ép USD
    bằng cookie, và chuỗi giá không có `$` ⇒ 0 ⇒ bị lọc, không bao giờ đưa giá VND vào ensemble.
  - **Đặt ZIP bằng POST cũ không còn chạy** (API mới cần CSRF token) ⇒ Amazon vẫn ghi "Deliver to Vietnam" [suy luận: một số
    hàng không giao về VN có thể bị ẩn giá].
  - **Trang "Continue shopping"** (29/10): sau khi qua WAF, trang chủ không có ô tìm kiếm ⇒ code cũ chờ 20 s rồi báo lỗi và
    **bỏ luôn cookie đã có** ⇒ nay chờ tối đa 3 s rồi dùng cookie đang có (lấy cookie 22 s ⇒ ~5 s).
  - **Chặn mềm:** trang 200 nhưng không có thẻ sản phẩm (2,4 KB khi chưa có token; ~282 KB khi có) — gặp 3 lần trong ~8 lượt
    ngày 29/10. Code thử lại 1 lần với cookie mới; trang rỗng được log tiêu đề + chữ đầu trang để nhận dạng sau.
  - **Gửi dồn dập ⇒ bị chặn IP tạm thời** ⇒ thử nghiệm Amazon phải thưa, có nghỉ giữa các lượt.
- **Approach A / B:** thông số trên trang tìm kiếm ≥ 50 ký tự (A) gần như không còn từ 28/10 ⇒ hầu hết sản phẩm phải mở trang
  chi tiết (B), **lần lượt**, 0,5–4,1 s / trang [đã đo].

### Dữ liệu sau khi cào

`ScrapedBestBuyDeal` / `ScrapedAmazonDeal` → `UnifiedScrapedDeal(title ≤ 200 ký tự, brand, price, features ≤ 1500 ký tự,
url, source)`. **Giá gốc của shop (`regularPrice`, `list_price`) có cào được nhưng chưa đưa vào pipeline** [có trong code] —
xem "Giới hạn đã biết".

---

## Chọn deal bằng LLM (Bước 3) — vì sao làm thế này

- **Trước 29/10** [đã đo]: gpt-5-nano tự **chép lại** giá và URL của deal nó chọn (có thể chép sai) và 1 / 3 lượt đo trả
  **8 deal** dù được dặn tối đa 3 ⇒ Bước 4 phải ước giá cho cả 8.
- **Nay** [có trong code]: mỗi deal trong prompt được đánh số `Deal 1`, `Deal 2`… (không kèm URL); luna chỉ trả
  `deal_number` + câu tóm tắt; **code** lấy giá, URL, tên gốc từ danh sách đã cào, bỏ số không hợp lệ / lặp, tối đa 3.
  Nguyên tắc: *mô hình chỉ đề xuất, code giữ con số*.
- **Gộp hàng trùng trước khi hỏi LLM:** cùng nguồn và (cùng URL hoặc cùng tên khi bỏ các từ chỉ màu ở cuối) ⇒ giữ bản rẻ nhất
  ở vị trí xuất hiện đầu. Ví dụ [đã đo]: 12 deal `wireless headphones` ⇒ 8 (5 màu WH-1000XM5 gộp còn bản $228).
- **Tên gốc ghép vào đầu mô tả:** luna `none` có lúc tóm tắt "This 6-quart air fryer…" mất cả hãng lẫn tên mẫu ⇒ bảng kết quả
  không biết là hàng gì, ensemble mất thông tin hãng (Ninja DoubleStack $229,99 ước $167 so với $212 ở lượt có tên) [đã đo].
  Nay mô tả = `[Nguồn] <tên gốc>. <tóm tắt của luna>`.
- **Chọn `reasoning_effort="none"`** [đã đo, 2 danh sách deal × 3 lượt, cùng đầu vào]: none 4,2–4,3 s, low 4,6–5,3 s, cả hai
  6 / 6 lượt đủ 3 deal khác nhau, 0 sai giá / URL; nano cũ 3,3–4,4 s, 5 / 6.
- **Tiêu chí chọn của prompt vẫn là "mô tả chi tiết nhất, giá rõ ràng"** (giữ như bản cũ), chưa phải "giảm nhiều nhất".

---

## Xử lý song song

| Chỗ | Cách | Vì sao | Kết quả |
|---|---|---|---|
| BestBuy ‖ Amazon (Bước 1) | `ThreadPoolExecutor(2)` | hai nguồn độc lập, chủ yếu chờ mạng | có từ trước |
| 3 deal (Bước 4) | `ThreadPoolExecutor(số deal)` | các deal độc lập | Bước 4 33–40 s ⇒ ~4 s [đã đo] |
| 3 mô hình trong một deal | `ThreadPoolExecutor(3)` sau bước tiền xử lý | Llama / Frontier / DNN chỉ cần chung một `rewrite` | như trên |

- **Vì sao dùng luồng (thread) mà không dùng async:** gần như toàn bộ thời gian là chờ mạng (OpenAI, Groq, Modal, BestBuy,
  Amazon); DNN chỉ 0,1–0,2 s, RAG 0,0–0,3 s [đã đo 28/10]. Luồng cho lợi ích tương đương mà không phải viết lại code sang
  async; pipeline vốn đã chạy trong một luồng worker của Gradio. Async chỉ đáng khi cần phục vụ nhiều người dùng cùng lúc
  [suy luận].
- **Khoá (lock) — chỗ nào và vì sao** [có trong code]:
  - `FrontierAgent._search_lock`: encode câu (SentenceTransformer trên GPU) + query ChromaDB đi lần lượt — dùng chung một
    model GPU giữa các luồng; mỗi lần chỉ 0,1–0,3 s nên khoá gần như không làm chậm.
  - `NeuralNetworkAgent._lock`: một model PyTorch trên GPU dùng chung ⇒ suy luận lần lượt.
  - `SpecialistAgent._call_lock`: các lời gọi Llama xếp hàng — gọi song song có thể làm Modal **bật thêm máy nguội** (tốn tiền,
    không nhanh hơn); máy ấm chỉ ~0,9 s / lời gọi nên 3 deal xếp hàng vẫn ~2,7 s, chạy song song với Frontier.
  - `MultiSourceFramework._init_lock`, `App._framework_lock`: luồng nạp nền lúc mở app và lần bấm Search sớm không tạo 2 bộ mô hình.
- **Hai tầng ThreadPoolExecutor không kẹt nhau:** mỗi tầng một pool riêng, không khoá nào được giữ trong lúc chờ kết quả của
  pool kia [có trong code, agent con đọc diff xác nhận].
- **Việc chậm nhất quyết định thời gian cả bước:** Bước 4 chỉ nhanh khi Modal ấm; Modal nguội thì vẫn mất ~10–14 s (giới hạn chờ).
- **Cố ý chưa song song:**
  - Trang chi tiết Amazon (6 trang lần lượt, 13–19 s): gửi dồn dập dễ bị chặn [đã gặp 28/10].
  - Chi tiết BestBuy (~0,6 s / SKU): lợi nhỏ.
  - Cả hai cần mỗi luồng một session riêng vì `curl_cffi.Session` không bảo đảm an toàn khi nhiều luồng dùng chung [suy luận].
  - Đề xuất P4 [đề xuất]: song song 2–3 trang Amazon, session riêng mỗi luồng, đo tỉ lệ bị chặn trước khi giữ.

---

## Tối ưu tốc độ — trước / sau và nguyên nhân

Đo bằng `scripts/do_luong/profile_pipeline.py` (bọc hàm từ ngoài, Pushover bị chặn khi đo, đồng hồ `perf_counter`) [đã đo 29/10]:

| Chỗ | Trước | Sau | Nguyên nhân gốc / cách sửa |
|---|---|---|---|
| Lấy cookie Amazon | 22–44 s | ~5 s | chờ ô tìm kiếm 20 s trên trang "Continue shopping" rồi vứt cookie ⇒ chờ 3 s, dùng cookie có sẵn |
| Lần Search đầu tiên | +~22 s nạp thư viện + Chroma + mô hình | 0 s (nạp ở luồng nền khi mở app, ~9–20 s) | trước nạp lười ở lần bấm đầu |
| Llama trên Modal | 31,5–46 s mỗi lượt máy nguội | ~0,9 s khi ấm; nguội thì bỏ sau ~10–14 s | Modal tắt máy sau 60 s rảnh ⇒ đánh thức khi mở app + ping 50 s + chờ tối đa 10 s |
| Bước 4 (3 deal) | 33–40 s | ~4 s | trước tuần tự cả deal lẫn mô hình ⇒ song song 2 tầng |
| Bước 3 | 3,3–4,4 s (có lượt trả 8 deal) | 3,7–5,1 s, luôn ≤ 3 deal | đổi sang luna + chọn theo số thứ tự; chậm hơn ~0,5–1 s nhưng Bước 4 không còn bị phình |
| **Cả lượt** | **69,5 s / 106,7 s** (2 từ khoá) | **21,3–34,3 s**; User chạy app thật 27,1 s | |

**Đã thử, chưa áp dụng** (chi tiết ở `docs/changelog/README.md`):
- App Modal mới `pricer-service-v2` (giữ ấm 10 phút phía server, tối đa 1 máy, ghim thư viện, log thời gian khởi động):
  Modal từ chối deploy app GPU mới khi tài khoản chưa gắn thẻ ⇒ giữ ấm từ phía app thay thế. File `segment4/pricer_service_v2.py`
  để sẵn (chưa commit).
- luna `low` cho Bước 3 (chậm hơn, cùng chất lượng); gpt-6.1-terra cho Frontier (MAE $28,51, đắt hơn luna low ~7 lần, chênh
  lệch chưa vượt nhiễu).

**Chỗ chậm còn lại** [đã đo]: trang chi tiết Amazon lần lượt (Bước 1 còn 11–26 s, Amazon thường là nhánh chậm hơn BestBuy).

---

## Chống sập và an toàn

- **Trạng thái từng nguồn** `ok (n)` / `empty` / `blocked` / `error` — trước đây mọi trường hợp đều thành "0 sản phẩm";
  một nguồn ném lỗi làm mất cả kết quả nguồn kia [có trong code + đã đo].
- **Ensemble chia lại trọng số khi thiếu mô hình** [có trong code; công thức kiểm offline]:
  - Đủ 3 mô hình (Llama $60, Frontier $150, DNN $100) ⇒ 0,8 × 150 + 0,1 × 60 + 0,1 × 100 = **$136**.
  - Thiếu Llama (quá giờ) ⇒ (0,8 × 150 + 0,1 × 100) / 0,9 = **$144,44**.
  - Frontier trả 0 ⇒ (0,1 × 60 + 0,1 × 100) / 0,2 = **$80** — coi 0 là lỗi vì Frontier / Llama trả 0 khi không đọc được số;
    trước đây số 0 đi thẳng vào trung bình, kéo ước lượng xuống còn ~20 % mà không ai biết.
  - Không mô hình nào hợp lệ ⇒ bỏ deal đó, các deal khác vẫn hiện.
- **Kiểm link trước khi gửi thông báo** (`is_store_url`): chữ trên trang cào là **dữ liệu không đáng tin**, lại được đưa vào
  prompt của LLM; app có đường gửi ra ngoài (Pushover) ⇒ chỉ gửi khi host là `bestbuy.com` / `amazon.com` (chặn
  `amazon.com.evil.io`, `evilamazon.com`, `javascript:`) [có trong code, kiểm offline]. URL vốn do code dựng nên đây là lớp
  kiểm thêm.
- **Gửi tin:** `timeout=15`, HTTP ≠ 200 ⇒ báo lỗi; lỗi gửi chỉ ghi log, không làm mất bảng kết quả.
- **Giao diện:** lỗi pipeline hiện ở ô Status thay vì treo "Processing..." mãi.
- **Kiểm chéo:** một agent con chưa biết gì về phiên làm việc đọc diff cả nhánh và tìm ra 3 lỗi thật mà các lượt đo bỏ sót
  (Modal nguội + 3 deal song song ~30 s; `price_is_right` bị đổi hành vi; `PlanningAgent` có thể treo) — đã sửa và thử lại
  với Modal thật [đã đo] (`docs/changelog/2026_10_29_06_sua_theo_kiem_cheo.md`).

---

## Chi phí mỗi lượt tìm

[suy luận — ước từ số token và giá đã đo ngày 29/10; chưa có đồng hồ tiền trong app]

| Phần | Ước mỗi lượt (3 deal) | Căn cứ |
|---|---|---|
| Bước 3 — luna none | ~$0,0003–0,0007 | 1.322–4.755 token vào, ~300–500 token ra (đo 29/10); giá luna $0,10 / $0,50 mỗi triệu token |
| Frontier — luna low × 3 | ~$0,0003 | $0,018 cho 200 lời gọi khi đo MAE |
| Llama trên Modal × 3 (máy ấm) | ~$0,0005 | ~0,9 s × $0,000164 / s mỗi lời gọi |
| Viết tin nhắn (chỉ khi gửi) | < $0,0001 | LiteLLM báo $0,000016 cho một lời gọi ngắn |
| Groq gpt-oss-20b × 3 | chưa đo | — |
| Giữ ấm Modal | ~$0,59 / giờ khi app mở và có người tìm trong 15 phút gần nhất | giá T4 |

---

## Giới hạn đã biết

- **Chưa có thước đo chất lượng trên hàng cào thật:** MAE chỉ đo trên 200 mẫu test (dữ liệu Amazon 2023 đã xử lý), chưa biết
  giá ước cho sản phẩm hôm nay sai bao nhiêu [đề xuất: 15–20 sản phẩm có giá tham chiếu, chấm bằng code].
- **Vùng dữ liệu huấn luyện:** chỉ 8 nhóm hàng, giá ≤ $999 ⇒ laptop / TV đắt bị ước thấp, đồ bếp không có trong dữ liệu (mục
  "Nên thử từ khoá nào").
- **Llama hay lặp lại một số giá** ($60, $220, $350, $700, $950 xuất hiện nhiều lần cho các sản phẩm khác nhau) [đã thấy trong
  log, chưa phân tích nguyên nhân].
- **Giá gốc của shop chưa dùng:** có `regularPrice` / `list_price` nhưng Bước 3 không thấy, bảng kết quả không hiện để đối
  chiếu với giá AI ước [đề xuất Q5].
- **Amazon mong manh:** phụ thuộc WAF, trang chặn mềm, "Deliver to Vietnam".
- **`price_is_right.py` chưa chạy lại** sau đợt sửa (dùng chung Ensemble / Frontier / Specialist / Messaging).
- **Chưa có mốc không dùng LLM cho Bước 3** (ví dụ "3 deal giảm nhiều nhất") để chứng minh LLM đáng dùng [đề xuất].
- **Bước tiền xử lý vẫn dùng Groq**, chưa đo nếu đổi sang luna.

## Kiểm chứng lại

Script trong `scripts/do_luong/` (đọc README ở đó): `profile_pipeline.py` (cả pipeline, có `warm`), `save_pools.py` +
so Bước 3 trên cùng đầu vào, `eval_frontier.py` (MAE 200 mẫu), `test_modal_nguoi.py` (Modal nguội + 3 lời gọi song song),
`probe_keywords.py` (từ khoá có trong vùng dữ liệu không). Mỗi thay đổi ghi ở `docs/changelog/`.

---

## Nên thử từ khoá nào

Mô hình học từ **8 nhóm hàng Amazon năm 2023** (Automotive, Electronics, Office Products, Tools & Home Improvement, Cell
Phones & Accessories, Toys & Games, Appliances, Musical Instruments), **giá $0,5–$999,49**, đa số $10–$200
(`scraping_data_tv/Data_processing_for_English_data/Report_data_processing_v2.md`). Kiểm 29/10 bằng
`scripts/do_luong/probe_keywords.py` (20 sản phẩm gần nhất trong ChromaDB):

| Nhóm | Từ khoá | Vì sao |
|---|---|---|
| Nên thử | `noise cancelling headphones` ($175), `soundbar` ($215), `gaming monitor` ($235), `action camera` ($175), `digital piano` ($315), `electric guitar` ($425), `cordless drill` ($111) | sản phẩm gần nhất đúng loại, giá trung vị $100–$500 → dễ có discount > $100 |
| Tránh | `laptop`, `gaming laptop`, `smart tv` | nhiều hàng > $999 (6/20 sản phẩm gần nhất của "gaming laptop" ≥ $900) → ensemble ước thấp; giá phụ thuộc thông số |
| Tránh | `air fryer`, `coffee maker`, `microwave`, `blender` | không có nhóm đồ bếp: sản phẩm gần nhất của "air fryer" là rơ-le điện, của "blender" là phần mềm FL Studio |
| Ít lợi | `phone case`, `wireless earbuds`, `smartwatch` | giá trung vị $21–$42, hiếm khi giảm > $100 |

(Giá trong ngoặc = giá trung vị của 20 sản phẩm gần nhất. BestBuy có thể không bán nhạc cụ — chưa kiểm; khi đó chỉ có deal Amazon.)

---

## Cài đặt và chạy

```bash
cd tech2ai && uv sync && uv run playwright install chromium
cd segment4 && uv run search_key.py      # http://127.0.0.1:7860
```

`.env` ở **`tech2ai/.env`**: `OPENAI_API_KEY`, `GROQ_API_KEY`, `PRICER_PREPROCESSOR_MODEL=groq/openai/gpt-oss-20b`,
`PUSHOVER_USER` / `PUSHOVER_TOKEN` (tuỳ chọn), `HF_TOKEN`. Token Modal: `~/.modal.toml`.

---

## Thời gian chạy (đo thật 29/10, Modal đã được đánh thức khi mở app)

```
Tổng: ~21–34 s (trước tối ưu 69,5–106,7 s cùng 2 từ khoá); User chạy app thật ("laptop"): 27,1 s

  |-- Mở app (luồng nền, không rơi vào lần Search đầu)   nạp mô hình ~9–20 s
  |-- Bước 1: cào song song                              ~11–26 s
  |     |-- BestBuy                                        ~7–12 s
  |     |-- Amazon (cookie ~5 s + trang chi tiết lần lượt)  ~9–28 s
  |-- Bước 2: gộp                                        < 1 s
  |-- Bước 3: gpt-6-luna chọn deal                       ~4–5 s
  |-- Bước 4: ước giá song song                          ~4–8 s (Modal nguội: bỏ Llama sau ~10–14 s)
```

RAM đỉnh ~3,9 GB. Số đo chi tiết: `session_prompt/archive/SESSION_HANDOFF_OPTIMIZE.md` mục 3.4; script đo: `scripts/do_luong/`.

---

## Lưu ý kỹ thuật

- `curl_cffi` với `impersonate="chrome"` là BẮT BUỘC cho cả hai nguồn từ WSL2; trang sản phẩm BestBuy bị chặn → dùng API nội bộ.
- Amazon: vào thẳng `/s?k=` mà thiếu `ref=nb_sb_noss` + `Referer` → 503; giá không có `$` → 0 (bị lọc, không đưa giá VND vào
  ensemble); gửi request thưa, có nghỉ, nếu không dễ bị chặn IP / trả trang 200 rỗng.
- gpt-6-luna không nhận `reasoning_effort="minimal"`.
- Structured Outputs: `response_format=PickedDeals` (Bước 3).
- Log: `QueueHandler` → `queue.Queue` → Gradio cập nhật mỗi 0,1 s.
- Chạy app thật là gửi Pushover thật khi discount > $100.
