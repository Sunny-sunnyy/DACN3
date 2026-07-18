# Phase 8: Production Roadmap

## Mục Đích

Document production path sau khi local MVP ổn định. Phase này là planning và
hardening roadmap, không mặc định là deployment phase.

## Trạng Thái Hiện Tại

Production work không được bắt đầu cho tới khi:

- local MVP hoạt động;
- tests pass;
- demo script tồn tại;
- known failure modes được documented;
- user explicitly approves production work.

## Scope

Plan future work cho:

- Clerk auth.
- Postgres/Supabase/Aurora migration.
- queue-backed workers.
- production deployment.
- production observability.
- cost controls.
- scraper safety.
- Sidekick-inspired upgrades after local MVP: evidence-linked progress,
  dynamic todo lists, runtime evaluator, LLM-as-a-Judge, HITL approvals, and
  budget/error policy hardening.
- optional Compare và Advisor agents.

## Non-Goals

Trừ khi được explicitly approved:

- không AWS commands;
- không Terraform;
- không production deploy;
- không Clerk implementation;
- không database migration execution;
- không paid production observability setup;
- không live scraping scale work.

## Inputs From Previous Phases

Required:

- Phase 7 test/demo report.
- Current architecture and known limitations.
- Any approved implementation reports that changed contracts.

Optional references:

- `segment4/mo_ta_du_an/ALEX_PRODUCTION_ARCHITECTURE_TRANSFER.md` for
  production patterns.

## Contracts

Future production mapping:

| Local MVP | Production Candidate |
|---|---|
| SQLite | Postgres, Supabase, Aurora |
| local worker | queue-backed worker, SQS |
| console logs | CloudWatch, LangFuse, OpenAI traces |
| `demo_user` | Clerk user id |
| localhost CORS | explicit production origins |
| mock defaults | opt-in real service configs |

Production readiness concerns:

- CORS restrictions.
- auth and per-user authorization.
- rate limiting.
- prompt injection guardrails.
- structured logs.
- audit events.
- evidence-linked progress events.
- runtime answer validation.
- HITL approval gates for costly or sensitive actions.
- retries and timeouts.
- dead-letter queue.
- model timeout/fallback.
- scraper source safety.
- dashboard and alarms.
- cost tracking.

Sidekick pattern roadmap:

- Keep V3 as a domain-specific Vietnamese Shopping Sidekick, not a generic
  autonomous browser coworker.
- Preserve controlled Router + explicit tools as the default execution model.
- Upgrade `progress_steps` from minimal user-facing fields to optional
  evidence-linked fields only after the Phase 5/6 minimal contract is stable.
- Consider dynamic LLM-generated todo lists only after deterministic progress
  proves useful in demo.
- Start with Phase 7 rule-based test-only evidence evaluator; consider runtime
  validator or LLM-as-a-Judge only as opt-in future work.
- Add HITL approval only for costly/sensitive actions such as real model calls,
  real scraping retries, notifications, or production-side effects.

## Workflow Gate

Trước khi code hoặc production planning:

- Load `using-superpowers`.
- Dùng `brainstorming` với user.
- Chỉ hỏi các câu thay đổi scope, design, tests, hoặc implementation plan.
- Xác nhận production work được explicitly approved.
- Trình bày Phase 8 plan.
- Chờ explicit approval.

## Implementation Order

1. Review Phase 7 report và current known limitations.
2. Identify blockers với production readiness.
3. Decide production target:
   - local Docker only;
   - Supabase/Postgres local/managed;
   - AWS;
   - deployment platform khác.
4. Viết architecture decision cho next production step nếu được approve.
5. Split production work thành future guides riêng hoặc update guide này.
6. Không deploy cho tới khi user approve specific production implementation
   plan.

## Verification

Phase này verify documentation quality, không phải deployed infrastructure.

Checks:

- roadmap nói rõ planned và implemented khác nhau thế nào;
- không production task nào được mark complete nếu không có evidence;
- local MVP vẫn là baseline;
- cost và secret handling explicit;
- Sidekick-inspired features are clearly marked as planned, opt-in, or future
  unless implementation evidence exists;
- next production step có review gate.

## Report Requirements

Nếu Phase 8 được chạy như planning phase, viết:

```text
shopping_assistant_v3/reports/phase_8_production_roadmap_report.md
```

Bao gồm:

- production option được chọn hoặc deferred;
- risks;
- estimated cost categories;
- Sidekick pattern upgrades accepted, deferred, or rejected;
- docs đã update;
- next phase recommendation.

## Risks And Open Questions

- AWS có thể thêm cost và operational complexity trước khi product ổn định.
- Clerk auth thay đổi database ownership assumptions.
- Real scraping at scale có thể cần proxy/session/rate-limit strategy.
- Production observability không nên expose user data hoặc secrets.
- Compare/Advisor agents nên chờ tới khi search + price + summary ổn định.
