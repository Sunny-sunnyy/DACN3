# SESSION HANDOFF — Fine-tune Qwen V2 (MAE)

**Branch:** `feature/day5-qlora-qwen`
**Folder:** `tech2ai/fine_tune_qwen_v2/`
**Ngày tạo:** 2026-05-19
**Trạng thái:** PLANNING DONE — chưa viết code, chưa train

---

## Những gì đã thực hiện trong session này

### 1. Brainstorm + Design (hoàn thành)

So sánh 3 model/kiến trúc:

| Model | Params | Languages | Proven | Verdict |
|-------|--------|-----------|--------|---------|
| **Qwen3.5-4B-Base** | 4B | 201 | **YES (v1)** | **CHỌN** |
| Qwen3-4B-Base | 4B | ~100 | No | Không cần thiết |
| Qwen2.5-3B-Base | 3B | 29 | No | Capacity yếu hơn |

**Lý do chọn Qwen3.5-4B-Base:** Pipeline đã proven 100% từ v1, không có pipeline risk mới.

### 2. Các quyết định thiết kế đã chốt

| Quyết định | Giá trị | Lý do |
|-----------|---------|-------|
| Base model | `Qwen/Qwen3.5-4B-Base` | Proven v1 |
| Dataset | `SeanSunny/items_prompts_tv_4` | 269K train, đã augment |
| **Metric chính** | **MAE** (thay RMSLE) | Bám sát English recipe |
| Completion format | `"55"` (K VND, số nguyên) | Giữ nguyên từ v1 |
| Price range | ≤ 1,000,000 VND | Giữ nguyên từ v1 |
| max_seq_length | 192 | Reuse v1 profiling (p99=168) |
| max_new_tokens | 4 | Digit-by-digit tokenizer Qwen |
| LoRA r / alpha | 64 / 128 | English recipe |
| target_modules | 7: q,k,v,o,gate,up,down | English recipe |
| LR / scheduler | 2e-4 / cosine | English recipe |
| eff_batch_size | 64 (16×4) | English recipe |
| Epochs | 3 | English recipe |
| group_by_length | True | v1 lesson |
| Best ckpt metric | **eval generative MAE** | v1 lesson (CE↔MAE diverge) |
| Val eval size | 500 samples | v1 lesson (200 quá noisy) |
| Code | Viết lại sạch 100% | Không reuse v1 code |

### 3. Evaluator design

File `utils/evaluator_vn.py` — adapted từ `Data_processing_for_English_data/Code_Fine_tune/evaluator.py`:
- **Đơn vị:** K VND (5–1000) — cùng scale với English $5–$999
- **Metrics:** MAE (primary), RMSLE, R², MSE
- **Charts:** Scatter (actual vs predicted) + Error trend với 95% CI
- **Color thresholds:** green: error < 40K VND or < 20%, orange: < 80K VND or < 40%
- Eval trên **200 test items** (seed=42)

### 4. Folder structure tạo ra

```
fine_tune_qwen_v2/
├── plan_v2.md                  ✅ DONE (995 dòng, đầy đủ code)
├── SESSION_FINE_TUNE_QWEN_V2.md ✅ File này
├── utils/                      ✅ Folder tạo (trống)
└── results/                    ✅ Folder tạo (trống)
```

---

## Trạng thái hiện tại

| Phase | Trạng thái | Ghi chú |
|-------|-----------|---------|
| Design + Planning | **DONE** | plan_v2.md commit 0fbfe5e |
| Task 1: items_vn.py | **TODO** | Code đã có trong plan_v2.md |
| Task 2: evaluator_vn.py | **TODO** | Code đã có trong plan_v2.md |
| Task 3: training_utils.py | **TODO** | Code đã có trong plan_v2.md |
| Task 4: 02_train_v2.ipynb | **TODO** | ~15-18h GPU sau khi utils xong |
| Task 5: 03_eval_v2.ipynb | **TODO** | Sau training |
| Task 6: 01_zero_shot.ipynb | **TODO (optional)** | Chạy sau khi có thời gian |

