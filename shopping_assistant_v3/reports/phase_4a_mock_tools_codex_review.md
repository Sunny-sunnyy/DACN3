# Codex Review: Phase 4A Mock Search/Pricing Tools

Decision: approved
Reviewer: Codex
Date: 2026-07-19
Implementer report: `shopping_assistant_v3/reports/phase_4a_mock_tools_report.md`

## Tóm Tắt

Phase 4A is approved after two correction rounds. Mock tool schemas, JSON
fixtures, repository helpers, worker integration, safe real-mode failure
behavior, and audit rows for worker/tool success and failure paths are present.
The full mock-only suite passes locally.

Historical findings and re-review notes are preserved below for traceability.
They are superseded by the final approval section.

## Final Re-review 2026-07-19

Không có blocker hoặc major findings.

The latest fix preserves audit truth when a later tool fails after an earlier
tool has already completed. Direct probes now show:

```text
success:
[('worker', 'worker', 'completed', '3 products', None),
 ('deal_search_tool', 'tool', 'completed', '3 products, 0 warnings', None),
 ('price_estimator_tool', 'tool', 'completed', 'estimated=949.99, discount=200.0, score=hot', None),
 ('price_estimator_tool', 'tool', 'completed', 'estimated=307.99, discount=28.0, score=ok', None),
 ('price_estimator_tool', 'tool', 'completed', 'estimated=879.99, discount=180.0, score=good', None)]

deal_search failure:
[('deal_search_tool', 'tool', 'failed', None, 'deal_search_tool failed.'),
 ('worker', 'worker', 'failed', None, 'Worker failed. Try again later.')]

price_estimator failure after successful search:
[('deal_search_tool', 'tool', 'completed', '3 products, 0 warnings', None),
 ('price_estimator_tool', 'tool', 'failed', None, 'price_estimator_tool failed.'),
 ('worker', 'worker', 'failed', None, 'Worker failed. Try again later.')]
```

Additional documentation correction by Codex: source-of-truth examples in
`guides/architecture.md`, `guides/agent_architecture.md`,
`guides/2_backend_api_and_database.md`,
`guides/4_search_and_pricing_tools.md`, and
`guides/5_router_and_synthesizer.md` now use the approved
`max_results_per_source: 5` contract.

`PROJECT_STATUS.md` was updated to mark Phase 4A approved and Phase 4B as the
next allowed implementation milestone. The approved commit is still pending
because no git actions were requested.

## Verification

Commands run:

```bash
git status --short
codegraph status shopping_assistant_v3
```

Result: worktree contains the reviewed Phase 4A changes plus separate governance
doc changes. CodeGraph index is up to date at `25 files`, `334 nodes`, `711
edges`.

```bash
cd shopping_assistant_v3 && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_worker.py -v
```

Result: `20 passed, 1 warning in 2.83s`.

```bash
cd shopping_assistant_v3 && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v
```

Result: `81 passed, 1 warning in 9.15s`.

```bash
cd shopping_assistant_v3 && rg "segment4" backend tests
```

Result: only tool README references, no runtime/test imports.

```bash
cd shopping_assistant_v3 && rg "openai|litellm|curl_cffi|modal|brave" tests
```

Result: no matches.

```bash
rg -n '"max_results_per_source": 6|default max_results.*6|max_results default 6' \
  shopping_assistant_v3/guides shopping_assistant_v3/reports/PROJECT_STATUS.md
```

Result: no matches in current source-of-truth guides/status.

Generated `backend/database/app.db` from verification probes was removed after
review.

## Scope Check

Runtime scope stayed within Phase 4A: mock search/pricing tools, fixtures,
repository helpers, worker pipeline integration, and audit rows. No
`segment4/` or `shopping_assistant_v2/` runtime reuse/import was introduced.

The previously modified workflow docs
`CODEX_REVIEWER_WORKFLOW.md` and `DEEPSEEK_IMPLEMENTER_WORKFLOW.md` are
separate approved governance edits from the earlier CodeGraph discussion and
should be committed with the approved unit only if the user wants that same
commit to include governance updates.

## Safety And Quality Check

Security: no secrets were read or printed. Verification remained mock-only and
did not call paid APIs, AWS, deployment commands, or live Amazon/BestBuy
scraping.

Data safety: user/API-visible worker errors remain sanitized. Internal audit
rows preserve enough status/output/error summary for local debugging without
leaking raw exceptions to API clients.

Reliability: success, search failure, and later pricing failure paths now
persist truthful worker/tool `agent_runs`. Phase 3 idempotency and stale-running
recovery tests still pass.

Performance: fixture-based mock tools are appropriate for Phase 4A. JSON fixture
loading remains a local-MVP choice and is not a blocker.

## Approval Notes

