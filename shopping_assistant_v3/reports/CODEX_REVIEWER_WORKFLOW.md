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
codegraph status shopping_assistant_v3
```

Giữ nguyên các thay đổi không liên quan của user hoặc implementer. Không reset,
delete, stage, hoặc overwrite files không liên quan.

## CodeGraph Cho V3

`shopping_assistant_v3/` đã có local CodeGraph index. Index nằm trong
`.codegraph/`, là generated local artifact, và không được stage hoặc commit.

Trước mỗi review, Codex phải chạy:

```bash
codegraph status shopping_assistant_v3
```

Mục đích:

- xác nhận CodeGraph đã initialized cho `shopping_assistant_v3/`;
- xác nhận index đang `up to date`;
- nắm nhanh số files/nodes/edges hiện tại nếu cần so với changed scope;
- phát hiện tình huống index stale hoặc thiếu sau một phase/guide.

Nếu status báo index up to date, không cần làm gì thêm. CodeGraph có auto-sync
theo file changes trong điều kiện bình thường.

Nếu status báo stale hoặc thiếu symbols cần cho review, chạy sync hẹp:

```bash
codegraph sync shopping_assistant_v3
```

Không chạy `codegraph init`, `codegraph uninit`, hoặc xóa `.codegraph/` trừ khi
user explicitly approve. Nếu CodeGraph lỗi hoặc không initialized, báo trong
review notes và tiếp tục review bằng `rg`/file reads khi cần.

### Cách Sử Dụng CodeGraph Khi Review

Ưu tiên MCP `codegraph_explore` khi tool có sẵn, vì nó trả về source liên quan,
call paths, và blast radius trong một lần hỏi. Luôn truyền `projectPath` để
tránh query nhầm repo:

```text
projectPath: /home/hieu0606sunny/price2026wsl/tech2ai/shopping_assistant_v3
query: "How does POST /api/chat-jobs create a job and start worker processing?"
```

Các review prompts hữu ích:

```text
How does POST /api/chat-jobs create a job and start worker processing?
How does process_job update job status, result payload, and agent_runs?
What code is affected if JobResponse or ChatJobCreate changes?
How do repository functions persist jobs, products, and agent run audit rows?
```

Nếu MCP không có sẵn, dùng CLI từ repo root:

```bash
codegraph explore -p shopping_assistant_v3 "How does POST /api/chat-jobs create a job and start worker processing?"
codegraph query -p shopping_assistant_v3 "process_job"
codegraph impact -p shopping_assistant_v3 "process_job"
codegraph affected -p shopping_assistant_v3 shopping_assistant_v3/backend/worker.py
```

Cách chọn lệnh:

- `explore`: dùng đầu tiên cho architecture/call-flow/review context.
- `query`: tìm symbol hoặc file khi đã biết tên gần đúng.
- `impact`: kiểm tra blast radius khi một schema/function/shared helper đổi.
- `affected`: gợi ý tests liên quan tới files đã thay đổi; vẫn phải dùng
  judgment, không thay thế phase guide hoặc report evidence.

Không paste raw CodeGraph output dài vào review file. Chỉ ghi command/question
đã dùng và kết luận quan trọng trong phần `Verification` hoặc `Scope Check`.

Khi review code runtime phức tạp, Codex nên dùng CodeGraph nếu nó giúp giảm
guesswork, đặc biệt cho:

- API route -> worker -> repository flow;
- database schema/repository impact;
- future router/tool/synthesizer call flow;
- blast radius của thay đổi shared schemas hoặc shared config.

Sau mỗi phase hoặc guide update có thay đổi runtime đáng kể, Codex nên kiểm tra
lại `codegraph status shopping_assistant_v3`. Nếu auto-sync đã cập nhật và
status up to date thì không chạy sync thủ công.

## Human-Assisted Tasks

Nếu `CODEX_REVIEWER` hoặc `DEEPSEEK_IMPLEMENTER` không thể tự thực hiện một tác
vụ cụ thể vì giới hạn sandbox, quyền truy cập, môi trường local, browser UI, tài
khoản, hoặc secret handling, agent phải yêu cầu user hỗ trợ thay vì đoán hoặc
bỏ qua âm thầm.

Các ví dụ gồm:

- tạo, migrate, seed, hoặc kiểm tra database mà agent không truy cập được;
- duyệt một website cụ thể, thao tác tab cụ thể, mở DevTools/F12, hoặc lấy HTML
  mà browser/tooling của agent không thể lấy đúng;
- cài browser extension, package hệ thống, app desktop, hoặc công cụ local nằm
  ngoài quyền của agent;
- cấu hình service/account, lấy API key/env key, hoặc xác nhận secret tồn tại;
- thực hiện thao tác trên máy tính/trang web mà agent không thể tự làm an toàn
  hoặc không có quyền.

Khi cần user hỗ trợ, agent phải hỏi rõ:

- mục tiêu của thao tác;
- các bước user cần làm;
- output hoặc evidence cần gửi lại;
- dữ liệu nào không được paste trực tiếp, đặc biệt là secrets, tokens, private
  keys, credentials, hoặc nội dung nhạy cảm.

Nếu cần secret/env key, agent không được yêu cầu user paste secret vào chat.
Thay vào đó, yêu cầu user tự đặt vào file/env phù hợp trên máy local hoặc gửi
evidence đã redact, ví dụ tên biến đã tồn tại, status command, hoặc error message
đã ẩn giá trị secret.

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

## User-Facing Reports

Sau khi một phase, milestone, hoặc guide thay đổi thực tế project được approve,
Codex phải kiểm tra và cập nhật báo cáo dễ đọc cho user trong:

```text
shopping_assistant_v3/reports/user_reports/
```

Mục đích của các file này là giúp project owner hiểu hệ thống đang có gì mà
không phải đọc toàn bộ implementation reports kỹ thuật.

Quy tắc:

- Mỗi completed phase hoặc milestone có một file riêng:
  `phase_<id>_user_report.md`.
- Nếu phase có sub-milestone, dùng id rõ ràng, ví dụ
  `phase_4c1_user_report.md`.
- `README.md` trong `user_reports/` phải phản ánh current approved milestone,
  thứ tự đọc, và milestone tiếp theo.
- Mỗi report nên dưới 500 dòng.
- Viết bằng tiếng Việt dễ hiểu; technical terms giữ English khi rõ hơn.
- Không copy nguyên implementation report. Tóm tắt lại thành: mục tiêu, vấn đề
  phase giải quyết, chức năng đã có, kỹ thuật dùng, luồng hoạt động, file quan
  trọng và quan hệ giữa chúng, cách tự kiểm tra, giới hạn hiện tại, và phase
  sau nối tiếp.
- Không claim functionality chưa được implementation và verification chứng
  minh.
- Khi guide thay đổi product/architecture behavior dài hạn, cập nhật
  `README.md` hoặc phase report liên quan nếu user-facing understanding bị
  stale.

## User-Facing Notebooks

Khi user-facing runnable docs thay đổi, Codex cũng phải kiểm tra notebook
companion trong:

```text
shopping_assistant_v3/reports/notebooks/
```

Mục đích của notebooks là giúp project owner chạy và hiểu từng approved phase
trên current codebase, không phải tạo historical checkout theo từng phase
commit.

Quy tắc review notebook:

- Notebook phải là companion cho approved user report hoặc approved phase.
- Notebook outputs phải để trống trong repo; expected output ghi trong Markdown
  cell.
- Default executable cells không được gọi live Amazon/BestBuy scraping, OpenAI,
  Modal, AWS, Terraform, deploy, hoặc secrets.
- Opt-in real-mode cells phải có guard rõ bằng env flags/config và không chạy
  khi user chỉ chạy default notebook.
- Không lưu API keys, tokens, private paths nhạy cảm, raw headers, raw HTML lớn,
  raw model payloads, hoặc stack traces chứa sensitive data.
- Commands trong notebook phải dùng `uv run` cho Python project commands.
- Notebook phải chạy trên current approved codebase và ghi rõ nếu output có thể
  khác historical phase snapshot.
- Reviewer nên validate notebook JSON parse được, `execution_count` là `null`,
  `outputs` rỗng, và safety guards còn tồn tại trước approval.

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
