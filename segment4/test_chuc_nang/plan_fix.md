# Plan: Fix BestBuy + Optimize Pipeline Speed

**Date:** 2026-03-23
**Branch:** claudedev
**Workflow:** Plan -> Test in .ipynb -> Confirm OK -> Update into .py

---

## Problem Overview

Pipeline ban dau chay ~6.3 min (375.9s). Breakdown:

| Step | Time | Issue | Status |
|------|------|-------|--------|
| Step 1: Search (Brave MCP) | 73s | Spawn npx process, cham | **FIXED** - curl_cffi truc tiep |
| Step 2: Filter BestBuy | ~100s waste | `requests.get()` is blocked, 10/10 timeouts | **FIXED** - BestBuy APIs |
| Step 2: Filter Amazon | ~70s | OK but opens a separate browser | **FIXED** - curl_cffi HTML parse |
| Step 3-4: Scrape | 41s | Opens a NEW browser, sets location AGAIN | **FIXED** - curl_cffi |
| Step 6: Estimate | 45.7s | 5 deals x 3 models running sequentially | **CHUA FIX** |

**Goal:** Reduce from ~6.3 min down to ~3 min
**Hien tai:** Search+Filter+Scrape (BestBuy+Amazon parallel): ~6s. Tong pipeline chua test full (cho Step 4).

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

## Step 2: Optimize Step 1 — Direct Brave Search (replace MCP) — DONE

### Status
- **BestBuy**: DONE (Step 1). `curl_cffi` search truc tiep tren bestbuy.com (~4s).
- **Amazon**: DONE. `curl_cffi` search truc tiep tren amazon.com (~2s). Xoa Brave MCP + Playwright.

### Solution (thay doi so voi plan ban dau)
Plan ban dau: dung Brave REST API. Thuc te: search truc tiep tren amazon.com (giong BestBuy).
- `curl_cffi` (impersonate Chrome) + parse HTML search page
- ZIP 96150 set qua POST API
- Approach A (specs tu search page) / B (GET product page) tu dong chon
- BestBuy + Amazon chay parallel bang `ThreadPoolExecutor`

### Integrated (commit `c98733d`, 2026-04-06)

| File | Thay doi |
|------|----------|
| `amazon_deals.py` | Xoa Playwright. Them curl_cffi search+filter+scrape |
| `amazon_scanner_agent.py` | Xoa AmazonSearchAgent + AmazonScannerAgent (dung MultiSourceScannerAgent) |
| `multi_source_planning_agent.py` | Re-enable Amazon, ThreadPoolExecutor parallel, max_results=6 |
| `multi_source_framework.py` | Default max_urls: 10 -> 6 |
| `search_key.py` | Default 6, UI text multi-source |

### Test Results (test_integration.py)
- Amazon standalone: 6 deals, 2.3s
- BestBuy standalone: 2 deals, 6.9s
- Parallel: 8 deals, 6.0s
- UnifiedScrapedDeal: 8/8 OK

### Files
- Chi tiet: `test_chuc_nang/fix_amazon_v2_s2/plan_amazon.md`

---

## Step 3: Source Selection UI — Cho user chon nguon scrape — CHUA LAM

### Task
Them option cho nguoi dung chon scrape o dau: BestBuy, Amazon, hoac ca 2 (Both).

### How to do it

**1. UI (`search_key.py`):**
- Them `gr.Radio` hoac `gr.Dropdown` voi 3 lua chon: "Both", "BestBuy", "Amazon" (default: "Both")
- Truyen gia tri `source` vao `framework.run(keyword, max_urls, source)`
- Cap nhat title/text UI phan anh lua chon

**2. Framework (`multi_source_framework.py`):**
- Them tham so `source` vao `run(keyword, max_urls, source="both")`
- Truyen xuong `planner.plan(keyword, max_urls, source)`

**3. Pipeline (`multi_source_planning_agent.py`):**
- `search_and_scrape(keyword, max_results, source)`:
  - `source="both"` -> ThreadPoolExecutor chay 2 pipeline (hien tai)
  - `source="bestbuy"` -> chi goi `_bestbuy_pipeline()`
  - `source="amazon"` -> chi goi `_amazon_pipeline()`
