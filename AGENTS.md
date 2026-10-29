# AGENTS.md

Hướng dẫn cho mọi coding agent (Codex, Antigravity, Cursor…) trong repo này. Nội dung không lặp lại ở đây để mỗi luật chỉ
nằm một chỗ:

1. **Mở phiên:** làm theo khối prompt trong [`session_prompt/START_SESSION.md`](session_prompt/START_SESSION.md).
2. **Luật chung** (quyền, an toàn, bằng chứng, môi trường, bẫy kỹ thuật, skill, ghi chép):
   [`session_prompt/CACH_LAM_VIEC.md`](session_prompt/CACH_LAM_VIEC.md).
3. **Trạng thái phiên gần nhất:** [`session_prompt/CURRENT_HANDOFF.md`](session_prompt/CURRENT_HANDOFF.md).
4. **Mô tả hệ thống và code:** [`CLAUDE.md`](CLAUDE.md) (dùng chung cho mọi agent).
5. **Skill** (các bước làm chi tiết): `.claude/skills/<tên>/SKILL.md` — mở đúng file khi việc khớp bảng mục 8 của
   `CACH_LAM_VIEC.md`.

Tối thiểu phải nhớ: trả lời tiếng Việt; chỉ làm việc mới khi User nói "làm đi" (hoặc chọn một phương án agent đưa ra); commit / push / deploy / chi tiền ngoài việc
đã duyệt / chạy app thật (gửi Pushover thật) ⇒ hỏi trước; không đọc `.env`; Python chỉ qua `uv run`.
