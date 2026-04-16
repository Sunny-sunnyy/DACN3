# Day 4: Deep Learning + Frontier LLM — Vietnamese Price Prediction

**Ngay:** 2026-04-15 (cap nhat: 2026-04-16)
**Trang thai:** v4 DA CHAY XONG — v5 PLAN (research-backed improvements)
**Branch:** `feature/data-preprocessing-vi`
**Dataset:** `SeanSunny/items_tv_v6` filtered <= 1,000,000 VND
**Data:** 85,727 train / 3,926 val / 3,872 test | 8 categories | Price: 4.9K-1M VND
**Baseline (Day 3):** Blended TF-IDF+LGB RMSLE=0.5164, MAE=110K, R2=47.1%
**Best Day 4 v4:** AITeamVN+MLP RMSLE=0.4986 (cai thien 3.4%)
**Target:** RMSLE <= 0.40 (CHUA DAT — khoang cach ~20%)

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
    day4_dl_models_v5.ipynb         # TAO MOI — v5 improvements
    day4_dl_models.py               # Reference .py (khong chay)
    day4_frontier_llm.py            # Frontier LLM (chua chay)
    *.pkl, *.npy                    # Cache tokenized + embeddings
    *.pth                           # Model weights

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

### v5 (CAN LAM)
- [ ] Huong 1: PhoBERT fine-tune (normalize target + mean pooling + early stopping)
- [ ] Huong 2: PhoBERT embed → LGB + Optuna + PCA
- [ ] Huong 3: Blending best models
- [ ] Frontier LLM: 3 models x 200 items (optional)
- [ ] Tong hop v5: bang so sanh + ket luan

---

*Tao: 2026-04-15. Cap nhat: 2026-04-16. v4 DA CHAY (best 0.4986). v5 PLAN — target 0.40.*
