# Day 5 — QLoRA Fine-tune Qwen3.5-4B-Base cho bài toán ước giá tiếng Việt

**Phiên bản:** 2.0 (rewrite gọn lại)
**Ngày tạo:** 2026-04-24
**Cập nhật:** 2026-04-29 (session 9 — Stage 2 DONE, items_prompts_tv_4 269K pushed)
**Branch:** `feature/day5-qlora-qwen`
**Folder:** `tech2ai/fine_tune_qwen/`

---

## Trạng thái thực thi

| Phase | Trạng thái | Kết quả |
|-------|-----------|---------|
| Phase 0 — Profile + Dataset | **DONE** | `profile_results_v3.json`, `SeanSunny/items_prompts_tv_3` (85K/3.9K/3.9K) |
| Phase 1 — Zero-shot v0 | **DONE 2026-04-26** | RMSLE=4.4428 (`02_baseline_v1.ipynb`) |
| Phase 2 — Smoke v1 | **DONE 2026-04-26** | RMSLE=0.6084 (20K/2ep/r=32/4mod) |
| Phase 3 — Full v3 | **DONE 2026-04-27** | **RMSLE=0.4426** (85K/3ep/r=64/7mod, HF: `SeanSunny/qwen3.5-4b-vn-pricer-v3`) |
| Phase 4 — Stage 1 (v4-resume) | **TODO** | Target 0.40–0.42 |
| Phase 4 — Stage 2 (augment) | **DONE 2026-04-29** | `items_prompts_tv_4` 269,112 train đã push HF |
| Phase 4 — Stage 3 (v4-scratch) | **TODO** | Target 0.36–0.40, dataset = tv_4 |
| Phase 5 — Ensemble | **DESIGN — Section 7** | Target < 0.38 |

---

## 0. Ngữ cảnh và mục tiêu

### 0.1. Bối cảnh từ Day 3 và Day 4

| Day | Best | Test RMSLE |
|-----|------|-----------|
| Day 3 | Blended TF-IDF + LGB | 0.5164 |
| Day 4 v6 Blended | PhoBERT + PCA+LGB + v4 + Day3 | 0.4187 |
| Day 4 v7 Stacked (7 models) | Ridge+EN+LGB | 0.4059 |
| **Day 4 v8 Stacked (8 models)** | **+ PhoBERT-large** | **0.4004** |

**Ceiling encoder-only + stacking ≈ 0.40.** Target 0.38 chưa đạt (gap 0.0204).

### 0.2. Giả thuyết Day 5

Decoder LLM (Qwen3.5-4B) với scale 10x PhoBERT-large + autoregressive + QLoRA → có thể phá ceiling 0.40.

### 0.3. Mục tiêu định lượng

| Mục tiêu | Ưu tiên |
|---------|---------|
| **Chính:** RMSLE < 0.40 (beat Day 4 v8 standalone) | P0 |
| **Stretch:** RMSLE < 0.38 trên full test | P1 |
| MAPE < 30% | P2 |
| R² > 0.70 | P2 |

### 0.4. Ràng buộc

- **GPU available:** RTX 5090 32GB / 1× RTX 3090 Ti 24GB / 2× RTX 3090 Ti 24GB
- **Open-source only:** Qwen3.5-4B Apache 2.0
- **Day 5 đánh giá decoder LLM thuần** (KHÔNG gộp Qwen vào v8 stacking ở phase eval)

---

## 1. Quyết định kiến trúc (đã chốt và proven qua v1+v3)

### 1.1. Model

| Thành phần | Quyết định | Trạng thái |
|-----------|-----------|-----------|
| Base model | `Qwen/Qwen3.5-4B-Base` | Proven v3 |
| Quantization | QLoRA 4-bit NF4 + double quant | Proven |
| Compute dtype | `torch_dtype=torch.bfloat16` (BẮT BUỘC trong `from_pretrained`) | Proven — không có sẽ crash conv1d ở inference |
| Framework | **PEFT + bitsandbytes + TRL 0.24** (KHÔNG Unsloth) | Unsloth dropped 2026-04-26 (lỗi VLProcessor với Hybrid arch) |
| Tokenizer | Qwen stock (vocab 151,936) | KHÔNG extend |

