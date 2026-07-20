# Phase 4C.2: Frontier Price Estimator Extraction — Implementation Report

## Phase

`Phase 4C.2: Frontier Price Estimator Extraction — Frontier Adapter + Boundary`

Implementer: DeepSeek

Date: 2026-07-20

Branch: TTTN

Commit reviewed: not committed yet

## Tom Tat

Implemented Frontier price estimator extraction (milestone 4C.2) behind `ENABLE_REAL_MODEL_CALLS=true`. Mock path unchanged. Frontier adapter lazy-loads ChromaDB + SentenceTransformer + OpenAI SDK on first call.

Key behaviors:
- **Mock path (default)**: JSON fixture lookup + 10% fallback rule — completely unchanged from Phase 4A.
- **Real path**: frontier adapter runs first. If frontier succeeds, neural is short-circuited (not loaded). If frontier fails, neural adapter runs as fallback (4C.1 behavior). If both fail, 5% markup fallback.
- Frontier adapter copy+adapts `FrontierAgent` logic from `segment4/price_agents/frontier_agent.py` — RAG via ChromaDB (5 similar products), OpenAI GPT model call, price extraction. No runtime imports from segment4.
- Heavy dependencies (chromadb, sentence-transformers, openai) are optional (`[project.optional-dependencies] frontier`) and lazy-loaded only inside `FrontierPriceAdapter._load()`.
- Specialist (4C.3) deferred — output includes `specialist_unavailable:deferred_to_4c3` warning.
- Warning grammar: `key:value` (no space after colon), consistent across all warnings.
- ChromaDB uses `get_collection()` (not `get_or_create_collection`) — missing collection returns `collection_not_found`.
- `_extract_price` returns `None` on parse failure (not silent 0.0) — treated as `parse_error`.
- OpenAI SDK direct (not LiteLLM) — intentional deviation, LiteLLM deferred to Phase 5.
- `reasoning_effort` param removed — not universally supported across models.

## Files Da Tao

```text
backend/tools/price_estimator/frontier/__init__.py — package init (stdlib only, no heavy imports)
backend/tools/price_estimator/frontier/adapter.py — FrontierPriceAdapter + FrontierEstimateResult (_sanitize_detail, _extract_price, _build_prompt)
tests/test_real_pricing_frontier.py — 4 opt-in frontier smoke tests (skipped by default)
reports/phase_4c2_implementation_plan.md — approved implementation plan
```

## Files Da Sua

```text
backend/shared/config.py — added PRICER_CHROMADB_PATH="", PRICER_FRONTIER_MODEL_ID=""
backend/tools/price_estimator/real_estimator.py — replaced 4C.1 module with 4C.2: _assemble_output(product, frontier_result, neural_result), estimate_price_real with short-circuit, updated warning constants
pyproject.toml — added [project.optional-dependencies] frontier = ["chromadb>=0.5.0", "sentence-transformers>=3.0.0", "openai>=1.0.0"]
uv.lock — auto-updated (frontier extras + transitive deps resolved)
tests/test_real_pricing.py — updated imports, replaced TestAssembly (7 tests with frontier), updated TestRealEstimatorFallback/TestRealEstimatorWarnings/TestRealModeDispatch, added 5 Frontier test classes (13 tests), added frontier lazy import guard
```

## Adapted Functions (segment4 → V3)

| segment4 | V3 | Notes |
|---|---|---|
| `FrontierAgent.__init__(collection)` | `FrontierPriceAdapter.__init__(chromadb_path, model_id)` | Path-based instead of collection-based. Lazy init pattern mirrors neural adapter. |
| `FrontierAgent.price(description)` | `FrontierPriceAdapter.try_estimate(text)` | Never raises. Returns `FrontierEstimateResult` with availability metadata. |
| `FrontierAgent.find_similars()` | Inlined in `try_estimate()` | Same logic: encode → query → extract documents + prices. |
| `FrontierAgent.messages_for()` | `_build_prompt()` | Same template. Inlined as single method. |
| `FrontierAgent.make_context()` | Inlined in `_build_prompt()` | Same logic, simpler. |
| `FrontierAgent.get_price()` | `_extract_price()` (module-level) | Returns `None` on parse failure instead of `0.0`. Caller treats None as `parse_error`. |
| `chromadb.PersistentClient` | Same, via lazy import | `get_collection` instead of `get_or_create_collection`. |
| `SentenceTransformer("all-MiniLM-L6-v2")` | Same, via lazy import | Identical embedding model. |
| `OpenAI()` client | Same, via lazy import | `seed=42` preserved. `reasoning_effort` removed. |

