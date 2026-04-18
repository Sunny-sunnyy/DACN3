# Day 4: Deep Learning — Vietnamese Price Prediction

**Cap nhat:** 2026-04-18
**Branch:** `feature/data-preprocessing-vi`
**Dataset:** `SeanSunny/items_tv_v6` filtered <= 1,000,000 VND
**Data:** 85,727 train / 3,926 val / 3,872 test | 8 categories | Price: 4.9K-1M VND
**Target:** RMSLE <= 0.40

---

## 1. Tong hop ket qua (v4 -> v6)

| Version | Best Model | Test RMSLE | MAE (VND) | Gap vs 0.40 |
|---------|-----------|-----------|-----------|-------------|
| Day 3 (baseline) | Blended TF-IDF+LGB | 0.5164 | 109,725 | 0.1164 |
| Day 4 v4 | AITeamVN+MLP (frozen) | 0.4986 | 99,786 | 0.0986 |
| Day 4 v5-old | Blended (PhoBERT+v4-2b+v4-0a+Day3) | 0.4191 | 84,550 | 0.0191 |
| **Day 4 v6** | **Blended (v6-PhoBERT+v6-PCA+LGB+v4+Day3)** | **0.4187** | **82,766** | **0.0187** |

**v6 chi tiet:**
- v6-PhoBERT full fine-tune (20ep): 0.4418 (val best = 0.4462 @ ep18)
- v6-PCA+LGB (PhoBERT embed + PCA(256) + LGB Optuna): 0.4375
- v6 Blended (5 models, weighted): 0.4187 — cai thien MARGINAL so voi v5-old

**Ket luan v6:**
- Tang epochs 10->20 KHONG HIEU QUA — overfit nang (train 0.05 vs val 0.33 = 6.6x gap)
- Blending saturated: cung 5 models, cung correlation -> ceiling ~0.4187
- Frontier LLM zero-shot kem (gpt-5-mini 0.6261, gpt-4o-mini 0.9894) — khong dung duoc

---

## 2. v7 Plan — DL Optimization (SOTA 2024-2025)

**Muc tieu:** RMSLE <= 0.40 bang DL-only, tap trung toi uu mo hinh.

**May thue:** RTX 3090 Ti 24GB VRAM | 64GB RAM | Xeon E5-2686 v4 36 cores

### 2.1. Phase A — PhoBERT++ Single Strong Model (GPU ~1.5h)

**Nguyen tac:** 1 seed, mo hinh toi uu nhat, early stop som, khong over-regularize.

| # | Ky thuat | Config | Ly do |
|---|---------|--------|-------|
| 1 | **Layer-wise LR Decay (LLRD)** | top=2e-5, decay=0.9x moi layer | Top layers can LR cao hon, bottom giu features pre-train |
| 2 | **R-Drop** | alpha=0.5, KL consistency loss | Regularization hieu qua +1.2 pts tren GLUE, khong can tang dropout |
| 3 | **EMA weights** | decay=0.999 | Eval dung EMA weights -> smoother minima, near-zero overhead |
| 4 | **Multi-task Aux Head** | category classification, alpha=0.1 | Regularize encoder, tan dung thong tin category san co |
| 5 | **Huber Loss** | delta=1.0 tren normalized log-target | Robust hon MSE voi outlier, log-price van con skew |
| 6 | **Dropout + WD** | dropout=0.2, weight_decay=0.02 | Same v6 dropout, WD tang nhe |
| 7 | **Early stop** | epochs=12, patience=3 | v6 overfit tu ep13+, stop som |
| 8 | **Batch size + AMP** | PhoBERT=80 (R-Drop 2x), XLM-R=64, AITeamVN=32 | 3090 Ti 24GB |
| 9 | **LR schedule** | lr=2e-5 base, warmup=10%, cosine | Same v5/v6 (da kiem chung) |
| 10 | **Pooling + Head** | mean pooling + LayerNorm + GELU | Same v6 (da kiem chung) |

**Pipeline code-level:**
```
y_log = log1p(price)
y_norm = (y_log - mean) / std

for epoch in range(12):
    for batch in train_loader:
        # R-Drop: forward 2 lan
        pred1, cat1 = model(batch)  # dropout mask 1
        pred2, cat2 = model(batch)  # dropout mask 2

        # Huber loss tren price
        loss_price = (huber(pred1, y) + huber(pred2, y)) / 2
        # KL consistency (R-Drop)
        loss_kl = 0.5 * (kl(pred1, pred2) + kl(pred2, pred1))
        # Aux category
        loss_cat = (ce(cat1, cat_label) + ce(cat2, cat_label)) / 2

        loss = loss_price + 0.5 * loss_kl + 0.1 * loss_cat
        backward + AdamW step + EMA update

    eval(EMA_model, val) -> rmsle
    if no_improve for 3 epochs: early stop
```

