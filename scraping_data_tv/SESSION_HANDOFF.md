# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-23)

**Trang thai:** v7 DA CHAY (0.4059, gap 0.0059). **v8 DA TAO CODE** — chua chay tren may thue.
**Branch:** `feature/data-preprocessing-vi`

### Da hoan thanh:
- [x] Tiki scraper — 111/113 categories, 102,117 SP
- [x] Kaggle CSV -> JSONL — 41,603 SP
- [x] Hasaki scraper — 128/130 categories, 11,410 SP
- [x] WinMart scraper — 18 categories, 3,232 SP
- [x] Day 1 v1-v4: iterate pipeline, chot v4 config
- [x] HF dataset `SeanSunny/items_raw_tv_v4` push (120K raw)
- [x] **Day 2 DONE:** 120K items rewrite thanh cong (6h, $5) -> `SeanSunny/items_tv_v6`
- [x] **Day 3 v2 DONE:** Best LightGBM RMSLE=0.5799
- [x] **Day 3 v3 DONE:** Blended RMSLE=0.5164 (TF-IDF ceiling)
- [x] **Day 4 v4 DONE:** 11 DL experiments, best AITeamVN+MLP=0.4986
- [x] **Day 4 v5-old DONE:** Blended=0.4191 (PhoBERT full=0.4413, PCA+LGB=0.4357, v4-2b, v4-0a, Day3-LGB)
- [x] **Day 4 v6 DONE:** PhoBERT 20ep=0.4418, PCA+LGB=0.4375, **Blended=0.4187** (ceiling)
  - Frontier LLM zero-shot khong canh tranh: gpt-4o-mini=0.9894, gpt-5-mini=0.6261
  - v6 ceiling ~0.4187 (5 correlated models, blending bao hoa) — can stacking + new models
- [x] **Day 4 v7 DONE (2026-04-23) — RMSLE=0.4059 (gap 0.0059 vs target 0.40):**
  - `day4_dl_models_v7.py` (1424 dong) + `.ipynb` (46 cells)
  - LLRD + R-Drop + EMA + Huber + Aux + Stacking (Ridge+EN+LGB)
  - 7 base models: PhoBERT++(0.4322), XLM-R++(0.4309), AITeamVN++(0.4350), v7-PCA+LGB(0.4333), v4-2b, v4-0a, Day3-LGB
  - Best: Stacked RMSLE=0.4059, MAE=81,776 VND, MAPE=31.3%, R2=68.3%
  - Stacking cai thien +3.1% vs v6 Blended (0.4187). Chua vuot target 0.40 (gap 0.0059)
- [x] **Day 4 v8 CODE DONE (2026-04-23) — tao TRUOC khi co ket qua v7:**
  - `day4_dl_models_v8.py` (1278 dong) + `.ipynb` (45 cells)
  - New: PhoBERT-large (370M) + mDeBERTa-v3-base (184M) + CatHeads + WeightedSampler
  - Fix: LGB meta early-stop (stratified 80/20 val split), transductive PCA
  - 9 base models (7 v7 pool + 2 new), target RMSLE <= 0.38
  - May thue: 3090 Ti 24GB (~2.5h GPU)

### Buoc tiep:
- [x] **v7 DA CHAY: RMSLE=0.4059** (gap 0.0059, chua vuot target 0.40)
- [ ] **Chay v8 tren may thue** (xem Prompt C)
  - v8 tu dong try-load v7 weights (da co trong weights_v7/)
  - Stacking pool se co day du 9 models (7 v7 + PhoBERT-large + mDeBERTa)
  - Target: RMSLE <= 0.38 | GPU: ~3.5h tren 3090 Ti 24GB
- [ ] Neu best RMSLE < 0.38: ket thuc Day 4, de xuat Day 5
- [ ] Neu best RMSLE >= 0.38: phan tich bottleneck, fallback QLoRA Qwen2.5-7B

### Day 4 v7 — Kien truc (DL-only, ~3.5h GPU)

| Phase | Model | Techniques | Batch | Ep/Pat | Ky vong RMSLE |
|-------|-------|-----------|-------|--------|---------------|
| 2 | PhoBERT-base++ | LLRD(0.9)+R-Drop(0.5)+EMA(0.999)+Huber+Aux | 80 | 12/3 | 0.41-0.43 |
| 3 | XLM-R++ | Same as PhoBERT++ | 64 | 12/3 | 0.43-0.45 |
| 4 | AITeamVN++ | LLRD+EMA+Huber+Aux (no R-Drop, freeze bottom 20) | 32 | 10/3 | 0.42-0.44 |
| 5 | Base pool | v7-PCA+LGB + v4-2b + v4-0a + Day3-LGB | — | — | — |
| 6 | Stacking | Ridge+ElasticNet+LGB meta (log-space, val as meta-train) | — | — | **0.39-0.41** |

