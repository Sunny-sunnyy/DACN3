# Day 4: Deep Learning + Frontier LLM — Vietnamese Price Prediction

**Ngay:** 2026-04-15 (cap nhat: 2026-04-18)
**Trang thai:** v5-old DA CHAY (best 0.4191) — v6 DA TAO (drop LoRA, 20ep, patience=5)
**Branch:** `feature/data-preprocessing-vi`
**Dataset:** `SeanSunny/items_tv_v6` filtered <= 1,000,000 VND
**Data:** 85,727 train / 3,926 val / 3,872 test | 8 categories | Price: 4.9K-1M VND
**Baseline (Day 3):** Blended TF-IDF+LGB RMSLE=0.5164, MAE=110K, R2=47.1%
**Best Day 4 v4:** AITeamVN+MLP RMSLE=0.4986 (cai thien 3.4%)
**Best Day 4 v5-old:** Blended ensemble RMSLE=0.4191 (cai thien 18.8% vs Day 3)
**Target:** RMSLE <= 0.40 (GAP 0.0191 — gan dat)

---

## 1. KET QUA v4 (12 experiments — 2026-04-16)

| # | Model | RMSLE | MAE (VND) | MAPE | R2 | Ghi chu |
|---|-------|-------|-----------|------|----|---------|
| 2b | AITeamVN+MLP | **0.4986** | 99,786 | 39.0% | 55.3% | **Best DL** |
| 5b | AITeamVN+DNN ResBlock | 0.5038 | 102,280 | 40.0% | 53.9% | |
| 0a | DNN+HashingVec (h=2048) | 0.5066 | 102,454 | 43.7% | 53.3% | |
| — | **Day 3 Baseline** | **0.5164** | **109,725** | **44.0%** | **47.1%** | |
| 3 | XLM-R fine-tune (3 ep) | 0.5170 | 111,584 | 51.0% | 53.1% | |
| 0c | DNN+TF-IDF (h=4096) | 0.5212 | 105,011 | 44.1% | 50.6% | 309M params |
| 2a | dangvantuan+MLP | 0.5256 | 107,960 | 44.5% | 49.4% | |
| 1 | PhoBERT-v2 (3 ep) | 0.5268 | 115,287 | 47.0% | 45.5% | THAT VONG |
| 5a | dangvantuan+DNN ResBlock | 0.5414 | 112,400 | 46.8% | 46.9% | |
| 0b | DNN+TF-IDF (h=2048) | 0.5458 | 117,722 | 41.6% | 35.1% | |
| 4b | AITeamVN+LightGBM | 0.5612 | 121,151 | 49.3% | 37.6% | |
| 4a | dangvantuan+LightGBM | 0.5685 | 121,652 | 49.2% | 36.1% | |

### Phan tich cot loi

1. **AITeamVN (1024d, BGE-M3) > dangvantuan (768d, PhoBERT) o MOI head** — MLP/DNN/LGB deu thang
2. **PhoBERT THAT VONG (0.5268, ky vong 0.38-0.44)** — root cause: target khong normalize (xem Section 2)
3. **LightGBM kem tren dense embeddings** (0.56-0.57) — default params, can Optuna tune hoac PCA
4. **Overfitting la van de chinh** — DNN 77-309M params qua lon cho 85K data (train/val gap 7x)
5. **MLP nho (562K params) + frozen embed tot nhat** — it overfitting, dense semantic features

---

## 2. ROOT CAUSE ANALYSIS

### 2.1. PhoBERT/XLM-R that bai vi TARGET KHONG NORMALIZE

| | `train_torch_model` (Model 0/2/5) | HF Trainer (PhoBERT/XLM-R) |
|---|---|---|
| Target | `log1p(price)` → **normalize(mean=12.1, std=0.83)** | `log1p(price)` RAW |
| Target range | **~-2 to +2** | **~8.5 to 13.8** |
| Head init | ~0 → **gan target** | ~0 → **xa target 12 don vi** |
| Hau qua | Hoc ngu nghia tu epoch 1 | Ton 1-2/3 epochs chi de shift scale |

**Minh chung:** PhoBERT 135M params (0.5268) thua MLP 562K params (0.4986). Van de la training pipeline, khong phai model.

### 2.2. So sanh English vs Vietnamese

