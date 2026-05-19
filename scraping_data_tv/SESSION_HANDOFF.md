# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Prompt cho session tiep theo (copy nguyen vao chat moi)

```
Nap ngu canh tu cac file:
- scraping_data_tv/SESSION_HANDOFF.md
- Data_processing_for_Vietnamese_data/day4_v2/plan_day4_v2.md

Trang thai hien tai (2026-05-19 — session 25 ket thuc):
- Branch: feature/day5-qlora-qwen
- Day 3 v2: XONG (MAE=92.6k).
- Day 4 v2: NB01/02/04/05/06/10 DA CHAY. NB07/08 DA XOA.
  NB09 PENDING (chua chay).
  NB11 TAO ROI (reference, optional).
  NB12/13/14 TAO ROI — SAN SANG CHAY.

== DAY 4 V2 — KET QUA DA CO ==
  KET QUA THUC TE (chay tren RTX 3090 Ti):
    Notebook 01 — DNN + TF-IDF char_wb 100K:          test MAE = 77.3k
    Notebook 02 — DNN + HashingVec 5000:               test MAE = 80.0k
    Notebook 04 — e5-small frozen + DNN:               test MAE = 102.7k, R2=50.3%
    Notebook 05 — AITeamVN frozen + DNN:               test MAE = 76.1k,  R2=71.7%
    Notebook 06 — AITeamVN fine-tune top-4:            test MAE = 74.2k,  R2=72.8%  <- BEST
    Notebook 10 — PhoBERT-base improved (top-8+RDrop): test MAE = 77.6k,  R2=70.8%
    Notebook 07/08 — DELETED
    Notebook 09 — AITeamVN top-8 + R-Drop:            PENDING (chua chay)
    Notebook 11 — Ridge stacking ensemble:             TAO ROI (reference, optional)
    Notebook 12 — AITeamVN full 24 layers:             TAO ROI — SAN SANG CHAY (session 25)
    Notebook 13 — PhoBERT-large top-8:                TAO ROI — SAN SANG CHAY (session 25)
    Notebook 14 — AITeamVN phased + price bins:        TAO ROI — SAN SANG CHAY (session 25)

== FILES DA TAO (session 25) ==
  pricer_vi_2/bert_finetune_model.py:
    - Them grad_accum=1 vao BERTFinetuneRunner.train() (backward compat, default=1)
    - NB12 su dung grad_accum=2 (batch=16 -> effective 32) — xoa GRAD_ACCUM neu OOM
  pricer_vi_2/bert_finetune_phased_model.py (MOI):
    - PhasedBERTRegressor: price_bin_head (5 bins) thay category_head (8 classes)
    - PhasedBERTRunner: 3-phase, rebuild optimizer+scheduler tai ep 1/5/9
    - Phase 1 (ep1-4): top-4, lr=2e-5
    - Phase 2 (ep5-8): top-8, lr=1e-5
    - Phase 3 (ep9-12): top-16, lr=5e-6
  day4_v2_12_aitvn_full.ipynb:
    keep_top=24, batch=16, grad_accum=2, llrd=0.70, base_lr=1.5e-5, warmup=0.10, epochs=8
    Save: weights/aitvn_full.pth, val_predictions/aitvn_full_{val,test}.json
  day4_v2_13_phobert_large.ipynb:
    vinai/phobert-large, keep_top=8, batch=32, llrd=0.85, epochs=10
    Reuse phobert_seg_*.pkl tu NB10 (khong phai chay lai word-segment 2-3h)
    Save: weights/phobert_large.pth, val_predictions/phobert_large_{val,test}.json
  day4_v2_14_aitvn_phased.ipynb:
    PhasedBERTRunner, batch=24, aux_alpha=0.15, epochs=12, patience=5
    Save: weights/aitvn_phased.pth, val_predictions/aitvn_phased_{val,test}.json

== KEY TECHNICAL NOTES ==
- PhoBERT bat buoc Underthesea word segmentation TRUOC tokenizer
  → Cache phobert_seg_{train,val,test}.pkl (reuse tu NB10 cho NB13)
- BERTFinetuneRunner.train() dung AveragedModel (EMA) — inference phai dung ema_model
- Checkpoint keys (NB12/13): ema_state_dict, y_mean, y_std, model_name, keep_top_layers, cat_classes
- Checkpoint keys (NB14): ema_state_dict, y_mean, y_std, model_name, price_bin_boundaries
- bert_finetune_model.py: .clamp(min=0) sau torch.exp()-1 o val/test_predictions
- num_workers=0 bat buoc tren Linux/WSL2

== FILE THAM KHAO ==
- Data_processing_for_Vietnamese_data/day4_v2/plan_day4_v2.md (Section 7: A12/13/14 spec)
- Data_processing_for_Vietnamese_data/pricer_vi_2/bert_finetune_model.py (BERTFinetuneRunner)
- Data_processing_for_Vietnamese_data/pricer_vi_2/bert_finetune_phased_model.py (PhasedBERTRunner)
- Data_processing_for_Vietnamese_data/pricer_vi_2/phobert_model.py (PhoBERTRunner)

Coding guidelines:
- Truoc khi viet/sua code: invoke skill karpathy-guidelines
- Su dung evaluator.py de ve bieu do (plot_training_history + evaluate)
```

---

## Trang thai hien tai (2026-05-19 — session 25)

**Trang thai:** Tao NB12/13/14 + bert_finetune_phased_model.py + grad_accum support. Tat ca san sang chay tren vast.ai.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 25 ket qua (2026-05-19)

**Da lam (code):**
- [x] `pricer_vi_2/bert_finetune_model.py`: Them `grad_accum=1` vao `BERTFinetuneRunner.train()` (backward compat). NB12 dung `grad_accum=2` (effective batch=32 tu batch=16).
- [x] `pricer_vi_2/bert_finetune_phased_model.py` (MOI):
  - `PhasedBERTRegressor`: AutoModel + price_head + `price_bin_head` (5 bins [<50k, 50-150k, 150-350k, 350-650k, >=650k])
  - `PhasedBERTRunner`: 3-phase training, rebuild optimizer+scheduler tai ep 1, 5, 9
  - Phase 1/2/3: top-4 lr=2e-5 → top-8 lr=1e-5 → top-16 lr=5e-6
- [x] `day4_v2/day4_v2_12_aitvn_full.ipynb`: AITeamVN full 24 layers, batch=16, grad_accum=2, llrd=0.70, epochs=8
- [x] `day4_v2/day4_v2_13_phobert_large.ipynb`: PhoBERT-large top-8, reuse pkl NB10, epochs=10
- [x] `day4_v2/day4_v2_14_aitvn_phased.ipynb`: PhasedBERTRunner, batch=24, aux_alpha=0.15, epochs=12

**Da lam (docs):**
- [x] plan_day4_v2.md: cap nhat PLANNED → CREATED cho NB12/13/14, them bert_finetune_phased_model.py vao folder structure, timestamp session 25
- [x] SESSION_HANDOFF.md: cap nhat prompt + them session 25 block

**Con lai:**
- [ ] Chay NB09 (AITeamVN top-8 + R-Drop) — PENDING, tuy ket qua quyet dinh thu tu NB12/13/14
- [ ] Chay NB12 (AITeamVN full 24L) — SAN SANG. Note: xoa GRAD_ACCUM=2 neu OOM
- [ ] Chay NB13 (PhoBERT-large top-8) — SAN SANG. Reuse phobert_seg_*.pkl tu NB10
- [ ] Chay NB14 (AITeamVN phased) — SAN SANG (MOST PROMISING, du kien MAE < 65k)

---

## Trang thai hien tai (2026-05-19 — session 24)