**Đặc điểm Qwen3.5 tokenizer:** tokenize từng chữ số riêng (digit-by-digit). `max_new_tokens=4` đủ cho completion range [5, 1000].

### 1.2. Dữ liệu hiện tại (proven qua v3)

| Thành phần | Giá trị |
|-----------|---------|
| Source | `SeanSunny/items_prompts_tv_3` |
| Train / Val / Test | 85,727 / 3,926 / 3,872 |
| Filter giá | price ≤ 1,000,000 VND (cả 3 splits) — **GIỮ cho v4** |
| Schema | `prompt`, `completion=round(price/1000)`, `price_vnd_true` |

### 1.3. Prompt format (proven)

```
Sản phẩm này có giá bao nhiêu ?
Tiêu đề: {title}
Danh mục: {category}
Thương hiệu: {brand}
Mô tả: {description}
Thông số: {features}

Giá là: 
```

**Completion:** `str(round(price / 1000))` — vd 150,000 VND → `"150"`.

### 1.4. Token profile (đã đo trên 1000 samples)

| Metric | Prompt | Full (prompt+completion) |
|--------|--------|--------------------------|
| p50 | 112 | 115 |
| p95 | 146 | 149 |
| p99 | 165 | 168 |
| max | 215 | 218 |

**Quyết định v4:** `max_seq_length = 192` (giữ như v3, truncation 0.1%) + `group_by_length=True` (tự giảm padding waste, mean=117).

### 1.5. Metric eval

- **Primary:** RMSLE (đo trên VND đầy đủ, sau unscale × 1000).
- Phụ: MAE, MAPE, R². Reuse `fine_tune_qwen/utils/evaluator.py`.

---

## 2. Kết quả các phase đã hoàn thành

### 2.1. Phase 1 — v0 zero-shot (2026-04-26)

- Notebook: `02_baseline_v1.ipynb` (BnB stack)
- RMSLE = **4.4428** | MAE = 296,807 VND | MAPE = 105.9% | R² = -2.09
- Saved: `results/v0_results.json`

### 2.2. Phase 2 — v1 smoke (2026-04-26)

- Notebook: `03_train_v1_smoke.ipynb`
- Config: r=32, 4 mod (q,k,v,o), 20K data, 2 epochs, eff_batch=64
- RMSLE = **0.6084** (epoch 2 best) | Time: 162 min | VRAM peak: 12.81 GB
- Saved: `results/v1_results.json`, `weights/v1_adapter/`
- Validate pipeline + bug fix: `torch_dtype=bfloat16`, manual `DataCollatorForCompletionOnlyLM`.

### 2.3. Phase 3 — v3 full (2026-04-27)

- Notebook: `04_train_v3.ipynb`
- Config: **r=64, alpha=128, 7 mod (q,k,v,o,gate,up,down), 85,727 data, 3 epochs, eff_batch=64, gradient_checkpointing=True**
- LR = 2e-4 cosine, warmup 0.03, weight_decay 0.001, max_grad_norm 0.3, paged_adamw_32bit
- **RMSLE epoch 1 → 2 → 3 = 0.5424 → 0.4618 → 0.4426**
- MAE = 80,100 VND | MAPE = 37.6% | R² = 0.664 | Time: 773 min (~12.9h on 3090Ti) | VRAM peak: 13.46 GB
- HF: `SeanSunny/qwen3.5-4b-vn-pricer-v3` (private)
- Weights backup: Google Drive (anh đã save ckpt e1, e2, e3)

**Insight quan trọng từ v3:**
1. **CE ↔ RMSLE divergence:** Eval CE loss đáy ở step 2600 (~giữa epoch 2) = 0.957 sau đó tăng đến 1.00 cuối epoch 3 (overfit CE). NHƯNG generative RMSLE epoch 3 (0.4426) vẫn tốt hơn epoch 2 (0.4618). → **Best ckpt phải chọn theo eval generative RMSLE, KHÔNG theo eval CE.**
2. **Diminishing returns:** Improvement e1→e2 = -15%, e2→e3 = -4.2%. Marginal value của epoch 3 thấp.
3. **Failure modes:**
   - Bỏ qua quantity trong title: `Narciso 0.6ml mini` → pred 600K vs true 60K (900% error).
   - Anchor theo category mean: tote 55K → pred 129K (134%); LEGO 999K → pred 259K (74%).
   - Under-predict price tail > 500K (rare in train).
