# Day 5 — QLoRA Fine-tune Qwen3.5-4B-Base cho bài toán ước giá tiếng Việt

**Phiên bản:** 1.1
**Ngày tạo:** 2026-04-24
**Cập nhật:** 2026-04-24 (session 2)
**Branch:** `feature/day5-qlora-qwen`
**Folder:** `tech2ai/fine_tune_qwen/`
**Người thực hiện:** Sunny
**Model code generation:** Claude Sonnet 4.6 (dựa trên file này)

---

## Trang thai thuc thi

| Phase | Trang thai | Ghi chu |
|-------|-----------|---------|
| Infrastructure | **DONE** | utils/, notebooks 00+01, pyproject.toml deps |
| Phase 0 — Profile tokens | **CHO USER CHAY** | `00_profile_tokens.ipynb` — khong can GPU |
| Phase 0 — Prepare dataset | **CHO USER CHAY** | `01_prepare_dataset.ipynb` — can HF_TOKEN |
| Phase 1 — Zero-shot v0 | PENDING | Can GPU, can confirm max_seq_length truoc |
| Phase 2 — Smoke v1 | PENDING | — |
| Phase 3 — Full v2 | PENDING | — |
| Phase 4 — High-rank v3 | PENDING | — |
| Phase 5 — Final v4 | PENDING | — |
| Phase 6 — Full eval | PENDING | — |

---

## 0. Ngữ cảnh và mục tiêu

### 0.1. Bối cảnh từ Day 3 và Day 4

| Day | Best approach | Test RMSLE | Gap vs 0.40 |
|-----|---------------|-----------|-------------|
| Day 3 | Blended TF-IDF + LGB | 0.5164 | 0.1164 |
| Day 4 v6 | Blended (PhoBERT + PCA+LGB + v4 + Day3) | 0.4187 | 0.0187 |
| Day 4 v7 | Stacked Ridge+EN+LGB (7 models) | 0.4059 | 0.0059 |
| **Day 4 v8** | **Stacked Ridge+EN+LGB (8 models, +PhoBERT-large)** | **0.4004** | **0.0004** |

**Kết luận Day 4:** Ceiling của encoder-only (BERT family) + stacking approach là ~0.40. Target 0.38 KHÔNG đạt — gap 0.0204.

### 0.2. Giả thuyết Day 5

Decoder LLM (Qwen3.5-4B-Base) với:
- **Scale lớn hơn** (4B params vs PhoBERT-large 370M) — hơn 10x
- **Pre-training đa ngữ** trên 201 ngôn ngữ bao gồm tiếng Việt
- **Autoregressive generation** có thể calibrate giá tốt hơn regression head truyền thống
- **QLoRA 4-bit** cho phép fine-tune trên 24GB VRAM với hiệu suất gần full fine-tune

→ **Có thể phá ceiling 0.40 và đạt target 0.38**.

### 0.3. Mục tiêu định lượng

| Mục tiêu | Ưu tiên | Ngưỡng |
|---------|---------|--------|
| **Chính:** RMSLE < 0.38 trên full test (3,872 items) | P0 | RMSLE ≤ 0.3800 |
| **Phụ 1:** RMSLE < 0.4004 (beat v8 standalone) | P1 | RMSLE ≤ 0.4000 |
| **Phụ 2:** MAPE < 30% | P2 | MAPE ≤ 30% |
| **Phụ 3:** R² > 0.70 | P2 | R² ≥ 0.70 |
| **Minh chứng:** Mỗi version (v0 → v4) đều có số liệu đầy đủ | P1 | Bảng leaderboard hoàn chỉnh |

### 0.4. Ràng buộc

- **GPU:** RTX 3090Ti hoặc 4090 **24GB VRAM** (1 card duy nhất)
- **Budget thời gian:** 4 tuần (28 ngày)
- **Độc lập với Day 4:** KHÔNG gộp Qwen vào v8 stacking pool. Day 5 đánh giá sức mạnh decoder LLM thuần.
- **Open-source only:** Qwen3.5-4B Apache 2.0, Unsloth Apache 2.0.

---

## 1. Quyết định kiến trúc (đã chốt với user)

### 1.1. Model

| Thành phần | Quyết định | Lý do |
|-----------|-----------|-------|
| Base model | `Qwen/Qwen3.5-4B-Base` | Base (không Instruct) — không có thinking mode, không có RLHF bias, "vải trắng" cho regression task. Model card chính thức khuyến nghị Base cho fine-tuning. |
| Quantization | QLoRA 4-bit NF4 + double quant | Giảm VRAM từ ~16GB (bf16) xuống ~4GB cho weights, còn VRAM cho activations + LoRA. |
| Compute dtype | bfloat16 | RTX 3090/4090 hỗ trợ bf16 native. |
| Framework | **PEFT + bitsandbytes** + TRL `SFTTrainer` | Unsloth 2026.4.8 load Qwen3.5 như VL model (Qwen3_5ForConditionalGeneration) — gây lỗi tokenizer và inference. Dùng PEFT + bitsandbytes thuần: chậm hơn ~2x nhưng stable. Phase 1 dùng HF transformers + BitsAndBytesConfig. |
| Tokenizer | Qwen stock (vocab 151,936) | Không extend vocab ở Day 5 (rủi ro cao, effort lớn). Day 6 consider nếu v4 thất bại. |

