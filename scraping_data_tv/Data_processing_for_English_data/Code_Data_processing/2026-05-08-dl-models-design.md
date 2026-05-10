# Design Doc: 2 New Deep Learning Models for Price Prediction

**Ngày:** 2026-05-08  
**Tác giả:** Sunny (hieu0606sunny)  
**Phạm vi:** Bổ sung 2 kiến trúc DL mới cho bài toán dự đoán giá sản phẩm từ text description  
**Môi trường train:** RTX 3090 Ti 24GB VRAM (vast.ai)  
**Dataset:** `SeanSunny/items_full` — 800k train / 10k val / 10k test  

---

## 1. Bối cảnh & Vấn đề

### Baseline hiện tại

Model DNN hiện tại (`deep_neural_network.py`) dùng **Bag of Words** làm input:

```
item.summary → HashingVectorizer(5000, binary) → sparse vector
             → Linear(5000→4096) + 8 ResidualBlocks + Linear(4096→1)
             → price
```

**Kết quả:** MAE **$46.49** — thắng Claude Opus 4.5 ($47.10).

### Vấn đề cốt lõi

HashingVectorizer chỉ biết "từ này có xuất hiện không" — không có ngữ nghĩa:
- "car" ≠ "automobile" với BoW, nhưng thực tế giá như nhau
- "cheap plastic" ≠ "economy grade" với BoW, nhưng nghĩa giống nhau  
- Không hiểu thứ tự từ, context, hoặc quan hệ giữa các khái niệm

### Câu hỏi nghiên cứu

> Biểu diễn văn bản tốt hơn có cải thiện độ chính xác không?

---

## 2. Câu chuyện học thuật (Academic Narrative)

Ba mô hình tạo ra progression rõ ràng:

```
Tầng 1 — BoW → ResNet ($46.49)
    Đặc trưng: tần suất từ xuất hiện, binary, stateless
    Vấn đề: mù về ngữ nghĩa

Tầng 2 — SentenceTransformer (frozen) → DNN  [MODEL 1]
    Đặc trưng: embedding ngữ nghĩa dày đặc 384-dim, pretrained
    Tiến bộ: biết "car" ≈ "automobile", nhưng encoder không học từ dữ liệu giá

Tầng 3 — Fine-tuned DistilBERT end-to-end  [MODEL 2]
    Đặc trưng: encoder học lại representations tối ưu cho price prediction
    Tiến bộ: attention học cái gì quan trọng với giá (brand, material, category)
```

---

## 3. Model 1: SentenceTransformer + Regression DNN

### 3.1 Lý do chọn kiến trúc này

`sentence-transformers/all-MiniLM-L6-v2` đã là dependency trong project (dùng bởi `frontier_agent.py` cho ChromaDB). Model này tạo ra **dense semantic embeddings 384-dim**, trong đó:
- Vector của "acoustic guitar" gần với "classical guitar"
- Vector của "premium stainless steel" xa vector "cheap plastic"

Thay BoW (5000-dim sparse binary) bằng SentTrans (384-dim dense semantic) là bước nâng cấp rõ ràng về chất lượng input mà không cần fine-tune encoder.

**Key optimization:** Pre-compute toàn bộ 800k embeddings một lần trước training → encoder không chạy lại trong mỗi epoch → training head nhanh như DNN hiện tại.

### 3.2 Kiến trúc

```
item.summary
    → all-MiniLM-L6-v2 (frozen, 22M params)
    → 384-dim dense embedding  [pre-computed, lưu vào tensor]
    → Linear(384 → 1024) + LayerNorm + ReLU + Dropout(0.2)
    → 6 × ResidualBlock(1024 → 1024)
    → Linear(1024 → 1)
    → price
```

- **Encoder:** frozen hoàn toàn — chỉ dùng để encode, không update weights
- **Regression head:** nhỏ hơn DNN hiện tại (1024 vs 4096) vì input semantic hơn
- **Target transform:** giống DNN hiện tại — log(price+1) normalized

### 3.3 Thông số ước tính

| Thành phần | Parameters |
|------------|-----------|
| Encoder (frozen) | 22M |
| Input proj (384→1024) | 393K |
| 6 ResidualBlocks (1024→1024) | ~12.6M |
| Output (1024→1) | 1K |
| **Trainable total** | **~13M** |

Memory (3090 Ti 24GB): thoải mái — có thể batch_size=256+

### 3.4 Training config

