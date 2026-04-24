# Day 4: Deep Learning — Vietnamese Price Prediction

**Cap nhat:** 2026-04-24
**Branch:** `feature/data-preprocessing-vi`
**Dataset:** `SeanSunny/items_tv_v6` filtered <= 1,000,000 VND
**Data:** 85,727 train / 3,926 val / 3,872 test | 8 categories | Price: 4.9K-1M VND

---

## 1. Tong hop ket qua (v3 -> v8)

| Version | Best Model | Test RMSLE | MAE (VND) | Gap vs 0.40 |
|---------|-----------|-----------|-----------|-------------|
| Day 3 (baseline) | Blended TF-IDF+LGB | 0.5164 | 109,725 | 0.1164 |
| Day 4 v4 | AITeamVN+MLP (frozen) | 0.4986 | 99,786 | 0.0986 |
| Day 4 v5-old | Blended (PhoBERT+v4-2b+v4-0a+Day3) | 0.4191 | 84,550 | 0.0191 |
| Day 4 v6 | Blended (PhoBERT+PCA+LGB+v4+Day3) | 0.4187 | 82,766 | 0.0187 |
| **Day 4 v7** | **Stacked (Ridge+EN+LGB, 7 models)** | **0.4059** | **81,776** | **0.0059** |
| **Day 4 v8** | **Stacked (Ridge+EN+LGB, 8 models)** | **0.4004** | **79,853** | **0.0004** |

**Ket luan:** v8 dat RMSLE=0.4004 — cach target 0.40 chi 0.0004. Target 0.38 KHONG dat.
Ceiling cua encoder-only approach nay co the la ~0.40.

---

## 2. Ky thuat da ap dung (v7 + v8)

| Ky thuat | Version | Ket qua |
|---------|---------|---------|
| LLRD (decay=0.9, top lr=2e-5) | v7 | Giu pre-train features, giam overfit |
| R-Drop (alpha=0.5, MSE consistency) | v7 | +~0.01 RMSLE vs v6 |
| EMA (decay=0.999) | v7 | Flatter minima, eval dung EMA weights |
| Huber loss (delta=1.0, log-space) | v7 | Robust vs outliers |
| Aux head (category 8-class, alpha=0.1) | v7 | Regularize encoder |
| Stacking (Ridge+EN+LGB meta) | v7 | +3.1% vs v6 Blended |
| PhoBERT-large (370M) + gradient_checkpointing | v8 | 0.4228 vs base-v2 0.4322 |
| WeightedRandomSampler (10 price bins) | v8 | Built into PhoBERT-large training |
| Category-specific heads (8 linear) | v8 | Built into PhoBERT-large |
| Transductive PCA (fit train+val+test) | v8 | v8-PCA+LGB = 0.4301 |
| 8-model stacking pool | v8 | +1.4% vs v7 stacking |

---

## 3. v8 Chi tiet — Phan tich (2026-04-24)

### 3.1. Ket qua tung model

| Model | Test RMSLE | MAE | MAPE | R2 |
|-------|-----------|-----|------|----|
| v8-PhoBERT-large++ (370M) | 0.4228 | 83,734 | 32.7% | 66.8% |
| v8-PCA+LGB (transductive) | 0.4301 | 86,156 | 33.9% | 65.5% |
| **v8: Stacked (Ridge+EN+LGB avg)** | **0.4004** | **79,853** | **30.7%** | **69.2%** |
| v8: Weighted Blend | 0.4010 | 79,673 | 31.2% | 69.6% |

### 3.2. Stacking pool (8 models)

| Model | Ridge coef | Nhan xet |
|-------|-----------|---------|
| v8-PhoBERT-large++ | +0.431 | Dominant — mo hinh manh nhat |
| v7-AITeamVN++ | +0.213 | Complementary (1024d, khac architecture) |
| v7-PhoBERT++ | +0.164 | Base version, still useful |
| v7-XLM-R++ | +0.145 | Multilingual diversity |
| v4-2b (AITeamVN frozen) | +0.104 | Frozen emb, low overhead |
| v4-0a (DNN+HV) | +0.078 | Bag-of-words diversity |
| Day3-LGB | **-0.072** | Negative coef — hurts ensemble |
| v8-PCA+LGB | **-0.056** | Negative coef — correlated residual |

**Quan sat quan trong:** Day3-LGB va v8-PCA+LGB co **he so am** trong ca Ridge lan ElasticNet.
Meta-learner hoc duoc rang 2 models TF-IDF/PCA+LGB nay du bao systematic error theo huong nhat dinh,
phan du cua chung correlate voi phần du tong — tru ra thi chinh xac hon.
Blend weights cung gan 0 cho 2 model nay — nhat quan voi Ridge/EN.

