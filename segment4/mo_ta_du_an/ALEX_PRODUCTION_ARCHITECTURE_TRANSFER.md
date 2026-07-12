# Alex Production Architecture Transfer for DATN

**Ngày tạo:** 2026-07-10
**Mục đích:** Tài liệu handoff cho coding agent ở session mới.
**Phạm vi:** Trích xuất kiến trúc, kỹ thuật production, enterprise patterns, deploy workflow và bài học từ project Alex để brainstorm áp dụng vào DATN.
**Trạng thái:** Chỉ là tài liệu tham chiếu và đề xuất sơ bộ. Không phải implementation plan cuối cùng.

---

## 0. Cách dùng tài liệu này trong session mới

Coding agent mới nên đọc theo thứ tự:

1. `DATN/ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md` file này.
2. `DATN/Project_Development_Plan.md`.
3. `DATN/DOCUMENTATION_SEARCHKEY.md`.
4. `DATN/DOCUMENTATION_PRICE_IS_RIGHT.md`.
5. Các README và guide của Alex khi cần xác minh chi tiết:
   - `gameplan.md`
   - `guides/architecture.md`
   - `guides/agent_architecture.md`
   - `guides/1_permissions.md` đến `guides/8_enterprise.md`
   - `backend/*/README.md`
   - `frontend/README.md`
   - `terraform/*/README.md`
   - `README_about_enterprise.md`
   - `Update_for_8_enterprise.md`

Nguyên tắc khi dùng tài liệu này:

- Không copy nguyên domain tài chính của Alex sang DATN. Chỉ tái sử dụng kiến trúc, workflow, kỹ thuật production và enterprise patterns.
- Không đọc, in, tóm tắt hoặc commit secret từ `.env`, `terraform.tfvars`, API keys, credentials, token hoặc ARN nhạy cảm.
- DATN hiện là shopping assistant tiếng Việt, chưa phải financial advisor. Mọi mapping phải đổi sang domain sản phẩm, giá, scraping, so sánh, tư vấn mua sắm.
- Đây chưa phải implementation plan. Sau khi đọc tài liệu này, nên tiếp tục brainstorming để chốt MVP DATN trước khi viết code.

---

## 1. DATN hiện tại đang có gì

### 1.1. Ba file chính trong `DATN/`

| File | Vai trò hiện tại | Nội dung chính |
|---|---|---|
| `DATN/Project_Development_Plan.md` | Kế hoạch tổng thể đồ án tốt nghiệp | Trợ lý mua sắm tiếng Việt, multi-agent, Qwen/vLLM, RAG, scraping sàn TMĐT Việt Nam, ensemble ML định giá. |
| `DATN/DOCUMENTATION_SEARCHKEY.md` | Tài liệu pipeline search theo keyword | Gradio app local, multi-source deal finder, BestBuy/Amazon, scraper song song, GPT chọn top deals, ensemble pricing. |
| `DATN/DOCUMENTATION_PRICE_IS_RIGHT.md` | Tài liệu autonomous deal hunter gốc | RSS DealNews, autonomous planning agent, ChromaDB, Pushover, ensemble pricing, Gradio dashboard. |

### 1.2. DATN đang thiếu gì nếu muốn deploy production lên AWS

DATN hiện mô tả tốt local prototype và kế hoạch nghiên cứu, nhưng chưa có các lớp production giống Alex:

- Chưa có Next.js frontend production.
- Chưa có FastAPI backend production.
- Chưa có authentication bằng Clerk/JWT.
- Chưa có user/account/session/conversation database production.
- Chưa có async job orchestration bằng SQS.
- Chưa có Lambda agents tách folder/package/deploy.
- Chưa có Terraform chia theo từng phần.
- Chưa có CloudFront/S3 frontend hosting.
- Chưa có API Gateway public API với CORS/rate limiting.
- Chưa có Aurora Serverless v2 hoặc schema production.
- Chưa có S3 Vectors hoặc vector store production trên AWS.
- Chưa có ECR/container deployment cho service nặng.
- Chưa có enterprise monitoring/observability như CloudWatch dashboard, structured logs, LangFuse/OpenAI traces.
- Chưa có guardrails chung cho input/output của agents.

### 1.3. DATN nên học gì từ Alex

Alex không chỉ là source code; Alex là một blueprint production:

- Cách chia repo thành `backend`, `frontend`, `terraform`, `scripts`, `guides`.
- Cách tách mỗi service/agent thành folder độc lập có `README.md`, `pyproject.toml`, `lambda_handler.py`, `agent.py`, `templates.py`, `test_simple.py`, `test_full.py`, `package_docker.py`.
- Cách deploy từng guide/tầng hạ tầng độc lập bằng Terraform local state.
- Cách nối frontend → API → SQS → Planner → specialist agents → database.
- Cách làm auth, CORS, rate limiting, async job tracking, logging, tracing, retries, guardrails, audit.
- Cách vận hành với AWS nhưng vẫn giữ model lớn bên ngoài nếu GPU AWS quá đắt.

---

## 2. Source of truth trong Alex

Khi có mâu thuẫn giữa guide cũ và code hiện tại, ưu tiên theo thứ tự:

1. Code và Terraform hiện tại.
2. README hiện tại trong từng folder.
3. `Update_for_8_enterprise.md`.
4. `README_about_enterprise.md`.
5. `gameplan.md`.
6. Guide gốc trong `guides/`.

Các mâu thuẫn quan trọng đã biết:

| Chủ đề | Guide cũ nói | Implementation hiện tại |
|---|---|---|
| Researcher runtime | App Runner | Lambda container image + public Function URL |
| Researcher model | Bedrock/Nova/OSS | OpenAI models qua LiteLLM, mặc định `openai/gpt-5.4-nano` |
| Agent orchestra models | Bedrock Nova Pro | OpenAI qua LiteLLM với `MODEL_ID_<AGENT>` |
| Agent IAM | Có Bedrock policy | Bedrock IAM đã bị xóa ở Part 6 |
| Scheduler | 2 giờ | 12 giờ trong Terraform/README hiện tại |
| Enterprise dashboard | Bedrock model metrics | Part 6 hiện dùng OpenAI, nên Bedrock widgets không đại diện agent inference |
| Guide 8 | Nhiều nội dung là đề xuất | Repo hiện có một phần code-level enterprise features và dashboard; WAF/GuardDuty/VPC endpoints/alarms chưa triển khai |

---

## 3. Repo structure của Alex cần học theo

### 3.1. Cấu trúc cấp cao

```text
alex/
├── backend/
│   ├── api/
│   ├── database/
│   ├── ingest/
│   ├── researcher/
│   ├── planner/
│   ├── tagger/
│   ├── reporter/
│   ├── charter/
│   ├── retirement/
│   └── shared/
├── frontend/
├── terraform/
│   ├── 2_sagemaker/
│   ├── 3_ingestion/
│   ├── 4_researcher/
│   ├── 5_database/
│   ├── 6_agents/
│   ├── 7_frontend/
│   └── 8_enterprise/
├── scripts/
├── guides/
└── DATN/
```

### 3.2. Pattern chia folder nên áp dụng cho DATN

DATN nên tiến tới cấu trúc tương tự:

```text
DATN_APP/
├── backend/
│   ├── api/                  # FastAPI + Mangum/Lambda hoặc container API
│   ├── database/             # Shared Aurora/Data API hoặc Postgres access layer
│   ├── shared/               # guardrails, audit, logging, common schemas
│   ├── router/               # Router Agent: intent classification
│   ├── searcher/             # Search Agent: tìm sản phẩm
│   ├── scraper/              # Scraper workers/tools
│   ├── comparer/             # Compare Agent: so sánh giá nhiều nguồn
│   ├── pricer/               # Price Estimator Agent: ensemble/DNN/model service bridge
│   ├── advisor/              # Advisor Agent: tư vấn sản phẩm
│   ├── synthesizer/          # Response Synthesizer: trả lời tiếng Việt tự nhiên
│   └── ingest/               # Product/research/vector ingest pipeline
├── frontend/                 # Next.js app mới cho DATN
├── terraform/
│   ├── 1_foundation/
│   ├── 2_database/
│   ├── 3_vector_store/
│   ├── 4_model_services/
│   ├── 5_agents/
│   ├── 6_frontend_api/
│   └── 7_monitoring/
├── scripts/
└── docs/
```

Không nhất thiết phải tạo ngay toàn bộ. Đây là target structure để agent mới brainstorm MVP.

---

## 4. AWS infrastructure đã triển khai trong Alex

### 4.1. Tổng quan hạ tầng

```text
User Browser
  |
  v
CloudFront
  |-- static frontend -> S3 frontend bucket
  |-- /api/*          -> API Gateway HTTP API
                         |
                         v
                       Lambda alex-api (FastAPI + Mangum)
                         |
                         |-- Aurora Data API (CRUD + jobs)
                         |-- SQS alex-analysis-jobs
                                  |
                                  v
                                Lambda alex-planner
                                  |
                                  |-- alex-tagger
                                  |-- alex-reporter
                                  |-- alex-charter
                                  |-- alex-retirement
                                  |
                                  v
                                Aurora jobs payloads

Researcher flow:
Researcher Lambda container + Function URL
  -> Ingest API Gateway REST API + API key
  -> Lambda alex-ingest
  -> SageMaker embedding endpoint
  -> S3 Vectors financial-research index
```

### 4.2. Terraform Part 2: SageMaker embedding endpoint

**Folder:** `terraform/2_sagemaker`
**Backend code liên quan:** `backend/ingest`, `backend/reporter`
**Mục đích:** Tạo embedding 384 chiều cho semantic search/RAG.

Resources chính:

- IAM role `alex-sagemaker-role`.
- SageMaker model `alex-embedding-model`.
- HuggingFace model `sentence-transformers/all-MiniLM-L6-v2`.
- Serverless endpoint config.
- Endpoint `alex-embedding-endpoint`.

Kỹ thuật đáng chú ý:

- Serverless endpoint scale-to-zero.
- HuggingFace inference container tự tải model.
- `time_sleep` để chờ IAM propagation.
- Endpoint name được truyền sang Part 3 và reporter.

DATN mapping:

- Với tiếng Việt, DATN nên cân nhắc embedding model tốt hơn `all-MiniLM-L6-v2`, ví dụ `multilingual-e5-base`, `bge-m3`, hoặc model embedding tiếng Việt.
- Nếu dùng S3 Vectors production, vẫn cần endpoint embedding hoặc external embedding service.
- Nếu dùng ChromaDB local-first, pattern embedding vẫn áp dụng nhưng không cần SageMaker ở giai đoạn đầu.

### 4.3. Terraform Part 3: S3 Vectors + ingest API

**Folder:** `terraform/3_ingestion`
**Backend code:** `backend/ingest`
**Mục đích:** Nhận text, tạo embedding, ghi vào S3 Vectors.

Resources chính:

- S3 vector bucket `alex-vectors-<account_id>`.
- Lambda `alex-ingest`.
- API Gateway REST API `alex-api` với `POST /ingest`.
- API key `alex-api-key`.
- Usage plan `alex-usage-plan`.
- IAM role cho Lambda ingest.
- CloudWatch log group `/aws/lambda/alex-ingest`.

Kỹ thuật enterprise:

- API key bắt buộc cho ingest endpoint.
- Usage plan quota 10,000 requests/month.
- Throttle rate 100 requests/second, burst 200.
- S3 public access block.
- IAM least privilege cho SageMaker invoke và S3 Vectors actions.
- CloudWatch log retention 7 ngày.

DATN mapping:

- DATN có thể dùng ingest pipeline cho:
  - product descriptions,
  - product specs,
  - scraped product snapshots,
  - shopping knowledge documents,
  - user query/result history nếu cần RAG.
- Ingest API nên không public rộng; cần API key hoặc internal-only path.
- Với scraping, nên lưu metadata: source, product_url, platform, category, price, timestamp, crawl_status, confidence.

### 4.4. Terraform Part 4: Researcher Lambda container + ECR

**Folder:** `terraform/4_researcher`
**Backend code:** `backend/researcher`
**Mục đích:** Chạy autonomous researcher bằng browser/MCP, lưu research vào S3 Vectors.

Resources chính:

- ECR repository `alex-researcher`.
- ECR repository policy cho Lambda pull image.
- IAM role `alex-researcher-lambda-role`.
- Lambda `alex-researcher` package type Image.
- Lambda Function URL public HTTPS.
- Optional scheduler Lambda `alex-researcher-scheduler`.
- EventBridge Scheduler `rate(12 hours)`.

Runtime hiện tại:

- FastAPI app trong container.
- Lambda Web Adapter.
- Playwright MCP + Chromium headless.
- OpenAI Agents SDK + LiteLLM.
- Model mặc định `openai/gpt-5.4-nano`.
- Verified-web-only contract.
- Immediate snapshot strategy.

Kỹ thuật enterprise:

- Container image cho workload nặng hơn zip Lambda.
- ECR deploy flow.
- Function URL để test trực tiếp.
- Structured CloudWatch logs với `research_run`, `research_ingest`, `run_id`, phase status.
- Browser verification gate: không ingest nếu không có nguồn web thật.
- Fail closed: trả 500 khi không xác minh được web content.

DATN mapping:

- DATN scraper/research service có thể học pattern này nhưng cần cẩn thận:
  - Scraping TMĐT có thể cần proxy, session/cookie, anti-bot logic.
  - Browser-heavy scraping trong Lambda có giới hạn timeout/cold start.
  - Với Shopee/Lazada/Tiki, có thể tốt hơn dùng container service riêng hoặc GPU/VPS worker ngoài AWS, còn AWS Lambda chỉ orchestrate.
- Verified-source contract rất phù hợp DATN:
  - Chỉ lưu giá/sản phẩm nếu có URL nguồn rõ ràng.
  - Reject fallback/general knowledge khi tác vụ yêu cầu dữ liệu web thật.

### 4.5. Terraform Part 5: Aurora Serverless v2 + Data API

**Folder:** `terraform/5_database`
**Backend code:** `backend/database`
**Mục đích:** Relational core cho user, account, position, job lifecycle.

Resources chính:

- Aurora PostgreSQL cluster `alex-aurora-cluster`.
- Aurora Serverless v2 instance `db.serverless`.
- Data API enabled.
- Secrets Manager secret cho DB credentials.
- Default VPC/subnets/subnet group/security group.
- IAM role/policy cho Lambda-style Data API access.

Schema Alex:

- `users`
- `instruments`
- `accounts`
- `positions`
- `jobs`

Kỹ thuật enterprise:

- Data API giúp Lambda không cần TCP connection pool.
- Secrets Manager không hard-code credentials.
- JSONB payloads cho agent outputs.
- User data tách theo `clerk_user_id`.
- Job state rõ: `pending`, `running`, `completed`, `failed`.

DATN mapping:

DATN nên dùng relational core tương tự:

- `users`: map từ Clerk user id.
- `conversations`: lưu chat sessions.
- `messages`: lưu history nếu cần.
- `products`: canonical product records.
- `product_sources`: mỗi nguồn/sàn một record giá/url/timestamp.
- `search_jobs`: async search requests.
- `scrape_jobs`: crawl/scrape tasks.
- `price_estimates`: kết quả ensemble pricing.
- `comparison_results`: bảng so sánh giá.
- `agent_runs`: audit từng agent/model/tool call.
- `notifications`: nếu có push/email later.