| | English (MAE $46.49) | Vietnamese (RMSLE 0.4986) |
|---|---|---|
| Data | **800K** train | 85K train (**10x it**) |
| DNN | 289M params | 77M params (da overfit) |
| Best | DNN ResidualBlock | AITeamVN+MLP (frozen embed) |

85K data khong du cho DNN lon. MLP nho + frozen embedding la phu hop.

### 2.3. LightGBM kem tren dense embeddings

- TF-IDF (10K sparse) + LGB = 0.52 (Day 3, tuned)
- Embedding (768/1024 dense) + LGB = 0.56-0.57 (default params)
- LGB `num_leaves=31` qua nho cho 768-1024 features. Can Optuna tune + PCA(256) giam noise.

---

## 3. RESEARCH FINDINGS (2024-2025)

### 3.1. Khong co paper nao ve Vietnamese product price prediction

- Tim tren Google Scholar, arXiv, NAACL, ACL Anthology — khong co ket qua
- Paper gan nhat: Mercari Kaggle (English), Airbnb/house pricing (khac domain)
- **Implication:** Chung ta dang lam bai toan moi, khong co benchmark truc tiep

### 3.2. Mercari Kaggle: RMSLE=0.428 voi GRU (khong can BERT)

- Data: ~1.4M products, price $0-$2000
- Best: GRU + fastText + engineered features = **RMSLE 0.428**
- **Implication:** Target 0.40 kha thi voi 85K data, nhung can optimize tot

### 3.3. Mean Pooling > CLS token cho regression

- Paper BERT regression (2023-2024): CLS token la weakest pooling cho regression
- **Mean pooling tren last hidden state** cho representation tot hon
- Fix: thay `outputs.last_hidden_state[:, 0]` bang `outputs.last_hidden_state.mean(dim=1)`

### 3.4. LoRA (r=8, alpha=16) tot hon full fine-tune khi data < 100K

- Full fine-tune 135M params voi 85K samples → overfitting risk cao
- LoRA chi train ~0.5-1M adapter params → regularization tu nhien
- Ket hop voi **reinitialize top 2-3 BERT layers** truoc fine-tune (giam variance)

### 3.5. Gradual Unfreezing + LLRD

- **Gradual Unfreezing:** Epoch 1-2 chi train head → epoch 3+: unfreeze top layers dan
- **Layer-wise LR Decay (LLRD):** top layer lr=2e-5, moi layer thap hon nhan 0.9x
- Tranh catastrophic forgetting, giu pre-trained features

### 3.6. PCA(256) tren embeddings truoc LightGBM

- Giam 768/1024d → 256d: regularization + tang toc
- LGB xu ly 256 features tot hon 1024 features (giam curse of dimensionality)

### 3.7. Giu stopwords — dung xoa

- Mercari Kaggle finding: removing stopwords tang RMSLE
- Tieng Viet: stopwords chua thong tin ve loai san pham ("cho", "cua", "voi")
- **Quyet dinh:** Khong dung stop_words filter

### 3.8. 85K data la du cho BERT regression

- Paper CamemBERT (French): converge voi chi 660 items cho regression
- Van de cua chung ta khong phai data it, ma la training pipeline (normalize target)

---

## 4. DAY 4 v5 PLAN — 3 huong cai thien

**Target:** RMSLE <= 0.40
**File:** `day4_dl_models_v5.ipynb` (tao moi, chay tren may thue)

### Huong 1: Fix PhoBERT fine-tune (UU TIEN CAO — ky vong 0.42-0.46)

| Thay doi | v4 (cu) | v5 (moi) |
|----------|---------|----------|
| **Target** | `log1p(price)` raw ~8-14 | `(log1p - mean) / std` ~-2 to +2 |
| **Epochs** | 3 | 5-10 + early stopping (patience=2) |
| **Pooling** | CLS token (HF default) | **Mean pooling** last hidden state |
| **LR schedule** | Linear decay | Warmup 10% + cosine decay |
| **Gradient clip** | Khong | `max_grad_norm=1.0` |
| **Eval metric** | eval_loss | Custom RMSLE callback |

**Nang cao (neu co thoi gian):**
- **LoRA (r=8, alpha=16):** Chi train adapter params ~0.5M thay vi full 135M
- **Reinitialize top 2 layers:** Giam variance, cho head adapt tot hon
- **Gradual Unfreezing + LLRD:** Top lr=2e-5, moi layer x0.9

