# Prompt cho session mới: áp dụng Alex production architecture vào DATN theo từng phase nhỏ

Bạn là coding agent trong một session mới. Bạn đang làm việc trong folder chính của dự án DATN, nơi sẽ chứa toàn bộ code production của DATN. Nhiệm vụ của bạn không phải là implement toàn bộ một lần. Nhiệm vụ của bạn là đọc kỹ tài liệu chuyển giao từ Alex, thảo luận với tôi bằng `brainstorming`, chia nhỏ thành phases, tạo plans/specs trước, rồi chỉ implement từng bước nhỏ khi đã được xác nhận.

Ngôn ngữ giao tiếp: tiếng Việt. Giữ technical terms bằng English khi rõ hơn.

---

## 0. Quy trình skill bắt buộc

Bạn hãy dùng `brainstorming` làm quy trình chính để cùng tôi thảo luận, hỏi thêm, làm rõ yêu cầu.

- Luôn bắt đầu bằng `using-superpowers`.
- Dùng `brainstorming` làm quy trình chính.
- Chỉ dùng `rich-elicitation` nếu vẫn còn từ 2 chiều mơ hồ quan trọng trở lên, và mỗi chiều có từ 3 hướng hợp lý.
- Hãy hỏi cho tới khi bạn nắm đầy đủ hết ngữ cảnh và yêu cầu của người dùng.
- Ưu tiên câu hỏi multiple-choice có recommended option.
- Không hỏi lan man. Mỗi câu hỏi phải làm thay đổi scope, design, test, hoặc implementation plan.
- Đừng bắt đầu viết code cho đến khi chúng ta đã thống nhất yêu cầu.

Phải ưu tiên sử dụng `using-superpowers` và các skill liên quan trong `superpowers` khi phù hợp với tác vụ.

Core workflow skills:

- `using-superpowers` - Bootstrap skill usage and workflow selection
- `brainstorming` - Socratic design refinement
- `writing-plans` - Detailed implementation plans
- `executing-plans` - Batch execution with checkpoints
- `dispatching-parallel-agents` - Concurrent subagent workflows
- `subagent-driven-development` - Fast iteration with two-stage review
- `using-git-worktrees` - Parallel development branches
- `finishing-a-development-branch` - Merge/PR decision workflow

Quality and validation skills:

- `test-driven-development` - RED-GREEN-REFACTOR cycle
- `systematic-debugging` - Root-cause debugging workflow
- `requesting-code-review` - Pre-review checklist
- `receiving-code-review` - Responding to feedback
- `verification-before-completion` - Final verification before completion

Nếu skill instructions yêu cầu viết design/spec trước, hãy làm đúng. Nếu có xung đột với yêu cầu của tôi, nêu xung đột ngắn gọn và hỏi hướng xử lý.

---

## 1. Context quan trọng

Tôi đã có tài liệu chuyển giao lớn từ repo Alex:

```text
ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md
```

File này mô tả toàn bộ những gì Alex đã triển khai:

- backend,
- frontend,
- FastAPI,
- Next.js,
- AWS architecture,
- CloudFront,
- API Gateway,
- S3,
- S3 Vectors,
- SageMaker embeddings,
- ECR,
- Lambda,
- SQS,
- Aurora Serverless v2,
- Clerk JWT auth,
- CORS,
- API rate limiting,
- async job orchestration bằng `job_id`,
- Lambda handlers,
- Planner/specialist agents,
- retry with exponential backoff,
- guardrails,
- output validation,
- logging,
- CloudWatch,
- LangFuse/OpenAI Agents traces,
- audit logging,
- Terraform chia nhỏ theo folder,
- guides end-to-end,
- enterprise techniques theo `guides/8_enterprise.md`,
- mapping sang DATN.

DATN hiện tại là project đồ án tốt nghiệp về shopping/product/price assistant, dùng các ý tưởng như:

- product search,
- product comparison,
- fair price / deal detection,
- RAG,
- scraping/crawling nguồn thương mại điện tử,
- Qwen/vLLM/fine-tuned models,
- hybrid architecture: AWS control plane + GPU ngoài AWS.

Mục tiêu dài hạn: biến DATN thành một production-grade app học theo Alex, nhưng không copy domain finance. Chỉ copy patterns production.

---

## 2. Việc đầu tiên phải làm trong session mới

Trước khi code, deploy, cài dependency, chạy Terraform, chạy AWS, hoặc chỉnh kiến trúc lớn:

