# SESSION HANDOFF — Fine-tune Qwen V2 (MAE)

**Branch:** `feature/day5-qlora-qwen`
**Folder:** `tech2ai/fine_tune_qwen_v2/`
**Ngày tạo:** 2026-05-19
**Cập nhật cuối:** 2026-05-19 (sau khi code + thêm 00_explore.ipynb bám sát English Llama reference)
**Trạng thái:** CODE DONE — đã commit + push, chưa train

---

## Lần cập nhật mới nhất (English-faithful exploration)

Sau khi review code Qwen V2 vs English Llama 3.2 reference (`Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb`), nhận ra Qwen V2 thiếu các print/display giúp người chạy notebook quan sát dataset format, tokenizer behavior, kiến trúc model — quan trọng cho mục đích học tập. Đã bổ sung:

### Files mới/sửa

| File | Thay đổi |
|------|----------|
| **`00_explore.ipynb`** (mới) | 19 code cells + 7 markdown — bám English Sections A→E |
| **`04_eval_v2.ipynb`** (sửa) | Thêm Section F prints: footprint, `print(fine_tuned_model)`, single sample, `set_seed(42)` |

### 00_explore.ipynb — chạy trên Colab T4 16GB

| Section | Cells | Mục đích |
|---------|-------|----------|
| **A. Data exploration** | Load dataset, `len(train/val/test)`, `train[0]` dict, `test[0]` dict, `train[0]["prompt"]`, `train[1]["completion"]`, **PROMPT/COMPLETION sample** | Hiển thị schema dataset trước khi train |
| **B. Tokenizer investigation** | Load tokenizer, `investigate_tokenizer()` cho `0/1/10/100/999/1000`, token count distribution | Xác nhận empirically Qwen tokenize digit-by-digit → MAX_NEW_TOKENS=8 đủ |
| **C. Architecture & memory** | Load 32-bit base → `print(base_model)` (Linear), del + load 4-bit NF4 → `print(base_model)` (Linear4bit) | Memory footprint comparison + visual lesson Linear→Linear4bit |
| **D. Zero-shot single predict** | `model_predict(test[0])` style English | Quan sát base model leak text trước khi fine-tune |
| **E. LoRA param count** | `get_peft_model + print_trainable_parameters()` | Xác nhận ~18M trainable / 4B base ≈ 0.45% |

**Lưu ý 32-bit load:** Qwen 3.5 4B fp32 ≈ 16 GB ≥ T4 VRAM. Khi dùng `device_map="auto"`, Accelerate sẽ tự offload phần thừa qua CPU RAM (yêu cầu Colab High-RAM). Khi load 4-bit chỉ ~2.5 GB.

### 04_eval_v2.ipynb — Section F additions

| Cell mới/sửa | Nội dung |
|------|---------|
| Cell 2 | Đổi `model` → `fine_tuned_model`, in `get_memory_footprint()` thay vì `memory_allocated` |
| **Cell 3 (new)** | `print(fine_tuned_model)` — hiển thị `PeftModelForCausalLM(LoraModel(Qwen3ForCausalLM))` repr |
| **Cell 5 (new)** | Display `test_items[0]` — title / price / prompt |
| Cell 6 | Thêm `qwen_v2_predict_raw` để inspect output thô |
| **Cell 7 (new)** | Single-sample sanity check: raw output + parsed prediction + ground truth + absolute error |
| Cell 8 | Thêm `set_seed(42)` trước `tester.run()` |

---

## Tổng kết trạng thái files

