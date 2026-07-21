# Phase 5A: Router And Synthesizer — Codex Review

## Phase

`Phase 5A: Router And Synthesizer — Deterministic Path`

Reviewer: Codex

Date: 2026-07-21

Branch: TTTN

Implementation report reviewed:

```text
shopping_assistant_v3/reports/phase_5a_router_and_synthesizer_report.md
```

## Decision

```text
approved
```

Phase 5A is approved after re-review. The initial two blockers were corrected,
and the deterministic Router/Synthesizer milestone is within the approved
Phase 5A scope.

## Scope Check

Reviewed scope:

- deterministic Router package;
- deterministic Synthesizer package;
- shared progress step contract;
- worker integration;
- API status response changes;
- router/synthesizer/unit/worker/API tests;
- Phase 5A implementation report.

Scope constraints checked:

- No `openai-agents` dependency added.
- No SDK provider code added.
- No live scraping or model calls are required by default tests.
- No new DB columns or migrations.
- `segment4/` was not modified.
- `shopping_assistant_v2/` was not modified by this phase; the existing
  untracked `README_*.md` files remain outside Phase 5A scope.
- `PROJECT_STATUS.md` was not updated by the implementer before review.

## Initial Findings And Corrections

### Blocker 1 — API response dropped `summary_cards`

Initial finding:

`backend/worker.py` wrote `summary_cards` into `job.result_payload`, but
`backend/api/schemas.py` did not declare `summary_cards` on `ChatJobResult`.
FastAPI/Pydantic therefore filtered the field out of the API response.

Correction verified:

- Added `SummaryCardResult`.
- Added `summary_cards: list[SummaryCardResult]` to `ChatJobResult`.
- Added API assertions that `result.summary_cards` exists and preserves card
  fields such as `url` and `highlight_vi`.

Codex verification probe:

```text
JobStatusResponse.model_validate(payload_with_summary_cards).model_dump()
```

Observed result after correction:

```text
result.summary_cards preserved source, title, url, highlight_vi, and optional
price fields.
```

### Blocker 2 — Router audit was lost on failure rollback

Initial finding:

`process_job()` created the router `agent_runs` row inside the main transaction.
If a later tool failed, `session.rollback()` removed that completed router audit
row. `_save_pipeline_failure()` recreated tool and worker rows but not the
router row.

Correction verified:

- Router completion is tracked in `_tool_timings` with `run_type="router"`.
- `_save_pipeline_failure()` uses `run_type` from timing entries rather than
  hardcoding `"tool"`.
- Added worker test coverage for a search failure after routing.

Codex temp-DB failure probe after correction:

```text
[('deal_search_tool', 'tool', 'failed'),
 ('router', 'router', 'completed'),
 ('worker', 'worker', 'failed')]
```

### Recommendation — "Nổi bật nhất" consistency

Initial recommendation:

The Synthesizer sorted `summary_cards` by discount but chose the text's
"Noi bat nhat" product from raw product order / sale-price proxy.

Correction verified:

- `_build_answer_vi()` now accepts estimates and chooses the highlighted product
  by `discount_usd`, consistent with summary card ordering.
- Added a test where the highest-discount product is not first in input order.

## Verification Run By Codex

CodeGraph status before re-review showed pending modified files, so Codex ran:

```bash
codegraph sync shopping_assistant_v3
codegraph status shopping_assistant_v3
```

Final CodeGraph result:

```text
Index is up to date
Files: 53
Nodes: 794
Edges: 1,755
```

CodeGraph exploration used:

```text
Re-review Phase 5A corrections: ChatJobResult SummaryCardResult summary_cards
JobStatusResponse get_chat_job process_job _save_pipeline_failure router audit
_finalize_timed_run deterministic_synthesize _build_answer_vi best discount.
```

Targeted tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_router.py tests/test_synthesizer.py -q --tb=short
```

Result:

```text
51 passed, 1 warning
```

Worker tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_worker.py -q --tb=short
```

Result:

```text
28 passed, 1 warning
```

Broad mock-only suite excluding API tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ --ignore=tests/test_api.py -q --tb=short
```

Result:

```text
208 passed, 18 skipped, 1 warning
```

API test note:

```text
tests/test_api.py could not complete in the Codex sandbox. Even a minimal
FastAPI TestClient.get() script hangs in this environment, so Codex did not use
that hang as an app-specific failure. The original API response blocker was
verified directly through Pydantic response-model validation.
```

Warning observed:

```text
StarletteDeprecationWarning from FastAPI TestClient/httpx.
```

This warning is not a Phase 5A blocker.

## Approval Notes

Phase 5A now establishes:

- deterministic Vietnamese Router;
- deterministic evidence-based Vietnamese Synthesizer;
- fixed 4-step `progress_steps`;
- `summary_cards` in persisted job result and API response schema;
- Router and Synthesizer `agent_runs` audit rows;
- safe unsupported-intent path with search/pricing skipped;
- no SDK imports, no OpenAI calls, no Modal calls, no live scraping, and no new
  dependency requirement in the default path.

## Next Milestone

Recommended next milestone:

```text
Phase 5B: Optional OpenAI Agents SDK Router/Synthesizer Providers
```

Phase 5B should remain behind:

```text
ENABLE_REAL_MODEL_CALLS=true
ENABLE_AGENTS_SDK=true
```

The deterministic Phase 5A contracts should stay as the default and as the
fallback path.

