# Phase 2/3 Execution Log — v1 Smoke + v3 Full Train

**File ownership:** Sonnet 4.6 (write) | Opus 4.7 (read-only, dùng để cập nhật plan/handoff giữa session)

**Quy tac:**
- File nay danh cho Sonnet ghi log thuc thi notebook `03_train_v1_smoke.ipynb`.
- Sonnet KHONG sua `plan_day5.md` hoac `SESSION_HANDOFF.md`.
- Neu phat hien design issue → ghi vao muc "## Can Opus xem xet" cuoi file, KHONG tu sua plan.
- Moi run training tao 1 muc `## Run #N — YYYY-MM-DD HH:MM` moi (giu lich su).

---

## Template cho moi run (copy-paste khi bat dau)

```markdown
## Run #N — YYYY-MM-DD HH:MM

**Notebook version:** <git sha cua commit gan nhat>
**Hardware:** GPU model / VRAM total
**Python env:** uv run, torch X.X.X, transformers X.X.X, peft X.X.X, trl X.X.X

### A. Setup verification (cell 2-3)
- GPU detected: yes/no, model: ...
- VRAM total: X.X GB
- bf16 supported: yes/no
- HF login: yes/no
- EOS token: '...' (id=...)
- PAD token: '...' (id=...)

### B. Module verification + LoRA (cell 4) — R2
- Linear suffixes found: {q_proj, k_proj, v_proj, o_proj, ...}
- target_modules used: [...] hoac "all-linear"
- Trainable params: X / Y (Z%)

### C. Truncation analysis (cell 5) — R7
- Summary token len: p50=X, p95=X, p99=X, max=X
- TOKENS_FIXED (QUESTION+PREFIX): X
- MAX_SUMMARY_TOKENS derived: X
- Truncated: X / 20000 (X.X%)

### D. Mask verification (cell 7) — R1+R6
- response_template_ids: [...]
- response_template decoded back: '...'
- labels[labels != -100] decoded sample: '...'
- PASS / FAIL (neu FAIL → noi ly do, dung notebook)

### E. VRAM smoke 100 samples (cell 8) — R8
- VRAM peak: X.X GB
- Avg sec/step: X.Xs
- Estimated total train time (625 steps): X phut

### F. Full train 20K (cell 9)
- Total steps: X
- Wall-clock time: X phut
- Train loss epoch 1 end: X.XXX
- Train loss epoch 2 end: X.XXX
- Eval loss epoch 1 end: X.XXX
- Eval loss epoch 2 end: X.XXX
- Final VRAM peak: X.X GB
- OOM events: 0 / X

### G. Generative eval — final (cell 10)
- 500 val samples
- RMSLE: X.XXXX
- MAE: X,XXX VND
- MAPE: X.X%
- R2: X.XXXX
- Zero pred count: X
- Clamp triggered count: X
- Avg sec/item: X.XXs

### H. Manual checkpoint eval per-epoch (cell 11) — Q4 bonus
- Epoch 1 checkpoint: RMSLE = X.XXXX
- Epoch 2 checkpoint: RMSLE = X.XXXX
- Improvement: +/- X.XXXX

### I. Save + push (cell 12-13)
- v1_results.json saved: yes/no, path: ...
- Adapter saved: yes/no, path: ...
- HF push: yes/no, URL: ...

### Issues / Deviations from plan
- (Liet ke cac diem khong khop voi plan + ly do thay doi)
- Vd: "OOM voi bs=8 → giam xuong bs=4 + grad_accum=16 (giu eff bs=64)"

### Notes for next session
- (Vd: "Eval epoch 1 RMSLE da < 0.5 → co the giam epochs cho v2")
```

---

## Run #1 — 2026-04-26

**Notebook version:** commit f260c8b (feature/day5-qlora-qwen)
**Hardware:** NVIDIA GeForce RTX 3090 Ti / 25.3 GB VRAM
**Python env:** uv run | torch 2.9.0+cu128 | transformers 5.5.0 | peft 0.19.1 | trl 0.24.0

### A. Setup verification

