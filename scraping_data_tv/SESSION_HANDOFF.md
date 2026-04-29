# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-29 — session 9)

**Trang thai:** Day 5 Phase 4 — Stage 2 DONE (items_prompts_tv_4 da push). Con lai: Stage 1 (05), Stage 3 (06), Stage 4 (07).
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 9 ket qua (2026-04-29)
- [x] Chay `push_dataset_v4.py` — push `SeanSunny/items_tv_v8` (183,385 train) + `SeanSunny/items_prompts_tv_4` (269,112 train).
- [x] Fix loi features mismatch (V8_FEATURES explicit schema) + fix HF upload drop connection (max_shard_size="20MB").
- [x] Tao `fine_tune_qwen/data_augmentation.md` — doc toan bo pipeline tu scraping → Day1 → Day2 → augmentation.
- [x] Stage 2 (08_augment) DONE: 85,727 orig + 183,385 aug = **269,112 train** cho items_prompts_tv_4.

### Session 8 ket qua (2026-04-28)
- [x] Tao `fine_tune_qwen/08_augment_dataset_v4.ipynb` — Stage 2 Groq Batch augmentation: merge tv6+raw_v6 → items_tv_v7, SYSTEM_PROMPT_AUG 2-dong, AugBatchManager, multiplier 5x/3x/2x/1x/4x, USER CONFIRMATION GATE, output items_prompts_tv_4.
- [x] Tao `fine_tune_qwen/06_train_v4_scratch.ipynb` — Stage 3 RTX 5090: r=128/alpha=256/DoRA/RSLoRA/NEFTune α=5/wd=0.01/eff_batch=80, best by eval_rmsle, save v4_scratch_val_predictions.json.
- [x] Tao `fine_tune_qwen/07_ensemble.ipynb` — Stage 4: Ridge log-space blend v3+v4-resume+v4-scratch+v8, graceful fallback khi thieu model, alpha grid search, test inference.
- [x] Update `fine_tune_qwen/phase2_execution_log.md` Run #4 prep.

### Session 7 ket qua (2026-04-28)
- [x] Tao `fine_tune_qwen/utils/rmsle_callback.py` — `RMSLEEvalCallback` (generative RMSLE moi 500 step, dung cho `metric_for_best_model="eval_rmsle"`).
- [x] Tao `fine_tune_qwen/05_train_v4_resume.ipynb` (22 cells) — resume tu `weights/v3_adapter/checkpoint-2680` (PeftModel.from_pretrained, is_trainable=True). LR=5e-5, NEFTune α=3, group_by_length, EarlyStop patience=3, save best by eval_rmsle.
- [x] Update plan_day5.md Section 4.3 A2: gpt-oss-120b → **gpt-oss-20b** (test 10-20 sample truoc, cost ~$3-5).
- [x] Self-review fix: transformers 5.5.0 doi `group_by_length=True` → `train_sampling_strategy="group_by_length"`.

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
- [x] **Day 5 plan_day5.md** (`fine_tune_qwen/plan_day5.md`, ~1100 dong, 15 sections + Section 4.5)
- [x] **Day 5 Phase 0 DONE (2026-04-25):**
  - `pyproject.toml`: da them trl, peft, bitsandbytes, accelerate, huggingface-hub
  - `fine_tune_qwen/utils/`: prompt_builder.py, evaluator.py, inference.py, hf_upload.py
  - Dataset `SeanSunny/items_prompts_tv_3` da push HF:
    - train: 85,727 | val: 3,926 | test: 3,872 (ca 3 splits filter price <= 1,000,000 VND)
    - Schema: `prompt`, `completion` (round(price/1000)), `price_vnd_true`
    - Prompt: `"San pham nay co gia bao nhieu ?\n{summary}\n\nGia la: "`
  - Token profile chinh xac (`fine_tune_qwen/profile_results_v3.json`):
    - Prompt p95 = 146 tokens | Full p95 = 149 tokens | Max = 218 tokens
    - **max_seq_length = 192** | **max_new_tokens = 4**
- [x] **Day 5 Phase 1 DONE (2026-04-26):** `02_baseline_v1.ipynb` (BnB) chay thanh cong.
  - RMSLE=4.4428 | MAE=296,807 VND | MAPE=105.9% | R2=-2.09 | 0.18s/item
  - Saved: `fine_tune_qwen/results/v0_results.json`