```
fine_tune_qwen_v2/
├── plan_v2.md                       ✅ Plan đầy đủ (1160 dòng)
├── SESSION_FINE_TUNE_QWEN_V2.md     ✅ File này
├── utils/
│   ├── __init__.py                  ✅
│   ├── items_vn.py                  ✅ Item dataclass + load_items
│   ├── evaluator_vn.py              ✅ VnTester (MAE/RMSLE/R²/MSE + charts)
│   └── training_utils.py            ✅ BnB/LoRA/SFTConfig + DataCollatorCompletionOnly + MaeEvalCallback
├── 00_explore.ipynb                 ✅ NEW — exploration trên Colab T4 16GB
├── 01_zero_shot.ipynb               ✅ Baseline MAE 200 test items
├── 02_pilot_20k.ipynb               ✅ Pilot 20K, verify VRAM/settings
├── 03_train_v2.ipynb                ✅ Full 269K, 3 epochs, batch 32×accum 2
└── 04_eval_v2.ipynb                 ✅ Final eval + Section F prints (English-faithful)
```

---

## Commit history (branch `feature/day5-qlora-qwen`)

```
80a02b2  docs(qwen-v2): SESSION_FINE_TUNE_QWEN_V2.md — handoff
0fbfe5e  feat(qwen-v2): plan_v2.md + folder structure
60a9052  feat(qwen-v2): training_utils.py — BnB/LoRA/SFTConfig + Collator + MaeEvalCallback
d8c69ca  feat(qwen-v2): 01_zero_shot.ipynb — baseline MAE
5088534  feat(qwen-v2): 02_pilot_20k.ipynb + 03_train_v2.ipynb
e095ca6  feat(qwen-v2): 04_eval_v2.ipynb — final eval + charts
(next)   feat(qwen-v2): 00_explore.ipynb + 04_eval_v2 Section F prints
```

---

## Quyết định thiết kế đã chốt

| Quyết định | Giá trị | Lý do |
|-----------|---------|-------|
| Base model | `Qwen/Qwen3.5-4B-Base` | Proven v1 |
| Dataset | `SeanSunny/items_prompts_tv_4` | 269K train, đã augment |
| **Metric chính** | **MAE** | Bám sát English recipe |
| Completion format | `"55"` (K VND, số nguyên) | Giữ nguyên từ v1 |
| Price range | ≤ 1,000,000 VND | Giữ nguyên từ v1 |
| max_seq_length | 192 | Reuse v1 profiling (p99=168) |
| max_new_tokens | **8** (đổi từ 4) | Safety margin cho Qwen digit-by-digit + space/newline prefix |
| LoRA r / alpha | 64 / 128 | English recipe |
| target_modules | 7: q,k,v,o,gate,up,down | English recipe |
| LR / scheduler | 2e-4 / cosine | English recipe |
| eff_batch_size | **64 (32×2)** — 5090 32GB | Tăng batch, giảm accum so v1 |
| Epochs | 3 | English recipe |
| `group_by_length` | **KHÔNG truyền** | TRL 0.24 drop khỏi SFTConfig |
| Best ckpt metric | **eval generative MAE** | v1 lesson (CE↔MAE diverge) |
| Val eval size | 500 samples | v1 lesson (200 quá noisy) |
| Code | Viết lại sạch 100% | Không reuse v1 code |

---

## Execution Order (cho session sau)

```
[Pre-training exploration]
00_explore.ipynb       → chạy trên Colab T4 16GB (~5-10 phút)
                         Quan sát dataset, tokenizer, kiến trúc model

[Baseline]
01_zero_shot.ipynb     → chạy trên 5090 (~10 phút) → baseline MAE

[Verify before full]
02_pilot_20k.ipynb     → chạy trên 5090 (~35-45 phút) → verify VRAM/settings

[Full training & eval]
03_train_v2.ipynb      → chạy trên 5090 (~7-10h) → push best ckpt to HF Hub
04_eval_v2.ipynb       → chạy sau training → final charts + results JSON
```

---

## Baseline để beat

- **v1 Qwen3.5-4B-Base** (85K data): MAE = 80,100 VND, RMSLE = 0.4426
- **Target P0:** MAE < 70,000 VND
- **Target P1 (stretch):** MAE < 60,000 VND

---