- GPU detected: yes — NVIDIA GeForce RTX 3090 Ti
- VRAM total: 25.3 GB
- bf16 supported: yes (compute 8, 6)
- HF login: yes (from .env)
- EOS token: `'<|endoftext|>'` (id=248044)
- PAD token: `'<|endoftext|>'` (id=248044)

### B. Module verification + LoRA (R2)

- Linear suffixes found: `down_proj, gate_proj, in_proj_a, in_proj_b, in_proj_qkv, in_proj_z, k_proj, lm_head, o_proj, out_proj, q_proj, up_proj, v_proj`
- target_modules used: `['q_proj', 'k_proj', 'v_proj', 'o_proj']` (attention-only, PASS — 4 modules tim thay du)
- Trainable params: 6,291,456 / 4,212,042,752 (0.1494%) — trong range ky vong 0.1-0.3%

### C. Truncation analysis (R7)

- Summary token len (train 20,000): p50=98, p95=128, p99=148, max=228
- TOKENS_FIXED (QUESTION+PREFIX): 14 (q=9, p=5)
- MAX_SUMMARY_TOKENS derived: 171 (= 192 - 14 - 4 - 1 - 2)
- Truncated: 21 / 20,000 (0.1%) — rat tot, thap hon ky vong < 30% nhieu

### D. Mask verification (R1 + R6)

- response_template_ids: `[271, 185394, 36663, 25, 220]`
- decoded back: `'\n\nGia la: '` — khop PRICE_PREFIX
- labels[labels != -100] decoded (sample 0): `'420\n<|endoftext|>'`
- Non-masked count: 5 tokens (completion + \n + EOS) — PASS

### E. VRAM smoke 100 samples (R8)

- VRAM peak: 7.46 GB
- Avg sec/step: 18.68s
- Steps/epoch: 313 | Total steps (plan): 626
- Estimated total train time: 194.8 min
- VRAM OK (7.5 GB < 22 GB headroom)

### F. Full train 20K

**Deviation so voi plan:** user doi `per_device_batch=16` (thay vi 8), `gradient_accumulation=4` (thay vi 8), `gradient_checkpointing=False` (thay vi True). Effective batch = 64 giu nguyen. Ly do: toc do hop ly, VRAM con room.

- Total steps: 626 (= ceil(20000/64) * 2)
- Wall-clock time: 162.4 min (9742.5 sec)
- Train loss step 20 (start): 1.4153
- Train loss step 620 (end): 1.1068
- Eval CE loss step 100 (start): 1.2036
- Eval CE loss step 626 (end): 1.1548
- Final VRAM peak: 12.81 GB
- OOM events: 0

**Nhan xet loss curve:**
- Train loss giam deu va on dinh tu 1.415 → 1.107 (giam 21.8%), khong co diverge.
- Eval CE loss cung giam: 1.204 → 1.155 (giam 4.1%), van dang giam o cuoi epoch 2 → chua converge → v2 them data + epoch se cai thien dang ke.
- Gap train/eval loss nho (1.107 vs 1.155) → khong co dau hieu overfit.

### G. Generative eval — final epoch 2 (500 val)

- RMSLE : **0.6084** (primary)
- MAE   : 116,769 VND
- MAPE  : 50.4%
- R2    : 0.3980
- Zero pred count  : 0 (model luon generate so hop le)
- Clamp trigger    : 0 (moi prediction trong [5K, 1M] VND)
- Avg sec/item     : 0.85s

**So sanh:**
- v0 zero-shot: RMSLE=4.4428 → v1: 0.6084 — **giam 86.3%**
- Day4 v8: RMSLE=0.4004 — v1 chua beat (gap 0.208), expected voi smoke config
- Target 0.38: gap 0.228, can v2/v3 full run

