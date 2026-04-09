# Plan: Tien xu ly du lieu tieng Viet cho bai toan du doan gia

**Ngay tao:** 2026-04-09
**Branch:** `feature/data-preprocessing-vi`
**Muc tieu:** Tien xu ly 121K SP tieng Viet → dataset chuan, san sang cho training
**Ngan sach LLM rewrite:** ~$10 (Groq Batch API)

---

## 1. Tong quan

### 1.1. Du lieu dau vao

| Nguon | Files | SP | Dac diem |
|---|---:|---:|---|
| Tiki Scraper | 48 JSONL | 79,382 | Features dai (3-5K chars), co brand, 49 categories |
| Tiki Kaggle | 6 JSONL | 41,603 | Features ngan (~188 chars), brand = ten the loai, 6 categories thoi trang |
| **Tong** | **54** | **120,985** | |

### 1.2. Du lieu dau ra (muc tieu)

- ~110K SP sau dedup va loc
- Split: **100K train / 5K val / 5K test**
- Format: prompt-completion cho SFT (tuong tu tieng Anh)
- Push len HuggingFace Hub
- Prompt format: `"San pham nay gia bao nhieu?\n\n{summary}\n\nGia: 299000"`

### 1.3. Evaluation metrics

- **MAE (VND):** Sai so tuyet doi trung binh — "model sai trung binh 500,000 VND"
- **MAPE (%):** Sai so phan tram trung binh — "model sai trung binh 10%"
- Dung ca hai de danh gia cong bang giua SP re va dat

### 1.4. Folder structure

```
scraping_data_tv/Data_processing_for_Vietnamese_data/
    plan_data_preprocessing_vi.md    # File nay
    pricer_vi/                       # Package chinh (tuong tu pricer/ tieng Anh)
        __init__.py
        parser.py                    # Load, filter, clean du lieu Tiki
        items.py                     # Pydantic Item model (VND)
        preprocessor.py              # LLM rewrite (Groq API)
        batch.py                     # Batch processing cho LLM rewrite
        evaluator.py                 # Danh gia MAE + MAPE
    day1_data_curation.py            # Day 1: Load, EDA, filter, dedup, split
    day2_llm_preprocessing.py        # Day 2: LLM rewrite descriptions
    day3_baseline_ml.py              # Day 3: Baseline + Traditional ML
    day4_neural_networks.py          # Day 4: DNN + Frontier LLM
```

---

## 2. Cac buoc thuc hien

### Day 1: Data Curation (Tuyen chon du lieu)

**Muc tieu:** Load 121K SP → clean → dedup → EDA → split train/val/test

#### 1a. Load du lieu

- Load tat ca 54 JSONL files tu `Tiki_dataset_scrape/`
- Chuan hoa fields: dam bao moi SP co `title`, `brand`, `price`, `features`, `category`
- Scraper data co them `product_id`, `url`, `category_id` — giu lai de dedup, bo khi training

#### 1b. Lam sach du lieu — TRUOC KHI LLM rewrite

**Tai sao xu ly truoc LLM rewrite?**
- Input sach → LLM output tot hon, it hallucinate
- Tiet kiem tien API — khong tra tien de LLM xu ly rac (emoji, HTML, SKU...)
- LLM tap trung vao viec tom tat, khong phai lam sach

**Khac biet so voi tieng Anh:**

| Tieu chi | Tieng Anh | Tieng Viet |
|---|---|---|
| Price range | $0.50 - $999.49 | **Giu tat ca** (0 - 50M VND) — khong loc gia |
| Min features | 600 chars | **Khong loc** — giu tat ca (Kaggle chi ~188 chars) |
| Max text | 4000 chars | 4000 chars (giu nguyen) |
| Unicode | ASCII | **NFC normalization** — chuan hoa dau tieng Viet |
| Removals | Part Number, Best Sellers Rank... | **SKU, barcode, ma san pham** |
| Emoji | Khong xu ly | **Xoa emoji** (Tiki data co nhieu) |
| Mixed text | English only | **Xu ly Viet-Anh lan lon** (pho bien tren Tiki) |
| HTML entities | Khong co | **Xoa** `&#x1f...` (co nhieu trong scraper data) |
| Title trung lap | Khong co | **Xoa title lap lai** o dau features |
| Separators | Khong co | **Xoa** `------`, `======` |

