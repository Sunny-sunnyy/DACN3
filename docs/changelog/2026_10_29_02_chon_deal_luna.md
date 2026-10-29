# CH-20261029-02 — Bước 3: luna chọn theo số thứ tự, code giữ giá / URL, gộp hàng trùng

29/10/2026 · Claude Code (Opus) · nhánh `toi-uu-search-key` · commit `a3a6b03`

## Giải thích ngắn
Trước đây mô hình nano tự **chép lại** giá và URL của 3 deal nó chọn (có thể chép sai) và có lần trả 8 deal dù chỉ được chọn
3. Giờ luna chỉ trả **số thứ tự** của deal kèm tóm tắt; giá và URL do code lấy từ dữ liệu đã cào. Sản phẩm trùng (cùng mẫu
khác màu) được gộp trước, giữ bản rẻ nhất.

## A. Trước
- `bestbuy_untils/multi_source_scanner_agent.py`: gpt-5-nano, `reasoning_effort="minimal"`, schema `DealSelection` có giá + URL do mô hình viết.
- So trên pool đã lưu (2 từ khoá × 3 lượt): 1/3 lượt `air fryer` trả **8 deal**; BestBuy trả 5 màu WH-1000XM5 cùng URL, giá $228–$298.
- gpt-6-luna không nhận `"minimal"`.

## B. Sau
- Schema mới `PickedDeals(deal_number, product_description)`; code ghép `Deal(price, url)` từ pool, bỏ số không hợp lệ / lặp, tối đa 3.
- `dedupe_deals`: gộp theo (nguồn, URL) hoặc (nguồn, tên bỏ từ chỉ màu), giữ bản rẻ nhất.
- Bỏ URL khỏi prompt (`UnifiedScrapedDeal.describe(include_url=False)`); nhãn `[BestBuy]` / `[Amazon]` do code gắn.
- Đổi nốt: `messaging_agent.py` (luna qua LiteLLM, cần `allowed_openai_params=["reasoning_effort"]`), `scanner_agent.py`
  (price_is_right; dòng `MODEL` bị ghi đè cũ đã gỡ), `clarification_agent.py`.
- Đo (cùng pool, 3 lượt): luna `none` trung vị 4,2–4,3 s, **6/6** lượt đủ 3 deal khác nhau, 0 sai giá / URL; nano 3,3–4,4 s, 5/6.

## C. Còn tồn tại
- Không có đáp án "deal đúng" để chấm chất lượng lựa chọn; chưa so với mốc không dùng LLM (ví dụ "3 deal giảm nhiều nhất").
- Tóm tắt của luna `none` có lúc mất tên hãng ⇒ sửa ở CH-20261029-06.

## D. Kiểm độc lập
Agent con đọc diff: ánh xạ số thứ tự ↔ pool, schema ↔ lời gọi parse đúng. Minor (ghi lại, không sửa): `dedupe_deals` gộp kiểu
"bắc cầu" khi chuỗi trùng phức tạp — giá / URL vẫn đi cặp, khó gặp với dữ liệu thật.

**Đã thử, chưa áp dụng:** luna `low` 4,6–5,3 s, cùng 6/6 ⇒ chọn `none`.
