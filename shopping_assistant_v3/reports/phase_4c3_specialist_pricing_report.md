# Phase 4C.3: Specialist Price Estimator Extraction — Implementation Report

## Phase

`Phase 4C.3: Specialist Price Estimator Extraction — Specialist Adapter + Boundary`

Implementer: DeepSeek

Date: 2026-07-21

Branch: TTTN

Commit reviewed: not committed yet

## Tom Tat

Implemented Specialist price estimator extraction (milestone 4C.3) behind `ENABLE_REAL_MODEL_CALLS=true`. Mock path unchanged. Specialist adapter lazy-loads Modal on first call.

Key behaviors:
- **Mock path (default)**: JSON fixture lookup + deterministic fallback rules — completely unchanged from Phase 4A.
- **Real path**: All 3 adapters attempted (Frontier, Specialist, Neural). If all 3 succeed → ensemble formula `0.8*f + 0.1*s + 0.1*n`. If partial → priority fallback: `frontier > specialist > neural > 5% markup`. Exactly one `ensemble_partial:<mode>` warning + model-specific unavailable codes.
- Specialist adapter copy+adapts `SpecialistAgent` logic from `segment4/price_agents/specialist_agent.py` — Modal `Cls.from_name()` + `.price.remote()`. No runtime imports from segment4.
- Heavy dependency (modal) is optional (`[project.optional-dependencies] specialist`) and lazy-loaded only inside `SpecialistPriceAdapter._load()`.
- `_assemble_output` now accepts 4 params: `product, frontier_result, neural_result, specialist_result`.
- Model breakdown shows only contributing model values (non-winning = 0.0).
- Full ensemble success state has NO `ensemble_partial` warning — tested by absence.
- Warning `specialist_unavailable:deferred_to_4c3` removed entirely — replaced with real error codes.
- Warning grammar `key:value` (no space after colon) preserved, consistent with 4C.1 and 4C.2.

## Files Da Tao

```text
backend/tools/price_estimator/specialist/__init__.py — package init (stdlib only, no Modal import)
backend/tools/price_estimator/specialist/adapter.py — SpecialistEstimateResult + SpecialistPriceAdapter (_sanitize_detail, _load, try_estimate)
tests/test_real_pricing_specialist.py — 14 mock-only specialist adapter tests (no Modal)
tests/test_real_pricing_specialist_smoke.py — 2 opt-in specialist smoke tests (skipped by default)
```

## Files Da Sua

```text
backend/shared/config.py — added PRICER_SPECIALIST_SERVICE="", PRICER_SPECIALIST_CLASS=""
backend/tools/price_estimator/real_estimator.py — _assemble_output accepts 4th param, new assembly policy with specialist priority chain, estimate_price_real attempts all 3 adapters
pyproject.toml — added [project.optional-dependencies] specialist = ["modal>=0.60.0"]
.env.example — added PRICER_SPECIALIST_SERVICE and PRICER_SPECIALIST_CLASS placeholders
tests/test_real_pricing.py — updated all 7 existing assembly tests to pass 4th param, added 8 new specialist tests, updated fallback/warnings/dispatch/guard tests
```

## Adapted Functions (segment4 → V3)

| segment4 | V3 | Notes |
|---|---|---|
| `SpecialistAgent.__init__()` | `SpecialistPriceAdapter.__init__(service_name, class_name)` | Config-based instead of hardcoded. Lazy init pattern mirrors frontier/neural adapters. |
| `SpecialistAgent.price(description)` | `SpecialistPriceAdapter.try_estimate(text)` | Never raises. Returns `SpecialistEstimateResult` with availability metadata. |
| `modal.Cls.from_name("pricer-service", "Pricer")` | Same, via lazy import | Service/class names from config, default empty. |
| `EnsembleAgent.price()` weighted combination | `_assemble_output()` in real_estimator.py | All-3 ensemble formula when all available. Priority fallback when partial. |

