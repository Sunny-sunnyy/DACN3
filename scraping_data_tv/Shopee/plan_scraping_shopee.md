# Plan: Scraping Shopee VN + Data Processing + ChromaDB tieng Viet

## Context

Du an tot nghiep "Tro ly mua sam thong minh tieng Viet" can 1M+ san pham tieng Viet de fine-tune LLM uoc gia. Giai doan 1 tap trung vao Shopee VN lam nguon du lieu chinh. Hien tai he thong da co pipeline tieng Anh (BestBuy/Amazon) hoat dong tot — can replicate quy trinh tuong tu cho tieng Viet.

**Muc tieu:** Xay dung pipeline cao du lieu Shopee VN, lam sach, va build ChromaDB tieng Viet. MVP: 10K-20K san pham (Dien tu + Gia dung), gia 50K-2M VND. Test tren WSL2 truoc, scale len may manh hon sau.

**Working directory:** `tech2ai/scraping_data_tv/Shopee/`

---

## Folder Structure

```
scraping_data_tv/Shopee/
    shopee_scraper/
        __init__.py
        models.py              # Pydantic: ShopeeProduct, ShopeeItem
        api_client.py          # curl_cffi session + Shopee API wrappers
        search.py              # Search API: keyword search, pagination
        product_detail.py      # Product detail API: full product info
        scraper.py             # Orchestrator: search -> detail -> save (checkpoint)
        config.py              # Constants: categories, price range, delays
    data_processing/
        __init__.py
        parser_vn.py           # Vietnamese text cleaning + filtering
        items_vn.py            # Item model cho Vietnamese products
        dedup.py               # Deduplication logic
        sampling.py            # Weighted sampling
        eda.py                 # EDA: price distribution, category balance
    chromadb_vn/
        __init__.py
        build_db.py            # Embed + insert vao ChromaDB
        test_search.py         # Validate Vietnamese similarity search
    scripts/
        01_scrape_category.py  # Scrape 1 category (test truoc)
        02_scrape_all.py       # Scrape tat ca categories
        03_clean_and_filter.py # Chay parser_vn pipeline
        04_dedup_and_sample.py # Dedup + weighted sampling + split
        05_build_chromadb.py   # Embed + build ChromaDB
        06_push_huggingface.py # Push dataset len HuggingFace Hub
    data/
        raw/                   # Raw JSONL per category
        cleaned/               # Cleaned JSONL sau parser_vn
        final/                 # Train/val/test splits
    checkpoints/               # Scraping progress checkpoints
```

---

## Implementation Steps

### Step 1: Thu nghiem lay raw data (QUAN TRONG NHAT)
**File:** `scripts/00_test_shopee_api.py`

**Muc tieu:** Viet 1 script .py don gian nhat co the, thu goi Shopee API, xem co lay duoc data khong.
Chua can models, config, hay bat ky abstraction nao. Chi can: goi API -> in ra JSON -> luu file.

**Approach A — Shopee Search API (thu truoc):**
1. Dung `curl_cffi` + `impersonate="chrome"` goi `shopee.vn/api/v4/search/search_items`
2. Xem response: co data khong? bi block khong? can headers gi?
3. Neu OK: thu pagination (page 2, 3...), thu product detail API
4. Luu raw JSON vao `data/raw/test_response.json`

**Approach B — Selenium + BS4 (fallback neu A bi block):**
1. Dung Selenium mo shopee.vn, search keyword, scroll lazy-load
2. Parse HTML bang BeautifulSoup
3. Hoac di tim tai lieu/nghien cuu them

**Approach C — Apify (fallback neu ca A va B deu that bai):**
1. Dung Apify actor (tra phi) de bypass anti-bot

**Nguyen tac:** Lam don gian nhat truoc. 1 file .py, chay duoc, thay ket qua ngay.
**Sau khi co raw data:** Moi bat dau refactor thanh models.py, config.py, pipeline...

---

### Step 1b: Models + Config (lam SAU khi co raw data)
**Files:** `shopee_scraper/models.py`, `shopee_scraper/config.py`

