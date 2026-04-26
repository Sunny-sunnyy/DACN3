# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-26)

**Trang thai:** Day 5 Phase 1 notebooks READY. Dang chay tren may thue (RTX 3090 Ti, CUDA 12.8, PyTorch 2.9).
**Branch hien tai:** `feature/day5-qlora-qwen`

### Da hoan thanh:
- [x] Tiki scraper — 111/113 categories, 102,117 SP
- [x] Kaggle CSV -> JSONL — 41,603 SP
- [x] Hasaki scraper — 128/130 categories, 11,410 SP
- [x] WinMart scraper — 18 categories, 3,232 SP
- [x] HF dataset `SeanSunny/items_tv_v6` (120K sample)
- [x] **Day 3 DONE:** Blended TF-IDF+LGB RMSLE=0.5164
- [x] **Day 4 v4 DONE:** AITeamVN+MLP RMSLE=0.4986
- [x] **Day 4 v6 DONE:** Blended RMSLE=0.4187 (ceiling — blending bao hoa)
- [x] **Day 4 v7 DONE (2026-04-23):** Stacked (7 models) RMSLE=0.4059, gap 0.0059
- [x] **Day 4 v8 DONE (2026-04-24):** Stacked (8 models) RMSLE=0.4004, gap 0.0004
- [x] **Day 5 plan_day5.md** (`fine_tune_qwen/plan_day5.md`, 743 dong, 15 sections)
- [x] **Day 5 Phase 0 DONE (2026-04-25):**
  - `pyproject.toml`: da them trl, peft, bitsandbytes, accelerate, huggingface-hub
  - `fine_tune_qwen/utils/`: prompt_builder.py (dung cot `summary`), evaluator.py, inference.py, hf_upload.py
  - Dataset `SeanSunny/items_prompts_tv_3` da push HF:
    - train: 85,727 | val: 3,926 | test: 3,872 (ca 3 splits filter price <= 1,000,000 VND)
    - Schema: `prompt`, `completion` (round(price/1000)), `price_vnd_true`
    - Prompt: `"San pham nay co gia bao nhieu ?\n{summary}\n\nGia la: "`
  - Token profile chinh xac (`fine_tune_qwen/profile_results_v3.json`):
    - Prompt p95 = 146 tokens | Full p95 = 149 tokens | Max = 218 tokens
    - **max_seq_length = 192** | **max_new_tokens = 4**
  - Scripts: push_dataset_v3.py, reprofile_v3.py, inspect_dataset.py
- [x] **Day 5 Phase 1 notebooks READY (2026-04-26):**
  - `02_baseline_v1.ipynb` — HF transformers + BitsAndBytesConfig, `Qwen/Qwen3.5-4B-Base`, 200 samples. **Stable. CHOSEN.**
  - `02_baseline_v2.ipynb` — Unsloth `FastLanguageModel`. **DEPRECATED (user da chot bo Unsloth).**
  - Fix: transformers nang len 5.5.0 (`uv add "transformers>=5.2.0"`) — bat buoc cho Qwen3.5
  - pyproject.toml: da them `transformers>=5.2.0` (unsloth khong con dung)
- [x] **Day 5 Phase 2 design DONE (2026-04-26):**
  - Xem `fine_tune_qwen/plan_day5.md` Section 4.5 (override Section 4.2 Unsloth).
  - 8 quyet dinh chot: BnB-only, truncate summary token-level, DataCollatorForCompletionOnlyLM (token IDs),
    eval B+ (CE loss in-train + generative RMSLE 500 val sau train + manual checkpoint eval per-epoch),
    inference safety lai (regex float-first + clamp [5,1000], khong StoppingCriteria),
    eval scope 500 val only, push HF v1 adapter, report_to="none".
  - 8 refinements research: response_template token IDs (R1), verify Qwen3.5 module names runtime (R2),
    log truncation rate (R3), prepare_model_for_kbit_training order (R4), verify EOS token (R5),
    verify mask labels fail-loud (R6), truncation cat duoi reference-style + log p95/p99 (R7),
    VRAM smoke 100 samples truoc khi train 20K (R8).

### Buoc tiep (Day 5 — can GPU):
- [x] **Phase 1 DONE (2026-04-26):** `02_baseline_v1.ipynb` (BnB) chay thanh cong.
  - RMSLE=4.4428 | MAE=296,807 VND | MAPE=105.9% | R2=-2.09 | 0.18s/item
  - Zero preds: 0. Raw output kieu USD decimal ("1.00", "199.") — expected cho zero-shot Base.
  - Saved: `fine_tune_qwen/results/v0_results.json`
