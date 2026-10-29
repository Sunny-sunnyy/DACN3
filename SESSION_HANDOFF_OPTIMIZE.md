# SESSION HANDOFF — Sửa cào dữ liệu + Kế hoạch tối ưu pipeline `search_key.py`

> **Mục đích:** Bàn giao đầy đủ cho session sau để **tối ưu thời gian chạy và độ ổn định** của pipeline `search_key.py`
> mà không phải đo lại hay dò lại từ đầu.
>
> **Session được bàn giao:** 2026-10-28 (tin nhắn cuối khoảng 16:04). **Viết file này:** 2026-10-29 09:15.
> **Nhánh git:** `claudedev` | **Thư mục làm việc:** `/home/minhhieu/price2026wsl/tech2ai`
> **Liên quan:** `SESSION_HANDOFF_NLP.md` (bối cảnh toàn dự án, dữ liệu, mô hình, báo cáo).
>
> **Quy ước trong file:** **[ĐÃ KIỂM]** = chạy thật, có số đo. **[SUY LUẬN]** = suy ra từ code hoặc số đo, chưa chạy kiểm.
> **[ĐỀ XUẤT]** = việc chưa làm, cần User duyệt ("làm đi") trước khi sửa code.

---

## 0. Đọc nhanh (TL;DR)

| Mục | Trạng thái |
|---|---|
| BestBuy cào thiếu deal | **Đã sửa + push** (`1a67113`) — lấy giá theo lô 25 SKU |
| Amazon bị chặn (AWS WAF) | **Đã sửa + push** (`25dbef4`) — cách "lai" Playwright lấy cookie → curl_cffi |
| Amazon hiện giá VND | **Đã sửa** — cookie `i18n-prefs=USD` |
| Pipeline full (headless, không Gradio) | **[ĐÃ KIỂM]** chạy được: 6 BestBuy + 6 Amazon, 72–90 giây/lượt |
| Giao diện Gradio `search_key.py` | **Chưa** chạy thử sau khi sửa (không sửa gì ở UI, nhưng nên bấm thử 1 lần) |
| Tối ưu thời gian | **Mới đo + đề xuất, CHƯA sửa code** (mục 5–6) |
| Nút thắt lớn nhất | **Modal cold start 46,2 giây = 64% thời gian pipeline** |

**Việc đầu tiên của session mới:** chạy lại 1 lượt tìm (mục 9, bước 1) để chắc Amazon vẫn vào được — lớp chặn của Amazon có thể đổi bất kỳ lúc nào.

---

## 1. Những gì đã làm trong session 2026-10-28

### 1.1 Kiểm tra sức khoẻ hệ thống [ĐÃ KIỂM]

| Thành phần | Kết quả | Thời gian |
|---|---|---|
| `uv` 0.12.5, Python 3.12, GPU CUDA (torch 2.9.0+cu128), cổng 7860 | OK | — |
| `.env` | Nằm ở **`tech2ai/.env`** (không phải `segment4/.env` như tài liệu cũ). `load_dotenv()` tự tìm lên thư mục cha → vẫn đọc được | — |
| Biến môi trường | Có đủ: `OPENAI_API_KEY`, `PUSHOVER_*`, `GROQ_API_KEY`, `HF_TOKEN`, `PRICER_PREPROCESSOR_MODEL=groq/openai/gpt-oss-20b`, `BRAVE_API_KEY`. Modal token ở `~/.modal.toml` | — |
| Import toàn bộ pipeline | OK | ~16 giây (nạp torch, transformers…) |
| ChromaDB `products_vectorstore/` | OK, **800.000** sản phẩm, 3,4 GB | <1 giây |
| `deep_neural_network.pth` | 1,1 GB | — |
| Preprocessor (Groq gpt-oss-20b) | OK | 0,3–1,1 giây/lần |
| FrontierAgent (GPT-5.1 + RAG) | OK | 1–2,2 giây/lần (lần đầu ~13 giây vì nạp SentenceTransformer) |
| NeuralNetworkAgent (DNN) | OK | 0,1–0,2 giây/lần |
| SpecialistAgent (Llama-3.2-3B trên Modal) | OK | **46 giây khi container nguội**, 0,9 giây khi đã ấm |
| MultiSourceScannerAgent (GPT-5-nano) | OK | 4,2–25 giây (dao động mạnh) |
| Pushover | **Chưa thử** (sẽ đẩy tin thật lên điện thoại User) | — |

### 1.2 Sửa BestBuy — commit `1a67113` [ĐÃ KIỂM]

File: `segment4/price_agents/bestbuy_deals.py`

**Nguyên nhân thiếu deal:**
1. API `/api/3.0/priceBlocks` **chỉ trả tối đa 25 SKU mỗi request** (gửi 40 hay 199 SKU đều chỉ nhận 25). Code cũ gửi cả danh sách
   một lần → chỉ 25/200+ sản phẩm được kiểm giá.
2. `search_bestbuy()` dùng `set()` → thứ tự SKU **ngẫu nhiên**, không phải thứ tự liên quan trên trang tìm kiếm.
3. Khoá `buttonState.skuId` **thiếu ở 21/25 item** → các item đè nhau dưới khoá rỗng `""`. *Lưu ý:* đo lại thì lỗi này hầu như
   chỉ rơi vào hàng **không** sale nên không làm mất deal; nguyên nhân thật là (1). Vẫn sửa: dùng `sku.skuId` (có ở 25/25).

**Sửa:**
- Hằng số `PRICE_BLOCKS_BATCH_SIZE = 25`; vòng lặp gọi theo lô, **dừng sớm** khi đủ `max_results` deal sale.
- `all_skus = list(dict.fromkeys(...))` giữ thứ tự trang.
- `sku_id = sku.get("skuId") or buttonState.skuId`, bỏ item không có khoá.

**Kết quả:**

