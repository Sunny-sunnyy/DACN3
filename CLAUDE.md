# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Price Intelligence System (DACN3) — A multi-agent system that searches for product deals on BestBuy and Amazon, estimates true prices using an ML ensemble, and sends push notifications for high-value discounts.

## Build & Run Commands

**IMPORTANT:** This project uses `uv` as the sole package manager and runtime. The virtual environment is managed by `uv` in the project root (`tech2ai/`). NEVER use `python` or `pip` directly — always use `uv run` to execute scripts (it automatically activates the correct venv and resolves dependencies).

```bash
# Install dependencies
uv sync
uv run playwright install

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
- **LLMs:** OpenAI GPT-5.1/5-mini/5-nano, fine-tuned Llama-3.2-3B on Modal
- **ML:** PyTorch DNN (ResidualBlocks), XGBoost, scikit-learn
- **Vector DB:** ChromaDB with sentence-transformers/all-MiniLM-L6-v2
- **Web Scraping:** Playwright + BeautifulSoup4
- **Search:** Brave Search API via MCP
- **UI:** Gradio
- **Notifications:** Pushover API
- **LLM Abstraction:** LiteLLM

## Architecture

All active code lives in `segment4/`. Other dirs (`base/`, `ghi_chu/`, `sandbox/`) are reference/experimental only.

### Two Applications

1. **`search_key.py`** — User enters keyword → ClarificationAgent asks 3 questions → 6-step pipeline searches, scrapes, estimates prices → results table (The relevant documents: "segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md")
2. **`price_is_right.py`** — Autonomous: timer scans DealNews RSS → selects top deals → estimates prices → deduplicates via `memory.json` → sends push notifications (The relevant documents: "segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md")

### Three-Layer Architecture

```
UI Layer:        search_key.py / price_is_right.py (Gradio)
Framework Layer: multi_source_framework.py / deal_agent_framework.py (ChromaDB init, lazy agent loading)
Agent Layer:     price_agents/ (single-responsibility agents inheriting from Agent base class)
```

### 6-Step Pipeline (search_key.py)

`MultiSourcePlanningAgent.plan()` orchestrates:
1. `search_both_sources()` — Parallel BestBuy + Amazon via Brave API (ThreadPoolExecutor)
2. `filter_sales()` — Keep only discounted items
3. `scrape_and_combine()` — Playwright extraction → UnifiedScrapedDeal
4. Transform to Deal objects (LLM summarization)
5. `select_top_deals()` — GPT-5-mini picks top 5 (Structured Outputs)
6. `estimate_prices()` — EnsembleAgent predicts true value

### Price Estimation Ensemble

`EnsembleAgent` combines three independent models:
- **FrontierAgent (80%)** — GPT-5.1 + RAG from ChromaDB (800K+ products)
- **SpecialistAgent (10%)** — Fine-tuned Llama-3.2-3B on Modal
- **NeuralNetworkAgent (10%)** — PyTorch DNN loaded from `deep_neural_network.pth`

Final price = 0.8 * frontier + 0.1 * specialist + 0.1 * neural

### Key Data Models (Pydantic, in `price_agents/deals.py`)

- `Deal` — product_description, price, url
- `DealSelection` — List[Deal] (top 5)
- `Opportunity` — Deal + estimated true value + discount
- `ScrapedDeal` / `UnifiedScrapedDeal` — Raw scraped data

## Environment Variables (`.env`)

Required: `OPENAI_API_KEY`, `BRAVE_API_KEY`, `PUSHOVER_USER`, `PUSHOVER_TOKEN`
Optional: `GOOGLE_API_KEY`, `HF_TOKEN`, `GROQ_API_KEY`, `PRICER_PREPROCESSOR_MODEL`

## Key Conventions

- All agents inherit from `Agent` base class (`price_agents/agent.py`) which provides ANSI color-coded logging
- Utilities in `bestbuy_untils/` (note: intentional typo in dir name, not "utils")
- OpenAI Structured Outputs pattern: `response_format=PydanticModel` for deterministic LLM responses
- Real-time log streaming via queue-based system in Gradio
- `memory.json` prevents duplicate notifications in autonomous mode