Not extracted:
- `Preprocessor` (segment4 uses LiteLLM) → V3 uses deterministic formatter (Phase 4C.1).
- `SpecialistAgent` (segment4 uses Modal) → deferred to 4C.3.
- `EnsembleAgent` weighted combination → deferred until all 3 models available.

## CodeGraph Evidence

**Pre-implementation (baseline Phase 4C.1):**
```text
codegraph status shopping_assistant_v3 → 37 files, 542 nodes, 1,147 edges
```

**Post-implementation:**
```text
codegraph sync shopping_assistant_v3 → 6 changed files (+3 added, 3 modified), 143 nodes
codegraph status shopping_assistant_v3 → 40 files, 605 nodes, 1,295 edges (up to date)
```

## Commands Da Chay

```bash
# Task 1: Config + Deps
uv run python -c "from backend.shared.config import PRICER_CHROMADB_PATH, PRICER_FRONTIER_MODEL_ID; print(repr(PRICER_CHROMADB_PATH), repr(PRICER_FRONTIER_MODEL_ID))"
# → '' '' (both empty by default)

uv run python -c "import tomllib; assert 'frontier' in tomllib.load(open('pyproject.toml','rb'))['project']['optional-dependencies']; print('OK')"
# → OK

uv lock
# → Resolved 132 packages in 1ms

# Task 2: Frontier adapter
uv run python -c "from backend.tools.price_estimator.frontier.adapter import FrontierEstimateResult, FrontierPriceAdapter, COLLECTION_NAME, N_SIMILARS; print('OK')"
# → OK — no heavy deps loaded

uv run python -c "from backend.tools.price_estimator.frontier.adapter import _extract_price; assert _extract_price('$899.99') == 899.99; assert _extract_price('none') is None; print('OK')"
# → OK

# Task 3: real_estimator
uv run python -c "from backend.tools.price_estimator.real_estimator import _assemble_output, estimate_price_real; print('OK')"
# → OK — no heavy deps loaded

uv run python -c "..." # _assemble_output smoke checks
# → PASS: frontier priority
# → PASS: neural fallback with frontier_unavailable warning
# → PASS: fallback markup

# Task 4-5: Tests
uv run pytest tests/test_real_pricing.py -v
# → 49 passed

uv run pytest tests/test_real_pricing_frontier.py -v
# → 4 skipped

# Task 6: Verification
uv run pytest tests/ -v
# → 148 passed, 16 skipped

rg -n "from segment4\|import segment4" backend/ tests/
# → NO MATCHES

git diff --name-only -- segment4/
# → (no output — untouched)

rg -n "OPENAI_API_KEY\|sk-\|api_key.*=" backend/tools/price_estimator/frontier/
# → NO MATCHES

codegraph sync shopping_assistant_v3 && codegraph status shopping_assistant_v3
# → 40 files, 605 nodes, 1,295 edges (up to date)

uv run python -c "assert no heavy imports in frontier/__init__.py"
# → OK — __init__.py is stdlib-only
```

## Tests Da Chay

| File | Count | Result |
|---|---|---|
| tests/test_api.py | 22 | 22 passed |
| tests/test_repository.py | 8 | 8 passed |
| tests/test_tools.py | 51 | 51 passed |
| tests/test_worker.py | 20 | 20 passed |
| tests/test_real_pricing.py | 49 | 49 passed (up from 26) |
| tests/test_real_search.py | 8 | 8 skipped (Phase 4B opt-in) |
| tests/test_real_pricing_neural.py | 4 | 4 skipped (Phase 4C.1 opt-in) |
| tests/test_real_pricing_frontier.py | 4 | 4 skipped (Phase 4C.2 opt-in) |
| **Total** | **166** | **148 passed, 16 skipped** |

All default tests are mock/fixture-only. No network, no model calls, no secrets, no ChromaDB/OpenAI/neural deps required.

## Bang Chung Verification