| Từ khoá | Trước | Sau | Thời gian sau |
|---|---|---|---|
| wireless headphones | 2 | 6 | 15,6 giây (trong pipeline song song: 12,3 giây) |
| air fryer | 3 | 6 | 10,8 giây |
| laptop | 1 | 3 | 10,0 giây |
| gaming monitor | 0–1 | 1 (BestBuy ít màn hình sale) | 8,9 giây |

### 1.3 Sửa Amazon — commit `25dbef4` [ĐÃ KIỂM]

File: `segment4/price_agents/amazon_deals.py` (+ chú thích ở `multi_source_planning_agent.py`, cập nhật `CLAUDE.md`,
`segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`)

**Hiện tượng:** Amazon trả 0 sản phẩm. Trang chủ trả **202 + 2 KB** chứa `window.awsWafCookieDomainList` / `window.gokuProps`
= **AWS WAF JavaScript challenge** (trang bắt trình duyệt chạy JS để chứng minh là người). `curl_cffi` chỉ giả dấu vân tay TLS
của Chrome, **không chạy JS** → không qua. Trang tìm kiếm trả "Sorry! Something went wrong!" / 503.

**So sánh các cách đã thử (2026-10-28):**

| # | Cách | Kết quả | Thời gian |
|---|---|---|---|
| M0 | Chỉ `curl_cffi` (code cũ), thử 6 kiểu impersonate (chrome, chrome131, chrome124, safari17_0, edge101, firefox133) | Chặn (503) | — |
| M1 | Playwright headless-shell vào thẳng `/s?k=` | 503, không có cookie | 19 giây |
| M2 | Playwright Chromium "new headless" (`channel="chromium"`) vào thẳng `/s?k=` | 503 | 23 giây |
| M2b | M2 nhưng vào **trang chủ** trước | **Qua**: 202 → JS chạy → 200, có cookie `aws-waf-token` | 2,4–6,7 giây |
| M2c | Có token rồi `page.goto("/s?k=...")` | Vẫn 503 (WAF chặn link tìm kiếm vào thẳng) | — |
| C | Gõ từ khoá vào ô `#twotabsearchtextbox` + Enter | **Qua**: 16 sản phẩm | 6,3 giây/lần, phải giữ trình duyệt |
| **M3 (chọn)** | **Lai:** browser chỉ mở trang chủ lấy cookie → đóng; `curl_cffi` + cookie + `&ref=nb_sb_noss` + header `Referer: https://www.amazon.com/` | **Qua**: 11–13 sản phẩm | lấy cookie 3–7 giây + 1,3–1,8 giây/lần tìm |

**Bẫy gặp khi dò (để session sau khỏi mắc lại):**
- Thiếu `ref=nb_sb_noss` **hoặc** thiếu `Referer` → WAF trả 503 (form tìm kiếm thật có `action="/s/ref=nb_sb_noss"`).
- Bộ chọn `"#twotabsearchtextbox, input[name='field-keywords']"` **bắt nhầm ô ẩn** trùng tên trong form `ue_backdetect` →
  timeout. Chỉ dùng `#twotabsearchtextbox`.
- Gửi nhiều request dồn dập khi dò → IP bị 503 tạm thời. **Thử nghiệm Amazon phải thưa, có `sleep`**.
- **Giá VND:** IP ở Việt Nam → Amazon hiển thị VND (vd. nồi chiên Ninja "4.649.862"). Hàm `_parse_price` cũ bỏ hết ký tự
  không phải số → **ra số VND như thể USD** → ensemble so sai hoàn toàn. Cookie `i18n-prefs` ban đầu = `VND`.
- Đặt ZIP 96150 bằng POST `/gp/delivery/ajax/address-change.html` (code cũ) **không còn chạy** (trả không phải JSON).
  Thử API mới `/portal-migration/hz/glow/address-change` cần `anti-csrftoken-a2z` nhưng **không tìm thấy CSRF token** → bỏ.
  Hệ quả: Amazon vẫn ghi "Deliver to Vietnam"; [SUY LUẬN] một số sản phẩm không giao về VN có thể bị ẩn giá → lọc mất.
- Trang tìm kiếm Amazon **không còn khối thông số** (`div[data-cy="product-details-recipe"]`) → "Approach A" không bao giờ
  dùng được; **mọi** sản phẩm đi "Approach B" (mở trang chi tiết, ~0,7–1 giây/cái khi qua curl, tới 2,8 giây lúc đo lẻ).
- Amazon **chập chờn**: 4 lần chạy đầu có 2 lần hụt (gaming monitor 0 deal; laptop browser timeout), chạy lại thì đều được.

**Sửa (đã commit):**
- `_get_waf_cookies()`: Chromium headless (`channel="chromium"`) mở trang chủ, chờ `aws-waf-token` (tối đa 15 giây),
  chờ `#twotabsearchtextbox`, lấy cookies, **luôn đóng browser** (`finally`).
- `init_amazon_session()`: session `curl_cffi` + cookies từ browser + cookie `i18n-prefs=USD`. Lỗi browser → log error, vẫn trả session.
- `_is_waf_blocked(resp)`: status 202/503 hoặc có `awsWafCookieDomainList` → log `"Blocked by AWS WAF"` thay vì "0 products".
- `_parse_price`: chuỗi **không có `$`** → 0.0 (bị lọc) → không bao giờ đưa VND vào ensemble. Có cảnh báo nếu có card mà 0 giá USD.
- `search_amazon`: URL thêm `&ref=nb_sb_noss`, header `Referer`.
- `search_filter_scrape_amazon`: lần tìm đầu rỗng → `sleep(2)`, lấy cookie mới, **thử lại 1 lần**.

**Kết quả từng từ khoá (lần chạy 2, sau khi có retry):** wireless headphones 6, air fryer 6, gaming monitor 6, laptop 3 deal.

