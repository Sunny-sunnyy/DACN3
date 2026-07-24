# Phase 7: Testing And Demo

## Mục Đích

Harden local MVP để demo DATN/CV đáng tin cậy.

Phase này biến local app đang hoạt động thành repeatable demo với deterministic
tests, fixtures, known limitations, và opt-in real-mode instructions.

## Trạng Thái Hiện Tại

Phase 7 bắt đầu sau khi backend, worker, mock tools, Router/Synthesizer, và
frontend chat flow hoạt động local.

## Scope

Implement hoặc hoàn thiện:

- backend unit tests;
- backend integration test cho job lifecycle;
- tool fixture tests;
- Router/Synthesizer fixture tests;
- frontend smoke/component tests;
- progress_steps consistency tests;
- test-only rule-based evidence evaluator;
- manual demo script/checklist;
- opt-in real search/model test documentation;
- known limitations;
- verification commands trong docs.

## Non-Goals

- Không new major feature development.
- Không production deployment.
- Không Clerk auth.
- Không AWS/Terraform.
- Không default live scraping/model tests.
- Không broad UI redesign trừ khi cần cho demo reliability.

## Inputs From Previous Phases

Required:

- Phase 2 API.
- Phase 3 async jobs.
- Phase 4 mock tools.
- Phase 5 Router/Synthesizer.
- Phase 6 frontend chat.

## Contracts

Default tests không được:

- scrape live Amazon/BestBuy;
- call OpenAI;
- call Modal;
- require AWS;
- require secrets.

Backend tests bắt buộc:

- request validation;
- repository create/update/read;
- job status transition;
- Router fixture classification;
- Router unsupported/off-topic fixture examples lấy cảm hứng từ ITLR gate
  testing;
- tool input/output schema validation;
- Synthesizer fixture validation.

Backend integration test bắt buộc:

```text
create job
-> process by worker in mock mode
-> poll completed result
```

Frontend tests bắt buộc:

- component render smoke;
- API client handle pending/completed/failed;
- product cards render expected fields.
- progress panel render expected step statuses from backend response.

Evidence evaluator:

- Phase 7 dùng rule-based test-only validator, không runtime LLM judge.
- Validator kiểm tra `answer_vi`, product cards, warnings, và `progress_steps`
  đều được backed by tool/result evidence.
- Validator nên có fixture cases cho hallucinated URL, hallucinated price,
  missing warning, unsupported request, và progress step marked completed khi
  thiếu matching evidence.
- Ranking/evidence checks có thể mượn tư duy evaluation của ITLR nhưng phải giữ
  nhỏ: verify sorted deal cards, source coverage, warning propagation, và
  bounded result counts thay vì xây full recommender benchmark.
- Default evaluator tests không được gọi OpenAI, Modal, live scraping, AWS, hoặc
  secrets.
- Optional LLM-as-a-Judge kiểu Sidekick chỉ được đưa vào Phase 8 roadmap hoặc
  future opt-in work.

Latency và repeatability checks:

- thêm mock-mode latency smoke check cho backend job completion nếu làm được mà
  không tạo flaky timing assertions;
- ghi expected command outputs và known slow paths trong demo checklist;
- giữ real search/model latency measurements ở opt-in path, tách khỏi default
  tests.

Manual demo checklist:

- start backend;
- start frontend;
- submit Vietnamese request;
- observe status;
- verify Vietnamese answer;
- verify product cards;
- verify logs contain `job_id`;
- verify failure state nếu có thể.

## Workflow Gate

Trước khi code:

- Load `using-superpowers`.
- Dùng `brainstorming` với user.
- Chỉ hỏi các câu thay đổi scope, design, tests, hoặc implementation plan.
- Xác nhận test stacks và demo commands nào nằm trong scope.
- Trình bày Phase 7 plan.
- Chờ explicit approval.

## Implementation Order

1. Inventory existing tests.
2. Thêm missing backend unit tests.
3. Thêm backend integration test cho mock job lifecycle.
4. Thêm tool fixture tests.
5. Thêm Router/Synthesizer fixture tests.
6. Thêm frontend smoke tests.
7. Thêm progress_steps consistency tests.
8. Thêm test-only evidence evaluator.
9. Thêm small fixture-based ranking/warning checks nếu chưa có.
10. Thêm manual demo script/checklist.
11. Document opt-in real search/model tests riêng.
12. Document known limitations.
13. Chạy full local verification.
14. Viết Phase 7 report.

## Verification

Expected local verification:

```bash
uv run pytest
npm run test
npm run lint
```

Exact commands phụ thuộc implementation và phải được ghi trong report.

Manual verification phải cho thấy:

- mock mode demo hoạt động đáng tin cậy;
- không default test nào yêu cầu network/model calls;
- failed job path visible và safe;
- progress panel phản ánh đúng backend `progress_steps`;
- evidence evaluator phát hiện hallucinated price/URL/title/warnings trong test
  fixtures;
- fixture ranking checks chứng minh best cards được backed by discount
  evidence;
- latency/demo notes không biến opt-in real scraping/model calls thành default
  verification;
- logs trace được bằng `job_id`.

## Report Requirements

Viết:

```text
shopping_assistant_v3/reports/phase_7_testing_and_demo_report.md
```

Bao gồm:

- commands đã chạy;
- tests passed/failed;
- manual demo evidence;
- progress/evidence evaluator evidence;
- opt-in real-mode instructions đã thêm;
- known limitations;
- MVP có demo-ready hay không.

## Risks And Open Questions

- Frontend testing stack có thể cần dependency decisions.
- Live scraper reliability không nên block mock demo readiness.
- Real model costs phải giữ opt-in và documented.
- Demo script nên đủ ngắn cho repeatable DATN presentation.
- Không mở rộng Phase 7 thành full ITLR-style evaluation platform; chỉ giữ các
  checks phục vụ Shopping Assistant MVP.