**Van de thuc te phat hien trong data Tiki (mau 50 SP/file x 54 files):**

| Van de | So luong | Vi du |
|---|---:|---|
| HTML entities (`&#x1f...`) | 433 | `&#x1f4e6` (emoji HTML encode) |
| SKU/ma san pham | 422 | `AURESEASY3`, `SLIM315RSVN`, `IEC60529` |
| Multi-spaces | 362 | `"mau trang,   mau den"` |
| Title lap lai trong features | 260 | Features bat dau bang chinh title |
| Emoji Unicode | 187 | Emoji trong mo ta san pham |
| Separators (`---`, `===`) | 88 | `"----------"` ngan cach sections |
| Features qua ngan (<50 chars) | 5 | Kaggle data |

**Pipeline lam sach (thu tu quan trong — xu ly tuan tu):**

```
1. Unicode NFC normalization
   - Chuan hoa dau tieng Viet (VD: ă [2 byte] → ă [1 byte])
   - Dung unicodedata.normalize('NFC', text)

2. Xoa HTML entities
   - Pattern: &#x[0-9a-f]+; va &[a-z]+;
   - VD: &#x1f4e6; → xoa

3. Xoa emoji Unicode
   - Regex range: \U0001F600-\U0001FAFF va cac block khac
   - Giu lai chu tieng Viet va tieng Anh

4. Xoa separators
   - Pattern: [-=]{5,} (5+ dau gach noi hoac bang)
   - VD: "----------" → xoa

5. Xoa SKU/ma san pham
   - Pattern: \b[A-Z0-9]{8,}\b (8+ ky tu hoa+so lien tuc)
   - Can than khong xoa tu viet hoa binh thuong

6. Xoa title lap lai o dau features
   - Neu features.startswith(title) → cat bo phan title
   - Tranh trung lap khi tao field `full`

7. Chuan hoa khoang trang
   - \n, \r, \t → space
   - Nhieu space → 1 space
   - Strip dau cuoi

8. Cat toi da 4000 chars
   - Giong MAX_TEXT_TOTAL trong parser.py tieng Anh

9. Tao field `full` = title + "\n" + features (cleaned)
   - Giong ham scrub() tieng Anh
   - Day la field se gui cho LLM rewrite
```

**Thu vien ho tro (tham khao, chua chac can dung het):**
- `vietnormalizer` — chuan hoa so, ngay, tien te, viet tat (pure Python, khong dependency)
- `underthesea` — tach tu, POS tagging (dung cho TF-IDF o Day 3)
- `unicodedata` — NFC normalization (built-in Python)

#### 1c. Deduplication

- Dedup theo `title` (normalize: lowercase, strip, remove extra spaces)
- Neu co `product_id` trung — uu tien SP co features dai hon
- Uoc tinh mat ~5-10% → ~110K SP

#### 1d. EDA (Exploratory Data Analysis)

- Phan phoi gia theo category (histogram)
- Phan phoi do dai features (histogram)
- Kiem tra mat can bang category (bar chart)
- Thong ke: min/max/avg price, features length, brand count
- So sanh chat luong Scraper vs Kaggle

#### 1e. Weighted Sampling

Ap dung tuong tu tieng Anh:
- **price² weighting** — de SP gia cao khong bi "chem" boi SP gia thap
- **Penalty category lon** — giam ty trong categories chiem da so (VD: Linh Kien May Tinh 9.6K, Phu kien thoi trang 16K)
- Dam bao phan phoi gia va category can bang

#### 1f. Split dataset

