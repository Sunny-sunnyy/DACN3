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

## Step 1: Fix BestBuy Filter (being blocked) — DONE

### Task
Replace `requests.get()` with `curl_cffi` + BestBuy internal APIs.

Product pages bi block tu WSL2 do HTTP/2 incompatibility voi Akamai CDN.
Giai phap: dung `curl_cffi` (impersonate Chrome) + 3 APIs noi bo thay vi scrape product pages.

### Solution (thay doi so voi plan ban dau)
Plan ban dau: dung Playwright thay requests. Thuc te: Playwright cung bi block tu WSL2.
Giai phap cuoi cung: `curl_cffi` + BestBuy APIs (search page + priceBlocks + v2 product API).

### Success Criteria
- [x] Reproduce the bug: `requests.get()` timeout 10/10
- [x] New function detects products ON SALE (7/136 SKUs on sale with keyword "laptop")
- [x] New function does NOT get timed out or blocked
- [x] Time to filter+scrape < 10s (cu: 100s timeout)

### Integrated
- `bestbuy_deals.py`: xoa `requests`/`BeautifulSoup`/`Playwright`, them `curl_cffi` + APIs
- `multi_source_planning_agent.py`: bo `BestBuySearchAgent`, pipeline 6->4 buoc
- `multi_source_scanner_agent.py`: GPT-5-mini -> Cerebras via LiteLLM
- `search_key.py`: bo clarification, URL clickable
- Pipeline: 375.9s -> **95.7s**

### Files
- `buoc1.py`: 3 functions doc lap (unit test)
- `buoc1.ipynb`: Full pipeline test voi GPT-5-mini
- `buoc1a.ipynb`: Optimized pipeline: gop Step 2+3, Cerebras thay GPT-5-mini

---

## Step 2: Optimize Step 1 — Direct Brave Search (replace MCP) — PARTIALLY DONE

### Status
- **BestBuy**: KHONG CAN Brave Search nua. Step 1 da thay bang `curl_cffi` search truc tiep tren bestbuy.com (~4s).
- **Amazon**: VAN CON dung Brave MCP (cham ~60-70s). Can thay bang Brave REST API hoac tuong tu BestBuy.
- Amazon hien dang **tam an** (commit `566544e`), se fix khi re-enable.

### Remaining Task (chi Amazon)
1. Call Brave Search REST API: `GET https://api.search.brave.com/res/v1/web/search`
2. Parse JSON, extract Amazon URLs: `https://www.amazon.com/.../dp/XXXXXXXXXX`
3. Hoac: search truc tiep tren amazon.com tuong tu BestBuy

### Files
- After OK -> update: `price_agents/amazon_scanner_agent.py`

---

## Step 3: Optimize Step 2+3 — Reuse Browser Session

### Status Update
- **BestBuy**: KHONG CON dung browser. Da chuyen sang `curl_cffi` + APIs (~8s tong). Buoc nay khong con ap dung cho BestBuy.
- **Amazon**: VAN CAN optimize. Hien dang tam an, se thuc hien khi re-enable Amazon.

### Remaining Task (chi Amazon)
1. Gop `filter_amazon_sale_urls_playwright()` + `scrape_amazon_products()` thanh 1 ham
2. Mo 1 browser, set US location 1 lan, filter+scrape cung luc
3. Target: Step 2+3 Amazon < 80s (cu: ~110s)

### Files
- After OK -> update: `price_agents/amazon_deals.py`, `price_agents/multi_source_planning_agent.py`

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
Step 1 (Fix BestBuy)       -->  DONE - curl_cffi + APIs
Step 5 (Integrate .py)     -->  DONE - da tich hop, bo clarification, Cerebras, URL clickable
    |
Step 2 (Direct Brave)      -->  chi con Amazon (BestBuy xong)
    |
Step 3 (Reuse browser)     -->  chi con Amazon (BestBuy khong con dung browser)
    |
Step 4 (Parallel ensemble) -->  chua lam
```

## Actual Time After Step 1 Integration (BestBuy only, Amazon tam an)

| Step | Before | After | Savings |
|------|--------|-------|---------|
| Search+Filter+Scrape BestBuy | 173s (search 73s + filter 100s timeout) | ~8s (curl_cffi + APIs) | 165s |
| Select top 5 | 29s (GPT-5-mini) | ~17s (Cerebras) | 12s |
| Estimate | 45.7s | ~50s | -4s |
| **TOTAL (BestBuy only)** | **375.9s (6.3 min)** | **95.7s (1.6 min)** | **280s** |

Ghi chu: thoi gian thuc te 95.7s bao gom ca init agents (~10s lan dau).