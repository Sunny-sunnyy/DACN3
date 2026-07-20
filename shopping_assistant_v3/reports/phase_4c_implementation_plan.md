# Phase 4C: Real Price Estimator Extraction — Implementation Plan

## Phase

`Phase 4C: Real Price Estimator Extraction`

Implementer: DeepSeek

Date: 2026-07-20

Branch: TTTN

Status: plan — chưa implement

## Scope Phê Duyệt

Staged extraction qua 3 milestones:
- **4C.1** (current): Neural adapter + deterministic formatter + real estimator boundary
- **4C.2** (deferred): Frontier agent + ChromaDB RAG
- **4C.3** (deferred): Specialist Modal integration (document as external, không extract)

### 4C.1 scope cụ thể

1. **Copy+adapt** `DeepNeuralNetwork`, `ResidualBlock`, `DeepNeuralNetworkInference` từ `segment4/price_agents/deep_neural_network.py` vào V3 — giữ nguyên math gốc.
2. **Formatter** deterministic: `ProductCandidate` → structured text, không model call.
3. **Neural adapter**: lazy-load heavy deps, wrap `DeepNeuralNetworkInference`, fail safely thành `NeuralEstimateResult`.
4. **Real estimator orchestrator**: `estimate_price_real()` — gọi formatter → adapter → assemble `PriceEstimateOutput`.
5. **Wire vào `tool.py`**: dispatch real path khi `ENABLE_REAL_MODEL_CALLS=true`.
6. **Mock path unchanged**: fixture lookup + 10% fallback rule.

### Không làm trong 4C.1

- Không copy `deep_neural_network.pth` vào V3 (~1.1GB).
- Không import trực tiếp từ `segment4`.
- Không reweight ensemble (không `frontier * 0.9 + neural * 0.1`).
- Không mock Frontier/Specialist trong real mode — ghi nhận là missing components.
- Không thêm `torch`, `scikit-learn`, `numpy` vào base dependencies.

## Architecture

### Flow

```
estimate_price(input)
    |
    +-- ENABLE_REAL_MODEL_CALLS=false
    |       → mock path (fixture lookup + 10% fallback) — UNCHANGED
    |
    +-- ENABLE_REAL_MODEL_CALLS=true
            → real_estimator.estimate_price_real(product)
                |
                +-- formatter.format_product_for_pricing(product)
                |       → deterministic structured text
                |
                +-- neural_adapter.estimate(text) if weights_path exists
                |       → NeuralEstimateResult (value or error_code)
                |
                +-- _assemble_output(product, neural_result)
                        → PriceEstimateOutput with explicit warnings
```

### Files

```
NEW (5 files + 1 package):
  backend/tools/price_estimator/real_estimator.py     — orchestrator boundary
  backend/tools/price_estimator/formatter.py           — deterministic ProductCandidate → text
  backend/tools/price_estimator/neural/__init__.py     — package init
  backend/tools/price_estimator/neural/deep_neural_network.py — copy+adapt từ segment4
  backend/tools/price_estimator/neural/adapter.py      — lazy-load wrapper → NeuralEstimateResult
  tests/test_real_pricing.py                           — formatter + boundary + assembly + config tests
  tests/test_real_pricing_neural.py                    — opt-in neural smoke test (skipped by default)

MODIFIED (2 files):
  backend/tools/price_estimator/tool.py                — dispatch real_estimator khi flag=true
  backend/shared/config.py                             — thêm PRICER_NEURAL_WEIGHTS_PATH
  pyproject.toml                                       — thêm [project.optional-dependencies] neural group
```

## Contracts

### 1. Formatter (`formatter.py`)

```python
def format_product_for_pricing(product: ProductCandidate) -> str:
    """Convert a ProductCandidate into structured text for neural inference.

    Deterministic — no model calls, no network, no file I/O.
    Uses "Unknown" for missing fields. Returns "Unknown product" only
    when title, brand, and features are all empty.
    """
```

Template:
```text
Title: {title or "Unknown Product"}
Category: Unknown
Brand: {brand or "Unknown"}
Description: {title or "Unknown Product"} by {brand or "Unknown"}, priced at ${sale_price_usd}
Details: {features or "No details available"}
```

Rules:
- Category luôn `"Unknown"` — trung thực, không bias neural model.
- Không return empty string.
- `sale_price_usd` format 2 chữ số thập phân, ghi `$0.00` nếu None.

