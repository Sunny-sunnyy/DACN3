# Báo cáo: Fine-Tune Llama 3.2 3B với QLoRA — "The Price Is Right"

> **Mục đích:** Tài liệu chi tiết về quá trình fine-tune mô hình open-source Llama 3.2 3B bằng kỹ thuật QLoRA để dự đoán giá sản phẩm.
> **Phạm vi:** Week 7 (Day 1–5) — từ lý thuyết QLoRA đến evaluation kết quả cuối
> **Ngày cập nhật:** 2026-05-10
> **Thư mục code:** `scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune/`
> **Model đã train:** `SeanSunny/price-2026-final` trên HuggingFace

---

## Hành trình tổng quan

```
Base Llama 3.2 3B (MAE $110.72 — tệ hơn cả đoán mò)
    │
    ▼ Day 1 — Lý thuyết QLoRA + khám phá kiến trúc Llama
Hiểu được: tại sao 4-bit, LoRA là gì, tại sao không full fine-tune
    │
    ▼ Day 2 — Chuẩn bị dữ liệu (token analysis + prompt format)
Dataset: 820k items → prompt/completion pairs → push lên HuggingFace
    │
    ▼ Day 3-4 — Training (SFTTrainer + W&B monitoring)
GPU: RTX 3090 Ti | Epochs: 3 | r=64 | 800k samples
    │
    ▼ Day 5 — Evaluation
Fine-tuned Llama 3.2 3B: MAE $39.85 | MSE 4,643 | R² 78.9%
```

**Bảng so sánh trước/sau:**

| Mô hình | MAE | Ghi chú |
|---------|-----|---------|
| Constant Pricer (baseline) | $106.18 | Luôn đoán giá trung bình |
| Base Llama 3.2 3B (zero-shot) | $110.72 | Tệ hơn cả đoán mò |
| HashingVec DNN (289M params) | $46.02 | Baseline tốt nhất trước Week 7 |
| Claude Opus 4.5 (zero-shot) | $47.10 | Frontier model |
| **Fine-tuned Llama 3.2 3B (QLoRA)** | **$39.85** | **Top 1 leaderboard** |

---

## Phần 1: Kiến trúc Llama 3.2 3B

### Tổng quan

Llama 3.2 3B là mô hình ngôn ngữ của Meta với 3 tỷ tham số, được tối ưu cho thiết bị biên (Edge devices). Điểm đặc biệt: dù nhỏ, nó thừa hưởng toàn bộ quy trình training từ Llama 405B thông qua Knowledge Distillation — nên thông minh hơn kích thước cho thấy.

### Cấu trúc các lớp

Khi load model và in ra, ta thấy 3 thành phần chính:

```
LlamaForCausalLM
├── embed_tokens        # Embedding Layer
├── layers (x28)        # 28 Decoder Layers
│   ├── self_attn       # Self-Attention
│   │   ├── q_proj  [3072 × 3072]
│   │   ├── k_proj  [1024 × 3072]
│   │   ├── v_proj  [1024 × 3072]
│   │   └── o_proj  [3072 × 3072]
│   ├── mlp             # Multi-Layer Perceptron
│   │   ├── gate_proj [8192 × 3072]
│   │   ├── up_proj   [8192 × 3072]
│   │   └── down_proj [3072 × 8192]
│   ├── input_layernorm      # RMSNorm
│   └── post_attention_layernorm  # RMSNorm
├── norm                # Final RMSNorm
└── lm_head             # Output Head [128256 × 3072]
```

**Giải thích từng phần:**

**Embedding Layer (`embed_tokens`)**
- Input: vector one-hot kích thước 128,256 (tương ứng vocabulary size)
- Output: vector dense 3,072 chiều (hidden size)
- Vai trò: chuyển token ID thành vector ngữ nghĩa để model xử lý

**28 Decoder Layers**

*Self-Attention:* Đây là cơ chế cho phép model "nhìn" toàn bộ câu để hiểu ngữ cảnh. Với mỗi token, model tính:
- Query (q_proj): "Tôi đang tìm gì?"
- Key (k_proj): "Mỗi token khác có thể cung cấp gì?"
- Value (v_proj): "Nội dung thực sự của token đó là gì?"
- Output (o_proj): Kết hợp thông tin → đầu ra attention

