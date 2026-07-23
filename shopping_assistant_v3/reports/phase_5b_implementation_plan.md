# Phase 5B Agents SDK Router/Synthesizer Providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional OpenAI Agents SDK providers for the V3 Router and Synthesizer, with OpenAI dashboard tracing and deterministic fallback, while keeping the Phase 5A deterministic path as the default.

**Architecture:** The worker remains the orchestration owner. Phase 5B adds provider boundaries around Router and Synthesizer only: deterministic providers run by default, SDK providers run only when `ENABLE_REAL_MODEL_CALLS=true` and `ENABLE_AGENTS_SDK=true`. The SDK providers use structured Pydantic outputs, safe `RunConfig` tracing metadata, and never receive search/pricing tools.

**Tech Stack:** Python 3.12, FastAPI, SQLite, SQLAlchemy, Pydantic, optional `openai-agents>=0.18.3`, OpenAI Agents SDK `Agent`, `Runner`, and `RunConfig`.

## Global Constraints

- V3 source of truth remains `shopping_assistant_v3/`; `shopping_assistant_v2/` and `segment4/` are not part of this implementation.
- Default path must remain deterministic and mock-only.
- `openai-agents` must be an optional extra named `agents`, not a base dependency.
- SDK path only runs when both `ENABLE_REAL_MODEL_CALLS=true` and `ENABLE_AGENTS_SDK=true`.
- SDK path requires explicit model IDs: `MODEL_ID_ROUTER` and `MODEL_ID_SYNTHESIZER`.
- No default test may call OpenAI, Modal, Amazon, BestBuy, AWS, Terraform, or require secrets.
- Do not expose `deal_search_tool` or `price_estimator_tool` as SDK tools in Phase 5B.
- Worker-owned order stays fixed: Router provider -> search tool -> pricing tool -> Synthesizer provider.
- `RunConfig.trace_include_sensitive_data` must be `False` for every SDK call.
- `RunConfig.group_id` must be `job_id`; `trace_metadata` must contain only safe bounded fields.
- Phase 5B uses OpenAI dashboard tracing plus existing V3 `agent_runs`; no custom `TracingProcessor` and no trace-events API endpoint in this milestone.
- SDK failures fall back to deterministic Router/Synthesizer and add bounded warnings.
- Bounded warning codes: `router_sdk_fallback_used:<reason>` and `synthesizer_sdk_fallback_used:<reason>`.
- Do not log, print, persist, or summarize secret values.
- Do not change the API test harness dependency strategy unless the user explicitly approves it.

## OpenAI SDK Evidence Used

- `openai-agents` latest checked on PyPI at planning time: `0.18.3` published July 17, 2026.
- Agents SDK supports `Agent`, `Runner`, and structured `output_type` using Pydantic-compatible models.
- `RunConfig` supports `workflow_name`, `group_id`, `trace_metadata`, and `trace_include_sensitive_data`.
- Agents SDK tracing may include sensitive generation/tool payloads by default; Phase 5B must set `trace_include_sensitive_data=False`.
- Custom `TracingProcessor` exists, but Phase 5B intentionally defers it.

---

## File Structure

Create:

- `backend/router/provider.py` - provider selector and deterministic/SDK fallback wrapper for Router.
- `backend/router/sdk_provider.py` - lazy OpenAI Agents SDK Router provider.
- `backend/synthesizer/provider.py` - provider selector and deterministic/SDK fallback wrapper for Synthesizer.
- `backend/synthesizer/sdk_provider.py` - lazy OpenAI Agents SDK Synthesizer provider.
- `backend/synthesizer/validation.py` - simple evidence validation for SDK Synthesizer output.
- `tests/test_agents_sdk_providers.py` - mock-only unit tests using fake SDK modules/runners.
- `tests/test_real_agents_sdk.py` - opt-in real SDK smoke tests, skipped by default.
- `reports/phase_5b_agents_sdk_router_synthesizer_report.md` - implementation evidence report.

Modify:

- `pyproject.toml` - add `[project.optional-dependencies].agents`.
- `backend/worker.py` - call provider wrappers instead of direct deterministic functions.
- `backend/synthesizer/deterministic.py` - translate new SDK fallback warning prefixes.
- `tests/test_worker.py` - cover worker fallback warnings and audit behavior.

---

### Task 0: Preflight API Test Harness And CodeGraph Baseline

**Files:** None.

**Interfaces:**
- Consumes: existing Phase 5A backend and tests.
- Produces: report evidence for the known `TestClient`/AnyIO sandbox issue.

- [ ] **Step 1: Confirm worktree scope**

Run:

```bash
git status --short
```

Expected: V3 changes are either clean or only Phase 5B files. Existing unrelated untracked files in `shopping_assistant_v2/` must remain untouched.

- [ ] **Step 2: Confirm V3 CodeGraph index**

Run:

```bash
codegraph status shopping_assistant_v3
```

Expected: index exists. If stale, run:

```bash
codegraph sync shopping_assistant_v3
```

Do not run `codegraph init`.

- [ ] **Step 3: Reproduce AnyIO threadpool behavior**

Run:

```bash
cd shopping_assistant_v3 && uv run python -c "import anyio
async def main():
    result = await anyio.to_thread.run_sync(lambda: 'OK')
    print(result)
anyio.run(main)"
```

Expected outside the known Codex sandbox issue: `OK`. If this hangs or times out in Codex, record it in the implementation report and continue with non-API focused tests.

- [ ] **Step 4: Reproduce minimal FastAPI TestClient behavior**

Run:

```bash
cd shopping_assistant_v3 && uv run python -c "from fastapi import FastAPI
from fastapi.testclient import TestClient
app = FastAPI()
@app.get('/ping')
def ping():
    return {'ok': True}
with TestClient(app) as client:
    print(client.get('/ping').json())"
```

