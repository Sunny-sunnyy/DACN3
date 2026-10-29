# AI Price Intelligence System — DACN3 ("The Price Is Right")

Hệ thống AI nhiều tác tử (multi-agent) tìm sản phẩm đang giảm giá trên **BestBuy** và **Amazon**, ước lượng giá trị thật bằng
một **ensemble 3 mô hình**, và gửi thông báo đẩy (Pushover) khi gặp deal tốt.

*Cập nhật lần cuối: 29/10/2026.*

---

## Hai ứng dụng

### 1. Multi-Source Deal Finder — `segment4/search_key.py`

Người dùng nhập từ khoá; pipeline 4 bước:

```
Từ khoá
  │
  ├─ Bước 1  Cào song song: BestBuy (API nội bộ, curl_cffi) ‖ Amazon (Playwright lấy cookie WAF → curl_cffi + HTML)
  │          mỗi nguồn tối đa N sản phẩm đang sale; mỗi nguồn báo trạng thái ok / empty / blocked / error
  ├─ Bước 2  Gộp thành một danh sách chung, gộp hàng trùng (cùng mẫu khác màu → giữ bản rẻ nhất)
  ├─ Bước 3  gpt-6-luna chọn 3 deal (trả số thứ tự + tóm tắt; giá và URL do code lấy từ dữ liệu đã cào)
  └─ Bước 4  Ensemble ước giá 3 deal song song
             → bảng kết quả trên Gradio; giảm > $100 thì tự gửi Pushover (chỉ cho link bestbuy.com / amazon.com)
```

Thời gian đo ngày 29/10/2026 (Modal đã được đánh thức): **21–34 giây / lượt**, trước tối ưu 70–107 giây.

### 2. Autonomous Deal Hunter — `segment4/price_is_right.py`

Cứ 5 phút quét RSS của DealNews → gpt-6-luna chọn deal → ensemble ước giá → giảm > $50 thì gửi Pushover → lưu
`memory.json` để không báo trùng.

---

## Ensemble ước giá

| Mô hình | Trọng số | Mô tả |
|---|---|---|
| **FrontierAgent** | 80 % | gpt-6-luna (reasoning `low`) + RAG: 5 sản phẩm giống nhất trong ChromaDB (800.000 sản phẩm) |
| **SpecialistAgent** | 10 % | Llama-3.2-3B fine-tune bằng QLoRA, chạy trên GPU T4 của Modal |
| **NeuralNetworkAgent** | 10 % | mạng nơ-ron sâu PyTorch (ResidualBlocks, 289 triệu tham số), chạy trên máy |

```
giá ước = 0,8 × Frontier + 0,1 × Specialist + 0,1 × DNN      (mô hình lỗi / trả 0 thì bỏ và chia lại trọng số)
discount = giá ước − giá bán
```

Trước khi vào ensemble, mô tả sản phẩm được viết lại theo khuôn `Title / Category / Brand / Description / Details`
(Groq `gpt-oss-20b` qua LiteLLM) — giống khuôn dữ liệu lúc huấn luyện.

Sai số trên 200 mẫu test (`SeanSunny/items_full`, đo 29/10/2026, 1 lượt / cấu hình): Frontier GPT-5.1 MAE $31,16 →
gpt-6-luna low $29,69 (không kém, rẻ hơn ~10 lần). Bảng xếp hạng các mô hình đã thử khi huấn luyện:
`session_prompt/archive/SESSION_HANDOFF_NLP.md` mục 12.

---

## Nên thử với từ khoá nào

Mô hình được huấn luyện trên **8 nhóm hàng Amazon (dữ liệu 2023)** — Automotive, Electronics, Office Products, Tools &
Home Improvement, Cell Phones & Accessories, Toys & Games, Appliances, Musical Instruments — và **chỉ hàng giá $0,5–$999,49**.

| Nên thử | Nên tránh |
|---|---|
| `noise cancelling headphones`, `soundbar`, `gaming monitor`, `action camera`, `digital piano`, `cordless drill`, `electric guitar` | `laptop`, `gaming laptop`, `smart tv` — nhiều sản phẩm > $999 (vượt vùng huấn luyện ⇒ ước thấp) |
| giá thường $100–$500 ⇒ dễ có discount > $100 | `air fryer`, `coffee maker`, `microwave`, `blender` — **không có nhóm đồ bếp** trong dữ liệu (hàng xóm RAG sai loại) |
| | `phone case`, `wireless earbuds` — quá rẻ, hiếm khi giảm > $100 |

Kiểm lại bằng `scripts/do_luong/probe_keywords.py` (tra 20 sản phẩm gần nhất trong ChromaDB, không tốn API).

---

## Cấu trúc