- **100K train / 5K val / 5K test**
- Stratified split theo category (dam bao moi category co mat trong ca 3 tap)
- Kiem tra khong co data leakage (SP trung giua train/val/test)
- Luu thanh 3 files: `train.jsonl`, `val.jsonl`, `test.jsonl`

**Tieu chi hoan thanh Day 1:**
- [ ] Load thanh cong 121K SP
- [ ] Lam sach + dedup → ~110K SP
- [ ] EDA report (bieu do phan phoi)
- [ ] Split 100K/5K/5K — khong co data leakage
- [ ] Push raw dataset len HuggingFace Hub

---

### Day 2: LLM Preprocessing (Tien xu ly bang LLM)

**Muc tieu:** Dung LLM rewrite descriptions thanh format chuan, ngan gon, dong nhat

#### 2a. Thiet ke SYSTEM_PROMPT tieng Viet

Adapt tu tieng Anh:
```
# Tieng Anh (goc):
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features

# Tieng Viet (adapt):
Tieu de: Viet lai tieu de ngan gon chinh xac
Danh muc: VD Dien tu
Thuong hieu: Ten thuong hieu
Mo ta: 1 cau mo ta san pham
Thong so: 1 cau ve tinh nang/thong so noi bat
```

**Luu y:** Output phai bang tieng Viet, khong dich sang tieng Anh.

#### 2b. Chon model cho LLM rewrite

**Uu tien tren Groq:**
- `gpt-oss-20b` — da dung thanh cong cho tieng Anh
- Cac model hieu tieng Viet tot tren Groq (can test):
  - `llama-3.3-70b-versatile` — da ngon ngu tot
  - `qwen-qwq-32b` — Qwen hieu tieng Viet tot
  - `gemma2-9b-it` — Google, multilingual

**Chien luoc:** Test 10-20 SP voi moi model → so sanh chat luong → chon model tot nhat

#### 2c. Batch processing (adapt tu batch.py)

- Batch size: 1000 SP/batch (giong tieng Anh)
- Groq Batch API: submit → poll → fetch output
- Retry logic cho failed batches
- Luu checkpoint moi batch (phong mat data)
- Uoc tinh: ~$10 cho 110K SP (reasoning_effort="low")

#### 2d. Ap dung summary

- Parse output LLM → field `summary`
- Kiem tra chat luong: co du 5 fields (Tieu de, Danh muc, Thuong hieu, Mo ta, Thong so)?
- Xu ly edge cases: LLM tra ve sai format, qua ngan, qua dai

**Tieu chi hoan thanh Day 2:**
- [ ] SYSTEM_PROMPT tieng Viet da test va chon
- [ ] Chon model tot nhat cho tieng Viet
- [ ] Batch processing 110K SP thanh cong
- [ ] Chat luong summary dat yeu cau (kiem tra mau)
- [ ] Push dataset co summary len HuggingFace Hub

---

### Day 3: Baseline Models & Traditional ML

**Muc tieu:** Thiet lap moc chuan (baselines) de so sanh voi DNN va LLM sau nay

#### 3a. Baseline models

| Model | Cach hoat dong | Muc dich |
|---|---|---|
| Random | Doan gia ngau nhien trong phan phoi | Moc thap nhat |
| Constant (mean) | Luon doan gia trung binh | Moc "khong hoc gi" |
| Constant (median) | Luon doan gia trung vi | Robust hon mean voi outliers |

#### 3b. Traditional ML

| Model | Features | Muc dich |
|---|---|---|
| Linear Regression | TF-IDF + category encoding + log(price) | Baseline ML |
| XGBoost | TF-IDF + metadata (brand, category, text length) | Strong baseline |

**Luu y cho tieng Viet:**
- TF-IDF can Vietnamese tokenizer — dung `underthesea` hoac `pyvi` de tach tu tieng Viet
- Hoac dung character n-grams (khong can tokenizer, hoat dong tot cho tieng Viet)

#### 3c. Evaluation

