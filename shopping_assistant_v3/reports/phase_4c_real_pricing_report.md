# Phase 4C: Real Price Estimator Extraction — Implementation Report

## Phase

`Phase 4C.1: Real Price Estimator Extraction — Neural Adapter + Formatter + Boundary`

Implementer: DeepSeek

Date: 2026-07-20

Branch: TTTN

Commit reviewed: not committed yet

## Tóm Tắt

Implemented staged real price estimator extraction (milestone 4C.1) behind `ENABLE_REAL_MODEL_CALLS=true`. Mock path unchanged.

Key behaviors:
- **Mock path (default)**: fixture lookup + 10% fallback rule — completely unchanged from Phase 4A.
- **Real path**: deterministic formatter → neural adapter (lazy-load) → `PriceEstimateOutput` assembly with explicit warnings.
- Neural adapter copy+adapts `DeepNeuralNetworkInference` math from `segment4/price_agents/deep_neural_network.py`. No runtime imports from segment4.
- Heavy dependencies (torch, sklearn, numpy) are optional (`[project.optional-dependencies] neural`) and lazy-loaded only inside `NeuralPriceAdapter._load_model()`.
- Frontier (4C.2) and Specialist (4C.3) deferred — real mode returns explicit `frontier_unavailable:deferred_to_4c2`, `specialist_unavailable:deferred_to_4c3` warnings.
- Warning grammar: `key:value` (no space after colon), consistent across all warnings.

## Files Đã Tạo

```text
backend/tools/price_estimator/formatter.py — deterministic ProductCandidate → structured text, no model calls
backend/tools/price_estimator/neural/__init__.py — package init (stdlib only, no heavy imports)
backend/tools/price_estimator/neural/deep_neural_network.py — copy+adapt from segment4 (ResidualBlock, DeepNeuralNetwork, DeepNeuralNetworkInference, Y_STD, Y_MEAN)
backend/tools/price_estimator/neural/adapter.py — NeuralPriceAdapter with NeuralEstimateResult, lazy-load heavy deps
backend/tools/price_estimator/real_estimator.py — estimate_price_real() orchestrator + _assemble_output() pure function
tests/test_real_pricing.py — 26 mock-only tests (formatter, boundary, assembly, adapter, config, dispatch, lazy-import guard)
tests/test_real_pricing_neural.py — 4 opt-in neural smoke tests (skipped by default)
reports/phase_4c_implementation_plan.md — approved implementation plan
```

## Files Đã Sửa

```text
backend/shared/config.py — added PRICER_NEURAL_WEIGHTS_PATH env var (default "")
backend/tools/price_estimator/tool.py — replaced NotImplementedError gate with real_estimator dispatch (inline import to keep mock path lazy)
pyproject.toml — added [project.optional-dependencies] neural = ["torch>=2.0.0", "scikit-learn>=1.3.0", "numpy>=1.24.0"]
uv.lock — auto-updated (neural group + transitive torch deps resolved)
tests/test_tools.py — updated TestRealModeFlags.test_real_model_calls_still_not_implemented → test_real_model_calls_dispatches_to_real_path (Phase 4C behavior)
tests/test_worker.py — updated TestRealModeInWorker.test_real_model_flag_fails_job_with_safe_error → test_real_model_flag_completes_job_with_fallback (Phase 4C behavior)
```

## Adapted Functions (segment4 → V3)

| segment4 | V3 | Notes |
|---|---|---|
| `deep_neural_network.py` | `neural/deep_neural_network.py` | Copy+adapt. Removed training-only imports (tqdm, optim, DataLoader, TensorDataset, CosineAnnealingLR). Architecture, math, constants preserved exactly. |
| `ResidualBlock` | `neural/deep_neural_network.ResidualBlock` | Identical |
| `DeepNeuralNetwork` | `neural/deep_neural_network.DeepNeuralNetwork` | Identical |
| `DeepNeuralNetworkInference` | `neural/deep_neural_network.DeepNeuralNetworkInference` | Identical |
| `Y_STD`, `Y_MEAN` | `neural/deep_neural_network.Y_STD`, `Y_MEAN` | Identical |
| `Preprocessor.preprocess()` | `formatter.format_product_for_pricing()` | Deterministic template replacing LiteLLM call. Category: Unknown (trung thực, không bias). |
| `EnsembleAgent.price()` | `real_estimator.estimate_price_real()` | Orchestrator boundary. Calls formatter → neural adapter → assemble. |
| N/A (new) | `neural/adapter.NeuralPriceAdapter` | Lazy-load wrapper, fail-safe, bounded errors. |

Not extracted:
- `Preprocessor` (segment4 uses LiteLLM) → replaced with deterministic formatter
- `FrontierAgent` (segment4 uses OpenAI + ChromaDB) → deferred to 4C.2
- `SpecialistAgent` (segment4 uses Modal) → deferred to 4C.3
- `EnsembleAgent` weighted combination → deferred until all 3 models available

## CodeGraph Evidence

