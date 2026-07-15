# Prompt Khởi Động Session Cho Agent

Trước khi làm bất kỳ thay đổi nào, hãy đọc kỹ toàn bộ ngữ cảnh sau để nắm đúng trạng thái hiện tại của repo.

## 0. Bối Cảnh DATN & Dữ Liệu Tiếng Việt (đọc trước)

Repository này là đồ án tốt nghiệp (DATN) — bên cạnh runtime tiếng Anh trong `segment4/`,
còn có toàn bộ pipeline phát triển dữ liệu và mô hình tiếng Việt.

**Đọc file tổng hợp trước tiên:**

- `VIETNAMESE_PRICING_DEVELOPMENT_REPORT.md`: Báo cáo tổng hợp toàn bộ quá trình phát triển
  dữ liệu tiếng Việt — từ scraping, tiền xử lý, augmentation, đến huấn luyện ML/DL/LLM.
  File này chứa leaderboard, checklist việc chưa hoàn thành, và link đến tất cả file .md chi tiết.

**Trạng thái tóm tắt (cập nhật 2026-07-12):**

- Dữ liệu: 158K SP thô → 110K sau làm sạch → 269K sau augmentation (tất cả trên HF Hub `SeanSunny/items_*`)
- **SOTA hiện tại:** AITeamVN BERT fine-tune (NB06) — MAE = 74,200 VND
- Qwen V2 (`fine_tune_qwen_v2/`): CODE HOÀN TẤT, CHƯA TRAIN (cần RTX 5090, ~7-10h)
- Day4 v2: NB09, NB12, NB13, NB14 — SẴN SÀNG, CHƯA CHẠY (NB14 kỳ vọng MAE < 65k)
- Day5 ensemble (`07_ensemble.ipynb`): CHƯA CHẠY

**Các thư mục liên quan đến dữ liệu tiếng Việt:**

- `scraping_data_tv/` — Pipeline scraping và xử lý dữ liệu
- `scraping_data_tv/Data_processing_for_Vietnamese_data/` — Code xử lý, models ML/DL
- `fine_tune_qwen/` — QLoRA Qwen3.5-4B V1 (RMSLE)
- `fine_tune_qwen_v2/` — QLoRA Qwen3.5-4B V2 (MAE, code done chưa train)

---

## 1. Tài Liệu Bắt Buộc Đọc

Bắt buộc đọc đầy đủ các file sau:

- `VIETNAMESE_PRICING_DEVELOPMENT_REPORT.md`: báo cáo tổng hợp toàn bộ quá trình dữ liệu & mô hình tiếng Việt.
- `segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md`: dự án cũ, autonomous deal hunter.
- `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`: dự án chính hiện tại.
- `segment4/mo_ta_du_an/Project_Development_Plan.md`: kế hoạch phát triển dự án, phiên bản 1.
- `README.md`: tổng quan repo, trạng thái hiện tại, cách chạy và roadmap ngắn.

Chỉ đọc các link/tài liệu liên quan thêm khi thật sự cần nếu thấy thiếu bối cảnh hoặc hiểu implementation hiện tại.

Đừng bắt đầu bất kỳ công việc nào khác ngoài việc đọc tài liệu và kiểm tra cấu trúc thư mục. Khi đã đọc xong tất cả, hãy cho tôi biết nếu có thắc mắc trước khi chúng ta bắt đầu.

## 2. Kiểm Tra Trạng Thái Repo

Chạy:

```bash
git status --short
```

Mục tiêu:

- Nhận biết các thay đổi có sẵn trong worktree.
- Tuyệt đối không sửa, reset, stage hoặc commit các thay đổi đó nếu chưa được yêu cầu rõ ràng.
- Nếu thấy thay đổi không do bạn tạo, giữ nguyên và báo lại ngắn gọn trong phần báo cáo context.

## 3. Dùng CodeGraph Để Nắm Code Structure