**Cài thêm:** `uv run playwright install chromium` → `~/.cache/ms-playwright` **622 MB** (Chromium + headless shell + ffmpeg).
Gói `playwright>=1.58.0` đã có sẵn trong `pyproject.toml`.

### 1.4 Sự cố môi trường do agent gây ra (cần biết)

`uv sync --locked` (chạy lúc kiểm tra, **không** dùng `--dry-run`) đã **gỡ các gói cài tay không có trong `uv.lock`**:
thấy được trong log có `xformers 0.0.33.post1`, `wsproto 1.3.2`, `wheel 0.47.0`, và hạ `urllib3 2.6.3 → 2.3.0` (danh sách đầy đủ
không lưu được). search_key không cần các gói này. **Nếu notebook fine-tune nào báo thiếu `xformers`… thì do bước này** — cài lại.
Bài học: kiểm môi trường dùng `uv sync --locked --dry-run`.

---

## 2. Bản đồ code pipeline (vị trí chính xác, tại commit `25dbef4`)

```
search_key.py
  App.__init__ (dòng 31)            framework = None  → LAZY: chưa nạp gì khi mở app
  App.get_framework (37)            tạo MultiSourceFramework ở lần tìm đầu
  _run_pipeline: threading.Thread (76) worker chạy pipeline; main thread poll queue log mỗi 0,1 giây, yield cho Gradio
multi_source_framework.py
  __init__                          load_dotenv, ChromaDB PersistentClient → collection 'products'
  init_agents_as_needed (52)        lazy tạo MultiSourcePlanningAgent (nạp ensemble: SentenceTransformer, DNN 1,1 GB, Modal handle)
  run (59)                          → planner.plan()
price_agents/multi_source_planning_agent.py
  DEAL_THRESHOLD = 100 (42)
  search_and_scrape (69)            ThreadPoolExecutor(max_workers=2) (75): BestBuy ‖ Amazon  ← ĐÃ song song
  estimate_prices (127)             for deal in deal_selection.deals (132): TUẦN TỰ 3 deal
  plan()                            auto-notify (194) nếu discount > 100
price_agents/bestbuy_deals.py
  search_filter_scrape_bestbuy (157) vòng lô priceBlocks (176) → get_product_details(session, sku) (183) TUẦN TỰ từng SKU
price_agents/amazon_deals.py
  _get_waf_cookies (70)             Playwright, mỗi lượt tìm mở 1 lần (CHƯA cache)
  init_amazon_session (94)
  search_filter_scrape_amazon (286) retry (306); scrape_product_page(session, url) (330) TUẦN TỰ từng sản phẩm
bestbuy_untils/multi_source_scanner_agent.py
  scan (63) → openai.chat.completions.parse (77), gpt-5-nano, reasoning_effort="minimal" (84), response_format=DealSelection
            LLM tự VIẾT LẠI price + url trong output
bestbuy_untils/unified_deal.py      features[:1500] (65)
price_agents/ensemble_agent.py
  price (24): preprocess → specialist (35) → frontier (36) → neural (37) TUẦN TỰ; combined = 0.8F+0.1S+0.1N (38)
price_agents/specialist_agent.py    price (22) → self.pricer.price.remote() (27) — KHÔNG try/except, KHÔNG timeout
price_agents/frontier_agent.py      find_similars (54); get_price (68) trả 0.0 nếu không parse được (74); GPT-5.1 reasoning_effort="none" (91)
price_agents/preprocessor.py        LiteLLM completion; lỗi → trả text gốc (đã có fallback)
w8/pricer_service2.py               (bản giống hệt ở segment4/khong_su_dung/) Modal app "pricer-service", class Pricer,
                                    GPU T4, MIN_CONTAINERS = 0 (21), max_new_tokens=5 (74), parse lỗi → return 0
```

---

## 3. Số đo pipeline — MỐC "TRƯỚC TỐI ƯU" [ĐÃ KIỂM]

### 3.1 Lượt đo chi tiết — `wireless headphones`, 2026-10-28, max 6/nguồn, source "All"

Đo bằng script bọc hàm từ bên ngoài (Phụ lục A), không sửa code. Pushover bị chặn trong lúc đo. RAM đỉnh **~3,9 GB**.
Cột "bắt đầu/kết thúc" tính bằng giây kể từ lúc script bắt đầu (0–10 giây đầu là import thư viện).

| Hàm | Bắt đầu | Kết thúc | Mất | Luồng | Ghi chú |
|---|---|---|---|---|---|
| import thư viện | 0 | 10,0 | 10,0 | Main | torch, transformers, chromadb… |
| framework_init (ChromaDB) | 10,0 | 13,5 | 3,5 | Main | |
| init_agents (mô hình) | 13,5 | 22,1 | 8,6 | Main | SentenceTransformer + DNN + Modal handle |
| **search_and_scrape (Bước 1)** | 22,2 | 34,6 | **12,3** | Main | |
| ├ BestBuy tổng | 22,2 | 34,6 | 12,3 | Pool | |
| │ ├ `_init_session` | | | 1,0 | | |
| │ ├ `search_bestbuy` | | | 2,2 | | |
| │ ├ `get_price_blocks` ×4 | | | 4,9 (1,1–1,6/lần) | | tuần tự |
| │ └ `get_product_details` ×6 | | | 4,1 (0,6–0,8/lần) | | tuần tự |
| └ Amazon tổng | 22,2 | 33,7 | 11,5 | Pool | |
|   ├ `_get_waf_cookies` | 22,2 | 26,6 | 4,4 | | Playwright |
|   ├ `search_amazon` | 26,6 | 28,4 | 1,7 | | |
|   └ `scrape_product_page` ×6 | 28,4 | 33,7 | 5,3 (0,7–1,0/lần) | | tuần tự |
| combine (Bước 2) | 34,6 | 34,6 | 0,0 | | |
| **select_top_deals (Bước 3)** GPT-5-nano | 34,6 | 38,8 | **4,2** | Main | in 3.083 tok / out 294 tok |
| **estimate_prices (Bước 4)** | 38,8 | 94,0 | **55,3** | Main | |
| ├ Deal 1 | 38,8 | 88,3 | 49,6 | | |
| │ ├ preprocess (Groq) | | | 0,7 | | |
| │ ├ **specialist (Modal)** | 39,5 | 85,6 | **46,2** | | **COLD START** → $80 |
| │ ├ frontier RAG (Chroma) | | | 0,3 | | |
| │ ├ frontier GPT-5.1 | | | 2,2 | | in 570 / out 13 tok |
| │ └ neural (DNN) | | | 0,2 | | $234 |
| ├ Deal 2 | 88,3 | 91,6 | 3,3 | | preprocess 1,1 · Modal **0,9** ($60) · RAG 0,0 · GPT-5.1 1,1 · DNN 0,1 ($136) |
| └ Deal 3 | 91,6 | 94,0 | 2,5 | | preprocess 0,3 · Modal **0,9** ($60) · RAG 0,0 · GPT-5.1 1,0 · DNN 0,2 ($111) |
| **TỔNG `fw.run()`** | | | **71,8** | | (chưa tính 22 giây khởi động lần đầu) |