**Nhan xet sample 20:**
- Tot (error < 20%): idx 2 (3.4%), idx 13 (1.0%), idx 15 (4.4%), idx 17 (13.1%), idx 19 (16.3%) — 5/20 = 25%
- Kha (error 20-60%): idx 1 (27.6%), idx 7 (30.3%), idx 8 (50.1%), idx 9 (52.6%), idx 18 (51.3%) — 5/20 = 25%
- Xau (error > 60%): 10/20 = 50% — pho bien o cac san pham gia thap (<100K) bi predict qua cao
- Model co xu huong predict trong khoang 100-500K, underestimate san pham gia cao (LEGO 999K → pred 499K) va overestimate san pham gia thap (tui tote 55K → pred 199K). Day la hieu ung underfit dien hinh khi train 20K/2ep.

### H. Manual checkpoint eval per-epoch (Q4 bonus)

- Epoch 1 checkpoint: RMSLE = 0.6295, MAE = 122,374 VND, MAPE = 50.5%
- Epoch 2 checkpoint: RMSLE = 0.6084, MAE = 116,769 VND, MAPE = 50.4%
- Improvement e1 → e2: RMSLE -0.0211 (-3.4%), MAE -5,605 VND
- Nhan xet: Van dang cai thien, chua plateau → ky vong epoch 3 trong v2 se tiep tuc giam

### I. Save + push

- v1_results.json saved: yes — `fine_tune_qwen/results/v1_results.json`
- Adapter saved: yes — `fine_tune_qwen/weights/v1_adapter/`
- HF push: pending (can confirm voi user)

### Issues / Deviations from plan

1. **[BUG — DA FIX]** RuntimeError khi inference: `expected scalar type BFloat16 but found Float` tai `Qwen3_5GatedDeltaNet.conv1d`. Root cause: `conv1d` la non-Linear layer, BnB khong quantize → weight o float32. Training dung `bf16=True` AMP nen khong lo. Inference thu cong khong co AMP → crash. Fix runtime: cast tat ca `nn.Conv1d` ve bfloat16 truoc khi goi `model.generate()`. Fix permanent: them `torch_dtype=torch.bfloat16` vao `AutoModelForCausalLM.from_pretrained()`.

2. **[DEVIATION]** `DataCollatorForCompletionOnlyLM` da bi xoa khoi TRL 0.24.0. Phai viet tay manual impl (dataclass). Impl nay hoat dong dung (mask verify PASS).

3. **[DEVIATION]** Training config thay doi: `per_device_batch=16` (plan: 8), `gradient_accumulation=4` (plan: 8), `gradient_checkpointing=False` (plan: True). Effective batch = 64 giu nguyen. Ly do: user dieu chinh truc tiep tren may thue.

4. **[INFO]** `causal-conv1d` va `flash-linear-attention` khong duoc cai dat → Qwen3.5 GatedDeltaNet dung fallback PyTorch native (cham hon). Toc do inference: 0.85s/item (chap nhan duoc cho smoke).

---

## Can Opus xem xet (deviations can update plan)

1. **[BUG FIX can dua vao plan]** Them `torch_dtype=torch.bfloat16` vao `AutoModelForCausalLM.from_pretrained()` trong tat ca notebook Phase 2+ (Section 4.5.4 code skeleton). Neu khong co dong nay, inference sau training se crash voi Qwen3.5 Hybrid (conv1d float32 vs bf16 hidden states).

2. **[DECISION can chot cho v2]** `DataCollatorForCompletionOnlyLM` da bi remove khoi TRL 0.24.0. Manual impl da viet va hoat dong tot. De nghi Opus confirm: giu manual impl hay co cach khac (vi du: SFTTrainer voi `completion_only_loss=True` param moi)?

3. **[TUNING SIGNAL cho v2]** Eval loss van dang giam o cuoi epoch 2 (1.155 vs 1.204 luc dau). Epoch improvement: RMSLE 0.6295 → 0.6084 (-0.021/epoch). Voi v2 full 85K data + 3 epochs + r=64 + 7 modules, RMSLE co the dat 0.40-0.45. De nghi giu plan v2 nhu hien tai (khong can dieu chinh).

---

## Phase 3 v3 prep log (2026-04-26)

