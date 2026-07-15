# Cấu Trúc Dự Án Và Thứ Tự Triển Khai Shopping Assistant V2

**Dự án:** Vietnamese-speaking US Deal Assistant  
**Thư mục chính:** `shopping_assistant_v2/`  
**Trạng thái hiện tại:** Documentation-first, chưa implement runtime backend/frontend  
**Mục tiêu tài liệu này:** Mô tả đầy đủ cấu trúc dự án, nhiệm vụ từng thư mục, và thứ tự triển khai được khuyến nghị cho coding agents.

---

## 1. Dự Án Này Là Gì

`shopping_assistant_v2/` là phiên bản kế hoạch mới cho đồ án tốt nghiệp. Dự án không tiếp tục hướng cũ là xây dựng mô hình ước giá tiếng Việt làm lõi sản phẩm, vì kết quả thực nghiệm dự đoán giá tiếng Việt bằng text chưa đủ tốt để làm nền tảng demo chính.

Hướng mới là:

```text
Trợ lý mua sắm nói tiếng Việt
-> tìm kiếm sản phẩm trên Amazon và BestBuy
-> ước tính giá trị sản phẩm bằng pipeline ensemble tiếng Anh
-> tổng hợp và giải thích kết quả bằng tiếng Việt
```

Người dùng trò chuyện bằng tiếng Việt. Kết quả sản phẩm lấy từ Amazon/BestBuy có thể giữ tên, thông số, nguồn bằng tiếng Anh. Giá trả về theo USD.

---

## 2. Mức Độ Đầy Đủ Của Bộ Tài Liệu Hiện Tại

Bộ `plans/`, `specs/`, `guides/`, `docs/` hiện tại khoảng hơn 3,000 dòng. Nó **không phải là toàn bộ implementation blueprint ở mức từng function/class**, mà là bộ tài liệu nền tảng để thống nhất hướng phát triển và giao việc cho coding agents theo phase.

### 2.1. Đã Đủ Cho Giai Đoạn Nào

Bộ tài liệu hiện tại đủ để bắt đầu các phase sau:

1. Review lại scope V2.
2. Tạo local app foundation.
3. Thiết kế backend FastAPI.
4. Thiết kế async job lifecycle.
5. Thiết kế SQLite schema.
6. Thiết kế Next.js chat-first frontend.
7. Thiết kế contracts cho `deal_search_tool` và `price_estimator_tool`.
8. Thiết kế Router và Vietnamese Synthesizer.
9. Thiết kế test strategy dùng mock/fixture trước.

Nói ngắn gọn: tài liệu hiện tại **đủ cho MVP search + price + Vietnamese summary**.

### 2.2. Chưa Đủ Sâu Cho Giai Đoạn Nào

Các phần sau mới ở mức roadmap/spec sơ bộ, chưa đủ để coding agent implement ngay mà không brainstorming/research thêm:

- Compare Agent chi tiết.
- Advisor Agent chi tiết.
- Clerk authentication.
- Supabase/Postgres migration.
- AWS deployment.
- Queue/SQS production.
- Observability production: LangFuse, OpenAI traces, CloudWatch.
- UI/UX visual design chi tiết.
- Scale scraping, rate limiting, proxy, anti-bot strategy.

Trước khi implement các phần này, coding agent phải mở rộng spec tương ứng.

### 2.3. Có Yêu Cầu Phát Triển Sau MVP Không

Có. `PROJECT_DEVELOPMENT_PLAN_V2.md`, `plans/08_roadmap_to_production.md`, và nhiều specs/guides đã ghi rõ sau MVP sẽ phát triển tiếp:

- Compare.
- Advisor.
- Clerk auth.
- Supabase/Postgres.
- AWS deployment.
- Production observability.
- UI/UX polish.
- More sources nếu cần.

MVP không phải điểm kết thúc. MVP chỉ là vertical slice đầu tiên để chứng minh app chạy được end-to-end.

---

## 3. Cấu Trúc Thư Mục Hiện Tại

```text
shopping_assistant_v2/
├── README.md
├── PROJECT_DEVELOPMENT_PLAN_V2.md
├── PROJECT_STRUCTURE_AND_IMPLEMENTATION_ORDER.md
├── PROMPT_NEW_SESSION.md
├── plans/
├── specs/
├── guides/
├── docs/
└── scripts/
```

### 3.1. `README.md`

Vai trò:

- Giới thiệu nhanh dự án V2.
- Nói rõ đây là Vietnamese-speaking US Deal Assistant.
- Nói rõ `segment4/` là prototype/reference.
- Nêu reading order cơ bản.
- Nêu non-goals của MVP.

Khi dùng:

- File đầu tiên nên đọc khi mở folder `shopping_assistant_v2/`.

### 3.2. `PROJECT_DEVELOPMENT_PLAN_V2.md`

Vai trò:

- Source of truth cấp cao cho V2.
- Giải thích lý do pivot khỏi plan V1.
- Định vị sản phẩm.
- Mô tả MVP vertical slice.
- Mô tả architecture tổng quan.
- Mô tả phases từ local MVP đến future production.
- Mô tả rủi ro và success criteria.

Khi dùng:

- Coding agent phải đọc trước mọi implementation.
- Nếu mâu thuẫn với file nhỏ hơn, ưu tiên file này trừ khi spec chi tiết mới đã được người dùng xác nhận cập nhật.

### 3.3. `PROMPT_NEW_SESSION.md`

Vai trò:

- Prompt handoff cho coding agents trong session mới.
- Yêu cầu nạp context đầy đủ.
- Yêu cầu kiểm tra `git status` và CodeGraph.
- Yêu cầu dùng `using-superpowers` và `brainstorming`.
- Cấm code ngay khi chưa brainstorming và chưa được xác nhận.

Khi dùng:

- Copy hoặc đưa file này cho coding agent mới trước khi giao task.

### 3.4. `PROJECT_STRUCTURE_AND_IMPLEMENTATION_ORDER.md`

Vai trò:

- File hiện tại.
- Mô tả cấu trúc folder.
- Mô tả nhiệm vụ mỗi folder.
- Mô tả thứ tự triển khai.
- Giải thích coverage của bộ 33 file tài liệu.

Khi dùng:

- Đọc sau `PROJECT_DEVELOPMENT_PLAN_V2.md` để biết nên triển khai theo thứ tự nào.

### 3.5. `plans/`

Vai trò:

- Trả lời câu hỏi: **Vì sao làm như vậy, phase nào trước, scope đến đâu?**
- Đây là tài liệu chiến lược.
- Không phải API/schema contract chi tiết.

Khi dùng:

- Đọc trước specs nếu chưa rõ hướng tổng thể.
- Cập nhật khi scope hoặc roadmap thay đổi.

### 3.6. `specs/`

Vai trò:

- Trả lời câu hỏi: **Implement chính xác contract gì?**
- Đây là tài liệu kỹ thuật cho coding agents.
- API, DB, tools, agents, frontend, logging, testing đều phải bám vào specs.

Khi dùng:

- Đọc trước khi viết code.
- Nếu spec chưa đủ chi tiết cho task, dừng lại brainstorming/research và cập nhật spec trước.

### 3.7. `guides/`

Vai trò:

- Trả lời câu hỏi: **Làm từng bước như thế nào?**
- Đây là runbook triển khai theo phase.
- Mỗi guide nên có Goal, Prerequisites, Steps, Verify, Troubleshooting, Next Guide.

Khi dùng:

- Khi bắt đầu một phase cụ thể, đọc guide tương ứng.
- Không nhảy guide nếu prerequisites chưa xong.

### 3.8. `docs/`

Vai trò:

- Chứa giải thích kiến trúc, decisions, agent architecture, UI/UX research.
- Đây là tài liệu hỗ trợ hiểu hệ thống.
- Không thay thế specs/guides.

Khi dùng:

- Đọc để hiểu quyết định thiết kế.
- Cập nhật khi có ADR hoặc thay đổi kiến trúc.

### 3.9. `scripts/`

Vai trò:

- Hiện chưa có runtime script.
- Sau này chứa helper scripts cho local dev, test, setup, demo.

Khi dùng:

- Chỉ thêm script sau khi có implementation plan được xác nhận.
- Script phải an toàn, không hard-code secrets.

---

## 4. Cấu Trúc Runtime Dự Kiến Sau Này

Hiện chưa tạo runtime code. Khi bắt đầu implement, cấu trúc dự kiến sẽ là:

```text
shopping_assistant_v2/
├── backend/
│   ├── README.md
│   ├── shared/
│   ├── database/
│   ├── api/
│   ├── router/
│   ├── tools/
│   │   ├── deal_search/
│   │   └── price_estimator/
│   ├── synthesizer/
│   ├── comparer/
│   └── advisor/
├── frontend/
├── scripts/
├── plans/
├── specs/
├── guides/
└── docs/
```

