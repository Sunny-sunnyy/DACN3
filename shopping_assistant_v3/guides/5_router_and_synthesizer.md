# Phase 5: Router And Synthesizer

## Mục Đích

Implement assistant behavior quanh tool contracts: route Vietnamese user
requests, chạy allowed tool path, và tạo câu trả lời tiếng Việt từ structured
evidence.

## Trạng Thái Hiện Tại

Phase 5 bắt đầu sau khi job lifecycle tồn tại và mock tools đã sẵn sàng.

Phase 5A đã được approve. App hiện có deterministic Vietnamese Router,
deterministic evidence-based Vietnamese Synthesizer, fixed `progress_steps`,
`summary_cards`, unsupported-intent fallback, và `agent_runs` audit rows cho
Router/Synthesizer.

Approved direction for Phase 5: dùng hybrid controlled OpenAI Agents SDK.
FastAPI, SQLite, local worker, deterministic progress, và V3 tool contracts
vẫn là orchestration source of truth. OpenAI Agents SDK chỉ được dùng như
optional model-backed runtime layer cho Router/Synthesizer sau feature flag,
không thay thế worker pipeline và không tạo free-form ReAct loop.

Approved direction for Phase 5B: thêm OpenAI Agents SDK provider thật cho
Router/Synthesizer, nhưng giữ Phase 5A deterministic path làm default và
fallback. Phase 5B dùng OpenAI dashboard tracing qua `RunConfig` và V3
`agent_runs` summary; chưa thêm custom `TracingProcessor` hoặc trace-events API.

## Scope

Implement:

- Router schemas.
- deterministic/mock Router behavior.
- optional OpenAI Agents SDK Router provider sau opt-in config.
- Vietnamese Synthesizer schemas.
- deterministic/mock Synthesizer behavior từ evidence.
- optional OpenAI Agents SDK Synthesizer provider sau opt-in config.
- unsupported intent fallback.
- deterministic `progress_steps` contract cho backend response, dùng fixed
  shopping pipeline steps thay vì LLM-generated todo list.
- validation để final answers không bịa price/spec/URL fields.
- `agent_runs` audit records cho Router và Synthesizer.
- safe tracing metadata correlated bằng `job_id` khi Agents SDK path được bật.

Phase 5A đã implement deterministic/default path. Phase 5B chỉ implement phần
optional SDK provider, fallback, tracing metadata, test harness preflight, và
opt-in smoke tests.

## Non-Goals

- Không free-form ReAct loop.
- Không compare/advisor execution.
- Không frontend implementation.
- Không default paid model calls.
- Không live scraping/model calls trong tests.
- Không để OpenAI Agents SDK tự quyết định search/pricing tool loop trong MVP.
- Không dùng handoffs hoặc agents-as-tools để thay thế fixed
  `Router -> tools -> Synthesizer` pipeline trong Phase 5.

## Inputs From Previous Phases

Required:

- Phase 3 async jobs.
- Phase 4A mock tools.
- `guides/agent_architecture.md`.

Recommended:

- Phase 4B/4C real tools có thể chưa có; mock tools là đủ cho phase này.

## Contracts

### Router Input

```json
{
  "message_vi": "Tìm laptop gaming dưới 800 đô",
  "conversation_context": []
}
```

### Router Output

```json
{
  "intent": "search_deals",
  "query_en": "gaming laptop under 800 dollars",
  "source": "All",
  "max_results_per_source": 5,
  "confidence": 0.9,
  "needs_tool": true
}
```

MVP chỉ thực thi:

```text
search_deals
```

Các intents khác trả về safe Vietnamese fallback.

### Synthesizer Input

```json
{
  "message_vi": "Tìm laptop gaming dưới 800 đô",
  "products": [],
  "price_estimates": [],
  "warnings": []
}
```

### Synthesizer Output

```json
{
  "answer_vi": "Mình tìm được vài lựa chọn đáng chú ý...",
  "summary_cards": [],
  "warnings_vi": []
}
```

Quy tắc:

- trả lời bằng tiếng Việt;
- preserve USD;
- preserve English product names khi rõ hơn;
- nhắc source/tool warnings nếu liên quan;
- không bao giờ bịa fields không được tools cung cấp.

### Progress Steps Contract

Phase 5 thêm deterministic Sidekick-style planning/progress vào job response.
Đây là fixed pipeline plan, không phải free-form autonomous to-do list.

Initial minimal contract:

```json
{
  "progress_steps": [
    {
      "step_id": "route_request",
      "title_vi": "Hiểu nhu cầu mua sắm",
      "status": "completed",
      "detail_vi": "Đã xác định yêu cầu và tạo truy vấn tìm kiếm."
    }
  ]
}
```

Allowed `step_id` values:

```text
route_request
search_deals
estimate_prices
synthesize_answer
```

Allowed `status` values:

```text
pending
running
completed
failed
skipped
```

Future optional fields, chỉ thêm sau khi minimal contract ổn:

```text
component
started_at
completed_at
warnings
agent_run_id
```

`progress_steps` phải phản ánh actual orchestration state. Không mark một step
`completed` nếu evidence tương ứng chưa tồn tại.

### OpenAI Agents SDK Boundary

Phase 5 dùng OpenAI Agents SDK theo kiểu controlled island, không phải main
orchestrator tự do.

Allowed SDK usage:

- Router Agent tạo structured `RouterOutput`.
- Synthesizer Agent tạo structured `SynthesizerOutput`.
- `RunConfig` set `workflow_name`, `group_id=job_id`, safe `trace_metadata`,
  và `trace_include_sensitive_data=False`.
- SDK tracing dùng OpenAI dashboard trace trong Phase 5B.
- SDK path chỉ chạy khi `ENABLE_REAL_MODEL_CALLS=true` và
  `ENABLE_AGENTS_SDK=true`.
- SDK path yêu cầu explicit model IDs: `MODEL_ID_ROUTER` và
  `MODEL_ID_SYNTHESIZER`.
- `openai-agents` là optional dependency extra `[agents]`, không nằm trong
  base dependencies.
- SDK provider failures fallback sang deterministic provider và ghi bounded
  warnings.
- `agent_runs` phải ghi rõ provider identity. Khi SDK fallback xảy ra, audit
  nên có một SDK attempt row `failed` và một deterministic fallback row
  `completed`.

Not allowed in Phase 5:

- expose `deal_search_tool` hoặc `price_estimator_tool` cho một LLM tự gọi tự
  do;
- dynamic LLM-generated todo list;
- free-form ReAct loop;
- handoff chain nơi specialist agent tự trả lời user cuối cùng;
- SDK sessions thay thế SQLite conversation/message persistence hiện có.
- custom `TracingProcessor` trong Phase 5B;
- trace-events API endpoint trong Phase 5B.

Recommended implementation shape:

```text
worker
-> deterministic progress state
-> Router provider (deterministic default, SDK optional)
-> existing deal_search_tool
-> existing price_estimator_tool
-> Synthesizer provider (deterministic default, SDK optional)
-> evidence validation
-> save result/progress/audit rows
```

OpenAI Agents SDK dependency must be optional until user explicitly approves
install/runtime model calls. Default import path should not require the package
unless the SDK feature flag is enabled or SDK-specific tests are running.

Phase 5B provider selection:

```text
default:
  deterministic Router/Synthesizer
  no OpenAI calls
  no Agents SDK import requirement

sdk enabled:
  ENABLE_REAL_MODEL_CALLS=true
  ENABLE_AGENTS_SDK=true
  MODEL_ID_ROUTER set for Router SDK path
  MODEL_ID_SYNTHESIZER set for Synthesizer SDK path
```

Phase 5B fallback warning grammar:

```text
router_sdk_fallback_used:<reason>
synthesizer_sdk_fallback_used:<reason>
```

Initial reason:

```text
sdk_error
```

Warnings must be bounded and must not include raw exceptions, stack traces,
payloads, API keys, tokens, or request headers.