Sau khi hoan thanh Run #1:
- Tao `04a_probe_7mod.ipynb`: 10K/1ep/r=64/7mod — do VRAM+time, quyet dinh config.
- Tao `04b_probe_4mod.ipynb`: 10K/1ep/r=64/4mod — doi chieu.
- Tao `04_train_v3.ipynb`: full 85K/3ep, da ap dung tat ca fix tu v1.
  - **User chot config 7mod truc tiep, KHONG chay probe** (probe notebook khong duoc thuc thi).
- Cac fix tu v1 da dua vao notebook v3:
  1. `torch_dtype=torch.bfloat16` trong `from_pretrained` (fix conv1d crash)
  2. Manual `DataCollatorForCompletionOnlyLM` (TRL 0.24.0 da xoa class nay)
  3. Memory cleanup cells sau moi giai doan chinh

**Note naming:** Skip ten "v2" — version chinh thuc cho full train la **v3** (notebook `04_train_v3.ipynb`, results `v3_results.json`, HF repo `qwen3.5-4b-vn-pricer-v3`).

---

## Run #2 — v3 full train — 2026-04-27

**Notebook:** `fine_tune_qwen/04_train_v3.ipynb` (commit truoc 9c19fe3)
**Hardware:** NVIDIA RTX 3090 Ti / 25.3 GB VRAM (may thue, GPU load 17-19 GB / 24 GB luc train)
**Python env:** uv run | torch 2.9.0+cu128 | transformers 5.5.0 | peft 0.19.1 | trl 0.24.0

### Config v3 (vs v1)

| Tham so | v1 smoke | v3 full |
|---|---|---|
| Data | 20,000 | **85,727** (full train split) |
| Epochs | 2 | **3** |
| LoRA r / alpha | 32 / 64 | **64 / 128** |
| LoRA dropout | 0.1 | 0.1 |
| Target modules | 4 (q,k,v,o) | **7** (q,k,v,o,gate,up,down) |
| per_device_batch / grad_accum | 16 / 4 | 16 / 4 (eff = 64) |
| gradient_checkpointing | False | **True** |
| LR / scheduler | 2e-4 / cosine | 2e-4 / cosine |
| warmup_ratio | 0.03 | 0.03 |
| weight_decay | 0.001 | 0.001 |
| max_grad_norm | 0.3 | 0.3 |
| optim | paged_adamw_32bit | paged_adamw_32bit |
| eval_steps | 200 | 200 |
| save_strategy | epoch | epoch (3 ckpt) |
| max_seq_length | 192 | 192 |
| Trainable params | 6.29M (0.149%) | ~15-18M (~0.4%) (uoc tinh tu r=64, 7mod) |

**Khac biet quan trong:** v3 = r 2x + 7 modules thay vi 4 → ~3x trainable params; full data 4.3x; +1 epoch.

### F. Full train 85K

- Total optimizer steps: **4,020** (= ceil(85727/64) * 3 = 1340 * 3)
- Wall-clock time: **773.4 phut** (~12.9 gio)
- Train loss start (step 50): 1.226
- Train loss epoch 1 end (~step 1340): 1.041
- Train loss epoch 2 end (~step 2680): 0.876
- Train loss epoch 3 end (step 4000): 0.642 (giam manh)
- Eval CE loss step 200 (start): 1.183
- Eval CE loss min: **0.957 tai step 2600** (giua epoch 2)
- Eval CE loss step 4020 (end): 1.002
- VRAM smoke: 12.96 GB | VRAM peak train: **13.46 GB** | OOM: 0

**Phan tich loss curve (QUAN TRONG):**

1. **Eval CE loss da overfit tu giua epoch 2:** min 0.957 @ step 2600, tang nguoc len 1.00 o cuoi epoch 3. Train loss tut sau (1.04 → 0.64) khien gap train/eval mo rong.
2. **Train loss step jump tai epoch 3 boundary** (step 2700: 0.83 → 2750: 0.69) — model "thuoc bai" tren training set.
3. **Generative RMSLE van cai thien e2 → e3** mac du eval CE tang. Day la **CE ↔ RMSLE divergence** — token-level CE penalize toan bo distribution, nhung greedy generation chi can top-1 dung. Model van learn duoc "next number" tot hon du confidence overall te di. **He qua: chon best checkpoint theo eval CE se sai — phai chon theo generative RMSLE.**

