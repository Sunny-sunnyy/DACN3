# Day 4: Deep Learning + Frontier LLM — Vietnamese Price Prediction

**Ngay:** 2026-04-15 (cap nhat: 2026-04-16)
**Trang thai:** DA CHAY XONG — KET QUA THAT VONG. Khong model nao vuot Day 3 baseline (RMSLE=0.5164). Best DL: Model 2b AITeamVN+MLP RMSLE=0.4986. Can research huong moi.
**Branch:** `feature/data-preprocessing-vi`
**Dataset:** `SeanSunny/items_tv_v6` filtered <= 1,000,000 VND
**Baseline (Day 3):** Blended RMSLE=0.5164, MAE=110K, R2=47.1% (3,872 test items)
**Target Day 4:** RMSLE <= 0.40 (CHUA DAT)

---

## 1. Muc tieu

Vuot qua gioi han TF-IDF (RMSLE ~0.52) bang 2 huong tiep can:

1. **Deep Learning (5 models):** Tu DNN don gian den PhoBERT fine-tune. So sanh bag-of-words vs dense embeddings vs Transformer.
2. **Frontier LLM (3 models):** Zero-shot inference. Khong fine-tune — chi dung kien thuc san co.

### Bang ky vong

| Model | Loai | Ky vong RMSLE |
|-------|------|---------------|
| Day 3 Blended (TF-IDF+LGB) | ML Ensemble | 0.5164 (baseline) |
| Model 0: DNN ResidualBlock | DL — bag-of-words | 0.48-0.52 |
| Model 1: PhoBERT-v2 fine-tune | DL — Transformer | **0.38-0.44** |
| Model 2: VN Embedding + MLP | DL — frozen embed | 0.42-0.48 |
| Model 3: XLM-R fine-tune | DL — multilingual | 0.40-0.46 |
| Model 4: VN Embedding + LightGBM | Hybrid DL+ML | 0.40-0.46 |
| Model 5: VN Embedding + DNN ResidualBlock | DL — frozen embed + deep | 0.42-0.48 |
| Frontier LLM (best) | Zero-shot LLM | kho du doan (VND) |

---

## 2. Du lieu

Dung lai tu Day 3, khong thay doi:

| | So luong | Chi tiet |
|---|---------|---------|
| **Dataset** | SeanSunny/items_tv_v6 | Tiki + Kaggle + Hasaki + WinMart |
| **Filter** | <= 1M VND | 77.9% data |
| **Train** | 85,727 | Training |
| **Val** | 3,926 | Validation + early stopping |
| **Test** | 3,872 | Final evaluation (chung cho tat ca models) |
| **Price range** | 4,900 — 1,000,000 VND | Mean: 301K, Median: 229K |
| **8 categories** | Thoi Trang, Dien Tu, Nha Cua, Bach Hoa, Lam Dep, Me va Be, Dien Lanh, O To |

---

## 3. Tokenizer / Vectorizer cho tieng Viet

### 3.1. 5 phuong phap

| ID | Phuong phap | Output | Dac diem | Dung cho |
|----|-------------|--------|----------|----------|
| **V1** | HashingVectorizer(5000, binary=True) | Dense 5000-dim | Stateless, nhanh, hash collision, mat ngu nghia | Model 0 (variant A) |
| **V2** | Underthesea + TF-IDF (Arch B/C) | Sparse 10K-dim → dense | Da chung minh o Day 3. Giu term-frequency | Model 0 (variant B) |
| **V3** | PhoBERT tokenizer (BPE, 64K vocab) | Token IDs | **Bat buoc** `underthesea.word_tokenize()` truoc. Subword-level | Model 1 (PhoBERT) |
| **V4** | XLM-R tokenizer (SentencePiece, 250K vocab) | Token IDs | **Khong can** Vietnamese segmenter. Multilingual | Model 3 (XLM-R) |
| **V5a** | pyvi + dangvantuan/vietnamese-embedding (frozen 768d) | Dense 768-dim | Can pyvi segment. STS Pearson 88.33 (best VN) | Model 2a, Model 4a |
| **V5b** | AITeamVN/Vietnamese_Embedding (frozen 1024d) | Dense 1024-dim | KHONG can segment. BGE-M3 backbone. Nang hon | Model 2b, Model 4b |

### 3.2. So sanh 2 Vietnamese Embedding models

| | dangvantuan/vietnamese-embedding | AITeamVN/Vietnamese_Embedding |
|---|---|---|
| **HuggingFace** | `dangvantuan/vietnamese-embedding` | `AITeamVN/Vietnamese_Embedding` |
| **Backbone** | PhoBERT (RoBERTa) | BAAI/bge-m3 (XLM-R based) |
| **Dims** | 768 | 1024 |
| **Max seq** | 512 tokens | 2048 tokens |
| **Params** | 135M (~500MB) | 568M (~2.2GB) |
| **Training data** | ViNLI-SimCSE + XNLI-vn + STSB-vn | ~300K Vietnamese triplets |
| **Word segmentation** | **Bat buoc** `pyvi.ViTokenizer.tokenize()` | **Khong can** (SentencePiece built-in) |
| **STS-Vi Pearson (dev)** | **88.33** | Khong cong bo STS |
| **Retrieval (Legal Zalo)** | Khong test | Acc@1=72.74%, MRR@10=81.81% |
| **So voi BGE-M3 baseline** | — | +27.6% Acc@1 |
| **Similarity function** | Cosine | Dot product |
| **License** | Apache 2.0 | Apache 2.0 |
| **VRAM encode 85K items** | ~2GB | ~4-5GB |

**So sanh voi cac model VN khac (STS-Vi dev):**

| Model | Pearson | Spearman | Ghi chu |
|-------|---------|----------|---------|
| **dangvantuan/vietnamese-embedding** | **88.33** | **88.20** | Best STS |
| VoVanPhuc/sup-SimCSE-VietNamese | 84.65 | 84.59 | |
| keepitreal/vietnamese-sbert | 84.51 | 84.44 | |
| bkai-foundation-models/vietnamese-bi-encoder | 78.05 | 77.94 | |

**Viblo benchmark 2025 (bai khac, khong test 2 model tren):**

| Model | STS Accuracy | MRR@10 | Speed (sent/s) |
|-------|-------------|--------|----------------|
| bge-vi-base | 0.88 | 0.84 | 950 |
| sBERT-Vi | 0.86 | 0.81 | 1,100 |
| PhoBERT | 0.82 | 0.77 | 1,200 |
| ViEmbedding (fastText) | 0.74 | 0.69 | 2,200 |

### 3.3. Nhan xet

- **V1/V2:** Bag-of-words — mat ngu nghia va thu tu tu. Gioi han RMSLE ~0.50
- **V3/V4:** Subword tokenizer cua Transformer — giu ngu nghia, hoc context. Ky vong vuot bag-of-words
- **V5a/V5b:** Dense embedding — giu ca ngu nghia lan ngu canh, nhung frozen (khong adapt theo task)
- **dangvantuan** (V5a): Nhe hon, STS tot hon, nhung can pyvi segment
- **AITeamVN** (V5b): Nang hon (4x params), max seq dai hon (2048), khong can segment, backbone BGE-M3 manh

### 3.4. Vietnamese word segmentation