### 2. Neural adapter (`neural/adapter.py`)

```python
@dataclass
class NeuralEstimateResult:
    value_usd: float | None = None
    available: bool = False
    error_code: str | None = None       # bounded grammar: xem bảng dưới
    error_detail: str | None = None     # safe, max 200 chars, no stack trace


class NeuralPriceAdapter:
    def __init__(self, weights_path: str):
        """Store config. No file I/O, no heavy imports."""

    def estimate(self, text: str) -> NeuralEstimateResult:
        """Run inference. Lazy-loads deps + model on first call.

        Never raises — failures become NeuralEstimateResult metadata.
        """
```

`_load_model()` sequence:
```
1. if not weights_path or not Path(weights_path).exists():
     → NeuralEstimateResult(available=False, error_code="missing_weights_path")
2. try: import torch; from sklearn.feature_extraction.text import HashingVectorizer; import numpy
     → nếu ImportError: NeuralEstimateResult(available=False, error_code="missing_dependency")
3. from .deep_neural_network import DeepNeuralNetworkInference
   model.setup(); model.load(weights_path)
     → nếu lỗi: NeuralEstimateResult(available=False, error_code="model_load_failed")
4. model.inference(text)
     → thành công: NeuralEstimateResult(value_usd=float, available=True)
     → runtime error: NeuralEstimateResult(available=False, error_code="inference_failed")
```

**Module-level imports trong `adapter.py`:**
- `dataclasses`, `logging`, `pathlib` — stdlib only.
- KHÔNG import `torch`, `sklearn`, `numpy`, `deep_neural_network` ở top-level.
- `deep_neural_network.py` CHỈ được import trong `_load_model()`.

### 3. Real estimator orchestrator (`real_estimator.py`)

```python
def estimate_price_real(product: ProductCandidate) -> PriceEstimateOutput:
    """Real price estimation using available components.

    Current available: neural (via PRICER_NEURAL_WEIGHTS_PATH).
    Deferred: frontier (4C.2), specialist (4C.3).
    """
```

Decision table:

| Neural status | estimated_value_usd | breakdown.neural | Warnings |
|---|---|---|---|
| Available, success | `neural.value_usd` | `neural.value_usd` | `ensemble_partial:neural_only`, `frontier_unavailable:deferred_to_4c2`, `specialist_unavailable:deferred_to_4c3` |
| Unavailable | `round(sale_price*1.05,2)` | `0.0` | `neural_unavailable:<code>`, `real_pricing_fallback_used:sale_price_markup`, `frontier_unavailable:deferred_to_4c2`, `specialist_unavailable:deferred_to_4c3`, `ensemble_partial:fallback_only` |

Warning grammar (nhất quán `key:value`, không space sau dấu hai chấm — dễ assert trong tests):
```
frontier_unavailable:deferred_to_4c2
specialist_unavailable:deferred_to_4c3
ensemble_partial:neural_only
ensemble_partial:fallback_only
neural_unavailable:missing_weights_path
neural_unavailable:missing_dependency
neural_unavailable:model_load_failed
neural_unavailable:inference_failed
real_pricing_fallback_used:sale_price_markup
```

Fallback: `round(sale_price * 1.05, 2)` — markup 5% (khác mock 10%).
`deal_score = "ok"` khi dùng fallback.

Model breakdown trong real mode:
```python
ModelBreakdown(
    frontier=0.0,      # deferred, không phải giá trị thật
    specialist=0.0,    # deferred, không phải giá trị thật
    neural=neural_value_or_0,  # giá trị thật khi available
)
```

### 4. Config (`shared/config.py`)

```python
PRICER_NEURAL_WEIGHTS_PATH: str = os.getenv("PRICER_NEURAL_WEIGHTS_PATH", "")
```

### 5. Tool dispatch (`tool.py`)

```python
def estimate_price(input: PriceEstimateInput) -> PriceEstimateOutput:
    if ENABLE_REAL_MODEL_CALLS:
        # Phase 4C.1: real path with neural + fallback warnings
        from backend.tools.price_estimator.real_estimator import estimate_price_real
        return estimate_price_real(input.product)
    # ... mock path unchanged
```

## Dependency Strategy

### pyproject.toml — thêm `neural` vào block hiện có

File hiện tại (`pyproject.toml:14-18`):

```toml
[project.optional-dependencies]
dev = [
    "httpx>=0.28.0",
    "pytest>=8.0.0",
]
```