CodeGraph đã được cài và MCP Codex đã được cấu hình.

Trước tiên kiểm tra index:

```bash
codegraph status segment4
```

Nếu đang đứng trong `segment4/`, có thể chạy:

```bash
codegraph status
```

### Khi Index Hợp Lệ Và Up-To-Date

Ưu tiên dùng `codegraph_explore` cho các câu hỏi về:

- Architecture code.
- Symbol/function/class.
- Request flow.
- Dependency.
- Callers/callees.
- Impact/blast radius.
- Test bị ảnh hưởng.

Không đọc tuần tự toàn bộ source code chỉ để "hiểu repo". Hãy dùng CodeGraph để lấy đúng phần code liên quan trước.

Ví dụ MCP:

```text
codegraph_explore:
query = "How does search_key.py run the multi source search pipeline?"
projectPath = "/home/hieu0606sunny/price2026wsl/tech2ai/segment4"
```

Ví dụ CLI fallback:

```bash
cd segment4
codegraph explore "How does search_key.py run the multi source search pipeline?"
```

### Nếu MCP Tool Chưa Xuất Hiện Trong Session

Dùng CLI fallback:

```bash
cd segment4
codegraph explore "<câu hỏi>"
```

Báo rõ rằng cần mở session Codex mới để MCP được nạp nếu muốn dùng MCP tool trực tiếp.

### Nếu `.codegraph/` Bị Thiếu Hoặc Index Lỗi

Không tự ý rebuild khi chưa báo cho tôi.

Đề xuất chính xác lệnh cần chạy:

```bash
cd segment4
codegraph init
```

Chờ tôi xác nhận trước khi chạy lại init nếu việc đó có thể thay đổi local artifact.

### Sau Khi Chỉnh Code Ở Các Lượt Sau

- Ưu tiên dùng CodeGraph để xem impact trước khi đọc file thủ công hoặc chạy test.
- Dùng `codegraph affected` khi cần xác định test bị ảnh hưởng.
- Nhớ rằng CodeGraph là nguồn cho quan hệ tĩnh của code; nó không thay thế việc đọc guide, README, tài liệu thiết kế, cấu hình và kết quả test/runtime.

## 4. Cấu Trúc Cần Kiểm Tra

Kiểm tra nhanh cấu trúc thư mục ở mức cần thiết, đặc biệt:

- `segment4/`: runtime chính hiện tại.
- `segment4/price_agents/`: agent layer.
- `segment4/bestbuy_untils/`: utilities cho multi-source pipeline.
- `segment4/mo_ta_du_an/`: tài liệu dự án.
- `fine_tune_qwen/` và `fine_tune_qwen_v2/`: notebook/thử nghiệm fine-tune Qwen.
- `scraping_data_tv/`: scraping và xử lý dữ liệu tiếng Việt.

Không cần đọc toàn bộ notebook/dataset nếu chưa có yêu cầu cụ thể.

## 5. Báo Cáo Sau Khi Nạp Context

Sau khi hoàn tất đọc context và kiểm tra repo, chỉ trả lời ngắn gọn theo format:

```text
Đã nạp context.

CodeGraph:
- Version: <version nếu kiểm tra được>
- Index: <up-to-date / lỗi / chưa init>
- Cách dùng trong session: <MCP / CLI fallback>

Tech stack và entry points chính:
- <tóm tắt ngắn>

Luồng chính hoạt động:
- <tóm tắt ngắn>

Mâu thuẫn hoặc rủi ro quan trọng giữa .md và implementation hiện tại:
- <nếu có>

Thay đổi có sẵn trong worktree cần giữ nguyên:
- <nếu có>

Câu hỏi cần làm rõ trước khi bắt đầu:
- <chỉ hỏi câu thực sự ảnh hưởng scope/design/test/implementation>
```

Sau đó dừng lại và chờ lệnh tiếp theo của tôi.
