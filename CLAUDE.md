# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Price Intelligence System (DACN3) — A multi-agent system that searches for product deals on BestBuy and Amazon, estimates true prices using an ML ensemble, and sends push notifications for high-value discounts.

## Build & Run Commands

**IMPORTANT:** This project uses `uv` as the sole package manager and runtime. The virtual environment is managed by `uv` in the project root (`tech2ai/`). NEVER use `python` or `pip` directly — always use `uv run` to execute scripts (it automatically activates the correct venv and resolves dependencies).

```bash
# Install dependencies
uv sync

# Run Multi-Source Deal Finder (keyword search UI)
cd segment4 && uv run search_key.py

# Run Autonomous Deal Hunter (RSS-based, auto-runs every 5 min)
cd segment4 && uv run price_is_right.py

# Both apps serve at http://127.0.0.1:7860

# Run any Python script or one-liner
uv run some_script.py
uv run python -c "print('hello')"
```

## Tech Stack

- **Python 3.12** with `uv` package manager
- **LLMs:** OpenAI gpt-6.1-terra (Frontier) + gpt-6-luna (deal selection, messages) — both since 2026-10-29, replacing GPT-5.1 / gpt-5-nano / gpt-5-mini; fine-tuned Llama-3.2-3B on Modal
- **ML:** PyTorch DNN (ResidualBlocks), XGBoost, scikit-learn
- **Vector DB:** ChromaDB with sentence-transformers/all-MiniLM-L6-v2
- **Web Scraping:** `curl_cffi` (Chrome impersonation) + BeautifulSoup4; Amazon also uses Playwright headless Chromium once per search to pass the AWS WAF JS challenge (needs `uv run playwright install chromium`)
- **Search:** Direct search on bestbuy.com and amazon.com via `curl_cffi` — Brave MCP removed from search_key pipeline
- **UI:** Gradio
- **Notifications:** Pushover API
- **LLM Abstraction:** LiteLLM

## Architecture

All active code lives in `segment4/`. Other dirs (`base/`, `ghi_chu/`, `sandbox/`) are reference/experimental only.

### Two Applications

1. **`search_key.py`** — User enters keyword → 4-step pipeline: search+filter+scrape (BestBuy+Amazon parallel via curl_cffi) → select top 3 (gpt-6-luna) → estimate prices (EnsembleAgent) → results table (The relevant documents: "segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md")
2. **`price_is_right.py`** — Autonomous: timer scans DealNews RSS → selects top deals → estimates prices → deduplicates via `memory.json` → sends push notifications (The relevant documents: "segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md")

### Three-Layer Architecture

```
UI Layer:        search_key.py / price_is_right.py (Gradio)
Framework Layer: multi_source_framework.py / deal_agent_framework.py (ChromaDB init, lazy agent loading)
Agent Layer:     price_agents/ (single-responsibility agents inheriting from Agent base class)
```

### 4-Step Pipeline (search_key.py)

`MultiSourcePlanningAgent.plan()` orchestrates:
1. `search_and_scrape()` — BestBuy (curl_cffi + internal APIs) + Amazon (Playwright WAF cookies → curl_cffi + HTML parsing) in parallel via `ThreadPoolExecutor`. Max 6 results/source
2. `combine()` — Convert to `UnifiedScrapedDeal` pool (BestBuy + Amazon)
3. `select_top_deals()` — gpt-6-luna (reasoning `none`) picks top 3 by deal number (Structured Outputs via `MultiSourceScannerAgent`); price/URL are copied from the scraped pool by code, duplicates (same URL / same title minus colour) merged first
4. `estimate_prices()` — EnsembleAgent predicts true value; 3 deals in parallel, and the 3 models in parallel inside each deal. A model that fails or returns 0 is dropped and the weights are renormalised

### Price Estimation Ensemble

`EnsembleAgent` combines three independent models:
- **FrontierAgent (80%)** — gpt-6.1-terra (reasoning `none`) + RAG from ChromaDB (800K+ products). Measured 2026-10-29 on the first 200 test items of `SeanSunny/items_full` (1 run each): gpt-5.1 MAE $31.16, luna none $31.42, luna low $29.69, terra none $28.51 — differences within noise
- **SpecialistAgent (10%)** — Fine-tuned Llama-3.2-3B on Modal
- **NeuralNetworkAgent (10%)** — PyTorch DNN loaded from `deep_neural_network.pth`

Final price = 0.8 * frontier + 0.1 * specialist + 0.1 * neural

### Key Data Models (Pydantic, in `price_agents/deals.py`)

- `Deal` — product_description, price, url
- `DealSelection` — List[Deal] (top 3)
- `Opportunity` — Deal + estimated true value + discount
- `ScrapedBestBuyDeal` / `ScrapedAmazonDeal` — Raw scraped data per source
- `UnifiedScrapedDeal` — Normalized format combining both sources

## Environment Variables (`.env`)

Required: `OPENAI_API_KEY`, `PUSHOVER_USER`, `PUSHOVER_TOKEN`
Optional: `BRAVE_API_KEY` (only for price_is_right.py), `GOOGLE_API_KEY`, `HF_TOKEN`, `GROQ_API_KEY`, `PRICER_PREPROCESSOR_MODEL`

## Key Conventions

- All agents inherit from `Agent` base class (`price_agents/agent.py`) which provides ANSI color-coded logging
- Utilities in `bestbuy_untils/` (note: intentional typo in dir name, not "utils")
- OpenAI Structured Outputs pattern: `response_format=PydanticModel` for deterministic LLM responses
- Real-time log streaming via queue-based system in Gradio
- `memory.json` prevents duplicate notifications in autonomous mode
- Modal Llama (`pricer-service`, scaledown 60 s): search_key wakes it when the app opens, pings it every 50 s (stops after 15 min without a search) and waits max 10 s per call; price_is_right waits without a limit. A new Modal GPU app cannot be deployed until a payment method is added (2026-10-29)
- gpt-6-luna rejects `reasoning_effort="minimal"` (use `none`/`low`…); via LiteLLM 1.79 it needs `allowed_openai_params=["reasoning_effort"]`
- Each source reports a status (`ok`/`empty`/`blocked`/`error`); a failing source does not break the other
- `curl_cffi` with `impersonate="chrome"` is required for both BestBuy and Amazon scraping from WSL2
- BestBuy uses internal APIs (searchpage + priceBlocks + v2 product); priceBlocks returns max 25 SKUs/request → batched
- Amazon uses HTML search page parsing. Direct `/s?k=` needs `&ref=nb_sb_noss` + `Referer` or WAF returns 503; prices forced to USD via cookie `i18n-prefs=USD` (IP in Vietnam shows VND otherwise; old ZIP POST no longer works)
- Deprecated files: `amazon_scanner_agent.py` (Brave MCP removed), `bestbuy_scanner_agent.py` (Brave MCP, still exists but unused by search_key pipeline)