Lưu ý kích thước: k_proj và v_proj có chiều đầu ra 1,024 (thay vì 3,072) — đây là kỹ thuật Grouped Query Attention (GQA) giúp giảm bộ nhớ khi inference.

*MLP (Multi-Layer Perceptron):* "Phình" dữ liệu từ 3,072 → 8,192 để xử lý phi tuyến, rồi nén lại về 3,072. Gate projection kiểm soát luồng thông tin (SwiGLU activation). Đây là nơi model "suy nghĩ" và lưu trữ kiến thức thực tế.

*RMSNorm:* Chuẩn hóa dữ liệu trước mỗi sub-layer để ổn định gradient. Đơn giản và hiệu quả hơn LayerNorm vì bỏ qua phép tính mean.

**Output Head (`lm_head`)**
- Input: 3,072 chiều
- Output: 128,256 chiều (logits cho từng token trong vocabulary)
- Mỗi số là xác suất của token đó xuất hiện tiếp theo — model chọn token có xác suất cao nhất

### Tại sao cần Quantization?

```python
# Load model ở chế độ mặc định (32-bit)
base_model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-3B")
print(f"Memory footprint: {base_model.get_memory_footprint() / 1e9:.1f} GB")
# Output: ~12.9 GB
```

3 tỷ tham số × 4 bytes (float32) = **12.9 GB** — gần như chiếm trọn GPU T4 (16GB), không còn chỗ cho training. Đây là lý do cần QLoRA.

---

## Phần 2: Lý thuyết QLoRA

QLoRA = **Q**uantization + **Lo**w-**R**ank **A**daptation. Hai kỹ thuật này giải quyết hai vấn đề độc lập: thiếu bộ nhớ (Q) và chi phí tính toán quá lớn (LoRA).

### 2.1 LoRA — Chỉ train phần nhỏ

**Vấn đề:** Full fine-tuning cập nhật 3 tỷ tham số — cần tới vài chục GB VRAM chỉ để lưu gradients và optimizer states.

**Giải pháp LoRA:**
1. **Freeze** toàn bộ trọng số gốc W — không thay đổi, không tính gradient
2. **Thêm Adapter** vào các lớp được chọn: hai ma trận nhỏ A và B
3. **Chỉ train** A và B

**Công thức toán học:**

```
W_mới = W_gốc + ΔW
       = W_gốc + (A × B) × (alpha / r)
```

Trong đó:
- `W_gốc`: ma trận trọng số gốc, kích thước [d_out × d_in], bị đóng băng
- `A`: ma trận [d_out × r], khởi tạo ngẫu nhiên (Gaussian)
- `B`: ma trận [r × d_in], khởi tạo bằng 0 (để ΔW = 0 lúc đầu)
- `r`: rank — số chiều của ma trận nén
- `alpha / r`: hệ số scaling

**Tại sao B khởi tạo bằng 0?** Để đầu ra của Adapter bằng 0 lúc bắt đầu, đảm bảo fine-tuning xuất phát từ chính xác hành vi của base model.

**Tính toán số tham số (r=32, chỉ attention layers):**

```python
r = 32

# Mỗi module attention (ví dụ q_proj: d=3072)
lora_q = 3072 * r + 3072 * r  # = 196,608 params
lora_k = 3072 * r + 1024 * r  # = 131,072 params
lora_v = 3072 * r + 1024 * r  # = 131,072 params
lora_o = 3072 * r + 3072 * r  # = 196,608 params

params_per_layer = lora_q + lora_k + lora_v + lora_o  # = 655,360
total_params = params_per_layer * 28  # = ~18.3M params

size_mb = (total_params * 4) / 1_000_000  # Float32 = 4 bytes
# Output: ~73 MB
```

**Kết quả:** Thêm ~18 triệu tham số (chỉ 0.6% so với 3 tỷ), nặng 73MB — và đây là toàn bộ thứ cần lưu trữ sau khi train.

Kiểm chứng thực tế: file `adapter_model.safetensors` trên HuggingFace = **73.4 MB**.

### 2.2 Quantization — 4-bit NF4

**So sánh dung lượng:**