Not extracted:
- `EnsembleAgent` full class (orchestration is in `estimate_price_real`).
- `Preprocessor` (V3 uses deterministic formatter from 4C.1).
- `Modal` deployment/training (V3 only calls existing Modal service).

## Assembly Policy (Final)

| Condition | Estimated Value | Breakdown | Warnings |
|---|---|---|---|
| All 3 available | `0.8*f + 0.1*s + 0.1*n` | All 3 values | None (success state) |
| Frontier available (partial) | frontier value | frontier only | `ensemble_partial:frontier_only` + unavailable codes |
| Specialist available (f+s unavailable) | specialist value | specialist only | `ensemble_partial:specialist_only` + unavailable codes |
| Neural available (f+s unavailable) | neural value | neural only | `ensemble_partial:neural_only` + unavailable codes |
| None available | 5% markup | all 0.0 | `ensemble_partial:fallback_only` + `real_pricing_fallback_used:sale_price_markup` + unavailable codes |

## Warning Taxonomy (Final 4C.3)

```text
# Ensemble state (exactly one in partial cases)
ensemble_partial:frontier_only
ensemble_partial:specialist_only        # NEW
ensemble_partial:neural_only
ensemble_partial:fallback_only

# Model-specific unavailable
frontier_unavailable:<code>
specialist_unavailable:missing_service_config   # NEW
specialist_unavailable:missing_dependency       # NEW
specialist_unavailable:modal_error              # NEW
neural_unavailable:<code>

# Fallback
real_pricing_fallback_used:sale_price_markup
```

Removed: `specialist_unavailable:deferred_to_4c3`

## CodeGraph Evidence

**Pre-implementation (baseline Phase 4C.2):**
```text
codegraph status shopping_assistant_v3 → 40 files, 605 nodes, 1,295 edges
codegraph status segment4 → 24 files, 360 nodes, 718 edges (up to date)
```

**segment4 Specialist flow (used for extraction):**
```text
codegraph explore "How does SpecialistAgent connect to Modal and how does
EnsembleAgent combine specialist price with other models?"
→ SpecialistAgent.__init__ → modal.Cls.from_name() → Pricer()
→ SpecialistAgent.price → pricer.price.remote(description) → float
→ EnsembleAgent.price: specialist+frontier+neural → 0.8*f + 0.1*s + 0.1*n
→ 2 callers, 0 tests (unchanged segment4)
```

**Post-implementation:**
```text
codegraph sync shopping_assistant_v3 → 7 changed files (+4 added, 3 modified), 173 nodes
```

## Commands Da Chay

```bash
# Mock-only specialist + real pricing tests
uv run pytest tests/test_real_pricing.py tests/test_real_pricing_specialist.py -v
# Result: 72 passed, 0 failed

# Full default test suite
uv run pytest tests/ -v
# Result: 171 passed, 18 skipped, 0 failed

# CodeGraph sync
codegraph sync shopping_assistant_v3
# Result: 4 added, 3 modified — 173 nodes
```

## Tests Da Chay

**Mock-only (default): 171 passed**

- `tests/test_real_pricing.py` — 57 tests (15 Assembly incl. 8 new specialist, formatter, fallback, warnings, adapters, dispatch, guards)
- `tests/test_real_pricing_specialist.py` — 14 tests (SpecialistEstimateResult, missing config, missing dependency, sanitized error, config defaults, lazy import guard)
- `tests/test_api.py` — 22 tests (unchanged)
- `tests/test_tools.py` — 38 tests (unchanged)
- `tests/test_worker.py` — 20 tests (unchanged)
- `tests/test_repository.py` — 8 tests (unchanged)

**Opt-in smoke (skipped by default): 18 skipped**

- `tests/test_real_pricing_frontier.py` — 4 skipped (ENABLE_REAL_MODEL_CALLS not set)
- `tests/test_real_pricing_neural.py` — 4 skipped (ENABLE_REAL_MODEL_CALLS not set)
- `tests/test_real_pricing_specialist_smoke.py` — 2 skipped (ENABLE_REAL_MODEL_CALLS not set)
- `tests/test_real_search.py` — 8 skipped (ENABLE_REAL_SEARCH not set)