**Trang thai:** NB06/10 co ket qua. NB07/08 da xoa. NB11 da tao. Research + plan 3 kien truc moi (A12/13/14). plan_day4_v2.md va SESSION_HANDOFF.md cap nhat day du.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 24 ket qua (2026-05-19)

**Ket qua nhan duoc tu user:**
- [x] Notebook 06 — AITeamVN fine-tune top-4: **test MAE = 74.2k, R2=72.8%** (val best: 81.06k ep10)
- [x] Notebook 10 — PhoBERT-base improved (top-8+RDrop): **test MAE = 77.6k, R2=70.8%** (val best: 82.55k ep10)
  - Nhan xet: ca 2 notebooks chua plateau o epoch 10, loss van giam → con room de cai thien
  - AITeamVN van vuot PhoBERT du improved config — backbone AITeamVN (568M, BGE-M3) manh hon

**Da lam (doc/cap nhat):**
- [x] Doc SESSION_HANDOFF.md va plan_day4_v2.md
- [x] Doc ket qua tu NB06 va NB10 notebooks (agent)
- [x] Xoa day4_v2_07_phobert_base.ipynb va day4_v2_08_phobert_large.ipynb
- [x] Tao day4_v2_11_ensemble.ipynb (Ridge stacking reference, optional)
- [x] Research 3 kien truc moi: A12 (full encoder), A13 (PhoBERT-large), A14 (phased+price bins)
- [x] Cap nhat plan_day4_v2.md: Section 0.2 (targets), Section 3 (folder), Section 4 (results), Section 5 (constraints), Section 7 (3 kien truc moi)
- [x] Cap nhat SESSION_HANDOFF.md: prompt + session 24 block

**Con lai:**
- [ ] Nhan ket qua NB09 (AITeamVN top-8 + R-Drop, mai chay ~8-10h)
- [ ] Tuy ket qua NB09: chay NB14 (A14, most promising) hoac NB12 (A12)
- [ ] Implement NB12/13/14 dua tren spec trong plan_day4_v2.md Section 7

---

## Trang thai hien tai (2026-05-18 — session 23)

**Trang thai:** Research kỹ thuật + data exploration + tạo NB09/NB10 (improved config). Runner files updated.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 23 ket qua (2026-05-18)

**Research & Data Exploration:**
- [x] Chay code kham pha dataset SeanSunny/items_tv_v9:
  - Price: bimodal (peak 50-100k + peak 500-600k), sau log1p skewness=-0.110 (optimal)
  - Categories: 8 top-level, moi cat span [5,1000k] voi std~250k (coarse, aux head hieu qua thap)
  - Sub-categories: 5,575+ unique trong "Danh muc:" field — BERT tu hoc duoc
  - Summary: median=317 chars / 67 words / p95=88 words → max_length=256 du bao phu
- [x] Research literature (EMA arXiv 2411.18704, AutoFreeze 2102.01386, LLRD ACM, NeurIPS 2024 WD):
  - EMA 0.999 → 0.9999 (window 1K→10K, 84K total steps)
  - keep_top_layers=4 → 8 (269K samples can 33%+ encoder)
  - warmup_ratio=0.1 → 0.05 (tranh mat toan bo epoch 1 ramp-up)
  - weight_decay=0.02 → 0.01 (BERT standard)
  - llrd_decay=0.9 → 0.85 (wider range cho top-8)
  - R-Drop alpha=0.3 (MSE consistency loss, su dung trong English Day 4)
  - max_length=256: giu nguyen (p95=88 words, 256 tokens du bao phu, thoi gian khong quan trong)
- [x] Cap nhat plan_day4_v2.md Section 9 (day du analysis + bang summary)

**Da lam (code):**
- [x] `pricer_vi_2/bert_finetune_model.py`:
  - Them `r_drop_alpha=0.0` vao `train()` (backward-compatible)
  - R-Drop branch: 2x forward, MSE consistency loss, trong ca AMP va non-AMP path
  - Cap nhat print: hien thi r_drop_alpha
- [x] `pricer_vi_2/phobert_model.py`:
  - Them `r_drop_alpha=0.0` vao `train()` (backward-compatible)
  - R-Drop branch tuong tu
- [x] Tao `day4_v2/day4_v2_09_aitvn_improved.ipynb`:
  - AITeamVN top-8, batch=24, ema=0.9999, warmup=0.05, wd=0.01, llrd=0.85, r_drop=0.3
  - Save: weights/aitvn_improved.pth + val_predictions/aitvn_improved_{val,test}.json
- [x] Tao `day4_v2/day4_v2_10_phobert_improved.ipynb`:
  - PhoBERT-base top-8, batch=48, ema=0.9999, warmup=0.05, wd=0.01, llrd=0.85, r_drop=0.3
  - Reuse Underthesea cache tu NB07
  - Save: weights/phobert_base_improved.pth + val_predictions/phobert_base_improved_{val,test}.json
- [x] Cap nhat plan_day4_v2.md: folder structure (NB09/10/11), results table (them NB09/10)
- [x] Cap nhat SESSION_HANDOFF.md: prompt + session 23 block

**Thu tu chay tren may thue (doi NB06 xong):**
- [ ] Doi NB06 ket qua (dang chay epoch 5+/10)
- [ ] Chay NB09 (AITeamVN improved) — uu tien cao nhat
- [ ] Chay NB10 (PhoBERT-base improved)
- [ ] Tuy ket qua: co the chay them NB07/08 cho ensemble diversity
- [ ] Tao NB11 (ensemble Ridge stacking)

**Con lai:**
- [ ] Nhan ket qua NB06 (val_mae moi epoch + final test MAE)
- [ ] Chay NB09 tren vast.ai — bao cao val_mae moi epoch
- [ ] Chay NB10 tren vast.ai — reuse Underthesea cache
- [ ] Tao NB11 (ensemble) sau khi co du val_predictions

---

## Trang thai hien tai (2026-05-18 — session 22)

**Trang thai:** Tao PhoBERT plan + 3 files moi + fix bug. NB06/07/08 san sang chay tren vast.ai.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 22 ket qua (2026-05-18)

**Da lam (code):**
- [x] Tao `pricer_vi_2/phobert_model.py` (moi):
  - Import BERTFineTuneRegressor, freeze_bottom_layers, build_llrd_param_groups, _MultiTaskDataset tu bert_finetune_model.py (khong duplicate)
  - `PHOBERT_BASE = "vinai/phobert-base-v2"`, `PHOBERT_LARGE = "vinai/phobert-large"`
  - `word_segment(texts, cache_path)`: Underthesea word_tokenize voi joblib pkl cache
  - `PhoBERTRunner`: setup() word-segments TRUOC khi tokenize, reuse toan bo training loop tu BERTFinetuneRunner
  - val_predictions() va test_predictions(): .clamp(min=0) de tranh gia am
  - inference(): word_segment 1 sample, tra ve max(5.0, pred)
- [x] Tao `day4_v2/day4_v2_07_phobert_base.ipynb`:
  - Model: vinai/phobert-base-v2 (12L, 768d, 135M)
  - Sweep: keep_top_layers=4 → evaluate → neu MAE > 78k → chay lai top-8
  - batch_size=64, max_length=256, base_lr=2e-5
  - Cache: cache/phobert_seg_{train,val,test}.pkl (dung chung NB08)
  - Save: weights/phobert_base_{top4,top8}.pth, val_predictions/phobert_base_{val,test}.json
- [x] Tao `day4_v2/day4_v2_08_phobert_large.ipynb`:
  - Model: vinai/phobert-large (24L, 1024d, 370M)
  - Sweep: keep_top_layers=4 → evaluate → neu MAE > 73k → chay lai top-8
  - batch_size=48 (kem VRAM headroom hon base), max_length=256
  - Tai su dung cache tu NB07 (khong chay lai Underthesea)
  - Save: weights/phobert_large_{top4,top8}.pth, val_predictions/phobert_large_{val,test}.json