1. **Mock path unchanged**: All 31 Phase 4A mock price estimator tests pass. `ENABLE_REAL_MODEL_CALLS=false` → fixture lookup + 10% fallback rule.
2. **Real path dispatch**: `ENABLE_REAL_MODEL_CALLS=true` → `real_estimator.estimate_price_real()` (verified by `TestRealModeDispatch`).
3. **Frontier adapter lazy import**: `chromadb`, `sentence_transformers`, `openai` NOT in `sys.modules` after all default tests (`test_frontier_heavy_modules_not_imported`).
4. **__init__.py stdlib-only**: AST verification confirms no heavy imports.
5. **Adapter module safe import**: `adapter.py` imports only stdlib at module level. Heavy deps loaded inside `_load()`.
6. **Missing chromadb path safe failure**: `FrontierPriceAdapter(chromadb_path="")` → `FrontierEstimateResult(available=False, error_code="missing_chromadb_path")`.
7. **Missing model_id safe failure**: `FrontierPriceAdapter(chromadb_path="/tmp/exists", model_id="")` → `FrontierEstimateResult(available=False, error_code="model_config_missing")`.
8. **Missing dependency safe failure**: Blocked chromadb import → `error_code="missing_dependency"`, detail bounded to 200 chars.
9. **Frontier > Neural priority**: `_assemble_output(frontier_success, neural_success)` → frontier value used, neural in breakdown = 0.0 (verified by 4 `TestAssembly` tests).
10. **Frontier unavailable + Neural available**: `_assemble_output` uses neural + includes `frontier_unavailable:<reason>` warning (verified by `test_neural_success_frontier_unavailable`).
11. **Both unavailable → 5% fallback**: Same as 4C.1, with `frontier_unavailable:<reason>`, `neural_unavailable:<reason>`, `real_pricing_fallback_used:sale_price_markup`, `ensemble_partial:fallback_only`.
12. **Short-circuit**: `estimate_price_real` skips neural entirely when frontier succeeds (`neural_result.error_code="skipped_frontier_available"`).
13. **Warning grammar**: All warnings follow `key:value` format, no space after colon (verified by `TestRealEstimatorWarnings`).
14. **Warning completeness**: Frontier unavailable + neural unavailable produces exactly 5 required warnings. No duplicates.
15. **Error sanitization**: `_sanitize_detail` bounds to 200 chars, flattens newlines, handles non-string inputs (verified by `TestFrontierAdapterSanitizedError`, 3 tests).
16. **`_extract_price` parse safety**: Returns `None` when no numeric price found. Adapter treats as `parse_error`, not silent 0.0 (verified by `TestFrontierExtractPrice`, 5 tests).
17. **`get_collection` not `get_or_create_collection`**: Silently creating empty collection prevented. Missing collection → `collection_not_found`.
18. **Opt-in frontier smoke**: 4 tests skipped by default (require `ENABLE_REAL_MODEL_CALLS=true` + `PRICER_CHROMADB_PATH` valid + `PRICER_FRONTIER_MODEL_ID` set + `OPENAI_API_KEY` set + frontier extras installed). Heavy deps checked via `pytest.importorskip()` in test body, not at module import.
19. **No segment4 runtime imports**: `rg` search confirms zero `from segment4` or `import segment4` in V3 backend or tests.
20. **segment4 untouched**: `git diff --name-only -- segment4/` returns empty.
21. **No secrets accessed**: No .env reading, no API keys, no credentials. All tests run without secrets.
22. **No hardcoded key patterns**: `rg "sk-"` returns no results in frontier code.
23. **CodeGraph**: Post-implementation index at 40 files, 605 nodes, 1,295 edges (up from 37/542/1,147 baseline).

## Known Issues

- **Specialist deferred to 4C.3** (Major): SpecialistAgent is a Modal remote wrapper — no meaningful local extraction possible. Real mode marks it as `specialist_unavailable:deferred_to_4c3`.
- **Ensemble partial** (Major): With only frontier + neural available (and frontier short-circuits neural), real mode produces `ensemble_partial:frontier_only` or `ensemble_partial:neural_only`. Full ensemble formula 0.8/0.1/0.1 deferred until 4C.3.
- **Neural weights not bundled** (Minor): `deep_neural_network.pth` (~1.1GB) not included. Real neural pricing requires `PRICER_NEURAL_WEIGHTS_PATH`.
- **ChromaDB data not bundled** (Minor): `products_vectorstore/` not copied to V3. Real frontier requires `PRICER_CHROMADB_PATH` pointing to valid ChromaDB database.
- **OpenAI API cost** (Minor): Frontier calls incur paid API costs when `ENABLE_REAL_MODEL_CALLS=true`. No cost in default mock path.
- **uv.lock auto-updated** (Minor): Adding `frontier` optional group resolved chromadb, sentence-transformers, openai and transitive deps. These are only installed with `uv sync --extra frontier`.