Kết quả lượt đo: $88.00 → ước $149.82 [BestBuy] Sony WH-CH720N; $88.00 → $135.55 [Amazon] Sony WH-CH720N
(cùng một mẫu ở 2 nơi!); $29.99 → $63.58 [Amazon] tai nghe Hybrid ANC.

### 3.2 Lượt đo trước — `air fryer`, 2026-10-28 (chỉ có tổng từng bước)

init agents 11,4 giây · Bước 1: 20,0 giây (6 BestBuy + 6 Amazon; cookie Amazon 5,5 giây) · Bước 3: **25,3 giây** ·
Bước 4: 44,8 giây · **Tổng 90,0 giây** · RAM đỉnh ~3,9 GB. Top 3 đều Amazon: Chefman $79.88 → $136.46; Ninja $99 → $146.51;
Cosori $99 → $133.70. Không auto-notify (discount < $100).

### 3.3 Đọc số đo

- **Modal cold start 46,2 / 71,8 giây = 64%.** Khi ấm chỉ 0,9 giây. Nguyên nhân: `MIN_CONTAINERS = 0` → container tắt sau
  thời gian rảnh, lần sau phải khởi động lại (tải Llama 3B + LoRA lên GPU T4).
- **Khởi động lần đầu 22 giây** (import 10 + Chroma 3,5 + mô hình 8,6) rơi vào **lần bấm tìm đầu tiên** vì code lazy.
- Bước 4 khi Modal ấm ≈ **3 giây/deal × 3 deal tuần tự ≈ 9–10 giây**.
- Bước 1: BestBuy và Amazon đã song song với nhau, nhưng **bên trong mỗi bên tuần tự** (~4–5 giây/bên chỉ để lấy chi tiết).
- Bước 3 **dao động 4,2 → 25,3 giây** với cùng mô hình, cùng cỡ input → độ trễ API OpenAI, không phải code.
- Hầu hết thời gian là **chờ mạng (I/O)**, không phải tính toán (DNN 0,1 giây, RAG 0,0–0,3 giây).

### 3.4 Sau tối ưu — 29/10 (nhánh `toi-uu-search-key`, mốc quay lại: tag `moc-truoc-toi-uu-2026-10-29`) [ĐÃ KIỂM]

Đo bằng script Phụ lục A (bản 29/10: `time.perf_counter()` vì đồng hồ WSL có lúc nhảy lùi ~4 s; thêm đối số `warm`
= đánh thức Modal ngay đầu, như lúc mở app; kết quả JSON ở `/tmp/prof/runs/`). Pushover bị chặn khi đo.

| | Mốc 29/10 sáng | Sau tối ưu |
|---|---|---|
| `wireless headphones` cả lượt | 69,5 s | **21,3 s** (lượt cuối) / 34,3 s |
| `air fryer` cả lượt | 106,7 s | **30,2 s** |
| Lấy cookie Amazon | 22–44 s (trình duyệt chờ ô tìm kiếm tới timeout) | ~5 s |
| Bước 3 chọn deal | nano 3,3–4,4 s (1/3 lượt trả 8 deal) | luna none 4,2–4,9 s, luôn ≤ 3 deal |
| Bước 4 ước giá | 33–40 s (Modal nguội + tuần tự) | ~4 s |
| Modal nguội | chờ 32–46 s | bỏ Llama sau ~10–14 s (3 lời gọi song song: 12,7 s cả nhóm) |
| RAM đỉnh | 3,7–3,9 GB | 3,9 GB |

**Đã đổi (7 commit):** `4f22fe0` cookie Amazon không chờ trang "Continue shopping" · `a3a6b03` luna chọn theo số thứ tự,
code giữ giá/URL, gộp hàng trùng (giữ bản rẻ nhất) · `c2f1b69` trạng thái từng nguồn, ensemble bỏ mô hình lỗi/0 và chia
lại trọng số, chỉ gửi link bestbuy/amazon, Gradio báo lỗi thay vì treo · `8e667cf` đánh thức + giữ ấm Modal phía app,
chờ Llama tối đa 10 s, nạp mô hình khi mở app · `1c44ea1` Bước 4 song song · `d6f6155` ghép tên sản phẩm gốc vào mô tả
(luna có lúc tóm tắt mất tên hãng) · `65109f4` sửa theo kiểm chéo sub-agent (kiểm "bỏ qua" trong khoá; price_is_right
chờ Llama không giới hạn như cũ; PlanningAgent không treo khi gửi tin / ước giá lỗi).