```python
optimizer = AdamW(head.parameters(), lr=1e-3, weight_decay=0.01)
scheduler = CosineAnnealingLR(T_max=10, eta_min=0)
loss      = nn.L1Loss()  # giống DNN hiện tại
epochs    = 10           # nhiều hơn vì model nhỏ, converge nhanh
batch_size= 256          # lớn hơn vì model nhỏ
grad_clip = 1.0
```

### 3.5 Ưu và Nhược điểm

**Ưu điểm:**
- Semantic understanding rõ ràng vs BoW
- Zero dependency mới (SentTrans đã có)
- Training nhanh (pre-computed embeddings)
- Inference nhanh (~5ms/item)
- Model nhỏ, dễ deploy

**Nhược điểm:**
- Encoder **frozen** — không học từ dữ liệu giá của chúng ta
- Bị giới hạn bởi max_seq_len = 256 tokens
- SentTrans được train cho sentence similarity, không phải price prediction → có thể không tối ưu

---

## 4. Model 2: Fine-tuned DistilBERT (End-to-End)

### 4.1 Lý do chọn kiến trúc này

Model 1 dùng **frozen** encoder. Model 2 **fine-tune toàn bộ** DistilBERT để học representations tối ưu cho price prediction.

Sau fine-tuning, attention heads của DistilBERT sẽ học:
- Chú ý vào brand names (Fender, Samsung → tier giá khác nhau)
- Nhận biết materials ("stainless steel", "ceramic" → cao hơn "plastic")
- Hiểu category context ("wireless noise-cancelling" trong context headphone → $150+)

**Tại sao DistilBERT thay vì BERT-base?**
- 66M params (BERT-base: 110M) — nhanh 2x, nhỏ hơn
- Giữ 97% performance của BERT-base
- Fit thoải mái trên 3090 Ti 24GB với batch_size=32-64

**Tại sao không dùng BERT-large hay RoBERTa-large?**
- 800k samples là dataset lớn nhưng cho NLP task, fine-tuning model quá lớn có thể overfitting → DistilBERT là sweet spot cho dataset này

### 4.2 Kiến trúc

```
item.summary
    → DistilBERT tokenizer (max_length=256, truncation=True)
    → DistilBERT encoder (6 layers, 768-dim, 66M params) [fine-tuned]
    → [CLS] token embedding (768-dim)
    → LayerNorm(768)
    → Linear(768 → 256) + GELU + Dropout(0.1)
    → Linear(256 → 1)
    → price
```

- **[CLS] pooling:** token đặc biệt ở đầu sequence, sau fine-tuning chứa thông tin tổng hợp của cả câu
- **GELU** thay ReLU vì BERT ecosystem dùng GELU — giữ consistency
- **Target transform:** log(price+1) normalized — giống 2 model kia

### 4.3 Thông số

| Thành phần | Parameters |
|------------|-----------|
| DistilBERT encoder | 66M |
| Regression head | ~197K |
| **Total** | **~66.2M** |

Memory (3090 Ti 24GB):
- Model weights: ~250MB (fp16) → ~500MB (fp32)
- Batch 32 × seq 256: ~2GB activations
- Tổng: ~8-10GB → thoải mái

### 4.4 Training config

```python
# Discriminative fine-tuning: encoder LR thấp, head LR cao
optimizer = AdamW([
    {"params": encoder.parameters(), "lr": 2e-5},
    {"params": head.parameters(),    "lr": 1e-4},
], weight_decay=0.01)
scheduler  = get_linear_schedule_with_warmup(warmup_steps=1000)
loss       = nn.L1Loss()
epochs     = 5           # Fine-tuning LLM không cần nhiều epoch
batch_size = 32          # Nhỏ hơn vì model lớn hơn
grad_clip  = 1.0
precision  = fp16 (torch.cuda.amp)  # Mixed precision → 2x nhanh, ít VRAM
```

**Discriminative fine-tuning:** LR khác nhau cho encoder và head. Tránh phá vỡ pretrained knowledge trong encoder với LR quá cao.

**Warmup:** 1000 steps đầu tăng LR từ 0 → target → tránh unstable training ở đầu.

### 4.5 Ưu và Nhược điểm

**Ưu điểm:**
- **Task-specific learned representations** — tốt nhất về chất lượng
- Hiểu context, thứ tự từ, quan hệ giữa các khái niệm
- Có thể đạt MAE tốt nhất trong cả 4 models
- DistilBERT là production-ready, battle-tested

**Nhược điểm:**
- Training chậm hơn 3–5x so với Model 1 (nhưng khả thi trên 3090 Ti)
- Inference chậm hơn (~30-50ms/item vs ~5ms) — cần đánh giá nếu tích hợp Ensemble
- Cần thêm `transformers` library (HuggingFace)
- Phức tạp hơn: tokenizer, attention masks, warmup schedule