Không nên lưu mọi thứ vào vector DB. Vector store dùng để search semantic; Aurora dùng cho state, user data, audit, results.

### 4.6. Terraform Part 6: SQS + 5 Lambda agents

**Folder:** `terraform/6_agents`
**Backend code:** `backend/planner`, `backend/tagger`, `backend/reporter`, `backend/charter`, `backend/retirement`
**Mục đích:** Agent orchestra.

Resources chính:

- SQS queue `alex-analysis-jobs`.
- DLQ `alex-analysis-jobs-dlq`.
- Shared IAM role `alex-lambda-agents-role`.
- S3 bucket `alex-lambda-packages-<account_id>` cho zip lớn.
- 5 Lambda functions:
  - `alex-planner`
  - `alex-tagger`
  - `alex-reporter`
  - `alex-charter`
  - `alex-retirement`
- Event source mapping SQS → planner.
- CloudWatch log groups.

Runtime hiện tại:

- Tất cả model calls qua OpenAI API bằng LiteLLM.
- `OPENAI_API_KEY` bắt buộc.
- `MODEL_ID_<AGENT>` riêng cho từng Lambda.
- Bedrock IAM đã bị xóa ở Part 6.

Model mapping live từ `Update_for_8_enterprise.md`:

| Agent | Model | Env var |
|---|---|---|
| Planner | `openai/gpt-5.4-mini` | `MODEL_ID_PLANNER` |
| Tagger | `openai/gpt-5.4-nano` | `MODEL_ID_TAGGER` |
| Reporter | `openai/gpt-5.4-mini` | `MODEL_ID_REPORTER` |
| Charter | `openai/gpt-4.1-nano` | `MODEL_ID_CHARTER` |
| Retirement | `openai/gpt-5.4-nano` | `MODEL_ID_RETIREMENT` |
| Judge | `openai/gpt-5.4-nano` | `MODEL_ID_JUDGE` |

Kỹ thuật enterprise:

- Async queue decouples API request from long-running AI work.
- DLQ cho failed messages.
- Planner timeout lớn hơn specialists.
- Specialist agents ghi payload riêng vào DB.
- Model id/timing trả về trong response body.
- Structured logs và audit events.

DATN mapping:

DATN nên có queue/job system tương tự:

- API nhận user request → tạo job → gửi SQS.
- Router/Planner Lambda nhận job.
- Planner gọi specialist agents hoặc external GPU/model endpoints.
- Mỗi agent ghi kết quả vào payload riêng:
  - search results,
  - scrape results,
  - price estimates,
  - compare table,
  - final answer,
  - errors,
  - audit/timing.

Không nên để frontend chờ trực tiếp một request scrape/model lâu. Frontend nên poll job status hoặc dùng SSE/WebSocket later.

### 4.7. Terraform Part 7: Frontend + API Gateway + FastAPI Lambda

**Folder:** `terraform/7_frontend`
**Frontend:** `frontend`
**Backend:** `backend/api`
**Mục đích:** Production web app.

Resources chính:

- S3 bucket `alex-frontend-<account_id>`.
- S3 website configuration.
- Public bucket policy.
- CloudFront distribution.
- Ordered cache behavior `/api/*` → API Gateway.
- API Gateway HTTP API `alex-api-gateway`.
- Lambda `alex-api`.
- IAM role/policies:
  - Aurora Data API,
  - Secrets Manager,
  - SQS SendMessage,
  - optional Lambda invoke.

Kỹ thuật enterprise:

- Static frontend served by CloudFront.
- API Gateway stage throttle `100/100`.
- FastAPI handles Clerk JWT verification.
- CloudFront caches static assets; `/api/*` has TTL 0.
- SPA fallback 403/404 → `index.html`.

DATN mapping:

- DATN chưa có Next.js. Nên xây luôn frontend mới:
  - Next.js frontend static export hoặc server mode tùy nhu cầu.
  - Clerk login/signup.
  - Chat assistant page.
  - Product search page.
  - Product compare page.
  - Price estimation/job history page.
  - Admin/debug-lite page nếu cần cho demo.
- Production nên route:
  - `/` static frontend,
  - `/api/*` FastAPI backend.

### 4.8. Terraform Part 8: Enterprise dashboards

**Folder:** `terraform/8_enterprise`
**Docs:** `README_about_enterprise.md`, `Update_for_8_enterprise.md`
**Mục đích:** Monitoring dashboard và enterprise evidence map.

Resources hiện có:

- CloudWatch dashboard `alex-ai-model-usage`.
- CloudWatch dashboard `alex-agent-performance`.

Giới hạn:

- Dashboard model usage còn Bedrock-oriented.
- Part 6 đang dùng OpenAI, nên cần dashboard mới nếu muốn theo dõi OpenAI cost/latency trực tiếp.
- Chưa có WAF, GuardDuty, VPC endpoints, SNS alarms hoặc metric alarms trong Terraform.

DATN mapping:

- Nên tạo dashboards:
  - API latency/errors.
  - SQS queue depth/DLQ.
  - Lambda duration/errors/throttles.
  - Aurora query/API errors.
  - scraper success/failure per source.
  - model endpoint latency/errors/cost.
  - job completion time.
- Nếu dùng LangFuse/OpenAI traces, CloudWatch dashboard không thay thế được trace-level observability.

---

## 5. Backend/API pattern từ Alex

### 5.1. `backend/api`

Alex API là FastAPI app chạy 2 chế độ:

- Local: `uv run main.py`.
- Production: Lambda + Mangum qua `lambda_handler.handler`.

Files chính:

| File | Vai trò |
|---|---|
| `backend/api/main.py` | FastAPI app, Clerk auth, CORS, CRUD routes, `/api/analyze`, SQS send. |
| `backend/api/lambda_handler.py` | Mangum entry point cho API Gateway. |
| `backend/api/package_docker.py` | Build `api_lambda.zip` bằng Docker Lambda Python 3.12. |
| `backend/api/pyproject.toml` | Dependencies FastAPI/Mangum/boto3/Clerk/db/shared. |

Routes chính trong Alex:

- `GET /health`
- `GET /api/user`
- `PUT /api/user`
- `GET /api/accounts`
- `POST /api/accounts`
- `PUT /api/accounts/{account_id}`
- `DELETE /api/accounts/{account_id}`
- `GET /api/accounts/{account_id}/positions`
- `POST /api/positions`
- `PUT /api/positions/{position_id}`
- `DELETE /api/positions/{position_id}`
- `GET /api/instruments`
- `POST /api/analyze`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs`
- `DELETE /api/reset-accounts`
- `POST /api/populate-test-data`

### 5.2. Auth bằng Clerk JWT

Alex dùng:

- Clerk ở frontend.
- Frontend lấy JWT.
- API nhận `Authorization: Bearer <token>`.
- `ClerkHTTPBearer` verify token qua `CLERK_JWKS_URL`.
- User identity lấy từ JWT `sub`.
- Database key là `clerk_user_id`.

DATN mapping:

- Dùng Clerk để tránh tự build auth/password.
- Bảng `users` chỉ lưu profile tối thiểu, không lưu password.
- Mọi dữ liệu user-owned phải filter bằng `clerk_user_id`:
  - conversations,
  - search jobs,
  - saved products,
  - comparison history,
  - notifications.

### 5.3. CORS pattern

Alex có 2 lớp CORS:

- API Gateway HTTP API CORS.
- FastAPI CORS middleware với `CORS_ORIGINS`.

Hiện trạng:

- API Gateway Part 7 còn rộng (`allow_origins = ["*"]`).
- FastAPI dùng `CORS_ORIGINS` cụ thể hơn.

DATN khuyến nghị:

- Local allow: `http://localhost:3000`.
- Production allow: CloudFront domain hoặc custom domain.
- Không dùng wildcard nếu gửi credentials/token.
- CORS config nên nằm trong Terraform/env, không hard-code trong code.

### 5.4. Async job pattern

`POST /api/analyze` trong Alex:

1. Verify user.
2. Create job row in Aurora.
3. Send message to SQS with `job_id`.
4. Return `job_id`.
5. Frontend polls `GET /api/jobs/{job_id}`.

DATN mapping:

Các request nên async:

- `POST /api/chat` nếu cần multi-step agent lâu.
- `POST /api/search` cho scraping/search sản phẩm.
- `POST /api/compare` cho so sánh nhiều sàn.
- `POST /api/estimate-price` cho ensemble/model inference lâu.
- `POST /api/scrape` cho admin/internal crawl.

Response nên trả:

```json
{
  "job_id": "...",
  "status": "pending",
  "message": "Job created. Poll status endpoint for results."
}
```

### 5.5. Error handling

Alex API có:

- Pydantic request/response models.
- Validation exception handler.
- HTTP exception handler.
- General exception handler.
- Friendly messages.
- Logging errors server-side.

DATN nên áp dụng:

- Không expose stack traces ra frontend.
- Log server-side có `request_id`, `user_id`, `job_id`.
- Response error nhất quán:

```json
{
  "detail": "Human-readable message",
  "error_code": "SEARCH_SOURCE_UNAVAILABLE",
  "job_id": "..."
}
```

---

## 6. Frontend pattern từ Alex và đề xuất Next.js cho DATN

### 6.1. Alex frontend hiện tại

**Folder:** `frontend`

Tech stack:

- Next.js 15.
- React 19.
- Pages Router.
- Static export.
- Clerk.
- Recharts.
- React Markdown.
- Tailwind CSS.

Files chính:

| File/folder | Vai trò |
|---|---|
| `frontend/pages/_app.tsx` | ClerkProvider, ErrorBoundary, ToastContainer. |
| `frontend/components/Layout.tsx` | Protected app shell, nav, footer. |
| `frontend/lib/config.ts` | Local vs production API base URL. |
| `frontend/lib/api.ts` | Typed API client with Bearer token. |
| `frontend/lib/events.ts` | Event bus for analysis lifecycle. |
| `frontend/pages/advisor-team.tsx` | Trigger analysis and poll job. |
| `frontend/pages/analysis.tsx` | Render report/charts/retirement. |

Production pattern:

- `next.config.ts` uses `output: 'export'`.
- Build output synced to S3.
- CloudFront serves static app.
- CloudFront routes `/api/*` to API Gateway.
- Client in production calls relative `/api/*`.
- Local dev calls `http://localhost:8000`.

### 6.2. DATN nên xây Next.js frontend mới

DATN hiện chưa có Next.js. Đề xuất sơ bộ:

```text
frontend/
├── pages/
│   ├── _app.tsx
│   ├── index.tsx
│   ├── dashboard.tsx
│   ├── chat.tsx
│   ├── search.tsx
│   ├── compare.tsx
│   ├── estimates.tsx
│   ├── history.tsx
│   └── admin.tsx
├── components/
│   ├── Layout.tsx
│   ├── ProductCard.tsx
│   ├── PriceComparisonTable.tsx
│   ├── ChatWindow.tsx
│   ├── JobProgress.tsx
│   ├── Toast.tsx
│   └── ConfirmModal.tsx
├── lib/
│   ├── api.ts
│   ├── config.ts
│   └── events.ts
└── styles/
```

Pages gợi ý:

| Page | Vai trò |
|---|---|
| `/` | Landing page tiếng Việt, login/signup. |
| `/dashboard` | Tổng quan user, search history, saved products. |
| `/chat` | Chatbot trợ lý mua sắm tiếng Việt. |
| `/search` | Tìm sản phẩm theo keyword/ngân sách/sàn. |
| `/compare` | So sánh giá sản phẩm giữa sàn. |
| `/estimates` | Lịch sử ước giá và confidence. |
| `/history` | Job history và kết quả cũ. |
| `/admin` | Debug/demo page: queues, sources, model status. |

### 6.3. Frontend job polling pattern

Alex `advisor-team.tsx`:

- gọi `POST /api/analyze`,
- nhận `job_id`,
- poll `GET /api/jobs/{job_id}` mỗi 2 giây,
- chuyển stage UI,
- redirect sang result page khi completed.

DATN nên dùng pattern tương tự:

- `POST /api/search` → `search_job_id`.
- Poll `GET /api/jobs/{job_id}`.
- UI stages:
  - queued,
  - scraping,
  - ranking,
  - pricing,
  - synthesizing,
  - completed,
  - failed.

Later có thể nâng cấp SSE/WebSocket, nhưng MVP polling đơn giản hơn.

---

## 7. Agent architecture pattern từ Alex

### 7.1. Alex agent folders

Mỗi agent Alex có cấu trúc tương tự:

```text
backend/<agent>/
├── agent.py
├── lambda_handler.py
├── templates.py
├── observability.py
├── package_docker.py
├── test_simple.py
├── test_full.py
├── pyproject.toml
└── uv.lock
```

Pattern này rất nên áp dụng cho DATN.

### 7.2. Planner + specialist pattern

Alex:

- Planner nhận job từ SQS.
- Planner làm preprocessing.
- Planner gọi specialist Lambdas qua tools:
  - reporter,
  - charter,
  - retirement.
- Tagger chạy trước nếu thiếu instrument metadata.
- Mỗi specialist ghi payload riêng vào DB.

DATN mapping:

```text
User request
  -> API creates job
  -> SQS
  -> Router/Planner Agent
       |-- Search Agent
       |-- Scraper Agent
       |-- Compare Agent
       |-- Price Estimator Agent
       |-- Advisor Agent
       |-- Synthesizer Agent
  -> Aurora job payloads
  -> Frontend polls and renders result
```

### 7.3. DATN agent roles sơ bộ

| DATN Agent | Học từ Alex agent | Vai trò |
|---|---|---|
| Router Agent | Planner/Tagger structured classification | Phân loại intent: hỏi đáp, tìm sản phẩm, so sánh, tư vấn, ước giá. |
| Search Agent | Reporter tool/RAG + planner tool pattern | Tìm sản phẩm từ vector store hoặc scrape pipeline. |
| Scraper Agent | Researcher verified-web-only + tools | Crawl/scrape nguồn TMĐT có xác minh URL/source. |
| Compare Agent | Charter payload pattern | Tạo bảng so sánh giá có schema rõ. |
| Price Estimator Agent | Retirement precompute + LLM explanation | Gọi ensemble/DNN/Qwen pricer, trả estimate/confidence. |
| Advisor Agent | Reporter narrative | Tư vấn sản phẩm bằng tiếng Việt có reasoning và nguồn. |
| Synthesizer Agent | Reporter final markdown | Tổng hợp câu trả lời cuối cùng tự nhiên, có dẫn nguồn. |

### 7.4. Structured outputs vs tools

Alex lesson:

- Một số agent dùng tools.
- Một số agent dùng structured output.
- Với LiteLLM/Bedrock từng có limitation tools + structured outputs không dùng chung ổn định trong một agent.
- Dù hiện dùng OpenAI, vẫn nên tách responsibility:
  - Router/Tagger: structured output.
  - Scraper/Search/Reporter: tools.
  - Compare/Chart: JSON output + validation.

