# Phase 6: Frontend Chat

## Mục Đích

Xây Next.js chat-first frontend để submit Vietnamese messages, poll job status,
và render Vietnamese answers với product cards.

## Trạng Thái Hiện Tại

Phase 6 bắt đầu sau khi backend có thể hoàn thành mock end-to-end job và trả về
result payload khớp API contract.

Không có frontend cho tới phase này hoặc Phase 1 tạo skeleton.

## Scope

Implement:

- Next.js frontend app.
- API client cho backend job endpoints.
- chat input và submit flow.
- job polling.
- status display.
- Vietnamese answer rendering.
- product cards.
- Sidekick-style deterministic progress panel từ backend `progress_steps`.
- warnings display.
- debug panel với `job_id`.
- failed state display.

## Non-Goals

- Không marketing landing page.
- Không production auth.
- Không payment/subscription.
- Không advanced UI polish trước khi backend contracts hoạt động.
- Không direct scraping/model calls từ frontend.
- Không server-side product search trong frontend.

## Inputs From Previous Phases

Required:

- Phase 2 API contract.
- Phase 3/5 completed job result shape.
- `guides/architecture.md`.

Optional:

- Phase 7 có thể expand demo polish và tests về sau.

## Contracts

Frontend flow:

```text
user enters Vietnamese message
-> POST /api/chat-jobs
-> receive job_id
-> poll GET /api/chat-jobs/{job_id}
-> render pending/running/completed/failed
```

Các UI states bắt buộc:

- `idle`
- `submitting`
- `pending`
- `running`
- `completed`
- `failed`

Các components bắt buộc:

- `ChatPanel`
- `JobStatus`
- `ProgressSteps`
- `ProductResults`
- `ProductCard`
- `DebugLogPanel`

Product card fields:

```json
{
  "source": "Amazon",
  "title": "Example Laptop",
  "brand": "Example",
  "sale_price_usd": 699.99,
  "estimated_value_usd": 890.0,
  "discount_usd": 190.01,
  "deal_score": "good",
  "url": "https://www.amazon.com/..."
}
```

Polling:

- mỗi 1 giây khi `pending` hoặc `running`;
- dừng khi `completed` hoặc `failed`;
- hiển thị timeout/long wait warning nếu cần.

Progress panel:

- render `progress_steps` từ backend nếu response có field này;
- dùng Vietnamese titles/details từ backend, không tự bịa completed work;
- hiển thị `pending`, `running`, `completed`, `failed`, và `skipped`;
- nếu backend chưa trả `progress_steps`, frontend có thể dùng fallback status
  text đơn giản, nhưng không hardcode một completed plan.

Accessibility minimum:

- inputs có labels;
- buttons có readable text;
- status visible;
- product links mở an toàn.

## Workflow Gate

Trước khi code:

- Load `using-superpowers`.
- Dùng `brainstorming` với user.
- Chỉ hỏi các câu thay đổi scope, design, tests, hoặc implementation plan.
- Xác nhận frontend package/router choices trước khi scaffolding.
- Trình bày Phase 6 plan.
- Chờ explicit approval.

## Implementation Order

1. Xác nhận backend có thể return completed mock result.
2. Chọn App Router hoặc Pages Router rõ ràng.
3. Tạo frontend structure.
4. Define TypeScript types khớp API contract.
5. Implement API client.
6. Implement chat input và submit state.
7. Implement polling.
8. Implement status display.
9. Implement progress panel từ `progress_steps`.
10. Implement answer và product card rendering.
11. Implement warning và failed state display.
12. Thêm debug panel với `job_id`.
13. Thêm frontend smoke tests nếu project tooling hỗ trợ.
14. Viết Phase 6 report.

## Verification

Manual checks:

- User có thể submit Vietnamese query.
- UI nhận `job_id`.
- UI hiển thị `pending`/`running`.
- UI render completed Vietnamese answer.
- UI render progress steps từ backend và không claim completed work khi backend
  chưa gửi completed step.
- UI render product cards.
- Failed job render safe error.
- Debug `job_id` visible.

Commands depend on frontend tooling. Expected examples:

```bash
npm run lint
npm run test
npm run dev
```

Chỉ chạy dependency install hoặc package scripts sau khi user đã approve
frontend package setup.

## Report Requirements

Viết:

```text
shopping_assistant_v3/reports/phase_6_frontend_chat_report.md
```

Bao gồm:

- router choice: App Router hoặc Pages Router;
- files/components đã tạo;
- API contract assumptions;
- progress panel behavior;
- commands đã chạy;
- screenshot/manual validation notes nếu có;
- remaining UI risks.

## Risks And Open Questions

- UI visual style cố ý chưa được cố định.
- CORS có thể yêu cầu backend config updates.
- Product text có thể dài; card layout không được vỡ với long English titles.
- Debug panel hữu ích cho DATN demo nhưng không nên expose secrets hoặc stack
  traces.
