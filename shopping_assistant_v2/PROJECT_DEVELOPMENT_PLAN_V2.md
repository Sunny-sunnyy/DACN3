# Project Development Plan V2: Vietnamese-Speaking US Deal Assistant

**Date:** 2026-07-15  
**Status:** Planning and specification stage  
**Scope:** DATN/CV-ready local-first assistant  
**Replaces:** `segment4/mo_ta_du_an/Project_Development_Plan.md` as the active V2 direction  
**Does not modify:** `segment4/` prototype code

## 1. Why V2 Exists

The original plan focused on building a Vietnamese shopping assistant for Vietnamese e-commerce, including Vietnamese data collection, Vietnamese pricing models, and Vietnamese marketplace scraping.

After experiments, text-only Vietnamese price prediction did not perform well enough to justify making it the project core. The current best Vietnamese model is competitive for research, but the English `segment4/search_key.py` pipeline is more practical for a working demo because it already combines:

- Amazon and BestBuy search/scraping.
- GPT-based deal selection.
- Ensemble price estimation.
- ChromaDB RAG.
- Fine-tuned specialist model.
- Local DNN model.
- Gradio working prototype.

V2 pivots from "Vietnamese marketplace pricing-first" to:

```text
Vietnamese-speaking assistant
using US Amazon/BestBuy search and English ensemble pricing
with Vietnamese explanation and UX.
```

This is more realistic for a graduation project and stronger for a CV/demo because it prioritizes a working, explainable, agentic application over more model training experiments.

## 2. Product Positioning

The product is a Vietnamese-speaking US deal assistant.

Users interact in Vietnamese. The assistant can:

- Answer natural Vietnamese product questions.
- Search Amazon and BestBuy when the user asks for products or deals.
- Estimate fair product value using the existing English ensemble pipeline.
- Explain results in Vietnamese.
- Show product cards with source, sale price, estimated value, discount, and URL.
- Later compare products and provide buying advice.

The product is not initially a Vietnamese-market shopping assistant. Vietnamese e-commerce scraping and Vietnamese price modeling are out of scope for the first working version.

## 3. Core Architecture

V2 is a new app under `shopping_assistant_v2/`.

`segment4/` is kept as the legacy/prototype reference. Logic from `segment4` should be extracted or adapted into V2 modules only after a focused migration plan is approved.

Target architecture:

```text
Next.js frontend
  -> FastAPI backend
  -> SQLite local database
  -> async job lifecycle
  -> controlled Router
  -> deal_search_tool
  -> price_estimator_tool
  -> Vietnamese Synthesizer
  -> structured response for frontend cards
```

## 4. MVP Vertical Slice

The first working vertical slice must prove the full product loop:

```text
User asks in Vietnamese:
"Tìm laptop gaming dưới 800 đô"

Frontend:
creates a chat job and polls status

Backend:
returns job_id immediately

Router:
classifies intent as search_deals

Tools:
search Amazon/BestBuy and estimate fair prices

Synthesizer:
returns a Vietnamese answer

Frontend:
renders answer and product cards
```

Required MVP capabilities:

- Chat-first Next.js UI.
- FastAPI local backend.
- SQLite persistence.
- Async `job_id` lifecycle.
- Controlled Router, not free-form ReAct.
- Search and pricing tool contracts.
- Vietnamese final answer.
- Product result cards.
- Structured logs with `job_id`.

## 5. Future Capabilities

After the MVP is stable:

- Product comparison.
- Buying advisor.
- Clerk auth.
- Supabase/Postgres option.
- Postgres/Aurora migration readiness.
- AWS deployment.
- More sources if justified.
- Better UI/UX based on research.
- Optional local Qwen/vLLM provider through LiteLLM.

## 6. Phases

### Phase 0: Context Load

Goal: understand the repo and preserve existing work.

Tasks:

- Read current docs and this plan.
- Check `git status --short`.
- Check CodeGraph for `segment4`.
- Do not modify `segment4`.

Exit criteria:

- Agent can explain the V2 pivot.
- Agent knows `segment4` is reference-only.

### Phase 1: Documentation Foundation

Goal: create detailed plans/specs/guides before runtime code.

Tasks:

- Create `plans/`, `specs/`, `guides/`, `docs/`.
- Define contracts for backend, frontend, agents, tools, database, logging, testing.
- Make files detailed enough for other coding agents to implement.

Exit criteria:

- Every implementation phase has a guide.
- Every tool/agent/API/database concept has a spec.
- No runtime code is required yet.

### Phase 2: Local App Foundation

Goal: build a local production-style skeleton.

Tasks:

- Create Next.js frontend.
- Create FastAPI backend.
- Create SQLite schema and repository.
- Implement `POST /api/chat-jobs`.
- Implement `GET /api/chat-jobs/{job_id}`.
- Implement local worker with deterministic/mock output.
- Add structured console logs.

Exit criteria:

- User submits Vietnamese message.
- Backend returns `job_id`.
- Frontend polls job status.
- Job completes with mock product cards.

### Phase 3: Extract Search And Pricing Tools

Goal: reuse the working `segment4` behavior in V2.

Tasks:

- Extract/adapt Amazon and BestBuy search logic.
- Extract/adapt unified deal representation.
- Extract/adapt ensemble price estimation.
- Keep V2 tool interfaces clean.
- Add fixture-based tests before real network/model tests.

Exit criteria:

- `deal_search_tool` returns normalized candidates.
- `price_estimator_tool` returns estimated fair value in USD.
- `segment4` remains unchanged.

