# Plan: Tien xu ly du lieu tieng Viet cho bai toan du doan gia

**Ngay tao:** 2026-04-09
**Cap nhat:** 2026-04-10
**Branch:** `feature/data-preprocessing-vi`
**Muc tieu:** Thu thap va tien xu ly 150K+ SP tieng Viet (9 categories, moi cat >= 10K) → dataset chuan cho training
**Ngan sach LLM rewrite:** ~$10-15 (Groq Batch API)

---

## 1. Tong quan

### 1.1. Thay doi so voi plan cu

**Van de phat hien sau Day 1 EDA (2026-04-10):**
- Thoi Trang chiem 33% dataset (mat can bang nghiem trong)
- Kaggle data chat luong thap (features ngan 188 chars, brand chung)
- 3 categories qua it: Dien Tu Dien Lanh (1K), Nha Sach (1.7K), O To (2.4K)
- Gap lon nhat/nho nhat: 39x
- Penalty khong hieu qua vi sample 110K/114K = 96% (khong du room)

**Quyet dinh:**
- Cao them du lieu tu Tiki (73 categories chua cao) + cac trang khac (scraper co san + scraper moi)
- Gop categories: Dien Gia Dung + Dien Lanh, Phu kien TT + Thoi Trang, Do Choi + Me va Be
- Bo: Nha Sach Tiki (sach khong phai hang tieu dung), The Thao (chi 228 SP)
- Giam TRAIN_SIZE xuong 80K, cho room penalty hoat dong
- Target: **9 categories, moi cat >= 10K** (tru O To chap nhan nho hon)

### 1.2. Du lieu hien co (Day 1 da chay)

| Nguon | Files | SP | Ghi chu |
|---|---:|---:|---|
| Tiki Scraper (49 cat) | 48 JSONL | 79,382 | Features dai, chat luong tot |
| Tiki Kaggle (6 files) | 6 JSONL | 41,603 | Features ngan (188 chars), brand chung |
| **Tong** | **54** | **120,985** | Sau dedup: 114,778 |

### 1.3. Du lieu can them

| Uu tien | Nguon | Uoc tinh SP | Cach lam | Thoi gian |
|---:|---|---:|---|---|
| 1 | **Tiki** — 73 categories chua cao | ~32K (yield ~9K) | Da co scraper, chi can them config | 1-2 ngay |
| 2 | **Scraper co san** — Hasaki, Cocoshop, BiboMart, ConCung, KidsPlaza, CoopMart, WinMart, BachHoaXanh | ~30-50K | Convert output CSV → JSONL, test + chay | 2-3 ngay |
| 3 | **Scraper moi** — TGDD, FPT, Meta.vn, Dien May Xanh | ~20-40K | Viet scraper tu dau | 3-5 ngay/trang |

### 1.4. 9 Categories muc tieu

| # | Category | Hien co | Them Tiki | Them trang khac | Muc tieu |
|---:|---|---:|---:|---|---:|
| 1 | **Thoi Trang** (gop Phu kien TT + Tui Vi) | 42,032 | +14K TT Nam/Nu, +3K Tui Vi | -- | 15K (sample) |
| 2 | **Nha Cua - Doi Song** | 25,644 | +3K Ve sinh nha cua | -- | 15K (sample) |
| 3 | **Dien Tu - Cong Nghe** (Laptop + Thiet Bi So) | 22,648 | -- | -- | 15K (sample) |
| 4 | **Lam Dep - Suc Khoe** | 5,874 | +9.4K (Massage, TPCN, Trang diem) | Hasaki, Cocoshop | 15K+ |
| 5 | **Dien Tu - Dien Lanh + Dien Gia Dung** (gop) | 5,639 | +617 | TGDD, FPT, Meta.vn, Dien May Xanh | 10K+ |
| 6 | **Me va Be** (gop Do Choi) | 4,467 | -- | BiboMart, ConCung, KidsPlaza | 10K+ |
| 7 | **Bach Hoa** | 4,362 | +1.7K (ruou, sua, ngu coc) | CoopMart, WinMart, BachHoaXanh | 10K+ |
| 8 | **O To - Xe May** | 2,441 | +399 | -- | ~3K (chap nhan nho) |
| 9 | (Du phong — TGDD/FPT co the tach "Dien Thoai" rieng neu du data) | 0 | -- | TGDD, FPT | 10K+ |

