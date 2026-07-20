# Phase 4C.2: Frontier Price Estimator Extraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract FrontierAgent (GPT-5.1 + ChromaDB RAG with 5 similar products) from
segment4 into V3 as an independent opt-in adapter behind `ENABLE_REAL_MODEL_CALLS=true`,
following the same lazy-load boundary pattern as Phase 4C.1 neural adapter.

**Architecture:** Copy+adapt FrontierAgent logic into
`backend/tools/price_estimator/frontier/adapter.py` as a lazy-loading
`FrontierPriceAdapter`. Add `PRICER_CHROMADB_PATH` and `PRICER_FRONTIER_MODEL_ID` config.
Update `_assemble_output` to priority: frontier > neural > 5% fallback.
ChromaDB, sentence-transformers, openai are optional frontier extras, not base deps.

**Tech Stack:** Python 3.12, chromadb, sentence-transformers, openai SDK, all lazy-loaded.

## Global Constraints

- Không runtime import từ `segment4/`. Copy+adapt hẹp, ghi rõ trong report.
- ChromaDB path configurable qua `PRICER_CHROMADB_PATH=""`, không copy data vào V3.
- `PRICER_FRONTIER_MODEL_ID` configurable, default `""` (yêu cầu env var trong real mode).
- Optional deps `[frontier]`: `chromadb>=0.5.0`, `sentence-transformers>=3.0.0`, `openai>=1.0.0`.
- Lazy import: `frontier/__init__.py` stdlib-only, `adapter.py` import heavy deps trong `_load()`.
- Default tests mock-only: không load ChromaDB, không gọi OpenAI, không cần secrets.
- Warning grammar `key:value` (không space sau dấu `:`).
- Priority: frontier > neural > fallback 5% markup. Không renormalize, không average.
- `_assemble_output` signature: `(product, frontier_result, neural_result)`.
- Opt-in smoke tests skip mặc định.
- `segment4/` untouched. Không đọc/in secrets.
- LiteLLM deviation: intentional, ghi rõ trong report.

---

### Task 1: Config + Optional Deps

**Files:**
- Modify: `backend/shared/config.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `PRICER_CHROMADB_PATH: str`, `PRICER_FRONTIER_MODEL_ID: str`
- Produces: `[project.optional-dependencies] frontier = [...]`

- [ ] **Step 1: Add config vars to `backend/shared/config.py`**

Add after line 38 (`PRICER_NEURAL_WEIGHTS_PATH`):

```python
# Frontier pricing (Phase 4C.2): path to ChromaDB vectorstore directory.
# No default — real frontier requires explicit path via env.
PRICER_CHROMADB_PATH: str = os.getenv("PRICER_CHROMADB_PATH", "")