**Pipeline:**
```python
# 1. Normalize target
y_log = torch.log1p(prices)
y_mean, y_std = y_log.mean(), y_log.std()
y_norm = (y_log - y_mean) / y_std  # ~-2 to +2

# 2. Mean pooling thay CLS
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size())
    return (token_embeddings * mask_expanded).sum(1) / mask_expanded.sum(1)

# 3. Custom PhoBERT regression model
class PhoBERTRegressor(nn.Module):
    def __init__(self, model_name="vinai/phobert-base-v2"):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.regressor = nn.Sequential(
            nn.Linear(768, 256), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(256, 1)
        )
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = mean_pooling(outputs, attention_mask)
        return self.regressor(pooled)

# 4. Train voi train_torch_model style (normalize + MSELoss)
# 5. Inference: pred_price = expm1(pred * y_std + y_mean)
```

**Thoi gian:** ~1-2h GPU | **Ky vong:** RMSLE 0.42-0.46

---

### Huong 2: PhoBERT embedding → LightGBM (UU TIEN CAO — ky vong 0.44-0.48)

**Research:** Frozen BERT embed + GBDT thuong tot hon fine-tune BERT khi data < 100K.

**Pipeline:**
```
Step 1: Load PhoBERT (hoac fine-tuned tu Huong 1)
Step 2: Extract mean-pooled embedding (85K x 768) → cache .npy
Step 3: PCA 768d → 256d (giam noise, regularization)
Step 4: Concat: PCA_256d + category_8d = 264 features
Step 5: LightGBM + Optuna tune (target = log1p(price))
Step 6: Evaluate
```

**So sanh voi v4 Model 4a/4b:** v4 dung general-purpose embedding (dangvantuan/AITeamVN). Huong nay dung PhoBERT [CLS]/mean-pool — contextual, co the adapt sau fine-tune.

**Thoi gian:** ~30 phut GPU + 10 phut CPU | **Ky vong:** RMSLE 0.44-0.48

---

### Huong 3: Blending best models (ON DINH — ky vong 0.43-0.47)

**Y tuong:** Moi model co strengths khac nhau → ensemble cai thien:
- AITeamVN+MLP (0.4986): semantic understanding
- DNN+HashingVec (0.5066): keyword matching
- Day 3 LGB+TF-IDF (0.5164): n-gram patterns
- PhoBERT v5 (sau Huong 1): contextual understanding

**A. Simple Blending:**
```python
# Tim weight toi uu tren val set (scipy.minimize)
pred_final = w1*pred_2b + w2*pred_0a + w3*pred_day3 + w4*pred_phobert
```

**B. Stacking (meta-learner):**
```python
# Level 1: OOF predictions tu base models
# Level 2: Ridge/LGB train tren stacked predictions
```

**Thoi gian:** ~30 phut CPU | **Ky vong:** RMSLE 0.43-0.47

---

### Thu tu thuc hien

| Phase | Huong | GPU? | Thoi gian | Dependencies |
|-------|-------|------|-----------|-------------|
| v5-A | Fix PhoBERT fine-tune | Co | 1-2h | Khong |
| v5-B | PhoBERT embed → LGB | Co | 1h | Sau v5-A |
| v5-C | Blending best models | Khong | 30 phut | Sau v5-A+B |

**Tong thoi gian may thue:** ~3-4h

### Bang ky vong v5

| Model | Ky vong RMSLE | vs Day 3 (0.5164) |
|-------|---------------|-------------------|
| PhoBERT v5 (fixed) | 0.42-0.46 | +12-19% |
| PhoBERT embed + LGB | 0.44-0.48 | +7-15% |
| Blended ensemble | 0.43-0.47 | +9-17% |
| **Best possible** | **0.40-0.44** | **+15-23%** |

---

## 5. LUU Y KY THUAT

- **LightGBM eval keys:** `record_evaluation` dung `"training"`, `"valid_1"` (KHONG phai `"valid_0"`). Metric: `"l2"` (KHONG phai `"mse"`)
- **accelerate:** Can `uv add accelerate` truoc khi chay HF Trainer
- **PhoBERT warning:** `Some weights not initialized` — binh thuong (classifier head moi)
- **Loss function:** MSELoss tren normalized log-space (truc tiep optimize RMSLE). KHONG dung L1Loss
- **Model weights:** Luu/load `.pth` de skip retraining. Luu kem `y_mean`, `y_std` cho inference
- **Embedding cache:** `.npy` files cho dangvantuan (768d) va AITeamVN (1024d) da co tu v4

