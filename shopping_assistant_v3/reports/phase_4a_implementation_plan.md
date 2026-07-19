# Phase 4A: Mock Search/Pricing Tools — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build full mock pipeline: deal_search_tool + price_estimator_tool with JSON fixtures, integrated into worker lifecycle with DB persistence and agent_runs audit.

**Architecture:** Two independent tool modules under `backend/tools/`, each with schemas/fixtures/tool.py. Worker orchestrates: parse request → deal_search_tool → save products → price_estimator_tool per product → save estimates → build result. All tool invocations wrapped in agent_runs. Injectable tool runner seams for deterministic failure testing.

**Tech Stack:** Python 3.12, Pydantic, SQLAlchemy (existing), pytest (existing), JSON fixtures.

## Global Constraints

- No live Amazon/BestBuy scraping, no paid model calls, no OpenAI/Modal/AWS.
- No imports from `segment4/`.
- No Router, no Synthesizer, no progress_steps API contract (Phase 5).
- `ENABLE_REAL_SEARCH=true` and `ENABLE_REAL_MODEL_CALLS=true` must raise `NotImplementedError` in tools; worker catches and fails job safely.
- `max_results_per_source` default changes from 6 to 5 (approved contract change).
- `query_en` bridged from `request_payload["message"]` via `_normalize_query()`: lowercase + strip whitespace + remove common Vietnamese intent words (tìm, tim, mua, cho, giúp, mình, minh, giup).
- Keyword matcher uses **any-token** match: a product matches if ANY meaningful query token appears in its title or features (not ALL tokens). No-results tests use nonsense query like "zzzz nonexistent".
- Fixtures as JSON files: `mock_products.json` (10 products) + `mock_estimates.json` (lookup table).
- Price estimate: fixed lookup by source+title from fixtures; fallback rule: `estimated_value_usd = round(sale_price_usd * 1.10, 2)`.
- Model breakdown fallback: `frontier = specialist = neural = estimated_value_usd` (all equal to the estimate, since no real model distinction exists in mock mode).
- Deal score: rule-based only (hot >= 200, good >= 100, ok > 0, overpriced <= 0).
- `answer_vi` is a non-empty Vietnamese placeholder string. Tests assert non-empty string only, not locked to exact text.
- All default tests use mocks/fixtures only.
- `result_builder` parameter removed; replaced by `deal_search_runner` + `price_estimator_runner` injectable seams.
- Mỗi tool invocation được wrap trong agent_run: create started → run → update completed/failed.
- **No git add/commit/push.** Implementer workflow prohibits commits before Codex approval.

---

### Task 1: Update max_results_per_source default (6 → 5)

**Files:**
- Modify: `backend/api/schemas.py:24`

**Interfaces:**
- Produces: `ChatJobRequest.max_results_per_source` default becomes `5`.

- [ ] **Step 1: Change default in schemas.py**

In `backend/api/schemas.py`, line 24, change `default=6` to `default=5`:

```python
# Before (line 24):
    max_results_per_source: int = Field(default=6, ge=1, le=20)

# After:
    max_results_per_source: int = Field(default=5, ge=1, le=20)
```

- [ ] **Step 2: Run API tests to verify no regression**

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_api.py -v
```

Expected: all existing tests PASS. The only test that uses explicit `max_results_per_source` (line 141: `"max_results_per_source": 10`) overrides the default, so no test breaks.

- [ ] **Step 3: Verify with git status**

```bash
git status --short
```

Expected: only `backend/api/schemas.py` modified. No other files changed.

---

### Task 2: Create deal_search tool (schemas + fixtures + mock implementation)

**Files:**
- Create: `backend/tools/__init__.py`
- Create: `backend/tools/deal_search/__init__.py`
- Create: `backend/tools/deal_search/schemas.py`
- Create: `backend/tools/deal_search/fixtures/mock_products.json`
- Create: `backend/tools/deal_search/tool.py`

**Interfaces:**
- Produces:
  - `DealSearchInput(query_en: str, source: Literal["All","Amazon","BestBuy"] = "All", max_results_per_source: int = 5)`
  - `ProductCandidate(source, title, brand?, sale_price_usd?, url?, features?, raw_source_payload)`
  - `DealSearchOutput(products: list[ProductCandidate], warnings: list[str])`
  - `deal_search(input: DealSearchInput) -> DealSearchOutput`

- [ ] **Step 1: Create backend/tools/__init__.py**

```python
"""Shopping Assistant V3 tool modules.

deal_search: Amazon/BestBuy product search.
price_estimator: Fair USD value estimation.
"""
```

- [ ] **Step 2: Create backend/tools/deal_search/__init__.py**

```python
"""deal_search tool — search Amazon and/or BestBuy, return normalized candidates."""
```

- [ ] **Step 3: Create backend/tools/deal_search/schemas.py**

```python
"""Pydantic schemas for deal_search_tool matching agent_architecture.md contract."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DealSearchInput(BaseModel):
    query_en: str = Field(..., min_length=1, description="English search query")
    source: Literal["All", "Amazon", "BestBuy"] = "All"
    max_results_per_source: int = Field(default=5, ge=1, le=20)


class ProductCandidate(BaseModel):
    source: Literal["Amazon", "BestBuy"]
    title: str
    brand: str | None = None
    sale_price_usd: float | None = None
    url: str | None = None
    features: str | None = None
    raw_source_payload: dict[str, Any] = Field(default_factory=dict)


class DealSearchOutput(BaseModel):
    products: list[ProductCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Create backend/tools/deal_search/fixtures/mock_products.json**

10 products: 5 BestBuy + 5 Amazon, spread across categories.

```json
[
  {
    "source": "BestBuy",
    "title": "ASUS ROG Strix G16 Gaming Laptop",
    "brand": "ASUS",
    "sale_price_usd": 749.99,
    "url": "https://www.bestbuy.com/site/asus-rog-strix-g16",
    "features": "16-inch FHD 165Hz, Intel Core i7-13650HX, 16GB DDR5, NVIDIA GeForce RTX 4060, 512GB SSD",
    "raw_source_payload": {}
  },
  {
    "source": "BestBuy",
    "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
    "brand": "Sony",
    "sale_price_usd": 328.00,
    "url": "https://www.bestbuy.com/site/sony-wh-1000xm5",
    "features": "30hr battery, Multipoint connection, Auto NC Optimizer, Hi-Res Audio, Crystal clear hands-free calling",
    "raw_source_payload": {}
  },
  {
    "source": "BestBuy",
    "title": "Samsung 32-inch Odyssey G55A Gaming Monitor",
    "brand": "Samsung",
    "sale_price_usd": 279.99,
    "url": "https://www.bestbuy.com/site/samsung-odyssey-g55a",
    "features": "WQHD 2560x1440, 165Hz, 1ms MPRT, AMD FreeSync Premium, HDR10, HDMI 2.1",
    "raw_source_payload": {}
  },
  {
    "source": "BestBuy",
    "title": "Apple iPad Air 11-inch M3 chip",
    "brand": "Apple",
    "sale_price_usd": 549.99,
    "url": "https://www.bestbuy.com/site/apple-ipad-air-m3",
    "features": "11-inch Liquid Retina, M3 chip, 128GB, Wi-Fi 6E, 12MP camera, Apple Pencil Pro support",
    "raw_source_payload": {}
  },
  {
    "source": "BestBuy",
    "title": "Anker 7-in-1 USB-C Hub",
    "brand": "Anker",
    "sale_price_usd": 34.99,
    "url": "https://www.bestbuy.com/site/anker-usb-c-hub",
    "features": "7-in-1, 4K HDMI, 100W Power Delivery, USB 3.0, SD/microSD card reader",
    "raw_source_payload": {}
  },
  {
    "source": "Amazon",
    "title": "Acer Nitro V Gaming Laptop 15.6-inch",
    "brand": "Acer",
    "sale_price_usd": 699.99,
    "url": "https://www.amazon.com/dp/acer-nitro-v-gaming",
    "features": "15.6 FHD IPS 144Hz, Intel Core i5-13420H, 16GB DDR5, RTX 4050, 512GB NVMe SSD",
    "raw_source_payload": {}
  },
  {
    "source": "Amazon",
    "title": "Keychron K8 Pro Mechanical Keyboard Wireless",
    "brand": "Keychron",
    "sale_price_usd": 89.99,
    "url": "https://www.amazon.com/dp/keychron-k8-pro",
    "features": "TKL, Gateron G Pro Red switches, Bluetooth 5.1, QMK/VIA, Hot-swappable, Aluminum frame",
    "raw_source_payload": {}
  },
  {
    "source": "Amazon",
    "title": "Samsung 990 PRO 2TB NVMe M.2 SSD",
    "brand": "Samsung",
    "sale_price_usd": 149.99,
    "url": "https://www.amazon.com/dp/samsung-990-pro-2tb",
    "features": "PCIe 4.0 x4, Read 7450MB/s Write 6900MB/s, V-NAND, 256-bit AES encryption",
    "raw_source_payload": {}
  },
  {
    "source": "Amazon",
    "title": "Spigen Ultra Hybrid Case for iPhone 16 Pro",
    "brand": "Spigen",
    "sale_price_usd": 16.99,
    "url": "https://www.amazon.com/dp/spigen-iphone-16-pro-case",
    "features": "Air Cushion Technology, Crystal Clear, Anti-Yellowing, Slim Fit, Military Drop Protection",
    "raw_source_payload": {}
  },
  {
    "source": "Amazon",
    "title": "Logitech Brio 4K Webcam",
    "brand": "Logitech",
    "sale_price_usd": 129.99,
    "url": "https://www.amazon.com/dp/logitech-brio-4k",
    "features": "4K Ultra HD, Auto Light Correction, 5x Digital Zoom, Dual Noise-Cancelling Mics, USB-C",
    "raw_source_payload": {}
  }
]
```

- [ ] **Step 5: Create backend/tools/deal_search/tool.py**

```python
"""deal_search_tool — mock implementation using JSON fixtures.