# Frontier pricing (Phase 4C.2): model ID for OpenAI-compatible API call.
# No default — real frontier requires explicit model via env.
PRICER_FRONTIER_MODEL_ID: str = os.getenv("PRICER_FRONTIER_MODEL_ID", "")
```

- [ ] **Step 2: Add frontier extras to `pyproject.toml`**

After the `neural` block (line 22):

```toml
frontier = [
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "openai>=1.0.0",
]
```

- [ ] **Step 3: Verify imports**

```bash
cd shopping_assistant_v3 && uv run python -c "from backend.shared.config import PRICER_CHROMADB_PATH, PRICER_FRONTIER_MODEL_ID; print(repr(PRICER_CHROMADB_PATH), repr(PRICER_FRONTIER_MODEL_ID))"
```

Expected: `'' ''` (both empty by default)

- [ ] **Step 4: Lock dependencies**

```bash
cd shopping_assistant_v3 && uv lock
```

Expected: `uv.lock` updated with frontier extras resolved. Report `uv.lock` change in implementation report.

- [ ] **Step 5: Verify pyproject.toml syntax**

```bash
cd shopping_assistant_v3 && uv run python -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
extras = data['project']['optional-dependencies']
assert 'frontier' in extras
assert 'chromadb' in extras['frontier'][0]
assert 'sentence-transformers' in extras['frontier'][1]
assert 'openai' in extras['frontier'][2]
print('OK')
"
```

Expected: `OK`

---

### Task 2: Frontier Adapter Package

**Files:**
- Create: `backend/tools/price_estimator/frontier/__init__.py`
- Create: `backend/tools/price_estimator/frontier/adapter.py`

**Interfaces:**
- Produces: `FrontierEstimateResult` dataclass (`value_usd`, `available`, `error_code`, `error_detail`)
- Produces: `FrontierPriceAdapter(chromadb_path, model_id)` class with `try_estimate(text: str) -> FrontierEstimateResult`
- Produces: `COLLECTION_NAME = "products"`, `N_SIMILARS = 5`

- [ ] **Step 1: Write `__init__.py`**

```python
"""Frontier pricing package — Phase 4C.2.

Import nothing heavy here. chromadb, sentence_transformers, and openai
are lazy-loaded by adapter.py on first try_estimate() call.
"""
```

- [ ] **Step 2: Write `adapter.py`**

```python
"""Frontier Price Adapter — lazy-loading wrapper for ChromaDB RAG + OpenAI estimator.

Module-level imports are stdlib only. Heavy dependencies (chromadb,
sentence_transformers, openai) are imported lazily inside _load() on
first try_estimate() call. This keeps the mock path free of frontier deps.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("shopping_assistant_v3.frontier")

# Collection name used by segment4 ChromaDB vectorstore.
COLLECTION_NAME = "products"
# Number of similar products retrieved for RAG context.
N_SIMILARS = 5


@dataclass
class FrontierEstimateResult:
    """Result of a frontier price estimation attempt.

    When available=False, error_code describes the failure mode using a
    bounded grammar. error_detail is capped at 200 chars and must never
    contain raw exceptions, stack traces, or secrets.
    """

    value_usd: float | None = None
    available: bool = False
    error_code: str | None = None
    error_detail: str | None = None


def _sanitize_detail(raw: str) -> str:
    """Return a bounded, safe detail string (max 200 chars, single line)."""
    cleaned = str(raw).replace("\n", " ").replace("\r", "").strip()
    if len(cleaned) > 200:
        cleaned = cleaned[:197] + "..."
    return cleaned


def _extract_price(text: str) -> float | None:
    """Extract the first USD price from a model response string.

    Returns None if no numeric price is found — caller should treat this
    as a parse_error, not silently return 0.0.
    """
    s = text.replace("$", "").replace(",", "")
    match = re.search(r"[-+]?\d*\.\d+|\d+", s)
    if match:
        return float(match.group())
    return None


class FrontierPriceAdapter:
    """Lazy-loading adapter for the Frontier (GPT + ChromaDB RAG) estimator.

    Heavy dependencies (chromadb, sentence_transformers, openai) are
    imported only when try_estimate() is first called — never at
    module import time.

    Usage:
        adapter = FrontierPriceAdapter(
            chromadb_path="/path/to/products_vectorstore",
            model_id="gpt-5.1",
        )
        result = adapter.try_estimate("Title: Laptop ...")
        if result.available:
            print(result.value_usd)
    """

    def __init__(self, chromadb_path: str, model_id: str) -> None:
        """Store config. No heavy imports, no file I/O at init."""
        self._chromadb_path = chromadb_path
        self._model_id = model_id
        self._collection = None          # chromadb Collection or None
        self._embed_model = None         # SentenceTransformer or None
        self._openai_client = None       # OpenAI client or None
        self._init_error: FrontierEstimateResult | None = None
        self._init_attempted = False

    def try_estimate(self, text: str) -> FrontierEstimateResult:
        """Run frontier inference. Lazy-loads deps + model on first call.

        Never raises — failures become FrontierEstimateResult metadata.
        """
        if not self._init_attempted:
            self._init_attempted = True
            self._load()

        if self._init_error is not None:
            return self._init_error

        try:
            # Step 1: embed query
            vector = self._embed_model.encode([text])

            # Step 2: query ChromaDB for similar products
            results = self._collection.query(
                query_embeddings=vector.astype(float).tolist(),
                n_results=N_SIMILARS,
            )
            documents = results["documents"][0][:]
            prices = [m["price"] for m in results["metadatas"][0][:]]

            # Step 3: build prompt with RAG context
            message = self._build_prompt(text, documents, prices)

            # Step 4: call OpenAI
            response = self._openai_client.chat.completions.create(
                model=self._model_id,
                messages=[{"role": "user", "content": message}],
                seed=42,
            )
            reply = response.choices[0].message.content

            # Step 5: parse price from response
            value = _extract_price(reply)
            if value is None:
                return FrontierEstimateResult(
                    available=False,
                    error_code="parse_error",
                    error_detail="Model response contained no numeric price",
                )

            value = float(max(0, value))
            return FrontierEstimateResult(
                value_usd=round(value, 2),
                available=True,
            )

        except Exception as exc:
            logger.warning(
                "Frontier inference failed: %s", _sanitize_detail(str(exc))
            )
            return FrontierEstimateResult(
                available=False,
                error_code="model_error",
                error_detail=_sanitize_detail(str(exc)),
            )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Lazy init: validate config, import heavy deps, connect services.

        Sets self._init_error on any failure. Called once by try_estimate().
        """
        # Step 1: validate chromadb path
        if not self._chromadb_path:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="missing_chromadb_path",
                error_detail="PRICER_CHROMADB_PATH is not set",
            )
            return

        db_path = Path(self._chromadb_path)
        if not db_path.exists():
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="missing_chromadb_path",
                error_detail="ChromaDB path does not exist",
            )
            return

        # Step 2: validate model_id
        if not self._model_id:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="model_config_missing",
                error_detail="PRICER_FRONTIER_MODEL_ID is not set",
            )
            return

        # Step 3: lazy-import heavy dependencies
        try:
            import chromadb  # noqa: F401
            from sentence_transformers import SentenceTransformer
            from openai import OpenAI
        except ImportError as exc:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="missing_dependency",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 4: connect ChromaDB
        try:
            client = chromadb.PersistentClient(path=str(db_path))
            self._collection = client.get_collection(COLLECTION_NAME)
        except Exception as exc:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="collection_not_found",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 5: load embedding model
        try:
            self._embed_model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
        except Exception as exc:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="missing_dependency",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 6: init OpenAI client
        try:
            self._openai_client = OpenAI()
        except Exception as exc:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="model_config_missing",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

    def _build_prompt(
        self,
        description: str,
        documents: list[str],
        prices: list[float],
    ) -> str:
        """Build the RAG-augmented prompt with similar products as context.

        Adapted from segment4 FrontierAgent.messages_for() and make_context().
        """
        message = (
            "Estimate the price of this product. "
            "Respond with the price, no explanation\n\n"
            f"{description}\n\n"
        )
        message += (
            "To provide some context, here are some other items that might be "
            "similar to the item you need to estimate.\n\n"
        )
        for doc, price in zip(documents, prices):
            message += (
                f"Potentially related product:\n{doc}\n"
                f"Price is ${price:.2f}\n\n"
            )
        return message
```

- [ ] **Step 3: Verify mock-safe import (no heavy deps loaded)**

```bash
cd shopping_assistant_v3 && uv run python -c "
import sys
# Record modules before import
before = set(sys.modules.keys())
from backend.tools.price_estimator.frontier.adapter import (
    FrontierEstimateResult,
    FrontierPriceAdapter,
    COLLECTION_NAME,
    N_SIMILARS,
)
after = set(sys.modules.keys())
new_mods = after - before
heavy = {'chromadb', 'sentence_transformers', 'openai', 'torch', 'sklearn', 'numpy'}
leaked = [m for m in new_mods if any(m.startswith(h) for h in heavy)]
assert not leaked, f'Heavy deps leaked at import: {leaked}'
assert COLLECTION_NAME == 'products'
assert N_SIMILARS == 5
print('OK — no heavy deps loaded at import time')
"
```

Expected: `OK — no heavy deps loaded at import time`

- [ ] **Step 4: Verify _extract_price (stdlib-only function)**

```bash
cd shopping_assistant_v3 && uv run python -c "
from backend.tools.price_estimator.frontier.adapter import _extract_price
assert _extract_price('Estimated price: \$899.99') == 899.99
assert _extract_price('The price is 1,299.50 dollars') == 1299.50
assert _extract_price('No numbers here') is None
assert _extract_price('42') == 42.0
assert _extract_price('\$0.00') == 0.0
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Verify adapter init stores config (no heavy deps)**

