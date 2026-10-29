# Sổ cải tiến cách làm

**Cập nhật lần cuối: 13:15, ngày 29/10/2026** (vòng 1). Skill: `improve-workflow`. Xét lại các mục `đang thử` **mỗi tuần
một lần** (lần tới: tuần sau 05/11/2026).
Trạng thái: `đề xuất` → `đang thử` (User duyệt) → `đang dùng` (sự cố không lặp, luật được dùng) / `gỡ` (2 phiên thật không
ai cần hoặc gây vướng) / `bác`.

| # | Ngày | Sự cố — bằng chứng | Lần | Mất gì | Thay đổi (ở đâu) | Trạng thái | Xem lại |
|---|---|---|---|---|---|---|---|
| 1 | 29/10 | Sửa `messaging_agent.py`, `scanner_agent.py` bằng script Python đọc / ghi văn bản ⇒ CRLF thành LF, diff cả file (145 + 249 dòng) | 1 | ~2 phút, bắt được nhờ `git diff --stat` | 1 dòng bẫy "giữ `\r\n` khi sửa bằng script" — `CACH_LAM_VIEC.md` mục 7, skill `practical-project-coding` cổng 4 | đang thử | có diff cả file lần nào nữa không |
| 2 | 29/10 | Script đo dùng `time.time()` ⇒ thời gian âm (đồng hồ WSL nhảy lùi ~4 s) | 1 | một bảng đo sai, đo lại | "đo bằng `time.perf_counter()`" — `CACH_LAM_VIEC.md` mục 7, `practical-project-coding` cổng 3 | đang thử | — |
| 3 | 29/10 | Đổi timeout Llama + chạy song song: lượt đo đơn lẻ không bắt được (a) Modal nguội + 3 deal song song ⇒ ~30 s, (b) `price_is_right` dùng chung `SpecialistAgent` bị đổi hành vi, (c) `PlanningAgent` có thể treo khi gửi tin lỗi — agent con đọc diff bắt cả 3 | 1 | 3 lỗi major lọt qua 6 commit; sửa ~20 phút | (1) "tìm mọi bên gọi hàm dùng chung" — `practical-project-coding` cổng 1; (2) "agent con ngữ cảnh mới đọc diff trước commit" — `CACH_LAM_VIEC.md` mục 8 | đang thử | việc lớn tới có chạy đọc diff trước commit không |
| 4 | 29/10 | Script ở `/tmp` dùng `load_dotenv()` ⇒ tìm `.env` từ thư mục của script, không thấy khoá | 1 | ~1 phút | `load_dotenv(find_dotenv(usecwd=True))` — `practical-project-coding` mục Môi trường | đang thử | — |
| 5 | 29/10 | Đổi sang luna `none` ở Bước 3: tóm tắt có lúc mất tên hãng ⇒ bảng kết quả không biết hàng gì, giá ước lệch | 1 | phát hiện ở lượt kiểm hồi quy cuối; sửa bằng code ghép tên gốc | ý chờ: kiểm hồi quy đọc cả **nội dung** đầu ra (mô tả, tên), không chỉ số lượng / giá | ý chờ | lặp ⇒ thêm vào `run-experiment` mục sàn |

## Ý chờ (chưa có sự cố, chưa thành luật)

- Hook cảnh báo giờ ước (`HH:Mx`) khi ghi vào `session_prompt/` — repo khác của User cần tới sau ≥ 13 lần vi phạm; ở đây
  chưa vi phạm lần nào.
- Review kế hoạch việc lớn bằng một mô hình khác trước khi dựng (khoá AI FDE).