Phase 4A is approved. The project may move to Phase 4B planning after the user
explicitly confirms that phase and scope. Do not start live Amazon/BestBuy
extraction, real scraping, model calls, git stage/commit/push, AWS, or deploy
actions without explicit user approval.

## Initial Findings (Superseded)

- major: `shopping_assistant_v3/backend/worker.py:274` - Successful jobs no
  longer create a completed `worker` agent_run. Phase 3 approved status says the
  worker has `agent_runs` audit rows, and the Phase 4A report claims Phase 3
  behavior was preserved. A direct probe after a completed job returned only
  `deal_search_tool` and `price_estimator_tool` rows, with no completed
  `worker` run. Restore a worker-level audit run around the full pipeline, or
  get an explicit approved deviation before removing that Phase 3 behavior.

- major: `shopping_assistant_v3/backend/worker.py:105` and
  `shopping_assistant_v3/backend/worker.py:170` - Failed tool invocations are
  not persisted as failed tool `agent_runs`. `_run_deal_search()` and
  `_run_price_estimator()` create a tool run, call `session.rollback()` on
  failure, then try to update the rolled-back run. A direct failure probe showed
  only a failed `worker` row remained; no failed `deal_search_tool` or
  `price_estimator_tool` row survived. This violates the Phase 4A requirement
  that every tool invocation is audited. Persist failed tool runs durably, for
  example by recording failure in a fresh audit transaction/session or another
  rollback-safe pattern.

- minor: `shopping_assistant_v3/reports/phase_4a_mock_tools_report.md` -
  CodeGraph verification is stale. The report says `16 files, 206 nodes, 400
  edges`, but after syncing changed files the current status is `25 files, 331
  nodes, 701 edges`. Update the report with the final CodeGraph status and note
  that Codex had to run `codegraph sync shopping_assistant_v3`.

- minor: `shopping_assistant_v3/backend/tools/deal_search/README.md` and
  `shopping_assistant_v3/backend/tools/price_estimator/README.md` - These
  tracked READMEs still say Phase 4A has no code. They are now stale because
  Phase 4A implements mock contracts and fixtures in these directories. Update
  the READMEs or mention why they intentionally remain skeleton notes.

## Verification

Commands run:

```bash
git status --short
```

Result: Phase 4A runtime/tests/reports are modified or untracked. Two unrelated
untracked files remain under `shopping_assistant_v2/`.

```bash
codegraph status shopping_assistant_v3
```

Initial result: index had pending changes, `Added: 9 files`, `Modified: 5
files`; report's CodeGraph status was stale.

```bash
codegraph sync shopping_assistant_v3
codegraph status shopping_assistant_v3
```

Result after sync: index up to date, `25 files`, `331 nodes`, `701 edges`.

```bash
cd shopping_assistant_v3 && uv run pytest tests/ -v
```

Result: `80 passed, 1 warning in 9.72s`.

```bash
cd shopping_assistant_v3 && rg "segment4" backend tests
```

Result: only tracked tool README references, no runtime/test imports.

```bash
cd shopping_assistant_v3 && rg "openai|litellm|curl_cffi|modal|brave" tests
```

Result: no matches.

Additional audit probes:

```text
completed job agent_runs:
[('deal_search_tool', 'tool', 'completed'),
 ('price_estimator_tool', 'tool', 'completed'),
 ('price_estimator_tool', 'tool', 'completed'),
 ('price_estimator_tool', 'tool', 'completed')]
```

No completed `worker` row was present.

```text
deal_search failure agent_runs:
[('worker', 'worker', 'failed', 'Worker failed. Try again later.')]

price_estimator failure agent_runs:
[('worker', 'worker', 'failed', 'Worker failed. Try again later.')]
```

No failed tool rows were persisted.

## Scope Check

Runtime scope stayed within Phase 4A: mock tool contracts, fixtures, repository
helpers, and worker integration. I did not see `segment4/` or
`shopping_assistant_v2/` changes in the reviewed Phase 4A implementation.

The previously modified workflow docs
`CODEX_REVIEWER_WORKFLOW.md` and `DEEPSEEK_IMPLEMENTER_WORKFLOW.md` are
separate governance edits from the earlier CodeGraph discussion and should be
handled separately from Phase 4A unless user includes them in the approved unit.

## Safety And Quality Check

Security: no secrets were read or printed during review. Default tests did not
call paid APIs, AWS, deployment commands, or live Amazon/BestBuy scraping.

Data safety: user/API-visible worker errors remain sanitized. Raw exceptions
were visible only in internal logger output during direct probes.

Reliability: happy-path job completion and DB persistence work in tests, but
audit durability is incomplete for worker success and tool failure paths.

Performance: JSON fixture loading is acceptable for local MVP. No new live
network/model cost was introduced.

Tests: automated tests are mock-only and pass, but they missed the specific
audit regressions above.

## Initial Required Changes (Superseded)

1. Restore completed `worker` agent_run coverage for successful jobs, or obtain
   explicit approval to remove that Phase 3 behavior.