| Tool | Mo ta | Do chinh xac | Ghi chu |
|------|-------|-------------|---------|
| **underthesea** | Python-native, da cai san | ~80% | Dung cho V2, V3. KHONG thread-safe — pre-tokenize + cache |
| **pyvi** | Lightweight, nhanh | ~75% | Dung cho V5a (dangvantuan yeu cau pyvi). Backup cho V2/V3 |
| **VnCoreNLP (RDRSegmenter)** | Java wrapper, gold standard | ~85% | Chinh xac hon nhung can Java. Khong uu tien |
| *Khong can* | — | — | V4 (XLM-R), V5b (AITeamVN) — built-in tokenizer |

**Quyet dinh:** Dung `underthesea` cho V2/V3 (da setup tu Day 3). Dung `pyvi` cho V5a (dangvantuan yeu cau). V4/V5b khong can segment.

---

## 4. Phan A: 5 Deep Learning Models

### Model 0: DNN ResidualBlock (baseline DL — tu khoa hoc tieng Anh)

**Kien truc:**
```
Input (summary text)
  -> Vectorizer (V1 hoac V2)
  -> InputLayer(input_dim -> hidden_size) -> LayerNorm -> ReLU -> Dropout
  -> ResidualBlock x (num_layers - 2)
  -> OutputLayer(hidden_size -> 1)
  -> Inverse transform -> VND
```

**ResidualBlock:**
```
Input -> Linear -> LayerNorm -> ReLU -> Dropout -> Linear -> LayerNorm -> (+Input) -> ReLU
```

**Cau hinh — 2 buoc:**

| Tham so | Buoc 1 (nho) | Buoc 2 (lon) |
|---------|-------------|-------------|
| hidden_size | **2048** | **4096** |
| num_layers | 10 | 10 |
| Params uoc tinh | **~73M** | **~289M** |
| VRAM | ~4-6GB | ~8-12GB |

> **Quy trinh:** Chay hidden=2048 truoc. Neu ket qua tot → tang len 4096 so sanh. Neu 2048 da overfitting → khong can tang.

**Vectorizer — 2 phuong an:**

| | V1: HashingVectorizer | V2: Underthesea + TF-IDF |
|---|---|---|
| Input dim | 5,000 (dense) | 10,000 (sparse → dense) |
| Pro | Don gian, stateless | Da chung minh o Day 3 |
| Con | Hash collision, mat ngu nghia | Sparse→dense ton RAM (~3.2GB cho 85K x 10K float32) |

> **Quy trinh:** Chay ca V1 va V2 voi hidden=2048 → so sanh → chon tot hon cho hidden=4096.

**Tong: 4 experiments cho Model 0:**
1. V1 + hidden=2048
2. V2 + hidden=2048
3. (Vectorizer tot hon) + hidden=4096
4. (Optional) Vectorizer con lai + hidden=4096

**Cau hinh chung:**

| Tham so | Gia tri |
|---------|---------|
| dropout | 0.2 |
| batch_size | 64 |
| epochs | 5 |
| optimizer | AdamW(lr=0.001, weight_decay=0.01) |
| loss | L1Loss (MAE) tren normalized target |
| target transform | log(price+1) → normalize(mean, std) |
| scheduler | CosineAnnealingLR(T_max=10) |
| gradient clipping | max_norm=1.0 |

**Thay doi so voi English version:**

| | English | Vietnamese |
|---|---------|------------|
| Ngon ngu | English summaries | Vietnamese summaries |
| HashingVectorizer | stop_words="english" | stop_words=None |
| Dataset size | 800K items | 85K items |
| Price unit | USD ($0 - $999) | VND (4,900 - 1,000,000) |
| Evaluator | MAE ($) | RMSLE + MAE + MAPE + R2 |
| Hidden size | 4096 only | 2048 → 4096 (tung buoc) |

**Ky vong:** RMSLE ~0.48-0.52 (canh tranh Day 3, kho vuot xa vi van la bag-of-words)

---

### Model 1: PhoBERT-base-v2 Fine-tune (ky vong tot nhat)

| | Chi tiet |
|---|---------|
| **HuggingFace** | `vinai/phobert-base-v2` |
| **Kien truc** | RoBERTa encoder (12 layers, 768 hidden) + Linear regression head (num_labels=1) |
| **Params** | 135M (pre-trained tren 140GB text tieng Viet) |
| **Tokenizer** | V3: PhoBERT BPE. **Bat buoc** `underthesea.word_tokenize()` truoc |
| **Target** | log1p(price) → MSELoss |
| **VRAM** | ~8-10GB (FP16, batch=16). Du RTX 4060 Ti 16GB |
| **Train time** | ~30-45 phut (3-5 epochs, 85K items) |

**Tai sao PhoBERT tot cho bai toan nay:**
- Hieu ngu nghia tieng Viet: "Samsung Galaxy S24" vs "op lung Samsung Galaxy" → gia rat khac nhau
- Pre-trained tren 140GB tieng Viet — da biet cau truc ngon ngu
- Contextual embeddings: moi tu co vector khac nhau tuy ngu canh
- 135M params vua du cho 85K dataset (khong qua lon → overfitting)

**HuggingFace Trainer config:**
```python
TrainingArguments(
    num_train_epochs=3-5,
    per_device_train_batch_size=16,
    learning_rate=2e-5,        # Typical cho BERT fine-tune
    weight_decay=0.01,
    fp16=True,                 # Tiet kiem VRAM
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
)
```

**Uu diem:** Ky vong RMSLE tot nhat (0.38-0.44). SOTA cho Vietnamese NLP.
**Nhuoc diem:** Can underthesea. Cham hon DNN. Can HuggingFace Trainer boilerplate.

---

### Model 2: Vietnamese Embedding (frozen) + MLP

**2 variants:** dung 2 embedding models khac nhau, so sanh.

#### Model 2a: dangvantuan/vietnamese-embedding + MLP

| | Chi tiet |
|---|---------|
| **Embedding** | `dangvantuan/vietnamese-embedding` (768-dim, PhoBERT-based, STS 88.33) |
| **Kien truc** | Frozen embedding → MLP(768+8 → 512 → 256 → 128 → 1) |
| **Params** | Embedding 135M (frozen) + MLP ~500K (train) |
| **Tokenizer** | V5a: `pyvi.ViTokenizer.tokenize()` → encode → cache .npy |
| **VRAM** | ~2GB (encode) + ~1GB (MLP train) |
| **Train time** | Embed: ~15-20 phut + MLP: ~5 phut |

#### Model 2b: AITeamVN/Vietnamese_Embedding + MLP

| | Chi tiet |
|---|---------|
| **Embedding** | `AITeamVN/Vietnamese_Embedding` (1024-dim, BGE-M3 based, 300K triplets) |
| **Kien truc** | Frozen embedding → MLP(1024+8 → 512 → 256 → 128 → 1) |
| **Params** | Embedding 568M (frozen) + MLP ~600K (train) |
| **Tokenizer** | V5b: Khong can segment. Built-in SentencePiece |
| **VRAM** | ~4-5GB (encode) + ~1GB (MLP train) |
| **Train time** | Embed: ~25-30 phut + MLP: ~5 phut |

**Cau hinh chung cho Model 2:**

| Tham so | Gia tri |
|---------|---------|
| **Target** | log1p(price) → MSELoss |
| **MLP** | Input → 512 → ReLU → Dropout(0.3) → 256 → ReLU → 128 → ReLU → 1 |
| **Optimizer** | Adam(lr=0.001) |
| **Epochs** | 20-50 (MLP nho, train nhanh) |
| **Input** | embedding_dim + 8 (category one-hot) |