**Phát hiện quan trọng về Qwen tokenizer (2026-04-25):**
Qwen3.5 tokenize từng chữ số thành 1 token riêng (digit-by-digit), khác với Llama 3.2 (3 chữ số = 1 token).

| Number | Llama 3.2 | Qwen3.5 | Tokens Qwen |
|--------|-----------|---------|-------------|
| 100 | **1 token** | 3 tokens | `['1','0','0']` |
| 999 | **1 token** | 3 tokens | `['9','9','9']` |
| 1000 | ~2 tokens | **4 tokens** | `['1','0','0','0']` |

Tác động:
- `max_new_tokens = 4` vẫn đúng (completion range [5, 1000], max "1000" = 4 tokens — xác nhận bởi profile_results_v3.json).
- Qwen phải chain-generate từng digit tuần tự → có rủi ro sinh thêm digit thừa nếu không học EOS đúng cách (xem Section 12, R8).
- Llama biến bài toán thành classification 1 bước; Qwen chia thành nhiều bước sequential — khó hơn nhưng vẫn feasible với fine-tuning.

### 1.2. Dữ liệu

| Thành phần | Quyết định |
|-----------|-----------|
| Nguồn | `SeanSunny/items_tv_v6` (HuggingFace) — 110K train / 5K val / 5K test (gốc) |
| Phạm vi giá | price ≤ 1,000,000 VND (filter cả 3 splits) |
| Output dataset | `SeanSunny/items_prompts_tv_3` (**DA PUSH** — train=85,727 / val=3,926 / test=3,872) |
| Schema | `prompt` (từ cột `summary`), `completion` (round(price/1000)), `price_vnd_true` |

### 1.3. Prompt format (CHỐT)

**Prompt template:**

```
Sản phẩm này có giá bao nhiêu ?
Tiêu đề: {title}
Danh mục: {category}
Thương hiệu: {brand}
Mô tả: {description}
Thông số: {features}

Giá là: 
```

**Completion:**

- **Train/Val:** `str(round(price / 1000))` — integer thuần, string. Ví dụ giá 150,000 VND → `"150"`; giá 4,900 VND → `"5"`; giá 2,376,000 VND → `"2376"`.
- **Test:** giữ nguyên `price` gốc (VND đầy đủ) làm ground truth. Completion chỉ dùng để build prompt, không dùng eval trực tiếp.

**Lý do chọn completion "nghìn đồng":**
- Giá VND có 4-7 chữ số → tokenize thành 3-4 tokens. Chia 1000 → 1-4 chữ số → 1-2 tokens. `max_new_tokens` giảm mạnh.
- Phân phối completion [5, 1000] gọn hơn [4900, 1000000] — dễ học.
- Round để model học integer thuần, pattern sạch. Sai số round tối đa 500 VND/item (chỉ ảnh hưởng train, không ảnh hưởng metric test).

### 1.4. Xử lý field `brand` và `features` (nếu thiếu)

Một số item có thể thiếu `brand` hoặc `features`. Xử lý:
- `brand` thiếu → điền `"Không rõ"`
- `features` thiếu → điền `"Không có thông số"`
- `description` thiếu → điền `"Không có mô tả"`

Việc có tất cả field nhất quán giúp model học ổn định.

### 1.5. Metric eval

| Metric | Mô tả | Tính như thế nào |
|--------|-------|-------------------|
| **RMSLE** (primary) | Root Mean Squared Log Error | `sqrt(mean((log1p(y_pred) - log1p(y_true))^2))` — đo trên giá VND (sau khi unscale × 1000) |
| MAE | Mean Absolute Error (VND) | `mean(|y_pred - y_true|)` |
| MAPE | Mean Absolute Percentage Error | `mean(|y_pred - y_true| / y_true) × 100` |
| R² | Coefficient of determination | `1 - SS_res/SS_tot` |

**Reuse:** `pricer_vi/evaluator.py` (đã có từ Day 3/4). Function `rmsle(y_true, y_pred)` đã implement sẵn.

---

## 2. Phase 0 — Profile & chuẩn bị (Ngày 1-2)

**Mục tiêu:** Đo các tham số quan trọng trên dữ liệu THỰC TẾ trước khi fine-tune.

### 2.1. Notebook `00_profile_tokens.ipynb`

