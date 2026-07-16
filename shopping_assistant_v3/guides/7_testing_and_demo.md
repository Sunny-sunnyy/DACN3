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
7. Thêm manual demo script/checklist.
8. Document opt-in real search/model tests riêng.
9. Document known limitations.
10. Chạy full local verification.
11. Viết Phase 7 report.

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
- opt-in real-mode instructions đã thêm;
- known limitations;
- MVP có demo-ready hay không.

## Risks And Open Questions

- Frontend testing stack có thể cần dependency decisions.
- Live scraper reliability không nên block mock demo readiness.
- Real model costs phải giữ opt-in và documented.
- Demo script nên đủ ngắn cho repeatable DATN presentation.
