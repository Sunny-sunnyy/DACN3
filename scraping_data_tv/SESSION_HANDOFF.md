# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-27 — session 6)

**Trang thai:** Day 5 Phase 3 v3 DONE. RMSLE=0.4426 (chua beat v8 0.4004, gap +0.042). Chuan bi v4 cai thien.
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

### Buoc tiep (Day 5 — can GPU):
- [x] **Phase 1 DONE** — v0 zero-shot RMSLE=4.4428
- [x] **Phase 2 DONE** — v1 smoke RMSLE=0.6084 (beat v0 86%)
- [x] **Phase 3 v3 DONE** — full 85K/3ep/r=64/7mod RMSLE=0.4426 (beat v1 27%, gap v8 +0.042, chua dat target 0.38)
- [ ] **Phase 4 v4 (dang thiet ke):** Cai thien sau v3 — xem section "Levers v4" trong phase2_execution_log.md
  - Top candidates: NEFTune + DoRA + dropout 0.15 + epoch 2 + early stopping + group_by_length + max_seq=160 + best ckpt theo RMSLE
  - Lever lon nhat: data augmentation (English Llama dat MAE $39 voi 800K mau, v3 chi co 85K)
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

### Prompt K: Day 5 — Phase 4 v4 implement (Sonnet 4.6, session moi)