**Ky vong PhoBERT++:** 0.41-0.43 (tot hon v6-PhoBERT 0.4418)

### 2.2. Phase B — Model Diversity (GPU ~1.5h)

Tang model diversity cho stacking, moi model ap dung ky thuat Phase A.

| Model | Config | Epochs | Ky vong RMSLE |
|-------|--------|--------|--------------|
| **XLM-R base** fine-tune | LLRD + R-Drop + EMA + Huber + Aux | 12, patience=3 | 0.43-0.45 |
| **AITeamVN fine-tune** | Unfreeze top 4 layers + LLRD + EMA + Huber + Aux (**no R-Drop** — memory) | 10, patience=3 | 0.42-0.44 |

**Ly do chon 2 models nay:**
- XLM-R: multilingual, embedding space khac PhoBERT -> diversity cao
- AITeamVN: 1024d BGE-M3 (568M params) — freeze bottom 20 layers, fine-tune top 4 + heads
- AITeamVN bo R-Drop (qua lon voi 24GB) — dung batch=32 + LLRD + EMA + Aux
- Ca 2 deu da co tokenized cache tu v4/v6

### 2.3. Phase C — Stacking Meta-learner (CPU ~30 phut)

**Thay weighted blend (saturated o 0.4187) bang proper stacking.**

**Base models (7 models):**
1. PhoBERT++ (Phase A)
2. XLM-R++ fine-tune (Phase B)
3. AITeamVN++ fine-tune (Phase B)
4. v7-PCA+LGB (PhoBERT++ embed + PCA(256) + LGB, dung v6 best params)
5. v4-2b (AITeamVN frozen + MLP) — reload weights
6. v4-0a (DNN + HashingVec) — reload weights
7. Day3-LGB (TF-IDF Arch C + LGB) — reload neu co cache, retrain neu khong

**Meta training data (simplified OOF):**
- Val predictions (3,926 items) = meta-train
- Test predictions (3,872 items) = meta-test
- Ly do simplified: full 5-fold CV voi 3 BERT models qua ton GPU (~9h extra).
  Val predictions hop le lam meta-features vi moi base model eval tren val sau khi train.

**Level 2 meta-learners (ensemble 3):**
- Ridge regression (alpha=1.0, convex, robust) — log-space
- ElasticNet (alpha=0.001, l1_ratio=0.5, sparsity) — log-space
- LightGBM (n_est=200, small, non-linear) — log-space
- Final: simple average cua 3 meta predictions (exp back to VND)
- **Bonus:** so sanh voi weighted blend baseline (same v6 weights)

**Ky vong stacking:** 0.39-0.41 (vuot target 0.40)

### 2.4. Tong hop v7

| Phase | Nhiem vu | Time GPU | Ky vong RMSLE |
|-------|---------|---------|--------------|
| A | PhoBERT++ (LLRD+R-Drop+EMA+Huber+Aux, 12ep) | ~1.5h | 0.41-0.43 |
| B1 | XLM-R++ (LLRD+R-Drop+EMA+Huber+Aux, 12ep) | ~1h | 0.43-0.45 |
| B2 | AITeamVN++ top 4 layers (LLRD+EMA+Huber+Aux, 10ep, no R-Drop) | ~1h | 0.42-0.44 |
| C | Stacking 7 base models (Ridge + ElasticNet + LGB meta) | 10 phut CPU | **0.39-0.41** |
| **Tong** | | **~3.5h GPU + 10 phut CPU** | **best ~0.39-0.41** |

### 2.5. Fallback plan

Neu v7 RMSLE > 0.41 (ca stacking van khong vuot 0.40):
- Chuyen QLoRA fine-tune **Qwen3.5 4B** (khac repo, khac session)
- Ly do: DL encoder ceiling co the ~0.41, can decoder-based LLM voi scale lon hon

---

## 3. Ky thuat SOTA — References

### 3.1. Layer-wise LR Decay (LLRD)
- Ref: ModernBERT-XAI 2025 (Tandfonline). Layer gan input lr = 0.1x base, head lr = base
- Cho PhoBERT: 12 layers, decay = 0.9x moi layer -> bottom layer ~ 2.8e-6

### 3.2. R-Drop
- Ref: Liang et al. 2021 (arXiv 2106.14448), Microsoft Research
- Forward 2 lan voi dropout mask khac nhau + KL(pred1||pred2) + KL(pred2||pred1)
- Gain: +1.2 pts tren GLUE cho BERT-base, regularize manh hon dropout thuan

### 3.3. EMA (Exponential Moving Average)
- Ref: PyTorch `torch.optim.swa_utils.AveragedModel` (use_ema=True)
- Decay=0.999, maintain running average cua weights
- Eval dung EMA model -> flatter minima, better generalization

