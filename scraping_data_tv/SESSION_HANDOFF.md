# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-16)

**Trang thai:** Day 4 v4 DA CHAY (best 0.4986). v5 PLAN — 3 huong cai thien (fix PhoBERT normalize, PhoBERT embed+LGB, blending). Target 0.40 CHUA DAT.
**Branch:** `feature/data-preprocessing-vi`

### Da hoan thanh:
- [x] Tiki scraper — 111/113 categories, 102,117 SP
- [x] Kaggle CSV → JSONL — 41,603 SP (6 files thoi trang)
- [x] Hasaki scraper — 128/130 categories, 11,410 SP
- [x] WinMart scraper — 18 categories, 3,232 SP (API discovery + scraper)
- [x] Day 1 v1-v4: iterate pipeline, chot v4 config
- [x] HF dataset `SeanSunny/items_raw_tv_v4` da push (120K items raw)
- [x] **Day 2 HOAN TAT:** 120K items rewrite thanh cong (6h, $5)
  - LLM (gpt-oss-20b) tao Mo ta + Thong so, title/category/brand tu data goc
  - Dataset: `SeanSunny/items_tv_v6`
- [x] **Day 3 v2 HOAN TAT:** 9 baseline models, filtered <= 1M VND
  - Data: 85K train / 3.9K val / 3.9K test (tu 120K, filter <= 1M)
  - Best: **LightGBM RMSLE=0.5799**, MAE=114K, MAPE=59.7%, R2=52%
- [x] **Day 3 v3 HOAN TAT:** ML optimization (12 models, 3,872 test items)
  - Log-transform + Arch C (word+char_wb) + Category + Optuna + Blending
  - Best: **Blended RMSLE=0.5164**, MAE=110K, MAPE=44.0%, R2=47.1%
  - RMSLE ~0.52 la gioi han cua TF-IDF approach. Can dense embeddings
- [x] **Day 4 PLAN + CODE DA TAO:** 12 DL experiments + 3 Frontier LLM
  - Plan chi tiet: `day4/plan_day4.md`
  - Code: `day4/day4_dl_models.py/.ipynb` + `day4/day4_frontier_llm.py/.ipynb`
  - Model classes: `pricer_vi/deep_neural_network.py`

### Dang lam / Buoc tiep:
- [x] **Day 4 Phase 2:** Model 0 DNN bag-of-words (3 experiments) — Best: 0a RMSLE=0.5066
- [x] **Day 4 Phase 3:** Model 2/4/5 embedding-based (6 experiments) — Best: 2b RMSLE=0.4986
- [x] **Day 4 Phase 4:** Model 1 PhoBERT fine-tune — RMSLE=0.5268 (THAT VONG)
- [x] **Day 4 Phase 5:** Model 3 XLM-R fine-tune — RMSLE=0.5170 (ngang Day 3)
- [ ] **Day 4 Phase 6:** Frontier LLM (3 models, 200 items) — chua chay
- [x] **Day 4 Phase 7:** Tong hop — Best DL=0.4986, cai thien 3.4%
- [ ] **Day 4 v5:** 3 huong cai thien (fix PhoBERT normalize+mean pooling, PhoBERT embed→LGB+PCA, blending)

### Day 4 — 12 DL Experiments (DA CHAY XONG)

| # | Model | Ky vong RMSLE | Thuc te RMSLE | Ghi chu |
|---|-------|---------------|---------------|---------|
| 0a | DNN + HashingVec (h=2048) | 0.48-0.52 | 0.5066 | HashingVec bat ngo tot hon TF-IDF |
| 0b | DNN + TF-IDF (h=2048) | 0.48-0.52 | 0.5458 | Overfitting nang (train 0.07 vs val 0.50) |
| 0c | DNN + TF-IDF (h=4096) | 0.46-0.50 | 0.5212 | 309M params khong giup |
| **1** | **PhoBERT-v2 fine-tune** | **0.38-0.44** | **0.5268** | **THAT VONG** — 3 epochs, khong normalize target |
| 2a | dangvantuan embed + MLP | 0.42-0.48 | 0.5256 | Frozen embed = TF-IDF level |
| **2b** | **AITeamVN embed + MLP** | **0.42-0.48** | **0.4986** | **BEST DL** — AITeamVN 1024d > dangvantuan 768d |
| 3 | XLM-R fine-tune | 0.40-0.46 | 0.5170 | Ngang Day 3, MAPE=51% cao |
| 4a | dangvantuan embed + LightGBM | 0.40-0.46 | 0.5685 | LGB kem tren dense embedding |
| 4b | AITeamVN embed + LightGBM | 0.40-0.46 | 0.5612 | LGB kem tren dense embedding |
| 5a | dangvantuan embed + DNN ResBlock | 0.42-0.48 | 0.5414 | Deep network khong giup |
| 5b | AITeamVN embed + DNN ResBlock | 0.42-0.48 | 0.5038 | AITeamVN tot hon dangvantuan |

**Frontier LLM (200 items):** gpt-4o-mini, gpt-5-nano, gpt-5-mini — CHUA CHAY

