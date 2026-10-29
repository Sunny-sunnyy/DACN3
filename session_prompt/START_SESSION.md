# Prompt mở phiên — dùng cho mọi coding agent

**Cập nhật lần cuối: 13:15, ngày 29/10/2026.**
Copy nguyên khối dưới, gửi cho agent (Claude Code, Codex, Antigravity, Cursor…) ở đầu mỗi phiên. Nếu có việc cụ thể, viết
thêm **sau** khối — agent vẫn chỉ làm khi bạn nói "làm đi".

```text
Bạn là coding agent trong repo /home/minhhieu/price2026wsl/tech2ai (dự án cá nhân "The Price Is Right", đồ án DACN3).

1. Đọc toàn bộ, theo thứ tự:
   session_prompt/CACH_LAM_VIEC.md      — luật chung: quyền, an toàn, bằng chứng, môi trường, bẫy, khi nào dùng skill
   session_prompt/CURRENT_HANDOFF.md    — phiên gần nhất: hệ thống lúc kết, việc dở, câu hỏi đang chờ, quyền
   CLAUDE.md                            — mô tả hệ thống và code (dùng chung cho mọi agent, không riêng Claude)
   Sau đó đọc những gì CURRENT_HANDOFF chỉ định cho việc tiếp theo (tài liệu trong segment4/mo_ta_du_an/,
   docs/changelog/README.md, session_prompt/archive/… — chỉ phần cần).
   Nếu việc có sửa code: đọc .claude/skills/practical-project-coding/SKILL.md. Nếu việc là thử / so phương án / đổi mô hình:
   đọc .claude/skills/run-experiment/SKILL.md. Khi cần tôi chọn hướng: .claude/skills/propose-options/SKILL.md.
   (Claude Code tự thấy các skill trong .claude/skills/; agent khác mở đúng file SKILL.md khi việc khớp bảng mục 8 của
   CACH_LAM_VIEC.md.)

2. Kiểm nhanh, CHỈ ĐỌC:
   cd /home/minhhieu/price2026wsl/tech2ai
   git branch --show-current; git log --oneline -5; git status --short; git tag --list 'moc-*'
   ss -ltnp 2>/dev/null | grep 7860 || echo "cổng 7860 trống"     (app Gradio của User có đang mở không)
   free -h | head -2; nvidia-smi --query-gpu=memory.used,memory.total --format=csv 2>/dev/null
   ls segment4/products_vectorstore segment4/deep_neural_network.pth
   (Không đọc .env. Không chạy app, không gọi API trả phí, không bật Modal ở bước này.)

3. Báo tôi 5–10 dòng tiếng Việt: bạn là agent gì; nhánh / commit hiện tại; việc dở và câu hỏi đang chờ theo CURRENT_HANDOFF;
   chỗ lệch giữa tài liệu và thực tế (ví dụ nhánh khác, file thiếu, tiến trình còn chạy); tên các skill bạn thấy và sẽ dùng;
   thắc mắc (nếu có).
   Rồi CHỜ. Chỉ khi tôi nói "làm đi" (hoặc chọn một phương án bạn đưa ra) mới bắt đầu. Trước đó không sửa file, không chạy việc nặng, không gọi API trả phí.
```

Ghi chú cho User:
- Mỗi phiên chỉ cần gửi khối trên. Việc cụ thể của phiên nằm ở `CURRENT_HANDOFF.md` (agent kết phiên trước đã ghi) hoặc
  bạn viết thêm sau khối.
- Muốn agent hỏi lại để tự kiểm mình hiểu chưa: gõ **"hỏi tôi"** (skill `teach-and-quiz`).
- Codex đọc `AGENTS.md`, Claude Code đọc `CLAUDE.md` tự động — cả hai file đều trỏ về đây, nên quên gửi khối này thì agent
  vẫn được nhắc đọc `CACH_LAM_VIEC.md`.
