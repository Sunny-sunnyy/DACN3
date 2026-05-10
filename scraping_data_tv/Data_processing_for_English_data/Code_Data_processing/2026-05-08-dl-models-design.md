# Design Doc: Deep Learning Models for Price Prediction

**Ngày tạo:** 2026-05-08  
**Cập nhật lần cuối:** 2026-05-10  
**Tác giả:** Sunny (hieu0606sunny)  
**Phạm vi:** Các kiến trúc DL cho bài toán dự đoán giá sản phẩm từ text description  
**Môi trường train:** RTX 3090 Ti 24GB VRAM (vast.ai)  
**Dataset:** `SeanSunny/items_full` — 800k train / 10k val / 10k test  

---

## 1. Bối cảnh & Vấn đề

### Baseline hiện tại (DNN với HashingVectorizer)

Model DNN hiện tại (`deep_neural_network.py`) dùng **HashingVectorizer** làm input:

```
item.summary → HashingVectorizer(5000, binary=True, stop_words="english") → sparse binary vector
             → Linear(5000→4096) + 8 ResidualBlocks(4096) + Linear(4096→1)
             → price
```

**Kết quả thực tế:** MAE **$46.02** — thắng Claude Opus 4.5 ($47.10).

**Lưu ý kỹ thuật:** HashingVectorizer ≠ CountVectorizer (BoW truyền thống):
- Dùng hashing trick để map từ → bucket index, không lưu vocabulary
- `binary=True` → chỉ biết từ xuất hiện hay không (như BoW)
- Không có OOV issue, stateless, memory-efficient
- Nhược điểm: hash collision (2 từ khác nhau → cùng bucket)

### Vấn đề cốt lõi

HashingVectorizer chỉ biết "từ này có xuất hiện không" — không có ngữ nghĩa:
- `"car"` ≠ `"automobile"` với hashing, nhưng thực tế giá như nhau
- `"cheap plastic"` ≠ `"economy grade"` với hashing, nhưng nghĩa giống nhau
- Không hiểu thứ tự từ, context, hoặc quan hệ giữa các khái niệm

### Câu hỏi nghiên cứu

> Biểu diễn văn bản tốt hơn có cải thiện độ chính xác không?

---

## 2. Câu chuyện học thuật (Academic Narrative)

Bốn mô hình tạo ra progression rõ ràng:

```
Tầng 1 — HashingVec → ResNet DNN ($46.02)
    Đặc trưng: keyword presence, stateless, no semantics
    Vấn đề: "car" ≠ "automobile", không hiểu ngữ nghĩa

Tầng 2 — SentenceTransformer (frozen) → DNN  [MODEL 1]
    Đặc trưng: dense semantic embedding 384-dim, pretrained
    Tiến bộ: "car" ≈ "automobile" — nhưng encoder không học từ dữ liệu giá

Tầng 3 — Fine-tuned DistilBERT / SentTrans E2E  [MODEL 2 & 3]
    Đặc trưng: encoder học representations tối ưu cho price prediction
    Tiến bộ: attention học cái gì quan trọng (brand, material, category)

Tầng 4 — Feature Fusion: HashingVec + SentTrans  [MODEL 4]
    Đặc trưng: kết hợp lexical signal + semantic signal
    Hypothesis: 2 nguồn thông tin bổ sung cho nhau
```

### Tại sao DNN (HashingVec) vẫn mạnh sau khi training ít epoch?

1. **Dữ liệu đã được LLM pre-process** — Groq batch rewrite thành format chuẩn `Title / Category / Brand / Description / Details`. Brand và Category đã extract rõ → hashing capture được signal này trực tiếp.
2. **Price prediction là keyword-driven**: brand tier (`"bose"`, `"anker"`), category, material (`"stainless steel"`, `"plastic"`) — HashingVec với 5000 features học statistical distribution này cực tốt trên 800k samples.
3. **289M params overparametrized**: với sparse binary input, model có thể học phân phối giá theo từng keyword bucket rất chi tiết.

---

## 3. Kết quả thực tế (Đã train)

| Model | File | Epochs | Val MAE (best) | Test MAE | Ghi chú |
|-------|------|--------|---------------|----------|---------|
| HashingVec DNN | `deep_neural_network.py` | 5 | $53.84 | **$46.02** | Baseline |
| SentTrans frozen (1024) | `sentence_transformer_model.py` | 15 | $56.24 | $47.56 | Tệ hơn DNN |
| SentTrans frozen (4096) | `sentence_transformer_model.py` | 15 | $49.99 | **$43.78** | Tốt hơn DNN |
| DistilBERT V1 (CLS, batch=32) | `distilbert_model.py` | 5 | $47.42 | **$44.19** | Chưa hội tụ |