4. **MAE v3 (80,100 VND) chỉ cao hơn v8 (79,853 VND) 0.3%** — gap RMSLE chủ yếu do outlier kéo. Fix outlier có thể beat v8.

### 2.4. So sánh v3 vs English Llama recipe (đã proven)

| Hyperparam | English Llama | v3 Qwen | Note |
|---|---|---|---|
| r / alpha / dropout | 64 / 128 / 0.1 | 64 / 128 / 0.1 | **identical** |
| target_modules | 7 (q,k,v,o,gate,up,down) | 7 | **identical** |
| LR / scheduler / warmup | 2e-4 / cosine / 0.03 | 2e-4 / cosine / 0.03 | **identical** |
| weight_decay / max_grad_norm | 0.001 / 0.3 | 0.001 / 0.3 | **identical** |
| optim | paged_adamw_32bit | paged_adamw_32bit | **identical** |
| epochs / eff_batch | 3 / 64 | 3 / 64 | **identical** |
| **Dataset** | **800K** | **85K** | **CHÊNH 10x — chính là bottleneck** |
| group_by_length | True | False | v4 BẬT |
| MAE đạt được | $39.85 (sau full 3ep) | 80,100 VND | — |

**Kết luận:** Kiến trúc + hyperparams v3 đúng theo recipe đã proven. Bottleneck duy nhất là **dataset size + balance**. Lever lớn nhất cho v4 là **data augmentation**.

---

## 3. Lessons learned & guardrails (cho Sonnet code v4)

| Lesson | Action |
|--------|--------|
| `torch_dtype=torch.bfloat16` BẮT BUỘC trong `from_pretrained` | Áp dụng mọi notebook v4 |
| `DataCollatorForCompletionOnlyLM` đã bị xóa khỏi TRL 0.24 | Dùng manual impl từ v3 |
| Chọn best ckpt theo eval generative RMSLE, KHÔNG theo eval CE | Eval RMSLE mỗi 500 steps trên 500 val |
| `val_eval_size=200` quá noisy | Tăng lên 500 cho v4 |
| `group_by_length=False` lãng phí 10-15% time | Bật True cho v4 |
| `load_best_model_at_end=True` với metric custom (eval_rmsle) | Cần custom callback |
| HF push private từ đầu | Dùng `os.environ['HF_TOKEN']`, repo `qwen3.5-4b-vn-pricer-v4-{resume,scratch}` |

---

## 4. Phase 4 — v4 Design (FOCUS CHÍNH)

### 4.1. Strategy: Plan B (proven by interview 2026-04-27)

```
Stage 1 (NGAY) ─→ v4-resume trên data CŨ (85K, NEFTune+lr nhỏ) → isolate technique impact
                  Hardware: 1× 3090 Ti 24GB
                  Time est: ~10h

Stage 2 (SONG SONG) ─→ Augment data → items_prompts_tv_4 (~255-350K)
                       Cost: ~$10-12 Groq Batch
                       Time prep: 1-2 ngày

Stage 3 (SAU stage 2) ─→ v4-scratch trên data MỚI (r=128, DoRA, RSLoRA, full SOTA)
                          Hardware: RTX 5090 32GB
                          Time est: ~16-20h

Stage 4 ─→ Ensemble v3 + v4-resume + v4-scratch + v8 (Ridge weights)
           Time: 1-2h, không cần GPU
```

### 4.2. Stage 1 — Notebook `05_train_v4_resume.ipynb`

**Mục tiêu:** Test tách biệt tác động của technique (NEFTune + LR mềm + best ckpt by RMSLE) trên cùng data v3.

**Constraint khi resume LoRA adapter:** KHÔNG thể đổi `r`, `alpha`, `target_modules`, `use_dora`, `use_rslora` (cấu trúc adapter đã fix). CÓ thể đổi: `lr`, `scheduler`, `data`, `epochs thêm`, `NEFTune`, `gradient_checkpointing`, `group_by_length`.

**Config:**