DATN nên tránh một agent quá lớn vừa gọi nhiều tools vừa trả schema phức tạp. Tách nhỏ dễ debug hơn.

---

## 8. Hybrid AWS control plane + GPU ngoài AWS cho DATN

### 8.1. Vì sao không full AWS GPU

DATN có kế hoạch:

- Qwen2.5-7B-Instruct serve bằng vLLM.
- Qwen fine-tuned QLoRA.
- Qwen2.5-3B specialist.
- DNN PyTorch.
- Scraping nhiều sàn.

AWS GPU cho workload này có thể đắt và phức tạp cho đồ án. Kiến trúc hợp lý:

- AWS lo control plane, API, auth, jobs, database, static hosting, observability.
- GPU/model inference chạy ở Vast.ai, RunPod, Modal hoặc server GPU riêng.

### 8.2. Sơ bộ kiến trúc DATN

```text
Browser
  -> CloudFront
      |-- S3 Next.js static frontend
      |-- /api/* -> API Gateway -> FastAPI Lambda
                                      |
                                      |-- Clerk JWT verification
                                      |-- Aurora Data API
                                      |-- SQS jobs
                                      |-- S3/S3 Vectors
                                      |
                                      v
                                   Planner/Router Lambda
                                      |
                                      |-- lightweight Lambda agents
                                      |-- external GPU model endpoints
                                      |-- scraper/container workers
                                      |
                                      v
                                   Aurora job results

External GPU/model services:
  - Qwen/vLLM router/synthesizer endpoint
  - Fine-tuned Qwen pricer endpoint
  - Modal/Vast/RunPod specialist endpoint
  - Optional DNN inference service
```

### 8.3. Boundaries nên giữ rõ

AWS side:

- Auth.
- API boundary.
- Job state.
- User isolation.
- Async queues.
- Logging/audit.
- Static frontend.
- Result storage.
- Lightweight orchestration.

External GPU side:

- Model inference.
- vLLM serving.
- Fine-tuned adapters.
- Batch price estimation.
- Heavy embedding if not using SageMaker.

Scraping side:

- Nếu nhẹ: Lambda/container Lambda.
- Nếu nặng hoặc cần proxy/session: VPS/container worker ngoài AWS hoặc ECS/App Runner later.

---

## 9. Enterprise techniques từ Alex

### 9.1. Scalability

Alex đã áp dụng:

- CloudFront cho static frontend.
- API Gateway cho HTTP entry point.
- Lambda cho compute serverless.
- SQS decoupling giữa API và agents.
- DLQ cho message failures.
- Aurora Serverless v2.
- Data API để tránh connection pooling.
- S3 Vectors cho vector search managed.

DATN áp dụng:

- API không chạy trực tiếp scraping/model lâu.
- Long-running work phải qua SQS jobs.
- Mỗi job có status và payload rõ.
- Frontend poll status.
- Scrapers/model services scale độc lập.

### 9.2. Authentication

Alex:

- Clerk frontend.
- JWT Bearer token.
- JWKS verification trong FastAPI.
- `clerk_user_id` làm tenant/user key.

DATN:

- Dùng Clerk cho login/signup.
- Không tự lưu password.
- Mọi table user-owned có `clerk_user_id`.
- API endpoints phải verify JWT trước khi đọc/ghi job/conversation/history.

### 9.3. Authorization và tenant isolation

Alex pattern:

- API lấy `clerk_user_id` từ token.
- Query jobs/accounts theo user.
- Không tin user id từ body nếu có token.

DATN:

- `GET /api/jobs/{job_id}` phải kiểm tra job thuộc user hiện tại.
- `GET /api/conversations/{id}` phải kiểm tra owner.
- Saved products/search history phải filter theo `clerk_user_id`.

### 9.4. API anti-spam và rate limiting

Alex đã có:

- API Gateway usage plan cho ingest endpoint.
- API key bắt buộc cho `/ingest`.
- API Gateway HTTP API stage throttling cho Part 7.
- SQS giúp absorb bursts.
- DLQ giúp failure không loop vô hạn mãi.

DATN nên có:

- Public user API:
  - API Gateway throttling.
  - Per-user application-level quota nếu cần.
- Internal ingest/scrape API:
  - API key hoặc private route.
  - Usage plan.
- Search/scrape endpoints:
  - Rate limit để tránh user spam gây crawl quá nhiều.
  - Job dedup: nếu cùng user search cùng keyword trong vài phút, reuse/cache.
- External GPU endpoints:
  - API key/service token.
  - Timeout/retry budget.

### 9.5. CORS

Alex:

- CloudFront serves frontend.
- `/api/*` same-origin route qua CloudFront.
- Local API uses localhost origin.
- FastAPI CORS controlled by env.

DATN:

- Production nên dùng same-origin `/api/*` qua CloudFront để giảm CORS complexity.
- Local dev:
  - frontend `localhost:3000`,
  - backend `localhost:8000`.
- Không dùng `*` nếu có auth headers/token.

### 9.6. Input Validation Guardrails

Alex:

- Pydantic models trong API.
- `backend/database/src/schemas.py` validation.
- `backend/shared/alex_shared/guardrails.py`:
  - `sanitize_user_input(text)`
  - detect prompt injection patterns.

Patterns phát hiện:

- `ignore previous instructions`
- `disregard all prior`
- `forget everything`
- `new instructions:`
- `system:`
- `assistant:`

DATN:

- Validate:
  - keyword,
  - budget/max_price,
  - category,
  - source list,
  - product URL,
  - conversation text.
- Sanitize free-text fields:
  - chat input,
  - search query,
  - user profile display name,
  - saved notes.
- Không nên block mọi tiếng Việt lạ; chỉ reject/flag prompt injection rõ ràng.

### 9.7. Agent Output Validation

Alex:

- Tagger dùng structured Pydantic output.
- Charter JSON output được validate bằng `validate_chart_data`.
- Reporter có `judge.py` evaluator.
- Researcher verified-web-only gate.
- Response truncation bằng `truncate_response`.

DATN:

- Router Agent output phải schema:

```json
{
  "intent": "TIM_SAN_PHAM",
  "keyword": "laptop gaming",
  "max_price": 15000000,
  "category": "laptop",
  "entities": {}
}
```

- Compare Agent output phải schema:

```json
{
  "product_name": "...",
  "results": [
    {
      "source": "Shopee",
      "price": 12300000,
      "url": "https://...",
      "availability": "in_stock",
      "captured_at": "..."
    }
  ]
}
```

- Price Estimator output phải có:
  - estimate,
  - currency,
  - confidence,
  - model_breakdown,
  - caveats.
- Scraper output phải validate URL/source/price.
- Synthesizer final answer nên truncate nếu quá dài.

### 9.8. Retry Logic with Exponential Backoff

Alex:

- Dùng `tenacity`.
- Retry rate limit/temporary failures.
- Researcher retry constrained browser path.
- Agent lambdas retry model errors/temporary failures.

DATN:

- Retry nên áp dụng cho:
  - model endpoint calls,
  - scraper HTTP calls,
  - vector ingest,
  - transient API failures.
- Không retry vô hạn.
- Không retry lỗi validation/user input.
- Với scraping:
  - retry 2-3 lần,
  - exponential backoff,
  - rotate source/fallback,
  - record source failure.

### 9.9. Logging ở console và CloudWatch

Alex:

- `[TIMING]` logs ở agent phases.
- Structured JSON events từ Guide 8 update:
  - `PLANNER_STARTED`
  - `AGENT_INVOKED`
  - `AI_DECISION`
  - `PLANNER_COMPLETED`
  - `REPORTER_STARTED`
  - `REPORTER_COMPLETED`
  - `CHARTER_STARTED`
  - `CHARTER_COMPLETED`
  - `RETIREMENT_STARTED`
  - `RETIREMENT_COMPLETED`
- `backend/watch_agents.py` để tail logs nhiều Lambda.
- Researcher logs:
  - `research_run phase_start`
  - `research_run phase_end`
  - `research_run request_end`
  - `research_ingest`

DATN:

- Mọi job nên log:
  - event,
  - job_id,
  - user_id,
  - agent,
  - source,
  - model,
  - duration_ms,
  - status,
  - error_type.
- Không log API keys, JWT, raw credentials, full env.
- Console local logs nên tương tự CloudWatch structure để debug dễ.

### 9.10. LangFuse, Logfire và OpenAI Agents traces

Alex:

- `observability.py` trong từng agent.
- Optional LangFuse env:
  - `LANGFUSE_PUBLIC_KEY`
  - `LANGFUSE_SECRET_KEY`
  - `LANGFUSE_HOST`
- Logfire instruments OpenAI Agents SDK.
- OpenAI traces có thể xem ở OpenAI platform khi dùng OpenAI models.
- Observability context flush cuối Lambda.

Lưu ý:

- Observability optional; agents vẫn chạy nếu thiếu LangFuse credentials.
- Flush có thể tăng tail latency.

DATN:

- Nên thêm `backend/shared/observability.py` dùng chung.
- Track:
  - agent traces,
  - tool calls,
  - model latency,
  - token usage/cost,
  - failed tool calls,
  - prompt/output snippets ở mức an toàn.
- Với Qwen/vLLM external endpoints, cần tự log request/response metadata vì OpenAI traces có thể không tự có nếu không qua OpenAI.

### 9.11. Audit logging và explainability

Alex Guide 8 update:

- `backend/shared/alex_shared/audit.py`.
- `AuditLogger.log_ai_decision()` ghi:
  - timestamp,
  - agent,
  - job_id,
  - model,
  - input hash,
  - output summary,
  - duration_ms.
- Tagger có `rationale`.
- Reporter recommendations có:
  - Recommendation,
  - Reasoning,
  - Impact,
  - Priority.

DATN:

- Price estimates cần explainability:
  - model breakdown,
  - similar products,
  - assumptions,
  - confidence,
  - limitations.
- Product advice cần reasoning:
  - vì sao chọn sản phẩm,
  - tradeoffs,
  - nguồn giá,
  - freshness timestamp.
- Audit logs cần đủ để bảo vệ báo cáo đồ án:
  - agent nào quyết định gì,
  - model nào,
  - dữ liệu nguồn nào,
  - mất bao lâu,
  - outcome.

---

## 10. Shared package pattern

Alex có `backend/shared/` sau Guide 8 update:

```text
backend/shared/
├── pyproject.toml
├── uv.lock
└── alex_shared/
    ├── __init__.py
    ├── guardrails.py
    └── audit.py
```

Nó được mount/cài vào Lambda packages của agents.

DATN nên tạo package tương tự:

```text
backend/shared/
├── pyproject.toml
└── datn_shared/
    ├── __init__.py
    ├── guardrails.py
    ├── audit.py
    ├── logging.py
    ├── schemas.py
    ├── retry.py
    └── observability.py
```

Nội dung nên có:

- prompt injection detection,
- response truncation,
- schema validators,
- source URL validation,
- product price normalization,
- audit logger,
- structured logger,
- retry decorators,
- common Pydantic models.

---

## 11. Packaging và deploy workflow từ Alex

### 11.1. Nguyên tắc chung

Alex dùng:

- `uv` cho Python package management.
- Mỗi folder Python là uv project riêng.
- Docker để package Lambda tương thích Linux x86_64.
- ZIP cho Lambda source package.
- ECR container image cho Researcher.
- Terraform apply từng folder độc lập.

### 11.2. ZIP Lambda packaging

Mỗi agent có `package_docker.py`:

- export dependencies từ `uv.lock`,
- strip ANSI color codes từ `uv export`,
- mount `backend/database` và `backend/shared`,
- install vào package dir,
- copy source files,
- zip thành `<agent>_lambda.zip`.

Alex đã gặp lỗi WSL2:

- Docker root tạo files trong `/tmp`.
- Python host không cleanup được root-owned files.
- Fix: catch `PermissionError` sau khi ZIP đã tạo.

DATN mapping:

- Nếu deploy Lambda agents, dùng pattern này.
- Nếu agents cần native deps, luôn package bằng Docker.
- Không rely vào local OS package.
- Với shared package, nhớ mount/cài `/shared`.

### 11.3. Container image packaging

Researcher dùng:

- `backend/researcher/Dockerfile`.
- ECR repo.
- `backend/researcher/deploy.py`.
- `docker buildx build --platform linux/amd64`.
- push image.
- write `researcher.auto.tfvars.json`.
- Terraform apply.

DATN mapping:

- Browser/scraper service hoặc model bridge service có thể dùng container.
- Nếu chạy Playwright/Chromium/curl_cffi phức tạp, container image ổn định hơn zip Lambda.
- Nếu chạy Qwen/vLLM, không dùng Lambda; dùng external GPU service/container.

### 11.4. Terraform apply từng folder

Alex chia:

```text
terraform/2_sagemaker
terraform/3_ingestion
terraform/4_researcher
terraform/5_database
terraform/6_agents
terraform/7_frontend
terraform/8_enterprise
```

Đặc điểm:

- Mỗi folder có local `terraform.tfstate`.
- Mỗi folder có `terraform.tfvars.example`.
- Deploy incremental theo guide.
- Outputs folder trước được copy/đọc bởi folder sau.

DATN nên học theo:

```text
terraform/1_foundation
terraform/2_database
terraform/3_vector_store
terraform/4_ingest
terraform/5_agents
terraform/6_frontend_api
terraform/7_monitoring
```

Không cần y hệt tên. Quan trọng là mỗi part độc lập, có README rõ, có outputs rõ.

### 11.5. Deploy workflow gợi ý cho DATN

MVP production deploy có thể theo thứ tự:

1. `terraform/1_foundation`: IAM/logging/basic config nếu cần.
2. `terraform/2_database`: Aurora + secrets.
3. `backend/database`: migrations + seed minimal.
4. `terraform/3_vector_store`: S3 Vectors hoặc chọn ChromaDB external.
5. `backend/api`: package FastAPI Lambda.
6. `terraform/6_frontend_api`: API Gateway + Lambda + CloudFront/S3.
7. `frontend`: build Next.js, deploy static.
8. `terraform/5_agents`: SQS + Lambda agents.
9. External GPU/model endpoints: deploy riêng, inject URLs/secrets.
10. `terraform/7_monitoring`: dashboards/alarms.

---

## 12. Testing và validation workflow từ Alex

Alex có pattern:

- `test_simple.py`: local smoke test, sometimes mocks Lambda calls.
- `test_full.py`: deployed AWS integration test.
- `backend/test_full.py`: end-to-end SQS test.
- `watch_agents.py`: CloudWatch tail for all agents.
- `terraform output`: inspect deployed resources.
- Frontend local via `scripts/run_local.py`.

DATN nên có:

| Test type | Ví dụ |
|---|---|
| Unit test scraper | parse known HTML/API response thành product object. |
| Unit test guardrails | prompt injection, invalid URL, invalid price. |
| Unit test router | 100 câu tiếng Việt → intent expected. |
| Local agent test | mock model/scraper, verify job payload. |
| External model smoke test | Qwen/vLLM endpoint health + simple completion. |
| SQS e2e test | create job → send SQS → planner → result in DB. |
| API auth test | no token/invalid token/valid token. |
| Rate-limit test | burst requests expected throttled. |
| Frontend smoke | login, start job, poll result. |