**Nhận xét:**
- SentTrans 1024 tệ hơn DNN vì 13M params không đủ capacity so với 289M của DNN
- SentTrans 4096 (203M params) tốt hơn DNN — improvement một phần đến từ model capacity lớn hơn, không chỉ từ semantic embedding
- DistilBERT V1 val MAE vẫn giảm đều ($54.60 → $47.42) tại epoch 5, chưa plateau → cần train thêm

---

## 4. Model 1: SentenceTransformer + Regression DNN (Frozen)

### Kiến trúc

```
item.summary
    → all-MiniLM-L6-v2 (frozen, 22M params) [pre-computed một lần]
    → 384-dim dense embedding
    → Linear(384 → hidden_size) + LayerNorm + ReLU + Dropout(0.2)
    → 6 × ResidualBlock(hidden_size)
    → Linear(hidden_size → 1)
    → price
```

**Hai variants đã train:**
- `hidden_size=1024` → 13M trainable params → Test MAE **$47.56**
- `hidden_size=4096` → 203M trainable params → Test MAE **$43.78** ✓

**Key technique:** Pre-compute toàn bộ 800k embeddings một lần → encoder không chạy lại trong training loop → fast.

### Hyperparameters chốt

```python
hidden_size  = 4096       # Variant tốt hơn
num_blocks   = 6
dropout_prob = 0.2
optimizer    = AdamW(lr=1e-3, weight_decay=0.01)
scheduler    = CosineAnnealingLR(T_max=15, eta_min=0)
loss         = L1Loss()
batch_size   = 256
epochs       = 15         # max, early stopping patience=3
```

---

## 5. Model 2: Fine-tuned DistilBERT (End-to-End)

### Tại sao DistilBERT

- 66M params (BERT-base: 110M) — nhanh 2x, giữ 97% performance
- Fine-tuning encoder dạy attention heads học: brand names, materials, category context
- DistilBERT production-ready, battle-tested

### Kiến trúc

```
item.summary
    → DistilBERT tokenizer (max_length=128, truncation=True)
    → DistilBERT encoder (6 layers, 768-dim, 66M params) [fine-tuned]
    → pooling → 768-dim
    → LayerNorm(768) → Linear(768→256) → GELU → Dropout(0.1) → Linear(256→1)
    → price
```

**Token length analysis:** 99.8% samples ≤ 128 tokens → max_length=128 optimal.

### Ba variants

**V1** (`distilbert_model.py`): CLS pooling, batch=32, 5 epochs → Test MAE **$44.19** (chưa hội tụ)

**V2** (`distilbert_model_v2.py`): CLS pooling, batch=64, 15 epochs, patience=3
```python
# Subclass của V1, thay đổi defaults
def setup(self, batch_size=64)
def train(self, epochs=15, patience=3, warmup_steps=500)
```

**V3** (`distilbert_model_v3.py`): Mean pooling, batch=64, 15 epochs, patience=3
```python
# Mean pooling thay [CLS]
mask = attention_mask.unsqueeze(-1).float()
mean_emb = (outputs.last_hidden_state * mask).sum(1) / mask.sum(1)
```

**Tại sao thử mean pooling:**
- CLS token được pretrain cho NSP (classification) — không optimal cho regression
- Mean pooling = average tất cả token embeddings theo attention mask
- SentTrans (all-MiniLM-L6-v2) dùng mean pooling và cho kết quả tốt
- Nhiều paper BERT regression: mean pooling ≥ CLS

### Hyperparameters chung (V2 và V3)

```python
max_length   = 128
optimizer    = AdamW([
    {"params": encoder, "lr": 2e-5},   # Discriminative LR
    {"params": head,    "lr": 1e-4},
], weight_decay=0.01)
scheduler    = linear_schedule_with_warmup(warmup_steps=500)
loss         = L1Loss()
batch_size   = 64
epochs       = 15        # max, early stopping patience=3
precision    = fp16 (torch.cuda.amp)
```

---

## 6. Model 3: SentenceTransformer End-to-End Fine-tuning

### Lý do

Model 1 frozen encoder bị giới hạn: all-MiniLM-L6-v2 được train cho semantic similarity, không phải price prediction. Fine-tuning dạy encoder chú ý đến brand tier, material quality, category context.

**Contrast:**
- Model 1: pre-compute embeddings một lần → encoder không học → fast nhưng suboptimal
- Model 3: encoder chạy trong mỗi batch, weights được update → học price-specific representation

### Kiến trúc

```
item.summary
    → all-MiniLM-L6-v2 tokenizer (max_length=128)
    → all-MiniLM-L6-v2 encoder (22M params) [FINE-TUNED]
    → mean pooling → 384-dim
    → LayerNorm(384) → Linear(384→256) → GELU → Dropout(0.1) → Linear(256→1)
    → price
```

