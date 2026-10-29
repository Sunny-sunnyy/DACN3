# Cách làm việc trong repo tech2ai — luật chung cho mọi coding agent

**Cập nhật lần cuối: 13:15, ngày 29/10/2026.**
Áp dụng cho **mọi agent** (Claude Code, Codex, Antigravity, Cursor…) và mọi phiên. Mở phiên bằng
[START_SESSION.md](START_SESSION.md). Trạng thái phiên gần nhất: [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md).
Mô tả hệ thống / code: [CLAUDE.md](../CLAUDE.md) (tên file của Claude, nhưng nội dung dùng chung cho mọi agent) và
`segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`, `DOCUMENTATION_PRICE_IS_RIGHT.md`.

> Nguồn gốc: chuyển thể từ cách làm việc ở một repo khác của User và khoá AI FDE (ghi chú riêng của User ở
> `session_prompt/ghi_chu_khoa_hoc/`, không commit). File này là **luật**; các bước làm chi tiết nằm trong skill (mục 8).

---

## 1. Dự án và người dùng

- **tech2ai = "The Price Is Right" (đồ án DACN3), dự án cá nhân của User** (Phạm Minh Hiếu). Không liên quan công việc ở
  công ty. Nhánh làm việc thường: `claudedev`; việc lớn làm trên nhánh riêng rồi gộp khi User đồng ý.
- Code đang chạy: `segment4/` — app `search_key.py` (tìm theo từ khoá) và `price_is_right.py` (tự quét RSS 5 phút / lần).
  Thư mục khác (`w8/`, `scraping_data_tv/`, `segment4/khong_su_dung/`…) là notebook / thử nghiệm cũ, chỉ đọc khi cần.
- **User muốn hiểu được việc agent làm.** User tự nhận hay chọn phương án "khuyến nghị" dù chưa hiểu ⇒ mọi lựa chọn phải
  có lời thường + hệ quả + khi nào sai + chọn khác mất gì (skill `propose-options`). Việc agent làm chỉ có giá trị đầy đủ khi
  User tự giải thích lại được (mục 8, "hỏi tôi").

## 2. Giao tiếp

- **Tiếng Việt**, lời thường, rõ; **đủ quan trọng hơn ngắn**; thuật ngữ lần đầu kèm nghĩa; không dùng mã nội bộ chưa giải nghĩa.
- Tên hàm / biến / lệnh bằng tiếng Anh; ghi chú trong code bằng tiếng Việt, ghi *vì sao*.
- Phản biện bằng lập luận và số đo, không chỉ đồng ý. Phân biệt rõ: **đã đo** ↔ **có trong code** ↔ **suy luận** ↔ **đề xuất**.
- Hỏi khi câu trả lời đổi phạm vi / cách làm / quyền / tiền; bàn mở thì **hỏi mỗi lần một câu**, có đáp án để chọn.
- **Chỉ bắt đầu việc mới khi User nói "làm đi"** — hoặc User chọn một phương án trong câu hỏi agent đưa ra, hoặc User ra
  lệnh cụ thể ("đổi X thành Y"). "Làm đi" cho một việc = được gọi API trả phí **cần cho việc đó** trong trần tiền (mục 3);
  không cấp quyền commit / push / deploy. User gõ "hỏi tôi" / "giải thích…" = được giảng ngay (chỉ đọc).
- Giờ ghi vào tài liệu **lấy từ lệnh `date`**, không ước. Không ghi giờ cho việc chưa xảy ra.

## 3. Quyền mặc định

| Được tự làm | Phải hỏi User trước |
|---|---|
| Đọc file, code, log; `git status / diff / log / show` | `git commit`, `git push`, gộp nhánh (merge), xoá nhánh / tag |
| Chạy script offline không ghi dữ liệu dùng chung | Gọi API trả phí **ngoài việc đã được duyệt** hoặc vượt trần tiền của phiên |
| Gọi API trả phí (OpenAI, Groq, Modal) **trong việc User đã duyệt**, trong trần tiền (mặc định ≤ 1 USD / phiên) | Deploy / đổi app Modal (`modal deploy`), đổi cấu hình giữ ấm, gắn thẻ / chi phí GPU |
| Sửa file trong phạm vi việc được giao | Chạy app thật có thể **gửi Pushover thật** tới điện thoại User |
| Tạo script thử ở `/tmp/…` | Cài / nâng thư viện (`uv add`, `uv sync` không `--dry-run`), đổi `pyproject.toml`, `uv.lock` |
| | Đổi `.env`, xoá dữ liệu (`segment4/products_vectorstore/`, `memory.json`, volume Modal `hf-hub-cache`, file model `.pth`) |
| | Đổi luật chung: file này, START_SESSION, skill, hook |