### G. Generative eval — final epoch 3 (200 val)

- **RMSLE: 0.4426** (primary, best epoch)
- MAE: **80,100 VND**
- MAPE: 37.6%
- R2: 0.6639
- Avg sec/item: 0.19s (gpt nhanh hon v1 0.85s do batch=1 + greedy + ngan)
- Zero pred: 0 | Clamp trigger: 0

### H. Per-epoch checkpoint eval (200 val)

| Epoch | RMSLE | MAE (VND) | MAPE | R2 |
|---|---|---|---|---|
| 1 | 0.5424 | 94,854 | 41.0% | 0.579 |
| 2 | 0.4618 | 82,440 | 38.9% | 0.642 |
| **3** | **0.4426** | **80,100** | **37.6%** | **0.664** |

Improvement e1→e2: -0.081 (-15%). e2→e3: -0.019 (-4.2%) — diminishing returns ro rang.

### I. Save + push

- v3_results.json saved: yes — `fine_tune_qwen/results/v3_results.json`
- Adapter saved: yes — `fine_tune_qwen/weights/v3_adapter/` (3 epoch checkpoints)
- HF push: **yes — `SeanSunny/qwen3.5-4b-vn-pricer-v3` (private)**

### Sample analysis (20 val samples)

- **Best (error < 10%):** idx 0 (6.7%), idx 5 (5.0%), idx 9 (9.5%), idx 15 (7.4%), idx 17 (2.5%) — 5/20 = 25%
- **Acceptable (10-30%):** idx 1 (27.6%), idx 7 (29.2%), idx 13 (20.2%), idx 10 (22.2%), idx 19 (23.3%), idx 18 (18.9%) — 6/20 = 30%
- **Poor (> 60%):** idx 16 (**900%** — Narciso 0.6ml mini → pred 600K vs true 60K, model bo qua "0.6ml"), idx 4 (200% kem nhuom), idx 11 (151% vali), idx 12 (134% tui tote), idx 3 (140% master lock), idx 8 (74% LEGO 999K under-pred 259K), idx 14 (71% combo loi loc), idx 2 (59% tui handmade)

**Failure modes pho bien:**
1. **Bo qua so dinh luong trong title** ("0.6ml", "60mlx2", "Combo 5") → over-predict cho mini sample, under-predict cho combo lon.
2. **Anchor sai theo category mean:** tui xach predict trong khoang 100-300K bat ke detail; LEGO predict tam trung bat ke do phuc tap.
3. **Outlier price tail (> 500K):** model van under-predict — distribution train co < 5% mau price > 500K.

### Issues / Deviations

1. **[OBSERVATION]** Eval CE loss overfit tu step 2600. Generative RMSLE van improve nhung diminishing returns (-4% e2→e3 vs -15% e1→e2). Nghi van epoch 3 marginal value vs train cost (+4.3 gio).
2. **[DEVIATION]** Khong chay probe (04a/04b) — user chot 7mod truc tiep. VRAM thuc te 13.46 GB << 23 GB headroom → quyet dinh dung.
3. **[CONFIG MISSING vs English ref]** Llama recipe co `group_by_length=True` (giam padding waste). v3 KHONG bat → estimate lang phi 10-15% time.
4. **[LIMITATION]** val_eval_size=200 — noisy. English ref dung 500 → tin cay hon.

### Notes for next session (v4 design candidates)