**models.py** — Pydantic models:
- `ShopeeProduct`: Raw data tu API (item_id, shop_id, title, category, price, description, features, brand, url, weight, rating, sold, image_url)
- `ShopeeItem`: Cleaned product cho ChromaDB/training (title, category, price, full, weight) — tuong tu `Item` trong pipeline tieng Anh

**config.py** — Constants:
- `CATEGORIES`: Dict 10 keywords (dien_thoai, laptop, may_tinh_bang, tai_nghe, loa, may_giat, tu_lanh, may_loc_nuoc, noi_com_dien, may_hut_bui)
- `PRICE_MIN_VND = 50_000`, `PRICE_MAX_VND = 2_000_000`
- `MIN_DESCRIPTION_CHARS = 200` (Vietnamese text ngan hon English)
- `MAX_TEXT_TOTAL = 4000`
- `SEARCH_DELAY = (2.0, 3.5)`, `DETAIL_DELAY = (1.0, 2.0)` — random uniform
- `MAX_RETRIES = 3`

**Luu y:** Price tu Shopee API phai chia 100,000 de co gia that (VD: API tra ve 10,000,000,000 = 100,000 VND)

**Ref:** `segment4/price_agents/deals.py` cho Pydantic pattern

---

### Step 2: API Client
**File:** `shopee_scraper/api_client.py`

Dung `curl_cffi` voi `impersonate="chrome"` (giong `bestbuy_deals.py`):

```python
def init_shopee_session() -> Session:
    session = curl_requests.Session(impersonate="chrome")
    session.headers.update({
        "Referer": "https://shopee.vn",
        "X-Requested-With": "XMLHttpRequest",
        "X-API-SOURCE": "pc",
    })
    # Visit homepage de lay cookies
    session.get("https://shopee.vn", timeout=15)
    return session
```

- Retry logic: exponential backoff (1s, 2s, 4s), max 3 retries
- Neu HTTP 403/429: save checkpoint, doi 5 phut, tao session moi
- Tao session moi moi 500 requests (cookie rotation)

**Ref:** `segment4/price_agents/bestbuy_deals.py:56-60` cho curl_cffi session pattern

---

### Step 3: Search Module
**File:** `shopee_scraper/search.py`

Endpoint chinh: `https://shopee.vn/api/v4/search/search_items`

Parameters:
- `keyword`: tu khoa tim kiem
- `limit`: 60 (max per page)
- `newest`: offset (0, 60, 120, ...)
- `by`: "relevancy"
- `order`: "desc"
- `page_type`: "search"
- `scenario`: "PAGE_GLOBAL_SEARCH"

```python
def search_shopee(session, keyword, max_pages=50, price_min=50000, price_max=2000000) -> list[dict]:
    """Search Shopee, paginate, return list of {item_id, shop_id, name, price} dicts."""
```

- Paginate bang `newest += 60` moi trang
- Dung cho toi khi `items` rong hoac dat max_pages
- Random delay 2-3.5s giua cac trang
- Log progress moi 10 trang

---

### Step 4: Product Detail Module
**File:** `shopee_scraper/product_detail.py`

Endpoint: `https://shopee.vn/api/v4/item/get?itemid={item_id}&shopid={shop_id}`

```python
def get_product_detail(session, shop_id, item_id) -> Optional[ShopeeProduct]:
    """Fetch full product detail, return ShopeeProduct or None."""
```

Data extraction:
- `price = item["price"] / 100_000`
- `brand`: tim trong `attributes` array, key "Thuong hieu"
- `features`: join tat ca attributes thanh string
- `description`: truong `description`
- `category`: join `categories[].display_name` bang " > "
- `url`: `https://shopee.vn/{slug}-i.{shop_id}.{item_id}`
- `weight`: tu `item.get("weight", 0) / 1000` (gram -> kg)

Random delay 1-2s giua cac requests. Day la bottleneck chinh — 10K products ~ 3-6 gio.

---

### Step 5: Scraper Orchestrator
**File:** `shopee_scraper/scraper.py`