- [x] Fix `pricer_vi_2/bert_finetune_model.py`:
  - val_predictions(): them .clamp(min=0) sau torch.exp()-1 (tranh gia am early epochs)
  - test_predictions(): them .clamp(min=0) tuong tu

**Cap nhat plan:**
- [x] `day4_v2/plan_day4_v2.md`:
  - Folder structure: them NB07/08, rename ensemble NB07→NB09, them phobert_model.py, them phobert cache/weights/predictions
  - Results table: them hang PhoBERT-base/large, renumber ensemble → NB09
  - Them sweep logic va observation session 22
  - Them timestamp cap nhat session 22
- [x] `scraping_data_tv/SESSION_HANDOFF.md`: cap nhat prompt + them session 22 block nay

**Thao luan kien truc (session 22):**
- keep_top_layers=8 co the tot hon top-4: ~30M trainable (vs 15M) → thich nghi sau hon voi price features
  AITeamVN: 8/24 tang = 33% encoder. PhoBERT-base: 8/12 = 67% (nhieu). PhoBERT-large: 8/24 = 33%.
- EMA(0.999) + dropout(0.2) + weight_decay(0.02) + HuberLoss kiem soat overfit tot voi 269K samples
- PhoBERT bo sung diversity cho ensemble: tokenizer khac (Underthesea), backbone khac (VinAI 20GB VN corpus)
- Thong tin: vinai/phobert-base-v2 va vinai/phobert-large doi hoi Underthesea word_tokenize TRUOC tokenizer
  → "Man hinh TV" → "Man_hinh TV" → PhoBERT tokenizer xu ly dung

**Con lai:**
- [ ] Chay NB06 (AITeamVN fine-tune) tren vast.ai — bao cao val_mae moi epoch + final test MAE
- [ ] Tuy ket qua NB06: neu MAE > 75k → chay section sweep top-8 trong NB06
- [ ] Chay NB07 (PhoBERT-base): Underthesea cache ~2-3h + train
- [ ] Chay NB08 (PhoBERT-large): tai su dung cache + train
- [ ] Tao NB09 (ensemble): Ridge stacking NB01+02+05+06+07+08 → target MAE < 65k

---

## Trang thai hien tai (2026-05-18 — session 21)

**Trang thai:** Day 4 v2 notebooks 01/02/04/05 DA CHAY. Fix senttrans_model.py + tao bert_finetune_model.py + notebook 06. San sang chay fine-tune AITeamVN.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 21 ket qua (2026-05-18)

**Ket qua chay tren vast.ai (RTX 3090 Ti) — user bao cao:**
- [x] Notebook 01 — DNN + TF-IDF char_wb 100K: **test MAE = 77.3k VND**
- [x] Notebook 02 — DNN + HashingVec 5000:     **test MAE = 80.0k VND**
- [x] Notebook 04 — e5-small frozen + DNN:     **test MAE = 102.7k VND**, R2=50.3%
- [x] Notebook 05 — AITeamVN frozen + DNN:     **test MAE = 76.1k VND**,  R2=71.7% ← best

**Da lam (code):**
- [x] Fix `pricer_vi_2/senttrans_model.py` (surgical edits):
  - `setup()`: expose `hidden_size=4096` parameter (truoc: an trong PriceDNN default)
  - `num_workers=4` → `num_workers=0` (fix HuggingFace tokenizer fork warning trong WSL2/Linux)
  - Val early stopping: `val_items[:1000]` → `val_items` (full 3926) — `val[:1000]` qua nhieu nhieu va khong representative
  - Doi ten attribute: `y_val_1k`, `y_val_1k_norm` → `y_val`, `y_val_norm`
- [x] Tao `pricer_vi_2/bert_finetune_model.py` (moi):
  - `BERTFinetuneRegressor`: AutoModel + mean_pooling + price_head + aux category_head
  - `freeze_bottom_layers(keep_top_n=4)`: freeze embeddings + bottom 20/24 layers
  - `build_llrd_param_groups()`: LLRD heads=base_lr, layer i = base_lr × decay^(num_layers-i-1)
  - `BERTFinetuneRunner`: setup/train/val_predictions/test_predictions/save/load/inference
  - Training: LLRD + EMA(AveragedModel 0.999) + HuberLoss(delta=1.0) + AMP(GradScaler) + CosineWarmup
  - history keys: train_loss/val_loss/val_mae/lr — compatible voi evaluator.plot_training_history
- [x] Tao `day4_v2/day4_v2_06_aitvn_finetune.ipynb`:
  - 8 cells: imports → load data → setup → train → plot history → save → evaluate → sanity check
  - Config: keep_top_layers=4, batch=32, max_length=256, base_lr=2e-5, llrd_decay=0.9
  - Save: weights/aitvn_finetune.pth + val_predictions/aitvn_finetune_{val,test}.json

**Phan tich ket qua session 21:**
- Frozen e5-small (384-dim) MAE=102.7k thua ca TF-IDF (77.3k): frozen embeddings treat "ao 100k" va "ao 500k" nhu nhau (embedding space cho similarity, khong phai price)
- AITeamVN frozen (1024-dim, VN-MTEB 63.34) MAE=76.1k: embedding phong phu hon, classification score 69.06 cao (price range by category)
- Training history notebook 05: train_loss=0.0705 vs val_loss=0.3669 epoch 15 — heavy overfitting. Fix: fine-tune (thay vi frozen head) cho phep encoder adapt de giam gap nay
- Fine-tune top-4 layers ky vong giam MAE xuong 60-70k

**Con lai:**
- [ ] Chay `day4_v2_06_aitvn_finetune.ipynb` tren vast.ai — bao cao val_mae moi epoch + final test MAE
- [ ] Neu MAE < 70k: tao `day4_v2_07_ensemble.ipynb` (Ridge stacking 4 models)
- [ ] Neu MAE > 75k: xem xet tang keep_top_layers=8 hoac dung XLM-RoBERTa

---

## Trang thai hien tai (2026-05-17 — session 20)

**Trang thai:** Day 4 v2 embedding models fix + 3 notebooks moi. San sang chay 00_token_analysis.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 20 ket qua (2026-05-17)

**Da lam:**
- [x] Fix `pricer_vi_2/senttrans_model.py`:
  - `ENCODER_NAME`: `paraphrase-multilingual-MiniLM-L12-v2` → `intfloat/multilingual-e5-small`
  - Them param `encode_batch_size=256` vao `encode_and_cache()` va `test_predictions()` (backward compatible)
  - Ly do: MiniLM co 128-TOKEN LIMIT truncate am tham, e5-small = 512 tokens cung dim 384
- [x] Tao `day4_v2_00_token_analysis.ipynb`:
  - Profile char count / word count / MiniLM token count / e5-small token count
  - Hien thi % bi truncate tai 128 tokens (MiniLM) va 512 tokens (e5-small)
  - Distribution plots + summary table — chay tren vast.ai, bao cao ket qua
- [x] Tao `day4_v2_04_e5small.ipynb` (Huong A):
  - Mirror notebook 03, override `sm.ENCODER_NAME = "intfloat/multilingual-e5-small"`
  - Cache: `cache/e5small_embeddings.pkl`, weights: `weights/e5small_dnn.pth`
- [x] Tao `day4_v2_05_aitvn.ipynb` (Huong B):
  - Override `sm.ENCODER_NAME = "AITeamVN/Vietnamese_Embedding"`
  - `encode_batch_size=64` (model 568M), DNN `batch_size=128` (1024-dim activations)
  - Cache: `cache/aitvn_embeddings.pkl`, weights: `weights/aitvn_dnn.pth`