- [x] **Day 5 Phase 2 design DONE (2026-04-26):** plan_day5.md Section 4.5 — BnB-only, 8 decisions + 8 refinements.
- [x] **Day 5 Phase 2 implement DONE (2026-04-26):** `03_train_v1_smoke.ipynb` chay thanh cong.
  - Config: r=32, 4 attention modules, 20K data, 2 epochs, batch=16, grad_accum=4 (eff=64)
  - Train time: 162.4 min | VRAM peak: 12.81 GB | Truncation rate: 0.1%
  - RMSLE epoch 1: 0.6295 | RMSLE epoch 2: **0.6084** (primary)
  - MAE: 116,769 VND | MAPE: 50.4% | R2: 0.398
  - Saved: `fine_tune_qwen/results/v1_results.json`
- [x] **Day 5 Phase 3 v3 DONE (2026-04-27):** `04_train_v3.ipynb` chay thanh cong.
  - Config: r=64, alpha=128, 7 modules, 85,727 data, 3 epochs, batch=16, grad_accum=4 (eff=64), gradient_checkpointing=True
  - Train time: **773.4 min (~12.9h)** | VRAM peak: **13.46 GB** | OOM: 0
  - RMSLE per epoch: e1=0.5424 → e2=0.4618 → **e3=0.4426 (best)**
  - MAE: 80,100 VND | MAPE: 37.6% | R2: 0.664 | 0.19s/item
  - Saved: `fine_tune_qwen/results/v3_results.json` + `weights/v3_adapter/`
  - HF push: **`SeanSunny/qwen3.5-4b-vn-pricer-v3` (private)**
  - **Loss curve insight:** Eval CE loss overfit tu step 2600 (giua epoch 2), nhung generative RMSLE van cai thien e2→e3 (-4.2%). Day la **CE↔RMSLE divergence** — chon best checkpoint phai theo RMSLE, khong theo CE.
  - **Failure modes:** (1) bo qua so dinh luong trong title (mini sample 0.6ml predict 600K vs true 60K), (2) anchor theo category mean, (3) under-predict outlier price > 500K.
  - Log day du: `fine_tune_qwen/phase2_execution_log.md` Run #2

### Buoc tiep (Day 5 — can GPU/Groq):
- [x] **Phase 1 DONE** — v0 zero-shot RMSLE=4.4428
- [x] **Phase 2 DONE** — v1 smoke RMSLE=0.6084 (beat v0 86%)
- [x] **Phase 3 v3 DONE** — full 85K/3ep/r=64/7mod RMSLE=0.4426 (beat v1 27%, gap v8 +0.042, chua dat target 0.38)
- [ ] **Phase 4 Stage 1** — chay `05_train_v4_resume.ipynb` tren 1x 3090Ti (~10h) → `results/v4_resume_val_predictions.json`
- [x] **Phase 4 Stage 2 DONE (2026-04-29)** — `push_dataset_v4.py`: Groq batch 183,385 aug rows → `items_tv_v8` + `items_prompts_tv_4` (269,112 train)
- [ ] **Phase 4 Stage 3** — chay `06_train_v4_scratch.ipynb` tren RTX 5090 (~16-20h) voi `items_prompts_tv_4` → `results/v4_scratch_val_predictions.json`
- [ ] **Phase 4 Stage 4** — chay `07_ensemble.ipynb` (CPU, ~2h): Ridge blend v3+v4-resume+v4-scratch+v8
- [ ] **Phase 5 final** — `09_eval_full.ipynb` + `day5_summary.md`

**Cau hinh:** Qwen3.5-4B-Base + PEFT + bitsandbytes (QLoRA 4-bit NF4) | RTX 3090 Ti 25.3GB | 4 tuan
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

## Leaderboard tong hop (2026-04-27)

| Version | Approach | RMSLE | MAE (VND) |
|---|---|---|---|
| Day4 v8 | Stacked 8 models | **0.4004** | 79,853 |
| Day5 v3 | QLoRA Qwen3.5-4B (85K/3ep/r=64/7mod) | 0.4426 | **80,100** |
| Day5 v1 | QLoRA Qwen3.5-4B (smoke 20K/2ep/r=32/4mod) | 0.6084 | 116,769 |
| Day5 v0 | Zero-shot Qwen3.5-4B-Base | 4.4428 | 296,807 |