**Mục đích:** Đo distribution token count để chốt `max_seq_length` và `max_new_tokens`.

**Các bước code:**

1. Load tokenizer Qwen3.5-4B-Base:
```python
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-4B-Base")
```

2. Load dataset `SeanSunny/items_tv_v6`, build prompt cho 1000 random train samples.

3. Đo:
   - **Prompt token length:** tokenize prompt (không có completion), ghi lại `len(tokens)`. Plot histogram. Báo cáo p50/p90/p95/p99/max.
   - **Completion token length:** tokenize `str(round(price/1000))` cho 1000 samples. Thường 1-3 tokens. Xác định `max_new_tokens` = p99 + 1 (round buffer).
   - **Full (prompt + completion) length:** quyết định `max_seq_length` = p95 round lên bội số 64 (thường 256, 384, 512).

4. So sánh với English reference (prompt EN ~110-128 tokens). Dự kiến VN sẽ dài hơn 1.5-2x.

5. **Output cần ghi:**
   - `profile_results.json`:
     ```json
     {
       "prompt_tokens": {"p50": ..., "p90": ..., "p95": ..., "p99": ..., "max": ...},
       "completion_tokens": {"p50": ..., "p99": ..., "max": ...},
       "recommended_max_seq_length": ...,
       "recommended_max_new_tokens": ...
     }
     ```

### 2.2. Notebook `01_prepare_dataset.ipynb`

**Mục đích:** Build prompt/completion, push lên HF.

**Các bước:**

1. Load `SeanSunny/items_tv_v6` (train/val/test).

2. Function `build_prompt(item)`:
```python
PROMPT_TEMPLATE = """Sản phẩm này có giá bao nhiêu ?
Tiêu đề: {title}
Danh mục: {category}
Thương hiệu: {brand}
Mô tả: {description}
Thông số: {features}

Giá là: """

def build_prompt(item: dict) -> str:
    return PROMPT_TEMPLATE.format(
        title=item.get("title") or "",
        category=item.get("category") or "",
        brand=item.get("brand") or "Không rõ",
        description=item.get("description") or "Không có mô tả",
        features=item.get("features") or "Không có thông số",
    )

def build_completion(price: float, for_test: bool) -> str:
    if for_test:
        # test giữ VND gốc làm ground truth
        return str(int(round(price)))
    else:
        # train/val round về nghìn đồng
        return str(int(round(price / 1000)))
```

3. Apply lên 3 splits:
   - Train: `{"prompt": ..., "completion": "150", "price_vnd_true": 150000}`
   - Val: giống train
   - Test: `{"prompt": ..., "completion": "150000", "price_vnd_true": 150000}` — completion chỉ reference, eval dùng `price_vnd_true`

4. Schema cuối:

| Column | Type | Mô tả |
|--------|------|-------|
| `prompt` | str | Template đã fill |
| `completion` | str | Giá dạng string (train/val: /1000 rounded; test: VND gốc) |
| `price_vnd_true` | int | Giá VND gốc (dùng cho eval) |
| `category` | str | Danh mục (kept for stratification) |
| `id` | int | ID gốc từ items_tv_v6 |

5. Push lên HF: `DatasetDict({...}).push_to_hub("SeanSunny/items_prompts_tv_1")`.

6. **Output cần ghi:** `dataset_stats.md` — số lượng items mỗi split, distribution giá/category, sample 5 row.

### 2.3. Checklist Phase 0

- [ ] `profile_results.json` có đủ p50/p95/p99 cho prompt/completion/full
- [x] Chốt được `max_seq_length` = **192** (p95_full=149, profile_results_v3.json)
  - Lý do giữ 192 thay vì 256: tiết kiệm VRAM, đủ cho p95.
  - Bù trừ bằng **Option B — pre-truncate prompt trong `formatting_func`**: cắt prompt tối đa `MAX_PROMPT_TOKENS = 192 - 4 - 1 = 187` tokens trước khi concat completion + EOS. Đảm bảo completion không bao giờ bị SFTTrainer truncate (SFTTrainer dùng `keep_start` — cắt từ cuối, completion bị cắt trước). Khoảng 5% prompt dài nhất bị cắt — chấp nhận được (English reference cũng cắt 5.7%).
  - **Áp dụng từ Phase 2 (training)** — Phase 1 (zero-shot inference) không cần truncate.
- [x] Chốt được `max_new_tokens` = **4** (profile xác nhận completion max=4 tokens, p99=3; "1000" = 4 digits = 4 tokens với Qwen tokenizer digit-by-digit)
- [ ] `SeanSunny/items_prompts_tv_1` pushed lên HF, 3 splits
- [ ] `dataset_stats.md` có sample 5 prompt hoàn chỉnh
- [ ] Confirm tokenizer không có issue encode/decode tiếng Việt (round-trip test)

