# CURRENT_HANDOFF — phiên gần nhất (≤ 60 dòng; khối cũ ⇒ `archive/`)

**Cập nhật lần cuối: 14:28, ngày 29/10/2026** — phiên Claude Code (Opus), cả ngày 29/10.

## Hệ thống lúc kết phiên
- Nhánh **`claudedev`** — đã gộp (fast-forward) `toi-uu-search-key` lúc kết phiên 29/10 sau khi User chạy app ổn; **chưa push**
  (`origin/claudedev` còn ở `54c18bf`). Tag mốc trước đợt tối ưu: **`moc-truoc-toi-uu-2026-10-29`** (`2860714`) — xem bản
  cũ: `git switch --detach moc-truoc-toi-uu-2026-10-29` (working tree phải sạch). Nhánh `toi-uu-search-key` còn giữ.
  Untracked cố ý không commit: `segment4/.codegraph/`, `shopping_assistant_v3/`, `segment4/pricer_service_v2.py`.
- Mô hình: luna cho mọi lời gọi OpenAI của search_key (Frontier `low`; chọn deal, tin nhắn `none`). Tiền xử lý mô tả vẫn
  Groq `gpt-oss-20b`. `autonomous_planning_agent.py` còn GPT-5.1 nhưng không chạy (price_is_right dùng `PlanningAgent`).
- Modal: app cũ `pricer-service`; giữ ấm từ phía search_key. Deploy app GPU mới bị chặn tới khi User gắn thẻ.
- Không còn tiến trình nền của phiên. App Gradio User tự chạy (có thể còn mở — hỏi trước khi chạy cổng 7860).

## Đã làm 29/10 (chi tiết: `docs/changelog/README.md`, số đo: `archive/SESSION_HANDOFF_OPTIMIZE.md` mục 3.4)
- search_key: 69,5–106,7 s ⇒ **21–34 s** (2 từ khoá), User chạy app thật 27,1 s. Amazon cookie 22 s ⇒ 5 s; Bước 4 33–40 s ⇒ ~4 s.
- Chống sập (trạng thái từng nguồn, bỏ mô hình lỗi, kiểm link trước khi gửi); Bước 3 code giữ giá / URL.
- Frontier GPT-5.1 ⇒ luna low (MAE $31,16 ⇒ $29,69 / 200 mẫu, không kém; rẻ hơn GPT-5.1 ~10 lần, rẻ hơn terra ~7 lần).
- Cách làm việc: `CACH_LAM_VIEC.md`, `START_SESSION.md`, `AGENTS.md`, 6 skill trong `.claude/skills/`, `docs/changelog/`,
  `SO_CAI_TIEN.md`, `hoc/NHAT_KY_TU_GIAI_THICH.md`, script đo `scripts/do_luong/`.
- Tài liệu viết lại theo code hiện tại, tiếng Việt có dấu, bỏ icon: `README.md`, `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`;
  `DOCUMENTATION_PRICE_IS_RIGHT.md` sửa mô hình / mặc định PlanningAgent / bỏ icon.
- **Báo cáo hệ thống bản 3:** `scraping_data_tv/Data_processing_for_English_data/report_system3.md` → `report_system3.html`
  (giao diện nền sáng, sinh bằng `uv run python gen_report_html.py report_system3.md report_system3.html` trong thư mục đó;
  sửa .md rồi sinh lại, không sửa tay .html). Bản 1–2 (nền tối, `gen_report_system.py`) giữ nguyên.
- **Từ khoá nên thử** (dữ liệu huấn luyện: 8 nhóm Amazon 2023, giá ≤ $999; kiểm bằng `scripts/do_luong/probe_keywords.py`):
  `noise cancelling headphones`, `soundbar`, `gaming monitor`, `action camera`, `digital piano`, `cordless drill`.
  Tránh `laptop` / `smart tv` (> $999), đồ bếp (`air fryer`… không có trong dữ liệu), hàng < $50.

## Việc đang chờ (thứ tự đề xuất)
1. ~~User chạy app với Frontier luna low~~ — User báo chạy ổn (29/10). ~~Gộp vào `claudedev`~~ — đã gộp.
2. **Push `claudedev`** khi User cho phép (repo công khai). Lưu ý: commit `2860714` có chú thích `.gitignore` nhắc tên công
   ty (bản sau đã sửa trung tính) — muốn xoá khỏi lịch sử thì phải viết lại commit **trước** khi push; hỏi User.
3. Chạy thử `price_is_right.py` một lần (dùng chung Ensemble / Frontier / Specialist đã đổi; gửi Pushover thật nếu có deal).
4. Tuỳ User: cào thử 6 từ khoá nên thử (không gọi LLM) xem BestBuy / Amazon có bao nhiêu deal sale; mở song song trang chi tiết Amazon (P4, ~13–19 s còn lại ở Bước 1); nhận dạng trang Amazon 200 rỗng
   (log "Page without results"); thước đo chất lượng trên hàng cào thật; mốc không dùng LLM cho Bước 3; thử bỏ Llama.

## Câu hỏi đang chờ User (hỏi mỗi lần một câu)
- Có push `claudedev` lên GitHub không (và có viết lại commit `2860714` trước khi push không)?
- Có gắn thẻ Modal để dùng app `pricer-service-v2` (giữ ấm phía server, tối đa 1 máy) không?

## Quyền phiên 29/10 (đã hết hạn)
Gọi API trả phí cho đo / thử (đã dùng < $1), commit trên nhánh `toi-uu-search-key`. Phiên sau hỏi lại.

## Bẫy cần nhớ
CRLF ở `segment4/price_agents/` · đo bằng `perf_counter` · Amazon request thưa · chạy app thật = Pushover thật ·
`load_dotenv(find_dotenv(usecwd=True))` cho script ngoài repo — đủ ở `CACH_LAM_VIEC.md` mục 7.