### Day 4 v8 — Kien truc (new models + architecture, ~2.5h GPU)

| Phase | Model | Techniques | Batch | Ep/Pat | Ky vong RMSLE |
|-------|-------|-----------|-------|--------|---------------|
| 3 | **PhoBERT-large++** (370M) | LLRD+R-Drop+EMA+Huber+CatHeads+WeightedSampler | **48** | 12/3 | 0.40-0.42 |
| 4 | **mDeBERTa-v3-base++** (184M) | LLRD+EMA+Huber+CatHeads+WeightedSampler (no R-Drop) | **128** | 12/3 | 0.41-0.43 |
| 5 | Pool reload | v7 weights (skip neu chua chay) + v4-2b + v4-0a + Day3-LGB | — | — | — |
| 5 | v8-PCA+LGB | PhoBERT-large embed + Transductive PCA(256) + LGB | — | — | — |
| 6 | Stacking 9M | Ridge+ElasticNet+LGB meta (fixed early-stop 80/20 val split) | — | — | **0.37-0.40** |

**Ky thuat moi v8 so voi v7:**
- Category-specific heads: 8 Linear(h,1) rieng thay 1 shared head (giam cross-category noise)
- WeightedRandomSampler: 10 price bins, giam mid-price bias, +0.01-0.02 RMSLE
- Transductive PCA: fit PCA tren train+val+test embeddings (domain alignment)
- LGB meta fix: stratified 80/20 split cua val lam eval set (khong overfit nhu v7)
- cudnn.benchmark=True: faster kernel selection cho fixed seq_len=256

**Ky thuat moi so voi v6:**
- **LLRD:** top layer lr=2e-5, decay 0.9x moi layer -> bottom lr ~2.8e-6 (giu pre-trained features)
- **R-Drop:** forward 2 lan, MSE consistency loss (regression variant, alpha=0.5) — regularize hon dropout
- **EMA:** `AveragedModel + get_ema_multi_avg_fn(0.999)` — eval dung EMA weights (flatter minima)
- **Multi-task aux:** category head 8-class, alpha=0.1 — regularize encoder
- **Huber loss:** delta=1.0 tren normalized log-target — robust hon MSE voi outliers
- **Stacking thay weighted blend:** Ridge + ElasticNet + LGB meta-learners (log-space features)

### Quyet dinh da dua ra:
- Fine-tune (fallback): Qwen 3.5 4B (tot hon tieng Viet)
- Du lieu: Tiki 102K + Kaggle 42K + Hasaki 11K + WinMart 3.2K = 158K raw -> 120K sample
- 8 categories: Thoi Trang, Dien Tu Cong Nghe, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Lanh Gia Dung, O To Xe May
- **Day 3:** RMSLE la primary metric. Filter <= 1M VND (77.9% data)
- **Day 4:** Embedding: dangvantuan (768d) + AITeamVN (1024d BGE-M3)
- **Day 4 v5:** LoRA r=8 THAT BAI (0.5729), loai hoan toan khoi v6/v7
- **Day 4 v6:** LayerNorm + GELU head, Xavier init, dropout=0.2, full fine-tune
- **Day 4 v6:** Blending saturated o 0.4187 -> v7 stacking + model diversity
- **Day 4 v7:** DL-only (khong LLM/QLoRA), 1 seed, focus 1 mo hinh toi uu nhat, early stop som
- **Day 4 v7:** Dropout=0.2 (same v6), weight_decay=0.02, epochs=12, patience=3 (v6 overfit tu ep13+)
- **Day 4 v7:** Stacking simplified: val predictions = meta-train (khong full 5-fold CV vi ton GPU ~9h extra)

### Ket qua du lieu:
- **Day 3 v3:** Blended RMSLE=0.5164, MAE=110K, MAPE=44.0%, R2=47.1%
- **Day 4 v4:** Best AITeamVN+MLP RMSLE=0.4986
- **Day 4 v5-old:** Blended RMSLE=0.4191
- **Day 4 v6:** Blended RMSLE=0.4187, MAE=82,766 VND (ceiling reached)
- **Day 4 v7:** Stacked RMSLE=0.4059, MAE=81,776 VND, MAPE=31.3%, R2=68.3% (gap 0.0059 vs 0.40)