**Bo:** Nha Sach Tiki (1,671 — sach), The Thao (228 — qua it)

### 1.5. Folder structure (cap nhat)

```
scraping_data_tv/
    Tiki/                          # Tiki scraper (49 cat done + them 73 cat)
    e-commerce-sites-scraping/     # Scraper co san (Hasaki, CoopMart, BiboMart...)
    Data_processing_for_Vietnamese_data/
        plan_data_preprocessing_vi.md    # File nay
        pricer_vi/                       # Package chinh
            __init__.py
            parser.py                    # Vietnamese text cleaning (9 steps)
            items.py                     # Pydantic Item model (VND)
            preprocessor.py              # Day 2: LLM rewrite
            batch.py                     # Day 2: Batch processing
            evaluator.py                 # Day 4: MAE + MAPE
        day1_data_curation.py            # Day 1: Load, EDA, filter, dedup, split
        day1_data_curation.ipynb         # Day 1: Interactive notebook
        day2_llm_preprocessing.py        # Day 2: LLM rewrite
        day3_baseline_ml.py              # Day 3: Baseline + Traditional ML
        day4_neural_networks.py          # Day 4: DNN + Frontier LLM
```

### 1.6. Du lieu dau ra (muc tieu cap nhat)

- ~120-150K SP sau dedup va loc (tang tu 110K)
- 9 categories, moi cat >= 10K (tru O To ~3K)
- Split: **80K train / 5K val / 5K test** (giam tu 100K train)
- Category penalties: Thoi Trang 0.4, Nha Cua 0.7
- Format: prompt-completion cho SFT
- Push len HuggingFace Hub: `SeanSunny/items_raw_tv`

### 1.7. Evaluation metrics

- **MAE (VND):** Sai so tuyet doi trung binh
- **MAPE (%):** Sai so phan tram trung binh
- Dung ca hai de danh gia cong bang giua SP re va dat

---

## 2. Cac buoc thuc hien

### Day 0: Thu thap them du lieu (MOI — truoc Day 1)

**Muc tieu:** Tang dataset tu 121K → 150K+ SP, can bang 9 categories.

#### 0a. Uu tien 1 — Tiki (73 categories chua cao)

Da co scraper (`scraping_data_tv/Tiki/`), chi can them categories vao `config.py` va chay.

**Tiki categories can them:**

**Thoi Trang Nam (parent 931) — ~9.1K uoc tinh:**

| ID | Name | Uoc tinh |
|---:|---|---:|
| 4554 | Do lot nu | 3,310 |
| 1508 | Do ngu - Do mac nha nu | 1,110 |
| 941 | Dam nu | 1,050 |
| 936 | Ao vest - Ao khoac nu | 870 |
| 933 | Ao thun nu | 573 |
| 27600 | Quan nu | 472 |
| 935 | Ao kieu nu | 377 |
| 6179 | Trang phuc boi nu | 318 |
| 934 | Ao so mi nu | 267 |
| 5404 | Chan vay | 265 |
| 1702 | Ao lien quan - Bo trang phuc | 264 |
| 4553 | Do doi - Do gia dinh | 94 |
| 49384 | Thoi trang nu trung nien | 56 |
| 10389 | Ao crop-top | 54 |

**Thoi Trang Nu (parent 915) — ~5.1K uoc tinh:**

| ID | Name | Uoc tinh |
|---:|---|---:|
| 917 | Ao thun nam | 1,541 |
| 918 | Ao so mi nam | 856 |
| 925 | Ao vest - Ao khoac nam | 761 |
| 27548 | Do lot nam | 534 |
| 27562 | Quan dai nam | 492 |
| 67329 | Quan short nam | 380 |
| 10382 | Ao hoodie nam | 136 |
| 67309 | Bo trang phuc nam | 134 |
| 4546 | Ao ni - Ao len nam | 114 |
| 16004 | Do boi nam | 82 |
| 27570 | Do ngu nam | 68 |

**Tui - Vi - Balo (parent 6000) — ~2.9K uoc tinh:**

