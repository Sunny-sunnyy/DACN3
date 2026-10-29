# CURRENT_HANDOFF — phiên gần nhất (≤ 60 dòng; khối cũ ⇒ `archive/`)

**Cập nhật lần cuối: 13:46, ngày 29/10/2026** — phiên Claude Code (Opus), cả ngày 29/10.

## Hệ thống lúc kết phiên
- Nhánh **`toi-uu-search-key`** (chưa gộp vào `claudedev`, chưa push). Tag quay lại: **`moc-truoc-toi-uu-2026-10-29`**
  (= `claudedev` trước đợt tối ưu). Quay về bản cũ: `git checkout claudedev` (working tree phải sạch: commit / stash trước).
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
- **Từ khoá nên thử** (dữ liệu huấn luyện: 8 nhóm Amazon 2023, giá ≤ $999; kiểm bằng `scripts/do_luong/probe_keywords.py`):
  `noise cancelling headphones`, `soundbar`, `gaming monitor`, `action camera`, `digital piano`, `cordless drill`.
  Tránh `laptop` / `smart tv` (> $999), đồ bếp (`air fryer`… không có trong dữ liệu), hàng < $50.

## Việc đang chờ (thứ tự đề xuất)
1. **User chạy app sau khi đổi Frontier sang luna low** (`cd segment4 && uv run search_key.py`, 1 từ khoá) — pipeline đầy
   đủ chưa chạy lại sau thay đổi này.
2. **Gộp `toi-uu-search-key` vào `claudedev`** khi User thấy ổn; push khi User cho phép (repo công khai).
3. Chạy thử `price_is_right.py` một lần (dùng chung Ensemble / Frontier / Specialist đã đổi; gửi Pushover thật nếu có deal).
4. Tuỳ User: cào thử 6 từ khoá nên thử (không gọi LLM) xem BestBuy / Amazon có bao nhiêu deal sale; mở song song trang chi tiết Amazon (P4, ~13–19 s còn lại ở Bước 1); nhận dạng trang Amazon 200 rỗng
   (log "Page without results"); thước đo chất lượng trên hàng cào thật; mốc không dùng LLM cho Bước 3; thử bỏ Llama.

## Câu hỏi đang chờ User (hỏi mỗi lần một câu)
- App chạy ổn với Frontier luna low chưa ⇒ có gộp nhánh không?
- Có gắn thẻ Modal để dùng app `pricer-service-v2` (giữ ấm phía server, tối đa 1 máy) không?

## Quyền phiên 29/10 (đã hết hạn)
Gọi API trả phí cho đo / thử (đã dùng < $1), commit trên nhánh `toi-uu-search-key`. Phiên sau hỏi lại.

## Bẫy cần nhớ
CRLF ở `segment4/price_agents/` · đo bằng `perf_counter` · Amazon request thưa · chạy app thật = Pushover thật ·
`load_dotenv(find_dotenv(usecwd=True))` cho script ngoài repo — đủ ở `CACH_LAM_VIEC.md` mục 7.
