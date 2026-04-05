# Plan: Fix BestBuy + Optimize Pipeline Speed

**Date:** 2026-03-23
**Branch:** claudedev
**Workflow:** Plan -> Test in .ipynb -> Confirm OK -> Update into .py

---

## Problem Overview

The current pipeline runs ~6.3 min (375.9s). Breakdown:

| Step | Time | Issue |
|------|------|-------|
| Step 1: Search (Brave MCP) | 73s | Slow because it spawns an npx process for every search |
| Step 2: Filter BestBuy | ~100s waste | `requests.get()` is blocked, 10/10 timeouts |
| Step 2: Filter Amazon | ~70s | OK but opens a separate browser |
| Step 3-4: Scrape | 41s | Opens a NEW browser, sets location AGAIN |
| Step 6: Estimate | 45.7s | 5 deals x 3 models running sequentially |

**Goal:** Reduce from ~6.3 min down to ~3 min

---

## Step 1: Fix BestBuy Filter (being blocked)

### Task
Replace `requests.get()` with Playwright to bypass BestBuy's anti-bot protection.

Currently `filter_sale_urls()` in `bestbuy_deals.py` uses the `requests` library -> BestBuy blocks it -> timeout on 10/10 URLs.

In the old notebook (February 2026, file `skipflow.ipynb`), BestBuy filter was still working (11/15 sales). So BestBuy has updated its anti-scraping measures since then.

### How to do it
1. Reproduce the bug: call `filter_sale_urls(urls)` in the notebook -> confirm 10/10 timeouts
2. Write a new `filter_bestbuy_sale_urls_playwright()` function using Playwright (similar to `filter_amazon_sale_urls_playwright()`)
3. Use Playwright with anti-detection args (`--disable-blink-features=AutomationControlled`)
4. Check for sale by looking for elements: strikethrough price, "Save $XX", "Was $XX"
5. Test in notebook with 10 URLs from Brave Search

### Success Criteria
- [ ] Reproduce the bug: `requests.get()` timeout 10/10
- [ ] New function detects products that are ON SALE (>= 5/10 URLs have sale price)
- [ ] New function does NOT get timed out or blocked
- [ ] Time to filter 10 URLs < 60s (currently wastes 100s due to timeouts)

### How to verify
- Run notebook with keyword "laptop" or "Samsung smartphone"
- Compare old result (0/10) vs new (>= 5/10)
- Print: URL, whether on sale, sale price, original price

### Files
- Notebook: `buoc1_fix_bestbuy_filter.ipynb`
- After OK -> update: `price_agents/bestbuy_deals.py`

---

## Step 2: Optimize Step 1 — Direct Brave Search (replace MCP)

### Task
Replace Brave MCP Server (which spawns an npx process) with a direct call to the Brave Search REST API.

Currently `BestBuySearchAgent` and `AmazonSearchAgent` both:
1. Spawn an npx process for `@modelcontextprotocol/server-brave-search`
2. Communicate via stdio (MCP protocol)
3. Call the OpenAI Agent SDK to control the MCP tool

This process takes ~73s. The Brave REST API only needs 1 HTTP request, taking ~2-3s.

### How to do it
1. Reproduce: measure current search time in notebook (confirm ~60-70s)
2. Call Brave Search REST API directly: `GET https://api.search.brave.com/res/v1/web/search`
3. Parse JSON result, extract product URLs with regex:
   - BestBuy: `https://www.bestbuy.com/product/...`
   - Amazon: `https://www.amazon.com/.../dp/XXXXXXXXXX`
4. No need for OpenAI Agent SDK, no need for MCP, no need for npx
5. Test in notebook: compare number of URLs and quality

### Success Criteria
- [ ] Brave REST API returns >= 10 URLs per source
- [ ] Search time < 10s (currently 73s)
- [ ] Valid URLs (correct BestBuy/Amazon product page format)
- [ ] No npx process spawning required

### How to verify
- Run notebook with keywords "laptop", "Samsung smartphone", "headphones"
- Measure time: current vs new
- Compare quantity and quality of URLs

### Files
- Notebook: `buoc2_brave_search_truc_tiep.ipynb`
- After OK -> update: `price_agents/bestbuy_scanner_agent.py`, `price_agents/amazon_scanner_agent.py`

---

## Step 3: Optimize Step 2+3 — Reuse Browser Session

### Task
Currently Step 2 (filter) and Step 3 (scrape) open 2 SEPARATE browsers. Each browser launch requires:
- Launch Chromium (~3-5s)
- Call `set_amazon_us_location()` (~5-10s)
- Close browser after completion

Optimization: use 1 browser session throughout both steps.

### Environment Notes
- The machine runs Windows, the project runs on WSL Ubuntu
- Check CPU/RAM/GPU configuration before deciding on the number of parallel tabs
- Playwright on WSL may need additional configuration (headless mode preferred)

### How to do it
1. Check machine specs (CPU cores, RAM, GPU) in notebook
2. Write a combined `filter_and_scrape_amazon()` function:
   - Open 1 browser
   - Set US location once
   - Filter URLs (keep sale items + price_info)
   - Scrape product details (same browser, same page)
   - Close browser