2. Persist failed `deal_search_tool` and `price_estimator_tool` agent_runs when
   those tool invocations fail.
3. Add/adjust tests so they fail on both audit regressions:
   - successful job has a completed `worker` run plus completed tool runs;
   - failed search/pricing tool invocation persists a failed tool run and a safe
     failed job.
4. Update the implementation report with final CodeGraph sync/status evidence.
5. Update stale tool READMEs or document why they remain unchanged.

## Initial Approval Notes (Superseded)

At the initial checkpoint, approval was withheld pending the fixes listed
above.

## Re-review 2026-07-19 (Superseded)

Historical decision at this checkpoint: `changes_requested`.

### Resolved

- resolved: completed jobs now persist a completed `worker` `agent_run` along
  with completed tool runs. A direct happy-path probe returned:

```text
[('worker', 'worker', 'completed', '3 products', None),
 ('deal_search_tool', 'tool', 'completed', '3 products, 0 warnings', None),
 ('price_estimator_tool', 'tool', 'completed', 'estimated=949.99, discount=200.0, score=hot', None),
 ('price_estimator_tool', 'tool', 'completed', 'estimated=307.99, discount=28.0, score=ok', None),
 ('price_estimator_tool', 'tool', 'completed', 'estimated=879.99, discount=180.0, score=good', None)]
```

- resolved: tool READMEs no longer say Phase 4A has no code.

- resolved: CodeGraph status is currently up to date at `25 files`, `332
  nodes`, `704 edges`.

### New / Remaining Findings

- major: `shopping_assistant_v3/backend/worker.py:413` - The failure persistence
  path marks every started tool timing as `failed`, even tools that already
  completed before a later tool failed. A direct pricing-failure probe produced:

```text
job_status failed error Worker failed. Try again later.
[('deal_search_tool', 'tool', 'failed', None, 'deal_search_tool failed.'),
 ('price_estimator_tool', 'tool', 'failed', None, 'price_estimator_tool failed.'),
 ('worker', 'worker', 'failed', None, 'Worker failed. Try again later.')]
```

  In that flow, `deal_search_tool` had already returned products successfully;
  only `price_estimator_tool` failed. The audit trail must not record a
  successful tool as failed. Track per-tool timing status/output as the pipeline
  progresses, then in `_save_pipeline_failure` recreate completed tool runs as
  `completed` and only the active failing tool as `failed`.

- major: `shopping_assistant_v3/tests/test_worker.py:243` - The new regression
  test only covers a failing search tool. Add a pricing-failure audit test that
  asserts `deal_search_tool` is `completed`, `price_estimator_tool` is `failed`,
  and `worker` is `failed` when the price estimator fails after search succeeds.

- minor: `shopping_assistant_v3/reports/phase_4a_mock_tools_report.md:138` -
  The report still contains stale evidence: `CodeGraph: index up to date, 16
  files indexed.` The later fixes section has the correct value, but this stale
  line needed to be updated or removed before final approval.

- minor: `shopping_assistant_v3/reports/phase_4a_mock_tools_report.md:96` and
  `shopping_assistant_v3/reports/phase_4a_mock_tools_report.md:136` - The report
  says `rg "segment4" backend/ tests/` returns only Phase 1 README references,
  but current matches are the tool READMEs under `backend/tools/`. Update the
  wording to avoid confusing old skeleton docs with current tool docs.

### Re-review Verification

Commands run:

```bash
codegraph status shopping_assistant_v3
```

Result: index up to date, `25 files`, `332 nodes`, `704 edges`.

```bash
cd shopping_assistant_v3 && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_worker.py -v
```

Result: `19 passed, 1 warning in 2.67s`.

```bash
cd shopping_assistant_v3 && rg "segment4" backend tests
```

Result: only tool README references, no runtime/test imports.

```bash
cd shopping_assistant_v3 && rg "openai|litellm|curl_cffi|modal|brave" tests
```

Result: no matches.

Attempted full/API suites:

```bash
cd shopping_assistant_v3 && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v
cd shopping_assistant_v3 && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_api.py -v
```

Both runs hung at `tests/test_api.py::TestHealth::test_health_returns_ok` in
this re-review environment and were interrupted. Focused worker tests passed,
but final approval still needed a clean full-suite run after the audit fix.

Generated `backend/database/app.db` from direct probes was removed after review.

### Required Changes For Next Review

1. Fix `_save_pipeline_failure` so successful tools before a later failure are
   restored as completed audit runs, not failed audit runs.
2. Add a worker test for price-estimator failure after successful search:
   `deal_search_tool=completed`, `price_estimator_tool=failed`,
   `worker=failed`.
3. Update stale report evidence lines for CodeGraph and `segment4` references.
4. Re-run focused worker tests and a clean full suite, then hand back for
   re-review.
