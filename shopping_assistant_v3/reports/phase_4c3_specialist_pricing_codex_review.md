# Codex Review: Phase 4C.3 Specialist Price Estimator Extraction

Decision: approved
Reviewer: Codex
Date: 2026-07-21
Implementer report: `shopping_assistant_v3/reports/phase_4c3_specialist_pricing_report.md`

## Tóm Tắt

Phase 4C.3 is approved. The implementation stays inside the approved Specialist
pricing boundary: Modal is optional and lazy-loaded, default tests remain
mock-only, real Specialist smoke tests are opt-in and skipped by default, and
`segment4/` remains untouched.

The real pricing path now has the complete Phase 4C model boundary:

```text
All three available -> 0.8*frontier + 0.1*specialist + 0.1*neural
Partial availability -> frontier > specialist > neural > 5% fallback
```

OpenAI Agents SDK documentation updates for Phase 5 were also kept aligned with
the approved hybrid controlled direction, but no Phase 5 runtime code was
implemented.

## Findings

Không có blocker hoặc major findings.

Minor doc drift found and fixed by Codex during review:

- `backend/tools/price_estimator/specialist/__init__.py` still said Specialist
  was deferred to Phase 4C.3.
- `backend/tools/price_estimator/tool.py` still described the real path as
  Phase 4C.2 / Frontier-Neural only.
- `.env.example` did not yet include the approved Phase 5 `ENABLE_AGENTS_SDK`
  mock-safe flag and still described Router/Synthesizer model config as
  LiteLLM-specific.

## Verification

Commands run:

```bash
git status --short
```

Result: Phase 4C.3 files are modified/untracked. Existing untracked
`shopping_assistant_v2/README_*.md` files remain unrelated and were not
modified.

```bash
codegraph status shopping_assistant_v3
```

Result: index is up to date with `44 files`, `665 nodes`, `1,453 edges`.

```text
CodeGraph MCP query:
How does estimate_price_real use Frontier Specialist Neural adapters and
assemble PriceEstimateOutput in Phase 4C.3?
```

Result: verified `estimate_price_real()` calls Frontier, Specialist, and Neural
adapters and `_assemble_output()` applies the full/partial assembly policy.

```bash
uv run pytest tests/test_real_pricing.py tests/test_real_pricing_specialist.py -q --tb=short
```

Result: `72 passed, 1 warning in 7.30s`.

```bash
uv run pytest tests/test_real_pricing_specialist_smoke.py -q --tb=short
```

Result: `2 skipped, 1 warning in 0.01s`.

```bash
uv run pytest tests/ -q --tb=short
```

Result: `171 passed, 18 skipped, 1 warning in 29.53s`.

```bash
rg -n "^\s*(from\s+segment4(\.|\s+import\b)|import\s+segment4\b)" shopping_assistant_v3/backend shopping_assistant_v3/tests
```

Result: no direct runtime import statements from `segment4`.

```bash
git diff --name-only -- segment4/ shopping_assistant_v2/
```

Result: no tracked diffs under `segment4/` or `shopping_assistant_v2/`.

```bash
rg -n "sk-|api_key\s*=|token\s*=|secret\s*=|credentials\s*=" shopping_assistant_v3/backend/tools/price_estimator/specialist shopping_assistant_v3/tests/test_real_pricing_specialist.py shopping_assistant_v3/tests/test_real_pricing_specialist_smoke.py shopping_assistant_v3/.env.example
```

Result: no hardcoded secret/key patterns.

## Scope Check

Scope stayed within approved Phase 4C.3 plus Codex-owned documentation
finalization:

- added lazy Modal Specialist adapter;
- added empty Specialist service/class config defaults;
- added optional `specialist` dependency group;
- updated real pricing assembly to support full three-model ensemble and
  deterministic partial fallback priority;
- added mock-only Specialist tests and opt-in Specialist smoke tests;
- kept default verification mock-only;
- kept `segment4/` and `shopping_assistant_v2/` unchanged;
- updated current docs/status/user reports after approval.

No live Modal, OpenAI, Amazon, BestBuy, AWS, Terraform, or deploy commands were
run.

## Safety And Quality Check

Security: no secrets were read or printed. Default tests did not call Modal,
OpenAI, live Amazon/BestBuy scraping, AWS, Terraform, or deployment commands.
Specialist config defaults are empty.

Data safety: Modal/config/import failures return bounded error metadata through
`SpecialistEstimateResult`. Real estimator warnings use explicit
`key:value` grammar and no legacy `specialist_unavailable:deferred_to_4c3`
warning remains.

Reliability: missing Specialist config, missing Modal dependency, Modal connect
error, Modal inference error, partial model availability, and full fallback all
produce valid `PriceEstimateOutput` values. Full ensemble success has no
partial warning; partial cases have exactly one `ensemble_partial:*` warning.

Performance: default mock path does not import Modal, ChromaDB,
SentenceTransformer, OpenAI, Torch, sklearn, or numpy. In opt-in real mode the
real estimator attempts all configured adapters to allow the full ensemble when
available; this cost is documented and gated by `ENABLE_REAL_MODEL_CALLS=true`.

Tests: focused and full default suites pass with mocks/fixtures only.

## Thay Đổi Bắt Buộc

Không có required changes.

## Approval Notes

Phase 4C.3 is approved. `PROJECT_STATUS.md`, `gameplan.md`,
`guides/4_search_and_pricing_tools.md`, `reports/user_reports/README.md`, and
`reports/user_reports/phase_4c3_user_report.md` now record Specialist pricing
as the latest approved milestone. The next implementation milestone is Phase 5:
Router And Synthesizer, using the approved hybrid controlled OpenAI Agents SDK
direction only after separate brainstorming and explicit approval.
