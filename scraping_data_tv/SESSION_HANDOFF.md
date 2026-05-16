# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Prompt cho session tiep theo (copy nguyen vao chat moi)

```
Nap ngu canh tu cac file:
- scraping_data_tv/SESSION_HANDOFF.md
- Data_processing_for_Vietnamese_data/day3_v2/plan_day3_v2.md

Trang thai hien tai (2026-05-16 — session 15 da ket thuc):
- Branch: feature/day5-qlora-qwen
- Day 5 QLoRA: Run #5 (v4-scratch-v4) DONE — RMSLE=0.4608, MAE=79,589 VND, R2=62.93%
- Day 3 v2: Notebook day3_v2_baseline_ml.ipynb DA TAO XONG (Section 0-4)

NHIEM VU CHINH (session tiep theo): Chay notebook day3_v2_baseline_ml.ipynb tren may thue

NHUNG GI DA CO SAN:
- Dataset: SeanSunny/items_tv_v9 (train=269,112 | val=3,926 | test=3,872)
  Schema: title, category, brand, summary, price (round/1000 = 5-1000), price_vnd_true
- pricer_vi_2/items.py: Item dataclass + from_hub() method (da verify)
- pricer_vi_2/evaluator.py: match English — MAE/MSE/R2, hien thi "k VND", KHONG co RMSLE/MAPE
- day3_v2/day3_v2_baseline_ml.ipynb: 28 cells, Section 0-4 hoan chinh
- plan_day3_v2.md: CANONICAL — doc truoc khi code

CAU TRUC NOTEBOOK (Section 0-4 da co):
Section 0: Setup + EDA + results = {}
Section 1: Statistical baselines (random / mean / median / category_mean)
Section 2: LR simple + LR + BoW + LR + TF-IDF char_wb
Section 3: Benchmark 3 vectorizer (BoW / char_wb / Underthesea) tren 50K subset voi LGB
Section 4: RandomForest (15K) + XGBoost (full 269K) + bang so sanh tong hop

KEY CONSTRAINTS (cap nhat 2026-05-16):
- Price label: price = round(price_vnd/1000), range 5-1000. KHONG dung price_vnd_true.
- Primary metric: MAE (k VND) — KHONG dung RMSLE nua.
- KHONG dung log1p transform — train tren raw price (5-1000), giong English.
- Evaluate tren TEST set, 200 samples — giong English day3.
- Underthesea: benchmark bat buoc trong Section 3 (khong bo qua).
- KHONG dung evaluator cu (pricer_vi/) — chi dung pricer_vi_2/.

SAU KHI CHAY SECTION 0-4:
- Xem ket qua MAE cua tung model
- Quyet dinh ky thuat MAE optimization cho Section 5+ (plan_day3_v2.md Section 4 co cac option)
- Cac option: MAE loss truc tiep (LGB objective='regression_l1'), Quantile regression, Huber, Blend

CAC FILE THAM KHAO:
- Data_processing_for_English_data/Code_Data_processing/day3.ipynb — English baseline structure
- Data_processing_for_Vietnamese_data/day3_v2/plan_day3_v2.md — CANONICAL plan
- Data_processing_for_Vietnamese_data/pricer_vi_2/evaluator.py — evaluator da cap nhat

Coding guidelines:
- Truoc khi viet hoac sua bat ki doan code nao: invoke skill karpathy-guidelines
- KHONG chay GPU — Day 3 v2 chay tren CPU/RAM.
```

---

## Trang thai hien tai (2026-05-16 — session 14)

**Trang thai:** Day 3 v2 khoi dong. pricer_vi_2 (items.py + evaluator.py) da tao va verify.
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 14 ket qua (2026-05-16)

**Context:**
- Day 5 Run #5 (v4-scratch-v4) da chay xong truoc session nay: RMSLE=0.4608, MAE=79,589 VND, R2=62.93%, MAPE=32.78%, best ckpt step=4500. Ket qua luu tai fine_tune_qwen/results/v4_scratch_v4_results.json.
- Quyet dinh retrain Day 3 / Day 4 voi items_tv_v9 (269K) va price=round/1000.

**Da tao:**
- [x] `Data_processing_for_Vietnamese_data/day3_v2/plan_day3_v2.md` — plan day du cho Day 3 v2 (9 sections, 3 kien truc, acceptance criteria)
- [x] `Data_processing_for_Vietnamese_data/pricer_vi_2/__init__.py`
- [x] `Data_processing_for_Vietnamese_data/pricer_vi_2/items.py`
  - Item dataclass (price = round/1000, range 5-1000)
  - from_hub("SeanSunny/items_tv_v9") classmethod
  - Bo: weight, full, prompt (khong can cho Day 3)
  - Them: brand, price_vnd_true (optional)
