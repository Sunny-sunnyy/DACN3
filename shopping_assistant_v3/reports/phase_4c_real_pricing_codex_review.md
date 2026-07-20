# Codex Review: Phase 4C.1 Real Price Estimator Extraction

Decision: approved
Reviewer: Codex
Date: 2026-07-20
Implementer report: `shopping_assistant_v3/reports/phase_4c_real_pricing_report.md`

## Tóm Tắt

Phase 4C.1 is approved after one correction round. The implementation stays
inside the approved staged scope: deterministic formatter, neural adapter,
real estimator boundary, optional neural dependencies, mock-safe default tests,
and opt-in neural smoke tests. Frontier and Specialist remain deferred.

The required fixes from the initial review were applied:

- fallback-only real pricing now returns `deal_score="ok"` consistently;
- `estimate_price()` docstring now describes Phase 4C.1 real dispatch;
- mock-safe `missing_dependency` adapter tests were added;
- generated `backend/database/app.db` was removed and ignored.

## Findings

Không có blocker hoặc major findings.

Minor note: the report body still contains the original `125 passed, 12
skipped` entries in earlier sections, then records the corrected `127 passed,
12 skipped` count in the review-fixes appendix. I did not block approval because
the appendix and this review record the verified final result.

## Verification

Commands run:

```bash
git status --short
```

Result: Phase 4C.1 files are modified/untracked. The unrelated untracked
`shopping_assistant_v2/README_Project_Sidekick.md` and
`shopping_assistant_v2/README_codegraph.md` remain. No untracked
`shopping_assistant_v3/backend/database/app.db` is present.

```bash
codegraph sync shopping_assistant_v3
codegraph status shopping_assistant_v3
```

Result: synced `3` changed files. Final index is up to date, `37 files`,
`542 nodes`, `1147 edges`.

```bash
uv run pytest tests/test_real_pricing.py -q --tb=short
```

Result: `28 passed, 1 warning in 4.48s`.

```bash
uv run pytest tests/test_tools.py tests/test_worker.py -q --tb=short
```

Result: `69 passed, 1 warning in 15.57s`.

```bash
uv run pytest tests/ -q --tb=short
```

Result: `127 passed, 12 skipped, 1 warning in 20.33s`.

```bash
rg -n "^\s*(from\s+segment4(\.|\s+import\b)|import\s+segment4\b)" shopping_assistant_v3/backend shopping_assistant_v3/tests
```

Result: no direct runtime import statements from `segment4`.

```bash
git diff --name-only -- segment4/
```

Result: no output; `segment4/` unchanged.

```bash
find shopping_assistant_v3 -path 'shopping_assistant_v3/.venv' -prune -o -name '*.pth' -print
```

Result: no model weight files copied into V3 outside `.venv`.

I also compared `segment4/price_agents/deep_neural_network.py` with the V3
copy. The architecture, constants, and inference math are preserved; the V3
copy adds documentation and removes training-only imports.

## Scope Check

Scope stayed within approved Phase 4C.1: deterministic formatter, neural
adapter, real estimator boundary, optional neural dependency group, dispatch
change, mock-safe tests, opt-in neural smoke tests, implementation plan, and
implementation report. Frontier and Specialist are not implemented and remain
explicitly deferred.

## Safety And Quality Check

Security: default verification did not run live scraping, paid model calls,
AWS, Terraform, deployment, or secret-dependent commands. I did not read or
print secrets.

Data safety: warning grammar is bounded and uses `key:value`. Adapter error
details are bounded and single-line. Fallback-only pricing is explicit through
`real_pricing_fallback_used:sale_price_markup` and
`ensemble_partial:fallback_only`.

Reliability: default tests pass. Real-mode missing weights and missing neural
dependencies produce safe `PriceEstimateOutput` fallback behavior instead of
raw exceptions. Worker real-model flag path completes with fallback warnings.

Performance: mock path does not import the heavy neural module; neural deps are
optional and lazy-loaded. `uv.lock` grows because optional neural extras resolve
torch transitive dependencies, which is acceptable for this milestone.

## Thay Đổi Bắt Buộc

Không còn required changes.

## Approval Notes

Phase 4C.1 is approved. `PROJECT_STATUS.md` has been updated to record this
milestone as the latest approved progress. The next implementation milestone is
Phase 4C.2 Frontier pricing extraction, and it still requires separate
brainstorming plus explicit user approval before implementation or paid/model
verification.