**Pipeline:**
```
1. (V5a) pyvi tokenize → dangvantuan encode → cache 85K x 768 float32 (.npy)
   (V5b) AITeamVN encode truc tiep → cache 85K x 1024 float32 (.npy)
2. Concat voi category one-hot (8 dim)
3. Train MLP
4. Evaluate
```

**Uu diem:** Nhanh nhat. Embed 1 lan, train nhieu lan. Dense semantic features.
**Nhuoc diem:** Frozen embedding khong adapt theo task. Model 2b nang hon (4x params) nhung co the tot hon.

---

### Model 3: XLM-RoBERTa-base Fine-tune (multilingual so sanh)

| | Chi tiet |
|---|---------|
| **HuggingFace** | `FacebookAI/xlm-roberta-base` |
| **Kien truc** | XLM-R encoder (12 layers, 768 hidden) + Linear regression head |
| **Params** | 278M (pre-trained tren 100 ngon ngu) |
| **Tokenizer** | V4: SentencePiece. **Khong can** underthesea/pyvi |
| **Target** | log1p(price) → MSELoss |
| **VRAM** | ~12-14GB (FP16, batch=16). Vua du RTX 4060 Ti 16GB |
| **Train time** | ~45-60 phut (3-5 epochs) |

**Tai sao test XLM-R:**
- So sanh voi PhoBERT: multilingual vs Vietnamese-specific
- Khong can Vietnamese tokenizer → setup don gian hon
- Ho tro mixed-language text tot (brand names tieng Anh trong data tieng Viet)
- 278M params lon hon PhoBERT 135M — nhung khong nhat thiet tot hon cho tieng Viet

**Uu diem:** Khong can Vietnamese segmenter. Ho tro mixed-language.
**Nhuoc diem:** Khong chuyen cho tieng Viet — PhoBERT thuong thang 2-5% tren VN benchmarks. Nang, ton VRAM.

---

### Model 4: Vietnamese Embedding (frozen) + LightGBM (Hybrid DL+ML)

**2 variants:** reuse cached embeddings tu Model 2.

#### Model 4a: dangvantuan embedding (768d) + LightGBM

| | Chi tiet |
|---|---------|
| **Input** | 768-dim embedding (reuse cache Model 2a) + 8 category one-hot = 776 features |
| **Model** | LightGBM (giong Day 3 config) |
| **Target** | log1p(price) |
| **Train time** | Reuse cache + LightGBM: ~1-2 phut |

#### Model 4b: AITeamVN embedding (1024d) + LightGBM

| | Chi tiet |
|---|---------|
| **Input** | 1024-dim embedding (reuse cache Model 2b) + 8 category one-hot = 1032 features |
| **Model** | LightGBM |
| **Target** | log1p(price) |
| **Train time** | Reuse cache + LightGBM: ~1-2 phut |

**Y tuong:** Ket hop suc manh:
- Dense semantic embeddings (vuot TF-IDF sparse 10K-dim)
- LightGBM (best ML model tu Day 3)
- Co the Optuna tune nhu Day 3

**So sanh truc tiep:** TF-IDF(10K) + LGB (Day 3 best) vs Embedding(768/1024) + LGB → do impact cua dense embeddings.

**Uu diem:** Nhanh, on dinh, ket hop best of DL + ML. Truc tiep do luong gia tri cua embeddings.
**Nhuoc diem:** Khong phai "pure DL". Frozen embeddings van khong adapt.

---

### Model 5: Vietnamese Embedding (frozen) + DNN ResidualBlock

**Y tuong:** Reuse code ResidualBlock tu Model 0, nhung input la dense embedding 768/1024 thay vi bag-of-words 5000/10K. Kiem tra xem deeper network co hoc mapping phi tuyen tot hon MLP don gian khong.

**2 variants:** reuse cached embeddings tu Model 2.

#### Model 5a: dangvantuan embedding (768d) + DNN ResidualBlock

| | Chi tiet |
|---|---------|
| **Input** | 768-dim embedding + 8 category one-hot = 776 features |
| **Kien truc** | InputLayer(776→1024) → ResidualBlock x 4 → OutputLayer(1024→1) |
| **Params** | ~8M (hidden=1024, nho hon Model 0 vi input nho) |
| **Target** | log(price+1) → normalize(mean, std) → L1Loss |
| **VRAM** | ~2GB |
| **Train time** | Reuse cache + DNN: ~10-15 phut |

#### Model 5b: AITeamVN embedding (1024d) + DNN ResidualBlock

| | Chi tiet |
|---|---------|
| **Input** | 1024-dim embedding + 8 category one-hot = 1032 features |
| **Kien truc** | InputLayer(1032→1024) → ResidualBlock x 4 → OutputLayer(1024→1) |
| **Params** | ~8M |
| **VRAM** | ~2GB |
| **Train time** | Reuse cache + DNN: ~10-15 phut |

**Cau hinh chung Model 5:**

| Tham so | Gia tri |
|---------|---------|
| hidden_size | 1024 (nho hon Model 0, vi embedding da encode ngu nghia) |
| num_layers | 6 (4 ResidualBlocks) |
| dropout | 0.2 |
| batch_size | 64 |
| epochs | 10 |
| optimizer | AdamW(lr=0.001, weight_decay=0.01) |
| scheduler | CosineAnnealingLR(T_max=10) |

**Uu diem:** Deeper than MLP, skip connections, reuse code Model 0. Kiem tra phi tuyen mapping.
**Nhuoc diem:** Likely marginal vs MLP vi input da la dense embedding (thong tin da "phang"). Nhung dang thu.
**Du doan:** LightGBM >= DNN ResidualBlock >= MLP (tren frozen embeddings)

---

### Bang so sanh tat ca models (bao gom variants)

| # | Model | Embedding | Params | VRAM | Train time | Ky vong RMSLE | Do kho |
|---|-------|-----------|--------|------|-----------|---------------|--------|
| 0a | DNN + HashingVec (2048) | V1 5000d | 73M | 4-6GB | 30 min | 0.48-0.52 | TB |
| 0b | DNN + TF-IDF (2048) | V2 10Kd | 73M | 4-6GB | 30 min | 0.48-0.52 | TB |
| 0c | DNN best vectorizer (4096) | V1/V2 | 289M | 8-12GB | 60 min | 0.46-0.50 | TB |
| 1 | **PhoBERT-v2 fine-tune** | V3 | 135M | 8-10GB | 30-45 min | **0.38-0.44** | TB |
| 2a | dangvantuan embed + MLP | V5a 768d | 135M+500K | 2-3GB | 25 min | 0.42-0.48 | De |
| 2b | AITeamVN embed + MLP | V5b 1024d | 568M+600K | 4-5GB | 35 min | 0.42-0.48 | De |
| 3 | XLM-R fine-tune | V4 | 278M | 12-14GB | 45-60 min | 0.40-0.46 | TB |
| 4a | dangvantuan embed + LGB | V5a 768d | frozen+trees | CPU | 2 min | 0.40-0.46 | De |
| 4b | AITeamVN embed + LGB | V5b 1024d | frozen+trees | CPU | 2 min | 0.40-0.46 | De |
| 5a | dangvantuan embed + DNN ResBlock | V5a 768d | ~8M | 2GB | 10-15 min | 0.42-0.48 | De |
| 5b | AITeamVN embed + DNN ResBlock | V5b 1024d | ~8M | 2GB | 10-15 min | 0.42-0.48 | De |