- [x] Cap nhat `plan_day4_v2.md`:
  - Folder structure: them notebooks 00/04/05, rename 06-08 cho XLM-R/PhoBERT/Ensemble
  - Task 4b: mark [x] DONE
  - Task 4c (dangvantuan): DROPPED — PyVi dependency phuc tap, bo khoi plan
  - Task 4d: renumber 05, mark [x] DONE
  - Section 6.1: them note ve senttrans_model.py fix
  - Section 6.4: cap nhat thu tu chay

**Con lai:**
- [ ] Chay `day4_v2_00_token_analysis.ipynb` tren vast.ai → bao cao % truncation
- [ ] Chay notebooks 01/02/03/04/05 tren vast.ai → bao cao MAE
- [ ] Quyet dinh co can XLM-R/PhoBERT (06/07) hay ensemble luon
- [ ] Tao `day4_v2_08_ensemble.ipynb` (Ridge stacking)

---

## Trang thai hien tai (2026-05-17 — session 19)

**Trang thai:** Day 4 v2 code HOAN CHINH. 2 runner files + 3 notebooks + plan cap nhat 2072 dong. San sang chay.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 19 ket qua (2026-05-17)

**Da lam:**
- [x] Tao `pricer_vi_2/deep_neural_network_sparse.py`:
  - `ResidualBlock` + `PriceDNN` (input flexible, num_blocks=8, hidden=4096)
  - `SparseDataset` (per-row toarray — khong toarray() toan bo 269K×100K)
  - `SparseDNNRunner`: val[:1000] training, `val_predictions()` full 3926, `test_predictions()`
  - history: 4 keys (train_loss, val_loss, val_mae, lr) — compatible voi `evaluator.plot_training_history`
  - `inference()` clip tai `max(5.0, ...)` — dung cho price range 5-1000k VND
- [x] Tao `pricer_vi_2/senttrans_model.py`:
  - `SentTransRunner`: frozen encoder, `encode_and_cache()`, val[:1000] training
  - `ENCODER_NAME = "paraphrase-multilingual-MiniLM-L12-v2"` (default, co the override)
  - Reuse `PriceDNN` tu `deep_neural_network_sparse.py`
- [x] Tao 3 notebooks trong `day4_v2/`:
  - `day4_v2_01_dnn_tfidf.ipynb` — TF-IDF char_wb 100K + SparseDNNRunner
  - `day4_v2_02_dnn_hashvec.ipynb` — HashingVec 5000 + SparseDNNRunner
  - `day4_v2_03_senttrans.ipynb` — paraphrase-multilingual-MiniLM + SentTransRunner
  - Tat ca: 7 sections, save weights + val_predictions + test_predictions, evaluate 200 test
- [x] Research 3 Vietnamese embedding models (VN-MTEB benchmark):
  - `intfloat/multilingual-e5-small`: 118M, 384-dim, 512 tokens, VN-MTEB 60.66
  - `dangvantuan/vietnamese-embedding`: 135M, 768-dim, STS 88.33, can PyVi tokenize
  - `AITeamVN/Vietnamese_Embedding`: 568M, 1024-dim, VN-MTEB 63.34 (tot nhat), BGE-M3 base
- [x] Cap nhat `plan_day4_v2.md` (1652 → 2072 dong):
  - Section 6: Embedding Model Research + bang so sanh VN-MTEB
  - Task 4b: multilingual-e5-small + DNN (chay truoc tien)
  - Task 4c: dangvantuan/vietnamese-embedding + DNN (can PyVi)
  - Task 4d: AITeamVN/Vietnamese_Embedding + DNN (tot nhat, nang nhat)
  - Cap nhat folder structure, results table

**Phat hien quan trong session 19:**
- `paraphrase-multilingual-MiniLM-L12-v2` (notebook 03) co 128-TOKEN LIMIT — truncate am tham product descriptions dai
- AITeamVN/Vietnamese_Embedding: classification score 69.06 (manh nhat) — phu hop price prediction theo category
- 3 notebooks moi (4b/4c/4d) chua tao — se lam session tiep theo

**Con lai:**
- [ ] Tao 3 notebooks: `day4_v2_04_e5small.ipynb`, `day4_v2_05_dangvantuan.ipynb`, `day4_v2_06_aitvn.ipynb`
- [ ] Commit + push tat ca files session 19
- [ ] Chay 3 notebooks DNN (01/02/03) tren vast.ai, bao cao MAE
- [ ] Chay 3 notebooks SentTrans (03/04/05/06), bao cao MAE

== NHIEM VU SESSION TIEP THEO ==
  1. Commit tat ca files session 19 (2 runner .py + 3 notebooks + plan update)
  2. Tao 3 notebooks Task 4b/4c/4d theo plan_day4_v2.md Section Task4b/4c/4d
  3. Chay notebooks tren vast.ai + bao cao MAE

== KEY TECHNICAL NOTES SESSION 19 ==
- SparseDNNRunner.setup(): HashingVec khong co fit() — fit_transform() va transform() deu nhu nhau
- history format: {"train_loss", "val_loss", "val_mae", "lr"} — 4 keys cho plot_training_history()
- SentTransRunner: override ENCODER_NAME TRUOC khi tao runner: `import pricer_vi_2.senttrans_model as sm; sm.ENCODER_NAME = "new-model"`
- dangvantuan: inject X_train/X_val truc tiep sau PyVi tokenize (khong qua encode_and_cache)
- AITeamVN uses dot product similarity (khong phai cosine) — khong anh huong den DNN head

---

## Trang thai hien tai (2026-05-17 — session 18)

**Trang thai:** Day 4 v2 plan HOAN CHINH. 7 tasks, 1652 lines. Chua bat dau implement.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 18 ket qua (2026-05-17)

**Da lam:**
- [x] Doc Report_data_processing_v2.md + tat ca model files tieng Anh
- [x] Brainstorm + interview 6 cau hoi (GPU, model scope, PhoBERT, stacking, target MAE, sparse handling)
- [x] Viet `day4_v2/plan_day4_v2.md` — 1,652 dong, 7 tasks day du:
  - Task 1: 4 model runner files (dnn_sparse, senttrans, xlmr, phobert) — code day du
  - Task 2-6: 5 notebooks (DNN TF-IDF, DNN HashVec, SentTrans, XLM-R, PhoBERT) — code day du
  - Task 7: Ridge Stacking Ensemble — code day du, khong reload models
- [x] Self-review + fix 6 issues (placeholder Task 7, test predictions cho tung notebook)
- [x] Commit plan_day4_v2.md

**Quyet dinh quan trong session 18:**
- Log1p + z-normalize CHO DNN (mirror English Day 4) — khac Day 3 v2 LGB
- TF-IDF 100K features: mini-batch sparse (SparseDataset + collate) — khong toarray() toan bo
- Moi notebook save ca val_predictions + test_predictions → Task 7 chi load, khong reload model
- Ridge stacking optimize MAE tren val set
- Target: MAE < 65k VND (ensemble)

**Con lai:**
- [ ] Dong Day 3 v2: day3_v2_results.json + day3_v2_summary.md (optional truoc Day 4)
- [ ] Thuc thi Task 1: tao 4 model files trong pricer_vi_2/
- [ ] Tao 5 notebooks tren may thue (vast.ai RTX 3090 Ti)
- [ ] Chay tung notebook, bao cao MAE

### Session 17 ket qua (2026-05-17)

**Da chay tren may thue:**
- [x] 5A: LGB + char_wb 269K (MSE) → MAE=92.6k ← BEST
- [x] 5B: LGB + char_wb 269K (MAE obj) → MAE=95.1k
- [x] 5D: RF + CountVect word 50K (15K subset) → MAE=123.3k
- [x] 5E: XGBoost + CountVect word 50K (269K) → MAE=113.2k
- [x] 5F: LGB + CountVect word 50K (MSE, 269K) → MAE=97.3k
- [x] 5G: LGB + CountVect word 50K (MAE obj, 269K) → MAE=100.0k
- [ ] 5C: Blend 5A+5B — CHUA implement

