# ITLR Patterns Brainstorm Report

Date: 2026-07-24
Reviewer/Facilitator: Codex
Status: brainstorm approved by user; documentation-only update

## Tóm Tắt

User yêu cầu Codex review:

```text
shopping_assistant_v2/ITLR_Fullstack_Recommender_RAG_TECHNICAL_DOSSIER.md
```

File này là external project dossier được đặt trong `shopping_assistant_v2/`
cho tiện quản lý. Nó không phải Shopping Assistant V2 source of truth và không
được migrate nguyên dự án vào V3.

Quyết định: V3 có thể tái sử dụng bounded engineering patterns từ ITLR, nhưng vẫn
phải là Vietnamese-speaking US deal assistant với controlled Router, explicit
Amazon/BestBuy search/pricing tools, evidence-first synthesis, và mock-safe
default verification.

## Patterns Được Chấp Nhận

- Clear subsystem boundaries giữa product API, AI/tool runtime, persistence,
  evaluation, và future analytics.
- Lightweight query understanding như future Router improvement: typo
  correction, abbreviation expansion, và short follow-up resolution.
- Fixture-based evaluation discipline: labeled unsupported examples, ranking
  checks, latency notes, và repeatable demo commands.
- Evidence guardrails: final answer, product cards, warnings, và progress steps
  phải được backed by tool/result evidence.
- Future interaction feedback loop: clicked products, saved products, dismissed
  cards, và recommendation usefulness signals.
- Security hardening patterns: rate limits, safe metrics, secret handling,
  bounded logs, và production guards.

## Deferred Hoặc Rejected Cho MVP

- Social network, direct messages, uploads, community feeds, và admin media
  workflows.
- Full DataLake, Spark, Delta Lake, dbt, MLflow, CDC, hoặc BI dashboards.
- General learning recommender behavior không liên quan tới shopping deals.
- Free-form agent loops tự chọn tools.
- Runtime LLM-as-a-Judge trong default execution.
- Docker/CD/production deployment trước local MVP demo readiness.

## Docs Đã Update

```text
shopping_assistant_v3/guides/architecture.md
shopping_assistant_v3/guides/agent_architecture.md
shopping_assistant_v3/guides/7_testing_and_demo.md
shopping_assistant_v3/guides/8_production_roadmap.md
shopping_assistant_v3/reports/itlr_patterns_brainstorm_report.md
```

## Tác Động Tới Phase

Brainstorm này không thay đổi runtime behavior và không approve implementation
phase mới.

Phase 5B vẫn là next approved implementation milestone trong
`PROJECT_STATUS.md`. ITLR-inspired ideas chỉ là guidance cho documentation,
Phase 7 testing/demo hardening, và Phase 8 production roadmap.

## Safety Notes

- Không đọc hoặc summarize secrets.
- Không sửa runtime code.
- Không cài dependencies.
- Không chạy live Amazon/BestBuy scraping hoặc model calls.
- `shopping_assistant_v2/ITLR_Fullstack_Recommender_RAG_TECHNICAL_DOSSIER.md`
  vẫn là external reference, không phải source-of-truth V3 document.