### Luu y ky thuat (v7):
- **LLRD implementation:** param groups theo layer index, `build_llrd_param_groups(model, base_lr, decay)`
- **R-Drop regression:** MSE giua 2 forward passes (khong phai KL — KL cho classification)
- **EMA PyTorch 2.x:** `AveragedModel(model, multi_avg_fn=get_ema_multi_avg_fn(0.999))` + `ema.update_parameters(model)` moi step
- **AITeamVN freeze:** `freeze_layers_below(model, num_to_freeze=20)` — giam ~60% VRAM
- **Batch sizes 3090 Ti fp16:** PhoBERT=80 (R-Drop 2x), XLM-R=64, AITeamVN=32
- **num_workers=0:** bat buoc Linux/WSL2 tranh multiprocessing overhead
- **Stacking log-space:** feed log1p(pred) vao meta-learners -> exp sau inference -> rmsle
- **Weights:** `.pth` luu kem `y_mean`, `y_std` cho inference. `weights_v7/` rieng
- **Cache:** reuse `ait_v2_train/val/test.npy`, `tokenized_*_train/val/test.pkl`, `arch_c_vectorizer.pkl` tu v4/v5/v6

### Moi truong chay:
- **May thue (v7/v8):** RTX 3090 Ti 24GB VRAM | AMD Ryzen 9 3900X 12C | 64GB RAM
- **Workflow:** git clone -> uv sync -> download cache tu Drive -> chay .ipynb -> copy ket qua ve
- `tokenized_*.pkl` da co trong repo — KHONG can download tu Drive
- Moi lan thue may moi: `uv sync` lai de cai dependencies

---

## Prompt dau tien cho session moi

### Prompt A: Chay v7 tren may thue

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md"
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md"

Trang thai:
- v6 DA CHAY: Blended RMSLE=0.4187 (ceiling)
- v7 DA TAO CODE: day4_dl_models_v7.ipynb (46 cells, 1424 dong)
  PhoBERT++(b=80) + XLM-R++(b=64) + AITeamVN++(b=32) + Stacking 7 models
  Target: RMSLE <= 0.40 | GPU: ~3.5h tren 3090 Ti 24GB

Files cache can download tu Drive truoc khi chay:
- day4/tokenized_*.pkl (da co trong repo)
- day4/aiteamvn_*.npy (frozen embeddings 1024d)
- day4/weights_v4/model_2b_mlp_aiteamvn.pth
- day4/weights_v4/model_0a_dnn_hv2048.pth
- day4/weights_v6/arch_c_vectorizer.pkl
- day4/weights_v6/lgb_day3_retrain.pkl

Toi se chay day4_dl_models_v7.ipynb va dan ket qua o day.
Hay cho toi biet ban da nam duoc gi va huong dan setup may thue.
```

### Prompt B: Phan tich ket qua v7 (sau khi chay xong)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md"
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md"

Trang thai: Day 4 v7 DA CHAY xong tren 3090 Ti. Ket qua:
[DAN NOI DUNG v7_results.json + output cua cell cuoi cung vao day]

Hay phan tich:
1. So sanh tung Phase voi ky vong
2. Neu best RMSLE < 0.40: cap nhat .md, ket thuc Day 4, de xuat Day 5
3. Neu best RMSLE >= 0.40: v8 da code san, chay tiep -> Prompt C
4. Cap nhat SESSION_HANDOFF.md + plan_day4.md voi so lieu thuc te
5. Commit + push
```

### Prompt C: Chay v8 tren may thue (RECOMMENDED — code da san)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md"
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md"

Trang thai:
- v6 DA CHAY: RMSLE=0.4187 (ceiling)
- v7: [CHUA CHAY / DA CHAY voi RMSLE=X.XXXX]
- v8 DA TAO CODE: day4_dl_models_v8.ipynb (45 cells, 1278 dong)
  PhoBERT-large++(370M, b=48) + mDeBERTa++(184M, b=128)
  CatHeads + WeightedSampler + Transductive PCA + Stacking 9 models (fixed LGB meta)
  Target: RMSLE <= 0.38 | GPU: ~2.5h tren 3090 Ti 24GB

Setup may thue:
  git clone <repo> && cd tech2ai
  uv sync
  # Download tu Drive vao day4/:
  #   aiteamvn_*.npy, weights_v4/*.pth, weights_v6/*.pkl
  #   [neu v7 da chay] weights_v7/phobert_v7.pth, xlmr_v7.pth, aiteamvn_v7.pth
  # tokenized_*.pkl da co trong repo (khong can download)