### 4.1. `backend/`

Vai trò:

- Chứa toàn bộ backend local-first.
- FastAPI API.
- SQLite persistence.
- Local async worker.
- Router, tools, synthesizer.

Không nên:

- Nhồi toàn bộ logic vào một file.
- Để route FastAPI chạy long-running scraping/model calls trực tiếp.
- Import trực tiếp lung tung từ `segment4`.

### 4.2. `backend/shared/`

Nhiệm vụ:

- Config.
- Structured logging.
- Common schemas.
- Guardrails.
- Retry helpers.
- Error types.
- HTTP client helpers.

Quy tắc:

- Không phụ thuộc ngược vào `router`, `tools`, `synthesizer`.
- Chỉ chứa code dùng chung thật sự.

### 4.3. `backend/database/`

Nhiệm vụ:

- SQLite schema.
- Repository layer.
- Job persistence.
- Conversations/messages.
- Agent run audit.
- Product and price estimate storage.

Các bảng cốt lõi:

- `jobs`
- `conversations`
- `messages`
- `agent_runs`
- `products`
- `price_estimates`

### 4.4. `backend/api/`

Nhiệm vụ:

- FastAPI app.
- `GET /health`
- `POST /api/chat-jobs`
- `GET /api/chat-jobs/{job_id}`
- optional `GET /api/chat-jobs/{job_id}/events`

Quy tắc:

- API tạo job và trả `job_id` ngay.
- API không chờ scraper/model chạy xong.
- API không expose stack trace.

### 4.5. `backend/router/`

Nhiệm vụ:

- Load job.
- Classify intent tiếng Việt.
- Chọn path `search_deals` trong MVP.
- Gọi tools.
- Gọi synthesizer.
- Update job status.

MVP không dùng ReAct tự do.

### 4.6. `backend/tools/deal_search/`

Nhiệm vụ:

- Tìm sản phẩm Amazon/BestBuy.
- Normalize product candidates.
- Trả về source, title, brand, sale price USD, URL, features.

Nguồn tham khảo:

- `segment4/price_agents/bestbuy_deals.py`
- `segment4/price_agents/amazon_deals.py`
- `segment4/bestbuy_untils/unified_deal.py`

### 4.7. `backend/tools/price_estimator/`

Nhiệm vụ:

- Ước tính fair value USD.
- Tính discount USD.
- Gán deal score.
- Trả model breakdown nếu có.

Nguồn tham khảo:

- `segment4/price_agents/ensemble_agent.py`
- `segment4/price_agents/frontier_agent.py`
- `segment4/price_agents/specialist_agent.py`
- `segment4/price_agents/neural_network_agent.py`

### 4.8. `backend/synthesizer/`

Nhiệm vụ:

- Tổng hợp output của tools thành câu trả lời tiếng Việt.
- Không bịa giá.
- Không bịa URL.
- Giữ product name tiếng Anh nếu rõ hơn.
- Nêu warning nếu source/tool lỗi một phần.

### 4.9. `backend/comparer/`

Nhiệm vụ sau MVP:

- So sánh nhiều sản phẩm.
- Tạo comparison table.
- Giải thích pros/cons.
- Rank theo tiêu chí người dùng.

Không bắt buộc trong MVP.

### 4.10. `backend/advisor/`

Nhiệm vụ sau MVP:

- Tư vấn sản phẩm phù hợp nhu cầu.
- Dựa trên kết quả search/price/compare.
- Giải thích tradeoff.

Không bắt buộc trong MVP.

### 4.11. `frontend/`

Nhiệm vụ:

- Next.js chat-first UI.
- Gửi request tạo job.
- Poll job status.
- Render Vietnamese answer.
- Render product cards.
- Hiển thị debug `job_id` và warnings.

Không bắt buộc phải chốt visual design quá sớm. UI/UX sẽ research sau.

---

## 5. Thứ Tự Đọc Tài Liệu Khi Bắt Đầu Session Mới

Coding agent mới nên đọc theo thứ tự:

1. `shopping_assistant_v2/PROMPT_NEW_SESSION.md`
2. `shopping_assistant_v2/README.md`
3. `shopping_assistant_v2/PROJECT_DEVELOPMENT_PLAN_V2.md`
4. `shopping_assistant_v2/PROJECT_STRUCTURE_AND_IMPLEMENTATION_ORDER.md`
5. `shopping_assistant_v2/docs/decisions.md`
6. `shopping_assistant_v2/docs/architecture.md`
7. `shopping_assistant_v2/plans/00_context.md`
8. `shopping_assistant_v2/plans/01_mvp_scope.md`
9. Spec liên quan tới phase đang làm.
10. Guide liên quan tới phase đang làm.