- [x] **Phase 2 design DONE (2026-04-26):** plan_day5.md Section 4.5 — BnB-only, 8 decisions + 5 refinements.
- [ ] **Phase 2 implement (can GPU):** `03_train_v1_smoke.ipynb` — v1 smoke 20K (r=32, 2ep), follow Section 4.5
- [ ] **Phase 3 (can GPU):** `04_train_v2.ipynb` — v2 full (r=64, all 7 modules, 3ep)
- [ ] **Phase 4 (can GPU):** `05_train_v3.ipynb` — v3 high-rank (r=128)
- [ ] **Phase 5 (can GPU):** `06_train_v4_final.ipynb` — v4 + NEFTune + packing
- [ ] **Phase 6:** `07_eval_full.ipynb` + day5_summary.md

**Cau hinh:** Qwen3.5-4B-Base + PEFT + bitsandbytes (QLoRA 4-bit NF4) | GPU 24GB (thue) | 4 tuan
**Unsloth: DROPPED 2026-04-26** (loi VLProcessor + user chot bo)
**max_seq_length = 192 | max_new_tokens = 4 | dataset = SeanSunny/items_prompts_tv_3**
**Target:** RMSLE < 0.38 (phu: beat v8 0.4004 standalone)

---

## Ket qua Day 4 (tom tat)

| Version | RMSLE | MAE | Gap vs 0.40 |
|---------|-------|-----|-------------|
| v6 Blended | 0.4187 | 82,766 | 0.0187 |
| v7 Stacked (7M) | 0.4059 | 81,776 | 0.0059 |
| **v8 Stacked (8M)** | **0.4004** | **79,853** | **0.0004** |

---

## Luu y ky thuat quan trong

### Qwen3.5-4B-Base architecture (phat hien 2026-04-26)
- `Qwen3.5-4B-Base` co Vision Encoder trong architecture (Hybrid: Gated DeltaNet + sparse MoE).
  Model type = `qwen3_5`, class = `Qwen3_5ForConditionalGeneration` — day la DUNG, khong phai bug.
- **Unsloth + `Qwen/Qwen3.5-4B-Base`** → loi VLProcessor (tokenizer bi wrap nhu image processor) + FailOnRecompileLimitHit.
- **Fix:** Dung `unsloth/Qwen3.5-4B-Base` (Unsloth repo) thay vi `Qwen/Qwen3.5-4B-Base` (HF repo).
- **Fallback:** HF transformers + BitsAndBytesConfig + `Qwen/Qwen3.5-4B-Base` — stable, cham hon 2x.
- **transformers >= 5.2.0** bat buoc (Qwen3.5 dung model type `qwen3_5` chi co tu 5.2.0+).
- Instruct model co thinking mode (`<think>...</think>`) — Base model thi KHONG co.

### Day 4 / legacy
- **Checkpoint v4 keys:** `state_dict` (KHONG phai `model_state`)
- **v4-2b MLP input_size:** 1032 = 1024 (AITeamVN) + 8 (cat one-hot)
- **v4-0a DNN input_size:** 5008 = 5000 (HashingVec) + 8 (cat one-hot)
- **MLP params:** `input_size`, `hidden_sizes`, `dropout_prob` (KHONG `input_dim`/`hidden_dims`/`dropout`)
- **num_workers=0:** bat buoc Linux/WSL2
- **Stacking log-space:** feed log1p(pred) -> exp sau inference

---

## Prompt cho session moi

### Prompt I: Day 5 — Phase 2 implement (smoke training, sau khi co design)

```
Doc cac file sau de nap ngu canh (DOC KY):
1. "scraping_data_tv/SESSION_HANDOFF.md" (trang thai hien tai)
2. "fine_tune_qwen/plan_day5.md" Section 4.5 (DESIGN CUOI BnB-only)

Trang thai Day 5:
- Phase 1 v0 RMSLE=4.4428 (zero-shot, expected) — `fine_tune_qwen/results/v0_results.json`
- Phase 2 design DONE (2026-04-26) — Section 4.5 plan_day5.md (8 decisions + 5 refinements)

Yeu cau Phase 2 — Implement smoke v1 (can GPU):
1. Tao notebook fine_tune_qwen/03_train_v1_smoke.ipynb theo Section 4.5.4 code skeleton:
   - PEFT + bitsandbytes 4-bit NF4 + Qwen/Qwen3.5-4B-Base (KHONG Unsloth)
   - 20K train samples, LoRA r=32 attention-only, 2 epochs, bs=8 grad_accum=8 (eff 64)
   - Truncate SUMMARY token-level (style English reference, KHONG cat ca prompt)
   - DataCollatorForCompletionOnlyLM voi response_template = TOKEN IDS (R1)
   - Verify Qwen3.5 module names runtime truoc khi LoRA (R2)
   - Log truncation rate (R3); verify EOS token (R5)
   - Eval B+: eval_strategy="steps" (CE loss, 500 val) trong train + generative RMSLE sau train
   - Inference safety lai: regex float-first + clamp [5, 1000]
   - Save adapter: fine_tune_qwen/weights/v1_adapter/
   - Save results: fine_tune_qwen/results/v1_results.json
   - Push HF: SeanSunny/qwen3.5-4b-vn-pricer-v1 (private)
2. KHONG chay training cho den khi user confirm notebook structure OK.

Luu y:
- uv run cho moi lenh Python, seed=42
- Tham khao English reference: scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune/
- Checklist 11 items: Section 4.5.5 plan_day5.md
```

