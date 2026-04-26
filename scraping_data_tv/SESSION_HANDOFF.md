# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-26 — session 5)

**Trang thai:** Day 5 Phase 2 DONE. Chuan bi Phase 3 (v2 full train). Dang chay probe 4mod/7mod de chon config.
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
  - Zero preds: 0 | Clamp trigger: 0 — pipeline validated
  - Saved: `fine_tune_qwen/results/v1_results.json`
  - Log day du: `fine_tune_qwen/phase2_execution_log.md`

### Buoc tiep (Day 5 — can GPU):
- [x] **Phase 1 DONE** — v0 zero-shot RMSLE=4.4428
- [x] **Phase 2 DONE** — v1 smoke RMSLE=0.6084 (beat v0 86%)
- [ ] **Phase 3 (dang chuan bi):** Chay probe truoc khi full train
  - `04a_probe_7mod.ipynb` — 10K, 1ep, r=64, 7 modules → do VRAM + time
  - `04b_probe_4mod.ipynb` — 10K, 1ep, r=64, 4 modules → doi chieu
  - `04_train_v2.ipynb` — full 85K, 3ep (da tao san, cho ket qua probe de chon config)
- [ ] **Phase 4 (can GPU):** `05_train_v3.ipynb` — v3 high-rank (r=128)
- [ ] **Phase 5 (can GPU):** `06_train_v4_final.ipynb` — v4 + NEFTune + packing
- [ ] **Phase 6:** `07_eval_full.ipynb` + day5_summary.md

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

### Prompt I: Day 5 — Phase 2 implement (smoke training, dung cho Sonnet 4.6)

```
BAN LA SONNET 4.6 — chuyen code generation. Opus 4.7 da chot design qua interview voi user.
Nhiem vu cua ban: code notebook theo design, log thuc thi, KHONG tu sua design.

== QUY TAC 3-FILE WORKFLOW (BAT BUOC) ==
- READ-ONLY: plan_day5.md, SESSION_HANDOFF.md
- WRITE: 03_train_v1_smoke.ipynb, phase2_execution_log.md, weights/v1_adapter/, results/v1_results.json
- Neu thay design co van de → flag vao phase2_execution_log.md muc "Can Opus xem xet", KHONG tu sua plan.

== DOC NGU CANH (theo thu tu) ==
1. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the
2. "fine_tune_qwen/plan_day5.md" Section 4.5 (toan bo 4.5.1 → 4.5.8) — DESIGN CANONICAL
3. "fine_tune_qwen/02_baseline_v1.ipynb" — reference style cho Phase 1 (BnB)
4. "scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune/Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb" — English ref
5. "fine_tune_qwen/utils/evaluator.py" — compute_metrics, plot_predictions
6. "fine_tune_qwen/phase2_execution_log.md" — template log can dien sau khi chay

== TRANG THAI ==
- Phase 1 v0 DONE: RMSLE=4.4428 zero-shot (expected) — results/v0_results.json
- Phase 2 design DONE 2026-04-26 (commit fccf94b): 8 decisions Q1-Q8 + 8 refinements R1-R8

== YEU CAU ==
1. Tao notebook fine_tune_qwen/03_train_v1_smoke.ipynb theo:
   - Section 4.5.4 code skeleton (7 phan)
   - Section 4.5.7 cell structure (~22 cell, 14 nhom)
   - Section 4.5.6 refinements R1-R8 (BAT BUOC AP DUNG)
   - Section 4.5.5 checklist 11 items
   
   Dac biet luu y:
   - PEFT + bitsandbytes 4-bit NF4 + Qwen/Qwen3.5-4B-Base (KHONG Unsloth)
   - DataCollatorForCompletionOnlyLM voi response_template = TOKEN IDS (R1) + verify mask fail-loud (R6)
   - Verify Qwen3.5 module names runtime (R2), fallback "all-linear" neu can
   - Cat SUMMARY token-level tu duoi (R7), log p50/p95/p99 + truncation rate
   - VRAM smoke 100 samples truoc khi train 20K (R8)
   - Inference safety: regex r"[-+]?\d*\.\d+|\d+" + clamp [5, 1000] (Q5)
   - Eval B+: eval_strategy="steps" CE loss + generative RMSLE 500 val sau train (Q4/Q6)
   - Push HF: SeanSunny/qwen3.5-4b-vn-pricer-v1 private (Q7)

2. KHONG chay training cho den khi user confirm notebook structure OK.

3. Sau khi chay xong → ghi log day du vao phase2_execution_log.md theo template co san:
   - Tao muc "## Run #1 — YYYY-MM-DD HH:MM"
   - Dien tat ca cac muc A → I theo template
   - Liet ke deviations va "Can Opus xem xet" neu co

== TIEU CHUAN CODE ==
- uv run cho moi lenh Python, seed=42 moi noi
- Style match 02_baseline_v1.ipynb (markdown header, comment vi/en mix, print thay vi log)
- Khong emoji
- Path tuong doi qua Path(NOTEBOOK_DIR)
- Khong hardcode API keys, dung os.environ + .env

== DEN BU ==
Sau khi tao xong notebook (chua chay), in ra:
- Cell list summary (number + title + group A-I)
- Dry-run import check
- Confirm voi user: "Notebook OK, chay full pipeline?"
```

