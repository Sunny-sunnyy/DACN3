# Ghi chép thay đổi code

**Cập nhật lần cuối: 13:15, ngày 29/10/2026.**
Mỗi thay đổi code **một file** `YYYY_MM_DD_<số>_<tên_ngắn>.md`, viết ngay khi sửa xong (trước commit), và **một dòng** trong
bảng dưới. Luật chung: `session_prompt/CACH_LAM_VIEC.md` mục 9.

## Khuôn một file

```
# CH-<YYYYMMDD>-<số> — <tên thay đổi>
Ngày · người sửa (agent / model) · nhánh · commit
## Giải thích ngắn      2–3 câu lời thường: trước sai / chậm gì, giờ khác gì, ảnh hưởng người dùng
## A. Trước             vấn đề, bằng chứng, số đo
## B. Sau               đổi gì (file, hàm), số đo cùng đầu vào, hồi quy
## C. Còn tồn tại       giới hạn, NOT RUN, việc dở
## D. Kiểm độc lập      ai kiểm (agent con đọc diff / phiên khác / "chưa kiểm độc lập"), phát hiện, đã xử lý thế nào
```

Phương án **đã thử mà không dùng** cũng ghi (ở file của thay đổi liên quan và ở bảng cuối).

## Mục lục

| Mã | Ngày | Thay đổi | Kiểm độc lập | Commit |
|---|---|---|---|---|
| [CH-20261029-01](2026_10_29_01_amazon_cookie.md) | 29/10 | Amazon: không chờ ô tìm kiếm 20 s, giữ cookie WAF | agent con đọc diff: OK | `4f22fe0` |
| [CH-20261029-02](2026_10_29_02_chon_deal_luna.md) | 29/10 | Bước 3: luna chọn theo số thứ tự, code giữ giá / URL, gộp hàng trùng; đổi nano / mini ⇒ luna | agent con: OK (1 minor ghi lại) | `a3a6b03` |
| [CH-20261029-03](2026_10_29_03_chong_sap.md) | 29/10 | Trạng thái từng nguồn; ensemble bỏ mô hình lỗi / 0; kiểm link trước khi gửi; Gradio báo lỗi | agent con: 1 major (price_is_right) ⇒ sửa ở -06 | `c2f1b69` |
| [CH-20261029-04](2026_10_29_04_modal_giu_am.md) | 29/10 | Đánh thức + giữ ấm Modal, chờ Llama tối đa 10 s, nạp mô hình khi mở app | agent con: 2 major ⇒ sửa ở -06 | `8e667cf` |
| [CH-20261029-05](2026_10_29_05_song_song_buoc4.md) | 29/10 | Bước 4 song song (3 deal × 3 mô hình) | agent con: OK | `1c44ea1` |
| [CH-20261029-06](2026_10_29_06_sua_theo_kiem_cheo.md) | 29/10 | Sửa theo kiểm chéo + ghép tên sản phẩm gốc vào mô tả | chưa kiểm độc lập (đã thử Modal thật) | `d6f6155`, `65109f4` |
| [CH-20261029-07](2026_10_29_07_frontier_luna.md) | 29/10 | Frontier GPT-5.1 ⇒ gpt-6-luna low (thử terra trước) | chưa đọc diff độc lập (đã đo 200 mẫu) | `ae00fa3`, `4d7aaf2` |

## Đã thử, chưa áp dụng

| Phương án | Số đo | Vì sao không dùng | Ở đâu |
|---|---|---|---|
| luna `low` cho Bước 3 (chọn deal) | 4,6–5,3 s, 6/6 đủ 3 deal | `none` nhanh hơn (4,2–4,3 s), cùng chất lượng | CH-20261029-02 |
| gpt-6.1-terra `none` cho Frontier | MAE $28,51 / 200 mẫu, $0,130 | không phân biệt được với luna low ($29,69), đắt hơn ~7 lần | CH-20261029-07 |
| luna `none` cho Frontier | MAE $31,42, $0,013 | luna low sát hơn ~$1,7, tiền chênh rất nhỏ | CH-20261029-07 |
| App Modal mới `pricer-service-v2` (giữ ấm 10 phút, tối đa 1 máy, ghim thư viện) | NOT RUN | Modal chặn deploy app GPU mới khi chưa gắn thẻ; file `segment4/pricer_service_v2.py` (chưa commit) | CH-20261029-04 |
| Mở song song trang chi tiết Amazon (P4) | NOT RUN | ngoài phạm vi đợt 29/10; rủi ro bị chặn IP | `session_prompt/CURRENT_HANDOFF.md` |