- `combine()` xu ly truong hop 1 list rong (chi 1 nguon)

**4. Scanner (`multi_source_scanner_agent.py`):**
- Prompt hien tai yeu cau prefix [BestBuy]/[Amazon]. Khi chi 1 nguon, van hoat dong dung (chi co 1 source)

### Success Criteria
- [ ] User chon "BestBuy" -> chi scrape BestBuy, khong goi Amazon
- [ ] User chon "Amazon" -> chi scrape Amazon, khong goi BestBuy
- [ ] User chon "Both" -> chay parallel nhu hien tai
- [ ] UI hien thi ro nguon dang chon
- [ ] Pipeline time giam khi chi chon 1 nguon

### Files can sua
- `search_key.py` — them Radio/Dropdown, truyen source
- `multi_source_framework.py` — them tham so source
- `multi_source_planning_agent.py` — logic chon nguon trong search_and_scrape()

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
- [ ] Step 4 time reduced >= 30% (currently ~50s for 3 deals)

### How to verify
- Run notebook with 3-5 product descriptions
- Compare prices: sequential vs parallel (must be the same)
- Measure time: sequential vs parallel

### Files
- Notebook: `buoc4_ensemble_song_song.ipynb`
- After OK -> update: `price_agents/ensemble_agent.py`

---

## Step 5: Integrate Everything into .py Files — DA GOP VAO STEP 1+2

Step nay khong con la buoc rieng. Moi step da tu integrate vao code chinh ngay khi test xong:
- Step 1: integrate BestBuy (commit `ef9084c`)
- Step 2: integrate Amazon + parallel (commit `c98733d`)
- Step 4 (parallel ensemble): se integrate truc tiep sau khi test OK

### Da thuc hien (across Step 1+2)
- [x] `bestbuy_deals.py` — curl_cffi + BestBuy APIs (xoa Playwright/requests)
- [x] `amazon_deals.py` — curl_cffi + HTML parsing (xoa Playwright)
- [x] `amazon_scanner_agent.py` — deprecated (xoa AmazonSearchAgent + AmazonScannerAgent)
- [x] `multi_source_planning_agent.py` — 4-step pipeline, ThreadPoolExecutor parallel
- [x] `multi_source_scanner_agent.py` — GPT-5-nano chon top 3
- [x] `multi_source_framework.py` — default max_urls=6
- [x] `search_key.py` — UI multi-source, default 6
- [ ] `ensemble_agent.py` — chua sua (cho Step 4)
- [ ] `bestbuy_scanner_agent.py` — van con code cu (Brave MCP), nhung KHONG duoc import boi pipeline hien tai

---

## Execution Order

```
Step 1 (Fix BestBuy)       -->  DONE - curl_cffi + APIs
Step 5 (Integrate .py)     -->  DONE - da tich hop, bo clarification, Cerebras, URL clickable
    |
Step 2 (Direct Search)     -->  DONE - Amazon curl_cffi, ThreadPoolExecutor parallel, commit c98733d
    |
Step 3 (Source Selection)  -->  CHUA LAM - UI cho user chon BestBuy/Amazon/Both
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

## Actual Time After Step 2 Integration (BestBuy + Amazon parallel)

| Step | BestBuy only (Step 1) | BestBuy + Amazon (Step 2) | Ghi chu |
|------|----------------------|--------------------------|---------|
| Search+Filter+Scrape | ~8s (BestBuy) | ~6s (parallel: BB 6.9s, AZ 2.3s) | ThreadPoolExecutor, time = max(BB, AZ) |
| Select top deals | ~17s (Cerebras) | chua test GPT-5-nano | Doi sang GPT-5-nano |
| Estimate | ~50s | chua test | |
| **TOTAL** | **95.7s** | **chua test full pipeline** | Chua test Gradio UI |

Ghi chu: test_integration.py chi test Step 1 (search+filter+scrape). Chua test full pipeline qua Gradio.