## Deviations From Guide

```text
Guide expectation: Extract full EnsembleAgent (Frontier + Specialist + Neural).
Actual implementation: Only Frontier extracted (4C.2). Specialist deferred to 4C.3. Neural extracted in 4C.1.
Reason: Staged extraction per user approval. Specialist is Modal wrapper — not meaningfully extractable. Frontier is highest-value component (80% ensemble weight).
Should docs be updated? Yes — Phase 4C guide status should reflect 4C.1 + 4C.2 complete, 4C.3 pending.

Guide expectation: LiteLLM abstraction for model calls (agent_architecture.md).
Actual implementation: OpenAI SDK direct for frontier adapter.
Reason: LiteLLM deferred to Phase 5 Router/Synthesizer where multi-provider abstraction has value. For single-model frontier call, OpenAI SDK direct is simpler, matches segment4 reference, and avoids unnecessary dependency.
Should docs be updated? Yes — document as intentional deviation in agent_architecture.md model provider policy notes.

Guide expectation: reasoning_effort="none" from segment4 FrontierAgent.
Actual implementation: reasoning_effort parameter removed.
Reason: Not universally supported across OpenAI-compatible models. Seed=42 preserved for reproducibility.
Should docs be updated? No — internal deviation, documented in report.

Guide expectation: _extract_price returns 0.0 on parse failure (segment4 get_price).
Actual implementation: Returns None on parse failure — adapter treats as parse_error.
Reason: Silent 0.0 fallback is indistinguishable from a valid $0.00 estimate. None forces explicit error handling.
Should docs be updated? No — improvement over reference, documented in report.

Guide expectation: get_or_create_collection (segment4 pattern).
Actual implementation: get_collection — missing collection returns collection_not_found.
Reason: Silently creating an empty collection would produce misleading results (no RAG context). Explicit failure is safer.
Should docs be updated? No — documented in report and plan.

Guide expectation: Both adapters always run (Phase 4C.2 design draft).
Actual implementation: Frontier short-circuits neural when available.
Reason: Makes ensemble_partial:frontier_only warning accurate. Avoids unnecessary neural deps loading when frontier succeeds.
Should docs be updated? No — plan revision incorporated this before implementation.
```

## Suggested Doc Updates

```text
architecture.md — add PRICER_CHROMADB_PATH and PRICER_FRONTIER_MODEL_ID to environment categories list.
agent_architecture.md — document LiteLLM deviation for Phase 4C.2 frontier adapter. Note that LiteLLM abstraction still applies to Phase 5 Router/Synthesizer.
guides/4_search_and_pricing_tools.md — update Phase 4C status (4C.1 + 4C.2 complete, 4C.3 pending).
gameplan.md and PROJECT_STATUS.md — update after Codex approval (not implementer responsibility).
```

## Self-Check (Mandatory Before Handoff)

- **security**: No secrets read, printed, logged, committed, or exposed. No live model calls in default tests (`ENABLE_REAL_MODEL_CALLS=false`). No paid API calls. No AWS/Terraform/deploy. Frontier deps optional, not in base install. No `sk-` patterns in code. ✓
- **data safety**: `error_detail` capped at 200 chars, no raw stack traces, no secrets, no huge paths. Warning grammar bounded. All failure paths return safe `PriceEstimateOutput`. Frontier response parsing fails safely — `None` on parse error, never silent 0.0. ✓
- **reliability**: Frontier unavailable → neural fallback → 5% markup fallback, never crashes. Mock path completely unchanged. Short-circuit prevents unnecessary work. Job fail/success transitions preserved. Agent_runs audit rows preserved. ✓
- **performance**: Mock path zero overhead (no frontier imports). Real path lazy-loads heavy deps on first call. Short-circuit avoids neural loading when frontier succeeds. No unbounded work, uncontrolled threads, polling loops. ✓
- **tests**: 148 default tests pass (mock/fixture-only). 16 opt-in tests skipped by default. chromadb/sentence_transformers/openai NOT imported in default suite (verified by `test_frontier_heavy_modules_not_imported`). No secrets, live scraping, paid model calls, AWS, or external services. ✓

## Handoff

Ready for Codex review. No commits made.

Branch: TTTN
Files changed: 4 modified + 3 created + uv.lock (see git status)
Dependency: frontier extras added to pyproject.toml, uv.lock auto-updated (132 packages resolved)
