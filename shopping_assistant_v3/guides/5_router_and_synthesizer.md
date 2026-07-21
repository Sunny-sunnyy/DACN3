# Phase 5: Router And Synthesizer

## Mục Đích

Implement assistant behavior quanh tool contracts: route Vietnamese user
requests, chạy allowed tool path, và tạo câu trả lời tiếng Việt từ structured
evidence.

## Trạng Thái Hiện Tại

Phase 5 bắt đầu sau khi job lifecycle tồn tại và mock tools đã sẵn sàng.

App có thể tạo/xử lý jobs, nhưng chưa hiểu Vietnamese user intent hoặc
synthesize final answers từ tool evidence.

Approved direction for Phase 5: dùng hybrid controlled OpenAI Agents SDK.
FastAPI, SQLite, local worker, deterministic progress, và V3 tool contracts
vẫn là orchestration source of truth. OpenAI Agents SDK chỉ được dùng như
optional model-backed runtime layer cho Router/Synthesizer sau feature flag,
không thay thế worker pipeline và không tạo free-form ReAct loop.

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
- `RunConfig` set `workflow_name`, `group_id=job_id`, và safe metadata.
- `trace_include_sensitive_data=False` theo mặc định khi tracing được bật.
- SDK tracing có thể được flush sau background job nếu implementation cần trace
  hiện nhanh trong OpenAI dashboard.
- SDK path chỉ chạy khi `ENABLE_REAL_MODEL_CALLS=true` và
  `ENABLE_AGENTS_SDK=true`.

Not allowed in Phase 5:

- expose `deal_search_tool` hoặc `price_estimator_tool` cho một LLM tự gọi tự
  do;
- dynamic LLM-generated todo list;
- free-form ReAct loop;
- handoff chain nơi specialist agent tự trả lời user cuối cùng;
- SDK sessions thay thế SQLite conversation/message persistence hiện có.

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
- Decide whether to keep `TestClient`, add the Starlette-recommended `httpx2`
  dev dependency, or move API tests to an async `httpx.AsyncClient` /
  `ASGITransport` harness.
- Do not change API test harness dependencies without explicit user approval,
  because dependency changes affect `pyproject.toml` and `uv.lock`.
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
- Trình bày Phase 5 plan.
- Chờ explicit approval.

## Implementation Order

1. Xác nhận Phase 4A report và tests pass.
2. Thêm Router schemas và fixture tests.
3. Implement deterministic Router cho common Vietnamese search queries.
4. Thêm unsupported fallback behavior.
5. Thêm Synthesizer schemas và fixture tests.
6. Implement deterministic Synthesizer từ product và estimate evidence.
7. Tạo deterministic `progress_steps` cho fixed pipeline.
8. Integrate Router -> tools -> Synthesizer vào worker path.
9. Thêm validation để product cards, progress steps, và final text được backed
   by evidence.
10. Phase 5B preflight: xác minh API test harness, AnyIO threadpool behavior,
    và Starlette/httpx warning trong môi trường sẽ dùng để verify.
11. Thêm optional OpenAI Agents SDK provider wrapper chỉ nếu user approve
    hybrid SDK scope.
12. Với SDK path, cấu hình safe `RunConfig`, disabled sensitive trace payloads,
    bounded tool/model errors, và `agent_runs` audit rows.
13. Viết Phase 5 report.

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
- Phase 5B report phải ghi rõ kết quả API test harness preflight:
  `anyio.to_thread.run_sync()`, minimal `TestClient.get()`, `tests/test_api.py`,
  và full default suite trong môi trường verify được approve.

Example:

```bash
uv run pytest <router and synthesizer tests>
uv run pytest <worker integration test>
```

Manual checks:

- Submit: `Tìm laptop gaming dưới 800 đô`.
- Xác nhận result có Vietnamese answer và product cards.
- Xác nhận không có price/URL xuất hiện trừ khi có trong tool output.
- Nếu opt-in SDK path được approve, xác nhận trace metadata có `job_id` nhưng
  không chứa raw secrets hoặc sensitive payloads.

## Report Requirements

Viết:

```text
shopping_assistant_v3/reports/phase_5_router_and_synthesizer_report.md
```

Bao gồm:

- Router strategy: deterministic, model-backed, hoặc cả hai.
- Synthesizer strategy.
- Agents SDK usage nếu có: flags, models, tracing policy, và fallback behavior.
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
- Nếu để SDK tự gọi search/pricing tools, pipeline có thể mất deterministic
  progress và khó review; Phase 5 giữ worker-owned tool order.
- Vietnamese answer quality nên cải thiện về sau, nhưng correctness từ evidence
  quan trọng hơn style trong MVP.
- Codex sandbox hiện có thể timeout với AnyIO threadpool/TestClient trong khi
  local unsandboxed tests pass. Phase 5B phải document hoặc xử lý test harness
  trước khi thêm SDK surface area.