Toi se chay day4_dl_models_v8.ipynb va dan ket qua o day.
Hay tom tat nhung gi toi can lam va kiem tra code neu can.
```

### Prompt D: Phan tich ket qua v8 (sau khi chay xong)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md"
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md"

Trang thai: Day 4 v8 DA CHAY xong tren 3090 Ti. Ket qua:
[DAN NOI DUNG weights_v8/v8_results.json + stacking_config_v8.json vao day]

Hay phan tich:
1. So sanh tung model voi ky vong (PhoBERT-large, mDeBERTa, Stacking)
2. Neu best RMSLE < 0.38: XUAT SAC, cap nhat .md, ket thuc Day 4, de xuat Day 5
3. Neu best RMSLE < 0.40: dat target v7, xem xet co nen push tiep khong
4. Neu best RMSLE >= 0.40: phan tich bottleneck, fallback QLoRA Qwen2.5-7B
5. Cap nhat SESSION_HANDOFF.md + plan_day4.md voi so lieu thuc te
6. Commit + push
```

### Khi nao can doc them:
- **Tien xu ly du lieu**: `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md`
- **Ke hoach du an**: `segment4/mo_ta_du_an/Project_Development_Plan.md`
- **Ket qua Day 3**: `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md`

---

## Files quan trong

| File | Muc dich |
|------|----------|
| **PLAN & STATUS** | |
| `scraping_data_tv/SESSION_HANDOFF.md` | File nay — trang thai tong the |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md` | Plan Day 4 v4->v8 (505 dong) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md` | Plan Day 3 |
| **CODE — CHAY TREN MAY THUE** | |
| `day4/day4_dl_models_v8.ipynb` | **v8 notebook — RECOMMENDED (45 cells, target 0.38)** |
| `day4/day4_dl_models_v8.py` | v8 source (1278 dong) |
| `day4/day4_dl_models_v7.ipynb` | v7 notebook (46 cells, target 0.40) |
| `day4/day4_dl_models_v7.py` | v7 source (1424 dong) |
| **CACHE — TRONG REPO** | |
| `day4/tokenized_train_1m.pkl` | Underthesea tokenized 85,727 train docs |
| `day4/tokenized_val_1m.pkl` | Val 3,926 docs |
| `day4/tokenized_test_1m.pkl` | Test 3,872 docs |
| **CACHE — TREN GOOGLE DRIVE** | |
| `day4/aiteamvn_train/val/test.npy` | AITeamVN frozen embs (85727/3926/3872 x 1024d) |
| `day4/weights_v4/model_2b_mlp_aiteamvn.pth` | v4-2b: AITeamVN frozen + MLP |
| `day4/weights_v4/model_0a_dnn_hv2048.pth` | v4-0a: DNN + HashingVec |
| `day4/weights_v6/arch_c_vectorizer.pkl` | TF-IDF Arch C (word bigram + char_wb) |
| `day4/weights_v6/lgb_day3_retrain.pkl` | Day3 LGB (retrained, best params) |
| `day4/weights_v7/*.pth` | v7 weights (chi co neu v7 da chay) |
| **PACKAGE** | |
| `pricer_vi/items.py` | Item model, from_hub() |
| `pricer_vi/evaluator.py` | rmsle(), Tester, plot_predictions() |
| `pricer_vi/deep_neural_network.py` | DNN + MLP + predict_batch() |

---

## Lenh chay nhanh tren may thue

```bash
# 1. Clone repo + setup
git clone <repo_url> && cd tech2ai
uv sync
uv add transformers sentence-transformers accelerate lightgbm plotly underthesea

# 2. Download cache tu Google Drive vao dung thu muc:
#    day4/aiteamvn_train.npy, aiteamvn_val.npy, aiteamvn_test.npy
#    day4/weights_v4/model_2b_mlp_aiteamvn.pth
#    day4/weights_v4/model_0a_dnn_hv2048.pth
#    day4/weights_v6/arch_c_vectorizer.pkl
#    day4/weights_v6/lgb_day3_retrain.pkl
#    [Optional] day4/weights_v7/*.pth  (neu v7 da chay truoc do)

# 3. Mo va chay notebook (chon 1):
#    day4_dl_models_v8.ipynb  <-- RECOMMENDED (target 0.38, ~2.5h)
#    day4_dl_models_v7.ipynb  <-- (target 0.40, ~3.5h)

# 4. Sau khi chay xong, copy ve repo:
#    weights_v8/v8_results.json
#    weights_v8/stacking_config_v8.json
```

---

*Cap nhat: 2026-04-23 — Day 0-3 HOAN TAT. Day 4 v6 DA CHAY (0.4187). v7 DA CHAY (0.4059, gap 0.0059). v8 CODE DA TAO — RECOMMENDED: target 0.38, PhoBERT-large+mDeBERTa+CatHeads+Stacking 9 models, try-load v7 weights.*
