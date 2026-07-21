# Shopping Assistant V3 Project Status

## Mục Đích

File này là status ledger ngắn cho Shopping Assistant V3. Nó tracking phase
hoặc milestone mới nhất đã được approve mà không cần cập nhật `gameplan.md`
thường xuyên.

`gameplan.md` vẫn là source of truth cho product và architecture. File này là
source of truth cho current approved progress.

Chỉ Codex cập nhật file này, và chỉ sau khi approve một phase hoặc milestone.

## Trạng Thái Đã Approve Hiện Tại

Current approved milestone: Phase 5A Router And Synthesizer —
Deterministic Router/Synthesizer Path

Last approved commit:

```text
This commit: Approve shopping assistant v3 phase 5a deterministic router synthesizer
```

Approved report:

```text
shopping_assistant_v3/reports/phase_5a_router_and_synthesizer_report.md
```

Approved reviewer notes:

```text
shopping_assistant_v3/reports/phase_5a_router_and_synthesizer_codex_review.md
```

## Lịch Sử Approved

| Phase/Milestone | Status | Commit | Notes |
|---|---|---|---|
| Phase 1: Project Setup | approved | `3e37428` | Runtime skeleton, mock-safe env template, setup verification script, và Phase 1 report đã được approve. |
| Phase 2: Backend API And Database | approved | `b9f71d3` | FastAPI health/chat-job endpoints, SQLite schema initialization, repositories, safe error shape, và bộ 20 tests đã được approve. |
| Phase 3: Async Jobs | approved | `2fa46f3` | Local daemon-thread worker, async job lifecycle, mock completion, stale-running recovery, structured logs, agent_runs audit rows, và bộ 36 tests đã được approve. |
| Phase 4A: Mock Search/Pricing Tools | approved | this commit | Mock search/pricing tool contracts, JSON fixtures, product/price estimate persistence, worker pipeline wiring, tool/worker audit rows, safe real-mode failure gates, and 81 mock-only tests đã được approve. |
| Phase 4B: Real Amazon/BestBuy Search Extraction | approved | this commit | Opt-in real Amazon/BestBuy search extraction behind `ENABLE_REAL_SEARCH=true`, copy/adapt modules independent from `segment4`, local parser fixtures, bounded warnings, and default mock/fixture verification đã được approve. |
| Phase 4C.1: Real Price Estimator Extraction — Neural Adapter + Formatter + Boundary | approved | this commit | Deterministic formatter, copy/adapt neural DNN math, lazy neural adapter behind `ENABLE_REAL_MODEL_CALLS=true`, optional neural dependencies, fallback warnings, and `127 passed, 12 skipped` mock-only default verification đã được approve. |
| Phase 4C.2: Frontier Price Estimator Extraction — Frontier Adapter + Boundary | approved | this commit | Configurable ChromaDB path, lazy Frontier adapter with optional ChromaDB/SentenceTransformer/OpenAI deps, `frontier > neural > fallback` pricing priority, opt-in Frontier smoke tests, and `148 passed, 16 skipped` mock-only default verification đã được approve. |
| Phase 4C.3: Specialist Price Estimator Extraction — Specialist Adapter + Boundary | approved | this commit | Lazy Modal Specialist adapter behind `ENABLE_REAL_MODEL_CALLS=true`, optional `modal` dependency, full `frontier/specialist/neural` ensemble when all three are available, deterministic partial fallback priority, opt-in Specialist smoke tests, and `171 passed, 18 skipped` mock-only default verification đã được approve. |
| Phase 5A: Router And Synthesizer — Deterministic Path | approved | this commit | Deterministic Vietnamese Router, evidence-based Vietnamese Synthesizer, fixed `progress_steps`, API `summary_cards`, Router/Synthesizer audit rows, unsupported-intent fallback, and mock-only verification đã được approve. |

## Công Việc Tiếp Theo Được Phép

Next implementation milestone:

```text
Phase 5B: Optional OpenAI Agents SDK Router/Synthesizer Providers
```

Phase 5B may add optional OpenAI Agents SDK providers behind the same Router and
Synthesizer contracts created in Phase 5A. It must follow:

```text
shopping_assistant_v3/guides/5_router_and_synthesizer.md
```

Phase 5B requires separate brainstorming and explicit user approval before any
SDK implementation. Approved direction is hybrid controlled OpenAI Agents SDK
as an optional model-backed layer; deterministic Phase 5A must remain default
and default verification must remain mock-only unless the user opts into real
model tests.

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
