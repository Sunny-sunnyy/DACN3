# Codex Review: Phase 4B Real Amazon/BestBuy Search Extraction

Decision: approved
Reviewer: Codex
Date: 2026-07-20
Implementer report: `shopping_assistant_v3/reports/phase_4b_real_search_report.md`

## Tóm Tắt

Phase 4B is approved after one correction round. The copy/adapt boundary is
clean, `segment4/` is untouched, default search remains mock-only, opt-in real
search is gated behind `ENABLE_REAL_SEARCH=true`, and the required
`amazon_features_limited` evidence warning is now returned in
`DealSearchOutput.warnings`.

## Final Re-review 2026-07-20

Không có blocker hoặc major findings.

The required fixes were applied:

- `search_amazon_real()` now appends `amazon_features_limited:
  <truncated_title>` to returned warnings for thin search-page specs.
- `TestAmazonFeaturesLimitedWarning` verifies the warning with a fake session
  and local Amazon fixture, without live network access.
- `deal_search()` docstrings now describe mock/default and real/opt-in paths.
- The implementation report was updated to `107` collected tests: `99 passed`,
  `8 skipped`.
- The generated `backend/database/app.db` file was removed from the worktree.

Approval note: I reran the full suite outside the sandboxed tool environment
after reproducing a sandbox-only `TestClient` hang. The rerun completed
successfully with `99 passed, 8 skipped, 1 warning in 31.93s`.

## Findings

Không có blocker hoặc major findings.

Historical initial findings are preserved below in the superseded section.

## Verification

Commands run:

```bash
git status --short
```

Result: Phase 4B files are modified/untracked. Two unrelated untracked
`shopping_assistant_v2/` files remain. Generated
`shopping_assistant_v3/backend/database/app.db` is no longer present.

```bash
codegraph status shopping_assistant_v3
```

Initial result: index stale after correction changes. I ran:

```bash
codegraph sync shopping_assistant_v3
codegraph status shopping_assistant_v3
```

Final result: index up to date, `30 files`, `427 nodes`, `907 edges`.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_tools.py -v
```

Result after fixes: `49 passed, 1 warning in 13.44s`.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_real_search.py -v
```

Result after fixes: `8 skipped, 1 warning in 0.06s`.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_worker.py -v
```

Result after fixes: `20 passed, 1 warning in 8.62s`.

Mock-safe probe for thin Amazon features:

```text
TestAmazonFeaturesLimitedWarning passed; the warning is returned through
DealSearchOutput.warnings.
```

```bash
rg -n "from segment4|import segment4" shopping_assistant_v3/backend/ shopping_assistant_v3/tests/
```

Result: no runtime imports. Matches mentioning `segment4` are documentation
strings/comments only.

```bash
git diff --name-only -- segment4/
```

Result: no output.

Full suite rerun:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -q --tb=short
```

Result after rerun outside sandbox: `99 passed, 8 skipped, 1 warning in 31.93s`.
The earlier sandboxed attempts hung at
`tests/test_api.py::TestHealth::test_health_returns_ok`; a `faulthandler` probe
showed the request waiting in Starlette/TestClient paths, not Phase 4B scraper
code. The successful rerun is the approval evidence.

## Scope Check

Runtime scope stayed inside Phase 4B: opt-in real Amazon/BestBuy search
extraction, parser fixtures/tests, real search orchestrator, dependency lock
updates, and report/plan files. I did not see `segment4/` edits or V3 runtime
imports from `segment4`.

## Safety And Quality Check

Security: no secrets were read or printed during review. Default verification
did not run live Amazon/BestBuy scraping, paid model calls, AWS, Terraform, or
deployment commands.

Data safety: source failure warnings are bounded reason codes. Thin Amazon
search-page specs now surface as `amazon_features_limited` warning evidence.

Reliability: focused worker/tool tests and the full suite pass. Real source
functions catch expected request/parse failures into safe warnings.

Performance: sequential source execution and per-request timeouts are
acceptable as documented Phase 4B limitations.

## Thay Đổi Bắt Buộc

Không còn required changes.

## Approval Notes

Phase 4B is approved. The project may move to Phase 4C planning only after the
user explicitly confirms that milestone and scope. Do not start real pricing
extraction, paid model calls, live model tests, git stage/commit/push, AWS, or
deploy actions without explicit user approval.

## Initial Findings (Superseded)

- major: `shopping_assistant_v3/backend/tools/deal_search/amazon_search.py:265` - `amazon_features_limited` was not returned as tool evidence. The Phase 4B design and module docstring said products with specs shorter than `MIN_FEATURES_LEN` should get an `amazon_features_limited` warning, but the implementation only wrote a log line and returned `products, []` at line 287. A mock-safe probe using `tests/fixtures/amazon_search_page.html` returned `2` products and `warnings=[]` even though the second fixture product had thin specs.

- minor: `shopping_assistant_v3/backend/tools/deal_search/tool.py:42` - The function docstring was stale. It still said the function was mock-only and raised `NotImplementedError` when `ENABLE_REAL_SEARCH` was true.

- minor: `shopping_assistant_v3/reports/phase_4b_real_search_report.md:145` - The report said there were 18 parser tests, while the collected test count indicated 17 parser/price parsing additions and `48` total tests in `tests/test_tools.py`.

- minor: `shopping_assistant_v3/backend/database/app.db` - A generated SQLite DB was untracked in the worktree.
