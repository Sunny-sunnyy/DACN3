# CH-20261029-05 — Bước 4 chạy song song (3 deal × 3 mô hình)

29/10/2026 · Claude Code (Opus) · nhánh `toi-uu-search-key` · commit `1c44ea1`

## Giải thích ngắn
Trước đây 3 deal được ước giá lần lượt, và trong mỗi deal 3 mô hình cũng chạy lần lượt — phần lớn thời gian là chờ mạng
(OpenAI, Modal). Giờ 3 deal chạy cùng lúc, và sau bước viết lại mô tả, 3 mô hình của mỗi deal cũng chạy cùng lúc.

## A. Trước
- `estimate_prices` vòng `for` tuần tự; `EnsembleAgent.price` gọi specialist → frontier → neural tuần tự.
- Khi Modal ấm: ~2,5–3 s / deal ⇒ ~9–10 s cho 3 deal; mốc có cold start 33–40 s.

## B. Sau
- `multi_source_planning_agent.py`: `_estimate_one` + `ThreadPoolExecutor` cho các deal.
- `ensemble_agent.py`: `ThreadPoolExecutor(3)` cho 3 mô hình.
- Khoá cho phần chạy trên GPU máy mình: `frontier_agent.py` (encode + query Chroma), `neural_network_agent.py` (DNN).
- Đo (`wireless headphones`, Modal đã đánh thức): Bước 4 **3,9 s**, cả 3 deal đủ 3 mô hình; cả lượt 69,5 s (mốc) ⇒ 34,3 s,
  lượt cuối 21,3 s; RAM đỉnh 3,9 GB (không đổi).

## C. Còn tồn tại
- Việc chậm nhất vẫn quyết thời gian: Modal nguội ⇒ ~10–14 s.

## D. Kiểm độc lập
Agent con đọc diff: hai tầng ThreadPoolExecutor không thể kẹt (không khoá nào giữ trong lúc chờ future); `_safe_price` bắt mọi
lỗi. Lỗi ghép với khoá của Llama lúc Modal nguội ⇒ CH-20261029-06.
