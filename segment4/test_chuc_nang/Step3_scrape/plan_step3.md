# Plan: Step 3 — Source Selection UI

**Date:** 2026-04-06
**Branch:** claudedev
**Status:** DONE — Integrated + Gradio UI tested
**Workflow:** Plan -> Code -> Test -> Confirm OK

---

## Problem

Hien tai pipeline LUON chay ca BestBuy + Amazon. User khong co lua chon nguon scrape. Khi chi can tim o 1 nguon, van phai doi ca 2 (mat ~6s thay vi ~2-4s).

---

## Solution

Them `gr.Radio` cho user chon: "All", "BestBuy", "Amazon". Default: "All".

Dat ten "All" (khong phai "Both") vi sau nay se them Walmart va cac nguon khac.

---

## Thay doi chi tiet

### 1. `search_key.py` — Them Radio vao UI

**Them `gr.Radio`:**
```python
source_input = gr.Radio(
    choices=["All", "BestBuy", "Amazon"],
    value="All",
    label="Source",
    scale=1,
)
```

**Vi tri:** Cung hang voi keyword_input va max_urls_input (trong `gr.Row()`).

**Truyen source vao pipeline:**
- `search_handler(self, keyword, max_urls, source, log_data)` — them tham so `source`
- `self.current_source = source`
- Log message: `"Source: BestBuy"`, `"Source: Amazon"`, `"Source: BestBuy + Amazon"`
- `search_btn.click(inputs=[keyword_input, max_urls_input, source_input, log_state], ...)`

**Goi framework:**
- `self.get_framework().run(query, self.current_max_urls, self.current_source)`

---

### 2. `multi_source_framework.py` — Truyen source xuong planner

```python
def run(self, keyword: str, max_urls: int = 6, source: str = "All") -> List[Opportunity]:
    self.init_agents_as_needed()
    opportunities = self.planner.plan(keyword, max_urls, source)
    ...
```

Chi them tham so `source`, truyen thang xuong `planner.plan()`.

---

### 3. `multi_source_planning_agent.py` — Logic chon nguon

**`search_and_scrape(keyword, max_results, source)`:**

```python
def search_and_scrape(self, keyword, max_results=6, source="All"):
    if source == "All":
        # ThreadPoolExecutor chay 2 pipeline song song (nhu hien tai)
        with ThreadPoolExecutor(max_workers=2) as executor:
            bb_future = executor.submit(self._bestbuy_pipeline, keyword, max_results)
            az_future = executor.submit(self._amazon_pipeline, keyword, max_results)
            bb_deals = bb_future.result()
            az_deals = az_future.result()
    elif source == "BestBuy":
        bb_deals = self._bestbuy_pipeline(keyword, max_results)
        az_deals = []
    elif source == "Amazon":
        bb_deals = []
        az_deals = self._amazon_pipeline(keyword, max_results)
    return bb_deals, az_deals
```

**`plan(keyword, max_urls, source)`:**
- Them tham so `source`, truyen vao `search_and_scrape()`
- Log: `self.log(f"Starting pipeline for: '{keyword}' (source: {source})")`

**`combine()`:** Khong can sua — da xu ly duoc list rong (vd: bb_deals=[], az_deals co data).

---

## Files can sua

| File | Thay doi | Do phuc tap |
|------|----------|-------------|
| `search_key.py` | Them `gr.Radio`, truyen source | Thap |
| `multi_source_framework.py` | Them tham so `source` | Thap |
| `multi_source_planning_agent.py` | If/elif logic trong `search_and_scrape()` | Thap |

**Files KHONG can sua:**
- `bestbuy_deals.py` — khong doi
- `amazon_deals.py` — khong doi
- `unified_deal.py` — `from_bestbuy()`/`from_amazon()` van hoat dong voi list rong
- `multi_source_scanner_agent.py` — prompt van giu prefix [BestBuy]/[Amazon]
- `gradio_helpers.py` — khong doi
- `deals.py` — khong doi

---

## Success Criteria

- [x] User chon "BestBuy" -> chi goi `_bestbuy_pipeline()`, KHONG goi Amazon
- [x] User chon "Amazon" -> chi goi `_amazon_pipeline()`, KHONG goi BestBuy
- [x] User chon "All" -> ThreadPoolExecutor parallel (nhu hien tai)
- [x] Log hien thi dung: "Source: BestBuy", "Source: Amazon", "Source: BestBuy + Amazon"
- [x] Pipeline time giam khi chi chon 1 nguon
- [x] Ket qua hien thi dung tren Gradio UI

---

## Test Results

### test_source_selection.py (unit test, keyword="laptop", max=3)
- BestBuy only: 3 deals, 0 Amazon, 5.7s
- Amazon only: 3 deals, 0 BestBuy, 2.7s
- All (parallel): 6 deals (3 BB + 3 AZ), 7.0s

### Gradio UI (uv run search_key.py)
- Da test thanh cong ca 3 options qua UI

---

## Integrated (2026-04-06)

| File | Thay doi |
|------|----------|
| `search_key.py` | Them `gr.Radio` (All/BestBuy/Amazon), `self.current_source`, truyen source vao handler + pipeline |
| `multi_source_framework.py` | `run()` them param `source="All"`, truyen xuong `planner.plan()` |
| `multi_source_planning_agent.py` | `search_and_scrape()` + `plan()` them param `source`. If/elif: All=parallel, BestBuy=only BB, Amazon=only AZ |

### Files test
- `test_source_selection.py`: Unit test search_and_scrape() voi 3 source options

---

## Mo rong tuong lai

- Them "Walmart" vao `choices` khi co `walmart_deals.py`
- "All" se tu dong bao gom tat ca nguon co san
- Co the dung `gr.CheckboxGroup` thay `gr.Radio` khi co 4+ nguon (cho phep chon nhieu nguon bat ky)