**Fix loi trong session nay:**
- CountVectorizer tra ve int64 o predict → them .astype(np.float32) vao vec_count.transform()
- Loi xuat hien ca o fit (truoc) va predict (session nay)

**Phat hien quan trong:**
- MSE obj (5A: 92.6k) BEAT MAE obj (5B: 95.1k) — voi 269K data lon, MSE on dinh hon
- TF-IDF char_wb (5A: 92.6k) beat CountVect word (5F: 97.3k) — IDF + char ngrams co gia tri
- Hypothesis 4a/4b confirmed: RF/XGB deu cai thien voi low-dim features

**plan_day3_v2.md va SESSION_HANDOFF.md: DA CAP NHAT** (session nay)

**Buoc tiep (session 18):**
- [ ] Quyet dinh: dong Day 3 v2 (92.6k) hay tiep tuc implement 5C/OHE
- [ ] Save day3_v2_results.json
- [ ] Tao day3_v2_summary.md
- [ ] Commit + push

---

## Trang thai hien tai (2026-05-16 — session 16)

**Trang thai:** Section 5 notebook HOAN CHINH. San sang chay tren may thue.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 16 ket qua (2026-05-16)

**Phan tich root cause 4a/4b thua:**
- English day3: BoW 2000 features → XGBoost/RF hoat dong tot
- Vietnamese day3: TF-IDF 100K features → XGBoost/RF overloaded (qua cao chieu)
- LGB thich hop voi sparse high-dim nhung RF/XGB thi khong

**Da tao:**
- [x] `day3_v2/day3_v2_section5.ipynb` — 5A/5B/5C (LGB) + 5D/5E (hypothesis BoW 2000)

**Fix loi trong session nay:**
- CountVectorizer tra ve int64 → LGB TypeError: them .astype(np.float32) khi fit va predict
- LinearRegression (269K x 100K) chay > 25 phut → doi sang Ridge(solver='sag') → vai phut
- under_lgb_bench: dat nham .astype(np.float32) vao vi_tokenize (str) thay vi transform()

**Buoc tiep (session 17):**
- [ ] Chay day3_v2_section5.ipynb tren may thue
- [ ] Bao cao MAE tung model
- [ ] Neu best MAE < 90k → tao day3_v2_summary.md va dong Day 3 v2
- [ ] Neu chua < 90k → quyet dinh tiep tuc tuning

### Session 15 ket qua (2026-05-16)

**Quyet dinh lon:**
- Doi primary metric tu RMSLE sang **MAE** — vi price range 5-1000 da giong English (1-999)
- Bo log1p transform — train tren raw price, bam sat English day3
- Evaluator: match English structure (MAE/MSE/R2 only, "k VND" display, khong RMSLE/MAPE)

**Da tao/cap nhat:**
- [x] `pricer_vi_2/evaluator.py` — rewrite match English: MAE/MSE/R2, error print khong co "k" suffix
- [x] `day3_v2/day3_v2_baseline_ml.ipynb` — 28 cells, Section 0-4 hoan chinh:
  - Section 0: Setup + EDA + results = {}
  - Section 1: random / mean / median / category_mean
  - Section 2: LR simple + LR+BoW + LR+TF-IDF char_wb (raw price, khong log1p)
  - Section 3: Benchmark BoW / char_wb / Underthesea voi LGB default tren 50K subset
  - Section 4: RF (15K) + XGBoost (full 269K) + bang so sanh tong hop
- [x] `day3_v2/plan_day3_v2.md` — cap nhat: MAE primary, bo log1p, them Section 5+ MAE optimization roadmap (B1-B5)
- [x] `SESSION_HANDOFF.md` — cap nhat prompt session 16

**Push:** `git push origin feature/day5-qlora-qwen` — DONE

### Buoc tiep (session 16):
- [ ] User chay notebook tren may thue → bao cao MAE tung model
- [ ] Phan tich ket qua → chon ky thuat Section 5+ (MAE optimization)
- [ ] Viet Section 5+ vao notebook
- [ ] Final eval tren test (3,872) + save day3_v2_results.json
- [ ] Viet day3_v2_summary.md

---

## Trang thai hien tai (2026-05-16 — session 14)

**Trang thai:** Day 3 v2 khoi dong. pricer_vi_2 (items.py + evaluator.py) da tao va verify.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 14 ket qua (2026-05-16)

**Context:**
- Day 5 Run #5 (v4-scratch-v4) da chay xong truoc session nay: RMSLE=0.4608, MAE=79,589 VND, R2=62.93%, MAPE=32.78%, best ckpt step=4500. Ket qua luu tai fine_tune_qwen/results/v4_scratch_v4_results.json.
- Quyet dinh retrain Day 3 / Day 4 voi items_tv_v9 (269K) va price=round/1000.

**Da tao:**
- [x] `Data_processing_for_Vietnamese_data/day3_v2/plan_day3_v2.md` — plan day du cho Day 3 v2 (9 sections, 3 kien truc, acceptance criteria)
- [x] `Data_processing_for_Vietnamese_data/pricer_vi_2/__init__.py`
- [x] `Data_processing_for_Vietnamese_data/pricer_vi_2/items.py`
  - Item dataclass (price = round/1000, range 5-1000)
  - from_hub("SeanSunny/items_tv_v9") classmethod
  - Bo: weight, full, prompt (khong can cho Day 3)
  - Them: brand, price_vnd_true (optional)
- [x] `Data_processing_for_Vietnamese_data/pricer_vi_2/evaluator.py`
  - *(Cap nhat session 15: doi sang MAE/MSE/R2, bo RMSLE/MAPE, match English)*
  - color_for: error<40 OR ratio<20% → green; error<80 OR ratio<40% → orange
  - plot_training_history: co san (English co, pricer_vi v1 khong co)

**Quyet dinh kien truc Day 3 v2 (cap nhat session 15):**
- Price unit: round(price/1000) → range 5-1000 (align English pipeline)
- Primary metric: MAE (k VND) — KHONG dung RMSLE (da doi session 15)
- Target transform: KHONG dung log1p — train raw price (da doi session 15)
- Vectorizer chinh: TfidfVectorizer(char_wb, ngram=(2,4), 100K vocab, sublinear_tf=True)
- Underthesea: benchmark bat buoc trong Section 3
- Section 5+: chon MAE optimization technique sau khi co ket qua Section 0-4

### Buoc tiep (→ hoan thanh session 15):
- [x] Tao `day3_v2/day3_v2_baseline_ml.ipynb` (Section 0-4, 28 cells)
- [ ] Chay toan bo notebook tren may thue (CPU/RAM)
- [ ] Save `day3_v2/day3_v2_results.json`
- [ ] Viet `day3_v2/day3_v2_summary.md`

---

## Trang thai hien tai (2026-05-01 — session 13)

**Trang thai:** Day 5 Phase 4 Stage 3 — SAN SANG. Notebook `06_train_v4_scratch_v4.ipynb` da tao va fix xong. KHONG dung v2 (failed), KHONG dung v3 (malformed).
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 13 ket qua (2026-05-01)

- [x] **Phan tich Root Cause v4-scratch-v2 mode collapse:**
  RSLoRA voi r=128 → scale=alpha/sqrt(r)=22.6x → gradient spike step200 (loss 1.24→4.82→2.19) → collapse ve "199".
  Chi tiet: 17/20 val samples predict "199", R2=-0.28, RMSLE=0.9739.