```
tech2ai/
├── segment4/                         code đang chạy
│   ├── search_key.py                 app 1 (Gradio)
│   ├── price_is_right.py             app 2 (Gradio, tự chạy 5 phút / lần)
│   ├── multi_source_framework.py     framework của app 1 (ChromaDB, nạp agent)
│   ├── deal_agent_framework.py       framework của app 2 (memory.json)
│   ├── price_agents/                 các agent: planning, ensemble, frontier, specialist, neural network,
│   │                                 preprocessor, messaging, scanner, cào BestBuy / Amazon, data models
│   ├── bestbuy_untils/               chọn deal (multi_source_scanner_agent), gộp nguồn (unified_deal), Gradio helpers
│   ├── mo_ta_du_an/                  tài liệu chi tiết từng app
│   ├── products_vectorstore/         ChromaDB 800.000 sản phẩm (không đưa lên GitHub)
│   └── khong_su_dung/                code cũ không còn dùng (Brave MCP scanner, pricer_service2.py…)
├── scraping_data_tv/                 xử lý dữ liệu, huấn luyện DNN / DL, fine-tune Llama (notebook + báo cáo)
├── w8/                               notebook tuần 8 (RAG + ensemble), pricer_service2.py (Modal)
├── scripts/do_luong/                 script đo dùng lại (pipeline, MAE Frontier, từ khoá…)
├── docs/changelog/                   ghi chép từng thay đổi code (trước / sau, số đo)
└── session_prompt/                   cách làm việc cho coding agent (START_SESSION, CACH_LAM_VIEC, CURRENT_HANDOFF)
```

---

## Cài đặt và chạy

Yêu cầu: Python 3.12, [`uv`](https://docs.astral.sh/uv/), GPU CUDA (khuyến nghị cho DNN), tài khoản Modal (app
`pricer-service` đã deploy), khoá OpenAI / Groq.

```bash
cd tech2ai
uv sync                                   # cài thư viện theo uv.lock
uv run playwright install chromium        # Chromium chạy ngầm để lấy cookie AWS WAF của Amazon

cd segment4
uv run search_key.py                      # app 1 → http://127.0.0.1:7860
uv run price_is_right.py                  # app 2 → http://127.0.0.1:7860
```

File `.env` đặt ở **`tech2ai/.env`** (không commit):

```env
OPENAI_API_KEY=...                        # bắt buộc (gpt-6-luna)
GROQ_API_KEY=...                          # bắt buộc với preprocessor mặc định
PRICER_PREPROCESSOR_MODEL=groq/openai/gpt-oss-20b
PUSHOVER_USER=...                         # tuỳ chọn — thông báo đẩy
PUSHOVER_TOKEN=...
HF_TOKEN=...                              # tải dataset / model từ HuggingFace
```

Modal đọc token ở `~/.modal.toml`. Máy Modal tự tắt sau 60 giây rảnh; `search_key.py` đánh thức nó khi mở app và giữ ấm
trong lúc có người dùng (dừng sau 15 phút không tìm).

---

## Tech stack

| Lớp | Công nghệ |
|---|---|
| Giao diện | Gradio |
| Cào dữ liệu | `curl_cffi` (giả TLS Chrome) + BeautifulSoup4; Playwright Chromium chỉ để lấy cookie WAF của Amazon |
| LLM | OpenAI gpt-6-luna (Frontier, chọn deal, viết tin nhắn); Groq gpt-oss-20b (viết lại mô tả) qua LiteLLM |
| Mô hình fine-tune | Llama-3.2-3B, QLoRA 4-bit NF4, adapter `SeanSunny/price-2026-final`, chạy trên Modal T4 |
| Mạng nơ-ron | PyTorch DNN (HashingVectorizer 5000 → 8 ResidualBlocks 4096) |
| Vector DB | ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` |
| Thông báo | Pushover API |
| Quản lý gói | uv |
| Dataset | HuggingFace `SeanSunny/items_lite`, `SeanSunny/items_full` (820.000 sản phẩm) |

---

## Tài liệu chi tiết

- [`segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`](segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md) — Multi-Source Deal Finder
- [`segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md`](segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md) — Autonomous Deal Hunter
- [`scraping_data_tv/Data_processing_for_English_data/Report_data_processing_v2.md`](scraping_data_tv/Data_processing_for_English_data/Report_data_processing_v2.md) — dữ liệu, mô hình truyền thống, DNN
- [`scraping_data_tv/Data_processing_for_English_data/report_fine_tune_llm.md`](scraping_data_tv/Data_processing_for_English_data/report_fine_tune_llm.md) — fine-tune Llama 3.2 bằng QLoRA
- [`docs/changelog/README.md`](docs/changelog/README.md) — các thay đổi gần nhất và phương án đã thử

---

## Tác giả

**Phạm Minh Hiếu** — [@Sunny-sunnyy](https://github.com/Sunny-sunnyy) · Đồ án chuyên ngành DACN3, 2026
