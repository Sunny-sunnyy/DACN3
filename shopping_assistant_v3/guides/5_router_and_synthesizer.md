# Phase 5: Router And Synthesizer

## Mục Đích

Implement assistant behavior quanh tool contracts: route Vietnamese user
requests, chạy allowed tool path, và tạo câu trả lời tiếng Việt từ structured
evidence.

## Trạng Thái Hiện Tại

Phase 5 bắt đầu sau khi job lifecycle tồn tại và mock tools đã sẵn sàng.

App có thể tạo/xử lý jobs, nhưng chưa hiểu Vietnamese user intent hoặc
synthesize final answers từ tool evidence.

## Scope

Implement:

- Router schemas.
- deterministic/mock Router behavior.
- optional LiteLLM/OpenAI Router provider sau opt-in config.
- Vietnamese Synthesizer schemas.
- deterministic/mock Synthesizer behavior từ evidence.
- optional model-backed Synthesizer sau opt-in config.
- unsupported intent fallback.
- validation để final answers không bịa price/spec/URL fields.
- `agent_runs` audit records cho Router và Synthesizer.

## Non-Goals

- Không free-form ReAct loop.
- Không compare/advisor execution.
- Không frontend implementation.
- Không default paid model calls.
- Không live scraping/model calls trong tests.

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
  "max_results_per_source": 6,
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

## Workflow Gate

Trước khi code:

- Load `using-superpowers`.
- Dùng `brainstorming` với user.
- Chỉ hỏi các câu thay đổi scope, design, tests, hoặc implementation plan.
- Xác nhận model-backed Router/Synthesizer có được phép hay chỉ mock-only.
- Trình bày Phase 5 plan.
- Chờ explicit approval.

## Implementation Order

1. Xác nhận Phase 4A report và tests pass.
2. Thêm Router schemas và fixture tests.
3. Implement deterministic Router cho common Vietnamese search queries.
4. Thêm unsupported fallback behavior.
5. Thêm Synthesizer schemas và fixture tests.
6. Implement deterministic Synthesizer từ product và estimate evidence.
7. Integrate Router -> tools -> Synthesizer vào worker path.
8. Thêm validation để product cards và final text được backed by evidence.
9. Chỉ thêm optional model provider wrapper nếu user approve paid/local provider
   behavior.
10. Viết Phase 5 report.

## Verification

Default required tests:

- Vietnamese query route tới `search_deals`.
- Router tạo English query.
- unsupported query trả về fallback.
- Synthesizer trả về Vietnamese answer từ fixtures.
- Synthesizer preserve warnings.
- Worker hoàn thành với Router/tools/Synthesizer mock path.
- Không default test nào gọi OpenAI hoặc live scraping.

Example:

```bash
uv run pytest <router and synthesizer tests>
uv run pytest <worker integration test>
```

Manual checks:

- Submit: `Tìm laptop gaming dưới 800 đô`.
- Xác nhận result có Vietnamese answer và product cards.
- Xác nhận không có price/URL xuất hiện trừ khi có trong tool output.

## Report Requirements

Viết:

```text
shopping_assistant_v3/reports/phase_5_router_and_synthesizer_report.md
```

Bao gồm:

- Router strategy: deterministic, model-backed, hoặc cả hai.
- Synthesizer strategy.
- model calls đã thực hiện, nếu có.
- validation evidence.
- unsupported intent behavior.
- remaining hallucination risks.

## Risks And Open Questions

- Deterministic Router có thể quá limited, nhưng an toàn hơn cho mock MVP.
- Model-backed Router/Synthesizer yêu cầu paid/local provider risk management.
- Vietnamese answer quality nên cải thiện về sau, nhưng correctness từ evidence
  quan trọng hơn style trong MVP.
