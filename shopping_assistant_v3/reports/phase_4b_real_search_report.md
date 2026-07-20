# Phase 4B: Real Amazon/BestBuy Search Extraction — Implementation Report

## Phase

`Phase 4B: Real Amazon/BestBuy Search Extraction`

Implementer: DeepSeek

Date: 2026-07-20

Branch: TTTN

Commit reviewed: not committed yet

## Tom Tat

Implemented real Amazon and BestBuy search extraction adapted from `segment4/` into V3 as independent opt-in modules behind `ENABLE_REAL_SEARCH=true`. Copy + Adapt approach — no runtime imports from segment4, no edits to segment4.

Key behaviors:
- `ENABLE_REAL_SEARCH=false` (default): mock path unchanged (Phase 4A JSON fixtures).
- `ENABLE_REAL_SEARCH=true`: dispatches to `real_deal_search()` which runs BestBuy and Amazon search sequentially.
- BestBuy: `curl_cffi` + internal APIs (search page -> priceBlocks -> v2 product details).
- Amazon: `curl_cffi` + HTML parsing, Approach A only (search page). Product page scraping (Approach B) deferred. Thin-specs products emit `amazon_features_limited` warning in tool output.
- All source failures and product warnings become sanitized bounded warnings returned in `DealSearchOutput.warnings` — no raw exceptions, HTML, or stack traces in user-facing output.
- Parsers (`_parse_apollo_search_page`, `_parse_amazon_search_page`, `_parse_price`) are testable with local HTML fixtures, no network required.
- `curl_cffi` imported via try/except — modules importable without the dependency.

## Files Da Tao

```text
backend/tools/deal_search/bestbuy_search.py — BestBuy real search: 5 functions, ~170 lines, adapted from segment4/price_agents/bestbuy_deals.py
backend/tools/deal_search/amazon_search.py — Amazon real search: 4 functions, ~220 lines, adapted from segment4/price_agents/amazon_deals.py
backend/tools/deal_search/real_search.py — Real search orchestrator: sequential dispatch, warning grammar, ~80 lines
tests/fixtures/__init__.py — Fixture package init
tests/fixtures/amazon_search_page.html — 2 product cards (detailed + thin specs) for parser tests
tests/fixtures/bestbuy_search_page.html — Apollo SSR cache simulation with 2 SKUs for parser tests
tests/test_real_search.py — 8 opt-in live integration tests, skipped by default
reports/phase_4b_implementation_plan.md — Implementation plan (this report's companion document)
```

## Files Da Sua

```text
backend/tools/deal_search/tool.py — replaced NotImplementedError gate with real_search.real_deal_search() dispatch; updated docstring; changed import from function-import to module-import pattern
pyproject.toml — added curl_cffi>=0.7.0 and beautifulsoup4>=4.12.0 to dependencies
uv.lock — auto-updated by uv lock (39 packages resolved)
tests/test_tools.py — replaced TestRealModeFlags (Phase 4A -> Phase 4B behavior); added 18 parser tests across 3 new test classes (TestBestBuyApolloParser, TestAmazonSearchPageParser, TestAmazonParsePrice)
tests/test_worker.py — updated test_real_search_flag_fails_job_with_safe_error -> test_real_search_flag_completes_job_with_real_path (Phase 4B behavior)
```

## Adapted Functions (segment4 -> V3)

| segment4 | V3 | Notes |
|---|---|---|
| `_init_session()` | `_create_session()` in bestbuy_search | Same logic, inline |
| `search_bestbuy()` | `_parse_apollo_search_page()` | Extracted as testable parser |
| `get_price_blocks()` | `_fetch_price_blocks()` | Same logic |
| `get_product_details()` | `_fetch_product_details()` | Same logic |
| `search_filter_scrape_bestbuy()` | `search_bestbuy_real()` | Returns `ProductCandidate` directly, sanitized warnings |
| `init_amazon_session()` | `_create_session()` in amazon_search | Same logic |
| `parse_search_results()` | `_parse_amazon_search_page()` | Same logic, testable with fixture |
| `_parse_price()` | `_parse_price()` | Identical |
| `search_amazon()` | inline in `search_amazon_real()` | Same logic |
| `scrape_product_page()` | DEFERRED | Comment boundary only, no stub function |
| `search_filter_scrape_amazon()` | `search_amazon_real()` | Approach A only, `amazon_features_limited` warning |

## CodeGraph Evidence

**Pre-extraction (Task 0):**
```text
codegraph --version → 1.4.0
codegraph status segment4 → 24 files, 360 nodes, 718 edges (up to date)
codegraph explore BestBuy flow → search_filter_scrape_bestbuy -> _init_session -> search_bestbuy -> get_price_blocks -> get_product_details -> ScrapedBestBuyDeal
codegraph explore Amazon flow → search_filter_scrape_amazon -> init_amazon_session -> search_amazon -> parse_search_results -> scrape_product_page (Approach B) -> ScrapedAmazonDeal
codegraph impact search_filter_scrape_bestbuy → 5 affected symbols in segment4, no V3 callers
codegraph impact search_filter_scrape_amazon → 5 affected symbols in segment4, no V3 callers
Baseline: shopping_assistant_v3 → 25 files, 334 nodes, 711 edges
```