```python
def scrape_category(category_keyword, target_count=5000, checkpoint_dir="checkpoints/", output_dir="data/raw/") -> list[ShopeeProduct]:
    """Search -> get details -> save with checkpoints."""
```

Pipeline:
1. Search de lay list `(item_id, shop_id)` pairs
2. Filter gia trong khoang 50K-2M VND (tu search results)
3. Loop get_product_detail cho tung san pham
4. Save raw data dang JSONL (append mode): `data/raw/{keyword}_{date}.jsonl`
5. Checkpoint moi 100 products: `checkpoints/{keyword}_progress.json`
6. Neu bi block (403/429): save checkpoint, doi 5 phut, tao session moi, resume

Logging: ANSI color-coded giong `Agent` base class (`segment4/price_agents/agent.py`)

---

### Step 6: Test voi 1 category (VALIDATION GATE)
**File:** `scripts/01_scrape_category.py`

Chay thu voi keyword "tai nghe", target 500-1000 products.

**Kiem tra:**
- [ ] API co tra ve data khong?
- [ ] Price normalization dung (chia 100,000)?
- [ ] Description co du dai (>200 chars)?
- [ ] URL hop le, co the truy cap?
- [ ] Checkpoint hoat dong (resume duoc)?
- [ ] Rate limiting khong bi block?

**Neu bi block:** Chuyen sang Selenium+BS4 backup (doc Scraping_Data_Shopee_clip3.md)

---

### Step 7: Vietnamese Text Cleaning
**File:** `data_processing/parser_vn.py`

Tuong tu `parser.py` tieng Anh nhung adapt cho tieng Viet:

```python
def normalize_vietnamese(text: str) -> str:
    """NFC normalize Vietnamese Unicode (critical cho dau)."""
    return unicodedata.normalize("NFC", text)

def clean_shopee_text(text: str) -> str:
    """Remove Shopee-specific noise."""
    # 1. NFC normalization
    # 2. Remove emojis (rat nhieu tren Shopee VN)
    # 3. Remove marketing spam (###, ===, ***)
    # 4. Remove SKU/barcode patterns (regex tu English parser)
    # 5. Collapse whitespace
    return cleaned[:MAX_TEXT_TOTAL]

def parse_shopee(product: ShopeeProduct) -> Optional[ShopeeItem]:
    """Filter + clean. Return None neu khong dat tieu chuan."""
    # Check price range
    # Clean + concatenate title + description + features
    # Check min length (200 chars)
    # Return ShopeeItem or None
```

REMOVALS_VN: "Ma san pham", "Barcode", "SKU", "Ma vach", "Xuat xu thuong hieu"

**Ref:** English parser.py (Data_processing_for_English_data.txt lines 226-329)

---

### Step 8: Deduplication
**File:** `data_processing/dedup.py`

```python
# Dedup theo title (giong English pipeline)
seen = set()
items = [x for x in items if not (x.title in seen or seen.add(x.title))]
```

Them dedup theo `(title + 100 ky tu dau description)` de bat cac san pham trung tu nhieu seller.

---

### Step 9: EDA + Weighted Sampling
**Files:** `data_processing/eda.py`, `data_processing/sampling.py`

**EDA:** Matplotlib plots:
- Histogram phan phoi gia
- Histogram do dai mo ta
- Bieu do so luong theo category
- Scatter plot gia vs do dai

**Weighted Sampling** (giong English pipeline):
- `w = normalized_price ** 2` (boost hang dat)
- Penalize dominant categories (dieu chinh sau EDA)
- `np.random.choice(len(items), size=target, replace=False, p=w)`

Split:
- MVP: 15K train / 2K val / 2K test (total ~19K)
- Lite: 5K train / 500 val / 500 test

**Ref:** English weighted sampling (Data_processing_for_English_data.txt lines 539-559)

---

### Step 10: Build ChromaDB tieng Viet
**File:** `chromadb_vn/build_db.py`

```python
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"  # Thay all-MiniLM-L6-v2
DB_PATH = "products_vectorstore_vn"
COLLECTION_NAME = "products_vn"
BATCH_SIZE = 256
```

**Luu y quan trong:** `multilingual-e5-base` can prefix:
- Documents: `"passage: {text}"`
- Queries: `"query: {text}"`