## Kết quả training (điền sau khi chạy)

| Version | Dataset | MAE (VND) | RMSLE | R² | Ghi chú |
|---------|---------|-----------|-------|----|---------|
| v1 Qwen (baseline) | 85K | 80,100 | 0.4426 | 0.664 | 3 epochs, r=64 |
| **v2 Qwen (mục tiêu)** | **269K** | **TBD** | **TBD** | **TBD** | **3 epochs, r=64, MAE-optimized** |

---

## Critical lessons từ v1 (nhắc lại — đã apply vào code)

1. **`torch_dtype=torch.bfloat16` BẮT BUỘC** trong `AutoModelForCausalLM.from_pretrained()` — thiếu sẽ crash ở inference
2. **`DataCollatorForCompletionOnlyLM` đã bị xóa khỏi TRL 0.24** → đã dùng `DataCollatorCompletionOnly` manual
3. **`group_by_length` đã bị xóa khỏi SFTConfig TRL 0.24** → KHÔNG truyền arg này (collator pad longest đã đủ)
4. **CE loss ≠ MAE/RMSLE** → chọn best checkpoint bằng `MaeEvalCallback` (generate MAE mỗi 500 steps)
5. **RESPONSE_TEMPLATE = `"\nGiá là: "`** — verify tokenize đúng trong Cell 2 (đã có trong notebooks)
6. **`use_cache=False` cho gradient_checkpointing** + toggle `True` tạm thời trong callback generate (5× nhanh)
7. **Push `best_mae_checkpoint`, KHÔNG push `trainer.model`** (có thể đã overfit) — đã apply ở Cell 9 của 03_train_v2

---

## Prompt cho session tiếp theo (nếu muốn run)

```
Đọc:
- tech2ai/fine_tune_qwen_v2/SESSION_FINE_TUNE_QWEN_V2.md
- tech2ai/fine_tune_qwen_v2/plan_v2.md

Context:
- Branch: feature/day5-qlora-qwen
- Folder làm việc: tech2ai/fine_tune_qwen_v2/
- Tất cả code (utils + 5 notebooks) đã commit + push
- Metric tối ưu: MAE (không phải RMSLE như v1)
- Dataset: SeanSunny/items_prompts_tv_4 (269K train, ≤1M VND)
- Model: Qwen/Qwen3.5-4B-Base
- Hardware: RTX 5090 32GB (chính); Colab T4 16GB (cho 00_explore)

Việc cần làm:
1. Mở 00_explore.ipynb trên Colab T4 16GB, chạy tuần tự → quan sát output các cell
2. Mở 01_zero_shot.ipynb trên 5090, chạy → lấy baseline MAE
3. Mở 02_pilot_20k.ipynb trên 5090, chạy → verify VRAM/settings
4. Pass pilot → mở 03_train_v2.ipynb chạy full 269K (7-10h)
5. Sau training: mở 04_eval_v2.ipynb chạy → final charts + results JSON
6. Cập nhật bảng "Kết quả training" trong file này

Công cụ: uv run (không dùng python3/pip)
```

---

## Tham chiếu

| File | Mục đích |
|------|---------|
| `plan_v2.md` | Implementation plan đầy đủ với code (1160 dòng) |
| `fine_tune_qwen/plan_day5.md` | V1 plan (RMSLE) — tham khảo lessons |
| `fine_tune_qwen/phase2_execution_log.md` | V1 run log |
| `Data_processing_for_English_data/Code_Fine_tune/Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb` | English reference (107 cells) — template cho 00_explore + 04_eval Section F |
| `Data_processing_for_English_data/Code_Fine_tune/evaluator.py` | English evaluator (template cho `evaluator_vn.py`) |
| `Data_processing_for_English_data/report_fine_tune_llm.md` | English recipe reference |
| `SeanSunny/items_prompts_tv_4` (HuggingFace) | Dataset: 269K train / 3.93K val / 3.87K test |