**Post-implementation (Task 10):**
```text
codegraph sync shopping_assistant_v3 → 8 changed files (+5 added, 3 modified), 193 nodes
codegraph status shopping_assistant_v3 → 30 files, 421 nodes, 895 edges (up to date)
```

## Commands Da Chay

```bash
# Task 0: CodeGraph evidence
codegraph --version                          # → 1.4.0
codegraph status segment4                    # → up to date, 24/360/718
codegraph explore -p ... segment4 "BestBuy"  # → full call chain
codegraph explore -p ... segment4 "Amazon"   # → full call chain
codegraph impact ... search_filter_scrape_bestbuy  # → 5 affected
codegraph impact ... search_filter_scrape_amazon   # → 5 affected
codegraph status shopping_assistant_v3       # → baseline 25/334/711

# Task 1: Dependencies
uv lock                                       # → 39 packages resolved
uv sync --all-extras                          # → installed curl_cffi + bs4
uv run python -c "from curl_cffi import requests; from bs4 import BeautifulSoup"  # → OK

# Task 2-4: Module creation + verification
uv run python -c "from backend.tools.deal_search.bestbuy_search import ..."  # → OK
uv run python -c "from backend.tools.deal_search.amazon_search import ..."   # → OK
# Parser verification:
#   BestBuy: 2 SKUs extracted (6501234, 6501235)
#   Amazon: 2 products (B0TEST0001 on_sale=True $1099.99, B0TEST0002 on_sale=True $19.99)
#   _parse_price: $1,099.99 -> 1099.99, $19.99 -> 19.99

# Task 5-6: Orchestrator + tool wiring
uv run python -c "from backend.tools.deal_search.real_search import real_deal_search"  # → OK
uv run python -c "mock path unchanged, 3 products for 'gaming laptop'"   # → OK

# Task 7-8: Tests
uv run pytest tests/test_tools.py -v -k "BestBuyApollo or AmazonSearchPage or AmazonParsePrice or RealModeFlags"  # → 19 passed
uv run pytest tests/ -v                                                   # → 98 passed
uv run pytest tests/test_real_search.py -v                                # → 8 skipped

# Task 10: Verification
rg -n "from segment4\|import segment4" shopping_assistant_v3/backend/ shopping_assistant_v3/tests/  # → NO MATCHES
git diff --name-only -- segment4/                                          # → no output (untouched)
codegraph sync shopping_assistant_v3                                       # → 8 changed, 193 nodes
codegraph status shopping_assistant_v3                                     # → 30/421/895 up to date
```

## Tests Da Chay

| File | Count | Result |
|---|---|---|
| tests/test_api.py | 22 | 22 passed |
| tests/test_repository.py | 8 | 8 passed |
| tests/test_tools.py | 49 | 49 passed (+18 parser + 1 features_limited warning) |
| tests/test_worker.py | 20 | 20 passed (1 updated for Phase 4B) |
| tests/test_real_search.py | 8 | 8 skipped |
| **Total** | **107** | **99 passed, 8 skipped** |

All default tests are mock/fixture-only. No network, no model calls, no secrets required.
Opt-in real search tests (test_real_search.py) skipped by default, require `ENABLE_REAL_SEARCH=true`.

## Bang Chung Verification

1. **Mock path unchanged**: All 31 Phase 4A mock tests pass without modification. `ENABLE_REAL_SEARCH=false` -> JSON fixture keyword matching.
2. **Real path dispatch**: `ENABLE_REAL_SEARCH=true` -> `real_search.real_deal_search()` is called (verified by `TestRealModeFlags::test_real_search_dispatches_to_real_path`).
3. **Parser tests deterministic**: 18 parser tests use local HTML fixtures, no network. BestBuy Apollo parser extracts correct SKU IDs. Amazon search page parser extracts all fields (asin, title, brand, prices, specs, on_sale). `_parse_price` handles standard/edge cases.
4. **Module import safety**: `curl_cffi` imported via try/except in both source modules — modules importable even without the dependency.
5. **Warning grammar**: All source warnings follow bounded grammar (`bestbuy_search_failed: request_failed`, `amazon_search_failed: blocked`, `amazon_features_limited: <title>`, etc.). No raw exceptions/HTML/stack traces in warnings. Default test `TestAmazonFeaturesLimitedWarning` verifies `amazon_features_limited` is returned in `DealSearchOutput.warnings` using fake session + local fixture — no network.
6. **Source failures are warnings, not crashes**: `search_bestbuy_real` and `search_amazon_real` never raise — all failures become sanitized warning strings. Orchestrator returns partial results when one source fails.
7. **No source_skipped warnings**: Source filter is normal operation — no `bestbuy_skipped`/`amazon_skipped` warnings for `source="Amazon"`.
8. **Worker integration**: `ENABLE_REAL_SEARCH=true` job completes (not fails) because real search is implemented. Failures at network level become warnings, not job errors.
9. **No segment4 runtime imports**: `rg` search confirms zero `from segment4` or `import segment4` in V3 backend or tests.
10. **segment4 untouched**: `git diff --name-only -- segment4/` returns empty.
11. **CodeGraph**: Post-implementation index at 30 files, 421 nodes, 895 edges (up from 25/334/711 baseline).
12. **No secrets accessed**: No .env reading, no API keys, no credentials. All tests run without secrets.