- [x] `Data_processing_for_Vietnamese_data/pricer_vi_2/evaluator.py`
  - Don vi: k VND (55 = 55,000 VND)
  - color_for: error<40k OR ratio<20% → green; error<80k OR ratio<40% → orange (theo English)
  - Metrics: RMSLE (primary), MAE (k VND + VND), MSE (log-space), MAPE, R2
  - plot_predictions: color logic dung numpy vectorized voi cung threshold
  - plot_training_history: them moi (English co, pricer_vi v1 khong co)
  - Da verify: all checks passed

**Quyet dinh kien truc Day 3 v2 (da chot):**
- Price unit: round(price/1000) → range 5-1000 (align English pipeline)
- Target transform: log1p(price) train, expm1(pred) inference (mandatory cho RMSLE)
- Vectorizer chinh: TfidfVectorizer(char_wb, ngram=(2,4), 100K vocab, sublinear_tf=True)
- Underthesea: tuy chon — benchmark truoc voi 50K subset LGB default
- Model chinh: LightGBM + TruncatedSVD(200) + log-space
- Best result: Blend Ridge 30% + LGB 70% trong log-space

**3 kien truc da research va de xuat:**
1. Ridge + TF-IDF sparse — RMSLE ~0.50-0.55, <1 phut train
2. LGB + SVD(TF-IDF) + Optuna — RMSLE ~0.40-0.48, 5-15 phut train
3. Blend Ridge + LGB (log-space) — RMSLE ~0.37-0.45, +5 phut

### Buoc tiep (session tiep theo):
- [ ] Tao `day3_v2/day3_v2_baseline_ml.ipynb` (9 sections theo plan)
- [ ] Chay toan bo notebook tren CPU (khong can GPU)
- [ ] Save `day3_v2/day3_v2_results.json`
- [ ] Viet `day3_v2/day3_v2_summary.md`

---

## Trang thai hien tai (2026-05-01 — session 13)

**Trang thai:** Day 5 Phase 4 Stage 3 — SAN SANG. Notebook `06_train_v4_scratch_v4.ipynb` da tao va fix xong. KHONG dung v2 (failed), KHONG dung v3 (malformed).
**Branch hien tai:** `feature/day5-qlora-qwen`

### Session 13 ket qua (2026-05-01)

- [x] **Phan tich Root Cause v4-scratch-v2 mode collapse:**
  RSLoRA voi r=128 → scale=alpha/sqrt(r)=22.6x → gradient spike step200 (loss 1.24→4.82→2.19) → collapse ve "199".
  Chi tiet: 17/20 val samples predict "199", R2=-0.28, RMSLE=0.9739.
- [x] **Tao 06_train_v4_scratch_v4.ipynb** — clone English reference config, fix root cause:
  r=64/alpha=128/scale=2.0x, USE_DORA=False, USE_RSLORA=False, wd=0.001, 3 epochs, NEFTune=5, batch=32.
  Output: `results/v4_scratch_v4_results.json`, `results/v4_scratch_v4_val_predictions.json`.
  HF repo: `SeanSunny/qwen3.5-4b-vn-pricer-v4-scratch-v4`.
- [x] **Fix utils/evaluator.py** — `compute_metrics` tra ve `r2 * 100` (% nhu day4).
  Truoc: 0.6639 (0-1 scale). Sau: 66.39% (0-100 scale).
- [x] **Thao luan so sanh English Llama vs Vietnamese Qwen:**
  Qwen v3 R2=66.39% (200 mau) — gan ngang PhoBERT++ (64.4%). Gap Llama chu yeu la data volume (9x) + pre-training language fit.
- [x] **Thao luan Day3/Day4 retrain voi items_tv_v9 (269K)** — plan chi tiet de lai session sau.

### Session 12 ket qua (2026-04-30)

- [x] **System reset cell** — phat hien GPU RTX 5090 load 100% khi moi thue (initialization, khong phai stale process). Cell cleanup chay OK.
- [x] **Token re-profile tren 5K sample (items_prompts_tv_4):**
  - p99=191, max=262 (aug data), trunc@208=0.42% → max_seq_length=208 xac nhan hop le.
  - p99 tu profile lan 1 (SESSION_HANDOFF ghi 196) vs lan nay (191) — chech lech nho do random sample.
- [x] **Build model:** trainable params=170,643,456 (3.9%), memory footprint=5.01 GB. DoRA voi r=128 tang 10x params so v3 (15M → 170M).
- [x] **Smoke PER_DEVICE_BATCH=20:** VRAM peak=18.93 GB (PyTorch) / ~24.8 GB (vast.ai UI), 8.64s/step, est 16.1h.
- [x] **Smoke PER_DEVICE_BATCH=28 (thu nghiem):** VRAM peak=24.39 GB (PyTorch) / 30.3-31.2 GB (vast.ai UI) → chi con 0.6 GB headroom. **ABORT** — OOM risk cao cho 17h run voi group_by_length (batch dai se spike cao hon).
- [x] **Research causal-conv1d + flash-linear-attention:** SKIP — Triton bug #176426 segfault tren sm_120 (RTX 5090 Blackwell), rui ro crash giua chung.
- [x] **CHOT CONFIG:** `PER_DEVICE_BATCH=24`, eff_batch=96, est ~17h, ~$6.60. VRAM an toan ~28 GB.