**Note:** v3 MAE chi cao hon v8 0.3% — gap RMSLE chu yeu do outlier (vd sample mini 0.6ml: 900% error). Fix failure mode quantity-aware co the dua v3 vuot v8.

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

### Prompt L: Day 5 — Chay v4 + ghi ket qua + summary (session moi)

```
Day 5 QLoRA Qwen3.5-4B — tat ca 4 notebook da san sang (05/08/06/07). Session nay:
1. Nap ngu canh tu `scraping_data_tv/SESSION_HANDOFF.md` va `fine_tune_qwen/phase2_execution_log.md`.
2. User se thong bao ket qua training (RMSLE, loss curve, VRAM, time) sau khi chay tung notebook xong.
3. Ghi ket qua vao `phase2_execution_log.md` (Run #3 v4-resume, Run #4 v4-scratch, ensemble).
4. Neu co loi hoac ket qua bat ngo → debug theo protocol: reproduce → root cause → 1 fix → verify.
5. Sau khi tat ca stage xong: tao `fine_tune_qwen/09_eval_full.ipynb` (eval v3/v4-resume/v4-scratch/ensemble tren test 3,872) va `fine_tune_qwen/day5_summary.md`.

== DOC NGU CANH (theo thu tu) ==
1. `scraping_data_tv/SESSION_HANDOFF.md` — trang thai tong the + leaderboard
2. `fine_tune_qwen/phase2_execution_log.md` — ket qua Run #1/2/3/4 (dien vao neu trong)
3. `fine_tune_qwen/plan_day5.md` — v4 design CANONICAL (Section 4)
4. `fine_tune_qwen/results/*.json` — ket qua da co (v3, v4-resume, v4-scratch, ensemble)

== NOTEBOOK / SCRIPT DA SAN SANG ==
- `05_train_v4_resume.ipynb` — Stage 1 (3090Ti ~10h, LR=5e-5, NEFTune α=3, resume v3 ep2)
- `push_dataset_v4.py` — Stage 2 DONE: items_tv_v8 + items_prompts_tv_4 (269,112 train) da push HF
- `06_train_v4_scratch.ipynb` — Stage 3 (5090 ~16-20h, r=128/DoRA/RSLoRA/NEFTune α=5, dataset=items_prompts_tv_4)
- `07_ensemble.ipynb` — Stage 4 (CPU, Ridge log-space v3+v4r+v4s+v8)

== KEY CONSTRAINTS ==
- KHONG sua plan_day5.md (READ-ONLY).
- KHONG chay GPU tu dong — chi code/debug, user tu chay.
- transformers 5.5.0: `dtype=torch.bfloat16`, `train_sampling_strategy="group_by_length"`.
- val/test predictions luu o `fine_tune_qwen/results/*_val_predictions.json` (dung cho 07).
- v8 test predictions: export tu `day4/day4_dl_models_v8.ipynb` theo huong dan trong 07_ensemble.ipynb Section 2c.

== TARGET ==
- v4-resume: RMSLE 0.40-0.42
- v4-scratch: RMSLE 0.36-0.40
- Ensemble: RMSLE < 0.38 (P0), < 0.36 (stretch)
- Day4 v8 ref: RMSLE=0.4004
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
| `fine_tune_qwen/plan_day5.md` | **Plan Day 5** v2.0 (~470 dong, rewrite gon 2026-04-27): plan QLoRA Qwen3.5-4B-Base + PEFT/BnB. Section 0-3 = nen tang + ket qua v0/v1/v3 + lessons. **Section 4 = v4 design CANONICAL (4 stages: resume + augment + scratch + ensemble).** DOC TRUOC KHI CODE v4. |
| `fine_tune_qwen/phase2_execution_log.md` | Log thuc thi v1 (Run #1) + v3 (Run #2) day du, gom config thuc te + loss curve + samples + failure modes + leaderboard. |

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

*Cap nhat: 2026-04-29 (session 9) — Stage 2 DONE: items_prompts_tv_4 (269,112 train) da push HF. Con lai: Stage 1 (05_resume), Stage 3 (06_scratch), Stage 4 (07_ensemble). Session sau dung Prompt L de ghi ket qua + debug + tao 09_eval_full + day5_summary.*