### Phase 5B Test Harness Preflight

Before implementing optional SDK providers in Phase 5B, explicitly handle the
API test harness issue observed during Codex review:

```text
In the Codex sandbox, tests/test_api.py timed out because FastAPI/Starlette
sync endpoints use AnyIO threadpool execution, and anyio.to_thread.run_sync()
also timed out in that sandbox. The same API tests passed outside the sandbox:
22 passed for tests/test_api.py and 230 passed, 18 skipped for the full default
suite.
```

This is not a Phase 5A runtime blocker, but Phase 5B must not ignore it because
SDK integration will add more async/model-provider surface area.

Phase 5B preflight requirements:

- Reproduce `anyio.to_thread.run_sync()` and `fastapi.testclient.TestClient`
  behavior in the target environment before adding SDK code.
- Keep default API tests mock-only and free of OpenAI/Modal/live scraping.
- Phase 5B approved strategy is to keep the existing API test harness unless
  preflight proves it cannot be used in the verification environment. Do not
  add `httpx2` or migrate API tests to `httpx.AsyncClient` / `ASGITransport`
  without separate explicit user approval, because that changes test
  dependencies and scope.
- Document verification evidence in the Phase 5B report, including whether
  tests were run inside Codex sandbox, outside sandbox, or both.

## Workflow Gate

Trước khi code:

- Load `using-superpowers`.
- Dùng `brainstorming` với user.
- Chỉ hỏi các câu thay đổi scope, design, tests, hoặc implementation plan.
- Xác nhận deterministic-only hay hybrid controlled OpenAI Agents SDK path nằm
  trong scope.
- Nếu dùng Agents SDK, xác nhận feature flags, optional dependency strategy,
  tracing policy, và no-sensitive-data policy.
- Xác nhận Phase 5B test harness strategy cho `tests/test_api.py`,
  `TestClient`/AnyIO threadpool behavior, và Starlette/httpx warning trước khi
  thêm SDK dependency hoặc SDK tests.
- Với Phase 5B, confirmed scope là:
  `openai-agents` optional extra `[agents]`, OpenAI dashboard trace only,
  deterministic fallback, opt-in real smoke tests, và không custom
  `TracingProcessor`.
- Trình bày Phase 5 plan.
- Chờ explicit approval.

## Implementation Order

1. Phase 5A: Thêm Router schemas và deterministic Router tests.
2. Phase 5A: Implement deterministic Router cho common Vietnamese search
   queries và unsupported fallback.
3. Phase 5A: Thêm Synthesizer schemas và deterministic Synthesizer tests.
4. Phase 5A: Implement deterministic Synthesizer từ product/estimate evidence.
5. Phase 5A: Tạo deterministic `progress_steps` cho fixed pipeline.
6. Phase 5A: Integrate Router -> tools -> Synthesizer vào worker path.
7. Phase 5A: Thêm validation để product cards, progress steps, và final text
   được backed by evidence.
8. Phase 5B: Preflight API test harness, AnyIO threadpool behavior, và
   Starlette/httpx warning trong môi trường verify.
9. Phase 5B: Thêm optional `[agents]` dependency cho `openai-agents`.
10. Phase 5B: Thêm Router provider boundary và lazy SDK Router provider.
11. Phase 5B: Thêm Synthesizer provider boundary, lazy SDK Synthesizer provider,
    và evidence validation hẹp cho SDK output.
12. Phase 5B: Integrate provider wrappers vào worker, preserving deterministic
    default/fallback.
13. Phase 5B: Với SDK path, cấu hình safe `RunConfig`,
    `trace_include_sensitive_data=False`, bounded tool/model errors, và
    `agent_runs` audit rows.
14. Phase 5B: Thêm mock-only SDK provider tests và opt-in real SDK smoke tests.
15. Viết phase/milestone report.

## Verification

Default required tests:

- Vietnamese query route tới `search_deals`.
- Router tạo English query.
- unsupported query trả về fallback.
- Synthesizer trả về Vietnamese answer từ fixtures.
- Synthesizer preserve warnings.
- `progress_steps` trả về fixed steps với status hợp lệ.
- Completed progress steps chỉ xuất hiện khi matching evidence tồn tại.
- Worker hoàn thành với Router/tools/Synthesizer mock path.
- Không default test nào gọi OpenAI hoặc live scraping.
- Default tests pass khi `openai-agents` chưa được cài, nếu dependency được giữ
  optional.
- Agents SDK tests dùng fake/stub runner hoặc bị skip mặc định nếu cần package
  thật.
- Phase 5B SDK provider unit tests phải mock/fake `Agent`, `RunConfig`, và
  runner path để không yêu cầu cài `[agents]` trong default suite.
- Real SDK smoke tests phải skip mặc định. Chỉ chạy khi
  `ENABLE_REAL_MODEL_CALLS=true`, `ENABLE_AGENTS_SDK=true`, `OPENAI_API_KEY`
  tồn tại, và relevant model id được set.
- Real SDK smoke tests không được live scrape Amazon/BestBuy.
- Phase 5B report phải ghi rõ kết quả API test harness preflight:
  `anyio.to_thread.run_sync()`, minimal `TestClient.get()`, `tests/test_api.py`,
  và full default suite trong môi trường verify được approve.

Example:

```bash
uv run pytest <router and synthesizer tests>
uv run pytest <worker integration test>
uv run pytest tests/test_agents_sdk_providers.py -q --tb=short
uv run pytest tests/test_real_agents_sdk.py -q --tb=short
```

Manual checks:

- Submit: `Tìm laptop gaming dưới 800 đô`.
- Xác nhận result có Vietnamese answer và product cards.
- Xác nhận không có price/URL xuất hiện trừ khi có trong tool output.
- Nếu opt-in SDK path được approve, xác nhận trace metadata có `job_id` nhưng
  không chứa raw secrets hoặc sensitive payloads.

## Report Requirements

Viết theo milestone:

```text
shopping_assistant_v3/reports/phase_5a_router_and_synthesizer_report.md
shopping_assistant_v3/reports/phase_5b_agents_sdk_router_synthesizer_report.md
```

Bao gồm:

- Router strategy: deterministic, model-backed, hoặc cả hai.
- Synthesizer strategy.
- Agents SDK usage nếu có: flags, models, tracing policy, và fallback behavior.
- Agents SDK dependency strategy: optional `[agents]`, not base dependency.
- Trace strategy: OpenAI dashboard trace through `RunConfig`; no custom
  `TracingProcessor` in Phase 5B.
- API test harness decision: giữ `TestClient`, thêm `httpx2`, hoặc chuyển sang
  async ASGI tests; kèm verification evidence và lý do.
- model calls đã thực hiện, nếu có.
- validation evidence.
- unsupported intent behavior.
- progress_steps contract và tests.
- remaining hallucination risks.

## Risks And Open Questions

- Deterministic Router có thể quá limited, nhưng an toàn hơn cho mock MVP.
- OpenAI Agents SDK Router/Synthesizer yêu cầu paid/local provider risk
  management.
- SDK tracing mặc định có thể capture model/tool inputs/outputs; Phase 5 phải
  disable sensitive trace payloads hoặc document explicit opt-in debugging.
- Phase 5B deliberately defers custom trace processors and local trace event
  API. Phase 6/7 may use existing `agent_runs` first, then add richer trace
  event persistence only after UI/evaluator requirements are clear.
- Nếu để SDK tự gọi search/pricing tools, pipeline có thể mất deterministic
  progress và khó review; Phase 5 giữ worker-owned tool order.
- Vietnamese answer quality nên cải thiện về sau, nhưng correctness từ evidence
  quan trọng hơn style trong MVP.
- Codex sandbox hiện có thể timeout với AnyIO threadpool/TestClient trong khi
  local unsandboxed tests pass. Phase 5B phải document hoặc xử lý test harness
  trước khi thêm SDK surface area.
