---
name: teach-and-quiz
description: Dùng khi User gõ "hỏi tôi", "giải thích…", "X là gì", "vì sao chọn…", "khi nào nó hỏng", "chuẩn bị bảo vệ / bị hỏi về…". Giải thích khái niệm hoặc giảng lại việc agent đã làm theo lớp (bài toán → cơ chế → vì sao chọn → khi nào hỏng → code ở đâu), rồi hỏi lại User 2–4 câu, chờ User tự trả lời, sửa chỗ sai, và ghi sổ khi User trả lời đúng. Dùng ngay trong phiên đang làm, không cần phiên riêng. Khi đang giảng: chỉ đọc, không sửa code, không gọi API trả phí.
---

# Giảng và hỏi lại — tech2ai

Chuyển thể 29/10/2026 từ skill cùng tên ở một repo khác của User. Lý do: việc agent làm chỉ thành năng lực của User khi User
**tự giải thích lại được** (bảo vệ đồ án DACN3, phỏng vấn, người khác hỏi "vì sao").

## Khi giảng

- User gõ "hỏi tôi" / "giải thích…" = được giảng ngay, không cần chờ "làm đi" (vì chỉ đọc).

- **Chỉ đọc** (lệnh đọc nhỏ như `grep`, `git show`, `sed -n` để chỉ đúng chỗ code là được). Không sửa code, không chạy
  pipeline, không gọi API trả phí.
- Không giảng số liệu từ trí nhớ: mở `docs/changelog/`, `CLAUDE.md`, `session_prompt/archive/` hoặc code để lấy. Tài liệu
  mâu thuẫn code ⇒ code là sự thật, nói rõ chỗ lệch.
- Gắn nhãn: **[đã đo]**, **[có trong code]**, **[kiến thức chung]**, **[giả thuyết]**.

## Ba chế độ (câu hỏi rõ thì làm luôn, chưa rõ thì hỏi User muốn chế độ nào)

**A. Giải thích khái niệm** (RAG, embedding, ensemble, MAE, reasoning effort, cold start, structured output, WAF…):
một câu lời thường → ví dụ ngay trong dự án (số thật nếu có) → hay nhầm với gì → khi nào dùng / không dùng → *(nếu User
muốn)* cơ chế bên trong.

**B. Giảng lại việc đã làm:** bài toán (lớp vấn đề) → cơ chế (dữ liệu đi qua đâu) → vì sao chọn cách này, **phương án nào đã
thử và bị bỏ, vì sao** → khi nào nó hỏng → code ở đâu (`file:dòng`).

**C. "Hỏi tôi" — luyện tự giải thích:**
1. Hỏi **2–4 câu, mỗi lần một câu**. Ưu tiên "vì sao không chọn cách khác?", "khi nào nó hỏng?", "số đo nói gì, chưa nói
   gì?" — không hỏi "nó làm gì" (dễ trả lời bằng cách đọc lại).
2. **Chờ User trả lời. Không trả lời hộ, không gợi ý trước.**
3. Phản hồi: đúng ở đâu (ngắn) · **sai** ở đâu (sửa + lý do) · **thiếu** gì (bổ sung). Không khen chung chung.
4. Sai ⇒ giảng lại phần đó (chế độ A / B) rồi hỏi một câu tương tự.

Ví dụ câu hỏi (đợt 29/10): "Vì sao để luna trả số thứ tự deal thay vì trả giá và URL?" · "Vì sao chọn luna low cho Frontier
dù terra có MAE thấp hơn?" · "Khi Modal nguội, ensemble còn lại mô hình nào và trọng số đổi thế nào?" · "Vì sao 1 lượt đo
không đủ để nói luna tốt hơn GPT-5.1?"

## Ghi sổ — chỉ khi User tự trả lời đúng

Thêm vào cuối `session_prompt/hoc/NHAT_KY_TU_GIAI_THICH.md` (giờ lấy bằng `date`):

```
## <ngày giờ> — <chủ đề>
- Câu hỏi: …
- User trả lời: đúng / thiếu … / sai … ⇒ đã giảng lại …
- Còn chưa vững: …
```

Kết thúc mỗi lần giảng bằng **một câu tự kiểm**: "nếu hiểu rồi thì trả lời được: …".