**Tong: ~12 experiments** (4 DNN-BoW + 2 Transformer fine-tune + 2 Embed+MLP + 2 Embed+LGB + 2 Embed+DNN)

---

## 5. Phan B: Frontier LLM (Zero-shot)

### 5.1. Cach tiep can

Goi API cac LLM, gui summary san pham va yeu cau du doan gia (VND). Khong fine-tune.
Test 200 items moi model. Chi dung cac model OpenAI re/nhanh.

### 5.2. Prompt (tieng Anh)

```
Estimate the price of this Vietnamese product in VND.
Respond with only the number, no explanation.

{item.summary}
```

### 5.3. Models

| Model | Provider | Loai | Chi phi uoc tinh (200 items) |
|-------|----------|------|------------------------------|
| gpt-4o-mini | OpenAI | Fast, re | ~$0.1-0.3 |
| gpt-5-nano | OpenAI | Fast | ~$0.3-0.5 |
| gpt-5-mini | OpenAI | Mid | ~$0.5-1 |

### 5.4. Thach thuc rieng cho tieng Viet

- LLM co the khong biet gia san pham VN (training data thieu so voi US/EU)
- Gia VND lon (100K-1M) — LLM co the bi nhau lan don vi
- Summary tieng Viet nhung prompt tieng Anh → model can hieu cross-language
- Ky vong: Frontier LLM se kem hon tren VND so voi USD (ky vong RMSLE co the > 0.50)

---

## 6. Pipeline thuc hien

### Phase 1: Data loading + Embedding extraction (chay 1 lan, dung chung Model 2 + 4)

```
Step 1: Load data tu HuggingFace (SeanSunny/items_tv_v6)
Step 2: Filter <= 1M VND, split train/val/test
Step 3: Underthesea tokenize tat ca summaries (cache .pkl — reuse Day 3 neu co)

Step 4a: pyvi tokenize → dangvantuan/vietnamese-embedding encode
         → cache train 85K x 768, val 3.9K x 768, test 3.9K x 768 (.npy)
Step 4b: AITeamVN/Vietnamese_Embedding encode (khong can segment)
         → cache train 85K x 1024, val 3.9K x 1024, test 3.9K x 1024 (.npy)
```

### Phase 2: Model 0 — DNN ResidualBlock (4 experiments)

```
Step 1: Vectorize V1 (HashingVectorizer) + V2 (TF-IDF)
Step 2: Train DNN hidden=2048 voi V1 → evaluate
Step 3: Train DNN hidden=2048 voi V2 → evaluate
Step 4: Chon vectorizer tot hon → train DNN hidden=4096 → evaluate
Step 5: (Optional) Vectorizer con lai + hidden=4096
Step 6: Save best model weights (.pth)
```

### Phase 3: Model 2 + 4 + 5 — Embedding-based (nhanh, 6 experiments)

```
Step 1: Load cached embeddings (.npy)
Step 2: Model 2a — MLP tren dangvantuan 768d + cat(8) → evaluate
Step 3: Model 2b — MLP tren AITeamVN 1024d + cat(8) → evaluate
Step 4: Model 4a — LightGBM tren dangvantuan 768d + cat(8) → evaluate
Step 5: Model 4b — LightGBM tren AITeamVN 1024d + cat(8) → evaluate
Step 6: Model 5a — DNN ResidualBlock tren dangvantuan 768d + cat(8) → evaluate
Step 7: Model 5b — DNN ResidualBlock tren AITeamVN 1024d + cat(8) → evaluate
Step 8: (Optional) Optuna tune LightGBM cho embedding tot nhat
```

### Phase 4: Model 1 — PhoBERT fine-tune (ky vong tot nhat)

```
Step 1: Load vinai/phobert-base-v2
Step 2: Tao custom Dataset class (tokenize + log1p price)
Step 3: HuggingFace Trainer, 3-5 epochs, FP16
Step 4: Evaluate tren test set (full 3,872 items)
Step 5: Save model
```

### Phase 5: Model 3 — XLM-RoBERTa fine-tune (so sanh)

```
Step 1: Load FacebookAI/xlm-roberta-base
Step 2: Tuong tu Phase 4, nhung KHONG can underthesea tokenize
Step 3: Evaluate → so sanh voi PhoBERT
```

### Phase 6: Frontier LLM (chay tren may local — chi can internet)

```
Step 1: Tao messages_for() function (prompt tieng Anh)
Step 2: Test 1 item truoc (debug)
Step 3: evaluate() 200 items cho moi LLM (gpt-4o-mini, gpt-5-nano, gpt-5-mini)
```

### Phase 7: Tong hop

```
Step 1: Bang tong hop: Day 3 ML vs 5 DL models vs 3 Frontier LLM
Step 2: Chart so sanh (Plotly)
Step 3: Phan tich: model nao tot nhat, tai sao
Step 4: Ket luan va huong di tiep (Day 5: Fine-tune LLM)
```

---

## 7. Moi truong chay

### May thue (DL training)

| Cau hinh | Option A | Option B |
|----------|----------|----------|
| GPU | RTX 4060 Ti 16GB VRAM | RTX 3090 Ti 24GB VRAM |
| CPU | i5-13400F 12 cores | i5 14th Gen 18 cores |
| RAM | 28GB | 88GB |
| CUDA cores | 4,352 | 10,752 |
| SSD | 1,500GB | 1,500GB |
| Net | 1 Gbps | 1 Gbps |

**Phu hop model:**

| Model | RTX 4060 Ti (16GB) | RTX 3090 Ti (24GB) |
|-------|--------------------|--------------------|
| 0: DNN (2048) | Du | Du |
| 0: DNN (4096) | Du (~8-12GB) | Du |
| 1: PhoBERT (FP16, bs=16) | Du (~8-10GB) | Du |
| 2: Embedding + MLP | Du (~2-4GB) | Du |
| 3: XLM-R (FP16, bs=16) | Sat (~12-14GB, giam bs=8 neu can) | Du |
| 4: Embedding + LGB | Du (CPU) | Du |

**De xuat:** RTX 4060 Ti du cho tat ca models. RTX 3090 Ti chi can neu muon chay XLM-R batch lon hoac PhoBERT-large sau nay.

### Workflow tren may thue

**Chi chay .ipynb** (tiet kiem chi phi, khong chay .py de tranh x2).
Sau khi chay xong, cung cap ket qua lai de phan tich + dieu chinh.

