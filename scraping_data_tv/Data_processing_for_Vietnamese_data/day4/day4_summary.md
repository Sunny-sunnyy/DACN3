# Day 4 — Deep Learning: Vietnamese Price Prediction

**Mục tiêu:** Vượt qua ceiling TF-IDF của Day 3 (RMSLE=0.5164) bằng DL embeddings + fine-tuning.  
**Target:** RMSLE <= 0.40  
**Kết quả tốt nhất:** RMSLE = **0.4004** (v8 Stacked, 8 models)

---

## 1. Dữ liệu đầu vào

Giữ nguyên từ Day 3:

| Split | Số lượng |
|-------|---------|
| Train | 85,727  |
| Val   | 3,926   |
| Test  | 3,872   |

**Dataset:** `SeanSunny/items_tv_v6` — filter giá <= 1,000,000 VND, 8 danh mục.  
**Input text:** `item.summary` (5 dòng mô tả do LLM rewrite ở Day 2) + `item.category`.

---

## 2. Kiến trúc DL (áp dụng từ v6 trở đi)

### 2a. BERT-style Fine-tuning

```
input_ids, attention_mask
    → BERT encoder (PhoBERT / XLM-R / AITeamVN)
    → mean pooling (weighted by attention mask)
    → LayerNorm(hidden_size)
    → Linear(hidden_size, 256) → GELU → Dropout(0.2)
    → price_head: Linear(256, 1)   ← predict log-normalized price
    → cat_head:   Linear(256, 8)   ← aux task: category classification
```

**Target transform:**
```python
y_log  = log1p(price)
y_norm = (y_log - mean) / std   # train trên normalized, eval = expm1(pred * std + mean)
```

**Loss (v7+):**
```
loss = Huber(pred, y) + 0.5 * MSE(pred1, pred2)  # R-Drop
     + 0.1 * CrossEntropy(cat_logits, cat_label)  # Aux
```

### 2b. Các model BERT sử dụng

| Model | Params | Ngôn ngữ | Ghi chú |
|-------|--------|----------|---------|
| `vinai/phobert-base-v2` | 135M | Tiếng Việt | Baseline DL, BPE + word-segment |
| `FacebookAI/xlm-roberta-base` | 278M | Multilingual | Diversity cho stacking |
| `AITeamVN/gte-Qwen2-7B` (BGE-M3 1024d) | 568M | Multilingual | Freeze bottom 20/24 layers |
| `vinai/phobert-large` | 370M | Tiếng Việt | v8: model scale experiment |

### 2c. Frozen Embeddings + MLP (v4)

Trước khi fine-tune, thử dùng AITeamVN như feature extractor:

```
text → AITeamVN(frozen) → 1024d embedding
     → concat OneHot(category) → 1032d
     → MLP([512, 256, 128]) → price
```

**Kết quả:** RMSLE=0.4986 — frozen embeddings không đủ, cần fine-tune.

---

## 3. Kỹ thuật tối ưu (v7 — SOTA 2024-2025)

### 3a. Layer-wise LR Decay (LLRD)

```python
# Top layer: lr = 2e-5, decay 0.9x mỗi layer xuống dưới
# Bottom layer: lr ≈ 2.8e-6 (giữ pre-trained features)
param_groups = build_llrd_param_groups(model, base_lr=2e-5, decay=0.9)
```

**Tại sao cần:** Các layer dưới của BERT đã học được linguistic patterns — LR lớn sẽ phá hỏng chúng. Layer trên cần LR cao hơn để adapt sang task mới.

### 3b. R-Drop (Regression variant)

```python
# Forward 2 lần với dropout mask khác nhau
pred1, cat1 = model(batch)   # mask 1
pred2, cat2 = model(batch)   # mask 2
loss_rdrop = F.mse_loss(pred1, pred2)  # consistency (KHÔNG dùng KL vì regression)
```

**Ref:** Liang et al. 2021 (+1.2 pts GLUE cho BERT-base).  
**Regression variant:** MSE thay vì KL divergence vì output là scalar.

### 3c. EMA Weights

```python
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
ema_model = AveragedModel(model, multi_avg_fn=get_ema_multi_avg_fn(0.999))
# Mỗi step: ema_model.update_parameters(model)
# Eval dùng: ema_model (flatter minima, better generalization)
```

### 3d. Huber Loss (log-space)

```python
loss_fn = nn.HuberLoss(delta=1.0)   # MSE khi |err| < 1, MAE khi > 1
# Tại sao: phân phối log-price vẫn còn skew → outlier ảnh hưởng nếu dùng MSE thuần
```

### 3e. Multi-task Auxiliary Head

```python
loss = loss_price + 0.1 * loss_category   # alpha=0.1
# Tại sao: category head regularize encoder, tận dụng label có sẵn
```

### 3f. WeightedRandomSampler (v8)

```python
log_prices = np.log1p(train_prices)
bins = pd.qcut(log_prices, q=10, labels=False)
sample_weights = 1.0 / bin_counts[bins]
sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)
```

**Tại sao:** 60%+ train set là mid-price (200-300K VND) → model bias về mid-price. Sampler cân bằng distribution.