**Chưa làm / còn mở:**
- **Giao diện Gradio chưa bấm thử** sau đợt sửa (User tự thử — app thật gửi Pushover thật).
- **Amazon chặn mềm ngày càng hay gặp:** trang 200 không sản phẩm (2,4 KB khi không lấy được token; ~282 KB có token) —
  3 lần / ~8 lượt 29/10; code thử lại 1 lần, nay log tiêu đề + chữ đầu trang ("Page without results") để nhận dạng rồi mới sửa.
- **Chỗ chậm lớn nhất còn lại:** 6 trang chi tiết Amazon mở tuần tự (0,5–4,1 s / trang) ⇒ P4 (song song 2–3, session riêng).
- **Modal app mới không deploy được** ("Please add a payment method to use T4 GPU functions"). `segment4/pricer_service_v2.py`
  (chưa commit) sẵn sàng nếu User gắn thẻ: scaledown 10 phút, max 1 máy, ghim thư viện, log thời gian cold start.
- Kiểm chéo còn 3 điểm nhỏ chưa sửa (ghi để biết): ping giữ ấm không qua khoá; `dedupe_deals` gộp bắc cầu khi chuỗi trùng
  (giá/URL vẫn đi cặp); `is_store_url` gần như luôn đúng vì URL do code dựng.
- Q5 (giá gốc của shop), Q6 (Llama hay ra $60/$220/$350 — các giá trị lặp lại), P5 (SQLite) chưa làm.

**Frontier đổi GPT-5.1 → gpt-6.1-terra (User chọn 29/10, sau khi đo):** 200 mẫu test đầu `SeanSunny/items_full`, cùng RAG,
1 lượt / cấu hình — gpt-5.1 none MAE $31,16 ($0,179 / 200 mẫu) · luna none $31,42 ($0,013) · luna low $29,69 ($0,018) ·
**terra none $28,51** ($0,130; sát hơn gpt-5.1 ở 87 mẫu, kém hơn 50). So từng mẫu: khoảng 95 % của chênh lệch đều chứa 0 ⇒
chưa vượt nhiễu, chỉ chắc là **không kém** GPT-5.1. Script `/tmp/prof/eval_frontier.py` (đối số `model:effort`).
(MAE $31 thấp hơn số $44,06 của bảng xếp hạng — khác cách / tập đánh giá; so sánh ở đây là cùng 200 mẫu.)

---

## 4. Song song / bất đồng bộ: phân tích

**Kết luận chọn công cụ [SUY LUẬN]:** việc chậm đều là gọi API / tải trang (I/O-bound) → dùng **luồng (`ThreadPoolExecutor`)**
được lợi gần như `async` mà ít phải viết lại; khớp phong cách sẵn có ở `search_and_scrape`. Pipeline đang chạy trong
`threading.Thread` của Gradio (không có event loop) → thêm thread pool là an toàn. Chỉ nên chuyển `async` (AsyncOpenAI,
`litellm.acompletion`, `modal ... .remote.aio`, `curl_cffi.AsyncSession`) nếu sau này cần phục vụ **nhiều người dùng đồng thời**.

| Chỗ | Hiện tại | Có thể | Phụ thuộc / an toàn luồng |
|---|---|---|---|
| 3 deal ở Bước 4 (`estimate_prices`, dòng 132) | Tuần tự | Song song 3 luồng | Độc lập nhau. Log xen kẽ → thêm số thứ tự deal vào log |
| Trong 1 deal (`ensemble.price`) | preprocess → S → F → N tuần tự | preprocess xong → **S ‖ F ‖ N** | 3 mô hình đều cần `rewrite` của preprocess. OpenAI client thread-safe; Modal `.remote()` gọi từ nhiều luồng được (hoặc `.map()`); Chroma query đọc song song được; DNN trên GPU nên bọc `threading.Lock` cho chắc; `SentenceTransformer.encode` nên khoá hoặc gom batch |
| Modal với nhiều deal cùng lúc | — | `pricer.price.map([...])` | [SUY LUẬN] container ấm đang xử lý 1 input/lần (không thấy `allow_concurrent_inputs`) → Modal có thể bật thêm container = thêm cold start + tiền. Cân nhắc gom batch hoặc giới hạn đồng thời = 1 cho Specialist (chỉ 0,9 giây/lần) |
| BestBuy `get_product_details` ×6 | Tuần tự | Song song 3–4 | **`curl_cffi.Session` không bảo đảm thread-safe** → mỗi luồng một session (copy cookie) hoặc `AsyncSession` + `asyncio.gather` |
| BestBuy `get_price_blocks` theo lô | Tuần tự, dừng sớm | Song song 2 lô/lần | Đánh đổi với "dừng sớm" (có thể gọi thừa lô) |
| Amazon `scrape_product_page` ×6 | Tuần tự | Song song **tối đa 2–3** | Dồn dập dễ bị WAF chặn (đã thấy 503 khi dò). Như trên: session riêng mỗi luồng |
| Bước 2 → Bước 3 → Bước 4 | Tuần tự | **Không** song song được | Bước 3 cần đủ pool; Bước 4 cần kết quả Bước 3 |
| Modal warm-up ‖ Bước 1 | — | Bắn 1 lệnh "đánh thức" Modal khi bắt đầu tìm (hoặc khi mở app) | Che cold start sau thời gian Bước 1 + 3 (~16 giây); mở app sớm thì che được hết |

---

## 5. Đề xuất tối ưu thời gian (theo thứ tự lợi ích) [ĐỀ XUẤT]

### P1. Modal cold start — lợi ~45 giây/lượt, công nhỏ

Chọn một hoặc kết hợp:

| Cách | Làm gì | Lợi | Giá phải trả / rủi ro |
|---|---|---|---|
| P1a Warm-up khi mở app | Thread nền gọi `pricer.price.remote("warmup")` (hoặc `.spawn`) ngay khi app khởi động | Cold start xảy ra lúc User đang gõ từ khoá | Nếu User mở app rồi để lâu hơn thời gian giữ ấm → nguội lại |
| P1b Warm-up đầu mỗi lượt tìm | Bắn `.spawn()` lúc bắt đầu Bước 1 | Che ~16 giây (Bước 1 + 3), còn chờ ~30 giây | Không hết hẳn |
| P1c Kéo dài giữ ấm | `scaledown_window=600–900` trong `@app.cls` của `pricer_service2.py`, `modal deploy` lại | Các lượt tìm cách nhau < 10–15 phút luôn ấm | Trả tiền GPU T4 cả lúc rảnh (~$0.59/giờ — [SUY LUẬN] theo giá Modal đã biết, kiểm lại trang giá) |
| P1d Nút "giữ ấm khi demo" (đúng như kế hoạch cũ "Modal Warm-up Button") | Nút Gradio gọi `update_autoscaler(min_containers=1)` / tắt về 0 | Demo cho giáo viên không bao giờ chờ | Quên tắt ≈ $14/ngày |
| P1e Timeout + bỏ qua | Specialist quá ~10 giây → bỏ, chia lại trọng số (0,8/0,9 · F, 0,1/0,9 · N) | Chặn trên thời gian chờ, chống sập | Lượt đó mất 10% đóng góp của Llama (ảnh hưởng nhỏ) |

**Khuyến nghị:** P1a + P1e (rẻ, an toàn), thêm P1d nếu sắp demo. Cần User chọn vì có chi phí tiền (P1c/P1d).
Còn có "memory snapshot" của Modal để giảm cold start — [SUY LUẬN] chưa kiểm, cần đọc tài liệu Modal trước.

### P2. Nạp mô hình ngay khi mở app — lợi ~22 giây ở lần tìm đầu, công nhỏ

`search_key.py` `App.__init__`/`run()`: thread nền gọi `get_framework().init_agents_as_needed()`. Cần khoá
(`threading.Lock`) trong `get_framework` để lần bấm tìm sớm không tạo framework thứ hai. RAM không đổi (vẫn nạp như cũ, chỉ sớm hơn).

### P3. Bước 4 song song — lợi ~6–7 giây (khi Modal ấm: ~10 → ~3 giây)

- `estimate_prices`: `ThreadPoolExecutor(max_workers=3)` cho 3 deal, giữ thứ tự / sort như cũ.
- `EnsembleAgent.price`: sau preprocess, chạy S ‖ F ‖ N (3 luồng). Lock cho DNN.
- Ước sau: preprocess ~0,7 + max(Modal 0,9; RAG 0,3 + GPT-5.1 1,5; DNN 0,2) ≈ **2,5–3 giây cho cả 3 deal**.

### P4. Bước 1 song song bên trong + cache cookie Amazon — lợi ~5–6 giây (~12 → ~6 giây)

- Chi tiết BestBuy song song 3–4; trang sản phẩm Amazon song song 2–3 (session riêng mỗi luồng hoặc `AsyncSession`).
- **Cache cookie WAF** ở mức module/phiên (vd. 10–20 phút), chỉ mở lại Chromium khi `_is_waf_blocked` → tiết kiệm 3–7 giây
  mỗi lượt sau lượt đầu, đỡ RAM (Chromium vài trăm MB mỗi lần). [SUY LUẬN] thời hạn `aws-waf-token` chưa đo — cần thử.
- Có thể khởi động Chromium lấy cookie ngay khi mở app (gộp với P2).

### P5. Cache giá đã ước (SQLite) — lợi: tìm lại sản phẩm cũ gần như tức thì

Bảng (url/ASIN/SKU, mô tả, giá sale, ước lượng, thời điểm). Trùng URL và còn "mới" (vd. < 24 giờ) → dùng lại ước lượng,
bỏ qua 3 mô hình. Đồng thời là dữ liệu cho tính năng **lịch sử giá** (đúng ý "SQLite Deal History" trong kế hoạch cũ).

### P6. Bước 3 — giảm và ổn định độ trễ

- LLM chỉ trả **ID deal + tóm tắt** (xem Q2 ở mục 6) → output ít token hơn.
- Rút `features[:1500]` (unified_deal.py:65) xuống ~600–800 ký tự → input ít hơn (hiện 3.083 tok cho 12 deal).
- Đặt `timeout` + 1 lần retry cho lời gọi OpenAI (đo được 4,2 ↔ 25,3 giây).

**Ước tính tổng [SUY LUẬN]:** làm P1–P4 (+P6) → mỗi lượt khoảng **12–15 giây** thay vì 72–90 giây; lần đầu không còn +22 giây.

---

## 6. Vấn đề độ ổn định & chất lượng (không chỉ tốc độ) [ĐỀ XUẤT]