| ID | Name | Uoc tinh |
|---:|---|---:|
| 27608 | Balo | 1,589 |
| 8387 | Tui du lich va phu kien | 581 |
| 6526 | Vali, phu kien vali | 514 |
| 27612 | Balo, cap, tui chong soc laptop | 195 |
| 68140 | Phu kien du lich | 53 |

**Lam Dep - Suc Khoe (tu Bach hoa online 1520) — ~9.4K uoc tinh:**

| ID | Name | Uoc tinh |
|---:|---|---:|
| 2307 | May Massage va Thiet bi cham soc suc khoe | 3,370 |
| 2322 | Thuc pham chuc nang | 2,924 |
| 5873 | San pham thien nhien va Khac | 1,275 |
| 1584 | Trang diem | 1,223 |
| 1625 | Cham soc rang mieng | 576 |

**Bach Hoa (tu Dien gia dung 4384) — ~1.6K uoc tinh:**

| ID | Name | Uoc tinh |
|---:|---|---:|
| 53582 | Ruou, bia va nuoc len men | 849 |
| 53562 | Sua va cac San pham tu sua | 493 |
| 68576 | Ngu coc va mut | 141 |
| 24024 | Do Uong Khong Con | 106 |

**Dien Tu - Dien Lanh (parent 4221) — ~617 uoc tinh:**

| ID | Name | Uoc tinh |
|---:|---|---:|
| 3868 | Tu dong - Tu mat | 350 |
| 8074 | Phu kien dien lanh | 217 |
| 3863 | May say quan ao | 50 |

**Ve sinh nha cua (tu Suc khoe 15078) — ~3K uoc tinh:**

| ID | Name | Uoc tinh |
|---:|---|---:|
| 4399 | Ve sinh nha bep | 1,401 |
| 4400 | Ve sinh nha tam | 511 |
| 4387 | Giat giu va Cham soc quan ao | 474 |
| 4388 | Giay ve sinh va giay an | 275 |
| 4386 | Ve sinh nha cua | 243 |
| 4441 | Diet con trung | 104 |

**O To - Xe May (parent 8594) — ~389 uoc tinh:**

| ID | Name | Uoc tinh |
|---:|---|---:|
| 8597 | Xe may | 270 |
| 6070 | Xe dien | 119 |

**Tong Tiki them:** ~32K uoc tinh → yield 28% → ~9K thuc te

**Cach thuc hien:**
1. Them categories vao `config.py`
2. Chay `run_scraper.py --all --workers 3` (tren may thue hoac may ca nhan)
3. Uoc tinh thoi gian: 2.7 SP/s × 3 workers → ~32K SP trong ~3-4 gio
4. Convert output vao cung folder `Tiki_dataset_scrape/`

#### 0b. Uu tien 2 — Scraper co san (e-commerce-sites-scraping)

Code tai `scraping_data_tv/e-commerce-sites-scraping/`. Dung Selenium + Requests + BeautifulSoup.

**Output hien tai:** CSV format:
```
product_name, image, cat_l0, cat_l1, cat_l2, cat_l3, barcode, brand, 
manufacturer, capacity, effect, price, source, href
```

**Can convert sang JSONL:** title, price, features, brand, category (giong Tiki).

| Trang | Category map | Tech | Uu tien |
|---|---|---|---|
| **Hasaki** | Lam Dep - Suc Khoe | Requests (JSON API) | Cao |
| **Cocoshop** | Lam Dep - Suc Khoe | Requests | Cao |
| **BiboMart** | Me va Be | Requests | Cao |
| **ConCung** | Me va Be | Requests | Cao |
| **KidsPlaza** | Me va Be | Selenium + Requests | Cao |
| **CoopMart** | Bach Hoa | Selenium | Trung binh |
| **WinMart** | Bach Hoa | Selenium (infinite scroll) | Trung binh |
| **BachHoaXanh** | Bach Hoa | Selenium | Trung binh |
| **FujiMart** | Bach Hoa | Requests | Trung binh |
| **ThiTruongSi** | Bach Hoa | Requests (JSON API) | Thap (B2B, gia si) |