- Beat v1 dang ke (-27% RMSLE: 0.6084 → 0.4426). Chua beat Day4 v8 (gap +0.042) va chua dat target 0.38.
- **Levers cho v4 (xem section "Phan tich v3 → v4" duoi):**
  1. NEFTune alpha=5 (+1-3% generative)
  2. DoRA (`use_dora=True`) (+1-2% RMSLE tai cung r)
  3. LoRA dropout 0.1 → 0.15 (chong overfit)
  4. Epochs 3 → 2 + EarlyStoppingCallback theo eval CE (tiet kiem ~4.3h)
  5. Best checkpoint theo **generative RMSLE** chu khong eval CE (do divergence)
  6. group_by_length=True (-10-15% time)
  7. max_seq_length 192 → 160 hoac 128 (giam padding, p99 = 162)
  8. val_eval_size 200 → 500 (giam noise)
  9. Data augmentation hoac mo rong dataset (lever lon nhat — English Llama dat MAE $39 voi 800K mau)

---

## Leaderboard (cap nhat 2026-04-27)

| Version | Approach | Data | Epoch | r/mod | RMSLE | MAE (VND) | Gap vs v8 | Note |
|---|---|---|---|---|---|---|---|---|
| Day4 v8 | Stacked 8 models (BERT+TFIDF+LGB) | full | — | — | **0.4004** | 79,853 | — | SOTA hien tai |
| Target | — | — | — | — | <0.38 | — | -0.020 | Day 5 goal |
| **v3** | **QLoRA Qwen3.5-4B (full)** | **85,727** | **3** | **64/7** | **0.4426** | **80,100** | **+0.042** | **MAE da gan v8!** |
| v1 smoke | QLoRA Qwen3.5-4B (smoke) | 20,000 | 2 | 32/4 | 0.6084 | 116,769 | +0.208 | validate pipeline |
| v0 | Zero-shot Qwen3.5-4B-Base | — | 0 | — | 4.4428 | 296,807 | +4.04 | baseline |

**Diem dang chu y:** v3 MAE = 80,100 VND chi cao hon v8 MAE 79,853 VND chi 0.3% — gap RMSLE chu yeu do v3 sai nang o vai outlier (sample idx 16: 900% error keo RMSLE len). Neu fix duoc failure mode quantity-aware (mini sample, combo), v3 co the beat v8.

---

---

## Run #3 prep — v4-resume notebook (2026-04-28, session 7)

**Trang thai:** Notebook + utils SAN SANG, chua chay GPU.

### Da tao
- `fine_tune_qwen/utils/rmsle_callback.py` — `RMSLEEvalCallback(TrainerCallback)`:
  - `on_evaluate` chay generative tren val_subset (500 mau co dinh), modify `metrics["eval_rmsle"]` → Trainer dung cho `metric_for_best_model="eval_rmsle"` (`greater_is_better=False`).
  - Append entry vao `state.log_history` + restore `model.train()` mode sau eval.
  - Init: tokenizer, val_subset, max_new_tokens=4, clamp [5, 1000], scale=1000.
- `fine_tune_qwen/05_train_v4_resume.ipynb` (22 cells, uuid IDs day du):
  - Resume tu `weights/v3_adapter/checkpoint-2680` (epoch 2 v3) qua `PeftModel.from_pretrained(base_model, ckpt, is_trainable=True)` — KHONG `get_peft_model` (giu nguyen r/alpha/modules cua v3).
  - Config: LR=5e-5, warmup_ratio=0.01, NEFTune alpha=3, num_epochs=2, eval/save every 500 steps, EarlyStoppingCallback patience=3.
  - `dtype=torch.bfloat16` (transformers 5.5.0 doi `torch_dtype` → `dtype`) + conv1d cast bf16 + manual `DataCollatorForCompletionOnlyLM` (copy v3).
  - SFTTrainer + `train_sampling_strategy="group_by_length"` + `length_column_name="length"` + `load_best_model_at_end=True` + `metric_for_best_model="eval_rmsle"` + `greater_is_better=False`.
  - Final eval tren full 3,926 val + plot 200 sample random (seed=42) + push HF `SeanSunny/qwen3.5-4b-vn-pricer-v4-resume` private.

### Plan v4 update
- Section 4.3 A2: gpt-oss-120b → **gpt-oss-20b** (theo day2 ref). Test 10-20 mau truoc khi run full ~$3-5 cost.

### Self-review caught
- `group_by_length=True` removed in transformers 5.5.0 → fix bang `train_sampling_strategy="group_by_length"`. Validate qua `uv run` instantiate SFTConfig pass.