```bash
cd shopping_assistant_v3 && uv run python -c "
from backend.tools.price_estimator.frontier.adapter import FrontierPriceAdapter
a = FrontierPriceAdapter(chromadb_path='/tmp/test', model_id='gpt-5.1')
assert a._chromadb_path == '/tmp/test'
assert a._model_id == 'gpt-5.1'
assert a._init_attempted is False
print('OK')
"
```

Expected: `OK`

---

### Task 3: Update real_estimator.py — Assembly + Dispatch

**Files:**
- Modify: `backend/tools/price_estimator/real_estimator.py`

**Interfaces:**
- Consumes: `FrontierEstimateResult`, `FrontierPriceAdapter` from frontier adapter
- Consumes: `PRICER_CHROMADB_PATH`, `PRICER_FRONTIER_MODEL_ID` from config
- Modifies: `_assemble_output(product, frontier_result, neural_result) -> PriceEstimateOutput`
- Modifies: `estimate_price_real(product) -> PriceEstimateOutput`

- [ ] **Step 1: Update warning constants and imports**

Replace lines 11-34 (imports + warning constants) with:

```python
"""Real price estimator orchestrator — Phase 4C.2.

Assembles PriceEstimateOutput from available components:
  - Frontier adapter (via PRICER_CHROMADB_PATH + PRICER_FRONTIER_MODEL_ID) — Phase 4C.2.
  - Neural adapter (via PRICER_NEURAL_WEIGHTS_PATH) — Phase 4C.1.
Deferred: Specialist (4C.3).

Mock path is in tool.py; this module is only reached when
ENABLE_REAL_MODEL_CALLS=true.

Priority: frontier > neural > fallback 5% markup.
"""

from __future__ import annotations

import logging

from backend.shared.config import (
    PRICER_CHROMADB_PATH,
    PRICER_FRONTIER_MODEL_ID,
    PRICER_NEURAL_WEIGHTS_PATH,
)
from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.formatter import format_product_for_pricing
from backend.tools.price_estimator.frontier.adapter import (
    FrontierEstimateResult,
    FrontierPriceAdapter,
)
from backend.tools.price_estimator.neural.adapter import (
    NeuralEstimateResult,
    NeuralPriceAdapter,
)
from backend.tools.price_estimator.schemas import (
    ModelBreakdown,
    PriceEstimateOutput,
)

logger = logging.getLogger("shopping_assistant_v3.real_estimator")

# ── warning grammar (key:value, no space after colon) ──────────────────
_WARN_SPECIALIST = "specialist_unavailable:deferred_to_4c3"
_WARN_ENSEMBLE_FRONTIER = "ensemble_partial:frontier_only"
_WARN_ENSEMBLE_NEURAL = "ensemble_partial:neural_only"
_WARN_ENSEMBLE_FALLBACK = "ensemble_partial:fallback_only"
_WARN_FALLBACK_USED = "real_pricing_fallback_used:sale_price_markup"
```

- [ ] **Step 2: Update `_assemble_output` signature and priority logic**

Replace the entire `_assemble_output` function (lines 48-92) with:

```python
def _assemble_output(
    product: ProductCandidate,
    frontier_result: FrontierEstimateResult,
    neural_result: NeuralEstimateResult,
) -> PriceEstimateOutput:
    """Pure function: assemble PriceEstimateOutput with frontier > neural > fallback.

    Priority:
      1. Frontier available → use frontier_value directly (dominant model, 80% weight).
      2. Frontier unavailable, neural available → use neural_value (4C.1 behavior).
      3. Neither available → 5% markup fallback.

    Testable without any heavy deps — just pass real or fake result objects.
    """
    sale_price = product.sale_price_usd or 0.0
    warnings: list[str] = [_WARN_SPECIALIST]

    frontier_value = 0.0
    neural_value = 0.0

    # ── Priority 1: Frontier ──
    if frontier_result.available and frontier_result.value_usd is not None:
        estimated_value = frontier_result.value_usd
        frontier_value = frontier_result.value_usd
        warnings.append(_WARN_ENSEMBLE_FRONTIER)
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)

    # ── Priority 2: Neural (frontier unavailable) ──
    elif neural_result.available and neural_result.value_usd is not None:
        estimated_value = neural_result.value_usd
        neural_value = neural_result.value_usd
        if frontier_result.error_code:
            warnings.append(f"frontier_unavailable:{frontier_result.error_code}")
        warnings.append(_WARN_ENSEMBLE_NEURAL)
        discount = round(estimated_value - sale_price, 2)
        deal_score = _compute_deal_score(sale_price, estimated_value)

    # ── Priority 3: Fallback ──
    else:
        estimated_value = round(sale_price * 1.05, 2)
        discount = round(estimated_value - sale_price, 2)
        deal_score = "ok"

        if frontier_result.error_code:
            warnings.append(f"frontier_unavailable:{frontier_result.error_code}")
        if neural_result.error_code:
            warnings.append(f"neural_unavailable:{neural_result.error_code}")
        warnings.append(_WARN_FALLBACK_USED)
        warnings.append(_WARN_ENSEMBLE_FALLBACK)

    return PriceEstimateOutput(
        estimated_value_usd=estimated_value,
        discount_usd=discount,
        deal_score=deal_score,
        confidence=None,
        model_breakdown=ModelBreakdown(
            frontier=frontier_value,
            specialist=0.0,
            neural=neural_value,
        ),
        warnings=warnings,
    )
```