```bash
# ==========================================
# BUOC 1: Clone repo + setup (5-10 phut)
# ==========================================
git clone <repo-url> && cd tech2ai
uv sync

# Kiem tra GPU
uv run python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name()}' if torch.cuda.is_available() else 'CPU only')"

# ==========================================
# BUOC 2: Cai them dependencies cho Day 4
# ==========================================
uv add transformers accelerate sentence-transformers pyvi litellm lightgbm

# ==========================================
# BUOC 3: Copy tokenized cache tu Day 3 (neu co)
# ==========================================
# Neu may thue co file tokenized tu Day 3 (Google Drive), copy vao day4/:
# cp day3/tokenized_train_1m.pkl day4/
# cp day3/tokenized_val_1m.pkl day4/
# cp day3/tokenized_test_1m.pkl day4/
# Neu khong co → code se tu tokenize (~20 phut)

# ==========================================
# BUOC 4: Chay DL models notebook
# ==========================================
# Mo file: scraping_data_tv/Data_processing_for_Vietnamese_data/day4/day4_dl_models.ipynb
# Chay tung cell theo thu tu:
#   Phase 1: Load data + tokenize + embed + vectorize (~40-60 phut lan dau, <1 phut khi co cache)
#   Phase 2: Model 0 — DNN (3 experiments, ~30-60 phut)
#   Phase 3: Model 2/4/5 — Embedding-based (6 experiments, ~30-40 phut)
#   Phase 4: Model 1 — PhoBERT fine-tune (~30-45 phut)
#   Phase 5: Model 3 — XLM-R fine-tune (~45-60 phut)
#   Phase 7: Summary — in bang ket qua
#
# TONG THOI GIAN UOC TINH: 3-5 tieng (lan dau, co embedding extraction)
#                            2-3 tieng (lan sau, co cache)

# ==========================================
# BUOC 5: Chay Frontier LLM notebook (may local cung duoc)
# ==========================================
# Mo file: day4/day4_frontier_llm.ipynb
# Can OPENAI_API_KEY trong .env
# Thoi gian: ~15-30 phut (3 models x 200 items)

# ==========================================
# BUOC 6: Copy ket qua ve
# ==========================================
# Copy cac file nay ve may local:
#   day4/day4_results.json              — ket qua DL models
#   day4/day4_frontier_llm_results.json — ket qua Frontier LLM
#   day4/*.npy                          — embedding cache (neu muon reuse)
#   day4/phobert_best/                  — PhoBERT model (neu muon deploy)
#   day4/dnn_best.pth                   — DNN model weights
#
# Cung cap output cua cell cuoi (Phase 7: Summary) cho Claude de phan tich
```

### Luu y khi chay

- **Neu GPU het VRAM:** Giam `per_device_train_batch_size` tu 16 xuong 8 (PhoBERT/XLM-R)
- **Neu underthesea cham:** Kiem tra cache .pkl da load chua (dong log "Loading cache")
- **Neu embedding extraction cham:** Giam batch_size encode (128→64 cho dangvantuan, 64→32 cho AITeamVN)
- **Co the chay tung Phase rieng:** Moi cell doc lai cache tu Phase 1. Khong can chay lai tu dau
- **XLM-R sat VRAM (RTX 4060 Ti):** Neu OOM, giam batch_size=8 hoac bo qua Model 3

---

## 8. Caching strategy

Tat ca artifacts luu trong `day4/` de tiet kiem thoi gian khi re-run hoac doi may.

### 8.1. Tokenizer / Vectorizer cache

| File | Noi dung | Size uoc tinh | Tao boi |
|------|---------|---------------|---------|
| `tokenized_train_1m.pkl` | Underthesea pre-tokenized train summaries | ~30MB | Phase 1 (hoac reuse Day 3) |
| `tokenized_val_1m.pkl` | Underthesea pre-tokenized val | ~2MB | Phase 1 |
| `tokenized_test_1m.pkl` | Underthesea pre-tokenized test | ~2MB | Phase 1 |
| `hashing_vectorizer.pkl` | HashingVectorizer fitted (stateless, nho) | ~1KB | Phase 2 |
| `tfidf_vectorizer.pkl` | TfidfVectorizer fitted (can cho inference) | ~5MB | Phase 2 |

### 8.2. Embedding cache

| File | Noi dung | Size uoc tinh | Tao boi |
|------|---------|---------------|---------|
| `dangvantuan_train.npy` | dangvantuan embeddings train (85K x 768 float32) | ~250MB | Phase 1 |
| `dangvantuan_val.npy` | dangvantuan embeddings val (3.9K x 768) | ~12MB | Phase 1 |
| `dangvantuan_test.npy` | dangvantuan embeddings test (3.9K x 768) | ~12MB | Phase 1 |
| `aiteamvn_train.npy` | AITeamVN embeddings train (85K x 1024 float32) | ~330MB | Phase 1 |
| `aiteamvn_val.npy` | AITeamVN embeddings val (3.9K x 1024) | ~16MB | Phase 1 |
| `aiteamvn_test.npy` | AITeamVN embeddings test (3.9K x 1024) | ~16MB | Phase 1 |

### 8.3. Model weights

| File | Noi dung | Size uoc tinh | Tao boi |
|------|---------|---------------|---------|
| `dnn_best.pth` | DNN ResidualBlock best weights | ~300MB-1.1GB | Phase 2 |
| `phobert_best/` | PhoBERT fine-tuned model (full folder) | ~500MB | Phase 4 |
| `xlmr_best/` | XLM-R fine-tuned model | ~1.1GB | Phase 5 |
| `embed_dnn_best.pth` | Embed+DNN ResidualBlock best | ~32MB | Phase 3 |

### 8.4. Load order khi re-run

```python
# Neu cache ton tai → skip buoc tao, load truc tiep
if Path("tokenized_train_1m.pkl").exists():
    tokenized_train = joblib.load("tokenized_train_1m.pkl")  # skip underthesea
if Path("dangvantuan_train.npy").exists():
    emb_train = np.load("dangvantuan_train.npy")  # skip encode
```

**Tong dung luong cache:** ~700MB-1GB (embeddings) + ~35MB (tokenizer) + ~1-3GB (model weights)
Vua du SSD 1.5TB cua may thue.

---

## 9. Files

```
day4/
    plan_day4.md                    # File nay

    # Code (tao ca .py va .ipynb, chi CHAY .ipynb)
    day4_dl_models.py               # 6 DL models: train + evaluate (reference)
    day4_dl_models.ipynb            # Notebook tuong tac — CHAY FILE NAY
    day4_frontier_llm.py            # Frontier LLM evaluation (reference)
    day4_frontier_llm.ipynb         # Notebook Frontier LLM — CHAY FILE NAY

    # Tokenizer / Vectorizer cache
    tokenized_train_1m.pkl          # Underthesea cache (reuse Day 3 hoac tao moi)
    tokenized_val_1m.pkl
    tokenized_test_1m.pkl
    hashing_vectorizer.pkl          # HashingVectorizer fitted
    tfidf_vectorizer.pkl            # TfidfVectorizer fitted

    # Embedding cache
    dangvantuan_train.npy           # dangvantuan 85K x 768
    dangvantuan_val.npy             # 3.9K x 768
    dangvantuan_test.npy            # 3.9K x 768
    aiteamvn_train.npy              # AITeamVN 85K x 1024
    aiteamvn_val.npy                # 3.9K x 1024
    aiteamvn_test.npy               # 3.9K x 1024

    # Model weights (sau khi train)
    dnn_best.pth                    # DNN ResidualBlock best
    embed_dnn_best.pth              # Embed+DNN ResidualBlock best
    phobert_best/                   # PhoBERT fine-tuned model folder
    xlmr_best/                      # XLM-R fine-tuned model folder

pricer_vi/
    deep_neural_network.py          # MOI — DNN + ResidualBlock classes
    evaluator.py                    # Da co tu Day 3
    items.py                        # Da co
```

---

## 9. Dependencies