1. Chạy:

```bash
git status --short
```

2. Không reset, stage, commit, xóa, hoặc ghi đè thay đổi có sẵn.

3. Kiểm tra tài liệu tồn tại:

```text
ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md
```

Nếu file nằm trong folder con, hãy tìm bằng `rg --files`.

4. Đọc file này theo từng phần, không cố implement toàn bộ một lần.

5. Nếu còn 3 file DATN gốc thì đọc thêm:

```text
Project_Development_Plan.md
DOCUMENTATION_SEARCHKEY.md
DOCUMENTATION_PRICE_IS_RIGHT.md
```

Nếu chúng nằm trong folder khác, hãy tìm bằng `rg --files`.

6. Không đọc hoặc in secrets:

- `.env`
- `terraform.tfvars`
- credentials files
- API keys
- tokens
- private keys
- secret files

Chỉ được nói rằng secret/config file tồn tại nếu cần.

---

## 3. CodeGraph bắt buộc kiểm tra

Tôi nhớ dự án có thể có `.codegraph`. Nếu chưa có thì chúng ta sẽ tạo, nhưng vẫn phải kiểm tra trước.

Hãy chạy:

```bash
codegraph status .
```

Nếu index hợp lệ và up-to-date:

- Dùng CodeGraph cho câu hỏi về code structure, symbols, request flow, dependency, callers/callees, impact.
- Không đọc tuần tự toàn bộ source chỉ để hiểu repo.

Nếu MCP CodeGraph tool chưa xuất hiện trong session:

- Dùng CLI fallback:

```bash
codegraph explore "<câu hỏi cụ thể>"
```

- Báo rõ rằng cần mở session mới hoặc reload MCP nếu muốn dùng MCP tool.

Nếu `.codegraph/` thiếu hoặc index lỗi:

1. Báo rõ tình trạng.
2. Đề xuất lệnh:

```bash
codegraph init .
```

3. Nếu session permissions cho phép và tôi xác nhận, hãy chạy để tạo index.
4. Sau khi tạo index, dùng CodeGraph trước khi đọc thủ công code structure.

Lưu ý: CodeGraph chỉ dùng cho quan hệ code tĩnh. Nó không thay thế việc đọc:

- README,
- guides,
- Terraform configs,
- AWS state,
- CloudWatch logs,
- runtime behavior.

---

## 4. Không được làm ngay

Không làm các việc sau trong lượt đầu tiên:

- Không implement toàn bộ DATN.
- Không chạy `terraform apply`.
- Không deploy AWS.
- Không push.
- Không commit nếu tôi chưa yêu cầu.
- Không cài dependency mới nếu chưa thống nhất.
- Không build Docker image nếu chưa cần.
- Không gọi external GPU provider.
- Không gọi model API tốn phí.
- Không tự ý tạo secrets.
- Không copy domain finance của Alex vào DATN.

Nếu cần làm một trong các việc trên, hãy dừng và hỏi tôi.

---

## 5. Cách đọc `ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md`

File transfer rất lớn. Không thực hiện một lần. Hãy đọc và xử lý theo chunks:

### Chunk A: Context và Alex source of truth

Đọc các phần:

- mục tiêu tài liệu,
- DATN hiện tại,
- Alex source of truth,
- repo structure,
- AWS infra overview.

Kết quả mong muốn:

- Tóm tắt Alex đã triển khai gì.
- Tóm tắt DATN đang thiếu gì.
- Không code.

### Chunk B: Backend/API/Frontend/Agents

Đọc các phần:

- backend/API pattern,
- frontend pattern,
- agent architecture,
- async job flow,
- `job_id` lifecycle.

Kết quả mong muốn:

- Đề xuất DATN backend folder split.
- Đề xuất DATN API contract sơ bộ.
- Đề xuất DATN agent list.
- Không code nếu chưa thống nhất.

### Chunk C: AWS/Terraform/Deployment

Đọc các phần:

- Terraform folder split,
- packaging/deploy workflow,
- AWS services,
- hybrid AWS + external GPU model service.

Kết quả mong muốn:

- Đề xuất DATN `terraform/` structure.
- Nêu thứ tự deploy từng folder.
- Nêu stop-gates trước AWS.

### Chunk D: Enterprise/Security/Observability

Đọc các phần:

