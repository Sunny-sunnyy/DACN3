---
name: improve-workflow
description: Dùng lúc kết phiên, khi User phải nhắc / sửa agent cùng một lỗi lần thứ hai, khi một sự cố quy trình làm mất giờ / tiền / dữ liệu (đo nhầm bản, chạy lại mù tốn tiền, sửa file mất kiểu xuống dòng, ghi giờ ước…), hoặc khi User xin "rút kinh nghiệm", "cải tiến cách làm". Biến sự cố có bằng chứng thành ≤ 3 đề xuất sửa skill / CLAUDE.md / rào bằng máy cho User duyệt, gỡ luật thừa, ghi sổ cải tiến, xét lại mỗi tuần. Không dùng để đổi mục tiêu, tiêu chí đo hay code app.
---

# Tự cải tiến cách làm — tech2ai

Chuyển thể 29/10/2026 từ skill cùng tên ở một repo khác của User. Nguyên tắc (khoá AI FDE): agent sai thì sửa vào **harness**
(`session_prompt/` + `CLAUDE.md` / `AGENTS.md` + `.claude/skills/` + hook; Claude Code có thêm memory), không chỉ sửa một lần; người duyệt cho **thử**, bằng chứng quyết **giữ / gỡ**.
Sổ: `session_prompt/SO_CAI_TIEN.md`.

## 1. Đầu vào — chỉ sự cố có bằng chứng

Lời User sửa / nhắc trong phiên, lỗi do kiểm chéo (agent con đọc diff) bắt được, lệnh phải chạy lại, commit sửa commit trước.
Mỗi sự cố ghi: ngày · chuyện gì · **mất gì** (giờ / USD / dữ liệu / User phải nhắc) · bằng chứng (file:dòng, commit) ·
**lần thứ mấy**. Ý hay từ khoá học mà chưa có sự cố ⇒ "ý chờ", chưa thành luật.

## 2. Đề xuất — tối đa 3 mỗi vòng, nấc rẻ trước

1. **Gỡ / gộp / dời:** luật trùng, hết hiệu lực, nằm sai chỗ (bài học chỉ ở handoff hay memory ⇒ về skill / `CACH_LAM_VIEC.md`).
2. **Sửa câu** của luật có sẵn mà vẫn bị làm sai.
3. **Thêm luật** vào đúng một chỗ, 1–3 dòng, kèm "vì sao" (sự cố).
4. **Rào bằng máy** (hook / quyền Claude Code) khi luật chữ bị vi phạm **≥ 2 lần**. Agent soạn; **User duyệt và tự áp**
   (Claude Code: skill `update-config`; agent khác: User tự sửa file cấu hình của agent đó).

Mỗi đề xuất theo `propose-options` mục 2: sự cố + lần thứ mấy; sửa ở đâu (nguyên văn dòng thêm / gỡ); cái giá (thêm chữ phải
đọc, chặn nhầm gì); cách biết có ích; khi nào gỡ.

## 3. Duyệt → thử → giữ / gỡ

- Sổ một bảng: `Ngày | Sự cố | Lần | Mất gì | Bằng chứng | Thay đổi (ở đâu) | Trạng thái | Xem lại`.
- Trạng thái: `đề xuất` → `đang thử` (User duyệt) → `đang dùng` (sự cố không lặp, luật được dùng) / `gỡ` (2 phiên thật
  không ai cần hoặc gây vướng) / `bác`.
- **Mỗi tuần xét lại một lần** các mục `đang thử` (repo gốc không xét lại nên mọi mục mãi "đang thử").
- Bằng chứng là quan sát (sự cố có lặp không) — nói thẳng mức này, không gọi là "đã chứng minh".

## 4. Giữ harness gọn

- File đọc mỗi phiên (`session_prompt/START_SESSION.md`, `CACH_LAM_VIEC.md`, `CURRENT_HANDOFF.md`, `CLAUDE.md`): đếm dòng
  (`wc -l`); `CURRENT_HANDOFF.md` quá 60 dòng ⇒ dời phần cũ ra `session_prompt/archive/`.
- Memory sai / đã bị thay ⇒ sửa hoặc xoá. Một luật ghi hai chỗ ⇒ giữ một, chỗ kia trỏ tới.

## 5. Kết vòng

3–5 dòng lời thường cho User: sự cố nào, đã đổi gì, đã gỡ gì, phiên sau theo dõi gì. Commit khi User cho phép.
