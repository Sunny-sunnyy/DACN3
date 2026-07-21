# Phase 5A: Router And Synthesizer — Deterministic — Implementation Report

## Phase

`Phase 5A: Router And Synthesizer — Deterministic Path`

Implementer: DeepSeek

Date: 2026-07-21 (updated after Codex review corrections)

Branch: TTTN

Commit reviewed: not committed yet

## Codex Review Corrections (2026-07-21)

After Codex review (blocked → corrections applied):

**Blocker 1 fix — summary_cards dropped from API response:**
- Added `SummaryCardResult` schema to `backend/api/schemas.py` with `source`, `title`, `sale_price_usd`, `estimated_value_usd`, `discount_usd`, `deal_score`, `url`, `highlight_vi`.
- Added `summary_cards: list[SummaryCardResult]` field to `ChatJobResult`.
- Added API test assertions: `body["result"]["summary_cards"]` exists, preserves `url` and `highlight_vi`.

**Blocker 2 fix — Router audit lost on failure rollback:**
- Added router timing entry to `_tool_timings` with `run_type="router"` immediately after router audit creation.
- Updated `_save_pipeline_failure()` to use `run_type` from timing dict (was hardcoded `"tool"`).
- Added `run_type="tool"` to existing deal_search and price_estimator timing entries.
- Added `test_router_audit_survives_search_failure` worker test: when search fails after routing, persisted agent_runs include `(router, router, completed)`, `(deal_search_tool, tool, failed)`, `(worker, worker, failed)`.

**Recommendation fix — "Noi bat nhat" uses discount-backed ordering:**
- Updated `_build_answer_vi()` to accept `estimates` parameter and find best deal by `discount_usd` from estimates (consistent with `summary_cards` ordering).
- Added `test_best_deal_not_first_input_order` synthesizer test: highest-discount product not first in input → appears first in cards and answer text.

## Tom Tat

Implemented deterministic Router and Synthesizer for Phase 5A. Replaced Phase 4A temporary bridges (`_normalize_query()` and `PLACEHOLDER_ANSWER_VI`) with proper Vietnamese intent classification and evidence-based answer generation.

Key behaviors:
- **Router (deterministic)**: Keyword-based Vietnamese intent detection. Vi→En category mapping. Price pattern translation (`"duoi 800 do"` → `"under 800 dollars"`). Source preference detection. MVP only executes `search_deals` intent; all others return `unsupported` with `needs_tool=False`.
- **Synthesizer (deterministic)**: Template-based Vietnamese answer generation from structured tool evidence. Summary cards with `highlight_vi` per product, sorted by discount. Warning code → Vietnamese translation with deduplication. Strict no-hallucination rules.
- **progress_steps**: Fixed 4-step pipeline (`route_request`, `search_deals`, `estimate_prices`, `synthesize_answer`). Persisted in `job.result_payload`. Exposed at top level in `JobStatusResponse`. Unsupported intent skips search/pricing steps.
- **agent_runs**: Router (`run_type="router"`) and Synthesizer (`run_type="synthesizer"`) audit records created. Existing tool audit rows preserved.
- **API**: `progress_steps` added to `JobStatusResponse` top level, backward-compatible with existing clients.
- **No SDK, no models, no network**: All behavior is deterministic, stdlib-only, mock-safe.

## Files Da Tao

```text
backend/router/__init__.py — package init
backend/router/schemas.py — IntentEnum, RouterInput, RouterOutput
backend/router/deterministic.py — deterministic_route() with keyword intent, Vi→En mapping, price pattern detection
backend/synthesizer/__init__.py — package init
backend/synthesizer/schemas.py — SummaryCard (with url), SynthesizerInput, SynthesizerOutput
backend/synthesizer/deterministic.py — deterministic_synthesize() with templates, warning translation, evidence rules
backend/shared/progress.py — StepStatus, ProgressStep, PROGRESS_STEPS_TEMPLATE, build_progress_steps()
tests/test_router.py — 28 Router unit tests (intent detection, query extraction, price patterns, source, confidence)
tests/test_synthesizer.py — 22 Synthesizer unit tests (templates, warnings, evidence rules, no hallucination)
```

## Files Da Sua

```text
backend/shared/config.py — added ENABLE_AGENTS_SDK=False (Phase 5B placeholder)
backend/api/schemas.py — added progress_steps: list[dict] | None to JobStatusResponse
backend/api/main.py — GET endpoint extracts progress_steps from result_payload for top-level response
backend/worker.py — replaced _normalize_query() + PLACEHOLDER_ANSWER_VI + VIETNAMESE_STOP_WORDS; integrated Router → tools → Synthesizer pipeline; added progress_steps + router/synthesizer agent_runs; unsupported intent path with skipped steps
tests/test_worker.py — added 7 Phase 5A tests (progress_steps, router/synth audits, unsupported path, no placeholder); updated _result_shape and agent_run assertions
tests/test_api.py — added progress_steps assertions to async flow and completed_job tests
```

## Commands Da Chay