### 3.3. mDeBERTa bi bo qua

v8 chi co 8 models thay vi 9 theo ke hoach (thieu mDeBERTa-v3-base++).
mDeBERTa co the bi skip trong qua trinh chay do loi hoac thieu weights.
**Anh huong:** Stacking pool thieu 1 model diversity source.

### 3.4. So sanh v7 vs v8

| | v7 | v8 | Cai thien |
|--|----|----|----------|
| Best single model | XLM-R++ 0.4309 | PhoBERT-large++ 0.4228 | +1.9% |
| Stacked | 0.4059 | 0.4004 | +1.4% |
| Pool size | 7 models | 8 models | +1 model |
| GPU time | ~3.5h | ~3.5h | Ngang |

### 3.5. Nhan xet tong the

- PhoBERT-large (370M) cai thien ro so voi base-v2 (135M): 0.4228 vs 0.4322 — xac nhan model scale co ich
- Stacking tiep tuc la phuong phap hieu qua nhat: 0.4004 vs best single 0.4228
- **Ceiling van la ~0.40** voi encoder-only + stacking approach tren data nay
- Target 0.38 cua v8 khong dat — gap 0.0204. Cach tan cung khi scale BERT models tren 158K items tieng Viet

---

## 4. Cac quyet dinh va bai hoc

| Quyet dinh | Ket qua |
|-----------|---------|
| LoRA r=8 (v5) | THAT BAI: 0.5729 — loai hoan toan |
| Full fine-tune (v6) | Overfit nang (train 0.05 vs val 0.33 @ 20ep) |
| Early stop ep=12, patience=3 (v7) | Giai quyet overfit — v7 tot hon v6 |
| Stacking thay weighted blend (v7) | +3.1% — decisive improvement |
| PhoBERT-large thay base-v2 (v8) | +2.2% — model scale co ich nhung khong du |
| Frontier LLM zero-shot | Kem: gpt-4o-mini 0.9894, gpt-5-mini 0.6261 — khong dung |
| num_workers=0 | Bat buoc (Linux/WSL2) tranh multiprocessing crash |

---

## 5. Fallback — Day 5

**Neu muon push RMSLE xuong duoi 0.38:**

**Option A (recommended):** QLoRA fine-tune decoder LLM
- Model: Qwen2.5-7B-Instruct hoac Gemma-3-4B-IT (multilingual SOTA 2025)
- Prompt: 5-line product summary → log1p(price) supervised
- Ly do: decoder LLM scale + instruction tuning → calibrate price range tot hon encoder
- GPU: A100 40GB (QLoRA 4-bit NF4), ~4-6h

**Option B:** Cross-lingual transfer
- Pretrain tren English Mercari data (1.4M items), fine-tune tren Vietnamese
- Risk: domain mismatch tieng Viet vs tieng Anh

**Option C:** Feature engineering them
- Trich xuat structured features: brand, model number, condition keywords
- Combine voi BERT embed trong stacking

---

## 6. Files

```
day4/
    plan_day4.md                    # File nay
    day4_dl_models_v7.ipynb         # v7: RMSLE=0.4059 (46 cells)
    day4_dl_models_v8.ipynb         # v8: RMSLE=0.4004 (45 cells)
    weights_v7/                     # PhoBERT++, XLM-R++, AITeamVN++ weights
    weights_v8/                     # PhoBERT-large++ weights + v8_results.json
    tokenized_*.pkl                 # Tokenized cache (trong repo)

pricer_vi/
    deep_neural_network.py          # DeepNeuralNetwork(input_size, hidden_size, num_layers)
                                    # MLP(input_size, hidden_sizes, dropout_prob)
    evaluator.py                    # rmsle(), Tester, evaluate()
    items.py                        # Item model, from_hub()
```

**Luu y checkpoint v4 (quan trong cho v8+ reload):**
- `model_2b_mlp_aiteamvn.pth`: keys=`state_dict/y_mean/y_std`, MLP input_size=**1032** (1024+8 cat)
- `model_0a_dnn_hv2048.pth`: keys=`state_dict/y_mean/y_std`, DNN input_size=**5008** (5000+8 cat)

---

*Tao: 2026-04-15. Cap nhat: 2026-04-24. v7 DONE (0.4059). v8 DONE (0.4004, gap 0.0004 vs 0.40). Target 0.38 chua dat. Fallback: QLoRA Qwen2.5-7B (Day 5).*