**Implementation:** Dùng `transformers.AutoModel` thay vì `sentence_transformers.SentenceTransformer` để kiểm soát fine-tuning trực tiếp.

### Hyperparameters

```python
model_name   = "sentence-transformers/all-MiniLM-L6-v2"
max_length   = 128
optimizer    = AdamW([
    {"params": encoder, "lr": 5e-5},   # Nhỏ hơn DistilBERT vì model nhỏ hơn
    {"params": head,    "lr": 1e-3},
], weight_decay=0.01)
scheduler    = linear_schedule_with_warmup(warmup_steps=500)
loss         = L1Loss()
batch_size   = 128       # Lớn hơn DistilBERT vì model nhỏ hơn (22M vs 66M)
epochs       = 15        # max, early stopping patience=3
precision    = fp16
```

**Params:** 22M encoder + ~197K head = ~22.2M total

---

## 7. Model 4: Feature Fusion (HashingVec + SentTrans)

### Hypothesis

HashingVec và SentTrans capture hai loại thông tin khác nhau, bổ sung cho nhau:
- **HashingVec**: lexical signal — brand names (`"samsung"`, `"bose"`), explicit keywords (`"wireless"`, `"4k"`, `"stainless steel"`)
- **SentTrans**: semantic signal — quality context (`"premium"`, `"economy grade"`), conceptual similarity

Kết hợp cả hai trong một model nên tốt hơn từng model riêng lẻ.

### Kiến trúc

```
HashingVec(5000) → LayerNorm(5000) → Linear(5000→512) → ReLU ─┐
                                                                  ├→ concat(1024) → 4×ResidualBlock(1024) → Linear(1) → price
SentTrans(384) frozen → LayerNorm(384) → Linear(384→512) → ReLU ─┘
```

**Tại sao project riêng (không concat thẳng 5384):**
- 5000-dim HashingVec sẽ dominate 384-dim SentTrans nếu concat trực tiếp
- LayerNorm + projection riêng cho từng modality giải quyết scale mismatch
- Mỗi tower học representation tối ưu cho modality của nó trước khi fusion

### Hyperparameters

```python
hash_dim     = 5000
sem_dim      = 384
proj_dim     = 512        # Mỗi modality project về 512
fused_dim    = 1024       # concat(512, 512)
num_blocks   = 4          # ResidualBlocks sau fusion
dropout_prob = 0.2
optimizer    = AdamW(lr=1e-3, weight_decay=0.01)
scheduler    = CosineAnnealingLR(T_max=15, eta_min=0)
loss         = L1Loss()
batch_size   = 256        # Lớn vì không có transformer overhead
epochs       = 15         # max, early stopping patience=3
```

**Setup:** Pre-compute cả hai feature types một lần (SentTrans frozen) → training loop chỉ chạy FusionDNN.

---

## 8. Token Length Analysis (2026-05-10)

Chạy trên 10k random samples từ `SeanSunny/items_full` với DistilBERT tokenizer:

```
Min:    40  |  Max:    163
Mean:   81.9 |  Median: 81
P90:    99   |  P95:    105  |  P99:    118

<= 64:  7.6%
<= 128: 99.8%
<= 256: 100.0%
> 128:  25 samples (0.2%)
```

**Kết luận:** `max_length=128` cover 99.8% samples, power of 2 cho memory alignment, áp dụng cho cả DistilBERT và SentTrans E2E.

---

## 9. File Structure

```
Code_Data_processing/
│
├── pricer/
│   ├── deep_neural_network.py        # Baseline: HashingVec + ResNet DNN (289M params)
│   ├── sentence_transformer_model.py # Model 1: SentTrans frozen + DNN head
│   ├── distilbert_model.py           # Model 2 V1: DistilBERT CLS, batch=32, 5 epochs
│   ├── distilbert_model_v2.py        # Model 2 V2: CLS, batch=64, 15 epochs
│   ├── distilbert_model_v3.py        # Model 2 V3: Mean pooling, batch=64, 15 epochs
│   ├── senttrans_e2e_model.py        # Model 3: SentTrans fine-tuned E2E
│   ├── fusion_model.py               # Model 4: HashingVec + SentTrans fusion
│   └── evaluator.py                  # evaluate() + plot_training_history()
│
├── redemption_train.ipynb            # Train Baseline DNN (5 epochs) → MAE $46.02
├── model1_senttrans_train_1024.ipynb # Train Model 1 (hidden=1024) → MAE $47.56
├── model1_senttrans_train_4096.ipynb # Train Model 1 (hidden=4096) → MAE $43.78
├── model2_distilbert_train.ipynb     # Train Model 2 V1 (5 epochs) → MAE $44.19
├── model2_distilbert_train_v2.ipynb  # Train Model 2 V2 (batch=64, 15 epochs) [TODO]
├── model2_distilbert_train_v3.ipynb  # Train Model 2 V3 (mean pooling) [TODO]
├── model3_senttrans_e2e_train.ipynb  # Train Model 3 (SentTrans E2E) [TODO]
└── model4_fusion_train.ipynb         # Train Model 4 (Feature Fusion) [TODO]
```

