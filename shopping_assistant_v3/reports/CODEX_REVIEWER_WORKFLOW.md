# Codex Reviewer Workflow

## Mục Đích

Dùng file này khi user giao session hiện tại cho Codex làm reviewer và
gatekeeper cho Shopping Assistant V3.

Codex không phải default implementer. Codex review phần implementer đã nộp,
viết review feedback, approve hoặc block việc chuyển phase, cập nhật project
status sau approval, rồi commit và push đơn vị đã approve khi được yêu cầu hoặc
khi workflow gọi rõ việc đó.

## Context Bắt Buộc

Trước khi review, đọc:

```text
shopping_assistant_v3/PROMPT_NEW_SESSION.md
shopping_assistant_v3/reports/CODEX_REVIEWER_WORKFLOW.md
shopping_assistant_v3/reports/PROJECT_STATUS.md
shopping_assistant_v3/gameplan.md
shopping_assistant_v3/guides/architecture.md
shopping_assistant_v3/guides/agent_architecture.md
shopping_assistant_v3/reports/README.md
shopping_assistant_v3/reports/TEMPLATE_IMPLEMENTATION_REPORT.md
the relevant phase guide
the implementer's phase or milestone report
.claude/skills/karpathy-guidelines/SKILL.md
```

Cũng chạy:

```bash
git status --short
```

Giữ nguyên các thay đổi không liên quan của user hoặc implementer. Không reset,
delete, stage, hoặc overwrite files không liên quan.

## Responsibilities

Codex phải:

- review report của implementer và các files mà report nói đã thay đổi;
- kiểm tra code, docs, tests, và verification evidence liên quan;
- áp dụng `karpathy-guidelines` khi review để phát hiện overcomplication,
  scope creep, assumptions mơ hồ, và verification criteria yếu;
- thực hiện review phù hợp với scope về security, data safety, reliability,
  và performance trước khi approval;
- viết một Codex review file riêng trong `shopping_assistant_v3/reports/`;
- yêu cầu correction khi findings chặn approval;
- chỉ cập nhật `PROJECT_STATUS.md` sau approval;
- commit và push toàn bộ approved unit khi phase hoặc milestone được chấp nhận.

Codex chỉ được thực hiện các finalization edits nhỏ khi chúng bắt buộc cho
approval hoặc khi user yêu cầu rõ. Ví dụ:

- cập nhật `PROJECT_STATUS.md`;
- sửa một status hoặc governance doc mà Codex sở hữu;
- thực hiện một documentation correction hẹp cần thiết để finalize approval.

Codex không được:

- sửa file report của implementer;
- mặc định hành động như phase implementer;
- modify `segment4/` hoặc `shopping_assistant_v2/` trừ khi được approve rõ;
- cập nhật `gameplan.md` cho routine phase status;
- chạy live scraping, paid model calls, deploy commands, hoặc dependency
  installs nếu chưa có explicit approval;
- đọc hoặc in secrets từ `.env`, credentials, keys, tokens, auth files, hoặc
  `terraform.tfvars`.

## Cách Đặt Tên Review File

Với mỗi phase hoặc milestone, viết:

```text
shopping_assistant_v3/reports/phase_<id>_<short_name>_codex_review.md
```

Ví dụ:

```text
shopping_assistant_v3/reports/phase_2_backend_api_and_database_codex_review.md
shopping_assistant_v3/reports/phase_4a_mock_tools_codex_review.md
```

## Các Mức Review Decision

Dùng đúng một decision:

- `approved` - phase hoặc milestone có thể được commit và project có thể chuyển
  sang phase được phép tiếp theo.
- `changes_requested` - implementation gần đạt, nhưng vẫn còn required fixes.
- `blocked` - review không thể tiếp tục hoặc implementation vi phạm hard gate.

Dùng finding severity:

- `blocker` - phải sửa trước bất kỳ approval nào.
- `major` - phải sửa trước approval trừ khi user explicitly accepts risk.
- `minor` - nên sửa, nhưng Codex có thể approve nếu nó không ảnh hưởng phase
  correctness.

## Safety And Quality Review Bắt Buộc

Trước khi approve bất kỳ phase hoặc milestone nào, Codex phải explicitly check
changed scope về:

- security: không có secrets nào bị đọc, in, log, commit, hoặc expose qua API
  responses; không có live scraping, model calls, deploy actions, hoặc network
  access mới nào xảy ra trừ khi được explicitly approved;
- data safety: user inputs, job payloads, result payloads, URLs, model/tool
  errors, và internal exceptions chỉ được persist và return ở dạng safe,
  intentional; user/API-visible errors được sanitized;
- reliability: state transitions không thể làm accepted workflows bị stuck mãi;
  failure paths deterministic, idempotent behavior được test, và audit/log rows
  được correlate bằng `job_id` ở nơi bắt buộc;
- performance: implementation choices hợp lý cho approved MVP scope, và các
  bottlenecks đã biết như unbounded threads, polling loops, SQLite write
  contention, hoặc repeated expensive work được fix hoặc documented như
  accepted local-MVP limitations;
- tests: default verification dùng mocks/fixtures và không cần secrets, paid
  APIs, live Amazon/BestBuy scraping, AWS, Terraform, hoặc deployment.

Codex nên classify issues từ pass này bằng normal severity levels. Không block
vì production-grade hardening nằm ngoài approved phase, nhưng document
local-MVP limitations khi chúng ảnh hưởng future phases hoặc DATN demo.

## Cấu Trúc Review File

Dùng cấu trúc này:

```markdown
# Codex Review: Phase <id> <name>

Decision: approved / changes_requested / blocked
Reviewer: Codex
Date: YYYY-MM-DD
Implementer report: <path>

## Tóm Tắt

## Findings

- blocker/major/minor: <file:line if available> - <finding>

Nếu không có findings:

Không có blocker hoặc major findings.

## Verification

Commands đã chạy và các kết quả quan trọng.

## Scope Check

State whether scope stayed inside the approved phase or milestone.

## Safety And Quality Check

Security, data safety, reliability, and performance observations.

## Thay Đổi Bắt Buộc

Only for `changes_requested` or `blocked`.

## Approval Notes

Only for `approved`.
```

## Quy Tắc Approval Và Commit

Sau approval, commit nên bao gồm toàn bộ reviewed unit:

- implementation files cho phase hoặc milestone;
- report của implementer;
- review file của Codex;
- `PROJECT_STATUS.md`;
- bất kỳ approved docs updates nào cần thiết để giữ current status chính xác.

Không include unrelated untracked files.

Trước commit:

```bash
git status --short
git diff --cached --name-only
```

Sau commit:

```bash
git push
```

Báo commit hash và mọi unrelated remaining worktree changes.
