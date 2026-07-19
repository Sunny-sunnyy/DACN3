# Phase 4A: Mock Search/Pricing Tools — Implementation Report

## Phase

`Phase 4A: Mock Search/Pricing Tools`

Implementer: DeepSeek

Date: 2026-07-19 (updated after Codex review)

Branch: TTTN

Commit reviewed: not committed yet (Codex re-review pending)

## Tom Tat

Implemented full mock pipeline for deal_search_tool and price_estimator_tool with JSON fixtures, integrated into the worker lifecycle with DB persistence and agent_runs audit trails. All behavior is mock-only. No live Amazon/BestBuy scraping, no paid model calls, no network access.

Key changes:
- `max_results_per_source` default changed from 6 to 5 (approved contract change).
- `deal_search_tool`: any-token keyword match against 10 JSON fixture products (5 Amazon + 5 BestBuy).
- `price_estimator_tool`: fixture lookup by source+title, fallback rule `estimated = round(sale_price * 1.10, 2)`.
- Worker `result_builder` parameter replaced by `deal_search_runner` + `price_estimator_runner` injectable seams.
- Worker uses `_normalize_query()` to strip Vietnamese intent/filler words before passing to deal_search.
- `ENABLE_REAL_SEARCH=true` and `ENABLE_REAL_MODEL_CALLS=true` raise `NotImplementedError` in tools; worker catches and fails job with safe "Phase 4A" error message.
- `answer_vi` is a non-empty Vietnamese placeholder string.

## Files Da Tao

```text
backend/tools/__init__.py — package init
backend/tools/deal_search/__init__.py — module init
backend/tools/deal_search/schemas.py — DealSearchInput, ProductCandidate, DealSearchOutput
backend/tools/deal_search/fixtures/mock_products.json — 10 mock products
backend/tools/deal_search/tool.py — deal_search() mock implementation with any-token match
backend/tools/price_estimator/__init__.py — module init
backend/tools/price_estimator/schemas.py — PriceEstimateInput, ModelBreakdown, PriceEstimateOutput
backend/tools/price_estimator/fixtures/mock_estimates.json — 4 product lookup entries
backend/tools/price_estimator/tool.py — estimate_price() with fixture lookup + 10% fallback
tests/test_tools.py — 31 tests: schema validation, fixture integrity, mock behavior, ENABLE_REAL_* flags
tests/test_repository.py — 8 tests: product/price_estimate CRUD, cascade delete
reports/phase_4a_implementation_plan.md — implementation plan (reference)
```

## Files Da Sua

```text
backend/api/schemas.py — max_results_per_source default 6 → 5 (line 26)
backend/database/repository.py — added Product, PriceEstimate imports; added create_product, get_products_by_job_id, create_price_estimate, get_price_estimates_by_product_ids
backend/worker.py — removed build_mock_result; added VIETNAMESE_STOP_WORDS, _normalize_query, PLACEHOLDER_ANSWER_VI, DealsSearchRunner, PriceEstimatorRunner, _run_deal_search, _run_price_estimator; replaced process_job signature (result_builder → deal_search_runner + price_estimator_runner); replaced process_job body with Phase 4A pipeline; added NotImplementedError catch; preserved _log_event, _save_failure, idempotency gates, stale-running recovery
tests/test_worker.py — removed build_mock_result import and TestMockResult; updated _create_pending_job; replaced TestProcessJob with Phase 4A tests; replaced result_builder failure tests with runner injection; added TestRealModeInWorker; preserved TestIdempotency, TestUnknownJob, TestLogEvents
tests/test_api.py — added test_default_max_results_is_5
```

## Commands Da Chay

```bash
# Task 1: API tests after max_results change
uv run pytest tests/test_api.py -v
# Result: 21 passed

# Task 2: Verify deal_search tool loads
uv run python -c "from backend.tools.deal_search.tool import ..."
# Result: 3 products matched for "gaming laptop"

# Task 3: Verify price_estimator tool
uv run python -c "from backend.tools.price_estimator.tool import ..."
# Result: fixture lookup 949.99, fallback 55.00

# Task 4: Verify repository imports
uv run python -c "from backend.database.repository import create_product, ..."
# Result: OK

# Task 5: Verify worker normalization
uv run python -c "from backend.worker import _normalize_query; ..."
# Result: "Tìm Gaming LAPTOP dưới 800" → "gaming laptop 800"

# Task 6: Tool tests
uv run pytest tests/test_tools.py -v
# Result: 31 passed

# Task 7: Repository tests
uv run pytest tests/test_repository.py -v
# Result: 8 passed

# Task 8: Worker + API tests
uv run pytest tests/test_worker.py tests/test_api.py -v
# Result: 41 passed

# Task 9: Full suite
uv run pytest tests/ -v
# Result: 80 passed

# Verification: no segment4 imports
rg "segment4" backend/ tests/
# Result: only reference READMEs from Phase 1 (no code imports)

# Verification: no paid API imports in tests
rg "openai|litellm|curl_cffi|modal|brave" tests/
# Result: No paid/external API imports

# Verification: codegraph sync + status (after Codex review)
codegraph sync shopping_assistant_v3 && codegraph status shopping_assistant_v3
# Result: Index up to date, 25 files, 332 nodes, 704 edges (after syncing Phase 4A changes)

# Verification: git status
git status --short
# Result: only approved files changed + unrelated v2 untracked files
```

