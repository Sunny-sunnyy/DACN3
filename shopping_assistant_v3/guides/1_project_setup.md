# Phase 1: Project Setup

## Mục Đích

Chuẩn bị V3 runtime structure và local development assumptions mà chưa xây
user-facing functionality.

Phase này tồn tại để các coding agents sau này bắt đầu từ một cấu trúc sạch
thay vì tái tạo documentation rải rác và boundaries chưa rõ của V2.

## Trạng Thái Hiện Tại

Phase 1 đã được implement và approve. V3 hiện chứa documentation source of
truth cộng với runtime skeleton folders:

```text
shopping_assistant_v3/
├── README.md
├── .env.example
├── backend/
│   ├── README.md
│   ├── shared/
│   ├── database/
│   ├── api/
│   ├── router/
│   ├── tools/
│   └── synthesizer/
├── frontend/
│   └── README.md
├── gameplan.md
├── guides/
├── reports/
└── scripts/
    ├── README.md
    └── verify_setup.sh
```

Chưa có runtime backend API, database schema, worker, tool, hoặc frontend UI
code nào được implement. Phase 2 là implementation phase tiếp theo.

## Scope

Phase 1 có thể tạo:

- runtime folder skeletons cho `backend/`, `frontend/`, và `scripts/`;
- minimal README files cho runtime folders;
- local environment documentation;
- project-level ignore/config files chỉ khi cần và được approve;
- setup verification command không gọi network/model/scraping APIs.

Phase 1 phải xác nhận:

- Python commands dùng `uv`;
- backend sẽ là FastAPI;
- frontend sẽ là Next.js;
- local persistence sẽ là SQLite;
- default mode sẽ là mock/fixture;
- `segment4/` chỉ là reference;
- `shopping_assistant_v2/` chỉ là reference.

## Non-Goals

- Không backend API endpoints.
- Không database schema implementation.
- Không worker.
- Không tool implementation.
- Không frontend UI.
- Không dependency installation trừ khi được explicitly approved.
- Không live scraping hoặc paid model calls.
- Không modification `segment4/` hoặc `shopping_assistant_v2/`.

## Inputs From Previous Phases

Required reading:

- `shopping_assistant_v3/gameplan.md`
- `shopping_assistant_v3/guides/architecture.md`
- `shopping_assistant_v3/guides/agent_architecture.md`

Không cần implementation phase trước đó.

## Contracts

Target runtime structure:

```text
shopping_assistant_v3/
├── backend/
│   ├── README.md
│   ├── shared/
│   ├── database/
│   ├── api/
│   ├── router/
│   ├── tools/
│   │   ├── deal_search/
│   │   └── price_estimator/
│   └── synthesizer/
├── frontend/
│   └── README.md
├── scripts/
├── guides/
└── reports/
```

Nếu implementation agent muốn runtime layout khác, agent phải brainstorm với
user và cập nhật guide này sau approval.

## Workflow Gate

Trước khi code:

- Load `using-superpowers`.
- Dùng `brainstorming` với user.
- Chỉ hỏi các câu thay đổi scope, design, tests, hoặc implementation plan.
- Trình bày Phase 1 plan.
- Chờ explicit approval.

## Implementation Order

1. Xác nhận `git status --short` và giữ nguyên existing changes.
2. Đọc required V3 docs.
3. Brainstorm Phase 1 scope với user.
4. Chỉ tạo approved runtime folders và minimal documentation.
5. Document local commands và assumptions.
6. Tránh runtime feature implementation.
7. Viết Phase 1 implementation report.

## Verification

Minimum verification:

```bash
find shopping_assistant_v3 -maxdepth 3 -type f -print | sort
git status --short
```

Nếu runtime folders được tạo, verify rằng:

- không file nào dưới `segment4/` thay đổi;
- không file nào dưới `shopping_assistant_v2/` thay đổi;
- không secrets nào bị đọc hoặc in;
- không network/model/scraping commands nào được chạy.

## Report Requirements

Viết:

```text
shopping_assistant_v3/reports/phase_1_project_setup_report.md
```

Report phải liệt kê:

- folders/files đã tạo;
- bất kỳ docs nào đã cập nhật;
- commands đã chạy;
- dependencies có được install hay không;
- V2 hoặc `segment4` có được giữ nguyên hay không;
- remaining setup risks.

## Risks And Open Questions

- Frontend package manager chưa được cố định bởi guide này. Việc tạo Next.js có
  thể dùng npm, pnpm, hoặc tool khác chỉ sau user approval.
- Python dependency layout chưa được cố định. Các backend phases sau nên chọn
  minimal project structure hoạt động với `uv`.
- Tạo quá nhiều scaffolding trong Phase 1 có thể overfit architecture trước khi
  API/database contracts được implement.