Expected outside the known Codex sandbox issue: `{'ok': True}`. If this hangs or times out in Codex, record it in the implementation report and do not change test dependencies.

---

### Task 1: Add Optional Agents SDK Dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock` after `uv lock`

**Interfaces:**
- Produces: optional extra `agents = ["openai-agents>=0.18.3"]`.

- [ ] **Step 1: Add optional extra to `pyproject.toml`**

Add this block under `[project.optional-dependencies]`, after `specialist`:

```toml
agents = [
    "openai-agents>=0.18.3",
]
```

- [ ] **Step 2: Verify TOML syntax**

Run:

```bash
cd shopping_assistant_v3 && uv run python -c "import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
assert data['project']['optional-dependencies']['agents'] == ['openai-agents>=0.18.3']
print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Update lockfile**

Run:

```bash
cd shopping_assistant_v3 && uv lock
```

Expected: `uv.lock` updates with the optional `openai-agents` dependency. This may require network access; if sandbox blocks it, request approval rather than bypassing.

- [ ] **Step 4: Verify base imports do not require Agents SDK**

Run:

```bash
cd shopping_assistant_v3 && uv run python -c "from backend.router.deterministic import deterministic_route; from backend.synthesizer.deterministic import deterministic_synthesize; print('OK')"
```

Expected: `OK` without installing `[agents]`.

---

### Task 2: Add Router Provider Boundary

**Files:**
- Create: `backend/router/provider.py`
- Create: `backend/router/sdk_provider.py`
- Test: `tests/test_agents_sdk_providers.py`

**Interfaces:**
- Consumes: `RouterInput`, `RouterOutput`, `deterministic_route`.
- Produces: `RouterProviderResult(output: RouterOutput, provider: str, warnings: list[str])`.
- Produces: `route_with_provider(message_vi: str, job_id: str) -> RouterProviderResult`.
- Produces: `sdk_route(input_data: RouterInput, *, job_id: str, model_id: str) -> RouterOutput`.

- [ ] **Step 1: Write failing provider-selection tests**

Create `tests/test_agents_sdk_providers.py` with these initial tests:

```python
"""Phase 5B SDK provider tests — mock-only, no OpenAI calls."""

from __future__ import annotations

from backend.router.schemas import IntentEnum, RouterOutput


def test_router_provider_defaults_to_deterministic(monkeypatch) -> None:
    import backend.router.provider as provider

    monkeypatch.setattr(provider, "ENABLE_REAL_MODEL_CALLS", False)
    monkeypatch.setattr(provider, "ENABLE_AGENTS_SDK", False)

    result = provider.route_with_provider(
        "Tim laptop gaming duoi 800 do",
        job_id="job-test",
    )

    assert result.provider == "deterministic"
    assert result.output.intent == IntentEnum.SEARCH_DEALS
    assert result.warnings == []


