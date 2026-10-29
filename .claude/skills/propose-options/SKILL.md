---
name: propose-options
description: Dùng mỗi khi cần User chọn hướng hoặc duyệt — đưa phương án A/B/C, đề xuất cách làm, đổi kiến trúc / mô hình / quy trình, việc có chi phí tiền (API, GPU Modal), hoặc khi vấn đề còn mở cần bàn nhiều bước (brainstorm) — hỏi mỗi lần một câu có đáp án để tick. Mỗi phương án bằng lời thường kèm hệ quả, khi nào sai, chọn khác mất gì, lý do khuyến nghị và một câu tự kiểm để User biết mình đã hiểu chưa.
---

# Đề xuất để User chọn — tech2ai

Chuyển thể 29/10/2026 từ skill cùng tên ở một repo khác của User.

## Vì sao

User tự nhận hay chọn phương án "khuyến nghị" dù chưa hiểu. Chọn theo nhãn thì quyết định là của agent và User không học
được gì — trong khi User phải tự giải thích được dự án (bảo vệ đồ án, phỏng vấn, người khác hỏi "vì sao chọn cách này").

## 1. Có cần hỏi không

Chỉ hỏi khi câu trả lời đổi phạm vi, cách làm, cách kiểm, quyền hoặc tiền. Có mặc định thông thường ⇒ làm theo và nói ra.
Không hỏi lại điều đã chốt (`session_prompt/CURRENT_HANDOFF.md`, `docs/changelog/`; Claude Code có thêm memory). Bị chặn bởi việc của User (gắn thẻ Modal, cấp quyền) ⇒ nói rõ chặn ở đâu,
đưa phương án thay thế.

## 2. Mỗi phương án

| Phần | Viết gì |
|---|---|
| **Là gì** | 1–2 câu lời thường; thuật ngữ kèm nghĩa |
| **Đổi gì** | với User (phải làm / hiểu gì) và với hệ thống (chạy khác thế nào) |
| **Tốn gì** | thời gian, tiền API / GPU (có số: ví dụ T4 $0,000164 / s ≈ $0,59 / giờ), độ phức tạp, bảo trì |
| **Khi nào sai** | điều kiện làm phương án hỏng hoặc không đáng |
| **Chọn khác mất gì** | so trên cùng tiêu chí |

Thêm phương án "giữ như cũ" khi đó là lựa chọn thật.

## 3. Khuyến nghị

- Nói **lý do**, và **thông tin nào nếu có sẽ đảo khuyến nghị**. Không dùng nhãn "(Recommended)" thay cho lý do.
- Tách rõ **đã đo / có trong code** ↔ **ước lượng** ↔ **giả thuyết**.
- Phản biện cả phương án mình khuyến nghị.
- Kết bằng **một câu tự kiểm**: "nếu hiểu đúng thì trả lời được: …".
- Sau khi User chọn: nhắc lại 2–3 dòng **nghĩa là gì, cái giá là gì**. Câu trả lời của User sửa / bổ sung đề bài (ví dụ
  "đây là dự án cá nhân", "chỉ tối ưu, giữ ổn định") ⇒ ghi lại (`CURRENT_HANDOFF.md`; Claude Code ghi thêm memory) và đi theo.
- User nói không hiểu câu hỏi ⇒ giải thích lại bằng ví dụ đúng bài toán trước khi hỏi tiếp.

## 4. Bàn mở (brainstorm)

- Đọc đủ ngữ cảnh trước (handoff, CLAUDE.md, code); không hỏi điều file đã trả lời.
- Chia thành chuỗi quyết định theo thứ tự phụ thuộc (mục tiêu → phạm vi → cách làm → thứ tự); **mỗi lần một câu** bằng
  câu hỏi có đáp án để tick (2–4 đáp án, phần giải thích theo mục 2), luôn có đường ghi ý khác.
- Bàn xong: tóm tắt kế hoạch (bước → kiểm bằng gì → mốc quay lại), **không tự làm khi User chưa nói "làm đi"**.

## 5. Cách nói

Tiếng Việt, rõ, đơn giản, **đủ quan trọng hơn ngắn**; không mã nội bộ khi chưa giải nghĩa; số luôn kèm điều kiện (đo trên
gì, mấy lượt).
