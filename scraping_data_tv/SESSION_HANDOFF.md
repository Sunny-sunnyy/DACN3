# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-24)

**Trang thai:** Day 4 v8 DONE (RMSLE=0.4004). Day 5 plan DA CHOT, san sang thuc thi.
**Branch hien tai:** `feature/day5-qlora-qwen` (moi tao tu `feature/data-preprocessing-vi`)

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
  - PhoBERT++(0.4322) + XLM-R++(0.4309) + AITeamVN++(0.4350) + PCA+LGB + v4-2b + v4-0a + Day3-LGB
  - Ky thuat: LLRD + R-Drop + EMA + Huber + Aux + Stacking (Ridge+EN+LGB)
- [x] **Day 4 v8 DONE (2026-04-24):** Stacked (8 models) RMSLE=0.4004, gap 0.0004
  - PhoBERT-large++(0.4228) thay the PhoBERT-base++
  - mDeBERTa bi skip (khong co trong stacking pool)
  - Ky thuat moi: PhoBERT-large(370M) + CatHeads + WeightedSampler + Transductive PCA
  - Day3-LGB va v8-PCA+LGB co negative Ridge coef — meta-learner loai tru

### Buoc tiep (Day 5 — DA CHOT PLAN):
- [x] **plan_day5.md DA TAO** (`fine_tune_qwen/plan_day5.md`, 743 dong, 15 sections)
- [x] Branch `feature/day5-qlora-qwen` DA TAO
- [x] Folder `tech2ai/fine_tune_qwen/` DA TAO
- [ ] **Phase 0:** profile token count + prepare dataset `SeanSunny/items_prompts_tv_1`
- [ ] **Phase 1:** v0 zero-shot baseline (Qwen3.5-4B-Base khong fine-tune)
- [ ] **Phase 2:** v1 smoke test 20K sample (r=32, attn-only, 2ep)
- [ ] **Phase 3:** v2 full train (r=64, all 7 modules, 3ep, full 85K)
- [ ] **Phase 4:** v3 high-rank (r=128)
- [ ] **Phase 5:** v4 final + tricks (NEFTune, packing, LR sweep)
- [ ] **Phase 6:** full eval 5 versions + day5_summary.md

**Cau hinh:** Qwen3.5-4B-Base + Unsloth + QLoRA 4-bit NF4 | GPU 24GB | 2 tuan
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

### Prompt F: Day 5 — Thuc thi plan_day5.md (QLoRA Qwen3.5-4B-Base)

```
Doc cac file sau de nap ngu canh (DOC KY):
0. "segment4/mo_ta_du_an/Project_Development_Plan.md"
1. "scraping_data_tv/SESSION_HANDOFF.md"
2. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md"
3. "fine_tune_qwen/plan_day5.md" (FILE QUAN TRONG NHAT — chi tiet toan bo Day 5)

Trang thai:
- Day 4 v8 DONE: RMSLE=0.4004 (gap 0.0004 vs 0.40, target 0.38 KHONG dat)
- Day 5 plan DA CHOT: QLoRA Qwen3.5-4B-Base + Unsloth + TRL SFTTrainer
- Branch: feature/day5-qlora-qwen (DA TAO)
- Folder: tech2ai/fine_tune_qwen/ (DA TAO)
- GPU: RTX 3090Ti/4090 24GB | Budget: 2 tuan
- Data: SeanSunny/items_tv_v6 -> build SeanSunny/items_prompts_tv_1

Quyet dinh da chot (xem plan_day5.md Section 1):
- Model: Qwen/Qwen3.5-4B-Base (KHONG Instruct — tranh thinking mode)
- Framework: Unsloth + TRL SFTTrainer, QLoRA 4-bit NF4 + double quant, bf16
- Prompt format tieng Viet: "Tieu de / Danh muc / Thuong hieu / Mo ta / Thong so / Gia la: "
- Completion: round(price / 1000) integer thuan (vd 150000 VND -> "150")
- Train/Val: round; Test: giu VND goc lam ground truth, unscale x1000 khi eval
- Eval: 500 sample moi checkpoint; full 3,872 test o cuoi moi version
- Standalone: KHONG gop vao v8 stacking pool
- Iterative v0 -> v4: zero-shot -> smoke 20K -> full r=64 -> r=128 -> tricks
- Push HF: dataset + 4 adapter + 1 merged model

Toi muon bat dau thuc thi Day 5 theo plan_day5.md.
Bat dau voi Phase 0 (Ngay 1-2): profile token + prepare dataset.
Tao cac notebook theo folder structure trong plan_day5.md Section 9.
Chay Phase 0 xong thi stop, bao cao ket qua profile, cho user confirm max_seq_length
va max_new_tokens truoc khi sang Phase 1.

Luu y:
- Dung `uv run` cho moi lenh Python
- Reuse pricer_vi/evaluator.py cho RMSLE
- Seed = 42 moi noi
- Commit moi Phase xong voi message "day5 phaseN: [desc]"
- KHONG emoji trong code/log
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

*Cap nhat: 2026-04-24 — Day 4 HOAN TAT (v8 RMSLE=0.4004). Day 5 plan DA CHOT: QLoRA Qwen3.5-4B-Base + Unsloth (xem `fine_tune_qwen/plan_day5.md`). Branch: `feature/day5-qlora-qwen`. San sang bat dau Phase 0.*