- [x] **Tao 06_train_v4_scratch_v4.ipynb** — clone English reference config, fix root cause:
  r=64/alpha=128/scale=2.0x, USE_DORA=False, USE_RSLORA=False, wd=0.001, 3 epochs, NEFTune=5, batch=32.
  Output: `results/v4_scratch_v4_results.json`, `results/v4_scratch_v4_val_predictions.json`.
  HF repo: `SeanSunny/qwen3.5-4b-vn-pricer-v4-scratch-v4`.
- [x] **Fix utils/evaluator.py** — `compute_metrics` tra ve `r2 * 100` (% nhu day4).
  Truoc: 0.6639 (0-1 scale). Sau: 66.39% (0-100 scale).
- [x] **Thao luan so sanh English Llama vs Vietnamese Qwen:**
  Qwen v3 R2=66.39% (200 mau) — gan ngang PhoBERT++ (64.4%). Gap Llama chu yeu la data volume (9x) + pre-training language fit.
- [x] **Thao luan Day3/Day4 retrain voi items_tv_v9 (269K)** — plan chi tiet de lai session sau.

### Session 12 ket qua (2026-04-30)

- [x] **System reset cell** — phat hien GPU RTX 5090 load 100% khi moi thue (initialization, khong phai stale process). Cell cleanup chay OK.
- [x] **Token re-profile tren 5K sample (items_prompts_tv_4):**
  - p99=191, max=262 (aug data), trunc@208=0.42% → max_seq_length=208 xac nhan hop le.
  - p99 tu profile lan 1 (SESSION_HANDOFF ghi 196) vs lan nay (191) — chech lech nho do random sample.
- [x] **Build model:** trainable params=170,643,456 (3.9%), memory footprint=5.01 GB. DoRA voi r=128 tang 10x params so v3 (15M → 170M).
- [x] **Smoke PER_DEVICE_BATCH=20:** VRAM peak=18.93 GB (PyTorch) / ~24.8 GB (vast.ai UI), 8.64s/step, est 16.1h.
- [x] **Smoke PER_DEVICE_BATCH=28 (thu nghiem):** VRAM peak=24.39 GB (PyTorch) / 30.3-31.2 GB (vast.ai UI) → chi con 0.6 GB headroom. **ABORT** — OOM risk cao cho 17h run voi group_by_length (batch dai se spike cao hon).
- [x] **Research causal-conv1d + flash-linear-attention:** SKIP — Triton bug #176426 segfault tren sm_120 (RTX 5090 Blackwell), rui ro crash giua chung.
- [x] **CHOT CONFIG:** `PER_DEVICE_BATCH=24`, eff_batch=96, est ~17h, ~$6.60. VRAM an toan ~28 GB.

**TONIGHT:** User chay `06_train_v4_scratch_v2.ipynb` voi PER_DEVICE_BATCH=24. Constants cell can doi truoc khi chay:
```python
PER_DEVICE_BATCH = 24   # DOI TU 20 (hoac 28) → 24
GRAD_ACCUM       = 4    # giu nguyen — eff_batch = 96
```

### Session 11 ket qua (2026-04-29)
- [x] DECISION: SKIP v4-resume — ensemble cuoi se la 3-model (v3 + v4-scratch + v8).
- [x] Verify chat luong aug data `SeanSunny/items_prompts_tv_4`: 0/1000 hallucination, 0/100 issue → PASS.
- [x] Re-profile token tren aug data: p99=196, max=346 → de xuat bump `max_seq_length` 192 → **208** (trunc ~0.5%).
- [x] Tao `fine_tune_qwen/06_train_v4_scratch_v2.ipynb` (31 cells, 12 sections) — KHONG sua v1:
  + Smoke VRAM cell (30 steps, abort neu peak > 30GB), rebuild model fresh truoc full train.
  + Resume detection: local `output/last-checkpoint` → fallback HF `last-checkpoint` branch (snapshot_download).
  + `hub_strategy="checkpoint"` — auto push checkpoint moi 500 step (resilient cho vast.ai disconnect).
  + 8 charts PNG post-train (matplotlib): train/eval loss, LR, grad_norm, RMSLE timeline, scatter pred vs true (200 sample), residual hist, bucket RMSLE.
  + `max_seq_length=208`, eff_batch=80, eval_steps=500, save_total_limit=2.
  + Bug fix: capture `best_ckpt_path = trainer.state.best_model_checkpoint` truoc `del trainer`.

### Session 10 ket qua (2026-04-29)
- [x] Tao va chay `push_dataset_v9.py` — push `SeanSunny/items_tv_v9`:
  - train: 85,727 orig + 183,385 aug = **269,112** (shuffle seed=42)
  - validation: 3,926 | test: 3,872 (filter price <= 1M tu v7)
  - Schema: title, category, brand, summary (merged), price (round/1000), price_vnd_true
  - Khong co cot aug_version
- [x] Day3/Day4 chi can thay doi duong dan dataset → `SeanSunny/items_tv_v9` (code khong doi)

### Session 9 ket qua (2026-04-29)
- [x] Chay `push_dataset_v4.py` — push `SeanSunny/items_tv_v8` (183,385 train) + `SeanSunny/items_prompts_tv_4` (269,112 train).
- [x] Fix loi features mismatch (V8_FEATURES explicit schema) + fix HF upload drop connection (max_shard_size="20MB").
- [x] Tao `fine_tune_qwen/data_augmentation.md` — doc toan bo pipeline tu scraping → Day1 → Day2 → augmentation.
- [x] Stage 2 (08_augment) DONE: 85,727 orig + 183,385 aug = **269,112 train** cho items_prompts_tv_4.

### Session 8 ket qua (2026-04-28)
- [x] Tao `fine_tune_qwen/08_augment_dataset_v4.ipynb` — Stage 2 Groq Batch augmentation: merge tv6+raw_v6 → items_tv_v7, SYSTEM_PROMPT_AUG 2-dong, AugBatchManager, multiplier 5x/3x/2x/1x/4x, USER CONFIRMATION GATE, output items_prompts_tv_4.
- [x] Tao `fine_tune_qwen/06_train_v4_scratch.ipynb` — Stage 3 RTX 5090: r=128/alpha=256/DoRA/RSLoRA/NEFTune α=5/wd=0.01/eff_batch=80, best by eval_rmsle, save v4_scratch_val_predictions.json.
- [x] Tao `fine_tune_qwen/07_ensemble.ipynb` — Stage 4: Ridge log-space blend v3+v4-resume+v4-scratch+v8, graceful fallback khi thieu model, alpha grid search, test inference.
- [x] Update `fine_tune_qwen/phase2_execution_log.md` Run #4 prep.

### Session 7 ket qua (2026-04-28)
- [x] Tao `fine_tune_qwen/utils/rmsle_callback.py` — `RMSLEEvalCallback` (generative RMSLE moi 500 step, dung cho `metric_for_best_model="eval_rmsle"`).
- [x] Tao `fine_tune_qwen/05_train_v4_resume.ipynb` (22 cells) — resume tu `weights/v3_adapter/checkpoint-2680` (PeftModel.from_pretrained, is_trainable=True). LR=5e-5, NEFTune α=3, group_by_length, EarlyStop patience=3, save best by eval_rmsle.
- [x] Update plan_day5.md Section 4.3 A2: gpt-oss-120b → **gpt-oss-20b** (test 10-20 sample truoc, cost ~$3-5).
- [x] Self-review fix: transformers 5.5.0 doi `group_by_length=True` → `train_sampling_strategy="group_by_length"`.