---

## 3. Phase 1 — Zero-shot baseline (Ngày 3)

**Mục tiêu:** Đo khả năng ước giá của Qwen3.5-4B-Base KHÔNG fine-tune. Cung cấp lower bound để đánh giá improvement.

### 3.1. Notebook `02_baseline_v0.ipynb`

**Các bước:**

1. Load Qwen3.5-4B-Base với Unsloth 4-bit:
```python
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen3.5-4B-Base",
    max_seq_length=MAX_SEQ_LENGTH,  # từ Phase 0
    dtype=None,  # auto
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)  # enable 2x faster inference
```

2. Load test set (3,872 items), chọn 500 random sample.

3. Function `predict(prompt)`:
```python
def predict(prompt: str) -> int:
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,  # từ Phase 0
        do_sample=False,  # greedy
        pad_token_id=tokenizer.eos_token_id,
    )
    generated = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    # Extract first number
    import re
    match = re.search(r'\d+', generated)
    return int(match.group()) if match else 0
```

4. Predict trên 500 sample → so với `price_vnd_true`:
   - `pred_vnd = predict(prompt) * 1000`
   - Compute RMSLE, MAE, MAPE, R² dùng `utils/evaluator.py`

5. **Output:** `results/v0_results.json` với metrics + 20 sample (prompt excerpt, generated_raw, pred_vnd, true_vnd, error_pct).

6. **Kỳ vọng:** RMSLE rất xấu (> 1.0) vì model chưa biết pattern completion number thuần. Đây là baseline để đo improvement.

**Ghi chú kỹ thuật Phase 1 (zero-shot):**
- Dùng `predict_one()` đơn giản từ `utils/inference.py` — chưa áp dụng StoppingCriteria (xem R8).
- Mục tiêu Phase 1 là đo lower bound, không cần optimize inference pipeline.
- Nếu model sinh ra chuỗi không có chữ số → `predict_one` trả về 0 → pred_vnd = 0 → RMSLE rất cao — ghi nhận vào kết quả.
- **StoppingCriteria + 3-layer inference safety sẽ implement từ Phase 2** khi có fine-tuned model (xem R8).
- Load model theo cách **Unsloth primary, HF transformers + BitsAndBytes fallback** (xem Section 11).

### 3.2. Checklist Phase 1

- [ ] v0 RMSLE recorded
- [ ] Sample 20 predictions inspected manually (model output có format lạ không?)
- [ ] Generation speed measured (items/sec)

---

## 4. Phase 2 — Smoke test v1 (Ngày 4-5)

**Mục tiêu:** Fine-tune 20K sample với config nhỏ để validate pipeline end-to-end trước khi dùng full data.

### 4.1. Notebook `03_train_v1_smoke.ipynb`

**Config v1:**

| Param | Value |
|-------|-------|
| Training data | 20,000 random samples từ train split |
| Val data | 500 random từ val split |
| LoRA rank | **32** |
| LoRA alpha | **64** (= r × 2) |
| LoRA dropout | 0.1 |
| Target modules | **Attention only**: `q_proj`, `k_proj`, `v_proj`, `o_proj` |
| Epochs | **2** |
| Per-device batch size | 8 (điều chỉnh theo seq_length từ Phase 0) |
| Grad accumulation | 8 (effective bs = 64) |
| Learning rate | 2e-4 |
| Scheduler | cosine |
| Warmup ratio | 0.03 |
| Weight decay | 0.001 |
| Optimizer | `paged_adamw_32bit` |
| Max seq length | From Phase 0 |
| Gradient checkpointing | True (Unsloth "unsloth" mode) |
| Packing | False (keep simple ở v1) |

### 4.2. Code structure

```python
from unsloth import FastLanguageModel
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset

# 1. Load model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen3.5-4B-Base",
    max_seq_length=MAX_SEQ_LENGTH,
    load_in_4bit=True,
)

# 2. Add LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=64,
    lora_dropout=0.1,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# 3. Load dataset
ds = load_dataset("SeanSunny/items_prompts_tv_1")
train_ds = ds["train"].shuffle(seed=42).select(range(20000))
val_ds = ds["val"].shuffle(seed=42).select(range(500))

# 4. Format function: Option B — pre-truncate prompt để đảm bảo completion không bị SFTTrainer cắt.
# SFTTrainer dùng keep_start (cắt từ cuối) → completion bị mất nếu prompt quá dài.
# Giải pháp: cắt prompt tại token level trước khi concat, giống English reference (CUTOFF=110).
MAX_PROMPT_TOKENS = MAX_SEQ_LENGTH - MAX_NEW_TOKENS - 1  # 192 - 4 - 1 = 187

def formatting_func(example):
    prompt_ids = tokenizer.encode(example["prompt"], add_special_tokens=False)
    if len(prompt_ids) > MAX_PROMPT_TOKENS:
        prompt_ids = prompt_ids[:MAX_PROMPT_TOKENS]
        prompt = tokenizer.decode(prompt_ids, skip_special_tokens=True)
    else:
        prompt = example["prompt"]
    return prompt + example["completion"] + "\n" + tokenizer.eos_token

# 5. Trainer
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_ds,
    formatting_func=formatting_func,
    args=SFTConfig(
        output_dir="weights/v1_adapter",
        per_device_train_batch_size=8,
        gradient_accumulation_steps=8,
        num_train_epochs=2,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        weight_decay=0.001,
        optim="paged_adamw_32bit",
        bf16=True,
        max_seq_length=MAX_SEQ_LENGTH,
        packing=False,
        save_strategy="epoch",
        logging_steps=20,
        report_to="none",
        seed=42,
    ),
)

trainer.train()
model.save_pretrained("weights/v1_adapter")
tokenizer.save_pretrained("weights/v1_adapter")
```

