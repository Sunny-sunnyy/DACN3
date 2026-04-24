# Session Handoff

File nay giup bat dau session moi ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-24)

**Trang thai:** v8 DA CHAY (RMSLE=0.4004, gap 0.0004 vs 0.40). Target 0.38 KHONG dat.
**Branch:** `feature/data-preprocessing-vi`

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

### Buoc tiep (Day 5):
- [ ] **Fallback: QLoRA fine-tune Qwen2.5-7B-Instruct** (decoder LLM, khac repo)
  - Ceiling encoder-only ~0.40 — can decoder scale + instruction tuning
  - GPU: A100 40GB, ~4-6h training

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

### Prompt E: Day 5 — QLoRA Qwen2.5-7B

```
Doc cac file sau de nap ngu canh:
0. "scraping_data_tv/SESSION_HANDOFF.md"
1. "scraping_data_tv/Data_processing_for_Vietnamese_data/day4/plan_day4.md"

Trang thai:
- Day 4 v8 DA CHAY: RMSLE=0.4004 (gap 0.0004 vs 0.40, target 0.38 KHONG dat)
- Ceiling encoder-only ~0.40 — can decoder LLM
- Fallback: QLoRA fine-tune Qwen2.5-7B-Instruct hoac Gemma-3-4B-IT
- Data: SeanSunny/items_tv_v6 | 8 categories | Price <= 1M VND

Toi muon bat dau Day 5 voi QLoRA approach.
Hay de xuat architecture + training plan.
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

*Cap nhat: 2026-04-24 — Day 4 HOAN TAT. Best RMSLE=0.4004 (v8 stacked). Target 0.38 chua dat. Fallback: QLoRA Qwen2.5-7B (Day 5).*
