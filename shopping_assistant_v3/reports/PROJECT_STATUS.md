# Shopping Assistant V3 Project Status

## Mục Đích

File này là status ledger ngắn cho Shopping Assistant V3. Nó tracking phase
hoặc milestone mới nhất đã được approve mà không cần cập nhật `gameplan.md`
thường xuyên.

`gameplan.md` vẫn là source of truth cho product và architecture. File này là
source of truth cho current approved progress.

Chỉ Codex cập nhật file này, và chỉ sau khi approve một phase hoặc milestone.

## Trạng Thái Đã Approve Hiện Tại

Current approved milestone: Phase 4B Real Amazon/BestBuy Search Extraction

Last approved commit:

```text
This commit: Approve shopping assistant v3 phase 4b real search
```

Approved report:

```text
shopping_assistant_v3/reports/phase_4b_real_search_report.md
```

Approved reviewer notes:

```text
shopping_assistant_v3/reports/phase_4b_real_search_codex_review.md
```

## Lịch Sử Approved

| Phase/Milestone | Status | Commit | Notes |
|---|---|---|---|
| Phase 1: Project Setup | approved | `3e37428` | Runtime skeleton, mock-safe env template, setup verification script, và Phase 1 report đã được approve. |
| Phase 2: Backend API And Database | approved | `b9f71d3` | FastAPI health/chat-job endpoints, SQLite schema initialization, repositories, safe error shape, và bộ 20 tests đã được approve. |
| Phase 3: Async Jobs | approved | `2fa46f3` | Local daemon-thread worker, async job lifecycle, mock completion, stale-running recovery, structured logs, agent_runs audit rows, và bộ 36 tests đã được approve. |
| Phase 4A: Mock Search/Pricing Tools | approved | this commit | Mock search/pricing tool contracts, JSON fixtures, product/price estimate persistence, worker pipeline wiring, tool/worker audit rows, safe real-mode failure gates, and 81 mock-only tests đã được approve. |
| Phase 4B: Real Amazon/BestBuy Search Extraction | approved | this commit | Opt-in real Amazon/BestBuy search extraction behind `ENABLE_REAL_SEARCH=true`, copy/adapt modules independent from `segment4`, local parser fixtures, bounded warnings, and default mock/fixture verification đã được approve. |

## Công Việc Tiếp Theo Được Phép

Next implementation phase:

```text
Phase 4C: Real Price Estimator Extraction
```

Phase 4C must start from the approved Phase 4A mock tool foundation and Phase
4B opt-in real search modules, and follow:

```text
shopping_assistant_v3/guides/4_search_and_pricing_tools.md
```

Phase 4C requires separate brainstorming and explicit user approval before any
real pricing/model extraction work. Default verification must remain mock-only
unless the user opts into real model tests.

## Open Blockers

Không có approved blockers.

## Ghi Chú Worktree Đã Biết

Tại thời điểm status file này được tạo, các untracked files sau nằm ngoài
approved phase flow của Shopping Assistant V3 và nên được giữ nguyên trừ khi
user explicitly scope chúng:

```text
shopping_assistant_v2/README_Project_Sidekick.md
shopping_assistant_v2/README_codegraph.md
```

## Quy Tắc Cập Nhật Status

- DeepSeek hoặc bất kỳ implementer nào không được cập nhật file này.
- Codex chỉ cập nhật file này sau khi approve một phase hoặc milestone.
- Routine progress nên được ghi ở đây, không ghi trong `gameplan.md`.
- `gameplan.md` chỉ nên thay đổi khi product direction, architecture, phase
  contracts, hoặc long-lived project guidance thay đổi.
