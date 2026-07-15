# Plan 01: MVP Scope

## Purpose

Define the smallest useful version of the V2 assistant.

## MVP Goal

Build a local app where a Vietnamese user can ask for product deals, and the assistant returns Amazon/BestBuy deal results with USD prices and Vietnamese explanation.

## MVP Flow

```text
User enters Vietnamese product request
-> frontend creates chat job
-> backend returns job_id
-> local worker processes job
-> router chooses search_deals path
-> deal_search_tool finds candidates
-> price_estimator_tool estimates fair value
-> synthesizer writes Vietnamese answer
-> frontend renders answer and product cards
```

## Must-Have Capabilities

- Next.js chat-first frontend.
- FastAPI backend.
- SQLite persistence.
- Async job lifecycle.
- `demo_user` identity.
- Controlled Router.
- Deal search tool contract.
- Price estimator tool contract.
- Vietnamese Synthesizer.
- Structured logs with `job_id`.
- Fixture/mock test mode.

## Should-Have Capabilities

- Debug log panel in frontend.
- Source filter: `All`, `Amazon`, `BestBuy`.
- Configurable max results per source.
- Product cards sorted by discount.
- Warning display for partial failures.

## Later Capabilities

- Product comparison.
- Buying advisor.
- Clerk auth.
- Supabase/Postgres.
- AWS deployment.
- More sources.
- UI/UX polish after research.

## Non-Goals

- No Vietnamese marketplace scraping.
- No new Vietnamese model training.
- No AWS deployment.
- No auth in the first local MVP.
- No free-form ReAct loop.
- No payment/subscription.
- No production scraper scaling.

## Success Criteria

- One local command starts backend.
- One local command starts frontend.
- User submits Vietnamese message.
- Job status is visible.
- Final answer is Vietnamese.
- Product cards include source, title, sale price USD, estimated value USD, discount USD, URL.
- Backend logs include `job_id`.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