| Tham số | Giá trị | Lý do |
|--------|---------|-------|
| Resume from | v3 epoch 2 ckpt (Google Drive download) | Eval CE đáy ở epoch 2 = sweet spot, tránh "memorize" của epoch 3 |
| Dataset | `items_prompts_tv_3` (85K cũ) | Isolate technique vs data |
| Epochs thêm | 2 | Đủ test technique, total ~4 ep effective |
| LR | **5e-5** (giảm từ 2e-4) | Fine-tune mềm vì checkpoint đã warm |
| Scheduler | cosine, warmup_ratio=0.01 | Warmup ngắn hơn vì đã warm |
| **NEFTune alpha** | **3** | Nhẹ hơn vì warm start (Jain et al. 2023, alpha=5 cho 7B từ scratch) |
| LoRA dropout | 0.1 (không reload được) | — |
| group_by_length | **True** | -10-15% time |
| max_seq_length | 192 | Truncation 0.1% |
| eval_steps | 500 | Eval generative RMSLE 500 val |
| best_metric | `eval_rmsle` (custom) | CE↔RMSLE divergence |
| early_stopping | patience=3 | Auto stop khi plateau |
| per_device_batch / grad_accum | 16 / 4 (eff=64) | Giữ như v3 |
| gradient_checkpointing | True | — |
| HF push | `SeanSunny/qwen3.5-4b-vn-pricer-v4-resume` | private |

**Mục tiêu:** RMSLE 0.40-0.42. Nếu beat 0.40 → Stage 1 đã đủ; vẫn run Stage 3 để đẩy < 0.38.

### 4.3. Stage 2 — Data augmentation

**Pipeline tạo `SeanSunny/items_prompts_tv_4`:**

#### A1: Quantity-aware preprocessing (rule-based, ~10% items)

Regex detect pattern trong `Tiêu đề`:
```
\d+\s?(ml|gr|g|kg|l|gói|combo|set|box|tuýp|chai|hộp|cái|pack)
```

Nếu match → inject `[Số lượng/Khối lượng: {match}]` vào đầu `Mô tả`. Cost = 0.

**Ví dụ áp dụng:**
- Trước: `Tiêu đề: Trà lá xanh hương lá dứa Trần Quang (gói 500gr)` → `Mô tả: Trà lá xanh ướp hương lá dứa, êm nhẹ...`
- Sau: `Mô tả: [Số lượng/Khối lượng: 500gr] Trà lá xanh ướp hương lá dứa, êm nhẹ...`

Mục tiêu fix: idx 16 v3 (Narciso 0.6ml → pred 600K vs true 60K).

#### A2: LLM Paraphrase (Groq Batch `openai/gpt-oss-20b`, 2-3 versions)

**Model:** `openai/gpt-oss-20b` qua Groq Batch API (đồng bộ với pipeline day2 đã proven trên `items_raw_tv_v6 → items_tv_v6`).

Prompt LLM (input mỗi item):
```
Viết lại phần "Mô tả" và "Thông số" của sản phẩm sau bằng tiếng Việt tự nhiên,
giữ nguyên ý nghĩa, độ dài tương đương, KHÔNG thay đổi giá trị định lượng.
KHÔNG sửa Tiêu đề, Danh mục, Thương hiệu.

Trả về JSON: {"mo_ta": "...", "thong_so": "..."}

Mô tả gốc: {description}
Thông số gốc: {features}
```

- Per item × 2 versions → 85K → 255K samples (cùng giá, khác phrasing).
- **Quy trình bắt buộc:** chạy thử **10-20 sample** trước (sample manual check chất lượng paraphrase tiếng Việt + đảm bảo không thay đổi quantity), nếu OK mới submit full batch 85K × 2.
- **Cost ước tính:** ~$3-5 (gpt-oss-20b rẻ hơn 120b ~3x trên Groq Batch).
- Time: ~1 giờ batch process.

#### A4: Hard negative mining

1. Run v3 inference trên 3,926 val → save error per item.
2. Filter items có error > 50% → ~200-400 "hard examples".
3. Group theo (`category`, `price-bucket`) → identify failure regions.
4. Trong TRAIN, tìm items cùng (category, price-bucket) với hard example → augment paraphrase × 5 lần.
5. **KHÔNG add val item vào train** (data leak).
6. Output: +20-30K samples targeted.

#### A5: Price-bucket re-sampling

