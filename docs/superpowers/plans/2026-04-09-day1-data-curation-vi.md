# Day 1: Data Curation (Vietnamese) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load 121K Vietnamese products from Tiki JSONL files, clean, deduplicate, analyze, weighted sample, split train/val/test, and push to HuggingFace Hub as `SeanSunny/items_raw_tv`.

**Architecture:** Mirrors English Day 1 pipeline (pricer/ package) adapted for Vietnamese. Data flows: 54 JSONL files -> parser (9-step Vietnamese cleaning) -> dedup -> EDA -> weighted sampling -> split -> HF Hub. Kaggle files mapped to category "Thoi Trang".

**Tech Stack:** Python 3.12, uv, Pydantic, matplotlib, numpy, tqdm, huggingface datasets

---

## File Structure

| File | Responsibility |
|---|---|
| `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/__init__.py` | Package marker |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/items.py` | Pydantic Item model, HF Hub push/load |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/parser.py` | Vietnamese text cleaning (9 steps), parse function |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py` | Full Day 1 pipeline script |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.ipynb` | Interactive notebook version |

## Data Source

- 54 JSONL files at `scraping_data_tv/Tiki/Tiki_dataset_scrape/`
- Scraper files: `tiki_{category_id}.jsonl` (48 files, 79,382 SP)
- Kaggle files: `tiki_kaggle_*.jsonl` (6 files, 41,603 SP)

## Thresholds (confirmed)

| Parameter | Value |
|---|---|
| MIN_PRICE | 1,000 VND |
| MAX_PRICE | 50,000,000 VND |
| MIN_CHARS | 50 (on `full` field) |
| MAX_TEXT_EACH | 3,000 |
| MAX_TEXT_TOTAL | 4,000 |

## Category Mapping

- Scraper: extract top-level from breadcrumb (`"Nha Cua - Doi Song > Dung cu nha bep > ..."` -> `"Nha Cua - Doi Song"`)
- Kaggle (all 6 files): override to `"Thoi Trang"`

---

### Task 1: Create pricer_vi/items.py

**Files:**
- Create: `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/__init__.py`
- Create: `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/items.py`

- [ ] **Step 1: Create __init__.py**
- [ ] **Step 2: Create items.py with Item model**
- [ ] **Step 3: Verify import works**

Run: `uv run python -c "from scraping_data_tv.Data_processing_for_Vietnamese_data.pricer_vi.items import Item; print(Item.__fields__.keys())"`

---

### Task 2: Create pricer_vi/parser.py

**Files:**
- Create: `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/parser.py`

- [ ] **Step 1: Create parser.py with clean_text, scrub, parse functions**
- [ ] **Step 2: Verify import works**

---

### Task 3: Test parser on real data

- [ ] **Step 1: Run parser on sample scraper + kaggle items, verify cleaning**

---

### Task 4: Create day1_data_curation.py

**Files:**
- Create: `scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py`

Pipeline: load -> clean -> dedup -> EDA -> weighted sampling -> split -> push HF

- [ ] **Step 1: Write full pipeline script**
- [ ] **Step 2: Run and verify**

---

### Task 5: Run full pipeline

- [ ] **Step 1: Execute day1_data_curation.py**
- [ ] **Step 2: Review EDA charts and statistics**
- [ ] **Step 3: Decide weighted sampling penalties based on EDA**
- [ ] **Step 4: Re-run with penalties if needed**

---

### Task 6: Create day1_data_curation.ipynb

- [ ] **Step 1: Convert .py logic to .ipynb cells (mirrors English day1.ipynb)**

---

### Task 7: Commit

- [ ] **Step 1: Git commit all Day 1 files**