**Pre-implementation:**
```text
codegraph status shopping_assistant_v3 → 30 files, 427 nodes, 907 edges (baseline Phase 4B)
codegraph explore EnsembleAgent flow → 29 symbols across 4 files
codegraph explore preprocessor and model call chain → 23 symbols across 3 files
```

**Post-implementation:**
```text
codegraph sync shopping_assistant_v3 → 11 changed files (+7 added, 4 modified), 259 nodes
codegraph status shopping_assistant_v3 → 37 files, 537 nodes, 1136 edges (up to date)
```

## Commands Đã Chạy

```bash
# Mock path import verification
uv run python -c "from backend.tools.price_estimator.formatter import format_product_for_pricing"  # → OK
uv run python -c "from backend.tools.price_estimator.neural.adapter import NeuralPriceAdapter"   # → OK (no heavy deps)
uv run python -c "
import sys
from backend.tools.price_estimator.neural.adapter import NeuralPriceAdapter
assert 'backend.tools.price_estimator.neural.deep_neural_network' not in sys.modules
"  # → OK (lazy import works)

# Full lazy import chain verification
uv run python -c "... all 7 checks ..."  # → ALL CHECKS PASSED

# Mock path unchanged
uv run python -c "
from backend.tools.price_estimator.tool import estimate_price
# fixture lookup → 879.99, fallback rule unchanged
"  # → OK

# Tests
uv run pytest tests/test_real_pricing.py -v              # → 26 passed
uv run pytest tests/test_real_pricing_neural.py -v       # → 4 skipped
uv run pytest tests/ -v                                  # → 125 passed, 12 skipped

# Verification checks
rg -n "from segment4\|import segment4" backend/ tests/   # → NO MATCHES
git diff --name-only -- segment4/                         # → no output (untouched)
codegraph sync shopping_assistant_v3                     # → 11 changed files, 259 nodes
codegraph status shopping_assistant_v3                   # → 37/537/1136 up to date
```

## Tests Đã Chạy

| File | Count | Result |
|---|---|---|
| tests/test_api.py | 22 | 22 passed |
| tests/test_repository.py | 8 | 8 passed |
| tests/test_tools.py | 51 | 51 passed (1 updated for Phase 4C) |
| tests/test_worker.py | 20 | 20 passed (1 updated for Phase 4C) |
| tests/test_real_pricing.py | 26 | 26 passed |
| tests/test_real_search.py | 8 | 8 skipped (Phase 4B opt-in) |
| tests/test_real_pricing_neural.py | 4 | 4 skipped (Phase 4C opt-in) |
| **Total** | **139** | **125 passed, 12 skipped** |

All default tests are mock/fixture-only. No network, no model calls, no secrets, no neural deps required.

## Bằng Chứng Verification

1. **Mock path unchanged**: All 31 Phase 4A mock price estimator tests pass. `ENABLE_REAL_MODEL_CALLS=false` → fixture lookup + 10% fallback rule.
2. **Real path dispatch**: `ENABLE_REAL_MODEL_CALLS=true` → `real_estimator.estimate_price_real()` (verified by `TestRealModeFlags` and `TestRealModeDispatch`).
3. **Formatter deterministic**: 8 formatter tests pass. Template output consistent. All-empty fields → "Unknown product". Category always "Unknown".
4. **Neural adapter lazy import**: `deep_neural_network` NOT in `sys.modules` after all default tests (`test_neural_heavy_module_not_imported`).
5. **Adapter module safe import**: `neural/adapter.py` imports only stdlib. `_load_model()` imports heavy deps + `deep_neural_network` lazily.
6. **Missing weights safe failure**: `NeuralPriceAdapter(weights_path="")` → `NeuralEstimateResult(available=False, error_code="missing_weights_path")`.
7. **Fallback 5% markup**: Real mode without weights → `round(sale_price * 1.05, 2)`, distinct from mock 10%.
8. **Warning grammar**: All warnings use `key:value` format (no space after colon). Verified by `TestRealEstimatorWarnings`.
9. **Warning completeness**: Fallback path returns exactly 5 warnings (frontier_unavailable, specialist_unavailable, neural_unavailable, real_pricing_fallback_used, ensemble_partial:fallback_only).
10. **Assembly pure function**: `_assemble_output(product, NeuralEstimateResult)` testable without neural deps. Verified by `TestAssembly` (3 tests).
11. **Error sanitization**: `_sanitize_detail` bounds to 200 chars, flattens newlines, handles non-string inputs. Verified by `TestNeuralAdapterSanitizedError` (3 tests).
12. **Opt-in neural smoke**: 4 tests skipped by default (require `ENABLE_REAL_MODEL_CALLS=true` + weights path + file exists + neural extras installed).
13. **No segment4 runtime imports**: `rg` search confirms zero `from segment4` or `import segment4` in V3 backend or tests.
14. **segment4 untouched**: `git diff --name-only -- segment4/` returns empty.
15. **No secrets accessed**: No .env reading, no API keys, no credentials. All tests run without secrets.
16. **No .pth committed**: `deep_neural_network.pth` not copied. Weight path via `PRICER_NEURAL_WEIGHTS_PATH` env var.

## Known Issues