- Danh gia tren **test set** (5K SP)
- Metrics: MAE (VND) + MAPE (%) + MSE + R²
- So sanh bang + bieu do scatter (predicted vs actual)
- Error trend chart (giong evaluator.py tieng Anh)

**Tieu chi hoan thanh Day 3:**
- [ ] 4 baseline models da chay
- [ ] Evaluation report (bang so sanh + bieu do)
- [ ] XGBoost la strong baseline de so sanh voi DNN/LLM

---

### Day 4: Neural Networks & Frontier LLMs

**Muc tieu:** DNN va Frontier LLM cho du doan gia, so sanh voi baselines

#### 4a. DNN (Deep Neural Network)

Adapt tu `deep_neural_network.py` tieng Anh:

**Chon embedding model — 2 phuong an:**

| | **PA1: AITeamVN/Vietnamese_Embedding** | **PA2: dangvantuan/vietnamese-embedding** |
|---|---|---|
| Base | BAAI/bge-m3 | PhoBERT (RoBERTa) |
| Params | 568M | 135M |
| Dims | 1024 | 768 |
| Max tokens | 2048 | 512 |
| Pre-tokenize | Khong can | **Can `pyvi.ViTokenizer`** |
| STS Viet (Pearson) | Chua co benchmark | **88.33** (STSB-vn) |
| Retrieval Viet (Acc@1) | **0.727** (Legal Zalo) | Chua co benchmark |
| Downloads/thang | 350K | 235K |
| Uu diem | 1024d nhieu thong tin, max 2048 tokens xu ly text dai, khong can pre-tokenize | Nhe gap 4x (135M vs 568M), nhanh, it RAM |
| Nhuoc diem | Lon, ton RAM/GPU hon | Can pyvi, max 512 tokens (cat features dai) |
| Phu hop khi | GPU du manh (A100, RTX 3090+), data features dai | GPU han che, can toc do |

**Khuyen nghi:** PA1 (`AITeamVN/Vietnamese_Embedding`) — 1024 dims tot hon cho DNN regression, max 2048 tokens xu ly features dai, khong can pre-tokenize. Neu GPU/RAM han che thi dung PA2.

- **Kien truc:** Giu nguyen ResidualBlock network
- **Input:** text embedding (1024d hoac 768d) + metadata (category encoding, brand encoding, text length)
- **Output:** predicted price (VND)
- **Training:** GPU (Colab A100 hoac RTX 3090)

#### 4b. Frontier LLM (du doan gia truc tiep)

- Dung OpenAI GPT hoac Qwen qua API
- Prompt: gui mo ta SP → yeu cau doan gia VND
- Co the ket hop RAG (ChromaDB) de cung cap context
- So sanh: LLM alone vs LLM + RAG

#### 4c. So sanh tong hop

| Model | MAE (VND) | MAPE (%) | R² | Chi phi |
|---|---|---|---|---|
| Random | ? | ? | ? | 0 |
| Mean | ? | ? | ? | 0 |
| Linear Regression | ? | ? | ? | 0 |
| XGBoost | ? | ? | ? | 0 |
| DNN | ? | ? | ? | GPU |
| Frontier LLM | ? | ? | ? | API |
| Frontier LLM + RAG | ? | ? | ? | API |

**Tieu chi hoan thanh Day 4:**
- [ ] DNN trained va evaluated
- [ ] Frontier LLM tested (co/khong RAG)
- [ ] Bang so sanh day du tat ca models
- [ ] Chon model tot nhat lam baseline cho fine-tuning

---

## 3. Nghien cuu: Xu ly du lieu tieng Viet

### 3a. Vietnamese NLP — dac thu va cong cu

**Dac thu tieng Viet trong du lieu thuong mai dien tu:**