## Known Issues

- **Per-request timeout** (Minor): `BESTBUY_TIMEOUT` and `AMAZON_TIMEOUT` are per-request timeouts, not source-level deadlines. One BestBuy search can make 1 (search) + 1 (priceBlocks) + up to `max_results` (product details) requests. Worst-case wall time ≈ `timeout * (2 + max_results)`. Source-level deadline wrapping is deferred to a future hardening milestone.
- **Amazon Approach B deferred** (Minor): Product page scraping (`scrape_product_page`) is not implemented. Products with thin specs (< 50 chars) from search page get `amazon_features_limited` log entries but no detail enrichment. Boundary documented in amazon_search.py comment block. Future milestone: 4B.1 with `ENABLE_AMAZON_DETAIL_SCRAPE=true` flag.
- **Sequential execution** (Minor): `source="All"` runs BestBuy then Amazon sequentially. Parallel execution (like segment4's `ThreadPoolExecutor`) deferred to keep Phase 4B simple and testable.

## Deviations From Guide

```text
Guide expectation: Parallel BestBuy + Amazon search via ThreadPoolExecutor (matching segment4).
Actual implementation: Sequential execution (BestBuy first, then Amazon).
Reason: Prioritize correctness, testability, and audit clarity over latency. Request handler already async via job worker.
Should docs be updated? No — documented as intentional simplification in plan and report.

Guide expectation: Amazon product page fallback (Approach B) when specs < 50 chars.
Actual implementation: Approach A only. Thin specs logged with "features_limited" detail. No product page GET requests.
Reason: Reduce live scraping risk in Phase 4B. Fewer requests = less chance of detection/blocking, easier to test.
Should docs be updated? No — deferred to future milestone 4B.1.

Guide expectation: max_results_per_source default = 6 (segment4 convention).
Actual implementation: max_results_per_source default = 5 (Phase 4A contract change, carried forward).
Reason: Approved contract change during Phase 4A brainstorming.
Should docs be updated? Yes — architecture.md and agent_architecture.md examples show 6, should be 5.

Guide expectation: query_en from Router (Phase 5).
Actual implementation: query_en bridged from request_payload["message"] via _normalize_query() in worker.
Reason: Phase 4A temporary bridge. Router replaces this in Phase 5.
Should docs be updated? No — documented as temporary in code comments.

Guide expectation: NotImplementedError when ENABLE_REAL_SEARCH=true (Phase 4A).
Actual implementation: Real search executes normally. NotImplementedError only for ENABLE_REAL_MODEL_CALLS (still Phase 4A).
Reason: Phase 4B implements real search. Pricing remains mock-only until Phase 4C.
Should docs be updated? No — this is the expected Phase 4B behavior change.
```

## Suggested Doc Updates

```text
architecture.md — update max_results_per_source examples from 6 to 5 (if examples exist).
agent_architecture.md — update max_results_per_source examples from 6 to 5.
gameplan.md and PROJECT_STATUS.md — update after Codex approval (not implementer responsibility).
```

## Self-Check (Mandatory Before Handoff)

- **security**: No secrets read, printed, logged, committed, or exposed. No live scraping in default tests (`ENABLE_REAL_SEARCH=false`). No paid model calls. No AWS/Terraform/deploy. Network only in opt-in path gated by env var. ✓
- **data safety**: Persisted payloads, URLs, user messages, tool/model errors are sanitized. Safe error messages to API (no raw exceptions). Source warnings use bounded grammar — no raw HTML, headers, cookies, or stack traces. ✓
- **reliability**: Job/status transitions work. Idempotency gates preserved. Failure paths save safe errors and agent_runs. Stale-running recovery preserved. Real search failures (network timeout, CAPTCHA, parse error) become warnings — never crash the job. ✓
- **performance**: Mock path unchanged (instant from JSON). Real search adds per-request timeout (15s) * up to (2 + max_results) requests per source. Sequential execution avoids thread safety issues. No unbounded work, uncontrolled threads, repeated expensive calls, or polling loops. ✓
- **tests**: 98 default tests pass (mock/fixture-only). 8 opt-in tests skipped by default. 18 new parser tests use local HTML fixtures only. No secrets, live scraping, paid model calls, AWS, or external services required for default test suite. ✓

## Handoff

Ready for Codex review. No commits made (implementer workflow prohibits commits before Codex approval).

Branch: TTTN
Files changed: 5 modified + 8 new (see git status)
Dependency: uv.lock updated, curl_cffi + beautifulsoup4 installed