**Weights (lưu vào `Code_Data_processing/`):**
- `sentence_transformer_model.pth` — Model 1 (4096 variant)
- `distilbert_model.pth` — Model 2 V1
- `distilbert_model_v2.pth` — Model 2 V2 (sau khi train)
- `distilbert_model_v3.pth` — Model 2 V3 (sau khi train)
- `senttrans_e2e_model.pth` — Model 3 (sau khi train)
- `fusion_model.pth` — Model 4 (sau khi train)

---

## 10. Interface chuẩn

Tất cả Runner classes implement cùng interface:

```python
class XxxRunner:
    def setup(self, batch_size=...): ...   # Load model, prepare data
    def train(self, epochs, patience) -> dict: ...  # Return history dict
    def save(self, path): ...              # Save weights + y_mean + y_std
    def load(self, path): ...              # Load weights + y_mean + y_std
    def inference(self, item) -> float: ... # item.summary → price float
```

`evaluate()` từ `pricer/evaluator.py` gọi `inference(item)` → tương thích với mọi runner.

---

## 11. Implementation Status

| Model | `.py` | `.ipynb` | Train | Test MAE | Ghi chú |
|-------|-------|----------|-------|----------|---------|
| Baseline DNN (HashingVec) | `deep_neural_network.py` ✓ | `redemption_train.ipynb` ✓ | DONE | **$46.02** | 5 epochs |
| Model 1 SentTrans frozen (1024) | `sentence_transformer_model.py` ✓ | `model1_senttrans_train_1024.ipynb` ✓ | DONE | $47.56 | 15 epochs |
| Model 1 SentTrans frozen (4096) | `sentence_transformer_model.py` ✓ | `model1_senttrans_train_4096.ipynb` ✓ | DONE | **$43.78** | 15 epochs |
| Model 2 V1 DistilBERT CLS | `distilbert_model.py` ✓ | `model2_distilbert_train.ipynb` ✓ | DONE | $44.19 | 5 epochs, chưa hội tụ |
| Model 2 V2 DistilBERT CLS long | `distilbert_model_v2.py` ✓ | `model2_distilbert_train_v2.ipynb` ✓ | TODO | — | batch=64, 15 epochs |
| Model 2 V3 DistilBERT mean pool | `distilbert_model_v3.py` ✓ | `model2_distilbert_train_v3.ipynb` ✓ | TODO | — | mean pooling |
| Model 3 SentTrans E2E | `senttrans_e2e_model.py` ✓ | `model3_senttrans_e2e_train.ipynb` ✓ | TODO | — | encoder fine-tuned |
| Model 4 Feature Fusion | `fusion_model.py` ✓ | `model4_fusion_train.ipynb` ✓ | TODO | — | HashingVec + SentTrans |

---

## 12. Thứ tự train (Priority hôm nay)

Ưu tiên theo ROI và thời gian, với 3090 Ti 24GB:

| Priority | Notebook | Ước tính | Lý do |
|----------|----------|---------|-------|
| 1 | `model2_distilbert_train_v2.ipynb` | ~2h | Val MAE v1 đang giảm mạnh, highest ROI |
| 2 | `model2_distilbert_train_v3.ipynb` | ~2h | Chạy song song v2 (8GB+8GB < 24GB) |
| 3 | `model3_senttrans_e2e_train.ipynb` | ~1.5h | Model nhỏ (22M), batch=128 |
| 4 | `model4_fusion_train.ipynb` | ~1.5h | Setup lâu (pre-compute 2 features) |

**Lưu ý v3:** Output sẽ in "DistilBERT Regressor: 66M" (từ V2 super().setup()) rồi in "DistilBERT V3 (mean pooling): 66M" — expected behavior, model đã được swap đúng.

---

## 13. Leaderboard hiện tại

| Hạng | Model | MAE | Loại |
|------|-------|-----|------|
| ? | Model 2 V2/V3 | TBD | DistilBERT 15 epochs |
| ? | Model 3 | TBD | SentTrans E2E |
| ? | Model 4 | TBD | Feature Fusion |
| 1 | SentTrans frozen (4096) | $43.78 | Model 1 |
| 2 | DistilBERT V1 (5 epoch) | $44.19 | Model 2 V1 |
| 3 | Baseline HashingVec DNN | $46.02 | DNN |
| 4 | Claude Opus 4.5 | $47.10 | Frontier LLM |
| 5 | SentTrans frozen (1024) | $47.56 | Model 1 |

---

*Design doc cập nhật lần cuối: 2026-05-10*