---

### Prompt H: Day 5 — Phase 1 zero-shot baseline (can GPU)

```
Doc cac file sau de nap ngu canh (DOC KY):
1. "scraping_data_tv/SESSION_HANDOFF.md" (trang thai hien tai)
2. "fine_tune_qwen/plan_day5.md" (FILE QUAN TRONG NHAT)

Trang thai Day 5 — Phase 0 DA XONG HOAN TOAN:
- Branch: feature/day5-qlora-qwen
- Dataset: SeanSunny/items_prompts_tv_3 (train=85727, val=3926, test=3872, ca 3 filter <=1M)
- Schema: prompt (tu cot summary), completion (round(price/1000)), price_vnd_true
- max_seq_length = 192 | max_new_tokens = 4 (tu profile_results_v3.json)
- Model: Qwen/Qwen3.5-4B-Base | Framework: Unsloth + TRL SFTTrainer | QLoRA 4-bit NF4
- GPU thue: RTX 3090Ti/4090 24GB

Yeu cau:
1. Tao notebook fine_tune_qwen/02_baseline_v0.ipynb (Phase 1 — can GPU):
   - Load Qwen3.5-4B-Base voi Unsloth 4-bit (max_seq_length=192)
   - Eval zero-shot tren 500 random test samples (seed=42)
   - pred_vnd = predict(prompt) * 1000 (completion la don vi nghin dong)
   - Xuat fine_tune_qwen/results/v0_results.json: RMSLE, MAE, MAPE, R2 + 20 sample predictions
   - Huong dan install unsloth tren may thue GPU (CUDA 12.x specific)
2. Fallback neu unsloth loi: dung HF transformers + bitsandbytes (cham hon 2x nhung van OK)

Luu y:
- uv run cho moi lenh Python, seed=42 moi noi
- KHONG bat dau training (Phase 2+) cho den khi user confirm Phase 1 chay OK
- Test RMSLE se rat xau (>1.0) vi chua fine-tune — day la expected
```

---

## Files quan trong

### Plan & Summary files (doc khi can nap lai ngu canh)

| File | Noi dung |
|------|---------|
| `scraping_data_tv/SESSION_HANDOFF.md` | File nay — trang thai tong the, buoc tiep, luu y ky thuat |
| `day3/plan_day3.md` | **Plan Day 3** (230 dong): toan bo qua trinh TF-IDF baseline — 3 architecture (A/B/C), log-transform, Optuna tuning, blending. Co bang ket qua 12 models, tac dong tung ky thuat, luu y Underthesea. Doc khi can hieu pipeline TF-IDF hoac reload Day3-LGB. |
| `day3/day3_summary.md` | **Summary Day 3** (260 dong): viet bang tieng Viet co dau, giai thich khai niem (tai sao log-transform, char_wb, blending). Doc nhanh de hieu Day 3 ma khong can doc code. |
| `day4/plan_day4.md` | **Plan Day 4** (160 dong): bang tong hop v4->v8 voi so lieu thuc te, ky thuat ap dung (LLRD/R-Drop/EMA), phan tich stacking weights, fallback Day 5. Co luu y checkpoint v4 (input_size). |
| `day4/day4_summary.md` | **Summary Day 4** (270 dong): viet bang tieng Viet co dau, giai thich kien truc BERT fine-tuning, tung ky thuat SOTA (tai sao can, code minh hoa), tien trinh v4->v8, phan tich stacking, ceiling analysis, so sanh Mercari benchmark. Doc nhanh de hieu toan bo Day 4. |
| `fine_tune_qwen/plan_day5.md` | **Plan Day 5** v1.2 (~1100 dong): plan chi tiet QLoRA Qwen3.5-4B-Base + PEFT/BnB. **Section 4.5 la canonical truth cho Phase 2 (override Unsloth template cu).** 15 sections + Section 4.5 (8 decisions + 8 refinements + code skeleton + checklist). DOC KY truoc khi code Phase 2. |

### Code & weights

| File | Muc dich |
|------|----------|
| `day4/day4_dl_models_v8.ipynb` | v8 notebook (RMSLE=0.4004) |
| `day4/weights_v7/*.pth` | v7 model weights |
| `day4/weights_v8/v8_results.json` | v8 ket qua day du |
| `day4/weights_v8/stacking_config_v8.json` | v8 stacking coefs (Ridge/EN/LGB) |
| `day4/tokenized_*.pkl` | Underthesea cache (trong repo) |
| `pricer_vi/deep_neural_network.py` | DeepNeuralNetwork + MLP class |

---

*Cap nhat: 2026-04-26 (session 4) — Phase 2 DESIGN DONE (BnB-only, 8 decisions + 5 refinements, plan_day5 Section 4.5). San sang implement notebook 03_train_v1_smoke.ipynb. Dung Prompt I.*
