---
name: run-experiment
description: Dùng trước khi thử bất kỳ thay đổi nào ở cào dữ liệu / chọn deal / ước giá (ensemble, prompt, mô hình, reasoning effort, trọng số) / viết tin nhắn / tốc độ pipeline, hoặc khi so phương án, đổi mô hình, quyết một thay đổi có giữ hay không. Các bước — lớp bài toán, tiêu chí ghi trước (sàn / mức tụt cho phép / chỉ số quyết), mốc đo nhiễu, đầu vào cố định, đổi một thứ, giữ / gỡ khi vượt nhiễu, kiểm cuối trên dữ liệu chưa thấy, giữ hồ sơ phương án bị bỏ, trần thời gian / tiền. Không dùng cho sửa lỗi nhỏ đã rõ nguyên nhân (dùng practical-project-coding).
---

# Thí nghiệm có kỷ luật — tech2ai

Chuyển thể 29/10/2026 từ skill cùng tên ở một repo khác của User; nguyên tắc lấy từ khoá AI FDE (ghi chú riêng của User:
`session_prompt/ghi_chu_khoa_hoc/GHI_CHU_AI_FDE.md` — chỉ có trên máy User, không commit). Luật trong
`session_prompt/CACH_LAM_VIEC.md` và lời User thắng skill này.

## 1. Trước khi đo — ghi ra (kế hoạch ngắn hoặc mục trong handoff), giờ lấy bằng `date`

1. **Lớp bài toán**, không phải một sản phẩm: "Amazon trả trang 200 không có sản phẩm", không phải "air fryer lượt 3 rỗng".
2. **Thay đổi sẽ thử** — mỗi bản một thứ; ghi giả định và **kiểm giả định bằng máy trước khi code** (29/10: dò trang chủ
   Amazon thấy trang "Continue shopping" trước khi sửa chỗ chờ ô tìm kiếm).
3. **Mục tiêu của đợt** quyết thước đo:
   - **Tối ưu / sửa lỗi** (User 29/10: "chạy ổn như trước, nhanh hơn") ⇒ chất lượng là **sàn không tụt**, chỉ số quyết là
     thời gian / độ ổn định.
   - **Nâng chất lượng** ⇒ chất lượng cần thiết ghi trước **bằng số**; chưa đạt thì tiền / thời gian chỉ là trần cứng, không
     làm lý do gỡ; đạt rồi mới tối ưu hiệu suất.
4. **Tiêu chí ba lớp, ghi trước khi thấy số:** **sàn** (không lỗi; mỗi nguồn có deal; ≤ 3 deal khác nhau; giá USD > 0;
   giá / URL khớp dữ liệu đã cào; Pushover không gửi khi đo) · **mức tụt cho phép** từng chỉ số · **chỉ số quyết** (phải
   vượt nhiễu) tách khỏi chỉ số theo dõi. Định nghĩa chính xác: đếm gì, trên tập nào.
5. **Chỉ số sát mục tiêu nhất có được:** ước giá ⇒ sai số $ và % so giá tham chiếu (giá gốc shop / người ghi), không chỉ
   MAE trên tập test 2023; thông báo ⇒ báo nhầm (FP) / bỏ lỡ deal tốt (FN) theo ngưỡng $100; chọn deal ⇒ đủ 3 deal khác
   nhau, deal tốt bị bỏ / deal xấu bị chọn so một **mốc không dùng LLM** (ví dụ "3 deal giảm nhiều nhất").
6. **Trần:** thời gian (ví dụ 1 giờ), tiền API (OpenAI / Modal — báo User trước khi tiêu nhiều), một việc nặng một lúc.

## 2. Đầu vào và bộ thử

- **Cố định đầu vào trước khi so:** web thay đổi từng phút ⇒ cào một lần, lưu pool (`pickle` các `UnifiedScrapedDeal`) rồi
  chạy mọi cấu hình trên cùng pool (29/10: so nano ↔ luna none ↔ luna low).
- **≤ 20 mẫu / phép thử**, chọn bằng máy (seed ghi trước). Ghi rõ bộ **đã thấy** hay **giữ kín**; bộ đã dùng để quyết từ đó
  chỉ là bộ hồi quy.
- Người chấm: **code** khi chấm được (giá, số deal, khớp URL); lời văn (tin nhắn) ⇒ **agent con chấm mù** (agent không có agent con ⇒ User chấm vài phiếu, hoặc mở phiên agent khác) (phiếu trộn mã,
  không biết bản nào) + 2–3 phiếu đã biết mức để kiểm người chấm. Không dùng chính mô hình đang thử để chấm.

## 3. Đo

1. **Mốc:** cùng đầu vào, cùng cách đo. Bước có LLM / Modal / web ⇒ **≥ 2 lượt** (tốt nhất 3) để thấy nhiễu; so **theo từng
   mẫu**, không chỉ trung bình. Pipeline đầy đủ: thời gian dao động mạnh vì web (Amazon 8–28 s cùng từ khoá) ⇒ báo cả khoảng.
2. **Đổi một thứ**, đo lại đúng như mốc. Mỗi lượt ghi **commit + model + reasoning + tiền (từ `usage`) + giây**.
3. **Đo theo tầng** khi lỗi có thể ở nhiều chỗ: cào (đủ / đúng giá USD?) → chọn deal → tiền xử lý (preprocess) → từng mô
   hình (Frontier / Llama / DNN) → ensemble → thông báo.
4. **Chạy thật**, không mock. Lỗi provider / mạng / chặn là kết quả quan sát được — ghi lại, không che.
5. Script đo dùng lại: `scripts/do_luong/` (README trong đó — pipeline, pool deal, MAE Frontier, Modal nguội). Bọc hàm từ
   ngoài, không sửa code dự án; đối số `warm` = đánh thức Modal trước.

## 4. Kết luận

- **Tốt hơn / không đổi / kém hơn / chưa rõ** theo tiêu chí đã ghi; **không đổi tiêu chí sau khi thấy số**.
- **Luật giữ / gỡ** (đủ cả ba mới giữ): không phạm sàn; không chỉ số nào tụt quá mức cho phép; ít nhất một chỉ số quyết tăng
  **vượt nhiễu**. Ngưỡng thực dụng — không viết "đã chứng minh".
- Một chỉ số tăng ≠ tốt hơn mọi mặt: báo cả chỉ số tụt (29/10: luna nhanh hơn ở một pool, chậm ~1 s ở pool kia).
- **Kiểm cuối trên dữ liệu chưa thấy** (từ khoá / sản phẩm chưa dùng để chỉnh) trước khi coi là xong.
- 3 vòng sửa không đạt ⇒ dừng, ghi giới hạn, báo User.

## 5. Hồ sơ — kể cả khi bỏ

Phương án không dùng vẫn ghi: số đo, tiền, giây, vì sao bỏ (ví dụ Bước 3 chọn deal — luna `low`: 4,6–5,3 s so `none` 4,2–4,3 s, cùng 6/6
đủ deal ⇒ chọn `none`). Ghi vào `docs/changelog/` (file của thay đổi + bảng "Đã thử, chưa áp dụng"). Kết thúc bằng **3–5 dòng lời thường cho User**: đã thử gì, vì sao, kết quả,
quyết định, giới hạn.