- [ ] **Step 3: Update `estimate_price_real` to run both adapters**

Replace the entire `estimate_price_real` function (lines 95-118) with:

```python
def estimate_price_real(product: ProductCandidate) -> PriceEstimateOutput:
    """Real price estimation using available components.

    Current available:
      - Frontier (4C.2): GPT + ChromaDB RAG via PRICER_CHROMADB_PATH
      - Neural (4C.1): PyTorch DNN via PRICER_NEURAL_WEIGHTS_PATH
    Deferred: Specialist (4C.3).

    Short-circuits: if frontier succeeds, neural is skipped entirely.
    This makes ensemble_partial:frontier_only accurate and avoids
    unnecessary neural deps loading. If frontier fails, falls back
    to neural, then to 5% markup.

    Never raises — all failure paths produce valid PriceEstimateOutput
    with explicit warnings.
    """
    text = format_product_for_pricing(product)

    # Run frontier adapter (lazy-loads on first call)
    frontier_adapter = FrontierPriceAdapter(
        chromadb_path=PRICER_CHROMADB_PATH,
        model_id=PRICER_FRONTIER_MODEL_ID,
    )
    frontier_result = frontier_adapter.try_estimate(text)

    logger.debug(
        "Real estimator: frontier available=%s value=%s error=%s",
        frontier_result.available,
        frontier_result.value_usd,
        frontier_result.error_code,
    )

    # Short-circuit: if frontier available, skip neural entirely.
    if frontier_result.available:
        neural_result = NeuralEstimateResult(
            available=False, error_code="skipped_frontier_available"
        )
    else:
        # Run neural adapter (lazy-loads on first call)
        neural_adapter = NeuralPriceAdapter(weights_path=PRICER_NEURAL_WEIGHTS_PATH)
        neural_result = neural_adapter.estimate(text)

        logger.debug(
            "Real estimator: neural available=%s value=%s error=%s",
            neural_result.available,
            neural_result.value_usd,
            neural_result.error_code,
        )

    return _assemble_output(product, frontier_result, neural_result)
```

- [ ] **Step 4: Verify mock-safe import (no heavy deps loaded)**

```bash
cd shopping_assistant_v3 && uv run python -c "
import sys
before = set(sys.modules.keys())
from backend.tools.price_estimator.real_estimator import _assemble_output, estimate_price_real
after = set(sys.modules.keys())
new_mods = after - before
heavy = {'chromadb', 'sentence_transformers', 'openai', 'torch', 'sklearn', 'numpy'}
leaked = [m for m in new_mods if any(m.startswith(h) for h in heavy)]
assert not leaked, f'Heavy deps leaked at import: {leaked}'
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Verify _assemble_output with fake results works (smoke)**

```bash
cd shopping_assistant_v3 && uv run python -c "
from backend.tools.price_estimator.real_estimator import _assemble_output
from backend.tools.price_estimator.frontier.adapter import FrontierEstimateResult
from backend.tools.price_estimator.neural.adapter import NeuralEstimateResult
from backend.tools.deal_search.schemas import ProductCandidate

p = ProductCandidate(source='BestBuy', title='Test', sale_price_usd=100.0, url=None)

# Frontier available → uses frontier
fr = FrontierEstimateResult(value_usd=150.0, available=True)
nr = NeuralEstimateResult(value_usd=200.0, available=True)
out = _assemble_output(p, fr, nr)
assert out.estimated_value_usd == 150.0, f'Expected 150.0, got {out.estimated_value_usd}'
assert out.model_breakdown.frontier == 150.0
assert out.model_breakdown.neural == 0.0
assert 'ensemble_partial:frontier_only' in out.warnings
assert 'ensemble_partial:neural_only' not in out.warnings
print('PASS: frontier priority')

# Frontier unavailable, neural available → uses neural + frontier_unavailable warning
fr2 = FrontierEstimateResult(available=False, error_code='missing_chromadb_path')
nr2 = NeuralEstimateResult(value_usd=130.0, available=True)
out2 = _assemble_output(p, fr2, nr2)
assert out2.estimated_value_usd == 130.0
assert out2.model_breakdown.frontier == 0.0
assert out2.model_breakdown.neural == 130.0
assert 'ensemble_partial:neural_only' in out2.warnings
assert 'frontier_unavailable:missing_chromadb_path' in out2.warnings
print('PASS: neural fallback with frontier_unavailable warning')

# Both unavailable → 5% markup
fr3 = FrontierEstimateResult(available=False, error_code='missing_chromadb_path')
nr3 = NeuralEstimateResult(available=False, error_code='missing_weights_path')
out3 = _assemble_output(p, fr3, nr3)
assert out3.estimated_value_usd == 105.0
assert out3.deal_score == 'ok'
assert 'frontier_unavailable:missing_chromadb_path' in out3.warnings
assert 'neural_unavailable:missing_weights_path' in out3.warnings
assert 'real_pricing_fallback_used:sale_price_markup' in out3.warnings
assert 'ensemble_partial:fallback_only' in out3.warnings
print('PASS: fallback markup')

print('ALL SMOKE CHECKS PASSED')
"
```

Expected: all 3 checks pass

---

### Task 4: Mock-Only Tests — Extend test_real_pricing.py

**Files:**
- Modify: `tests/test_real_pricing.py`

**Interfaces:**
- Consumes: `FrontierEstimateResult`, `FrontierPriceAdapter` from frontier adapter
- Consumes: Updated `_assemble_output(product, frontier_result, neural_result)`
- Consumes: Updated `estimate_price_real(product)`

- [ ] **Step 1: Update imports in test_real_pricing.py**

Replace lines 14-24 (imports) with:

```python
"""Tests for Phase 4C.2 real price estimator — formatter, boundary, assembly, adapters.

All tests are mock/fixture-only — no ChromaDB, no OpenAI, no neural deps, no network.
deep_neural_network.py and frontier heavy deps must NOT be imported by any test.
"""