### 4.3. Eval v1

Sau train xong:
1. `FastLanguageModel.for_inference(model)`
2. Eval trên 500 val items → RMSLE
3. Eval trên full 3,872 test items → full metrics
4. Save `v1_results.json`

### 4.4. Checklist Phase 2

- [ ] v1 train completed không OOM
- [ ] Loss giảm liên tục (ghi lại train loss mỗi 20 steps)
- [ ] v1 RMSLE < v0 RMSLE (chứng minh fine-tune có tác dụng)
- [ ] Push adapter lên HF: `SeanSunny/qwen3.5-4b-vn-pricer-v1`
- [ ] Nếu v1 RMSLE > 0.6 → có vấn đề pipeline, debug trước khi v2

---

## 5. Phase 3 — Full training v2 (Ngày 6-8)

**Mục tiêu:** Main run với config chuẩn (matching English reference full run), full 85K data.

### 5.1. Config v2

| Param | Value | Diff vs v1 |
|-------|-------|------------|
| Training data | **Full 85,727 samples** | 4.3x hơn v1 |
| LoRA rank | **64** | 2x hơn v1 |
| LoRA alpha | **128** | 2x hơn v1 |
| LoRA dropout | 0.1 | = |
| Target modules | **All 7**: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` | Thêm MLP |
| Epochs | **3** | 1.5x hơn v1 |
| Batch/grad_accum | Same (effective 64) | = |
| LR | 2e-4 cosine | = |

### 5.2. Code delta so với v1

Chỉ thay 2 blocks:

```python
# LoRA config
model = FastLanguageModel.get_peft_model(
    model,
    r=64,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=128,
    lora_dropout=0.1,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# Dataset
train_ds = ds["train"].shuffle(seed=42)  # full 85K
val_ds = ds["val"].shuffle(seed=42).select(range(500))

# Trainer: num_train_epochs=3
```

### 5.3. Monitoring

- **Train loss:** kỳ vọng giảm từ ~3.0 → ~0.5 sau 3 epochs
- **Val RMSLE eval mỗi epoch** (500 sample, không chặn training):
  - Epoch 1: RMSLE < 0.50 (sanity)
  - Epoch 2: RMSLE < 0.45
  - Epoch 3: RMSLE < 0.40 (hy vọng)
- **VRAM usage:** log peak mỗi 100 steps
- **Time per epoch:** log để estimate cho v3

### 5.4. Eval v2

Sau train:
1. Eval full 3,872 test → `v2_results.json`
2. **Gate:** RMSLE v2 < 0.4004 (v8) → PASSED
3. Push adapter: `SeanSunny/qwen3.5-4b-vn-pricer-v2`
4. Nếu v2 đạt < 0.38 → có thể skip v3, focus vào v4 tricks. Ngược lại đi v3.

### 5.5. Checklist Phase 3

- [ ] v2 train 3 epochs complete
- [ ] Val RMSLE curve saved (per epoch)
- [ ] Full test RMSLE < 0.4004
- [ ] Adapter pushed to HF
- [ ] VRAM không crash (log peak usage)

---

## 6. Phase 4 — High-rank v3 (Ngày 9-11)

**Mục tiêu:** Xem LoRA rank cao hơn có improvement không, hay bị saturation.

### 6.1. Config v3

| Param | Value | Diff vs v2 |
|-------|-------|------------|
| LoRA rank | **128** | 2x hơn v2 |
| LoRA alpha | **256** | 2x hơn v2 |
| Target modules | All 7 | = |
| Epochs | 3 | = |
| Batch size | **4** (giảm) | Nửa v2 |
| Grad accumulation | **16** (tăng) | 2x v2 — giữ effective bs = 64 |
| LR | **1.5e-4** | Giảm vì rank cao cần LR nhỏ hơn |

### 6.2. Rationale

- Rank 128 → trainable params ~2x v2. Theo heuristics, rank cao cần LR thấp hơn để không diverge.
- Giảm bs để tránh OOM (rank 128 cần thêm VRAM cho adapter weights + gradients).
- Grad accum tăng giữ effective batch = 64 → training dynamics giống v2.

### 6.3. Eval & decision

- Eval v3 full test → `v3_results.json`
- **So sánh v2 vs v3:**
  - Nếu v3 RMSLE < v2 RMSLE (improvement) → dùng v3 làm base cho v4
  - Nếu v3 ≈ v2 → saturation ở rank 64, dùng v2 cho v4
  - Nếu v3 > v2 → overfit, dùng v2 cho v4
- Push adapter: `SeanSunny/qwen3.5-4b-vn-pricer-v3`

### 6.4. Checklist Phase 4

- [ ] v3 train complete
- [ ] Compare table v2 vs v3 (RMSLE, MAE, MAPE, R²)
- [ ] Decide base cho v4 (v2 hoặc v3)
- [ ] Adapter pushed

---

## 7. Phase 5 — Final v4 với tricks (Ngày 12-13)

**Mục tiêu:** Squeeze cuối — áp dụng các tricks để đạt dưới 0.38.

### 7.1. Tricks cần thử (chọn 2-3 từ list)

| Trick | Mô tả | Kỳ vọng |
|-------|-------|---------|
| **NEFTune** | Add noise vào embedding khi train (noise_alpha=5) | +0.5-1% RMSLE |
| **Packing** | Nhiều sequences trong 1 batch → training nhanh hơn 2-3x | Speed, không direct improve RMSLE |
| **LR sweep** | Thử 1e-4, 2e-4, 3e-4 với cutoff 30% data → pick best | +~0.5% |
| **Longer training** | 5 epochs với early stop trên val RMSLE | Xem có underfit không |
| **Data augmentation** | Paraphrase 10K random train prompt bằng LLM | Rủi ro, có thể không improve |
| **Weighted sampling** | Over-sample rare price bins (giống v8 PhoBERT-large) | +~0.5% |

### 7.2. Config v4 đề xuất

Base: v2 hoặc v3 (tùy Phase 4 decide). Apply:
- **NEFTune alpha=5** (trivial change trong SFTConfig: `neftune_noise_alpha=5`)
- **Packing=True** (training nhanh hơn → có thể train 5 epochs)
- **LR:** dùng best từ sweep nhỏ (chạy 3 runs 30% data với LR ∈ {1e-4, 2e-4, 3e-4}, pick best RMSLE val → áp cho full run)
- **Epochs:** 5 với early_stopping patience=2 (monitor val RMSLE)

### 7.3. Eval v4

- Eval full test → `v4_results.json`
- **Gate:** RMSLE v4 < 0.38 ? → PASS target
- Push adapter: `SeanSunny/qwen3.5-4b-vn-pricer-v4`
- Merge LoRA + save full model:
```python
model.save_pretrained_merged("weights/v4_merged", tokenizer, save_method="merged_16bit")
# Push merged ~8GB
model.push_to_hub_merged("SeanSunny/qwen3.5-4b-vn-pricer-v4-merged", tokenizer,
                         save_method="merged_16bit", token=HF_TOKEN)
```

### 7.4. Checklist Phase 5

- [ ] LR sweep hoàn tất (nếu chọn)
- [ ] v4 train 5 epochs hoặc early-stopped
- [ ] v4 RMSLE so với v2, v3 ghi nhận rõ
- [ ] Adapter + merged model pushed to HF

---

## 8. Phase 6 — Full evaluation & viết summary (Ngày 14)

### 8.1. Notebook `07_eval_full.ipynb`

**Các bước:**

1. Re-eval mọi version (v0, v1, v2, v3, v4) trên **cùng** full test 3,872 items để đảm bảo fair comparison.
2. Build leaderboard table.
3. Plot error distribution per version.
4. Case study: 10 items predict đúng + 10 items predict sai nhiều → phân tích.

### 8.2. Leaderboard format (output cuối)

| Version | RMSLE | MAE (VND) | MAPE (%) | R² | Δ vs v8 (0.4004) |
|---------|-------|-----------|----------|----|-----------------| 
| v0 zero-shot | ? | ? | ? | ? | ? |
| v1 smoke 20K | ? | ? | ? | ? | ? |
| v2 full r=64 | ? | ? | ? | ? | ? |
| v3 r=128 | ? | ? | ? | ? | ? |
| **v4 final** | **?** | **?** | **?** | **?** | **?** |
| **Day 4 v8 (ref)** | **0.4004** | **79,853** | **30.7%** | **69.2%** | **0** |

### 8.3. Summary file `day5_summary.md`

Viết bằng tiếng Việt có dấu, ~300 dòng, cover:
1. Tóm tắt kết quả + leaderboard
2. Giải thích QLoRA (tại sao 4-bit NF4, LoRA rank)
3. Giải thích Unsloth (tại sao nhanh + ít RAM hơn HF thuần)
4. Tiến trình v0 → v4, mỗi version 1 paragraph
5. Phân tích tokenizer tiếng Việt (Phase 0 findings)
6. Case study (10 items tốt + 10 items xấu)
7. So sánh Day 4 v8 vs Day 5 v4
8. Hạn chế và hướng phát triển (Day 6: vocab extension, scale 9B, stacking với v8)

### 8.4. Checklist Phase 6

- [ ] Leaderboard hoàn chỉnh 5 versions
- [ ] `day5_summary.md` ≥ 300 dòng
- [ ] `SESSION_HANDOFF.md` updated với Day 5 results
- [ ] Merge branch (confirm với user trước khi merge)

---

## 9. Folder structure cuối Day 5

```
tech2ai/fine_tune_qwen/
├── plan_day5.md                       # File này
├── day5_summary.md                    # Viết cuối Day 5
├── profile_results.json               # Output Phase 0
├── dataset_stats.md                   # Output Phase 0
├── 00_profile_tokens.ipynb            # Phase 0
├── 01_prepare_dataset.ipynb           # Phase 0
├── 02_baseline_v0.ipynb               # Phase 1
├── 03_train_v1_smoke.ipynb            # Phase 2
├── 04_train_v2.ipynb                  # Phase 3
├── 05_train_v3.ipynb                  # Phase 4
├── 06_train_v4_final.ipynb            # Phase 5
├── 07_eval_full.ipynb                 # Phase 6
├── utils/
│   ├── __init__.py
│   ├── prompt_builder.py              # build_prompt, build_completion
│   ├── inference.py                   # predict(), batched_predict()
│   ├── evaluator.py                   # import from pricer_vi/
│   └── hf_upload.py                   # push adapter/merged helpers
├── weights/
│   ├── v1_adapter/
│   ├── v2_adapter/
│   ├── v3_adapter/
│   └── v4_adapter/
└── results/
    ├── v0_results.json
    ├── v1_results.json
    ├── v2_results.json
    ├── v3_results.json
    ├── v4_results.json
    └── leaderboard.md
```

---

## 10. HuggingFace deliverables

| Resource | Name | Size | Mô tả |
|----------|------|------|-------|
| Dataset | `SeanSunny/items_prompts_tv_1` | ~50MB | 3 splits, prompt/completion format |
| Adapter v1 | `SeanSunny/qwen3.5-4b-vn-pricer-v1` | ~80MB | LoRA r=32, smoke 20K |
| Adapter v2 | `SeanSunny/qwen3.5-4b-vn-pricer-v2` | ~200MB | LoRA r=64, all modules, full data |
| Adapter v3 | `SeanSunny/qwen3.5-4b-vn-pricer-v3` | ~400MB | LoRA r=128 |
| Adapter v4 | `SeanSunny/qwen3.5-4b-vn-pricer-v4` | ~200-400MB | Best + tricks |
| Merged v4 | `SeanSunny/qwen3.5-4b-vn-pricer-v4-merged` | ~8GB | Merged bf16 cho inference |

---

## 11. Dependencies và setup

### 11.1. Environment

Thêm vào `pyproject.toml` (hoặc `uv add`):

```bash
uv add unsloth
uv add "trl>=0.8.0"
uv add "transformers>=4.44.0"
uv add "peft>=0.11.0"
uv add "bitsandbytes>=0.43.0"
uv add "accelerate>=0.30.0"
uv add datasets
```

Lưu ý Unsloth yêu cầu phiên bản PyTorch + CUDA khớp — tham khảo `unsloth.ai/docs/models/qwen3.5` cho lệnh install chính xác.

### 11.2. HF auth

```bash
huggingface-cli login  # paste HF_TOKEN có write access
```

Hoặc `export HF_TOKEN=hf_xxx` trong `.env`.

### 11.3. GPU check

Trước Phase 0 chạy:
```python
import torch
print(torch.cuda.is_available(), torch.cuda.get_device_name(0))
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
# Expected: True, "NVIDIA GeForce RTX 3090/4090", VRAM: 24.0
```

---

## 12. Risks & fallbacks

| # | Rủi ro | Xác suất | Tác động | Phương án |
|---|--------|---------|----------|-----------|
| R1 | Tokenizer Qwen split tiếng Việt quá tệ (p95 > 800 tokens) | Trung bình | seq_length phải tăng → bs giảm → train chậm | Phase 0 profile trước. Nếu xấu: tăng seq lên 768, giảm bs xuống 4, grad_accum 16. |
| R2 | v1 smoke RMSLE > 0.6 (không beat v0 much) | Thấp | Pipeline có bug | Debug: inspect generated output, check prompt format có leak completion không, check tokenizer encode-decode round-trip |
| R3 | OOM khi v3 (rank 128) | Trung bình | Phải giảm bs | Fallback bs=2, grad_accum=32; hoặc skip v3, làm 2 versions v4 khác thay thế |
| R4 | v4 RMSLE vẫn > 0.38 | Trung bình cao | Không đạt target chính | Day 6: (a) vocab extension VN tokens; (b) scale lên Qwen3.5-9B QLoRA với CPU offload; (c) stacking v4 với v8 pool (cần user approve) |
| R5 | Training diverge (loss tăng) | Thấp | Phải restart | Giảm LR 2x, tăng warmup lên 0.1, check data có NaN |
| R6 | HF upload fail (token, size) | Thấp | Không push được | Keep local weights, retry sau. Merged 8GB cần git-lfs, kiểm tra quota HF |
| R7 | Unsloth version conflict với Qwen3.5 | **XAY RA** | Load như VL model, lỗi tokenizer + FailOnRecompileLimitHit | **RESOLVED (2026-04-26):** Dùng PEFT + bitsandbytes thuần cho toàn bộ Day 5. Unsloth bị loại khỏi pipeline. |
| R8 | Qwen sinh thêm digit thừa sau số (digit-by-digit tokenizer) | Trung bình | pred_vnd sai 10x (ví dụ "150"→"1500"→1,500,000 VND) | **3 lớp phòng vệ — implement từ Phase 2:** (1) `StopOnNonDigit` StoppingCriteria dừng khi token không phải digit; (2) `extract_price_thousands()` clamp về [5,1000]; (3) Thêm `"\n"` sau completion trong formatting_func để model học stop token rõ ràng hơn. Phase 1 (zero-shot) chưa cần — kết quả xấu là expected. |

---

## 13. Acceptance criteria (để Sonnet 4.6 biết khi nào done)

Day 5 coi là **DONE** khi tất cả:

- [ ] 5 notebooks chạy xong, output commit vào git
- [ ] 5 versions adapter + 1 merged model trên HF
- [ ] Dataset `items_prompts_tv_1` trên HF
- [ ] `leaderboard.md` có số liệu 5 versions
- [ ] `day5_summary.md` ≥ 300 dòng tiếng Việt có dấu
- [ ] `SESSION_HANDOFF.md` updated
- [ ] Branch `feature/day5-qlora-qwen` pushed, ready for review

**Target phụ (nice-to-have):**
- [ ] RMSLE v4 < 0.38 (đạt target chính)
- [ ] RMSLE v4 < 0.4004 (beat v8 standalone)

---

## 14. Ghi chú cho code generator (Sonnet 4.6)

1. **Dùng `uv run`** cho mọi lệnh Python (KHÔNG dùng `python3` hoặc `pip`).
2. **Reuse `pricer_vi/evaluator.py`** cho metric — đã có RMSLE function.
3. **Reuse prompt/completion builder** trong `utils/prompt_builder.py` xuyên suốt, KHÔNG duplicate logic trong từng notebook.
4. **Seed = 42** mọi nơi (numpy, torch, random, Unsloth random_state).
5. **Luôn log:** train loss mỗi 20 steps, val RMSLE mỗi epoch, VRAM peak mỗi 100 steps.
6. **Save intermediate:** Sau mỗi phase complete, git commit với message `day5 phaseN: [short desc]`.
7. **Notebook format:** Mỗi notebook mở đầu bằng markdown cell giải thích mục đích + config, kết thúc bằng markdown cell tóm tắt kết quả.
8. **KHÔNG emoji** trong code, log, comments.
9. **Tiếng Việt** trong markdown/comments giải thích là OK; code + identifiers tiếng Anh.
10. **Commit pattern:** `day5 vN: [phase] [outcome]`. Ví dụ `day5 v2: training complete, test RMSLE=0.39`.

---

## 15. Timeline tổng hợp

```
Ngày:    1   2   3   4   5   6   7   8   9  10  11  12  13  14
Phase 0: ██████
Phase 1:         ██
Phase 2:            ██████
Phase 3:                  ████████████
Phase 4:                               ████████████
Phase 5:                                            ████████
Phase 6:                                                       ██
```

Buffer: Nếu v2 đạt < 0.38 thì skip v3, dành buffer cho v4 experiments.

---


## code và tài liệu tham khảo khi xử lý đối với dữ liệu tiếng anh ở: scraping_data_tv/Data_processing_for_English_data/fine_tune_LLM.txt và scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune

*Tạo: 2026-04-24. Dựa trên English reference `Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb` + Day 4 v8 results + Qwen3.5 model card (Feb 2026). Người thực hiện tiếp theo: Claude Sonnet 4.6 tạo code theo từng Phase.*
