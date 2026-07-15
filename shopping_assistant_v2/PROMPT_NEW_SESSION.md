# Prompt Khởi Động Session Cho Coding Agent: Shopping Assistant V2

Bạn là coding agent trong repo `tech2ai`. Nhiệm vụ của bạn là làm việc với dự án mới:

```text
shopping_assistant_v2/
```

Không bắt đầu code ngay. Trước khi làm bất kỳ thay đổi nào, hãy nạp đầy đủ context, báo cáo lại trạng thái, brainstorming với tôi, rồi chỉ implement khi tôi xác nhận rõ.

Ngôn ngữ giao tiếp: tiếng Việt. Technical terms giữ tiếng Anh khi rõ hơn.

---

## 0. Quy Trình Bắt Buộc

Luôn bắt đầu bằng:

1. Dùng `using-superpowers`.
2. Dùng `brainstorming` làm quy trình chính.
3. Không dùng implementation skill, không viết code, không tạo/sửa file runtime cho tới khi đã brainstorming và tôi xác nhận.

Nếu session/harness không có skill tool trực tiếp, hãy nói rõ và vẫn tuân thủ quy trình tương đương:

- nạp context,
- hỏi làm rõ,
- đề xuất hướng,
- chờ xác nhận,
- rồi mới lập plan/implement.

Nếu có nhiều hướng kiến trúc lớn, đưa 3 option:

1. Modern/SOTA.
2. Safe/stable.
3. MVP/simple.

Recommend hướng an toàn nhất cho DATN/CV demo: local-first MVP, nhưng structure đủ mở rộng.

---

## 1. Mục Tiêu V2 Cần Nắm

V2 không tiếp tục hướng "Vietnamese marketplace pricing-first" của plan cũ.

V2 là:

```text
Vietnamese-speaking US Deal Assistant
```

Người dùng trò chuyện bằng tiếng Việt, nhưng hệ thống tìm kiếm và định giá sản phẩm từ:

- Amazon
- BestBuy

Search/pricing sẽ reuse logic từ prototype English trong `segment4`, đặc biệt pipeline được mô tả ở:

```text
segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md
```

Kết quả sản phẩm có thể là tiếng Anh và giá là USD. Assistant phải tổng hợp, giải thích, và trả lời người dùng bằng tiếng Việt.

---

## 2. Những Gì Không Được Làm Ngay

Không làm các việc sau nếu chưa được tôi xác nhận rõ:

- Không implement runtime code.
- Không sửa `segment4/`.
- Không refactor prototype cũ.
- Không stage/commit/push.
- Không chạy AWS/Terraform/deploy.
- Không gọi model API tốn phí.
- Không scrape live Amazon/BestBuy nếu chưa được phép.
- Không cài dependency mới nếu chưa thống nhất.
- Không đọc/in secrets từ `.env`, credentials, keys, tokens.

`segment4/` là reference/prototype, không phải nơi implement V2.

---

## 3. Việc Đầu Tiên Phải Làm

Chạy:

```bash
git status --short
```

Mục tiêu:

- Nhận biết worktree đang có thay đổi gì.
- Không reset, stage, commit, xóa, ghi đè thay đổi có sẵn.
- Nếu thấy thay đổi không do bạn tạo, giữ nguyên và báo lại ngắn gọn.

Sau đó kiểm tra CodeGraph:

```bash
codegraph --version
codegraph status segment4
```

Nếu CodeGraph MCP có sẵn, ưu tiên `codegraph_explore` cho câu hỏi về architecture, call flow, symbol, impact trong `segment4`.

Nếu MCP chưa có, dùng CLI fallback:

```bash
cd segment4
codegraph explore "<câu hỏi cụ thể>"
```

Không tự ý chạy `codegraph init` nếu index lỗi hoặc thiếu. Báo tôi trước.

---

## 4. Tài Liệu Bắt Buộc Đọc

Đọc theo thứ tự này.

### 4.1. Context V2

```text
shopping_assistant_v2/README.md
shopping_assistant_v2/PROJECT_DEVELOPMENT_PLAN_V2.md
shopping_assistant_v2/PROJECT_STRUCTURE_AND_IMPLEMENTATION_ORDER.md
shopping_assistant_v2/docs/decisions.md
shopping_assistant_v2/docs/architecture.md
shopping_assistant_v2/docs/agent_architecture.md
```

### 4.2. Plans V2

Đọc tất cả:

```text
shopping_assistant_v2/plans/
```

Tối thiểu phải nắm:

- `00_context.md`
- `01_mvp_scope.md`
- `02_local_architecture.md`
- `03_backend_architecture.md`
- `05_agent_and_tool_architecture.md`
- `07_testing_and_validation.md`

### 4.3. Specs V2

Đọc các spec liên quan trực tiếp tới task. Trước khi implement phase mới, phải đọc đủ:

```text
shopping_assistant_v2/specs/repo_structure.md
shopping_assistant_v2/specs/api_contract.md
shopping_assistant_v2/specs/database_schema.md
shopping_assistant_v2/specs/job_orchestration.md
shopping_assistant_v2/specs/tool_contracts.md
shopping_assistant_v2/specs/agent_contracts.md
shopping_assistant_v2/specs/frontend_contract.md
shopping_assistant_v2/specs/logging_observability.md
shopping_assistant_v2/specs/testing_strategy.md
shopping_assistant_v2/specs/migration_from_segment4.md
```