---

## 6. FILES

```
day4/
    plan_day4.md                    # File nay
    day4_dl_models_v4.ipynb         # DA CHAY — 12 experiments, ket qua o Section 1
    day4_dl_models_v5.ipynb         # DA CHAY — v5-old ket qua o Section 8
    day4_dl_models_v6.ipynb         # TAO MOI — v6 (drop LoRA, 20ep, Frontier LLM)
    day4_dl_models_v6.py            # Reference .py cho v6
    day4_dl_models.py               # Reference .py v4 (khong chay)
    day4_frontier_llm.py            # Frontier LLM standalone (da tich hop vao v6)
    weights_v5/                     # v5-old weights (reuse caches)
    weights_v6/                     # v6 weights (tao moi khi chay)
    *.pkl, *.npy                    # Cache tokenized + embeddings

pricer_vi/
    deep_neural_network.py          # DNN + MLP + train_torch_model (REFERENCE cho normalize target)
    evaluator.py                    # rmsle(), mape(), Tester, evaluate(), plot_predictions()
    items.py                        # Item model, from_hub()
```

---

## 7. TIEU CHI HOAN THANH

### v4 (DA XONG)
- [x] 12 DL experiments. Best: AITeamVN+MLP RMSLE=0.4986
- [x] Root cause: PhoBERT target khong normalize
- [x] Model weights saved

### v5-old (DA CHAY — 2026-04-17)
- [x] v5-A1: PhoBERT full fine-tune — **RMSLE=0.4413** (10ep, 93 phut)
- [x] v5-A2: PhoBERT + LoRA r=8 — RMSLE=0.5729 (THAT BAI, r qua nho)
- [x] v5-B: PhoBERT embed + PCA + LGB — **RMSLE=0.4357** (Optuna 50 trials)
- [x] v5-C: Blending — **RMSLE=0.4191** (gap 0.0191 den target)
- [ ] Frontier LLM: 3 models x 200 items (optional)

### v6 (DA TAO — 2026-04-18)
- [ ] Phase 2: PhoBERT full fine-tune (20 epochs, patience=5, LayerNorm+GELU head, batch=96)
- [ ] Phase 3: PhoBERT embed -> PCA(256) -> LGB + Optuna
- [ ] Phase 4: Frontier LLM (gpt-4o-mini, gpt-5-nano, gpt-5-mini, 200 items)
- [ ] Phase 5: Blending (v6 + v4 + Day3) — ky vong 0.39-0.41
- [ ] Phase 6: Tong hop + charts

---

## 8. KET QUA v5-old (2026-04-17) — batch_size=64, LoRA r=8, ReLU head

**Config:** PhoBERT-base-v2 | batch_size=64 | num_workers=0 | ReLU head (khong LayerNorm) | LoRA r=8, alpha=16, targets=[query, value]

**May thue:** RTX 5060 Ti 16GB VRAM | i5-13400F 12C | 28GB RAM | Thoi gian: ~3.5h

### 8.1. Ket qua chi tiet

| # | Model | RMSLE | MAE (VND) | MAPE | R2 | Thoi gian | Ghi chu |
|---|-------|-------|-----------|------|----|-----------|---------|
| **v5-C** | **Blended ensemble** | **0.4191** | **84,550** | **33.6%** | **67.2%** | 15 phut | **BEST v5** |
| v5-B | PhoBERT embed+PCA+LGB | 0.4357 | 88,669 | 34.8% | 63.8% | ~30 phut | Optuna 50 trials |
| v5-A1 | PhoBERT full fine-tune | 0.4413 | 88,206 | 34.7% | 64.5% | ~93 phut (10ep) | Khong early stop |
| — | v4 AITeamVN+MLP | 0.4986 | 99,786 | 39.0% | 55.3% | — | Baseline v4 |
| — | Day 3 Blended (TF-IDF) | 0.5164 | 109,725 | 44.0% | 47.1% | — | Baseline Day 3 |
| v5-A2 | PhoBERT + LoRA (r=8) | 0.5729 | 124,188 | 50.9% | 36.0% | ~79 phut (10ep) | **THAT BAI** |

### 8.2. v5-A1: PhoBERT Full Fine-tune — Training Log

