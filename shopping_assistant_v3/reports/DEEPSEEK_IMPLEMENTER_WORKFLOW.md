# DeepSeek Implementer Workflow

## Mục Đích

Dùng file này khi user giao session hiện tại cho DeepSeek hoặc một
implementation agent khác cho Shopping Assistant V3.

Implementer xây approved phase hoặc milestone, chạy verification, và viết
implementation report. Implementer không approve chính work của mình và không
commit hoặc push trừ khi Codex đã approve hành động đó.

## Context Bắt Buộc

Trước khi implement, đọc:

```text
shopping_assistant_v3/PROMPT_NEW_SESSION.md
shopping_assistant_v3/reports/DEEPSEEK_IMPLEMENTER_WORKFLOW.md
shopping_assistant_v3/reports/PROJECT_STATUS.md
shopping_assistant_v3/gameplan.md
shopping_assistant_v3/guides/architecture.md
shopping_assistant_v3/guides/agent_architecture.md
shopping_assistant_v3/reports/README.md
shopping_assistant_v3/reports/TEMPLATE_IMPLEMENTATION_REPORT.md
the relevant phase guide
relevant Codex review feedback, if resubmitting fixes
.claude/skills/karpathy-guidelines/SKILL.md
```

Cũng chạy:

```bash
git status --short
```

Giữ nguyên unrelated changes. Không reset, delete, stage, commit, push, hoặc
overwrite files ngoài approved scope.

## Responsibilities

Implementer phải:

- chỉ implement user-approved phase hoặc milestone scope;
- tuân theo current phase guide và V3 architecture contracts;
- áp dụng `karpathy-guidelines` để giữ assumptions rõ ràng, code đơn giản,
  surgical, và success criteria có thể verify;
- dùng mocks và fixtures theo mặc định;
- chạy smallest relevant verification trước;
- thực hiện self-check về security, data safety, reliability, và performance
  trước khi hand work cho Codex;
- viết hoặc cập nhật report riêng của implementer trong
  `shopping_assistant_v3/reports/`;
- phản hồi Codex feedback bằng cách sửa code/docs và report riêng của
  implementer khi cần.

Implementer không được:

- sửa Codex review files;
- cập nhật `PROJECT_STATUS.md`;
- cập nhật `gameplan.md` cho routine status;
- commit hoặc push nếu không có Codex approval;
- modify `segment4/` hoặc `shopping_assistant_v2/` trừ khi được explicitly
  approved;
- chạy live Amazon/BestBuy scraping, paid model calls, AWS/Terraform/deploy
  commands, hoặc dependency installs nếu không có explicit approval;
- đọc hoặc in secrets từ `.env`, credentials, keys, tokens, auth files, hoặc
  `terraform.tfvars`.

## Quy Tắc Implementation Report

Sau mỗi approved phase hoặc milestone, viết implementer report bằng:

```text
shopping_assistant_v3/reports/TEMPLATE_IMPLEMENTATION_REPORT.md
```

Ví dụ naming:

```text
shopping_assistant_v3/reports/phase_2_backend_api_and_database_report.md
shopping_assistant_v3/reports/phase_4a_mock_tools_report.md
```

Report phải nêu:

- exact scope đã implement;
- files created;
- files modified;
- commands run;
- tests run;
- verification evidence;
- known issues;
- deviations from the guide;
- liệu có real network, scraping, model, deploy, hoặc secret access nào xảy ra
  hay không.

## Self-Check Bắt Buộc Trước Handoff

Trước khi nói một phase hoặc milestone đã sẵn sàng cho Codex review,
implementer phải check changed scope về:

- security: không có secrets nào bị đọc, in, log, commit, hoặc expose qua API
  responses; không có live scraping, paid model calls, AWS/Terraform/deploy,
  hoặc new network access nào xảy ra trừ khi user explicitly approved;
- data safety: persisted payloads, result payloads, URLs, user messages,
  tool/model errors, và internal exceptions chỉ được lưu và trả về ở intentional
  safe forms; user/API-visible errors được sanitized;
- reliability: job/status transitions không thể bị stuck trong approved flow;
  idempotency và failure paths được test; audit/log records có `job_id` ở nơi
  guides yêu cầu;
- performance: implementation không thêm obvious avoidable slowness, unbounded
  work, uncontrolled threads, repeated expensive calls, hoặc polling loops nếu
  không document local-MVP limitation và risk;
- tests: default tests dùng mocks/fixtures và không yêu cầu secrets, live
  scraping, paid model calls, AWS, Terraform, deployment, hoặc external
  services.

Implementer report phải bao gồm ghi chú ngắn cho self-check này. Nếu một risk
được chấp nhận như local-MVP behavior, liệt kê nó dưới `Known Issues` với
severity và giải thích vì sao nó không block current phase.

## Phản Hồi Codex Feedback

Khi Codex viết review file:

1. Đọc Codex review file.
2. Sửa mọi `blocker` và `major` finding trừ khi user explicitly changes scope.
3. Sửa `minor` findings khi chúng cheap và local.
4. Cập nhật report của implementer với:
   - những gì đã thay đổi sau review;
   - commands/tests mới đã chạy;
   - remaining known issues.
5. Không sửa Codex review file.
6. Hand work lại cho Codex để review lần nữa.

## Quy Tắc Commit Và Push

Implementer có thể inspect git status nhưng mặc định không được commit hoặc
push.

Nếu commit hoặc push có vẻ cần thiết, dừng lại và yêu cầu user để Codex review
và approve hành động đó.