from __future__ import annotations

import os
import sys

import pytest

from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.frontier.adapter import (
    FrontierEstimateResult,
    FrontierPriceAdapter,
)
from backend.tools.price_estimator.neural.adapter import (
    NeuralEstimateResult,
    NeuralPriceAdapter,
)
from backend.tools.price_estimator.real_estimator import (
    _assemble_output,
    estimate_price_real,
)
from backend.tools.price_estimator.schemas import PriceEstimateInput
from backend.tools.price_estimator.tool import estimate_price
```

- [ ] **Step 2: Update `_assemble_output` calls in existing tests — TestAssembly**

The `TestAssembly` class (line 191) needs a `frontier_result` parameter added to each `_assemble_output` call. Replace the entire `TestAssembly` class:

```python
class TestAssembly:
    """_assemble_output pure-function tests with fake results."""

    def test_frontier_available_takes_priority(self) -> None:
        """Frontier available → use frontier_value, ignore neural."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=150.0, available=True)
        nr = NeuralEstimateResult(value_usd=200.0, available=True)
        output = _assemble_output(p, fr, nr)
        assert output.estimated_value_usd == 150.0
        assert output.model_breakdown.frontier == 150.0
        assert output.model_breakdown.neural == 0.0
        assert output.model_breakdown.specialist == 0.0
        assert output.discount_usd == 50.0
        assert output.deal_score == "ok"  # discount 50 < 100
        assert "ensemble_partial:frontier_only" in output.warnings
        assert "ensemble_partial:neural_only" not in output.warnings
        assert "specialist_unavailable:deferred_to_4c3" in output.warnings

    def test_neural_success_frontier_unavailable(self) -> None:
        """Frontier unavailable, neural available → use neural_value + frontier_unavailable warning."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(available=False, error_code="missing_chromadb_path")
        nr = NeuralEstimateResult(value_usd=150.0, available=True)
        output = _assemble_output(p, fr, nr)
        assert output.estimated_value_usd == 150.0
        assert output.model_breakdown.frontier == 0.0
        assert output.model_breakdown.neural == 150.0
        assert output.model_breakdown.specialist == 0.0
        assert output.discount_usd == 50.0
        assert output.deal_score == "ok"  # discount 50 < 100
        assert "ensemble_partial:neural_only" in output.warnings
        assert "frontier_unavailable:missing_chromadb_path" in output.warnings
        assert "ensemble_partial:frontier_only" not in output.warnings

    def test_both_unavailable_produces_fallback(self) -> None:
        """Both adapters unavailable → 5% markup fallback."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(available=False, error_code="missing_chromadb_path")
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        output = _assemble_output(p, fr, nr)
        assert output.estimated_value_usd == 105.0
        assert output.deal_score == "ok"
        assert output.model_breakdown.frontier == 0.0
        assert output.model_breakdown.neural == 0.0
        assert "frontier_unavailable:missing_chromadb_path" in output.warnings
        assert "neural_unavailable:missing_weights_path" in output.warnings
        assert "real_pricing_fallback_used:sale_price_markup" in output.warnings
        assert "ensemble_partial:fallback_only" in output.warnings

    def test_hot_deal_score_frontier(self) -> None:
        """Frontier estimate with large discount → hot."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=350.0, available=True)
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        output = _assemble_output(p, fr, nr)
        assert output.deal_score == "hot"
        assert output.discount_usd == 250.0
        assert "ensemble_partial:frontier_only" in output.warnings

    def test_good_deal_score_frontier(self) -> None:
        """Frontier estimate with moderate discount → good."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=210.0, available=True)
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        output = _assemble_output(p, fr, nr)
        assert output.deal_score == "good"
        assert output.discount_usd == 110.0

    def test_overpriced_frontier(self) -> None:
        """Frontier estimate below sale price → overpriced."""
        p = _make_product(sale_price_usd=200.0)
        fr = FrontierEstimateResult(value_usd=150.0, available=True)
        nr = NeuralEstimateResult(available=False, error_code="missing_weights_path")
        output = _assemble_output(p, fr, nr)
        assert output.deal_score == "overpriced"
        assert output.discount_usd == -50.0

    def test_frontier_available_neural_available_frontier_wins(self) -> None:
        """Both available → frontier takes priority, neural value in breakdown is 0.0."""
        p = _make_product(sale_price_usd=100.0)
        fr = FrontierEstimateResult(value_usd=180.0, available=True)
        nr = NeuralEstimateResult(value_usd=250.0, available=True)
        output = _assemble_output(p, fr, nr)
        assert output.estimated_value_usd == 180.0  # frontier, not neural
        assert output.model_breakdown.frontier == 180.0
        assert output.model_breakdown.neural == 0.0
        assert "ensemble_partial:frontier_only" in output.warnings
```

- [ ] **Step 3: Update RealEstimatorFallback tests for new signature**

Replace `TestRealEstimatorFallback` class (line 125):

```python
class TestRealEstimatorFallback:
    """Real mode with no config → both adapters unavailable → safe fallback markup."""

    def test_fallback_uses_5_percent_markup(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product(sale_price_usd=100.0)
        output = estimate_price_real(p)
        assert output.estimated_value_usd == 105.0  # 5% markup
        assert output.deal_score == "ok"
        assert output.model_breakdown.neural == 0.0
        assert output.model_breakdown.frontier == 0.0

    def test_fallback_includes_all_required_warnings(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product()
        output = estimate_price_real(p)
        assert "frontier_unavailable:missing_chromadb_path" in output.warnings
        assert "specialist_unavailable:deferred_to_4c3" in output.warnings
        assert "neural_unavailable:missing_weights_path" in output.warnings
        assert "real_pricing_fallback_used:sale_price_markup" in output.warnings
        assert "ensemble_partial:fallback_only" in output.warnings

    def test_fallback_with_zero_sale_price(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product(sale_price_usd=0.0)
        output = estimate_price_real(p)
        assert output.estimated_value_usd == 0.0  # 0 * 1.05 = 0
        assert output.deal_score == "ok"
```

- [ ] **Step 4: Update RealEstimatorWarnings tests**

Replace `TestRealEstimatorWarnings` class (line 163):

```python
class TestRealEstimatorWarnings:
    """Warning grammar consistency (key:value, no space after colon)."""

    def test_warning_format_no_spaces(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product()
        output = estimate_price_real(p)
        for w in output.warnings:
            assert ":" in w
            key, value = w.split(":", 1)
            assert key
            assert " " not in key

    def test_no_duplicate_warnings(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID", ""
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH", ""
        )
        p = _make_product()
        output = estimate_price_real(p)
        assert len(output.warnings) == len(set(output.warnings))
```

- [ ] **Step 5: Update RealModeDispatch test**

Replace `TestRealModeDispatch` class (line 362):

```python
class TestRealModeDispatch:
    """ENABLE_REAL_MODEL_CALLS=true dispatches to real path."""

    def test_real_mode_returns_valid_output(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.tool.ENABLE_REAL_MODEL_CALLS",
            True,
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_CHROMADB_PATH",
            "",
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_FRONTIER_MODEL_ID",
            "",
        )
        monkeypatch.setattr(
            "backend.tools.price_estimator.real_estimator.PRICER_NEURAL_WEIGHTS_PATH",
            "",
        )
        p = _make_product()
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.estimated_value_usd > 0
        assert isinstance(result.model_breakdown.frontier, float)
        assert isinstance(result.model_breakdown.specialist, float)
        # With no config, frontier and neural should be 0.0
        assert result.model_breakdown.frontier == 0.0
        assert result.model_breakdown.neural == 0.0
```

- [ ] **Step 6: Add new Frontier adapter test classes**

Add after the `TestNeuralAdapterSanitizedError` class (before line 334):

```python
# ====================================================================
# Frontier adapter tests (mock-safe, no heavy deps)
# ====================================================================


class TestFrontierAdapterMissingPath:
    """Adapter fails cleanly when chromadb path is missing."""

    def test_empty_path_returns_missing_chromadb_path(self) -> None:
        adapter = FrontierPriceAdapter(chromadb_path="", model_id="gpt-5.1")
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "missing_chromadb_path"

    def test_nonexistent_path_returns_missing_chromadb_path(self) -> None:
        adapter = FrontierPriceAdapter(
            chromadb_path="/tmp/nonexistent_chromadb_4c2_test",
            model_id="gpt-5.1",
        )
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "missing_chromadb_path"

    def test_result_is_idempotent(self) -> None:
        adapter = FrontierPriceAdapter(chromadb_path="", model_id="gpt-5.1")
        r1 = adapter.try_estimate("text a")
        r2 = adapter.try_estimate("text b")
        assert not r1.available
        assert not r2.available
        assert r1.error_code == r2.error_code


class TestFrontierAdapterMissingModelId:
    """Adapter fails cleanly when model_id is empty."""

    def test_empty_model_id_with_valid_path(self, tmp_path) -> None:
        """Path exists but model_id empty → model_config_missing."""
        adapter = FrontierPriceAdapter(
            chromadb_path=str(tmp_path),
            model_id="",
        )
        result = adapter.try_estimate("test text")
        assert not result.available
        assert result.error_code == "model_config_missing"


class TestFrontierAdapterMissingDependency:
    """Adapter returns missing_dependency when heavy deps cannot be imported."""

    def test_missing_dependency_returns_safe_error(self, monkeypatch, tmp_path) -> None:
        """With valid config but blocked chromadb import → missing_dependency."""
        import builtins

        real_import = builtins.__import__

        def _block_heavy(name, *args, **kwargs):
            if name in ("chromadb",):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_heavy)

        adapter = FrontierPriceAdapter(
            chromadb_path=str(tmp_path),
            model_id="gpt-5.1",
        )
        result = adapter.try_estimate("test")
        assert not result.available
        assert result.error_code == "missing_dependency"
        assert result.error_detail is not None
        assert len(result.error_detail) <= 200

    def test_missing_dependency_sanitized_detail(self, monkeypatch, tmp_path) -> None:
        """Long import error message is bounded to 200 chars."""
        import builtins

        real_import = builtins.__import__

        def _fail_long(name, *args, **kwargs):
            if name == "chromadb":
                raise ImportError("X" * 500)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fail_long)

        adapter = FrontierPriceAdapter(
            chromadb_path=str(tmp_path),
            model_id="gpt-5.1",
        )
        result = adapter.try_estimate("test")
        assert not result.available
        assert result.error_code == "missing_dependency"
        assert result.error_detail is not None
        assert len(result.error_detail) <= 200


class TestFrontierAdapterSanitizedError:
    """Frontier adapter error_detail is bounded, safe, no stack traces."""

    def test_sanitize_detail_bounds_long_strings(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _sanitize_detail

        long_msg = "A" * 500
        result = _sanitize_detail(long_msg)
        assert len(result) <= 200

    def test_sanitize_detail_flattens_newlines(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _sanitize_detail

        result = _sanitize_detail("line1\nline2\r\nline3")
        assert "\n" not in result
        assert "\r" not in result

    def test_sanitize_detail_handles_non_strings(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _sanitize_detail

        result = _sanitize_detail(Exception(42))  # type: ignore[arg-type]
        assert len(result) <= 200
        assert "42" in result


class TestFrontierExtractPrice:
    """_extract_price is deterministic, stdlib-only."""

    def test_extracts_dollar_amount(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("Estimated price: $899.99") == 899.99

    def test_extracts_with_commas(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("The price is 1,299.50 dollars") == 1299.50

    def test_returns_none_when_no_number(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("No numbers here") is None

    def test_extracts_integer(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("42") == 42.0

    def test_extracts_zero(self) -> None:
        from backend.tools.price_estimator.frontier.adapter import _extract_price

        assert _extract_price("$0.00") == 0.0


# ====================================================================
# Frontier config tests
# ====================================================================


class TestFrontierConfig:
    """PRICER_CHROMADB_PATH and PRICER_FRONTIER_MODEL_ID env var handling."""

    def test_chromadb_path_default_empty(self) -> None:
        from backend.shared.config import PRICER_CHROMADB_PATH

        assert PRICER_CHROMADB_PATH == ""

    def test_frontier_model_id_default_empty(self) -> None:
        from backend.shared.config import PRICER_FRONTIER_MODEL_ID

        assert PRICER_FRONTIER_MODEL_ID == ""
```

- [ ] **Step 7: Update lazy import guard test**

Replace the final `test_neural_heavy_module_not_imported` (line 386) with a broader guard:

```python
# ====================================================================
# Lazy import guard — heavy modules must NOT be loaded by default tests
# ====================================================================


def test_neural_heavy_module_not_imported() -> None:
    """Default test suite must not pull torch/sklearn via deep_neural_network."""
    heavy = "backend.tools.price_estimator.neural.deep_neural_network"
    assert heavy not in sys.modules, (
        f"{heavy} was imported — default tests must not pull heavy deps"
    )


def test_frontier_heavy_modules_not_imported() -> None:
    """Default test suite must not pull chromadb/sentence_transformers/openai."""
    for mod_start in ("chromadb", "sentence_transformers", "openai"):
        leaked = [m for m in sys.modules if m.startswith(mod_start)]
        assert not leaked, (
            f"{mod_start} was imported — default tests must not pull frontier deps: {leaked}"
        )
```

- [ ] **Step 8: Run updated tests**

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_real_pricing.py -v
```

Expected: all tests pass (expected ~40-45 tests, up from 26)

---

### Task 5: Opt-In Frontier Smoke Tests

**Files:**
- Create: `tests/test_real_pricing_frontier.py`

**Interfaces:**
- Consumes: `FrontierPriceAdapter`, `FrontierEstimateResult` from frontier adapter
- Consumes: `estimate_price_real` from real_estimator
- Skipped by default via `pytestmark`

- [ ] **Step 1: Write `test_real_pricing_frontier.py`**

```python
"""Opt-in frontier smoke tests — skipped by default.