```
Epoch  1/10 (559s) | Train: 0.6636 | Val: 0.5168 | RMSLE: 0.5561 | MAE: 116,241
Epoch  2/10 (560s) | Train: 0.4479 | Val: 0.4220 | RMSLE: 0.5026 | MAE: 102,332
Epoch  3/10 (555s) | Train: 0.3413 | Val: 0.3801 | RMSLE: 0.4770 | MAE:  96,496
Epoch  4/10 (557s) | Train: 0.2694 | Val: 0.3686 | RMSLE: 0.4697 | MAE:  92,963
Epoch  5/10 (557s) | Train: 0.2157 | Val: 0.3565 | RMSLE: 0.4619 | MAE:  91,037
Epoch  6/10 (555s) | Train: 0.1752 | Val: 0.3482 | RMSLE: 0.4565 | MAE:  90,055
Epoch  7/10 (557s) | Train: 0.1445 | Val: 0.3495 | RMSLE: 0.4574 | MAE:  89,265
Epoch  8/10 (567s) | Train: 0.1245 | Val: 0.3468 | RMSLE: 0.4556 | MAE:  88,565
Epoch  9/10 (555s) | Train: 0.1113 | Val: 0.3472 | RMSLE: 0.4559 | MAE:  88,320
Epoch 10/10 (555s) | Train: 0.1074 | Val: 0.3464 | RMSLE: 0.4554 | MAE:  88,221
Restored best: Val RMSLE=0.4554
```

**Nhan xet A1:**
- Converge tot, RMSLE giam deu tu 0.5561 -> 0.4554 (val)
- Train loss giam manh (0.66 -> 0.11) nhung val loss giam cham (0.52 -> 0.35) — dau hieu overfitting nhe
- Khong early stop (best epoch 10, patience=3 khong trigger) — model van dang hoc
- Test RMSLE=0.4413 tot hon val 0.4554 — test set "de" hon val
- **Fix normalize target thanh cong:** v4 PhoBERT 0.5268 -> v5 0.4413 = cai thien 16.2%

### 8.3. v5-A2: PhoBERT + LoRA (r=8) — Training Log

```
Epoch  1/10 (473s) | Train: 0.8786 | Val: 0.7206 | RMSLE: 0.6568 | MAE: 143,139
Epoch  2/10 (472s) | Train: 0.6703 | Val: 0.6476 | RMSLE: 0.6226 | MAE: 134,691
Epoch  3/10 (473s) | Train: 0.6303 | Val: 0.6236 | RMSLE: 0.6109 | MAE: 131,836
Epoch  4/10 (473s) | Train: 0.6074 | Val: 0.6090 | RMSLE: 0.6037 | MAE: 129,255
Epoch  5/10 (473s) | Train: 0.5936 | Val: 0.6061 | RMSLE: 0.6023 | MAE: 128,486
Epoch  6/10 (473s) | Train: 0.5821 | Val: 0.5905 | RMSLE: 0.5945 | MAE: 126,770
Epoch  7/10 (472s) | Train: 0.5752 | Val: 0.5858 | RMSLE: 0.5921 | MAE: 126,226
Epoch  8/10 (473s) | Train: 0.5711 | Val: 0.5857 | RMSLE: 0.5921 | MAE: 125,966
Epoch  9/10 (472s) | Train: 0.5683 | Val: 0.5834 | RMSLE: 0.5909 | MAE: 125,746
Epoch 10/10 (473s) | Train: 0.5676 | Val: 0.5836 | RMSLE: 0.5910 | MAE: 125,721
Restored best: Val RMSLE=0.5909
```

**Nhan xet A2:**
- **THAT BAI NANG — kem hon ca v4 PhoBERT (0.5268)**
- Train loss giam rat cham (0.88 -> 0.57 sau 10 epochs), model chua converge
- Val RMSLE chi dat 0.5909 — kem hon Day 3 baseline (0.5164)
- **Root cause:** r=8, targets=[query, value] qua nho — chi ~295K LoRA params, khong du capacity
- Toc do nhanh hon A1 (473s vs 559s/epoch) nhung vo nghia khi ket qua kem

### 8.4. v5-B: PhoBERT Embedding + PCA + LGB

- PCA 768d -> 256d: **variance retained = 92.50%**
- Optuna 50 trials (471s): best val RMSLE=0.4495
- Best params: `num_leaves=204, min_child_samples=43, feature_fraction=0.63, learning_rate=0.027`
- Test RMSLE=0.4357 — **tot hon A1 (0.4413)** du chi dung frozen embedding