Không nên deploy trước khi có tối thiểu:

- `/health` API.
- DB connection smoke.
- auth smoke.
- SQS job smoke.
- one agent end-to-end smoke.

---

## 13. Database design lessons

### 13.1. Alex database decision

Alex dùng 5 bảng đơn giản:

- users,
- instruments,
- accounts,
- positions,
- jobs.

Key design:

- User identity từ Clerk.
- Shared reference data tách khỏi user data.
- Jobs có nhiều JSONB payload fields, mỗi agent ghi một field riêng.

### 13.2. DATN sơ bộ schema

Chưa implement, chỉ gợi ý brainstorm:

```text
users
  clerk_user_id PK
  display_name
  preferences JSONB
  created_at
  updated_at

conversations
  id UUID PK
  clerk_user_id FK
  title
  status
  created_at
  updated_at

messages
  id UUID PK
  conversation_id FK
  role
  content
  metadata JSONB
  created_at

jobs
  id UUID PK
  clerk_user_id FK
  conversation_id nullable
  job_type
  status
  request_payload JSONB
  router_payload JSONB
  search_payload JSONB
  scrape_payload JSONB
  pricing_payload JSONB
  compare_payload JSONB
  advisor_payload JSONB
  final_payload JSONB
  error_message
  started_at
  completed_at
  created_at
  updated_at

products
  id UUID PK
  canonical_name
  brand
  category
  normalized_specs JSONB
  created_at
  updated_at

product_sources
  id UUID PK
  product_id FK
  source
  source_product_id
  url
  price_vnd
  availability
  captured_at
  raw_payload JSONB

price_estimates
  id UUID PK
  job_id FK
  product_id nullable
  estimate_vnd
  confidence
  model_breakdown JSONB
  created_at

agent_runs
  id UUID PK
  job_id FK
  agent_name
  model
  input_hash
  output_summary JSONB
  duration_ms
  status
  created_at
```

### 13.3. Vì sao nên dùng JSONB payloads

Alex chứng minh JSONB payload per-agent làm multi-agent system đơn giản hơn:

- Agent không cần tranh ghi một field chung.
- Frontend dễ render từng tab/block.
- Debug dễ biết agent nào failed.
- Schema relational core vẫn gọn.

DATN nên dùng tương tự cho `jobs`.

---

## 14. Vector store/RAG lessons

Alex:

- Ingest text → SageMaker embedding → S3 Vectors.
- Reporter query S3 Vectors để lấy market insights.
- Researcher liên tục nạp knowledge vào vector store.

DATN:

- Có kế hoạch ChromaDB + multilingual embeddings.
- Khi production lên AWS, có hai hướng:

### Option A: S3 Vectors production

Ưu:

- AWS managed.
- Integrates với Lambda/IAM.
- Không phải vận hành ChromaDB server.
- Phù hợp nếu dữ liệu vừa phải và query qua AWS.

Nhược:

- Cần embedding endpoint.
- S3 Vectors mới, tooling có thể thay đổi.
- Cần migration từ ChromaDB.

### Option B: ChromaDB external/local-first

Ưu:

- Phù hợp tài liệu DATN hiện tại.
- Dễ dev local.
- Có sẵn pipeline build vectorstore.

Nhược:

- Production vận hành khó hơn nếu cần multi-user/reliability.
- Lambda không phù hợp giữ ChromaDB local lớn.
- Cần server/container riêng.

Khuyến nghị sơ bộ:

- MVP local/research: ChromaDB.
- Production AWS demo: cân nhắc S3 Vectors cho knowledge/product embeddings hoặc host ChromaDB trong container riêng nếu dataset lớn.

---

## 15. Scraping lessons

Alex Researcher không phải ecommerce scraper, nhưng có lessons quan trọng:

- Verified web content only.
- Source URL validation.
- Degraded/fallback detection.
- Browser phase tracking.
- Fail closed khi không xác minh được nội dung.
- Structured logs theo run id.

DATN scraping TMĐT nên có:

- Source-specific adapters:
  - Shopee,
  - Tiki,
  - Lazada,
  - Thế Giới Di Động,
  - CellphoneS,
  - FPT Shop.
- Unified product/deal schema.
- Per-source timeout.
- Per-source retry/backoff.
- CAPTCHA/block detection.
- Proxy/session strategy nếu cần.
- Source health tracking.
- Legal/ToS review cho đồ án.

Không nên để một Lambda user request scrape 5 nguồn rồi chờ sync. Nên:

1. API tạo job.
2. SQS fan-out hoặc planner gọi scraper tasks.
3. Scraper results lưu DB.
4. Compare/pricing chạy sau.
5. Frontend poll.

---

## 16. Cost management lessons

Alex:

- Aurora là chi phí đáng chú ý nhất khi chạy lâu.
- SageMaker serverless scale-to-zero.
- Lambda/SQS/API Gateway rẻ theo usage.
- CloudWatch logs có chi phí nếu retention lớn.
- OpenAI model calls có token cost.
- External researcher/browser có timeout/cold start.

DATN:

- GPU external là chi phí lớn nhất.
- Scraping nhiều nguồn có thể phát sinh proxy/VPS cost.
- Aurora chạy liên tục có chi phí.
- Model calls cần quota/rate limit.
- Nên có budget guard:
  - per-user search limit,
  - per-job max sources,
  - max model iterations,
  - max scraping timeout,
  - cache/reuse recent results.

---

## 17. Security checklist cần học từ Alex

Alex đã có:

- Clerk JWT.
- API key cho ingest.
- Secrets Manager.
- IAM roles per service.
- CORS.
- API throttling.
- SQS/DLQ.
- No secret logging rule.

DATN nên có:

- Clerk JWT cho user API.
- Service API keys cho internal/external GPU model endpoints.
- Secrets Manager hoặc parameter store cho production secrets.
- Không commit `.env`, `terraform.tfvars`.
- Không log JWT/API keys.
- API Gateway throttling.
- Per-user quota nếu demo public.
- S3 bucket private nơi chứa raw scraped data nếu có.
- Scraper source allowlist.
- URL validation chống SSRF nếu user submit URL.
- CloudWatch log retention có chủ đích.

Chưa nên triển khai ngay nếu chưa có threat model:

- WAF.
- GuardDuty.
- VPC endpoints.
- Private subnets.
- Custom domain/cert.
- API Gateway JWT authorizer.

Nhưng tài liệu DATN nên biết đây là roadmap enterprise hardening.

---

## 18. Known risks khi áp dụng Alex sang DATN

| Risk | Tác động | Cách giảm |
|---|---|---|
| Scraping bị block/CAPTCHA | Search/compare fail | Multi-source fallback, proxy/session, cache, fail gracefully. |
| Lambda timeout với scraping/model | Job fail | Async jobs, external workers, timeouts per source. |
| Qwen/vLLM endpoint chậm hoặc down | Chat/search fail | Health checks, retry, fallback smaller model. |
| CORS/auth config sai | Frontend không gọi được API | Same-origin CloudFront `/api/*`, test local/prod. |
| Cost GPU cao | Hết budget | External GPU only when needed, stop instances, use smaller models for router. |
| Data quality thấp | Tư vấn sai | Source validation, timestamp, confidence, audit. |
| Vector search tiếng Việt kém | RAG kém | Test embeddings, bge-m3/e5, evaluate retrieval. |
| Over-engineering quá sớm | Chậm tiến độ DATN | MVP first: auth + API + job + one search/compare flow. |

---

## 19. DATN target architecture sơ bộ

Đây là đề xuất để brainstorm, chưa phải plan implement.

### 19.1. MVP production-ish

MVP nên tập trung:

- Next.js frontend mới.
- Clerk login.
- FastAPI backend.
- Aurora users/jobs/conversations.
- SQS queue.
- Một Planner/Router agent.
- Một Search/Scrape flow đơn giản với 1-2 nguồn.
- Một Price Estimator bridge gọi model/service hiện có.
- Job polling UI.
- Structured logs.

### 19.2. Components

```text
frontend/
  Next.js UI:
    - landing
    - login
    - chat
    - search
    - job result/history

backend/api/
  FastAPI:
    - auth guard
    - create/search jobs
    - job status
    - conversation APIs

backend/database/
  Aurora Data API:
    - users
    - conversations
    - jobs
    - products/results

backend/router/
  Router Agent:
    - classify intent
    - build job plan

backend/searcher/
  Search Agent:
    - source selection
    - query/scrape kickoff

backend/scraper/
  Scraper service/agent:
    - Shopee/Tiki/TGDĐ adapters

backend/pricer/
  Price estimator bridge:
    - Qwen pricer
    - DNN
    - specialist model

backend/synthesizer/
  Final response:
    - Vietnamese answer
    - citations/sources
```

### 19.3. AWS resources

```text
CloudFront
S3 frontend bucket
API Gateway HTTP API
Lambda alex-datn-api
Aurora Serverless v2 + Data API
Secrets Manager
SQS queues + DLQs
Lambda router/search/pricer/synthesizer
S3/S3 Vectors or external ChromaDB
ECR for containerized scraper if needed
CloudWatch dashboards/logs
Optional LangFuse/OpenAI traces
```

### 19.4. External GPU/model services

```text
Qwen/vLLM endpoint:
  - router/synthesizer or only synthesizer
  - OpenAI-compatible API preferred

Fine-tuned pricer endpoint:
  - Vast.ai/RunPod/Modal
  - service token auth
  - timeout/retry

DNN endpoint:
  - local container or Modal
  - can be called by pricer agent
```

### 19.5. API endpoints sơ bộ

```text
GET  /health
GET  /api/user
PUT  /api/user

POST /api/chat
GET  /api/conversations
GET  /api/conversations/{id}

POST /api/search
POST /api/compare
POST /api/estimate-price

GET  /api/jobs
GET  /api/jobs/{job_id}

GET  /api/products/{product_id}
POST /api/saved-products
GET  /api/saved-products
```

---

## 20. Concrete Alex files to inspect before implementing DATN

### Backend/API

- `backend/api/README.md`
- `backend/api/main.py`
- `backend/api/lambda_handler.py`
- `backend/api/package_docker.py`

### Database

- `backend/database/README.md`
- `backend/database/src/client.py`
- `backend/database/src/models.py`
- `backend/database/src/schemas.py`
- `backend/database/migrations/001_schema.sql`
- `backend/database/run_migrations.py`

### Agents

- `backend/planner/README.md`
- `backend/planner/agent.py`
- `backend/planner/lambda_handler.py`
- `backend/reporter/README.md`
- `backend/reporter/agent.py`
- `backend/reporter/judge.py`
- `backend/charter/README.md`
- `backend/charter/lambda_handler.py`
- `backend/tagger/README.md`
- `backend/tagger/agent.py`
- `backend/retirement/README.md`
- `backend/retirement/agent.py`

### Shared enterprise utilities

- `backend/shared/alex_shared/guardrails.py`
- `backend/shared/alex_shared/audit.py`

### Researcher/scraping-like service

- `backend/researcher/README.md`
- `backend/researcher/server.py`
- `backend/researcher/context.py`
- `backend/researcher/tools.py`
- `backend/researcher/mcp_servers.py`
- `backend/researcher/Dockerfile`
- `backend/researcher/deploy.py`

### Frontend

- `frontend/README.md`
- `frontend/lib/config.ts`
- `frontend/lib/api.ts`
- `frontend/lib/events.ts`
- `frontend/pages/advisor-team.tsx`
- `frontend/pages/analysis.tsx`
- `frontend/components/Layout.tsx`

### Terraform

- `terraform/2_sagemaker/README.md`
- `terraform/3_ingestion/README.md`
- `terraform/4_researcher/README.md`
- `terraform/5_database/README.md`
- `terraform/6_agents/README.md`
- `terraform/7_frontend/README.md`
- `terraform/8_enterprise/README.md`

### Enterprise docs

- `README_about_enterprise.md`
- `Update_for_8_enterprise.md`
- `guides/8_enterprise.md`

---

## 21. Handoff checklist cho coding agent tiếp theo

Trước khi viết code cho DATN:

- [ ] Đọc file này.
- [ ] Đọc 3 file trong `DATN/`.
- [ ] Xác định MVP DATN đầu tiên: chat, search, compare, hay price estimate.
- [ ] Chốt frontend Next.js target: static export + CloudFront hay server mode.
- [ ] Chốt auth: Clerk.
- [ ] Chốt database schema MVP.
- [ ] Chốt vector store MVP: ChromaDB hay S3 Vectors.
- [ ] Chốt model serving MVP: external Qwen/vLLM hay OpenAI-compatible temporary model.
- [ ] Chốt scraping MVP: nguồn nào trước, timeout, legal/ToS considerations.
- [ ] Chốt job orchestration: SQS queue structure.
- [ ] Chốt observability: CloudWatch only hay thêm LangFuse/OpenAI traces.
- [ ] Chốt deploy budget và cleanup policy.

Không nên bắt đầu bằng full architecture implementation. Nên chọn một vertical slice:

```text
User logs in
  -> starts product search
  -> API creates job
  -> SQS triggers simple search agent
  -> result saved to DB
  -> frontend polls and displays result
```

Sau khi vertical slice chạy ổn, mới thêm:

- compare,
- price estimation,
- Qwen/vLLM,
- multiple scrapers,
- RAG,
- audit dashboard,
- enterprise hardening.

---

## 22. Tóm tắt ngắn cho agent mới

Alex là blueprint production đã triển khai đầy đủ hơn DATN:

- CloudFront + S3 static frontend.
- FastAPI + Mangum Lambda.
- Clerk JWT auth.
- Aurora Serverless v2 + Data API.
- SQS + DLQ async jobs.
- Lambda planner + specialist agents.
- S3 Vectors + SageMaker embeddings.
- ECR + Lambda container for browser/research service.
- API Gateway, API key, usage plan, throttling.
- Terraform từng folder độc lập.
- Docker ZIP packaging cho Lambda.
- Structured logs, CloudWatch, LangFuse/OpenAI traces.
- Guardrails, retries, output validation, audit logging.

DATN nên học patterns này nhưng đổi domain:

- financial portfolio → shopping/products/prices.
- instruments/accounts/positions → products/sources/searches/comparisons.
- report/charts/retirement agents → search/compare/pricer/advisor/synthesizer agents.
- researcher market news → scraper/product knowledge ingest.
- OpenAI-only Alex agents → hybrid AWS control plane + external GPU Qwen/vLLM.

Mục tiêu tiếp theo không phải deploy ngay toàn bộ. Mục tiêu là brainstorm MVP DATN production slice dựa trên các pattern đã chứng minh trong Alex.

---

## 23. DATN production scaffold spec: tổ chức repo theo kiểu Alex

Phần này là spec bổ sung bắt buộc cho coding agent tiếp theo. Mục tiêu không chỉ là bê logic DATN hiện tại lên AWS, mà phải tổ chức lại project thành một production repo có thể triển khai từng phần, debug từng phần, và học được end-to-end như Alex.

### 23.1. Nguyên tắc thiết kế repo DATN

DATN nên áp dụng các nguyên tắc sau từ Alex:

1. Tách hạ tầng thành nhiều thư mục Terraform độc lập.
   - Mỗi folder có `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`, `README.md`.
   - Mỗi folder có local state riêng.
   - Không dùng một root Terraform khổng lồ cho toàn bộ hệ thống ở giai đoạn đầu.
   - Mỗi folder có thể `terraform init`, `terraform plan`, `terraform apply`, `terraform destroy` riêng.
   - Output của folder trước được copy thủ công vào `terraform.tfvars` của folder sau, giống Alex. Cách này không tối ưu cho production team lớn, nhưng rất tốt cho học tập, debug, và DATN.

2. Tách backend thành nhiều service/module nhỏ.
   - Không để toàn bộ FastAPI, agents, scraper, ingest, database, model client trong một file hoặc một folder.
   - Mỗi backend component nên có README riêng, test local riêng, package/deploy riêng nếu là Lambda/container riêng.
   - Shared code để trong `backend/shared/` hoặc package nội bộ tương tự Alex.

3. Tạo `guides/` như một runbook end-to-end.
   - Coding agent không chỉ viết code; phải viết hướng dẫn triển khai tuần tự.
   - Mỗi guide phải có mục tiêu, prerequisites, commands, expected outputs, troubleshooting, rollback/cleanup.
   - Guides là tài liệu vận hành chính cho sinh viên hoặc agent session mới.

4. Tách plan/spec khỏi implementation.
   - Trước khi code, agent phải đọc file handoff này.
   - Sau đó tạo hoặc cập nhật plans/specs trong DATN.
   - Chỉ implement sau khi plan được xác nhận hoặc sau khi phạm vi MVP rõ ràng.

5. Không deploy toàn bộ ngay.
   - Bắt đầu bằng vertical slice nhỏ.
   - Deploy được một luồng đơn giản trước: frontend -> API -> job -> worker -> DB -> frontend.
   - Sau đó mới thêm RAG, scraper nhiều nguồn, external GPU model, observability nâng cao.

### 23.2. Cấu trúc repo DATN được đề xuất

Nếu DATN được tách thành một app riêng trong repo này, có thể dùng cấu trúc:

```text
DATN/
├── README.md
├── plans/
│   ├── 00_context.md
│   ├── 01_mvp_scope.md
│   ├── 02_aws_architecture.md
│   ├── 03_backend_architecture.md
│   ├── 04_frontend_architecture.md
│   ├── 05_agent_architecture.md
│   ├── 06_security_enterprise.md
│   └── 07_deployment_plan.md
│
├── specs/
│   ├── repo_structure.md
│   ├── api_contract.md
│   ├── database_schema.md
│   ├── job_orchestration.md
│   ├── vector_ingest.md
│   ├── model_gateway.md
│   ├── frontend_pages.md
│   ├── observability.md
│   └── security.md
│
├── guides/
│   ├── 1_foundation.md
│   ├── 2_database.md
│   ├── 3_backend_api.md
│   ├── 4_vector_ingest.md
│   ├── 5_agents.md
│   ├── 6_frontend.md
│   ├── 7_model_services.md
│   ├── 8_enterprise.md
│   ├── architecture.md
│   └── agent_architecture.md
│
├── backend/
│   ├── README.md
│   ├── shared/
│   ├── database/
│   ├── api/
│   ├── ingest/
│   ├── router/
│   ├── searcher/
│   ├── scraper/
│   ├── comparer/
│   ├── pricer/
│   ├── advisor/
│   └── synthesizer/
│
├── frontend/
│   ├── README.md
│   └── ...
│
├── terraform/
│   ├── README.md
│   ├── 1_foundation/
│   ├── 2_database/
│   ├── 3_vector_store/
│   ├── 4_ingest/
│   ├── 5_agents/
│   ├── 6_frontend_api/
│   ├── 7_model_services/
│   └── 8_enterprise/
│
└── scripts/
    ├── README.md
    ├── run_local.py
    ├── deploy_frontend.py
    ├── package_lambda.py
    ├── package_container.py
    └── destroy.py
```

Ghi chú:

- `plans/` trả lời câu hỏi "làm gì, vì sao, phase nào".
- `specs/` trả lời câu hỏi "contract kỹ thuật cụ thể là gì".
- `guides/` trả lời câu hỏi "người khác triển khai end-to-end thế nào".
- `backend/` chứa implementation backend.
- `frontend/` chứa Next.js app mới cho DATN.
- `terraform/` chứa IaC chia nhỏ để deploy độc lập.
- `scripts/` chứa script hỗ trợ package/deploy/test local, ưu tiên `uv`.

Nếu muốn giữ 3 file DATN hiện tại, đặt chúng vào:

```text
DATN/references/
├── Project_Development_Plan.md
├── DOCUMENTATION_SEARCHKEY.md
└── DOCUMENTATION_PRICE_IS_RIGHT.md
```

Hoặc giữ nguyên ở root `DATN/`, nhưng coding agent phải coi chúng là tài liệu nguồn, không phải production app.

---

## 24. Terraform spec cho DATN: chia folder để triển khai riêng biệt

DATN nên có một folder `terraform/` riêng, không dùng chung Terraform state với Alex.

### 24.1. `terraform/README.md`

File này phải giải thích:

- Mỗi folder Terraform là độc lập.
- Mỗi folder cần copy `terraform.tfvars.example` thành `terraform.tfvars`.
- Không commit `terraform.tfvars`.
- Chạy thứ tự theo guides.
- Khi debug, chỉ chạy folder đang lỗi.
- Khi cleanup, destroy ngược thứ tự.
- Không chạy `terraform apply` nếu chưa kiểm tra plan.

Ví dụ thứ tự deploy:

```text
1_foundation
  -> 2_database
  -> 3_vector_store
  -> 4_ingest
  -> 5_agents
  -> 6_frontend_api
  -> 7_model_services
  -> 8_enterprise
```

### 24.2. `terraform/1_foundation/`

Mục tiêu:

- Tạo các tài nguyên nền tảng dùng chung cho DATN.

Nên bao gồm:

- Project naming convention.
- IAM roles cơ bản.
- S3 bucket cho artifacts/package nếu cần.
- Optional KMS key.
- Optional CloudWatch log group retention policy.
- Optional Secrets Manager placeholders cho external services.

Không nên bao gồm:

- Database.
- Lambda business logic.
- Frontend distribution.
- External GPU infra.

Outputs nên có:

- `project_name`
- `aws_region`
- `artifact_bucket_name`
- `artifact_bucket_arn`
- `kms_key_arn` nếu dùng
- common IAM role ARNs nếu tạo ở đây

Debug dễ vì:

- Nếu foundation lỗi, chưa có service business nào phụ thuộc.
- Có thể destroy mà không mất user data.

### 24.3. `terraform/2_database/`

Mục tiêu:

- Tạo relational database cho DATN.

Pattern học từ Alex:

- Aurora Serverless v2 PostgreSQL.
- Data API để tránh VPC complexity cho MVP.
- Secrets Manager để lưu database credentials.
- Schema init script chạy riêng hoặc Lambda/init script tùy lựa chọn.

Bảng gợi ý cho DATN:

- `users`
- `search_sessions`
- `search_jobs`
- `products`
- `product_sources`
- `price_snapshots`
- `comparisons`
- `recommendations`
- `agent_runs`
- `audit_events`

Outputs nên có:

- `cluster_arn`
- `database_name`
- `secret_arn`
- `db_resource_arn`

Không đưa secret value vào output.

### 24.4. `terraform/3_vector_store/`

Mục tiêu:

- Tạo vector storage cho RAG/product knowledge.

Option recommended:

- S3 Vectors nếu muốn bám sát Alex và deploy serverless trên AWS.

Alternative:

- ChromaDB chỉ cho local/dev.
- OpenSearch Serverless nếu cần query/filter mạnh hơn nhưng chi phí cao hơn.

Nên bao gồm:

- S3 Vectors bucket/index.
- IAM permissions cho ingest/search Lambdas.
- Optional S3 raw document bucket cho crawled product documents.

Outputs nên có:

- vector bucket/index identifiers.
- raw docs bucket.
- IAM policy ARNs hoặc role attachments nếu tách.

### 24.5. `terraform/4_ingest/`

Mục tiêu:

- Tạo ingestion API/worker cho product documents, scraped pages, specs, reviews.

Pattern học từ Alex:

- Lambda ingest.
- API Gateway endpoint.
- API key/usage plan cho endpoint internal hoặc admin.
- Embedding endpoint/client.
- Ghi vectors vào S3 Vectors.

DATN variation:

- Nếu dùng external embedding service hoặc OpenAI-compatible embedding endpoint, config qua env var.
- Nếu dùng SageMaker embedding giống Alex, có thể thêm folder riêng hoặc gộp vào `3_vector_store`.

Nên bao gồm:

- `datn-ingest` Lambda.
- API Gateway REST/HTTP endpoint cho ingest.
- API key nếu endpoint không public-user-facing.
- IAM permissions đọc raw docs, ghi vector index.

Outputs nên có:

- ingest API URL.
- ingest API key name, không output key value nếu có thể tránh.
- ingest Lambda name.

### 24.6. `terraform/5_agents/`

Mục tiêu:

- Tạo SQS queues và Lambda workers cho agent workflow.

Pattern học từ Alex:

- Main SQS queue.
- DLQ.
- Planner/router Lambda.
- Specialist Lambdas.
- Per-Lambda IAM permissions tối thiểu.
- Environment variables truyền ARNs/URLs.

DATN agents gợi ý:

- `router`: nhận job và quyết định workflow.
- `searcher`: tìm sản phẩm theo query/user need.
- `scraper`: lấy dữ liệu từ nguồn public/allowed.
- `comparer`: so sánh sản phẩm.
- `pricer`: estimate giá hợp lý hoặc phát hiện deal.
- `advisor`: tư vấn mua/không mua theo nhu cầu người dùng.
- `synthesizer`: tổng hợp output cuối cùng dễ đọc.

Resources nên có:

- SQS main queue.
- SQS DLQ.
- Lambda `datn-router`.
- Lambda specialist workers.
- Optional Lambda reserved concurrency per worker.
- Optional event source mapping từ SQS đến router/worker.

Outputs nên có:

- queue URL/ARN.
- DLQ URL/ARN.
- Lambda names/ARNs.

### 24.7. `terraform/6_frontend_api/`

Mục tiêu:

- Deploy public entry points: API + frontend.

Pattern học từ Alex:

- FastAPI chạy trong Lambda qua Mangum.
- API Gateway route tới Lambda.
- Next.js static export deploy vào S3.
- CloudFront serve frontend và route `/api/*` về API Gateway.
- CORS xử lý ở FastAPI/API Gateway/CloudFront.
- Clerk JWT verification ở API.

Resources nên có:

- API Lambda.
- API Gateway.
- S3 frontend bucket.
- CloudFront distribution.
- CloudFront behaviors:
  - `/*` -> S3 static frontend.
  - `/api/*` -> API Gateway origin.
- Optional custom domain sau MVP.

Outputs nên có:

- API URL.
- CloudFront distribution URL.
- frontend bucket name.

### 24.8. `terraform/7_model_services/`

Mục tiêu:

- Cấu hình kết nối đến model services.

Vì DATN cần Qwen/vLLM/fine-tuned models và GPU AWS đắt, recommended architecture là hybrid:

- AWS giữ control plane.
- Model lớn chạy ở Vast.ai/Modal/RunPod hoặc provider GPU ngoài AWS.
- Backend gọi qua OpenAI-compatible API.

Terraform folder này không nhất thiết tạo GPU ngoài AWS nếu provider chưa có Terraform ổn định. Nó có thể:

- Tạo Secrets Manager secret names/placeholders cho external model API keys.
- Tạo Lambda/API config để gọi model gateway.
- Tạo optional lightweight model gateway trên Lambda nếu chỉ proxy HTTP.
- Tạo CloudWatch alarms cho model latency/error rate.

Không nên:

- Hardcode external API keys.
- Commit model endpoint private URL nếu nhạy cảm.
- Tạo dependency cứng vào một GPU vendor quá sớm.

Outputs nên có:

- secret ARN cho model API key.
- model gateway URL nếu có.
- config names cho backend.

### 24.9. `terraform/8_enterprise/`

Mục tiêu:

- Thêm enterprise operations sau khi core flow đã chạy.

Pattern học từ Alex:

- CloudWatch dashboard.
- Metrics cho Lambda/API/SQS.
- Logs Insights query.
- Alarms.
- Optional LangFuse/OpenAI trace env config.

DATN nên bổ sung:

- API Gateway throttling.
- WAF rate-based rule nếu public traffic đáng kể.
- CloudWatch alarms:
  - API 5xx.
  - Lambda errors.
  - Lambda duration p95.
  - SQS queue age.
  - DLQ messages.
  - Aurora ACU/cost.
  - External model error/timeout rate.
- Cost alarms/budget note.
- GuardDuty/Security Hub optional nếu scope DATN cần trình bày enterprise.

Outputs nên có:

- dashboard URL/name.
- alarm names.

---

## 25. Backend spec cho DATN: chia module nhỏ như Alex

Backend DATN không nên là một monolith script. Mỗi folder nên có trách nhiệm rõ ràng, README riêng, và test riêng.

### 25.1. `backend/shared/`

Mục tiêu:

- Chứa code dùng chung giữa API, agents, ingest.

Nên có:

- `config.py`: đọc env var an toàn, không in secrets.
- `logging.py`: structured logging JSON hoặc consistent console logs.
- `auth.py`: helper verify JWT hoặc parse identity nếu dùng chung.
- `guardrails.py`: input validation, prompt injection checks cơ bản.
- `retry.py`: retry with exponential backoff + jitter.
- `http.py`: HTTP client wrapper timeout/retry.
- `schemas.py`: Pydantic models chung.
- `audit.py`: audit event helper.
- `tracing.py`: LangFuse/OpenAI Agents trace integration.
- `rate_limit.py`: app-level rate limiting helper nếu cần.

Quy tắc:

- Không để shared package phụ thuộc ngược vào từng agent cụ thể.
- Shared chỉ chứa utility rõ ràng dùng từ hai nơi trở lên.
- Không trừu tượng hóa sớm nếu chỉ một module dùng.

### 25.2. `backend/database/`

Mục tiêu:

- Wrapper truy cập Aurora Data API hoặc database layer.

Pattern học từ Alex:

- Database class/service tách riêng khỏi FastAPI routes và agent logic.
- Query rõ ràng theo user/session/job.
- Không tin user_id từ request body; lấy từ verified JWT.

Nên có:

- `database.py`
- `schema.sql`
- `seed_data.py` nếu có dữ liệu demo.
- `README.md`
- `test_simple.py`
- `test_full.py`

APIs nội bộ gợi ý:

- create/get user.
- create search job.
- update job status.
- save product candidates.
- save price snapshots.
- save comparison.
- save recommendation.
- append audit event.
- load job context for agent.

### 25.3. `backend/api/`

Mục tiêu:

- FastAPI public backend cho frontend.

Pattern học từ Alex:

- FastAPI + Mangum for Lambda.
- Clerk JWT auth.
- CORS configured explicitly.
- API endpoints không chạy long task trực tiếp; tạo job và enqueue SQS.

