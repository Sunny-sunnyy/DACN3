# Phase 5A User Report - Router And Synthesizer Deterministic

## 1. Mục Tiêu

Phase 5A thay phần placeholder trong worker bằng Router và Synthesizer
deterministic.

Mục tiêu không phải gọi OpenAI Agents SDK ngay. Mục tiêu là khóa contract an
toàn trước: hệ thống hiểu câu hỏi tiếng Việt cơ bản, gọi tools theo pipeline cố
định, rồi trả lời tiếng Việt dựa trên evidence.

## 2. Vấn Đề Phase Này Giải Quyết

Trước Phase 5A, worker dùng `_normalize_query()` đơn giản để strip vài stop
words tiếng Việt và trả một câu trả lời hardcoded. Điều này đủ cho Phase 4 tool
foundation nhưng chưa giống assistant thật.

Sau Phase 5A:

- Router phân loại intent và tạo `query_en`.
- Worker gọi search/pricing tools theo quyết định của Router.
- Synthesizer tạo `answer_vi` từ product và pricing evidence.
- API trả thêm `progress_steps` và `summary_cards`.
- `agent_runs` có audit rows cho Router và Synthesizer.

## 3. Chức Năng Đã Có

Router deterministic:

- nhận message tiếng Việt;
- detect shopping intent phổ biến;
- map category Việt sang English tokens, ví dụ `dien thoai` -> `phone`;
- detect source preference `Amazon`, `BestBuy`, hoặc `All`;
- detect price phrase như `duoi 800 do` -> `under 800 dollars`;
- unsupported intent không gọi search/pricing.

Synthesizer deterministic:

- trả lời bằng tiếng Việt;
- giữ product names và giá USD từ evidence;
- tạo `summary_cards` cho từng product;
- sort cards theo discount;
- dịch warning codes sang lời nhắc tiếng Việt dễ hiểu;
- không bịa price, URL, specs, hoặc discount ngoài tool output.

Progress:

```text
route_request
search_deals
estimate_prices
synthesize_answer
```

Supported search path hoàn tất cả bốn steps. Unsupported intent sẽ skip
`search_deals` và `estimate_prices`.

## 4. Kỹ Thuật Dùng

Phase 5A dùng pure Python deterministic logic:

```text
backend/router/
backend/synthesizer/
backend/shared/progress.py
backend/worker.py
backend/api/schemas.py
```

Không thêm dependency mới. Không import OpenAI Agents SDK. `ENABLE_AGENTS_SDK`
chỉ là config placeholder cho Phase 5B.

## 5. Luồng Hoạt Động

```text
POST /api/chat-jobs
  -> create SQLite job
  -> process_job()
  -> deterministic_route(message_vi)
  -> if search_deals:
       deal_search_tool(query_en)
       price_estimator_tool(product)
     else:
       skip search/pricing
  -> deterministic_synthesize(evidence)
  -> save result_payload:
       answer_vi
       products
       warnings
       summary_cards
       progress_steps
  -> GET /api/chat-jobs/{job_id}
```

Audit:

```text
worker
router
deal_search_tool
price_estimator_tool
synthesizer
```

Failure handling đã được kiểm tra để router audit không mất nếu tool sau đó
fail và transaction bị rollback.

## 6. File Quan Trọng

```text
backend/router/deterministic.py
backend/router/schemas.py
backend/synthesizer/deterministic.py
backend/synthesizer/schemas.py
backend/shared/progress.py
backend/worker.py
backend/api/schemas.py
tests/test_router.py
tests/test_synthesizer.py
tests/test_worker.py
tests/test_api.py
```

## 7. Cách Tự Kiểm Tra

Default verification:

```bash
cd shopping_assistant_v3
uv run pytest tests/test_router.py tests/test_synthesizer.py -q --tb=short
uv run pytest tests/test_worker.py -q --tb=short
uv run pytest tests/ -q --tb=short
```

Codex verification trong sandbox:

```text
51 passed for Router/Synthesizer focused tests
28 passed for worker tests
208 passed, 18 skipped for broad suite excluding API tests
```

Codex không chạy được `tests/test_api.py` tới completion trong sandbox vì
FastAPI `TestClient` tối thiểu cũng timeout ở môi trường này. API schema bug
quan trọng nhất đã được kiểm bằng Pydantic response-model validation.

Implementer report ghi nhận full local verification:

```text
230 passed, 18 skipped
```

## 8. Giới Hạn Hiện Tại

- Router deterministic chỉ tốt cho common shopping queries; query phức tạp vẫn
  cần Phase 5B SDK provider hoặc logic sau này.
- Synthesizer là template-based, chưa linh hoạt như LLM.
- Chưa có OpenAI Agents SDK tracing hoặc guardrails runtime.
- Frontend chat chưa có; Phase 6 sẽ dùng `progress_steps` và `summary_cards`
  để render UI.

## 9. Phase Sau Sẽ Xây Tiếp Gì?

Milestone tiếp theo được phép là Phase 5B: optional OpenAI Agents SDK
Router/Synthesizer providers.

Phase 5B phải giữ deterministic Phase 5A làm default/fallback và chỉ bật SDK
khi:

```text
ENABLE_REAL_MODEL_CALLS=true
ENABLE_AGENTS_SDK=true
```

Phase 5B cũng nên xử lý hoặc document test harness issue đã thấy khi review:
trong Codex sandbox, `tests/test_api.py` timeout vì `TestClient` dùng AnyIO
threadpool cho sync endpoints; ngoài sandbox, `tests/test_api.py` và full suite
đều pass. Đây không phải blocker của Phase 5A, nhưng là preflight cần chốt
trước khi thêm SDK dependency hoặc SDK tests.

## 10. Tóm Tắt Ngắn

Phase 5A biến backend từ tool pipeline có placeholder answer thành assistant
backend có Router tiếng Việt, Synthesizer tiếng Việt, progress steps, summary
cards, và audit trail rõ ràng. Đây là nền tảng đúng để thêm optional OpenAI
Agents SDK ở Phase 5B hoặc đi tiếp frontend ở Phase 6 nếu user quyết định defer
SDK.