| Precision | VRAM | Khả thi? |
|-----------|------|----------|
| 32-bit (float32) | ~12.9 GB | Load được, không train được |
| 8-bit | ~3.6 GB | OK |
| **4-bit (QLoRA)** | **~2.2 GB** | **Train thoải mái** |

**NF4 (Normal Float 4) là gì?**

4-bit thông thường chỉ lưu được 16 giá trị nguyên (0–15). NF4 thông minh hơn: nó ánh xạ 16 giá trị đó theo phân phối chuẩn (Normal Distribution) của trọng số neural network. Phần lớn trọng số nằm gần 0, nên NF4 phân bổ nhiều "điểm mô tả" hơn ở vùng này, giảm sai số lượng tử hóa.

**Double Quantization:** Nén thêm một lần nữa cả hằng số lượng tử hóa — tiết kiệm thêm ~0.37 bits/parameter.

**Lưu ý quan trọng:** Chỉ base model bị nén xuống 4-bit. Các LoRA adapter vẫn giữ ở float32/bfloat16 — vì đây là phần cần tính gradient chính xác để học.

```python
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,       # Double quantization
    bnb_4bit_compute_dtype=torch.bfloat16, # Tính toán ở 16-bit cho nhanh
    bnb_4bit_quant_type="nf4"             # Normal Float 4
)
```

**Tại sao `compute_dtype=bfloat16` chứ không phải float32?** Khi thực hiện phép tính (không phải lưu trữ), model tạm thời dequantize về bfloat16 để tính. bfloat16 đủ chính xác cho forward pass và nhanh hơn float32 trên GPU hiện đại.

---

## Phần 3: Luồng hoạt động QLoRA

### 3.1 Luồng Forward Pass khi training

```
Input Prompt (text)
        │
        ▼ Tokenizer
Token IDs [batch × seq_len]
        │
        ├─────────────────────────────────────────┐
        │                                         │
        ▼ (Base Model — FROZEN, 4-bit)            ▼ (LoRA Adapter — TRAINABLE, bf16)
embed_tokens                                      │
        │                                         │
 Layer 0..27:                                     │
   q_proj (4-bit) ──────────────────────────> + lora_A_q × lora_B_q × (α/r)
   k_proj (4-bit)
   v_proj (4-bit) ──────────────────────────> + lora_A_v × lora_B_v × (α/r)
   o_proj (4-bit) ──────────────────────────> + lora_A_o × lora_B_o × (α/r)
   MLP    (4-bit) ──────────────────────────> + lora_A_mlp × lora_B_mlp × (α/r)
        │                                         │
        └─────────────── cộng gộp (+) ────────────┘
                              │
                              ▼
                    Output logits [vocab_size]
                              │
                              ▼
                    Cross Entropy Loss (so với completion thực)
```

**Điểm mấu chốt:** Base model xử lý forward pass bình thường. Adapter tính song song và cộng kết quả vào. Đây là lý do LoRA không làm chậm inference — chỉ là một phép cộng thêm.

### 3.2 Bốn bước Training Loop

```
Bước 1: FORWARD PASS
    Prompt → [Base Model 4-bit] + [LoRA Adapters] → Predicted tokens

Bước 2: LOSS CALCULATION
    Cross Entropy(predicted_tokens, completion_tokens)
    Ví dụ: model dự đoán "249" nhưng thực tế là "199" → Loss cao

Bước 3: BACKWARD PASS (Backpropagation)
    Tính gradient chỉ cho A và B (bỏ qua 3 tỷ params của base model)
    → tiết kiệm ~99.4% khối lượng tính toán

Bước 4: OPTIMIZATION (paged_adamw_32bit)
    Cập nhật A và B theo hướng giảm Loss
    → bước nhỏ theo learning rate hiện tại
```

**Tại sao chỉ tính gradient cho Adapter?** Vì base model bị freeze — PyTorch biết không cần tính gradient cho các tensor này (`requires_grad=False`). Backprop chỉ đi qua nhánh LoRA.

### 3.3 Luồng Inference (sau khi train)

