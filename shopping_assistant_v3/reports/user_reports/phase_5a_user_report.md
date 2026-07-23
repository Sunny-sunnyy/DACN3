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

## 7. Cách Tự Kiểm Tra Và Chạy Code

### 7.1 Mục Tiêu Khi Chạy

Phase 5A cần chứng minh backend đã có assistant behavior deterministic:

- Router hiểu query tiếng Việt phổ biến và tạo `query_en`;
- unsupported intent không gọi search/pricing;
- worker chạy fixed pipeline và cập nhật `progress_steps`;
- Synthesizer trả `answer_vi` và `summary_cards` từ evidence;
- audit rows có worker/router/tools/synthesizer.

### 7.2 Command An Toàn

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

### 7.3 Manual Backend Flow

Chạy server local:

```bash
uv run uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

Mở terminal khác và gửi một shopping request:

```bash
curl -X POST http://127.0.0.1:8000/api/chat-jobs \
  -H "Content-Type: application/json" \
  -d '{"message":"Tìm laptop gaming dưới 800 đô","source":"All","max_results_per_source":5}'
```

Poll bằng `job_id`:

```bash
curl http://127.0.0.1:8000/api/chat-jobs/<job_id>
```

Kết quả mong đợi:

- `status` chuyển sang `completed`;
- `result.answer_vi` là tiếng Việt;
- `result.products` có product evidence;
- `result.summary_cards` có cards đã sort theo discount;
- top-level `progress_steps` có 4 step ids:
  `route_request`, `search_deals`, `estimate_prices`, `synthesize_answer`.

Unsupported request ví dụ:

```bash
curl -X POST http://127.0.0.1:8000/api/chat-jobs \
  -H "Content-Type: application/json" \
  -d '{"message":"Kể chuyện cười đi"}'
```

Kết quả mong đợi: câu fallback tiếng Việt, `search_deals` và
`estimate_prices` có status `skipped`.

### 7.4 Cách Đọc Kết Quả

- Router tests pass: intent/source/price pattern/query extraction ổn.
- Synthesizer tests pass: answer/cards/warnings không bịa data ngoài evidence.
- Worker tests pass: pipeline và audit rows ổn.
- Full local suite pass: Phase 5A không phá các phase trước.
- `tests/test_api.py` có thể timeout trong Codex sandbox do `TestClient`/AnyIO,
  nhưng đã pass ngoài sandbox theo implementer report. Nếu máy bạn cũng timeout,
  ưu tiên đọc focused worker/router/synth tests và thử manual backend flow.

### 7.5 Notebook Companion

Notebook tương ứng:

```text
shopping_assistant_v3/reports/notebooks/phase_5a_router_synthesizer.ipynb
```

Notebook này gọi `deterministic_route()`, `deterministic_synthesize()`, và
progress builder trực tiếp để bạn thấy contract trước khi chạy worker tests.

### 7.6 Lỗi Thường Gặp

- Query tiếng Việt quá lạ: deterministic Router có thể trả unsupported hoặc
  query chưa đẹp; Phase 5B SDK provider sẽ cải thiện chuyện này.
- Mong đợi LLM style answer: Phase 5A là template deterministic, ưu tiên
  correctness hơn văn phong.
- `summary_cards` rỗng: kiểm tra search fixture có match query không.
- Test API timeout trong sandbox: không tự đổi dependency/test harness nếu chưa
  có Phase 5B approval.

### 7.7 Safety Notes

Phase 5A không import OpenAI Agents SDK và không gọi model. Giữ
`ENABLE_REAL_MODEL_CALLS=false` và `ENABLE_AGENTS_SDK=false` cho default
verification.

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