```bash
# Da co tu Day 3
uv add torch scikit-learn plotly underthesea lightgbm

# Them cho Day 4
uv add transformers accelerate   # HuggingFace Trainer (PhoBERT, XLM-R)
uv add sentence-transformers     # dangvantuan + AITeamVN embedding
uv add pyvi                      # Vietnamese word segmentation (cho dangvantuan)
uv add litellm                   # Frontier LLM API calls
```

**Env vars:** `OPENAI_API_KEY` (cho Frontier LLM). `HF_TOKEN` (optional, cho private models).

---

## 10. Metrics va evaluation

Dung `pricer_vi/evaluator.py` (da co) cho tat ca models. 4 metrics:

| Metric | Y nghia | Target |
|--------|---------|--------|
| **RMSLE** | Primary. Chuan Kaggle cho price prediction | <= 0.40 |
| **MAE (VND)** | Sai so tuyet doi trung binh | < 100K |
| **MAPE (%)** | Sai so phan tram | < 40% |
| **R2 (%)** | Giai thich duoc bao nhieu variance | > 55% |

**DL models:** evaluate full 3,872 test items.
**Frontier LLM:** evaluate 200 items (du de so sanh, tiet kiem chi phi).

---

## 11. KET QUA THUC TE (Day 4 v4 — 2026-04-16)

### Bang ket qua toan bo (sap xep theo RMSLE)

| # | Model | RMSLE | MAE (VND) | MAPE | R2 | Ghi chu |
|---|-------|-------|-----------|------|----|---------|
| 2b | AITeamVN+MLP | **0.4986** | 99,786 | 39.0% | 55.3% | **Best DL** — AITeamVN 1024d tot hon dangvantuan 768d |
| 0a | DNN+HashingVec (h=2048) | 0.5066 | 102,454 | 43.7% | 53.3% | HashingVec bat ngo tot hon TF-IDF |
| 5b | AITeamVN+DNN ResBlock | 0.5038 | 102,280 | 40.0% | 53.9% | AITeamVN tot hon dangvantuan |
| — | **Day 3 Baseline (Blended)** | **0.5164** | **109,725** | **44.0%** | **47.1%** | **BASELINE** |
| 3 | XLM-R fine-tune | 0.5170 | 111,584 | 51.0% | 53.1% | Ngang Day 3, MAPE cao |
| 0c | DNN+TF-IDF (h=4096) | 0.5212 | 105,011 | 44.1% | 50.6% | 309M params, khong cai thien |
| 2a | dangvantuan+MLP | 0.5256 | 107,960 | 44.5% | 49.4% | Frozen embed = TF-IDF level |
| 1 | PhoBERT-v2 fine-tune | 0.5268 | 115,287 | 47.0% | 45.5% | **THAT VONG** — ky vong 0.38-0.44 |
| 5a | dangvantuan+DNN ResBlock | 0.5414 | 112,400 | 46.8% | 46.9% | Deep network khong giup |
| 0b | DNN+TF-IDF (h=2048) | 0.5458 | 117,722 | 41.6% | 35.1% | Overfitting nang |
| 4b | AITeamVN+LightGBM | 0.5612 | 121,151 | 49.3% | 37.6% | LGB kem tren dense embedding |
| 4a | dangvantuan+LightGBM | 0.5685 | 121,652 | 49.2% | 36.1% | LGB kem nhat |

**Best DL: Model 2b (AITeamVN+MLP) RMSLE=0.4986** — cai thien 3.4% so voi Day 3 baseline.
**Target 0.40: CHUA DAT.** Khoang cach con ~20%.

### Phan tich chi tiet

**1. PhoBERT (Model 1) THAT VONG — RMSLE=0.5268 (ky vong 0.38-0.44):**
- Chi train 3 epochs voi HF Trainer default — co the chua du
- Tuy nhien, ket qua kem ca frozen embedding + MLP (0.4986)
- Nguyen nhan co the: HF Trainer loss la MSE tren log1p(price) — KHONG normalize (mean, std) nhu train_torch_model. Model phai hoc ca scale cua target
- PhoBERT tokenizer max_length=256 co the cat mat thong tin quan trong (Thong so ky thuat)
- 3 epochs co the qua it cho regression task (classification thuong 3 du, regression thuong can 5-10)

**2. XLM-R (Model 3) NGANG BASELINE — RMSLE=0.5170:**
- Tuong tu PhoBERT — chi 3 epochs, khong normalize target
- MAPE=51% cao nhat — nhieu du doan sai tuong doi lon
- 278M params nhung multilingual, khong chuyen cho tieng Viet

**3. AITeamVN tot hon dangvantuan o MOI head:**
- MLP: 0.4986 vs 0.5256 (AITeamVN thang)
- DNN: 0.5038 vs 0.5414 (AITeamVN thang)
- LGB: 0.5612 vs 0.5685 (AITeamVN thang)
- AITeamVN (1024d, BGE-M3) > dangvantuan (768d, PhoBERT-based) cho price prediction

**4. LightGBM kem tren dense embeddings:**
- Embedding+LGB (0.56-0.57) kem hon Embedding+MLP (0.50-0.53) va Embedding+DNN (0.50-0.54)
- Day 3 LGB+TF-IDF (0.5164) tot hon LGB+embedding (0.56)
- LGB voi default params khong exploit duoc 768/1024 dense features tot — can Optuna tune, hoac LGB khong phu hop voi dense embeddings

**5. DNN bag-of-words (Model 0a) bat ngo tot:**
- HashingVec (0.5066) tot hon TF-IDF (0.5458) — nguoc lai Day 3
- 77M params DNN overfit manh tren TF-IDF (train MSE 0.07 vs val 0.50)
- HashingVec binary features don gian hon, DNN generalize tot hon

**6. Overfitting la van de chinh:**
- Model 0b: train MSE 0.07 vs val 0.50 (7x gap)
- Model 0c: train MSE 0.06 vs val 0.46 (7.5x gap)
- Model 5b: train MSE 0.18 vs val 0.43 (2.4x gap)
- MLP nho (Model 2b) it overfitting hon → ket qua tot hon

### Nguyen nhan khong dat target

1. **Du lieu la bottleneck, khong phai model:** 85K items, 8 categories, text summary ngắn — du lieu khong du phong phu de model DL khai thac
2. **Frozen embeddings mat thong tin gia:** Embeddings toi uu cho semantic similarity, khong phai price. "Samsung Galaxy S24" vs "op lung Samsung" — ngu nghia gan, gia cach 20 lan
3. **PhoBERT/XLM-R chua tune du:** 3 epochs qua it, target khong normalize, khong warmup, khong early stopping tren custom metric
4. **LightGBM khong phu hop voi dense embeddings:** Can feature engineering hoac Optuna
5. **Model qua lon (DNN 77-309M) cho 85K data:** Overfitting nghiem trong

### Luu y ky thuat (tu qua trinh chay)

- **LightGBM eval keys:** `record_evaluation` dung key `"training"` va `"valid_1"` (KHONG phai `"valid_0"`). Metric key la `"l2"` (KHONG phai `"mse"`)
- **accelerate package:** Can `uv add accelerate` truoc khi chay HF Trainer (notebook khong bao loi)
- **PhoBERT warning:** `Some weights of RobertaForSequenceClassification were not initialized` — binh thuong, classifier head moi tao
- **LightGBM feature names warning:** `X does not have valid feature names` — do predict tren numpy array khong co column names, khong anh huong ket qua

---

## 12. Tieu chi hoan thanh