### 4.4. Guides V2

Đọc guide tương ứng với phase được yêu cầu:

```text
shopping_assistant_v2/guides/
```

Nếu chưa rõ phase nào cần làm, dừng lại và hỏi tôi.

### 4.5. Prototype Và Report Cũ

Đọc để hiểu nguồn gốc quyết định:

```text
VIETNAMESE_PRICING_DEVELOPMENT_REPORT.md
segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md
segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md
segment4/mo_ta_du_an/Project_Development_Plan.md
README.md
```

Không cần đọc toàn bộ notebook/dataset nếu chưa có yêu cầu cụ thể.

---

## 5. Context Quan Trọng Cần Nhớ

### 5.1. Vì Sao Pivot Sang V2

Thực nghiệm dự đoán giá tiếng Việt dựa trên text chưa đủ tốt để làm core product. Vì vậy V2 dùng lại pipeline English tốt hơn:

- Amazon/BestBuy search.
- English ensemble pricing.
- USD estimated value.
- Vietnamese chat/summary layer.

### 5.2. MVP Bắt Buộc

MVP đầu tiên:

```text
Vietnamese chat
-> async job_id
-> controlled Router
-> deal_search_tool
-> price_estimator_tool
-> Vietnamese Synthesizer
-> Next.js answer + product cards
```

### 5.3. Architecture Đã Chốt

- App mới nằm trong `shopping_assistant_v2/`.
- `segment4/` giữ nguyên làm read-only reference.
- Frontend: Next.js chat-first.
- Backend: FastAPI local-first.
- Persistence: SQLite trước, schema tương thích Postgres.
- Auth MVP: `demo_user`, Clerk sau.
- Worker MVP: local async worker/job lifecycle.
- Model layer: LiteLLM/OpenAI default, Qwen/vLLM sau.
- AWS: chỉ làm sau khi local ổn định.

### 5.4. Quy Tắc Cuối Mỗi File Docs

Mỗi file trong `plans/`, `specs/`, `guides/`, `docs/` đều có gate:

```text
Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
```

Bạn phải tuân thủ gate này.

---

## 6. Báo Cáo Sau Khi Nạp Context

Sau khi đọc context và kiểm tra repo, chỉ báo cáo ngắn gọn theo format:

```text
Đã nạp context.

Repo status:
- <git status summary>

CodeGraph:
- Version: <version>
- segment4 index: <up-to-date/lỗi/chưa init>
- Cách dùng trong session: <MCP/CLI fallback>

V2 positioning:
- <1-2 dòng>

MVP đã chốt:
- <1-3 bullet>

Tài liệu V2 đã đọc:
- <liệt kê nhóm file chính>

Rủi ro/điểm cần giữ nguyên:
- <nếu có>

Câu hỏi cần làm rõ trước khi brainstorming tiếp:
- <chỉ hỏi câu ảnh hưởng scope/design/test/implementation>
```

Sau đó dừng lại và chờ tôi.

---

## 7. Khi Tôi Yêu Cầu Làm Một Phase

Trước khi implement:

1. Đọc guide/spec tương ứng.
2. Dùng CodeGraph nếu task liên quan tới `segment4`.
3. Brainstorm với tôi:
   - scope,
   - assumptions,
   - tradeoffs,
   - verification.
4. Đề xuất plan ngắn.
5. Chờ tôi xác nhận.
6. Sau đó mới viết code.

Không tự ý mở rộng scope.

---

## 8. Verification Rules

Khi đã được phép implement:

- Ưu tiên test nhỏ trước.
- Mặc định dùng mocks/fixtures, không gọi paid API/live scraping.
- Chỉ chạy real search/model tests nếu tôi xác nhận.
- Sau mỗi milestone, báo:
  - đã làm gì,
  - đã verify bằng gì,
  - còn rủi ro gì.

---

## 9. Output Style

- Giao tiếp tiếng Việt.
- Code/comments tiếng Anh.
- Không dùng emoji.
- Không fluff.
- Nếu có mâu thuẫn giữa docs, ưu tiên:
  1. System/developer instructions.
  2. `AGENTS.md`.
  3. `shopping_assistant_v2/PROJECT_DEVELOPMENT_PLAN_V2.md`.
  4. `shopping_assistant_v2/PROJECT_STRUCTURE_AND_IMPLEMENTATION_ORDER.md`.
  5. Specs trong `shopping_assistant_v2/specs/`.
  6. Guides/plans/docs.
  7. Tài liệu cũ trong `segment4/mo_ta_du_an/`.

---

## 10. First Question Template

Nếu tôi chưa chỉ rõ phase, hãy hỏi:

```text
Bạn muốn session này làm phase nào trước?

A. Docs/spec review và chỉnh tài liệu V2 (Recommended)
B. Phase 2: Local App Foundation, nhưng chỉ sau khi lập implementation plan
C. Phase 3: Extract search/pricing tools từ segment4, nhưng chỉ sau CodeGraph + plan
```

Không bắt đầu implement cho tới khi tôi chọn.
