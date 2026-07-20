# Codex Review: Phase 4C.2 Frontier Price Estimator Extraction

Decision: approved
Reviewer: Codex
Date: 2026-07-20
Implementer report: `shopping_assistant_v3/reports/phase_4c2_frontier_pricing_report.md`

## Tóm Tắt

Phase 4C.2 is approved. The implementation stays inside the approved Frontier
adapter boundary: ChromaDB path is configurable, Frontier dependencies are
optional and lazy-loaded, default tests remain mock-only, and real Frontier
smoke tests are opt-in and skipped by default.

The real pricing path now uses this priority:

```text
Frontier available -> Frontier value
Frontier unavailable + Neural available -> Neural value
Neither available -> 5% fallback markup
```

Frontier short-circuits Neural when it succeeds, so
`ensemble_partial:frontier_only` is accurate and the neural model is not loaded
unnecessarily.

## Findings

Không có blocker hoặc major findings.

Minor note: `backend/tools/price_estimator/tool.py` still describes the real
path as Phase 4C.1/neural-only in its docstring comments. Runtime behavior is
correct because it dispatches to `real_estimator`, and the phase report/docs now
record the 4C.2 behavior, so this does not block approval.

## Verification

Commands run:

```bash
git status --short
```

Result: Phase 4C.2 implementation files and reports are modified/untracked.
The pre-existing modified `reports/user_reports/phase_*_user_report.md` files
and untracked `shopping_assistant_v2/README_*.md` files remain unrelated and
were not reset.

```bash
codegraph status shopping_assistant_v3
```

Result: index is up to date with `40 files`, `605 nodes`, `1,295 edges`.

```bash
uv run pytest tests/test_real_pricing.py tests/test_real_pricing_frontier.py -q --tb=short
```

Result: `49 passed, 4 skipped, 1 warning in 11.29s`.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python -c "<fake Frontier branch checks>"
```

Result: `frontier fake branch checks passed`. This exercised
`collection_not_found`, `parse_error`, and successful parsed-value behavior with
fake ChromaDB/SentenceTransformer/OpenAI modules and no network calls.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -q --tb=short
```

Result: `148 passed, 16 skipped, 1 warning in 47.62s`.

```bash
rg -n "^\s*(from\s+segment4(\.|\s+import\b)|import\s+segment4\b)" shopping_assistant_v3/backend shopping_assistant_v3/tests
```

Result: no direct runtime import statements from `segment4`.

```bash
git diff --name-only -- segment4/
```

Result: no output; `segment4/` unchanged.

```bash
rg -n "OPENAI_API_KEY|sk-|api_key\s*=" shopping_assistant_v3/backend/tools/price_estimator/frontier
```

Result: no hardcoded key names or key-like values in Frontier runtime code.

## Scope Check

Scope stayed within approved Phase 4C.2:

- added `PRICER_CHROMADB_PATH` and `PRICER_FRONTIER_MODEL_ID`;
- added optional `frontier` dependency group;
- added a new `frontier` adapter package;
- updated real pricing assembly and dispatch to `frontier > neural > fallback`;
- added mock-only Frontier adapter tests and opt-in real Frontier smoke tests;
- kept `segment4/` untouched and avoided runtime imports from it.

No live ChromaDB/OpenAI calls were run during default verification.

## Safety And Quality Check

Security: no secrets were read or printed. Default tests did not call OpenAI,
Modal, live Amazon/BestBuy scraping, AWS, Terraform, or deployment commands.

Data safety: Frontier errors are returned as bounded `error_code` and
`error_detail` metadata. `_extract_price` returns `None` on parse failure rather
than silently converting bad output to `0.0`.

Reliability: missing ChromaDB path, missing model id, missing dependency,
missing collection, model error, parse error, neural fallback, and full fallback
paths produce valid `PriceEstimateOutput` values with explicit warnings.

Performance: mock mode does not import ChromaDB, SentenceTransformer, OpenAI,
Torch, sklearn, or numpy. Real mode lazy-loads Frontier dependencies only when
`ENABLE_REAL_MODEL_CALLS=true`, and skips Neural when Frontier succeeds.

## Thay Đổi Bắt Buộc

Không có required changes.

## Approval Notes

Phase 4C.2 is approved. `PROJECT_STATUS.md` and user-facing reports have been
updated to record Frontier pricing as the latest approved milestone. The next
implementation milestone is Phase 4C.3 Specialist pricing extraction, and it
requires separate brainstorming plus explicit user approval before any Modal or
real model verification work.