Chỉ thêm `neural` group, giữ nguyên `dev`:

```toml
[project.optional-dependencies]
dev = [
    "httpx>=0.28.0",
    "pytest>=8.0.0",
]
neural = [
    "torch>=2.0.0",
    "scikit-learn>=1.3.0",
    "numpy>=1.24.0",
]
```

Không thêm `pytest-asyncio` (không cần trong Phase 4C).

### Install commands

```bash
uv sync                          # mock path only, no neural deps
uv sync --extra dev              # dev deps for testing
uv sync --extra neural           # add neural deps
uv sync --extra dev --extra neural  # full setup
```

Không dùng `--all-extras` cho mock-only setup.

### Lazy import chain

```
tool.py ──import──> real_estimator.py ──import──> neural/adapter.py  [stdlib only, NO heavy deps]
                                                       │
                                                       │ _load_model() (private, lazy)
                                                       ▼
                                              neural/deep_neural_network.py  [torch, sklearn, numpy]
```

Mock path (`ENABLE_REAL_MODEL_CALLS=false`) không import `real_estimator`, không chạm neural.

## Verification

### Default tests — `uv run pytest tests/` (mock-only)

**Import rule:** `test_real_pricing.py` chỉ được import `neural/adapter.py` (stdlib-only). Không được import `neural/deep_neural_network.py` (kéo torch/sklearn/numpy). Có thể verify bằng assertion cuối test suite:

```python
def test_neural_heavy_module_not_imported():
    """Default suite must not pull torch/sklearn via deep_neural_network."""
    assert "backend.tools.price_estimator.neural.deep_neural_network" not in sys.modules
```

| Test | Count | Nội dung |
|---|---|---|
| `TestFormatter` | 5 | Input đủ/tối thiểu/rỗng → structured text đúng format |
| `TestFormatterMissingFields` | 3 | Thiếu brand/features/price → "Unknown" fallback fields |
| `TestFormatterAllEmpty` | 1 | Title/brand/features đều rỗng → "Unknown product" |
| `TestRealEstimatorFallback` | 3 | Real mode + missing weights → fallback markup + đủ 5 warnings |
| `TestRealEstimatorWarnings` | 2 | Warning grammar chính xác, không có warning thừa/thiếu |
| `TestAssembly` | 3 | `_assemble_output(product, NeuralEstimateResult)` → verify estimated_value, breakdown, discount, deal_score, warnings |
| `TestNeuralAdapterMissingWeights` | 2 | Weights path rỗng/không tồn tại → `available=False`, `error_code="missing_weights_path"` |
| `TestNeuralAdapterSanitizedError` | 2 | Monkeypatch import để test `missing_dependency`, verify `error_detail` bounded |
| `TestConfig` | 2 | `PRICER_NEURAL_WEIGHTS_PATH` default empty, load từ env |
| `TestRealModeDispatch` | 1 | `ENABLE_REAL_MODEL_CALLS=true` → gọi real path |
| `TestMockPathUnchanged` | verify | Các test mock hiện có vẫn pass, fixture lookup + fallback rule không đổi |
| **Total (est.)** | **~24 new** | + all existing tests unchanged |

### Opt-in real neural smoke test — `tests/test_real_pricing_neural.py`

```python
def _neural_deps_available() -> bool:
    """Return True if torch, sklearn, numpy are installed (neural extras)."""
    try:
        import torch  # noqa: F401
        import sklearn  # noqa: F401
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = [
    pytest.mark.skipif(
        os.getenv("ENABLE_REAL_MODEL_CALLS") != "true",
        reason="Requires ENABLE_REAL_MODEL_CALLS=true",
    ),
    pytest.mark.skipif(
        not os.getenv("PRICER_NEURAL_WEIGHTS_PATH"),
        reason="Requires PRICER_NEURAL_WEIGHTS_PATH set",
    ),
    pytest.mark.skipif(
        not Path(os.getenv("PRICER_NEURAL_WEIGHTS_PATH", "")).exists(),
        reason="Weights file does not exist at configured path",
    ),
    pytest.mark.skipif(
        not _neural_deps_available(),
        reason="Requires neural extras installed (uv sync --extra neural)",
    ),
]
```

3 tests:
1. Neural adapter loads weights và inference trả về float > 0
2. `estimate_price_real()` full flow với neural success → `PriceEstimateOutput` có `estimated_value_usd = neural_value`
3. `estimate_price_real()` với input tối thiểu → vẫn ra output hợp lệ