Nếu task liên quan tới reuse code từ `segment4`, đọc thêm:

1. `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`
2. `shopping_assistant_v2/specs/migration_from_segment4.md`
3. `shopping_assistant_v2/specs/tool_contracts.md`
4. CodeGraph query liên quan tới flow cần extract.

---

## 6. Thứ Tự Triển Khai Theo Phase

### Phase 0: Nạp Context Và Brainstorming

Mục tiêu:

- Không code.
- Không sửa file.
- Nạp toàn bộ context.
- Thảo luận scope với người dùng.

Các file phải đọc:

1. `PROMPT_NEW_SESSION.md`
2. `README.md`
3. `PROJECT_DEVELOPMENT_PLAN_V2.md`
4. `PROJECT_STRUCTURE_AND_IMPLEMENTATION_ORDER.md`
5. `plans/00_context.md`
6. `plans/01_mvp_scope.md`

Verify:

- Agent báo cáo được repo status.
- Agent báo cáo được CodeGraph status.
- Agent giải thích được V2 positioning.

### Phase 1: Review Và Cập Nhật Documentation Foundation

Mục tiêu:

- Làm tài liệu đủ rõ trước khi code.
- Không implement runtime.

Thứ tự xử lý:

1. Review `PROJECT_DEVELOPMENT_PLAN_V2.md`.
2. Review toàn bộ `plans/`.
3. Review toàn bộ `specs/`.
4. Review toàn bộ `guides/`.
5. Review `docs/`.
6. Bổ sung chỗ thiếu.
7. Loại bỏ mâu thuẫn.

Verify:

- Mỗi phase có guide tương ứng.
- Mỗi contract quan trọng có spec.
- Không còn chỗ mơ hồ blocking implementation.

### Phase 2: Local Backend Foundation

Mục tiêu:

- Tạo FastAPI backend local.
- Tạo SQLite schema.
- Tạo API job endpoints.

Đọc trước:

1. `plans/02_local_architecture.md`
2. `plans/03_backend_architecture.md`
3. `specs/repo_structure.md`
4. `specs/api_contract.md`
5. `specs/database_schema.md`
6. `guides/2_backend_api.md`

Thứ tự triển khai:

1. Tạo `backend/`.
2. Tạo `backend/shared/`.
3. Tạo `backend/database/`.
4. Tạo `backend/api/`.
5. Implement `GET /health`.
6. Implement SQLite init.
7. Implement `POST /api/chat-jobs`.
8. Implement `GET /api/chat-jobs/{job_id}`.

Verify:

- Backend chạy local.
- Health endpoint OK.
- Tạo job trả `job_id`.
- Poll job trả status `pending`.

### Phase 3: Local Async Job Worker

Mục tiêu:

- Job lifecycle chạy end-to-end bằng mock result.

Đọc trước:

1. `specs/job_orchestration.md`
2. `specs/logging_observability.md`
3. `guides/3_async_jobs.md`

Thứ tự triển khai:

1. Tạo worker local.
2. Worker nhận hoặc poll `job_id`.
3. Update status `running`.
4. Ghi mock result.
5. Update status `completed`.
6. Handle exception -> `failed`.
7. Thêm structured logs.

Verify:

- Job đi từ `pending` -> `running` -> `completed`.
- Failed path hoạt động.
- Logs có `job_id`.

### Phase 4: Tool Contracts Và Mock Tools

Mục tiêu:

- Implement tool interfaces bằng fixtures trước.
- Chưa gọi Amazon/BestBuy thật.
- Chưa gọi model thật.

Đọc trước:

1. `plans/05_agent_and_tool_architecture.md`
2. `specs/tool_contracts.md`
3. `specs/testing_strategy.md`

Thứ tự triển khai:

1. Tạo `backend/tools/`.
2. Tạo `backend/tools/deal_search/`.
3. Tạo `backend/tools/price_estimator/`.
4. Tạo schemas.
5. Tạo fixtures.
6. Implement mock `deal_search_tool`.
7. Implement mock `price_estimator_tool`.
8. Test schema và mock output.

Verify:

- Tools chạy không cần network.
- Tools trả đúng schema.
- Warnings được preserve.

### Phase 5: Router Và Synthesizer Mock/Provider Layer

Mục tiêu:

- Router hiểu intent tiếng Việt.
- Synthesizer trả lời tiếng Việt từ evidence.

Đọc trước:

1. `specs/agent_contracts.md`
2. `guides/5_router_and_synthesizer.md`
3. `docs/agent_architecture.md`

Thứ tự triển khai:

1. Tạo `backend/router/`.
2. Tạo `backend/synthesizer/`.
3. Tạo Router schema.
4. Tạo Synthesizer schema.
5. Implement deterministic fallback/mock.
6. Sau đó mới thêm LiteLLM/OpenAI provider nếu được phép.
7. Validate model output.

Verify:

- Query tiếng Việt được route vào `search_deals`.
- Synthesizer trả lời tiếng Việt.
- Không bịa giá/spec/URL.

### Phase 6: Frontend Next.js Chat MVP

Mục tiêu:

- UI chat-first chạy local.
- Tạo job.
- Poll status.
- Render result.

Đọc trước:

1. `plans/04_frontend_architecture.md`
2. `specs/frontend_contract.md`
3. `guides/6_frontend_chat.md`
4. `docs/ui_ux_research.md`

Thứ tự triển khai:

1. Tạo `frontend/`.
2. Chọn App Router hoặc Pages Router.
3. Tạo API client.
4. Tạo ChatPanel.
5. Tạo JobStatus.
6. Tạo ProductCard.
7. Tạo ProductResults.
8. Tạo DebugLogPanel.
9. Kết nối backend.

Verify:

- User gửi tiếng Việt.
- UI nhận `job_id`.
- UI poll status.
- UI render Vietnamese answer và product cards.

### Phase 7: Extract Real Search Tool Từ Segment4

Mục tiêu:

- Adapt Amazon/BestBuy search từ prototype.
- Không sửa `segment4`.

Đọc trước:

1. `specs/migration_from_segment4.md`
2. `guides/4_extract_search_pricing_tools.md`
3. `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`

CodeGraph bắt buộc:

```text
How does search_key.py run Amazon and BestBuy search through MultiSourcePlanningAgent?
```

Thứ tự triển khai:

1. Inspect code bằng CodeGraph.
2. Extract minimal BestBuy search behavior.
3. Extract minimal Amazon search behavior.
4. Normalize output theo V2 schema.
5. Add opt-in real test.
6. Preserve mock tests.

Verify:

- Mock tests vẫn pass.
- Real search opt-in chạy được khi được phép.
- `segment4` không đổi.

### Phase 8: Extract Real Price Estimator Tool Từ Segment4

Mục tiêu:

- Adapt ensemble pricing vào V2 tool.

Đọc trước:

1. `specs/tool_contracts.md`
2. `specs/migration_from_segment4.md`
3. `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`

CodeGraph bắt buộc:

```text
How does EnsembleAgent estimate prices using frontier specialist neural network?
```

Thứ tự triển khai:

1. Inspect ensemble flow bằng CodeGraph.
2. Extract preprocessor nếu cần.
3. Extract FrontierAgent bridge.
4. Extract SpecialistAgent bridge.
5. Extract NeuralNetworkAgent bridge.
6. Wrap weighted average.
7. Return V2 schema.
8. Add opt-in real model test.

Verify:

- Mock pricing vẫn pass.
- Real pricing opt-in chạy được khi có env/model.
- Tool trả estimated USD và discount USD.

### Phase 9: End-To-End Local Demo

Mục tiêu:

- Demo hoàn chỉnh local.

Đọc trước:

1. `plans/07_testing_and_validation.md`
2. `guides/7_testing_demo.md`
3. `specs/testing_strategy.md`

Thứ tự triển khai:

1. Backend start.
2. Frontend start.
3. Submit Vietnamese query.
4. Job created.
5. Router runs.
6. Tools run.
7. Synthesizer runs.
8. Frontend renders answer/cards.
9. Logs show `job_id`.

Verify:

- Demo path mock mode ổn định.
- Optional real mode documented.
- Known limitations documented.

### Phase 10: Post-MVP Expansion

Mục tiêu:

- Mở rộng sau khi MVP ổn.

Thứ tự ưu tiên:

1. Compare Agent.
2. Advisor Agent.
3. UI/UX research và polish.
4. Clerk auth.
5. Supabase/Postgres.
6. Queue-backed worker.
7. Production observability.
8. AWS deployment.

Không bắt đầu phase này nếu MVP chưa ổn.

---

## 7. Thứ Tự Làm Việc Với `plans/`

Nên đọc và triển khai theo thứ tự:

1. `00_context.md`
2. `01_mvp_scope.md`
3. `02_local_architecture.md`
4. `03_backend_architecture.md`
5. `06_data_and_persistence.md`
6. `05_agent_and_tool_architecture.md`
7. `04_frontend_architecture.md`
8. `07_testing_and_validation.md`
9. `08_roadmap_to_production.md`

Lý do thứ tự này:

- Hiểu context trước.
- Chốt MVP scope trước.
- Xây local/backend/database trước.
- Sau đó mới đến agent/tools/frontend.
- Testing phải đi cùng mọi phase.
- Production roadmap để sau.

---

## 8. Thứ Tự Làm Việc Với `specs/`

Nên đọc và triển khai theo thứ tự:

1. `repo_structure.md`
2. `api_contract.md`
3. `database_schema.md`
4. `job_orchestration.md`
5. `logging_observability.md`
6. `tool_contracts.md`
7. `agent_contracts.md`
8. `frontend_contract.md`
9. `testing_strategy.md`
10. `migration_from_segment4.md`

Lý do thứ tự này:

- Repo structure quyết định file/folder.
- API và DB quyết định backbone.
- Job orchestration quyết định async flow.
- Logging đi sớm để debug.
- Tool/agent/frontend triển khai sau khi backbone có.
- Migration từ `segment4` chỉ nên làm sau khi contracts đã rõ.

---

## 9. Thứ Tự Làm Việc Với `guides/`

Nên đi đúng thứ tự:

1. `1_local_setup.md`
2. `2_backend_api.md`
3. `3_async_jobs.md`
4. `4_extract_search_pricing_tools.md`
5. `5_router_and_synthesizer.md`
6. `6_frontend_chat.md`
7. `7_testing_demo.md`
8. `8_future_production.md`

Lưu ý:

- Có thể làm mock tools trước real extraction nếu muốn giảm rủi ro.
- Không nên làm frontend production polish trước khi API contract ổn.
- Không nên làm real search/pricing trước khi mock lifecycle pass.

---

## 10. Thứ Tự Làm Việc Với `docs/`

Nên đọc theo thứ tự:

1. `decisions.md`
2. `architecture.md`
3. `agent_architecture.md`
4. `ui_ux_research.md`

Cập nhật docs khi:

- Có quyết định kiến trúc mới.
- Có thay đổi scope.
- Có thay đổi flow agent/tool.
- Có research UI/UX mới.

---

## 11. Quy Tắc Quan Trọng Khi Giao Cho Coding Agents

Mỗi coding agent trước khi làm phải:

1. Đọc `PROMPT_NEW_SESSION.md`.
2. Chạy `git status --short`.
3. Kiểm tra CodeGraph nếu task liên quan `segment4`.
4. Đọc plan/spec/guide tương ứng.
5. Brainstorm/research lại phần sắp làm.
6. Hỏi xác nhận nếu scope chưa rõ.
7. Chỉ implement khi được duyệt.
8. Verify bằng test nhỏ nhất.
9. Báo lại thay đổi, test, rủi ro.

Không được:

- Tự ý sửa `segment4`.
- Tự ý gọi API tốn phí.
- Tự ý scrape live.
- Tự ý deploy AWS.
- Tự ý thêm dependency lớn.
- Tự ý mở rộng MVP sang compare/advisor/auth khi chưa được giao.

---

## 12. Kết Luận

Bộ tài liệu hiện tại đã đủ để định hướng và bắt đầu triển khai **MVP local-first** cho `shopping_assistant_v2`.

Tuy nhiên, nó chưa phải tài liệu cuối cùng cho toàn bộ sản phẩm production. Các phần post-MVP như Compare, Advisor, Clerk, Supabase/Postgres, AWS, observability production cần được brainstorming/research và mở rộng specs trước khi implement.

Thứ tự đúng là:

```text
Context
-> Documentation review
-> Backend API
-> Async jobs
-> Mock tools
-> Router/Synthesizer
-> Frontend chat
-> Real search/pricing extraction
-> End-to-end demo
-> Post-MVP expansion
```

Không đi ngược thứ tự này nếu chưa có lý do kỹ thuật rõ ràng và chưa được người dùng xác nhận.

## Brainstorming And Research Gate

Trước khi triển khai bất kỳ phần nào trong tài liệu này, coding agent phải brainstorming/research lại phần đó để xác minh giả định, tối ưu scope, và cập nhật tài liệu nếu phát hiện hướng tốt hơn.
