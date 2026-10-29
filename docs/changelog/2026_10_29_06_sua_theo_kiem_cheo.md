# CH-20261029-06 — Sửa theo kiểm chéo + ghép tên sản phẩm gốc vào mô tả

29/10/2026 · Claude Code (Opus) · nhánh `toi-uu-search-key` · commit `d6f6155`, `65109f4`

## Giải thích ngắn
Một agent con (không biết gì về phiên làm việc) đọc toàn bộ thay đổi và tìm ra 3 lỗi thật mà các lượt đo không bắt được;
đã sửa cả 3. Ngoài ra, lượt kiểm cuối cho thấy luna có lúc tóm tắt sản phẩm mà không nhắc tên hãng ⇒ code tự ghép tên gốc
vào đầu mô tả.

## A. Trước
1. `SpecialistAgent`: kiểm "đang bỏ qua" ngoài khoá ⇒ Modal nguội + 3 deal song song: 3 lần chờ 10 s nối nhau (~30 s).
2. Giới hạn 10 s áp cả cho `price_is_right` (quét 5 phút / lần, không giữ ấm) ⇒ Llama gần như luôn bị bỏ — đổi hành vi app thứ hai.
3. `PlanningAgent` (price_is_right) không bắt lỗi gửi tin / lỗi ensemble ⇒ có thể treo vòng cập nhật giao diện.
4. Tóm tắt luna `none`: "This 6-quart air fryer…" — mất hãng; Ninja DoubleStack $229,99 ước $167 (lượt có tên: $212).

## B. Sau
1. Kiểm "bỏ qua" bên trong khoá. Thử Modal thật (nguội, 3 lời gọi song song): cả nhóm **12,7 s**.
2. `SpecialistAgent(timeout_seconds=None)` mặc định chờ như cũ; `MultiSourcePlanningAgent.SPECIALIST_TIMEOUT_SECONDS = 10`
   truyền qua `EnsembleAgent(specialist_timeout=…)`.
3. `planning_agent.py`: deal không ước được ⇒ bỏ deal; gửi tin lỗi ⇒ ghi log.
4. Mô tả = `[Nguồn] <tên gốc>. <tóm tắt của luna>`.
- Thêm: khoá khi bật lại luồng giữ ấm; đánh thức Modal có `try` riêng (lỗi Modal không chặn nạp mô hình).
- Kiểm hồi quy cuối `wireless headphones`: **21,3 s**, 3 deal, ước giá gần mốc (WH-CH720N $88: $140,51 ⇒ $136,33).

## C. Còn tồn tại
- `price_is_right` chưa được chạy thật sau thay đổi (chỉ import + đọc code).

## D. Kiểm độc lập
Chưa có lượt đọc diff độc lập cho chính các sửa này; phần Modal đã thử với Modal thật.