Phase 4A: always returns fixture data. Real search (Phase 4B) gated behind
ENABLE_REAL_SEARCH, which raises NotImplementedError in this phase.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.shared.config import ENABLE_REAL_SEARCH
from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput, ProductCandidate

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mock_products.json"


def _load_products() -> list[ProductCandidate]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [ProductCandidate(**item) for item in raw]


def _keyword_match(product: ProductCandidate, query: str) -> bool:
    """Case-insensitive ANY-token match in title or features.

    A product matches if at least one query token appears in its title or
    features. Empty query matches everything. Uses any-token (not all-token)
    so Vietnamese messages that have been normalized still match.
    """
    q = query.strip()
    if not q:
        return True
    searchable = product.title.lower()
    if product.features:
        searchable += " " + product.features.lower()
    tokens = q.split()
    return any(token in searchable for token in tokens)


def deal_search(input: DealSearchInput) -> DealSearchOutput:
    """Run a mock product search using local JSON fixtures.

    Args:
        input: DealSearchInput with query_en, source filter, and result limit.

    Returns:
        DealSearchOutput with matching products and any warnings.

    Raises:
        NotImplementedError: If ENABLE_REAL_SEARCH is True (Phase 4A mock-only).
    """
    if ENABLE_REAL_SEARCH:
        raise NotImplementedError(
            "Real search is not available in Phase 4A mock-only mode. "
            "Set ENABLE_REAL_SEARCH=false or wait for Phase 4B."
        )

    all_products = _load_products()
    warnings: list[str] = []

    # Filter by source.
    if input.source in ("Amazon", "BestBuy"):
        candidates = [p for p in all_products if p.source == input.source]
    else:
        candidates = list(all_products)

    # Filter by keyword match if query is provided.
    if input.query_en.strip():
        candidates = [p for p in candidates if _keyword_match(p, input.query_en)]

    if not candidates:
        return DealSearchOutput(
            products=[],
            warnings=[f"No products found for query: {input.query_en}"],
        )

    # Limit per source.
    per_source_limit = input.max_results_per_source
    by_source: dict[str, list[ProductCandidate]] = {}
    for p in candidates:
        by_source.setdefault(p.source, []).append(p)

    limited: list[ProductCandidate] = []
    for source_products in by_source.values():
        limited.extend(source_products[:per_source_limit])

    if len(candidates) > len(limited):
        warnings.append(
            f"Results truncated to {per_source_limit} per source. "
            f"Total: {len(candidates)} matched, returning {len(limited)}."
        )

    return DealSearchOutput(products=limited, warnings=warnings)
```

- [ ] **Step 6: Verify the fixture JSON is valid and tool can load it**

```bash
cd shopping_assistant_v3 && uv run python -c "
from backend.tools.deal_search.tool import deal_search, DealSearchInput
result = deal_search(DealSearchInput(query_en='gaming laptop', source='All'))
print(f'Products: {len(result.products)}, Warnings: {result.warnings}')
for p in result.products:
    print(f'  [{p.source}] {p.title} — \${p.sale_price_usd}')
"
```

Expected: 2 products matched (ASUS ROG Strix + Acer Nitro V), no warnings from truncation.

- [ ] **Step 7: Verify with git status**

```bash
git status --short
```

Expected: new files under `backend/tools/`. No modifications to existing files.

---

### Task 3: Create price_estimator tool (schemas + fixtures + mock implementation)

**Files:**
- Create: `backend/tools/price_estimator/__init__.py`
- Create: `backend/tools/price_estimator/schemas.py`
- Create: `backend/tools/price_estimator/fixtures/mock_estimates.json`
- Create: `backend/tools/price_estimator/tool.py`

**Interfaces:**
- Consumes: `ProductCandidate` from Task 2
- Produces:
  - `PriceEstimateInput(product: ProductCandidate)`
  - `ModelBreakdown(frontier, specialist, neural)`
  - `PriceEstimateOutput(estimated_value_usd, discount_usd, deal_score, confidence?, model_breakdown, warnings)`
  - `estimate_price(input: PriceEstimateInput) -> PriceEstimateOutput`

- [ ] **Step 1: Create backend/tools/price_estimator/__init__.py**

```python
"""price_estimator tool — estimate fair USD value from normalized product evidence."""
```

- [ ] **Step 2: Create backend/tools/price_estimator/schemas.py**

```python
"""Pydantic schemas for price_estimator_tool matching agent_architecture.md contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.tools.deal_search.schemas import ProductCandidate


class PriceEstimateInput(BaseModel):
    product: ProductCandidate


class ModelBreakdown(BaseModel):
    frontier: float
    specialist: float
    neural: float


class PriceEstimateOutput(BaseModel):
    estimated_value_usd: float
    discount_usd: float
    deal_score: Literal["hot", "good", "ok", "overpriced"]
    confidence: float | None = None
    model_breakdown: ModelBreakdown
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: Create backend/tools/price_estimator/fixtures/mock_estimates.json**

Lookup table keyed by `"<source>|<title>"`. Covers selected products; unmatched products fall back to rule-based estimate.

```json
{
  "BestBuy|ASUS ROG Strix G16 Gaming Laptop": {
    "estimated_value_usd": 949.99,
    "model_breakdown": {
      "frontier": 960.0,
      "specialist": 920.0,
      "neural": 940.0
    }
  },
  "BestBuy|Sony WH-1000XM5 Wireless Noise Cancelling Headphones": {
    "estimated_value_usd": 399.99,
    "model_breakdown": {
      "frontier": 400.0,
      "specialist": 390.0,
      "neural": 410.0
    }
  },
  "Amazon|Acer Nitro V Gaming Laptop 15.6-inch": {
    "estimated_value_usd": 879.99,
    "model_breakdown": {
      "frontier": 890.0,
      "specialist": 850.0,
      "neural": 880.0
    }
  },
  "Amazon|Samsung 990 PRO 2TB NVMe M.2 SSD": {
    "estimated_value_usd": 199.99,
    "model_breakdown": {
      "frontier": 200.0,
      "specialist": 195.0,
      "neural": 205.0
    }
  }
}
```

- [ ] **Step 4: Create backend/tools/price_estimator/tool.py**

```python
"""price_estimator_tool — deterministic mock estimation using JSON fixture lookup.