Endpoints MVP gợi ý:

- `GET /health`
- `GET /me`
- `POST /search-jobs`
- `GET /search-jobs`
- `GET /search-jobs/{job_id}`
- `GET /search-jobs/{job_id}/results`
- `POST /comparisons`
- `GET /products/{product_id}`

Security:

- Verify Clerk JWT.
- Enforce per-user ownership.
- Validate input bằng Pydantic.
- Size limit cho query và filters.
- Return generic errors, log detailed errors server-side.

### 25.4. `backend/ingest/`

Mục tiêu:

- Nhận documents/product data/reviews/specs, embed, ghi vector store.

Nên có:

- `lambda_handler.py`
- `ingest.py`
- `embeddings.py`
- `vector_store.py`
- `schemas.py`
- `README.md`
- `test_simple.py`
- `test_full.py`

Input:

- source URL hoặc source name.
- product metadata.
- text chunks.
- optional category.
- optional language.

Output:

- number of chunks ingested.
- vector IDs.
- source metadata.

Guardrails:

- Validate source.
- Limit document size.
- Deduplicate by URL/content hash.
- Avoid storing raw secrets or private user data in vector metadata.

### 25.5. `backend/router/`

Mục tiêu:

- Planner/orchestrator cho DATN.

Alex equivalent:

- `backend/planner/`.

DATN responsibilities:

- Load job from DB.
- Decide which specialist agents to run.
- Dispatch search/scrape/compare/price/advice steps.
- Save final status.
- Handle partial failures.

Nên có:

- `lambda_handler.py`
- `agent.py`
- `templates.py`
- `schemas.py`
- `README.md`
- `test_simple.py`
- `test_full.py`

### 25.6. `backend/searcher/`

Mục tiêu:

- Tìm product candidates từ internal DB/vector store và optional external APIs.

Nên làm:

- Query vector store/product DB.
- Normalize product names.
- Return candidate list with confidence.
- Không scrape web nặng trong searcher nếu scraper đã tách riêng.

### 25.7. `backend/scraper/`

Mục tiêu:

- Thu thập thông tin từ nguồn được phép.

Nên làm:

- Fetch pages/APIs với timeout.
- Parse structured product info.
- Save raw snapshots hoặc normalized fields.
- Respect robots/ToS/legal constraints theo scope DATN.

Không nên:

- Dùng browser automation nặng trong Lambda ZIP nếu dependency quá lớn.
- Chạy crawl vô hạn.
- Spam websites.

Nếu cần browser:

- Dùng Lambda container image.
- Hoặc external scraping service.
- Hoặc queue riêng với concurrency thấp.

### 25.8. `backend/comparer/`

Mục tiêu:

- So sánh products theo tiêu chí người dùng.

Inputs:

- user need.
- product candidates.
- normalized specs.
- prices.
- reviews/ratings nếu có.

Outputs:

- comparison table JSON.
- pros/cons.
- ranked products.
- explanation.

Validation:

- Output phải match schema.
- Không được hallucinate price/spec nếu thiếu dữ liệu.
- Field nào thiếu phải ghi `unknown` hoặc `not_available`.

### 25.9. `backend/pricer/`

Mục tiêu:

- Estimate fair price / detect deal.

Pattern từ DATN hiện tại:

- ensemble pricing.
- historical comparisons.
- product similarity.

Production adaptation:

- Tách model estimation khỏi prompt text.
- Log input features.
- Save price snapshot.
- Return confidence interval.

Outputs:

- current price.
- estimated fair price.
- deal score.
- confidence.
- reasons.

### 25.10. `backend/advisor/`

Mục tiêu:

- Đưa recommendation theo nhu cầu người dùng.

Nên làm:

- Dùng output từ comparer/pricer.
- Cá nhân hóa theo budget, brand preference, usage intent.
- Giải thích tradeoffs.

Không nên:

- Tự bịa dữ liệu.
- Recommend nếu confidence quá thấp mà không cảnh báo.

### 25.11. `backend/synthesizer/`

Mục tiêu:

- Tổng hợp kết quả cuối cùng cho frontend.

Nên làm:

- Convert agent outputs thành response UX-friendly.
- Produce sections:
  - best pick.
  - alternatives.
  - price analysis.
  - evidence.
  - warnings.
  - next actions.

Đây có thể là agent hoặc deterministic formatter tùy MVP.

---

## 26. Guides spec cho DATN: viết từng bước end-to-end như Alex

Folder `guides/` không phải tài liệu phụ. Nó là cách triển khai chính cho DATN.

### 26.1. Quy chuẩn cho mỗi guide

Mỗi file guide phải có:

```text
# Guide N: Title

## Goal
Guide này triển khai phần nào.

## What you will build
Danh sách AWS/backend/frontend components.

## Prerequisites
Guide trước nào cần xong, output nào cần copy.

## Files involved
Các folder/file liên quan.

## Configuration
Biến môi trường, terraform.tfvars.example, không ghi secrets thật.

## Step-by-step
Các bước cụ thể.

## Verify
Lệnh kiểm tra, expected output.

## Troubleshooting
Lỗi thường gặp và cách debug.

## Cost notes
Tài nguyên nào có thể tốn tiền.

## Cleanup
Cách destroy phần này nếu cần.

## Next guide
Guide tiếp theo dùng output nào.
```

### 26.2. `guides/1_foundation.md`

Nội dung:

- AWS account/region assumptions.
- IAM user/permissions.
- AWS CLI configured.
- Naming convention.
- Terraform folder strategy.
- S3 artifact bucket.
- Secrets policy.
- Cost warning.

Deliverable:

- `terraform/1_foundation` applied.
- Outputs copied to next guide.

### 26.3. `guides/2_database.md`

Nội dung:

- Aurora Serverless v2 rationale.
- Data API rationale.
- Schema design.
- Seed demo data if needed.
- How user isolation works.
- How jobs/products/snapshots are stored.

Deliverable:

- DB available.
- Schema initialized.
- Basic database test passes.

### 26.4. `guides/3_backend_api.md`

Nội dung:

- FastAPI + Mangum architecture.
- Clerk JWT.
- CORS.
- API Gateway.
- Job creation endpoint.
- Health endpoint.
- Local run vs Lambda run.

Deliverable:

- API deployed.
- Authenticated request works.
- Job row can be created in DB.

### 26.5. `guides/4_vector_ingest.md`

Nội dung:

- S3 Vectors or chosen vector store.
- Embedding model.
- Chunking strategy.
- Ingest Lambda/API.
- Search test.

Deliverable:

- A product document can be ingested.
- Search returns relevant chunks.

### 26.6. `guides/5_agents.md`

Nội dung:

- SQS architecture.
- Router/planner.
- Specialist agents.
- Retry/DLQ.
- Output validation.
- Agent trace observability.

Deliverable:

- A search job goes through SQS and worker.
- DB status updates from queued to completed.
- At least one specialist result saved.

### 26.7. `guides/6_frontend.md`

Nội dung:

- Next.js project setup.
- Clerk frontend.
- Pages/routes:
  - login.
  - search.
  - job status.
  - results.
  - comparison.
- Static export to S3.
- CloudFront.

Deliverable:

- User can log in.
- User can submit product query.
- User can view job/result.

### 26.8. `guides/7_model_services.md`

Nội dung:

- Hybrid AWS + external GPU architecture.
- Qwen/vLLM endpoint contract.
- OpenAI-compatible client.
- Timeout/retry.
- Fallback model.
- Cost control.
- Secret management.

Deliverable:

- Backend can call external model service.
- Model call is logged/traced.
- Timeout/failure is handled.

### 26.9. `guides/8_enterprise.md`

Nội dung:

- CloudWatch dashboard.
- API rate limiting.
- WAF or API Gateway throttling.
- Guardrails.
- Audit logs.
- LangFuse/OpenAI traces.
- Security checklist.
- Cost alarms.

Deliverable:

- Dashboard visible.
- Rate limit/throttle configured.
- Logs/traces visible.
- Guardrail rejects bad input.

### 26.10. `guides/architecture.md`

Nội dung:

- Overall AWS architecture.
- Request flow.
- Data flow.
- Agent flow.
- Deployment flow.
- Security boundaries.
- Cost-sensitive resources.

### 26.11. `guides/agent_architecture.md`

Nội dung:

- Router and specialists.
- Tool vs structured output rule.
- Prompt templates.
- Schemas.
- Validation.
- Failure modes.
- Human-readable explanations.

---

## 27. Plans/specs mà coding agent phải tạo hoặc cập nhật trước khi implement

Trước khi viết code production cho DATN, coding agent nên tạo hoặc cập nhật các file sau.

### 27.1. `plans/00_context.md`

Nội dung:

- Tóm tắt DATN hiện tại.
- 3 tài liệu nguồn hiện có nói gì.
- Alex patterns nào được áp dụng.
- Những gì chưa có trong DATN.
- Assumptions hiện tại.

### 27.2. `plans/01_mvp_scope.md`

Nội dung:

- MVP đầu tiên là gì.
- Recommended MVP:

```text
Authenticated user
  -> submit product search query
  -> API creates search job
  -> SQS triggers router/searcher
  -> result saved to DB
  -> Next.js frontend polls and displays result
```

Không đưa vào MVP đầu tiên:

- Full multi-source scraper.
- Fine-tuned Qwen.
- Complex price prediction.
- Payment/subscription.
- Custom domain.
- WAF nếu chưa có public load.

### 27.3. `plans/02_aws_architecture.md`

Nội dung:

- Diagram text hoặc Mermaid.
- AWS services by phase.
- Which Terraform folder creates what.
- Dependencies between folders.
- Cleanup order.
- Cost risks.

### 27.4. `plans/03_backend_architecture.md`

Nội dung:

- Backend modules.
- API endpoints.
- Job lifecycle.
- Shared package rules.
- Error handling policy.
- Retry/backoff policy.

### 27.5. `plans/04_frontend_architecture.md`

Nội dung:

- Next.js choice.
- Pages/components.
- Clerk flow.
- API client.
- Polling behavior.
- UX states:
  - idle.
  - loading.
  - queued.
  - running.
  - completed.
  - failed.

### 27.6. `plans/05_agent_architecture.md`

Nội dung:

- Agents list.
- Prompt boundaries.
- Tool contracts.
- Structured output schemas.
- Validation rules.
- Trace names.
- Failure fallback.

### 27.7. `plans/06_security_enterprise.md`

Nội dung:

- Auth/authz.
- CORS.
- Rate limiting.
- Input validation.
- Prompt injection guardrails.
- Output validation.
- Audit logging.
- Secrets handling.
- Observability.

### 27.8. `plans/07_deployment_plan.md`

Nội dung:

- Phase order.
- Per-phase commands.
- Verification after each phase.
- Rollback/cleanup.
- What requires user approval.

### 27.9. `specs/repo_structure.md`

Nội dung:

- Final folder tree.
- Ownership/responsibility of each folder.
- Which files are required in each backend module.
- Which files are required in each Terraform module.

### 27.10. `specs/api_contract.md`

Nội dung:

- Endpoint list.
- Request/response schemas.
- Auth requirements.
- Error format.
- Rate limit behavior.

### 27.11. `specs/database_schema.md`

Nội dung:

- Tables.
- Columns.
- Indexes.
- Ownership model by user.
- Job status enum.
- Audit event model.

### 27.12. `specs/job_orchestration.md`

Nội dung:

- SQS message schema.
- Job statuses.
- Retry behavior.
- DLQ handling.
- Idempotency keys.

### 27.13. `specs/vector_ingest.md`

Nội dung:

- Chunk schema.
- Metadata schema.
- Embedding model.
- Search query contract.
- Deduplication.

### 27.14. `specs/model_gateway.md`

Nội dung:

- OpenAI-compatible model endpoint contract.
- Qwen/vLLM assumptions.
- Timeout.
- Retry.
- Fallback.
- Secret names.
- Logging/tracing fields.

### 27.15. `specs/frontend_pages.md`

Nội dung:

- Route list.
- Components.
- Data fetching.
- Auth states.
- Error/loading states.

### 27.16. `specs/observability.md`

Nội dung:

- Log fields.
- Trace names.
- Metrics.
- Dashboards.
- Alarms.
- LangFuse/OpenAI traces.

### 27.17. `specs/security.md`

Nội dung:

- JWT validation.
- User ownership checks.
- CORS allowed origins.
- Rate limit rules.
- Input validation.
- Output validation.
- Secrets policy.

---

## 28. Implementation plan cho coding agent tiếp theo

Coding agent tiếp theo nên thực hiện theo thứ tự này. Không nhảy thẳng vào AWS deploy.

### Phase 0: Context load

Agent phải đọc:

- `DATN/ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md`
- `DATN/Project_Development_Plan.md`
- `DATN/DOCUMENTATION_SEARCHKEY.md`
- `DATN/DOCUMENTATION_PRICE_IS_RIGHT.md`
- `AGENTS.md` nếu có trong repo/session.
- Các README liên quan của Alex nếu cần đối chiếu.

Không đọc secrets.

### Phase 1: Documentation scaffold only

Tạo:

- `DATN/plans/`
- `DATN/specs/`
- `DATN/guides/`

Viết bản đầu của:

- `plans/00_context.md`
- `plans/01_mvp_scope.md`
- `specs/repo_structure.md`
- `guides/architecture.md`

Verify:

- Folder tree rõ ràng.
- MVP scope rõ.
- Chưa có code runtime.
- Chưa chạy Terraform.

### Phase 2: Terraform skeleton only

Tạo:

- `DATN/terraform/README.md`
- `DATN/terraform/1_foundation/`
- `DATN/terraform/2_database/`
- `DATN/terraform/3_vector_store/`
- `DATN/terraform/4_ingest/`
- `DATN/terraform/5_agents/`
- `DATN/terraform/6_frontend_api/`
- `DATN/terraform/7_model_services/`
- `DATN/terraform/8_enterprise/`

Trong mỗi folder, tối thiểu có:

- `README.md`
- `main.tf`
- `variables.tf`
- `outputs.tf`
- `terraform.tfvars.example`

Ở phase này:

- Có thể viết skeleton.
- Không cần `terraform apply`.
- Chỉ chạy format/validate nếu user cho phép.

Verify:

- Mỗi folder độc lập.
- Không có secret value.
- README nói rõ mục tiêu và outputs.

### Phase 3: Backend skeleton only

Tạo:

- `DATN/backend/README.md`
- `DATN/backend/shared/`
- `DATN/backend/database/`
- `DATN/backend/api/`
- `DATN/backend/ingest/`
- `DATN/backend/router/`
- `DATN/backend/searcher/`
- `DATN/backend/scraper/`
- `DATN/backend/comparer/`
- `DATN/backend/pricer/`
- `DATN/backend/advisor/`
- `DATN/backend/synthesizer/`

Trong mỗi folder backend service, nên có:

- `README.md`
- `pyproject.toml` nếu là uv project riêng.
- `lambda_handler.py` nếu deploy Lambda.
- `agent.py` nếu là agent.
- `templates.py` nếu dùng prompts.
- `schemas.py` nếu có structured I/O.
- `test_simple.py`
- `test_full.py` chỉ khi có AWS integration.

