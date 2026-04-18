# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-18)

**Trang thai:** Day 4 v6 DA CHAY (Blended RMSLE=0.4187, gap 0.0187). **v7 DA TAO CODE** (DL-only, SOTA 2024-2025) — chua chay tren may thue.
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
- [x] **Day 4 v6 DONE:** PhoBERT 20ep=0.4418, PCA+LGB=0.4375, **Blended=0.4187** (marginal vs v5)
  - Frontier LLM zero-shot khong canh tranh: gpt-4o-mini=0.9894, gpt-5-nano=0.7025, gpt-5-mini=0.6261
  - v6 ceiling ~0.4187 (same 5 models, high correlation) — can v7
- [x] **Day 4 v7 CODE CREATED (2026-04-18):**
  - `day4_dl_models_v7.py` (1424 dong) + `day4_dl_models_v7.ipynb` (46 cells)
  - DL-only (khong LLM, khong QLoRA) — SOTA 2024-2025 techniques
  - Plan chi tiet: `day4/plan_day4.md` (228 dong, cleanup)

### Buoc tiep (v7):
- [ ] Chay `day4_dl_models_v7.ipynb` tren may thue 3090 Ti 24GB (~3.5h GPU + 10 phut CPU)
- [ ] Neu RMSLE < 0.40: dat target, ket thuc Day 4
- [ ] Neu RMSLE >= 0.40: phan tich bottleneck, cham QLoRA Qwen3.5 4B (repo khac)

### Day 4 v7 — Kien truc (DL-only)

| Phase | Model | Techniques | Batch | Ep/Pat | Ky vong RMSLE |
|-------|-------|-----------|-------|--------|---------------|
| 2 | **PhoBERT++** | LLRD(0.9) + R-Drop(0.5) + EMA(0.999) + Huber(1.0) + Aux(0.1) | 80 | 12/3 | 0.41-0.43 |
| 3 | **XLM-R++** | Same as PhoBERT++ | 64 | 12/3 | 0.43-0.45 |
| 4 | **AITeamVN++** | LLRD + EMA + Huber + Aux (**no R-Drop**, freeze bottom 20) | 32 | 10/3 | 0.42-0.44 |
| 5 | **Base pool** | v7-PCA+LGB + reload v4-2b + v4-0a + Day3-LGB | — | — | — |
| 6 | **Stacking** | Ridge + ElasticNet + LGB meta (log-space), avg of 3 | — | — | **0.39-0.41** |

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
- **Day 4 v7:** CHUA CHAY — target 0.39-0.41 qua stacking

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
- **May thue v7:** RTX 3090 Ti 24GB VRAM | Xeon E5-2686 v4 36C | 64GB RAM (VN1x)
- **Workflow:** git clone -> uv sync -> chay .ipynb -> copy ket qua ve
- Moi lan thue may moi: `uv sync` lai, tokenize cache se tai tu GG Drive

---

## Prompt dau tien cho session moi

### Prompt A: Chay v7 tren may thue (TIEP THEO)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md" — plan v7 chi tiet
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models_v7.py" — code v7 (neu can xem)

Trang thai:
- v6 DA CHAY: Blended RMSLE=0.4187 (gap 0.0187 den target 0.40), ceiling ~0.4187
- v7 DA TAO: day4_dl_models_v7.ipynb (46 cells) + .py (1424 dong), DL-only SOTA 2024-2025
- Ky thuat moi: LLRD + R-Drop + EMA + Multi-task Aux + Huber Loss + Stacking
- Base models (7): PhoBERT++, XLM-R++, AITeamVN++, v7-PCA+LGB, v4-2b, v4-0a, Day3-LGB
- Meta-learners (3): Ridge + ElasticNet + LGB (log-space, val as meta-train), final avg
- Batch: PhoBERT=80, XLM-R=64, AITeamVN=32 (freeze bottom 20) — 3090 Ti 24GB
- Target: RMSLE <= 0.40

Buoc tiep (toi se lam):
1. Thue 3090 Ti 24GB (VN1x, ~3.5h GPU + 10 phut CPU)
2. Clone repo, uv sync, chay day4_dl_models_v7.ipynb
3. Copy ket qua (v7_results.json + stacking_config.json) ve repo

Sau khi chay xong se dan ket qua vao day. Hay phan tich va cap nhat .md files.
```

### Prompt B: Phan tich ket qua v7 (SAU KHI CHAY)

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md" — plan v7

Trang thai: Day 4 v7 DA CHAY xong tren 3090 Ti. Ket qua:
[DAN KET QUA v7_results.json + output notebook vao day]

Hay phan tich ket qua:
1. So sanh tung Phase voi ky vong (Phase A/B/C)
2. Neu RMSLE < 0.40: cap nhat .md files, ket thuc Day 4, de xuat Day 5
3. Neu RMSLE >= 0.40: phan tich bottleneck, de xuat v8 HOAC chuyen QLoRA Qwen3.5 4B
4. Cap nhat SESSION_HANDOFF.md + plan_day4.md voi ket qua thuc te
5. Commit + push
```

### Khi nao can doc them:
- **Tien xu ly du lieu**: `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md`
- **Ke hoach du an**: `segment4/mo_ta_du_an/Project_Development_Plan.md`
- **Ket qua Day 3**: `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md`

---

## Files quan trong

| File | Muc dich |
|------|----------|
| **DATA PROCESSING** | |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md` | Plan Day 0-4 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day3/plan_day3.md` | Plan Day 3 |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md` | Plan Day 4 (v4 -> v7) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi/` | Package (items, evaluator, DNN) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models_v7.ipynb` | **v7 notebook (run on 3090 Ti)** |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models_v7.py` | v7 source (jupytext) |
| `scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models_v6.ipynb` | v6 notebook (blended 0.4187) |
| **ENGLISH REFERENCE** | |
| `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/pricer/deep_neural_network.py` | DNN English |
| **PROJECT** | |
| `segment4/mo_ta_du_an/Project_Development_Plan.md` | Tong the |

---

## Lenh chay nhanh

```bash
cd tech2ai

# Setup may thue 3090 Ti
uv sync
uv add transformers sentence-transformers accelerate lightgbm optuna plotly pyvi underthesea

# Chay Day 4 v7 (notebook)
# scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models_v7.ipynb
```

---

*Cap nhat: 2026-04-18 — Day 0-3 HOAN TAT. Day 4 v6 DA CHAY (0.4187, gap 0.0187). v7 CODE DA TAO (DL-only SOTA 2024-2025, chua chay). Target 0.40.*