Quyền riêng của một phiên (ví dụ "được commit trên nhánh X", "trần 0,5 USD" — khác với quyền tiêu tiền trong việc đã duyệt ở mục 2) ghi ở `CURRENT_HANDOFF.md` mục "Quyền phiên
này" và **hết hạn cuối phiên**. Quyền đã cấp thì không xin lại từng lệnh.

## 4. An toàn

- **Không đọc / in / commit `.env`** (ở `tech2ai/.env`), khoá API, `~/.modal.toml`. Cần biết biến có hay không ⇒ in "CÓ / KHÔNG".
- **Repo đẩy lên GitHub công khai (`Sunny-sunnyy/DACN3`)** ⇒ không commit tài liệu công ty, tài liệu khoá học trả phí, dữ liệu
  cá nhân. Các folder ghi chú riêng trong `session_prompt/` (xem `.gitignore`) không được commit.
- Stage Git **theo từng đường dẫn**, không `git add -A` / `commit -a`; luôn `git diff --cached --stat` trước khi commit.
  Không `git add` 3 thư mục chưa theo dõi: `segment4/.codegraph/`, `shopping_assistant_v3/`, `segment4/pricer_service_v2.py`
  (bản Modal mới chưa deploy được).
- Không `git reset --hard`, `checkout -- .`, xoá file người khác đang dở. Trước khi xoá / dọn: đọc kỹ lệnh / script xoá gì.

## 5. Bằng chứng — bốn mức (đừng nhầm mức dưới với mức trên)

1. **Có trong code / tài liệu** — chưa chứng minh chạy.
2. **Đã chạy thật** — chưa chứng minh đúng.
3. **Đã đối chiếu** với kết quả mong đợi — ghi rõ đúng / sai / thiếu.
4. **Đã chứng minh cải tiến** — cùng đầu vào, cùng cách đo, trước–sau, có kiểm hồi quy.

- Chạy **thật** với dịch vụ thật; **không mock / fake / stub**. Lỗi nhà cung cấp / bị chặn là kết quả quan sát được, ghi lại,
  không che bằng giá trị giả.
- Ghi trạng thái `PASS / PARTIAL / FAIL / NOT RUN`; giữ cả kết quả không đạt.
- "HTTP 200" ≠ có dữ liệu (Amazon trả trang 200 rỗng khi chặn mềm); "pipeline chạy xong" ≠ giá ước đúng.

## 6. Đơn giản là mặc định

- Giải pháp nhỏ nhất đủ nhu cầu thật. Không thêm abstraction, retry, fallback, cache, cấu hình khi chưa có vấn đề quan sát được.
- **Code giữ con số:** giá, URL, ngưỡng, phép tính do code làm; LLM chỉ chọn (trả ID) hoặc viết lời.
- Mỗi thay đổi code **giải thích được bằng lời thường** (dòng "Giải thích ngắn" trong changelog — mục 9).
- Chi tiết: skill `practical-project-coding`.

## 7. Môi trường và bẫy kỹ thuật

- **Python chỉ qua `uv`:** `uv run …`, không `python` / `pip` trực tiếp. Kiểm môi trường: `uv sync --locked --dry-run`
  (bản không `--dry-run` từng gỡ gói cài tay như `xformers`).
- Chạy app: `cd segment4 && uv run search_key.py` (hoặc `price_is_right.py`), cổng 7860. App thật **gửi Pushover thật**.
- Máy WSL ~15 GB RAM, từng treo ⇒ **một việc nặng một lúc** (pipeline ~3,9 GB RAM; huấn luyện; nhiều lượt Modal), luôn có
  `timeout`; tiến trình dài chạy bằng chế độ chạy nền của công cụ, không `&` / `nohup` (mồ côi, không dừng được). Agent
  không có chế độ chạy nền ⇒ không tự bật server / app dài, đưa lệnh để User chạy.
- **Amazon:** request thưa, có `sleep` giữa các lượt; dồn dập ⇒ bị chặn IP / trang 200 rỗng. **BestBuy:** dùng API nội bộ,
  priceBlocks tối đa 25 SKU / request.