### Da hoan thanh:
- [x] Tiki scraper — 111/113 categories, 102,117 SP
- [x] Kaggle CSV -> JSONL — 41,603 SP
- [x] Hasaki scraper — 128/130 categories, 11,410 SP
- [x] WinMart scraper — 18 categories, 3,232 SP
- [x] HF dataset `SeanSunny/items_tv_v6` (120K sample)
- [x] **Day 3 DONE:** Blended TF-IDF+LGB RMSLE=0.5164
- [x] **Day 4 v4 DONE:** AITeamVN+MLP RMSLE=0.4986
- [x] **Day 4 v6 DONE:** Blended RMSLE=0.4187 (ceiling — blending bao hoa)
- [x] **Day 4 v7 DONE (2026-04-23):** Stacked (7 models) RMSLE=0.4059, gap 0.0059
- [x] **Day 4 v8 DONE (2026-04-24):** Stacked (8 models) RMSLE=0.4004, gap 0.0004
- [x] **Day 5 plan_day5.md** (`fine_tune_qwen/plan_day5.md`, ~1100 dong, 15 sections + Section 4.5)
- [x] **Day 5 Phase 0 DONE (2026-04-25):**
  - `pyproject.toml`: da them trl, peft, bitsandbytes, accelerate, huggingface-hub
  - `fine_tune_qwen/utils/`: prompt_builder.py, evaluator.py, inference.py, hf_upload.py
  - Dataset `SeanSunny/items_prompts_tv_3` da push HF:
    - train: 85,727 | val: 3,926 | test: 3,872 (ca 3 splits filter price <= 1,000,000 VND)
    - Schema: `prompt`, `completion` (round(price/1000)), `price_vnd_true`
    - Prompt: `"San pham nay co gia bao nhieu ?\n{summary}\n\nGia la: "`
  - Token profile chinh xac (`fine_tune_qwen/profile_results_v3.json`):
    - Prompt p95 = 146 tokens | Full p95 = 149 tokens | Max = 218 tokens
    - **max_seq_length = 192** | **max_new_tokens = 4**
- [x] **Day 5 Phase 1 DONE (2026-04-26):** `02_baseline_v1.ipynb` (BnB) chay thanh cong.
  - RMSLE=4.4428 | MAE=296,807 VND | MAPE=105.9% | R2=-2.09 | 0.18s/item
  - Saved: `fine_tune_qwen/results/v0_results.json`
- [x] **Day 5 Phase 2 design DONE (2026-04-26):** plan_day5.md Section 4.5 — BnB-only, 8 decisions + 8 refinements.
- [x] **Day 5 Phase 2 implement DONE (2026-04-26):** `03_train_v1_smoke.ipynb` chay thanh cong.
  - Config: r=32, 4 attention modules, 20K data, 2 epochs, batch=16, grad_accum=4 (eff=64)
  - Train time: 162.4 min | VRAM peak: 12.81 GB | Truncation rate: 0.1%
  - RMSLE epoch 1: 0.6295 | RMSLE epoch 2: **0.6084** (primary)
  - MAE: 116,769 VND | MAPE: 50.4% | R2: 0.398
  - Saved: `fine_tune_qwen/results/v1_results.json`
- [x] **Day 5 Phase 3 v3 DONE (2026-04-27):** `04_train_v3.ipynb` chay thanh cong.
  - Config: r=64, alpha=128, 7 modules, 85,727 data, 3 epochs, batch=16, grad_accum=4 (eff=64), gradient_checkpointing=True
  - Train time: **773.4 min (~12.9h)** | VRAM peak: **13.46 GB** | OOM: 0
  - RMSLE per epoch: e1=0.5424 → e2=0.4618 → **e3=0.4426 (best)**
  - MAE: 80,100 VND | MAPE: 37.6% | R2: 0.664 | 0.19s/item
  - Saved: `fine_tune_qwen/results/v3_results.json` + `weights/v3_adapter/`
  - HF push: **`SeanSunny/qwen3.5-4b-vn-pricer-v3` (private)**
  - **Loss curve insight:** Eval CE loss overfit tu step 2600 (giua epoch 2), nhung generative RMSLE van cai thien e2→e3 (-4.2%). Day la **CE↔RMSLE divergence** — chon best checkpoint phai theo RMSLE, khong theo CE.
  - **Failure modes:** (1) bo qua so dinh luong trong title (mini sample 0.6ml predict 600K vs true 60K), (2) anchor theo category mean, (3) under-predict outlier price > 500K.
  - Log day du: `fine_tune_qwen/phase2_execution_log.md` Run #2

### Buoc tiep (Day 5 — can GPU/Groq):
- [x] **Phase 1 DONE** — v0 zero-shot RMSLE=4.4428
- [x] **Phase 2 DONE** — v1 smoke RMSLE=0.6084 (beat v0 86%)
- [x] **Phase 3 v3 DONE** — full 85K/3ep/r=64/7mod RMSLE=0.4426 (beat v1 27%, gap v8 +0.042, chua dat target 0.38)
- [~] **Phase 4 Stage 1 SKIP** — quyet dinh bo v4-resume (session 11). Ensemble = 3-model.
- [x] **Phase 4 Stage 2 DONE (2026-04-29)** — `push_dataset_v4.py`: Groq batch 183,385 aug rows → `items_tv_v8` + `items_prompts_tv_4` (269,112 train)
- [x] **Phase 4 Stage 3 prep DONE (2026-05-01)** — `06_train_v4_scratch_v4.ipynb` san sang (v2 FAILED, v4 = fixed)
- [ ] **Phase 4 Stage 3 RUN** — chay `06_train_v4_scratch_v4.ipynb` tren RTX 5090 32GB / vast.ai (~17-20h) → `results/v4_scratch_v4_val_predictions.json`
- [ ] **Phase 4 Stage 4** — chay `07_ensemble.ipynb` (CPU, ~2h): Ridge blend v3+v4-scratch+v8 (3-model — can verify graceful skip v4-resume)
- [ ] **Phase 5 final** — `09_eval_full.ipynb` + `day5_summary.md`

**Cau hinh:** Qwen3.5-4B-Base + PEFT + bitsandbytes (QLoRA 4-bit NF4) | RTX 3090 Ti 25.3GB | 4 tuan
**Unsloth: DROPPED 2026-04-26** (loi VLProcessor + user chot bo)
**max_seq_length = 208 (v4-scratch) | max_new_tokens = 4 | dataset = SeanSunny/items_prompts_tv_4**
**Target:** RMSLE < 0.38 (phu: beat v8 0.4004 standalone)

---

## Ket qua Day 4 (tom tat)

| Version | RMSLE | MAE | Gap vs 0.40 |
|---------|-------|-----|-------------|
| v6 Blended | 0.4187 | 82,766 | 0.0187 |
| v7 Stacked (7M) | 0.4059 | 81,776 | 0.0059 |
| **v8 Stacked (8M)** | **0.4004** | **79,853** | **0.0004** |

## Leaderboard tong hop (2026-04-27)

| Version | Approach | RMSLE | MAE (VND) |
|---|---|---|---|
| Day4 v8 | Stacked 8 models | **0.4004** | 79,853 |
| Day5 v3 | QLoRA Qwen3.5-4B (85K/3ep/r=64/7mod) | 0.4426 | **80,100** |
| Day5 v1 | QLoRA Qwen3.5-4B (smoke 20K/2ep/r=32/4mod) | 0.6084 | 116,769 |
| Day5 v0 | Zero-shot Qwen3.5-4B-Base | 4.4428 | 296,807 |
| Day5 v4-scratch-v2 | FAILED — mode collapse (RSLoRA scale 22.6x) | 0.9739 | 175,989 |

**Note:** v3 MAE chi cao hon v8 0.3% — gap RMSLE chu yeu do outlier (vd sample mini 0.6ml: 900% error). Fix failure mode quantity-aware co the dua v3 vuot v8.

---

## Luu y ky thuat quan trong