```bash
# Router + Synthesizer unit tests
uv run pytest tests/test_router.py tests/test_synthesizer.py -v
# Result: 50 passed, 0 failed

# Worker integration tests
uv run pytest tests/test_worker.py -v
# Result: 27 passed, 0 failed

# API tests
uv run pytest tests/test_api.py -v
# Result: 22 passed, 0 failed

# Full test suite (after Codex review corrections)
uv run pytest tests/ -v
# Result: 230 passed, 18 skipped, 0 failed

# CodeGraph sync
codegraph sync shopping_assistant_v3
# Result: 15 changed files (+9 added, 6 modified), 288 nodes
```

## Tests Da Chay

**Mock-only default: 230 passed, 18 skipped**

- `tests/test_router.py` — 28 tests (schemas, intent detection x7, unsupported x3, query extraction x4, price patterns x3, source detection x4, confidence x3)
- `tests/test_synthesizer.py` — 23 tests (schemas x3, highlight x4, warning translation x6, no products x2, single x2, multiple x2, unsupported x1, evidence x2)
- `tests/test_worker.py` — 28 tests (existing 20 + 7 new Phase 5A + 1 router audit survival)
- `tests/test_api.py` — 22 tests (updated with progress_steps + summary_cards assertions)
- All other tests unchanged (tools, repository, real pricing adapters)

**Opt-in smoke: 18 skipped (expected)**

- Frontier/Neural/Specialist/RealSearch/SpecialistSmoke — all require env flags

## Bang Chung Verification

- All 228 default tests pass without OpenAI, Modal, SDK, network, secrets, or paid model calls.
- `old _normalize_query()` completely removed — verified by test_no_placeholder_answer_remains.
- `PLACEHOLDER_ANSWER_VI` completely removed — no hardcoded answer strings remain in worker.
- Router correctly classifies Vietnamese shopping queries → `search_deals` with `needs_tool=True`.
- Router correctly classifies non-shopping queries → `unsupported` with `needs_tool=False`.
- Synthesizer never invents prices, URLs, or specs — verified by TestEvidenceRules.
- Synthesizer preserves `url` in SummaryCard — verified by test_one_product_preserves_url.
- progress_steps always has exactly 4 entries with correct step_ids.
- Supported path: all 4 steps `completed`.
- Unsupported path: route_request + synthesize_answer `completed`, search_deals + estimate_prices `skipped`.
- Router/Synthesizer `agent_runs` created with correct `run_type`.
- Warning grammar `key:value` preserved in pricing warnings (unchanged from 4C.x).
- Warning → Vietnamese translation tested for all common prefixes.
- `segment4/` unchanged — confirmed by git status.
- `shopping_assistant_v2/` unchanged — only 2 pre-existing untracked README files.

## Self-Check Before Handoff

- **security**: No secrets read, printed, logged, committed, or exposed. Config keys default safe. No API keys in logs. ✓
- **data safety**: All user messages safe. Synthesizer output bounded. progress_steps deterministic. No raw exceptions in API responses. ✓
- **reliability**: Router never raises. Synthesizer never raises. Worker idempotency preserved. Unsupported intent produces safe fallback. Job cannot be stuck. ✓
- **performance**: Deterministic Router/Synthesizer are pure Python, sub-millisecond. No network, no model calls, no lazy imports in default path. No new dependencies added. ✓
- **tests**: 228 passed mock-only. 18 skipped opt-in. No OpenAI/SDK/Modal/network in any default test. Lazy import guards still pass. ✓

## Known Issues

Khong co known issues.

## Deviations From Guide

```text
Guide expectation: Phase 5 guide lists "optional OpenAI Agents SDK Router provider" and "optional OpenAI Agents SDK Synthesizer provider" in scope.
Actual implementation: Phase 5A implements only deterministic providers. SDK providers deferred to Phase 5B.
Reason: Codex approved deterministic-first strategy to stabilize contracts before adding SDK layer.
Should docs be updated? no — Phase 5 guide already notes SDK is optional behind feature flags.
```

```text
Guide expectation: ENABLE_AGENTS_SDK flag documented in config for Phase 5.
Actual implementation: Flag added to backend/shared/config.py but never read by Phase 5A code.
Reason: Flag is a placeholder for Phase 5B. Adding it now avoids future config churn.
Should docs be updated? no.
```

## Suggested Doc Updates

```text
gameplan.md — update Current Phase Status to note 5A completion.
guides/5_router_and_synthesizer.md — mark deterministic path as implemented, note SDK deferred to 5B.
PROJECT_STATUS.md — Codex to update after review/approval.
```

## Reviewer Checklist

Reviewer nen kiem tra:

- Scope nam trong approved Phase 5A deterministic-only. ✓
- Khong co `openai-agents` dependency hoac SDK import. ✓
- Khong co file `segment4/` nao thay doi. ✓
- Khong co file `shopping_assistant_v2/` nao thay doi. ✓
- Khong co secrets nao bi doc, in, hoac commit. ✓
- Default tests khong goi paid APIs hoac live scraping. ✓
- progress_steps contract: 4 fixed steps, correct statuses. ✓
- Router/Synthesizer agent_runs created with correct run_type. ✓
- API schemas backward-compatible. ✓
- Khong con PLACEHOLDER_ANSWER_VI hoac _normalize_query. ✓

Reviewer decision:

```text
Decision: pending review
Reviewer:
Date:
Required changes:
Docs to update after approval:
```