- **Modal** (Llama, app `pricer-service`): tự tắt sau 60 s rảnh ⇒ cold start 32–46 s. Deploy app GPU mới **bị chặn** cho tới
  khi User gắn phương thức thanh toán (29/10). search_key đánh thức + giữ ấm từ phía app.
- **gpt-6-luna:** không nhận `reasoning_effort="minimal"` (dùng `none` / `low` / …); gọi qua LiteLLM 1.79 cần
  `allowed_openai_params=["reasoning_effort"]`.
- **Kiểu xuống dòng:** nhiều file trong `segment4/price_agents/` là CRLF — sửa bằng script phải giữ `\r\n`, nếu không cả
  file thành diff.
- **Đo thời gian bằng `time.perf_counter()`** — đồng hồ WSL có lúc nhảy lùi.
- Script đo dùng lại: `scripts/do_luong/` (README trong đó). Script thử một lần: `/tmp/…` (mất khi khởi động lại máy).

## 8. Skill — dùng khi nào

Skill nằm ở `.claude/skills/<tên>/SKILL.md`. Claude Code tự thấy; **agent khác: mở và đọc đúng file SKILL.md khi việc khớp
cột "Khi"** rồi làm theo.

| Khi | Skill |
|---|---|
| Viết / sửa / debug / review code | `practical-project-coding` (+ `karpathy-guidelines` cho nguyên tắc chung) |
| Thử một thay đổi, so phương án, đổi mô hình / prompt / reasoning, đo trước–sau | `run-experiment` |
| Cần User chọn hướng, việc có chi phí, bàn mở (brainstorm) | `propose-options` |
| User gõ "hỏi tôi", "giải thích…", "vì sao chọn…" — giúp User tự nói lại việc đã làm | `teach-and-quiz` |
| Kết phiên; User phải nhắc cùng một lỗi lần 2; sự cố mất giờ / tiền / dữ liệu | `improve-workflow` (sổ `SO_CAI_TIEN.md`) |

**Kiểm chéo khi chỉ có một phiên:** việc vừa / lớn ⇒ trước khi commit, giao **một agent con ngữ cảnh mới** (hoặc một agent
khác) đọc diff, chỉ đưa code + mục tiêu, không đưa kết luận của mình; kiểm từng phát hiện trước khi sửa. (29/10: cách này bắt
được 3 lỗi thật mà các lượt đo đã bỏ sót.) Agent không có agent con ⇒ ghi "chưa kiểm độc lập" và đề nghị User mở một phiên
agent khác để đọc diff.

## 9. Ghi chép

| Ghi gì | Ở đâu | Khi nào |
|---|---|---|
| Mỗi thay đổi code (giải thích ngắn, trước / sau có số đo, còn tồn tại, commit, kiểm độc lập) | `docs/changelog/` — mỗi thay đổi một file + dòng mục lục | ngay khi sửa xong, trước commit |
| Mô tả hệ thống đang chạy | `CLAUDE.md`, `segment4/mo_ta_du_an/DOCUMENTATION_*.md` | khi hành vi / mô hình / cấu hình đổi |
| Trạng thái phiên, việc dở, câu hỏi cho User | `session_prompt/CURRENT_HANDOFF.md` (**≤ 60 dòng**) | kết phiên (ghi đè khối cũ; khối cũ dài ⇒ chuyển vào `archive/`) |
| Sự cố quy trình, luật mới đang thử | `session_prompt/SO_CAI_TIEN.md` | kết phiên (skill `improve-workflow`) |
| User tự giải thích đúng | `session_prompt/hoc/NHAT_KY_TU_GIAI_THICH.md` | sau "hỏi tôi" (skill `teach-and-quiz`) |
| Lịch sử dài (handoff cũ, báo cáo đo) | `session_prompt/archive/` | khi dời ra |

## 10. Kết phiên — checklist

1. Không để tiến trình nền chạy (app, server, lượt đo). Liệt kê lệnh User nên chạy nếu cần.
2. Mỗi thay đổi code đã có file changelog; tài liệu hệ thống khớp code.
3. Ghi đè `CURRENT_HANDOFF.md`: hệ thống lúc kết (nhánh, commit, tag mốc), việc dở + **lệnh đang chạy dở / đầu ra ở đâu**
   ("đừng chạy lại mù"), câu hỏi cho User (mỗi lần một câu), quyền phiên này đã hết.
4. Vòng `improve-workflow` nếu phiên có sự cố.
5. Báo User 3–5 dòng lời thường: đã làm gì, số trước ⇒ sau, còn gì, User cần làm gì. Commit khi User cho phép.