### 3g. Category-specific Regression Heads (v8)

```python
self.price_heads = nn.ModuleList([
    nn.Sequential(LayerNorm, Linear(h, 256), GELU, Dropout, Linear(256, 1))
    for _ in range(8)  # 8 heads = 8 categories
])
# Forward: price_heads[category_id](pooled)
```

**Tại sao:** 1 shared head phải học 8 price distributions khác nhau (Bách Hóa 5K-100K vs Ô Tô 200K-1M).

---

## 4. Stacking Meta-learner (v7+)

### Vấn đề với Weighted Blend

v6 đạt 0.4187 với weighted blend — nhưng 5 model đều correlated (cùng PhoBERT foundation) → blending bão hòa.

### Giải pháp: Proper Stacking

```
Base models: predict trên val set → val_preds (N_val × n_models)
Meta input:  log1p(val_preds)     # log-space features
Meta train:  Ridge, ElasticNet, LGB   (trên val_preds → val_labels)
Meta test:   Ridge, ElasticNet, LGB   (trên test_preds)
Final:       simple average của 3 meta predictions → expm1 → VND
```

**Tại sao log-space cho meta-features:** Meta-learner học trọng số tuyến tính tốt hơn trong log-space (tránh scale mismatch giữa các model).

**LGB early stopping fix (v8):** v7 dùng toàn bộ val set làm eval → overfit. v8 split 80/20 val làm meta-train/early-stop.

---

## 5. Tiến trình kết quả — v4 đến v8

| Version | Approach | Best RMSLE | Cải thiện |
|---------|----------|-----------|-----------|
| Day 3 baseline | TF-IDF + LGB blend | 0.5164 | — |
| v4 | AITeamVN frozen + MLP | 0.4986 | +3.4% |
| v5-old | PhoBERT full fine-tune + blend | 0.4191 | +18.9% |
| v6 | PhoBERT 20ep + PCA+LGB + blend | 0.4187 | +19.0% (ceiling) |
| v7 | LLRD+R-Drop+EMA + Stacking 7M | 0.4059 | +21.4% |
| **v8** | **PhoBERT-large + Stacking 8M** | **0.4004** | **+22.5%** |

### v7 — Chi tiết từng model

| Model | RMSLE | MAE | MAPE | R2 |
|-------|-------|-----|------|----|
| XLM-R++ | 0.4309 | 86,293 | 34.4% | 65.6% |
| PhoBERT++ | 0.4322 | 87,584 | 33.7% | 64.4% |
| AITeamVN++ (top 4 layers) | 0.4350 | 86,940 | 33.7% | 65.0% |
| v7-PCA+LGB | 0.4333 | 88,761 | 34.6% | 64.3% |
| **v7 Stacked** | **0.4059** | **81,776** | **31.3%** | **68.3%** |
| v7 Weighted Blend | 0.4063 | 81,569 | 32.0% | 68.7% |

### v8 — Chi tiết từng model

| Model | RMSLE | MAE | MAPE | R2 |
|-------|-------|-----|------|----|
| PhoBERT-large++ (370M) | 0.4228 | 83,734 | 32.7% | 66.8% |
| v8-PCA+LGB (transductive) | 0.4301 | 86,156 | 33.9% | 65.5% |
| **v8 Stacked** | **0.4004** | **79,853** | **30.7%** | **69.2%** |
| v8 Weighted Blend | 0.4010 | 79,673 | 31.2% | 69.6% |

---

## 6. Frontier LLM Zero-shot (thất bại)

Thử GPT làm pricer không cần training:

| Model | RMSLE | MAE | Nhận xét |
|-------|-------|-----|---------|
| gpt-4o-mini | 0.9894 | 248,393 | Worse than median baseline |
| gpt-5-nano | 0.7025 | 157,939 | Không competitive |
| gpt-5-mini | 0.6261 | 131,132 | Vẫn tệ hơn Day 3 TF-IDF |

**Kết luận:** LLM zero-shot không calibrate giá VND tốt. Cần fine-tune hoặc RAG với price catalog. Loại bỏ hoàn toàn khỏi pipeline.

---

## 7. Phân tích Stacking Weights

Từ `stacking_config_v8.json` (Ridge coefficients):

| Model | Ridge coef | Ý nghĩa |
|-------|-----------|---------|
| v8-PhoBERT-large++ | **+0.431** | Dominant — model mạnh nhất, weight cao nhất |
| v7-AITeamVN++ | +0.213 | Bổ sung tốt (1024d, architecture khác) |
| v7-PhoBERT++ | +0.164 | Phiên bản base, still useful |
| v7-XLM-R++ | +0.145 | Multilingual diversity |
| v4-2b (frozen MLP) | +0.104 | Ensemble member nhỏ, ít overfit |
| v4-0a (DNN+HV) | +0.078 | Bag-of-words, diversity source |
| Day3-LGB | **-0.072** | Negative — hurts ensemble |
| v8-PCA+LGB | **-0.056** | Negative — correlated residual |