**Kết quả đạt được:** Chưa có số liệu training — session này chỉ lên kế hoạch.

**Baseline để beat:**
- v1 Qwen3.5-4B-Base (85K data): **MAE = 80,100 VND**, RMSLE = 0.4426
- Target P0: MAE < 70,000 VND
- Target P1 (stretch): MAE < 60,000 VND

---

## Kết quả training (điền sau khi chạy)

| Version | Dataset | MAE (VND) | RMSLE | R² | Ghi chú |
|---------|---------|-----------|-------|----|---------|
| v1 Qwen (baseline) | 85K | 80,100 | 0.4426 | 0.664 | 3 epochs, r=64 |
| **v2 Qwen (mục tiêu)** | **269K** | **TBD** | **TBD** | **TBD** | **3 epochs, r=64, MAE-optimized** |

---

## Prompt cho session tiếp theo

```
Đọc file: tech2ai/fine_tune_qwen_v2/SESSION_FINE_TUNE_QWEN_V2.md
và: tech2ai/fine_tune_qwen_v2/plan_v2.md

Context:
- Branch: feature/day5-qlora-qwen
- Folder làm việc: tech2ai/fine_tune_qwen_v2/
- Đây là clean-room implementation của Qwen fine-tune v2 cho bài toán dự đoán giá sản phẩm tiếng Việt
- Metric tối ưu: MAE (không phải RMSLE như v1)
- Dataset: SeanSunny/items_prompts_tv_4 (269K train, ≤1M VND)
- Model: Qwen/Qwen3.5-4B-Base

Trạng thái hiện tại: Plan DONE, chưa viết code.

Việc cần làm (theo thứ tự):
1. Implement Task 1 (utils/items_vn.py) — code đầy đủ ở plan_v2.md Task 1
2. Implement Task 2 (utils/evaluator_vn.py) — code đầy đủ ở plan_v2.md Task 2
3. Implement Task 3 (utils/training_utils.py) — code đầy đủ ở plan_v2.md Task 3
4. Tạo 02_train_v2.ipynb theo plan_v2.md Task 4 rồi chạy training

Lưu ý CRITICAL từ v1:
- torch_dtype=torch.bfloat16 BẮT BUỘC trong from_pretrained
- DataCollatorForCompletionOnlyLM đã bị xóa khỏi TRL 0.24 → dùng DataCollatorCompletionOnly (có trong training_utils.py)
- Best checkpoint chọn theo eval generative MAE, KHÔNG phải CE loss
- RESPONSE_TEMPLATE = "\nGiá là: " — cần verify tokenization đúng trong Cell 2 của notebook

Công cụ build: uv run (không dùng python3/pip)
```

---

## Critical lessons từ v1 (nhắc lại)

1. **`torch_dtype=torch.bfloat16` BẮT BUỘC** trong `AutoModelForCausalLM.from_pretrained()` — thiếu sẽ crash ở inference với lỗi conv1d
2. **DataCollatorForCompletionOnlyLM đã bị xóa** khỏi TRL 0.24 → phải dùng manual `DataCollatorCompletionOnly`
3. **CE loss ≠ MAE/RMSLE** — chọn best checkpoint bằng eval generative MAE mỗi 500 steps
4. **`group_by_length=True`** giảm 10-15% thời gian train
5. **RESPONSE_TEMPLATE = `"\nGiá là: "`** — phải verify tokenizer encode đúng trước khi train

## Tham chiếu

| File | Mục đích |
|------|---------|
| `plan_v2.md` | Implementation plan đầy đủ với code |
| `fine_tune_qwen/plan_day5.md` | V1 plan (RMSLE) — tham khảo lessons |
| `fine_tune_qwen/phase2_execution_log.md` | V1 run log |
| `Data_processing_for_English_data/Code_Fine_tune/evaluator.py` | English evaluator (template cho evaluator_vn.py) |
| `Data_processing_for_English_data/report_fine_tune_llm.md` | English recipe reference |
| `SeanSunny/items_prompts_tv_4` (HuggingFace) | Dataset: 269K train / 3.93K val / 3.87K test |