| Van de | Giai phap | Ghi chu |
|---|---|---|
| Tach tu (Word Segmentation) | `underthesea` hoac `pyvi` | Tieng Viet khong co space giua tu ghep ("may tinh" = 1 tu) |
| Unicode normalization | `unicodedata.normalize('NFC', text)` | `ă` co 2 bieu dien Unicode — can chuan hoa |
| Mixed Viet-Anh | Giu nguyen | Pho bien: "Smart TV 4K 55 inch", "Ao thun cotton" |
| Emoji | Xoa bang regex Unicode ranges | 187/2700 mau co emoji — gay nhieu cho model |
| HTML entities | Xoa `&#x...;` va `&amp;` | 433/2700 mau — tu scraper API |
| SKU/ma san pham | Regex `\b[A-Z0-9]{8,}\b` | 422/2700 mau — VD: `AURESEASY3`, `IEC60529` |
| Title lap lai | Cat bo neu features.startswith(title) | 260/2700 mau — title xuat hien 2 lan |
| Separators | Regex `[-=]{5,}` | 88/2700 mau — `"----------"` |
| Multi-spaces | Regex `\s+` → 1 space | 362/2700 mau |

**Thu vien NLP tieng Viet:**

| Thu vien | Chuc nang | Dependency | Khi nao dung |
|---|---|---|---|
| `vietnormalizer` | Chuan hoa so, ngay, tien te, viet tat tieng Viet | Pure Python, 0 deps | Khong can cho bai toan nay (LLM se tu hieu so/ngay) |
| `underthesea` | Tach tu, POS tag, NER, sentiment | Nhieu deps | Day 3: TF-IDF can tach tu |
| `pyvi` | Tach tu (nhe hon underthesea) | It deps | Fallback cho underthesea, hoac dung voi dangvantuan embedding |
| `unicodedata` | NFC normalization | Built-in Python | Day 1: lam sach data |