| # | Vấn đề | Bằng chứng / vị trí | Hệ quả | Đề xuất |
|---|---|---|---|---|
| Q1 | **Một lỗi nhỏ làm sập cả lượt** | `specialist_agent.py:27` không try/except, không timeout; `search_and_scrape` gọi `future.result()` (lỗi mạng một nguồn ném lên trên) | Modal sập / BestBuy timeout → User thấy lỗi, mất cả kết quả nguồn kia | try/except từng mô hình + từng nguồn; nguồn lỗi → `[]`; mô hình lỗi → chia lại trọng số |
| Q2 | **Giá 0 lặng lẽ** | `frontier_agent.py:74` và `pricer_service2.py` trả 0 khi không parse được | Mất 80% (Frontier) → ước lượng rất thấp → "discount" âm/sai mà không ai biết | Coi 0 là lỗi → loại mô hình đó, chia lại trọng số, log cảnh báo |
| Q3 | **LLM tự chép lại giá + URL** ở Bước 3 | `multi_source_scanner_agent.py` — `Deal(product_description, price, url)` do GPT sinh | [SUY LUẬN] rủi ro chép sai/bịa giá hoặc URL (chưa thấy xảy ra) | Đánh số deal; LLM trả `id` + tóm tắt; code lấy giá/URL thật từ pool |
| Q4 | **Sản phẩm trùng** | WH-1000XM5 ×5 màu (BestBuy); Cosori ×2 (Amazon); lượt đo 3.1 chọn **cùng mẫu WH-CH720N ở cả 2 nguồn** | Top 3 kém đa dạng; prompt dài hơn | Gộp trùng trước Bước 3 (chuẩn hoá tên/mã model) |
| Q5 | **Bỏ phí giá gốc của shop** | BestBuy có `regularPrice`/`savingsAmount`; Amazon có `list_price` — không đưa vào `UnifiedScrapedDeal` | Bước 3 chọn theo "mô tả chi tiết nhất" (đúng nguyên văn prompt), không theo "deal tốt nhất" | Đưa giá gốc vào pool; dùng làm tiêu chí chọn và hiển thị cạnh giá AI để kiểm tra chéo |
| Q6 | **Llama trên Modal hay ra $60** | 3/4 lần gọi khác sản phẩm trả đúng $60 (Sony WH-CH720N, tai nghe Hybrid…), 1 lần $80 | [SUY LUẬN] có thể mô hình "kẹt", hoặc định dạng text sau preprocess lệch với lúc train; `max_new_tokens=5` | Thử 10–20 sản phẩm đa dạng, so text đầu vào với format lúc train (`SESSION_HANDOFF_NLP.md` Phase 6) |
| Q7 | DNN lệch xa | $234 cho tai nghe $88 (lượt 3.1) | Trọng số 10% nên ảnh hưởng nhỏ | Ghi nhận; xem lại khi xét thay DNN bằng SentTrans E2E ($44.44 MAE) |
| Q8 | Amazon mong manh | Phụ thuộc WAF + "Deliver to Vietnam" | Có thể hỏng lại bất kỳ lúc nào | Đã có log rõ + retry; về sau cân nhắc theo dõi tỉ lệ thành công |
| Q9 | Cùng lúc 2 lượt tìm | Dùng chung 1 `planner` | Đủ cho demo 1 người; nhiều người → cần khoá/hàng đợi | Ghi nhận, chưa cần |

**Khuyến nghị thứ tự làm (đã nói với User):** **P1 (a+e) + P2 + Q1/Q2** trước — công ít, cắt ~2/3 thời gian chờ, demo không
sập vì dịch vụ ngoài. Sau đó P3 → P4 → Q3/Q4/Q5 → P5/P6.

---

## 7. Cách kiểm chứng sau mỗi thay đổi

1. Chạy script đo ở **Phụ lục A** với cùng từ khoá `wireless headphones` và `air fryer`; so với bảng mục 3 (mốc trước tối ưu).
2. Kiểm cả 2 trường hợp Modal **nguội** (đợi container tắt) và **ấm** (chạy 2 lần liền).
3. Kiểm chống sập: giả lập Modal lỗi (vd. đổi tên app tạm trong biến), giả lập 1 nguồn lỗi mạng → pipeline vẫn ra kết quả.
4. Chạy Gradio thật (`cd segment4 && uv run search_key.py`) và bấm tìm — UI chưa được thử sau đợt sửa cào.
5. Không gửi Pushover thật khi test (script đo đã chặn `messenger.notify`).

---

## 8. Ghi chú môi trường & luật làm việc

- Máy WSL ~15 GB RAM (đã từng treo) → một việc nặng một lúc, luôn có `timeout`. Pipeline đỉnh ~3,9 GB.
- Không đọc/in `.env`; kiểm biến chỉ in "CÓ/KHÔNG".
- Commit/push phải hỏi User. Không `git add` 2 thư mục chưa theo dõi: `segment4/.codegraph/`, `shopping_assistant_v3/`.
- Thử nghiệm Amazon: request thưa, có `sleep`; script thử để ở `/tmp`, không để trong repo.
- `segment4/plan.md` mà `SESSION_HANDOFF_NLP.md` nhắc tới **không còn tồn tại**; các file kế hoạch hiện có:
  `segment4/test_chuc_nang/plan_fix.md`, `.../fix_amazon_v2_s2/plan_amazon.md`, `.../Step3_scrape/plan_step3.md`.
- `pricer_service2.py` có 2 bản giống hệt: `w8/` và `segment4/khong_su_dung/`. Chưa rõ bản nào được `modal deploy` lần cuối
  (app tên `pricer-service`, class `Pricer`) — hỏi User trước khi sửa/deploy lại.
- README.md còn mô tả cũ (Brave Search, Playwright cho mọi bước, top 5, `.env` trong `segment4/`) — `CLAUDE.md` mới đúng.

---

## 9. Việc cần làm ở session tiếp theo

1. **Kiểm lại Amazon còn vào được** (chạy Phụ lục A hoặc 1 lượt `search_filter_scrape_amazon("air fryer", 3)`).
2. Chạy thử Gradio 1 lần.
3. Hỏi User chọn phương án P1 (có chi phí tiền ở P1c/P1d), rồi làm theo thứ tự mục 6 khi User nói "làm đi".
4. Sau mỗi mốc: đo lại bằng Phụ lục A, ghi số "sau tối ưu" vào file này (thêm mục 3.4), commit/push khi User cho phép.

---

## 10. Prompt dán vào đầu session mới