Requires ALL of:
  - ENABLE_REAL_MODEL_CALLS=true
  - PRICER_CHROMADB_PATH set and directory exists
  - PRICER_FRONTIER_MODEL_ID set
  - OPENAI_API_KEY set (used by openai.OpenAI())
  - frontier extras installed (chromadb, sentence-transformers, openai)

Run manually:
  ENABLE_REAL_MODEL_CALLS=true \
  PRICER_CHROMADB_PATH=/path/to/products_vectorstore \
  PRICER_FRONTIER_MODEL_ID=gpt-5.1 \
  OPENAI_API_KEY=<set locally> \
  uv run pytest tests/test_real_pricing_frontier.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Module-level skips use stdlib only — no heavy imports at collection time.
# Heavy deps are checked inside test bodies via pytest.importorskip().
pytestmark = [
    pytest.mark.skipif(
        os.getenv("ENABLE_REAL_MODEL_CALLS") != "true",
        reason="Requires ENABLE_REAL_MODEL_CALLS=true",
    ),
    pytest.mark.skipif(
        not os.getenv("PRICER_CHROMADB_PATH"),
        reason="Requires PRICER_CHROMADB_PATH set",
    ),
    pytest.mark.skipif(
        not Path(os.getenv("PRICER_CHROMADB_PATH", "")).exists(),
        reason="ChromaDB directory does not exist at configured path",
    ),
    pytest.mark.skipif(
        not os.getenv("PRICER_FRONTIER_MODEL_ID"),
        reason="Requires PRICER_FRONTIER_MODEL_ID set",
    ),
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY set",
    ),
]