**Nhan xet B:**
- PhoBERT fine-tuned embedding + PCA + tuned LGB > PhoBERT fine-tune truc tiep
- Chung to: embedding quality cua fine-tuned PhoBERT rat tot, chi can head phu hop (LGB > linear head)
- PCA 256d giu 92.5% variance — giam noise hieu qua

### 8.5. v5-C: Blending — Weights + Phan tich

**Blend weights (val RMSLE=0.4303):**

| Model | Weight | Ghi chu |
|-------|--------|---------|
| v5-A1 (PhoBERT full) | **0.578** | Dominant — contextual understanding |
| v4-2b (AITeamVN+MLP) | **0.279** | Complementary — different embedding space |
| v4-0a (DNN+HashingVec) | 0.111 | Keyword matching |
| Day3-LGB | 0.032 | Minimal contribution |
| v5-A2 (LoRA) | 0.000 | Loai bo hoan toan |
| v5-B (PCA+LGB) | 0.000 | Loai bo (trung voi A1 embedding) |

**Nhan xet C:**
- Blend RMSLE=0.4191 — **tot hon moi model don le**
- v5-A1 chiem 57.8% — PhoBERT fine-tuned la backbone chinh
- v4-2b (AITeamVN) chiem 27.9% — bo sung goc nhin khac (different embedding model)
- v5-B bi loai du RMSLE tot (0.4357) — correlation cao voi A1 (cung PhoBERT embedding)
- v5-A2 bi loai hoan toan — confirm LoRA r=8 that bai

### 8.6. So sanh tien do

| Version | Best RMSLE | vs Day 3 | vs Target (0.40) |
|---------|-----------|----------|-----------------|
| Day 3 v3 | 0.5164 | baseline | gap 0.1164 |
| Day 4 v4 | 0.4986 | +3.4% | gap 0.0986 |
| **Day 4 v5-old** | **0.4191** | **+18.8%** | **gap 0.0191** |

### 8.7. Nhan xet tong hop v5-old

1. **Fix normalize target la breakthrough lon nhat:** PhoBERT 0.5268 -> 0.4413 (cai thien 16.2%)
2. **LoRA r=8 qua nho:** 0.5729 — kem hon ca v4. Can tang rank va them key module
3. **PCA+LGB la strong alternative:** 0.4357, tot hon fine-tune head, re hon (30 phut vs 93 phut)
4. **Blending hieu qua:** 0.4191 — PhoBERT (58%) + AITeamVN (28%) bo sung tot
5. **Gap den target chi con 0.0191** — can optimize them de vuot 0.40

### 8.8. v6: Thay doi tu v5-old (2026-04-18)

| Thay doi | v5-old | v6 | Ly do |
|----------|--------|-----|-------|
| **LoRA** | r=8, alpha=16, [q,v] | **BO** | That bai 0.5729, khong hieu qua |
| **Head** | ReLU, khong LayerNorm | LayerNorm(768) + GELU + Xavier init | Stabilize mean-pool output |
| **Dropout** | 0.1 | 0.2 | Regularize full fine-tune |
| **Epochs** | 10 | **20** | Cosine LR hit 0 at ep10, model van hoc |
| **Patience** | 3 | **5** | Cho model vuot qua plateaus |
| **batch_size** | 64 | 96 | VRAM chi dung 8.9/16 GB |
| **num_workers** | 0 | 4 | CPU chi dung 10% |
| **Frontier LLM** | Khong | 200 items x 3 models | Benchmark zero-shot |
| **Weights dir** | weights_v5 | **weights_v6** | Tach biet ket qua |

**Ky vong v6:**
- PhoBERT full (20ep): 0.40-0.44 (tot hon v5-old 0.4413 nho head + epochs)
- PCA+LGB: 0.42-0.44 (dung v6 embedding moi)
- Blended: **0.39-0.41** (vuot target 0.40)

**Files:**
- `day4_dl_models_v6.py` — .py reference
- `day4_dl_models_v6.ipynb` — chay tren may thue

---

*Tao: 2026-04-15. Cap nhat: 2026-04-18. v5-old DA CHAY (best 0.4191, gap 0.0191). v6 DA TAO (drop LoRA, 20ep).*