**Cach thuc hien:**
1. Test tung scraper: chay 1 category, kiem tra output
2. Viet script convert CSV → JSONL (map fields)
3. Chay full scraper cho cac trang uu tien cao
4. Merge vao `Tiki_dataset_scrape/` voi prefix (VD: `hasaki_*.jsonl`, `bibomart_*.jsonl`)

**Luu y:** Code dung `selenium` + `webdriver-manager` — can cai Chrome + ChromeDriver.

#### 0c. Uu tien 3 — Scraper moi (nghien cuu sau)

| Trang | Category map | Do kho | Ghi chu |
|---|---|---|---|
| **The Gioi Di Dong** (thegioididong.com) | Dien Tu - Dien Lanh + DGD, Dien Thoai | Trung binh | HTML parsing, nhieu SP |
| **FPT Shop** (fptshop.com.vn) | Dien Tu - Dien Lanh + DGD, Dien Thoai | Trung binh | HTML parsing |
| **Meta.vn** | Dien Tu - Dien Lanh + DGD | Trung binh | Aggregator, nhieu nguon |
| **Dien May Xanh** (dienmayxanh.com) | Dien Tu - Dien Lanh + DGD | Trung binh | Cung he thong TGDD |
| **Shopee** | Nhieu categories | Cao (anti-bot manh) | Da quyet dinh khong lam |

**Cach thuc hien:** Viet scraper moi dung `curl_cffi` + BeautifulSoup (giong Tiki scraper).

**Tieu chi hoan thanh Day 0:**
- [ ] Them 73 Tiki categories vao config, chay scraper
- [ ] Test + chay scraper co san (Hasaki, BiboMart, CoopMart...)
- [ ] Convert CSV → JSONL
- [ ] (Neu can) Viet scraper moi cho TGDD/FPT
- [ ] Tong du lieu >= 150K SP, 9 categories can bang

---

### Day 1: Data Curation (Tuyen chon du lieu) — DA CHAY, CAN RE-RUN

**Muc tieu:** Load tat ca JSONL files → clean → dedup → EDA → split → push HF Hub

**Thay doi so voi lan chay truoc:**
- Them data tu Day 0 (Tiki them + trang khac)
- Gop categories: Dien Gia Dung + Dien Lanh, Phu kien TT + Thoi Trang, Do Choi + Me va Be
- Bo: Nha Sach Tiki, The Thao
- TRAIN_SIZE = 80,000 (giam tu 100K)
- Category penalties: Thoi Trang 0.4, Nha Cua 0.7
- Gop Laptop-MVTLK + Thiet Bi So → "Dien Tu - Cong Nghe"

**Pipeline:** Load → Clean (9-step) → Category mapping → Dedup → EDA → Weighted sampling (penalty) → Split → Push HF

**Category mapping logic (trong parser hoac day1_data_curation.py):**

```python
CATEGORY_MAP = {
    # Gop Dien Tu - Dien Lanh + Dien Gia Dung
    "Điện Tử - Điện Lạnh": "Dien Tu - Dien Lanh va Gia Dung",
    "Điện Gia Dụng": "Dien Tu - Dien Lanh va Gia Dung",
    # Gop Phu kien TT vao Thoi Trang
    "Phụ kiện thời trang": "Thoi Trang",
    "Thời Trang": "Thoi Trang",
    # Gop Do Choi + Me va Be
    "Đồ Chơi - Mẹ & Bé": "Me va Be",
    # Gop Laptop + Thiet Bi So
    "Laptop - Máy Vi Tính - Linh kiện": "Dien Tu - Cong Nghe",
    "Thiết Bị Số - Phụ Kiện Số": "Dien Tu - Cong Nghe",
    # Giu nguyen
    "Nhà Cửa - Đời Sống": "Nha Cua - Doi Song",
    "Làm Đẹp - Sức Khỏe": "Lam Dep - Suc Khoe",
    "Bách Hóa Online": "Bach Hoa",
    "Ô Tô - Xe Máy - Xe Đạp": "O To - Xe May",
    # Bo
    "Nhà Sách Tiki": None,  # Bo
}
# Cac trang khac (Hasaki, BiboMart, CoopMart...) → map theo category tuong ung
```