```python
# Load base model (4-bit, ~2.2GB)
base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.2-3B",
    quantization_config=quant_config,
    device_map="auto"
)

# Gắn adapter vào base model (+73MB)
fine_tuned_model = PeftModel.from_pretrained(base_model, "SeanSunny/price-2026-final")

# Inference
def model_predict(item):
    inputs = tokenizer(item["prompt"], return_tensors="pt").to("cuda")
    with torch.no_grad():
        output_ids = fine_tuned_model.generate(**inputs, max_new_tokens=8)
    prompt_len = inputs["input_ids"].shape[1]
    generated_ids = output_ids[0, prompt_len:]
    return tokenizer.decode(generated_ids)
```

**`max_new_tokens=8`:** Giá sản phẩm dưới $1000 — Llama tokenizer mã hóa số 0–999 thành 1 token duy nhất, cộng thêm dấu "." và "00" là tối đa 3–4 tokens. Đặt 8 là đủ an toàn.

**`torch.no_grad()`:** Tắt tính toán gradient khi inference — giảm ~50% VRAM sử dụng và tăng tốc đáng kể.

---

## Phần 4: Chuẩn bị dữ liệu cho Fine-Tuning

### File: `Code_Fine_tune/items.py` — Cấu trúc dữ liệu

```python
PREFIX = "Price is $"
QUESTION = "What does this cost to the nearest dollar?"

class Item(BaseModel):
    title: str
    category: str
    price: float
    summary: Optional[str] = None     # Text sạch từ Day 2 (LLM pre-processing)
    prompt: Optional[str] = None      # Input cho fine-tuning
    completion: Optional[str] = None  # Ground truth output
```

`summary` là đầu ra của Groq Batch API (Tuần 6 Day 2) — đã được LLM viết lại thành dạng chuẩn `Title / Category / Brand / Description / Details`. Đây là input duy nhất cho fine-tuning.

### Phân tích Token và chọn Cutoff

**Vấn đề:** Các mô tả sản phẩm có độ dài rất khác nhau — từ 20 đến 245+ tokens. GPU phải padding tất cả về cùng độ dài → mẫu dài nhất quyết định bộ nhớ cần dùng cho toàn bộ batch.

```python
# Đếm token với đúng tokenizer của model sẽ train
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B")
token_counts = [item.count_tokens(tokenizer) for item in items]

# Histogram cho thấy phần lớn < 100 tokens, đuôi dài đến 245+
```

**Quyết định: CUTOFF = 110 tokens**

```python
CUTOFF = 110
cut = len([c for c in token_counts if c > CUTOFF])
# Kết quả: ~5.7% mẫu bị cắt bớt
```

Chấp nhận cắt 5.7% dữ liệu để loại "đuôi dài" — thông tin quan trọng của sản phẩm thường nằm ở phần đầu (brand, category, main features), không mất nhiều khi cắt phần sau.

**Tại sao max_sequence_length = 128?**

- Summary tối đa: 110 tokens
- Question + PREFIX: ~16 tokens
- Tổng thực tế: 126 tokens
- Chọn 128 = 2⁷ (lũy thừa của 2) vì GPU xử lý bộ nhớ hiệu quả nhất ở kích thước này

### Prompt Format

```python
def make_prompts(self, tokenizer, max_tokens, do_round):
    tokens = tokenizer.encode(self.summary, add_special_tokens=False)
    if len(tokens) > max_tokens:
        summary = tokenizer.decode(tokens[:max_tokens]).rstrip()  # Cắt nếu quá dài
    else:
        summary = self.summary

    self.prompt = f"{QUESTION}\n\n{summary}\n\n{PREFIX}"
    self.completion = f"{round(self.price)}.00" if do_round else str(self.price)
```

**Ví dụ một mẫu train:**
```
Prompt:   "What does this cost to the nearest dollar?

           Title: Sony WH-1000XM5 Wireless Headphones
           Category: Electronics
           Brand: Sony
           Description: Premium noise-canceling headphones with 30h battery.
           Details: Multipoint connection, speak-to-chat feature.

           Price is $"

Completion: "280.00"
```

### Chiến lược Làm tròn giá (Rounding)

| Tập | Xử lý | Lý do |
|-----|--------|-------|
| Train & Val | Làm tròn → `"280.00"` | LLM là bài toán classification (next-token prediction), không phải regression. Làm tròn giúp model tập trung học magnitude (hàng đô) thay vì bị nhiễu bởi cents |
| Test | Giữ nguyên → `"279.99"` | Đánh giá công bằng, so sánh được với kết quả của DNN và frontier models |