Chạy:
```bash
ENABLE_REAL_MODEL_CALLS=true \
PRICER_NEURAL_WEIGHTS_PATH=/home/hieu0606sunny/price2026wsl/tech2ai/segment4/deep_neural_network.pth \
uv run pytest tests/test_real_pricing_neural.py -v
```

### Fake runner strategy

Không inject fake model vào adapter. Test assembly như pure function:

```python
def test_assemble_success():
    """Neural success → output uses neural_value, warns about missing components."""
    product = ProductCandidate(source="BestBuy", title="Test", sale_price_usd=100.0)
    neural_result = NeuralEstimateResult(value_usd=150.0, available=True)
    output = _assemble_output(product, neural_result)
    assert output.estimated_value_usd == 150.0
    assert output.model_breakdown.neural == 150.0
    assert output.model_breakdown.frontier == 0.0
    assert output.model_breakdown.specialist == 0.0
    assert output.discount_usd == 50.0
    assert output.deal_score == "good"
    assert "ensemble_partial:neural_only" in output.warnings


def test_assemble_fallback():
    """Neural unavailable → fallback markup + ok score."""
    product = ProductCandidate(source="BestBuy", title="Test", sale_price_usd=100.0)
    neural_result = NeuralEstimateResult(
        available=False, error_code="missing_weights_path"
    )
    output = _assemble_output(product, neural_result)
    assert output.estimated_value_usd == 105.0  # 5% markup
    assert output.deal_score == "ok"
    assert "real_pricing_fallback_used:sale_price_markup" in output.warnings
    assert "neural_unavailable:missing_weights_path" in output.warnings
```

Adapter test chỉ cover missing weights path và sanitized failure mapping (monkeypatch import).

## Implementation Order

```
Task 1: dependency setup
  - Đọc pyproject.toml hiện tại, thêm neural optional group
  - uv lock

Task 2: config
  - Thêm PRICER_NEURAL_WEIGHTS_PATH vào shared/config.py

Task 3: formatter
  - Tạo formatter.py
  - Verify: import + chạy thử với ProductCandidate fixture

Task 4: neural deep_neural_network.py
  - Copy+adapt từ segment4/price_agents/deep_neural_network.py
  - Giữ nguyên ResidualBlock, DeepNeuralNetwork, DeepNeuralNetworkInference, Y_STD, Y_MEAN

Task 5: neural adapter
  - Tạo adapter.py với NeuralEstimateResult + NeuralPriceAdapter
  - Lazy import trong _load_model()

Task 6: real estimator orchestrator
  - Tạo real_estimator.py với estimate_price_real() + _assemble_output()

Task 7: tool dispatch
  - Sửa tool.py: thay NotImplementedError bằng dispatch tới real_estimator

Task 8: tests — default
  - Tạo test_real_pricing.py với tất cả test classes
  - Chạy uv run pytest tests/test_real_pricing.py -v

Task 9: tests — opt-in neural smoke
  - Tạo test_real_pricing_neural.py với skip conditions

Task 10: full verification
  - uv run pytest tests/ (toàn bộ, mock-only)
  - Verify segment4 unchanged
  - Verify không có segment4 import nào trong V3
  - CodeGraph sync + status

Task 11: implementation report
  - Viết phase_4c_real_pricing_report.md theo template
```

## Self-Check Preview

- **security**: Không secrets, không live model calls trong default tests. Weights path từ env, không hard-code.
- **data safety**: `error_detail` bounded ≤ 200 chars, không raw stack trace. Warnings dùng fixed grammar.
- **reliability**: Neural unavailable → fallback + warnings, không crash. Mock path unchanged.
- **performance**: Mock path không import heavy deps. Neural lazy-load chỉ khi thực sự gọi real path.
- **tests**: Default mock-only. Opt-in neural smoke skipped by default.

## Deviations From Guide

```text
Guide expectation: Extract cả Preprocessor + Frontier + Specialist + Neural.
Actual implementation: Chỉ extract Neural. Frontier deferred 4C.2, Specialist deferred 4C.3.
Preprocessor → deterministic formatter thay vì LiteLLM call.
Reason: Staged extraction per user approval. Preprocessor model call không cần thiết cho MVP real path.
Should docs be updated? Có — model_breakdown semantics khác guide (0.0 nghĩa là deferred, không phải real value).
```
