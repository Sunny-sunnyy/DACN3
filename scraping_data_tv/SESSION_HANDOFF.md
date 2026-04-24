# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-24)

**Trang thai:** Day 5 Phase 0 INFRASTRUCTURE DONE. Cho user chay notebook tren may local/Colab.
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
- [x] **Day 5 infrastructure (2026-04-24):**
  - `pyproject.toml`: da them trl, peft, bitsandbytes, accelerate, huggingface-hub
  - `fine_tune_qwen/utils/`: prompt_builder.py, evaluator.py, inference.py, hf_upload.py, __init__.py
  - `fine_tune_qwen/weights/`, `fine_tune_qwen/results/` (folders da tao)
  - `fine_tune_qwen/00_profile_tokens.ipynb`: READY — do token distribution, xuat profile_results.json
  - `fine_tune_qwen/01_prepare_dataset.ipynb`: READY — build + push SeanSunny/items_prompts_tv_1

### Buoc tiep (Day 5 — cho user chay Phase 0):
- [ ] **USER CHAY** `00_profile_tokens.ipynb` (khong can GPU — local/Colab)
  - Output can: `profile_results.json` — paste vao session moi
- [ ] **USER CHAY** `01_prepare_dataset.ipynb` (khong can GPU — can HF_TOKEN write)
  - Output can: `dataset_stats.md` — paste vao session moi
- [ ] **CONFIRM** max_seq_length va max_new_tokens (Claude confirm sau khi co profile_results.json)
- [ ] **Phase 1 (can GPU):** `02_baseline_v0.ipynb` — v0 zero-shot baseline
- [ ] **Phase 2 (can GPU):** `03_train_v1_smoke.ipynb` — v1 smoke 20K (r=32, 2ep)
- [ ] **Phase 3 (can GPU):** `04_train_v2.ipynb` — v2 full (r=64, all 7 modules, 3ep)
- [ ] **Phase 4 (can GPU):** `05_train_v3.ipynb` — v3 high-rank (r=128)
- [ ] **Phase 5 (can GPU):** `06_train_v4_final.ipynb` — v4 + NEFTune + packing
- [ ] **Phase 6:** `07_eval_full.ipynb` + day5_summary.md

**Cau hinh:** Qwen3.5-4B-Base + Unsloth + QLoRA 4-bit NF4 | GPU 24GB (thue) | 4 tuan
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

- **Checkpoint v4 keys:** `state_dict` (KHONG phai `model_state`)
- **v4-2b MLP input_size:** 1032 = 1024 (AITeamVN) + 8 (cat one-hot)
- **v4-0a DNN input_size:** 5008 = 5000 (HashingVec) + 8 (cat one-hot)
- **MLP params:** `input_size`, `hidden_sizes`, `dropout_prob` (KHONG `input_dim`/`hidden_dims`/`dropout`)
- **num_workers=0:** bat buoc Linux/WSL2
- **Stacking log-space:** feed log1p(pred) -> exp sau inference

---

## Prompt cho session moi

### Prompt G: Day 5 — Confirm Phase 0 + Tao Phase 1 notebook (can GPU)

```
Doc cac file sau de nap ngu canh (DOC KY):
1. "scraping_data_tv/SESSION_HANDOFF.md"
2. "fine_tune_qwen/plan_day5.md" (FILE QUAN TRONG NHAT)

Trang thai Day 5:
- Branch: feature/day5-qlora-qwen
- Phase 0 infrastructure DA XONG:
  - fine_tune_qwen/utils/ (prompt_builder, evaluator, inference, hf_upload)
  - fine_tune_qwen/00_profile_tokens.ipynb — DA CHAY XONG
  - fine_tune_qwen/01_prepare_dataset.ipynb — DA CHAY XONG
  - SeanSunny/items_prompts_tv_1 DA PUSH LEN HF
- Model: Qwen/Qwen3.5-4B-Base | Framework: Unsloth + TRL SFTTrainer | QLoRA 4-bit NF4
- Prompt: "San pham nay co gia bao nhieu? ... Gia la: "
- Completion train/val: round(price/1000) | Test: VND goc
- GPU thue: RTX 3090Ti/4090 24GB

Ket qua Phase 0 (user chay xong, cung cap duoi day):
[DAN KET QUA profile_results.json VAO DAY]
[DAN KET QUA dataset_stats.md VAO DAY]

Yeu cau:
1. Doc profile_results.json, confirm max_seq_length va max_new_tokens chinh thuc
2. Tao notebook fine_tune_qwen/02_baseline_v0.ipynb (Phase 1 — can GPU):
   - Load Qwen3.5-4B-Base voi Unsloth 4-bit
   - Eval zero-shot tren 500 test samples
   - Xuat v0_results.json voi RMSLE, MAE, MAPE, R2 + 20 sample predictions
   - Huong dan install unsloth tren may thue (CUDA-specific command)
3. Neu unsloth chua install duoc: fallback HF transformers + peft thuan

Luu y:
- uv run cho moi lenh Python
- Seed = 42 moi noi
- KHONG bat dau training (Phase 2+) cho den khi user confirm Phase 1 chay OK
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
| `fine_tune_qwen/plan_day5.md` | **Plan Day 5** (743 dong): plan chi tiet QLoRA Qwen3.5-4B-Base + Unsloth. 15 sections bao gom muc tieu, decisions (model/prompt/completion), Phase 0-6 chi tiet voi code template, folder structure, HF deliverables, dependencies, risks, acceptance criteria, ghi chu cho Sonnet 4.6, timeline 14 ngay. DOC KY truoc khi bat dau Day 5 implementation. |

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

*Cap nhat: 2026-04-24 (session 2) — Day 5 Phase 0 infrastructure DA XONG. Notebooks 00+01 tao xong, utils/ tao xong, deps them vao pyproject.toml. User can chay 00_profile_tokens.ipynb + 01_prepare_dataset.ipynb tren local/Colab (khong can GPU). Sau do paste ket qua vao Prompt G de Claude tao Phase 1 notebook.*