**Llama Tokenizer — lợi thế đặc biệt:** Tokenizer của Llama mã hóa số 0–999 thành **1 token duy nhất** (ví dụ: "280" = 1 token). Với các model khác, "280" có thể bị tách thành "2", "8", "0" (3 tokens). Điều này biến bài toán thành: chọn đúng 1 trong ~1000 token giá — classification thuần túy, dễ học hơn nhiều.

---

## Phần 5: Cấu hình Training

### Hằng số và Hyperparameters (file `Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb`)

```python
BASE_MODEL = "meta-llama/Llama-3.2-3B"
LITE_MODE = False  # Full training với 800k samples

# Dataset
DATASET_NAME = "SeanSunny/items_prompts_full"  # 800k mẫu

# --- QLoRA Hyperparameters ---
QUANT_4_BIT = True
LORA_R = 64                          # Rank — năng lực học của adapter
LORA_ALPHA = LORA_R * 2              # = 128 (quy tắc: alpha = 2 × r)
LORA_DROPOUT = 0.1                   # Dropout 10% chống overfitting

ATTENTION_LAYERS = ["q_proj", "v_proj", "k_proj", "o_proj"]
MLP_LAYERS = ["gate_proj", "up_proj", "down_proj"]
TARGET_MODULES = ATTENTION_LAYERS + MLP_LAYERS  # Full mode: train cả attention lẫn MLP

# --- Training Hyperparameters ---
EPOCHS = 3
BATCH_SIZE = 16
MAX_SEQUENCE_LENGTH = 128
GRADIENT_ACCUMULATION_STEPS = 4     # Effective batch size = 16 × 4 = 64

# --- Optimizer & Scheduler ---
LEARNING_RATE = 2e-4
WARMUP_RATIO = 0.03                  # 3% bước đầu để warm-up
LR_SCHEDULER_TYPE = 'cosine'
WEIGHT_DECAY = 0.001
OPTIMIZER = "paged_adamw_32bit"

# --- Monitoring ---
VAL_SIZE = 1000
LOG_STEPS = 10
SAVE_STEPS = 200
```

### Giải thích từng Hyperparameter

**5 QLoRA Hyperparameters:**

**`LORA_R = 64`** — Rank của ma trận adapter. Số càng lớn, adapter càng "thông minh" (có thể học được các đặc trưng phức tạp hơn) nhưng tốn VRAM. Bắt đầu từ 8 hoặc 16 cho Light Mode; 64 là mức tốt cho Full Mode.

**`LORA_ALPHA = 128`** — Hệ số scaling. Công thức: ΔW thực tế = (A × B) × (alpha/r). Với alpha=128, r=64 → alpha/r = 2. Quy tắc ngón tay cái: `alpha = 2 × r` cho kết quả ổn định. Tăng alpha sẽ khuếch đại ảnh hưởng của adapter lên base model.

**`LORA_DROPOUT = 0.1`** — Xác suất "tắt" ngẫu nhiên 10% neurons trong adapter mỗi bước train. Cách hoạt động: mỗi forward pass, một nhóm neurons ngẫu nhiên bị set = 0. Model buộc phải học các đặc trưng độc lập, không phụ thuộc vào bất kỳ neuron cụ thể nào → chống overfitting.

**`TARGET_MODULES`** — Chọn attention + MLP vì Full Mode có đủ VRAM. Attention layers học "cái gì quan trọng trong mô tả" (ngữ cảnh). MLP layers học "kiến thức về giá" (fact-based knowledge). Kết hợp cả hai giúp model vừa hiểu ngữ cảnh vừa nhớ được mối quan hệ brand/category → price.

**`QUANT_4_BIT = True`** — Nén base model xuống NF4 (xem Phần 2). Kết quả: 12.9GB → 2.2GB, đủ VRAM để chứa cả model lẫn gradients.

**5 Training Hyperparameters:**

**`EPOCHS = 3`** — Số lần model nhìn thấy toàn bộ 800k mẫu. Quan sát thực tế: Epoch 1-2 model học tốt (Eval Loss giảm liên tục). Epoch 3 bắt đầu overfitting (Eval Loss tăng lại). Checkpoint tốt nhất lấy ở cuối Epoch 2.

