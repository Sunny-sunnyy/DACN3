# Implementation Plan — search_key.py Improvements

**App target:** `search_key.py` (Multi-Source Deal Finder)
**Date:** 2026-05-08
**Status:** Planning

---

## Feature 1: Modal Warm-up Button

**Vấn đề:** SpecialistAgent (Llama-3.2-3B trên Modal) có cold start 30-60s nếu container đang ngủ. Lần chạy đầu tiên luôn chậm.

**Giải pháp:** Thêm button "Warm up Llama" trên Gradio UI. Khi bấm, gọi `update_autoscaler` để giữ container warm trong 20 phút.

**Kỹ thuật (từ notebook d1_specialist_agent.ipynb):**
```python
import modal
Pricer = modal.Cls.from_name("pricer-service", "Pricer")
pricer = Pricer()
pricer.update_autoscaler(scaledown_window=1200)  # 20 phút
```

**Files cần thay đổi:**
- `search_key.py` — Thêm button `warm_up_btn` + handler `warm_up_handler()`
- `multi_source_framework.py` — Thêm method `warm_up_specialist()`
- `price_agents/specialist_agent.py` — Thêm method `warm_up()`

**Verify:** Bấm button → log xuất hiện "Warming up Modal..." → sau ~5s log "Llama is ready" → lần chạy tiếp theo không có cold start delay.

---

## Feature 2: SQLite Deal History Database

**Vấn đề:** Mỗi lần search, deals bị mất. Không biết sản phẩm hôm nay rẻ hơn hay đắt hơn tuần trước.

**Giải pháp:** Lưu tất cả deals (bao gồm estimated price) vào SQLite sau mỗi lần pipeline chạy. Hiển thị price history trên Gradio.

**Schema:**
```sql
CREATE TABLE deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    keyword TEXT,
    source TEXT,           -- "BestBuy" hoặc "Amazon"
    title TEXT,
    price REAL,
    estimated_price REAL,
    discount REAL,
    url TEXT UNIQUE
);
```

**Files cần tạo/thay đổi:**
- `price_agents/deals_db.py` — Class `DealsDB` với methods: `save_deal()`, `get_price_history(url)`, `get_recent_deals(keyword)`
- `multi_source_framework.py` — Init `DealsDB`, gọi `save_deal()` sau mỗi pipeline run
- `search_key.py` — Thêm tab "Price History" trên Gradio với Plotly line chart

**Verify:** Chạy search "laptop" 2 lần → check SQLite có 6 rows (3 deals × 2 lần) → click vào deal → thấy chart giá theo thời gian.

---

## Feature 3: Review Sentiment Agent

**Vấn đề:** Deal rẻ có thể là "bẫy" — sản phẩm lỗi, review xấu, chất lượng kém.

**Giải pháp:** Sau khi select top 3 deals (Step 3), scrape 5-10 reviews từ Amazon cho mỗi deal, dùng GPT-5-nano phân tích sentiment và tìm "Red Flags".

**Output:**
```
Sentiment: POSITIVE (4.2/5) — Không có red flags đáng kể.
Sentiment: WARNING (2.8/5) — Red flags: "overheating", "battery drain", "poor build quality"
```

**Pipeline change:**
```
Step 3: select_top_deals() → DealSelection (top 3)
Step 3.5 (NEW): analyze_reviews() → {deal_url: SentimentResult} cho mỗi deal Amazon
Step 4: estimate_prices() → List[Opportunity]  (thêm sentiment_score vào Opportunity)
```

**Files cần tạo/thay đổi:**
- `price_agents/review_agent.py` — Class `ReviewSentimentAgent`: scrape reviews từ Amazon bằng `curl_cffi`, gọi GPT-5-nano phân tích
- `price_agents/deals.py` — Thêm field `sentiment_score: Optional[float]` và `red_flags: List[str]` vào `Opportunity`
- `price_agents/multi_source_planning_agent.py` — Gọi `analyze_reviews()` sau Step 3
- `bestbuy_untils/gradio_helpers.py` — Cập nhật `opportunities_to_html()` để hiển thị sentiment badge

**Verify:** Search "headphones" → kết quả hiển thị sentiment badge (xanh/vàng/đỏ) bên cạnh mỗi deal.

---

## Feature 4: Pipeline Profiling

**Vấn đề:** Chưa biết chính xác step nào chiếm nhiều thời gian nhất.

**Giải pháp:** Thêm timing decorator/context manager vào từng step, log thời gian thực thi.

**Output log mong muốn:**
```
[MultiSourcePlanningAgent] Step 1 Search+Scrape: 7.2s (BestBuy: 5.1s, Amazon: 6.8s parallel)
[MultiSourcePlanningAgent] Step 2 Combine: 0.05s
[MultiSourcePlanningAgent] Step 3 Select top 3: 4.3s
[MultiSourcePlanningAgent] Step 4 Estimate prices: 52.1s
  - Deal 1 Preprocessor: 3.2s | Frontier: 4.1s | Specialist: 18.3s | Neural: 0.1s
  - Deal 2 Preprocessor: 2.8s | Frontier: 3.9s | Specialist: 2.1s | Neural: 0.1s
  - Deal 3 Preprocessor: 3.0s | Frontier: 4.2s | Specialist: 2.0s | Neural: 0.1s
[MultiSourcePlanningAgent] Total: 63.6s
```

**Files cần thay đổi:**
- `price_agents/multi_source_planning_agent.py` — Thêm `time.perf_counter()` vào từng step
- `price_agents/ensemble_agent.py` — Log thời gian từng sub-agent

**Verify:** Chạy pipeline → log hiển thị thời gian chi tiết từng step.

---

## Thứ tự triển khai

| Thứ tự | Feature | Độ phức tạp | Giá trị |
|--------|---------|-------------|---------|
| 1 | Pipeline Profiling | Thấp | Cần thiết trước khi tối ưu |
| 2 | Modal Warm-up Button | Thấp | Quick win, giảm frustration ngay |
| 3 | SQLite Deal History | Trung bình | Nền tảng cho price history |
| 4 | Review Sentiment Agent | Cao | Tính năng AI ấn tượng nhất |

---

## Notes

- Không thay đổi `price_is_right.py` trong giai đoạn này
- Không parallel hóa Ensemble chưa — đo profiling trước, quyết định sau
- `DealsDB` dùng raw `sqlite3`, không dùng ORM (SQLAlchemy overkill)
- `ReviewSentimentAgent` chỉ scrape Amazon deals (BestBuy không public reviews dễ)