Verify:

- Folder responsibilities rõ.
- Không copy-paste Alex financial code nguyên xi.
- Domain đổi sang shopping/product/price.

### Phase 4: API + DB vertical slice

Implement nhỏ nhất:

- FastAPI health.
- Clerk JWT verification skeleton.
- Create user from JWT.
- Create search job.
- Get job status.
- Save job in DB.

Deploy target:

- `terraform/2_database`
- `terraform/6_frontend_api` API part.

Verify:

- `GET /health` works.
- Authenticated `POST /search-jobs` creates a DB row.
- User A cannot read User B job.

### Phase 5: SQS + one worker vertical slice

Implement:

- SQS job message.
- Router or searcher worker.
- Worker updates DB from `queued` -> `running` -> `completed`.
- Dummy deterministic result first, before real model/scraper.

Verify:

- API creates job and enqueues message.
- Worker consumes.
- DB result is visible.
- DLQ handles failures.

### Phase 6: Next.js frontend MVP

Implement:

- Next.js Pages Router or App Router, but choose one explicitly.
- Clerk login.
- Search form.
- Job status polling.
- Result display.

Recommended for Alex alignment:

- Next.js static export + S3 + CloudFront.
- Clerk frontend auth.
- API calls to `/api/*` via CloudFront behavior.

Verify:

- User logs in.
- User submits query.
- UI shows queued/running/completed.

### Phase 7: Real search/RAG/scraper

Implement:

- Product search logic.
- Ingest a small known dataset.
- Vector search.
- One allowed source scraper or static seed dataset first.

Verify:

- Query returns relevant products.
- Metadata includes source and timestamp.
- No hallucinated price/spec.

### Phase 8: External model service

Implement:

- OpenAI-compatible client for Qwen/vLLM endpoint.
- Secrets Manager config.
- Timeout/retry/backoff.
- Fallback to cheaper hosted model if configured.
- Trace each model call.

Verify:

- Model endpoint health check.
- Successful generation.
- Timeout behavior.
- Logged model name, latency, token usage if available.

### Phase 9: Enterprise hardening

Implement:

- Rate limiting.
- API Gateway throttling.
- Optional WAF.
- Guardrails.
- Output validation.
- Audit logs.
- CloudWatch dashboard.
- Alarms.
- LangFuse/OpenAI traces.

Verify:

- Bad input rejected.
- Spam requests throttled.
- Agent output schema validation catches malformed output.
- Dashboard shows API/Lambda/SQS/DB metrics.

---

## 29. Coding agent execution instructions

Phần này là instruction trực tiếp cho coding agent session mới.

### 29.1. Required first action

Trước khi sửa file:

1. Chạy `git status --short`.
2. Không reset/stage/commit thay đổi có sẵn.
3. Đọc file này.
4. Đọc 3 tài liệu DATN hiện tại.
5. Xác định user đang yêu cầu phase nào.
6. Nếu chưa rõ phase, hỏi lại trước khi implement.

### 29.2. What to implement first

Nếu user nói "bắt đầu triển khai DATN", recommended first implementation là:

1. Tạo `plans/`, `specs/`, `guides/`.
2. Viết specs/plans rõ.
3. Tạo skeleton `terraform/` chia nhỏ.
4. Tạo skeleton `backend/` chia module.
5. Chưa deploy AWS.

Lý do:

- DATN hiện có tài liệu ý tưởng và prototype logic, chưa có production structure.
- Nếu code thẳng FastAPI/Next.js/Terraform cùng lúc, debug sẽ khó.
- Alex thành công vì mỗi guide/folder có boundary rõ.

### 29.3. Required stop points

Agent phải dừng và hỏi user trước khi:

- Chạy `terraform apply`.
- Chạy deploy lên AWS.
- Tạo hoặc sửa secret files.
- Cài dependency mới.
- Build Docker image nếu Docker/environment chưa rõ.
- Gọi external GPU/API mất phí.
- Đổi architecture lớn khỏi hybrid AWS + external GPU direction.

### 29.4. Quality bar

Mỗi phase phải có:

- Scope rõ.
- Files changed rõ.
- Verify step rõ.
- Rollback/cleanup nếu có AWS.
- Không hardcode secrets.
- Không đọc/in secrets.
- Không over-engineer.

### 29.5. How to map Alex into DATN without copying blindly

Nên copy pattern, không copy domain:

```text
Alex Planner      -> DATN Router
Alex Reporter     -> DATN Synthesizer/Advisor
Alex Charter      -> DATN Comparison UI/chart/table generator
Alex Retirement   -> DATN Pricer/Deal evaluator
Alex Researcher   -> DATN Scraper/Product research service
Alex Ingest       -> DATN Product ingest
Alex Aurora schema -> DATN user/job/product/source schema
Alex S3 Vectors   -> DATN product knowledge vector index
Alex CloudFront   -> DATN frontend/API edge
Alex Clerk auth   -> DATN auth
Alex Guide 8      -> DATN enterprise/security/observability checklist
```

Không nên:

- Giữ tên financial như portfolio/instrument/retirement trong DATN.
- Dùng Bedrock nếu target là Qwen/vLLM external GPU.
- Thiết kế quá nhiều agents trước khi có one working vertical slice.
- Tạo Terraform dependency graph quá phức tạp ở MVP.

### 29.6. Expected final deliverable for first coding session

Nếu session đầu chỉ làm scaffold, expected deliverable:

- `DATN/plans/*`
- `DATN/specs/*`
- `DATN/guides/*`
- `DATN/terraform/*` skeleton
- `DATN/backend/*` skeleton
- Không có AWS resource mới.
- Không có secrets.
- User có thể mở session mới và tiếp tục implement từng guide.

---

## 30. DATN end-to-end target flow after scaffold

Luồng production mục tiêu sau khi scaffold và MVP được implement:

```text
User opens Next.js app through CloudFront
  -> Clerk authenticates user
  -> Frontend calls /api/search-jobs
  -> FastAPI verifies Clerk JWT
  -> FastAPI validates input and rate limit
  -> FastAPI creates job in Aurora
  -> FastAPI sends message to SQS
  -> Router Lambda consumes job
  -> Router decides required specialists
  -> Searcher queries product DB/vector store
  -> Scraper fetches allowed sources if needed
  -> Pricer estimates fair price/deal score
  -> Comparer ranks candidates
  -> Advisor/Synthesizer creates final answer
  -> Outputs validated against schemas
  -> Result saved to Aurora
  -> Logs/traces/audit emitted
  -> Frontend polls job status/result
  -> User sees recommendation with evidence
```

Hybrid model call path:

```text
DATN Agent Lambda
  -> model client with retry/backoff
  -> OpenAI-compatible endpoint
  -> external GPU provider running Qwen/vLLM/fine-tuned model
  -> structured output returned
  -> output validation
  -> trace/log/audit
```

Vector ingest path:

```text
Admin/internal ingest request
  -> API Gateway/API key or authenticated admin API
  -> Ingest Lambda
  -> chunk + metadata validation
  -> embedding model
  -> S3 Vectors
  -> searchable product knowledge
```

Deployment path:

```text
Guide 1: foundation
Guide 2: database
Guide 3: backend API
Guide 4: vector ingest
Guide 5: agents/SQS
Guide 6: frontend
Guide 7: external model services
Guide 8: enterprise hardening
```

Đây là architecture target. Không implement toàn bộ trong một lượt.

---

## 31. Bổ sung sau đối chiếu Alex: async job lifecycle theo `job_id`, Lambda handlers, observability, enterprise hardening

Phần này được bổ sung sau khi đối chiếu lại với Alex, đặc biệt:

- `guides/6_agents.md`
- `guides/8_enterprise.md`
- `backend/api/main.py`
- `backend/planner/lambda_handler.py`
- `backend/planner/agent.py`
- `backend/reporter/lambda_handler.py`
- `backend/charter/lambda_handler.py`
- `backend/retirement/lambda_handler.py`
- `backend/tagger/lambda_handler.py`
- `backend/database/src/models.py`
- `backend/database/src/schemas.py`
- `backend/shared/alex_shared/guardrails.py`
- `backend/shared/alex_shared/audit.py`
- `backend/planner/observability.py`

Kết luận đối chiếu: tài liệu này đã có nhắc tới SQS/job tracking, nhưng chưa đủ chi tiết ở mức "coding agent có thể implement lại". DATN phải có section/spec riêng cho `job_id` lifecycle vì đây là xương sống production của hệ thống async agents.

### 31.1. Alex async job lifecycle thực tế

Trong Alex, long-running AI analysis không chạy trực tiếp trong HTTP request. HTTP API chỉ tạo job, gửi message vào SQS, trả `job_id` cho frontend, sau đó frontend poll trạng thái job.

Luồng thực tế:

```text
Frontend
  -> POST /api/analyze
  -> FastAPI verifies Clerk JWT
  -> FastAPI creates row in jobs table with status=pending
  -> FastAPI sends SQS message containing job_id
  -> FastAPI returns job_id immediately
  -> Frontend polls GET /api/jobs/{job_id}

SQS
  -> triggers alex-planner Lambda
  -> Planner extracts job_id
  -> Planner updates jobs.status=running
  -> Planner loads job/user/portfolio context from Aurora
  -> Planner pre-processes missing instruments through Tagger
  -> Planner invokes Reporter, Charter, Retirement
  -> Specialist agents write their own payloads to jobs row
  -> Planner marks jobs.status=completed
  -> On failure, Planner marks jobs.status=failed with error_message
```

Important Alex details:

- `backend/api/main.py` endpoint `POST /api/analyze` creates the job and sends SQS message.
- `backend/api/main.py` endpoint `GET /api/jobs/{job_id}` verifies the job belongs to the current Clerk user before returning it.
- `backend/database/src/models.py` creates jobs with default `status='pending'`.
- `backend/database/src/schemas.py` defines job status as `pending`, `running`, `completed`, `failed`.
- `backend/planner/lambda_handler.py` is SQS-triggered and supports both SQS event format and direct `{ "job_id": "..." }` invocation for tests.
- `backend/planner/lambda_handler.py` updates status to `running`, then `completed`, or `failed`.
- `backend/planner/agent.py` invokes specialist Lambda functions synchronously with payload `{ "job_id": job_id }`.
- `backend/reporter/lambda_handler.py`, `backend/charter/lambda_handler.py`, and `backend/retirement/lambda_handler.py` all accept `job_id`, load missing context from DB, run agent logic, and update their specific result fields in the job row.
- `backend/tagger/lambda_handler.py` is batch-style. It receives instruments rather than a first-class job row, but still participates in the Planner pre-processing phase and emits structured logs.

### 31.2. DATN must implement the same `job_id` backbone

DATN should not let frontend wait for model/scraper/agent execution inside one HTTP call. DATN tasks can be slow:

- scraping websites,
- calling Qwen/vLLM,
- running comparison,
- estimating fair price,
- ingesting product documents,
- generating final answer.

Therefore DATN must use a job model:

```text
search_jobs or jobs table:
  id
  clerk_user_id
  job_type
  status
  request_payload
  result_payload
  error_message
  created_at
  started_at
  completed_at
```

Recommended DATN statuses:

```text
pending
queued
running
partial
completed
failed
cancelled
```

MVP can keep Alex-compatible statuses first:

```text
pending
running
completed
failed
```

Then add `queued`, `partial`, and `cancelled` later if needed.

### 31.3. DATN API job endpoints spec

DATN FastAPI should expose job endpoints equivalent to Alex:

```text
POST /api/search-jobs
GET  /api/search-jobs
GET  /api/search-jobs/{job_id}
GET  /api/search-jobs/{job_id}/results
```

Optional later:

```text
POST /api/search-jobs/{job_id}/cancel
POST /api/search-jobs/{job_id}/retry
GET  /api/search-jobs/{job_id}/events
```

`POST /api/search-jobs` should:

1. Verify Clerk JWT.
2. Extract `clerk_user_id` from verified token, not request body.
3. Validate request with Pydantic.
4. Sanitize user text with guardrails.
5. Create DB job row.
6. Send SQS message with `job_id`.
7. Return immediately:

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Search started. Poll job status for results."
}
```

`GET /api/search-jobs/{job_id}` must:

1. Verify Clerk JWT.
2. Load job by `job_id`.
3. Check `job.clerk_user_id == current_user_id`.
4. Return 403 if job belongs to another user.
5. Return job status, timing fields, and safe result summary.

This ownership check is non-negotiable. Alex already does this in `GET /api/jobs/{job_id}`.

### 31.4. DATN SQS message contract

DATN SQS message should be small and idempotent. Do not send large product data or full scraped documents through SQS.

Recommended message:

```json
{
  "job_id": "uuid",
  "clerk_user_id": "user_xxx",
  "job_type": "product_search",
  "trace_id": "optional-request-trace-id",
  "attempt": 1
}
```

Rules:

- `job_id` is the primary correlation key.
- `clerk_user_id` is useful for logging, but worker must still verify/load job from DB.
- Large payloads stay in Aurora/S3, not SQS.
- SQS message body should be JSON, but workers should tolerate raw `job_id` for direct testing, like Alex Planner.
- Workers must be idempotent: if a duplicate SQS message arrives, the worker should not create duplicate final results.

### 31.5. DATN Lambda handler pattern

Every DATN worker Lambda should follow this pattern:

```text
lambda_handler(event, context)
  -> start timer
  -> log handler start with service/model
  -> parse SQS Records or direct invocation
  -> extract job_id
  -> validate job_id exists
  -> open observability context
  -> load job from DB
  -> verify status allows processing
  -> update status/running phase if this worker owns lifecycle
  -> run agent/tool logic
  -> validate output
  -> save result to DB
  -> emit structured completion log
  -> emit audit event
  -> return small response
```

For DATN specialist workers, recommended event input:

```json
{
  "job_id": "uuid"
}
```

The worker should load all needed context from DB/S3/vector store. This keeps agent invocations simple and reduces payload coupling.

### 31.6. DATN router/planner lifecycle

The DATN router is Alex Planner equivalent.

Responsibilities:

1. Receive SQS event.
2. Extract `job_id`.
3. Update job status to `running`.
4. Log `ROUTER_STARTED`.
5. Load request payload and user preferences.
6. Decide which specialists to call:
   - `searcher`
   - `scraper`
   - `comparer`
   - `pricer`
   - `advisor`
   - `synthesizer`
7. Invoke specialist Lambdas with `{ "job_id": job_id }`.
8. Handle partial failures:
   - if non-critical scraper fails, continue with known data and mark warning;
   - if required search fails, mark job failed;
   - if model times out, retry according to retry budget.
9. Mark job `completed` only after required outputs are saved.
10. On exception, mark job `failed` and store sanitized `error_message`.

Structured logs:

```json
{
  "event": "ROUTER_STARTED",
  "job_id": "uuid",
  "user_id": "user_xxx",
  "timestamp": "iso8601",
  "job_type": "product_search",
  "model": "model-name"
}
```

```json
{
  "event": "SPECIALIST_INVOKED",
  "agent": "searcher",
  "job_id": "uuid",
  "timestamp": "iso8601"
}
```

```json
{
  "event": "ROUTER_COMPLETED",
  "job_id": "uuid",
  "duration_ms": 12345,
  "status": "success"
}
```

### 31.7. DATN specialist worker lifecycle

Each DATN specialist should mirror Alex Reporter/Charter/Retirement:

```text
Searcher
  -> accepts job_id
  -> loads query/user preferences
  -> queries vector/product DB
  -> saves candidates_payload
  -> logs SEARCHER_COMPLETED