Bin train theo log-price: `<50K, 50-100K, 100-200K, 200-500K, 500K-1M`.

Đếm distribution thực tế (cần 1 cell trong notebook augment), sau đó set hệ số paraphrase mỗi bucket sao cho:
- Bucket peak (predicted 100-200K): paraphrase 1x
- Bucket thiếu (<50K, 500K-1M): paraphrase 4x
- Còn lại: 2x

→ 85K + ~170K augment = ~255K total, distribution gần đều.

#### A3: Brand extraction — SKIP

Brand đã có sẵn trong prompt schema (line `Thương hiệu:`), đã extract từ `items_raw_tv_v4`. Không cần thêm.

#### Notebook implement augmentation: `08_augment_dataset_v4.ipynb`

Cells:
1. Load `items_prompts_tv_3` train split (85,727)
2. Run A1 (regex injection) → output 1
3. Compute price buckets cho A5
4. Build prompts cho LLM batch (A2 + A5 hệ số) → JSONL batch file
5. Submit Groq batch job (gpt-oss-120b)
6. Poll + download results
7. Parse responses → reconstruct prompts (paraphrase versions)
8. (Optional) Run v3 inference trên val → A4 hard negative mining
9. Augment train items quanh failure regions
10. Combine + shuffle → push `SeanSunny/items_prompts_tv_4`

**Output (DONE 2026-04-29):** `SeanSunny/items_prompts_tv_4` — **269,112 train** (85,727 orig + 183,385 aug), val/test giữ nguyên từ `items_prompts_tv_3`. Script: `push_dataset_v4.py`.

### 4.4. Stage 3 — Notebook `06_train_v4_scratch.ipynb`

**Hardware: RTX 5090 32GB** (anh confirm).

**Config full SOTA:**

| Tham số | Giá trị | Lý do |
|--------|---------|-------|
| Base model | `Qwen/Qwen3.5-4B-Base` (4-bit NF4) | Proven |
| LoRA r | **128** | Capacity scaling |
| LoRA alpha | **256** (= 2r) | Standard |
| LoRA dropout | **0.15** | Tăng từ 0.1 chống overfit |
| target_modules | 7 (q,k,v,o,gate,up,down) | Proven |
| **use_dora** | **True** | +1-2% RMSLE (Liu et al. 2024) |
| **use_rslora** | **True** | Stable cho r ≥ 128 |
| **NEFTune alpha** | **5** | Standard cho 7B-class (Jain 2023) |
| LR | 2e-4 | Proven |
| Scheduler | cosine, warmup_ratio=0.03 | Proven |
| weight_decay | **0.01** (tăng từ 0.001) | Regularization mạnh hơn |
| max_grad_norm | 0.3 | Proven |
| Optim | paged_adamw_32bit | Proven |
| Epochs | **2** + EarlyStoppingCallback patience=3 | Tránh overfit ở epoch 3 |
| per_device_batch | 20 (5090 dư VRAM) | — |
| grad_accum | 4 | eff=80 |
| group_by_length | True | -10-15% time |
| max_seq_length | 192 | Proven |
| gradient_checkpointing | True | — |
| eval_steps | 500 | — |
| eval generative RMSLE | mỗi 500 steps trên 500 val | CE↔RMSLE divergence |
| save_strategy | `best` (theo eval_rmsle) | — |
| Dataset | `items_prompts_tv_4` (**269,112**) | Augment data (DONE) |
| HF push | `SeanSunny/qwen3.5-4b-vn-pricer-v4-scratch` | private |

**Time estimate (5090):** 269K × 2ep × ~1.3s/step ≈ 17-21h.

**Mục tiêu:** RMSLE **0.36-0.40**.

### 4.5. Stage 4 — Notebook `07_ensemble.ipynb`

**Mục tiêu:** Quick win. Blend v3 / v4-resume / v4-scratch / v8 (Day 4) để giảm RMSLE thêm.

**Pipeline:**
1. Load predictions của các model trên 3,926 val:
   - `v3_pred` (Qwen v3, đã có nếu run inference)
   - `v4_resume_pred`
   - `v4_scratch_pred`
   - `v8_pred` (Day 4 stacked)