- **Frontier deferred to 4C.2** (Major): FrontierAgent requires ChromaDB vectorstore (800K+ products) + SentenceTransformer + OpenAI API key + paid model calls. Real mode marks it as `frontier_unavailable:deferred_to_4c2`.
- **Specialist deferred to 4C.3** (Major): SpecialistAgent is a Modal remote wrapper — no meaningful local extraction possible. Real mode marks it as `specialist_unavailable:deferred_to_4c3`.
- **Ensemble partial** (Major): With only neural available, real mode produces `ensemble_partial:neural_only` or `ensemble_partial:fallback_only`. Full ensemble requires 4C.2 + 4C.3.
- **Neural weights not bundled** (Minor): `deep_neural_network.pth` (~1.1GB) is not included in V3. Real neural pricing requires manual `PRICER_NEURAL_WEIGHTS_PATH` pointing to segment4 weights or a separate download.
- **uv.lock auto-updated** (Minor): Adding `neural` optional group resolved torch transitive deps (cuda-bindings, nvidia-* packages). These are large but only installed with `uv sync --extra neural`.

## Deviations From Guide

```text
Guide expectation: Extract cả Preprocessor + Frontier + Specialist + Neural (full ensemble).
Actual implementation: Only Neural extracted. Preprocessor → deterministic formatter. Frontier/Specialist deferred.
Reason: Staged extraction per user approval. Frontier needs ChromaDB + OpenAI (cost). Specialist is Modal wrapper (not meaningful to extract).
Should docs be updated? Yes — model_breakdown semantics changed. 0.0 means "deferred/unavailable", not "real value of 0".

Guide expectation: ensemble formula frontier*0.8 + specialist*0.1 + neural*0.1.
Actual implementation: No reweight. Neural value used directly when available. Ensemble partial warnings make this explicit.
Reason: Changing ensemble math without calibration would produce misleading estimates.
Should docs be updated? Yes — Phase 4C real mode docs should reflect partial ensemble semantics.

Guide expectation: Preprocessor uses LiteLLM with configurable model.
Actual implementation: Deterministic formatter, no model call. Category always "Unknown".
Reason: LiteLLM Preprocessor is an unnecessary model call for MVP. Category: "Unknown" is more honest than guessing "Electronics".
Should docs be updated? Yes — formatter contract differs from segment4 Preprocessor contract.
```

## Suggested Doc Updates

```text
architecture.md — add PRICER_NEURAL_WEIGHTS_PATH to environment categories list.
agent_architecture.md — update model_breakdown semantics (0.0 = unavailable/deferred, not real value). Document warning grammar key:value format.
guides/4_search_and_pricing_tools.md — update Phase 4C status, note staged extraction, document new config var.
gameplan.md and PROJECT_STATUS.md — update after Codex approval (not implementer responsibility).
```

## Self-Check (Mandatory Before Handoff)

- **security**: No secrets read, printed, logged, committed, or exposed. No live model calls in default tests (`ENABLE_REAL_MODEL_CALLS=false`). No paid API calls. No AWS/Terraform/deploy. Neural deps optional, not in base install. ✓
- **data safety**: `error_detail` capped at 200 chars, no raw stack traces, no secrets, no huge paths. Warning grammar bounded. All failure paths return safe `PriceEstimateOutput`. ✓
- **reliability**: Neural unavailable → fallback markup + warnings, never crashes. Mock path completely unchanged. Job fail/success transitions preserved. Agent_runs audit rows preserved. ✓
- **performance**: Mock path zero overhead (no neural imports). Real path lazy-loads heavy deps on first call. No unbounded work, uncontrolled threads, polling loops. ✓
- **tests**: 125 default tests pass (mock/fixture-only). 4 opt-in neural smoke tests skipped by default. deep_neural_network NOT imported in default suite (verified by `test_neural_heavy_module_not_imported`). No secrets, live scraping, paid model calls, AWS, or external services. ✓

## Handoff

Ready for Codex re-review. No commits made.

Branch: TTTN
Files changed: 6 modified + 9 new (see git status)
Dependency: neural extras added to pyproject.toml, uv.lock auto-updated

## Codex Review Fixes (2026-07-20)

Findings addressed from phase_4c_real_pricing_codex_review.md:

1. **real_estimator.py fallback deal_score**: `_assemble_output` fallback path now always returns `deal_score="ok"`, regardless of computed score. Previously `sale_price_usd=0.0` returned `"overpriced"` via `_compute_deal_score`. Fixed by inlining `deal_score="ok"` in the fallback branch.

2. **tool.py docstring**: Removed stale `Raises: NotImplementedError` section. Updated to describe Phase 4C.1 dispatch behavior.

3. **missing_dependency adapter test**: Added `TestNeuralAdapterMissingDependency` class (2 tests) using `monkeypatch.setattr(builtins, "__import__", ...)` to block torch import and verify `missing_dependency` error_code + bounded `error_detail`.

4. **app.db**: Removed `backend/database/app.db` and added `app.db`/`app.db-journal` patterns to root `.gitignore`.

Updated test count: 127 passed, 12 skipped.