---

## 5. Kỳ vọng kết quả

| Hạng | Model | MAE (ước tính) | Lý do |
|------|-------|----------------|-------|
| ? | Fine-tuned DistilBERT | ~$38–44 | Task-specific end-to-end |
| ? | SentenceTransformer DNN | ~$43–46 | Better repr, nhưng frozen |
| 2 | Current DNN (BoW) | $46.49 | Baseline |
| 3 | Claude Opus 4.5 | $47.10 | Reference |

---

## 6. File Structure Output

```
Code_Data_processing/
├── pricer/
│   ├── sentence_transformer_model.py    # SentTransRunner class (Model 1)
│   └── distilbert_model.py              # DistilBERTRunner class (Model 2)
│
├── model1_senttrans_train.ipynb         # Train Model 1, visualize, evaluate
├── model2_distilbert_train.ipynb        # Train Model 2, visualize, evaluate
│
└── [weights được lưu vào segment4/ để dùng trong EnsembleAgent]
    # segment4/sentence_transformer_model.pth
    # segment4/distilbert_model.pth
```

### Interface chuẩn (giống `DeepNeuralNetworkRunner`)

Cả 2 Runner classes phải implement cùng interface để dễ plug vào EnsembleAgent:

```python
class SentTransRunner:
    def __init__(self, train, val): ...
    def setup(self): ...          # Load model, vectorize/encode data
    def train(self, epochs) -> dict: ...  # Return history dict
    def save(self, path): ...
    def load(self, path): ...
    def inference(self, item) -> float: ...  # item.summary → price float
```

```python
class DistilBERTRunner:
    # Cùng interface với SentTransRunner
```

---

## 7. Implementation Plan

### Bước 1: Model 1 — SentenceTransformer DNN
1. Tạo `pricer/sentence_transformer_model.py` — `SentTransRunner` class  
   → verify: `runner.inference(item)` trả về float hợp lý
2. Tạo `model1_senttrans_train.ipynb` — train 10 epochs, plot history, evaluate  
   → verify: MAE < $46.49 (thắng BoW DNN)
3. Lưu weights → `segment4/sentence_transformer_model.pth`  
   → verify: load lại và inference đúng

### Bước 2: Model 2 — Fine-tuned DistilBERT
1. Tạo `pricer/distilbert_model.py` — `DistilBERTRunner` class với mixed precision  
   → verify: training không OOM trên 3090 Ti với batch_size=32
2. Tạo `model2_distilbert_train.ipynb` — train 5 epochs, plot history, evaluate  
   → verify: MAE < Model 1
3. Lưu weights → `segment4/distilbert_model.pth`  
   → verify: load lại và inference đúng

### Bước 3: So sánh & Báo cáo
- Bảng kết quả 4 models trong cùng 1 cell của notebook
- Dùng `evaluate()` và `plot_training_history()` từ `pricer/evaluator.py` (không viết lại)

---

## 8. Constraints & Decisions (DA CHOT — 2026-05-10)

| Quyết định | Lý do |
|------------|-------|
| Dùng `all-MiniLM-L6-v2` cho Model 1 | Đã có trong project, không thêm dependency |
| Dùng DistilBERT (không phải BERT-base) | 97% performance, 2x nhanh, phù hợp 800k dataset |
| Pre-compute embeddings cho Model 1 | Tách encoding khỏi training loop → nhanh hơn nhiều |
| Mixed precision (fp16) cho Model 2 | 2x tốc độ, giảm VRAM, không ảnh hưởng kết quả |
| Cùng target transform (log normalize) | Consistency với DNN hiện tại, dễ so sánh |
| Cùng L1Loss | Giảm sensitivity với outliers (giá rất cao/thấp) |
| **max_length=128** cho DistilBERT | **Verified:** 99.8% samples <= 128 tokens, power of 2 memory-aligned |
| **hidden_size=1024** cho Model 1 | Input 384-dim dense, 4096 quá lớn gây overfitting. 1024 đủ capacity |
| **6 ResidualBlocks** cho Model 1 | 384→1024 + 6 blocks = 8 layers, tương đương Vanilla NN depth |
| Early stopping cho cả 2 models | Tránh overfitting, tự dừng khi val MAE không cải thiện |
| Lưu .pth vào segment4/ | Dùng ngay trong EnsembleAgent mà không cần copy |

---

## 9. Token Length Analysis (2026-05-10)

Chạy `check_token_length.py` trên 10k random samples từ `SeanSunny/items_full` với DistilBERT tokenizer:

```
--- Token Length Distribution (DistilBERT tokenizer) ---
Min:    40
Max:    163
Mean:   81.9
Median: 81
P90:    99
P95:    105
P99:    118

<= 64:  7.6%
<= 128: 99.8%
<= 256: 100.0%
> 128:  25 samples (0.2%)
```

**Kết luận:** `max_length=128` là lựa chọn tối ưu — cover 99.8% samples, power of 2 cho memory alignment, chỉ 25/10000 mẫu bị truncate.

---

## 10. Thảo luận: Skip Connection cho Model 1 & 2

### Model 1 (SentTrans DNN) — Đã có Skip Connection

`SentTransDNN` dùng 6 `ResidualBlock`, mỗi block có `out += residual` (skip connection). Cùng pattern với `deep_neural_network.py`. **Không cần bổ sung.**

### Model 2 (DistilBERT) — Không cần thêm Skip Connection vào head

**Lý do 1:** DistilBERT encoder đã có sẵn skip connections. Mỗi transformer layer có 2 residual connections (sau attention và sau FFN). 6 layers × 2 = **12 skip connections** trong encoder.

**Lý do 2:** Regression head chỉ có 2 linear layers (768 → 256 → 1). Skip connection yêu cầu cùng hidden_size (768 ≠ 256 ≠ 1), và mạng 2 layers không bị vanishing gradient.

**Lý do 3:** Các paper fine-tuning BERT cho regression (STS-B, sentiment) đều dùng head 1-2 layers. Head lớn thường không cải thiện kết quả vì encoder đã học representation tốt.

**Kết luận:** Giữ nguyên thiết kế hiện tại. Nếu kết quả chưa đạt, ưu tiên điều chỉnh LR và epochs trước khi thêm complexity vào head.

---

## 11. Hyperparameters chốt cuối cùng

### Model 1: SentenceTransformer + DNN

```python
input_size   = 384        # all-MiniLM-L6-v2 output dim
hidden_size  = 1024
num_blocks   = 6          # ResidualBlocks
dropout_prob = 0.2
optimizer    = AdamW(lr=1e-3, weight_decay=0.01)
scheduler    = CosineAnnealingLR(T_max=15, eta_min=0)
loss         = L1Loss()
batch_size   = 256
epochs       = 15         # max, early stopping patience=3
grad_clip    = 1.0
```

Trainable params: ~13M | Encoder (frozen): 22M

### Model 2: Fine-tuned DistilBERT

```python
max_length     = 128
encoder        = distilbert-base-uncased (66M params, fine-tuned)
head           = LayerNorm(768) → Linear(768,256) → GELU → Dropout(0.1) → Linear(256,1)
optimizer      = AdamW([
    {"params": encoder, "lr": 2e-5},   # Discriminative LR
    {"params": head,    "lr": 1e-4},
], weight_decay=0.01)
scheduler      = linear_schedule_with_warmup(warmup_steps=1000)
loss           = L1Loss()
batch_size     = 32
epochs         = 5        # max, early stopping patience=2
grad_clip      = 1.0
precision      = fp16 (torch.cuda.amp)
```

Total params: ~66.2M (encoder: 66M, head: ~197K)

---

## 12. Implementation Status (2026-05-10)

| File | Trạng thái | Mô tả |
|------|-----------|-------|
| `pricer/sentence_transformer_model.py` | DONE | SentTransDNN + SentTransRunner class |
| `pricer/distilbert_model.py` | DONE | DistilBERTRegressor + DistilBERTRunner class |
| `model1_senttrans_train.ipynb` | DONE | Notebook: load → setup → train → plot_training_history → evaluate(200) → save |
| `model2_distilbert_train.ipynb` | DONE | Notebook: load → setup → train → plot_training_history → evaluate(200) → save |
| Train on GPU (vast.ai 3090 Ti) | CHUA LAM | Thuê máy khi code sẵn sàng |
| Report kỹ thuật (mức A) | CHUA LAM | Viết sau khi có kết quả train |

### Cả 2 model đều tuân thủ:

- Cùng interface với `DeepNeuralNetworkRunner` (setup / train / save / load / inference)
- Dùng `evaluate()` từ `pricer/evaluator.py` cho 200 test samples
- Dùng `plot_training_history()` để vẽ biểu đồ Train Loss / Val Loss / Val MAE / LR
- Log-normalize target: `log(price+1)` → Z-score normalize
- Early stopping trên validation MAE (restore best weights)
- Gradient clipping max_norm=1.0

---

*Design doc cập nhật lần cuối: 2026-05-10*