def _require_frontier_deps() -> None:
    """Skip if frontier extras not installed. Call inside test body.

    Uses pytest.importorskip so heavy deps are only checked after
    env-based pytestmark skips have already passed.
    """
    pytest.importorskip("chromadb", reason="Requires frontier extras (chromadb)")
    pytest.importorskip(
        "sentence_transformers",
        reason="Requires frontier extras (sentence-transformers)",
    )
    pytest.importorskip("openai", reason="Requires frontier extras (openai)")


# ====================================================================
# Helpers
# ====================================================================


def _make_product(**overrides) -> "ProductCandidate":
    from backend.tools.deal_search.schemas import ProductCandidate

    defaults = {
        "source": "BestBuy",
        "title": "Test Laptop Pro 15",
        "brand": "TestBrand",
        "sale_price_usd": 799.99,
        "url": "https://example.com/test-laptop",
        "features": "16GB RAM, 512GB SSD, RTX 4060",
    }
    defaults.update(overrides)
    return ProductCandidate(**defaults)


# ====================================================================
# Frontier adapter real load tests (opt-in only)
# ====================================================================


class TestFrontierAdapterRealLoad:
    """Frontier adapter loads ChromaDB, embedding model, and returns estimates."""

    def test_loads_and_returns_value(self) -> None:
        _require_frontier_deps()
        chromadb_path = os.environ["PRICER_CHROMADB_PATH"]
        model_id = os.environ["PRICER_FRONTIER_MODEL_ID"]
        assert Path(chromadb_path).exists(), f"ChromaDB missing: {chromadb_path}"

        from backend.tools.price_estimator.frontier.adapter import FrontierPriceAdapter

        adapter = FrontierPriceAdapter(
            chromadb_path=chromadb_path,
            model_id=model_id,
        )
        result = adapter.try_estimate(
            "Title: Gaming Laptop\n"
            "Category: Unknown\n"
            "Brand: ASUS\n"
            "Description: ASUS gaming laptop, priced at $1200\n"
            "Details: RTX 4070, 32GB RAM"
        )
        assert result.available, f"Frontier unavailable: {result.error_code} — {result.error_detail}"
        assert result.value_usd is not None
        assert result.value_usd > 0.0, f"Expected positive price, got {result.value_usd}"

    def test_inference_on_minimal_text(self) -> None:
        _require_frontier_deps()
        chromadb_path = os.environ["PRICER_CHROMADB_PATH"]
        model_id = os.environ["PRICER_FRONTIER_MODEL_ID"]

        from backend.tools.price_estimator.frontier.adapter import FrontierPriceAdapter

        adapter = FrontierPriceAdapter(
            chromadb_path=chromadb_path,
            model_id=model_id,
        )
        result = adapter.try_estimate("Unknown product")
        assert result.available, f"Frontier unavailable: {result.error_code}"
        assert result.value_usd is not None
        assert result.value_usd >= 0.0