3. Similarly for BestBuy: `filter_and_scrape_bestbuy()` (using Playwright from Step 1)
4. Consider scraping in parallel across multiple tabs (depending on machine specs):
   - If RAM >= 16GB: can open 3-4 tabs in parallel
   - If RAM < 16GB: run sequentially but reuse browser

### Success Criteria
- [ ] Only 1 browser opened for Amazon (instead of 2)
- [ ] `set_amazon_us_location()` called only once (instead of 2)
- [ ] Time for Step 2+3 Amazon < 80s (currently ~110s = 70s filter + 41s scrape)
- [ ] Scrape results match the old ones (same number of products, accurate prices)

### How to verify
- Run notebook with 8-10 Amazon URLs
- Measure time: old (2 browsers) vs new (1 browser)
- Confirm USD prices are accurate (not VND)
- Confirm `set_amazon_us_location()` only runs once

### Files
- Notebook: `buoc3_reuse_browser.ipynb`
- After OK -> update: `price_agents/amazon_deals.py`, `price_agents/bestbuy_deals.py`, `price_agents/multi_source_planning_agent.py`

---

## Step 4: Optimize Step 6 — Parallel Ensemble

### Task
Currently `EnsembleAgent` runs 3 models SEQUENTIALLY for each deal:
1. Frontier (GPT-5.1 + RAG) — calls OpenAI API (network I/O)
2. Specialist (Llama fine-tuned) — calls Modal API (network I/O)
3. Neural Network — runs on local GPU (compute)

Even though all 3 models use 3 DIFFERENT resources (OpenAI API, Modal API, local GPU), they are currently running sequentially. They can run in parallel because:
- Frontier: waiting for response from OpenAI server (network wait)
- Specialist: waiting for response from Modal server (network wait)
- Neural: computing on local GPU

While Frontier is waiting for OpenAI's response, Specialist can simultaneously wait for Modal's response, and Neural can simultaneously compute on the GPU. There is no resource conflict.

### How to do it
1. Reproduce: measure time for each model in notebook
   - Frontier: ~Xs (network I/O)
   - Specialist: ~Ys (network I/O)
   - Neural: ~Zs (GPU compute)
2. Use `ThreadPoolExecutor` (or `asyncio.gather`) to run 3 models in parallel
3. New time = max(Frontier, Specialist, Neural) instead of sum
4. Apply to all 5 deals

### Success Criteria
- [ ] 3 models run in parallel without errors
- [ ] Estimated price results IDENTICAL to sequential run (difference < $1)
- [ ] Step 6 time reduced >= 30% (currently 45.7s for 5 deals)

### How to verify
- Run notebook with 3-5 product descriptions
- Compare prices: sequential vs parallel (must be the same)
- Measure time: sequential vs parallel

### Files
- Notebook: `buoc4_ensemble_song_song.ipynb`
- After OK -> update: `price_agents/ensemble_agent.py`

---

## Step 5: Integrate Everything into .py Files

### Task
After all 4 steps above have been tested OK in notebooks, update the main code.

### How to do it
1. Update `price_agents/bestbuy_deals.py` — new filter function (Playwright)
2. Update `price_agents/bestbuy_scanner_agent.py` — Brave REST API
3. Update `price_agents/amazon_scanner_agent.py` — Brave REST API
4. Update `price_agents/amazon_deals.py` — combined filter+scrape
5. Update `price_agents/ensemble_agent.py` — parallel execution
6. Update `price_agents/multi_source_planning_agent.py` — call new functions

### Success Criteria
- [ ] `uv run search_key.py` runs successfully
- [ ] Pipeline completes < 3 min
- [ ] BestBuy returns sale products (>= 3)
- [ ] Amazon returns accurate USD prices
- [ ] Ensemble results are accurate

### How to verify
- Run full pipeline with keyword "laptop"
- Check [TIMER] logs
- Compare with Test Run 2 (375.9s)

---

## Execution Order

```
Step 2 (Direct Brave)      -->  fastest win, saves 60s
    |
Step 1 (Fix BestBuy)       -->  fix critical bug
    |
Step 3 (Reuse browser)     -->  optimize scraping
    |
Step 4 (Parallel ensemble) -->  optimize estimation
    |
Step 5 (Integrate .py)     -->  final integration
```

## Expected Time After Optimization

| Step | Current | Expected | Savings |
|------|---------|----------|---------|
| Step 1: Search | 73s | ~10s | 63s |
| Step 2: Filter BestBuy | 100s waste | ~40s (Playwright) | 60s |
| Step 2: Filter Amazon | 70s | (merged with Step 3) | — |
| Step 3-4: Scrape | 41s | ~50s (merged filter+scrape) | 61s |
| Step 5: Select | 29s | 29s | 0s |
| Step 6: Estimate | 45.7s | ~30s | 15s |
| **TOTAL** | **375.9s (6.3 min)** | **~170s (2.8 min)** | **~200s** |