- auth,
- authorization,
- CORS,
- rate limiting,
- anti-spam,
- retry/backoff,
- guardrails,
- output validation,
- logging,
- LangFuse/OpenAI traces,
- CloudWatch,
- audit,
- Guide 8 mapping.

Kết quả mong muốn:

- Checklist enterprise cho DATN.
- Phân loại: MVP required, next phase, optional enterprise.

### Chunk E: Plans/specs/guides implementation instructions

Đọc các phần:

- DATN production scaffold spec,
- plans/specs,
- guides spec,
- implementation plan,
- coding agent execution instructions,
- section bổ sung về `job_id`.

Kết quả mong muốn:

- Đề xuất phase đầu tiên cụ thể.
- Xin xác nhận trước khi tạo file.

---

## 6. Brainstorming trước khi implement

Sau khi đọc context, hãy dùng `brainstorming` để hỏi tôi từng câu một.

Không hỏi lan man. Mỗi câu hỏi phải ảnh hưởng đến scope/design/test/implementation.

Câu hỏi đầu tiên nên là multiple-choice:

```text
Bạn muốn session này thực hiện phase nào trước?

1. Docs/plans/specs scaffold only (Recommended)
   Tạo plans/, specs/, guides/ và viết tài liệu triển khai trước. Chưa code runtime, chưa Terraform apply.

2. Repo scaffold gồm docs + backend/terraform/frontend skeleton
   Tạo cấu trúc folder và file README/skeleton. Chưa deploy AWS.

3. MVP vertical slice đầu tiên
   Bắt đầu implement FastAPI + job_id + SQS + DB skeleton, nhưng cần thống nhất kỹ hơn trước.
```

Recommended option là `1. Docs/plans/specs scaffold only`.

Nếu tôi chọn option 1, hãy tạo tài liệu trước, chưa code runtime.

Nếu tôi chọn option 2, hãy tạo skeleton nhưng vẫn chưa deploy.

Nếu tôi chọn option 3, phải dùng `writing-plans` trước khi code.

---

## 7. 3 hướng kiến trúc phải trình bày khi cần quyết định lớn

Khi bàn về architecture hoặc algorithms, hãy luôn đưa 3 options:

1. Modern/SOTA:
   - Hybrid AWS control plane + external GPU Qwen/vLLM.
   - Full observability, queue-based agents, RAG, external model gateway.

2. Safe/stable:
   - AWS serverless core.
   - External model gọi qua OpenAI-compatible API.
   - Scraping hạn chế, dataset seed trước.

3. MVP/simple:
   - Next.js + FastAPI + DB + one queue + one worker.
   - Mock/deterministic model trước.
   - Chưa scraper thật, chưa Qwen thật.

Hãy recommend option an toàn nhất cho đồ án: bắt đầu MVP/simple nhưng thiết kế folder/infra đủ để mở rộng sang hybrid/SOTA.

---

## 8. Kiến trúc DATN target phải giữ trong đầu

Target architecture sơ bộ:

```text
CloudFront
  -> S3 static Next.js frontend
  -> /api/* to API Gateway
  -> FastAPI Lambda
  -> Clerk JWT verification
  -> Aurora Serverless v2 Data API
  -> SQS jobs
  -> Router Lambda
  -> Specialist Lambdas
       - searcher
       - scraper
       - comparer
       - pricer
       - advisor
       - synthesizer
  -> S3 Vectors for product knowledge RAG
  -> external GPU model service for Qwen/vLLM/fine-tuned models
  -> CloudWatch + LangFuse/OpenAI traces
```

Không implement tất cả cùng lúc.

Vertical slice đầu tiên nên là:

```text
User logs in
  -> submits product search
  -> API creates job_id
  -> API sends SQS message
  -> Router/Searcher worker processes by job_id
  -> DB stores status/result
  -> Frontend polls by job_id
  -> User sees result
```

---

## 9. Folder structure DATN cần hướng tới

Nếu chưa có, hãy đề xuất tạo:

```text
plans/
specs/
guides/
backend/
frontend/
terraform/
scripts/
```

Trong `terraform/`, chia nhỏ như Alex:

```text
terraform/
├── README.md
├── 1_foundation/
├── 2_database/
├── 3_vector_store/
├── 4_ingest/
├── 5_agents/
├── 6_frontend_api/
├── 7_model_services/
└── 8_enterprise/
```

Trong `backend/`, chia nhỏ như:

```text
backend/
├── README.md
├── shared/
├── database/
├── api/
├── ingest/
├── router/
├── searcher/
├── scraper/
├── comparer/
├── pricer/
├── advisor/
└── synthesizer/
```

Trong `guides/`, tạo end-to-end guides:

```text
guides/
├── 1_foundation.md
├── 2_database.md
├── 3_backend_api.md
├── 4_vector_ingest.md
├── 5_agents.md
├── 6_frontend.md
├── 7_model_services.md
├── 8_enterprise.md
├── architecture.md
└── agent_architecture.md
```

Trong `plans/` và `specs/`, tạo trước khi code:

```text
plans/
├── 00_context.md
├── 01_mvp_scope.md
├── 02_aws_architecture.md
├── 03_backend_architecture.md
├── 04_frontend_architecture.md
├── 05_agent_architecture.md
├── 06_security_enterprise.md
└── 07_deployment_plan.md

specs/
├── repo_structure.md
├── api_contract.md
├── database_schema.md
├── job_orchestration.md
├── vector_ingest.md
├── model_gateway.md
├── frontend_pages.md
├── observability.md
└── security.md
```

---

## 10. `job_id` async orchestration là bắt buộc

DATN phải có backbone này, học từ Alex:

```text
API creates job
  -> SQS message contains job_id
  -> Router Lambda processes by job_id
  -> Specialist Lambda processes by job_id
  -> DB stores status/result by job_id
  -> Frontend polls by job_id
  -> Logs/traces/audit correlate by job_id
```

Không được thiết kế long-running request kiểu frontend chờ API cho tới khi scraper/model xong.

Specs bắt buộc:

- `specs/job_orchestration.md`
- `specs/api_contract.md`
- `specs/database_schema.md`
- `specs/observability.md`

Acceptance criteria đầu tiên:

- API tạo job và trả `job_id`.
- DB có job row.
- SQS message có `job_id`.
- Worker xử lý theo `job_id`.
- Status chuyển `pending/running/completed/failed`.
- Frontend poll theo `job_id`.
- Logs filter được theo `job_id`.

---

## 11. Enterprise techniques bắt buộc đưa vào plans/specs

Khi tạo plans/specs, phải đưa vào:

- Clerk JWT authentication.
- Per-user authorization.
- CORS.
- API Gateway throttling.
- App-level rate limiting nếu cần.
- Anti-spam API policy.
- Input Validation Guardrails.
- Prompt injection detection.
- Agent Output Validation.
- Retry Logic with Exponential Backoff.
- DLQ.
- Idempotency.
- Structured logging.
- CloudWatch Logs Insights by `job_id`.
- CloudWatch dashboards.
- CloudWatch alarms.
- LangFuse traces.
- OpenAI Agents traces.
- Audit logging.
- Secrets Manager.
- IAM least privilege.
- Cost monitoring.
- External GPU model timeout/fallback.
- Safe scraping policy.

Hãy phân loại từng mục:

```text
MVP required
Next phase
Optional enterprise
```

Không claim đã implement nếu mới chỉ là planned.

---

## 12. Phase plan bắt buộc

Không làm toàn bộ trong một lần. Hãy đề xuất theo phases:

### Phase 0: Context load

- Git status.
- CodeGraph status.
- Read transfer manual.
- Read DATN docs.
- Summarize findings.
- No code.

### Phase 1: Docs/plans/specs scaffold

- Create/update `plans/`.
- Create/update `specs/`.
- Create/update initial `guides/architecture.md`.
- No runtime code.
- No AWS.

### Phase 2: Local App Foundation

- Mục tiêu: chuyển DATN từ Gradio prototype sang app local production-style.
- Tạo hoặc chuẩn hóa local Next.js frontend.
- Tạo hoặc chuẩn hóa local FastAPI backend.
- Thiết kế API contract tối thiểu.
- Implement local `job_id` lifecycle.
- Dùng local/mock worker hoặc FastAPI background task thay SQS ở phase local.
- Thêm structured console logs ở backend.
- Thêm status/log panel trong frontend để quan sát job.
- Chưa AWS.
- Chưa Terraform apply.
- Chưa Lambda/SQS/Aurora.
- Chưa external GPU/model API tốn phí.

Verify:

- User nhập product query trên frontend.
- Frontend gọi FastAPI `POST /api/search-jobs`.
- Backend trả `job_id`.
- Frontend poll `GET /api/search-jobs/{job_id}`.
- Backend logs hiển thị ở console.
- UI hiển thị status/logs/result.
- Worker trả mock/deterministic result trước, chưa cần model thật.