## Tests Da Chay

| File | Count | Result |
|---|---|---|
| tests/test_api.py | 22 | 22 passed |
| tests/test_repository.py | 8 | 8 passed |
| tests/test_tools.py | 31 | 31 passed |
| tests/test_worker.py | 19 | 19 passed |
| **Total** | **80** | **80 passed** |

All tests are mock-only. No network, no model calls, no secrets required.

## Bang Chung Verification

1. **Tool schemas match contracts**: `DealSearchInput/Output`, `PriceEstimateInput/Output`, `ModelBreakdown` all match `agent_architecture.md` field-for-field.
2. **Fixtures load correctly**: 10 products (5 Amazon + 5 BestBuy), 4 estimate lookup entries.
3. **Keyword matching**: any-token match works; "gaming laptop" → 3 products; "xyznonexistent12345" → empty + warning.
4. **Price estimate**: fixture lookup returns exact values; fallback computes `round(sale_price * 1.10, 2)`.
5. **Deal score**: hot (discount >= 200), good (>= 100), ok (> 0), overpriced (<= 0).
6. **Worker pipeline**: request → normalize → deal_search → persist products → estimate per product → persist estimates → build result.
7. **agent_runs**: created for deal_search_tool and per-product price_estimator_tool, status completed/failed, duration_ms recorded.
8. **DB persistence**: products and price_estimates rows match result_payload.
9. **Idempotency**: completed/failed/running jobs preserved; stale-running recovered.
10. **ENABLE_REAL_* flags**: tools raise `NotImplementedError("Phase 4A")`; worker catches → job failed with safe message.
11. **Phase 3 behavior preserved**: idempotency gates (4 tests), stale-running recovery, structured JSON logs with job_id, _save_failure, unknown job handling.
12. **No segment4 runtime imports**: only reference in tool READMEs (reference notes, not code imports).
13. **No secrets accessed**: no .env reading, no API keys, no credentials.
14. **CodeGraph**: index up to date, 25 files, 332 nodes, 704 edges.

## Codex Review Fixes (2026-07-19)

Sau Codex review `phase_4a_mock_tools_codex_review.md`, cac fixes sau da duoc apply:

1. **major (fixed):** Restored completed `worker` agent_run for successful jobs. `process_job` now creates a `worker` run with status "started" and updates it to "completed" at end of pipeline, preserving Phase 3 behavior.

2. **major (fixed):** Failed tool agent_runs now persist durably. `_save_pipeline_failure` creates both worker AND tool runs in a fresh session after the main session is rolled back. This avoids SQLite lock contention from separate-session approaches while ensuring audit durability. Tool run metadata (`_tool_timings`) is collected during pipeline execution and used by the failure path.

3. **minor (fixed):** CodeGraph synced: `codegraph sync shopping_assistant_v3` — now 25 files, 332 nodes, 704 edges (was stale at 16/206/400).

4. **minor (fixed):** Updated `backend/tools/deal_search/README.md` and `backend/tools/price_estimator/README.md` — removed "Chưa có code", now reflect Phase 4A implementation complete.

Tests added/updated:
- `test_creates_agent_runs_for_tools_and_worker` — asserts `worker` component is present alongside tool runs.
- `test_failure_persists_failed_tool_and_worker_runs` — asserts both failed tool AND worker runs survive rollback.
- All 80 tests pass (unchanged count).

## Known Issues

Khong co known issues.

## Deviations From Guide

```text
Guide expectation: max_results_per_source default = 6.
Actual implementation: max_results_per_source default = 5.
Reason: Approved contract change during Phase 4A brainstorming.
Should docs be updated? Yes — architecture.md and agent_architecture.md examples use 6.

Guide expectation: query_en from Router (Phase 5).
Actual implementation: query_en bridged from request_payload["message"] via _normalize_query().
Reason: Phase 4A temporary bridge. Router replaces this in Phase 5.
Should docs be updated? No — documented as temporary in code comments.

Guide expectation: result_builder(fail) for failure testing.
Actual implementation: deal_search_runner and price_estimator_runner injectable seams.
Reason: More granular failure injection for tool-level tests.
Should docs be updated? No — internal implementation detail.
```

## Suggested Doc Updates

```text
architecture.md — update max_results_per_source examples from 6 to 5 (if examples exist).
agent_architecture.md — update max_results_per_source examples from 6 to 5.
gameplan.md and PROJECT_STATUS.md — update after Codex approval (not implementer responsibility).
```

## Reviewer Checklist (Self-Check)

- **security**: No secrets read, printed, logged, committed, or exposed. No live scraping, paid model calls, AWS/Terraform/deploy, or new network access. ✓
- **data safety**: Persisted payloads, URLs, user messages, tool/model errors are sanitized. Safe error messages to API (no raw exceptions). ✓
- **reliability**: Job/status transitions work. Idempotency gates tested. Failure paths save safe errors and agent_runs. Stale-running recovery preserved. ✓
- **performance**: No obvious slowdowns. Mock tools return instantly from JSON fixtures. No unbounded work, uncontrolled threads, repeated expensive calls, or polling loops. ✓
- **tests**: All 80 tests use mocks/fixtures only. No secrets, live scraping, paid model calls, AWS, or external services required. ✓

## Handoff

Ready for Codex review. No commits made (implementer workflow prohibits commits before Codex approval).

Branch: TTTN
Files changed: 7 modified + 13 new (see git status above)
