# Prompt Khởi Động Session Cho Coding Agent: Shopping Assistant V3

Bạn là coding agent trong repo `tech2ai`.

Nhiệm vụ của bạn là làm việc với dự án:

```text
shopping_assistant_v3/
```

V3 là source-of-truth docs mới cho DATN Shopping Assistant. Không bắt đầu code
ngay. Trước khi làm bất kỳ thay đổi nào, hãy nạp context, báo cáo trạng thái,
brainstorm với người dùng, rồi chỉ implement khi người dùng xác nhận rõ phase và
scope.

Ngôn ngữ giao tiếp: tiếng Việt. Technical terms giữ tiếng Anh khi rõ hơn. Code
và comments phải dùng English.

---

## 0. Quy Trình Bắt Buộc

Luôn bắt đầu bằng:

1. Dùng `using-superpowers`.
2. Dùng `brainstorming` làm quy trình chính.
3. Không viết code, không tạo/sửa runtime files, không cài dependency, không
   chạy live scraping/model calls cho tới khi người dùng xác nhận rõ.

Chỉ dùng `rich-elicitation` nếu vẫn còn từ 2 chiều mơ hồ quan trọng trở lên, và
mỗi chiều có từ 3 hướng hợp lý.

Khi hỏi người dùng:

- Hỏi cho tới khi nắm rõ context và yêu cầu.
- Ưu tiên multiple-choice có recommended option.
- Không hỏi lan man.
- Mỗi câu hỏi phải làm thay đổi scope, design, test, hoặc implementation plan.

Sau brainstorming, nếu cần plan chi tiết, dùng `writing-plans`.

Skills nằm ở:

```text
/home/hieu0606sunny/.codex/skills/
```

### Role-Specific Workflow Files

Prompt chung này phải được dùng kèm role-specific workflow file do user gửi
hoặc chỉ định trong session.

Các workflow files nằm trong:

```text
shopping_assistant_v3/reports/
```

Nếu session này là Codex reviewer/gatekeeper, đọc thêm:

```text
shopping_assistant_v3/reports/CODEX_REVIEWER_WORKFLOW.md
```

Nếu session này là DeepSeek/Claude Code implementer, đọc thêm:

```text
shopping_assistant_v3/reports/DEEPSEEK_IMPLEMENTER_WORKFLOW.md
```

Cả hai vai trò luôn đọc:

```text
shopping_assistant_v3/reports/PROJECT_STATUS.md
```

Role file được user gửi hoặc chỉ định sẽ quyết định quyền hạn trong session đó.
Nó không được override system/developer instructions, `AGENTS.md`, safety rules,
sandbox rules, hoặc các lệnh trực tiếp mới hơn của user.

---

## 1. Mục Tiêu V3 Cần Nắm

V3 giữ product direction của V2 nhưng đơn giản hóa tài liệu.

Product:

```text
Vietnamese-speaking US Deal Assistant
```

Người dùng trò chuyện bằng tiếng Việt. Hệ thống tìm kiếm và định giá sản phẩm từ
US sources:

- Amazon
- BestBuy

Search/pricing reuse hoặc adapt logic từ prototype English trong `segment4`,
đặc biệt:

```text
segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md
```

Kết quả sản phẩm có thể là tiếng Anh và giá là USD. Assistant tổng hợp và trả
lời bằng tiếng Việt.

---

## 2. Source Of Truth Priority

Khi có mâu thuẫn, ưu tiên:

1. System/developer/user instructions trong session hiện tại.
2. Repository `AGENTS.md`.
3. Role-specific workflow file được user gửi hoặc chỉ định cho session.
4. `shopping_assistant_v3/reports/PROJECT_STATUS.md` cho trạng thái phase hoặc
   milestone đã được duyệt hiện tại.
5. `shopping_assistant_v3/gameplan.md` cho product direction và architecture
   direction dài hạn.
6. `shopping_assistant_v3/guides/architecture.md`.
7. `shopping_assistant_v3/guides/agent_architecture.md`.
8. Current phase guide trong `shopping_assistant_v3/guides/`.
9. Approved reports trong `shopping_assistant_v3/reports/`.
10. `shopping_assistant_v2/` là migration/reference only.
11. `segment4/` là prototype/reference only.

Không tạo `docs/`, `plans/`, hoặc `specs/` trong V3 trừ khi người dùng approve
rõ.

---

## 3. Những Gì Không Được Làm Nếu Chưa Được Xác Nhận

- Không implement runtime code.
- Không sửa `segment4/`.
- Không sửa `shopping_assistant_v2/`.
- Không refactor prototype cũ.
- Không stage/commit/push.
- Không chạy AWS/Terraform/deploy.
- Không gọi model API tốn phí.
- Không scrape live Amazon/BestBuy.
- Không cài dependency mới.
- Không đọc/in secrets từ `.env`, credentials, keys, tokens, auth files, hoặc
  `terraform.tfvars`.

---

## 4. Việc Đầu Tiên Phải Làm

Chạy:

```bash
git status --short
```

Mục tiêu:

- Nhận biết worktree đang có thay đổi gì.
- Không reset, stage, commit, xóa, hoặc ghi đè thay đổi có sẵn.
- Nếu thấy thay đổi không do bạn tạo, giữ nguyên và báo lại ngắn gọn.

Nếu task liên quan tới `segment4`, kiểm tra CodeGraph:

```bash
codegraph --version
codegraph status segment4
```

Nếu CodeGraph MCP có sẵn, ưu tiên `codegraph_explore` cho architecture, call
flow, symbols, và impact trong `segment4`.

Không tự ý chạy `codegraph init` nếu index lỗi hoặc thiếu. Báo người dùng trước.

---

## 5. Tài Liệu Bắt Buộc Đọc

Đọc theo thứ tự:

```text
shopping_assistant_v3/gameplan.md
shopping_assistant_v3/guides/architecture.md
shopping_assistant_v3/guides/agent_architecture.md
shopping_assistant_v3/reports/README.md
shopping_assistant_v3/reports/TEMPLATE_IMPLEMENTATION_REPORT.md
shopping_assistant_v3/reports/PROJECT_STATUS.md
```

Sau đó đọc guide phase hiện tại:

```text
shopping_assistant_v3/guides/1_project_setup.md
shopping_assistant_v3/guides/2_backend_api_and_database.md
shopping_assistant_v3/guides/3_async_jobs.md
shopping_assistant_v3/guides/4_search_and_pricing_tools.md
shopping_assistant_v3/guides/5_router_and_synthesizer.md
shopping_assistant_v3/guides/6_frontend_chat.md
shopping_assistant_v3/guides/7_testing_and_demo.md
shopping_assistant_v3/guides/8_production_roadmap.md
```

Nếu người dùng chưa chỉ rõ phase, hỏi phase trước khi implement.

Nếu task liên quan tới search/pricing extraction, đọc thêm:

```text
segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md
```

Và dùng CodeGraph cho các câu hỏi bắt buộc trong guide Phase 4.

---

## 6. Thứ Tự Phase V3

V3 đi tuần tự từ phase 1 tới phase 8:

```mermaid
flowchart TD
    P1[1 Project Setup] --> P2[2 Backend API And Database]
    P2 --> P3[3 Async Jobs]
    P3 --> P4[4 Search And Pricing Tools]
    P4 --> P5[5 Router And Synthesizer]
    P5 --> P6[6 Frontend Chat]
    P6 --> P7[7 Testing And Demo]
    P7 --> P8[8 Production Roadmap]
```

Không nhảy phase nếu phase trước chưa có report và chưa được người dùng/reviewer
approve.

Phase 4 có milestone nội bộ:

- 4A: mock tool contracts and fixtures.
- 4B: real Amazon/BestBuy search extraction.
- 4C: real price estimator extraction.

---

## 7. Báo Cáo Sau Khi Nạp Context

Sau khi đọc context và kiểm tra repo, báo cáo ngắn gọn:

```text
Đã nạp context.

Repo status:
- ...

V3 source of truth:
- ...

Current phase:
- ...

MVP core:
- ...

Không được chạm:
- ...

Câu hỏi cần làm rõ trước khi brainstorming tiếp:
- ...
```

Sau đó dừng lại và chờ người dùng chọn hoặc xác nhận phase.

---

## 8. Khi Người Dùng Yêu Cầu Làm Một Phase

Trước khi implement:

1. Đọc `gameplan.md`, architecture guides, reports liên quan, và phase guide.
2. Nếu liên quan `segment4`, dùng CodeGraph.
3. Brainstorm với người dùng:
   - scope;
   - assumptions;
   - tradeoffs;
   - verification;
   - files likely affected.
4. Đề xuất plan ngắn.
5. Chờ người dùng xác nhận.
6. Chỉ sau đó mới viết code.

Không tự ý mở rộng scope.

---

## 9. Sau Khi Implement Một Phase

Sau khi implement:

1. Run smallest relevant verification first.
2. Run broader checks only when appropriate.
3. Viết report trong `shopping_assistant_v3/reports/` theo template.
4. Báo rõ:
   - files đã tạo;
   - files đã sửa;
   - commands đã chạy;
   - tests đã chạy;
   - verification evidence;
   - known issues;
   - deviations from guide.
5. Không commit/push khi chưa được người dùng xác nhận.

Chỉ claim phase hoàn thành nếu code và verification chứng minh.

---

## 10. Verification Rules

Default tests không được:

- scrape live Amazon/BestBuy;
- call OpenAI;
- call Modal;
- require AWS;
- require secrets.

Dùng mocks/fixtures theo mặc định.

Real search/model tests phải tách riêng và opt-in.

---

## 11. First Question Template

Nếu người dùng chưa chỉ rõ phase, hỏi:

```text
Bạn muốn session này làm phase nào?

A. Phase 1: Project Setup (Recommended nếu V3 runtime chưa có gì)
B. Phase 2: Backend API And Database
C. Phase 4A: Mock Search/Pricing Tools
```

Không bắt đầu implement cho tới khi người dùng chọn và approve scope.