---

### Prompt J: Day 5 — Phase 3 v2 full train (dung cho Sonnet 4.6, sau khi co ket qua probe)

```
Doc cac file sau de nap ngu canh:
1. "scraping_data_tv/SESSION_HANDOFF.md"
2. "fine_tune_qwen/plan_day5.md" Section 5 (Phase 3 v2)
3. "fine_tune_qwen/phase2_execution_log.md" (ket qua v1 + notes Opus)
4. "fine_tune_qwen/04_train_v2.ipynb" (notebook da tao san)

== TRANG THAI ==
- Phase 2 v1 smoke DONE: RMSLE=0.6084 (20K/2ep/r=32/4mod) — v1_results.json
- Phase 3 v2 notebooks da tao:
  - fine_tune_qwen/04a_probe_7mod.ipynb (10K/1ep/r=64/7mod — uoc tinh VRAM+time)
  - fine_tune_qwen/04b_probe_4mod.ipynb (10K/1ep/r=64/4mod — doi chieu)
  - fine_tune_qwen/04_train_v2.ipynb    (full 85K/3ep — cho user confirm config)

== BUG DA FIX (BAT BUOC AP DUNG) ==
- `torch_dtype=torch.bfloat16` trong `AutoModelForCausalLM.from_pretrained()` — da co san trong 04_train_v2.ipynb.
  Neu khong co dong nay: conv1d Qwen3.5 GatedDeltaNet o float32 → crash khi inference.
- `DataCollatorForCompletionOnlyLM` bi xoa khoi TRL 0.24.0 → dung manual impl (da co trong 04_train_v2.ipynb).

== CONFIG THUC TE (v1 actual, khac plan) ==
- per_device_batch=16, gradient_accumulation=4 (plan: 8/8). Eff batch = 64 giu nguyen.
- gradient_checkpointing=False trong v1 (plan: True). V2 da bat lai True trong 04_train_v2.ipynb.

== YEU CAU ==
1. Doc ket qua probe (user paste vao) de chon config 7mod hoac 4mod cho 04_train_v2.ipynb.
   Decision guide (cuoi file 04b_probe_4mod.ipynb):
   - VRAM 7mod < 23GB → dung 7mod (default trong 04_train_v2.ipynb)
   - VRAM 7mod > 23GB → sua LORA_TARGET_MODULES = 4mod trong 04_train_v2.ipynb

2. Neu user chua chay probe: phong van user de lay so lieu VRAM + time, roi quyet dinh.

3. Chay 04_train_v2.ipynb (full 85K, 3ep). Config v2:
   - r=64, alpha=128, 7mod (hoac 4mod tuy probe), gradient_checkpointing=True
   - per_device_batch=16, grad_accum=4, eff batch=64
   - EVAL_STEPS=200, SAVE_STRATEGY=epoch → 3 checkpoints

4. Sau khi chay xong:
   - Ghi log vao fine_tune_qwen/phase2_execution_log.md (muc Run #2)
   - Ghi leaderboard v0/v1/v2 vs Day4 v8

5. Cap nhat SESSION_HANDOFF.md voi v2 RMSLE thuc te.

== TIEU CHUAN CODE ==
- seed=42 moi noi, khong emoji, path tuong doi, os.environ cho token
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