### Quyet dinh da dua ra:
- Fine-tune: Qwen 3.5 4B (tot hon cho tieng Viet)
- Du lieu: Tiki 102K + Kaggle 42K + Hasaki 11K + WinMart 3.2K = 158K raw → 147K dedup → 120K sample
- Day 1 v4: TRAIN_SIZE=110K, total=120K (110K/5K/5K), HF=v4
- 8 categories (chot): Thoi Trang, Dien Tu Cong Nghe, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Lanh Gia Dung, O To Xe May
- Penalty: Thoi Trang 0.40, Nha Cua 0.60
- **Day 2:** LLM chi tao 2 truong (Mo ta + Thong so), title/category/brand lay tu data goc
- **Day 2:** Model: groq/openai/gpt-oss-20b, chi phi thuc te cho 120k san pham la 5$, thoi gian: 6h
- **Day 2:** Output dataset: SeanSunny/items_tv_v6
- **Day 3:** RMSLE lam primary metric (chuan Kaggle cho e-commerce price prediction)
- **Day 3:** Filter <= 1M VND (77.9% data). Ly do: phan phoi full dataset lech qua manh (skew=6.85)
- **Day 3:** So sanh Arch A (n-gram) vs B (underthesea): B tot hon, tat ca ensemble dung B
- **Day 3:** GPU treo voi sparse matrix → dung CPU cho tat ca models (XGBoost hist, CatBoost CPU)
- **Day 3 v2:** Best model: LightGBM RMSLE=0.5799 (cai thien 29% so voi Median baseline)
- **Day 3 v3:** Log-transform bat buoc cho RMSLE. Arch C can tuning moi tot. Blended RMSLE=0.5164
- **Day 3 v3:** RMSLE ~0.52 la gioi han cua TF-IDF approach. Can dense embeddings cho < 0.45
- **Day 4:** DNN hidden=2048 truoc, 4096 sau. TF-IDF tot hon HashingVec. h=4096 overfitting
- **Day 4:** May thue: RTX 4060 Ti 16GB VRAM, CUDA 13.1, PyTorch nightly cu130
- **Day 4:** Embedding: dangvantuan/vietnamese-embedding (768d) + AITeamVN/Vietnamese_Embedding (1024d)
- **Day 4:** Frontier LLM: prompt tieng Anh, 200 items, 3 model OpenAI
- **Day 4:** Chi chay .ipynb (khong .py) de tiet kiem chi phi may thue
- **Day 4:** Cache tat ca tokenized/embedding vao day4/*.pkl/*.npy
- **Day 4:** Loss function fix: L1Loss (MAE) → MSELoss (truc tiep optimize RMSLE). DA CHAY LAI THANH CONG
- **Day 4:** AITeamVN embedding (1024d, BGE-M3) > dangvantuan (768d, PhoBERT) o moi head
- **Day 4:** PhoBERT/XLM-R chi 3 epochs + khong normalize target → ket qua kem. Can tune lai
- **Day 4:** LightGBM kem tren dense embeddings (0.56-0.57) — can Optuna hoac khong phu hop
- **Day 4:** LGB record_evaluation keys: "training" (khong phai "valid_0"), metric "l2" (khong phai "mse")

### Ket qua du lieu:
- **Day 1 (v4):** 158K raw → 147K dedup → 120K sample (110K/5K/5K)
- **Day 2 (DONE):** 120K items, 0 missing, push `SeanSunny/items_tv_v6`
  - Summary: Tieu de/Danh muc/Thuong hieu (data goc) + Mo ta/Thong so (LLM)
  - Prompt: "San pham nay gia bao nhieu?\n\n[summary]\n\nGia: [price VND]"
- **Day 3 v2 (DONE):** Best: LightGBM RMSLE=0.5799, MAE=114K, MAPE=59.7%, R2=52% (200 items)
- **Day 3 v3 (DONE):** Best: Blended RMSLE=0.5164, MAE=110K, MAPE=44.0%, R2=47.1% (3,872 items)
  - Filter: <= 1M VND → 85K train / 3.9K val / 3.9K test
  - Log-transform + Arch C (word+char_wb) + Category + Optuna + Blending
- **Day 4 v4 DA CHAY (MSELoss):** 11 DL experiments. Best: AITeamVN+MLP RMSLE=0.4986
  - PhoBERT RMSLE=0.5268 (THAT VONG), XLM-R 0.5170 (ngang Day 3)
  - AITeamVN embedding tot hon dangvantuan o moi head
  - LightGBM kem tren dense embeddings (0.56-0.57)
  - Target 0.40 CHUA DAT. Can research huong moi

### Luu y ky thuat:
- Tiki API cap 2000 SP/category; dung Adaptive Price-Range Slicing de vuot
- WinMart API: `api-crownx.winmart.vn`, chi dung parent slugs
- **Day 3:** XGBoost/CatBoost GPU treo voi sparse matrix 85K x 10K → dung CPU
- **Day 3:** Underthesea KHONG thread-safe, phai pre-tokenize va luu cache .pkl
- **Day 3 v2:** LR predict am cho SP re → clip 0 → RMSLE cuc cao (1.75) du R2 tot (52.9%)
- **Day 3 v3:** Log-transform giai quyet LR negative. Ridge (0.5415) canh tranh voi ensemble
- **Day 4:** dangvantuan embedding can pyvi segment. AITeamVN khong can segment
- **Day 4:** PhoBERT can underthesea segment. XLM-R khong can segment
- **Day 4:** Loss fix: L1Loss → MSELoss trong train_torch_model (RMSLE = sqrt(MSE) trong log-space)
- **Day 4:** LightGBM eval_metric doi tu "l1" sang "mse" de monitor dung (objective mac dinh da la L2)
- **Day 4:** predict_batch: y_mean/y_std can .to(device) khi load tu checkpoint

### Moi truong chay:
- **May thue (ML/DL):** RTX 4060 Ti 16GB VRAM | i5-13400F 12C | 28GB RAM | CUDA 4352 (toi thieu)
  - Hoac RTX 3090 Ti 24GB VRAM | i5 14th Gen 18C | 88GB RAM | CUDA 10752
  - Thue 3-5 tieng/lan, co the thue nhieu lan. Moi lan co the may khac nhau.
- **May thue (Fine-tune QLoRA):** RTX 3090 24GB VRAM | i5-13400F 12C | 56GB RAM | CUDA 10496
  - Hoac GPU A100 tren Google Colab
- **Workflow:** git clone → uv sync → chay .ipynb → copy ket qua ve
- Moi lan thue may moi: can `uv sync` lai va tokenize sẽ được tải từ gg drive về

---

## Prompt dau tien cho session moi

### Prompt A: Day 4 v5 — Tao code cai thien (HIEN TAI)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md" — plan Day 4 (da trim, 290 dong)
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/" — tat ca file .py
3. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models.py" — code DL v4 (reference)
4. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_frontier_llm.py" — code Frontier LLM

Trang thai:
- Day 4 v4 DA CHAY: 12 DL experiments. Best: AITeamVN+MLP RMSLE=0.4986 (Day 3: 0.5164)
- Target 0.40 CHUA DAT. Root cause: PhoBERT target khong normalize (xem plan Section 2)
- Research xong: mean pooling > CLS, LoRA, PCA+LGB, gradual unfreezing (xem plan Section 3)

Buoc tiep: Tao file day4_dl_models_v5.ipynb voi 3 huong cai thien (xem plan Section 4):
1. Fix PhoBERT fine-tune (normalize target + mean pooling + early stopping) — ky vong 0.42-0.46
2. PhoBERT embedding → LGB + PCA + Optuna — ky vong 0.44-0.48
3. Blending best models — ky vong 0.43-0.47

Luu y:
- File .ipynb chay tren may thue (RTX 4060 Ti 16GB VRAM)
- Reuse cache tu v4: tokenized .pkl, embeddings .npy, model weights .pth
- Luon dung uv de chay code
```

### Prompt B: Day 4 — Phan tich ket qua v5 (SAU KHI CHAY)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md" — plan Day 4

Trang thai:
- Day 4 v5 DA CHAY XONG tren may thue. Day la ket qua:
[DAN KET QUA OUTPUT VAO DAY]

Hay phan tich ket qua va de xuat buoc tiep theo.
```

### Khi nao can doc them:
- **Tien xu ly du lieu**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md`
- **Ke hoach du an**: doc `segment4/mo_ta_du_an/Project_Development_Plan.md`
- **Ket qua Day 3**: doc `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md`

---

## Files quan trong

| File | Muc dich |
|------|----------|
| **DATA PROCESSING** | |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md` | Plan Day 0-4 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md` | Plan chi tiet Day 3 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md` | Plan chi tiet Day 4 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/` | Package chinh (items, parser, preprocessor, batch, evaluator, deep_neural_network) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models.py` | Day 4 DL script (12 experiments) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_frontier_llm.py` | Day 4 Frontier LLM script |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/day3_baseline_ml_1m_v3.py` | Day 3 v3 script |
| **ENGLISH REFERENCE** | |
| `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/pricer/deep_neural_network.py` | DNN English (tham khao) |
| `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/day4.txt` | Day 4 bai giang |
| **PROJECT** | |
| `segment4/mo_ta_du_an/Project_Development_Plan.md` | Ke hoach tong the |

---

## Lenh chay nhanh

```bash
cd tech2ai

# Setup may thue
uv sync && uv add transformers accelerate sentence-transformers pyvi litellm lightgbm

# Chay Day 4 DL (mo notebook)
# scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models.ipynb

# Chay Day 4 Frontier LLM (mo notebook)
# scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_frontier_llm.ipynb
```

---


*Cap nhat: 2026-04-16 — Day 0-3 HOAN TAT. Day 4 v4 DA CHAY (best 0.4986). v5 PLAN — 3 huong cai thien. Target 0.40.*