2. Fit Ridge regression: `y_val = w1*log(v3) + w2*log(v4r) + w3*log(v4s) + w4*log(v8) + b`
3. Predict test set bằng cùng weights.
4. So sánh ensemble RMSLE vs từng model riêng.

**Anh đã có:** v3 weights (Google Drive), v8 weights (`day4/weights_v8/`), pipeline inference (`pricer_vi/`).

**Time:** 1-2h.

**Mục tiêu:** RMSLE **0.36-0.38** (free lunch nếu các model uncorrelated errors).

---

## 5. Risk & fallbacks

| Risk | Mitigation |
|------|-----------|
| Augment paraphrase kém chất lượng (LLM ra rác) | Sample manual 50 items kiểm tra trước khi train |
| v4-resume stuck ở local min của v3 | Nếu sau 2 ep RMSLE > 0.45 → bỏ resume, focus v4-scratch |
| 5090 không sẵn → fallback 1× 3090Ti | Giảm r=128 → r=96, batch=16, time tăng 30% |
| OOM r=128 + DoRA | Giảm batch=12, grad_accum=6 (eff=72) |
| Ensemble không cải thiện | OK — v4-scratch standalone đã đủ goal P0 |
| Groq batch downtime | Fallback OpenAI gpt-5-nano (cost ~$15-20 ở 85K x 2) |

---

## 6. Folder structure cuối Day 5

```
fine_tune_qwen/
├── plan_day5.md                           # File này
├── phase2_execution_log.md                # Run #1 (v1) + Run #2 (v3) + Run #3 (v4)
├── 02_baseline_v1.ipynb                   # Phase 1 v0 (DONE)
├── 03_train_v1_smoke.ipynb                # Phase 2 v1 (DONE)
├── 04_train_v3.ipynb                      # Phase 3 v3 (DONE)
├── 05_train_v4_resume.ipynb               # Stage 1 v4 (TODO)
├── 06_train_v4_scratch.ipynb              # Stage 3 v4 (TODO) — dataset: items_prompts_tv_4 269K
├── 07_ensemble.ipynb                      # Stage 4 (TODO)
├── 08_augment_dataset_v4.ipynb            # Stage 2 (DONE — xem push_dataset_v4.py)
├── push_dataset_v4.py                     # Stage 2 script (DONE 2026-04-29)
├── 09_eval_full.ipynb                     # Final eval all versions trên test 3,872 (TODO)
├── day5_summary.md                        # Final summary (TODO)
├── utils/
│   ├── prompt_builder.py
│   ├── evaluator.py
│   ├── inference.py
│   └── hf_upload.py
├── results/
│   ├── v0_results.json (DONE)
│   ├── v1_results.json (DONE)
│   ├── v3_results.json (DONE)
│   ├── v4_resume_results.json (TODO)
│   ├── v4_scratch_results.json (TODO)
│   └── ensemble_results.json (TODO)
├── weights/
│   ├── v1_adapter/ (DONE)
│   ├── v3_adapter/ (DONE — backup Google Drive)
│   ├── v4_resume_adapter/ (TODO)
│   └── v4_scratch_adapter/ (TODO)
└── profile_results_v3.json
```

---

## 7. Acceptance criteria

| Yêu cầu | Mức |
|---------|-----|
| v4-resume RMSLE | < 0.42 (tốt: < 0.40) |
| v4-scratch RMSLE | < 0.40 (stretch: < 0.38) |
| Ensemble RMSLE | < 0.38 (target P0+) |
| Tất cả notebook đã commit + HF push | Bắt buộc |
| `phase2_execution_log.md` có Run #3 (v4-resume) + Run #4 (v4-scratch) | Bắt buộc |
| `day5_summary.md` viết bằng tiếng Việt + bảng leaderboard final | Bắt buộc |

---

## 8. Tham chiếu code (English Llama, đã proven)

- `scraping_data_tv/Data_processing_for_English_data/fine_tune_LLM.txt` — curriculum notes
- `scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune/Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb` — full code (r=64, 7 mod, 800K data, MAE=$39.85)

---

*Cập nhật: 2026-04-29 (session 9) — Stage 2 DONE: items_prompts_tv_4 (269,112 train) pushed HF. Sẵn sàng cho Stage 1 (05_resume) + Stage 3 (06_scratch trên RTX 5090).*