- [x] **Cache Phase 1:** tokenized .pkl + dangvantuan .npy + AITeamVN .npy
- [x] **Model 0 (DNN):** 3 variants da chay (MSELoss). Best: 0a RMSLE=0.5066
- [x] **Model 1 (PhoBERT):** 3 epochs. RMSLE=0.5268 (THAT VONG)
- [x] **Model 2a/2b (Embed+MLP):** Best: 2b RMSLE=0.4986 (best DL overall)
- [x] **Model 3 (XLM-R):** 3 epochs. RMSLE=0.5170 (ngang Day 3)
- [x] **Model 4a/4b (Embed+LGB):** Best: 4b RMSLE=0.5612 (kem)
- [x] **Model 5a/5b (Embed+DNN):** Best: 5b RMSLE=0.5038
- [ ] **Frontier LLM:** Chua chay (3 models x 200 items)
- [x] **Tong hop:** Bang so sanh da co. Best DL = 2b (0.4986), cai thien 3.4% so Day 3
- [x] **Model weights:** Da luu tat ca
- [x] **Code:** day4_dl_models_v4.ipynb da chay hoan tat

---

## 13. Quyet dinh da dua ra

- **Chay code:** Tao ca .py va .ipynb, chi CHAY .ipynb tren may thue (tranh x2 chi phi). .py la reference
- **Caching:** Tat ca tokenized/vectorized/embedding luu .pkl/.npy trong folder day4/. Load lai khi re-run
- DNN hidden_size: **2048 truoc, 4096 sau** (tung buoc, tranh overfitting tren 85K data)
- DNN Vectorizer: **chay ca HashingVectorizer va TF-IDF**, so sanh
- Frontier LLM: **prompt tieng Anh**, 200 items, chi 3 model OpenAI (gpt-4o-mini, gpt-5-nano, gpt-5-mini)
- Vietnamese tokenizer: **underthesea** (Day 3 cache) + **pyvi** (cho dangvantuan embedding)
- Vietnamese embedding: **test ca 2 models**, so sanh:
  - `dangvantuan/vietnamese-embedding` (768d, 135M, STS Pearson 88.33, can pyvi segment)
  - `AITeamVN/Vietnamese_Embedding` (1024d, 568M, BGE-M3 based, khong can segment)
- Embedding heads: **3 loai** — MLP, LightGBM, DNN ResidualBlock (so sanh tren cung embeddings)
- May thue: RTX 4060 Ti 16GB du cho tat ca models. RTX 3090 Ti neu can XLM-R batch lon
- Tong experiments: ~12 DL (4 DNN-BoW + 2 Transformer + 2 Embed+MLP + 2 Embed+LGB + 2 Embed+DNN) + 3 Frontier LLM

---

## 14. Root Cause Analysis — Tai sao ket qua kem

### 14.1. PhoBERT/XLM-R that bai vi TARGET KHONG NORMALIZE

Day la nguyen nhan chinh. So sanh 2 pipeline training:

| | `train_torch_model` (Model 0/2/5) | HF Trainer (PhoBERT/XLM-R) |
|---|---|---|
| Target | `log1p(price)` → **normalize(mean=12.1, std=0.83)** → MSELoss | `log1p(price)` → MSELoss (RAW, khong normalize) |
| Target range | **~-2 to +2** (mean=0, std=1) | **~8.5 to 13.8** |
| Classifier head init | Random weights → output ~0 → **gan target** | Random weights → output ~0 → **xa target 12 don vi** |
| Hau qua | Hoc ngu nghia tu epoch 1 | **Ton 1-2 epochs chi de shift output len ~12** |
| Epochs hieu qua | 5/5 epochs deu hoc ngu nghia | Chi ~1/3 epochs hoc ngu nghia (sau khi shift xong) |

**Minh chung:** PhoBERT 3 epochs (0.5268) thua MLP 30 epochs (0.4986). Nhung MLP chi co 562K params, PhoBERT co 135M. Van de khong phai model ma la training pipeline.

### 14.2. So sanh English vs Vietnamese

| | English (MAE $46.49) | Vietnamese (RMSLE 0.4986) |
|---|---|---|
| Data | **800K** train, 10K test | 85K train, 3.9K test (**10x it**) |
| DNN | 289M params, hidden=4096 | 77M params, hidden=2048 |
| Loss | L1Loss (normalize log-space) | MSELoss (normalize log-space) |
| Best model | DNN ResidualBlock | AITeamVN+MLP (frozen embed) |
| Transformer fine-tune | Khong test | PhoBERT/XLM-R (**khong normalize target**) |
| Ket qua | DNN thang Frontier LLM | DL chi hon ML 3.4% |

English thanh cong nho **800K data** (10x). Voi chi 85K, DNN lon (77-309M) overfitting nang. MLP nho (562K) + frozen embedding tot hon.

### 14.3. LightGBM kem tren dense embeddings

- Day 3: TF-IDF (10K sparse) + LGB = RMSLE 0.52 (tuned)
- Day 4: Embedding (768/1024 dense) + LGB = RMSLE 0.56-0.57 (default params)
- **Nguyen nhan:** LGB default `num_leaves=31` qua nho cho 768-1024 features. Can Optuna tune. Hoac: LGB split tren dense features khong hieu qua bang split tren sparse (TF-IDF co interpretable features, embedding khong co).

---

## 15. Day 4 v5 — 3 huong cai thien (Research-backed)

**Trang thai:** PLAN — chua thuc hien
**Target:** RMSLE <= 0.40 (hien tai: 0.4986)
**Nguon research:** BERT regression papers, e-commerce price prediction 2024-2025, so sanh English pipeline

### Huong 1: Fix PhoBERT fine-tune (UU TIEN CAO — ky vong RMSLE 0.44-0.48)

**Van de:** PhoBERT v4 train tren log1p(price) RAW (~8.5-13.8) → classifier head phai hoc scale truoc, roi moi hoc ngu nghia. 3 epochs qua it.

**Fix:**

| Thay doi | Cu (v4) | Moi (v5) | Ly do |
|----------|---------|----------|-------|
| **Target** | `log1p(price)` raw | `(log1p(price) - mean) / std` | Normalize ve ~0, +-2. Head init ~0 → match target |
| **Epochs** | 3 | 5-10 + early stopping (patience=2) | Regression can nhieu epochs hon classification |
| **LR schedule** | Linear decay (HF default) | Warmup 10% + cosine decay | Tranh hoc qua nhanh o dau |
| **Gradient clipping** | Khong | `max_grad_norm=1.0` | On dinh training |
| **Batch size** | 16 | 16 (giu nguyen) | VRAM du |
| **Eval metric** | eval_loss (MSE) | Custom RMSLE metric | Monitor dung metric target |

**Nang cao (neu co thoi gian):**

| Ky thuat | Mo ta | Ky vong |
|----------|-------|---------|
| **Gradual Unfreezing** | Epoch 1-2: chi train head. Epoch 3-5: unfreeze 2 top layers. Epoch 6+: full | Tranh catastrophic forgetting |
| **Layer-wise LR Decay (LLRD)** | Top layer lr=2e-5, moi layer duoi nhan 0.9x | Giu pre-trained features o layers thap |
| **Max length** | Tang 256 → 384 | Giu nhieu thong so ky thuat hon |