```
Đọc file SESSION_HANDOFF_OPTIMIZE.md (thư mục /home/minhhieu/price2026wsl/tech2ai) để nắm ngữ cảnh,
đọc thêm SESSION_HANDOFF_NLP.md nếu cần bối cảnh dự án.

Dự án: "The Price Is Right" — DACN3, nhánh claudedev.
Session trước (28/10): đã sửa cào BestBuy (1a67113) và Amazon (25dbef4, vượt AWS WAF bằng Playwright cookie + curl_cffi,
ép giá USD), đã đo pipeline: 72–90 giây/lượt, Modal cold start chiếm 64%.

Việc hôm nay:
1. Kiểm lại Amazon còn cào được không (lớp chặn có thể đã đổi).
2. Tối ưu pipeline search_key theo mục 5–6 của file handoff, bắt đầu với P1 (Modal warm-up + timeout),
   P2 (nạp mô hình khi mở app), Q1/Q2 (chống sập). Hỏi tôi chọn phương án P1 trước khi sửa.
3. Đo lại bằng script Phụ lục A, so với mốc mục 3.
```

---

## Phụ lục A — Script đo thời gian từng hàm (không sửa code dự án)

Lưu ra `/tmp/prof/profile_pipeline.py`, chạy từ `segment4/`:

```bash
cd /home/minhhieu/price2026wsl/tech2ai/segment4
/usr/bin/time -f "MAX_RSS_KB %M" timeout 500 uv run python /tmp/prof/profile_pipeline.py "wireless headphones" 2>&1 \
  | sed 's/\x1b\[[0-9;]*m//g' | sed -n '/^=====/,$p;/MAX_RSS/p;/Traceback/,+15p'
```

Lưu ý: nếu code đã được tối ưu (đổi tên hàm, thêm luồng), cập nhật danh sách hàm được bọc cho khớp. Tốn vài cent API mỗi lần.

```python
"""Đo thời gian từng hàm trong pipeline search_key (không sửa code dự án: bọc hàm từ bên ngoài).
Chạy từ segment4/: uv run python /tmp/prof/profile_pipeline.py "<keyword>"
"""
import functools
import sys
import threading
import time

sys.path.insert(0, ".")
T0 = time.time()
EVENTS = []  # (name, start, end, thread, extra)


def timed(name, fn, extra_fn=None):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        s = time.time()
        try:
            r = fn(*a, **kw)
            return r
        finally:
            e = time.time()
            extra = ""
            if extra_fn:
                try:
                    extra = extra_fn(locals().get("r"))
                except Exception:
                    pass
            EVENTS.append((name, s - T0, e - T0, threading.current_thread().name[:12], extra))
    return wrapper


import price_agents.bestbuy_deals as bb
import price_agents.amazon_deals as az

for mod, names in [(bb, ["_init_session", "search_bestbuy", "get_price_blocks", "get_product_details"]),
                   (az, ["_get_waf_cookies", "search_amazon", "scrape_product_page"])]:
    for n in names:
        setattr(mod, n, timed(f"{mod.__name__.split('.')[-1][:2]}.{n}", getattr(mod, n)))

from multi_source_framework import MultiSourceFramework

t = time.time()
fw = MultiSourceFramework()
EVENTS.append(("framework_init(chroma)", t - T0, time.time() - T0, "Main", ""))
t = time.time()
fw.init_agents_as_needed()
EVENTS.append(("init_agents(models)", t - T0, time.time() - T0, "Main", ""))

pl = fw.planner
pl.messenger.notify = lambda **kw: print(">>> [TEST] Pushover bi chan")
pl._bestbuy_pipeline = timed("STEP1.bestbuy_total", pl._bestbuy_pipeline)
pl._amazon_pipeline = timed("STEP1.amazon_total", pl._amazon_pipeline)

usage = lambda r: f"in {r.usage.prompt_tokens} tok / out {r.usage.completion_tokens} tok"
comp = pl.multi_scanner.openai.chat.completions
comp.parse = timed("STEP3.gpt5nano_select", comp.parse, usage)

ens = pl.ensemble
ens.preprocessor.preprocess = timed("S4.preprocess(groq)", ens.preprocessor.preprocess)
ens.specialist.price = timed("S4.specialist(modal)", ens.specialist.price, lambda r: f"${r:.0f}")
ens.frontier.find_similars = timed("S4.frontier.rag(chroma)", ens.frontier.find_similars)
fcomp = ens.frontier.client.chat.completions
fcomp.create = timed("S4.frontier.gpt51", fcomp.create, usage)
ens.neural_network.price = timed("S4.neural(dnn)", ens.neural_network.price, lambda r: f"${r:.0f}")
ens.price = timed("S4.ensemble_one_deal", ens.price)

for step in ["search_and_scrape", "combine", "select_top_deals", "estimate_prices"]:
    setattr(pl, step, timed(f"== {step}", getattr(pl, step)))

kw = sys.argv[1] if len(sys.argv) > 1 else "wireless headphones"
t = time.time()
opps = fw.run(kw, 6, "All")
total = time.time() - t

print("\n" + "=" * 100)
print(f"KEYWORD '{kw}' | pipeline {total:.1f}s | {len(opps)} opportunities")
print(f"{'ham':32s} {'bat dau':>8s} {'ket thuc':>8s} {'mat':>6s}  {'luong':12s} ghi chu")
for name, s, e, th, extra in sorted(EVENTS, key=lambda x: x[1]):
    print(f"{name:32s} {s:8.1f} {e:8.1f} {e - s:6.1f}  {th:12s} {extra}")

print("\nTONG THEO LOAI HAM:")
agg = {}
for name, s, e, *_ in EVENTS:
    a = agg.setdefault(name, [0, 0.0])
    a[0] += 1
    a[1] += e - s
for name, (n, sec) in sorted(agg.items(), key=lambda x: -x[1][1]):
    print(f"  {name:32s} x{n:<3d} tong {sec:6.1f}s  tb {sec / n:5.1f}s")
for o in opps:
    print(f"  ${o.deal.price:>7.2f} -> est ${o.estimate:>7.2f} | {o.deal.product_description[:60]}")
```

---

*Cập nhật file này sau mỗi mốc tối ưu (thêm số đo "sau" vào mục 3.4).*