Phase 4A: fixed lookup + rule-based fallback. Real model calls (Phase 4C) gated
behind ENABLE_REAL_MODEL_CALLS, which raises NotImplementedError in this phase.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.shared.config import ENABLE_REAL_MODEL_CALLS
from backend.tools.price_estimator.schemas import (
    ModelBreakdown,
    PriceEstimateInput,
    PriceEstimateOutput,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mock_estimates.json"


def _load_estimates() -> dict[str, dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _compute_deal_score(sale_price_usd: float, estimated_value_usd: float) -> str:
    discount = estimated_value_usd - sale_price_usd
    if discount >= 200:
        return "hot"
    if discount >= 100:
        return "good"
    if discount > 0:
        return "ok"
    return "overpriced"


def _fallback_estimate(sale_price: float) -> tuple[float, ModelBreakdown]:
    """Simple deterministic fallback: 10% markup, all models equal.

    Phase 4A uses a fixed 10% markup rule. model_breakdown values are all
    equal to the estimated value since no real model distinction exists.
    """
    estimated = round(sale_price * 1.10, 2)
    breakdown = ModelBreakdown(
        frontier=estimated,
        specialist=estimated,
        neural=estimated,
    )
    return estimated, breakdown


def estimate_price(input: PriceEstimateInput) -> PriceEstimateOutput:
    """Estimate fair USD value for a product using fixture lookup or fallback rule.

    Args:
        input: PriceEstimateInput wrapping a ProductCandidate.

    Returns:
        PriceEstimateOutput with estimated value, discount, deal score, and breakdown.

    Raises:
        NotImplementedError: If ENABLE_REAL_MODEL_CALLS is True (Phase 4A mock-only).
    """
    if ENABLE_REAL_MODEL_CALLS:
        raise NotImplementedError(
            "Real model calls are not available in Phase 4A mock-only mode. "
            "Set ENABLE_REAL_MODEL_CALLS=false or wait for Phase 4C."
        )

    product = input.product
    sale_price = product.sale_price_usd or 0.0
    lookup_key = f"{product.source}|{product.title}"
    estimates = _load_estimates()
    warnings: list[str] = []

    if lookup_key in estimates:
        entry = estimates[lookup_key]
        estimated_value = entry["estimated_value_usd"]
        breakdown = ModelBreakdown(**entry["model_breakdown"])
    else:
        estimated_value, breakdown = _fallback_estimate(sale_price)
        warnings.append("Price estimate from fallback rule — not in fixture lookup.")

    discount = round(estimated_value - sale_price, 2)
    deal_score = _compute_deal_score(sale_price, estimated_value)

    return PriceEstimateOutput(
        estimated_value_usd=estimated_value,
        discount_usd=discount,
        deal_score=deal_score,
        confidence=None,
        model_breakdown=breakdown,
        warnings=warnings,
    )
```

- [ ] **Step 5: Verify fixture JSON is valid and tool works**

```bash
cd shopping_assistant_v3 && uv run python -c "
from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.tool import estimate_price, PriceEstimateInput

# Test fixture lookup match.
p1 = ProductCandidate(
    source='BestBuy', title='ASUS ROG Strix G16 Gaming Laptop',
    brand='ASUS', sale_price_usd=749.99, url='https://example.com'
)
r1 = estimate_price(PriceEstimateInput(product=p1))
print(f'Lookup match: estimated={r1.estimated_value_usd}, discount={r1.discount_usd}, score={r1.deal_score}, warnings={r1.warnings}')

# Test fallback.
p2 = ProductCandidate(
    source='Amazon', title='Unknown Gadget XYZ',
    brand='Unknown', sale_price_usd=50.0, url='https://example.com'
)
r2 = estimate_price(PriceEstimateInput(product=p2))
print(f'Fallback: estimated={r2.estimated_value_usd}, discount={r2.discount_usd}, score={r2.deal_score}, warnings={r2.warnings}')
"
```

Expected: p1 matches fixture lookup (estimated=949.99, discount=200.00, score=hot). p2 uses fallback (estimated=55.00 from 50.00 * 1.10, score=ok, has fallback warning).

- [ ] **Step 6: Verify with git status**

```bash
git status --short
```

Expected: new files under `backend/tools/price_estimator/`. No other changes.

---

### Task 4: Add product + price_estimate repository functions

**Files:**
- Modify: `backend/database/repository.py`

**Interfaces:**
- Consumes: `Product`, `PriceEstimate` models from `backend/database/schema.py`
- Produces:
  - `create_product(session, *, job_id, source, title, brand?, sale_price_usd?, url?, features?, raw_source_payload?) -> Product`
  - `get_products_by_job_id(session, job_id) -> list[Product]`
  - `create_price_estimate(session, *, product_id, estimated_value_usd?, discount_usd?, deal_score?, confidence?, model_breakdown?, warnings?) -> PriceEstimate`
  - `get_price_estimates_by_product_ids(session, product_ids) -> list[PriceEstimate]`

- [ ] **Step 1: Add product + price_estimate repository functions**

Append to `backend/database/repository.py`:

```python
# ---------------------------------------------------------------------------
# Product repository
# ---------------------------------------------------------------------------

def create_product(
    session: Session,
    *,
    job_id: str,
    source: str,
    title: str,
    brand: str | None = None,
    sale_price_usd: float | None = None,
    url: str | None = None,
    features: str | None = None,
    raw_source_payload: dict[str, Any] | None = None,
) -> Product:
    """Store a normalized product candidate linked to a job."""
    product = Product(
        job_id=job_id,
        source=source,
        title=title,
        brand=brand,
        sale_price_usd=sale_price_usd,
        url=url,
        features=features,
        raw_source_payload=(
            json.dumps(raw_source_payload, ensure_ascii=False)
            if raw_source_payload is not None
            else None
        ),
    )
    session.add(product)
    session.flush()
    return product


def get_products_by_job_id(session: Session, job_id: str) -> list[Product]:
    """Return all products linked to a job, ordered by creation time."""
    return (
        session.query(Product)
        .filter(Product.job_id == job_id)
        .order_by(Product.created_at)
        .all()
    )


# ---------------------------------------------------------------------------
# Price estimate repository
# ---------------------------------------------------------------------------

def create_price_estimate(
    session: Session,
    *,
    product_id: str,
    estimated_value_usd: float | None = None,
    discount_usd: float | None = None,
    deal_score: str | None = None,
    confidence: float | None = None,
    model_breakdown: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> PriceEstimate:
    """Store a price estimate linked to a product."""
    estimate = PriceEstimate(
        product_id=product_id,
        estimated_value_usd=estimated_value_usd,
        discount_usd=discount_usd,
        deal_score=deal_score,
        confidence=confidence,
        model_breakdown=(
            json.dumps(model_breakdown, ensure_ascii=False)
            if model_breakdown is not None
            else None
        ),
        warnings=(
            json.dumps(warnings, ensure_ascii=False)
            if warnings is not None
            else None
        ),
    )
    session.add(estimate)
    session.flush()
    return estimate


def get_price_estimates_by_product_ids(
    session: Session, product_ids: list[str]
) -> list[PriceEstimate]:
    """Return price estimates for a batch of product IDs."""
    if not product_ids:
        return []
    return (
        session.query(PriceEstimate)
        .filter(PriceEstimate.product_id.in_(product_ids))
        .order_by(PriceEstimate.created_at)
        .all()
    )
```

Note: `Product` and `PriceEstimate` imports already exist at top of file from `backend.database.schema`.

- [ ] **Step 2: Verify imports resolve**

```bash
cd shopping_assistant_v3 && uv run python -c "from backend.database.repository import create_product, get_products_by_job_id, create_price_estimate, get_price_estimates_by_product_ids; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Verify with git status**

```bash
git status --short
```

Expected: only `backend/database/repository.py` modified.

---

### Task 5: Wire tools into worker with injectable seams

**Files:**
- Modify: `backend/worker.py`

**Interfaces:**
- Consumes: `DealSearchInput`, `DealSearchOutput`, `deal_search` from Task 2; `PriceEstimateInput`, `PriceEstimateOutput`, `estimate_price` from Task 3; `create_product`, `get_products_by_job_id`, `create_price_estimate` from Task 4.
- Produces: Updated `process_job(job_id, *, deal_search_runner=None, price_estimator_runner=None)`.
- Removes: `build_mock_result` function and `result_builder` parameter.

- [ ] **Step 1: Surgically edit backend/worker.py**

**Preserved from Phase 3 (do NOT change):**
- `_log_event()` structured logging
- `_save_failure()` function
- Idempotency gates (completed/failed/running skip, stale-running recovery)
- Daemon thread call in `main.py` (caller is unchanged)

**Changes to make:**
1. Remove `build_mock_result()` and the `result_builder: Callable` parameter.
2. Add `VIETNAMESE_STOP_WORDS` set and updated `_normalize_query()`.
3. Add `DealSearchRunner` and `PriceEstimatorRunner` type aliases.
4. Add `_run_deal_search()` and `_run_price_estimator()` helpers (agent_run wrapping).
5. Replace `process_job` body: parse request → normalize query → deal_search → persist products → estimate per product → persist estimates → build result.
6. Add `NotImplementedError` catch for safe ENABLE_REAL_* failure.
7. Add `PLACEHOLDER_ANSWER_VI` constant.

```python
"""Local async job worker.

process_job(job_id) is called by daemon thread after POST /api/chat-jobs.

Phase 4A pipeline:
  1. Parse request → normalize query_en
  2. deal_search_tool → save products to DB
  3. price_estimator_tool per product → save estimates to DB
  4. Build result_payload from tool outputs

Injectable tool runner seams (deal_search_runner, price_estimator_runner)
allow deterministic failure testing without monkeypatching.

Lifecycle: pending -> running -> completed (or failed).
Idempotent: completed jobs return existing result; running/failed jobs are skipped.
"""

from __future__ import annotations

import datetime
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from backend.database.repository import (
    create_agent_run,
    create_price_estimate,
    create_product,
    get_job_by_id,
    update_agent_run,
    update_job_error,
    update_job_result,
    update_job_status,
)
from backend.database.session import get_session_factory
from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput
from backend.tools.price_estimator.schemas import PriceEstimateInput, PriceEstimateOutput

logger = logging.getLogger("shopping_assistant_v3.worker")

DealSearchRunner = Callable[[DealSearchInput], DealSearchOutput]
PriceEstimatorRunner = Callable[[PriceEstimateInput], PriceEstimateOutput]

PLACEHOLDER_ANSWER_VI = (
    "Minh da tim thay mot so san pham phu hop. Duoi day la ket qua phan tich deal."
)

VIETNAMESE_STOP_WORDS = {
    "tìm", "tim", "mua", "cho", "giúp", "giup", "mình", "minh",
    "tôi", "toi", "với", "voi", "cần", "can", "muốn", "muon",
    "một", "mot", "cái", "cai", "nào", "nao", "giá", "gia",
    "dưới", "duoi", "trên", "tren", "khoảng", "khoang",
}


# ---------------------------------------------------------------------------
# Query normalization (Phase 4A bridge — Router replaces this in Phase 5)
# ---------------------------------------------------------------------------

def _normalize_query(message: str) -> str:
    """Normalize a Vietnamese user message into English-like search tokens.

    Phase 4A temporary bridge: lowercase + strip Vietnamese intent/filler words.
    Phase 5 Router will replace this with actual translation/intent extraction.
    """
    tokens = message.strip().lower().split()
    meaningful = [t for t in tokens if t not in VIETNAMESE_STOP_WORDS]
    return " ".join(meaningful)


# ---------------------------------------------------------------------------
# Tool runner helpers
# ---------------------------------------------------------------------------

def _run_deal_search(
    session: Any,
    job_id: str,
    query_en: str,
    source: str,
    max_results_per_source: int,
    runner: DealSearchRunner,
) -> DealSearchOutput:
    """Execute deal_search_tool wrapped in an agent_run audit record."""
    run = create_agent_run(
        session,
        job_id=job_id,
        component="deal_search_tool",
        run_type="tool",
        status="started",
        input_summary=f"query_en={query_en}, source={source}",
    )
    t0 = time.monotonic()
    try:
        search_input = DealSearchInput(
            query_en=query_en,
            source=source,
            max_results_per_source=max_results_per_source,
        )
        output = runner(search_input)
        duration_ms = int((time.monotonic() - t0) * 1000)
        update_agent_run(
            session,
            run,
            status="completed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            duration_ms=duration_ms,
            output_summary=f"{len(output.products)} products, {len(output.warnings)} warnings",
        )
        return output
    except NotImplementedError:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        duration_ms = int((time.monotonic() - t0) * 1000)
        update_agent_run(
            session,
            run,
            status="failed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            duration_ms=duration_ms,
            error_message="Deal search tool failed.",
        )
        raise


def _run_price_estimator(
    session: Any,
    job_id: str,
    product: Any,
    runner: PriceEstimatorRunner,
) -> PriceEstimateOutput:
    """Execute price_estimator_tool for a single product wrapped in an agent_run."""
    run = create_agent_run(
        session,
        job_id=job_id,
        component="price_estimator_tool",
        run_type="tool",
        status="started",
        input_summary=f"product={product.title[:80]}, source={product.source}",
    )
    t0 = time.monotonic()
    try:
        from backend.tools.deal_search.schemas import ProductCandidate as PC

        # Build a clean ProductCandidate from DB row for the tool input.
        candidate = PC(
            source=product.source,
            title=product.title,
            brand=product.brand,
            sale_price_usd=product.sale_price_usd,
            url=product.url,
            features=product.features,
            raw_source_payload=(
                json.loads(product.raw_source_payload)
                if product.raw_source_payload
                else {}
            ),
        )
        est_input = PriceEstimateInput(product=candidate)
        output = runner(est_input)
        duration_ms = int((time.monotonic() - t0) * 1000)
        update_agent_run(
            session,
            run,
            status="completed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            duration_ms=duration_ms,
            output_summary=(
                f"estimated={output.estimated_value_usd}, "
                f"discount={output.discount_usd}, "
                f"score={output.deal_score}"
            ),
        )
        return output
    except NotImplementedError:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        duration_ms = int((time.monotonic() - t0) * 1000)
        update_agent_run(
            session,
            run,
            status="failed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            duration_ms=duration_ms,
            error_message="Price estimator tool failed.",
        )
        raise


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------

def _log_event(event: str, job_id: str, **extra: object) -> None:
    payload = {
        "event": event,
        "job_id": job_id,
        "component": "worker",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **extra,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------

def process_job(
    job_id: str,
    *,
    deal_search_runner: DealSearchRunner | None = None,
    price_estimator_runner: PriceEstimatorRunner | None = None,
) -> None:
    """Process a single job through the mock search/pricing pipeline.

    Args:
        job_id: The job to process.
        deal_search_runner: Injectable deal_search function. Defaults to mock.
        price_estimator_runner: Injectable estimate_price function. Defaults to mock.

    Idempotency:
        - completed: return existing result, no new processing.
        - failed: skip.
        - running: skip unless stale (>5 min).
        - pending: process normally.
    """
    if deal_search_runner is None:
        from backend.tools.deal_search.tool import deal_search as deal_search_runner
    if price_estimator_runner is None:
        from backend.tools.price_estimator.tool import (
            estimate_price as price_estimator_runner,
        )

    factory = get_session_factory()
    session = factory()
    started_at = datetime.datetime.now(datetime.timezone.utc)
    t0 = time.monotonic()

    try:
        job = get_job_by_id(session, job_id)
        if job is None:
            _log_event("JOB_FAILED", job_id, reason="unknown_job_id")
            return

        # --- Idempotency gates ---
        if job.status == "completed":
            _log_event("JOB_SKIPPED", job_id, reason="already_completed")
            return

        if job.status == "failed":
            _log_event("JOB_SKIPPED", job_id, reason="already_failed")
            return

        if job.status == "running":
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            started = job.started_at
            if started is not None and started.tzinfo is not None:
                started = started.replace(tzinfo=None)
            stale = (
                started is None
                or (now_utc.replace(tzinfo=None) - started).total_seconds() > 300
            )
            if not stale:
                _log_event("JOB_SKIPPED", job_id, reason="already_running")
                return
            _log_event("JOB_RECOVERING", job_id, reason="stale_running")

        # --- Parse request ---
        request = json.loads(job.request_payload or "{}")
        message = request.get("message", "")
        source = request.get("source", "All")
        max_results = request.get("max_results_per_source", 5)
        query_en = _normalize_query(message)

        # --- Start job ---
        update_job_status(session, job, "running", started_at=started_at)
        _log_event("JOB_STARTED", job_id)

        # --- Phase 4A pipeline ---

        # Step 1: Deal search.
        search_output = _run_deal_search(
            session, job_id, query_en, source, max_results, deal_search_runner
        )

        # Step 2: Persist products.
        all_warnings: list[str] = list(search_output.warnings)
        db_products: list[Any] = []
        for sp in search_output.products:
            p = create_product(
                session,
                job_id=job_id,
                source=sp.source,
                title=sp.title,
                brand=sp.brand,
                sale_price_usd=sp.sale_price_usd,
                url=sp.url,
                features=sp.features,
                raw_source_payload=sp.raw_source_payload,
            )
            db_products.append(p)

        # Step 3: Estimate prices per product.
        result_products: list[dict[str, Any]] = []
        for db_p in db_products:
            est_output = _run_price_estimator(
                session, job_id, db_p, price_estimator_runner
            )
            create_price_estimate(
                session,
                product_id=db_p.id,
                estimated_value_usd=est_output.estimated_value_usd,
                discount_usd=est_output.discount_usd,
                deal_score=est_output.deal_score,
                confidence=est_output.confidence,
                model_breakdown=est_output.model_breakdown.model_dump(),
                warnings=est_output.warnings,
            )
            all_warnings.extend(est_output.warnings)
            result_products.append(
                {
                    "source": db_p.source,
                    "title": db_p.title,
                    "brand": db_p.brand,
                    "sale_price_usd": db_p.sale_price_usd,
                    "estimated_value_usd": est_output.estimated_value_usd,
                    "discount_usd": est_output.discount_usd,
                    "deal_score": est_output.deal_score,
                    "url": db_p.url,
                }
            )

        # Step 4: Build result payload.
        result = {
            "answer_vi": PLACEHOLDER_ANSWER_VI,
            "products": result_products,
            "warnings": all_warnings,
        }
        update_job_result(session, job, result)

        duration_ms = int((time.monotonic() - t0) * 1000)
        _log_event(
            "JOB_COMPLETED",
            job_id,
            duration_ms=duration_ms,
            product_count=len(result_products),
        )

        session.commit()

    except NotImplementedError as exc:
        session.rollback()
        safe_error = (
            "Real search/model calls are not available in Phase 4A mock-only mode."
        )
        logger.exception("Worker NotImplementedError for job %s", job_id)
        try:
            _save_failure(job_id, started_at, t0, safe_error)
        except Exception:
            logger.exception("Failed to persist job failure for %s", job_id)
        _log_event("JOB_FAILED", job_id, reason="not_implemented")

    except Exception as exc:
        session.rollback()
        safe_error = "Worker failed. Try again later."
        logger.exception("Worker internal failure for job %s", job_id)
        try:
            _save_failure(job_id, started_at, t0, safe_error)
        except Exception:
            logger.exception("Failed to persist job failure for %s", job_id)
        _log_event("JOB_FAILED", job_id)

    finally:
        session.close()


def _save_failure(
    job_id: str,
    started_at: datetime.datetime,
    t0: float,
    error_message: str,
) -> None:
    """Persist job failure in a fresh session."""
    factory = get_session_factory()
    session = factory()
    try:
        job = get_job_by_id(session, job_id)
        if job is None:
            return
        update_job_error(session, job, error_message)
        duration_ms = int((time.monotonic() - t0) * 1000)
        agent_run = create_agent_run(
            session,
            job_id=job_id,
            component="worker",
            run_type="worker",
            status="failed",
            input_summary="Phase 4A pipeline",
        )
        update_agent_run(
            session,
            agent_run,
            status="failed",
            ended_at=datetime.datetime.now(datetime.timezone.utc),
            duration_ms=duration_ms,
            error_message=error_message,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 2: Verify worker can import and run**

```bash
cd shopping_assistant_v3 && uv run python -c "
from backend.worker import process_job, _normalize_query
print(f'Normalize: {_normalize_query(\"  Gaming LAPTOP  \")}')
print('Worker module loaded OK')
"
```

Expected: `Normalize: gaming laptop`, `Worker module loaded OK`

- [ ] **Step 3: Verify with git status**

```bash
git status --short
```

Expected: `backend/worker.py` modified. No other changes.

---

### Task 6: Create tool tests (schemas + fixtures + mock behavior)

**Files:**
- Create: `tests/test_tools.py`

**Interfaces:**
- Tests `DealSearchInput`, `DealSearchOutput`, `deal_search`, `PriceEstimateInput`, `PriceEstimateOutput`, `estimate_price` from Tasks 2-3.

- [ ] **Step 1: Write tests/test_tools.py**

```python
"""Tool schema validation and mock behavior tests.

All tests use JSON fixtures only. No network, no model calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput, ProductCandidate
from backend.tools.deal_search.tool import deal_search
from backend.tools.price_estimator.schemas import (
    ModelBreakdown,
    PriceEstimateInput,
    PriceEstimateOutput,
)
from backend.tools.price_estimator.tool import estimate_price

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

PRODUCTS_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "backend" / "tools" / "deal_search" / "fixtures" / "mock_products.json"
)
ESTIMATES_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "backend" / "tools" / "price_estimator" / "fixtures" / "mock_estimates.json"
)


# ====================================================================
# Deal search schema tests
# ====================================================================

class TestDealSearchInput:
    def test_valid_input(self) -> None:
        inp = DealSearchInput(query_en="gaming laptop")
        assert inp.query_en == "gaming laptop"
        assert inp.source == "All"
        assert inp.max_results_per_source == 5  # Updated default.

    def test_default_max_results_is_5(self) -> None:
        """Phase 4A contract: default max_results_per_source changed from 6 to 5."""
        inp = DealSearchInput(query_en="test")
        assert inp.max_results_per_source == 5

    def test_empty_query_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DealSearchInput(query_en="")

    def test_invalid_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DealSearchInput(query_en="laptop", source="Ebay")  # type: ignore[arg-type]

    def test_max_results_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DealSearchInput(query_en="laptop", max_results_per_source=0)
        with pytest.raises(ValidationError):
            DealSearchInput(query_en="laptop", max_results_per_source=21)


class TestDealSearchOutput:
    def test_empty_output(self) -> None:
        out = DealSearchOutput()
        assert out.products == []
        assert out.warnings == []

    def test_output_with_products(self) -> None:
        p = ProductCandidate(source="Amazon", title="Test Product")
        out = DealSearchOutput(products=[p], warnings=["warning text"])
        assert len(out.products) == 1
        assert out.products[0].title == "Test Product"
        assert out.warnings == ["warning text"]


# ====================================================================
# Price estimator schema tests
# ====================================================================

class TestPriceEstimateInput:
    def test_valid_input(self) -> None:
        p = ProductCandidate(source="Amazon", title="Test Laptop", sale_price_usd=100.0)
        inp = PriceEstimateInput(product=p)
        assert inp.product.title == "Test Laptop"


class TestModelBreakdown:
    def test_valid_breakdown(self) -> None:
        mb = ModelBreakdown(frontier=100.0, specialist=90.0, neural=95.0)
        assert mb.frontier == 100.0
        assert mb.specialist == 90.0
        assert mb.neural == 95.0

    def test_missing_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelBreakdown(frontier=100.0, specialist=90.0)  # type: ignore[arg-type]


class TestPriceEstimateOutput:
    def test_valid_output(self) -> None:
        mb = ModelBreakdown(frontier=100.0, specialist=90.0, neural=95.0)
        out = PriceEstimateOutput(
            estimated_value_usd=110.0,
            discount_usd=10.0,
            deal_score="ok",
            model_breakdown=mb,
        )
        assert out.deal_score == "ok"
        assert out.discount_usd == 10.0

    def test_invalid_deal_score_rejected(self) -> None:
        mb = ModelBreakdown(frontier=100.0, specialist=90.0, neural=95.0)
        with pytest.raises(ValidationError):
            PriceEstimateOutput(
                estimated_value_usd=110.0,
                discount_usd=10.0,
                deal_score="amazing",  # type: ignore[arg-type]
                model_breakdown=mb,
            )


# ====================================================================
# Fixture integrity tests
# ====================================================================

class TestMockProductsFixture:
    def test_json_is_parseable(self) -> None:
        data = json.loads(PRODUCTS_FIXTURE.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 10

    def test_all_products_have_required_fields(self) -> None:
        data = json.loads(PRODUCTS_FIXTURE.read_text(encoding="utf-8"))
        for product in data:
            assert "source" in product
            assert product["source"] in ("Amazon", "BestBuy")
            assert "title" in product
            assert len(product["title"]) > 0
            assert "sale_price_usd" in product
            assert isinstance(product["sale_price_usd"], (int, float))
            assert "url" in product

    def test_source_counts(self) -> None:
        data = json.loads(PRODUCTS_FIXTURE.read_text(encoding="utf-8"))
        amazon_count = sum(1 for p in data if p["source"] == "Amazon")
        bestbuy_count = sum(1 for p in data if p["source"] == "BestBuy")
        assert amazon_count == 5
        assert bestbuy_count == 5


class TestMockEstimatesFixture:
    def test_json_is_parseable(self) -> None:
        data = json.loads(ESTIMATES_FIXTURE.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert len(data) >= 1

    def test_entries_have_required_fields(self) -> None:
        data = json.loads(ESTIMATES_FIXTURE.read_text(encoding="utf-8"))
        for key, entry in data.items():
            assert "|" in key  # Format: "source|title"
            assert "estimated_value_usd" in entry
            assert "model_breakdown" in entry
            mb = entry["model_breakdown"]
            assert "frontier" in mb
            assert "specialist" in mb
            assert "neural" in mb


# ====================================================================
# Mock deal_search behavior tests
# ====================================================================

class TestDealSearchMock:
    def test_returns_both_sources_when_source_is_all(self) -> None:
        result = deal_search(DealSearchInput(query_en="gaming laptop", source="All"))
        sources = {p.source for p in result.products}
        assert "Amazon" in sources
        assert "BestBuy" in sources

    def test_returns_only_amazon_when_filtered(self) -> None:
        result = deal_search(DealSearchInput(query_en="gaming laptop", source="Amazon"))
        sources = {p.source for p in result.products}
        assert sources == {"Amazon"}

    def test_returns_only_bestbuy_when_filtered(self) -> None:
        result = deal_search(DealSearchInput(query_en="gaming laptop", source="BestBuy"))
        sources = {p.source for p in result.products}
        assert sources == {"BestBuy"}

    def test_keyword_match_filters_results(self) -> None:
        result = deal_search(DealSearchInput(query_en="gaming laptop", source="All"))
        assert len(result.products) >= 2  # At least ASUS ROG + Acer Nitro
        for p in result.products:
            text = (p.title + " " + (p.features or "")).lower()
            assert "gaming" in text or "laptop" in text

    def test_empty_results_sets_warning(self) -> None:
        result = deal_search(DealSearchInput(query_en="xyznonexistent12345", source="All"))
        assert result.products == []
        assert len(result.warnings) >= 1
        assert "No products found" in result.warnings[0]

    def test_results_dont_exceed_max_per_source(self) -> None:
        result = deal_search(
            DealSearchInput(query_en="laptop", source="All", max_results_per_source=1)
        )
        by_source: dict[str, int] = {}
        for p in result.products:
            by_source[p.source] = by_source.get(p.source, 0) + 1
        for count in by_source.values():
            assert count <= 1


# ====================================================================
# Mock price_estimator behavior tests
# ====================================================================

def _make_product(
    source: str = "Amazon",
    title: str = "Test Product",
    sale_price: float = 100.0,
) -> ProductCandidate:
    return ProductCandidate(
        source=source, title=title, sale_price_usd=sale_price, url="https://example.com"
    )


class TestPriceEstimatorMock:
    def test_fixture_lookup_returns_exact_value(self) -> None:
        """Product in mock_estimates.json should return the exact fixture value."""
        p = _make_product(
            source="BestBuy",
            title="ASUS ROG Strix G16 Gaming Laptop",
            sale_price=749.99,
        )
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.estimated_value_usd == 949.99
        assert result.discount_usd == 200.0
        assert result.deal_score == "hot"
        assert result.warnings == []  # No fallback warning.

    def test_fallback_rule_for_unknown_product(self) -> None:
        """Product not in fixtures should use 10% markup fallback."""
        p = _make_product(
            source="Amazon",
            title="Unknown Gadget XYZ",
            sale_price=100.0,
        )
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.estimated_value_usd == 110.0  # 100.0 * 1.10
        assert result.discount_usd == 10.0
        assert result.deal_score == "ok"
        assert len(result.warnings) >= 1
        assert "fallback" in result.warnings[0].lower()
        # model_breakdown: all three equal to estimated_value_usd.
        assert result.model_breakdown.frontier == 110.0
        assert result.model_breakdown.specialist == 110.0
        assert result.model_breakdown.neural == 110.0

    def test_identical_inputs_produce_identical_outputs(self) -> None:
        """Deterministic: same product → same estimate (no randomness)."""
        p = _make_product(
            source="Amazon",
            title="Consistent Test Product",
            sale_price=50.0,
        )
        r1 = estimate_price(PriceEstimateInput(product=p))
        r2 = estimate_price(PriceEstimateInput(product=p))
        assert r1.estimated_value_usd == r2.estimated_value_usd
        assert r1.discount_usd == r2.discount_usd
        assert r1.deal_score == r2.deal_score

    def test_deal_score_hot(self) -> None:
        """Fixture-backed product with large discount gets 'hot'."""
        p_big = _make_product(
            source="BestBuy",
            title="ASUS ROG Strix G16 Gaming Laptop",
            sale_price=749.99,
        )
        result = estimate_price(PriceEstimateInput(product=p_big))
        assert result.deal_score == "hot"
        assert result.discount_usd >= 200

    def test_deal_score_overpriced(self) -> None:
        """Product priced above estimated value gets overpriced."""
        p = _make_product(
            source="BestBuy",
            title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
            sale_price=500.00,  # Above fixture estimate of 399.99
        )
        result = estimate_price(PriceEstimateInput(product=p))
        # With sale_price=500 and fixture estimated=399.99, discount is negative.
        assert result.deal_score == "overpriced"
        assert result.discount_usd < 0

    def test_model_breakdown_present(self) -> None:
        p = _make_product(sale_price=100.0)
        result = estimate_price(PriceEstimateInput(product=p))
        assert result.model_breakdown.frontier > 0
        assert result.model_breakdown.specialist > 0
        assert result.model_breakdown.neural > 0


# ====================================================================
# ENABLE_REAL_* flag tests
# ====================================================================

class TestRealModeFlags:
    def test_real_search_raises_not_implemented(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.deal_search.tool.ENABLE_REAL_SEARCH", True
        )
        with pytest.raises(NotImplementedError, match="Phase 4A"):
            deal_search(DealSearchInput(query_en="laptop"))

    def test_real_model_calls_raises_not_implemented(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.tool.ENABLE_REAL_MODEL_CALLS", True
        )
        p = _make_product()
        with pytest.raises(NotImplementedError, match="Phase 4A"):
            estimate_price(PriceEstimateInput(product=p))
```

- [ ] **Step 2: Run tool tests**

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_tools.py -v
```

Expected: all tests PASS (~22 tests).

- [ ] **Step 3: Verify with git status**

```bash
git status --short
```

Expected: new file `tests/test_tools.py`. No other changes.

---

### Task 7: Create repository tests (product + price_estimate CRUD)

**Files:**
- Create: `tests/test_repository.py`

- [ ] **Step 1: Write tests/test_repository.py**

```python
"""Repository tests for product and price_estimate persistence.

All tests use the isolated temp SQLite from conftest.py. No network, no model calls.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from backend.database.repository import (
    create_conversation,
    create_job,
    create_price_estimate,
    create_product,
    get_price_estimates_by_product_ids,
    get_products_by_job_id,
)
from backend.database.schema import Job, Product
from backend.shared.config import DEMO_USER_ID


def _create_job_with_conversation(session: Session) -> Job:
    conv = create_conversation(session, user_id=DEMO_USER_ID)
    session.commit()
    job = create_job(
        session,
        user_id=DEMO_USER_ID,
        conversation_id=conv.id,
        request_payload={"message": "test"},
    )
    session.commit()
    return job


class TestProductRepository:
    def test_create_and_retrieve_by_job_id(self, db_session: Session) -> None:
        job = _create_job_with_conversation(db_session)
        prod = create_product(
            db_session,
            job_id=job.id,
            source="Amazon",
            title="Test Laptop",
            brand="TestBrand",
            sale_price_usd=599.99,
            url="https://amazon.com/test",
            features="16GB RAM",
            raw_source_payload={"sku": "ABC123"},
        )
        db_session.commit()

        assert prod.id is not None
        assert prod.source == "Amazon"

        products = get_products_by_job_id(db_session, job.id)
        assert len(products) == 1
        assert products[0].title == "Test Laptop"
        assert products[0].sale_price_usd == 599.99
        # raw_source_payload stored as JSON string.
        raw = json.loads(products[0].raw_source_payload)
        assert raw["sku"] == "ABC123"

    def test_get_products_by_job_id_empty(self, db_session: Session) -> None:
        assert get_products_by_job_id(db_session, "no-such-job") == []

    def test_multiple_products_for_same_job(self, db_session: Session) -> None:
        job = _create_job_with_conversation(db_session)
        create_product(db_session, job_id=job.id, source="Amazon", title="Product A")
        create_product(db_session, job_id=job.id, source="BestBuy", title="Product B")
        db_session.commit()

        products = get_products_by_job_id(db_session, job.id)
        assert len(products) == 2

    def test_nulls_allowed_for_optional_fields(self, db_session: Session) -> None:
        job = _create_job_with_conversation(db_session)
        prod = create_product(
            db_session, job_id=job.id, source="Amazon", title="Minimal Product"
        )
        db_session.commit()
        assert prod.brand is None
        assert prod.sale_price_usd is None
        assert prod.url is None
        assert prod.features is None
        assert prod.raw_source_payload is None


class TestPriceEstimateRepository:
    def test_create_and_retrieve(self, db_session: Session) -> None:
        job = _create_job_with_conversation(db_session)
        prod = create_product(
            db_session, job_id=job.id, source="Amazon", title="Test"
        )
        db_session.commit()

        est = create_price_estimate(
            db_session,
            product_id=prod.id,
            estimated_value_usd=899.99,
            discount_usd=200.00,
            deal_score="hot",
            confidence=None,
            model_breakdown={"frontier": 900.0, "specialist": 850.0, "neural": 880.0},
            warnings=["test warning"],
        )
        db_session.commit()

        assert est.id is not None
        assert est.deal_score == "hot"

        estimates = get_price_estimates_by_product_ids(db_session, [prod.id])
        assert len(estimates) == 1
        assert estimates[0].estimated_value_usd == 899.99

        # JSON fields are stored as strings.
        mb = json.loads(estimates[0].model_breakdown)
        assert mb["frontier"] == 900.0
        warnings = json.loads(estimates[0].warnings)
        assert warnings == ["test warning"]

    def test_get_by_empty_product_ids(self, db_session: Session) -> None:
        assert get_price_estimates_by_product_ids(db_session, []) == []

    def test_get_by_nonexistent_product_ids(self, db_session: Session) -> None:
        assert get_price_estimates_by_product_ids(db_session, ["no-such-id"]) == []

    def test_cascade_delete_job_deletes_products_and_estimates(
        self, db_session: Session
    ) -> None:
        """Verify SQLAlchemy cascade="all, delete-orphan" works end-to-end."""
        from backend.database.schema import PriceEstimate

        job = _create_job_with_conversation(db_session)
        prod = create_product(
            db_session, job_id=job.id, source="Amazon", title="Cascade Test"
        )
        db_session.commit()
        create_price_estimate(
            db_session,
            product_id=prod.id,
            estimated_value_usd=100.0,
            discount_usd=10.0,
            deal_score="ok",
            model_breakdown={"frontier": 100.0, "specialist": 90.0, "neural": 95.0},
        )
        db_session.commit()

        # Verify rows exist.
        assert len(get_products_by_job_id(db_session, job.id)) == 1
        assert (
            len(get_price_estimates_by_product_ids(db_session, [prod.id])) == 1
        )

        # Delete job and verify cascade.
        db_session.delete(job)
        db_session.commit()

        assert get_products_by_job_id(db_session, job.id) == []
        remaining_estimates = (
            db_session.query(PriceEstimate).filter_by(product_id=prod.id).all()
        )
        assert remaining_estimates == []
```

- [ ] **Step 2: Run repository tests**

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_repository.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 3: Verify with git status**

```bash
git status --short
```

Expected: new file `tests/test_repository.py`. No other changes.

---

### Task 8: Update worker tests and API tests

**Files:**
- Modify: `tests/test_worker.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Surgically edit tests/test_worker.py**

**Preserved from Phase 3 (do NOT rewrite from scratch):**
- `TestIdempotency` — all 4 tests (completed not reprocessed, running skip, stale recovery, failed skip)
- `TestUnknownJob` — unknown_job_does_not_crash
- `TestLogEvents` — all 3 tests (started+completed events, failed event, valid JSON)
- `_create_pending_job` helper signature

**Changes:**
- Remove `build_mock_result` import and `TestMockResult` class
- Replace `result_builder` injection with `deal_search_runner`/`price_estimator_runner` seams in failure tests
- Add `TestProcessJob` tests for Phase 4A pipeline (persistence, agent_runs, answer_vi)
- Add `TestRealModeInWorker` tests for safe ENABLE_REAL_* failure

```python
"""Worker tests: tool-based pipeline, idempotency, failure path, audit, and log events.

All tests call process_job() directly. No network, no model calls, no real search.
Uses the isolated temp SQLite from conftest.py.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from backend.database.repository import (
    create_conversation,
    create_job,
    get_job_by_id,
    get_products_by_job_id,
    update_job_error,
    update_job_status,
)
from backend.database.schema import AgentRun, Job, PriceEstimate, Product
from backend.shared.config import DEMO_USER_ID
from backend.tools.deal_search.schemas import DealSearchInput, DealSearchOutput
from backend.tools.price_estimator.schemas import PriceEstimateInput, PriceEstimateOutput
from backend.worker import process_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_pending_job(session: Session) -> Job:
    conv = create_conversation(session, user_id=DEMO_USER_ID)
    session.commit()
    job = create_job(
        session,
        user_id=DEMO_USER_ID,
        conversation_id=conv.id,
        request_payload={"message": "gaming laptop"},
    )
    session.commit()
    return job


def _result_shape(result: dict) -> None:
    assert "answer_vi" in result
    assert isinstance(result["answer_vi"], str)
    assert len(result["answer_vi"]) > 0
    assert "products" in result
    assert isinstance(result["products"], list)
    assert "warnings" in result
    assert isinstance(result["warnings"], list)


# ---------------------------------------------------------------------------
# process_job — happy path (Phase 4A tool pipeline)
# ---------------------------------------------------------------------------

class TestProcessJob:
    def test_completes_with_product_and_estimate_persistence(
        self, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)

        assert job.status == "completed"
        assert job.completed_at is not None
        result = json.loads(job.result_payload)
        _result_shape(result)
        assert len(result["products"]) >= 1

        # Verify DB persistence.
        products = get_products_by_job_id(db_session, job.id)
        assert len(products) == len(result["products"])
        for p in products:
            assert p.source in ("Amazon", "BestBuy")

            # Each product should have a price estimate.
            estimates = (
                db_session.query(PriceEstimate)
                .filter(PriceEstimate.product_id == p.id)
                .all()
            )
            assert len(estimates) == 1
            assert estimates[0].deal_score is not None

    def test_result_products_match_db_rows(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)

        result = json.loads(job.result_payload)
        db_products = get_products_by_job_id(db_session, job.id)
        assert len(result["products"]) == len(db_products)

        result_titles = {p["title"] for p in result["products"]}
        db_titles = {p.title for p in db_products}
        assert result_titles == db_titles

    def test_creates_agent_runs_for_each_tool(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)

        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id)
            .all()
        )
        # At minimum: 1 deal_search + N price_estimator runs.
        components = {r.component for r in runs}
        assert "deal_search_tool" in components
        assert "price_estimator_tool" in components

        # All runs should be completed.
        for run in runs:
            assert run.status == "completed"
            assert run.duration_ms is not None
            assert run.duration_ms >= 0

    def test_answer_vi_is_non_empty_vietnamese_placeholder(
        self, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        result = json.loads(job.result_payload)
        assert len(result["answer_vi"]) > 0
        # Contains Vietnamese characters or is the expected placeholder.
        assert isinstance(result["answer_vi"], str)

    def test_sets_running_before_completing(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        assert job.status == "completed"


# ---------------------------------------------------------------------------
# Idempotency (preserved from Phase 3)
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_completed_job_not_reprocessed(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        first_completed = job.completed_at
        first_result = job.result_payload

        process_job(job.id)
        db_session.refresh(job)
        assert job.status == "completed"
        assert job.completed_at == first_completed
        assert job.result_payload == first_result

        runs = db_session.query(AgentRun).filter(AgentRun.job_id == job.id).all()
        assert len(runs) > 0

    def test_running_job_is_skipped_when_fresh(self, db_session: Session) -> None:
        import datetime as dt

        job = _create_pending_job(db_session)
        update_job_status(
            db_session, job, "running",
            started_at=dt.datetime.now(dt.timezone.utc),
        )
        db_session.commit()
        original_updated = job.updated_at

        process_job(job.id)
        db_session.refresh(job)
        assert job.status == "running"
        assert job.updated_at == original_updated

    def test_stale_running_job_is_recovered(self, db_session: Session) -> None:
        import datetime as dt

        job = _create_pending_job(db_session)
        update_job_status(
            db_session, job, "running",
            started_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10),
        )
        db_session.commit()

        process_job(job.id)
        db_session.refresh(job)
        assert job.status == "completed"

    def test_failed_job_is_skipped(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        update_job_error(db_session, job, "previous failure")
        db_session.commit()
        original_error = job.error_message

        process_job(job.id)
        db_session.refresh(job)
        assert job.status == "failed"
        assert job.error_message == original_error


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------

class TestFailurePath:
    def test_deal_search_failure_sets_job_failed(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("mock search failure")

        process_job(job.id, deal_search_runner=_failing_search)
        db_session.refresh(job)
        assert job.status == "failed"
        assert job.error_message is not None
        assert "Worker failed" in job.error_message

    def test_price_estimator_failure_sets_job_failed(
        self, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session)

        def _failing_estimator(_input: PriceEstimateInput) -> PriceEstimateOutput:
            raise RuntimeError("mock estimator failure")

        process_job(job.id, price_estimator_runner=_failing_estimator)
        db_session.refresh(job)
        assert job.status == "failed"
        assert "Worker failed" in job.error_message

    def test_failure_creates_failed_agent_run(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("boom")

        process_job(job.id, deal_search_runner=_failing_search)
        db_session.refresh(job)

        runs = (
            db_session.query(AgentRun)
            .filter(AgentRun.job_id == job.id, AgentRun.status == "failed")
            .all()
        )
        assert len(runs) >= 1

    def test_failure_does_not_leave_stale_running(self, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("x")

        process_job(job.id, deal_search_runner=_failing_search)
        db_session.refresh(job)
        assert job.status == "failed"


# ---------------------------------------------------------------------------
# ENABLE_REAL_* flag in worker context
# ---------------------------------------------------------------------------

class TestRealModeInWorker:
    def test_real_search_flag_fails_job_with_safe_error(
        self, db_session: Session, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "backend.tools.deal_search.tool.ENABLE_REAL_SEARCH", True
        )
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        assert job.status == "failed"
        assert "Phase 4A" in job.error_message
        # No raw NotImplementedError text leaked.
        assert "NotImplementedError" not in job.error_message

    def test_real_model_flag_fails_job_with_safe_error(
        self, db_session: Session, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "backend.tools.price_estimator.tool.ENABLE_REAL_MODEL_CALLS", True
        )
        job = _create_pending_job(db_session)
        process_job(job.id)
        db_session.refresh(job)
        assert job.status == "failed"
        assert "Phase 4A" in job.error_message
        assert "NotImplementedError" not in job.error_message


# ---------------------------------------------------------------------------
# Unknown job
# ---------------------------------------------------------------------------

class TestUnknownJob:
    def test_unknown_job_does_not_crash(self) -> None:
        process_job("nonexistent-job-id")


# ---------------------------------------------------------------------------
# Log events (preserved from Phase 3, adapted for Phase 4A)
# ---------------------------------------------------------------------------

class TestLogEvents:
    def test_emits_started_and_completed_events(
        self, caplog, db_session: Session
    ) -> None:
        job = _create_pending_job(db_session)
        with caplog.at_level("INFO", logger="shopping_assistant_v3.worker"):
            process_job(job.id)

        log_text = caplog.text
        assert "JOB_STARTED" in log_text
        assert "JOB_COMPLETED" in log_text
        assert job.id in log_text

    def test_emits_failed_event_on_error(self, caplog, db_session: Session) -> None:
        job = _create_pending_job(db_session)

        def _failing_search(_input: DealSearchInput) -> DealSearchOutput:
            raise RuntimeError("xyz")

        with caplog.at_level("INFO", logger="shopping_assistant_v3.worker"):
            process_job(job.id, deal_search_runner=_failing_search)

        log_text = caplog.text
        assert "JOB_STARTED" in log_text
        assert "JOB_FAILED" in log_text
        assert job.id in log_text

    def test_logs_are_valid_json(self, caplog, db_session: Session) -> None:
        job = _create_pending_job(db_session)
        with caplog.at_level("INFO", logger="shopping_assistant_v3.worker"):
            process_job(job.id)

        for record in caplog.records:
            if record.name == "shopping_assistant_v3.worker":
                parsed = json.loads(record.message)
                assert parsed["job_id"] == job.id
                assert "event" in parsed
                assert parsed["component"] == "worker"
                assert "timestamp" in parsed
```

- [ ] **Step 2: Update tests/test_api.py — add default max_results assertion**

Add one test to `TestCreateChatJob` class (in `tests/test_api.py`, after line 154 — the `test_request_payload_is_stored` method):

```python
    def test_default_max_results_is_5(self, client: TestClient, db_session: Session) -> None:
        """Phase 4A contract: default max_results_per_source changed from 6 to 5."""
        response = client.post(
            "/api/chat-jobs",
            json={"message": "Tim laptop"},
        )
        assert response.status_code == 201
        body = response.json()
        job = get_job_by_id(db_session, body["job_id"])
        assert job is not None
        stored = json.loads(job.request_payload)
        assert stored["max_results_per_source"] == 5
```

- [ ] **Step 3: Run worker and API tests**

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_worker.py tests/test_api.py -v
```

Expected: all tests PASS (~16 worker + 10 API = 26 tests).

- [ ] **Step 4: Verify with git status**

```bash
git status --short
```

Expected: `tests/test_worker.py`, `tests/test_api.py` modified. No other changes.

---

### Task 9: Run full test suite and verification

- [ ] **Step 1: Run full test suite**

```bash
cd shopping_assistant_v3 && uv run pytest tests/ -v
```

Expected: all tests PASS. Target: ~22 (tools) + 7 (repository) + 16 (worker) + 10 (API) = ~55 tests risk-based.

- [ ] **Step 2: Verify no segment4 imports**

```bash
cd shopping_assistant_v3 && rg "segment4" backend/ tests/ || echo "No segment4 imports found — OK"
```

Expected: `No segment4 imports found — OK`

- [ ] **Step 3: Verify no live network or model calls in default tests**

All tests pass without `OPENAI_API_KEY`, network access, or model files. Confirm by checking no test module imports `openai`, `litellm`, `curl_cffi`, or `modal`.

```bash
cd shopping_assistant_v3 && rg "openai|litellm|curl_cffi|modal|brave" tests/ || echo "No paid/external API imports in tests — OK"
```

- [ ] **Step 4: CodeGraph status check**

```bash
codegraph status shopping_assistant_v3
```

Report the output in the implementation report.

- [ ] **Step 5: Write implementation report**

Write `shopping_assistant_v3/reports/phase_4a_mock_tools_report.md` using the template at `TEMPLATE_IMPLEMENTATION_REPORT.md`. Include self-check (security, data safety, reliability, performance, tests).

- [ ] **Step 6: Show final git status and handoff**

```bash
git status --short
```

Verify only approved files are changed. No segment4/, no v2/. Ready for Codex review handoff.

---

## Task Dependency Graph

```
Task 1 (max_results default)
  │
  v
Task 2 (deal_search tool)
  │
  v
Task 3 (price_estimator tool)
  │
  v
Task 4 (repository functions)
  │
  v
Task 5 (worker integration)
  │
  ├──> Task 6 (tool tests)
  ├──> Task 7 (repository tests)
  └──> Task 8 (worker + API tests)
            │
            v
          Task 9 (full suite + report)
```

Tasks 6-8 can be done in parallel after Task 5 (though they're small enough sequential is fine).