```
BAN LA SONNET 4.6 — chuyen code generation. Opus 4.7 da chot design v4 qua interview voi user (2026-04-27).

== QUY TAC 3-FILE WORKFLOW (BAT BUOC) ==
- READ-ONLY: plan_day5.md (Section 4 v4 design), SESSION_HANDOFF.md
- WRITE: 05_train_v4_resume.ipynb, 06_train_v4_scratch.ipynb, 07_ensemble.ipynb,
         08_augment_dataset_v4.ipynb, phase2_execution_log.md (Run #3, #4),
         weights/v4_*_adapter/, results/v4_*_results.json
- Neu thay design co van de → flag vao phase2_execution_log.md muc "Can Opus xem xet", KHONG tu sua plan.

== DOC NGU CANH (theo thu tu) ==
1. "scraping_data_tv/SESSION_HANDOFF.md" — trang thai tong the (file nay)
2. "fine_tune_qwen/plan_day5.md" — DESIGN CANONICAL (rewrite v2.0, gon)
   - Section 0-3: nen tang + ket qua v0/v1/v3 + lessons learned
   - Section 4: v4 design FULL (4 stages, config day du)
3. "fine_tune_qwen/04_train_v3.ipynb" — reference style + bug fix (torch_dtype=bfloat16, manual collator)
4. "fine_tune_qwen/phase2_execution_log.md" Run #2 — chi tiet ket qua v3 + failure modes
5. "fine_tune_qwen/results/v3_results.json" — train/eval loss curves + samples
6. "scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune/Fine_tune_Llama3_2_qlora_colab_fullcode.ipynb" — English ref proven
7. "scraping_data_tv/Data_processing_for_Vietnamese_data/day2/day2_llm_preprocessing_v4.ipynb" — Groq Batch pipeline ref cho A2 augment

== TRANG THAI ==
- v3 DONE: RMSLE=0.4426 (85K/3ep/r=64/7mod) — gap v8 +0.042, chua dat target 0.38
- v3 weights backup tren Google Drive (anh da save ckpt e1, e2, e3)
- HF: SeanSunny/qwen3.5-4b-vn-pricer-v3 (private)
- Hardware available: 5090 32GB / 1x 3090Ti 24GB / 2x 3090Ti 24GB

== KEY INSIGHTS TU v3 (BAT BUOC NHO) ==
1. CE ↔ RMSLE divergence: eval CE day o step 2600 (giua ep 2) nhung RMSLE van improve e2→e3. → Best ckpt PHAI chon theo eval generative RMSLE.
2. Failure modes: (a) bo qua quantity title (Narciso 0.6ml → 600K vs 60K, 900%); (b) anchor category mean (tote 55K → 129K); (c) under-pred price tail > 500K.
3. v3 hyperparams gan identical voi English Llama recipe proven → bottleneck la DATA SIZE (85K vs 800K).
4. MAE v3 (80,100 VND) chi cao hon v8 (79,853) 0.3% → fix outlier co the beat v8.

== BUG DA FIX (BAT BUOC AP DUNG MOI NOTEBOOK) ==
- `torch_dtype=torch.bfloat16` trong AutoModelForCausalLM.from_pretrained() — neu khong co se crash conv1d Qwen3.5 GatedDeltaNet luc inference.
- DataCollatorForCompletionOnlyLM da bi xoa khoi TRL 0.24.0 → dung manual impl tu v3.
- Qwen3.5 tokenize digit-by-digit (max_new_tokens=4 du).

== YEU CAU (theo thu tu, Plan B chot tu interview) ==

STAGE 1 — Notebook 05_train_v4_resume.ipynb (UU TIEN, chay tren 1x 3090Ti)
- Load v3 epoch 2 ckpt (anh download tu Google Drive vao weights/v3_adapter_e2/)
- Train tiep 2 ep tren data CU (items_prompts_tv_3 85K)
- LR=5e-5 cosine warmup 0.01, NEFTune alpha=3, group_by_length=True, max_seq=192, eff_batch=64
- Eval generative RMSLE moi 500 step tren 500 val
- Best ckpt theo eval_rmsle (custom callback)
- EarlyStoppingCallback patience=3
- HF push: SeanSunny/qwen3.5-4b-vn-pricer-v4-resume private
- Time est: ~10h. Muc tieu RMSLE 0.40-0.42.
- Log: phase2_execution_log.md muc "Run #3 v4-resume"

STAGE 2 — Notebook 08_augment_dataset_v4.ipynb (SONG SONG voi Stage 1)
- Pipeline tu plan_day5.md Section 4.3:
  - A1: regex inject quantity vao Mo ta cho ~10% items co pattern
  - A2: Groq Batch gpt-oss-120b paraphrase Mo ta + Thong so x 2-3 versions (giu Tieu de/Danh muc/Thuong hieu/gia)
  - A4: hard negative mining tu v3 errors (chay v3 inference tren val, augment train items quanh failure regions)
  - A5: price-bucket re-sampling (paraphrase nhieu hon cho bucket thieu data)
  - A3: SKIP (brand da co san trong items_prompts_tv_3)
- Cost target: $10-15 (Groq batch ~$8/120K item)
- Output: SeanSunny/items_prompts_tv_4 train ~255-350K, val/test giu nguyen
- KHONG add val items vao train (data leak)
- Sample manual 50 items kiem tra paraphrase quality truoc khi push

STAGE 3 — Notebook 06_train_v4_scratch.ipynb (chay tren 5090 32GB)
- Train from scratch tren items_prompts_tv_4
- Config full SOTA (plan Section 4.4):
  - r=128, alpha=256, dropout=0.15, 7 mod
  - use_dora=True, use_rslora=True, NEFTune alpha=5
  - LR=2e-4 cosine warmup 0.03, weight_decay=0.01, max_grad_norm=0.3
  - Epochs=2 + EarlyStoppingCallback patience=3
  - per_device_batch=20, grad_accum=4 (eff=80) tren 5090
  - group_by_length=True, max_seq=192
  - Eval gen RMSLE moi 500 step, save best by eval_rmsle
- HF push: SeanSunny/qwen3.5-4b-vn-pricer-v4-scratch private
- Time est: ~16-20h. Muc tieu RMSLE 0.36-0.40.
- Log: phase2_execution_log.md muc "Run #4 v4-scratch"

STAGE 4 — Notebook 07_ensemble.ipynb (sau khi co v4-resume + v4-scratch)
- Load predictions cua v3 / v4-resume / v4-scratch / v8 tren 3,926 val
- Fit Ridge log-space: y_val = w1*log(v3) + w2*log(v4r) + w3*log(v4s) + w4*log(v8) + b
- Predict test (3,872) bang weights da fit
- So sanh ensemble RMSLE vs tung model
- Save: results/ensemble_results.json, output/leaderboard.md
- Muc tieu RMSLE 0.36-0.38

== TIEU CHUAN CODE ==
- uv run cho moi lenh Python, seed=42 moi noi
- Khong emoji
- Path tuong doi Path(NOTEBOOK_DIR)
- Token: os.environ['HF_TOKEN'] / os.environ['GROQ_API_KEY'] tu .env
- Style match 04_train_v3.ipynb (markdown header VN, print thay vi log)

== DEN BU TUNG STAGE ==
Sau khi tao xong moi notebook (chua chay):
- Print cell list summary
- Dry-run import check
- Confirm voi user: "Notebook OK, chay [stage]?"

KHONG bat dau training cho den khi user confirm notebook structure OK.
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

*Cap nhat: 2026-04-27 (session 6) — Phase 3 v3 DONE (RMSLE=0.4426). v4 design CHOT (Plan B: resume + augment + scratch + ensemble). Plan_day5.md rewrite v2.0 gon. San sang cho Sonnet code v4 — dung Prompt K.*