class TestRealEstimatorFullFlowFrontier:
    """estimate_price_real end-to-end with frontier available."""

    def test_real_estimator_frontier_primary(self) -> None:
        _require_frontier_deps()
        from backend.tools.price_estimator.real_estimator import estimate_price_real

        p = _make_product()
        output = estimate_price_real(p)
        assert output.estimated_value_usd > 0
        # With real frontier available, short-circuit means neural skipped.
        assert "ensemble_partial:frontier_only" in output.warnings
        assert output.model_breakdown.frontier > 0.0
        assert output.model_breakdown.neural == 0.0
        assert "real_pricing_fallback_used" not in output.warnings

    def test_real_estimator_with_minimal_product(self) -> None:
        _require_frontier_deps()
        from backend.tools.price_estimator.real_estimator import estimate_price_real

        p = _make_product(
            title="Headphones", brand="", features="", sale_price_usd=49.99
        )
        output = estimate_price_real(p)
        assert output.estimated_value_usd > 0
        assert isinstance(output.estimated_value_usd, float)
```

- [ ] **Step 2: Verify opt-in tests are skipped by default**

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_real_pricing_frontier.py -v
```

Expected: `4 skipped` (không có env vars)

- [ ] **Step 3: Verify skip message is clear**

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_real_pricing_frontier.py -v 2>&1 | grep -i "reason"
```

Expected: shows skip reasons mentioning `ENABLE_REAL_MODEL_CALLS`, `PRICER_CHROMADB_PATH`, etc.

---

### Task 6: Full Verification

- [ ] **Step 1: Run full default test suite**

```bash
cd shopping_assistant_v3 && uv run pytest tests/ -v
```

Expected: all default tests pass (expected ~142 passed), frontier + neural + search opt-in tests skipped (expected ~16 skipped)

Count breakdown dự kiến:
| File | Count | Result |
|---|---|---|
| tests/test_api.py | 22 | passed |
| tests/test_repository.py | 8 | passed |
| tests/test_tools.py | 51 | passed |
| tests/test_worker.py | 20 | passed |
| tests/test_real_pricing.py | ~42 | passed |
| tests/test_real_search.py | 8 | skipped |
| tests/test_real_pricing_neural.py | 4 | skipped |
| tests/test_real_pricing_frontier.py | 4 | skipped |
| **Total** | **~143** | **~143 passed, 16 skipped** |

- [ ] **Step 2: Verify no segment4 runtime imports**

```bash
rg -n "from segment4\|import segment4" shopping_assistant_v3/backend/ shopping_assistant_v3/tests/
```

Expected: NO MATCHES

- [ ] **Step 3: Verify segment4 untouched**

```bash
git diff --name-only -- segment4/
```

Expected: no output (unchanged)

- [ ] **Step 4: Verify no secrets in code**

```bash
rg -n "OPENAI_API_KEY\|sk-\|api_key.*=" shopping_assistant_v3/backend/tools/price_estimator/frontier/
```

Expected: NO MATCHES (OpenAI client uses env var automatically, no hardcoded keys)

- [ ] **Step 5: CodeGraph sync and status**

```bash
codegraph sync shopping_assistant_v3 && codegraph status shopping_assistant_v3
```

Expected: index up to date, files count increased from 37

- [ ] **Step 6: Verify frontier/__init__.py is stdlib-only**

```bash
cd shopping_assistant_v3 && uv run python -c "
import ast, sys
with open('backend/tools/price_estimator/frontier/__init__.py') as f:
    tree = ast.parse(f.read())
imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
from_imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
all_imports = imports + [m for m in from_imports if m]
heavy = {'chromadb', 'sentence_transformers', 'openai', 'torch', 'sklearn', 'numpy'}
for imp in all_imports:
    for h in heavy:
        assert not imp.startswith(h), f'Heavy import in __init__.py: {imp}'
print('OK — __init__.py is stdlib-only')
"
```

Expected: `OK — __init__.py is stdlib-only`

---

## Verification Summary

Sau khi hoan thanh tat ca tasks, verify:

1. `uv run pytest tests/ -v` — ~143 passed, 16 skipped
2. `rg "from segment4\|import segment4" backend/ tests/` — NO MATCHES
3. `git diff --name-only -- segment4/` — no output
4. `rg "OPENAI_API_KEY\|sk-" backend/tools/price_estimator/frontier/` — NO MATCHES
5. `codegraph status shopping_assistant_v3` — up to date
6. Default tests khong load chromadb, sentence_transformers, openai

## Known Deviations (To Document In Report)

1. **OpenAI SDK direct** thay vi LiteLLM — intentional deviation. LiteLLM deferred to Phase 5 Router/Synthesizer.
2. **`reasoning_effort` removed** — `gpt-5.1` khong ho tro `reasoning_effort` parameter (khac voi segment4). Bo qua param nay.
3. **`_extract_price` tra ve None** thay vi 0.0 khi parse fail — improvement over segment4's silent 0.0 fallback.
4. **No `make_context` as separate method** — inlined into `_build_prompt` vi logic don gian.
5. **`get_collection` instead of `get_or_create_collection`** — prevents silently creating empty collection. Returns `collection_not_found` if collection doesn't exist in ChromaDB path.
6. **Frontier short-circuits Neural** — if frontier succeeds, neural adapter is never loaded or called. This makes `ensemble_partial:frontier_only` accurate and avoids unnecessary heavy imports.