## Bang Chung Verification

- All 171 mock-only tests pass without Modal, network, secrets, or paid model calls.
- `modal` module confirmed NOT imported in default test suite (lazy import guard).
- Warning grammar `key:value` verified — no spaces in keys across all warnings.
- `specialist_unavailable:deferred_to_4c3` confirmed absent — no legacy warning leakage.
- `_assemble_output` pure function — testable without any heavy deps.
- Full ensemble success has zero `ensemble_partial` warnings (tested by string absence).
- Partial cases have exactly one `ensemble_partial:*` warning (tested by count).
- Model breakdown shows only contributing model values.
- All 3 adapters follow identical pattern: lazy _load(), try_estimate() never raises, fail-fast on missing config.
- `segment4/` unchanged — confirmed via git status.
- No live scraping, no paid model calls, no AWS/Terraform/deploy in default tests.

## Self-Check Before Handoff

- **security**: No secrets read, printed, logged, committed, or exposed via API. Config keys default empty. Modal token/env not required. `_sanitize_detail` bounds all error messages to 200 chars, single-line. ✓
- **data safety**: All payloads safe. Error messages sanitized. No raw exceptions in outputs. ✓
- **reliability**: All adapter failure paths deterministic. Idempotent calls (same adapter returns consistent errors). Job cannot be stuck — fallback always produces valid PriceEstimateOutput. ✓
- **performance**: Lazy imports prevent heavy deps at module load. Missing config returns immediately (no network). All 3 adapters attempted in opt-in real mode — documented as intentional extra cost for ensemble accuracy. ✓
- **tests**: 171 mock-only default tests (0 network, 0 secrets, 0 paid calls). 18 opt-in smoke tests skipped by default. No Modal/OpenAI/ChromaDB/network in any default test. ✓

## Known Issues

Khong co known issues.

## Deviations From Guide

```text
Guide expectation: Phase 4C.3 only. Phase 4 guide says "Adapt/wrap Specialist model calls."
Actual implementation: Full specialist adapter with lazy Modal import, plus _assemble_output update to 4-param with all-3 ensemble formula.
Reason: Phase 4C.2 already had Frontier + Neural. Adding Specialist naturally completes the ensemble. Assembly update was required to integrate the 3rd model.
Should docs be updated? yes — Phase 4 guide should note that 4C.3 completes the 3-model ensemble boundary.
```

```text
Guide expectation: Phase 4 guide mentions "GPT top-deal selector from segment4 may belong to Router/tool orchestration later."
Actual implementation: Not extracted. Deferred to Phase 5.
Reason: Top-deal selection is a Router concern, not a pricing concern.
Should docs be updated? no — already documented as future work in Phase 4 guide.
```

## Suggested Doc Updates

```text
gameplan.md — update Current Phase Status to note 4C.3 completion.
guides/4_search_and_pricing_tools.md — mark 4C.3 as completed in Phase 4 scope section.
PROJECT_STATUS.md — Codex to update after review/approval.
```

## Reviewer Checklist

Reviewer nen kiem tra:

- Scope nam trong approved Phase 4C.3. ✓
- Khong co file `segment4/` nao thay doi. ✓
- Khong co file `shopping_assistant_v2/` nao thay doi. ✓
- Khong co secrets nao bi doc, in, hoac commit. ✓
- Default tests khong goi paid APIs hoac live scraping. ✓
- API/schema/tool contracts khop guide lien quan. ✓
- Failure paths luu safe errors. ✓
- Logs/audit events co `job_id` o noi bat buoc. ✓
- Docs phan anh thay doi thuc te duoc cap nhat sau approval. (pending Codex)

Reviewer decision:

```text
Decision: pending review
Reviewer:
Date:
Required changes:
Docs to update after approval:
```