### 3.4. Huber Loss
- Ref: Nair et al. 2025 (Springer), Deep Huber Quantile Regression 2025
- Delta=1.0: MSE khi |error| < delta, MAE khi |error| > delta
- Robust voi outliers trong log-space (van con skew sau log1p)

### 3.5. Multi-task Auxiliary Head
- Ref: Stanford CS224N Multi-task BERT
- Shared encoder + 2 heads: price regression + category (8-class)
- Alpha=0.1 cho aux loss: regularize encoder, khong lan at main task

### 3.6. Stacking
- Ref: Wolpert 1992, Kaggle Mercari winner 2018 (GRU + fastText + stacking)
- 5-fold OOF tranh overfit meta-learner
- Meta-learner da dang (linear + non-linear) tranh bias

---

## 4. Luu y ky thuat (accumulated)

- **LightGBM eval keys:** `record_evaluation` dung `"training"`, `"valid_1"`. Metric: `"l2"` (KHONG `"mse"`)
- **accelerate:** Can `uv add accelerate` truoc HF Trainer
- **Loss:** MSELoss tren normalized log-space (Huber cho v7). KHONG dung L1Loss
- **Weights:** `.pth` luu kem `y_mean`, `y_std` cho inference
- **Embedding cache:** `.npy` cho AITeamVN (1024d) da co tu v4
- **v5 fix normalize target:** PhoBERT 0.5268 -> 0.4413 (breakthrough lon nhat)
- **v5 LoRA r=8 that bai:** 0.5729 — loai hoan toan khoi v6/v7
- **v6 overfit:** train 0.05 vs val 0.33 @ 20 epochs -> v7 dung R-Drop + EMA + early stop 12ep
- **DataLoader:** `num_workers=0` bat buoc (Linux WSL2 + rental Linux, tranh multiprocessing overhead)
- **v7 batch sizes (3090 Ti 24GB, fp16):** PhoBERT=80 (R-Drop 2x mem), XLM-R=64, AITeamVN=32 (568M + freeze bottom 20)
- **EMA:** `torch.optim.swa_utils.AveragedModel` + `get_ema_multi_avg_fn(0.999)` — eval va predict dung EMA model
- **R-Drop regression variant:** MSE giua 2 forward passes (thay KL vi regression dau ra scalar)
- **AITeamVN freeze:** bottom 20/24 layers freeze, top 4 + pooler + heads fine-tune (giam ~60% VRAM)

---

## 5. Files

```
day4/
    plan_day4.md                    # File nay (v4->v7)
    day4_dl_models_v4.ipynb         # v4: 12 experiments (best 0.4986)
    day4_dl_models_v5.ipynb         # v5-old: blend 0.4191
    day4_dl_models_v6.ipynb         # v6: blend 0.4187 (20ep, LayerNorm+GELU)
    day4_dl_models_v7.ipynb         # v7: DA TAO (LLRD+R-Drop+EMA+Huber+Aux+Stacking)
    day4_frontier_llm.ipynb         # Frontier LLM zero-shot (not competitive)
    weights_v5/, weights_v6/        # Weights cache
    weights_v7/                     # v7 weights (moi)
    *.pkl, *.npy                    # Tokenized + embeddings cache

pricer_vi/
    deep_neural_network.py          # DNN + MLP + train_torch_model
    evaluator.py                    # rmsle(), Tester, evaluate(), plot_predictions()
    items.py                        # Item model, from_hub()
```

---

## 6. Tieu chi hoan thanh v7

### v6 (DA CHAY)
- [x] PhoBERT full fine-tune 20ep -> 0.4418
- [x] PhoBERT embed + PCA + LGB -> 0.4375
- [x] Frontier LLM zero-shot 3 models -> 0.63-0.99 (khong competitive)
- [x] Blended 5 models -> 0.4187

### v7 (DA TAO CODE — 2026-04-18, CHUA CHAY)
- [x] Code `.py` + `.ipynb` (46 cells, 1424 dong) — san sang chay tren may thue
- [ ] Phase 2: PhoBERT++ 1 seed (LLRD+R-Drop+EMA+Huber+Aux, 12ep patience=3, batch=80)
- [ ] Phase 3: XLM-R++ (same techniques, 12ep, batch=64)
- [ ] Phase 4: AITeamVN++ top 4 layers (no R-Drop, 10ep, batch=32)
- [ ] Phase 5: Reload v4-2b/0a + Day3-LGB, tinh PhoBERT++ embed -> PCA(256) -> LGB
- [ ] Phase 6: Stacking Ridge + ElasticNet + LGB meta-learners (val as meta-train)
- [ ] Phase 7: Summary + charts + save results
- [ ] Target: RMSLE <= 0.40

---

*Tao: 2026-04-15. Cap nhat: 2026-04-18. v6 DA CHAY (0.4187, gap 0.0187). v7 CODE SAN (DL-only, SOTA 2024-2025, target 0.40) — CHO CHAY TREN 3090 Ti.*