Scraper
  -> accepts job_id
  -> loads candidate URLs/sources
  -> fetches allowed sources
  -> saves source_snapshots or product_sources
  -> logs SCRAPER_COMPLETED

Comparer
  -> accepts job_id
  -> loads candidates and snapshots
  -> creates comparison_payload
  -> validates schema
  -> logs COMPARER_COMPLETED

Pricer
  -> accepts job_id
  -> loads prices and comparable products
  -> estimates fair price/deal score
  -> saves pricing_payload
  -> logs PRICER_COMPLETED

Advisor
  -> accepts job_id
  -> loads comparison/pricing/user need
  -> generates recommendation
  -> validates output
  -> logs ADVISOR_COMPLETED

Synthesizer
  -> accepts job_id
  -> loads all specialist outputs
  -> writes final result_payload
  -> logs SYNTHESIZER_COMPLETED
```

Each specialist log should include:

- `event`
- `job_id`
- `agent`
- `model`
- `duration_ms`
- output size/count, not full sensitive payload
- success/failure status

### 31.8. Database fields for DATN job observability

DATN should add enough fields to observe a job by `job_id` from API, DB, CloudWatch, and traces.

Recommended `jobs` or `search_jobs` fields:

```text
id uuid primary key
clerk_user_id text not null
job_type text not null
status text not null
request_payload jsonb
candidates_payload jsonb
scrape_payload jsonb
comparison_payload jsonb
pricing_payload jsonb
recommendation_payload jsonb
result_payload jsonb
warnings jsonb
error_message text
created_at timestamp
started_at timestamp
completed_at timestamp
updated_at timestamp
```

Recommended `agent_runs` table:

```text
id uuid primary key
job_id uuid not null
agent_name text not null
model text
status text not null
input_hash text
output_summary jsonb
duration_ms integer
error_message text
started_at timestamp
completed_at timestamp
trace_id text
```

Recommended `audit_events` table:

```text
id uuid primary key
job_id uuid
clerk_user_id text
event_type text not null
actor_type text
actor_id text
metadata jsonb
created_at timestamp
```

Why this matters:

- Frontend can show progress by job.
- Coding agent can debug one job end-to-end.
- CloudWatch Logs Insights can filter by `job_id`.
- LangFuse/OpenAI traces can be correlated with DB state.
- Failed jobs are explainable instead of disappearing into logs.

### 31.9. CloudWatch Logs Insights queries DATN should support

Because all structured logs include `job_id`, DATN should be debuggable with queries like:

```text
fields @timestamp, event, job_id, agent, status, duration_ms, model
| filter job_id = "JOB_ID_HERE"
| sort @timestamp asc
```

```text
fields @timestamp, @message
| filter event like /FAILED|ERROR/
| sort @timestamp desc
| limit 50
```

```text
fields @timestamp, event, agent, duration_ms
| filter event like /COMPLETED/
| stats avg(duration_ms), max(duration_ms), count(*) by agent
```

```text
fields @timestamp, job_id, error_message
| filter event = "ROUTER_FAILED" or event = "WORKER_FAILED"
| sort @timestamp desc
```

DATN guides should include these queries in `guides/8_enterprise.md`.

### 31.10. Retry and DLQ behavior from Alex to DATN

Alex uses multiple retry layers:

- SQS retry and DLQ at infrastructure level.
- Tenacity retry in agent functions for model rate limits and temporary errors.
- Lambda error logging with timing.
- Job status update to `failed` when orchestration fails.

DATN should implement:

1. API should not retry long-running jobs synchronously.
2. SQS handles async retry.
3. Lambda workers use tenacity for retryable model/network errors.
4. Retry only temporary failures:
   - rate limit,
   - timeout,
   - transient external model failure,
   - temporary scraping connection failure.
5. Do not retry:
   - invalid user input,
   - unauthorized request,
   - unsupported source,
   - schema validation failure caused by deterministic bug.
6. DLQ must be monitored.
7. If message lands in DLQ, job should eventually be marked failed or surfaced in admin/debug tooling.

Recommended retry settings:

```text
model call retry:
  attempts: 3 to 5
  wait: exponential backoff
  min wait: 2 to 4 seconds
  max wait: 30 to 60 seconds
  jitter: recommended

scraper retry:
  attempts: 2 to 3
  wait: exponential backoff
  max wait: 20 seconds
  per-source timeout: strict

SQS redrive:
  max receive count: 2 to 5
  DLQ: required
```

### 31.11. Guide 8 enterprise checklist: Alex vs DATN

This is the expanded enterprise checklist DATN should inherit from Alex.

| Enterprise area | Alex implementation / guide | DATN requirement |
|---|---|---|
| Serverless scaling | Lambda, API Gateway, SQS, Aurora Serverless v2 | Keep API/agents serverless on AWS; external GPU only for heavy models |
| Async decoupling | API creates job, SQS triggers Planner | All slow DATN tasks must be job-based |
| Job correlation | `job_id` passed through Planner and specialists | Every log, trace, DB row, and audit event must include `job_id` |
| Status tracking | `pending`, `running`, `completed`, `failed` | Same for MVP; add `queued`, `partial`, `cancelled` later |
| DLQ | `alex-analysis-jobs-dlq` | Required for DATN queues |
| API auth | Clerk JWT via FastAPI dependency | Clerk JWT for every user endpoint |
| Authorization | API checks resource belongs to `clerk_user_id` | Required for every job/product/user resource |
| CORS | API Gateway + FastAPI CORS env | Prefer CloudFront same-origin `/api/*`; still configure CORS explicitly |
| Rate limiting | API Gateway throttling in Guide 8 | API Gateway throttling from MVP; WAF later if public traffic grows |
| Input guardrails | `sanitize_user_input` | Apply to search query, product preferences, user text |
| Output validation | Charter JSON validation | Validate comparer/pricer/advisor/synthesizer schemas |
| Response size limit | `truncate_response` | Apply to LLM outputs, scraped text summaries, final response |
| Retry/backoff | tenacity for rate limits/temp errors | Use tenacity for model/external HTTP/scraper calls |
| Structured logs | JSON events in agents | Every worker logs started/completed/failed with `job_id` |
| Timing logs | `[TIMING]` for phases | Track create/model/db/total durations |
| Audit logs | `AuditLogger.log_ai_decision` | Create `agent_runs` and/or `audit_events` |
| Observability | `observe()` context + LangFuse/logfire instrumentation | Optional but recommended; must degrade gracefully if not configured |
| OpenAI traces | `RunConfig(workflow_name=...)` in agent runs | Set workflow names per DATN agent |
| CloudWatch dashboard | `terraform/8_enterprise` dashboards | Add API/Lambda/SQS/DB/model dashboards |
| CloudWatch alarms | Guide 8 manual alarms | Add Terraform alarms if possible |
| Secrets | Secrets Manager/env vars, no code secrets | Use Secrets Manager for external model keys, DB creds, API keys |
| Least privilege IAM | Per-service policies | Per-Lambda role or scoped policy per module |
| XSS/CSP | Guide 8 recommends CSP | Add CSP/security headers for Next.js/CloudFront |
| WAF | Guide 8 recommended add-on | Optional after public deploy; rate-based rule first |
| GuardDuty | Guide 8 recommended add-on | Optional enterprise section, note cost |
| VPC endpoints | Guide 8 recommended add-on | Optional for high-security/cost-sensitive AWS traffic |
| Cost monitoring | Billing alerts, Cost Explorer | Required guide section; external GPU cost guardrails |

### 31.12. What is implemented in Alex vs what is only recommended

Important nuance for DATN:

- Implemented in Alex current code:
  - FastAPI + Clerk auth.
  - CORS middleware.
  - API creates DB job and sends SQS.
  - SQS triggers Planner Lambda.
  - Planner extracts `job_id` from SQS or direct event.
  - Planner updates job status.
  - Planner invokes specialist Lambdas.
  - Specialists load data by `job_id`.
  - Specialists write result payloads back to jobs row.
  - Structured JSON logs.
  - Timing logs.
  - Tenacity retry for model rate limits/temporary errors.
  - Guardrails for user input and response size.
  - Charter JSON output validation.
  - AuditLogger for AI decisions.
  - Optional LangFuse/logfire/OpenAI Agents instrumentation.
  - CloudWatch dashboards in Terraform part 8.

- Recommended in Guide 8 but not necessarily fully implemented as Terraform resources in current Alex:
  - WAF.
  - GuardDuty.
  - VPC endpoints.
  - Full Terraform-managed CloudWatch alarms.
  - Full CSP/security headers across the frontend.
  - Advanced app-level per-user rate limiting.

DATN should label these correctly in its docs:

```text
implemented_now
planned_next
optional_enterprise
```

This avoids claiming enterprise controls exist before they are actually deployed.

### 31.13. DATN observability requirements by `job_id`

DATN must make one `job_id` observable across:

1. Frontend UI.
2. FastAPI logs.
3. SQS message.
4. Router Lambda logs.
5. Specialist Lambda logs.
6. Aurora job row.
7. `agent_runs` table.
8. CloudWatch dashboard/log queries.
9. LangFuse traces.
10. OpenAI Agents traces when available.

Minimum trace/log fields:

```text
job_id
user_id or clerk_user_id
request_id
trace_id
agent_name
job_type
status
model
duration_ms
attempt
error_type
error_message_sanitized
```

Do not log:

- full JWT,
- API keys,
- raw secrets,
- payment info,
- unnecessary personal data,
- full scraped page if it can contain sensitive content.

### 31.14. DATN frontend job observability UX

DATN frontend should expose the async job model clearly.

Recommended pages/components:

```text
/search
  -> submit product search query
  -> receives job_id
  -> navigates to /jobs/{job_id}

/jobs/{job_id}
  -> polls GET /api/search-jobs/{job_id}
  -> displays status
  -> displays progress timeline
  -> displays partial warnings
  -> displays final result

/history
  -> lists user jobs
  -> links to previous results
```

Recommended status UI:

```text
pending: "Đã nhận yêu cầu"
running: "Đang phân tích"
partial: "Có kết quả một phần"
completed: "Hoàn tất"
failed: "Thất bại, có thể thử lại"
cancelled: "Đã hủy"
```

Do not hide `job_id`. For a graduation project, showing `job_id` in a debug/details panel is useful for demo:

```text
Job ID: ...
Started at: ...
Completed at: ...
Agents run: searcher, comparer, pricer, advisor
Trace: available/not configured
```

### 31.15. DATN guide additions required

Coding agent must update DATN guides to include job lifecycle explicitly.

Add to `guides/3_backend_api.md`:

- How API creates job.
- How API sends SQS message.
- How API returns `job_id`.
- How frontend polls status.
- How ownership check works.

Add to `guides/5_agents.md`:

- SQS event format.
- Direct Lambda test format.
- Router lifecycle.
- Specialist lifecycle.
- Job status transitions.
- DLQ behavior.
- How to debug one `job_id`.

Add to `guides/8_enterprise.md`:

- Structured log schema.
- CloudWatch Logs Insights queries by `job_id`.
- LangFuse/OpenAI trace correlation.
- Audit log schema.
- Rate limiting.
- Guardrails.
- Retry/backoff.
- Output validation.
- Dashboard and alarms.

### 31.16. DATN specs additions required

Coding agent must update these specs:

`specs/job_orchestration.md` must include:

- job table schema.
- SQS message schema.
- router handler contract.
- specialist handler contract.
- job status machine.
- retry and DLQ rules.
- idempotency rules.
- debugging by `job_id`.

`specs/observability.md` must include:

- structured log schema.
- required fields.
- event names.
- trace naming.
- CloudWatch queries.
- dashboard metrics.
- alert thresholds.

`specs/api_contract.md` must include:

- `POST /api/search-jobs`.
- `GET /api/search-jobs`.
- `GET /api/search-jobs/{job_id}`.
- ownership rules.
- error response schema.

`specs/database_schema.md` must include:

- `jobs` or `search_jobs`.
- `agent_runs`.
- `audit_events`.
- result payload fields by specialist.

### 31.17. DATN implementation acceptance criteria for async jobs

The first production DATN vertical slice is not complete until all these pass:

1. Authenticated user can create a search job.
2. API returns a `job_id` without waiting for long processing.
3. DB row exists with `status=pending` or `queued`.
4. SQS message contains the same `job_id`.
5. Router Lambda receives the message.
6. Router logs `ROUTER_STARTED` with `job_id`.
7. Router updates DB status to `running`.
8. One specialist worker runs with `{ "job_id": job_id }`.
9. Worker loads context from DB by `job_id`.
10. Worker writes result payload to DB.
11. Router marks job `completed`.
12. Frontend polls and displays completed result.
13. `GET /api/search-jobs/{job_id}` rejects a different user.
14. CloudWatch logs can be filtered by `job_id`.
15. If worker fails, job is marked `failed` or message reaches DLQ and is visible.

### 31.18. DATN debugging runbook by `job_id`

When a DATN job fails, coding agent should debug in this order:

1. Get the `job_id` from frontend/API response.
2. Query API `GET /api/search-jobs/{job_id}` as the same user.
3. Check DB row:
   - status,
   - error_message,
   - started_at,
   - completed_at,
   - partial payloads.
4. Check SQS:
   - messages available,
   - messages in flight,
   - approximate age,
   - DLQ count.
5. Check Router Lambda logs filtered by `job_id`.
6. Check specialist Lambda logs filtered by `job_id`.
7. Check model gateway logs/traces.
8. Check external GPU endpoint health if model call failed.
9. Check retry behavior and whether error is retryable.
10. Only then change code.

This matches the Alex debugging discipline from Guide 6 and Guide 8: reproduce, observe, identify root cause, fix one thing, verify.

### 31.19. Important caveat from Alex observability

Alex `observe()` context manager is designed to degrade gracefully:

- If LangFuse is not configured, agents still run.
- If OpenAI trace export env is absent, logs warn but execution continues.
- Traces are flushed at the end of the Lambda context.

DATN should follow the same principle:

- Observability must not be a hard dependency for core user flow.
- Missing LangFuse credentials should not fail a job.
- Trace flush should be bounded; avoid long blocking waits if it threatens Lambda timeout.
- Always keep CloudWatch structured logs as the baseline.

### 31.20. Updated instruction for coding agents

Before implementing DATN, coding agent must read this section and explicitly confirm the intended first vertical slice includes:

```text
API creates job
  -> SQS message contains job_id
  -> Router Lambda processes by job_id
  -> Specialist Lambda processes by job_id
  -> DB stores status/result by job_id
  -> Frontend polls by job_id
  -> Logs/traces/audit correlate by job_id
```

If a proposed implementation does not include this backbone, it is not aligned with Alex and should be revised before coding.