**TONIGHT:** User chay `06_train_v4_scratch_v2.ipynb` voi PER_DEVICE_BATCH=24. Constants cell can doi truoc khi chay:
```python
PER_DEVICE_BATCH = 24   # DOI TU 20 (hoac 28) → 24
GRAD_ACCUM       = 4    # giu nguyen — eff_batch = 96
```

### Session 11 ket qua (2026-04-29)
- [x] DECISION: SKIP v4-resume — ensemble cuoi se la 3-model (v3 + v4-scratch + v8).
- [x] Verify chat luong aug data `SeanSunny/items_prompts_tv_4`: 0/1000 hallucination, 0/100 issue → PASS.
- [x] Re-profile token tren aug data: p99=196, max=346 → de xuat bump `max_seq_length` 192 → **208** (trunc ~0.5%).
- [x] Tao `fine_tune_qwen/06_train_v4_scratch_v2.ipynb` (31 cells, 12 sections) — KHONG sua v1:
  + Smoke VRAM cell (30 steps, abort neu peak > 30GB), rebuild model fresh truoc full train.
  + Resume detection: local `output/last-checkpoint` → fallback HF `last-checkpoint` branch (snapshot_download).
  + `hub_strategy="checkpoint"` — auto push checkpoint moi 500 step (resilient cho vast.ai disconnect).
  + 8 charts PNG post-train (matplotlib): train/eval loss, LR, grad_norm, RMSLE timeline, scatter pred vs true (200 sample), residual hist, bucket RMSLE.
  + `max_seq_length=208`, eff_batch=80, eval_steps=500, save_total_limit=2.
  + Bug fix: capture `best_ckpt_path = trainer.state.best_model_checkpoint` truoc `del trainer`.

### Session 10 ket qua (2026-04-29)
- [x] Tao va chay `push_dataset_v9.py` — push `SeanSunny/items_tv_v9`:
  - train: 85,727 orig + 183,385 aug = **269,112** (shuffle seed=42)
  - validation: 3,926 | test: 3,872 (filter price <= 1M tu v7)
  - Schema: title, category, brand, summary (merged), price (round/1000), price_vnd_true
  - Khong co cot aug_version
- [x] Day3/Day4 chi can thay doi duong dan dataset → `SeanSunny/items_tv_v9` (code khong doi)

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
- [~] **Phase 4 Stage 1 SKIP** — quyet dinh bo v4-resume (session 11). Ensemble = 3-model.
- [x] **Phase 4 Stage 2 DONE (2026-04-29)** — `push_dataset_v4.py`: Groq batch 183,385 aug rows → `items_tv_v8` + `items_prompts_tv_4` (269,112 train)
- [x] **Phase 4 Stage 3 prep DONE (2026-05-01)** — `06_train_v4_scratch_v4.ipynb` san sang (v2 FAILED, v4 = fixed)
- [ ] **Phase 4 Stage 3 RUN** — chay `06_train_v4_scratch_v4.ipynb` tren RTX 5090 32GB / vast.ai (~17-20h) → `results/v4_scratch_v4_val_predictions.json`
- [ ] **Phase 4 Stage 4** — chay `07_ensemble.ipynb` (CPU, ~2h): Ridge blend v3+v4-scratch+v8 (3-model — can verify graceful skip v4-resume)
- [ ] **Phase 5 final** — `09_eval_full.ipynb` + `day5_summary.md`

**Cau hinh:** Qwen3.5-4B-Base + PEFT + bitsandbytes (QLoRA 4-bit NF4) | RTX 3090 Ti 25.3GB | 4 tuan
**Unsloth: DROPPED 2026-04-26** (loi VLProcessor + user chot bo)
**max_seq_length = 208 (v4-scratch) | max_new_tokens = 4 | dataset = SeanSunny/items_prompts_tv_4**
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
| Day5 v4-scratch-v2 | FAILED — mode collapse (RSLoRA scale 22.6x) | 0.9739 | 175,989 |

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

*Cap nhat: 2026-05-01 (session 13) — v4-scratch-v2 FAILED (mode collapse RSLoRA). Da tao v4-scratch-v4 (fix: r=64/no-DoRA/no-RSLoRA/wd=0.001). Fix evaluator.py R2 display. Session sau: chay v4, ghi Run #5, chay 07_ensemble, tao 09_eval_full + day5_summary.*