### Qwen3.5-4B-Base architecture (phat hien 2026-04-26)
- `Qwen3.5-4B-Base` co Vision Encoder trong architecture (Hybrid: Gated DeltaNet + sparse MoE).
  Model type = `qwen3_5`, class = `Qwen3_5ForConditionalGeneration` — day la DUNG, khong phai bug.
- **Unsloth + `Qwen/Qwen3.5-4B-Base`** → loi VLProcessor (tokenizer bi wrap nhu image processor) + FailOnRecompileLimitHit.
- **Fix:** Dung `unsloth/Qwen3.5-4B-Base` (Unsloth repo) thay vi `Qwen/Qwen3.5-4B-Base` (HF repo).
- **Fallback:** HF transformers + BitsAndBytesConfig + `Qwen/Qwen3.5-4B-Base` — stable, cham hon 2x.
- **transformers >= 5.2.0** bat buoc (Qwen3.5 dung model type `qwen3_5` chi co tu 5.2.0+).
- Instruct model co thinking mode (`<think>...</think>`) — Base model thi KHONG co.

### Day 4 / legacy
- **Checkpoint v4 keys:** `state_dict` (KHONG phai `model_state`)
- **v4-2b MLP input_size:** 1032 = 1024 (AITeamVN) + 8 (cat one-hot)
- **v4-0a DNN input_size:** 5008 = 5000 (HashingVec) + 8 (cat one-hot)
- **MLP params:** `input_size`, `hidden_sizes`, `dropout_prob` (KHONG `input_dim`/`hidden_dims`/`dropout`)
- **num_workers=0:** bat buoc Linux/WSL2
- **Stacking log-space:** feed log1p(pred) -> exp sau inference

---

## Prompt cho session moi

### Prompt L: Day 5 — Chay v4 + ghi ket qua + summary (session moi)

```
Day 5 QLoRA Qwen3.5-4B — tat ca 4 notebook da san sang (05/08/06/07). Session nay:
1. Nap ngu canh tu `scraping_data_tv/SESSION_HANDOFF.md` va `fine_tune_qwen/phase2_execution_log.md`.
2. User se thong bao ket qua training (RMSLE, loss curve, VRAM, time) sau khi chay tung notebook xong.
3. Ghi ket qua vao `phase2_execution_log.md` (Run #3 v4-resume, Run #4 v4-scratch, ensemble).
4. Neu co loi hoac ket qua bat ngo → debug theo protocol: reproduce → root cause → 1 fix → verify.
5. Sau khi tat ca stage xong: tao `fine_tune_qwen/09_eval_full.ipynb` (eval v3/v4-resume/v4-scratch/ensemble tren test 3,872) va `fine_tune_qwen/day5_summary.md`.

== DOC NGU CANH (theo thu tu) ==
1. `scraping_data_tv/SESSION_HANDOFF.md` — trang thai tong the + leaderboard
2. `fine_tune_qwen/phase2_execution_log.md` — ket qua Run #1/2/3/4 (dien vao neu trong)
3. `fine_tune_qwen/plan_day5.md` — v4 design CANONICAL (Section 4)
4. `fine_tune_qwen/results/*.json` — ket qua da co (v3, v4-resume, v4-scratch, ensemble)

== NOTEBOOK / SCRIPT DA SAN SANG ==
- `05_train_v4_resume.ipynb` — Stage 1 (3090Ti ~10h, LR=5e-5, NEFTune α=3, resume v3 ep2)
- `push_dataset_v4.py` — Stage 2 DONE: items_tv_v8 + items_prompts_tv_4 (269,112 train) da push HF
- `06_train_v4_scratch.ipynb` — Stage 3 (5090 ~16-20h, r=128/DoRA/RSLoRA/NEFTune α=5, dataset=items_prompts_tv_4)
- `07_ensemble.ipynb` — Stage 4 (CPU, Ridge log-space v3+v4r+v4s+v8)

== KEY CONSTRAINTS ==
- KHONG sua plan_day5.md (READ-ONLY).
- KHONG chay GPU tu dong — chi code/debug, user tu chay.
- transformers 5.5.0: `dtype=torch.bfloat16`, `train_sampling_strategy="group_by_length"`.
- val/test predictions luu o `fine_tune_qwen/results/*_val_predictions.json` (dung cho 07).
- v8 test predictions: export tu `day4/day4_dl_models_v8.ipynb` theo huong dan trong 07_ensemble.ipynb Section 2c.

== TARGET ==
- v4-resume: RMSLE 0.40-0.42
- v4-scratch: RMSLE 0.36-0.40
- Ensemble: RMSLE < 0.38 (P0), < 0.36 (stretch)
- Day4 v8 ref: RMSLE=0.4004
```

---

## Files quan trong

### Plan & Summary files (doc khi can nap lai ngu canh)

| File | Noi dung |
|------|---------|
| `scraping_data_tv/SESSION_HANDOFF.md` | File nay — trang thai tong the, buoc tiep, luu y ky thuat |
| `day3/plan_day3.md` | **Plan Day 3** (230 dong): toan bo qua trinh TF-IDF baseline — 3 architecture (A/B/C), log-transform, Optuna tuning, blending. Co bang ket qua 12 models, tac dong tung ky thuat, luu y Underthesea. Doc khi can hieu pipeline TF-IDF hoac reload Day3-LGB. |
| `day3/day3_summary.md` | **Summary Day 3** (260 dong): viet bang tieng Viet co dau, giai thich khai niem (tai sao log-transform, char_wb, blending). Doc nhanh de hieu Day 3 ma khong can doc code. |
| `day4/plan_day4.md` | **Plan Day 4** (160 dong): bang tong hop v4->v8 voi so lieu thuc te, ky thuat ap dung (LLRD/R-Drop/EMA), phan tich stacking weights, fallback Day 5. Co luu y checkpoint v4 (input_size). |
| `day4/day4_summary.md` | **Summary Day 4** (270 dong): viet bang tieng Viet co dau, giai thich kien truc BERT fine-tuning, tung ky thuat SOTA (tai sao can, code minh hoa), tien trinh v4->v8, phan tich stacking, ceiling analysis, so sanh Mercari benchmark. Doc nhanh de hieu toan bo Day 4. |
| `fine_tune_qwen/plan_day5.md` | **Plan Day 5** v2.0 (~470 dong, rewrite gon 2026-04-27): plan QLoRA Qwen3.5-4B-Base + PEFT/BnB. Section 0-3 = nen tang + ket qua v0/v1/v3 + lessons. **Section 4 = v4 design CANONICAL (4 stages: resume + augment + scratch + ensemble).** DOC TRUOC KHI CODE v4. |
| `fine_tune_qwen/phase2_execution_log.md` | Log thuc thi v1 (Run #1) + v3 (Run #2) day du, gom config thuc te + loss curve + samples + failure modes + leaderboard. |

### Code & weights

| File | Muc dich |
|------|----------|
| `day4/day4_dl_models_v8.ipynb` | v8 notebook (RMSLE=0.4004) |
| `day4/weights_v7/*.pth` | v7 model weights |
| `day4/weights_v8/v8_results.json` | v8 ket qua day du |
| `day4/weights_v8/stacking_config_v8.json` | v8 stacking coefs (Ridge/EN/LGB) |
| `day4/tokenized_*.pkl` | Underthesea cache (trong repo) |
| `pricer_vi/deep_neural_network.py` | DeepNeuralNetwork + MLP class |

---

*Cap nhat: 2026-05-01 (session 13) — v4-scratch-v2 FAILED (mode collapse RSLoRA). Da tao v4-scratch-v4 (fix: r=64/no-DoRA/no-RSLoRA/wd=0.001). Fix evaluator.py R2 display. Session sau: chay v4, ghi Run #5, chay 07_ensemble, tao 09_eval_full + day5_summary.*
