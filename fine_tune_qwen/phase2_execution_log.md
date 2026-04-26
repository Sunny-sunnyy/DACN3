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

## Run #1 — (chua chay)

(Sonnet dien khi chay xong)

---

## Can Opus xem xet (deviations can update plan)

- (Sonnet ghi vao day cac diem cu the can Opus update plan_day5.md hoac SESSION_HANDOFF.md)
- Vd: "R8 estimate sai — VRAM thuc te 18GB voi bs=8, plan ghi <12GB. De nghi update Section 4.5.6 R8."

---

## Cleanup history

(Khi Opus update plan dua tren execution log → archive run cu vao day, giu file gon)

(empty)