**`BATCH_SIZE = 16` + `GRADIENT_ACCUMULATION_STEPS = 4`** — Effective batch size = 64. GPU chỉ load 16 mẫu mỗi lần (tránh OOM), nhưng tích lũy gradient qua 4 bước trước khi update → tương đương train với batch 64. Batch lớn hơn giúp gradient ổn định hơn.

**`LEARNING_RATE = 2e-4`** — Tốc độ học. Điểm khởi đầu chuẩn cho QLoRA (từ paper gốc của Dettmers et al.). Quá lớn → gradient bùng nổ, không hội tụ. Quá nhỏ → train rất chậm, dễ kẹt local minima.

**`OPTIMIZER = "paged_adamw_32bit"`** — Adam với Weight Decay, phiên bản Paged để quản lý bộ nhớ hiệu quả hơn. "Paged" nghĩa là optimizer states (momentum, variance) được đẩy sang CPU RAM khi GPU VRAM đầy, tránh OOM. Weight Decay = 0.001 là regularization nhẹ.

**`LR_SCHEDULER_TYPE = 'cosine'` + `WARMUP_RATIO = 0.03`** — Learning rate không cố định mà thay đổi theo thời gian:
- 3% bước đầu (Warmup): tăng tuyến tính từ 0 → 2e-4. Lý do: lúc đầu LoRA weights ngẫu nhiên → gradient hỗn loạn → LR cao ngay sẽ phá model. Warmup giúp ổn định.
- Phần còn lại: giảm dần theo hàm cosine về 0. Đầu train: LR lớn để thoát local minima. Cuối train: LR nhỏ để tinh chỉnh chính xác.

### Cấu hình LoRA và SFTConfig

```python
# LoRA config
lora_parameters = LoraConfig(
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    r=LORA_R,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=TARGET_MODULES,
)

# Training config
train_parameters = SFTConfig(
    output_dir=PROJECT_RUN_NAME,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
    optim=OPTIMIZER,
    save_steps=SAVE_STEPS,
    save_total_limit=10,              # Chỉ giữ 10 checkpoint gần nhất (tránh đầy đĩa)
    logging_steps=LOG_STEPS,
    learning_rate=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
    fp16=not use_bf16,
    bf16=use_bf16,
    max_grad_norm=0.3,                # Gradient clipping — tránh gradient bùng nổ
    warmup_ratio=WARMUP_RATIO,
    group_by_length=True,             # Nhóm mẫu cùng độ dài → giảm padding → train nhanh hơn
    lr_scheduler_type=LR_SCHEDULER_TYPE,
    report_to="wandb",
    max_length=MAX_SEQUENCE_LENGTH,
    eval_strategy="steps",
    eval_steps=SAVE_STEPS,
    push_to_hub=True,
    hub_model_id=HUB_MODEL_NAME,
)
```

**`max_grad_norm=0.3`:** Gradient clipping — nếu gradient vượt ngưỡng 0.3, scale nó xuống. Tránh "gradient explosion" khi model gặp mẫu dữ liệu bất thường.

**`group_by_length=True`:** Sắp xếp dataset theo độ dài token trước khi tạo batch. Các mẫu cùng độ dài được nhóm lại → giảm padding tối đa → tăng tốc train ~10–20%.

---

## Phần 6: Quá trình huấn luyện

### SFTTrainer — Cỗ máy tự động hóa

```python
fine_tuning = SFTTrainer(
    model=base_model,
    train_dataset=train,
    eval_dataset=val,
    peft_config=lora_parameters,
    args=train_parameters
)

# Một dòng lệnh thực thi toàn bộ training loop
fine_tuning.train()

# Push lên HuggingFace Hub
fine_tuning.model.push_to_hub(PROJECT_RUN_NAME, private=True)
```

`SFTTrainer` (từ thư viện `trl`) tự động:
- Nhận dataset với columns `prompt` và `completion`, ghép thành `text` hoàn chỉnh
- Thêm EOS token vào cuối mỗi mẫu (để model biết khi nào dừng)
- Thực hiện 4-bước training loop lặp đi lặp lại
- Tính Validation Loss mỗi `SAVE_STEPS` bước
- Lưu checkpoint và push lên Hub định kỳ