def test_router_provider_falls_back_when_sdk_raises(monkeypatch) -> None:
    import backend.router.provider as provider

    monkeypatch.setattr(provider, "ENABLE_REAL_MODEL_CALLS", True)
    monkeypatch.setattr(provider, "ENABLE_AGENTS_SDK", True)
    monkeypatch.setattr(provider, "MODEL_ID_ROUTER", "gpt-test-router")

    def fail_sdk(*args, **kwargs):
        raise RuntimeError("sdk unavailable")

    monkeypatch.setattr(provider, "_sdk_route", fail_sdk)

    result = provider.route_with_provider(
        "Tim laptop gaming duoi 800 do",
        job_id="job-test",
    )

    assert result.provider == "deterministic_fallback"
    assert result.output.intent == IntentEnum.SEARCH_DEALS
    assert result.warnings == ["router_sdk_fallback_used:sdk_error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_agents_sdk_providers.py::test_router_provider_defaults_to_deterministic tests/test_agents_sdk_providers.py::test_router_provider_falls_back_when_sdk_raises -q --tb=short
```

Expected: fail because `backend.router.provider` does not exist.

- [ ] **Step 3: Implement `backend/router/provider.py`**

```python
"""Router provider boundary for deterministic and optional Agents SDK paths."""

from __future__ import annotations

from dataclasses import dataclass

from backend.router.deterministic import deterministic_route
from backend.router.schemas import RouterInput, RouterOutput
from backend.shared.config import (
    ENABLE_AGENTS_SDK,
    ENABLE_REAL_MODEL_CALLS,
    MODEL_ID_ROUTER,
)


@dataclass
class RouterProviderResult:
    output: RouterOutput
    provider: str
    warnings: list[str]


def _sdk_route(input_data: RouterInput, *, job_id: str, model_id: str) -> RouterOutput:
    from backend.router.sdk_provider import sdk_route

    return sdk_route(input_data, job_id=job_id, model_id=model_id)


def route_with_provider(message_vi: str, *, job_id: str) -> RouterProviderResult:
    """Route a Vietnamese message using SDK when enabled, otherwise deterministic."""
    if ENABLE_REAL_MODEL_CALLS and ENABLE_AGENTS_SDK and MODEL_ID_ROUTER:
        try:
            output = _sdk_route(
                RouterInput(message_vi=message_vi),
                job_id=job_id,
                model_id=MODEL_ID_ROUTER,
            )
            return RouterProviderResult(
                output=output,
                provider="openai_agents_sdk",
                warnings=[],
            )
        except Exception:
            fallback = deterministic_route(message_vi)
            return RouterProviderResult(
                output=fallback,
                provider="deterministic_fallback",
                warnings=["router_sdk_fallback_used:sdk_error"],
            )

    return RouterProviderResult(
        output=deterministic_route(message_vi),
        provider="deterministic",
        warnings=[],
    )
```

- [ ] **Step 4: Implement `backend/router/sdk_provider.py` with lazy SDK import**

```python
"""OpenAI Agents SDK Router provider.

The `agents` package is imported only inside sdk_route(), so default
mock tests and deterministic runtime do not require the optional extra.
"""

from __future__ import annotations

import json
from typing import Any

from backend.router.schemas import RouterInput, RouterOutput


ROUTER_INSTRUCTIONS = """You are the Router for a Vietnamese-speaking US shopping assistant.

Return a structured RouterOutput only.

Rules:
- Classify the user's Vietnamese message into one allowed intent.
- MVP executable intent is search_deals.
- Use unsupported when the request is not about shopping/product deals.
- Produce a concise English query_en for shopping searches.
- source must be All, Amazon, or BestBuy.
- max_results_per_source must be between 1 and 20.
- Do not call tools. You only classify and normalize the request.
"""


def _run_agent(agent: Any, input_text: str, run_config: Any) -> Any:
    from agents import Runner

    return Runner.run_sync(agent, input_text, run_config=run_config)


def _load_agents_sdk() -> tuple[Any, Any]:
    from agents import Agent, RunConfig

    return Agent, RunConfig


def sdk_route(input_data: RouterInput, *, job_id: str, model_id: str) -> RouterOutput:
    """Run the SDK Router agent and return a validated RouterOutput."""
    Agent, RunConfig = _load_agents_sdk()

    agent = Agent(
        name="Shopping Router",
        instructions=ROUTER_INSTRUCTIONS,
        model=model_id,
        output_type=RouterOutput,
    )
    run_config = RunConfig(
        workflow_name="shopping_assistant_v3_router",
        group_id=job_id,
        trace_metadata={
            "component": "router",
            "run_type": "router",
            "provider": "openai_agents_sdk",
        },
        trace_include_sensitive_data=False,
    )
    input_text = json.dumps(input_data.model_dump(), ensure_ascii=False)
    result = _run_agent(agent, input_text, run_config)
    final_output = result.final_output
    if isinstance(final_output, RouterOutput):
        return final_output
    return RouterOutput.model_validate(final_output)
```

- [ ] **Step 5: Run Router provider tests**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_agents_sdk_providers.py::test_router_provider_defaults_to_deterministic tests/test_agents_sdk_providers.py::test_router_provider_falls_back_when_sdk_raises -q --tb=short
```

Expected: pass without OpenAI calls and without importing `agents` in the default path.

---

### Task 3: Add Synthesizer Provider Boundary And Evidence Validation

**Files:**
- Create: `backend/synthesizer/provider.py`
- Create: `backend/synthesizer/sdk_provider.py`
- Create: `backend/synthesizer/validation.py`
- Modify: `backend/synthesizer/deterministic.py`
- Test: `tests/test_agents_sdk_providers.py`

**Interfaces:**
- Consumes: `SynthesizerInput`, `SynthesizerOutput`, `deterministic_synthesize`.
- Produces: `SynthesizerProviderResult(output: SynthesizerOutput, provider: str, warnings: list[str])`.
- Produces: `synthesize_with_provider(input_data: SynthesizerInput, job_id: str) -> SynthesizerProviderResult`.
- Produces: `validate_synthesizer_output(input_data: SynthesizerInput, output: SynthesizerOutput) -> None`.

- [ ] **Step 1: Add failing Synthesizer provider tests**

Append to `tests/test_agents_sdk_providers.py`:

```python
from backend.synthesizer.schemas import SynthesizerInput, SynthesizerOutput
from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.schemas import ModelBreakdown, PriceEstimateOutput


def _product() -> ProductCandidate:
    return ProductCandidate(
        source="BestBuy",
        title="Test Laptop Pro",
        brand="TestBrand",
        sale_price_usd=799.99,
        url="https://example.com/laptop",
        features="16GB RAM",
    )


def _estimate() -> PriceEstimateOutput:
    return PriceEstimateOutput(
        estimated_value_usd=900.0,
        discount_usd=100.01,
        deal_score="good",
        confidence=None,
        model_breakdown=ModelBreakdown(frontier=900.0, specialist=0.0, neural=0.0),
        warnings=[],
    )


def test_synthesizer_provider_defaults_to_deterministic(monkeypatch) -> None:
    import backend.synthesizer.provider as provider

    monkeypatch.setattr(provider, "ENABLE_REAL_MODEL_CALLS", False)
    monkeypatch.setattr(provider, "ENABLE_AGENTS_SDK", False)

    result = provider.synthesize_with_provider(
        SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=[_product()],
            price_estimates=[_estimate()],
            warnings=[],
        ),
        job_id="job-test",
    )

    assert result.provider == "deterministic"
    assert result.warnings == []
    assert result.output.summary_cards[0].title == "Test Laptop Pro"


def test_synthesizer_provider_falls_back_when_sdk_raises(monkeypatch) -> None:
    import backend.synthesizer.provider as provider

    monkeypatch.setattr(provider, "ENABLE_REAL_MODEL_CALLS", True)
    monkeypatch.setattr(provider, "ENABLE_AGENTS_SDK", True)
    monkeypatch.setattr(provider, "MODEL_ID_SYNTHESIZER", "gpt-test-synth")

    def fail_sdk(*args, **kwargs):
        raise RuntimeError("sdk unavailable")

    monkeypatch.setattr(provider, "_sdk_synthesize", fail_sdk)

    result = provider.synthesize_with_provider(
        SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=[_product()],
            price_estimates=[_estimate()],
            warnings=[],
        ),
        job_id="job-test",
    )

    assert result.provider == "deterministic_fallback"
    assert result.warnings == ["synthesizer_sdk_fallback_used:sdk_error"]
    assert result.output.summary_cards[0].title == "Test Laptop Pro"
```

- [ ] **Step 2: Add failing evidence validation tests**

Append to `tests/test_agents_sdk_providers.py`:

```python
def test_synthesizer_validation_rejects_unknown_url() -> None:
    from backend.synthesizer.validation import validate_synthesizer_output
    from backend.synthesizer.schemas import SummaryCard

    input_data = SynthesizerInput(
        message_vi="Tim laptop",
        intent="search_deals",
        products=[_product()],
        price_estimates=[_estimate()],
        warnings=[],
    )
    output = SynthesizerOutput(
        answer_vi="Xem tai https://fake.example.com",
        summary_cards=[
            SummaryCard(
                source="BestBuy",
                title="Test Laptop Pro",
                sale_price_usd=799.99,
                url="https://fake.example.com",
                highlight_vi="Deal tot.",
            )
        ],
        warnings_vi=[],
    )

    import pytest

    with pytest.raises(ValueError, match="unknown_url"):
        validate_synthesizer_output(input_data, output)
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_agents_sdk_providers.py -q --tb=short
```

Expected: fail because synthesizer provider and validation modules do not exist.

- [ ] **Step 4: Implement `backend/synthesizer/validation.py`**

```python
"""Evidence validation for SDK Synthesizer outputs."""

from __future__ import annotations

import re

from backend.synthesizer.schemas import SynthesizerInput, SynthesizerOutput


_URL_RE = re.compile(r"https?://\S+")


def validate_synthesizer_output(
    input_data: SynthesizerInput,
    output: SynthesizerOutput,
) -> None:
    """Raise ValueError if SDK output includes unsupported evidence.

    This is intentionally small for Phase 5B. It blocks unknown URLs in the
    answer or cards and unknown card identities. Broader hallucination checks
    belong in Phase 7 evaluator work.
    """
    allowed_urls = {p.url for p in input_data.products if p.url}
    allowed_cards = {(p.source, p.title, p.url) for p in input_data.products}

    for url in _URL_RE.findall(output.answer_vi):
        if url.rstrip(".,)") not in allowed_urls:
            raise ValueError("unknown_url")

    for card in output.summary_cards:
        identity = (card.source, card.title, card.url)
        if identity not in allowed_cards:
            raise ValueError("unknown_summary_card")
```

- [ ] **Step 5: Implement `backend/synthesizer/provider.py`**

```python
"""Synthesizer provider boundary for deterministic and optional Agents SDK paths."""

from __future__ import annotations

from dataclasses import dataclass

from backend.shared.config import (
    ENABLE_AGENTS_SDK,
    ENABLE_REAL_MODEL_CALLS,
    MODEL_ID_SYNTHESIZER,
)
from backend.synthesizer.deterministic import deterministic_synthesize
from backend.synthesizer.schemas import SynthesizerInput, SynthesizerOutput
from backend.synthesizer.validation import validate_synthesizer_output


@dataclass
class SynthesizerProviderResult:
    output: SynthesizerOutput
    provider: str
    warnings: list[str]


def _sdk_synthesize(
    input_data: SynthesizerInput,
    *,
    job_id: str,
    model_id: str,
) -> SynthesizerOutput:
    from backend.synthesizer.sdk_provider import sdk_synthesize

    return sdk_synthesize(input_data, job_id=job_id, model_id=model_id)


def synthesize_with_provider(
    input_data: SynthesizerInput,
    *,
    job_id: str,
) -> SynthesizerProviderResult:
    """Synthesize an answer using SDK when enabled, otherwise deterministic."""
    if ENABLE_REAL_MODEL_CALLS and ENABLE_AGENTS_SDK and MODEL_ID_SYNTHESIZER:
        try:
            output = _sdk_synthesize(
                input_data,
                job_id=job_id,
                model_id=MODEL_ID_SYNTHESIZER,
            )
            validate_synthesizer_output(input_data, output)
            return SynthesizerProviderResult(
                output=output,
                provider="openai_agents_sdk",
                warnings=[],
            )
        except Exception:
            fallback_warning = "synthesizer_sdk_fallback_used:sdk_error"
            fallback_input = input_data.model_copy(
                update={"warnings": [*input_data.warnings, fallback_warning]}
            )
            fallback = deterministic_synthesize(fallback_input)
            return SynthesizerProviderResult(
                output=fallback,
                provider="deterministic_fallback",
                warnings=[fallback_warning],
            )

    return SynthesizerProviderResult(
        output=deterministic_synthesize(input_data),
        provider="deterministic",
        warnings=[],
    )
```

- [ ] **Step 6: Implement `backend/synthesizer/sdk_provider.py` with lazy SDK import**

```python
"""OpenAI Agents SDK Synthesizer provider.

The SDK provider receives only structured product and price evidence. It
does not receive search or pricing tools.
"""

from __future__ import annotations

import json
from typing import Any

from backend.synthesizer.schemas import SynthesizerInput, SynthesizerOutput


SYNTHESIZER_INSTRUCTIONS = """You are the Vietnamese Synthesizer for a US shopping assistant.

Return a structured SynthesizerOutput only.

Rules:
- Write answer_vi in Vietnamese.
- Preserve product names in English when clearer.
- Preserve prices in USD.
- Use only product and price evidence from the input JSON.
- Do not invent URLs, prices, specs, discounts, sources, or product names.
- summary_cards must correspond only to input products.
- Mention warnings when relevant.
- Do not call tools.
"""


def _run_agent(agent: Any, input_text: str, run_config: Any) -> Any:
    from agents import Runner

    return Runner.run_sync(agent, input_text, run_config=run_config)


def _load_agents_sdk() -> tuple[Any, Any]:
    from agents import Agent, RunConfig

    return Agent, RunConfig


def sdk_synthesize(
    input_data: SynthesizerInput,
    *,
    job_id: str,
    model_id: str,
) -> SynthesizerOutput:
    """Run the SDK Synthesizer agent and return a validated Pydantic output."""
    Agent, RunConfig = _load_agents_sdk()

    agent = Agent(
        name="Shopping Synthesizer",
        instructions=SYNTHESIZER_INSTRUCTIONS,
        model=model_id,
        output_type=SynthesizerOutput,
    )
    run_config = RunConfig(
        workflow_name="shopping_assistant_v3_synthesizer",
        group_id=job_id,
        trace_metadata={
            "component": "synthesizer",
            "run_type": "synthesizer",
            "provider": "openai_agents_sdk",
        },
        trace_include_sensitive_data=False,
    )
    input_text = json.dumps(input_data.model_dump(), ensure_ascii=False)
    result = _run_agent(agent, input_text, run_config)
    final_output = result.final_output
    if isinstance(final_output, SynthesizerOutput):
        return final_output
    return SynthesizerOutput.model_validate(final_output)
```

- [ ] **Step 7: Add warning translations**

Modify `_WARNING_TRANSLATIONS` in `backend/synthesizer/deterministic.py` by adding:

```python
    ("router_sdk_fallback_used", "Router dung OpenAI Agents SDK khong thanh cong, da fallback sang logic mac dinh."),
    ("synthesizer_sdk_fallback_used", "Synthesizer dung OpenAI Agents SDK khong thanh cong, da fallback sang logic mac dinh."),
```

- [ ] **Step 8: Run Synthesizer provider tests**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_agents_sdk_providers.py -q --tb=short
```

Expected: pass without OpenAI calls.

---

### Task 4: Integrate Providers Into Worker

**Files:**
- Modify: `backend/worker.py`
- Test: `tests/test_worker.py`

**Interfaces:**
- Consumes: `route_with_provider(message_vi, job_id)`.
- Consumes: `synthesize_with_provider(input_data, job_id)`.
- Produces: result warnings containing provider fallback warnings.
- Produces: `agent_runs` summaries that include provider identity.
- Produces: when SDK fallback occurs, a failed SDK attempt row and a completed deterministic fallback row.

- [ ] **Step 1: Add failing worker tests for Router SDK fallback**

Append to `tests/test_worker.py`:

```python
def test_worker_router_sdk_fallback_warning(monkeypatch, temp_db) -> None:
    import json

    from backend.worker import process_job
    from backend.database.repository import create_job, get_job_by_id
    from backend.database.session import get_session_factory
    from backend.database.schema import AgentRun
    from backend.router.provider import RouterProviderResult
    from backend.router.schemas import IntentEnum, RouterOutput

    session = get_session_factory()()
    job = create_job(
        session,
        message="Tim laptop gaming duoi 800 do",
        conversation_id=None,
        source="All",
        max_results_per_source=2,
    )
    job_id = job.id
    session.commit()
    session.close()

    def fake_route(message_vi: str, *, job_id: str):
        return RouterProviderResult(
            output=RouterOutput(
                intent=IntentEnum.SEARCH_DEALS,
                query_en="gaming laptop under 800 dollars",
                source="All",
                max_results_per_source=2,
                confidence=0.7,
                needs_tool=True,
            ),
            provider="deterministic_fallback",
            warnings=["router_sdk_fallback_used:sdk_error"],
        )

    monkeypatch.setattr("backend.worker.route_with_provider", fake_route, raising=False)

    process_job(job_id)

    session = get_session_factory()()
    saved = get_job_by_id(session, job_id)
    result = json.loads(saved.result_payload)
    router_runs = (
        session.query(AgentRun)
        .filter(AgentRun.job_id == job_id, AgentRun.component == "router")
        .all()
    )
    session.close()

    assert "router_sdk_fallback_used:sdk_error" in result["warnings"]
    assert any(
        r.status == "failed" and r.model_provider == "openai_agents_sdk"
        for r in router_runs
    )
    assert any(
        r.status == "completed" and "provider=deterministic_fallback" in (r.output_summary or "")
        for r in router_runs
    )
```

- [ ] **Step 2: Add failing worker tests for Synthesizer SDK fallback**

Append to `tests/test_worker.py`:

```python
def test_worker_synthesizer_sdk_fallback_warning(monkeypatch, temp_db) -> None:
    import json

    from backend.worker import process_job
    from backend.database.repository import create_job, get_job_by_id
    from backend.database.session import get_session_factory
    from backend.database.schema import AgentRun
    from backend.synthesizer.provider import SynthesizerProviderResult
    from backend.synthesizer.deterministic import deterministic_synthesize

    session = get_session_factory()()
    job = create_job(
        session,
        message="Tim laptop gaming duoi 800 do",
        conversation_id=None,
        source="All",
        max_results_per_source=2,
    )
    job_id = job.id
    session.commit()
    session.close()

    def fake_synthesize(input_data, *, job_id: str):
        return SynthesizerProviderResult(
            output=deterministic_synthesize(input_data),
            provider="deterministic_fallback",
            warnings=["synthesizer_sdk_fallback_used:sdk_error"],
        )

    monkeypatch.setattr("backend.worker.synthesize_with_provider", fake_synthesize, raising=False)

    process_job(job_id)

    session = get_session_factory()()
    saved = get_job_by_id(session, job_id)
    result = json.loads(saved.result_payload)
    synth_runs = (
        session.query(AgentRun)
        .filter(AgentRun.job_id == job_id, AgentRun.component == "synthesizer")
        .all()
    )
    session.close()

    assert "synthesizer_sdk_fallback_used:sdk_error" in result["warnings"]
    assert any(
        r.status == "failed" and r.model_provider == "openai_agents_sdk"
        for r in synth_runs
    )
    assert any(
        r.status == "completed" and "provider=deterministic_fallback" in (r.output_summary or "")
        for r in synth_runs
    )
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_worker.py::test_worker_router_sdk_fallback_warning tests/test_worker.py::test_worker_synthesizer_sdk_fallback_warning -q --tb=short
```

Expected: fail because worker still calls deterministic functions directly.

- [ ] **Step 4: Import provider functions at module level**

Add near existing imports in `backend/worker.py`:

```python
from backend.router.provider import route_with_provider
from backend.shared.config import MODEL_ID_ROUTER, MODEL_ID_SYNTHESIZER
from backend.synthesizer.provider import synthesize_with_provider
```

- [ ] **Step 5: Replace direct Router call**

Replace:

```python
from backend.router.deterministic import deterministic_route

route_output = deterministic_route(message)
```

with:

```python
route_result = route_with_provider(message, job_id=job_id)
route_output = route_result.output
router_warnings = list(route_result.warnings)
```

- [ ] **Step 6: Include Router provider in audit summaries**

Update Router audit `output_summary` to include provider:

```python
output_summary=(
    f"provider={route_result.provider}, "
    f"intent={route_output.intent.value}, "
    f"query_en={route_output.query_en[:100]}, "
    f"confidence={route_output.confidence}"
)
```

Also update `_tool_timings[-1]["output_summary"]` for router to include `provider=...`.

- [ ] **Step 7: Create failed SDK Router audit row when fallback occurs**

After the Router `update_agent_run(...)` completed fallback row, add:

```python
if route_result.provider == "deterministic_fallback":
    sdk_router_run = create_agent_run(
        session,
        job_id=job_id,
        component="router",
        run_type="router",
        status="started",
        model_provider="openai_agents_sdk",
        model_name=MODEL_ID_ROUTER or None,
        input_summary=f"message_vi={message[:200]}",
    )
    update_agent_run(
        session,
        sdk_router_run,
        status="failed",
        ended_at=datetime.datetime.now(datetime.timezone.utc),
        error_message="Router SDK provider failed; deterministic fallback used.",
    )
    _tool_timings.append({
        "component": "router",
        "run_type": "router",
        "model_provider": "openai_agents_sdk",
        "model_name": MODEL_ID_ROUTER or "",
        "input_summary": f"message_vi={message[:200]}",
        "status": "failed",
        "error_message": "Router SDK provider failed; deterministic fallback used.",
        "t0": time.monotonic(),
    })
```

- [ ] **Step 8: Include Router warnings in unsupported path**

In unsupported path, change `warnings=[]` in `SynthesizerInput` to:

```python
warnings=router_warnings
```

and change result warnings from:

```python
"warnings": [],
```

to:

```python
"warnings": router_warnings,
```

- [ ] **Step 9: Include Router warnings in supported path**

Change:

```python
all_warnings: list[str] = list(search_output.warnings)
```

to:

```python
all_warnings: list[str] = list(router_warnings) + list(search_output.warnings)
```

- [ ] **Step 10: Replace direct Synthesizer call**

Replace:

```python
synth_output = deterministic_synthesize(synth_input)
```

with:

```python
synth_result = synthesize_with_provider(synth_input, job_id=job_id)
synth_output = synth_result.output
all_warnings.extend(synth_result.warnings)
```

Apply the same pattern in the unsupported path, using a local `unsupported_warnings` list:

```python
synth_result = synthesize_with_provider(synth_input, job_id=job_id)
synth_output = synth_result.output
unsupported_warnings = router_warnings + synth_result.warnings
```

- [ ] **Step 11: Include Synthesizer provider in audit summaries**

Update Synthesizer audit `output_summary` in both supported and unsupported paths:

```python
output_summary=(
    f"provider={synth_result.provider}, "
    f"answer_vi={synth_output.answer_vi[:180]}"
)
```

- [ ] **Step 12: Create failed SDK Synthesizer audit row when fallback occurs**

After the Synthesizer `update_agent_run(...)` completed fallback row, add this in both supported and unsupported paths:

```python
if synth_result.provider == "deterministic_fallback":
    sdk_synth_run = create_agent_run(
        session,
        job_id=job_id,
        component="synthesizer",
        run_type="synthesizer",
        status="started",
        model_provider="openai_agents_sdk",
        model_name=MODEL_ID_SYNTHESIZER or None,
        input_summary=(
            f"intent={route_output.intent.value}, "
            f"products={len(synth_input.products)}, "
            f"warnings={len(synth_input.warnings)}"
        ),
    )
    update_agent_run(
        session,
        sdk_synth_run,
        status="failed",
        ended_at=datetime.datetime.now(datetime.timezone.utc),
        error_message="Synthesizer SDK provider failed; deterministic fallback used.",
    )
```

- [ ] **Step 13: Preserve provider metadata in failure rollback**

Update `_save_pipeline_failure()` so timing entries can preserve provider metadata:

```python
run = create_agent_run(
    session,
    job_id=job_id,
    component=component,
    run_type=run_type,
    status="completed" if was_completed else "failed",
    model_provider=str(timing.get("model_provider") or "") or None,
    model_name=str(timing.get("model_name") or "") or None,
    input_summary=input_summary[:500],
)
```

For failed timing entries, update the error message from:

```python
error_message=f"{component} failed.",
```

to:

```python
error_message=str(timing.get("error_message") or f"{component} failed."),
```

- [ ] **Step 14: Run worker fallback tests**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_worker.py::test_worker_router_sdk_fallback_warning tests/test_worker.py::test_worker_synthesizer_sdk_fallback_warning -q --tb=short
```

Expected: pass.

---

### Task 5: Mock-Only SDK Provider Unit Tests

**Files:**
- Modify: `tests/test_agents_sdk_providers.py`

**Interfaces:**
- Consumes: `sdk_route`, `sdk_synthesize`, `_run_agent`.
- Produces: tests proving SDK provider builds safe `RunConfig` without calling OpenAI.

- [ ] **Step 1: Add fake SDK result helper**

Append to `tests/test_agents_sdk_providers.py`:

```python
class _FakeResult:
    def __init__(self, final_output):
        self.final_output = final_output


class _FakeAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeRunConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
```

- [ ] **Step 2: Add Router SDK safe RunConfig test**

Append:

```python
def test_sdk_router_uses_safe_run_config(monkeypatch) -> None:
    import backend.router.sdk_provider as sdk_provider

    captured = {}

    def fake_run(agent, input_text, run_config):
        captured["agent"] = agent
        captured["input_text"] = input_text
        captured["run_config"] = run_config
        return _FakeResult(
            RouterOutput(
                intent=IntentEnum.SEARCH_DEALS,
                query_en="gaming laptop",
                source="All",
                max_results_per_source=5,
                confidence=0.9,
                needs_tool=True,
            )
        )

    monkeypatch.setattr(sdk_provider, "_run_agent", fake_run)
    monkeypatch.setattr(
        sdk_provider,
        "_load_agents_sdk",
        lambda: (_FakeAgent, _FakeRunConfig),
    )

    output = sdk_provider.sdk_route(
        __import__("backend.router.schemas", fromlist=["RouterInput"]).RouterInput(
            message_vi="Tim laptop gaming"
        ),
        job_id="job-123",
        model_id="gpt-test-router",
    )

    assert output.query_en == "gaming laptop"
    run_config = captured["run_config"]
    assert run_config.group_id == "job-123"
    assert run_config.workflow_name == "shopping_assistant_v3_router"
    assert run_config.trace_include_sensitive_data is False
    assert run_config.trace_metadata["component"] == "router"
```

- [ ] **Step 3: Add Synthesizer SDK safe RunConfig test**

Append:

```python
def test_sdk_synthesizer_uses_safe_run_config(monkeypatch) -> None:
    import backend.synthesizer.sdk_provider as sdk_provider

    captured = {}

    def fake_run(agent, input_text, run_config):
        captured["agent"] = agent
        captured["input_text"] = input_text
        captured["run_config"] = run_config
        return _FakeResult(
            SynthesizerOutput(
                answer_vi="Minh tim duoc san pham phu hop.",
                summary_cards=[],
                warnings_vi=[],
            )
        )

    monkeypatch.setattr(sdk_provider, "_run_agent", fake_run)
    monkeypatch.setattr(
        sdk_provider,
        "_load_agents_sdk",
        lambda: (_FakeAgent, _FakeRunConfig),
    )

    output = sdk_provider.sdk_synthesize(
        SynthesizerInput(
            message_vi="Tim laptop",
            intent="search_deals",
            products=[],
            price_estimates=[],
            warnings=[],
        ),
        job_id="job-123",
        model_id="gpt-test-synth",
    )

    assert "san pham" in output.answer_vi
    run_config = captured["run_config"]
    assert run_config.group_id == "job-123"
    assert run_config.workflow_name == "shopping_assistant_v3_synthesizer"
    assert run_config.trace_include_sensitive_data is False
    assert run_config.trace_metadata["component"] == "synthesizer"
```

- [ ] **Step 4: Run mock-only SDK provider tests**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_agents_sdk_providers.py -q --tb=short
```

Expected: pass without real OpenAI calls and without `openai-agents` installed in the default environment.

---

### Task 6: Add Opt-In Real SDK Smoke Tests

**Files:**
- Create: `tests/test_real_agents_sdk.py`

**Interfaces:**
- Consumes: `sdk_route`, `sdk_synthesize`.
- Produces: skipped-by-default smoke tests for real Agents SDK path.

- [ ] **Step 1: Create `tests/test_real_agents_sdk.py`**

```python
"""Opt-in OpenAI Agents SDK smoke tests.

Skipped by default. These tests may call OpenAI and require:
  - uv sync --extra agents
  - ENABLE_REAL_MODEL_CALLS=true
  - ENABLE_AGENTS_SDK=true
  - OPENAI_API_KEY set in environment
  - MODEL_ID_ROUTER and MODEL_ID_SYNTHESIZER set
"""

from __future__ import annotations

import os

import pytest

from backend.router.schemas import IntentEnum, RouterInput
from backend.synthesizer.schemas import SynthesizerInput
from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.schemas import ModelBreakdown, PriceEstimateOutput


pytestmark = pytest.mark.skipif(
    not (
        os.getenv("ENABLE_REAL_MODEL_CALLS") == "true"
        and os.getenv("ENABLE_AGENTS_SDK") == "true"
        and os.getenv("OPENAI_API_KEY")
    ),
    reason="Requires ENABLE_REAL_MODEL_CALLS=true, ENABLE_AGENTS_SDK=true, and OPENAI_API_KEY",
)


def test_real_sdk_router_smoke() -> None:
    model_id = os.getenv("MODEL_ID_ROUTER")
    if not model_id:
        pytest.skip("MODEL_ID_ROUTER is not set")

    pytest.importorskip("agents", reason="Requires uv sync --extra agents")

    from backend.router.sdk_provider import sdk_route

    output = sdk_route(
        RouterInput(message_vi="Tim laptop gaming duoi 800 do"),
        job_id="smoke-router",
        model_id=model_id,
    )

    assert output.intent in IntentEnum
    assert 0.0 <= output.confidence <= 1.0


def test_real_sdk_synthesizer_smoke() -> None:
    model_id = os.getenv("MODEL_ID_SYNTHESIZER")
    if not model_id:
        pytest.skip("MODEL_ID_SYNTHESIZER is not set")

    pytest.importorskip("agents", reason="Requires uv sync --extra agents")

    from backend.synthesizer.sdk_provider import sdk_synthesize

    product = ProductCandidate(
        source="BestBuy",
        title="Test Laptop Pro",
        brand="TestBrand",
        sale_price_usd=799.99,
        url="https://example.com/laptop",
        features="16GB RAM, RTX 4060",
    )
    estimate = PriceEstimateOutput(
        estimated_value_usd=900.0,
        discount_usd=100.01,
        deal_score="good",
        confidence=None,
        model_breakdown=ModelBreakdown(frontier=900.0, specialist=0.0, neural=0.0),
        warnings=[],
    )

    output = sdk_synthesize(
        SynthesizerInput(
            message_vi="Tim laptop gaming duoi 800 do",
            intent="search_deals",
            products=[product],
            price_estimates=[estimate],
            warnings=[],
        ),
        job_id="smoke-synthesizer",
        model_id=model_id,
    )

    assert output.answer_vi
```

- [ ] **Step 2: Verify smoke tests skip by default**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_real_agents_sdk.py -q --tb=short
```

Expected: skipped, no OpenAI call.

- [ ] **Step 3: Document optional real smoke command**

Only after the user has local env and wants paid model calls, run:

```bash
cd shopping_assistant_v3 && uv sync --extra agents
cd shopping_assistant_v3 && uv run pytest tests/test_real_agents_sdk.py -q --tb=short
```

Expected when env is configured: 2 passed. If model/API errors occur, record bounded error summaries in the implementation report without printing secrets.

---

### Task 7: Focused And Broad Verification

**Files:** None.

**Interfaces:**
- Consumes: all Phase 5B code and tests.
- Produces: verification evidence for implementation report.

- [ ] **Step 1: Run provider tests**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_agents_sdk_providers.py -q --tb=short
```

Expected: pass.

- [ ] **Step 2: Run Router/Synthesizer deterministic tests**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_router.py tests/test_synthesizer.py -q --tb=short
```

Expected: pass.

- [ ] **Step 3: Run worker tests**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_worker.py -q --tb=short
```

Expected: pass.

- [ ] **Step 4: Run API tests only if preflight is healthy**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/test_api.py -q --tb=short
```

Expected outside the known Codex sandbox issue: pass. If Codex sandbox hangs on minimal `TestClient`, do not treat that as Phase 5B app failure; document it and run the broad suite excluding API tests.

- [ ] **Step 5: Run broad mock-only suite**

Run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/ -q --tb=short
```

Expected outside the known Codex sandbox issue: pass with real-mode smoke tests skipped.

If API tests hang only because of the known sandbox issue, run:

```bash
cd shopping_assistant_v3 && uv run pytest tests/ --ignore=tests/test_api.py -q --tb=short
```

Expected: pass with real-mode smoke tests skipped. Record both the skipped API limitation and the focused API validation evidence in the report.

- [ ] **Step 6: Confirm default tests did not import heavy optional modules**

Run:

```bash
cd shopping_assistant_v3 && uv run python -c "import sys
bad = [m for m in ('agents', 'openai', 'modal') if m in sys.modules]
assert bad == [], bad
print('OK')"
```

Expected immediately after a fresh Python process: `OK`.

---

### Task 8: Implementation Report

**Files:**
- Create: `reports/phase_5b_agents_sdk_router_synthesizer_report.md`

**Interfaces:**
- Consumes: `reports/TEMPLATE_IMPLEMENTATION_REPORT.md`.
- Produces: reviewer handoff evidence.

- [ ] **Step 1: Write report with this title**

```markdown
# Phase 5B: Optional OpenAI Agents SDK Router/Synthesizer Providers — Implementation Report
```

- [ ] **Step 2: Include required summary facts**

Report must state:

```text
Behavior: optional real SDK provider, deterministic default/fallback.
Dependency: openai-agents is optional extra [agents], not base dependency.
SDK tools exposed: none.
Trace strategy: OpenAI dashboard trace through RunConfig, no custom TracingProcessor.
Sensitive trace policy: trace_include_sensitive_data=False.
Fallback warnings: router_sdk_fallback_used:sdk_error, synthesizer_sdk_fallback_used:sdk_error.
Default tests: mock-only, no OpenAI, no live scraping, no secrets.
Real smoke: skipped by default; report whether it was run.
```

- [ ] **Step 3: Include commands and results**

Include exact output summaries for:

```text
git status --short
codegraph status shopping_assistant_v3
AnyIO threadpool preflight
minimal FastAPI TestClient preflight
uv lock
uv run pytest tests/test_agents_sdk_providers.py -q --tb=short
uv run pytest tests/test_router.py tests/test_synthesizer.py -q --tb=short
uv run pytest tests/test_worker.py -q --tb=short
uv run pytest tests/test_api.py -q --tb=short, or documented sandbox limitation
uv run pytest tests/ -q --tb=short, or documented --ignore=tests/test_api.py fallback
uv run pytest tests/test_real_agents_sdk.py -q --tb=short
```

- [ ] **Step 4: Include safety checklist**

Report must explicitly check:

```text
No secrets read or printed.
No default OpenAI calls.
No default live Amazon/BestBuy scraping.
No AWS/Terraform/deploy commands.
No segment4 or shopping_assistant_v2 changes.
OpenAI trace metadata contains job_id via group_id and safe metadata only.
SDK failure path falls back to deterministic provider.
```

---

## Self-Review Checklist

- Spec coverage: Phase 5B adds optional SDK Router/Synthesizer providers, tracing config, fallback, tests, smoke tests, and report.
- Scope check: no frontend, no custom tracing processor, no trace API endpoint, no SDK-owned search/pricing tool loop.
- Dependency check: `openai-agents>=0.18.3` is optional `[agents]`, not base.
- Safety check: default tests remain mock-only and do not require API keys.
- Evidence check: Synthesizer SDK output is bounded by simple validation and deterministic fallback.
- Report check: implementation report must document API test harness preflight and real smoke status.