**Pipeline cu the:**
```python
# 1. Normalize target (nhu train_torch_model)
y_log = torch.log1p(prices)
y_mean, y_std = y_log.mean(), y_log.std()
y_norm = (y_log - y_mean) / y_std  # range ~-2 to +2

# 2. Train PhoBERT voi normalized target
# HF Trainer, MSELoss, 5-10 epochs

# 3. Inference: inverse transform
pred_log_norm = model(input).logits  # output ~-2 to +2
pred_price = torch.expm1(pred_log_norm * y_std + y_mean)
```

**Thoi gian:** ~1-2h GPU (5-10 epochs x 85K items)
**Ky vong RMSLE:** 0.44-0.48 (cai thien 10-15% tu 0.5268)

---

### Huong 2: PhoBERT [CLS] embedding → LightGBM stacking (UU TIEN CAO — ky vong RMSLE 0.45-0.49)

**Y tuong:** Research 2024-2025 cho thay: **frozen BERT embedding + GBDT thường tot hon fine-tune BERT** khi data < 100K. Ly do: GBDT xu ly tabular features tot hon MLP, va frozen embedding khong bi overfitting.

**Khac voi Day 4 v4 (Model 4a/4b):** v4 dung dangvantuan/AITeamVN (general-purpose embedding). Huong nay dung **PhoBERT [CLS] token** — embedding tu contextual model tren tieng Viet, 768d.

**Pipeline:**

```
Step 1: Load PhoBERT-base-v2 (hoac PhoBERT da fine-tune tu Huong 1)
Step 2: Extract [CLS] embedding cho train/val/test (85K x 768)
        → Cache .npy (tuong tu dangvantuan)
Step 3: (Optional) PCA 768d → 256d (giam noise, tranh overfitting LGB)
Step 4: Concat features: [CLS]_768d + category_8d = 776 features
Step 5: LightGBM Optuna tune (target = log1p(price))
Step 6: Evaluate
```

**Thoi gian:** ~30 phut GPU (extract embed) + ~10 phut CPU (Optuna LGB)
**Ky vong RMSLE:** 0.45-0.49

**Bien the:** Neu PhoBERT da fine-tune (Huong 1), extract [CLS] tu fine-tuned model → embeddings da adapt cho price task → ky vong tot hon general-purpose.

---

### Huong 3: Blending / Stacking best models (ON DINH — ky vong RMSLE 0.47-0.49)

**Y tuong:** Ket hop suc manh cua nhieu models. Moi model co strengths khac nhau:
- **AITeamVN+MLP (0.4986):** Tot tren semantic understanding
- **DNN+HashingVec (0.5066):** Tot tren keyword matching
- **Day 3 LGB+TF-IDF (0.5164):** Tot tren n-gram patterns
- **PhoBERT fine-tune (sau Huong 1):** Tot tren contextual understanding

**2 phuong phap:**

**A. Simple Blending (weighted average):**
```python
# Tim weight toi uu tren validation set
pred_final = w1 * pred_2b + w2 * pred_0a + w3 * pred_day3 + w4 * pred_phobert
# w1 + w2 + w3 + w4 = 1
# Optimize bang scipy.minimize tren val RMSLE
```

**B. Stacking (meta-learner):**
```python
# Level 1: Out-of-fold predictions tu moi base model
# Level 2: Ridge/LightGBM train tren stacked predictions
meta_features = [pred_2b_oof, pred_0a_oof, pred_day3_oof, pred_phobert_oof]
meta_model = Ridge().fit(meta_features_train, y_train_log)
```

**Thoi gian:** ~30 phut CPU (chi can predictions da co)
**Ky vong RMSLE:** 0.47-0.49 (chac chan cai thien vi diversified ensemble)

---

### Thu tu thuc hien

| Phase | Huong | Can GPU? | Thoi gian | Dependencies |
|-------|-------|----------|-----------|-------------|
| v5-A | **Huong 1:** Fix PhoBERT fine-tune | Co (1-2h) | 1-2h | Khong |
| v5-B | **Huong 2:** PhoBERT [CLS] → LGB | Co (30 phut) | 1h | Sau Huong 1 (dung fine-tuned PhoBERT) |
| v5-C | **Huong 3:** Blending best models | Khong (CPU) | 30 phut | Sau Huong 1+2 (co predictions) |

**Tong thoi gian may thue:** ~3-4h (bao gom ca train + extract + tune)

### Bang ky vong v5

| Model | Ky vong RMSLE | So voi Day 3 (0.5164) |
|-------|---------------|----------------------|
| PhoBERT v5 (fixed) | 0.44-0.48 | +7-15% |
| PhoBERT [CLS] + LGB | 0.45-0.49 | +5-13% |
| Blended ensemble | 0.47-0.49 | +5-9% |
| **Best possible (combine all)** | **0.42-0.46** | **+11-19%** |

---

## 16. Tieu chi hoan thanh (cap nhat)

### Day 4 v4 (DA XONG)
- [x] Cache Phase 1: tokenized + embeddings
- [x] Model 0 (DNN): 3 variants. Best: 0a RMSLE=0.5066
- [x] Model 1 (PhoBERT): 3 epochs. RMSLE=0.5268 (THAT VONG — khong normalize target)
- [x] Model 2a/2b (Embed+MLP): Best: 2b RMSLE=0.4986 (best DL overall)
- [x] Model 3 (XLM-R): 3 epochs. RMSLE=0.5170
- [x] Model 4a/4b (Embed+LGB): Best: 4b RMSLE=0.5612 (LGB default, khong tune)
- [x] Model 5a/5b (Embed+DNN): Best: 5b RMSLE=0.5038
- [x] Tong hop v4: Best = 2b (0.4986), target 0.40 chua dat

### Day 4 v5 (CAN LAM)
- [ ] **Huong 1:** PhoBERT fine-tune voi normalized target, 5-10 epochs, early stopping
- [ ] **Huong 2:** PhoBERT [CLS] embedding → LightGBM Optuna
- [ ] **Huong 3:** Blending best models (weighted/stacking)
- [ ] **Frontier LLM:** 3 models x 200 items (optional, tham khao)
- [ ] **Tong hop v5:** Bang so sanh toan bo + ket luan

---

## 17. Quyet dinh da dua ra

### v4 (da chay)
- Chi chay .ipynb tren may thue (tranh x2 chi phi). .py la reference
- Caching: tokenized/vectorized/embedding luu .pkl/.npy
- DNN hidden_size: 2048 truoc, 4096 sau → 4096 overfitting, 2048 tot hon
- HashingVec bat ngo tot hon TF-IDF cho DNN (nguoc lai Day 3)
- AITeamVN (1024d) > dangvantuan (768d) o moi head
- LightGBM kem tren dense embeddings voi default params
- PhoBERT/XLM-R chi 3 epochs + khong normalize target → ket qua kem

### v5 (moi — tu research)
- **PhoBERT target phai normalize** (mean, std) nhu train_torch_model — day la fix quan trong nhat
- **Gradual unfreezing** + LLRD cho PhoBERT (tranh catastrophic forgetting)
- **PhoBERT [CLS] → LGB** thuong tot hon fine-tune khi data < 100K (research 2024-2025)
- **Blending/stacking** chac chan cai thien vi diversified ensemble

---

*Tao: 2026-04-15. Cap nhat: 2026-04-16. Trang thai: v4 DA CHAY (best 0.4986). v5 PLAN — 3 huong cai thien (fix PhoBERT, [CLS]+LGB, blending). Target 0.40.*