Khac voi `all-MiniLM-L6-v2` (khong can prefix).

Insert batches of 256, luu metadatas: `{price, category, title}`

**Ref:** `segment4/price_agents/frontier_agent.py:24` cho SentenceTransformer, `segment4/multi_source_framework.py:40` cho ChromaDB init

---

### Step 11: Validate ChromaDB
**File:** `chromadb_vn/test_search.py`

Test queries:
- "tai nghe bluetooth chong on"
- "noi com dien 1.8 lit"
- "laptop gaming RTX 4060"
- "may giat Samsung 9kg inverter"

Retrieve top 5, in ra kem gia, kiem tra relevance bang tay.

---

### Step 12: Push HuggingFace
**File:** `scripts/06_push_huggingface.py`

Dung `datasets.DatasetDict` + `push_to_hub()` giong English pipeline.

---

## Anti-Bot Strategy (thu tu uu tien)

1. **curl_cffi + impersonate="chrome"** (primary — da proven trong project)
2. **Headers**: Referer, X-API-SOURCE, X-Requested-With
3. **Random delays**: 2-3.5s search, 1-2s detail (KHONG dung interval co dinh)
4. **Cookie rotation**: Session moi moi 500 requests
5. **Checkpoint + resume**: Neu 403/429, save state, doi 5 phut, retry
6. **Fallback**: Selenium+BS4 neu API bi block hoan toan
7. **Scale-up**: Rotating proxy VN IP khi thue may manh

---

## Execution Order

| # | Script/Task | Thoi gian code | Thoi gian chay | Dieu kien |
|---|------------|---------------|----------------|-----------|
| 1 | models.py + config.py | ~30 phut | - | - |
| 2 | api_client.py | ~30 phut | - | Step 1 |
| 3 | search.py + product_detail.py | ~1-2 gio | - | Step 2 |
| 4 | scraper.py (orchestrator) | ~1 gio | - | Step 3 |
| 5 | 01_scrape_category.py (test "tai nghe" 500sp) | - | ~1-2 gio | Step 4 |
| 6 | **VALIDATION GATE**: kiem tra data quality | ~30 phut | - | Step 5 |
| 7 | parser_vn.py + dedup.py | ~1 gio | - | Step 6 OK |
| 8 | 02_scrape_all.py (10 categories) | - | ~10-20 gio | Step 6 OK |
| 9 | 03_clean_and_filter.py | - | ~10-30 phut | Step 8 |
| 10 | eda.py + sampling.py | ~1 gio | - | Step 9 |
| 11 | 04_dedup_and_sample.py | - | ~5-10 phut | Step 10 |
| 12 | build_db.py + 05_build_chromadb.py | ~1 gio | ~1-2 gio | Step 11 |
| 13 | test_search.py (validate) | - | ~15 phut | Step 12 |
| 14 | 06_push_huggingface.py | ~30 phut | ~10 phut | Step 13 OK |

**Tong thoi gian code:** ~7-9 gio
**Tong thoi gian chay (scraping):** ~12-24 gio (phu thuoc toc do mang + rate limit)

---

## Dependencies

Tat ca dependencies da co trong project (`curl_cffi`, `beautifulsoup4`, `chromadb`, `sentence-transformers`, `datasets`, `tqdm`, `pydantic`). Chi can them:
- `uv add matplotlib` (cho EDA plots, neu chua co)

Embedding model doi tu `all-MiniLM-L6-v2` sang `intfloat/multilingual-e5-base` — khong can thay doi package, chi doi model name string.

---

## Verification

Sau khi hoan thanh, kiem tra:
1. `data/raw/` co JSONL files voi raw products
2. `data/cleaned/` co JSONL sau khi clean
3. `data/final/` co train.jsonl, val.jsonl, test.jsonl
4. ChromaDB `products_vectorstore_vn/` co du products
5. `test_search.py` tra ve ket qua relevant cho cac query tieng Viet
6. Dataset da push len HuggingFace Hub
7. EDA plots cho thay phan phoi gia va category hop ly
