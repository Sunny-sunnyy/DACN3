# Phase 2 Execution Log — v1 Smoke Training

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

## Phase 3 v2 prep log (2026-04-26)

Sau khi hoan thanh Run #1:
- Tao `04a_probe_7mod.ipynb`: 10K/1ep/r=64/7mod — do VRAM+time, quyet dinh config v2.
- Tao `04b_probe_4mod.ipynb`: 10K/1ep/r=64/4mod — doi chieu.
- Tao `04_train_v2.ipynb`: full 85K/3ep, da ap dung tat ca fix tu v1, cho ket qua probe.
- Cac fix tu v1 da dua vao tat ca notebook Phase 3+:
  1. `torch_dtype=torch.bfloat16` trong `from_pretrained` (fix conv1d crash)
  2. Manual `DataCollatorForCompletionOnlyLM` (TRL 0.24.0 da xoa class nay)
  3. Memory cleanup cells sau moi giai doan chinh
- Ket qua probe se duoc log o day sau khi chay.

---

## Cleanup history

(Khi Opus update plan dua tren execution log → archive run cu vao day, giu file gon)

(empty)