**Quan sát quan trọng:** Day3-LGB và v8-PCA+LGB có **hệ số âm** trong cả Ridge lẫn ElasticNet. Meta-learner học được rằng phần dư của 2 model TF-IDF/PCA này tương quan có hướng nhất định — trừ ra thì chính xác hơn. Weighted blend cũng cho weight ≈ 0 với 2 model này. **Kết luận: TF-IDF features và các biến thể không bổ sung giá trị vào stacking khi đã có BERT-based models.**

---

## 8. Bài học từ các quyết định sai

| Thử nghiệm | Kết quả | Lý do thất bại |
|-----------|---------|---------------|
| LoRA r=8 (v5) | 0.5729 (+11% tệ hơn v6) | LoRA underfits cho regression task — cần full fine-tune |
| Tăng epochs 10→20 (v6) | Không cải thiện, overfit nặng | Train RMSLE 0.05 vs val 0.33 @ ep20 — 6.6x gap |
| Frontier LLM zero-shot | 0.63-0.99 | Không calibrate được đơn vị tiền VND |
| Weighted blend saturated | 0.4187 (ceiling v5→v6) | 5 model đều correlated, blending bão hòa |

---

## 9. Impact của từng cải tiến

| Kỹ thuật | RMSLE trước → sau | Cải thiện |
|---------|-------------------|-----------|
| Frozen embed → full fine-tune | 0.4986 → 0.4418 | **-11.4%** |
| Blending (v5 style) | 0.4418 → 0.4187 | -5.2% |
| LLRD + R-Drop + EMA + Huber | 0.4418 → 0.4322 (PhoBERT++) | -2.2% |
| Stacking (7M) vs blend | 0.4187 → 0.4059 | **-3.1%** |
| PhoBERT-large (370M vs 135M) | 0.4322 → 0.4228 | -2.2% |
| Stacking (8M) vs v7 | 0.4059 → 0.4004 | -1.4% |

---

## 10. Giới hạn và hướng Day 5

**Ceiling encoder-only là ~0.40** trên dataset này (158K items, tiếng Việt ngắn).

**Tại sao bị giới hạn:**
- PhoBERT-large (370M) chỉ cải thiện 2.2% so với base-v2 (135M) — diminishing returns khi scale
- Stacking pool bão hòa: thêm model thứ 8 chỉ cho +1.4%
- Text summary 5 dòng thiếu thông tin giá (brand tier, model number, condition)
- mDeBERTa (184M) bị skip ở v8 — chưa khai thác disentangled attention

**So sánh với benchmark quốc tế:**
- Kaggle Mercari (English, cùng metric): 1st place RMSLE=0.3875 (Sparse MLP ensemble, 2018)
- Tiếng Việt ngắn hơn và ít structured hơn English → floor tự nhiên cao hơn ~0.03-0.05
- **RMSLE floor ước tính cho task này: ~0.33-0.37**

**Fallback Day 5:**
- **Option A (recommended):** QLoRA fine-tune Qwen2.5-7B-Instruct hoặc Gemma-3-4B-IT
  - Decoder LLM scale + instruction tuning → calibrate price range tốt hơn encoder
  - GPU: A100 40GB, 4-bit NF4, ~4-6h
- **Option B:** mDeBERTa retry (disentangled attention, 184M, chưa thử)
- **Option C:** Feature engineering (brand extraction, model number, condition keywords)

---

## 11. Pipeline inference (v8)

```python
item.summary + item.category
    → AutoTokenizer("vinai/phobert-large")
    → BERTMultiTaskRegressorV8.forward()   # 8 category-specific heads
    → EMA model weights
    → mean pooling → price_heads[cat_id] → pred_norm
    → expm1(pred_norm * y_std + y_mean)    # inverse transform
    → price_vnd

# Stacking (production):
preds = [model(item) for model in [phobert_large, xlmr, aiteamvn, ...]]  # 8 models
meta_features = log1p(preds)
final_price = expm1(mean([ridge(meta), enet(meta), lgb(meta)]))
```

---

## 12. Files

```
day4/
    day4_dl_models_v7.ipynb     # v7: RMSLE=0.4059 (46 cells)
    day4_dl_models_v8.ipynb     # v8: RMSLE=0.4004 (45 cells)
    day4_frontier_llm.ipynb     # LLM zero-shot (thất bại)
    v7_results.json             # v7 full results
    weights_v8/
        v8_results.json         # v8 full results
        stacking_config_v8.json # Ridge/EN/LGB coefficients
    weights_v7/                 # PhoBERT++, XLM-R++, AITeamVN++ weights
    tokenized_*.pkl             # Underthesea cache (trong repo)

pricer_vi/
    deep_neural_network.py      # DeepNeuralNetwork + MLP + predict_batch
    evaluator.py                # rmsle(), Tester, plot_predictions
    items.py                    # Item dataclass, from_hub()
```

**Lưu ý checkpoint v4 (cần khi reload):**
- `model_2b_mlp_aiteamvn.pth` → `state_dict` key, `MLP(input_size=1032)` (1024+8 cat)
- `model_0a_dnn_hv2048.pth` → `state_dict` key, `DeepNeuralNetwork(input_size=5008)` (5000+8 cat)