### Phase 3: Repo skeleton for AWS production

- Create `backend/`, `terraform/`, `frontend/`, `scripts/`.
- Add READMEs and skeleton files only.
- No AWS deploy.

### Phase 4: API + DB vertical slice

- FastAPI health.
- Clerk auth.
- DB schema.
- Job create/status endpoints.
- No real model/scraper yet.

### Phase 5: SQS + one worker

- SQS queue.
- Router/searcher worker.
- `job_id` lifecycle.
- Mock/deterministic result first.

### Phase 6: Next.js frontend AWS MVP

- Clerk login.
- Search form.
- Job polling.
- Results page.

### Phase 7: RAG/vector ingest

- S3 Vectors or chosen vector store.
- Ingest small dataset.
- Search product knowledge.

### Phase 8: External GPU model service

- Qwen/vLLM OpenAI-compatible endpoint.
- Secrets.
- Timeout/retry/fallback.

### Phase 9: Enterprise hardening

- Dashboards.
- Alarms.
- Rate limiting.
- Guardrails.
- Audit.
- Traces.
- Cost controls.

Mỗi phase phải có:

- Goal.
- Files changed.
- Verification.
- Stop condition.
- Next action.

---

## 13. Expected first response của agent

Sau khi đọc prompt này, agent không được bắt đầu code ngay.

Expected response đầu tiên nên có:

```text
Tôi sẽ bắt đầu bằng using-superpowers và brainstorming.
Tôi sẽ kiểm tra git status, CodeGraph status, rồi đọc ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md theo chunks.
Tôi sẽ không code/deploy/Terraform cho tới khi phase đầu tiên được xác nhận.
```

Sau khi kiểm tra context, agent nên hỏi câu multiple-choice:

```text
Bạn muốn tôi thực hiện phase nào trước?

1. Docs/plans/specs scaffold only (Recommended)
2. Repo scaffold docs + backend/terraform/frontend skeleton
3. MVP vertical slice đầu tiên
```

Nếu tôi chọn option 1, hãy thực hiện Phase 1 và dừng sau khi tạo docs/plans/specs.

---

## 14. Definition of done cho session đầu tiên

Session đầu tiên được coi là thành công nếu:

- Không làm AWS deploy.
- Không chạy Terraform apply.
- Không cài dependency ngoài ý muốn.
- Không đọc/in secrets.
- Đã kiểm tra git status.
- Đã kiểm tra CodeGraph.
- Đã đọc transfer manual.
- Đã tạo hoặc cập nhật plans/specs/guides theo phase được chọn.
- Đã chia nhỏ các bước tiếp theo.
- Đã ghi rõ stop-gates cho coding agent session sau.

Nếu chọn Phase 1, deliverables recommended:

```text
plans/00_context.md
plans/01_mvp_scope.md
plans/02_aws_architecture.md
specs/repo_structure.md
specs/job_orchestration.md
specs/api_contract.md
specs/database_schema.md
specs/security.md
specs/observability.md
guides/architecture.md
guides/agent_architecture.md
```

Nếu chọn Phase 2, deliverables recommended:

```text
frontend/
backend/api/
specs/api_contract.md
specs/job_orchestration.md
guides/local_development.md
```

Phase 2 chỉ cần chạy local:

```text
Next.js frontend
  -> FastAPI backend
  -> local job store hoặc in-memory store
  -> local/mock worker
  -> frontend polling
  -> console logs + UI logs
```

Không dùng AWS ở Phase 2. Mục tiêu là thấy app thật chạy local thay cho Gradio trước khi chuyển sang AWS.

Không cần hoàn hảo 100% trong lần đầu, nhưng phải đủ rõ để session sau implement theo từng guide.

---

## 15. Nhắc lại mục tiêu

Đây là đồ án tốt nghiệp quan trọng. Ưu tiên:

- đúng architecture,
- chia nhỏ dễ debug,
- production patterns rõ,
- có docs/guides để người khác đọc được,
- có async job tracking theo `job_id`,
- có auth/security/enterprise concerns,
- có deployment plan an toàn,
- không over-engineer trước khi có vertical slice chạy được.

Không được biến `ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md` thành một checklist implement ồ ạt. Hãy dùng nó như blueprint, rồi triển khai DATN theo từng phase nhỏ có xác nhận.
