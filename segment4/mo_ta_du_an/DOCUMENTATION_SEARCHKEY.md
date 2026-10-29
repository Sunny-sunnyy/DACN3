# SEARCH_KEY.PY — Multi-Source Deal Finder

**Cập nhật lần cuối:** 29/10/2026 (đợt tối ưu: luna, chống sập, giữ ấm Modal, song song Bước 4 — xem `docs/changelog/`)
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