Sources:
- [VietNormalizer (arxiv)](https://arxiv.org/html/2603.04145v1)
- [Underthesea GitHub](https://github.com/undertheseanlp/underthesea)
- [NVIDIA LLM Data Preprocessing](https://developer.nvidia.com/blog/mastering-llm-techniques-data-preprocessing/)

**Chien luoc dedup (tu nghien cuu NVIDIA):**
- **Buoc 1 — Exact dedup:** Hash title (nhanh, bat trung 100%)
- **Buoc 2 — Fuzzy dedup:** Neu can, dung MinHash/LSH bat SP gan giong (VD: cung SP nhung title khac 1-2 tu)
- Buoc 2 chi lam neu exact dedup khong du — test truoc

### 3b. Embedding models cho tieng Viet

**So sanh chi tiet (da nghien cuu 2026-04-09):**

| Model | Base | Params | Dims | Max tokens | Pre-tokenize | Dac diem |
|---|---|---:|---:|---:|---|---|
| **AITeamVN/Vietnamese_Embedding** | bge-m3 | 568M | 1024 | 2048 | Khong | Retrieval tot nhat (Acc@1: 0.727 Legal Zalo) |
| **dangvantuan/vietnamese-embedding** | PhoBERT | 135M | 768 | 512 | Can `pyvi` | STS tot nhat (Pearson: 88.33 STSB-vn) |
| multilingual-e5-base | XLM-R | 278M | 768 | 512 | Khong | Da ngon ngu, khong toi uu cho VN |
| multilingual-e5-large | XLM-R | 560M | 1024 | 512 | Khong | Tot hon e5-base nhung cham |
| bkai-foundation-models/vietnamese-bi-encoder | PhoBERT | 135M | 768 | 256 | Khong | Chuyen VN nhung Acc@1 thap hon (0.711) |
| keepitreal/vietnamese-sbert | PhoBERT | 135M | 768 | 512 | Khong | STS Pearson: 84.51 |

**Benchmark Vietnamese:**

| Model | STS-vn Pearson | Legal Zalo Acc@1 |
|---|---:|---:|
| AITeamVN/Vietnamese_Embedding | - | **0.727** |
| dangvantuan/vietnamese-embedding | **88.33** | - |
| bkai-foundation-models/vietnamese-bi-encoder | 78.05 | 0.711 |
| keepitreal/vietnamese-sbert | 84.51 | - |
| multilingual-e5-base (BGE-M3) | - | 0.568 |

**Khuyen nghi:** `AITeamVN/Vietnamese_Embedding` (PA1) hoac `dangvantuan/vietnamese-embedding` (PA2).
Chi tiet so sanh 2 phuong an: xem Day 4, muc 4a.

Sources:
- https://huggingface.co/AITeamVN/Vietnamese_Embedding
- https://huggingface.co/dangvantuan/vietnamese-embedding

### 3c. Vietnamese tokenization cho TF-IDF

| Cach | Uu | Nhuoc |
|---|---|---|
| `underthesea.word_tokenize()` | Tach tu chinh xac | Cham, can cai them |
| `pyvi.ViTokenizer` | Nhanh hon | Kem chinh xac hon |
| Character n-grams (3-5) | Khong can tokenizer, robust | Khong hieu nghia tu |
| **Khuyen nghi:** Dung `underthesea` cho TF-IDF, character n-grams lam fallback |

### 3d. Gia VND — dac thu

- Range lon: 1,000 - 50,000,000 VND (gap 50,000 lan)
- **Nen dung log(price)** lam target cho regression — giam skew
- Khi evaluate: chuyen ve VND goc (exp) de tinh MAE/MAPE
- Prompt completion: van dung VND nguyen (`"Gia: 299000"`) — model hoc pattern so

---

## 4. Tech stack

| Thanh phan | Cong nghe |
|---|---|
| Package manager | uv |
| Data loading | json, pathlib |
| EDA | pandas, matplotlib/plotly |
| NLP tieng Viet | underthesea (tach tu), unicodedata (NFC) |
| Text embeddings | multilingual-e5-base (sentence-transformers) |
| TF-IDF | scikit-learn (TfidfVectorizer) |
| ML models | scikit-learn (LinearRegression), xgboost |
| DNN | PyTorch (ResidualBlock, giong tieng Anh) |
| LLM rewrite | Groq Batch API (litellm) |
| Frontier LLM | OpenAI GPT / Qwen (litellm) |
| Vector DB | ChromaDB (cho RAG) |
| Dataset hub | HuggingFace datasets |
| GPU training | Google Colab Pro (A100) / Vast.ai (RTX 3090/5090) |

---

## 5. Dependencies

```bash
# Da co trong project
curl_cffi pydantic tqdm litellm chromadb

# Can them
uv add underthesea sentence-transformers xgboost plotly
```

---

## 6. Uoc tinh thoi gian va chi phi

| Buoc | Thoi gian code | Thoi gian chay | Chi phi |
|---|---|---|---|
| Day 1: Data Curation | 2-3 gio | 5-10 phut | 0 |
| Day 2: LLM Preprocessing | 2-3 gio | 2-4 gio (batch) | ~$10 |
| Day 3: Baseline ML | 2-3 gio | 10-30 phut | 0 |
| Day 4: DNN + Frontier LLM | 3-4 gio | 1-2 gio (GPU) | GPU + API |
| **Tong** | **~10-13 gio** | **~4-7 gio** | **~$10-20** |

---

## 7. Rui ro va giai phap

| Rui ro | Giai phap |
|---|---|
| LLM rewrite tieng Viet kem chat luong | Test nhieu model truoc khi batch, co the can chinh SYSTEM_PROMPT |
| Groq Batch API limit/delay | Chia nho batch, retry logic, luu checkpoint |
| Mat can bang category (thoi trang chiem 34%) | Weighted sampling + stratified split |
| Features Kaggle qua ngan (188 chars) | LLM rewrite se chuan hoa — nhung summary van ngan hon Scraper |
| DNN khong hoi tu | Thu nhieu learning rates, dung log(price) lam target |

---

*Tao ngay: 2026-04-09. Buoc tiep: bat dau Day 1 — Data Curation.*