### Cho session sau (08, 06, 07)
- 08_augment_dataset_v4.ipynb (Groq Batch gpt-oss-20b, target items_prompts_tv_4 ~255-350K)
- 06_train_v4_scratch.ipynb (5090 32GB, r=128/alpha=256/DoRA/RSLoRA/NEFTune α=5)
- 07_ensemble.ipynb (Ridge log-space v3 + v4-resume + v4-scratch + v8)

---

## Run #4 prep — Stages 2/3/4 notebooks (2026-04-28, session 8)

**Trang thai:** Ba notebook SAN SANG, chua chay GPU/Groq.

### Da tao (session 8)

**`08_augment_dataset_v4.ipynb`** — Stage 2 (Groq Batch augmentation):
- Source: merge `items_raw_tv_v6` (co `full`) + `items_tv_v6` (co `summary`) → `items_tv_v7` (push HF private).
- `parse_summary()` regex: tach summary 5 dong thanh `header` (Tieu de/Danh muc/Thuong hieu) + `body` (Mo ta/Thong so).
- `SYSTEM_PROMPT_AUG`: LLM viet lai chi `body` (2 dong), dung `full` lam context, giu nguyen `header`.
- `AugBatchManager`: `custom_id = f"{item_idx}_{version}"`, Groq Batch `gpt-oss-20b`, batch 1000 items.
- Multiplier A5 theo price bucket: `<50K→5x, 50-100K→3x, 100-200K→2x, 200-500K→1x, 500K-1M→4x` (~185K requests total).
- Cell flow: single-item test → 15-sample batch + USER CONFIRMATION GATE → full submit → poll → parse → combine tv_3 + push `items_prompts_tv_4`.
- Output schema: `prompt, completion, price_vnd_true` (matching tv_3).

**`06_train_v4_scratch.ipynb`** — Stage 3 (RTX 5090, 22 cells):
- Dataset: `SeanSunny/items_prompts_tv_4` (~271K).
- LoRA scratch: `r=128, alpha=256, dropout=0.15, use_dora=True, use_rslora=True` (7 modules).
- NEFTune alpha=5, weight_decay=0.01, per_device_batch=20, grad_accum=4 (eff=80).
- Best ckpt theo `eval_rmsle` (RMSLEEvalCallback 500 val) + EarlyStop patience=3.
- Save `results/v4_scratch_val_predictions.json` (dung cho 07_ensemble).
- HF push: `SeanSunny/qwen3.5-4b-vn-pricer-v4-scratch` private.

**`07_ensemble.ipynb`** — Stage 4 (25 cells):
- Load val predictions tu JSON files (v3/v4-resume/v4-scratch/v8).
- Neu file MISSING: optional Qwen inference tu HF Hub (GPU) hoac huong dan save v8 tu Day 4.
- Alpha grid search (0.001→10) → Ridge fit trong log-space → eval val + test RMSLE.
- Graceful fallback khi v8 hoac bat ky model nao thieu.
- Save `results/ensemble_results.json` + leaderboard final.

### Thu tu chay (nguoi dung)

```
1. [GPU 3090Ti ~10h]  05_train_v4_resume.ipynb   → v4_resume_val_predictions.json
2. [Groq ~$3-5]       08_augment_dataset_v4.ipynb  → items_prompts_tv_4 HF
3. [GPU 5090 ~16-20h] 06_train_v4_scratch.ipynb   → v4_scratch_val_predictions.json
4. [CPU/GPU ~2h]      07_ensemble.ipynb            → ensemble_results.json
```

### Notes cho session sau (Run #3 v4-resume)

- Sau khi chay xong 05: dien ket qua vao muc "Run #3 — v4-resume" o day.
- Sau khi chay xong 06: dien ket qua vao muc "Run #4 — v4-scratch" o day.
- Sau khi chay xong 07: dien final leaderboard o day.

---

## Cleanup history

(Khi Opus update plan dua tren execution log → archive run cu vao day, giu file gon)

(empty)