### Phase 4: Router And Synthesizer

Goal: make the app feel like a Vietnamese assistant.

Tasks:

- Implement controlled Router with LiteLLM/OpenAI default.
- Implement Vietnamese Synthesizer.
- Validate structured outputs.
- Add fallback for unsupported intents.

Exit criteria:

- Vietnamese search requests trigger tools.
- Final response is natural Vietnamese.
- No model hallucinated price/spec is accepted without tool evidence.

### Phase 5: Demo Hardening

Goal: make the project presentable for DATN/CV.

Tasks:

- Improve UI polish.
- Add debug log panel.
- Add test fixtures.
- Add demo script.
- Document known limitations.

Exit criteria:

- Local demo runs reliably.
- README and guides explain how to run and debug.
- Core flow has tests.

### Later Phases

- Compare Agent.
- Advisor Agent.
- Clerk auth.
- Supabase/Postgres.
- AWS deployment.
- Observability dashboards.

## 7. Backend Direction

Backend should be modular:

```text
backend/
├── shared/
├── database/
├── api/
├── router/
├── tools/
│   ├── deal_search/
│   └── price_estimator/
├── synthesizer/
├── comparer/
└── advisor/
```

Rules:

- Shared code must not depend on specific agents.
- Every module must have clear input/output contracts.
- Tools should be deterministic wrappers around external capability.
- Model calls should be behind configurable provider interfaces.
- No secrets in logs.

## 8. Frontend Direction

Frontend should be chat-first:

```text
frontend/
├── app/ or pages/
├── components/
├── lib/
└── README.md
```

MVP UI:

- Chat input in Vietnamese.
- Job status indicator.
- Assistant answer in Vietnamese.
- Product cards.
- Optional debug/log panel.

UI/UX details are intentionally not frozen. They should be researched after backend contracts are clear.

## 9. Persistence Direction

MVP default:

- SQLite.
- Fake `demo_user`.
- Postgres-compatible schema style.

Future:

- Supabase as optional local/managed Postgres research path.
- Clerk auth.
- Aurora/Postgres if AWS deployment is pursued.

Core tables:

- `jobs`
- `conversations`
- `messages`
- `agent_runs`
- `products`
- `price_estimates`

## 10. Agent And Tool Direction

MVP uses controlled Router plus explicit tools.

No free-form ReAct loop in the first MVP.

Agent/tool roles:

- Router: classify intent and choose allowed path.
- Deal Search Tool: search Amazon/BestBuy and normalize products.
- Price Estimator Tool: estimate USD fair value through English ensemble.
- Synthesizer: produce Vietnamese user-facing answer.
- Comparer: later.
- Advisor: later.

Default model provider:

- LiteLLM abstraction.
- OpenAI default for MVP stability.
- Qwen/vLLM optional later.

## 11. Testing Strategy

Default tests should avoid paid model calls and live scraping.

Required test categories:

- Unit tests for request validation.
- Unit tests for job status transitions.
- Unit tests for Router fixtures.
- Unit tests for tool contracts with mocked data.
- Integration test for local job lifecycle.
- Frontend smoke test.
- Manual opt-in real network/model test.

## 12. Multi-Agent Collaboration Workflow

Recommended roles:

- Implementer agent: writes code for one approved phase.
- Reviewer/architect agent: reviews the implementation report and code when needed.
- User: product owner and final decision maker.

Workflow per phase:

1. Implementer reads the prompt, plans, specs, and guides.
2. Implementer brainstorms with the user before coding.
3. Implementer executes only the approved phase.
4. Implementer writes a report in `reports/` using `reports/TEMPLATE_IMPLEMENTATION_REPORT.md`.
5. Reviewer reads the report first.
6. Reviewer inspects code/files when needed.
7. Reviewer returns blocker/major/minor findings.
8. Implementer fixes issues.
9. Reviewer approves the phase.
10. Reviewer updates relevant `.md` files to reflect what was actually implemented.
11. User decides when to commit/push.

Documentation update rule:

- If implementation changes an API, schema, folder structure, tool behavior, phase status, verification command, or known risk, update the relevant docs/specs/guides after reviewer approval.
- Do not claim a feature is complete in docs unless implementation and verification prove it.

## 13. Risks And Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Amazon/BestBuy scraping breaks | Core demo fails | Use fixtures/mocks, isolate scraper, support source-specific warnings |
| Model/API cost | Unexpected spend | Mock by default, opt-in real tests only |
| Scope grows too large | Project stalls | MVP only search + price + Vietnamese summary |
| Frontend waits too long | Bad UX | Async job polling from start |
| Hallucinated prices/specs | User trust issue | Tool evidence required, schema validation |
| Segment4 coupling | V2 becomes messy | Extract/adapt clean modules, keep segment4 read-only |

## 14. Out Of Scope For MVP

- Vietnamese marketplace scraping.
- New Vietnamese price model training.
- AWS deployment.
- Clerk auth.
- Payment/subscription.
- Mobile app.
- Complex personalization.
- Full product review analysis.

## 15. Success Criteria

The V2 MVP succeeds when:

- A Vietnamese user can request a product/deal.
- The app returns a `job_id` immediately.
- The frontend shows job progress.
- The backend runs search/pricing through V2 tool interfaces.
- The final answer is Vietnamese.
- Product cards contain USD sale price, estimated value, discount, source, and URL.
- Logs can be traced by `job_id`.
- The project is understandable from plans/specs/guides without reading all source code.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