**Tieu chi hoan thanh Day 1 (cap nhat):**
- [ ] Load thanh cong 150K+ SP (bao gom data moi)
- [ ] Category mapping 9 categories
- [ ] Lam sach + dedup → ~120-140K SP
- [ ] EDA report (bieu do phan phoi 9 categories)
- [ ] Penalty: Thoi Trang 0.4, Nha Cua 0.7
- [ ] Split 80K/5K/5K — khong co data leakage
- [ ] Push dataset len HuggingFace Hub

---

### Day 2: LLM Preprocessing (Tien xu ly bang LLM)

(Giu nguyen nhu plan cu — xem chi tiet trong commit truoc)

**Muc tieu:** Dung LLM rewrite descriptions thanh format chuan, ngan gon, dong nhat

**SYSTEM_PROMPT tieng Viet:**
```
Tieu de: Viet lai tieu de ngan gon chinh xac
Danh muc: VD Dien tu
Thuong hieu: Ten thuong hieu
Mo ta: 1 cau mo ta san pham
Thong so: 1 cau ve tinh nang/thong so noi bat
```

**Model:** Test tren Groq: qwen-qwq-32b, llama-3.3-70b, gemma2-9b → chon tot nhat
**Batch:** Groq Batch API, 1000 SP/batch, ~$10-15 cho 120K SP

**Tieu chi hoan thanh Day 2:**
- [ ] SYSTEM_PROMPT tieng Viet da test va chon
- [ ] Chon model tot nhat cho tieng Viet
- [ ] Batch processing thanh cong
- [ ] Push dataset co summary len HuggingFace Hub

---

### Day 3: Baseline Models & Traditional ML

(Giu nguyen nhu plan cu)

**Models:** Random, Mean, Median, Linear Regression, XGBoost, LightGBM, CatBoost
**Metrics:** MAE (VND), MAPE (%), MSE, R2

---

### Day 4: Neural Networks & Frontier LLMs

(Giu nguyen nhu plan cu)

**Models:** DNN ResidualBlock (Vietnamese_Embedding 1024d), PhoBERT (optional), Qwen3-8B + RAG

---

## 3. Nghien cuu (giu nguyen — xem plan cu)

- Vietnamese NLP dac thu (Section 3a-3f cua plan cu)
- Embedding models cho tieng Viet
- ML/DL models phu hop
- Qwen3.5 fine-tune

---

## 4. Tech stack (cap nhat)

| Thanh phan | Cong nghe |
|---|---|
| Package manager | uv |
| Tiki scraper | curl_cffi + BeautifulSoup (da co) |
| E-commerce scrapers | Selenium + Requests + BeautifulSoup (da co) |
| Data loading | json, pathlib |
| EDA | pandas, matplotlib |
| NLP tieng Viet | underthesea, unicodedata |
| Text embeddings | AITeamVN/Vietnamese_Embedding (1024d) |
| ML models | scikit-learn, xgboost, lightgbm, catboost |
| DNN | PyTorch |
| LLM rewrite | Groq Batch API (litellm) |
| Frontier LLM | Qwen3-8B / GPT-5-nano |
| LLM fine-tune | Qwen3.5-4B-Base (LoRA bf16 via Unsloth) |
| Dataset hub | HuggingFace datasets |

---

## 5. Uoc tinh thoi gian va chi phi (cap nhat)

| Buoc | Thoi gian code | Thoi gian chay | Chi phi |
|---|---|---|---|
| **Day 0: Thu thap them** | 1-2 ngay | 4-8 gio (scraping) | ~$5 (may thue) |
| Day 1: Data Curation (re-run) | 1-2 gio | 5-10 phut | 0 |
| Day 2: LLM Preprocessing | 2-3 gio | 2-4 gio (batch) | ~$10-15 |
| Day 3: Baseline ML | 2-3 gio | 10-30 phut | 0 |
| Day 4: DNN + Frontier LLM | 3-4 gio | 1-2 gio (GPU) | GPU + API |
| **Tong** | **~3-5 ngay** | **~8-15 gio** | **~$15-25** |

---

*Cap nhat: 2026-04-10. Them Day 0 (thu thap du lieu). 9 categories muc tieu. Uu tien: Tiki → scraper co san → scraper moi.*