### Giám sát với Weights & Biases

W&B ghi lại 3 chỉ số quan trọng theo thời gian thực:

**Training Loss:** Giảm mạnh ngay từ đầu (từ ~3.0 xuống ~1.3 trong vài trăm bước đầu). Giai đoạn 1 này nhanh vì model học format ("À, phải trả lời bằng 'Price is $...'"). Sau đó giảm chậm hơn — giai đoạn 2 này model mới học kiến thức thực sự về giá.

**Validation Loss (Eval Loss):** Chỉ số trung thực nhất. Tính trên 1000 mẫu validation chưa bao giờ dùng để train. Nếu Training Loss giảm mà Eval Loss tăng → overfitting.

**Learning Rate:** Đường cong hình "quả núi" — tăng dần 3% bước đầu (warmup) rồi giảm theo cosine. Áp dụng liên tục qua toàn bộ 3 epochs, không reset.

### Phân tích Overfitting

```
Epoch 1-2:  Eval Loss ổn định giảm: 1.29 → 1.24 → 1.124 (tại bước ~6200)
                                                    ↑
                                            Điểm tốt nhất
Epoch 3:    Eval Loss tăng vọt lên 1.283 → OVERFITTING
```

**Nguyên nhân:** Với r=64 và 800k mẫu, model có đủ "bộ nhớ" để bắt đầu học vẹt sau 2 epochs. Epoch 3 củng cố memorization thay vì generalization.

**Giải pháp:** Lấy checkpoint tại bước ~6200 (cuối Epoch 2), không dùng model cuối cùng. Đây là lý do cấu hình `save_steps=200` — có đủ checkpoint để chọn lại.

---

## Phần 7: Kết quả và so sánh

### Kết quả Evaluation (200 mẫu test, `set_seed(42)`)

```
Fine-tuned Llama 3.2 3B (QLoRA) results
Error: $39.85   MSE: 4,643   R²: 78.9%
```

| Metric | Giá trị | Ý nghĩa |
|--------|---------|---------|
| **MAE** | **$39.85** | Trung bình sai lệch tuyệt đối — model sai trung bình $39.85/sản phẩm |
| **MSE** | **4,643** | Phạt nặng hơn cho các lỗi lớn — phản ánh một số dự đoán sai xa |
| **R²** | **78.9%** | Model giải thích được 78.9% variance trong giá — khá tốt cho bài toán giá sản phẩm |

**Đọc R² = 78.9%:** Nếu R² = 100%, model dự đoán hoàn hảo. R² = 0% tương đương đoán giá trung bình cố định. 78.9% nghĩa là model nắm bắt được ~79% tín hiệu thực sự trong dữ liệu — phần còn lại là noise (giá sale, regional pricing, v.v. không có trong mô tả).

### So sánh với toàn bộ leaderboard

| Hạng | Model | MAE |
|------|-------|-----|
| **1** | **Fine-tuned Llama 3.2 3B (QLoRA)** | **$39.85** |
| 2 | SentTrans frozen (4096) | $43.78 |
| 3 | DistilBERT V1 (5 epochs) | $44.19 |
| 4 | HashingVec DNN (289M params) | $46.02 |
| 5 | Claude Opus 4.5 (zero-shot) | $47.10 |
| 6 | Gemini 3 Pro | $50.54 |
| 13 | Human (giảng viên) | $87.62 |
| 14 | Base Llama 3.2 3B (zero-shot) | $110.72 |

**Nhận xét quan trọng:**

- Fine-tuned Llama cải thiện **64%** so với chính base model của nó ($110.72 → $39.85)
- Đánh bại DNN 289M params dù chỉ train một phần rất nhỏ của model
- Đánh bại Claude Opus 4.5 (frontier model đắt tiền) với chi phí inference gần như bằng 0 sau khi train xong
- Adapter nặng 73MB — toàn bộ "trí tuệ mới" học được gói gọn trong file nhỏ hơn nhiều ảnh RAW

---

## Phần 8: Deployment

Model được deploy lên **Modal serverless T4 GPU** qua `segment4/khong_su_dung/pricer_service2.py`. Chi tiết kiến trúc deployment, cách tích hợp vào EnsembleAgent (weight 10%), và xử lý cold start xem tại `report_system.md`.
